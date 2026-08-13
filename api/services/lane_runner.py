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

import asyncio
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
#: ⚠️ THIS DICT IS ALSO THE TURN-TIME WHITELIST, NOT JUST THE CREATION PICKER.
#: `run_lane_turn` and `run_lane_turn_stream` both refuse a model that is not a
#: key here (lines ~528 / ~720), so **deleting a row breaks every existing lane
#: pinned to it** — a lane's `model` is persisted at creation and is a
#: historical fact (ADR-460 D4). At the 2026-08-12 roster refresh all 65 live
#: lanes pinned `claude-sonnet-4-6`, 56 of them bound Studio lanes; removing
#: that row would have orphaned the entire workspace. Hence `retired`:
#: superseded rows STAY and keep running their lanes; they simply leave the
#: chooser (ADR-559 D2).
#:
#: `retired`: absent/False = offered at the door. True = still routable for
#: lanes already pinned to it, never offered for a NEW conversation.
LANE_MODELS: dict[str, dict[str, Any]] = {
    # ── Anthropic ────────────────────────────────────────────────────────
    # ADR-559 D1: the Anthropic lane was two generations stale — Sonnet 4.6
    # with no Opus tier at all, so a member wanting Anthropic's frontier model
    # could not pick one. Sonnet 5 supersedes 4.6 at the SAME list price
    # ($3/$15); Opus 5 adds the frontier tier the roster never had.
    "anthropic/claude-opus-5": {"label": "Claude Opus", "vision": True},
    "anthropic/claude-sonnet-5": {"label": "Claude Sonnet", "vision": True},
    "anthropic/claude-haiku-4-5": {"label": "Claude Haiku", "vision": True},
    # ── OpenAI ───────────────────────────────────────────────────────────
    "openai/gpt-5": {"label": "GPT-5", "vision": True},                        # frontier OpenAI
    "openai/gpt-4o-mini": {"label": "GPT-4o mini", "vision": True},            # cheap OpenAI
    # ── Google ───────────────────────────────────────────────────────────
    "gemini/gemini-2.5-pro": {"label": "Gemini Pro", "vision": True},          # frontier Google reasoning
    "gemini/gemini-2.5-flash": {"label": "Gemini Flash", "vision": True},      # the Google lane (fast/cheap)
    # ── DeepSeek ─────────────────────────────────────────────────────────
    "deepseek/deepseek-chat": {"label": "DeepSeek", "vision": False},          # cost-floor / sovereign lane
    # ── xAI ──────────────────────────────────────────────────────────────
    # A genuinely new price/context point, not a duplicate: $2/$6 sits between
    # Haiku and Sonnet, with a 500k window. ⚠️ xAI prices by PROMPT LENGTH
    # (≥200k doubles to $4/$12) and `_BILLING_RATES` is flat — the rate row
    # carries the ≥200k tier deliberately. See the note there.
    "xai/grok-4.6": {"label": "Grok", "vision": True},
    # ── RETIRED (honored, not offered) ───────────────────────────────────
    # Superseded engines. They keep every lane already pinned to them running
    # — a lane's engine is what ACTUALLY ran and must not be rewritten — but
    # they are gone from the chooser. Keep the `_BILLING_RATES` row for each:
    # `unpriced_lane_model` gates every turn, so an unpriced retired row would
    # refuse the very lanes this state exists to protect.
    "anthropic/claude-sonnet-4-6": {
        "label": "Claude Sonnet 4.6", "vision": True, "retired": True,
    },
    # The dated Haiku spelling. `claude-haiku-4-5` is the same model — the
    # suffix-free id is the current form (a date-suffixed alias is not a
    # distinct engine), so the old spelling is retired rather than deleted:
    # SYSTEM_CALLS and any pre-refresh lane may still name it.
    "anthropic/claude-haiku-4-5-20251001": {
        "label": "Claude Haiku (4.5)", "vision": True, "retired": True,
    },
}


def offered_lane_models() -> dict[str, dict[str, Any]]:
    """The engines a member may START a conversation with (ADR-559 D2).

    `LANE_MODELS` minus retired rows. The chooser reads THIS; the turn-time
    whitelist reads the full dict. One dict, two audiences — a retired engine
    keeps running its own lanes and stops being offered for new ones."""
    return {k: v for k, v in LANE_MODELS.items() if not v.get("retired")}

_LANE_MAX_ROUNDS = 8       # cost ceiling, not behavior (ADR-402 posture)
#: The think profile (Phase-A chassis item 1, ADR-457 D6 as amended 2026-07-15).
#: 2048 was a hands-profile that truncated thinking answers. Held below the
#: 8192 authoring profile (ADR-440 D3: authoring > chat, gate-asserted); raise
#: further against felt truncation, not speculation.
#:
#: Sonnet 5 re-measurement (2026-08-12, ADR-559 follow-through): Sonnet 5's
#: tokenizer is x1.35–1.47 heavier than Sonnet 4.6 on identical text (mean
#: x1.39 across prose/code/mixed corpora, via count_tokens), so 4096 here is
#: ~2940 Sonnet-4.6-equivalent tokens — still above the 2048 that truncated,
#: and a live lane-shaped ask finished `stop` at 22% of budget on Sonnet 5.
#: The budget HOLDS on evidence; if felt truncation arrives, x1.39 says the
#: parity raise is ~5700, not a guess.
_LANE_MAX_TOKENS = 4096
_LANE_TIMEOUT_S = 120.0


def _studio_max_tokens() -> int:
    """ADR-440 D3 — the authoring token profile for BOUND (Studio) lanes."""
    from services.authoring import STUDIO_LANE_MAX_TOKENS
    return STUDIO_LANE_MAX_TOKENS

# ---------------------------------------------------------------------------
# Tool surface (ADR-411 D3) — five file verbs, registry definitions converted
# ---------------------------------------------------------------------------

#: The lane tool allowlist. A helper is hands on the filesystem — no entity
#: verbs, no Schedule, no DispatchSpecialist, no platform tools.
LANE_TOOL_NAMES = ("ReadFile", "WriteFile", "EditFile", "SearchFiles", "ListFiles")

#: The three reads beyond the five verbs — UNIFORM for every lane (ADR-467 D4).
#: Capability stopped being a per-Agent fact: the per-row `tools` field was a
#: bug factory with no safety payoff (the gate, not the allowlist, was always
#: the boundary — both names are derived non-consequential in
#: `permission.py::READ_ONLY_PRIMITIVES`, the D4.a ceiling, gate-asserted).
#: Character is the differentiator; reach is not. Any FUTURE addition here is a
#: uniform addition, evidence-gated, and must be in READ_ONLY_PRIMITIVES (the
#: gate asserts this) AND have a schema in `lane_tools_openai` (which fails
#: loud, not silent, on a missing one).
#: `list_integrations` (ADR-535 D2) is the member's BINDING INVENTORY — which
#: connectors they bound, and their status. Metadata only: it never calls a
#: provider API and never decrypts a credential. It is here because a lane that
#: cannot see the member's bindings GUESSES about them, and guessed wrong on a
#: live surface (the ADR-535 §1 screenshot: "this workspace doesn't have a live
#: Notion connector", said over an active Notion binding). Seeing a connector is
#: NOT reaching through one — no `platform_*` tool is on this surface, and the
#: frame states that edge affirmatively (ADR-535 D3), because a model handed the
#: inventory will otherwise infer the reach.
#: ADR-568 D3 adds `GenerateImage` — the first CONSEQUENTIAL name on this
#: list. The ADR-467 D4.a ceiling is RESTATED, not bent: every name here is in
#: `READ_ONLY_PRIMITIVES` **or** in `LANE_ARTIFACT_VERBS`. Putting a spending,
#: revision-landing verb into the read-only set to satisfy a subset check
#: would be defeating a gate in order to pass it.
LANE_SURFACE_EXTRA = ("QueryKnowledge", "WebSearch", "list_integrations", "GenerateImage")

#: The subset of the lane surface that PRODUCES substrate. A successful call
#: to one of these lands an attributed revision, and the member should SEE what
#: their lane made — not just the verb's name (2026-07-09, the artifact card).
#: ReadFile/SearchFiles/ListFiles also return a `path`, which is why the gate
#: is on the verb and not merely on the result's shape.
#: ADR-568 D3: `GenerateImage` belongs here for the reason the set exists —
#: a successful call lands an attributed revision the member should SEE. It is
#: also what keeps the restated D4.a ceiling honest: the verb is classified as
#: consequential rather than smuggled into `READ_ONLY_PRIMITIVES`.
LANE_ARTIFACT_VERBS = ("WriteFile", "EditFile", "GenerateImage")


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


# ---------------------------------------------------------------------------
# Engine availability (ADR-559 D3)
# ---------------------------------------------------------------------------
#
# An engine can be unavailable for THREE structurally different reasons, and
# only two of them are knowable before a member clicks:
#
#   no_provider_key  — the key never landed on this deployment. Ours to fix;
#                      checkable from env.
#   unpriced         — no `_BILLING_RATES` row. Ours to fix; checkable.
#   upstream_refused — the provider itself declines (billing, quota). NOT
#                      predictable — only a real call reveals it. DeepSeek's
#                      "Insufficient Balance" (probe, 2026-08-12) is the first
#                      instance, and it is why this is a general mechanism
#                      rather than a special case for one row.
#
# The first two are computed; the third is OBSERVED and remembered (see
# `note_upstream_refusal`). A member sees the engine greyed with its reason —
# never hidden. Hiding is worse: someone who expects DeepSeek and sees nothing
# assumes a bug, and files one.

#: provider prefix → the env var whose presence lights that provider.
_PROVIDER_KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "xai": "XAI_API_KEY",
}

#: Engines observed refusing upstream this process, → the provider's own words.
#: Process-local and deliberately NOT persisted: an upstream refusal is a
#: transient fact about someone else's account, and a funded account must heal
#: on its next successful call without an operator clearing a table. A restart
#: re-learns from the next attempt.
_upstream_refused: dict[str, str] = {}

#: The provider-side error shapes that mean "your account, not your request".
#: Substring match on the exception text — providers do not share an error
#: taxonomy, and a 4xx body is the only signal they agree on.
_UPSTREAM_REFUSAL_MARKERS = (
    "insufficient balance",
    "insufficient_quota",
    "exceeded your current quota",
    "billing",
    "payment required",
)


def note_upstream_refusal(model: str, exc: BaseException) -> bool:
    """Record an engine as upstream-unavailable IFF the provider refused for
    an ACCOUNT reason. Returns True when it did.

    Deliberately narrow: a timeout, a rate limit, or a bad request is not
    unavailability — marking an engine dark on any error would take a whole
    lane out of the picker for one transient blip."""
    text = str(exc).lower()
    if not any(marker in text for marker in _UPSTREAM_REFUSAL_MARKERS):
        return False
    _upstream_refused[model] = str(exc)[:200]
    logger.warning(
        "[LANE] %s marked upstream-unavailable: %s", model, str(exc)[:160],
    )
    return True


def clear_upstream_refusal(model: str) -> None:
    """A successful call heals the engine. Called on every successful routed
    turn, so a funded account recovers without operator action."""
    if _upstream_refused.pop(model, None) is not None:
        logger.info("[LANE] %s is available again (a call succeeded)", model)


def lane_model_availability(model: str) -> tuple[bool, Optional[str]]:
    """`(available, reason)` for one engine. Pure apart from env + the
    observed-refusal map. `reason` is None when available."""
    import os

    provider = model.split("/", 1)[0] if "/" in model else model
    env_var = _PROVIDER_KEY_ENV.get(provider)
    if env_var and not (os.environ.get(env_var) or "").strip():
        return False, "no_provider_key"
    if unpriced_lane_model(model):
        return False, "unpriced"
    if model in _upstream_refused:
        return False, "upstream_refused"
    return True, None


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


def lane_tool_names() -> tuple:
    """THE lane's tool-name set: the five file verbs + the uniform reads
    (ADR-467 D4). One set, every lane, every Agent.

    ⚠️ SINGULAR SOURCE. Three things must agree about which tools a turn has:
    the DECLARED payload the model receives (`lane_tools_openai`), the EXECUTION
    allowlist the tool loop dispatches against, and the PROMPT prose that tells
    the model what it holds. When they were computed separately they disagreed
    and shipped a bug (Scout's declared-but-undispatchable tools, `5ba26e1`);
    when the set varied per Agent, the variance itself was the bug surface
    (ADR-467 §1). This is the one computation all three read, and it no longer
    takes an argument to disagree about.
    """
    return LANE_TOOL_NAMES + LANE_SURFACE_EXTRA


def lane_tools_openai() -> list[dict]:
    """The lane tool surface in OpenAI format, derived from the registry's
    own definitions (no parallel schemas — Singular Implementation).

    Composes definitions; it does not authorize — the D4.a ceiling is asserted
    in the gate (`LANE_SURFACE_EXTRA` ⊆ `READ_ONLY_PRIMITIVES`). A surface name
    with no schema here is an ERROR, never a silent drop: the pre-ADR-467 code
    filtered `if n in by_name`, which would have shipped the Scout bug mirrored
    (prompt + allowlist claiming a tool the payload never carried) on the next
    surface addition.
    """
    # ADR-535 D2: the registry's own LIST_INTEGRATIONS_TOOL, composed — not a
    # parallel lane-local definition (Singular Implementation).
    from services.primitives.generate_image import GENERATE_IMAGE_TOOL
    from services.primitives.registry import LIST_INTEGRATIONS_TOOL
    from services.primitives.web_search import WEB_SEARCH_PRIMITIVE
    from services.primitives.workspace import (
        EDIT_FILE_TOOL,
        LIST_FILES_TOOL,
        QUERY_KNOWLEDGE_TOOL,
        READ_FILE_TOOL,
        SEARCH_FILES_TOOL,
        WRITE_FILE_TOOL,
    )

    by_name = {
        t["name"]: t
        for t in (READ_FILE_TOOL, WRITE_FILE_TOOL, EDIT_FILE_TOOL,
                  SEARCH_FILES_TOOL, LIST_FILES_TOOL,
                  QUERY_KNOWLEDGE_TOOL, WEB_SEARCH_PRIMITIVE,
                  LIST_INTEGRATIONS_TOOL, GENERATE_IMAGE_TOOL)
    }
    missing = [n for n in lane_tool_names() if n not in by_name]
    if missing:
        raise ValueError(
            f"lane surface names {missing} have no tool schema — a surface "
            "addition must land its schema in the same edit (ADR-467 D4)"
        )
    return [_anthropic_to_openai_tool(by_name[n]) for n in lane_tool_names()]


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
{commons_contract}

- {read_before_write} Use SearchFiles / ListFiles / ReadFile.
- Every write attributes as "{member} via {model}", {attribution_rule}
- {citation_rule}

{filesystem_model}

Your reach is exactly the member's grant: anything they could not write, you
cannot. The system's own settings + runtime state are owner-and-steward
territory — read them to understand intent, don't author there.

## Your tools
{tools_line} — the complete surface. You cannot schedule work, dispatch
agents, or write out to external platforms; you read this member's commons
(QueryKnowledge searches it by meaning) and the open web (WebSearch), and you
write only to the commons.

list_integrations tells you which platforms {member} has CONNECTED (Notion,
Slack, GitHub) and whether each is active. Call it instead of guessing — never
tell them a connector is absent without looking. But seeing a connection is not
having it: you can name what they bound, and you CANNOT read through it. There
is no tool here that opens a Notion page or a Slack channel. If they want that
content, say so plainly and offer what you can do — they can paste it, or
export and drop the files into the commons, where you read them normally.

## Format discipline
{format_discipline}
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
    agent: Optional[str] = None,
    focus: Optional[dict] = None,
    app: Optional[str] = None,
) -> str:
    """Compose the AGENTS.md-shaped system prompt for one lane turn.

    Kernel constants + the workspace's MANDATE head, composed at turn time
    (DP29 derived-never-stored — a stored copy would drift against
    _workspace_guide.md). Program-bundle deepening is a later, additive
    section (the kernel block stays program-neutral, ADR-222).

    ADR-440 D3: a BOUND lane (``artifact_path`` set — a Studio lane) gains the
    authoring posture as an additive section: the artifact's current head is
    read fresh here (derived, never stored) and ``services.authoring`` composes
    the overlay purely.

    ADR-450 D3: a DERIVE-bound lane (``derive_recipe`` + ``derive_source``
    set — a "Learn from" lane) gains the kernel recipe as an additive section.
    The two bindings may coexist; both are per-turn overlays over the same
    conventions frame.
    """
    # ADR-533 D1: the commons-contract clauses are kernel data composed here —
    # this frame never restates one inline (ratcheted by
    # test_adr533_participant_contract.py, same discipline ADR-424 D1 set for
    # PARTICIPANT_FILESYSTEM_MODEL).
    from services.workspace_paths import (
        CONSTITUTION_MANDATE_PATH,
        PARTICIPANT_ATTRIBUTION_RULE,
        PARTICIPANT_CITATION_RULE,
        PARTICIPANT_COMMONS_CONTRACT,
        PARTICIPANT_FILESYSTEM_MODEL,
        PARTICIPANT_FORMAT_DISCIPLINE,
        PARTICIPANT_READ_BEFORE_WRITE,
    )

    label = LANE_MODELS.get(model, {}).get("label", model)
    member = member_label or "the member"

    # This turn's member-authored Agents, read ONCE for the whole frame — the
    # posture and the skills consume it (best-effort; a broken manifest never
    # breaks a turn). Empty for a lane with no agent.
    from services.agents_registry import find_member_agents
    _mine = find_member_agents(client, user_id) if agent else []

    # The tool line names the lane surface — UNIFORM for every lane (ADR-467
    # D4). Derived from the same `lane_tool_names` the payload + the loop's
    # allowlist read, so the prose can never claim a surface the model wasn't
    # handed (the Scout bug's prose half).
    tools_line = " · ".join(lane_tool_names())

    mandate = _read_workspace_file(client, user_id, CONSTITUTION_MANDATE_PATH)
    mandate_head = "\n".join(mandate.strip().splitlines()[:40]).strip()
    mandate_section = (
        f"\n## The workspace's mandate (read-only orientation)\n{mandate_head}\n"
        if mandate_head else ""
    )

    posture_section = ""

    # The bound artifact's CURRENT head, read ONCE for the whole frame (derived,
    # never stored). Two consumers: ADR-562 D6's app-name resolution (below) and
    # ADR-440 D3's authoring posture (further down). It was read twice for one
    # commit — a second round-trip per turn for the same bytes.
    artifact = (
        _read_workspace_file(client, user_id, artifact_path) if artifact_path else ""
    )

    # ADR-460 D4 — WHO this lane's helper is, composed at turn time from the
    # slug (the ADR-411 D6 derived-never-stored pattern: a posture is not a
    # historical fact about what ran, it is how this Agent works NOW, so it
    # must follow the registry — unlike `model`, which IS such a fact and is
    # persisted on the lane). Composed FIRST: the Agent's character precedes
    # what it is working on; the binding postures below are the JOB, this is
    # the colleague. Empty string for a lane with no agent (every pre-registry
    # lane, and every Studio/derive lane) — byte-identical to today.
    if agent:
        from services.agents_registry import build_agent_posture, find_agent_skills
        # Member-first (the later-widening): a named colleague ("Lisa") wears a
        # kernel capability's character plus the member's own tone. `_mine` was
        # read once at the top of the frame (shared with the tool line).
        # ADR-464 — the skills the member taught THIS colleague. The folder comes
        # free from the manifest the discovery above already read; a kernel agent
        # has no folder, so it has no skills (a kernel skill would be a kernel
        # edit, and the kernel corpus is code — the DERIVE_RECIPES pattern).
        _skills: list = []
        _me = next((a for a in _mine if a["slug"] == agent), None)
        if _me and _me.get("manifest_path"):
            _skills = find_agent_skills(
                client, user_id, _me["manifest_path"].rsplit("/", 1)[0]
            )
        # ADR-562 D6 — the APP's name for its resident (Docs calls Designer
        # "Writer"). DERIVED from the artifact's own `data-template`, never
        # stored on the lane: the app is a fact about the DOCUMENT, so deriving
        # it means a lane can never carry a stale label for an artifact that
        # changed hands. Empty for an unbound lane (no artifact → no app → the
        # character's own name), which is byte-identical to pre-564.
        _as_name = ""
        if artifact_path:
            import services.apps  # noqa: F401  (registration side-effect)
            from services.authoring import (
                app_for_layout,
                extract_template,
                resolve_app,
            )

            _app = app_for_layout(extract_template(artifact))
            _as_name = (resolve_app(_app) or {}).get("name") or ""
        posture_section += build_agent_posture(agent, _mine, _skills, as_name=_as_name)
    if artifact_path and app == "radar":
        # ADR-567 D4 — the DESK posture: a radar lane is bound to the watched
        # folder's report.md, and its JOB is folder management (author/revise
        # CRITERION.md + _radar.yaml, tend the report), not Studio authoring.
        # The binding app is a LANE fact here: the artifact is plain markdown,
        # so the document-derived app resolution (data-template) has nothing
        # to read, and the agent slug cannot name the app (Docs and Studio
        # share designer). Selects the JOB overlay only — never the resident.
        from services.radar import build_desk_posture
        posture_section += "\n" + build_desk_posture(client, user_id, artifact_path) + "\n"
    elif artifact_path:
        from services.authoring import build_studio_posture
        # `artifact` was read once at the top of the frame (shared with ADR-562 D6's
        # app-name resolution) — still the CURRENT head, still derived-never-stored.
        # `+=`, NOT `=`. This was an assignment until 2026-07-16, which was
        # latent-only because no bound lane carried an agent — the moment
        # Studio's lane got a Designer (ADR-460 §4b), an `=` here would have
        # silently eaten the colleague's character and left only the job. The
        # rule the comment above states ("the binding postures below are the
        # JOB, this is the colleague") is now what the code does. Three
        # overlays, one rule: every binding APPENDS to the character.
        # ADR-522: the focus rides the SAME overlay as the artifact head — both
        # are per-turn readings of the bound artifact (what it IS, where the
        # member IS in it), so they compose in one place.
        posture_section += (
            "\n" + build_studio_posture(artifact_path, artifact, focus) + "\n"
        )
        # ADR-449 D4: when the workspace has a design system, the bound lane
        # learns the Skin contract as an ADDITIVE section (composed here, not
        # in build_studio_posture — the studio posture frame is the ADR-447
        # pass's file). No design system → empty string → zero prompt cost.
        from services.design_systems import build_design_system_section
        ds_section = build_design_system_section(client, user_id)
        if ds_section:
            posture_section += "\n" + ds_section + "\n"
    elif focus and (focus.get("path") or focus.get("label")):
        # ADR-522, completed for the UNBOUND lane (2026-08-12). The focus wire
        # was threaded end-to-end and then rendered ONLY inside the bound
        # lane's studio posture — a general chat lane received the member's
        # declared focus and said nothing about it, so file work the member
        # expected to SEE on their canvas was meaning-placed elsewhere (the
        # fundraiser-copy incident: the lane duplicated the open document into
        # a new folder and the member watched an unchanged canvas). One
        # situational line; the member's open file is the DEFAULT target for
        # file work they expect to watch land.
        _fpath = (focus.get("path") or "").strip()
        _flabel = (focus.get("label") or "").strip()
        _fapp = (focus.get("app") or "a surface").strip()
        _fdesc = _fpath or _flabel
        posture_section += (
            f"\n- The member is looking at: {_fapp} — {_fdesc}."
            " When they ask for changes to a document or file without naming"
            " one, they mean THIS one — edit it in place; never a copy"
            " elsewhere.\n"
        )

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
        commons_contract=PARTICIPANT_COMMONS_CONTRACT,
        attribution_rule=PARTICIPANT_ATTRIBUTION_RULE,
        citation_rule=PARTICIPANT_CITATION_RULE,
        read_before_write=PARTICIPANT_READ_BEFORE_WRITE,
        filesystem_model=PARTICIPANT_FILESYSTEM_MODEL,
        format_discipline=PARTICIPANT_FORMAT_DISCIPLINE,
        tools_line=tools_line,
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
    # str, or OpenAI content-parts list when the turn carries image
    # attachments (Phase A) — embedded into the messages verbatim either way.
    user_message: Any,
    member_label: Optional[str] = None,
    artifact_path: Optional[str] = None,
    derive_recipe: Optional[str] = None,
    derive_source: Optional[str] = None,
    # ADR-522 — what the member is looking at THIS turn (transient; never
    # persisted). Threaded straight to the posture; None → byte-identical.
    focus: Optional[dict] = None,
    # ADR-460 D4 — WHO the member is talking to: the kernel Agent slug whose
    # posture this turn composes. None on Studio/derive lanes and every
    # pre-registry lane (they run byte-identically).
    agent: Optional[str] = None,
    # W0 / ADR-457 D8: the lane's session id — the falsifier join key. Passed
    # to the cost ledger so a metered turn can be joined back to the surface
    # that asked for it (the ledger writes slug="lane" for BOTH chat and Studio
    # bound lanes; the discriminator is the session's binding). Optional: a
    # caller that doesn't pass it still meters correctly, it is just
    # unclassifiable in falsifier 1.
    session_id: Optional[str] = None,
    # ADR-492: rooms reuse this loop for their addressed agent turns but meter
    # under their own slug — the D8 falsifiers stay honest (a room turn is not
    # a lane turn; per-phase evaluation, pre-rooms baseline recorded). For
    # rooms, session_id is the conversation id.
    ledger_slug: str = "lane",
    # ADR-567 D4 — the lane's binding app (lane_meta["app"]), selecting the
    # JOB overlay only (radar → the desk posture). None → byte-identical.
    app: Optional[str] = None,
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

    from services.model_router import lanes_enabled, route_completion
    if not lanes_enabled():
        return {"success": False, "error": "router_disabled",
                "message": "MODEL_ROUTER_ENABLED is off — lanes need the router"}

    from services.primitives.registry import execute_primitive

    tool_auth = _lane_auth(auth, model)
    # ADR-467 D4: ONE surface, every lane — payload and execution allowlist
    # from the same computation (Singular Implementation, lane_tool_names), so
    # the declared-but-undispatchable bug class is unrepresentable.
    tools = lane_tools_openai()
    _allowed = lane_tool_names()
    system = build_lane_conventions(
        auth.client, auth.user_id, model=model, member_label=member_label,
        artifact_path=artifact_path,
        derive_recipe=derive_recipe, derive_source=derive_source,
        agent=agent,
        focus=focus,
        app=app,
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
        # ADR-559 D3 — LEARN from the call. An upstream account refusal is the
        # one unavailability reason nothing can predict; the only way to know
        # is to try. Re-raised either way: this observes, it never swallows.
        try:
            routed = await route_completion(
                model,
                messages,
                system=system,
                max_tokens=max_tokens,
                timeout=_LANE_TIMEOUT_S,
                tools=tools,
                api_key=byok_key,
            )
        except Exception as exc:
            note_upstream_refusal(model, exc)
            raise
        clear_upstream_refusal(model)  # a success heals the engine
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
                slug=ledger_slug,
                mode="judgment",
                trigger_type="addressed",
                status="success",
                tool_rounds=rounds,
                model=routed.ledger_model,
                principal_id=getattr(auth, "principal_id", None) or auth.user_id,
                workspace_id=getattr(auth, "workspace_id", None),
                cost_override_usd=byok_cost_override,
                session_id=session_id,  # W0 — the falsifier join key
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
            if name not in _allowed:
                result: Any = {
                    "success": False, "error": "tool_not_on_lane_surface",
                    "message": f"lane tools: {', '.join(_allowed)}",
                }
            else:
                try:
                    # Round-boundary abort discipline (Phase-A stop): a member
                    # abort cancels the turn at any await — a STARTED primitive
                    # completes whole (the ledger never holds half a revision).
                    # The stopped transcript may omit a write that landed; the
                    # ledger is truth (the no-rewind rule).
                    result = await asyncio.shield(
                        execute_primitive(tool_auth, name, tc["arguments"])
                    )
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
    # str, or OpenAI content-parts list when the turn carries image
    # attachments (Phase A) — embedded into the messages verbatim either way.
    user_message: Any,
    member_label: Optional[str] = None,
    artifact_path: Optional[str] = None,
    derive_recipe: Optional[str] = None,
    derive_source: Optional[str] = None,
    # ADR-522 — the focus declaration; see ``run_lane_turn``.
    focus: Optional[dict] = None,
    # ADR-460 D4 — the Agent slug; see ``run_lane_turn``.
    agent: Optional[str] = None,
    # W0 / ADR-457 D8 — the falsifier join key; see ``run_lane_turn``.
    session_id: Optional[str] = None,
    # ADR-492 — the metering slug; see ``run_lane_turn``.
    ledger_slug: str = "lane",
    # ADR-567 D4 — the lane's binding app; see ``run_lane_turn``.
    app: Optional[str] = None,
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

    from services.model_router import lanes_enabled, route_completion_stream
    if not lanes_enabled():
        yield ("error", {"error": "router_disabled",
                         "message": "MODEL_ROUTER_ENABLED is off — lanes need the router"})
        return

    from services.primitives.registry import execute_primitive

    tool_auth = _lane_auth(auth, model)
    # ADR-467 D4: ONE surface, every lane — payload and execution allowlist
    # from the same computation (Singular Implementation, lane_tool_names), so
    # the declared-but-undispatchable bug class is unrepresentable.
    tools = lane_tools_openai()
    _allowed = lane_tool_names()
    system = build_lane_conventions(
        auth.client, auth.user_id, model=model, member_label=member_label,
        artifact_path=artifact_path,
        derive_recipe=derive_recipe, derive_source=derive_source,
        agent=agent,
        focus=focus,
        app=app,
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
        #
        # ADR-559 D3 — same observe-and-re-raise as the non-streaming loop.
        # An account refusal on a streamed round raises before the first
        # delta, so it is learnable here too.
        try:
            async for kind, payload in route_completion_stream(
                model, messages, system=system,
                max_tokens=max_tokens, timeout=_LANE_TIMEOUT_S, tools=tools,
                api_key=byok_key,
            ):
                if kind == "delta":
                    yield ("delta", payload)
                elif kind == "done":
                    routed = payload
        except Exception as exc:
            note_upstream_refusal(model, exc)
            raise
        clear_upstream_refusal(model)  # a success heals the engine

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
                slug=ledger_slug,
                mode="judgment",
                trigger_type="addressed",
                status="success",
                tool_rounds=rounds,
                model=routed.ledger_model,
                principal_id=getattr(auth, "principal_id", None) or auth.user_id,
                workspace_id=getattr(auth, "workspace_id", None),
                cost_override_usd=byok_cost_override,
                session_id=session_id,  # W0 — the falsifier join key
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
            if name not in _allowed:
                result: Any = {
                    "success": False, "error": "tool_not_on_lane_surface",
                    "message": f"lane tools: {', '.join(_allowed)}",
                }
            else:
                try:
                    # Round-boundary abort discipline (Phase-A stop): a member
                    # abort cancels the turn at any await — a STARTED primitive
                    # completes whole (the ledger never holds half a revision).
                    # The stopped transcript may omit a write that landed; the
                    # ledger is truth (the no-rewind rule).
                    result = await asyncio.shield(
                        execute_primitive(tool_auth, name, tc["arguments"])
                    )
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
    "LANE_SURFACE_EXTRA",
    "lane_tools_openai",
    "lane_caller_identity",
    "build_lane_conventions",
    "run_lane_turn",
    "run_lane_turn_stream",
]
