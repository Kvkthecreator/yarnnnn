"""Principal-commons helpers — the shared home for "who is a principal of this
workspace, and what may they write" (ADR-373 + the 2026-06-30 steward-envelope
re-scope).

Relocated here from `routes/workspace.py` so BOTH the legibility surface (the
Workspace Members / External Agents pane) and the steward's wake envelope read
the SAME roster logic (Singular Implementation). A route is a presentation
boundary; a service is shared logic — the envelope (a service) must not import
from a route.

The principal-vs-peripheral distinction (the analysis
`docs/analysis/perception-and-the-principal-commons-first-principles-2026-06-30.md`):
a PRINCIPAL is an intent-bearing, grant-backed, self-attributing identity (the
owner, members, own-agents, foreign LLMs, A2A callers — the rows of
`principal_grants`). A PERIPHERAL (web feed, broker API) is a driver-class
transport with no intent, attributed to the `system:` mechanism that operated it
— it is NOT a principal and does NOT appear here. The steward judges HONESTY over
principals (this module's roster is the referent) and HEALTH over peripherals
(a separate fact).
"""
from __future__ import annotations

from typing import Any, Optional

#: The six semantic-class roots, for rendering the class-default write-region set
#: as the COMPLEMENT of CALLER_WRITE_POLICY's locked prefixes (ADR-320 topology).
_ALL_WRITE_ROOTS = (
    "governance/", "constitution/", "persona/", "operation/", "system/", "contract/",
)

#: principal_grants.role → the CALLER_WRITE_POLICY class key whose default the
#: role inherits (ADR-373 D3 table). owner→operator, foreign-llm→mcp,
#: own-agent/member→agent (the member ceiling), platform/a2a→mcp (lowest-trust).
_ROLE_TO_CLASS = {
    "owner": "operator",
    "member": "agent",
    "own-agent": "agent",
    "foreign-llm": "mcp",
    "platform": "mcp",
    "a2a": "mcp",
}


def class_default_write_regions(role: str) -> list[str]:
    """The write-region set a role inherits from its class default (the
    complement of the class's locked prefixes in CALLER_WRITE_POLICY)."""
    from services.workspace_paths import CALLER_WRITE_POLICY
    klass = _ROLE_TO_CLASS.get(role, "agent")
    locked = set(CALLER_WRITE_POLICY.get(klass, ()))
    return [r for r in _ALL_WRITE_ROOTS if r not in locked]


def load_principal_roster(client: Any, user_id: str) -> list[dict]:
    """Read the active principal grants for the workspace this user owns, with
    each grant's resolved write-region set and a humanized label.

    Returns a list of dicts: {principal_id, role, label, write_regions,
    scopes_explicit}. Empty list when no workspace row exists yet (pre-substrate)
    — never raises (perception is a flow, never a gate).

    Used by BOTH the Workspace Members route (GET /api/workspace/members) and the
    steward wake envelope's principal-commons fact. service-client read: the
    grant table is the gate's authority; membership RLS is mid-transition and the
    lookup is already scoped to the resolved owner-workspace.
    """
    from services.supabase import get_service_client, resolve_owner_workspace_id

    workspace_id = resolve_owner_workspace_id(user_id)
    if not workspace_id:
        return []

    svc = get_service_client()
    rows = (
        svc.table("principal_grants")
        .select("principal_id, role, scopes, status, granted_by, created_at")
        .eq("workspace_id", workspace_id)
        .eq("status", "active")
        .order("created_at")
        .execute()
    ).data or []

    # Humanize foreign-LLM / platform / a2a principals (their principal_id is an
    # OAuth client_id) to their registered room name. Owner is humanized by the
    # caller that knows the auth email; here we leave owner label None.
    client_names: dict[str, str] = {}
    client_ids = [
        r["principal_id"] for r in rows
        if r.get("role") in ("foreign-llm", "platform", "a2a")
    ]
    if client_ids:
        try:
            name_rows = (
                svc.table("mcp_oauth_clients")
                .select("client_id, client_name")
                .in_("client_id", client_ids)
                .execute()
            ).data or []
            client_names = {r["client_id"]: r.get("client_name") for r in name_rows}
        except Exception:
            pass  # best-effort humanization

    roster: list[dict] = []
    for r in rows:
        role = r.get("role") or "member"
        principal_id = r["principal_id"]
        scopes = r.get("scopes")
        explicit = bool(scopes)
        write_regions = list(scopes) if explicit else class_default_write_regions(role)
        label: Optional[str] = None
        if role in ("foreign-llm", "platform", "a2a"):
            label = client_names.get(principal_id) or principal_id
        roster.append({
            "principal_id": principal_id,
            "role": role,
            "label": label,
            "write_regions": write_regions,
            "scopes_explicit": explicit,
        })
    return roster
