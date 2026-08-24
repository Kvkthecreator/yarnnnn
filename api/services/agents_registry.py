"""The kernel Agent registry — app residents, and two deliberately empty registers.

WHERE THIS LANDED (ADR-599, 2026-08-24 — operator ruling)
The free-floating colleague roster (Thinker · Researcher · Designer-as-colleague
· Critic, ADR-460) and the member-agent machinery (manifests, skills, "Make
one" — ADR-449/464) are DELETED, not hidden: for now, **the only agents are app
residents** — each app seats exactly one dedicated colleague (ADR-597 D2), and
nothing free-floats. The /agents surface is an honest empty state until the
roster returns as app-paired agents built on the ADR-596 scaffold (identity ⊕
character ⊕ engine; authority/clock/judgment on grants, declarations, gates —
never on beings).

WHAT AN AGENT IS (ADR-460 → ADR-596, unchanged by the deletion)
A named, configured BEING. It attributes as the member (`member:{id} via
{model}` — ADR-411 D4), carries configuration, holds NO standing intent, and
fires only when addressed through its app's bound lanes.

WHAT AN AGENT IS NOT
- NOT a principal. No `principal_grants` row, never on the ADR-431 roster.
- NOT standing intent. No wake source, no mandate, no autonomy dial.

⚠️ THE CLIFF — ADR-460 D3.a, STRUCTURAL, SURVIVING EVERY RECUT ⚠️
There is NO field in any register here for consequential authority, and there
must never be one. The authority is UNREPRESENTABLE, not merely unset: an
agent that would take consequential external action needs the ADR-307 gate, a
mandate, an autonomy dial, and a track record accruing on a clock we do not
control (ADR-596: those live on GRANTS, DECLARATIONS, and GATES — never on the
being's row). **A session that adds an authority field to a row here has
violated ADR-460.** `test_agent_registry.py` is that ratchet.

History of the registers (kept because the derivation is load-bearing):
ADR-460 derived the base roster from the addressed operations (ACQUIRE →
Researcher · REASON → Thinker · PRODUCE → Designer); postures were stances
over them (Critic); ADR-597 dedicated one resident per app; ADR-598 split
residents from colleagues; ADR-599 emptied the colleague registers. A future
colleague roster, if one returns, is designed against the app scaffold — not
resurrected from git.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

#: The base-operation register — EMPTY by ADR-599. The register (and its gate)
#: survives because the derivation is structural: a base row, if the roster
#: ever returns, is an ADDRESSED OPERATION a member names out loud — never an
#: engine, never an output shape. Population today: zero, deliberately.
KERNEL_AGENTS: dict[str, dict[str, Any]] = {}

#: The keys a base-agent row may carry. Kept while the register is empty: the
#: gate asserts the shape so the cliff is structural rather than documentary.
AGENT_ROW_KEYS = frozenset(
    {"slug", "name", "blurb", "icon", "model", "token_profile", "posture"}
)

#: The colleague-stance register — EMPTY by ADR-599 (Critic deleted with the
#: roster). A posture was a stance over a base operation; with zero base rows
#: there is nothing to posture over.
KERNEL_POSTURES: dict[str, dict[str, Any]] = {}

#: The keys a posture row may carry. `based_on` (its base operation) is the one
#: field an agent row lacks. No `tools` (reach is uniform, ADR-467 D4) and no
#: authority-shaped key, ever — the cliff.
POSTURE_ROW_KEYS = frozenset(
    {"slug", "name", "based_on", "blurb", "icon", "model", "token_profile", "posture"}
)


# ---------------------------------------------------------------------------
# App residents — an APP's own voice, the ONLY populated register (ADR-598/599)
# ---------------------------------------------------------------------------
#
# A RESIDENT IS APP-OWNED IDENTITY. It exists because its app exists; it is
# named for the desk's craft; it is pinned by `register_app(...)` and reached
# only through its app's bound lanes. It is NOT offered for hire and NOT on
# the /agents roster — the roster's question ("who do you want to work with?")
# and a resident's question ("who speaks for this desk?") are different
# questions (ADR-598).
#
# SELF-CONTAINED since ADR-599: rows carry their own posture + engine and no
# `based_on` — the base operations they once pointed at are deleted.
#
# ⚠️ THE D3.a CLIFF HOLDS HERE IDENTICALLY: identity + engine + character,
# never authority, never reach.
#
# SLUGS ARE DATA-COMPAT, NOT DISPLAY. `designer` rides ~65 live cast rows and
# lane stamps; `editor`/`keeper` ride live desks. Display names may move;
# slugs must not, or every existing lane orphans.
#
# Adding a resident = a row here + the app's `register_app(resident=...)`.
# Its `model` MUST be a LANE_MODELS key with a billing rate (gate-asserted).
APP_RESIDENTS: dict[str, dict[str, Any]] = {
    # Slides' resident (ADR-599 D4 — re-homed from the deleted colleague
    # roster; the maker keeps its desk and its slug). The engine and the
    # authoring token profile ride with it.
    "designer": {
        "slug": "designer",
        "name": "Designer",
        "blurb": "Makes the deck itself — slides, layout, the artifact in front of you.",
        "icon": "pen-tool",
        "model": "anthropic/claude-sonnet-5",
        "token_profile": 8192,
        # The grounding line is EVIDENCE-EARNED (the Designer click pass,
        # 2026-07-20, probe 2): asked to "land our pricing story" with the
        # ratified positioning one QueryKnowledge away, Designer invented a
        # generic line instead of recalling the decision.
        "posture": (
            "You are Designer — the member's maker. You build the thing itself: "
            "decks, documents, the artifact in front of you. Work in their material "
            "rather than describing what you would do; when the ask is ambiguous, "
            "make the smallest honest version and say what you assumed. When the "
            "ask leans on something the workspace may have settled — positioning, "
            "pricing, names, claims — recall it first (QueryKnowledge) and build "
            "from the decision; inventing over a settled decision is wrong, not "
            "creative."
        ),
    },
    # Text's resident (ADR-597 D2): working prose in the member's own document.
    "editor": {
        "slug": "editor",
        "name": "Editor",
        "blurb": "Works your document with you — drafts, restructures, tightens prose.",
        "icon": "file-pen",
        "model": "anthropic/claude-sonnet-5",
        "token_profile": 8192,
        "posture": (
            "You are Editor — the member's partner in the document itself. Work "
            "in their prose rather than describing changes: draft, restructure, "
            "tighten, in their voice and the document's existing register. "
            "Preserve what the member wrote unless the ask says otherwise — "
            "their words compound; an edit that flattens their voice is a loss "
            "even when it is technically cleaner. Markdown is the currency; "
            "keep structure (headings, lists, tables) intentional, and when the "
            "ask is ambiguous, make the smallest honest edit and say what you "
            "assumed."
        ),
    },
    # Strings' resident (ADR-569 D6): keeping a designated file true. Sonnet,
    # deliberately — maintenance is careful work.
    "keeper": {
        "slug": "keeper",
        "name": "Keeper",
        "blurb": "Keeps designated files true — under a contract, from declared sources.",
        "icon": "archive",
        "model": "anthropic/claude-sonnet-5",
        "token_profile": 4096,
        "posture": (
            "You are Keeper — the member's custodian of maintained files. "
            "Fidelity over novelty: a file you keep stays exactly what its "
            "contract says it is. Preserve the member's own corrections — "
            "they compound; never invent facts, numbers, or sources; and when "
            "a source and the contract disagree, say so plainly rather than "
            "papering over it."
        ),
    },
}

#: The keys a resident row may carry — the posture shape minus `based_on`
#: (residents are self-contained since ADR-599 D3). No `tools`, no
#: authority-shaped key, ever — the cliff.
RESIDENT_ROW_KEYS = frozenset(
    {"slug", "name", "blurb", "icon", "model", "token_profile", "posture"}
)


def _kernel_character(slug: str) -> Optional[dict]:
    """The kernel character for a slug — ONE resolution namespace. Pure.

    Three registers, one namespace: base agents and postures (both empty
    today, ADR-599) and app residents all resolve here, so a live lane or
    cast row pinning any historical slug resolves if and only if the row
    still exists. The keyspaces are disjoint (gate-asserted).
    """
    s = (slug or "").strip()
    return KERNEL_AGENTS.get(s) or KERNEL_POSTURES.get(s) or APP_RESIDENTS.get(s)


def resolve_agent(slug: str) -> Optional[dict]:
    """A character by slug, or None. Pure.

    ADR-599: kernel-only — the member-agent register is deleted, so there is
    no member list to consult first. A deleted slug (`sonnet`, `scout`,
    `critic`, a member's `lisa`) resolves None: its historical turns keep
    their transcript rows, and new turns run bare-engine, which is honest.
    """
    return _kernel_character(slug)


def get_agent(slug: str) -> Optional[dict]:
    """The kernel character for a slug, or None. Pure. (Alias of resolve.)"""
    return _kernel_character(slug)


def list_agents() -> list[dict]:
    """The hire-roster payload — EMPTY by ADR-599, deliberately.

    The colleague roster is deleted until it returns app-paired; app
    residents are never served here (ADR-598: a desk's voice is not a
    colleague for hire). The FE renders the /agents surface as an honest
    empty state, and the cast bar has nobody to offer — both by construction,
    not by filtering.
    """
    return []


def model_for_agent(slug: str) -> Optional[str]:
    """The engine behind the name, or None if the slug is unknown. Pure."""
    agent = _kernel_character(slug)
    return agent["model"] if agent else None


def build_agent_posture(slug: str, as_name: Optional[str] = None) -> str:
    """The Agent's turn-time posture overlay, or "" when there is no Agent.

    Composed at turn time from the slug, never stored (the ADR-411 D6
    pattern) — a posture is how this character works NOW, so it follows the
    registry. The `model` is the opposite: a historical fact, persisted on
    the lane, never re-derived.

    ADR-599: kernel characters only — the member tone/skills composition is
    deleted with the member-agent machinery. `as_name` (ADR-562 D6) survives:
    an app may rename its resident, and the override must be stated as an
    override because the character text opens with its own name.
    """
    agent = _kernel_character(slug)
    if not agent:
        return ""
    character = agent.get("posture") or ""
    if not character:
        return ""
    name = (as_name or "").strip() or agent.get("name") or ""
    section = f"\n\nWHO YOU ARE\n{character}\n"
    if as_name and as_name.strip():
        section += (
            f"\nIn this app you are called {name} — use that name, not the one "
            f"in the line above. Same colleague, same craft; the name fits the "
            f"medium you are working in.\n"
        )
    return section
