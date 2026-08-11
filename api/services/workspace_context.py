"""Request-scoped workspace binding — ADR-373 Phase 1 (the sweep spine).

The substrate's binding unit is the WORKSPACE (ADR-373). The acting
workspace is resolved ONCE per request at the auth layer
(``get_user_client`` — owner workspace, or a granted workspace selected
via the ``X-Workspace-Id`` header) and published here as a contextvar, so
the data layer (``authored_substrate``, ``UserMemory``,
``AgentWorkspace``) can key queries on ``workspace_id`` WITHOUT threading
a new parameter through the ~118 historical call sites.

Fallback chain at the data layer (``effective_workspace_id``):
  1. an explicit ``workspace_id`` the caller passed;
  2. the request contextvar (set by the auth dependency);
  3. owner-resolution from ``user_id`` (the N=1 case; also correct for
     every service-key path — scheduler, wake, capture — which always
     operates a workspace AS its owner's steward).

A ``None`` result means "workspace unresolvable" and callers fall back to
legacy ``user_id`` scoping — byte-identical behavior, never a block.

⚠️ **ADR-548 D8 — rung 2 does NOT reach a FastAPI route handler.** The claim
above that the contextvar spares call sites from "threading a new parameter"
is FALSE for any route using the ``UserClient`` dependency. ``get_user_client``
is a *sync* generator, so FastAPI runs it in a threadpool: the contextvar is
set in the worker thread's context and the async handler — a different context
— reads ``None``. Resolution then falls to rung 3 and returns the CALLER'S OWN
workspace, which is a real workspace, so nothing errors and nothing is logged.

Receipted on prod 2026-08-11 (a member saw 1 document instead of 4):

    [SCOPE] artifacts user=2be30ac5 ws=d5b9029b
            scope=workspace_id=4ca9c664 rows=1

``ws=`` is the request's binding; ``scope=`` is what the query read.

**Therefore: any caller holding an ``auth`` MUST pass the binding** —
``substrate_scope_filter(auth.user_id, getattr(auth, "workspace_id", None))``.
Rung 2 remains load-bearing only for service-key paths (scheduler, wake,
capture) that set it in their own async context. Gated by
``test_adr548_primitive_scope_doorway.py``.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

# The workspace the current request acts on. None outside a request (or
# before the auth dependency ran) — data-layer callers then owner-resolve.
_current_workspace_id: ContextVar[Optional[str]] = ContextVar(
    "yarnnn_current_workspace_id", default=None
)


def set_request_workspace(workspace_id: Optional[str]):
    """Bind the acting workspace for this request context. Returns the token
    so the auth dependency can reset on teardown."""
    return _current_workspace_id.set(workspace_id)


def reset_request_workspace(token) -> None:
    try:
        _current_workspace_id.reset(token)
    except Exception:  # pragma: no cover — teardown is best-effort
        pass


def get_request_workspace() -> Optional[str]:
    return _current_workspace_id.get()


def effective_workspace_id(
    user_id: Optional[str], explicit: Optional[str] = None
) -> Optional[str]:
    """The data layer's single workspace-resolution rule (ADR-373 sweep).

    explicit > request contextvar > owner-resolution(user_id) > None.
    """
    if explicit:
        return explicit
    ctx = _current_workspace_id.get()
    if ctx:
        return ctx
    if user_id:
        try:
            # ADR-465 D2 (join-only genesis): a member-only principal owns no
            # workspace, so the fallback must honor grants — the
            # member-aware resolver, not the owner-only one.
            from services.supabase import resolve_workspace_for_principal
            return resolve_workspace_for_principal(user_id)
        except Exception:  # pragma: no cover — resolution is best-effort
            return None
    return None


def substrate_scope_filter(
    user_id: str, workspace_id: Optional[str] = None
) -> tuple:
    """The (column, value) scope for any WORKSPACE-CONTENT table query — the
    ONE helper every route/service uses (ADR-373 route sweep, generalized by
    ADR-407 Phase 1).

    Workspace-keyed when the acting workspace resolves (explicit auth value,
    request binding, or owner resolution); legacy user_id fallback otherwise
    (byte-identical in N=1). Applies to every table carrying workspace_id:
    the substrate pair (migration 189), execution_events (200), and the
    Phase-1 set — tasks, agents, agent_runs, activity_log, wake_queue,
    action_proposals (201). NOT for member-experience tables (chat_sessions,
    notifications, member_state) — those key on the principal. NOT for
    platform_connections — ADR-425 re-scoped the CREDENTIAL to the HUMAN's
    account (a platform credential is an account object); use
    account_scope_filter for it, per the ADR-407 §3 scope registry.

    `sync_registry` is the nuance (ADR-548 sharpened this line, which used to
    lump it in with platform_connections): ADR-425 D3 keeps it declared
    `content` for the future agent-owned connection, but every row that exists
    TODAY is a human's and is keyed `user_id`. So it reads with the account
    filter in practice while staying content-scoped in the manifest. The
    ADR-548 doorway gate carries that exception explicitly rather than letting
    two docs disagree.
    """
    ws = effective_workspace_id(user_id, workspace_id)
    return ("workspace_id", ws) if ws else ("user_id", user_id)


def account_scope_filter(user_id: str) -> tuple:
    """The (column, value) scope for an ACCOUNT-scoped table query — a store
    that belongs to the HUMAN across workspaces, keyed by `user_id` alone
    (ADR-407 §3 D1 account scope).

    Introduced by ADR-425 for `platform_connections` / `sync_registry`: a
    human's platform credential (Slack, Drive, Notion, GitHub) is their own
    account object, not a workspace peripheral — so its reads key on the human,
    never on the acting workspace. Always `("user_id", user_id)`; there is no
    workspace resolution, by design. (The vestigial `workspace_id` column on
    those tables is reserved for the future D3 agent-owned connection, which
    would use its own scope — not this helper.)
    """
    return ("user_id", user_id)


def acting_workspace_owner(
    client, user_id: str, workspace_id: Optional[str] = None
) -> str:
    """Resolve the OWNER user id of the acting workspace (ADR-408 D2).

    The Freddie/wake stack is keyed by the workspace owner's user_id (its
    documented contract: "user_id: Workspace owner UUID"). When a MEMBER
    addresses the steward (chat, FireInvocation, MCP write), the wake must
    run FOR THE COMMONS — so the request-layer seams resolve
    acting-workspace → owner before entering the stack, while the member
    stays the attributed principal. Owner fallback == the caller themselves,
    byte-identical in N=1. Best-effort: any failure returns the caller
    (their own lane — never a block).
    """
    try:
        # ADR-501 (probe 2026-07-29): pass the EXPLICIT binding when the caller
        # holds it. Omitting it fell through to the contextvar/owner path, so a
        # member resolved their OWN workspace and every owner-keyed stack
        # (radar, emissions, the wake) ran against the wrong one.
        ws = effective_workspace_id(user_id, workspace_id)
        if not ws:
            return user_id
        # SERVICE client, deliberately: `workspaces` RLS is
        # `owner_id = auth.uid()`, so a MEMBER resolving the owner of a
        # workspace they hold an active grant in reads ZERO rows and silently
        # falls back to themselves — which is exactly the wrong key for every
        # owner-keyed lookup downstream. The owner id of a workspace the caller
        # is already bound to is not a secret; `effective_workspace_id` above
        # is the authorization step (a member only resolves a workspace they
        # reach). Passing `client` in is preserved for callers that hand us a
        # service client already; we no longer DEPEND on them doing so.
        from services.supabase import get_service_client

        row = (
            get_service_client()
            .table("workspaces")
            .select("owner_id")
            .eq("id", ws)
            .limit(1)
            .execute()
        )
        rows = getattr(row, "data", None) or []
        owner = rows[0].get("owner_id") if rows else None
        return owner or user_id
    except Exception:
        return user_id


__all__ = [
    "set_request_workspace",
    "reset_request_workspace",
    "get_request_workspace",
    "effective_workspace_id",
    "substrate_scope_filter",
    "acting_workspace_owner",
]
