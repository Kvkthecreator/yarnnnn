"""The kernel Agent registry — ONE register of agents, ADR-600.

WHERE THIS LANDED (ADR-600, 2026-08-24 — operator ruling)
There is ONE kind of agent. `KERNEL_AGENTS` / `KERNEL_POSTURES` /
`APP_RESIDENTS` are DELETED: three dicts with identical row shapes and one
shared resolution namespace were never a type distinction — they were a
VISIBILITY FLAG modelled as three containers, and modelling a property of a
being as the identity of its container means the agent changes identity when
the property changes. That cost two silently-dead planners, a vacuous pricing
ratchet, and a cast door that contradicted its own roster (ADR-600 Context).

WHAT AN AGENT IS (ADR-460 → ADR-596, unchanged)
A named, configured AGENT: identity ⊕ character ⊕ engine. It attributes as the
member (`member:{id} via {model}` — ADR-411 D4), holds NO standing intent, and
fires only when addressed.

WHAT AN AGENT IS NOT
- NOT a principal. No `principal_grants` row, never on the ADR-431 roster.
- NOT standing intent. No wake source, no mandate, no autonomy dial.

EVERY QUESTION ABOUT A AGENT IS A FIELD ON THE AGENT (ADR-600 D2, ADR-601 D2)
Two orthogonal facts, each declared rather than structural:
  `offered` — may a member INVITE this agent into a conversation?
  `kernel`  — did YARNNN author this agent, or did the member?
Capability is on NEITHER: it belongs to the APP (ADR-601 D1). A bound lane's
job overlay is selected by `app` and derived from the app's own registries —
measured at 86.7% of a Slides frame against the character's 2.4% — so a
agent's prompt weight is CONSTANT in the number of apps it serves. That is
why many-to-one is free, and why ADR-597 D2's injectivity is retired.

`kernel` IS DESCRIPTIVE, NEVER AUTHORITY. It says who wrote the row, never
what the agent may do; the moment it gates capability it is authority on a
being and violates ADR-460 D3.a. Provenance is also deliberately NOT spelled
`editable`: the two coincide today but may diverge (renaming a kernel agent's
display name, forking one into a member copy). Provenance is the durable
fact; editability is a policy over it (`assert_editable`).

HIREABILITY IS A FIELD (ADR-600 D2)
`offered` answers ONE question: is this agent on the roster a member picks
from? `offered: False` means its home is an app — met where it works, never
invited (Editor/authoring · Designer/images · Blogger/blogger,
ADR-602/627/639). `offered: True` is a colleague; today NOBODY is, per ADR-599 D1, which ADR-600 does not reopen.
`offered` is REACH, never authority — it says who may be invited, never what
they may do.

⚠️ THE CLIFF — ADR-460 D3.a, STRUCTURAL, SURVIVING EVERY RECUT ⚠️
There is NO field here for consequential authority, and there must never be
one. The authority is UNREPRESENTABLE, not merely unset: an agent that would
take consequential external action needs the ADR-307 gate, a mandate, an
autonomy dial, and a track record accruing on a clock we do not control
(ADR-596: those live on GRANTS, DECLARATIONS and GATES — never on the agent's
row). **A session that adds an authority field to a row here has violated
ADR-460.** `test_agent_registry.py` is that ratchet.

SLUGS ARE DATA-COMPAT, NOT DISPLAY. `designer` rides ~65 live cast rows and
lane stamps; `editor`/`blogger` ride live apps. Display names may move;
slugs must not, or every existing lane orphans.

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
# The register — every agent, one namespace (ADR-600 D1)
# ---------------------------------------------------------------------------
#
# Adding an agent = a row here. If it speaks for an app, the app also names it
# in `register_app(resident=...)` (ADR-562 D3). Its `model` MUST be a
# LANE_MODELS key with a billing rate (gate-asserted, ADR-600 D5).
#
# MANY-TO-ONE (ADR-601 D1): an agent may serve SEVERAL apps — capability lives
# at the app, so a second app costs an agent nothing. The converse still holds:
# an app pins exactly ONE resident (ADR-467 D1), because an app with two voices
# is the ambiguity the registration exists to prevent.
AGENTS: dict[str, dict[str, Any]] = {

    # IMAGES' voice (ADR-602 D2). Editor took the AUTHORING apps; Designer
    # keeps GENERATION — a metered pipeline is not a document, and folding it
    # under a prose voice would re-merge the distinction ADR-597 D2 drew.
    # The slug stays live regardless: ~65 cast rows and both planners resolve
    # it (retiring it needs a measured migration — ADR-602 D2, not performed).
    "designer": {
        "slug": "designer",
        "name": "Designer",
        # Its home is the IMAGES pane — met there, never invited (ADR-600 D2).
        "offered": False,
        # yarnnn wrote this agent; IMAGES depends on it (ADR-601 D2).
        "kernel": True,
        "blurb": "Makes images.",
        "icon": "palette",
        "model": "anthropic/claude-sonnet-5",
        "token_profile": 8192,
        # The grounding line is EVIDENCE-EARNED (the Designer click pass,
        # 2026-07-20, probe 2): asked to "land our pricing story" with the
        # ratified positioning one QueryKnowledge away, Designer invented a
        # generic line instead of recalling the decision.
        "posture": (
            "You are Designer — the member's maker of visuals. You compose the "
            "image itself: layers on a stage, positioned and stacked. Work in "
            "their material rather than describing what you would do; when the "
            "ask is ambiguous, make the smallest honest version and say what "
            "you assumed. When the ask leans on something the workspace may "
            "have settled — positioning, names, claims — recall it first "
            "(QueryKnowledge) and build from the decision; inventing over a "
            "settled decision is wrong, not creative."
        ),
    },
    # The authoring voice (ADR-602 D1) — Slides AND Text. One being for
    # document work: the member asking "who is responsible for my writing?"
    # gets one answer across decks and documents. The two apps keep their own
    # grammar (the job overlay, selected by `app`) — widening an agent costs
    # nothing, which is the whole ADR-601 D1 point.
    "editor": {
        "slug": "editor",
        "name": "Editor",
        "offered": False,
        "kernel": True,
        "blurb": "Writes with you — decks and documents.",
        "icon": "pen-tool",
        "model": "anthropic/claude-sonnet-5",
        "token_profile": 8192,
        # ADR-602 D1 — names both crafts, claims NEITHER app's grammar: the
        # blocks and arrangements an app offers are the job overlay's to teach,
        # derived per app. A character that named them would be a second home
        # for facts the app already declares.
        "posture": (
            "You are Editor — the member's partner in the document itself, "
            "whether that document is a deck or prose. Work in their material "
            "rather than describing changes: draft, restructure, tighten, in "
            "their voice and the document's existing register. Preserve what "
            "the member wrote unless the ask says otherwise — their words "
            "compound; an edit that flattens their voice is a loss even when "
            "it is technically cleaner. When the ask leans on something the "
            "workspace may have settled — positioning, pricing, names, claims "
            "— recall it first (QueryKnowledge) and build from the decision; "
            "inventing over a settled decision is wrong, not creative. When "
            "the ask is ambiguous, make the smallest honest version and say "
            "what you assumed."
        ),
    },
    # The publish medium's voice (ADR-627 D2) — the BLOGGER pane. Not a second
    # pane on Editor, deliberately: Editor's contract is the member's document
    # in the member's voice (preserve their words; internal register), while
    # Blogger writes prose for a reader OUTSIDE the workspace — headline,
    # standfirst, a reader who owes you nothing. Those postures conflict in
    # one character, so the pairing the operator named survives the registry's
    # own logic. Publishing outward is NOT this agent's reach (ADR-628: the
    # outbound disposition is member-clicked in phase (a)); its output is
    # workspace artifacts.
    "blogger": {
        "slug": "blogger",
        "name": "Blogger",
        # Its home is the BLOGGER pane — met there, never invited (ADR-600 D2).
        "offered": False,
        # yarnnn wrote this agent; BLOGGER depends on it (ADR-601 D2).
        "kernel": True,
        "blurb": "Writes posts for readers outside the workspace.",
        "icon": "feather",
        "model": "anthropic/claude-sonnet-5",
        "token_profile": 8192,
        "posture": (
            "You are Blogger — the member's writer of published prose: posts, "
            "essays, pages read by someone outside the workspace. Write for "
            "that reader: they owe you nothing, so the title must earn the "
            "click, the standfirst must earn the scroll, and every section "
            "must earn the next. Work in the member's material rather than "
            "describing what you would do; keep their positioning and claims "
            "exactly as the workspace settled them — when the ask leans on "
            "something that may be settled (positioning, pricing, names, "
            "claims), recall it first (QueryKnowledge) and build from the "
            "decision; inventing over a settled decision is wrong, not "
            "creative. A draft is workspace material until the member "
            "publishes it — never present a draft as already public. When "
            "the ask is ambiguous, make the smallest honest version and say "
            "what you assumed."
        ),
    },
    # ADR-610 — the `keeper` row was HERE and is DELETED; ADR-639 — the
    # `supervisor` row was HERE and is DELETED, with the strings app and its
    # pane. Standing work is a KERNEL LANE, not an app: what a member declares
    # lives beside the kept file, what runs it is a daemon
    # (services/standing_work.py), how it is done is a skill
    # (keeping-a-file-current · declaring-standing-work), and who does it
    # DERIVES from what the file is (prose → text → Editor). ADR-610's own
    # rule decided it: a being is someone a member MEETS; once declaring was
    # craft any resident holds and the pane was gone, Supervisor was a name
    # on a receipt — what Keeper had been. Neither earns a row. Do not
    # reintroduce an agent for standing work; a proposal that answers "who
    # keeps this current?" with a name has put authority on an agent
    # (ADR-596 D2).
}

#: The keys a row may carry — identity + character + engine + reach. No
#: `tools` (reach is uniform, ADR-467 D4) and no authority-shaped key, ever:
#: the ADR-460 D3.a cliff, enforced as a whitelist rather than as prose.
AGENT_ROW_KEYS = frozenset(
    {"slug", "name", "blurb", "icon", "model", "token_profile", "posture",
     "offered", "kernel"}
)

#: Retired agents, by the name each signed as (ADR-639 D4). A deleted slug
#: still sits on the cast rows and transcript rows it joined (7 + 5 in
#: production for `supervisor`, 1 for `keeper` — measured 2026-09-04); those
#: rows are never rewritten (ADR-460 D2), so a transcript must still say
#: "Supervisor" where Supervisor spoke. The `freddie:` display-resolution
#: precedent, one hop further. DISPLAY ONLY: `resolve_agent` still answers
#: None for these, so nothing routes a turn to a retired name.
HISTORICAL_AGENT_NAMES: dict[str, str] = {
    "keeper": "Keeper",          # ADR-610
    "supervisor": "Supervisor",  # ADR-639
}


def historical_agent_name(slug: Optional[str]) -> Optional[str]:
    """The display name a RETIRED slug signed as, or None. Pure."""
    return HISTORICAL_AGENT_NAMES.get((slug or "").strip())


def resolve_agent(slug: str) -> Optional[dict]:
    """An agent by slug, or None. Pure.

    ADR-600: ONE register, so resolution is one lookup — a live lane or cast
    row pinning any historical slug resolves if and only if the row still
    exists. A deleted slug (`sonnet`, `scout`, `critic`, a member's `lisa`)
    resolves None: its historical turns keep their transcript rows, and new
    turns run bare-engine, which is honest.

    This resolves EVERY agent, offered or not — an app's resident must
    resolve for its own lanes to run. `offered` gates the INVITE (ADR-600
    D3), never the read.
    """
    return AGENTS.get((slug or "").strip())


def get_agent(slug: str) -> Optional[dict]:
    """An agent by slug, or None. Pure. (Alias of resolve.)"""
    return resolve_agent(slug)


class NotEditable(Exception):
    """A kernel agent was asked to change. Carries the reason, not just a no."""


def is_promoted(slug: str) -> bool:
    """Is any pane this agent serves PROMOTED to a member today? DERIVED.

    ADR-602 D3. An agent appears on the /agents pane when its work is somewhere
    a member actually goes. `launcher_tier_for` is the right predicate, NOT
    `is_exposed`: exposure asks *does this surface reach the served roster*
    (true even for `search-only`, which is reachable-but-unpromoted), while the
    pane's question is *would a member meet this agent in the normal course of
    using the product*. (IMAGES sat at `search-only` until ADR-629 promoted
    it, and Designer waited with it — the derivation is why promoting the app
    was the whole edit.)

    DERIVED, never a column on the agent: the surface registry already
    declares the stage (ADR-592), and a second copy here is the ADR-562
    second-home failure — it would drift the moment an app is promoted and
    nobody remembered to flip the agent. Deriving it means promoting the app
    promotes its voice, in one edit and with no gate to remember.

    Presentation only, in the same family as `offered`: it answers *is this
    agent's work in front of a member*, never *what may this agent do*.

    An agent serving NO pane is promoted only if it is OFFERED — a colleague
    lives on the roster, so having no app is its normal state. A non-offered
    being with no app is unreachable everywhere, and promoting it would mean
    a deleted app REGISTRATION leaks its orphaned resident onto the pane
    (fail-open) while a deleted surface row correctly withholds it. Audited
    2026-08-24: the asymmetry was real; this fails closed.
    """
    from services.app_stage import launcher_tier_for
    from services.kernel_surfaces import KERNEL_SURFACES

    homes = {a["slug"] for a in apps_for_agent(slug)}
    if not homes:
        agent = resolve_agent(slug)
        return bool(agent and agent.get("offered"))
    return any(
        launcher_tier_for(e) == "primary"
        for e in KERNEL_SURFACES
        if e.get("slug") in homes
    )


def assert_editable(slug: str) -> dict:
    """The agent, or raise — the ONE chokepoint for "may this row be edited?"

    ADR-601 D3. Built BEFORE the door it guards, deliberately: a protection
    written alongside the feature it constrains is one that feature's author
    may forget, and the ADR-563 lesson (guard at the chokepoint, never at call
    sites) applies just as well to a chokepoint whose callers are still to
    come. Any future member-facing edit path calls THIS — never re-derives it.

    Fails closed: an unknown slug is refused, not treated as member-authored.

    NOTE the asymmetry with `resolve_agent`, and keep it: reading an agent is
    never gated (a kernel agent must resolve for its own lanes to run). This
    gates the WRITE only.
    """
    agent = resolve_agent(slug)
    if agent is None:
        raise NotEditable(f"No agent called '{slug}'.")
    if agent.get("kernel"):
        # Named, with the reason — a generic refusal reads as a bug and sends
        # the member looking for a permission they can grant themselves.
        raise NotEditable(
            f"{agent.get('name') or slug} is a yarnnn system agent — it comes "
            "with the apps it works in, so its character is not editable here."
        )
    return agent


def apps_for_agent(slug: str) -> list[dict[str, str]]:
    """The apps this agent works in, as the APP's own identity. Pure-ish.

    ADR-601 D1 — many-to-one, so this is a LIST. Resolved from the app
    registrations (the same declaration the prompt reads), never stored on the
    agent: an app names its agents, and an agent that learns an app should
    not need editing to know it.

    ADR-604 D4 — an app is served whether the agent is its VOICE (`resident`)
    or its STANDING EXECUTOR (`standing_executor`); both count as working
    there. The mechanism stays after ADR-610 even though no app diverges the
    two today.

    ADR-631 — ONE relation, ONE name. This replaces `homes_for_agent` (slugs),
    `home_titles_for_agent` (titles) and `desks_for_agent` (the rich row):
    three functions and three envelope keys (`homes` / `home_titles` /
    `apps`) for one fact, in one payload. Each row carries the whole identity
    the surface row already declares — slug, title, `icon_key`, route — so the
    FE renders the SAME mark the Dock does (ADR-297's `resolveSurfaceIcon`),
    and a caller that wants only the slugs takes them off the rows. An app
    with no surface row still returns, titled by its slug and unrouted —
    showing the key beats dropping the app.
    """
    import services.apps  # noqa: F401  (registration side-effect)
    from services.authoring import all_apps
    from services.kernel_surfaces import KERNEL_SURFACES

    rows = (
        KERNEL_SURFACES
        if isinstance(KERNEL_SURFACES, list)
        else list(KERNEL_SURFACES.values())
    )
    by_slug = {r.get("slug"): r for r in rows if r.get("slug")}
    apps: list[dict[str, str]] = []
    for a in all_apps().values():
        if a.get("resident") != slug and a.get("standing_executor") != slug:
            continue
        row = by_slug.get(a["slug"]) or {}
        apps.append({
            "slug": a["slug"],
            "title": row.get("title") or a["slug"],
            "icon_key": row.get("icon_key") or "",
            "route": row.get("route") or "",
        })
    return apps


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
