"""
Composio Driver — external-action executor behind YARNNN's primitive contract.

SPIKE STATUS (ADR-353, Proposed): this module is the "consume capability below"
half of the stack axis (positioning-discourse §6.6). It is wired behind the
``COMPOSIO_DRIVER_ENABLED`` flag + a per-provider allowlist (Slack only in the
spike) in ``services.platform_tools.handle_platform_tool``. Default OFF. The
first-party clients (``integrations/core/*_client.py``) remain the live path and
are NOT deleted — deletion is a separate, post-ratification decision (ADR-353
§6/§12).

What this module IS (ADR-353 §2–§3):
  - A *mechanical execution layer only*. It carries bytes to/from an external
    platform via Composio. It is one implementation behind a swappable driver
    interface (``execute``).

What this module is NOT (hard invariants — ADR-353 §3 + the spike charter):
  - NOT a gate. The ADR-307 permission gate (``resolve_permission``) runs in
    ``execute_primitive`` BEFORE ``handle_platform_tool`` is ever reached, keyed
    on the *tool name* (``is_consequential_platform_tool``) — unchanged by which
    driver executes. Composio is an executor behind the gate, never a gate.
  - NOT a writer of substrate. Attribution stays in the kernel: the caller of
    ``handle_platform_tool`` authors the result via ``write_revision`` as
    ``agent:{slug}`` / ``system:*`` exactly as today. Composio never reaches the
    substrate.
  - NOT a token custodian. Phase 1 (ADR-353 §7): YARNNN fetches the per-user
    token from ``platform_connections``, decrypts via the Fernet
    ``TokenManager``, and passes plaintext to ``execute(..., token=...)`` for the
    single call. Composio holds ZERO tenant auth state — it executes with the
    bearer token we inject per call (``custom_auth_params``). This makes the
    multi-tenant isolation property (ADR-353 §12.6) structural: there is no
    Composio-stored credential to mix across users.

Consumption protocol (ADR-353 §12 spike decision): Composio's REST API
(``POST /api/v3/tools/execute/{tool_slug}``), NOT its MCP interface. The
swappability the ADR demands is provided by THIS module's interface, not by the
wire protocol underneath — so we take the simpler, stateless, synchronous REST
call and keep the MCP surface (Composio's agent-facing routing/learning layer,
the part §10 says never to consume) out of the path entirely.

No silent success (CLAUDE.md Pitfall #4): every Composio failure mode — non-2xx
HTTP, ``successful: false`` in the body, timeout, missing token, unmapped verb —
maps to ``{"success": False, "error": "..."}``. The driver NEVER returns
``success: True`` on a failed action.

Swappability (ADR-353 §12.5): reverting is a config change (flag OFF), not a
refactor. Switching aggregators means writing a sibling module with the same
``execute`` signature; ``handle_platform_tool`` is the only call site.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration (env)
# =============================================================================

COMPOSIO_API_BASE = os.getenv("COMPOSIO_API_BASE", "https://backend.composio.dev")
_COMPOSIO_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


def _api_key() -> Optional[str]:
    """The Composio account API key (env). Distinct from the per-user platform
    token: this authenticates YARNNN-the-account to Composio; the per-user token
    is injected per call via ``custom_auth_params`` (Phase 1, ADR-353 §7).

    Render parity (ADR-353 §8): belongs on yarnnn-api + yarnnn-unified-scheduler,
    NOT mcp-server / render. Do not set production env in the spike.
    """
    return os.getenv("COMPOSIO_API_KEY")


# =============================================================================
# Verb → Composio action-slug map (the kernel-stable seam)
# =============================================================================
#
# YARNNN's tool *names* are the kernel contract (ADR-353 §5). Composio's action
# *slugs* are an implementation detail of this driver — and an unstable one:
# the spike found the same Slack chat.postMessage action referred to as
# SLACK_SEND_MESSAGE / SLACK_CHAT_POST_MESSAGE / SLACK_SENDS_A_MESSAGE_TO_A_
# SLACK_CHANNEL across Composio doc versions. Pinning the slug HERE (one table,
# one place to update on Composio drift) is the swappability discipline: the
# kernel never sees a Composio slug.
#
# `verb` is the YARNNN tool suffix after `platform_{provider}_` — i.e. the
# `tool` value `handle_platform_tool` parses out (e.g. "send_to_channel").
#
# SPIKE SCOPE: Slack only is in the allowlist. Notion/GitHub slugs are recorded
# here from the coverage check (ADR-353 §12.1) so the matrix is grounded in
# code, but they are NOT wired (the allowlist gates that) until per-platform
# parity is proven. Capital family (trading/commerce) is deliberately ABSENT —
# out of scope per ADR-353 §11.
_COMPOSIO_ACTION_MAP: dict[str, dict[str, str]] = {
    "slack": {
        # Reads — confirmed against the LIVE Composio tool-enum (2026-06-22).
        "list_channels": "SLACK_LIST_ALL_CHANNELS",
        "get_channel_history": "SLACK_FETCH_CONVERSATION_HISTORY",
        # External-write family (gated upstream by ADR-307 before reaching here).
        # LIVE slug is SLACK_CHAT_POST_MESSAGE — the spike's first guess
        # (SLACK_SEND_MESSAGE, from a stale doc) does NOT exist in the live
        # catalog. This correction is the slug-instability finding (ADR-353 §10)
        # paying off: the live round-trip caught it before any default flip.
        "send_message": "SLACK_CHAT_POST_MESSAGE",
        "send_to_channel": "SLACK_CHAT_POST_MESSAGE",
    },
    # ── NOT wired in the spike (recorded from coverage check, ADR-353 §12.1) ──
    "notion": {
        "search": "NOTION_SEARCH_NOTION_PAGE",
        "get_page": "NOTION_GET_PAGE_MARKDOWN",
        "create_page": "NOTION_CREATE_NOTION_PAGE",
        "append_block": "NOTION_APPEND_TEXT_BLOCKS",
        "create_comment": "NOTION_CREATE_COMMENT",
    },
    "github": {
        "list_repos": "GITHUB_LIST_REPOSITORIES_FOR_THE_AUTHENTICATED_USER",
        "get_issues": "GITHUB_LIST_REPOSITORY_ISSUES",
        "get_repo_metadata": "GITHUB_GET_A_REPOSITORY",
        "get_readme": "GITHUB_GET_A_REPOSITORY_README",
        "get_releases": "GITHUB_LIST_RELEASES",
    },
    # ADR-353 §15a — Reddit (live-confirmed slugs, tool-enum 2026-06-22).
    # WIRED (in the allowlist): alpha-author / yarnnn-author publishing.
    "reddit": {
        # External-write family (gated upstream by ADR-307 before reaching here).
        "submit_post": "REDDIT_CREATE_REDDIT_POST",
        # The perceive read — comments → audience_signal as observation (§14).
        "get_post_comments": "REDDIT_RETRIEVE_POST_COMMENTS",
    },
}


# =============================================================================
# Payload adapters (YARNNN tool_input → Composio arguments)
# =============================================================================
#
# YARNNN's tool input field names differ from Composio's argument names. Each
# adapter is pure (no I/O), returns the Composio `arguments` dict for one verb.
# Kept tiny and per-verb so drift in one verb's mapping is isolated.

def _slack_arguments(verb: str, payload: dict) -> dict:
    if verb == "list_channels":
        # Match the first-party default (public + private, exclude archived).
        return {
            "types": "public_channel,private_channel",
            "exclude_archived": True,
            "limit": payload.get("limit", 200),
        }
    if verb == "get_channel_history":
        args: dict[str, Any] = {
            "channel": payload["channel_id"],
            "limit": payload.get("limit", 50),
        }
        if payload.get("oldest"):
            args["oldest"] = payload["oldest"]
        return args
    if verb in ("send_message", "send_to_channel"):
        args = {
            "channel": payload["channel_id"],
            "text": payload["text"],
        }
        if payload.get("thread_ts"):
            args["thread_ts"] = payload["thread_ts"]
        return args
    raise _UnmappedVerb(f"slack:{verb}")


def _reddit_arguments(verb: str, payload: dict) -> dict:
    """ADR-353 §15a. Map YARNNN reddit tool_input → Composio arguments (live
    schema confirmed 2026-06-22). submit needs subreddit/title/text + kind="self"
    (text post) + flair_id (required by the action; empty string where the
    subreddit imposes no flair). get_post_comments maps post_id → `article`."""
    if verb == "submit_post":
        return {
            "subreddit": payload["subreddit"],
            "title": payload["title"],
            "text": payload["text"],
            "kind": "self",          # self = text post (vs link)
            "flair_id": payload.get("flair_id", ""),
        }
    if verb == "get_post_comments":
        # Composio's RETRIEVE_POST_COMMENTS takes `article` (the post id).
        return {"article": payload["post_id"]}
    raise _UnmappedVerb(f"reddit:{verb}")


_PAYLOAD_ADAPTERS = {
    "slack": _slack_arguments,
    "reddit": _reddit_arguments,
}


# =============================================================================
# Result adapters (Composio data → YARNNN _handle_* return shape)
# =============================================================================
#
# CRITICAL for parity (ADR-353 §12.2): the result dict MUST carry the SAME keys
# the first-party `_handle_slack_tool` returns, so every caller of
# `handle_platform_tool` (registry.execute_primitive, harvest, sync_platform_
# state) is byte-compatible regardless of driver. The first-party Slack shapes:
#   send_*            → {"ts", "channel"} (+ "message" for send_to_channel)
#   list_channels     → {"channels": [{id,name,is_private,is_archived}], "count"}
#   get_channel_hist  → {"messages": [{user,text,ts,reactions?}], "count"}

def _slack_result(verb: str, data: dict) -> dict:
    """Map Composio Slack `data` to the YARNNN result dict. Composio nests the
    raw Slack API response; we re-derive exactly the fields the first-party
    handler exposes (no extra Composio shape leaks upward)."""
    if verb in ("send_message", "send_to_channel"):
        out: dict[str, Any] = {"ts": data.get("ts"), "channel": data.get("channel")}
        return out
    if verb == "list_channels":
        raw = data.get("channels") or []
        channels = [
            {
                "id": ch.get("id"),
                "name": ch.get("name") or ch.get("name_normalized"),
                "is_private": ch.get("is_private", False),
                "is_archived": ch.get("is_archived", False),
            }
            for ch in raw
            if isinstance(ch, dict) and ch.get("id")
        ]
        return {"channels": channels, "count": len(channels)}
    if verb == "get_channel_history":
        raw = data.get("messages") or []
        normalized = []
        for msg in raw:
            if not isinstance(msg, dict):
                continue
            text = msg.get("text", "")
            if not text:
                continue
            entry: dict[str, Any] = {
                "user": msg.get("user") or msg.get("username"),
                "text": text,
                "ts": msg.get("ts"),
            }
            reactions = msg.get("reactions")
            if reactions:
                entry["reactions"] = [
                    {"name": r.get("name"), "count": r.get("count", 0)}
                    for r in reactions
                    if isinstance(r, dict)
                ]
            normalized.append(entry)
        return {"messages": normalized, "count": len(normalized)}
    raise _UnmappedVerb(f"slack:{verb}")


def _reddit_result(verb: str, data: dict) -> dict:
    """ADR-353 §15a. Re-derive a stable YARNNN result shape from Composio's Reddit
    `data` (defensive — Reddit nests under data.json.data for posts). submit_post →
    {post_id, url} (post_id feeds the later perceive read). get_post_comments →
    {comments:[{author,body,score}], count} for audience_signal."""
    if verb == "submit_post":
        # Reddit submit response: {json: {data: {id, name (t3_..), url}}}.
        json_data = ((data.get("json") or {}).get("data")) or {}
        post_id = json_data.get("name") or json_data.get("id") or data.get("name") or data.get("id")
        url = json_data.get("url") or data.get("url")
        return {"post_id": post_id, "url": url}
    if verb == "get_post_comments":
        # Comments listing — Reddit returns a listing tree; flatten top-level.
        raw = data.get("comments")
        if raw is None:
            # Fall back to common listing shapes without over-assuming structure.
            raw = data.get("children") or (data.get("data") or {}).get("children") or []
        comments = []
        for c in raw if isinstance(raw, list) else []:
            body = c.get("body") if isinstance(c, dict) else None
            if isinstance(c, dict) and isinstance(c.get("data"), dict):
                body = body or c["data"].get("body")
                author = c["data"].get("author")
                score = c["data"].get("score")
            else:
                author = c.get("author") if isinstance(c, dict) else None
                score = c.get("score") if isinstance(c, dict) else None
            if not body:
                continue
            comments.append({"author": author, "body": body, "score": score})
        return {"comments": comments, "count": len(comments)}
    raise _UnmappedVerb(f"reddit:{verb}")


_RESULT_ADAPTERS = {
    "slack": _slack_result,
    "reddit": _reddit_result,
}


class _UnmappedVerb(Exception):
    """Raised when a (provider, verb) has no Composio mapping — surfaces as a
    {success: False} error, never a silent success."""


# =============================================================================
# Driver interface
# =============================================================================

async def execute(
    provider: str,
    verb: str,
    payload: dict,
    *,
    token: str,
    user_id: str,
) -> dict:
    """Execute one external action via Composio and return the YARNNN handler
    shape.

    Args:
        provider: e.g. "slack" (the `platform_{provider}_*` segment).
        verb:     e.g. "send_to_channel" (the tool suffix).
        payload:  the YARNNN `tool_input` dict.
        token:    the per-user PLAINTEXT platform token (already decrypted by the
                  caller via TokenManager). Injected into Composio per call via
                  `custom_auth_params` — Composio stores nothing (Phase 1,
                  ADR-353 §7). This is the load-bearing isolation property.
        user_id:  the YARNNN user_id. Passed to Composio as its `user_id`
                  (Composio entity == YARNNN user_id, ADR-353 §7) — even though
                  Phase 1 injects auth per call, passing user_id keeps the entity
                  attribution consistent and prepares the Phase-2 evaluation
                  without changing the interface.

    Returns:
        {"success": bool, "result": dict | None, "error": str | None}
        — identical shape to the first-party `_handle_*_tool` functions, so
        `handle_platform_tool` routes to either path transparently.

    No silent success: any failure → success=False with a mapped error string.
    """
    api_key = _api_key()
    if not api_key:
        # Misconfiguration must be loud (Pitfall #4): never proceed as if OK.
        logger.error("[COMPOSIO] COMPOSIO_API_KEY not set — driver cannot execute %s:%s", provider, verb)
        return {"success": False, "result": None, "error": "Composio driver not configured (COMPOSIO_API_KEY missing)"}

    if not token:
        logger.error("[COMPOSIO] No platform token supplied for %s:%s", provider, verb)
        return {"success": False, "result": None, "error": f"No {provider} token available"}

    slug = _COMPOSIO_ACTION_MAP.get(provider, {}).get(verb)
    if not slug:
        logger.error("[COMPOSIO] No action mapping for %s:%s", provider, verb)
        return {"success": False, "result": None, "error": f"Unsupported action: {provider}_{verb}"}

    adapter = _PAYLOAD_ADAPTERS.get(provider)
    result_adapter = _RESULT_ADAPTERS.get(provider)
    if adapter is None or result_adapter is None:
        logger.error("[COMPOSIO] No adapters for provider %s", provider)
        return {"success": False, "result": None, "error": f"Unsupported provider: {provider}"}

    try:
        arguments = adapter(verb, payload)
    except _UnmappedVerb as e:
        return {"success": False, "result": None, "error": f"Unsupported action: {e}"}
    except KeyError as e:
        # Required input field missing — caller-shape error, surfaced loudly.
        return {"success": False, "result": None, "error": f"Missing required field: {e}"}

    url = f"{COMPOSIO_API_BASE}/api/v3/tools/execute/{slug}"
    body = {
        "user_id": user_id,
        "arguments": arguments,
        # Phase 1: inject OUR token per call. Composio executes with this bearer
        # and stores no connected-account credential for this user (ADR-353 §7).
        "custom_auth_params": {
            "parameters": [
                {"name": "Authorization", "value": f"Bearer {token}", "in": "header"},
            ],
        },
    }
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=_COMPOSIO_TIMEOUT) as client:
            resp = await client.post(url, headers=headers, json=body)
    except httpx.TimeoutException as e:
        # Reliability degradation (ADR-353 §10): surface as retryable error, not
        # a silent success. The caller / gate routes this to QUEUE/retry.
        logger.warning("[COMPOSIO] Timeout executing %s:%s — %s", provider, verb, e)
        return {"success": False, "result": None, "error": "Composio request timed out"}
    except httpx.HTTPError as e:
        logger.error("[COMPOSIO] Transport error executing %s:%s — %s", provider, verb, e)
        return {"success": False, "result": None, "error": f"Composio transport error: {e}"}

    # Non-2xx → loud failure (auth failures, rate limits, 5xx).
    if resp.status_code >= 400:
        detail = _safe_error_detail(resp)
        logger.warning(
            "[COMPOSIO] HTTP %s executing %s:%s — %s",
            resp.status_code, provider, verb, detail,
        )
        return {
            "success": False,
            "result": None,
            "error": f"Composio HTTP {resp.status_code}: {detail}",
        }

    try:
        envelope = resp.json()
    except Exception as e:
        logger.error("[COMPOSIO] Non-JSON response executing %s:%s — %s", provider, verb, e)
        return {"success": False, "result": None, "error": "Composio returned a non-JSON response"}

    # Composio envelope: {successful: bool, data: {...}, error: ..., log_id}.
    #
    # TWO success layers — BOTH must pass (confirmed against the LIVE API
    # 2026-06-22, the finding the mocks could not catch):
    #
    #   1. envelope.successful — "Composio executed the tool and got a response."
    #      This is TRUE even when the underlying platform action FAILED. A Slack
    #      send with a bad token returns HTTP 200 + successful:True + error:None,
    #      with the real failure buried at data.ok=false / data.error.
    #   2. the PLATFORM-level success flag inside `data` — for Slack this is
    #      `data.ok` (Slack's own contract; the first-party SlackAPIClient checks
    #      the same field). Trusting only `successful` would report success on a
    #      failed send — the exact Pitfall #4 / "reports success with 0 items"
    #      silent-success bug. NEVER trust the outer flag alone.
    if not envelope.get("successful", False):
        err = envelope.get("error") or "Composio action failed"
        logger.warning("[COMPOSIO] composio-level failure %s:%s — %s", provider, verb, err)
        return {"success": False, "result": None, "error": str(err)}

    data = envelope.get("data") or {}

    # Platform-level success check (layer 2). Per-provider: Slack uses `ok`.
    platform_err = _platform_level_error(provider, data)
    if platform_err is not None:
        logger.warning("[COMPOSIO] platform-level failure %s:%s — %s", provider, verb, platform_err)
        return {"success": False, "result": None, "error": platform_err}
    try:
        result = result_adapter(verb, data)
    except _UnmappedVerb as e:
        return {"success": False, "result": None, "error": f"Unsupported action: {e}"}

    out: dict[str, Any] = {"success": True, "result": result, "error": None}
    # Preserve the first-party `message` annotation on channel sends (parity).
    if verb == "send_to_channel":
        out["message"] = f"Posted to channel {result.get('channel')}"
    return out


def _platform_level_error(provider: str, data: dict) -> Optional[str]:
    """Return a human error string if the PLATFORM-level outcome inside Composio's
    `data` is a failure, else None.

    Composio's outer `successful` flag only means "the call reached the platform";
    the platform's own success contract lives in `data`. This is the layer that
    prevents silent success (confirmed live 2026-06-22). Per-provider because each
    platform signals failure differently:

      - Slack: `data.ok == false`, reason in `data.error` (matches the first-party
        SlackAPIClient, which checks the same `ok` field).
      - Reddit: a failed submit returns `data.json.errors` as a NON-EMPTY list
        (e.g. [["SUBREDDIT_NOEXIST", "...", "sr"]]) while the outer `successful`
        is still true — the same silent-success trap as Slack, different shape.

    Providers without a known nested contract return None here (outer `successful`
    is the only available signal) — those providers are not in the allowlist, so
    the conservative default never ships unverified.
    """
    if not isinstance(data, dict):
        return None
    if provider == "slack":
        # Slack always returns `ok`; absence + nonempty data is treated as ok
        # (defensive — a malformed shape falls through to the result adapter).
        if data.get("ok") is False:
            return f"Slack API error: {data.get('error', 'unknown')}"
    if provider == "reddit":
        # Reddit submit failures surface as data.json.errors (non-empty list).
        errors = ((data.get("json") or {}).get("errors")) if isinstance(data.get("json"), dict) else None
        if errors:
            # errors is a list of [CODE, message, field] triples.
            first = errors[0] if isinstance(errors, list) and errors else errors
            return f"Reddit API error: {first}"
    return None


def _safe_error_detail(resp: httpx.Response) -> str:
    """Best-effort human-readable error from a non-2xx Composio response."""
    try:
        body = resp.json()
        if isinstance(body, dict):
            return str(body.get("error") or body.get("message") or body)
        return str(body)
    except Exception:
        return (resp.text or "")[:300] or "no detail"


# =============================================================================
# Allowlist helper (the per-provider routing gate, ADR-353 spike task 4)
# =============================================================================

def driver_enabled_for(provider: str) -> bool:
    """True iff the Composio driver should execute for this provider RIGHT NOW.

    Two conditions, both required (master switch defaults OFF):
      1. COMPOSIO_DRIVER_ENABLED is truthy (the master switch + presence of
         COMPOSIO_API_KEY on yarnnn-api + yarnnn-unified-scheduler, §8).
      2. `provider` is in COMPOSIO_PROVIDER_ALLOWLIST (comma-separated env).
         Default allowlist: "slack,reddit". Slack = the live-proven reference
         (§3a); Reddit = the ADR-353 §15a publishing path (Composio-ONLY backend —
         there is no first-party reddit client, so Reddit can only work via the
         driver). Other platforms (notion/github) stay first-party unless added.

    Capital family (trading/commerce) can NEVER be enabled here even if added to
    the env allowlist — they are hard-excluded (ADR-353 §11): out of scope, and
    money-moving actions must not route through a third party.
    """
    if provider in ("trading", "commerce"):
        return False
    flag = os.getenv("COMPOSIO_DRIVER_ENABLED", "").strip().lower()
    if flag not in ("1", "true", "yes", "on"):
        return False
    allowlist = {
        p.strip().lower()
        for p in os.getenv("COMPOSIO_PROVIDER_ALLOWLIST", "slack,reddit").split(",")
        if p.strip()
    }
    return provider in allowlist
