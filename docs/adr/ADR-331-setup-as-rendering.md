# ADR-331 — Setup-as-Rendering: the `/setup` Sequence Surface and the Harvest Invocation

**Status:** **Phases 1 + 2 Implemented** (2026-06-10) — `/setup` Sequence surface (P1: D1/D2/D6 CTA) + the curated harvest invocation + scope picker (P2: D3/D4) landed. Regression gate `api/test_adr331_setup_rendering.py` 17/17 PASS; ADR-297 P1 kernel-surface gate 7/7 PASS; FE `tsc --noEmit` clean; harvest route + service import clean. Phase 3 (multi-file upload, D5) pending. *(Two pre-existing ADR-312 D9 gate failures — `/api/cockpit` mount folding — are a concurrent lane's in-flight work, orthogonal to this ADR; verified identical with ADR-331 changes stashed.)*
**Date:** 2026-06-10
**Deciders:** KVK (operator) + Claude (collaborator)
**Hat:** A (system canon — real-operator-facing)

> **Discourse base:** [`reality-in-current-standing-and-setup-as-rendering-2026-06-10.md`](../analysis/reality-in-current-standing-and-setup-as-rendering-2026-06-10.md) §1a (context-in's three modes), §3 (the dual-tracking retraction — *harvest is an invocation, not a subsystem*), §4 (setup-as-rendering, the macOS mapping). Receipts re-verified 2026-06-10 (discourse capture §0). **Companion ADR:** [ADR-330](ADR-330-ground-truth-intake.md) handles flow 3 (outcomes in); this ADR handles flow 1 (context in) + its rendering. **Post-pause addendum (same day):** [`four-flow-completeness-and-program-floor-2026-06-10.md`](../analysis/four-flow-completeness-and-program-floor-2026-06-10.md) supplies the deeper frame this ADR's sequence walks: a program IS a flow-declaration set, and `/setup` is **flow-declaration walking** — the kernel's definition of "becoming operational," rendered as a sequence. A lens, not a scope change.

**Amends:**
- [ADR-297](ADR-297-surfaces-as-substrate-mirror.md) — adds `setup` to the `KERNEL_SURFACES` registry (a kernel atomic surface, **Sequence** archetype) and **changes the first-run redirect target** from `/program?first_run=1` to `/setup?first_run=1`. (ADR-297's migration had already moved the redirect off ADR-244 D5's `/settings?tab=workspace`; this ADR moves it one more hop to the new guided surface.)
- [ADR-244](ADR-244-workspace-settings-surface.md) — the Settings → Workspace / `/program` lifecycle drawer is **unchanged and retained** as the random-access *reference* rendering. ADR-331 adds the *sequence* rendering; both read the same `api.workspace.getState()` endpoint. D5's redirect framing is fully superseded by the ADR-297 + ADR-331 chain.
- [ADR-312](ADR-312-home-as-composition.md) — the home empty-state CTA (`UnactivatedHomeCTA`) repoints from `/program` to `/setup`. The home still only **points** to setup; it never grows setup functionality (D6 boundary preserved).
- [ADR-205](ADR-205-primitive-collapse.md) — the harvest is an instance of ADR-205's inline-action→recurrence graduation: harvest = the inline action; ongoing live reads = its graduated recurrence form. One mechanism, two trigger shapes (Axiom 4). No new primitive.

**Preserves:** FOUNDATIONS Axioms 0–9 · Axiom 1 (substrate is the record — no stored wizard state) · Axiom 4 (Trigger — harvest is an addressed trigger, recurrence is its periodic form) · [ADR-153](ADR-153-platform-content-sunset.md) (no continuous sync; harvest is bounded + attributed) · [ADR-209](ADR-209-authored-substrate.md) (harvest writes attributed substrate, `agent:harvest`) · [ADR-329](ADR-329-files-as-first-class-work-legibility-surface.md) (Files stays the raw substrate surface; `/setup` does not colonize it) · ADR-297 atomic-surface + compositor-registry + summon-index model · ADR-244 lifecycle drawer.

---

## 1. Problem statement

Two gaps, one resolution.

### Problem A — first boot is an anti-welcome

A brand-new operator's first authenticated experience is a redirect into `/program?first_run=1` (live, `web/app/auth/callback/page.tsx`) — the `ProgramLifecycleDrawer` rendered over `api.workspace.getState()`. That drawer is a **reference** surface: random-access, status-board-shaped, built for an operator who already knows what a program is and wants to switch or deactivate one. Dropping a first-time operator into it is the equivalent of booting a new Mac straight into System Settings instead of Setup Assistant. The operator sees a config panel, not a guided sequence; the welcome is missing.

### Problem B — context-in has no catch-up door

The operation's first flow — **context in** — has three modes (discourse capture §1a):

- **Mode A — live reads at execution time:** built as capability (Slack/Notion/GitHub/Trading/Commerce read tools + kernel `WebSearch`), but active bundles declare only a thin slice (alpha-trader = trading; alpha-author = `read_uploads` + `websearch`). Slack/Notion/GitHub reads are wired and used by no active program.
- **Mode B — operator push:** built, manual-grade. Single-file 25MB upload (receipt: `api/routes/documents.py::MAX_FILE_SIZE = 25 * 1024 * 1024`, single `UploadFile`), chat, MCP `remember_this`, text-paste bulk-import. **No archive/multi-file path.**
- **Mode C — catch-up/harvest of pre-YARNNN reality:** **not built.** A new operator's fragmented reality (Notion spaces, Slack history, drives, logs) has no door beyond one-file-at-a-time.

Mode C is the onboarding gap. A new operator's accumulated context — the thing that makes the workspace cumulative — has no way in at the scale reality arrives in.

### Why this is not an ADR-153 violation (the line that must hold)

ADR-153 killed *continuous sync into an unattributed shadow content table*. A catch-up harvest is **dimensionally different**: a bounded invocation — addressed trigger, reads via Mode-A tools that already exist, writes **attributed, curated substrate** into context domains (`agent:harvest`, dated, revisioned per ADR-209). The machinery exists end-to-end. What's missing is the *product motion*, not architecture. The discipline (discourse capture §3) is binding: **harvest is an invocation, not a subsystem; the substrate is the record.**

---

## 2. Decision summary

| # | Decision | Shape |
|---|---|---|
| **D1** | **`/setup` is a kernel atomic surface (Sequence archetype), a RENDERING over the existing workspace-state endpoint** — not a system. One state source (`api.workspace.getState()`), one action set, two renderings (sequence = `/setup`; reference = `/program` drawer, unchanged). **No stored wizard-state** — progress is derived from substrate. | FE + compositor |
| **D2** | **First-run redirect target moves** `/program?first_run=1` → `/setup?first_run=1` (amends ADR-297). `/setup` is re-enterable any time (Migration-Assistant property). Home CTA + summon-index also point to it. | FE |
| **D3** | **The harvest invocation is an ordinary ADR-205 addressed inline action.** Reads via existing Mode-A read tools (slack/notion/github reads, uploads, web), writes attributed substrate (`agent:harvest`) into context domains, narrative entries its only trace. **No harvest subsystem, no coverage state.** | Backend (light) |
| **D4** | **Scope control is a custom picker UI in v1.** The `/setup` "bring in reality" step renders a source/range selector (available connected platforms + their containers, range pickers) with an inline **dry-run estimate** ("~N pages → these domains") computed from a metadata-only read. The operator selects + confirms; the harvest fires. **Selection state is ephemeral** — it lives in component state until confirm, never persisted (the no-stored-state rule holds: the picker chooses scope, the substrate records what got brought in). | FE + backend (dry-run endpoint) |
| **D5** | **Minimal multi-file upload lands here** (Mode B is half of "bring in reality"): accept multiple files in one `/documents/upload` call + a single archive (`.zip`) that expands to per-file `/workspace/uploads/{slug}.md`. Same 25MB-per-file cap, same attributed-substrate write. | Backend + light FE |
| **D6** | **Home/Files boundaries restated (not reimplemented):** Home's empty state POINTS to `/setup` (CTA repointed); Files stays the raw substrate surface. `/setup` never grows into either. | Boundary restatement |

**Anti-goals (binding):**

- **No stored wizard/setup/coverage/progress state.** Every "step done?" answer is derived from substrate (files authored? connections active? harvest invocations ran in narrative?). If a step needs state the substrate can't derive, the step is wrong (discourse capture §4).
- **No harvest manager.** No `_harvest_tracker.md`, no `sync_registry` rebirth, no per-source coverage table. What's been brought in = the files that exist, attributed and dated.
- **No continuous sync** (ADR-153 stands).
- **No new primitive for harvest** — it's an addressed invocation using existing read tools + `WriteFile` (the dimensional test: harvest is an existing mechanism with a different trigger shape, not a new cell).

---

## 3. D1 — `/setup` is a rendering, not a system

The macOS mapping resolves the UX without dual machinery, because macOS Setup Assistant **has no state of its own** — it writes the same preferences domain that System Settings displays. One substrate, two presentation registers.

| macOS | YARNNN | Standing |
|---|---|---|
| Setup Assistant (first boot, thin, guided sequence) | **`/setup`** — a Sequence-archetype kernel surface rendering over `api.workspace.getState()` | **To build** (this ADR) |
| Migration Assistant (bring your stuff; re-runnable) | The harvest invocation(s), fired from a `/setup` step or chat, with scope control | **To build** (D3/D4 — invocation + picker, no subsystem) |
| System Settings (random-access reference) | `/program` lifecycle drawer (ADR-244/297) + connectors | **Built** (unchanged) |
| Desktop / Finder | Home (ADR-312 composition) / Files (ADR-329) | **Built** (boundary held — D6) |

**The shape:**
- **One state source:** `api.workspace.getState()` (ADR-244 shape, re-verified live: `activation_state`, `available_programs`, `substrate_status` per-file skeleton/authored classification, `capability_gaps`). `/setup` adds **no** state, queries this endpoint.
- **One action set:** activate program · connect platform · author constitution (via the ADR-226 chat overlay deep-link) · fire harvest invocation. Every action already exists; `/setup` orders them.
- **Two renderings:** sequence (`/setup`, full-bleed, ordered, re-enterable — "setup, not onboarding") and reference (`/program` drawer). Complete a step anywhere; both renderings reflect it because both read the same substrate.
- **Progress is derived, never stored:** a step is "done" because the substrate says so — `substrate_status.mandate == authored` (constitution authored), a `platform_connections` row is active (platform connected), narrative shows a fired harvest invocation (reality brought in). **Dual tracking is impossible because there is nothing to drift.**

**Registration (ADR-297 model):** `setup` becomes a `KERNEL_SURFACES` entry in `api/services/kernel_surfaces.py`:
```python
{
    "slug": "setup",
    "register": "os-config",         # ADR-309/312 — it configures the OS, not an open file
    "title": "Setup",
    "archetype": "sequence",         # extends ADR-198 archetype catalog (new: Sequence)
    "substrate_paths": [],           # reads api.workspace.getState() composition, owns no file
    "icon_key": "rocket",            # finalize at implementation
    "default_pinned": False,         # summon-only after first run
    "route": "/setup",
    "summary": "Guided first-boot sequence — activate, author, connect, bring in reality.",
},
```
It flows through the compositor's `surfaces[]` registry and appears in the summon-index under the *Workspace* tier group, exactly like every other kernel surface. No parallel registry.

**Sequence archetype (new, extends ADR-198):** a Sequence surface renders an ordered list of steps, each step a *derived* status (incomplete/complete from substrate) + an action affordance. It is the guided, ordered presentation of substrate that a Dashboard presents random-access. The invariant: **a Sequence surface stores no progress of its own** — step status is computed from substrate at render time. This is the archetype-level encoding of the no-wizard-state rule.

**Plausible sequence steps (each an existing mechanism, each derived — and, per the four-flow lens, each the declaration/completion of one flow of the operation):**
1. **Pick program** (or bare workspace) — done when `active_program_slug` set; action = activate via `/program` lifecycle or inline. *(Direction A: program-activation is the floor; the bare-workspace card stays the honest secondary per ADR-240 — a resting state, not an operating path.)*
2. **Author constitution** — done when `substrate_status.mandate/identity` authored; action = ADR-226 chat-overlay deep-link. *(Purpose.)*
3. **Connect platforms** — done when `capability_gaps` empty for the active program; action = connectors. *(Flow 1 + flow 2 transports.)*
4. **Bring in reality** — done when a harvest invocation appears in narrative OR uploads exist; action = harvest invocation (D3/D4) + multi-file upload (D5). *(Flow 1, self-past.)*
5. **First artifact lands** — done when the operation produces its first output; action = (program-specific, points to Home). *(Flow 2 live — and with ADR-330's D4, flow 3/4 light up behind it.)*

---

## 4. D3 — the harvest invocation

Harvest is an **ordinary ADR-205 addressed inline action**. It is not a new mechanic — it fails the dimensional test for "new cell" and passes as "existing mechanism, different trigger shape" (the operator addresses it once; its graduated form is a periodic recurrence — Axiom 4, exactly ADR-205's inline-action→recurrence lifecycle).

- **Reads:** via existing Mode-A read tools — slack/notion/github reads (capability-gated by active connections), `read_uploads`, kernel `WebSearch`. No new read capability.
- **Writes:** **attributed substrate** into context domains via `WriteFile` (ADR-209). Author string `agent:harvest` — verified valid against `api/services/authored_substrate.py::is_valid_author` (the `agent:` prefix is in `VALID_AUTHOR_PREFIXES`). Dated, revisioned, content-addressed like every other workspace write.
- **Trace:** narrative entries only. There is **no harvest subsystem, no coverage table, no `_harvest_tracker.md`.** The dual-tracking retraction (discourse capture §3) is binding here: "what's been brought in" = the files that exist, attributed and dated; the calibration question "did we cover everything?" is answered by reading the substrate, never by a stored coverage ledger.
- **Lifecycle:** the harvest inline action graduates to a recurrence ("read these spaces every morning") via the **existing** ADR-205 graduation path — no new graduation mechanism. The recurrence form is just Mode A on a periodic trigger.

**Why no new primitive:** the harvest agent is a normal addressed invocation with the read tools + `WriteFile` already in its surface. The only "new" thing is a product motion (a named harvest agent + the `/setup` step that fires it), not a capability. *(Implementation note: whether "harvest" is a dedicated agent identity or an addressed turn to an existing agent with a harvest-shaped prompt is a Phase decision; either way it uses the existing tool surface and `agent:harvest`/equivalent attribution — no new primitive, no new permission mode.)*

---

## 5. D4 — scope control (custom picker UI in v1)

The Migration Assistant works because **you pick what to migrate.** Without scope control, "bring in reality" degrades to "ingest everything" — a cost-and-curation failure, since the substrate's value is *authored and curated*, not hoarded.

**v1 is a custom picker UI:**
1. The `/setup` "bring in reality" step renders a **source/range selector** — the operator's connected platforms and their containers (Slack channels, Notion spaces/pages, GitHub repos), each with a range control (date window or item count). Sources are read from active `platform_connections` + the existing list-tools (`list_channels`, Notion `search`, `list_repos`), so the picker shows only what's actually connected — no manual id entry.
2. As the operator selects, a **dry-run estimate** updates inline ("~400 pages across 3 spaces → these context domains") — computed by a **metadata-only read** (counts, not full content; new lightweight dry-run endpoint that reuses the read tools' count/list shape, performs no writes).
3. The operator confirms; the harvest invocation (D3) fires with the selected scope, writing attributed substrate.

**Selection state is ephemeral — the no-stored-state rule holds.** The picker's selections live in component state until confirm; nothing about *what the operator considered* or *intends to harvest* is persisted. The substrate records only *what got brought in* (the attributed files the harvest wrote) — never a scope-plan or a coverage target. The picker chooses scope; the substrate is the record (discourse capture §3). There is no `_harvest_scope.md`, no saved selection, no resume-where-you-left-off — re-entering `/setup` re-renders the picker fresh from current connections.

**Why a picker over chat in v1 (operator decision):** the picker gives a tighter, more legible first-run feel — the operator sees their actual connected sources and dials scope directly, rather than describing them in prose and trusting the agent's interpretation. The dry-run-before-fire loop is more trustworthy as a visible estimate than a chat assertion. *(Cost weighed and accepted: the picker is more FE surface than a chat deep-link, and the dry-run needs a small metadata-only endpoint. The discipline guard against a "parallel scope-state surface" is satisfied by keeping selection ephemeral — the picker is a transient chooser, not a persisted plan.)*

---

## 6. D5 — minimal multi-file upload

Mode B (operator push) is half of "bring in reality," and it's stuck at one-file-at-a-time. The minimal multi-file path lands here:

- **Multiple files in one call:** `/documents/upload` accepts a list of files; each is processed through the **existing** single-file path (extract text → `/workspace/uploads/{slug}.md` via authored substrate). Same 25MB-per-file cap, same allowed types (PDF/DOCX/TXT/MD), same attributed write. No new persistence.
- **Single archive (`.zip`):** accepted and expanded server-side to per-file uploads through the same path, each entry capped at 25MB. Archive itself is not retained as a blob — it's a transport envelope, expanded and discarded.
- **What this is NOT:** not a new bulk-ingestion subsystem, not a background job, not a progress table. It's the existing upload path called N times in one request. If any file fails (oversize, unsupported), it's reported per-file; the batch is not transactional (partial success is fine and surfaced).

*(Scope boundary: drive/cloud-storage connectors — pulling from Google Drive, Dropbox — are NOT in this ADR. Those are Mode-A read connectors, bundle-side follow-ons. D5 is strictly the local multi-file/archive push.)*

---

## 7. D6 — Home/Files boundaries (restated, not reimplemented)

- **Home** (ADR-312): the empty-state CTA (`UnactivatedHomeCTA` in `web/components/library/HomeRenderer.tsx`, currently `href="/program"`) **repoints to `/setup`**. The home still only *points* to setup; the constitution-band CTA is the onboarding/activation entry that hands off to the guided sequence. Home never grows setup chrome.
- **Files** (ADR-329): stays the raw substrate surface (L1 — the escape hatch). Harvest *writes* files; Files *displays* them. `/setup` never colonizes Files, and Files never grows setup affordances.

The boundary discipline: `/setup` is the *ordered* presentation, Home is the *operation rendered*, Files is the *raw substrate*. Three renderings, one substrate, no overlap.

---

## 8. What this ADR explicitly does NOT do

- Does not store wizard/setup/coverage/progress state (derivation over substrate only).
- Does not build a harvest subsystem, manager, or coverage table (invocation only).
- Does not add a new primitive or permission mode for harvest (existing read tools + `WriteFile`).
- Does not revive continuous sync (ADR-153 stands).
- Does not add drive/cloud-storage connectors (Mode-A bundle-side follow-ons).
- Does not persist scope selection or harvest plans (the v1 picker's selection is ephemeral component state — the substrate records what got brought in, never a scope target).
- Does not touch flow 3 (outcomes in) — that's [ADR-330](ADR-330-ground-truth-intake.md).
- Does not absorb the perception field (flow 1, world-present — watch declarations, signal substrate, generic cadenced web/RSS transport). That is arc 3, a future ADR per the four-flow capture §2/§4.

---

## 9. Render-service parity

- `/setup` is a **frontend** surface reading the existing `/api/workspace/state` endpoint — no new backend route, no env var, no scheduler change.
- The harvest invocation runs through the existing addressed-invocation path on the **API** (fired from the picker's confirm, or from chat — same addressed-invocation entrypoint). It uses existing read tools (capability-gated) + `WriteFile`. The dry-run estimate is a metadata-only read on the same API path (no writes). No new Render service touch beyond the API already serving invocations.
- Multi-file upload (D5) extends the existing `/documents/upload` route on the **API** — no new service, no new secret.
- **No env-var changes; all four Render services unaffected.**

---

## 10. Phased implementation

1. **Phase 1 — `/setup` surface (D1, D2). ✅ Implemented 2026-06-10.** Registered `setup` in `KERNEL_SURFACES` (archetype `sequence`, register `os-config`, `substrate_paths: []`, summon-only); added `sequence` to the Python `ARCHETYPES` tuple + the TS `Archetype` union (drift-gate parity); built `SetupSequence` (the Sequence renderer over `api.workspace.getState()` — five derived steps, every status computed from substrate, zero stored progress) + the `/setup` route page (`SurfacePage` wrapper); repointed the first-run redirect (`auth/callback` → `/setup?first_run=1`) + the Home empty-state CTA (`HomeRenderer` → `/setup`, "Get set up"); registered the `rocket` icon; added `/setup` to `PROTECTED_PREFIXES`. Steps 1–3 (pick program · author constitution · connect platforms) fully derived + actioned via existing affordances; steps 4–5 (bring in reality · first artifact) render with Phase-1-honest derivation (uploads-presence; Home pointer) — step 4's action gains the harvest scope picker in Phase 2 without changing the surface shape. Pure FE + one registry entry.
2. **Phase 2 — harvest invocation + scope picker (D3, D4). ✅ Implemented 2026-06-10.** Resolved the §4 "Phase decision" as a **harvest-shaped headless invocation** (NOT a dedicated agent identity, NOT the Reviewer judgment seat) — operator decision: harvest is a button action, not a system actor. `api/services/harvest.py` reuses the DispatchSpecialist headless machinery (`get_headless_tools_for_agent` + `chat_completion_with_tools` bounded loop) with a harvest-shaped curation prompt, the scoped platform read tools + `WriteFile`, attributed `agent:harvest` (via a `HeadlessAuth.caller_identity` that flows to `WriteFile`'s `authored_by`, ADR-288 D1). `POST /api/harvest/dry-run` (metadata-only: existing list tools for counts + coarse source→domain hint, NO writes/LLM) + `POST /api/harvest/run` (the curated invocation) in `api/routes/harvest.py`, mounted at `/api/harvest/*`. FE: `api.harvest.{dryRun,run}` + `HarvestSource` type (client.ts) + `HarvestPicker.tsx` (connected-provider toggles + range selector + live dry-run estimate + confirm-to-fire), wired into `SetupSequence` step 4's action. **Operator decision: LLM-curated, not deterministic dump** — the harvest reads, curates (drops noise), routes each piece to the right context domain, summarizes; "curated, not hoarded" per §123. **v1 scope is provider-level** (Slack/Notion/GitHub + range), not per-container — per-container granularity is open question #1. Selection state ephemeral (picker component state → request body, never persisted). CHANGELOG `[2026.06.10.2]`.
3. **Phase 3 — multi-file upload (D5).** Extend `/documents/upload` to accept a file list + `.zip` expansion; FE multi-select on the upload affordance.

Each phase lands green. Regression gate `api/test_adr331_setup_rendering.py` covers: (a) `setup` present in `KERNEL_SURFACES` with `archetype="sequence"` + `register="os-config"`; (b) no stored-state assertion (the surface owns no substrate path — `substrate_paths == []`); (c) `agent:harvest` validates against `is_valid_author`; (d) multi-file upload writes N attributed `/workspace/uploads/*.md` rows from one call. *(Phase 1 lands assertions (a)+(b)+the sequence-archetype Python/TS parity + redirect/CTA/icon/protected-route + (c); the dry-run-no-writes and (d) multi-file assertions extend in place per phase, per ADR-287 conformance-gate discipline.)*

**WORKSPACE doc cascade — deferred (Phase 1 note).** `docs/design/WORKSPACE.md` carries the per-surface contracts but is mid-refactor by a concurrent ADR-297/312 lane and explicitly defers known framing drift ("tracked as follow-up, not silently rewritten here"). Adding the `/setup` surface contract there now would conflict with that lane and violate its own deferral discipline. The authoritative `/setup` inventory is `api/services/kernel_surfaces.py` (updated) + this ADR; the WORKSPACE.md surface-contract entry for `/setup` lands with the doc's next coherence pass (tracked alongside the existing deferred drift), not piecemeal here.

**Prompt-change protocol:** Phase 2 adds/changes a harvest-shaped LLM-facing prompt — `api/prompts/CHANGELOG.md` entry required in that commit.

---

## 11. Open questions (carried, not resolved)

1. **Dry-run estimate fidelity** — how precise must the picker's "~N pages → these domains" estimate be (exact counts vs order-of-magnitude), and how does it map sources to target context domains before the harvest runs? (v1: metadata-only counts + a coarse source→domain mapping; refine if operators find the estimate misleading — §5.)
2. **Drive/cloud-storage harvest connectors** — Google Drive / Dropbox as Mode-A read connectors. (Out of scope; bundle-side follow-on ADRs — §6.)
3. **Bare-kernel default program** — ~~carried open~~ **RESOLVED post-pause** (2026-06-10) by [`four-flow-completeness-and-program-floor-2026-06-10.md`](../analysis/four-flow-completeness-and-program-floor-2026-06-10.md) §3: no default program (Direction A reaffirmed — a program IS a flow-declaration set; a default would be declarations with no operation behind them). The `/setup` "pick program" step renders the active-program cards + the honest bare-workspace secondary card, no default preselection. Mirror resolution in [ADR-330](ADR-330-ground-truth-intake.md) §11.
4. **Sequence-archetype reuse** — is `/setup` the only Sequence surface, or does the archetype earn its catalog slot via future guided flows (program-switch migration, deactivation wind-down)? (Designed for one; generalizes cheaply if a second appears.)
