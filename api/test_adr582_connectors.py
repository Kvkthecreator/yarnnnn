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
check("1d settings default: the default destination lane (ADR-591 retired "
      "cadence + digest with the walker)",
      s["destination"] is None and "cadence" not in s and "digest" not in s,
      str(s))


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

# ADR-591: cadence is retired. The clock, its law, and the walker that read
# it are all deleted — a connector has no "how often".
import services.connectors as _conn_mod  # noqa: E402

check("3h the cadence law is DELETED (no clock to compare against)",
      not hasattr(_conn_mod, "_cadence_due"))
check("3i the cadence enum + seconds map are DELETED",
      not hasattr(_conn_mod, "CONNECTOR_CADENCE_CHOICES")
      and not hasattr(_conn_mod, "_CADENCE_SECONDS"))
check("3j no per-platform binding carries a cadence (the walker's defaults)",
      all("cadence" not in b for b in CONNECTOR_CAPTURE_BINDINGS.values()),
      str({k: sorted(v) for k, v in CONNECTOR_CAPTURE_BINDINGS.items()}))


# ═════════════════════════════════════════════════════════════════════════════
print("§4 the digest is OPT-IN — no LLM on the connect path")
# ═════════════════════════════════════════════════════════════════════════════

# DRIVEN, not grepped (a co-occurrence check here passed its own falsifier's
# gutting — "digest" matched digest_path calls): run the real drain over one
# connection each way and count the derives attempted.


# ADR-582 D5's opt-in was a per-connection dial on a WALKER. ADR-591 deleted
# the walker, so the guarantee is now structural rather than conditional:
# nothing on a tick can invoke the deriver, so connecting cannot cost a
# member anything. Driven where a drive is still possible; asserted on the
# module surface where the thing that could have driven it is gone.
import services.connector_derive as cd  # noqa: E402

check("4a no clock can invoke the deriver — the walker is DELETED "
      "(connecting costs $0 by construction, not by a dial)",
      not hasattr(cd, "drain_due_connector_derives"))
check("4a2 the derive WRITER survives and stays invocable (D3.a — a "
      "consumer calls it; only its clock died)",
      callable(getattr(cd, "run_connector_derive", None)))
check("4a3 the spend guard survives the walker (a caller in a loop is "
      "exactly what is_due exists to refuse — ADR-401 D5)",
      callable(getattr(cd, "is_due", None))
      and cd.is_due(None, None, datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)) is False)
check("4b the capture walk never calls the derive (decoupled consumers)",
      "run_connector_derive" not in _calls_in(ast.parse(conn_code))
      and "drain_due_connector_derives" not in conn_code)


# ═════════════════════════════════════════════════════════════════════════════
print("§5 wiring — inside the flag, walk before digest")
# ═════════════════════════════════════════════════════════════════════════════

sched_src = (API / "jobs" / "unified_scheduler.py").read_text()
# ADR-591 D2/D3.a: the scheduler holds NO connector job. Both walkers and
# the raw-lane GC that only existed to age out what a clock accumulated are
# deleted — capture is consumer-invoked, and a dormant walker would be a
# second way to do it (Singular Implementation).
check("5a the connector capture walk is GONE from the scheduler",
      "drain_due_connector_captures" not in sched_src)
check("5b the connector digest walk is GONE from the scheduler",
      "drain_due_connector_derives" not in sched_src)
check("5c the connector raw-lane GC is GONE from the scheduler",
      "prune_raw_lane" not in sched_src)
check("5c2 no connector walker survives in the service modules either",
      not hasattr(_conn_mod, "drain_due_connector_captures"))
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

# ═════════════════════════════════════════════════════════════════════════════
print("§7 the settings surface — dials validated, doors honest (2026-08-19)")
# ═════════════════════════════════════════════════════════════════════════════

from services.connectors import _validate_destination, update_connector_settings  # noqa: E402

check("7a destination: empty/slashes normalize to None (the default lane)",
      _validate_destination("") is None
      and _validate_destination("  /  ") is None
      and _validate_destination("/Projects/Acme/") == "Projects/Acme")

for bad in ("../escape", "a/../b", "a/./b", "a//b", "a\\b", "x" * 121):
    try:
        _validate_destination(bad)
        check(f"7b destination rejects {bad[:20]!r}", False)
    except ValueError:
        check(f"7b destination rejects {bad[:20]!r}", True)


class _SettingsQ:
    def __init__(self, store):
        self._store = store

    def __getattr__(self, name):
        return lambda *a, **k: self

    def update(self, payload):
        self._store["updated"] = payload
        return self

    def execute(self):
        from types import SimpleNamespace
        return SimpleNamespace(data=[{"id": "row1", "settings": self._store.get("settings", {})}])


class _SettingsC:
    def __init__(self, store):
        self._store = store

    def table(self, name):
        return _SettingsQ(self._store)


_store: dict = {"settings": {}}
stored = update_connector_settings(_SettingsC(_store), "u1", "slack",
                                   {"destination": " Projects/Acme/ "})
check("7c the retired dials are not reintroduced at the chokepoint "
      "(ADR-591: no cadence, no digest — a connector has one setting)",
      stored is not None and "cadence" not in stored and "digest" not in stored,
      str(stored))
check("7d destination is normalized at the chokepoint",
      stored is not None and stored.get("destination") == "Projects/Acme")

# The request model forbids extras, so a stale client's `cadence`/`digest`
# 422s at the door rather than being silently dropped (ADR-591 D1) — a dial
# that controls nothing must fail loudly.
from routes.integrations import ConnectorSettingsRequest  # noqa: E402
import pydantic  # noqa: E402

_refused = []
for _dead in ("cadence", "digest"):
    try:
        ConnectorSettingsRequest(**{_dead: "x"})
    except pydantic.ValidationError:
        _refused.append(_dead)
check("7e a retired dial is REFUSED at the door, never silently dropped",
      _refused == ["cadence", "digest"], str(_refused))

# --- the route roster: one settings door, the cadence-only door is gone ------
import routes.integrations as ri  # noqa: E402

route_paths = {r.path for r in ri.router.routes}
check("7f PUT connector-settings exists (the three dials' one door)",
      "/integrations/{provider}/connector-settings" in route_paths,
      str(sorted(p for p in route_paths if "cadence" in p or "connector-settings" in p)))
check("7g the cadence-only route is DELETED (singular implementation)",
      "/integrations/{provider}/cadence" not in route_paths)

# The pre-582 sync/coverage/import surface is DELETED (2026-08-19 sweep):
# nothing wrote sync_registry.last_synced_at any more, the import routes were
# {"deprecated": True} stubs, and every FE binding had zero callers. A route
# reappearing here means a second implementation is growing back.
_DEAD_ROUTES = {
    "/integrations/{provider}/sync",
    "/integrations/{provider}/sync-status",
    "/integrations/{provider}/coverage/{resource_id}",
    "/integrations/{provider}/destinations",
    "/integrations/history",
    "/integrations/import",
    "/integrations/import/{job_id}",
    "/integrations/slack/channels",
    "/integrations/notion/pages",
    "/integrations/notion/import",
    "/integrations/notion/designated-page",
}
check("7g2 the dead pre-582 sync/coverage/import routes STAY deleted",
      not (_DEAD_ROUTES & route_paths), str(sorted(_DEAD_ROUTES & route_paths)))

# --- the reconnect crash: the callback writes only columns that EXIST --------
# platform_connections has no `last_error` column (measured in production,
# 2026-08-19 — PGRST204 refused the WHOLE update, so every re-connect
# exchanged a fresh token and dropped it). The write-set is pinned to the
# columns the fix intends, so a re-added dead column fails here and a new
# column is added consciously.
_ri_tree = ast.parse((API / "routes" / "integrations.py").read_text())
_cb = next(n for n in ast.walk(_ri_tree)
           if isinstance(n, ast.AsyncFunctionDef) and n.name == "oauth_callback")
_update_dicts = [
    n.value for n in ast.walk(_cb)
    if isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict)
    and any(isinstance(t, ast.Name) and t.id == "update_data" for t in n.targets)
]
_keys = {k.value for d in _update_dicts for k in d.keys
         if isinstance(k, ast.Constant)}
check("7h the reconnect update_data exists and is inspectable",
      len(_update_dicts) == 1, f"found {len(_update_dicts)}")
check("7i the reconnect writes NO dead column (last_error crashed every "
      "re-connect via PGRST204)",
      bool(_keys) and "last_error" not in _keys
      and _keys <= {"credentials_encrypted", "metadata", "status", "updated_at",
                    "landscape", "landscape_discovered_at",
                    "refresh_token_encrypted"},
      str(sorted(_keys)))

# --- discovery honesty: a failed listing RAISES, never masquerades as [] ----
_ls_tree = ast.parse((API / "services" / "landscape.py").read_text())
_disc = next(n for n in ast.walk(_ls_tree)
             if isinstance(n, ast.AsyncFunctionDef) and n.name == "discover_landscape")
check("7j discover_landscape swallows NOTHING (no try/except — a revoked "
      "token must not read as an empty landscape)",
      not any(isinstance(n, ast.Try) for n in ast.walk(_disc)))

_nc_tree = ast.parse((API / "integrations" / "core" / "notion_client.py").read_text())
_sp = next(n for n in ast.walk(_nc_tree)
           if isinstance(n, ast.AsyncFunctionDef) and n.name == "search_paginated")
_status_ifs = [
    n for n in ast.walk(_sp)
    if isinstance(n, ast.If)
    and any(isinstance(c, ast.Attribute) and c.attr == "status_code"
            for c in ast.walk(n.test))
]
check("7k search_paginated's non-200 branch RAISES (the silent break made a "
      "dead token look like zero shared pages)",
      len(_status_ifs) == 1
      and any(isinstance(x, ast.Raise) for x in ast.walk(_status_ifs[0]))
      and not any(isinstance(x, ast.Break) for n in _status_ifs
                  for x in ast.walk(n)))

# --- the capture-signal payload carries the dials -----------------------------
_cs = next(n for n in ast.walk(_ri_tree)
           if isinstance(n, ast.AsyncFunctionDef) and n.name == "get_capture_signal")
_ret_keys = {
    k.value
    for n in ast.walk(_cs) if isinstance(n, ast.Return)
    and isinstance(n.value, ast.Dict)
    for k in n.value.keys if isinstance(k, ast.Constant)
}
# Re-anchored 2026-08-21: `capture` was REMOVED from this set. It carried
# `schedule` off the cadence ADR-591 deleted, its emitter raised KeyError for
# every connected provider, and no caller ever read it. The very next check
# already enforces the same ablation for `cadence_choices` — `capture` was
# simply missed when the clock went. Pinning it kept a deleted field alive.
check("7l capture-signal serves the settings object beside the existing shape "
      "(extend, not fork)",
      {"settings", "does", "declared", "observed"} <= _ret_keys,
      str(sorted(_ret_keys)))
check("7l1 the retired `capture` block is GONE from the payload (ADR-591)",
      "capture" not in _ret_keys, str(sorted(_ret_keys)))
check("7l2 the retired cadence enum is GONE from the payload (ADR-591)",
      "cadence_choices" not in _ret_keys, str(sorted(_ret_keys)))

# --- the capability facts are DERIVED, never a parallel copy ------------------
from services.connectors import connector_does  # noqa: E402

_slack_does = connector_does("slack") or {}
_gh_does = connector_does("github") or {}
check("7m does.reads comes from the binding row itself (one home)",
      _slack_does.get("reads") == CONNECTOR_CAPTURE_BINDINGS["slack"]["reads"]
      and all("reads" in b for b in CONNECTOR_CAPTURE_BINDINGS.values()))

# Driven against the real exporter registry: slack HAS an exporter, github
# does not — the writes fact must follow the registry, not a hand-kept list.
from integrations.exporters import get_exporter_registry  # noqa: E402

check("7n does.writes follows the exporter registry (slack exports, github "
      "never writes)",
      get_exporter_registry().get("slack") is not None
      and get_exporter_registry().get("github") is None
      and "export" in _slack_does.get("writes", "")
      and "never writes" in _gh_does.get("writes", ""),
      f"slack={_slack_does.get('writes')!r} github={_gh_does.get('writes')!r}")
check("7o does is None for an unbound platform (no fabricated facts)",
      connector_does("commerce") is None and connector_does("") is None)

# --- a selection is CONSENT: nothing machine-fills selected_sources ----------
# ADR-079/113 auto-selection deleted 2026-08-19: a heuristic pre-checking 50
# sources fabricated the capture writer's mandate (and the ADR-576 reach
# bound) at a moment nothing consumed it — to be enacted whenever the flag
# flips. Smart defaults survive ONLY as the `recommended` badge.
_sel_writers = []
for n in ast.walk(_ri_tree):
    if isinstance(n, ast.Assign):
        tgt_has_sel = any(isinstance(c, ast.Constant) and c.value == "selected_sources"
                          for t in n.targets for c in ast.walk(t))
        if tgt_has_sel:
            _sel_writers.append(n)
check("7p selected_sources is never assigned from smart defaults (consent, "
      "not heuristic)",
      _sel_writers and all(
          "compute_smart_defaults" not in ast.unparse(w.value)
          and "smart_selected" not in ast.unparse(w.value)
          for w in _sel_writers),
      f"{len(_sel_writers)} writers")

n = PASS + FAIL
print(f"\n{PASS}/{n} ADR-582 assertions pass")
sys.exit(0 if FAIL == 0 else 1)
