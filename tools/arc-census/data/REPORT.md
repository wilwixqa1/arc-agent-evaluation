# Arc ERC-8004 / ERC-8183 Census

Generated 2026-08-30T05:27:43.461719+00:00

## Chain

- RPC: `https://rpc.testnet.arc.io/`  chain id `5042002`
- Block height: 59,447,221
- Average block time: 530.0 ms

### Contracts

| Contract | Proxy | Implementation | Transactions |
|---|---|---|---|
| identity | `0x8004A818BFB912233c491871b3d84c89A494BD9e` | `0x7274e874ca62410a93bd8bf61c69d8045e399c02` | 886637 |
| reputation | `0x8004B663056A597Dffe9eCcC1965A193B7388713` | `0x16e0fa7f7c56b9a767e34b192b51f921be31da34` | 18972296 |
| validation | `0x8004Cb1BF31DAf7788923b405b754f57acEB4272` | `0xdb31f5d9167f8ebc8b30fbbf814c4d297c2d7f99` | 110222 |
| agentic_commerce | `0x0747EEf0706327138c69792bF28Cd525089e4583` | `0xa316fd02827242d537f84730f8a37d0ba5fd351a` | 600477 |

- AgentIdentity holders: **47215**
- AgentIdentity transfers: **887911**

- ERC-8183 jobs: **182373**
- evaluatorFeeBP: **0**, platformFeeBP: **0**

## Agent identity and reachability

Random sample of **250** agents from **888,262** registered (seed 7).

| Metric | Count | Share |
|---|---|---|
| No tokenURI set | 1 | 0.4% |
| Declares a service endpoint | 4 | 1.6% |
| **Reachable endpoint** | 0 | 0.0% |
| Uses Circle quickstart CID | 3 | 1.2% |
| Malformed IPFS CID | 4 | 1.6% |
| Placeholder host (example.com) | 3 | 1.2% |
| Has ERC-8004 `services` array | 0 | 0.0% |
| Has ERC-8004 `registrations` array | 0 | 0.0% |
| Has `type` field | 6 | 2.4% |
| Mentions x402 | 0 | 0.0% |
| Mentions MCP | 0 | 0.0% |

URI schemes: `{'data': 238, 'ipfs': 7, 'none': 1, 'http': 4}`

**Zero reachable endpoints in 250 samples.** Rule of three puts the 95% upper bound on the true rate at 1.2%.

Name patterns (trailing hash stripped):

```
  109  Agent
   56  Trader
   50  Bridge
    7  Agent-Mega
    5  hermes
    3  VAgent
    1  Agent-Mega-101
    1  Agent-Mega-847
    1  Agent-Mega-133
    1  Agent-Mega-57
```

## ERC-8183 jobs

Random sample of **120** of **182,398** jobs.

- Status: `{'Completed': 60, 'Open': 54, 'Funded': 3, 'Rejected': 2, 'Submitted': 1}`
- **evaluator == client: 81 (67.5%)**
- evaluator == provider: 13
- **hook set (not address(0)): 0 (0.0%)**
- Zero budget: 60

Top descriptions:

```
   19  'Arc automation job'
   13  'ERC-8183 job'
    6  'ERC-8183 demo job on Arc Testnet'
    5  'Analyze competitor DEX features and write a detailed comparison'
    4  'Arc autonomous agent job | client_wallet=4 | provider_wallet=5 | evalu'
    3  'Arc autonomous agent job | client_wallet=5 | provider_wallet=1 | evalu'
    3  'ERC-8183 demo job from viem on Arc Testnet'
    2  'crosschain USDC arbitrage scan between Arc and Ethereum Sepolia'
    2  'Optimize LP positions across Arc DEX pools'
    2  'Arc autonomous agent job | client_wallet=3 | provider_wallet=4 | evalu'
```

## Reputation

- Agents sampled: 140
- With any feedback: **35** (25.0%)
- **Owner rated own agent: 0 (0.0% of rated)**
- Single-client agents: 6 (17.14%)
- Distinct reviewers: 959, top reviewer share 0.5%
- Value range: None to None, above 100: None, below zero: None
- valueDecimals distribution: `{'2': 1742, '0': 549, '1': 4}`
- Distinct tags: 316

---

Reproduce: `python census.py all`. Set `ARC_RPC_URL` to a keyed provider and raise `ARC_RPC_CONCURRENCY` to scale the sample size.
