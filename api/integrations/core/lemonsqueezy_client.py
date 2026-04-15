"""
Lemon Squeezy API Client — ADR-183: Commerce Substrate

Direct API client for Lemon Squeezy operations (ADR-076 pattern).
Uses LS REST API v1 (JSON:API spec) with API key auth.

This is the USER's LS account (content commerce), NOT YARNNN's own LS
account (platform billing in routes/subscription.py). Two distinct surfaces.

Key differences from other platform clients:
- API key auth (no OAuth, no token refresh)
- JSON:API response format (data/attributes/relationships)
- Pagination via cursor, not page number
"""

import asyncio
import logging
from typing import Any, Optional

import httpx

from integrations.core.commerce_provider import (
    CommerceCustomer,
    CommerceOrder,
    CommerceProduct,
    CommerceProvider,
    CommerceRevenueSummary,
)

logger = logging.getLogger(__name__)

LS_API_BASE = "https://api.lemonsqueezy.com/v1"
_LS_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
_MAX_RETRIES = 3
_RETRY_BACKOFF_SECONDS = [1, 2, 4]


class LemonSqueezyClient(CommerceProvider):
    """
    Direct API client for Lemon Squeezy content commerce.

    Usage:
        client = LemonSqueezyClient()
        products = await client.list_products(api_key="lsq_...")
        subscribers = await client.get_subscribers(api_key="lsq_...")
    """

    async def _request(
        self,
        method: str,
        path: str,
        api_key: str,
        params: Optional[dict] = None,
    ) -> Any:
        """Make LS API request with retry on transient failures."""
        url = f"{LS_API_BASE}{path}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/vnd.api+json",
            "Content-Type": "application/vnd.api+json",
        }
        last_error = None

        for attempt in range(_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=_LS_TIMEOUT) as client:
                    response = await client.request(
                        method, url, headers=headers, params=params,
                    )

                if response.status_code == 401:
                    return {"error": "invalid_api_key", "status": 401}

                if response.status_code == 404:
                    return {"error": "not_found", "status": 404}

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "5"))
                    logger.warning(f"[LS_API] Rate limited, waiting {retry_after}s")
                    await asyncio.sleep(min(retry_after, 30))
                    continue

                if response.status_code >= 500:
                    last_error = f"LS API {response.status_code}"
                    backoff = _RETRY_BACKOFF_SECONDS[
                        min(attempt, len(_RETRY_BACKOFF_SECONDS) - 1)
                    ]
                    await asyncio.sleep(backoff)
                    continue

                if response.status_code in (200, 201):
                    return response.json()

                return {
                    "error": f"Unexpected status {response.status_code}",
                    "status": response.status_code,
                }

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = str(e)
                backoff = _RETRY_BACKOFF_SECONDS[
                    min(attempt, len(_RETRY_BACKOFF_SECONDS) - 1)
                ]
                logger.warning(
                    f"[LS_API] Request failed (attempt {attempt + 1}): {e}"
                )
                await asyncio.sleep(backoff)
            except Exception as e:
                logger.error(f"[LS_API] Unexpected error: {e}")
                return {"error": str(e)}

        return {"error": f"Max retries exceeded: {last_error}"}

    async def _paginate(
        self,
        path: str,
        api_key: str,
        params: Optional[dict] = None,
        max_pages: int = 5,
    ) -> list[dict]:
        """Paginate through LS JSON:API cursor-based results."""
        all_data: list[dict] = []
        params = dict(params or {})
        current_url_path = path

        for _ in range(max_pages):
            result = await self._request("GET", current_url_path, api_key, params=params)

            if isinstance(result, dict) and result.get("error"):
                logger.warning(f"[LS_API] Pagination error: {result}")
                break

            data = result.get("data", [])
            if isinstance(data, list):
                all_data.extend(data)
            elif isinstance(data, dict):
                all_data.append(data)

            # JSON:API cursor pagination
            next_url = result.get("links", {}).get("next")
            if not next_url:
                break
            # Next URL is absolute — extract path
            if next_url.startswith(LS_API_BASE):
                current_url_path = next_url[len(LS_API_BASE):]
            else:
                break
            params = {}  # params are in the URL for subsequent pages

        return all_data

    # =========================================================================
    # CommerceProvider implementation
    # =========================================================================

    async def validate_key(self, api_key: str) -> dict:
        """Validate API key by fetching the user/store info."""
        result = await self._request("GET", "/users/me", api_key)
        if isinstance(result, dict) and result.get("error"):
            raise ValueError(f"Invalid API key: {result['error']}")

        attrs = result.get("data", {}).get("attributes", {})
        return {
            "store_name": attrs.get("name", ""),
            "email": attrs.get("email", ""),
        }

    async def list_products(self, api_key: str) -> list[CommerceProduct]:
        """List all products in the user's LS store."""
        # First get store ID
        stores = await self._request("GET", "/stores", api_key)
        if isinstance(stores, dict) and stores.get("error"):
            return []

        store_data = stores.get("data", [])
        if not store_data:
            return []
        store_id = store_data[0].get("id")

        # Get products for this store
        raw = await self._paginate(
            "/products",
            api_key,
            params={"filter[store_id]": store_id},
        )

        products = []
        for item in raw:
            attrs = item.get("attributes", {})
            products.append(
                CommerceProduct(
                    id=str(item.get("id", "")),
                    name=attrs.get("name", ""),
                    price_cents=attrs.get("price", 0),
                    currency="USD",  # LS is USD-primary
                    interval=None,  # resolved from variants
                    status=attrs.get("status", "draft"),
                    subscriber_count=0,  # resolved from subscriptions
                    url=attrs.get("buy_now_url"),
                )
            )
        return products

    async def get_subscribers(
        self, api_key: str, product_id: Optional[str] = None
    ) -> list[CommerceCustomer]:
        """List active subscribers."""
        params: dict[str, Any] = {"filter[status]": "active"}
        if product_id:
            params["filter[product_id]"] = product_id

        raw = await self._paginate("/subscriptions", api_key, params=params)

        customers = []
        for item in raw:
            attrs = item.get("attributes", {})
            customers.append(
                CommerceCustomer(
                    id=str(item.get("id", "")),
                    email=attrs.get("user_email", ""),
                    name=attrs.get("user_name"),
                    status=attrs.get("status", "active"),
                    product_name=attrs.get("product_name"),
                    product_id=str(attrs.get("product_id", "")),
                    total_revenue_cents=0,  # aggregated separately
                    created_at=attrs.get("created_at", ""),
                    updated_at=attrs.get("updated_at"),
                )
            )
        return customers

    async def get_customers(self, api_key: str) -> list[CommerceCustomer]:
        """List all customers (from /customers endpoint)."""
        raw = await self._paginate("/customers", api_key)

        customers = []
        for item in raw:
            attrs = item.get("attributes", {})
            customers.append(
                CommerceCustomer(
                    id=str(item.get("id", "")),
                    email=attrs.get("email", ""),
                    name=attrs.get("name"),
                    status=attrs.get("status", "active"),
                    product_name=None,
                    product_id=None,
                    total_revenue_cents=attrs.get("total_revenue_in_cents", 0),
                    created_at=attrs.get("created_at", ""),
                    updated_at=attrs.get("updated_at"),
                )
            )
        return customers

    async def get_revenue_summary(self, api_key: str) -> CommerceRevenueSummary:
        """Compute revenue summary from subscriptions + orders."""
        # Active subscriptions for MRR
        active_subs = await self.get_subscribers(api_key)
        # All customers for total
        all_customers = await self.get_customers(api_key)

        # MRR = sum of active subscription prices (approximation via subscription count)
        # LS doesn't have a single MRR endpoint — we count active subs
        total_revenue = sum(c.total_revenue_cents for c in all_customers)

        return CommerceRevenueSummary(
            mrr_cents=0,  # TODO: compute from product prices × active subs
            total_revenue_cents=total_revenue,
            active_subscribers=len(active_subs),
            total_customers=len(all_customers),
            currency="USD",
        )

    async def list_orders(
        self, api_key: str, limit: int = 50
    ) -> list[CommerceOrder]:
        """List recent orders."""
        raw = await self._paginate(
            "/orders",
            api_key,
            params={"page[size]": str(min(limit, 100))},
            max_pages=1,
        )

        orders = []
        for item in raw:
            attrs = item.get("attributes", {})
            orders.append(
                CommerceOrder(
                    id=str(item.get("id", "")),
                    customer_email=attrs.get("user_email", ""),
                    product_name=attrs.get("first_order_item", {}).get(
                        "product_name", ""
                    )
                    if isinstance(attrs.get("first_order_item"), dict)
                    else "",
                    total_cents=attrs.get("total", 0),
                    currency=attrs.get("currency", "USD"),
                    status=attrs.get("status", "paid"),
                    created_at=attrs.get("created_at", ""),
                )
            )
        return orders

    async def create_checkout(self, api_key: str, product_id: str) -> str:
        """Generate a checkout URL for a product variant."""
        # LS checkouts require a variant ID, not product ID
        # For Phase 1 (read-only), this is a placeholder
        return f"https://checkout.lemonsqueezy.com/buy/{product_id}"


# Singleton
_ls_client: Optional[LemonSqueezyClient] = None


def get_lemonsqueezy_client() -> LemonSqueezyClient:
    """Get singleton LS client instance."""
    global _ls_client
    if _ls_client is None:
        _ls_client = LemonSqueezyClient()
    return _ls_client


# Generic commerce client getter — returns the LS client for now
def get_commerce_client() -> CommerceProvider:
    """Get the active commerce provider client."""
    return get_lemonsqueezy_client()
