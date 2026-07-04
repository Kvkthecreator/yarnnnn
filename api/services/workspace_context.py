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
            from services.supabase import resolve_owner_workspace_id
            return resolve_owner_workspace_id(user_id)
        except Exception:  # pragma: no cover — resolution is best-effort
            return None
    return None


__all__ = [
    "set_request_workspace",
    "reset_request_workspace",
    "get_request_workspace",
    "effective_workspace_id",
]
