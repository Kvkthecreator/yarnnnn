"""
Chat routes - Thinking Partner conversations

ADR-005: Unified memory with embeddings
ADR-006: Session and message architecture

Endpoints:
- POST /chat - Global chat (user-level, no project required)
- POST /projects/:id/chat - Project chat (user + project context)
- GET /projects/:id/chat/history - Get chat history
- GET /chat/history - Get global chat history
"""

import json
import asyncio
from fastapi import APIRouter, HTTPException, Query
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
    session_id: Optional[str] = None  # Optional: continue existing session


# =============================================================================
# Session Management (ADR-006)
# =============================================================================

async def get_or_create_session(
    client,
    user_id: str,
    project_id: Optional[UUID] = None,
    session_type: str = "thinking_partner",
    scope: str = "daily"  # "conversation", "daily", "project"
) -> dict:
    """
    Get or create a chat session using the database RPC.

    Scope behaviors:
    - conversation: Always creates new session
    - daily: Reuses today's active session
    - project: Reuses any active session for this project
    """
    try:
        result = client.rpc(
            "get_or_create_chat_session",
            {
                "p_user_id": user_id,
                "p_project_id": str(project_id) if project_id else None,
                "p_session_type": session_type,
                "p_scope": scope
            }
        ).execute()

        if result.data:
            return result.data
        raise Exception("No session returned from RPC")
    except Exception as e:
        print(f"[SESSION] RPC failed, falling back to direct insert: {e}")
        # Fallback: create session directly
        data = {
            "user_id": user_id,
            "session_type": session_type,
            "status": "active"
        }
        if project_id:
            data["project_id"] = str(project_id)

        result = client.table("chat_sessions").insert(data).execute()
        return result.data[0] if result.data else None


async def append_message(
    client,
    session_id: str,
    role: str,
    content: str,
    metadata: Optional[dict] = None
) -> dict:
    """Append a message to a session using the database RPC."""
    try:
        result = client.rpc(
            "append_session_message",
            {
                "p_session_id": session_id,
                "p_role": role,
                "p_content": content,
                "p_metadata": metadata or {}
            }
        ).execute()
        return result.data
    except Exception as e:
        print(f"[SESSION] RPC append failed, falling back to direct insert: {e}")
        # Fallback: direct insert with manual sequence
        seq_result = client.table("session_messages")\
            .select("sequence_number")\
            .eq("session_id", session_id)\
            .order("sequence_number", desc=True)\
            .limit(1)\
            .execute()

        next_seq = 1
        if seq_result.data:
            next_seq = seq_result.data[0]["sequence_number"] + 1

        result = client.table("session_messages").insert({
            "session_id": session_id,
            "role": role,
            "content": content,
            "sequence_number": next_seq,
            "metadata": metadata or {}
        }).execute()
        return result.data[0] if result.data else None


async def get_session_messages(
    client,
    session_id: str,
    limit: int = 50
) -> list[dict]:
    """Get messages for a session, ordered by sequence."""
    result = client.table("session_messages")\
        .select("*")\
        .eq("session_id", session_id)\
        .order("sequence_number")\
        .limit(limit)\
        .execute()
    return result.data or []


# =============================================================================
# Memory Loading (ADR-005)
# =============================================================================

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
    """
    memories = []

    try:
        use_semantic = query is not None

        if use_semantic:
            try:
                query_embedding = await get_embedding(query)
                result = client.rpc(
                    "search_memories",
                    {
                        "query_embedding": query_embedding,
                        "match_user_id": user_id,
                        "match_project_id": str(project_id) if project_id else None,
                        "match_count": max_results,
                        "similarity_threshold": 0.0
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
                print(f"[CONTEXT] Semantic search returned {len(memories)} memories")
            except Exception as e:
                print(f"[CONTEXT] Semantic search failed, falling back: {e}")
                use_semantic = False

        if not use_semantic:
            if project_id:
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
        print(f"[CONTEXT] Failed to load memories: {e}")

    bundle = ContextBundle(
        memories=memories,
        documents=[],
        project_id=project_id,
    )

    print(f"[CONTEXT] Loaded {len(memories)} memories (user={len(bundle.user_memories)}, project={len(bundle.project_memories)})")
    return bundle


# =============================================================================
# Background Extraction
# =============================================================================

async def _background_extraction(
    user_id: str,
    messages: list[dict],
    client,
    project_id: Optional[str] = None
):
    """Background task for memory extraction (ADR-005)."""
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
            print(f"[EXTRACTION] {user_count} user + {project_count} project memories from {context_type}")
    except Exception as e:
        print(f"[EXTRACTION] Failed: {e}")


# =============================================================================
# Chat Endpoints
# =============================================================================

@router.post("/chat")
async def global_chat(
    request: ChatRequest,
    auth: UserClient,
):
    """
    Global chat with Thinking Partner (no project required).
    Uses user memories only. Session is reused daily.
    """
    # Get or create session (daily scope for global chat)
    session = await get_or_create_session(
        auth.client,
        auth.user_id,
        project_id=None,
        scope="daily"
    )
    session_id = session["id"]

    # Load existing messages from session
    existing_messages = await get_session_messages(auth.client, session_id)
    history = [{"role": m["role"], "content": m["content"]} for m in existing_messages]

    # Load user memories
    context = await load_memories(
        auth.client,
        auth.user_id,
        project_id=None,
        query=request.content if request.include_context else None
    )

    agent = ThinkingPartnerAgent()

    async def response_stream():
        full_response = ""

        try:
            # Append user message to session
            await append_message(auth.client, session_id, "user", request.content)

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

            # Append assistant response to session
            await append_message(
                auth.client,
                session_id,
                "assistant",
                full_response,
                {"model": agent.model}
            )

            yield f"data: {json.dumps({'done': True, 'session_id': session_id})}\n\n"

            # Fire-and-forget extraction
            messages_for_extraction = history + [
                {"role": "user", "content": request.content},
                {"role": "assistant", "content": full_response},
            ]
            asyncio.create_task(
                _background_extraction(auth.user_id, messages_for_extraction, auth.client, None)
            )

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        response_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/projects/{project_id}/chat")
async def project_chat(
    project_id: UUID,
    request: ChatRequest,
    auth: UserClient,
):
    """
    Project chat with Thinking Partner.
    Loads both user and project memories. Session is reused daily per project.
    """
    # Verify project access
    project_result = auth.client.table("projects").select("id").eq("id", str(project_id)).single().execute()
    if not project_result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get or create session (daily scope)
    session = await get_or_create_session(
        auth.client,
        auth.user_id,
        project_id=project_id,
        scope="daily"
    )
    session_id = session["id"]

    # Load existing messages from session
    existing_messages = await get_session_messages(auth.client, session_id)
    history = [{"role": m["role"], "content": m["content"]} for m in existing_messages]

    # Load memories (user + project)
    context = await load_memories(
        auth.client,
        auth.user_id,
        project_id=project_id,
        query=request.content if request.include_context else None
    )

    agent = ThinkingPartnerAgent()

    async def response_stream():
        full_response = ""

        try:
            # Append user message to session
            await append_message(auth.client, session_id, "user", request.content)

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

            # Append assistant response to session
            await append_message(
                auth.client,
                session_id,
                "assistant",
                full_response,
                {"model": agent.model}
            )

            yield f"data: {json.dumps({'done': True, 'session_id': session_id})}\n\n"

            # Fire-and-forget extraction
            messages_for_extraction = history + [
                {"role": "user", "content": request.content},
                {"role": "assistant", "content": full_response},
            ]
            asyncio.create_task(
                _background_extraction(auth.user_id, messages_for_extraction, auth.client, str(project_id))
            )

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        response_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/chat/history")
async def get_global_chat_history(
    auth: UserClient,
    limit: int = Query(default=1, le=10),
):
    """
    Get global chat history (no project).
    Returns the most recent session(s) with messages.
    """
    # Fetch recent global sessions
    sessions_result = (
        auth.client.table("chat_sessions")
        .select("*")
        .eq("user_id", auth.user_id)
        .is_("project_id", "null")
        .eq("session_type", "thinking_partner")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    sessions = []
    for session in (sessions_result.data or []):
        # Get messages for each session
        messages_result = (
            auth.client.table("session_messages")
            .select("id, role, content, sequence_number, created_at")
            .eq("session_id", session["id"])
            .order("sequence_number")
            .execute()
        )
        sessions.append({
            **session,
            "messages": messages_result.data or []
        })

    return {"sessions": sessions}


@router.get("/projects/{project_id}/chat/history")
async def get_project_chat_history(
    project_id: UUID,
    auth: UserClient,
    limit: int = Query(default=1, le=10),
):
    """
    Get chat history for a project.
    Returns the most recent session(s) with messages.
    """
    # Verify project access
    project_result = auth.client.table("projects").select("id").eq("id", str(project_id)).single().execute()
    if not project_result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    # Fetch recent project sessions
    sessions_result = (
        auth.client.table("chat_sessions")
        .select("*")
        .eq("user_id", auth.user_id)
        .eq("project_id", str(project_id))
        .eq("session_type", "thinking_partner")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    sessions = []
    for session in (sessions_result.data or []):
        # Get messages for each session
        messages_result = (
            auth.client.table("session_messages")
            .select("id, role, content, sequence_number, created_at")
            .eq("session_id", session["id"])
            .order("sequence_number")
            .execute()
        )
        sessions.append({
            **session,
            "messages": messages_result.data or []
        })

    return {
        "sessions": sessions,
        "project_id": str(project_id),
    }


@router.get("/projects/{project_id}/context/stats")
async def get_context_stats(
    project_id: UUID,
    auth: UserClient,
):
    """Get context statistics for a project."""
    project_result = auth.client.table("projects").select("id").eq("id", str(project_id)).single().execute()
    if not project_result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    project_mem_result = (
        auth.client.table("memories")
        .select("id", count="exact")
        .eq("project_id", str(project_id))
        .eq("is_active", True)
        .execute()
    )

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
