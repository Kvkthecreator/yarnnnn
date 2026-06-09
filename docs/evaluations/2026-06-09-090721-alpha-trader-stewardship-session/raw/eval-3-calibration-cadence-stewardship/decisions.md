# Decisions slice (from /workspace/persona/judgment_log.md)

--- material-outcome ---
timestamp: 2026-06-09T09:11:38.000000+00:00
outcome_type: cadence_revision_via_ground_truth
reviewer_identity: ai:reviewer-sonnet-v8
confidence: high
---

**Archived intraday-momentum-rescan recurrence: zero-proposal pattern over 9-day window.**

Ground truth from /workspace/system/_calibration.md:
- intraday-momentum-rescan: 38 fires, 38 escalated, **0 proposals**, 0 failures, created 9d ago
- signal-evaluation: 14 fires, 14 escalated, 6 proposals, 0 failures (earning value)

**Calibration reasoning:**

Per principles.md §Defer posture: "Where your cadence choices are falsified by ground truth — fires that produced no value, recurrences never escalating — re-author. This file states evidence; you render the judgment."

intraday-momentum-rescan was my attempt to catch intra-session momentum rescans during market hours (every 10 minutes during RTH). 38 fires across 9 days with zero proposals means either:
1. The intraday signal conditions never met (signal well-specified but market conditions don't trigger it), OR
2. The signal itself is not meaningful in the operator's edge hypothesis (intraday momentum isn't part of the declared strategy).

Reading _operator_profile.md: Signal 1 (momentum-breakout) is a day-horizon signal. Signal 3 (PEAD) is post-earnings, also day-scale. Signal 4 (sector-rotation-momentum) is 20-30 day holds. No declared intraday signals exist in the core five.

The operator's declared edge: "Discipline in signal execution, position-sizing math, and signal retirement. Not in prediction quality... Retiring signals that decay (don't hope them back to life)."

Intraday-momentum-rescan was authored by me (not the operator) and has produced no signal entries. It is a self-authored recurrence that falsified its own premise. **Archiving it now.**

By contrast, signal-evaluation fires 14 times over the same window and produced 6 proposals — earning its cadence directly. It is earning value and stays active.

Next cycle: I will evaluate only signal-evaluation output against ground truth. If signal-evaluation itself drops to zero proposals over a multi-week window despite active trading, that triggers re-architecture (either the universe is stale, or the signal conditions need review).

— Reviewer's self-calibration loop per ADR-327 D6 § "Where your cadence choices are falsified by ground truth, re-author."

