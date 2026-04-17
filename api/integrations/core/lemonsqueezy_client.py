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
        json_body: Optional[dict] = None,
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
                        method, url, headers=headers,
                        params=params, json=json_body,
                    )

                if response.status_code == 401:
                    return {"error": "invalid_api_key", "status": 401}

                if response.status_code == 404:
                    return {"error": "not_found", "status": 404}

                if response.status_code == 422:
                    # Validation error — don't retry
                    try:
                        body = response.json()
                    except Exception:
                        body = response.text
                    return {"error": "validation_error", "status": 422, "detail": body}

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

                if response.status_code in (200, 201, 204):
                    if response.status_code == 204:
                        return {"success": True}
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

    async def _get_store_id(self, api_key: str) -> Optional[str]:
        """Resolve the user's store ID (needed for create operations)."""
        stores = await self._request("GET", "/stores", api_key)
        if isinstance(stores, dict) and stores.get("error"):
            return None
        store_data = stores.get("data", [])
        if not store_data:
            return None
        return str(store_data[0].get("id"))

    async def create_checkout(self, api_key: str, product_id: str) -> str:
        """Generate a checkout URL via LS /checkouts endpoint.

        LS checkouts require a variant ID. We resolve the first variant
        for the given product, then create a checkout.
        """
        # Resolve first variant for this product
        variants = await self._request(
            "GET", "/variants", api_key,
            params={"filter[product_id]": product_id},
        )
        if isinstance(variants, dict) and variants.get("error"):
            logger.warning(f"[LS_API] Failed to get variants for product {product_id}: {variants}")
            return f"https://checkout.lemonsqueezy.com/buy/{product_id}"

        variant_data = variants.get("data", [])
        if not variant_data:
            logger.warning(f"[LS_API] No variants found for product {product_id}")
            return f"https://checkout.lemonsqueezy.com/buy/{product_id}"

        variant_id = str(variant_data[0]["id"])
        store_id = await self._get_store_id(api_key)
        if not store_id:
            return f"https://checkout.lemonsqueezy.com/buy/{product_id}"

        # Create checkout via JSON:API
        body = {
            "data": {
                "type": "checkouts",
                "attributes": {
                    "checkout_data": {"custom": {}},
                },
                "relationships": {
                    "store": {"data": {"type": "stores", "id": store_id}},
                    "variant": {"data": {"type": "variants", "id": variant_id}},
                },
            }
        }
        result = await self._request("POST", "/checkouts", api_key, json_body=body)
        if isinstance(result, dict) and result.get("error"):
            logger.warning(f"[LS_API] Checkout creation failed: {result}")
            return f"https://checkout.lemonsqueezy.com/buy/{product_id}"

        checkout_url = result.get("data", {}).get("attributes", {}).get("url", "")
        return checkout_url or f"https://checkout.lemonsqueezy.com/buy/{product_id}"

    # =========================================================================
    # Phase 3: Write operations (ADR-183)
    # =========================================================================

    async def create_product(
        self,
        api_key: str,
        name: str,
        description: str,
        price_cents: int,
        interval: Optional[str] = None,
    ) -> CommerceProduct:
        """Create a product + variant in LS.

        LS products always need at least one variant (the pricing entity).
        We create the product, then create a variant with the price.
        """
        store_id = await self._get_store_id(api_key)
        if not store_id:
            raise ValueError("Could not resolve store ID")

        # Create product
        product_body = {
            "data": {
                "type": "products",
                "attributes": {
                    "name": name,
                    "description": description,
                    "status": "draft",
                },
                "relationships": {
                    "store": {"data": {"type": "stores", "id": store_id}},
                },
            }
        }
        result = await self._request("POST", "/products", api_key, json_body=product_body)
        if isinstance(result, dict) and result.get("error"):
            raise ValueError(f"Product creation failed: {result.get('error')} — {result.get('detail', '')}")

        product_id = str(result["data"]["id"])
        attrs = result["data"]["attributes"]

        # Create variant (pricing entity)
        is_subscription = interval in ("month", "year")
        variant_body = {
            "data": {
                "type": "variants",
                "attributes": {
                    "name": "Default",
                    "price": price_cents,
                    "is_subscription": is_subscription,
                },
                "relationships": {
                    "product": {"data": {"type": "products", "id": product_id}},
                },
            }
        }
        if is_subscription:
            # LS interval values: "day", "week", "month", "year"
            variant_body["data"]["attributes"]["interval"] = interval
            variant_body["data"]["attributes"]["interval_count"] = 1

        variant_result = await self._request("POST", "/variants", api_key, json_body=variant_body)
        if isinstance(variant_result, dict) and variant_result.get("error"):
            logger.warning(f"[LS_API] Variant creation failed (product {product_id} exists without variant): {variant_result}")

        return CommerceProduct(
            id=product_id,
            name=attrs.get("name", name),
            price_cents=price_cents,
            currency="USD",
            interval=interval,
            status="draft",
            subscriber_count=0,
            url=attrs.get("buy_now_url"),
        )

    async def update_product(
        self,
        api_key: str,
        product_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
    ) -> CommerceProduct:
        """Update an existing product's name, description, or status."""
        update_attrs: dict[str, Any] = {}
        if name is not None:
            update_attrs["name"] = name
        if description is not None:
            update_attrs["description"] = description
        if status is not None:
            update_attrs["status"] = status

        if not update_attrs:
            raise ValueError("No fields to update")

        body = {
            "data": {
                "type": "products",
                "id": product_id,
                "attributes": update_attrs,
            }
        }
        result = await self._request("PATCH", f"/products/{product_id}", api_key, json_body=body)
        if isinstance(result, dict) and result.get("error"):
            raise ValueError(f"Product update failed: {result.get('error')} — {result.get('detail', '')}")

        attrs = result["data"]["attributes"]
        return CommerceProduct(
            id=product_id,
            name=attrs.get("name", ""),
            price_cents=attrs.get("price", 0),
            currency="USD",
            interval=None,
            status=attrs.get("status", ""),
            subscriber_count=0,
            url=attrs.get("buy_now_url"),
        )

    async def create_discount(
        self,
        api_key: str,
        name: str,
        code: str,
        amount: int,
        amount_type: str = "percent",
        product_id: Optional[str] = None,
    ) -> dict:
        """Create a discount code in LS.

        Args:
            name: Internal discount name.
            code: Customer-facing code (e.g., "LAUNCH20").
            amount: Percentage (20 = 20%) or fixed cents.
            amount_type: "percent" or "fixed".
            product_id: Scope to product, or None for store-wide.
        """
        store_id = await self._get_store_id(api_key)
        if not store_id:
            raise ValueError("Could not resolve store ID")

        body: dict[str, Any] = {
            "data": {
                "type": "discounts",
                "attributes": {
                    "name": name,
                    "code": code,
                    "amount": amount,
                    "amount_type": amount_type,
                },
                "relationships": {
                    "store": {"data": {"type": "stores", "id": store_id}},
                },
            }
        }

        # Scope to a specific product via variants
        if product_id:
            variants = await self._request(
                "GET", "/variants", api_key,
                params={"filter[product_id]": product_id},
            )
            variant_ids = []
            if not (isinstance(variants, dict) and variants.get("error")):
                variant_ids = [
                    {"type": "variants", "id": str(v["id"])}
                    for v in variants.get("data", [])
                ]
            if variant_ids:
                body["data"]["relationships"]["variants"] = {"data": variant_ids}

        result = await self._request("POST", "/discounts", api_key, json_body=body)
        if isinstance(result, dict) and result.get("error"):
            raise ValueError(f"Discount creation failed: {result.get('error')} — {result.get('detail', '')}")

        d_attrs = result["data"]["attributes"]
        return {
            "id": str(result["data"]["id"]),
            "code": d_attrs.get("code", code),
            "amount": d_attrs.get("amount", amount),
            "amount_type": d_attrs.get("amount_type", amount_type),
            "status": d_attrs.get("status", "published"),
        }

    # =========================================================================
    # ADR-192 Phase 3: Commerce operational tools
    # =========================================================================

    async def issue_refund(
        self,
        api_key: str,
        order_id: str,
        amount_cents: Optional[int] = None,
    ) -> dict:
        """Refund an order (full or partial).

        Args:
            order_id: LS order ID.
            amount_cents: Partial refund amount. Omit for full refund.

        Returns refund dict with id / status / amount.
        """
        attrs: dict[str, Any] = {}
        if amount_cents is not None:
            attrs["amount"] = amount_cents

        body = {
            "data": {
                "type": "refunds",
                "attributes": attrs,
                "relationships": {
                    "order": {"data": {"type": "orders", "id": str(order_id)}},
                },
            }
        }

        result = await self._request("POST", "/refunds", api_key, json_body=body)
        if isinstance(result, dict) and result.get("error"):
            return {"error": result.get("error"), "detail": result.get("detail", "")}

        r_attrs = result["data"]["attributes"]
        return {
            "id": str(result["data"]["id"]),
            "order_id": order_id,
            "amount": r_attrs.get("amount", amount_cents),
            "status": r_attrs.get("status", "completed"),
            "refunded_at": r_attrs.get("refunded_at"),
        }

    async def update_variant(
        self,
        api_key: str,
        variant_id: str,
        *,
        name: Optional[str] = None,
        price_cents: Optional[int] = None,
        is_subscription: Optional[bool] = None,
        interval: Optional[str] = None,
    ) -> dict:
        """Update a product variant (price, name, subscription interval).

        LS variants are the pricing entity — changing price, name, or
        subscription settings all happen at variant level, not product level.
        """
        update_attrs: dict[str, Any] = {}
        if name is not None:
            update_attrs["name"] = name
        if price_cents is not None:
            update_attrs["price"] = price_cents
        if is_subscription is not None:
            update_attrs["is_subscription"] = is_subscription
        if interval is not None:
            update_attrs["interval"] = interval
            update_attrs["interval_count"] = 1

        if not update_attrs:
            return {"error": "no_changes", "detail": "provide at least one field to update"}

        body = {
            "data": {
                "type": "variants",
                "id": str(variant_id),
                "attributes": update_attrs,
            }
        }
        result = await self._request(
            "PATCH", f"/variants/{variant_id}", api_key, json_body=body,
        )
        if isinstance(result, dict) and result.get("error"):
            return {"error": result.get("error"), "detail": result.get("detail", "")}

        v_attrs = result["data"]["attributes"]
        return {
            "id": str(result["data"]["id"]),
            "name": v_attrs.get("name"),
            "price": v_attrs.get("price"),
            "is_subscription": v_attrs.get("is_subscription"),
            "interval": v_attrs.get("interval"),
            "status": v_attrs.get("status"),
        }

    async def bulk_update_variant_prices(
        self,
        api_key: str,
        updates: list,
    ) -> dict:
        """Apply price updates across many variants. Per-variant outcome reported.

        Args:
            updates: list of {variant_id, price_cents} dicts.

        Returns:
            {
                success_count: int,
                failure_count: int,
                results: [{variant_id, price_cents, outcome, error?}, ...],
            }

        Each variant updated independently — partial failure doesn't roll back.
        """
        results = []
        for update in updates:
            variant_id = update.get("variant_id")
            price_cents = update.get("price_cents")
            if not variant_id or price_cents is None:
                results.append({
                    "variant_id": variant_id,
                    "price_cents": price_cents,
                    "outcome": "skipped",
                    "error": "variant_id and price_cents required",
                })
                continue

            result = await self.update_variant(
                api_key, str(variant_id), price_cents=int(price_cents),
            )
            if isinstance(result, dict) and result.get("error"):
                results.append({
                    "variant_id": variant_id,
                    "price_cents": price_cents,
                    "outcome": "failed",
                    "error": result.get("error"),
                })
            else:
                results.append({
                    "variant_id": variant_id,
                    "price_cents": price_cents,
                    "outcome": "updated",
                })

        success_count = sum(1 for r in results if r["outcome"] == "updated")
        failure_count = len(results) - success_count
        return {
            "success_count": success_count,
            "failure_count": failure_count,
            "results": results,
        }

    async def create_variant(
        self,
        api_key: str,
        product_id: str,
        name: str,
        price_cents: int,
        interval: Optional[str] = None,
    ) -> dict:
        """Create an additional variant on an existing product.

        LS products auto-get a "Default" variant on create. Use this to add
        secondary variants (e.g., monthly + annual pricing tiers on the
        same product).
        """
        is_subscription = interval in ("day", "week", "month", "year")
        attrs: dict[str, Any] = {
            "name": name,
            "price": price_cents,
            "is_subscription": is_subscription,
        }
        if is_subscription:
            attrs["interval"] = interval
            attrs["interval_count"] = 1

        body = {
            "data": {
                "type": "variants",
                "attributes": attrs,
                "relationships": {
                    "product": {"data": {"type": "products", "id": str(product_id)}},
                },
            }
        }
        result = await self._request("POST", "/variants", api_key, json_body=body)
        if isinstance(result, dict) and result.get("error"):
            return {"error": result.get("error"), "detail": result.get("detail", "")}

        v_attrs = result["data"]["attributes"]
        return {
            "id": str(result["data"]["id"]),
            "product_id": product_id,
            "name": v_attrs.get("name", name),
            "price": v_attrs.get("price", price_cents),
            "is_subscription": v_attrs.get("is_subscription", is_subscription),
            "interval": v_attrs.get("interval", interval),
            "status": v_attrs.get("status", "pending"),
        }

    async def update_customer(
        self,
        api_key: str,
        customer_id: str,
        *,
        name: Optional[str] = None,
        city: Optional[str] = None,
        country: Optional[str] = None,
        region: Optional[str] = None,
        email_marketing: Optional[bool] = None,
    ) -> dict:
        """Update LS-native customer metadata.

        LS doesn't natively support tags / segments. For cross-customer
        segmentation + targeting, write to workspace context (e.g.,
        `/workspace/context/customers/{slug}/_tags.md`) via WriteFile —
        that layer belongs to YARNNN, not LS.

        This tool updates LS's native customer record fields.
        """
        update_attrs: dict[str, Any] = {}
        if name is not None:
            update_attrs["name"] = name
        if city is not None:
            update_attrs["city"] = city
        if country is not None:
            update_attrs["country"] = country
        if region is not None:
            update_attrs["region"] = region
        if email_marketing is not None:
            # LS uses "email_marketing" (opt-in/opt-out) at the subscriber level;
            # use the relevant attribute per LS docs when available.
            update_attrs["email_marketing"] = email_marketing

        if not update_attrs:
            return {"error": "no_changes", "detail": "provide at least one field to update"}

        body = {
            "data": {
                "type": "customers",
                "id": str(customer_id),
                "attributes": update_attrs,
            }
        }
        result = await self._request(
            "PATCH", f"/customers/{customer_id}", api_key, json_body=body,
        )
        if isinstance(result, dict) and result.get("error"):
            return {"error": result.get("error"), "detail": result.get("detail", "")}

        c_attrs = result["data"]["attributes"]
        return {
            "id": str(result["data"]["id"]),
            "name": c_attrs.get("name"),
            "email": c_attrs.get("email"),
            "city": c_attrs.get("city"),
            "country": c_attrs.get("country"),
            "region": c_attrs.get("region"),
            "status": c_attrs.get("status"),
        }


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
