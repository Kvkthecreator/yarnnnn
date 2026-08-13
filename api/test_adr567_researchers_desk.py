"""ADR-567 gate — the Researcher's desk (chat-first watched-folder management).

Run with:  cd api && python3 test_adr567_researchers_desk.py
(studio/check style — prints ✗ and exits 1 on failure.)

The load-bearing behavior is EXECUTED, not grepped: build_lane_conventions is
run for a radar-bound lane and a studio-bound lane against stubbed reads, and
the posture selection is asserted on the composed output — the exact seam
where a radar lane would silently receive Studio's authoring job (the D4
defect this ADR exists to prevent).
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
# Fake client — path-keyed workspace_files reads; everything else empty.
# ---------------------------------------------------------------------------


class FakeQuery:
    def __init__(self, table: str, files: dict):
        self.table_name = table
        self.files = files
        self.path = None

    def select(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def order(self, *a, **k): return self
    def like(self, *a, **k): return self
    def in_(self, *a, **k): return self

    def eq(self, key, val):
        if key == "path":
            self.path = val
        return self

    def execute(self):
        if self.table_name == "workspace_files" and self.path in self.files:
            return SimpleNamespace(data=[{"content": self.files[self.path]}])
        return SimpleNamespace(data=[])


class FakeClient:
    def __init__(self, files: dict):
        self.files = files

    def table(self, name):
        return FakeQuery(name, self.files)


ROOT = "/workspace/operation/the-acme-deal"
REPORT = f"{ROOT}/report.md"
GOOD_YAML = (
    'schedule: "0 21 * * *"\npaused: false\nsources:\n'
    "  - id: blog\n    url: https://example.com/feed\n"
)

# ---------------------------------------------------------------------------
# 1. build_desk_posture — the three states, executed
# ---------------------------------------------------------------------------
print("1. build_desk_posture states")
from services.radar import build_desk_posture

empty = build_desk_posture(FakeClient({}), "u1", REPORT)
check("names the folder root", ROOT in empty)
check("no declaration → the SETTING UP branch",
      "NO DECLARATION YET" in empty and "SETTING UP" in empty)
check("teaches never-invent for sources", "NEVER invent source URLs" in empty)
check("teaches read-back after writing machine config (D6)",
      "READ IT BACK" in empty)
check("teaches the three files",
      all(s in empty for s in ("CRITERION.md", "_radar.yaml", "report.md")))

configured = build_desk_posture(
    FakeClient({
        f"{ROOT}/_radar.yaml": GOOD_YAML,
        f"{ROOT}/CRITERION.md": "Track the acme deal's competitors.",
        REPORT: "# Acme deal — current picture\n\nbody\n",
    }),
    "u1", REPORT,
)
check("parsed declaration echoed into the state block",
      "parses OK" in configured and "https://example.com/feed" in configured)
check("criterion echoed", "Track the acme deal's competitors." in configured)
check("report head summarized", "Acme deal — current picture" in configured)

broken = build_desk_posture(
    FakeClient({f"{ROOT}/_radar.yaml": "schedule: [unclosed\n  nonsense"}),
    "u1", REPORT,
)
check("unparseable declaration → the loud repair line (D6)",
      "DOES NOT PARSE" in broken)

# ---------------------------------------------------------------------------
# 2. The posture SELECTION — build_lane_conventions executed both ways
# ---------------------------------------------------------------------------
print("2. build_lane_conventions selects the job by binding app (D4)")
from services.lane_runner import LANE_MODELS, build_lane_conventions

model = next(iter(LANE_MODELS))
files = {
    f"{ROOT}/_radar.yaml": GOOD_YAML,
    f"{ROOT}/CRITERION.md": "Track competitors.",
}

desk = build_lane_conventions(
    FakeClient(files), "u1", model=model, artifact_path=REPORT, app="radar",
)
check("radar-bound lane gets the DESK posture",
      "THE RESEARCHER'S DESK" in desk)
check("radar-bound lane does NOT get the studio authoring posture",
      "data-ref" not in desk)

studio = build_lane_conventions(
    FakeClient({}), "u1", model=model,
    artifact_path="/workspace/operation/deck/presentation.html",
)
check("app-less bound lane still gets the studio posture (byte-compatible)",
      "THE RESEARCHER'S DESK" not in studio)
check("studio posture actually present for the app-less bound lane",
      "artifact" in studio.lower())

unbound = build_lane_conventions(FakeClient({}), "u1", model=model)
check("unbound lane gets neither job overlay",
      "THE RESEARCHER'S DESK" not in unbound and "data-ref" not in unbound)

# ---------------------------------------------------------------------------
# 3. The wiring — lane_meta persists the app; the dispatch threads it
#    (source-anchored, each with a real falsifier: remove the line, go red)
# ---------------------------------------------------------------------------
print("3. wiring (persist + thread)")
import pathlib

lanes_src = pathlib.Path("routes/lanes.py").read_text()
check("create_lane persists the binding app into lane_meta",
      'lane_meta["app"] = app_slug' in lanes_src)
check("the turn dispatch threads lane_meta.app to the runner",
      'app=lane_meta.get("app")' in lanes_src)
check("_lane_row_to_dict exposes the binding app",
      '"app": lane_meta.get("app")' in lanes_src)

import inspect

from services.lane_runner import run_lane_turn, run_lane_turn_stream
check("run_lane_turn accepts app",
      "app" in inspect.signature(run_lane_turn).parameters)
check("run_lane_turn_stream accepts app",
      "app" in inspect.signature(run_lane_turn_stream).parameters)

# ---------------------------------------------------------------------------
print()
if FAILURES:
    print(f"✗ {len(FAILURES)} check(s) failed: {FAILURES}")
    sys.exit(1)
print("✓ all ADR-567 researcher's-desk checks passed")
