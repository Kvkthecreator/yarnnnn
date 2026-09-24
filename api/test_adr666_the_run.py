"""ADR-666 — the run: work that acts, seen while it happens.

Run: cd api && python3 test_adr666_the_run.py

Script-shaped (the house form): prints each check, a count, exits 1 on any
failure. The loop arms are DRIVEN — the real lane loop with a fake engine, the
real standing sweep with stubbed ledgers — not read.
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "x")

ROOT = Path(__file__).resolve().parent.parent
PASS = 0
FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name} {('— ' + detail) if detail else ''}")


def read(rel: str) -> str:
    return (ROOT / rel).read_text()


from services import client_tools as ct  # noqa: E402
from services import runs as runs_mod  # noqa: E402
from services import standing_work as st  # noqa: E402

M = "5f0e1234-1111-2222-3333-444455556666"


def _decl(body: str, topic: str = "prices"):
    return st.parse_standing_yaml(body, topic=topic, declaration_path=f"/workspace/{topic}/_standing.yaml",
                                  user_id="owner-1", workspace_id="ws-1")


# ═════════════════════════════════════════════════════════════════════════════
print("D1 browser work is standing work — one key")
# ═════════════════════════════════════════════════════════════════════════════
_ok = _decl(f"target: prices.csv\nschedule: '0 9 * * 1'\nbrowser:\n  member: {M}\n  sites: [https://www.Example.com/x, shop.example.org]\n")
check("a browser block parses healthy, sites normalized to bare hosts",
      _ok.problem is None and _ok.browser == {"member": M, "sites": ["example.com", "shop.example.org"]},
      f"{_ok.problem} {_ok.browser}")
check("a type with no app (csv) runs under Text when it is browser work", _ok.app == "text")
check("…while the same csv kept by the drain has no app", _decl("target: p.csv\nsources: [{id: s, url: 'https://x.y'}]\n").app is None)
check("browser work needs no source", _ok.problem is None and _ok.sources == [])
for _bad, _why in [
    ("browser: yes\n", "not a mapping"),
    ("browser:\n  member: someone\n  sites: [example.com]\n", "member is not a member id"),
    (f"browser:\n  member: {M}\n  sites: []\n", "no sites"),
    (f"browser:\n  member: {M}\n  sites: ['not a site']\n", "a site that is not a host"),
]:
    check(f"a malformed block is refused by name — {_why}",
          _decl("target: p.md\n" + _bad).problem == "browser_invalid", str(_decl("target: p.md\n" + _bad).problem))
check("browser work's sources are workspace paths only",
      _decl(f"target: p.md\nbrowser: {{member: {M}, sites: [a.com]}}\nsources: [{{id: s, url: 'https://x.y'}}]\n").problem
      == "sources_invalid")
check("…and a path source is accepted",
      _decl(f"target: p.md\nbrowser: {{member: {M}, sites: [a.com]}}\nsources: [{{id: s, path: notes/}}]\n").problem is None)
check("`browser` is the one key added", "browser" in st.DECLARATION_KEYS and len(st.DECLARATION_KEYS) == 8)
check("a site allows itself and its subdomains", st.site_allowed("https://m.example.com/a", ["example.com"])
      and st.site_allowed("https://example.com", ["example.com"]))
check("…and never a lookalike suffix or a non-web scheme",
      not st.site_allowed("https://notexample.com", ["example.com"])
      and not st.site_allowed("https://example.com.evil.io", ["example.com"])
      and not st.site_allowed("javascript:alert(1)", ["example.com"]))

# The door stamps the signed-in member; a client never names one.
from routes import standing_work as R  # noqa: E402

check("the door's request has no member field — only sites",
      "browser_sites" in R.CreateStandingRequest.model_fields
      and not any("member" in f for f in R.CreateStandingRequest.model_fields))
_create_src = read("api/routes/standing_work.py")
# ADR-667 D2 — the stamp lives in the ONE door both the routes and DeclareWork call.
_door_src = read("api/services/standing_door.py")
check("…and it stamps the signed-in member",
      '{"member": auth.user_id, "sites": list(browser_sites)}' in _door_src
      and "browser_sites=request.browser_sites" in _create_src)
check("an edit may change the sites, never the member",
      "browser_sites" in R.UpdateStandingRequest.model_fields
      and '{**parsed["browser"], "sites": list(browser_sites)}' in _door_src)


async def _run_now_other():
    decl = _ok
    auth = types.SimpleNamespace(user_id="someone-else", client=None, workspace_id="ws-1")
    try:
        await R._start_browser_run(auth, "owner-1", decl)
    except Exception as exc:  # noqa: BLE001
        return getattr(exc, "status_code", None), (getattr(exc, "detail", None) or {})
    return None, {}

# ⭐ Found by the production click-pass (2026-09-24): the ROUTE returned the
# coroutine un-awaited — FastAPI 500'd on a coroutine as the response, the
# browser saw CORS. Calling `_start_browser_run` directly (below) never saw it.
import ast as _ast  # noqa: E402

_route = next(n for n in _ast.walk(_ast.parse(read("api/routes/standing_work.py")))
              if isinstance(n, _ast.AsyncFunctionDef) and n.name == "run_standing_now")
_calls_bare = [n for n in _ast.walk(_route) if isinstance(n, _ast.Return)
               and isinstance(n.value, _ast.Call) and getattr(n.value.func, "id", "") == "_start_browser_run"]
_awaited = [n for n in _ast.walk(_route) if isinstance(n, _ast.Await)
            and isinstance(n.value, _ast.Call) and getattr(n.value.func, "id", "") == "_start_browser_run"]
check("Run now AWAITS the browser start (a bare coroutine is a 500 the browser reads as CORS)",
      len(_awaited) == 1 and not _calls_bare)
_status, _detail = asyncio.run(_run_now_other())
check("Run now on another member's browser work is refused (403, by name)",
      _status == 403 and _detail.get("problem") == "browser_not_yours", f"{_status} {_detail}")

# ═════════════════════════════════════════════════════════════════════════════
print("\nD2 a run is a row — every standing run opens one and finishes it")
# ═════════════════════════════════════════════════════════════════════════════
_opened: list = []
_finished: list = []
_saved = (runs_mod.open_run, runs_mod.finish_run, runs_mod.live_for_topic)
runs_mod.open_run = lambda **k: (_opened.append(k), f"run-{len(_opened)}")[1]
runs_mod.finish_run = lambda run_id, **k: _finished.append((run_id, k))

_problem_decl = _decl("target: poster.png\nsources: [{id: s, url: 'https://x.y'}]\n", topic="posters")
_res = asyncio.run(st.run_standing_sweep(object(), "owner-1", _problem_decl))
check("a run opens exactly one row (derive, scheduled, its topic)",
      len(_opened) == 1 and _opened[0]["kind"] == "derive" and _opened[0]["trigger"] == "scheduled"
      and _opened[0]["topic"] == "posters", str(_opened))
check("…and finishes it exactly once, failed, with the reason as its outcome",
      len(_finished) == 1 and _finished[0][0] == "run-1" and _finished[0][1]["state"] == "failed"
      and _finished[0][1]["outcome"] == "unsupported_format", str(_finished))
check("…and the result names the run", _res.get("run_id") == "run-1")

# The cost is summed from the ledger rows the run wrote — by id.
import services.telemetry as tel  # noqa: E402
import services.platform_limits as pl  # noqa: E402
_opened.clear(); _finished.clear()
_saved_tel = (tel.record_execution_event, pl.get_effective_balance)
tel.record_execution_event = lambda *a, **k: "ev-1"
pl.get_effective_balance = lambda c, u, _b=0.0: 0.0
_healthy = _decl("target: brief.md\nsources: [{id: s, url: 'https://x.y'}]\n", topic="brief")
asyncio.run(st.run_standing_sweep(object(), "owner-1", _healthy, force=True))
tel.record_execution_event, pl.get_effective_balance = _saved_tel
check("a refused run still finishes its row, with the ids of the ledger rows it wrote",
      len(_finished) == 1 and list(_finished[0][1]["ledger_ids"]) == ["ev-1"]
      and _finished[0][1]["outcome"] == "balance_exhausted" and _opened[0]["trigger"] == "manual",
      str(_finished))

# ═════════════════════════════════════════════════════════════════════════════
print("\nD4 browser work that comes due waits on its member — it never runs")
# ═════════════════════════════════════════════════════════════════════════════
_opened.clear(); _finished.clear()
_saved_sweep = st._sweep


async def _must_not_run(*a, **k):
    raise AssertionError("the drain performed browser work")

st._sweep = _must_not_run
runs_mod.live_for_topic = lambda client, ws, topic: None
runs_mod._svc = lambda: None
try:
    _due = asyncio.run(st.run_standing_sweep(object(), "owner-1", _ok))
except AssertionError:  # the drain PERFORMED it — a failed check, never a crash
    _due = {"performed": True}
check("⭐ the drain never performs browser work", not _due.get("performed"))
check("a due tick opens ONE run, waiting on its member, as that member",
      _due.get("waiting") is True and len(_opened) == 1 and _opened[0]["state"] == "waiting"
      and _opened[0]["waiting_on"] == {"kind": "member"} and _opened[0]["user_id"] == M
      and _opened[0]["kind"] == "browser", str(_opened))
runs_mod.live_for_topic = lambda client, ws, topic: {"id": "run-waiting", "state": "waiting"}
try:
    _due2 = asyncio.run(st.run_standing_sweep(object(), "owner-1", _ok))
except AssertionError:
    _due2 = {"performed": True}
check("a second due tick does not stack another", len(_opened) == 1 and _due2.get("run_id") == "run-waiting")
check("the index guards it too — one waiting run per topic",
      "runs_one_waiting_per_topic" in read("supabase/migrations/262_adr666_runs.sql"))
st._sweep = _saved_sweep
runs_mod.open_run, runs_mod.finish_run, runs_mod.live_for_topic = _saved

# ═════════════════════════════════════════════════════════════════════════════
print("\nD1/D6 driven through the real lane loop — the scope and the stop")
# ═════════════════════════════════════════════════════════════════════════════
from services import lane_runner as lr  # noqa: E402
from services import model_router  # noqa: E402


class _Routed:
    def __init__(self, text="", tool_calls=None):
        self.text = text
        self.tool_calls = tool_calls or []
        self.usage = {"input_tokens": 1, "output_tokens": 1}
        self.ledger_model = "fake"
        self.finish_reason = "stop"
        self.raw_assistant_message = {"role": "assistant", "content": text, "tool_calls": []}


async def _drive(url: str, *, sites: tuple, on_act=None):
    calls = {"n": 0}

    async def fake_stream(model, messages, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            yield ("done", _Routed(tool_calls=[{"id": "tc1", "name": "BrowserOpen", "arguments": {"url": url}}]))
        else:
            yield ("delta", "done.")
            yield ("done", _Routed(text="done."))

    saved = (model_router.lanes_enabled, model_router.route_completion_stream, lr.resolve_turn_reach,
             lr.build_lane_conventions, lr.unpriced_lane_model, lr._resolve_byok_key)
    model_router.lanes_enabled = lambda: True
    model_router.route_completion_stream = fake_stream
    lr.resolve_turn_reach = lambda *a, **k: (False, ())
    lr.build_lane_conventions = lambda *a, **k: "system"
    lr.unpriced_lane_model = lambda m: False
    lr._resolve_byok_key = lambda a, m: None

    class _Auth:
        user_id = "member-a"
        client = None
        workspace_id = None

    events = []
    try:
        async for kind, payload in lr.run_lane_turn_stream(
            _Auth(), model="anthropic/claude-sonnet-5", history=[], user_message="run it",
            client_tools=ct.offered(None, ["browser"], "extension/0.1.0"), browser_sites=sites,
        ):
            events.append((kind, payload))
            if kind == "client_tool" and on_act:
                on_act(payload)
    finally:
        (model_router.lanes_enabled, model_router.route_completion_stream, lr.resolve_turn_reach,
         lr.build_lane_conventions, lr.unpriced_lane_model, lr._resolve_byok_key) = saved
    return events, calls["n"]


_ev, _ = asyncio.run(_drive("https://evil.example.net/x", sites=("example.com",)))
_kinds = [k for k, _ in _ev if k != "round_break"]
_rcpt = next((p for k, p in _ev if k == "receipt"), {})
check("⭐ an open outside the run's sites never reaches the member's machine",
      "client_tool" not in _kinds and "receipt" in _kinds, str(_kinds))
check("…and the step says so, as an `outside` act naming the site",
      (_rcpt.get("record") or {}).get("act") == "outside"
      and (_rcpt.get("record") or {}).get("subject") == "evil.example.net" and _rcpt.get("ok") is False, str(_rcpt))
_ev, _ = asyncio.run(_drive("https://shop.example.com/x", sites=("example.com",),
                            on_act=lambda p: ct.resolve(p["nonce"], p["call_id"], "member-a",
                                                        {"success": True, "receipt": "Opened.",
                                                         "record": {"act": "opened", "subject": "Shop", "changed": True}})))
check("an open inside them goes out as before", "client_tool" in [k for k, _ in _ev])
_ev, _ = asyncio.run(_drive("https://anything.org", sites=(),
                            on_act=lambda p: ct.resolve(p["nonce"], p["call_id"], "member-a",
                                                        {"success": True, "receipt": "Opened."})))
check("a chat turn (no run scope) is not scoped", "client_tool" in [k for k, _ in _ev])


def _stop_now(payload):
    ct.bind_run(payload["nonce"], "run-stop")
    check("the run's Stop finds its turn in this process", ct.stop_run("run-stop") is True)

_ev, _rounds = asyncio.run(_drive("https://example.com", sites=("example.com",), on_act=_stop_now))
_done = next((p for k, p in _ev if k == "done"), {})
check("⭐ a stopped run ends its turn at the act in flight — no further engine round",
      _rounds == 1 and _done.get("text") == ct.STOPPED_SENTENCE, f"rounds={_rounds} text={_done.get('text')!r}")
check("…and the step says it stopped",
      any(k == "receipt" and "Stopped" in (p.get("text") or "") for k, p in _ev))
check("no turn and no run binding is left behind", not ct._TURNS and not ct._RUNS)
check("the turn's cost rows ride `done` so its run can sum them", "ledger_ids" in _done)

# ⭐ Found by the production click-pass: a run stopped from outside finished as
# `stopped` but carried `outcome: no_change` — the turn ended normally after
# the stop and derived a done-style outcome. A stopped run has none.
_upd: list = []
_saved_rf = (runs_mod.get_run, runs_mod._update, runs_mod._cost_of, runs_mod._svc)
runs_mod.get_run = lambda c, rid: {"id": rid, "state": "stopped"}
runs_mod._update = lambda rid, f: _upd.append(f)
runs_mod._cost_of = lambda ids: None
runs_mod._svc = lambda: None
runs_mod.finish_run("run-x", state="done", outcome="no_change", revision_id="rev-1")
runs_mod.get_run, runs_mod._update, runs_mod._cost_of, runs_mod._svc = _saved_rf
check("a run stopped from outside stays stopped, with no outcome and no revision claimed",
      _upd and _upd[-1]["state"] == "stopped" and _upd[-1]["outcome"] is None
      and "revision_id" not in _upd[-1], str(_upd))

# ═════════════════════════════════════════════════════════════════════════════
print("\nD5 a browser turn in chat is a run; receipts have one home")
# ═════════════════════════════════════════════════════════════════════════════
_lanes = read("api/routes/lanes.py")
check("a receipt is a step of the turn's run", "turn_run.on_receipt(payload)" in _lanes)
check("the reply row carries run_id and never the receipts",
      'extra["run_id"] = turn_run.run_id' in _lanes and 'extra["receipts"]' not in _lanes
      and "receipts.append(" not in _lanes)
check("the transcript read brings the steps back from the run", "hydrate_receipts(auth.client" in _lanes)
check("both ends of a turn finish its run (stopped and not)",
      _lanes.count("turn_run.finish(") == 2)


class _FakeRuns:
    def __init__(self, rows):
        self.rows = rows

    def table(self, name):
        rows = self.rows
        q = types.SimpleNamespace()
        q.select = lambda *a, **k: q
        q.in_ = lambda col, vals: (setattr(q, "_ids", vals), q)[1]
        q.execute = lambda: types.SimpleNamespace(data=[r for r in rows if r["id"] in q._ids])
        return q

_msgs = [{"id": "m1", "metadata": {"run_id": "r1"}}, {"id": "m2", "metadata": {}}]
runs_mod.hydrate_receipts(_FakeRuns([{"id": "r1", "steps": [{"name": "BrowserOpen", "text": "Opened."}]}]), _msgs)
check("hydration puts a run's steps back under metadata.receipts, and touches nothing else",
      _msgs[0]["metadata"]["receipts"] == [{"name": "BrowserOpen", "text": "Opened."}]
      and "receipts" not in _msgs[1]["metadata"])
_mig = read("supabase/migrations/262_adr666_runs.sql")
check("the migration moved the stored receipts into runs and verifies none remain",
      "(metadata - 'receipts') || jsonb_build_object('run_id', new_id)" in _mig
      and "still carry metadata.receipts" in _mig)

# ═════════════════════════════════════════════════════════════════════════════
print("\nD6 every member sees every run, live")
# ═════════════════════════════════════════════════════════════════════════════
check("members read runs through RLS", "FOR SELECT USING (is_workspace_member(workspace_id))" in _mig)
check("runs are published to realtime, with the RLS check before it is trusted",
      "ALTER PUBLICATION supabase_realtime ADD TABLE public.runs" in _mig and "RLS off" in _mig)
_rr = read("api/routes/runs.py")
check("stop is the run's own member's act or the owner's",
      "auth.user_id not in (str(run.get(\"user_id\") or \"\"), _acting_owner(auth))" in _rr)
check("a run in another workspace reads as absent", 'str(run.get("workspace_id")) != str(ws)' in _rr)

# ═════════════════════════════════════════════════════════════════════════════
print("\nD2 the run replaces the time-window join; the cost ledger is only the cost ledger")
# ═════════════════════════════════════════════════════════════════════════════
_sw_routes = read("api/routes/standing_work.py")
check("the standing routes read no run from execution_events",
      not re.search(r"""table\(\s*["']execution_events["']""", _sw_routes))
for _gone in ("_join_revision", "_written_revisions", "_RUN_REVISION_WINDOW_S", "_LEGACY_LEDGER_PREFIXES",
              "_recent_runs", "_last_runs", "class LastRun", "class StandingRun"):
    check(f"deleted: {_gone}", _gone not in _sw_routes)
# ⭐ Found by the production click-pass: a lost claim read "Ran — nothing
# changed" above a run card saying the file was updated. A run in flight is
# `already`, never `no_change`, and both Run now handlers word it so.
check("a Run now that finds a run in flight says `already`, never `no_change`",
      '"already": True,\n                "detail": "already running' in _sw_routes
      and all("res.already" in read(f) for f in ("web/components/supervisor/StandingDetail.tsx",
                                                  "web/components/supervisor/SupervisorSurface.tsx")))
check("the detail and the roster serve the one run shape", "list[RunOut]" in _sw_routes
      and "last_run: Optional[RunOut]" in _sw_routes)

# ═════════════════════════════════════════════════════════════════════════════
print("\nD3 a declared browser run leaves a record; nothing else does")
# ═════════════════════════════════════════════════════════════════════════════
_rec = runs_mod.render_record(
    {"started_at": "2026-09-24T09:00:00+00:00", "trigger": "manual", "state": "done", "outcome": "wrote",
     "revision_id": "abcdef123456", "steps": [{"text": "Opened “Shop”.", "ok": True},
                                              {"text": "Could not fill “Price”.", "ok": False}]},
    topic="prices", target="prices.csv", member_name="Kevin")
check("the record says who, how it started, how it ended, what it wrote, every step",
      "Kevin's browser" in _rec and "run now" in _rec and "Wrote prices.csv" in _rec
      and "1. Opened “Shop”." in _rec and "2. Could not fill “Price”. (failed)" in _rec, _rec)
_runs_src = read("api/services/runs.py")
check("the record lands in the work's own runs/ folder, UTC-stamped",
      'f"{decl.root}/{RECORDS_FOLDER}/{stamp.astimezone(timezone.utc):%Y-%m-%d-%H%M}.md"' in _runs_src)
check("only a turn performing DECLARED work writes one",
      "if self.decl is not None:\n            write_record(self.decl, self.run_id)" in _runs_src
      and "write_record" not in read("api/services/standing_work.py"))

# ═════════════════════════════════════════════════════════════════════════════
print("\nD8 the cockpit: `note` is gone")
# ═════════════════════════════════════════════════════════════════════════════
import services.supervisor_state as ss  # noqa: E402
check("the composed payload has no note and no DECISIONS path",
      not hasattr(ss, "DECISIONS_PATH") and not hasattr(ss, "_note")
      and set(ss.supervisor_state(None, "u", "ws").keys()) == {"needs_you"})

# ═════════════════════════════════════════════════════════════════════════════
print("\nD7/D8/D9 the client: one reader, one view, the cockpit by run state, the tray")
# ═════════════════════════════════════════════════════════════════════════════
_web = ROOT / "web"
_readers = sorted(str(p.relative_to(_web)) for d in ("app", "components", "contexts", "lib")
                  for p in (_web / d).rglob("*.ts*")
                  if re.search(r"api\.runs\s*\.list\(", p.read_text(errors="ignore")))
check("ONE client reader of the run ledger (useRuns)", _readers == ["lib/runs/useRuns.ts"], str(_readers))
_store = read("web/lib/runs/useRuns.ts")
check("…live: it subscribes to `runs`, token before subscribe, with a poll floor while a run is live",
      "table: 'runs'" in _store and _store.index("setAuth(") < _store.index(".subscribe()")
      and "LIVE_POLL_MS" in _store)
for _mount in ("web/components/supervisor/SupervisorSection.tsx", "web/components/supervisor/StandingDetail.tsx",
               "web/components/runs/RunTray.tsx"):
    check(f"a run renders through the one RunView — {_mount.split('/')[-1]}", "<RunView" in read(_mount))
_surf = read("web/components/supervisor/SupervisorSurface.tsx")
check("the cockpit declares running · needs-you · work · recent",
      re.findall(r"kind:\s*'([a-z-]+)'", _surf) == ["running", "needs-you", "work", "recent"])
check("the tray is in the top bar", "<RunTray />" in read("web/components/shell/chrome/TopBarSurface.tsx"))
_tray = read("web/components/runs/RunTray.tsx")
check("…and absent when nothing runs or is due on the viewer", "if (shown.length === 0) return null;" in _tray)
_lp = read("web/components/chat-surface/LanePanel.tsx")
check("a started run is performed through regenerate, once per run",
      "runStream('regenerate', { runId: startRunId })" in _lp and "startedRunRef.current.add(startRunId)" in _lp)
check("the work's conversation knows its viewer (the StudioSurface defect)",
      "viewerId={userId}" in read("web/components/supervisor/Conversation.tsx"))
_detail = read("web/components/supervisor/StandingDetail.tsx")
check("ONE door starts a browser run — the detail — and only with the browser on",
      "async function startBrowserRun()" in _detail and "browserHands()" in _detail
      and "param.get('start')" in _detail)
check("a derive run's reads and write are its steps (what it was made from)",
      '_step("read"' in read("api/services/standing_work.py") and '_step("wrote"' in read("api/services/standing_work.py"))

print()
print("=" * 70)
print(f"  {PASS} passed, {FAIL} failed")
print("=" * 70)
print("✓ all ADR-666 checks passed" if not FAIL else "✗ ADR-666 gate RED")
sys.exit(1 if FAIL else 0)
