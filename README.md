```
  ____                                        ____  _    _ _ _
 / ___|_      ____ _ _ __ _ __ ___  _   _   / ___|| | _(_) | |____
 \___ \ \ /\ / / _` | '__| '_ ` _ \| | | |  \___ \| |/ / | | |_  /
  ___) \ V  V / (_| | |  | | | | | | |_| |   ___) |   <| | | |/ /
 |____/ \_/\_/ \__,_|_|  |_| |_| |_|\__, |  |____/|_|\_\_|_|_/___|
                                     |___/
```

# Swarmy Skillz

**AI swarm intelligence for prediction markets.** Thousands of AI agents with unique personalities debate any question on simulated Twitter + Reddit, then form emergent crowd consensus. Compare that consensus against real prediction market odds to find betting edges.

Built with [MiroFish](https://github.com/666ghj/MiroFish) + [OASIS](https://github.com/camel-ai/oasis) for the Solana Agentic Hackathon.

## What It Does

1. **`/swarmy "Will BTC hit $120K by April?"`** — Runs a swarm simulation with AI agents
2. Agents debate for 120 rounds across Twitter + Reddit
3. Returns crowd consensus (e.g. "40% YES, MEDIUM confidence")
4. Automatically compares against live Polymarket, Kalshi, and Manifold odds
5. Calculates betting edge: `Swarm 68% - Market 54% = +14% edge → BUY YES`

## Quick Start

```bash
# Install via skills.sh (works with Claude Code, Cursor, Cline, Copilot, 20+ agents)
npx skilladd AaroneGeorge/Swarmy-Skillz

# Or manual install
git clone https://github.com/AaroneGeorge/Swarmy-Skillz.git
cd Swarmy-Skillz

# One-command setup (gets API keys, starts Docker)
chmod +x setup.sh && ./setup.sh

# Install skills into Claude Code
cp -r skills/* ~/.claude/skills/

# Use it — in Claude Code, type:
/swarmy "Will the Fed cut rates in June?"
```

## What You Need

| Requirement | Free? | Where to Get |
|-------------|:-----:|-------------|
| Docker | Yes | https://docs.docker.com/get-docker/ |
| NVIDIA API Key | Yes | https://build.nvidia.com |
| Zep API Key | Yes | https://app.getzep.com |
| Python 3.11+ | Yes | Pre-installed on most systems |

**No API keys needed** for reading prediction market odds (Polymarket, Kalshi, Manifold are free to read).

## Manual Setup

If you prefer to set things up yourself:

```bash
# 1. Configure environment
cd backend
cp .env.example .env
# Edit .env — set NVIDIA_API_KEY and ZEP_API_KEY

# 2. Start MiroFish
docker compose up -d
# Wait ~15 seconds
curl http://localhost:5001/health
# Expected: {"status": "ok"}

# 3. Test it
python3 swarmbet.py "Will Bitcoin hit $120K by April 2026?" --verbose

# 4. Test market reader (instant, no simulation)
python3 -c "
from market_reader import MarketReader
r = MarketReader()
markets = r.search_all('bitcoin', limit=5)
for m in markets:
    print(f'[{m[\"source\"]}] {m[\"question\"][:50]} — YES: {m[\"yes_price\"]}')
"
```

## Skills

| Skill | What It Does | API Key? |
|-------|-------------|:--------:|
| **swarm-intelligence** | Core `/swarmy` command — runs MiroFish swarm simulation | NVIDIA + Zep (free) |
| **market-polymarket** | Read Polymarket odds, calculate edge vs swarmy | None |
| **market-kalshi** | Read Kalshi odds (USD, CFTC-regulated) | None |
| **market-manifold** | Read Manifold Markets odds | None |
| *More markets* | Coming soon (Drift BET, Pump Fun, etc.) | — |

## How the Swarm Works

```
Question → Parse → Gather Seed Data (CoinGecko, news)
    → Generate Ontology (LLM) → Build Knowledge Graph (Zep)
    → Create Agent Profiles (unique personalities)
    → Run OASIS Simulation (120 rounds, Twitter + Reddit)
    → Agents post, argue, react, form opinions
    → Generate Report → Extract Consensus
    → Compare vs Prediction Market Odds → Edge Signal
```

Each simulation creates **real AI personas** from the knowledge graph. For "Who wins IPL 2026?", it created 22 agents including cricket players (Rohit Sharma, KL Rahul), analysts, and fans who debated across 471 actions.

## Example Output

```
 ───────────────────────────────────────────────────────
  SWARMY PREDICTION RESULT
 ───────────────────────────────────────────────────────
  Question:    Will Bitcoin hit $120K by April 2026?
  Consensus:   40% YES
  Direction:   NO (majority skeptical)
  Confidence:  MEDIUM
  Simulation:  120 rounds | 92 agent actions

 ───────────────────────────────────────────────────────
  MARKET EDGE ANALYSIS
 ───────────────────────────────────────────────────────
  [kalshi]     BTC above $120K?   Market: 54% | Edge: -14% → BUY NO
  [manifold]   Bitcoin $120K?     Market: 48% | Edge: -8%  → NO EDGE
  [polymarket] BTC 120K Q1?       Market: 51% | Edge: -11% → BUY NO
 ───────────────────────────────────────────────────────
```

## Architecture

```
repo/
├── setup.sh                          # One-command setup
├── skills/
│   ├── swarm-intelligence/SKILL.md   # Core /swarmy command
│   ├── market-polymarket/SKILL.md    # Polymarket reader
│   ├── market-kalshi/SKILL.md        # Kalshi reader
│   ├── market-manifold/SKILL.md      # Manifold reader
│   └── (more markets coming soon)
├── backend/
│   ├── docker-compose.yml            # MiroFish container
│   ├── .env.example                  # Template env vars
│   ├── swarmbet.py                   # Pipeline orchestrator
│   ├── mirofish_client.py            # MiroFish API client
│   ├── data_collector.py             # CoinGecko + news collector
│   └── market_reader.py              # Prediction market reader
├── TESTING.md                        # Full test guide
└── DISTRIBUTION.md                   # How to publish skills
```

## Prediction Markets Supported

| Market | Type | Settlement | Read API | Key Needed? |
|--------|------|-----------|----------|:-----------:|
| Polymarket | Crypto | USDC (Polygon) | gamma-api / clob | No |
| Kalshi | Regulated | USD (CFTC) | REST API v2 | No |
| Manifold | Play money | Mana | REST API v0 | No |

## Limitations

- Swarm consensus predicts **crowd behavior**, not guaranteed outcomes
- Simulations take **5-10 minutes** — not for time-sensitive decisions
- Quality depends on seed data — garbage in, garbage out
- NVIDIA free tier has rate limits
- Zep free tier: 1000 credits/month (~300-500 simulations)
- This is NOT financial advice

## License

MIT