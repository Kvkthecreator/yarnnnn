# ADR-312 — Home as Composition: Kernel Constituent Slots, Constitution Register, Generic Ground-Truth Hero

**Status:** Proposed (2026-06-02). Doc-only ratification of the frame + decisions; the implementation cascade (§Implementation) is gated on operator approval of this ADR.
**Supersedes:** ADR-228 (Cockpit as Operation — four-faces framing) and ADR-273 (Cockpit Refactor — program-section-split) at the *framing* level: the cockpit is no longer a program-shaped dashboard with a fixed face stack. Their substrate-read routes and program-component library survive, re-homed under the home-as-composition contract (§D2, §D9).
**Amends:** ADR-309 (two-register model — the `settings` register cleaves into `os-config` + `constitution`, §D5); ADR-226 (bundle fork ships an autonomy *default*, §D7); ESSENCE v13.0 (the two-layer product gets its surface expression).
**Preserves / consumes:** FOUNDATIONS Axioms 1–9; ADR-222 (kernel/program boundary — the program declares weighting, the kernel provides slots); ADR-225 (compositor — the mechanism a program uses to weight slots); ADR-245 (three-layer rendering — Files is L1 raw, the home is L3 composed); ADR-281 (six-role substrate taxonomy — the home composes substrate by role); ADR-307 (generic gated-action queue — slot #3 unchanged); THESIS four commitments; the sequenced-moat substrate-first / judgment-as-rider thesis.
**Dimensional classification:** Channel (primary, Axiom 6 — what the operator sees and where) + Identity (the Constitution register names the operation's authored intent) + Purpose (the home renders *why this operation exists* first).
**Discourse trail (Hat B):** [home-as-composition-stress-test-2026-06-02.md](../analysis/home-as-composition-stress-test-2026-06-02.md) (the two-persona stress test + six findings) + [sequenced-moat-strategy-2026-06-01.md](../analysis/sequenced-moat-strategy-2026-06-01.md) (the substrate-first product frame this surfaces).

---

## 1. Context — the false binary the cockpit framing created

ADR-228 + ADR-273 built the cockpit as *the operation, rendered* — a program-shaped dashboard (four faces, then a trader section stack). That was correct for an *activated* trader workspace and wrong for everything else: a bare-kernel workspace (no program) rendered as a *de-activated trader cockpit* — empty money-truth, empty queue, empty faces — which reads as "blank," and the question "what is the bare-kernel home, Files or cockpit?" had no answer.

The ESSENCE v13.0 rewrite (substrate floor + additive judgment layer) and the two-persona stress test (Hat B) dissolved the binary. **Every workspace — trader, author, partnership manager, A&R, SCM, engineer — has the same six constituents at different weights; the weight-shift is what a *program* declares.** The home is not a fixed dashboard; it is a **composition over the workspace's present constituents**, substrate-forward when empty, operation-forward when a program runs. Files-vs-cockpit was never a fork — Files is the L1 raw escape hatch (ADR-245), the home is the L3 composed default.

## 2. Decisions

### D1 — Cockpit dissolves into Home

The home surface (`slug: "cockpit"`, route `/cockpit`, `CockpitPage`, `CockpitRenderer`) renames to **`home`** (route `/home`, `HomePage`, `HomeRenderer`). Singular Implementation: the cockpit slug/route/component are deleted, not aliased. The four-face stack (ADR-228) and the fixed trader section sequence (ADR-273) as the *default render* are deleted; they survive only as a program's declared composition (§D2).

### D2 — The kernel home contract: six constituent slots

The home renders six slots, top→bottom. The kernel owns the slot set and their order; the **program declares each slot's weight, label, shape, and whether it renders** (via the compositor, ADR-225). Absent constituents do not render — the home is honest about what exists.

1. **Constitution band** (collapsible, top) — mandate one-liner + Reviewer persona. Operation's authored intent (§D5 constitution register).
2. **Ground-truth hero** — the operation's primary signal. *Generic; program-declares the shape* (§D3).
3. **Decision queue** — consequential actions awaiting operator approval. The ADR-307 generic gated-action queue, unchanged.
4. **Live entities** — the operation's currently-active entities. *Program-labeled* (§D4).
5. **Recent artifacts** — delivered outputs (reports / contracts / published / shipped).
6. **Judgment trail** — recent decisions + reconciled outcomes.

### D3 — The ground-truth hero is generic, not money-truth (F1)

Slot #2 is a **ground-truth panel** whose shape the program declares: money-truth strip (trader), pipeline-stage board (partnerships), coherence/publication panel (author). The kernel content-shape names a generic hero contract; `web/lib/content-shapes/money-truth.ts::CANONICAL_L3 = 'TraderMoneyTruth'` is de-skinned — `TraderMoneyTruth` becomes the *alpha-trader binding* of the hero slot, not the kernel default. This is the concrete code instance of the "money-truth is a trader-skin in the kernel frame" finding (sequenced-moat §8; ESSENCE v13.0 demotion of money-truth).

### D4 — The live-entities slot is program-labeled (F2)

Slot #4's label and entity shape are program-declared ("Positions" / "Partners" / "Pieces" / "Open PRs"). The kernel never hardcodes a trader noun.

### D5 — Register split: `os-config` vs `constitution` (amends ADR-309)

ADR-309's `settings` register conflated *the OS configuring itself* with *the operation declaring what it is*. It cleaves:

- **`os-config`** — autonomy, pace, connectors, billing/settings. "The OS configuring itself." Glanceable in the menu-bar vitals (`SystemStatusCluster`); click-to-configure. Rarely opened.
- **`constitution`** — mandate, principles, identity. The operation's authored intent. Surfaced **first-class** as the home's Constitution band (slot #1), NOT buried in a settings drawer. *The mandate is the project's charter, not a wifi setting.*

`kernel_surfaces.py` `register` flips for `mandate`/`principles`/`identity`: `settings` → `constitution`. `autonomy`/`pace`/`connectors`/`settings` → `os-config`. Application surfaces (`home`/`files`/`agents`/`queue`/`cadence`/`activity`) unchanged.

### D6 — The constitution band's empty state is the onboarding/activation entry (F5, F6)

On a bare kernel (no mandate), slot #1 renders "Declare what this workspace is for / activate a program" — the home doubles as onboarding. The cold-start home = empty constitution CTA + slot #4 showing "your authored files" + menu-bar vitals (Balance, Connections). No ground-truth hero, no queue, no faces. **Honest Phase-1 home; the "blank cockpit" is eliminated structurally.** Constitution is a *section of the home*, not a separate surface.

### D7 — Autonomy default is program-declared (F4, amends ADR-226)

The bundle fork ships an autonomy *default* appropriate to the operation: capital/rule-bound operations (trader) default `bounded`/`autonomous`; relationship/high-touch operations (partnerships, A&R) default `manual`. The kernel does not pick a global default; the program declares it at activation. Operator tunes from there. (The `DEFAULT_REVIEWER_WRITE_LOCKS` self-authority floor is unchanged — autonomy remains operator-owned, Reviewer-locked.)

### D8 — Substrate surfaced by role (consumes ADR-281)

The home composes substrate by ADR-281's six-role taxonomy (`operator-canon` / `reviewer-workbench` / `system-ledger` / `world-mirror` / `running-narrative` / `kernel-index`): constitution band ← `operator-canon`; live entities + context ← `world-mirror` + accumulated context; judgment trail ← `system-ledger` + `running-narrative`. Files (L1) remains the flat raw-substrate escape hatch.

### D9 — The cockpit-route fold (operator-elected, one sweep)

`/api/cockpit/*` is de-namespaced. **Trader-program data routes** (money-truth, positions, regime, signals, indicators, portfolio-history, recent-orders) move under a program-data namespace (e.g. `/api/programs/alpha-trader/*` or `/api/trading/*` — exact prefix chosen at code-PR time). **`/api/cockpit/pace`** is a *kernel governance dial*, not trader data — it folds to a kernel location (e.g. `/api/pace` or under `os-config`). Singular Implementation: no `/api/cockpit/*` route survives. Frontend `web/lib/api/client.ts` callers migrate in the same commit.

## 3. Implementation phases (gated on ratification of this ADR)

1. **This ADR + the stress-test analysis doc** — doc-only ratification (done as drafts; operator approves).
2. **Register split** — `kernel_surfaces.py` `register` values (`constitution` + `os-config`); shell register handling; ADR-309 amendment banner.
3. **cockpit → home surface rename** — slug/route/`CockpitPage`→`HomePage`/`CockpitRenderer`→`HomeRenderer`/`SurfaceRegistry`; delete the four-face fallback remnants.
4. **Kernel home contract** — six slots; generic ground-truth hero (de-skin `CANONICAL_L3`); program-labeled live-entities; substrate-by-role composition.
5. **`/api/cockpit/*` fold** — trader routes → program namespace; `pace` → kernel; client.ts migration; Render parity check (API + Scheduler use these paths).
6. **Bundle autonomy default** — alpha-trader + alpha-author + reference bundles declare autonomy default at fork (ADR-226 amendment).
7. **Doc cascade** — ESSENCE (done, v13.0); FOUNDATIONS (Channel/Axiom-6 home-as-composition note); GLOSSARY (Home / Constitution register / Ground-truth hero); SERVICE-MODEL (Frame 5 surface model); `compositor.md` + `COCKPIT-COMPONENT-DESIGN.md` (rename + slot contract); supersede banners on ADR-228 + ADR-273; amend banner on ADR-309.

Each phase lands green (tsc/build clean, regression gates pass). A regression gate asserts: no kernel surface hardcodes a trader noun in slots #2/#4; the bare-kernel home renders without a program; `/api/cockpit/*` returns 404 post-fold.

## 4. Rejected alternatives

- **Keep cockpit as a program dashboard + add a separate generic "Overview."** Two home surfaces, two cold-start answers, the "which is home?" ambiguity persists. Rejected — Singular Implementation. One adaptive home.
- **Files as the bare-kernel home, cockpit program-supplied (the §fork option a).** Cleaner-sounding but makes the cold-start a raw file browser (poor first experience) and creates a home/cockpit toggle. The composition model gives one home that is substrate-forward when empty — strictly better. Rejected.
- **Keep `mandate` in the `settings` register.** Buries the most-consulted authored artifact behind a config drawer. The mandate is the operation's constitution, not OS config. Rejected (D5).
- **Defer the `/api/cockpit/*` fold.** Operator elected one clean sweep — leaving trader data mis-namespaced under "cockpit" after the surface renames to "home" would be a fresh inconsistency. Rejected (D9).
- **A program-declared *slot set* (programs add/remove slots).** Over-flexible; the six constituents are universal (stress test §2) — programs weight and label, they do not invent slots. Rejected — kernel owns the slot set, program owns the weighting.
