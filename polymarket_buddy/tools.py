"""High-level tools designed for AI agents.

Each function is self-contained (creates its own client), returns plain
Python dicts/lists, and includes concise natural-language summaries that
LLMs can consume directly.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from polymarket_buddy.client import PolymarketClient
from polymarket_buddy.models import Market, OrderBook


async def search_markets(
    query: str,
    *,
    limit: int = 5,
    include_orderbook: bool = False,
) -> List[Dict[str, Any]]:
    """Search Polymarket for events/markets matching a query.

    Returns a list of market dicts with keys:
    - ``question`` — the market question
    - ``slug`` — unique identifier
    - ``yes_odds`` / ``no_odds`` — current implied probability
    - ``volume`` — USDC volume
    - ``status`` — ACTIVE or CLOSED
    - ``orderbook`` (optional) — top bid/ask if requested
    """
    async with PolymarketClient() as client:
        result = await client.search(query, limit=limit)
        markets: List[Dict[str, Any]] = []
        for evt in result.events:
            for m in evt.markets:
                entry = _market_to_dict(m)
                if include_orderbook and m.clob_token_ids:
                    try:
                        ob = await client.get_orderbook(m.clob_token_ids[0])
                        entry["orderbook"] = _orderbook_to_dict(ob)
                    except Exception:
                        entry["orderbook"] = None
                markets.append(entry)
        return markets


async def get_market_odds(
    slug: str,
    *,
    include_history: bool = False,
    history_interval: str = "1w",
) -> Dict[str, Any]:
    """Fetch current odds and metadata for a single market by slug.

    Args:
        slug: Market slug (e.g. ``will-trump-win-2024``).
        include_history: Whether to fetch price-history series.
        history_interval: ``1d``, ``1w``, ``1m``, ``3m``, ``6m``, ``1y``, ``all``.

    Returns:
        Dict with ``question``, ``yes_odds``, ``no_odds``, ``volume``,
        ``status``, ``history`` (list of ``{time, price}`` if requested).
    """
    async with PolymarketClient() as client:
        markets = await client.list_markets(slug=slug, limit=1)
        if not markets:
            return {"error": f"Market '{slug}' not found."}
        m = markets[0]
        out = _market_to_dict(m)

        if include_history and m.condition_id:
            try:
                hist = await client.get_price_history(
                    m.condition_id, interval=history_interval, fidelity=50
                )
                out["history"] = [
                    {"time": pt.timestamp, "price": pt.price_float}
                    for pt in hist.history
                ]
            except Exception:
                out["history"] = []
        return out


async def get_orderbook_summary(
    token_id: str,
    *,
    depth: int = 5,
) -> Dict[str, Any]:
    """Fetch a concise orderbook snapshot for a token.

    Args:
        token_id: CLOB token ID (from ``clobTokenIds[0]`` for Yes, ``[1]`` for No).
        depth: Number of price levels to return on each side.

    Returns:
        Dict with ``best_bid``, ``best_ask``, ``spread``, ``bids``, ``asks``.
    """
    async with PolymarketClient() as client:
        ob = await client.get_orderbook(token_id)
        return {
            "best_bid": ob.bids[0].price_float if ob.bids else None,
            "best_ask": ob.asks[0].price_float if ob.asks else None,
            "spread": (
                ob.asks[0].price_float - ob.bids[0].price_float
                if ob.asks and ob.bids else None
            ),
            "last_trade_price": float(ob.last_trade_price) if ob.last_trade_price else None,
            "bids": [
                {"price": b.price_float, "size": b.size_float}
                for b in ob.bids[:depth]
            ],
            "asks": [
                {"price": a.price_float, "size": a.size_float}
                for a in ob.asks[:depth]
            ],
        }


async def get_recent_trades(
    *,
    condition_id: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Fetch recent trades, optionally filtered to a single market.

    Returns list of dicts with ``side``, ``price``, ``size``, ``outcome``,
    ``market_title``, ``timestamp``.
    """
    async with PolymarketClient() as client:
        trades = await client.get_trades(limit=limit, condition_id=condition_id)
        return [
            {
                "side": t.side,
                "price": t.price,
                "size": t.size,
                "outcome": t.outcome,
                "market_title": t.title,
                "timestamp": t.timestamp,
                "transaction_hash": t.transaction_hash,
            }
            for t in trades
        ]


# ---------------------------------------------------------------------------
# Synchronous wrappers for non-async callers
# ---------------------------------------------------------------------------

def search_markets_sync(*args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
    return asyncio.run(search_markets(*args, **kwargs))


def get_market_odds_sync(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return asyncio.run(get_market_odds(*args, **kwargs))


def get_orderbook_summary_sync(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return asyncio.run(get_orderbook_summary(*args, **kwargs))


def get_recent_trades_sync(*args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
    return asyncio.run(get_recent_trades(*args, **kwargs))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _market_to_dict(m: Market) -> Dict[str, Any]:
    return {
        "question": m.question,
        "slug": m.slug,
        "yes_odds": m.yes_price,
        "no_odds": m.no_price,
        "volume": m.volume,
        "liquidity": m.liquidity,
        "status": "CLOSED" if m.closed else "ACTIVE",
        "condition_id": m.condition_id,
        "clob_token_ids": m.clob_token_ids,
        "end_date": m.end_date.isoformat() if m.end_date else None,
    }


def _orderbook_to_dict(ob: OrderBook) -> Dict[str, Any]:
    return {
        "best_bid": ob.bids[0].price_float if ob.bids else None,
        "best_ask": ob.asks[0].price_float if ob.asks else None,
        "bid_depth": len(ob.bids),
        "ask_depth": len(ob.asks),
    }
