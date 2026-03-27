---
name: swarm-intelligence
description: "Swarmy Skillz — AI swarm intelligence prediction engine. Activate with /swarmy command."
version: 2.0.0
author: SwarmBet
metadata:
  filePattern: "**/*swarm*"
  bashPattern: "swarmy|mirofish|swarm"
dependencies: []
env:
  - MIROFISH_URL
  - NVIDIA_API_KEY
  - LLM_API_KEY
  - LLM_BASE_URL
  - LLM_MODEL_NAME
  - ZEP_API_KEY
---

# Swarm Intelligence — /swarmy

This skill is **command-driven**. It ONLY activates when the user types `/swarmy`. Do NOT run swarm analysis unprompted.

## Activation

When the user types `/swarmy`, FIRST display this ASCII banner:

```
  ____                                        ____  _    _ _ _
 / ___|_      ____ _ _ __ _ __ ___  _   _   / ___|| | _(_) | |____
 \___ \ \ /\ / / _` | '__| '_ ` _ \| | | |  \___ \| |/ / | | |_  /
  ___) \ V  V / (_| | |  | | | | | | |_| |   ___) |   <| | | |/ /
 |____/ \_/\_/ \__,_|_|  |_| |_| |_|\__, |  |____/|_|\_\_|_|_/___|
                                     |___/
 ───────────────────────────────────────────────────────────────────
  Swarm Intelligence Engine  |  Powered by MiroFish + OASIS
  AI agents debate so you don't have to.
 ───────────────────────────────────────────────────────────────────
```

Then process the user's question.

## Usage

```
/swarmy "Will BTC hit $120K by April 2026?"
/swarmy "Will the US go for a ceasefire with Iran before April?"
/swarmy "Who wins NBA MVP this season?"
/swarmy "Will the Fed cut rates in June?"
```

If the user types just `/swarmy` with no question, respond:

```
Usage: /swarmy "your prediction question here"

Examples:
  /swarmy "Will Bitcoin hit $120K by April?"
  /swarmy "Will the Fed cut rates in June?"
  /swarmy "Will Ethereum flip Solana in TVL?"
  /swarmy "Who wins the 2026 NBA Finals?"

What can I predict for you?
```

## Setup Requirements

Before first use, the user must have a running MiroFish instance. If any required env var is missing, display this setup guide:

```
Swarmy needs a MiroFish backend running locally via Docker.

Quick setup (run from project root):
  chmod +x setup.sh && ./setup.sh

Or manually:
  1. Install Docker         → https://docs.docker.com/get-docker/
  2. Get free NVIDIA API key → https://build.nvidia.com
  3. Get free Zep API key    → https://app.getzep.com (1000 credits/month)
  4. Configure:
       cd backend
       cp .env.example .env
       # Edit .env — set NVIDIA_API_KEY and ZEP_API_KEY
  5. Start MiroFish:
       docker compose up -d
       # Wait ~15 seconds
       curl http://localhost:5001/health
  6. Set env vars in your shell or .env:
       MIROFISH_URL=http://localhost:5001
       NVIDIA_API_KEY=nvapi-your-key
       LLM_API_KEY=nvapi-your-key  (same as NVIDIA)
       LLM_BASE_URL=https://integrate.api.nvidia.com/v1
       LLM_MODEL_NAME=meta/llama-3.3-70b-instruct
       ZEP_API_KEY=z_your-key

Docker image: ghcr.io/666ghj/mirofish:latest
Health check: GET /health on port 5001
```

## How It Works

Swarmy uses **MiroFish** — an open-source engine that simulates AI "digital humans" with unique personalities on a social media simulation (Twitter + Reddit). The agents debate, post, argue, react, and form emergent consensus. This is crowd behavior simulation, not single-AI reasoning.

The pipeline:
1. Parse the question and detect type (crypto/general)
2. Gather real-time seed data (CoinGecko prices, market data)
3. Generate an ontology (knowledge structure) from the seed data via LLM
4. Build a knowledge graph via Zep Cloud
5. Create agent profiles from graph entities (each agent has a unique personality)
6. Run OASIS swarm simulation — 120 rounds on Twitter + Reddit platforms
7. Agents post, react, argue, and form opinions
8. Generate analysis report from simulation results
9. Extract consensus prediction via LLM chat

Total runtime: **5-10 minutes per prediction**.

## MiroFish API Reference

All endpoints are relative to `MIROFISH_URL` (default: `http://localhost:5001`).

### Health
```
GET /health
Response: {"status": "ok", "service": "MiroFish Backend"}
```

### Graph (Ontology + Knowledge Graph)
```
POST /api/graph/ontology/generate
Content-Type: multipart/form-data
Fields: simulation_requirement (text), project_name (text), files (file upload)
Response: {"success": true, "data": {"project_id": "proj_xxx", "ontology": {...}}}

POST /api/graph/build
Body: {"project_id": "proj_xxx"}
Response: {"success": true, "data": {"task_id": "task_xxx", "graph_id": "mirofish_xxx"}}

GET /api/graph/task/{task_id}
Response: {"success": true, "data": {"status": "completed", "graph_id": "mirofish_xxx"}}
Note: graph_id may be null in the task status response. If so, retrieve it from the project list API below.

GET /api/graph/project/list
Response: {"success": true, "data": [{"project_id": "proj_xxx", "graph_id": "mirofish_xxx", ...}], "count": N}
Use this as a fallback to retrieve graph_id when the task status doesn't include it.
```

### Simulation
```
POST /api/simulation/create
Body: {"project_id": "proj_xxx", "graph_id": "mirofish_xxx"}
Response: {"success": true, "data": {"simulation_id": "sim_xxx"}}

POST /api/simulation/prepare
Body: {"simulation_id": "sim_xxx"}
Response: {"success": true, ...}
Note: Async — generates agent profiles from graph entities

POST /api/simulation/prepare/status
Body: {"simulation_id": "sim_xxx"}
Response: {"success": true, "data": {"status": "ready|preparing|not_started"}}

POST /api/simulation/start
Body: {"simulation_id": "sim_xxx"}
Response: {"success": true, "data": {"runner_status": "running", "process_pid": N}}

GET /api/simulation/{sim_id}/run-status
Response: {"success": true, "data": {
  "runner_status": "running|completed|failed",
  "twitter_completed": bool, "reddit_completed": bool,
  "twitter_current_round": N, "reddit_current_round": N,
  "total_rounds": 120, "total_actions_count": N
}}
Poll every 5 seconds until runner_status is "completed".
```

### Reports & Chat
```
POST /api/report/generate
Body: {"simulation_id": "sim_xxx"}
Response: {"success": true, "data": {"report_id": "report_xxx", "status": "generating"}}
Note: Prone to 429 rate limits — the client retries automatically with exponential backoff.

POST /api/report/generate/status
Body: {"simulation_id": "sim_xxx"}   ← NOTE: uses simulation_id, NOT report_id
Response: {"success": true, "data": {"status": "completed|generating|failed"}}

POST /api/report/chat
Body: {"simulation_id": "sim_xxx", "message": "What % of agents believe YES?"}
Response: {"success": true, "data": {"response": "Based on the analysis..."}}
Note: Response text may be in Chinese — this is normal for MiroFish.
```

## Step-by-Step Pipeline

When the user runs `/swarmy "question"`:

### Step 1 — Show banner + acknowledge
Display the ASCII banner. Tell the user:
> "Firing up the swarm... this takes 5-10 minutes. The agents need time to debate."

### Step 2 — Parse the question
```python
from swarmbet import parse_question
parsed = parse_question(question)
# Returns: {type: "crypto"|"general", coin_id, target, deadline, search_terms}
```

### Step 3 — Gather seed data
```python
from data_collector import DataCollector
collector = DataCollector()
if parsed["type"] == "crypto":
    seed_markdown = collector.collect_crypto_seed(coin_id=parsed["coin_id"], question=question)
else:
    seed_markdown = collector.collect_general_seed(question=question, search_terms=parsed["search_terms"])
```

### Step 4 — Run MiroFish simulation
```python
from mirofish_client import MiroFishClient
client = MiroFishClient()  # reads MIROFISH_URL from env

result = client.run_full_simulation(
    name=project_name,
    description=question,
    seed_content=seed_markdown,
    verbose=True,
)
# Returns: {
#   "project_id": str,
#   "simulation_id": str,
#   "status": dict,       # final run status
#   "report": dict,       # generated report
#   "prediction": dict,   # chat response with consensus
#   "error": str | None,  # set if pipeline failed
# }
```

This internally calls: upload_text → graph/build → poll task → simulation/create → prepare → poll prep → start → poll run → generate_report → chat

**Important notes:**
- `run_full_simulation()` automatically retries on 429 rate limit errors (exponential backoff)
- If `graph_id` is not returned by the task status API, it falls back to the project list API
- The method returns an `"error"` key if any step fails — always check `result.get("error")` before accessing other keys

### Step 5 — Extract consensus
```python
from swarmbet import _extract_consensus

# Handle both response formats the API may return
prediction_raw = result.get("prediction", {})
prediction_text = (
    prediction_raw.get("response")
    or (prediction_raw.get("data", {}) or {}).get("response")
    or str(prediction_raw)
)
consensus = _extract_consensus(prediction_text)
# Returns: {pct: 40, direction: "NO", confidence: "MEDIUM", insights: [...]}
```

**Note:** MiroFish responses may contain Chinese text — this is normal. The `_extract_consensus()` parser handles both English and Chinese keywords for direction, confidence, and insight extraction.

### Step 6 — Display results

ALWAYS display results in this format:

```
 ───────────────────────────────────────────────────────
  SWARMY PREDICTION RESULT
 ───────────────────────────────────────────────────────

  Question:    Will BTC hit $120K by April 2026?
  Consensus:   40% YES
  Direction:   NO (majority skeptical)
  Confidence:  MEDIUM

  Key Insights:
    1. Agents noted current price ($70K) requires 70% rally
    2. Mixed sentiment on ETF inflow sustainability
    3. Macro uncertainty dampened bullish momentum

  Simulation:  120 rounds | 92 agent actions
  Platforms:   Twitter + Reddit
  Duration:    ~7 minutes

 ───────────────────────────────────────────────────────
  Swarm consensus != truth. This predicts crowd
  behavior, not guaranteed outcomes.
 ───────────────────────────────────────────────────────
```

### Step 7 — Offer market integrations

After showing results, automatically search prediction markets for matching odds:

```python
from market_reader import MarketReader
reader = MarketReader()

# Search all markets for the question
markets = reader.search_all(question, limit=5)
if markets:
    print("Prediction Market Odds:")
    for m in markets:
        edge = reader.calculate_edge(consensus["pct"], m["yes_price"])
        print(f'  [{m["source"]}] {m["question"][:50]}')
        print(f'    Market: {m["yes_price"]:.0%} YES | Edge: {edge["edge_pct"]} | {edge["action"]}')
```

Display format:
```
 ───────────────────────────────────────────────────────
  MARKET EDGE ANALYSIS
 ───────────────────────────────────────────────────────
  [kalshi]    BTC above $120K by April?
              Market: 54% YES | Swarmy: 68% | Edge: +14% → BUY YES
  [manifold]  Bitcoin hits $120K before May?
              Market: 48% YES | Swarmy: 68% | Edge: +20% → STRONG BUY YES
  [polymarket] BTC $120K Q1 2026?
              Market: 51% YES | Swarmy: 68% | Edge: +17% → STRONG BUY YES
 ───────────────────────────────────────────────────────
  Supported markets (no API keys needed for reading):
    Polymarket  — polymarket.com (crypto-settled)
    Kalshi      — kalshi.com (USD, CFTC-regulated)
    Manifold    — manifold.markets (play money)
    More markets coming soon...
 ───────────────────────────────────────────────────────
```

## Timing Expectations

| Step | Duration |
|------|----------|
| Parse question + gather seed data | ~5 seconds |
| Generate ontology (LLM call) | ~30-90 seconds |
| Build knowledge graph (Zep) | ~30-60 seconds |
| Prepare agent profiles | ~60-120 seconds |
| Run swarm simulation (120 rounds x 2 platforms) | ~3-7 minutes |
| Generate report + extract prediction | ~30-60 seconds |
| **Total** | **~5-10 minutes per prediction** |

Warn users upfront: "The swarm needs 5-10 minutes to debate. Grab a coffee."

## Error Handling

- **MiroFish unreachable**: Check `MIROFISH_URL`. Make sure Docker is running and the container is up: `docker compose up -d`.
- **Graph build fails with ZEP error**: `ZEP_API_KEY` is required (not optional). Sign up free at https://app.getzep.com.
- **graph_id is None**: The task status API sometimes doesn't return `graph_id`. The client automatically falls back to the project list API (`GET /api/graph/project/list`) to retrieve it.
- **LLM call hangs**: Some models can be unresponsive. The default `meta/llama-3.3-70b-instruct` is recommended.
- **429 Too Many Requests**: Report generation and chat endpoints are rate-limited. The client retries automatically with exponential backoff (5s, 10s, 20s). If it still fails, wait a minute and retry.
- **Simulation stuck / prepare stays at not_started**: Usually caused by a null `graph_id` cascading into simulation creation. The fix above should prevent this. If it still happens, check MiroFish logs: `docker compose logs mirofish`.
- **Poor seed data**: If consensus is 50/50 with LOW confidence, the seed data was insufficient. The collector now generates enriched context for general questions even without a news API key. User can also provide additional context with `--context`.
- **Chinese text in responses**: MiroFish is a Chinese-language backend. Chat responses and logs may contain Chinese text. The consensus extractor handles both English and Chinese.
- **CoinGecko rate limit**: Wait 60 seconds or set `COINGECKO_API_KEY` for higher limits.
- **Polymarket/Kalshi unreachable**: These APIs may be blocked by DNS in certain regions (e.g., India). The client logs a warning and returns empty results — Manifold will still work. Consider using a VPN if you need all three markets.
- **News API 401**: If `NEWS_API_KEY` returns 401, the key may be invalid or expired. Get a new one at https://newsapi.org. Without it, the collector generates synthetic context from the question itself.

## Limitations (Be Honest With Users)

1. Swarm consensus predicts **crowd behavior**, not outcomes.
2. Quality depends entirely on seed data — garbage in, garbage out. Without a News API key, general questions get synthetic context only.
3. Simulations take 5-10 minutes — not suitable for time-sensitive decisions.
4. NVIDIA free tier has rate limits — heavy use may need a higher-tier key (free tier is generous). Report generation is particularly prone to 429 errors.
5. Zep free tier has 1000 credits/month — each simulation uses ~1-3 credits.
6. MiroFish is relatively new software — expect occasional instability (null graph_ids, stuck preparations).
7. Results and MiroFish logs/chat responses may contain Chinese text — this is normal. The parser handles it.
8. Polymarket and Kalshi APIs may be unreachable from certain regions (e.g., India) due to DNS/geo-blocking. Only Manifold is globally accessible.
9. Market search uses client-side filtering — niche topics may return zero results even when markets exist.
