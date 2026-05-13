"""Pydantic models for Polymarket API responses."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


def _parse_json_str(value: Any) -> Any:
    """Parse double-encoded JSON strings (Gamma API quirk)."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    return value


class Market(BaseModel):
    """A Polymarket prediction market."""

    id: Optional[str] = None
    question: str = ""
    slug: Optional[str] = None
    condition_id: Optional[str] = Field(None, alias="conditionId")
    description: Optional[str] = None
    outcomes: List[str] = Field(default_factory=list)
    outcome_prices: List[str] = Field(default_factory=list, alias="outcomePrices")
    clob_token_ids: List[str] = Field(default_factory=list, alias="clobTokenIds")
    volume: Optional[float] = None
    liquidity: Optional[float] = None
    active: bool = True
    closed: bool = False
    market_type: Optional[str] = Field(None, alias="marketType")
    end_date: Optional[datetime] = Field(None, alias="endDate")
    created_at: Optional[datetime] = Field(None, alias="createdAt")

    @field_validator("outcomes", "outcome_prices", "clob_token_ids", mode="before")
    @classmethod
    def _parse_json(cls, v: Any) -> Any:
        return _parse_json_str(v)

    @property
    def yes_price(self) -> Optional[float]:
        """Return the Yes outcome price as a float (0.0–1.0)."""
        if self.outcome_prices:
            try:
                return float(self.outcome_prices[0])
            except (ValueError, TypeError):
                pass
        return None

    @property
    def no_price(self) -> Optional[float]:
        """Return the No outcome price as a float (0.0–1.0)."""
        if len(self.outcome_prices) > 1:
            try:
                return float(self.outcome_prices[1])
            except (ValueError, TypeError):
                pass
        return None


class Event(BaseModel):
    """A Polymarket event containing one or more markets."""

    id: Optional[str] = None
    title: str = ""
    slug: Optional[str] = None
    description: Optional[str] = None
    volume: Optional[float] = None
    liquidity: Optional[float] = None
    active: bool = True
    closed: bool = False
    category: Optional[str] = None
    start_date: Optional[datetime] = Field(None, alias="startDate")
    end_date: Optional[datetime] = Field(None, alias="endDate")
    markets: List[Market] = Field(default_factory=list)


class SearchResult(BaseModel):
    """Gamma public-search response wrapper."""

    events: List[Event] = Field(default_factory=list)
    has_more: bool = Field(False, alias="hasMore")
    total_results: int = Field(0, alias="totalResults")


class PricePoint(BaseModel):
    """Single point in a price-history series."""

    timestamp: int = Field(..., alias="t")
    price: str = Field(..., alias="p")

    @property
    def price_float(self) -> float:
        return float(self.price)


class PriceHistory(BaseModel):
    """CLOB prices-history response."""

    history: List[PricePoint] = Field(default_factory=list)


class OrderBookLevel(BaseModel):
    """Single bid or ask level."""

    price: str
    size: str

    @property
    def price_float(self) -> float:
        return float(self.price)

    @property
    def size_float(self) -> float:
        return float(self.size)


class OrderBook(BaseModel):
    """CLOB orderbook response."""

    market: Optional[str] = None
    asset_id: Optional[str] = Field(None, alias="asset_id")
    bids: List[OrderBookLevel] = Field(default_factory=list)
    asks: List[OrderBookLevel] = Field(default_factory=list)
    min_order_size: Optional[str] = None
    tick_size: Optional[str] = None
    last_trade_price: Optional[str] = None
    neg_risk: Optional[bool] = Field(None, alias="neg_risk")


class Trade(BaseModel):
    """A single trade from the Data API."""

    side: str = ""
    size: float = 0.0
    price: float = 0.0
    timestamp: Optional[int] = None
    title: Optional[str] = None
    slug: Optional[str] = None
    outcome: Optional[str] = None
    transaction_hash: Optional[str] = Field(None, alias="transactionHash")
    condition_id: Optional[str] = Field(None, alias="conditionId")
    asset_id: Optional[str] = Field(None, alias="asset")
    proxy_wallet: Optional[str] = Field(None, alias="proxyWallet")
