# ADR-364 — The Reflection Organ: close the intent→outcome loop, and let the agent learn from the gap

**Status**: **Accepted** (2026-06-24) — keystone fix shipped; reflection organ + envelope-fact scoped; Concerns 2/3 re-sequenced.
**Deciders**: KVK + Claude
**Dimensional classification** (Axiom 0): **Substrate** (primary — a new persona file `reflection.md` + one persisted join key) + **Mechanism** (the mechanical gap-join, a computed envelope fact, DP19) + **Purpose** (learning-from-the-gap, the tenure-improvement claim made substrate).
**Concern + sequence**: This **re-founds the three-concern split** ([`context-continuity-and-self-improvement-2026-06-24.md`](../analysis/context-continuity-and-self-improvement-2026-06-24.md)). It supersedes the *sequencing* of Concerns 2+3, not their substance: the missing primitive turned out to be **the intent→outcome join key, not a new rule field or a new seat.** Builds on [ADR-363](ADR-363-wake-context-handling.md) (Concern 1, settled).
**Supersedes (in part)**: **[ADR-361](ADR-361-verdict-rule-binding.md) + [ADR-362](ADR-362-inspector-auditor-seat.md)** — demoted from "the self-improvement path" to "optional deepenings, pulled only if the basic reflection loop proves it needs them." See §6. Neither is deleted; both are re-scoped as *deferred-and-conditional*.
**Reuses (no new taxonomy)**: ADR-330 (outcome attestation — the join's honesty floor), ADR-209 (authored substrate — `reflection.md` is attributed like every persona file), ADR-284 (the persona-file contract + standing_intent's forward half), ADR-281 §5 (judgment_log's backward half), ADR-254 (lowercase `.md` = LLM-facing narrative — what `reflection.md` is).
**Amends (the canon this completes)**: [`docs/architecture/persona-reflection.md`](../architecture/persona-reflection.md) — its "persona-as-living-accumulator" thesis was architecturally sound but operationally **open**; its own §1.5 audit finding (C2 self-coupling, A5) named the pathology — *"reflection verdicts accumulate without principles.md changes; surface looks stagnant despite calibration activity."* **The cause was the dropped `proposal_id` FK** (this ADR's D1 keystone). ADR-364 closes the loop that doc named. "Reflection" is therefore NOT a new term — it is the existing canonical concept (ADR-218 → persona-reflection.md), finally given its missing primitive. Per that doc's own rule ("every ADR that implements reflection cites + amends this doc in the same commit"), amended in this commit.
**Discourse base**: the 2026-06-24 missing-organ assessment (this session) — three Explore ground-truth passes establishing (a) standing_intent + judgment_log are clean single-purpose primitives, NOT conflated; (b) the gap is the *open loop between them*; (c) the loop is buildable today, blocked on one dropped FK.

---

## 1. The finding that re-founds the split (receipt-grounded)

The operator's instinct: *what if the eval AND the self-improvement both feel incomplete because the existing persona substrate is not primitive/comprehensive enough?* The from-scratch assessment (three Explore passes, this session) found the instinct **right about the symptom, wrong about the cause** — and the correction is the whole ADR.

**Wrong about the cause: the files are not conflated.** Ground truth (`reviewer_audit.py`, `reviewer_envelope.py`, FOUNDATIONS Axiom 2, GLOSSARY):
- `standing_intent.md` carries exactly ONE concern — forward intent ("what I'm watching for next"). Reviewer-written, overwrite-per-cycle, envelope-pushed (rendered every wake with the header *"What you were watching for last cycle"*).
- `judgment_log.md` carries exactly ONE concern — the backward audit trail ("what I decided"). Infrastructure-written (the material-outcome gate), append-only, machine-parseable.
- FOUNDATIONS Axiom 2 already names a *complete* 7-file persona set; this is not an accreted pile. Forward-vs-backward is the cleanest possible cut. **Shuffling files would be wrong.**

**Right about the symptom: the loop between the two files is open.** The substrate has *forward intent* and *backward audit* but **no join across intent → action → outcome → did-it-work**:
- `standing_intent` is forward only — it never records whether watching for X paid off.
- `judgment_log` records the *decision*, not whether it was *right* — and the material-outcome gate even drops routine stand-downs, so the log is blind to the suppression side.
- `calibration.md` exists as a canonical persona file (Axiom 2) but **nothing writes it** on the persona side — a vacant slot named after one narrow downstream use (tuning metrics) of a loop that was never closed.

**That open loop is why both Concern 2 and Concern 3 felt incomplete** — they are two views of the same missing thing. The eval (Concern 2) could only test "did the wake honor a spoon-fed note" (weak) because the strong claim — "did the agent reason from its accumulated *track record*" — has nothing to perceive, the track record being absent. Self-improvement (Concern 3) is fiction without it — you cannot revise a rule ground-truth falsified if nothing recorded that it was applied and what happened.

## 2. The actual missing primitive: one dropped join key

The mechanical gap-join needs three inputs connected. Ground truth (`ledger.py`, `base.py`, `trading.py`, `operator.py`):

| Input | What it is | Present? | Joinable? |
|---|---|---|---|
| **A — judgment_log entry** | what I decided (verdict) | ✅ | ✅ carries `proposal_id` (UUID) on decision blocks |
| **B — outcome** | what happened (P&L, attestation) | ✅ ADR-330 implemented | ❌ **`proposal_id` dropped before persistence** |
| **C — standing_intent** | what I intended (the watch) | ✅ envelope-read | ⚠️ one-way `MAY`-reference (ADR-284 D7) |

**The single point of failure is one dropped field.** The providers (`trading.py:152`, `operator.py:207`) set `proposal_id` on the `OutcomeCandidate`. `ledger.py` reads `signal_id` and persists it onto the event record — and **silently drops `proposal_id` one line away** (it was future work when written; ADR-361/362 didn't exist yet). So every outcome in `_money_truth.md` / `_signal.md` has *no FK back to the verdict that caused it.* The loop is severed by a 2-line omission.

This is the real correction to the operator's instinct, stated precisely: **the incompleteness was never in `standing_intent` or `judgment_log` as files — it was in the join between judgment and outcome, which was quietly never wired. The substrate has both halves and threw away the key that connects them.**

## 3. Decisions

### D1 — KEYSTONE: persist `proposal_id` on the outcome event (SHIPPED)

`services/outcomes/ledger.py::_apply_entries` now writes `event_record["proposal_id"]` when the candidate carries it (mirroring the existing `signal_id` carry). After this, every realized outcome joins back to the `judgment_log` verdict that caused it. Smallest possible change, highest leverage — **the intent→outcome loop is now closeable.** Mechanical, zero-LLM, no new table, no schema migration (the events array is already in `_money_truth.md` frontmatter). The narrative line (`_to_narrative_entry`) is deliberately NOT touched — a UUID in prose is noise; the organ joins on the structured events array.

### D2 — The mechanical gap-join is a COMPUTED ENVELOPE FACT, not a file (DP19, derived-not-stored)

The raw observed loop — *for each recent material verdict: what was decided, and what outcome (value + attestation) it produced* — is **reconstructable** from `judgment_log` (joined to outcome events by `proposal_id`). By Axiom 1, what is reconstructable is **not stored as authored substrate** (the same logic that dropped `action_outcomes` per ADR-195, made `wake_queue` transient per ADR-298, derived pace per ADR-327). So the gap-join is **assembled into the wake envelope**, NOT a persisted file.

**DP19 compliance (the load-bearing constraint — "the kernel does not compute for the prompt").** The envelope helper does a **bounded read-and-present**, the exact shape of the existing `_inventory_specs` discovery surface (`reviewer_envelope.py` — "a bounded substrate read, NOT state derivation"): it reads recent `judgment_log` verdicts, joins each to its outcome event by `proposal_id`, and **presents the raw joined rows** (verdict headline + outcome value + attestation + outcome label). It does **NOT** compute `matched`/`diverged`/`worked`/`failed` — that labeling is *new analytical state*, which DP19 forbids the kernel from deriving at prompt-assembly. **The kernel presents the join; the LLM judges the gap.** That division is also what makes it honest by construction: the kernel surfaces an ADR-330-attested outcome the agent cannot fake; the agent's *interpretation* (did my call work, what do I conclude) is the only judgment in the loop, and it's authored into `reflection.md` (D3) — never computed by the kernel.

### D3 — `reflection.md`: ONE new persona file — the agent's interpreted learning over an input it cannot edit

What persists is the *interpretation*, not the raw gap. "Last month I kept watching for X and it never paid; I've stopped" is **accumulated narrative over tenure** — not reconstructable from a single wake's join, prose-for-the-LLM (lowercase `.md`, ADR-254), the genuinely new thing. So **one new persona file `reflection.md`**, Reviewer-authored, **from the mechanical gap-fact it cannot edit.** This is the structural-independence ADR-362 wanted a whole new *seat* to get — obtained from a computed fact + one file, no new persona: the honesty comes from the *mechanical* layer (the gap the agent can't fake); the *reflection* is the agent's interpretation of an honest input.

`reflection.md` IS the moat's "learns from feedback / improves with tenure" claim made substrate — and it is **program-agnostic** ("what did I learn from the gap between intent and outcome" holds for trader, author, any program), which is why the name is `reflection`, not `calibration` (a metric word that pre-commits to one use), not `ground_truth_ledger` (names only the mechanical half, which is a fact not a file).

**Count: 1 new file (`reflection.md`), 1 new computed envelope fact (the gap-join), 0 new seats.**

### D4 — RETIRE `calibration.md` → `reflection.md`; INHERIT its system-writer slot (scoped migration, not a swap)

`calibration.md` was the symptom — a canonical persona file (Axiom 2) named after one narrow use of a loop never closed. **Correction to the first read of "nothing writes it":** ground truth shows the *persona-side LLM* never writes it, but **infrastructure does** — it is seeded at signup (`workspace_init.py`), reapplied (`substrate_reapply.py`), and is **the one named cross-class exception in the ADR-286 single-writer topology** (a "system" caller — the reconciler — writing a named path into `persona/`; `workspace_paths.py` CALLER_WRITE_POLICY notes). So retiring it is a **scoped topology migration, not a constant rename.**

This is actually a gift, not a cost: the reconciler→`calibration.md` system-writer path is *exactly* the "mechanical outcome write into persona" wiring the reflection organ needs. So `reflection.md` **inherits** that slot rather than rebuilding it. The design choice within D4: `reflection.md` is **Reviewer-authored** (the interpretation, D3), and the *mechanical* half is the **gap-fact in the envelope** (D2) — so the calibration single-writer EXCEPTION is **retired** (no system-caller writes `persona/reflection.md`; the Reviewer does, like `standing_intent`), which *simplifies* the single-writer topology by removing its one cross-class hole. The Axiom 2 persona set stays 7 files (one out, one in): `IDENTITY · principles · judgment_log · **reflection** · standing_intent · handoffs · OCCUPANT`. (`system/_calibration.md`, the ADR-327 D6 kernel-mirror, is a different file, untouched.)

**Migration sites (deliberate, not rushed into this ADR's pass)**: `workspace_paths.py` (constant + `PERSONA_FILES` + CALLER_WRITE_POLICY note), `workspace_init.py` (seed), `substrate_reapply.py` (reapply), `orchestration.py` (single-writer declaration), `primitives/workspace.py:1787` (reconciler-exception docstring), `test_adr286_single_writer_per_path.py` (the conformance test asserts the exception — it must assert its *removal*). This lands as its own step (§7), after the gap-fact + `reflection.md` author path exist.

### D5 — DEFER the rule dimension (`cited_rules`/ADR-361) and the independent seat (ADR-362); pull only on demonstrated need

The gap-join has two dimensions: **verdict→outcome** ("did my judgment work" — needs only `proposal_id`, buildable now) and **verdict→rule→outcome** ("which of my rules earn their keep" — needs `cited_rules`, ADR-361, Proposed-not-implemented). Apply the discipline ADR-363 D3/D5 just earned: **close the cheap, honest, buildable loop first; don't build the rule-calibration superstructure on a loop we haven't seen produce signal.** `reflection.md` carries the verdict→outcome loop now. If — and only if — it shows that rule-attribution is the missing depth, *then* `cited_rules` (ADR-361) earns its place, and *then* the independent-vantage question (ADR-362's seat) is worth re-opening. Building the seat first is the same error as adopting D3 before measuring: structure ahead of evidence.

## 4. The re-sequenced concerns (the real contribution)

The split stays three concerns; the *sequencing* is corrected so they're finally coherent:

| Concern | Was | Now |
|---|---|---|
| **1. Context handling** | settled (ADR-363) | unchanged — the floor |
| **2. Continuity eval** | "does the wake perceive a spoon-fed standing_intent note" (weak claim, nothing real to perceive) | **"does the wake reason from its accumulated reflection loop"** — now there's a *real* accumulated track record to perceive (the closed intent→outcome loop), so the eval has teeth |
| **3. Self-improvement** | a new Inspector seat (ADR-362) + verdict→rule binding (ADR-361), built up front | **the rule dimension + independent seat, DEFERRED and CONDITIONAL** — pulled only if the basic reflection loop proves it needs them |

The reflection loop (D1+D2+D3) *is* the substrate Concern 2 evaluates. The rule/seat dimension (ADR-361/362) *is* the genuinely-Concern-3 work, now optional.

## 5. What this does NOT do

- **No file shuffle.** `standing_intent` / `judgment_log` are clean primitives, untouched. The only topology change is `calibration.md` → `reflection.md` (D4).
- **No new seat.** The independent-vantage problem ADR-362 raised is real but solved here by the mechanical-fact / interpreted-file split, not by a second persona (deferred, D5).
- **No LLM in the join.** The gap-fact is mechanical (DP19); the agent only authors the *interpretation* from it.
- **No new table / migration.** `proposal_id` rides the existing events array in `_money_truth.md` frontmatter.
- **No forced rule citation.** `cited_rules` stays deferred (D5) — its Goodhart risk (ADR-361 D5) is real and unneeded until the basic loop demands the depth.

## 6. Disposition of ADR-361 + ADR-362

Both are **re-scoped, not deleted** — they were patching the loop from the rule-attribution end and inventing a seat, when the real break was the dropped FK:
- **ADR-361 (verdict→rule binding)** → **deferred-conditional**. Its `cited_rules` field is the *rule dimension* of the join (D5), pulled only when `reflection.md` shows rule-attribution is the missing depth. Status stays Proposed; sequence note updated to "gated behind ADR-364's basic loop proving it needs the rule dimension."
- **ADR-362 (Inspector seat)** → **deferred-conditional**. Its independent-vantage thesis is sound but premature: the mechanical-fact/interpreted-file split (D2+D3) gives the structural independence without a second seat. Re-open only if the reflection loop proves the Reviewer cannot honestly interpret its own gap-fact (the self-grading concern) *in practice* — which the attestation floor makes unlikely. Status stays Proposed; sequence note updated.

## 7. Implementation scope

**SHIPPED (D1):**
1. `services/outcomes/ledger.py::_apply_entries` — persist `proposal_id` onto the outcome event record. Import-clean; mirrors `signal_id`.

**SCOPED, not yet built (D2+D3):**
2. The gap-join computed fact — a `reviewer_envelope.py` helper that, per material verdict in `judgment_log`, joins to its outcome by `proposal_id` and emits the gap (intended/decided/outcome/matched|diverged|pending) into the wake envelope. Mechanical, DP19. (Buildable now — D1 supplied the join key.)
3. `reflection.md` — new persona path constant + persona-frame directive (the Reviewer authors it from the gap-fact each material cycle) + envelope render.

**SCOPED migration, deliberate step (D4):**
4. Retire `calibration.md` → `reflection.md` across the 6 live sites (D4 list), including removing its single-writer cross-class exception (a topology *simplification*). Lands AFTER step 3, so the conformance test flips from "assert the exception exists" to "assert it's gone" against a live reflection path.

**Canon cascade (this ADR's pass, docs-only):**
5. §8 documentation radius — FOUNDATIONS / GLOSSARY / seat-substrate / agent-composition / WORKSPACE / ADR-361+362 sequence notes. Done in this commit; the *code* migration (steps 2–4) is the next build.

**Build order**: keystone (D1, DONE) → gap-fact + `reflection.md` author path (steps 2–3) → calibration retirement migration (step 4) → *then* Concern 2's eval (which tests the reflection loop). The canon (step 5) leads so the build targets a written contract.

## 8. Documentation impact radius

- **`docs/architecture/persona-reflection.md`** — the canonical reflection framing this ADR completes (amended this commit — top-of-doc banner + the calibration→reflection boundary). "Reflection" is its term, not a new one; ADR-364 supplies the missing join key its §1.5 audit finding flagged.
- **FOUNDATIONS Axiom 2** — the persona-file set: `calibration.md` → `reflection.md` (done: the development-axis table now reads "develops through reflection", and the Reviewer's-identity file list swapped). The tenure-improvement claim now has substrate.
- **GLOSSARY** — new entry "Reflection" (the agent's interpreted learning over the mechanical gap-fact); retire/redirect "Calibration" (persona file).
- **`docs/architecture/reviewer-seat-substrate.md`** — the seat's file inventory: swap calibration→reflection; document the gap-fact as a computed envelope input.
- **`docs/architecture/agent-composition.md` §3.2.1** — the persona-frame partition: `reflection.md` is *interpreted learning*, distinct from `principles.md` (the rules) — note where reflection sits relative to the four-field rule shape.
- **`docs/design/WORKSPACE.md`** — persona/ root 7-file enumeration: calibration→reflection.
- **ADR-361 + ADR-362** — sequence-note updates (§6).
- **`workspace_paths.py`** — `PERSONA_REFLECTION_PATH` added; `PERSONA_CALIBRATION_PATH` retired from `PERSONA_FILES`.
- The discourse doc + this ADR re-found the three-concern sequencing; Concern 2's eval design (pending) now targets the reflection loop.

## 9. The honest bottom line

The operator asked the right question — *is the framing wrong?* — and the answer is: **the framing was wrong about where, not whether.** The persona files are clean primitives; the incompleteness was the *open loop between them*, severed by a single dropped join key. Closing it took a 2-line keystone, not a new file topology and not a new seat. The reflection organ (mechanical honest gap-fact + one interpreted file) gives the self-improvement claim its substrate AND gives Concern 2's eval something real to test — the same missing thing, two views, now closed. The rule dimension and the independent seat (ADR-361/362) drop to optional, pulled on demonstrated need. This is the cheaper-measurement-first / structure-after-evidence discipline ADR-363 earned, applied to the deepest unaddressed canon claim — self-improvement — and it lands as the smallest change that closes the loop.
