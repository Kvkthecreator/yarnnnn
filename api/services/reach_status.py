"""
Reach status — ONE structure per first-party connection (ADR-644).

Four faces used to describe what a connection lets a turn do: the tool
definitions a lane holds (structurally true, invisible as a description),
three hand-written prose branches in the lane frame, the `list_integrations`
tool result (platform + status, nothing more) and `connector_does` (prose for
the member's Connectors page, derived from three sources). The first Reach
click-pass put two of them on one screen and they disagreed — the surface
claimed an agent write path the lane has never held.

ADR-635 already solved this for attached connectors: `attached_surface` is one
structure feeding the tools, the frame paragraph and the settings pane. This
module is the same rule for first-party connections:

    connection_rows(client, user_id)      → the member's rows, metadata only
    platform_reach(platform, …)           → the facts for ONE platform, derived
    reach_status(rows, …)                 → the facts per connection row
    describe(facts)                       → the member face (reads · writes · chat · agents)
    frame_paragraph(status, member, …)    → the agent face (the frame's reach section)

Every fact derives from the machinery that enacts it — the capture binding,
the live tool surface, the gate's family classifier, the publish seam's door
roster. Nothing here is stored (DP29) and nothing here DECIDES: consent,
selection and aperture are Settings acts (ADR-594 D1); scope is the agent
page's (ADR-612/615). This module reads the decision and says it the same way
to everyone.

⭐ A registry row is not a live path. `agent_writes` intersects the capability
registry with the tools a lane actually composes; the registry alone still
carries `write_slack` for the task pipeline ADR-231 deleted.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

ATTACHED_PREFIX = "mcp:"

#: The ADR-535 D2 boundary: seeing a connection is not reaching it. Metadata
#: only — never a credential column, never a provider call.
_ENUMERATION_COLUMNS = "id, platform, status, metadata, created_at, updated_at"


def is_attached(platform: Any) -> bool:
    return str(platform or "").startswith(ATTACHED_PREFIX)


def connection_rows(client: Any, user_id: str) -> list[dict]:
    """Every connection this member holds — first-party and attached —
    account-scoped (ADR-425: a credential is the HUMAN's), metadata only.
    The ONE enumeration reader every face uses. Never raises."""
    try:
        res = (
            client.table("platform_connections")
            .select(_ENUMERATION_COLUMNS)
            .eq("user_id", user_id)
            .order("platform")
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[REACH] connection rows unreadable for %s: %s", (user_id or "")[:8], exc)
        return []
    return [r for r in (res.data or []) if r.get("platform")]


def platform_reach(
    platform: str,
    *,
    reach_on: bool,
    scoped_platforms: Optional[tuple] = None,
) -> Optional[dict]:
    """The reach facts for ONE first-party platform, derived. None when the
    platform has no binding, no door, no read roster and no live write tool
    (an unbound platform fabricates no facts — ADR-582 7o).

    `scoped_platforms` is the turn's narrowing (`resolve_turn_reach`): None =
    every granted platform; a tuple = exactly those; () = none.
    """
    plat = (platform or "").strip().lower()
    if not plat or is_attached(plat):
        return None
    from services.connectors import CONNECTOR_CAPTURE_BINDINGS, platform_display_name
    from services.platform_tools import (
        PLATFORM_TOOLS_BY_CAPABILITY,
        consequential_platform_family,
    )
    from services.publish import PUBLISH_DOORS
    from services.turn_reach import turn_reach_tool_names

    binding = CONNECTOR_CAPTURE_BINDINGS.get(plat)
    door = PUBLISH_DOORS.get(plat)
    try:
        live = tuple(turn_reach_tool_names((plat,)))
    except Exception:  # noqa: BLE001
        live = ()
    agent_writes = [
        {"tool": t, "mode": "propose" if consequential_platform_family(t) else "direct"}
        for t in PLATFORM_TOOLS_BY_CAPABILITY.get(f"write_{plat}", [])
        if t in live
    ]
    if binding is None and door is None and not live and not agent_writes:
        return None
    return {
        "platform": plat,
        "name": platform_display_name(plat),
        # What a CAPTURE reads — the binding's own statement (ADR-582 7m).
        "captures": binding["reads"] if binding else None,
        # The read tools a lane composes for this platform (the live surface).
        "reads": list(live),
        # Write tools composed into a live loop, each with its gate mode.
        "agent_writes": agent_writes,
        # The member's own acts: verb · door · pane · what it takes (ADR-628).
        "member_doors": [dict(door, platform=plat)] if door else [],
        "reach_on": bool(reach_on),
        "in_scope": None if scoped_platforms is None else (plat in tuple(scoped_platforms)),
    }


def reach_status(
    rows: list[dict],
    *,
    reach_on: bool,
    scoped_platforms: Optional[tuple] = None,
) -> list[dict]:
    """The facts per FIRST-PARTY connection row, with target + status. Attached
    rows are skipped — they keep ADR-635's own structure (`attached_surface`)."""
    from services.connectors import connection_target, platform_display_name

    out: list[dict] = []
    for r in rows or []:
        plat = str(r.get("platform") or "").strip().lower()
        if not plat or is_attached(plat):
            continue
        facts = platform_reach(plat, reach_on=reach_on, scoped_platforms=scoped_platforms) or {
            "platform": plat,
            "name": platform_display_name(plat),
            "captures": None,
            "reads": [],
            "agent_writes": [],
            "member_doors": [],
            "reach_on": bool(reach_on),
            "in_scope": None if scoped_platforms is None else (plat in tuple(scoped_platforms)),
        }
        md = r.get("metadata") or {}
        facts["status"] = r.get("status")
        facts["target"] = connection_target(plat, md)
        facts["connected_at"] = r.get("created_at")
        out.append(facts)
    return out


# ---------------------------------------------------------------------------
# The two renderers. Sentences, never facts of their own.
# ---------------------------------------------------------------------------

def _first_verb(door: dict) -> str:
    return (door.get("verb") or "publish").split()[0]


def describe(facts: Optional[dict]) -> Optional[dict]:
    """The MEMBER face — the four rows the Connectors page and Reach state
    (reads · writes · chat · agents). Every sentence is rendered from the
    facts; the ADR-585 D5 engine disclosure keeps its validated words."""
    if not facts:
        return None
    name = facts["name"]
    door = (facts.get("member_doors") or [None])[0]
    agent_writes = facts.get("agent_writes") or []
    reads_any = bool(facts.get("reads"))
    reach_on = bool(facts.get("reach_on"))

    reads = facts.get("captures") or f"nothing — yarnnn never captures from {name}"

    if door:
        writes = (
            f"only when you {door['verb']} to {name} from the {door['pane']} pane "
            f"({door['door']}) — your click, receipted beside the file, never scheduled"
            + (
                f"; an agent's {name} post goes out only through a proposal you approve"
                if agent_writes
                else ""
            )
        )
    elif agent_writes:
        writes = (
            f"only through a proposal you approve — an agent's {name} post waits in "
            "your queue for the decision"
        )
    else:
        writes = f"nothing — yarnnn never writes to {name}"

    if not reads_any:
        chat = f"chat does not read {name} — " + (
            f"this connection carries only your own {door['door']} clicks"
            if door
            else "nothing reads it"
        )
    elif reach_on:
        chat = (
            f"your chat can read {name} through your own connection — read-only, in "
            "the turn, nothing saved unless you ask. What it reads goes to the engine "
            "you picked for that chat, the same as pasting it in"
        )
    else:
        chat = "chat cannot reach platforms on this deployment"

    if not reads_any and door:
        agents = (
            f"agents never {_first_verb(door)} to {name} — that is your click, with "
            "your credential"
        )
    elif reach_on:
        agents = (
            f"an agent you scope to {name} reads it while you're working with it — "
            "never on its own schedule, where it reads landed files only"
        )
    else:
        agents = "no direct platform access — agents read the landed capture files only"
    if agent_writes:
        agents += (
            f". An agent's {name} post never goes out on its own — it lands in your "
            "queue as a proposal for your decision"
        )
    elif door and reads_any:
        agents += (
            f". It cannot {door['verb']} there — that is your click, from the "
            f"{door['pane']} pane ({door['door']})"
        )

    return {"reads": reads, "writes": writes, "chat": chat, "agents": agents}


def _row_line(facts: dict, member: str, *, reach_on: bool) -> str:
    name = facts["name"]
    label = name + (f" ({facts['target']})" if facts.get("target") else "")
    if facts.get("status") and facts["status"] != "active":
        label += f" [{facts['status']}]"
    parts: list[str] = []
    if facts.get("reads"):
        if reach_on and facts.get("in_scope") in (None, True):
            parts.append("you read it with " + ", ".join(facts["reads"]))
        elif reach_on:
            parts.append(f"outside what {member} scoped you to")
        # Darkened / scoped-to-nothing: the edge sentence already said it;
        # a per-row repeat would be the model reading the same fact twice.
    if facts.get("agent_writes"):
        parts.append(
            "you can post with "
            + ", ".join(
                f"{w['tool']} ({'by PROPOSAL — queued for ' + member if w['mode'] == 'propose' else 'runs now'})"
                for w in facts["agent_writes"]
            )
        )
    elif facts.get("member_doors"):
        d = facts["member_doors"][0]
        parts.append(
            f"you cannot {d['verb']} there — {member} can, from the {d['pane']} pane ({d['door']})"
        )
    else:
        parts.append(f"nothing writes to {name}")
    return f"{label}: " + "; ".join(parts)


def frame_paragraph(
    status: list[dict],
    member: str,
    *,
    reach_on: bool,
    scoped_platforms: Optional[tuple] = None,
) -> str:
    """The AGENT face — the lane frame's reach section, generated.

    ADR-535 D3's invariant for all four reach states: name the inventory
    tool, state the turn's own edge truthfully, never deny a binding it can
    see. Then one line per connection from the same facts the member reads.
    The three hand-written branches this replaces were the fourth face.
    """
    from services.connectors import platform_display_name

    inventory = (
        f"list_integrations tells you which platforms {member} has CONNECTED and "
        "whether each is active — the same facts as below, at any time. Call it "
        "instead of guessing, and never tell them a connector is absent without "
        "looking. "
    )
    scoped_to_nothing = scoped_platforms is not None and not tuple(scoped_platforms)
    if not reach_on and scoped_to_nothing:
        edge = (
            f"You have no platform reach in this workspace: {member} scoped you to "
            "no connections. You may name what they connected; you cannot read "
            "through any of it. If they want that content here, say so plainly: "
            "they can widen your connections on your agent page, paste it, or drop "
            "the files into the commons."
        )
    elif not reach_on:
        edge = (
            "Seeing a connection is not having it: you can name what they bound, "
            "and you CANNOT read through it — there is no tool here that opens a "
            "Notion page or a Slack channel. If they want that content, say so "
            "plainly and offer what you can do — they can paste it, or export and "
            "drop the files into the commons, where you read them normally."
        )
    elif scoped_platforms is None:
        edge = (
            f"The platform_* tools read through {member}'s OWN connections — theirs "
            "only, granted by their authorization on each platform, read-only. What "
            "you fetch lives in this conversation and dies with it; if it is worth "
            "keeping, save it to the commons with WriteFile so it is attributed and "
            "citable. A platform they have not connected answers honestly that it "
            "is not connected — offer Connect in Settings, or paste."
        )
    else:
        plats = ", ".join(platform_display_name(p) for p in scoped_platforms)
        edge = (
            f"YOU can read through {plats} — that is what {member} scoped you to, "
            "and the platform_* tools you hold are only for those. What you fetch "
            "lives in this conversation and dies with it; save what is worth keeping "
            "with WriteFile. A platform they have not connected answers honestly "
            "that it is not connected — offer Connect in Settings, or paste."
        )
    lines = [_row_line(f, member, reach_on=reach_on) for f in status or []]
    rows = (" Connected now — " + "; ".join(lines) + ".") if lines else ""
    doors = any(f.get("member_doors") for f in status or [])
    outbound = " You cannot send or publish anywhere yourself" + (
        " — where a door is named above, it is theirs; asked to send something out, say you cannot and point them to it."
        if doors
        else "."
    )
    return inventory + edge + rows + outbound
