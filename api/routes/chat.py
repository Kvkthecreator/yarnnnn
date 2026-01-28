"""
Chat routes - Thinking Partner conversations

Endpoints:
- POST /projects/:id/chat - Send message (streaming)
- GET /projects/:id/chat/history - Get chat history
"""

import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

from services.supabase import UserClient
from agents.base import ContextBundle, Block
from agents.thinking_partner import ThinkingPartnerAgent

router = APIRouter()


class ChatHistoryMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    content: str
    include_context: bool = True
    history: list[ChatHistoryMessage] = []


async def load_context(client, project_id: UUID) -> ContextBundle:
    """Load project blocks as context."""
    # Fetch blocks for this project
    result = client.table("blocks").select("*").eq("project_id", str(project_id)).execute()

    blocks = [
        Block(
            id=UUID(row["id"]),
            content=row["content"],
            block_type=row["block_type"],
            metadata=row.get("metadata"),
        )
        for row in (result.data or [])
    ]

    return ContextBundle(
        project_id=project_id,
        blocks=blocks,
        documents=[],  # TODO: Add document support
    )


async def save_agent_session(
    client,
    project_id: UUID,
    agent_type: str,
    messages: list[dict],
    metadata: dict,
):
    """Save agent session for provenance."""
    client.table("agent_sessions").insert({
        "project_id": str(project_id),
        "agent_type": agent_type,
        "messages": messages,
        "metadata": metadata,
        "completed_at": datetime.utcnow().isoformat(),
    }).execute()


@router.post("/projects/{project_id}/chat")
async def send_message(
    project_id: UUID,
    request: ChatRequest,
    client: UserClient,
):
    """
    Send message to Thinking Partner with streaming response.

    Loads project context (blocks) and streams the response via SSE.
    """
    # Verify project access
    project_result = client.table("projects").select("id").eq("id", str(project_id)).single().execute()
    if not project_result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    # Load context
    context = await load_context(client, project_id)

    # Create agent
    agent = ThinkingPartnerAgent()

    # Convert history to dict format
    history = [{"role": msg.role, "content": msg.content} for msg in request.history]

    async def response_stream():
        full_response = ""

        try:
            async for chunk in agent.execute_stream(
                task=request.content,
                context=context,
                parameters={
                    "include_context": request.include_context,
                    "history": history,
                },
            ):
                full_response += chunk
                # SSE format
                yield f"data: {json.dumps({'content': chunk})}\n\n"

            # Send done event
            yield f"data: {json.dumps({'done': True, 'full_content': full_response})}\n\n"

            # Save session for provenance (fire and forget)
            try:
                messages = history + [
                    {"role": "user", "content": request.content},
                    {"role": "assistant", "content": full_response},
                ]
                await save_agent_session(
                    client,
                    project_id,
                    "thinking_partner",
                    messages,
                    {
                        "model": agent.model,
                        "context_blocks": len(context.blocks),
                        "include_context": request.include_context,
                    },
                )
            except Exception as e:
                # Don't fail the response if session save fails
                print(f"Failed to save agent session: {e}")

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        response_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/projects/{project_id}/chat/history")
async def get_chat_history(
    project_id: UUID,
    client: UserClient,
    limit: int = 10,
):
    """
    Get recent chat sessions for a project.

    Returns the most recent agent sessions with their messages.
    """
    # Verify project access
    project_result = client.table("projects").select("id").eq("id", str(project_id)).single().execute()
    if not project_result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    # Fetch recent sessions
    result = (
        client.table("agent_sessions")
        .select("*")
        .eq("project_id", str(project_id))
        .eq("agent_type", "thinking_partner")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return {
        "sessions": result.data or [],
        "project_id": str(project_id),
    }


@router.get("/projects/{project_id}/context/stats")
async def get_context_stats(
    project_id: UUID,
    client: UserClient,
):
    """
    Get context statistics for a project.

    Returns block count and types available.
    """
    # Verify project access
    project_result = client.table("projects").select("id").eq("id", str(project_id)).single().execute()
    if not project_result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    # Count blocks by type
    result = client.table("blocks").select("block_type").eq("project_id", str(project_id)).execute()

    blocks = result.data or []
    type_counts = {}
    for block in blocks:
        bt = block["block_type"]
        type_counts[bt] = type_counts.get(bt, 0) + 1

    return {
        "project_id": str(project_id),
        "total_blocks": len(blocks),
        "blocks_by_type": type_counts,
    }
