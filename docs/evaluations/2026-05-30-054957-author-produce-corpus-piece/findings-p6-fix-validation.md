# Validation finding — ADR-303 §9 P6 fix WORKS + citation-catch ANSWERED

**Date**: 2026-06-01
**Hat**: B (developer-surface validation of the Hat-A fix landed this session)
**Persona**: yarnnn-author (alpha-author, user `0b7a852d-4a67-447d-91d9-2ba1145a60d7`)
**Fix under test**: commit `1d8563c` (ADR-303 §9 P6 — two-channel audit verdict + verdict-in-prose recovery), deployed live (scheduler `dep-d8ed72jrjlhs73br3n60`, API `dep-d8ed72brjlhs73br3m9g`, both `live` 00:36Z)
**Cost**: $0.34 (one validation re-fire)

> **What this closes**: `findings-silent-exit-reproduction.md` proved the silent-exit was structural and diagnosed it as a channel-shape mismatch. This file validates the fix end-to-end on deployed code AND answers the citation-catch question (`findings.md` §2) that the original silent-exit had left open.

---

## Headline

**The fix works — the silent-exit is GONE — and a *completing* audit gives us the clean answer to the citation question: the audit does NOT catch citation fabrication, because `principles.md` has no citation-grounding rule. The §2 recommendation #1 is now empirically confirmed load-bearing.**

Two distinct results, both receipt-backed:

1. **Silent-exit eliminated (the fix).** The same moat-thesis pre-ship-audit that silent-exited 3× now **completes** with a real, model-authored, rule-by-rule verdict in `judgment_log.md`. Zero dispatcher silent-exit fallbacks. The two-channel guidance (A) alone prevented it — the model went straight to `WriteFile(judgment_log)` without ever emitting the verdict as prose, so the recovery guard (C) never had to fire.
2. **Citation-catch answered (the still-open §2 question).** The completing audit **APPROVED the piece** and explicitly cited the fabricated ADRs as *evidence of passing* Rule 1 (voice-fingerprint-match). It never verified the citations resolve. So a fully-completing, correctly-reasoned 7-rule audit **still approves fabricated citations** — confirming the missing `citation-grounding` rule is exactly the gap.

---

## §1 — The fix: silent-exit eliminated (receipts)

| Metric | Original (05-30) | Repro #2 (05-31) | **Validation (06-01, fixed)** |
|---|---|---|---|
| tool_rounds | 4/20 | 14/20 | **11/20** |
| output_tokens | 2,771 | 8,406 | **11,471** |
| Exit | P5 silent-exit | P5 silent-exit | **clean ReturnVerdict close** |
| judgment_log verdict | none | none | **APPROVE (model-authored, 3× WriteFile)** |
| dispatcher silent_exit_fallback revisions | 1 | 1 | **0** |

**Trace (scheduler logs, 00:39:43–00:42:00):** ReadFile×N + ListRevisions + SearchFiles (substrate gathering) → `WriteFile(judgment_log.md)` ×3 (the rule-by-rule audit, written incrementally) → `WriteFile(standing_intent.md)` (cycle close) → ReturnVerdict ends the loop. **No `verdict-in-prose detected` warning, no `text-only response` warning** — the model used the judgment_log channel directly because the prompt now tells it to. The cause-fix (A) worked at the source; the backstop (C) was not needed (and that's the ideal outcome — prevention over recovery).

**Receipts:**
- `execution_events` 2026-06-01 00:42:04 slug=pre-ship-audit status=success tool_rounds=11 output_tokens=11471.
- `judgment_log.md` revisions 00:40:58 / 00:41:21 / 00:41:41, all `authored_by=reviewer:ai:reviewer-sonnet-v8` (model-authored, NOT dispatcher).
- `COUNT(dispatcher:silent_exit_fallback revisions since fire) = 0`.
- Fire dedup_key `741d76ab-7c66-4147-aab7-9e75afdf87b6`.

**This resolves `findings.md` §6 "unvalidated because the audit didn't finish."** The independent pre-ship audit now finishes. The authoring SAFETY LOOP completes — UNVALIDATED → VALIDATED-COMPLETES.

---

## §2 — The citation-catch: a completing audit does NOT catch fabrication (the clean answer)

The verdict written to `judgment_log.md` walks all 7 rules with evidence. Rule 1 (voice-fingerprint-match) evidence reads:

> *"Architecture-grounded: ADR-209, ADR-253, ADR-256, ADR-283, ADR-293, ADR-254, ADR-295 cited with direct links."*

**The audit treated the fabricated citations as evidence of PASSING.** It saw "ADRs cited with links" and checked the box — it never verified that ADR-254 is *file-format-discipline* (not the amendment-discipline the piece claims) or that the `github.com/yarnnn/yarnnn/blob/main/docs/architecture/adr/...` URLs are invented (real path is `docs/adr/`). Verdict: **APPROVE**, "zero violations."

This is the **clean answer the §6 silent-exit had blocked**: the audit completes, walks every rule it has, and **still approves fabricated citations** — because none of the 7 rules (voice / anti-slop / text-continuity / entity-continuity / voice-declaration / engagement-bait / hot-take) check whether a cited reference resolves to a real file with matching content. The `_editorial.md` #3 principle ("architecture-grounded, cite shipped ADRs") is declared but has **no enforcing audit rule** in `principles.md`.

**Conclusion**: `findings.md` §2 recommendation #1 (add a `citation-grounding` rule to alpha-author `principles.md`) is **empirically confirmed load-bearing** — the completing audit demonstrably needs it. This is now the next Hat-A fix in the sequence (Fix 2), and it can be validated cleanly because the audit now completes (Fix 1 unblocked it, exactly as the design's sequencing note predicted: completion before catch).

---

## §3 — Receipts + reproducibility

```sql
-- the completing audit (status=success, no error, model-authored verdict)
SELECT slug, status, error_reason, tool_rounds, output_tokens
FROM execution_events
WHERE user_id='0b7a852d-4a67-447d-91d9-2ba1145a60d7'
  AND slug='pre-ship-audit' AND created_at >= '2026-06-01T00:39:16';

-- the verdict-of-record, model-authored, zero dispatcher fallback
SELECT path, authored_by, message, created_at FROM workspace_file_versions
WHERE user_id='0b7a852d-4a67-447d-91d9-2ba1145a60d7'
  AND created_at >= '2026-06-01T00:39:16' ORDER BY created_at;
```

- Fix deployed: scheduler `dep-d8ed72jrjlhs73br3n60` + API `dep-d8ed72brjlhs73br3m9g`, both live with `1d8563c`.
- Live prep: `_autonomy.yaml` → autonomous (rev `4a0ed3b2`); live `pre-ship-check.md` spec synced to two-channel (rev `5124c06f`).
- Regression gate: `api/test_adr303_p6_verdict_in_prose.py` 8/8 + `test_adr303_phase3_dispatcher_writes.py` 8/8.

---

## Read-state

**Fix VALIDATED.** Silent-exit eliminated on deployed code (audit completes, model-authored rule-by-rule verdict in judgment_log, zero dispatcher fallback). The two-channel cause-fix (A) prevented the failure at source; the recovery backstop (C) was correctly not needed. **Citation-catch ANSWERED**: a completing 7-rule audit does NOT catch citation fabrication (approves fabricated ADR citations as Rule-1 PASS) → the §2 `citation-grounding` rule is confirmed load-bearing and is the next fix (Fix 2), now cleanly testable because the audit completes. The authoring SAFETY LOOP (independent audit) is, for the first time, validated as completing — though it is not yet validated as *catching* (that is Fix 2's job).
