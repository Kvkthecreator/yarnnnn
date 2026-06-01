# Follow-on finding — the §6 silent-exit REPRODUCES (structural, not one-off)

**Date**: 2026-06-01 (diagnostic follow-up to this session's `findings.md` §6)
**Hat**: B (developer-surface diagnosis of the pre-ship-audit silent-exit)
**Persona**: yarnnn-author (alpha-author, user `0b7a852d-4a67-447d-91d9-2ba1145a60d7`)
**Read kind**: reproduction + root-cause (does the silent-exit recur deterministically; what causes it)
**Cost**: $0.23 (one re-fire wake, contaminated — see §Contamination)

> **Why this follow-up exists**: `findings.md` §6 left the silent-exit's status as "one-off vs structural — UNKNOWN." The original pre-ship-audit (05-30 05:54) silent-exited at round 4/20 via `text_only_mid_loop`. The operator chose "diagnose recurrence first" before designing any fix. This file records the diagnosis: **the silent-exit is structural — it reproduced twice, independently, on two different trigger types — and the root cause is a channel-shape mismatch, not a generic action-grammar fumble.**

---

## Headline

**The silent-exit is STRUCTURAL and audit-shape-triggered. It reproduced 2× independently (different triggers, same long piece). Root cause: a channel-shape mismatch — the pre-ship-audit spec demands a long, structured, multi-rule verdict document, but the only structured verdict channel (`ReturnVerdict.reasoning`) is sized for "2-5 sentences." Facing a long audit, the model pours the verdict into a text block (the natural shape for it), and the runtime's `if not tool_uses` reads that text-only round as a terminal silent-exit.**

---

## §1 — The reproduction (2 independent silent-exits)

| # | Wake | Trigger | Rounds | output_tokens | Exit | Receipt |
|---|---|---|---|---|---|---|
| 1 | pre-ship-audit (05-30 05:54:58) | substrate_event | **4**/20 | 2,771 | **P5 silent-exit** — prose `### Rule 1: voice-fingerprint-match...` | `execution_events` status=success; `standing_intent.md` rev `dispatcher:silent_exit_fallback` 05:54:58 |
| 2 | weekly-corpus-review (05-31 18:02:17) | cron_tick | **14**/20 | **8,406** | **P5 silent-exit** — prose "The moat-thesis content appears..." | `execution_events` status=success, 14 rounds, 8406 out-tokens; preserved in proposal `49779ef9` decision_context |

**Two independent fires, two trigger types (reactive substrate-event + cron), both silent-exit via `text_only_mid_loop` while reasoning about the same long piece (moat-thesis).** This kills the one-off hypothesis from §6. The failure is deterministic on long-piece audits.

**The token signature is the tell.** Wake #2 emitted **8,406 output tokens** before silent-exiting at round 14/20 — that is the model writing a *long prose audit document*, with budget to spare. It is not running out of rounds or tokens; it is rendering the verdict in the wrong channel.

---

## §2 — Root cause: channel-shape mismatch (sharper than "action-grammar fumble")

The original §6 framing called this "the same action-grammar class ADR-306 targets." The reproduction sharpens it: ADR-306's collapsed action-grammar frame ("a tool call IS the action; close every cycle with a verdict") **is present** in `_compute_minimal_frame` (`reviewer_agent.py:444-481`) and the failure happens anyway. So it is not a missing-frame problem. It is a **channel-shape mismatch**:

- **The spec** (`docs/programs/alpha-author/reference-workspace/specs/pre-ship-check.md` "Verdict criteria" + "Quality criteria") demands a long, structured, multi-rule audit document: walk Rule 1 / Rule 2 / ..., cite "specific evidence (paragraph locations, excerpts, prior-piece references)."
- **The channel** (`RETURN_VERDICT_TOOL.reasoning`, `reviewer_agent.py:264-270`) is documented as **"2-5 sentences in your persona's voice."**

A long audit does not fit a 2-5-sentence field. So the model does the natural thing: it writes the full `## Pre-Ship Audit ### Rule 1...` document as a **text block** (intending, presumably, to summarize into ReturnVerdict after), and the loop's `if not tool_uses:` branch (`reviewer_agent.py:1216`) reads that text-only round as terminal → synthesizes `stand_down` → `break`. The real verdict — fully reasoned — is discarded into the dispatcher's last-prose snippet.

**Corollary from the contaminated re-fire (§Contamination): even a NON-silent-exit run never lands the verdict in judgment_log.** Under `bounded`, my re-fire ran 8 rounds, read 9 files, then tried to `WriteFile(standing_intent.md)` — never `WriteFile(judgment_log.md)`, never `ReturnVerdict`. So the audit verdict has no well-fitting output channel *regardless of exit shape*; the silent-exit is the most visible symptom, but the underlying gap is "the long audit verdict has nowhere natural to land."

---

## §Contamination — the re-fire was not a clean repro (and why that's OK)

I fired a re-run (`api/scripts/operator/repro_silent_exit_moat_audit.py`) by flipping moat-thesis `profile.md` status draft→ready_for_review to re-trigger the pre-ship-audit hook. The re-fire was **contaminated**: a later eval-suite pre-flight had flipped `_autonomy.yaml` from `autonomous` → `bounded` at 05-30 06:22:58 (`message: "eval-suite pre-flight: establish default.delegation=bounded"`), *after* the original run. So my re-fire (05-31 23:46) executed under `bounded`, where the Reviewer's terminal WriteFile **queued** as proposal `49779ef9` rather than executing — a different code path than the autonomous original.

**S1 discipline note**: the first receipt I read (the re-fire) looked like "ran 8 rounds, produced zero substrate" — a misleading partial. Chasing it (reading the queued proposal's `decision_context`) surfaced the *prior* standing_intent, which revealed silent-exit **#2** (weekly-corpus-review) that I did not know existed. The contamination accidentally produced a *stronger* result than a clean re-fire would have: two independent self-fired reproductions instead of one induced one.

**Cleanup**: profile.md restored to `ready_for_review` (net-unchanged); contaminating proposal `49779ef9` rejected (`reason: "repro-cleanup: induced under bounded delegation; not an operator decision"`); prior silent-exit standing_intent left intact (honest substrate).

---

## §3 — Receipts

- Repro #1: `execution_events` 2026-05-30 05:54:58 slug=pre-ship-audit status=success tool_rounds=4. Silent-exit standing_intent rev `dispatcher:silent_exit_fallback` same timestamp.
- Repro #2: `execution_events` 2026-05-31 18:02:17 slug=weekly-corpus-review status=success tool_rounds=14 output_tokens=8406. Silent-exit prose preserved in proposal `49779ef9` `decision_context.diff.before`.
- Contaminated re-fire: `execution_events` 2026-05-31 23:46:17 slug=pre-ship-audit status=success tool_rounds=8; wake_queue dedup_key `6f76915b` status=completed; proposal `49779ef9` (now rejected).
- Autonomy flip: `workspace_file_versions` `/workspace/context/_shared/_autonomy.yaml` 05-30 06:22:58 `operator-proxy:scenario-runner:acting-as-yarnnn-author` "establish default.delegation=bounded".
- Render scheduler logs (crn-d604uqili9vc73ankvag) 23:45:22–23:46:17: 9× ReadFile/ListFiles → WriteFile(standing_intent)→QUEUE.
- Code: silent-exit branch `api/agents/reviewer_agent.py:1216`; ReturnVerdict 2-5-sentence channel `:264-270`; spec demand `docs/programs/alpha-author/reference-workspace/specs/pre-ship-check.md`.
- Reproducible:
```sql
SELECT slug, wake_source, status, tool_rounds, output_tokens, created_at
FROM execution_events
WHERE user_id='0b7a852d-4a67-447d-91d9-2ba1145a60d7'
  AND slug IN ('pre-ship-audit','weekly-corpus-review')
  AND created_at >= '2026-05-30'
ORDER BY created_at;
```

---

## §4 — Implication for the fix (recommendation, not landed)

The two intervention shapes ADR-303 named (nudge-then-retry; force-tool-on-terminal) both treat the **symptom** (text-only round) without addressing the **cause** (no channel fits a long verdict). A cause-addressing fix gives the audit verdict a real output channel — e.g., the Reviewer writes the full audit document to `judgment_log.md` via `WriteFile` as the verdict-of-record on audit-shaped wakes, with `ReturnVerdict` carrying just the headline + the judgment_log path. That matches what the model is *already trying to do* (write the long document) instead of fighting it. Design pending (this session, next step). The §2 citation-grounding rule recommendation from the parent `findings.md` is downstream of this — a citation-grounding audit rule only fires if the audit reaches it, which requires the audit to *complete and land*.

---

## Read-state

Diagnosis complete with substrate receipts. The §6 silent-exit is **structural** (2 independent repros, 2 trigger types) — UNKNOWN→STRUCTURAL. Root cause reframed: **channel-shape mismatch** (long audit verdict vs 2-5-sentence ReturnVerdict), not generic action-grammar fumble. Fix design (cause-addressing output channel) is the next step; nothing landed yet.
