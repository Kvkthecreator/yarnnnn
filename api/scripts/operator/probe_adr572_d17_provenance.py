"""ADR-572 D17/D18 in the LANE — does the Text posture's new bullet make a
bound Text lane write the provenance line when it lifts figures from a CSV?

The failure this measures (2026-09-07, `docs/analysis/composing-an-image-in-a-
bound-lane-2026-09-07.md`, postscript): two bound Text runs on a notes file +
a 3-row CSV, asked to "write the Q3 platform review into the bound document",
both retyped the CSV's figures into a markdown table and cited the source file
nowhere. That is the toolbar's own snapshot shape (ADR-572 D18) minus the
provenance line D18 makes it honest with. Those two runs are the CONTROL arm
(0/2 provenance lines, same fixture, same ask, posture without the bullet).

This drives the TREATED arm: the live posture (bullet present), the same
fixture, the same ask, n trials, each in its own run folder on the production
substrate (real `run_lane_turn`, real Editor engine, real substrate writes).

Pre-registered measure, ONE per arm:
    provenance_line_present — the bound document carries a line of the form
                              `_From `…q3.csv` · snapshot YYYY-MM-DD_`
Everything else printed is exploratory (figures retyped, tools called,
rounds) and is read as description, never as evidence.

At n=3 treated vs n=2 control the exact permutation floor with perfect
separation (3/3 vs 0/2) is p = 1/C(5,3) = 0.100. A single miss on the treated
side does not clear it — report it as such.

Run:  cd api && python3 scripts/operator/probe_adr572_d17_provenance.py [trials]
Purge (after reading the receipts): … --purge
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

API = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(API))

for _line in (API / ".env").read_text().splitlines():
    if _line.strip() and not _line.strip().startswith("#") and "=" in _line:
        _k, _v = _line.split("=", 1)
        os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

# The router flags live on Render, not in .env: the transport flag is
# infra, the lanes flag is product (ADR-557 — two flags, two questions). A
# probe that drives a real lane turn from a laptop needs both, in-process.
os.environ.setdefault("MODEL_ROUTER_ENABLED", "1")
os.environ.setdefault("LANES_ENABLED", "1")

from services.agents_registry import AGENTS  # noqa: E402
from services.authored_substrate import write_revision  # noqa: E402
from services.lane_runner import run_lane_turn  # noqa: E402
from services.supabase import AuthenticatedClient, get_service_client  # noqa: E402

#: The production workspace (`whoami` on the connector names it; the owner is
#: resolved from the row rather than pasted).
WORKSPACE_ID = "d5b9029b-bd4e-4757-9fcb-e2b139fd4913"
PROBE_ROOT = "operation/_probe-adr572-d17"

NOTES = """# Q3 platform notes

Platform team standup notes, Q3.

- July: migration to the new ingest pipeline finished mid-month; p95 latency
  dropped after it landed.
- August: two incidents, both in the scheduler; a post-mortem is in the wiki.
- September: onboarding flow rewritten; the support queue halved by week 3.
- Headcount flat at 6 all quarter. One contractor rolled off in August.
- Ask from leadership: a short review of the quarter for the all-hands, with
  the monthly active numbers in it.
"""

CSV = """month,monthly_active,incidents
July,1850,0
August,2310,2
September,3040,0
"""

ASK = "write the Q3 platform review into the bound document"

PROVENANCE_RE = re.compile(r"_From `[^`]*q3\.csv` · snapshot \d{4}-\d{2}-\d{2}")


def _owner_id(service) -> str:
    row = service.table("workspaces").select("owner_id").eq("id", WORKSPACE_ID).limit(1).execute().data
    if not row:
        raise SystemExit(f"workspace {WORKSPACE_ID} not found")
    return row[0]["owner_id"]


def _auth(service, user_id: str) -> AuthenticatedClient:
    return AuthenticatedClient(
        client=service, user_id=user_id, caller_identity="operator",
        workspace_id=WORKSPACE_ID, principal_id=user_id,
    )


def _head(service, user_id: str, path: str) -> str:
    row = (
        service.table("workspace_files").select("content")
        .eq("user_id", user_id).eq("path", f"/workspace/{path}").limit(1).execute().data
    )
    return (row[0]["content"] or "") if row else ""


async def _trial(auth: AuthenticatedClient, folder: str, model: str) -> dict:
    for leaf, body in (("notes.md", NOTES), ("q3.csv", CSV), ("review.md", "")):
        write_revision(
            auth.client, user_id=auth.user_id, path=f"/workspace/{folder}/{leaf}",
            content=body, authored_by="operator", author_identity_uuid=auth.user_id,
            message=f"probe fixture {leaf}", lifecycle="active",
        )
    bound = f"/workspace/{folder}/review.md"
    res = await run_lane_turn(
        auth, model=model, history=[], user_message=ASK, member_label="Kevin",
        artifact_path=bound, agent="editor", app="text",
    )
    head = _head(auth.client, auth.user_id, f"{folder}/review.md")
    return {
        "folder": folder,
        "success": res.get("success"),
        "rounds": res.get("rounds"),
        "tools": [t.get("name") if isinstance(t, dict) else str(t) for t in res.get("tools_called", [])],
        "read_skill": any("SKILL.md" in str(t) for t in res.get("tools_called", [])),
        "provenance_line_present": bool(PROVENANCE_RE.search(head)),
        "figures_present": [n for n in ("1,850", "1850", "2,310", "2310", "3,040", "3040") if n in head],
        "mentions_csv": "q3.csv" in head,
        "head_bytes": len(head),
        "error": res.get("message") if not res.get("success") else None,
    }


def _purge(service, user_id: str) -> int:
    rows = (
        service.table("workspace_files").select("id,path")
        .eq("user_id", user_id).like("path", f"/workspace/{PROBE_ROOT}/%").execute().data or []
    )
    for r in rows:
        service.table("workspace_files").delete().eq("id", r["id"]).execute()
    left = (
        service.table("workspace_files").select("id", count="exact")
        .eq("user_id", user_id).like("path", f"/workspace/{PROBE_ROOT}/%").execute().count
    )
    print(f"purged {len(rows)} rows; {left} remaining under {PROBE_ROOT}/")
    return left or 0


async def main() -> None:
    service = get_service_client()
    user_id = _owner_id(service)
    if "--purge" in sys.argv:
        _purge(service, user_id)
        return
    trials = next((int(a) for a in sys.argv[1:] if a.isdigit()), 3)
    model = AGENTS["editor"]["model"]
    auth = _auth(service, user_id)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    print(f"TREATED arm · model={model} · trials={trials} · stamp={stamp}")
    results = []
    for i in range(1, trials + 1):
        folder = f"{PROBE_ROOT}/{stamp}-{i}"
        r = await _trial(auth, folder, model)
        results.append(r)
        print(f"  t{i}  provenance_line={'YES' if r['provenance_line_present'] else 'no '}  "
              f"rounds={r['rounds']}  figures={r['figures_present']}  mentions_csv={r['mentions_csv']}  "
              f"read_skill={r['read_skill']}  tools={r['tools']}"
              + (f"  ERROR={r['error']}" if r["error"] else ""))
    hits = sum(1 for r in results if r["provenance_line_present"])
    print(f"\nprovenance_line_present: {hits}/{trials} treated  vs  0/2 control (2026-09-07 postscript)")
    if hits == trials and trials >= 3:
        print("perfect separation at n=3 vs n=2 → exact permutation p = 0.100 (the floor)")
    else:
        print("NOT perfectly separated — report as directional, not as clearing the floor")
    print(f"\nreceipts under {PROBE_ROOT}/{stamp}-*/review.md — read them, then --purge")


if __name__ == "__main__":
    asyncio.run(main())
