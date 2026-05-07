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
#:
#: v5 → v6 (2026-04-28, ADR-229 D2 + D5). Adds generative defer:
#: tool schema accepts optional `propose_followup` field on `defer`
#: verdicts so the Reviewer can request substrate-building work as
#: recursion. System prompt declares the "follow-up is recursion, not
#: bypass" invariant + the action_type allow-list. Also reflects the
#: ADR-229 D1 gate inversion in the system prompt (the AUTONOMY filter
#: now runs after this verdict, not before — Reviewer reasons on merits
#: regardless of whether AUTONOMY would auto-execute the result).
REVIEWER_MODEL_IDENTITY = "ai:reviewer-sonnet-v6"

#: Model slug passed to Anthropic. Keep parallel to REVIEWER_MODEL_IDENTITY.
_MODEL_SLUG = "claude-sonnet-4-6"

#: Caller string for token_usage records.
_TOKEN_CALLER = "reviewer"


class ReviewDecision(TypedDict, total=False):
    """Structured output of the AI Reviewer.

    `decision`, `reasoning`, `confidence` are always present.
    `directives` (ADR-253 D2) replaces the deleted `propose_followup`
    (ADR-229 D2). Directives are System Agent instructions that execute
    immediately when the Reviewer defers for evidence gap — no action_proposals
    row, no second Reviewer pass.
    """
    decision: Literal["approve", "reject", "defer"]
    reasoning: str
    #: Present when the model supplies it; may be empty for defer.
    confidence: str  # "low" | "medium" | "high"
    #: ADR-253 D2: System Agent directives on defer verdicts (replaces propose_followup).
    #: List of dicts: {action: "fire_invocation"|"write_file"|"clarify", ...args}
    directives: list


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
            "directives": {
                "type": "array",
                "description": (
                    "ADR-253 D2: System Agent directives — replaces propose_followup. "
                    "ONLY valid on decision='defer' when deferring for evidence gap. "
                    "Each directive executes immediately via the System Agent — no "
                    "action_proposals row, no second Reviewer pass. "
                    "Allowed actions: fire_invocation (fire an existing recurrence), "
                    "write_file (write to /workspace/review/ only), "
                    "clarify (surface a question to the operator in the narrative). "
                    "Do NOT use for external platform writes (those are proposals). "
                    "Do NOT use for infrastructure changes. "
                    "Do NOT issue a directive to yourself."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["fire_invocation", "write_file", "clarify"],
                        },
                        "slug": {
                            "type": "string",
                            "description": "fire_invocation: recurrence slug to fire (must already exist)",
                        },
                        "path": {
                            "type": "string",
                            "description": "write_file: path within /workspace/review/",
                        },
                        "content": {
                            "type": "string",
                            "description": "write_file: file content to write",
                        },
                        "message": {
                            "type": "string",
                            "description": "clarify: question to surface to the operator",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Why this directive is needed — cited evidence gap",
                        },
                    },
                    "required": ["action", "reason"],
                },
            },
        },
        "required": ["decision", "reasoning", "confidence"],
    },
}


_SYSTEM_PROMPT = """\
You are the operator's judgment character — personified via IDENTITY.md.
You are not a system, not a filter, not a policy engine. You are a person:
the specific judgment character the operator installed to act on their behalf.
Your IDENTITY.md tells you who that is. Embody it fully.

You have been given a proposal to evaluate. You reason from your character's
perspective — their framework, their experience, their standards — and render
a verdict. You speak in first person as that character.

Context you have (passed in the user message):
1. IDENTITY.md      — who you are. Read it first. This is the character you
                      embody: Simons, Buffett, Deming, or the operator's own
                      original. Your voice, your priorities, your thresholds
                      come from here. If it's a generic default, reason as a
                      skeptical, independent-minded judge.
2. principles.md    — the framework you apply. Your declared standards.
3. PRECEDENT.md     — the operator's rulings on past edge cases. When your
                      principles and precedent conflict, precedent wins — the
                      operator's explicit interpretation is law.
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

**Autonomy delegation (ADR-217 + ADR-229 D1).** The workspace's autonomy
posture is declared separately in `/workspace/context/_shared/AUTONOMY.md`
— the operator's standing intent about how much judgment authority you
carry on their behalf. **You run BEFORE the autonomy filter, not after**
(ADR-229 inverted the dispatch order): you render a verdict on merits
regardless of whether AUTONOMY would auto-execute the result. The
dispatcher decides post-verdict whether your `approve` binds (auto-
execute) or surfaces as advisory (operator clicks). What this means for
your reasoning:

- Reason on the **merits of the action**, not on whether it falls within
  AUTONOMY's ceiling. AUTONOMY filters your verdict downstream; your job
  is to be the operator's judgment proxy.
- Your framework (principles + precedent) can *narrow* delegation (add
  defer conditions) but never *widen* it. If your framework and the raw
  delegation conflict, apply the stricter.
- The servant can be more conservative than the master permits, never
  more permissive.

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

**Directives on defer (ADR-253 D2).** When you defer because evidence is
insufficient — sparse `_performance.md`, ambiguous signal, missing context —
you may include `directives`: a list of instructions for the System Agent
to execute immediately. Use this when the deferral is *evidence-gap-shaped*,
not when it is *risk-shaped*. The System Agent executes directives without
another Reviewer pass — you are commissioning substrate work, not proposing.

- *Evidence-gap defer with directive:* "I cannot evaluate IH-2 expectancy;
  `_performance.md` has zero entries."
  → `directives: [{action: "fire_invocation", slug: "track-universe",
     reason: "Need fresh indicator data to evaluate RSI threshold"}]`
- *Operator clarification needed:* "Signal spec is ambiguous — IH-3 entry
  says 'prior-day low' but RSI threshold is not declared."
  → `directives: [{action: "clarify", message: "IH-3 needs RSI threshold
     declared. What value?", reason: "Cannot evaluate without declared threshold"}]`
- *Risk-shaped defer (no directive):* "Position size exceeds `_risk.md`
  VAR budget." — no directive; the proposer must resize.

Constraints:
- Only valid on `decision="defer"`. NEVER on approve or reject.
- Allowed actions: fire_invocation (fire an existing recurrence slug),
  write_file (write to /workspace/review/ only), clarify (question to operator).
- You cannot issue directives for external platform writes (those are proposals).
- You cannot issue a directive to yourself. No `task.create` proposals.
- Directives are recursion (gather substrate), not bypass. You cannot widen
  autonomy through directives.

Reason explicitly:
- What's the upside if this action works out?
- What's the downside if it doesn't?
- Is the upside/downside ratio asymmetric?
- Given the operator's track record on similar actions, is this
  inside their edge or outside it?
- Does _risk.md explicitly prohibit this? (If so, reject.)

Call `return_review_decision` exactly once with your decision,
reasoning (2–5 sentences), and confidence.

**Voice discipline — this is critical**:

Write in your persona's natural voice. You are the operator's judgment
character — Simons, Buffett, or whoever was installed. Speak as that person
thinking through whether this trade makes sense.

Never cite filenames. The operator doesn't think in "_risk.md" or
"principles.md" — they think in the rules they declared. Say "you told me
no same-day closes" not "_risk.md says max_day_trades: 0". Say "your declared
signals are IH-1 through IH-5" not "per _signals.md".

When you identify a fixable problem, name the fix clearly. If two declared
rules conflict and one of them should change, say what the change is:
"The fix is straightforward: allow same-day closes for paper trading.
Say the word and YARNNN will update it." You are an active participant,
not just a verdict machine — but YARNNN holds the write primitives.
You surface the judgment and the resolution path; the operator authorizes;
YARNNN executes. Exception: you may write directly to AUTONOMY.md when
pausing autonomous execution (ADR-248 D4) — that is the only file you
author directly.

Two-sentence structure: verdict in the first sentence, reasoning in the second.
The operator needs to know immediately whether to act, then why.
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

        # ADR-253 D2: extract optional directives (replaces deleted propose_followup).
        # Only honored on defer verdicts — System Agent executes them immediately.
        result: ReviewDecision = {
            "decision": decision,
            "reasoning": reasoning,
            "confidence": confidence,
        }
        directives = tool_input.get("directives")
        if isinstance(directives, list) and decision == "defer" and directives:
            result["directives"] = directives
        return result
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


class ReflectionProposal(TypedDict, total=False):
    """A single proposed change to the Reviewer's substrate."""
    #: Which kind of change — shapes how reflection_writer applies it.
    #: ADR-252 D6: generate_proposal added — Reviewer proposes an action
    #: (trading, commerce, etc.) from reflection. Uses action_type + proposal_inputs
    #: instead of target_file + new_content. AUTONOMY gate applies downstream.
    change_type: Literal["narrow", "relax", "character_note", "no_change", "pause_autonomy", "generate_proposal"]
    #: Which file to edit. Scope ceiling enforced by reflection_writer.
    #: pause_autonomy proposals use "AUTONOMY.md" and leave new_content empty.
    #: generate_proposal proposals leave target_file empty.
    target_file: Literal["principles.md", "IDENTITY.md", "AUTONOMY.md", ""]
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
    #: skips the write. Empty for generate_proposal.
    new_content: str
    #: ADR-252 D6: generate_proposal only — action_type for ProposeAction.
    #: Example: "trading.submit_order_paper". Leave empty for other change_types.
    action_type: str
    #: ADR-252 D6: generate_proposal only — inputs dict for ProposeAction.
    #: Serialized as JSON string to fit TypedDict. Leave empty for other types.
    proposal_inputs: str


class ReflectionVerdict(TypedDict):
    """Structured output of a reflection-mode invocation.

    Returned by run_reflection() on successful model call. A verdict
    with `overall="no_change"` is the common outcome — reflection that
    concludes "nothing to adjust" is valuable data (it means the
    framework is working) and should be common, not rare.
    """
    #: Top-level verdict — controls whether writer applies any changes.
    overall: Literal["no_change", "narrow", "relax", "character_note", "pause_autonomy", "generate_proposal"]
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
                "enum": ["no_change", "narrow", "relax", "character_note", "pause_autonomy"],
                "description": (
                    "Top-level verdict. 'no_change' — framework is working, "
                    "no adjustment warranted; common and expected. "
                    "'narrow' — add a defer condition or tighten a rule. "
                    "'relax' — remove an overly-conservative rule; evidence "
                    "bar is higher than narrow. 'character_note' — propose "
                    "an IDENTITY.md edit; rare, only when decisions reveal "
                    "a persona trait not in the declared character. "
                    "'pause_autonomy' — write a timed pause to AUTONOMY.md "
                    "(ADR-248 D3); highest bar — only when cumulative outcomes "
                    "show consistent capital loss or drift severe enough that "
                    "continued autonomous execution is unsafe. "
                    "'generate_proposal' — ADR-252 D6: Reviewer generates an "
                    "action proposal from reflection (trading/commerce action); "
                    "only when autonomy=autonomous AND evidence clearly supports "
                    "the action; uses action_type + proposal_inputs fields."
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
                            "enum": ["narrow", "relax", "character_note", "no_change", "pause_autonomy", "generate_proposal"],
                        },
                        "target_file": {
                            "type": "string",
                            "enum": ["principles.md", "IDENTITY.md", "AUTONOMY.md", ""],
                            "description": (
                                "Scope ceiling: principles.md or IDENTITY.md for "
                                "framework/persona changes. AUTONOMY.md only for "
                                "pause_autonomy proposals (writes paused_until + "
                                "pause_reason). Empty string for generate_proposal "
                                "and no-op proposals."
                            ),
                        },
                        "reasoning": {"type": "string"},
                        "evidence": {"type": "string"},
                        "new_content": {
                            "type": "string",
                            "description": (
                                "Full new content for target_file. For "
                                "pause_autonomy and generate_proposal, leave empty."
                            ),
                        },
                        "duration_hours": {
                            "type": "integer",
                            "description": (
                                "pause_autonomy only. How long to pause autonomous "
                                "execution (hours). Default 48. Range 24–168."
                            ),
                        },
                        "reason": {
                            "type": "string",
                            "description": (
                                "pause_autonomy only. Short human-readable reason "
                                "surfaced to the operator in the narrative and the "
                                "AUTONOMY.md pause_reason field. Max 200 chars."
                            ),
                        },
                        "action_type": {
                            "type": "string",
                            "description": (
                                "generate_proposal only (ADR-252 D6). The action to "
                                "propose — e.g. 'trading.submit_order_paper'. Must "
                                "be in ACTION_DISPATCH_MAP. Leave empty for other "
                                "change_types."
                            ),
                        },
                        "proposal_inputs": {
                            "type": "string",
                            "description": (
                                "generate_proposal only. JSON-encoded inputs dict for "
                                "the ProposeAction call. Include ticker, quantity, "
                                "order_type, rationale. Leave empty for other change_types."
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
  - `AUTONOMY.md` — ONLY via pause_autonomy proposal type (see below)

You CANNOT propose changes to: MANDATE.md, PRECEDENT.md, any file
under `/workspace/context/{domain}/`, any file outside `/workspace/review/`
(except the AUTONOMY.md pause via the pause_autonomy mechanism below).
The writer will reject any proposal targeting files outside this ceiling.

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
- `pause_autonomy` — ADR-248 D3. Highest bar. Use ONLY when cumulative
  outcomes show consistent capital loss, win rate has fallen below a
  defensible threshold across multiple cycles, or position/exposure
  has drifted beyond declared risk limits in a way that cannot be
  corrected by narrowing principles alone. Do NOT pause autonomy for:
  a single losing trade, a temporary drawdown within declared limits,
  or uncertainty about future outcomes. Pause is a circuit-breaker
  for observable structural problems, not a precaution. When proposing
  pause_autonomy: set target_file="AUTONOMY.md", leave new_content="",
  set duration_hours (24–168, default 48), set reason to a single
  concrete sentence the operator will read in the narrative.

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

        _VALID_OVERALL = {
            "no_change", "narrow", "relax", "character_note",
            "pause_autonomy", "generate_proposal",  # ADR-248 + ADR-252
        }
        if overall not in _VALID_OVERALL:
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
                # ADR-252 D6: generate_proposal fields
                action_type=p.get("action_type") or "",
                proposal_inputs=p.get("proposal_inputs") or "",
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


# ============================================================================
# Addressed mode — ADR-252 D2
# ============================================================================
# Third invocation mode alongside verdict (reactive) and reflection (periodic).
# Triggered when the intent classifier routes a user message to 'judgment'.
# The Reviewer reads the operator's question + full substrate and responds
# in persona directly to the operator. No approve/reject/defer — this is
# the Reviewer speaking conversationally, not gating a proposal.
#
# Called by api/routes/chat.py when Reviewer keyword trigger matches (ADR-252 simplified)..
# Output surfaces as role='reviewer' narrative entry via write_reviewer_message().

_ADDRESSED_TOKEN_CALLER = "reviewer-addressed"

_ADDRESSED_SYSTEM_PROMPT = """\
You are the operator's judgment character — the persona they installed to
think and reason on their behalf. Your IDENTITY.md tells you who that is.

The operator has addressed you directly with a question or request for
your perspective. This is not a proposal to gate; it is a direct
conversation. You speak in first person as your declared character.

You have access to:
1. IDENTITY.md      — who you are. Read it first. Embody the character fully.
2. principles.md    — your declared judgment framework.
3. PRECEDENT.md     — the operator's rulings on past edge cases.
4. MANDATE.md       — the operation's declared primary intent.
5. _operator_profile.md + _risk.md — declared strategy + hard floors.
6. _performance.md  — accumulated track record (rolling windows).
7. Recent conversation — what was just discussed this session.
8. The operator's question — what they're asking you directly.

**Voice discipline:**
Speak as the character in IDENTITY.md. First person, direct, your natural
register. Never cite filenames — say "you told me" not "_risk.md says".
Two to four sentences is usually right. Long enough to be substantive;
short enough to be a voice in a conversation, not a report.

**What this mode is NOT:**
- Not a proposal gate (approve/reject/defer is for reactive mode)
- Not a planning session ("here's what we should do next")
- Not a system status report

**What this mode IS:**
The operator's judgment character speaking directly on the operator's question.
If the question implies an action the operator should take, say so plainly.
If you need the System Agent to execute something based on your assessment,
include a brief "Action:" line at the end naming the mechanical step.

Call `return_addressed_assessment` exactly once.\
"""

_ADDRESSED_TOOL = {
    "name": "return_addressed_assessment",
    "description": (
        "Return your direct assessment of the operator's question. "
        "Called exactly once. `response` is your persona's voice. "
        "`action_instruction` is an optional mechanical step for the "
        "System Agent to execute based on your assessment (e.g., "
        "'ProposeAction: trading.submit_order for NVDA IH-3'). Leave "
        "action_instruction empty if no mechanical action follows."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "response": {
                "type": "string",
                "description": (
                    "Your persona's direct answer to the operator's question. "
                    "First person, your natural voice. 2–4 sentences typically."
                ),
            },
            "action_instruction": {
                "type": "string",
                "description": (
                    "Optional: a mechanical action the System Agent should "
                    "dispatch after your assessment (e.g., "
                    "'FireInvocation: signal-evaluation'). Empty string if none."
                ),
            },
            "confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": (
                    "Your confidence in this assessment. 'low' when substrate "
                    "is thin, framework is ambiguous, or stakes are novel."
                ),
            },
        },
        "required": ["response", "action_instruction", "confidence"],
    },
}


class AddressedAssessment(TypedDict):
    """Structured output of an addressed-mode invocation."""
    response: str
    action_instruction: str
    confidence: Literal["high", "medium", "low"]


def _build_addressed_user_message(
    *,
    user_message: str,
    identity_md: str,
    principles_md: str,
    precedent_md: str,
    mandate_md: str,
    operator_profile_md: str | None,
    risk_md: str | None,
    performance_summary: str | None,
    conversation_window: str | None,
) -> str:
    """Assemble the user-message envelope for addressed mode."""
    parts: list[str] = []

    parts.append("## /workspace/review/IDENTITY.md — Your persona")
    parts.append("")
    parts.append(identity_md or "_(empty — reason as a neutral skeptical judgment seat)_")
    parts.append("")

    parts.append("## /workspace/review/principles.md — Your framework")
    parts.append("")
    parts.append(principles_md or "_(empty — no declared review framework)_")
    parts.append("")

    parts.append("## /workspace/context/_shared/PRECEDENT.md")
    parts.append("")
    parts.append(precedent_md or "_(empty — no precedent authored yet)_")
    parts.append("")

    parts.append("## /workspace/context/_shared/MANDATE.md")
    parts.append("")
    parts.append(mandate_md or "_(empty — no mandate declared)_")
    parts.append("")

    if operator_profile_md:
        parts.append("## _operator_profile.md — Declared strategy")
        parts.append("")
        parts.append(operator_profile_md)
        parts.append("")

    if risk_md:
        parts.append("## _risk.md — Hard floors")
        parts.append("")
        parts.append(risk_md)
        parts.append("")

    if performance_summary:
        parts.append("## _performance.md — Track record")
        parts.append("")
        parts.append(performance_summary)
        parts.append("")

    if conversation_window:
        parts.append("## Recent conversation (context)")
        parts.append("")
        parts.append(conversation_window)
        parts.append("")

    parts.append("## The operator's question")
    parts.append("")
    parts.append(user_message.strip())
    parts.append("")

    parts.append(
        "## Instruction\n\n"
        "Answer the operator's question in your persona's voice. "
        "Call `return_addressed_assessment` exactly once."
    )

    return "\n".join(parts)


async def address_turn(
    client: Any,
    user_id: str,
    *,
    user_message: str,
    conversation_window: str | None = None,
) -> AddressedAssessment | None:
    """Invoke the Reviewer in addressed mode — direct operator question.

    ADR-252 D2. Third trigger mode: addressed (alongside reactive and
    periodic). Called by chat.py when Reviewer keyword trigger matches (ADR-252 simplified)..

    Reads the Reviewer's full substrate from the workspace, builds the
    addressed-mode user message, invokes Sonnet with forced tool call,
    returns structured assessment. Returns None on any failure (caller
    treats as no assessment available; System Agent responds instead).

    Never raises. Token usage recorded under 'reviewer-addressed'.
    """
    try:
        # --- 1. Read Reviewer substrate ---
        from services.workspace_paths import (
            REVIEW_IDENTITY_PATH,
            REVIEW_PRINCIPLES_PATH,
            SHARED_PRECEDENT_PATH,
            SHARED_MANDATE_PATH,
        )

        async def _read(path: str) -> str:
            full = f"/workspace/{path}"
            try:
                res = (
                    client.table("workspace_files")
                    .select("content")
                    .eq("user_id", user_id)
                    .eq("path", full)
                    .limit(1)
                    .execute()
                )
                return (res.data or [{}])[0].get("content") or ""
            except Exception:
                return ""

        import asyncio
        identity_md, principles_md, precedent_md, mandate_md = await asyncio.gather(
            _read(REVIEW_IDENTITY_PATH),
            _read(REVIEW_PRINCIPLES_PATH),
            _read(SHARED_PRECEDENT_PATH),
            _read(SHARED_MANDATE_PATH),
        )

        # Domain-specific substrate: try trading domain first (alpha-trader)
        operator_profile_md = await _read("context/trading/_operator_profile.md") or None
        risk_md = await _read("context/trading/_risk.md") or None

        # Performance summary: cross-domain summary if available
        performance_summary = (
            await _read("context/_performance_summary.md")
            or await _read("context/trading/_performance.md")
            or None
        )

        # --- 2. Build user message ---
        user_msg = _build_addressed_user_message(
            user_message=user_message,
            identity_md=identity_md,
            principles_md=principles_md,
            precedent_md=precedent_md,
            mandate_md=mandate_md,
            operator_profile_md=operator_profile_md,
            risk_md=risk_md,
            performance_summary=performance_summary,
            conversation_window=conversation_window,
        )

        # --- 3. LLM call — Sonnet, forced tool call ---
        response = await chat_completion_with_tools(
            messages=[{"role": "user", "content": user_msg}],
            system=_ADDRESSED_SYSTEM_PROMPT,
            tools=[_ADDRESSED_TOOL],
            model=_MODEL_SLUG,
            max_tokens=1024,
            tool_choice={"type": "tool", "name": "return_addressed_assessment"},
        )

        tool_uses = getattr(response, "tool_uses", None) or []
        usage = getattr(response, "usage", None) or {}

        record_token_usage(
            client,
            user_id=user_id,
            caller=_ADDRESSED_TOKEN_CALLER,
            model=_MODEL_SLUG,
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
        )

        if not tool_uses:
            logger.warning(
                "[REVIEWER_ADDRESSED] no tool call for user=%s — falling back",
                user_id[:8],
            )
            return None

        raw = tool_uses[0].get("input") if isinstance(tool_uses[0], dict) else getattr(tool_uses[0], "input", {})
        if not raw or not isinstance(raw, dict):
            return None

        return AddressedAssessment(
            response=raw.get("response", ""),
            action_instruction=raw.get("action_instruction", ""),
            confidence=raw.get("confidence", "medium"),
        )

    except Exception as exc:
        logger.error(
            "[REVIEWER_ADDRESSED] failed for user=%s: %s",
            user_id[:8] if user_id else "?",
            exc,
        )
        return None


# ============================================================================
# Heartbeat mode — ADR-253 D5
# ============================================================================
# Fourth invocation mode alongside verdict (reactive), reflection (periodic),
# and addressed (operator message). Triggered when a recurrence matching
# AUTONOMY.md heartbeat_triggers completes.
#
# The Reviewer wakes, reads the fresh substrate output, applies principles,
# and decides: propose a trade / issue a directive / stand down.
#
# Called by invocation_dispatcher._maybe_fire_reviewer_heartbeat() after
# any recurrence dispatch. Never raises.

_HEARTBEAT_TOKEN_CALLER = "reviewer-heartbeat"

_HEARTBEAT_SYSTEM_PROMPT = """\
You are the operator's judgment character — the persona declared in IDENTITY.md.

A recurrence you declared interest in has just completed. You have been given
the fresh output so you can decide whether to act.

This is heartbeat mode. You are waking to read what the system just produced
and decide what to do. You are not reviewing a proposal someone else made.
You are exercising independent judgment at your declared cadence.

Your CLAUDE.md-equivalent (read before every invocation):
1. IDENTITY.md   — who you are. Read it first. Embody the character fully.
2. principles.md — your evaluation framework + defer posture + directive posture.
3. MANDATE.md    — what the operation is trying to achieve.
4. AUTONOMY.md   — your delegation ceiling and when you wake.

Your fresh substrate (what just changed):
5. The trigger recurrence output (signals, indicators, performance data).
6. Recent decisions.md — your own verdict history for context continuity.

**What you do here (three possible outcomes):**

1. **Propose a trade**: if signal conditions are clearly met per principles.md,
   include an `action_instruction` with the ProposeAction details. The System
   Agent will dispatch it immediately. Your reasoning becomes the proposal's
   rationale.

2. **Issue a directive**: if you need more substrate before you can evaluate
   (evidence gap), issue directives via `action_instruction`. Not a proposal —
   a System Agent instruction that executes without gating.

3. **Stand down**: if no actionable condition exists, say so in one sentence.
   "No IH-2 conditions met on today's scan. Standing by." This is a valid
   and common outcome. Brief is correct.

**Voice discipline**: speak in your persona's voice. First person. Numbers-first
if you are Simons. "What's the expectancy? What's the sample?" is the question.
Never speculate. Never trade on priors without sample. Stand down if the data
is insufficient — and say why in one sentence.

Call `return_addressed_assessment` exactly once.
"""


async def heartbeat_turn(
    client: Any,
    user_id: str,
    *,
    trigger_slug: str,
) -> AddressedAssessment | None:
    """Invoke the Reviewer in heartbeat mode — substrate-change trigger.

    ADR-253 D5. Fourth trigger mode: heartbeat (alongside reactive, periodic,
    addressed). Called by invocation_dispatcher after a recurrence matching
    AUTONOMY.md heartbeat_triggers completes.

    Reads: IDENTITY.md + principles.md + MANDATE.md + AUTONOMY.md (the
    CLAUDE.md-equivalent) + fresh substrate output (signal state files,
    performance data) + recent decisions.md.

    Returns AddressedAssessment | None on failure.
    Never raises.
    """
    try:
        from services.workspace_paths import (
            REVIEW_IDENTITY_PATH,
            REVIEW_PRINCIPLES_PATH,
            SHARED_MANDATE_PATH,
            SHARED_AUTONOMY_PATH,
            REVIEW_DECISIONS_PATH,
        )

        async def _read(path: str) -> str:
            full = f"/workspace/{path}"
            try:
                res = (
                    client.table("workspace_files")
                    .select("content")
                    .eq("user_id", user_id)
                    .eq("path", full)
                    .limit(1)
                    .execute()
                )
                return (res.data or [{}])[0].get("content") or ""
            except Exception:
                return ""

        import asyncio
        identity_md, principles_md, mandate_md, autonomy_md, decisions_md = (
            await asyncio.gather(
                _read(REVIEW_IDENTITY_PATH),
                _read(REVIEW_PRINCIPLES_PATH),
                _read(SHARED_MANDATE_PATH),
                _read(SHARED_AUTONOMY_PATH),
                _read(REVIEW_DECISIONS_PATH),
            )
        )

        # Read fresh trigger output — signal state files + performance
        signal_files = await _read_signal_files(client, user_id)
        performance_summary = (
            await _read("context/_performance_summary.md")
            or await _read("context/trading/_performance.md")
            or ""
        )

        # Compact decisions trail (last 5 entries)
        decisions_window = "\n".join(decisions_md.strip().split("\n")[-30:]) if decisions_md else ""

        # Build heartbeat context
        context_parts = [
            f"## Trigger: {trigger_slug} just completed",
            "",
            "## /workspace/review/IDENTITY.md",
            identity_md or "_(empty)_",
            "",
            "## /workspace/review/principles.md",
            principles_md or "_(empty)_",
            "",
            "## /workspace/context/_shared/MANDATE.md",
            mandate_md or "_(empty)_",
            "",
            "## /workspace/context/_shared/AUTONOMY.md",
            autonomy_md or "_(empty)_",
        ]
        if signal_files:
            context_parts += ["", "## Fresh signal state files", signal_files]
        if performance_summary:
            context_parts += ["", "## _performance.md summary", performance_summary]
        if decisions_window:
            context_parts += ["", "## Recent decisions (last entries)", decisions_window]

        context_parts += [
            "",
            "## Your task",
            "Read the fresh signal output. Apply your principles. Decide: propose a trade, "
            "issue a directive for missing substrate, or stand down with one sentence.",
        ]

        user_msg = "\n".join(context_parts)

        # LLM call — Sonnet, forced tool call (same as addressed mode)
        response = await chat_completion_with_tools(
            messages=[{"role": "user", "content": user_msg}],
            system=_HEARTBEAT_SYSTEM_PROMPT,
            tools=[_ADDRESSED_TOOL],  # reuse addressed tool schema
            model=_MODEL_SLUG,
            max_tokens=1024,
            tool_choice={"type": "tool", "name": "return_addressed_assessment"},
        )

        tool_uses = getattr(response, "tool_uses", None) or []
        usage = getattr(response, "usage", None) or {}

        record_token_usage(
            client,
            user_id=user_id,
            caller=_HEARTBEAT_TOKEN_CALLER,
            model=_MODEL_SLUG,
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
        )

        if not tool_uses:
            logger.warning(
                "[REVIEWER_HEARTBEAT] no tool call for user=%s trigger=%s",
                user_id[:8], trigger_slug,
            )
            return None

        raw = tool_uses[0].get("input") if isinstance(tool_uses[0], dict) else getattr(tool_uses[0], "input", {})
        if not raw or not isinstance(raw, dict):
            return None

        return AddressedAssessment(
            response=raw.get("response", ""),
            action_instruction=raw.get("action_instruction", ""),
            confidence=raw.get("confidence", "medium"),
        )

    except Exception as exc:
        logger.error(
            "[REVIEWER_HEARTBEAT] failed for user=%s trigger=%s: %s",
            user_id[:8] if user_id else "?", trigger_slug, exc,
        )
        return None


async def _read_signal_files(client: Any, user_id: str) -> str:
    """Read all signal state files and return compact summary."""
    try:
        result = (
            client.table("workspace_files")
            .select("path, content")
            .eq("user_id", user_id)
            .like("path", "/workspace/context/trading/signals/%.md")
            .execute()
        )
        lines = []
        for row in result.data or []:
            path = row.get("path", "")
            content = row.get("content", "")
            slug = path.split("/")[-1].replace(".md", "")
            # Extract key frontmatter fields
            import re as _re
            triggered = _re.search(r"triggered_today:\s*(\[.*?\])", content)
            state = _re.search(r"state:\s*(\S+)", content)
            lines.append(
                f"- {slug}: state={state.group(1) if state else '?'} "
                f"triggered={triggered.group(1) if triggered else '[]'}"
            )
        return "\n".join(lines) if lines else "_(no signal state files found)_"
    except Exception:
        return "_(signal files unavailable)_"
