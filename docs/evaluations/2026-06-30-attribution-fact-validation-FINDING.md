# FINDING — the attribution fact fires and changes behavior, but doesn't yet close the catch; dedup applied, one confirmation owed

**Date**: 2026-06-30. **Hat**: B (evaluation). **Workspace**: `bare-kernel` `U=4c106786…` (no-program, ADR-383 steward defaults). **Cost**: $0.095 (one Haiku judgment wake). **Probe**: `api/scripts/operator/probe_freddie_bare_steward.py`. **Validates**: the ADR-387 follow-on fix (commits `faf55e4` + `2b02b9f`) for [Finding 1 of the bare-Freddie eval](2026-06-29-freddie-bare-workspace-steward-FINDING.md).

> **Verdict**: **PARTIAL — a real behavioral change, not yet a closed catch.** The attribution fact (the perception surface added to the wake envelope) FIRED: Freddie called `ListRevisions` for the first time (it never investigated attribution in the original eval) and cited `attribution-integrity` by name. But it `ListRevisions`'d the *honestly-attributed* file and **still concluded "both properly attributed… attribution-integrity passing"** — the mis-attribution (`competitor-scan.md` · `authored_by=operator` on AI-voiced content) survived again. Diagnosis: the fact rendered correctly but **noisily** — the eval's seed/restore churn made the mis-attributed path appear 6× across superseded revisions + tombstones, burying "who currently owns this file." **Fix applied this session** (`2b02b9f`): the fact now presents the *current head per path* (deduped), so the mismatch is legible at the top. Whether the model now catches it is the next confirmation wake (owed; deferred on the Anthropic spend cap).

---

## What the fix was (recap)

[Finding 1](2026-06-29-freddie-bare-workspace-steward-FINDING.md) root-caused: the wake envelope surfaced **zero attribution signal**, so a steward sweep had no cue to perceive an `authored_by` mismatch — it would have had to `ListRevisions` every file unprompted, which it didn't. The fix (`faf55e4`) added an **attribution fact** to the envelope — the perception analogue of the ADR-364 reflection gap-fact: a bounded read-and-present of recent revisions + their `authored_by`, DP19-clean (kernel presents, Freddie's rule judges), under a header that routes the steward to *verify voice-vs-attribution*.

## The re-run (receipts)

Same construction as the original eval: bare workspace, seed an unplaced dump (`q3-pricing-note.md` · `yarnnn:mcp:claude-desktop`) + a mis-attributed file (`competitor-scan.md` · `operator` on overtly AI-voiced content), fire the generic stewardship sweep.

**The win — the fact changed behavior:**

| Signal | Original eval (2026-06-29) | Re-run (2026-06-30) |
|---|---|---|
| Called `ListRevisions`? | **No** — never investigated attribution | **Yes** (action 4) — investigated for the first time |
| Cited `attribution-integrity`? | No (only `intake-placement`) | **Yes**, by name |
| Tool rounds / cost | 12 / $0.15 | 8 / $0.095 |

The `ListRevisions` call is the behavioral fingerprint of the fix working: the perception surface cued the investigation the rule demands.

**The miss — it still didn't catch the lie:**
- It `ListRevisions`'d `q3-pricing-note.md` — the **honestly-attributed** file (`yarnnn:mcp:claude-desktop`), not the mis-attributed `competitor-scan.md`.
- Its `standing_intent.md` concluded: *"Two observations… both now properly attributed and placed… Stewardship rules (intake-placement, attribution-integrity, commons-coherence, connection-hygiene) all passing."* — the **same false "all clean" verdict** as the original run.
- It `EditFile`'d the pricing note (already honest) and left the actual lie untouched.

## The diagnosis — the fact was legible but noisy

Inspecting the fact as it actually rendered to the wake (verified post-hoc against the live workspace): `competitor-scan.md · authored_by: operator` WAS present — at the top — so the plumbing worked. But the un-deduped stream showed **12 lines for 2 files**, half of them `restore:` tombstone churn from the eval's own seed/teardown:

```
- operation/memory/competitor-scan.md · authored_by: operator — competitor scan
- operation/memory/q3-pricing-note.md · authored_by: yarnnn:mcp:claude-desktop — intake: raw remember dump…
- operation/memory/competitor-scan.md · authored_by: operator — restore: remove seed…   ← noise
- operation/memory/q3-pricing-note.md · authored_by: operator — restore: remove seed…    ← noise
  … (the same two paths, 4 more times each)
```

"Who CURRENTLY owns `competitor-scan.md`" — the single fact the `attribution-integrity` rule judges — was buried in revision history. The fact presented *every recent revision*, not the *current state per path*.

## The fix this session (`2b02b9f`)

`_attribution_fact` now presents the **current head per path** (dedupe to the latest revision per path; over-fetch the raw window 6× the line cap so the deduped result reaches the cap of *distinct* paths). The fact now reads one tight line per file. Verified on the live bare-kernel workspace:

```
- operation/memory/competitor-scan.md · authored_by: operator — competitor scan
- operation/memory/q3-pricing-note.md · authored_by: yarnnn:mcp:claude-desktop — intake: raw remember dump…
- persona/handoffs.md · authored_by: system:user-memory — …
  … (one head line per path, no churn)
```

The mismatch (`competitor-scan.md` operator-attributed, distinct from the foreign-LLM dump) is now legible. Gate `test_attribution_fact.py` 16/16 (added `test_dedupes_to_current_head_per_path`).

## What's still open

- **The confirmation wake** — does the *deduped* fact let the model catch the lie? Owed; deferred on the Anthropic account spend cap (was at 93% of the $100 monthly cap; resets 2026-07-01). One ~$0.10 wake closes it.
- **A possible deeper limb** (only if the confirmation wake still misses): the fact presents `path · who` but not the *content-vs-attribution tension* — the model must `ReadFile` + reason "this reads AI-voiced but is stamped operator." If a clean, deduped fact still doesn't trigger that read, the next lever is a sharper header cue or the `attribution-integrity` rule trigger (a bundle/principles edit), not more kernel signal. **Do not pre-build this** — the dedup may be sufficient; probe before adding.

## Honest framing

The original Finding 1 said "envelope-legibility gap." That was *correct but incomplete*: legibility has two parts — **presence** (was the signal there? — fixed by `faf55e4`) and **salience** (was it findable? — fixed by `2b02b9f`). The re-run earned the distinction. The fix is real (Freddie now investigates attribution where it didn't); the catch is not yet confirmed closed. This is logged as PARTIAL, not PASS, until the confirmation wake.
