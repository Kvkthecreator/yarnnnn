# Playbook — kvk-billing-smoke-addressed

## Metadata

```json
{
  "scenario_slug": "kvk-billing-smoke-addressed",
  "scenario_description": "Hat-B smoke on the LIVE kvk workspace (operator-requested, 2026-07-28,\nthe ADR-490/491 verification pass): ONE benign addressed turn to\n(1) exercise the new billing path end to end on prod \u2014 the check_draw\ngate (pool hard-stop + member cap, ADR-445 \u00a79 closure) ahead of a real\ncosted judgment call \u2014 and (2) land the first post-deploy ledger row,\nwhose billed_usd must read cost_usd \u00d7 1.30 (the ADR-490 margin receipt;\nevery earlier row is pre-deploy backfill parity, billed == cost).\n\nDELIBERATELY ZERO SETUP: this is the operator's live personal workspace\n(d5b9029b, starter, freshly streamlined to allowance=0 / balance=37.09).\nNo resets, no seeded substrate, no proposals \u2014 a read-shaped status ask\nonly. The read is mechanical (ledger receipts), not a judgment-axis eval.\n",
  "persona": "kvk",
  "caller": "claude-fable-5-billing-smoke",
  "evaluations": [
    {
      "phase": "turn",
      "turn_index": 0,
      "expect": [
        "reviewer_responded",
        "no_substrate_writes"
      ],
      "action": "send_message",
      "content": "Quick status check: in one or two sentences, what changed most recently in this workspace, and is anything waiting on me?",
      "response_text_preview": "The most recent workspace changes are the operator's own Studio edits to operation/hello/document.html, and the AI frontier radar's brief on Claude Opus 5's release (2026-07-27). All connections are active, no proposals are pending, and there's nothing in the substrate waiting on operator action.",
      "reviewer_verdict_present": false
    }
  ]
}
```
