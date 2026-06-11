# Playbook — anr-scout-stage1-approve

## Metadata

```json
{
  "scenario_slug": "anr-scout-stage1-approve",
  "scenario_description": "Lifecycle-journey Stage-1 COMPLETION (operator-side act): approve the\nfive constitution/persona WriteFile proposals the seat queued in\n2026-06-11-013544-anr-scout-stage1-seat-formation, then verify via a\nread-back turn that the seat now reports the constitution as LIVE\nsubstrate (skeleton\u2192authored transition).\n\nCRITERION: (1) all five proposals execute \u2014 MANDATE/BRAND/IDENTITY/\nprinciples/standing_intent land as revisions with reviewer attribution\n+ operator approval trail (ADR-209 + ADR-307); (2) the post-approval\nread-back reflects the new substrate state (MANDATE now exists) and\ncorrectly names the remaining gap (no program activated \u2014 Stage 2).\n",
  "persona": "anr-scout",
  "caller": "scenario-runner",
  "evaluations": [
    {
      "phase": "turn",
      "turn_index": 0,
      "expect": [],
      "action": "approve_proposal",
      "proposal_id": "4315c8f1-21cb-47a3-a42b-1218f7bb83de",
      "result": {
        "success": true,
        "proposal_id": "4315c8f1-21cb-47a3-a42b-1218f7bb83de",
        "action_type": "substrate:WriteFile",
        "execution_result": {
          "success": true,
          "scope": "workspace",
          "path": "/workspace/constitution/MANDATE.md",
          "mode": "overwrite"
        },
        "reviewer_identity": "human:89f467f1-3ff9-4877-a898-ff5599ab4b08"
      }
    },
    {
      "phase": "turn",
      "turn_index": 1,
      "expect": [],
      "action": "approve_proposal",
      "proposal_id": "6e8d2ffe-ad5e-4f02-adc0-12c90899440d",
      "result": {
        "success": true,
        "proposal_id": "6e8d2ffe-ad5e-4f02-adc0-12c90899440d",
        "action_type": "substrate:WriteFile",
        "execution_result": {
          "success": true,
          "scope": "workspace",
          "path": "/workspace/operation/BRAND.md",
          "mode": "overwrite"
        },
        "reviewer_identity": "human:89f467f1-3ff9-4877-a898-ff5599ab4b08"
      }
    },
    {
      "phase": "turn",
      "turn_index": 2,
      "expect": [],
      "action": "approve_proposal",
      "proposal_id": "e5e1c22b-a1dc-40fc-9132-3dd8082bb37a",
      "result": {
        "success": true,
        "proposal_id": "e5e1c22b-a1dc-40fc-9132-3dd8082bb37a",
        "action_type": "substrate:WriteFile",
        "execution_result": {
          "success": true,
          "scope": "workspace",
          "path": "/workspace/persona/IDENTITY.md",
          "mode": "overwrite"
        },
        "reviewer_identity": "human:89f467f1-3ff9-4877-a898-ff5599ab4b08"
      }
    },
    {
      "phase": "turn",
      "turn_index": 3,
      "expect": [],
      "action": "approve_proposal",
      "proposal_id": "226e125c-61d0-4422-b158-d48a1c20f670",
      "result": {
        "success": true,
        "proposal_id": "226e125c-61d0-4422-b158-d48a1c20f670",
        "action_type": "substrate:WriteFile",
        "execution_result": {
          "success": true,
          "scope": "workspace",
          "path": "/workspace/persona/principles.md",
          "mode": "overwrite"
        },
        "reviewer_identity": "human:89f467f1-3ff9-4877-a898-ff5599ab4b08"
      }
    },
    {
      "phase": "turn",
      "turn_index": 4,
      "expect": [],
      "action": "approve_proposal",
      "proposal_id": "c2d482dc-2820-4adc-848a-e0cdc651ef67",
      "result": {
        "success": true,
        "proposal_id": "c2d482dc-2820-4adc-848a-e0cdc651ef67",
        "action_type": "substrate:WriteFile",
        "execution_result": {
          "success": true,
          "scope": "workspace",
          "path": "/workspace/persona/standing_intent.md",
          "mode": "overwrite"
        },
        "reviewer_identity": "human:89f467f1-3ff9-4877-a898-ff5599ab4b08"
      }
    },
    {
      "phase": "turn",
      "turn_index": 5,
      "expect": [
        "addressed_wake_within_1min",
        "reviewer_responded",
        "readback_reports_constitution_live",
        "readback_names_program_activation_as_next_step"
      ],
      "action": "send_message",
      "content": "I've approved everything in the queue. Quick check: is my\nconstitution live now? What's the next step to get this operation\nactually running?\n",
      "response_text_preview": "Wrote to Reviewer substrate on its direction. proposal_id=1843dd06...Constitution is live: MANDATE, BRAND, and IDENTITY are approved and active. The framework is structurally sound and ready for artist intake. Autonomy.md is not yet authored (governance-locked), so all writes currently require operator approval. I'm running under manual delegation posture until you declare otherwise. The operation is unblocked on your end: submit first artist(s) to evaluate, and I can begin research and draft-br",
      "reviewer_verdict_present": false
    }
  ]
}
```
