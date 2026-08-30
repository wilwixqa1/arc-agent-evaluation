"""JSON-RPC client for Arc, with retry, adaptive concurrency and ABI helpers.

The public Arc RPC sits behind Cloudflare and throttles hard above roughly eight
concurrent requests. Set ARC_RPC_URL to a keyed provider (QuickNode, Chainstack,
GetBlock) and raise ARC_RPC_CONCURRENCY to scan at speed.
"""
from __future__ import annotations

import os
import time
import threading
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, Sequence

import requests
from eth_abi import abi as eth_abi
from eth_hash.auto import keccak

DEFAULT_RPC = "https://rpc.testnet.arc.io/"
ARC_TESTNET_CHAIN_ID = 5042002
ARC_MAINNET_CHAIN_ID = 5042

# EIP-1967 implementation slot
IMPL_SLOT = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"

CONTRACTS = {
    "identity": "0x8004A818BFB912233c491871b3d84c89A494BD9e",
    "reputation": "0x8004B663056A597Dffe9eCcC1965A193B7388713",
    "validation": "0x8004Cb1BF31DAf7788923b405b754f57acEB4272",
    "agentic_commerce": "0x0747EEf0706327138c69792bF28Cd525089e4583",
    "usdc": "0x3600000000000000000000000000000000000000",
}


def selector(signature: str) -> str:
    """Four byte function selector for a canonical signature."""
    return "0x" + keccak(signature.encode()).hex()[:8]


def topic(signature: str) -> str:
    """Event topic0 for a canonical signature."""
    return "0x" + keccak(signature.encode()).hex()


def encode_call(signature: str, arg_types: Sequence[str], args: Sequence[Any]) -> str:
    """Encode a function call. signature must be canonical, e.g. tokenURI(uint256)."""
    body = eth_abi.encode(list(arg_types), list(args)).hex() if arg_types else ""
    return selector(signature) + body


def decode_result(result: str, out_types: Sequence[str]) -> tuple:
    if not result or result == "0x":
        raise ValueError("empty result")
    return eth_abi.decode(list(out_types), bytes.fromhex(result[2:]))


class RpcError(RuntimeError):
    pass


@dataclass
class RpcStats:
    calls: int = 0
    retries: int = 0
    failures: int = 0
    throttles: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def bump(self, name: str, n: int = 1) -> None:
        with self._lock:
            setattr(self, name, getattr(self, name) + n)


class ArcClient:
    """Thread-safe JSON-RPC client.

    Retries with exponential backoff. Treats HTTP 429 and Cloudflare failures as
    throttling and backs the whole client off briefly so parallel workers do not
    stampede a rate-limited endpoint.
    """

    def __init__(
        self,
        url: str | None = None,
        concurrency: int | None = None,
        max_attempts: int = 5,
        timeout: int = 45,
    ) -> None:
        self.url = url or os.environ.get("ARC_RPC_URL", DEFAULT_RPC)
        self.concurrency = concurrency or int(os.environ.get("ARC_RPC_CONCURRENCY", "5"))
        self.max_attempts = max_attempts
        self.timeout = timeout
        self.stats = RpcStats()
        self._session = requests.Session()
        pool = max(self.concurrency + 8, 16)
        self._session.mount(
            "https://", requests.adapters.HTTPAdapter(pool_connections=pool, pool_maxsize=pool)
        )
        self._cooldown_until = 0.0
        self._cool_lock = threading.Lock()

    # -- transport ---------------------------------------------------------

    def _respect_cooldown(self) -> None:
        while True:
            with self._cool_lock:
                wait = self._cooldown_until - time.monotonic()
            if wait <= 0:
                return
            time.sleep(min(wait, 1.0))

    def _trigger_cooldown(self, seconds: float) -> None:
        with self._cool_lock:
            self._cooldown_until = max(self._cooldown_until, time.monotonic() + seconds)
        self.stats.bump("throttles")

    def raw(self, method: str, params: list) -> Any:
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        last: Exception | None = None
        for attempt in range(self.max_attempts):
            self._respect_cooldown()
            try:
                resp = self._session.post(self.url, json=payload, timeout=self.timeout)
                self.stats.bump("calls")
                if resp.status_code == 429:
                    self._trigger_cooldown(1.5 * (attempt + 1))
                    last = RpcError("HTTP 429")
                    continue
                data = resp.json()
                if "result" in data:
                    return data["result"]
                err = data.get("error", {})
                # Deterministic contract reverts are answers, not failures.
                if "revert" in str(err.get("message", "")).lower():
                    raise RpcError(err.get("message", "execution reverted"))
                last = RpcError(str(err))
            except RpcError:
                raise
            except Exception as exc:  # network, json, timeout
                last = exc
                self._trigger_cooldown(0.75 * (attempt + 1))
            self.stats.bump("retries")
            time.sleep(0.35 * (attempt + 1))
        self.stats.bump("failures")
        raise RpcError(f"{method} failed after {self.max_attempts} attempts: {last}")

    # -- convenience -------------------------------------------------------

    def chain_id(self) -> int:
        return int(self.raw("eth_chainId", []), 16)

    def block_number(self) -> int:
        return int(self.raw("eth_blockNumber", []), 16)

    def code_size(self, address: str, block: str = "latest") -> int:
        code = self.raw("eth_getCode", [address, block])
        return max(len(code) // 2 - 1, 0)

    def implementation_of(self, proxy: str) -> str | None:
        """Resolve an EIP-1967 proxy to its implementation, or None if not a proxy."""
        slot = self.raw("eth_getStorageAt", [proxy, IMPL_SLOT, "latest"])
        if not slot or int(slot, 16) == 0:
            return None
        return "0x" + slot[-40:]

    def deployment_block(self, address: str, hi: int | None = None) -> int | None:
        """Binary search the first block at which the address has code."""
        hi = hi if hi is not None else self.block_number()
        if self.code_size(address, hex(hi)) == 0:
            return None
        lo = 0
        while lo < hi:
            mid = (lo + hi) // 2
            if self.code_size(address, hex(mid)) == 0:
                lo = mid + 1
            else:
                hi = mid
        return lo

    def call(
        self,
        to: str,
        signature: str,
        arg_types: Sequence[str] = (),
        args: Sequence[Any] = (),
        out_types: Sequence[str] = (),
        block: str = "latest",
    ):
        data = encode_call(signature, arg_types, args)
        result = self.raw("eth_call", [{"to": to, "data": data}, block])
        if not out_types:
            return result
        return decode_result(result, out_types)

    def map(self, fn, items: Iterable, workers: int | None = None) -> Iterator:
        """Parallel map that never raises; failures come back as None."""
        from concurrent.futures import ThreadPoolExecutor

        def safe(x):
            try:
                return fn(x)
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=workers or self.concurrency) as ex:
            yield from ex.map(safe, items)
