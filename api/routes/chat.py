"""
Chat routes - Thinking Partner conversations

ADR-006: Session and message architecture
ADR-007: Tool use for TP authority (unified streaming + tools)
ADR-059/064: Memory via user_memory table and build_working_memory()
ADR-067: Session compaction and conversational continuity
ADR-087: Agent-scoped context (agent_id on sessions, scoped working memory)
ADR-125: Project-native sessions — two scopes (Global TP + Project), thread model

Session Philosophy (ADR-067, updated ADR-125):
- In-session compaction at 80% of MAX_HISTORY_TOKENS (40k of 50k)
- Cross-session continuity via chat_sessions.summary
- Global TP: 4h inactivity boundary
- Project sessions: 24h inactivity boundary (ADR-125)
- Compaction format: assistant <summary> block prepended to remaining history

ADR-125: Project-Native Sessions:
- Two session scopes: Global TP (no project) and Project (via project_slug)
- No standalone agent sessions — agent requests resolve to project sessions
- Thread model: thread_agent_id on session_messages filters 1:1 threads
- Agent pages render their thread from the project session

Endpoints:
- POST /chat - Global chat with streaming + tools
- GET /chat/history - Get chat history (global, project, or thread)
- GET /chat/sessions - List global TP sessions (lightweight, for dashboard panel)
- GET /commands - List available slash commands
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
from services.task_workspace import TaskWorkspace

logger = logging.getLogger(__name__)
from agents.base import ContextBundle
from agents.thinking_partner import ThinkingPartnerAgent

router = APIRouter()


class ChatHistoryMessage(BaseModel):
    role: str
    content: str


class SurfaceContext(BaseModel):
    """Surface context for TP - what the user is currently viewing."""
    type: str  # e.g., "agent-review", "work-output", "idle", "task-detail"
    agentId: Optional[str] = None
    projectSlug: Optional[str] = None  # ADR-119 P4b: project-scoped chat
    taskSlug: Optional[str] = None  # Task-scoped chat sessions
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
    target_agent_id: Optional[str] = None  # ADR-124: route message to specific agent in meeting room


# =============================================================================
# Session Management (ADR-006)
# =============================================================================

async def get_or_create_session(
    client,
    user_id: str,
    session_type: str = "thinking_partner",
    scope: str = "daily",  # "conversation", "daily"
    agent_id: Optional[str] = None,  # DEPRECATED by ADR-125: use project sessions with thread_agent_id
) -> dict:
    """
    Get or create a chat session using the database RPC.

    Scope behaviors (ADR-067 Phase 2):
    - conversation: Always creates new session
    - daily: Reuses session active within last 4 hours (inactivity boundary)

    DEPRECATED (ADR-125): agent_id parameter is a legacy fallback for agents not
    yet wrapped in projects. New code should use get_or_create_project_session()
    with thread_agent_id on messages instead. The agent_id column on chat_sessions
    will be removed once all agents are project-native.

    Returns:
        Session dict with 'id', 'is_new' (bool), and optionally
        'previous_session_id' (str) when a new session replaces an old one.
    """
    try:
        result = client.rpc(
            "get_or_create_chat_session",
            {
                "p_user_id": user_id,
                "p_project_id": None,
                "p_session_type": session_type,
                "p_scope": scope,
                "p_agent_id": agent_id,
            }
        ).execute()

        if result.data:
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
            q = client.table("chat_sessions")\
                .select("id")\
                .eq("user_id", user_id)\
                .eq("session_type", session_type)\
                .gte("updated_at", inactivity_cutoff)\
                .eq("status", "active")
            # ADR-087 Phase 3: scope by agent_id
            if agent_id:
                q = q.eq("agent_id", agent_id)
            else:
                q = q.is_("agent_id", "null")
            existing = q.order("updated_at", desc=True)\
                .limit(1)\
                .execute()
            if existing.data:
                return {**existing.data[0], "is_new": False}

        # Find the most recent session (will become previous_session_id)
        previous_session_id = None
        try:
            prev = client.table("chat_sessions")\
                .select("id")\
                .eq("user_id", user_id)\
                .eq("session_type", session_type)\
                .is_("summary", "null")\
                .order("updated_at", desc=True)\
                .limit(1)\
                .execute()
            if prev.data:
                previous_session_id = prev.data[0]["id"]
        except Exception as e:
            logger.debug(f"[SESSION] Failed to find previous session: {e}")

        # Create new session
        data = {
            "user_id": user_id,
            "session_type": session_type,
            "status": "active",
        }
        if agent_id:
            data["agent_id"] = agent_id

        result = client.table("chat_sessions").insert(data).execute()
        if result.data:
            return {
                **result.data[0],
                "is_new": True,
                "previous_session_id": previous_session_id,
            }
        return None


# get_or_create_project_session — REMOVED (project sessions dissolved)


async def get_or_create_task_session(
    client,
    user_id: str,
    task_slug: str,
    session_type: str = "thinking_partner",
) -> dict:
    """
    Get or create a task-scoped TP session.

    Same 4h inactivity boundary as global TP sessions.
    Looks up by user_id + task_slug + session_type + status=active.
    """
    from datetime import timedelta, timezone

    inactivity_cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=4)
    ).isoformat()

    # Look for active session within inactivity window
    existing = (
        client.table("chat_sessions")
        .select("id")
        .eq("user_id", user_id)
        .eq("task_slug", task_slug)
        .eq("session_type", session_type)
        .eq("status", "active")
        .gte("updated_at", inactivity_cutoff)
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )

    if existing.data:
        return {**existing.data[0], "is_new": False}

    # Find previous session for summary generation
    previous_session_id = None
    try:
        prev = (
            client.table("chat_sessions")
            .select("id")
            .eq("user_id", user_id)
            .eq("task_slug", task_slug)
            .eq("session_type", session_type)
            .is_("summary", "null")
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        if prev.data:
            previous_session_id = prev.data[0]["id"]
    except Exception as e:
        logger.debug(f"[SESSION] Failed to find previous task session: {e}")

    # Create new task-scoped session
    result = (
        client.table("chat_sessions")
        .insert({
            "user_id": user_id,
            "session_type": session_type,
            "status": "active",
            "task_slug": task_slug,
        })
        .execute()
    )

    if result.data:
        return {
            **result.data[0],
            "is_new": True,
            "previous_session_id": previous_session_id,
        }
    return None


async def append_message(
    client,
    session_id: str,
    role: str,
    content: str,
    metadata: Optional[dict] = None,
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

        insert_data = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "sequence_number": next_seq,
            "metadata": metadata or {}
        }

        result = client.table("session_messages").insert(insert_data).execute()
        return result.data[0] if result.data else None


async def get_session_messages(
    client,
    session_id: str,
    limit: int = 50,
) -> list[dict]:
    """Get messages for a session, ordered by sequence."""
    result = client.table("session_messages")\
        .select("*")\
        .eq("session_id", session_id)\
        .order("sequence_number")\
        .limit(limit)\
        .execute()
    return result.data or []


async def _summarize_previous_session(previous_session_id: str, client) -> None:
    """
    Generate summary for a closed session (runs as BackgroundTask).

    Inline summary at session close eliminates the intraday context gap
    where nightly cron hasn't run yet. Nightly cron remains as fallback.

    ADR-125: Project sessions get author-aware summaries that attribute
    decisions to specific agent participants.
    """
    try:
        # Check if already summarized
        session = client.table("chat_sessions")\
            .select("id, summary, created_at")\
            .eq("id", previous_session_id)\
            .single()\
            .execute()

        if not session.data or session.data.get("summary"):
            return  # Already summarized or not found

        # Fetch messages (include metadata for author attribution in project sessions)
        messages = client.table("session_messages")\
            .select("role, content, metadata")\
            .eq("session_id", previous_session_id)\
            .order("sequence_number")\
            .limit(50)\
            .execute()

        if not messages.data or len([m for m in messages.data if m.get("role") == "user"]) < 3:
            return  # Too short to summarize

        session_date = (session.data.get("created_at") or "")[:10]

        # ADR-138: Project sessions removed. Always use standard summary.
        from services.session_continuity import generate_session_summary
        summary = await generate_session_summary(messages.data, session_date)

        if summary:
            client.table("chat_sessions")\
                .update({"summary": summary})\
                .eq("id", previous_session_id)\
                .execute()
            logger.info(f"[SESSION] Inline summary generated for session {previous_session_id[:8]}")

    except Exception as e:
        logger.warning(f"[SESSION] Failed to generate inline summary: {e}")


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
    global_tool_index = 0  # Global counter for unique tool IDs across all messages

    for m in messages:
        role = m["role"]
        content = m.get("content") or ""
        metadata = m.get("metadata") or {}
        tool_history = metadata.get("tool_history", [])

        if role == "assistant" and tool_history and use_structured_format:
            # Build structured content: separate tool_use and text blocks.
            # Claude API requires tool_use blocks NOT be followed by text in
            # the same assistant message. The correct structure is:
            #   assistant: [tool_use blocks]
            #   user: [tool_result blocks]
            #   assistant: [text response]  (if any)
            tool_use_blocks = []
            tool_results = []
            text_blocks = []

            for item in tool_history:
                if item.get("type") == "tool_call":
                    tool_id = f"toolu_{global_tool_index:04d}"

                    tool_use_blocks.append({
                        "type": "tool_use",
                        "id": tool_id,
                        "name": item["name"],
                        "input": _parse_input_summary(item.get("input_summary", "{}"))
                    })

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": item.get("result_summary", "Success")
                    })

                    global_tool_index += 1
                elif item.get("type") == "text" and item.get("content"):
                    text_blocks.append({
                        "type": "text",
                        "text": item["content"]
                    })

            if tool_use_blocks:
                # Assistant message with ONLY tool_use blocks
                history.append({
                    "role": "assistant",
                    "content": tool_use_blocks
                })

                # Tool results as user turn
                history.append({
                    "role": "user",
                    "content": tool_results
                })

                # Text response as separate assistant turn (if any)
                if text_blocks:
                    history.append({
                        "role": "assistant",
                        "content": text_blocks
                    })
            elif text_blocks:
                # Just text content, no tools
                history.append({
                    "role": "assistant",
                    "content": text_blocks
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

    # Merge consecutive same-role messages to satisfy Claude API alternation requirement.
    # This happens when tool_result user messages are followed by the next real user message.
    merged = []
    for msg in history:
        if merged and merged[-1]["role"] == msg["role"]:
            prev_content = merged[-1]["content"]
            curr_content = msg["content"]
            # Normalize both to lists
            if isinstance(prev_content, str):
                prev_content = [{"type": "text", "text": prev_content}]
            if isinstance(curr_content, str):
                curr_content = [{"type": "text", "text": curr_content}]
            merged[-1]["content"] = prev_content + curr_content
        else:
            merged.append(msg)

    return merged


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

        if surface_type == "agent-review" and surface.agentId and surface.versionId:
            # User is reviewing an agent version - fetch the content
            agent_result = client.table("agents")\
                .select("title, scope, role")\
                .eq("id", surface.agentId)\
                .eq("user_id", user_id)\
                .single()\
                .execute()

            version_result = client.table("agent_runs")\
                .select("content, version_number, status")\
                .eq("id", surface.versionId)\
                .single()\
                .execute()

            if agent_result.data and version_result.data:
                d = agent_result.data
                v = version_result.data
                content = v.get("content", "")
                # Truncate if too long
                if len(content) > 8000:
                    content = content[:8000] + "\n\n[Content truncated...]"

                return f"""## Currently Viewing: {d['title']} (Run {v['version_number']})
Type: {d.get('role', 'custom').replace('_', ' ').title()}
Status: {v['status']}

### Content:
{content}
"""

        elif surface_type == "agent-detail" and surface.agentId:
            # User is viewing agent details (not content)
            result = client.table("agents")\
                .select("title, scope, role, status, type_config")\
                .eq("id", surface.agentId)\
                .eq("user_id", user_id)\
                .single()\
                .execute()

            if result.data:
                d = result.data
                return f"""## Currently Viewing: {d['title']} (Agent Detail)
Type: {d.get('role', 'custom').replace('_', ' ').title()}
Status: {d['status']}
Config: {d.get('type_config', {})}
"""

        elif surface_type == "task-detail" and surface.taskSlug:
            # User is viewing a task — load task context for TP
            return await _load_task_context(client, user_id, surface.taskSlug)

        elif surface_type == "context-browser":
            # User is browsing their context/memories - just note it
            return "## Currently Viewing: Context Browser\nUser is browsing their stored memories and context."

        # For list views and idle, no specific content needed
        return None

    except Exception as e:
        logger.warning(f"Failed to load surface content: {e}")
        return None


async def _load_task_context(
    client,
    user_id: str,
    task_slug: str,
) -> Optional[str]:
    """
    Load task context for TP when user is on a task-detail surface.

    Reads TASK.md, last 5 run log entries, latest output preview,
    and assigned agent info.
    """
    import re

    tw = TaskWorkspace(client, user_id, task_slug)

    # 1. Read TASK.md
    task_md = await tw.read("TASK.md")
    if not task_md:
        return None  # Task doesn't exist or has no TASK.md

    # Extract task title from first heading
    task_title = task_slug
    title_match = re.search(r"^#\s+(.+)", task_md, re.MULTILINE)
    if title_match:
        task_title = title_match.group(1).strip()

    # 2. Read run_log.md — last 5 ## sections
    run_log_last_5 = ""
    run_log = await tw.read("memory/run_log.md")
    if run_log:
        sections = re.split(r"(?=^## )", run_log, flags=re.MULTILINE)
        # Filter out empty sections
        sections = [s.strip() for s in sections if s.strip()]
        last_5 = sections[-5:] if len(sections) > 5 else sections
        run_log_last_5 = "\n\n".join(last_5)

    # 3. Read latest output preview (first 500 chars)
    output_preview = ""
    output_content = await tw.read("outputs/output.md")
    if output_content:
        output_preview = output_content[:500]
        if len(output_content) > 500:
            output_preview += "\n[truncated...]"

    # 4. Parse assigned agent slug from TASK.md ## Process section
    agent_info = ""
    agent_slug_match = re.search(
        r"## Process.*?agent:\s*(\S+)", task_md, re.DOTALL | re.IGNORECASE
    )
    if agent_slug_match:
        agent_slug = agent_slug_match.group(1).strip()
        try:
            agent_result = (
                client.table("agents")
                .select("title, role")
                .eq("user_id", user_id)
                .eq("slug", agent_slug)
                .limit(1)
                .execute()
            )
            if agent_result.data:
                a = agent_result.data[0]
                agent_info = f"{a['title']} ({a.get('role', 'custom')})"
        except Exception as e:
            logger.debug(f"[TASK_CONTEXT] Failed to fetch agent: {e}")

    # Build formatted context
    parts = [f'You are helping the user manage the task "{task_title}".']
    parts.append(f"\nTask definition:\n{task_md}")

    if run_log_last_5:
        parts.append(f"\nRecent run log:\n{run_log_last_5}")

    if output_preview:
        parts.append(f"\nLatest output preview:\n{output_preview}")

    if agent_info:
        parts.append(f"\nAssigned agent: {agent_info}")

    return "\n".join(parts)


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

    ADR-100: Enforces monthly message limit based on user tier.
    """
    from services.platform_limits import check_monthly_message_limit

    # ADR-125: Extract routing context from surface_context
    request_agent_id = None
    request_task_slug = None
    if request.surface_context:
        if request.surface_context.agentId:
            request_agent_id = request.surface_context.agentId
        if request.surface_context.taskSlug:
            request_task_slug = request.surface_context.taskSlug

    # Session routing: Task-scoped > Agent-scoped > Global TP
    if request_task_slug:
        # Task-scoped session (takes priority over agent_id)
        session = await get_or_create_task_session(
            auth.client,
            auth.user_id,
            task_slug=request_task_slug,
        )
    elif request_agent_id:
        # Agent-scoped session
        session = await get_or_create_session(
            auth.client,
            auth.user_id,
            scope="daily",
            agent_id=request_agent_id,
        )
    else:
        # Global TP session (no agent)
        session = await get_or_create_session(
            auth.client,
            auth.user_id,
            scope="daily",
        )
    session_id = session["id"]

    # Generate summary for previous session if this is a new session
    if session.get("is_new") and session.get("previous_session_id"):
        import asyncio
        from services.supabase import get_service_client
        asyncio.create_task(_summarize_previous_session(
            session["previous_session_id"],
            get_service_client(),
        ))

    # Check monthly message limit (Free tier only — Pro is unlimited)
    allowed, messages_used, message_limit = check_monthly_message_limit(auth.client, auth.user_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "monthly_message_limit_exceeded",
                "message": f"You've reached your {message_limit} monthly messages ({messages_used}/{message_limit}). Upgrade to Pro for unlimited chat.",
                "messages_used": messages_used,
                "message_limit": message_limit,
                "upgrade_url": "/settings?tab=billing",
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
    except Exception as e:
        logger.debug(f"[TP-COMPACT] Failed to load existing compaction: {e}")

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
        use_structured_format=True,
        compaction_block=compaction_block,
    )
    logger.info(
        f"[TP] Loaded {len(existing_messages)} messages, built {len(history)} history entries"
        + (f" (compaction block present)" if compaction_block else "")
    )

    # ADR-087 Phase 3: agent_id is now set at session creation time (above).
    # Still need to fetch the agent for working memory injection.
    agent_id = request_agent_id
    scoped_agent = None
    if agent_id:
        try:
            d_result = auth.client.table("agents").select(
                "id, user_id, title, scope, role, agent_instructions, agent_memory"
            ).eq("id", agent_id).eq("user_id", auth.user_id).single().execute()
            if d_result.data:
                scoped_agent = d_result.data
        except Exception as e:
            logger.warning(f"[TP] Failed to fetch scoped agent: {e}")

    # ADR-059/064: Memory now loaded via build_working_memory in execute_stream_with_tools
    # ContextBundle is passed for backwards compatibility but is empty
    context = ContextBundle()

    # Check if user has any agents (for onboarding mode)
    is_onboarding = False
    try:
        agents_result = auth.client.table("agents")\
            .select("id")\
            .eq("user_id", auth.user_id)\
            .neq("status", "archived")\
            .limit(1)\
            .execute()
        is_onboarding = len(agents_result.data or []) == 0
    except Exception as e:
        logger.debug(f"[TP] Onboarding check failed, defaulting to non-onboarding: {e}")

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

    # All messages route to TP (ChatAgent/project meeting room routing removed)
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
            # ADR-124: User message metadata with attribution
            user_message_metadata = {}

            await append_message(auth.client, session_id, "user", request.content, user_message_metadata)
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

            stream_params = {
                    "include_context": request.include_context,
                    "history": history,
                    "is_onboarding": is_onboarding,
                    "surface_content": surface_content,  # ADR-023: What user is viewing
                    "images": images_for_api,  # Inline base64 images
                    "scoped_agent": scoped_agent,  # ADR-087: Agent-scoped context
                }

            async for event in agent.execute_stream_with_tools(
                task=request.content,
                context=context,
                auth=auth,
                parameters=stream_params,
            ):
                if event.type == "text":
                    full_response += event.content
                    yield f"data: {json.dumps({'content': event.content})}\n\n"
                elif event.type == "tool_use":
                    tools_used.append(event.content["name"])
                    current_tool_use = event.content
                    msg = f"[TP-STREAM] Tool use: {event.content['name']}"
                    logger.info(msg)
                    yield f"data: {json.dumps({'tool_use': event.content})}\n\n"
                elif event.type == "tool_result":
                    result = event.content.get("result", {})
                    ui_action = result.get("ui_action")
                    tool_name = event.content.get("name")
                    msg = f"[TP-STREAM] Tool result for {tool_name}: ui_action={ui_action}, success={result.get('success')}"
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
            # ADR-124: Add author attribution for meeting room messages
            assistant_metadata = {
                "model": agent.model,
                "tools_used": tools_used,
                "tool_history": assistant_content_for_history,
                "input_tokens": last_token_usage.get("input_tokens", 0),
                "output_tokens": last_token_usage.get("output_tokens", 0),
            }
            await append_message(
                auth.client,
                session_id,
                "assistant",
                full_response,
                assistant_metadata,
            )

            done_payload = {'done': True, 'session_id': session_id, 'tools_used': tools_used}
            yield f"data: {json.dumps(done_payload)}\n\n"

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
            except Exception as e:
                logger.debug(f"[TP] Activity log write failed: {e}")

            # ADR-059: Background extraction removed.

        except Exception as e:
            import traceback
            error_msg = f"[TP-STREAM] Error: {type(e).__name__}: {str(e)}"
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
    agent_id: Optional[str] = Query(default=None),
    task_slug: Optional[str] = Query(default=None),
):
    """
    Get chat history scoped by agent, task, or global.
    Returns the most recent session(s) with messages.

    ADR-138: project_slug and thread_agent_id removed (columns dropped).
    """
    # Fetch recent sessions — task-scoped, agent-scoped, or global TP
    q = (
        auth.client.table("chat_sessions")
        .select("*")
        .eq("user_id", auth.user_id)
        .eq("session_type", "thinking_partner")
    )
    if task_slug:
        q = q.eq("task_slug", task_slug)
    elif agent_id:
        q = q.eq("agent_id", agent_id)
    else:
        q = q.is_("agent_id", "null").is_("task_slug", "null")
    sessions_result = q.order("created_at", desc=True).limit(limit).execute()

    sessions = []
    for session in (sessions_result.data or []):
        msg_q = (
            auth.client.table("session_messages")
            .select("id, role, content, sequence_number, created_at, metadata")
            .eq("session_id", session["id"])
        )
        messages_result = msg_q.order("sequence_number").execute()
        sessions.append({
            **session,
            "messages": messages_result.data or []
        })

    return {"sessions": sessions}


@router.get("/chat/sessions")
async def list_global_sessions(
    auth: UserClient,
    limit: int = Query(default=10, le=50),
):
    """
    List global (non-agent-scoped) TP chat sessions.

    Lightweight endpoint returning session metadata with message counts,
    mirroring the agent-scoped GET /api/agents/{id}/sessions endpoint.
    Used by the dashboard Sessions panel.
    """
    result = (
        auth.client.table("chat_sessions")
        .select("id, created_at, summary")
        .eq("user_id", auth.user_id)
        .is_("agent_id", "null")
        .eq("session_type", "thinking_partner")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    sessions = result.data or []

    response = []
    for s in sessions:
        count_result = (
            auth.client.table("session_messages")
            .select("id", count="exact")
            .eq("session_id", s["id"])
            .execute()
        )
        response.append({
            "id": s["id"],
            "created_at": s["created_at"],
            "summary": s.get("summary"),
            "message_count": count_result.count or 0,
        })

    return response


# =============================================================================
# Slash Commands (ADR-025 Claude Code Agentic Alignment)
# =============================================================================

@router.get("/commands")
async def list_commands():
    """
    List available slash commands for TP.

    ADR-025: Commands are packaged workflows that expand to system prompts.
    This endpoint returns the list for UI autocomplete/picker.

    No auth required - commands are public metadata.
    """
    from services.commands import list_available_commands, COMMANDS

    commands = list_available_commands()

    # Add tier information for UI filtering
    enriched = []
    for cmd in commands:
        cmd_def = COMMANDS.get(cmd["name"], {})
        enriched.append({
            **cmd,
            "tier": cmd_def.get("tier", "core"),  # "core" or "beta"
            "trigger_patterns": cmd_def.get("trigger_patterns", []),
        })

    return {
        "commands": enriched,
        "total": len(enriched),
    }
