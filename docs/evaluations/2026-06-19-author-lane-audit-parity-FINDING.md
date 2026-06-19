# Finding — author-lane audit: no execution bug (the trader's gap doesn't exist here); the real gap was a contaminated DAG + an unauthored compose organ that already existed in canon

**Date**: 2026-06-19
**Hat**: B (evaluation). Cleanup + the operator cadence declaration were executed in-session (operator delegated depth fully); no system-canon change was needed.
**Subject**: applying the trader-lane discipline (clean substrate → find the real execution blocker → set up an autonomous throughput test) to yarnnn-author.
**Sibling**: `2026-06-19-execution-emit-contract-gap-FINDING.md` (the trader's serialization bug) + `2026-06-19-reliance-axis-mechanized-FINDING.md` (the reliance instrument).

---

## Criterion declared (discipline rule 0)

Measured against the same one-liner the trader audit used, re-cast for the author program: *does the author loop, on a clean workspace under autonomous delegation, ORIGINATE the pieces it is accountable for — or does it only audit?* Operationalized: (1) is the revision DAG clean enough that the Reviewer perceives true state (not test residue), and (2) is there a live organ that originates a piece on cadence, with the anti-slop/voice floor intact?

**The structural asymmetry the audit must respect (not flatten).** The trader's consequential act is `capital` family — irreversible, gated by a risk floor, serialized into a broker order. The author's act is `WriteFile` / `substrate` family — **reversible, auditable, revertible** (ADR-209). So the trader's execution bug (a correct judgment serialized into a malformed order) **has no author analog**: there is no order to malform, no emit contract to drift. Copying the trader's fix to the author would be solving a problem that doesn't exist here. The reliance ledger reads `RELIANCE-ZERO` for the author **by construction** (it counts irreversible consequential families; the author has none), not because of a bug.

---

## What the audit found

### 1. The real gap is ADR-344 Path B — and it was already named on this very workspace

Pre-clean, every author recurrence was an **audit or review**: `corpus-coherence-check`, `revision-audit`, `quarterly-voice-audit`, `weekly-corpus-review`, `outcome-reconciliation`. Not one **originates** a piece. This is verbatim the ADR-344 "structurally-can't" (Path B) condition: *a left-alone alpha-author converges to articulate inaction — its recurrences all audit, none originates; stays coherent + flat forever = autonomy-in-costume.* Your own ADR-344 validation (2026-06-18, this workspace) already classified it (B) and the Reviewer **offered to author the missing compose organ** via Clarify — an offer that was never accepted, so the loop never closed.

### 2. The compose organ already exists in canon (ADR-333) — it was just never authored into a live recurrence

The fix is NOT to hardcode a compose recurrence into the bundle — that would violate ADR-275 D1 (bundles ship no judgment/deliverable cadence; the Reviewer authors it). The bundle is **already correct**: `governance/_preferences.yaml` declares `compose-piece` (ADR-333: "the program's first PRODUCTION (non-audit) deliverable... cadence: null... the Reviewer authors the actual recurrence from judgment + operator intent"), `active: true`, with a real spec at `operation/specs/piece-composition.md` (108 lines). The organ was declared but dormant: `cadence: null` means "compose when the operator has a piece, not on a clock," so on a contaminated workspace it never fired.

### 3. The DAG was contaminated — same class as kvk, same fix

161 of 1,004 revisions were operator-proxy (test/eval) authored; 125 carried test/fixture/probe/eval messages. The Reviewer reads history (verified 2026-06-18), so it did not perceive true dormancy — the exact "head-state reset insufficient" problem prior findings flagged. Needed the same clean-slate treatment kvk got.

---

## What was done (operator delegated depth fully; balance preserved)

1. **Clean + reactivate** via the canonical persona-agnostic L2 path (`services.workspace_purge.clear_workspace_for_user` — the same body the HTTP route + harness use; Singular Implementation, no forked script). Preserves the `workspaces` row → **balance $58 → $58 intact**. Re-forks the captured program (alpha-author).
   - Purged: 1,004 revisions, 86 files, 6 proposals, 9 chat sessions, 3,747 activity rows, 44 wake_queue, 5 tasks.
   - Result: 40 files, **45 revisions (0 fake operator-proxy left — the 161 contaminated rows gone)**, 0 proposals, 7 recurrences (incl. `compose-piece`), delegation autonomous, anti-slop floor present in `principles.md`.

2. **Declare the compose cadence** (operator declaration per ADR-275, NOT a bundle change): `governance/_preferences.yaml` `compose-piece.cadence: null → "0 16 * * 3"` (Wednesday 16:00 UTC weekly), written through `authored_substrate.write_revision` with operator-proxy attribution (revision `a66020f5`). This is the throughput-test parity with the trader's "trade actively" — a declared cadence the Reviewer reads and authors the originate recurrence from, on its next wake. The anti-slop/voice floor gates every composed piece (it is NOT a quota — ADR-345 Goodhart guard).

---

## What is now true (and the one remaining step that is the Reviewer's, not ours)

The author workspace is clean, autonomous, floor-intact, with a **declared weekly compose cadence**. Per ADR-275, the live `tasks` index still shows `compose-piece` at `schedule: null` — **the Reviewer authors the actual `Schedule(action="update", schedule="0 16 * * 3")` from the operator declaration on its next judgment wake.** That authoring step is the system's job, by design (the operator declares *what + when*; the Reviewer decides *how* and authors the cadence). Watching whether the Reviewer (a) reads the new preference, (b) authors the compose recurrence, and (c) then actually originates a floor-passing piece on Wednesday is the ADR-344 Path-B loop closing for real — the thing the 2026-06-18 Clarify left open.

**The honest contamination note:** the clean DAG now carries exactly **1** operator-proxy revision — my own cadence declaration (`a66020f5`). That is legitimate operator authorship (a config edit), not test residue, but it means the DAG is not pristine of proxy attribution. For dormancy-perception it is inert (a preference edit, not a fabricated piece).

---

## The parity, stated plainly

| | Trader (kvk) | Author (yarnnn-author) |
|---|---|---|
| Consequential act | `capital` (irreversible, broker order) | `WriteFile` (reversible substrate) |
| Execution blocker found | **emit-contract serialization bug** (stop under wrong key) — FIXED (`f58cf99`) | **none of that class** — reversible act, no emit contract |
| Real gap | none beyond the bug | **ADR-344 Path B** — no organ originates a piece |
| Organ status | signal-evaluation existed + worked | `compose-piece` existed in canon, never authored into a live recurrence |
| DAG contamination | 161 proxy revs (cleaned) | 161 proxy revs (cleaned) |
| Fix | code fix + clean + reactivate | clean + reactivate + **operator declares compose cadence** (no code, ADR-275-respecting) |
| Throughput-test ready? | yes (awaits an RTH signal) | yes (awaits the Reviewer authoring the recurrence + a Wednesday) |
| Reliance ledger | RELIANCE-ZERO (real, post-clean) | RELIANCE-ZERO (by construction — reversible family) |

Both lanes are now clean, autonomous, floor-intact, and set up to ORIGINATE on cadence. Neither has yet produced an autonomous consequential output — the trader awaits a live RTH signal, the author awaits the Reviewer authoring its compose recurrence + the first Wednesday. That is the right place to be: the machinery is ready on both lanes, and the next move is the system's, not ours.

---

## Receipts

| Claim | Receipt |
|---|---|
| All author recurrences were audits, none originate | pre-clean `tasks`: corpus-coherence-check, revision-audit, quarterly-voice-audit, weekly-corpus-review, outcome-reconciliation |
| compose-piece exists in canon (ADR-333) | bundle `governance/_preferences.yaml` deliverable_preferences slug=compose-piece, active:true, spec=piece-composition.md |
| DAG was contaminated | pre-clean: 161 operator-proxy revs / 125 test-message revs of 1,004 total |
| Clean preserved balance | L2 `clear_workspace_for_user`: balance_usd 58.0 → 58.0 (workspaces row untouched) |
| Post-clean state | 40 files, 45 revisions, 0 fake proxy revs, 0 proposals, 7 recurrences, autonomous, anti-slop floor present |
| Compose cadence declared | `_preferences.yaml` rev `a66020f5`: compose-piece cadence null → "0 16 * * 3" (operator-proxy attribution) |
| No trader-style execution bug exists for the author | author proposal family = substrate (reversible) only; reliance ledger zero by construction |
