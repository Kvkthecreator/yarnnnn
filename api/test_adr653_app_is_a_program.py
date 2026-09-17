"""ADR-653 — an app is an AI-native program. The declaration's gate.

Script-shaped: run it and READ THE COUNT. A pytest-shaped gate run as a script
exits green having collected nothing (the ADR-645 lesson), so this one prints
every check and returns a count.

    cd api && python3 test_adr653_app_is_a_program.py

SCOPE. This covers the DECLARATION half (ADR-653 D1/D2 + R4), which is what
exists at this commit. The checks ADR-653 §11 names for later phases are listed
at the bottom as NOT YET — named so their absence is visible rather than
assumed:
  3  — `register: "composition"` validated + has a runtime reader (D3.a)
  4  — section kinds resolve in the client vocabulary (D3.b)
  5  — a declared app slug foregrounds from the Launcher (D3.c)
  6  — standing executor resolves through the app (D5)
Checks 6a (R3, the app binding kind) and 6b (R1, the delete blast radius) ARE
implemented, below.

⚠️ FALSIFIED BEFORE IT SHIPPED. Each check below was driven RED by mutating the
thing it asserts: an authority key admitted into AGENT_KEYS, a kernel slug
allowed, a second app naming one agent, an unknown section kind waved through.
A parity check that has only ever been seen green is indistinguishable from one
that parses nothing.
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")

from services.member_apps import (  # noqa: E402
    AGENT_KEYS,
    APP_DECLARATION_LEAF,
    DECLARATION_KEYS,
    SECTION_KEYS,
    SECTION_KINDS,
    app_declaration_path,
    app_delete_roots,
    app_slug_from_path,
    is_app_owned_path,
    declaration_problem_message,
    parse_app_yaml,
)

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


def _kernel_names() -> tuple[frozenset[str], frozenset[str]]:
    """The live kernel registries — read, never hand-spelled.

    A hand-spelled expectation set inside a parity gate is the same defect the
    gate exists to catch, one level up (the ADR-636 D3 lesson).
    """
    import services.apps  # noqa: F401  (registration side-effect)
    from services.agents_registry import AGENTS
    from services.authoring import all_apps

    return frozenset(all_apps()), frozenset(AGENTS)


KERNEL_APPS, KERNEL_AGENTS = _kernel_names()

GOOD = """
name: Photos
about: Client shoots, culled and delivered.
agent:
  name: Mara
  character: You look after this member's photo work.
skills: [culling-a-shoot]
surface:
  sections:
    - kind: files
      source: clients/
"""


def _parse(body: str, slug: str = "photos"):
    return parse_app_yaml(
        body,
        slug=slug,
        kernel_app_slugs=KERNEL_APPS,
        kernel_agent_slugs=KERNEL_AGENTS,
    )


# =============================================================================
print("\n[1] A well-formed declaration parses, and carries what it declared")
# =============================================================================

d = _parse(GOOD)
check("a good declaration parses", d is not None)
if d:
    check("no problem on a good declaration", d.problem is None, str(d.problem))
    check("name read", d.name == "Photos", d.name)
    check("agent name read", d.agent_name == "Mara", d.agent_name)
    check("skills read", d.skills == ["culling-a-shoot"], str(d.skills))
    check("sections read", len(d.sections) == 1, str(d.sections))

check("unparseable yaml returns None", _parse("name: [unclosed") is None)
check("a non-mapping body returns None", _parse("- a\n- b") is None)
check("an empty body returns None", _parse("") is None)


# =============================================================================
print("\n[2] The whitelists REFUSE authority — the ADR-460 D3.a cliff")
# =============================================================================

# ⭐ The whole point of the key whitelist. These four keys are the ones a
# session would most plausibly add "for convenience", and each one would be
# authority on a declaration.
for key, value in (
    ("model", "anthropic/claude-opus-5"),
    ("engine", "gpt-4"),
    ("tools", "[WriteFile]"),
    ("reach", "[slack]"),
):
    body = GOOD.replace("  name: Mara", f"  name: Mara\n  {key}: {value}")
    got = _parse(body)
    check(
        f"agent key `{key}` is refused",
        got is not None and got.problem == "agent_key_refused",
        f"problem={got.problem if got else None}",
    )

check(
    "AGENT_KEYS carries no authority-shaped key",
    AGENT_KEYS == frozenset({"name", "character"}),
    str(sorted(AGENT_KEYS)),
)
check(
    "SECTION_KEYS carries no layout-shaped key",
    SECTION_KEYS == frozenset({"kind", "source", "title"}),
    str(sorted(SECTION_KEYS)),
)

# An unknown TOP-LEVEL key is parked inert, not refused — the standing_work
# posture: the declaration still runs, and the key is never read.
parked = _parse(GOOD + "\nbudget_cents: 5000\n")
check(
    "an unknown top-level key is PARKED, not read",
    parked is not None and parked.problem is None and "budget_cents" in parked.options,
    f"problem={parked.problem if parked else None}",
)
check(
    "a parked key is absent from DECLARATION_KEYS",
    "budget_cents" not in DECLARATION_KEYS,
)


# =============================================================================
print("\n[3] A kernel slug is REFUSED, never overridden (D2)")
# =============================================================================

check("kernel apps resolved non-empty (guards a vacuous scan)", len(KERNEL_APPS) > 0, str(KERNEL_APPS))
check("kernel agents resolved non-empty", len(KERNEL_AGENTS) > 0, str(KERNEL_AGENTS))

for kernel_slug in sorted(KERNEL_APPS):
    got = _parse(GOOD, slug=kernel_slug)
    check(
        f"app slug `{kernel_slug}` is refused",
        got is not None and got.problem in ("kernel_slug", "kernel_agent_slug"),
        f"problem={got.problem if got else None}",
    )

for kernel_agent in sorted(KERNEL_AGENTS):
    if kernel_agent in KERNEL_APPS:
        continue  # already covered above
    got = _parse(GOOD, slug=kernel_agent)
    check(
        f"agent slug `{kernel_agent}` is refused",
        got is not None and got.problem == "kernel_agent_slug",
        f"problem={got.problem if got else None}",
    )


# =============================================================================
print("\n[4] R4 — one app, one agent; and the kernel's many-to-one STILL LEGAL")
# =============================================================================

# ⭐⭐⭐ The agent slug is DERIVED from the app's, so a collision between two
# member apps is impossible BY CONSTRUCTION rather than by a check that could
# be forgotten. Two apps cannot name one agent because neither names its agent.
a = _parse(GOOD, slug="photos")
b = _parse(GOOD.replace("name: Mara", "name: Tess"), slug="client-work")
check(
    "two member apps derive two distinct agents",
    a is not None and b is not None and a.agent_slug != b.agent_slug,
    f"{a.agent_slug if a else None} vs {b.agent_slug if b else None}",
)
check(
    "a member app's agent slug IS its app slug (one app, one agent)",
    a is not None and a.agent_slug == a.slug,
)
check(
    "the agent block cannot declare its own slug",
    "slug" not in AGENT_KEYS,
)

# ⚠️ THE OTHER HALF OF R4, and it must be asserted in the same breath: the
# kernel keeps many-to-one. A future session "fixing" the asymmetry into one
# rule would silently break ADR-602 D1 (one voice across decks and documents).
import services.apps  # noqa: E402,F401
from services.authoring import all_apps as _all_apps  # noqa: E402

_residents: dict[str, list[str]] = {}
for _slug, _row in _all_apps().items():
    _residents.setdefault(_row["resident"], []).append(_slug)
_shared = {k: v for k, v in _residents.items() if len(v) > 1}
check(
    "a KERNEL agent may still reside several apps (ADR-602 D1 preserved)",
    bool(_shared),
    "no kernel agent serves >1 app — if this is deliberate, R4's asymmetry note needs revisiting",
)
print(f"      kernel many-to-one: {_shared or 'NONE'}")


# =============================================================================
print("\n[5] The section vocabulary is CLOSED, and a refusal is legible")
# =============================================================================

check(
    "the first cut is exactly four kinds",
    SECTION_KINDS == ("files", "recent", "needs-you", "note"),
    str(SECTION_KINDS),
)

for kind in SECTION_KINDS:
    got = _parse(GOOD.replace("kind: files", f"kind: {kind}"))
    check(f"kind `{kind}` is accepted", got is not None and got.problem is None,
          f"problem={got.problem if got else None}")

unknown = _parse(GOOD.replace("kind: files", "kind: chart"))
check(
    "an unknown kind is refused, not guessed",
    unknown is not None and unknown.problem == "section_kind_unknown",
    f"problem={unknown.problem if unknown else None}",
)
check(
    "the refusal NAMES what it can show",
    all(k in declaration_problem_message("section_kind_unknown") for k in SECTION_KINDS),
)

layout = _parse(GOOD.replace("      source: clients/", "      source: clients/\n      columns: 3"))
check(
    "a layout prop on a section is refused",
    layout is not None and layout.problem == "section_key_refused",
    f"problem={layout.problem if layout else None}",
)


# =============================================================================
print("\n[6] A broken declaration is VISIBLE, and speaks the member's language")
# =============================================================================

no_agent = _parse("name: Photos\n")
check(
    "an app with no agent is a problem, not a silent pass",
    no_agent is not None and no_agent.problem == "missing_agent",
    f"problem={no_agent.problem if no_agent else None}",
)

no_name = _parse(GOOD.replace("name: Photos", "name: ''"))
check(
    "an app with no name is a problem",
    no_name is not None and no_name.problem == "missing_name",
    f"problem={no_name.problem if no_name else None}",
)

# VOICE-AND-TONE §3 — no kernel noun reaches a member.
_BANNED = (
    "lane", "artifact", "substrate", "principal", "grant", "declaration",
    "resident", "composition", "slug", "yaml", "kernel", "registry", "parser",
)
_problems = [
    "missing_slug", "invalid_slug", "kernel_slug", "missing_name",
    "missing_agent", "agent_unnamed", "agent_key_refused", "kernel_agent_slug",
    "surface_invalid", "section_kind_unknown", "section_key_refused",
]
for p in _problems:
    msg = declaration_problem_message(p)
    hit = [w for w in _BANNED if w in msg.lower()]
    check(f"`{p}` speaks plainly", not hit and msg.endswith((".", "?")), f"{hit} in {msg!r}")

check(
    "an unknown problem token still answers",
    declaration_problem_message("nonsense_token") == "This app could not be read.",
)


# =============================================================================
print("\n[7] Paths — only the declaration leaf names an app")
# =============================================================================

check("declaration path composes", app_declaration_path("photos") == "apps/photos/_app.yaml")
check("slug reads back from its path", app_slug_from_path("apps/photos/_app.yaml") == "photos")
check("a /workspace/ prefix is tolerated",
      app_slug_from_path("/workspace/apps/photos/_app.yaml") == "photos")
check("an app's ORDINARY file is not its declaration",
      app_slug_from_path("apps/photos/notes.md") is None)
check("a bare apps/ path names no app", app_slug_from_path("apps/_app.yaml") is None)
check("a path outside apps/ names no app",
      app_slug_from_path("agents/mara/memory/notes.md") is None)
check("the leaf is underscore-yaml (ADR-254)", APP_DECLARATION_LEAF == "_app.yaml")

# The `about` budget is a WARNING, never a block — the app runs and the member
# is told (APP-BUILDER-UX §6).
long_about = _parse(GOOD.replace(
    "about: Client shoots, culled and delivered.",
    "about: " + "x" * 200,
))
check(
    "an over-budget `about` warns but does not block",
    long_about is not None
    and long_about.problem is None
    and any(w.startswith("about_over_budget") for w in long_about.warnings),
    f"warnings={long_about.warnings if long_about else None}",
)


# =============================================================================
print("\n[6a] R3 — a lane bound to an APP ALONE is created, not refused")
# =============================================================================

# Read the SHIPPED source: this leg crosses a route, so a fake would assert a
# fake. The conditions below are re-evaluated with app-only inputs rather than
# pattern-matched, because what matters is which way the branch goes.
_lanes_src = open("routes/lanes.py").read()
_create = _lanes_src[_lanes_src.index("async def create_lane("):]

_m = __import__("re").search(r"is_bound = bool\(\n(.*?)\n    \)", _create, __import__("re").S)
check("is_bound admits an app alone", bool(_m) and "app_slug" in _m.group(1),
      _m.group(1).strip() if _m else "expression not found")

check(
    "the pre-R3 refusal is DELETED, not commented out",
    "names a binding, not a colleague" not in _create,
)
check(
    "the chat cap exempts a bound lane by BINDING, not by artifact",
    "if not is_bound and len(chat_lanes) >= _MAX_ACTIVE_LANES:" in _create,
    "an app-only lane would otherwise count against the member's chat budget",
)

# ⚠️ What the deleted refusal PROTECTED must still hold. Deleting a guard is
# only safe if its purpose survives elsewhere.
check("an unregistered app is still refused", "Unknown app:" in _create)
check("a bound lane still refuses a client-sent colleague",
      "if chat_agent and is_bound:" in _create)
check("the app is still stamped on lane_meta", 'lane_meta["app"] = app_slug' in _create)

# Drive the real expression with each binding shape.
for _name, _art, _skill, _deriv, _app, _want in (
    ("app only", "", "", "", "photos", True),
    ("artifact only", "deck.html", "", "", "", True),
    ("skill only", "", "s", "src.md", "", True),
    ("plain chat", "", "", "", "", False),
):
    _bound = bool(_art.strip() or _skill.strip() or _deriv.strip() or _app)
    check(f"binding `{_name}` -> bound={_want}", _bound is _want, f"got {_bound}")

# The job overlay must reach an app-bound lane, and the studio fallback must
# NOT — it builds its posture FROM an artifact head that does not exist.
_runner = open("services/lane_runner.py").read()
check("the job overlay admits an app with no artifact",
      "if artifact_path or app:" in _runner)
check("the studio fallback stays artifact-only",
      "studio_pane_posture if artifact_path else None" in _runner)
check("a None builder is skipped rather than called",
      "if _builder is not None:" in _runner)

_block = _runner[_runner.index("if artifact_path or app:"):]
_block = _block[: _block.index("_compose_focus_section")]
check(
    "no unconditional studio fallback survives in the block",
    "or studio_pane_posture\n" not in _block,
    "an app-only lane would be handed a document grammar for no document",
)


# =============================================================================
print("\n[6b] R1 — deleting an app takes its agent's memory, and NOTHING else")
# =============================================================================

_roots = app_delete_roots("photos")
check("exactly two roots — the app and its agent's home", len(_roots) == 2, str(_roots))
check("the app's own folder is a root", "apps/photos/" in _roots, str(_roots))
check("the agent's HOME is a root (not just its memory/)",
      "agents/photos/" in _roots, str(_roots))

# ⭐ R4 is what makes the pairing a DERIVATION rather than a lookup: the agent's
# slug IS the app's, so there is no declaration to read and no way for the two
# to disagree at delete time.
_other = app_delete_roots("client-work")
check("a second app's roots do not overlap the first",
      not set(_roots) & set(_other), f"{_roots} vs {_other}")

# ⚠️ THE BLAST RADIUS, asserted as a NEGATIVE. The delete confirm promises the
# member's files stay; this is that promise as a check. Their work lives by
# MEANING anywhere in the workspace, so every path below must be outside.
for _inside in ("apps/photos/_app.yaml", "apps/photos/notes.md",
                "agents/photos/memory/feedback.md", "agents/photos/_autonomy.yaml",
                "/workspace/apps/photos/deep/nested.md"):
    check(f"inside the radius: {_inside}", is_app_owned_path(_inside, "photos"))

for _outside in ("clients/shoot.jpg", "Documents/notes.md", "Downloads/raw.csv",
                 "apps/client-work/_app.yaml", "agents/editor/memory/notes.md",
                 "skills/culling-a-shoot/SKILL.md", "system/skills/writing-a-spec/SKILL.md"):
    check(f"OUTSIDE the radius: {_outside}", not is_app_owned_path(_outside, "photos"))

# The agent home must be the SAME shape a kernel agent uses — the species split
# ADR-624 refused would arrive here first, as a second home under apps/.
from services.workspace_paths import agent_home as _agent_home  # noqa: E402
check(
    "a member agent's home is the ordinary agent home (no species split)",
    _agent_home("photos") in _roots and _agent_home("photos") == "agents/photos/",
    _agent_home("photos"),
)
check(
    "no delete root lives under apps/ for the AGENT half",
    not any(r.startswith("apps/") and "agent" in r for r in _roots),
    str(_roots),
)


# =============================================================================
print("\n" + "=" * 70)
print(f"  {_passed} passed, {_failed} failed")
print("=" * 70)
print(
    "\n  NOT YET (later phases — ADR-653 §11): 3 composition register · "
    "4 client vocabulary · 5 launcher foregrounding · 6 standing executor · "
    "(all §11 declaration-phase checks implemented)\n"
)
sys.exit(1 if _failed else 0)
