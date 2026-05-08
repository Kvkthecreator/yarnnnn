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
# Unified tool set (ADR-256 D3) — Reviewer has hands
# ---------------------------------------------------------------------------
# The Reviewer runs a bounded tool-use loop (≤3 rounds). It reads what it
# needs, acts on what it decides, then calls ReturnVerdict to end the loop.
# No more action_instruction string — actions are structured tool calls.

_TOOLS = [
    {
        "name": "ReadFile",
        "description": (
            "Read a workspace file. Use to fetch signal state, performance data, "
            "or any substrate you need before deciding. Path must start with /workspace/."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Full workspace path, e.g. /workspace/context/trading/signals/nvda.yaml"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "FireInvocation",
        "description": (
            "Fire an existing recurrence by slug. Use when substrate is missing or stale "
            "and you need it before you can assess. The recurrence must already be declared."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "slug": {"type": "string", "description": "Recurrence slug, e.g. signal-evaluation"},
                "reason": {"type": "string", "description": "Why you are firing this now"},
            },
            "required": ["slug", "reason"],
        },
    },
    {
        "name": "ProposeAction",
        "description": (
            "Submit a structured action proposal for execution. Use when signal conditions "
            "are clearly met per principles.md and the action is within your declared edge. "
            "The proposal routes through the AUTONOMY gate — auto-execute if within ceiling, "
            "queue for operator click if above."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "action_type": {"type": "string", "description": "e.g. trading.submit_order_paper"},
                "ticker": {"type": "string"},
                "direction": {"type": "string", "enum": ["long", "short"]},
                "quantity": {"type": "integer"},
                "signal": {"type": "string", "description": "Signal that triggered this, e.g. IH-3"},
                "rationale": {"type": "string", "description": "Your reasoning in persona voice"},
            },
            "required": ["action_type", "rationale"],
        },
    },
    {
        "name": "WriteFile",
        "description": (
            "Write a file within /workspace/review/ only. Use for writing notes to "
            "decisions.md or updating your own substrate. Scope ceiling: /workspace/review/."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Must be under /workspace/review/"},
                "content": {"type": "string"},
                "mode": {"type": "string", "enum": ["overwrite", "append"], "default": "append"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "ReturnVerdict",
        "description": (
            "End the loop and return your structured verdict. Call exactly once, last. "
            "After any ReadFile/FireInvocation/ProposeAction calls, call this to close the turn."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "verdict": {
                    "type": "string",
                    "enum": [
                        "approve", "reject", "defer",          # proposal / heartbeat / addressed
                        "no_change", "narrow", "relax",        # reflection
                        "character_note", "pause_autonomy",    # reflection
                        "stand_down",                          # heartbeat / addressed: no action
                    ],
                },
                "reasoning": {
                    "type": "string",
                    "description": "2-5 sentences in persona voice. Written to decisions.md verbatim.",
                },
                "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                # reflection-only
                "proposals": {
                    "type": "array",
                    "description": "Framework change proposals (reflection trigger only).",
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
                    "description": "Substrate citations (reflection trigger only).",
                },
            },
            "required": ["verdict", "reasoning", "confidence"],
        },
    },
]


# ---------------------------------------------------------------------------
# System prompt — one base, trigger framing in user message (ADR-256 D2)
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are the operator's judgment character — personified via IDENTITY.md.
You are not a system, not a filter, not a policy engine. You are a person:
the specific judgment character the operator installed to act on their behalf.
Your IDENTITY.md tells you who that is. Embody it fully.

You have a tool-use loop (≤3 rounds). Use it:
1. ReadFile — fetch any substrate you need before deciding (signal files,
   performance data, etc.). Do this first if data is missing.
2. FireInvocation / ProposeAction / WriteFile — act on your decision.
3. ReturnVerdict — always last. Closes the loop.

You reason in capital-EV terms:
- What is the upside if this action works?
- What is the downside if it doesn't?
- Is the ratio asymmetric in your favor?
- Does the track record support this edge, or is it untested?

**Autonomy delegation (ADR-217 + ADR-229 D1):**
You run BEFORE the autonomy filter. Render a verdict on merits regardless
of whether AUTONOMY would auto-execute. Your framework (principles +
precedent) can narrow delegation but never widen it.

**Precedent hierarchy:**
PRECEDENT.md overrides conflicting clauses in principles.md. Cite precedent
explicitly when it drove the verdict.

**Voice discipline:**
First person, your declared character's register. Never cite filenames.
Say "your declared 3% risk ceiling" not "_risk.md says".
Two sentences: verdict first, reasoning second.

Call ReturnVerdict exactly once — always last.
"""


# ---------------------------------------------------------------------------
# User message builder — trigger-specific framing (ADR-256 D2)
# ---------------------------------------------------------------------------

def _build_user_message(
    trigger: str,
    ctx: "ReviewerContext",
) -> str:
    """Assemble the user-message envelope. Load order: persona → framework
    → mandate/autonomy → domain substrate → trigger-specific context."""
    import json as _json
    parts: list[str] = []

    # --- Persona (always first — who you are before you see anything else) ---
    parts += [
        "## IDENTITY.md — Your persona",
        "",
        ctx.get("identity_md") or "_(empty — reason as neutral skeptical judgment seat)_",
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
            "## PRECEDENT.md — Operator-declared durable interpretations (overrides principles)",
            "",
            ctx["precedent_md"],
            "",
        ]

    if ctx.get("mandate_md"):
        parts += [
            "## MANDATE.md — Operation's primary intent",
            "",
            ctx["mandate_md"],
            "",
        ]

    if ctx.get("autonomy_md"):
        parts += [
            "## AUTONOMY.md — Delegation ceiling",
            "",
            ctx["autonomy_md"],
            "",
        ]

    # --- Domain substrate ---
    if ctx.get("operator_profile_md"):
        parts += ["## _operator_profile.md — Declared strategy", "", ctx["operator_profile_md"], ""]
    if ctx.get("risk_md"):
        parts += ["## _risk.md — Hard floors", "", ctx["risk_md"], ""]
    if ctx.get("performance_md"):
        parts += ["## _performance.md — Track record", "", ctx["performance_md"], ""]

    # --- Trigger-specific context ---
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
        parts += [
            "## Your task",
            "Evaluate this proposal. Apply your framework. Call ReturnVerdict with "
            "approve / reject / defer + reasoning. Use ReadFile to fetch missing substrate "
            "before deciding if needed.",
        ]

    elif trigger == "heartbeat":
        slug = ctx.get("trigger_slug", "unknown")
        parts += [f"## Trigger: `{slug}` just completed", ""]
        if ctx.get("signal_files"):
            parts += ["## Fresh signal state", "", ctx["signal_files"], ""]
        if ctx.get("workspace_state"):
            parts += ["## Workspace state (what the system has done)", "", ctx["workspace_state"], ""]
        parts += [
            "## Your task",
            f"`{slug}` just completed. Read the fresh signal output above. Apply your "
            "principles. Decide: ProposeAction if conditions are met, FireInvocation if "
            "substrate is missing, or ReturnVerdict(stand_down) if no actionable condition exists.",
        ]

    elif trigger == "reflection":
        if ctx.get("recent_decisions_md"):
            parts += ["## Recent decisions (your verdict trail)", "", ctx["recent_decisions_md"], ""]
        parts += [
            "## Your task",
            "Reflect on your recent decisions against your framework. `no_change` is the "
            "expected and common outcome. If you notice patterns warranting adjustment, "
            "include proposals with full revised file content. Call ReturnVerdict with "
            "no_change | narrow | relax | character_note | pause_autonomy.",
        ]

    elif trigger == "addressed":
        if ctx.get("workspace_state"):
            parts += [
                "## Workspace state (what the system has done recently)",
                "(Signal runs, positions, cadence, pending proposals)",
                "",
                ctx["workspace_state"],
                "",
            ]
        if ctx.get("conversation_window"):
            parts += ["## Recent conversation", "", ctx["conversation_window"], ""]
        msg = ctx.get("user_message", "")
        parts += [
            "## Operator message",
            "",
            msg.strip(),
            "",
            "## Your task",
            "Read the workspace state. Know what's been done and what's pending. "
            "Apply your framework. If signal data is missing and the operator wants "
            "action, call FireInvocation to commission it — do not ask the operator to do it. "
            "If conditions are met, call ProposeAction. If purely informational, "
            "call ReturnVerdict(stand_down) with your answer as the reasoning.",
        ]

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Tool call dispatcher — executes tool calls made during the loop
# ---------------------------------------------------------------------------

async def _dispatch_tool_call(
    client: Any,
    user_id: str,
    tool_name: str,
    tool_input: dict,
) -> tuple[str, dict]:
    """Execute a Reviewer tool call. Returns (result_text, action_record)."""
    import json as _json

    if tool_name == "ReadFile":
        path = tool_input.get("path", "")
        if not path.startswith("/workspace/"):
            return "Error: path must start with /workspace/", {}
        try:
            res = (
                client.table("workspace_files")
                .select("content")
                .eq("user_id", user_id)
                .eq("path", path)
                .limit(1)
                .execute()
            )
            content = (res.data or [{}])[0].get("content") or ""
            if not content:
                return f"_(file not found or empty: {path})_", {}
            return content[:4000], {"tool": "ReadFile", "path": path}
        except Exception as e:
            return f"Error reading {path}: {e}", {}

    elif tool_name == "FireInvocation":
        slug = tool_input.get("slug", "")
        reason = tool_input.get("reason", "")
        try:
            from services.recurrence import walk_workspace_recurrences
            import asyncio
            decls = await asyncio.to_thread(walk_workspace_recurrences, client, user_id)
            matched = next((d for d in decls if d.slug == slug), None)
            if not matched:
                matched = next((d for d in decls if d.slug.startswith(slug)), None)
            if not matched:
                return f"No recurrence found for slug '{slug}'", {}
            from types import SimpleNamespace
            auth = SimpleNamespace(client=client, user_id=user_id)
            from services.primitives.fire_invocation import handle_fire_invocation
            inp = {"shape": matched.shape.value, "slug": matched.slug}
            if matched.domain:
                inp["domain"] = matched.domain
            result = await handle_fire_invocation(auth, inp)
            return f"Fired `{matched.slug}`: {result.get('message', 'dispatched')}", {
                "tool": "FireInvocation", "slug": matched.slug, "reason": reason,
            }
        except Exception as e:
            return f"FireInvocation failed for '{slug}': {e}", {}

    elif tool_name == "ProposeAction":
        action_type = tool_input.get("action_type", "")
        rationale = tool_input.get("rationale", "")
        inputs = {k: v for k, v in tool_input.items()
                  if k not in ("action_type", "rationale")}
        try:
            from types import SimpleNamespace
            auth = SimpleNamespace(client=client, user_id=user_id)
            from services.primitives.propose_action import handle_propose_action
            result = await handle_propose_action(auth, {
                "action_type": action_type,
                "inputs": inputs,
                "rationale": rationale,
                "source": "reviewer_loop",
            })
            proposal_id = result.get("proposal_id", "")
            return (
                f"Proposal submitted: `{action_type}` "
                + (f"(ID: {proposal_id[:8]})" if proposal_id else ""),
                {"tool": "ProposeAction", "action_type": action_type, "proposal_id": proposal_id},
            )
        except Exception as e:
            return f"ProposeAction failed for '{action_type}': {e}", {}

    elif tool_name == "WriteFile":
        path = tool_input.get("path", "")
        content = tool_input.get("content", "")
        mode = tool_input.get("mode", "append")
        if not path.startswith("/workspace/review/"):
            return "Error: WriteFile scope ceiling is /workspace/review/", {}
        try:
            from services.authored_substrate import write_revision
            full_path = path if path.startswith("/workspace/") else f"/workspace/{path}"
            write_revision(
                client, user_id,
                path=full_path,
                content=content,
                authored_by=f"reviewer:{REVIEWER_MODEL_IDENTITY}",
                message="Reviewer loop write",
                mode=mode,
            )
            return f"Written: {path}", {"tool": "WriteFile", "path": path}
        except Exception as e:
            return f"WriteFile failed for '{path}': {e}", {}

    return f"Unknown tool: {tool_name}", {}


# ---------------------------------------------------------------------------
# Public entry point — ADR-256 D1
# ---------------------------------------------------------------------------

async def invoke_reviewer(
    client: Any,
    user_id: str,
    *,
    trigger: Literal["proposal", "reflection", "heartbeat", "addressed"],
    context: "ReviewerContext",
) -> "ReviewerOutput | None":
    """Unified Reviewer invocation — ADR-256.

    One function, four trigger shapes. Bounded tool-use loop (≤3 rounds).
    The Reviewer reads what it needs, acts on what it decides, calls
    ReturnVerdict to close the loop.

    Model selection:
    - Sonnet (capital decisions): proposal + heartbeat
    - Haiku  (reasoning):         reflection + addressed

    Never raises. Returns None on total failure (callers treat as
    observe-only / no-change / stand-down depending on trigger).
    """
    model = _SONNET if trigger in ("proposal", "heartbeat") else _HAIKU
    caller = _CALLER_SONNET if trigger in ("proposal", "heartbeat") else _CALLER_HAIKU

    try:
        user_message = _build_user_message(trigger, context)

        messages: list[dict] = [{"role": "user", "content": user_message}]
        actions_taken: list[dict] = []
        verdict_raw: dict | None = None

        max_rounds = 3
        total_input = 0
        total_output = 0

        for _round in range(max_rounds):
            response = await chat_completion_with_tools(
                messages=messages,
                system=_SYSTEM_PROMPT,
                tools=_TOOLS,
                model=model,
                max_tokens=2048,
            )

            usage = getattr(response, "usage", None) or {}
            total_input += int(getattr(usage, "input_tokens", 0) or 0)
            total_output += int(getattr(usage, "output_tokens", 0) or 0)

            tool_uses = getattr(response, "tool_uses", None) or []
            stop_reason = getattr(response, "stop_reason", None)

            # Collect assistant turn for multi-round history
            assistant_content: list[dict] = []
            text_content = getattr(response, "content", None)
            if isinstance(text_content, list):
                for block in text_content:
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
                # No tool calls — model gave up or returned text only; treat as failure
                logger.warning(
                    "[REVIEWER] no tool calls in round %d trigger=%s user=%s stop=%s",
                    _round, trigger, user_id[:8], stop_reason,
                )
                break

            tool_results: list[dict] = []
            for tu in tool_uses:
                name = getattr(tu, "name", None) or (tu.get("name") if isinstance(tu, dict) else None)
                inp = getattr(tu, "input", None) or (tu.get("input") if isinstance(tu, dict) else {}) or {}
                tu_id = getattr(tu, "id", None) or (tu.get("id") if isinstance(tu, dict) else "") or ""

                if name == "ReturnVerdict":
                    verdict_raw = inp
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tu_id,
                        "content": "Verdict recorded.",
                    })
                    break  # verdict closes the loop

                # Execute the tool call
                result_text, action_record = await _dispatch_tool_call(
                    client, user_id, name, inp,
                )
                if action_record:
                    actions_taken.append(action_record)
                logger.info(
                    "[REVIEWER] tool=%s trigger=%s user=%s result=%.80r",
                    name, trigger, user_id[:8], result_text,
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu_id,
                    "content": result_text,
                })

            if verdict_raw is not None:
                break  # ReturnVerdict found — exit loop

            # Continue loop with tool results
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

        # Record token usage (combined across all rounds)
        record_token_usage(
            client,
            user_id=user_id,
            caller=caller,
            model=model,
            input_tokens=total_input,
            output_tokens=total_output,
            ref_id=context.get("proposal_row", {}).get("id") if trigger == "proposal" else None,
            metadata={"trigger": trigger, "rounds": _round + 1},
        )

        if verdict_raw is None:
            logger.warning(
                "[REVIEWER] no ReturnVerdict after %d rounds trigger=%s user=%s",
                max_rounds, trigger, user_id[:8],
            )
            return None

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
                "[REVIEWER] invalid verdict=%r trigger=%s user=%s — treating as defer/no_change",
                verdict, trigger, user_id[:8],
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

        # Reflection-only fields
        if trigger == "reflection":
            proposals_raw = verdict_raw.get("proposals") or []
            # Normalize — same shape reflection_writer expects
            from agents.reviewer_agent_compat import _normalize_reflection_proposals
            output["proposals"] = _normalize_reflection_proposals(proposals_raw)
            output["evidence_summary"] = (verdict_raw.get("evidence_summary") or "").strip()

        return output

    except Exception as exc:
        logger.error(
            "[REVIEWER] invoke_reviewer failed trigger=%s user=%s: %s",
            trigger, user_id[:8] if user_id else "?", exc,
        )
        return None


# ---------------------------------------------------------------------------
# Signal file reader — used by heartbeat context loader in callers
# ---------------------------------------------------------------------------

async def read_signal_files(client: Any, user_id: str) -> str:
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
