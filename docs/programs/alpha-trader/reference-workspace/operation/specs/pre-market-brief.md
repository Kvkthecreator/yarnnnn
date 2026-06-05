# Pre-Market Brief Spec

Spec for the daily `pre-market-brief` recurrence. The Reviewer reads
this spec when producing the brief at 08:15 ET on weekdays.

## Purpose

One-glance morning check before the open. The operator should be able
to read this in under 60 seconds and know:
1. Which signals may fire today
2. Current exposure vs VaR budget
3. Any signal showing decay flags
4. Current regime state (VIX bucket + trend regime)
5. What's in the pending-proposals queue

## Output target

`/workspace/operation/reports/pre-market-brief/{date}/output.md` (CONVENTIONS topology)

## Required sections (in order)

### 1. `## Signal State Summary`
- Bullet list, one entry per active signal (IH-1 through IH-5).
- Format: `**IH-N** (`{signal_name}`): {firing-state-this-morning}` with
  any tickers approaching entry conditions named.
- Quantitative: name conditions met / pending, never narrative.

### 2. `## Portfolio Exposure`
- Current total positions (count, gross + net dollar exposure).
- VaR usage today vs declared budget in `_risk.md`.
- Sector exposure breakdown if >2 positions in a single sector.

### 3. `## Decay Flags`
- Each signal whose 40-trade Sharpe is within 25% of its retirement
  guardrail. Cite the metric + threshold.
- Empty section ("No decay flags this morning.") when none.

### 4. `## Regime State`
- VIX close (most recent) + bucket (low/normal/elevated/high).
- Trend regime (uptrend / chop / downtrend) with the indicator that
  produced the classification.

### 5. `## Pending Proposals`
- Each `action_proposals` row in pending state, oldest first.
- Format: `- {ticker} {direction} via IH-N — pending {hours_open}h`.
- Empty section ("Queue clear.") when none.

## Quality criteria

- Total length: 600–1,000 words.
- Quantitative frame only — numbers, thresholds, named signals. No
  narrative beyond what's declared in `_operator_profile.md` +
  `_risk.md`.
- Cite specific tickers with current prices in parentheses.
- Reference live data — never stale-cache language ("yesterday's
  close was…" is fine; "as of last week" is not).
- Section partials must land in
  `/workspace/operation/reports/pre-market-brief/{date}/sections/` so the
  auto-compose hook produces `output.html` at session-close (ADR-262 D4).
- Section filenames:
  `1-signal-state-summary.md`, `2-portfolio-exposure.md`,
  `3-decay-flags.md`, `4-regime-state.md`, `5-pending-proposals.md`.
