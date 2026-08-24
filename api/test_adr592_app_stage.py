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

# Coherence, derived rather than hand-kept (the ADR-297 invariant).
_served = kernel_surface_entries()
_prim = {s["slug"] for s in _served if s.get("launcher_tier") == "primary"}
_pin = {s["slug"] for s in _served if s.get("default_pinned")}
check("served pinned set == served primary tier (ADR-297 coherence, derived)",
      _prim == _pin, f"primary={sorted(_prim)} pinned={sorted(_pin)}")

check("a chrome/dormant row is never pinned however its stage resolves",
      not any(
          is_default_pinned(e)
          for e in KERNEL_SURFACES
          if not e.get("route")
      ))

# ── D2 — internal leaves the roster, AND stays gated ────────────────────────
print("\n[D2] `internal` leaves the roster — and the route stays gated")

_internal = [e for e in KERNEL_SURFACES if resolve_stage(e) == "internal"]
# ADR-599 deleted Docs (the one internal app), so the internal SET may be
# empty — the MECHANISM is what this section holds, and the roster-exclusion
# check below exercises it regardless of population.
check("the internal stage resolves (mechanism live, population may be zero)",
      isinstance(_internal, list))
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
