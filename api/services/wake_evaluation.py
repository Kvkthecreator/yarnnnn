"""
services/wake_evaluation.py — The wake evaluation funnel (ADR-296 v2 D2).

The funnel decides which wake proposals warrant the Reviewer's full
real-time loop. Per ADR-296 v2 D2 there is ONE evaluation mechanism;
five wake sources contribute proposals to it.

Two tiers:

  - Tier 1 (deterministic, zero LLM cost) — given the wake-source
    taxonomy + payload + budget state + recent-fire history, decide
    `skip` | `tier_2` | `escalate` | `mechanical`. Most cron-tick
    wakes resolve here. Operator-addressed wakes always escalate
    (operator presence is itself a wake-warrant). Mechanical-mode
    recurrences bypass the Reviewer entirely with `mechanical`.

  - Tier 2 (cheap Haiku, ~$0.001/call) — when Tier 1 returns
    `tier_2`, a minimal-envelope LLM call asks "given the wake event
    and your standing intent, does this moment warrant your full
    attention now?" Decision: `tier_2_wait` | `tier_2_observe` |
    `escalate`. Returns to bodies as a FunnelDecision.

The funnel decision stamps every execution_events row via the
wake_source + funnel_decision columns (migration 177). Operators
observe funnel behavior via that telemetry.

ADR-296 v2 §C1 calibration: Tier 2 cost is bounded by the wake
frequency. At today's scheduler tick cadence (5min) + per-workspace
recurrence counts (~10-15 active), expected Tier 2 calls are
substantially below the daily spend ceiling. If empirical observation
shows Tier 2 cost approaching the ceiling, the operator's
`_token_budget.yaml` declares the calibration knob.

Reviewer's standing intent (`/workspace/review/standing_intent.md`)
shapes Tier 2 reasoning: it carries the Reviewer's prior-cycle
declarations of what substrate transitions / next moments warrant
its attention. Tier 2 reads it as the standing-intent envelope.

Module organization:

  - `evaluate(client, user_id, source, payload)` — top-level decision
    function. Returns `FunnelDecision`. Composes Tier 1 + Tier 2.

  - `tier_1_decision(source, payload, budget_signals)` — pure
    deterministic decision logic. Synchronous. No LLM.

  - `tier_2_decision(client, user_id, source, payload)` — async
    Haiku call. Loads minimal envelope, asks the gate question,
    parses response.

  - `BudgetSignals` — dataclass carrying the inputs Tier 1 needs
    (balance_ok, daily_spend, spend_ceiling, judgment_count_today,
    judgment_cap, min_interval_floor, seconds_since_last_fire).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Literal, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Taxonomies (mirror services/wake.py — Singular Implementation)
# ---------------------------------------------------------------------------

WakeSource = Literal[
    "cron_tick",
    "addressed",
    "proposal_arrival",
    "substrate_event",
    "manual_fire",
]

FunnelDecision = Literal[
    "skip",
    "tier_2_wait",
    "tier_2_observe",
    "escalate",
    "mechanical",
]


# ---------------------------------------------------------------------------
# Tier 1 inputs — budget signals (substrate-aware kernel pre-conditions)
# ---------------------------------------------------------------------------


@dataclass
class BudgetSignals:
    """Substrate-aware inputs Tier 1 reads to gate wake escalation.

    Carries the pre-computed budget + history signals the kernel needs
    to short-circuit the funnel before doing any work. Callers
    (`services/wake.py::_invoke_recurrence_wake` and substrate-event
    body) assemble this dict from `services.platform_limits.check_balance`
    + `services.token_budget.load_token_budget` + recent
    execution_events lookup.

    All fields optional — `None` means "don't check this gate."
    """

    balance_ok: Optional[bool] = None
    daily_spend: Optional[float] = None
    spend_ceiling: Optional[float] = None
    judgment_count_today: Optional[int] = None
    judgment_cap: Optional[int] = None
    min_interval_floor_sec: Optional[int] = None
    seconds_since_last_fire: Optional[int] = None
    prior_failure_was_capability_missing: Optional[bool] = None


# ---------------------------------------------------------------------------
# Tier 1 — deterministic decision (zero LLM)
# ---------------------------------------------------------------------------


def tier_1_decision(
    source: WakeSource,
    payload: dict,
    budget: BudgetSignals,
) -> tuple[FunnelDecision, str]:
    """Tier 1 deterministic funnel decision per ADR-296 v2 D2.

    Returns a (decision, reason) tuple. Reason is a structured tag
    suitable for execution_events.error_reason or downstream logging.

    Decision logic:

      addressed         → escalate (operator presence is wake-warrant)
      proposal_arrival  → escalate (proposal creation is wake-warrant)
      manual_fire       → escalate (operator explicit assertion)
      substrate_event   → escalate (hook match is the wake-warrant)
                          (kernel gates still apply at body layer)
      cron_tick:
        mechanical-mode recurrence  → mechanical
        budget exhausted            → skip
        spend ceiling reached       → skip (reactive) or escalate (manual proceed)
        judgment cap reached        → skip
        min-interval floor          → skip
        otherwise                   → escalate
                                     (Tier 2 reserved for ambiguous-freshness
                                      cases that don't have a deterministic
                                      signal; today's runtime treats fresh
                                      recurrences as escalate by default,
                                      Tier 2 is the upgrade path)

    Args:
        source: WakeSource value
        payload: source-specific dict. For cron_tick:
            {"recurrence": Recurrence, "is_reactive": bool}
            For substrate_event: {"hook": dict}
        budget: BudgetSignals dataclass (only consulted for cron_tick)

    Returns:
        (decision, reason) — decision is the FunnelDecision value;
        reason is a structured tag.
    """
    if source in ("addressed", "proposal_arrival", "manual_fire"):
        return "escalate", "wake_warrant_unconditional"

    if source == "substrate_event":
        return "escalate", "hook_match"

    if source == "cron_tick":
        recurrence = payload.get("recurrence")
        if recurrence is not None and getattr(recurrence, "mode", "judgment") == "mechanical":
            return "mechanical", "mechanical_mode_bypass"

        # Kernel gates — substrate-aware Tier 1 short-circuits
        if budget.balance_ok is False:
            return "skip", "balance_exhausted"

        if (
            budget.daily_spend is not None
            and budget.spend_ceiling is not None
            and budget.daily_spend >= budget.spend_ceiling
        ):
            return "skip", "spend_ceiling"

        if (
            budget.judgment_count_today is not None
            and budget.judgment_cap is not None
            and budget.judgment_count_today >= budget.judgment_cap
        ):
            return "skip", "judgment_cap"

        if (
            budget.seconds_since_last_fire is not None
            and budget.min_interval_floor_sec is not None
            and budget.seconds_since_last_fire < budget.min_interval_floor_sec
        ):
            return "skip", "min_interval"

        return "escalate", "fresh_judgment_cycle"

    return "escalate", f"unknown_source:{source}"


# ---------------------------------------------------------------------------
# Tier 2 — cheap Haiku idle-tick judgment
# ---------------------------------------------------------------------------


_TIER_2_PROMPT_TEMPLATE = """\
A wake proposal was raised in the YARNNN substrate-canonical world.

Wake source: {source}
Substrate context: {context_summary}

Reviewer standing intent (excerpt):
{standing_intent}

Operator mandate (excerpt):
{mandate}

Given the wake event and your standing intent, does this moment warrant
your full attention now? Choose exactly one:

  - wait     — defer; nothing has changed enough since last cycle
  - observe  — note but don't act; substrate change is small / routine
  - escalate — substrate has changed enough to warrant a full Reviewer cycle

Respond with one word: wait | observe | escalate
"""


async def tier_2_decision(
    client: Any,
    user_id: str,
    source: WakeSource,
    payload: dict,
) -> tuple[FunnelDecision, str]:
    """Tier 2 cheap Haiku decision per ADR-296 v2 D2.

    Loads a minimal envelope (Reviewer standing intent excerpt + operator
    mandate excerpt + wake-source context summary) and asks Haiku
    whether the moment warrants the Reviewer's full cycle. Returns
    `tier_2_wait`, `tier_2_observe`, or `escalate`.

    The token cost (caller="reviewer-tier-2-idle-tick") is recorded
    via the standard cost ledger.

    Failure handling: any exception in the LLM call returns
    ("escalate", "tier_2_exception_fail_open") — failing open is the
    safe default (better to over-fire than to silently suppress).

    Args:
        client: Supabase service client
        user_id: Workspace owner UUID
        source: WakeSource value (informs the wake-event summary)
        payload: source-specific dict (informs the wake-event summary)

    Returns:
        (decision, reason) tuple. Decision is one of tier_2_wait |
        tier_2_observe | escalate. Reason is "tier_2_<verdict>" or
        "tier_2_exception_fail_open".
    """
    # Allow tests to disable the Tier 2 LLM call via env var so they
    # don't burn real API budget. When disabled, fail open to escalate.
    if os.environ.get("WAKE_TIER_2_DISABLED") == "1":
        return "escalate", "tier_2_disabled"

    try:
        from services.workspace import UserMemory
        from services.anthropic import chat_completion

        # Load minimal envelope. Both files are small enough not to
        # need truncation; we cap at ~2k chars defensively.
        memory = UserMemory(client, user_id)
        try:
            standing_intent = (memory.read("review/standing_intent.md") or "")[:2000]
        except Exception:
            standing_intent = ""
        try:
            mandate = (memory.read("context/_shared/MANDATE.md") or "")[:2000]
        except Exception:
            mandate = ""

        context_summary = _summarize_wake_context(source, payload)

        prompt = _TIER_2_PROMPT_TEMPLATE.format(
            source=source,
            context_summary=context_summary,
            standing_intent=standing_intent or "(empty — no prior cycle declared interest)",
            mandate=mandate or "(empty — operator has not declared mandate)",
        )

        # ADR-291: Haiku rate via the canonical cost ledger.
        # caller="reviewer-tier-2-idle-tick" stamps the telemetry call
        # for cost observability.
        response_text, _meta = await chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            user_id=user_id,
            caller="reviewer-tier-2-idle-tick",
        )

        verdict = (response_text or "").strip().lower()
        if "escalate" in verdict:
            return "escalate", "tier_2_escalate"
        if "observe" in verdict:
            return "tier_2_observe", "tier_2_observe"
        if "wait" in verdict:
            return "tier_2_wait", "tier_2_wait"
        # Unparseable — fail open
        logger.warning(
            "[WAKE:tier_2] unparseable Haiku verdict %r for source=%s — escalating",
            verdict, source,
        )
        return "escalate", "tier_2_unparseable_fail_open"
    except Exception as exc:
        logger.warning(
            "[WAKE:tier_2] Haiku call raised (failing open to escalate): %s", exc,
        )
        return "escalate", "tier_2_exception_fail_open"


def _summarize_wake_context(source: WakeSource, payload: dict) -> str:
    """Produce a one-line summary of the wake event for Tier 2's envelope."""
    if source == "cron_tick":
        rec = payload.get("recurrence")
        slug = getattr(rec, "slug", "?") if rec is not None else "?"
        mode = getattr(rec, "mode", "?") if rec is not None else "?"
        return f"cron-fired recurrence slug={slug!r} mode={mode!r}"
    if source == "substrate_event":
        hook = payload.get("hook") or {}
        path = payload.get("path") or "?"
        return (
            f"substrate-event hook slug={hook.get('slug', '?')!r} "
            f"matched path={path!r}"
        )
    return f"source={source}"


# ---------------------------------------------------------------------------
# Top-level evaluate() — composes Tier 1 + Tier 2
# ---------------------------------------------------------------------------


async def evaluate(
    client: Any,
    user_id: str,
    *,
    source: WakeSource,
    payload: dict,
    budget: Optional[BudgetSignals] = None,
) -> tuple[FunnelDecision, str]:
    """Singular wake-evaluation entry per ADR-296 v2 D2.

    Composes Tier 1 + Tier 2. The bodies in services/wake.py call this
    to receive the funnel decision, then act on it.

    Tier 1 is always evaluated. If Tier 1 returns `tier_2`, Tier 2
    fires. Otherwise the Tier 1 decision propagates.

    Args:
        client: Supabase service client
        user_id: Workspace owner UUID
        source: WakeSource value
        payload: source-specific dict
        budget: BudgetSignals dataclass (only consulted for cron_tick;
            callers should pre-compute this from platform_limits +
            token_budget + execution_events queries)

    Returns:
        (decision, reason) tuple. Decision is the final FunnelDecision;
        reason is a structured tag.
    """
    if budget is None:
        budget = BudgetSignals()

    decision, reason = tier_1_decision(source, payload, budget)

    # ADR-296 v2 §C1: Tier 2 is invoked only when Tier 1 returns a
    # `tier_2` sentinel. Current Tier 1 logic returns escalate as the
    # default (no Tier 2 path is wired today); the hook is here for
    # future ambiguous-freshness cases.
    if decision == "tier_2":  # type: ignore[comparison-overlap]
        return await tier_2_decision(client, user_id, source, payload)

    return decision, reason


__all__ = [
    "WakeSource",
    "FunnelDecision",
    "BudgetSignals",
    "tier_1_decision",
    "tier_2_decision",
    "evaluate",
]
