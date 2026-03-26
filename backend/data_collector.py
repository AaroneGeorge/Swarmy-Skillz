"""
Seed Data Collector

Gathers real-time data from public APIs to feed MiroFish simulations.
Outputs formatted markdown suitable for MiroFish document upload.
"""

import os
import json
from datetime import datetime, timezone

import requests


COINGECKO_BASE = "https://api.coingecko.com/api/v3"
NEWS_API_BASE = "https://newsapi.org/v2"


class DataCollector:
    """Collects and formats seed data for MiroFish swarm simulations."""

    def __init__(self):
        self.coingecko_key = os.environ.get("COINGECKO_API_KEY", "")
        self.news_api_key = os.environ.get("NEWS_API_KEY", "")

    # --- CoinGecko (free, no key required for basic endpoints) ---

    def get_crypto_price(self, coin_id: str = "bitcoin", days: int = 30) -> dict:
        """Get price history from CoinGecko.

        Args:
            coin_id: CoinGecko coin ID (e.g. "bitcoin", "ethereum", "solana").
            days: Number of days of history.

        Returns: {"prices": [[timestamp, price], ...], "current_price": float}
        """
        params = {"vs_currency": "usd", "days": days}
        if self.coingecko_key:
            params["x_cg_demo_api_key"] = self.coingecko_key

        resp = requests.get(f"{COINGECKO_BASE}/coins/{coin_id}/market_chart", params=params)
        resp.raise_for_status()
        data = resp.json()

        prices = data.get("prices", [])
        current = prices[-1][1] if prices else None

        return {
            "prices": prices,
            "current_price": current,
            "high_30d": max(p[1] for p in prices) if prices else None,
            "low_30d": min(p[1] for p in prices) if prices else None,
        }

    def get_crypto_info(self, coin_id: str = "bitcoin") -> dict:
        """Get coin metadata and market data."""
        params = {
            "localization": "false",
            "tickers": "false",
            "community_data": "true",
            "developer_data": "false",
        }
        if self.coingecko_key:
            params["x_cg_demo_api_key"] = self.coingecko_key

        resp = requests.get(f"{COINGECKO_BASE}/coins/{coin_id}", params=params)
        resp.raise_for_status()
        data = resp.json()

        market = data.get("market_data", {})
        return {
            "name": data.get("name"),
            "symbol": data.get("symbol"),
            "market_cap": market.get("market_cap", {}).get("usd"),
            "total_volume": market.get("total_volume", {}).get("usd"),
            "price_change_24h_pct": market.get("price_change_percentage_24h"),
            "price_change_7d_pct": market.get("price_change_percentage_7d"),
            "price_change_30d_pct": market.get("price_change_percentage_30d"),
            "ath": market.get("ath", {}).get("usd"),
            "ath_change_pct": market.get("ath_change_percentage", {}).get("usd"),
            "sentiment_up": data.get("sentiment_votes_up_percentage"),
            "sentiment_down": data.get("sentiment_votes_down_percentage"),
        }

    # --- News (requires NEWS_API_KEY, optional) ---

    def get_news(self, query: str, page_size: int = 10) -> list[dict]:
        """Search recent news articles.

        Args:
            query: Search query (e.g. "bitcoin price prediction").
            page_size: Number of articles to return.

        Returns: List of {"title", "description", "source", "published_at", "url"}
        """
        if not self.news_api_key:
            return self._fallback_news(query)

        resp = requests.get(f"{NEWS_API_BASE}/everything", params={
            "q": query,
            "sortBy": "publishedAt",
            "pageSize": page_size,
            "apiKey": self.news_api_key,
            "language": "en",
        })
        resp.raise_for_status()
        articles = resp.json().get("articles", [])

        return [
            {
                "title": a["title"],
                "description": a.get("description", ""),
                "source": a["source"]["name"],
                "published_at": a["publishedAt"],
                "url": a["url"],
            }
            for a in articles
            if a.get("title") and a["title"] != "[Removed]"
        ]

    def _fallback_news(self, query: str) -> list[dict]:
        """Fallback when no news API key — returns empty list with note."""
        return [{
            "title": f"[No NEWS_API_KEY set — skipping news for: {query}]",
            "description": "Set NEWS_API_KEY env var to enable news collection.",
            "source": "system",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "url": "",
        }]

    # --- Formatting ---

    def format_as_markdown(
        self,
        question: str,
        crypto_data: dict | None = None,
        crypto_info: dict | None = None,
        news: list[dict] | None = None,
        custom_context: str | None = None,
    ) -> str:
        """Format collected data as markdown for MiroFish upload.

        Args:
            question: The prediction question.
            crypto_data: Price history from get_crypto_price().
            crypto_info: Coin info from get_crypto_info().
            news: News articles from get_news().
            custom_context: Any additional context to include.

        Returns: Formatted markdown string.
        """
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        sections = [f"# Seed Data for Swarm Simulation\n\n**Question:** {question}\n**Generated:** {now}\n"]

        if crypto_info:
            sections.append("## Market Data\n")
            sections.append(f"- **Asset:** {crypto_info.get('name')} ({crypto_info.get('symbol', '').upper()})")
            if crypto_info.get("market_cap"):
                sections.append(f"- **Market Cap:** ${crypto_info['market_cap']:,.0f}")
            if crypto_info.get("total_volume"):
                sections.append(f"- **24h Volume:** ${crypto_info['total_volume']:,.0f}")
            if crypto_info.get("price_change_24h_pct") is not None:
                sections.append(f"- **24h Change:** {crypto_info['price_change_24h_pct']:+.2f}%")
            if crypto_info.get("price_change_7d_pct") is not None:
                sections.append(f"- **7d Change:** {crypto_info['price_change_7d_pct']:+.2f}%")
            if crypto_info.get("price_change_30d_pct") is not None:
                sections.append(f"- **30d Change:** {crypto_info['price_change_30d_pct']:+.2f}%")
            if crypto_info.get("ath"):
                sections.append(f"- **ATH:** ${crypto_info['ath']:,.0f} ({crypto_info.get('ath_change_pct', 0):+.1f}% from ATH)")
            if crypto_info.get("sentiment_up") is not None:
                sections.append(f"- **CoinGecko Sentiment:** {crypto_info['sentiment_up']:.0f}% bullish / {crypto_info.get('sentiment_down', 0):.0f}% bearish")
            sections.append("")

        if crypto_data:
            sections.append("## Price History (30 days)\n")
            if crypto_data.get("current_price"):
                sections.append(f"- **Current Price:** ${crypto_data['current_price']:,.2f}")
            if crypto_data.get("high_30d"):
                sections.append(f"- **30d High:** ${crypto_data['high_30d']:,.2f}")
            if crypto_data.get("low_30d"):
                sections.append(f"- **30d Low:** ${crypto_data['low_30d']:,.2f}")
            sections.append("")

        if news:
            sections.append("## Recent News\n")
            for article in news:
                sections.append(f"### {article['title']}")
                sections.append(f"*{article['source']} — {article['published_at'][:10]}*\n")
                if article.get("description"):
                    sections.append(f"{article['description']}\n")

        if custom_context:
            sections.append(f"## Additional Context\n\n{custom_context}\n")

        return "\n".join(sections)

    # --- High-Level Collectors ---

    def collect_crypto_seed(self, coin_id: str, question: str, custom_context: str | None = None) -> str:
        """Collect all available crypto data and format as markdown.

        Args:
            coin_id: CoinGecko coin ID.
            question: The prediction question.
            custom_context: Optional extra context.

        Returns: Markdown string ready for MiroFish upload.
        """
        crypto_data = None
        crypto_info = None
        news = None

        try:
            crypto_data = self.get_crypto_price(coin_id)
        except Exception as e:
            print(f"Warning: Failed to get price data: {e}")

        try:
            crypto_info = self.get_crypto_info(coin_id)
        except Exception as e:
            print(f"Warning: Failed to get coin info: {e}")

        try:
            news = self.get_news(f"{coin_id} price prediction")
        except Exception as e:
            print(f"Warning: Failed to get news: {e}")

        return self.format_as_markdown(
            question=question,
            crypto_data=crypto_data,
            crypto_info=crypto_info,
            news=news,
            custom_context=custom_context,
        )

    def collect_general_seed(self, question: str, search_terms: list[str] | None = None, custom_context: str | None = None) -> str:
        """Collect seed data for a non-crypto question.

        Args:
            question: The prediction question.
            search_terms: Keywords to search news for.
            custom_context: Optional extra context.

        Returns: Markdown string ready for MiroFish upload.
        """
        news = []
        if search_terms:
            for term in search_terms:
                try:
                    news.extend(self.get_news(term, page_size=5))
                except Exception as e:
                    print(f"Warning: Failed news search for '{term}': {e}")

        return self.format_as_markdown(
            question=question,
            news=news if news else None,
            custom_context=custom_context,
        )
