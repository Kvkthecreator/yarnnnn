# Findings — first attempt (balance-gated, superseded)

This run produced no wake: the feed route's balance gate fired
(`balance_exhausted`, effective balance −$0.28 via `get_effective_balance`
RPC — stored `workspaces.balance_usd` was $33; the divergence is spend
since last refill, by design). The runner reported `turns_executed: 1`
with an empty response instead of surfacing the gate — harness gap noted
in the superseding run's findings (observation 2).

The only revision in the window (`system:conversation-summary`) is the
session-close summarizer, not Reviewer activity.

Superseded by `2026-06-12-004813-yarnnn-author-housekeeping-genesis/`
(run after a +$25 admin_grant refill). Retained as the receipt for the
balance-gate behavior + the harness gap.
