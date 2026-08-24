"""The kernel Agent registry — ONE register of beings, ADR-600.

WHERE THIS LANDED (ADR-600, 2026-08-24 — operator ruling)
There is ONE kind of agent. `KERNEL_AGENTS` / `KERNEL_POSTURES` /
`APP_RESIDENTS` are DELETED: three dicts with identical row shapes and one
shared resolution namespace were never a type distinction — they were a
VISIBILITY FLAG modelled as three containers, and modelling a property of a
being as the identity of its container means the being changes identity when
the property changes. That cost two silently-dead planners, a vacuous pricing
ratchet, and a cast door that contradicted its own roster (ADR-600 Context).

WHAT AN AGENT IS (ADR-460 → ADR-596, unchanged)
A named, configured BEING: identity ⊕ character ⊕ engine. It attributes as the
member (`member:{id} via {model}` — ADR-411 D4), holds NO standing intent, and
fires only when addressed.

WHAT AN AGENT IS NOT
- NOT a principal. No `principal_grants` row, never on the ADR-431 roster.
- NOT standing intent. No wake source, no mandate, no autonomy dial.

EVERY QUESTION ABOUT A BEING IS A FIELD ON THE BEING (ADR-600 D2, ADR-601 D2)
Two orthogonal facts, each declared rather than structural:
  `offered` — may a member INVITE this being into a conversation?
  `kernel`  — did YARNNN author this being, or did the member?
Capability is on NEITHER: it belongs to the APP (ADR-601 D1). A bound lane's
job overlay is selected by `app` and derived from the app's own registries —
measured at 86.7% of a Slides frame against the character's 2.4% — so a
being's prompt weight is CONSTANT in the number of desks it serves. That is
why many-to-one is free, and why ADR-597 D2's injectivity is retired.

`kernel` IS DESCRIPTIVE, NEVER AUTHORITY. It says who wrote the row, never
what the being may do; the moment it gates capability it is authority on a
being and violates ADR-460 D3.a. Provenance is also deliberately NOT spelled
`editable`: the two coincide today but may diverge (renaming a kernel being's
display name, forking one into a member copy). Provenance is the durable
fact; editability is a policy over it (`assert_editable`).

HIREABILITY IS A FIELD (ADR-600 D2)
`offered` answers ONE question: is this being on the roster a member picks
from? `offered: False` means its home is a desk — met where it works, never
invited (Designer/Slides · Editor/Text · Keeper/Strings). `offered: True` is a
colleague; today NOBODY is, per ADR-599 D1, which ADR-600 does not reopen.
`offered` is REACH, never authority — it says who may be invited, never what
they may do.

⚠️ THE CLIFF — ADR-460 D3.a, STRUCTURAL, SURVIVING EVERY RECUT ⚠️
There is NO field here for consequential authority, and there must never be
one. The authority is UNREPRESENTABLE, not merely unset: an agent that would
take consequential external action needs the ADR-307 gate, a mandate, an
autonomy dial, and a track record accruing on a clock we do not control
(ADR-596: those live on GRANTS, DECLARATIONS and GATES — never on the being's
row). **A session that adds an authority field to a row here has violated
ADR-460.** `test_agent_registry.py` is that ratchet.

SLUGS ARE DATA-COMPAT, NOT DISPLAY. `designer` rides ~65 live cast rows and
lane stamps; `editor`/`keeper` ride live desks. Display names may move; slugs
must not, or every existing lane orphans.

History (kept because the derivation is load-bearing): ADR-460 derived a base
roster from the addressed operations (ACQUIRE → Researcher · REASON → Thinker
· PRODUCE → Designer), with postures as stances over them; ADR-597 dedicated
one resident per app; ADR-598 split residents from colleagues into their own
register; ADR-599 emptied the colleague registers and made resident rows
self-contained; ADR-600 collapsed what was left to one register plus a field.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# The register — every being, one namespace (ADR-600 D1)
# ---------------------------------------------------------------------------
#
# Adding a being = a row here. If it speaks for an app, the app also names it
# in `register_app(resident=...)` (ADR-562 D3). Its `model` MUST be a
# LANE_MODELS key with a billing rate (gate-asserted, ADR-600 D5).
#
# MANY-TO-ONE (ADR-601 D1): a being may serve SEVERAL desks — capability lives
# at the app, so a second desk costs a being nothing. The converse still holds:
# an app pins exactly ONE resident (ADR-467 D1), because a desk with two voices
# is the ambiguity the registration exists to prevent.
AGENTS: dict[str, dict[str, Any]] = {

    # Slides' voice (ADR-599 D4 — the maker keeps its desk and its slug).
    # The engine and the authoring token profile ride with it.
    "designer": {
        "slug": "designer",
        "name": "Designer",
        # Its home is the Slides desk — met there, never invited (ADR-600 D2).
        "offered": False,
        # yarnnn wrote this being; Slides depends on it (ADR-601 D2).
        "kernel": True,
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
    # Text's voice (ADR-597 D2): working prose in the member's own document.
    "editor": {
        "slug": "editor",
        "name": "Editor",
        "offered": False,
        "kernel": True,
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
    # Strings' voice (ADR-569 D6): keeping a designated file true. Sonnet,
    # deliberately — maintenance is careful work.
    "keeper": {
        "slug": "keeper",
        "name": "Keeper",
        "offered": False,
        "kernel": True,
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

#: The keys a row may carry — identity + character + engine + reach. No
#: `tools` (reach is uniform, ADR-467 D4) and no authority-shaped key, ever:
#: the ADR-460 D3.a cliff, enforced as a whitelist rather than as prose.
AGENT_ROW_KEYS = frozenset(
    {"slug", "name", "blurb", "icon", "model", "token_profile", "posture",
     "offered", "kernel"}
)


def resolve_agent(slug: str) -> Optional[dict]:
    """A being by slug, or None. Pure.

    ADR-600: ONE register, so resolution is one lookup — a live lane or cast
    row pinning any historical slug resolves if and only if the row still
    exists. A deleted slug (`sonnet`, `scout`, `critic`, a member's `lisa`)
    resolves None: its historical turns keep their transcript rows, and new
    turns run bare-engine, which is honest.

    This resolves EVERY being, offered or not — a desk's resident must
    resolve for its own lanes to run. `offered` gates the INVITE (ADR-600
    D3), never the read.
    """
    return AGENTS.get((slug or "").strip())


def get_agent(slug: str) -> Optional[dict]:
    """A being by slug, or None. Pure. (Alias of resolve.)"""
    return resolve_agent(slug)


def list_agents() -> list[dict]:
    """The hire-roster payload — the OFFERED beings. Pure.

    ADR-600 D2: hireability is a field, so this is a filter over the one
    register rather than a separate namespace. Empty today (ADR-599 D1 left
    nobody offered), but empty as an OBSERVABLE FACT about the beings — a
    row flipping `offered` appears here with no other edit.
    """
    return [r for r in AGENTS.values() if r.get("offered")]


class NotEditable(Exception):
    """A kernel being was asked to change. Carries the reason, not just a no."""


def assert_editable(slug: str) -> dict:
    """The being, or raise — the ONE chokepoint for "may this row be edited?"

    ADR-601 D3. Built BEFORE the door it guards, deliberately: a protection
    written alongside the feature it constrains is one that feature's author
    may forget, and the ADR-563 lesson (guard at the chokepoint, never at call
    sites) applies just as well to a chokepoint whose callers are still to
    come. Any future member-facing edit path calls THIS — never re-derives it.

    Fails closed: an unknown slug is refused, not treated as member-authored.

    NOTE the asymmetry with `resolve_agent`, and keep it: reading a being is
    never gated (a kernel being must resolve for its own lanes to run). This
    gates the WRITE only.
    """
    being = resolve_agent(slug)
    if being is None:
        raise NotEditable(f"No agent called '{slug}'.")
    if being.get("kernel"):
        # Named, with the reason — a generic refusal reads as a bug and sends
        # the member looking for a permission they can grant themselves.
        raise NotEditable(
            f"{being.get('name') or slug} is a yarnnn system agent — it comes "
            "with the apps it works in, so its character is not editable here."
        )
    return being


def homes_for_agent(slug: str) -> list[str]:
    """The app slugs this being speaks for, registration order. Pure-ish.

    ADR-601 D1 — many-to-one, so this is a LIST. Resolved from the app
    registrations (the same declaration the prompt reads), never stored on the
    being: an app names its resident, and a being that learns a desk should
    not need editing to know it.
    """
    import services.apps  # noqa: F401  (registration side-effect)
    from services.authoring import all_apps

    return [a["slug"] for a in all_apps().values() if a.get("resident") == slug]


def model_for_agent(slug: str) -> Optional[str]:
    """The engine behind the name, or None if the slug is unknown. Pure."""
    agent = resolve_agent(slug)
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
    agent = resolve_agent(slug)
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
