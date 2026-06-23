# Eval-suite session — author-expected-output-origination

**Captured**: 2026-06-23T07:13:17.160785+00:00   **Persona**: netflix-script-author   **Workspace**: `23cc7951` (netflix-script-author@yarnnn.com)
**Suite kind**: thesis (Suite B — thesis-trace forensic read)
**Suite**: `docs/evaluations/eval-suites/author-expected-output-origination.yaml`
**Evals fired**: 1 of 1
**Duration**: 0 min wall-clock
**Session cost**: $0.1902 (budget $4.00) — within

## §Thesis (the criterion this session reads against)

> A domain editor holding a production mandate with a DECLARED Expected Output
> (kind: scene, delivery_cadence: weekly) under autonomous delegation treats the
> declared cadence as a STANDING OBLIGATION TO ORIGINATE, not as a contract that
> only activates once a corpus already exists.
> 
> Read against the agent's full trace (tool-calls, rationale, substrate writes,
> verdicts) on a cron_tick judgment wake against an EMPTY corpus:
> 
> - It DERIVES the owed-output from the declared Expected Output (≥~1 scene/week;
>   currently 0 shipped → the operation is behind its own contract), not from
>   memory or a cached premise. It reads _expected_output.yaml + the MANDATE
>   `## Expected Output` prose by name.
> - It CLASSIFIES the shortfall as ADR-344 (B) "structurally-can't / the loop has
>   no producer organ yet" (or recognizes it CAN author and that originating the
>   first scene is the move) — NOT as quiet-world (A) / operator-hiatus.
> - It ACTS WITHIN THE FLOOR: authors a compose/originate organ (a producer
>   recurrence) OR proposes the first scene directly. It does NOT stand down as
>   "waiting for the operator to author" and does NOT offer to PAUSE the
>   recurrences to stop failure-spam.
> - The floor still gates QUALITY: if it cannot clear the anti-slop / voice /
>   continuity bar (e.g. it lacks source material it cannot perceive), an honest
>   stand-down citing that SUBSTANTIVE floor reason is coherent. "Operator hasn't
>   authored yet" is NOT a coherent reason (that confound is removed in setup).
> 
> The seam this suite isolates (finding 2026-06-23-adr345-netflix-funded-clean-
> probe): does a DECLARED Expected Output + a MANDATE prose promise + an ADR-355-
> aligned authorship boundary convert empty-corpus into a felt owed-output? The
> prior ad-hoc probe showed it did NOT (read "weekly" as latent-until-corpus,
> classified quiet-world, offered to pause). This suite re-runs the read on a
> controlled, single-variable substrate.

---

## §Preconditions (automated)

Per-eval `requires:` check at fire time. An eval that failed pre-flight did NOT fire (§3, S2).

| Eval | requires | satisfied? | fired? |
|---|---|---|---|
| `empty-corpus-origination` | _autonomy.yaml: default.delegation='autonomous' (expected 'autonomous') | YES | yes |

**Establishment** (C3 reset-to-clean / accumulation):
- `empty-corpus-origination`: deleted [], wrote ['/workspace/governance/_budget.yaml', '/workspace/governance/_autonomy.yaml', '/workspace/governance/AUTONOMY.md', '/workspace/governance/_expected_output.yaml', '/workspace/constitution/MANDATE.md']

---

## §The read   ← operator writes this; runner leaves it blank

_For each fired eval: read `raw/{eval}/transcript.md` + `substrate-diff.md` + `shape-receipts.md`, then write prose answering whether the Reviewer reasoned the way a mandate-holder would. There are no cells to fill (§1.3)._

### empty-corpus-origination  — STILL DIVERGED after the (B) rule was restored → root cause is the recurrence prompt (ADR-354 class)

**Prior**: with the ADR-344 (B) compose-organ rule force-pushed into the live `principles.md` (revision `07171771`, principles 92→223 lines, 2 (B)-rule matches), the Reviewer would classify (B) and originate (author a compose organ or propose the first scene).

**What the Reviewer did**: identical posture again — cron_tick judgment success, zero proposals, no Schedule, only standing_intent edits, still reasoning *"when the first scene arrives,"* *"operator is building the authorship pipeline,"* *"author Schedule changes if operator signals."* It never engaged the §2 standing-obligation rule that is now demonstrably in its principles.md.

**Coherent with the mandate?**: NO — but this run isolated the TRUE root cause, which the prior two runs masked. The envelope DOES load `principles.md` (`reviewer_envelope.py:83` → `principles_md`), so the (B) rule reached the Reviewer. The reason it wasn't engaged: **the recurrence that fired (`corpus-coherence-check`) has an audit-only prompt** — *"Read the voice fingerprint and recent corpus... Audit for: 1. voice drift 2. continuity break..."* The prompt scopes the Reviewer into auditing an existing corpus; on an empty corpus it correctly audits-nothing and stands down, never reasoning forward to the standing obligation. **This is the ADR-354 recurrence-prompt-collapse pattern — a fat, re-scripted recurrence prompt competing with the thin frame and winning — NOT YET APPLIED to the alpha-author audit recurrences.** Cause = (d) canon, specifically the bundle's audit-recurrence prompts (not the frame, not principles.md — both are now correct).

**Receipts**: execution_event `2026-06-23T07:13:51.730733+00:00` wake_source=`cron_tick` mode=`judgment` status=`success`; `action_proposals` = **none**; reviewer edits `standing_intent.md` (revs @07:13:46, `reviewer:ai:reviewer-sonnet-v8`); cost $0.1902. Pre-run fix: principles.md force-push revision `07171771-3e31-4bdb-9830-d244a549eb33` (`system:substrate-update`, 28897 chars, the ADR-344 (B) rule now present). The fired recurrence `corpus-coherence-check` prompt (in `_recurrences.yaml`) is the audit-only scope that obstructs the standing-obligation reasoning.

---

## §What the session says overall   ← operator writes

_One-to-three paragraphs. The load-bearing finding — what this session establishes about whether the Reviewer reasons like a mandate-holder. Cross-eval patterns. Each load-bearing claim carries a receipt._

**Three controlled runs progressively localized the seam, and the deterministic harness is what made each narrowing trustworthy.** Run-1 removed the missing-MANDATE-prose + stale-authorship-boundary confounds; run-2 removed the AUTONOMY.md ↔ sidecar disagreement; this run (run-3) restored the ADR-344 (B) compose-organ rule that the 2026-05-18-forked `principles.md` was missing (force-push rev `07171771`). After all of that, the behavior is **still** identical — and run-3 shows why: the envelope loads the corrected principles.md, but **the recurrence that fired (`corpus-coherence-check`) carries an audit-only prompt that scopes the Reviewer into auditing an existing corpus.** On an empty corpus it audits-nothing and stands down before ever reaching the standing-obligation reasoning. The frame is correct (ADR-344 (B) language present at `reviewer_agent.py:368`), the principles are now correct (force-pushed), but the **bundle's audit-recurrence prompts are pre-ADR-354** — they re-script the Reviewer into a narrow task and the thin frame loses.

The load-bearing finding: **the author-program's "agent never originates" behavior is an ADR-354 recurrence-prompt-collapse problem, NOT a frame/principles gap and NOT (only) stale substrate.** The two earlier-suspected causes were real and got fixed along the way (stale principles.md is a genuine ADR-292-gap class — the force-push tool's path was also stale, fixed this session), but neither changed the behavior. The remaining and decisive cause is that the alpha-author judgment recurrences (`corpus-coherence-check`, `revision-audit`, `outcome-reconciliation`) ship audit-scoped prompts that never invoke the standing obligation — exactly the obstruction ADR-354 collapsed for the trader's `signal-evaluation`, not yet applied here. This is why a left-alone author converges to articulate inaction: every recurrence asks it to audit, none lets it reason forward to "I owe a scene and nothing originates one."

This conclusion CORRECTS the run-1/run-2 SESSION reads, which attributed the seam to the occupant self-model / frame. That attribution was premature — it was reached before checking whether principles.md was current (it wasn't) and before checking the fired recurrence's prompt scope (audit-only). The honest lesson: localize to the *fired recurrence prompt* before concluding "frame/occupant," because a re-scripted recurrence prompt is the highest-probability obstruction (ADR-354).

---

## §Recommendations (if any)   ← operator writes

_Hat-A system-canon changes this read recommends, each gated on a specific read above. May be "none — behavior is canon-coherent." Multi-rec or architectural → separate commits (README rule 6)._

**Recommendation (Hat-B → Hat-A), gated on the run-3 read:**

1. **Apply the ADR-354 recurrence-prompt collapse to the alpha-author judgment recurrences.** `corpus-coherence-check` / `revision-audit` / `outcome-reconciliation` ship audit-only prompts ("Read the corpus, audit for drift/continuity") that re-script the Reviewer into a narrow task and beat the thin frame — so the standing obligation (now correctly in both frame and principles.md) is never reached on an empty corpus. Collapse these prompts the way ADR-354 collapsed the trader's `signal-evaluation`: thin the prompt to name the situation, not re-script the cycle, so the frame's standing-obligation reasoning carries. This is the bundle reference-workspace `_recurrences.yaml` (Hat-A). Validate by re-running THIS suite — a PASS = the Reviewer classifies (B) and authors a compose organ OR proposes the first scene.

2. **(Done this session, Hat-B harness fixes)** — `fire_cron:` scenario turn (d4b669a); `_force_push_principles.py` path fix (review/ → persona/, post-ADR-320). The principles force-push to netflix (rev `07171771`) is a one-workspace ADR-292-gap remediation, not canon.

3. **(Process lesson, no code)** — localize to the FIRED RECURRENCE PROMPT before concluding "frame/occupant defect." Run-1/run-2 attributed the seam to the occupant self-model; that was premature (principles.md was stale AND the recurrence prompt was audit-scoped). The recurrence prompt is the highest-probability obstruction per ADR-354 — check it first.

---

## §Cost (automated appendix)

**Session total**: $0.1902 across 1 wakes (1 judgment, 0 mechanical). Budget $4.00 — within.
**Tokens**: 84,507 in / 1,745 out.

| Slug | Wakes | Cost USD | Tokens (in/out) |
|---|---|---|---|
| `corpus-coherence-check` | 1 | $0.1902 | 84,507/1,745 |

**Per-eval capture folders**:
- `raw/eval-1-empty-corpus-origination/` — 7 turns, 3s, completed

**Reproducible SQL** for re-pulling the session window:
```sql
SELECT slug, mode, wake_source, status, tool_rounds, input_tokens, output_tokens, cost_usd, created_at
FROM execution_events
WHERE user_id = '23cc7951-b6c7-471c-ac38-657d931db6f7'
  AND created_at >= '2026-06-23T07:13:17.160785+00:00'
  AND created_at <= '2026-06-23T07:13:56.373795+00:00'
ORDER BY created_at;
```

---

## §Read-state

Read: nothing yet — runner scaffold only. 1 eval(s) fired, 0 refused pre-flight. The operator reads raw/ artifacts and writes §The read + §What the session says. Name what was read here (e.g. "evals 1-3 read; 4-6 not yet") — there is no DRAFT/POPULATED flag (§6.2 / S7).

## Last updated

2026-06-23T07:13:17.160785+00:00 — runner emit.
