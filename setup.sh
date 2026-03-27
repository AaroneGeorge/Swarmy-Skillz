#!/bin/bash
# ─────────────────────────────────────────────────────────
#  Swarmy Skillz — Quick Setup Script
#  Sets up MiroFish + Swarm Intelligence locally
# ─────────────────────────────────────────────────────────

set -e

echo ""
echo "  ____                                        ____  _    _ _ _"
echo " / ___|_      ____ _ _ __ _ __ ___  _   _   / ___|| | _(_) | |____"
echo " \___ \ \ /\ / / _\` | '__| '_ \` _ \| | | |  \___ \| |/ / | | |_  /"
echo "  ___) \ V  V / (_| | |  | | | | | | |_| |   ___) |   <| | | |/ /"
echo " |____/ \_/\_/ \__,_|_|  |_| |_| |_|\__, |  |____/|_|\_\_|_|_/___|"
echo "                                     |___/"
echo " ───────────────────────────────────────────────────────────────────"
echo "  Setup Script — Let's get you up and running"
echo " ───────────────────────────────────────────────────────────────────"
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed."
    echo "  Install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi
echo "✓ Docker found"

# Check Docker running
if ! docker info &> /dev/null 2>&1; then
    echo "ERROR: Docker daemon is not running."
    echo "  Start Docker and try again."
    echo "  If permission denied: sudo usermod -aG docker \$USER && newgrp docker"
    exit 1
fi
echo "✓ Docker is running"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed."
    exit 1
fi
echo "✓ Python 3 found"

# Install Python deps
echo ""
echo "Installing Python dependencies..."
pip install requests python-dotenv --quiet 2>/dev/null || pip3 install requests python-dotenv --quiet 2>/dev/null || python3 -m pip install requests python-dotenv --quiet 2>/dev/null
echo "✓ Python dependencies installed"

# Setup .env
echo ""
if [ -f "backend/.env" ]; then
    echo "Found existing backend/.env"
    read -p "  Overwrite with fresh .env? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cp backend/.env.example backend/.env
        echo "  ✓ Copied .env.example → .env"
    fi
else
    cp backend/.env.example backend/.env
    echo "✓ Created backend/.env from example"
fi

# Collect API keys
echo ""
echo "─── API Key Setup ───"
echo ""
echo "You need 2 free API keys (no credit card required):"
echo ""

# NVIDIA
echo "1. NVIDIA API Key (for LLM inference)"
echo "   Get yours free: https://build.nvidia.com"
read -p "   Paste your NVIDIA_API_KEY: " nvidia_key
if [ -n "$nvidia_key" ]; then
    sed -i "s|^NVIDIA_API_KEY=.*|NVIDIA_API_KEY=${nvidia_key}|" backend/.env
    sed -i "s|^LLM_API_KEY=.*|LLM_API_KEY=${nvidia_key}|" backend/.env
    echo "   ✓ NVIDIA key saved (set for both NVIDIA_API_KEY and LLM_API_KEY)"
fi

echo ""

# Zep
echo "2. Zep Cloud API Key (for knowledge graph — 1000 free credits/month)"
echo "   Get yours free: https://app.getzep.com"
read -p "   Paste your ZEP_API_KEY: " zep_key
if [ -n "$zep_key" ]; then
    sed -i "s|^ZEP_API_KEY=.*|ZEP_API_KEY=$zep_key|" backend/.env
    echo "   ✓ Zep key saved"
fi

# Start MiroFish
echo ""
echo "─── Starting MiroFish ───"
echo ""
echo "Pulling MiroFish Docker image (first time takes ~2GB download)..."
cd backend
docker compose up -d
echo ""
echo "Waiting for MiroFish to start..."
sleep 15

# Health check
health=$(curl -s http://localhost:5001/health 2>/dev/null)
if echo "$health" | grep -q "ok"; then
    echo "✓ MiroFish is running and healthy!"
else
    echo "⚠ MiroFish may still be starting. Check with:"
    echo "  curl http://localhost:5001/health"
fi

cd ..

# Done
echo ""
echo "─────────────────────────────────────────────────────"
echo "  Setup Complete!"
echo "─────────────────────────────────────────────────────"
echo ""
echo "  Quick test:"
echo "    cd backend"
echo "    python3 swarmbet.py \"Will BTC hit \$120K?\" --verbose"
echo ""
echo "  Market data (no simulation needed):"
echo "    python3 -c \"from market_reader import MarketReader; r=MarketReader(); print(r.manifold_search('bitcoin', 3))\""
echo ""
echo "  Stop MiroFish:"
echo "    cd backend && docker compose down"
echo ""
