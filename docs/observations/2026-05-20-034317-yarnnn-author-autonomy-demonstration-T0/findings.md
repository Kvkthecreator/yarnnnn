# Findings — T0 (yarnnn-author autonomy demonstration baseline)

> **No interpretation at T0.** This folder captures the *before-snapshot* of the autonomy demonstration window. Findings belong in subsequent T+24h / T+48h observation folders after the system has been observed running autonomously.

What this folder establishes:

1. **T0 substrate state captured.** See `PLAYBOOK.md` for the full state declaration + setup history.
2. **No diff to interpret.** Baseline IS endpoint at this instant; `substrate-diff.md`, `decisions.md`, `proposals.md`, `transcript.md`, `token-usage.md` show empty diffs (no events since baseline was taken because baseline IS now).
3. **The autonomy hypothesis being tested:**
   - The Reviewer + System Agent + Orchestration substrate produces material behavior (recurrence fires, judgment_log writes, standing_intent updates, possibly substrate amendments) **without operator-on-behalf interjection** during the elapsed window.

What to look for at T+24h / T+48h:

- pre-ship-audit reactive fire on the seeded `governance-as-trust` piece — fire-or-not is itself a binary finding.
- Scheduled recurrence fires: 3-4 expected within 48h.
- Reviewer-authored revisions on `review/judgment_log.md` + `review/standing_intent.md` substrate.
- Any operator-canon edit (rare, would be highly informative — evaluate against ADR-295 D1-D4 Edit Checklist).
- Any wake failures (round-budget exhaustion, infrastructure errors, missing-substrate errors).

Cross-reference: `PLAYBOOK.md` here, `docs/observations/2026-05-20-034317-adr-292-gap-finding.md` (sibling Hat-A finding from setup work).

Next capture: 2026-05-21 ~03:43 UTC (T+24h).
