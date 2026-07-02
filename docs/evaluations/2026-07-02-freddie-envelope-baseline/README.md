# Freddie envelope refactor — Rung-0 baseline (addressed turns)

**Date**: 2026-07-02
**Hat**: B (evaluation — expected vs observed)
**Plan**: [docs/analysis/freddie-envelope-refactor-plan-2026-07-02.md](../../analysis/freddie-envelope-refactor-plan-2026-07-02.md)
**Harness**: `api/scripts/operator/probe_freddie_addressed_baseline.py` — 6 byte-stable steward-shaped asks through the real addressed wake source (`services/wake_sources/addressed.py::stream`), local code, bare-kernel persona workspace (`4c106786…`).
**Code state**: main @ `85e3d19` (pre-Rung-1 — the un-re-carved `_TRIGGER_FRAMING`), model routing = production (addressed → Haiku 4.5, 20 rounds).

## What this captures

Per-turn: wall seconds · rounds · tool calls (names, order) · final-response chars · close rate · full event transcript (`turn-N.json`). Every refactor rung re-runs the same asks and diffs against this.

## Workspace-state caveats (read before diffing)

- The bare-kernel workspace carries residue from the ADR-383 bare-steward probe (seeded `operation/memory/q3-pricing-note.md` + `competitor-scan.md` and their revision history). The smoke turn (pre-baseline) already derived them into `operation/competitors/` + `operation/decisions/` via gated proposals. Substrate is therefore NOT identical between runs — turns mutate the workspace (proposals, judgment_log, notes). Diff on STRUCTURAL metrics (rounds, tool-call count/mix, response length, close rate, liturgy writes on read-only asks), not on exact content.
- Ask #2 (the pricing note) intentionally writes; asks #1/#3/#4/#5/#6 are read-shaped — WriteFiles on those are the ceremony-tax signal.

## Smoke finding (pre-baseline, ask #1 only)

"What's in my workspace right now?" → 61s, 12 rounds, 24 tool calls (10+ ReadFiles despite the envelope pre-loading governance, GetSystemState ×1, ListRevisions/ReadRevision chains, 3 WriteFiles incl. `persona/judgment_log.md`), final response 509 chars.

Posture verdict: CORRECT (found unplaced intake, derived with `derived_from` citations, routed writes through the proposal gate, concise final response). Economy verdict: POOR (re-reads pre-loaded substrate; liturgy writes on a read question; 12 rounds for a lookup). The operator-perceived wordiness is dominated by the per-tool narration stream (one chat line per action), not the final response.

## Results — addressed set (6 asks, Haiku 4.5, 20-round budget)

6/6 closed, 0 errors. **Mean: 33.6s wall · 6.0 rounds · 11.2 tool calls · 495 response chars.**

| # | ask (shape) | wall | tools | response | notes |
|---|---|---|---|---|---|
| 1 | what's in workspace (read) | 57s | 23 | 608c | 4× SearchFiles, 3× ListRevisions, closes with a liturgy WriteFile |
| 2 | keep a pricing note (write) | 18s | 3 | 364c | **efficient** — read, list, write. The good shape. |
| 3 | summarize activity (read) | 47s | 14 | 505c | liturgy WriteFile on a read ask |
| 4 | anything out of place (read) | 24s | 11 | 476c | no write — clean |
| 5 | connections/sources (read) | 15s | 2 | 617c | **efficient** — list_integrations + GetSystemState |
| 6 | what to look at tomorrow (read) | 40s | 14 | 400c | liturgy WriteFile on a read ask |

**Patterns (the Rung-1/2 targets):**
- **Re-reading pre-loaded substrate** on every heavy turn (ReadFile on MANDATE/principles/etc. that the envelope already carries) — the framing's "do NOT ReadFile these" is not holding on Haiku.
- **Liturgy writes on read-shaped asks** (3 of 5): standing_intent/judgment_log/notes writes the ceremony encourages — the Rung-2 target.
- Final responses are consistently CONCISE (~400–600 chars) and correctly steward-voiced. The operator-perceived wordiness is the **narration stream** (one chat line per tool action; 11–23 actions/turn), which rungs 1–2 shrink by shrinking the action count.
- When the ask maps to a single obvious tool (asks 2, 5), Freddie is already efficient — the inefficiency is specifically on OPEN-ENDED asks, where the framing offers a menu instead of a decision procedure.

## Results — reactive side (bare-steward --live wake, same day)

Transcript: `bare-steward-live-wake.json`. Three-halves heuristic: **PASS** (stewardship acted, zero capital terms, no standby-standdown). Economy/contract findings:
- 16 tool events; **14 of them ReadFiles of envelope-pre-loaded files** (MANDATE, AUTONOMY, reflection, _workspace_guide, system/_playbook).
- Acted correctly on the unplaced dump (gated DeleteFile + standing_intent WriteFile, both pending proposals); did NOT touch the mis-attribution half this wake.
- **Closed WITHOUT ReturnVerdict** (verdict=None, acted=True) — the ADR-360 honest-terminal fault shape on a 20-round Haiku recurrence wake. Baseline close-rate on reactive: 0/1.

## Probe-harness note

`probe_freddie_bare_steward.py` was stale against ADR-393 (passed the deleted `mode=` field to `Recurrence`) — fixed in this commit. The addressed harness double-counted tool_start/tool_end in the smoke run — fixed before the baseline set (counts are tool_start only).
