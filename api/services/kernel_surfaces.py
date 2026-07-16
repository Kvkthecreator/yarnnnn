"""Kernel surfaces — ADR-297 Phase 1.

The canonical list of surfaces that exist in every YARNNN workspace,
regardless of which program bundles are active. Per ADR-297:

- Surfaces mirror substrate. Each kernel surface corresponds 1:1 to a
  substrate concept that exists in every workspace.
- Substrate location determines surface tier. Files under
  `/workspace/...` that the kernel scaffolds (or always-present DB
  tables) are kernel surfaces. Per-bundle substrate produces program
  surfaces (see composition_resolver.py + SURFACES.yaml). Operator-
  authored arbitrary substrate produces composed surfaces (forward
  horizon, D10).
- Each surface declares its archetype per ADR-198 (Document / Dashboard
  / Queue / Stream / Briefing — plus the catalog extensions Browser
  and Roster called out in ADR-297 D1).

This module is the **declaration**, not the rendering. The frontend
consumes the `surfaces[]` array emitted by `composition_resolver` and
renders each surface using kernel-library components. No render logic
here — pure data.

Phase 1 discipline: this file is additive. Phase 2 (shell rebuild)
will route the launcher + dock against these declarations. Phase 3
(container deletion) will collapse the existing `tabs` composition
output once every consumer has migrated to `surfaces[]`.
"""

from __future__ import annotations

from typing import Any


# =============================================================================
# Archetype enum — extends ADR-198's five with D1 + D11 catalog additions
# =============================================================================
#
# ADR-198 names five archetypes: document | dashboard | queue | briefing |
# stream. This module extends with two content-shape additions from
# ADR-297 D1 and three structural-role additions from ADR-297 D11:
#
#   ADR-297 D1 (content shapes — operator-facing reading):
#     - `browser` — interactive file/path navigation (the Files surface)
#     - `roster` — list-of-actors surface (the Agents surface)
#
#   ADR-297 D11 (structural — Universal Surface Application):
#     - `input` — writes substrate (composer, command bar, search field)
#     - `navigator` — lists/dispatches surface set (dock, launcher, breadcrumb)
#     - `chrome` — structural framing (top bar, status bar, brand mark)
#
#   ADR-331 D1 (guided ordered presentation):
#     - `sequence` — an ordered list of steps, each a *derived* status
#       (incomplete/complete computed from substrate at render time) + an
#       action affordance. The guided presentation of substrate that a
#       Dashboard presents random-access. Invariant: a Sequence surface
#       stores NO progress of its own — step status is always derived
#       (the archetype-level encoding of ADR-331's no-wizard-state rule).
#       Today: `/setup` (the only Sequence surface; generalizes cheaply
#       if a second guided flow appears — ADR-331 open question #4).
#
# Per ADR-297 D11: chrome-vs-content is not a special case at the
# architecture layer. Every operator-visible thing is a surface; the
# archetype classifies its reading/writing shape. Visibility policy (always
# visible / summon / pinned-only) is a separate 2nd-order concern handled
# by the compositor's layout regions.
#
# The TS mirror in web/lib/compositor/types.ts extends `Archetype` to
# match. Drift between this list and the TS union is a regression-gate
# failure target.

ARCHETYPES = (
    "document",
    "dashboard",
    "queue",
    "briefing",
    "stream",
    "browser",
    "roster",
    "input",
    "navigator",
    "chrome",
    "sequence",  # ADR-331 D1
)


# =============================================================================
# Kernel surfaces declaration
# =============================================================================
#
# Order in this list is the **canonical display order in the launcher's
# Workspace section**. The launcher renders them in this order under the
# subtle "Workspace" group header (ADR-297 D4 subtle tier grouping).
#
# `default_pinned: True` means the surface ships pinned by default in the
# operator's dock. Per ADR-297 D5: Feed only. Every other surface is
# summon-only until the operator pins it.
#
# `route` is the URL the launcher navigates to when the operator selects
# the surface. Phase 1: routes either already exist (created in prior
# ADRs) or are placeholders for Phase 2 to create. Routes for surfaces
# that don't yet have a dedicated page are marked with a `_route_status`
# comment for the Phase 2 implementation; the frontend's launcher consumer
# tolerates 404s during the transitional state.
#
# `substrate_paths` lists the workspace files this surface reads. Used
# by:
#   - Phase 2: to know which files to subscribe to / refetch when a
#     surface is active.
#   - Phase 3: to validate that container deletion didn't orphan a
#     substrate concept (every substrate path here must have a surface
#     hosting it).
# Some surfaces (Feed, Queue, Activity) read DB tables, not files; their
# `substrate_paths` is empty and the substrate-class is documented in
# the comment.
#
# `register` field (ADR-309 2026-06-01; cleaved by ADR-312 2026-06-02):
# which windowed register this surface belongs to. Required on every
# content surface; absent on chrome (chrome is the window manager's own
# framing, neither register).
#
# `launcher_tier` field (ADR-340 P3, 2026-06-12): the launcher's AT-REST
# grouping — derived from the operator's standing loop (ADR-340 D2/D5),
# NOT from the register (registers stay code-level taxonomy; ADR-338 IA
# Move A's register grouping is superseded by this tier model):
#   - "primary"     — the loop: Home (dwell) · Feed (read) · Queue (decide)
#                     · Files (artifacts). Foregrounded at rest.
#   - "configure"   — the ONE Settings door (ADR-347): the operation's
#                     settings — Constitution + Contract (Rhythm/Witness/
#                     Expected Output) + Operation + Perception. Its own
#                     launcher group "Settings". ADR-347 reversed ADR-341's
#                     two-door split: the account (Billing/Usage/Account) is
#                     the human/principal's concern → moved to the UserMenu
#                     (the `settings` slug becomes the account window,
#                     search-only); Governance (Autonomy/Budget) is
#                     per-operation config → moved INTO this door's Contract
#                     group. The "workspace-config" + "system-config" tier
#                     pair (ADR-341 D3) collapses to this one tier.
#   - "utilities"   — present, searchable, de-prioritized: Setup, Recurrence,
#                     Agents (the Activity-Monitor class; Activity folded to
#                     a Recurrence pane per ADR-340 D8).
#   - "search-only" — hidden at rest, found by flat search (ADR-340 D5
#                     "search stays flat"): the constitution mirrors
#                     (mandate/principles/identity — their FIRST-CLASS door
#                     is the Home constitution band, ADR-312 slot #1; their
#                     read/manage pane door is the one Settings door, ADR-347)
#                     and the pane-grade Settings panes (their door is the
#                     Settings container per `pane_of`); plus the account
#                     window (the `settings` slug, UserMenu-reached, ADR-347).
# Chrome entries (route="") have no tier — never listed.
#
# `pane_of` field (ADR-340 P2, 2026-06-12): pane-grade surfaces. A surface
# carrying `pane_of: "<parent-slug>"` is NOT window-grade — it renders as a
# sidebar pane INSIDE its parent's window (the macOS System Settings shape:
# one door, nested panes; depth under one well-named door is cheap, breadth
# at the top level is expensive — ADR-340 D4). The entry STAYS in the
# registry so the launcher's flat search still finds it (ADR-340 D5:
# "search stays flat") and its metadata (icon, summary, substrate_paths)
# stays canonical. Consumers:
#   - window manager: `foregroundSurface(pane-slug)` resolves to the parent
#     window + `?pane=` param (web/lib/shell/useSurfacePreferences.tsx)
#   - viewport + dock: pane-grade slugs are filtered from window mounting
#   - routes: the pane's legacy route is an ADR-308 server redirect stub →
#     `{parent.route}?pane={slug}`
# `pane_group` is the sidebar section label inside the parent container.
# Registers (below) are unchanged — pane-grade is orthogonal to register;
# it states WINDOW-GRADE vs PANE-GRADE, not which register owns the surface.
#
# ADR-312 D5 split ADR-309's single `settings` register — it conflated
# *the OS configuring itself* with *the operation declaring what it is*:
#   - `intent`       — the operation's authored intent: the constitution.
#                      Mandate, Principles, Identity. Surfaced FIRST-CLASS
#                      as the Home's Constitution band (slot #1), NOT buried
#                      in a config drawer. The mandate is the operation's
#                      charter, not a wifi setting.
#   - `os-config`    — the OS configuring itself. Autonomy, Pace, Connectors,
#                      Program, Settings. Glanceable in the menu-bar vitals
#                      (SystemStatusCluster); click-to-configure. Rarely
#                      opened. The operator does not author these to declare
#                      what the workspace is; they tune how the OS behaves.
#   - `application`  — Applications: open files + live state. A typed file,
#                      a folder/filesystem, or live state composed into a
#                      view. (Files, Home, Feed, Queue, Activity, Agents,
#                      Cadence.) Artifacts are files opened by Applications
#                      via the type→application association layer.
#
# ADR-297 D11 fields (optional; absent on legacy content surfaces, which
# default to the `main` region with `summon`-style visibility — i.e., the
# active atomic surface mounts to `main`):
#   - `default_region`: which named layout region the compositor mounts
#     this surface into. One of `main | main-rail | top | bottom-floating |
#     bottom-fixed | floating-overlay`. `main-rail` (ADR-316) is the
#     dockable command rail docked to the right of `main`'s window area —
#     a flex sibling of SurfaceViewport that *reduces* the surface area
#     rather than occluding it. Chat lives here, not in floating-overlay.
#   - `default_visibility`: when the compositor mounts it. One of
#     `always` (mounted whenever any authenticated surface is active),
#     `summon` (mounted only when explicitly opened — e.g., Launcher
#     overlay), `pinned-only` (mounted only if pinned by operator —
#     today: not used; reserved for future ops).
# The kernel ships default policy via these fields; operator overrides
# land in Phase D (out of scope for D11 minimum-viable).

KERNEL_SURFACES: list[dict[str, Any]] = [
    # ADR-385 follow-on (2026-06-30) — the legacy `feed` + `context` alias
    # surface entries are DELETED (full alias deletion). They were search-only
    # registry rows that still carried an `icon_key` + no `pane_of`, so any
    # stale persisted dock entry (`kept`/`open`/`foregrounded` naming `feed` or
    # `context` from before the renames) rendered a SECOND dock icon — for
    # `context`, an identical `arrow-left-right` glyph next to the live
    # `channels` icon — whose click bounced through the `/context`→`/channels`
    # (resp. `/feed`→ the narrative) redirect. That duplicate icon +
    # confusing-redirect was the operator-observed symptom.
    #
    # The slugs are now retired from the registry entirely. Bookmark safety for
    # the OLD external `/feed` + `/context` URLs moves to next.config.js
    # `redirects()` (pure server transport, ADR-308). Persisted dock state that
    # still names `feed`/`context` is normalized → `channels` at the
    # surface-preferences read boundary (lib/shell/surface-preferences.ts), so a
    # returning operator's kept icon collapses onto the live Channels icon —
    # no vanished icon, no duplicate. (Was: two search-only alias rows here.)
    {
        # ADR-412 D3 (2026-07-06) — Chat: the lanes surface, Altitude 2's
        # chrome home. The member's model-pinned helper threads (ADR-411)
        # get a windowed workbench: work-first recents (the model is a CHIP
        # on the row, never the namespace — D4), the conversation panel,
        # inline creation. Member-experience scope: the surface lists the
        # VIEWER's lanes in the acting workspace (ADR-407 D6) — it composes
        # chat_sessions lanes, not authored substrate, so substrate_paths
        # is honestly empty. The steward is NOT here (Altitude 1 lives in
        # the chat-drawer rail — D2); the slug's redirect-stub lineage
        # (ADR-259 → /feed, ADR-385 → notifications) ends — third life as
        # a real surface.
        #
        # ADR-435 (2026-07-10) — Chat is now FIRST in the primary (Workspace)
        # tier and the DEFAULT DOCK ANCHOR (`default_pinned: True`), inheriting
        # both roles from the deleted `home` surface. Chat is the steward's
        # operating voice + the activation landing for an empty workspace — "what
        # do you want to do," not a passive browser. Coherent with
        # DEFAULT_KEPT_SURFACES=['chat'] and the context/feed/channels/home
        # legacy-slug normalization → `chat`.
        "slug": "chat",
        "launcher_tier": "primary",  # ADR-412 D3
        "register": "application",
        "title": "Chat",
        "archetype": "stream",
        "substrate_paths": [],  # member-experience scope (chat_sessions lanes)
        "icon_key": "message-circle",
        "default_pinned": True,  # ADR-435 — dock anchor (was `home`)
        "route": "/chat",
        "summary": "Your model-pinned helper conversations — isolated lanes over the shared workspace. The transcript stays private to each lane; the work lands in files, attributed to you via the lane's model.",
    },
    {
        # ADR-440 (2026-07-10) — the Studio, the first AUTHORING app (the
        # second app class after ADR-436's viewer renderers). One surface ↔
        # one operator act: AUTHOR AN ARTIFACT — the first honest DP29
        # composition since ADR-435 deleted Home. Left pane = a BOUND lane
        # (ADR-411 machinery + an artifact binding + the authoring posture);
        # right pane = the live canvas over one self-contained HTML artifact.
        # Templates: Document · Deck · Article (kernel constants,
        # services/studio.py — apps bring program, not substrate, D6).
        "slug": "studio",
        "launcher_tier": "primary",  # ADR-440 D2 — the probe needs traffic
        "register": "application",
        "title": "Studio",
        "archetype": "document",
        "substrate_paths": [],  # artifacts are meaning-placed; no app namespace
        "icon_key": "palette",
        "default_pinned": False,
        "route": "/studio",
        "summary": "Author documents, decks, and articles as living artifacts: a model-pinned lane drafts and patches the file while the canvas re-renders it — every citation a live workspace reference, every edit an attributed revision.",
    },
    # ADR-415 (2026-07-08): the `channels` surface is DISSOLVED. It was a fossil
    # of the Feed → Context → Channels lineage, scoped by boundary (edge vs
    # interior) — an axis operators don't hold, producing two "what happened"
    # surfaces (Channels + Notifications→Activity). Its content re-homed along
    # the ACT each piece performs: Out (emissions) → the Activity Out lens; In →
    # retired (the timeline already carries inbound writes as revisions); AI
    # Connections → Access (the full roster already mounts there); Connections +
    # Sources → Workspace Settings → Perception (a management pane, un-hidden —
    # managing a connector ≠ running its capture lane). `/context` + `/channels`
    # redirect via next.config.js. See ADR-415, supersedes the Channels shape of
    # ADR-385/404/370/377.
    {
        # ADR-346 (2026-06-19) — the Operation surface, the SECOND composition
        # window (Home was the first, serving Dwell). A composition OVER the
        # operational mirrors, not a new mirror: one door for operating the
        # recurring work, with three SettingsPaneShell panes = the three acts
        # ADR-340 D2 named but never built a composition for:
        #   Resolve   (Decide) → the Queue body over action_proposals
        #   Understand (Read)   → FeedSurface narrative + the run ledger
        #   Tune      (Tune)    → RecurrenceList + Schedule/Runs lens toggle
        # Window-grade (no pane_of) — its panes are composition VIEWS that reuse
        # mirror bodies (one body, two mounts, the ADR-340 D8 rule), each with
        # an "Open full ___ →" escape hatch. substrate_paths [] — it composes
        # action_proposals + session_messages + _recurrences.yaml/execution_events.
        # Primary tier: the default destination for operating work; the mirrors
        # it fronts (Feed, Queue) demote to utilities in the same ADR.
        # ADR-349 (2026-06-19): renamed operation → notifications. The window
        # and the topbar Attention bell are the same object at two zooms (their
        # vocabulary was unified by ADR-346 §5a: To do · Activity · Coming up);
        # they now take one name — Notifications. The bell is the glance, this
        # window is the full surface. Pane keys (resolve/understand/tune) +
        # the ADR-340 D2 act identities (Decide/Read/Tune) are unchanged.
        "slug": "notifications",
        # 2026-07-04 — operator re-sort, step 2: Notifications leaves the
        # at-rest launcher ENTIRELY (was demoted to its own bottom group
        # 2026-07-01). The top-bar bell (ADR-349 D2 "one name, two zooms") is
        # the always-present door to this window on every screen size, so ANY
        # at-rest launcher tile is redundant chrome — the operator observed the
        # duplication on mobile and ruled it applies to all sizes. Still
        # summonable by name via flat search, still dockable while open.
        "launcher_tier": "search-only",  # fronted by the top-bar bell (was own bottom group)
        # 2026-07-08 — the top-bar bell (AttentionCenter) is this surface's
        # DEDICATED chrome door, so it must not ALSO render a generic Dock
        # tile: a Dock icon appears the moment the window enters `open`
        # (D14 kept ∪ open) — the exact "two doors for one thing" the
        # 2026-07-04 launcher re-sort ruled out, but `search-only` only
        # removed the LAUNCHER tile, not the Dock one. `chrome_fronted`
        # completes that intent: the Dock filters chrome-fronted surfaces
        # the same way it filters pane-grade ones, and the bell carries the
        # foregrounded highlight instead. Generic field (not a magic slug)
        # so any future status/chrome-fronted surface inherits the rule.
        "chrome_fronted": True,
        "register": "application",  # a windowed composition like home / workspace-settings
        "title": "Notifications",
        "archetype": "dashboard",  # composition over multiple substrates
        "substrate_paths": [],  # composes action_proposals + session_messages + _recurrences.yaml
        # ADR-349 D2: the Notifications window IS the top-bar bell at a second
        # zoom ("one name, two zooms"). It carries the SAME bell glyph the
        # AttentionCenter renders, so the Launcher tile, Dock icon, and top-bar
        # bell read as one object. (Was "gauge" — a vestige of the ADR-327-
        # retired /pace surface; that orphan mapping is removed FE-side.)
        "icon_key": "bell",
        "default_pinned": False,
        "route": "/notifications",
        "summary": "Operate the recurring work in one place — what wants your decision, what just happened, what's coming up.",
    },
    {
        # Renamed cadence → recurrence (2026-06-03). The surface's
        # substrate, hooks (useRecurrenceDetail), and detail logic already
        # spoke "recurrence" everywhere — only the surface label/slug/route
        # lagged. "Cadence" survives as a temporal-classification concept
        # (Recurring vs Reactive grouping; Pace's tempo tagline), NOT as
        # this surface's name. /cadence kept as a redirect stub.
        "slug": "recurrence",
        "launcher_tier": "search-only",  # ADR-349 — fronted by Notifications (Schedule pane); summon by name (was utilities)
        "register": "application",  # ADR-309 two-register model
        "title": "Recurrence",
        "archetype": "dashboard",
        "substrate_paths": [
            "/workspace/_recurrences.yaml",
            "/workspace/_hooks.yaml",
            "/workspace/persona/standing_intent.md",
        ],
        "icon_key": "clock",
        "default_pinned": False,
        "route": "/recurrence",
        "summary": "What's on the schedule — the recurring work this workspace runs, what fires when, and what your agent is standing watch on.",  # ADR-340 P4 F1: operator vocabulary
    },
    {
        # ADR-327 (2026-06-08) — budget repurposed from /pace (ADR-300, which
        # promoted pace from a cockpit-tab section to an atomic kernel surface).
        # Pace retired: "how often the agent works" is the Reviewer's allocation
        # problem within the dollar budget, not an operator dial. Document
        # archetype, operator-only edit, mirrors /autonomy's shape. Slotted
        # between /recurrence and /autonomy to keep Trigger-dimension surfaces
        # adjacent before transitioning into Mechanism (Autonomy) and Identity
        # (Identity / Brand / Principles) per axiom order.
        "slug": "budget",
        "launcher_tier": "search-only",  # ADR-340 P3
        "register": "os-config",  # ADR-312 D5 (was `settings`)
        # ADR-347 (2026-06-19): the two-door split is reversed — Governance
        # moves OUT of the dissolved System Settings door INTO the one
        # operation-settings door (workspace-settings), as the "Contract"
        # group (Rhythm · Witness · Expected Output — the operating contract).
        # Budget (Rhythm) is per-operation config, not machine config.
        # ADR-387 §6.4 (2026-06-30) moved the agent-scoped governance panes to
        # Freddie's roster pane. ADR-412 D5 (2026-07-06): re-homed pane_of agents → workspace-settings
        # (System Agent group) — Freddie left the roster; the steward's dials
        # live on the system layer. Still the agent's GRANT (ADR-366).
        # ADR-426 (2026-07-09): the System Agent group leaves Workspace Settings
        # and becomes its OWN door — re-homed pane_of workspace-settings →
        # system-agent (the "Freddie System Agent" door, same launcher plane as
        # Workspace Settings). foregroundSurface('budget') resolves there now.
        # ADR-454 D4 (2026-07-13): the door is REVERSED (the ambient steward) —
        # re-homed pane_of system-agent → workspace-settings, in an unbranded
        # "System" pane group. Same pane body (SystemAgentPanes), third move,
        # never duplicated. foregroundSurface('budget') resolves there now.
        "pane_of": "workspace-settings",
        "pane_group": "System",
        "title": "Budget",
        "archetype": "document",
        "substrate_paths": [
            "/workspace/governance/_budget.yaml",
        ],
        "icon_key": "wallet",
        "default_pinned": False,
        # ADR-327 D7/Phase 5: pace retired → /budget is the canonical surface.
        # ADR-347: pane-grade — /budget is a redirect stub → /workspace-settings?pane=budget.
        "route": "/budget",
        "summary": "The operation's dollar spend envelope — declared budget plus window-to-date utilization. The Reviewer allocates wakes within it.",
    },
    {
        # 2026-05-24 design polish: renamed from "delegation" to "autonomy"
        # to align with the substrate file (_autonomy.yaml) and the
        # operator's mental model. The schema field `default_delegation`
        # stays — it's the precise data-layer term for the delegated
        # level. At the operator surface the broader concept is Autonomy.
        # /delegation kept as a redirect stub for bookmark safety.
        "slug": "autonomy",
        "launcher_tier": "search-only",  # ADR-340 P3
        "register": "os-config",  # ADR-312 D5 (was `settings`)
        # ADR-347 (2026-06-19): Governance → the one operation-settings door's
        # Contract group (Witness dial = per-operation config, not machine).
        # ADR-387 §6.4 — Autonomy is a governance/ GRANT (the delegation ceiling
        # the agent runs under, ADR-366). ADR-412 D5 (2026-07-06): re-homed pane_of agents → workspace-settings (System Agent group).
        # ADR-426 (2026-07-09): re-homed pane_of workspace-settings → system-agent
        # (the "Freddie System Agent" door). foregroundSurface('autonomy') — the
        # Home autonomy badge deep-link — resolves there now, unchanged call site.
        # ADR-454 D4 (2026-07-13): the door is REVERSED (the ambient steward) —
        # re-homed pane_of system-agent → workspace-settings ("System" group).
        "pane_of": "workspace-settings",
        "pane_group": "System",
        "title": "Autonomy",
        "archetype": "document",
        "substrate_paths": [
            "/workspace/governance/_autonomy.yaml",
        ],
        "icon_key": "shield-check",
        "default_pinned": False,
        "route": "/autonomy",  # _route_status: NEW 2026-05-24 (renamed from /delegation)
        "summary": "How much the Reviewer can execute without operator approval. Switching levels requires confirmation.",
    },
    {
        # ADR-348 (2026-06-19) — Expected Output, operator-facing. ADR-345
        # shipped the concept + contract/_expected_output.yaml referent +
        # wake-envelope wiring backend-only; this is the FE the operator
        # sees + sets. The third Contract-group member (Rhythm · Witness ·
        # Expected Output). Governance-region: operator authors, Reviewer
        # reads-not-authors (ADR-345 / ADR-320). A floor-gated delivery
        # cadence, NEVER a quota (ADR-345 Goodhart guard).
        "slug": "expected-output",
        # ADR-418 — dormant: routeless, so no launcher_tier (the P3 gate treats a
        # routeless entry as chrome, which must carry no tier). Returns with the
        # per-agent contract FE (ADR-382 / ADR-414 §9b).
        "register": "os-config",  # governance-region machine config (like budget/autonomy)
        # ADR-387 §6.4 — Expected Output is the contract/ CONTRACT (what the
        # operator declares the agent owes, ADR-345/366).
        # ADR-412 D5 (2026-07-06): re-homed pane_of agents → workspace-settings (System Agent group).
        # ADR-418 (2026-07-08): DORMANT. Post ADR-414 D2/D6 the output contract is
        # a HIRED Altitude-3 agent's concern (ADR-408 D2 / ADR-382 §3), not the
        # steward's — and unlike identity/principles it has no constitution-band
        # door, so nothing else needs it reachable at Rung 1. The row stays in the
        # registry (so the surface concept survives + flat search still knows it),
        # but drops `route` + `pane_of` + `pane_group`: routeless (non-navigable,
        # like chrome), off the FE allowlist (desk.ts), stub neutralized. It
        # returns when the per-agent contract pane is built (ADR-382 / ADR-414 §9b
        # per-agent FE). No `_route_status` route: dormant by design.
        "title": "Expected Output",
        "archetype": "document",
        "substrate_paths": [
            "/workspace/contract/_expected_output.yaml",
        ],
        "icon_key": "target",
        "default_pinned": False,
        "route": "",  # ADR-418 — dormant: non-navigable until the per-agent FE (ADR-382)
        "summary": "What the operation owes when it works — the output contract (kind + delivery-cadence + bar). A floor-gated cadence, never a quota. (Dormant per ADR-418 until the hired-agent contract pane is built.)",
    },
    {
        "slug": "mandate",
        # ADR-421 (2026-07-08): DORMANT. A workspace has NO constitution of its
        # own — a mandate is a hired Altitude-3 agent's declared intent (ADR-414
        # D6), read from agents/{slug}/MANDATE.md and surfaced on the agent
        # detail (AgentConstitutionBlock, ADR-419). The workspace-level Mandate
        # pane + its Home-band link + its route are removed; the surface concept
        # survives in the registry (flat search) but is non-navigable. The Home
        # HEADER still reads MANDATE.md content directly via the home-bundle
        # (independent of this surface) until the ADR-414 §9b Home recompose.
        "register": "intent",
        "title": "Mandate",
        "archetype": "document",
        "substrate_paths": [
            "/workspace/constitution/MANDATE.md",
        ],
        "icon_key": "target",
        "default_pinned": False,
        "route": "",  # ADR-421 — dormant: non-navigable (mandate is per-agent)
        "summary": "A hired agent's declared intent — its Primary Action. Not a workspace-level concept (ADR-421); surfaced on the agent detail. (Dormant.)",
    },
    {
        "slug": "principles",
        # ADR-421 (2026-07-08): DORMANT. A workspace has no principles of its
        # own — a judgment framework belongs to whoever holds the seat: the
        # steward (kernel constant, ADR-414 D2) or a hired agent (agents/{slug}/
        # principles.md, surfaced on the agent detail). The workspace-level pane
        # + Home-band link + route are removed. (ADR-419 had re-homed it to the
        # Constitution group as an interim; ADR-421 removes the workspace surface.)
        "register": "intent",
        "title": "Principles",
        "archetype": "document",
        "substrate_paths": [
            "/workspace/persona/principles.md",
            "/workspace/persona/_principles.yaml",
        ],
        "icon_key": "scale",
        "default_pinned": False,
        "route": "",  # ADR-421 — dormant: non-navigable (principles are per-agent)
        "summary": "A hired agent's judgment framework and decision thresholds. Not a workspace-level concept (ADR-421); surfaced on the agent detail. (Dormant.)",
    },
    {
        "slug": "identity",
        # ADR-421 (2026-07-08): DORMANT. A workspace has no persona of its own —
        # a reasoning-character belongs to the steward (kernel constant, ADR-414
        # D2) or a hired agent (agents/{slug}/IDENTITY.md, surfaced on the agent
        # detail). The workspace-level pane + Home-band link + route are removed.
        # (ADR-419 had re-homed it to the Constitution group as an interim;
        # ADR-421 removes the workspace surface.)
        "register": "intent",
        "title": "Identity",
        "archetype": "document",
        "substrate_paths": [
            "/workspace/persona/IDENTITY.md",
        ],
        "icon_key": "user-circle",
        "default_pinned": False,
        "route": "",  # ADR-421 — dormant: non-navigable (persona is per-agent)
        "summary": "A hired agent's persona — voice, role, reasoning-character. Not a workspace-level concept (ADR-421); surfaced on the agent detail. (Dormant.)",
    },
    # ADR-309 (2026-06-01): the `brand` kernel surface is DELETED. Brand is
    # not a standalone surface — the Identity Settings pane (IdentityBrandCard)
    # co-renders BRAND.md alongside IDENTITY.md. /brand is a server redirect →
    # /identity (ADR-308). BRAND.md substrate is unchanged; only the dedicated
    # surface is removed.
    {
        "slug": "files",
        "launcher_tier": "primary",  # ADR-340 P3
        "register": "application",  # ADR-309 two-register model
        "title": "Files",
        "archetype": "browser",
        "substrate_paths": [],  # All paths under workspace_files
        "icon_key": "folder",
        "default_pinned": False,
        "route": "/files",  # _route_status: EXISTING — slug/route/label all coherent (legacy /context is a redirect stub)
        "summary": "Raw substrate browser — every file in the workspace, with revision history.",
    },
    {
        "slug": "agents",
        # ADR-349 D3 made the roster Workspace-tier first-class (A3 the judgment
        # seat). Demoted to search-only (2026-07-08) because Altitude-3 "hire an
        # agent" was the deferred horizon: the launch focus was the user's HANDS
        # (the A2 chat lanes), not the user's HIRE, and a roster beside /chat
        # would be "a second, confusing AI door". That comment predicted a
        # one-word revert when "the Rung-2 track-record clock says it's time."
        #
        # RE-SURFACED 2026-07-16 — and NOT by that clock. Both clauses of the
        # demotion inverted by a different route:
        #   1. HANDS-not-HIRE: hiring IS the launch focus now. Sonnet/Scout/
        #      Critic are hired today; a member names their own (ADR-460 D4 +
        #      the personified widening).
        #   2. "a second, confusing AI door": that fear was A2-vs-A3 — two KINDS
        #      of AI needing two doors. ADR-460 D1 DISSOLVED that ladder. There
        #      is one kind, and its door was a <select> inside a form.
        # This does NOT re-open Rung 2. Consequential authority is still
        # unrepresentable (ADR-460 D3.a) and /agents must never become the
        # persona-seat surface by accident — every pane here is identity or
        # capability, never authority.
        # Receipt: the `agents` TABLE is empty (ADR-414 retired the last row);
        # this surface now mirrors the workspace's Agent FOLDERS + the kernel
        # set, not that table.
        # Derivation: docs/analysis/agents-surface-and-debt-2026-07-16.md
        # Freddie's own dials stay at Workspace Settings → System Agent
        # (ADR-412 D5), not here.
        "launcher_tier": "primary",
        "register": "application",  # ADR-309 two-register model
        "title": "Agents",
        "archetype": "roster",
        "substrate_paths": [],  # agents DB table + per-agent substrate
        "icon_key": "users",
        "default_pinned": False,
        "route": "/agents",  # _route_status: EXISTING — hired-agent detail + roster live here
        "summary": "Agent roster — hired Altitude-3 persona agents (the deferred horizon; A2 chat lanes are the launch AI surface).",
    },
    {
        # ADR-437 (2026-07-10): DORMANT — the guided first-boot SEQUENCE surface
        # is DELETED. It was built on the pre-pure-workspace model (ADR-414 D4/D5:
        # genesis is empty, programs are anytime hires; ADR-421: a workspace has
        # no constitution to author). The activation model reframes to two channels
        # (cold discovery → the default landing with a deliberate empty state;
        # invited/shared → one accept surface, the shared-artifact wedge) — neither
        # needs a wizard. No `route`, no `launcher_tier` — non-navigable; the row
        # survives for flat search only (mirrors ADR-421/432 dormant-slug pattern).
        # `/setup` is a bookmark-safe redirect → /chat (web/next.config.js).
        "slug": "setup",
        "register": "os-config",  # ADR-309/312 — it configured the OS (dormant)
        "title": "Setup",
        "archetype": "sequence",
        "substrate_paths": [],
        "icon_key": "rocket",
        "default_pinned": False,
        "summary": "Guided first-boot sequence (DORMANT — ADR-437 deleted the wizard).",
    },
    {
        "slug": "program",
        # ADR-432 D2d (2026-07-09): DORMANT — mirrors the ADR-421 mandate/identity
        # dormancy. The operator-facing Program PANE (the "hire a program"
        # activation UI) is retired: zero hired-program grants exist anywhere,
        # activation has never fired, and it presented a launch operator an action
        # into the deliberately-unvalidated Rung-2 path (ADR-380). No `pane_of`, no
        # `pane_group`, no `route`, no `launcher_tier` — non-navigable, the surface
        # concept survives in the registry (flat search) only. The hire MACHINERY
        # is untouched (getState available_programs / active_program_slug, the
        # compositor ProgramCockpit, routes/programs.py, ProgramLifecycleDrawer via
        # SetupSequence). Activation re-surfaces on /agents when ADR-382 builds the
        # hired-agent roster (ADR-432 D2c).
        "register": "os-config",  # ADR-312 D5 (was `settings`)
        "title": "Program",
        "archetype": "document",
        "substrate_paths": [
            "/workspace/_program.yaml",
        ],
        "icon_key": "package",
        "default_pinned": False,
        "summary": "Active program bundle, phase, and capability gaps.",
    },
    {
        # ADR-346 (2026-06-19) — Queue demoted primary → utilities. The
        # Operation composition fronts it (Resolve pane mounts the same Queue
        # body over the same action_proposals — ADR-307 one gate, one queue
        # preserved). Queue stays the complete decide mirror, reachable +
        # searchable; the Attention bell + Operation are now the default route in.
        "slug": "queue",
        "launcher_tier": "search-only",  # ADR-349 — fronted by Notifications (To do pane); summon by name (was utilities, ADR-346)
        "register": "application",  # ADR-309 two-register model
        "title": "Queue",
        "archetype": "queue",
        "substrate_paths": [],  # action_proposals DB table (pending state)
        "icon_key": "inbox",
        "default_pinned": False,
        "route": "/queue",  # _route_status: NEW in Phase 2 — extracts proposal queue from /work or /agents context
        "summary": "Pending proposals awaiting Reviewer or operator decision.",
    },
    {
        # ADR-340 D8 (2026-06-18) — Machinery consolidation. Activity folds
        # to pane-grade under Recurrence: the two surfaces are one operator
        # concern ("the machinery") seen at two moments — declaration
        # (_recurrences.yaml, "what fires when") and execution
        # (execution_events, "did it run, what did it cost"). Declaration-led:
        # /recurrence is the window, Activity is the Runs lens reached via
        # ?pane=activity. Generic P2 pane_of mechanism (nothing hardcodes
        # `settings` as the only valid parent). Mirror discipline intact —
        # the substrate read + route + deep-link all survive (§11/§12); only
        # the launcher tile count drops (Utilities 4 → 3).
        "slug": "activity",
        "launcher_tier": "search-only",  # ADR-340 D8 — pane-grade, hidden at rest, found via flat search
        "register": "application",  # ADR-309 two-register model
        "pane_of": "recurrence",  # ADR-340 D8 — Runs lens inside the Recurrence window
        "pane_group": "Machinery",
        "title": "Activity",
        "archetype": "stream",
        "substrate_paths": [],  # execution_events DB table
        "icon_key": "activity",
        "default_pinned": False,
        "route": "/activity",  # ADR-308 server redirect stub → /recurrence?pane=activity (ADR-340 D8)
        "summary": "What ran and what it cost — the execution log behind the Feed's story. Open when you're checking the machinery, not the narrative.",  # ADR-340 P4 F1: operator vocabulary
    },
    # ADR-297 D19.4 (2026-05-22) — Settings + Connectors promoted from
    # legacy pages to atomic kernel surfaces. Reverses D19.7 ("settings
    # stays a page") after operator surfaced the real axiom violation:
    # the legacy isLegacyNonAtomicRoute branch in SurfaceViewport
    # returns <>{children}</>, which REPLACES the Desktop layer + all
    # open windows when the operator clicks Settings — that's the
    # opposite of the OS metaphor. macOS Preferences opens ON TOP of
    # existing apps. Both surfaces are now windowed; intra-surface tabs
    # (?tab=billing on Settings; per-platform expansion on Connectors)
    # remain as window-internal deep-link state per D19.4.
    {
        # ADR-347 (2026-06-19) — the two-door split is reversed. This surface
        # is NO LONGER a launcher door. It shrinks to the ACCOUNT window the
        # the human/principal's concern (Billing · Usage · Account),
        # program-agnostic and cross-workspace — the machine/account level, NOT
        # operation config. Governance (Autonomy/Budget) lives on the
        # operation door (workspace-settings, the Contract group).
        # ADR-349 D4 (2026-06-19): the operator re-split the launcher into two
        # settings doors — this re-promotes to an at-rest launcher door,
        # `system-config` tier. Still ALSO reachable from the UserMenu (two
        # doors, one window — fine).
        # 2026-07-08 (naming-coherence pass): titled "User Settings" — its
        # content is Billing · Usage · Account, all user_id-scoped (the human,
        # not "the machine"). "System Settings" read like OS/machine config and
        # fought both its own content and the UserMenu's "Account" label. Now
        # ONE render name — "User Settings" — everywhere a human reads it
        # (window title + launcher group + UserMenu item). The `settings` slug +
        # /settings route STAY (naming-drift policy: rename stops at the render
        # layer; keep-slug below — GLOSSARY §Exceptions, ratified 2026-07-08).
        "slug": "settings",
        "launcher_tier": "system-config",  # ADR-349 D4 — re-promoted to a launcher door (was search-only/UserMenu-only, ADR-347)
        "register": "os-config",  # ADR-312 D5 (was `settings`)
        "title": "User Settings",
        "archetype": "dashboard",
        "substrate_paths": [],  # account/billing — DB + Stripe; user_id-scoped (ADR-171/172)
        # 2026-07-08 icon swap: User Settings takes the `user-circle` (account)
        # glyph — its content is the human/principal's account (billing, usage,
        # privacy), so an account-person icon reads truer than a gear. The gear
        # (`settings`) moves to Workspace Settings (the operation config door).
        "icon_key": "user-circle",
        "default_pinned": False,
        "route": "/settings",
        "summary": "User Settings — your account: billing, usage, and data/privacy. Program-agnostic, cross-workspace (user_id-scoped). Also reachable from the avatar menu.",
    },
    {
        # ADR-341 (2026-06-18) created the second door; ADR-347 (2026-06-19)
        # makes it THE one Settings door — the operation's settings. It
        # configures THIS operation (the constitution/ + operation/ + persona/
        # + governance/ roots). Container surface; renders the shared pane
        # shell. Sidebar groups: Constitution (Mandate/Identity/Principles —
        # read/manage; first-class door stays the Home band, ADR-312 D5),
        # Contract (Budget=Rhythm · Autonomy=Witness · Expected Output — the
        # operating contract, moved in by ADR-347), Operation (Program),
        # Access (members). Perception left: Connectors → the account door
        # (ADR-425 — a credential is a human's account object), Sources hidden.
        # The account moved OUT to the UserMenu (ADR-347 D2).
        # ADR-349 D4 (2026-06-19): the operator re-split the launcher into two
        # settings doors. This is the OPERATION door, titled "Workspace
        # Settings", `workspace-config` tier (above User Settings).
        # 2026-07-08 icon swap: Workspace Settings takes the `settings` GEAR —
        # it's the operation-configuration door, the truest "settings" surface.
        # User Settings (the account) took the `user-circle` glyph, so the two
        # doors still read apart.
        "slug": "workspace-settings",
        "launcher_tier": "workspace-config",  # ADR-349 D4 — the operation door (re-split from ADR-347's one `configure` tier)
        "register": "application",  # a windowed app like `settings`
        "title": "Workspace Settings",
        "archetype": "dashboard",
        "substrate_paths": [],  # constitution/ + governance/ + operation/ + persona/ reads
        "icon_key": "settings",
        "default_pinned": False,
        "route": "/workspace-settings",
        "summary": "Workspace Settings — what this operation is and how it runs. Program, Access (members), Billing/Usage. (ADR-426 moved the System Agent dials to their own door; ADR-425 moved Connectors to the account door + hid Sources.)",
    },
    {
        # ADR-426 (2026-07-09) — Freddie System Agent: the system agent's own
        # settings door. The System Agent group (ADR-412 D5 / ADR-418: Autonomy ·
        # Budget · Capabilities · Activity) leaves Workspace Settings and becomes
        # its own window-grade surface on the SAME launcher plane as Workspace
        # Settings + User Settings — three sibling doors, three altitudes: the
        # operation (workspace-settings) · the system agent (this) · the human
        # (settings). The panes are the SAME SystemAgentPanes bodies (Singular
        # Implementation — the group moved, not duplicated); the budget/autonomy
        # rows re-point pane_of → system-agent (above). Its own launcher tier
        # `system-agent-config` renders the "Freddie System Agent" group right
        # after Workspace Settings (Launcher.tsx KERNEL_TIER_GROUPS). Steward-
        # coupled (STEWARD_SURFACE_SLUGS): when AGENT_ENABLED is off the system
        # agent has no dials to tune, so the door filters out (ADR-375 §6). The
        # door carries the proper noun "Freddie System Agent" (ADR-426 D3 —
        # reverses ADR-412 D5's role-only label ruling now that the panes have
        # their own frame; the rail stays Freddie's conversational home, ADR-412 D1).
        # ADR-454 D4 (2026-07-13) — the door is REVERSED (the ambient steward):
        # the persona-fronting third settings door retires. hidden (hide-not-
        # delete, the ADR-425 D2 sources precedent); launcher tier drops to
        # search-only… and `hidden` keeps it out of route parity; the dials
        # (autonomy/budget) re-home pane_of → workspace-settings ("System"
        # group); /system-agent is a next.config redirect stub →
        # /workspace-settings?pane=autonomy. Row retained for any re-light.
        "slug": "system-agent",
        "hidden": True,  # ADR-454 D4 — no operator door; renders in no pane
        "launcher_tier": "search-only",  # ADR-454 D4 (was system-agent-config, ADR-426)
        "register": "application",  # a windowed app like workspace-settings / settings
        "title": "Freddie System Agent",
        "archetype": "dashboard",
        "substrate_paths": [],  # governance/_autonomy.yaml + governance/_budget.yaml (via the pane bodies)
        # ADR-426 amendment (2026-07-09): the door wears Freddie's OWN mark — the
        # mascot face (FreddieAvatar, the chat-rail FAB face), not the generic
        # shield-check (which also read as the Autonomy pane glyph). The `freddie`
        # icon_key resolves to the still mascot in resolveSurfaceIcon.
        "icon_key": "freddie",
        "default_pinned": False,
        "route": "/system-agent",
        "summary": "Freddie System Agent — how the system agent is configured. Its two operator-tunable dials (Autonomy = the witness dial, Budget = the allocation) plus its read-only legibility (Capabilities · Activity).",
    },
    {
        "slug": "connectors",
        "launcher_tier": "search-only",  # ADR-340 P3
        "register": "os-config",  # ADR-312 D5 (was `settings`)
        "pane_of": "settings",  # ADR-425 — a platform credential is an account object; the Connectors pane lives in the account door (the UserMenu window), not Workspace Settings. Re-homed from workspace-settings (ADR-415) → settings.
        "pane_group": "Connections",
        "title": "Connectors",
        "archetype": "dashboard",
        "substrate_paths": [],  # platform_connections DB table (account-scoped, user_id — ADR-425)
        "icon_key": "link-2",
        "default_pinned": False,
        "route": "/connectors",
        "summary": "Your platform connections (Slack, Notion, GitHub, Alpaca, Lemon Squeezy, etc.) — each is your own credential, in your account. Connect, see status, disconnect.",
    },
    {
        # ADR-425 D2 (2026-07-09): Sources is HIDDEN from the operator surface.
        # It has no pane home — `pane_of`/`pane_group` stripped so it renders
        # nowhere; the row is retained (hide-not-delete) so the slug still
        # resolves for the /sources redirect stub and so the substrate + GET
        # /api/sources + SourcesCard stay intact for a future first-class home
        # (ADR-425 OQ3). A standing web/RSS watch is the operation watching the
        # world (ADR-336/338) — a legitimate concern, but not one the operator
        # manages today; it returns as its own thing, not grouped with a human's
        # OAuth connectors under a cosmetic "Perception" label.
        "slug": "sources",
        "launcher_tier": "search-only",  # ADR-340 P3
        "register": "os-config",  # ADR-312 D5 — a transport/driver binding
        "hidden": True,  # ADR-425 D2 — no operator door; renders in no pane
        "title": "Sources",
        "archetype": "dashboard",
        "substrate_paths": [],  # per-bundle _sources.yaml + _watch_signal.yaml, resolved via GET /api/sources
        "icon_key": "rss",
        "default_pinned": False,
        "route": "/sources",  # redirect stub → /home (ADR-425 D2); substrate retained
        "summary": "Standing-watch sources — the web/RSS feeds the operation reads on cadence. Hidden from the operator surface (ADR-425 D2); substrate retained for a future first-class home.",
    },
    # =========================================================================
    # ADR-297 D11 — Chrome surfaces (Universal Surface Application)
    # ADR-297 D12 — Top-center merged dock-bar (2026-05-21)
    # =========================================================================
    #
    # These chrome entries dissolve the chrome-as-special-case in
    # AuthenticatedLayout.tsx. The compositor mounts them into named
    # layout regions via `default_region`. They are NOT navigable from
    # the launcher (`route` is "" — the launcher consumer filters out
    # entries with no route). They are NOT pinnable (`default_pinned` is
    # always False). They participate in the kernel surface registry
    # purely so the compositor has a single source of truth for what
    # mounts where.
    #
    # D12 (2026-05-21) collapsed the prior 4-entry chrome set (top-bar,
    # dock, launcher, chat-composer) to 3 entries. The `dock` kernel
    # surface is DELETED — its responsibility (rendering pinned-surface
    # icons + dispatching `setSurface` on click) absorbs into the
    # top-bar body. The launcher's overlay still mounts in
    # `floating-overlay`; only the *trigger button* moves into the
    # top-bar body. See ADR-297 §D12 for rationale (Singular
    # Implementation + composer real estate + visual hierarchy).
    {
        "slug": "top-bar",
        "title": "Top Bar",
        "archetype": "chrome",
        "substrate_paths": [],  # reads useSurfacePreferences().pinned for the merged dock-bar body
        "icon_key": "layout-top",
        "default_pinned": False,
        "route": "",  # not navigable; structural framing only
        "summary": "Top-center merged dock-bar — brand · launcher trigger · pinned surfaces · user menu (D12).",
        "default_region": "top",
        "default_visibility": "always",
    },
    {
        "slug": "launcher",
        "title": "Launcher",
        "archetype": "navigator",
        "substrate_paths": [],  # reads composition.surfaces[] (full registry)
        "icon_key": "layout-grid",
        "default_pinned": False,
        "route": "",  # not navigable; summon-only overlay
        "summary": "Full surface index overlay — type-to-filter, per-row pin toggle, tier grouping. Trigger lives in top-bar (D12).",
        "default_region": "floating-overlay",
        "default_visibility": "summon",
    },
    {
        # D16 (2026-05-22): chat-composer renamed → chat-drawer; region
        # flips bottom-fixed → floating-overlay; visibility flips
        # always → summon. The pre-D16 bottom-strip composer dissolves
        # into a FAB + slide-over drawer pattern (universal generalization
        # of /feed's ADR-289 ConversationDrawer). See ADR-297 §D16.
        #
        # ADR-316 (2026-06-04): region flips floating-overlay → main-rail.
        # Chat is the command-line OVER the active surface — a dockable
        # rail that reduces the surface area, not an overlay that occludes
        # it. The FAB still summons it; on desktop it docks to main's right
        # (surface reflows), on mobile it degrades to a full-screen overlay
        # (the isMobile branch in ChatDrawer). The "Viewing: X" label is
        # now honest because the surface stays visible. See ADR-316.
        "slug": "chat-drawer",
        "title": "Chat Drawer",
        "archetype": "input",
        "substrate_paths": [],  # writes session_messages DB table
        "icon_key": "message-circle",
        "default_pinned": False,
        "route": "",  # not navigable; FAB-summoned command rail
        "summary": "Operator command rail — FAB summons a dockable right rail (desktop) / overlay (mobile) with composer + addressed-conversation timeline, scoped to the foregrounded surface.",
        "default_region": "main-rail",
        "default_visibility": "summon",
    },
]


# =============================================================================
# Public helpers
# =============================================================================


# ADR-375 §6 chokepoint #4 — the steward-coupled surfaces. When
# AGENT_ENABLED is off (Phase-1 interop-first deploy), these are filtered
# out of the surface registry. Backend-driven nav → zero FE change. The
# keepers (ledger + membrane + constitution mirrors + structural chrome)
# always render: files, channels (the perception+principal surface, ADR-385;
# was context), connectors/sources, settings/workspace-settings,
# identity/mandate/principles, home (substrate-forward empty state per
# ADR-374), budget, top-bar/launcher/chat-drawer/setup.
STEWARD_SURFACE_SLUGS: frozenset[str] = frozenset({
    "agents",
    "queue",
    "notifications",
    "autonomy",
    "program",
    "recurrence",
    "expected-output",
    "activity",
    # ADR-426 — the Freddie System Agent door. When AGENT_ENABLED is off the
    # system agent has no dials to tune, so its door filters out with the rest
    # of the steward-coupled surfaces. (budget is intentionally NOT here — it is
    # a per-principal allocation that stands even without the internal steward.)
    "system-agent",
})


def kernel_surface_entries() -> list[dict[str, Any]]:
    """Return the kernel surface list with `tier: "kernel"` added.

    This is the shape the compositor emits into `surfaces[]`. Always
    returns a deep copy so callers can mutate freely without affecting
    the canonical declaration.

    ADR-375 §6 chokepoint #4: when the internal steward is gated off
    (`is_agent_enabled()` is False), the steward-coupled surfaces
    (`STEWARD_SURFACE_SLUGS`) are filtered out. The nav is 100%
    backend-driven (ADR-297), so this removes the steward tabs from the UI
    with zero frontend change. The default is ON (ADR-375 D4), so the
    full registry is returned unless a deploy explicitly sets
    `AGENT_ENABLED=false`.
    """
    from copy import deepcopy
    from services.agent_gating import is_agent_enabled

    agent_on = is_agent_enabled()

    return [
        {**deepcopy(entry), "tier": "kernel"}
        for entry in KERNEL_SURFACES
        if agent_on or entry["slug"] not in STEWARD_SURFACE_SLUGS
    ]


def kernel_surface_slugs() -> set[str]:
    """Set of all kernel surface slugs. Useful for test gates and
    validation — every kernel surface must be present in every
    workspace's `surfaces[]` output."""
    return {entry["slug"] for entry in KERNEL_SURFACES}


def kernel_pane_slugs() -> set[str]:
    """Slugs of pane-grade surfaces (ADR-340 P2) — registry entries
    carrying `pane_of`. These render as sidebar panes inside their
    parent's window, never as windows of their own. Used by test gates
    and the FE parity check."""
    return {entry["slug"] for entry in KERNEL_SURFACES if entry.get("pane_of")}


__all__ = [
    "ARCHETYPES",
    "KERNEL_SURFACES",
    "STEWARD_SURFACE_SLUGS",
    "kernel_surface_entries",
    "kernel_surface_slugs",
    "kernel_pane_slugs",
]
