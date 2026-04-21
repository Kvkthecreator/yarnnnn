# Alpha-1 Observations

One note per friction / surprise / qualitative-agent-behavior event.
Filename: `{YYYY-MM-DD}-{persona}-{slug}.md`

## Template (copy into new note)

```markdown
# {YYYY-MM-DD} — {persona} — {one-line summary}

## Classification
- **Objective:** [A-system | B-product | both]
- **Within-A scope:** [systematic-workflow | ui-ux | qualitative-agent-behavior | N/A]
- **FOUNDATIONS dimension:** [Substrate | Identity | Purpose | Trigger | Mechanism | Channel]
- **Severity:** [dead-stop | cognitive-load | surprise | aesthetic]
- **Resolution path:** [prompt-tweak | component-patch | ADR-candidate | persona-identity-edit | real-money-observation-only | harness-extension]
- **Money impact:** [direct-capital | decision-impact | none]

## Context
What was I trying to do? (include persona + access mode)

## What happened
What the cockpit / Reviewer / agent actually did.

## Friction
What was harder, slower, less legible, or surprising than it should be.

## Hypothesis
What change would resolve this? Be specific — file path, prompt section, ADR-candidate-name, or "observe further before acting."

## Counterfactual (Objective B only)
If money impact: what would have happened without YARNNN? Would decision quality or outcome differ?

## Links
- Proposal ID / decision.md entry / task output / substrate file paths
- Related observations (same-theme cluster)
```

## Rules

- **R1:** if a note can't classify on any axis, it's not an observation — it's a private thought or todo. Don't write it here.
- **R2:** "Cockpit slow" is incomplete; "Cockpit slow AND I missed a trade" is complete. Always ask the money-impact question on UX notes.
- **Empty sections are OK** — they signal which axes the observation touches.
- **Authoritative schema** + anti-drift rules: [DUAL-OBJECTIVE-DISCIPLINE.md](../DUAL-OBJECTIVE-DISCIPLINE.md).

## Index of notes

(Add entries as notes land. Keep chronological + searchable.)

| Date | Persona | Summary | Objective(s) | Resolution path |
|---|---|---|---|---|
| 2026-04-21 | alpha-trader | [Cockpit first-run semantically empty](./2026-04-21-alpha-trader-cockpit-first-run-semantically-empty.md) | A-system (ui-ux) | component-patch |
| 2026-04-21 | alpha-trader | [Phase-1 seeding bypassed architecture for 3/5 identity-domain files](./2026-04-21-alpha-trader-phase-1-seeding-bypassed-architecture.md) | A-system (systematic-workflow) | ADR-candidate (×3) |
| 2026-04-21 | alpha-trader | [POST /api/tasks dispatches through ManageTask (architectural fix shipped)](./2026-04-21-alpha-trader-tasks-route-dispatch-fix.md) | A-system (systematic-workflow) | component-patch (landed) |
