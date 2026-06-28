# Marketing interaction design — the spec of record

**Date:** 2026-06-29
**Status:** Phase 0 (this doc). Phases 1–4 implement against it.
**Scope:** the four marketing surfaces — Landing (`/`), How it works (`/how-it-works`),
About (`/about`), Pricing (`/pricing`).
**Companion:** [marketing-interop-pivot-rewrite-2026-06-26.md](./marketing-interop-pivot-rewrite-2026-06-26.md)
(the positioning + copy strategy of record). This doc governs *interaction*; that one governs
*message*. They cross-reference.
**Not an ADR:** marketing-surface design, not kernel/canon. Touches no FOUNDATIONS axiom, no
primitive, no substrate. Lives under `docs/design/` like its companion.

---

## 0. Why this exists

The pages went flat after the interop pivot. The diagnosis was concrete, not aesthetic: the
pivot's copy refactor replaced richer interactive sections with static bordered text blocks and
**left the product's three differentiating mechanisms told in prose and shown nowhere.** Two
animated components (`AnimatedTimeline`, `MockOutputs`) were orphaned in the process; the one
interactive card style that survived (`SpotlightCard`) was applied inconsistently — the landing
page's most important section (the product trio) became its flattest.

This spec reframes the interaction model **from the positioning down**, not from the components
up. The center of gravity is the thesis, not the asset inventory.

---

## 1. The governing principle

> **Interaction demonstrates the mechanism; it does not decorate the page.**

This is the discipline that separates "more interactions" done well from junior over-animation.
Every interactive element earns its place by *showing a property of the product that prose can
only assert*. The brand is restraint ("receipts, not claims") — so motion is **spent only where
it proves a claim**, and everything else stays deliberately calm. A page where the three moat
mechanisms move and nothing else does reads as confident; a page where everything moves reads as
hype. **That contrast is the design.**

The three mechanisms worth demonstrating are the three rungs of the moat
(from the pivot strategy §1):

| Rung | The claim | Why prose alone fails | The demonstration |
|---|---|---|---|
| **Membrane** | "write it once, it's in every AI" | a static chip row can't convey *shared* | one input visibly propagates to many rooms |
| **Ledger / trace** | "every change has an author + a version" | this is the uncopyable property and it's currently invisible | a version stack reveals author · date · what-changed |
| **Compounds** | "fix once; day 1 → 30 → 90" | three static boxes don't convey *advancing* | a progression the visitor moves through |

Everything else — the problem section, the insight prose, the steward-beta teaser, the pricing
teaser, the About beliefs — stays **static on purpose**, lifted only by the global scroll-reveal
connective layer (§2).

---

## 2. Global motion rules (binding on every page)

1. **Scroll-reveal is connective tissue, not a feature.** A single fade + 12px rise on section
   enter makes the long scroll feel composed. One shared wrapper component, applied to every
   **non-hero** section.
2. **Never animate the hero.** Above-the-fold renders instantly — protects LCP and perceived
   speed. The hero's *interactive demo* (membrane) may animate after paint, but the hero text +
   CTAs are never reveal-gated.
3. **`prefers-reduced-motion` is honored everywhere.** Every animation in this system — new and
   existing — degrades to its final static state under reduced-motion. This includes the
   existing `globals.css` keyframes (`breathe`, `shimmer`, `tp-pulse`, `gradient-shift`, etc.),
   which currently have **no reduced-motion guard** — Phase 1 adds a global
   `@media (prefers-reduced-motion: reduce)` block that neutralizes them. (Pre-existing a11y gap,
   fixed in passing.)
4. **No layout shift.** Reveals animate `opacity` + `transform` only — never height/margin that
   would cause CLS. Elements occupy their final box from first paint; only their appearance
   transitions.
5. **Touch-aware.** Hover-driven interactions (spotlight, membrane line-draw) no-op on coarse
   pointers and fall back to the auto-cycling / static state. (`SpotlightCard` already does this;
   new components match the pattern.)
6. **Client-component budget.** These pages are otherwise static server components. Each new
   interactive piece is an island (`'use client'`) kept small; no heavy animation dependency is
   added (no `framer-motion`) — CSS transitions + `IntersectionObserver` + the existing canvas
   beam engine cover the whole system.

---

## 3. Page-by-page: intent → interaction → component

### Landing (`/`)

| Section | Design intent | Interaction | Component | State today |
|---|---|---|---|---|
| Hero | "every AI, one memory" grasped in 3s | **Membrane demo** (centerpiece): a memory card center; rooms (Claude/ChatGPT/Slack/Notion/your agents) beam to it; auto-cycles, interactive on hover; reflects "available here." | `MembraneDemo` (new — harvests the `IntegrationHub` beam engine; retires its agent-flow framing) | static chip row + decorative `IntegrationHub` ("Context→yarnnn→Agents", pre-pivot) |
| Problem | the trapped-context ache; calm | scroll-reveal only | — | static (keep) |
| Product trio | the three moat mechanisms, *shown* | Card 1 **Traceable** → live `trace` mini-widget (expands to author·date·diff). Cards 2 **Cross-LLM** + 3 **Compounds** → `SpotlightCard` for consistency. | `TraceCard` (new, mock data) + `SpotlightCard` (existing, applied) | three flat `border bg-[0.02]` boxes |
| Steward beta | forward-looking, quieter | scroll-reveal only; beta tag, no fake motion | — | static (keep) |
| Insight + Day 1/30/90 | accumulation you *advance through* | **Compounds stepper**: Day 1 → 30 → 90 advance on scroll/click, the memory visibly thickening | `CompoundsStepper` (new) | three static `SpotlightCard`s in a bento |
| Pricing teaser + CTA | confident close; static | scroll-reveal only | — | static (keep) |

### How it works (`/how-it-works`)

| Section | Design intent | Interaction | Component | State today |
|---|---|---|---|---|
| Hero | "set up once, everywhere after" | static (above fold) | — | static (keep) |
| The 5-step loop | a *connected journey*, not a flat list | **Step flow**: a vertical progress line that fills as you scroll past each step, pulse marker at the active step | `StepFlow` (new — harvests the pulse-line technique from orphaned `AnimatedTimeline`, then deletes it) | flat `01/02/03` vertical list |
| Step 05 verdict trio | the beta seat's three calls | keep `SpotlightCard` (already good) | existing | good (keep) |
| Mechanism trio | Traceable / Cross-LLM / Compounds | keep `SpotlightCard` (already good) | existing | good (keep) |

### About (`/about`)

Calm by design — the "why we exist" page; over-animating cheapens it.
- Beliefs, "what it's not," "who it's for": **static + scroll-reveal only.**
- One earned moment (optional): the quiet "git's model, served cross-LLM" under-the-hood line
  may get a small `trace`-style reveal so the page's one technical proof is shown, not told.
  Propose in Phase 2; don't force.

### Pricing (`/pricing`)

Already interop-forward and copy-stable. **Scroll-reveal only.** A pricing page that animates
too much distracts from the number. Restraint is correct here.

---

## 4. Component inventory (singular implementation — one home each)

**New:**
- `ScrollReveal` — wrapper; `IntersectionObserver` → fade+rise once on enter; reduced-motion → no-op (renders final state). Used on every non-hero section, all four pages.
- `MembraneDemo` — hero island; memory card + room beams; auto-cycle + hover. Built on the `IntegrationHub` canvas/beam logic. Landing hero only.
- `TraceCard` — small island; a 2–3 entry revision stack that expands to author·date·diff on hover/tap. **Mock data** (tasteful, hand-crafted — decided 2026-06-29). Landing product trio, card 1. (Reused on About if the optional moment lands.)
- `CompoundsStepper` — island; Day 1/30/90 advance-through. Landing insight section only.
- `StepFlow` — island; vertical 5-step connected flow with filling progress line. How-it-works only.

**Existing, kept:**
- `SpotlightCard` / `BentoGrid` — applied to landing trio cards 2/3 (new) + how-it-works trios (existing). Gets a reduced-motion guard in Phase 4.
- `ShaderBackground` / `ShaderBackgroundDark` / `GrainOverlay` — ambient layer, unchanged (covered by the global reduced-motion block).
- `IntegrationHub` — beam engine **harvested** by `MembraneDemo`. If `MembraneDemo` fully subsumes it, the file is retired; if it extends it, `IntegrationHub` stays as the shared engine. Decided at Phase 2 build.

**Retired (per CLAUDE.md singular-implementation discipline):**
- `MockOutputs.tsx` — orphaned + off-thesis (shows agent deliverables PDF/email/brief = pre-pivot agent-first story). **Delete in Phase 2.**
- `AnimatedTimeline.tsx` — orphaned + stale copy ("tasks run on schedule," "the right agent" = pre-pivot). **Harvest pulse-line → `StepFlow`, then delete in Phase 3.**

No parallel/duplicate components survive a phase.

---

## 5. Accessibility & performance checklist (gate before each phase ships)

- [ ] `prefers-reduced-motion: reduce` → every animation renders its final static state (new + the existing `globals.css` keyframes).
- [ ] No CLS — reveals are `opacity`/`transform` only; elements hold their final box from first paint.
- [ ] Keyboard — any interactive demo (membrane rooms, trace expand, stepper, step-flow) is operable by keyboard and focus-visible; nothing is hover-only for its core meaning.
- [ ] Touch — hover-driven affordances no-op on coarse pointers and fall back to auto-cycle/static.
- [ ] Hero LCP unaffected — hero text + CTAs never reveal-gated; demo hydrates after paint.
- [ ] Bundle — no new animation dependency; new islands are small; `tsc --noEmit` + `next build` clean per phase.
- [ ] Semantics — decorative motion is `aria-hidden`; meaningful content (trace entries, steps) stays in the DOM and readable with JS off where feasible.

---

## 6. Build sequence

Phased; each lands independently, validated before the next; one commit per phase.

- **Phase 0 — docs** (this doc + a pointer section in the pivot doc). *Doc-first.*
- **Phase 1 — global motion layer.** `ScrollReveal` on non-hero sections, all four pages + the global reduced-motion block in `globals.css`. Lowest risk, biggest "alive" delta. Retire nothing.
- **Phase 2 — the three moat demonstrations.** `MembraneDemo`, `TraceCard` (mock), `CompoundsStepper`. Retire `MockOutputs`.
- **Phase 3 — the flow.** `StepFlow` on how-it-works; harvest + delete `AnimatedTimeline`.
- **Phase 4 — consistency + final pass.** `SpotlightCard` on landing trio cards 2/3; reduced-motion guard on `SpotlightCard`; full a11y + build validation.

Each phase: `tsc --noEmit` + `next build` clean; commit; review.
