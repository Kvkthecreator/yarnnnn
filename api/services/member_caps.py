"""Per-member spend caps — the owner's abuse lever over the shared pool (ADR-445
§7 Phase 4; ADR-391 Layer ②).

The two-axis model (ADR-445) makes the metered pool ONE shared, owner-funded pool
(Axis ②). The owner's control over an individual member's draw is NOT a per-member
billing relationship (that would undo ADR-416's workspace-as-billing-unit) — it is a
CAP: "this principal may draw ≤ $X of the shared pool this cycle." Seats are revenue;
caps are safety; the pool hard-stop is the backstop (ADR-445 §4, three distinct
mechanisms).

Substrate: `governance/_member_caps.yaml` (machine-parsed; ADR-254 underscore
prefix). A map of principal_id → cap_usd. Owner-authored only (the owner bounds a
member; a member cannot lift their own cap — the file is in the locked governance/
root, ADR-320). Absent file / absent key = UNCAPPED (the default: draw the whole
pool, backstopped by the hard-stop).

The gate (`check_member_cap`) compares the acting principal's spend-since-anchor
(the same `spend_by_principal` window the balance gate + Usage pane use) against
their cap. It is a READ-side gate layered ON TOP of the pool hard-stop: the pool
hard-stop still governs the workspace total; this only bounds one principal's slice.
The owner is never capped (no self-lockout — ADR-386 D4 parity).

Fail-safe: any read/parse error → UNCAPPED (an abuse cap must never block a legit
draw over a transient hiccup; the pool hard-stop remains the hard backstop).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _caps_path() -> str:
    from services.workspace_paths import GOVERNANCE_MEMBER_CAPS_PATH
    return f"/workspace/{GOVERNANCE_MEMBER_CAPS_PATH}"


def load_member_caps(client: Any, user_id: str) -> dict[str, float]:
    """Read the per-principal cap map for the workspace. {principal_id: cap_usd}.

    Empty on absent file / parse error (UNCAPPED default). Only positive numeric
    caps are kept — a zero/negative/non-numeric entry is dropped (a 0 cap would be
    a total lockout better expressed via Revoke/Narrow, not a spend cap)."""
    try:
        res = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", _caps_path())
            .limit(1)
            .execute()
        )
        content = (res.data or [{}])[0].get("content") or ""
    except Exception as exc:  # noqa: BLE001 — fail-safe to uncapped
        logger.warning("[MEMBER_CAPS] read failed for %s: %s", user_id[:8], exc)
        return {}

    if not content.strip():
        return {}

    try:
        import yaml  # type: ignore
        parsed = yaml.safe_load(content) or {}
    except Exception as exc:  # noqa: BLE001
        logger.warning("[MEMBER_CAPS] YAML parse failed for %s: %s", user_id[:8], exc)
        return {}

    if not isinstance(parsed, dict):
        return {}
    caps_block = parsed.get("caps")
    if not isinstance(caps_block, dict):
        caps_block = parsed  # tolerate a bare top-level map too

    out: dict[str, float] = {}
    for pid, cap in caps_block.items():
        if isinstance(cap, (int, float)) and cap > 0:
            out[str(pid)] = float(cap)
    return out


def get_member_cap(client: Any, user_id: str, principal_id: str) -> Optional[float]:
    """The cap for one principal, or None (uncapped)."""
    return load_member_caps(client, user_id).get(principal_id)


def check_member_cap(
    client: Any,
    user_id: str,
    acting_principal_id: Optional[str],
    workspace_id: Optional[str] = None,
) -> tuple[bool, Optional[float], float]:
    """Is the acting principal within their per-member cap on the shared pool?

    Returns (allowed, cap_usd_or_None, spent_usd). `allowed` is True when there is
    no cap (the default) or the principal's spend-since-anchor is below their cap.
    The OWNER (acting_principal_id == the workspace owner / user_id) is never
    capped. Fail-safe: any error → allowed=True (the pool hard-stop is the backstop).
    """
    if not acting_principal_id:
        return True, None, 0.0
    try:
        # The owner is never capped (no self-lockout).
        from services.workspace_context import effective_workspace_id
        ws = workspace_id or effective_workspace_id(user_id)
        owner_id = None
        if ws:
            row = (
                client.table("workspaces").select("owner_id").eq("id", ws).limit(1).execute()
            ).data
            owner_id = (row[0].get("owner_id") if row else None)
        if acting_principal_id in {owner_id, user_id}:
            return True, None, 0.0

        cap = load_member_caps(client, user_id).get(acting_principal_id)
        if cap is None:
            return True, None, 0.0

        # Spend-since-anchor for THIS principal (same window the pool gate uses).
        from services.platform_limits import spend_by_principal
        rows = spend_by_principal(client, user_id, workspace_id=ws)
        spent = next(
            (float(r.get("spend_usd") or 0) for r in rows
             if r.get("principal_id") == acting_principal_id),
            0.0,
        )
        return (spent < cap), cap, spent
    except Exception as exc:  # noqa: BLE001 — fail-safe to allowed (pool hard-stop backstops)
        logger.warning("[MEMBER_CAPS] cap check failed for %s: %s", user_id[:8], exc)
        return True, None, 0.0


def set_member_cap(
    client: Any,
    user_id: str,
    principal_id: str,
    cap_usd: Optional[float],
    *,
    authored_by: str = "operator",
) -> dict[str, float]:
    """Owner sets (or clears, cap_usd=None/≤0) a principal's cap. Writes the sidecar
    through the authored-substrate write path. Returns the new cap map.

    Owner-only is enforced at the route (the governance/ root is owner-locked, ADR-320);
    this helper is the write mechanism. The owner's OWN principal id is never written
    (no self-cap — parity with the gate's owner carve)."""
    caps = load_member_caps(client, user_id)
    # Never cap the owner themselves.
    ws_owner = None
    try:
        from services.workspace_context import effective_workspace_id
        ws = effective_workspace_id(user_id)
        if ws:
            row = (client.table("workspaces").select("owner_id").eq("id", ws).limit(1).execute()).data
            ws_owner = row[0].get("owner_id") if row else None
    except Exception:  # noqa: BLE001
        ws_owner = None
    if principal_id in {ws_owner, user_id}:
        raise ValueError("the owner cannot be spend-capped")

    if cap_usd is None or cap_usd <= 0:
        caps.pop(principal_id, None)
    else:
        caps[principal_id] = round(float(cap_usd), 2)

    import yaml  # type: ignore
    body = (
        "# governance/_member_caps.yaml — per-member spend caps (ADR-445 §7 Phase 4)\n"
        "# Owner-authored. Each entry bounds a principal's draw from the shared pool\n"
        "# this cycle. Absent = uncapped. Clearing a cap removes its key.\n"
        + yaml.safe_dump({"caps": caps}, sort_keys=True)
    )

    from services.authored_substrate import write_revision
    from services.workspace_paths import GOVERNANCE_MEMBER_CAPS_PATH
    write_revision(
        client,
        user_id=user_id,
        path=f"/workspace/{GOVERNANCE_MEMBER_CAPS_PATH}",
        content=body,
        authored_by=authored_by,
        message=f"set member cap: {principal_id[:8]} → {caps.get(principal_id, 'cleared')}",
    )
    return caps


__all__ = [
    "load_member_caps",
    "get_member_cap",
    "check_member_cap",
    "set_member_cap",
]
