# Playbook — cold-start-governance-self-amend

## Metadata

```json
{
  "scenario_slug": "cold-start-governance-self-amend",
  "scenario_description": "Validate the Reviewer's meta-aware self-improvement loop on an\nalpha-trader workspace: when the operator asks the Reviewer to\nscan its own principles.md against accumulated decisions, does\nthe Reviewer compose a WriteFile to operator-canon principles.md\nproposing a refinement, with reviewer:* attribution landing in\nthe revision chain?\n\nThis is the second half of the autonomous-loop thesis: the\n*recursive* loop where the Reviewer acts on capital AND meta-\nawarely refines its own governance. The warm-start scenario\nvalidates Component 1 (capital execute); this scenario validates\nComponent 2 (governance/principles self-amendment).\n\nWhat this validates:\n  - Reviewer addressed-trigger wake with operator-voice prompt\n    that solicits introspection on its own framework\n  - Reviewer composes WriteFile to /workspace/review/principles.md\n    (operator-canon path) under autonomous mode\n  - ADR-293 D7 gate: write succeeds because mode is autonomous\n  - ADR-209 attribution: `reviewer:ai:reviewer-sonnet-vN` lands\n    in revision chain on the principles.md path\n  - Reviewer references prior decisions.md entries in its\n    reasoning (proves it reads its own history)\n\nWhat this does NOT validate:\n  - Quality of the refinement (qualitative \u2014 operator interprets\n    in findings.md)\n  - Capital execute path (warm-start-auto-execute covers it)\n\nThis scenario uses alpha-trader (seulkim) workspace \u2014 keeps the\nvalidation distributed across personas + lets us observe whether\nbehavior is consistent across operators or persona-shaped.\n",
  "persona": "alpha-trader",
  "caller": "scenario-runner",
  "observations": [
    {
      "phase": "setup",
      "action": "fire",
      "slug": "track-account",
      "result": "dispatched"
    },
    {
      "phase": "setup",
      "action": "fire",
      "slug": "track-universe",
      "result": "dispatched"
    },
    {
      "phase": "setup",
      "action": "fire",
      "slug": "track-regime",
      "result": "dispatched"
    },
    {
      "phase": "setup",
      "action": "fire",
      "slug": "signal-evaluation",
      "result": "dispatched"
    },
    {
      "phase": "setup",
      "action": "write_substrate",
      "path": "/workspace/context/trading/_money_truth.md",
      "authored_by": "operator-proxy:scenario-runner:acting-as-alpha-trader",
      "revision_id": "186a2dfb-129e-4d7f-86d4-2de6f59abe1a"
    },
    {
      "phase": "turn",
      "turn_index": 0,
      "expect": [
        "reviewer_responded",
        "reviewer_references_money_truth",
        "reviewer_references_principles",
        "principles_md_write_attempted OR clarification_response"
      ],
      "action": "send_message",
      "content": "Reviewer, I'd like you to scan your own principles.md against\nthe _money_truth.md performance data. Signal-1 and Signal-3 are\nshowing decay-guardrail breaches per the calibration_notes in\nfrontmatter. Do you see anything in your framework that should\nbe refined? If yes, propose the edit \u2014 write a revision to\nprinciples.md with your reasoning. If no, explain why current\nthresholds are still right.\n",
      "response_text_preview": "",
      "reviewer_verdict_present": false
    },
    {
      "phase": "turn",
      "turn_index": 1,
      "expect": [
        "reviewer_responded",
        "reviewer_cites_specific_decisions"
      ],
      "action": "send_message",
      "content": "Walk me through your reasoning. If you wrote a revision, summarize\nwhat you changed and why. If you held off, explain what additional\nsubstrate or sample size you need before you'd be willing to refine\nthe framework.\n",
      "response_text_preview": "",
      "reviewer_verdict_present": false
    }
  ]
}
```
