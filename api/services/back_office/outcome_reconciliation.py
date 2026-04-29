"""Back Office: Outcome Reconciliation — ADR-195 v2.

Runs every registered OutcomeProvider and folds new outcomes into each
domain's `/workspace/context/{domain}/_performance.md`. Daily back-office
task owned by YARNNN (per ADR-164 pattern).

Thin executor — all the interesting logic lives in
`services.outcomes.reconciler.reconcile_user`. This module just delivers
the standard back-office shape (`summary` + `output_markdown` +
`actions_taken`) over it. See `services.invocation_dispatcher` line 646
for the contract.

Zero LLM cost. Platform API calls only on the providers' side. Filesystem
writes are the persistence path (per FOUNDATIONS v6.0 Axiom 1 — Substrate).
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
          "summary": str,                  # one-line summary
          "output_markdown": str,          # full per-provider markdown report
          "actions_taken": list[dict],     # one entry per provider that
                                            # appended outcomes (action="fold_outcomes")
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
            "total_appended": 0,
            "error": str(exc),
        }

    finished_at = datetime.now(timezone.utc)
    duration_s = (finished_at - started_at).total_seconds()

    # Markdown report
    total_appended = summary.get("total_appended", 0)
    summary_written = summary.get("cross_domain_summary_written", False)
    report_lines = [
        f"# Outcome Reconciliation — {started_at.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        f"Appended **{total_appended}** new outcome(s) across all providers.",
        f"Outcomes landed in `/workspace/context/{{domain}}/_performance.md` "
        f"per each provider's domain (see per-provider results below).",
        (
            f"Cross-domain summary at `/workspace/context/_performance_summary.md`: "
            f"{'regenerated' if summary_written else '**FAILED TO WRITE** (see logs)'}."
        ),
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
            appended = result.get("appended", 0)
            dup = result.get("skipped_duplicate", 0)
            invalid = result.get("skipped_invalid", 0)
            candidates = result.get("candidates", 0)
            error = result.get("error")
            since = result.get("since", "<bootstrap>")
            status_marker = "ERROR" if error else "OK"
            report_lines.append(
                f"- **{provider_name}** ({status_marker}): "
                f"candidates={candidates}, appended={appended}, "
                f"duplicate={dup}, invalid={invalid}, since={since}"
            )
            if error:
                report_lines.append(f"  - error: {error}")
        report_lines.append("")
    else:
        report_lines.append("_No providers registered or all disconnected._")
        report_lines.append("")

    logger.info(
        "[OUTCOME_RECONCILIATION] user=%s appended=%d duration=%.2fs",
        user_id[:8],
        total_appended,
        duration_s,
    )

    # Build one actions_taken entry per provider that actually appended
    # outcomes — keeps the audit log focused on real mutations rather
    # than no-op runs.
    actions_taken: list[dict] = []
    for provider_name, result in providers.items():
        appended = result.get("appended", 0)
        if appended <= 0:
            continue
        actions_taken.append({
            "action": "fold_outcomes",
            "provider": provider_name,
            "appended": appended,
            "skipped_duplicate": result.get("skipped_duplicate", 0),
            "skipped_invalid": result.get("skipped_invalid", 0),
        })
    if summary_written:
        actions_taken.append({
            "action": "write_cross_domain_summary",
            "path": "/workspace/context/_performance_summary.md",
        })

    if top_error:
        executor_summary = f"Reconcile crashed: {top_error}"
    elif total_appended:
        executor_summary = (
            f"Appended {total_appended} outcome(s) across "
            f"{len([p for p, r in providers.items() if r.get('appended', 0) > 0])} provider(s)"
        )
    else:
        executor_summary = "No new outcomes to reconcile"

    return {
        "summary": executor_summary,
        "output_markdown": "\n".join(report_lines),
        "actions_taken": actions_taken,
    }
