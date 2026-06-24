# Three separable concerns: context continuity · its eval · self-improvement-as-a-seat (the Inspector)

**Date**: 2026-06-24
**Hat**: B (external-developer / architecture + evaluation design) — a first-principles sketch, not an implementation. No code moved by this doc.
**Provenance**: follows the envelope-collapse arc (`the-envelope-collapse-2026-06-24.md`, governance-caching shipped `66a9090`). The re-assessment flagged self-improvement as the deepest unaddressed canon claim. The operator then (a) drew the eval-vs-architecture distinction, (b) refused to take filesystem-native context as de-facto truth, and (c) proposed self-improvement be carried by a NEW systemic seat — an Inspector/Auditor Agent — rather than bolted onto the Reviewer. This doc is the objective assessment of all three.
**Status**: Pre-design conviction, pressure-tested 2026-06-24. Probe-before-canon — nothing here ratifies until probed. The pressure-test surfaced BREAK 1 (the verdict→rule join does not exist) → split into two ADRs: **[ADR-361](../adr/ADR-361-verdict-rule-binding.md)** (the prerequisite verdict→rule binding — Reviewer-side) + **[ADR-362](../adr/ADR-362-inspector-auditor-seat.md)** (the Inspector/Auditor seat, activating deferred FOUNDATIONS Axiom 2 canon). Both Proposed.

> **Pressure-test record (2026-06-24)**: BREAK 1 — the judgment-calibration organ's core join (verdict→rule) did NOT exist: `judgment_log.md` records the rule only in free-form prose, and DP31/ADR-357 binds claims to external *Sources*, not to *rules*. Resolution: ADR-361 adds a structured `cited_rules` field (operator chose the DP19-clean structured option over LLM-inference). BREAK 2 — the material-outcome gate means stand-downs leave no lineage entry, so the organ is blind to suppression-side (false-negative) rules; stated as a known bound (ADR-361 D4 / ADR-362 §6), not elided. SURVIVED — attestation join (ADR-330 ✓), seat legitimacy (three-cell test ✓), D9 reconciliation ✓, structural-independence requirement ✓ (now more load-bearing). The breaks reshaped the organ and revealed the ADR-361 prerequisite; they did not kill the Inspector.

---

## 0. The three concerns, cleanly separated (and why they stay separate)

The original framing called this "two layers." The sharper frame the operator pushed it to is **three concerns**, each with a distinct owner, a distinct substrate, and a distinct eval. They are separated not by adding structure but by recognizing the writers already own distinct files, and imposing one directional rule.

| | **Concern 1 — Context continuity** | **Concern 2 — Continuity eval** | **Concern 3 — Self-improvement (the Inspector seat)** |
|---|---|---|---|
| **Owns the question** | Does a stateless wake reliably perceive its own prior state? Is substrate-read-back the right cross-wake memory — or should it accommodate API-native mechanisms, *while preserving the moat AND improving cost*? | Can we measure that perception? | Does accumulated judgment-quality evidence revise the rulebook — judged from an *independent vantage*? |
| **Substrate it owns** | perception files: `standing_intent.md`, `judgment_log.md`, `_schedule_index.md`, `_recent_execution.md` | none (a harness) | learning files: `_calibration.md` + a rule-track-record file; Inspector seat at `/workspace/inspector/` |
| **Writer (= concern owner)** | `reviewer_audit.py`, `kernel_mirrors.py` | snapshot/restore harness | a NEW Inspector occupant + judgment-calibration organ |
| **Eval claim** | "the wake reads back what it wrote" | "seed prior state → assert it's honored" | "seeded falsified rule → Inspector proposes the correction" |
| **Depends on** | nothing (it's the floor) | Concern 1 being *defined* | Concerns 1 + 2 being *stable* |

**The one rule that keeps them separate (the directional invariant):**
> Self-improvement reads perception substrate but never writes it; continuity never reads learning substrate. The flow is one-directional: **perception → learning → (gated) rule-revision.**

If learning ever wrote `standing_intent.md`, or `standing_intent` carried learning verdicts, the concerns re-fuse. That single rule is the whole separation. It is *already mostly true* in code — `reviewer_audit.py` (perception) and `mirror_calibration.py` (learning) are distinct writers; they only *look* fused because the wake envelope reads them together and the eval-reset wipes them together.

**Sequence (operator's, and correct): Concern 1 first, Concern 2 second, Concern 3 third — each over a stabilized prior.** Each step has a concrete stability gate; Concern 3 is *forbidden* to start until Concern 2 proves perception, because a learning loop over unread memory is fiction. That gating is what makes the separation *enforced*, not merely hoped.

---

## 1. Concern 1 — Context continuity, as an OPEN architectural evaluation (NOT a confirmation)

**Operator directive (load-bearing):** do not treat Axiom 1 (filesystem-native) as de-facto truth here. Stress-test whether the approach can and should be more accommodative to existing API conventions (sessions, memory tool, compaction, context editing) **while preserving the moat AND potentially improving token/cost efficiency** — these are not mutually exclusive (the governance-caching win this session already proved moat + API-native efficiency are complementary).

### 1a. What's true today (receipt-grounded)
- A wake is a **stateless LLM call**: `reviewer_agent.py:1369` builds a fresh `messages = [{...}]` every wake. `messages.append(...)` grows it only *within* one wake's tool-loop. **No cross-wake conversation, no retained context window, no Anthropic session.**
- The **only** cross-wake bridge is **authored substrate read-back** via the wake envelope. What a wake "remembers" = files it wrote last cycle and reads this cycle.
- This is the CC-analogue (CC re-reads CLAUDE.md + repo fresh each conversation) and the moat consequence is real: cross-wake memory lives in **authored, attributed, portable** substrate (ADR-209), not a provider blob.

### 1b. The honest stress-test (the part that must NOT assume the status quo wins)
The question is per-mechanism, not all-or-nothing. For each API-native primitive, the test is: *does it preserve the moat (authored/attributed/portable) AND improve cost/latency — or does it move memory-of-record into an unportable provider blob?*

| API mechanism | Moat-preserving? | Cost/latency? | Verdict to PROBE (not assume) |
|---|---|---|---|
| **Prompt caching** (governance block) | ✅ keeps substrate as truth; caches the *rendered* bytes | ✅ proven ~40% uncached-input cut this session | **Already adopted** — proof that moat + API efficiency compose. Precedent for the rest. |
| **Compaction** (within-wake) | ✅ summarizes a *single wake's* tool-loop, not cross-wake memory | ✅ wakes hit the 20-round ceiling — a real long-loop case | **PROBE**: adopt for long single-wakes as a transport optimization. Memory-of-record stays substrate. Strong candidate. |
| **Memory tool** (`memory_20250818`) | ⚠️ its *shape* (structured read/write dir) is what `persona/` already IS | neutral | **LIKELY NO as a mechanism** (we'd move memory into a provider-managed dir — unportable, unattributed). **YES as a discipline model** (one-lesson-per-file, consult-before-acting — how the agent should *use* `persona/`). |
| **Managed-Agents sessions** | ❌ retained server-side conversation state = unportable, unattributed memory-of-record | ✅ would remove substrate re-read cost | **PROBE-then-likely-NO**: directly contradicts substrate-portability. But the *cost* it would save (re-reading ~16k governance every wake) is exactly what prompt-caching already recovers WITHOUT the moat cost — so the cheaper, moat-safe path likely dominates. Worth measuring to confirm. |
| **Context editing** (prune stale tool results) | ✅ within-wake only | ✅ | **PROBE**: cheap, moat-neutral, pairs with compaction for long loops. |

**The framing for the doc/ADR (not yet decided):** the open question is *"which API-native mechanisms are moat-safe transport optimizations vs which would relocate memory-of-record off authored substrate."* The hypothesis (to be probed, not assumed) is that **caching + compaction + context-editing are moat-safe wins (within-wake / rendering layer), while sessions + the memory-tool-as-mechanism would move the moat off-substrate and are likely rejected — but only after measuring that the moat-safe path captures the same cost win.** The directive stands: re-derive this from probes, don't inherit the Axiom-1 default.

### 1c. Concern 1's deliverable
Not (yet) a code change — an **architectural evaluation** + the **continuity eval** (Concern 2) that proves the agent reliably perceives prior state under *whatever* mechanism wins. The eval is mechanism-agnostic: it tests perception, not the transport.

---

## 2. Concern 2 — The continuity eval (the floor's instrument) + the snapshot/restore harness

**Claim under test:** a wake reliably *perceives and acts on* its own prior-cycle substrate. Before "does it improve," prove "does it read what accumulated."

**Why separate from the behavioral (ADR-360) eval:** the behavioral eval *wipes* persona memory to isolate the wake (correct for *that* test). The continuity eval *seeds* prior state and checks it's honored — the opposite operation.

### 2a. The snapshot/restore harness (enables all three concerns' evals cleanly)
The current reset **destroys** persona memory (one-way `delete` of `persona/{standing_intent,judgment_log,calibration,handoffs}.md`). Replace with **checkpoint + restore**:
- `snapshot_persona(user_id) -> blob` — capture the persona files (+ revision heads).
- `restore_persona(user_id, blob)` — write them back.

Three replay modes over the same substrate, instead of one destructive reset:
- **isolated** (behavioral / ADR-360): restore to a *clean* snapshot — same isolation as today, reversible.
- **seeded** (continuity): restore to a *hand-authored* snapshot, fire once, measure prior-state honoring.
- **accumulating** (tenure / Inspector): never restore between runs — memory grows across N wakes.

Pure Hat-B harness improvement, no kernel change. **It is the tool that physically enforces the three-concern separation** — it can wipe perception while preserving learning, or vice versa, giving each eval its own clean substrate state. (Today's wipe takes all four files together — the exact conflation that started this thread.)

### 2b. The eval itself
1. **Seed**: `standing_intent.md` = "watching for the hedge-stack anti-pattern, +0/+1/+2 over last 3 pieces, trending up."
2. **Fire** one wake with substrate containing a 4th piece with a hedge-stack hit.
3. **Assert** the verdict *references the standing intent* (caught what it said it'd watch for, named the trend) — not "did it read the file" but "did prior state change the verdict."
4. **Negative control**: same wake, `standing_intent.md` wiped → verdict must NOT reference a trend it has no record of. The **delta** is the continuity signal.

**Pass:** seeded run produces a materially different, prior-state-grounded verdict vs the wiped control. **Fail (the silent regression):** identical verdict regardless of seeded state → the agent isn't perceiving prior substrate, and Concern 3 is dead on arrival. **This is the gate** for Concern 3. Cheap: 2 funded wakes.

---

## 3. Concern 3 — Self-improvement as a SEAT: the Inspector/Auditor Agent

The operator's reframe: rather than bolt a self-improving *loop* onto the Reviewer, create a **new systemic Agent** — an Inspector (a.k.a. Auditor) — that absorbs all self-assessment / meta-judgment, with its own wakes and a clean role boundary. First-principles assessment below.

### 3a. This is deferred canon, NOT a new invention
- **FOUNDATIONS Axiom 2 (line 213)** already names "**Auditor**, Advocate, Custodian" as *Future judgment archetypes* with substrate homes at `/workspace/{role}/`.
- **ADR-284** already wrote the standing-intent contract for "future systemic Agents at `/workspace/{role}/standing_intent.md`."
- **`orchestration.py:301`** has the registration slot ("Future systemic Agent archetypes (Auditor, Advocate, Custodian)").
- **CLAUDE.md** (Reviewer section) states future systemic Agents "will be additional persona-bearing members, registered in `api/services/orchestration.py`."

So the proposal **instantiates a seat the architecture was built to hold.** The work is activation + the organ it operates, not a structural invention.

### 3b. The FOUNDATIONS three-cell test (does it earn separate-seat status, or is it drift?)
FOUNDATIONS' design-drift test (Axiom 0): a mechanic must not span a dimension without necessity. A separate seat is justified **iff** it has a distinct **Purpose** AND a distinct **Trigger** AND a distinct **vantage**. The Inspector against all three:

| Dimension | Reviewer (existing seat) | Inspector (proposed seat) | Distinct? |
|---|---|---|---|
| **Purpose** | Render a verdict on a *proposed action / live operation* (forward-looking, fiduciary at proposal level) | Assess *judgment-quality against ground-truth* + propose rulebook revisions (backward-looking, fiduciary at meta level) | ✅ categorically different objects |
| **Trigger** | Event-fired — a proposal arrives, a draft is ready, the market moves | Cadence-fired on accumulated evidence — "every N judgments / weekly, review the track record" | ✅ different wake source + rhythm (this is the strongest signal — it genuinely wants its own wakes) |
| **Vantage** | Reasons over *live proposals + current substrate* (one decision, forward) | Reasons over *`judgment_log.md` + ground-truth outcomes* (a corpus of past decisions, backward) | ✅ different input, different object |

**Three distinct cells → by FOUNDATIONS' own test, a legitimate separate seat, not drift.**

### 3c. Reconciling with ADR-320 D9 ("a single judgment seat per workspace")
D9 chose one seat *spanning all operations*. The apparent conflict dissolves on inspection: **D9 is about judgment ON the operation** (you don't want two reviewers disagreeing on the same trade — operational judgment must be singular and accountable). The Inspector judges **the Reviewer's record, not the operation** — a different object entirely. One seat judges the operation; one seat judges the judgment. D9 and the Inspector are compatible; the ADR must state this explicitly so the "single seat" canon isn't read as blocking it.

### 3d. The independence the design MUST earn (the one real failure mode)
The risk that would *kill* this: a second seat that reads the same files, reasons with the same model, and writes the same substrate = a costly duplicate, not a separation. The "single seat" instinct exists to prevent exactly that. The Inspector's independence must be **structural, not nominal**:
- **Input is outcomes**, not proposals — ground-truth attestation (`platform|operator|agent`, ADR-330), the reconciled record, not the live decision.
- **Object is the Reviewer's track record** — `judgment_log.md` joined to outcomes — not the operation.
- **Output is *proposals* to the Reviewer's rulebook** (`principles.md`), gated through the existing permission surface (ADR-307) — *never self-applied, never silently mutating the Reviewer's substrate.* This breaks the self-referential awkwardness ADR-295 has always carried (the Reviewer amending its own rules in the same breath it applies them).
- **Its own seat substrate** at `/workspace/inspector/` (IDENTITY + principles + standing_intent + its own judgment_log), per the `/workspace/{role}/` canon — so it accumulates its *own* tenure as a meta-judge.

If the Inspector merely re-runs the Reviewer's reasoning, it fails this test and should not ship. The design earns the seat by reasoning over a *different object* (outcomes-vs-record) with a *different cadence* than the Reviewer ever does.

### 3e. The organ the Inspector operates (what was missing all along)
The judgment-calibration mirror, now owned by the Inspector instead of bolted onto the Reviewer: a **mechanical (zero-LLM, DP19) rule→outcome attribution pass** that, per material judgment in `judgment_log.md`:
- resolves the **rule(s)** the verdict cited (citation discipline already binds verdicts to authority — ADR-345/DP31),
- joins to the **ground-truth outcome** that judgment produced (attestation field, ADR-330),
- accumulates a **per-rule track record** ("anti-slop §3.2: 12 applications, 9 confirmed, 0 falsified" vs "cadence-flag §4: 3 applications, 0 confirmed, 2 falsified"),
- writes it to the Inspector's substrate.

The Inspector then wakes on cadence, reads the track record, and where a rule is falsified by ground-truth, **proposes** a revision to the Reviewer's `principles.md` — floor-gated (ADR-342/343: rules tighten on falsification, never loosen to produce more). This gives the Reviewer's self-amendment authority a *driver from an independent seat*, which is cleaner than self-amendment.

### 3f. The tenure eval (Concern 3's instrument, accumulating mode)
**Claim:** the Inspector self-corrects a seeded-falsified rule over tenure, and *only* when its evidence organ is present.
1. **Seed** a rule in `principles.md` that ground-truth has *already falsified* (the seeded track record shows 0 value across 5 applications).
2. **Fire N Inspector wakes** in accumulating mode (no restore).
3. **Measure** whether the Inspector *proposes the correction* (a `principles.md` revision proposal attributed `inspector:`) in the direction ground-truth points.
4. **Negative control**: same N wakes with the track-record organ withheld → no correction → confirms causation, not drift.

**Pass = the first observation of self-improvement** — the moat's headline claim, currently unproven, now carried by a seat that earns its independence.

---

## 4. Sequence (probe-before-canon; each gated)

1. **Concern 1 architectural evaluation** — the moat-safe-vs-off-substrate per-mechanism stress-test (§1b). Output: a decision on compaction/context-editing adoption, a documented reject-rationale for sessions/memory-tool-as-mechanism. *(analysis; possibly small Hat-A for compaction)*
2. **Snapshot/restore harness** (§2a) — pure Hat-B, enables every eval below. *(no canon)*
3. **Continuity eval** (§2b, seeded mode) — prove the agent perceives prior substrate. **GATE**: if it fails, fix perception before anything else. *(no canon)*
4. **Inspector seat ADR** — activates deferred Axiom 2 canon: `/workspace/inspector/`, its Purpose+Trigger+vantage, the D9 reconciliation, the structural-independence contract (§3b-d). *(Hat-A, ADR — canon move)*
5. **Judgment-calibration organ** (§3e) — the mechanical rule→outcome attribution mirror the Inspector operates. *(Hat-A)*
6. **Tenure eval** (§3f, accumulating mode) — the first attempt to *observe* self-improvement. **GATE**: this is the claim. *(no canon)*
7. **Canon close** — FOUNDATIONS amendment naming the closed loop (Inspector → rule-revision-proposal → Reviewer), only after the tenure eval shows correction. *(canon last)*

---

## 5. The honest bottom line

- **Concern 1 (context)** is reframed from "confirm filesystem-native" to **an open architectural evaluation** — per the operator's directive that moat-preservation and API-native cost efficiency are not mutually exclusive (governance-caching already proved it). Probe each mechanism; don't inherit the Axiom-1 default.
- **Concern 2 (eval)** is sound as premised — the work is the snapshot/restore harness + a seeded continuity eval, the gate for everything downstream.
- **Concern 3 (self-improvement)** is reframed from "a loop bolted onto the Reviewer" to **a new Inspector/Auditor seat** — and on first-principles assessment this is *stronger*: it activates deferred Axiom 2 canon, passes FOUNDATIONS' three-cell separate-seat test (distinct Purpose + Trigger + vantage), reconciles with ADR-320 D9 (judges the judgment, not the operation), and breaks the self-referential awkwardness of the Reviewer amending its own rules. The single hard constraint: the Inspector's independence must be **structural** (different object, different cadence, gated proposals to the Reviewer's substrate — never self-applied), or it's a costly duplicate. The design earns the seat by reasoning over outcomes-vs-record, which the Reviewer never does.

The three concerns separate cleanly because the writers already own distinct files and one directional rule holds (perception → learning → gated revision). The Inspector seat is the architecture *finally placing self-improvement where it belongs* — its own seat, its own wakes, its own tenure — rather than as a meta-loop the operational judge runs on itself. That is the cleaner seat↔agent↔system separation the operator intuited.
