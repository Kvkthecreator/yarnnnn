"""ADR-592 gate — an app declares how far along it is.

Run: `python3 test_adr592_app_stage.py` from `api/`.

What this protects, in the order the ADR decides it:

  D1  the stage ladder + the DERIVATION, including that it is an IDENTITY for
      every row that predates the field (the seam ships inert)
  D2  `internal` leaves the served roster — and its route is a stub that is
      STILL auth-gated (the pairing, which is the half ADR-574 missed)
  D3  Radar is DELETED — no module, no route, no registration, no lane
  D4  Docs is hidden in full while its IMPLEMENTATION stays resolvable
  D5  the briefs' author keeps its display name

Assertions match COMPOSITIONS, never spellings, and code is stripped of
comments before matching — a gate that matches its own explanatory comment
reads a correct file as broken (recorded defect, ADR-587).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_API = Path(__file__).parent
_ROOT = _API.parent
_WEB = _ROOT / "web"

PASSED = 0
FAILED: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    global PASSED
    if cond:
        print(f"  ok   {label}")
        PASSED += 1
    else:
        print(f"  FAIL {label}{(' — ' + detail) if detail else ''}")
        FAILED.append(label)


def code_only(text: str) -> str:
    """Strip block + line comments so an assertion cannot match prose."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)


def read(rel: str, root: Path = _WEB) -> str:
    p = root / rel
    return p.read_text() if p.exists() else ""


# ── D1 — the ladder and the derivation ──────────────────────────────────────
print("\n[D1] the stage ladder + derivation")

from services.app_stage import (  # noqa: E402
    DEFAULT_STAGE,
    STAGES,
    is_default_pinned,
    is_exposed,
    launcher_tier_for,
    resolve_stage,
)
from services.kernel_surfaces import (  # noqa: E402
    KERNEL_SURFACES,
    kernel_surface_entries,
    kernel_surface_slugs,
)

check("four stages, ordered least→most exposed",
      STAGES == ("internal", "search-only", "beta", "primary"))
check("the ladder's order is meaningful (index compares)",
      STAGES.index("internal") < STAGES.index("beta") < STAGES.index("primary"))
check("a row declaring no stage is not forced to a constant",
      DEFAULT_STAGE in STAGES)

# The identity property: for every row EXCEPT the ones this ADR deliberately
# changed, the derived tier/pin must equal what the row already declared. This
# is what makes the field inert on arrival — and it is the assertion that
# would have caught a flat `primary` default promoting 27 surfaces to the Dock.
_changed = {"docs"}
_drift = []
for e in KERNEL_SURFACES:
    if e["slug"] in _changed:
        continue
    if e.get("launcher_tier") is not None:
        d = launcher_tier_for(e)
        if d is not None and d != e.get("launcher_tier"):
            _drift.append((e["slug"], "tier", e.get("launcher_tier"), d))
    if "default_pinned" in e:
        d = is_default_pinned(e)
        if d != e["default_pinned"]:
            _drift.append((e["slug"], "pin", e["default_pinned"], d))
check("the derivation is an IDENTITY for every untouched row (ships inert)",
      not _drift, f"drift={_drift[:4]}")

# ⚠️ THE VACUITY GUARD (added 2026-08-26 — the defect this section had).
# The identity check above compares DECLARED against DERIVED, so it is
# strictly weaker the fewer rows declare, and perfectly green when NOTHING
# declares. That was the live state until this commit: zero rows carried a
# `stage`, `_implied_stage` back-derived it from the very pair the field
# exists to replace, and the whole chain was a tautological round-trip. The
# gate was green and would have stayed green if the field were deleted.
#
# So assert the POPULATION, not only the consistency: an APP must state its
# stage. "App" is defined structurally — a row with a route and an
# `application` register — never by a hand-kept slug list, which would be the
# same drift one level up.
# A config DOOR is not an app: it declares a PLACEMENT tier
# (`workspace-config` / `system-config`), which `launcher_tier_for` passes
# through untouched precisely because a placement is not a promotion rung. An
# app declares `primary` or `search-only` — the rungs the stage governs. That
# distinction is read from the row, never from a slug list, so a new app is
# covered the day it is added and a new door is not miscounted.
_PLACEMENT_TIERS = {"workspace-config", "system-config"}
_apps = [
    e for e in KERNEL_SURFACES
    if e.get("route")
    and e.get("register") == "application"
    and e.get("launcher_tier") not in _PLACEMENT_TIERS
]
check("there ARE app rows to check (guards a silent no-op scan)",
      len(_apps) >= 8, f"found {len(_apps)}")
_undeclared = sorted(e["slug"] for e in _apps if e.get("stage") not in STAGES)
check("every APP declares its stage (the field is not inert)",
      not _undeclared,
      f"undeclared={_undeclared} — a row that declares none cannot drift, so "
      f"the identity check above passes vacuously for it")
_declared = [e for e in KERNEL_SURFACES if e.get("stage") in STAGES]
check("the declared set is non-empty (the identity check has subjects)",
      len(_declared) >= 8, f"declared={len(_declared)}")

# Coherence, derived rather than hand-kept (the ADR-297 invariant).
_served = kernel_surface_entries()
_prim = {s["slug"] for s in _served if s.get("launcher_tier") == "primary"}
_pin = {s["slug"] for s in _served if s.get("default_pinned")}
check("served pinned set == served primary tier (ADR-297 coherence, derived)",
      _prim == _pin, f"primary={sorted(_prim)} pinned={sorted(_pin)}")

# ⭐ The Dock's client-side seed must equal the derived pinned set.
# `DEFAULT_KEPT_SURFACES` is a hand-kept copy of a truth the backend derives —
# it exists only because the Dock seeds before any roster arrives. A hand-kept
# list beside a derived truth is the exact drift vector this ADR was written to
# eliminate, so if it cannot be deleted it must at least be ASSERTED. Its own
# ordering comment had gone stale by three deleted slugs (Docs · Studio ·
# Radar) before anyone noticed, which is what an unasserted copy does.
_prefs = read("lib/shell/surface-preferences.ts")
_kept_block = _prefs.split("DEFAULT_KEPT_SURFACES: string[] = [")[1].split("]")[0]
_kept = set(re.findall(r"^\s*'([a-z0-9-]+)'", _kept_block, re.M))
check("DEFAULT_KEPT_SURFACES parsed (guards a silent no-op scan)",
      len(_kept) >= 4, f"parsed={sorted(_kept)}")
check("DEFAULT_KEPT_SURFACES == the DERIVED pinned set",
      _kept == _pin,
      f"dock={sorted(_kept)} derived={sorted(_pin)} — the derivation is right; "
      f"this list is stale")

check("a chrome/dormant row is never pinned however its stage resolves",
      not any(
          is_default_pinned(e)
          for e in KERNEL_SURFACES
          if not e.get("route")
      ))

# ⭐ ONE hiding mechanism, not two (the ADR-592 premise, enforced 2026-08-26).
# `hidden: True` was a SECOND spelling of "not a product": declared on two rows
# and honoured by exactly ONE consumer (the Launcher's filter). `is_exposed`
# never read it, so backend and frontend disagreed about what hidden meant —
# the six-spellings problem this ADR exists to end, surviving inside the ADR
# that ended it. Both rows now carry `stage: "internal"`.
check("no registry row carries the retired `hidden` flag",
      not [e["slug"] for e in KERNEL_SURFACES if e.get("hidden")],
      f"found={[e['slug'] for e in KERNEL_SURFACES if e.get('hidden')]}")
_launcher = read("components/shell/Launcher.tsx")
check("the Launcher no longer filters on `hidden` (its only reader)",
      "!s.hidden" not in code_only(_launcher))

# ── D2 — internal leaves the roster, AND stays gated ────────────────────────
print("\n[D2] `internal` leaves the roster — and the route stays gated")

_internal = [e for e in KERNEL_SURFACES if resolve_stage(e) == "internal"]
# ⚠️ This was `isinstance(_internal, list)` — a TAUTOLOGY, written when ADR-599
# deleted the one internal app and left the set empty. The loop below (the
# stub + middleware pairing, the whole point of D2) therefore ran ZERO
# iterations, and five ungated redirect stubs went undetected until an audit
# found them by hand. The set is populated again (`sources`, `system-agent`),
# so assert the population: an empty set means the loop is measuring nothing.
check("there ARE internal rows, so the pairing loop below actually runs",
      len(_internal) >= 1,
      "an empty internal set makes every per-route check below vacuous")
check("no internal app reaches the served roster",
      not ({e["slug"] for e in _internal} & {s["slug"] for s in _served}))
check("kernel_surface_slugs() is the EXPOSED set, not the declared one",
      kernel_surface_slugs() == {e["slug"] for e in KERNEL_SURFACES if is_exposed(e)})

# The pairing ADR-574 missed: unserved slug ⇒ middleware loses it from the
# DERIVED protected set ⇒ the route must be BOTH a stub AND hand-listed.
_mw = read("lib/supabase/middleware.ts")
_mw_code = code_only(_mw)
for e in _internal:
    slug = e["slug"]
    # ADR-603: an internal app may have NO route yet — a desk that has never
    # been exposed (Supervisor) has nothing to stub, and inventing a redirect
    # to a page nobody can reach is worse than the absence. The obligation
    # binds a route that EXISTS: declaring one without both halves is exactly
    # what this loop catches, so the row's `route` key is the trigger.
    if not e.get("route"):
        check(f"/{slug} declares no route (nothing to gate) — internal, unbuilt",
              not (_WEB / "app" / "(authenticated)" / slug / "page.tsx").exists(),
              "a routeless internal row must not have a live page either")
        continue
    route_src = read(f"app/(authenticated)/{slug}/page.tsx")
    check(f"/{slug} is a redirect stub (internal app must not render)",
          "redirect(" in code_only(route_src) and bool(route_src))
    check(f"/{slug} is still auth-gated (hand-listed in middleware)",
          f'"/{slug}"' in _mw_code,
          "an unserved route not listed here serves 200 logged-out")

# ── D3 — Radar is DELETED ───────────────────────────────────────────────────
print("\n[D3] Radar is deleted — module, route, registration, lane, surface")

check("services/radar.py is gone", not (_API / "services" / "radar.py").exists())
check("routes/radar.py is gone", not (_API / "routes" / "radar.py").exists())
check("web/components/radar/ is gone", not (_WEB / "components" / "radar").exists())
check("no radar registry row",
      not any(e["slug"] == "radar" for e in KERNEL_SURFACES))

_main = (_API / "main.py").read_text()
check("no radar router is mounted",
      "radar.router" not in _main and ", radar," not in _main)

_apps_init = (_API / "services" / "apps" / "__init__.py").read_text()
check("radar is not registered as an app",
      '_register_app("radar"' not in _apps_init)

_sched = (_API / "jobs" / "unified_scheduler.py").read_text()
check("the radar drain is gone from the scheduler tick (the SPEND path)",
      "drain_due_radar_sweeps" not in _sched)

_lane = (_API / "services" / "lane_runner.py").read_text()
check("no radar branch survives in the lane job overlay",
      'app == "radar"' not in _lane)

# The whole point of deleting rather than staging: nothing may still import it.
_py_importers = []
for p in list((_API / "services").rglob("*.py")) + list((_API / "routes").rglob("*.py")) + list((_API / "jobs").rglob("*.py")):
    t = p.read_text()
    if "from services.radar import" in t or "import services.radar" in t:
        _py_importers.append(p.name)
check("nothing still imports services.radar", not _py_importers, f"{_py_importers}")

_client = code_only(read("lib/api/client.ts"))
check("the api.radar namespace is gone", "api/radar/hubs" not in _client)
check("the Radar hub types are gone",
      "RadarHubSummary" not in _client and "RadarHubView" not in _client)

_desk = code_only(read("types/desk.ts"))
_slug_arr = re.search(r"KERNEL_SURFACE_SLUGS.*?=\s*\[(.*?)\]\s*as const", _desk, re.DOTALL)
check("radar left the FE slug allowlist",
      bool(_slug_arr) and "'radar'" not in _slug_arr.group(1))
check("docs left the FE slug allowlist (it is not a navigable surface)",
      bool(_slug_arr) and "'docs'" not in _slug_arr.group(1))

_prefs = code_only(read("lib/shell/surface-preferences.ts"))
_retired = re.search(r"DOCK_RETIRED_SLUGS\s*=\s*new Set<string>\(\[(.*?)\]\)", _prefs, re.DOTALL)
check("radar + docs are DOCK-RETIRED (a curated Dock drops the ghost icon)",
      bool(_retired) and "'radar'" in _retired.group(1) and "'docs'" in _retired.group(1),
      "this is what the byte-equality reseed could never reach")

# ── D4 — Docs hidden, implementation intact ─────────────────────────────────
print("\n[D4] Docs is hidden in full; its implementation stays")

import services.apps  # noqa: F401,E402  (registration side-effect)
from services.authoring import resolve_app, resolve_layout  # noqa: E402

# ⚠️ RE-ANCHORED for ADR-599 D5: Docs graduated from `stage: internal`
# (ADR-592's hide) to DELETED — row, registration, and layouts all gone. The
# internal-stage checks this block held are superseded by absence checks: the
# hide became a delete, which is the stricter form of the same decision.
check("the docs row is DELETED (ADR-599 — the hide became a delete)",
      not any(e["slug"] == "docs" for e in KERNEL_SURFACES))
check("docs is NOT served", not any(s["slug"] == "docs" for s in _served))
check("the docs app is NOT registered (deleted with its layouts)",
      resolve_app("docs") is None)
check("the `document` layout no longer resolves (creation gone; old files render)",
      resolve_layout("document") is None)

_reg = code_only(read("components/shell/SurfaceRegistry.tsx"))
check("SurfaceRegistry carries no docs row (nothing may mount it)",
      "docs: DocsPage" not in _reg)
_ft = code_only(read("lib/file-types/index.ts"))
check("APP_SURFACES no longer claims docs",
      "docs: { surface: 'docs'" not in _ft)
check("the _radar.yaml declaration claim is gone",
      "_radar\\.yaml" not in _ft and "surface: 'radar'" not in _ft)

# ── D5 — the briefs keep their author's name ────────────────────────────────
print("\n[D5] the briefs remain; their author keeps a name")

_pd = (_API / "services" / "principal_display.py").read_text()
check("system:radar keeps a display name server-side (history renders a name)",
      "system:radar" in _pd)
_attr = read("lib/workspace/attribution.ts")
check("system:radar keeps a display name client-side",
      "system:radar" in _attr)

from services.agents_registry import AGENTS  # noqa: E402

# ⚠️ RE-ANCHORED for ADR-599 D1: scout was deleted WITH the colleague roster
# (a deliberate later ruling, not radar's deletion reaching an agent). The
# principle this check held — "an agent is not an app" — survives as its
# inverse ruling: an app is not an agent's lifeline either; both are deleted
# on their own grounds. `system:radar` attribution never read the registry
# (principal_display), so the briefs keep rendering their author.
check("scout is deleted with the roster (ADR-599), not resurrected by data",
      "scout" not in AGENTS)

# ── verdict ─────────────────────────────────────────────────────────────────
print()
if FAILED:
    print(f"ADR-592 gate RED — {PASSED} passed, {len(FAILED)} failed")
    for f in FAILED:
        print(f"    - {f}")
    sys.exit(1)
print(f"ADR-592 gate GREEN — {PASSED}/{PASSED}")
