"""Member apps — an app is a declaration in the workspace (ADR-653).

An app is an AI-native program a member scaffolds: an agent, the skills it
works by, and a surface that shows its state. It is declared at
``apps/{slug}/_app.yaml`` as an ORDINARY WORKSPACE FILE — attributed,
versioned, revertible, forkable, exportable — and everything it is made of
comes from that one file.

    apps/photos/_app.yaml
      name: Photos
      about: Client shoots, culled and delivered.
      agent:
        name: Mara
        character: |
          You look after this member's photo work...
      skills: [culling-a-shoot]
      surface:
        sections:
          - kind: files
            source: clients/

WHY A FILE AND NOT A TABLE (ADR-653 D1)
ADR-464's ruling, held verbatim across ADR-562 and ``services/apps/__init__``:
*the member's copy is a folder; the kernel's is code*. A kernel app is a Python
module calling ``register_app``; a member's app is a folder they author. Same
convention, different tree — and that difference IS the ADR-460 D3.a cliff. A
member declaration is never read as a kernel registration, so it can never
re-point a kernel app's resident.

Being a file buys every substrate property at zero cost: ``write_revision``
gives it history, attribution and revert; ``git_export`` carries it out; and
SHARING AN APP IS SHARING A FILE, so the marketplace needs no distribution
machinery.

⚠️ WHAT A DECLARATION MAY NEVER CARRY (ADR-653 D1/D6, the cliff)
No engine pin, no tool grant, no reach list, no scope, no authority of any
kind. ``DECLARATION_KEYS`` and ``AGENT_KEYS`` are the whitelists, and an
unknown key is PARKED INERT rather than read — the ``standing_work`` discipline
(a parser that can be talked into reading a new key is an authority surface
waiting to happen). The app declares WHEN and WHERE; the agent is identity
only; reach stays the member's, asked for per act.

THE CARDINALITY RULE (ADR-653 R4)
**A member app has exactly ONE agent, and that agent serves exactly ONE app.**
Kernel apps keep many-to-one (``editor`` resides both Slides and Text for
ADR-602 D1's reason) — the two cases are structurally different: a member's app
agent is a CONSTITUENT of its app (ADR-653 R2), a kernel agent is a registered
row that apps point at. Cardinality is NOT authority: a member agent is not
less capable, it belongs to one app because it was declared as part of one.

A declaration naming a KERNEL slug — as the app or as its agent — is REFUSED,
never an override (ADR-548: a plausible default is worse than an honest
absence).

This module is PURE. It parses and validates; it does not read the workspace,
write revisions, or resolve a lane. Callers own I/O.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

import yaml as _yaml

logger = logging.getLogger(__name__)


# =============================================================================
# Paths
# =============================================================================

#: Where member apps live. A principal home's sibling: ``agents/`` answers
#: *whose is this*, ``apps/`` answers *what work is this*.
APPS_ROOT = "apps/"

#: The one declaration leaf. Underscore-yaml per ADR-254: machine-parsed
#: config, ``yaml.safe_load``, ints are ints, never hand-rolled frontmatter.
APP_DECLARATION_LEAF = "_app.yaml"


def app_home(slug: str) -> str:
    """The app's folder (workspace-relative). ``apps/photos/``."""
    return f"{APPS_ROOT}{slug}/"


def app_declaration_path(slug: str) -> str:
    """The app's declaration (workspace-relative). ``apps/photos/_app.yaml``."""
    return f"{app_home(slug)}{APP_DECLARATION_LEAF}"


def app_slug_from_path(path: str) -> Optional[str]:
    """The slug whose declaration ``path`` is, or None.

    Exact by construction: only ``apps/{slug}/_app.yaml`` names an app. A file
    elsewhere under ``apps/{slug}/`` is the app's ordinary content, not its
    declaration, and must not be mistaken for one.
    """
    rel = path.strip().lstrip("/")
    if rel.startswith("workspace/"):
        rel = rel[len("workspace/"):]
    if not rel.startswith(APPS_ROOT):
        return None
    remainder = rel[len(APPS_ROOT):]
    slug, sep, leaf = remainder.partition("/")
    if not sep or not slug or leaf != APP_DECLARATION_LEAF:
        return None
    return slug


# =============================================================================
# The whitelists — a key not named here is parked, never read
# =============================================================================

#: Top-level keys the parser reads. Anything else lands in ``options`` as inert
#: residue (the ADR-639 ``DECLARATION_KEYS`` discipline).
DECLARATION_KEYS = frozenset({"name", "about", "agent", "skills", "surface"})

#: Keys the ``agent:`` block may carry. ⚠️ NO engine, NO model, NO tools, NO
#: reach, NO scope — an agent is identity ⊕ character ⊕ engine (ADR-596) and
#: the engine is the MEMBER's choice (ADR-647), never the app's. A session
#: adding an authority key here has violated ADR-460 D3.a.
AGENT_KEYS = frozenset({"name", "character"})

#: Keys a surface section may carry. ⚠️ NO layout, NO columns, NO align — the
#: moment a section takes a layout prop this is a page builder, which is the
#: feature race the app-seam analysis refuses (APP-BUILDER-UX §5).
SECTION_KEYS = frozenset({"kind", "source", "title"})

#: The first-cut component vocabulary (APP-BUILDER-UX §5). Four kinds, each
#: answering a question about WORK that listing a folder cannot:
#:   files     — what is here?
#:   recent    — what moved?
#:   needs-you — what is waiting on me?
#:   note      — what did we decide?
#: GROWTH RULE (ADR-653 D3.b): a kind is added when a real app needs it and
#: cannot be served — never speculatively — and every refusal is counted.
SECTION_KINDS = ("files", "recent", "needs-you", "note")

#: A slug is lowercase kebab: it names a folder, a surface and a lane binding,
#: so it must survive a path, a URL and a registry key unchanged.
_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]{1,38}[a-z0-9]$")

#: Written to the launcher summary budget — VOICE-AND-TONE §2 measures the slot
#: at ~312 px / 12 px system font on a 390 px phone, which is ~48 characters in
#: practice. A longer `about` TRUNCATES with an ellipsis, and a string that
#: truncates has failed regardless of its words. The authoring path surfaces
#: this rather than silently cutting (APP-BUILDER-UX §6).
ABOUT_BUDGET_CHARS = 48


@dataclass
class AppDecl:
    """One parsed member-app declaration.

    ``problem`` is the D3 posture, inherited from standing work: a PARSEABLE
    declaration that cannot run comes back with the reason set — visible, never
    silently dark. Unparseable returns None from the parser instead.
    """

    slug: str
    name: str
    about: str = ""
    agent_name: str = ""
    agent_character: str = ""
    skills: list[str] = field(default_factory=list)
    sections: list[dict] = field(default_factory=list)
    options: dict = field(default_factory=dict)
    declaration_path: str = ""
    problem: Optional[str] = None
    #: Non-fatal notes for the member (e.g. an `about` over the slot budget).
    #: A warning never blocks; it is surfaced at the authoring door.
    warnings: list[str] = field(default_factory=list)

    @property
    def home(self) -> str:
        return app_home(self.slug)

    @property
    def agent_slug(self) -> str:
        """The agent's slug — DERIVED from the app's, never declared.

        R4 makes this sound: one app, one agent, both directions. Deriving it
        rather than declaring it means a collision is impossible by
        construction (two apps cannot name one agent because neither names its
        agent at all), and it is why `AGENT_KEYS` has no `slug`.
        """
        return self.slug


# =============================================================================
# Validation — each returns a problem token, or None
# =============================================================================

def _classify_slug(slug: str, kernel_app_slugs: frozenset[str]) -> Optional[str]:
    if not slug:
        return "missing_slug"
    if not _SLUG_RE.match(slug):
        return "invalid_slug"
    # ADR-653 D2 — a kernel slug is REFUSED, never overridden. A member app
    # shadowing `slides` would be the D3.a cliff arriving through a file.
    if slug in kernel_app_slugs:
        return "kernel_slug"
    return None


def _classify_agent(block: Any, kernel_agent_slugs: frozenset[str], slug: str) -> Optional[str]:
    if not isinstance(block, dict):
        return "missing_agent"
    if not str(block.get("name") or "").strip():
        return "agent_unnamed"
    # The cliff, checked at the door rather than trusted to review.
    stray = sorted(set(block) - AGENT_KEYS)
    if stray:
        logger.info("[MEMBER_APPS] %s: agent block carries unread keys %s", slug, stray)
        return "agent_key_refused"
    # The derived agent slug must not collide with a kernel agent, for the same
    # reason the app slug must not collide with a kernel app.
    if slug in kernel_agent_slugs:
        return "kernel_agent_slug"
    return None


def _classify_sections(raw: Any) -> Optional[str]:
    if raw is None:
        return None  # an app with no sections is legal — bands 1 and 2 still render
    if not isinstance(raw, list):
        return "surface_invalid"
    for section in raw:
        if not isinstance(section, dict):
            return "surface_invalid"
        kind = str(section.get("kind") or "").strip()
        if kind not in SECTION_KINDS:
            # Counted, not guessed. The refusal IS the demand measurement
            # (ADR-653 §9.5) — an unknown kind is how the vocabulary learns
            # what to grow into.
            logger.info("[MEMBER_APPS] section kind refused: %r", kind)
            return "section_kind_unknown"
        stray = sorted(set(section) - SECTION_KEYS)
        if stray:
            logger.info("[MEMBER_APPS] section carries unread keys %s", stray)
            return "section_key_refused"
    return None


# =============================================================================
# The parser
# =============================================================================

def parse_app_yaml(
    content: str,
    *,
    slug: str,
    declaration_path: str = "",
    kernel_app_slugs: frozenset[str] = frozenset(),
    kernel_agent_slugs: frozenset[str] = frozenset(),
) -> Optional[AppDecl]:
    """Parse one ``_app.yaml`` body. Pure — no I/O, never raises.

    Returns None when the body is unparseable or not a mapping (the caller's
    repair state). A parseable declaration that cannot run comes back with
    ``problem`` set, so a broken app is VISIBLE rather than silently absent.

    ``kernel_app_slugs`` / ``kernel_agent_slugs`` are passed in rather than
    imported so this module stays pure and the kernel registries stay the one
    source of those names (the caller reads them from ``all_apps()`` and
    ``AGENTS``).
    """
    if not content or not content.strip():
        return None
    try:
        parsed = _yaml.safe_load(content)
    except _yaml.YAMLError as e:
        logger.warning("[MEMBER_APPS] %s unparseable: %s", declaration_path or slug, e)
        return None
    if not isinstance(parsed, dict):
        return None

    agent_block = parsed.get("agent")
    agent_name = ""
    agent_character = ""
    if isinstance(agent_block, dict):
        agent_name = str(agent_block.get("name") or "").strip()
        agent_character = str(agent_block.get("character") or "").strip()

    skills_raw = parsed.get("skills")
    if isinstance(skills_raw, str):
        skills = [skills_raw.strip()] if skills_raw.strip() else []
    elif isinstance(skills_raw, list):
        skills = sorted({str(s).strip() for s in skills_raw if s and str(s).strip()})
    else:
        skills = []

    surface_raw = parsed.get("surface")
    sections_raw = surface_raw.get("sections") if isinstance(surface_raw, dict) else None
    sections = [s for s in sections_raw if isinstance(s, dict)] if isinstance(sections_raw, list) else []

    about = str(parsed.get("about") or "").strip()

    decl = AppDecl(
        slug=slug,
        name=str(parsed.get("name") or "").strip(),
        about=about,
        agent_name=agent_name,
        agent_character=agent_character,
        skills=skills,
        sections=sections,
        # Inert residue — parked so the parser cannot be talked into reading it.
        options={k: v for k, v in parsed.items() if k not in DECLARATION_KEYS},
        declaration_path=declaration_path or app_declaration_path(slug),
    )

    decl.problem = (
        _classify_slug(slug, kernel_app_slugs)
        or ("missing_name" if not decl.name else None)
        or _classify_agent(agent_block, kernel_agent_slugs, slug)
        or _classify_sections(sections_raw)
    )

    # A warning is not a problem: the app runs, and the member is told.
    if about and len(about) > ABOUT_BUDGET_CHARS:
        decl.warnings.append(
            f"about_over_budget:{len(about)}/{ABOUT_BUDGET_CHARS}"
        )

    return decl


def declaration_problem_message(problem: str) -> str:
    """The member-facing sentence for a problem token.

    VOICE-AND-TONE: say what happened and what to do, one idea per sentence,
    their words not ours. No kernel noun appears here.
    """
    return {
        "missing_slug": "This app has no name in its folder. Rename the folder and try again.",
        "invalid_slug": "An app folder's name can use lowercase letters, numbers and dashes.",
        "kernel_slug": "That name is already used by one of the built-in apps. Pick another.",
        "missing_name": "This app needs a name. Add one and it will show up.",
        "missing_agent": "This app needs someone to look after it. Add an agent with a name.",
        "agent_unnamed": "The agent here needs a name.",
        "agent_key_refused": "An agent can have a name and a character, and nothing else.",
        "kernel_agent_slug": "That name is already used by one of the built-in agents. Pick another.",
        "surface_invalid": "This app's sections could not be read. Each one needs a kind.",
        "section_kind_unknown": (
            "One of the sections asks for something this can't show yet. "
            f"It can show: {', '.join(SECTION_KINDS)}."
        ),
        "section_key_refused": "A section can have a kind, a source and a title, and nothing else.",
    }.get(problem, "This app could not be read.")


# =============================================================================
# Deletion — ADR-653 R1: memory is deleted WITH the app
# =============================================================================
#
# The operator's ruling, and the coherent half of it: an app-bound agent's
# memory is PART OF THE APP. What it learned was about this work, so when the
# work goes there is nowhere for it to carry that judgment to. The delete
# confirm can therefore say the true thing — *the app and its agent go away;
# your files stay* — rather than quietly orphaning a folder.
#
# ⚠️ WHY THIS FUNCTION EXISTS AT ALL. ADR-624 D1 puts every agent's memory at
# `agents/{slug}/memory/` — a PRINCIPAL HOME keyed by slug, not by app. So
# deleting `apps/photos/` cannot reach `agents/photos/memory/` without knowing
# the pairing. Two shapes were available (ADR-653 §8a R1) and the other one —
# moving an app agent's memory under `apps/{slug}/memory/` — was REFUSED: it
# would give member agents a different home shape from kernel agents, which is
# the species split ADR-624 argued against on a scaling argument, arriving
# through the filesystem. One home shape for every agent; the pairing is
# DERIVED here instead, which is cheap because R4 makes the slugs equal.


def app_delete_roots(slug: str) -> list[str]:
    """Every folder deleting app ``slug`` removes, workspace-relative.

    TWO roots and never more: the app's own folder, and its agent's home.
    Pure — the caller trashes them through the ordinary folder path, so
    attribution, the archive revision and restorability come for free (nothing
    here is a bespoke deleter).

    R4 is what makes the pairing a derivation rather than a lookup: the agent's
    slug IS the app's, so there is no declaration to read and no way for the
    two to disagree.

    ⚠️ The agent HOME is returned, not just its `memory/` — the home holds
    exactly what it knows (free) and the grants it runs under (locked), and a
    dismissed agent keeps neither. Leaving the locked sidecars behind would
    strand a dial for an agent that no longer exists.
    """
    from services.workspace_paths import agent_home

    return [app_home(slug), agent_home(slug)]


def is_app_owned_path(path: str, slug: str) -> bool:
    """Is ``path`` inside what deleting app ``slug`` removes? Pure.

    The blast-radius predicate, so a caller (and the gate) can assert the
    negative — that a member's OWN files, which live by meaning anywhere else
    in the workspace, are never inside the two roots.
    """
    rel = path.strip().lstrip("/")
    if rel.startswith("workspace/"):
        rel = rel[len("workspace/"):]
    return any(rel.startswith(root) for root in app_delete_roots(slug))
