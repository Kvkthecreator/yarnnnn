# Playbook — trader-eod-pnl-send

## Metadata

```json
{
  "scenario_slug": "trader-eod-pnl-send",
  "scenario_description": "Validate the FULL daily-P&L compose-AND-send path under full autonomy\n(ADR-317). This is the operator's \"the Reviewer runs my daily P&L\nconfirmation alone, and I receive it without intervention\" requirement,\nend-to-end.\n\nThe architecture (ADR-317): the Reviewer does NOT send the email \u2014 the\nemail tool is deliberately excluded from REVIEWER_PRIMITIVES (verdict-\nquality regression, 2026-05-25 canary). The Reviewer's outcome-\nreconciliation JUDGMENT triggers; a post-judgment dispatcher\n(api/services/daily_pnl_email.py) fires after the wake completes, reads\nthe reconciled _money_truth.md, and sends via the system Resend wire.\nReviewer triggers; dispatcher sends.\n\nThis scenario flips operator_notifications.daily_pnl_reconciliation to\nactive: true (default-off per ADR-299), seeds reconciled _money_truth.md,\nfires outcome-reconciliation, and reads BOTH halves:\n  (a) the Reviewer's judgment closed cleanly (ReturnVerdict +\n      standing_intent), AND\n  (b) the dispatcher composed + sent the expository-pointer email\n      (deep-link CTA, deterministic P&L windows, no fabricated numbers).\n\nThe send half is observable in logs / send result, not in substrate \u2014\nthe email is operator-addressing observability, not a substrate write.\nThe read judges whether the composed P&L headline matches the seeded\n_money_truth.md windows (the dispatcher must not fabricate; bootstrap\nwindows degrade to honest copy).\n\nNOTE on RESEND: the dispatcher calls jobs.email.send_email which requires\nRESEND_API_KEY. In a dry environment the send returns\n{success: false, error: \"RESEND_API_KEY not configured\"} \u2014 the dispatcher\nstill RAN (opt-in gate passed, windows parsed, email composed); the read\nnotes whether the send wire was exercised vs. the compose path validated.\n",
  "persona": "kvk",
  "caller": "adr323-canary",
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
      "slug": "track-positions",
      "result": "dispatched"
    },
    {
      "phase": "setup",
      "action": "write_substrate",
      "path": "/workspace/governance/_preferences.yaml",
      "authored_by": "operator-proxy:scenario-runner:acting-as-kvk",
      "revision_id": "7b448f71-2773-4dc5-b1ba-df998243751b"
    },
    {
      "phase": "setup",
      "action": "write_substrate",
      "path": "/workspace/operation/trading/_money_truth.md",
      "authored_by": "operator-proxy:scenario-runner:acting-as-kvk",
      "revision_id": "db59501b-1d44-4560-8f15-d1c274facd71"
    },
    {
      "phase": "turn",
      "turn_index": 0,
      "expect": [
        "reviewer_responded",
        "reviewer_returnverdict_present",
        "daily_pnl_dispatcher_fired",
        "composed_headline_matches_money_truth"
      ],
      "action": "fire",
      "slug": "outcome-reconciliation",
      "result": "dispatched"
    }
  ]
}
```
