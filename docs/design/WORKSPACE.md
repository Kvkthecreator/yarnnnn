---
title: Workspace (Design)
counterpart: docs/architecture/WORKSPACE.md
scope: design — operator-facing surface contracts, CRUD shapes, affordances
status: Canonical
version: v3.0 (2026-06-10 — ADR-297 + ADR-312 surface-model rewrite: four-tab nav → windowed Desktop + Home-as-composition)
last_updated: 2026-06-10
---

# Workspace — Design

**Counterpart (architecture):** [docs/architecture/WORKSPACE.md](../architecture/WORKSPACE.md) — substrate, files, layers, bootstrap, autonomy threshold
**Governed by:** [ADR-215](../adr/ADR-215-surface-contracts-and-crud-principles.md) — Surface Contracts and CRUD Principles

> **ADR-320 path-consistency pass (2026-06-10).** Every *live* substrate-path reference in the tab contracts below was migrated to the [ADR-320](../adr/ADR-320-constitution-region-topological-cut.md) five-root topology: `_shared/` → `constitution/` + `governance/` + `operation/`; `review/` → `persona/`; `memory/` → `system/`; `context/{domain}/` → `operation/{domain}/`; `specs/` → `operation/specs/`; recurrence outputs → `operation/reports/{slug}/`; ACTION → `operation/operations/{slug}/`. Canonical homes: [`api/services/conventions.py`](../../api/services/conventions.py) + [`api/services/workspace_paths.py`](../../api/services/workspace_paths.py). The `/context` route is now `/files` throughout (legacy `/context` is a redirect stub). **Dated changelog entries (Phase 2/3/9 below) are NOT rewritten** — they are a historical audit trail accurate as of their commit dates.
>
> **Known deferred framing drift (separate from this path pass):** the Work tab's cockpit section still describes ADR-228's "four faces" framing, superseded at the *framing* level by [ADR-312](../adr/ADR-312-home-as-composition.md) (Home as composition — kernel constituent slots, route `/home`); and the MAINTENANCE-recurrence + `back-office.yaml` model was dissolved into `_recurrences.yaml` by ADR-261/262. Those are architectural reframes, not path fixes — tracked as a follow-up, not silently rewritten here.
**Grounded in:** [ADR-198](../adr/ADR-198-surface-archetypes.md) surface archetypes · [ADR-214](../adr/ADR-214-agents-page-consolidation.md) four-tab nav (Chat | Work | Agents | Files) · [ADR-209](../adr/ADR-209-authored-substrate.md) authored substrate · [ADR-219](../adr/ADR-219-invocation-narrative-implementation.md) invocation + narrative · [ADR-231](../adr/ADR-231-task-abstraction-sunset.md) task abstraction sunset · [ADR-235](../adr/ADR-235-update-context-dissolution.md) UpdateContext dissolution (lifecycle → `ManageRecurrence`; substrate writes → `WriteFile(scope='workspace')`; identity/brand merges → `InferContext` / `InferWorkspace`) · [ADR-168](../architecture/primitives-matrix.md) primitive matrix · [ADR-225](../adr/ADR-225-compositor-layer.md) compositor (Phase 3 — unified seam) · [ADR-245](../adr/ADR-245-frontend-kernel-three-layer-content-rendering.md) three-layer content rendering model (orthogonal: per-tab CRUD matrix here governs the **operational shape** of each tab; ADR-245 governs the **render layers** — L1 raw view + L2 content-shape parsers + L3 structured affordances — that L3 components on these tabs sit in) · [FOUNDATIONS v6.8](../architecture/FOUNDATIONS.md) Axiom 6 (Channel) + Axiom 9 (Invocation + Narrative)
**Supersedes:** `SURFACE-CONTRACTS.md` (renamed 2026-05-12) · `archive/SURFACE-ARCHITECTURE.md` · `archive/SURFACE-ACTION-MAPPING.md` · `archive/SURFACE-DISPLAY-MAP.md` · `archive/SURFACE-PRIMITIVES-MAP.md`

---

## Purpose

This is the single design reference for YARNNN's cockpit. It answers five questions, in order:

0. **How does the shell + kernel/program seam work?** (window-manager + composition layer)
1. **What surfaces exist, and what does each do?** (surface inventory + per-surface contracts)
2. **How is mutation expressed?** (CRUD matrix + 6 rules)
3. **What affordances live where?** (affordance cookbook)
4. **In what order do we harden the surfaces?** (sequencing)

When a design decision spans two surfaces (e.g. "deep-link from Recurrence to Files"), both surfaces' contracts must allow it. When a CRUD decision arises (e.g. "how do we let the operator refine a recurrence's deliverable?"), the matrix picks the shape. When the answer would require branching FE code on `program_slug`, the contract is wrong — programs specialize via composition manifest (Part 0), never via FE conditionals.

> **ADR-297 + ADR-312 surface-model rewrite (2026-06-10).** This doc previously described a **four-tab nav** (Chat | Work | Agents | Files via `ToggleBar`). That model was superseded by [ADR-297](../adr/ADR-297-surfaces-as-substrate-mirror.md) (the cockpit is a **windowed Desktop**, surfaces are windows not tabs; `ToggleBar` deleted) and [ADR-312](../adr/ADR-312-home-as-composition.md) (the cockpit composition is **Home**, a six-slot composition at `/home`). Parts 0 + 1 below are rewritten to the surface model; the CRUD matrix (Part 2), affordance cookbook (Part 3), and hardening sequence (Part 4) are unchanged by the surface-model shift (CRUD is substrate's layer per ADR-235/231; surfaces are viewport policy). Verified against `api/services/kernel_surfaces.py` + `web/components/shell/SurfaceRegistry.tsx`.

> **Findings surfaced during this rewrite (out of scope — tracked, not fixed here).** Both are Hat-A backend/comment drift the doc-verification turned up; neither is a design-doc change:
> 1. **`kernel_surfaces.py` registry drift.** The backend registry still names the budget surface `pace` (route `/pace`); ADR-327 (Implemented 2026-06-08) renamed it `budget` (`/budget`) and the frontend `SurfaceRegistry.tsx` already has `budget` (with `/pace` a redirect stub). The backend constant is stale — the operator-facing truth (`budget`) is what this doc documents. *Fix: update `KERNEL_SURFACES` entry slug `pace`→`budget` + route → `/budget`.*
> 2. **`web/lib/routes.ts` nav comment drift.** The header comment (line ~15) still reads "Current nav: Feed | Work | Agents | Files" — the pre-ADR-297 four-tab framing. *Fix: update the comment to the windowed-surface model.*

---

## Part 0 — The Shell: Window Manager + Composition Layer

### The surface model (ADR-297)

The authenticated cockpit is a **window manager** (macOS-literal), not a tab bar. The model:

- **A surface is a mountable React component bound to substrate**, addressed by surface state (`slug` + params), rendered into the shell's viewport (ADR-297 D11). URLs are *optional addressing transport* (deep-links), not identity.
- **`HOME_ROUTE = /desktop`** (ADR-297 D17) — login boots to the **Desktop** layer (the shell), not to a surface. Last-session windows restore from the operator-authored open-surfaces registry (D13); an empty registry → empty Desktop with context-aware welcome copy.
- **Multi-mount lifecycle** (D13): opened surfaces stay mounted in the React tree; exactly one is foregrounded (visible), others hidden. Closing is explicit. No LRU eviction — the open set is operator-authored.
- **Window chrome** (D14): every open surface renders inside a `WindowFrame` (32px title bar + close ×). The "pinned" concept dissolved into **Kept** (macOS "Keep in Dock" semantic); the dock shows the union of kept + open surfaces.
- **Navigation primitive** (D19.5): **`navigateToSurface(slug, params)`** is the *single* sanctioned cross-surface verb — it wraps `foregroundSurface(slug)` + URL param-sync. `router.push` is demoted to transport; the window manager owns navigation.

**Shell components** (`web/components/shell/`): `ShellCompositor` (top-level layout — TopBar region + SurfaceViewport + main-rail) · `SurfaceViewport` (mounts + z-stacks open windows) · `SurfaceRegistry` (`KERNEL_SURFACE_REGISTRY` slug→component map) · `Launcher`/`LauncherSurface` (the summon overlay that replaced the nav bar) · `AuthenticatedLayout` (auth + provider stack + pathname→foreground tracking). The backend surface registry is `api/services/kernel_surfaces.py::KERNEL_SURFACES` — the authoritative slug/register/route/archetype/substrate inventory.

### The composition seam (ADR-225 → ADR-312)

Each surface's contract below describes the **kernel surface**. Bundles (program manifests at `docs/programs/{slug}/SURFACES.yaml`) extend kernel surfaces declaratively via the compositor seam ([ADR-225](../adr/ADR-225-compositor-layer.md), Phase 3 Implemented).

**The single mental model:** every compositor-resolved slot has the same shape — bundle declaration → kernel default fallback → library component dispatch by `kind`. There is no "kernel render path" and "bundle render path"; there is one path, where kernel defaults are themselves library components registered alongside bundle components.

Post-ADR-312, the primary composition surface is **Home** (`/home`), whose six kernel slots are the cockpit (see [§ Home](#surface-home--the-cockpit-composition)). A program shapes Home by declaring **exactly two** of the six slots — the ground-truth hero (#2) and live entities (#4) — via `home.program_sections[]` in SURFACES.yaml. The other four slots are kernel-owned. The pre-ADR-312 `tabs.work.list.cockpit.{mandate,money_truth,performance,tracking}` four-faces binding is **deleted** (the four faces — `MandateFace`/`MoneyTruthFace`/`PerformanceFace`/`TrackingFace` — no longer exist).

The architecture-level reference for the seam is [docs/architecture/compositor.md](../architecture/compositor.md). This contract names which slots are bundle-shapeable; the architecture doc names how they get rendered.

### Refuses (composition-layer-wide)

- **No FE branch on `program_slug`.** Specialization happens via composition manifest, never via FE conditionals. If a surface feels it needs to know which program is active, the answer is to declare the variation in SURFACES.yaml.
- **No bundle-supplied executable logic.** SURFACES.yaml carries declarations only. The resolver inspects strings; it never `eval`s anything.
- **No kernel-only dual paths.** Per Singular Implementation, kernel defaults are library components dispatched through the same registry as bundle components.
- **Programs may not re-render kernel-owned Home slots** (constitution band, decision queue, recent artifacts, judgment trail). A program declares the hero + entities; the kernel owns the rest (ADR-312 D2).

### Contract authority

When this doc and `docs/architecture/compositor.md` disagree, the architecture doc wins on *how the seam works*. This doc wins on *what each surface should look like* (per-surface contracts, archetype assignments, refuses lists). When [ADR-297](../adr/ADR-297-surfaces-as-substrate-mirror.md) / [ADR-312](../adr/ADR-312-home-as-composition.md) / [ADR-225](../adr/ADR-225-compositor-layer.md) and either doc disagree, the ADR wins on decisions; the docs adjust.

---

## Part 1 — Surface Inventory + Per-Surface Contracts

The cockpit is **15 content surfaces + 3 chrome surfaces** (`api/services/kernel_surfaces.py::KERNEL_SURFACES`), in three **registers** (ADR-312 D5):

- **intent** — the constitution: operator-authored intent. `mandate` · `principles` · `identity`. Surfaced first-class as Home's constitution band, NOT a config drawer.
- **os-config** — the OS configuring itself. `autonomy` · `budget` · `connectors` · `program` · `settings`.
- **application** — open files + live state. `feed` · `home` · `recurrence` · `files` · `agents` · `queue` · `activity`.

Plus **chrome** (no register, route `""`, not Launcher-navigable): `top-bar` · `launcher` · `chat-drawer`.

### Surface inventory

| Surface | Route | Register | Archetype | Reads (substrate) |
|---|---|---|---|---|
| **Home** | `/home` | application | Dashboard (composition) | MANDATE + `_autonomy.yaml` + `action_proposals` + program sections + reports + `judgment_log.md` |
| **Feed** | `/feed` | application | Stream | `session_messages` (multi-actor invocation narrative) |
| **Recurrence** | `/recurrence` | application | Dashboard / Document (detail) | `tasks` index + `_recurrences.yaml` + per-shape natural-home substrate |
| **Files** | `/files` | application | Browser | `workspace_files` + `workspace_file_versions` (ADR-209) |
| **Agents** | `/agents` | application | Roster / Dashboard | `agents` table + per-agent substrate (`agents/{slug}/`, Reviewer `persona/`) |
| **Queue** | `/queue` | application | Queue | `action_proposals` (gated actions awaiting operator decision) |
| **Activity** | `/activity` | application | Stream | `execution_events` (workspace-wide execution ledger) |
| **Mandate** | `/mandate` | intent | Document | `constitution/MANDATE.md` |
| **Principles** | `/principles` | intent | Document | `persona/principles.md` + `persona/_principles.yaml` |
| **Identity** | `/identity` | intent | Document | `persona/IDENTITY.md` (co-renders `operation/BRAND.md` per ADR-309) |
| **Autonomy** | `/autonomy` | os-config | Document | `governance/_autonomy.yaml` |
| **Budget** | `/budget` | os-config | Document | `governance/_budget.yaml` (ADR-327 — collapsed pace + token-budget) |
| **Program** | `/program` | os-config | Document | active program bundle state |
| **Connectors** | `/connectors` | os-config | Dashboard | `platform_connections` (Slack · Notion · GitHub · Lemon Squeezy · Alpaca) |
| **Settings** | `/settings` | os-config | Dashboard | account / workspace / billing config |
| *(chrome)* `top-bar` | `""` | — | chrome | brand · launcher trigger · kept surfaces · user menu |
| *(chrome)* `launcher` | `""` | — | navigator | `composition.surfaces[]` (summon-to-filter index) |
| *(chrome)* `chat-drawer` | `""` | — | input | `session_messages` (the always-available chat summon) |

> **Backend/frontend registry drift (finding, out of this lane — 2026-06-10):** `api/services/kernel_surfaces.py` still names the budget surface `pace` (route `/pace`); ADR-327 (Implemented 2026-06-08) renamed it `budget` (route `/budget`) on the frontend (`SurfaceRegistry.tsx` has `budget`; `/pace` is a redirect stub). The operator-facing truth is `budget`, documented above. The stale backend registry constant is a tracked Hat-A fix, not part of this doc pass.

Per-surface contracts below carry the seven fixed sections where they apply: **Archetype · Reads · List/empty mode · Detail mode · `+` menu / writes · Deep-links out · Refuses.** Surfaces are grouped by register. (Document-archetype intent/os-config surfaces are thin — a rendered file + edit-via-chat — so their contracts are brief.)

### Surface: Files

**Route:** `/files` · **Register:** application · **Archetype:** Browser. (slug `files`, operator label "Files" per ADR-180; legacy `/context` is a redirect stub per `web/lib/routes.ts`, 2026-06-01)

- **Archetype:** Dashboard (primary, per ADR-198 §3) — live substrate slice, read-primary. Detail view of a file is a Document archetype when the file is a composed output.
- **Reads:** `workspace_files` (entire filesystem), `workspace_file_versions` (revision chain per ADR-209), `workspace_blobs` indirectly via revision reads.
- **List mode** (no `?path=`): filesystem tree grouped by the **ADR-320 five-root topology** (2026-06-10 correction — the prior grouping read stale `_shared/` · `context/` · `review/` · `memory/` roots that ADR-320 dissolved, so the Persona + System regions silently rendered empty). Groups, ordered Intent-first:
  - **Identity** — operator-authored rules via `nav.settings`: `persona/IDENTITY.md`, `operation/BRAND.md`, `system/{awareness,notes,style}.md` (ADR-320 constants in the nav route). MANDATE/AUTONOMY live in `constitution/` + `governance/`.
  - **Context** — accumulated domain knowledge, **disk-derived** from `operation/{domain}/` (any `operation/` folder that isn't `reports/` or `specs/`). NOT registry-derived — program domains (`portfolio`, `trading`) are created by work demand and aren't in the kernel registry; the registry only enriches display names. Each domain holds `_money_truth.md` (ADR-195), `_tracker.md`, `_recurring.yaml` (ADR-231 D3), `_feedback.md` (ADR-181).
  - **Reports** — DELIVERABLE-shape recurrences at `operation/reports/{slug}/` per ADR-231 D2 (`_spec.yaml` · `_run_log.md` · `_feedback.md` · `{date}/output.md`). Built from the recurrences index (those with `last_run_at`, minus `back-office-`).
  - **Persona** — the Reviewer seat (`persona/`): `IDENTITY.md` · `principles.md` · `judgment_log.md` · `calibration.md` · `standing_intent.md` · `handoffs.md` · `OCCUPANT.md`. **Was the dead `/workspace/review` fetch.**
  - **System** — YARNNN working memory (`system/`): `awareness.md` · `notes.md` · `style.md` · `conversation.md` + machine state. **Was the dead `/workspace/memory` fetch.**
  - **Agents** — per-domain-agent substrate (`agents/{slug}/`: AGENT.md, memory, style).
  - **Uploads** — operator-contributed documents (`uploads/`).
  - **System files are visible, not hidden** (ADR-320 correction): `_`-prefixed machine-config files (`_principles.yaml`, `_autonomy.yaml`, `_account.yaml`, `_tracker.md`…) render **de-emphasized** with a `sys` tag rather than vanishing — the prior hide-rule made the tree unable to "follow" a deep-link or Get-Info into the very files Home/cockpit link to. Only `operation/signals` (high-churn temporal log) stays hidden. Empty groups (Persona/System/Reports/Agents/Uploads) omit-if-empty.
- **Detail mode** (`?path=/workspace/...`):
  - Rendered file content (markdown, HTML, or binary via `content_url`)
  - Inference-meta caption (ADR-162 sub-phase D) when present
  - Head-revision author glance ("Last edited by …") on the file header (ADR-329 D1)
  - **Node Details ("Get Info")** — per-node provenance property (ADR-329 Amendment 1), opened via header ⓘ toggle or tree right-click. File → revision chain (`authored_by` trail, diff, restore per ADR-209 P4); folder → subtree recent-changes. Replaced the deleted standing "Recently authored" left-rail feed.
  - Substrate-native edit affordance when `authored_by=operator` is appropriate (IDENTITY, BRAND, CONVENTIONS, principles, MANDATE, uploaded documents)
- **`+` menu:** UploadFileModal (operator uploads a document into `/workspace/uploads/`). No other modals. No chat seeders.
- **Deep-links out:** every file path is a stable URL (`/files?path=...`) linked from Recurrence detail (`/workspace/operation/reports/{slug}/_spec.yaml` · `_feedback.md` · `{date}/output.md` per ADR-231 D2 + ADR-320), Agents detail (`/workspace/agents/{slug}/AGENT.md` · `memory/` · `style.md`), Feed artifacts, and Home's recent-artifacts slot.
- **Refuses:**
  - Recurrence orchestration, agent authoring, proposal approval — those are Work/Agents/Work respectively
  - "Edit in chat" buttons on substrate files (per R3) — Files is where substrate gets edited; Chat would invoke `WriteFile(scope='workspace', ...)` / `InferContext` and produce the same write with less clear provenance
  - Duplicate rendering of recurrence outputs (outputs exist in one canonical place at the natural-home `/workspace/operation/reports/{slug}/{date}/` per ADR-320; Files links rather than embeds per ADR-198 I2)

### Surface: Agents

**Route:** `/agents` · **Register:** application · **Archetype:** Roster / Dashboard. (canonical per ADR-214, reverses ADR-201)

- **Archetype:** List (list mode — roster) + Dashboard (detail mode, per ADR-167 v2 + ADR-251). Reviewer decisions stream is a Stream archetype accessible via Files deep-link.
- **Reads:** `agents` table filtered to principals (`thinking_partner` System Agent + user-authored domain agents, per ADR-189 origin filter + ADR-214 synthesized Reviewer pseudo-agent), plus each agent's filesystem home (`/workspace/agents/{slug}/*` for domain agents, `/workspace/persona/*` for Reviewer, `/workspace/system/*` for System Agent — ADR-320 five-root topology).
- **List mode** (no query param) — **Reinstated by ADR-251 D2**. Roster shows two systemic cards (System Agent + Reviewer) + "Your Agents" section (user-authored domain agents). Clicking a card navigates to `?agent=system` or `?agent=reviewer`. Bookmark-safety: `?agent=yarnnn` and `?agent=thinking-partner` redirect to `?agent=system`.
- **Detail mode** (`?agent={slug}`): dispatches on `agent_class`:
  - `meta-cognitive` (System Agent, `?agent=system`) → **SystemDetail**: Identity card + Mandate pointer (links to `/workspace`) + Reviewer cross-link. Tabs: Identity · Mandate · Back Office. **Autonomy and Principles removed from this surface — migrated to Reviewer (ADR-251 D3).**
  - `reviewer` (`?agent=reviewer`) → **ReviewerDetail** directly — **no redirect (ADR-251 D4, reverses ADR-241 D3)**. **Five tabs (expanded 2026-05-14)**: Identity (`IDENTITY.md`) · Principles (`principles.md`) · Capabilities (`/workspace/operation/specs/*.md` library) · Autonomy (delegation config only) · Activity (Reviewer supervision surface). Tab ordering reads top-to-bottom as operator orientation: who → frame → what-it-can-produce → how-much-delegation → what-it-did. The Capabilities tab renders `ReviewerCapabilitiesPanel` (one card per spec file under `/workspace/operation/specs/`, server-side correlation of `used_by` recurrences from `_recurrences.yaml` prompt text). The Autonomy tab renders just `AutonomyCard` (manual / bounded / autonomous selector — Direct-mutation write to `_autonomy.yaml`, gated by confirm modal per 2026-05-24 design polish; renamed from `DelegationCard`). The Activity tab renders `ReviewerActivityPanel` standalone. Track Record + Decisions link-outs deleted in earlier passes — calibration headline already on cockpit PerformanceFace; raw files via `/files`.
  - domain agents → IDENTITY card + health card + AGENT.md + memory/style substrate panes (unchanged).
- **Reviewer capability library panel** (added 2026-05-14) — `ReviewerCapabilitiesPanel` (`web/components/agents/ReviewerCapabilitiesPanel.tsx`) surfaced in Reviewer's Capabilities tab. Live-aggregate content class (ADR-245 D5): reads `/workspace/operation/specs/*.md` via `GET /api/agents/reviewer/capabilities`, parses each file for title (H1) + description (intro prose, ≤280 chars) + sections (## headings), correlates `used_by` against `_recurrences.yaml` prompt text (server-side — recurrences whose prompt body references `/workspace/operation/specs/{slug}.md`). Operator-facing analog of Claude Code's `skills.md`: a first-class inventory of "what kinds of outputs can my Reviewer produce, and what does each one promise?" Pre-2026-05-14 the capability library was entirely backend-internal — the Reviewer read specs by explicit path reference, but the operator could only see them by manually browsing `/files?path=/workspace/operation/specs/` as raw markdown. Per-card affordances: View source deep-link (→ `/files?path={path}`), Used-by recurrence chips (→ `/recurrence?task={slug}`), Edit-in-chat affordance routing through `useNarrative.sendMessage`. Empty state for newly-activated workspaces with no specs forked yet. Read-only by design; mutations route through chat per ADR-235 D1 + ADR-245. Reviewer-specific by intent — capability libraries are Reviewer concepts; if a second persona-bearing agent ever needs one, generalise then per ADR-225 §library scoping.
- **Reviewer activity panel** (originally ADR-251 D5, rewritten 2026-05-14 against canonical post-ADR-261 substrate) — `ReviewerActivityPanel` (`web/components/agents/ReviewerActivityPanel.tsx`) surfaced in Reviewer's Activity tab + chat `WorkspaceContextOverlay` Review section. Live-aggregate content class (ADR-245 D5): joins three sources via `GET /api/agents/reviewer/activity` — (1) `/workspace/_recurrences.yaml` judgment-mode entries (per ADR-263 D1, judgment mode = Reviewer wake) → schedule list + slug allowlist; (2) `execution_events` matching any judgment-mode slug (last 7d, the liveness signal); (3) `action_proposals` auto-approved or Reviewer-sourced (the autonomous-action history). Four-section render: Health headline · Upcoming wakes · Recent autonomous actions · Recent runs. Each Recent-runs row deep-links to `/activity?slug={slug}` for forensic detail per the supervision-vs-execution lens distinction (cross-surface affordance — same pattern as Schedule/Activity below). Read-only; "Edit schedule via chat →" routes through `useNarrative.sendMessage`. Direct-imported (not `kind`-dispatched through the library registry). Reviewer-specific by intent — heartbeat triggers + delegation ceiling are Reviewer concepts; if a second agent ever needs an analogous panel, generalise then per ADR-225 §library scoping. **Lens distinction (sharpened 2026-05-14):** Activity tab answers *"is my Reviewer functioning autonomously the way I told it to?"* — Reviewer-only supervision-lens. `/activity` (user-menu) answers *"did any recurrence run, what did it cost?"* — workspace-wide execution-lens. Both surfaces useful; deep-links bridge them.
- **`+` menu:** none. Per ADR-235 D2, no feed-surface pathway to create user-authored Agents.
- **Deep-links out:** each agent's files on Files (`/files?path=/workspace/agents/{slug}/AGENT.md`), Reviewer substrate on Files (`/files?path=/workspace/persona/judgment_log.md` etc. — ADR-320), the agent's recurrences filtered on Recurrence (`/recurrence?agent={slug}`), Feed with the agent preselected (`/feed?agent={slug}`). The autonomy chip links to `/agents?agent=reviewer&tab=autonomy` (ADR-251 D6).
- **Refuses:**
  - Recurrence management (recurrences live on the Recurrence surface; Agents shows agent *identity*, not agent *work*)
  - Editing production roles or platform integrations as if they were agents (ADR-212 — those are Orchestration, not Agents)
  - Principles/IDENTITY modal editing (ADR-215 R3 — substrate edit goes to Files or via chat)

### Surface: Home — the cockpit composition

**Route:** `/home` · **Register:** application · **Archetype:** Dashboard (composition)

Home is the cockpit (ADR-312, supersedes the ADR-228 four-faces framing). It is a **composition over the workspace's present constituents** — substrate-forward when empty (a constitution CTA), operation-forward when a program runs. Rendered by `HomeRenderer` (`web/components/library/HomeRenderer.tsx`); the four legacy faces (`MandateFace`/`MoneyTruthFace`/`PerformanceFace`/`TrackingFace`) are **deleted**.

- **Six kernel constituent slots, fixed order** (ADR-312 D2). The kernel owns the slot set + order; absent constituents self-hide (no dead-end Home):
  1. **Constitution band** (`HomeHeader`, kernel) — mandate one-liner + Reviewer persona + autonomy posture. The operation's authored intent, first-class (not a config drawer). Reads `constitution/MANDATE.md` + `governance/_autonomy.yaml`. Its empty state IS the onboarding/activation CTA.
  2. **Ground-truth hero** (program-declared) — the operation's primary "is this working?" signal. Generic kernel shape (`GroundTruthHero`); the program binds a component via `home.program_sections[]`. Alpha-trader binds `TraderMoneyTruth` (ADR-312 D3).
  3. **Decision queue** (`KernelDecisionQueue`, kernel-universal) — consequential gated actions awaiting operator approval. Reads `action_proposals` (ADR-307).
  4. **Live entities** (program-declared) — the operation's currently-active entities. Program-labeled ("Positions" / "Partners" / "Pieces"); the kernel never hardcodes a program noun.
  5. **Recent artifacts** (`KernelRecentArtifacts`, kernel-universal) — delivered outputs. Reads `operation/reports/{slug}/{date}/output.md` (ADR-320). Thinned to a glance + "View in Files" pointer (ADR-329 D7).
  6. **Judgment trail** (`KernelJudgmentTrail`, kernel-universal) — recent Reviewer decisions + reconciled outcomes. Reads `persona/judgment_log.md` (ADR-320; was `review/decisions.md`).
- **Program binding:** a program declares **exactly two** slots (#2 hero + #4 entities) via `home.program_sections[]` in `docs/programs/{slug}/SURFACES.yaml`, dispatched by `kind` through the library. It may NOT re-render the four kernel-owned slots. (Note: alpha-trader's SURFACES.yaml currently declares a seven-section trader stack — a documented known exception pending reshape to the two-slot contract.)
- **Writes:** none direct — Home is read-composition. Mutations route through chat (`WriteFile` / `ManageRecurrence` / etc.) or the decision queue's approve/reject (which calls `ExecuteProposal`/`RejectProposal`).
- **Deep-links out:** decision-queue rows → `/queue`; recent-artifact rows → `/files?path=...`; judgment-trail → `/agents?agent=reviewer`; constitution band → `/mandate` · `/identity`.
- **Refuses:** recurrence orchestration (→ Recurrence), file management (→ Files), agent authoring (→ Agents). No program noun hardcoded in the kernel slots. No `'use client'` redirect stubs (ADR-308 — pure server transport).

### Surface: Recurrence — the work list

**Route:** `/recurrence` (slug `recurrence`; renamed from `/cadence` 2026-06-03; the legacy `/work` + `/schedule` + `/overview` all redirect here per ADR-297). `WORK_ROUTE = "/recurrence"`.

The recurrence list + per-recurrence detail. ADR-297 dissolved the old `/work` two-zone layout (cockpit + work zones) — **the cockpit moved entirely to Home**; Recurrence is now a single-mode list/detail surface, no cockpit zone.

- **Archetype:** Dashboard / Queue (list mode) → Document/Dashboard/Stream (detail mode, per output_kind).
- **Narrative semantics** (ADR-219 D4): Recurrence **is the narrative filtered by `metadata.task_slug`**. The list-row recent-activity headline reads from the narrative via `GET /api/narrative/by-task` (ADR-219 Commit 4); recurrences with no narrative entries render no headline. Detail's per-recurrence run-history reads `agent_runs` (ADR-219 D7 — the audit ledger, separate consumer).
- **Reads** (ADR-320 five-root + ADR-261/262 natural-home paths — canonical homes in `api/services/conventions.py`): `tasks` thin scheduling index (ADR-231 D4 Path B — `next_run_at`, `last_run_at`, `paused`, `declaration_path`), `/workspace/operation/reports/{slug}/*` (DELIVERABLE: `_spec.yaml`, `_feedback.md`, `_run_log.md`, `{date}/output.md`), `/workspace/operation/{domain}/*` (ACCUMULATION: `_feedback.md`, `_run_log.md`, synthesis `_<name>.md`, entity files), `/workspace/operation/operations/{slug}/*` (ACTION: `_action.yaml`, `_run_log.md`), `/workspace/_recurrences.yaml` (the single canonical recurrence declarations file per ADR-261 D2; the legacy `_shared/back-office.yaml` MAINTENANCE index dissolved into it), `agent_runs`, **`GET /api/narrative/by-task`**.
- **List mode** (no `?task=`): the recurrence list, cadence-grouped (Recurring · Reactive · One-time) via `RecurrenceList`. Search + agent filter. System recurrences hidden by default (overflow toggle "Show system"). **Pinned recurrences** (`tabs.work.list.pinned_tasks`) float to the top of their group. **Banner** (`tabs.work.list.banner`, incl. via `phase_overlays`) renders above via `<BundleBanner />`.
  - **Lens distinction:** Recurrence answers the declaration-lens question — *"What recurrences exist, when do they fire, who runs them?"* The execution-lens question — *"Did they run, succeed, what did they cost?"* — lives at `/activity`. Recurrence rows surface declaration signals (cadence, agents, next-run); they do NOT carry execution detail. Each row carries `View runs →` to `/activity?slug={slug}`; `/activity` carries reciprocal `Manage →` to `/recurrence?task={slug}`. Anti-pattern: narrative excerpts in a recurrence row — those are execution-lens content.
- **Detail mode** (`?task={slug}`): three compositor-resolved layers — chrome (top), middle (content), feedback strip (bottom). Per Part 0, every layer flows through the resolver pattern.
  - **Chrome** (`<ChromeRenderer>`) — single component for the metadata strip + array of components for the actions row. Resolved via `resolveChrome(ctx, middles)`:
    - **Kernel default per output_kind** (`KERNEL_DEFAULT_CHROME` in `kernel-defaults.ts`):
      - `produces_deliverable` → KernelDeliverableMetadata + KernelDeliverableActions
      - `accumulates_context` → KernelTrackingMetadata + KernelTrackingActions
      - `external_action` → KernelActionMetadata + KernelActionActions (Fire button + Edit-in-chat)
      - `system_maintenance` → KernelMaintenanceMetadata + (no actions)
    - **Bundle override** via `tabs.work.detail.middles[].chrome` (optional, partial overrides allowed): bundles override metadata only, actions only, or both. Missing slots inherit kernel default.
    - **Action handlers** thread via `WorkDetailActionsContext` provider in `WorkDetail.tsx`. Kernel and bundle chrome components both consume `useWorkDetailActions()`.
    - **Operational vs historical timestamp rule** (rule made contract-explicit in v2.0): chrome metadata strips show **operational** timestamps that help the operator answer "is this recurrence healthy and current?" Bundle middles whose content area regenerates substrate every run (e.g., a Dashboard reading `_money_truth.md`) should override the metadata to show *substrate* freshness, not artifact age. Historical context lives in the narrative (Recurrence list-row headlines, ADR-219), not in chrome.
  - **Middle** (`<MiddleResolver>`) — content area. Resolved via `resolveMiddle(ctx, middles)` 4-tier match:
    - **Kernel default per output_kind** (kind-specific components at `web/components/work/details/`, retained as the kernel-default fallback per ADR-225 §5):
      - `produces_deliverable` → DeliverableMiddle (rendered output + quality contract panel)
      - `accumulates_context` → TrackingEntityGrid (domain folder + entity cards)
      - `external_action` → ActionMiddle (fire history + platform link-out)
      - `system_maintenance` → MaintenanceMiddle (hygiene log + run history)
    - **Bundle override** via `tabs.work.detail.middles[]` 4-tier match (task_slug → output_kind+condition → output_kind → agent_role/class). First match wins. Bundle middles take full content area; archetype declared via `archetype` field per ADR-198.
  - **FeedbackStrip** — thin bar below the middle. Single "Edit in chat" prompt per kind (ADR-181 Phase 4a). Skipped for system_maintenance (back-office tasks have no user feedback loop).
- **`+` menu:** `TaskSetupModal` (singular creation modal — ADR-178 two-route rich intake; forwards to YARNNN via `sendMessage`. Per ADR-231 D5, YARNNN calls `ManageRecurrence(action='create', shape=..., slug=..., body={...})` in the same turn — `ManageTask` was deleted in ADR-231 Phase 3.7). Per ADR-215 Phase 4 singular-implementation, `CreateTaskModal` was retired — one creation modal across the cockpit (summoned from any surface).
- **Deep-links out:** recurrence files on Files (`/files?path=/workspace/operation/reports/{slug}/_spec.yaml` for DELIVERABLE; `/workspace/operation/{domain}/` for ACCUMULATION; `/workspace/operation/operations/{slug}/_action.yaml` for ACTION; per ADR-231 D2/D3 + ADR-320), assigned agents on Agents (`/agents?agent={slug}`), Feed with recurrence preselected for "Edit in chat" (`/feed?task={slug}` — query-param name preserved per ADR-219 D4 task_slug = declaration slug), execution log on Activity (`/activity?slug={slug}`).
- **Refuses:**
  - The cockpit composition (→ Home) — Recurrence is the work list, not the dashboard.
  - File browsing outside recurrence scope (→ Files)
  - Agent identity editing (→ Agents → Feed)
  - Replacing Files for the operator-authored rules (MANDATE in `constitution/`, IDENTITY/principles in `persona/`, BRAND/CONVENTIONS in `operation/` per ADR-320; per R3 — `ManageContextModal` retired)

### Surface: Feed

**Route:** `/feed` · **Register:** application · **Archetype:** Stream. (`/chat` redirects to `/feed` per ADR-259; the always-available chat-drawer chrome summons this surface.)

> **ADR-289 Phase 2 update (2026-05-18):** The Feed tab is now split into two render surfaces — the **FeedTimeline** (operations-timeline rendering of typed event rows, no chat bubbles) and a **ConversationDrawer** (chat-shaped exchange surface scoped to `pulse='addressed'`). Bubble grammar is preserved ONLY on the Conversation surface. The Feed surface groups rows by `metadata.invocation_id` (re-anchored to `execution_events.id` per ADR-289 D2) into InvocationCards. Operator engages a conversation via the header "Talk" button or by clicking an OperatorEventMarker's "opened conversation →" affordance — the drawer slides over the timeline. Autonomous wakes that fire while the drawer is open surface silently in the timeline behind; visible when the drawer closes.

- **Archetype:** Stream — **the narrative surface** per [ADR-219](../adr/ADR-219-invocation-narrative-implementation.md) (FOUNDATIONS Axiom 9). The universal log of every invocation in the workspace, of which the operator's own conversation is one thread. Reviewer verdicts (`role='reviewer'`), agent task completions (`role='agent'`), back-office digests (`role='system'`), and external MCP foreign-LLM calls (`role='external'`) all surface here as Identity-tagged entries with **invocation-grouped typed-event rendering** (ADR-289 D6 supersedes ADR-219 D5's bubble-everywhere policy). Cold-start empty-state is the one exception — renders a curated landing panel.
- **Narrative semantics** (ADR-219):
  - **Identity widening** — `session_messages.role` enum is `user | assistant | system | reviewer | agent | external` (migration 161). Every invocation in the workspace emits exactly one narrative entry into this stream.
  - **Weight-driven rendering** (ADR-219 D5) — `metadata.weight` ∈ `{material, routine, housekeeping}` drives per-row UI density. Material → full card (existing user/assistant/reviewer card path). Routine → collapsed line with chevron + click-to-expand. Housekeeping → dim one-liner; the curated rollup card written by `back-office-narrative-digest` (ADR-219 Commit 3) is the recommended surface for housekeeping clusters. Legacy "no envelope" rows default to material so messages predating ADR-219 Commit 2 don't disappear.
  - **Pulse** = trigger sub-shape attached to each entry. Periodic / reactive / addressed / heartbeat. Carried in `metadata.pulse`.
  - **Filter bar** (`<ChatFilterBar>`) — three deep-linkable query-param dimensions: `?weight=...&identity=...&task=...`. Bar auto-opens when any filter is active. The filter is a Channel-layer slice over the same Stream — never a substrate change.
  - **Recurrence is the same narrative filtered by `metadata.task_slug`** — Feed and Recurrence read the same source of truth (ADR-219 D4); Recurrence is the legibility wrapper for task-labeled invocations, Feed is everything.
- **Reads:** `chat_sessions` + `session_messages` (windowed per ADR-159), compact index (`format_compact_index()` per ADR-186 profile), all substrate indirectly via YARNNN's tool calls.
- **Writes:** through primitives (`WriteFile(scope='workspace')`, `InferContext`, `FireInvocation`, `ManageAgent` (lifecycle-only per ADR-235 D2), `ManageRecurrence`, `ManageDomains`, `ProposeAction`, etc. per ADR-168 + ADR-231 D5 + ADR-235; the `InferWorkspace` first-act primitive was removed per ADR-314 D4). Chat never writes substrate directly; it writes through YARNNN's primitive invocations. Recurrence lifecycle flows through `ManageRecurrence` (create/update/pause/resume/archive) + `FireInvocation` (manual fire) per ADR-231 D5 + ADR-235 D1.c — the legacy `ManageTask` primitive was deleted in Phase 3.7 and `UpdateContext` was deleted in ADR-235. Every primitive invocation also emits a narrative entry via `services.narrative.write_narrative_entry` (ADR-219 Commit 2 single write path; ADR-219 Commit 6 final coverage gate enforces this).
- **Stream mode** (default, conversation active): append-only message log. Reviewer verdicts appear as `role='reviewer'` messages per ADR-212; agent task completions appear as `role='agent'` entries with task-slug envelope. `system_card='narrative_digest'` system cards are retired (digest mechanism deleted by ADR-260/261/262 back-office cleanup; the housekeeping-roll-up surface that ADR-219 D5 originally targeted was replaced by emission-at-source policy per ADR-277). MCP foreign-LLM calls land as `role='external'` entries (ADR-219 Commit 6) with `metadata.mcp_tool` + `metadata.mcp_client` provenance. Artifact cards render inline when a primitive's response carries one. "Edit in chat" entries from other surfaces open the Feed with a seeded first message.

- **Feed emission policy** (ADR-277, 2026-05-15) — **The feed is the central conversational substrate that surfaces throughout the cockpit (Feed surface, context overlay deep-links, Reviewer activity Recent runs cross-link, Recurrence narrative entries). Its emission discipline governs operator experience everywhere it appears.** Two tiers of system-event emission, by intent at source:

  | Tier | When to emit | Render | Examples |
  |---|---|---|---|
  | **Material** | Operator must see this even if not actively reading the feed | Full bubble | Balance exhausted, capability transition (first-detection), Reviewer verdict, real failures, spend-ceiling reactive skip |
  | **Routine** | Context if the operator's already reading the feed | Slim collapsed line | Stand-down verdicts, warn-but-proceed events, mode transitions |
  | **(no emit)** | Already canonical in substrate; no operator-relevant judgment to add | — | Mechanical-mirror successes, idempotent no-ops, skipped paused-recurrence fires |

  **Rule of thumb (the canon for future emission decisions):** Each event has one canonical home. The feed is for events whose canonical home is conversation. If the same event is already captured in `execution_events` / `workspace_file_versions` / `action_proposals` / `agent_runs`, the feed only earns a parallel narrative emit when it carries operator-relevant judgment or context the substrate row doesn't carry. Density (material vs routine) is determined by whether the operator should see it when not actively reading the feed — not by frequency. High-frequency events typically emit nothing (their canonical home is the substrate), not "emit at routine density."

  **Cross-surface implications:** anything *not* in the feed has a canonical home the operator can navigate to:
  - Mechanical fire forensics (status / duration / cost) → `/activity` filtered to `mode=mechanical`
  - What each fire wrote to substrate → `/files` file detail + `workspace_file_versions` revision chain (ADR-209)
  - Reviewer-loop activity → `/agents?agent=reviewer&tab=activity`
  - Full upcoming-fires schedule → `/recurrence` (cadence-grouped list)

  This is the lens-sharpening discipline applied at the emission policy layer — same shape as the Schedule/Activity (declaration vs execution) and Reviewer Autonomy/Activity (config vs supervision) splits canonized elsewhere in this doc. **Future emission decisions reviewed against this rule of thumb.**
- **Empty state** (cold start per ADR-205 F1): `<ChatEmptyState>` — deterministic client-side landing with four suggestion chips (Upload a doc, Paste a URL, Track something recurring, Build a recurring report). Zero LLM cost on first load. The only surface in the cockpit that overrides its archetype for first-run guidance.
- **`+` menu:** exactly one entry per ADR-215 Phase 5 — "Start new work" → `TaskSetupModal` (R4 modal launcher). The prior "Update workspace" entry was retired — it violated R2 (update is never Modal) and R3 (identity/brand/conventions are substrate, edited on Files).
- **Deep-links out:** any file YARNNN cites (`/files?path=...`), any recurrence `ManageRecurrence` creates or updates (`/recurrence?task=...` — query-param name preserved per ADR-219 D4 task_slug = declaration slug), any agent `ManageAgent` touches (`/agents?agent=...`). Reviewer verdict cards (role='reviewer' messages per ADR-212) link to `/agents?agent=reviewer` (ADR-214 canonical route). Artifacts carry links, not embeds.
- **Context overlay** (`<WorkspaceContextOverlay>`): modal opened by YARNNN-emitted `<!-- snapshot: {"lead":"..."} -->` marker OR the surface header "Context" button. **Briefing archetype in its purest form** (ADR-198 §3): pure read, composed by selection, no outbound nav, zero LLM at open time. The overlay is *of* the conversation — Close returns the operator to typing with enriched awareness, not to another tab.

  **Three sections (refactored 2026-05-14 from 8 overlapping sub-blocks to a 3-section primer):** single operator question this modal answers is *"what do I need to know right now to make sense of the next chat turn?"* — a 5-second awareness primer, not a supervision or forensic surface. Anything richer routes to canonical dedicated surfaces via inline deep-links.

  | Section | Purpose (the operator's *why*) | What renders in place | Sources | Cost |
  |---|---|---|---|---|
  | **Mandate** | "What's the operation trying to do?" | MandateCard variant=compact — Primary Action sentence + autonomy posture chip | `GET /api/workspace/file?path=/workspace/constitution/MANDATE.md` (ADR-320) | 1 HTTP GET, 0 LLM |
  | **Rules** | "How does the system judge + how much autonomy?" | PrinciplesCard variant=compact + AutonomyCard variant=compact | `GET` principles.md + `GET` _autonomy.yaml | 2 HTTP GETs, 0 LLM |
  | **Pulse** | "Is it alive + what demands my attention now?" | One-line liveness ("Last wake N ago · M runs in window") + nearest next-wake hint + pending-proposals card (only when count > 0) + deep-links footer | `GET /api/agents/reviewer/activity` + `GET /api/proposals?status=pending` | 2 HTTP GETs, 0 LLM |

  **Lens distinction (sharpened 2026-05-14)** — modal answers ONE operator question (right-now awareness primer). Richer views live on dedicated surfaces:
    - Full upcoming-wakes schedule → `/recurrence` (declaration-lens, cadence-grouped)
    - Full execution history → `/activity` (execution-lens)
    - Reviewer-loop supervision (full activity + capabilities + autonomy config) → `/agents?agent=reviewer&tab=activity` (supervision-lens)

  The Pulse section renders a footer link-row pointing at all three so operators can drill into the richer view with one click.

  **SnapshotLead vocabulary (post-2026-05-14 rename):** `mandate | rules | pulse`. Legacy values `review` / `recent` from in-flight TP messages are accepted on read (mapped to `rules` / `pulse` respectively at parse time in `web/lib/content-shapes/snapshot.ts`) — Singular Implementation rule: read-side tolerance during transition, prompt-side emits new vocabulary only.

  **Out-of-scope on this surface** (intentionally dropped from the modal):
    - 10-row upcoming-wakes schedule (was overload for an "at-a-glance" surface)
    - 8-row recent-runs history (forensic detail belongs on `/activity`)
    - "Recent autonomous actions" empty-state noise when autonomy is Manual
    - awareness.md free-form notes — pre-2026-05-14 surface rendered stale skeleton headings ("Tasks / Context State / Next Steps") for active workspaces because nothing updates them. Post-ADR-261 between-session continuity is judgment_log.md + per-domain ground-truth substrate (alpha-trader instance: `_money_truth.md`) + domain `_run_log.md`; awareness.md as parallel substrate is vestigial. File stays in substrate (operator data preserved); no longer surfaced in modal.

  **Zero LLM cost at modal open**, by contract. No summarization, no reasoning, no cross-referencing commentary. Every byte rendered was persisted by an earlier conversational turn — the overlay reads what already exists.

  **Stay-in-chat invariant** (the defining discipline): every section renders its content in place. The Pulse footer deep-links are explicit operator choice (one click, one destination, no surprise navigation). Close button returns to typing.

  **Permitted affordances per section:**
  1. Close button — return to conversation.
  2. At most one Edit-in-chat affordance per concept card (R5 single label) seeding a section-contextual prompt ("Revise my mandate", "Evolve principles", "Walk me through pending proposals"). The seed closes the modal and drops the prompt into the composer. Operator still owns pressing Send.

  **Identity-empty states** degrade gracefully — a missing MANDATE.md renders "Not yet declared" with Edit-in-chat seed; same for principles.md. R3 preserved (substrate-file edits happen on Files; this overlay never *edits* substrate — only seeds the conversation that eventually writes via `WriteFile(scope='workspace')` or `InferContext`).
- **Reviewer verdict thread** (ADR-258, supersedes ADR-212 visual treatment): `role='reviewer'` session messages render as a uniform muted bubble — same shape as System Agent, differentiated by persona name label. Color differentiation is deleted; semantic state (approved/rejected/deferred) appears as a compact inline chip in text + icon only, never as bubble background tinting. No section dividers. The Reviewer is a chat participant, not a gate announcement. Stream archetype invariant: append-only; entries are historical, never mutated inline. Observation entries collapse to a dim Eye-icon one-liner (routine weight per ADR-277 — was "housekeeping" pre-ADR-277 retirement).
- **Interactive stream entries — chip → modal pattern** (ADR-258 D2): proposals and workspace file references use one pattern. Stream entry = compact chip (1–2 lines, append-only). Clicking opens `InteractiveModal` (centered modal, Escape to close) with full detail and action affordances. `InteractiveModal` is the single shared style for all interactive stream items — one component, no per-entry modal variants. Approve/reject executes in the modal and closes it; chip reflects terminal state. This supersedes the prior inline `ProposalCard` expand pattern and the inline `WorkspaceFileView` overlay in `MessageRow`.
- **Inline-to-recurrence graduation** (ADR-219 D6 + ADR-231 D1/D5): material-weight operator messages that have no `metadata.task_slug` (i.e. inline invocations per FOUNDATIONS Axiom 9 + ADR-231 D1 invocation-first default) carry an inline **"Make this recurring"** affordance. Per D1 the operator's first invocation already fired and produced its result; this affordance attaches a nameplate + pulse + contract for repeat firings. Click opens `TaskSetupModal` pre-filled with `Recurring intent: <message-prefix>` so YARNNN turns it into `ManageRecurrence(action='create', shape=..., slug=..., body={...})` on submit. Reversible: a recurrence can be archived later via `ManageRecurrence(action='archive', ...)` and the same intent returns to inline. The atom of action (the invocation) is the same throughout — only the legibility wrapper rotates.
- **Refuses:**
  - Full CRUD forms (modal-shape — those belong on their owning surfaces per R2)
  - Heavy data tables (those are Dashboard archetype — Home / Recurrence / Files)
  - Replacing direct affordances on other surfaces (approve/reject stays on Queue + Home's decision queue; pause/run-now stays on Recurrence; no chat-only paths for Direct-shape operations per R1)
  - Onboarding forms — onboarding is conversational per ADR-190; no `OnboardingModal` / `ContextSetup` after ADR-215 Phase 5

### Surface: Queue + Activity (application)

- **Queue** (`/queue`, application, **Queue** archetype) — consequential gated actions awaiting operator decision. Reads `action_proposals`. Approve/reject executes in place (`ExecuteProposal` / `RejectProposal`); the same decision-queue slot renders on Home (#3). **Refuses:** authoring (proposals come from agents/Reviewer, not the operator); execution detail (→ Activity).
- **Activity** (`/activity`, application, **Stream** archetype) — the workspace-wide execution ledger. Reads `execution_events` (ADR-250 + ADR-265). The execution-lens counterpart to Recurrence's declaration-lens (the Schedule/Activity split). Rows carry reciprocal `Manage →` deep-links to `/recurrence?task={slug}`. **Refuses:** declaration mutation (→ Recurrence); conversation (→ Feed).

### Surfaces: intent + os-config (thin contracts)

The constitution (**intent**) and OS-tuning (**os-config**) surfaces are thin **Document/Dashboard** surfaces — a rendered file or config view + edit-via-chat. They share one contract shape, so they're documented as a group rather than repeating seven sections each:

- **intent** (the constitution band, also surfaced as Home slot #1): **Mandate** (`/mandate` → `constitution/MANDATE.md`) · **Principles** (`/principles` → `persona/principles.md` + `_principles.yaml`) · **Identity** (`/identity` → `persona/IDENTITY.md`, co-renders `operation/BRAND.md` per ADR-309). Read-render + revision history (ADR-209). **Writes:** edit-via-chat only (`WriteFile`/`InferContext` per ADR-235/329 D5 — no inline editor). The operator authors these; the Reviewer may amend within its write-lock topology (ADR-320 D3).
- **os-config** (the OS configuring itself): **Autonomy** (`/autonomy` → `governance/_autonomy.yaml`, the delegation dial) · **Budget** (`/budget` → `governance/_budget.yaml`, the collapsed pace + token-budget gate per ADR-327) · **Program** (`/program`, bundle lifecycle — activate/switch/deactivate) · **Connectors** (`/connectors` → `platform_connections`, OAuth + API keys) · **Settings** (`/settings`, account/workspace/billing — `?tab=` sub-views). Autonomy + Budget are governance YAML (operator-only write per ADR-320 D3, structured edit via confirm-gated direct mutation); Connectors + Settings + Program are dashboard config surfaces.
- **Refuses (both registers):** substrate-authoring outside the file's owning primitive; cross-surface orchestration; `'use client'` redirect stubs (ADR-308 — pure server transport).

---

## Part 2 — The CRUD Matrix

Four shapes. One rule per verb-object pair. Every mutation in the cockpit picks exactly one shape.

| Shape | When | Surface | Example |
|---|---|---|---|
| **Direct** | High-precision, well-specified, one-step, reversible | In-place button/input on the object's own detail page | Pause task · Archive file · Approve proposal · Run task now |
| **Modal** | High-precision, multi-field, **creation flow**, operator arrives with a blueprint | Modal launched from `+` menu or page header | CreateTaskModal · UploadFileModal |
| **Chat** | Judgment-shaped, ambiguous, needs YARNNN's context | Seeded prompt into the Feed (`/feed`) | Refine a recurrence's deliverable · Rewrite a mandate · Author a domain agent · Define review principles |
| **Substrate** | Operator-authored content that IS a file | Open the file on Files (`/files`); edit-via-chat records `authored_by=operator` (ADR-329 D5 — no inline editor) | IDENTITY.md · BRAND.md · CONVENTIONS.md · MANDATE.md · principles.md · uploaded documents |

### The six rules

- **R1 — One verb, one shape per object.** "Edit a task" is always Chat. "Edit a file" is always Substrate. "Approve a proposal" is always Direct. No mixing across the cockpit.
- **R2 — Create is always Modal. Update/Delete is Direct or Chat, never Modal.** Modals exist for the moment of creation where the operator arrives with a blueprint. After creation, mutation is single-click Direct or judgment-shaped Chat. No "edit modal" anywhere in the cockpit.
- **R3 — Substrate operations bypass Chat.** If the thing being edited IS a file, the edit surface is Files. The revision panel (ADR-209 P4) shows `authored_by=operator`. No "Edit in chat" button on substrate files — Chat would invoke `WriteFile(scope='workspace')` or `InferContext` anyway, and direct substrate edit produces the same write with clearer provenance.
- **R4 — The `+` menu is a modal launcher. Never a chat seeder.** A surface's `+` menu lists only Modal creation flows. Chat-shaped mutations live on the object's own detail surface as the R5 label.
- **R5 — One label: "Edit in chat".** All existing phrasings ("Edit via chat" / "Edit via YARNNN" / "Edit via yarnnn") converge on **"Edit in chat"**. Lowercase. No YARNNN branding — chat is the Feed; YARNNN is the agent; the operator is editing *in a surface*, not *through an agent*. Single `<EditInChatButton prompt={...} />` component across the cockpit.
- **R6 — Surfaces never branch on `program_slug`.** Specialization happens via composition manifest (Part 0), never via FE conditionals. If a surface's contract feels it needs to know which program is active, the answer is to declare the variation in `SURFACES.yaml`. The compositor seam is the kernel/program boundary at the FE layer; bypassing it for "just one quick conditional" undoes the structural reason the seam exists. Per ADR-225 Phase 3 + ADR-222 Principle 16.

---

## Part 3 — Affordance Cookbook

Quick lookup for common verb-object pairs. When adding a new affordance, add it here in the same commit it lands in code.

| Verb | Object | Shape | Location | Notes |
|---|---|---|---|---|
| Create | Task | Modal | Any surface `+` menu → TaskSetupModal (singular per ADR-215 Phase 4) | R2 |
| Create | Domain agent | Chat | Agents header → "Edit in chat" | R1 (judgment-shaped) |
| Create | Proposal | Chat | Agent proposes via ProposeAction primitive | Not operator-initiated |
| Upload | Document | Modal | Files `+` menu → UploadFileModal | R2 |
| Edit | Task (DELIVERABLE, team, schedule by judgment) | Chat | Recurrence detail → "Edit in chat" | R1 |
| Edit | Task (mode, pause/resume, run now, archive) | Direct | Recurrence detail → header buttons | R1, R2 |
| Edit | Agent identity (IDENTITY.md, memory/style) | Chat or Substrate | Substrate if file; Chat if judgment-shaped | R1 per field |
| Edit | Operator-authored rules (MANDATE in `constitution/`; IDENTITY in `persona/`; BRAND · CONVENTIONS in `operation/` — ADR-320) | Chat | Files detail → "Edit in chat" (no inline editor; SubstrateEditor deleted per ADR-236/ADR-329 D5) | R3 / ADR-329 verb 5 |
| Edit | Reviewer `persona/principles.md` (ADR-320) | Chat | Files detail → "Edit in chat" | R3 / ADR-329 verb 5 |
| Edit | `feedback.md` on a task | Chat | Recurrence detail → FeedbackStrip → "Edit in chat" | R1 |
| Approve | Proposal | Direct | Queue (or Home decision-queue slot) → Approve button | R1 |
| Reject | Proposal | Direct | Queue (or Home decision-queue slot) → Reject button | R1 |
| Archive | Task | Direct | Recurrence detail → header overflow | R1 |
| Archive | File | Direct | Files detail → overflow | R1 (when lifecycle allows) |
| Restore | File revision | Direct | Files Get-Info → Restore (ADR-329) | R1 |
| Connect | Platform | Modal | Connectors (`/connectors`) → connect flow | R2 |
| Graduate | Inline action → Task | Chat | Feed → material operator entry → "Make this recurring" → opens TaskSetupModal pre-filled | R5 phrasing; ADR-219 D6 |
| Filter | Narrative stream | Direct | Feed header → Filter icon → ChatFilterBar (weight / identity / task chips) | ADR-219 D5; deep-link query params |

---

## Part 4 — Surface-Hardening Sequence

> The original four-tab framing (Files → Agents → Work → Chat) is preserved below as the dependency-graph reasoning that drove the ADR-215 hardening pass (the "Implementation status" changelog records its execution). It still reads correctly under the surface model with the rename `Work → Recurrence` + `Chat → Feed`; the cockpit composition (Home) hardens last alongside Feed, since it composes over every other surface's substrate.

Surfaces harden by dependency depth — each surface's design consumes substrate + deep-link targets from surfaces earlier in the sequence:

```
Files  ←── Agents ←── Recurrence ←── Feed / Home
(substrate)  (identity)  (action)       (conductor / composition)
zero inbound   1 inbound   2 inbound      N inbound
```

- **Files first** — zero inbound dependencies. Every other surface links into Files paths. File detail shape, revision panel, Get-Info provenance (ADR-329), upload UX must be stable before any deep-link target is promised.
- **Agents second** — Systemic vs Domain split (ADR-214) hardens before Recurrence references agents in `## Team` sections. Reviewer detail is the highest-complexity agent type; lock that shape.
- **Recurrence third** — Recurrence detail links to recurrence files (→ Files) and assigned agents (→ Agents).
- **Feed + Home last** — Feed mirrors affordances exposed on other surfaces; Home composes over all of them. Both converge to what's already stable. Locking them first forces reshapes every time another surface moves.

Each phase lands with: code changes + this doc's contract section updated in the same commit + `docs/design/CHANGELOG.md` entry. No phase ships without the contract change — that discipline is what prevents ADR-215's motivation from recurring.

### Implementation status

> **Supersession note (2026-04-30, ADR-236 Cluster A + ADR-241):** Phase 2's `<SubstrateEditor>` was deleted by ADR-236 Round 5 Cluster A — every file now routes to chat for edits via `<EditInChatButton>` per the original ADR-236 assessment ("not notion-like, streamline back to edit via Chat"). Phase 3's `PrinciplesPane` and `ReviewerDetailView` were deleted by ADR-241 — Reviewer surface collapsed into Thinking Partner (Principles became a TP tab; Decisions relocated to `/work`). The `editable_prefixes` allowlist on the backend stays — chat's WriteFile primitive uses it server-side. The Phase 2/3 entries below are preserved verbatim per ADR-236 Rule 2 (historical record); for current canonical state see the §"Cockpit nav" topology above + the per-tab contracts.

- **Phase 1 — Contracts + CRUD matrix** — **Implemented 2026-04-24** (commit `936eacc`). ADR-215 + this doc + four archive supersedes + CHANGELOG entry.
- **Phase 2 — Files hardening** — **Implemented 2026-04-24**. `<EditInChatButton>` shared component landed at `web/components/shared/EditInChatButton.tsx` (R5 single label). `<SubstrateEditor>` landed at `web/components/workspace/SubstrateEditor.tsx` with `isSubstrateEditable()` predicate covering `/workspace/context/_shared/{IDENTITY,BRAND,CONVENTIONS,MANDATE}.md`. `ManageContextModal.tsx` deleted. `ContentViewer.tsx` refactored — substrate-editable files render inline editor, non-substrate files keep chat-draft affordance. Backend `editable_prefixes` gained `MANDATE.md`. Labels normalized across `WorkDetail.tsx` and `PrinciplesPane.tsx` to R5 ("Edit in chat"). Phase 2 follow-up (MemorySection on `/settings`) closed same day in the Settings cleanup commit — see CHANGELOG entry "Settings > Memory tab retirement." TypeScript pass.
- **Phase 3 — Agents hardening** — **Implemented 2026-04-24**. `PrinciplesPane` retired from chat-seeded edit path (R3 compliance). `/workspace/review/principles.md` added to both `SHARED_EDITABLE_PATHS` (frontend) and `editable_prefixes` (backend `api/routes/workspace.py`). PrinciplesPane now renders read-only with a deep-link to Files (`/files?path=/workspace/review/principles.md`) — same substrate editor as the four `_shared/` rules. `ReviewerDetailView` prop surface simplified (no `onOpenChatDraft` required; decisions stream was already read-only). `AgentContentView` YARNNN + domain + platform-bot + reviewer dispatch audited clean — no R5 label drift, AGENT.md edits continue to flow through primitives (judgment-shaped per R1). TypeScript pass.
  - **Known follow-ups (not blocking Phase 4):**
    - `web/components/settings/MemorySection.tsx` retains a parallel IDENTITY/BRAND edit path on `/settings`. Files is canonical; Settings mouth retires in a later sweep.
    - `TaskSetupModal` remains as the `/agents` `+` menu entry "Assign a new task" — it's a modal that seeds chat rather than a direct-create API call. R2 gray area. `/work` already uses `CreateTaskModal` for direct-create; Phase 4 reconciles the two creation modals into a single model per ADR-215 R2.
- **Phase 4 — Work hardening** — **Implemented 2026-04-24**.
  - `IntelligenceCard` silent-degrade fix per ADR-198 §3 Briefing invariant. The 404-before-first-run path is a normal empty state (task not scaffolded at signup per ADR-206), not an error. Missing output + transient HTTP failure both collapse to "Synthesis pending" placeholder. Retry box removed — Briefing never sprouts error chrome inside a list surface.
  - `CreateTaskModal` retired; `/work` `+` menu uses `TaskSetupModal` (singular creation flow across all four tabs). `api.tasks.create` client method removed (YARNNN is the sole frontend consumer of task creation via `ManageTask(action="create")`; backend POST `/api/tasks` endpoint preserved for the primitive). R2 singular-implementation achieved.
  - Cockpit-zone visual treatment on `/work` list mode: section labels "Cockpit" + "Work", subtle zone tint on Cockpit, zone padding. Single vertical scroll preserved per ADR-205 F2 — tab-ify was considered and rejected (would force proposals behind a click, undoes ADR-206 deliverables-first).
  - 4 kind-middles audited: zero R1/R3/R5 violations. Middles are content-only; edit affordances live in `WorkDetail` header (Run/Pause = Direct, Edit in chat = Chat) with R5-compliant labels from Phase 2.
- **Phase 6 — Snapshot reframe (2026-04-24)** — **Implemented 2026-04-24**.
  - The four-tab `WorkspaceStateView` overlay (Readiness / Attention / Last session / Activity) reframed as three-tab `SnapshotModal` (Mandate / Review standard / Recent). See the Chat contract's "Snapshot overlay" subsection above for the full shape.
  - Zero LLM at modal open — every tab reads substrate files and neutral audit ledgers; no summarization pass.
  - Stay-in-chat contract: overlay is *of* the conversation, not a nav hub. No outbound links per row. Close returns to typing.
  - Marker renamed `<!-- workspace-state: ... -->` → `<!-- snapshot: {"lead":"mandate|review|recent"} -->`. Header button label renamed "Workspace" → "Snapshot". `parseWorkspaceStateMeta` → `parseSnapshotMeta` (singular implementation, no dual markers).
  - `WORKSPACE-STATE-SURFACE.md` archived — the living contract for this overlay now lives here in SURFACE-CONTRACTS.
  - YARNNN prompts (`yarnnn_prompts/*`) updated to emit the new marker where applicable; `api/prompts/CHANGELOG.md` records the change per ADR-215 discipline rule 7.

- **Phase 7 — ADR-219 narrative absorption (doc-only)** — **Implemented 2026-04-26**.
  - Chat contract reframed as **the narrative surface** per FOUNDATIONS Axiom 9 — every invocation in the workspace surfaces here as an Identity-tagged entry with weight-driven rendering. Identity widening (`user | assistant | system | reviewer | agent | external`), weight gradient (`material | routine | housekeeping`), pulse vocabulary, filter bar, narrative_digest card all named in the contract.
  - Work contract amended: list-row headlines source from `GET /api/narrative/by-task` (ADR-219 Commit 4), not `task.last_run_at`. WorkDetail's run-history stays on `agent_runs` per ADR-219 D7.
  - Affordance cookbook gains three new rows: Make-this-recurring (Chat / R5), narrative filter chip (Direct), housekeeping digest expand (Direct).
  - **No code change in this phase** — ADR-219 Commits 1–6 already shipped (commits `1007869` → `e67abd6`, merged to main 2026-04-26). This is the canon-doc catch-up so SURFACE-CONTRACTS agrees with what live code does.
  - **Known follow-ups (deferred from Phase 7, not blocking):**
    - **Cockpit zone (BriefingStrip on /work) hasn't migrated to narrative.** `NeedsMePane`, `SinceLastLookPane`, `SnapshotPane`, `IntelligenceCard` all read `tasks` / `agents` / workspace files directly; the narrative endpoint is unused there. After a soak period of operator use, evaluate whether `SinceLastLookPane` should consume narrative directly (it most directly answers "what happened while I was away," which is what narrative is for). Two read paths to the same truth is acceptable for alpha — promote to drift if duplication causes operator confusion.
    - **D6 "Archive task (keep history)" affordance** belongs on WorkDetail, not Chat. Pairs with a future task-lifecycle commit. ADR-219 D6 part 2.
    - **Pulse + time-range filters** on Chat — richer UI than chips, deferred.

- **Phase 8 — Unified compositor seam (ADR-225 Phase 3)** — **Implemented 2026-04-27** (commits `3460919` → `[final]`). Bumps doc to v2.0.
  - **New Part 0** added: composition layer preamble + slot inventory + R6 (no FE branch on `program_slug`).
  - **R6 ratified** as the sixth CRUD rule. The compositor seam is the kernel/program boundary at the FE layer; bypassing it for "just one quick conditional" undoes the structural reason the seam exists.
  - **Work tab contract rewritten** around three compositor-resolved layers in detail mode (chrome / middle / feedback strip) and two compositor-resolved zones in list mode (cockpit panes / pinned tasks + banner). Per-kind hardcoded dispatch is gone from this contract — the contract describes what each layer does and where its declarations live.
  - **Operational vs historical timestamp rule** now contract-explicit (was code-implicit per the audit's observation #2). Chrome metadata shows operational signal; narrative carries historical context.
  - Closes the prior Phase 7 deferred follow-up: "Cockpit zone hasn't migrated to narrative." The cockpit zone is now compositor-resolved, which makes the migration question scoped — narrative-shaped panes can register as library components and bundles can swap them in via `cockpit_panes`.
  - **Code changes** absorbed: `WorkDetail.tsx` 515 → 164 lines (per-kind chrome dispatch + OverflowMenu DELETED); `BriefingStrip.tsx` DELETED; new `ChromeRenderer` + `CockpitRenderer` siblings to `MiddleResolver`; new `KERNEL_DEFAULT_CHROME` + `KERNEL_DEFAULT_COCKPIT_PANES` registries; new `WorkDetailActionsContext` + `CockpitContext` providers; alpha-trader SURFACES.yaml extended end-to-end.
  - **Known gaps named in `docs/architecture/compositor.md`** (not blocking):
    - `MiddleResolver` name overfits to "middle" now that `ChromeRenderer` and `CockpitRenderer` are siblings. Rename rejected (too many call sites); clarification at the doc layer is sufficient.
    - Bundle-supplied agent-tab and files-tab chrome are deferred — the resolver pattern is portable; extending to other tabs is incremental as bundles need it.
    - Multi-bundle chrome merge semantics tested on backend (10/10 ADR-225 backend tests still pass) but no real two-active-bundle workspace exists yet to surface FE rendering edge cases.

- **Phase 5 — Chat hardening** — **Implemented 2026-04-24**.
  - `OnboardingModal` + `ContextSetup` retired. Auto-trigger was already retired by ADR-190 (onboarding is conversational); the manual "Update workspace" `+` menu entry violated R2 (update is never Modal) and R3 (identity/brand/conventions are substrate). `WorkspaceStateView` identity-empty CTAs now seed chat prompts — YARNNN infers identity/brand from the conversation and writes via `InferContext` (post-ADR-235; the `InferWorkspace` first-act primitive was later removed per ADR-314 D4).
  - `/chat` `+` menu now has exactly one built-in entry: "Start new work" → `TaskSetupModal`. R4 fully enforced on Chat.
  - `ChatSurface.onContextSubmit` prop removed (orphan after OnboardingModal retirement); `/chat` page simplified.
  - `ReviewerCard` deep-link migrated `/review` → `/agents?agent=reviewer` (ADR-214 canonical route). Docstring updated with Stream archetype invariants.
  - `parseOnboardingMeta` export removed (dead code). `stripOnboardingMeta` retained — display hygiene for historical messages that may still carry the retired marker.
  - `ChatEmptyState` + 4-chip cold-start landing retained as-is — already R-compliant (seed composer text or open file picker).
  - Stale doc comments cleaned in `auth/callback/page.tsx`, `ComposerInput.tsx`, `TaskSetupModal.tsx`, `WorkspaceStateView.tsx`, `workspace-state-meta.ts`.
  - TypeScript pass. `grep -rn "Edit via" web/`: zero live hits. Full R1–R5 compliance across all four tabs.

- **Phase 9 — ADR-231 substrate-vocabulary alignment** — **Implemented 2026-04-29** (commits `b7e4fd3` Class A · `1a77459` Class B · this commit Class D).
  - **Class A logic fix**: `/context` Reports section deep-links migrated from the dead `/tasks/{slug}/outputs/latest` namespace to the natural-home `/workspace/reports/{slug}` substrate root per ADR-231 D2. Detail-mode dispatcher regex updated; `DeliverableMiddle` consumes via `api.recurrences.listOutputs` already (Phase 3.6/3.8 backend migration).
  - **Class B vocabulary refresh**: `ChatEmptyState` adds primary "Ask for something" chip per ADR-231 D1 invocation-first default — recurrence chips (Track / Build a recurring report) become explicit-graduation affordances at indexes 3-4. `TaskSetupModal` + `ChatSurface` + `client.ts` comment refs to `ManageTask` retired; all docstrings now point at `ManageRecurrence(action='create', ...)` per ADR-231 D5 + ADR-235 D1.c (ManageTask deleted in Phase 3.7; UpdateContext deleted in ADR-235).
  - **Class D doc refresh** (this entry): SURFACE-CONTRACTS.md Files tab list-mode tree, Work tab Reads section, Work `+` menu primitive ref, deep-links out, Chat tab Writes/Deep-links, inline-to-recurrence graduation flow — all aligned with ADR-231 D2/D3 natural-home substrate (`reports/{slug}/`, `context/{domain}/`, `operations/{slug}/`, `_shared/back-office.yaml`) + D5 primitive surface (`ManageRecurrence` + `FireInvocation`).
  - **Refuses preserved** — Class C file renames (`web/components/tasks/` → `recurrences/`, etc.) are pure cosmetic file moves; deferred to a quiet hygiene window once the parallel ADR-233 prompt reorg lands.
  - TypeScript pass. Backend tests 96/96 still green.

---

---

## ~~/workspace surface~~ — DISSOLVED by ADR-297 (2026-05-30)

> **Superseded.** The `/workspace` container surface (ADR-244, 2026-05-06) was dissolved by ADR-297 into atomic kernel surfaces — `WORKSPACE_CONFIG_ROUTE ('/workspace')` deleted 2026-05-30, zero consumers. Its concerns are now individual surfaces in the inventory (Part 1): active program / activate / deactivate → **Program** (`/program`); platform connections → **Connectors** (`/connectors`); per-file workspace setup (mandate/identity/brand/autonomy/principles state) → the **intent** + **os-config** surfaces (`/mandate`, `/identity`, `/autonomy`, `/principles`) + the constitution band on **Home**. The `/operation` stub redirects to `/mandate` (not the deleted `/workspace`).
>
> The backend read survives: **`GET /api/workspace/state`** — canonical workspace-state read, `{ has_agents, activation_state, active_program_slug, available_programs[], substrate_status, capability_gaps[] }` — consumed by the Program surface + first-run activation (ADR-244 / ADR-312 D6 constitution-band CTA). Activate/deactivate endpoints unchanged: `POST /api/programs/activate` (idempotent re-fork) + `POST /api/programs/deactivate` (soft, drops MANDATE.md program marker, body untouched per ADR-209).

---

## Related docs

- [ADR-215](../adr/ADR-215-surface-contracts-and-crud-principles.md) — governs this doc
- [ADR-297](../adr/ADR-297-surfaces-as-substrate-mirror.md) — **the surface model: windowed Desktop, surfaces-as-windows, `navigateToSurface`, `/recurrence` (dissolved `/work`)**
- [ADR-312](../adr/ADR-312-home-as-composition.md) — **Home as composition (six kernel slots); supersedes the ADR-228 four-faces cockpit**
- [ADR-198](../adr/ADR-198-surface-archetypes.md) — archetype vocabulary (Document · Dashboard · Queue · Briefing · Stream)
- [ADR-214](../adr/ADR-214-agents-page-consolidation.md) — Reviewer-inside-Agents (the four-tab nav it established was superseded by ADR-297's windowed model)
- [ADR-309](../adr/ADR-309-two-registers-settings-and-applications.md) / ADR-312 D5 — the register split (intent · os-config · application)
- [ADR-327](../adr/ADR-327-budget-and-the-self-improving-loop.md) — pace → budget surface collapse (supersedes ADR-300)
- [ADR-243](../adr/ADR-243-schedule-surface.md) — `/schedule` (dissolved into the Recurrence cadence list)
- [ADR-167 v2](../adr/ADR-167-list-detail-surfaces.md) — list/detail pattern (now per-surface)
- [ADR-209](../adr/ADR-209-authored-substrate.md) — revision chain, `authored_by`, substrate attribution
- [ADR-219](../adr/ADR-219-invocation-narrative-implementation.md) — invocation as atom; Feed is the narrative surface; Recurrence is the narrative filtered by task slug
- [ADR-225](../adr/ADR-225-compositor-layer.md) — compositor seam (chrome + middle through one resolver pattern; cockpit composition is now Home per ADR-312)
- [docs/architecture/compositor.md](../architecture/compositor.md) — architecture-level reference for the resolver pattern, binding taxonomy, kernel-default registry
- [invocation-and-narrative.md](../architecture/invocation-and-narrative.md) — canonical narrative vocabulary (invocation · pulse · narrative · task as legibility wrapper)
- [ADR-206](../adr/ADR-206-operation-first-scaffolding.md) — operator-facing three-layer view (Intent · Operation · Deliverables)
- [ADR-244](../adr/ADR-244-workspace-settings-surface.md) — the `/workspace` settings surface (dissolved into atomic surfaces by ADR-297, 2026-05-30)
- [ADR-320](../adr/ADR-320-constitution-region-topological-cut.md) — the five-root substrate topology the surface contracts read
- [ADR-168](../architecture/primitives-matrix.md) — canonical primitive matrix (not a design doc, but the authority for what verbs exist)
- [FOUNDATIONS v6.8](../architecture/FOUNDATIONS.md) — Axiom 6 (Channel), Axiom 9 (Invocation + Narrative), Derived Principle 12 (Channel legibility gates autonomy)
- [INLINE-PLUS-MENU.md](./INLINE-PLUS-MENU.md) — existing plus-menu verb taxonomy; under ADR-215 R4 it is strictly a modal launcher
