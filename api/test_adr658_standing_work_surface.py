"""ADR-658 gate — the Supervisor manages standing work: the door, the detail,
the starts, the retire, and the surface that mounts them.

Run with:  cd api && python3 test_adr658_standing_work_surface.py
(script-style — prints ✗ and exits 1 on failure; under pytest it reports a
false PASS like the other script gates, so read the count.)

Every check is DRIVEN where the ADR says driven — the route handlers run
unmodified over a fake database that models Trash (`lifecycle`), the revision
chain and the blob store, so `write_revision`, `archive_live_file`,
`discover_standing` and `materialize_standing_index` all execute for real.
A fake that answers correctly whatever you ask cannot see a missing
constraint; this one refuses to hide an archived row unless the caller asked
for live rows (the ADR-639 gate's lesson), which is exactly what the tombstone
drive (§A1.6) needs to fail on.

  D4  THE DOOR refuses BY NAME (missing_contract · unsupported_format ·
      sources_invalid · app_invalid · already_declared), writes nothing on a
      refusal, and on success lands CONTRACT.md + _standing.yaml through the
      one composer and the one write path, armed, indexed, agent-free.
  D2  THE MINDER IS DERIVED: falsify the derivation and the label changes;
      no key in the YAML or the index row names an agent.
  D6  THE DETAIL serves the instructions and the runs for exactly that topic;
      a widened PATCH that would produce a problem is refused by name and
      writes nothing; the pause switch on a problem declaration is allowed.
  §6.2 RETIRE archives the declaration ONLY — target and instructions stay
      live with their chains — and the index drops the row.
  A1.6 THE TOMBSTONE DRIVE: create → retire → create the same folder; the
      second declaration is live and discovered, never left in Trash.
  D7  THE STARTS derive from connections that hold a capture binding; an
      attached MCP row and an unbound platform yield none; HTTP is always last.
  D5  `threads` is gone; the surface renders work · needs-you · note; the
      honest miss survives; every band degrades closed.
  A1.5 ONE ROW, TWO MOUNTS: the mirror and the composition import the same
      row; the mirror keeps its three verbs.
"""
from __future__ import annotations

import asyncio
import inspect
import re
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
REPO = Path(__file__).resolve().parents[1]
WEB = REPO / "web"

_passed = 0
_failed = 0
_failures: list[str] = []


def check(name: str, cond: bool, note: str = "") -> None:
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  ✓ {name}")
    else:
        _failed += 1
        _failures.append(name)
        print(f"  ✗ {name}{('  — ' + note) if note else ''}")


def _read(rel: str) -> str:
    p = REPO / rel
    return p.read_text() if p.exists() else ""


def _code_only_ts(src: str) -> str:
    """Strip TS comments — LINE comments first (a literal `/*` inside a line
    comment must not open a block that swallows the file — the ADR-656 lesson)."""
    src = re.sub(r"^\s*//.*$", "", src, flags=re.M)
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return src


# ═══════════════════════════════════════════════════════════════════════════
# The fake database — PostgREST-shaped, models Trash + the chain + the CAS
# ═══════════════════════════════════════════════════════════════════════════

class _Res:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self.filters: list = []
        self._order = None
        self._limit = None
        self._op = "select"
        self._payload = None
        self._on_conflict = None
        self.live_only = False

    # shape
    def select(self, *a, **k): return self
    def insert(self, row): self._op, self._payload = "insert", dict(row); return self
    def upsert(self, row, on_conflict=None, **k):
        self._op, self._payload, self._on_conflict = "upsert", dict(row), on_conflict; return self
    def update(self, data): self._op, self._payload = "update", dict(data); return self
    def delete(self): self._op = "delete"; return self
    # filters
    def eq(self, k, v): self.filters.append(("eq", k, v)); return self
    def neq(self, k, v): self.filters.append(("neq", k, v)); return self
    def in_(self, k, vs): self.filters.append(("in", k, list(vs))); return self
    def like(self, k, pat): self.filters.append(("like", k, pat)); return self
    def lte(self, k, v): self.filters.append(("lte", k, v)); return self
    def is_(self, k, v): self.filters.append(("is", k, v)); return self
    def or_(self, clause, *a, **k):
        if "lifecycle" in str(clause):
            self.live_only = True
        self.filters.append(("or", clause, None)); return self
    def order(self, col, desc=False, **k): self._order = (col, bool(desc)); return self
    def limit(self, n, **k): self._limit = n; return self

    def _match(self, r) -> bool:
        for op, k, v in self.filters:
            if op == "eq" and r.get(k) != v: return False
            if op == "neq" and r.get(k) == v: return False
            if op == "in" and r.get(k) not in v: return False
            if op == "lte" and not (r.get(k) is not None and r.get(k) <= v): return False
            if op == "is" and r.get(k) is not None: return False
            if op == "like":
                rx = "^" + re.escape(str(v)).replace("%", ".*") + "$"
                if not re.match(rx, str(r.get(k) or "")): return False
            if op == "or":
                ok = False
                for part in str(k).split(","):
                    col, cmp, val = part.split(".", 2)
                    cur = r.get(col)
                    if cmp == "is" and val == "null" and cur is None: ok = True
                    if cmp == "neq" and cur != val: ok = True
                    if cmp == "eq" and str(cur) == val: ok = True
                if not ok: return False
        return True

    def execute(self):
        rows = self.db.tables.setdefault(self.name, [])
        if self._op == "insert":
            row = self._payload
            row.setdefault("id", self.db.next_id())
            row.setdefault("created_at", self.db.next_ts())
            rows.append(row)
            return _Res([dict(row)])
        if self._op == "upsert":
            row = self._payload
            keys = [k.strip() for k in (self._on_conflict or "id").split(",")]
            for existing in rows:
                if all(existing.get(k) == row.get(k) for k in keys):
                    existing.update(row)
                    return _Res([dict(existing)])
            row.setdefault("id", self.db.next_id())
            row.setdefault("created_at", self.db.next_ts())
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
        # select
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

    def next_ts(self):
        self._seq += 1
        return f"2026-09-19T00:00:{self._seq % 60:02d}.{self._seq:06d}+00:00"

    def table(self, name):
        return _Query(self, name)

    # helpers
    def files(self, path):
        return [r for r in self.tables.get("workspace_files", []) if r.get("path") == path]

    def live_file(self, path):
        return [r for r in self.files(path) if (r.get("lifecycle") or "active") != "archived"]

    def versions(self, path):
        return [r for r in self.tables.get("workspace_file_versions", []) if r.get("path") == path]


U = "00000000-0000-4000-8000-00000000aaaa"
WS = "ws-0001"
db = FakeDB()
db.tables["workspaces"] = [{"id": WS, "owner_id": U, "timezone": "UTC"}]
db.tables["platform_connections"] = [
    {"user_id": U, "platform": "slack", "status": "active", "settings": {}, "connected_by": U,
     "landscape": {"selected_sources": [{"id": "C01", "name": "general"}, {"id": "C02", "name": "eng"}]}},
    {"user_id": U, "platform": "mcp:linear", "status": "active", "settings": {}, "landscape": {}},
    {"user_id": U, "platform": "wordpress", "status": "active", "settings": {}, "landscape": {}},
    {"user_id": U, "platform": "github", "status": "revoked", "settings": {}, "landscape": {}},
]
db.tables["execution_events"] = [
    {"user_id": U, "slug": "standing-sweep:team-brief", "status": "success", "error_reason": None,
     "created_at": "2026-09-18T09:00:00+00:00", "cost_usd": 0.0},
    {"user_id": U, "slug": "standing-write:team-brief", "status": "success", "error_reason": None,
     "created_at": "2026-09-18T09:00:05+00:00", "cost_usd": 0.02},
    {"user_id": U, "slug": "standing-write:other/topic", "status": "failed", "error_reason": "shape_violation",
     "created_at": "2026-09-18T09:00:06+00:00", "cost_usd": 0.01},
]

# ── patches: the scope resolvers, the access decider, the clock ──────────────
import services.workspace_context as _wc  # noqa: E402
import services.supabase as _sb  # noqa: E402
import services.access as _access  # noqa: E402
import services.schedule_utils as _su  # noqa: E402

_wc._current_workspace_id.set(WS)
_wc.acting_workspace_owner = lambda client, user_id, workspace_id=None: U
_sb.get_service_client = lambda: db
_access.resolve_access = lambda auth, path, verb: types.SimpleNamespace(allowed=True, reason="ok")
_su.get_workspace_timezone = lambda client, user_id, default="UTC": "UTC"

auth = types.SimpleNamespace(client=db, user_id=U, workspace_id=WS, caller_identity="operator")

import routes.standing_work as R  # noqa: E402
from services.standing_work import (  # noqa: E402
    DECLARATION_KEYS, DECLARATION_LEAF, CONTRACT_LEAF, discover_standing, parse_standing_yaml,
)
from services.agents_registry import AGENTS  # noqa: E402

loop = asyncio.new_event_loop()
run = loop.run_until_complete


def _status(exc):
    return getattr(exc, "status_code", None), getattr(exc, "detail", None)


def _problem(exc):
    d = getattr(exc, "detail", None)
    return d.get("problem") if isinstance(d, dict) else None


def _snapshot():
    return [dict(r) for r in db.tables.get("workspace_files", [])]


# ═══════════════════════════════════════════════════════════════════════════
print("D7. the starts are DERIVED from reach — connections that hold a capture binding")
# ═══════════════════════════════════════════════════════════════════════════
starts = run(R.list_standing_starts(auth))
kinds = [(s.kind, s.connector) for s in starts]
check("slack (active, bound) yields a start", ("connector", "slack") in kinds)
check("an attached MCP row yields NO start (reach for a turn, not a source for a run)",
      not any(c == "mcp:linear" for _, c in kinds))
check("an unbound platform (wordpress) yields NO start", not any(c == "wordpress" for _, c in kinds))
check("a revoked connection (github) yields NO start", not any(c == "github" for _, c in kinds))
check("the HTTP start is always offered, last", kinds[-1] == ("url", None))
_slack = next(s for s in starts if s.connector == "slack")
from services.connectors import CONNECTOR_CAPTURE_BINDINGS  # noqa: E402
check("the start carries the binding's OWN reads sentence, never a copy",
      _slack.reads == CONNECTOR_CAPTURE_BINDINGS["slack"]["reads"])
check("the start carries the selectors chosen at the aperture", _slack.selectors == ["C01", "C02"])
check("the start seeds a contract, a target and a schedule",
      bool(_slack.contract_seed) and _slack.suggested_target.endswith(".md") and bool(_slack.suggested_schedule))

# ═══════════════════════════════════════════════════════════════════════════
print("D4. the door refuses BY NAME and writes nothing on a refusal")
# ═══════════════════════════════════════════════════════════════════════════
_good = dict(folder="team-brief", target="brief.md", schedule="0 9 * * 1-5",
             contract="What moved in #general and #eng since the last update.",
             sources=[{"id": "general", "connector": "slack", "selector": "C01"}])

def _try_create(**over):
    body = dict(_good); body.update(over)
    before = _snapshot()
    try:
        res = run(R.create_standing(R.CreateStandingRequest(**body), auth))
        return res, None, before == _snapshot()
    except Exception as exc:  # noqa: BLE001
        return None, exc, before == _snapshot()

_, exc, untouched = _try_create(contract="   ")
check("a blank contract is refused as `missing_contract`", _problem(exc) == "missing_contract", str(_status(exc)))
check("…and nothing is written", untouched)
_, exc, untouched = _try_create(target="deck.pptx")
check("a deck target is refused BY NAME as `unsupported_format` (ADR-569 D1)", _problem(exc) == "unsupported_format")
check("…and nothing is written", untouched)
_, exc, untouched = _try_create(sources=[])
check("no sources is refused as `sources_invalid`", _problem(exc) == "sources_invalid")
_, exc, untouched = _try_create(app="editor")
check("an AGENT slug in `app` is refused as `app_invalid` — never honoured, never parked",
      _problem(exc) == "app_invalid")
check("…and nothing is written", untouched)
_, exc, _ = _try_create(folder="system/skills")
check("a folder under system/ is refused", _status(exc)[0] == 422)

# ═══════════════════════════════════════════════════════════════════════════
print("D4. the door lands both files through the ONE composer + the ONE write path")
# ═══════════════════════════════════════════════════════════════════════════
created, exc, _ = _try_create()
check("a valid declaration is created", created is not None and created.topic == "team-brief", repr(exc))
if created is None:
    # The door is broken; every check below would crash on it. Report the
    # count rather than nothing (a gate that crashes reports nothing).
    print("\n" + "=" * 70); print(f"  {_passed} passed, {_failed} failed  (aborted: the door refused a valid declaration)"); sys.exit(1)
decl_path = f"/workspace/team-brief/{DECLARATION_LEAF}"
contract_path = f"/workspace/team-brief/{CONTRACT_LEAF}"
check("_standing.yaml is a LIVE row", len(db.live_file(decl_path)) == 1)
check("CONTRACT.md is a LIVE row carrying the member's words",
      len(db.live_file(contract_path)) == 1 and _good["contract"] in db.live_file(contract_path)[0]["content"])
_yaml_body = db.live_file(decl_path)[0]["content"]
check("the body is what compose_standing_yaml emits (one composer)",
      _yaml_body == R.compose_standing_yaml(target="brief.md", schedule="0 9 * * 1-5", paused=False,
                                            sources=_good["sources"], fire_on_activation=True))
_parsed = parse_standing_yaml(_yaml_body, topic="team-brief", declaration_path=decl_path, user_id=U)
check("the one parser accepts it with no problem", _parsed is not None and _parsed.problem is None)
check("the app DERIVES from the target's type (md → text) — nothing stored named it",
      _parsed.app == "text" and "app:" not in _yaml_body)
check("the first run is ARMED on creation (fire_on_activation, consumed on first update)",
      _parsed.options.get("fire_on_activation") is True)
_rows = db.tables.get("tasks", [])
_task = next((r for r in _rows if r.get("slug") == "standing:team-brief"), None)
check("the index carries the row NOW (materialized on write), armed",
      _task is not None and bool(_task.get("next_run_at")))
check("both revisions are attributed and messaged (ADR-209)",
      all(v.get("authored_by") == "operator" and v.get("message") for v in db.versions(decl_path) + db.versions(contract_path)))

# ═══════════════════════════════════════════════════════════════════════════
print("D2. the minder is DERIVED and DISPLAYED, never stored")
# ═══════════════════════════════════════════════════════════════════════════
import yaml as _yaml  # noqa: E402
_keys = set(_yaml.safe_load(_yaml_body).keys())
check("the YAML's keys are the parser's whitelist (+ the consume-once arm flag)",
      _keys <= (DECLARATION_KEYS | {"fire_on_activation"}), str(_keys))
for _slug in AGENTS:
    check(f"no key or value in the written YAML names the agent {_slug!r}",
          not re.search(rf"\b{_slug}\b", _yaml_body))
    check(f"the index row names no agent {_slug!r}",
          not any(_slug in str(v) for v in (_task or {}).values()))
check("the summary says who minds it — Editor, derived from text's executor",
      created is not None and created.minder is not None and created.minder.slug == "editor")

import services.authoring as _authoring  # noqa: E402
_orig_exec = _authoring.standing_executor_for_app
_authoring.standing_executor_for_app = lambda slug: "designer"
try:
    _again = run(R.get_standing("team-brief", auth))
    check("FALSIFIED: swap the derivation and the displayed minder changes (nothing stored held it)",
          _again.summary.minder is not None and _again.summary.minder.slug == "designer")
finally:
    _authoring.standing_executor_for_app = _orig_exec
check("…restored: Editor again", run(R.get_standing("team-brief", auth)).summary.minder.slug == "editor")

# ═══════════════════════════════════════════════════════════════════════════
print("D4. one declaration per folder")
# ═══════════════════════════════════════════════════════════════════════════
_, exc, untouched = _try_create()
check("a second declaration in the same folder is refused as `already_declared` (409)",
      _problem(exc) == "already_declared" and _status(exc)[0] == 409)
check("…and nothing is written", untouched)

# ═══════════════════════════════════════════════════════════════════════════
print("D6. the detail: the instructions, the runs for exactly this topic, the switches")
# ═══════════════════════════════════════════════════════════════════════════
detail = run(R.get_standing("team-brief", auth))
check("the detail serves the instructions text", (detail.contract or "").strip() == _good["contract"])
check("the detail's runs are THIS topic's ledger rows, newest first, other topics excluded",
      [r.step for r in detail.runs] == ["write", "sweep"] and all(r.error_reason != "shape_violation" for r in detail.runs))
check("the detail names the contract path", detail.contract_path == contract_path)

_before = db.live_file(decl_path)[0]["content"]
_res = run(R.update_standing("team-brief", R.UpdateStandingRequest(schedule="0 8 * * 1"), auth))
_after = db.live_file(decl_path)[0]["content"]
check("PATCH schedule rewrites through the composer", _res.schedule == "0 8 * * 1" and "0 8 * * 1" in _after)
check("the arm flag is CONSUMED on the first update (never re-emitted)", "fire_on_activation" not in _after)
_before = db.live_file(decl_path)[0]["content"]
try:
    run(R.update_standing("team-brief", R.UpdateStandingRequest(target="poster.png"), auth))
    _exc = None
except Exception as e:  # noqa: BLE001
    _exc = e
check("PATCH to an unsupported target is refused BY NAME", _problem(_exc) == "unsupported_format")
check("…and the declaration is byte-identical after the refusal", db.live_file(decl_path)[0]["content"] == _before)

# a declaration already in a problem state may still be paused
from services.authored_substrate import write_revision  # noqa: E402
_broken_path = f"/workspace/broken/{DECLARATION_LEAF}"
write_revision(db, user_id=U, path=_broken_path, content="target: slides.pptx\nschedule: '0 9 * * *'\npaused: false\nsources: []\n",
               authored_by="operator", message="seed a broken one", workspace_id=WS, lifecycle="active")
_res = run(R.update_standing("broken", R.UpdateStandingRequest(paused=True), auth))
check("the pause switch alone is never refused, even on a problem declaration",
      _res.paused is True and _res.problem == "unsupported_format")

# ═══════════════════════════════════════════════════════════════════════════
print("§6.2. retire archives the declaration ONLY — the file and its instructions stay")
# ═══════════════════════════════════════════════════════════════════════════
target_path = "/workspace/team-brief/brief.md"
write_revision(db, user_id=U, path=target_path, content="# Brief\n\nfirst\n", authored_by="operator",
               message="the member's own draft", workspace_id=WS)
write_revision(db, user_id=U, path=target_path, content="# Brief\n\nsecond\n", authored_by="system:standing",
               message="kept 'brief.md' current (standing run, 1 sources)", workspace_id=WS,
               revision_kind="derivation")
_target_chain = len(db.versions(target_path))
_contract_chain = len(db.versions(contract_path))
_decl_chain = len(db.versions(decl_path))
out = run(R.retire_standing("team-brief", auth))
check("retire succeeds and names what it kept", out.get("success") and target_path in out.get("kept", []) and contract_path in out.get("kept", []))
check("the declaration is in TRASH (archived), not removed — restorable, attributed",
      db.files(decl_path) and db.files(decl_path)[0].get("lifecycle") == "archived"
      and db.versions(decl_path)[-1].get("message", "").startswith("retire"))
check("the kept file is UNTOUCHED — live, its chain intact",
      len(db.live_file(target_path)) == 1 and len(db.versions(target_path)) == _target_chain
      and db.live_file(target_path)[0]["content"].endswith("second\n"))
check("the instructions are UNTOUCHED — live, chain intact",
      len(db.live_file(contract_path)) == 1 and len(db.versions(contract_path)) == _contract_chain)
check("the index dropped the row NOW", not any(r.get("slug") == "standing:team-brief" for r in db.tables.get("tasks", [])))
check("the roster no longer lists it", all(s.topic != "team-brief" for s in run(R.list_standing(auth))))
for verb, call in (("detail", lambda: run(R.get_standing("team-brief", auth))),
                   ("PATCH", lambda: run(R.update_standing("team-brief", R.UpdateStandingRequest(paused=True), auth))),
                   ("run now", lambda: run(R.run_standing_now("team-brief", auth)))):
    try:
        call(); _code = 200
    except Exception as e:  # noqa: BLE001
        _code = _status(e)[0]
    check(f"a retired declaration answers 404 to {verb} (the live filter at every door)", _code == 404)

# ═══════════════════════════════════════════════════════════════════════════
print("A1.6. THE TOMBSTONE DRIVE — create → retire → create the same folder")
# ═══════════════════════════════════════════════════════════════════════════
revived, exc, _ = _try_create(contract="Second life: the same folder, declared again.")
check("re-creating the retired folder succeeds (not `already_declared`, not a burned name)",
      revived is not None and revived.topic == "team-brief", repr(exc))
_live_contract = db.live_file(contract_path) or [{"content": ""}]
check("the declaration row is LIVE again — never left in Trash",
      db.files(decl_path) and (db.files(decl_path)[0].get("lifecycle") or "active") == "active")
check("discovery finds it (the drain would run it)",
      any(d.topic == "team-brief" for d in discover_standing(db, workspace_id=WS).get(U, [])))
check("the index carries the row again", any(r.get("slug") == "standing:team-brief" for r in db.tables.get("tasks", [])))
check("the revision chain is the record: retire + re-create are two more revisions of the same path",
      len(db.versions(decl_path)) == _decl_chain + 2, f"{_decl_chain} → {len(db.versions(decl_path))}")
check("the new instructions replaced the old as a new revision, chain intact",
      _live_contract[0]["content"].startswith("Second life") and len(db.versions(contract_path)) == _contract_chain + 1)

# ═══════════════════════════════════════════════════════════════════════════
print("A1.8. Run now against a row the drain is holding — the honest no-op, driven")
# ═══════════════════════════════════════════════════════════════════════════
import services.standing_work as _sw  # noqa: E402
from datetime import datetime as _dt, timedelta as _td, timezone as _tzz  # noqa: E402
_calls: list = []
_orig_sweep = _sw.run_standing_sweep
async def _spy(client, user_id, decl):
    _calls.append(decl.slug); return {"success": True, "slug": decl.slug, "no_change": True}
_sw.run_standing_sweep = _spy
try:
    _task_row = next(r for r in db.tables["tasks"] if r["slug"] == "standing:team-brief")
    _armed = _task_row.get("next_run_at")
    # (i) a row the drain holds: next_run_at = a sentinel the schedule could not have produced
    _task_row["next_run_at"] = (_dt.now(_tzz.utc) + _td(hours=2)).isoformat()
    _out = run(R.run_standing_now("team-brief", auth))
    check("a manual Run now against a drain-held row is the honest no-op (never a second run)",
          _out.get("no_change") is True and _calls == [], str(_out))
    check("…and the sentinel is left for the drain to clear", _task_row["next_run_at"] != _armed)
    # (ii) the ordinary armed row (the schedule's own boundary) still runs by hand
    _task_row["next_run_at"] = _armed
    _out = run(R.run_standing_now("team-brief", auth))
    check("Run now against the ordinary armed row proceeds (table stakes)", _calls == ["standing:team-brief"], str(_out))
    # (iii) a due (past) commitment is claimable too
    _task_row["next_run_at"] = (_dt.now(_tzz.utc) - _td(minutes=5)).isoformat()
    run(R.run_standing_now("team-brief", auth))
    check("Run now against a due row proceeds", len(_calls) == 2)
finally:
    _sw.run_standing_sweep = _orig_sweep
R.run_standing_sweep = _orig_sweep if hasattr(R, "run_standing_sweep") else None

# ═══════════════════════════════════════════════════════════════════════════
print("HTTP. the routes over real transport — ordering and the by-name refusal body")
# ═══════════════════════════════════════════════════════════════════════════
import typing  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
_app = FastAPI()
_app.include_router(R.router, prefix="/api")
_args = typing.get_args(R.UserClient)
_app.dependency_overrides[_args[1].dependency] = lambda: auth
_c = TestClient(_app)
_r = _c.get("/api/standing/starts")
check("GET /api/standing/starts is NOT swallowed by /standing/{topic} (declared first)",
      _r.status_code == 200 and isinstance(_r.json(), list) and _r.json()[-1]["kind"] == "url", str(_r.status_code))
_r = _c.post("/api/standing", json=dict(_good, folder="http-test", target="poster.png"))
check("POST refusal rides `detail.problem` by name over HTTP", _r.status_code == 422 and _r.json()["detail"]["problem"] == "unsupported_format")
_r = _c.get("/api/standing/team-brief")
_body = _r.json() if _r.status_code == 200 and isinstance(_r.json(), dict) else {}
check("GET /api/standing/{topic} serves the detail shape (summary · contract · runs)",
      _r.status_code == 200 and {"summary", "contract", "runs", "contract_path"} <= set(_body.keys()), str(_r.status_code))
check("the served summary carries the DERIVED minder", ((_body.get("summary") or {}).get("minder") or {}).get("slug") == "editor")
_r = _c.delete("/api/standing/http-test")
check("DELETE on an undeclared folder is 404", _r.status_code == 404)

# ═══════════════════════════════════════════════════════════════════════════
print("D4. both authoring paths emit what the ONE parser accepts")
# ═══════════════════════════════════════════════════════════════════════════
_skill = _read("api/services/skills/declaring-standing-work/SKILL.md")
_m = re.search(r"\n {7}target:.*?(?=\n\n)", _skill, re.S)
_block = "\n".join(l[7:] if l.startswith("       ") else l for l in (_m.group(0).strip("\n").splitlines() if _m else []))
_block = re.sub(r"\s+#.*$", "", _block, flags=re.M)
_block = "\n".join(l for l in _block.splitlines() if l.strip())
_sk = parse_standing_yaml(_block, topic="x", declaration_path="/workspace/x/_standing.yaml", user_id=U)
check("the skill's YAML example parses through the one parser with no problem",
      _sk is not None and _sk.problem is None, str(_sk.problem if _sk else "unparseable") + "\n" + _block)
check("the composer takes no key the parser does not name (no `assignee`, no agent field)",
      set(inspect.signature(R.compose_standing_yaml).parameters) - {"fire_on_activation", "paused"} <= DECLARATION_KEYS)
_foreign = parse_standing_yaml("target: a.md\nschedule: daily\nsources:\n  - id: s\n    url: https://x.y\nassignee: editor\n",
                               topic="x", declaration_path="/workspace/x/_standing.yaml", user_id=U)
check("a foreign key (`assignee: editor`) is parked as inert residue, never read as authority",
      _foreign is not None and "assignee" in _foreign.options and "assignee" not in DECLARATION_KEYS)

# ═══════════════════════════════════════════════════════════════════════════
print("D5. `threads` is gone; the composed bands degrade closed and independently")
# ═══════════════════════════════════════════════════════════════════════════
import services.supervisor_state as _ss  # noqa: E402
check("supervisor_state has no _threads and no THREAD_CAP",
      not hasattr(_ss, "_threads") and not hasattr(_ss, "THREAD_CAP"))
check("the module's docstring no longer lists threads as a band",
      "threads    →" not in (_ss.__doc__ or ""))
write_revision(db, user_id=U, path=_ss.DECISIONS_PATH, content="# Decided\n\n- ship it\n", authored_by="operator",
               message="a decision", workspace_id=WS)
import services.mentions as _mentions  # noqa: E402
_orig_lm = _mentions.list_mentions
_mentions.list_mentions = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("mentions down"))
try:
    _state = _ss.supervisor_state(db, U, WS)
finally:
    _mentions.list_mentions = _orig_lm
check("the payload is exactly {needs_you, note}", set(_state.keys()) == {"needs_you", "note"})
check("a dead mentions read degrades to an EMPTY band, and the note band still renders",
      _state["needs_you"] == [] and (_state["note"] or {}).get("content", "").startswith("# Decided"))

# ═══════════════════════════════════════════════════════════════════════════
print("FE. the surface: work · needs-you · note, one row two mounts, the door, the copy")
# ═══════════════════════════════════════════════════════════════════════════
_sec = _code_only_ts(_read("web/components/supervisor/SupervisorSection.tsx"))
for _kind in ("work", "needs-you", "note"):
    check(f"the client draws {_kind!r}", f"case '{_kind}':" in _sec)
check("the client no longer draws `threads`", "case 'threads':" not in _sec and "ThreadsSection" not in _sec)
_default = _sec[_sec.index("default:"):] if "default:" in _sec else ""
_default = _default[: _default.index("}")] if "}" in _default else _default
check("an unknown kind still renders the honest miss", "<SectionMiss" in _default and "return null" not in _default)
check("the resting copy reassures; `No items` never appears",
      "Nothing is waiting on you." in _sec and "No items" not in _sec)
check("the work band's empty state names the next step, not an absence",
      "Nothing runs on its own yet." in _sec)
check("with nothing connected, the empty state points at Reach", "Reach" in _sec)

_surf = _code_only_ts(_read("web/components/supervisor/SupervisorSurface.tsx"))
_order = re.findall(r"kind:\s*'([a-z-]+)'", _surf)
check("the declared sections are work · needs-you · note, in that order",
      _order == ["work", "needs-you", "note"], str(_order))
check("the surface renders DECLARED sections", "SECTIONS.map" in _surf)
check("the work band reads the ONE roster route (api.standing.list), not a second composition",
      "api.standing.list(" in _surf or "api.standing.list(" in _sec)
check("the surface reads the starts", "api.standing.starts(" in _surf or "api.standing.starts(" in _sec)
check("opening a mention still navigates to chat", "navigateToSurface('chat'" in _surf)
# ⚠️ Driven 2026-09-19: the surface showed "Loading… still working" at 6s while
# the mentions read was slow — the work band, the app's reason, sat behind a
# spinner it did not need. The bands LOAD independently, not only degrade.
check("the surface never gates every band on the composed-state read alone",
      "if (!data && !failed) return <Working" not in _surf and "rows === null" in _surf)
check("the three reads ARRIVE independently — never awaited together (a 23s mentions read held the roster)",
      "Promise.allSettled" not in _surf and "Promise.all(" not in _surf
      and all(f"{c}.then(" in _surf.replace("\n", "").replace(" ", "") for c in ("api.supervisor.state()", "api.standing.list()", "api.standing.starts()")))
check("an opened detail is never held behind the bands' wait", "if (!openTopic && " in _surf)
check("no diagnostic logging shipped", "[DIAG]" not in _read("web/components/supervisor/SupervisorSurface.tsx") + _read("web/components/supervisor/StandingDetail.tsx"))
check("a band whose read is still out says so itself", _sec.count("Loading…") >= 2)

_row = _code_only_ts(_read("web/components/standing/StandingRow.tsx"))
check("the shared row exists", bool(_row) and "export function StandingRow" in _row)
_mirror = _code_only_ts(_read("web/components/notifications/StandingWork.tsx"))
_ROW_IMPORT = re.compile(r"import \{[^}]*\bStandingRow\b[^}]*\} from '@/components/standing/StandingRow';")
check("the MIRROR mounts the shared row (the exact import, and a render)",
      _ROW_IMPORT.search(_mirror) is not None and "<StandingRow" in _mirror)
check("the COMPOSITION mounts the shared row (the exact import, and a render)",
      _ROW_IMPORT.search(_sec) is not None and "<StandingRow" in _sec)
check("the mirror keeps its three verbs (ADR-639 D4)",
      all(w in _mirror for w in ("api.standing.list", "api.standing.run", "api.standing.update")))
check("the mirror's empty state names the Supervisor as where standing work is set up", "Supervisor" in _mirror)
check("the row shows who minds it (the derived minder)", "minder" in _row and "looks after this" in _row)
check("the row's repair copy names no kernel noun", "declaration" not in _row.lower())

_door = _code_only_ts(_read("web/components/supervisor/NewStandingWorkModal.tsx"))
check("the door exists", "export function NewStandingWorkModal" in _door)
_textareas = re.findall(r"<textarea\b[^>]*?(?:/>|>)", _door, flags=re.S)
check("the door renders a REAL instructions box — a <textarea> that is not hidden",
      any("hidden" not in t for t in _textareas), str(_textareas)[:200])
check("the door posts through the create door", "api.standing.create(" in _door)
check("the door offers a folder picker (the one tree picker)", "WorkspacePickerModal" in _door)
check("the door says the first run starts soon", "first" in _door.lower() and "minutes" in _door.lower())

_detail = _code_only_ts(_read("web/components/supervisor/StandingDetail.tsx"))
check("the detail exists", "export function StandingDetail" in _detail)
check("the detail reads the detail route", "api.standing.get(" in _detail)
check("the detail can retire, and its confirm says the file stays",
      "api.standing.retire(" in _detail and "stay" in _detail)
check("the detail edits the instructions as the FILE they are (editFile), never a second door",
      "api.workspace.editFile(" in _detail)
check("the detail can pause and run now", "api.standing.update(" in _detail and "api.standing.run(" in _detail)

_client = _code_only_ts(_read("web/lib/api/client.ts"))
for _verb in ("create", "get", "retire", "starts"):
    check(f"the api client carries standing.{_verb}", re.search(rf"\n\s+{_verb}: \(", _client[_client.index("standing: {"):]) is not None)
check("the stale `no create route` comment is gone", "no create route" not in _read("web/lib/api/client.ts"))
check("StandingSummary carries the derived minder", "minder?:" in _client)
check("the supervisor state type no longer carries threads",
      "threads: Array" not in _client[_client.index("supervisor: {"):_client.index("supervisor: {") + 1200])

# =============================================================================
print("\n" + "=" * 70)
print(f"  {_passed} passed, {_failed} failed")
print("=" * 70)
if _failed:
    print("✗ check(s) failed:", _failures)
    sys.exit(1)
print("✓ all ADR-658 checks passed")
