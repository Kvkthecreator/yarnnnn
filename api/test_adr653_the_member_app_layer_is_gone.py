"""ADR-653 — the member-authored app layer is GONE, and the composed surface SURVIVES.

Script-shaped: run it and READ THE COUNT. A pytest-shaped gate run as a script
exits green having collected nothing (the ADR-645 lesson), so this one prints
every check and returns a count.

    cd api && python3 test_adr653_the_member_app_layer_is_gone.py

WHY THIS GATE REPLACES `test_adr653_app_is_a_program.py` (185 checks, deleted
with the feature). ADR-653 shipped a member-authored app layer: a member wrote
`apps/{slug}/_app.yaml`, it became a surface, and its agent ran a lane. The
operator re-scoped 2026-09-18 — **one app, one agent (the supervisor and its
app), and the app-builder is postponed indefinitely** — and ruled that app a
KERNEL app (code, like Slides and Text). A member authors no app, so every
member-authored mechanism has ZERO tenants and was deleted rather than left
dormant (the 8 "registered, no live surface" primitives are the standing
example of what dormancy costs).

⭐ THE DIVISION THIS GATE HOLDS, and it is the whole point:

    DELETED — the member-AUTHORED layer (a member writes a declaration)
    KEPT    — the COMPOSED-SURFACE layer (a surface whose shape is DECLARED)

They are separable because `is_composition()` reads the REGISTER FIELD, never
the app's provenance. A KERNEL row may declare `register: "composition"`, so
the supervisor app inherits D3.a unchanged. This gate asserts BOTH halves: a
session that re-adds member-app machinery goes red, and a session that deletes
the composition register as "unused" goes red too.

⚠️ FALSIFIED IN BOTH DIRECTIONS before it shipped.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, ".")

_API = Path(__file__).resolve().parent
_WEB = _API.parent / "web"

_passed = 0
_failed = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global _passed, _failed
    if ok:
        _passed += 1
        print(f"  ✓ {label}")
    else:
        _failed += 1
        print(f"  ✗ {label}{(' — ' + detail) if detail else ''}")


def _read(root: Path, rel: str) -> str:
    p = root / rel
    return p.read_text() if p.exists() else ""


def _strip_comments_py(src: str) -> str:
    return re.sub(r"(?m)^\s*#.*$", "", src)


def _strip_comments_ts(src: str) -> str:
    """TS source with comments removed — LINE comments first, and that order
    is the whole correctness of this function.

    ⚠️ A naive block-strip (`/\*.*?\*/` with DOTALL) run FIRST is catastrophic
    and silent: a literal `/*` inside a string or a glob — `client.ts` contains
    `/*.md)` in a comment — opens a fake span that swallowed **37,491
    characters**, a third of the file. Every check reading the result then
    scanned a hole and passed for the wrong reason. Caught here by a check
    going red against code that was correct.

    Stripping LINE comments first removes the `/*` that live inside them, which
    is where all of this file's false openers are. A block comment that opens
    and closes on its own lines still goes.
    """
    src = re.sub(r"(?m)^\s*//.*$", "", src)
    return re.sub(r"(?m)^\s*/\*.*?\*/\s*$", "", src, flags=re.DOTALL)


# =============================================================================
print("\n[1] The member-authored layer is DELETED — no file, no route, no caller")
# =============================================================================

for rel in ("services/member_apps.py", "routes/member_apps.py"):
    check(f"{rel} is gone", not (_API / rel).exists())

for rel in ("components/apps/AppSurface.tsx",
            "components/apps/AppSection.tsx",
            "app/(authenticated)/apps/[slug]/page.tsx"):
    check(f"web/{rel} is gone", not (_WEB / rel).exists())

# ⚠️ A DELETED MODULE WITH A SURVIVING IMPORT is a 500 waiting for its first
# caller. Assert the absence at every site that used to reach it.
_py_importers = []
for p in _API.rglob("*.py"):
    if "venv" in p.parts or ".venv-mcp" in p.parts:
        continue
    if p.name == Path(__file__).name:
        continue
    if "member_apps" in p.read_text():
        _py_importers.append(str(p.relative_to(_API)))
check("no python file references member_apps", not _py_importers, str(_py_importers))

check("the /api/apps router is unmounted",
      "member_apps" not in _read(_API, "main.py"))

# The composition resolver no longer reads declarations.
_res = _strip_comments_py(_read(_API, "services/composition_resolver.py"))
check("the resolver has no member-app branch",
      "_resolve_member_app_surfaces" not in _res)

# The lane door resolves through the KERNEL registry only.
_lanes = _strip_comments_py(_read(_API, "routes/lanes.py"))
check("the lane door reads no declaration", "read_member_app" not in _lanes)
check("the lane door builds no member agent row", "agent_row(" not in _lanes)
check("an unknown app is still REFUSED, not defaulted",
      "Unknown app:" in _lanes, "the ADR-548 posture must survive the deletion")

_frame = _strip_comments_py(_read(_API, "services/lane_runner.py"))
check("the lane frame resolves no member character", "read_member_app" not in _frame)

_reg = _strip_comments_py(_read(_API, "services/agents_registry.py"))
check("build_agent_posture takes no injected row", "row: Optional[dict]" not in _reg)
# It existed ONLY because a member row carried no engine; every kernel row does.
check("default_agent_engine is gone with its reason",
      "def default_agent_engine" not in _reg)

_ts = _strip_comments_ts(_read(_WEB, "types/surface.ts"))
for sym in ("isOpenableSurfaceSlug", "appSurfaceSlugs", "appSlugFromPath",
            "appRoute", "isAppSurface", "APP_ROUTE_PREFIX", "AppSurfaceSlug"):
    check(f"web: {sym} is gone", sym not in _ts)

_mw = _strip_comments_ts(_read(_WEB, "lib/supabase/middleware.ts"))
# ⚠️ The auth list must not keep a prefix for a namespace that no longer
# exists — a protected route with no page is a fossil, and this file's own
# history is a list that grew them.
check("the /apps namespace prefix left the auth gate WITH its route",
      "APP_NAMESPACE_PREFIX" not in _mw and '"/apps"' not in _mw)

_client = _strip_comments_ts(_read(_WEB, "lib/api/client.ts"))
check("the api client has no apps namespace",
      not re.search(r"^\s{2}apps:\s*\{", _client, re.MULTILINE))

_tiers = _strip_comments_ts(_read(_WEB, "lib/compositor/types.ts"))
_tier_union = _tiers[_tiers.index("export type SurfaceTier"):]
_tier_union = _tier_union[: _tier_union.index(";")]
check("SurfaceTier no longer carries 'app'", "'app'" not in _tier_union, _tier_union)

for rel in ("components/shell/Launcher.tsx",
            "components/shell/SurfaceViewport.tsx",
            "components/shell/chrome/TopBarSurface.tsx"):
    src = _strip_comments_ts(_read(_WEB, rel))
    check(f"{rel.split('/')[-1]} gates on the kernel slug again",
          "isOpenableSurfaceSlug" not in src and "isKernelSurfaceSlug" in src)

_sr = _strip_comments_ts(_read(_WEB, "components/shell/SurfaceRegistry.tsx"))
check("the surface registry resolves kernel components only",
      "resolveOpenableComponent" not in _sr and "resolveSurfaceComponent" in _sr)


# =============================================================================
print("\n[2] The COMPOSED-SURFACE layer SURVIVES — the supervisor app inherits it")
# =============================================================================

# ⭐⭐⭐ THE SEPARABILITY FACT. `is_composition` reads the FIELD, not who
# authored the app — which is why a KERNEL app can be a composition and why
# deleting the member layer did not take D3.a with it.
from services.kernel_surfaces import REGISTERS, is_composition  # noqa: E402

check("`composition` is still a validated register", "composition" in REGISTERS)
check("is_composition has a runtime reader", callable(is_composition))
check("it classifies by the FIELD", is_composition({"register": "composition"}))
check("...and fails CLOSED on anything else",
      not is_composition({"register": "application"}) and not is_composition({}))

# A KERNEL row may declare it — driven, because this is the claim the whole
# re-scope rests on.
_kernel_row = {
    "slug": "supervisor", "register": "composition", "stage": "primary",
    "launcher_tier": "primary", "title": "Supervisor", "archetype": "dashboard",
    "substrate_paths": [], "icon_key": "layout-grid", "default_pinned": True,
    "route": "/supervisor", "summary": "What is underway, and what needs you.",
}
check("a KERNEL row may declare composition", is_composition(_kernel_row))
check("...and its register is in the validated set",
      _kernel_row["register"] in REGISTERS)

from services.app_stage import is_exposed  # noqa: E402

check("...and such a row would reach the served roster", is_exposed(_kernel_row))

# The §10.3 typing repair is unrelated to apps and must not be swept out.
check("surfaces[] is still typed at the client boundary",
      "surfaces: Surface[];" in _client,
      "the endpoint's most load-bearing field had NO compile-time checking")

# The kernel's three-way lockstep is untouched — the union stayed CLOSED
# through both the addition and the deletion, which is why it still means
# something (ADR-653 §10.2's lesson).
_union = _ts[_ts.index("export type KernelSurfaceSlug ="):]
_union = _union[: _union.index(";")]
check("the kernel slug union is still a closed set of literals",
      "'chat'" in _union and "string" not in _union, repr(_union[:60]))


# =============================================================================
print("\n[3] The cliff is unmoved — nothing gained authority in the deletion")
# =============================================================================

from services.agents_registry import AGENTS, AGENT_ROW_KEYS  # noqa: E402

check("AGENT_ROW_KEYS is unchanged",
      AGENT_ROW_KEYS == frozenset(
          {"slug", "name", "blurb", "icon", "model", "token_profile",
           "posture", "offered", "kernel"}),
      str(sorted(AGENT_ROW_KEYS)))

for slug, row in AGENTS.items():
    extra = set(row) - AGENT_ROW_KEYS
    check(f"{slug!r} carries no key outside the whitelist", not extra, str(extra))
    for forbidden in ("tools", "reach", "scope", "grant", "permissions",
                      "mandate", "autonomy", "authority"):
        check(f"{slug!r} has no {forbidden!r} key", forbidden not in row)

# Every live agent is the kernel's own now — there is no data ingress for a
# member-authored row, and that is the re-scope stated as a fact.
check("every registered agent is kernel-authored",
      all(r.get("kernel") is True for r in AGENTS.values()),
      str({s: r.get("kernel") for s, r in AGENTS.items()}))



# =============================================================================
print("\n[4] ADR-656 — the composed surface has its FIRST TENANT, and it is drawn")
# =============================================================================

from services.kernel_surfaces import KERNEL_SURFACES  # noqa: E402

_sup = next((e for e in KERNEL_SURFACES if e["slug"] == "supervisor"), None)
check("the supervisor surface row exists", _sup is not None)
check("it declares the composition register", is_composition(_sup or {}))
check("...and it is the register's first live tenant",
      [e["slug"] for e in KERNEL_SURFACES if is_composition(e)] == ["supervisor"])

# ⚠️ THE THREE KEYS MOVE TOGETHER (stage · tier · route). Half a door is the
# empty-window class: a slug the client foregrounds and then cannot draw
# (`connectors`, ADR-653 §10.1). The stage gate caught exactly this on the
# first draft, so it is asserted here as a pairing rather than three facts.
_door = [bool(_sup.get(k)) for k in ("launcher_tier", "route")] if _sup else []
check("stage · tier · route agree — a whole door or none",
      (_sup or {}).get("stage") == "primary" and all(_door),
      str({k: (_sup or {}).get(k) for k in ("stage", "launcher_tier", "route")}))

# ⭐ The pin is DERIVED from the stage, never declared beside it — a row that
# disagreed with its own stage is the hand-kept drift the derivation ends.
from services.app_stage import is_default_pinned  # noqa: E402

check("the declared pin agrees with the derivation",
      bool((_sup or {}).get("default_pinned")) == is_default_pinned(_sup or {}))

# The FE half: the surface, its dispatch, and the honest miss.
_sec = _strip_comments_ts(_read(_WEB, "components/supervisor/SupervisorSection.tsx"))
check("the section dispatch exists", bool(_sec))
check("dispatch is by KIND", "switch (kind)" in _sec)
# ADR-666 D8: the vocabulary is running · needs-you · work · recent (read by
# RUN STATE); `threads` is DELETED (ADR-658 §2) and `note` is DELETED (ADR-666
# D8 — no writer, no workspace held one).
for _kind in ("running", "needs-you", "work", "recent"):
    check(f"the client draws {_kind!r}", f"case '{_kind}':" in _sec)
check("the client no longer draws `threads` (ADR-658 §2)", "case 'threads':" not in _sec)
check("the client no longer draws `note` (ADR-666 D8)", "case 'note':" not in _sec)

# ⚠️ An unknown kind renders the HONEST MISS, never a blank. Silence is the
# failure mode: a blank band reads as "this app has nothing" and a member
# cannot tell a limit from an emptiness.
_default = _sec[_sec.index("default:"):] if "default:" in _sec else ""
_default = _default[: _default.index("}")] if "}" in _default else _default
check("an unknown kind renders the honest miss",
      "<SectionMiss" in _default and "return null" not in _default)

# ⭐ THE GROWTH RULE, asserted rather than trusted: the vocabulary is what this
# app needs, NOT ADR-653's folder-shaped first cut carried over. `files` is
# deliberately absent — the supervisor owns no folder of work. `recent` returned
# with ADR-666 D8 as recent RUNS, and only as that: "what moved" is still the
# timeline's job (duplicating it is the "glorified redirect" ADR-435 deleted the
# last composition for being), so the band must read the run ledger and never
# the timeline.
check("the folder-shaped kind 'files' is NOT carried over", "case 'files':" not in _sec)
_recent = _sec[_sec.index("function RecentSection"):] if "function RecentSection" in _sec else ""
_recent = _recent[: _recent.index("\nfunction ", 1)] if "\nfunction " in _recent[1:] else _recent
check("`recent` is recent RUNS (ADR-666 D8) — the run ledger, never the timeline",
      "RunList" in _recent and "band.runs" in _recent and "timeline" not in _recent.lower())

_surf = _strip_comments_ts(_read(_WEB, "components/supervisor/SupervisorSurface.tsx"))
check("the surface renders DECLARED sections", "SECTIONS.map" in _surf)
check("band 2 names who is minding it", "looks after this." in _surf)
# ⭐ Resting is not an empty state. "Nothing is waiting on you" is a complete,
# reassuring sentence; "No items" says the same and reads like a failure.
check("the resting copy reassures rather than reporting absence",
      "Nothing is waiting on you." in _sec and "No items" not in _sec)

# The supervisor does the work of no thread: a mention opens as a NAVIGATION.
# (ADR-658 adds the standing-work verbs — create, pause, run, retire — which
# are acts on DECLARATIONS, never on beings.)
check("opening a mention navigates to chat",
      "navigateToSurface('chat'" in _surf)

_sup_ts = _strip_comments_ts(_read(_WEB, "types/surface.ts"))
check("the slug joined the FE union", "'supervisor'" in _sup_ts)
_client_ts = _strip_comments_ts(_read(_WEB, "lib/api/client.ts"))
check("the api client reads the app's state", "/api/supervisor/state" in _client_ts)

# =============================================================================
print("\n" + "=" * 70)
print(f"  {_passed} passed, {_failed} failed")
print("=" * 70)
print(
    "\n  The supervisor app (ADR-653's successor scope) is NOT built yet:\n"
    "    - services/apps/supervisor.py + its kernel surface row\n"
    "    - an AGENTS row for the supervisor\n"
    "    - memory with a writer and a reader\n"
    "    - routing (stamp a lane with its app)\n"
)
sys.exit(1 if _failed else 0)
