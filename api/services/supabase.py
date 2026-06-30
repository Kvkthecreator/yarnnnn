"""
Supabase client configuration
"""
from __future__ import annotations

import os
import json
import base64
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


def decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload without verification (Supabase handles verification via RLS)."""
    try:
        # JWT format: header.payload.signature
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")

        # Decode payload (add padding if needed)
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding

        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        raise ValueError(f"Failed to decode JWT: {e}")


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
    """Resolve the workspace id a human user owns (ADR-373 D1).

    The N=1 resolver: each user owns exactly one workspace. The binding unit is
    the EXISTING ``workspaces`` table (the billing/account root from
    001_initial_schema.sql), keyed by ``owner_id`` — confirmed 1:1 with users
    and already covering every substrate owner (migration 189 pre-flight). Uses
    the service client (the lookup must not depend on the caller's own RLS,
    which is mid-transition). Returns None if no workspace row exists yet —
    callers then fall back to ``user_id`` scoping, byte-identical in N=1.

    Cached per-process: the owner→workspace mapping is stable, so this is safe
    to memoize and keeps the hot auth path off a per-request DB round-trip.
    """
    return _resolve_owner_workspace_id_cached(user_id)


@lru_cache(maxsize=4096)
def _resolve_owner_workspace_id_cached(user_id: str) -> Optional[str]:
    try:
        client = get_service_client()
        result = (
            client.table("workspaces")
            .select("id")
            .eq("owner_id", user_id)
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

    # ADR-373 D1: resolve the binding workspace once, here, so every substrate
    # access through this auth keys on it without re-resolving. Cached + best-
    # effort — None pre-migration, where callers fall back to user_id scoping
    # (byte-identical in N=1). This adds no per-request DB round-trip after the
    # first resolution for a given user (lru_cache on the stable owner mapping).
    workspace_id = resolve_owner_workspace_id(user_id)

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
        # Release BOTH request-scoped httpx pools (postgrest + gotrue auth).
        close_supabase_client(client)


# Type alias for dependency injection
UserClient = Annotated[AuthenticatedClient, Depends(get_user_client)]
ServiceClient = Annotated[Client, Depends(get_service_client)]
