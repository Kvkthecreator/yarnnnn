# Floor and Fiduciary: The Inherent Base Use Case, the Metaphor Re-Examined, and the Four-Flow Feature Scope

**Status:** Hat B (discourse capture) — **proposed for discourse before any canon edit.** This doc recommends a positioning frame and a feature-scope lattice; it does NOT amend ESSENCE / NARRATIVE / FOUNDATIONS. The canon cascade is named in §11 and deferred.
**Date:** 2026-06-15
**Hat:** B (external-developer surface — positioning + scope reasoning)
**Authors:** KVK (operator), Claude (collaborator)
**Origin:** the operator asked how to position YARNNN as a "general-purpose autonomous self-improving agent," reaching for device metaphors (iPhone, telephone) and the idea of an *inherent base use case* a general-purpose technology assumes. The telephone metaphor was worked in full, found to strain on the judgment half, and is re-examined here.

**Grounded in:**
- `docs/ESSENCE.md` v14.1 (the two-layer cumulative-workspace model — the floor/generality structure this doc names)
- `docs/architecture/THESIS.md` (the four commitments; the fiduciary/independence properties)
- `docs/adr/ADR-332-four-flow-completeness-model.md` + `docs/adr/ADR-335-perception-field.md` (the four flows — the second-order scoping lattice)
- `docs/adr/ADR-310-judged-substrate-interop-face.md` + `docs/adr/ADR-311-primitive-interop-surface.md` (the interop face — the portability mechanism)
- `docs/adr/ADR-320-constitution-region-topological-cut.md` (the five-root substrate topology)
- `docs/adr/ADR-340-operator-experience-model.md` (the FE standing loop — mirror once, compose few)
- `docs/adr/ADR-222-agent-native-operating-system-framing.md` (the OS framing — already canon, load-bearing for the recommended frame)

---

## 0. Executive summary (the finding)

1. **The durable insight (metaphor-independent):** general-purpose technologies never ship general-purpose. They enter through one *inherent base use case* — an always-on, zero-configuration **floor function** — and the generality *accretes* on the floor. The floor is what the thing does by merely existing and being on. (§1)

2. **YARNNN already encodes this** as ESSENCE v14's two layers: Layer 1 (authored, attributed, portable substrate) is the floor; Layer 2 (the judgment layer — programs, the Reviewer, the autonomous self-improving operation) is the accretion. "General-purpose autonomous self-improving agent" is **not the base use case** — it is the accretion layer. (§1)

3. **The four-flow model decomposes the three adjectives precisely** (§7): *general-purpose* = the floor; *autonomous* = flows 1→2 (perception → work) on cadence; *self-improving* = flows 3→4 (outcomes reconcile against judgment → calibration). You do not position "a general-purpose autonomous agent." You position **a general-purpose floor on which a specific autonomous operation (a program = a declared flow-set) runs.**

4. **The telephone strained on three seams** (§2): it has a network-effect floor (YARNNN's is single-operator), its judgment seat (the switchboard operator) was historically *automated away* (YARNNN's compounds), and it is weak on flows 3+4.

5. **The metaphor re-examination's structural finding** (§4–5): **no single object carries both layers.** Impersonal general-purpose technologies (telephone, PC, grid) ace the floor and fail the judgment seat; personal fiduciary relationships (banker, doctor) ace the judgment seat and fail general-purpose. The two have never coexisted in one artifact because they are *historically opposed* — generality scales by being impersonal; fiduciary judgment is valuable by being personal and unscalable.

6. **The recommended frame is a deliberate fusion** (§6): the floor is an **operating system** (already YARNNN's canon metaphor, ADR-222); the seat is a **fiduciary** (private banker / family doctor). YARNNN is the first artifact where the two coexist — authored substrate makes personal context scalable/portable; an occupant-rotating seat makes fiduciary judgment instantiable in software. This is also *why* ESSENCE v14 leads with the seat and proves with the substrate.

---

## 1. The pattern: general-purpose technology enters through an always-on floor

Two different objects get conflated in the phrase "general-purpose autonomous self-improving agent":

- **The general-purpose substrate** — what the thing *can* do (open-ended; the long-term reason it matters).
- **The inherent base use case** — what the thing *always* does (narrow, always-on; the reason it is present and powered).

Every successful general-purpose technology was *positioned by the second and grew into the first.* The floor function has three properties:

1. **Always-on, not invoked** — true when you are not using the thing for anything special (the dial tone before a call; the clock before an app; the kernel before a program).
2. **Zero-config value** — valuable the instant you possess it; no "imagine day 90."
3. **Gravitational** — the generality accretes *on top of and around* the floor and never replaces it (the App Store on "the always-present connected screen").

Receipts from the adoption record: the PC sold via VisiCalc / word processing, not "Turing-complete computation"; the iPhone (2007) shipped with **zero** third-party apps and sold fine — the App Store (2008) *defined* it later; the browser sold "render a page at a URL," not "a universal application runtime."

**YARNNN already encodes the pattern** (ESSENCE v14, "The Two Layers, Concretely"):
- **Layer 1 — authored substrate, served everywhere** = the floor. *"Valuable the moment you author anything; it needs no program, no mandate, no autonomous agent."* Always-on, zero-config, gravitational.
- **Layer 2 — the judgment layer (what a program adds)** = the accretion. Programs, the Reviewer, the autonomous self-improving operation.

So the answer to the operator's framing difficulty: the "general-purpose autonomous self-improving agent" is the accretion layer, not the base use case. Trying to make the generality the entry is the PC-as-"Turing-machine" error — generality has no zero-config value because it requires the user to supply the specific use, the one thing a cold user cannot do. (NARRATIVE.md already bans this as the "demo that requires tenure" anti-pattern.)

---

## 2. Why the telephone strained (the three seams)

The telephone was worked in full (line → dial tone → number → handset → switchboard operator → services). It is excellent for the *architecture* of the floor + accretion, but it strains on three seams, all on the judgment half:

1. **Network-effect floor vs. per-operator asset.** A phone with no one to call is useless (Metcalfe). YARNNN's floor is valuable with zero counterparties — portable context, not a connection to others. *Stronger* than the telephone (no cold-start network problem), but it means the telephone's "everyone already has one" growth story does not transfer.
2. **The switchboard operator was automated away.** The human operator *was* the telephone's judgment seat — and the industry's whole arc was *removing* them. YARNNN's thesis is the opposite: the seat is the durable, compounding, un-removable thing (Principle 14 — occupant rotates, seat persists). Invoking the operator invites the rejoinder "didn't they automate that away?"
3. **Weak on flows 3+4.** The telephone carries perception (incoming) and work (outgoing) naturally, but has no native analog for *outcomes reconciling against judgment over tenure* — which is exactly the self-improving half.

The seams are not telephone-specific bad luck. They are the signature of *every impersonal general-purpose technology*, which §4–5 makes precise.

---

## 3. The criteria a metaphor must satisfy

Derived from the two-layer structure (§1), the four flows (§7), and the three seams (§2):

| # | Criterion | Which half it tests |
|---|---|---|
| C1 | **Always-on floor** — zero-config, valuable day one, single-user | Floor |
| C2 | **Owned + portable substrate** — yours, travels with you | Floor |
| C3 | **Generality accretes** — the App Store pattern | Floor → generality |
| C4 | **Judgment seat compounds over tenure** — not automated away | Generality |
| C5 | **Independence** — the seat refuses the principal's bad impulse (THESIS Commitment 2 / ADR-319) | Generality |
| C6 | **Four-flow fit** — perception / work / outcomes / loop all map (esp. 3+4) | Generality |
| C7 | **General-purpose** — not domain-locked | Floor |
| C8 | **Avoids YARNNN anti-patterns** — not "lock-in moat," not "wiki/memory," not "delegate-labor" | Both |

---

## 4. The candidate survey

| Candidate | C1 floor | C2 owned/portable | C3 accretes | C4 seat compounds | C5 independence | C6 four-flow | C7 general | C8 anti-patterns | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| **Telephone** | ~ (network-dep) | ✓ (number port.) | ✓✓ (modem→internet) | ✗ (operator automated away) | ✗ | ~ | ✓ | ~ | Great floor+accretion; bankrupt on judgment |
| **PC / OS** | ✓✓ | ✓ (your files) | ✓✓ (apps) | ✗ (no seat) | ✗ | ✗ (OS doesn't perceive/reconcile) | ✓✓ | ✓ | Best floor; already canon (ADR-222); zero judgment |
| **Electrical grid** | ✓✓ (purest) | ✗ (no ownership) | ✓✓ (every appliance) | ✗ | ✗ | ✗ | ✓ | ✓ | Pure commodity; no ownership, no judgment |
| **Bank + private banker** | ✓ | ✓ (move banks) | ✓ | ✓✓ (fiduciary) | ✓ | ✓✓ (ledger ≈ revision chain) | ✗ (finance-locked) | ✗ (opaque; lock-in moat) | Best technical four-flow fit; domain-locked + anti-patterns |
| **Family doctor + owned record** | ~ (record not day-one) | ✓ (patient-owned) | ✓ (care apparatus) | ✓✓ (strongest intuition) | ✓✓ ("no, you don't need that") | ✓✓ (labs = un-fakeable outcome) | ✗ (health-locked) | ✓ | Best judgment + independence + outcomes; domain-locked |
| **AI chief-of-staff / staff** | ✗ (labor, no floor) | ✗ | ~ | ~ | ~ | ~ | ✓ | ✗ (the incumbent commodity frame) | The frame to AVOID — pure labor, no owned floor |

Notes worth keeping:
- **Bank ledger ≈ revision chain** is the single most *precise* technical correspondence in the whole space: double-entry accounting invented attribution-as-structure 500 years ago, which is exactly ADR-209's authored substrate. But banks are opaque (anti-inspectability) and their moat is lock-in (ESSENCE explicitly disclaims lock-in — "irreplaceable not because of lock-in but because of accumulation").
- **The doctor over tenure** is the strongest *cultural intuition* for "judgment that compounds and can't be automated away," and the follow-up lab is a perfect ground-truth analog (an outcome the patient cannot fake — Axiom 8). But health-locked, and the empty record is not zero-config valuable.

---

## 5. The structural finding

The table divides cleanly along one axis:

- **Impersonal general-purpose technologies** (telephone, PC, grid): ace C1/C2/C3/C7 (the floor + generality), fail C4/C5/C6 (the judgment seat).
- **Personal fiduciary relationships** (banker, doctor): ace C4/C5/C6 (the judgment seat), fail C7 and partly C1 (general-purpose + day-one floor).
- **The delegate/staff frame**: fails C1 outright — it is labor, not an owned floor; it is the incumbent commodity.

**No single object carries both layers, and the reason is structural.** Scale-and-generality and compounding-personal-judgment have never coexisted in one artifact because they are *historically opposed*:

- Generality **scales by being impersonal and judgment-free** — a phone line does not care who you call; an OS does not judge your programs. Impersonality is *why* it scales.
- Fiduciary judgment is **valuable by being personal and unscalable** — a doctor who has your 20-year chart, a banker who knows your account. The non-transferability is *why* it is valuable.

This is the deepest output of the re-examination: **YARNNN is attempting to fuse two things that have never coexisted.** The two enabling moves are exactly the two halves of its architecture:

- **Authored substrate** (ADR-209) makes the *personal context* scalable and portable — the thing that historically did not transfer now does, attributed and inspectable.
- **An occupant-rotating seat** (THESIS Commitment 2, Principle 14) makes *fiduciary judgment* instantiable in software — the thing that historically did not scale now can, calibrated against ground truth.

The fusion is the product. The metaphor must therefore be a fusion, not a single object.

---

## 6. The recommended frame: the floor (OS) + the fiduciary (seat)

A two-part metaphor that mirrors the two layers exactly, using YARNNN's already-canonical OS framing for the floor and a fiduciary professional for the seat:

> **The floor is an operating system** — your files, general-purpose, portable, always-on. (ADR-222 is already this, literally.)
> **The seat is a fiduciary** — a private banker / family doctor — judgment that compounds over tenure and refuses your bad impulse.
> **YARNNN is the first artifact where the two coexist.**

Why this frame and not a single replacement object:
- It keeps the **general-purpose** claim where it is structurally true (the floor / OS) — the half the operator most wants to position.
- It puts the **judgment seat** where no impersonal technology can carry it (the fiduciary) — the half the telephone failed.
- It names the fusion as the novelty, which is the honest differentiator and explains the ESSENCE v14 sequencing decision: *lead with the seat, prove with the substrate* — because the floor (OS) is the commoditized-but-necessary base, and the fiduciary seat is the half no general-purpose technology has ever carried.

One-liners to test in discourse (not yet canon):
- *"What if your operating system came with a fiduciary?"*
- *"The portability of a filesystem; the judgment of a trusted advisor — fused."*
- *"Your files, but they have a banker."*

Frames to explicitly reject:
- **"AI chief of staff / your AI employee"** — pure labor, no owned floor; the incumbent commodity (NARRATIVE Beat 1 / vocabulary rules).
- **"AI memory / second brain"** — collapses to the wiki degenerate form THESIS warns against (Layer 1 with no judgment loop).
- **Any single impersonal device** (telephone, PC alone, grid) — structurally cannot carry the seat (§5).

---

## 7. Re-run: the two core promises through the fused frame

**Layer 1 — the floor (the operating system):**
> *Your context is an authored, attributed, portable filesystem — present the moment you write anything, reachable from any AI you use, yours forever. Valuable before any program, any mandate, any agent.*

**Layer 2 — the generality (the fiduciary + the operation):**
> *Activate a program and the floor becomes a flow-complete operation: it watches what you declare, produces work in your absence, reconciles against what actually happened, and a judgment seat you author gets measurably sharper over tenure — and refuses your bad impulse when ground truth says so. Autonomous because flows 1→2 run without you; self-improving because flows 3→4 close against ground truth the agent cannot fake.*

The four-flow decomposition of the three adjectives:
- **General-purpose** = the floor (OS): domain-agnostic, model-agnostic, always-on.
- **Autonomous** = flows 1→2 run on cadence without the operator present.
- **Self-improving** = flows 3→4 — outcomes reconcile against judgment, written by the kernel mechanically, the agent cannot author its own grade (Axiom 8).

A program **is** a flow-declaration set (ADR-332 D3). The floor is the flow-agnostic *medium* the four flows inscribe on; the program is what *activates and completes* them.

---

## 8. Re-run: the four-flow feature scope (comprehensive, with build status)

### Layer 1 — the floor (the operating system). Flow-agnostic medium.

| Feature | Detail | Substrate root (ADR-320) | Interop exposure (ADR-311) | Status |
|---|---|---|---|---|
| **Authored, attributed substrate** | Every mutation content-addressed (`workspace_blobs`), parent-pointered (`workspace_file_versions`), required `authored_by` + message | all five roots | `ReadFile` returns content + attribution | **Implemented** (ADR-209) |
| **Revision chain** | Walkable authored history per path | all | `ListRevisions`/`ReadRevision`/`DiffRevisions` — *the killer interop primitive* (no competitor's agent-filesystem exposes an attributed, walkable chain) | **Implemented**; interop-exposed Phase 1 |
| **Five-root topology** | `governance/` · `constitution/` · `persona/` · `operation/` · `system/` — directory IS permission (`access(2)`) | — | foreign `WriteFile` gated to commons, lock-set DENYs governance + seat | Canon P1 done (ADR-320); P2–P5 in progress |
| **Interop face (portability)** | Kernel file+revision primitives in MCP mode, scoped to the commons; protocol-agnostic (MCP is first binding) | `operation/` + readable authored substrate | `ReadFile`·`ListFiles`·`SearchFiles`·`QueryKnowledge`·`WriteFile`(gated) | Gate **shipped** (`test_adr310_mcp_write_gate.py` 12/12); primitive rebuild phased (P1 substrate, P2 judgment rider, P3 shared-workspace deferred) |

**Floor positioning line:** valuable the instant you author anything — needs no program, no mandate, no Reviewer. The dial tone is there before any call; the OS runs before any app.

### Layer 2 — the generality. Scoped by the four flows.

**Flow 1 — Context in (perception).** *The fiduciary's standing watch on the slice of the world you declared.*
- **Three cells (DP26):** self-past (harvest/uploads, ADR-331) · self-present (live reads + operator push, **built**) · world-present (the perception field, ADR-335).
- **Mechanism:** watch declared (`substrate_abi.watches`) → recurrence reads on cadence → **distilled** into attributed observation substrate → wakes on threshold. Three-layer cut: Declaration (judgment, sovereign) · Observation contract (attributed, attested, dated, distilled) · Transport (commodity driver).
- **Substrate root:** `operation/{domain}/`. **Surface:** program home sections. **Interop:** observations are ordinary attributed substrate.
- **Status:** **Crawl-A shipped** (`substrate_abi.watches` slot, observation contract, conformance gate, FOUNDATIONS axiom-text). Crawl-B (kernel MCP client), Walk (registry resolution), Run (Reviewer proposes watches) — demand-pulled.
- **Positioning gold:** *reading the world is commodity; the declared/distilled/tenured/calibrated perception field is not.* Selection is judgment — the substrate's world-facing half (ESSENCE v14.1).

**Flow 2 — Work out (the acts).** *Producing the work; consequential acts wait for the fiduciary's sign-off.*
- **Mechanism:** deliverable specs + capabilities; artifacts compose lazily (ADR-333); consequential acts emit `ProposeAction`.
- **Substrate root:** `operation/`. **Surface:** Files (first-class, ADR-329) + Home "recent artifacts." **Interop:** composed artifacts + source sub-files readable.
- **Status:** mature (kernel-universal artifact acts; alpha-trader runs transactional acts via Reviewer-gated proposals).

**Flow 3 — Outcomes in (ground-truth intake).** *The statement / the follow-up lab — the world's verdict on your own acts, which the agent cannot fake.*
- **Mechanism:** `substrate_abi.ground_truth` slot (ADR-330); reconciler folds outcome candidates; attestation enum (`platform`/`operator`/`agent`).
- **Substrate root:** `operation/{domain}/_money_truth.md`. **Surface:** Home ground-truth hero (generic `GroundTruthHero`, program-bound e.g. `TraderMoneyTruth`). **Interop:** outcome substrate readable; the coupling term.
- **Status:** implemented for alpha-trader (money-truth); generalized as kernel slot. alpha-author declares `flows_na.perception` but must declare ground-truth.
- **Why it is the moat's spine:** Axiom 8 — written mechanically by the kernel from reality; the agent cannot author its own grade.

**Flow 4 — The loop (calibration).** *The fiduciary who learns your account/body over tenure and gets measurably better.*
- **Mechanism:** outcomes reconcile against the Reviewer's verdicts → calibration trail densifies (ADR-327 `mirror_calibration.py`); `by_signal` expectancy attribution.
- **Substrate root:** `persona/calibration.md` (the one system-write into the seat) + `operation/.../_money_truth.md` `by_signal`. **Surface:** Home judgment trail + Reviewer detail. **Interop:** Phase 2 of ADR-311 — reads gain a judgment-standing rider.
- **Status:** live in alpha programs; perception-under-calibration (does a watch earn its attention?) is Walk-stage.
- **This is "self-improving," precisely:** not "it learns from feedback" (every incumbent claims that) — outcomes the agent cannot author, reconciling against judgment, written by the kernel.

**Flow-completeness is the diagnosis vocabulary (ADR-332 D2):** when a workspace feels partial, enumerate its four flows; the missing one is the diagnosis. alpha-trader feels like an operation because all four run; a generic workspace has flow 2 + fragments of flow 1 — a document generator with a chat interface. This is the single most useful scoping tool: *which flow does this feature serve, and does the program declare it?*

---

## 9. Front-end wiring (the standing loop) through the frame

The FE is scoped by "mirror once, compose few" (ADR-340 / DP29) and maps onto layers + flows:

| Act (FE) | What it is | Flow / layer | Surface |
|---|---|---|---|
| **Decide** | Consent moments — queued proposals | Flow 2 gate (the fiduciary's sign-off) | Queue + attention center |
| **Read** | What happened since I last looked | Flows 3+4 reads | Feed + attention center |
| **Dwell** | Where the operation stands | All four flows, composed | Home |
| **Tune** | Adjust granted allowances | `governance/` (floor boundary) | System Settings |
| **Amend** | Constitution authorship | `constitution/` + `persona/` | Home constitution band → mirrors |
| **Setup** | Become operational = walk the program's flow declarations | activates the generality on the floor | `/setup` (Utilities tier) |

Two FE classes (both shipped, ADR-340 P1–P4): **mirror surfaces** (one ↔ one substrate concern — the `/proc` escape hatch, the floor's raw view) and **composition surfaces** (one ↔ one operator act — Home is the front page). **Attention is derived, never stored** (no `notifications` table). **Setup = flow-declaration walking** (ADR-332 D3): the onboarding sequence *is* "becoming operational," where the floor becomes a flow-complete operation under the fiduciary.

---

## 10. Pressure test of the fused frame (where IT strains)

1. **A two-part metaphor is heavier than a one-liner.** "OS + fiduciary, fused" needs a beat to land; a single device metaphor is stickier in a cold open. Mitigation: lead external surfaces with the *fusion one-liner* ("an operating system that came with a fiduciary") and unpack the two halves only when there's room. The two-part shape is a liability in a tweet and an asset in a deck.

2. **"Fiduciary" carries regulatory/legal weight.** In finance/health it is a term of art with duties attached; using it loosely could imply claims YARNNN does not make. Mitigation: use it as an *analogy of relationship* (independent, acts in your interest, refuses your impulse), explicitly not a legal-fiduciary claim. THESIS already uses "fiduciary at the proposal level" internally — keep that scoping.

3. **The OS half is over-used internally and may be invisible to laymen.** ADR-222 makes the OS framing literal and load-bearing for *architecture*, but a non-technical buyer may not feel "OS" as a floor. Mitigation: for layman surfaces, render the floor as "your files / your context that follows you," reserving "operating system" for technical/architecture register — same split THESIS already enforces between internal and external vocabulary.

4. **The fusion claim invites "so it's a bank/doctor for X?"** — re-domain-locking the general-purpose claim the frame was chosen to protect. Mitigation: the banker/doctor is the *seat*, never the *product category*; the product is the OS (general-purpose) that *has* a fiduciary seat. Hold the line: the fiduciary is a relationship analogy, not a vertical.

---

## 11. Open questions for discourse + proposed canon cascade (deferred)

**Open for discourse:**
- Is the fused frame the right external lead, or does it stay internal (a reasoning frame) while external copy keeps ESSENCE v14's seat-led / substrate-proof sequencing? (My lean: the fusion is the *internal reasoning frame* that *justifies* the existing external sequencing — it may not need to surface verbatim externally.)
- Which fiduciary reads best — private banker (precise ledger analog, but lock-in/opacity baggage) or family doctor (strongest tenure/independence intuition, un-fakeable-outcome analog)? Or keep both as register-dependent variants?
- Does "inherent base use case → accretion" deserve a named FOUNDATIONS Derived Principle, or is it sufficiently carried by ESSENCE's two-layer structure already?

**Proposed canon cascade (only after discourse converges — NOT in this doc):**
- `docs/ESSENCE.md` — possibly a "floor / generality" framing note + the fusion one-liner under Canonical Positioning (additive; the two-layer model already carries the substance).
- `docs/NARRATIVE.md` — Beat 3 could adopt the fusion frame for "Meet the Product"; vocabulary rules gain the fiduciary analogy + the explicit rejection of "chief of staff."
- `docs/architecture/FOUNDATIONS.md` — *only if* §11 discourse decides the inherent-base-use-case pattern warrants a Derived Principle (it may not — it is positioning, not architecture).
- New companion doc under `docs/architecture/` — a positioning architecture doc if the frame proves load-bearing across surfaces.

Until then: this is a Hat-B finding. It recommends; it does not amend.
