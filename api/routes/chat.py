"""
Chat routes - Thinking Partner conversations

ADR-005: Unified memory with embeddings
ADR-006: Session and message architecture
ADR-007: Tool use for project authority (unified streaming + tools)

Endpoints:
- POST /chat - Global chat with streaming + tools (user-level, no project required)
- POST /projects/:id/chat - Project chat with streaming + tools
- GET /chat/history - Get global chat history
- GET /projects/:id/chat/history - Get project chat history
"""

import json
import asyncio
import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

from services.supabase import UserClient

logger = logging.getLogger(__name__)
from services.extraction import extract_from_conversation
from services.embeddings import get_embedding
from agents.base import ContextBundle, Memory
from agents.thinking_partner import ThinkingPartnerAgent

router = APIRouter()


class ChatHistoryMessage(BaseModel):
    role: str
    content: str


class SurfaceContext(BaseModel):
    """Surface context for TP - what the user is currently viewing."""
    type: str  # e.g., "deliverable-review", "work-output", "idle"
    deliverableId: Optional[str] = None
    versionId: Optional[str] = None
    workId: Optional[str] = None
    outputId: Optional[str] = None
    projectId: Optional[str] = None
    memoryId: Optional[str] = None
    documentId: Optional[str] = None
    # Additional fields as needed based on DeskSurface types


class ChatRequest(BaseModel):
    content: str
    include_context: bool = True
    session_id: Optional[str] = None  # Optional: continue existing session
    surface_context: Optional[SurfaceContext] = None  # ADR-023: What user is viewing
    project_id: Optional[str] = None  # ADR-024: Selected project for context routing


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
    except Exception:
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
    except Exception:
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
            except Exception:
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

    except Exception:
        pass  # Continue with empty memories on error

    return ContextBundle(
        memories=memories,
        documents=[],
        project_id=project_id,
    )


# =============================================================================
# Surface Context Loading (ADR-023)
# =============================================================================

async def load_surface_content(
    client,
    user_id: str,
    surface: SurfaceContext
) -> Optional[str]:
    """
    Load the actual content of the surface the user is viewing.

    Returns a formatted string describing what the user is looking at,
    suitable for injection into the TP system prompt.
    """
    try:
        surface_type = surface.type

        if surface_type == "deliverable-review" and surface.deliverableId and surface.versionId:
            # User is reviewing a deliverable version - fetch the content
            deliverable_result = client.table("deliverables")\
                .select("title, deliverable_type")\
                .eq("id", surface.deliverableId)\
                .eq("user_id", user_id)\
                .single()\
                .execute()

            version_result = client.table("deliverable_versions")\
                .select("content, version_number, status")\
                .eq("id", surface.versionId)\
                .single()\
                .execute()

            if deliverable_result.data and version_result.data:
                d = deliverable_result.data
                v = version_result.data
                content = v.get("content", "")
                # Truncate if too long
                if len(content) > 8000:
                    content = content[:8000] + "\n\n[Content truncated...]"

                return f"""## Currently Viewing: {d['title']} (v{v['version_number']})
Type: {d.get('deliverable_type', 'custom').replace('_', ' ').title()}
Status: {v['status']}

### Content:
{content}
"""

        elif surface_type == "deliverable-detail" and surface.deliverableId:
            # User is viewing deliverable details (not content)
            result = client.table("deliverables")\
                .select("title, deliverable_type, status, schedule, type_config")\
                .eq("id", surface.deliverableId)\
                .eq("user_id", user_id)\
                .single()\
                .execute()

            if result.data:
                d = result.data
                return f"""## Currently Viewing: {d['title']} (Deliverable Detail)
Type: {d.get('deliverable_type', 'custom').replace('_', ' ').title()}
Status: {d['status']}
Schedule: {d.get('schedule', {})}
"""

        elif surface_type == "work-output" and surface.workId:
            # User is viewing work output
            work_result = client.table("work_tickets")\
                .select("task, agent_type, status")\
                .eq("id", surface.workId)\
                .eq("user_id", user_id)\
                .single()\
                .execute()

            # Get the latest output
            output_result = client.table("work_outputs")\
                .select("title, content, output_type")\
                .eq("ticket_id", surface.workId)\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()

            if work_result.data:
                w = work_result.data
                content_section = ""
                if output_result.data:
                    o = output_result.data[0]
                    content = o.get("content", "")
                    if len(content) > 8000:
                        content = content[:8000] + "\n\n[Content truncated...]"
                    content_section = f"\n### Output: {o.get('title', 'Untitled')}\n{content}"

                return f"""## Currently Viewing: Work Output
Task: {w['task'][:200]}
Agent: {w['agent_type']}
Status: {w['status']}{content_section}
"""

        elif surface_type == "context-browser":
            # User is browsing their context/memories - just note it
            return "## Currently Viewing: Context Browser\nUser is browsing their stored memories and context."

        elif surface_type == "project-detail" and surface.projectId:
            result = client.table("projects")\
                .select("name, description")\
                .eq("id", surface.projectId)\
                .single()\
                .execute()

            if result.data:
                p = result.data
                return f"""## Currently Viewing: Project - {p['name']}
Description: {p.get('description', 'No description')}
"""

        # For list views and idle, no specific content needed
        return None

    except Exception as e:
        logger.warning(f"Failed to load surface content: {e}")
        return None


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
    except Exception:
        pass  # Background extraction failures are non-critical


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
    Supports tool use with streaming (ADR-007).
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
    history = [{"role": m["role"], "content": m.get("content") or ""} for m in existing_messages]

    # ADR-024: Parse selected project context
    selected_project_id = UUID(request.project_id) if request.project_id else None
    selected_project_name = None
    if selected_project_id:
        try:
            project_result = auth.client.table("projects")\
                .select("name")\
                .eq("id", str(selected_project_id))\
                .single()\
                .execute()
            if project_result.data:
                selected_project_name = project_result.data["name"]
                logger.info(f"[TP] Selected project context: {selected_project_name} ({selected_project_id})")
        except Exception as e:
            logger.warning(f"[TP] Failed to load project name: {e}")

    # Load memories - include project context if selected (ADR-024)
    context = await load_memories(
        auth.client,
        auth.user_id,
        project_id=selected_project_id,
        query=request.content if request.include_context else None
    )

    # Check if user has any deliverables (for onboarding mode)
    is_onboarding = False
    try:
        deliverables_result = auth.client.table("deliverables")\
            .select("id")\
            .eq("user_id", auth.user_id)\
            .neq("status", "archived")\
            .limit(1)\
            .execute()
        is_onboarding = len(deliverables_result.data or []) == 0
    except Exception:
        pass  # Default to non-onboarding if check fails

    # ADR-023: Load surface content if user is viewing something specific
    surface_content = None
    if request.surface_context:
        logger.info(f"[TP] Surface context received: {request.surface_context.type}")
        surface_content = await load_surface_content(
            auth.client,
            auth.user_id,
            request.surface_context
        )
        if surface_content:
            logger.info(f"[TP] Loaded surface content ({len(surface_content)} chars)")

    agent = ThinkingPartnerAgent()

    async def response_stream():
        full_response = ""
        tools_used = []

        try:
            # Append user message to session
            await append_message(auth.client, session_id, "user", request.content)
            logger.info(f"[TP-STREAM] Starting stream for message: {request.content[:50]}...")

            async for event in agent.execute_stream_with_tools(
                task=request.content,
                context=context,
                auth=auth,
                parameters={
                    "include_context": request.include_context,
                    "history": history,
                    "is_onboarding": is_onboarding,
                    "surface_content": surface_content,  # ADR-023: What user is viewing
                    "selected_project_id": str(selected_project_id) if selected_project_id else None,  # ADR-024
                    "selected_project_name": selected_project_name,  # ADR-024
                },
            ):
                if event.type == "text":
                    full_response += event.content
                    yield f"data: {json.dumps({'content': event.content})}\n\n"
                elif event.type == "tool_use":
                    tools_used.append(event.content["name"])
                    msg = f"[TP-STREAM] Tool use: {event.content['name']}"
                    print(msg, flush=True)
                    logger.info(msg)
                    yield f"data: {json.dumps({'tool_use': event.content})}\n\n"
                elif event.type == "tool_result":
                    result = event.content.get("result", {})
                    ui_action = result.get("ui_action")
                    msg = f"[TP-STREAM] Tool result for {event.content.get('name')}: ui_action={ui_action}, success={result.get('success')}"
                    print(msg, flush=True)
                    logger.info(msg)
                    yield f"data: {json.dumps({'tool_result': event.content})}\n\n"
                elif event.type == "done":
                    msg = f"[TP-STREAM] Stream done, tools_used={tools_used}"
                    print(msg, flush=True)
                    logger.info(msg)
                    pass  # Will send done event after saving

            # Append assistant response to session
            await append_message(
                auth.client,
                session_id,
                "assistant",
                full_response,
                {"model": agent.model, "tools_used": tools_used}
            )

            yield f"data: {json.dumps({'done': True, 'session_id': session_id, 'tools_used': tools_used})}\n\n"

            # Fire-and-forget extraction
            messages_for_extraction = history + [
                {"role": "user", "content": request.content},
                {"role": "assistant", "content": full_response},
            ]
            asyncio.create_task(
                _background_extraction(auth.user_id, messages_for_extraction, auth.client, None)
            )

        except Exception as e:
            import traceback
            error_msg = f"[TP-STREAM] Error: {type(e).__name__}: {str(e)}"
            print(error_msg, flush=True)
            logger.error(error_msg)
            logger.error(f"[TP-STREAM] Traceback: {traceback.format_exc()}")
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
    Supports tool use with streaming (ADR-007).
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
    history = [{"role": m["role"], "content": m.get("content") or ""} for m in existing_messages]

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
        tools_used = []

        try:
            # Append user message to session
            await append_message(auth.client, session_id, "user", request.content)

            async for event in agent.execute_stream_with_tools(
                task=request.content,
                context=context,
                auth=auth,
                parameters={
                    "include_context": request.include_context,
                    "history": history,
                },
            ):
                if event.type == "text":
                    full_response += event.content
                    yield f"data: {json.dumps({'content': event.content})}\n\n"
                elif event.type == "tool_use":
                    tools_used.append(event.content["name"])
                    yield f"data: {json.dumps({'tool_use': event.content})}\n\n"
                elif event.type == "tool_result":
                    yield f"data: {json.dumps({'tool_result': event.content})}\n\n"
                elif event.type == "done":
                    pass  # Will send done event after saving

            # Append assistant response to session
            await append_message(
                auth.client,
                session_id,
                "assistant",
                full_response,
                {"model": agent.model, "tools_used": tools_used}
            )

            yield f"data: {json.dumps({'done': True, 'session_id': session_id, 'tools_used': tools_used})}\n\n"

            # Fire-and-forget extraction
            messages_for_extraction = history + [
                {"role": "user", "content": request.content},
                {"role": "assistant", "content": full_response},
            ]
            asyncio.create_task(
                _background_extraction(auth.user_id, messages_for_extraction, auth.client, str(project_id))
            )

        except Exception as e:
            import traceback
            error_msg = f"[TP-STREAM] Project chat error: {type(e).__name__}: {str(e)}"
            print(error_msg, flush=True)
            logger.error(error_msg)
            logger.error(f"[TP-STREAM] Traceback: {traceback.format_exc()}")
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


# =============================================================================
# Skills (ADR-025 Claude Code Agentic Alignment)
# =============================================================================

@router.get("/skills")
async def list_skills():
    """
    List available skills (slash commands) for TP.

    ADR-025: Skills are packaged workflows that expand to system prompts.
    This endpoint returns the list for UI autocomplete/picker.

    No auth required - skills are public metadata.
    """
    from services.skills import list_available_skills, SKILLS

    skills = list_available_skills()

    # Add tier information for UI filtering
    enriched_skills = []
    for skill in skills:
        skill_def = SKILLS.get(skill["name"], {})
        enriched_skills.append({
            **skill,
            "tier": skill_def.get("tier", "core"),  # "core" or "beta"
            "trigger_patterns": skill_def.get("trigger_patterns", []),
        })

    return {
        "skills": enriched_skills,
        "total": len(enriched_skills),
    }
