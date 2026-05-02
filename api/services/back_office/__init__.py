"""Back office executors — ADR-164.

Back office tasks are tasks owned by TP (role='thinking_partner'). When the
scheduler dispatches one, invocation_dispatcher routes to the executor declared
in the recurrence YAML's `executor:` field.

Two executor styles:
  1. Deterministic — a Python function that reads workspace state and writes
     a structured output. Zero LLM cost.
  2. LLM-backed — a focused prompt that scopes TP judgment to a single
     decision. Used when the rule can't be expressed deterministically.

Each executor module exports a `run(client, user_id, task_slug)` async function
that returns a dict with:
  - summary: str         — one-line human-readable summary
  - output_markdown: str — full run output written to the recurrence's natural-home path
  - actions_taken: list  — structured record of mutations (for logging)

The executor never writes the output itself — the dispatcher handles output file
writing, manifest creation, and run log appending. Executors are pure functions
from (client, user_id, task_slug) to a result dict.

Active executors (ADR-231 maintenance shape):
  - narrative_digest      — rolls up narrative events into /workspace/memory/recent.md
  - outcome_reconciliation — reconciles platform outcomes into _performance.md
  - proposal_cleanup      — archives stale action proposals
  - reviewer_calibration  — updates /workspace/review/decisions.md calibration stats
  - reviewer_reflection   — writes reflection entry to /workspace/review/IDENTITY.md
"""
