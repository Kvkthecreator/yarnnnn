# Surface Model — Atomic vs. Container (Parked Design Discussion)

> **Status:** Parked — design discussion, not ratified canon. Awaiting decision.
> **Authors:** KVK, Claude (drafted 2026-05-21)
> **Touches:** [ADR-244](../adr/ADR-244-workspace-settings-surface.md) · [ADR-266](../adr/ADR-266-workspace-surface-content-discipline.md) · [ADR-251](../adr/ADR-251-system-agent-reviewer-first-class-surfaces.md) · [ADR-214](../adr/ADR-214-agents-page-consolidation.md) · [ADR-243](../adr/ADR-243-schedule-surface.md)
> **Does not amend or supersede** anything yet — this is the parked-question doc that future ADR work cites.

---

## Why this doc exists

Three sessions of frontend work (ADR-244 → ADR-251 → ADR-266) iterated on a **page-as-container** model: one `/workspace` page holding four operator-authored governance concepts (Mandate, Delegation, Principles, Identity/Brand), with Reviewer-page tabs mirroring some of the same content. Each iteration tightened the model but left a recurring symptom: when a new concept needed surfacing (the prompt for this doc was *cadence*), the conversation re-opened the question *"which container does this go in?"* — Workspace page, Reviewer tab, Settings tab, or new top-level surface.

Operator (KVK, 2026-05-21) surfaced an alternative shape that the prior model can't accommodate cleanly: **each authored concept gets its own atomic surface, indexed by a dispatcher page** — inspired by Apple's Launchpad / Applications pattern where each app is self-contained and the chips-and-grid view is the index, not the container.

This doc parks the question with enough fidelity that the next ADR session can pick it up cold.

---

## The two models

### Model A — Page-as-container (status quo)

- `/workspace` renders four concept cards inline (Mandate, Delegation, Principles, Identity/Brand) per ADR-266.
- Program lifecycle collapses into a drawer at the bottom (ADR-266 D1).
- Reviewer page (`/agents?agent=reviewer`) carries five tabs (Identity · Principles · Capabilities · Autonomy · Activity per ADR-251 D4 expanded 2026-05-14). Two of those tabs (Principles, Autonomy) currently render the same `PrinciplesCard` / `DelegationCard` components used on `/workspace` — i.e. the same substrate is presented in two places.
- A new concept (cadence) has no natural container without amending one of the existing surfaces.

### Model B — Atomic surfaces + index dispatcher

- Each authored substrate concept gets its own page:
  - `/mandate` (renders `MANDATE.md`)
  - `/delegation` (renders `_autonomy.yaml`)
  - `/principles` (renders `principles.md` + `_principles.yaml`)
  - `/identity` and `/brand` (separately or jointly)
  - `/cadence` (renders `_recurrences.yaml` + `_hooks.yaml` + `standing_intent.md` + wake telemetry)
  - `/program` (program lifecycle — currently the drawer)
- `/workspace` becomes a thin **index dispatcher** — link-cards (not full-render cards) with one-line summaries (current state + last revision) deep-linking to the atomic surfaces.
- Reviewer page sheds governance content entirely → 3 tabs (Identity · Capabilities · Activity).
- New concepts (cadence, future ones) are additive — they get their own atomic surface, the index page lists them, no container amendments needed.

---

## Comparison

| Property | Model A (Container) | Model B (Atomic + Index) |
|---|---|---|
| Each concept has its own URL | No (deep-link via anchor only) | Yes |
| Adding a new concept | Amends container ADR | Adds atomic page + index entry |
| Substrate-to-surface mapping | N-to-1 (many files in one page) | 1-to-1 (one file class per page) |
| Discoverability ("where do I configure X?") | One URL answers it | Index page answers it |
| Visual tour ("show me everything") | Scroll one page | Index + deep-dive on demand |
| Surface duplication (Reviewer tabs vs Workspace) | Currently present | Structurally eliminated |
| User mental model | "Page about workspace setup" | "Each thing has its place" |
| Cost of getting placement wrong | High (re-shuffle ADRs) | Low (atomic; move one URL) |

---

## Arguments for Model B (atomic)

1. **Substrate atomicity is already canon.** Each authored concept already has its own file (`MANDATE.md`, `_autonomy.yaml`, `principles.md`, `IDENTITY.md`, `BRAND.md`, `_recurrences.yaml`, `_hooks.yaml`, `standing_intent.md`). The kernel treats them as atomic per FOUNDATIONS Axiom 1. The container model is the surface-layer departure from that atomicity, not the granular alternative.

2. **ADR-266's drawer-collapse decision is a symptom.** They had so much heterogeneous content on `/workspace` that program lifecycle had to be hidden in a drawer to give the four cards room. Atomic surfaces dissolve that strain at the root.

3. **Singular Implementation is enforced for free.** Model A produces the current ADR-266 vs ADR-251 drift (Reviewer page still mirrors `/workspace` content even though `WorkspaceConfigSection.tsx` docstring explicitly states it "replaces the Mandate/Autonomy/Principles tabs on the YARNNN agent detail"). Model B makes this drift structurally impossible — there's no parallel render of the same substrate.

4. **New concepts surface additively.** Cadence (the trigger for this discussion) gets `/cadence` as its own destination, with the index page listing it alongside the others. No re-shuffling of an existing container.

5. **Apple precedent works for a reason.** Launchpad doesn't try to render every app on one screen; it lists them. Each app gets full attention when chosen. That pattern scales — YARNNN has 4 concepts today; it will likely have 6-10 in 12 months (cadence, possibly precedent, possibly performance review, etc.). Container models hit a ceiling; index+atomic models don't.

---

## Arguments for Model A (container) — what we'd lose

1. **One-screen tour is genuinely useful for new operators.** Scrolling `/workspace` once shows everything that's configurable. Atomic loses that — the operator has to click into each surface to know what's there. Mitigated by index design: if the index shows a one-line summary per concept, the tour survives.

2. **ADR-244 + ADR-266 are recent investments** (2026-05-01 and 2026-05-11). Replacing the container model with atomic is a real architectural shift, not a small refactor. Migration cost ≠ zero.

3. **Some concepts genuinely co-render.** Identity and Brand are conventionally edited together. Splitting them might force two surface visits where one was natural. Mitigated by allowing `/identity` to be the joint surface (the URL is the model, not a strict 1:1 with files).

4. **Discoverability via user menu currently works** for the container model — user menu lists `/workspace` once. Atomic with many top-level routes risks user-menu bloat, which the index-dispatcher pattern fixes (still one user-menu entry: `/workspace` as index).

---

## Open questions for the future ADR

1. **Is `/workspace` the right index URL?** Or does the index belong at a different route (`/setup`, `/operator`, etc.)? Naming question; not architecturally load-bearing.

2. **What's the index-card minimum viable summary?** Concept name + last revision timestamp + current state badge (configured / skeleton / locked)? Or richer (1-2 lines of content preview)?

3. **Should the user menu list atomic surfaces directly** (for the operator's most-touched concepts), or always route through the index? Recommendation: index-only; user menu stays clean.

4. **Should Reviewer page's Identity tab link to `/identity`** or render its own Reviewer-persona-specific identity? *Different files* — operator IDENTITY.md vs Reviewer occupant IDENTITY.md. Probably separate atomic surfaces (`/identity` for operator, `/agents?agent=reviewer&tab=identity` for the Reviewer's occupant persona). Worth confirming.

5. **What's the migration path?** Atomic introduction can be additive (build new atomic pages, redirect `/workspace` to the index, deprecate inline cards in one PR) or staged (build atomic alongside, deprecate container later). Recommendation: additive single-PR. Singular Implementation discipline argues for no transitional dual-render.

6. **How does cadence fit?** This was the prompt for the entire discussion. If atomic wins, cadence is one of the atomic surfaces from day one — no special-case work. If container wins, cadence either becomes the *fifth* card on `/workspace` (forcing another re-shape) or a Reviewer tab (reviving the cross-page mirror drift problem).

---

## Recommended next step

**Do not decide this in chat or in a frontend implementation PR.** Bundle the decision into a new ADR — *"Atomic Surface Model for Operator-Authored Substrate"* — with:

- The Model A vs Model B comparison from this doc
- Decision (likely Model B, with the index-dispatcher pattern)
- Migration plan from current state
- Amendment trail: ADR-244 (Workspace surface), ADR-266 (workspace content discipline), ADR-251 (Reviewer tabs), ADR-214 (Agents page consolidation), ADR-243 (Schedule surface)
- Companion ADR for the cadence atomic surface (`/cadence`) consuming the model

That ADR is **the right home** for the decision, not the cadence-hardening session. The cadence-hardening session should write the canon synthesis doc (`docs/architecture/cadence-and-wakes.md`), land the kernel-side hardening it identifies, and explicitly defer surface placement to this parked discussion.

---

## What this doc does NOT do

- Does not ratify Model B.
- Does not amend ADR-244, ADR-251, ADR-266, ADR-214, ADR-243.
- Does not commit to specific atomic URLs (`/mandate` vs `/setup/mandate` etc. is naming-only).
- Does not specify the index-card design.
- Does not block the cadence-hardening work — that work is surface-neutral and proceeds regardless.

This is a **parked design discussion**. The next ADR session opens it.
