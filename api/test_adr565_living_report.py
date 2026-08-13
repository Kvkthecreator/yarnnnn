"""ADR-565 gate — the living report re-cut (with ADR-564's frame invariants).

Run with:  cd api && python3 test_adr565_living_report.py
(studio/check style — prints ✗ and exits 1 on failure.)

Covers what the amended ADR-486 harness does not: the write-confinement
assertion (ADR-564 D6), the any-depth topic validation + the nested-hub
refusal (ADR-565 D3), the criterion read order (file over legacy steer),
and the delta-headline lift for the revision message.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ✓ {name}")
    else:
        print(f"  ✗ {name} {detail}")
        FAILURES.append(name)


# ---------------------------------------------------------------------------
# 1. Write-confinement (ADR-564 D6 / ADR-565 D4) — asserted, falsifiable
# ---------------------------------------------------------------------------
print("1. write-confinement")
from services.radar import RadarHub, _assert_hub_write

hub = RadarHub(topic="competitor-x", slug="radar:competitor-x",
               declaration_path="/workspace/operation/competitor-x/_radar.yaml")

try:
    _assert_hub_write(hub, "/workspace/operation/competitor-x/report.md")
    check("in-subtree write passes", True)
except ValueError:
    check("in-subtree write passes", False)

for outside in (
    "/workspace/operation/other-topic/report.md",
    "/workspace/governance/_autonomy.yaml",
    "/workspace/operation/competitor-x-adjacent/report.md",  # prefix ≠ subtree
):
    try:
        _assert_hub_write(hub, outside)
        check(f"outside write REFUSED: {outside}", False)
    except ValueError:
        check(f"outside write REFUSED: {outside}", True)

# ---------------------------------------------------------------------------
# 2. Any-depth topics (ADR-565 D3) — route validation
# ---------------------------------------------------------------------------
print("2. topic validation (routes)")
from fastapi import HTTPException

from routes.radar import _validate_topic

check("single segment ok", _validate_topic("competitor-x") == "competitor-x")
check("nested path ok", _validate_topic("the-acme-deal/competitors") ==
      "the-acme-deal/competitors")
check("normalizes case + edge slashes", _validate_topic("/A-B/c/") == "a-b/c")
for bad in ("", "a//b", "Not A Slug!", "a/b/c/d/e", "../escape", "a/_radar"):
    try:
        _validate_topic(bad)
        check(f"rejects {bad!r}", False)
    except HTTPException as e:
        check(f"rejects {bad!r}", e.status_code == 422)

# ---------------------------------------------------------------------------
# 3. Nested-hub refusal at discovery (named-deferred nested criteria)
# ---------------------------------------------------------------------------
print("3. nested-hub refusal (discovery)")
from services.radar import discover_radar_hubs

DECL = 'schedule: "0 13 * * *"\nsources:\n  - id: s\n    url: https://x.com/f\n'


class NestedFakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def select(self, *a, **k): return self
    def like(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def execute(self): return SimpleNamespace(data=self.rows)


class NestedFakeClient:
    def __init__(self, rows):
        self.rows = rows

    def table(self, name):
        return NestedFakeQuery(self.rows)


rows = [
    {"user_id": "u1", "workspace_id": None,
     "path": "/workspace/operation/alpha/_radar.yaml", "content": DECL},
    {"user_id": "u1", "workspace_id": None,
     "path": "/workspace/operation/alpha/deeper/_radar.yaml", "content": DECL},
    {"user_id": "u1", "workspace_id": None,
     "path": "/workspace/operation/alpha-adjacent/_radar.yaml", "content": DECL},
]
hubs = discover_radar_hubs(NestedFakeClient(rows)).get("u1", [])
topics = sorted(h.topic for h in hubs)
check("outer hub + non-nested sibling kept, nested refused",
      topics == ["alpha", "alpha-adjacent"])
check("string-prefix sibling is NOT treated as nested",
      "alpha-adjacent" in topics)

# ---------------------------------------------------------------------------
# 4. Criterion read order — the file wins; legacy steer is only a fallback
# ---------------------------------------------------------------------------
print("4. criterion read order")
from services.radar import _read_criterion, parse_radar_yaml


class CritFakeQuery:
    def __init__(self, files):
        self.files = files
        self.path = None

    def select(self, *a, **k): return self
    def limit(self, *a, **k): return self

    def eq(self, key, val):
        if key == "path":
            self.path = val
        return self

    def execute(self):
        body = self.files.get(self.path)
        return SimpleNamespace(data=[{"content": body}] if body is not None else [])


class CritFakeClient:
    def __init__(self, files):
        self.files = files

    def table(self, name):
        return CritFakeQuery(self.files)


legacy_hub = parse_radar_yaml(
    'schedule: "0 13 * * *"\nprompt: legacy steer text\nsources:\n  - id: s\n    url: https://x.com/f\n',
    topic="t", declaration_path="/workspace/operation/t/_radar.yaml", user_id="u1",
)
check("CRITERION.md wins over the legacy steer",
      _read_criterion(CritFakeClient(
          {"/workspace/operation/t/CRITERION.md": "the real criterion"}),
          "u1", legacy_hub) == "the real criterion")
check("no file → legacy steer fallback (migration only)",
      _read_criterion(CritFakeClient({}), "u1", legacy_hub) == "legacy steer text")
no_steer_hub = parse_radar_yaml(
    'schedule: "0 13 * * *"\nsources:\n  - id: s\n    url: https://x.com/f\n',
    topic="t", declaration_path="/workspace/operation/t/_radar.yaml", user_id="u1",
)
check("no file, no steer → None (the conservative-bar branch)",
      _read_criterion(CritFakeClient({}), "u1", no_steer_hub) is None)

# ---------------------------------------------------------------------------
# 5. The delta headline — the revision message carries the sweep's delta
# ---------------------------------------------------------------------------
print("5. extract_delta_headline")
from services.radar import extract_delta_headline

REPORT = """# Competitor X — current picture

## Recent developments
- 2026-08-13: raised seat pricing 20% ([post](https://x.com/p))
- 2026-08-10: shipped a new tier

## Pricing
...
"""
check("lifts the first Recent-developments bullet",
      extract_delta_headline(REPORT) ==
      "2026-08-13: raised seat pricing 20% ([post](https://x.com/p))")
check("no recent-developments section → None",
      extract_delta_headline("# T\n\n## Pricing\n- a bullet\n") is None)
check("empty report → None", extract_delta_headline("") is None)

# ---------------------------------------------------------------------------
print()
if FAILURES:
    print(f"✗ {len(FAILURES)} check(s) failed: {FAILURES}")
    sys.exit(1)
print("✓ all ADR-565 living-report checks passed")
