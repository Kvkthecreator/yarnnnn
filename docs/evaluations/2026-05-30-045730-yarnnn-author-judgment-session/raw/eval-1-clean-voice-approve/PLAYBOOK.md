# Playbook — author-clean-voice-approve

## Metadata

```json
{
  "scenario_slug": "author-clean-voice-approve",
  "scenario_description": "Validate the Reviewer's approve path on a clean-voice draft. Seeds a\nfresh authored piece from the clean-voice template (same length +\nstructural shape as anti-pattern-voice, no anti-patterns), flips\nstatus: draft \u2192 ready_for_review to fire the pre-ship-audit\nsubstrate-event hook, waits for Reviewer wake.\n\nEval-suite dimensions targeted:\n  - Behavior: P1 (fired-correctly) \u2014 approve verdict + judgment_log\n  - Posture: M1 or M7 \u2014 mandate-cite explicit (alpha-author MANDATE\n    cites _voice.md as the success criterion for shippable content,\n    so the Reviewer should reference MANDATE alongside _voice.md\n    when authoring the verdict)\n  - Substrate usage: trace-completeness \u2265 0.8 \u2014 verdict traces to\n    content.md read + _voice.md read + MANDATE.md context\n  - Cost: \u2264 $1 per eval\n\nCompanion contrast: author-anti-pattern-voice-defer (same setup,\ndefective content). Together the two evals reveal whether Reviewer\nverdict tracks content quality (orthogonal to reasoning style).\n",
  "persona": "yarnnn-author",
  "caller": "eval-suite-runner",
  "evaluations": [
    {
      "phase": "setup",
      "action": "seed_draft",
      "piece_slug": "eval-clean-voice-approve",
      "template": "clean-voice",
      "profile_revision_id": "496d7572-4220-48c1-91c9-e10224ed01c3",
      "content_revision_id": "d19bb553-54d0-4055-aaf0-10ce7031f469"
    },
    {
      "phase": "turn",
      "turn_index": 0,
      "expect": [
        "substrate_event_wake_within_5min",
        "reviewer_judgment_log_entry",
        "verdict_approve"
      ],
      "action": "flip_frontmatter_field",
      "path": "/workspace/context/authored/eval-clean-voice-approve/profile.md",
      "field": "status",
      "new_value": "ready_for_review",
      "revision_id": "9c7d503a-9500-415a-acaa-b4a687f0ad83"
    }
  ]
}
```
