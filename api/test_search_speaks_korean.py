#!/usr/bin/env python3
"""Gate — search finds a Korean noun inside an inflected word (migration 260).

    python3 test_search_speaks_korean.py

## What this defends

`search_workspace` matched with `to_tsvector('english', …)`. The English
stemmer whitespace-splits Korean and stems nothing, and Korean is
agglutinative — a particle attaches directly to the noun. So a noun was found
only when it happened to appear BARE, which in real Korean prose is the
minority case.

Measured on production 2026-09-21, against a Korean file a member had already
written (`operation/한국어-커넥터-테스트.md`, authored 2026-09-18) whose own
item 3 asks *"can I find this file again with a Korean query"*:

    커넥터 → 2   한국어 → 1   테스트 → 1      (bare nouns: found)
    본문   → 0   삭제   → 0                   (본문이 / 삭제하거나: LOST)
    workspace (English control) → 20

Search did not error. It returned fewer rows, and that is reported as "search
is bad", never as "search is broken".

## The shape, and why each check exists

260 adds a THIRD tier below 246's strict/loose ladder: a pgroonga substring
match, running only when strict AND loose both found nothing. Ordering it last
is what makes it safe — an English query's result set is byte-identical to
what 246 returned, so the tier is pure addition.

- **The Korean arms** drive the LIVE RPC over the exact queries that failed.
  A unit test over a stubbed row set would pass against a broken index; only
  the real function on real rows answers the smoke-test file's question.
- **The English control** must be unchanged AND must never show a `korean`
  row. A substring tier that fired on English would dilute precise results.
- **The filter arms** re-assert workspace scope, the powerbox deny-all, the
  path prefix and the trash exclusion THROUGH the new tier. A matching
  strategy must never reach a file the caller cannot read, and a new CTE is
  exactly where such a filter gets forgotten.
- **The grading arm** is pure logic and needs no database: a `korean` row is
  a substring LEAD, so it must cap confidence at WEAK. Graded as full
  `bm25` it would report a substring hit as precise — the inverse of the
  2026-08-22 defect this ladder exists to prevent, and the same class of lie.

⚠️ The DB arms need `SUPABASE_DB_URL` (or `_RO`). Without it they SKIP loudly
rather than passing, because a gate that quietly passes when it could not
connect is worse than one that fails.
"""

import os
import re
import subprocess
import sys
from typing import Optional
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

_passed = 0
_failed = 0
_skipped = 0

# The workspace that holds the Korean files (measured 2026-09-21: 33 of the 34
# Hangul-bearing rows live here). A different workspace returns 0 for every
# arm and the gate would read green over nothing — the "a scan over a world
# with no data cannot fail" shape.
WS = "d5b9029b-bd4e-4757-9fcb-e2b139fd4913"


def check(label: str, ok: bool, detail: str = "") -> bool:
    global _passed, _failed
    if ok:
        _passed += 1
        print(f"  ok   {label}")
    else:
        _failed += 1
        print(f"  FAIL {label}" + (f" — {detail}" if detail else ""))
    return ok


def skip(label: str, why: str) -> None:
    global _skipped
    _skipped += 1
    print(f"  SKIP {label} — {why}")


def db_url() -> Optional[str]:
    for var in ("SUPABASE_DB_URL_RO", "SUPABASE_DB_URL"):
        if os.environ.get(var):
            return os.environ[var]
    secrets = ROOT / ".secrets.local"
    if secrets.exists():
        for line in secrets.read_text().splitlines():
            m = re.match(r'\s*export\s+(SUPABASE_DB_URL(?:_RO)?)\s*=\s*"?([^"\n]+)"?', line)
            if m:
                return m.group(2)
    return None


def q(url: str, sql: str) -> str:
    # `SET` is passed with its own -c so it cannot echo into the -At output;
    # chaining it inside one -c prints "SET" as the first line and every
    # int() downstream reads it instead of the answer.
    out = subprocess.run(
        ["psql", url, "-At", "-q",
         "-c", "SET client_min_messages=ERROR;",
         "-c", sql],
        capture_output=True, text=True, timeout=180,
    )
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip()[:300])
    return out.stdout.strip()


print("Search speaks Korean — migration 260")
print()

URL = db_url()

print("The Korean tier, driven on the live RPC")
if not URL:
    skip("every Korean arm", "no SUPABASE_DB_URL / _RO — cannot reach the database")
else:
    try:
        # The two queries that returned ZERO before 260. 본문 appears only as
        # 본문이 (particle); 삭제 only as 삭제하거나 (conjugated).
        for term in ("본문", "삭제"):
            n = q(URL, f"SELECT count(*) FROM search_workspace('{WS}'::uuid,'{term}',NULL,20,NULL);")
            check(f"'{term}' finds the file it is written in (was 0)", int(n) >= 1, f"{n} hits")

        modes = q(URL, f"SELECT DISTINCT match_mode FROM search_workspace('{WS}'::uuid,'본문',NULL,20,NULL);")
        check("it is labelled 'korean', so the caller can grade it", modes == "korean", modes)

        # Bare nouns must still come from the ENGLISH tier — the Korean tier
        # runs only on a double miss, so these are proof of the ordering.
        for term in ("커넥터", "한국어"):
            m = q(URL, f"SELECT DISTINCT match_mode FROM search_workspace('{WS}'::uuid,'{term}',NULL,20,NULL);")
            check(f"a bare noun '{term}' still answers from the English tier", m == "strict", m)

        print()
        print("English is untouched — the tier is pure addition")
        for term in ("workspace", "reports", "agent"):
            m = q(URL, f"SELECT DISTINCT match_mode FROM search_workspace('{WS}'::uuid,'{term}',NULL,50,NULL);")
            check(f"'{term}' returns no substring rows", "korean" not in m, m)
        n = q(URL, f"SELECT count(*) FROM search_workspace('{WS}'::uuid,'downturn companies deck',NULL,50,NULL);")
        check("246's own receipt still answers (the 2026-08-22 false miss)", int(n) >= 1, f"{n} hits")

        print()
        print("Every filter applies THROUGH the new tier")
        n = q(URL, "SELECT count(*) FROM search_workspace('bf5b25a9-477f-462e-b7f3-65812f489411'::uuid,'본문',NULL,20,NULL);")
        check("workspace scope holds", n == "0", f"{n} rows leaked across workspaces")
        n = q(URL, f"SELECT count(*) FROM search_workspace('{WS}'::uuid,'본문',NULL,20,ARRAY[]::text[]);")
        check("an empty powerbox array is deny-all", n == "0", f"{n} rows past deny-all")
        n = q(URL, f"SELECT count(*) FROM search_workspace('{WS}'::uuid,'본문','/workspace/nonexistent',20,NULL);")
        check("a non-matching path prefix excludes", n == "0", f"{n} rows past the prefix")
        n = q(URL, f"""SELECT count(*) FROM search_workspace('{WS}'::uuid,'배출증',NULL,50,NULL) r
                       JOIN workspace_files f ON f.id = r.id WHERE f.lifecycle = 'archived';""")
        check("archived files stay unsearchable (218 holds)", n == "0", f"{n} archived rows returned")

        print()
        print("The index exists — without it the tier is a sequential scan")
        n = q(URL, "SELECT count(*) FROM pg_class WHERE relname = 'workspace_files_content_pgroonga';")
        check("the pgroonga content index is live", n == "1")
    except Exception as exc:  # noqa: BLE001
        check("the database arms ran", False, str(exc))

# --- Grading: pure logic, no database ---------------------------------------
print()
print("A substring hit is a LEAD, and must grade WEAK")
src = (Path(__file__).resolve().parent / "services/primitives/workspace.py").read_text()
check(
    "the grader treats 'korean' like 'loose'",
    '"loose", "korean"' in src or "'loose', 'korean'" in src,
    "a korean row graded as full bm25 reports a substring hit as precise",
)

weak_modes = {"loose", "korean"}
def grade(rows):
    return "bm25_loose" if all(r["match_mode"] in weak_modes for r in rows) else "bm25"

for name, rows, want in (
    ("all strict", [{"match_mode": "strict"}], "bm25"),
    ("all loose", [{"match_mode": "loose"}], "bm25_loose"),
    ("all korean", [{"match_mode": "korean"}], "bm25_loose"),
    ("korean + loose", [{"match_mode": "korean"}, {"match_mode": "loose"}], "bm25_loose"),
    # A precise hit alongside a substring one is still a precise ANSWER.
    ("strict + korean", [{"match_mode": "strict"}, {"match_mode": "korean"}], "bm25"),
):
    check(f"{name} grades {want}", grade(rows) == want, grade(rows))

print()
print(f"  {_passed} passed, {_failed} failed" + (f", {_skipped} skipped" if _skipped else ""))
if _failed:
    print()
    print("✗ Korean search is not answering")
    sys.exit(1)
if _skipped:
    print()
    print("⚠ some arms could not reach the database — not a pass")
    sys.exit(1)
print()
print("✓ a Korean noun is found inside the word it lives in")
