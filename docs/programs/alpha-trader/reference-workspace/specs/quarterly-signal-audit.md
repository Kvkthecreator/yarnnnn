# Quarterly Signal Audit Spec

Spec for the `quarterly-signal-audit` recurrence (fires Mar 31 / Jun 30
/ Sep 30 / Dec 31 at 18:00 ET). The Reviewer reads this spec when
producing the audit report.

## Purpose

Operator-discipline ritual. Prevents letting decayed signals linger;
surfaces research candidates for new signals; **never** auto-modifies
`_operator_profile.md`.

The Reviewer prepares the analysis. The operator ratifies all
signal-roster decisions.

## Output target

`/workspace/reports/quarterly-signal-audit/{date}/output.md`

## Required sections (in order)

### 1. `## Signal Performance Summary`
- Table per signal:
  ```
  | Signal | Lifetime fills | Last-40 Sharpe | Lifetime Sharpe |
  |--------|----------------|----------------|-----------------|
  | IH-1   | 248            | 1.42           | 1.61            |
  ...
  ```
- Compare last-40 Sharpe against the declared baseline in
  `_operator_profile.md` for each signal.
- Note any signal whose last-40 Sharpe < 50% of lifetime Sharpe
  (a structural-drift indicator).

### 2. `## Retirement Candidates`
- Each signal that has crossed a retirement guardrail from `_risk.md`.
- For each: cite the specific guardrail crossing with quantitative
  evidence (the metric, the threshold, the actual value, the date
  of crossing).
- Recommend retire / re-tune / watch with reasoning.
- Empty section ("No retirement candidates this quarter.") when none.

### 3. `## Retune Proposals`
- For signals approaching but not crossing guardrails, propose
  parameter tweaks (e.g., wider stops, different timeframe, narrower
  universe).
- Each proposal: state the current parameter, the proposed
  parameter, the quantitative justification.

### 4. `## New Signal Research Candidates`
- Patterns observed in fill history that suggest a new signal
  could be derived (without committing the operator).
- Each candidate: the pattern, the evidence (which past trades
  exhibit it), the rough sizing of opportunity.

### 5. `## Operator Decision Block`
- **LEAVE EMPTY.** This is where the operator fills in their
  decisions after reading the analysis above.
- Render exactly:
  ```
  ## Operator Decision Block
  <!-- Operator fills in decisions below after reviewing analysis -->

  - Signals to retire:
  - Signals to re-tune (with new params):
  - New signals to research further:
  - No-action items reviewed:
  ```

## Quality criteria

- Every signal's last-40 Sharpe + expectancy surfaced with
  comparison to declared baseline.
- Retirement recommendations cite specific guardrail crossings
  from `_risk.md`. Never recommend retirement on opinion alone.
- The recurrence does NOT mutate `_operator_profile.md` autonomously.
  The operator ratifies all signal-roster changes by editing
  `_operator_profile.md` themselves after reading this report.
- Length: 2,000–3,500 words.
- Section partials in
  `/workspace/reports/quarterly-signal-audit/{date}/sections/`:
  `1-signal-performance-summary.md`, `2-retirement-candidates.md`,
  `3-retune-proposals.md`, `4-new-signal-research-candidates.md`,
  `5-operator-decision-block.md`.
