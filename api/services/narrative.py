"""ADR-219 Commit 2 — narrative substrate write path.

Per FOUNDATIONS v6.8 Axiom 9 + invocation-and-narrative.md, every invocation
in YARNNN emits exactly one chat-shaped narrative entry. This module is the
SINGLE write path into `session_messages`. Every other call site that wants
to surface an invocation in the operator-facing timeline calls
`write_narrative_entry()` — no parallel inserts, no shadow paths.

Migration 161 widened `session_messages.role` to accept the full Identity
taxonomy: user, assistant, system, reviewer, agent, external.

The narrative envelope (per ADR-219 D1) lives in `metadata` JSONB:

    invocation_id  — links to the agent_runs row (or None for operator
                     messages / external MCP calls that don't produce one)
    task_slug      — task nameplate this invocation was labeled with, or
                     None for inline / unlabelled invocations (ADR-219 D4)
    pulse          — periodic | reactive | addressed | heartbeat
    weight         — material | routine | housekeeping (rendering policy
                     per ADR-219 D3 / D5)
    summary        — one-line headline; collapsed-rendering text
    provenance     — list of substrate pointers (output folder paths,
                     decisions.md line refs, _performance.md anchors).

This file is deliberately small. Storage uses the existing
`append_session_message` RPC (atomic sequence_number assignment) with a
direct-insert fallback that preserves sequence semantics. No new table.
No write-ahead-log shape. No buffering.

Failure discipline: when the operator's chat session is the target and
the session lookup fails, return None (best-effort surfacing, identical
to reviewer_chat_surfacing's discipline). When session_id is provided
explicitly, raise on failure — the caller asked us to write to a
specific row and we couldn't.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable, Literal, Optional

logger = logging.getLogger(__name__)


NarrativeRole = Literal[
    "user", "assistant", "system", "reviewer", "agent", "external"
]
"""The six Identity classes that can author a narrative entry. Mirrors the
session_messages.role CHECK constraint (migration 161). Validation lives
here at the application layer; the constraint is the database backstop.
"""

VALID_ROLES: frozenset[str] = frozenset(
    {"user", "assistant", "system", "reviewer", "agent", "external"}
)


NarrativePulse = Literal["periodic", "reactive", "addressed", "heartbeat"]
"""Axiom 4 Trigger viewed through the Identity lens. Per
invocation-and-narrative.md §2."""

VALID_PULSES: frozenset[str] = frozenset(
    {"periodic", "reactive", "addressed", "heartbeat"}
)


NarrativeWeight = Literal["material", "routine", "housekeeping"]
"""Render-layer policy per ADR-219 D3 / D5. Log layer is complete; UI
surfaces the gradient proportionally."""

VALID_WEIGHTS: frozenset[str] = frozenset(
    {"material", "routine", "housekeeping"}
)


def write_narrative_entry(
    client: Any,
    session_id: str,
    *,
    role: NarrativeRole,
    summary: str,
    body: Optional[str] = None,
    pulse: NarrativePulse = "addressed",
    weight: Optional[NarrativeWeight] = None,
    invocation_id: Optional[str] = None,
    task_slug: Optional[str] = None,
    provenance: Optional[list[dict[str, Any]]] = None,
    extra_metadata: Optional[dict[str, Any]] = None,
) -> Optional[dict]:
    """Emit one narrative entry for one invocation.

    Args:
        client: Supabase client (user JWT or service key, caller's choice;
            session_messages RLS is permissive for the session owner).
        session_id: target chat session row id. Required — if you don't
            have one yet, resolve via routes.chat.get_or_create_session
            or services.reviewer_chat_surfacing._find_active_workspace_session
            before calling.
        role: Identity class of the invocation per VALID_ROLES.
        summary: one-line headline. Always required. Used for collapsed
            rendering and as `content` in session_messages (so existing
            chat history readers continue to work without metadata
            introspection).
        body: optional richer content. When provided, becomes the
            `content` field; `summary` is preserved in `metadata.summary`.
            When omitted, `summary` is the `content`.
        pulse: trigger sub-shape. Defaults to 'addressed' (operator-driven)
            because that's the most common non-default — task pipeline +
            back-office callers always pass an explicit pulse.
        weight: rendering weight. When None, applies the default policy
            (resolve_default_weight); callers who know better should pass
            an explicit value.
        invocation_id: agent_runs.id for invocations produced by the task
            pipeline / agent execution. None for operator messages and
            for external MCP calls (Commit 6).
        task_slug: task nameplate label per ADR-219 D4. None for inline
            actions and unlabelled workspace events.
        provenance: list of {"path": ..., "kind": ...} substrate pointers
            for drill-in. Frontend renders as a footer of clickable refs.
        extra_metadata: pass-through for caller-specific fields that
            haven't earned envelope status yet (e.g. `tools_used`,
            `model`, `input_tokens`, `system_card`). Merged under the
            envelope; envelope keys take precedence on collision.

    Returns:
        The inserted session_messages row dict on success, or None on
        graceful failure paths (RPC + direct-insert both raised). Errors
        are logged at WARNING; the caller decides whether to escalate.

    Raises:
        ValueError: when role/pulse/weight is outside the allowed set,
            or when summary is empty. These are programmer errors, not
            runtime conditions — the migration's CHECK constraint plus
            UI rendering both depend on valid values.
    """
    if not session_id:
        raise ValueError("session_id is required")
    if not role or role not in VALID_ROLES:
        raise ValueError(
            f"invalid role {role!r}; expected one of {sorted(VALID_ROLES)}"
        )
    if pulse not in VALID_PULSES:
        raise ValueError(
            f"invalid pulse {pulse!r}; expected one of {sorted(VALID_PULSES)}"
        )

    summary = (summary or "").strip()
    if not summary:
        raise ValueError("summary is required (one-line headline)")

    resolved_weight: NarrativeWeight = weight or resolve_default_weight(
        role=role, pulse=pulse, has_invocation=invocation_id is not None
    )
    if resolved_weight not in VALID_WEIGHTS:
        raise ValueError(
            f"invalid weight {resolved_weight!r}; expected one of {sorted(VALID_WEIGHTS)}"
        )

    content = body if body is not None else summary

    envelope: dict[str, Any] = {
        "summary": summary,
        "pulse": pulse,
        "weight": resolved_weight,
    }
    if invocation_id:
        envelope["invocation_id"] = invocation_id
    if task_slug:
        envelope["task_slug"] = task_slug
    if provenance:
        envelope["provenance"] = list(provenance)

    metadata: dict[str, Any] = {}
    if extra_metadata:
        metadata.update(extra_metadata)
    metadata.update(envelope)  # envelope wins on collision

    try:
        result = client.rpc(
            "append_session_message",
            {
                "p_session_id": session_id,
                "p_role": role,
                "p_content": content,
                "p_metadata": metadata,
            },
        ).execute()
        return result.data
    except Exception as rpc_exc:
        logger.warning(
            "[NARRATIVE] RPC append_session_message failed; falling back to direct insert: %s",
            rpc_exc,
        )

    # Direct-insert fallback. Manual sequence_number — best-effort, races
    # are rare and resolve next read.
    try:
        seq = (
            client.table("session_messages")
            .select("sequence_number")
            .eq("session_id", session_id)
            .order("sequence_number", desc=True)
            .limit(1)
            .execute()
        )
        next_seq = 1
        if seq.data:
            next_seq = int(seq.data[0]["sequence_number"]) + 1

        result = (
            client.table("session_messages")
            .insert(
                {
                    "session_id": session_id,
                    "role": role,
                    "content": content,
                    "sequence_number": next_seq,
                    "metadata": metadata,
                }
            )
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception as insert_exc:
        logger.warning(
            "[NARRATIVE] direct insert failed for session=%s role=%s: %s",
            session_id[:8] if session_id else "?",
            role,
            insert_exc,
        )
        return None


def resolve_default_weight(
    *,
    role: str,
    pulse: str,
    has_invocation: bool,
) -> NarrativeWeight:
    """Default weight policy per ADR-219 D3.

    Callers should override when they have task-shape context (e.g. a
    `produces_deliverable` first-of-day delivery is material; a recurring
    no-change run is routine; back-office cleanup that found nothing is
    housekeeping). The defaults below catch the cases where the caller
    doesn't have that context.

    Policy:
        operator messages   → material (operator intent is always material)
        reviewer verdicts   → material (every verdict is material by D3)
        external MCP calls  → routine (per D3 default for pull_context;
                              remember_this overrides to material)
        addressed YARNNN    → material when an invocation produced output
                              (has_invocation), else routine (chat-only
                              answer with no substrate write)
        periodic / reactive → routine (the workhorse default)
        heartbeat           → housekeeping
        system events       → routine
    """
    if role == "user":
        return "material"
    if role == "reviewer":
        return "material"
    if role == "external":
        return "routine"
    if role == "assistant" and pulse == "addressed":
        return "material" if has_invocation else "routine"
    if pulse == "heartbeat":
        return "housekeeping"
    return "routine"


def is_valid_envelope(metadata: Optional[dict[str, Any]]) -> bool:
    """Test gate helper — confirms a session_messages row's metadata
    carries the ADR-219 envelope. Used by the test suite (Commit 2 gate)
    and could be used by the upcoming /work filter-over-narrative
    endpoint (Commit 4) as a sanity check.

    Required keys: summary, pulse, weight. Other envelope keys are
    optional (invocation_id, task_slug, provenance) — not all invocations
    have a task slug or an agent_runs row.
    """
    if not isinstance(metadata, dict):
        return False
    if "summary" not in metadata or not metadata["summary"]:
        return False
    if metadata.get("pulse") not in VALID_PULSES:
        return False
    if metadata.get("weight") not in VALID_WEIGHTS:
        return False
    return True


__all__ = [
    "write_narrative_entry",
    "resolve_default_weight",
    "is_valid_envelope",
    "VALID_ROLES",
    "VALID_PULSES",
    "VALID_WEIGHTS",
    "NarrativeRole",
    "NarrativePulse",
    "NarrativeWeight",
]
