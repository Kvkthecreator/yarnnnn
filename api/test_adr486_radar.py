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
import os
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
# 1. Topic extraction — any-depth meaning-folder (ADR-565 D3)
# ---------------------------------------------------------------------------
print("1. topic_from_declaration_path")
from services.radar import topic_from_declaration_path

check("valid hub path → topic",
      topic_from_declaration_path("/workspace/operation/competitor-x/_radar.yaml") == "competitor-x")
check("nested path → joined topic (ADR-565 D3 — the single-level rule fell)",
      topic_from_declaration_path("/workspace/operation/a/b/_radar.yaml") == "a/b")
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
# 4. Posture — the NO_CHANGE contract (ADR-565: the living report job)
# ---------------------------------------------------------------------------
print("4. build_radar_posture")
from services.radar import NO_CHANGE_SENTINEL, build_radar_posture

posture = build_radar_posture("competitor-x")
check("names the topic", '"competitor-x"' in posture)
check("carries the NO_CHANGE contract", NO_CHANGE_SENTINEL in posture)
check("contracts the FULL revised report (fold, not append)",
      "FULL REVISED REPORT" in posture and "fold" in posture)
check("member edits are corrections to preserve (correction-compounds)",
      "corrections to preserve" in posture)
check("never-invent bar present", "NEVER invent" in posture)

# ---------------------------------------------------------------------------
# 5+6. run_radar_sweep EXECUTED — the report revision and the NO_CHANGE path
# ---------------------------------------------------------------------------
print("5. run_radar_sweep — the living report is revised (executed, stubbed I/O)")


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


# ADR-557 D1: radar now PRE-CHECKS the transport flag before deriving (it was
# the one routed caller with no guard, and a flag-off sweep reached the provider
# over the network). This harness stubs `route_completion`, so it must declare
# the transport it is pretending to have — otherwise the sweep correctly
# short-circuits to `router_disabled` and never reaches the stub.
os.environ["MODEL_ROUTER_ENABLED"] = "1"

route_calls: list[dict] = []


def make_fake_route(text: str):
    async def fake_route(model, messages, **kwargs):
        route_calls.append({"model": model, "system": kwargs.get("system", ""),
                            "user": messages[0]["content"] if messages else ""})
        return SimpleNamespace(text=text, ledger_model="gemini-2.5-flash",
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
    check("the report is the FIXED leaf (history = the chain, not the namespace)",
          result.get("report_path") == "/workspace/operation/competitor-x/report.md")
    check("exactly one revision written", len(revisions) == 1)
    rev = revisions[0] if revisions else {}
    check("revision written to report.md",
          rev.get("path") == "/workspace/operation/competitor-x/report.md")
    check("revision_kind='derivation'", rev.get("revision_kind") == "derivation")
    check("derived_from cites signal + raw",
          rev.get("derived_from") == [
              "/workspace/operation/competitor-x/_watch_signal.yaml",
              "/workspace/inbound/web/blog/2026-07-24T100000Z.xml"])
    check("authored_by system:radar", rev.get("authored_by") == "system:radar")
    check("revision message names the report revision",
          "revised the living report" in (rev.get("message") or ""))
    check("report embedded (the retrieval fix)", embedded == [rev.get("path")])
    # The criterion governs the derive: the fixture declaration still carries
    # the legacy `prompt:` steer and NO CRITERION.md exists, so the migration
    # fallback must put that steer on the user message as THE CRITERION.
    check("criterion rides the user message (legacy prompt fallback)",
          "THE CRITERION" in route_calls[-1]["user"]
          and "pricing moves" in route_calls[-1]["user"])
    check("first sweep → baseline-report instruction (no report yet)",
          "THERE IS NO REPORT YET" in route_calls[-1]["user"])
    sweep_evts = [e for e in events if e.get("slug", "").startswith("radar-sweep:")]
    brief_evts = [e for e in events if e.get("slug", "").startswith("radar-brief:")]
    check("sweep event metered (mechanical)",
          len(sweep_evts) == 1 and sweep_evts[0].get("mode") == "mechanical"
          and sweep_evts[0].get("status") == "success")
    check("brief event metered (judgment, with usage)",
          len(brief_evts) == 1 and brief_evts[0].get("mode") == "judgment"
          and brief_evts[0].get("status") == "success"
          and brief_evts[0].get("output_tokens") == 50)
    # The resident binding, asserted on the EXECUTED call (2026-07-28):
    # engine from the scout row; system = character first, job second.
    from services.agents_registry import KERNEL_AGENTS as _KA
    rc = route_calls[-1]
    check("derive routes on the resident's engine (scout row)",
          rc["model"] == _KA["scout"]["model"])
    char_pos = rc["system"].find("You are Researcher")
    job_pos = rc["system"].find("THE STANDING RADAR JOB")
    check("system composes character BEFORE the job overlay",
          0 <= char_pos < job_pos)

    print("6. run_radar_sweep — NO_CHANGE (the honest empty sweep)")
    events.clear(); revisions.clear(); embedded.clear()
    _router.route_completion = make_fake_route("NO_CHANGE")
    result2 = asyncio.run(run_radar_sweep(FakeClient(), "user-1", hub))
    check("no-change sweep still succeeds", result2.get("success") is True and result2.get("no_change") is True)
    check("nothing written on NO_CHANGE", len(revisions) == 0 and len(embedded) == 0)
    nb = [e for e in events if e.get("slug") == "radar-brief:competitor-x"]
    check("derive event skipped + error_reason=no_change (falsifier 4)",
          len(nb) == 1 and nb[0].get("status") == "skipped"
          and nb[0].get("error_reason") == "no_change")

    # A mid-deploy engine echoing the pre-565 contract still reads honest.
    events.clear(); revisions.clear(); embedded.clear()
    _router.route_completion = make_fake_route("NO_BRIEF")
    result3 = asyncio.run(run_radar_sweep(FakeClient(), "user-1", hub))
    check("legacy NO_BRIEF token also reads as the empty sweep",
          result3.get("no_change") is True and len(revisions) == 0)
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
check("radar NOT gated on the capture lane flag (ADR-404 stands; ADR-591 deleted the connector flag entirely)",
      "drain_due_radar_sweeps" not in capture_flag_block)

# The resident binding (operator-ratified 2026-07-28): the sweep's engine +
# character come from the Researcher row — no hardcoded model constant (the
# Designer precedent: a named colleague, never models[0]).
from services.agents_registry import KERNEL_AGENTS
from services.lane_runner import LANE_MODELS
from services.radar import resolve_radar_resident
_res_model, _res_char = resolve_radar_resident()
check("resident is Researcher (scout row: engine + character)",
      _res_model == KERNEL_AGENTS["scout"]["model"]
      and _res_char == KERNEL_AGENTS["scout"]["posture"])
check("resident model is a LANE_MODELS key (priced, routable)", _res_model in LANE_MODELS)

# ---------------------------------------------------------------------------
# 9. R1/R2 routes — authoring + the composed view (handlers EXECUTED)
# ---------------------------------------------------------------------------
print("9. radar routes (R1 authoring + R2 view)")

import yaml as _yaml_mod

import routes.radar as _routes
from routes.radar import (
    CreateHubRequest, HubSource, UpdateHubRequest,
    compose_declaration_yaml, create_hub, get_hub, update_hub,
)

# compose → parse round-trip: what the route writes, the walker schedules
composed = compose_declaration_yaml(
    schedule="0 21 * * *", paused=False,
    sources=[{"id": "blog", "url": "https://example.com/feed", "max_entries": 8}],
    fire_on_activation=True,
)
rt = parse_radar_yaml(composed, topic="t", declaration_path="/workspace/operation/t/_radar.yaml")
check("composed yaml round-trips through parse_radar_yaml",
      rt is not None and rt.schedule == "0 21 * * *"
      and rt.options.get("fire_on_activation") is True)
check("composed yaml is PURE machine config — no prompt key (ADR-565 D2)",
      "prompt" not in (_yaml_mod.safe_load(composed) or {}))
check("composed yaml carries sources for TrackWebSources",
      _routes._declared_sources(composed)[0]["url"] == "https://example.com/feed")

# The briefs shelf reads each brief's own title. EXECUTED, not grepped: this is
# the one radar path a module-level import check can't defend, because
# `_title_of` resolves its reader inside the function body. It shipped broken on
# 2026-07-30 (ADR-507 deleted `services/settle.py`, which it imported from) and
# 500'd `GET /api/radar/hubs` in prod — the sweep gate above caught the WRITER's
# identical dead import, but nothing called the READER.
check("_title_of reads a brief's leading heading",
      _routes._title_of("# Pricing moved\n\nbody") == "Pricing moved")
check("_title_of falls back on a heading-less brief",
      _routes._title_of("plain first line") == "plain first line")
check("_title_of survives an empty brief (the shelf renders, not 500s)",
      _routes._title_of("") == "Untitled note")

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
                           criterion="Watch pricing.")
    summary = asyncio.run(create_hub(req, _route_auth))
    check("create_hub writes the declaration through the one door",
          len(written) == 2 and written[0]["path"] == "/workspace/operation/competitor-x/_radar.yaml"
          and written[0]["authored_by"] == "operator")
    check("create_hub writes the criterion as its OWN file (ADR-564 D2)",
          written[1]["path"] == "/workspace/operation/competitor-x/CRITERION.md"
          and written[1]["authored_by"] == "operator"
          and "Watch pricing." in written[1]["content"])
    check("the declaration itself carries NO criterion prose",
          "Watch pricing." not in _route_client.files[
              "/workspace/operation/competitor-x/_radar.yaml"])
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

    check("create arms fire_on_activation in the declaration (a create-time fact)",
          "fire_on_activation" in _route_client.files[
              "/workspace/operation/competitor-x/_radar.yaml"])

    upd = asyncio.run(update_hub("competitor-x", UpdateHubRequest(paused=True), _route_auth))
    check("update_hub pause persists to the declaration",
          upd.paused is True and "paused: true" in _route_client.files[
              "/workspace/operation/competitor-x/_radar.yaml"])
    # Consume-on-first-update: the flag is never re-emitted. Re-emitting kept a
    # never-run hub permanently armed — compute_next_run_at returns `now` while
    # the flag is set with last_run_at NULL, so every pause/resume re-fired.
    check("update_hub consumes fire_on_activation (never re-emitted)",
          "fire_on_activation" not in _route_client.files[
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
# 10. R2 — the dedicated app (the Images lesson: never grown inside Files)
# ---------------------------------------------------------------------------
print("10. the Radar app (dedicated, search-only until R3)")

import os
_ROOT = os.path.dirname(os.path.abspath(__file__))
def _read(rel):
    with open(os.path.join(_ROOT, rel)) as f:
        return f.read()

ks_src = _read("services/kernel_surfaces.py")
radar_row = ks_src[ks_src.find('"slug": "radar"'):ks_src.find('"slug": "radar"') + 800]
check("BE registry row exists", '"slug": "radar"' in ks_src)
# The unveil (2026-07-28, operator: "handled exactly like Studio") — D7's R3
# gate taken early. Radar wears the Studio treatment: primary tile, shipped
# in the Dock by default.
check("launcher tier is primary (unveiled — the Studio treatment)",
      '"launcher_tier": "primary"' in radar_row and '"route": "/radar"' in radar_row)
check("registered as an application, default-pinned like the other apps",
      '"register": "application"' in radar_row and '"default_pinned": True' in radar_row)

prefs_src = _read("../web/lib/shell/surface-preferences.ts")
check("radar ships in DEFAULT_KEPT_SURFACES (the Dock seed)",
      "'radar'," in prefs_src.split("DEFAULT_KEPT_SURFACES")[1][:400])
check("dock reseed generation exists for existing operators",
      "dock-reseed-2026-07-28-radar" in prefs_src)

desk_src = _read("../web/types/desk.ts")
check("FE slug union + allowlist carry 'radar'",
      "| 'radar'" in desk_src and "'images', 'radar'," in desk_src)

reg_src = _read("../web/components/shell/SurfaceRegistry.tsx")
check("SurfaceRegistry mounts RadarPage", "radar: RadarPage" in reg_src)

surface_src = _read("../web/components/radar/RadarSurface.tsx")
check("the app is its own component tree (never inside Files' viewers)",
      os.path.exists(os.path.join(_ROOT, "../web/components/radar/RadarSurface.tsx"))
      and "useSurfaceParam('radar')" in surface_src)
check("briefs open via Files (the record never requires the app)",
      "navigateToSurface('files'" in surface_src)

ft_src = _read("../web/lib/file-types/index.ts")
check("declaration claim is exactly one leaf in one namespace",
      "resolveDeclarationApplication" in ft_src
      and "operation\\/[^/]+\\/_radar\\.yaml$" in ft_src)

files_src = _read("../web/app/(authenticated)/files/page.tsx")
op = files_src[files_src.find("const openPath"):files_src.find("openPathRef.current = openPath")]
check("openPath consults the declaration claim BEFORE the artifact gate",
      0 < op.find("resolveDeclarationApplication") < op.find("isArtifactCandidate(path)"))

# ---------------------------------------------------------------------------
# 8. materialize preserves a due-but-unfired commitment (EXECUTED)
#
# Falsified live 2026-08-13: materialize_radar_index runs at the TOP of the
# drain tick and recomputed next_run_at from `now` for a never-run hub
# (compute_next_run_at anchors on `last_run_at or now`), destroying the due
# time before the same tick's due scan could claim it. A conversationally-
# created hub (ADR-567 D3 — no fire_on_activation) could therefore NEVER
# fire: the desk-e2e hub armed for 09:00 was rolled to the next day at the
# 09:04 tick (tasks row created 08:59:29, next_run_at 2026-08-14, zero
# execution events). The rule under test: a stored next_run_at that has come
# due survives re-materialization; pause still wins.
# ---------------------------------------------------------------------------
print()
print("8. materialize preserves a due-but-unfired commitment (executed)")

from datetime import datetime, timedelta, timezone as _tz

_DUE_ISO = (datetime.now(_tz.utc) - timedelta(minutes=5)).isoformat()


class _IdxQuery:
    def __init__(self, table, updates, stored_next):
        self._table = table
        self._updates = updates
        self._stored_next = stored_next
        self._op = None
        self._payload = None

    def select(self, *a, **k): self._op = "select"; return self
    def update(self, payload): self._op = "update"; self._payload = payload; return self
    def insert(self, payload): self._op = "insert"; self._payload = payload; return self
    def delete(self, *a, **k): self._op = "delete"; return self
    def eq(self, *a, **k): return self
    def order(self, *a, **k): return self
    def limit(self, *a, **k): return self

    def execute(self):
        if self._table == "tasks" and self._op == "select":
            return SimpleNamespace(data=[{
                "id": "row-1", "slug": hub.slug, "kind": "radar",
                "last_run_at": None, "next_run_at": self._stored_next,
            }])
        if self._op in ("update", "insert"):
            self._updates.append((self._op, self._payload))
        return SimpleNamespace(data=[])


class _IdxClient:
    def __init__(self, stored_next):
        self.updates = []
        self._stored_next = stored_next

    def table(self, name):
        return _IdxQuery(name, self.updates, self._stored_next)


from services.radar import materialize_radar_index

_idx_client = _IdxClient(_DUE_ISO)
asyncio.new_event_loop().run_until_complete(
    materialize_radar_index(_idx_client, "user-1", [hub])
)
_writes = [p for op, p in _idx_client.updates if op == "update"]
check("due-but-unfired next_run_at survives re-materialization",
      len(_writes) == 1 and _writes[0].get("next_run_at") == _DUE_ISO)

from services.scheduling import preserve_due_commitment as _pdc

_now = datetime.now(_tz.utc)
_due = _now - timedelta(minutes=5)
_future = _now + timedelta(hours=1)
check("a future stored time is NOT preserved (recompute wins)",
      _pdc(_future, _now, now=_now, paused=False) == _now)
check("pause wins over the commitment",
      _pdc(_due, None, now=_now, paused=True) is None)
check("no stored time → computed passes through",
      _pdc(None, _future, now=_now, paused=False) == _future)

# ---------------------------------------------------------------------------
print()
if FAILURES:
    print(f"✗ {len(FAILURES)} check(s) failed: {FAILURES}")
    sys.exit(1)
print("✓ all ADR-486 radar checks passed (R0 lane + R1 authoring + R2 view + app)")
