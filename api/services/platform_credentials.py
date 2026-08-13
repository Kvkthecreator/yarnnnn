"""Platform credential resolution — the single chokepoint (ADR-566 D4).

WHY THIS MODULE EXISTS
Before ADR-566 there was ONE credential store (`platform_connections` keyed
`user_id`, ADR-425 D1) and EIGHT inline lookups spelling `.eq("user_id",
auth.user_id)` across `services/platform_tools.py`. That was survivable with one
store. ADR-566 adds a second — the WORKSPACE's own allocated credential, the
one its agents act through — and eight independent call sites become eight
independent opportunities to read the wrong store.

That is the defect class ADR-563 closed for MCP scopes: the check belongs at the
seam that already resolves identity, never at each call site, and it FAILS
CLOSED. This module is that seam for credentials.

THE TWO STORES (ADR-566 D2) — disjoint, never a fallback for each other:

    a human's connector        →  keyed user_id      →  the member acts, and
                                                        their lane as their hands
    the workspace's connector  →  keyed workspace_id →  an `own-agent` principal
                                                        acts, gated by ADR-307

⚠️ NO CROSS-STORE FALLBACK, EVER ⚠️
An agent whose workspace credential is missing gets NOTHING — it does not
silently fall through to the owner's personal token. That fallback IS the
"reuse the owner's credential" branch ADR-566 D3 RETIRED, and it would arrive
through an error path where nobody chose it. It is also the ADR-548 shape: a
fallback degrading to a PLAUSIBLE value is worse than one that fails, because
the plausible one ships and nobody sees it. `resolve_platform_credential`
returns None and the caller reports "not connected".

⚠️ THIS GRANTS NO AUTHORITY ⚠️
Resolving a credential is REACH, not authority (ADR-566 D1). Every consequential
act through one still passes the ADR-307 gate and waits on the witness dial
(ADR-405 D2). An agent holding a workspace Slack credential can PROPOSE a Slack
write; it cannot SEND one without the gate's approval. Nothing here is a
bypass, and nothing here is a field on an agent row (ADR-460 D3.a — the cliff).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

#: The principal classes that act through the WORKSPACE's allocated credential.
#: `own-agent` is the live role programs already mint on activation
#: (`services/programs.py::HIRE_GRANT_ROLE`) — not a new class, not a reserved
#: enum. Every other principal reads its own account store or nothing.
_WORKSPACE_CREDENTIAL_ROLES = frozenset({"own-agent"})

#: The columns a credential read needs. Kept here so the two store reads cannot
#: drift apart in what they select (they are decrypted by the same manager).
_CREDENTIAL_COLUMNS = "credentials_encrypted, metadata, status"


def workspace_credential_filter(workspace_id: str) -> tuple:
    """The (column, value) scope for the WORKSPACE's own credential store.

    The counterpart to `workspace_context.account_scope_filter`, and the reason
    `platform_connections.workspace_id` exists: ADR-425 D3 retained the column
    for exactly this case and ADR-566 D3 makes it load-bearing. Always
    `("workspace_id", workspace_id)` — there is no user resolution, by design,
    because the whole point is that this credential belongs to no human.
    """
    return ("workspace_id", workspace_id)


def is_agent_principal(auth: Any) -> bool:
    """Does this caller act through the WORKSPACE's credential, not a human's?

    Reads the acting principal's GRANT ROLE — the same `principal_grants` fact
    the ADR-307 gate consults, resolved through the same uniform abstraction
    (`resolve_principal_id`, ADR-373 D2). `own-agent` is the workspace's own
    hired agent (`programs.py::HIRE_GRANT_ROLE`, minted on activation);
    everything else — owner, member, viewer, foreign-llm, a2a, platform — acts
    as or through a human and reads the account store.

    ⚠️ Deliberately the ROLE, never the `caller_identity` STRING. A lane stamps
    `member:{id} via {model}` (ADR-411 D4) and IS the member's hands, so it must
    resolve to the account store even though an AI is driving it. The grant is
    the fact; the string is a label. Keying on the string would hand a chat lane
    the workspace's credential, which is exactly the reach ADR-566 §7 refuses.

    FAILS CLOSED: any resolution failure returns False (the account store), the
    conservative answer — a human reading their own credential is always safe;
    a wrongly-classified agent reading the workspace's is the thing to prevent.
    """
    try:
        from services.principal_grants import _load_active_grant
        from services.supabase import resolve_principal_id

        principal_id = resolve_principal_id(auth)
        workspace_id = (getattr(auth, "workspace_id", None) or "").strip()
        if not principal_id or not workspace_id:
            return False
        grant = _load_active_grant(principal_id, workspace_id)
        role = ((grant or {}).get("role") or "").strip()
        return role in _WORKSPACE_CREDENTIAL_ROLES
    except Exception as exc:  # noqa: BLE001 — classification degrades to human
        logger.debug("[CREDENTIAL] principal classification failed: %s", exc)
        return False


def resolve_platform_credential(
    auth: Any, platform: str, *, workspace_id: Optional[str] = None
) -> Optional[dict]:
    """The ONE path to a platform credential row. Returns None when there is none.

    Selects the store from the acting principal ALONE (ADR-566 D4):

      - an `own-agent` principal  → the workspace's allocated credential
      - any human principal       → that human's account credential
      - an unrecognized principal → None (FAIL CLOSED)

    Returns the raw row ({credentials_encrypted, metadata, status}) — decryption
    stays with the caller's existing TokenManager so this module never holds a
    plaintext token. Never raises: a credential read that blows up must degrade
    to "not connected", never to a traceback on a member's turn.

    ⚠️ The two stores NEVER fall back to each other (D3/D4). If you find
    yourself wanting to add an `or` here, that is the retired owner-reuse branch
    asking to come back through an error path.
    """
    plat = (platform or "").strip()
    if not plat:
        return None

    if is_agent_principal(auth):
        ws = (workspace_id or getattr(auth, "workspace_id", None) or "").strip()
        if not ws:
            # An agent principal with no resolvable workspace has no credential
            # to reach. Refusing beats guessing — the alternative is reading
            # SOME human's store, which is the retired branch.
            logger.warning(
                "[CREDENTIAL] own-agent principal with no workspace — refusing "
                "(no cross-store fallback, ADR-566 D4)"
            )
            return None
        scope = workspace_credential_filter(ws)
    else:
        from services.workspace_context import account_scope_filter

        user_id = (getattr(auth, "user_id", None) or "").strip()
        if not user_id:
            logger.warning("[CREDENTIAL] no acting principal — refusing (fail closed)")
            return None
        scope = account_scope_filter(user_id)

    try:
        res = (
            auth.client.table("platform_connections")
            .select(_CREDENTIAL_COLUMNS)
            .eq(*scope)
            .eq("platform", plat)
            .eq("status", "active")
            .limit(1)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001 — a credential read degrades, never raises
        logger.error("[CREDENTIAL] %s lookup failed: %s", plat, exc)
        return None

    rows = res.data or []
    return rows[0] if rows else None


def connected_platforms(auth: Any, *, workspace_id: Optional[str] = None) -> set:
    """The platform names the ACTING PRINCIPAL has an active credential for.

    The enumeration counterpart to `resolve_platform_credential`, and it must
    live here for the same reason: the capability probe that gates which tools
    a caller is even OFFERED has to agree with the resolver that will later
    fetch the token. If the probe read the human's store while the resolver read
    the workspace's, an agent would be offered a tool whose credential it cannot
    reach — a capability that lies, which is the ADR-467 §1 Scout-bug shape.

    Never raises: an enumeration failure degrades to "nothing connected", which
    withholds tools rather than offering ones that cannot run.
    """
    if is_agent_principal(auth):
        ws = (workspace_id or getattr(auth, "workspace_id", None) or "").strip()
        if not ws:
            return set()
        scope = workspace_credential_filter(ws)
    else:
        from services.workspace_context import account_scope_filter

        user_id = (getattr(auth, "user_id", None) or "").strip()
        if not user_id:
            return set()
        scope = account_scope_filter(user_id)

    try:
        res = (
            auth.client.table("platform_connections")
            .select("platform, status")
            .eq(*scope)
            .eq("status", "active")
            .execute()
        )
        return {r["platform"] for r in (res.data or [])}
    except Exception as exc:  # noqa: BLE001 — degrade to withholding, never offer
        logger.error("[CREDENTIAL] connected-platform enumeration failed: %s", exc)
        return set()


def credential_missing_error(auth: Any, platform: str) -> dict:
    """The handler-shaped error for an absent credential — honest per store.

    The two stores fail differently and a member must be told which one, or the
    message sends them to a settings pane that cannot fix it: an agent's missing
    credential is a WORKSPACE allocation the owner makes, not something the
    member connects in their own account door.
    """
    plat = (platform or "").strip() or "platform"
    if is_agent_principal(auth):
        return {
            "success": False,
            "error": (
                f"No {plat} credential is allocated to this workspace. "
                "An owner can allocate one in Workspace Settings → Connectors."
            ),
        }
    return {
        "success": False,
        "error": f"No active {plat} integration. Connect it in Settings.",
    }
