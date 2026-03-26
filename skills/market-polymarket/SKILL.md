---
name: market-polymarket
description: "Read Polymarket prediction market odds and compare against Swarmy consensus to find betting edges"
version: 2.0.0
author: SwarmBet
metadata:
  filePattern: "**/*polymarket*"
  bashPattern: "polymarket"
dependencies:
  - swarm-intelligence
env: []
---

# Market Reader: Polymarket

Read-only access to **Polymarket** prediction market odds. No API key required.

Polymarket is the world's largest prediction market (crypto-settled on Polygon). Binary YES/NO outcomes on politics, crypto, world events, sports, and more.

## No API Key Needed

Polymarket's market data is publicly accessible via the Gamma API and CLOB API.

## Usage

After running `/swarmy "question"`, compare against Polymarket odds:

```python
from market_reader import MarketReader

reader = MarketReader()

# Search for markets
markets = reader.polymarket_search("bitcoin", limit=5)
for m in markets:
    print(f'{m["question"]}')
    print(f'  YES: {m["yes_price"]}  NO: {m["no_price"]}  Volume: {m["volume"]}')

# Calculate edge against swarmy result
edge = reader.calculate_edge(swarm_pct=68, market_yes_price=0.54)
print(f'{edge["action"]} | Edge: {edge["edge_pct"]} | {edge["reasoning"]}')
```

## API Reference

Gamma API: `https://gamma-api.polymarket.com`
CLOB API: `https://clob.polymarket.com`

```
GET /markets?closed=false&limit=10&order=volume&ascending=false
Response: [{"question": "...", "outcomes": "Yes,No", "outcomePrices": "0.54,0.46", ...}]
```

## Edge Output Format

```
 ───────────────────────────────────────────────────────
  EDGE ANALYSIS: Swarmy vs Polymarket
 ───────────────────────────────────────────────────────
  Market:    Will BTC hit $120K by April?
  Polymarket: 54% YES ($1.2M volume)
  Swarmy:     68% YES
  Edge:       +14%
  Signal:     BUY YES (MEDIUM confidence)
 ───────────────────────────────────────────────────────
  This is NOT financial advice. Markets can lose 100%.
 ───────────────────────────────────────────────────────
```
