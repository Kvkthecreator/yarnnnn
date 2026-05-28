<!--
  SESSION.md template — the artifact an eval-suite session emits.
  Canonical shape per EVAL-SUITE-DISCIPLINE.md §6 (Proposed 2026-05-29).

  This is what the v2 runner scaffold (EVAL-SUITE-DISCIPLINE.md §8 C4/C5)
  targets. The runner fills only: header, §Preconditions, §Cost, and the
  per-eval prompt skeleton (situation + prior + receipt-pointers). It
  leaves THE READ BLANK — there are no Pass? cells to auto-fill, by design.

  The operator writes §The read, §What the session says overall, and
  §Recommendations after reading raw/ transcripts.

  Replace every {placeholder}. Delete this comment block in a live session.

  WHAT IS DELIBERATELY ABSENT vs. the old template:
    - no ### Behavior / ### Posture / ### Substrate usage tables
    - no Pass? columns, no per-dimension aggregates, no trace-completeness numbers
    - no DRAFT/POPULATED status flag
  These were the drift-inviting structures (EVAL-SUITE-DISCIPLINE.md §1.3).
-->

# Eval-suite session — {suite-slug}

**Captured**: {ISO timestamp}
**Persona**: {persona-slug}
**Workspace**: `{user_id-prefix}` ({email})
**Suite**: `docs/evaluations/eval-suites/{suite-slug}.yaml`
**Read kind**: {judgment_coherence | substrate_responsiveness}
**Evals fired**: {N} of {M}  ({K refused pre-flight — see §Preconditions})
**Session cost**: ${total} (budget ${budget}) — {within | EXCEEDS}

---

## §Preconditions (automated — runner-filled)

Per-eval `requires:` check at fire time (EVAL-SUITE-DISCIPLINE.md §3). An eval
that failed pre-flight did NOT fire — no read exists for it, and that is the
correct outcome (a measurement that can't honor its precondition is not run).

| Eval | requires | satisfied at fire time? | fired? |
|---|---|---|---|
| {eval-slug} | {requires summary} | {YES / NO (detail)} | {yes / REFUSED} |

---

## §The read   ← operator writes this; runner leaves it blank

_For each FIRED eval: read `raw/{eval}/transcript.md` + `substrate-diff.md` +
`decisions.md`, then write the four prose fields. No cells. The deliverable is
the judgment in "Coherent with the mandate?" — everything else orients it._

### {eval-slug} — {one-line situation}

**Prior** (from manifest): {the orienting hypothesis — what a coherent
mandate-holder would do here. NOT a grade.}

**What the Reviewer did**: {prose, read from raw/. The verdict, the reasoning
shape, the substrate it wrote. Quote the load-bearing transcript line.}

**Coherent with the mandate?**: {THE FINDING. Judge against MANDATE + principles,
not against the prior. If it diverged from the prior, is the divergence a
defensible alternative (the Reviewer found a better move) or a real gap? If a
gap, name which of the four causes (EVAL-SUITE-DISCIPLINE.md §1.2):
(a) substrate / (b) Reviewer-read / (c) envelope / (d) canon.}

**Receipts**: {revision_ids, execution_event ids, inline. Every load-bearing
claim above carries one (S1).}

<!-- repeat per fired eval -->

---

## §What the session says overall   ← operator writes

{One to three paragraphs. The load-bearing finding of the whole session. What
this establishes about whether the Reviewer reasons like a mandate-holder.
Cross-eval patterns the per-eval reads reveal together that no single read does.
Each load-bearing claim carries a receipt.}

---

## §Recommendations (if any)   ← operator writes

{Hat-A system-canon changes this read recommends, each gated on a specific read
above. May legitimately be "none — behavior is canon-coherent." Multiple
recommendations or architectural changes route to separate commits per
README.md rule 6. A clean Hat-A fix with named in-canon precedent may cross
over in this commit (S8).}

---

## §Cost (automated appendix — runner-filled)

_The one honest number. Surfaced, never a pass/fail gate (S6)._

**Session total**: ${total} across {N} wakes ({J} judgment, {M} mechanical).
**Tokens**: {in} in / {out} out.

| Slug | Wakes | Cost USD | Tokens (in/out) |
|---|---|---|---|
| {slug} | {n} | ${cost} | {in}/{out} |

**Reproducible**: `raw/cost-rollup.csv` + the execution_events query below.

```sql
SELECT slug, mode, wake_source, status, input_tokens, output_tokens, cost_usd, created_at
FROM execution_events
WHERE user_id = '{user_id}'
  AND created_at >= '{session_start}'
  AND created_at <= '{session_end}'
ORDER BY created_at;
```

---

## §Read-state   ← operator updates as the read progresses

_Names exactly what was read. NOT a DRAFT/POPULATED binary (S7). Honest partial
state is stated plainly, not apologized for._

Read: {e.g. "evals 1-4 read (3 transcripts each); eval-5 fired but not yet read;
eval-6 REFUSED pre-flight (no read possible)."}

Runner scaffold emitted: {ISO timestamp}. Read begun/completed by: {who, when}.
