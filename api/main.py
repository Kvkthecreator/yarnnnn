"""
YARNNN API - Context-aware AI work platform

Single FastAPI application with route groups:
- /api/memory: Memory layer (profile, styles, entries, activity)
- /api/knowledge: Knowledge filesystem browsing (/knowledge/* in workspace_files)
- /api/work: Work ticket lifecycle
- /api/feed: Feed surface (operator timeline) — multi-actor, asynchronous, ADR-259
- /api/domains: Context domains (ADR-034)
"""

import os
import logging
from typing import Optional

import sentry_sdk
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging - ensure INFO level logs are visible
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Observability — ADR-250 Phase 1
# Sentry captures unhandled exceptions + performance traces.
# SENTRY_DSN is required in production; silently no-ops if absent (local dev).
_sentry_dsn = os.getenv("SENTRY_DSN")
if _sentry_dsn:
    sentry_sdk.init(
        dsn=_sentry_dsn,
        environment=os.getenv("ENVIRONMENT", "production"),
        traces_sample_rate=0.1,   # 10% of transactions — free tier headroom
        send_default_pii=False,   # no PII sent to Sentry
    )
    logger.info("[STARTUP] Sentry initialized (environment=%s)", os.getenv("ENVIRONMENT", "production"))
else:
    logger.info("[STARTUP] SENTRY_DSN not set — Sentry disabled")


def _validate_environment():
    """Validate required environment variables at startup. Fail fast, not mid-request."""
    required = [
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_KEY",
        "ANTHROPIC_API_KEY",
        "INTEGRATION_ENCRYPTION_KEY",
    ]
    missing = [var for var in required if not os.getenv(var)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Check your .env file or deployment config."
        )

    optional = ["LEMONSQUEEZY_API_KEY"]  # ADR-131: Google env vars removed (sunset)
    for var in optional:
        if not os.getenv(var):
            logger.warning(f"[STARTUP] Optional env var not set: {var}")


_validate_environment()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from routes import memory, feed, documents, admin, webhooks, subscription, agents, account, integrations, domains, system, recurrences, workspace, proposals, narrative, programs, alpha_trader, budget, mcp, authored, harvest, sources, emissions, member_state, lanes, shares, studio

app = FastAPI(
    title="YARNNN API",
    description="Context-aware AI work platform",
    version="5.0.0",
)

# CORS - allow frontend origins
# Note: allow_origin_regex is used for Vercel preview deployments
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://yarnnn.com",
        "https://www.yarnnn.com",
        "https://yarnnnn.vercel.app",
        "https://www.yarnnnn.vercel.app",
    ],
    allow_origin_regex=r"https://yarnnnn-.*\.vercel\.app",  # Vercel preview URLs (includes git branch deployments)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Structured JSON error responses
#
# Every error the API returns is machine-parseable JSON of the shape
#   {"error": {"code": <str>, "message": <str>, "hint": <str|null>}}
# so agents (and the frontend) never have to parse an HTML error page. This
# covers three classes: raised HTTPExceptions (4xx/5xx), request-validation
# failures (422), and otherwise-unhandled exceptions (500). See the "JSON
# error responses" agent-readiness requirement.
# ---------------------------------------------------------------------------

_STATUS_ERROR_CODES = {
    400: "bad_request",
    401: "unauthorized",
    402: "payment_required",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    502: "bad_gateway",
    503: "service_unavailable",
}


def _error_body(code: str, message: str, hint: Optional[object] = None) -> dict:
    return {"error": {"code": code, "message": message, "hint": hint}}


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Normalize raised HTTPExceptions to the structured JSON error shape.

    Preserves the original status code; derives a machine-readable `code` from
    it. `exc.detail` becomes the human `message` (it is usually already a plain
    string set by the route). Keeps any WWW-Authenticate header for 401s.
    """
    code = _STATUS_ERROR_CODES.get(exc.status_code, f"http_{exc.status_code}")
    detail = exc.detail
    message = detail if isinstance(detail, str) else "Request failed."
    body = _error_body(code, message)
    # If detail was a dict/list (structured), surface it under `hint` so nothing
    # is lost while keeping the top-level contract stable.
    if not isinstance(detail, str) and detail is not None:
        body["error"]["hint"] = detail
    return JSONResponse(
        status_code=exc.status_code,
        content=body,
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return 422 validation failures as structured JSON with per-field hints."""
    return JSONResponse(
        status_code=422,
        content=_error_body(
            "validation_error",
            "Request validation failed. Check the fields listed in `hint`.",
            hint=exc.errors(),
        ),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Last-resort handler: never leak an HTML/traceback page to a client.

    The full exception is still captured by Sentry (initialized above) and the
    server logs; the client receives a stable, opaque JSON error.
    """
    logger.exception("[UNHANDLED] %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=_error_body(
            "internal_error",
            "An unexpected error occurred. If this persists, contact support.",
        ),
    )


@app.get("/health")
async def health():
    return {"status": "ok", "version": "5.0.0"}


# Mount routers
app.include_router(memory.router, prefix="/api/memory", tags=["memory"])
app.include_router(feed.router, prefix="/api", tags=["feed"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(harvest.router, prefix="/api", tags=["harvest"])  # ADR-331
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(subscription.router, prefix="/api", tags=["subscription"])
app.include_router(subscription.webhook_router, prefix="/api", tags=["subscription-webhooks"])

# Agents routes (ADR-018)
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])

# Account management routes (Danger Zone)
app.include_router(account.router, prefix="/api", tags=["account"])

# Integration routes (ADR-026)
app.include_router(integrations.router, prefix="/api", tags=["integrations"])

# Domain routes (ADR-034)
app.include_router(domains.router, tags=["domains"])

# System/Operations status routes (ADR-072)
app.include_router(system.router, prefix="/api/system", tags=["system"])

# Tasks routes (ADR-138)
app.include_router(recurrences.router, prefix="/api/recurrences", tags=["recurrences"])
app.include_router(authored.router, prefix="/api/authored", tags=["authored"])  # ADR-333 D6
app.include_router(workspace.router, prefix="/api", tags=["workspace"])
# ADR-437 D4: the shared-artifact wedge — create/list/revoke + the /s/{token}
# accept surface (the member-invite's generous, link-based sibling).
app.include_router(shares.router, prefix="/api", tags=["shares"])
# ADR-193: approval loop — proposal list + approve/reject endpoints
app.include_router(proposals.router, prefix="/api", tags=["proposals"])
# ADR-407 Phase 3: member-experience home (shell state, read cursor, prefs)
app.include_router(member_state.router, prefix="/api", tags=["member-state"])
app.include_router(lanes.router, prefix="/api", tags=["lanes"])  # ADR-411 chat lanes
app.include_router(studio.router, prefix="/api", tags=["studio"])  # ADR-440 the Studio

# ADR-219 Commit 4: narrative filter-over-substrate for /work list view
app.include_router(narrative.router, prefix="/api/narrative", tags=["narrative"])

# ADR-225: program composition surfaces (compositor's API-side resolver)
app.include_router(programs.router, prefix="/api/programs", tags=["programs"])

# ADR-312 D9: alpha-trader program data (live brokerage + trading substrate).
# Renamed from /api/cockpit/* — trader data is program-scoped. Mounted at the
# more-specific /api/programs/alpha-trader prefix (no collision with the
# programs.router /surfaces|/activatable|/activate|/deactivate routes).
app.include_router(alpha_trader.router, prefix="/api/programs/alpha-trader", tags=["alpha-trader"])

# ADR-327: budget is the kernel governance dial (supersedes the retired pace
# dial) — the operation's dollar spend envelope. /api/pace → /api/budget.
app.include_router(budget.router, prefix="/api/budget", tags=["budget"])

# ADR-338 D4.1: sources is the standing-watch "drivers" view — declared web
# sources (_sources.yaml) paired with observed health (_watch_signal.yaml).
app.include_router(sources.router, prefix="/api/sources", tags=["sources"])
# ADR-370: emissions — the operation's outbound boundary (Context → Out lens).
# Read-only union over destination_delivery_log + notifications. No write path.
app.include_router(emissions.router, prefix="/api/emissions", tags=["emissions"])

# ADR-310 D4: MCP OAuth login callback (binds Supabase user to pending auth code)
app.include_router(mcp.router, prefix="/api/mcp", tags=["mcp"])
