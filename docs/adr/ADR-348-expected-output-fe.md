# ADR-348 — Expected Output, Operator-Facing: the contract pane in the one Settings door

**Status:** **Accepted + Implemented (2026-06-19)** — same session. Depends on ADR-347 (the one Settings door + the Contract group). Gate `api/test_adr348_expected_output_fe.py`. `tsc --noEmit` clean.
**Date:** 2026-06-19
**Deciders:** KVK (operator) + Claude (collaborator)
**Hat:** A (system canon)

> **Discourse base:** [operator-experience-for-wide-workspace-cases-2026-06-19.md](../analysis/operator-experience-for-wide-workspace-cases-2026-06-19.md) §1.2 (the gap), §5 (the editor-shape fork), §9 (the operator's pick: structured, program-declared) + [ADR-345](ADR-345-expected-output-contract.md) (the concept) + the [heartbeat discourse](../analysis/operation-heartbeat-and-autonomy-as-witness-2026-06-19.md).

**Extends:** ADR-345 (Expected Output gets its operator-facing surface — ADR-345 shipped the concept + the `_expected_output.yaml` referent + the wake-envelope wiring, backend-only; this ADR builds the FE the operator sees + sets), ADR-347 (lands the pane in the new Contract group), ADR-245 (a new L2 content-shape + L3 card).
**Preserves:** ADR-345 (a floor-gated delivery-cadence, NEVER a quota — the Goodhart guard is enforced in the pane copy), ADR-340 D1 (mirror discipline — one surface ↔ one substrate concern), the ADR-347 §3 editability rule (Expected Output is operator-authored governance-region → inline editor), ADR-320 (governance-region, Reviewer-reads-not-authors).

---

## 1. The gap ADR-345 left

ADR-345 named Expected Output as *"the measurable half of the mandate"* and shipped it **backend-only**:

- `governance/_expected_output.yaml` (the machine sidecar — `workspace_paths.py:90`).
- Wake-envelope wiring: `reviewer_envelope.py:102` → `ReviewerContext.expected_output_yaml` (`occupant_contract.py:151`) → persona-frame render (`reviewer_agent.py:682-686`).
- The standing-obligation check (DP30) reads-declared-then-derives against it.
- Both bundles ship worked instances (`alpha-author` kind=piece/event-driven; `alpha-trader` kind=trade/per-signal-when-fires).

**But the operator had no surface to declare, see, or tune it** — there was no `content-shapes/expected-output.ts`, no pane, no Home expression. Its only authoring path was chat → `WriteFile`. Three of the four operating-contract declarations (Rhythm/Witness/Persona) had homes; Expected Output was the homeless fourth — exactly the harness-dependency failure class ADR-338 D1 named. This ADR closes it.

## 2. Decision

### D1 — A content-shape + an operator pane in the Contract group

- **`web/lib/content-shapes/expected-output.ts`** — a new L2 content-shape mirroring `budget.ts`/`autonomy.ts`: `SHAPE_KEY='expected-output'`, `PATH_GLOB='**/governance/_expected_output.yaml'`, `WRITE_CONTRACT='configuration'`, `CANONICAL_L3='ExpectedOutputCard'`. Parses the `expected_output:` block (`kind` · `delivery_cadence` · `bar` · optional `rough_volume_per_window`), round-trips the tier frontmatter + comments, and exposes `useExpectedOutput({ initialContent })` with a `setContract()` mutator that routes through `writeShape('expected-output', 'governance/_expected_output.yaml', …)`. Registered in `content-shapes/index.ts`.
- **`web/components/workspace-concepts/ExpectedOutputCard.tsx`** (`variant="full"`) — the L3 card, mounted in the ADR-347 **Contract** group of the one Settings door (alongside Budget + Autonomy).

### D2 — The headline is the READ; the editor is below it

Per the discourse (§7), the pane's load-bearing value is making the **standing-obligation check visible** — *owed vs produced* — not the editor. The card leads with the declared contract in plain words ("Owes: a piece, when a draft clears the bar") and (when the data is cheaply available) a quiet support line. The structured editor sits below the headline.

### D3 — A generic, kind-agnostic structured editor (the kernel-fallback form; Shape 2's default)

The operator picked **Shape 2 (structured, program-declared)** in the discourse. Shape 2 *subsumes* Shape 3 (generic form): the kernel ships the **generic three-field form** as the always-present fallback, and a per-program `expected_output.form` compositor override is the **named follow-on** (OQ1) for when a program needs a field the generic three don't cover. The bundles' shipped YAML uses exactly the generic three (`kind`/`delivery_cadence`/`bar`), so the generic form is sufficient for both worked instances **today** — building the per-program override slot now would be speculative (no program needs it yet), violating Singular Implementation's "one way, no parallel paths until demand." The generic form:

- **kind** — free text (the artifact: "piece", "trade", "campaign", "shortlist").
- **delivery_cadence** — the declared cadences plus free entry: `event-driven` · `per-signal-when-fires` · `daily` · `weekly` · `biweekly` · `monthly` · `on-demand`. **Labeled as a floor-gated cadence**, with the ADR-345 copy ("the slot slips if nothing clears the bar — never a quota") at the control.
- **bar** — free text or a pointer to where the floor lives (`principles.md` / `_risk.md`).

The **"zero is correct" / floor-gated-not-quota guard** (ADR-345) is enforced in the pane copy: an event/per-signal cadence reads "produces when the trigger fires; zero when it doesn't is on-contract," so the form *cannot* render as a body-count target.

### D4 — Reviewer-reads-not-authors (governance discipline preserved)

Expected Output is governance-region: the operator authors it, the Reviewer reads it (ADR-345 / ADR-320). The pane is an **operator** editor (ADR-347 §3 operator-authored → inline). The prose companion (`MANDATE ## Expected Output`) stays edit-via-chat in the Constitution group — the two are kept in agreement by the operator, exactly as `_autonomy.yaml`/`AUTONOMY.md` are.

## 3. What this does NOT do

- Does not build the per-program `expected_output.form` compositor slot (OQ1 — named follow-on; the generic form serves both bundles today).
- Does not turn the cadence into a quota (ADR-345 Goodhart guard, enforced in copy).
- Does not make the Reviewer author `_expected_output.yaml` (governance — operator-only, ADR-345/ADR-320).
- Does not add a Home slot for Expected Output (the ADR-346 Operation surface §7 heartbeat band is the composition home; this ADR builds the mirror it reads from).
- Does not duplicate the bundle YAML — the shipped `_expected_output.yaml` instances are the data; this ADR builds the parser/editor over them.

## 4. Implementation

- `web/lib/content-shapes/expected-output.ts` (NEW) — parser/serializer/`useExpectedOutput` hook.
- `web/lib/content-shapes/index.ts` — register the shape.
- `web/components/workspace-concepts/ExpectedOutputCard.tsx` (NEW) — the L3 card.
- `web/app/(authenticated)/workspace-settings/page.tsx` — mount `ExpectedOutputCard` in the Contract group (ADR-347 D1).
- `api/services/kernel_surfaces.py` — add the `expected-output` pane-grade surface (`pane_of: "workspace-settings"`, `pane_group: "Contract"`, `register: os-config`, `route: /expected-output`, `launcher_tier: search-only`).
- `web/types/desk.ts` — add `'expected-output'` to `KernelSurfaceSlug` + `KERNEL_SURFACE_SLUGS`.
- `web/components/shell/SurfaceRegistry.tsx` — no new page component (it's a pane; the door's renderPane handles it) — verify the pane-resolution path.
- `api/test_adr348_expected_output_fe.py` — regression gate.

## 5. Open questions (carried)

1. **Per-program `expected_output.form` compositor slot** — when a program needs a contract field the generic three don't cover, declare the form shape in `SURFACES.yaml` (the Home-slot mechanism). Named follow-on; not built (no demand yet).
2. **The owed-vs-produced support line fidelity** — D2's quiet support line ("N produced this window") needs a cheap read of recent fires/outputs against the cadence. v1 may ship the headline declaration only and add the produced-count when the read is cheap (the ADR-346 Operation surface is the richer home for that comparison).

**Dimensional classification:** **Channel** (Axiom 6) projected through **Purpose** (Axiom 3 — the operator declaring what the operation owes). Builds the FE half of ADR-345's GLOSSARY v2.8 Expected-Output concept.
