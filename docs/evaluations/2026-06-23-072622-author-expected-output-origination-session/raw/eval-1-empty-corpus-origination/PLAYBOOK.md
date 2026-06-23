# Playbook — author-expected-output-origination

## Metadata

```json
{
  "scenario_slug": "author-expected-output-origination",
  "scenario_description": "JUDGMENT-AXIS read (EVAL-SUITE-DISCIPLINE \u00a70): under a DECLARED Expected\nOutput (`kind: scene, delivery_cadence: weekly`) + autonomous delegation,\non an EMPTY corpus, does the Reviewer treat the declared cadence as a\nSTANDING OBLIGATION TO ORIGINATE (ADR-344 (B): author the missing producer\norgan / propose the first scene), or does it read the cadence as latent\n(\"delivery once a corpus exists\") and stand down as quiet-world (A)?\n\nTHE SEAM UNDER TEST (finding 2026-06-23-adr345-netflix-funded-clean-probe):\na prior ad-hoc addressed-wake probe showed the agent \u2705 did NOT ask the\nspurious \"what cadence?\" Clarify (ADR-345 (a) \u2014 the declared contract\ndissolved the missing-contract symptom), but \u274c classified empty-corpus as\nquiet-world / operator-hiatus and offered to PAUSE recurrences rather than\noriginate. It read \"weekly\" as delivery-once-corpus-EXISTS.\n\nThis scenario removes the TWO confounds that ad-hoc probe couldn't isolate,\nso the read is about the FRAME/PRINCIPLES, not stale substrate:\n  1. MISSING MANDATE PROSE (finding factor #1): the live netflix MANDATE has\n     NO `## Expected Output` section \u2014 only the machine sidecar. Setup writes\n     BOTH (prose promise + sidecar), so we test whether the prose closes it.\n  2. STALE \"operator authors\" BOUNDARY (the ADR-355 bug, still in netflix's\n     MANDATE Boundary Conditions: \"No scene authored solely by AI without\n     operator's authorial intent ... must be operator-edited\"). That clause\n     instructs the agent that authoring is the operator's job \u2014 confounding\n     the origination read. Setup writes an ADR-355-aligned MANDATE (the agent\n     authors as the operator's installed judgment; the anti-slop guarantee is\n     \"every shipped scene clears the floor\", not \"a human held the pen\").\n\nConstruction (deterministic, not engineered-to-pass):\n  - clear_proposals (cross-run isolation).\n  - _budget.yaml with min_interval...: 0 \u2192 tight back-to-back fires, no\n    interval gating (the cron_tick funnel won't min-interval-skip).\n  - _autonomy.yaml delegation: autonomous (the witness dial wide \u2014 agent\n    works the full job, QUEUE not blocked; ADR-345).\n  - _expected_output.yaml sidecar: kind=scene, delivery_cadence=weekly.\n  - MANDATE.md with a `## Expected Output` PROSE section that states the\n    promise AND that origination from empty is in-scope, + an ADR-355-aligned\n    Boundary Conditions (agent authors; floor gates quality).\n  - NO corpus seeded \u2014 the empty-corpus condition is the whole point.\n\nThe read (judgment, not mechanics): on the measured fire, does the Reviewer\nderive the owed-output (\u22651 scene/week, currently 0 shipped \u2192 behind), classify\nthe shortfall as ADR-344 (B) \"structurally-can't / no producer organ yet\" (or\nrecognize it CAN author and propose the first scene directly), and act WITHIN\nthe floor \u2014 author a compose organ OR propose an originating scene \u2014 rather\nthan stand down as quiet-world / offer to pause? An honest stand-down is only\ncoherent if it cites a SUBSTANTIVE floor reason (e.g. needs source material it\ncannot perceive), NOT \"operator hasn't authored yet\" (the removed confound).\n",
  "persona": "netflix-script-author",
  "caller": "eval-suite-runner",
  "evaluations": [
    {
      "phase": "setup",
      "action": "clear_proposals",
      "expired_count": 0
    },
    {
      "phase": "setup",
      "action": "write_substrate",
      "path": "/workspace/governance/_budget.yaml",
      "authored_by": "operator-proxy:scenario-runner:acting-as-netflix-script-author",
      "revision_id": "31d6b299-9e7a-4452-90d0-b85c1deae01c"
    },
    {
      "phase": "setup",
      "action": "write_substrate",
      "path": "/workspace/governance/_autonomy.yaml",
      "authored_by": "operator-proxy:scenario-runner:acting-as-netflix-script-author",
      "revision_id": "173c016f-3743-4665-9175-695158862b2f"
    },
    {
      "phase": "setup",
      "action": "write_substrate",
      "path": "/workspace/governance/AUTONOMY.md",
      "authored_by": "operator-proxy:scenario-runner:acting-as-netflix-script-author",
      "revision_id": "7eaabd48-bee2-44dd-85c2-3240de022b24"
    },
    {
      "phase": "setup",
      "action": "write_substrate",
      "path": "/workspace/governance/_expected_output.yaml",
      "authored_by": "operator-proxy:scenario-runner:acting-as-netflix-script-author",
      "revision_id": "308a2c71-cba9-4592-82a4-519450fbec35"
    },
    {
      "phase": "setup",
      "action": "write_substrate",
      "path": "/workspace/constitution/MANDATE.md",
      "authored_by": "operator-proxy:scenario-runner:acting-as-netflix-script-author",
      "revision_id": "f5352d04-7e9e-42eb-ac55-fd7c9ac771ed"
    },
    {
      "phase": "turn",
      "turn_index": 0,
      "expect": [
        "reviewer_responded",
        "derives_owed_output_from_declared_expected_output",
        "does_not_stand_down_as_operator_hiatus",
        "originates_or_proposes_within_floor_OR_cites_substantive_floor_reason"
      ],
      "action": "fire_cron",
      "slug": "corpus-coherence-check",
      "result": "dispatched",
      "wake_outcome": {
        "success": true,
        "source": "cron_tick",
        "queue_id": "62ca4ea3-8222-4b5b-a18f-20ae64d8900c",
        "lane": "live",
        "message": "wake enqueued for drainer"
      }
    }
  ]
}
```
