# `assembling-a-composite-document`, measured: the craft is the model's own

> Closes Part R owed 1 / Part S owed 1. Probe:
> `api/scripts/operator/probe_composite_document_skill_ab.py`. Real
> `run_lane_turn`, the Editor engine (`anthropic/claude-sonnet-5`), live
> production substrate, 3 trials per arm interleaved, each trial in its own
> folder under `operation/_probe-composite-skill/` (purged after: 18 rows → 0).

## What the skill claims

Step 4: *"keep the document's own numbers to the few the argument actually
uses — copying a whole table into prose is how two versions of the truth
start."* A 3-row fixture cannot fail that claim, so this one is **24 monthly
rows** (Oct 2024 → Sep 2026), of which the quarter under review is three.

## Pre-registered measure (one per arm)

`rows_copied_fraction` — of the 24 rows, the fraction whose `monthly_active`
figure appears in the document. Direction: ARM A (skill in the index) < ARM B
(slug withheld from the in-process kernel index; the mirrored body still
exists under `system/skills/`, exactly as in Parts P/Q/R — the treatment is
discovery). The ask names the skill's subject word for word: *"Write the Q3
platform review into the bound document — a one-page report for the
all-hands where the numbers matter as much as the words."*

## Result

```
ARM A  rows_copied_fraction  0.292 / 0.250 / 0.292   mean 0.278
ARM B  rows_copied_fraction  0.292 / 0.250 / 0.333   mean 0.292
exact permutation p (A<B) = 0.500      floor at n=3/arm = 0.050
exploratory:  read the skill  A 0/3  B 0/3      provenance line  A 2/3  B 3/3
```

**Null.** Not directional, not separated — identical to the third decimal in
two of three pairs. Every document in both arms carried ~7 of 24 figures: the
Q3 three in a table, and Q2's average, June, and the prior September in prose
as comparison points.

## What the receipts say

A1 and B1 are the same document to the paragraph: a growth section that sets
Q3 against Q2 and against a year earlier; a reliability section that pairs
the p95 drop with the ingest migration; a three-row table **under the
provenance line**; and the standup's "support queue halved" figure marked
*"a standup-reported figure, not one tracked in the metrics above"*. That
last move — marking what is inferred or unsourced — is the skill's step 5,
performed by an arm that never read the skill.

## Rulings

1. **The craft is the model's own.** Steps 1–6 describe what a frontier model
   does with a report ask unaided. Measured flat in both arms → the Part Q
   profile: prose paid for in every turn. `_INDEX_RANK` → 2 (measured-null).
   Kept, not pruned — the arc's rule — but the silent failure it guards (a
   whole table pasted into prose) did not occur in the control arm.
2. **Naming the subject did not reach the body: 0/3.** The description
   already states the craft, so the lane conforms without reading (Part M).
   That is the third time this arc has seen it; treat "did it read the
   skill?" as a discovery metric only, and expect the description to be the
   whole treatment for a craft skill.
3. **The contract half is where the movement was — and it is in the posture
   now.** The provenance line separated 3/3 vs 0/2 as a posture bullet
   (`[2026.09.07.2]`); here it appears 2/3 and 3/3 with the bullet present in
   both arms (one A trial cited the CSV in prose instead of the line — a
   miss under the regex, not a missing source).

## Method notes

- A `grep -v "^\s+"` on the probe's own log erased every per-trial line; the
  summary survived because it is left-aligned. Filter tracebacks by their
  first token, never by indentation.
- The withhold is an in-process patch of `services.skills._kernel_cache`,
  restored in `finally`; the run composes the frame in-process, so no
  deploy and no second workspace were needed.
