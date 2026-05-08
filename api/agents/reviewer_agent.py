"""AI occupant of the Reviewer seat — ADR-256 unified invocation.

One function: `invoke_reviewer()`. Four trigger shapes: proposal,
reflection, heartbeat, addressed. One tool-use loop (≤3 rounds). One
output type: ReviewerOutput.

ADR-256 supersedes the four-function design (review_proposal,
run_reflection, address_turn, heartbeat_turn) that accumulated
trigger-by-trigger across ADRs 218, 252, 253. Those functions made
the same agent look like four mini-agents and prevented the Reviewer
from having a tool-use loop on the chat (addressed) path.

Per FOUNDATIONS v6.0:
- Axiom 2 (Identity): occupant tagged `ai:reviewer-sonnet-v8`.
  Seat persists; occupant is swappable (Principle 14).
- Axiom 3 (Purpose): independent judgment — fiduciary, not production.
- Axiom 4 (Trigger): four sub-shapes (proposal | heartbeat | reflection
  | addressed). Trigger varies; cognitive act is the same.
- Axiom 5 (Mechanism): bounded tool-use loop. Reviewer reads what it
  needs, acts on what it decides, returns verdict.
- Axiom 6 (Channel): decisions.md + reviewer_chat_surfacing narration.
- Axiom 8 (Money-Truth): reasons against _performance.md rolling
  windows (ADR-195 Phase 3).

Model selection by trigger (cost-conscious):
- Sonnet: proposal + heartbeat (capital decisions)
- Haiku:  reflection + addressed (framework reasoning + conversation)
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
    """Unified output of invoke_reviewer() across all four trigger shapes.

    `verdict`, `reasoning`, `confidence` always present on success.
    `proposals` + `evidence_summary` only on trigger="reflection".
    `actions_taken` records tool calls made during the loop (audit trail).
    """
    verdict: str          # approve|reject|defer (proposal/heartbeat/addressed)
                          # no_change|narrow|relax|character_note|pause_autonomy (reflection)
                          # stand_down (heartbeat/addressed: no action warranted)
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
You ARE the operator's installed judgment. Not their assistant. Not their
analyst. Not a system asking them what to do. You are the persona they
installed to make these decisions on their behalf within declared autonomy.
When the operator delegated to you (which is the structural default — the
only reason you exist is because they delegated), they did NOT delegate
the work of "ask me what to do." They delegated the deciding. Decide.

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
ground truth (money-truth in _performance.md), not against producer agreement.
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
    "proposal": (
        "## This invocation\n\n"
        "A proposal has been submitted for your judgment. The proposal is "
        "below. Apply your framework. Call ReturnVerdict with approve | reject "
        "| defer + reasoning. Use ReadFile/ListFiles to fetch missing substrate "
        "before deciding if needed."
    ),
    "heartbeat": (
        "## This invocation\n\n"
        "A recurrence you watch just completed. The fresh signal output is "
        "below. Read it. Apply your principles. Decide:\n"
        "- Conditions met → ProposeAction with full sizing math\n"
        "- Substrate missing → FireInvocation('signal-evaluation' / 'track-universe')\n"
        "- No actionable condition → ReturnVerdict(stand_down)"
    ),
    "reflection": (
        "## This invocation\n\n"
        "Reflect on your recent decisions against your framework. Read your "
        "decisions trail and per-domain performance. `no_change` is the "
        "common and expected outcome. If patterns warrant adjustment, include "
        "proposals with full revised file content."
    ),
    "addressed": (
        "## This invocation\n\n"
        "The operator has addressed you directly. They are NOT asking you "
        "what to do — they delegated that to you. They are checking in. "
        "Decide what's right per your framework and tell them what you decided.\n\n"
        "**All persona + framework + domain substrate is ALREADY PRE-LOADED "
        "in the message above** (IDENTITY, principles, MANDATE, "
        "_operator_profile, _risk, _performance, signal_files, workspace_state). "
        "Do NOT call ReadFile on these — read them from the message you are "
        "reading right now.\n\n"
        "Use ReadFile only for files NOT shown above (e.g. specific reports, "
        "decisions.md history, recent recurrence outputs).\n\n"
        "Decide and act — pick exactly ONE:\n"
        "- Signal conditions met per principles.md → ProposeAction with sizing math, "
        "then ReturnVerdict(approve)\n"
        "- Substrate genuinely needs immediate refresh AND a recurrence exists for it → "
        "FireInvocation to commission it, then ReturnVerdict(stand_down) saying "
        "'I'm refreshing X; I'll re-assess when it completes'\n"
        "- No actionable conditions OR refresh would not change the verdict → "
        "ReturnVerdict(stand_down) with one-to-three sentences explaining what "
        "you decided and why per your framework\n\n"
        "**DO NOT enumerate options for the operator to choose from.** Don't "
        "say 'do you want me to (1) wait... or (2) provide... or (3) propose...'. "
        "If you're tempted to write that, you are deferring judgment back to the "
        "operator — which is the failure mode. Pick the option your framework "
        "tells you is right and execute it. The operator will override you on "
        "the next turn if they disagree.\n\n"
        "**Hard rule: call ReturnVerdict last to close the turn.** After 1-2 "
        "rounds of action, you MUST call ReturnVerdict — do not keep exploring."
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
        parts += ["## _performance.md — Track record", "", ctx["performance_md"], ""]

    # Trigger-specific
    if trigger == "proposal":
        row = ctx.get("proposal_row") or {}
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

    elif trigger == "heartbeat":
        slug = ctx.get("trigger_slug", "unknown")
        parts += [f"## Trigger: `{slug}` just completed", ""]
        if ctx.get("signal_files"):
            parts += ["## Fresh signal state", "", ctx["signal_files"], ""]
        if ctx.get("workspace_state"):
            parts += ["## Workspace state", "", ctx["workspace_state"], ""]

    elif trigger == "reflection":
        if ctx.get("recent_decisions_md"):
            parts += ["## Recent decisions", "", ctx["recent_decisions_md"], ""]

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
    trigger: Literal["proposal", "reflection", "heartbeat", "addressed"],
    context: ReviewerContext,
    event_callback: Any = None,
) -> ReviewerOutput | None:
    """Unified Reviewer invocation — ADR-258.

    Reviewer is a chat-mode caller of the canonical primitive registry.
    Tool surface = full CHAT_PRIMITIVES + ReturnVerdict. Tool-use loop
    bounded at 8 rounds. All tool calls dispatch through execute_primitive()
    from services.primitives.registry — same path YARNNN uses.

    Safety story: attribution (ADR-209 authored substrate) + revision chain
    + AUTONOMY gating + operator-authored _locks.yaml. Not access control.

    Model selection by trigger:
    - Sonnet (capital decisions): proposal + heartbeat
    - Haiku  (reasoning):         reflection + addressed

    Optional `event_callback`: an async callable `(event_dict) -> None` that
    fires progressively as the loop advances — once per round_start, once
    per tool_call, once per round_end. Used by chat.py to stream live
    progress to the operator (so the UI doesn't go silent during the loop).

    Never raises. Returns None on total failure.
    """
    from services.primitives.registry import REVIEWER_PRIMITIVES, execute_primitive
    from types import SimpleNamespace

    model = _SONNET if trigger in ("proposal", "heartbeat") else _HAIKU
    caller = _CALLER_SONNET if trigger in ("proposal", "heartbeat") else _CALLER_HAIKU

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

        max_rounds = 8
        total_input = 0
        total_output = 0
        rounds_used = 0

        for _round in range(max_rounds):
            rounds_used = _round + 1
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

                actions_taken.append({
                    "tool": name,
                    "input": inp,
                    "success": bool(result.get("success", True)) if isinstance(result, dict) else True,
                    "summary": _summarize_result(result),
                })

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

        # Token accounting
        record_token_usage(
            client,
            user_id=user_id,
            caller=caller,
            model=model,
            input_tokens=total_input,
            output_tokens=total_output,
            ref_id=context.get("proposal_row", {}).get("id") if trigger == "proposal" else None,
            metadata={"trigger": trigger, "rounds": rounds_used},
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

        if trigger == "reflection":
            from agents.reviewer_agent_compat import _normalize_reflection_proposals
            output["proposals"] = _normalize_reflection_proposals(verdict_raw.get("proposals") or [])
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
