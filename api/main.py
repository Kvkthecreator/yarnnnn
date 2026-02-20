"""
YARNNN API - Context-aware AI work platform

Single FastAPI application with route groups:
- /api/memory: Memory layer (profile, styles, entries, activity)
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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import memory, chat, documents, admin, webhooks, subscription, work, deliverables, account, integrations, domains, signal_processing, jobs

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

# Work routes (ADR-009)
app.include_router(work.router, prefix="/api/work", tags=["work"])

# Deliverables routes (ADR-018)
app.include_router(deliverables.router, prefix="/api/deliverables", tags=["deliverables"])

# Account management routes (Danger Zone)
app.include_router(account.router, prefix="/api", tags=["account"])

# Integration routes (ADR-026)
app.include_router(integrations.router, prefix="/api", tags=["integrations"])

# Domain routes (ADR-034)
app.include_router(domains.router, tags=["domains"])

# Signal processing routes (ADR-068)
app.include_router(signal_processing.router, prefix="/api", tags=["signal-processing"])

# Jobs/Operations status routes (ADR-072)
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
