"""ADR-582 gate — the connector is a WRITER, not a pipeline.

Holds the re-cut's contract:
  §1 one selection store (the mirror stays deleted; every consumer reads it)
  §2 placement — destination flexible at wiring, deterministic at write
  §3 the capture walk DRIVEN — attribution, kind, diff-awareness, no embed
  §4 the digest is OPT-IN (no LLM on the connect path)
  §5 wiring — the walk runs inside the dormancy flag, before the digest
  §6 apps consume LANDED files (Strings' connector source, driven)

Script-style (python3, from api/). Every non-trivial check was falsified
against a broken shape before being trusted (ADR-582 §4).
"""

from __future__ import annotations

import ast
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = Path(__file__).resolve().parent
sys.path.insert(0, str(API))

PASS = 0
FAIL = 0


def check(label: str, ok, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}" + (f" — {detail}" if detail else ""))


def _code_only(path: Path) -> str:
    src = path.read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                body[0].value.value = ""
    return ast.unparse(tree)


def _calls_in(node) -> set:
    names = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                names.add(f.id)
            elif isinstance(f, ast.Attribute):
                names.add(f.attr)
    return names


# ═════════════════════════════════════════════════════════════════════════════
print("§1 one selection store — the mirror stays deleted")
# ═════════════════════════════════════════════════════════════════════════════

check("1a connector_watch.py stays deleted",
      not (API / "services" / "connector_watch.py").exists())
check("1b capture_connector.py stays deleted",
      not (API / "services" / "primitives" / "capture_connector.py").exists())

from services.connectors import (  # noqa: E402
    CONNECTOR_CAPTURE_BINDINGS,
    capture_destination,
    connector_settings,
    selected_ids_from_row,
    snapshot_path,
)

row = {"platform": "slack", "landscape": {"selected_sources": [
    {"id": "C001"}, {"id": "C003"}, {"id": ""}]}, "settings": {}}
check("1c selection reads from landscape.selected_sources (no-id dropped)",
      selected_ids_from_row(row) == ["C001", "C003"])

s = connector_settings(row)
check("1d settings default: platform-binding cadence · default destination · "
      "digest OFF",
      s["cadence"] == CONNECTOR_CAPTURE_BINDINGS["slack"]["cadence"]
      and s["destination"] is None and s["digest"] is False, str(s))


# ═════════════════════════════════════════════════════════════════════════════
print("§2 placement — flexible at wiring, deterministic at write")
# ═════════════════════════════════════════════════════════════════════════════

check("2a default destination follows the intake grammar",
      capture_destination("slack", "C0A6P2WS4HL", {}) == "inbound/slack/c0a6p2ws4hl")
check("2b operator destination is honored, filing stays per-selector",
      capture_destination("slack", "C001", {"destination": "Projects/Acme/slack"})
      == "Projects/Acme/slack/c001")
check("2c a slash-bearing selector stays ONE segment",
      capture_destination("github", "Kvk/yarnnnn", {}).count("/") == 2)
check("2d the snapshot filename is the stamp",
      snapshot_path("slack", "C001", "2026-08-19T00:00:00Z", {})
      == "inbound/slack/c001/2026-08-19T00:00:00Z.md")


# ═════════════════════════════════════════════════════════════════════════════
print("§3 the capture walk — DRIVEN")
# ═════════════════════════════════════════════════════════════════════════════

captured_writes: list = []


class _FakeUM:
    def __init__(self, client, uid):
        pass

    async def list(self, sub):
        return []

    async def read(self, rel):
        return None

    async def write(self, path, content, **kw):
        captured_writes.append({"path": path, "content": content, **kw})
        return True


async def _fake_tool(auth, tool, args):
    return {"success": True, "result": {"messages": [{"t": "hi"}], "args": args}}


def _drive_capture(row):
    import services.workspace as ws
    import services.platform_tools as pt
    from services.connectors import run_connector_capture

    orig = (ws.UserMemory, pt.handle_platform_tool)
    ws.UserMemory = _FakeUM
    pt.handle_platform_tool = _fake_tool
    try:
        return asyncio.get_event_loop().run_until_complete(
            run_connector_capture(None, "u1", row,
                                  observed_at="2026-08-19T01:00:00Z")
        )
    finally:
        ws.UserMemory, pt.handle_platform_tool = orig


captured_writes.clear()
res = _drive_capture({"platform": "slack", "settings": {},
                      "landscape": {"selected_sources": [{"id": "C001"}]}})
check("3a the walk succeeds and lands one snapshot per selected slice",
      res.get("success") and len(captured_writes) == 1, str(res))
w = captured_writes[0] if captured_writes else {}
check("3b the snapshot lands at the default destination with the stamp",
      w.get("path") == "inbound/slack/c001/2026-08-19T01:00:00Z.md",
      str(w.get("path")))
check("3c attributed to the MECHANISM — system:capture-{platform}",
      w.get("authored_by") == "system:capture-slack", str(w.get("authored_by")))
check("3d the write is an OBSERVATION on the ledger (the ADR-423 key — "
      "visibility follows revision_kind, never the path)",
      w.get("revision_kind") == "observation")

captured_writes.clear()
res2 = _drive_capture({"platform": "slack",
                       "settings": {"connector": {"destination": "Projects/Acme/slack"}},
                       "landscape": {"selected_sources": [{"id": "C001"}]}})
check("3e an operator destination re-homes the snapshot",
      captured_writes
      and captured_writes[0]["path"].startswith("Projects/Acme/slack/c001/"),
      str([w.get("path") for w in captured_writes]))

check("3f nothing selected → nothing captured, honestly",
      _drive_capture({"platform": "slack", "settings": {}, "landscape": {}})
      .get("skipped") == "nothing_selected")

# The writer must never rank raw into recall — no embed call anywhere in it.
conn_code = _code_only(API / "services" / "connectors.py")
check("3g the writer never embeds (raw is keyed, not ranked — wherever it lands)",
      "embed" not in conn_code.lower())

from services.connectors import _cadence_due  # noqa: E402
NOW = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)
check("3h cadence: never captured → due", _cadence_due({}, NOW))
check("3i cadence: inside the interval → not due",
      not _cadence_due({"cadence": "@every 1h",
                        "last_capture_at": (NOW - timedelta(minutes=10)).isoformat()}, NOW))
check("3j cadence: past the interval → due",
      _cadence_due({"cadence": "@every 1h",
                    "last_capture_at": (NOW - timedelta(hours=2)).isoformat()}, NOW))


# ═════════════════════════════════════════════════════════════════════════════
print("§4 the digest is OPT-IN — no LLM on the connect path")
# ═════════════════════════════════════════════════════════════════════════════

# DRIVEN, not grepped (a co-occurrence check here passed its own falsifier's
# gutting — "digest" matched digest_path calls): run the real drain over one
# connection each way and count the derives attempted.


def _drive_digest_drain(digest_on: bool) -> int:
    import services.connector_derive as cd

    class _Q:
        def __init__(self, data):
            self._d = data

        def __getattr__(self, name):
            return lambda *a, **k: self

        def execute(self):
            from types import SimpleNamespace
            return SimpleNamespace(data=self._d)

    class _C:
        def table(self, name):
            return _Q([{
                "user_id": "u1", "platform": "slack", "connected_by": "u1",
                "landscape": {"selected_sources": [{"id": "C001"}]},
                "settings": {"connector": {"digest": digest_on}},
            }])

    attempts = []

    async def _fake_run(*a, **k):
        attempts.append(1)
        return {"success": True}

    async def _fake_fresh(*a, **k):
        return [("inbound/slack/c001/2026-08-19T01:00:00Z.md",
                 datetime(2026, 8, 19, 1, 0, tzinfo=timezone.utc))]

    import services.workspace as ws
    orig = (cd.run_connector_derive, cd._fresh_raw, cd._last_derive_at, ws.UserMemory)
    cd.run_connector_derive = _fake_run
    cd._fresh_raw = _fake_fresh
    cd._last_derive_at = lambda *a, **k: None
    ws.UserMemory = lambda c, u: object()
    try:
        asyncio.get_event_loop().run_until_complete(
            cd.drain_due_connector_derives(_C()))
    finally:
        cd.run_connector_derive, cd._fresh_raw, cd._last_derive_at, ws.UserMemory = orig
    return len(attempts)


check("4a digest OFF → the drain derives NOTHING (the D5 opt-in, driven)",
      _drive_digest_drain(False) == 0)
check("4a2 digest ON → the drain derives (the gate is a gate, not a wall)",
      _drive_digest_drain(True) == 1)
check("4b the capture walk never calls the derive (decoupled consumers)",
      "run_connector_derive" not in _calls_in(ast.parse(conn_code))
      and "drain_due_connector_derives" not in conn_code)


# ═════════════════════════════════════════════════════════════════════════════
print("§5 wiring — inside the flag, walk before digest")
# ═════════════════════════════════════════════════════════════════════════════

sched_src = (API / "jobs" / "unified_scheduler.py").read_text()
sched_tree = ast.parse(sched_src)
walk_gated = digest_gated = False
for n in ast.walk(sched_tree):
    if isinstance(n, ast.If):
        test_names = {x.id for x in ast.walk(n.test) if isinstance(x, ast.Name)}
        if "capture_lane_on" in test_names:
            calls = _calls_in(n)
            if "drain_due_connector_captures" in calls:
                walk_gated = True
            if "drain_due_connector_derives" in calls:
                digest_gated = True
check("5a the capture walk runs inside the dormancy flag", walk_gated)
check("5b the digest drain stays inside the flag too", digest_gated)
check("5c the walk runs BEFORE the digest (a digest can read this tick's raw)",
      sched_src.index("drain_due_connector_captures")
      < sched_src.index("drain_due_connector_derives"))
check("5d no seeding exists anywhere in the routes",
      "seed_connector_capture" not in (API / "routes" / "integrations.py").read_text())


# ═════════════════════════════════════════════════════════════════════════════
print("§6 apps consume LANDED files — Strings' connector source, driven")
# ═════════════════════════════════════════════════════════════════════════════

from services.strings import _classify_sources, _is_connector_source  # noqa: E402

check("6a a connector source form is valid",
      _classify_sources([{"id": "standup", "connector": "slack",
                          "selector": "C001"}], "md") is None)
check("6b a source with neither url nor connector is still refused",
      _classify_sources([{"id": "x"}], "md") == "sources_invalid")
check("6c the connector-source predicate needs BOTH platform and selector",
      not _is_connector_source({"connector": "slack"})
      and not _is_connector_source({"selector": "C1"}))


def _drive_string_source():
    import services.workspace as ws
    import services.connectors as cn
    from services.strings import _read_connector_source

    class _UM:
        def __init__(self, client, uid):
            pass

        async def list(self, sub):
            assert sub == "inbound/slack/c001/", f"unexpected sub={sub}"
            return ["2026-08-19T01:00:00Z.md"]

        async def read(self, rel):
            return "landed snapshot body"

    orig_um = ws.UserMemory
    orig_row = cn.connection_row
    ws.UserMemory = _UM
    cn.connection_row = lambda client, uid, plat: {"platform": plat, "settings": {}}
    try:
        return asyncio.get_event_loop().run_until_complete(
            _read_connector_source(None, "u1", "slack", "C001")
        )
    finally:
        ws.UserMemory = orig_um
        cn.connection_row = orig_row


body, cited = _drive_string_source()
check("6d the source resolves the LANDED snapshot (substrate, no HTTP, no API)",
      body == "landed snapshot body", str(body))
check("6e the string cites the landed path as its raw (no re-retain)",
      cited == "/workspace/inbound/slack/c001/2026-08-19T01:00:00Z.md", str(cited))

# The connector branch must never reach httpx or a platform tool.
strings_src = _code_only(API / "services" / "strings.py")
strings_tree = ast.parse(strings_src)
rcs = next(n for n in ast.walk(strings_tree)
           if isinstance(n, ast.AsyncFunctionDef) and n.name == "_read_connector_source")
check("6f the connector source path calls no platform API and no HTTP",
      "handle_platform_tool" not in _calls_in(rcs)
      and "httpx" not in ast.unparse(rcs))

n = PASS + FAIL
print(f"\n{PASS}/{n} ADR-582 assertions pass")
sys.exit(0 if FAIL == 0 else 1)
