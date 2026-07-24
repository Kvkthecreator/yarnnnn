"""ADR-486 R0 gate — the radar lane (standing sweep → derive → brief).

Run with:  cd api && python3 test_adr486_radar.py
(studio/check style — prints ✗ and exits 1 on failure; pytest would
false-pass these, run the file directly.)

Behavioral, not textual, where it matters: check 5/6 EXECUTE
``run_radar_sweep`` end-to-end against stubbed I/O (fake supabase client,
patched intake/router/write/embed/telemetry) — the gate the memory lessons
demand ("gates grep text, not execution" is the failure mode this avoids).
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from types import SimpleNamespace

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ✓ {name}")
    else:
        print(f"  ✗ {name} {detail}")
        FAILURES.append(name)


# ---------------------------------------------------------------------------
# 1. Topic extraction — the single-level meaning-folder rule
# ---------------------------------------------------------------------------
print("1. topic_from_declaration_path")
from services.radar import topic_from_declaration_path

check("valid hub path → topic",
      topic_from_declaration_path("/workspace/operation/competitor-x/_radar.yaml") == "competitor-x")
check("nested path → None (single-level only)",
      topic_from_declaration_path("/workspace/operation/a/b/_radar.yaml") is None)
check("non-radar leaf → None",
      topic_from_declaration_path("/workspace/operation/x/_sources.yaml") is None)
check("outside operation/ → None",
      topic_from_declaration_path("/workspace/governance/x/_radar.yaml") is None)

# ---------------------------------------------------------------------------
# 2. Declaration parse — schedule/paused/steer lifted; sources stay in-file
# ---------------------------------------------------------------------------
print("2. parse_radar_yaml")
from services.radar import parse_radar_yaml

HUB_YAML = """\
schedule: "0 13 * * *"
paused: false
prompt: |
  Watch for pricing moves.
sources:
  - id: blog
    url: https://example.com/feed
"""
hub = parse_radar_yaml(HUB_YAML, topic="competitor-x",
                       declaration_path="/workspace/operation/competitor-x/_radar.yaml",
                       user_id="u1")
check("parses", hub is not None)
check("slug is radar:{topic}", hub.slug == "radar:competitor-x")
check("schedule lifted", hub.schedule == "0 13 * * *")
check("prompt steer in options", "pricing moves" in (hub.options.get("prompt") or ""))
check("sources NOT lifted into options (TrackWebSources reads the file)",
      "sources" not in hub.options)
check("hub root + signal path", hub.signal_path == "/workspace/operation/competitor-x/_watch_signal.yaml")
check("empty content → None",
      parse_radar_yaml("", topic="t", declaration_path="p") is None)
check("tier frontmatter stripped",
      parse_radar_yaml("---\ntier: authored\n---\nschedule: \"0 9 * * *\"\n",
                       topic="t", declaration_path="p").schedule == "0 9 * * *")

# ---------------------------------------------------------------------------
# 3. Scheduling compatibility — a RadarHub flows through the REAL
#    compute_next_run_at (structural-compatibility executed, not asserted)
# ---------------------------------------------------------------------------
print("3. compute_next_run_at compatibility")
from services.scheduling import compute_next_run_at

now = datetime(2026, 7, 24, 10, 0, tzinfo=timezone.utc)
nr = compute_next_run_at(hub, last_run_at=None, now=now)
check("cron next-run computes", nr is not None and nr.hour == 13 and nr.day == 24)

hub_paused = parse_radar_yaml("schedule: \"0 13 * * *\"\npaused: true\n",
                              topic="t", declaration_path="p")
check("paused hub → no next run",
      compute_next_run_at(hub_paused, last_run_at=None, now=now) is None)

# ---------------------------------------------------------------------------
# 4. Posture — the NO_BRIEF contract + steer inclusion
# ---------------------------------------------------------------------------
print("4. build_radar_posture")
from services.radar import NO_BRIEF_SENTINEL, build_radar_posture

posture = build_radar_posture("competitor-x", "Watch for pricing moves.")
check("names the topic", '"competitor-x"' in posture)
check("carries the NO_BRIEF contract", NO_BRIEF_SENTINEL in posture)
check("carries the steer", "Watch for pricing moves." in posture)
check("no steer → no steer block", "OPERATOR STEER" not in build_radar_posture("t"))
check("never-invent bar present", "NEVER invent" in posture)

# ---------------------------------------------------------------------------
# 5+6. run_radar_sweep EXECUTED — brief path and NO_BRIEF path
# ---------------------------------------------------------------------------
print("5. run_radar_sweep — brief lands (executed with stubbed I/O)")


class FakeQuery:
    """Chainable stub: workspace_files reads route on the path filter."""

    def __init__(self, table: str):
        self.table = table
        self.filters: dict = {}
        self.liked = None

    def select(self, *a, **k): return self
    def insert(self, *a, **k): return self
    def update(self, *a, **k): return self
    def delete(self, *a, **k): return self
    def order(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def lte(self, *a, **k): return self
    def in_(self, *a, **k): return self

    def eq(self, key, val):
        self.filters[key] = val
        return self

    def like(self, key, val):
        self.liked = (key, val)
        return self

    def execute(self):
        if self.table == "workspace_files":
            p = self.filters.get("path", "")
            if p.endswith("_watch_signal.yaml"):
                return SimpleNamespace(data=[{"content": "sources:\n- id: blog\n  entries:\n  - title: Big pricing change\n    url: https://example.com/post\n"}])
            return SimpleNamespace(data=[])  # no prior briefs, no collisions
        return SimpleNamespace(data=[])


class FakeClient:
    def table(self, name):  # noqa: D102
        return FakeQuery(name)


events: list[dict] = []
revisions: list[dict] = []
embedded: list[str] = []


async def fake_intake(auth, args):
    return {"success": True, "items_processed": 1,
            "paths_written": ["/workspace/operation/competitor-x/_watch_signal.yaml",
                              "/workspace/inbound/web/blog/2026-07-24T100000Z.xml"],
            "errors": []}


def make_fake_route(text: str):
    async def fake_route(model, messages, **kwargs):
        return SimpleNamespace(text=text, ledger_model="claude-sonnet-4-6",
                               usage={"input_tokens": 100, "output_tokens": 50})
    return fake_route


def fake_write_revision(client, **kwargs):
    revisions.append(kwargs)
    return "rev-abc-123"


async def fake_embed(client, user_id, path, content):
    embedded.append(path)


def fake_record_event(client, **kwargs):
    events.append(kwargs)
    return "evt-1"


import services.authored_substrate as _subst
import services.model_router as _router
import services.primitives.track_web_sources as _tws
import services.primitives.workspace as _wsp
import services.telemetry as _tel
from services.radar import run_radar_sweep

_orig = (_tws.handle_track_web_sources, _router.route_completion,
         _subst.write_revision, _wsp._embed_workspace_file,
         _tel.record_execution_event)
_tws.handle_track_web_sources = fake_intake
_router.route_completion = make_fake_route("# Pricing moved\n\nCompetitor X raised prices ([post](https://example.com/post)).")
_subst.write_revision = fake_write_revision
_wsp._embed_workspace_file = fake_embed
_tel.record_execution_event = fake_record_event

try:
    result = asyncio.get_event_loop().run_until_complete(
        run_radar_sweep(FakeClient(), "user-1", hub)
    ) if sys.version_info < (3, 10) else asyncio.run(run_radar_sweep(FakeClient(), "user-1", hub))

    check("sweep succeeds", result.get("success") is True)
    check("brief placed under briefs/ with date prefix",
          (result.get("brief_path") or "").startswith(
              "/workspace/operation/competitor-x/briefs/") and
          "-pricing-moved" in result.get("brief_path", ""))
    check("exactly one revision written", len(revisions) == 1)
    rev = revisions[0] if revisions else {}
    check("revision_kind='derivation'", rev.get("revision_kind") == "derivation")
    check("derived_from cites signal + raw",
          rev.get("derived_from") == [
              "/workspace/operation/competitor-x/_watch_signal.yaml",
              "/workspace/inbound/web/blog/2026-07-24T100000Z.xml"])
    check("authored_by system:radar", rev.get("authored_by") == "system:radar")
    check("brief embedded (the retrieval fix)", embedded == [rev.get("path")])
    sweep_evts = [e for e in events if e.get("slug", "").startswith("radar-sweep:")]
    brief_evts = [e for e in events if e.get("slug", "").startswith("radar-brief:")]
    check("sweep event metered (mechanical)",
          len(sweep_evts) == 1 and sweep_evts[0].get("mode") == "mechanical"
          and sweep_evts[0].get("status") == "success")
    check("brief event metered (judgment, with usage)",
          len(brief_evts) == 1 and brief_evts[0].get("mode") == "judgment"
          and brief_evts[0].get("status") == "success"
          and brief_evts[0].get("output_tokens") == 50)

    print("6. run_radar_sweep — NO_BRIEF (the honest empty sweep)")
    events.clear(); revisions.clear(); embedded.clear()
    _router.route_completion = make_fake_route("NO_BRIEF")
    result2 = asyncio.run(run_radar_sweep(FakeClient(), "user-1", hub))
    check("no-brief sweep still succeeds", result2.get("success") is True and result2.get("no_brief") is True)
    check("nothing written on NO_BRIEF", len(revisions) == 0 and len(embedded) == 0)
    nb = [e for e in events if e.get("slug") == "radar-brief:competitor-x"]
    check("brief event skipped + error_reason=no_brief (falsifier 4)",
          len(nb) == 1 and nb[0].get("status") == "skipped"
          and nb[0].get("error_reason") == "no_brief")
finally:
    (_tws.handle_track_web_sources, _router.route_completion,
     _subst.write_revision, _wsp._embed_workspace_file,
     _tel.record_execution_event) = _orig

# ---------------------------------------------------------------------------
# 7. Kind-disjointness — the adjacent fix + radar's own scoping
# ---------------------------------------------------------------------------
print("7. kind-disjointness")
import inspect

import services.scheduling as _sched
src_mat = inspect.getsource(_sched.materialize_scheduling_index)
src_due = inspect.getsource(_sched.get_due_recurrences)
check("recurrence materializer is kind-scoped (won't delete radar/capture rows)",
      '.eq("kind", "judgment")' in src_mat)
check("recurrence due-query is kind-scoped",
      '.eq("kind", "judgment")' in src_due)

import services.radar as _radar
check("radar due/claim/record all kind-scoped",
      all('.eq("kind", RADAR_KIND)' in inspect.getsource(f)
          for f in (_radar.claim_radar_run, _radar.record_radar_run,
                    _radar.drain_due_radar_sweeps)))

# ---------------------------------------------------------------------------
# 8. Scheduler wiring — radar drains inside AGENT_ENABLED, outside the
#    capture flag; module compiles
# ---------------------------------------------------------------------------
print("8. scheduler wiring")
import ast

with open("jobs/unified_scheduler.py") as f:
    sched_src = f.read()
ast.parse(sched_src)  # compiles
check("scheduler imports drain_due_radar_sweeps",
      "from services.radar import drain_due_radar_sweeps" in sched_src)
gate_pos = sched_src.find("if is_agent_enabled():")
radar_pos = sched_src.find("drain_due_radar_sweeps")
check("radar drain inside the AGENT_ENABLED gate", 0 < gate_pos < radar_pos)
capture_flag_block = sched_src[sched_src.find("capture_lane_on = "):radar_pos]
check("radar NOT gated on CONNECTOR_CAPTURE_ENABLED (ADR-404 stands)",
      "drain_due_radar_sweeps" not in capture_flag_block)

# radar model must be a routable priced model (the ADR-439 §4 rule)
from services.lane_runner import LANE_MODELS
from services.radar import RADAR_MODEL
check("RADAR_MODEL is a LANE_MODELS key (priced, routable)", RADAR_MODEL in LANE_MODELS)

# ---------------------------------------------------------------------------
# 9. R1/R2 routes — authoring + the composed view (handlers EXECUTED)
# ---------------------------------------------------------------------------
print("9. radar routes (R1 authoring + R2 view)")

import routes.radar as _routes
from routes.radar import (
    CreateHubRequest, HubSource, UpdateHubRequest,
    compose_declaration_yaml, create_hub, get_hub, update_hub,
)

# compose → parse round-trip: what the route writes, the walker schedules
composed = compose_declaration_yaml(
    schedule="0 21 * * *", paused=False, prompt="Watch pricing.",
    sources=[{"id": "blog", "url": "https://example.com/feed", "max_entries": 8}],
    fire_on_activation=True,
)
rt = parse_radar_yaml(composed, topic="t", declaration_path="/workspace/operation/t/_radar.yaml")
check("composed yaml round-trips through parse_radar_yaml",
      rt is not None and rt.schedule == "0 21 * * *"
      and rt.options.get("fire_on_activation") is True
      and "Watch pricing." in (rt.options.get("prompt") or ""))
check("composed yaml carries sources for TrackWebSources",
      _routes._declared_sources(composed)[0]["url"] == "https://example.com/feed")

# route handlers executed against a stateful fake
class RouteFakeQuery(FakeQuery):
    def __init__(self, table, store):
        super().__init__(table)
        self.store = store

    def execute(self):
        if self.table == "workspace_files":
            p = self.filters.get("path", "")
            if p in self.store:
                return SimpleNamespace(data=[{"path": p, "content": self.store[p]}])
            return SimpleNamespace(data=[])
        return SimpleNamespace(data=[])


class RouteFakeClient:
    def __init__(self):
        self.files: dict = {}

    def table(self, name):
        return RouteFakeQuery(name, self.files)


written: list[dict] = []


def route_fake_write(client, **kwargs):
    written.append(kwargs)
    client_files = _route_client.files
    client_files[kwargs["path"]] = kwargs["content"]
    return "rev-route-1"


async def route_fake_materialize(client, user_id):
    return None


_route_client = RouteFakeClient()
_route_auth = SimpleNamespace(user_id="user-1", client=_route_client, workspace_id=None)

_orig_wr = _subst.write_revision
_orig_mat = _routes._materialize
_subst.write_revision = route_fake_write
_routes._materialize = route_fake_materialize
try:
    from fastapi import HTTPException

    req = CreateHubRequest(topic="competitor-x",
                           sources=[HubSource(id="blog", url="https://example.com/feed")],
                           prompt="Watch pricing.")
    summary = asyncio.run(create_hub(req, _route_auth))
    check("create_hub writes the declaration through the one door",
          len(written) == 1 and written[0]["path"] == "/workspace/operation/competitor-x/_radar.yaml"
          and written[0]["authored_by"] == "operator")
    check("create_hub returns the hub summary",
          summary.topic == "competitor-x" and summary.sources[0].url == "https://example.com/feed")

    try:
        asyncio.run(create_hub(req, _route_auth))
        check("duplicate create → 409", False)
    except HTTPException as e:
        check("duplicate create → 409", e.status_code == 409)

    try:
        bad = CreateHubRequest(topic="Not A Slug!", sources=[HubSource(id="b", url="https://x.com/f")])
        asyncio.run(create_hub(bad, _route_auth))
        check("bad topic → 422", False)
    except HTTPException as e:
        check("bad topic → 422", e.status_code == 422)

    upd = asyncio.run(update_hub("competitor-x", UpdateHubRequest(paused=True), _route_auth))
    check("update_hub pause persists to the declaration",
          upd.paused is True and "paused: true" in _route_client.files[
              "/workspace/operation/competitor-x/_radar.yaml"])

    view = asyncio.run(get_hub("competitor-x", _route_auth))
    check("get_hub composes the view (derived, not stored)",
          view.topic == "competitor-x" and view.briefs == [] and view.brief_count == 0)

    try:
        asyncio.run(get_hub("nope", _route_auth))
        check("unknown hub → 404", False)
    except HTTPException as e:
        check("unknown hub → 404", e.status_code == 404)
finally:
    _subst.write_revision = _orig_wr
    _routes._materialize = _orig_mat

# registration — the route ships wired
with open("main.py") as f:
    main_src = f.read()
check("radar router registered in main.py",
      "radar.router" in main_src and ", radar" in main_src)

# ---------------------------------------------------------------------------
print()
if FAILURES:
    print(f"✗ {len(FAILURES)} check(s) failed: {FAILURES}")
    sys.exit(1)
print("✓ all ADR-486 radar checks passed (R0 lane + R1 authoring + R2 view)")
