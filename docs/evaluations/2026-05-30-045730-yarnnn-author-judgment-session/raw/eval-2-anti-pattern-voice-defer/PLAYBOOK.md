# Playbook — author-anti-pattern-voice-defer

## Metadata

```json
{
  "scenario_slug": "author-anti-pattern-voice-defer",
  "scenario_description": "Validate the Reviewer's defer-with-directive path on a defective draft.\nSeeds a fresh authored piece from the anti-pattern-voice template\n(list-of-three openers, \"at the end of the day\", \"absolutely pivotal\",\nintensifier adverbs, \"in conclusion\" closer), flips status: draft \u2192\nready_for_review to fire the pre-ship-audit substrate-event hook,\nwaits for Reviewer wake.\n\nThis is the negative-case companion to author-clean-voice-approve.\nSame setup shape, defective content; verdict should flip from\napprove to defer (or reject) with a directive in standing_intent.md\nciting the specific anti-patterns.\n\nEval-suite dimensions targeted:\n  - Behavior: P1 (fired-correctly) \u2014 defer/reject verdict + judgment_log\n    + directive in standing_intent.md\n  - Posture: M1 \u2014 directive grounds in MANDATE voice clause (the\n    voice anti-patterns being flagged should trace to MANDATE's\n    declared voice criterion, not just _voice.md)\n  - Substrate usage: trace-completeness \u2265 0.8 \u2014 verdict traces to\n    content.md read + _voice.md read + MANDATE.md voice clause\n  - Cost: \u2264 $1 per eval\n\nExtracted from canary_phase4_v3/v4/v5 imperative pattern (same\ncontent, same probe shape). Migrated to YAML scenario form per the\nevaluation-infrastructure consolidation 2026-05-27.\n",
  "persona": "yarnnn-author",
  "caller": "eval-suite-runner",
  "evaluations": [
    {
      "phase": "setup",
      "action": "seed_draft",
      "piece_slug": "eval-anti-pattern-voice-defer",
      "template": "anti-pattern-voice",
      "profile_revision_id": "6d2c96be-1a02-4bb1-9617-345c56409d00",
      "content_revision_id": "501920e5-b752-424a-b6ae-2c1a387b932a"
    },
    {
      "phase": "turn",
      "turn_index": 0,
      "expect": [
        "substrate_event_wake_within_5min",
        "reviewer_judgment_log_entry",
        "verdict_defer_or_reject",
        "standing_intent_cites_voice_anti_patterns"
      ],
      "action": "flip_frontmatter_field",
      "path": "/workspace/context/authored/eval-anti-pattern-voice-defer/profile.md",
      "field": "status",
      "new_value": "ready_for_review",
      "revision_id": "0215fc14-bd58-4cc9-a2ea-e36e7309497f"
    }
  ]
}
```
