# ADR-312 — Home as Composition: Kernel Constituent Slots, Constitution Register, Generic Ground-Truth Hero

**Status:** **Implemented (2026-06-02) — Phases 1–7 landed.** Register split (`intent` + `os-config`, P2); cockpit→Home surface rename (P3); generic ground-truth hero de-skin + program-labeled live-entities + ADR-312 regression gate `api/test_adr312_home_as_composition.py` 9/9 (P4); `/api/cockpit/*` fold → `/api/programs/alpha-trader/*` (trader data) + `/api/pace` (kernel governance), FE `api.cockpit.*` → `api.programs.alphaTrader.*` + `api.pace()`, Render parity confirmed (P5); program-declared autonomy defaults documented, ADR-226 amendment (P6); doc cascade — supersede banners on ADR-228 + ADR-273, amend banner on ADR-309 + ADR-226, GLOSSARY (Home / Constitution band / Ground-truth hero / three registers), FOUNDATIONS Axiom 6 home-as-composition note, SERVICE-MODEL Frame 5, compositor.md + COCKPIT-COMPONENT-DESIGN.md banners, CLAUDE.md index + surface-model addendum (P7). Singular Implementation throughout — cockpit slug/route/components/composition-key deleted, not aliased. Gates green: `test_adr312_home_as_composition.py` 9/9, `test_adr297_phase1.py` 137/137, `test_adr309_two_registers.py` 9/9; `tsc --noEmit` clean; `next build` emits `/home`. The dead ADR-242-phase2 four-face gate was deleted; ADR-242-phase1 + ADR-300 pace gates updated to the post-fold reality.
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

#### D2 amendment (2026-06-04) — kernel renders the three universal slots; the program declares only the two program-shaped ones

The original D2 sentence ("the program declares each slot's … whether it renders") was implemented as *all of Layer 2 is program-gated* — the kernel rendered only slot #1 (constitution band) and delegated #2–#6 entirely to the program's `SURFACES.yaml home.program_sections[]`. The consequence was a defect: an activated program that declared no sections — or a bare kernel — fell through to a near-empty "this program does not declare a home dashboard" CTA, even when the workspace had pending proposals, delivered outputs, and a Reviewer decision trail.

The fix partitions the six slots by **substrate ownership**:

- **Kernel-universal slots (#3 Decision queue, #5 Recent artifacts, #6 Judgment trail)** read *kernel* substrate — `action_proposals` (the ADR-307 generic gated-action queue), delivered outputs in `workspace_files` (`/workspace/reports/{slug}/{date}/output.md`), and `/workspace/review/decisions.md`. These exist in **every** workspace, program or not. The **kernel renders them directly** via `web/components/library/kernel-home/{KernelDecisionQueue, KernelRecentArtifacts, KernelJudgmentTrail}.tsx`, interleaved by `HomeRenderer` in slot order. They are NOT declared in any `SURFACES.yaml`. Each **self-hides when its substrate is empty**, so the cold-start Home stays honest.
- **Program-shaped slots (#2 Ground-truth hero, #4 Live entities)** read *program* substrate whose shape only the program knows (a trader's P&L strip, an author's corpus signal). These stay program-declared via `home.program_sections[]` (§D3/§D4), generic contract, no kernel default.

So "the program declares whether [a slot] renders" holds for #2/#4 (the program-shaped slots), and is superseded for #3/#5/#6 (the kernel-universal slots — the kernel renders them whenever their substrate is non-empty). This closes the dead-end-Home defect and is faithful to D2's own description of slot #3 as "the ADR-307 generic gated-action queue, unchanged" — a generic, kernel-owned queue was never a program concern.

Backend: `GET /api/workspace/recent-artifacts` (new, browser-only) backs slot #5; #3 reuses `GET /api/proposals`; #6 reuses `getFile(decisions.md)` + the canonical `content-shapes/decisions.ts` parser. No parallel implementations.

#### D2 amendment #2 (2026-06-04) — a program declares exactly two slots (hero + entities); plain language throughout

The first D2 amendment fixed *what the kernel renders*. This one fixes *what a program may declare* — and the operator-facing language of the whole Home. It was triggered by the alpha-yarnnn-author Home reading as an incoherent metric dashboard rather than "here's your writing operation."

**The defect.** A program's `home.program_sections[]` accepted an arbitrary stack of component `kind`s. alpha-author declared four (`AuthorMandate`, `AuthorCorpus`, `AuthorVoice`, `AuthorPipeline`); alpha-trader declared seven. The result, on the author Home: (a) the mandate rendered **twice** — once in the kernel `HomeHeader` (slot #1) and again in `AuthorMandate`; (b) the autonomy posture rendered twice (both); (c) "voice accuracy" appeared in **two separate cards** (`AuthorCorpus` + `AuthorVoice`), each showing the same `—`; (d) eight mostly-empty metric cards (`0` / `—` / `never`) read as a broken dashboard, not an operation. This violated D2's own wording — slot #2 is "the operation's **primary** signal" (singular), not "every metric the program tracks."

**The rule.** A program declares **exactly two slots**:

- **#2 Ground-truth hero** — *one* component answering the single human question "**is this working?**" One headline, in plain words, with at most a quiet line of support. (Author: `AuthorHero` — "Your voice is holding / drifting"; voice-consistency is the headline, coherence + audit volume are quiet support. Not three cards.)
- **#4 Live entities** — *one* labeled list answering "**what's in play?**" Program-labeled rows, newest-first, not a metric grid. (Author: `AuthorPieces` — the corpus pieces with their state. Not Drafts/Published/Total counters.)

A program **may NOT**: re-render the mandate or autonomy (kernel slot #1 owns them); render the decision queue, recent artifacts, or judgment trail (kernel slots #3/#5/#6 own them); or declare more than two program sections. The kernel test gate asserts `home.program_sections` has ≤2 entries and that no program registers a `*Mandate` component.

**Plain-language pass (the macOS lesson).** A Mac shows "Storage: 234 GB available," not inode counts. The Home was showing inodes. Every operator-facing string is de-jargoned: the decision-queue maps primitives to verbs (`WriteFile` → "Save a workspace change") and drops the `substrate`/`capital` jargon word (the color dot carries that distinction); recent artifacts strip machine/path summaries ("Workspace write: reports/…/output.md" → the clean title) server-side via `_artifact_title()`; slot headers read "Waiting for your OK" / "Recently delivered" / "Recent decisions." The vocabulary north star, per program-author guidance:

| Engineer term | Operator-facing |
|---|---|
| Primary Action | the operation's one-line mission (kernel HomeHeader) |
| Voice fingerprint / Pattern markers | "your writing voice" / "style tells" |
| voice_audit_accuracy_30d | "your voice is holding / drifting" |
| WriteFile · substrate | "Save a workspace change" |
| Decision queue | "Waiting for your OK" |
| Judgment trail | "Recent decisions" |
| Recent artifacts | "Recently delivered" |

alpha-author reshaped this pass (4 sections → `AuthorHero` + `AuthorPieces`). alpha-trader's seven-section stack also violates the two-slot rule; its reshape is deferred to a follow-up (it has genuinely more ground-truth surface — regime, P&L, positions, signals, orders — and was iterated heavily; reshaping it is its own pass). The contract + gate are in force now; trader is the known exception pending follow-up.

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

On a bare kernel (no mandate), slot #1 renders "Declare what this workspace is for / activate a program" — the home doubles as onboarding. The cold-start home = empty constitution CTA + menu-bar vitals (Balance, Connections) + whichever kernel-universal slots (#3/#5/#6) already have substrate. No ground-truth hero, no program faces (those are program-shaped, #2/#4). Per the **D2 amendment (2026-06-04)** the kernel-universal slots self-hide when empty, so a truly-fresh workspace shows just the constitution CTA, while a workspace that has accumulated proposals / outputs / decisions shows those even before a program is picked. **Honest Phase-1 home; the "blank cockpit" is eliminated structurally.** Constitution is a *section of the home*, not a separate surface.

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
