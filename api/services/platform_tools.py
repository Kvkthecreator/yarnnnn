"""
Platform Capability Runtime

Provider-native tool definitions and handlers for platform operations.
These tools are available to TP and, when explicitly granted by agent
capabilities, to headless task execution as well.

ADR-131: Gmail and Calendar sunset.
ADR-147: GitHub platform integration — list repos, get issues/PRs.
"""

import logging
from typing import Any

from integrations.core.tokens import get_token_manager

logger = logging.getLogger(__name__)


# =============================================================================
# Prompt Versioning
# =============================================================================

PROMPT_VERSIONS = {
    "platform_tools": {
        "version": "2026-03-29",
        "adr_refs": ["ADR-050", "ADR-131", "ADR-147"],
        "changelog": "ADR-147: Added GitHub platform tools (list repos, get issues/PRs)",
    },
    "slack": {
        "version": "2026-02-12",
        "adr_refs": ["ADR-050"],
        "changelog": "Streamlined for personal DM pattern (send to authed_user_id)",
    },
    "notion": {
        "version": "2026-02-12",
        "adr_refs": ["ADR-050"],
        "changelog": "Fixed MCP tool names for v2 server, added designated_page_id pattern",
    },
}


def get_prompt_version(component: str) -> dict:
    """Get version info for a platform tool component."""
    return PROMPT_VERSIONS.get(component, {})


def get_all_prompt_versions() -> dict:
    """Get all prompt version metadata."""
    return PROMPT_VERSIONS.copy()


# =============================================================================
# Tool Definitions (Anthropic format)
# =============================================================================

SLACK_TOOLS = [
    {
        "name": "platform_slack_send_message",
        "description": """Send a message to a Slack DM (direct message to self).

PRIMARY USE: Send to user's own DM so they own the output.
1. Call list_integrations to get authed_user_id
2. Use that user ID as channel_id

The user's authed_user_id is in integration metadata. Always send to self unless explicitly asked for a channel.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "channel_id": {
                    "type": "string",
                    "description": "User ID for DM (U...). Get from list_integrations authed_user_id"
                },
                "text": {
                    "type": "string",
                    "description": "Message text"
                }
            },
            "required": ["channel_id", "text"]
        }
    },
    {
        "name": "platform_slack_list_channels",
        "description": """List channels in the Slack workspace. Returns channel IDs and names.

Use to find a channel_id before calling platform_slack_get_channel_history.

After getting the list:
- If the user's channel name matches exactly → call get_channel_history immediately
- If no exact match → show the channel list to the user and ask which one they meant. Do NOT fall back to Search.
- If warning="channel_names_unavailable" → ask briefly for the channel link (one question, no tutorial)""",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "platform_slack_get_channel_history",
        "description": """Get recent message history from a Slack channel.

USE THIS to read what was discussed in a channel — this is the primary way to get Slack message content.

Workflow:
1. platform_slack_list_channels() → find the channel_id matching the channel name the user gave
2. platform_slack_get_channel_history(channel_id="C...", limit=50) → get messages

Do NOT fall back to Search at any point — Search only queries old cached content, not live messages. If the channel isn't found in list_channels, ask the user which channel they meant.

For "last 7 days", use oldest = Unix timestamp of 7 days ago (e.g., str(int(time.time()) - 7*86400)).

Parameters:
- channel_id: Channel ID (C...) — get from platform_slack_list_channels
- limit: Number of messages to retrieve (default 50, max 200)
- oldest: Unix timestamp string — filter messages after this time (optional, for date ranges)""",
        "input_schema": {
            "type": "object",
            "properties": {
                "channel_id": {
                    "type": "string",
                    "description": "Channel ID (C...). Get from platform_slack_list_channels."
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of messages to retrieve. Default: 50, max: 200."
                },
                "oldest": {
                    "type": "string",
                    "description": "Unix timestamp string. Only return messages after this time."
                }
            },
            "required": ["channel_id"]
        }
    },
]

NOTION_TOOLS = [
    {
        "name": "platform_notion_search",
        "description": "Search for pages in the Notion workspace. Returns page IDs for use with other tools.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "platform_notion_get_page",
        "description": """Read the content of a Notion page by ID.

Use AFTER platform_notion_search to read the actual content of a page.

Workflow:
1. platform_notion_search(query="...") → find the page, get its id
2. platform_notion_get_page(page_id="<id from search>") → read the content

Returns the page title and its text content as plain text blocks. Do NOT use Read or create_comment to probe page content — use this tool.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {
                    "type": "string",
                    "description": "Page ID (UUID). Get from platform_notion_search results."
                }
            },
            "required": ["page_id"]
        }
    },
    {
        "name": "platform_notion_create_comment",
        "description": """Add a comment to a Notion page.

PRIMARY USE: Add to user's designated page so they own the output.
1. Call list_integrations to get designated_page_id
2. Use that page ID as the target

The user's designated_page_id is in integration metadata. Use it unless user explicitly asks for a different page.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {
                    "type": "string",
                    "description": "Page ID (UUID). Get from list_integrations designated_page_id or search"
                },
                "content": {
                    "type": "string",
                    "description": "Comment text"
                }
            },
            "required": ["page_id", "content"]
        }
    },
]

# ADR-131: Gmail and Calendar tools removed (sunset)

# ADR-147: GitHub tools
GITHUB_TOOLS = [
    {
        "name": "platform_github_list_repos",
        "description": """List GitHub repositories accessible to the user.

Returns repo names, languages, and activity stats. Use to find repo names before calling platform_github_get_issues.""",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "platform_github_get_issues",
        "description": """Get recent issues and pull requests from a GitHub repository.

Workflow:
1. platform_github_list_repos() → find the repo
2. platform_github_get_issues(repo="owner/repo") → get issues + PRs

Parameters:
- repo: Full repo name (owner/repo format, e.g. "acme/webapp")
- state: "open" (default), "closed", or "all"
- limit: Number of items (default 20, max 50)""",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Full repo name: owner/repo"
                },
                "state": {
                    "type": "string",
                    "enum": ["open", "closed", "all"],
                    "description": "Issue state filter. Default: open"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of issues to retrieve. Default: 20, max: 50."
                }
            },
            "required": ["repo"]
        }
    },
    # ADR-158 Phase 5: GitHub reference tools
    {
        "name": "platform_github_get_repo_metadata",
        "description": """Get metadata for a GitHub repository: description, topics, language, stars, forks, license.

Use to understand what a repo is about without reading code. Works for any public repo or repos the user has access to.

Parameters:
- repo: Full repo name (owner/repo format)""",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Full repo name: owner/repo"
                },
            },
            "required": ["repo"]
        }
    },
    {
        "name": "platform_github_get_readme",
        "description": """Get the README content for a GitHub repository.

Returns the README as text (truncated to 5000 chars). Use to understand what a product/project claims to be. NOT for code analysis.

Parameters:
- repo: Full repo name (owner/repo format)""",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Full repo name: owner/repo"
                },
            },
            "required": ["repo"]
        }
    },
    {
        "name": "platform_github_get_releases",
        "description": """Get recent releases for a GitHub repository.

Returns tag names, release notes (truncated), and publish dates. Use to track what shipped.

Parameters:
- repo: Full repo name (owner/repo format)
- limit: Number of releases (default 10)""",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Full repo name: owner/repo"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of releases to retrieve. Default: 10."
                },
            },
            "required": ["repo"]
        }
    },
]

# ── Commerce Tools (ADR-183: Commerce Substrate) ──

COMMERCE_TOOLS = [
    {
        "name": "platform_commerce_list_products",
        "description": "List all products in the user's commerce store (Lemon Squeezy). Returns product name, price, status, subscriber count, and checkout URL.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "platform_commerce_get_subscribers",
        "description": "Get active subscribers. Optionally filter by product_id. Returns subscriber email, name, status, product, and dates.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "Optional: filter subscribers by product ID"
                },
            },
            "required": []
        }
    },
    {
        "name": "platform_commerce_get_revenue",
        "description": "Get aggregate revenue metrics: MRR, total revenue, active subscriber count, total customer count.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "platform_commerce_get_customers",
        "description": "List all customers (subscribers + one-time buyers). Returns email, name, total revenue, status, and dates.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "platform_commerce_create_checkout",
        "description": "Generate a checkout URL for a product. Returns a shareable link that anyone can use to purchase.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "The product ID to create a checkout URL for"
                },
            },
            "required": ["product_id"]
        }
    },
]

# ADR-183 Phase 3: Commerce write tools
COMMERCE_WRITE_TOOLS = [
    {
        "name": "platform_commerce_create_product",
        "description": "Create a new product in the commerce store. Returns the created product with its ID. Product starts in 'draft' status — use update_product to publish.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Product name (e.g., 'Weekly Competitive Brief')"
                },
                "description": {
                    "type": "string",
                    "description": "Product description for the store listing"
                },
                "price_cents": {
                    "type": "integer",
                    "description": "Price in cents (e.g., 1999 = $19.99)"
                },
                "interval": {
                    "type": "string",
                    "enum": ["month", "year"],
                    "description": "Billing interval for subscriptions. Omit for one-time purchase."
                },
            },
            "required": ["name", "description", "price_cents"]
        }
    },
    {
        "name": "platform_commerce_update_product",
        "description": "Update an existing product's name, description, or status. Only provided fields are changed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "The product ID to update"
                },
                "name": {
                    "type": "string",
                    "description": "New product name"
                },
                "description": {
                    "type": "string",
                    "description": "New product description"
                },
                "status": {
                    "type": "string",
                    "enum": ["published", "draft", "archived"],
                    "description": "Product status. Set to 'published' to make available for purchase."
                },
            },
            "required": ["product_id"]
        }
    },
    {
        "name": "platform_commerce_create_discount",
        "description": "Create a discount code for the commerce store. Can be store-wide or scoped to a specific product.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Internal name for the discount (e.g., 'Launch Promo')"
                },
                "code": {
                    "type": "string",
                    "description": "Customer-facing code (e.g., 'LAUNCH20')"
                },
                "amount": {
                    "type": "integer",
                    "description": "Discount amount — percentage (20 = 20%) or cents for fixed"
                },
                "amount_type": {
                    "type": "string",
                    "enum": ["percent", "fixed"],
                    "description": "Discount type: 'percent' (default) or 'fixed' (cents off)"
                },
                "product_id": {
                    "type": "string",
                    "description": "Scope discount to a specific product. Omit for store-wide."
                },
            },
            "required": ["name", "code", "amount"]
        }
    },
    # ADR-192 Phase 3: Commerce operational tools
    {
        "name": "platform_commerce_issue_refund",
        "description": "Refund an order. Pass amount_cents for partial refund; omit for full refund. Returns refund id + status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "Order ID to refund (from list_orders or customer lookup)."
                },
                "amount_cents": {
                    "type": "integer",
                    "description": "Partial refund amount in cents. Omit for full refund of original order amount."
                },
            },
            "required": ["order_id"]
        }
    },
    {
        "name": "platform_commerce_update_variant",
        "description": "Update a product variant (price, name, subscription interval). LS variants are the pricing entity — price changes happen here, not on the product. Pass only the fields you want to change.",
        "input_schema": {
            "type": "object",
            "properties": {
                "variant_id": {
                    "type": "string",
                    "description": "Variant ID to update (each product has ≥1 variant; the default is auto-created)."
                },
                "name": {"type": "string", "description": "New variant name."},
                "price_cents": {"type": "integer", "description": "New price in cents (e.g., 1999 = $19.99)."},
                "is_subscription": {"type": "boolean", "description": "Toggle subscription vs one-time."},
                "interval": {
                    "type": "string",
                    "enum": ["day", "week", "month", "year"],
                    "description": "Subscription interval (only relevant when is_subscription=true)."
                },
            },
            "required": ["variant_id"]
        }
    },
    {
        "name": "platform_commerce_bulk_update_variant_prices",
        "description": "Apply price updates across many variants. Each variant updated independently — partial failures don't roll back. Returns success_count, failure_count, and per-variant outcome.",
        "input_schema": {
            "type": "object",
            "properties": {
                "updates": {
                    "type": "array",
                    "description": "List of {variant_id, price_cents} updates.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "variant_id": {"type": "string"},
                            "price_cents": {"type": "integer"},
                        },
                        "required": ["variant_id", "price_cents"],
                    }
                }
            },
            "required": ["updates"]
        }
    },
    {
        "name": "platform_commerce_create_variant",
        "description": "Create an additional variant on an existing product (e.g., monthly + annual pricing tiers on the same product). Each product auto-gets a 'Default' variant on create; use this to add secondary tiers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string", "description": "Existing product ID."},
                "name": {"type": "string", "description": "Variant name (e.g., 'Annual', 'Monthly', 'Team tier')."},
                "price_cents": {"type": "integer", "description": "Price in cents."},
                "interval": {
                    "type": "string",
                    "enum": ["day", "week", "month", "year"],
                    "description": "Subscription interval. Omit for one-time purchase variant."
                },
            },
            "required": ["product_id", "name", "price_cents"]
        }
    },
    {
        "name": "platform_commerce_update_customer",
        "description": "Update LS-native customer metadata (name, city, country, region, email_marketing opt-in). For cross-customer tagging / segmentation, write to /workspace/context/customers/{slug}/_tags.md via WriteFile — that intelligence layer belongs in YARNNN, not LS.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "LS customer ID."},
                "name": {"type": "string", "description": "Customer display name."},
                "city": {"type": "string"},
                "country": {"type": "string", "description": "ISO country code (e.g., 'US')."},
                "region": {"type": "string", "description": "State / province / region."},
                "email_marketing": {"type": "boolean", "description": "Subscribe/unsubscribe customer from marketing emails."},
            },
            "required": ["customer_id"]
        }
    },
]


# =============================================================================
# ADR-187: Trading Platform Tools (Alpaca + Alpha Vantage)
# =============================================================================

TRADING_TOOLS = [
    {
        "name": "platform_trading_get_account",
        "description": "Get trading account details: equity, cash, buying power, portfolio value, account status.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "platform_trading_get_positions",
        "description": "Get all current open positions with unrealized P&L, market value, cost basis.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "platform_trading_get_orders",
        "description": "Get recent orders (last 7 days) with status, fill price, and timestamps.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by order status: open, closed, all. Default: all.",
                    "enum": ["open", "closed", "all"],
                },
                "limit": {
                    "type": "integer",
                    "description": "Max orders to return. Default: 50.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "platform_trading_get_market_data",
        "description": "Get daily price data for a ticker: open, high, low, close, volume. Returns last 30 trading days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g., AAPL, SPY, BTC/USD).",
                },
                "timeframe": {
                    "type": "string",
                    "description": "Data granularity: 1Day, 1Hour, 1Min. Default: 1Day.",
                    "enum": ["1Day", "1Hour", "1Min"],
                },
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "platform_trading_get_portfolio_history",
        "description": "Get portfolio value history over time for performance tracking.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": "History period: 1W, 1M, 3M, 6M, 1A. Default: 1M.",
                    "enum": ["1W", "1M", "3M", "6M", "1A"],
                },
            },
            "required": [],
        },
    },
]

TRADING_WRITE_TOOLS = [
    {
        "name": "platform_trading_submit_order",
        "description": "Submit a trading order. Returns order ID and status. Use limit orders for controlled execution.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g., AAPL, SPY).",
                },
                "side": {
                    "type": "string",
                    "description": "Order side: buy or sell.",
                    "enum": ["buy", "sell"],
                },
                "qty": {
                    "type": "number",
                    "description": "Number of shares (supports fractional, e.g., 0.5).",
                },
                "order_type": {
                    "type": "string",
                    "description": "Order type: market, limit, stop, stop_limit. Prefer limit.",
                    "enum": ["market", "limit", "stop", "stop_limit"],
                },
                "limit_price": {
                    "type": "number",
                    "description": "Limit price. Required for limit and stop_limit orders.",
                },
                "stop_price": {
                    "type": "number",
                    "description": "Stop price. Required for stop and stop_limit orders.",
                },
                "time_in_force": {
                    "type": "string",
                    "description": "Time in force: day, gtc (good til cancelled). Default: day.",
                    "enum": ["day", "gtc"],
                },
            },
            "required": ["ticker", "side", "qty", "order_type"],
        },
    },
    {
        "name": "platform_trading_cancel_order",
        "description": "Cancel an open order by order ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The Alpaca order ID to cancel.",
                },
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "platform_trading_close_position",
        "description": "Close an entire position for a ticker (sells all shares). Use partial_close_position if you want to close only N shares.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker to close position for.",
                },
            },
            "required": ["ticker"],
        },
    },
    # ADR-192 Phase 1: Trading sophistication
    {
        "name": "platform_trading_submit_bracket_order",
        "description": "Submit a bracket order (entry + take-profit + stop-loss in one atomic call). Recommended for disciplined position entry — if the entry doesn't fill, take-profit and stop-loss never activate. Use for all new positions unless you have a reason not to.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker (e.g., AAPL)."},
                "side": {"type": "string", "enum": ["buy", "sell"], "description": "Entry side."},
                "qty": {"type": "number", "description": "Number of shares (fractional supported)."},
                "entry_type": {"type": "string", "enum": ["limit", "market"], "description": "Entry order type. Prefer limit.", "default": "limit"},
                "entry_limit_price": {"type": "number", "description": "Entry limit price (required if entry_type=limit)."},
                "take_profit_limit_price": {"type": "number", "description": "Take-profit leg limit price."},
                "stop_loss_stop_price": {"type": "number", "description": "Stop-loss leg trigger price."},
                "stop_loss_limit_price": {"type": "number", "description": "Optional: stop-loss leg limit price (creates stop_limit instead of stop)."},
                "time_in_force": {"type": "string", "enum": ["day", "gtc"], "default": "day"},
            },
            "required": ["ticker", "side", "qty", "take_profit_limit_price", "stop_loss_stop_price"],
        },
    },
    {
        "name": "platform_trading_submit_trailing_stop",
        "description": "Submit a trailing-stop order. Stop follows price at a % or $ offset from the best mark. Provide EXACTLY ONE of trail_percent or trail_price.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker."},
                "side": {"type": "string", "enum": ["buy", "sell"], "description": "Stop side. Sell for long protection; buy for short cover."},
                "qty": {"type": "number", "description": "Number of shares."},
                "trail_percent": {"type": "number", "description": "Trail offset as % (e.g., 5.0 for 5%)."},
                "trail_price": {"type": "number", "description": "Trail offset in dollars (alternative to trail_percent)."},
                "time_in_force": {"type": "string", "enum": ["day", "gtc"], "default": "day"},
            },
            "required": ["ticker", "side", "qty"],
        },
    },
    {
        "name": "platform_trading_update_order",
        "description": "Modify an open order (qty / limit_price / stop_price / trail / time_in_force). Used to move a stop level on an existing stop order without cancel+resubmit race. Only provided fields change.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Alpaca order ID."},
                "qty": {"type": "number", "description": "New quantity."},
                "limit_price": {"type": "number", "description": "New limit price."},
                "stop_price": {"type": "number", "description": "New stop price (move stop-loss level)."},
                "trail": {"type": "number", "description": "New trailing offset."},
                "time_in_force": {"type": "string", "enum": ["day", "gtc"]},
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "platform_trading_partial_close",
        "description": "Close N shares of a position (not all). Safer wrapper than submit_order for position-reduction workflows; auto-detects position side and submits opposite-side market order for the requested quantity.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker."},
                "qty": {"type": "number", "description": "Number of shares to close (must be ≤ current position size)."},
            },
            "required": ["ticker", "qty"],
        },
    },
    {
        "name": "platform_trading_cancel_all_orders",
        "description": "Cancel all open orders. Use for 'get flat' scenarios or end-of-day cleanup. Returns per-order cancellation status.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "platform_trading_add_to_watchlist",
        "description": "Add a ticker to a named watchlist (creates watchlist if it doesn't exist). Default watchlist name is 'YARNNN'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker to add."},
                "watchlist_name": {"type": "string", "description": "Watchlist name.", "default": "YARNNN"},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "platform_trading_remove_from_watchlist",
        "description": "Remove a ticker from a named watchlist. No-op if watchlist or symbol absent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker to remove."},
                "watchlist_name": {"type": "string", "description": "Watchlist name.", "default": "YARNNN"},
            },
            "required": ["ticker"],
        },
    },
]


# =============================================================================
# ADR-192 Phase 4: Email platform class (Resend)
# =============================================================================
EMAIL_TOOLS = [
    {
        "name": "platform_email_send",
        "description": "Send a single email to one or more recipients (all receive the same body). For per-recipient personalized sends use send_bulk. Uses the user's connected Resend account. If the user hasn't verified a sending domain in Resend yet, falls back to 'onboarding@resend.dev' (alpha only — not production-quality sender).",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Recipient email addresses.",
                },
                "subject": {"type": "string", "description": "Email subject line."},
                "html": {"type": "string", "description": "Email body as HTML. Use <p>, <a>, basic inline styles. Plain text falls back from HTML."},
                "from_email": {"type": "string", "description": "Override sender email. Requires a verified domain in Resend. Omit to use the connection's default."},
                "from_name": {"type": "string", "description": "Sender display name (appears before the email in 'Name <email>')."},
                "reply_to": {"type": "string", "description": "Reply-To header. Replies land in this inbox."},
                "cc": {"type": "array", "items": {"type": "string"}, "description": "CC recipients."},
                "bcc": {"type": "array", "items": {"type": "string"}, "description": "BCC recipients."},
            },
            "required": ["to", "subject", "html"],
        },
    },
    {
        "name": "platform_email_send_bulk",
        "description": "Send many personalized emails in one call — each recipient gets their own subject + body. Use for campaigns, per-customer updates, segmented announcements. Returns per-message outcome; partial failure doesn't roll back. The shared from_email / from_name apply to any message that doesn't override.",
        "input_schema": {
            "type": "object",
            "properties": {
                "messages": {
                    "type": "array",
                    "description": "List of per-recipient messages. Each has its own {to, subject, html, optional reply_to / cc / bcc / from}.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "to": {
                                "oneOf": [
                                    {"type": "string"},
                                    {"type": "array", "items": {"type": "string"}},
                                ],
                                "description": "Recipient(s) for this message.",
                            },
                            "subject": {"type": "string"},
                            "html": {"type": "string"},
                            "reply_to": {"type": "string"},
                            "cc": {"type": "array", "items": {"type": "string"}},
                            "bcc": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["to", "subject", "html"],
                    },
                },
                "from_email": {"type": "string", "description": "Default sender email (any message may override)."},
                "from_name": {"type": "string", "description": "Default sender display name."},
            },
            "required": ["messages"],
        },
    },
]


# All platform tools by provider
PLATFORM_TOOLS_BY_PROVIDER = {
    "slack": SLACK_TOOLS,
    "notion": NOTION_TOOLS,
    "github": GITHUB_TOOLS,
    "commerce": COMMERCE_TOOLS + COMMERCE_WRITE_TOOLS,
    "trading": TRADING_TOOLS + TRADING_WRITE_TOOLS,
    "email": EMAIL_TOOLS,
}

PLATFORM_TOOLS_BY_CAPABILITY = {
    "read_slack": ["platform_slack_list_channels", "platform_slack_get_channel_history"],
    "write_slack": ["platform_slack_send_message"],
    "read_notion": ["platform_notion_search", "platform_notion_get_page"],
    "write_notion": ["platform_notion_create_comment"],
    "read_github": [
        "platform_github_list_repos", "platform_github_get_issues",
        "platform_github_get_repo_metadata", "platform_github_get_readme",
        "platform_github_get_releases",
    ],
    "read_commerce": [
        "platform_commerce_list_products", "platform_commerce_get_subscribers",
        "platform_commerce_get_revenue", "platform_commerce_get_customers",
        "platform_commerce_create_checkout",
    ],
    "write_commerce": [
        "platform_commerce_create_product", "platform_commerce_update_product",
        "platform_commerce_create_discount",
        # ADR-192 Phase 3: operational tools
        "platform_commerce_issue_refund",
        "platform_commerce_update_variant",
        "platform_commerce_bulk_update_variant_prices",
        "platform_commerce_create_variant",
        "platform_commerce_update_customer",
    ],
    "read_trading": [
        "platform_trading_get_account", "platform_trading_get_positions",
        "platform_trading_get_orders", "platform_trading_get_market_data",
        "platform_trading_get_portfolio_history",
    ],
    "write_trading": [
        "platform_trading_submit_order", "platform_trading_cancel_order",
        "platform_trading_close_position",
        # ADR-192 Phase 1: sophistication
        "platform_trading_submit_bracket_order",
        "platform_trading_submit_trailing_stop",
        "platform_trading_update_order",
        "platform_trading_partial_close",
        "platform_trading_cancel_all_orders",
        "platform_trading_add_to_watchlist",
        "platform_trading_remove_from_watchlist",
    ],
    # ADR-192 Phase 4: Email class
    "write_email": [
        "platform_email_send", "platform_email_send_bulk",
    ],
}

CAPABILITY_PROVIDER_MAP = {
    "read_slack": "slack",
    "write_slack": "slack",
    "read_notion": "notion",
    "write_notion": "notion",
    "read_github": "github",
    "read_commerce": "commerce",
    "write_commerce": "commerce",
    "read_trading": "trading",
    "write_trading": "trading",
    # ADR-192 Phase 4: email has no read capability (send-only in this phase)
    "write_email": "email",
}


# =============================================================================
# Dynamic Tool Loading
# =============================================================================

async def get_platform_tools_for_user(auth: Any) -> list[dict]:
    """
    Get platform tools for a user based on their connected integrations.

    Args:
        auth: Auth context with user_id and client

    Returns:
        List of tool definitions for connected platforms
    """
    tools = []
    seen_names: set[str] = set()  # Dedupe by tool name

    try:
        # Get user's active integrations
        result = auth.client.table("platform_connections").select(
            "platform, status"
        ).eq("user_id", auth.user_id).eq("status", "active").execute()

        connected_providers = [i["platform"] for i in (result.data or [])]

        for provider in connected_providers:
            provider_tools = PLATFORM_TOOLS_BY_PROVIDER.get(provider, [])
            for tool in provider_tools:
                tool_name = tool.get("name")
                if tool_name and tool_name not in seen_names:
                    tools.append(tool)
                    seen_names.add(tool_name)

        logger.info(f"[PLATFORM-TOOLS] User has {len(tools)} platform tools from {connected_providers}")

    except Exception as e:
        logger.error(f"[PLATFORM-TOOLS] Error loading tools: {e}")

    return tools


async def get_platform_tools_for_capabilities(auth: Any, capabilities: list[str]) -> list[dict]:
    """
    Get platform tools allowed by explicit provider-native capabilities.

    Only returns tools for:
    1. providers the user has connected, and
    2. providers/actions granted by the agent capability bundle
    """
    if not capabilities:
        return []

    try:
        result = auth.client.table("platform_connections").select(
            "platform, status"
        ).eq("user_id", auth.user_id).eq("status", "active").execute()
        connected_providers = {row["platform"] for row in (result.data or [])}
    except Exception as e:
        logger.error(f"[PLATFORM-TOOLS] Error loading connected providers: {e}")
        return []

    allowed_tool_names: set[str] = set()
    for capability in capabilities:
        provider = CAPABILITY_PROVIDER_MAP.get(capability)
        if not provider or provider not in connected_providers:
            continue
        allowed_tool_names.update(PLATFORM_TOOLS_BY_CAPABILITY.get(capability, []))

    if not allowed_tool_names:
        return []

    tools = []
    for provider in sorted(connected_providers):
        for tool in PLATFORM_TOOLS_BY_PROVIDER.get(provider, []):
            if tool.get("name") in allowed_tool_names:
                tools.append(tool)

    logger.info(
        "[PLATFORM-TOOLS] Capability-scoped tool load: %s tool(s) from %s",
        len(tools),
        sorted(connected_providers),
    )
    return tools


async def get_platform_tools_for_agent(auth: Any, agent: dict) -> list[dict]:
    """Get platform tools for a specific agent based on its explicit capabilities."""
    from services.agent_orchestration import get_type_capabilities

    role = (agent or {}).get("role", "")
    capabilities = get_type_capabilities(role) if role else []
    return await get_platform_tools_for_capabilities(auth, capabilities)


# =============================================================================
# Tool Handlers
# =============================================================================

async def handle_platform_tool(auth: Any, tool_name: str, tool_input: dict) -> dict:
    """
    Handle a platform tool call by routing to appropriate backend.

    ADR-076 Routing (all Direct API), ADR-131 (Gmail/Calendar sunset):
    - Slack: Direct API (SlackAPIClient)
    - Notion: Direct API (NotionAPIClient)

    Args:
        auth: Auth context
        tool_name: Tool name (e.g., platform_slack_send_message)
        tool_input: Tool arguments

    Returns:
        Tool result dict
    """
    # Parse tool name: platform_{provider}_{tool}
    parts = tool_name.split("_", 2)
    if len(parts) < 3 or parts[0] != "platform":
        return {
            "success": False,
            "error": f"Invalid platform tool name: {tool_name}",
        }

    provider = parts[1]
    tool = "_".join(parts[2:])  # Handle multi-part tool names

    # ADR-076: All platforms use Direct API
    if provider == "slack":
        return await _handle_slack_tool(auth, tool, tool_input)
    elif provider == "notion":
        return await _handle_notion_tool(auth, tool, tool_input)
    elif provider == "github":
        return await _handle_github_tool(auth, tool, tool_input)
    elif provider == "commerce":
        return await _handle_commerce_tool(auth, tool, tool_input)
    elif provider == "trading":
        return await _handle_trading_tool(auth, tool, tool_input)
    elif provider == "email":
        return await _handle_email_tool(auth, tool, tool_input)
    else:
        return {"success": False, "error": f"Unknown provider: {provider}"}


async def _handle_slack_tool(auth: Any, tool: str, tool_input: dict) -> dict:
    """Handle Slack tools via Direct API (ADR-076, replaces MCP Gateway)."""
    from integrations.core.slack_client import get_slack_client

    # Get user's integration credentials
    try:
        integration = auth.client.table("platform_connections").select(
            "credentials_encrypted, metadata"
        ).eq("user_id", auth.user_id).eq("platform", "slack").eq("status", "active").single().execute()

        if not integration.data:
            return {
                "success": False,
                "error": "No active Slack integration. Connect it in Settings.",
            }

        token_manager = get_token_manager()
        bot_token = token_manager.decrypt(integration.data["credentials_encrypted"])

    except Exception as e:
        logger.error(f"[PLATFORM-TOOLS] Failed to get Slack credentials: {e}")
        return {
            "success": False,
            "error": "Failed to get Slack credentials",
        }

    slack_client = get_slack_client()

    if tool == "send_message":
        result = await slack_client.post_message(
            bot_token=bot_token,
            channel_id=tool_input["channel_id"],
            text=tool_input["text"],
        )
        if result.get("ok"):
            return {
                "success": True,
                "result": {"ts": result.get("ts"), "channel": result.get("channel")},
            }
        return {"success": False, "error": result.get("error", "Slack API error")}

    elif tool == "list_channels":
        channels = await slack_client.list_channels(bot_token=bot_token)
        result_dict: dict = {
            "success": True,
            "result": {"channels": channels, "count": len(channels)},
        }
        # Detect missing names (token scope issue)
        if channels and all(not ch.get("name") for ch in channels):
            result_dict["warning"] = "channel_names_unavailable"
            result_dict["hint"] = (
                "Channel names unavailable — Slack token may lack channels:read scope. "
                "Ask the user for the channel link."
            )
        return result_dict

    elif tool == "get_channel_history":
        messages = await slack_client.get_channel_history(
            bot_token=bot_token,
            channel_id=tool_input["channel_id"],
            limit=tool_input.get("limit", 50),
            oldest=tool_input.get("oldest"),
        )
        # Normalize for TP readability
        normalized = []
        for msg in messages:
            text = msg.get("text", "")
            if not text:
                continue
            entry: dict = {
                "user": msg.get("user") or msg.get("username"),
                "text": text,
                "ts": msg.get("ts"),
            }
            reactions = msg.get("reactions")
            if reactions:
                entry["reactions"] = [
                    {"name": r.get("name"), "count": r.get("count", 0)}
                    for r in reactions
                    if isinstance(r, dict)
                ]
            normalized.append(entry)
        return {"success": True, "result": {"messages": normalized, "count": len(normalized)}}

    return {"success": False, "error": f"Unknown Slack tool: {tool}"}




def _extract_rich_text(rich_text_arr: list) -> str:
    """Extract plain text from a Notion rich_text array."""
    return "".join(part.get("plain_text", "") for part in rich_text_arr if isinstance(part, dict))


def _normalize_notion_blocks(blocks: list) -> list[dict]:
    """
    Convert Notion block objects to simple {type, text} dicts for TP readability.

    Notion blocks have deeply nested rich_text arrays inside type-specific sub-dicts.
    This normalizes to plain text so TP doesn't see raw API noise.
    """
    normalized = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_type = block.get("type")
        if not block_type:
            continue

        # Most block types have rich_text inside a type-keyed sub-dict
        type_data = block.get(block_type, {})
        rich_text = type_data.get("rich_text", [])
        text = _extract_rich_text(rich_text)

        # Special handling for specific types
        if block_type == "child_page":
            text = type_data.get("title", "")
        elif block_type == "image":
            img = type_data.get("external") or type_data.get("file") or {}
            text = img.get("url", "[image]")
        elif block_type == "divider":
            text = "---"
        elif block_type == "equation":
            text = type_data.get("expression", "")
        elif block_type == "to_do":
            checked = type_data.get("checked", False)
            prefix = "[x]" if checked else "[ ]"
            text = f"{prefix} {text}"
        elif block_type == "code":
            lang = type_data.get("language", "")
            text = f"```{lang}\n{text}\n```"

        if text or block_type in ("divider",):
            normalized.append({"type": block_type, "text": text})

    return normalized


async def _handle_notion_tool(auth: Any, tool: str, tool_input: dict) -> dict:
    """
    ADR-050: Handle Notion tools via Direct API.

    Why Direct API instead of MCP?
    1. @notionhq/notion-mcp-server requires internal tokens (ntn_...), not OAuth
    2. mcp.notion.com manages its own OAuth sessions, incompatible with pass-through
    3. Direct API works perfectly with our OAuth access tokens
    """
    from integrations.core.notion_client import get_notion_client
    from integrations.core.tokens import get_token_manager

    # Get user's Notion integration
    try:
        result = auth.client.table("platform_connections").select(
            "credentials_encrypted, metadata"
        ).eq("user_id", auth.user_id).eq("platform", "notion").eq("status", "active").single().execute()

        if not result.data:
            return {
                "success": False,
                "error": "No active Notion integration. Connect it in Settings.",
            }

        # Decrypt access token
        token_manager = get_token_manager()
        access_token = token_manager.decrypt(result.data["credentials_encrypted"])
        metadata = result.data.get("metadata") or {}

    except Exception as e:
        logger.error(f"[PLATFORM-TOOLS] Failed to get Notion credentials: {e}")
        return {
            "success": False,
            "error": "Failed to get Notion credentials",
        }

    # Get Notion API client
    notion_client = get_notion_client()

    try:
        return await _execute_notion_tool(notion_client, tool, tool_input, access_token, metadata)
    except Exception as e:
        logger.error(f"[PLATFORM-TOOLS] Notion API error: {e}")
        return {
            "success": False,
            "error": f"Notion API error: {str(e)}",
        }


async def _execute_notion_tool(
    notion_client,
    tool: str,
    args: dict,
    access_token: str,
    metadata: dict
) -> dict:
    """Execute Notion-specific tools via NotionAPIClient (NOT MCP)."""

    if tool == "search":
        results = await notion_client.search(
            access_token=access_token,
            query=args.get("query", ""),
            page_size=10,
        )

        # Format results for readability
        formatted = []
        for item in results:
            obj_type = item.get("object")
            title = ""

            # Extract title based on object type
            if obj_type == "page":
                props = item.get("properties", {})
                title_prop = props.get("title") or props.get("Name") or {}
                if "title" in title_prop:
                    title_arr = title_prop["title"]
                    if title_arr:
                        title = title_arr[0].get("plain_text", "Untitled")
            elif obj_type == "database":
                title_arr = item.get("title", [])
                if title_arr:
                    title = title_arr[0].get("plain_text", "Untitled Database")

            formatted.append({
                "id": item.get("id"),
                "type": obj_type,
                "title": title or "Untitled",
                "url": item.get("url"),
            })

        return {
            "success": True,
            "results": formatted,
            "count": len(results),
        }

    elif tool == "get_page":
        page_id = args.get("page_id")
        if not page_id:
            return {"success": False, "error": "page_id is required"}

        # Get page metadata (title, properties)
        page_meta = await notion_client.get_page(
            access_token=access_token,
            page_id=page_id,
        )

        # Extract title from page properties
        title = "Untitled"
        props = page_meta.get("properties", {})
        title_prop = props.get("title") or props.get("Name") or {}
        title_arr = title_prop.get("title", [])
        if title_arr:
            title = _extract_rich_text(title_arr) or "Untitled"

        # Get page content (blocks)
        blocks = await notion_client.get_page_content(
            access_token=access_token,
            page_id=page_id,
            page_size=100,
        )

        normalized_blocks = _normalize_notion_blocks(blocks)
        logger.info(f"[PLATFORM-TOOLS] notion get_page: {len(normalized_blocks)} blocks from page {page_id}")

        return {
            "success": True,
            "page_id": page_id,
            "title": title,
            "url": page_meta.get("url"),
            "blocks": normalized_blocks,
            "block_count": len(normalized_blocks),
        }

    elif tool == "create_comment":
        page_id = args.get("page_id")
        content = args.get("content")

        if not page_id:
            # Try to use designated page from metadata
            page_id = metadata.get("designated_page_id")
            if not page_id:
                return {
                    "success": False,
                    "error": "No page_id provided and no designated page set",
                }

        result = await notion_client.create_comment(
            access_token=access_token,
            page_id=page_id,
            content=content,
        )

        return {
            "success": True,
            "comment_id": result.get("id"),
            "page_id": page_id,
            "message": "Comment added to Notion page",
        }

    else:
        return {"success": False, "error": f"Unknown Notion tool: {tool}"}



# ADR-131: _handle_google_tool, _execute_gmail_tool, _execute_calendar_tool deleted (sunset)


async def _handle_github_tool(auth: Any, tool: str, tool_input: dict) -> dict:
    """Handle GitHub tools via Direct API (ADR-147)."""
    from integrations.core.github_client import get_github_client
    from integrations.core.tokens import get_token_manager

    try:
        result = auth.client.table("platform_connections").select(
            "credentials_encrypted, metadata"
        ).eq("user_id", auth.user_id).eq("platform", "github").eq("status", "active").single().execute()

        if not result.data:
            return {
                "success": False,
                "error": "No active GitHub integration. Connect it in Settings.",
            }

        token_manager = get_token_manager()
        token = token_manager.decrypt(result.data["credentials_encrypted"])

    except Exception as e:
        logger.error(f"[PLATFORM-TOOLS] Failed to get GitHub credentials: {e}")
        return {"success": False, "error": "Failed to get GitHub credentials"}

    github_client = get_github_client()

    if tool == "list_repos":
        repos = await github_client.list_repos(token=token, max_repos=50)
        if isinstance(repos, dict) and repos.get("error"):
            return {"success": False, "error": repos.get("error", "GitHub API error")}

        formatted = []
        for repo in (repos if isinstance(repos, list) else []):
            formatted.append({
                "name": repo.get("full_name"),
                "description": repo.get("description") or "",
                "language": repo.get("language"),
                "open_issues": repo.get("open_issues_count", 0),
                "updated_at": repo.get("updated_at"),
                "private": repo.get("private", False),
            })
        return {"success": True, "result": {"repos": formatted, "count": len(formatted)}}

    elif tool == "get_issues":
        repo = tool_input.get("repo")
        if not repo or "/" not in repo:
            return {"success": False, "error": "repo is required (format: owner/repo)"}

        state = tool_input.get("state", "open")
        limit = min(tool_input.get("limit", 20), 50)

        issues = await github_client.list_issues(
            token=token, repo=repo, state=state,
            per_page=limit, max_pages=1,
        )
        if isinstance(issues, dict) and issues.get("error"):
            return {"success": False, "error": issues.get("error", "GitHub API error")}

        formatted = []
        for item in (issues if isinstance(issues, list) else []):
            is_pr = bool(item.get("pull_request"))
            labels = [l.get("name", "") for l in item.get("labels", [])]
            formatted.append({
                "number": item.get("number"),
                "title": item.get("title"),
                "state": item.get("state"),
                "type": "pull_request" if is_pr else "issue",
                "author": item.get("user", {}).get("login"),
                "labels": labels,
                "comments": item.get("comments", 0),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "url": item.get("html_url"),
            })
        return {"success": True, "result": {"items": formatted, "count": len(formatted), "repo": repo}}

    # ADR-158 Phase 5: Reference reads
    elif tool == "get_repo_metadata":
        repo = tool_input.get("repo")
        if not repo or "/" not in repo:
            return {"success": False, "error": "repo is required (format: owner/repo)"}
        metadata = await github_client.get_repo_metadata(token=token, repo=repo)
        if isinstance(metadata, dict) and metadata.get("error"):
            return {"success": False, "error": metadata.get("error", "GitHub API error")}
        return {"success": True, "result": metadata}

    elif tool == "get_readme":
        repo = tool_input.get("repo")
        if not repo or "/" not in repo:
            return {"success": False, "error": "repo is required (format: owner/repo)"}
        readme = await github_client.get_readme(token=token, repo=repo)
        if isinstance(readme, dict) and readme.get("error"):
            return {"success": False, "error": readme.get("error", "GitHub API error")}
        return {"success": True, "result": readme}

    elif tool == "get_releases":
        repo = tool_input.get("repo")
        if not repo or "/" not in repo:
            return {"success": False, "error": "repo is required (format: owner/repo)"}
        limit = tool_input.get("limit", 10)
        releases = await github_client.get_releases(token=token, repo=repo, per_page=limit)
        if releases and isinstance(releases[0], dict) and releases[0].get("error"):
            return {"success": False, "error": releases[0].get("error", "GitHub API error")}
        return {"success": True, "result": {"releases": releases, "count": len(releases), "repo": repo}}

    return {"success": False, "error": f"Unknown GitHub tool: {tool}"}


async def _handle_commerce_tool(auth: Any, tool: str, tool_input: dict) -> dict:
    """Handle Commerce tools via Direct API (ADR-183)."""
    from integrations.core.lemonsqueezy_client import get_commerce_client
    from integrations.core.tokens import get_token_manager

    try:
        result = auth.client.table("platform_connections").select(
            "credentials_encrypted, metadata"
        ).eq("user_id", auth.user_id).eq("platform", "commerce").eq(
            "status", "active"
        ).single().execute()

        if not result.data:
            return {
                "success": False,
                "error": "No active commerce integration. Connect it in Settings.",
            }

        token_manager = get_token_manager()
        api_key = token_manager.decrypt(result.data["credentials_encrypted"])

    except Exception as e:
        logger.error(f"[PLATFORM-TOOLS] Failed to get commerce credentials: {e}")
        return {"success": False, "error": "Failed to get commerce credentials"}

    commerce_client = get_commerce_client()

    if tool == "list_products":
        products = await commerce_client.list_products(api_key=api_key)
        formatted = [
            {
                "id": p.id,
                "name": p.name,
                "price": f"${p.price_cents / 100:.2f}",
                "status": p.status,
                "subscriber_count": p.subscriber_count,
                "checkout_url": p.url,
            }
            for p in products
        ]
        return {"success": True, "result": {"products": formatted, "count": len(formatted)}}

    elif tool == "get_subscribers":
        product_id = tool_input.get("product_id")
        subscribers = await commerce_client.get_subscribers(
            api_key=api_key, product_id=product_id,
        )
        formatted = [
            {
                "email": s.email,
                "name": s.name,
                "status": s.status,
                "product": s.product_name,
                "created_at": s.created_at,
            }
            for s in subscribers
        ]
        return {"success": True, "result": {"subscribers": formatted, "count": len(formatted)}}

    elif tool == "get_revenue":
        summary = await commerce_client.get_revenue_summary(api_key=api_key)
        return {
            "success": True,
            "result": {
                "mrr": f"${summary.mrr_cents / 100:.2f}",
                "total_revenue": f"${summary.total_revenue_cents / 100:.2f}",
                "active_subscribers": summary.active_subscribers,
                "total_customers": summary.total_customers,
                "currency": summary.currency,
            },
        }

    elif tool == "get_customers":
        customers = await commerce_client.get_customers(api_key=api_key)
        formatted = [
            {
                "email": c.email,
                "name": c.name,
                "status": c.status,
                "total_revenue": f"${c.total_revenue_cents / 100:.2f}",
                "created_at": c.created_at,
            }
            for c in customers
        ]
        return {"success": True, "result": {"customers": formatted, "count": len(formatted)}}

    elif tool == "create_checkout":
        product_id = tool_input.get("product_id")
        if not product_id:
            return {"success": False, "error": "product_id is required"}
        url = await commerce_client.create_checkout(
            api_key=api_key, product_id=product_id,
        )
        return {"success": True, "result": {"checkout_url": url}}

    # ── Phase 3: Write operations ──

    elif tool == "create_product":
        name = tool_input.get("name")
        description = tool_input.get("description", "")
        price_cents = tool_input.get("price_cents")
        interval = tool_input.get("interval")
        if not name or price_cents is None:
            return {"success": False, "error": "name and price_cents are required"}
        try:
            product = await commerce_client.create_product(
                api_key=api_key, name=name, description=description,
                price_cents=price_cents, interval=interval,
            )
            return {
                "success": True,
                "result": {
                    "id": product.id,
                    "name": product.name,
                    "price": f"${product.price_cents / 100:.2f}",
                    "interval": product.interval or "one-time",
                    "status": product.status,
                    "note": "Product created as draft. Use update_product to set status='published' when ready.",
                },
            }
        except ValueError as e:
            return {"success": False, "error": str(e)}

    elif tool == "update_product":
        product_id = tool_input.get("product_id")
        if not product_id:
            return {"success": False, "error": "product_id is required"}
        try:
            product = await commerce_client.update_product(
                api_key=api_key,
                product_id=product_id,
                name=tool_input.get("name"),
                description=tool_input.get("description"),
                status=tool_input.get("status"),
            )
            return {
                "success": True,
                "result": {
                    "id": product.id,
                    "name": product.name,
                    "status": product.status,
                    "url": product.url,
                },
            }
        except ValueError as e:
            return {"success": False, "error": str(e)}

    elif tool == "create_discount":
        name = tool_input.get("name")
        code = tool_input.get("code")
        amount = tool_input.get("amount")
        if not name or not code or amount is None:
            return {"success": False, "error": "name, code, and amount are required"}
        try:
            discount = await commerce_client.create_discount(
                api_key=api_key,
                name=name,
                code=code,
                amount=amount,
                amount_type=tool_input.get("amount_type", "percent"),
                product_id=tool_input.get("product_id"),
            )
            return {"success": True, "result": discount}
        except ValueError as e:
            return {"success": False, "error": str(e)}

    # ADR-192 Phase 3: Commerce operational tools
    elif tool == "issue_refund":
        order_id = tool_input.get("order_id")
        if not order_id:
            return {"success": False, "error": "order_id is required"}
        amount_cents = tool_input.get("amount_cents")
        result = await commerce_client.issue_refund(
            api_key,
            order_id=str(order_id),
            amount_cents=int(amount_cents) if amount_cents is not None else None,
        )
        if isinstance(result, dict) and result.get("error"):
            return {"success": False, "error": result["error"], "message": result.get("detail", "")}
        return {"success": True, "result": result}

    elif tool == "update_variant":
        variant_id = tool_input.get("variant_id")
        if not variant_id:
            return {"success": False, "error": "variant_id is required"}
        result = await commerce_client.update_variant(
            api_key,
            variant_id=str(variant_id),
            name=tool_input.get("name"),
            price_cents=int(tool_input["price_cents"]) if tool_input.get("price_cents") is not None else None,
            is_subscription=tool_input.get("is_subscription"),
            interval=tool_input.get("interval"),
        )
        if isinstance(result, dict) and result.get("error"):
            return {"success": False, "error": result["error"], "message": result.get("detail", "")}
        return {"success": True, "result": result}

    elif tool == "bulk_update_variant_prices":
        updates = tool_input.get("updates")
        if not isinstance(updates, list) or not updates:
            return {"success": False, "error": "updates (non-empty list of {variant_id, price_cents}) is required"}
        result = await commerce_client.bulk_update_variant_prices(api_key, updates)
        return {"success": True, "result": result}

    elif tool == "create_variant":
        product_id = tool_input.get("product_id")
        name = tool_input.get("name")
        price_cents = tool_input.get("price_cents")
        if not (product_id and name and price_cents is not None):
            return {"success": False, "error": "product_id, name, and price_cents are required"}
        result = await commerce_client.create_variant(
            api_key,
            product_id=str(product_id),
            name=name,
            price_cents=int(price_cents),
            interval=tool_input.get("interval"),
        )
        if isinstance(result, dict) and result.get("error"):
            return {"success": False, "error": result["error"], "message": result.get("detail", "")}
        return {"success": True, "result": result}

    elif tool == "update_customer":
        customer_id = tool_input.get("customer_id")
        if not customer_id:
            return {"success": False, "error": "customer_id is required"}
        result = await commerce_client.update_customer(
            api_key,
            customer_id=str(customer_id),
            name=tool_input.get("name"),
            city=tool_input.get("city"),
            country=tool_input.get("country"),
            region=tool_input.get("region"),
            email_marketing=tool_input.get("email_marketing"),
        )
        if isinstance(result, dict) and result.get("error"):
            return {"success": False, "error": result["error"], "message": result.get("detail", "")}
        return {"success": True, "result": result}

    return {"success": False, "error": f"Unknown commerce tool: {tool}"}


async def _handle_trading_tool(auth: Any, tool: str, tool_input: dict) -> dict:
    """Handle Trading tools via Direct API (ADR-187)."""
    from integrations.core.alpaca_client import get_trading_client
    from integrations.core.tokens import get_token_manager

    try:
        result = auth.client.table("platform_connections").select(
            "credentials_encrypted, metadata"
        ).eq("user_id", auth.user_id).eq("platform", "trading").eq(
            "status", "active"
        ).single().execute()

        if not result.data:
            return {
                "success": False,
                "error": "No active trading integration. Connect it in Settings.",
            }

        token_manager = get_token_manager()
        credentials = token_manager.decrypt(result.data["credentials_encrypted"])
        metadata = result.data.get("metadata") or {}
        paper = metadata.get("paper", True)

        # Credentials stored as "key:secret"
        if ":" not in credentials:
            return {"success": False, "error": "Invalid trading credentials format"}
        api_key, api_secret = credentials.split(":", 1)

    except Exception as e:
        logger.error(f"[PLATFORM-TOOLS] Failed to get trading credentials: {e}")
        return {"success": False, "error": "Failed to get trading credentials"}

    trading_client = get_trading_client()

    # -- Read tools --

    if tool == "get_account":
        account = await trading_client.get_account(api_key, api_secret, paper)
        if isinstance(account, dict) and account.get("error"):
            return {"success": False, "error": account["error"]}
        return {"success": True, "result": account}

    elif tool == "get_positions":
        positions = await trading_client.get_positions(api_key, api_secret, paper)
        return {
            "success": True,
            "result": {"positions": positions, "count": len(positions)},
        }

    elif tool == "get_orders":
        status = tool_input.get("status", "all")
        limit = tool_input.get("limit", 50)
        orders = await trading_client.list_orders(
            api_key, api_secret, paper, status=status, limit=limit,
        )
        return {
            "success": True,
            "result": {"orders": orders, "count": len(orders)},
        }

    elif tool == "get_market_data":
        ticker = tool_input.get("ticker")
        if not ticker:
            return {"success": False, "error": "ticker is required"}
        timeframe = tool_input.get("timeframe", "1Day")

        # Try Alpaca Data API first (no extra key needed)
        bars = await trading_client.get_bars(
            api_key, api_secret, ticker, timeframe=timeframe,
        )

        # Fall back to Alpha Vantage if Alpaca returns empty and key is available
        if not bars and metadata.get("market_data_key"):
            bars = await trading_client.get_daily_prices(
                metadata["market_data_key"], ticker,
            )

        return {
            "success": True,
            "result": {
                "ticker": ticker,
                "timeframe": timeframe,
                "bars": bars,
                "count": len(bars),
            },
        }

    elif tool == "get_portfolio_history":
        period = tool_input.get("period", "1M")
        history = await trading_client.get_portfolio_history(
            api_key, api_secret, paper, period=period,
        )
        if isinstance(history, dict) and history.get("error"):
            return {"success": False, "error": history["error"]}
        return {"success": True, "result": history}

    # -- Write tools --

    elif tool == "submit_order":
        ticker = tool_input.get("ticker")
        side = tool_input.get("side")
        qty = tool_input.get("qty")
        order_type = tool_input.get("order_type")
        if not all([ticker, side, qty, order_type]):
            return {"success": False, "error": "ticker, side, qty, and order_type are required"}

        # ADR-192 Phase 2: pre-trade risk gate
        from services.risk_gate import check_risk_limits
        mode = tool_input.get("_mode", "supervised")
        proposed = {
            "ticker": ticker, "side": side, "qty": qty,
            "order_type": order_type,
            "limit_price": tool_input.get("limit_price"),
            "stop_price": tool_input.get("stop_price"),
        }
        gate = await check_risk_limits(
            auth.client, auth.user_id,
            proposed_order=proposed,
            mode=mode,
        )
        if not gate.get("approved"):
            # ADR-193 Phase 3: autonomous rejection → emit proposal; supervised → hard error
            if mode == "autonomous":
                from services.primitives.propose_action import (
                    handle_propose_action, build_trading_expected_effect,
                )
                prop_result = await handle_propose_action(auth, {
                    "action_type": "trading.submit_order",
                    "inputs": proposed,
                    "rationale": f"Risk gate rejected autonomous execution: {gate.get('reason')}. Review limits or approve override.",
                    "expected_effect": build_trading_expected_effect("trading.submit_order", proposed),
                    "reversibility": "irreversible",
                    "risk_warnings": [gate.get("reason", "")] + (gate.get("warnings") or []),
                    "expires_in_hours": 1,
                })
                return {
                    "success": False,
                    "error": "risk_limit_violation_proposed",
                    "message": f"Risk gate rejected; proposal emitted for user review.",
                    "proposal_id": prop_result.get("proposal_id"),
                    "proposal": prop_result.get("proposal"),
                    "mode": mode,
                }
            return {
                "success": False,
                "error": "risk_limit_violation",
                "message": gate.get("reason"),
                "warnings": gate.get("warnings", []),
                "mode": mode,
            }

        order = await trading_client.submit_order(
            api_key, api_secret, paper,
            symbol=ticker,
            side=side,
            qty=float(qty),
            order_type=order_type,
            time_in_force=tool_input.get("time_in_force", "day"),
            limit_price=tool_input.get("limit_price"),
            stop_price=tool_input.get("stop_price"),
        )
        if isinstance(order, dict) and order.get("error"):
            return {"success": False, "error": order["error"]}
        return {
            "success": True,
            "result": order,
            "risk_warnings": gate.get("warnings", []) or None,
        }

    elif tool == "cancel_order":
        order_id = tool_input.get("order_id")
        if not order_id:
            return {"success": False, "error": "order_id is required"}
        result = await trading_client.cancel_order(
            api_key, api_secret, order_id, paper,
        )
        if isinstance(result, dict) and result.get("error"):
            return {"success": False, "error": result["error"]}
        return {"success": True, "result": {"cancelled": True, "order_id": order_id}}

    elif tool == "close_position":
        ticker = tool_input.get("ticker")
        if not ticker:
            return {"success": False, "error": "ticker is required"}
        result = await trading_client.close_position(
            api_key, api_secret, ticker, paper,
        )
        if isinstance(result, dict) and result.get("error"):
            return {"success": False, "error": result["error"]}
        return {"success": True, "result": {"closed": True, "ticker": ticker}}

    # ADR-192 Phase 1: Trading sophistication (with Phase 2 risk gate)
    elif tool == "submit_bracket_order":
        ticker = tool_input.get("ticker")
        side = tool_input.get("side")
        qty = tool_input.get("qty")
        tp = tool_input.get("take_profit_limit_price")
        sl_stop = tool_input.get("stop_loss_stop_price")
        if not all([ticker, side, qty, tp, sl_stop]):
            return {"success": False, "error": "ticker, side, qty, take_profit_limit_price, and stop_loss_stop_price are required"}

        from services.risk_gate import check_risk_limits
        mode = tool_input.get("_mode", "supervised")
        proposed = {
            "ticker": ticker, "side": side, "qty": qty,
            "order_class": "bracket",
            "entry_type": tool_input.get("entry_type", "limit"),
            "entry_limit_price": tool_input.get("entry_limit_price"),
            "take_profit_limit_price": tp,
            "stop_loss_stop_price": sl_stop,
        }
        gate = await check_risk_limits(
            auth.client, auth.user_id,
            proposed_order=proposed,
            mode=mode,
        )
        if not gate.get("approved"):
            if mode == "autonomous":
                from services.primitives.propose_action import (
                    handle_propose_action, build_trading_expected_effect,
                )
                prop_result = await handle_propose_action(auth, {
                    "action_type": "trading.submit_bracket_order",
                    "inputs": proposed,
                    "rationale": f"Risk gate rejected autonomous execution: {gate.get('reason')}. Review limits or approve override.",
                    "expected_effect": build_trading_expected_effect("trading.submit_bracket_order", proposed),
                    "reversibility": "irreversible",
                    "risk_warnings": [gate.get("reason", "")] + (gate.get("warnings") or []),
                    "expires_in_hours": 1,
                })
                return {
                    "success": False,
                    "error": "risk_limit_violation_proposed",
                    "message": "Risk gate rejected; proposal emitted for user review.",
                    "proposal_id": prop_result.get("proposal_id"),
                    "proposal": prop_result.get("proposal"),
                    "mode": mode,
                }
            return {
                "success": False,
                "error": "risk_limit_violation",
                "message": gate.get("reason"),
                "warnings": gate.get("warnings", []),
                "mode": mode,
            }

        order = await trading_client.submit_bracket_order(
            api_key, api_secret, paper,
            symbol=ticker,
            side=side,
            qty=float(qty),
            entry_type=tool_input.get("entry_type", "limit"),
            entry_limit_price=tool_input.get("entry_limit_price"),
            take_profit_limit_price=float(tp),
            stop_loss_stop_price=float(sl_stop),
            stop_loss_limit_price=tool_input.get("stop_loss_limit_price"),
            time_in_force=tool_input.get("time_in_force", "day"),
        )
        if isinstance(order, dict) and order.get("error"):
            return {"success": False, "error": order["error"]}
        return {
            "success": True,
            "result": order,
            "risk_warnings": gate.get("warnings", []) or None,
        }

    elif tool == "submit_trailing_stop":
        ticker = tool_input.get("ticker")
        side = tool_input.get("side")
        qty = tool_input.get("qty")
        if not all([ticker, side, qty]):
            return {"success": False, "error": "ticker, side, and qty are required"}

        from services.risk_gate import check_risk_limits
        mode = tool_input.get("_mode", "supervised")
        proposed = {
            "ticker": ticker, "side": side, "qty": qty,
            "order_type": "trailing_stop",
            "trail_percent": tool_input.get("trail_percent"),
            "trail_price": tool_input.get("trail_price"),
        }
        gate = await check_risk_limits(
            auth.client, auth.user_id,
            proposed_order=proposed,
            mode=mode,
        )
        if not gate.get("approved"):
            if mode == "autonomous":
                from services.primitives.propose_action import (
                    handle_propose_action, build_trading_expected_effect,
                )
                prop_result = await handle_propose_action(auth, {
                    "action_type": "trading.submit_trailing_stop",
                    "inputs": proposed,
                    "rationale": f"Risk gate rejected autonomous execution: {gate.get('reason')}. Review limits or approve override.",
                    "expected_effect": build_trading_expected_effect("trading.submit_trailing_stop", proposed),
                    "reversibility": "irreversible",
                    "risk_warnings": [gate.get("reason", "")] + (gate.get("warnings") or []),
                    "expires_in_hours": 1,
                })
                return {
                    "success": False,
                    "error": "risk_limit_violation_proposed",
                    "message": "Risk gate rejected; proposal emitted for user review.",
                    "proposal_id": prop_result.get("proposal_id"),
                    "proposal": prop_result.get("proposal"),
                    "mode": mode,
                }
            return {
                "success": False,
                "error": "risk_limit_violation",
                "message": gate.get("reason"),
                "warnings": gate.get("warnings", []),
                "mode": mode,
            }

        order = await trading_client.submit_trailing_stop(
            api_key, api_secret, paper,
            symbol=ticker,
            side=side,
            qty=float(qty),
            trail_percent=tool_input.get("trail_percent"),
            trail_price=tool_input.get("trail_price"),
            time_in_force=tool_input.get("time_in_force", "day"),
        )
        if isinstance(order, dict) and order.get("error"):
            return {"success": False, "error": order["error"], "message": order.get("message")}
        return {
            "success": True,
            "result": order,
            "risk_warnings": gate.get("warnings", []) or None,
        }

    elif tool == "update_order":
        order_id = tool_input.get("order_id")
        if not order_id:
            return {"success": False, "error": "order_id is required"}
        result = await trading_client.update_order(
            api_key, api_secret, order_id, paper,
            qty=tool_input.get("qty"),
            limit_price=tool_input.get("limit_price"),
            stop_price=tool_input.get("stop_price"),
            trail=tool_input.get("trail"),
            time_in_force=tool_input.get("time_in_force"),
        )
        if isinstance(result, dict) and result.get("error"):
            return {"success": False, "error": result["error"], "message": result.get("message")}
        return {"success": True, "result": result}

    elif tool == "partial_close":
        ticker = tool_input.get("ticker")
        qty = tool_input.get("qty")
        if not all([ticker, qty]):
            return {"success": False, "error": "ticker and qty are required"}
        result = await trading_client.partial_close_position(
            api_key, api_secret, paper,
            symbol=ticker,
            qty=float(qty),
        )
        if isinstance(result, dict) and result.get("error"):
            return {"success": False, "error": result["error"], "message": result.get("message")}
        return {"success": True, "result": result}

    elif tool == "cancel_all_orders":
        result = await trading_client.cancel_all_orders(
            api_key, api_secret, paper,
        )
        if isinstance(result, dict) and result.get("error"):
            return {"success": False, "error": result["error"]}
        return {"success": True, "result": result}

    elif tool == "add_to_watchlist":
        ticker = tool_input.get("ticker")
        if not ticker:
            return {"success": False, "error": "ticker is required"}
        result = await trading_client.add_to_watchlist(
            api_key, api_secret, paper,
            symbol=ticker,
            watchlist_name=tool_input.get("watchlist_name", "YARNNN"),
        )
        if isinstance(result, dict) and result.get("error"):
            return {"success": False, "error": result["error"], "message": result.get("message")}
        return {"success": True, "result": result}

    elif tool == "remove_from_watchlist":
        ticker = tool_input.get("ticker")
        if not ticker:
            return {"success": False, "error": "ticker is required"}
        result = await trading_client.remove_from_watchlist(
            api_key, api_secret, paper,
            symbol=ticker,
            watchlist_name=tool_input.get("watchlist_name", "YARNNN"),
        )
        if isinstance(result, dict) and result.get("error"):
            return {"success": False, "error": result["error"], "message": result.get("message")}
        return {"success": True, "result": result}

    return {"success": False, "error": f"Unknown trading tool: {tool}"}


async def _handle_email_tool(auth: Any, tool: str, tool_input: dict) -> dict:
    """Handle email (Resend) platform tools (ADR-192 Phase 4)."""
    from integrations.core.resend_client import get_resend_client

    # Fetch credentials + metadata
    try:
        result = auth.client.table("platform_connections").select(
            "credentials_encrypted, metadata"
        ).eq("user_id", auth.user_id).eq("platform", "email").eq("status", "active").execute()

        if not result.data:
            return {"success": False, "error": "No active email (Resend) connection found. Connect via POST /integrations/email/connect first."}
    except Exception as e:
        return {"success": False, "error": f"Failed to fetch email credentials: {e}"}

    conn = result.data[0]
    token_manager = get_token_manager()
    try:
        api_key = token_manager.decrypt(conn["credentials_encrypted"])
    except Exception as e:
        return {"success": False, "error": f"Failed to decrypt email API key: {e}"}

    metadata = conn.get("metadata") or {}
    default_from_email = metadata.get("from_email")
    default_from_name = metadata.get("from_name")
    default_reply_to = metadata.get("reply_to")

    resend = get_resend_client()

    if tool == "send":
        to = tool_input.get("to")
        if isinstance(to, str):
            to = [to]
        subject = tool_input.get("subject")
        html = tool_input.get("html")
        if not to or not subject or not html:
            return {"success": False, "error": "to, subject, and html are required"}

        result = await resend.send(
            api_key,
            to=to,
            subject=subject,
            html=html,
            from_email=tool_input.get("from_email") or default_from_email,
            from_name=tool_input.get("from_name") or default_from_name,
            reply_to=tool_input.get("reply_to") or default_reply_to,
            cc=tool_input.get("cc"),
            bcc=tool_input.get("bcc"),
        )
        if isinstance(result, dict) and result.get("error"):
            return {"success": False, "error": result["error"], "message": result.get("detail", "")}

        # Warn if sender fallback is active (no verified domain)
        response = {"success": True, "result": result}
        if not metadata.get("has_verified_domain"):
            response["warning"] = (
                "Email sent from Resend's shared sender (onboarding@resend.dev). "
                "Verify a domain in Resend and set from_email/from_name on the "
                "connection for production-quality sending."
            )
        return response

    elif tool == "send_bulk":
        messages = tool_input.get("messages")
        if not isinstance(messages, list) or not messages:
            return {"success": False, "error": "messages (non-empty list of {to, subject, html}) is required"}

        result = await resend.send_batch(
            api_key,
            messages=messages,
            from_email=tool_input.get("from_email") or default_from_email,
            from_name=tool_input.get("from_name") or default_from_name,
        )
        response = {"success": True, "result": result}
        if not metadata.get("has_verified_domain"):
            response["warning"] = (
                "Bulk emails sent from Resend's shared sender. "
                "Verify a domain in Resend for production sending."
            )
        return response

    return {"success": False, "error": f"Unknown email tool: {tool}"}


def is_platform_tool(tool_name: str) -> bool:
    """Check if a tool name is a platform tool."""
    return tool_name.startswith("platform_")
