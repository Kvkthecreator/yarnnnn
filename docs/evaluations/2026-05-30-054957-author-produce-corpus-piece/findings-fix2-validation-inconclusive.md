# Validation finding — Fix 2 citation-catch INCONCLUSIVE + a new budget-exhaustion finding

**Date**: 2026-06-01
**Hat**: B (developer-surface validation of Fix 2, commit `3f6bab8`)
**Persona**: yarnnn-author (alpha-author, user `0b7a852d-4a67-447d-91d9-2ba1145a60d7`)
**Cost**: $0.53 (one validation re-fire)

> **Honesty note**: this finding does NOT claim Fix 2 works. The validation re-fire did not reach the citation rule — it budget-exhausted on an unrelated failure. The citation-catch question is back to OPEN, and a new finding surfaced.

---

## Headline

**Fix 2's catch is UNVALIDATED — the re-fire budget-exhausted at 20/20 rounds before reaching the citation rule. The rule was in the Reviewer's envelope (principles.md head carried it, read at 01:28:19) but the audit never got to it. Cause: a verbose rule-by-rule audit written via many incremental WriteFile calls × a model run that fumbled the WriteFile `content` parameter ("I'm in a loop. Let me step back and properly construct the WriteFile call WITH the content parameter") consumed all 20 rounds on Rules 1–7. This is a NEW failure mode, distinct from the P6 silent-exit Fix 1 addressed.**

---

## §1 — What happened (receipts)

| Wake | rounds | output_tokens | judgment_log writes | outcome |
|---|---|---|---|---|
| Fix-1 validation (06-01 00:42) | 11 | 11,471 | 3 | clean APPROVE, ReturnVerdict close |
| **Fix-2 validation (06-01 01:34)** | **20 (max)** | **27,661** | **14** | **budget_exhausted silent-exit (P4); never reached Rule 8** |

Same piece, same deployed code (`1d8563c`), citation rule present in envelope. The difference is **model run-to-run variance in WriteFile tool-call mechanics**:

- The audit walked Rules 1–7 (the pre-Fix-2 seven), writing the verdict incrementally across **14 WriteFile calls** to judgment_log.
- The silent-exit prose (preserved in standing_intent, dispatcher-authored): *"I'm in a loop. Let me step back and properly construct the WriteFile call WITH the content parameter. The format I need is: WriteFile(scope=..., path=..., content=...). Let me do that now:"* — the model was **retrying malformed WriteFile calls** (omitting `content`), burning rounds on retries.
- At round 20/20 it budget-exhausted. `_dispatcher_write_silent_exit_standing_intent(exit_class="budget_exhausted")` fired (P4 — the unchanged path). The dispatcher synthesized the verdict from the last good judgment_log write (an APPROVE on Rules 1–7).
- **Zero of the 14 judgment_log writes mention citation-verifiability.** The audit never reached Rule 8.

**The rule was in context, not missing**: `principles.md` rev `31a3933b` (carrying the citation rule) was written 01:24:30; the wake fired 01:27:21; Render logs show the envelope read `/workspace/review/principles.md` at 01:28:19. So this is **budget-starvation, not rule-absence.**

**Bitter irony in the substrate**: Rule 1's evidence in this run *again* praises the fabricated citations — *"Every architectural claim cites live ADRs (209, 253, 256, 283, 293, 254, 295)"* — calling them "live." The exact failure Fix 2 targets is still visible; the rule that would catch it sat one round past where the budget ran out.

---

## §2 — The new finding (distinct from P6)

This is **not** the P6 verdict-in-prose silent-exit (Fix 1 fixed that — and Fix 1 worked here too: the model used the WriteFile-judgment_log channel, it just fumbled the call mechanics). This is a **separate P4 budget-exhaustion** with two compounding causes:

1. **Verbose incremental audit writes**: the model wrote the rule-by-rule audit across 14 separate WriteFile calls instead of one. Each round = one tool call; 14 writes + reads + retries ≈ 20 rounds.
2. **WriteFile `content`-parameter fumble**: the model repeatedly issued WriteFile without `content`, recognized the loop, and retried — pure round waste. (This is a model-mechanics failure on the WriteFile tool, possibly aggravated by the two-channel guidance now asking it to write a *long* document via WriteFile — a bigger/harder call than a short ReturnVerdict.)

**Tension worth naming**: Fix 1's two-channel design (long audit → WriteFile judgment_log) is what put the model on the WriteFile path for a long document. The Fix-1 validation run did this cleanly in 3 writes; this run fragmented into 14 + fumbles. So Fix 1 is not *wrong*, but it has surfaced a **second-order cost**: a long document written via WriteFile is a harder tool call than a short ReturnVerdict, and on a bad run the model can loop on it. The 20-round budget for a Haiku reactive audit may be too tight for "read 6 files + write a 7-rule (now 8-rule) audit document via WriteFile + close" when the model is also fumbling call mechanics.

---

## §3 — Why this is INCONCLUSIVE, not a failure

- Fix 2 (the citation rule) was **never executed** — the audit stopped at Rule 7. We have **no evidence either way** on whether the rule catches the fabrication. The catch question is OPEN again.
- The Fix-2 substrate (rule + spec) is correctly in place and in-envelope. The blocker is upstream (budget exhaustion), not the rule.
- This is a clean parallel to the original arc: just as the P6 silent-exit blocked the *first* citation test, a P4 budget-exhaustion blocked *this* one. The instrument failed before the measurement.

---

## §4 — Receipts + reproducibility

- Fix-2 wake: `execution_events` 2026-06-01 01:34:27 slug=pre-ship-audit status=success tool_rounds=20 output_tokens=27661.
- Silent-exit: `workspace_file_versions` standing_intent.md `dispatcher:silent_exit_fallback` "budget_exhausted @ round 20/20", 01:34:27.
- 14 judgment_log writes 01:29:16–01:34:27, all `reviewer:ai:reviewer-sonnet-v8`, **0** mention citation/verifiability.
- Rule in envelope: principles.md rev `31a3933b` (01:24:30) read by envelope 01:28:19 (Render logs crn-d604uqili9vc73ankvag).
- Fire dedup_key `795ae515-cdd4-4ed0-9a1e-bad4782cb2eb`.
- State clean: profile.md `ready_for_review` (net-unchanged), 0 pending proposals.

```sql
SELECT slug, status, tool_rounds, output_tokens FROM execution_events
WHERE user_id='0b7a852d-4a67-447d-91d9-2ba1145a60d7' AND slug='pre-ship-audit'
  AND created_at >= '2026-06-01T01:27:21';
```

---

## §5 — Next-step options (operator decision)

The citation rule is committed + in-envelope; the blocker is the budget-exhaustion on this run. Options:

1. **Re-fire as-is** — run-to-run variance; the next run may not fumble WriteFile and may reach Rule 8 (the Fix-1 validation run completed cleanly in 11 rounds, so a clean run is achievable). Cheapest; gambles on variance.
2. **Raise the reactive round budget** for audit-shaped wakes (currently 20 for Haiku) — gives a verbose 8-rule audit room to complete even on a fumbly run. Small code change in `reviewer_agent.py`. Addresses the new finding directly.
3. **Tighten the audit-write pattern** — guide the model to write the audit in ONE WriteFile (not 14 incremental) + ONE ReturnVerdict. Prompt/spec change. Reduces round consumption structurally; the better long-term fix for the new finding.
4. **Diagnose the WriteFile-content fumble** — is the model fumbling because the two-channel guidance is ambiguous about how to pass a long `content`? Prompt-clarity question.

The honest recommendation: **(3) + a confirming re-fire** — the new finding (verbose-incremental-write × budget) is the real issue surfaced, and tightening the write pattern to "one WriteFile, one ReturnVerdict" addresses it structurally AND gives the citation rule room to fire. (2) is a cruder lever (more budget for the same inefficiency). (1) alone leaves the new finding unaddressed.

---

## Read-state

Fix 2 catch **INCONCLUSIVE** (rule in-envelope but audit budget-exhausted at 20/20 before reaching it). **NEW finding**: verbose incremental audit writes × a WriteFile-content-parameter fumble loop exhausted the round budget — a P4 distinct from the P6 Fix 1 addressed, and a second-order cost of Fix 1's two-channel WriteFile path. Citation-catch question is OPEN again. Fix-2 substrate is correctly placed; the blocker is upstream budget. Recommend tightening the audit-write pattern (one WriteFile + one ReturnVerdict) before re-testing the catch.
