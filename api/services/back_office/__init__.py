"""Back office executors + lifecycle helpers — ADR-164 + ADR-206.

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

`materialize_back_office_task` (below) is the lifecycle helper: called by trigger
sites (platform connect, first proposal) to materialize a back-office recurrence at
the moment it becomes meaningful. Relocated from workspace_init.py 2026-05-03 —
it belongs here because it is back-office lifecycle, not workspace initialization.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def materialize_back_office_task(
    client: Any,
    user_id: str,
    type_key: str,
    slug: str,
    title: str,
    user_timezone: str | None = None,
) -> None:
    """Materialize a back-office task on trigger (ADR-206).

    ADR-206: back-office tasks are not scaffolded at signup. This helper is
    called by trigger-site hooks (first proposal created, platform connected)
    to materialize the task at the moment it becomes meaningful.
    Idempotent — no-op if the task already exists for this user.
    """
    from services.schedule_utils import get_user_timezone as _get_user_timezone
    from services.primitives.manage_recurrence import handle_manage_recurrence

    if user_timezone is None:
        user_timezone = _get_user_timezone(client, user_id)

    # Idempotency: check the scheduling index for an existing row
    existing = (
        client.table("tasks")
        .select("id")
        .eq("user_id", user_id)
        .eq("slug", slug)
        .execute()
    )
    if existing.data:
        return

    # Derive executor dotted-path from slug convention
    # (back-office-foo-bar → services.back_office.foo_bar)
    if slug.startswith("back-office-"):
        executor_tail = slug[len("back-office-"):].replace("-", "_")
        executor = f"services.back_office.{executor_tail}"
    else:
        executor = type_key

    class _Auth:
        def __init__(self, c, u):
            self.client = c
            self.user_id = u
    _auth = _Auth(client, user_id)
    result = await handle_manage_recurrence(_auth, {
        "action": "create",
        "shape": "maintenance",
        "slug": slug,
        "body": {
            "executor": executor,
            "schedule": "daily",
            "title": title,
        },
    })
    if not result.get("success"):
        raise RuntimeError(
            f"Failed to materialize back-office recurrence: {slug} ({result.get('message')})"
        )

    logger.info(f"[MATERIALIZE] Back-office recurrence created on trigger: {slug} for {user_id[:8]}")
