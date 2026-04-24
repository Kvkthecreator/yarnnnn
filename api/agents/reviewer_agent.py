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
`ALL_ROLES` entry. See docs/architecture/THESIS.md §"Vocabulary"
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
#: Identifies the CURRENT OCCUPANT CLASS (AI, Sonnet-backed, version 2) —
#: not the seat itself. The seat is identified structurally by the filesystem
#: home `/workspace/review/`. Bumped when prompt/model changes materially.
#:
#: v1 → v2 (2026-04-24, ADR-216 Commit 2): persona-aware reasoning.
#: IDENTITY.md now read at reasoning time and injected into the user message
#: as the opening persona section, so operator-authored persona content
#: (e.g. Simons-character for a trading Reviewer) actually flows into the
#: model's reasoning. Previously IDENTITY.md was scaffolded but ignored.
#:
#: v2 → v3 (2026-04-24, ADR-217 Commit 2): autonomy-narrowing rule.
#: System prompt explicitly declares the "principles can narrow the raw
#: delegation but never widen it" invariant. Before v3, the prompt was
#: silent on how the persona should resolve conflicts between its own
#: principles and the workspace's delegation; alpha-trader E2E showed
#: the Sonnet model already resolved this correctly in practice, but
#: v3 makes the rule explicit so future personas don't drift.
#:
#: v3 → v4 (2026-04-24, persona-reflection.md v1.1 alignment).
#: PRECEDENT.md (operator-authored durable interpretations, committed
#: fd4917a) is now read at reasoning time and injected into the user
#: message alongside principles.md. System prompt declares that
#: precedent + principles together form the narrowing layer the persona
#: applies on top of AUTONOMY.md. Precedent takes precedence over
#: persona principles when the two disagree — the operator's explicit
#: interpretation always wins over the persona's framework default.
#:
#: v4 → v5 (2026-04-24, ADR-218 Commit 3). Adds reflection-mode
#: invocation — a second call path distinct from verdict-mode. In
#: reflection mode the persona reads its own IDENTITY + principles +
#: PRECEDENT + MANDATE + AUTONOMY + recent decisions + per-domain
#: performance summary, and returns a structured verdict about whether
#: its framework warrants change (no_change | narrow | relax |
#: character_note). Same tool-call pattern as verdict mode; same
#: REVIEWER_MODEL_IDENTITY string — the persona IS the same, just
#: thinking about itself vs thinking about a proposal. Cost-conscious:
#: reflection mode uses Haiku (REFLECTION_MODEL) while verdict mode
#: stays on Sonnet (_MODEL_SLUG). Same as the ManageTask evaluate /
#: task-pipeline split pattern — expensive judgment gets the big
#: model; assessment of accumulated state gets the cheap one.
REVIEWER_MODEL_IDENTITY = "ai:reviewer-sonnet-v5"

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
1. IDENTITY.md      — your declared persona. This is the judgment character
                      you embody. It may be a named figure (e.g. Simons,
                      Buffett, Deming), an operator-authored original, or
                      the generic default "independent judgment seat."
                      Your reasoning voice, priorities, and defer/approve
                      thresholds should reflect this persona. If the file
                      is generic default, reason as a neutral skeptical
                      judgment seat.
2. principles.md    — the operator's declared review framework (the checks
                      your persona applies to proposals)
3. PRECEDENT.md     — operator-authored durable interpretations /
                      boundary-case resolutions. Read this alongside
                      principles.md; it captures the operator's explicit
                      decisions about recurring ambiguities. When
                      PRECEDENT.md and your persona principles disagree,
                      precedent wins — the operator's declared
                      interpretation always overrides your framework
                      default. Precedent is how the operator teaches the
                      workspace, one interpretation at a time.
4. _risk.md (if trading domain) — hard floors, non-negotiable
5. _operator_profile.md — declared strategy + style (if present)
6. _performance.md  — accumulated track record of similar actions
                      (rolling 7d / 30d / 90d windows)
7. The proposal itself — action_type, inputs, rationale, reversibility,
                         expected_effect

The persona (IDENTITY.md) is *who* is reviewing. The framework
(principles.md + PRECEDENT.md) is *what* you check. The substrate (risk,
performance, operator profile) is the data you reason against. Same
framework, same data, different persona → legitimately different
reasoning and different defer/approve boundaries. That is the point.

**Autonomy delegation (ADR-217).** The workspace's autonomy posture is
declared separately in `/workspace/context/_shared/AUTONOMY.md` — the
operator's standing intent about how much judgment authority you carry
on their behalf. You do NOT read AUTONOMY.md directly for the eligibility
gate (the dispatcher already did that before invoking you). You render a
verdict as your persona would; the dispatcher decides whether your
verdict auto-executes or routes to the Queue based on AUTONOMY.md. What
this means for your reasoning: your framework (principles + precedent)
can *narrow* delegation (add defer conditions) but never *widen* it. If
your framework and the raw delegation conflict on auto-approve
eligibility, apply the stricter. The servant can be more conservative
than the master permits, never more permissive.

**Precedent hierarchy.** When PRECEDENT.md contains a rule that applies
to the current proposal, it overrides any conflicting clause in your
principles.md. If principles say "approve below $X" but PRECEDENT says
"never auto-approve during earnings week," the precedent wins. Cite
precedent explicitly in your reasoning when it drove the verdict so the
operator can audit whether their interpretation was applied correctly.

Your decision categories:
- **approve** — EV is clearly positive AND within declared edge. The
  dispatcher will check your approve against AUTONOMY.md's ceiling;
  you do not need to know the ceiling — reason on merits.
- **reject** — EV is clearly negative OR violates _risk.md OR is
  outside the operator's declared strategy.
- **defer** — EV is ambiguous, stakes are high enough to warrant
  human judgment, or this is an edge case not yet represented in
  _performance.md. Also defer when a principle narrows past the
  threshold the raw autonomy grant would permit.

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
    identity_md: str,
    principles_md: str,
    precedent_md: str,
    performance_md: str | None,
    risk_md: str | None,
    operator_profile_md: str | None,
) -> ReviewDecision | None:
    """Run the AI Reviewer against a pending proposal. Returns a
    structured decision, or None on failure (seat then defers to
    human — never auto-approves a failed review).

    ADR-216 Commit 2: `identity_md` is the Reviewer's operator-authored
    persona content (`/workspace/review/IDENTITY.md`). Required
    parameter — callers must read and pass it.

    persona-reflection.md v1.1 alignment (v4 prompt): `precedent_md` is
    the operator-authored durable-interpretation content
    (`/workspace/context/_shared/PRECEDENT.md`). Required parameter —
    callers read and pass it. Empty string is acceptable (fresh
    workspace; operator hasn't authored any precedent yet); the model
    treats empty as "no precedent to apply, reason from persona
    principles alone."

    Token usage is always recorded via `record_token_usage`; the
    cost is borne by the workspace owner even for defer decisions.

    Never raises.
    """
    try:
        user_message = _build_user_message(
            proposal_row=proposal_row,
            identity_md=identity_md,
            principles_md=principles_md,
            precedent_md=precedent_md,
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
    identity_md: str,
    principles_md: str,
    precedent_md: str,
    performance_md: str | None,
    risk_md: str | None,
    operator_profile_md: str | None,
) -> str:
    """Assemble the user-message envelope the model reads against.

    Order is load-bearing: persona (IDENTITY.md) opens the envelope so
    the model knows who it's reasoning as before it sees the framework
    (principles.md + PRECEDENT.md) or the substrate
    (risk/performance/operator_profile). Same framework + same
    substrate, different persona → legitimately different reasoning;
    that divergence is the persona's point.

    PRECEDENT.md lands between principles.md and substrate so the
    operator's explicit interpretations are the last thing the model
    reads before the substrate data — precedent acts as a filter on
    substrate reasoning, matching how operators actually use precedent
    ("when X condition holds in the substrate, apply interpretation Y").
    """
    parts: list[str] = []

    # Persona section — ADR-216 Commit 2. First thing the model reads.
    parts.append("## /workspace/review/IDENTITY.md — Your persona")
    parts.append("")
    parts.append(identity_md or "_(empty — reason as a neutral skeptical judgment seat)_")
    parts.append("")

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

    # PRECEDENT section — operator-authored durable interpretations.
    # Overrides conflicting clauses in principles.md (see system prompt
    # §Precedent hierarchy). Empty is expected on fresh workspaces.
    parts.append("## /workspace/context/_shared/PRECEDENT.md — Operator-declared durable interpretations")
    parts.append("")
    parts.append(
        precedent_md
        or "_(empty — operator has not authored any precedent yet; reason from persona principles alone)_"
    )
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


# ============================================================================
# Reflection mode (ADR-218 Commit 3)
# ============================================================================
# Distinct invocation from verdict mode. The persona reads its own track
# record + accumulated substrate and produces a structured verdict about
# whether its framework warrants change. Same tool-call pattern as
# verdict mode (forced tool call returning structured output). Different
# model tier — Haiku for reflection, matching ManageTask(evaluate) cost
# posture. Verdict mode stays on Sonnet.
#
# Called by services/back_office/reviewer_reflection.py when the
# invocation gate passes (≥1 new decision since last reflection AND
# ≥24h elapsed). This function does NOT write any files — Commit 4's
# reflection_writer handles write-back. This function returns the
# structured proposals; the caller decides what to do with them.


#: Cost-conscious model for reflection — matches EVALUATE_MODEL in
#: ManageTask._handle_evaluate. Verdict mode stays on _MODEL_SLUG
#: (Sonnet) because verdict reasoning is time-sensitive + higher-stakes.
REFLECTION_MODEL_SLUG = "claude-haiku-4-5-20251001"

#: Caller string for token_usage records (distinct from verdict-mode
#: _TOKEN_CALLER so reflection spend shows up separately in the ledger).
_REFLECTION_TOKEN_CALLER = "reviewer-reflection"


class ReflectionProposal(TypedDict):
    """A single proposed change to the Reviewer's substrate."""
    #: Which kind of change — shapes how reflection_writer applies it.
    change_type: Literal["narrow", "relax", "character_note", "no_change"]
    #: Which file to edit. Commit 4's writer enforces the scope ceiling
    #: (only IDENTITY.md or principles.md allowed; anything else rejected).
    target_file: Literal["principles.md", "IDENTITY.md", ""]
    #: Concise description of what to change and why. Written into the
    #: revision message + reflections.md entry.
    reasoning: str
    #: Specific substrate citations — decision counts, outcome deltas,
    #: pattern observations. Evidence-citation invariant per
    #: persona-reflection.md §4 + ADR-218 D7.
    evidence: str
    #: Full proposed new content for target_file. For narrow/relax this
    #: is the revised principles.md; for character_note it's the
    #: revised IDENTITY.md; for no_change this is empty and writer
    #: skips the write.
    new_content: str


class ReflectionVerdict(TypedDict):
    """Structured output of a reflection-mode invocation.

    Returned by run_reflection() on successful model call. A verdict
    with `overall="no_change"` is the common outcome — reflection that
    concludes "nothing to adjust" is valuable data (it means the
    framework is working) and should be common, not rare.
    """
    #: Top-level verdict — controls whether writer applies any changes.
    overall: Literal["no_change", "narrow", "relax", "character_note"]
    #: The persona's own one-paragraph reasoning about what it noticed
    #: (or didn't notice) in its track record. This is the meta-commentary
    #: appended to reflections.md verbatim regardless of overall verdict.
    reasoning: str
    #: Evidence summary the persona cites — decisions reviewed, outcomes
    #: observed, notable patterns. Appended to reflections.md verbatim.
    evidence_summary: str
    #: List of concrete proposed changes. Empty for no_change. Writer
    #: applies each in order after scope-ceiling + mandate-preservation
    #: sanity checks.
    proposals: list[ReflectionProposal]


_REFLECTION_TOOL = {
    "name": "return_reflection_verdict",
    "description": (
        "Return your reflection verdict — whether your framework warrants "
        "change based on your own track record. Call this tool exactly "
        "once. Returning overall='no_change' with an empty proposals list "
        "is a valid and common outcome."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "overall": {
                "type": "string",
                "enum": ["no_change", "narrow", "relax", "character_note"],
                "description": (
                    "Top-level verdict. 'no_change' — framework is working, "
                    "no adjustment warranted; common and expected. "
                    "'narrow' — add a defer condition or tighten a rule. "
                    "'relax' — remove an overly-conservative rule; evidence "
                    "bar is higher than narrow. 'character_note' — propose "
                    "an IDENTITY.md edit; rare, only when decisions reveal "
                    "a persona trait not in the declared character."
                ),
            },
            "reasoning": {
                "type": "string",
                "description": (
                    "One paragraph in your persona's voice describing what "
                    "you noticed (or didn't notice) in your track record. "
                    "Appended to reflections.md verbatim. Write for the "
                    "operator's retrospective audit."
                ),
            },
            "evidence_summary": {
                "type": "string",
                "description": (
                    "Concrete substrate citations — how many decisions "
                    "reviewed, what outcome patterns observed, specific "
                    "examples. Appended to reflections.md verbatim."
                ),
            },
            "proposals": {
                "type": "array",
                "description": (
                    "Concrete proposed changes. Empty for no_change. Each "
                    "proposal carries the full revised file content — the "
                    "writer does NOT construct diffs from partial edits."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "change_type": {
                            "type": "string",
                            "enum": ["narrow", "relax", "character_note", "no_change"],
                        },
                        "target_file": {
                            "type": "string",
                            "enum": ["principles.md", "IDENTITY.md", ""],
                            "description": (
                                "Scope ceiling: only principles.md or IDENTITY.md. "
                                "Empty string for no-op proposals (rare; typically "
                                "the outer verdict captures no_change)."
                            ),
                        },
                        "reasoning": {"type": "string"},
                        "evidence": {"type": "string"},
                        "new_content": {
                            "type": "string",
                            "description": (
                                "Full new content for target_file. The writer "
                                "replaces the file wholesale (via ADR-209 "
                                "write_revision). If you want to keep most of "
                                "the file, echo it back with your changes."
                            ),
                        },
                    },
                    "required": ["change_type", "target_file", "reasoning", "evidence", "new_content"],
                },
            },
        },
        "required": ["overall", "reasoning", "evidence_summary", "proposals"],
    },
}


_REFLECTION_SYSTEM_PROMPT = """\
You are the independent judgment seat for this operator's workspace,
reflecting on your own track record.

This is a different invocation mode from verdict mode. You are not
judging a proposal right now; you are judging **your own framework**.
Your question is: given the decisions I've rendered and the outcomes
they produced, does my framework warrant change?

**The common outcome is `no_change`.** Frameworks that change on every
cycle aren't learning — they're reacting. You should only propose
adjustments when substrate evidence clearly warrants them. A workspace
where you reflect weekly and return `no_change` 80% of the time is a
well-calibrated workspace, not a broken one.

Substrate available to you (passed in the user message):

1. Your IDENTITY.md — who you are. Your character shapes how you reason
   about your own track record. The voice you use in your reflection
   reasoning should match this persona.
2. Your current principles.md — the framework you've been applying.
   This is what you're potentially revising.
3. PRECEDENT.md — operator-authored durable interpretations. You must
   respect these in any proposed change. Precedent always wins over
   your framework; you cannot propose changes that contradict precedent.
4. MANDATE.md — the operator's declared Primary Action. You cannot
   propose changes that contradict the mandate. If you notice the
   mandate seems ambiguous or inconsistent with observed outcomes, say
   so in your reasoning — the operator will decide whether to revise
   the mandate; you do not.
5. AUTONOMY.md — the operator's delegation ceiling. You cannot propose
   changes that would widen this ceiling. Your framework can narrow
   delegation (add defer conditions) but never widen it.
6. Recent decisions.md — your verdict trail since last reflection.
   Look for patterns: are you deferring to human judgment more than
   the substrate warrants? Approving in contexts where later outcomes
   reveal the approval was premature? Rejecting on grounds that have
   been consistently overturned by operator override?
7. Per-domain _performance.md — realized outcomes. Did your approvals
   generate expected value? Did your defers turn out to be over-
   cautious or well-placed?

**Scope ceiling (enforced structurally).** You can propose changes
to:
  - `principles.md` — your declared framework
  - `IDENTITY.md` — your persona character (rare; high bar)

You CANNOT propose changes to: MANDATE.md, AUTONOMY.md, PRECEDENT.md,
any file under `/workspace/context/{domain}/`, any file outside
`/workspace/review/`. The writer will reject any proposal targeting
files outside the scope ceiling.

**Evidence requirement.** Every proposal must cite specific substrate
evidence — decision counts, outcome deltas, pattern observations.
Proposals without evidence should be declared `no_change` instead.

**Change-type discipline.**
- `narrow` — adding a defer condition or tightening a rule. Evidence
  bar: observe at least 3 decisions where the narrowing would have
  improved outcomes.
- `relax` — removing an overly-conservative rule. Evidence bar is
  higher — observe at least 5 decisions where the conservative rule
  deferred things that later turned out fine. Servants should err
  toward conservative; relaxing requires clearer evidence.
- `character_note` — IDENTITY.md edit. Rarest. Only when decisions
  reveal a persona trait not in the declared character or a
  contradiction between declared character and actual behavior.
- `no_change` — framework is working. Return this whenever evidence
  is ambiguous or the patterns you observe don't clearly warrant
  change. Include reasoning about what you looked at and why it
  didn't warrant change — that reasoning itself is valuable data.

**Full-content replacement.** For each proposal, return the FULL new
content of `target_file`. The writer replaces the file wholesale (via
ADR-209 revision chain). If you want to keep most of the file, echo
it back with your specific changes. This is deliberate — structured
diff-over-tool-call is error-prone and review is cleaner with full
content in the revision message.

Call `return_reflection_verdict` exactly once with your overall
verdict, one-paragraph reasoning in your persona's voice, evidence
summary, and (if applicable) the list of concrete proposals.
"""


async def run_reflection(
    client: Any,
    user_id: str,
    *,
    identity_md: str,
    principles_md: str,
    precedent_md: str,
    mandate_md: str,
    autonomy_md: str,
    recent_decisions_md: str,
    performance_summary: str,
) -> ReflectionVerdict | None:
    """Invoke the Reviewer in reflection mode.

    Called by `services.back_office.reviewer_reflection.run()` after the
    invocation gate passes. Returns the structured verdict, or None on
    failure (caller treats as "no change, reflection unavailable" —
    never fabricates proposals on model failure).

    ADR-218 Commit 3. Same tool-call pattern as `review_proposal()` but
    distinct system prompt, distinct tool schema, cheaper model
    (Haiku). REVIEWER_MODEL_IDENTITY stays unchanged — the persona IS
    the same persona, just thinking about itself vs thinking about a
    proposal.

    Token usage recorded under caller="reviewer-reflection" so the
    ledger separates reflection spend from verdict spend.

    Never raises.
    """
    try:
        user_message = _build_reflection_user_message(
            identity_md=identity_md,
            principles_md=principles_md,
            precedent_md=precedent_md,
            mandate_md=mandate_md,
            autonomy_md=autonomy_md,
            recent_decisions_md=recent_decisions_md,
            performance_summary=performance_summary,
        )

        response = await chat_completion_with_tools(
            messages=[{"role": "user", "content": user_message}],
            system=_REFLECTION_SYSTEM_PROMPT,
            tools=[_REFLECTION_TOOL],
            model=REFLECTION_MODEL_SLUG,
            max_tokens=2048,
            tool_choice={"type": "tool", "name": "return_reflection_verdict"},
        )

        tool_uses = getattr(response, "tool_uses", None) or []
        usage = getattr(response, "usage", None) or {}

        record_token_usage(
            client,
            user_id=user_id,
            caller=_REFLECTION_TOKEN_CALLER,
            model=REFLECTION_MODEL_SLUG,
            input_tokens=int(usage.get("input_tokens", 0) or 0),
            output_tokens=int(usage.get("output_tokens", 0) or 0),
            ref_id=None,
            metadata={"mode": "reflection"},
        )

        verdict_call = None
        for tu in tool_uses:
            if getattr(tu, "name", None) == "return_reflection_verdict":
                verdict_call = tu
                break

        if verdict_call is None:
            logger.warning(
                "[REVIEWER_REFLECTION] model produced no tool call for user=%s — "
                "treating as no-change",
                user_id[:8],
            )
            return None

        tool_input = getattr(verdict_call, "input", None) or {}
        overall = tool_input.get("overall")
        reasoning = (tool_input.get("reasoning") or "").strip()
        evidence_summary = (tool_input.get("evidence_summary") or "").strip()
        proposals_raw = tool_input.get("proposals") or []

        if overall not in ("no_change", "narrow", "relax", "character_note"):
            logger.warning(
                "[REVIEWER_REFLECTION] invalid overall=%r for user=%s — "
                "treating as no-change",
                overall, user_id[:8],
            )
            return None
        if not reasoning:
            logger.warning(
                "[REVIEWER_REFLECTION] empty reasoning for user=%s — "
                "treating as no-change",
                user_id[:8],
            )
            return None

        # Normalize proposals — coerce missing fields to safe defaults;
        # writer will apply scope-ceiling + mandate-preservation checks.
        proposals: list[ReflectionProposal] = []
        for p in proposals_raw:
            if not isinstance(p, dict):
                continue
            proposals.append(ReflectionProposal(
                change_type=p.get("change_type", "no_change"),
                target_file=p.get("target_file", ""),
                reasoning=(p.get("reasoning") or "").strip(),
                evidence=(p.get("evidence") or "").strip(),
                new_content=p.get("new_content") or "",
            ))

        return ReflectionVerdict(
            overall=overall,
            reasoning=reasoning,
            evidence_summary=evidence_summary,
            proposals=proposals,
        )

    except Exception as exc:  # noqa: BLE001 — never raise
        logger.warning(
            "[REVIEWER_REFLECTION] run_reflection failed for user=%s: %s",
            user_id[:8], exc,
        )
        return None


def _build_reflection_user_message(
    *,
    identity_md: str,
    principles_md: str,
    precedent_md: str,
    mandate_md: str,
    autonomy_md: str,
    recent_decisions_md: str,
    performance_summary: str,
) -> str:
    """Assemble the user message for reflection mode.

    Order matters: persona first (IDENTITY), then framework under
    consideration (principles), then the operator-declared boundaries
    (PRECEDENT, MANDATE, AUTONOMY), then the track record (decisions +
    performance). The persona reads its own character before looking
    at its own record — matching the verdict-mode pattern of
    persona-before-substrate.
    """
    parts: list[str] = []

    parts.append("## /workspace/review/IDENTITY.md — Your persona")
    parts.append("")
    parts.append(identity_md or "_(empty — reason as a neutral skeptical judgment seat)_")
    parts.append("")

    parts.append("## /workspace/review/principles.md — The framework you are considering revising")
    parts.append("")
    parts.append(principles_md or "_(empty — operator has not declared a framework yet)_")
    parts.append("")

    parts.append("## /workspace/context/_shared/PRECEDENT.md — Operator-declared durable interpretations (you cannot contradict these)")
    parts.append("")
    parts.append(precedent_md or "_(empty — operator has not authored precedent yet)_")
    parts.append("")

    parts.append("## /workspace/context/_shared/MANDATE.md — The operator's Primary Action (you cannot contradict this)")
    parts.append("")
    parts.append(mandate_md or "_(empty — no mandate declared)_")
    parts.append("")

    parts.append("## /workspace/context/_shared/AUTONOMY.md — The operator's delegation ceiling (you cannot widen this)")
    parts.append("")
    parts.append(autonomy_md or "_(empty — default manual posture)_")
    parts.append("")

    parts.append("## Recent decisions.md — Your verdict trail since last reflection")
    parts.append("")
    parts.append(recent_decisions_md or "_(no decisions yet)_")
    parts.append("")

    parts.append("## Per-domain _performance.md — Realized outcomes")
    parts.append("")
    parts.append(performance_summary or "_(no _performance.md files yet)_")
    parts.append("")

    parts.append(
        "## Instruction\n\n"
        "Reflect on whether your framework warrants change. Remember: "
        "`no_change` is the common and expected outcome. If you notice "
        "patterns that warrant adjustment, propose concrete changes "
        "with full new file content and evidence citations. "
        "Call `return_reflection_verdict` exactly once."
    )

    return "\n".join(parts)
