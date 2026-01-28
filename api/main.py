"""
YARNNN API - Context-aware AI work platform

Single FastAPI application with 4 route groups:
- /context: Block and document management
- /work: Work ticket lifecycle
- /agents: Agent execution
- /chat: Thinking Partner conversations
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="YARNNN API",
    description="Context-aware AI work platform",
    version="5.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Add production URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "5.0.0"}


# Route imports (uncomment as implemented)
# from routes import context, work, agents, chat
# app.include_router(context.router, prefix="/api/context", tags=["context"])
# app.include_router(work.router, prefix="/api/work", tags=["work"])
# app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
# app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
