"""ADR-653 — an app is an AI-native program. The declaration's gate.

Script-shaped: run it and READ THE COUNT. A pytest-shaped gate run as a script
exits green having collected nothing (the ADR-645 lesson), so this one prints
every check and returns a count.

    cd api && python3 test_adr653_app_is_a_program.py

SCOPE. This covers the DECLARATION half (ADR-653 D1/D2 + R4), which is what
exists at this commit. The checks ADR-653 §11 names for later phases are listed
at the bottom as NOT YET — named so their absence is visible rather than
assumed:
  4  — section kinds resolve in the CLIENT vocabulary (D3.b, FE side)
  5  — a declared app slug foregrounds from the Launcher (D3.c, FE side)
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

import re
import sys
from pathlib import Path

sys.path.insert(0, ".")

_WEB = Path(__file__).resolve().parent.parent / "web"


def _web(rel: str) -> str:
    """One frontend file's source, or "" when absent.

    The ADR-338 idiom: checks 4 and 5 are FE-side, and a Python gate reads the
    TypeScript rather than pretending the half it cannot import does not exist
    (the ADR-653 §11 "NOT YET" block this replaces).
    """
    p = _WEB / rel
    return p.read_text() if p.exists() else ""


def _strip_comments(src: str) -> str:
    """Source with // and /* */ comments removed.

    ⚠️ RECURRING DEFECT, and the reason this exists. A substring check over raw
    source is satisfied by a COMMENT — including a comment explaining the very
    fix being asserted. It has cost this repo three separate green-against-
    nothing gates (2026-09-07, 09-13, 09-17), so every check below reads the
    stripped text.
    """
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    return re.sub(r"(?m)^\s*//.*$", "", src)

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
    surface_row,
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
print("\n[2b] D2 — the MEMBER app's agent resolves, and carries no authority")
# =============================================================================

from services.agents_registry import AGENT_ROW_KEYS, build_agent_posture  # noqa: E402
from services.member_apps import agent_row, is_member_app_slug  # noqa: E402

_decl = _parse(GOOD)
_row = agent_row(_decl)

# ⭐ THE ROW SHAPE DOES NOT CHANGE (ADR-653 D2). A member agent is not a second
# species — it is the SAME `AGENTS`-shaped row, distinguished by exactly one
# descriptive field.
check("the member row carries NO key outside AGENT_ROW_KEYS",
      set(_row) <= AGENT_ROW_KEYS, str(set(_row) - AGENT_ROW_KEYS))

# ⚠️ THE ADR-460 D3.a CLIFF, at the one place a member's words become an agent.
for _forbidden in ("tools", "reach", "scope", "grant", "permissions",
                   "mandate", "autonomy", "authority"):
    check(f"no {_forbidden!r} key on a member agent row", _forbidden not in _row)

# ⚠️ NO ENGINE — absent, not defaulted. The engine is the MEMBER's choice
# (ADR-647 D4); a row that pinned one would out-rank the member's own pick.
check("no engine is pinned by a declaration",
      "model" not in _row and "engine" not in _row, str(sorted(_row)))

check("kernel is False — a member wrote this row", _row.get("kernel") is False)
check("offered is False — met where it works, never invited (ADR-600 D2)",
      _row.get("offered") is False)
check("R4 — the agent's slug IS the app's", _row.get("slug") == _decl.slug)
check("the member's own words become the character",
      _row.get("posture") == _decl.agent_character and bool(_decl.agent_character))

# The character composes through the SAME door every kernel agent takes.
check("a member row composes a posture", bool(build_agent_posture(_decl.slug, row=_row)))
check("...and without the row the kernel lookup answers NOTHING",
      build_agent_posture(_decl.slug) == "",
      "a member slug must not resolve out of the kernel register")

# ⭐ KERNEL-FIRST. A member app may never shadow a kernel app's resident, and
# the predicate that decides it must refuse a kernel slug.
for _k in sorted(_kernel_names()[0]):
    check(f"{_k!r} (kernel app) is never a member app slug",
          not is_member_app_slug(_k))
check("a member slug IS one", is_member_app_slug("photos"))
check("a malformed slug is not", not is_member_app_slug("Not A Slug"))

# The lane door resolves kernel BEFORE member, and the order is the cliff.
import inspect as _inspect  # noqa: E402
import re as _re2  # noqa: E402
from routes.lanes import _lane_agent, create_lane  # noqa: E402

# ⚠️ Comments STRIPPED before every substring check below — a gate that reads
# its own explanatory prose is green against nothing (the recurring defect).
_cl = _re2.sub(r"#.*", "", _inspect.getsource(create_lane))
# ⚠️ ASSERT THE CALL AND ITS RESULT, not the symbol. A first cut read
# `"read_member_app" in src`, which the IMPORT satisfies on its own — stubbing
# the call to `decl = None` left it green. Falsified.
check("the lane door CALLS the member-app read",
      bool(_re2.search(r"read_member_app\(\s*auth\.client", _cl)))
check("...and turns the declaration into an agent row",
      bool(_re2.search(r"member_agent\s*=\s*agent_row\(decl\)", _cl)))
# ⭐ KERNEL-FIRST, asserted on the CALLS rather than on the import order: a
# member declaration must never be able to re-point a kernel app's resident.
_k_call = _re2.search(r"agent_slug\s*=\s*resident_for_app\(", _cl)
_m_call = _re2.search(r"read_member_app\(\s*auth\.client", _cl)
check("...asking the KERNEL registry first",
      bool(_k_call and _m_call) and _k_call.start() < _m_call.start())
check("...and consulting the member app ONLY when the kernel answered nothing",
      "if not agent_slug:\n            from services.member_apps import" in _cl)
check("a resolved member agent is used directly, never re-looked-up in AGENTS",
      "member_agent or resolve_agent" in _cl)

# ⚠️ The serve path must stay PURE: `_lane_agent` runs once per lane on a list
# of fifty, so a read there is fifty reads per serve. R4 is what makes the
# derivation free — the agent's slug IS the app's.
_la = _re2.sub(r"#.*", "", _inspect.getsource(_lane_agent))
check("the serve path derives a member resident with NO read",
      "is_member_app_slug" in _la and "read_member_app" not in _la)


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
print("\n[3] D3.a — `composition` is a validated register WITH a runtime reader")
# =============================================================================

from services.kernel_surfaces import (  # noqa: E402
    KERNEL_SURFACES,
    REGISTERS,
    is_composition,
)

check("`composition` is a valid register", "composition" in REGISTERS, str(REGISTERS))
check("the pre-existing three survive",
      {"intent", "os-config", "application"} <= set(REGISTERS), str(REGISTERS))

# ⭐ The reader is what makes the field load-bearing rather than decorative.
# `register` had ZERO runtime readers before D3.a — a taxonomy nothing reads
# is prose with a colon in it, which is how ADR-435's "the taxonomy could not
# express its distinctness" was allowed to be true.
check("no KERNEL surface is a composition (they are mirrors)",
      not any(is_composition(e) for e in KERNEL_SURFACES),
      str([e["slug"] for e in KERNEL_SURFACES if is_composition(e)]))

# Fail-closed BOTH ways: a typo and an absence must degrade to the mirror
# path, never into a dispatch with nothing to dispatch.
check("an unknown register is NOT a composition", not is_composition({"register": "typo"}))
check("a missing register is NOT a composition", not is_composition({}))
check("a member app's served row IS a composition",
      is_composition(surface_row(_parse(GOOD))))


# =============================================================================
print("\n[3b] D3.c — the served row, and what is WITHHELD from it")
# =============================================================================

_row = surface_row(_parse(GOOD))
check("the row carries the declaration's name", _row["title"] == "Photos", _row["title"])
check("the row routes under /apps/", _row["route"] == "/apps/photos", _row["route"])
check("every member app shares ONE launcher tier", _row["tier"] == "app", _row["tier"])
check("the row is not pinned by default", _row["default_pinned"] is False)
check("the summary is the declaration's own `about`",
      _row["summary"] == "Client shoots, culled and delivered.", _row["summary"])

# ⚠️ THE CLIFF ON THE WIRE. A served row says what to RENDER; what anyone may
# DO is decided by grants and gates at the act (ADR-460 D3.a).
for _forbidden in ("resident", "agent", "model", "engine", "tools", "reach",
                   "scope", "grant", "permissions"):
    check(f"the served row carries no `{_forbidden}`", _forbidden not in _row)

# Drive the resolver with a fake client: the payload is what the shell reads,
# so a shape assertion here is worth more than a source scan.
class _Q:
    def __init__(self, rows): self.rows = rows
    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def like(self, *a, **k): return self
    def order(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def execute(self):
        class _R: data = self.rows
        return _R()


class _C:
    def __init__(self, rows): self.rows = rows
    def table(self, name): return _Q(self.rows if name == "workspace_files" else [])


from services.composition_resolver import _resolve_member_app_surfaces  # noqa: E402

_BROKEN = "name: Broken\nagent:\n  name: Bo\nsurface:\n  sections:\n    - kind: chart\n"
_served = _resolve_member_app_surfaces("u1", _C([
    {"path": "/workspace/apps/photos/_app.yaml", "content": GOOD},
    {"path": "/workspace/apps/broken/_app.yaml", "content": _BROKEN},
    {"path": "/workspace/apps/bad/_app.yaml", "content": "[["},
]))
check("a good declaration is SERVED", len(_served) == 1, f"served {len(_served)}")
check("the served one is the good one",
      _served and _served[0]["slug"] == "photos", str([r["slug"] for r in _served]))

# ⭐⭐⭐ The empty-window class, refused at the source. A declaration with a
# problem would give the client a slug it foregrounds and then cannot draw —
# exactly the `connectors` phantom that shipped an empty window for nine days
# (ADR-653 §10.1). It is READ (so the member can be told) and not SERVED.
check("a declaration with a PROBLEM is withheld from the roster",
      all(r["slug"] != "broken" for r in _served), str([r["slug"] for r in _served]))
check("an unparseable declaration is withheld",
      all(r["slug"] != "bad" for r in _served), str([r["slug"] for r in _served]))


class _Boom:
    def table(self, *a, **k): raise RuntimeError("db down")


check("a failed read degrades to EMPTY, never blanks the shell",
      _resolve_member_app_surfaces("u1", _Boom()) == [])


# =============================================================================
print("\n[4] D3.b — section kinds resolve in the CLIENT vocabulary")
# =============================================================================

_section = _strip_comments(_web("components/apps/AppSection.tsx"))
check("the section dispatch exists", bool(_section))

# ⭐ THE DATA-DRIVEN RENDERING PATH. YARNNN had exactly one and it died as
# COLLATERAL in e18e178 — six weeks after ADR-435 explicitly preserved it, and
# by no ruling of its own (ADR-653 §1.3). This check is what stops that
# happening silently a second time.
check("dispatch is by KIND, not by a per-app component",
      "switch (kind)" in _section or "case 'files':" in _section)

for _kind in ("files", "note"):
    check(f"the client draws {_kind!r}", f"case '{_kind}':" in _section)

# ⚠️ THE HONEST MISS (D3.b). A kind we cannot draw must SAY so. A blank band is
# indistinguishable from an app that has nothing in it, and a member cannot
# tell a limit from an emptiness.
check("an unknown kind hits a default branch", "default:" in _section)
# Read the default BRANCH, not the file: a `<SectionMiss` anywhere would
# otherwise satisfy this while the default returned null.
_default = _section[_section.index("default:"):] if "default:" in _section else ""
_default = _default[: _default.index("}")] if "}" in _default else _default
check("the default branch returns the honest MISS, never null",
      "<SectionMiss" in _default and "return null" not in _default,
      repr(_default[:120]))
check("the miss names the kind it could not draw", "{kind" in _section)

# The server admits four kinds; the client draws two. The gap must render the
# SAME honest miss rather than a blank — asserted as a real inequality so a
# later session cannot quietly let an undrawable kind through.
_drawable = set(re.findall(r"case '([a-z-]+)':", _section))
check("every drawable kind is one the server admits",
      _drawable <= set(SECTION_KINDS), f"{_drawable} vs {SECTION_KINDS}")
check("the kinds the client cannot draw are a real, non-empty set",
      bool(set(SECTION_KINDS) - _drawable),
      "if this is empty the miss branch is unreachable and untested")

# ⚠️ THE TRAILING SLASH. `getTree` matches its `root` EXACTLY: the folder path
# lists its files, and the same path with a trailing slash returns 200 with
# ZERO ROWS. A member naming a folder writes `clients/` — ADR-653 D1's own
# example does — so without the strip the section renders a convincing
# "Nothing here yet" over a folder full of their work. Found by DRIVING the
# surface: an empty 200 is indistinguishable from an empty folder at every
# layer above the query.
check("a declared source strips its trailing slash",
      bool(re.search(r"replace\(/\\/\+\$/, ''\)", _section)),
      "sourcePath must not hand getTree a trailing slash")

# ⚠️ NO LAYOUT PROPS — the page-builder cliff (APP-BUILDER-UX §5).
for _banned in ("columns", "align", "width", "height"):
    check(f"a section may not carry {_banned!r}", _banned not in SECTION_KEYS)


# =============================================================================
print("\n[5] D3.c — a declared app slug FOREGROUNDS, and the kernel gate holds")
# =============================================================================

_surface_ts = _strip_comments(_web("types/surface.ts"))

# ⭐⭐⭐ THE ROSTER IS THE AUTHORITY. The predicate must consult the SERVED set,
# never the URL and never persisted state — a client that trusted either could
# foreground an app that does not exist and draw an empty window, which is
# exactly the `connectors` phantom (§10.1) arriving from the other direction.
check("an openable-surface predicate exists",
      "export function isOpenableSurfaceSlug" in _surface_ts)
check("it admits a kernel slug OR a served app slug",
      "isKernelSurfaceSlug(slug) || appSlugs.has(slug)" in _surface_ts)
check("the served app set is DERIVED from the roster",
      "export function appSurfaceSlugs" in _surface_ts)
# D3.a's register is the classifier, not the route and not the tier: matching
# on a route would make a string a capability.
check("an app surface is identified by its REGISTER",
      "register === 'composition'" in _surface_ts)

# ⭐ THE KERNEL UNION STAYS CLOSED. Widening `KernelSurfaceSlug` to admit an
# arbitrary string would make the ADR-338 three-way lockstep VACUOUSLY true and
# retire that gate without a ruling — the §10.2 lesson, one level up.
# ⚠️ SLICE FROM THE DECLARATION, not from the file start. A first cut took
# everything up to the first `;` in the stripped source — which is blank-line
# residue ahead of the union — so the slice was empty and `KernelSurfaceSlug =
# string` passed. Falsified.
_u_start = _surface_ts.find("export type KernelSurfaceSlug =")
check("the kernel slug union is declared", _u_start >= 0)
_union = _surface_ts[_u_start:]
_union = _union[: _union.index(";")] if ";" in _union else _union
check("the union is a real set of literals, not a bare string",
      "'chat'" in _union and "string" not in _union,
      repr(_union[:80]))

# ⚠️ ASSERT THE CALL, NOT THE FILE. A first cut of this check read
# `"isOpenableSurfaceSlug" in src`, which the IMPORT LINE satisfies on its own
# — reverting a gate to `isKernelSurfaceSlug` left it green. Falsified.
_gates = {
    "components/shell/Launcher.tsx": ("the Launcher click", 1),
    "components/shell/SurfaceViewport.tsx": ("the window mount", 2),
    "components/shell/chrome/TopBarSurface.tsx": ("the Dock click", 2),
}
for _f, (_what, _n) in _gates.items():
    _src = _strip_comments(_web(_f))
    _calls = len(re.findall(r"isOpenableSurfaceSlug\(", _src))
    check(f"{_what} gate CALLS the widened predicate ({_n} site/s)",
          _calls >= _n, f"{_f}: {_calls} call(s), want >= {_n}")
    # The kernel-only predicate may still be IMPORTED (SurfaceViewport and the
    # registry legitimately use it); what must not survive is a DECIDING call
    # that gates foregrounding on it.
    check(f"{_what} no longer decides on the kernel predicate alone",
          "isKernelSurfaceSlug(surface.slug)" not in _src
          and "isKernelSurfaceSlug(contextMenu.slug)" not in _src
          and "isKernelSurfaceSlug(foregrounded)" not in _src,
          _f)

# ⚠️ THE SILENT DROP. `mountSlugs` filtered on `isKernelSurfaceSlug`, so a
# member app could be foregrounded and NO WINDOW EVER MOUNTED — the failure
# that makes a Launcher-only fix look like it works.
_viewport = _strip_comments(_web("components/shell/SurfaceViewport.tsx"))
check("mountSlugs no longer filters on the kernel predicate alone",
      ".filter(isKernelSurfaceSlug)" not in _viewport)
check("the two-segment app route is read",
      "appSlugFromPath" in _viewport)
check("a URL-named app is honoured ONLY when the roster carries it",
      "appSlugs.has(s) ? s : null" in _viewport)

# ONE generic component for every app — no per-app static import, which is what
# leaves the ADR-338 lockstep over KERNEL surfaces untouched.
_registry = _strip_comments(_web("components/shell/SurfaceRegistry.tsx"))
check("a resolver serves both kinds", "resolveOpenableComponent" in _registry)
check("an app resolves to the ONE generic", "<AppSurface slug={slug} />" in _registry)
check("the kernel registry map is still union-typed",
      "Partial<Record<KernelSurfaceSlug, ComponentType>>" in _registry)
check("an unserved slug resolves to NOTHING, never a guessed component",
      "return undefined;" in _registry)

# ⚠️ THE NAMESPACE IS AUTHENTICATED. The gate derives its protected set from
# KERNEL_SURFACE_SLUGS as `/{slug}` — single-segment by construction — so a
# two-segment app route slips under it however current the roster is. That is
# the 2026-08-20 incident's SHAPE (eight surfaces served 200 to logged-out
# visitors), reached a different way.
_mw = _strip_comments(_web("lib/supabase/middleware.ts"))
check("the app namespace is protected", 'APP_NAMESPACE_PREFIX = "/apps"' in _mw)
check("and it is actually IN the protected set",
      "APP_NAMESPACE_PREFIX," in _mw or "APP_NAMESPACE_PREFIX ," in _mw)

# The app's own route exists and is a real page.
check("the /apps/{slug} route exists",
      bool(_web("app/(authenticated)/apps/[slug]/page.tsx")))

# The three bands (APP-BUILDER-UX §2.2) — fixed frame, declared contents.
_app_surface = _strip_comments(_web("components/apps/AppSurface.tsx"))
check("band 1 renders the app's name", "{decl.name}" in _app_surface)
check("band 1 renders its `about` (the visible claim)", "{decl.about}" in _app_surface)
check("band 2 names who is minding it",
      "looks after this." in _app_surface)
check("band 3 renders the DECLARED sections", "<AppSection" in _app_surface)
# ⚠️ Band 2's resting line is a complete sentence, not an empty state. Compare
# "No new activity", which says the same thing and sounds like a failure.
check("the resting line is not an absence",
      "No new activity" not in _app_surface and "Nothing to report" not in _app_surface)


# =============================================================================
print("\n" + "=" * 70)
print(f"  {_passed} passed, {_failed} failed")
print("=" * 70)
print(
    "\n  NOT YET (ADR-653 §11):\n"
    "    6  standing executor resolves through the app (D5)\n"
)
sys.exit(1 if _failed else 0)
