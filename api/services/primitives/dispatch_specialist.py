"""
DispatchSpecialist Primitive — ADR-261 D7.

The Reviewer's chat-mode loop calls this primitive to dispatch a
focused-prompt specialist sub-LLM-call. The deterministic System Agent
(per ADR-257) is the boundary between Reviewer judgment and specialist
production: it composes the specialist's prompt from
(role-default-instructions + Reviewer-supplied brief + relevant
substrate refs), runs the headless LLM call, and returns the
specialist's markdown output to the Reviewer.

Per ADR-261 D7:
  - Specialist execution is identical in shape to Claude Code sub-agents.
  - Specialists run with their own context window — focused prompt =
    no prompt-pressure dilution.
  - The Reviewer's context window is not polluted with specialist tool-
    use loops; the Reviewer sees only the specialist's final output.
  - `headless` permission mode (per ADR-080) survives as the LLM-runtime
    characteristic: non-streaming, curated tool surface, no operator-
    presence assumption.

Available in the Reviewer's chat-mode loop only — not exposed to
operator chat (operators don't dispatch specialists directly; they ask
the Reviewer, which then dispatches). Headless mode also has it for
multi-step recurrence prompts that orchestrate specialists internally.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Sonnet for specialist work — focused-prompt sub-calls warrant the model
# strength for genuine production work. Operators can override via the
# `model` option if cost discipline is paramount.
_SPECIALIST_MODEL_DEFAULT = "claude-sonnet-4-6"
_SPECIALIST_MAX_TOKENS = 4096
_SPECIALIST_MAX_ROUNDS = 5  # specialist sub-calls are bounded; ADR-260 D8 round discipline


# ADR-272: VALID_SPECIALIST_ROLES narrowed to a single role — `designer`.
# ADR-417: the designer's asset-generation half (RuntimeDispatch → the render
# service) is retired — generation is rented, not owned. The role survives as
# a compose-only shell (read substrate, compose HTML). DispatchSpecialist is
# therefore now near-inert; collapsing or removing it is a NAMED FOLLOW-ON
# (the specialist-dispatch architecture cleanup), deliberately out of ADR-417's
# subtractive scope so the three-actor execution model is revisited on its own.
VALID_SPECIALIST_ROLES = {
    "designer",
}


DISPATCH_SPECIALIST_TOOL = {
    "name": "DispatchSpecialist",
    "description": """Dispatch a focused-prompt specialist sub-LLM-call (ADR-261 D7, narrowed by ADR-272).

Escape hatch for production-shape work that genuinely needs a different
tool surface, larger output budget, and longer latency tolerance than
your own judgment loop.

DEFAULT POSTURE: do production work inline. Read substrate, compute,
write. Specialists are NOT a delegation pattern for "this would be nicer
in a specialist"; they exist for work that fails inline-execution on
structural grounds.

One specialist role (post ADR-272 Specialist Survival Test):
  - designer: composes substrate into HTML for in-workspace consumption.
    (ADR-417: the asset-generation half — charts/mermaid/images/video via
    the in-house render service — is retired. Generation is rented, not
    owned; yarnnn hosts no generation engine.)

Dissolved roles (do not call — Reviewer does this inline):
  - researcher, analyst, writer, tracker, reporting → all dissolved.
    These were judgment-adjacent activities expressed as production
    roles; the Reviewer does investigation, analysis, prose drafting,
    accumulation, and cross-domain synthesis using its own tool surface.

The brief tells the designer what to compose, what substrate to read
inputs from, and where to write the output (slug-templated paths per
CONVENTIONS topology). The designer returns markdown summarizing the
composed output.

Examples:
  DispatchSpecialist(role="designer",
    brief="Compose a weekly performance HTML section from
           /workspace/operation/portfolio/_money_truth.md — render the
           equity series as a native HTML table with a one-line summary.
           Output target: /workspace/operation/reports/
           weekly-performance-review/{date}/sections/equity.md")""",
    "input_schema": {
        "type": "object",
        "properties": {
            "role": {
                "type": "string",
                "enum": sorted(VALID_SPECIALIST_ROLES),
                "description": "Specialist role to dispatch.",
            },
            "brief": {
                "type": "string",
                "description": (
                    "Focused brief: what to produce, where to read from, "
                    "where to write to. The Reviewer's standing context "
                    "is NOT injected — the brief carries everything the "
                    "specialist needs to know."
                ),
            },
            "model": {
                "type": "string",
                "description": (
                    "Optional model override (defaults to Sonnet). Use "
                    "'claude-haiku-4-5-20251001' for cost-discipline on "
                    "format-shaped work."
                ),
            },
            "required_capabilities": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Capabilities the specialist needs to do this brief "
                    "(ADR-269 capability flow). The specialist's tool "
                    "surface is the union of the role's universal "
                    "capabilities + these. When dispatched for a "
                    "recurrence that declares required_capabilities, "
                    "pass those through at minimum — they're surfaced "
                    "in your context envelope as "
                    "`recurrence_required_capabilities`. You may extend "
                    "the list per dispatch (e.g., add `web_search` if "
                    "the brief needs web research on top of the "
                    "recurrence's declared trading capabilities)."
                ),
            },
        },
        "required": ["role", "brief"],
    },
}


async def handle_dispatch_specialist(auth: Any, input: dict) -> dict:
    """Execute one DispatchSpecialist call.

    Returns:
        {
          "success": True/False,
          "role": "<role>",
          "output_markdown": "<specialist's final output>",
          "rounds_used": <int>,
          "tokens_in": <int>,
          "tokens_out": <int>,
          "tools_called": [<tool_name>, ...],
          "error": "..." (only on failure),
        }
    """
    user_id = getattr(auth, "user_id", None)
    db_client = getattr(auth, "client", None)
    if not user_id:
        return {"success": False, "error": "auth_required", "message": "user_id required"}

    input = input or {}
    role = input.get("role") or ""
    brief = input.get("brief") or ""
    model = input.get("model")
    # ADR-269: capability flow — Reviewer passes (or extends) the
    # recurrence's declared required_capabilities here. Empty/missing →
    # specialist gets only the role's universal capabilities.
    rc_raw = input.get("required_capabilities") or []
    if not isinstance(rc_raw, list):
        rc_raw = []
    task_required_capabilities = [
        str(c).strip() for c in rc_raw
        if c and isinstance(c, str) and str(c).strip()
    ]

    if role not in VALID_SPECIALIST_ROLES:
        return {
            "success": False,
            "error": "invalid_role",
            "message": (
                f"role must be one of {sorted(VALID_SPECIALIST_ROLES)}; "
                f"got {role!r}"
            ),
        }
    if not brief or not isinstance(brief, str) or not brief.strip():
        return {
            "success": False,
            "error": "missing_brief",
            "message": "brief is required and must be non-empty",
        }

    # Resolve role-specific defaults from ALL_ROLES (union of SYSTEMIC_AGENTS
    # + PRODUCTION_ROLES). AGENT_TEMPLATES + AGENT_TYPES aliases were deleted
    # pre-Commit B per orchestration.py:44; this call site was missed in that
    # cleanup. Surfaced by iter-5 (2026-05-13): every DispatchSpecialist
    # invocation raised ImportError("cannot import name 'AGENT_TEMPLATES'"),
    # which dispatch_specialist's try/except caught as tool_resolution_failed
    # but only after the import, so the cleaner "specialist never launched"
    # was actually hiding "import error caught by outer try/except." Same
    # shape (display_name / tagline / default_instructions) so behavior
    # identical after rename.
    from services.orchestration import ALL_ROLES
    template = ALL_ROLES.get(role) or {}
    display_name = template.get("display_name", role.title())
    tagline = template.get("tagline", "")
    default_instructions = template.get("default_instructions", "")

    # Compose the focused prompt. Returns cache-marked content blocks so
    # rounds 2..N read the system frame from Anthropic's prompt cache
    # rather than re-billing it. See _compose_specialist_system_prompt
    # docstring for the ADR-171/172 economics.
    system_prompt = _compose_specialist_system_prompt(
        role=role,
        display_name=display_name,
        tagline=tagline,
        default_instructions=default_instructions,
    )

    # Resolve headless tool surface for this specialist role.
    # ADR-268 / iter-2 observation 2026-05-13: prior call signature passed
    # `agent_role=role` which is not a parameter of get_headless_tools_for_agent;
    # the resulting TypeError was caught silently here, returning
    # tool_resolution_failed on every dispatch since PR #9 (2026-05-10).
    # Fixed: pass `agent={"role": role}` matching the function's actual
    # signature. Note: even with this fix, platform_trading_* tools do NOT
    # flow to the specialist because (a) the universal specialist roles
    # (researcher/analyst/tracker/etc. per ADR-176) don't declare
    # `read_trading` in their role-level capability list, AND (b) the
    # `task_required_capabilities` parameter is not yet wired through from
    # the recurrence YAML's `required_capabilities:` block. That's L3 from
    # iter-2 (full capability-flow wiring) — deferred to a follow-up iter
    # with its own ADR pass. L2 (this fix) unblocks specialist *launch*;
    # L3 unblocks specialist *tool surface*.
    from services.primitives.registry import (
        create_headless_executor,
        get_headless_tools_for_agent,
    )
    try:
        # ADR-269: task_required_capabilities threaded through so the
        # specialist's tool surface includes program-specific capabilities
        # declared by the recurrence + (optionally) extended by the Reviewer.
        tools = await get_headless_tools_for_agent(
            db_client, user_id,
            agent={"role": role},
            task_required_capabilities=task_required_capabilities,
        )
    except Exception as e:
        logger.warning(
            "[DISPATCH_SPECIALIST] tool resolution failed for role=%s: %s",
            role, e,
        )
        return {
            "success": False,
            "error": "tool_resolution_failed",
            "message": str(e),
        }

    # ADR-268 / iter-2 follow-on: same kwarg-mismatch class as the
    # get_headless_tools_for_agent call above. create_headless_executor's
    # first positional is `client`, not `db_client`. Previously this would
    # have raised TypeError but execution never reached here (the prior
    # call already failed). Fixing concurrently so the dispatch path is
    # actually exercise-able post-deploy.
    executor = create_headless_executor(
        client=db_client,
        user_id=user_id,
        agent={"role": role},
        dynamic_tools=tools,
    )

    # Headless tool-use loop, bounded. The round ceiling is per-recurrence
    # tunable: the operator declares `options.max_rounds: N` on the
    # recurrence YAML, the dispatcher copies `options` into the Reviewer's
    # auth.recurrence_options namespace (freddie_agent.py), and we read
    # it here. Empty / missing → fall back to the global default. This
    # exists because the global default (5) is correctly sized for
    # single-output recurrences (e.g. track-regime) but undersized for
    # multi-output bundles (e.g. 5-ticker track-universe needs ~10-12;
    # 5-signal × 5-ticker falsify-signals needs ~15-20). Per ADR-176 /
    # ADR-216, work-shape is bundle-shaped not kernel-shaped, so the
    # kernel exposes the knob and the bundle declares its budget.
    from services.anthropic import chat_completion_with_tools
    rec_options = getattr(auth, "recurrence_options", None) or {}
    max_rounds_raw = rec_options.get("max_rounds")
    try:
        max_rounds = (
            int(max_rounds_raw)
            if max_rounds_raw is not None and int(max_rounds_raw) > 0
            else _SPECIALIST_MAX_ROUNDS
        )
    except (TypeError, ValueError):
        logger.warning(
            "[DISPATCH_SPECIALIST] invalid max_rounds=%r in recurrence options — "
            "falling back to global default %d",
            max_rounds_raw, _SPECIALIST_MAX_ROUNDS,
        )
        max_rounds = _SPECIALIST_MAX_ROUNDS
    chosen_model = model or _SPECIALIST_MODEL_DEFAULT
    messages: list[dict] = [{"role": "user", "content": brief}]
    tools_called: list[str] = []
    total_in = 0
    total_out = 0
    final_text = ""
    rounds = 0

    for round_idx in range(max_rounds):
        rounds = round_idx + 1
        try:
            response = await chat_completion_with_tools(
                messages=messages,
                system=system_prompt,
                tools=tools,
                model=chosen_model,
                max_tokens=_SPECIALIST_MAX_TOKENS,
            )
        except Exception as e:
            logger.exception(
                "[DISPATCH_SPECIALIST] LLM call failed role=%s round=%d: %s",
                role, rounds, e,
            )
            return {
                "success": False,
                "error": "llm_call_failed",
                "message": str(e),
                "role": role,
                "rounds_used": rounds,
            }

        usage = getattr(response, "usage", None) or {}
        if isinstance(usage, dict):
            total_in += int(usage.get("input_tokens", 0) or 0)
            total_out += int(usage.get("output_tokens", 0) or 0)

        # ADR-291: unified cost ledger — write directly to execution_events.
        try:
            from services.telemetry import record_execution_event
            from services.supabase import get_service_client
            _in = int(usage.get("input_tokens", 0) or 0) if isinstance(usage, dict) else 0
            _out = int(usage.get("output_tokens", 0) or 0) if isinstance(usage, dict) else 0
            _cache_read = int(usage.get("cache_read_input_tokens", 0) or 0) if isinstance(usage, dict) else 0
            _cache_create = int(usage.get("cache_creation_input_tokens", 0) or 0) if isinstance(usage, dict) else 0
            record_execution_event(
                get_service_client(),
                user_id=user_id,
                slug=f"specialist:{role}",
                mode="judgment",
                trigger_type="reactive",
                status="success",
                tool_rounds=rounds,
                input_tokens=_in,
                output_tokens=_out,
                cache_read_tokens=_cache_read,
                cache_create_tokens=_cache_create,
                model=chosen_model,
            )
        except Exception as _e:
            logger.warning(
                "[DISPATCH_SPECIALIST] cost ledger record failed: %s", _e
            )

        # Append assistant turn — reconstruct dict-shaped content from the
        # SDK content blocks in response.content. Mirrors the canonical
        # pattern in api/agents/freddie_agent.py (same problem: round-trip
        # tool_use blocks back to the Anthropic API for the next turn).
        # The earlier shape `response.tool_uses_raw` referenced a field
        # that never existed on ChatResponse — Python raised AttributeError
        # before the `or` fallback could evaluate. This is the fix path.
        if response.tool_uses:
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
            messages.append({
                "role": "assistant",
                "content": assistant_content,
            })
        else:
            final_text = (response.text or "").strip()
            messages.append({"role": "assistant", "content": final_text})

        if response.stop_reason != "tool_use" or not response.tool_uses:
            # Specialist returned text — terminal
            break

        # Execute tools, append results.
        # `response.tool_uses` is `list[ToolUseBlock]` per anthropic.py
        # _parse_response: ToolUseBlock is a @dataclass with `.id`, `.name`,
        # `.input` attributes — NOT a dict. The earlier `.get()` access
        # raised `'ToolUseBlock' has no 'get' attribute` and blocked every
        # specialist's tool-execution turn. Same canonical pattern as
        # freddie_agent.py: attribute access against the typed dataclass.
        tool_results: list[dict] = []
        for tu in response.tool_uses:
            tool_name = tu.name or ""
            tool_input = tu.input or {}
            tool_use_id = tu.id or ""
            tools_called.append(tool_name)
            try:
                result = await executor(tool_name, tool_input)
            except Exception as e:
                result = {"success": False, "error": "tool_raised", "message": str(e)}
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": _stringify_tool_result(result),
            })
        messages.append({"role": "user", "content": tool_results})
    else:
        logger.warning(
            "[DISPATCH_SPECIALIST] role=%s exhausted %d rounds without terminal text",
            role, max_rounds,
        )
        # Use the last assistant text we have, even if empty
        final_text = final_text or (
            f"[specialist {role} exhausted round budget without final output]"
        )

    logger.info(
        "[DISPATCH_SPECIALIST] role=%s rounds=%d tokens=%d/%d tools=%d",
        role, rounds, total_in, total_out, len(tools_called),
    )

    return {
        "success": True,
        "role": role,
        "output_markdown": final_text,
        "rounds_used": rounds,
        "tokens_in": total_in,
        "tokens_out": total_out,
        "tools_called": tools_called,
    }


# ---------------------------------------------------------------------------
# Prompt composition
# ---------------------------------------------------------------------------


_SPECIALIST_FRAME = """You are a {display_name} specialist dispatched by the Reviewer.

{tagline}

You have a focused brief from the Reviewer (in the user message). Your job is
to execute that brief and return a short markdown summary of what you
produced. The Reviewer reads your summary and decides what to do next — they
do NOT see your tool-use loop.

## Role-specific guidance
{default_instructions}

## Headless execution conventions

- Read substrate via ReadFile / SearchFiles / ListFiles / LookupEntity. The
  brief tells you where to look.
- Write substrate via WriteFile. The brief tells you where to write. Use
  the slug-templated paths from CONVENTIONS topology — never invent paths.
- When the brief asks for a deliverable section, write it to the dated
  sections folder (`/workspace/operation/reports/{{slug}}/{{date}}/sections/{{name}}.md`)
  so the auto-compose hook picks it up at session-close.
- When the brief asks for accumulation work, write entity files to
  `/workspace/operation/{{domain}}/{{entity}}.{{md|yaml}}` per the convention.
- Stand down quietly if the brief is impossible (missing inputs, platform
  unreachable, etc.). Return a short markdown summary explaining what was
  blocked.

## Final output

Your final assistant message (without tool calls) is your terminal return.
It should be a brief markdown summary the Reviewer can read in seconds:
- What you produced
- Where you wrote it (paths)
- Anything the Reviewer should know before next steps

Do NOT echo the full content you wrote — the Reviewer will read it from
substrate if needed. Keep the summary short."""


def _compose_specialist_system_prompt(
    *,
    role: str,
    display_name: str,
    tagline: str,
    default_instructions: str,
) -> list[dict]:
    """Compose the specialist system prompt as cache-marked content blocks.

    Returns a single text block with `cache_control: {"type": "ephemeral"}`.
    The frame + role defaults are static across every round of one
    specialist invocation, so caching them avoids re-billing the system
    prompt on rounds 2..N. ADR-171 §"Cache discount: not passed through"
    + ADR-172 budget gate both assume caching is firing — the user-facing
    2× markup is computed against full input rate, cache discount accrues
    as platform margin. Without cache markers here, the markup compresses
    rapidly on multi-round specialist work.
    """
    body = _SPECIALIST_FRAME.format(
        display_name=display_name,
        tagline=tagline or "Universal contributor.",
        default_instructions=(
            default_instructions
            or "Apply your role's standard methodology to the brief."
        ),
    )
    return [
        {
            "type": "text",
            "text": body,
            "cache_control": {"type": "ephemeral"},
        }
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stringify_tool_result(result: Any) -> str:
    """Coerce a tool result to a string for the next user message."""
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        import json
        try:
            return json.dumps(result, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(result)
    return str(result)


__all__ = [
    "DISPATCH_SPECIALIST_TOOL",
    "handle_dispatch_specialist",
    "VALID_SPECIALIST_ROLES",
]
