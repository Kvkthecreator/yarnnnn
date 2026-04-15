"""
Commerce Provider — Abstract Interface (ADR-183)

Provider-agnostic commerce operations. Lemon Squeezy is the first
implementation; architecture supports provider swap without pipeline changes.

All methods accept `api_key` as first parameter for multi-user safety
(same pattern as Slack/Notion/GitHub clients accepting `token`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class CommerceProduct:
    """A product in the user's commerce store."""

    id: str
    name: str
    price_cents: int
    currency: str
    interval: Optional[str]  # "month", "year", None for one-time
    status: str  # "published", "draft", "archived"
    subscriber_count: int
    url: Optional[str]  # checkout URL


@dataclass
class CommerceCustomer:
    """A customer/subscriber in the user's commerce store."""

    id: str
    email: str
    name: Optional[str]
    status: str  # "active", "cancelled", "past_due", "expired"
    product_name: Optional[str]
    product_id: Optional[str]
    total_revenue_cents: int
    created_at: str  # ISO8601
    updated_at: Optional[str]


@dataclass
class CommerceRevenueSummary:
    """Aggregate revenue metrics."""

    mrr_cents: int
    total_revenue_cents: int
    active_subscribers: int
    total_customers: int
    currency: str


@dataclass
class CommerceOrder:
    """A one-time order."""

    id: str
    customer_email: str
    product_name: str
    total_cents: int
    currency: str
    status: str  # "paid", "refunded", "pending"
    created_at: str


class CommerceProvider(ABC):
    """
    Provider-agnostic commerce operations.

    Implementations: LemonSqueezyClient (first).
    Future: StripeConnectClient, PaddleClient.
    """

    @abstractmethod
    async def validate_key(self, api_key: str) -> dict:
        """Validate API key and return store info (name, id, currency).

        Raises on invalid key.
        """
        ...

    @abstractmethod
    async def list_products(self, api_key: str) -> list[CommerceProduct]:
        """List all products in the store."""
        ...

    @abstractmethod
    async def get_subscribers(
        self, api_key: str, product_id: Optional[str] = None
    ) -> list[CommerceCustomer]:
        """List active subscribers, optionally filtered by product."""
        ...

    @abstractmethod
    async def get_customers(self, api_key: str) -> list[CommerceCustomer]:
        """List all customers (subscribers + one-time buyers)."""
        ...

    @abstractmethod
    async def get_revenue_summary(self, api_key: str) -> CommerceRevenueSummary:
        """Get aggregate revenue metrics (MRR, total, subscriber count)."""
        ...

    @abstractmethod
    async def list_orders(
        self, api_key: str, limit: int = 50
    ) -> list[CommerceOrder]:
        """List recent one-time orders."""
        ...

    @abstractmethod
    async def create_checkout(
        self, api_key: str, product_id: str
    ) -> str:
        """Generate a checkout URL for a product. Returns the URL."""
        ...
