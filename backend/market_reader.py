"""
Prediction Market Reader — Read-only access to prediction market odds.

Supports: Polymarket, Kalshi, Manifold Markets
No API keys required for read access.
"""

import requests
from typing import Optional


class MarketReader:
    """Read-only client for prediction market data."""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    # ─── Polymarket ───────────────────────────────────────────────

    def polymarket_search(self, query: str, limit: int = 5) -> list[dict]:
        """Search Polymarket for active markets.

        No API key required. Uses the Gamma API.
        Fallback to CLOB API if Gamma is unavailable.
        """
        # Try Gamma API first
        for base in ["https://gamma-api.polymarket.com", "https://clob.polymarket.com"]:
            try:
                if "gamma" in base:
                    resp = self.session.get(
                        f"{base}/markets",
                        params={"closed": "false", "limit": limit, "order": "volume", "ascending": "false"},
                        timeout=self.timeout,
                    )
                    if resp.ok:
                        markets = resp.json()
                        # Filter by query
                        if query:
                            q = query.lower()
                            markets = [m for m in markets if q in m.get("question", "").lower()]
                        return [self._normalize_polymarket(m) for m in markets[:limit]]
                else:
                    resp = self.session.get(
                        f"{base}/markets",
                        params={"next_cursor": "MA==", "limit": 100},
                        timeout=self.timeout,
                    )
                    if resp.ok:
                        data = resp.json()
                        markets = data.get("data", data) if isinstance(data, dict) else data
                        if query:
                            q = query.lower()
                            markets = [m for m in markets if q in m.get("question", "").lower()]
                        return [self._normalize_polymarket_clob(m) for m in markets[:limit]]
            except (requests.RequestException, ValueError):
                continue
        return []

    def _normalize_polymarket(self, m: dict) -> dict:
        outcomes = m.get("outcomes", "")
        prices = m.get("outcomePrices", "")
        if isinstance(outcomes, str):
            outcomes = [o.strip('" ') for o in outcomes.split(",")]
        if isinstance(prices, str):
            prices = [float(p.strip('" ')) for p in prices.split(",")]

        yes_price = prices[0] if len(prices) > 0 else None
        no_price = prices[1] if len(prices) > 1 else None

        return {
            "source": "polymarket",
            "question": m.get("question", ""),
            "url": f"https://polymarket.com/event/{m.get('slug', '')}",
            "yes_price": yes_price,
            "no_price": no_price,
            "volume": m.get("volume"),
            "active": m.get("active", True),
        }

    def _normalize_polymarket_clob(self, m: dict) -> dict:
        tokens = m.get("tokens", [])
        yes_price = None
        no_price = None
        for t in tokens:
            if t.get("outcome") == "Yes":
                yes_price = float(t.get("price", 0))
            elif t.get("outcome") == "No":
                no_price = float(t.get("price", 0))
        return {
            "source": "polymarket",
            "question": m.get("question", ""),
            "url": f"https://polymarket.com/event/{m.get('condition_id', '')}",
            "yes_price": yes_price,
            "no_price": no_price,
            "volume": None,
            "active": m.get("active", True),
        }

    # ─── Kalshi ───────────────────────────────────────────────────

    def kalshi_search(self, query: str, limit: int = 5) -> list[dict]:
        """Search Kalshi for active markets.

        No API key required for read access.
        """
        try:
            resp = self.session.get(
                "https://api.elections.kalshi.com/trade-api/v2/markets",
                params={"limit": 100, "status": "open"},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            markets = resp.json().get("markets", [])
            if query:
                q = query.lower()
                markets = [m for m in markets if q in m.get("title", "").lower()]
            return [self._normalize_kalshi(m) for m in markets[:limit]]
        except (requests.RequestException, ValueError):
            return []

    def _normalize_kalshi(self, m: dict) -> dict:
        yes_bid = m.get("yes_bid_dollars") or m.get("yes_bid")
        yes_ask = m.get("yes_ask_dollars") or m.get("yes_ask")
        no_bid = m.get("no_bid_dollars") or m.get("no_bid")
        no_ask = m.get("no_ask_dollars") or m.get("no_ask")

        # Convert to float, handling cent values
        def to_float(v):
            if v is None:
                return None
            v = float(v)
            if v > 1:  # cents, convert to dollars
                v = v / 100
            return round(v, 4)

        yes_price = to_float(yes_bid)
        no_price = to_float(no_bid)

        return {
            "source": "kalshi",
            "question": m.get("title", ""),
            "ticker": m.get("ticker", ""),
            "url": f"https://kalshi.com/markets/{m.get('ticker', '')}",
            "yes_price": yes_price,
            "no_price": no_price,
            "yes_bid": to_float(yes_bid),
            "yes_ask": to_float(yes_ask),
            "volume": m.get("volume_fp") or m.get("volume"),
            "active": m.get("status") == "active",
        }

    # ─── Manifold Markets ─────────────────────────────────────────

    def manifold_search(self, query: str, limit: int = 5) -> list[dict]:
        """Search Manifold Markets for active markets.

        No API key required.
        """
        try:
            resp = self.session.get(
                "https://api.manifold.markets/v0/search-markets",
                params={"term": query, "limit": limit, "filter": "open", "sort": "liquidity"},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            markets = resp.json()
            return [self._normalize_manifold(m) for m in markets[:limit]]
        except (requests.RequestException, ValueError):
            return []

    def _normalize_manifold(self, m: dict) -> dict:
        prob = m.get("probability")
        return {
            "source": "manifold",
            "question": m.get("question", ""),
            "url": m.get("url", ""),
            "yes_price": round(prob, 4) if prob is not None else None,
            "no_price": round(1 - prob, 4) if prob is not None else None,
            "volume": m.get("volume"),
            "liquidity": m.get("totalLiquidity"),
            "active": not m.get("isResolved", False),
        }

    # ─── Unified Search ──────────────────────────────────────────

    def search_all(self, query: str, limit: int = 5) -> list[dict]:
        """Search all supported prediction markets.

        Returns normalized results from all sources.
        """
        results = []
        for search_fn in [self.polymarket_search, self.kalshi_search, self.manifold_search]:
            try:
                results.extend(search_fn(query, limit=limit))
            except Exception:
                continue
        # Sort by volume (descending), with None last
        results.sort(key=lambda x: float(x.get("volume") or 0), reverse=True)
        return results[:limit * 3]

    # ─── Edge Calculation ─────────────────────────────────────────

    @staticmethod
    def calculate_edge(swarm_pct: float, market_yes_price: float) -> dict:
        """Calculate betting edge: swarm consensus vs market odds.

        Args:
            swarm_pct: Swarm consensus percentage (0-100, e.g. 68)
            market_yes_price: Market YES price (0-1, e.g. 0.54)

        Returns: {edge, action, reasoning, strength}
        """
        swarm_prob = swarm_pct / 100.0
        edge = swarm_prob - market_yes_price

        if edge > 0.15:
            action = "STRONG BUY YES"
            strength = "HIGH"
        elif edge > 0.10:
            action = "BUY YES"
            strength = "MEDIUM"
        elif edge < -0.15:
            action = "STRONG BUY NO"
            strength = "HIGH"
        elif edge < -0.10:
            action = "BUY NO"
            strength = "MEDIUM"
        else:
            action = "NO EDGE"
            strength = "LOW"

        reasoning = (
            f"Swarm: {swarm_pct:.0f}% YES | Market: {market_yes_price:.0%} YES | "
            f"Edge: {edge:+.1%}"
        )

        return {
            "edge": round(edge, 4),
            "edge_pct": f"{edge:+.1%}",
            "action": action,
            "strength": strength,
            "reasoning": reasoning,
        }
