"""
MCP Server Authentication Bridge — ADR-075 + ADR-310

Service key + per-request user identity. Service key bypasses RLS; every
query uses explicit .eq("user_id", user_id), so isolation is correct once
the right user_id flows in.

Two identity sources, in priority order (ADR-310 D4 — per-request identity):
  1. The per-request OAuth access token's user_id (the real authenticating
     user, set by YarnnnOAuthProvider.load_access_token). This is what makes
     the connector multi-user: each operator's own LLM authenticates as
     themselves and reaches their own substrate.
  2. MCP_USER_ID env var — fallback for the static-bearer path and stdio
     transport (one process = one user). The static bearer's YarnnnAccessToken
     already carries MCP_USER_ID as its user_id, so even that path flows
     through source 1; the env fallback is the last resort.

For stdio transport: one process = one user (MCP_USER_ID).
For HTTP transport: per-request identity from the validated token.
"""

import os
import logging

from services.supabase import (
    AuthenticatedClient,
    get_service_client,
)

logger = logging.getLogger(__name__)


class ScopeDenied(Exception):
    """A token reached a verb its scopes do not authorize (ADR-563 D2)."""

    def __init__(self, verb: str, required: str, held: list[str]) -> None:
        self.verb = verb
        self.required = required
        self.held = held
        super().__init__(
            f"'{verb}' requires the '{required}' scope; this connection holds "
            f"{held or ['(none)']}. Re-authorize the connector to grant it."
        )


# ── Scopes (ADR-563) ────────────────────────────────────────────────────────
#
# The nine interop verbs are not equally consequential, and until ADR-563 the
# surface said they were: `valid_scopes=["read"]` was the ONLY scope, so a token
# LABELLED read could delete a file and mint a member-grant share link. The
# label was decorative.
#
# The tiers are ADDITIVE and ordered — each contains the ones before it. This
# is the whole reason the transition is non-breaking: `read` is retained as the
# LEGACY FULL-ACCESS grant it has always effectively been, so every already-
# connected assistant keeps working, while any token that carries a narrow
# scope is enforced for real. A new client asking for `files:read` gets exactly
# the four read verbs.
SCOPE_READ = "files:read"
SCOPE_WRITE = "files:write"
SCOPE_SHARE = "files:share"

# The legacy scope. Every token issued before ADR-563 carries exactly this
# (schema default `ARRAY['read']`, and both the OAuth and static-bearer paths
# hardcoded it). It authorizes everything — NOT because that is a good grant,
# but because narrowing it retroactively would silently break live connectors
# on a deploy nobody watched. New registrations should request the narrow set.
SCOPE_LEGACY_FULL = "read"

# verb → the narrow scope it requires. Derived from the SAME distinction the
# tool annotations already declare (readOnlyHint / destructiveHint) — the gate
# in `test_adr563_mcp_scope_enforcement.py` asserts the two agree, so a new
# read-only verb cannot land here demanding write.
VERB_SCOPES: dict[str, str] = {
    # pure reads — enumeration and retrieval, write nothing
    "open": SCOPE_READ,
    "list": SCOPE_READ,
    "search": SCOPE_READ,
    "history": SCOPE_READ,
    # substrate mutations — each lands an attributed revision
    "save": SCOPE_WRITE,
    "edit": SCOPE_WRITE,
    "delete": SCOPE_WRITE,
    "move": SCOPE_WRITE,
    # widens who can reach the workspace at all: 'member' grants full access to
    # whoever opens the link. Its own tier because granting reach is a
    # different act from changing content — a token that may write need not be
    # a token that may hand the workspace to a stranger.
    "share": SCOPE_SHARE,
}

# Which held scopes satisfy a requirement. Ordered containment, plus the legacy
# grant satisfying everything.
_SATISFIES: dict[str, frozenset[str]] = {
    SCOPE_READ: frozenset({SCOPE_READ, SCOPE_WRITE, SCOPE_SHARE, SCOPE_LEGACY_FULL}),
    SCOPE_WRITE: frozenset({SCOPE_WRITE, SCOPE_SHARE, SCOPE_LEGACY_FULL}),
    SCOPE_SHARE: frozenset({SCOPE_SHARE, SCOPE_LEGACY_FULL}),
}

# What a newly registering client may ask for. `read` stays valid so existing
# clients can still refresh, but it is no longer the DEFAULT — a fresh
# registration that names nothing gets the read-only tier, which is the safe
# floor rather than the full grant.
VALID_SCOPES = [SCOPE_READ, SCOPE_WRITE, SCOPE_SHARE, SCOPE_LEGACY_FULL]
DEFAULT_SCOPES = [SCOPE_READ]


def token_scopes() -> list[str]:
    """The scopes on the CURRENT request's token, or [] when there is none."""
    try:
        from mcp.server.auth.middleware.auth_context import get_access_token

        token = get_access_token()
        return list(getattr(token, "scopes", None) or [])
    except Exception as exc:  # noqa: BLE001
        logger.debug("[MCP Auth] no request token scopes (%s)", exc)
        return []


def assert_scope(verb: str) -> None:
    """Refuse `verb` unless the request's token authorizes it (ADR-563 D2).

    Called from `resolve_request_client(verb=…)` — the single chokepoint every
    tool handler already goes through — rather than from nine handlers, so a
    new verb cannot ship unguarded by forgetting a line. A verb absent from
    VERB_SCOPES is refused rather than allowed: an unclassified verb is a
    mistake, and failing open is how the pre-563 surface got here.

    The stdio / static-bearer path has no OAuth token and therefore no scopes;
    it is one process pinned to one user by env, so it is not a multi-tenant
    boundary and keeps full access.
    """
    required = VERB_SCOPES.get(verb)
    if required is None:
        raise ScopeDenied(verb, "a declared scope", [])

    held = token_scopes()
    if not held:
        # No token on the request: stdio/static-bearer. Env-pinned, single user.
        return

    if any(s in _SATISFIES[required] for s in held):
        return

    raise ScopeDenied(verb, required, held)


def _build_client(
    user_id: str,
    client_name: str | None = None,
    principal_id: str | None = None,
) -> AuthenticatedClient:
    """Build a service-key client scoped to a specific user_id.

    Service key bypasses RLS; isolation comes from explicit .eq("user_id", …)
    on every query (same pattern as unified_scheduler). ADR-288 D1:
    caller_identity sets the default authored_by for MCP-routed writes through
    execute_primitive().

    Client-qualified attribution: when the contributing LLM is known (resolved
    from the OAuth session), caller_identity becomes ``yarnnn:mcp:<client>``
    (e.g. ``yarnnn:mcp:claude.ai``) so every foreign write — and the `history`
    chain — NAMES THE ROOM, not just "an MCP write". This is the cross-LLM
    provenance story made literal: history shows "contributed via claude.ai →
    filed by the Reviewer". Validates under the ``yarnnn:`` prefix
    (is_valid_author), so no schema/validation change. Falls back to the bare
    ``yarnnn:mcp`` when the client can't be identified.

    ADR-373 D2 (grant-consult): ``principal_id`` is the foreign-LLM principal's
    STABLE id — the OAuth ``client_id`` (a UUID), the key the permission gate
    consults against ``principal_grants``. Distinct from ``client_name`` (the
    human-readable room, used for attribution): the gate keys on the stable id,
    attribution names the room. When no grant row exists for ``(client_id,
    workspace)`` the gate falls to the ``mcp`` class default = today's behavior.
    """
    caller_identity = f"yarnnn:mcp:{client_name}" if client_name and client_name != "unknown" else "yarnnn:mcp"
    return AuthenticatedClient(
        client=get_service_client(),
        user_id=user_id,
        email=None,
        caller_identity=caller_identity,
        principal_id=principal_id,
    )


def resolve_request_client(verb: str | None = None) -> AuthenticatedClient:
    """Resolve the authenticated client for the CURRENT request (ADR-310 D4).

    Reads the per-request OAuth token's user_id (the real authenticating
    operator) via the FastMCP auth context. Falls back to MCP_USER_ID only
    when no token user is present (stdio / misconfiguration). This is the
    single entry point every HTTP tool handler should call — it replaces
    reading the boot-time lifespan singleton, which pinned every request to
    one user regardless of who authenticated.

    ADR-563: pass `verb` and the caller's scopes are checked BEFORE identity is
    resolved and before any substrate is touched. The check lives here, at the
    one door every handler already opens, rather than as nine remembered lines
    — a guard a call site can forget is not a guard (the pre-563 surface had
    the scope field and no check at all). Raises `ScopeDenied`.
    """
    if verb is not None:
        assert_scope(verb)

    user_id = None
    client_id = None
    try:
        from mcp.server.auth.middleware.auth_context import get_access_token

        token = get_access_token()
        # YarnnnAccessToken carries user_id (oauth_provider.py); the static
        # bearer path also stamps MCP_USER_ID onto it.
        user_id = getattr(token, "user_id", None)
        # ADR-373 D2: the OAuth client_id is the foreign-LLM principal's stable
        # id — the gate's grant-consult key. (Distinct from the room NAME used
        # for attribution, resolved below.)
        client_id = getattr(token, "client_id", None)
    except Exception as exc:  # noqa: BLE001
        logger.debug("[MCP Auth] no request token user (%s); falling back to env", exc)

    if not user_id:
        user_id = os.environ.get("MCP_USER_ID")
        if not user_id:
            raise ValueError(
                "No authenticated user for MCP request and MCP_USER_ID unset."
            )

    # Client-qualified attribution (Finding 2, 2026-06-26): the revision's
    # authored_by must NAME the contributing LLM (yarnnn:mcp:<client>). The
    # earlier direct-only `_normalize_client_id(client_id)` mapping returned
    # None for claude.ai's OPAQUE registration-UUID client_id, so authored_by
    # silently fell back to bare `yarnnn:mcp` even though the provenance stamp
    # (which used the DB-backed lookup) resolved the name. Use the SAME DB-backed
    # resolver here so authored_by and provenance never diverge. It needs an auth
    # client to read mcp_oauth_clients, so build a base client ONCE, derive the
    # name with it, then re-stamp caller_identity on the same underlying client —
    # no second create_client(). (live test surfaced the divergence: authored_by=
    # yarnnn:mcp while provenance=mcp:Claude on the same write.)
    # ADR-373 D2: the stable principal_id for an MCP caller is its OAuth
    # client_id (a UUID). Fall back to user_id (the authorizing operator) when
    # the token carried no client_id — the gate then keys on the owner grant,
    # still class-default in N=1.
    principal_id = client_id or user_id
    base = _build_client(user_id, principal_id=principal_id)
    client_name = None
    try:
        from services.mcp_composition import derive_client_name_from_token
        resolved = derive_client_name_from_token(base)
        if resolved and resolved != "unknown":
            client_name = resolved
    except Exception as exc:  # noqa: BLE001
        logger.debug("[MCP Auth] client-name resolution failed (%s)", exc)

    if not client_name:
        return base
    return AuthenticatedClient(
        client=base.client,
        user_id=user_id,
        email=None,
        caller_identity=f"yarnnn:mcp:{client_name}",
        principal_id=principal_id,
    )


def resolve_request_host_id() -> str | None:
    """Resolve the calling host id for the CURRENT request (ADR-379), best-effort.

    Used by the DISCOVERY + RESOURCE-READ gates (server.py) — these run before any
    tool response, so the response-time `client_name` isn't available; they need
    the host identity here. Returns a HostProfile id ("chatgpt" | "claude.ai" | …)
    or None when the caller can't be identified.

    Resolution order, cheapest-first (discovery is hot and should avoid a DB hit
    unless needed):
      1. The token `client_id` resolved directly by substring (catches ChatGPT,
         whose client_id carries "openai"/"chatgpt"; zero DB).
      2. The DB-backed registered `client_name` lookup (catches claude.ai's opaque
         UUID via the registered name) — only when (1) misses.

    SAFE DEFAULT: None on any failure / unidentified caller. The gate treats None
    as a non-widget host (text-safe), so an unidentified host is never advertised a
    widget it might choke on — the same fail-closed posture as the response gate.
    """
    try:
        from mcp.server.auth.middleware.auth_context import get_access_token
        token = get_access_token()
    except Exception:  # noqa: BLE001
        token = None
    client_id = getattr(token, "client_id", None) if token else None
    if not client_id:
        return None

    from mcp_server.presentation.hosts import resolve_host_id

    # (1) cheap direct resolve from the client_id itself (ChatGPT, etc.)
    direct = resolve_host_id(client_id)
    if direct:
        return direct

    # (2) DB-backed registered-name lookup (claude.ai opaque UUID). Best-effort.
    try:
        user_id = getattr(token, "user_id", None) or os.environ.get("MCP_USER_ID")
        if not user_id:
            return None
        base = _build_client(user_id)
        row = (
            base.client.table("mcp_oauth_clients")
            .select("client_name")
            .eq("client_id", client_id)
            .limit(1)
            .execute()
        )
        name = (row.data or [{}])[0].get("client_name") if row.data else None
        return resolve_host_id(name) if name else None
    except Exception as exc:  # noqa: BLE001
        logger.debug("[MCP Auth] host-id resolution failed (%s)", exc)
        return None
