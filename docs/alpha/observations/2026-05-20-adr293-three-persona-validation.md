# 2026-05-20 — ADR-293 Three-Persona Validation

Validation of ADR-293 governance/operational substrate taxonomy + uniform
AUTONOMY-mode gating, post-Work 1 prompt-envelope alignment (commit
`332a950`).

## Setup

All three persona workspaces purged via `DELETE /api/account/reset` and
re-activated via `activate_persona.py` (canonical ADR-230 path — kernel
init + bundle fork + persona overrides + platform connect + scheduling-
index re-materialize). Bundle default for `_autonomy.yaml` is
`delegation: autonomous` per ADR-269 iter-4; alpha-trader-2 flipped to
`bounded` post-activation via the new `_test_flip_autonomy.py` harness
(write_revision with `authored_by="operator:test-validation"`).

## Results

| Test | Persona | Mode | Stimulus | Result |
|---|---|---|---|---|
| **C** | alpha-trader-2 | bounded | `manual_fire signal-evaluation` | Reviewer composed WriteFile to `review/standing_intent.md` → gate returned `error: substrate_write_requires_autonomous`. Revision chain: **zero `reviewer:*` rows**. ✓ |
| **B** | alpha-trader (seulkim) | autonomous | `manual_fire signal-evaluation` | Identical WriteFile path **succeeded**. Revision chain: `reviewer:ai:reviewer-sonnet-v8` row present with `authored_by` attribution per ADR-209. ✓ |
| **A** | kvk | autonomous | `emit_test_proposal kvk` (Signal 2 NVDA) | Dispatch path + Reviewer wake fired correctly. Reviewer exhausted 3-round Sonnet budget reading cold-start substrate, returned `defer` (low confidence). Proposal `status='pending'` → routes to operator Queue. **Auto-execute branch not exercised** — Reviewer never reached approve verdict. ◐ |

## What this validates

**Substrate-write surface (Tests B + C end-to-end on real Reviewer wakes):**
- Capability is universal across modes — same Reviewer reasoning, same WriteFile composed under both bounded and autonomous.
- AUTONOMY mode is the *only* gate that changes outcome; mode-shift toggles permission to land, not capability to compose.
- ADR-209 attribution lands correctly (`reviewer:ai:reviewer-sonnet-v8`) when the gate permits.
- Bounded gate returns honest structured error (`error: substrate_write_requires_autonomous`) — Reviewer continues + reasoning preserved in verdict envelope.

**Capital action dispatch (Test A partial):**
- `handle_propose_action` writes `action_proposals` row.
- `on_proposal_created` routes through `review_proposal_dispatch.py`.
- Reviewer agent invoked under autonomous mode with full governance envelope.
- Defer outcome → proposal stays `pending` → operator Queue receives it.
- This is the *safety floor working as designed* — fresh workspace with zero performance history doesn't auto-execute capital actions.

## What this does NOT validate

**The autonomous capital execute branch:** `should_auto_apply(action_class="capital")` returning True → `handle_execute_proposal` → Alpaca paper order submission. Two consecutive Test A fires both deferred from the same root cause (Reviewer round budget exhausted on cold substrate before reaching `ReturnVerdict`). The execute branch is covered by:
- Unit test gate `api/test_adr293_governance_taxonomy.py` (20/20).
- `should_auto_apply` deterministic logic.
- Prior production runs of approved proposals on warmer workspaces.

**Governance file gate behavior under live Reviewer wake:** the Reviewer in Tests B and C never attempted to write AUTONOMY.md / `_autonomy.yaml` / `_token_budget.yaml`. Governance gate is unit-tested but not exercised in live persona behavior here.

## Findings worth recording

**Cold-start defer is structural, not a bug:** The 3-round Sonnet budget for capital review is intentional (cost control per ADR-260), but it means a fresh workspace's first proposal will likely defer — the Reviewer needs substrate reads to reason and burns the budget before reaching verdict. **Operator implication**: fresh workspaces should expect their first 1–3 proposals to go to Queue rather than auto-execute. After a few wakes the substrate warms (positions tracked, ground-truth substrate accumulates) and the Reviewer reaches verdict in fewer rounds.

**Reviewer behavior parity across modes confirms ADR-293 D5 (single decision surface):** Tests B and C fired the same recurrence on near-identical substrate. The Reviewer composed identical actions; only the gate at write-time differed. This is the Claude Code analog landing structurally — capability universal, gating per-mode.

## Open questions surfaced

1. **Bounded UX**: when the gate returns `substrate_write_requires_autonomous`, where does the operator see the deferred write? Today the reasoning is in the verdict envelope only — Phase 4 Substrate-Queue (deferred per ADR-293 D10) would surface this as a click-to-approve affordance in the cockpit. Until Phase 4 ships, bounded operators read the verdict envelope to see what would have been written.

2. **Test A execute-branch validation**: separately worth exercising once a workspace has 1–2 wakes of accumulated substrate, or with a higher round budget for cold-start. Not blocking ADR-293 validation; orthogonal future test.

3. **The full recursive loop** — Reviewer submits a capital action AND meta-aware updates governance/principles substrate to accommodate the learning — is the harder downstream behavioral target. Tests B + C validate the substrate-write *mechanism*; what's not yet validated is *whether* the Reviewer chooses to use that mechanism in response to capital outcomes. That's behavioral observation over multi-wake tenure, not a structural test.

## Files

- `api/scripts/alpha_ops/_test_flip_autonomy.py` — one-shot harness, sync `write_revision` wrapper for `_autonomy.yaml` mode flipping. Lives alongside other alpha-ops scripts; underscore prefix marks it as test scaffolding (not part of the activation pipeline).
- Validation logs (ephemeral, not committed): `/tmp/testC_fire.log`, `/tmp/testB_fire.log`, `/tmp/testA_proposal.log`, `/tmp/testA_proposal2.log`.

## Commits in scope

- `332a950` fix(adr-293 work-1) — cockpit_awareness prompt envelope alignment (deployed live; validated by this observation)
- This observation document
- New helper script `_test_flip_autonomy.py`
