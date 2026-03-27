"""
Prediction Market Reader — Read-only access to prediction market odds.

Supports: Polymarket, Kalshi, Manifold Markets
No API keys required for read access.
"""

import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


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

        Fetches a large batch and filters client-side since the Gamma API
        doesn't support text search — only sorting by volume.
        """
        # Fetch enough markets for meaningful client-side filtering
        fetch_limit = max(100, limit * 20)

        # Try Gamma API first
        for base in ["https://gamma-api.polymarket.com", "https://clob.polymarket.com"]:
            try:
                if "gamma" in base:
                    resp = self.session.get(
                        f"{base}/markets",
                        params={"closed": "false", "limit": fetch_limit, "order": "volume", "ascending": "false"},
                        timeout=self.timeout,
                    )
                    if resp.ok:
                        markets = resp.json()
                        if query:
                            markets = self._fuzzy_filter(markets, query, key="question")
                        return [self._normalize_polymarket(m) for m in markets[:limit]]
                else:
                    resp = self.session.get(
                        f"{base}/markets",
                        params={"next_cursor": "MA==", "limit": fetch_limit},
                        timeout=self.timeout,
                    )
                    if resp.ok:
                        data = resp.json()
                        markets = data.get("data", data) if isinstance(data, dict) else data
                        if query:
                            markets = self._fuzzy_filter(markets, query, key="question")
                        return [self._normalize_polymarket_clob(m) for m in markets[:limit]]
            except requests.exceptions.ConnectionError as e:
                logger.warning("Polymarket (%s) unreachable — DNS or network issue: %s", base, e)
                continue
            except (requests.RequestException, ValueError) as e:
                logger.warning("Polymarket (%s) request failed: %s", base, e)
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

        No API key required for read access. Uses the /events endpoint
        (with nested markets) since the /markets endpoint returns MVE
        multi-leg markets with concatenated titles that are unsearchable.
        Paginates through events and filters by query words.
        """
        try:
            all_markets = []
            cursor = None
            # Paginate through events (up to 100 events = ~10 pages)
            for _ in range(10):
                params = {"limit": 10, "status": "open", "with_nested_markets": "true"}
                if cursor:
                    params["cursor"] = cursor
                resp = self.session.get(
                    "https://api.elections.kalshi.com/trade-api/v2/events",
                    params=params,
                    timeout=self.timeout,
                )
                resp.raise_for_status()
                data = resp.json()
                events = data.get("events", [])
                cursor = data.get("cursor")

                for event in events:
                    event_title = event.get("title", "")
                    for mkt in event.get("markets", []):
                        # Use event title as the readable question (market titles are often truncated)
                        mkt["_event_title"] = event_title
                        all_markets.append(mkt)

                if not cursor or not events:
                    break

            if query:
                all_markets = self._fuzzy_filter(all_markets, query, key="_event_title")

            return [self._normalize_kalshi(m) for m in all_markets[:limit]]
        except requests.exceptions.ConnectionError as e:
            logger.warning("Kalshi unreachable — DNS or network issue: %s", e)
            return []
        except (requests.RequestException, ValueError) as e:
            logger.warning("Kalshi request failed: %s", e)
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

        # Use event title if available (more readable than market title)
        question = m.get("_event_title") or m.get("title", "")

        return {
            "source": "kalshi",
            "question": question,
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

        No API key required. Manifold has a proper text search endpoint.
        """
        try:
            resp = self.session.get(
                "https://api.manifold.markets/v0/search-markets",
                params={"term": query, "limit": limit, "filter": "open", "sort": "liquidity"},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            markets = resp.json()
            normalized = [self._normalize_manifold(m) for m in markets[:limit]]
            # Filter out markets where we couldn't determine a price
            return [m for m in normalized if m["yes_price"] is not None]
        except requests.exceptions.ConnectionError as e:
            logger.warning("Manifold unreachable — DNS or network issue: %s", e)
            return []
        except (requests.RequestException, ValueError) as e:
            logger.warning("Manifold request failed: %s", e)
            return []

    def _normalize_manifold(self, m: dict) -> dict:
        # probability is the primary field, but some markets use other fields
        prob = m.get("probability")
        if prob is None:
            # Fallback: try to derive from pool YES/NO shares
            pool = m.get("pool", {})
            yes_pool = pool.get("YES", 0)
            no_pool = pool.get("NO", 0)
            if yes_pool + no_pool > 0:
                prob = no_pool / (yes_pool + no_pool)  # AMM-style pricing

        return {
            "source": "manifold",
            "question": m.get("question", ""),
            "url": m.get("url", ""),
            "yes_price": round(prob, 4) if prob is not None else None,
            "no_price": round(1 - prob, 4) if prob is not None else None,
            "probability": round(prob, 4) if prob is not None else None,
            "volume": m.get("volume"),
            "liquidity": m.get("totalLiquidity"),
            "active": not m.get("isResolved", False),
        }

    # ─── Fuzzy Filtering ─────────────────────────────────────────

    @staticmethod
    def _fuzzy_filter(markets: list[dict], query: str, key: str = "question") -> list[dict]:
        """Filter markets by matching ANY word from the query (case-insensitive).

        This is more permissive than exact substring matching — a query like
        "Iran ceasefire" will match markets containing either "Iran" OR "ceasefire".
        Results containing more query words are ranked first.
        """
        query_words = [w.lower() for w in query.split() if len(w) > 2]
        if not query_words:
            return markets

        scored = []
        for m in markets:
            text = m.get(key, "").lower()
            matches = sum(1 for w in query_words if w in text)
            if matches > 0:
                scored.append((matches, m))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored]

    # ─── Unified Search ──────────────────────────────────────────

    def search_all(self, query: str, limit: int = 5) -> list[dict]:
        """Search all supported prediction markets.

        Returns normalized results from all sources.
        Logs warnings when individual markets are unreachable.
        """
        results = []
        sources_searched = []
        for name, search_fn in [("Polymarket", self.polymarket_search), ("Kalshi", self.kalshi_search), ("Manifold", self.manifold_search)]:
            try:
                found = search_fn(query, limit=limit)
                results.extend(found)
                if found:
                    sources_searched.append(name)
                else:
                    logger.info("%s returned no matching markets for query: %s", name, query)
            except Exception as e:
                logger.warning("%s search failed: %s", name, e)
                continue

        if not sources_searched:
            logger.warning("No prediction markets returned results for query: %s", query)

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
