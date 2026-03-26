---
name: market-manifold
description: "Read Manifold Markets odds and compare against Swarmy consensus to find betting edges"
version: 2.0.0
author: SwarmBet
metadata:
  filePattern: "**/*manifold*"
  bashPattern: "manifold"
dependencies:
  - swarm-intelligence
env: []
---

# Market Reader: Manifold Markets

Read-only access to **Manifold Markets** prediction market odds. No API key required.

Manifold is an open-source prediction market platform. Play-money (Mana) based, but has the largest number of active markets on any topic.

## No API Key Needed

Manifold's API is fully public. No authentication for reading.

## Usage

After running `/swarmy "question"`, compare against Manifold odds:

```python
from market_reader import MarketReader

reader = MarketReader()

# Search for markets
markets = reader.manifold_search("bitcoin", limit=5)
for m in markets:
    print(f'{m["question"]}')
    print(f'  YES: {m["yes_price"]}  NO: {m["no_price"]}  Volume: {m["volume"]}')

# Calculate edge against swarmy result
edge = reader.calculate_edge(swarm_pct=68, market_yes_price=0.54)
print(f'{edge["action"]} | Edge: {edge["edge_pct"]} | {edge["reasoning"]}')
```

## API Reference

Base URL: `https://api.manifold.markets/v0`

```
GET /search-markets?term=bitcoin&limit=5&filter=open&sort=liquidity
Response: [{"question": "...", "probability": 0.54, "volume": 1234, ...}]
```

## Edge Output Format

```
 ───────────────────────────────────────────────────────
  EDGE ANALYSIS: Swarmy vs Manifold
 ───────────────────────────────────────────────────────
  Market:    Will Bitcoin hit $80K in March?
  Manifold:  4% YES (play money)
  Swarmy:    40% YES
  Edge:      +36%
  Signal:    STRONG BUY YES (HIGH confidence)
  Note:      Manifold uses play money — edge is
             informational, not directly tradeable.
 ───────────────────────────────────────────────────────
```

## Note on Manifold

Manifold uses play money (Mana), not real USD/crypto. Edge signals from Manifold are useful for:
- Validating swarm predictions against crowd wisdom
- Finding questions where swarm disagrees with the crowd
- Academic/research purposes

For real-money edge signals, use Kalshi or Polymarket.
