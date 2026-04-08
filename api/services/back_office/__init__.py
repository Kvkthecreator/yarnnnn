"""Back office executors — ADR-164.

Back office tasks are tasks owned by TP (role='thinking_partner'). When the
scheduler dispatches one, task_pipeline._execute_tp_task() reads the TASK.md
## Process section to find a declared executor and invokes it.

Two executor styles:
  1. Deterministic — a Python function that reads workspace state and writes
     a structured output. Zero LLM cost. Example: agent_hygiene, workspace_cleanup.
  2. LLM-backed — a focused prompt that scopes TP judgment to a single
     decision. Used when the rule can't be expressed deterministically.

Each executor module exports a `run(client, user_id, task_slug)` async function
that returns a dict with:
  - summary: str         — one-line human-readable summary
  - output_markdown: str — full run output written to /tasks/{slug}/outputs/{date}/output.md
  - actions_taken: list  — structured record of mutations (for logging)

The executor never writes the output itself — the pipeline handles output file
writing, manifest creation, and run log appending. Executors are pure functions
from (client, user_id, task_slug) to a result dict.
"""
