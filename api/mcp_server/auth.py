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
# The tier definitions live in `services/mcp_scopes.py`, NOT here. The consent
# screen must name the same capabilities this module enforces, and it is served
# by the API service, which cannot import this module (py3.9 venv + the
# py3.11-only `mcp` SDK — the same constraint that put
# `delete_tokens_for_client` in `services/principal_grants.py`).
#
# Re-exported so every existing `from mcp_server.auth import SCOPE_*` call site
# and the ADR-563 gate keep working against ONE definition. A second copy here
# would be the pre-563 defect re-created at the surface: a label that can
# disagree with the check.
from services.mcp_scopes import (  # noqa: F401  (re-exported for call sites)
    SCOPE_READ,
    SCOPE_WRITE,
    SCOPE_SHARE,
    SCOPE_LEGACY_FULL,
    VERB_SCOPES,
    VALID_SCOPES,
    DEFAULT_SCOPES,
    SATISFIES as _SATISFIES,
    satisfied_by,
)


def token_scopes() -> list[str]:
    """The scopes on the CURRENT request's token, or [] when there is none."""
    try:
        from mcp.server.auth.middleware.auth_context import get_access_token

        token = get_access_token()
        return list(getattr(token, "scopes", None) or [])
    except Exception as exc:  # noqa: BLE001
        logger.debug("[MCP Auth] no request token scopes (%s)", exc)
        return []


def request_binding(user_id: str) -> str:
    """How the CURRENT request's workspace was arrived at (ADR-584 D2).

    Returns one of the BINDING_* values. Reads the token's stamped workspace the
    same way `resolve_request_client` does, then re-runs the resolver's own
    branch logic through `resolve_mcp_workspace_detail` — the reason travels with
    the resolution rather than being inferred by a second, drifting copy.

    Used only by `whoami`, which is called once per session; every file verb
    stays on the plain `resolve_mcp_workspace` path with no extra work.
    """
    bound_workspace_id = None
    try:
        from mcp.server.auth.middleware.auth_context import get_access_token

        bound_workspace_id = getattr(get_access_token(), "workspace_id", None)
    except Exception as exc:  # noqa: BLE001 — stdio / static-bearer carries no token
        logger.debug("[ADR-584] no request token for binding (%s)", exc)

    _workspace_id, binding = resolve_mcp_workspace_detail(user_id, bound_workspace_id)
    return binding


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

    if satisfied_by(required, held):
        return

    raise ScopeDenied(verb, required, held)


def _build_client(
    user_id: str,
    client_name: str | None = None,
    principal_id: str | None = None,
    bound_workspace_id: str | None = None,
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

    ADR-373 **D6 (built 2026-08-17)**: the client is stamped with a
    ``workspace_id``, resolved the SAME way the browser's JWT door resolves it
    (``resolve_workspace_for_principal``). Before this, the MCP client carried
    ``workspace_id=None`` and every read/write fell through to the rung-3
    default inside ``effective_workspace_id`` — so the connector could not
    address a workspace at all.

    That was not a verification inconvenience: a member working in a workspace
    they do not OWN had every connector write land in their owner workspace
    instead, **succeeding, returning a revision id, and being invisible in the
    surface they were looking at**. An incorrect success with no error anywhere.
    Observed 2026-08-16 — an MCP `save` returned a revision_id while the
    browser 404'd the same path, and vice versa.

    D6 was ratified in ADR-373 and never built ("Post-ADR it resolves
    ``principal → (workspace_id, role, grant)``"). This discharges it for the
    workspace half; the role/grant half already routes through ``principal_id``
    above.
    """
    caller_identity = f"yarnnn:mcp:{client_name}" if client_name and client_name != "unknown" else "yarnnn:mcp"
    return AuthenticatedClient(
        client=get_service_client(),
        user_id=user_id,
        email=None,
        caller_identity=caller_identity,
        principal_id=principal_id,
        # ADR-573 — the token's chosen workspace when it has one, else the
        # principal's default. Reach is re-checked inside the resolver.
        workspace_id=resolve_mcp_workspace(user_id, bound_workspace_id),
    )


def resolve_mcp_workspace(user_id: str, bound_workspace_id: str | None = None) -> str | None:
    """The workspace an MCP request binds to (ADR-373 D6, selection by ADR-573).

    Deliberately the SAME function the browser's JWT door calls. ADR-573 gives
    it the same ARGUMENT too: ``bound_workspace_id`` is the connector's
    equivalent of the browser's ``X-Workspace-Id`` header — the workspace the
    operator chose at the consent screen, stamped on the token.

    **Reach is re-checked here, every request, not trusted from the token.**
    ``resolve_workspace_for_principal`` returns None when the principal cannot
    reach the requested workspace, and ``principal_reaches_workspace`` is
    deliberately uncached, so a member revoked after the token was minted loses
    reach on their very next call. A stamped workspace therefore NARROWS what a
    connection addresses; it can never grant reach the principal lacks.

    ``None`` (every pre-573 token, and any connection whose operator did not
    choose) resolves the principal's default — owner workspace, else newest
    active grant. That is exactly the ADR-373 D6 behaviour, which is why ADR-573
    ships without a backfill.

    **Resolved per request, never cached here.** The MCP service is a
    long-lived process with no request recycle (unlike the API's
    ``--limit-max-requests 10000``), so a value cached at this layer would
    outlive a workspace change indefinitely. ``resolve_owner_workspace_id``
    has its own ``lru_cache`` with an invalidation path; this adds no second,
    un-invalidatable one.

    Best-effort by design: a resolution failure returns None, which restores
    exactly the pre-D6 behavior (fall through to ``effective_workspace_id``'s
    own rungs) rather than failing the request. A connector that cannot
    resolve a workspace should still be able to read its own substrate.

    ⚠️ The one asymmetry with the browser: an UNREACHABLE requested workspace
    403s at the JWT door, but here it degrades to the default rather than
    failing the tool call. That is deliberate — the operator is not present to
    re-authorize mid-session, and a connector that silently stops working is
    worse than one that falls back to the substrate it can always reach. The
    reach loss is still enforced (the unreachable workspace is never returned).

    ADR-584 D2: that degrade is correct and stays. What was NOT acceptable is
    that it was unobservable — every read and write correct, attributed, landing
    somewhere real, with no signal anywhere in the response that the operator's
    chosen binding was not honoured. Callers that want to REPORT the reason use
    ``resolve_mcp_workspace_detail``; this function keeps its exact signature and
    return so its ~90 call sites are untouched.
    """
    workspace_id, _binding = resolve_mcp_workspace_detail(user_id, bound_workspace_id)
    return workspace_id


# How a request's workspace was arrived at (ADR-584 D2). Reported by `whoami`,
# so a silent fallback becomes a stateable fact in the room where it matters.
BINDING_CHOSEN = "chosen"      # the token's stamped workspace, honoured
BINDING_DEFAULT = "default"    # no stamp on the token → the principal's default
BINDING_FALLBACK = "fallback"  # a stamp existed and was UNREACHABLE → degraded
BINDING_UNRESOLVED = "unresolved"  # resolution failed → effective_workspace_id's rungs


def resolve_mcp_workspace_detail(
    user_id: str, bound_workspace_id: str | None = None
) -> tuple[str | None, str]:
    """``resolve_mcp_workspace`` plus HOW the answer was reached (ADR-584 D2).

    Returns ``(workspace_id, binding)``. The workspace half is byte-identical to
    what ``resolve_mcp_workspace`` has always returned — this adds no policy, no
    query, and no failure mode. Only the *reason* is new, and it exists because
    ADR-584 found the fallback branch below to be an incorrect-success generator:
    correct, attributed, invisible.

    The four bindings map 1:1 to the branches, so a reader of `whoami` can tell
    "you are in the workspace you chose" from "you are in a workspace you did not
    choose, because the one you chose is out of reach."
    """
    try:
        from services.supabase import resolve_workspace_for_principal

        if bound_workspace_id:
            reached = resolve_workspace_for_principal(user_id, bound_workspace_id)
            if reached:
                return reached, BINDING_CHOSEN
            logger.warning(
                "[ADR-573] token-bound workspace %s is unreachable for %s — "
                "falling back to the principal default",
                str(bound_workspace_id)[:8], str(user_id)[:8],
            )
            return resolve_workspace_for_principal(user_id), BINDING_FALLBACK

        return resolve_workspace_for_principal(user_id), BINDING_DEFAULT
    except Exception as exc:  # noqa: BLE001 — never block a request on this
        logger.debug("[ADR-373 D6] workspace resolve failed for %s: %s", user_id, exc)
        return None, BINDING_UNRESOLVED


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
    # ADR-573 — initialized BEFORE the try: the stdio / static-bearer path takes
    # the except branch, and a name bound only inside the try would raise
    # UnboundLocalError at the call below rather than degrading to the default.
    bound_workspace_id = None
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
        # ADR-573: the workspace chosen at consent, stamped on this token.
        # None on every pre-573 token → the principal's default (ADR-373 D6).
        bound_workspace_id = getattr(token, "workspace_id", None)
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
    base = _build_client(
        user_id,
        principal_id=principal_id,
        # ADR-573 — the consent-time binding. Resolved ONCE here; the re-stamp
        # below carries `base.workspace_id` rather than resolving again.
        bound_workspace_id=bound_workspace_id,
    )
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
        # ADR-373 D6 — carried from `base`, not re-resolved: this re-stamp
        # changes only the attribution string, and a second resolve would be a
        # second DB round trip that could disagree with the first. Dropping it
        # here would ALSO have silently un-scoped every client whose name
        # resolves (i.e. every real claude.ai/ChatGPT caller) while leaving
        # the unnamed fallback path correct — a bug reachable only in prod.
        workspace_id=base.workspace_id,
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
