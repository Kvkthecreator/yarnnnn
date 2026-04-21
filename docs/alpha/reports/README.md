# Alpha-1 Weekly Reports

**Two reports per persona per week.** Sunday evening cadence.

Filenames:
- `week-{N}-{persona}-A-system.md` — Objective A (system validation)
- `week-{N}-{persona}-B-product.md` — Objective B (money-truth validation)

Never combine. Never skip B even when data is thin — thin B report
honestly written is more valuable than omission.

## Why two reports

Alpha-1 validates two objectives simultaneously. Same substrate, different
framings:

- **A-system** reader: KVK-as-architect + fresh Claude sessions + future
  ADR drafting. Asks "does YARNNN work as a platform?"
- **B-product** reader: KVK-as-trader-now + KVK-as-trader-future-self
  reviewing Alpha-2 readiness. Asks "does YARNNN help me make money?"

Reports read the same data (`_performance.md`, `decisions.md`,
observation notes, activity log). They differ in what they emphasize
and what question they answer.

## Templates

Canonical templates + rules in
[DUAL-OBJECTIVE-DISCIPLINE.md §dual-weekly-report-templates](../DUAL-OBJECTIVE-DISCIPLINE.md#dual-weekly-report-templates).

### Objective A template (brief skeleton — full template in discipline doc)

```markdown
# Week {N} — {persona} — Objective A (System)
**Range:** {start} → {end}

## What worked
## What surfaced as friction
  ### systematic-workflow
  ### ui-ux
  ### qualitative-agent-behavior
## ADR candidates this week
## Prompt-tweak backlog
## Component-patch backlog
## Phase-transition signal
## What remains unverified
```

### Objective B template (brief skeleton)

```markdown
# Week {N} — {persona} — Objective B (Product)
**Range:** {start} → {end}
**Starting equity:** $X  |  **Ending equity:** $Y  (change $Y-X, %)

## Capital trajectory
## Per-signal attribution
## Reviewer calibration
## Decisions made this week
## Honesty check (five required questions)
## Hypothesis status
## Decision impact (forward-looking)
```

## Index of reports

| Week | Persona | A-system | B-product |
|---|---|---|---|
| _(no reports yet)_ | | | |
