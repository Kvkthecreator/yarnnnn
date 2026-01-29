"""
Chat routes - Thinking Partner conversations

Endpoints:
- POST /projects/:id/chat - Send message (streaming)
- GET /projects/:id/chat/history - Get chat history
"""

import json
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

from services.supabase import UserClient
from services.extraction import extract_from_conversation
from agents.base import ContextBundle, Block, UserContextItem
from agents.thinking_partner import ThinkingPartnerAgent

router = APIRouter()


class ChatHistoryMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    content: str
    include_context: bool = True
    history: list[ChatHistoryMessage] = []


async def load_context(client, project_id: UUID, user_id: str, include_user_context: bool = True) -> ContextBundle:
    """
    Load context for ThinkingPartner (ADR-004 two-layer architecture).

    Args:
        client: Supabase client
        project_id: Project UUID
        user_id: User UUID for user context
        include_user_context: Whether to include user-level context

    Returns:
        ContextBundle with both user and project context
    """
    # Fetch project blocks
    blocks_result = client.table("blocks").select("*").eq("project_id", str(project_id)).execute()

    blocks = [
        Block(
            id=UUID(row["id"]),
            content=row["content"],
            block_type=row["block_type"],
            semantic_type=row.get("semantic_type"),
            metadata=row.get("metadata"),
        )
        for row in (blocks_result.data or [])
    ]

    # Fetch user context (sorted by importance)
    user_context = []
    if include_user_context:
        try:
            user_result = (
                client.table("user_context")
                .select("*")
                .eq("user_id", user_id)
                .order("importance", desc=True)
                .limit(20)  # Top 20 most important items
                .execute()
            )

            user_context = [
                UserContextItem(
                    id=UUID(row["id"]),
                    category=row["category"],
                    key=row["key"],
                    content=row["content"],
                    importance=row.get("importance", 0.5),
                    confidence=row.get("confidence", 0.8),
                )
                for row in (user_result.data or [])
            ]
        except Exception as e:
            # Don't fail if user_context table doesn't exist yet
            print(f"Failed to load user context: {e}")

    return ContextBundle(
        project_id=project_id,
        blocks=blocks,
        documents=[],  # TODO: Add document support
        user_context=user_context,
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


async def _background_extraction(project_id: str, user_id: str, messages: list[dict], client):
    """
    Background task for dual-stream context extraction (ADR-004).
    Extracts both user context and project blocks.
    Runs after response streaming completes, doesn't block user.
    """
    try:
        result = await extract_from_conversation(
            project_id=project_id,
            user_id=user_id,
            messages=messages,
            db_client=client,
            source_type="chat"
        )
        user_count = result.get("user_items_inserted", 0)
        project_count = result.get("project_items_inserted", 0)
        if user_count > 0 or project_count > 0:
            print(f"Extracted {user_count} user items and {project_count} project blocks from chat in project {project_id}")
    except Exception as e:
        # Log but don't fail - extraction is best-effort
        print(f"Background extraction failed for project {project_id}: {e}")


@router.post("/projects/{project_id}/chat")
async def send_message(
    project_id: UUID,
    request: ChatRequest,
    auth: UserClient,
):
    """
    Send message to Thinking Partner with streaming response.

    Loads project context (blocks) and streams the response via SSE.
    """
    # Verify project access
    project_result = auth.client.table("projects").select("id").eq("id", str(project_id)).single().execute()
    if not project_result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    # Load two-layer context (user + project)
    context = await load_context(
        auth.client,
        project_id,
        user_id=auth.user_id,
        include_user_context=request.include_context
    )

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

            # Build full message list for session save and extraction
            messages = history + [
                {"role": "user", "content": request.content},
                {"role": "assistant", "content": full_response},
            ]

            # Save session for provenance (fire and forget)
            try:
                await save_agent_session(
                    auth.client,
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
                print(f"Failed to save agent session: {e}")

            # Fire-and-forget dual-stream context extraction from conversation
            asyncio.create_task(
                _background_extraction(str(project_id), auth.user_id, messages, auth.client)
            )

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
    auth: UserClient,
    limit: int = 10,
):
    """
    Get recent chat sessions for a project.

    Returns the most recent agent sessions with their messages.
    """
    # Verify project access
    project_result = auth.client.table("projects").select("id").eq("id", str(project_id)).single().execute()
    if not project_result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    # Fetch recent sessions
    result = (
        auth.client.table("agent_sessions")
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
    auth: UserClient,
):
    """
    Get context statistics for a project.

    Returns block count and types available.
    """
    # Verify project access
    project_result = auth.client.table("projects").select("id").eq("id", str(project_id)).single().execute()
    if not project_result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    # Count blocks by type
    result = auth.client.table("blocks").select("block_type").eq("project_id", str(project_id)).execute()

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
