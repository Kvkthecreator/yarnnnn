"""Compute-resource governance (ADR-293 D7).

Per-workspace `_token_budget.yaml` declares the operator's ceiling on
Reviewer compute spend. The scheduler reads this before firing each
judgment-mode recurrence; tripping a ceiling skips the fire.

The governance file is operator-only-authored (in `DEFAULT_REVIEWER_WRITE_LOCKS`)
— the Reviewer cannot escalate its own resource ceiling.

Schema:

    daily_spend_ceiling_usd: 5.00
    max_judgment_recurrences_per_day: 50
    min_interval_between_recurrence_fires_seconds: 60
    # optional per-recurrence overrides:
    # overrides:
    #   <slug>:
    #     min_interval_seconds: 900

Kernel defaults (env-derived, ADR-250 legacy) apply when the file is
absent or malformed. Per-workspace governance always wins.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


# Kernel defaults (ADR-250 legacy continues as the seeded default value)
_KERNEL_DEFAULT_DAILY_SPEND_USD: float = float(
    os.getenv("DAILY_SPEND_CEILING_USD", "10.0")
)
_KERNEL_DEFAULT_MAX_JUDGMENT_PER_DAY: int = int(
    os.getenv("MAX_JUDGMENT_RECURRENCES_PER_DAY", "50")
)
_KERNEL_DEFAULT_MIN_INTERVAL_SECONDS: int = int(
    os.getenv("MIN_INTERVAL_BETWEEN_RECURRENCE_FIRES_SECONDS", "60")
)


@dataclass(frozen=True)
class TokenBudget:
    """Resolved compute-resource governance for one workspace."""
    daily_spend_ceiling_usd: float
    max_judgment_recurrences_per_day: int
    min_interval_between_recurrence_fires_seconds: int
    overrides: dict[str, dict[str, Any]]

    def min_interval_for(self, slug: str) -> int:
        """Per-slug min-interval override, falling back to workspace default."""
        ov = self.overrides.get(slug) or {}
        v = ov.get("min_interval_seconds")
        if isinstance(v, int) and v > 0:
            return v
        return self.min_interval_between_recurrence_fires_seconds


def load_token_budget(client: Any, user_id: str) -> TokenBudget:
    """Resolve the workspace's `_token_budget.yaml` with kernel-default
    fall-through. Always returns a usable TokenBudget — no exceptions
    propagate to the scheduler.
    """
    defaults = TokenBudget(
        daily_spend_ceiling_usd=_KERNEL_DEFAULT_DAILY_SPEND_USD,
        max_judgment_recurrences_per_day=_KERNEL_DEFAULT_MAX_JUDGMENT_PER_DAY,
        min_interval_between_recurrence_fires_seconds=_KERNEL_DEFAULT_MIN_INTERVAL_SECONDS,
        overrides={},
    )
    try:
        from services.workspace_paths import SHARED_TOKEN_BUDGET_PATH
        res = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", f"/workspace/{SHARED_TOKEN_BUDGET_PATH}")
            .limit(1)
            .execute()
        )
        content = (res.data or [{}])[0].get("content") or ""
    except Exception as exc:
        logger.warning(
            "[TOKEN_BUDGET] read failed for user=%s, falling back to kernel defaults: %s",
            user_id[:8], exc,
        )
        return defaults

    if not content.strip():
        return defaults

    try:
        import yaml  # type: ignore
        parsed = yaml.safe_load(content) or {}
    except Exception as exc:
        logger.warning(
            "[TOKEN_BUDGET] YAML parse failed for user=%s, falling back: %s",
            user_id[:8], exc,
        )
        return defaults

    if not isinstance(parsed, dict):
        return defaults

    daily = parsed.get("daily_spend_ceiling_usd")
    daily_val = float(daily) if isinstance(daily, (int, float)) and daily > 0 else defaults.daily_spend_ceiling_usd

    max_jud = parsed.get("max_judgment_recurrences_per_day")
    max_val = int(max_jud) if isinstance(max_jud, int) and max_jud > 0 else defaults.max_judgment_recurrences_per_day

    min_iv = parsed.get("min_interval_between_recurrence_fires_seconds")
    min_val = int(min_iv) if isinstance(min_iv, int) and min_iv > 0 else defaults.min_interval_between_recurrence_fires_seconds

    overrides = parsed.get("overrides") or {}
    if not isinstance(overrides, dict):
        overrides = {}

    return TokenBudget(
        daily_spend_ceiling_usd=daily_val,
        max_judgment_recurrences_per_day=max_val,
        min_interval_between_recurrence_fires_seconds=min_val,
        overrides=overrides,
    )


def count_judgment_fires_today(client: Any, user_id: str) -> int:
    """Count today's (UTC) judgment-mode execution_events rows for the
    workspace. Used by the scheduler to gate on
    `max_judgment_recurrences_per_day`.
    """
    from datetime import datetime, timezone
    today_utc = datetime.now(timezone.utc).date().isoformat()
    try:
        res = (
            client.table("execution_events")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("mode", "judgment")
            .gte("created_at", f"{today_utc}T00:00:00+00:00")
            .lt("created_at", f"{today_utc}T23:59:59.999999+00:00")
            .execute()
        )
        return getattr(res, "count", None) or len(res.data or [])
    except Exception as exc:
        logger.warning(
            "[TOKEN_BUDGET] judgment count failed for user=%s: %s",
            user_id[:8], exc,
        )
        return 0


def seconds_since_last_fire(
    client: Any, user_id: str, slug: str,
) -> Optional[int]:
    """Return seconds since the most recent execution_events row for this
    slug, or None when no prior fire exists.
    """
    from datetime import datetime, timezone
    try:
        res = (
            client.table("execution_events")
            .select("created_at")
            .eq("user_id", user_id)
            .eq("slug", slug)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        row = (res.data or [{}])[0]
        ts = row.get("created_at")
        if not ts:
            return None
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        last_dt = datetime.fromisoformat(ts)
        return int((datetime.now(timezone.utc) - last_dt).total_seconds())
    except Exception as exc:
        logger.warning(
            "[TOKEN_BUDGET] last-fire lookup failed for slug=%s user=%s: %s",
            slug, user_id[:8], exc,
        )
        return None


# Default content seeded into _token_budget.yaml at workspace activation.
# Operator may freely edit; values here are the kernel-default fall-through.
DEFAULT_TOKEN_BUDGET_YAML = """\
# _token_budget.yaml — compute-resource governance (ADR-293 D7)
# Operator declares; Reviewer respects. Scheduler enforces at fire time.
# This file is GOVERNANCE per ADR-293 D2 — Reviewer cannot author.

# Hard cap on workspace daily LLM spend. Tripping this skips the fire
# and surfaces a system narrative entry; the next fire that would push
# past the ceiling waits until the daily window rolls over (00:00 UTC).
daily_spend_ceiling_usd: 10.00

# Cap on number of judgment-mode recurrence fires per UTC day.
# Mechanical-mode recurrences (zero LLM cost) don't count.
max_judgment_recurrences_per_day: 50

# Floor on cadence: a recurrence cannot fire more frequently than this
# many seconds apart (per-slug last_run_at gate). Operator may declare
# per-recurrence overrides under `overrides:` below.
min_interval_between_recurrence_fires_seconds: 60

# Per-recurrence overrides (optional). Example:
# overrides:
#   signal-evaluation:
#     min_interval_seconds: 900   # never more frequent than 15 min
"""


__all__ = [
    "TokenBudget",
    "load_token_budget",
    "count_judgment_fires_today",
    "seconds_since_last_fire",
    "DEFAULT_TOKEN_BUDGET_YAML",
]
