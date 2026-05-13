"""Async HTTP client for Polymarket's three public APIs."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx

from polymarket_buddy.models import (
    Event,
    Market,
    OrderBook,
    PriceHistory,
    SearchResult,
    Trade,
)

GAMMA_URL = "https://gamma-api.polymarket.com"
CLOB_URL = "https://clob.polymarket.com"
DATA_URL = "https://data-api.polymarket.com"


class PolymarketClient:
    """Unified async client for Gamma, CLOB, and Data APIs.

    All read-only endpoints require **no authentication**.
    If you need trading or private endpoints, set ``api_key`` / ``secret``
    via constructor or environment variables.
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        timeout: float = 15.0,
    ) -> None:
        self.api_key = api_key or os.getenv("POLYMARKET_API_KEY")
        self.api_secret = api_secret or os.getenv("POLYMARKET_API_SECRET")
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            headers={"User-Agent": "polymarket-buddy/0.1.0"},
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Gamma API — Discovery / Search
    # ------------------------------------------------------------------

    async def search(self, query: str, limit: int = 20) -> SearchResult:
        """Search events & markets by free-text query."""
        params: Dict[str, str] = {"q": query}
        if limit:
            params["limit"] = str(limit)
        data = await self._gamma_get("/public-search", params=params)
        return SearchResult.model_validate(data)

    async def list_events(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        active: Optional[bool] = True,
        closed: Optional[bool] = False,
        order: str = "volume",
        ascending: bool = False,
        tag: Optional[str] = None,
        slug: Optional[str] = None,
    ) -> List[Event]:
        """List events with optional filters."""
        params: Dict[str, str] = {
            "limit": str(limit),
            "offset": str(offset),
            "order": order,
            "ascending": "true" if ascending else "false",
        }
        if active is not None:
            params["active"] = "true" if active else "false"
        if closed is not None:
            params["closed"] = "true" if closed else "false"
        if tag:
            params["tag"] = tag
        if slug:
            params["slug"] = slug
        data = await self._gamma_get("/events", params=params)
        if isinstance(data, list):
            return [Event.model_validate(e) for e in data]
        return []

    async def list_markets(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        active: Optional[bool] = True,
        closed: Optional[bool] = False,
        order: str = "volume",
        ascending: bool = False,
        slug: Optional[str] = None,
    ) -> List[Market]:
        """List markets with optional filters."""
        params: Dict[str, str] = {
            "limit": str(limit),
            "offset": str(offset),
            "order": order,
            "ascending": "true" if ascending else "false",
        }
        if active is not None:
            params["active"] = "true" if active else "false"
        if closed is not None:
            params["closed"] = "true" if closed else "false"
        if slug:
            params["slug"] = slug
        data = await self._gamma_get("/markets", params=params)
        if isinstance(data, list):
            return [Market.model_validate(m) for m in data]
        return []

    # ------------------------------------------------------------------
    # CLOB API — Prices / Orderbooks / History
    # ------------------------------------------------------------------

    async def get_price(self, token_id: str, side: str = "buy") -> Optional[str]:
        """Get current price for a token."""
        data = await self._clob_get("/price", params={"token_id": token_id, "side": side})
        return data.get("price")

    async def get_midpoint(self, token_id: str) -> Optional[str]:
        """Get midpoint price for a token."""
        data = await self._clob_get("/midpoint", params={"token_id": token_id})
        return data.get("mid")

    async def get_spread(self, token_id: str) -> Optional[str]:
        """Get spread for a token."""
        data = await self._clob_get("/spread", params={"token_id": token_id})
        return data.get("spread")

    async def get_orderbook(self, token_id: str) -> OrderBook:
        """Get full orderbook for a token."""
        data = await self._clob_get("/book", params={"token_id": token_id})
        return OrderBook.model_validate(data)

    async def get_price_history(
        self,
        condition_id: str,
        *,
        interval: str = "all",
        fidelity: int = 50,
    ) -> PriceHistory:
        """Get historical prices for a market.

        Args:
            condition_id: Hex string (with 0x prefix) from Market.condition_id.
            interval: ``all``, ``1d``, ``1w``, ``1m``, ``3m``, ``6m``, ``1y``.
            fidelity: Max number of data points.
        """
        data = await self._clob_get(
            "/prices-history",
            params={"market": condition_id, "interval": interval, "fidelity": fidelity},
        )
        return PriceHistory.model_validate(data)

    async def list_clob_markets(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List markets directly from CLOB."""
        data = await self._clob_get("/markets", params={"limit": limit})
        return data.get("data", [])

    # ------------------------------------------------------------------
    # Data API — Trades / Open Interest
    # ------------------------------------------------------------------

    async def get_trades(
        self,
        *,
        limit: int = 20,
        condition_id: Optional[str] = None,
    ) -> List[Trade]:
        """Get recent trades, optionally filtered by market."""
        params: Dict[str, str] = {"limit": str(limit)}
        if condition_id:
            params["market"] = condition_id
        data = await self._data_get("/trades", params=params)
        if isinstance(data, list):
            return [Trade.model_validate(t) for t in data]
        return []

    async def get_open_interest(self, condition_id: str) -> Dict[str, Any]:
        """Get open interest for a market."""
        return await self._data_get("/oi", params={"market": condition_id})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _gamma_get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return await self._get(GAMMA_URL + path, params)

    async def _clob_get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return await self._get(CLOB_URL + path, params)

    async def _data_get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return await self._get(DATA_URL + path, params)

    async def _get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> PolymarketClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
