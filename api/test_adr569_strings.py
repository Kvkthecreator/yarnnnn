"""ADR-569 gate — Strings: the maintained file, kept under contract.

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
     executed two ways: app='strings' → THE STANDING-WORK DESK (role-neutral
     since ADR-604/610 — Supervisor both speaks and executes); (app='radar' was
     deleted with the app, ADR-592);
     THE RESEARCHER'S DESK; app-less bound → studio. Extends test_adr567's
     pins, never breaks them.
  5. THE RESIDENT (ADR-562) — strings registers supervisor, which resolves as a
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
check("a strings-bound lane gets THE STANDING-WORK DESK (role-neutral, ADR-604)",
      "THE STANDING-WORK DESK" in sdesk and "KEEPER'S DESK" not in sdesk)
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
# ADR-592 — the radar app is DELETED, so its desk branch is gone. A lane still
# naming `app="radar"` (a stale lane_meta row) must fall through to NO job
# overlay rather than resolving one — the branch is absent, not re-pointed.
check("a stale radar-bound lane resolves NO desk (the app is deleted, ADR-592)",
      "THE RESEARCHER'S DESK" not in rdesk and "STANDING-WORK DESK" not in rdesk)

studio = build_lane_conventions(
    FakeClient({}), "u1", model=model,
    artifact_path="/workspace/operation/deck/presentation.html",
)
check("an app-less bound lane still gets the studio posture (byte-compatible)",
      "STANDING-WORK DESK" not in studio and "THE RESEARCHER'S DESK" not in studio)

# ADR-606 D3: the target's head is a PARAMETER now — the lane kernel reads
# the bound artifact once per turn and hands it in; the builder's own reads
# are the desk files only (declaration + contract).
from services.strings import build_strings_desk_posture
empty = build_strings_desk_posture(FakeClient({}), "u1", TARGET, "")
check("no declaration → the SETTING UP branch, naming the picked leaf",
      "NO DECLARATION YET" in empty and "metrics.csv" in empty)
broken = build_strings_desk_posture(
    FakeClient({f"{ROOT}/_string.yaml": "x: [unclosed\n y"}), "u1", TARGET, "")
check("unparseable declaration → the loud repair line", "DOES NOT PARSE" in broken)
prob = build_strings_desk_posture(
    FakeClient({f"{ROOT}/_string.yaml":
                "target: deck.html\nsources:\n  - id: a\n    url: https://a.b/c\n"}),
    "u1", TARGET, "")
check("parseable-but-cannot-run → named in the state block",
      "CANNOT RUN (unsupported_format)" in prob)
check("a handed-in head is DESCRIBED, never re-read (ADR-606 D3)",
      "2 lines" in build_strings_desk_posture(FakeClient({}), "u1", TARGET, "a\nb"))

# ---------------------------------------------------------------------------
print("5. the resident (ADR-562) — supervisor, a posture, priced")
import services.apps  # noqa: F401  (registration side-effect)
from services.agents_registry import AGENTS
from services.authoring import resident_for_app, standing_executor_for_app
from services.strings import resolve_strings_resident

# ADR-604 opened the voice/executor seam; ADR-610 dissolved the executor
# BEING, so both resolve to Supervisor — and must do so BY DERIVATION (the
# field undeclared), never by the two being re-merged into one.
check("strings' desk voice is Supervisor (ADR-604 D1)",
      resident_for_app("strings") == "supervisor")
check("strings' standing executor derives the resident (ADR-610 D2)",
      standing_executor_for_app("strings") == "supervisor")
check("the dissolved `keeper` being is not resurrected (ADR-610 D1)",
      "keeper" not in AGENTS)
# Re-anchored for ADR-599: residents are self-contained (no based_on — the
# base operations are deleted with the colleague roster, which is EMPTY).
check("supervisor is a self-contained APP RESIDENT; the colleague roster is empty",
      "supervisor" in AGENTS
      and "based_on" not in AGENTS["supervisor"]
      # ADR-600 D2 — its home is the Strings desk: a being, not a hire.
      and AGENTS["supervisor"].get("offered") is False)
r_model, r_posture = resolve_strings_resident()
# Identity by IDENTITY, not by a substring of the prose: assert the resolved
# character IS the register's row, so a reworded posture cannot fail this and
# a swapped being cannot pass it.
check("the EXECUTOR resolves to Supervisor's character on a live engine",
      r_posture == AGENTS["supervisor"]["posture"]
      and r_model == AGENTS["supervisor"]["model"]
      and r_model in LANE_MODELS
      and not LANE_MODELS[r_model].get("retired"))
try:
    from services.model_router import ledger_model_name
    from services.telemetry import has_billing_rate
    check("the executor's engine is priced (never routes unpriced)",
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
print("7. reach with a receipt (ADR-594 D2) — DRIVEN")
import asyncio
from datetime import datetime, timezone
from services.strings import _reach_connector_sources, _CONNECTOR_CAPTURE_MIN_INTERVAL_S

# The run body invokes the reach step for connector sources, before the read.
check("the run reaches connector sources before reading",
      "_reach_connector_sources(" in _run_src
      and _run_src.index("_reach_connector_sources(") < _run_src.index("_read_connector_source("))

_captures: list = []


def _drive_reach(landed_age_s):
    """Drive the reach with one declared slack source whose newest landed
    snapshot is `landed_age_s` old (None = nothing landed)."""
    import services.workspace as ws
    import services.connectors as cn

    now = datetime.now(timezone.utc)

    class _UM:
        def __init__(self, client, uid):
            pass

        async def list(self, sub):
            if landed_age_s is None:
                return []
            stamp = datetime.fromtimestamp(
                now.timestamp() - landed_age_s, tz=timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
            return [f"{stamp}.md"]

    async def _fake_capture(client, user_id, row, *, observed_at, selectors=None):
        _captures.append({"row": row, "selectors": selectors})
        return {"success": True}

    orig = (ws.UserMemory, cn.connection_row, cn.run_connector_capture)
    ws.UserMemory = _UM
    cn.connection_row = lambda client, uid, plat: {"platform": plat, "landscape": {}}
    cn.run_connector_capture = _fake_capture
    try:
        asyncio.get_event_loop().run_until_complete(
            _reach_connector_sources(
                None, "u1",
                [{"id": "standup", "connector": "slack", "selector": "C001"}],
                observed_at="2026-08-21T09:00:00Z",
            )
        )
    finally:
        ws.UserMemory, cn.connection_row, cn.run_connector_capture = orig


_captures.clear()
_drive_reach(None)
check("nothing landed → the run REACHES (capture invoked, selector-narrowed)",
      len(_captures) == 1 and _captures[0]["selectors"] == ["C001"],
      str(_captures))

_captures.clear()
_drive_reach(_CONNECTOR_CAPTURE_MIN_INTERVAL_S * 4)
check("a stale snapshot → the run reaches again",
      len(_captures) == 1, str(_captures))

_captures.clear()
_drive_reach(60)
check("a FRESH snapshot → no reach (the freshness floor is the spend guard: "
      "the receipt itself gates the platform read)",
      len(_captures) == 0, str(_captures))


def _drive_reach_unconnected():
    import services.connectors as cn
    orig = cn.connection_row
    cn.connection_row = lambda client, uid, plat: None
    try:
        asyncio.get_event_loop().run_until_complete(
            _reach_connector_sources(
                None, "u1",
                [{"id": "standup", "connector": "slack", "selector": "C001"}],
                observed_at="2026-08-21T09:00:00Z",
            )
        )
    finally:
        cn.connection_row = orig


_captures.clear()
_drive_reach_unconnected()
check("an unconnected platform → no reach, no raise (the read step reports "
      "the honest empty)", len(_captures) == 0)

# The reach stamp must satisfy the shared reader's grammar — an isoformat
# stamp would land snapshots the reader then skips as unstamped.
from services.connectors import parse_stamp as _ps
check("the run passes a parse_stamp-conformant stamp to the reach",
      '%Y-%m-%dT%H:%M:%SZ' in _run_src and _ps("2026-08-21T09:00:00Z.md") is not None)

# ---------------------------------------------------------------------------
print()
if FAILURES:
    print(f"✗ {len(FAILURES)} check(s) failed: {FAILURES}")
    sys.exit(1)
print("✓ all ADR-569 strings checks passed")
