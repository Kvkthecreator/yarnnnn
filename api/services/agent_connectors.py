"""Agent connector opt-in — which granted connectors a being works against.

ADR-612. Three layers, each narrowing the one above:

    workspace  GRANT   which connectors exist here at all      (platform_connections)
    agent      OPT-IN  which of those THIS being works against (here)
    declaration ASK    which slices THIS file pulls            (_string.yaml)

⭐ THE CLIFF TEST (ADR-596 D1 / ADR-460 D3.a). An opt-in is NOT authority on a
being, because it can only ever NARROW what the workspace already granted, and
that is enforced rather than asserted: `allowed_platforms` intersects the
opt-in against the platforms actually reachable, so an opt-in naming a platform
the member never connected yields nothing. **There is no value of this field
that widens anything** — which is the whole difference between a preference
about a being and power granted to one.

⭐ WHY member_state AND NOT the being's row. The registry row is KERNEL code and
its `AGENT_ROW_KEYS` whitelist deliberately admits no reach-shaped key. A
member's preference about a kernel being is not a property of the being; it is
member data, and `member_state` is its established home (the ADR-489 D5
notification-prefs precedent): workspace-scoped by primary key, service-role
RLS with the API mediating authorization, already swept by the purge paths.

⭐ ABSENT ≠ EMPTY, and the default is load-bearing. No record = everything
granted, which is exactly today's behaviour: an opt-in defaulting to "nothing"
would silently break every existing lane the day it deployed, and a scoping
feature whose rollout is a regression is not a scoping feature. An explicit
empty list is a DIFFERENT and meaningful state — the member said "no platforms."
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

#: The `member_state.key` this lives under. One key holding the whole map
#: (`{slug: [platform, ...]}`) rather than a key per being: the pane reads and
#: writes every being's setting in one round-trip, and a per-being key would
#: make "what is scoped where" an N-read question.
MEMBER_STATE_KEY = "agent_connectors"


def _read_map(client: Any, workspace_id: str, principal_id: str) -> dict:
    """The raw opt-in map, or {} — never raises.

    A read failure must degrade to "no opt-in recorded" (= everything granted,
    per the module docstring), NOT to "nothing allowed": a transient DB error
    that silently stripped a being's tools would look exactly like a working
    scope the member never set.
    """
    try:
        rows = (
            client.table("member_state")
            .select("value")
            .eq("workspace_id", workspace_id)
            .eq("principal_id", principal_id)
            .eq("key", MEMBER_STATE_KEY)
            .limit(1)
            .execute()
        ).data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[AGENT_CONNECTORS] read failed ws=%s: %s",
                       str(workspace_id)[:8], exc)
        return {}
    if not rows:
        return {}
    value = rows[0].get("value")
    return value if isinstance(value, dict) else {}


def opt_in_for(
    client: Any,
    workspace_id: str,
    principal_id: str,
    agent_slug: Optional[str],
) -> Optional[list[str]]:
    """This being's declared opt-in, or None when it has none.

    None (absent) and [] (explicitly empty) are DIFFERENT — see the module
    docstring. Callers must not collapse them with `or []`.
    """
    if not agent_slug or not workspace_id or not principal_id:
        return None
    entry = _read_map(client, workspace_id, principal_id).get(agent_slug)
    if not isinstance(entry, list):
        return None
    return [str(p).strip().lower() for p in entry if str(p).strip()]


def allowed_platforms(
    reachable: tuple | list,
    opt_in: Optional[list[str]],
) -> tuple:
    """The platforms a being may work against — the NARROWING, pure.

    `reachable` is what the turn could otherwise reach (the grant side).
    `opt_in` is the being's declaration, or None for "not scoped".

    This is the function that makes the cliff test hold: the result is always
    a SUBSET of `reachable`, so an opt-in naming something ungranted adds
    nothing. Order follows `reachable` so the frame prose reads consistently
    rather than in whatever order the member happened to click.
    """
    if opt_in is None:
        return tuple(reachable)
    wanted = {p.strip().lower() for p in opt_in if p and p.strip()}
    return tuple(p for p in reachable if p in wanted)


def set_opt_in(
    client: Any,
    workspace_id: str,
    principal_id: str,
    agent_slug: str,
    platforms: Optional[list[str]],
) -> dict:
    """Record (or clear) one being's opt-in; returns the whole updated map.

    `platforms=None` DELETES the entry — back to "not scoped" (everything
    granted), which is a real state a member must be able to return to and is
    not the same as passing []. Read-modify-write on the single key: the map is
    a handful of slugs, and one key keeps the pane's read to one round-trip.
    """
    current = _read_map(client, workspace_id, principal_id)
    if platforms is None:
        current.pop(agent_slug, None)
    else:
        current[agent_slug] = [
            str(p).strip().lower() for p in platforms if str(p).strip()
        ]
    client.table("member_state").upsert(
        {
            "workspace_id": workspace_id,
            "principal_id": principal_id,
            "key": MEMBER_STATE_KEY,
            "value": current,
        },
        on_conflict="workspace_id,principal_id,key",
    ).execute()
    return current


def read_all(client: Any, workspace_id: str, principal_id: str) -> dict:
    """Every being's opt-in in this workspace, for the pane. Never raises."""
    return _read_map(client, workspace_id, principal_id)


__all__ = [
    "MEMBER_STATE_KEY",
    "allowed_platforms",
    "opt_in_for",
    "read_all",
    "set_opt_in",
]
