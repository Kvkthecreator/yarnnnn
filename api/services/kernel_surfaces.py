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
#   - "system"      — System Settings, the one os-config door (panes fold
#                     inside it per `pane_of`).
#   - "utilities"   — present, searchable, de-prioritized: Setup, Activity,
#                     Recurrence, Agents (the Activity-Monitor class).
#   - "search-only" — hidden at rest, found by flat search (ADR-340 D5
#                     "search stays flat"): the constitution mirrors
#                     (mandate/principles/identity — their door is the
#                     Home constitution band, ADR-312 slot #1) and the
#                     pane-grade Settings panes (their door is System
#                     Settings).
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
    {
        "slug": "feed",
        "launcher_tier": "primary",  # ADR-340 P3
        "register": "application",  # ADR-309 two-register model
        "title": "Feed",
        "archetype": "stream",
        "substrate_paths": [],  # session_messages DB table
        # ADR-297 D18.2 (2026-05-22): Feed Dock icon swapped from
        # message-circle → scroll-text. message-circle was visually
        # identical to the universal ChatDrawer FAB (also a chat
        # bubble), causing operator confusion. Feed is a narrative
        # ledger (every invocation, every wake, append-only) — the
        # scroll glyph reads as "log / timeline / ledger" without
        # colliding with the conversation summon.
        "icon_key": "scroll-text",
        "default_pinned": True,
        "route": "/feed",
        "summary": "Operator chat surface and multi-actor narrative timeline.",
    },
    {
        # ADR-312 D1 (2026-06-02): the cockpit surface renames to `home`.
        # The home is a composition over the workspace's present
        # constituents (six kernel slots, top→bottom; the program declares
        # each slot's weight/label/shape via the compositor) — substrate-
        # forward when empty, operation-forward when a program runs. The
        # four-face stack (ADR-228) and fixed trader section sequence
        # (ADR-273) survive ONLY as a program's declared composition, never
        # as the kernel default. The atomic Home surface hosts HomeRenderer.
        # (Was: ADR-297 D1 cockpit, the 13th kernel surface.)
        "slug": "home",
        "launcher_tier": "primary",  # ADR-340 P3
        "register": "application",  # ADR-309 / ADR-312 D5 two-register model
        "title": "Home",
        "archetype": "dashboard",
        "substrate_paths": [
            "/workspace/constitution/MANDATE.md",
            "/workspace/governance/_autonomy.yaml",
            "/workspace/operation/_performance.md",
            "/workspace/operation/_performance_summary.md",
        ],
        # 2026-06-03: icon → `home`. Post the ADR-312 cockpit→home rename the
        # square-activity glyph (a "live operations monitor" shape) no longer
        # matched the surface's name or operator mental model. The literal
        # home glyph reads unambiguously as "the home surface."
        "icon_key": "home",
        "default_pinned": False,
        "route": "/home",  # ADR-312 D1 (was /cockpit)
        "summary": "The operation, rendered — constitution, ground-truth, decision queue, live entities, recent artifacts, judgment trail. Composition over the workspace's present constituents.",
    },
    {
        # Renamed cadence → recurrence (2026-06-03). The surface's
        # substrate, hooks (useRecurrenceDetail), and detail logic already
        # spoke "recurrence" everywhere — only the surface label/slug/route
        # lagged. "Cadence" survives as a temporal-classification concept
        # (Recurring vs Reactive grouping; Pace's tempo tagline), NOT as
        # this surface's name. /cadence kept as a redirect stub.
        "slug": "recurrence",
        "launcher_tier": "utilities",  # ADR-340 P3
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
        "summary": "Recurrences, substrate-event hooks, standing intent, and wake telemetry.",
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
        "pane_of": "settings",  # ADR-340 P2 — Governance pane in System Settings
        "pane_group": "Governance",
        "title": "Budget",
        "archetype": "document",
        "substrate_paths": [
            "/workspace/governance/_budget.yaml",
        ],
        "icon_key": "wallet",
        "default_pinned": False,
        # ADR-327 D7/Phase 5: pace retired → /budget is the canonical surface.
        # ADR-340 P2: pane-grade — /budget is a redirect stub → /settings?pane=budget.
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
        "pane_of": "settings",  # ADR-340 P2 — Governance pane in System Settings
        "pane_group": "Governance",
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
        "slug": "mandate",
        "launcher_tier": "search-only",  # ADR-340 P3
        "register": "intent",  # ADR-312 D5 — constitution band, slot #1 (was `settings`)
        "title": "Mandate",
        "archetype": "document",
        "substrate_paths": [
            "/workspace/constitution/MANDATE.md",
        ],
        "icon_key": "target",
        "default_pinned": False,
        "route": "/mandate",  # _route_status: NEW in Phase 2
        "summary": "Operator's standing intent — the Primary Action this workspace is built around.",
    },
    {
        "slug": "principles",
        "launcher_tier": "search-only",  # ADR-340 P3
        "register": "intent",  # ADR-312 D5 — constitution band (was `settings`)
        "title": "Principles",
        "archetype": "document",
        "substrate_paths": [
            "/workspace/persona/principles.md",
            "/workspace/persona/_principles.yaml",
        ],
        "icon_key": "scale",
        "default_pinned": False,
        "route": "/principles",  # _route_status: NEW in Phase 2
        "summary": "Reviewer's judgment framework and decision thresholds.",
    },
    {
        "slug": "identity",
        "launcher_tier": "search-only",  # ADR-340 P3
        "register": "intent",  # ADR-312 D5 — constitution band (was `settings`)
        "title": "Identity",
        "archetype": "document",
        "substrate_paths": [
            "/workspace/persona/IDENTITY.md",
        ],
        "icon_key": "user-circle",
        "default_pinned": False,
        "route": "/identity",  # _route_status: NEW in Phase 2
        "summary": "Operator persona — voice, role, context the workspace reasons against.",
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
        "launcher_tier": "utilities",  # ADR-340 P3
        "register": "application",  # ADR-309 two-register model
        "title": "Agents",
        "archetype": "roster",
        "substrate_paths": [],  # agents DB table + per-agent substrate
        "icon_key": "users",
        "default_pinned": False,
        "route": "/agents",  # _route_status: EXISTING — Reviewer detail + roster live here
        "summary": "Agent roster — Reviewer, specialists, platform integrations.",
    },
    {
        # ADR-331 D1 (2026-06-10): the guided first-boot SEQUENCE rendering
        # over the same workspace-state composition the /program drawer
        # presents random-access. macOS Setup Assistant ⇄ System Settings:
        # one substrate, two presentation registers. NO stored wizard state
        # — every step's status is derived from substrate at render time
        # (substrate_status authored? platform_connections active? harvest
        # invocation in narrative?). `substrate_paths == []` is load-bearing:
        # the surface owns no file; it reads api.workspace.getState(). The
        # first-run redirect (auth/callback), the Home empty-state CTA, and
        # the summon-index all point here. Re-enterable any time (the
        # Migration-Assistant property).
        "slug": "setup",
        "launcher_tier": "utilities",  # ADR-340 P3
        "register": "os-config",  # ADR-309/312 — it configures the OS, not an open file
        "title": "Setup",
        "archetype": "sequence",  # ADR-331 D1 — new archetype
        "substrate_paths": [],  # reads api.workspace.getState() composition; owns no file
        "icon_key": "rocket",
        "default_pinned": False,  # summon-only after first run
        "route": "/setup",  # _route_status: NEW in ADR-331 Phase 1
        "summary": "Guided first-boot sequence — activate, author, connect, bring in reality.",
    },
    {
        "slug": "program",
        "launcher_tier": "search-only",  # ADR-340 P3
        "register": "os-config",  # ADR-312 D5 (was `settings`)
        "pane_of": "settings",  # ADR-340 P2 — Program pane in System Settings
        "pane_group": "Program",
        "title": "Program",
        "archetype": "document",
        "substrate_paths": [
            "/workspace/_program.yaml",
        ],
        "icon_key": "package",
        "default_pinned": False,
        "route": "/program",  # _route_status: NEW in Phase 2 — replaces ProgramLifecycleDrawer
        "summary": "Active program bundle, phase, and capability gaps.",
    },
    {
        "slug": "queue",
        "launcher_tier": "primary",  # ADR-340 P3
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
        "slug": "activity",
        "launcher_tier": "utilities",  # ADR-340 P3
        "register": "application",  # ADR-309 two-register model
        "title": "Activity",
        "archetype": "stream",
        "substrate_paths": [],  # execution_events DB table
        "icon_key": "activity",
        "default_pinned": False,
        "route": "/activity",  # _route_status: NEW in Phase 2 — current /activity is deleted per ADR-163; reinstated as surface-mode
        "summary": "Execution-event log — every wake, every dispatch, every cost.",
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
        "slug": "settings",
        "launcher_tier": "system",  # ADR-340 P3
        "register": "os-config",  # ADR-312 D5 (was `settings`)
        "title": "System Settings",
        "archetype": "dashboard",
        "substrate_paths": [],  # account/workspace/billing config — DB + Stripe
        "icon_key": "settings",
        "default_pinned": False,
        "route": "/settings",
        # ADR-340 P2: THE os-config window — the one door. Sidebar panes:
        # General (Billing / Usage / Account, the legacy tabs) + the five
        # pane-grade surfaces above (Connectors, Sources, Autonomy, Budget,
        # Program), grouped per ADR-340 D4. `?pane=` is the intra-surface
        # deep-link param (`?tab=` accepted as legacy alias).
        "summary": "System Settings — the one os-config door. Governance dials, transports, program lifecycle, billing, account. Sidebar panes; ?pane= deep-links.",
    },
    {
        "slug": "connectors",
        "launcher_tier": "search-only",  # ADR-340 P3
        "register": "os-config",  # ADR-312 D5 (was `settings`)
        "pane_of": "settings",  # ADR-340 P2 — Perception & transports pane
        "pane_group": "Perception & transports",
        "title": "Connectors",
        "archetype": "dashboard",
        "substrate_paths": [],  # platform_connections DB table
        "icon_key": "link-2",
        "default_pinned": False,
        "route": "/connectors",
        "summary": "OAuth + API-key platform integrations (Slack, Notion, GitHub, Alpaca, Lemon Squeezy, etc.). Live connection state + per-platform substrate.",
    },
    {
        # ADR-338 D4.1 (2026-06-11): the standing-watch "drivers" view. Sibling
        # of Connectors in the os-config register — both bind transports the
        # operation perceives through. Connectors binds head platforms (OAuth);
        # Sources binds the generic web/RSS standing watch (ADR-336). Reads the
        # active bundle's declared watch sources (_sources.yaml) paired with
        # observed per-source health (_watch_signal.yaml). Kernel-agnostic: the
        # declaration path comes from the bundle's substrate_abi.watches, not a
        # kernel constant (ADR-224 boundary). substrate_paths is [] — the surface
        # reads GET /api/sources, which resolves the per-bundle paths server-side.
        "slug": "sources",
        "launcher_tier": "search-only",  # ADR-340 P3
        "register": "os-config",  # ADR-312 D5 — a transport/driver binding
        "pane_of": "settings",  # ADR-340 P2 — Perception & transports pane
        "pane_group": "Perception & transports",
        "title": "Sources",
        "archetype": "dashboard",
        "substrate_paths": [],  # per-bundle _sources.yaml + _watch_signal.yaml, resolved via GET /api/sources
        "icon_key": "rss",
        "default_pinned": False,
        "route": "/sources",  # _route_status: NEW in ADR-338 D4.1
        "summary": "Standing-watch sources — the web/RSS feeds the operation reads on cadence, with observed per-source health. A portfolio of attention, not a crawler.",
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


def kernel_surface_entries() -> list[dict[str, Any]]:
    """Return the kernel surface list with `tier: "kernel"` added.

    This is the shape the compositor emits into `surfaces[]`. Always
    returns a deep copy so callers can mutate freely without affecting
    the canonical declaration.
    """
    from copy import deepcopy

    return [
        {**deepcopy(entry), "tier": "kernel"}
        for entry in KERNEL_SURFACES
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
    "kernel_surface_entries",
    "kernel_surface_slugs",
    "kernel_pane_slugs",
]
