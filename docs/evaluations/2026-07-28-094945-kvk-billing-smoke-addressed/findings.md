# Findings — kvk-billing-smoke-addressed (2026-07-28)

**Criterion (declared before the read)**: ADR-490 §2 — the pool is debited at
`cost_usd × USAGE_BILLING_MULTIPLIER (1.30)`, stamped as `billed_usd` at the
single telemetry write site, with `cost_usd` staying actual provider cost; and
ADR-445 §9 (closed) — the addressed entry runs the one draw gate before model
work. Operationalization: fire one benign addressed turn as the operator on the
live workspace and read the ledger row + balance delta it produces. The read is
mechanical (receipts), not judgment-axis.

**Verdict: PASS — the ADR-490 margin is live end to end.**

## Receipts

1. **The margin row** (the first post-deploy costed call — every earlier row is
   pre-deploy backfill parity, billed == cost):
   `execution_events` @ 2026-07-28T09:49:59Z — slug `addressed`, judgment,
   success, principal-attributed.
   `cost_usd = 0.113762` (provider truth) · `billed_usd = 0.147891` ·
   **ratio = 1.3000 exactly**.
2. **The pool drew the BILLED amount**: effective balance
   37.0904 → 36.9425 = −0.147891 (not −0.113762) — the migration-224
   `get_effective_balance` COALESCE debits billed, so the margin is realized,
   not merely recorded.
3. **The draw gate ran ahead of the call** (the ADR-445 §9 closure path in
   `routes/feed.py::response_stream` — balance > 0, owner never capped →
   allowed; the turn streamed normally).
4. **Incidental reply quality**: Freddie answered the status ask correctly and
   concisely (the operator's recent Studio edits + the 07-27 radar brief;
   nothing pending). `no_substrate_writes` held — substrate-diff shows zero
   new revisions.

## What this closes

The last open item of the 2026-07-28 verification pass: marketing copy ✓, LS
per-seat Starter variant ✓ (operator screenshot: $20.00/unit/month), Supabase
allowance streamline ✓ (receipted same day, effective preserved at $37.0904),
and now the organic ×1.30 margin ✓. The ADR-490/491 + ADR-445 §9 billing arc
has no unverified claims outstanding.
