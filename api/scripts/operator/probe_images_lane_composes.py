"""Can the LANE compose a stage? — the question that decides ADR-468's compose door.

`POST /api/images/compose` is fully built (access-checked, draw-gated,
type-refusing, N+1 attributed revisions) and has ZERO client callers. Its own
module says the work belongs to an agent:

    `plan_layers` is JUDGMENT: the resident (Designer) reads the brief and
    decides what objects a good ad has. That is a real design act and belongs
    to an agent, not to a rule table.   — services/apps/images/decompose.py

Designer already sits in the bound lane of an open stage, already holds the
`composing-an-image` skill (ADR-630), and already writes through the ordinary
member write door. So the endpoint is a SECOND implementation of an authoring
act the lane already owns — unless the lane cannot actually do it.

That is an empirical question, not a design one. This probe answers it:
create a blank stage exactly as the create door does, ask Designer to compose
it from a brief, and MEASURE THE ARTIFACT — never the transcript. A lane that
says "I composed it" and writes nothing is the failure mode that matters.

Run:  python3 api/scripts/operator/probe_images_lane_composes.py
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path

API = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(API))

for _line in (API / ".env").read_text().splitlines():
    if _line.strip() and not _line.strip().startswith("#") and "=" in _line:
        _k, _v = _line.split("=", 1)
        os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

os.environ.setdefault("MODEL_ROUTER_ENABLED", "1")
os.environ.setdefault("LANES_ENABLED", "1")

import services.apps.images  # noqa: E402,F401 — registration side-effect
from services.apps.images import STAGE_SLUG, resolve_dimensions, stage_root_attrs  # noqa: E402
from services.agents_registry import AGENTS  # noqa: E402
from services.authored_substrate import write_revision  # noqa: E402
from services.authoring import build_skeleton, set_artifact_title  # noqa: E402
from services.lane_runner import run_lane_turn  # noqa: E402
from services.supabase import AuthenticatedClient, get_service_client  # noqa: E402

WORKSPACE_ID = "d5b9029b-bd4e-4757-9fcb-e2b139fd4913"
PROBE_ROOT = "operation/_probe-images-lane"
STAGE_LEAF = f"{PROBE_ROOT}/launch-ad/{STAGE_SLUG}.html"

BRIEF = (
    "Compose a launch ad for YARNNN — the workspace where every file change is "
    "signed by whoever made it, human or AI. Headline: 'Every change, signed.' "
    "Supporting line: 'The workspace with a memory.' Dark ground, one dominant "
    "type statement, the wordmark small in a corner. Make it read at thumbnail size."
)


def _blank_stage(title: str) -> str:
    """A stage born exactly as `POST /studio/artifacts` bears one.

    Same skeleton, same title pass, same dimension stamping — so what the lane
    is handed is what a member's Create hands it. A hand-rolled fixture here
    would be testing a stage no member can make.
    """
    content = set_artifact_title(build_skeleton(STAGE_SLUG, title), title, set_h1=False)
    w, h = resolve_dimensions(preset_slug="square")
    return content.replace(
        f'<html data-template="{STAGE_SLUG}">',
        f'<html data-template="{STAGE_SLUG}" {stage_root_attrs(w, h)}>',
        1,
    )


def _head(client, user_id: str, path: str) -> str:
    rows = (
        client.table("workspace_files").select("content")
        .eq("user_id", user_id).eq("path", f"/workspace/{path}")
        .limit(1).execute().data or []
    )
    return (rows[0].get("content") or "") if rows else ""


def _score(html: str) -> dict:
    """What the SKILL asks for, counted in the artifact's own bytes.

    Every measure is a property of the composition the member would see, not a
    claim the lane made about it. `data-z` on every layer is the skill's
    load-bearing rule (an unstamped layer has no authored value for the layer
    rail to move), so it is measured as a RATIO, not a presence.

    ⚠️ BODY ONLY. The kernel CSS baked into every skeleton mentions
    `data-block` 89 times in its selectors, so scoring the whole document
    reported 91 "blocks" for an empty stage — a scorer reading the wrong
    region, which would have made any composition look like a no-op.
    """
    body = html.split("</head>")[-1]
    html = body
    blocks = re.findall(r'data-block="[a-z-]+"', html)
    placed = re.findall(r"data-x=", html)
    zed = re.findall(r"data-z=", html)
    return {
        "bytes": len(html),
        "blocks": len(blocks),
        "placed": len(placed),
        "z_stamped": len(zed),
        "all_placed": bool(blocks) and len(placed) >= len(blocks),
        "all_zed": bool(blocks) and len(zed) >= len(blocks),
        "dark_ground": 'data-ground="dark"' in html,
        "figures": html.count('data-block="figure"'),
        "still_scaffold": "The visual statement." in html,
    }


async def main() -> None:
    service = get_service_client()
    owner = (
        service.table("workspaces").select("owner_id")
        .eq("id", WORKSPACE_ID).limit(1).execute().data or []
    )
    if not owner:
        print(f"FAIL: workspace {WORKSPACE_ID} not found")
        sys.exit(1)
    user_id = owner[0]["owner_id"]
    auth = AuthenticatedClient(client=service, user_id=user_id, workspace_id=WORKSPACE_ID)

    # Clean first — a stale stage from a prior run would let the lane "pass"
    # on someone else's composition.
    stale = (
        service.table("workspace_files").select("id")
        .eq("user_id", user_id).like("path", f"/workspace/{PROBE_ROOT}/%")
        .execute().data or []
    )
    for row in stale:
        service.table("workspace_files").delete().eq("id", row["id"]).execute()
    print(f"purged {len(stale)} stale probe row(s)")

    write_revision(
        service, user_id=user_id, path=f"/workspace/{STAGE_LEAF}",
        content=_blank_stage("Launch ad"), authored_by="operator",
        author_identity_uuid=user_id, message="probe: blank stage", lifecycle="active",
    )
    before = _score(_head(service, user_id, STAGE_LEAF))
    print(f"blank stage: {before['bytes']}B, {before['blocks']} blocks, scaffold={before['still_scaffold']}")

    # Designer's OWN declared engine — the app's resident answers this
    # server-side in production (ADR-562), so a hardcoded model here would be
    # probing a lane no member gets.
    model = AGENTS["designer"]["model"]
    print(f"model={model} (designer's declared engine)")

    res = await run_lane_turn(
        auth, model=model, history=[], user_message=BRIEF, member_label="Kevin",
        artifact_path=f"/workspace/{STAGE_LEAF}", agent="designer", app="images",
    )

    after = _score(_head(service, user_id, STAGE_LEAF))
    tools = [t.get("name") if isinstance(t, dict) else str(t) for t in res.get("tools_called", [])]

    print()
    print(f"success={res.get('success')} rounds={res.get('rounds')} tools={tools}")
    print(f"skill read: {any('composing-an-image' in str(t) for t in res.get('tools_called', []))}")
    print()
    print("ARTIFACT (what the member would see):")
    for k in ("bytes", "blocks", "placed", "z_stamped", "all_placed", "all_zed",
              "dark_ground", "figures", "still_scaffold"):
        print(f"  {k:16} {before[k]!r:>8}  ->  {after[k]!r}")

    wrote = after["bytes"] != before["bytes"]
    composed = wrote and after["blocks"] > before["blocks"] and not after["still_scaffold"]
    print()
    print(f"VERDICT: wrote={wrote} composed={composed} "
          f"honours_skill={composed and after['all_placed'] and after['all_zed']}")
    if not res.get("success"):
        print(f"lane error: {res.get('message')}")


if __name__ == "__main__":
    asyncio.run(main())
