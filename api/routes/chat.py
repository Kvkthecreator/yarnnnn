"""
Chat routes - Thinking Partner conversations

ADR-005: Unified memory with embeddings
ADR-006: Session and message architecture
ADR-007: Tool use for TP authority (unified streaming + tools)
ADR-034: Domain-based context scoping

Endpoints:
- POST /chat - Global chat with streaming + tools
- GET /chat/history - Get global chat history
- GET /skills - List available TP skills
"""

import json
import asyncio
import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Literal
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
    memoryId: Optional[str] = None
    documentId: Optional[str] = None
    domainId: Optional[str] = None  # ADR-034: Domain scoping
    # Additional fields as needed based on DeskSurface types


class ImageAttachment(BaseModel):
    """Image sent inline as base64 (not stored, ephemeral like Claude Code)."""
    type: Literal["base64"] = "base64"
    media_type: Literal["image/jpeg", "image/png", "image/gif", "image/webp"]
    data: str  # Base64-encoded image data


class ChatRequest(BaseModel):
    content: str
    include_context: bool = True
    session_id: Optional[str] = None  # Optional: continue existing session
    surface_context: Optional[SurfaceContext] = None  # ADR-023: What user is viewing
    images: Optional[list[ImageAttachment]] = None  # Images attached to message (ephemeral)


# =============================================================================
# Session Management (ADR-006)
# =============================================================================

async def get_or_create_session(
    client,
    user_id: str,
    session_type: str = "thinking_partner",
    scope: str = "daily"  # "conversation", "daily"
) -> dict:
    """
    Get or create a chat session using the database RPC.

    Scope behaviors:
    - conversation: Always creates new session
    - daily: Reuses today's active session
    """
    try:
        result = client.rpc(
            "get_or_create_chat_session",
            {
                "p_user_id": user_id,
                "p_project_id": None,
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
# History Building (Claude Code Alignment)
# =============================================================================

# Maximum messages to include in history to prevent context overflow
# This is ~15 conversation turns (user + assistant pairs)
MAX_HISTORY_MESSAGES = 30


def build_history_for_claude(
    messages: list[dict],
    use_structured_format: bool = True
) -> list[dict]:
    """
    Build conversation history in Anthropic message format.

    Claude Code uses structured tool_use/tool_result blocks for better coherence.
    This function reconstructs that format from our stored tool_history metadata.

    Args:
        messages: Raw session messages from database
        use_structured_format: If True, use tool_use/tool_result blocks.
                              If False, use simplified text-based format.

    Returns:
        List of messages in Anthropic API format
    """
    # Limit history to prevent context overflow
    # Take the most recent messages, but ensure we start with a user message
    if len(messages) > MAX_HISTORY_MESSAGES:
        messages = messages[-MAX_HISTORY_MESSAGES:]
        # Ensure history starts with user message (Anthropic requirement)
        while messages and messages[0].get("role") == "assistant":
            messages = messages[1:]

    history = []

    for m in messages:
        role = m["role"]
        content = m.get("content") or ""
        metadata = m.get("metadata") or {}
        tool_history = metadata.get("tool_history", [])

        if role == "assistant" and tool_history and use_structured_format:
            # Build structured content with tool_use blocks
            # This matches Claude Code's format for better model understanding
            assistant_content = []
            tool_results = []
            tool_call_index = 0

            for item in tool_history:
                if item.get("type") == "tool_call":
                    # Use consistent index for tool_use and tool_result matching
                    tool_id = f"tool_{item['name']}_{tool_call_index}"

                    # Add tool_use block to assistant content
                    assistant_content.append({
                        "type": "tool_use",
                        "id": tool_id,
                        "name": item["name"],
                        "input": _parse_input_summary(item.get("input_summary", "{}"))
                    })

                    # Add corresponding tool_result
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": item.get("result_summary", "Success")
                    })

                    tool_call_index += 1
                elif item.get("type") == "text" and item.get("content"):
                    # Add text block
                    assistant_content.append({
                        "type": "text",
                        "text": item["content"]
                    })

            if tool_results:
                # Add assistant message with tool_use blocks
                history.append({
                    "role": "assistant",
                    "content": assistant_content if assistant_content else [{"type": "text", "text": content}]
                })

                # Add tool_result blocks as next "user" turn
                history.append({
                    "role": "user",
                    "content": tool_results
                })
            elif assistant_content:
                # Just text content, no tools
                history.append({
                    "role": "assistant",
                    "content": assistant_content
                })
            else:
                # Fallback to simple text
                history.append({"role": role, "content": content})

        elif role == "assistant" and tool_history:
            # Fallback: simplified text format with [Called X] prefix
            tool_summaries = []
            text_content = ""

            for item in tool_history:
                if item.get("type") == "tool_call":
                    tool_summaries.append(f"[Called {item['name']}]")
                elif item.get("type") == "text":
                    text_content = item.get("content", "")

            if tool_summaries:
                content = " ".join(tool_summaries) + "\n" + text_content
            elif text_content:
                content = text_content

            history.append({"role": role, "content": content})
        else:
            # Regular message (user or assistant without tools)
            history.append({"role": role, "content": content})

    return history


def _parse_input_summary(input_summary: str) -> dict:
    """Parse input_summary back to dict, handling truncation gracefully."""
    try:
        # Handle case where it's already a dict representation
        if input_summary.startswith("{") and input_summary.endswith("}"):
            import ast
            return ast.literal_eval(input_summary)
        return {}
    except (ValueError, SyntaxError):
        # If parsing fails, return empty dict
        return {}


# =============================================================================
# Memory Loading (ADR-005, ADR-034)
# =============================================================================

async def load_memories(
    client,
    user_id: str,
    domain_id: Optional[UUID] = None,
    query: Optional[str] = None,
    max_results: int = 20
) -> ContextBundle:
    """
    Load memories for context assembly (ADR-005, ADR-034).

    Domain scoping (ADR-034):
    - If domain_id is provided: searches domain + default domain (user profile)
    - If domain_id is None: searches all user's memories

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
                        "match_domain_id": str(domain_id) if domain_id else None,
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
                        domain_id=UUID(row["domain_id"]) if row.get("domain_id") else None,
                    ))
            except Exception:
                use_semantic = False

        if not use_semantic:
            # Use the get_memories_by_importance RPC for domain-scoped retrieval
            result = client.rpc(
                "get_memories_by_importance",
                {
                    "p_user_id": user_id,
                    "p_domain_id": str(domain_id) if domain_id else None,
                    "p_limit": max_results
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
                    domain_id=UUID(row["domain_id"]) if row.get("domain_id") else None,
                ))

    except Exception:
        pass  # Continue with empty memories on error

    return ContextBundle(
        memories=memories,
        documents=[],
        domain_id=domain_id,
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
    domain_id: Optional[str] = None
):
    """Background task for memory extraction (ADR-005, ADR-034)."""
    try:
        result = await extract_from_conversation(
            user_id=user_id,
            messages=messages,
            db_client=client,
            source_type="chat",
            domain_id=domain_id
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
    Global chat with Thinking Partner.
    Uses user memories only. Session is reused daily.
    Supports tool use with streaming (ADR-007).
    """
    # Get or create session (daily scope for global chat)
    session = await get_or_create_session(
        auth.client,
        auth.user_id,
        scope="daily"
    )
    session_id = session["id"]

    # Load existing messages from session and build history
    # Using simple text format for robustness - structured format had ID mismatch issues
    # Limited to MAX_HISTORY_MESSAGES to prevent context overflow
    existing_messages = await get_session_messages(auth.client, session_id)
    history = build_history_for_claude(existing_messages, use_structured_format=False)
    logger.info(f"[TP] Loaded {len(existing_messages)} messages, built {len(history)} history entries")

    # ADR-034: Determine active domain from context
    # Priority: surface deliverable > only-one-domain > none (search all)
    active_domain_id = None
    active_domain_name = None

    # Get domain from surface context if viewing a deliverable
    deliverable_id_for_domain = None
    if request.surface_context and request.surface_context.deliverableId:
        deliverable_id_for_domain = request.surface_context.deliverableId

    if deliverable_id_for_domain:
        try:
            domain_result = auth.client.rpc(
                "get_deliverable_domain",
                {"p_deliverable_id": deliverable_id_for_domain}
            ).execute()
            if domain_result.data:
                active_domain_id = UUID(domain_result.data)
                # Get domain name
                domain_name_result = auth.client.table("context_domains")\
                    .select("name")\
                    .eq("id", str(active_domain_id))\
                    .single()\
                    .execute()
                if domain_name_result.data:
                    active_domain_name = domain_name_result.data["name"]
                logger.info(f"[TP] Active domain from deliverable: {active_domain_name} ({active_domain_id})")
        except Exception as e:
            logger.debug(f"[TP] Could not resolve domain from deliverable: {e}")

    # Fallback: check if user has only one domain (use it implicitly)
    if not active_domain_id:
        try:
            domains_result = auth.client.table("context_domains")\
                .select("id, name")\
                .eq("user_id", auth.user_id)\
                .eq("is_default", False)\
                .execute()
            if domains_result.data and len(domains_result.data) == 1:
                active_domain_id = UUID(domains_result.data[0]["id"])
                active_domain_name = domains_result.data[0]["name"]
                logger.info(f"[TP] Single domain auto-selected: {active_domain_name}")
        except Exception as e:
            logger.debug(f"[TP] Could not check user domains: {e}")

    # Load memories with domain scoping (ADR-034)
    context = await load_memories(
        auth.client,
        auth.user_id,
        domain_id=active_domain_id,
        query=request.content if request.include_context else None
    )
    context.domain_name = active_domain_name

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
        # Track tool calls and results for proper history storage
        # This allows Claude to maintain coherence across turns
        tool_call_history = []  # List of {"tool_use": {...}, "tool_result": {...}}
        current_tool_use = None

        try:
            # Append user message to session
            await append_message(auth.client, session_id, "user", request.content)
            logger.info(f"[TP-STREAM] Starting stream for message: {request.content[:50]}...")

            # Build images list for Claude API format (if any)
            images_for_api = None
            if request.images:
                images_for_api = [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": img.media_type,
                            "data": img.data,
                        }
                    }
                    for img in request.images
                ]
                logger.info(f"[TP] Processing {len(images_for_api)} image attachment(s)")

            async for event in agent.execute_stream_with_tools(
                task=request.content,
                context=context,
                auth=auth,
                parameters={
                    "include_context": request.include_context,
                    "history": history,
                    "is_onboarding": is_onboarding,
                    "surface_content": surface_content,  # ADR-023: What user is viewing
                    "images": images_for_api,  # Inline base64 images
                },
            ):
                if event.type == "text":
                    full_response += event.content
                    yield f"data: {json.dumps({'content': event.content})}\n\n"
                elif event.type == "tool_use":
                    tools_used.append(event.content["name"])
                    current_tool_use = event.content
                    msg = f"[TP-STREAM] Tool use: {event.content['name']}"
                    print(msg, flush=True)
                    logger.info(msg)
                    yield f"data: {json.dumps({'tool_use': event.content})}\n\n"
                elif event.type == "tool_result":
                    result = event.content.get("result", {})
                    ui_action = result.get("ui_action")
                    tool_name = event.content.get("name")
                    msg = f"[TP-STREAM] Tool result for {tool_name}: ui_action={ui_action}, success={result.get('success')}"
                    print(msg, flush=True)
                    logger.info(msg)

                    # Extract Respond/Clarify message as text content
                    # This handles the case where Claude uses Respond tool instead of direct text
                    if tool_name == "Respond" and ui_action:
                        respond_message = ui_action.get("data", {}).get("message", "")
                        if respond_message:
                            full_response += respond_message
                            yield f"data: {json.dumps({'content': respond_message})}\n\n"
                    elif tool_name == "Clarify" and ui_action:
                        clarify_data = ui_action.get("data", {})
                        clarify_question = clarify_data.get("question", "")
                        clarify_options = clarify_data.get("options", [])
                        if clarify_question:
                            clarify_text = clarify_question
                            if clarify_options:
                                clarify_text += "\n" + "\n".join(f"- {opt}" for opt in clarify_options)
                            full_response += clarify_text
                            yield f"data: {json.dumps({'content': clarify_text})}\n\n"

                    # Store tool call pair for history
                    if current_tool_use:
                        tool_call_history.append({
                            "tool_use": current_tool_use,
                            "tool_result": event.content
                        })
                        current_tool_use = None
                    yield f"data: {json.dumps({'tool_result': event.content})}\n\n"
                elif event.type == "done":
                    msg = f"[TP-STREAM] Stream done, tools_used={tools_used}"
                    print(msg, flush=True)
                    logger.info(msg)
                    pass  # Will send done event after saving

            # Build a comprehensive content record for the assistant message
            # This includes tool calls so Claude can maintain coherence across turns
            assistant_content_for_history = []

            # Add tool use/result pairs
            for tool_pair in tool_call_history:
                tu = tool_pair["tool_use"]
                tr = tool_pair["tool_result"]
                # Simplified representation for history storage
                assistant_content_for_history.append({
                    "type": "tool_call",
                    "name": tu["name"],
                    "input_summary": str(tu.get("input", {}))[:200],
                    "result_summary": str(tr.get("result", {}))[:500]
                })

            # Add the text response (from respond() tool)
            if full_response:
                assistant_content_for_history.append({
                    "type": "text",
                    "content": full_response
                })

            # Append assistant response to session with tool history in metadata
            await append_message(
                auth.client,
                session_id,
                "assistant",
                full_response,
                {
                    "model": agent.model,
                    "tools_used": tools_used,
                    "tool_history": assistant_content_for_history
                }
            )

            yield f"data: {json.dumps({'done': True, 'session_id': session_id, 'tools_used': tools_used})}\n\n"

            # Fire-and-forget extraction with domain context (ADR-034)
            messages_for_extraction = history + [
                {"role": "user", "content": request.content},
                {"role": "assistant", "content": full_response},
            ]
            asyncio.create_task(
                _background_extraction(
                    auth.user_id,
                    messages_for_extraction,
                    auth.client,
                    str(active_domain_id) if active_domain_id else None
                )
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
