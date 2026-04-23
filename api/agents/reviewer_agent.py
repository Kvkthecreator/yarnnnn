"""AI occupant of the Reviewer seat — ADR-194 v2 Phase 3.

This module implements ONE occupant class (AI, Sonnet-backed) of the
Reviewer seat. It is not the Reviewer seat itself — the seat is the
architectural role and its substrate lives at `/workspace/review/`
(IDENTITY, principles, decisions, + Phase 4 roadmap files). This module
is what runs when the AI occupant fills the seat; a different file
would run when a different occupant (human via UI, external service
via adapter) fills the seat. The seat persists; occupants rotate
(FOUNDATIONS Derived Principle 14).

Role vs. occupant in two sentences:
- **The Reviewer seat** is the judgment-layer role — substrate-expressed
  at `/workspace/review/`, canonical in `docs/architecture/reviewer-substrate.md`.
- **This module** is an occupant implementation — swappable, not
  architectural. Renaming or replacing this file does not change the
  architecture; it changes which occupant class is currently available.

What this occupant does:
Fills the Reviewer seat when policy permits auto-handling. Reads the
operator's declared framework (`/workspace/review/principles.md`), the
domain's accumulated track record (`/workspace/context/{domain}/
_performance.md`), and the proposed action, then reasons in capital-EV
terms to return `approve | reject | defer`. Output is a verdict, not an
artifact — judgment-layer output shape (see THESIS "Vocabulary:
production layers vs. judgment layers").

Per FOUNDATIONS v6.0:
- Axiom 2 (Identity): this occupant is tagged `ai:reviewer-sonnet-v1`
  and fills the seat the human occupant normally fills. Principle 14:
  identical seat, different occupant.
- Axiom 3 (Purpose): independent judgment gating proposed writes — the
  fiduciary function, not production.
- Axiom 4 (Trigger): reactive — invoked by `review_proposal_dispatch`
  after proposal creation. Distinct from addressed (chat) and periodic
  (cron) triggers that production-layer entities use.
- Axiom 5 (Mechanism): mixed — Sonnet with tight structural contract;
  output shape is declared (tool use forces approve/reject/defer),
  content is judged.
- Axiom 6 (Channel): decision writes to `decisions.md` via
  `append_decision` (Stream archetype per ADR-198).
- Axiom 8 (Money-Truth): reasons against `_performance.md` rolling
  windows (ADR-195 Phase 3) — capital-EV is the reasoning posture.

On the `thinking_partner`-class designation:
This occupant shares the `thinking_partner` capability class with
YARNNN itself at the LLM-invocation level (both reason meta-cognitively
with Sonnet). This is a shared *capability class*, not a shared *layer
class*. YARNNN is a production-layer entity (composes, scaffolds,
writes memory); this occupant is a judgment-layer occupant (renders
verdicts). The architectural distinction is expressed through scope,
substrate, trigger, and development axis — not through a separate
`AGENT_TEMPLATES` entry. See docs/architecture/THESIS.md §"Vocabulary"
and docs/architecture/reviewer-substrate.md §"Review orchestration
vs. reviewer entity — the split".

Cost ceiling: ~1–2K tokens per review (small prompt + 3 short files +
structured tool output). Metered via `token_usage` ledger per ADR-171.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Literal, TypedDict

from services.anthropic import chat_completion_with_tools
from services.platform_limits import record_token_usage

logger = logging.getLogger(__name__)


#: Occupant identity string persisted on action_proposals.reviewer_identity
#: and on decisions.md entries when this occupant fills the Reviewer seat.
#: Identifies the CURRENT OCCUPANT CLASS (AI, Sonnet-backed, version 1) —
#: not the seat itself. The seat is identified structurally by the filesystem
#: home `/workspace/review/`. Bumped when prompt/model changes materially.
REVIEWER_MODEL_IDENTITY = "ai:reviewer-sonnet-v1"

#: Model slug passed to Anthropic. Keep parallel to REVIEWER_MODEL_IDENTITY.
_MODEL_SLUG = "claude-sonnet-4-6"

#: Caller string for token_usage records.
_TOKEN_CALLER = "reviewer"


class ReviewDecision(TypedDict):
    """Structured output of the AI Reviewer."""
    decision: Literal["approve", "reject", "defer"]
    reasoning: str
    #: Present when the model supplies it; may be empty for defer.
    confidence: str  # "low" | "medium" | "high"


# ---------------------------------------------------------------------------
# Tool contract — forces the model into a structured decision
# ---------------------------------------------------------------------------


_REVIEW_TOOL = {
    "name": "return_review_decision",
    "description": (
        "Return the reviewer's decision on the proposed action. "
        "Always call this tool exactly once — it is the only way to "
        "communicate the decision."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "decision": {
                "type": "string",
                "enum": ["approve", "reject", "defer"],
                "description": (
                    "'approve' → AI believes the action has positive "
                    "expected value and is within declared edge. "
                    "'reject' → AI believes the action has negative "
                    "EV or violates declared constraints. 'defer' → "
                    "AI believes stakes or ambiguity warrant human "
                    "judgment."
                ),
            },
            "reasoning": {
                "type": "string",
                "description": (
                    "Concise rationale (2–5 sentences). Reference "
                    "specific facts from _risk.md, _operator_profile.md, "
                    "or _performance.md that drove the decision. This "
                    "reasoning is appended to /workspace/review/"
                    "decisions.md verbatim."
                ),
            },
            "confidence": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": (
                    "How confident the reviewer is in this decision. "
                    "Low → prefer defer unless policy allows. "
                    "High → strong evidence from substrate."
                ),
            },
        },
        "required": ["decision", "reasoning", "confidence"],
    },
}


_SYSTEM_PROMPT = """\
You are the independent judgment seat for this operator's workspace.
You are reviewing a proposed action. You reason in **expected-value
terms**, not rule-enforcement terms.

Substrate available to you (passed in the user message):
1. principles.md    — the operator's declared review framework
2. _risk.md (if trading domain) — hard floors, non-negotiable
3. _operator_profile.md — declared strategy + style (if present)
4. _performance.md  — accumulated track record of similar actions
                      (rolling 7d / 30d / 90d windows)
5. The proposal itself — action_type, inputs, rationale, reversibility,
                         expected_effect

Your decision categories:
- **approve** — EV is clearly positive AND within declared edge AND
  below the auto-approve threshold for this domain.
- **reject** — EV is clearly negative OR violates _risk.md OR is
  outside the operator's declared strategy.
- **defer** — EV is ambiguous, stakes are high enough to warrant
  human judgment, or this is an edge case not yet represented in
  _performance.md.

Always prefer **defer** when in doubt. The operator prefers a thin
Queue of truly high-confidence auto-decisions over a noisy Queue of
marginal calls.

Reason explicitly:
- What's the upside if this action works out?
- What's the downside if it doesn't?
- Is the upside/downside ratio asymmetric?
- Given the operator's track record on similar actions, is this
  inside their edge or outside it?
- Does _risk.md explicitly prohibit this? (If so, reject.)

Call `return_review_decision` exactly once with your decision,
reasoning (2–5 sentences, concrete substrate references), and
confidence. Your reasoning will be appended verbatim to the
workspace's decisions.md — write it clearly and for the operator's
future self to read.
"""


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def review_proposal(
    client: Any,
    user_id: str,
    proposal_row: dict,
    principles_md: str,
    performance_md: str | None,
    risk_md: str | None,
    operator_profile_md: str | None,
) -> ReviewDecision | None:
    """Run the AI Reviewer against a pending proposal. Returns a
    structured decision, or None on failure (seat then defers to
    human — never auto-approves a failed review).

    Token usage is always recorded via `record_token_usage`; the
    cost is borne by the workspace owner even for defer decisions.

    Never raises.
    """
    try:
        user_message = _build_user_message(
            proposal_row=proposal_row,
            principles_md=principles_md,
            performance_md=performance_md,
            risk_md=risk_md,
            operator_profile_md=operator_profile_md,
        )

        response = await chat_completion_with_tools(
            messages=[{"role": "user", "content": user_message}],
            system=_SYSTEM_PROMPT,
            tools=[_REVIEW_TOOL],
            model=_MODEL_SLUG,
            max_tokens=1024,
            tool_choice={"type": "tool", "name": "return_review_decision"},
        )

        tool_uses = getattr(response, "tool_uses", None) or []
        usage = getattr(response, "usage", None) or {}

        # Record token usage unconditionally — even on parse failure, the
        # spend happened.
        record_token_usage(
            client,
            user_id=user_id,
            caller=_TOKEN_CALLER,
            model=_MODEL_SLUG,
            input_tokens=int(usage.get("input_tokens", 0) or 0),
            output_tokens=int(usage.get("output_tokens", 0) or 0),
            ref_id=proposal_row.get("id"),
            metadata={
                "action_type": proposal_row.get("action_type"),
                "reversibility": proposal_row.get("reversibility"),
            },
        )

        # Extract the forced tool call
        decision_call = None
        for tu in tool_uses:
            if getattr(tu, "name", None) == "return_review_decision":
                decision_call = tu
                break

        if decision_call is None:
            logger.warning(
                "[REVIEWER_AGENT] model produced no tool call for proposal=%s user=%s — "
                "seat will defer to human",
                (proposal_row.get("id") or "?")[:8],
                user_id[:8],
            )
            return None

        tool_input = getattr(decision_call, "input", None) or {}
        decision = tool_input.get("decision")
        reasoning = (tool_input.get("reasoning") or "").strip()
        confidence = tool_input.get("confidence") or "low"

        if decision not in ("approve", "reject", "defer"):
            logger.warning(
                "[REVIEWER_AGENT] invalid decision=%r for proposal=%s — deferring",
                decision,
                (proposal_row.get("id") or "?")[:8],
            )
            return None
        if not reasoning:
            logger.warning(
                "[REVIEWER_AGENT] empty reasoning for proposal=%s — deferring",
                (proposal_row.get("id") or "?")[:8],
            )
            return None

        return ReviewDecision(
            decision=decision,
            reasoning=reasoning,
            confidence=confidence,
        )
    except Exception as exc:  # noqa: BLE001 — never raise
        logger.warning(
            "[REVIEWER_AGENT] review_proposal failed for proposal=%s user=%s: %s",
            (proposal_row.get("id") or "?")[:8],
            user_id[:8],
            exc,
        )
        return None


def _build_user_message(
    *,
    proposal_row: dict,
    principles_md: str,
    performance_md: str | None,
    risk_md: str | None,
    operator_profile_md: str | None,
) -> str:
    """Assemble the user-message envelope the model reads against."""
    parts: list[str] = []
    parts.append("## Proposed action")
    parts.append("")
    parts.append(f"**action_type:** `{proposal_row.get('action_type', '?')}`")
    parts.append(f"**reversibility:** {proposal_row.get('reversibility', '?')}")
    if proposal_row.get("rationale"):
        parts.append(f"**rationale (from caller):** {proposal_row['rationale']}")
    if proposal_row.get("expected_effect"):
        parts.append(f"**expected_effect:** {proposal_row['expected_effect']}")
    risk_warnings = proposal_row.get("risk_warnings") or []
    if risk_warnings:
        parts.append(f"**risk_warnings:** {risk_warnings}")
    inputs = proposal_row.get("inputs") or {}
    parts.append("**inputs:**")
    parts.append("```json")
    parts.append(json.dumps(inputs, indent=2, default=str))
    parts.append("```")
    parts.append("")

    parts.append("## /workspace/review/principles.md")
    parts.append("")
    parts.append(principles_md or "_(empty — operator has not declared a review framework)_")
    parts.append("")

    if operator_profile_md:
        parts.append("## Operator profile")
        parts.append("")
        parts.append(operator_profile_md)
        parts.append("")

    if risk_md:
        parts.append("## _risk.md")
        parts.append("")
        parts.append(risk_md)
        parts.append("")

    if performance_md:
        parts.append("## _performance.md (domain track record)")
        parts.append("")
        parts.append(performance_md)
        parts.append("")
    else:
        parts.append("## _performance.md")
        parts.append("")
        parts.append(
            "_(no accumulated track record for this domain yet — treat "
            "this as an early-cycle proposal where calibration data is thin)_"
        )
        parts.append("")

    parts.append(
        "## Instruction\n\n"
        "Call `return_review_decision` exactly once with your decision, "
        "concrete reasoning referencing the substrate above, and "
        "confidence level."
    )

    return "\n".join(parts)
