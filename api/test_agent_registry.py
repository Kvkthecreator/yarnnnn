"""The agent-registry ratchet — ADR-460 D3.a's cliff, on the ADR-600 register.

Script-style (run: cd api && python3 test_agent_registry.py).

What this gate holds, post-ADR-600 (one register; hireability is a field):

  1. There is ONE register. The three-dict split is DELETED, not aliased —
     a re-appearing KERNEL_AGENTS/KERNEL_POSTURES/APP_RESIDENTS (or a
     `_kernel_character` union) is the exact shape that produced two dead
     planners and a vacuous ratchet, so it must re-open the ADR.
  2. The member-agent machinery STAYS DELETED — the symbols do not import,
     and the /lane-agents doors are gone from the routes.
  3. THE CLIFF: a row carries identity + character + engine + `offered` +
     `kernel` (provenance, ADR-601 D2 — descriptive, never authority) and
     nothing else — no authority-shaped key, no tools, no based_on. The
     whitelist itself contains no authority vocabulary. `offered` is REACH
     (who may be invited), never authority (what they may do).
  4. Every being is routable and priced (the ADR-439 §4 rule), and the
     roster is the FIELD's filter — list_agents() serves exactly the
     offered rows (empty today, per ADR-599 D1).
  5. Machinery resolves a BEING, never a container (ADR-600 D4): no call
     site subscripts the register by name.
  6. The cast door gates on `offered`, not on bare resolvability (D3).
  7. Provenance is a field, and `assert_editable` is the chokepoint that
     refuses a kernel being WITH ITS REASON — built before its door
     (ADR-601 D3), so it is gated rather than merely absent.
  8. Promotion is DERIVED from the desks a being serves (ADR-602 D3) — a
     being whose only desk is unpromoted waits with it, and promoting the
     app promotes the being with no second edit.
  9. A bound lane names its RESIDENT, not its engine (ADR-602 D5) — both
     authoring surfaces resolve through the beings roster.
 10. The /agents surface shows beings sectioned by where they live (D6),
     rendering provenance and desks from SERVED FIELDS (ADR-601 D4), with a
     per-being page at the sanctioned depth param (ADR-602 D6).
"""

from __future__ import annotations

import ast
import inspect
import re
import sys
from pathlib import Path

API = Path(__file__).resolve().parent
sys.path.insert(0, str(API))

from services.agents_registry import (  # noqa: E402
    AGENT_ROW_KEYS,
    AGENTS,
    NotEditable,
    assert_editable,
    homes_for_agent,
    is_promoted,
    list_agents,
    model_for_agent,
    resolve_agent,
)
from services.lane_runner import LANE_MODELS, unpriced_lane_model  # noqa: E402

PASS = 0
FAIL = 0


def _check(label: str, cond: bool) -> None:
    global PASS, FAIL
    tag = "✓" if cond else "✗"
    print(f"  {tag} {label}")
    if cond:
        PASS += 1
    else:
        FAIL += 1


print("1. one register, no containers (ADR-600 D1)")
import services.agents_registry as _reg  # noqa: E402
for _dead in ("KERNEL_AGENTS", "KERNEL_POSTURES", "APP_RESIDENTS",
              "RESIDENT_ROW_KEYS", "POSTURE_ROW_KEYS", "_kernel_character"):
    _check(f"{_dead} is deleted, not aliased", not hasattr(_reg, _dead))
_check("the roster is a FILTER over the one register, not a second namespace",
       list_agents() == [r for r in AGENTS.values() if r.get("offered")])
_check("nobody is offered today (ADR-599 D1, unreopened)",
       list_agents() == [])
_check("a deleted colleague slug resolves None (honest, not aliased)",
       resolve_agent("sonnet") is None and resolve_agent("scout") is None
       and resolve_agent("critic") is None)
_check("resolution reaches EVERY being — `offered` gates the invite, not the read",
       all(resolve_agent(s) is not None for s in AGENTS))

print("2. the member-agent machinery stays deleted (ADR-599 D2)")
for _sym in ("find_member_agents", "find_agent_skills", "parse_agent_manifest",
             "build_skills_section", "AGENT_MANIFEST_BASENAME"):
    try:
        import services.agents_registry as _reg
        _gone = not hasattr(_reg, _sym)
    except Exception:
        _gone = False
    _check(f"{_sym} does not exist", _gone)
_lanes_src = (API / "routes" / "lanes.py").read_text()
_check("the /lane-agents doors are gone from the routes",
       '"/lane-agents"' not in _lanes_src and "'/lane-agents'" not in _lanes_src)
_check("resolution is kernel-only — resolve_agent(slug) takes no member list",
       list(inspect.signature(resolve_agent).parameters) == ["slug"])

print("3. the cliff on the surviving register (ADR-460 D3.a, unweakened)")
banned = (
    "tools", "authority", "permission", "approve", "autonomy", "budget",
    "autonomous", "unattended", "standing_intent", "mandate", "wake",
    "principal", "grant", "scopes",
)
_check("AGENT_ROW_KEYS contains no authority-shaped key",
       not any(w in " ".join(AGENT_ROW_KEYS).lower() for w in banned))
for r in AGENTS.values():
    _check(f"'{r['slug']}' carries no key outside AGENT_ROW_KEYS",
           set(r.keys()) <= AGENT_ROW_KEYS)
    _check(f"'{r['slug']}' carries every required key",
           {"slug", "name", "blurb", "icon", "model", "token_profile",
            "posture", "offered", "kernel"} <= set(r.keys()))
    _check(f"'{r['slug']}' is self-contained (no based_on — ADR-599 D3)",
           "based_on" not in r)
    _check(f"'{r['slug']}' declares reach as a bool, not a string",
           isinstance(r["offered"], bool))
    _check(f"'{r['slug']}' declares provenance as a bool, not a string",
           isinstance(r["kernel"], bool))
    keys = " ".join(r.keys()).lower()
    _check(f"'{r['slug']}' has no authority-shaped field",
           not any(w in keys for w in banned))

print("4. every being is routable and priced")
for r in AGENTS.values():
    _check(f"'{r['slug']}' routes a live engine with a billing rate",
           r["model"] in LANE_MODELS and not unpriced_lane_model(r["model"]))
    _check(f"model_for_agent('{r['slug']}') answers",
           model_for_agent(r["slug"]) == r["model"])
# ADR-603 — Supervisor joins. The set is pinned deliberately (a new being is
# an ADR decision, not a drive-by), and it is EDITED here when one lands —
# which is the point: this line is where the roster's growth gets noticed.
_check("the expected beings are exactly {designer, editor, keeper, supervisor}",
       set(AGENTS) == {"designer", "editor", "keeper", "supervisor"})
# ADR-602 D1/D2 — the craft split, asserted as the RELATION not a spelling.
_check("Editor serves BOTH authoring desks (slides + text)",
       set(homes_for_agent("editor")) == {"slides", "text"})
_check("Designer keeps generation only (images)",
       homes_for_agent("designer") == ["images"])
_check("each being's icon is distinct (the crafts read apart at a glance)",
       len({r["icon"] for r in AGENTS.values()}) == len(AGENTS))

print("5. machinery resolves a BEING, never a container (ADR-600 D4)")
# The pattern that broke: a call site subscripting the register by name.
# `designer` moved containers in ADR-599 and two planners KeyError'd into a
# permanent silent fallback. Resolution has one door; reaching past it is the
# bug, so the gate refuses the shape rather than the symptom.
_planners = {
    "services/apps/images/decompose.py": "IMAGES layer plan",
    "services/studio_arrangement_plan.py": "Slides arrangement plan",
}
for _rel, _what in _planners.items():
    _src = (API / _rel).read_text()
    _check(f"{_what} resolves through resolve_agent",
           'resolve_agent("designer")' in _src)
    _check(f"{_what} never subscripts a register by name",
           "AGENTS[" not in _src and "KERNEL_AGENTS" not in _src)
# ...and the lookup sits OUTSIDE the try, so a missing being RAISES instead of
# masquerading as "the router is off" (each file's own comment says so).
for _rel, _what in _planners.items():
    _src = (API / _rel).read_text()
    # `.find`, never `.index` — a moved anchor must read as a RED CHECK, not a
    # gate crash that hides which check failed (audited 2026-08-24).
    _lookup = _src.find('resolve_agent("designer")')
    _imp = _src.find("from services.model_router")
    _try = _src.find("    try:", _imp) if _imp != -1 else -1
    _check(f"{_what}: the lookup precedes the try (a missing being raises)",
           _lookup != -1 and _try != -1 and _lookup < _try)

# Whole-tree sweep: no OTHER module may subscript the register either, and
# the deleted container names must not come back as CODE. Comments are
# excluded deliberately — the registry's own docstring names what it deleted,
# and a gate that cannot tell prose from code teaches sessions to reword
# rather than to fix.
_offenders = []
for _py in list((API / "services").rglob("*.py")) + list((API / "routes").rglob("*.py")):
    if _py.name == "agents_registry.py":
        continue
    for _i, _line in enumerate(_py.read_text().splitlines(), 1):
        _code = _line.split("#", 1)[0]
        if "AGENTS[" in _code or "KERNEL_AGENTS" in _code or "APP_RESIDENTS" in _code:
            _offenders.append(f"{_py.relative_to(API)}:{_i}")
_check(f"no module subscripts the register or names a deleted container "
       f"(found: {_offenders or 'none'})", not _offenders)

print("6. the cast door gates on `offered`, not on resolvability (ADR-600 D3)")
_add_door = _lanes_src[_lanes_src.index('elif kind == "agent":'):]
_add_door = _add_door[:_add_door.index("result = add_participant")]
_check("the door reads `offered` before admitting a being",
       '.get("offered")' in _add_door)
_check("a housed being is refused with its reason, not a generic miss",
       "works at a desk" in _add_door)

print("7. provenance is a field, and the edit door is a GATE (ADR-601 D2/D3)")
_check("every being today is kernel-authored (no member beings yet)",
       all(r["kernel"] for r in AGENTS.values()))
# The chokepoint refuses, and says WHY — a generic no reads as a bug and sends
# the member hunting a permission they cannot grant.
for _slug in AGENTS:
    try:
        assert_editable(_slug)
        _ok, _msg = False, "admitted"
    except NotEditable as _e:
        _ok, _msg = True, str(_e)
    _check(f"assert_editable('{_slug}') refuses a kernel being", _ok)
    _check(f"...and names it and the reason",
           AGENTS[_slug]["name"] in _msg and "not editable" in _msg)
# Fails CLOSED: an unknown slug is refused, never treated as member-authored.
try:
    assert_editable("no-such-being")
    _closed = False
except NotEditable:
    _closed = True
_check("assert_editable fails closed on an unknown slug", _closed)
# ...and a member-authored being WOULD pass — the gate is a filter on
# provenance, not a blanket refusal that happens to look right today.
import services.agents_registry as _r
_r.AGENTS["_probe"] = dict(_r.AGENTS["editor"], slug="_probe", kernel=False)
try:
    _passes = assert_editable("_probe")["slug"] == "_probe"
except NotEditable:
    _passes = False
finally:
    del _r.AGENTS["_probe"]
_check("a member-authored being passes the same gate", _passes)

# Reading is NEVER gated — a kernel being must resolve for its own lanes to run.
_check("provenance gates the WRITE only (resolve_agent still answers)",
       all(resolve_agent(s) is not None for s in AGENTS))

# ADR-601 D1 — homes is a LIST, resolved from the registrations.
_check("homes_for_agent returns a list per being",
       all(isinstance(homes_for_agent(s), list) for s in AGENTS))
# Asserted as the RELATION, never a named being: which being serves two desks
# is a product decision that moves (it was designer until ADR-602, now editor),
# and a gate pinning the name reports an ordinary re-pairing as a violation.
_check("many-to-one is live in the data (some being serves >1 desk)",
       any(len(homes_for_agent(s)) > 1 for s in AGENTS))

print("8. promotion is derived from the desks a being serves (ADR-602 D3)")
import services.apps  # noqa: E402,F401  (registration side-effect)
from services.app_stage import launcher_tier_for  # noqa: E402
import services.kernel_surfaces as _ks  # noqa: E402

_tier = {e["slug"]: launcher_tier_for(e) for e in _ks.KERNEL_SURFACES if e.get("slug")}
_check("IMAGES is unpromoted today (the fact this derivation reads)",
       _tier.get("images") != "primary")
_check("Designer waits with its only desk", not is_promoted("designer"))
_check("Editor is promoted (slides + text are both primary)", is_promoted("editor"))
_check("Keeper is promoted (strings is primary)", is_promoted("keeper"))
# The derivation must FOLLOW the registry, not a copy of it: promoting the app
# must promote the being with NO edit here. Proven by moving the app's stage.
#
# ⚠️ Re-anchored 2026-08-26: this moved `launcher_tier`/`default_pinned`, which
# stopped working the day app rows began DECLARING a stage — a declared stage
# WINS over the pair, so the mutation was silently ignored and the check read
# "promoting the app does not promote its being". Move the STAGE, which is now
# the single declaration (ADR-592); the pair is derived FROM it.
_img = next(e for e in _ks.KERNEL_SURFACES if e.get("slug") == "images")
_saved = _img.get("stage")
_img["stage"] = "primary"
try:
    _follows = is_promoted("designer")
finally:
    if _saved is None:
        _img.pop("stage", None)
    else:
        _img["stage"] = _saved
_check("promoting the app promotes its being (derived, not copied)", _follows)
_check("...and the restore held (designer is withheld again)",
       not is_promoted("designer"))
# Presentation only — the cliff is untouched.
_check("promotion never gates resolution (the being still answers)",
       resolve_agent("designer") is not None)
# The payload is what the pane reads: an unpromoted being must not be served.
import routes.lanes as _L  # noqa: E402
_served = {b["slug"] for b in _L._beings_payload()}
_check("the payload withholds an unpromoted being",
       "designer" not in _served and {"editor", "keeper"} <= _served)
# Fail CLOSED on the unhoused (ADR-602 D3 as amended 2026-08-24): a NON-offered
# being with no desk is unreachable everywhere — a deleted app REGISTRATION
# must withhold its orphaned resident, never leak it onto the pane. An OFFERED
# being with no desk is the roster's normal state and stays promoted.
_r.AGENTS["_orphan"] = dict(_r.AGENTS["editor"], slug="_orphan", offered=False)
_r.AGENTS["_colleague"] = dict(_r.AGENTS["editor"], slug="_colleague", offered=True)
try:
    _check("an unhoused NON-offered being is withheld (fail closed)",
           not is_promoted("_orphan"))
    _check("an unhoused OFFERED being stays promoted (a colleague has no desk)",
           is_promoted("_colleague"))
finally:
    del _r.AGENTS["_orphan"], _r.AGENTS["_colleague"]
# The apps payload obeys the exposure rule (ADR-592): `stage: internal` (or a
# missing surface row — fail closed) means absent from the served envelope.
# No live app is internal today (the supervisor app is DELETED, ADR-604 D3),
# so the filter is exercised by PROBE — a registered app with no surface row
# must be withheld, or the check is green only because nothing tests it.
import services.authoring as _authoring
_authoring.register_app("_probe-internal", resident="editor")
try:
    _served_apps = {a["slug"] for a in _L._apps_payload()}
    _check("the apps payload withholds an app with no exposed surface (fail closed)",
           "_probe-internal" not in _served_apps
           and {"slides", "text", "strings"} <= _served_apps)
finally:
    _authoring._APP_REGISTRY.pop("_probe-internal", None)
_check("no `supervisor` app survives to serve (ADR-604 D3 — strings is its desk)",
       "supervisor" not in {a["slug"] for a in _L._apps_payload()})

print("8b. the desk's two roles are both served (ADR-604)")
_check("supervisor's home is strings — the voice (ADR-604 D1)",
       homes_for_agent("supervisor") == ["strings"])
_check("keeper's home is strings — the standing executor (ADR-604 D2/D4)",
       homes_for_agent("keeper") == ["strings"])
_check("both roles are promoted with the desk",
       is_promoted("supervisor") and is_promoted("keeper"))
_served2 = {b["slug"] for b in _L._beings_payload()}
_check("the beings payload serves BOTH halves of the desk",
       {"supervisor", "keeper"} <= _served2)

print("9. a bound lane names its RESIDENT, not its engine (ADR-602 D5)")
# The bug: both authoring surfaces resolved the speaker through `agents` (the
# HIRE roster, empty since ADR-599) and through `apps[].name` (the RENAME
# override, empty for slides/text) — so both missed and fell through to the
# ENGINE label. A member working with Editor read "Message Claude Sonnet 4.6…".
# A resident is not a hire; it was never going to be on that roster.
_WEB = API.parent / "web" / "components"
# EVERY speaker-resolution surface, not a hand-picked pair: DeskHousing mounts
# the Strings + Text desks and carried this exact defect unexamined until the
# 2026-08-24 audit — a coverage set that is hand-spelled is the ADR-559
# vacuity class one layer up. A new desk chrome that resolves a speaker gets a
# row HERE in the commit that adds it.
for _rel, _what in (("authoring/StudioSurface.tsx", "Slides"),
                    ("text/TextEditor.tsx", "Text"),
                    ("desk/DeskHousing.tsx", "Desk housing (Strings/Text)")):
    _src = (_WEB / _rel).read_text()
    _check(f"{_what} reads the beings roster for its speaker label",
           "res.beings" in _src or "env.beings" in _src)
    # `.index` raises when the lookup is gone — a CRASH is not a clean red, and
    # a gate that traps instead of reporting hides which check failed.
    _lookup, _fallback = _src.find("beings.find"), _src.find("return modelLabel")
    _check(f"{_what} resolves the being BEFORE falling back to the engine",
           _lookup != -1 and _fallback != -1 and _lookup < _fallback)
    # ADR-602 D7 — the surface resolves from ITS OWN app first. A pre-567 lane
    # has no `app` stamp, so trusting only `boundLane.agent` left the composer
    # naming the engine. A surface cannot be wrong about which app it is.
    _check(f"{_what} resolves the resident from its own app registration",
           "?.resident" in _src)

print("10. the surface shows beings, sectioned by where they live (ADR-600 D6)")
_surface = (API.parent / "web" / "components" / "agents" / "AgentsSurface.tsx").read_text()
# (A former check asserted "ADR-600 in the file" — satisfied solely by the
# header comment, in direct tension with the no-ADR-in-copy check below.
# Dropped 2026-08-24: a check a comment can satisfy verifies nothing.)
_check("no hire machinery survives on the surface",
       "makeAgent" not in _surface and "AgentCard" not in _surface)
# The failure this section replaces: the predecessor hardcoded "Designer in
# Slides, Editor in Text, Keeper in Strings" in PROSE, so a fourth being would
# silently never appear. Server-driven or it drifts (the ADR-562 second home).
# Comments stripped first: this file's own docstring quotes the copy it
# replaced, and a gate that cannot tell prose from code teaches sessions to
# reword rather than to fix (the same lesson as the register sweep above).
import re as _re
# Strip BOTH comment spellings before asserting: block comments (/** … */,
# leading `*`), line comments (`//`), and JSX comment nodes ({/* … */}). The
# ADR-600/601/602 arc hit the prose-vs-code trap three times — a gate that
# cannot tell a comment from a rendered string teaches sessions to reword
# rather than to fix.
_surface_code = _re.sub(r"\{/\*.*?\*/\}", "", _surface, flags=_re.DOTALL)
_surface_code = "\n".join(
    _re.sub(r"//.*$", "", l) for l in _surface_code.splitlines()
    if not l.lstrip().startswith(("*", "/*", "//"))
)
_check("the roster is read from the server, not hardcoded in copy",
       "res.beings" in _surface_code and "api.lanes" in _surface_code)
# Every being's display name, FROM the register — a literal tuple here missed
# Supervisor the day it landed (audited 2026-08-24).
for _name in sorted({_b["name"] for _b in AGENTS.values()}):
    _check(f"the surface does not hardcode '{_name}'", _name not in _surface_code)
_check("both sections exist — housed beings and the offered roster",
       "In an app" in _surface_code and "To work with" in _surface_code)
# ADR-601 D4 — rendered from the FIELDS, never inferred.
_check("the surface renders provenance from the served field",
       "b.kernel" in _surface_code)
# The point is the PLURAL — many-to-one is ordinary (ADR-601 D1), so a surface
# rendering "the home" would assert the opposite of the architecture.
# Re-anchored 2026-08-26: the desks now render through `homeNames()`, which
# prefers the served TITLES and falls back to the slugs. Pinning the old
# `b.homes` spelling would have pinned the ADDRESS being shown to a person —
# the very thing that change fixed. Assert the plural SOURCE and the absence of
# a singular spelling, not one call site's text.
_check("the surface renders the desk LIST, not a single home",
       ("b.homes" in _surface_code or "homeNames(" in _surface_code)
       # `(?!s)` — any bare `b.home` spelling (`b.home}`, `b.home?`) trips it;
       # the old trailing-space match let those through.
       and not _re.search(r"\bb\.home(?!s|_titles|Names)", _surface_code))
# The titles are PREFERRED but never required — a payload predating
# `home_titles` must still render the desks rather than an empty line.
_check("the desk names fall back to the slugs when titles are absent",
       "home_titles?.length ? " in _surface_code
       and ": being.homes" in _surface_code or ": b.homes" in _surface_code
       or "being.homes" in _surface_code)
# ADR-602 D6 — the per-being page. Depth rides the SANCTIONED param and moves
# via setSurfaceParams (a pathname flip trips the shell's foreground effects).
# Both halves: the component must be DEFINED and RENDERED. Checking only the
# usage passed when the definition was renamed away (falsifier F1) — a call
# site to a missing symbol is a build error, but the gate should not depend on
# the compiler to notice a deleted feature.
_check("a being's page exists (list/detail)",
       "function BeingDetail" in _surface_code and "<BeingDetail" in _surface_code)
_check("depth moves via setSurfaceParams, never a pathname flip",
       "setSurfaceParams" in _surface_code and "router.push" not in _surface_code)
_check("the page STATES editability rather than leaving it implied",
       "Editing" in _surface_code)
# ADR-602 D5 — plain language. An ADR number is an internal address; a member
# reading one learns nothing they can act on.
_check("no ADR number is shown to a member on this surface",
       "ADR-" not in _surface_code)
for _r in AGENTS.values():
    _check(f"'{_r['slug']}' blurb is terse plain language (<= 60 chars)",
           len(_r["blurb"]) <= 60)
# The anti-pattern ratchet (kept from the original gate): the surface must
# never grow the ChatGPT business-agent editor's authority vocabulary.
_check("the surface carries no authority vocabulary",
       "Write action safety" not in _surface and "Never ask" not in _surface)

# The registry module itself: no function may WRITE — the kernel corpus is
# code, and a write path here would be the ADR-449 posture violated at the
# root. (AST: no attribute call named `insert`/`update`/`upsert`.)
_tree = ast.parse((API / "services" / "agents_registry.py").read_text())
_writes = [
    n for n in ast.walk(_tree)
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
    and n.func.attr in ("insert", "update", "upsert", "delete")
]
_check("the registry module has no write path", not _writes)

# Every icon the register declares must exist in the surface's ICONS map.
# A missing key does NOT error — BeingIcon falls back to `Bot`, so the being
# renders looking like an unmapped generic. Supervisor shipped that way:
# the register said `clipboard-list`, the map had three keys, and the pane
# showed the fallback glyph with nothing anywhere going red.
# Derived from the register, never a hand-kept list — a hand-kept copy is the
# same drift one level up.
_icon_map_block = _surface.split("const ICONS", 1)[-1].split("};", 1)[0]
_missing_icons = sorted(
    {row["icon"] for row in AGENTS.values() if row.get("icon")}
    - {
        key
        for key in re.findall(r"^\s*'?([a-z-]+)'?\s*:", _icon_map_block, re.M)
    }
)
_check(
    f"every registry icon is mapped in the surface (unmapped: {_missing_icons or 'none'})",
    not _missing_icons,
)

print()
if FAIL:
    print(f"FAIL: {PASS}/{PASS + FAIL} checks")
    sys.exit(1)
print(f"PASS: {PASS}/{PASS} checks")
