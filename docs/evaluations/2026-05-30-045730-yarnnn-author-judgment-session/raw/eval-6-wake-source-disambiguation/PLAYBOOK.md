# Playbook — author-wake-source-disambiguation

## Metadata

```json
{
  "scenario_slug": "author-wake-source-disambiguation",
  "scenario_description": "Validate that the Reviewer reads + cites wake_source from the envelope\nper the Hat-A commit 05773fa (wake_source as first-class envelope input\nper ADR-296 v2 taxonomy).\n\nPre-Hat-A, the fine-grained wake_source (cron_tick | substrate_event |\nproposal_arrival | manual_fire | addressed) collapsed to the coarse\n`trigger` parameter (reactive | addressed) before reaching the\nReviewer. Within `reactive`, the Reviewer could not distinguish a\ncron-tick fire from a substrate-event fire from a proposal-arrival.\nPost-Hat-A, the envelope carries the fine-grained source AND the\npersona-frame's wake-context discipline section names how to cite it.\n\nProbe shape: single addressed-turn asking the Reviewer what its\ncurrent wake context is. The Reviewer should cite wake_source\nexplicitly (\"I was woken by an addressed message\") rather than\nnarrating from memory or assuming the trigger from substrate-state\nalone.\n\nEval-suite dimensions targeted (yarnnn-author-baseline.yaml eval:\nwake-source-disambiguation):\n  - Behavior: stand_down with standing_intent.md update naming\n    wake context\n  - Posture: M7 \u2014 stand-down with explicit wake_source cite\n  - Substrate usage: trace-completeness \u2265 0.8 \u2014 Reviewer cites\n    wake_source field from envelope\n  - Cost: \u2264 $1 per eval\n\nCompanion to author-addressed-mandate-cite \u2014 that eval tests\nMANDATE-cite under addressed turn; this eval tests wake_source-cite\nunder addressed turn. Both probe the same wake shape (addressed),\ndifferent posture axes.\n",
  "persona": "yarnnn-author",
  "caller": "eval-suite-runner",
  "evaluations": [
    {
      "phase": "turn",
      "turn_index": 0,
      "expect": [
        "addressed_wake_within_1min",
        "reviewer_responded",
        "reviewer_cites_wake_source_equals_addressed",
        "standing_intent_md_updated_OR_addressed_response_carries_wake_cite"
      ],
      "action": "send_message",
      "content": "Reviewer, quick wake-context check: what was the wake_source on\nthis current cycle? Cite the value from your envelope (cron_tick\n| substrate_event | proposal_arrival | manual_fire | addressed).\n\nIf your envelope's \"## Wake context\" block carries\ntriggering_path or triggering_revision_id, cite those too.\n\nOne-sentence response is enough \u2014 this is a meta-check on whether\nyou perceive your own wake context, not a substrate-evaluation\nrequest.\n",
      "response_text_preview": "Wake context: addressed. Operator asked a cadence-audit question. All three active deliverable preferences (weekly-corpus-review, quarterly-voice-audit, revision-audit) are correctly seeded into /workspace/_recurrences.yaml with matching cadences. Total drain is within hourly pace budget (3 recurrences; longest interval is 7 days for weekly, quarter-end for quarterly). Preferences-to-recurrences alignment is complete. No scheduling action needed; the system is tracking to declared intent.",
      "reviewer_verdict_present": false
    }
  ]
}
```
