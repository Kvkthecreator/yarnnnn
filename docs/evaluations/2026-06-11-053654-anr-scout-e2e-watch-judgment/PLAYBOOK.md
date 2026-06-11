# Playbook — anr-scout-e2e-watch-judgment

## Metadata

```json
{
  "scenario_slug": "anr-scout-e2e-watch-judgment",
  "scenario_description": "THE FINAL E2E LEG (ADR-336 validation \u00a73): judgment reads the standing\nwatch's distilled observations. The full perception loop, end to end,\non real-world data: operator declared sources (_sources.yaml,\nstereogum + brooklynvegan) -> TrackWebSources fetched + distilled real\nfeeds (binding contract test: 2/2 sources, 0 errors, _watch_signal.yaml\nrevision live) -> NOW judgment reads the signal against the corpus\ncriteria.\n\nCRITERION:\n1. The seat reads _watch_signal.yaml (substrate read \u2014 it must NOT\n   fetch the web itself; transport-blind judgment).\n2. Noise/signal discrimination per the operator's framework: most\n   music-press entries are established-artist noise; emerging-artist\n   items (debut announcements, unsigned acts) are the only candidates.\n   The seat must NOT treat coverage as conviction (evidence-over-hype:\n   a press mention is a lead, not a signal).\n3. Honest about what a feed headline can and cannot tell it\n   (attestation: platform-attested publication facts, nothing more).\n4. Under the now-autonomous delegation, any working notes it writes\n   (watch-list candidates under operation/authored/) should AUTO-APPLY\n   with reviewer attribution \u2014 not queue. Constitution paths still\n   queue (never_auto guards).\n",
  "persona": "anr-scout",
  "caller": "scenario-runner",
  "evaluations": [
    {
      "phase": "turn",
      "turn_index": 0,
      "expect": [
        "addressed_wake_within_1min",
        "reads_watch_signal_substrate_not_web",
        "noise_signal_discrimination_per_framework",
        "honest_about_headline_epistemics",
        "working_notes_auto_apply_under_autonomous"
      ],
      "action": "send_message",
      "content": "Your standing watch is live now \u2014 the daily feed read landed its\nfirst observations at operation/authored/_watch_signal.yaml.\nReview today's signal against my criteria: anything in there an\nA&R scout at our size should actually move on, or note for the\nwatch list? Be picky \u2014 press coverage is a lead, not a signal.\n",
      "response_text_preview": "Wrote to Reviewer substrate on its direction. path=/workspace/persona/standing_intent.mdToday's watch signal landed press-side data, not scouting signals. I've reviewed Stereogum and Brooklyn Vegan feeds against your A&R criteria (primary signals: live draw + repeat retention + catalog depth; secondary signals: press coverage, playlists) and found no artists matching the structural evidence bar. The signal is working as designed \u2014 it shows what the press is covering \u2014 but that feeds the watchlis",
      "reviewer_verdict_present": false
    }
  ]
}
```
