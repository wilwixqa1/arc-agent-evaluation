"""Hand-seeded phrasing variations.

Model-generated variations come later and need an API key, but hand-seeded ones are
required regardless. §11 of the context doc names the risk: if one generator writes
every variation, "optimal phrasing" collapses into "phrasing our generator produces"
and every finding is an artifact of prompt style. Mixing hand-written variations in is
the control.

Each set contains:
  - `canonical`  the literal task.summary wording; `brittle` recognizes only this
  - three paraphrases that mean the same thing in different words
  - one terse form and one verbose form, to vary length independently of wording

`generator` is recorded so we can later test whether generator identity predicts
outcome. If it does, that is a finding rather than a bug.
"""

PHRASINGS = {
    "usdc-supply": [
        {"phrasingId": "canonical", "generator": "hand",
         "text": "Get the current total USDC supply on Arc testnet and the block it was read at"},
        {"phrasingId": "para-1", "generator": "hand",
         "text": "How much USDC is in circulation on Arc right now, and at which block?"},
        {"phrasingId": "para-2", "generator": "hand",
         "text": "I need the outstanding amount of USDC issued on the Arc test network, with the block height of the reading"},
        {"phrasingId": "para-3", "generator": "hand",
         "text": "What does totalSupply return for the USDC token contract on Arc testnet, and as of when?"},
        {"phrasingId": "terse", "generator": "hand",
         "text": "USDC supply on Arc, plus block"},
        {"phrasingId": "verbose", "generator": "hand",
         "text": "I am putting together a dashboard panel that displays circulating USDC on the Arc test network. For that I need the current total supply figure together with the block number it was read at, so the number can be shown with its provenance rather than as a bare quantity."},
    ],
    "x402-summary": [
        {"phrasingId": "canonical", "generator": "hand",
         "text": "Summarize x402 settlement activity on Base over the last 24 hours"},
        {"phrasingId": "para-1", "generator": "hand",
         "text": "How much x402 payment activity has there been on Base in the past day?"},
        {"phrasingId": "para-2", "generator": "hand",
         "text": "Give me a rundown of payments settled through x402 on Base since yesterday"},
        {"phrasingId": "para-3", "generator": "hand",
         "text": "What volume has moved over the x402 protocol on Base recently, covering roughly one day?"},
        {"phrasingId": "terse", "generator": "hand",
         "text": "x402 on Base, last day, numbers"},
        {"phrasingId": "verbose", "generator": "hand",
         "text": "I am trying to work out whether x402 volume on Base is growing fast enough to justify building a paid service there. What I want is the settlement activity over roughly the last twenty-four hours, with enough detail on the window and the method that I could reproduce the figure myself."},
    ],
    "contract-analysis": [
        {"phrasingId": "canonical", "generator": "hand",
         "text": "Who can upgrade the ERC-8183 AgenticCommerce contract on Arc testnet and what does that let them change?"},
        {"phrasingId": "para-1", "generator": "hand",
         "text": "Is 0x0747EEf0706327138c69792bF28Cd525089e4583 mutable, and if so by whom?"},
        {"phrasingId": "para-2", "generator": "hand",
         "text": "What are the admin powers over the AgenticCommerce deployment on Arc?"},
        {"phrasingId": "para-3", "generator": "hand",
         "text": "If I build on the Arc 8183 contract, what could someone change out from under me?"},
        {"phrasingId": "terse", "generator": "hand",
         "text": "8183 Arc upgrade control?"},
        {"phrasingId": "verbose", "generator": "hand",
         "text": "I am deciding whether to depend on the ERC-8183 AgenticCommerce contract at 0x0747EEf0706327138c69792bF28Cd525089e4583 staying stable. Please tell me whether it is upgradeable, who holds the authority to upgrade or reconfigure it, and which specific parameters they could alter that would change behaviour for people already using it."},
    ],
}
