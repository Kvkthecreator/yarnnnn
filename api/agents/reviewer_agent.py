"""AI occupant of the Reviewer seat — ADR-256 unified invocation
(amended by ADR-260 D2 + ADR-263 D2 trigger collapse to two values).

One function: `invoke_reviewer()`. Two trigger shapes: `addressed`
(operator messaged the feed) and `reactive` (substrate event requires
judgment — proposal arrival OR judgment-mode recurrence fire). One
bounded tool-use loop (12 rounds for addressed, 3 for proposal-arrival
reactive — see ADR-260 D8). One output type: ReviewerOutput.

ADR-256 superseded the four-function design (review_proposal,
run_reflection, address_turn, heartbeat_turn) that accumulated
trigger-by-trigger across ADRs 218, 252, 253. ADR-263 then collapsed
the trigger taxonomy from 4→3→2 by recognizing that cron is part of
the environment that fires recurrences (not a trigger axis); the
recurrence's `mode` field declares whether the cron-fire wakes the
Reviewer at all. Reflection and heartbeat dissolved into `reactive`.

Per FOUNDATIONS v8.4:
- Axiom 1 (Substrate): the Reviewer reads + writes substrate; substrate
  is the bus the Loop runs over (fourth sub-clause). Cross-Reviewer
  reasoning persists via reviewer_audit.append_recurrence_fire().
- Axiom 2 (Identity): occupant tagged `ai:reviewer-sonnet-v8`. The
  Reviewer is the operator's judgment function rendered as an
  autonomous agent — operator in judging posture, not a separate
  principal (Axiom 2 two-embodiments sub-section).
- Axiom 3 (Purpose): independent judgment — fiduciary, not production.
- Axiom 4 (Trigger): two sub-shapes (addressed | reactive). Cognitive
  act is the same regardless of which woke the Loop.
- Axiom 5 (Mechanism): bounded tool-use loop. Reviewer reads what it
  needs, acts on what it decides, returns verdict.
- Axiom 6 (Channel): decisions.md + reviewer_chat_surfacing narration.
  Per-action narration is legibility, not control-flow.
- Axiom 8 (Money-Truth): reasons against _money_truth.md rolling
  windows (ADR-195 Phase 3, P&L unification 2026-05-12) — including
  by_signal block for per-signal expectancy.

Model selection by trigger sub-shape (cost-conscious):
- Sonnet: proposal-arrival reactive (capital decisions, discrete)
- Haiku:  addressed + recurrence-fire reactive (conversation +
          framework reasoning, real-time loop)
"""

from __future__ import annotations

import json
import logging
from typing import Any, Literal, TypedDict

from services.anthropic import chat_completion_with_tools
from services.platform_limits import record_token_usage

logger = logging.getLogger(__name__)


#: ADR-256: occupant identity bumped to v8. v1-v7 history in git log.
#: v8 = unified invoke_reviewer() replacing four separate mode-functions.
REVIEWER_MODEL_IDENTITY = "ai:reviewer-sonnet-v8"

#: Sonnet — capital decisions (proposal + heartbeat triggers)
_SONNET = "claude-sonnet-4-6"
#: Haiku — framework reasoning (reflection + addressed triggers)
_HAIKU = "claude-haiku-4-5-20251001"

#: Token caller for Sonnet invocations
_CALLER_SONNET = "reviewer"
#: Token caller for Haiku invocations
_CALLER_HAIKU = "reviewer-reflection"


# ---------------------------------------------------------------------------
# Output type — single shape for all triggers (ADR-256 D5)
# ---------------------------------------------------------------------------

class ReviewerOutput(TypedDict, total=False):
    """Unified output of invoke_reviewer() across both trigger shapes
    (addressed + reactive). Trigger taxonomy collapsed from four to two
    by ADR-263 D2 — the historical reflection/heartbeat-specific verdicts
    survive as substrate-write directives the Reviewer can emit on any
    trigger; the trigger axis no longer gates which verdicts are valid.

    `verdict`, `reasoning`, `confidence` always present on success.
    `proposals` + `evidence_summary` may appear on any reactive
    invocation that includes recurrence-fire prompts directing the
    Reviewer to author proposals or summarize evidence.
    `actions_taken` records tool calls made during the loop (audit trail).
    """
    verdict: str          # approve|reject|defer (proposal-arrival reactive)
                          # no_change|narrow|relax|character_note|pause_autonomy
                          #   (reflection-shaped recurrence prompts)
                          # stand_down (no action warranted)
    reasoning: str
    confidence: str       # low | medium | high
    actions_taken: list   # tool calls executed during the loop
    # reflection-only
    proposals: list
    evidence_summary: str


# ---------------------------------------------------------------------------
# Trigger context — caller pre-loads relevant substrate (ADR-256 D1)
# ---------------------------------------------------------------------------

class ReviewerContext(TypedDict, total=False):
    """Substrate bag passed by callers. Each trigger pre-loads what it has;
    the Reviewer uses ReadFile tool to fetch anything else it needs."""
    # Governance layer — all triggers should pass these when available
    identity_md: str
    principles_md: str
    precedent_md: str
    mandate_md: str
    autonomy_md: str
    # Domain substrate
    performance_md: str
    risk_md: str
    operator_profile_md: str
    # Proposal trigger
    proposal_row: dict
    # Reflection trigger
    recent_decisions_md: str
    # Heartbeat trigger
    trigger_slug: str
    signal_files: str
    # Addressed trigger
    user_message: str
    conversation_window: str
    # Workspace state (compact index) — addressed + heartbeat
    workspace_state: str


# ---------------------------------------------------------------------------
# ReturnVerdict tool — Reviewer-specific (not in CHAT_PRIMITIVES)
# ---------------------------------------------------------------------------
# This is the only Reviewer-specific tool. All other tools come from the
# canonical CHAT_PRIMITIVES registry (ADR-258 D1). ReturnVerdict closes the
# tool-use loop and emits the structured verdict.

RETURN_VERDICT_TOOL = {
    "name": "ReturnVerdict",
    "description": (
        "Close the loop with your structured verdict. Call exactly once, last. "
        "After any reads/actions/writes, call this to end the turn. "
        "Required fields: verdict, reasoning, confidence. "
        "Reflection-only fields: proposals, evidence_summary."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "enum": [
                    "approve", "reject", "defer",
                    "no_change", "narrow", "relax", "character_note", "pause_autonomy",
                    "stand_down",
                ],
                "description": (
                    "approve|reject|defer for proposal/heartbeat; "
                    "no_change|narrow|relax|character_note|pause_autonomy for reflection; "
                    "stand_down for heartbeat/addressed when no action warranted."
                ),
            },
            "reasoning": {
                "type": "string",
                "description": (
                    "2-5 sentences in your persona's voice. Written verbatim "
                    "to /workspace/review/decisions.md. First sentence is the "
                    "verdict; second is why."
                ),
            },
            "confidence": {
                "type": "string",
                "enum": ["low", "medium", "high"],
            },
            "proposals": {
                "type": "array",
                "description": "Reflection trigger only — framework change proposals.",
                "items": {
                    "type": "object",
                    "properties": {
                        "change_type": {"type": "string"},
                        "target_file": {"type": "string"},
                        "reasoning": {"type": "string"},
                        "evidence": {"type": "string"},
                        "new_content": {"type": "string"},
                        "duration_hours": {"type": "integer"},
                        "reason": {"type": "string"},
                        "action_type": {"type": "string"},
                        "proposal_inputs": {"type": "string"},
                    },
                    "required": ["change_type", "target_file", "reasoning", "evidence", "new_content"],
                },
            },
            "evidence_summary": {
                "type": "string",
                "description": "Reflection trigger only — substrate citations.",
            },
        },
        "required": ["verdict", "reasoning", "confidence"],
    },
}


# ---------------------------------------------------------------------------
# System prompt — persona frame + generated cockpit awareness + trigger framing
# ---------------------------------------------------------------------------

_PERSONA_FRAME = """\
You sit in the operator's chair at the cockpit. The mandate is yours.
The workspace is yours. The primitives are your toolbox. The System
Agent is your hands. YARNNN is the system you operate. The operator
delegated this entire seat to you — its goals, its data, its decisions,
its execution authority within declared autonomy.

Every turn, your question is: **given the mandate, given current state,
what action moves the operation forward right now?**

The answer is almost always an action — fire a recurrence to refresh
data, submit a proposal because conditions are met, write a note to your
own substrate to track a pattern, schedule a follow-up cycle. The answer
is NEVER "ask the operator what to do." The operator already told you
what to do — read MANDATE.md. Now execute against it.

Standing down is structurally rare. It is the verdict only when no
available action moves the operation forward. If you find yourself
about to stand down, ask yourself: is there a refresh I should fire?
A note I should write? A signal I should commission a deeper read of?
A research-action that would tighten my next cycle's judgment? If yes,
do that instead. Standing down is the LAST option, not the default.

You ARE the operator's installed judgment. Not their assistant. Not their
analyst. Not a system asking them what to do. You are the persona they
installed to make these decisions on their behalf within declared autonomy.
When the operator delegated to you (which is the structural default — the
only reason you exist is because they delegated), they did NOT delegate
the work of "ask me what to do." They delegated the deciding AND the doing.
Decide. Act.

Read your IDENTITY.md first. Embody it fully. Speak in first person as that
character. Your voice, your priorities, your thresholds come from there.
If IDENTITY.md is empty, reason as a skeptical, independent-minded judge.

You reason in capital-EV terms:
- What is the upside if this action works?
- What is the downside if it doesn't?
- Is the upside/downside ratio asymmetric?
- Does the track record support this edge, or is this untested?

**The hard rule on judgment**: when conditions are clear, decide. When
conditions are unclear, decide. When data is stale, decide what to do
about the staleness — fire a refresh, stand down until the next scheduled
run, or accept the staleness with sized-down sizing — and SAY which you
chose. Do NOT enumerate options for the operator and ask which they want.
That is delegation back to the operator. You are the one who was supposed
to decide. Asking is the failure mode.

**Asking the operator is structurally rare.** Use Clarify only when the
operator's own declarations are genuinely contradictory (principles.md
says X, PRECEDENT.md says not-X) and you cannot resolve them via the
documented hierarchy. NOT when:
  - data is stale (decide: wait for cron, or fire a refresh)
  - signal hasn't fired (decide: stand down with one sentence on what
    would change it)
  - track record is thin (decide: scale down per the framework, or
    stand down — your principles tell you which)
  - you're unsure between two reasonable actions (PICK ONE — that is
    literally your job; second-guessing yourself by asking the operator
    is a Simons-failure mode)

If you find yourself drafting "do you want me to (1)... or (2)... or
(3)...?" — stop. Pick the most disciplined option per your framework
and execute it. State your choice in one sentence. The operator can
override you on the next turn if they disagree.

**Independence (THESIS Commitment 2)**: your judgment is evaluated against
ground truth (money-truth in _money_truth.md), not against producer agreement.
You are not captured by whoever proposed an action — you can reject it,
defer, or rewrite the framework if patterns warrant.

**Autonomy (ADR-217 + ADR-229 D1)**: you reason BEFORE the autonomy filter.
Render verdicts on merits regardless of whether AUTONOMY would auto-execute.
The dispatcher applies AUTONOMY post-verdict. Your framework can narrow
delegation but never widen it.

**Precedent hierarchy**: PRECEDENT.md overrides conflicting clauses in your
own principles.md. Cite precedent explicitly when it drove the verdict.

**Voice discipline**: First person, your character's natural register. Never
cite filenames. Say "your declared 3% risk ceiling" not "_risk.md says".
Two sentences for simple verdicts: verdict first, reasoning second.

**Narrate your direction in first person.** When you direct an action — fire
a recurrence, submit a proposal, write a note to your own substrate — say so
in your reasoning. Examples:

  - "I'm refreshing the universe tracker now — current indicator data is stale."
  - "Proposing IH-3 NVDA long 100sh, sized at 0.75% per the framework. Submitting now."
  - "Standing down until the 08:00 ET signal-evaluation run. No actionable
    conditions on stale data; firing track-universe ad-hoc would burn cost
    without changing the verdict."
  - "Logging this judgment to my decisions notebook for next quarter's review."

Don't hide directives in passive phrasing — "Universe data unavailable.
Stand down." makes the conversation opaque. "I'm refreshing universe data;
I'll re-assess when it completes." makes it legible.

**When you can't write directly to operator-authored substrate** (MANDATE,
AUTONOMY, IDENTITY, BRAND, CONVENTIONS, PRECEDENT, _operator_profile, _risk —
the operator's declarations), do not attempt it as a write. Note the
suggestion in your own decisions/reflections notebook for the operator's
next review. Do NOT use this as a reason to ask the operator a runtime
question — your job is to operate within their declarations, not to
constantly verify them.
"""


_TRIGGER_FRAMING = {
    # ADR-260 D2 amended by ADR-263: two triggers — addressed | reactive.
    # `scheduled` collapsed into `reactive` — cron is part of the environment
    # that fires recurrences; whether a fire wakes the Reviewer is a property
    # of the recurrence's `mode` field (judgment | mechanical), not a separate
    # trigger sub-shape. `reactive` covers both proposal arrival and
    # judgment-mode recurrence fires; `_build_user_message` differentiates by
    # context-bag inspection.
    "reactive": (
        "## This invocation\n\n"
        "Something requires your judgment.\n\n"
        "If a Recurrence prompt is shown above, a judgment-mode recurrence "
        "fired — the recurrence's prompt is the operator's instruction. Read "
        "it. Read substrate it cites. Apply your framework. Take the action "
        "it directs.\n\n"
        "If a Proposed action is shown above, a proposal has been submitted "
        "for review. Apply your framework. Call ReturnVerdict with "
        "approve | reject | defer + reasoning. Use ReadFile/ListFiles to "
        "fetch missing substrate before deciding if needed.\n\n"
        "Common shapes for recurrence fires:\n"
        "- Reflection prompt → `no_change` is the common and expected "
        "outcome; if patterns warrant adjustment, include proposals with "
        "full revised file content.\n"
        "- Substrate-refresh prompt → fire the relevant tools/specialists, "
        "write findings to substrate per the prompt's path direction.\n"
        "- Compose-deliverable prompt → write section partials per spec, "
        "the framework auto-composes (ADR-262 D4) unless the prompt "
        "opts out.\n"
        "- Conditions-check prompt → ProposeAction when conditions are met."
    ),
    "addressed": (
        "## This invocation\n\n"
        "The operator checked in at the cockpit. They are NOT asking you "
        "what to do — they delegated that to you and they're seeing how the "
        "operation is running. Your job is to act, then tell them what you did "
        "and why.\n\n"
        "**All persona + framework + domain substrate is ALREADY PRE-LOADED "
        "in the message above** (IDENTITY, principles, MANDATE, "
        "_operator_profile, _risk, _money_truth, signal_files, workspace_state). "
        "Do NOT call ReadFile on these — read them from the message you are "
        "reading right now.\n\n"
        "Use ReadFile only for files NOT shown above (e.g. specific reports, "
        "decisions.md history, recent recurrence outputs).\n\n"
        "**The default is action.** Read state, decide what moves the "
        "operation forward, do it. Pick the most disciplined available action "
        "per your framework:\n\n"
        "- Signal conditions met → ProposeAction with sizing math (this is "
        "the strongest action you can take — take it whenever conditions warrant)\n"
        "- Data is stale and a refresh would change the next assessment → "
        "FireInvocation the relevant recurrence to commission fresh substrate. "
        "Narrate: 'I'm refreshing X — re-assessing when it completes.' This "
        "is action, not deferral.\n"
        "- A pattern, observation, or judgment is worth retaining for the next "
        "cycle → WriteFile to your own substrate (decisions.md or notes "
        "within /workspace/review/). The operator's chair owns its "
        "notebook; use it.\n"
        "- Combination of the above — typical case is fire-refresh + write-note "
        "explaining why you fired it. Sequence multiple actions in one turn.\n\n"
        "**Stand-down is the LAST option, only when no action moves the "
        "operation forward.** Before standing down, ask: would a refresh "
        "tighten my next assessment? Would a written observation help next "
        "quarter's audit? Is there research I should commission? Almost "
        "always the answer is yes — do that. Pure-stand-down is justified "
        "only when state is fully fresh AND signals are unambiguously absent "
        "AND no research-action would change next cycle's verdict.\n\n"
        "**DO NOT enumerate options for the operator.** Don't say 'do you "
        "want me to (1)... or (2)... or (3)...?'. That's deferral. Pick the "
        "option your framework tells you is right and execute it. The "
        "operator will override you next turn if they disagree.\n\n"
        "**Hard rule: call ReturnVerdict last to close the turn.** Verdict "
        "should be `approve` if you proposed an action, `stand_down` if "
        "you took only research/refresh actions and are awaiting their "
        "completion, or `stand_down` if pure-stand-down was genuinely "
        "warranted. Reasoning narrates what you did in first person."
    ),
}


# Composed once at module import; refreshes on deploy when canonical sources change.
def _build_system_prompt() -> str:
    """Compose the Reviewer system prompt from canonical sources.
    ADR-258 D5: cockpit awareness is generated from path constants and the
    chat-mode primitive registry — drift-resistant by construction."""
    from agents.cockpit_awareness import build_cockpit_section
    return "\n\n".join([_PERSONA_FRAME, build_cockpit_section()])


_SYSTEM_PROMPT_CACHE: str | None = None


def _system_prompt() -> str:
    """Lazy-cached system prompt (composed once per process)."""
    global _SYSTEM_PROMPT_CACHE
    if _SYSTEM_PROMPT_CACHE is None:
        _SYSTEM_PROMPT_CACHE = _build_system_prompt()
    return _SYSTEM_PROMPT_CACHE


# ---------------------------------------------------------------------------
# User message builder — trigger-specific pre-loaded substrate
# ---------------------------------------------------------------------------

def _build_user_message(trigger: str, ctx: ReviewerContext) -> str:
    """Compose the user message envelope for an invocation.
    Pre-loads governance + persona + framework + domain substrate based on
    what the caller provided. Trigger-specific framing is appended last."""
    import json as _json
    parts: list[str] = []

    # Persona — always first
    parts += [
        "## IDENTITY.md — Your persona",
        "",
        ctx.get("identity_md") or "_(empty — reason as a neutral skeptical judgment seat)_",
        "",
    ]
    parts += [
        "## principles.md — Your framework",
        "",
        ctx.get("principles_md") or "_(empty — no declared framework)_",
        "",
    ]
    if ctx.get("precedent_md"):
        parts += [
            "## PRECEDENT.md — Operator's durable interpretations (overrides principles)",
            "",
            ctx["precedent_md"],
            "",
        ]
    if ctx.get("mandate_md"):
        parts += ["## MANDATE.md — Operation's primary intent", "", ctx["mandate_md"], ""]
    if ctx.get("autonomy_md"):
        parts += ["## AUTONOMY.md — Delegation ceiling", "", ctx["autonomy_md"], ""]

    # Domain substrate
    if ctx.get("operator_profile_md"):
        parts += ["## _operator_profile.md — Declared strategy", "", ctx["operator_profile_md"], ""]
    if ctx.get("risk_md"):
        parts += ["## _risk.md — Hard floors", "", ctx["risk_md"], ""]
    if ctx.get("performance_md"):
        parts += ["## _money_truth.md — Track record (with by_signal frontmatter)", "", ctx["performance_md"], ""]

    # Trigger-specific (ADR-260 D2 amended by ADR-263: addressed | reactive)
    # `reactive` covers two sub-shapes — proposal arrival (specialized
    # reactive handler per ADR-247) and judgment-mode recurrence fire
    # (cron-driven per ADR-263). The sub-shape is detected by which keys
    # are present in the context bag, not by a separate trigger value.
    if trigger == "reactive":
        # Sub-shape detection: recurrence_prompt key present → judgment-mode
        # recurrence fire; otherwise → proposal arrival.
        if ctx.get("recurrence_prompt") or ctx.get("recurrence_slug"):
            # Judgment-recurrence fire: the recurrence's prompt is the
            # operator's instruction handed to the Reviewer at scheduled time
            # (ADR-261 D1). It is the addressed-equivalent message — narrate
            # intent, then act.
            prompt_text = ctx.get("recurrence_prompt") or ctx.get("user_message") or ""
            slug = ctx.get("recurrence_slug") or ctx.get("trigger_slug")
            if slug:
                parts += [f"## Recurrence: `{slug}`", ""]
            if prompt_text:
                parts += ["## Recurrence prompt (operator's instruction)", "", prompt_text.strip(), ""]
            if ctx.get("signal_files"):
                parts += ["## Current signal state (pre-loaded)", "", ctx["signal_files"], ""]
            if ctx.get("workspace_state"):
                parts += ["## Workspace state", "", ctx["workspace_state"], ""]
            if ctx.get("recent_decisions_md"):
                parts += ["## Recent decisions", "", ctx["recent_decisions_md"], ""]
        else:
            # Proposal arrival: the proposal row is the event being judged.
            row = ctx.get("proposal_row") or {}
            if row:
                parts += [
                    "## Proposed action",
                    "",
                    f"**action_type:** `{row.get('action_type', '?')}`",
                    f"**reversibility:** {row.get('reversibility', '?')}",
                ]
                if row.get("rationale"):
                    parts.append(f"**rationale:** {row['rationale']}")
                if row.get("expected_effect"):
                    parts.append(f"**expected_effect:** {row['expected_effect']}")
                inputs = row.get("inputs") or {}
                parts += ["**inputs:**", "```json", _json.dumps(inputs, indent=2, default=str), "```", ""]

    elif trigger == "addressed":
        if ctx.get("signal_files"):
            parts += ["## Current signal state (pre-loaded)", "", ctx["signal_files"], ""]
        if ctx.get("workspace_state"):
            parts += ["## Workspace state", "", ctx["workspace_state"], ""]
        if ctx.get("conversation_window"):
            parts += ["## Recent conversation", "", ctx["conversation_window"], ""]
        msg = ctx.get("user_message", "")
        parts += ["## Operator message", "", msg.strip(), ""]

    parts.append(_TRIGGER_FRAMING.get(trigger, ""))
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Public entry point — invoke_reviewer (ADR-258)
# ---------------------------------------------------------------------------

async def invoke_reviewer(
    client: Any,
    user_id: str,
    *,
    trigger: Literal["addressed", "reactive"],
    context: ReviewerContext,
    event_callback: Any = None,
) -> ReviewerOutput | None:
    """Unified Reviewer invocation — ADR-258 (revised) + ADR-260 D2 + ADR-263.

    Reviewer is a chat-mode caller of the canonical primitive registry.
    Tool surface = curated REVIEWER_PRIMITIVES + ReturnVerdict. Tool-use loop
    bounded at 12 rounds for addressed, 3 for reactive (ADR-260 D8).

    Safety story: attribution (ADR-209 authored substrate) + revision chain
    + AUTONOMY gating + operator-authored _locks.yaml. Not access control.

    Two triggers (ADR-260 D2 amended by ADR-263 D2):
    - `addressed` — operator addressed the Reviewer (chat turn).
    - `reactive`  — substrate event requires judgment. Two sub-shapes,
                    differentiated by context-bag contents:
                      • Proposal arrival (proposal_row in context).
                      • Judgment-mode recurrence fire (recurrence_prompt in context;
                        per ADR-263, mechanical-mode recurrences do NOT invoke
                        the Reviewer — they execute deterministic primitives).

    Cron is part of the environment that fires recurrences; the recurrence's
    `mode` field declares whether the fire wakes the Reviewer (judgment) or
    runs as deterministic Python (mechanical). The Reviewer never sees the
    `scheduled` trigger value because cron-fired Reviewer wakes are now
    `reactive` (ADR-263 D2 amendment).

    Model selection by trigger:
    - Sonnet (capital decisions): reactive proposals
    - Haiku  (reasoning):         addressed + reactive recurrences

    Optional `event_callback`: an async callable `(event_dict) -> None` that
    fires progressively as the loop advances — once per round_start, once
    per tool_call, once per round_end. Used by chat.py to stream live
    progress to the operator (so the UI doesn't go silent during the loop).

    Never raises. Returns None on total failure.
    """
    from services.primitives.registry import REVIEWER_PRIMITIVES, execute_primitive
    from types import SimpleNamespace

    # ADR-260 D2 + D8 + ADR-263 D2: model + round-bound selection.
    #
    # `reactive` covers two sub-shapes (per `_build_user_message` differentiation):
    #   - proposal arrival → Sonnet (capital judgment, discrete decision call)
    #   - judgment-recurrence fire → Haiku (longer real-time loop, similar
    #     to the previous `scheduled` trigger that ADR-263 D2 collapsed in)
    # `addressed` always uses Haiku (operator chat turn).
    #
    # Sub-shape detection mirrors the pattern in `_build_user_message`:
    # presence of `recurrence_prompt`/`recurrence_slug` keys = recurrence fire.
    is_recurrence_fire = bool(
        context.get("recurrence_prompt") or context.get("recurrence_slug")
    ) if isinstance(context, dict) else False

    use_sonnet = (trigger == "reactive") and not is_recurrence_fire
    model = _SONNET if use_sonnet else _HAIKU
    caller = _CALLER_SONNET if use_sonnet else _CALLER_HAIKU

    # Build auth namespace with reviewer_caller flag — handlers consult this
    # for ADR-258 D9 lock enforcement on operator-shared substrate.
    auth = SimpleNamespace(
        client=client,
        user_id=user_id,
        reviewer_caller=True,
        agent=None,
        agent_slug=None,
        task_slug=None,
    )

    # Tool list = curated reviewer primitives + ReturnVerdict (ADR-258 revised)
    tools = list(REVIEWER_PRIMITIVES) + [RETURN_VERDICT_TOOL]

    async def _emit(event: dict) -> None:
        """Best-effort progress emit — never raises, never blocks the loop.
        Callers can inspect events to surface progress in the UI without
        blocking the LLM cycle."""
        if event_callback is None:
            return
        try:
            await event_callback(event)
        except Exception as cb_exc:
            logger.debug("[REVIEWER] event_callback raised: %s", cb_exc)

    try:
        user_message = _build_user_message(trigger, context)
        messages: list[dict] = [{"role": "user", "content": user_message}]
        actions_taken: list[dict] = []
        verdict_raw: dict | None = None

        # ADR-260 D8 + ADR-263: round bound varies by sub-shape.
        # - Proposal-arrival reactive (Sonnet) is a discrete decision call → 3 rounds.
        # - Recurrence-fire reactive (Haiku) needs room for the recurrence's full
        #   real-time tool-use loop → 12 rounds (same as old `scheduled`).
        # - Addressed (Haiku) is a chat turn with full tool budget → 12 rounds.
        max_rounds = 3 if use_sonnet else 12
        total_input = 0
        total_output = 0
        rounds_used = 0

        for _round in range(max_rounds):
            rounds_used = _round + 1
            # Commit H (2026-05-11): cooperative cancellation check between
            # rounds. When the operator clicks Stop in the feed composer,
            # the FE POSTs /api/feed/cancel which sets
            # chat_sessions.cancellation_requested=true on the workspace's
            # active session. We check it here at the top of every round
            # (not inside a single LLM call — that's not interruptible).
            # On cancel: exit early with stand_down verdict; the caller
            # then resets the flag for the next session.
            if _check_session_cancellation(client, user_id):
                logger.info(
                    "[REVIEWER] cancellation_requested honored at round %d/%d trigger=%s user=%s",
                    rounds_used, max_rounds, trigger, user_id[:8],
                )
                _clear_session_cancellation(client, user_id)
                return ReviewerOutput(
                    verdict="stand_down",
                    reasoning="Operator interrupted the in-flight Loop via the Stop affordance. No further actions taken in this session.",
                    confidence="high",
                    actions_taken=actions_taken,
                )
            tool_choice = {"type": "any"} if _round == 0 else {"type": "auto"}
            await _emit({"phase": "round_start", "round": rounds_used, "trigger": trigger})

            response = await chat_completion_with_tools(
                messages=messages,
                system=_system_prompt(),
                tools=tools,
                model=model,
                max_tokens=2048,
                tool_choice=tool_choice,
            )

            usage = response.usage or {}
            total_input += int(usage.get("input_tokens", 0) or 0)
            total_output += int(usage.get("output_tokens", 0) or 0)

            tool_uses = response.tool_uses or []

            # Append assistant turn for multi-round history
            assistant_content: list[dict] = []
            for block in (response.content or []):
                btype = getattr(block, "type", None)
                if btype == "text":
                    assistant_content.append({"type": "text", "text": getattr(block, "text", "")})
                elif btype == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": getattr(block, "id", ""),
                        "name": getattr(block, "name", ""),
                        "input": getattr(block, "input", {}),
                    })
            if assistant_content:
                messages.append({"role": "assistant", "content": assistant_content})

            if not tool_uses:
                # Text-only response — fallback to stand_down with the text as reasoning
                text_fallback = (response.text or "").strip()
                if text_fallback:
                    logger.warning(
                        "[REVIEWER] text-only response round %d trigger=%s user=%s",
                        _round, trigger, user_id[:8],
                    )
                    verdict_raw = {
                        "verdict": "stand_down",
                        "reasoning": text_fallback[:1000],
                        "confidence": "medium",
                    }
                break

            tool_results: list[dict] = []
            clarify_called_this_round = False
            for tu in tool_uses:
                name = tu.name
                inp = tu.input or {}
                tu_id = tu.id

                if name == "ReturnVerdict":
                    verdict_raw = inp
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tu_id,
                        "content": "Verdict recorded.",
                    })
                    break

                # Emit tool_start for UI progress before dispatch
                await _emit({
                    "phase": "tool_start",
                    "round": rounds_used,
                    "tool": name,
                    "input": inp,
                })

                # Dispatch through canonical primitive registry
                try:
                    result = await execute_primitive(auth, name, inp)
                except Exception as exc:
                    result = {"success": False, "error": "execution_error", "message": str(exc)}

                # Capture proposal_id from ProposeAction results so the
                # downstream narration emit (surface_reviewer_actions) can
                # render an inline ProposalCard chip per Audit-pass-2 DD-4.
                # Pre-2026-05-11, narration was plain-text and operators had
                # to mentally stitch from the feed entry to the cockpit Queue
                # to find the proposal — mental-thread broken.
                action_record: dict = {
                    "tool": name,
                    "input": inp,
                    "success": bool(result.get("success", True)) if isinstance(result, dict) else True,
                    "summary": _summarize_result(result),
                }
                if name == "ProposeAction" and isinstance(result, dict):
                    pid = result.get("proposal_id") or (
                        result.get("proposal", {}) or {}
                    ).get("id")
                    if pid:
                        action_record["proposal_id"] = pid
                actions_taken.append(action_record)

                await _emit({
                    "phase": "tool_end",
                    "round": rounds_used,
                    "tool": name,
                    "success": actions_taken[-1]["success"],
                    "summary": actions_taken[-1]["summary"],
                })

                # Compact result for the model — limit size
                result_text = _compact_result_for_model(result)
                logger.info(
                    "[REVIEWER] tool=%s trigger=%s user=%s success=%s",
                    name, trigger, user_id[:8],
                    actions_taken[-1]["success"],
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu_id,
                    "content": result_text,
                })

                if name == "Clarify":
                    clarify_called_this_round = True

            if verdict_raw is not None:
                break

            # Loop-shape nudges to prevent runaway tool use:
            # - After Clarify: the operator's question is logged; the turn must close
            # - After round 4: hard nudge to close the turn before round budget exhausts
            nudge: str | None = None
            if clarify_called_this_round:
                nudge = (
                    "Your Clarify question has been surfaced to the operator. "
                    "Now call ReturnVerdict(verdict='stand_down', reasoning='[your "
                    "persona-voice summary including the question you asked]', "
                    "confidence='medium') to close this turn. The operator will "
                    "respond on a subsequent turn."
                )
            elif _round >= 4:
                nudge = (
                    f"You are on round {_round + 1} of {max_rounds}. You must call "
                    "ReturnVerdict next to close this turn. Synthesize what you've "
                    "learned from substrate above into a verdict + reasoning. Even "
                    "if conditions are unclear, ReturnVerdict(stand_down) with your "
                    "honest assessment is correct."
                )

            if tool_results:
                # Append nudge as a text block alongside tool_result blocks so the
                # model sees it as part of the user turn. tool_use_id cannot be
                # synthesized — must reference a real tool_use block — so the
                # nudge rides as a separate text block in the same user message.
                content_blocks: list[dict] = list(tool_results)
                if nudge:
                    content_blocks.append({"type": "text", "text": nudge})
                messages.append({"role": "user", "content": content_blocks})

        # Token accounting. Carry recurrence_slug + signal_id when known
        # so cost can be broken down per-recurrence and per-signal post-hoc
        # (cost-truth observability surfaced as gap during 2026-05-13 audit
        # of overnight Reviewer fires).
        usage_metadata: dict[str, Any] = {"trigger": trigger, "rounds": rounds_used}
        if isinstance(context, dict):
            if context.get("recurrence_slug"):
                usage_metadata["slug"] = context["recurrence_slug"]
            if context.get("recurrence_prompt"):
                usage_metadata["sub_shape"] = "recurrence_fire"
            elif trigger == "reactive" and context.get("proposal_row"):
                usage_metadata["sub_shape"] = "proposal_arrival"
        record_token_usage(
            client,
            user_id=user_id,
            caller=caller,
            model=model,
            input_tokens=total_input,
            output_tokens=total_output,
            ref_id=context.get("proposal_row", {}).get("id") if trigger == "proposal" else None,
            metadata=usage_metadata,
        )

        if verdict_raw is None:
            # Loop exhausted without ReturnVerdict — construct fallback from last text
            last_text = ""
            for m in reversed(messages):
                if m.get("role") != "assistant":
                    continue
                for block in (m.get("content") or []):
                    if isinstance(block, dict) and block.get("type") == "text":
                        last_text = block.get("text", "")
                        if last_text:
                            break
                if last_text:
                    break
            logger.warning(
                "[REVIEWER] no ReturnVerdict after %d rounds trigger=%s user=%s",
                max_rounds, trigger, user_id[:8],
            )
            verdict_raw = {
                "verdict": "stand_down",
                "reasoning": last_text or (
                    "I was unable to reach a verdict within my round budget. "
                    "Substrate may need refresh — fire track-universe or signal-evaluation."
                ),
                "confidence": "low",
            }

        verdict = verdict_raw.get("verdict", "")
        reasoning = (verdict_raw.get("reasoning") or "").strip()
        confidence = verdict_raw.get("confidence") or "low"

        _VALID_VERDICTS = {
            "approve", "reject", "defer",
            "no_change", "narrow", "relax", "character_note", "pause_autonomy",
            "stand_down",
        }
        if verdict not in _VALID_VERDICTS:
            logger.warning(
                "[REVIEWER] invalid verdict=%r trigger=%s user=%s", verdict, trigger, user_id[:8],
            )
            return None
        if not reasoning:
            logger.warning(
                "[REVIEWER] empty reasoning trigger=%s user=%s", trigger, user_id[:8],
            )
            return None

        output: ReviewerOutput = {
            "verdict": verdict,
            "reasoning": reasoning,
            "confidence": confidence,
            "actions_taken": actions_taken,
        }

        # Under ADR-263's two-trigger model, reflection-shaped output fields
        # (`proposals`, `evidence_summary`) may appear on any reactive
        # invocation whose recurrence prompt directs the Reviewer to author
        # proposals or summarize evidence. The gate is "model returned the
        # field," not "trigger == reflection" (which is a dead enum value
        # post-collapse). Older callers relying on field-presence to detect
        # reflection-shaped output continue to work.
        if verdict_raw.get("proposals") or verdict_raw.get("evidence_summary"):
            from agents.reviewer_agent_compat import _normalize_reflection_proposals
            if verdict_raw.get("proposals"):
                output["proposals"] = _normalize_reflection_proposals(verdict_raw.get("proposals") or [])
            if verdict_raw.get("evidence_summary"):
                output["evidence_summary"] = (verdict_raw.get("evidence_summary") or "").strip()

        return output

    except Exception as exc:
        logger.error(
            "[REVIEWER] invoke_reviewer failed trigger=%s user=%s: %s",
            trigger, user_id[:8] if user_id else "?", exc,
        )
        return None


def _summarize_result(result: Any) -> str:
    """One-line summary of a primitive result for actions_taken audit log."""
    if not isinstance(result, dict):
        return "ok"
    if result.get("success") is False:
        return f"error: {result.get('error') or 'unknown'}"
    if "path" in result:
        return f"path={result['path']}"
    if "proposal_id" in result:
        return f"proposal_id={result['proposal_id'][:8]}..."
    if "slug" in result:
        return f"slug={result['slug']}"
    return "ok"


def _compact_result_for_model(result: Any) -> str:
    """Compact a primitive result for tool_result content sent back to the model.
    Limits content size so a large file read doesn't blow the round budget."""
    import json as _json
    if isinstance(result, dict):
        # If there's a 'content' field (from ReadFile), truncate generously
        if "content" in result and isinstance(result["content"], str):
            content = result["content"]
            if len(content) > 6000:
                content = content[:6000] + f"\n\n_(truncated from {len(result['content'])} chars)_"
            shaped = {**result, "content": content}
            return _json.dumps(shaped, default=str)[:8000]
        return _json.dumps(result, default=str)[:8000]
    return str(result)[:8000]


# ---------------------------------------------------------------------------
    """Read all signal state YAML files and return compact summary.
    Public helper — called by invocation_dispatcher to pre-load heartbeat context."""
    import re as _re
    try:
        result = (
            client.table("workspace_files")
            .select("path, content")
            .eq("user_id", user_id)
            .like("path", "/workspace/context/trading/signals/%.yaml")
            .execute()
        )
        lines = []
        for row in result.data or []:
            path = row.get("path", "")
            content = row.get("content", "")
            slug = path.split("/")[-1].replace(".yaml", "")
            triggered = _re.search(r"triggered_today:\s*(\[.*?\])", content)
            state = _re.search(r"state:\s*(\S+)", content)
            lines.append(
                f"- {slug}: state={state.group(1) if state else '?'} "
                f"triggered={triggered.group(1) if triggered else '[]'}"
            )
        return "\n".join(lines) if lines else "_(no signal state files found)_"
    except Exception:
        return "_(signal files unavailable)_"


# ---------------------------------------------------------------------------
# Cooperative cancellation (Commit H.1, 2026-05-11)
# ---------------------------------------------------------------------------
#
# Two helpers used by invoke_reviewer's per-round cancellation check (Mode 1
# of the interruption surface). The flag lives on chat_sessions
# (migration 173); operator's POST /api/feed/cancel sets it; the Reviewer
# checks + clears it.
#
# Design choice: we look up the operator's *active workspace session* (same
# function reviewer_chat_surfacing uses) rather than threading a session_id
# parameter through every Reviewer call site. The Reviewer doesn't know
# which session it's running on behalf of — that's the orchestration
# context. Looking up the active session at check time matches how
# narration emits work too.
#
# Failure discipline: any exception (Supabase blip, no active session, etc.)
# → returns False (no cancellation). Cancellation is best-effort safety,
# never blocks the Loop on errors.

def _check_session_cancellation(client: Any, user_id: str) -> bool:
    """Return True iff the operator's active session has cancellation_requested=true."""
    if not user_id:
        return False
    try:
        from services.narrative import find_active_workspace_session
        session_id = find_active_workspace_session(client, user_id)
        if not session_id:
            return False
        result = (
            client.table("chat_sessions")
            .select("cancellation_requested")
            .eq("id", session_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            return False
        return bool(rows[0].get("cancellation_requested", False))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[REVIEWER] cancellation check failed: %s", exc)
        return False


def _clear_session_cancellation(client: Any, user_id: str) -> None:
    """Reset the cancellation flag after honoring it. Best-effort; never raises."""
    if not user_id:
        return
    try:
        from services.narrative import find_active_workspace_session
        session_id = find_active_workspace_session(client, user_id)
        if not session_id:
            return
        client.table("chat_sessions").update(
            {"cancellation_requested": False}
        ).eq("id", session_id).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[REVIEWER] cancellation clear failed: %s", exc)


async def read_signal_files(client: Any, user_id: str) -> str:
    """Read all signal state YAML files and return compact summary.
    Public helper — called by invocation_dispatcher and chat.py to pre-load
    signal state into invoke_reviewer's context bag for the heartbeat /
    addressed triggers."""
    import re as _re
    try:
        result = (
            client.table("workspace_files")
            .select("path, content")
            .eq("user_id", user_id)
            .like("path", "/workspace/context/trading/signals/%.yaml")
            .execute()
        )
        lines = []
        for row in result.data or []:
            path = row.get("path", "")
            content = row.get("content", "")
            slug = path.split("/")[-1].replace(".yaml", "")
            triggered = _re.search(r"triggered_today:\s*(\[.*?\])", content)
            state = _re.search(r"state:\s*(\S+)", content)
            lines.append(
                f"- {slug}: state={state.group(1) if state else '?'} "
                f"triggered={triggered.group(1) if triggered else '[]'}"
            )
        return "\n".join(lines) if lines else "_(no signal state files found)_"
    except Exception:
        return "_(signal files unavailable)_"
