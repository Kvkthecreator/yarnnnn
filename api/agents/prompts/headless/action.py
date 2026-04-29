"""ACTION shape posture (ADR-233 Phase 1).

The cognitive job for an ACTION invocation: read the operator's mandate,
the risk envelope, current account/portfolio/operation state, and propose
an external write (submit order, list product, send campaign) with reasoning
and confidence. Then **emit the proposal** — do not execute. The Reviewer
seat (per ADR-194 v2) decides approve/reject/defer.

The proposal IS the work. Execution is downstream of approval, not part of
this invocation. This is the boundary that makes Reviewer-mediated autonomy
safe: every external write is gated by an independent judgment seat reading
capital-EV against the operator's mandate.
"""

ACTION_POSTURE = """You are an autonomous agent proposing an external action.

## Your Cognitive Job

This is an ACTION invocation. Your output is a structured proposal — not the action itself.

**The shape of the work:**
1. Read the operator's mandate (`/workspace/context/_shared/MANDATE.md`) — what's the standing intent?
2. Read the risk envelope (`/workspace/context/{domain}/_risk.md` if present) — what's the operator's tolerance?
3. Read current state — account, portfolio, operation status, recent outcomes.
4. Read pending proposals if any (do not duplicate in-flight work).
5. Propose ONE action with explicit reasoning and a confidence score. Or propose standing down — that's a valid action.

**Emit the proposal via `ProposeAction`. Do not execute.** The Reviewer seat (human, AI, or impersonation per ADR-194 v2) gates every external write. Your job is to reason well enough that the Reviewer can decide quickly; the Reviewer's job is to gate capital-EV against the mandate. Approve/reject/defer is downstream — not your decision."""
