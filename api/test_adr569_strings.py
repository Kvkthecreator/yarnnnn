"""ADR-569 gate — Strings: the maintained file, kept by Keeper.

Run with:  cd api && python3 test_adr569_strings.py
(studio/check style — prints ✗ and exits 1 on failure. Script-style: under
pytest this file reports a false PASS, like the ADR-474/476/478 gates.)

The load-bearing behaviors are EXECUTED, not grepped, and each check is
falsified by construction — remove the mechanism and the check goes red:

  1. THE DESIGNATION BOUNDARY (D1) — parse_string_yaml refuses targets
     outside the v1 scope loudly (problem set), across MORE THAN ONE format
     (falsifier 1's shape: csv AND md exercised).
  2. THE CONFINEMENT LAW (D1/D3) — _assert_string_write raises for every
     path that is not the designated leaf; the run's write site calls it.
  3. THE SHAPE REFUSAL (D3) — map_structured raises ShapeViolation on a
     violating fetch (missing column, missing key, unparseable), maps a
     conforming one, and the route's repair composer turns the ledger's
     refusal into the desk's repair state (cleared by a later success).
  4. POSTURE SELECTION (D6, the ADR-567 D4 mechanism) — build_lane_conventions
     executed three ways: app='strings' → KEEPER'S DESK; app='radar' →
     THE RESEARCHER'S DESK; app-less bound → studio. Extends test_adr567's
     pins, never breaks them.
  5. THE RESIDENT (ADR-562) — strings registers keeper; keeper resolves as a
     kernel character (a POSTURE over Produce — the closed three-operation
     base roster holds) on a priced engine.
  6. WIRING — the drainer rides the scheduler tick; the routes are mounted;
     the due commitment is preserved through the materializer (source-
     anchored where execution needs a DB, each with a real falsifier).
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
    def contains(self, *a, **k): return self

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


ROOT = "/workspace/operation/kpis"
TARGET = f"{ROOT}/metrics.csv"
CSV_DECL = (
    'target: metrics.csv\nschedule: "0 13 * * *"\npaused: false\n'
    "sources:\n  - id: main\n    url: https://example.com/m.csv\n"
    "shape:\n  columns: [date, mrr]\n"
)
MD_DECL = (
    'target: notes.md\nschedule: "0 13 * * *"\npaused: false\n'
    "sources:\n  - id: a\n    url: https://example.com/a\n"
    "  - id: b\n    url: https://example.com/b\n"
)

# ---------------------------------------------------------------------------
print("1. the designation boundary (D1) — refused loudly, across formats")
from services.strings import parse_string_yaml

csv_decl = parse_string_yaml(CSV_DECL, topic="operation/kpis",
                             declaration_path=f"{ROOT}/_string.yaml")
check("a csv designation parses healthy",
      csv_decl is not None and csv_decl.problem is None and csv_decl.format == "csv")
md_decl = parse_string_yaml(MD_DECL, topic="operation/notes",
                            declaration_path="/workspace/operation/notes/_string.yaml")
check("an md designation parses healthy (several sources allowed for prose)",
      md_decl is not None and md_decl.problem is None and md_decl.format == "md")

for tgt, want in [
    ("", "missing_target"),
    ("sub/f.csv", "invalid_target"),          # one segment, this folder
    ("_string.yaml", "invalid_target"),       # never the machinery files
    ("CONTRACT.md", "invalid_target"),
    ("deck.html", "unsupported_format"),      # authoring artifacts: named-deferred
]:
    d = parse_string_yaml(
        f"target: {tgt}\nsources:\n  - id: a\n    url: https://a.b/c\n",
        topic="t", declaration_path="p",
    )
    check(f"target {tgt!r} → problem {want}",
          d is not None and d.problem == want,
          f"got {d.problem if d else None}")

d = parse_string_yaml(
    "target: a.csv\nsources:\n  - id: a\n    url: https://a.b/c\n"
    "  - id: b\n    url: https://a.b/d\n",
    topic="t", declaration_path="p",
)
check("a structured format maps EXACTLY ONE endpoint (two → sources_invalid)",
      d is not None and d.problem == "sources_invalid")
d = parse_string_yaml(
    "target: a.csv\nsources:\n  - id: a\n    url: ftp://a.b/c\n",
    topic="t", declaration_path="p",
)
check("non-http(s) sources are refused (v1 is HTTP pull only, D4)",
      d is not None and d.problem == "sources_invalid")
check("unparseable yaml → None (the 422 repair state)",
      parse_string_yaml("x: [unclosed\n y", topic="t", declaration_path="p") is None)

# ---------------------------------------------------------------------------
print("2. the confinement law (D1/D3) — the write site refuses, executed")
from services.strings import StringDecl, _assert_string_write

decl = StringDecl(topic="operation/kpis", slug="string:operation/kpis",
                  target="metrics.csv")
try:
    _assert_string_write(decl, TARGET)
    check("the designated leaf passes the confinement assert", True)
except ValueError:
    check("the designated leaf passes the confinement assert", False)

for bad in [
    f"{ROOT}/other.csv",          # a sibling — un-designated
    f"{ROOT}/CONTRACT.md",        # the contract is the member's, never the writer's
    f"{ROOT}/_string.yaml",       # the declaration is not a write target
    "/workspace/elsewhere/metrics.csv",  # same leaf name, wrong folder
    f"{ROOT}/sub/metrics.csv",    # nested — outside the designation
]:
    try:
        _assert_string_write(decl, bad)
        check(f"confinement refuses {bad}", False, "(no exception)")
    except ValueError:
        check(f"confinement refuses {bad}", True)

# The run's write site actually calls the assert (source-anchored — the
# falsifier is deleting the call; the behavior half is executed above).
import inspect
from services import strings as _strings_mod
_run_src = inspect.getsource(_strings_mod.run_string_sweep)
check("run_string_sweep asserts confinement at the write site",
      "_assert_string_write(" in _run_src)
check("the run writes as a derivation citing the raws (ADR-423/448)",
      'revision_kind="derivation"' in _run_src and "derived_from=raw_paths" in _run_src)

# ---------------------------------------------------------------------------
print("3. the shape refusal (D3) — a violating fetch never lands")
from services.strings import ShapeViolation, map_structured

out = map_structured("date,extra,mrr\n2026-01-01,zz,100\n",
                     fmt="csv", shape={"columns": ["date", "mrr"]})
check("csv is PROJECTED to the declared columns, declared order",
      out == "date,mrr\n2026-01-01,100\n", repr(out))
try:
    map_structured("date,x\n1,2\n", fmt="csv", shape={"columns": ["date", "mrr"]})
    check("a missing declared column is refused", False, "(no exception)")
except ShapeViolation as e:
    check("a missing declared column is refused", "mrr" in str(e))
try:
    map_structured("{\"a\": 1}", fmt="json", shape={"keys": ["mrr"]})
    check("a missing declared json key is refused", False, "(no exception)")
except ShapeViolation:
    check("a missing declared json key is refused", True)
try:
    map_structured("not json", fmt="json", shape={})
    check("unparseable json is refused even with no shape", False, "(no exception)")
except ShapeViolation:
    check("unparseable json is refused even with no shape", True)

# The refusal is metered as the LOUD repair state and the desk reads it from
# the ledger — the route's composer, executed both directions.
from routes.strings import RunEvent, _compose_repair

fail = [RunEvent(slug="string-write:t", status="failed",
                 error_reason="shape_violation", created_at="2026-08-14T01:00:00Z")]
r = _compose_repair(fail)
check("a refused write composes the repair state",
      r is not None and r.reason == "shape_violation")
cleared = [RunEvent(slug="string-write:t", status="success",
                    created_at="2026-08-14T02:00:00Z")] + fail
check("a later success clears it", _compose_repair(cleared) is None)
noop = [RunEvent(slug="string-write:t", status="skipped", error_reason="no_change",
                 created_at="2026-08-14T02:00:00Z")] + fail
check("an honest no-change clears it too", _compose_repair(noop) is None)
weather = [RunEvent(slug="string-write:t", status="skipped",
                    error_reason="router_disabled", created_at="2026-08-14T02:00:00Z")]
check("router-off is weather, not repair", _compose_repair(weather) is None)

# ---------------------------------------------------------------------------
print("4. posture selection (D6 / ADR-567 D4) — executed three ways")
from services.lane_runner import LANE_MODELS, build_lane_conventions

model = next(iter(LANE_MODELS))
sdesk = build_lane_conventions(
    FakeClient({f"{ROOT}/_string.yaml": CSV_DECL,
                f"{ROOT}/CONTRACT.md": "Monthly KPI table; mrr in USD."}),
    "u1", model=model, artifact_path=TARGET, app="strings",
)
check("a strings-bound lane gets KEEPER'S DESK", "KEEPER'S DESK" in sdesk)
check("…which teaches the D1 law and the strict grammar",
      "only the DESIGNATED target" in sdesk and "READ IT BACK" in sdesk
      and "NEVER invent source URLs" in sdesk)
check("…and echoes the parsed declaration + contract",
      "parses OK" in sdesk and "Monthly KPI table" in sdesk)
check("…not the radar desk", "THE RESEARCHER'S DESK" not in sdesk)

rdesk = build_lane_conventions(
    FakeClient({}), "u1", model=model,
    artifact_path="/workspace/operation/t/report.md", app="radar",
)
check("a radar-bound lane still gets THE RESEARCHER'S DESK (567 pin holds)",
      "THE RESEARCHER'S DESK" in rdesk and "KEEPER'S DESK" not in rdesk)

studio = build_lane_conventions(
    FakeClient({}), "u1", model=model,
    artifact_path="/workspace/operation/deck/presentation.html",
)
check("an app-less bound lane still gets the studio posture (byte-compatible)",
      "KEEPER'S DESK" not in studio and "THE RESEARCHER'S DESK" not in studio)

from services.strings import build_keeper_desk_posture
empty = build_keeper_desk_posture(FakeClient({}), "u1", TARGET)
check("no declaration → the SETTING UP branch, naming the picked leaf",
      "NO DECLARATION YET" in empty and "metrics.csv" in empty)
broken = build_keeper_desk_posture(
    FakeClient({f"{ROOT}/_string.yaml": "x: [unclosed\n y"}), "u1", TARGET)
check("unparseable declaration → the loud repair line", "DOES NOT PARSE" in broken)
prob = build_keeper_desk_posture(
    FakeClient({f"{ROOT}/_string.yaml":
                "target: deck.html\nsources:\n  - id: a\n    url: https://a.b/c\n"}),
    "u1", TARGET)
check("parseable-but-cannot-run → named in the state block",
      "CANNOT RUN (unsupported_format)" in prob)

# ---------------------------------------------------------------------------
print("5. the resident (ADR-562) — keeper, a posture, priced")
import services.apps  # noqa: F401  (registration side-effect)
from services.agents_registry import KERNEL_AGENTS, KERNEL_POSTURES
from services.authoring import resident_for_app
from services.strings import resolve_strings_resident

check("strings registers keeper as its resident",
      resident_for_app("strings") == "keeper")
check("keeper is a POSTURE over Produce — the three-operation base roster stays closed",
      "keeper" in KERNEL_POSTURES
      and KERNEL_POSTURES["keeper"]["based_on"] == "designer"
      and "keeper" not in KERNEL_AGENTS
      and len(KERNEL_AGENTS) == 3)
r_model, r_posture = resolve_strings_resident()
check("the resident resolves to Keeper's character on a live engine",
      "Keeper" in r_posture and r_model in LANE_MODELS
      and not LANE_MODELS[r_model].get("retired"))
try:
    from services.model_router import ledger_model_name
    from services.telemetry import has_billing_rate
    check("Keeper's engine is priced (never routes unpriced)",
          has_billing_rate(ledger_model_name(r_model)))
except Exception as exc:  # pragma: no cover
    check(f"billing-rate probe ran ({exc})", False)

# ---------------------------------------------------------------------------
print("6. wiring — scheduler tick, routes, the due commitment")
import pathlib

sched_src = pathlib.Path("jobs/unified_scheduler.py").read_text()
check("the scheduler tick drains the strings lane",
      "drain_due_string_runs" in sched_src)
main_src = pathlib.Path("main.py").read_text()
check("the strings routes are mounted", "strings.router" in main_src)

mat_src = inspect.getsource(_strings_mod.materialize_string_index)
check("the materializer preserves the due commitment (b8ac1c7)",
      "preserve_due_commitment(" in mat_src)
check("a problem declaration is never scheduled (repair stays loud, not a "
      "silent failure loop)",
      "d.problem is None" in mat_src)

# Event slugs are the ledger contract (D4) — the run body emits both.
check("the run meters string-sweep:{topic} + string-write:{topic}",
      'slug=f"string-sweep:{topic}"' in _run_src
      and 'slug=f"string-write:{topic}"' in _run_src)

# ---------------------------------------------------------------------------
print()
if FAILURES:
    print(f"✗ {len(FAILURES)} check(s) failed: {FAILURES}")
    sys.exit(1)
print("✓ all ADR-569 strings checks passed")
