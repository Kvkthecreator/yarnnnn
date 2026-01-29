"""
YARNNN API - Context-aware AI work platform

Single FastAPI application with route groups:
- /api: Projects and workspaces
- /api/context: Block and document management
- /api/work: Work ticket lifecycle
- /api/agents: Agent execution
- /api/chat: Thinking Partner conversations
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import context, projects, chat, documents, admin, webhooks, subscription

app = FastAPI(
    title="YARNNN API",
    description="Context-aware AI work platform",
    version="5.0.0",
)

# CORS - allow frontend origins
allowed_origins = [
    "http://localhost:3000",
    "https://yarnnn.com",
    "https://www.yarnnn.com",
    "https://yarnnnn.vercel.app",
    "https://yarnnnn-*.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "5.0.0"}


# Mount routers
app.include_router(projects.router, prefix="/api", tags=["projects"])
app.include_router(context.router, prefix="/api/context", tags=["context"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(subscription.router, prefix="/api", tags=["subscription"])
app.include_router(subscription.webhook_router, prefix="/api", tags=["subscription-webhooks"])

# TODO: Uncomment as implemented
# from routes import work, agents
# app.include_router(work.router, prefix="/api/work", tags=["work"])
# app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
