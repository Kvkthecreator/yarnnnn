# ADR-309 — Two Registers: System Settings and Applications. Hardening the Surface Concept Against the OS Primitives

> **AMENDED by [ADR-312](ADR-312-home-as-composition.md) (2026-06-02):** the single `settings` register cleaves into **`intent`** (the operation's authored intent — Mandate, Principles, Identity, surfaced first-class as the Home's Constitution band) and **`os-config`** (the OS configuring itself — Autonomy, Pace, Connectors, Program, Settings). ADR-309's two-register *insight* — distinguishing "the OS configuring itself" from "open files + live state" — holds; ADR-312 refines it by recognizing that the authored *constitution* (mandate/principles/identity) is not OS config at all but the operation's charter, and pulls it out of the config drawer into the Home. The `application` register and the type→application association layer are unchanged. The Cockpit `application` surface renames to **Home** (ADR-312 D1). See `SurfaceRegister = 'intent' | 'os-config' | 'application'`.
>
> **Status:** Implemented (2026-06-01) — frame ratified + enacted in one pass. **Register re-classification landed**: every content kernel surface carries `register: settings | application` (backend `kernel_surfaces.py` + FE `Surface` type); `brand` slug DELETED (Identity owns Brand; `/brand` → server redirect). **Type→application association landed**: the layer already existed as a private `getFileKind` buried in `ContentViewer.tsx` — ADR-309 *lifted* it into the named, shared, kernel-default module `web/lib/file-types` (`resolveViewerApplication`); ContentViewer now dispatches through it. **No parallel report Application built** — the report/artifact Application already exists as `DeliverableMiddle`, wired in `files/page.tsx` for `/workspace/reports/{slug}`; building a second would violate Singular Implementation. Guards: `api/test_adr309_two_registers.py` 9/9 + `test_adr297_phase1.py` register-coherence 137/137. Agent-composed applications remain the explicit deferred horizon (§Forward horizon). Implementation-time finding: the "missing artifact/PDF viewer" the operator named was **already present** in ContentViewer (pdf→iframe, image→img, html→iframe) — the un-hardening was that it wasn't *named* as the OS-level type→application layer. Naming it closed the conceptual gap without new viewer code.
> **Authors:** KVK, Claude
> **Amends:** [ADR-297](ADR-297-surfaces-as-substrate-mirror.md) (sharpens the flat "surface" concept into two registers; ADR-297's window-manager axiom and Desktop layer are preserved verbatim) · [ADR-225](ADR-225-compositor-layer.md) (the compositor reads which application opens an input, not just middle-component resolution)
> **Enacts (from "Not yet built" → named + framed):** [ADR-222](ADR-222-agent-native-operating-system-framing.md) rows — *Compositor / window manager*, *Per-user customization layer* (the type→application association), *Shared system libraries* (the renderer/component library)
> **Preserves:** [ADR-222](ADR-222-agent-native-operating-system-framing.md) kernel boundary + OS primitive set (this ADR is faithful to it, not a departure) · [ADR-245](ADR-245-frontend-kernel-three-layer-content-rendering.md) three-layer content model (becomes the renderer mechanism) · [ADR-213](ADR-213-surface-pull-composition.md) (tasks write substrate, surfaces render — generalized to "artifacts are files, applications render them") · [ADR-209](ADR-209-authored-substrate.md) · [FOUNDATIONS](../architecture/FOUNDATIONS.md) Axioms 1–9 · ADR-308 (independent; the bug-class fix that this frame contextualizes)
> **Dimensional classification:** **Channel** (Axiom 6 — the operator-facing window onto the system) + **Substrate** (Axiom 1 — artifacts-are-files)

---

## Context

[ADR-222](ADR-222-agent-native-operating-system-framing.md) canonized YARNNN as a literal agent-native operating system and named a clean primitive set: **kernel** (substrate + primitives + axioms + daemons), **compositor / window manager**, **application / program**, **userspace**, **shared system libraries**, and a **per-user customization layer** ("user overrides of application defaults"). Three of those — compositor, customization layer, system libraries — were marked *"Not yet built"* or *"convention not yet formal."*

[ADR-297](ADR-297-surfaces-as-substrate-mirror.md) then introduced **"surface"** as the frontend unit and shipped a real window manager (`useSurfacePreferences`, Desktop layer, WindowFrame, multi-mount). This was correct and load-bearing. But "surface" was coined as a **single flat concept**: one `KERNEL_SURFACES` list keyed by `slug`, differentiated only by an `archetype` string (document / dashboard / browser / roster / queue / stream / …). That flatness **collapsed several distinct ADR-222 primitives into one word.** The result is an un-hardened model that produces recurring operator-felt confusion. Three confusions, observed across this discourse:

1. **"Configuring `MANDATE.md` / `_autonomy.yaml` as 'surfaces' feels confused — but they DO warrant a dedicated view because they ARE the OS"** (cf. configuring trackpad settings on a Mac).
2. **"Agent-generated artifacts (a composed report, a PDF) need something closer to a file-viewer / PDF-viewer — and that seems to conflict with the `.md` governance 'surfaces'."**
3. **"Cockpit, and future agent-scaffolded synthesis views, feel confusing as the same kind of thing as the governance surfaces."**

These are not three bugs. They are **three faces of one fault**: "surface" is doing the work of four different OS concepts at once (a System Preferences pane, a file, a file-type, an application). The frontend feels un-hardened because the concept *is* un-hardened.

This ADR hardens it by mapping "surface" back onto the OS primitives ADR-222 already canonized. It is a **clarification of the existing canon, not a new architecture** — and per the operator's sequencing instruction it is **frame-only**: re-classify on paper now, refactor incrementally later, do not rebuild.

---

## Foundational principle

> **The authenticated workspace is an OS Desktop with two registers of windowed thing, sharing one window manager. Register 1 is System Settings (the OS configuring itself). Register 2 is Applications (the OS opening files and live state). A real OS has both; collapsing them into one "surface" concept is the un-hardening.**

The window manager (ADR-297, shipped) is unchanged — it instantiates *either register* as a window on the Desktop. What this ADR adds is the **register distinction** and the **type→application association layer** that the artifact-viewer need requires.

---

## The two registers

### Register 1 — System Settings (self-configuration panes)

A **Settings pane** is the OS configuring *itself*. It is the macOS System Settings analog: "Trackpad," "Energy," "Apple ID." In YARNNN these are the **governance substrate** panes — each binds 1:1 to a known governance file and renders a bespoke, purpose-built editor/view for it.

| Settings pane | Governance substrate | Why it's Register 1 |
|---|---|---|
| Mandate | `/workspace/context/_shared/MANDATE.md` | Configuring the workspace's standing intent = configuring the OS |
| Autonomy | `/workspace/context/_shared/_autonomy.yaml` | How far the Reviewer's decisions bind = OS execution policy |
| Principles | `/workspace/review/principles.md` + `_principles.yaml` | The judgment framework = OS policy |
| Pace | `/workspace/context/_shared/_pace.yaml` | Workspace rhythm = OS scheduling policy |
| Identity | `/workspace/context/_shared/IDENTITY.md` | Operator persona = OS account identity |
| Brand | `/workspace/context/_shared/BRAND.md` | Stylistic constraints = OS appearance policy |
| Program | `/workspace/_program.yaml` + bundle MANIFEST | Which program is "installed" = OS distribution config |

**Properties of Register 1:**
- **Finite + defined-by-existence.** The set is fixed by what the OS (kernel) and the installed program *are*. The operator does not install, request, or generate Settings panes. A program *can* contribute Settings panes (a program adds policy the operator configures) — same as a macOS app adding a Settings pane.
- **Bound (1:1) + bespoke.** Each pane knows its substrate file at definition time and renders a purpose-built affordance (ADR-245's L3). A Mandate editor ≠ an Autonomy toggle ≠ a Principles thresholds editor.
- **Self-configuration, not content.** You are changing how the OS *behaves*, not producing or consuming a document.
- **Provenance tiers:** kernel-shipped (the governance panes above) or program-installed (a bundle's policy panes). The agent-operator tier here means the *operator authors the substrate content via chat* (per ADR-206 D6 / ADR-235) — the pane is the window onto that authoring; the agent does not invent new Settings panes.

### Register 2 — Applications (open files and live state)

An **Application** opens an *input* into a window. The input is one of:
- a **typed userspace file** — a generated report (`/workspace/reports/{slug}/{date}/output.md` + assets), a PDF, an image, an upload. The application that opens it is determined by the file's **type** via the association layer (below). *This is the "file-viewer / PDF-viewer" the operator named as missing.*
- a **folder / the filesystem** — the Files application (Finder): navigates `workspace_files`, and opening a file launches that file's associated application.
- **live state** — Cockpit is the Activity-Monitor analog: it reads many substrate sources + DB tables and composes a live operating view. Activity, Queue, Feed, Agents are the same shape (read live state / a collection, compose a view).

| Application | Input | Analog |
|---|---|---|
| Files | the filesystem (`workspace_files`) | Finder |
| (report/artifact viewer) | a typed file (`reports/.../output.md`, `.pdf`, `.png`) | Preview / Quick Look |
| Cockpit | live state (mandate + autonomy + performance + positions + signals) | Activity Monitor / a dashboard widget |
| Feed | session_messages (live narrative) | Messages / a log viewer |
| Queue | action_proposals (pending) | a task inbox |
| Activity | execution_events (live log) | Console |
| Agents | agents table + per-agent substrate | a roster / contacts app |

**Properties of Register 2:**
- **Open-ended.** Userspace files are infinite; a small set of applications open their types.
- **Type-driven dispatch.** A file's *type* binds to a default application (next section). Files (Finder) launches the right application per file.
- **Provenance tiers:** kernel-shipped (Files, Cockpit, Feed, Queue, Activity, Agents), program-installed (a bundle's applications — e.g. alpha-trader's TraderSignals / TraderOrders views per ADR-273), or — **named horizon, deferred (§Forward horizon)** — agent-composed at runtime.

### One window manager

Both registers render as windows on the Desktop via the **single** shipped window manager (`useSurfacePreferences` + Desktop + WindowFrame, ADR-297). There is no second rendering mode. A Settings pane and an Application are both windows; they differ in *what they are* (self-config vs file/state), not in *how they mount*.

---

## The type → application association layer (enacts ADR-222's customization layer)

ADR-222 named a *"per-user customization layer — user overrides of application defaults"* and marked it **not built.** The artifact-viewer need makes it concrete and necessary. The layer answers: **given a userspace file, which application opens it?**

- A file declares (or is inferred to have) a **type** — by path convention + extension + frontmatter `kind` (the ADR-245 content-shape resolution already does shape detection; this generalizes it to a stable type identifier).
- A **type → default-application** table maps each type to the application that opens it: `composed-report → report-viewer`, `pdf → pdf-viewer`, `png → image-viewer`, `governance-md → (its Settings pane)`, plain `md → prose-viewer`, `_*.yaml → config-viewer`.
- The table has **kernel defaults**; whether the **operator/agent can rebind defaults** is left open (a named option, not decided this cycle — see Open questions).

**The renderer is the application's body; the association is the binding.** This subsumes ADR-245's three-layer model: L1 (raw view) = the universal fallback application; L2 (content-shape parser) = type detection; L3 (structured affordance) = the bespoke application/pane body. ADR-245 is preserved and slots in as the *rendering mechanism inside an application*; ADR-309 adds the *which-application-opens-this* layer above it.

**Artifacts are files, not surfaces.** This resolves confusion #2 definitively, and generalizes ADR-213 (tasks write substrate, surfaces render): a Reviewer-generated report/PDF is a **userspace file**; the **report/PDF application** opens it; Files dispatches to it on open; Cockpit may *embed* it (an application embedding another application's rendered output — ADR-225's `surface_embeds_document`). One artifact, potentially many applications showing it. No conflict with the governance Settings panes, because those are a different register entirely.

---

## Re-classification of the existing 16 kernel surfaces (on-paper)

Per "stabilize + refactor on the existing," every current `KERNEL_SURFACES` entry maps to exactly one register. No surface is deleted; this is a re-label that guides the future refactor.

| Current surface (ADR-297) | Register | Notes |
|---|---|---|
| `mandate` | **Settings** | governance-md pane |
| `autonomy` | **Settings** | `_autonomy.yaml` pane |
| `principles` | **Settings** | principles pane |
| `pace` | **Settings** | `_pace.yaml` pane |
| `identity` | **Settings** | governance-md pane |
| `brand` | **Settings** | governance-md pane |
| `program` | **Settings** | distribution/program config pane |
| `settings` | **Settings** | account/billing — the canonical Settings container (intra-pane `?tab=`) |
| `connectors` | **Settings** | platform-connection policy pane |
| `files` | **Application** | Finder — dispatches to per-type applications on open |
| `cockpit` | **Application** | Activity-Monitor (live state) |
| `feed` | **Application** | narrative log viewer |
| `queue` | **Application** | proposal inbox |
| `activity` | **Application** | execution-event log viewer |
| `agents` | **Application** | roster |
| `cadence` | **Application** | live state (recurrences + hooks + standing intent) — reads many sources, composes |

Plus the **(report/artifact) application** — *currently missing as a first-class entry*; it is the home for confusion #2 and the first concrete new Application the refactor adds (it already exists fragmentarily as `DeliverableMiddle` + the compose pipeline; the refactor formalizes it as the file-type-launched application).

The chrome entries (`top-bar`, `launcher`, `chat-drawer`) are neither register — they are the **window manager's own chrome** (ADR-297 D11–D12). ([ADR-316](ADR-316-chat-as-dockable-rail.md) later moves `chat-drawer` from the `floating-overlay` region to a dockable `main-rail` — chrome that *frames* the active surface beside it rather than occluding it — but it remains chrome, neither register.)

---

## Forward horizon — agent-composed applications (directionally ratified, deferred)

The fullest expression of agent-native OS: **the agent installs applications.** Three running models, layered, in sequence:

1. **System Settings** (Register 1) — finite, ships with the OS/program. *Stabilize now.*
2. **Install a program** (`.app` bundle) — operator activates an opinionated operation; it brings its Settings panes + its Applications. *Exists today (program-activation); refactor under this frame now.*
3. **Agent-composed Applications** — the orchestration layer (Reviewer / operator-via-chat) authors an **application manifest as a file in the substrate** (everything-is-a-file extends to app definitions, exactly as macOS `.app` bundles are directories of files); the compositor (ADR-225) reads installed-app manifests the way Finder reads `/Applications`. Includes both operator-requested ("make me a view of X") and — the distinguishing move — **mandate-driven self-initiative** (the OS grows its own views in pursuit of standing intent, the same way the Reviewer authors a recurrence or `standing_intent.md`).

**Decision: model 3 is directionally ratified as the OS's defining capability but explicitly deferred.** The operator's instruction is *stabilization and refactoring on the existing first.* This ADR commits to leaving the seam clean — the compositor + application-manifest path is the named mechanism — without building the authoring affordance. No agent-composed-application code, no manifest schema, this cycle.

---

## What this ADR does NOT do

- **Does not touch the window manager, Desktop, or WindowFrame** (ADR-297 shipped; preserved verbatim).
- **Does not build a parallel report/artifact Application** — it already exists as `DeliverableMiddle`; ADR-309 names it as the report Application and reuses it (Singular Implementation).
- **Does not build a new viewer for PDFs/images/html** — those renderers already exist in ContentViewer; ADR-309 only *named + centralized* the type→application association that selects them.
- **Does not expose operator/agent override of type→app defaults** — kernel defaults only (Open question 1).
- **Does not build agent-composed applications** — directionally ratified, deferred, seam kept clean.
- **Does not change the public/marketing site.** Decided this discourse: the public route group (`/`, `/blog`, `/pricing`, `/faq`, …) stays conventional, SEO-first, page-shaped **forever**. The OS framing is strictly behind-auth (robots.ts disallows every authenticated route). Two disjoint territories: the indexed web (pages) and the OS (windows). The OS framing does not threaten SEO/GEO — it clarifies the boundary.

---

## Refactor — as built (2026-06-01)

1. **Re-label by register — DONE.** `register: "settings" | "application"` added to every content surface in `kernel_surfaces.py`; FE mirror = `SurfaceRegister` + optional `register` on the `Surface` type (`compositor/types.ts`); flows to the FE automatically via `kernel_surface_entries()` deep-copy (no resolver whitelist). Coherence guarded in `test_adr297_phase1.py` (content surfaces have a valid register; chrome has none) + `test_adr309_two_registers.py`.
2. **`brand` deleted — DONE.** Removed from `KernelSurfaceSlug` union, `KERNEL_SURFACE_SLUGS`, `KERNEL_SURFACE_REGISTRY`, `kernel_surfaces.py`, and the nav/phase1 guards. `/brand` is a server redirect → `/identity` (ADR-308 transport). Identity surface (IdentityBrandCard) co-renders Brand.
3. **Type→application association formalized — DONE.** `web/lib/file-types/index.ts` (`resolveViewerApplication` + `describeViewerApplication`) is the kernel-default table, lifted out of `ContentViewer.tsx`'s private `getFileKind`. ContentViewer dispatches through it. The report/artifact Application is the *existing* `DeliverableMiddle` (wired in `files/page.tsx`) — not duplicated.
4. **Operator/agent override of type→app defaults — DEFERRED** (Open question 1). Kernel defaults only.
5. **Agent-composed-application seam — DEFERRED**, documented in `compositor.md` as the named horizon.

---

## Open questions (deferred)

1. **Is the type→application association table operator/agent-overridable, or kernel-default-only?** (Undecided this discourse. macOS allows rebinding; YARNNN may want it for the agent tier eventually. Default kernel-only is the safe start.)
2. **Application-manifest schema** for the agent-composed horizon — deferred until model 3 is in scope.
3. **Does Cadence belong in Application or is it a hybrid?** It reads live state (Application) but also configures recurrences (Settings-like). Provisionally Application (it's a live dashboard you act from); flagged for the refactor.

---

## Consequences

- **The surface concept is hardened**: "surface" resolves into *Settings pane* (Register 1) or *Application* (Register 2), both windowed by the one manager. The four-concepts-in-one-word collapse is undone.
- **All three operator confusions get a stable home**: governance `.md`/`.yaml` = Settings panes (they ARE the OS); artifacts = files opened by Applications via type-association; Cockpit + future synthesis = Applications (live-state, and the agent-installed horizon).
- **ADR-222's "not built" rows get named and framed** — compositor, customization layer, system libraries — closing the gap between the OS framing and the surface implementation.
- **Faithful to the OS, not to our conventions.** The frame is derived from how a real OS decomposes (Settings vs Applications, type→app association, app provenance), then mapped onto already-canonical YARNNN primitives — not reverse-engineered from the existing registry shape.
- **Sequenced, not big-bang.** Stabilize + refactor the existing kernel/program tiers under this frame; defer agent-composed applications with a clean seam.
