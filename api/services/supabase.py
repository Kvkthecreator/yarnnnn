"""
Supabase client configuration
"""
from __future__ import annotations

import os
import logging
from functools import lru_cache
from typing import Iterator, Optional, Tuple
from dataclasses import dataclass

from supabase import create_client, Client
from supabase.lib.client_options import SyncClientOptions as ClientOptions
from fastapi import Depends, HTTPException, Header

# Python 3.9 compatible Annotated import
try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated

logger = logging.getLogger(__name__)


_JWKS_CLIENT = None


def _get_jwks_client():
    """The project's JWKS client, module-cached. The URL derives from
    SUPABASE_URL, so ES256 verification needs no extra provisioning; the JWK set
    itself is cached in-process (lifespan below) so steady-state requests never
    refetch."""
    global _JWKS_CLIENT
    if _JWKS_CLIENT is None:
        from jwt import PyJWKClient

        _JWKS_CLIENT = PyJWKClient(
            f"{get_supabase_url()}/auth/v1/.well-known/jwks.json",
            cache_keys=True,
            cache_jwk_set=True,
            lifespan=3600,
        )
    return _JWKS_CLIENT


def decode_jwt_payload(token: str) -> dict:
    """Decode + VERIFY the Supabase user JWT. Fail-closed: every token is
    signature-checked before `sub` reaches any authorization decision
    (resolve_workspace_for_principal, principal_id stamping) — the 2026-08-03
    audit fix, completed 2026-08-05.

    Two verification lanes, dispatched on the token's own header:
    - ES256 → the project JWKS. Supabase's new-key system (the 2026-08-04
      migration) signs user access tokens with asymmetric keys published at
      /auth/v1/.well-known/jwks.json; there is no shared secret to configure.
    - HS256 → SUPABASE_JWT_SECRET, for stacks still on the legacy shared
      secret (local supabase). An HS256 token with no secret configured is
      REJECTED, never unverified-decoded.

    Each lane pins its algorithm list and key type, so a header-controlled
    algorithm-confusion downgrade (ES256 key verified as HS256, alg=none)
    cannot succeed.
    """
    import jwt as _pyjwt

    try:
        header = _pyjwt.get_unverified_header(token)
    except _pyjwt.InvalidTokenError as e:
        raise ValueError(f"Failed to decode JWT: {e}")

    alg = header.get("alg")
    try:
        if alg == "ES256":
            signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
            return _pyjwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256"],
                audience="authenticated",
                options={"verify_aud": True},
            )
        if alg == "HS256":
            secret = os.environ.get("SUPABASE_JWT_SECRET")
            if not secret:
                raise ValueError(
                    "HS256 JWT but SUPABASE_JWT_SECRET unset — rejecting"
                )
            return _pyjwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                audience="authenticated",
                options={"verify_aud": True},
            )
        raise ValueError(f"Unsupported JWT alg: {alg}")
    except _pyjwt.PyJWKClientError as e:
        logger.error("[AUTH] JWKS lookup failed: %s", e)
        raise ValueError(f"JWT verification unavailable: {e}")
    except _pyjwt.InvalidTokenError as e:
        raise ValueError(f"JWT signature/claims invalid: {e}")


@dataclass
class AuthenticatedClient:
    """Wrapper that holds Supabase client, user ID, and email.

    ADR-288 D1: ``caller_identity`` carries the ADR-209 attribution string
    for substrate writes performed through this auth (e.g., ``"operator"``,
    ``"freddie:ai:freddie-sonnet-v8"``, ``"yarnnn:mcp"``,
    ``"system:<recurrence-slug>"``). Defaults to ``"operator"`` because the
    only path that constructs ``AuthenticatedClient`` is the route-level JWT
    handler ``get_user_client`` — the operator hit the API. Non-operator
    callers (Reviewer wake, mechanical recurrence, MCP, specialist
    dispatch) build their own auth namespaces and set ``caller_identity``
    explicitly at construction time.

    ADR-373 D1: ``workspace_id`` carries the substrate's binding unit — the
    workspace this auth reaches. Resolved once, at auth construction, from the
    principal's grant (the N=1 case: the user's singleton owner-workspace). It
    is the SECOND growth of this dataclass (``caller_identity`` was the first,
    ADR-288): derive the workspace once here, thread the same object, never
    re-resolve at the 118 substrate query sites. ``Optional`` during the Phase-1
    transition — a caller that has not set it falls back to ``user_id`` scoping
    (byte-identical in N=1, where one user owns exactly one workspace). Code
    that has switched to workspace scoping reads ``workspace_id``; code still on
    ``user_id`` is unaffected. Both key the same rows until the sweep completes.

    ADR-373 D2 (grant-consult, 2026-06-29): ``principal_id`` carries the caller's
    STABLE principal identity — the key the permission gate consults against
    ``principal_grants`` to resolve a per-principal write-region grant (falling
    back to the caller-class default when no grant / NULL scopes). This is the
    THIRD growth of the dataclass, and it completes the attribution↔authorization
    symmetry (ADR-288 made attribution per-principal; this makes authorization the
    same granularity). It is set explicitly where the identity is known: the human
    JWT path stamps ``user_id`` (the owner-grant's principal_id, confirmed 1:1 with
    ``workspaces.owner_id``); the MCP path stamps the OAuth ``client_id`` (the
    foreign-LLM room — claude.ai/ChatGPT). When left ``None``, ``resolve_principal_id``
    derives a best-effort stable id from ``caller_identity`` + ``user_id`` so the
    gate always has a key. At N=1 (all live workspaces) the only grant rows are the
    owner's with NULL scopes, so the consult falls through to the class default and
    behavior is BYTE-IDENTICAL to the pre-consult gate.
    """
    client: Client
    user_id: str
    email: Optional[str] = None
    caller_identity: str = "operator"
    workspace_id: Optional[str] = None
    principal_id: Optional[str] = None


def resolve_owner_workspace_id(user_id: str) -> Optional[str]:
    """Resolve the workspace id a human user owns (ADR-373 D1, amended ADR-465 D2).

    The zero-or-one resolver: a user owns AT MOST one workspace (ADR-465 D2
    join-only genesis, ratified 2026-08-03 — was "exactly one" under the
    migration-106 auto-mint trigger, retired by migration 233). A member-only
    principal (arrived through a share/invite, never took an owner-act) owns
    none, and every caller either tolerates None or routes through
    ``resolve_workspace_for_principal`` (which falls back to the newest active
    grant). Owner-genesis is lazy and explicit: ``ensure_owner_workspace``,
    called from the cold-user door only — never from an accept path.

    Cached per-process: the owner→workspace mapping is stable, so this is safe
    to memoize and keeps the hot auth path off a per-request DB round-trip.
    (``ensure_owner_workspace`` clears the cache on mint.)
    """
    return _resolve_owner_workspace_id_cached(user_id)


# The mint-time placeholder name (both mint sites: here + the account-reset
# re-mint). A workspace still carrying it has never been named by its owner —
# outward surfaces (invite email/landing, share landing) treat it as unnamed
# and keep their own generic phrasing instead of leaking "My Workspace" to a
# recipient it isn't "my" to.
DEFAULT_WORKSPACE_NAME = "My Workspace"


def display_workspace_name(name: Optional[str]) -> Optional[str]:
    """The workspace's chosen name, or None while it still wears the mint default."""
    if not name:
        return None
    trimmed = name.strip()
    if not trimmed or trimmed.lower() == DEFAULT_WORKSPACE_NAME.lower():
        return None
    return trimmed


def ensure_owner_workspace(user_id: str) -> str:
    """Mint the caller's owner workspace if none exists (ADR-465 D2 — lazy genesis).

    The trigger-106 auto-mint moved up into the app, where it can be
    CONDITIONAL: this is called only from the cold-user door (the first
    ``/workspace/state`` fetch of a principal who resolves NO workspace at all
    — no owner row, no grants). A share-first arrival holds a member grant, so
    the door never fires for them: join-only is real. Idempotent (re-checks
    under the service client before inserting; the row shape mirrors the
    retired trigger — name + owner_id; balance rides the column DEFAULT,
    migration 144).
    """
    existing = resolve_owner_workspace_id(user_id)
    if existing:
        return existing
    client = get_service_client()
    # Re-check uncached (the lru may hold a stale None from earlier in-process).
    fresh = (
        client.table("workspaces").select("id").eq("owner_id", user_id).limit(1).execute()
    )
    if fresh.data:
        _resolve_owner_workspace_id_cached.cache_clear()
        return fresh.data[0]["id"]
    inserted = (
        client.table("workspaces")
        .insert({"name": DEFAULT_WORKSPACE_NAME, "owner_id": user_id})
        .execute()
    )
    if not inserted.data:
        raise RuntimeError(f"owner-workspace mint failed for {user_id}")
    _resolve_owner_workspace_id_cached.cache_clear()
    logger.info("[ADR-465 D2] lazily minted owner workspace for %s", user_id)
    return inserted.data[0]["id"]


@lru_cache(maxsize=4096)
def _resolve_owner_workspace_id_cached(user_id: str) -> Optional[str]:
    try:
        client = get_service_client()
        result = (
            client.table("workspaces")
            .select("id")
            # ⚠️ THE OWNERSHIP FILTER IS THE WHOLE FUNCTION. Without it this
            # selects the oldest workspace in the TABLE and hands it to every
            # caller — a cross-tenant resolution, not a mis-ordering.
            #
            # It was dropped on 2026-08-17 while adding the ORDER BY below (the
            # `.eq()` was replaced rather than joined by it), and the ordering
            # made the wrong answer DETERMINISTIC: every principal resolved to
            # one specific stranger's workspace. Observed live the same day —
            # a connector authenticated as an account with no ownership and no
            # grant into that workspace wrote three attributed revisions into
            # it, succeeding, while its own 275-file substrate read as 19 files.
            # The service key bypasses RLS, so nothing below this line would
            # have caught it. Never remove it; never let a "fix" replace it.
            .eq("owner_id", user_id)
            # ADR-373 D6 (2026-08-17) — ORDER BY is load-bearing, not tidiness.
            # This was `.limit(1)` with no ordering, so an account owning more
            # than one workspace row got an ARBITRARY pick that the lru_cache
            # below then froze for the process lifetime. Two processes (the API
            # and the long-lived MCP service) could cache DIFFERENT answers for
            # the same user and disagree about where that user's substrate
            # lives — permanently, since the MCP service has no request recycle.
            # Oldest-first: the first workspace an owner made is their home.
            .order("created_at", desc=False)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]["id"]
    except Exception as exc:  # pragma: no cover - resolution is best-effort
        # Transient / pre-existing-table edge: fall back to user_id scoping.
        # Never block the request on workspace resolution.
        logger.debug("[ADR-373] owner-workspace resolve failed for %s: %s", user_id, exc)
    return None


def resolve_owned_workspace_ids(user_id: str) -> list:
    """EVERY workspace this principal owns, oldest-first (ADR-465 D2 + genesis).

    The plural sibling of `resolve_owner_workspace_id`, which is deliberately
    zero-or-ONE: it answers "where is this principal's HOME" and its first
    element is that same answer. Ownership itself has never been capped — there
    is no unique constraint on `workspaces.owner_id` — and since deliberate
    genesis shipped a principal can hold several.

    Two callers need the plural form and would be WRONG with the singular one:
      - `principal_reaches_workspace`, which otherwise refuses the owner of a
        NON-home workspace access to their own commons (observed on production
        2026-08-18: the owner of a freshly-created workspace was 403'd out of it
        because the singular resolver returned their OLDER workspace, and the
        `X-Workspace-Id` pin the create flow had just written no longer matched
        anything reachable — locking them out of every endpoint, switcher
        included).
      - the memberships/switcher endpoint, which would list one owned workspace
        and silently hide the rest.

    NOT cached, and that is deliberate: the singular resolver is `lru_cache`d
    because a home is stable, but this set CHANGES the moment genesis runs, and
    a stale empty/short answer here is an authorization refusal rather than a
    mis-route. `create_workspace` clears the singular cache; nothing has to
    remember to clear this one.

    Ownership ground truth is the `owner_id` COLUMN, never an `owner`-role grant
    row (see `principal_grants.has_billing_authority` — live workspaces exist
    whose owner has no grant row, so keying on the grant would 403 real owners).
    """
    try:
        client = get_service_client()
        result = (
            client.table("workspaces")
            .select("id")
            # The ownership filter is the whole function — see the warning on
            # `_resolve_owner_workspace_id_cached`. Never remove it.
            .eq("owner_id", user_id)
            .order("created_at", desc=False)
            .execute()
        )
        return [r["id"] for r in (result.data or [])]
    except Exception as exc:  # pragma: no cover — best-effort, fail-closed
        logger.warning("[ADR-373] owned-workspace list failed for %s: %s", user_id, exc)
        return []


def principal_reaches_workspace(user_id: str, workspace_id: str) -> bool:
    """Whether a human principal may bind a request to a workspace (ADR-373).

    True iff they own it OR hold an active grant into it. Consulted when a
    request carries ``X-Workspace-Id``. NOT cached: a revoked member must
    lose reach on their next request, not at cache eviction.
    """
    try:
        # EVERY owned workspace, not just the home one. The singular resolver
        # is oldest-first, so an owner of a second workspace failed BOTH
        # branches here and was locked out of their own commons (2026-08-18).
        if workspace_id in resolve_owned_workspace_ids(user_id):
            return True
        client = get_service_client()
        result = (
            client.table("principal_grants")
            .select("id")
            .eq("principal_id", user_id)
            .eq("workspace_id", workspace_id)
            .eq("status", "active")
            .limit(1)
            .execute()
        )
        return bool(result.data)
    except Exception as exc:  # pragma: no cover — validation is fail-closed
        logger.warning(
            "[ADR-373] workspace reach check failed for %s→%s: %s",
            user_id, workspace_id, exc,
        )
        return False


def resolve_workspace_for_principal(
    user_id: str, requested_workspace_id: Optional[str] = None
) -> Optional[str]:
    """Resolve the workspace a request binds to (ADR-373 Phase 1, member-aware).

    - ``requested_workspace_id`` (the ``X-Workspace-Id`` header): honored iff
      the principal reaches it (owner or active grant); unreachable → None,
      and the auth layer rejects with 403 (fail-closed — never silently fall
      back to a different workspace than the one the client addressed).
    - No request: the owner workspace (today's behavior, byte-identical
      N=1). A principal with NO owner workspace (a fresh invitee before
      their own workspace exists) falls back to their newest active grant's
      workspace — the invited-member landing case.
    """
    if requested_workspace_id:
        return (
            requested_workspace_id
            if principal_reaches_workspace(user_id, requested_workspace_id)
            else None
        )
    owned = resolve_owner_workspace_id(user_id)
    if owned:
        return owned
    # Fresh-invitee fallback: no owned workspace → the newest active grant.
    try:
        client = get_service_client()
        result = (
            client.table("principal_grants")
            .select("workspace_id")
            .eq("principal_id", user_id)
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]["workspace_id"]
    except Exception as exc:  # pragma: no cover — best-effort
        logger.debug("[ADR-373] grant-workspace resolve failed for %s: %s", user_id, exc)
    return None


def resolve_principal_id(auth: "AuthenticatedClient") -> Optional[str]:
    """Resolve the caller's STABLE principal identity for the grant-consult (ADR-373 D2).

    The uniform abstraction every principal class flows through. The gate consults
    ``principal_grants(principal_id, workspace_id)`` with the returned id; a new
    principal type needs a mapping entry HERE and a grant row — no gate change.

    Resolution (the MCP/foreign-LLM branch is FIRST — ADR-373 D2.a — so it
    resolves to the PROVIDER host-id, not the explicit client_id):
      - ``yarnnn:mcp:<client>`` / ``yarnnn:mcp``  → the PROVIDER host-id (ADR-373
        D2.a): the member is the provider (claude.ai/chatgpt), NOT the churning
        OAuth client_id. Resolved via the ADR-379 registry from the room name,
        then the explicit principal_id (the client_id). A narrow on the provider
        then binds ALL its sessions incl. future re-registrations. Falls back to
        the room name / explicit client_id / user_id when the registry doesn't
        recognize the provider (still keyed stably, just not collapsed).
      - explicit ``auth.principal_id`` set        → use it verbatim (human JWT path
        stamps ``user_id``; non-MCP callers that set it explicitly).
      - ``agent:<slug>`` / ``specialist:<role>``  → the slug/role (the agent's id).
      - ``system:<actor>``                        → the actor (class-default only; no
        system grant rows by design).
      - ``reviewer:<identity>`` / ``operator``    → ``user_id`` (the workspace owner the
        seat acts for; the seat is workspace-level, ADR-368 D5).

    Returns ``None`` only when no id can be derived (no user_id, no caller_identity)
    — the gate then falls straight to the class default (today's behavior).

    SAFETY INVARIANT (ADR-373 D2.a): only the ``yarnnn:mcp*`` branch changed. The
    owner / agent / system / reviewer branches are byte-identical to the
    pre-D2.a resolver — so the owner-path 99/0 proof is preserved by construction.
    """
    caller_identity = getattr(auth, "caller_identity", "") or ""
    user_id = getattr(auth, "user_id", None)
    explicit = getattr(auth, "principal_id", None)
    # ADR-373 D2.a — MCP/foreign-LLM FIRST: resolve to the PROVIDER host-id.
    if caller_identity.startswith("yarnnn:mcp"):
        from mcp_server.presentation.hosts import resolve_host_id
        parts = caller_identity.split(":", 2)
        room = parts[2] if len(parts) == 3 and parts[2] else None
        # Strongest-first: the room name, then the explicit client_id.
        for signal in (room, explicit):
            if signal:
                hid = resolve_host_id(signal)
                if hid:
                    return hid
        # Provider unknown to the registry → keep a stable best-effort key
        # (room name, else the explicit client_id, else the operator).
        return room or explicit or user_id
    # Non-MCP: explicit principal_id wins (unchanged).
    if explicit:
        return explicit
    if caller_identity.startswith("agent:") or caller_identity.startswith("specialist:"):
        return caller_identity.split(":", 1)[1] or user_id
    if caller_identity.startswith("system:"):
        return caller_identity.split(":", 1)[1] or user_id
    # operator / reviewer:* / unknown → the owner the auth acts for.
    return user_id


def close_supabase_client(client: Client) -> None:
    """Release every httpx connection pool a ``create_client()`` opened.

    A Supabase ``Client`` eagerly constructs TWO httpx pools — postgrest (lazy,
    on first ``.table()``/``.rpc()``) and the gotrue auth client (eager, in
    ``__init__``) — and exposes NO unified ``close()``. Each must be released
    individually or the pools (TLS connections + buffers + HTTP/2 hpack state)
    accumulate over the process lifetime. That accumulation OOM-killed
    ``yarnnn-api`` on 2026-06-01 (postgrest leak, partially fixed) and again on
    2026-06-04 (the auth pool was still leaking + ``build_working_memory``
    leaked 23 clients/request). See
    ``docs/infrastructure/memory-and-client-lifecycle.md``.

    This is the Singular teardown — every per-request / per-thread ``create_client``
    call site closes through here, never a hand-rolled ``.session.close()``.
    Best-effort: a teardown error must never mask the response.
    """
    # postgrest pool — only built once a table/rpc call ran, so guard the lazy attr.
    try:
        client.postgrest.session.close()
    except Exception:  # pragma: no cover - teardown best-effort
        pass
    # gotrue auth pool — built eagerly in Client.__init__, always present.
    try:
        client.auth._http_client.close()
    except Exception:  # pragma: no cover - teardown best-effort
        pass


@lru_cache()
def get_supabase_url() -> str:
    url = os.environ.get("SUPABASE_URL")
    if not url:
        raise ValueError("SUPABASE_URL must be set")
    return url


@lru_cache()
def get_service_client() -> Client:
    """Get Supabase client with service key (bypasses RLS)."""
    url = get_supabase_url()
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not key:
        raise ValueError("SUPABASE_SERVICE_KEY must be set")
    return create_client(url, key)


def get_user_client(
    authorization: Optional[str] = Header(None),
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-Id"),
) -> Iterator[AuthenticatedClient]:
    """
    Get Supabase client with user's JWT for RLS enforcement.
    Yields an AuthenticatedClient with both the client and user_id.
    Use as FastAPI dependency.

    Memory discipline: this dependency runs on every authenticated request,
    including the always-on frontend polls (``/api/workspace/nav``,
    ``/api/recurrences``, ``/api/budget`` every ~60s). Each ``create_client``
    builds TWO ``httpx`` connection pools (postgrest + gotrue auth). Without an
    explicit teardown these pools (TLS connections + buffers + HTTP/2 hpack
    state) accumulate over the process lifetime — the RSS creep that OOM-killed
    yarnnn-api on 2026-06-01 and again on 2026-06-04. See
    ``docs/infrastructure/memory-and-client-lifecycle.md``.

    Two guards:
      1. ``auto_refresh_token=False`` + ``persist_session=False`` — we never run
         the sign-in flow here (the JWT is decoded locally and applied directly
         to postgrest), so the gotrue auto-refresh ``threading.Timer`` is pure
         overhead. Disabling it removes any chance of an orphaned refresh timer.
      2. ``finally: close_supabase_client(client)`` — releases BOTH per-request
         pools (the 2026-06-01 fix closed only postgrest; the auth pool kept
         leaking, which is why the OOM recurred). This is the load-bearing fix.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.replace("Bearer ", "")

    # Decode JWT to get user ID and email
    try:
        payload = decode_jwt_payload(token)
        user_id = payload.get("sub")
        email = payload.get("email")  # Supabase includes email in JWT
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no user ID")
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    url = get_supabase_url()
    key = os.environ.get("SUPABASE_ANON_KEY")

    if not key:
        raise ValueError("SUPABASE_ANON_KEY must be set")

    options = ClientOptions(auto_refresh_token=False, persist_session=False)
    client = create_client(url, key, options)
    # Set the auth token for RLS
    client.postgrest.auth(token)

    # ADR-373 D1 (member-aware, ADR-404 step 4): resolve the binding workspace
    # once, here. Default = the owner workspace (byte-identical N=1). An
    # ``X-Workspace-Id`` header selects a granted workspace instead —
    # validated fail-closed (an unreachable workspace is 403, never a silent
    # fallback to a different workspace than the client addressed). A fresh
    # invitee with no owned workspace lands on their newest grant's workspace.
    workspace_id = resolve_workspace_for_principal(user_id, x_workspace_id)
    if x_workspace_id and workspace_id is None:
        close_supabase_client(client)
        raise HTTPException(
            status_code=403,
            detail=f"No active grant into workspace {x_workspace_id}",
        )

    # Publish the binding for the data layer (contextvar — the sweep spine;
    # see services/workspace_context.py). Reset on teardown.
    from services.workspace_context import (
        reset_request_workspace, set_request_workspace,
    )
    _ws_token = set_request_workspace(workspace_id)

    try:
        yield AuthenticatedClient(
            client=client,
            user_id=user_id,
            email=email,
            workspace_id=workspace_id,
            # ADR-373 D2: the human owner's principal_id IS their user_id — the
            # backfilled owner grant is keyed on auth.users.id (confirmed 1:1 with
            # workspaces.owner_id, all 11 live rows). Stamp it so the gate consults
            # the owner grant directly without re-deriving.
            principal_id=user_id,
        )
    finally:
        reset_request_workspace(_ws_token)
        # Release BOTH request-scoped httpx pools (postgrest + gotrue auth).
        close_supabase_client(client)


# Type alias for dependency injection
UserClient = Annotated[AuthenticatedClient, Depends(get_user_client)]
ServiceClient = Annotated[Client, Depends(get_service_client)]
