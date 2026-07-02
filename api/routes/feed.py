"""
Chat routes - Thinking Partner conversations

ADR-006: Session and message architecture
ADR-007: Tool use for TP authority (unified streaming + tools)
ADR-059/064: Memory via user_memory table and build_working_memory()
ADR-067: Session compaction Phase 1+2 — cross-session continuity
ADR-087: Agent-scoped context (agent_id on sessions, scoped working memory)
ADR-125: Project-native sessions — two scopes (Global TP + Project), thread model
ADR-159: Filesystem-as-memory — compact index + 10-message window + conversation.md
ADR-219: Narrative substrate — session_messages.role widened (six Identities)
ADR-221: Layered context strategy — non-conversation roles filtered from API;
         older tool-history collapsed; in-session LLM compaction sunset

Session Philosophy (ADR-159 + ADR-221):
- 10-message rolling window for API call (singular truncation)
- Cross-session continuity via /workspace/system/awareness.md
- Conversation summary written every 5 user messages to /workspace/system/conversation.md
- Recent material non-conversation events rolled up to /workspace/system/recent.md
  by back-office-narrative-digest task; YARNNN reads on demand via ReadFile
- Global TP: 4h inactivity boundary (ADR-067 Phase 2)
- Project sessions: 24h inactivity boundary (ADR-125)

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
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Literal
from uuid import UUID
from datetime import datetime

from services.supabase import UserClient
# ADR-261 + ADR-262: slug-rooted task I/O reads are slug-templated through
# services.conventions; recurrence parsing through services.recurrence.

logger = logging.getLogger(__name__)
# ContextBundle and YarnnnAgent removed — ADR-257: System Agent LLM stream deleted.
# Reviewer (Haiku) is the sole intelligence; execution router dispatches directives.

router = APIRouter()


class ChatHistoryMessage(BaseModel):
    role: str
    content: str


# =============================================================================
# ADR-186 prompt-profile resolution DELETED (bare-kernel product floor, 2026-06-01).
# The chat-profile concept (workspace/entity) died with the YarnnnAgent chat
# surface (ADR-257). The live feed routes to the regex execution_router or the
# Reviewer, neither of which consumes a prompt profile — the Reviewer composes
# its own system prompt in agents/freddie_agent.py. The FE may still send
# surface_context on the request; it is harmlessly ignored.
# See docs/architecture/bare-kernel-product-floor-2026-06-01.md.
# =============================================================================


class ImageAttachment(BaseModel):
    """Image sent inline as base64 (not stored, ephemeral like Claude Code)."""
    type: Literal["base64"] = "base64"
    media_type: Literal["image/jpeg", "image/png", "image/gif", "image/webp"]
    data: str  # Base64-encoded image data


class FileAttachment(BaseModel):
    """Ephemeral file attachment for chat — referenced by Anthropic Files API file_id.

    ADR-249: Ephemeral path. file_id comes from POST /chat/attach.
    The file is passed as a document content block to Claude API in this turn only.
    Nothing is persisted to the workspace.
    """
    file_id: str          # Anthropic Files API file_id
    filename: str         # Original filename for display
    mime_type: str        # MIME type (application/pdf, text/plain, etc.)


class ChatRequest(BaseModel):
    content: str
    include_context: bool = True
    session_id: Optional[str] = None  # Optional: continue existing session
    # ADR-398 D2: the operator locator — a short human-readable string the
    # shell composes from the foregrounded window + its params (replaces the
    # deleted ADR-023 SurfaceContext fossil, which the backend ignored).
    locator: Optional[str] = None
    images: Optional[list[ImageAttachment]] = None  # Images attached to message (ephemeral)
    file_attachments: Optional[list[FileAttachment]] = None  # Ephemeral doc attachments (ADR-249)
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


# get_or_create_task_session DELETED — ADR-255 D5.
# Dead code post-ADR-231 (tasks dissolved into recurrence declarations).


async def append_message(
    client,
    session_id: str,
    role: str,
    content: str,
    metadata: Optional[dict] = None,
) -> dict:
    """Append a message to a session by emitting one narrative entry.

    Per ADR-219 Commit 2 (FOUNDATIONS Axiom 9): all session_messages
    inserts route through services.narrative.write_narrative_entry, the
    single write path. This helper preserves the legacy 5-arg signature
    that chat / memory / invocation_dispatcher callers use today; it
    derives the narrative envelope from the role + the optional metadata
    payload:

      - `summary` is taken from metadata['summary'] when provided, else
        derived from content (first line, truncated). The envelope's
        `body` carries the full content when it differs from summary.
      - `pulse` is taken from metadata['pulse'] when provided. Default
        is 'addressed' for the operator-driven turn pattern this helper
        was built for; invocation_dispatcher + back-office overrides their
        pulse explicitly.
      - `weight` is taken from metadata['weight'] when provided; else
        the narrative module applies the default policy.
      - `invocation_id` / `task_slug` / `provenance` flow through when
        present in metadata.

    Callers do not need to know about the envelope — passing only role +
    content + a metadata dict continues to work. New callers should
    enrich metadata with envelope fields for accurate /chat rendering.
    """
    from services.narrative import write_narrative_entry

    md = dict(metadata or {})

    summary = md.pop("summary", None)
    if not summary:
        first_line = (content or "").strip().split("\n", 1)[0]
        summary = first_line[:160] if first_line else f"{role} message"

    body = content if (content and content != summary) else None
    pulse = md.pop("pulse", "addressed")
    weight = md.pop("weight", None)
    invocation_id = md.pop("invocation_id", None)
    task_slug = md.pop("task_slug", None)
    provenance = md.pop("provenance", None)
    # ADR-209 actor identity (2026-06-30): popped to the explicit envelope param
    # so a caller can add `authored_by` to its metadata dict the same way it adds
    # `pulse`/`weight` — it lands in the envelope, not loose in extra_metadata.
    authored_by = md.pop("authored_by", None)

    return write_narrative_entry(
        client,
        session_id,
        role=role,
        summary=summary,
        body=body,
        pulse=pulse,
        weight=weight,
        invocation_id=invocation_id,
        task_slug=task_slug,
        provenance=provenance,
        authored_by=authored_by,
        extra_metadata=md or None,
    )


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


async def _write_conversation_summary(auth, messages: list[dict]) -> None:
    """
    ADR-159: Write rolling conversation summary to /workspace/system/conversation.md.

    Called every 5 user messages. Extracts key decisions, corrections, and focus
    from the full message history. Written as a workspace file that TP can read
    on demand via ReadFile (ADR-168).

    Uses a simple extraction (no LLM) — last 20 messages summarized by role.
    """
    try:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        # Extract key content from recent messages (last 20)
        recent = messages[-20:] if len(messages) > 20 else messages
        decisions = []
        topics = []

        for m in recent:
            role = m.get("role", "")
            content = (m.get("content") or "").strip()
            if not content:
                continue

            # User messages: capture as topics/requests
            if role == "user" and len(content) > 10:
                first_line = content.split("\n")[0][:120]
                topics.append(first_line)

            # Assistant messages with tool calls: capture as decisions
            tool_history = (m.get("metadata") or {}).get("tool_history", [])
            for tool in tool_history:
                name = tool.get("name", "")
                summary = tool.get("result_summary", "")
                if name in (
                    "ManageDomains",
                    "ManageRecurrence",
                    "ManageAgent",
                    "WriteFile",
                ):
                    decisions.append(f"{name}: {summary[:100]}" if summary else name)

        # Build summary
        summary_parts = [
            f"# Conversation Summary\nLast updated: {now}\n",
        ]

        if decisions:
            summary_parts.append("## Actions taken")
            for d in decisions[-10:]:  # Last 10 decisions
                summary_parts.append(f"- {d}")

        if topics:
            summary_parts.append("\n## Topics discussed")
            for t in topics[-8:]:  # Last 8 topics
                summary_parts.append(f"- {t}")

        summary_content = "\n".join(summary_parts)

        # Write to workspace (ADR-209: through Authored Substrate).
        # authored_by="system:conversation-summary" — this is an automatic
        # inline summary at session close (ADR-159), not an authored edit.
        from services.supabase import get_service_client
        from services.authored_substrate import write_revision

        svc = get_service_client()
        path = "/workspace/system/conversation.md"

        write_revision(
            svc,
            user_id=auth.user_id,
            path=path,
            content=summary_content,
            authored_by="system:conversation-summary",
            message=f"summarize session ({len(decisions)} decisions, {len(topics)} topics)",
            tags=["memory", "conversation"],
        )

        logger.debug(f"[ADR-159] Wrote conversation.md ({len(decisions)} decisions, {len(topics)} topics)")

    except Exception as e:
        logger.warning(f"[ADR-159] Failed to write conversation.md: {e}")


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
        summary = await generate_session_summary(messages.data, session_date, user_id=auth.user_id)

        if summary:
            client.table("chat_sessions")\
                .update({"summary": summary})\
                .eq("id", previous_session_id)\
                .execute()
            logger.info(f"[SESSION] Inline summary generated for session {previous_session_id[:8]}")

    except Exception as e:
        logger.warning(f"[SESSION] Failed to generate inline summary: {e}")


# =============================================================================
# History Management (ADR-159 + ADR-221: filesystem-native compaction)
# =============================================================================
#
# ADR-221 Commit C deleted ADR-067 Phase 3's in-session LLM compaction.
# Compaction is now filesystem-native via /workspace/system/conversation.md
# (written every 5 user messages by _write_conversation_summary). YARNNN
# reads conversation.md on demand via ReadFile when older context is needed.
#
# The 10-message window (MESSAGE_WINDOW in chat handler) is the singular
# truncation. Token-based truncation (truncate_history_by_tokens) was removed
# — the message window already bounds size; with Commit B's tool-history
# collapse on older turns, even a tool-heavy 10-message window stays well
# under Claude's input budget.
#
# Per singular-implementation discipline, the following were deleted in C:
#   - maybe_compact_history()
#   - COMPACTION_THRESHOLD, COMPACTION_PROMPT
#   - truncate_history_by_tokens()
#   - estimate_message_tokens()
#   - chat_sessions.compaction_summary writes (column dropped in migration 174)


def build_history_for_claude(
    messages: list[dict],
    use_structured_format: bool = True,
) -> list[dict]:
    """
    Build conversation history in Anthropic message format.

    Claude Code uses structured tool_use/tool_result blocks for better coherence.
    This function reconstructs that format from our stored tool_history metadata.

    ADR-221 Commit A: filters non-conversation roles (system/reviewer/agent/external)
    out of the API messages list — Claude only accepts user/assistant. Non-conversation
    Identity classes re-enter YARNNN's reasoning via /workspace/system/recent.md
    (Layer 2 pointer in the compact index, ReadFile on demand).

    ADR-221 Commit B: only the most-recent assistant turn carrying `tool_history`
    keeps full structured tool_use/tool_result blocks. Older assistant tool turns
    collapse to one-line `[Called X: result]` summaries. Cites Claude Code's
    "tool outputs drop first" auto-compaction precedent.

    Args:
        messages: Raw session messages from database (already windowed by caller
                  — chat handler trims to MESSAGE_WINDOW=10 before calling)
        use_structured_format: If True, the most-recent assistant tool turn uses
                               structured blocks. If False, all assistant tool
                               turns collapse to text summaries.

    Returns:
        List of messages in Anthropic API format
    """
    history = []
    global_tool_index = 0  # Global counter for unique tool IDs across all messages

    # ADR-221 Commit B: identify the most-recent assistant turn that has
    # tool_history. Only that turn keeps full structured tool_use/tool_result
    # blocks — Claude needs to see what it just did to continue the loop
    # correctly. Older assistant turns with tool_history collapse to one-line
    # `[Called X, Y, Z]` summaries — saves ~30-60% input tokens on tool-heavy
    # multi-turn sessions, and matches Claude Code's auto-compaction precedent
    # ("tool outputs drop first, then conversation summarizes").
    last_assistant_with_tools_idx = -1
    for i, m in enumerate(messages):
        if (
            m.get("role") in ("assistant", "system_agent")  # ADR-252 D4
            and (m.get("metadata") or {}).get("tool_history")
        ):
            last_assistant_with_tools_idx = i

    for m_idx, m in enumerate(messages):
        role = m["role"]
        # ADR-221 Commit A: filter non-conversation roles. Per ADR-219 (migration 161)
        # session_messages.role widened to {user, assistant, system, reviewer, agent,
        # external} — six Identity classes. Only user/assistant rows are conversation
        # turns; the others are workspace events that surface on /chat (frontend reads
        # them directly) but never enter the Claude API messages list (Claude only
        # accepts user/assistant). The narrative-side rollup (recent.md, ADR-221
        # Commit C) is the singular re-entry point for these into YARNNN's reasoning.
        # ADR-252 D4: system_agent is the new write role; map to 'assistant'
        # for Claude API (which only accepts user/assistant).
        if role == "system_agent":
            role = "assistant"
        if role not in ("user", "assistant"):
            continue
        content = m.get("content") or ""
        metadata = m.get("metadata") or {}
        tool_history = metadata.get("tool_history", [])

        is_most_recent_with_tools = (m_idx == last_assistant_with_tools_idx)

        if (
            role == "assistant"
            and tool_history
            and use_structured_format
            and is_most_recent_with_tools
        ):
            # Most-recent assistant turn with tool_history: keep full structured
            # tool_use/tool_result blocks. Claude needs the structured shape to
            # continue the agentic loop coherently.
            #
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
            # ADR-221 Commit B: older assistant turns + non-structured fallback
            # both collapse to one-line `[Called X]` summaries. Older turns
            # don't need structured tool blocks — Claude only continues a
            # tool loop from the most-recent turn; older turns just need a
            # text trace that "I called X earlier."
            tool_summaries = []
            text_content = ""

            for item in tool_history:
                if item.get("type") == "tool_call":
                    name = item.get("name", "?")
                    result = item.get("result_summary", "")
                    if result:
                        # Brief result for older-turn awareness without bloat.
                        tool_summaries.append(f"[Called {name}: {result[:80]}]")
                    else:
                        tool_summaries.append(f"[Called {name}]")
                elif item.get("type") == "text":
                    text_content = item.get("content", "")

            if tool_summaries:
                content = " ".join(tool_summaries) + (f"\n{text_content}" if text_content else "")
            elif text_content:
                content = text_content

            history.append({"role": role, "content": content})
        else:
            # Regular message (user, or assistant without tools)
            history.append({"role": role, "content": content})

    # ADR-221 Commit C: Anthropic API requires history to start with a user
    # message. Pre-Commit-C this was enforced inside truncate_history_by_tokens;
    # post-deletion the same guard lives here. Strip leading assistant rows
    # (rare — only happens if filtering out non-conversation roles in Commit A
    # leaves an assistant turn first).
    while history and history[0].get("role") == "assistant":
        history = history[1:]

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
# In-Session Compaction — DELETED (ADR-221 Commit C)
# =============================================================================
# `maybe_compact_history`, `COMPACTION_PROMPT`, `COMPACTION_THRESHOLD`,
# `truncate_history_by_tokens`, and `estimate_message_tokens` were deleted
# per ADR-221's singular-implementation discipline. Compaction is now
# filesystem-native via `/workspace/system/conversation.md` (written every
# 5 user messages by `_write_conversation_summary`); YARNNN reads it on
# demand via `ReadFile` when older context is needed.
#
# The 10-message window in the chat handler is the singular truncation.
# With ADR-221 Commit B's tool-history collapse on older turns, even a
# tool-heavy 10-message window stays well under Claude's input budget.
#
# `chat_sessions.compaction_summary` column was dropped in migration 174
# (ADR-221 Phase 2 follow-up, 2026-05-15). Filesystem-native conversation.md
# is the singular compaction substrate.


def _compact_tool_input(tool_input: object) -> str:
    """ADR-398 D1: one-line essence of a tool call's input for the operator.

    Never full content — the load-bearing locator fields only (path, query,
    slug, action). Server-composed truth, not an FE guess (the ADR-351 D4
    distinction): we show what the runtime received, compacted.
    """
    if not isinstance(tool_input, dict):
        return ""
    for key in ("path", "query", "slug", "pattern", "domain", "action", "platform"):
        val = tool_input.get(key)
        if isinstance(val, str) and val.strip():
            return f"{key}={val.strip()[:120]}"
    # Fallback: first short scalar value, key-labeled.
    for key, val in tool_input.items():
        if key == "content":
            continue
        if isinstance(val, (str, int, float, bool)) and str(val).strip():
            return f"{key}={str(val).strip()[:120]}"
    return ""


async def _load_task_context(
    client,
    user_id: str,
    task_slug: str,
) -> Optional[str]:
    """
    Load recurrence context for TP when user is on a work-detail surface.

    Reads the recurrence YAML declaration, last 5 run-log entries, latest
    output preview, and assigned agent info. All substrate paths resolve
    via the conventions module (ADR-231 D2 / ADR-262 D1).
    """
    import re
    from services.conventions import (
        RECURRENCES_PATH,
        report_root,
        report_run_log_path,
    )
    from services.recurrence import walk_workspace_recurrences
    from services.workspace import UserMemory

    # ADR-261 D1: a recurrence is {slug, schedule, prompt}. The operator-facing
    # display name (when set) lives under options.display_name per the Schedule
    # primitive's optional metadata convention.
    recurrences = walk_workspace_recurrences(client, user_id)
    rec = next((r for r in recurrences if r.slug == task_slug), None)
    if rec is None:
        return None

    um = UserMemory(client, user_id)

    def _strip_ws_prefix(p: str) -> str:
        return p[len("/workspace/"):] if p.startswith("/workspace/") else p

    # 1. Display title — option override, else slug
    task_title = (rec.options or {}).get("display_name") or rec.slug

    # 2. Read run_log.md — last 5 ## sections
    run_log_last_5 = ""
    run_log = await um.read(_strip_ws_prefix(report_run_log_path(task_slug)))
    if run_log:
        sections = re.split(r"(?=^## )", run_log, flags=re.MULTILINE)
        sections = [s.strip() for s in sections if s.strip()]
        last_5 = sections[-5:] if len(sections) > 5 else sections
        run_log_last_5 = "\n\n".join(last_5)

    # 3. Read latest output preview — list dated folders under report_root and
    #    pick the most recent. Cheap convenience read; not in a hot loop.
    output_preview = ""
    try:
        recent = (
            client.table("workspace_files")
            .select("path,content")
            .eq("user_id", user_id)
            .like("path", f"{report_root(task_slug)}/%/output.md")
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        if recent.data:
            output_content = recent.data[0].get("content") or ""
            if output_content:
                output_preview = output_content[:500]
                if len(output_content) > 500:
                    output_preview += "\n[truncated...]"
    except Exception as e:
        logger.debug(f"[TASK_CONTEXT] Output preview read failed: {e}")

    # Build formatted context
    parts = [f'You are helping the operator manage the recurrence "{task_title}".']
    parts.append(f"\nRecurrence file: {RECURRENCES_PATH}")
    if rec.schedule:
        parts.append(f"Schedule: {rec.schedule}{' (paused)' if rec.paused else ''}")
    elif rec.paused:
        parts.append("Schedule: reactive (paused)")
    else:
        parts.append("Schedule: reactive")

    parts.append(f"\nPrompt:\n{rec.prompt}")

    if run_log_last_5:
        parts.append(f"\nRecent run log:\n{run_log_last_5}")

    if output_preview:
        parts.append(f"\nLatest output preview:\n{output_preview}")

    return "\n".join(parts)


# ADR-059: Background extraction removed — TP only knows what users explicitly state.


# =============================================================================
# Chat Attach — Ephemeral File Upload (ADR-249)
# =============================================================================

@router.post("/feed/attach")
async def chat_attach(
    auth: UserClient,
    file: UploadFile = File(...),
):
    """Upload a file for ephemeral use in the current chat turn.

    ADR-249 ephemeral path: file is uploaded to the Anthropic Files API
    and a file_id is returned. The caller includes file_id in the next
    ChatRequest.file_attachments list. Claude reads the file natively
    in that turn. File expires after Anthropic's TTL (~24h).

    Nothing is written to the workspace or database.

    Supported types:
    - PDF (read natively by Claude API)
    - TXT, MD (read as text)
    - DOCX (extracted server-side → text block)
    - Images: use the existing base64 inline path (ChatRequest.images)
    """
    import anthropic as _anthropic

    SUPPORTED = {
        "application/pdf": "pdf",
        "text/plain": "txt",
        "text/markdown": "md",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    }
    MAX_SIZE = 20 * 1024 * 1024  # 20MB

    if file is None:
        raise HTTPException(status_code=400, detail="file is required")

    content_type = file.content_type or ""
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    file_type = SUPPORTED.get(content_type) or (ext if ext in ("pdf", "txt", "md", "docx") else None)
    if not file_type:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type for chat attach. Supported: PDF, TXT, MD, DOCX. For images use the base64 inline path."
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 20MB)")
    if len(file_bytes) < 10:
        raise HTTPException(status_code=400, detail="File is empty")

    filename = file.filename or f"document.{file_type}"

    # DOCX: extract text server-side (not natively supported by Files API)
    if file_type == "docx":
        from services.documents import extract_text_from_docx
        text, _ = await extract_text_from_docx(file_bytes)
        if not text or len(text.strip()) < 20:
            raise HTTPException(status_code=422, detail="Could not extract text from DOCX")
        return {
            "type": "text_block",
            "filename": filename,
            "content": text[:50000],  # Cap at ~50K chars for context window safety
        }

    # PDF / TXT / MD: upload to Anthropic Files API
    try:
        import os
        # Memory discipline: close the httpx pool Anthropic() opens
        # (see docs/infrastructure/memory-and-client-lifecycle.md).
        with _anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"]) as client:
            response = client.beta.files.upload(
                file=(filename, file_bytes, content_type or f"application/{file_type}"),
            )
        file_id = response.id
        logger.info(f"[CHAT-ATTACH] Uploaded {filename} → file_id={file_id} for user={auth.user_id}")
    except Exception as e:
        logger.error(f"[CHAT-ATTACH] Anthropic Files API upload failed: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to upload file to Anthropic: {e}")

    return {
        "type": "file_id",
        "file_id": file_id,
        "filename": filename,
        "mime_type": content_type or f"application/{file_type}",
    }


# =============================================================================
# Chat Endpoints
# =============================================================================

@router.post("/feed")
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
    # ADR-172: No message limit gate — balance is the only gate

    # Unified session: always global — one conversation per workspace.
    # Surface context (agent/task being viewed) is metadata on messages,
    # not a session boundary. TP adapts working memory based on surface.
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
        # ADR-159 Phase 2: Write final conversation.md on session close
        prev_messages = await get_session_messages(auth.client, session["previous_session_id"])
        if prev_messages:
            await _write_conversation_summary(auth, prev_messages)

    # ADR-159: Load existing messages with rolling window.
    # Only last N messages sent to API. Older context in conversation.md.
    MESSAGE_WINDOW = 10  # ~5 user+assistant pairs
    existing_messages = await get_session_messages(auth.client, session_id)

    # Write conversation.md every 5 user messages for rolling compaction
    user_msg_count = sum(1 for m in existing_messages if m.get("role") == "user")
    if user_msg_count > 0 and user_msg_count % 5 == 0:
        await _write_conversation_summary(auth, existing_messages)

    # Window: keep only last N messages for API call
    # Full history stays in DB for chat UI display.
    # ADR-221 Commit C: the 10-message window IS the singular truncation —
    # ADR-067 Phase 3's 40K-token in-session LLM compaction has been deleted.
    # Compaction is filesystem-native via /workspace/system/conversation.md
    # (written every 5 user messages by _write_conversation_summary).
    # YARNNN reads conversation.md on demand via ReadFile.
    if len(existing_messages) > MESSAGE_WINDOW:
        existing_messages = existing_messages[-MESSAGE_WINDOW:]

    history = build_history_for_claude(
        existing_messages,
        use_structured_format=True,
    )
    logger.info(
        f"[YARNNN] Loaded {len(existing_messages)} messages, built {len(history)} history entries"
    )

    # ── ADR-255 D3: Three clean dispatch functions ───────────────────────────
    # No optimistic placeholder. No nested control flow.
    # Each path is self-contained: write to DB → yield SSE → done.

    async def _dispatch_execution_turn(router_result):
        """Deterministic execution router result → system_agent narration → done."""
        narration = router_result.get("narration", "Done.")
        routed_tools = router_result.get("tools_used", [])
        await append_message(auth.client, session_id, "system_agent", narration, {
            "tools_used": routed_tools, "tool_history": [],
            "pulse": "addressed", "weight": "routine", "execution_router": True,
            "authored_by": "system:execution-router",  # actor identity (2026-06-30)
        })
        yield f"data: {json.dumps({'content': narration})}\n\n"
        yield f"data: {json.dumps({'done': True, 'session_id': session_id, 'tools_used': routed_tools})}\n\n"
        logger.info("[EXEC_ROUTER] routed — tools=%s for: %.50r", routed_tools, request.content)

    async def _dispatch_reviewer_turn(images_for_api, invocation_id: str):
        """Reviewer handles every non-execution turn via the addressed wake source.

        ADR-296 v2 D1: routes through wake_sources.addressed.stream() — the
        singular SSE-streaming entry point for operator-addressed wakes.
        The wake source handles envelope assembly + Reviewer invocation +
        progress event generation; this route maps the typed event stream
        to SSE frames + finalizes the execution_events row.
        """
        from agents.occupant_contract import FREDDIE_MODEL_IDENTITY  # ADR-315
        from services.freddie_chat_surfacing import write_freddie_message
        from services.supabase import get_service_client, resolve_principal_id
        from services.telemetry import record_execution_event
        from services.wake_sources.addressed import stream as wake_addressed_stream
        from datetime import timezone as _tz
        addressed_started_at = datetime.now(_tz.utc)
        # Capture-first (migration 192): attribute the addressed cycle to the
        # principal that spoke (the owner user_id on a human JWT; ADR-373).
        addressed_principal = resolve_principal_id(auth)

        # ADR-298: wake_queue is service-role-only per RLS. The addressed-wake
        # stream enqueues into wake_queue (single-lane serialization). Pass
        # a service client, not the request-scoped auth.client, otherwise the
        # INSERT silently fails with "new row violates row-level security
        # policy" mid-stream and the Reviewer cycle never starts.
        # Per addressed.stream() docstring §"Args: client: Supabase service client".
        wake_client = get_service_client()

        # Assemble route-layer inputs: conversation_window + workspace_state.
        # The wake source assembles the rest (governance envelope, operating
        # context, Reviewer invocation).
        conv_lines = []
        for m in history[-6:]:
            role_label = "Operator" if m.get("role") == "user" else "System"
            msg_content = m.get("content", "")
            if isinstance(msg_content, list):
                msg_content = " ".join(
                    b.get("text", "") for b in msg_content
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            if msg_content and isinstance(msg_content, str):
                conv_lines.append(f"{role_label}: {msg_content[:300]}")

        workspace_state_text: str | None = None
        try:
            from services.working_memory import build_working_memory, format_compact_index
            wm = await build_working_memory(auth.user_id, auth.client)
            workspace_state_text = format_compact_index(wm)
        except Exception:
            pass

        # Consume the wake-source's typed event stream + map to SSE frames.
        # System Agent narration writes happen here (route owns the
        # session_id + append_message); the wake source produces the
        # narration text via narrate_reviewer_action.
        try:
            captured_output: dict | None = None
            # ADR-398 D1: accumulate the actual-call trail for (a) live SSE
            # detail and (b) persistence on the settled Freddie row — the
            # exact metadata.tool_history contract the FE already
            # reconstructs into tool_call blocks (ADR-042).
            freddie_tool_history: list[dict] = []
            async for event in wake_addressed_stream(
                wake_client, auth.user_id,
                session_id=session_id,
                invocation_id=invocation_id,
                user_message=request.content,
                conversation_window="\n".join(conv_lines) if conv_lines else "",
                workspace_state_text=workspace_state_text or "",
                operator_locator=(request.locator or "").strip()[:200],
            ):
                etype = event.get("type")

                if etype == "progress":
                    ev = event.get("event") or {}
                    phase = ev.get("phase")
                    tool_name = ev.get("tool", "?")
                    if phase == "tool_start":
                        input_summary = _compact_tool_input(ev.get("input"))
                        freddie_tool_history.append({
                            "type": "tool_call",
                            "name": tool_name,
                            "input_summary": input_summary,
                            "result_summary": "",
                        })
                        yield f"data: {json.dumps({'reviewer_progress': True, 'phase': 'tool_start', 'tool': tool_name, 'input_summary': input_summary})}\n\n"
                    elif phase == "tool_end":
                        summary = ev.get("summary", "")
                        success = ev.get("success", True)
                        # Attach the result to the most recent open entry for
                        # this tool (calls are sequential within a wake).
                        for item in reversed(freddie_tool_history):
                            if item["name"] == tool_name and not item["result_summary"]:
                                item["result_summary"] = str(summary)[:200]
                                if not success:
                                    item["result_summary"] = f"failed: {item['result_summary']}" if summary else "failed"
                                break
                        yield f"data: {json.dumps({'reviewer_progress': True, 'phase': 'tool_end', 'tool': tool_name, 'summary': summary, 'success': success})}\n\n"

                elif etype == "text_delta":
                    # ADR-351 Phase 1: relay the Reviewer's reasoning tokens as
                    # they generate. The terminal reviewer_response (below)
                    # remains the persist+finalize point; this carries the live
                    # text so Phase 2's FE can append it to a streaming bubble
                    # instead of waiting for the whole block at cycle-end.
                    yield f"data: {json.dumps({'reviewer_progress': True, 'phase': 'text_delta', 'text': event.get('text', ''), 'round': event.get('round')})}\n\n"

                elif etype == "agent_narration":
                    tool_name = event.get("tool", "?")
                    narration = event.get("narration", "")
                    # 2026-05-25 clarify-silenced-from-feed: wake source
                    # declares the row role per-tool (Clarify → 'reviewer'
                    # for persona attribution; default → 'system_agent').
                    # Honor that decision here instead of hardcoding.
                    row_role = event.get("role", "system_agent")
                    # Actor identity (2026-06-30): a Clarify row attributed to the
                    # persona (row_role freddie/reviewer) authors as Freddie; the
                    # default reviewer-directed action authors as the system agent.
                    meta_out: dict = {
                        "tools_used": [tool_name], "tool_history": [],
                        "pulse": "addressed", "weight": "material", "reviewer_directed": True,
                        "invocation_id": invocation_id,
                        "authored_by": (
                            "freddie:reviewer"
                            if row_role in ("freddie", "reviewer")
                            else "system:reviewer-directed"
                        ),
                    }
                    # Pass through Clarify structured payload so future FE
                    # response affordances (inline button strip) have
                    # canonical data without re-parsing narration text.
                    cq = event.get("clarify_question")
                    co = event.get("clarify_options")
                    if cq:
                        meta_out["clarify_question"] = cq
                    if isinstance(co, list) and co:
                        meta_out["clarify_options"] = co
                    await append_message(auth.client, session_id, row_role, narration, meta_out)
                    yield f"data: {json.dumps({'content': narration})}\n\n"

                elif etype == "reviewer_response":
                    response_text = event.get("text", "")
                    captured_output = event.get("output")
                    await write_freddie_message(
                        auth.client, auth.user_id,
                        content=response_text,
                        verdict="addressed",
                        occupant=FREDDIE_MODEL_IDENTITY,
                        invocation_id=invocation_id,
                        pulse="addressed",
                        tool_history=freddie_tool_history or None,
                    )
                    yield f"data: {json.dumps({'reviewer_response': response_text})}\n\n"

                elif etype == "done":
                    actions = event.get("actions", [])
                    addressed_duration_ms = int(
                        (datetime.now(_tz.utc) - addressed_started_at).total_seconds() * 1000
                    )
                    out = captured_output or {}
                    # ADR-298: execution_events has SELECT-only user-JWT RLS;
                    # INSERTs require service client. Use the same wake_client
                    # constructed above for the wake_addressed_stream call —
                    # symmetric with the wake_queue write path.
                    record_execution_event(
                        wake_client, user_id=auth.user_id, slug="addressed",
                        id=invocation_id,
                        mode="judgment", trigger_type="addressed",
                        status="success", duration_ms=addressed_duration_ms,
                        input_tokens=out.get("input_tokens"),
                        output_tokens=out.get("output_tokens"),
                        cache_read_tokens=out.get("cache_read_tokens"),
                        cache_create_tokens=out.get("cache_create_tokens"),
                        model=out.get("model"),
                        tool_rounds=out.get("tool_rounds"),
                        wake_source="addressed",  # ADR-296 v2 D1
                        funnel_decision="escalate",  # ADR-296 v2 D2: operator presence is wake-warrant
                        principal_id=addressed_principal,
                    )
                    logger.info(
                        "[REVIEWER] addressed for user=%s actions=%d",
                        auth.user_id[:8], len(actions),
                    )
                    yield f"data: {json.dumps({'done': True, 'session_id': session_id, 'tools_used': [a.get('tool','') for a in actions]})}\n\n"

                elif etype == "error":
                    err = event.get("error", "Reviewer returned no response")
                    raise RuntimeError(err)

        except Exception as _reviewer_exc:
            addressed_duration_ms = int(
                (datetime.now(_tz.utc) - addressed_started_at).total_seconds() * 1000
            )
            # ADR-298: service client for execution_events INSERT (RLS gate).
            record_execution_event(
                wake_client, user_id=auth.user_id, slug="addressed",
                id=invocation_id,
                mode="judgment", trigger_type="addressed",
                status="failed", error_reason="exception",
                error_detail=str(_reviewer_exc),
                duration_ms=addressed_duration_ms,
                wake_source="addressed",  # ADR-296 v2 D1
                funnel_decision="escalate",  # ADR-296 v2 D2: operator presence escalated; Reviewer raised
                principal_id=addressed_principal,
            )
            raise

    # ── Main stream dispatcher ────────────────────────────────────────────────
    async def response_stream():
        # Balance gate
        from services.platform_limits import check_balance
        balance_ok, effective_balance = check_balance(auth.client, auth.user_id)
        if not balance_ok:
            yield f"data: {json.dumps({'balance_exhausted': True, 'balance_usd': round(effective_balance, 4)})}\n\n"
            return

        try:
            # ADR-289 D2 + D3: pre-generate the invocation atom id for this
            # addressed cycle. Stamp on the operator's message metadata so the
            # entire cycle's narrative rows (user question + Reviewer reply +
            # system_agent action narrations) share one invocation_id —
            # FE groups them into one invocation card on the Feed surface.
            import uuid as _uuid
            invocation_id = str(_uuid.uuid4())

            # Write user message to narrative
            await append_message(auth.client, session_id, "user", request.content, {
                "pulse": "addressed",
                "invocation_id": invocation_id,
                "authored_by": "operator",  # actor identity (2026-06-30)
            })
            logger.info("[SYSTEM_AGENT] turn for: %.50r", request.content)

            # Build media blocks (images + file attachments)
            images_for_api = None
            if request.images:
                images_for_api = [
                    {"type": "image", "source": {"type": "base64",
                     "media_type": img.media_type, "data": img.data}}
                    for img in request.images
                ]
            if request.file_attachments:
                doc_blocks = [
                    {"type": "document", "source": {"type": "file", "file_id": att.file_id},
                     "title": att.filename}
                    for att in request.file_attachments
                ]
                images_for_api = (images_for_api or []) + doc_blocks

            # Path 1: Execution router — zero LLM, mechanical commands
            router_result = None
            try:
                from services.execution_router import route_execution
                router_result = await route_execution(auth, request.content)
            except Exception as _e:
                logger.warning("[EXEC_ROUTER] failed: %s", _e)

            if router_result is not None:
                async for chunk in _dispatch_execution_turn(router_result):
                    yield chunk
                return

            # ADR-375 §6 chokepoint #3 — steward-presence gate (addressed path).
            # The addressed (chat→Reviewer) turn IS the steward's interface
            # (ADR-374 D2). Per ADR-374, the Phase-1 base product has no native
            # chat — so when AGENT_ENABLED is off, this path must not reach the
            # addressed wake stream (which would enqueue + wake the Reviewer).
            # Degrade gracefully: tell the operator judgment is gated, never
            # wake. The mechanical execution router (Path 1) already ran above
            # and is unaffected (zero-LLM commands keep working off-state).
            from services.agent_gating import is_agent_enabled
            if not is_agent_enabled(workspace_id=auth.user_id):
                msg = (
                    "Judgment is not enabled on this workspace. YARNNN is "
                    "serving as your attributed, cross-LLM substrate — your "
                    "files, memory, and revision history are fully available "
                    "(remember / recall / trace). The steward (judgment) "
                    "layer is a gated beta."
                )
                await append_message(auth.client, session_id, "system_agent", msg, {
                    "pulse": "addressed", "weight": "routine",
                    "invocation_id": invocation_id, "agent_disabled": True,
                    "authored_by": "system:agent-gate",  # actor identity (2026-06-30)
                })
                yield f"data: {json.dumps({'content': msg})}\n\n"
                yield f"data: {json.dumps({'done': True, 'session_id': session_id})}\n\n"
                return

            # Path 2: Reviewer (Haiku) — primary and only conversational intelligence.
            # No System Agent fallback. Reviewer is always the intelligence layer.
            # If Reviewer includes action_instruction, System Agent executes it as directed.
            # If Reviewer fails entirely, yield error — do not improvise with System Agent.
            async for chunk in _dispatch_reviewer_turn(images_for_api, invocation_id):
                yield chunk

        except Exception as e:
            import traceback
            logger.error("[STREAM] %s: %s\n%s", type(e).__name__, e, traceback.format_exc())
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        response_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/feed/history")
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


@router.get("/feed/sessions")
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
# Cooperative cancellation (Commit H, 2026-05-11) — interruption surface Mode 1
# =============================================================================

@router.post("/feed/cancel")
async def cancel_active_loop(auth: UserClient):
    """Set cancellation_requested=true on the operator's active workspace
    chat session.

    The Reviewer's invoke_freddie() loop (api/agents/freddie_agent.py)
    polls this flag at the top of every tool round; on true it exits the
    loop with a stand_down verdict and clears the flag. This is the
    server-side cooperative cancellation path used when:

      (a) the operator's own sendMessage stream isn't directly abortable
          (e.g., they navigated away mid-stream);
      (b) an autonomous cron-fired Loop wake is in flight and the
          operator wants to stop it without an HTTP stream of their own
          to abort.

    Best-effort. Returns 204 with a one-line status payload regardless of
    whether a session was found — the FE doesn't need to disambiguate;
    the realtime channel will surface the next state transition.
    """
    from services.narrative import find_active_workspace_session

    session_id = find_active_workspace_session(auth.client, auth.user_id)
    if not session_id:
        return {"ok": True, "applied": False, "reason": "no active session"}

    try:
        auth.client.table("chat_sessions").update(
            {"cancellation_requested": True}
        ).eq("id", session_id).execute()
        return {"ok": True, "applied": True, "session_id": session_id}
    except Exception as exc:
        return {"ok": False, "applied": False, "reason": f"db error: {exc}"}


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
