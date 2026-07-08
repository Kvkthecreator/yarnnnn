"""Cost governance — the operation's spend envelope (ADR-327).

Per-workspace `_budget.yaml` declares the operator's dollar budget over a
timeframe. The wake funnel reads it before firing each judgment-mode wake;
when window-to-date spend reaches the budget, scheduled (cron_tick) wakes
are skipped while reactive wakes warn-but-fire (ADR-327 D4).

The governance file is operator-only-authored (governance/ root — locked
from the seat per ADR-320 CALLER_WRITE_POLICY): the Reviewer cannot raise
its own ceiling.

**Supersedes `services/token_budget.py` + `services/pace.py`** (ADR-327 D2).
Collapses the two cost/frequency files into one:

  - `_pace.yaml` (frequency cap `kind`) — DELETED. "How often" is the
    Reviewer's allocation problem within the budget, not an operator dial.
  - `_token_budget.yaml` (`daily_spend_ceiling_usd` + judgment-fire cap +
    per-slug floor) — folded here. The daily ceiling generalizes to an
    operator-chosen window; the judgment-fire cap is deleted (cost is
    governed directly in dollars, not via a fire-count proxy); the per-slug
    `min_interval` floor survives verbatim (legitimate anti-thrash mechanic
    orthogonal to cost — ADR-313 Gate 3).

Schema:

    budget:
      amount_usd: 50.00      # the spend envelope
      window: monthly        # monthly | weekly | daily — timeframe the amount covers
    per_wake_ceiling_usd: 1.00   # runaway floor: a single fire above this routes to operator
    min_interval_between_recurrence_fires_seconds: 60
    # overrides:
    #   <slug>:
    #     min_interval_seconds: 900

Kernel defaults (env-derived) apply when the file is absent or malformed.
Per-workspace governance always wins.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, Optional

logger = logging.getLogger(__name__)

BudgetWindow = Literal["monthly", "weekly", "daily"]
_VALID_WINDOWS: tuple[str, ...] = ("monthly", "weekly", "daily")

# Kernel defaults (ADR-327 seed: monthly/$50, sized against observed
# 30-day spend — see ADR-327 §5 open-question #2).
_KERNEL_DEFAULT_AMOUNT_USD: float = float(os.getenv("BUDGET_AMOUNT_USD", "50.0"))
_KERNEL_DEFAULT_WINDOW: str = os.getenv("BUDGET_WINDOW", "monthly")
_KERNEL_DEFAULT_PER_WAKE_CEILING_USD: float = float(
    os.getenv("PER_WAKE_CEILING_USD", "1.0")
)
_KERNEL_DEFAULT_MIN_INTERVAL_SECONDS: int = int(
    os.getenv("MIN_INTERVAL_BETWEEN_RECURRENCE_FIRES_SECONDS", "60")
)


@dataclass(frozen=True)
class Budget:
    """Resolved cost governance for one workspace."""
    amount_usd: float
    window: str  # monthly | weekly | daily
    per_wake_ceiling_usd: float
    min_interval_between_recurrence_fires_seconds: int
    overrides: dict[str, dict[str, Any]]

    def min_interval_for(self, slug: str) -> int:
        """Per-slug min-interval override, falling back to workspace default."""
        ov = self.overrides.get(slug) or {}
        v = ov.get("min_interval_seconds")
        if isinstance(v, int) and v > 0:
            return v
        return self.min_interval_between_recurrence_fires_seconds


def _window_floor_iso(window: str) -> str:
    """UTC ISO timestamp marking the start of the current budget window."""
    now = datetime.now(timezone.utc)
    if window == "daily":
        floor = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif window == "weekly":
        # ISO week: Monday 00:00 UTC.
        monday = now - __import__("datetime").timedelta(days=now.weekday())
        floor = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    else:  # monthly (default)
        floor = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return floor.isoformat()


def window_elapsed_days(window: str) -> float:
    """Days elapsed since the current window's floor (ADR-338 D4.4 runway input).

    Used to derive an observed daily burn = window_spend / elapsed_days. The
    floor is 0-elapsed at the instant the window rolls over; we clamp to a
    minimum so a same-instant read doesn't divide by zero (the route guards
    burn==0 anyway). Returns a float; e.g. 0.5 = twelve hours into the window.
    """
    from datetime import timedelta  # local import — module already imports datetime

    now = datetime.now(timezone.utc)
    floor = datetime.fromisoformat(_window_floor_iso(window))
    elapsed = (now - floor).total_seconds() / 86400.0
    # Clamp to a small positive floor: a fresh window shouldn't report
    # infinite/zero-day burn; the route treats burn==0 as "not enough data".
    return max(elapsed, 1.0 / 24.0)  # at least one hour of window


def load_budget(client: Any, user_id: str) -> Budget:
    """Resolve the workspace's `_budget.yaml` with kernel-default
    fall-through. Always returns a usable Budget — no exceptions propagate
    to the wake funnel.
    """
    defaults = Budget(
        amount_usd=_KERNEL_DEFAULT_AMOUNT_USD,
        window=_KERNEL_DEFAULT_WINDOW,
        per_wake_ceiling_usd=_KERNEL_DEFAULT_PER_WAKE_CEILING_USD,
        min_interval_between_recurrence_fires_seconds=_KERNEL_DEFAULT_MIN_INTERVAL_SECONDS,
        overrides={},
    )
    try:
        from services.workspace_paths import GOVERNANCE_BUDGET_PATH
        res = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", f"/workspace/{GOVERNANCE_BUDGET_PATH}")
            .limit(1)
            .execute()
        )
        content = (res.data or [{}])[0].get("content") or ""
    except Exception as exc:
        logger.warning(
            "[BUDGET] read failed for user=%s, falling back to kernel defaults: %s",
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
            "[BUDGET] YAML parse failed for user=%s, falling back: %s",
            user_id[:8], exc,
        )
        return defaults

    if not isinstance(parsed, dict):
        return defaults

    budget_block = parsed.get("budget") or {}
    if not isinstance(budget_block, dict):
        budget_block = {}

    amount = budget_block.get("amount_usd")
    amount_val = (
        float(amount)
        if isinstance(amount, (int, float)) and amount > 0
        else defaults.amount_usd
    )

    window = budget_block.get("window")
    window_val = window if window in _VALID_WINDOWS else defaults.window

    pwc = parsed.get("per_wake_ceiling_usd")
    pwc_val = (
        float(pwc)
        if isinstance(pwc, (int, float)) and pwc > 0
        else defaults.per_wake_ceiling_usd
    )

    min_iv = parsed.get("min_interval_between_recurrence_fires_seconds")
    min_val = (
        int(min_iv)
        if isinstance(min_iv, int) and min_iv > 0
        else defaults.min_interval_between_recurrence_fires_seconds
    )

    overrides = parsed.get("overrides") or {}
    if not isinstance(overrides, dict):
        overrides = {}

    return Budget(
        amount_usd=amount_val,
        window=window_val,
        per_wake_ceiling_usd=pwc_val,
        min_interval_between_recurrence_fires_seconds=min_val,
        overrides=overrides,
    )


def window_spend(
    client: Any, user_id: str, window: str, workspace_id: Optional[str] = None
) -> float:
    """Sum `execution_events.cost_usd` over the current budget window
    (ADR-291 unified cost ledger; ADR-327 D3 — reader only, no new writer).

    `window` ∈ {monthly, weekly, daily}; monthly = since UTC month start.
    Returns 0.0 on any read failure (fail-open — a read error must not
    silently starve the operation).

    ADR-416 Phase 4 (bug-fix): the window is scoped to the ACTING WORKSPACE
    (`workspace_id`), matching the balance hard-stop gate (get_effective_balance,
    migration 200). Pre-fix this read filtered `.eq("user_id", …)` — so at N>1 a
    member's/agent's envelope check summed the wrong rows (their own singleton or
    the owner's), diverging from the workspace-scoped balance gate on the binding
    unit. Resolution mirrors the balance gate (contextvar / owner fallback), so
    the ~single caller needs no change. Falls back to the `user_id` filter only
    when no workspace resolves (fail-open, pre-ADR-416 behavior).
    """
    floor_iso = _window_floor_iso(window)
    try:
        from services.workspace_context import effective_workspace_id
        ws = effective_workspace_id(user_id, workspace_id)
        q = client.table("execution_events").select("cost_usd").gte("created_at", floor_iso)
        # Scope to the workspace pool (ADR-416); fall back to user_id only if no
        # workspace resolves (legacy safety — never a silent wrong-scope sum).
        q = q.eq("workspace_id", ws) if ws else q.eq("user_id", user_id)
        res = q.execute()
        rows = res.data or []
        return float(sum(float(r.get("cost_usd") or 0) for r in rows))
    except Exception as exc:
        logger.warning(
            "[BUDGET] window_spend failed for user=%s window=%s: %s",
            user_id[:8], window, exc,
        )
        return 0.0


def seconds_since_last_fire(
    client: Any, user_id: str, slug: str, workspace_id: Optional[str] = None,
) -> Optional[int]:
    """Return seconds since the most recent execution_events row for this
    slug, or None when no prior fire exists. (Per-slug min-interval floor —
    ADR-313 Gate 3, survives the budget collapse.)

    ADR-416 Phase 4 (bug-fix): scoped to the ACTING WORKSPACE — the per-slug
    pacing floor is a property of the recurrence in its workspace, not of the
    owner's user_id across workspaces. Mirrors window_spend's resolution; falls
    back to user_id only when no workspace resolves.
    """
    try:
        from services.workspace_context import effective_workspace_id
        ws = effective_workspace_id(user_id, workspace_id)
        q = (
            client.table("execution_events")
            .select("created_at")
            .eq("slug", slug)
            .order("created_at", desc=True)
            .limit(1)
        )
        q = q.eq("workspace_id", ws) if ws else q.eq("user_id", user_id)
        res = q.execute()
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
            "[BUDGET] last-fire lookup failed for slug=%s user=%s: %s",
            slug, user_id[:8], exc,
        )
        return None


# Default content seeded into _budget.yaml at workspace activation.
# Operator may freely edit; values here are the kernel-default fall-through.
# Monthly/$50 sized against observed 30-day spend (ADR-327 §5 open-question #2).
DEFAULT_BUDGET_YAML = """\
# _budget.yaml — the operation's spend envelope (ADR-327)
# Operator declares; the Reviewer respects + allocates wakes within it.
# This file is GOVERNANCE per ADR-293 D2 — the Reviewer cannot author it.
#
# Replaces _pace.yaml (deleted — tempo is the Reviewer's allocation problem,
# not an operator dial) + _token_budget.yaml (folded in).

budget:
  # The dollar amount this operation may spend over the window below.
  # Every judgment wake (scheduled + reactive) draws from it; mechanical
  # recurrences are free. The Reviewer allocates wakes within this envelope
  # against ground truth — that allocation, improving over tenure, is the
  # self-improving loop.
  amount_usd: 50.00
  # monthly | weekly | daily — the timeframe amount_usd covers.
  # Monthly absorbs day-to-day variance (the point of an envelope, not a
  # daily ceiling).
  window: monthly

# Runaway floor: a single wake whose projected cost exceeds this routes to
# the operator regardless of remaining budget. Independent of the envelope.
per_wake_ceiling_usd: 1.00

# Per-slug fire floor (ADR-313 Gate 3): a recurrence cannot fire more
# frequently than this many seconds apart. Orthogonal to cost.
min_interval_between_recurrence_fires_seconds: 60

# Per-recurrence overrides (optional). Example:
# overrides:
#   signal-evaluation:
#     min_interval_seconds: 900   # never more frequent than 15 min
"""


__all__ = [
    "Budget",
    "BudgetWindow",
    "load_budget",
    "window_spend",
    "seconds_since_last_fire",
    "DEFAULT_BUDGET_YAML",
]
