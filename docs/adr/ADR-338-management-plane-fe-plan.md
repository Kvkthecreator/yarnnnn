# ADR-338 Companion — Management-Plane FE Audit, IA Decision, and Implementation Plan

**Status:** Working plan (2026-06-11). Companion to [ADR-338](ADR-338-management-plane.md). Not a new ADR — the implementation-session scoping doc the ADR-338 carry-over prompt asked for.
**Hat:** A (system canon).
**Live validation bed:** `anr-scout` workspace (`89f467f1-3ff9-4877-a898-ff5599ab4b08`) — real `_sources.yaml`, `_autonomy.yaml`, queue history. Every pane renders real substrate, never fixtures.

---

## Part 1 — FE Management-Surface Audit (receipts)

Inventory against ADR-338 D4 across Settings, /queue, Files, /setup, Home, and the atomic pages /autonomy /budget /principles. Each row: state · receipts · consent-line classification · current input modality.

### D4.1 — Sources/watch editor — **MISSING**

The standing watch (ADR-336) has no operator surface at all.

- No content-shape parser. `web/lib/content-shapes/index.ts:54-65` registers 10 shapes; **no `sources`**.
- No component. No `SourcesPane`/`SourcesEditor`/`WatchPane` anywhere in `web/components/`.
- No read-side API. No `GET /api/sources` or `/api/watch` in `api/routes/`. (`/integrations/{provider}/sources` is OAuth-source selection, unrelated.)
- No path constant. `api/services/workspace_paths.py` has no `SOURCES_*` — paths arrive as directive kwargs to the primitive.
- Substrate is real and parseable: `api/services/primitives/track_web_sources.py:169-202` (`_read_sources` — `yaml.safe_load`, source schema `{id, url, attestation?, max_entries?}`, cap 12). Reference template `docs/programs/alpha-author/reference-workspace/operation/authored/_sources.yaml`. Distilled observations land at `_watch_signal.yaml` (the Check-7 declared-vs-observed health source — `track_web_sources.py:282-318` writes per-source `{status: ok|error, observed_at, entries}`).
- **Consent line:** ABOVE (declaring a watch source changes *what the operation perceives* — DP12). **Modality today:** none — editable only by hand-editing YAML in Files, or via chat. This is the exact harness-dependency ADR-338's trigger names.

### D4.2 — Delegation dial (`_autonomy.yaml`) — **PARTIAL** (the schema-completion target)

The dial exists and is good; `never_auto` is the structural hole.

- Parser + dial L3 exist: `web/lib/content-shapes/autonomy.ts` (parse extracts `delegation` — correct field, `level` retired — + `ceiling_cents` + `domains` + `paused_until`/`pause_reason`); canonical L3 `web/components/workspace-concepts/AutonomyCard.tsx`, mounted `web/app/(authenticated)/autonomy/page.tsx`. `/delegation` is a redirect stub → `/autonomy`.
- **Gap 1 — `never_auto` is opaque.** `autonomy.ts:256-263` serialize() preserves `never_auto` as *verbatim body text* and parse() never extracts it. Backend treats it as a **structured list under `default:`** — `_validate_autonomy_block` keeps it (`review_policy.py:108-140`, `result = dict(block)` preserves non-validated keys), `_check_never_auto` enforces it as path-glob + action-type patterns (`review_policy.py:267-303`). So an operator-or-bundle `never_auto` list is enforced by the kernel but **invisible and uneditable** in the dial. This is precisely the schema-inert-edit + duplicate-key-shadow failure class (the alpha-author bundle ships a trailing `never_auto: []` that duplicate-key-shadows operator lists — project memory).
- **Gap 2 — bounded's substrate-inertness not surfaced.** AutonomyCard's "bounded" consequence text describes capital ceilings only; it does not say *manual AND bounded both queue substrate writes; only autonomous auto-applies* (the schema-inert correction — project memory; `review_policy.should_auto_apply`).
- **Gap 3 — pause control hookless in UI.** `setPause`/`clearPause` exist in `useAutonomy` but no AutonomyCard affordance.
- **Consent line:** ABOVE (graduating delegation changes *what the operation may do*). **Modality:** delegation = direct-manipulation (dial + confirm); ceiling/never_auto/pause = chat-only.

### D4.3 — Queue diff previews (ADR-307) — **PARTIAL** (the page is a stub; the card is done)

- Card is family-shaped and renders the diff: `web/components/tp/ProposalCard.tsx` dispatches on `family: 'capital'|'substrate'` (`:39,67,109,423`), normalizes ADR-307 `decision_context` (`:57-85`), renders inline before/after `SubstrateDiff` (`:168-187`) with new-file handling (`:175-180`). Approval modal shows the diff before Approve/Reject (`:342-509`).
- **Gap 1 — `/queue` is a stub.** `web/app/(authenticated)/queue/page.tsx` (42 lines) is a placeholder card pointing to `/feed` (`:4-11`). No dedicated browse/batch surface, despite the kernel registering `queue` as a Queue-archetype application surface (`kernel_surfaces.py:366-376`).
- **Gap 2 — NULL/empty-diff path is silent.** `SubstrateDiff` does `if (!diff) return null` (`ProposalCard.tsx:169`). A NULL-content WriteFile proposal (the real journey finding — project memory: seat emitted WriteFile with NULL content, approved blind, executed as empty write) renders *nothing* at approval time instead of a visible "this writes empty content" warning. The fail-fast guard landed server-side (`dce79580`), but the approval-time *visibility* is the management-surface half ADR-338 D4.3 asks for.
- Backend ready: `api/routes/proposals.py:118-273` (`GET /proposals`, approve/reject). `action_proposals` carries `family` + `decision_context` (`propose_action.py:194-254`).
- **Consent line:** ABOVE (approving binds the operation's action). **Modality:** approval = direct-manipulation; creation = agent-proposed.

### D4.4 — Budget/runway pane (`_budget.yaml`) — **PARTIAL** (runway framing missing)

- Pane exists: `web/lib/content-shapes/budget.ts` (parse + serialize for `amount_usd`, `window`, `per_wake_ceiling_usd`, `min_interval`); canonical L3 `web/components/workspace-concepts/BudgetCard.tsx`, mounted `/budget`. Vitals chip `BudgetStatusItem`.
- Backend `GET /api/budget` (`api/routes/budget.py:48-80`) returns `{amount_usd, window, window_spend_usd, remaining_usd, per_wake_ceiling_usd, queue_depth}` — declared envelope + window-to-date spend + queue depth. Live.
- **Gap — no runway.** ADR-338 D4.4 asks for "balance + burn → time remaining." Card shows remaining dollars but no burn-rate → days-left. The response has spend-to-date but no rate; runway is uncomputable FE-side without a burn metric.
- **Consent line:** ABOVE (setting budget changes *how much the operation may spend*). **Modality:** window = direct-manipulation; amount = chat.

### D4.5 — Installer-shaped program management — **PARTIAL** (no pre-activation four-flow preview)

- `WorkspaceSection.tsx` (Settings) + `SetupSequence.tsx` (`/setup`, ADR-331) + `/program` all show program title/tagline/phase + activate/deactivate. None surfaces the bundle's **four-flow declaration before activation** (what the program perceives / produces / attests / loops — the "what this app needs" installer panel).
- `api.workspace.getState()` (`api/routes/workspace.py`) returns `available_programs[].{slug,title,tagline,current_phase,deferred}` + `capability_gaps[]` — but **no `substrate_abi`/`watches`/flows**. The four-flow declaration lives in `MANIFEST.yaml` (`substrate_abi.{ground_truth,watches,flows_na,...}`, `capabilities[]`, `oracle`) but is read at fork time, not exposed for preview.
- **Consent line:** ABOVE (activating a program changes *everything the operation does*). **Modality:** activate = direct-manipulation; preview = missing.

### D4.6 — ADR-245 P4 originals — **PARTIAL**

- **Autonomy toggle** — shipped (D4.2 above).
- **Principles thresholds** — `web/lib/content-shapes/principles.ts` parses `auto_approve_below_cents` (read-only, **no serialize()**); `PrinciplesCard` displays read-only + routes all edits to chat. `high_impact_threshold_cents` is backend-validated (`review_policy.py:143-165`) but **never extracted or displayed FE-side**.
- **Risk envelope** — referenced in ADR-245 but absent from both backend `load_principles()` and FE. No `risk_envelope` field. (Out of scope this session unless a substrate consumer exists — none does.)
- **Consent line:** ABOVE (thresholds change *what auto-approves*). **Modality:** chat-only.

### Consent-line violations flagged (both directions)

- **Invisible-above-the-line** (the dangerous direction): `never_auto` (kernel-enforced, FE-invisible — D4.2 Gap 1); NULL-diff proposals (approved blind — D4.3 Gap 2); watch sources (perception-granting, no surface — D4.1). These are the failure classes ADR-338 exists to eliminate.
- **No ceremony-below-the-line violations found.** The fork, fetch, distillation, mirrors stay invisible (correct).

---

## Part 2 — IA Decision (Phase 1.5)

**Decision: candidate (a), enacted lightly — the management plane coheres on the `os-config` register, which already exists. We do NOT build a sixth scattered pane, and we do NOT build a new "settings shell" container.**

The prompt's worry ("without an IA decision this session ships a sixth scattered pane") resolves by recognizing that the cohesion artifact **already shipped** across ADR-297 + ADR-312:

1. **The `register` field IS the management-plane grouping.** `kernel_surfaces.py:116-137` + `web/lib/compositor/types.ts:262` define `SurfaceRegister = 'intent' | 'os-config' | 'application'`. Every governance dial is already `register: os-config` (autonomy, pace, program, settings, connectors, setup). The constitution is `register: intent`. This is the operator-ratified vocabulary ADR-338 D2 points at ("System Settings panes").
2. **The index already exists — twice.** The `intent` register surfaces as Home's Constitution band (slot #1). The `os-config` register surfaces as the **menu-bar vitals cluster** (`SystemStatusCluster.tsx` — Autonomy · Budget · Balance · Connections, read-only popovers footer-linking to each atomic surface). That *is* the macOS Control Center / System Settings index. There is no missing container.

**Therefore the IA work is two small moves, not a new surface:**

- **Move A — make `register` a visible grouping dimension in the Launcher.** Today `Launcher.tsx:49-85` groups only by `tier` (Workspace/Program/Custom). Within the kernel tier, split the flat "Workspace" list into the three registers (**Constitution** · **System Settings** · **Applications**) so the operator sees the management plane cohere when they open the full index. This is the one structural IA change — it makes the existing `register` data legible without inventing a surface. Low-risk, additive, reversible.
- **Move B — file the two missing panes into their correct register.** The new Sources pane → `register: os-config` (it's a driver/transport binding — ADR-338 D2 "Drivers" row). The installer-preview is an *extension of the existing `program` os-config surface*, not a new surface.

**Empty/first-run states:**
- Sources pane empty (`sources: []`) → honest "No standing watch declared — uploads + websearch remain your context-in" (mirrors the substrate prompt). Add-source CTA.
- Queue empty → existing self-hiding glance + "Nothing awaiting your decision."
- Program pre-activation → the installer four-flow preview IS the first-run state (replaces today's bare title/tagline).
- Vitals cluster on a bare kernel → chips render kernel defaults ($50/monthly budget, manual autonomy, 0 connections) — already handled.

**What this decision explicitly rejects:** a `/os-config` index page (the register is a data-plane grouping, not a URL — `kernel_surfaces.py` has no such surface and `/system` already redirects to `/settings`); a Settings "Workspace" tab (deleted ADR-215 R3); any container that re-scatters the atomic surfaces ADR-297 deliberately windowed.

---

## Part 3 — Implementation Plan (sequenced by trust leverage)

Each item: ADR-245 discipline (L2 in `content-shapes/`, exactly one canonical L3, write through declared contract) + **interaction contract** (direct-manipulation / chat→agent→queue-diff / agent-proposed). Governing rule: operators never hand-type YAML — structured fields for machine-parsed substrate; prose only where the consumer is an LLM; raw editing stays in Files (L1 escape hatch). Gates per ADR-236 Rule 3 (python regression scripts).

**Sequence rationale (trust leverage, corrected against audit):**

1. **`never_auto` schema completion (D4.2 Gap 1)** — *highest leverage, smallest change.* Closes a kernel-enforced-but-FE-invisible consent hole AND the duplicate-key-shadow failure class. Pure L2 work: `autonomy.ts` parse() extracts `never_auto` (+ `ceiling_categories`) from the `default:` block; serialize() re-emits structurally (deletes the opaque-body path). AutonomyCard gains a never_auto list editor + the bounded-is-inert consequence text (D4.2 Gap 2). **Contract:** direct-manipulation (structured list add/remove + dial), write via existing `writeShape()` → `WriteFile(scope=workspace)`. Confirmation modal on delegation widening (existing). Gate: `api/test_adr338_never_auto.py` (round-trip + duplicate-key-collapse + bounded-inert copy).

2. **Sources/watch editor (D4.1)** — *greenfield, highest operator-visible value (the journey's #1 harness act).* New L2 `content-shapes/sources.ts` (`SHAPE_KEY='sources'`, `PATH_GLOB='**/operation/authored/_sources.yaml'`, `WRITE_CONTRACT='configuration'`, parse/serialize for `sources[]`). New canonical L3 `SourcesCard` mounted on a new `register: os-config` kernel surface `sources` (route `/sources`, "Drivers" archetype = document). New read-side API `GET /api/sources` returning declared sources joined with `_watch_signal.yaml` per-source health (declared-vs-observed, Check-7 shape) — budget-route precedent. **Contract:** direct-manipulation for source rows (add/remove/edit url+attestation+max_entries — structured, cap-12-enforced); health column read-only (system-owned). Gate: `api/test_adr338_sources.py` (parse/serialize round-trip + cap enforcement + health join shape).

3. **Queue page de-stub + NULL-diff visibility (D4.3)** — *closes the approve-blind hole.* Replace the `/queue` stub with a real Queue-archetype browse surface: list `GET /proposals` grouped by family, each row rendering the existing `ProposalCard` family dispatch; batch is deferred (no demand yet — log the deferral). Fix `SubstrateDiff` NULL/empty path: instead of `return null`, render an explicit "⚠ writes empty content" / "no diff available" affordance so a NULL-content proposal is *visible* at approval. **Contract:** approval = direct-manipulation (existing approve/reject); creation unchanged (agent-proposed). Gate: `api/test_adr338_queue.py` (NULL-diff renders warning, not silence) — FE-shape assertion via component-contract test.

4. **Installer-preview on `/program` (D4.5)** — extend `api.workspace.getState()` (or a new `GET /api/programs/{slug}/preview`) to return the bundle's four-flow declaration (`substrate_abi.flows`/`flows_na` + `watches` + `capabilities` + `oracle`) for pre-activation display. WorkspaceSection / `/program` renders the "what this program will do" installer panel before the activate button. **Contract:** read-only preview; activate = direct-manipulation (existing). Gate: `api/test_adr338_installer_preview.py` (preview shape from MANIFEST, deferred bundle excluded).

5. **Budget runway (D4.4)** — extend `GET /api/budget` with a burn-rate (window_spend / elapsed-window-fraction → projected) so the card can frame "N days left." BudgetCard adds the runway line. **Contract:** read-only runway; envelope edits unchanged. Gate: extend budget test.

6. **Launcher register grouping (IA Move A)** — split kernel tier into Constitution / System Settings / Applications by `register`. **Contract:** navigation only. Gate: `api/test_adr338_launcher_registers.py` (FE grouping assertion) or fold into existing ADR-297 phase-1 gate.

7. **Principles thresholds editor (D4.6)** — surface `high_impact_threshold_cents` + add serialize() to `principles.ts`; PrinciplesCard gains a structured threshold editor. Risk-envelope deferred (no substrate consumer). **Contract:** direct-manipulation thresholds. Gate: principles round-trip.

**Items 1–3 are the trust core** (they each eliminate a named consent-line violation from the audit). 4–7 are completeness. Build in order; each green before the next.

---

## Part 4 — Build Log

- **Item 1 — never_auto schema completion** — **Implemented** (commit `916bdbc`). `autonomy.ts` parse() extracts `never_auto` (block-list + inline `[]`) from the `default:` block; serialize() emits it structurally exactly once (duplicate-key shadow eliminated). New `setNeverAuto` mutation + `NeverAutoEditor` (structured list, no YAML) + bounded-is-schema-inert copy. Gate `api/test_adr338_never_auto.py` 20/20 (behavioral round-trip via real TS). Contract: direct-manipulation, writeShape → WriteFile.
- **Item 2 — Sources/watch editor** — **Implemented** (commit `8fec36a`). New `GET /api/sources` (`api/routes/sources.py`) reads the active bundle's `substrate_abi.watches`, pairs declared `_sources.yaml` with observed `_watch_signal.yaml` per-source health (Check-7 shape) — kernel-agnostic, path from bundle not constant (ADR-224 boundary). New L2 `content-shapes/sources.ts` + canonical L3 `SourcesCard` + `/sources` kernel surface (register: os-config, sibling of Connectors — both transport/driver bindings). Validated against live anr-scout substrate (2 sources, both observed ok, 8 entries each). Gate `api/test_adr338_sources.py` 35/35. Contract: direct-manipulation source rows (add/remove/edit), observed health read-only.
- **Item 3 — Queue de-stub + NULL-diff visibility** — **Implemented**. `/queue` was a stub pointing to the Feed; it is now a real browse surface — pending proposals grouped by family (capital/substrate), each row opening the SINGULAR `ProposalDetail` modal via `useProposalModal` (shared with Feed/cockpit/briefing) so the diff + reviewer reasoning are visible before approval. `SubstrateDiff` fixed: absent diff → explicit "no diff available" warning (was silent `return null`); empty `after` → "writes empty content" warning (was a blank `<pre>` — the NULL-content WriteFile failure class approved blind in the journey week). Gate `api/test_adr338_queue.py` 13/13. tsc --noEmit clean. Contract: approval direct-manipulation; creation agent-proposed. Batch multi-select deferred (no demand — logged in source, not silently dropped).

**Trust core complete (Items 1–3).** All three consent-line violations the audit named in the invisible-above-the-line direction are closed: `never_auto` (kernel-enforced, was FE-invisible), NULL-content proposals (was approved blind), watch sources (perception-granting, had no surface). Items 4–7 are completeness.

- **Item 6 — Launcher register grouping (IA Move A)** — **Implemented**. `Launcher.tsx::groupSurfaces` splits the kernel tier (was one flat "Workspace" group) by `register` into three subtle groups: **Constitution** (intent) · **Applications** (application) · **System Settings** (os-config). This is the IA-decision payoff — the management plane *coheres as a plane* in the one place the operator sees the full surface index; the os-config register reads as the macOS System-Settings analog (ADR-338 D2). No new container; existing `register` data becomes a visible grouping dimension. Unregistered kernel surfaces default to Applications (no silent drop). Contract: navigation only.
- **Item 5 — Budget runway (D4.4)** — **Implemented**. `GET /api/budget` gains `daily_burn_usd` + `runway_days` (`services/budget.py::window_elapsed_days` + route math: burn = window_spend / days-elapsed; runway = remaining / burn; both null until there's spend signal, capped at 999d). `BudgetCard` renders a runway line ("~N days left at this pace · $X/day burn", tone-graded red/amber/muted). Closes the "balance + burn → time remaining" gap the audit flagged. Contract: read-only runway; envelope edits unchanged.
- Gates: `api/test_adr338_runway_launcher.py` 27/27. ADR-327 budget gates still green (runway fields additive). tsc --noEmit clean.

**Remaining (Items 4 + 7) — completeness, deferred or next session:** installer-shaped program preview (needs a backend `getState` extension to expose the bundle's four-flow declaration pre-activation); principles thresholds editor (`high_impact_threshold_cents` surfacing + `principles.ts` serialize()). Risk-envelope editor remains deferred — no substrate consumer exists (audit D4.6).
