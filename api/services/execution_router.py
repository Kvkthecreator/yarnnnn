"""Deterministic execution router — ADR-252 Phase 2.

Pattern-matches common execution-intent operator messages and dispatches
the corresponding primitive directly — zero LLM call. For unrecognized
patterns, returns None and the caller falls through to the full System
Agent LLM stream.

Coverage: the ~80% of execution turns that are imperative commands with
a clearly-named slug or well-known operation. Matches are case-insensitive
on the cleaned message text.

Unmatched turns still cost a Sonnet call (same as Phase 1). Phase 2
doesn't eliminate all LLM spend on execution turns — it eliminates it
for the common, repetitive ones. Complex execution (multi-step, ambiguous
slug) still goes through the LLM.

Return shape:
    None            — no match, caller should fall through to LLM stream
    dict with keys:
        narration   — str: one-line System Agent narration written to DB
        result      — dict: the primitive's return value (for caller logging)
        tools_used  — list[str]: primitive names dispatched (mirrors stream shape)

Never raises. All errors return None (safe fallthrough).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pattern registry
# ---------------------------------------------------------------------------
# Each pattern is a (compiled_regex, handler_fn) pair. Matched in order;
# first match wins. Handler receives (auth, match, message) and returns a
# result dict or None on failure.

_patterns: list[tuple[re.Pattern, Any]] = []


def _register(pattern: str):
    """Decorator that registers a handler for a compiled regex pattern."""
    def decorator(fn):
        _patterns.append((re.compile(pattern, re.IGNORECASE), fn))
        return fn
    return decorator


# ---------------------------------------------------------------------------
# Slug extraction helper
# ---------------------------------------------------------------------------

def _extract_slug(text: str, match: re.Match) -> Optional[str]:
    """Extract named group 'slug' from match, normalise to kebab-case."""
    try:
        slug = match.group("slug").strip().lower()
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = re.sub(r"[^a-z0-9\-]", "", slug)
        return slug or None
    except (IndexError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Pattern handlers
# ---------------------------------------------------------------------------

@_register(
    r"(?:fire|run|trigger|execute|start)\s+(?:the\s+)?(?P<slug>[\w][\w\s\-]*?)(?:\s+(?:now|recurrence|invocation|recurrence now))?\s*$"
)
async def _handle_fire(auth: Any, match: re.Match, _msg: str) -> Optional[dict]:
    """FireInvocation: "fire signal-evaluation", "run trading-signal now"."""
    from services.primitives.fire_invocation import handle_fire_invocation
    from services.recurrence import walk_workspace_recurrences

    slug = _extract_slug(_msg, match)
    if not slug:
        return None

    # Resolve shape from the workspace recurrence declarations
    try:
        import asyncio
        decls = await asyncio.to_thread(walk_workspace_recurrences, auth.client, auth.user_id)
        matched = next((d for d in decls if d.slug == slug), None)
        if not matched:
            # Try prefix match (e.g. "signal" → "signal-evaluation")
            matched = next((d for d in decls if d.slug.startswith(slug)), None)
        if not matched:
            logger.debug("[EXEC_ROUTER] no recurrence found for slug=%r", slug)
            return None
        shape = matched.shape.value
        domain = matched.domain
        resolved_slug = matched.slug
    except Exception as exc:
        logger.warning("[EXEC_ROUTER] recurrence walk failed: %s", exc)
        return None

    inp = {"shape": shape, "slug": resolved_slug}
    if domain:
        inp["domain"] = domain

    result = await handle_fire_invocation(auth, inp)
    narration = (
        f"Fired `{resolved_slug}`. "
        f"{result.get('message', 'Invocation dispatched.')}"
    )
    return {"narration": narration, "result": result, "tools_used": ["FireInvocation"]}


@_register(
    r"(?:pause|stop|disable|suspend)\s+(?:the\s+)?(?P<slug>[\w][\w\s\-]*?)(?:\s+recurrence)?\s*$"
)
async def _handle_pause(auth: Any, match: re.Match, _msg: str) -> Optional[dict]:
    """ManageRecurrence pause: "pause signal-evaluation", "stop trading-signal"."""
    from services.primitives.schedule import handle_schedule
    from services.recurrence import walk_workspace_recurrences

    slug = _extract_slug(_msg, match)
    if not slug:
        return None

    try:
        import asyncio
        decls = await asyncio.to_thread(walk_workspace_recurrences, auth.client, auth.user_id)
        matched = next((d for d in decls if d.slug == slug), None)
        if not matched:
            matched = next((d for d in decls if d.slug.startswith(slug)), None)
        if not matched:
            return None
        shape = matched.shape.value
        domain = matched.domain
        resolved_slug = matched.slug
    except Exception as exc:
        logger.warning("[EXEC_ROUTER] recurrence walk failed: %s", exc)
        return None

    # ADR-274: operator-typed regex command → operator-attributed authorship.
    inp = {"action": "pause", "shape": shape, "slug": resolved_slug, "authored_by": "operator"}
    if domain:
        inp["domain"] = domain

    result = await handle_schedule(auth, inp)
    narration = f"Paused `{resolved_slug}`."
    return {"narration": narration, "result": result, "tools_used": ["ManageRecurrence"]}


@_register(
    r"(?:resume|unpause|enable|restart)\s+(?:the\s+)?(?P<slug>[\w][\w\s\-]*?)(?:\s+recurrence)?\s*$"
)
async def _handle_resume(auth: Any, match: re.Match, _msg: str) -> Optional[dict]:
    """ManageRecurrence resume: "resume signal-evaluation"."""
    from services.primitives.schedule import handle_schedule
    from services.recurrence import walk_workspace_recurrences

    slug = _extract_slug(_msg, match)
    if not slug:
        return None

    try:
        import asyncio
        decls = await asyncio.to_thread(walk_workspace_recurrences, auth.client, auth.user_id)
        matched = next((d for d in decls if d.slug == slug), None)
        if not matched:
            matched = next((d for d in decls if d.slug.startswith(slug)), None)
        if not matched:
            return None
        shape = matched.shape.value
        domain = matched.domain
        resolved_slug = matched.slug
    except Exception as exc:
        logger.warning("[EXEC_ROUTER] recurrence walk failed: %s", exc)
        return None

    # ADR-274: operator-typed regex command → operator-attributed authorship.
    inp = {"action": "resume", "shape": shape, "slug": resolved_slug, "authored_by": "operator"}
    if domain:
        inp["domain"] = domain

    result = await handle_schedule(auth, inp)
    narration = f"Resumed `{resolved_slug}`."
    return {"narration": narration, "result": result, "tools_used": ["ManageRecurrence"]}


@_register(
    r"(?:list|show me|show|what are|give me)\s+(?:my\s+|all\s+|the\s+)?(?:active\s+)?recurrences?\s*$"
)
async def _handle_list_recurrences(auth: Any, _match: re.Match, _msg: str) -> Optional[dict]:
    """ListFiles: "list my recurrences", "show recurrences"."""
    from services.recurrence import walk_workspace_recurrences

    try:
        import asyncio
        decls = await asyncio.to_thread(walk_workspace_recurrences, auth.client, auth.user_id)
        active = [d for d in decls if not getattr(d, "paused", False)]
        paused = [d for d in decls if getattr(d, "paused", False)]

        lines = ["**Active recurrences:**"]
        for d in active:
            sched = d.schedule or "on demand"
            lines.append(f"- `{d.slug}` ({d.shape.value}) — {sched}")
        if paused:
            lines.append("\n**Paused:**")
            for d in paused:
                lines.append(f"- `{d.slug}` ({d.shape.value})")
        if not active and not paused:
            lines = ["No recurrences declared yet."]

        narration = "\n".join(lines)
        return {"narration": narration, "result": {"declarations": len(decls)}, "tools_used": []}
    except Exception as exc:
        logger.warning("[EXEC_ROUTER] list_recurrences failed: %s", exc)
        return None


@_register(
    r"(?:read|show me|open|get|fetch|display)\s+(?P<slug>[/\w][\w/\.\-_]*\.md)\s*$"
)
async def _handle_read_file(auth: Any, match: re.Match, _msg: str) -> Optional[dict]:
    """ReadFile: "read /workspace/context/{domain}/_performance.md" — domain placeholder is illustrative; the regex matches any `.md` path the operator types."""
    from services.primitives.workspace import handle_read_file

    try:
        path = match.group("slug").strip()
        if not path.startswith("/workspace/"):
            path = f"/workspace/{path.lstrip('/')}"
    except (IndexError, AttributeError):
        return None

    result = await handle_read_file(auth, {"path": path})
    if not result.get("success"):
        return None  # file not found — fallthrough to LLM for better error message

    content = result.get("content", "")
    preview = content[:2000] + ("..." if len(content) > 2000 else "")
    narration = f"**{path}**\n\n{preview}"
    return {"narration": narration, "result": result, "tools_used": ["ReadFile"]}


@_register(
    r"(?:what happened|what's happened|status|how's the operation|any updates?|anything new|catch me up|what did i miss)\s*\??\s*$"
)
async def _handle_status(_auth: Any, _match: re.Match, _msg: str) -> Optional[dict]:
    """Status check — the compact index already covers this via YARNNN context.
    Return None so the LLM provides the rich answer from working memory context.
    This is intentionally a pass-through — the compact index in the prompt already
    contains the "since you were away" block. The LLM reads it and narrates.
    """
    return None  # always fall through — working memory handles this better


# ---------------------------------------------------------------------------
# NOTE: ProposeAction handler deleted (ADR-256).
# The Reviewer now calls ProposeAction as a structured tool inside its
# tool-use loop — no string pattern-matching needed. The execution router
# handles operator commands only (fire/pause/resume/list/read).
# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def route_execution(
    auth: Any,
    user_message: str,
) -> Optional[dict]:
    """Try to match and dispatch a deterministic execution pattern.

    Returns a result dict on match, None on no-match or any failure.
    Callers treat None as "run the LLM stream instead."

    Result dict shape:
        narration   str         — one-line narration for the System Agent bubble
        result      dict        — raw primitive return value
        tools_used  list[str]   — names of primitives dispatched
    """
    cleaned = user_message.strip()
    if not cleaned:
        return None

    for pattern, handler in _patterns:
        m = pattern.search(cleaned)
        if m:
            try:
                result = await handler(auth, m, cleaned)
                if result is not None:
                    logger.info(
                        "[EXEC_ROUTER] matched pattern=%r for: %.50r",
                        pattern.pattern[:40],
                        cleaned,
                    )
                    return result
            except Exception as exc:
                logger.warning(
                    "[EXEC_ROUTER] handler failed for pattern=%r: %s — falling through",
                    pattern.pattern[:40],
                    exc,
                )
                return None  # on handler error, fall through to LLM

    return None  # no pattern matched
