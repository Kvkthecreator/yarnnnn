"""DeclareWork — the conversation's door to standing work (ADR-667 D2).

A member tells their agent what keeps happening; the agent sets it up with
this tool. It calls `services.standing_door` — the SAME declare/revise the
Supervisor's routes call — so a conversation and a click produce one
declaration shape, refused by the same names.

⭐ THE STAMP. `sites` present makes it browser work in the ACTING member's
browser: the member is `auth.user_id`, the member whose turn this is. The
tool takes no member argument, so no agent can name one.

`WriteFile`/`EditFile` refuse `_standing.yaml` and name this tool: one way to
declare. Retiring stays a delete (`DeleteFile` on `_standing.yaml`).
"""

from __future__ import annotations

from typing import Any

DECLARE_WORK_TOOL = {
    "name": "DeclareWork",
    "description": """Set up standing work — a file kept current on a schedule — or change one that exists. Writes CONTRACT.md and _standing.yaml in `folder` through the one door; `_standing.yaml` is never written by hand.

New work needs folder, target, schedule and contract. Work that exists in `folder` is revised: pass only what changes (paused, schedule, sources, shape, target, sites); a new `contract` rewrites CONTRACT.md.

`sites` makes it browser work in the member's own browser, on those sites only: it runs when they start it, and when it comes due it waits for them. Name the sites the work actually needs — for work you just did in their browser, the sites you used. Without `sites` it runs on its own from its sources.

Sources: [{id, url}] · [{id, connector, selector}] · [{id, path}] (a workspace file, or a folder ending in /). A csv, json or txt target takes exactly one file source; prose takes up to twelve. Never invent a URL or a path.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "folder": {"type": "string", "description": "The work's folder, workspace-relative (e.g. 'shop/prices')."},
            "target": {"type": "string", "description": "The file kept current, one name in that folder: md, csv, json or txt."},
            "schedule": {"type": "string", "description": "Cron in the workspace's timezone, e.g. '0 9 * * 1'."},
            "contract": {"type": "string", "description": "CONTRACT.md: what the file must stay true to and, for browser work, how to get there."},
            "sources": {"type": "array", "items": {"type": "object"}},
            "shape": {"type": "object", "description": "csv: {columns: [...]}; json: {keys: [...]}."},
            "sites": {"type": "array", "items": {"type": "string"}, "description": "Browser work: the sites it may open, e.g. ['example.com']."},
            "paused": {"type": "boolean"},
        },
        "required": ["folder"],
    },
}


async def handle_declare_work(auth: Any, input: dict) -> dict:
    from services import standing_door as door
    from services.standing_door import DoorRefusal

    authored_by = getattr(auth, "caller_identity", None) or "system:unknown"
    folder = str(input.get("folder") or "")
    sites = input.get("sites")
    sites = [str(x) for x in sites] if isinstance(sites, list) else None
    contract = input.get("contract")
    try:
        topic = door.validate_topic(folder)
        exists = door.read_declaration(auth.client, door.acting_owner(auth), topic) is not None
        if exists:
            decl = await door.revise(
                auth, topic,
                paused=input.get("paused"), schedule=input.get("schedule"),
                sources=input.get("sources"), shape=input.get("shape"),
                target=input.get("target"), browser_sites=sites,
                contract=contract if isinstance(contract, str) else None, authored_by=authored_by,
            )
        else:
            decl = await door.declare(
                auth, folder=topic, target=str(input.get("target") or ""),
                schedule=input.get("schedule") or "0 9 * * *", contract=str(contract or ""),
                sources=input.get("sources"), shape=input.get("shape"),
                browser_sites=sites, authored_by=authored_by,
            )
    except DoorRefusal as e:
        return {"success": False, "error": e.problem, "message": e.message}

    browser = decl.browser is not None
    return {
        "success": True,
        "revised": exists,
        # The card (LANE_ARTIFACT_VERBS): the instructions just written — the
        # kept file may not exist until the first run.
        "path": door.contract_path(topic),
        "target": decl.target_path,
        "declaration": door.decl_path(topic),
        "browser": browser,
        "message": (
            ("Revised" if exists else "Set up") + f" '{topic}'. "
            + ("It runs in the member's browser when they start it, and waits for them when it comes due."
               if browser else
               "It runs on its schedule; the first run comes within minutes of setting it up.")
        ),
    }
