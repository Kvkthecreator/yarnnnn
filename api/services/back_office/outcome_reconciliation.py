"""Back Office: Outcome Reconciliation — ADR-195 Phase 2.

Runs every registered OutcomeProvider for the user and appends new rows
into `action_outcomes`. Daily back-office task owned by YARNNN (per
ADR-164 pattern).

Thin executor — all the interesting logic lives in
`services.outcomes.reconciler.reconcile_user`. This module just delivers
the standard back-office shape (`content` + `structured`) over it.

Zero LLM cost. Platform API calls only on the providers' side.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from services.outcomes.reconciler import reconcile_user

logger = logging.getLogger(__name__)


async def run(client: Any, user_id: str, task_slug: str) -> dict:
    """Run outcome reconciliation across all providers for `user_id`.

    Returns the standard back-office executor shape:
      {
          "content": "<markdown report>",
          "structured": {"total_inserted": int, "providers": {...}},
      }
    """
    started_at = datetime.now(timezone.utc)

    try:
        summary = await reconcile_user(client, user_id)
    except Exception as exc:  # noqa: BLE001 — preserve report even on total failure
        logger.error(
            "[OUTCOME_RECONCILIATION] user=%s reconcile_user crashed: %s",
            user_id[:8],
            exc,
            exc_info=True,
        )
        summary = {
            "user_id": user_id,
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "providers": {},
            "total_inserted": 0,
            "error": str(exc),
        }

    finished_at = datetime.now(timezone.utc)
    duration_s = (finished_at - started_at).total_seconds()

    # Markdown report
    total_inserted = summary.get("total_inserted", 0)
    report_lines = [
        f"# Outcome Reconciliation — {started_at.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        f"Inserted **{total_inserted}** new outcome(s) across all providers.",
        f"Run duration: {duration_s:.2f}s",
        "",
    ]

    top_error = summary.get("error")
    if top_error:
        report_lines.append(f"**Dispatcher error:** {top_error}")
        report_lines.append("")

    providers = summary.get("providers", {})
    if providers:
        report_lines.append("## Per-provider results")
        report_lines.append("")
        for provider_name, result in providers.items():
            inserted = result.get("inserted", 0)
            dup = result.get("skipped_duplicate", 0)
            invalid = result.get("skipped_invalid", 0)
            candidates = result.get("candidates", 0)
            error = result.get("error")
            since = result.get("since", "<bootstrap>")
            status_marker = "ERROR" if error else "OK"
            report_lines.append(
                f"- **{provider_name}** ({status_marker}): "
                f"candidates={candidates}, inserted={inserted}, "
                f"duplicate={dup}, invalid={invalid}, since={since}"
            )
            if error:
                report_lines.append(f"  - error: {error}")
        report_lines.append("")
    else:
        report_lines.append("_No providers registered or all disconnected._")
        report_lines.append("")

    logger.info(
        "[OUTCOME_RECONCILIATION] user=%s inserted=%d duration=%.2fs",
        user_id[:8],
        total_inserted,
        duration_s,
    )

    return {
        "content": "\n".join(report_lines),
        "structured": {
            "total_inserted": total_inserted,
            "duration_seconds": duration_s,
            "providers": providers,
        },
    }
