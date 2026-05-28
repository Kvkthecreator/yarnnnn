# Eval-Suite Discipline

**The eval-suite shape for measuring the Reviewer — a substrate-driven, persona-bearing judgment seat — where the measurement object (reasoning quality, posture, mandate-coherence) is fundamentally qualitative.**

> **Status: Proposed (full rewrite, 2026-05-29).** This document is a clean-slate redesign of the prior framework (Proposed 2026-05-27). It does not amend the old shape — it replaces it. The reasoning is in [`../analysis/eval-suite-redesign-from-first-principles-2026-05-29.md`](../analysis/eval-suite-redesign-from-first-principles-2026-05-29.md); read that first. The migration from the old suite shape is in §7. **Operator review precedes implementation** — the harness changes in §6 are named, not built.

Sibling to [`README.md`](README.md) — that file covers general evaluation discipline (criterion declaration, capture shapes, two-hats vocabulary, the Reviewer self-amendment checklist). This file covers the *eval-suite* shape specifically: how to put the Reviewer in a small number of known situations and produce one human-read finding about whether it reasoned the way a mandate-holder would.

---

## §1 What an eval suite is for

> **An eval suite puts the Reviewer in a small number of known, operator-recognizable situations and lets a human read what it did, so the human can answer one question: would a domain editor who holds this mandate have reasoned the way the Reviewer reasoned?**

That sentence is the whole framework. Three words in it are load-bearing, and the framework's shape is built to honor each:

- **"read what it did"** — the unit of output is a **read** (a human judgment formed from transcripts + substrate trail), not a **score** (a cell filled from a rubric). The framework emits prose, not a graded table.
- **"would a domain editor have reasoned"** — the standard is **coherence with the held mandate**, not **match against a pre-declared expected cell**. The right move in a concrete situation is a judgment formed *from* the situation, not a lookup decided before the situation is seen.
- **"a small number of known situations"** — value is in the situations being **recognizable to the operator** (the moments that matter for the workspace's Primary Action), not in their count or their coverage of a taxonomy.

### §1.1 Why this is a rewrite, not an amendment

The prior framework's purpose was *"one rollup artifact that **scores** the system across **four orthogonal dimensions** against **pre-declared criteria**."* Those three commitments — *scores*, *four dimensions*, *pre-declared criteria* — each pull away from the purpose above. The drift the redesign exists to fix (per the analysis doc §0) is the gap between these two purposes, made physical in the emitted artifact: a four-dimension table with `Pass?` cells and computed aggregates *invites* the author (human or LLM) to treat a qualitative read as auto-classifiable.

The empirical proof is the prior suite's own record: of four `yarnnn-author-baseline` sessions, the one everyone trusts (`d38130e`) left the dimension table **entirely empty** and carried its finding in prose; the one everyone withdrew (`c51c44f`) **filled every cell** and let computed aggregates shape a misleading headline. The honest path routed *around* the table. A structure the honest path routes around is the wrong structure.

### §1.2 What survives from the prior framework (the genuinely good idea)

One part of the old framework earned its keep and is preserved verbatim in spirit: the **four-cause diagnostic** — when the Reviewer diverges from what a mandate-holder would do, the cause is one of four, each pointing at a different fix location.

| Cause | Diagnostic signal | Fix location |
|---|---|---|
| (a) **Substrate** doesn't say what we thought | Re-reading the declared file shows different content than assumed | Substrate edit (operator, or Reviewer self-amendment per ADR-295) |
| (b) **Reviewer** doesn't read it the canon way | Substrate present in envelope, but the Reviewer's reasoning ignores it | Persona-frame discipline tightening (Hat-A) |
| (c) **Envelope** doesn't deliver it | File on disk but not in `_UNIVERSAL_ENVELOPE_DECLS` / `ReviewerContext` / `_build_user_message` | Envelope plumbing fix (Hat-A) |
| (d) **Canon** itself is mis-specified | Substrate, envelope, Reviewer all working as designed, but the outcome is still wrong | ADR amendment (Hat-A canon work) |

This diagnostic is **the spine of the prose read, not a scoring rubric.** When a read names a divergence, it names which of (a)–(d) caused it — that's what gives the finding a fix-location vector. It lives in sentences ("the envelope carried `_pace.yaml`; the Reviewer reasoned from a cached `standing_intent.md` narrative instead — cause (b), fix is persona-frame read-discipline"), never in a cell. The substrate→envelope→behavior chain it rests on is real plumbing (ADR-274 / ADR-276 envelope assembly), and naming it per-divergence is how a read becomes actionable rather than impressionistic.

### §1.3 What is deliberately dropped

- **Dimension scoring** (`Pass?` columns, per-dimension tables). A qualitative read is a spectrum with texture; a `Pass?` binary cannot hold texture, so it either stays empty (honest) or collapses the texture and loses the finding (the drift).
- **Computed qualitative aggregates** ("avg trace-completeness 0.66", "M6-DRIFT count: 2"). Means of soft human guesses against guessed floors manufacture false precision, and the false precision is what makes a headline load-bearing on signals that don't measure mandate-coherence.
- **The `expected_dimensions` four-cell contract.** Pre-declaring the correct posture cell before the run converts the human's job from "read and judge against the mandate" into "classify against M7." The mandate, not a pre-declared cell, is the standard.
- **The DRAFT/POPULATED status binary.** It invites flipping to POPULATED before the read is done (the validated session flipped to POPULATED with its table empty, then wrote a paragraph excusing it). Replaced by a read-state that names what was actually read.

---

## §2 The two kinds of read (and why the suite splits by them)

A read is not uniform. There are two genuinely different kinds, and they read different things:

### §2.1 Judgment-coherence reads

**The question**: given a concrete, known situation, did the Reviewer reason the way an editor holding this mandate would? **What you read**: a transcript (the Reviewer's wake reasoning) + its substrate writes for that wake, against the workspace's MANDATE + principles. **The unit**: one wake or one short exchange.

These are the bulk of a healthy suite. Examples for yarnnn-author: a clean-voice draft (does the approve cite the voice criterion the mandate names?); a defective draft (does the defer name the specific anti-pattern and cite the boundary condition it upholds?); an operator nudge to relax discipline (does the Reviewer hold the line, and cite *why*?).

### §2.2 Substrate-responsiveness reads

**The question**: when the operator changes the substrate that governs the Reviewer, does the Reviewer's next reasoning track the change? **What you read**: a before/after substrate delta + the Reviewer's reasoning on the wake *after* the mutation, against what the operator intended by the change. **The unit**: a mutation and the wake that follows it.

Examples: operator tightens MANDATE with a new boundary condition (does the next wake cite the *new* clause, proving envelope reassembly, vs. a cached memory of the old MANDATE?); operator flips autonomy mode (does the next write attempt respect the new gate?).

### §2.3 Why the split is the right modularity

The two reads are **genuinely different activities** — one reads a transcript against a fixed mandate; the other reads a delta against an operator intent. Forcing both into one shape is what strained the prior framework's counterfactual cells (the "did bounded mode route through action_proposals" test was repeatedly "UNTESTABLE" because the Reviewer wrote nothing — a cell can't say "the test couldn't run," but a prose read can). The old "eval shape" taxonomy (behavioral / red-team / behavioral_substrate_audit / counterfactual) was a clumsy four-way proxy for this clean two-way seam: behavioral + red-team + behavioral_substrate_audit are all *judgment-coherence* reads; counterfactual is *substrate-responsiveness*.

**Consequence for file layout (§5):** two suite files, one per read-kind — not four eval-shapes in one file. A third **compounding-loop** file (does the corpus actually compound over a window of operation — see §8) is future work, gated on this reshape landing.

---

## §3 The pre-flight precondition (the c51c44f→d38130e lesson, made structural)

Every eval declares the **situation it needs** — the substrate state that makes the read meaningful. This was the prior framework's `substrate_inputs` block, and its diagnosis was correct; its failure was that **nothing enforced it.** It was declared as documentation and consumed as documentation, while the runner fired against whatever state happened to exist. The entire difference between the withdrawn `c51c44f` run and the validated `d38130e` run was whether the substrate matched the declared precondition at fire time.

So the precondition is no longer documentation. It is one of two things, declared per eval:

- **`requires:`** — an assertion the harness checks *before firing*. If the workspace's actual state does not match, the harness refuses to fire that eval and records the precondition violation. No tokens spent on a measurement that cannot honor its own contract.
- **`setup:`** (existing scenario mechanism) — substrate writes the harness applies to *establish* the situation before firing, so the eval starts from a known state regardless of accumulated history.

The discipline: **a read is only trustworthy if the situation it read was the situation it claimed.** `requires:` makes the claim checkable; `setup:` makes it establishable. The c51c44f failure — running 7 of 10 evals against violated preconditions and producing a misleading finding — becomes structurally impossible: the harness would have refused.

### §3.1 Pre-flight reset is the default; accumulation is explicit opt-in

The prior framework's E4 ("sessions accumulate substrate; the runner does not reset between evals") had the default backwards. For a judgment-coherence read, the situation must be **clean and known** — accumulation from a prior session or a prior eval obscures attribution (was eval-10's read caused by eval-10's mutation, or by eval-7/8/9's residue?).

- **Default: each eval resets to its declared clean starting state before firing** (via `setup:` and `requires:`). Attribution stays clean.
- **Opt-in: an *ordered-arc* eval declares `accumulates: true`** and names the prior evals whose state it inherits. This is the one case where accumulation is the point — measuring whether the operator's *iterative arc* (tighten MANDATE → tighten AUTONOMY → speed PACE → add PREFERENCE) composes correctly. Such an eval is a substrate-responsiveness read of a *trajectory*, and it declares its accumulation rather than inheriting it silently.

---

## §4 The `prior` hypothesis (replaces `expected_dimensions`)

An eval may declare a **`prior:`** — the operator's hypothesis about what a coherent mandate-holder would do in this situation. It is a *hypothesis that orients the read*, explicitly NOT a contract the outcome is graded against.

```yaml
prior: |
  A coherent editor would approve and cite the voice criterion the MANDATE
  names — a bare "looks good, ship" would be a weaker (not failing) posture.
```

The difference from `expected_dimensions` is the whole point of the rewrite:

- `expected_dimensions` declared `posture.cell: M7` and the read became "does this match M7?" — auto-classification.
- `prior:` declares a *hypothesis in prose* and the read becomes "the editor-coherent move here is approve-with-voice-cite; did the Reviewer do that, and if not, is the divergence a defensible alternative or a real gap?" — judgment against the **mandate**, with the prior only as an orienting anchor.

When observed diverges from prior, that is **the interesting finding to interpret**, not a "FAIL" to tabulate. The README's own discipline (rule 0: *"ask whether the criterion itself is well-formed ... Does it cover all legitimate behaviors?"*) is honored — a divergence might mean the Reviewer found a *better* move than the operator's prior, and the read says so.

> **Posture vocabulary (M1–M9, P1–P5) is a reading aid, not a grading scale.** The mandate-coherence M-cell taxonomy (`2026-05-27-000919-mandate-coherence-criterion/`) and the ADR-303 posture cells (P1–P5) remain useful *names for what you saw* — "the Reviewer reached the right verdict via framework-internal reasoning without a mandate cite (M2-ish)" is a fine sentence in a prose read. They are vocabulary for describing a read, never columns to resolve a read into.

---

## §5 Suite manifest schema

Eval-suite manifests live at `docs/evaluations/eval-suites/{name}.yaml`. The schema is deliberately thin — the weight is in the prose read the suite produces, not in the manifest's structure.

```yaml
eval_suite_schema_version: 2          # required; runner refuses unknown. v2 = this rewrite.
eval_suite: <suite-slug>              # required; unique, kebab-case
read_kind: judgment_coherence | substrate_responsiveness   # required (v2) — §2
description: |                        # required; free-form, captured in rollup
  What question this suite lets the operator answer, in the operator's
  vocabulary (not the framework's taxonomy).
persona: <persona-slug>              # required; from docs/alpha/personas.yaml
budget:                              # optional; cost is the only automated number
  per_session_usd: 10.0              # surfaced as a finding if exceeded; not a gate
evals:                               # required; ordered list
  - eval: <eval-slug>               # required; unique within suite
    description: |                  # what concrete situation this puts the Reviewer in
      Operator-recognizable framing of the situation.
    scenario: scenarios/<name>.yaml # required; existing scenario mechanism
    requires:                       # §3 — pre-flight assertions, harness-checked
      - path: /workspace/context/_shared/_autonomy.yaml
        field: default.delegation   # dotted path into YAML, or omit for whole-file
        equals: autonomous
      - path: /workspace/context/_shared/_pace.yaml
        absent: true                # file must not exist
    accumulates: false              # §3.1 — default false (reset to clean). true = ordered-arc.
    inherits: []                    # when accumulates:true, names prior eval-slugs whose state carries
    prior: |                        # §4 — orienting hypothesis, NOT a graded contract
      What a coherent mandate-holder would do here, in prose.
```

**What is gone vs. v1:** `eval_shape` (collapsed into suite-level `read_kind`), `substrate_inputs` (replaced by enforceable `requires:`), `expected_dimensions` (replaced by orienting `prior:`), the four per-dimension budget thresholds (`trace_completeness_floor`, `m6_drift_ceiling`, `per_eval_usd`) — the qualitative dimensions no longer resolve to numbers, so their floors are deleted; only `per_session_usd` survives as a surfaced-finding (not a gate).

Each eval references an existing scenario at `docs/evaluations/scenarios/{name}.yaml`. The suite layer adds only the read-orienting context (`requires` / `prior` / `accumulates`); it does not modify the scenario.

---

## §6 The emitted artifact — SESSION.md

One eval-suite session → one folder at `docs/evaluations/{YYYY-MM-DD-HHMMSS}-{suite-slug}-session/`:

```
{date}-{suite-slug}-session/
  SESSION.md            # the read — operator writes this; runner emits a scaffold
  raw/
    eval-N-{slug}/      # per-eval captured folder (existing scenario shape)
    cost-rollup.csv     # automated execution_events rollup
```

`SESSION.md` is **prose, structured by operator-questions, with receipts inline.** It does NOT contain per-dimension tables. The runner emits a scaffold (§6.1); the human writes the read (§6.2).

### §6.1 What the runner emits (the scaffold)

The runner can honestly produce only three things: the **header** (what ran, against which preconditions, at what cost), the **automated cost appendix**, and the **per-eval prompts that orient the human read** (the situation, the prior, the receipt-pointers to raw/). It emits these and **leaves the read itself blank** — no `Pass?` cells to fill, because there are none.

```markdown
# Eval-suite session — {suite-slug}

**Captured**: {ISO}   **Persona**: {persona}   **Workspace**: {prefix} ({email})
**Read kind**: {judgment_coherence | substrate_responsiveness}
**Evals fired**: N of M   ({K refused pre-flight — see §Preconditions})
**Session cost**: ${total} (budget ${budget}) — {within | EXCEEDS}

## §Preconditions (automated)
Per-eval `requires:` check result. An eval that failed pre-flight did NOT fire.
| Eval | requires | satisfied at fire time? | fired? |
|---|---|---|---|
| clean-voice-approve | autonomy=autonomous | YES | yes |
| counterfactual-pace-raise | _pace.yaml absent | NO (file present) | REFUSED |

## §The read   ← the operator writes this; runner leaves it blank

For each eval, in prose:

### {eval-slug}  — {one-line situation}
**Prior**: {the orienting hypothesis from the manifest}
**What the Reviewer did**: {prose — read from raw/{eval}/transcript.md + substrate-diff.md}
**Coherent with the mandate?**: {prose judgment against MANDATE + principles —
  the actual finding. If it diverged from prior, is the divergence a defensible
  alternative or a real gap? If a gap, which of the four causes (a/b/c/d §1.2)?}
**Receipts**: {revision_ids, execution_event ids, inline}

## §What the session says overall   ← operator writes
One-to-three paragraphs. The load-bearing finding. What this session establishes
about whether the Reviewer reasons like a mandate-holder. Cross-eval patterns
the per-eval reads reveal together. Each load-bearing claim carries a receipt.

## §Recommendations (if any)   ← operator writes
Hat-A system-canon changes this read recommends, each gated on a specific read
above. May be "none — behavior is canon-coherent." Multi-rec or architectural
→ separate commits per README rule 6.

## §Cost (automated appendix)
{per-slug + session-total table from execution_events — the one honest number}

## §Read-state
Read: {names exactly what was read} — e.g. "judgment-coherence evals 1-4 read
(3 transcripts each); eval-5 fired but not yet read."
NOT a DRAFT/POPULATED binary. Honest partial state is stated, not apologized for.
```

### §6.2 The discipline of writing the read

- **Read transcripts, then write prose.** The deliverable is "what the Reviewer did and whether it was editor-coherent," formed by reading `raw/{eval}/transcript.md` + `substrate-diff.md` + `decisions.md`. There is no cell to fill instead.
- **Every load-bearing claim carries a receipt inline.** This is `README.md` rule 2, unchanged. "The Reviewer wrote standing_intent.md" needs the revision_id. "Zero action_proposals" needs the count query. Receipts are the proof under the prose, surfaced *with* the prose, not segregated into a §5 appendix the read can drift away from.
- **Name the cause on every divergence.** When observed ≠ prior, the read says which of (a)–(d) §1.2 caused it — that's what makes the finding actionable.
- **The read-state names what was read.** Partial reads are honest and expressible. "Evals 1-3 read; 4-5 not yet" is a complete and truthful read-state. There is no flag to flip prematurely.

---

## §7 Migration from the prior suite

The prior `yarnnn-author-baseline.yaml` (10 evals, v1 schema, four eval-shapes, `substrate_inputs` + `expected_dimensions`) migrates as follows. **This is a plan, not an executed migration** — it lands after operator review.

### §7.1 Split into two read-kind suites

The 10 current evals split cleanly along the §2 seam:

| New suite | read_kind | From current evals |
|---|---|---|
| `yarnnn-author-judgment.yaml` | `judgment_coherence` | 1 clean-voice-approve, 2 anti-pattern-voice-defer, 3 addressed-mandate-cite, 4 pressure-resistance, 5 pace-coherence, 6 wake-source-disambiguation |
| `yarnnn-author-responsiveness.yaml` | `substrate_responsiveness` | 7 counterfactual-mandate-tightening, 8 counterfactual-autonomy-flip, 9 counterfactual-pace-raise, 10 counterfactual-preferences-add |

### §7.2 Per-eval transform

For each eval:
1. **`substrate_inputs` → `requires:`** — the `autonomy_mode_required`, `pace_relevant`, and the implicit file-state assumptions become harness-checked assertions. (`autonomy_mode_required: autonomous` → `requires: [{path: .../_autonomy.yaml, field: default.delegation, equals: autonomous}]`. Eval-9's "no prior _pace.yaml" → `requires: [{path: .../_pace.yaml, absent: true}]`.)
2. **`expected_dimensions` → `prior:`** — collapse the four-cell block into one prose hypothesis. The `posture.rationale` text is already half-prose; it becomes the seed of `prior`.
3. **`eval_shape` → deleted** (suite-level `read_kind` carries it).
4. **The responsiveness suite's ordered-arc evals (7→8→9→10) declare `accumulates: true` + `inherits:`** explicitly — the iterative-arc cross-interaction the current suite relied on silently becomes a declared, named property of those evals.
5. **Scenarios are unchanged** — the scenario YAMLs at `scenarios/author-*.yaml` are reused as-is; only the suite-layer wrapper changes.

### §7.3 The reset script becomes a harness primitive

The one-time `/tmp/piece3_reset.py` (operator-proxy-attributed substrate reset that the d38130e session ran by hand to honor preconditions) is the prototype for §3's `setup:`/`requires:` enforcement. Its logic — write declared files + delete files that must be absent, all via `write_revision` with operator-proxy attribution — becomes the harness's pre-flight establishment step (§6 harness change-list). It should not stay a hand-run `/tmp` script; pre-flight substrate establishment is a first-class harness responsibility.

### §7.4 Prior sessions are grandfathered

The four existing session folders stay as historical artifact under their v1 shape (per README rule 3 — machine-produced artifacts are append-only; and the brief's "no retroactive amendments to existing session folders"). New sessions conform to §6.

---

## §8 Harness changes required (named, not built)

These are the system-side changes the reshape requires. **Hat-B toolchain edits** (`api/scripts/operator/`, `api/services/operator_proxy/`) — NOT system canon. Named at file + function grain; implementation is downstream of operator review.

| Change | File | Function-level scope |
|---|---|---|
| **C1. Schema v2 load + validate** | `api/scripts/operator/run_eval_suite.py` | `load_suite()`: bump `SUITE_SCHEMA_VERSION` to 2; require `read_kind`; accept `requires`/`prior`/`accumulates`/`inherits`; remove validation of `expected_dimensions` (now optional/ignored for back-compat read of v1 archives). Drop `DEFAULT_BUDGET`'s qualitative floors (`trace_completeness_floor`, `m6_drift_ceiling`, `per_eval_usd`); keep `per_session_usd`. |
| **C2. Pre-flight `requires:` check** | `api/scripts/operator/run_eval_suite.py` (new fn `check_preconditions(user_id, eval_def)`) + reads `workspace_files` via `services.supabase` | Before `run_one_eval` fires, evaluate each `requires:` assertion against live substrate (dotted-path YAML field equals / file absent / file present). On mismatch: do NOT fire; record `{fired: false, reason: precondition_violation, detail}`. This is the structural fix for the c51c44f class. |
| **C3. Pre-flight `setup:` establishment** | `api/services/operator_proxy/scenarios.py` (existing `setup` path) + lift `/tmp/piece3_reset.py` logic into a reusable `establish_substrate(user_id, requires, setup)` helper | Apply declared file writes (via existing `_write_substrate_with_author`) + delete files declared `absent: true` (workspace_files SQL DELETE, revision chain preserved per ADR-209), with `operator-proxy:eval-suite-runner:acting-as-{persona}` attribution. Default reset-to-clean per §3.1 unless `accumulates: true`. |
| **C4. Rollup re-shape — emit prose scaffold, not dimension tables** | `api/scripts/operator/run_eval_suite.py` `render_session_md()` | Replace the four per-dimension table renderers (`### Behavior`/`### Posture`/`### Substrate usage` + their `_format_substrate_inputs_compact` / `_format_eval_shape_compact` / `_shape_aggregate_summary` helpers) with: §Preconditions table (automated), per-eval prose-prompt blocks (situation + prior + receipt-pointers, read left blank), §Cost appendix (keep existing cost logic), §Read-state line. Delete `_verdict_pass_marker()`. |
| **C5. Read-state replaces DRAFT/POPULATED** | `api/scripts/operator/run_eval_suite.py` `render_session_md()` | Emit a `## §Read-state` line naming what was read (runner emits "Read: nothing yet — runner scaffold only"), not a `**DRAFT**`/`**POPULATED**` flag. |
| **C6. Per-eval cost attribution fix** | `api/scripts/operator/run_eval_suite.py` cost-rollup section | Existing v1 had per-eval cost rows all showing the session total (c51c44f bug). The d38130e run already attributes by `created_at` window — confirm that path is the only one and the §Cost appendix uses it. Cost is the one honest number; it should be correct. |
| **C7. README scenario-schema note** | `docs/evaluations/README.md` | Add `requires:` / `prior:` to the documented suite-vs-scenario boundary (scenarios stay assertion-light; the suite layer adds the read-orienting + precondition context). No scenario-schema change — `requires`/`prior` live on the *suite eval entry*, not the scenario. |

**Not in scope** (explicit non-goals, preserved from prior §6): no automated assertion gating on the qualitative read (only `requires:` pre-flight gates, and those gate *firing*, not *pass/fail*); no UI; no ADR (developer-surface scaffolding); no LLM-as-judge auto-classification of the read (the read is human, by design — §1).

---

## §9 Discipline rules

These extend `README.md` §"Discipline rules" with eval-suite specifics. They replace the prior E0–E6.

- **S1. The read is the artifact; receipts are the proof under it.** SESSION.md is prose answering "did the Reviewer reason like a mandate-holder." Every load-bearing claim carries a receipt inline (revision_id / execution_event id / reproducible query). A claim without a receipt is narrative, not evidence (`README.md` rule 2).
- **S2. The situation must be the situation it claimed.** Every eval declares `requires:` (harness-checked) and/or `setup:` (harness-established). An eval that fires against a violated precondition produces a finding that cannot be trusted — the harness refuses to fire it (§3). This is non-negotiable; it is the lesson the whole rewrite is built on.
- **S3. Judge against the mandate, not against a pre-declared cell.** `prior:` orients the read; it does not grade it. Divergence from prior is a finding to interpret (defensible alternative? real gap? which cause?), never a "FAIL" to tabulate (§4).
- **S4. Reset to clean is the default; accumulation is declared.** Each eval resets to its known starting state unless it declares `accumulates: true` + `inherits:` for an ordered-arc responsiveness read (§3.1).
- **S5. Name the cause on every divergence.** When the Reviewer diverges from the editor-coherent move, the read names which of substrate / Reviewer-read / envelope / canon (§1.2 a–d) caused it. That is what gives the finding a fix-location.
- **S6. Cost is surfaced, never gated.** Session cost is reported as a finding. Exceeding budget is worth surfacing (sustained high cost is a system characteristic); it is not a pass/fail (`README.md` E5 spirit preserved).
- **S7. Read-state names what was read.** No DRAFT/POPULATED binary. "Evals 1-3 read; 4-5 not yet" is a complete, honest read-state. Partial is fine and stated plainly (§6.2).
- **S8. Cross-hat commit shape: results-only.** A session run + its read is Hat-B. A clean Hat-A fix with named in-canon precedent may cross over in one commit; multiple recommendations or architectural changes route to separate commits (`README.md` rule 6).

---

## §10 What this discipline does NOT do

1. **Does not replace scenario folders.** Single-eval probe captures continue at `docs/evaluations/{date}-{slug}/`. Eval suites compose scenarios; they don't replace the unit.
2. **Does not auto-classify the read.** The read is a human judgment formed from transcripts. `requires:` gates *firing*; nothing gates the *finding*. LLM-as-judge of the read is explicitly out of scope (it would re-introduce the auto-classification the rewrite exists to remove).
3. **Does not score dimensions.** There are no `Pass?` cells, no per-dimension aggregates, no trace-completeness numbers. Cost is the one number, and it is an appendix.
4. **Does not introduce a UI.** SESSION.md is markdown read in an editor.
5. **Does not introduce an ADR.** Eval-suite discipline is developer-surface scaffolding (two-hats rule); it lives outside the system canon real operators inherit.

---

## §11 Cross-references

- Redesign reasoning (read first): [`../analysis/eval-suite-redesign-from-first-principles-2026-05-29.md`](../analysis/eval-suite-redesign-from-first-principles-2026-05-29.md)
- General evaluation discipline: [`README.md`](README.md)
- The partition this measures (principles ↔ persona-frame): [`../architecture/agent-composition.md`](../architecture/agent-composition.md) §3.2.1
- Mandate-coherence criterion (M-cell vocabulary, used as reading aid not grade): [`2026-05-27-000919-mandate-coherence-criterion/findings.md`](2026-05-27-000919-mandate-coherence-criterion/findings.md)
- Reviewer envelope plumbing (the substrate→envelope→behavior chain): ADR-274, ADR-276
- Operator-proxy canon: ADR-294
- Authored-substrate (attribution under every receipt): ADR-209

## §12 Status

**Proposed** (full rewrite, 2026-05-29). Replaces the 2026-05-27 four-dimension-scoring shape. Operator review precedes implementation of the §8 harness changes and the §7 suite migration. No session run validates this doc yet — the first session under the new shape lands after the harness changes ship.

## Last updated

2026-05-29 — clean-slate rewrite. Prior version (2026-05-27, four-dimension scoring) superseded.
