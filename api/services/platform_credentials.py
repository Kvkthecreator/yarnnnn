"""Platform credential resolution — the single chokepoint (ADR-566 D4).

WHY THIS MODULE EXISTS
There was ONE credential store (`platform_connections` keyed `user_id`,
ADR-425 D1) and EIGHT inline lookups spelling `.eq("user_id", auth.user_id)`
across `services/platform_tools.py` — eight independent opportunities to read
the wrong row, or to forget the agent question entirely.

That is the defect class ADR-563 closed for MCP scopes: the check belongs at the
seam that already resolves identity, never at each call site, and it FAILS
CLOSED. This module is that seam for credentials. ADR-566 introduced a second
store here; ADR-577 withdrew it (§ below). The seam is what had lasting value.

THE ONE STORE (ADR-577 D1) — a human's account credential, keyed `user_id`:

    a human's connector  →  keyed user_id  →  the member acts, and their lane
                                              as their hands

⚠️ AN AGENT GETS NOTHING, AND IS TOLD SO ⚠️
An agent-shaped caller is REFUSED a credential here and logged at WARNING. It
does not fall through to the owner's personal token. That fallback is the
"reuse the owner's credential" branch ADR-425 D3 RETIRED and ADR-566 D2
forbade — and until ADR-577 it was what production actually did, because the
guard that forbade it keyed on a grant role (`own-agent`) that ZERO rows hold,
behind a `workspace_id` that `HeadlessAuth` never carried. The refusal below
keys on what the auth object ACTUALLY carries, so it is reachable.

⚠️ THERE IS NO WORKSPACE CREDENTIAL STORE ⚠️
ADR-566's second store is withdrawn (ADR-577 D1/D3): it was unfillable (no
allocation route), mis-filled (migration 201's owner-fill trigger stamped every
human connect into it), and unreadable (RLS is `user_id = auth.uid()`).
`platform_connections.workspace_id` means ROUTING — which workspace a
credential feeds (ADR-425 AD1) — never ownership. Do not re-read it as a store.

⚠️ THIS GRANTS NO AUTHORITY ⚠️
Resolving a credential is REACH, not authority (ADR-566 D1). Every consequential
act through one still passes the ADR-307 gate and waits on the witness dial
(ADR-405 D2).

⚠️ RE-ENTRY TEST (ADR-577 §7) ⚠️
Before any future change may claim an agent acts through a workspace
credential, it must exhibit a DRIVEN TRACE — a real auth object, through this
resolver, returning the workspace row. Not a passing gate. Not a docstring.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

#: Caller-identity prefixes that mark an AGENT-shaped caller (ADR-577 D1.a).
#: These are what `HeadlessAuth` actually stamps (`registry.py`: "specialist:{role}")
#: and what agent dispatch paths carry — as opposed to a member's lane, which
#: stamps `member:{id} via {model}` (ADR-411 D4) and IS the member's hands.
#:
#: ⚠️ Keyed on the caller identity, deliberately, because that is the fact the
#: auth object CARRIES. ADR-566 keyed the same question on a `principal_grants`
#: role (`own-agent`) — the more principled fact — and the guard was therefore
#: UNREACHABLE: zero rows hold that role, and `HeadlessAuth` carries no
#: `workspace_id` to look one up with. A principled guard that never runs
#: protects nothing. Re-key this on the grant ONLY together with a driven trace
#: (ADR-577 §7).
_AGENT_CALLER_PREFIXES = ("specialist:", "agent:")

#: The columns a credential read needs. Kept here so the two store reads cannot
#: drift apart in what they select (they are decrypted by the same manager).
_CREDENTIAL_COLUMNS = "credentials_encrypted, metadata, status"


def is_agent_caller(auth: Any) -> bool:
    """Is this caller an AGENT acting on its own, rather than a human's hands?

    ADR-577 D1.a. True for headless agent dispatch (`HeadlessAuth`, which stamps
    `caller_identity = "specialist:{role}"`). False for a member, and false for
    a member's chat LANE — a lane stamps `member:{id} via {model}` and is the
    member's hands, so it correctly reads that member's account store even
    though an AI is driving it.

    FAILS TOWARD REFUSAL for agents: an unreadable caller identity on a
    `headless` auth is treated as an agent, because the cost of wrongly refusing
    an agent (a tool reports "not connected") is far below the cost of wrongly
    handing it a human's personal OAuth token.
    """
    identity = (getattr(auth, "caller_identity", None) or "").strip().lower()
    if identity.startswith(_AGENT_CALLER_PREFIXES):
        return True
    # A headless auth with no legible identity is agent-shaped by construction —
    # only agent dispatch builds one (`registry.py::HeadlessAuth`).
    return bool(getattr(auth, "headless", False)) and not identity.startswith("member:")


def resolve_platform_credential(
    auth: Any, platform: str, *, workspace_id: Optional[str] = None
) -> Optional[dict]:
    """The ONE path to a platform credential row. Returns None when there is none.

    Selects from the acting principal ALONE (ADR-566 D4, as amended by ADR-577):

      - an AGENT caller           → None (REFUSED — no workspace store exists)
      - any human principal       → that human's account credential
      - an unrecognized principal → None (FAIL CLOSED)

    Returns the raw row ({credentials_encrypted, metadata, status}) — decryption
    stays with the caller's existing TokenManager so this module never holds a
    plaintext token. Never raises: a credential read that blows up must degrade
    to "not connected", never to a traceback on a member's turn.

    ⚠️ An agent NEVER falls through to a human's credential. If you find
    yourself wanting to add an `or` here, that is the retired owner-reuse branch
    asking to come back through an error path — and until ADR-577 it succeeded,
    because the guard that forbade it could not run.
    """
    plat = (platform or "").strip()
    if not plat:
        return None

    if is_agent_caller(auth):
        # ADR-577 D1.a — the refusal that ADR-566 D2 specified and could not
        # reach. An agent has no credential of its own (the workspace store is
        # withdrawn), and the owner's personal token is not a substitute.
        logger.warning(
            "[CREDENTIAL] agent caller (%s) requested %s — REFUSING; agents hold "
            "no platform credential (ADR-577 D1). Not falling through to a "
            "human's token.",
            (getattr(auth, "caller_identity", None) or "unknown"), plat,
        )
        return None

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
    if is_agent_caller(auth):
        # Agents hold no credential (ADR-577 D1), so they are offered no
        # platform tool. This MUST agree with resolve_platform_credential above
        # or an agent is offered a tool whose token it cannot reach — the
        # ADR-467 §1 "capability that lies" shape.
        return set()

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
    if is_agent_caller(auth):
        # Honest about WHY, and it does not send anyone to a pane that cannot
        # fix it: no allocation surface exists (ADR-577 D3). Connecting the
        # platform in a member's own account door would NOT grant this agent
        # reach, so the message must not imply that it would.
        return {
            "success": False,
            "error": (
                f"Agents hold no {plat} credential. Platform reach for agents "
                "is not available (ADR-577)."
            ),
        }
    return {
        "success": False,
        "error": f"No active {plat} integration. Connect it in Settings.",
    }
