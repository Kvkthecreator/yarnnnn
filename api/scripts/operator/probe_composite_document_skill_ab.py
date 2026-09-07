"""`assembling-a-composite-document` — measured (Part R owed 1; Part S owed 1).

The skill shipped UNMEASURED at rank 1 (2026-09-07). Its posture-side half —
the provenance line — is now carried by `text_pane_posture` and measured 3/3
vs 0/2. What the SKILL still owns is the CRAFT half: *"keep the document's
own numbers to the few the argument actually uses — copying a whole table
into prose is how two versions of the truth start"* (step 4). A 3-row fixture
cannot exercise that; this one is 24 rows, of which the ask needs three.

ARM A — the live frame (the skill's index line present, body reachable).
ARM B — the same frame with the skill withheld from the kernel index
        (`services.skills._kernel_cache` minus the slug, in-process). The
        mirrored body still exists under `system/skills/` in the workspace,
        exactly as in every earlier arm comparison (Parts P/Q/R) — the
        treatment is DISCOVERY, and ListFiles reach is the known 58% floor.

The ask NAMES THE SUBJECT — a report where the numbers matter — because an
index line is reached when the ask says what the skill is for (Part Q, 58%
otherwise), and "write the Q3 review" did not.

Pre-registered measure, ONE per arm:
    rows_copied_fraction — of the CSV's 24 monthly rows, the fraction whose
                           monthly_active figure appears in the document.
                           The argument needs Q3 (3 rows); the skill says
                           carry those, not the table.
Direction: ARM A < ARM B. At n=3/arm the exact permutation floor with perfect
separation is p = 1/C(6,3) = 0.05.

Exploratory (printed, never evidence): read the skill (ReadFile on its
path), provenance line present, tables in the document, rounds.

Run:  cd api && python3 scripts/operator/probe_composite_document_skill_ab.py [trials]
      … --purge   (after reading the receipts)
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

os.environ.setdefault("MODEL_ROUTER_ENABLED", "1")
os.environ.setdefault("LANES_ENABLED", "1")

import services.skills as skills_mod  # noqa: E402
from services.agents_registry import AGENTS  # noqa: E402
from services.authored_substrate import write_revision  # noqa: E402
from services.lane_runner import run_lane_turn  # noqa: E402
from services.supabase import AuthenticatedClient, get_service_client  # noqa: E402

WORKSPACE_ID = "d5b9029b-bd4e-4757-9fcb-e2b139fd4913"
PROBE_ROOT = "operation/_probe-composite-skill"
SLUG = "assembling-a-composite-document"

NOTES = """# Q3 2026 platform notes

Platform team standup notes for the quarter.

- July: migration to the new ingest pipeline finished mid-month; p95 latency
  dropped after it landed.
- August: two incidents, both in the scheduler; the post-mortem is in the wiki.
- September: onboarding flow rewritten; the support queue halved by week 3.
- Headcount flat at 6 all quarter. One contractor rolled off in August.
- Ask from leadership: a one-page review of Q3 for the all-hands. The monthly
  active numbers matter — put the quarter in context, don't just list months.
"""

# 24 months. The QUARTER under review is the last three rows; the rest is
# context a good review might compare against (one or two figures), and a bad
# one copies wholesale.
_ROWS = [
    ("2024-10", 610, 1, 910), ("2024-11", 640, 0, 905), ("2024-12", 655, 2, 930),
    ("2025-01", 700, 0, 880), ("2025-02", 740, 1, 870), ("2025-03", 790, 0, 865),
    ("2025-04", 830, 3, 890), ("2025-05", 880, 0, 850), ("2025-06", 920, 1, 840),
    ("2025-07", 980, 0, 835), ("2025-08", 1020, 2, 845), ("2025-09", 1090, 0, 820),
    ("2025-10", 1150, 1, 810), ("2025-11", 1210, 0, 800), ("2025-12", 1240, 1, 815),
    ("2026-01", 1320, 0, 790), ("2026-02", 1390, 2, 780), ("2026-03", 1460, 0, 770),
    ("2026-04", 1540, 1, 760), ("2026-05", 1630, 0, 745), ("2026-06", 1720, 1, 740),
    ("2026-07", 1850, 0, 505), ("2026-08", 2310, 2, 520), ("2026-09", 3040, 0, 498),
]
CSV = "month,monthly_active,incidents,p95_ms\n" + "\n".join(f"{m},{a},{i},{p}" for m, a, i, p in _ROWS) + "\n"

ASK = (
    "Write the Q3 platform review into the bound document — a one-page report "
    "for the all-hands where the numbers matter as much as the words."
)

PROVENANCE_RE = re.compile(r"_From `[^`]*metrics\.csv` · snapshot \d{4}-\d{2}-\d{2}")


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


def _figure_present(doc: str, n: int) -> bool:
    return f"{n:,}" in doc or re.search(rf"(?<![\d,]){n}(?![\d,])", doc) is not None


def _score(doc: str) -> dict:
    copied = [m for m, a, _i, _p in _ROWS if _figure_present(doc, a)]
    return {
        "rows_copied": len(copied),
        "rows_copied_fraction": round(len(copied) / len(_ROWS), 3),
        "q3_present": all(_figure_present(doc, a) for _m, a, _i, _p in _ROWS[-3:]),
        "provenance_line": bool(PROVENANCE_RE.search(doc)),
        "tables": doc.count("| --- ") + doc.count("|---"),
        "bytes": len(doc),
    }


def _withhold(slug: str):
    """Remove one kernel skill from the in-process index. Returns a restorer."""
    full = skills_mod._load_kernel()
    trimmed = {k: v for k, v in full.items() if k != slug}
    skills_mod._kernel_cache = trimmed
    def restore():
        skills_mod._kernel_cache = full
    return restore


async def _trial(auth: AuthenticatedClient, folder: str, model: str, arm: str) -> dict:
    for leaf, body in (("notes.md", NOTES), ("metrics.csv", CSV), ("review.md", "")):
        write_revision(
            auth.client, user_id=auth.user_id, path=f"/workspace/{folder}/{leaf}",
            content=body, authored_by="operator", author_identity_uuid=auth.user_id,
            message=f"probe fixture {leaf}", lifecycle="active",
        )
    restore = _withhold(SLUG) if arm == "B" else (lambda: None)
    try:
        res = await run_lane_turn(
            auth, model=model, history=[], user_message=ASK, member_label="Kevin",
            artifact_path=f"/workspace/{folder}/review.md", agent="editor", app="text",
        )
    finally:
        restore()
    head = _head(auth.client, auth.user_id, f"{folder}/review.md")
    tools = res.get("tools_called", [])
    return {
        "arm": arm, "folder": folder,
        "success": res.get("success"), "rounds": res.get("rounds"),
        "read_skill": any(SLUG in str(t) for t in tools),
        "tools": [t.get("name") if isinstance(t, dict) else str(t) for t in tools],
        **_score(head),
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


def _perm_p(a: list[float], b: list[float]) -> float:
    """Exact one-sided permutation p for mean(A) < mean(B)."""
    from itertools import combinations
    pool = a + b
    n = len(a)
    observed = sum(a) / n - sum(b) / len(b)
    count = total = 0
    for idx in combinations(range(len(pool)), n):
        ga = [pool[i] for i in idx]
        gb = [pool[i] for i in range(len(pool)) if i not in idx]
        total += 1
        if sum(ga) / n - sum(gb) / len(gb) <= observed + 1e-12:
            count += 1
    return count / total


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
    print(f"model={model} · trials/arm={trials} · stamp={stamp} · measure=rows_copied_fraction (A<B)")
    results: dict[str, list[dict]] = {"A": [], "B": []}
    # Interleave arms so drift in the engine hits both alike.
    for i in range(1, trials + 1):
        for arm in ("A", "B"):
            r = await _trial(auth, f"{PROBE_ROOT}/{stamp}-{arm}{i}", model, arm)
            results[arm].append(r)
            print(f"  {arm}{i}  rows_copied={r['rows_copied']:2d}/24 ({r['rows_copied_fraction']})  "
                  f"q3={r['q3_present']}  provenance={r['provenance_line']}  tables={r['tables']}  "
                  f"read_skill={r['read_skill']}  rounds={r['rounds']}"
                  + (f"  ERROR={r['error']}" if r["error"] else ""))
    a = [r["rows_copied_fraction"] for r in results["A"]]
    b = [r["rows_copied_fraction"] for r in results["B"]]
    print(f"\nARM A (skill in index)  rows_copied_fraction: {a}  mean {sum(a)/len(a):.3f}")
    print(f"ARM B (withheld)        rows_copied_fraction: {b}  mean {sum(b)/len(b):.3f}")
    print(f"exact permutation p (A<B): {_perm_p(a, b):.3f}   (floor at n={trials}/arm: {1/__import__('math').comb(2*trials, trials):.3f})")
    print(f"exploratory: read_skill A={sum(r['read_skill'] for r in results['A'])}/{trials} B={sum(r['read_skill'] for r in results['B'])}/{trials}"
          f" · provenance A={sum(r['provenance_line'] for r in results['A'])}/{trials} B={sum(r['provenance_line'] for r in results['B'])}/{trials}")
    print(f"\nreceipts under {PROBE_ROOT}/{stamp}-*/review.md — read them, then --purge")


if __name__ == "__main__":
    asyncio.run(main())
