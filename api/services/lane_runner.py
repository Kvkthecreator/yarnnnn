"""Lane runner — ADR-411 (implements ADR-408 D6 chat lanes).

A lane is a member's model-pinned helper thread: an isolated conversation
whose model works the SHARED workspace through the file-verb tool surface.
The contract (ADR-408 D6): lanes are isolated conversations; the workspace
is the shared memory — a lane's model never reads another lane's (or the
steward's) transcript; it reads what others wrote to the commons, with
attribution.

This module owns:
- ``LANE_MODELS`` — the creation-time model whitelist (ADR-411 D5: a model
  enters only WITH a ``_BILLING_RATES`` row; no silent default pricing).
- The lane tool surface (ADR-411 D3): the five file verbs, converted
  mechanically from the registry's Anthropic-format definitions to the
  OpenAI format LiteLLM translates per provider. Executed through
  ``execute_primitive`` under the member's auth with the member-embodiment
  attribution (``member:{user_id} via {model}`` — ADR-411 D4), so grants,
  gates, revision attribution, and the timeline apply for free.
- The conventions projection (ADR-411 D6): an AGENTS.md-shaped system
  prompt composed at turn time from kernel constants + the workspace's
  MANDATE head — derived, never stored.
- ``run_lane_turn`` — the bounded non-streaming tool loop over
  ``route_completion`` (ADR-408 D4 router). Every round records into
  ``execution_events`` (slug ``lane``, the member as principal) — the one
  meter (ADR-396).

Altitude discipline: this is Altitude-2 machinery (ADR-408 D2). The
steward's loop (freddie_agent) never touches it; lanes never touch the
steward's wake drain.
"""

from __future__ import annotations

import dataclasses
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lane model registry (ADR-411 D5)
# ---------------------------------------------------------------------------

#: Models a lane may pin. Keys are LiteLLM provider/model strings; every
#: entry's ledger_model MUST have a telemetry _BILLING_RATES row (gate-
#: tested) — the D4 spike's rule: an unpriced model never routes in prod.
#: This is DATA (ADR-402 pattern): adding a provider = a row here + a rate
#: row + the provider key in env.
LANE_MODELS: dict[str, dict[str, str]] = {
    "anthropic/claude-sonnet-4-6": {"label": "Claude Sonnet"},
    "anthropic/claude-haiku-4-5-20251001": {"label": "Claude Haiku"},
    "openai/gpt-4o-mini": {"label": "GPT-4o mini"},
    # ADR-420 §10 seed set — "provide enough, not the most" (one lane per
    # reason a user would leave, not one per model that exists). Each row
    # is DATA: a _BILLING_RATES row (telemetry.py) + the provider key in env
    # (GEMINI_API_KEY / OPENAI_API_KEY / DEEPSEEK_API_KEY on API + Scheduler)
    # is all it costs. Lit dark until the key lands; MODEL_ROUTER_ENABLED gates.
    "openai/gpt-5": {"label": "GPT-5"},                        # frontier OpenAI (completes mini→frontier)
    "gemini/gemini-2.5-flash": {"label": "Gemini Flash"},      # the Google lane (fast/cheap)
    "gemini/gemini-2.5-pro": {"label": "Gemini Pro"},          # frontier Google reasoning
    "deepseek/deepseek-chat": {"label": "DeepSeek"},           # cost-floor / sovereign lane (compat alias → V4 Flash)
}

_LANE_MAX_ROUNDS = 8       # cost ceiling, not behavior (ADR-402 posture)
_LANE_MAX_TOKENS = 2048
_LANE_TIMEOUT_S = 120.0


def _studio_max_tokens() -> int:
    """ADR-440 D3 — the authoring token profile for BOUND (Studio) lanes."""
    from services.studio import STUDIO_LANE_MAX_TOKENS
    return STUDIO_LANE_MAX_TOKENS

# ---------------------------------------------------------------------------
# Tool surface (ADR-411 D3) — five file verbs, registry definitions converted
# ---------------------------------------------------------------------------

#: The lane tool allowlist. A helper is hands on the filesystem — no entity
#: verbs, no Schedule, no DispatchSpecialist, no platform tools.
LANE_TOOL_NAMES = ("ReadFile", "WriteFile", "EditFile", "SearchFiles", "ListFiles")

#: The subset of the lane surface that PRODUCES substrate. A successful call
#: to one of these lands an attributed revision, and the member should SEE what
#: their lane made — not just the verb's name (2026-07-09, the artifact card).
#: ReadFile/SearchFiles/ListFiles also return a `path`, which is why the gate
#: is on the verb and not merely on the result's shape.
LANE_ARTIFACT_VERBS = ("WriteFile", "EditFile")


def artifact_path_from(name: str, result: Any) -> Optional[str]:
    """The workspace path a lane tool call produced, or None.

    Pure. The path is read from the primitive's RESULT, never from the model's
    arguments: `handle_write_file` normalizes (`/workspace/…` and `workspace/…`
    prefixes are stripped, then re-absolutized), so the result carries the one
    canonical form the Files surface deep-links on. A failed write yields None —
    the member sees the tool row, never a card for a file that isn't there.
    """
    if name not in LANE_ARTIFACT_VERBS:
        return None
    if not isinstance(result, dict) or not result.get("success"):
        return None
    path = result.get("path")
    return path if isinstance(path, str) and path else None


def _resolve_byok_key(auth: Any, model: str) -> Optional[str]:
    """ADR-439 — the workspace's own provider key for this model, or None.

    None means the managed default (our platform keys, metered normally) — the
    byte-identical path for every non-BYOK workspace. Total + fail-safe: a resolver
    error must never break a member's turn (it falls back to managed). Resolved once
    per turn by the lane loop, threaded into every router call as `api_key`."""
    try:
        from services.byok import get_byok_key, provider_from_model
        workspace_id = getattr(auth, "workspace_id", None)
        return get_byok_key(auth.client, workspace_id, provider_from_model(model))
    except Exception as exc:  # pragma: no cover — defensive, never break a turn
        logger.warning("[LANE] BYOK resolve failed (falling back to managed): %s", exc)
        return None


def unpriced_lane_model(model: str) -> bool:
    """ADR-439 §4 (F1) — True if this lane model has NO `_BILLING_RATES` row.

    The D4-spike rule promoted from convention to ENFORCEMENT: an unpriced model
    would silently price at the Sonnet `_DEFAULT_RATE`, mis-metering the pool. This
    is the PRE-CALL check the lane loops gate on, so an unpriced model is refused
    BEFORE any (billable) API call — not warned about after. `LANE_MODELS` and
    `_BILLING_RATES` are kept in sync + gate-tested, so in practice this never trips
    in prod; it is the hard floor that makes the guarantee enforced, not incidental."""
    from services.model_router import ledger_model_name
    from services.telemetry import has_billing_rate
    return not has_billing_rate(ledger_model_name(model))


_UNPRICED_MODEL_ERROR = {
    "error": "model_unpriced",
    "message": "this model has no billing rate configured and cannot run (ADR-439 §4)",
}


def _anthropic_to_openai_tool(tool: dict) -> dict:
    """Mechanical format conversion — the registry's Anthropic-shape tool
    definition becomes the OpenAI function-tool shape LiteLLM expects."""
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": tool.get("input_schema", {"type": "object"}),
        },
    }


def lane_tools_openai() -> list[dict]:
    """The lane tool surface in OpenAI format, derived from the registry's
    own definitions (no parallel schemas — Singular Implementation)."""
    from services.primitives.workspace import (
        EDIT_FILE_TOOL,
        LIST_FILES_TOOL,
        READ_FILE_TOOL,
        SEARCH_FILES_TOOL,
        WRITE_FILE_TOOL,
    )

    by_name = {
        t["name"]: t
        for t in (READ_FILE_TOOL, WRITE_FILE_TOOL, EDIT_FILE_TOOL,
                  SEARCH_FILES_TOOL, LIST_FILES_TOOL)
    }
    return [_anthropic_to_openai_tool(by_name[n]) for n in LANE_TOOL_NAMES]


# ---------------------------------------------------------------------------
# Attribution (ADR-411 D4)
# ---------------------------------------------------------------------------

def lane_caller_identity(user_id: str, model: str) -> str:
    """The member-embodiment attribution string (ADR-408 D2 ratified shape).
    ``member:`` is a VALID_AUTHOR_PREFIXES entry; ``_caller_class`` maps it
    to the operator class so the member's own grant is the boundary."""
    return f"member:{user_id} via {model}"


def _lane_auth(auth: Any, model: str) -> Any:
    """The member's auth with the embodiment attribution stamped. Grants
    resolve by principal_id (unchanged — the member), so a lane write the
    member could not make is denied, and one they could binds immediately."""
    try:
        return dataclasses.replace(
            auth, caller_identity=lane_caller_identity(auth.user_id, model)
        )
    except TypeError:
        # Non-dataclass auth namespaces (tests): shallow attribute copy.
        import types
        clone = types.SimpleNamespace(**vars(auth))
        clone.caller_identity = lane_caller_identity(auth.user_id, model)
        return clone


# ---------------------------------------------------------------------------
# Conventions projection (ADR-411 D6) — composed, never stored
# ---------------------------------------------------------------------------

_CONVENTIONS_FRAME = """You are {model_label}, working inside a YARNNN workspace as {member}'s hands.

## The commons contract
This workspace is a SHARED, versioned filesystem (the commons) that several
humans and AIs work through. Your conversation here is private to this lane,
but everything you write to files is shared, attributed, and visible to
every member on the workspace timeline. The durable output of your work
belongs in FILES — the transcript is not shared memory.

- Read before writing: check what already exists (SearchFiles / ListFiles /
  ReadFile) before creating or overwriting.
- Every write attributes as "{member} via {model}" and is versioned with
  full history — writes are revertible, never silently destructive.
- Cite your sources: when you author a file FROM another file (something
  that arrived, a shared reference, any file you read and built on), pass
  derived_from=[its path(s)] on the WriteFile. The workspace uses that edge
  to show what was made from what and to warn before a source is deleted.
- Other members and other AI lanes collaborate with you THROUGH these files,
  never through your transcript. Leave files other actors can pick up.

{filesystem_model}

Your reach is exactly the member's grant: anything they could not write, you
cannot. The system's own settings + runtime state are owner-and-steward
territory — read them to understand intent, don't author there.

## Your tools
ReadFile · WriteFile · EditFile · SearchFiles · ListFiles — the complete
surface. You cannot schedule work, dispatch agents, or reach external
platforms; you are hands on the filesystem for this member.

## Format discipline
Prose documents are .md. Machine config is _*.yaml (don't author these
unless asked).
{mandate_section}{posture_section}"""


def _read_workspace_file(client: Any, user_id: str, path: str) -> str:
    """Best-effort substrate read (mirrors the envelope reader's shape)."""
    from services.workspace_context import substrate_scope_filter
    full = path if path.startswith("/workspace/") else f"/workspace/{path}"
    try:
        res = (
            client.table("workspace_files")
            .select("content")
            .eq(*substrate_scope_filter(user_id))
            .eq("path", full)
            .limit(1)
            .execute()
        )
        return (res.data or [{}])[0].get("content") or ""
    except Exception as exc:
        logger.warning("[LANE] mandate read failed for %s: %s", path, exc)
        return ""


def build_lane_conventions(
    client: Any,
    user_id: str,
    *,
    model: str,
    member_label: Optional[str] = None,
    artifact_path: Optional[str] = None,
    derive_recipe: Optional[str] = None,
    derive_source: Optional[str] = None,
) -> str:
    """Compose the AGENTS.md-shaped system prompt for one lane turn.

    Kernel constants + the workspace's MANDATE head, composed at turn time
    (DP29 derived-never-stored — a stored copy would drift against
    _workspace_guide.md). Program-bundle deepening is a later, additive
    section (the kernel block stays program-neutral, ADR-222).

    ADR-440 D3: a BOUND lane (``artifact_path`` set — a Studio lane) gains the
    authoring posture as an additive section: the artifact's current head is
    read fresh here (derived, never stored) and ``services.studio`` composes
    the overlay purely.

    ADR-450 D3: a DERIVE-bound lane (``derive_recipe`` + ``derive_source``
    set — a "Learn from" lane) gains the kernel recipe as an additive section.
    The two bindings may coexist; both are per-turn overlays over the same
    conventions frame.
    """
    from services.workspace_paths import (
        CONSTITUTION_MANDATE_PATH,
        PARTICIPANT_FILESYSTEM_MODEL,
    )

    label = LANE_MODELS.get(model, {}).get("label", model)
    member = member_label or "the member"

    mandate = _read_workspace_file(client, user_id, CONSTITUTION_MANDATE_PATH)
    mandate_head = "\n".join(mandate.strip().splitlines()[:40]).strip()
    mandate_section = (
        f"\n## The workspace's mandate (read-only orientation)\n{mandate_head}\n"
        if mandate_head else ""
    )

    posture_section = ""
    if artifact_path:
        from services.studio import build_studio_posture
        artifact = _read_workspace_file(client, user_id, artifact_path)
        posture_section = "\n" + build_studio_posture(artifact_path, artifact) + "\n"
        # ADR-449 D4: when the workspace has a design system, the bound lane
        # learns the Skin contract as an ADDITIVE section (composed here, not
        # in build_studio_posture — the studio posture frame is the ADR-447
        # pass's file). No design system → empty string → zero prompt cost.
        from services.design_systems import build_design_system_section
        ds_section = build_design_system_section(client, user_id)
        if ds_section:
            posture_section += "\n" + ds_section + "\n"

    # ADR-450 D3 — the derive binding's recipe section (the "Learn from"
    # lane's job description; pure composition from the kernel registry).
    # ADR-452 D3: a lane carrying BOTH bindings (the studio learn-from flow)
    # gets the target-override — derive INTO the bound artifact.
    if derive_recipe and derive_source:
        from services.derive_recipes import build_derive_section
        derive_section = build_derive_section(
            derive_recipe, derive_source, artifact_path=artifact_path
        )
        if derive_section:
            posture_section += "\n" + derive_section + "\n"

    return _CONVENTIONS_FRAME.format(
        model_label=label,
        member=member,
        model=label,
        filesystem_model=PARTICIPANT_FILESYSTEM_MODEL,
        mandate_section=mandate_section,
        posture_section=posture_section,
    )


# ---------------------------------------------------------------------------
# The turn loop (ADR-411 D2)
# ---------------------------------------------------------------------------

def _stringify_tool_result(result: Any) -> str:
    if isinstance(result, str):
        return result
    try:
        return json.dumps(result, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(result)


async def run_lane_turn(
    auth: Any,
    *,
    model: str,
    history: list[dict],
    user_message: str,
    member_label: Optional[str] = None,
    artifact_path: Optional[str] = None,
    derive_recipe: Optional[str] = None,
    derive_source: Optional[str] = None,
) -> dict:
    """Run one lane turn: bounded tool loop over the router.

    Args:
        auth: the member's AuthenticatedClient (JWT path — carries
              principal_id + workspace_id).
        model: the lane's pinned LiteLLM model string (LANE_MODELS key).
        history: prior conversation as OpenAI-shape messages (user/assistant
              text only — tool traffic is per-turn, not persisted).
        user_message: this turn's member message.

    Returns:
        {"success": True, "text": ..., "rounds": n, "tools_called": [...],
         "artifacts": [...], "tokens_in": n, "tokens_out": n}
        or {"success": False, "error": ..., "message": ...}
    """
    if model not in LANE_MODELS:
        return {"success": False, "error": "unknown_model",
                "message": f"model must be one of {sorted(LANE_MODELS)}"}

    # ADR-439 §4 (F1) — hard-block an unpriced model BEFORE any billable call.
    if unpriced_lane_model(model):
        logger.error("[LANE] refused unpriced model %r — no _BILLING_RATES row", model)
        return {"success": False, **_UNPRICED_MODEL_ERROR}

    from services.model_router import model_router_enabled, route_completion
    if not model_router_enabled():
        return {"success": False, "error": "router_disabled",
                "message": "MODEL_ROUTER_ENABLED is off — lanes need the router"}

    from services.primitives.registry import execute_primitive

    tool_auth = _lane_auth(auth, model)
    tools = lane_tools_openai()
    system = build_lane_conventions(
        auth.client, auth.user_id, model=model, member_label=member_label,
        artifact_path=artifact_path,
        derive_recipe=derive_recipe, derive_source=derive_source,
    )
    # ADR-440 D3 — authoring turns need more room than chat turns. ADR-450:
    # derive turns author whole files from a source — same profile.
    max_tokens = (
        _studio_max_tokens() if (artifact_path or derive_recipe) else _LANE_MAX_TOKENS
    )

    messages: list[dict] = list(history) + [{"role": "user", "content": user_message}]
    tools_called: list[str] = []
    artifacts: list[str] = []
    total_in = 0
    total_out = 0
    final_text = ""
    rounds = 0
    ledger_model = model.split("/", 1)[1] if "/" in model else model

    # ADR-439 BYOK — resolve the workspace's own key for this model's provider,
    # ONCE per turn. None → managed default (our keys, metered normally). When a
    # key resolves, the router authenticates with it AND the ledger records the
    # rounds at cost-to-us = 0 (ADR-409 D2 — draws nothing from the pool). The
    # steward still meters on our keys elsewhere (D3).
    byok_key = _resolve_byok_key(auth, model)
    byok_cost_override = 0.0 if byok_key else None

    for round_idx in range(_LANE_MAX_ROUNDS):
        rounds = round_idx + 1
        routed = await route_completion(
            model,
            messages,
            system=system,
            max_tokens=max_tokens,
            timeout=_LANE_TIMEOUT_S,
            tools=tools,
            api_key=byok_key,
        )
        total_in += routed.usage.get("input_tokens", 0)
        total_out += routed.usage.get("output_tokens", 0)

        # ADR-411 D5: every round is a metered judgment invocation on the
        # ONE ledger, attributed to the member (their embodiment acting).
        # ADR-439: a BYOK round records cost_usd=0 (an EXPLICIT, intentional
        # exception to the ADR-396 at-cost invariant — the customer's key paid,
        # so it draws nothing from the pool).
        try:
            from services.supabase import get_service_client
            from services.telemetry import record_execution_event
            record_execution_event(
                get_service_client(),
                user_id=auth.user_id,
                slug="lane",
                mode="judgment",
                trigger_type="addressed",
                status="success",
                tool_rounds=rounds,
                model=routed.ledger_model,
                principal_id=getattr(auth, "principal_id", None) or auth.user_id,
                workspace_id=getattr(auth, "workspace_id", None),
                cost_override_usd=byok_cost_override,
                **routed.usage,
            )
        except Exception as exc:
            logger.warning("[LANE] cost ledger record failed: %s", exc)

        if not routed.tool_calls:
            final_text = routed.text
            break

        # Continue the loop: provider-exact assistant message + tool results.
        messages.append(
            routed.raw_assistant_message
            or {"role": "assistant", "content": routed.text or ""}
        )
        for tc in routed.tool_calls:
            name = tc["name"]
            tools_called.append(name)
            if name not in LANE_TOOL_NAMES:
                result: Any = {
                    "success": False, "error": "tool_not_on_lane_surface",
                    "message": f"lane tools: {', '.join(LANE_TOOL_NAMES)}",
                }
            else:
                try:
                    result = await execute_primitive(tool_auth, name, tc["arguments"])
                except Exception as exc:
                    result = {"success": False, "error": "tool_raised", "message": str(exc)}
            produced = artifact_path_from(name, result)
            if produced and produced not in artifacts:
                artifacts.append(produced)
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": _stringify_tool_result(result),
            })
    else:
        final_text = final_text or "[lane turn exhausted its round budget without a final reply]"

    logger.info(
        "[LANE] model=%s rounds=%d tokens=%d/%d tools=%d artifacts=%d",
        model, rounds, total_in, total_out, len(tools_called), len(artifacts),
    )
    return {
        "success": True,
        "text": final_text,
        "rounds": rounds,
        "tools_called": tools_called,
        "artifacts": artifacts,
        "tokens_in": total_in,
        "tokens_out": total_out,
        "ledger_model": ledger_model,
    }


async def run_lane_turn_stream(
    auth: Any,
    *,
    model: str,
    history: list[dict],
    user_message: str,
    member_label: Optional[str] = None,
    artifact_path: Optional[str] = None,
    derive_recipe: Optional[str] = None,
    derive_source: Optional[str] = None,
):
    """Streaming sibling of ``run_lane_turn`` (ADR-412 D2 lane streaming).

    An async generator over the SAME bounded tool loop, yielding events for
    SSE transport:
      - ``("tool", {"name": str})``       — a tool round called this tool
                                            (emitted BEFORE execution, so the
                                            member sees the spinner name)
      - ``("artifact", {"path", "verb"})`` — a WriteFile/EditFile LANDED. The
                                            member's chat renders the file
                                            inline (the artifact card). Emitted
                                            AFTER execution, success only.
      - ``("delta", str)``                — a text fragment on the FINAL round
      - ``("done", {result dict})``       — terminal; the same shape
                                            ``run_lane_turn`` returns
      - ``("error", {error, message})``   — a fatal precondition

    The two invariants ``run_lane_turn`` holds are held here byte-identically:
    the ONE ledger record per round (ADR-396) and the bounded tool loop
    (ADR-411). Only text TRANSPORT changes — tool rounds carry no user-visible
    text (their deltas would be tool-call JSON), so text streams only on the
    final round. The caller persists ONE assistant row at ``done`` from the
    accumulated text + tools_called (the ADR-219 write path, unchanged).
    """
    if model not in LANE_MODELS:
        yield ("error", {"error": "unknown_model",
                         "message": f"model must be one of {sorted(LANE_MODELS)}"})
        return

    # ADR-439 §4 (F1) — hard-block an unpriced model BEFORE any billable call.
    if unpriced_lane_model(model):
        logger.error("[LANE] refused unpriced model %r — no _BILLING_RATES row", model)
        yield ("error", dict(_UNPRICED_MODEL_ERROR))
        return

    from services.model_router import model_router_enabled, route_completion_stream
    if not model_router_enabled():
        yield ("error", {"error": "router_disabled",
                         "message": "MODEL_ROUTER_ENABLED is off — lanes need the router"})
        return

    from services.primitives.registry import execute_primitive

    tool_auth = _lane_auth(auth, model)
    tools = lane_tools_openai()
    system = build_lane_conventions(
        auth.client, auth.user_id, model=model, member_label=member_label,
        artifact_path=artifact_path,
        derive_recipe=derive_recipe, derive_source=derive_source,
    )
    # ADR-440 D3 — authoring turns need more room than chat turns. ADR-450:
    # derive turns author whole files from a source — same profile.
    max_tokens = (
        _studio_max_tokens() if (artifact_path or derive_recipe) else _LANE_MAX_TOKENS
    )

    messages: list[dict] = list(history) + [{"role": "user", "content": user_message}]
    tools_called: list[str] = []
    artifacts: list[str] = []
    total_in = 0
    total_out = 0
    final_text = ""
    rounds = 0
    ledger_model = model.split("/", 1)[1] if "/" in model else model

    # ADR-439 BYOK — resolve once per turn (see the non-streaming path for the
    # full rationale). None → managed default; a key → customer auth + cost-0 rows.
    byok_key = _resolve_byok_key(auth, model)
    byok_cost_override = 0.0 if byok_key else None

    for round_idx in range(_LANE_MAX_ROUNDS):
        rounds = round_idx + 1
        routed = None
        # Stream this round. On a text round the deltas are user-visible; on
        # a tool round they are empty and we act on `routed.tool_calls`.
        async for kind, payload in route_completion_stream(
            model, messages, system=system,
            max_tokens=max_tokens, timeout=_LANE_TIMEOUT_S, tools=tools,
            api_key=byok_key,
        ):
            if kind == "delta":
                yield ("delta", payload)
            elif kind == "done":
                routed = payload

        if routed is None:  # defensive — the generator always yields done
            yield ("error", {"error": "stream_incomplete",
                             "message": "the model stream closed without a result"})
            return

        total_in += routed.usage.get("input_tokens", 0)
        total_out += routed.usage.get("output_tokens", 0)

        # ADR-411 D5 / ADR-396: one metered judgment invocation per round,
        # attributed to the member — identical to the non-streaming path.
        # ADR-439: BYOK rounds record cost_usd=0 (explicit at-cost exception).
        try:
            from services.supabase import get_service_client
            from services.telemetry import record_execution_event
            record_execution_event(
                get_service_client(),
                user_id=auth.user_id,
                slug="lane",
                mode="judgment",
                trigger_type="addressed",
                status="success",
                tool_rounds=rounds,
                model=routed.ledger_model,
                principal_id=getattr(auth, "principal_id", None) or auth.user_id,
                workspace_id=getattr(auth, "workspace_id", None),
                cost_override_usd=byok_cost_override,
                **routed.usage,
            )
        except Exception as exc:
            logger.warning("[LANE stream] cost ledger record failed: %s", exc)

        if not routed.tool_calls:
            final_text = routed.text
            break

        messages.append(
            routed.raw_assistant_message
            or {"role": "assistant", "content": routed.text or ""}
        )
        for tc in routed.tool_calls:
            name = tc["name"]
            tools_called.append(name)
            yield ("tool", {"name": name})
            if name not in LANE_TOOL_NAMES:
                result: Any = {
                    "success": False, "error": "tool_not_on_lane_surface",
                    "message": f"lane tools: {', '.join(LANE_TOOL_NAMES)}",
                }
            else:
                try:
                    result = await execute_primitive(tool_auth, name, tc["arguments"])
                except Exception as exc:
                    result = {"success": False, "error": "tool_raised", "message": str(exc)}
            # The work landed in a file — say WHICH file, so the member's chat
            # can open it inline. This is the ADR-411 lane contract ("the
            # transcript is private; the work lands in files") made visible.
            produced = artifact_path_from(name, result)
            if produced and produced not in artifacts:
                artifacts.append(produced)
                yield ("artifact", {"path": produced, "verb": name})
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": _stringify_tool_result(result),
            })
    else:
        final_text = final_text or "[lane turn exhausted its round budget without a final reply]"

    logger.info(
        "[LANE stream] model=%s rounds=%d tokens=%d/%d tools=%d artifacts=%d",
        model, rounds, total_in, total_out, len(tools_called), len(artifacts),
    )
    yield ("done", {
        "success": True,
        "text": final_text,
        "rounds": rounds,
        "tools_called": tools_called,
        "artifacts": artifacts,
        "tokens_in": total_in,
        "tokens_out": total_out,
        "ledger_model": ledger_model,
    })


__all__ = [
    "LANE_MODELS",
    "LANE_TOOL_NAMES",
    "lane_tools_openai",
    "lane_caller_identity",
    "build_lane_conventions",
    "run_lane_turn",
    "run_lane_turn_stream",
]
