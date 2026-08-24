"""ADR-562 — an app's AI configuration is declared where the app lives.

THE DEFECT THIS GATE EXISTS FOR. Residency was declared on the CLIENT
(`web/lib/apps/authoring.ts`), asserted over the wire, and never read back —
so `StudioSurface` created a lane pinning Designer and then rendered
"Claude Sonnet is working…", because it dropped the served roster. The pin was
real and invisible: the `models[0]` incoherence ADR-460 removed, surviving one
layer up where nobody looked.

WHAT IS PINNED HERE
  §1  one declaration per app, in the app's own module — no second home
  §2  the door: `register_app` beside `register_layouts`, kernel imports no app
  §3  the D3.a cliff on this layer — an app row carries IDENTITY, never authority
  §4  create_lane DERIVES the resident; the client cannot assert one
  §5  the name reaches the member (the join StudioSurface used to drop)
  §6  no dual approach — the retired frontend table is gone, not orphaned

Run: python3 test_adr562_app_owned_config.py   (from api/)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

ROOT = Path(__file__).parent.parent
WEB = ROOT / "web"

_failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else '✗'} {label}")
    if not ok:
        _failures.append(f"{label}{f' — {detail}' if detail else ''}")


# The package import IS the registration (ADR-562 §2).
import services.apps  # noqa: E402,F401
from services.agents_registry import KERNEL_AGENTS, KERNEL_POSTURES  # noqa: E402
from services.authoring import (  # noqa: E402
    all_apps,
    register_app,
    resident_for_app,
    resolve_app,
)
from services.derive_recipes import DERIVE_RECIPES, resident_for_recipe  # noqa: E402

print("\n── 1. one declaration per app ──")

APPS = all_apps()
# Re-anchored for ADR-599: `studio` renamed `slides` (the full evolve, D4);
# `docs` DELETED with its app (D5 — was `stage: internal`); `radar` deleted
# by ADR-592. The live set is exactly the four desk apps.
check("every live app is registered (slides · images · text · strings)",
      set(APPS) == {"slides", "images", "text", "strings"},
      f"registered={sorted(APPS)}")
check("the deleted apps are NOT registered (radar — ADR-592; docs, studio — ADR-599)",
      not ({"radar", "docs", "studio"} & set(APPS)),
      f"registered={sorted(APPS)}")

check("a registration carries IDENTITY only — slug · resident · name",
      all(set(row) == {"slug", "resident", "name"} for row in APPS.values()),
      f"keys={ {k: sorted(v) for k, v in APPS.items()} }")

# §3 — THE CLIFF. An app pins a colleague; it can never widen one. There is no
# field for authority or reach, and the absence must stay STRUCTURAL (the
# ADR-460 D3.a pattern: unrepresentable, not merely unset).
_BANNED = {"tools", "authority", "autonomy", "grant", "scopes", "wake", "mandate"}
check("no authority/reach-shaped key exists on any app row (the D3.a cliff)",
      all(not (_BANNED & set(row)) for row in APPS.values()))

print("\n── 2. the door, and its one direction ──")

# Re-registering is idempotent: FIRST registration wins, matching
# `register_layouts`. A second claim must not silently re-point a live app.
register_app("slides", resident="keeper")
check("re-registration does NOT re-point a live app (first wins)",
      resident_for_app("slides") == "designer",
      f"got {resident_for_app('slides')}")

check("an unregistered app resolves to None, never a plausible default",
      resident_for_app("no-such-app") is None and resolve_app("no-such-app") is None)

# The kernel must never import an app — registration is the only direction.
_authoring_src = (ROOT / "api" / "services" / "authoring.py").read_text()
check("the kernel imports no app module (registration is one-directional)",
      "from services.apps" not in _authoring_src
      and "import services.apps" not in _authoring_src)

# The eager-registration property: resolving an app must not depend on which
# ROUTER happened to be imported first (the import-order hazard the re-home
# introduced, closed by making the package itself the registration point).
_apps_init = (ROOT / "api" / "services" / "apps" / "__init__.py").read_text()
check("the apps package registers every app at import (no router dependency)",
      "from services.apps import images" in _apps_init  # ADR-599: docs deleted
      and '_register_app("strings"' in _apps_init)

print("\n── 3. every declared resident is real ──")

# ADR-598 — residents live in their own register; still one resolution namespace.
from services.agents_registry import APP_RESIDENTS  # noqa: E402
_characters = set(KERNEL_AGENTS) | set(KERNEL_POSTURES) | set(APP_RESIDENTS)
for slug, row in sorted(APPS.items()):
    check(f"{slug} names a resolvable kernel character ({row['resident']})",
          row["resident"] in _characters)

# A recipe may declare its own colleague (the canvas-less derive lanes). Same
# rule: declared, resolvable, never client-asserted.
for slug in sorted(DERIVE_RECIPES):
    r = resident_for_recipe(slug)
    check(f"recipe {slug}: resident is absent or resolvable ({r or '—'})",
          r is None or r in _characters)

print("\n── 4. create_lane DERIVES the colleague ──")

_lanes = (ROOT / "api" / "routes" / "lanes.py").read_text()
_create = _lanes[_lanes.index("async def create_lane("):]
_create = _create[: _create.index("\n@router.")]

check("the request carries `app`, never `agent`",
      "app: Optional[str] = None" in _lanes and "agent: Optional[str] = None" not in _lanes)

check("the resident is resolved from the app's declaration",
      "resident_for_app(app_slug)" in _create)

check("a canvas-less derive lane takes the RECIPE's colleague",
      "resident_for_recipe(" in _create)

# A stale client (cached bundle → new API) must be REFUSED, never silently
# obeyed-by-nothing: dropping `agent` would create a bound lane with no
# resident and re-introduce the exact defect this ADR removes.
import routes.lanes as L  # noqa: E402

check("a stale `agent` field is REFUSED, not silently dropped",
      L.CreateLaneRequest.model_config.get("extra") == "forbid")

_refused = False
try:
    L.CreateLaneRequest(agent="designer", artifact_path="/workspace/x.html")
except Exception:
    _refused = True
check("…proven by construction (the model rejects it)", _refused)

# And the legitimate shapes still construct.
for kw in ({"model": "anthropic/claude-sonnet-5"},
           {"app": "slides", "artifact_path": "/workspace/x.html"},
           {"derive_recipe": "design-system", "derive_source": "/workspace/s.md"}):
    _ok = True
    try:
        L.CreateLaneRequest(**kw)
    except Exception:
        _ok = False
    check(f"…while a valid shape still constructs ({sorted(kw)[0]})", _ok)

print("\n── 5. the name reaches the member ──")

_studio = (WEB / "components" / "authoring" / "StudioSurface.tsx").read_text()
_studio_code = "\n".join(
    l for l in _studio.splitlines() if not l.lstrip().startswith(("//", "*", "/*"))
)
_panel = (WEB / "components" / "chat-surface" / "LanePanel.tsx").read_text()

# THE DEFECT, pinned: the surface must KEEP the served roster and JOIN it.
check("StudioSurface keeps the served agents roster (it used to drop it)",
      "setAgents((res.agents ?? [])" in _studio_code)
check("…and joins slug → name for the bound lane",
      "agents.find((a) => a.slug === slug)?.name" in _studio_code)
check("…and hands the panel a speaker label",
      "speakerLabel={laneLabel}" in _studio_code)

# The two facts must stay SEPARATE: who is working vs what the engine can do.
# RE-DERIVED 2026-08-14. This pinned `${speaker} is working…`, the lane-level
# string. ADR-495 D3 addressing made identity a fact about a MESSAGE — the
# per-message author is preferred and `speaker` remains the fallback for a lane
# with no cast — so the pin read a strictly-better spelling as a violation. The
# standing claim is unchanged: the indicator names WHO IS WORKING, never the
# engine (which is why the two checks below stay exactly as they were).
check("the panel renders the SPEAKER for 'is working…'",
      "is working…`" in _panel and "${modelLabel} is working" not in _panel)
check("…and keeps the ENGINE for the vision refusal (a model's limit)",
      "${modelLabel} cannot see images" in _panel)
check("…and keeps the ENGINE on the attribution receipt (`you via {model}`)",
      "you via ${modelLabel}" in _panel)

print("\n── 5b. ADR-562 D6 — an app may NAME its resident ──")

from services.authoring import resolve_app  # noqa: E402
from services.agents_registry import build_agent_posture  # noqa: E402

# Re-anchored for ADR-599: Docs (the one renaming app) is deleted; no live
# registration renames its resident today. The MECHANISM is exercised below
# with a literal as_name — the overlay must still state the override.
check("no live app renames its resident (slides/text/strings use the character's own name)",
      not any((resolve_app(s) or {}).get("name") for s in ("slides", "text", "strings")))

_docs_posture = build_agent_posture("designer", as_name="Writer")
_studio_posture = build_agent_posture("designer", as_name="")

# The rename must be an OVERRIDE, not an alias: the character text opens "You
# are Designer —" and the colleague INTRODUCES ITSELF by name (observed, the
# 2026-08-13 click-pass). Two live names would let the model pick the first.
check("the app rename OVERRIDES the character's name in the prompt",
      "you are called Writer" in _docs_posture
      and "not the one in the line above" in _docs_posture)
check("…and an un-renamed app adds no naming line at all",
      "called" not in _studio_posture)
# Same character either way — a name is not a taxonomy (ADR-460 D1).
check("…while the CHARACTER is identical (a name is not a character)",
      "You are Designer" in _docs_posture and "You are Designer" in _studio_posture)

# The app is DERIVED from the artifact's own bytes, never stored on the lane —
# so a document that changes hands cannot carry a stale label.
from services.authoring import app_for_layout, extract_template  # noqa: E402

check("the app derives from the artifact's data-template (never lane state)",
      # ADR-599: deck → slides; a legacy `document` template resolves None
      # (its app is deleted — creation gone, rendering kept by kernel CSS).
      app_for_layout(extract_template('<html data-template="deck">')) == "slides"
      and app_for_layout(extract_template('<html data-template="document">')) is None)

_lane_src = (ROOT / "api" / "services" / "lane_runner.py").read_text()
check("the frame reads the bound artifact ONCE (one round-trip, two consumers)",
      _lane_src.count("_read_workspace_file(client, user_id, artifact_path)") == 1)

# ⚠️ THE WIRING, not the derivation. Removing `as_name=` from the lane's call
# left this section GREEN on the first run — the resolver worked and nothing
# consumed it, which is the exact shape of the width-ladder defect (a gate
# testing a derivation nothing called). Assert the CALL.
check("the lane PASSES the app name into the posture (not just resolves it)",
      "as_name=_as_name" in _lane_src)
check("…and resolves it from the app registry, keyed by the artifact's app",
      "resolve_app(_app) or {}).get(\"name\")" in _lane_src)

# Served, never mirrored — a TS copy is the second home ADR-562 deleted.
check("the app registry is SERVED to the FE (no parallel TS table)",
      '"apps": _apps_payload()' in _lanes)
check("…and the surface resolves the app's name from it",
      "apps.find((a) => a.slug === app.slug)?.name" in _studio_code)

print("\n── 6. no dual approach ──")

check("the retired frontend residency table is DELETED",
      not (WEB / "lib" / "apps" / "authoring.ts").exists())
check("…and nothing still imports it",
      not any(
          "lib/apps/authoring" in p.read_text()
          for p in WEB.rglob("*.tsx")
          if "node_modules" not in str(p)
      ))

# No create site may name a colleague — comments stripped, else the assertion
# matches the very comment that explains the removal.
_calls = re.findall(r"api\.lanes\s*\.?\s*create\(\{(.*?)\}\)", _studio_code, re.DOTALL)
check("no lane-create site names a colleague (identity is server-derived)",
      bool(_calls) and not any(re.search(r"\bagent:\s*['\"]", c) for c in _calls),
      f"{len(_calls)} site(s)")

print()
if _failures:
    print(f"FAIL: {len(_failures)} check(s) failed")
    for f in _failures:
        print(f"  - {f}")
    sys.exit(1)
print("ADR-562 gate GREEN")
