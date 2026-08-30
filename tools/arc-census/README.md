# arc-census

Measures the real state of the ERC-8004 and ERC-8183 deployments on Arc.

Answers one question the existing tooling does not: of the agents registered on
this chain, how many are reachable services rather than registry entries?

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python census.py totals                      # chain + contract aggregates
python census.py agents --n 250 --probe      # sample agents, probe endpoints
python census.py jobs --n 120                # ERC-8183 job sampling
python census.py reputation --n 140          # feedback, scales, self-dealing
python census.py all                         # everything, then render REPORT.md
python census.py report                      # re-render from cached data/
```

Output lands in `data/` as JSONL plus summary JSON, and `data/REPORT.md`.

## Scaling past the public RPC

The public endpoint throttles above roughly eight concurrent requests and caps
`eth_getLogs` at a 10,000 block range. For publication-grade sample sizes:

```bash
export ARC_RPC_URL="https://<your-provider-endpoint>"
export ARC_RPC_CONCURRENCY=32
python census.py agents --n 3000 --probe
```

Aggregate counts come from the Blockscout API at `testnet.arcscan.app`, which has
no such limits, so `totals` is fast regardless.

## Notes on the deployed contracts

All four registries are ERC-1967 proxies. `census.py totals` resolves and records
the implementation addresses; re-check them before trusting a cached ABI.

Two ABI details that differ from commonly published descriptions:

```
giveFeedback(uint256 agentId, int128 value, uint8 valueDecimals,
             string tag1, string tag2, string endpoint,
             string feedbackURI, bytes32 feedbackHash)

jobs(uint256) -> (id, client, provider, evaluator, description,
                  budget, expiredAt, status, hook)
```

There is no `commitmentRef` and no `intent` field on the job struct.
