"""
Chat routes - Thinking Partner conversations

ADR-005: Unified memory with embeddings

Endpoints:
- POST /chat - Global chat (user-level, no project required)
- POST /projects/:id/chat - Project chat (user + project context)
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
from services.embeddings import get_embedding
from agents.base import ContextBundle, Memory
from agents.thinking_partner import ThinkingPartnerAgent

router = APIRouter()


class ChatHistoryMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    content: str
    include_context: bool = True
    history: list[ChatHistoryMessage] = []


async def load_memories(
    client,
    user_id: str,
    project_id: Optional[UUID] = None,
    query: Optional[str] = None,
    max_results: int = 20
) -> ContextBundle:
    """
    Load memories for context assembly (ADR-005).

    Uses semantic search if query provided, otherwise importance-based retrieval.

    Args:
        client: Supabase client
        user_id: User UUID
        project_id: Optional project UUID (None = user memories only)
        query: Optional query for semantic search
        max_results: Maximum memories to return

    Returns:
        ContextBundle with memories
    """
    memories = []

    try:
        if query:
            # Semantic search using embeddings
            query_embedding = await get_embedding(query)

            # Build scope filter
            if project_id:
                # User-scoped OR this project
                scope_filter = f"(project_id IS NULL OR project_id = '{project_id}')"
            else:
                # User-scoped only
                scope_filter = "project_id IS NULL"

            # Use RPC for vector search with hybrid scoring
            # Note: This requires a Supabase function, fallback to simple query
            try:
                result = client.rpc(
                    "search_memories",
                    {
                        "query_embedding": query_embedding,
                        "match_user_id": user_id,
                        "match_project_id": str(project_id) if project_id else None,
                        "match_count": max_results
                    }
                ).execute()

                for row in (result.data or []):
                    memories.append(Memory(
                        id=UUID(row["id"]),
                        content=row["content"],
                        importance=row.get("importance", 0.5),
                        tags=row.get("tags", []),
                        entities=row.get("entities", {}),
                        source_type=row.get("source_type", "chat"),
                        project_id=UUID(row["project_id"]) if row.get("project_id") else None,
                    ))
            except Exception as e:
                # Fallback to simple importance-based query
                print(f"[CONTEXT DEBUG] Semantic search failed, falling back to importance: {e}")
                query = None  # Force fallback

        if not query:
            # Simple importance-based retrieval
            if project_id:
                # Get user memories + project memories
                user_result = (
                    client.table("memories")
                    .select("*")
                    .eq("user_id", user_id)
                    .is_("project_id", "null")
                    .eq("is_active", True)
                    .order("importance", desc=True)
                    .limit(max_results // 2)
                    .execute()
                )

                project_result = (
                    client.table("memories")
                    .select("*")
                    .eq("user_id", user_id)
                    .eq("project_id", str(project_id))
                    .eq("is_active", True)
                    .order("importance", desc=True)
                    .limit(max_results // 2)
                    .execute()
                )

                rows = (user_result.data or []) + (project_result.data or [])
            else:
                # User memories only
                result = (
                    client.table("memories")
                    .select("*")
                    .eq("user_id", user_id)
                    .is_("project_id", "null")
                    .eq("is_active", True)
                    .order("importance", desc=True)
                    .limit(max_results)
                    .execute()
                )
                rows = result.data or []

            for row in rows:
                memories.append(Memory(
                    id=UUID(row["id"]),
                    content=row["content"],
                    importance=row.get("importance", 0.5),
                    tags=row.get("tags", []),
                    entities=row.get("entities", {}),
                    source_type=row.get("source_type", "chat"),
                    project_id=UUID(row["project_id"]) if row.get("project_id") else None,
                ))

    except Exception as e:
        print(f"Failed to load memories: {e}")

    bundle = ContextBundle(
        memories=memories,
        documents=[],
        project_id=project_id,
    )

    # Debug: Log what we loaded
    print(f"[CONTEXT DEBUG] Loaded {len(memories)} total memories for project={project_id}")
    print(f"[CONTEXT DEBUG] Bundle project_id: {bundle.project_id} (type: {type(bundle.project_id)})")
    print(f"[CONTEXT DEBUG] User memories: {len(bundle.user_memories)}")
    print(f"[CONTEXT DEBUG] Project memories: {len(bundle.project_memories)}")
    if memories:
        for m in memories[:3]:  # Show first 3
            print(f"[CONTEXT DEBUG]   - Memory {m.id}: project_id={m.project_id} (type: {type(m.project_id)}), content={m.content[:50]}...")

    return bundle


async def save_agent_session(
    client,
    user_id: str,
    project_id: Optional[UUID],
    agent_type: str,
    messages: list[dict],
    metadata: dict,
):
    """Save agent session for provenance. project_id can be None for global chat."""
    data = {
        "user_id": user_id,
        "agent_type": agent_type,
        "messages": messages,
        "metadata": metadata,
        "completed_at": datetime.utcnow().isoformat(),
    }
    if project_id:
        data["project_id"] = str(project_id)
    client.table("agent_sessions").insert(data).execute()


async def _background_extraction(
    user_id: str,
    messages: list[dict],
    client,
    project_id: Optional[str] = None
):
    """
    Background task for memory extraction (ADR-005).
    Runs after response streaming completes, doesn't block user.
    """
    try:
        result = await extract_from_conversation(
            user_id=user_id,
            messages=messages,
            db_client=client,
            project_id=project_id,
            source_type="chat"
        )
        user_count = result.get("user_memories_inserted", 0)
        project_count = result.get("project_memories_inserted", 0)
        if user_count > 0 or project_count > 0:
            context_type = f"project {project_id}" if project_id else "global"
            print(f"Extracted {user_count} user + {project_count} project memories from {context_type} chat")
    except Exception as e:
        print(f"Background extraction failed: {e}")


@router.post("/chat")
async def global_chat(
    request: ChatRequest,
    auth: UserClient,
):
    """
    Global chat with Thinking Partner (no project required).

    Uses user memories only. Ideal for onboarding, general questions,
    or conversations that don't belong to a specific project.
    """
    # Load user memories only (with optional semantic search on the query)
    context = await load_memories(
        auth.client,
        auth.user_id,
        project_id=None,
        query=request.content if request.include_context else None
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
                yield f"data: {json.dumps({'content': chunk})}\n\n"

            yield f"data: {json.dumps({'done': True, 'full_content': full_response})}\n\n"

            # Build full message list
            messages = history + [
                {"role": "user", "content": request.content},
                {"role": "assistant", "content": full_response},
            ]

            # Save session (no project)
            try:
                await save_agent_session(
                    auth.client,
                    auth.user_id,
                    None,  # No project
                    "thinking_partner",
                    messages,
                    {
                        "model": agent.model,
                        "context_type": "user_only",
                        "memories_count": len(context.memories),
                    },
                )
            except Exception as e:
                print(f"Failed to save agent session: {e}")

            # Fire-and-forget extraction
            asyncio.create_task(
                _background_extraction(auth.user_id, messages, auth.client, None)
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


@router.post("/projects/{project_id}/chat")
async def send_message(
    project_id: UUID,
    request: ChatRequest,
    auth: UserClient,
):
    """
    Send message to Thinking Partner with streaming response.

    Loads both user and project memories.
    """
    # Verify project access
    project_result = auth.client.table("projects").select("id").eq("id", str(project_id)).single().execute()
    if not project_result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    # Load memories (user + project)
    context = await load_memories(
        auth.client,
        auth.user_id,
        project_id=project_id,
        query=request.content if request.include_context else None
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
                yield f"data: {json.dumps({'content': chunk})}\n\n"

            yield f"data: {json.dumps({'done': True, 'full_content': full_response})}\n\n"

            # Build full message list
            messages = history + [
                {"role": "user", "content": request.content},
                {"role": "assistant", "content": full_response},
            ]

            # Save session
            try:
                await save_agent_session(
                    auth.client,
                    auth.user_id,
                    project_id,
                    "thinking_partner",
                    messages,
                    {
                        "model": agent.model,
                        "context_type": "user_and_project",
                        "memories_count": len(context.memories),
                    },
                )
            except Exception as e:
                print(f"Failed to save agent session: {e}")

            # Fire-and-forget extraction
            asyncio.create_task(
                _background_extraction(auth.user_id, messages, auth.client, str(project_id))
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

    Returns memory counts by scope.
    """
    # Verify project access
    project_result = auth.client.table("projects").select("id").eq("id", str(project_id)).single().execute()
    if not project_result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    # Count project memories
    project_mem_result = (
        auth.client.table("memories")
        .select("id", count="exact")
        .eq("project_id", str(project_id))
        .eq("is_active", True)
        .execute()
    )

    # Count user memories
    user_result = (
        auth.client.table("memories")
        .select("id", count="exact")
        .eq("user_id", auth.user_id)
        .is_("project_id", "null")
        .eq("is_active", True)
        .execute()
    )

    return {
        "project_id": str(project_id),
        "project_memories": project_mem_result.count or 0,
        "user_memories": user_result.count or 0,
        "total_memories": (project_mem_result.count or 0) + (user_result.count or 0),
    }
