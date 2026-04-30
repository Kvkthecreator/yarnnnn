"""
YARNNN API - Context-aware AI work platform

Single FastAPI application with route groups:
- /api/memory: Memory layer (profile, styles, entries, activity)
- /api/knowledge: Knowledge filesystem browsing (/knowledge/* in workspace_files)
- /api/work: Work ticket lifecycle
- /api/chat: Thinking Partner conversations
- /api/domains: Context domains (ADR-034)
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging - ensure INFO level logs are visible
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import memory, chat, documents, admin, webhooks, subscription, agents, account, integrations, domains, system, recurrences, workspace, proposals, narrative, programs, cockpit

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


@app.get("/health")
async def health():
    return {"status": "ok", "version": "5.0.0"}


# Mount routers
app.include_router(memory.router, prefix="/api/memory", tags=["memory"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
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
app.include_router(workspace.router, prefix="/api", tags=["workspace"])
# ADR-193: approval loop — proposal list + approve/reject endpoints
app.include_router(proposals.router, prefix="/api", tags=["proposals"])

# ADR-219 Commit 4: narrative filter-over-substrate for /work list view
app.include_router(narrative.router, prefix="/api/narrative", tags=["narrative"])

# ADR-225: cockpit composition surfaces (compositor's API-side resolver)
app.include_router(programs.router, prefix="/api/programs", tags=["programs"])

# ADR-242: cockpit operator-facing surfaces (Alpaca account snapshot etc.)
app.include_router(cockpit.router, prefix="/api/cockpit", tags=["cockpit"])
