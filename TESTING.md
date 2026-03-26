# Testing Guide

## Prerequisites

- Python 3.11+
- Docker (user must be in `docker` group — see Troubleshooting)
- `pip install requests`

## 1. Setup

### Get API Keys (Free)

| Key | Where | Required |
|-----|-------|----------|
| `NVIDIA_API_KEY` | https://build.nvidia.com (sign up free) | Yes |
| `ZEP_API_KEY` | https://app.getzep.com (sign up free, 1000 credits/month) | Yes |
| `COINGECKO_API_KEY` | https://www.coingecko.com/en/api (optional, increases rate limit) | No |

### Configure .env

```bash
cd backend
cp .env.example .env
# Edit .env — set NVIDIA_API_KEY and ZEP_API_KEY
```

### Start MiroFish

```bash
cd backend
docker compose up -d
# First run pulls the image (~2GB) — takes a few minutes

# Wait ~15 seconds, then verify health
curl http://localhost:5001/health
# Expected: {"service": "MiroFish Backend", "status": "ok"}
```

## 2. Unit Tests (No MiroFish Required)

### Test Question Parser

```bash
cd backend
python -c "
from swarmbet import parse_question

# Crypto question
r = parse_question('Will BTC hit \$120K by April 2026?')
assert r['type'] == 'crypto'
assert r['coin_id'] == 'bitcoin'
assert r['target'] == '\$120K'
print('✓ Crypto question parsed:', r)

# General question
r = parse_question('Will the Fed cut rates in June?')
assert r['type'] == 'general'
assert r['coin_id'] is None
print('✓ General question parsed:', r)

# Multiple crypto keywords
r = parse_question('Will Ethereum flip Solana in TVL?')
assert r['type'] == 'crypto'
print('✓ Multi-keyword question parsed:', r)

print('\nAll parser tests passed.')
"
```

### Test Consensus Extraction

```bash
cd backend
python -c "
from swarmbet import _extract_consensus

# High confidence bullish
r = _extract_consensus('68% of agents believe YES. Strong consensus driven by ETF data.')
assert r['pct'] == 68
assert r['direction'] == 'YES'
assert r['confidence'] == 'HIGH'
print(f'✓ Bullish: {r[\"pct\"]}% {r[\"direction\"]} ({r[\"confidence\"]})')

# Low confidence split
r = _extract_consensus('The agents are divided, with 48% leaning YES. Unclear outcome.')
assert r['pct'] == 48
assert r['direction'] == 'NO'
assert r['confidence'] == 'LOW'
print(f'✓ Bearish: {r[\"pct\"]}% {r[\"direction\"]} ({r[\"confidence\"]})')

# Medium confidence
r = _extract_consensus('55% consensus for YES. Majority shifted due to recent data.')
assert r['pct'] == 55
assert r['direction'] == 'YES'
assert r['confidence'] == 'MEDIUM'
print(f'✓ Medium: {r[\"pct\"]}% {r[\"direction\"]} ({r[\"confidence\"]})')

print('\nAll consensus extraction tests passed.')
"
```

### Test Data Collector (CoinGecko — Free, No Key)

```bash
cd backend
python -c "
from data_collector import DataCollector

dc = DataCollector()

# Test price fetch
data = dc.get_crypto_price('bitcoin', days=7)
assert data['current_price'] is not None
assert data['current_price'] > 0
print(f'✓ BTC price: \${data[\"current_price\"]:,.2f}')
print(f'  7d range: \${data[\"low_30d\"]:,.2f} - \${data[\"high_30d\"]:,.2f}')

# Test coin info
info = dc.get_crypto_info('bitcoin')
assert info['name'] == 'Bitcoin'
print(f'✓ BTC market cap: \${info[\"market_cap\"]:,.0f}')

# Test markdown formatting
md = dc.format_as_markdown(
    question='Will BTC hit \$120K?',
    crypto_data=data,
    crypto_info=info,
)
assert '# Seed Data' in md
assert 'Bitcoin' in md
print(f'✓ Markdown generated ({len(md)} chars)')

print('\nAll data collector tests passed.')
"
```

### Test MiroFish Client (Mock — No Server)

```bash
cd backend
python -c "
from mirofish_client import MiroFishClient

# Test client initialization
client = MiroFishClient('http://localhost:5001')
assert client.base_url == 'http://localhost:5001'

# Test URL construction
assert client._url('/api/graph/project/list') == 'http://localhost:5001/api/graph/project/list'

# Test with trailing slash
client2 = MiroFishClient('http://localhost:5001/')
assert client2._url('/api/test') == 'http://localhost:5001/api/test'

print('✓ MiroFish client initialization works')
print('✓ URL construction works')
print('\nAll mock tests passed.')
"
```

### Test Edge Calculation Logic

```bash
cd backend
python -c "
# Drift BET edge calculation
swarm_consensus = 0.68
drift_yes_price = 0.54
edge = swarm_consensus - drift_yes_price

if edge > 0.10:
    action = 'BUY YES'
elif edge < -0.10:
    action = 'BUY NO'
else:
    action = 'NO EDGE'

print(f'Swarm: {swarm_consensus:.0%} | Market: {drift_yes_price:.0%} | Edge: {edge:+.0%} | Action: {action}')
assert action == 'BUY YES'
assert abs(edge - 0.14) < 0.001
print('✓ Edge calculation correct')

# No edge scenario
swarm_consensus = 0.52
drift_yes_price = 0.54
edge = swarm_consensus - drift_yes_price
action = 'BUY YES' if edge > 0.10 else ('BUY NO' if edge < -0.10 else 'NO EDGE')
assert action == 'NO EDGE'
print(f'✓ No edge: {edge:+.0%} → {action}')

print('\nAll edge tests passed.')
"
```

## 3. Live Tests (MiroFish Docker Required)

### Test MiroFish Connection

```bash
cd backend
python -c "
from mirofish_client import MiroFishClient

client = MiroFishClient()

# Health check
h = client.health()
assert h['status'] == 'ok'
print(f'✓ Health: {h}')

# List projects
projects = client.list_projects()
assert projects['success'] == True
print(f'✓ Project list: {projects[\"count\"]} projects')

print('\nAll connection tests passed.')
"
```

### Test Full Pipeline (5-10 minutes)

This runs the entire flow: question parsing, CoinGecko data collection, MiroFish ontology generation, Zep graph build, agent simulation (120 rounds on Twitter + Reddit), report generation, and prediction extraction.

```bash
cd backend
python swarmbet.py "Will Bitcoin hit \$120K by April 2026?" --verbose
```

Expected output:
```
[1/5] Parsing question...
[2/5] Collecting seed data (type: crypto)...
[3/5] Running MiroFish swarm simulation (this takes 3-7 minutes)...
  → Uploading seed data & generating ontology...
  → Project created: proj_xxxxx
  → Building knowledge graph...
  → Graph built: mirofish_xxxxx
  → Creating simulation...
  → Preparing agent profiles...
  → Starting swarm simulation...
  → Polling simulation status...
  → Generating report...
  → Extracting prediction via chat...
[4/5] Extracting prediction from swarm output...
[5/5] Building result...

Result: 40% YES (confidence: MEDIUM)
```

### Test with JSON Output

```bash
cd backend
python swarmbet.py "Will the Fed cut rates in June 2026?" --verbose --json
```

## 4. MiroFish API Endpoints (Manual Testing)

The MiroFish API is organized under three blueprints:

| Blueprint | Prefix | Purpose |
|-----------|--------|---------|
| Graph | `/api/graph/` | Projects, ontology, knowledge graph |
| Simulation | `/api/simulation/` | Create, prepare, run, monitor simulations |
| Report | `/api/report/` | Generate reports, chat with agents |

### Key endpoints

```bash
# Health
curl http://localhost:5001/health

# List projects
curl http://localhost:5001/api/graph/project/list

# List simulations
curl http://localhost:5001/api/simulation/list

# Check simulation run status
curl http://localhost:5001/api/simulation/<sim_id>/run-status

# List reports
curl http://localhost:5001/api/report/list
```

## 5. End-to-End Checklist

Run in order:

- [ ] `.env` has `NVIDIA_API_KEY` and `ZEP_API_KEY` set
- [ ] `docker compose up -d` — MiroFish starts without errors
- [ ] `curl localhost:5001/health` — returns `{"status": "ok"}`
- [ ] `docker compose logs mirofish | tail -5` — no config errors
- [ ] Unit tests pass (Section 2 above)
- [ ] MiroFish connection test passes (Section 3)
- [ ] `python swarmbet.py "Test question" --verbose` — full pipeline completes
- [ ] Output contains consensus %, confidence level
- [ ] Edge calculation tests pass
- [ ] `docker compose down` — clean shutdown

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `permission denied` on docker socket | User not in `docker` group | `sudo usermod -aG docker $USER` then log out/in. Workaround: prefix commands with `sg docker -c "..."` |
| MiroFish restart loop with `ZEP_API_KEY 未配置` | Missing Zep API key | Sign up at https://app.getzep.com (free) and add key to `.env` |
| Health returns 404 on `/api/health` | Wrong health URL | Use `/health` (not `/api/health`) |
| LLM call hangs (>3 min with no response) | Model unresponsive | Ensure `LLM_MODEL_NAME=meta/llama-3.3-70b-instruct` in `.env` (default, most reliable) |
| `ConnectionRefusedError` | MiroFish not running | `docker compose up -d` and wait 15s |
| Graph build returns 500 | Zep key missing or invalid | Verify `ZEP_API_KEY` is set and valid |
| Simulation stuck polling | `runner_status` field mismatch | Ensure you're using the latest `mirofish_client.py` |
| CoinGecko 429 error | Rate limited | Wait 60s, or set `COINGECKO_API_KEY` in `.env` |
| `TimeoutError` from poll | Simulation >10min | Check that `LLM_BASE_URL` is reachable: `curl https://integrate.api.nvidia.com/v1/models -H "Authorization: Bearer $NVIDIA_API_KEY"` |
| Docker image pull slow | Large image (~2GB) | First pull takes time; subsequent runs use cache |
| `xdg-open ENOENT` in logs | Container has no display | Harmless frontend warning, ignore it |

## 7. Architecture Reference

```
swarmbet.py (CLI entry point)
  ├── parse_question()          — classify question type + extract crypto info
  ├── DataCollector             — fetch live data from CoinGecko
  ├── MiroFishClient            — orchestrate MiroFish API calls
  │     ├── /api/graph/ontology/generate   — upload seed data, LLM generates ontology
  │     ├── /api/graph/build               — build knowledge graph via Zep
  │     ├── /api/simulation/create         — create simulation
  │     ├── /api/simulation/prepare        — generate agent profiles from graph entities
  │     ├── /api/simulation/start          — run OASIS swarm (Twitter + Reddit)
  │     ├── /api/simulation/<id>/run-status — poll until completed
  │     ├── /api/report/generate           — generate analysis report
  │     └── /api/report/chat               — extract prediction via LLM chat
  └── _extract_consensus()      — parse consensus %, direction, confidence
```
