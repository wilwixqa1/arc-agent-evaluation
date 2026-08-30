"""Arcscan (Blockscout) client.

Aggregate counts come from here rather than the RPC. The explorer has no
10,000-block log range limit and answers holder and transfer counts in one call,
which would otherwise take thousands of eth_getLogs requests.
"""
from __future__ import annotations

import os
import time
from typing import Any

import requests

DEFAULT_EXPLORER = "https://testnet.arcscan.app"


class Explorer:
    def __init__(self, base: str | None = None, timeout: int = 30) -> None:
        self.base = (base or os.environ.get("ARC_EXPLORER_URL", DEFAULT_EXPLORER)).rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()

    def _get(self, path: str, params: dict | None = None, attempts: int = 4) -> Any:
        url = f"{self.base}{path}"
        for i in range(attempts):
            try:
                r = self._session.get(
                    url, params=params, timeout=self.timeout, headers={"accept": "application/json"}
                )
                if r.status_code == 429:
                    time.sleep(1.5 * (i + 1))
                    continue
                r.raise_for_status()
                return r.json()
            except Exception:
                if i == attempts - 1:
                    raise
                time.sleep(0.6 * (i + 1))
        return None

    def stats(self) -> dict:
        return self._get("/api/v2/stats")

    def token(self, address: str) -> dict:
        return self._get(f"/api/v2/tokens/{address}")

    def token_counters(self, address: str) -> dict:
        return self._get(f"/api/v2/tokens/{address}/counters")

    def address_counters(self, address: str) -> dict:
        return self._get(f"/api/v2/addresses/{address}/counters")

    def contract(self, address: str) -> dict:
        return self._get(f"/api/v2/smart-contracts/{address}")

    def token_instances(self, address: str, pages: int = 1) -> list[dict]:
        """Walk the paginated NFT instance list, newest first."""
        out: list[dict] = []
        params: dict | None = None
        for _ in range(pages):
            page = self._get(f"/api/v2/tokens/{address}/instances", params=params)
            if not page:
                break
            out.extend(page.get("items", []))
            nxt = page.get("next_page_params")
            if not nxt:
                break
            params = nxt
        return out

    def token_holders(self, address: str, pages: int = 1) -> list[dict]:
        out: list[dict] = []
        params: dict | None = None
        for _ in range(pages):
            page = self._get(f"/api/v2/tokens/{address}/holders", params=params)
            if not page:
                break
            out.extend(page.get("items", []))
            nxt = page.get("next_page_params")
            if not nxt:
                break
            params = nxt
        return out
