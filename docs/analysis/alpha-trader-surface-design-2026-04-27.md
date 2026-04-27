---
title: alpha-trader Surface Design — Paper-Design Discourse
date: 2026-04-27
status: discourse / paper design (not a canonical spec)
trigger: post-OS-framing discourse (2026-04-27) — Q2 of three-question round on compose dispatcher, surface design venue, and reflexive-loop sequencing
related:
  - docs/adr/ADR-222-agent-native-operating-system-framing.md
  - docs/adr/ADR-223-program-bundle-specification.md
  - docs/programs/alpha-trader/README.md
  - docs/architecture/os-framing-implementation-roadmap.md
  - docs/analysis/external-oracle-thesis-2026-04-26.md
---

# alpha-trader Surface Design — Paper-Design Discourse

## What this is

A paper-design exploration of alpha-trader's cockpit surfaces. **Not a SURFACES.yaml spec.** Not an ADR. A discourse artifact in the same shape as `external-oracle-thesis-2026-04-26.md` — exploratory, structured, surfaces open questions rather than burying them.

Same role that `alpha-prediction/README.md` and `alpha-defi/README.md` reference SPECs serve: a **forcing function** that informs the implementation ADRs (Compositor + System Component Library + Surface Compose) before code lands. Designing surfaces on paper catches over-engineering and under-engineering early.

## Why now

Per the post-OS-framing discourse (2026-04-27, Q2 + Q3):

> "alpha-trader's specific surfaces get designed when we write the alpha-trader bundle's SURFACES.yaml, which depends on (1) ADR-223 [landed], (2) the compositor build, (3) the system component library being formalized." [...] "the alpha-trader cockpit design happens *now* (as a SPEC exercise), informs the compositor ADR (ADR 2), and the system component library ADR (ADR 3). It's not deferred to 'after compositor is built' — it's a forcing function for those ADRs."

Designing on paper *before* the compositor build forces concreteness about:
- Which components must exist in the universal library (informs ADR 3)
- Which substrate paths surfaces actually read (informs ADR 2's binding model)
- What empty states look like (informs ADR 5's activation flow)
- What's program-specific vs universal (informs ADR 4's kernel/program boundary)

If reference-program SURFACES sketches can be drawn without changing the compositor, the compositor is correctly general. If they reveal compositor gaps, ADR 2 gets refined before code.

## Key framing — two compose modes (from Q1)

Before walking the tabs, the architectural distinction this design honors:

| Mode | Produces | Lifetime | Examples in alpha-trader |
|---|---|---|---|
| **Document compose** | Frozen HTML artifacts (`output.html`, PDFs) — emailable, archived | Per-run, immutable once composed | Daily-update email body, weekly performance review PDF, exported portfolio brief |
| **Surface compose** | Live cockpit panes — re-rendered per load, bound to current substrate | Per-render, always current | Overview's live P&L band, Work tab's queue of pending proposals, Agents tab's current Reviewer health |

Both share the universal component library. A `MetricCardRow` works in surface compose (live binding) and document compose (frozen snapshot). The mode is a property of the *binding* in the SURFACES manifest, not the component itself.

For each tab below, surface compose entries are the default unless explicitly noted as document compose embeds.

---

## Tab-by-tab paper design

The cockpit's four tabs (Chat / Work / Agents / Files per ADR-214) plus the Review surface absorbed into Agents. For each, the design hypothesis + the open questions.

### Overview (HOME) — `/chat` route, but surface-compose-rendered

Per ADR-205 F1, `/chat` is the home surface — the operator lands here. Under the OS framing this surface gets program-specific composition.

**Design hypothesis — three bands:**

1. **Performance band (top, surface compose)** — operator's current capital-truth state, read live from `/workspace/context/portfolio/_performance.md` frontmatter.
   - Components: `MetricCardRow` × 4 (30d P&L, win rate, current drawdown, Sharpe rolling)
   - Bindings: live frontmatter reads
   - Empty state: "No trades yet — your reference workspace shows the metrics you'll track once trading starts." Pointer to MANDATE.md.

2. **Daily discipline band (middle, surface compose embedding document compose)** — today's daily-update output rendered as an embedded document.
   - Components: `TaskOutputViewer` (embeds frozen `output.html`)
   - Bindings: latest run of `daily-update` task
   - Empty state: deterministic empty-state template from ADR-161 (no LLM cost; "Your workforce is here, tell me what matters")

3. **Awareness band (bottom, surface compose)** — narrative rail (ADR-219), pending proposals queue if any, reviewer alerts.
   - Components: `NarrativeRail` (existing concept, ADR-219), `QueueCard` for proposals, `AlertCard` for reviewer flags
   - Bindings: narrative substrate + `action_proposals` table + `_workspace/review/decisions.md` recent entries

**Open questions:**
- Is the Performance band always-visible, or does it collapse when no positions are open (e.g., weekend, between trades)?
- Does the daily-discipline band render today's run before market open (predictive) or only the run that already executed (retrospective)?
- The awareness band's narrative rail — same component as the persistent rail across all surfaces, or different? Probably same; the SURFACES manifest just declares its layout slot.

### Work — `/work` route

Task list (list mode) + task detail (detail mode), per ADR-167 v2. Under OS framing, alpha-trader-specific overlays apply at task-detail level when output_kind is `external_action` (proposed orders).

**Design hypothesis — list mode (default):**

- Standard task list with filters (per ADR-167 v2: output_kind, agent, status, schedule)
- alpha-trader overlay: pre-filter chip "Trading proposals" lights up when any task has pending `external_action`
- Pre-pinned tasks: `daily-discipline-checklist`, `signal-monitor`, `position-tracker` (whatever the operator's lived workflow names them)
- Components: `TaskList` (universal), `FilterChipRow` (universal), pre-pin convention from SURFACES manifest

**Design hypothesis — task detail (overlay-driven):**

- Default detail: the four kind-specific middles (Deliverable / Tracking / Action / Maintenance per ADR-167 v2 + ADR-178)
- alpha-trader overlay on `external_action` tasks: replace the generic ActionMiddle with `SignalAttributionReview` — proposal envelope showing named signal, sized stop, expectancy, entry rules, alongside approve/reject buttons
- Components: `SignalAttributionReview` (program-specific component? Or could it generalize to any external_action with attribution?)

**Open questions — load-bearing for ADR 3 (Component Library):**
- Is `SignalAttributionReview` a program-specific component (lives in alpha-trader bundle? But components don't live in bundles — they're universal) or a universal `AttributedActionReview` that any program can use? The design pull is to universalize: alpha-prediction's "Yes/No proposal with Kelly-sizing reasoning" has the same shape; alpha-defi's "swap proposal with slippage-tolerance reasoning" has the same shape. Universal `AttributedActionReview` with binding-driven content is probably right.
- Does the universal component need a binding for "what fields to surface for attribution" (signal name, sized stop, expectancy) so each program declares its own attribution schema? Yes — and this is exactly the kind of insight paper design surfaces.

### Agents — `/agents` route

Roster (list mode) + agent detail (detail mode). Per ADR-214, includes Reviewer as a systemic-agents pseudo-row + universal six + thinking_partner.

**Design hypothesis — roster (list mode):**

- Standard agent list grouped by class
- alpha-trader overlay: Reviewer card surfaces capital-EV stance — "Last 7d: 12 approved, 3 rejected, 1 deferred. Calibration drift: low."
- Components: `AgentRoster` (universal), `ReviewerHealthCard` (with capital-EV bindings)

**Design hypothesis — agent detail:**

- Standard agent detail per ADR-167 v2 + ADR-214
- alpha-trader overlay on Reviewer detail: principles editor surfaces capital-EV-aware sections (stop-distance enforcement, signal expectancy decay, sector concentration, var budget) with templated placeholders from the bundle's reference principles
- Components: `PrincipleEditor` (universal), `ReviewerCalibrationView` (universal — reads `/workspace/review/decisions.md` + `_performance.md` to show how reviewer judgment is grading against outcomes)

**Open questions:**
- ReviewerCalibrationView is one of the most program-relevant components but its data flow is universal: read decisions, read outcomes, show alignment. Probably universal.
- Does alpha-trader's Reviewer get a *recommendation* surface — "AI Reviewer suggests these principle edits based on recent calibration data"? That ties into ADR-194 v2 Phase 4 (calibration tuning). Defer until that ADR is real.

### Files / Context — `/files` route

Workspace filesystem browser. Per ADR-180 the tab is "Files." Under OS framing, alpha-trader pre-pins program-relevant directories.

**Design hypothesis:**

- Standard workspace tree
- alpha-trader overlay: pre-pinned shortcuts to `/workspace/context/portfolio/`, `/workspace/context/trading/`, `/workspace/context/_shared/MANDATE.md`, `/workspace/review/principles.md`
- Quick-action affordances: "Show signals", "Show open positions", "Show today's _performance.md"
- Components: `FileTree` (universal), `PinnedShortcutRow` (universal — accepts a list of paths from SURFACES manifest)

**Open questions:**
- Should the file tree default-collapse to show pinned + working + memory, with full tree behind a "show all" toggle? Or always-full? Pinned + on-demand is probably the right default — keeps the pane scannable.
- Do quick-actions belong on Files tab, or on Overview? Probably both (Overview gets the pull; Files gets the discovery surface).

### Review — absorbed into Agents per ADR-214

Reviewer is a systemic-agents pseudo-row in `/agents`. ReviewerDetailView already absorbs principles + decisions + identity (per ADR-214 commit). Under OS framing, alpha-trader's ReviewerDetailView gets capital-EV-aware overlays as discussed in the Agents section above.

**No separate surface needed.** The OS framing reaffirms ADR-214 — Review is not its own destination.

---

## Cross-cutting components — what the system component library needs

Compiling components referenced above into the universal library set this design implies:

| Component | Universality | Binding shape |
|---|---|---|
| `MetricCardRow` | Universal | YAML frontmatter paths from a substrate file, label per metric |
| `TaskOutputViewer` | Universal | Task slug + run selector (latest / by-date) |
| `NarrativeRail` | Universal | Already implied by ADR-219 |
| `QueueCard` | Universal | `action_proposals` filter (by status, by task) |
| `AlertCard` | Universal | Substrate file with structured alerts (e.g., `_workspace/review/decisions.md` recent flagged entries) |
| `TaskList` | Universal | Filter + group spec from SURFACES manifest |
| `FilterChipRow` | Universal | Filter spec from SURFACES manifest |
| `AttributedActionReview` | Universal (probably) | Proposal envelope path + attribution schema declaration |
| `AgentRoster` | Universal | Agent class grouping spec |
| `ReviewerHealthCard` | Universal | Reads `decisions.md` + `_performance.md` |
| `PrincipleEditor` | Universal | Substrate file path (principles.md) |
| `ReviewerCalibrationView` | Universal | Reads decisions.md + outcomes substrate |
| `FileTree` | Universal | Workspace root path |
| `PinnedShortcutRow` | Universal | List of paths + labels from SURFACES manifest |

**The discipline this validates:** every component above is universal. Nothing in alpha-trader's design demands a program-specific component. That's exactly what FOUNDATIONS Principle 16 + ADR-222 commits to — adding a program is purely additive (new bundle, possibly new system component library entries, no kernel touch). Here the answer is "no new system components needed" — all reuse from the universal library.

If alpha-prediction or alpha-defi paper-designs reveal components NOT in this list, that's the signal to extend the library — but the *current* alpha-trader design is honest within the universal-library constraint.

---

## What this paper design forces, ADR by ADR

| Receiving ADR | What this design surfaces |
|---|---|
| **ADR 2 (Compositor Layer)** | Composition manifest must support: per-tab band layout, overlay-on-condition (e.g., overlay when task.output_kind = external_action), embedded document-compose artifacts, live-bound metric reads from substrate file frontmatter |
| **ADR 3 (System Component Library)** | The 14 components listed above must exist (most do, in some form) with documented binding contracts. Component contract must support: substrate-file-path bindings, frontmatter-path bindings, filter/group spec bindings, label declarations, layout-slot declarations |
| **ADR 4 (Kernel/Program Boundary Refactor)** | Confirms the boundary holds: every alpha-trader-specific surface need is a binding in SURFACES.yaml, not a kernel hook |
| **ADR 5 (Activation Flow)** | Empty states matter — the paper design names empty states for every surface, which means the activation flow's "fork the reference" must populate enough substrate that empty states render meaningfully (not generic placeholders) |
| **ADR 6 (Reflexive Loop)** | Confirms the loop's two graduation channels: substrate patterns (signal definitions, principles) AND composition patterns (e.g., kvk's authored layout overrides). Both flow through the same back-office task |

---

## Open questions worth third-eye review

Things this paper design does not resolve:

1. **AttributedActionReview generality.** Is it really one universal component with binding-driven content, or do programs have meaningfully different proposal-review affordances? alpha-prediction's "Kelly + resolution risk" vs alpha-trader's "signal + stop + expectancy" vs alpha-defi's "slippage + smart-contract-risk" might converge to one component or diverge. Test on paper-designs of the other two before committing.

2. **Predictive vs retrospective rendering on Overview.** Daily-discipline band — does it show today's intended discipline (a predictive forecast) or yesterday's outcome (retrospective summary)? Either is valid; the user's discipline (process > P&L) suggests retrospective.

3. **Reviewer recommendation surface.** Should the Reviewer detail surface a "suggested principle edits based on calibration drift" component? This would be ADR-194 v2 Phase 4 territory. Probably surface-able but gated on that ADR's progress.

4. **Embedded vs linked task outputs.** The design assumes the daily-discipline band on Overview *embeds* the daily-update output (iframe-style or markdown-rendered). Alternative: link to it, render in-pane only when clicked. Embedded is heavier but maps to "operator lands here, sees the day at a glance" — probably right.

5. **Pre-pinned shortcuts as user-customizable.** The Files-tab pinned shortcuts are SURFACES-declared by alpha-trader. Should the operator be able to override (add/remove pins) via workspace-overlay SURFACES? Almost certainly yes — but the override mechanism is ADR 2 territory.

---

## What this is NOT

- Not a SURFACES.yaml spec. The actual manifest writes after ADR 2 + ADR 3 land, when the binding format is precise.
- Not a commitment to specific components. Component names are illustrative; final names land in ADR 3.
- Not a full visual design. UI/UX work (spacing, color, typography, interaction patterns) is downstream.
- Not the only valid reading. This is one coherent design among several. Third-eye review is meant to push back on the strongest version.

---

## Recommendation

Treat this as the discourse anchor for ADR 2 + ADR 3 drafting. Specifically:

- **ADR 2 (Compositor Layer) author** should reference this doc when scoping the manifest format — every binding shape this design uses must be expressible in the manifest.
- **ADR 3 (System Component Library) author** should reference this doc when scoping the initial library set — the 14 components above are the v1 scope.
- **alpha-prediction + alpha-defi paper designs** should follow this doc's structure, as the next litmus check. If those designs reveal components or compose modes this design didn't surface, the system component library expands; if they don't, the design has converged.
- **Substantive component decisions** (especially `AttributedActionReview` generality) wait for the next round of operator-driven discourse.

This is a forcing function, not a final answer. It moves the OS framing from "we have a kernel + compositor + bundles" abstract to "here's what the cockpit actually looks like for our first program." That concrete grounding is what the next round of implementation needs.
