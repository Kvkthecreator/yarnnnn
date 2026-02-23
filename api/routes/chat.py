"""
Chat routes - Thinking Partner conversations

ADR-006: Session and message architecture
ADR-007: Tool use for TP authority (unified streaming + tools)
ADR-059/064: Memory via user_context table and build_working_memory()
ADR-067: Session compaction and conversational continuity

Session Philosophy (ADR-067):
- In-session compaction at 80% of MAX_HISTORY_TOKENS (40k of 50k)
- Cross-session continuity via chat_sessions.summary (written by nightly cron)
- Inactivity-based session boundary (4h, not UTC midnight)
- Compaction format: assistant <summary> block prepended to remaining history

Endpoints:
- POST /chat - Global chat with streaming + tools
- GET /chat/history - Get global chat history
- GET /skills - List available TP skills
"""

import json
import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Literal
from uuid import UUID
from datetime import datetime

from services.supabase import UserClient

logger = logging.getLogger(__name__)
from agents.base import ContextBundle
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

    Scope behaviors (ADR-067 Phase 2):
    - conversation: Always creates new session
    - daily: Reuses session active within last 4 hours (inactivity boundary)

    Returns:
        Session dict with 'id' and 'is_new' (bool indicating if session was just created)
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
            # RPC may return is_new; if not, assume existing session
            session = result.data
            if "is_new" not in session:
                session["is_new"] = False
            return session
        raise Exception("No session returned from RPC")
    except Exception:
        # Fallback: check for active session within inactivity window (ADR-067 Phase 2)
        if scope == "daily":
            from datetime import datetime, timedelta, timezone
            inactivity_cutoff = (
                datetime.now(timezone.utc) - timedelta(hours=4)
            ).isoformat()
            existing = client.table("chat_sessions")\
                .select("id")\
                .eq("user_id", user_id)\
                .eq("session_type", session_type)\
                .gte("updated_at", inactivity_cutoff)\
                .eq("status", "active")\
                .order("updated_at", desc=True)\
                .limit(1)\
                .execute()
            if existing.data:
                return {**existing.data[0], "is_new": False}

        # Create new session
        data = {
            "user_id": user_id,
            "session_type": session_type,
            "status": "active"
        }

        result = client.table("chat_sessions").insert(data).execute()
        if result.data:
            return {**result.data[0], "is_new": True}
        return None


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
# History Management (ADR-067: Session Compaction)
# =============================================================================
# Phase 3: In-session compaction at 80% of MAX_HISTORY_TOKENS.
# When truncation would drop messages exceeding COMPACTION_THRESHOLD tokens,
# a compaction LLM call generates a <summary> block that replaces the dropped
# messages. The summary is persisted to chat_sessions.compaction_summary so
# subsequent turns prepend it without re-generating.

# Token budget for history
# Conservative to leave room for system prompt (~8k) + context injection (~10k)
# Opus-4.5 has 200k context, we target ~50k for history
MAX_HISTORY_TOKENS = 50000

# Compaction trigger: 80% of budget (ADR-067 Phase 3)
COMPACTION_THRESHOLD = int(MAX_HISTORY_TOKENS * 0.8)  # 40,000 tokens

# Character-to-token ratio (conservative estimate)
# Claude tokenizes ~4 chars per token on average for English text
# Tool calls often have JSON which tokenizes more efficiently
CHARS_PER_TOKEN = 3.5


def estimate_message_tokens(message: dict) -> int:
    """
    Estimate token count for a message.

    Uses conservative character-based estimation.
    Structured content (tool_use blocks) gets additional overhead.
    """
    content = message.get("content", "")

    if isinstance(content, str):
        # Simple text message
        return int(len(content) / CHARS_PER_TOKEN) + 10  # +10 for message overhead

    if isinstance(content, list):
        # Structured content (tool_use, tool_result blocks)
        total = 20  # Base overhead for structured message

        for block in content:
            if isinstance(block, dict):
                block_type = block.get("type", "")

                if block_type == "text":
                    total += int(len(block.get("text", "")) / CHARS_PER_TOKEN)
                elif block_type == "tool_use":
                    # Tool name + input JSON
                    total += 50  # Overhead for tool_use structure
                    input_str = str(block.get("input", {}))
                    total += int(len(input_str) / CHARS_PER_TOKEN)
                elif block_type == "tool_result":
                    total += 30  # Overhead for tool_result structure
                    result_str = str(block.get("content", ""))
                    total += int(len(result_str) / CHARS_PER_TOKEN)
                else:
                    # Unknown block type
                    total += int(len(str(block)) / CHARS_PER_TOKEN)

        return total

    return 50  # Fallback for unknown formats


def truncate_history_by_tokens(
    messages: list[dict],
    max_tokens: int = MAX_HISTORY_TOKENS
) -> list[dict]:
    """
    Truncate message history to fit within token budget.

    Takes most recent messages that fit within budget.
    Ensures history starts with a user message (Anthropic requirement).

    Args:
        messages: Full message history (oldest first)
        max_tokens: Token budget for history

    Returns:
        Truncated list of messages (oldest first)
    """
    if not messages:
        return []

    # Calculate tokens for each message (in reverse order for recency priority)
    message_tokens = []
    for msg in reversed(messages):
        tokens = estimate_message_tokens(msg)
        message_tokens.append((msg, tokens))

    # Select messages that fit within budget (most recent first)
    selected = []
    total_tokens = 0

    for msg, tokens in message_tokens:
        if total_tokens + tokens <= max_tokens:
            selected.append(msg)
            total_tokens += tokens
        else:
            break

    # Reverse to restore chronological order
    selected.reverse()

    # Ensure history starts with user message (Anthropic requirement)
    while selected and selected[0].get("role") == "assistant":
        selected = selected[1:]

    return selected


def build_history_for_claude(
    messages: list[dict],
    use_structured_format: bool = True,
    max_tokens: int = MAX_HISTORY_TOKENS,
    compaction_block: Optional[dict] = None,
) -> list[dict]:
    """
    Build conversation history in Anthropic message format.

    Claude Code uses structured tool_use/tool_result blocks for better coherence.
    This function reconstructs that format from our stored tool_history metadata.

    ADR-067: Token-based truncation with compaction support.
    If a compaction_block is provided (assistant <summary> message), it is
    prepended to the truncated history — messages prior to the compaction are
    absent from the API call but retained in session_messages for audit.

    Args:
        messages: Raw session messages from database
        use_structured_format: If True, use tool_use/tool_result blocks.
                              If False, use simplified text-based format.
        max_tokens: Token budget for history (default: MAX_HISTORY_TOKENS)
        compaction_block: Optional assistant message with <summary> block to
                          prepend (ADR-067 Phase 3). If provided, messages are
                          truncated relative to this block.

    Returns:
        List of messages in Anthropic API format
    """
    # ADR-067: Token-based truncation
    messages = truncate_history_by_tokens(messages, max_tokens)

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

    # ADR-067 Phase 3: prepend compaction block if present
    # The model sees its own prior summary as the first message in history,
    # followed by the recent window. All earlier messages are excluded from
    # the API call (but remain in session_messages for audit).
    if compaction_block:
        history = [compaction_block] + history

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
# In-Session Compaction (ADR-067 Phase 3)
# =============================================================================

COMPACTION_PROMPT = (
    "Summarise the conversation above for continuity. "
    "The reader will have no access to the original messages — only this summary. "
    "Focus on: decisions made, work in progress, user preferences stated, "
    "platform actions taken, and anything left unresolved. "
    "Be concise but complete. Do not truncate important details."
)


async def maybe_compact_history(
    client,
    session_id: str,
    messages: list[dict],
    existing_compaction: Optional[str] = None,
) -> Optional[dict]:
    """
    ADR-067 Phase 3: Check if in-session compaction is needed.

    If the full message history would exceed COMPACTION_THRESHOLD tokens,
    generate a compaction summary via a single LLM call, write it to
    chat_sessions.compaction_summary, and return the compaction block.

    If a compaction already exists for this session (existing_compaction),
    return it directly without re-generating.

    Args:
        client: Supabase client (service client for DB writes)
        session_id: Current session ID
        messages: Raw session messages from database
        existing_compaction: Existing compaction_summary text from chat_sessions

    Returns:
        compaction_block dict (assistant message) or None if not needed
    """
    # If a compaction already exists, return it as a block without re-generating
    if existing_compaction:
        return {
            "role": "assistant",
            "content": [{
                "type": "text",
                "text": f"<summary>\n{existing_compaction}\n</summary>"
            }]
        }

    # Calculate total tokens for all messages
    total_tokens = sum(estimate_message_tokens(m) for m in messages)

    if total_tokens <= COMPACTION_THRESHOLD:
        return None  # Under threshold, no compaction needed

    # Over threshold — generate compaction summary
    logger.info(
        f"[TP-COMPACT] Session {session_id}: {total_tokens} tokens exceeds "
        f"threshold {COMPACTION_THRESHOLD}. Generating compaction summary."
    )

    try:
        import anthropic as anthropic_sdk
        from services.memory import EXTRACTION_MODEL

        # Build a text-only history for the compaction prompt
        # (tool_use/tool_result blocks are complex; summarise them as text)
        compact_messages = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content") or ""
            metadata = m.get("metadata") or {}
            tool_history = metadata.get("tool_history", [])

            if tool_history:
                parts = []
                for item in tool_history:
                    if item.get("type") == "tool_call":
                        parts.append(f"[Called {item['name']}: {item.get('result_summary', '')}]")
                    elif item.get("type") == "text" and item.get("content"):
                        parts.append(item["content"])
                compact_messages.append({"role": role, "content": " ".join(parts) or content})
            else:
                compact_messages.append({"role": role, "content": content})

        # Add the compaction instruction as the final user turn
        compact_messages.append({"role": "user", "content": COMPACTION_PROMPT})

        sdk_client = anthropic_sdk.Anthropic()
        response = sdk_client.messages.create(
            model=EXTRACTION_MODEL,
            max_tokens=1024,
            messages=compact_messages,
        )

        compaction_text = response.content[0].text.strip() if response.content else ""

        if not compaction_text:
            logger.warning(f"[TP-COMPACT] Session {session_id}: Empty compaction response, skipping.")
            return None

        # Persist to chat_sessions.compaction_summary
        try:
            client.table("chat_sessions").update(
                {"compaction_summary": compaction_text}
            ).eq("id", session_id).execute()
            logger.info(f"[TP-COMPACT] Session {session_id}: Compaction summary written ({len(compaction_text)} chars).")
        except Exception as db_err:
            logger.warning(f"[TP-COMPACT] Session {session_id}: Failed to write compaction_summary: {db_err}")

        return {
            "role": "assistant",
            "content": [{
                "type": "text",
                "text": f"<summary>\n{compaction_text}\n</summary>"
            }]
        }

    except Exception as e:
        logger.warning(f"[TP-COMPACT] Session {session_id}: Compaction failed, falling back to truncation: {e}")
        return None


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


# ADR-059: Background extraction removed — TP only knows what users explicitly state.


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

    ADR-053: Enforces daily token budget based on user tier.
    """
    from services.platform_limits import check_daily_token_budget

    # Get or create session (daily scope for global chat)
    session = await get_or_create_session(
        auth.client,
        auth.user_id,
        scope="daily"
    )
    session_id = session["id"]

    # ADR-053: Check daily token budget before every message
    allowed, tokens_used, token_limit = check_daily_token_budget(auth.client, auth.user_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "daily_token_budget_exceeded",
                "message": f"Daily token budget reached ({tokens_used:,}/{token_limit:,}). Resets at midnight UTC.",
                "tokens_used": tokens_used,
                "token_limit": token_limit,
                "upgrade_url": "/settings/subscription",
            }
        )

    # Load existing messages and session-level compaction summary
    # ADR-067: In-session compaction at 80% threshold; compaction block prepended if present
    existing_messages = await get_session_messages(auth.client, session_id)

    # Fetch compaction_summary from chat_sessions (may be None for most sessions)
    existing_compaction = None
    try:
        session_row = auth.client.table("chat_sessions").select(
            "compaction_summary"
        ).eq("id", session_id).single().execute()
        existing_compaction = (session_row.data or {}).get("compaction_summary")
    except Exception:
        pass  # Non-fatal: proceed without compaction

    # ADR-067 Phase 3: check compaction threshold; generate or reuse summary
    from services.supabase import get_service_client
    compaction_block = await maybe_compact_history(
        client=get_service_client(),
        session_id=session_id,
        messages=existing_messages,
        existing_compaction=existing_compaction,
    )

    history = build_history_for_claude(
        existing_messages,
        use_structured_format=False,
        compaction_block=compaction_block,
    )
    logger.info(
        f"[TP] Loaded {len(existing_messages)} messages, built {len(history)} history entries"
        + (f" (compaction block present)" if compaction_block else "")
    )

    # ADR-059/064: Memory now loaded via build_working_memory in execute_stream_with_tools
    # ContextBundle is passed for backwards compatibility but is empty
    context = ContextBundle()

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
        # ADR-053: Capture cumulative token usage for persistence
        last_token_usage = {"input_tokens": 0, "output_tokens": 0}

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
                elif event.type == "usage":
                    # ADR-053: Capture cumulative usage for persistence
                    last_token_usage = event.content
                    yield f"data: {json.dumps({'usage': event.content})}\n\n"
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

            # Append assistant response to session with tool history and token usage in metadata
            await append_message(
                auth.client,
                session_id,
                "assistant",
                full_response,
                {
                    "model": agent.model,
                    "tools_used": tools_used,
                    "tool_history": assistant_content_for_history,
                    "input_tokens": last_token_usage.get("input_tokens", 0),
                    "output_tokens": last_token_usage.get("output_tokens", 0),
                }
            )

            yield f"data: {json.dumps({'done': True, 'session_id': session_id, 'tools_used': tools_used})}\n\n"

            # Activity log: record chat turn completion (ADR-063)
            # Must use service client — activity_log RLS blocks INSERT from user JWT
            try:
                from services.activity_log import write_activity
                from services.supabase import get_service_client
                await write_activity(
                    client=get_service_client(),
                    user_id=auth.user_id,
                    event_type="chat_session",
                    summary=f"Chat turn complete" + (f" (tools: {', '.join(tools_used)})" if tools_used else ""),
                    event_ref=session_id,
                    metadata={"session_id": session_id, "tools_used": tools_used},
                )
            except Exception:
                pass  # Non-fatal

            # ADR-059: Background extraction removed.

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
        # Get messages for each session (include metadata for tool_history)
        messages_result = (
            auth.client.table("session_messages")
            .select("id, role, content, sequence_number, created_at, metadata")
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
