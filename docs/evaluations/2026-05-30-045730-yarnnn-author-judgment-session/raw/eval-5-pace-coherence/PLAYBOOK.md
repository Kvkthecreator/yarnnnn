# Playbook — author-pace-coherence

## Metadata

```json
{
  "scenario_slug": "author-pace-coherence",
  "scenario_description": "Validate that the Reviewer reads _preferences.yaml + _pace.yaml +\n_recurrences.yaml from the envelope and reports cadence coherence\nper ADR-275 D5 + Derived Principle 18.\n\nThe Reviewer is supposed to author Schedule() calls that match\noperator-declared deliverable preferences within declared pace\nbudget. This eval probes whether the Reviewer maintains that\ncoherence \u2014 reads the three substrate files, cross-references them,\nand reports alignment (or proposes Schedule() calls to close gaps).\n\nProbe shape: single addressed-turn asking the Reviewer to audit\nits current schedule against operator preferences + pace budget.\nReviewer's response should explicitly cite _preferences.yaml +\n_pace.yaml + _recurrences.yaml as the substrate read.\n\nEval-suite dimensions targeted (yarnnn-author-baseline.yaml\neval: pace-coherence):\n  - Behavior: stand_down with standing_intent.md update reporting\n    cadence audit result\n  - Posture: M7 \u2014 stand-down with explicit substrate cite (preferences/\n    pace/recurrences); if cite absent, falls to M5/M6\n  - Substrate usage: trace-completeness \u2265 0.8 \u2014 Reviewer cites which\n    substrate files it read\n  - Cost: \u2264 $1 per eval\n",
  "persona": "yarnnn-author",
  "caller": "eval-suite-runner",
  "evaluations": [
    {
      "phase": "turn",
      "turn_index": 0,
      "expect": [
        "addressed_wake_within_1min",
        "reviewer_responded",
        "standing_intent_md_updated",
        "standing_intent_cites_preferences_yaml_AND_recurrences_yaml",
        "standing_intent_cites_pace_yaml_OR_explains_why_pace_not_relevant"
      ],
      "action": "send_message",
      "content": "Reviewer, quick cadence audit: is your current scheduled-recurrence\nset (per /workspace/_recurrences.yaml) aligned with operator\ncadence preferences (per /workspace/context/_shared/_preferences.yaml)\nwithin the operator-declared pace budget (per /workspace/context/\n_shared/_pace.yaml)?\n\nReport:\n1. Are all preference deliverables (active: true) actually scheduled?\n2. Are any scheduled recurrences NOT backed by an operator preference?\n3. Total declared cadence within pace budget?\n\nCite the substrate files you read. If a gap exists, propose the\nSchedule() call that would close it (don't author the call \u2014\njust propose in standing_intent.md).\n",
      "response_text_preview": "I audited the recurrence set against operator cadence preferences and pace budget. All three checks pass: every active preference has a scheduled recurrence with matching cadence, all extra recurrences (bundle maintenance) are architecturally correct per ADR-275, and total declared cadence (47.3 fires/month) is well within the hourly pace budget (720/month capacity). The system is aligned. No Schedule() actions needed. The new `revision-audit` preference (added 2026-05-27) is already scheduled, ",
      "reviewer_verdict_present": false
    }
  ]
}
```
