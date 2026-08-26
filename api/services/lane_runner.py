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
- The lane tool surface (ADR-411 D3): the file + folder verbs, converted
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
#:
#: ⭐ `label` CARRIES THE VERSION, ALWAYS (2026-08-21). The label is not just
#: picker chrome — it is written into EVERY revision's attribution string
#: (`principal_display.model_display` → "Kevin via Claude Sonnet 5") and it is
#: what the model is TOLD IT IS (`_CONVENTIONS_FRAME`: "You are {model_label}").
#: A family name alone breaks both. Before this, `claude-sonnet-4-6` (retired)
#: and `claude-sonnet-5` (live) BOTH displayed "Claude Sonnet", so a member
#: reading their own history could not tell which engine authored a revision —
#: an incorrect-success in the ledger, on a product whose invariant is that
#: every change is signed by whoever made it. Two rows must never share a
#: label; the gate asserts uniqueness.
LANE_MODELS: dict[str, dict[str, Any]] = {
    # ── Anthropic ────────────────────────────────────────────────────────
    # ADR-559 D1: the Anthropic lane was two generations stale — Sonnet 4.6
    # with no Opus tier at all, so a member wanting Anthropic's frontier model
    # could not pick one. Sonnet 5 supersedes 4.6 at the SAME list price
    # ($3/$15); Opus 5 adds the frontier tier the roster never had.
    "anthropic/claude-opus-5": {"label": "Claude Opus 5", "vision": True},
    "anthropic/claude-sonnet-5": {"label": "Claude Sonnet 5", "vision": True},
    "anthropic/claude-haiku-4-5": {"label": "Claude Haiku 4.5", "vision": True},
    # ── OpenAI ───────────────────────────────────────────────────────────
    "openai/gpt-5": {"label": "GPT-5", "vision": True},                        # frontier OpenAI
    "openai/gpt-4o-mini": {"label": "GPT-4o mini", "vision": True},            # cheap OpenAI
    # ── Google ───────────────────────────────────────────────────────────
    "gemini/gemini-2.5-pro": {"label": "Gemini 2.5 Pro", "vision": True},  # frontier Google reasoning
    "gemini/gemini-3.5-flash-lite": {"label": "Gemini 3.5 Flash Lite", "vision": True},  # the Google lane (fast/cheap)
    # ── DeepSeek ─────────────────────────────────────────────────────────
    # `deepseek-chat` is an ALIAS that points at DeepSeek's current chat model
    # (V4 Flash as of 2026-08-21 — see the `_BILLING_RATES` note). The version
    # is real, it is just not in the id, so the label carries what the alias
    # resolves to today. When DeepSeek repoints the alias, update this label:
    # it is the only place the member learns which model actually ran.
    "deepseek/deepseek-chat": {"label": "DeepSeek V4 Flash", "vision": False},
    # ── xAI ──────────────────────────────────────────────────────────────
    # A genuinely new price/context point, not a duplicate: $2/$6 sits between
    # Haiku and Sonnet, with a 500k window. ⚠️ xAI prices by PROMPT LENGTH
    # (≥200k doubles to $4/$12) and `_BILLING_RATES` is flat — the rate row
    # carries the ≥200k tier deliberately. See the note there.
    "xai/grok-4.6": {"label": "Grok 4.6", "vision": True},
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
        "label": "Claude Haiku 4.5 (dated)", "vision": True, "retired": True,
    },
    # Superseded by gemini-3.5-flash-lite (same list price, higher intelligence
    # and throughput — Google's own upgrade notice, 2026-08-13). RETIRED rather
    # than deleted: this row is the TURN-TIME whitelist for every lane already
    # pinned to it, and a lane's engine is what ACTUALLY ran (ADR-559 D2).
    "gemini/gemini-2.5-flash": {
        "label": "Gemini 2.5 Flash", "vision": True, "retired": True,
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
# Tool surface (ADR-411 D3) — the file + folder verbs, registry definitions converted
# ---------------------------------------------------------------------------

#: The lane tool allowlist — the SEVEN file verbs. A helper is hands on the
#: filesystem — no entity verbs, no Schedule, no DispatchSpecialist, no
#: platform tools.
#:
#: ⭐ THE FILE-VERB SET IS ONE SET, WHOEVER HOLDS IT (2026-08-21).
#: `DeleteFile` + `MoveFile` were added here because their ABSENCE was the
#: anomaly, not their presence. They already shipped in CHAT_PRIMITIVES, in
#: FREDDIE_PRIMITIVES, and — as `delete` / `move` — on the MCP interop surface
#: (ADR-543/545). So a foreign LLM connected over MCP could delete a file in
#: the member's workspace while the member's OWN lane could not, and the lane
#: said so out loud ("my available file tools do not include a file deletion
#: primitive"). One surface silently narrower than the other two is a
#: coherence bug, not a safety posture.
#:
#: The safety argument was already settled by the verbs themselves (ADR-337):
#: deletion is a VIEW change, not information loss — an attributed tombstone
#: retains the chain, ListRevisions/ReadRevision still resolve the path, and
#: restore is ReadRevision + WriteFile (ADR-209 D7). Governance-locked paths
#: refuse. FREDDIE_PRIMITIVES says it plainly: *hygiene without delete/move is
#: a duty without hands*. That is as true of a member's lane as of the steward.
#:
#: ⭐ THE FOLDER GRAIN (2026-08-21, same day, one level up).
#: `DeleteFolder` + `MoveFolder` followed for the identical reason: the fan-out
#: EXISTED (`services/folder_organize.py`, shipped `360ea4c`) and only the Files
#: surface could reach it. A member asked their lane to delete a folder, was
#: told the primitives "only operate file-by-file", and was advised to run
#: `rm -rf` in a terminal — which would not have touched the files at all, since
#: the substrate is Postgres, not disk. ADR-337 named this failure in advance,
#: in the passage ruling out a `Bash` primitive: *"it is also why missing verbs
#: hurt so much here — there is no shell escape hatch — which argues for
#: COMPLETING THE VERB SET, not adding the hatch."*
#:
#: No extra ceremony in front of them, deliberately. `trash_folder` writes one
#: attributed archive revision PER FILE — nothing is removed, the group restores
#: as ONE unit, locked children are refused and REPORTED. That makes it safer
#: than the `rm -rf` the model reached for, and safer than `WriteFile`, which
#: can truncate content and flows freely. Gating the safest destructive verb
#: while the lossy one runs unimpeded would be incoherence, not caution.
#:
#: Uniform, never per-Agent — ADR-467 D4 holds exactly as written: capability
#: is not a character trait, and a per-row `tools` field was a bug factory with
#: no safety payoff. This is a uniform addition to the one set every lane reads.
LANE_TOOL_NAMES = (
    "ReadFile", "WriteFile", "EditFile", "DeleteFile", "MoveFile",
    "DeleteFolder", "MoveFolder", "Restore",
    "SearchFiles", "ListFiles",
)

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
#: `MoveFile` (2026-08-21) lands an attributed revision at its DESTINATION, so
#: the member should see the file where it now lives — which is why
#: `artifact_path_from` reads `new_path` for it, not `path` (the move's result
#: carries BOTH, and `path` is the source that no longer exists).
#:
#: ⚠️ `DeleteFile` is deliberately NOT here. It lands a tombstone revision, but
#: an artifact card is a DEEP LINK to a file to open — and after a successful
#: delete there is nothing at that path to open. Carding it would render a dead
#: link at the exact moment the member most needs the transcript to be honest.
#: The delete still shows: `toolLabels` prints "deleted a file", and the
#: revision chain remains walkable via history. The rule this set encodes is
#: "the member should SEE what their lane MADE"; a deletion is not a thing made.
#: `MoveFolder` is NOT here despite landing revisions: its result names a
#: FOLDER, and an artifact card deep-links a FILE to open. Carding the folder
#: root would hand the member a link to something the viewer cannot render.
#: `DeleteFolder` is absent for the stronger form of the same reason
#: (`DeleteFile`'s): after the fan there is nothing at that path at all.
LANE_ARTIFACT_VERBS = (
    "WriteFile", "EditFile", "MoveFile", "GenerateImage",
)


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
    # MoveFile's result carries BOTH paths, and `path` is the SOURCE — which no
    # longer exists once the move succeeds. The card must deep-link where the
    # file now lives, or it points at a tombstone (2026-08-21).
    if name == "MoveFile":
        dst = result.get("new_path")
        if isinstance(dst, str) and dst:
            return dst
    path = result.get("path")
    return path if isinstance(path, str) and path else None


#: The lane tools whose ARGUMENTS carry a subject worth showing mid-stream, and
#: which argument names it. A streaming step reads "Reading Documents/memo.md"
#: rather than a bare "Reading files in your workspace" — the member can see
#: WHICH file their colleague touched while the turn is still running, which is
#: exactly when it is cheapest to interrupt a wrong one.
#:
#: ⚠️ ARGUMENTS, not results — deliberately, and this is the one place in the
#: module where that is the right source. `artifact_path_from` reads the RESULT
#: because a card is a deep link that must not point at a file that never landed.
#: A step row makes the weaker claim ("this is what was asked for"), and it is
#: emitted BEFORE the call runs, when no result exists yet. A failed call still
#: leaves an honest row: the subject is what was attempted.
#:
#: Order matters within a tuple: the first key present wins. `MoveFile` names
#: its DESTINATION when it has one, mirroring `artifact_path_from`'s rule that
#: a move is read where the file ends up.
_TOOL_SUBJECT_KEYS: dict = {
    "ReadFile": ("path",),
    "WriteFile": ("path",),
    "EditFile": ("path",),
    "DeleteFile": ("path",),
    "MoveFile": ("new_path", "destination", "path"),
    "DeleteFolder": ("path",),
    "MoveFolder": ("new_path", "destination", "path"),
    "Restore": ("path",),
    "ListFiles": ("path", "directory"),
    "SearchFiles": ("query",),
    "QueryKnowledge": ("query",),
    "WebSearch": ("query",),
    "GenerateImage": ("prompt",),
    "platform_slack_get_channel_history": ("channel", "channel_id"),
    "platform_notion_search": ("query",),
    "platform_notion_get_page": ("page_id",),
    "platform_github_get_issues": ("repo", "repository"),
    "platform_github_get_repo_metadata": ("repo", "repository"),
    "platform_github_get_readme": ("repo", "repository"),
    "platform_github_get_releases": ("repo", "repository"),
}

#: A subject is a LABEL, not a payload. Long free text (a search query, an image
#: prompt) is clipped here rather than in the renderer: the cap is a property of
#: what we are willing to put on the wire, and a client-side cap would still have
#: shipped the whole string to the browser.
_SUBJECT_MAX = 120


def tool_subject_from(name: str, arguments: Any) -> Optional[str]:
    """The one short human-readable subject for a tool call, or None.

    Pure. Used only for DISPLAY (the streaming step row) — never for dispatch,
    authorization, or attribution. Returning None is always safe: the row falls
    back to the verb alone, which is what every tool without a meaningful
    subject (`ListFiles` at the root, `list_integrations`) should read as.

    Never returns the raw argument dict. Only the ONE named key is exposed, so
    a tool argument we did not intend to surface cannot reach the client just
    because a future primitive gained a field.
    """
    keys = _TOOL_SUBJECT_KEYS.get(name)
    if not keys or not isinstance(arguments, dict):
        return None
    for key in keys:
        value = arguments.get(key)
        if isinstance(value, str) and value.strip():
            subject = value.strip()
            return subject if len(subject) <= _SUBJECT_MAX else subject[: _SUBJECT_MAX - 1] + "…"
    return None


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


def turn_has_reach(app: Optional[str], artifact_path: Optional[str],
                   derive_recipe: Optional[str]) -> bool:
    """Whether THIS turn carries the member's turn-reach surface (ADR-585).

    The principal-presence cut line, derived from the turn's own shape: only
    the OPEN chat turn — no app binding, no bound artifact, no derive recipe —
    is the member present, driving, wielding their own connections. App lanes
    and derive turns are workspace-disciplined (landed files only), the same
    as agents. Pure; both the tool assembly and the frame prose derive from
    it with the same arguments, so they cannot disagree.
    """
    from services.turn_reach import is_turn_reach_enabled

    return (is_turn_reach_enabled()
            and not app and not artifact_path and not derive_recipe)


def reach_platforms_for(client: Any, user_id: str, workspace_id: Optional[str],
                        agent: Optional[str], turn_reach: bool) -> Optional[tuple]:
    """The platforms THIS turn may reach, narrowed by the being's opt-in.

    ADR-612 D3. None = not scoped (every reachable platform) — the load-bearing
    default: an opt-in that defaulted to "nothing" would silently strip tools
    from every existing lane the day it deployed.

    Resolved ONCE per turn and handed to the payload, the allowlist and the
    frame prose, because ADR-585's rule is that all three derive from one
    computation or they disagree and ship a lie (the Scout bug).

    Never raises: a lookup failure degrades to "not scoped", never to
    "nothing allowed" — a transient DB error must not look like a scope the
    member never set.
    """
    if not turn_reach or not agent:
        return None
    try:
        from services.agent_connectors import allowed_platforms, opt_in_for
        from services.turn_reach import TURN_REACH_PLATFORMS
        from services.workspace_context import effective_workspace_id

        ws = effective_workspace_id(user_id, workspace_id)
        if not ws:
            return None
        opt_in = opt_in_for(client, ws, user_id, agent)
        if opt_in is None:
            return None
        return allowed_platforms(TURN_REACH_PLATFORMS, opt_in)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[LANE] reach opt-in lookup failed for %s: %s",
                       agent, exc)
        return None


def lane_tool_names(turn_reach: bool = False,
                    reach_platforms: Optional[tuple] = None) -> tuple:
    """THE lane's tool-name set: the file + folder verbs + the uniform reads
    (ADR-467 D4). One set, every lane, every Agent.

    ⚠️ SINGULAR SOURCE. Three things must agree about which tools a turn has:
    the DECLARED payload the model receives (`lane_tools_openai`), the EXECUTION
    allowlist the tool loop dispatches against, and the PROMPT prose that tells
    the model what it holds. When they were computed separately they disagreed
    and shipped a bug (Scout's declared-but-undispatchable tools, `5ba26e1`);
    when the set varied per Agent, the variance itself was the bug surface
    (ADR-467 §1). This is the one computation all three read.

    ADR-585: `turn_reach` (the `turn_has_reach` fact, derived per turn from
    the turn's own shape — never per Agent) appends the member's read-only
    platform reach surface. All three consumers derive it from the same
    turn facts, so the D4 agreement holds with the flag on or off.
    """
    if turn_reach:
        from services.turn_reach import turn_reach_tool_names

        return (LANE_TOOL_NAMES + LANE_SURFACE_EXTRA
                + turn_reach_tool_names(reach_platforms))
    return LANE_TOOL_NAMES + LANE_SURFACE_EXTRA


def lane_tools_openai(turn_reach: bool = False,
                      reach_platforms: Optional[tuple] = None) -> list[dict]:
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
    from services.primitives.folder import (
        DELETE_FOLDER_TOOL,
        MOVE_FOLDER_TOOL,
        RESTORE_TOOL,
    )
    from services.primitives.workspace import (
        DELETE_FILE_TOOL,
        EDIT_FILE_TOOL,
        LIST_FILES_TOOL,
        MOVE_FILE_TOOL,
        QUERY_KNOWLEDGE_TOOL,
        READ_FILE_TOOL,
        SEARCH_FILES_TOOL,
        WRITE_FILE_TOOL,
    )

    by_name = {
        t["name"]: t
        for t in (READ_FILE_TOOL, WRITE_FILE_TOOL, EDIT_FILE_TOOL,
                  DELETE_FILE_TOOL, MOVE_FILE_TOOL,
                  DELETE_FOLDER_TOOL, MOVE_FOLDER_TOOL, RESTORE_TOOL,
                  SEARCH_FILES_TOOL, LIST_FILES_TOOL,
                  QUERY_KNOWLEDGE_TOOL, WEB_SEARCH_PRIMITIVE,
                  LIST_INTEGRATIONS_TOOL, GENERATE_IMAGE_TOOL)
    }
    if turn_reach:
        # ADR-585: the member's read-only reach surface, schemas from the
        # provider rosters themselves (turn_reach_tool_defs errors on a
        # missing schema — same fail-loud rule as below).
        from services.turn_reach import turn_reach_tool_defs

        by_name.update({t["name"]: t
                        for t in turn_reach_tool_defs(reach_platforms)})
    names = lane_tool_names(turn_reach, reach_platforms)
    missing = [n for n in names if n not in by_name]
    if missing:
        raise ValueError(
            f"lane surface names {missing} have no tool schema — a surface "
            "addition must land its schema in the same edit (ADR-467 D4)"
        )
    return [_anthropic_to_openai_tool(by_name[n]) for n in names]


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

{connector_reach_section}

## Format discipline
{format_discipline}
{cast_section}{mandate_section}{posture_section}"""


#: ADR-495 D3 — WHO ELSE is in this conversation. Absent before 2026-08-13, and
#: its absence was a live defect rather than a missing nicety: a member typed
#: "@lisa can you hear me" and the Agent answered "there's no agent by that
#: name active in this session or workspace that I can see" — TRUE from inside
#: a frame that named exactly two entities, itself and the member. The room had
#: three participants and the prompt could not say so.
#:
#: Empty for a cast of one (the overwhelmingly common case), so a solo
#: conversation's frame is byte-identical to before.
_CAST_SECTION = """
## Who else is here
This conversation has more than the two of you in it:
{roster}
One reply per turn, and this turn is yours — {addressing_note} You are not
speaking for the others and must not answer as them or invent what they said.
If the member wants one of them, they address them by name (`@name`) and that
member answers the next turn; you may suggest it when their question is better
aimed elsewhere.
"""


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


def _build_cast_section(
    client: Any,
    user_id: str,
    cast: list[dict],
    *,
    responder: Optional[str] = None,
    reason: Optional[str] = None,
) -> str:
    """The "who else is here" block, or "" for a cast of one.

    SPECIES-BLIND (ADR-495 D3): humans and Agents are listed the same way, in
    join order, because the roster answers "who is in this room" — a question
    that does not care what kind of participant you are. The only asymmetry is
    the one the substrate already carries: an Agent has a name, a human has a
    label.

    Best-effort throughout. A roster that cannot be read yields "", which is
    exactly the pre-2026-08-13 frame — a conversation must never fail to run
    because the cast was unreadable.
    """
    try:
        others = [
            p for p in cast
            if not (p.get("member_kind") == "agent" and p.get("agent_slug") == responder)
        ]
        if not others:
            return ""

        lines: list[str] = []
        for p in others:
            if p.get("member_kind") == "agent" and p.get("agent_slug"):
                # ADR-599: kernel resolution only — a deleted colleague's cast
                # row falls back to its slug label below, honestly.
                from services.agents_registry import resolve_agent
                character = resolve_agent(p["agent_slug"]) or {}
                name = character.get("name") or p["agent_slug"]
                blurb = (character.get("blurb") or "").strip()
                lines.append(f"- {name} — {blurb}" if blurb else f"- {name}")
            elif p.get("principal_id"):
                label = (p.get("display_name") or p.get("email") or "").strip()
                lines.append(f"- {label} (a person)" if label else "- another person")
        if not lines:
            return ""

        note = (
            "the member addressed you."
            if reason == "addressed"
            else "you are answering because you spoke last here."
            if reason == "last_responder"
            else "no one was addressed by name, so it falls to you."
        )
        return _CAST_SECTION.format(roster="\n".join(lines), addressing_note=note)
    except Exception as exc:  # noqa: BLE001 — never fail a turn over the roster
        logger.warning("[LANE] cast section unavailable: %s", exc)
        return ""


def _seed_line(seed: Optional[dict]) -> str:
    """ADR-579 D7 — the gesture, rendered: what the member CLICKED.

    The deliberate half of "sees what the member sees" (focus is the ambient
    half): a door named its target, typed, and this line hands the colleague
    that target as the turn's subject. Same register as the focus lines,
    same clip-honesty rule (a truncated excerpt says so)."""
    if not seed:
        return ""
    verb = (seed.get("verb") or "").strip()
    phrase = {
        "ask": "asked about",
        "rewrite": "clicked Rewrite on",
        "check": "clicked Check on",
    }.get(verb)
    if not phrase:
        return ""
    label = (seed.get("label") or "").strip()
    bid = (seed.get("block_id") or "").strip()
    ex = (seed.get("excerpt") or "").strip()
    page = seed.get("page_index")
    if label == "selection":
        noun = "the selection"
    elif page is not None and not bid:
        noun = f"{label or 'slide'} {page + 1}"
    else:
        noun = f"the {label or 'content'} block"
    ident = f" (id {bid})" if bid else ""
    clipped = ex[:80].strip()
    # ADR-609 D4 — one marker, never two (see build_focus_line's _quoted).
    _suffix = (
        "" if clipped.endswith("…")
        else "…" if len(ex.strip()) > len(clipped) else ""
    )
    quoted = f' — "{clipped}{_suffix}"' if clipped else ""
    line = (
        f"- The member's gesture: they {phrase} {noun}{ident}{quoted}."
        " That is this turn's target — act on it, never a copy elsewhere."
    )

    # ADR-609 D3 — hand over the ADDRESS, not just the name of the thing.
    # Until this clause the target was described and the colleague had to
    # re-find it by string search against a quoted PREFIX; an anchored edit
    # acts on the member's actual selection with nothing to reconstruct.
    rng = seed.get("range") if isinstance(seed.get("range"), dict) else None
    if rng and isinstance(rng.get("start"), int) and isinstance(rng.get("end"), int):
        line += (
            f" To change it, pass anchor={{'start': {rng['start']},"
            f" 'end': {rng['end']}}} to EditFile — that span IS the selection,"
            " so the quoted text above (a clipped prefix) is not its extent."
        )
    elif bid:
        line += (
            f" To change it, pass anchor={{'block_id': '{bid}'}} to EditFile"
            " — the edit is then confined to that block."
        )
    return line


def _compose_focus_section(
    artifact_path: Optional[str],
    artifact: str,
    focus: Optional[dict],
    seed: Optional[dict] = None,
) -> str:
    """The member's place AND gesture, rendered at ONE kernel site (ADR-606
    D1; the ADR-579 D7 gesture rides the same site — deliberate beside
    ambient, one home).

    BOUND lane: the ADR-522 grain line — but only when the declaration names
    the bound artifact or names nothing (ADR-606 D2). The binding is the
    authority on what this desk is about; a focus carried in by the shell's
    recency fallback that names a DIFFERENT file renders as silence, because
    narrating another file's selection into this desk's frame would aim the
    colleague at the wrong object.

    UNBOUND lane: the situational default-target line, verbatim from the
    2026-08-12 completion (the fundraiser-copy incident: a general chat lane
    received the member's declared focus, said nothing about it, and meaning-
    placed file work the member expected to watch land on their open canvas).
    """
    def _rel(p: str) -> str:
        return p[len("/workspace/"):] if p.startswith("/workspace/") else p

    lines: list[str] = []

    # The GESTURE first (deliberate beats ambient) — same binding-authority
    # guard as the focus: a seed naming a different file than the binding is
    # silence, not a redirected target.
    if seed:
        spath = _rel((seed.get("path") or "").strip())
        if not (artifact_path and spath and spath != _rel(artifact_path)):
            sline = _seed_line(seed)
            if sline:
                lines.append(sline)

    if focus:
        fpath = _rel((focus.get("path") or "").strip())
        if artifact_path:
            if not (fpath and fpath != _rel(artifact_path)):
                from services.authoring import build_focus_line, extract_template

                template = extract_template(artifact) or "document"
                fline = build_focus_line(focus, template)
                if fline:
                    lines.append(fline)
        else:
            _flabel = (focus.get("label") or "").strip()
            _fapp = (focus.get("app") or "a surface").strip()
            _fdesc = fpath or _flabel
            if _fdesc:
                lines.append(
                    f"- The member is looking at: {_fapp} — {_fdesc}."
                    " When they ask for changes to a document or file without"
                    " naming one, they mean THIS one — edit it in place; never"
                    " a copy elsewhere."
                )

    return "\n" + "\n".join(lines) + "\n" if lines else ""


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
    seed: Optional[dict] = None,
    app: Optional[str] = None,
    cast: Optional[list[dict]] = None,
    responder_reason: Optional[str] = None,
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


    # The tool line names the lane surface (ADR-467 D4). Derived from the same
    # `lane_tool_names` + the same turn facts the payload and the loop's
    # allowlist read, so the prose can never claim a surface the model wasn't
    # handed (the Scout bug's prose half). ADR-585: the reach fact re-derives
    # here from the SAME arguments run_lane_turn passed.
    _reach = turn_has_reach(app, artifact_path, derive_recipe)
    # ADR-612 D3 — the SAME narrowing the payload and allowlist got. Re-derived
    # from the same arguments rather than passed, which is the ADR-585 rule
    # this file already follows for `_reach` itself: two derivations from one
    # function agree; two hand-maintained values drift (the Scout bug).
    _reach_plats = reach_platforms_for(client, user_id, None, agent, _reach)
    tools_line = " · ".join(lane_tool_names(_reach, _reach_plats))

    # ADR-585 / ADR-535 D3 — the connector edge, stated affirmatively either
    # way. Without reach the model must not infer it from the inventory; with
    # reach it must know the bound (the MEMBER's own connections, read-only,
    # transient) rather than guess at more.
    if _reach and _reach_plats is not None and not _reach_plats:
        # ADR-612 D3 — an explicit empty opt-in. The member scoped this one to
        # NO platform, so it holds no platform_* tool at all. Said plainly:
        # the honest-absence branch below would tell it connections are
        # unreadable in general, which is false and would have it offering
        # remedies ("connect in Settings") for a limit the member set here.
        connector_reach_section = (
            f"You have no platform reach in this workspace: {member} scoped "
            "you to no connections. list_integrations still tells you what "
            "THEY have connected, and you may name it — you simply cannot "
            "read through any of it. If they want that content here, say so "
            "plainly: they can widen your connections on your agent page, "
            "paste it, or drop the files into the commons."
        )
    elif _reach:
        # Unscoped (None) and scoped-to-a-subset read differently, and the
        # difference must be TRUE: claiming "the member scoped you to these"
        # when nobody scoped anything would have the model report a limit that
        # does not exist.
        if _reach_plats is None:
            _scope_line = (
                "CONNECTED (Notion, Slack, GitHub) and whether each is "
                "active. Call it instead of guessing. "
            )
        else:
            _plat_label = ", ".join(p.capitalize() for p in _reach_plats)
            _scope_line = (
                f"CONNECTED and whether each is active. YOU can read through "
                f"{_plat_label} — that is what {member} scoped you to, and "
                "the platform_* tools you hold are only for those. Call "
                "list_integrations instead of guessing. "
            )
        connector_reach_section = (
            f"list_integrations tells you which platforms {member} has "
            + _scope_line
            + "The platform_* tools read through "
            f"{member}'s OWN connections — theirs only, granted by their "
            "authorization on each platform, read-only. What you fetch lives "
            "in this conversation and dies with it; if it is worth keeping, "
            "save it to the commons with WriteFile so it is attributed and "
            "citable. A platform they have not connected answers honestly "
            "that it is not connected — offer Connect in Settings, or paste."
        )
    else:
        connector_reach_section = (
            f"list_integrations tells you which platforms {member} has "
            "CONNECTED (Notion, Slack, GitHub) and whether each is active. "
            "Call it instead of guessing — never tell them a connector is "
            "absent without looking. But seeing a connection is not having "
            "it: you can name what they bound, and you CANNOT read through "
            "it. There is no tool here that opens a Notion page or a Slack "
            "channel. If they want that content, say so plainly and offer "
            "what you can do — they can paste it, or export and drop the "
            "files into the commons, where you read them normally."
        )

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
        # ADR-599: kernel characters only — the member-agent machinery
        # (manifests, tone, skills) is deleted; a resident's character is
        # self-contained.
        from services.agents_registry import build_agent_posture
        # ADR-562 D6 — the APP's name for its resident. DERIVED from the
        # artifact's own `data-template`, never stored on the lane: the app is
        # a fact about the DOCUMENT, so deriving it means a lane can never
        # carry a stale label for an artifact that changed hands. Empty for an
        # unbound lane (no artifact → no app → the character's own name).
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
        posture_section += build_agent_posture(agent, as_name=_as_name)
    if artifact_path:
        # ADR-606 D3 — the JOB overlay is the APP's declaration, resolved
        # through the same registry door as its resident (ADR-562). The old
        # per-app `if/elif` chain here (ADR-567 D4 → 569 D6 → 571 D4, one
        # branch per app) is deleted: a kernel chokepoint that must be hand-
        # edited per app is how Strings' and Text's focus got dropped on the
        # floor. `artifact` was read once at the top of the frame — still the
        # CURRENT head, still derived-never-stored.
        # `+=`, NOT `=`. This was an assignment until 2026-07-16, which was
        # latent-only because no bound lane carried an agent — an `=` here
        # would silently eat the colleague's character and leave only the
        # job. Every binding APPENDS to the character.
        import services.apps  # noqa: F401  (registration side-effect)
        from services.authoring import posture_for_app, studio_pane_posture

        _builder = posture_for_app(app) or studio_pane_posture
        posture_section += (
            "\n" + _builder(client, user_id, artifact_path, artifact) + "\n"
        )

    # ADR-606 D1 — the member's PLACE renders at this ONE kernel site, for
    # every lane. It is a fact about the MEMBER, not about the character or
    # the job wearing the turn (the ADR-495 cast-section reasoning) — rendered
    # inside one app's posture builder it decayed one branch at a time, with
    # Strings declaring focus the server dropped and Text never rendering any.
    posture_section += _compose_focus_section(artifact_path, artifact, focus, seed)

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

    # ADR-495 D3 — the room, named. Composed here (not in the posture) because
    # it is a fact about the CONVERSATION, not about the character wearing the
    # turn: the same roster is true whichever cast member is answering.
    cast_section = _build_cast_section(
        client, user_id, cast or [], responder=agent, reason=responder_reason,
    )

    return _CONVENTIONS_FRAME.format(
        model_label=label,
        member=member,
        model=label,
        cast_section=cast_section,
        commons_contract=PARTICIPANT_COMMONS_CONTRACT,
        attribution_rule=PARTICIPANT_ATTRIBUTION_RULE,
        citation_rule=PARTICIPANT_CITATION_RULE,
        read_before_write=PARTICIPANT_READ_BEFORE_WRITE,
        filesystem_model=PARTICIPANT_FILESYSTEM_MODEL,
        format_discipline=PARTICIPANT_FORMAT_DISCIPLINE,
        tools_line=tools_line,
        connector_reach_section=connector_reach_section,
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
    # ADR-579 D7 — what the member CLICKED this turn (the gesture target);
    # stamped by the route, rendered here. None → byte-identical.
    seed: Optional[dict] = None,
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
    # JOB overlay only (strings → the standing-work desk posture). None →
    # byte-identical.
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
    # ADR-585: the reach fact derives from the turn's own shape; the frame
    # prose re-derives it from the SAME arguments inside build_lane_conventions.
    _reach = turn_has_reach(app, artifact_path, derive_recipe)
    # ADR-612 D3 — resolved ONCE and handed to all three consumers below
    # (payload, allowlist, and the frame prose via build_lane_conventions).
    _reach_plats = reach_platforms_for(
        auth.client, auth.user_id, getattr(auth, "workspace_id", None),
        agent, _reach)
    tools = lane_tools_openai(_reach, _reach_plats)
    _allowed = lane_tool_names(_reach, _reach_plats)
    system = build_lane_conventions(
        auth.client, auth.user_id, model=model, member_label=member_label,
        artifact_path=artifact_path,
        derive_recipe=derive_recipe, derive_source=derive_source,
        agent=agent,
        focus=focus,
        seed=seed,
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
    # ADR-579 D7 — the gesture target; see ``run_lane_turn``.
    seed: Optional[dict] = None,
    # ADR-460 D4 — the Agent slug; see ``run_lane_turn``.
    agent: Optional[str] = None,
    # W0 / ADR-457 D8 — the falsifier join key; see ``run_lane_turn``.
    session_id: Optional[str] = None,
    # ADR-492 — the metering slug; see ``run_lane_turn``.
    ledger_slug: str = "lane",
    # ADR-567 D4 — the lane's binding app; see ``run_lane_turn``.
    app: Optional[str] = None,
    # ADR-495 D3 — the conversation's participants, so the frame can name the
    # room. Without it the Agent believes it is alone with the member and will
    # deny that a cast-mate exists (observed 2026-08-13).
    cast: Optional[list[dict]] = None,
    responder_reason: Optional[str] = None,
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
    # ADR-585: the reach fact derives from the turn's own shape; the frame
    # prose re-derives it from the SAME arguments inside build_lane_conventions.
    _reach = turn_has_reach(app, artifact_path, derive_recipe)
    # ADR-612 D3 — resolved ONCE and handed to all three consumers below
    # (payload, allowlist, and the frame prose via build_lane_conventions).
    _reach_plats = reach_platforms_for(
        auth.client, auth.user_id, getattr(auth, "workspace_id", None),
        agent, _reach)
    tools = lane_tools_openai(_reach, _reach_plats)
    _allowed = lane_tool_names(_reach, _reach_plats)
    system = build_lane_conventions(
        auth.client, auth.user_id, model=model, member_label=member_label,
        artifact_path=artifact_path,
        derive_recipe=derive_recipe, derive_source=derive_source,
        agent=agent,
        focus=focus,
        seed=seed,
        app=app,
        cast=cast,
        responder_reason=responder_reason,
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
            # The subject rides with the name (never the raw argument dict —
            # `tool_subject_from` exposes one named key). A step row that can
            # say WHICH file is being read is legible mid-turn; the bare verb
            # is the honest fallback when no key applies.
            yield ("tool", {"name": name, "subject": tool_subject_from(name, tc.get("arguments"))})
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
