"""ADR-659 gate — standing work reads the workspace.

    D1  the claim is its own column, and it is a lock
    D2  a run shows what it wrote (derived, never stored)
    D3  a composed app executes nothing
    D4  a source may be a workspace path        D5  the cycle is refused by name
    D6  the pace rule — unmoved sources are skipped at $0, before the paid turn
    D7  the door and the skill say it

Script-shaped: run it and READ THE COUNT (`pytest` collects nothing from it).

    cd api && python3 test_adr659_standing_work_reads_the_workspace.py

Everything is DRIVEN against an in-memory database that models the real query
shapes (`lt`, `like`, the not-in-Trash `or_`), with the REAL sweep, the REAL
derive turn, the REAL drain loop and the REAL routes. Only the edges are faked:
the model call, the HTTP fetch, the balance, the embed. Each arm was proven RED
by editing the shipped file in place and restoring it in a `finally`.
"""

from __future__ import annotations

import asyncio
import dataclasses
import re
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

API = Path(__file__).resolve().parent
sys.path.insert(0, str(API))

PASS = FAIL = 0


def check(name: str, cond, note: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}" + (f" — {note}" if note else ""))


def _read(rel: str) -> str:
    return (API / rel).read_text()


# ═════════════════════════════════════════════════════════════════════════════
# An in-memory PostgREST — the query shapes the code actually sends
# ═════════════════════════════════════════════════════════════════════════════


class _Res:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self.filters: list = []
        self._order = self._limit = None
        self._op, self._payload = "select", None

    def select(self, *a, **k): return self
    def insert(self, row): self._op, self._payload = "insert", dict(row); return self
    def update(self, data): self._op, self._payload = "update", dict(data); return self
    def delete(self): self._op = "delete"; return self
    def eq(self, k, v): self.filters.append(("eq", k, v)); return self
    def in_(self, k, vs): self.filters.append(("in", k, list(vs))); return self
    def like(self, k, pat): self.filters.append(("like", k, pat)); return self
    def lt(self, k, v): self.filters.append(("lt", k, v)); return self
    def lte(self, k, v): self.filters.append(("lte", k, v)); return self
    def or_(self, clause, *a, **k): self.filters.append(("or", clause, None)); return self
    def order(self, col, desc=False, **k): self._order = (col, bool(desc)); return self
    def limit(self, n, **k): self._limit = n; return self

    @staticmethod
    def _t(v):
        """Timestamps compare as instants, as Postgres compares them."""
        try:
            return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        except ValueError:
            return str(v)

    def _match(self, r) -> bool:
        for op, k, v in self.filters:
            cur = r.get(k)
            if op == "eq" and cur != v: return False
            if op == "in" and cur not in v: return False
            if op == "lt" and not (cur is not None and self._t(cur) < self._t(v)): return False
            if op == "lte" and not (cur is not None and self._t(cur) <= self._t(v)): return False
            if op == "like":
                # `%` any run, `_` any ONE character — LIKE's real semantics,
                # which is the over-match `gather_path_source` re-checks.
                rx = "^" + re.escape(str(v)).replace("%", ".*").replace("_", ".") + "$"
                if not re.match(rx, str(cur or "")): return False
            if op == "or":
                ok = False
                for part in str(k).split(","):
                    col, cmp, val = part.split(".", 2)
                    c = r.get(col)
                    if cmp == "is" and val == "null" and c is None: ok = True
                    if cmp == "neq" and c != val: ok = True
                if not ok: return False
        return True

    def execute(self):
        rows = self.db.tables.setdefault(self.name, [])
        if self._op == "insert":
            row = self._payload
            row.setdefault("id", self.db.next_id())
            if self.name == "tasks":  # migration 258's column default
                row.setdefault("claimed_until", "1970-01-01T00:00:00+00:00")
            rows.append(row)
            return _Res([dict(row)])
        matched = [r for r in rows if self._match(r)]
        if self._op == "update":
            for r in matched:
                r.update(self._payload)
            return _Res([dict(r) for r in matched])
        if self._op == "delete":
            for r in matched:
                rows.remove(r)
            return _Res([dict(r) for r in matched])
        if self._order:
            col, desc = self._order
            matched = sorted(matched, key=lambda r: str(r.get(col) or ""), reverse=desc)
        if self._limit is not None:
            matched = matched[: self._limit]
        return _Res([dict(r) for r in matched])


class FakeDB:
    def __init__(self):
        self.tables: dict[str, list[dict]] = {}
        self._seq = 0

    def next_id(self):
        self._seq += 1
        return f"id-{self._seq:04d}"

    def table(self, name):
        return _Query(self, name)

    def put(self, path, content, *, at, ws="ws-A", lifecycle="active"):
        self.tables.setdefault("workspace_files", []).append({
            "id": self.next_id(), "user_id": U, "workspace_id": ws, "path": path,
            "content": content, "updated_at": at.isoformat(), "lifecycle": lifecycle,
        })


U = "00000000-0000-4000-8000-00000000aaaa"
WS = "ws-A"
T0 = datetime(2026, 9, 20, 9, 0, tzinfo=timezone.utc)

import services.workspace_context as _wc  # noqa: E402
import services.schedule_utils as _su  # noqa: E402
import services.access as _access  # noqa: E402

_wc._current_workspace_id.set(WS)
_wc.acting_workspace_owner = lambda client, user_id, workspace_id=None: U
_su.get_workspace_timezone = lambda client, user_id, default="UTC": "UTC"
_access.resolve_access = lambda auth, path, verb: types.SimpleNamespace(allowed=True, reason="ok")

import services.standing_work as st  # noqa: E402
import services.scheduling as sched  # noqa: E402
import services.platform_limits as pl  # noqa: E402
import services.telemetry as tel  # noqa: E402
import services.lane_runner as _lr  # noqa: E402
import services.model_router as _mr  # noqa: E402
import services.authored_substrate as _asub  # noqa: E402
import routes.standing_work as R  # noqa: E402

loop = asyncio.new_event_loop()
run = loop.run_until_complete


def _decl(yaml_body: str, topic: str = "reports", ws: str = WS):
    return st.parse_standing_yaml(
        yaml_body, topic=topic, declaration_path=f"/workspace/{topic}/_standing.yaml",
        user_id=U, workspace_id=ws,
    )


# ═════════════════════════════════════════════════════════════════════════════
print("D1. the claim is its own column, and it is a lock")
# ═════════════════════════════════════════════════════════════════════════════

_NEVER_RUN = _decl(
    "target: brief.md\nschedule: '0 9 * * 1-5'\nfire_on_activation: true\n"
    "sources:\n  - id: a\n    url: https://example.com\n", topic="t",
)
_NEVER_RUN_YAML = (
    "target: brief.md\nschedule: '0 9 * * 1-5'\nfire_on_activation: true\n"
    "sources:\n  - id: a\n    url: https://example.com\n")
import services.supabase as _sb  # noqa: E402
db = FakeDB()
# The declaration FILE must exist: `_due_standing` discovers before it scans, and
# a scan over a workspace with no declarations returns [] whatever it filters —
# which is how this arm first stayed GREEN with the hold filter deleted.
db.put("/workspace/t/_standing.yaml", _NEVER_RUN_YAML, at=T0)
db.tables["workspaces"] = [{"id": WS, "owner_id": U}]
_sb.get_service_client = lambda: db
run(st.materialize_standing_index(db, U, [_NEVER_RUN], now=T0))
_row = db.tables["tasks"][0]
check("an armed, UNHELD row is due (the control for the arm below)",
      [d.slug for _, d in run(st._due_standing(db, datetime.now(timezone.utc)))] == ["standing:t"])
check("a new index row is born UNHELD (the column default)",
      _row.get("claimed_until") == sched.UNHELD, f"got {_row.get('claimed_until')}")
check("the first claim takes the lock", sched.claim_run(db, U, _NEVER_RUN.slug, "standing"))
_held = db.tables["tasks"][0]["claimed_until"]

# ⭐ THE DRIVEN DEFECT, INVERTED. Before D1 this exact sequence rewrote the
# sentinel to `now`, the row came due, and the second claim SUCCEEDED mid-run.
run(st.materialize_standing_index(db, U, [_NEVER_RUN], now=T0 + timedelta(minutes=5)))
check("the materializer does not touch the hold",
      db.tables["tasks"][0]["claimed_until"] == _held)
check("a SECOND claim is refused while the first run is in flight",
      sched.claim_run(db, U, _NEVER_RUN.slug, "standing") is False)
_due = run(st._due_standing(db, datetime.now(timezone.utc)))
check("a held row is not even DUE", _due == [], f"due={_due}")

sched.record_run(db, U, _NEVER_RUN, "standing", last_run_at=datetime.now(timezone.utc),
                 user_timezone="UTC")
check("record_run RELEASES the hold",
      db.tables["tasks"][0]["claimed_until"] == sched.UNHELD)
check("…and the row is claimable again", sched.claim_run(db, U, _NEVER_RUN.slug, "standing"))

db.tables["tasks"][0]["claimed_until"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
check("a LAPSED hold (a crashed run) is claimable",
      sched.claim_run(db, U, _NEVER_RUN.slug, "standing"))
check("no row → no claim (a caller materializes first; never 'free to run')",
      sched.claim_run(db, U, "standing:ghost", "standing") is False)

_routes_src, _sched_src, _sw_src = (
    _read("routes/standing_work.py"), _read("services/scheduling.py"), _read("services/standing_work.py"))
check("the A1.8 heuristic is DELETED, not kept beside the lock",
      "_claim_in_flight" not in _routes_src and "read_standing_task_row" not in _routes_src + _sw_src)
check("the claim reads no value from its caller",
      "original_next_run" not in _sched_src + _sw_src + _read("services/capture/scheduling.py"))
check("the materializer never writes the hold",
      "claimed_until" not in _sw_src.split("async def materialize_standing_index")[1]
      .split("\n# -----")[0])
check("scheduling.__all__ names only what exists",
      all(hasattr(sched, n) for n in sched.__all__), f"{[n for n in sched.__all__ if not hasattr(sched, n)]}")

# The manual door: materialize → claim → run(force) → release in `finally`.
_run_src = _routes_src.split("async def run_standing_now")[1].split("\ndef ")[0]
check("Run now materializes BEFORE it claims",
      0 < _run_src.find("await door.materialize(") < _run_src.find("claim_run("))
check("Run now releases in a `finally`",
      "finally:" in _run_src and _run_src.find("finally:") < _run_src.find("record_run("))

# ═════════════════════════════════════════════════════════════════════════════
print("D3. a composed app executes nothing")
# ═════════════════════════════════════════════════════════════════════════════

_SRC = "schedule: '0 9 * * *'\nsources:\n  - id: a\n    url: https://example.com\n"
check("`app: supervisor` is refused `app_invalid`",
      _decl("target: x.md\napp: supervisor\n" + _SRC).problem == "app_invalid")
_blog = _decl("target: x.md\napp: blogger\n" + _SRC)
check("`app: blogger` still resolves its resident",
      _blog.problem is None and st.resolve_executor(_blog)[0] == "blogger")
check("the derived default is untouched (prose → text → editor)",
      st.resolve_executor(_decl("target: x.md\n" + _SRC))[0] == "editor")

# ═════════════════════════════════════════════════════════════════════════════
print("D4. a source may be a workspace path")
# ═════════════════════════════════════════════════════════════════════════════

check("three spellings of one path are ONE path",
      {st.normalize_source_path(p) for p in
       ("/workspace/research/digest.md", "workspace/research/digest.md", "research/digest.md")}
      == {("research/digest.md", False)})
check("a trailing slash is a folder", st.normalize_source_path("inbound/uploads/") == ("inbound/uploads", True))
check("traversal, empties and backslashes are not paths",
      all(st.normalize_source_path(p) is None for p in ("../x", "a/../b", "", "/", "a//b", "a\\b")))

_P = "target: summary.md\nschedule: '0 9 * * *'\nsources:\n"
check("a file source parses healthy", _decl(_P + "  - id: d\n    path: research/digest.md\n").problem is None)
check("a folder source parses healthy", _decl(_P + "  - id: f\n    path: inbound/uploads/\n").problem is None)
check("a folder CONTAINING the kept file is healthy (it gathers around it)",
      _decl(_P + "  - id: f\n    path: reports/\n").problem is None)
check("its own CONTRACT.md is not a source",
      _decl(_P + "  - id: c\n    path: reports/CONTRACT.md\n").problem == "sources_invalid")
check("a structured target refuses a FOLDER",
      _decl("target: m.csv\nschedule: '0 9 * * *'\nsources:\n  - id: f\n    path: data/\n").problem
      == "sources_invalid")
check("a structured target takes one FILE",
      _decl("target: m.csv\nschedule: '0 9 * * *'\nsources:\n  - id: f\n    path: data/raw.csv\n").problem is None)
# ADR-666 D1 added `browser` — a key for WHO does the work, not a source shape.
check("no new declaration KEY was needed — `path` lives inside `sources`",
      st.DECLARATION_KEYS == frozenset({"target", "app", "schedule", "sources", "shape", "paused",
                                        "paused_until", "browser"}))

db = FakeDB()
db.put("/workspace/inbound/uploads/a.md", "alpha body", at=T0)
db.put("/workspace/inbound/uploads/b.extracted.md", "beta body", at=T0 + timedelta(hours=1))
db.put("/workspace/inbound/uploads/trashed.md", "SECRET-TRASH", at=T0 + timedelta(hours=2), lifecycle="archived")
db.put("/workspace/inbound/uploads/photo.png", None, at=T0 + timedelta(hours=3))
db.put("/workspace/inbound/uploads/_captures.yaml", "captures: []", at=T0 + timedelta(hours=3))
db.put("/workspace/inbound/uploads/other.md", "SECRET-OTHER-WORKSPACE", at=T0, ws="ws-B")
_f = _decl(_P + "  - id: f\n    path: inbound/uploads/\n")
_mat, _paths, _moved = st.gather_path_source(db, U, _f, "inbound/uploads", True)
check("a folder gathers its live text, NEWEST first",
      _mat is not None and _mat.index("beta body") < _mat.index("alpha body"), str(_mat)[:120])
check("Trash is never material", "SECRET-TRASH" not in (_mat or ""))
check("binary and `_`-prefixed machine config are never material",
      _paths == ["/workspace/inbound/uploads/b.extracted.md", "/workspace/inbound/uploads/a.md"], str(_paths))
# LIKE reads `_` as "any one character", so `team_notes/%` also matches
# `teamXnotes/…`. The folder name MUST carry an underscore for this arm to be
# able to fail — with `inbound/uploads` it stayed GREEN under falsification.
db.put("/workspace/team_notes/mine.md", "my notes", at=T0)
db.put("/workspace/teamXnotes/theirs.md", "SECRET-LIKE-OVERMATCH", at=T0)
_matU, _pathsU, _ = st.gather_path_source(
    db, U, _decl(_P + "  - id: f\n    path: team_notes/\n"), "team_notes", True)
check("LIKE's `_` wildcard cannot over-match a neighbouring folder",
      _pathsU == ["/workspace/team_notes/mine.md"] and "SECRET-LIKE-OVERMATCH" not in (_matU or ""),
      str(_pathsU))
check("ANOTHER WORKSPACE's same-named path is never read", "SECRET-OTHER-WORKSPACE" not in (_mat or ""))
check("the gather says when its newest file moved", _moved == T0 + timedelta(hours=1), str(_moved))

db.put("/workspace/reports/summary.md", "THE KEPT FILE", at=T0)
db.put("/workspace/reports/CONTRACT.md", "THE CONTRACT", at=T0)
db.put("/workspace/reports/note.md", "a note", at=T0)
_own = _decl(_P + "  - id: f\n    path: reports/\n")
_mat2, _paths2, _ = st.gather_path_source(db, U, _own, "reports", True)
check("a run never reads its OWN machinery as material",
      _paths2 == ["/workspace/reports/note.md"] and "THE KEPT FILE" not in _mat2, str(_paths2))

for i in range(st._MAX_FOLDER_FILES + 5):
    db.put(f"/workspace/big/n{i:02d}.md", f"file {i}", at=T0 + timedelta(minutes=i))
_mat3, _paths3, _ = st.gather_path_source(db, U, _decl(_P + "  - id: f\n    path: big/\n"), "big", True)
check("a folder is BOUNDED, and the turn is told what it did not see",
      len(_paths3) == st._MAX_FOLDER_FILES and "5 older files NOT shown" in _mat3, _mat3[:90])
_one, _onep, _ = st.gather_path_source(db, U, _f, "inbound/uploads/a.md", False)
check("a FILE's material is its content, unadorned (a structured map can parse it)",
      _one == "alpha body" and _onep == ["/workspace/inbound/uploads/a.md"])
check("an absent path is the honest empty", st.gather_path_source(db, U, _f, "nope", True) == (None, [], None))

# ═════════════════════════════════════════════════════════════════════════════
print("D5. the cycle is refused by name")
# ═════════════════════════════════════════════════════════════════════════════

check("a declaration sourcing its OWN target is `source_cycle`",
      _decl(_P + "  - id: s\n    path: reports/summary.md\n").problem == "source_cycle")


def _chain(a_src: str, b_src: str, c_src: str = ""):
    ds = [
        _decl(f"target: a.md\nschedule: '0 9 * * *'\nsources:\n  - id: s\n    {a_src}\n", topic="A"),
        _decl(f"target: b.md\nschedule: '0 9 * * *'\nsources:\n  - id: s\n    {b_src}\n", topic="B"),
    ]
    if c_src:
        ds.append(_decl(f"target: c.md\nschedule: '0 9 * * *'\nsources:\n  - id: s\n    {c_src}\n", topic="C"))
    st.mark_source_cycles(ds)
    return [d.problem for d in ds]


check("a two-declaration loop marks BOTH", _chain("path: B/b.md", "path: A/a.md") == ["source_cycle"] * 2)
check("a loop through a FOLDER source is still a loop",
      _chain("path: B/", "path: A/a.md") == ["source_cycle"] * 2)
check("a three-declaration loop marks all three",
      _chain("path: C/c.md", "path: A/a.md", "path: B/b.md") == ["source_cycle"] * 3)
check("a straight CHAIN is healthy — that is the point",
      _chain("url: https://example.com", "path: A/a.md", "path: B/b.md") == [None, None, None])

db = FakeDB()
db.put("/workspace/A/_standing.yaml",
       "target: a.md\nschedule: '0 9 * * *'\nsources:\n  - id: s\n    path: B/b.md\n", at=T0)
db.put("/workspace/B/_standing.yaml",
       "target: b.md\nschedule: '0 9 * * *'\nsources:\n  - id: s\n    path: A/a.md\n", at=T0)
db.put("/workspace/A/_standing.yaml",  # the SAME paths in the owner's other workspace: no part of it
       "target: a.md\nschedule: '0 9 * * *'\nsources:\n  - id: s\n    url: https://example.com\n", at=T0, ws="ws-B")
db.tables["workspaces"] = [{"id": "ws-A", "owner_id": U}, {"id": "ws-B", "owner_id": U}]
_sb.get_service_client = lambda: db
_found = st.discover_standing(db).get(U, [])
check("DISCOVERY marks the loop, so neither is indexed",
      sorted((d.workspace_id, d.topic, d.problem) for d in _found)
      == [("ws-A", "A", "source_cycle"), ("ws-A", "B", "source_cycle"), ("ws-B", "A", None)],
      str(sorted((d.workspace_id, d.topic, d.problem) for d in _found)))
run(st.materialize_standing_index(db, U, [d for d in _found if d.workspace_id == "ws-A"], now=T0))
check("a looped declaration gets NO index row (structural, not advisory)",
      db.tables.get("tasks", []) == [])

# ═════════════════════════════════════════════════════════════════════════════
print("D6. the pace rule — unmoved sources are skipped at $0")
# ═════════════════════════════════════════════════════════════════════════════


def _completion(text: str):
    kw = {"text": text, "finish_reason": "stop"}
    for name, f in _mr.RoutedCompletion.__dataclass_fields__.items():
        if name not in kw and f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING:
            kw[name] = "anthropic/claude-sonnet-5"
    out = _mr.RoutedCompletion(**kw)
    out.usage = {"input_tokens": 100, "output_tokens": 20}
    return out


def _sweep(db, decl, *, force=False, answer="# Summary\n\nfresh.\n", fetch="page body"):
    """The REAL sweep + the REAL derive turn. Returns (result, model_calls, events, writes)."""
    model = AsyncMock(return_value=_completion(answer))
    events: list = []
    writes: list = []

    def _ledger(*a, **k):
        events.append(k)
        db.tables.setdefault("execution_events", []).append({
            "slug": k.get("slug"), "status": k.get("status"), "error_reason": k.get("error_reason"),
            "workspace_id": k.get("workspace_id"), "user_id": k.get("user_id"),
            "duration_ms": k.get("duration_ms") or 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    def _write(client, **k):
        writes.append(k)
        if k.get("revision_kind") == "observation":
            db.put(k["path"], k["content"], at=datetime.now(timezone.utc))
        return "rev-1"

    real = tel.record_execution_event
    tel.record_execution_event = _ledger
    try:
        with patch.object(pl, "check_balance", return_value=(True, 5.0)), \
             patch.object(st, "_fetch_source", new=AsyncMock(return_value=fetch)), \
             patch.object(st, "resolve_executor", return_value=("editor", "anthropic/claude-sonnet-5", "c")), \
             patch.object(_lr, "build_standing_frame", return_value="frame"), \
             patch.object(_mr, "model_router_enabled", return_value=True), \
             patch.object(_mr, "route_completion", new=model), \
             patch.object(_asub, "write_revision", side_effect=_write), \
             patch("services.primitives.workspace._embed_workspace_file", new=AsyncMock()):
            out = run(st.run_standing_sweep(db, U, decl, force=force))
    finally:
        tel.record_execution_event = real
    return out, model.await_count, events, writes


_PAST = datetime.now(timezone.utc) - timedelta(days=2)
db = FakeDB()
db.put("/workspace/research/digest.md", "the digest, v1", at=_PAST)
db.put("/workspace/reports/CONTRACT.md", "A summary of the digest.", at=_PAST)
_d = _decl(_P + "  - id: d\n    path: research/digest.md\n")

_o1, _n1, _e1, _w1 = _sweep(db, _d)
check("a FIRST run (never judged) proceeds to the model", _n1 == 1 and _o1.get("success") is True, f"{_o1}")
check("…and cites the workspace path it read — the graph is WITNESSED on the ledger",
      [w.get("derived_from") for w in _w1 if w.get("revision_kind") == "derivation"]
      == [["/workspace/research/digest.md"]], str([w.get("derived_from") for w in _w1]))
check("every row of the run carries the declaration's OWN workspace",
      _e1 and all(e.get("workspace_id") == WS for e in _e1), str([e.get("workspace_id") for e in _e1]))

_o2, _n2, _e2, _w2 = _sweep(db, _d)
check("⭐ nothing moved → NO model call", _n2 == 0, f"calls={_n2} out={_o2}")
check("…recorded `skipped` / `sources_unchanged`, mechanical — never silent",
      any(e.get("slug") == "standing-write:reports" and e.get("status") == "skipped"
          and e.get("error_reason") == "sources_unchanged" and e.get("mode") == "mechanical" for e in _e2),
      str([(e.get("slug"), e.get("status"), e.get("error_reason")) for e in _e2]))
check("…and writes nothing", not any(w.get("revision_kind") == "derivation" for w in _w2))

_o3, _n3, _e3, _ = _sweep(db, _d)
check("a pace-skip is not a judgment — it does not reset the clock, and stays $0", _n3 == 0)

db.tables["workspace_files"][0].update(
    content="the digest, v2", updated_at=datetime.now(timezone.utc).isoformat())
_o4, _n4, _, _ = _sweep(db, _d)
check("a source that MOVED → the model is called", _n4 == 1, f"calls={_n4} out={_o4}")

_o5, _n5, _, _ = _sweep(db, _d)
check("…once: the next tick is $0 again", _n5 == 0)

db.tables["workspace_files"][1].update(updated_at=datetime.now(timezone.utc).isoformat())
_o6, _n6, _, _ = _sweep(db, _d)
check("a newer CONTRACT re-judges an unchanged world", _n6 == 1, f"calls={_n6}")

_o7, _n7, _e7, _ = _sweep(db, _d, force=True)
check("Run now (`force`) always proceeds — the member asked", _n7 == 1)
check("…and the ledger says `manual`, not `scheduled`",
      _e7 and all(e.get("trigger_type") == "manual" for e in _e7), str({e.get("trigger_type") for e in _e7}))
check("a scheduled run's rows say `scheduled`", all(e.get("trigger_type") == "scheduled" for e in _e1))

# A FAILED run is not a judgment: it must retry, not be paced out.
db = FakeDB()
db.put("/workspace/research/digest.md", "the digest", at=_PAST)
db.tables["execution_events"] = [
    {"slug": "standing-sweep:reports", "status": "success", "workspace_id": WS, "duration_ms": 10,
     "created_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()},
    {"slug": "standing-write:reports", "status": "failed", "error_reason": "derive_raised", "workspace_id": WS,
     "created_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()},
]
check("a FAILED prior run is not a judgment — the next tick retries",
      st.last_judged_at(db, U, _d) is None and _sweep(db, _d)[1] == 1)

# ⭐ A source that moves DURING the model call must read as moved.
db = FakeDB()
_start = datetime.now(timezone.utc) - timedelta(minutes=10)
db.tables["execution_events"] = [
    {"slug": "standing-sweep:reports", "status": "success", "workspace_id": WS, "duration_ms": 2000,
     "created_at": (_start + timedelta(seconds=2)).isoformat()},
    {"slug": "standing-write:reports", "status": "success", "workspace_id": WS,
     "created_at": (_start + timedelta(seconds=40)).isoformat()},
]
_j = st.last_judged_at(db, U, _d)
check("`last judged` is when the run began READING, not when its row was written",
      _j is not None and abs((_j - _start).total_seconds()) < 1, str(_j))
db.put("/workspace/research/digest.md", "changed mid-run", at=_start + timedelta(seconds=20))
check("…so a source that moved DURING the model call is re-read", _sweep(db, _d)[1] == 1)

# Another workspace's ledger is not this declaration's history.
db = FakeDB()
db.put("/workspace/research/digest.md", "the digest", at=_PAST)
db.tables["execution_events"] = [
    {"slug": "standing-write:reports", "status": "success", "workspace_id": "ws-B",
     "created_at": datetime.now(timezone.utc).isoformat()}]
check("another workspace's same-named topic is not this one's judgment",
      st.last_judged_at(db, U, _d) is None)

# HTTP: an unchanged body is cited, not retained again.
db = FakeDB()
_h = _decl("target: summary.md\nschedule: '0 9 * * *'\nsources:\n  - id: page\n    url: https://example.com\n")
_, _hn1, _, _hw1 = _sweep(db, _h, fetch="the page")
_, _hn2, _, _hw2 = _sweep(db, _h, fetch="the page")
check("an HTTP body identical to the last raw is NOT retained again",
      sum(1 for w in _hw1 if w.get("revision_kind") == "observation") == 1
      and sum(1 for w in _hw2 if w.get("revision_kind") == "observation") == 0)
check("…and an unchanged page costs no model call", (_hn1, _hn2) == (1, 0), f"{(_hn1, _hn2)}")
_, _hn3, _, _hw3 = _sweep(db, _h, fetch="the page, edited")
check("a CHANGED page is retained and judged",
      _hn3 == 1 and sum(1 for w in _hw3 if w.get("revision_kind") == "observation") == 1)

# ⭐ Axiom 4: nothing here FIRES a run.
check("the pace rule adds no trigger — the run's only callers are the drain and Run now",
      sorted(p.name for p in (API / "services").rglob("*.py") if "run_standing_sweep(" in p.read_text()
             and p.name != "standing_work.py") == []
      and "run_standing_sweep(" in _routes_src)

# ═════════════════════════════════════════════════════════════════════════════
# D2 ("a run shows what it wrote") is SUPERSEDED by ADR-666 D2: what a run wrote
# is stored on its row in `runs`, and the 180-second time-window join this
# section tested is deleted. `test_adr666_the_run.py` holds the pointer.
# ═════════════════════════════════════════════════════════════════════════════

# ═════════════════════════════════════════════════════════════════════════════
print("D4/D5 at the DOOR, and D7")
# ═════════════════════════════════════════════════════════════════════════════

db = FakeDB()
db.tables["workspaces"] = [{"id": WS, "owner_id": U, "timezone": "UTC"}]
_sb.get_service_client = lambda: db
auth = types.SimpleNamespace(client=db, user_id=U, workspace_id=WS, caller_identity="operator")
_written: list = []


def _door_write(client, **k):
    _written.append(k["path"])
    db.put(k["path"], k["content"], at=datetime.now(timezone.utc))
    return "rev"


def _create(**over):
    body = dict(folder="overview", target="overview.md", schedule="0 9 * * *",
                contract="An overview.", sources=[{"id": "f", "path": "inbound/uploads/"}])
    body.update(over)
    with patch.object(_asub, "write_revision", side_effect=_door_write):
        try:
            return run(R.create_standing(R.CreateStandingRequest(**body), auth)), None
        except Exception as exc:  # noqa: BLE001
            return None, (getattr(exc, "detail", None) or {})


_ok, _err = _create()
check("the door creates a declaration over a workspace FOLDER",
      _ok is not None and _ok.sources[0].path == "inbound/uploads/", str(_err))
check("…and it is discovered healthy", [d.problem for d in st.discover_standing(db).get(U, [])] == [None])

_, _err = _create(folder="loop", target="loop.md", sources=[{"id": "s", "path": "overview/overview.md"}])
check("a straight chain off that kept file is accepted", _err is None, str(_err))
with patch.object(_asub, "write_revision", side_effect=_door_write):
    try:
        run(R.update_standing("overview", R.UpdateStandingRequest(
            sources=[{"id": "s", "path": "loop/loop.md"}]), auth))
        _patched = None
    except Exception as exc:  # noqa: BLE001
        _patched = (getattr(exc, "detail", None) or {}).get("problem")
check("⭐ an EDIT that would close the loop is refused `source_cycle`, and writes nothing",
      _patched == "source_cycle", str(_patched))

import services.primitives.workspace as _pw  # noqa: E402
with patch.object(_pw, "_is_path_readable_for_principal", return_value=False):
    _, _err = _create(folder="secret", target="s.md")
check("a source the DECLARER cannot read is refused `source_unreadable`",
      (_err or {}).get("problem") == "source_unreadable" and "/workspace/secret/_standing.yaml" not in _written,
      str(_err))

_starts = R.standing_starts(db, U)
# ADR-666 D1 — the member's browser is always offered too, first among the three.
check("the workspace start is ALWAYS offered — connection or none",
      [s.kind for s in _starts] == ["browser", "path", "url"], str([s.kind for s in _starts]))

_skill = _read("services/skills/declaring-standing-work/SKILL.md")
check("the declaring skill teaches the path source", "path:" in _skill and "folder" in _skill.lower())
check("…and the chain, and the loop it must not make",
      "another" in _skill.lower() and "loop" in _skill.lower())

print()
print("=" * 70)
print(f"  {PASS} passed, {FAIL} failed")
print("=" * 70)
print("✓ all ADR-659 checks passed" if not FAIL else "✗ ADR-659 gate RED")
sys.exit(1 if FAIL else 0)
