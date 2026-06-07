"""Cockpit awareness — the Reviewer system prompt's tool-surface section.
ADR-258 D5 (drift-resistance) + ADR-323 (collapsed to DP22).

ADR-323 finished the persona-frame collapse ADR-306 scoped too narrowly: the
substrate map (build_filesystem_block — substrate pedagogy) and the operating
posture (_OPERATING_POSTURE — rules of judgment + fiduciary posture) were
DELETED from this section, because Derived Principle 22 says the system prompt
carries ONLY the model↔runtime interface contract. Substrate pedagogy lives in
the bundle's _workspace_guide.md (ADR-281); rules of judgment + posture live in
principles.md (DP24); the action-grammar lives in the minimal persona frame
(reviewer_agent.py). What remains here is the TOOL SURFACE only — the one
genuine interface fact this section owns (which tools the Reviewer has, which it
doesn't, that Schedule is its own job).

The tool block is still GENERATED from the REVIEWER_PRIMITIVES registry
(ADR-258 D5 drift-resistance preserved) so it cannot drift from runtime behavior.

Pure function. No I/O. Composed at module-level once per process.
"""
from __future__ import annotations

# ADR-323: the workspace_paths imports are gone — build_filesystem_block (the
# only consumer of those path constants) was deleted. The substrate map lives in
# _workspace_guide.md (ADR-281), not in this system-prompt section.


def _one_line(text: str, limit: int = 90) -> str:
    """Collapse a (potentially multi-line) tool description to one line."""
    if not text:
        return ""
    flat = " ".join(text.strip().split())
    return (flat[: limit - 3] + "...") if len(flat) > limit else flat


# ADR-323: build_filesystem_block DELETED. Per Derived Principle 22 (the system
# prompt carries only the model↔runtime interface contract), the substrate map —
# what each file is for, the permission topology, the domain-substrate
# convention pointers — is SUBSTRATE PEDAGOGY and lives in the bundle's
# `/workspace/_workspace_guide.md` (ADR-281, read at every wake) + the per-wake
# envelope's own labeled headers (which render each governance/persona/domain
# file with its full path). The one genuine interface fact (the write boundary:
# author everything except governance/ + system/) migrated UP into the minimal
# persona frame's "How you act" section. The kernel no longer re-teaches paths
# the guide explains and the envelope shows.


def build_tools_block(allowed_tool_names: set[str] | None = None) -> str:
    """Tool block — composed from REVIEWER_PRIMITIVES registry at call time.

    ADR-258 (revised 2026-05-08) + ADR-296 v2 D3: Reviewer uses the curated
    REVIEWER_PRIMITIVES subset (20 tools after ADR-296 v2 removed
    FireInvocation per D3 — Reviewer does not self-invoke), not the full
    CHAT_PRIMITIVES set. Imported lazily to avoid circular imports.
    """
    from services.primitives.registry import REVIEWER_PRIMITIVES

    lines = ["### Your tool surface (Reviewer-curated primitives)", ""]
    for tool in REVIEWER_PRIMITIVES:
        name = tool.get("name", "")
        if not name:
            continue
        if allowed_tool_names and name not in allowed_tool_names:
            continue
        desc = _one_line(tool.get("description") or "")
        lines.append(f"- `{name}` — {desc}")

    # ReturnVerdict is Reviewer-specific (not in REVIEWER_PRIMITIVES).
    lines.append(
        "- `ReturnVerdict` — close the turn with verdict + reasoning + confidence. "
        "Always last."
    )

    lines.append("")
    lines.append(
        "**Not in your curated tool surface** (per ADR-258 revised — the "
        "REVIEWER_PRIMITIVES subset of CHAT_PRIMITIVES is curated for the "
        "judgment-seat role): ManageDomains, ManageAgent, "
        "RuntimeDispatch, RepurposeOutput, EditEntity, "
        "ExecuteProposal, RejectProposal. These shape orchestration / agent "
        "scaffolding — not authority-escalation gates. "
        "ExecuteProposal / RejectProposal are dispatched on your behalf by "
        "review_proposal_dispatch after your verdict (you don't call them "
        "directly). If you want operator-scaffolding changes, surface a "
        "Clarify; the operator runs YARNNN-chat which has these tools."
    )
    lines.append("")
    lines.append(
        "**Schedule is in your tool surface (ADR-261 D4):** a recurrence is a "
        "self-scheduled future Reviewer session. Authoring one is your own job, "
        "not the operator's — when the operation needs a recurring check or "
        "reflection, schedule it. Every wake-up runs another bounded session "
        "that itself passes through AUTONOMY for capital gates, so self-scheduling "
        "is structurally safe."
    )
    return "\n".join(lines)


# ADR-323: _OPERATING_POSTURE DELETED. Per Derived Principle 22, rules of
# judgment + the fiduciary/stewardship posture (how-you-operate, when-substrate-
# missing, write-authority, when-things-diverge) live in principles.md (DP24) +
# the bundle's _workspace_guide.md (ADR-281); the action-grammar (tool-call-IS-
# action, close-with-verdict, the tool-use loop, the write boundary) lives in
# the minimal persona frame. The cockpit section carries ONLY the tool surface.


def build_cockpit_section(allowed_tool_names: set[str] | None = None) -> str:
    """Compose the full cockpit-awareness section for the Reviewer system prompt.

    Args:
        allowed_tool_names: optional filter — if None, all CHAT_PRIMITIVES
            tools are listed. Reviewer today gets all chat-mode primitives
            (ADR-258 D1), so callers typically pass None.

    Returns:
        Markdown section ready for inclusion in the Reviewer system prompt.
    """
    allowed = allowed_tool_names or set()
    parts = [
        "## Your operating environment",
        "",
        "You operate inside YARNNN — a workspace-native autonomous operations OS.",
        "Your substrate is a versioned filesystem with content-addressed retention",
        "and per-revision attribution (ADR-209 Authored Substrate). Your program's",
        "`/workspace/_workspace_guide.md` (read at every wake) declares the substrate",
        "topology — what each file is for, the wake-source taxonomy, the cadence",
        "trifecta. This section does not restate it.",
        "",
        # ADR-323: build_filesystem_block + _OPERATING_POSTURE DELETED. Per Derived
        # Principle 22 (the system prompt carries only the model↔runtime interface
        # contract), substrate pedagogy lives in _workspace_guide.md (ADR-281),
        # rules of judgment + fiduciary posture live in principles.md (DP24), and
        # the action-grammar (tool-call-IS-action, close-with-verdict, the tool-use
        # loop) lives in the minimal persona frame. The cockpit section now carries
        # ONLY the tool surface (interface), not re-taught substrate or posture.
        build_tools_block(allowed),
    ]
    return "\n".join(parts)
