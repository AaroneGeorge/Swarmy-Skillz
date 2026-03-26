---
name: market-kalshi
description: "Read Kalshi prediction market odds and compare against Swarmy consensus to find betting edges"
version: 2.0.0
author: SwarmBet
metadata:
  filePattern: "**/*kalshi*"
  bashPattern: "kalshi"
dependencies:
  - swarm-intelligence
env: []
---

# Market Reader: Kalshi (USD, CFTC-Regulated)

Read-only access to **Kalshi** prediction market odds. No API key required for reading.

Kalshi is a US CFTC-regulated prediction market. Binary YES/NO contracts, USD settlement, covers crypto, economics, politics, weather, sports.

## No API Key Needed

Kalshi's public market data is free to read. No authentication required.

## Usage

After running `/swarmy "question"`, compare the swarm consensus against Kalshi odds:

```python
from market_reader import MarketReader

reader = MarketReader()

# Search for markets
markets = reader.kalshi_search("bitcoin", limit=5)
for m in markets:
    print(f'{m["ticker"]}: {m["question"]}')
    print(f'  YES: {m["yes_price"]}  NO: {m["no_price"]}')

# Calculate edge against swarmy result
edge = reader.calculate_edge(swarm_pct=68, market_yes_price=0.54)
print(f'{edge["action"]} | Edge: {edge["edge_pct"]} | {edge["reasoning"]}')
```

## API Reference

Base URL: `https://api.elections.kalshi.com/trade-api/v2`

```
GET /markets?status=open&limit=100
Response: {"markets": [{"ticker": "...", "title": "...", "yes_bid_dollars": "0.54", ...}]}
```

## Edge Output Format

```
 ───────────────────────────────────────────────────────
  EDGE ANALYSIS: Swarmy vs Kalshi
 ───────────────────────────────────────────────────────
  Market:    BTCHIT120K-26APR30
  Question:  Will BTC hit $120K by April 30?
  Kalshi:    54% YES
  Swarmy:    68% YES
  Edge:      +14%
  Signal:    BUY YES (MEDIUM confidence)
 ───────────────────────────────────────────────────────
  This is NOT financial advice. Markets can lose 100%.
 ───────────────────────────────────────────────────────
```
