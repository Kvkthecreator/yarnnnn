"""
Alpaca Trading API Client — ADR-187: Trading Integration

Direct API client for Alpaca trading operations (ADR-076 pattern).
Uses Alpaca REST API v2 with API key + secret auth.

Two API surfaces via one client:
- Alpaca Trading API: account, positions, orders, portfolio history
- Alpha Vantage API: daily prices, fundamentals (market data key in connection metadata)

Paper vs. live trading determined by base URL:
- Paper: https://paper-api.alpaca.markets
- Live:  https://api.alpaca.markets

Market data (bars) uses Alpaca's data API:
- https://data.alpaca.markets
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

ALPACA_PAPER_BASE = "https://paper-api.alpaca.markets"
ALPACA_LIVE_BASE = "https://api.alpaca.markets"
ALPACA_DATA_BASE = "https://data.alpaca.markets"
ALPHA_VANTAGE_BASE = "https://www.alphavantage.co"

_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
_MAX_RETRIES = 3
_RETRY_BACKOFF_SECONDS = [1, 2, 4]


class AlpacaClient:
    """
    Direct API client for Alpaca trading + Alpha Vantage market data.

    Usage:
        client = AlpacaClient()
        account = await client.get_account(api_key="PK...", api_secret="...", paper=True)
        bars = await client.get_bars(api_key="PK...", api_secret="...", ticker="AAPL")
    """

    def _get_trading_base(self, paper: bool = True) -> str:
        """Return the correct base URL for paper vs. live trading."""
        return ALPACA_PAPER_BASE if paper else ALPACA_LIVE_BASE

    async def _request(
        self,
        method: str,
        base_url: str,
        path: str,
        api_key: str,
        api_secret: str,
        params: Optional[dict] = None,
        json_body: Optional[dict] = None,
    ) -> Any:
        """Make Alpaca API request with retry on transient failures."""
        url = f"{base_url}{path}"
        headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": api_secret,
            "Accept": "application/json",
        }
        if json_body:
            headers["Content-Type"] = "application/json"

        last_error = None

        for attempt in range(_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                    response = await client.request(
                        method, url, headers=headers,
                        params=params, json=json_body,
                    )

                if response.status_code == 401:
                    return {"error": "invalid_credentials", "status": 401}

                if response.status_code == 403:
                    return {"error": "forbidden", "status": 403}

                if response.status_code == 404:
                    return {"error": "not_found", "status": 404}

                if response.status_code == 422:
                    try:
                        body = response.json()
                    except Exception:
                        body = response.text
                    return {"error": "validation_error", "status": 422, "detail": body}

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "5"))
                    logger.warning(f"[ALPACA_API] Rate limited, waiting {retry_after}s")
                    await asyncio.sleep(min(retry_after, 30))
                    continue

                if response.status_code >= 500:
                    last_error = f"Alpaca API {response.status_code}"
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
                    f"[ALPACA_API] Request failed (attempt {attempt + 1}): {e}"
                )
                await asyncio.sleep(backoff)
            except Exception as e:
                logger.error(f"[ALPACA_API] Unexpected error: {e}")
                return {"error": str(e)}

        return {"error": f"Max retries exceeded: {last_error}"}

    async def _request_alpha_vantage(
        self,
        function: str,
        market_data_key: str,
        params: Optional[dict] = None,
    ) -> Any:
        """Make Alpha Vantage API request (simple GET, key-based auth)."""
        url = f"{ALPHA_VANTAGE_BASE}/query"
        all_params = {"function": function, "apikey": market_data_key}
        if params:
            all_params.update(params)

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.get(url, params=all_params)

            if response.status_code == 200:
                data = response.json()
                # AV returns errors in-band as {"Note": ...} or {"Error Message": ...}
                if "Error Message" in data:
                    return {"error": data["Error Message"]}
                if "Note" in data:
                    return {"error": f"Rate limited: {data['Note']}"}
                return data

            return {"error": f"Alpha Vantage {response.status_code}"}

        except Exception as e:
            logger.error(f"[ALPHA_VANTAGE] Error: {e}")
            return {"error": str(e)}

    # =========================================================================
    # Account & Portfolio
    # =========================================================================

    async def get_account(
        self, api_key: str, api_secret: str, paper: bool = True,
    ) -> dict:
        """Get trading account details: equity, cash, buying power, status."""
        base = self._get_trading_base(paper)
        result = await self._request("GET", base, "/v2/account", api_key, api_secret)
        if isinstance(result, dict) and result.get("error"):
            return result

        return {
            "account_number": result.get("account_number", ""),
            "status": result.get("status", ""),
            "equity": result.get("equity", "0"),
            "cash": result.get("cash", "0"),
            "buying_power": result.get("buying_power", "0"),
            "portfolio_value": result.get("portfolio_value", "0"),
            "currency": result.get("currency", "USD"),
            "pattern_day_trader": result.get("pattern_day_trader", False),
            "trading_blocked": result.get("trading_blocked", False),
        }

    async def get_positions(
        self, api_key: str, api_secret: str, paper: bool = True,
    ) -> list[dict]:
        """Get all current open positions with P&L."""
        base = self._get_trading_base(paper)
        result = await self._request("GET", base, "/v2/positions", api_key, api_secret)
        if isinstance(result, dict) and result.get("error"):
            return []

        if not isinstance(result, list):
            return []

        return [
            {
                "symbol": p.get("symbol", ""),
                "qty": p.get("qty", "0"),
                "side": p.get("side", "long"),
                "market_value": p.get("market_value", "0"),
                "cost_basis": p.get("cost_basis", "0"),
                "avg_entry_price": p.get("avg_entry_price", "0"),
                "current_price": p.get("current_price", "0"),
                "unrealized_pl": p.get("unrealized_pl", "0"),
                "unrealized_plpc": p.get("unrealized_plpc", "0"),
                "change_today": p.get("change_today", "0"),
            }
            for p in result
        ]

    async def get_portfolio_history(
        self,
        api_key: str,
        api_secret: str,
        paper: bool = True,
        period: str = "1M",
        timeframe: str = "1D",
    ) -> dict:
        """Get portfolio value history for performance tracking."""
        base = self._get_trading_base(paper)
        result = await self._request(
            "GET", base, "/v2/account/portfolio/history",
            api_key, api_secret,
            params={"period": period, "timeframe": timeframe},
        )
        if isinstance(result, dict) and result.get("error"):
            return result

        return {
            "timestamps": result.get("timestamp", []),
            "equity": result.get("equity", []),
            "profit_loss": result.get("profit_loss", []),
            "profit_loss_pct": result.get("profit_loss_pct", []),
            "base_value": result.get("base_value", 0),
        }

    # =========================================================================
    # Orders
    # =========================================================================

    async def list_orders(
        self,
        api_key: str,
        api_secret: str,
        paper: bool = True,
        status: str = "all",
        limit: int = 50,
    ) -> list[dict]:
        """Get recent orders with status and fill details."""
        base = self._get_trading_base(paper)
        params = {"status": status, "limit": limit, "direction": "desc"}
        result = await self._request(
            "GET", base, "/v2/orders", api_key, api_secret, params=params,
        )
        if isinstance(result, dict) and result.get("error"):
            return []

        if not isinstance(result, list):
            return []

        return [
            {
                "id": o.get("id", ""),
                "symbol": o.get("symbol", ""),
                "side": o.get("side", ""),
                "qty": o.get("qty", "0"),
                "filled_qty": o.get("filled_qty", "0"),
                "type": o.get("type", ""),
                "time_in_force": o.get("time_in_force", ""),
                "limit_price": o.get("limit_price"),
                "stop_price": o.get("stop_price"),
                "filled_avg_price": o.get("filled_avg_price"),
                "status": o.get("status", ""),
                "created_at": o.get("created_at", ""),
                "filled_at": o.get("filled_at"),
            }
            for o in result
        ]

    async def submit_order(
        self,
        api_key: str,
        api_secret: str,
        paper: bool = True,
        *,
        symbol: str,
        side: str,
        qty: float,
        order_type: str,
        time_in_force: str = "day",
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ) -> dict:
        """Submit a trading order. Returns order ID and status."""
        base = self._get_trading_base(paper)
        body: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "qty": str(qty),
            "type": order_type,
            "time_in_force": time_in_force,
        }
        if limit_price is not None:
            body["limit_price"] = str(limit_price)
        if stop_price is not None:
            body["stop_price"] = str(stop_price)

        result = await self._request(
            "POST", base, "/v2/orders", api_key, api_secret, json_body=body,
        )
        if isinstance(result, dict) and result.get("error"):
            return result

        return {
            "id": result.get("id", ""),
            "symbol": result.get("symbol", ""),
            "side": result.get("side", ""),
            "qty": result.get("qty", "0"),
            "type": result.get("type", ""),
            "status": result.get("status", ""),
            "created_at": result.get("created_at", ""),
            "limit_price": result.get("limit_price"),
            "stop_price": result.get("stop_price"),
        }

    async def cancel_order(
        self, api_key: str, api_secret: str, order_id: str, paper: bool = True,
    ) -> dict:
        """Cancel an open order by ID."""
        base = self._get_trading_base(paper)
        return await self._request(
            "DELETE", base, f"/v2/orders/{order_id}", api_key, api_secret,
        )

    async def close_position(
        self, api_key: str, api_secret: str, symbol: str, paper: bool = True,
    ) -> dict:
        """Close an entire position for a symbol."""
        base = self._get_trading_base(paper)
        return await self._request(
            "DELETE", base, f"/v2/positions/{symbol}", api_key, api_secret,
        )

    # =========================================================================
    # Market Data (Alpaca Data API)
    # =========================================================================

    async def get_bars(
        self,
        api_key: str,
        api_secret: str,
        symbol: str,
        timeframe: str = "1Day",
        limit: int = 30,
    ) -> list[dict]:
        """Get historical bars (OHLCV) from Alpaca Data API."""
        start = (datetime.now(timezone.utc) - timedelta(days=limit * 2)).strftime(
            "%Y-%m-%dT00:00:00Z"
        )
        params = {
            "timeframe": timeframe,
            "start": start,
            "limit": limit,
            "sort": "desc",
        }
        result = await self._request(
            "GET", ALPACA_DATA_BASE,
            f"/v2/stocks/{symbol}/bars",
            api_key, api_secret, params=params,
        )
        if isinstance(result, dict) and result.get("error"):
            return []

        bars = result.get("bars", [])
        if not isinstance(bars, list):
            return []

        return [
            {
                "date": b.get("t", ""),
                "open": b.get("o", 0),
                "high": b.get("h", 0),
                "low": b.get("l", 0),
                "close": b.get("c", 0),
                "volume": b.get("v", 0),
            }
            for b in bars
        ]

    # =========================================================================
    # Alpha Vantage — Supplementary Market Data
    # =========================================================================

    async def get_daily_prices(
        self, market_data_key: str, symbol: str,
    ) -> list[dict]:
        """Get daily OHLCV from Alpha Vantage (last 30 trading days)."""
        result = await self._request_alpha_vantage(
            "TIME_SERIES_DAILY",
            market_data_key,
            params={"symbol": symbol, "outputsize": "compact"},
        )
        if isinstance(result, dict) and result.get("error"):
            return []

        time_series = result.get("Time Series (Daily)", {})
        prices = []
        for date_str, values in sorted(time_series.items(), reverse=True)[:30]:
            prices.append({
                "date": date_str,
                "open": float(values.get("1. open", 0)),
                "high": float(values.get("2. high", 0)),
                "low": float(values.get("3. low", 0)),
                "close": float(values.get("4. close", 0)),
                "volume": int(values.get("5. volume", 0)),
            })
        return prices

    async def get_fundamentals(
        self, market_data_key: str, symbol: str,
    ) -> dict:
        """Get company fundamentals from Alpha Vantage."""
        result = await self._request_alpha_vantage(
            "OVERVIEW",
            market_data_key,
            params={"symbol": symbol},
        )
        if isinstance(result, dict) and result.get("error"):
            return result

        return {
            "name": result.get("Name", ""),
            "description": result.get("Description", ""),
            "sector": result.get("Sector", ""),
            "industry": result.get("Industry", ""),
            "market_cap": result.get("MarketCapitalization", ""),
            "pe_ratio": result.get("PERatio", ""),
            "dividend_yield": result.get("DividendYield", ""),
            "52_week_high": result.get("52WeekHigh", ""),
            "52_week_low": result.get("52WeekLow", ""),
            "50_day_ma": result.get("50DayMovingAverage", ""),
            "200_day_ma": result.get("200DayMovingAverage", ""),
        }

    # =========================================================================
    # Validation
    # =========================================================================

    async def validate_credentials(
        self, api_key: str, api_secret: str, paper: bool = True,
    ) -> dict:
        """Validate credentials by fetching account info. Raises on invalid."""
        result = await self.get_account(api_key, api_secret, paper)
        if isinstance(result, dict) and result.get("error"):
            raise ValueError(f"Invalid Alpaca credentials: {result['error']}")
        return result


# =============================================================================
# Singleton
# =============================================================================

_alpaca_client: Optional[AlpacaClient] = None


def get_trading_client() -> AlpacaClient:
    """Get singleton Alpaca client instance."""
    global _alpaca_client
    if _alpaca_client is None:
        _alpaca_client = AlpacaClient()
    return _alpaca_client
