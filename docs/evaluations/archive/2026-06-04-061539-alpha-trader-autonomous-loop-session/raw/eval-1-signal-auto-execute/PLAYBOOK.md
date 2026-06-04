# Playbook — warm-start-auto-execute

## Metadata

```json
{
  "scenario_slug": "warm-start-auto-execute",
  "scenario_description": "Validate the full autonomous capital path on a warm kvk workspace:\nReviewer should reach an approve verdict within Sonnet round budget\nwhen substrate has accumulated mechanical-mirror state + a stub\nground-truth file (_money_truth.md) so expectancy reasoning has\ndata to land on, rather than burning rounds inferring it.\n\nReplaces \"Test A\" from the 2026-05-20 three-persona validation,\nwhere the cold-start defer (proposal stayed pending) prevented\nobservation of the auto-execute branch. By pre-warming the workspace\nwith track-account + track-universe + track-regime fires and a\nseeded _money_truth.md, the Reviewer can reach verdict in 3 rounds.\n\nWhat this validates:\n  - should_auto_apply(action_class=\"capital\") returning True under\n    autonomous + verdict=approve + ceiling not exceeded\n  - handle_execute_proposal called by review_proposal_dispatch\n  - Alpaca paper submit_order endpoint reached\n  - proposal status flips from pending \u2192 executed\n  - reviewer_identity attribution on the executed proposal\n\nWhat this does NOT validate (separate scenarios):\n  - Reviewer's meta-aware governance/principles self-amendment loop\n    (covered by cold-start-governance-self-amend)\n  - Bounded-mode substrate-write gating (covered by 2026-05-20 Test C)\n",
  "persona": "kvk",
  "caller": "claude-opus-eval-2026-06-04",
  "evaluations": [
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
      "action": "write_substrate",
      "path": "/workspace/context/trading/_money_truth.md",
      "authored_by": "operator-proxy:scenario-runner:acting-as-kvk",
      "revision_id": "1ab811e3-ce56-4ad1-84bf-1dbde3fbbb4c"
    },
    {
      "phase": "turn",
      "turn_index": 0,
      "expect": [
        "reviewer_responded",
        "no_capital_action"
      ],
      "action": "send_message",
      "content": "Reviewer, you should now see a warm workspace \u2014 track-account\nran, track-universe + track-regime fired, and _money_truth.md\nhas 30d/90d rolling expectancy. What's your read on conditions?\n",
      "response_text_preview": "Wrote to Reviewer substrate on its direction. path=/workspace/review/standing_intent.mdUniverse bars are stale (31 hours old as of 06:15 UTC Wednesday). Signal-1 entry conditions depend on live 20-day high, RSI(14), volume data that change at market open and close each day. I cannot evaluate any signal conditions without fresh bars. The recurrence schedule will fire track-universe at @market_open + 15min (13:45 UTC today), refreshing all bars and triggering signal-evaluation immediately after. I",
      "reviewer_verdict_present": false
    },
    {
      "phase": "turn",
      "turn_index": 1,
      "expect": [
        {
          "reviewer_verdict_in": [
            "approve",
            "reject"
          ]
        },
        "if_approved_then_executed",
        "if_approved_then_alpaca_order_submitted"
      ],
      "action": "emit_proposal",
      "template": "signal-2-nvda",
      "proposal_id": "b7164dac-833a-4cce-9982-b1d4943a7efd",
      "proposal_status": "pending",
      "success": true
    }
  ]
}
```
