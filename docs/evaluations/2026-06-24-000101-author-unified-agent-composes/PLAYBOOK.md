# Playbook — author-unified-agent-composes

## Metadata

```json
{
  "scenario_slug": "author-unified-agent-composes",
  "scenario_description": "RE-FOUNDING PROBE (conviction doc 2026-06-24-judgment-execution-unification \u00a75):\ndoes the author agent COMPOSE a scene IN-CYCLE when the production-posture wall\nis removed \u2014 i.e. when the wake explicitly UNIFIES judgment and production\n(\"you decide the mandate owes a scene AND you compose it now; composing IS your\naction this wake\")?\n\nWHY A NEW PROBE (what the heartbeat falsification already settled):\nThe 2026-06-23 author-heartbeat-composes probe proved that situation-forward\nframing + WriteFile-available + autonomous + declared Expected Output is NOT\nenough \u2014 the agent STILL deferred (exec 23:28:26, \"routine heartbeat\", deferred\ncompose to \"Monday\"). That falsified the task-label thesis. The grounded cause:\nthe persona-frame's PRODUCTION-POSTURE WALL \u2014 \"you are the judgment that decides\nand directs; the runtime is the hands that execute\" + \"fiduciary, not production\"\n(reviewer_agent.py _compute_minimal_frame). The occupant has WriteFile\n(registry.py:460) \u2014 the block is POSTURE, not capability. The heartbeat probe\nleft that posture intact; it could not have composed.\n\nTHE SINGLE VARIABLE (vs the falsified heartbeat probe): the recurrence prompt\ncarries an explicit POSTURE OVERRIDE that countermands the frame's judge\u2260producer\nwall and unifies the two: the agent that judges \"the mandate owes a scene\" is the\nSAME agent that composes it, in one motion, this wake. Everything else is byte-\nidentical to the heartbeat control (same workspace, funding, autonomy, empty\ncorpus, declared weekly Expected Output, same MANDATE/AUTONOMY/_autonomy/_budget/\n_expected_output substrate).\n\nThis injects the unification through the ONE surface the harness controls (the\nrecurrence prompt) so NO canon moves before the probe passes (probe-before-canon\ndiscipline \u2014 it killed 3 wrong theories this arc). If the prompt-level\nunification composes in-cycle, the persona-frame rewrite is justified (the wall\nIS the blocker). If it STILL defers even when the prompt explicitly says\n\"compose it now, composing is your action,\" then something deeper than the frame\ngates production, and we learn that cheaply before touching THESIS/FOUNDATIONS.\n\nPASS (product, not setup): a new content.md exists under\n/workspace/operation/authored/{scene-slug}/ with ACTUAL PROSE (a real screenplay\nscene, not an outline/plan/standing_intent), attributed reviewer:*, status\ndraft/ready_for_review \u2014 OR a WriteFile proposal carrying the scene prose. The\nagent COMPOSED, in-cycle, on this wake.\n\nFAIL (deferral reproduced): schedule_create, clarify, standing_intent-only close,\nan outline-instead-of-prose, or a dispatch that defers to a future fire \u2014 any\nclose with no actual scene prose authored this cycle. If the explicitly-unified\nprompt ALSO defers, the unification is incomplete (the frame is not the only\nblocker) and the re-founding ADR must localize the deeper gate before canon moves.\n",
  "persona": "netflix-script-author",
  "caller": "scenario-runner",
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
      "revision_id": "6de57d19-471b-44ad-bb51-abc84df0f148"
    },
    {
      "phase": "setup",
      "action": "write_substrate",
      "path": "/workspace/governance/_autonomy.yaml",
      "authored_by": "operator-proxy:scenario-runner:acting-as-netflix-script-author",
      "revision_id": "9da237b9-d5f1-4931-af4d-82b96e6eca65"
    },
    {
      "phase": "setup",
      "action": "write_substrate",
      "path": "/workspace/governance/AUTONOMY.md",
      "authored_by": "operator-proxy:scenario-runner:acting-as-netflix-script-author",
      "revision_id": "6c941df1-ded9-4e82-ba4a-569b7726f27b"
    },
    {
      "phase": "setup",
      "action": "write_substrate",
      "path": "/workspace/governance/_expected_output.yaml",
      "authored_by": "operator-proxy:scenario-runner:acting-as-netflix-script-author",
      "revision_id": "f8f34cb0-d2f5-4844-aca5-30e9dd10ba6e"
    },
    {
      "phase": "setup",
      "action": "write_substrate",
      "path": "/workspace/constitution/MANDATE.md",
      "authored_by": "operator-proxy:scenario-runner:acting-as-netflix-script-author",
      "revision_id": "3f3a2151-f4a7-422a-af99-8a0ca7739159"
    },
    {
      "phase": "setup",
      "action": "append_recurrence",
      "slug": "heartbeat",
      "path": "/workspace/_recurrences.yaml",
      "revision_id": "04f644e3-4a79-4066-897e-3e599771bd9e"
    },
    {
      "phase": "turn",
      "turn_index": 0,
      "expect": [
        "reviewer_responded",
        "composes_a_scene_in_cycle",
        "does_not_defer_or_outline_or_plan"
      ],
      "action": "fire_cron",
      "slug": "heartbeat",
      "result": "dispatched",
      "wake_outcome": {
        "success": true,
        "source": "cron_tick",
        "queue_id": "683eb4ec-548e-4ff8-a7bf-997394319849",
        "lane": "live",
        "message": "wake enqueued for drainer"
      }
    }
  ]
}
```
