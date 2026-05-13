"""PolyMate — Polymarket Buddy: Agent-usable tools for prediction market data."""

from polymarket_buddy.client import PolymarketClient
from polymarket_buddy.tools import (
    search_markets,
    get_market_odds,
    get_orderbook_summary,
    get_recent_trades,
)

__all__ = [
    "PolymarketClient",
    "search_markets",
    "get_market_odds",
    "get_orderbook_summary",
    "get_recent_trades",
]
