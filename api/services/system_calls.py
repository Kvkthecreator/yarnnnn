"""System calls — the model each piece of MACHINERY runs on (ADR-556 D1).

⚠️ TWO POPULATIONS OF LLM CALL, AND THEY ARE NOT THE SAME KIND OF FACT.

    SYSTEMATIC (this file)  — machinery. Nobody picks these; the SYSTEM does.
                              Governed by cost, stability, scalability per
                              CALL TYPE. Optionality here is a liability.
    USER-FACING             — chat, lanes, apps. Routing IS the feature.
                              Governed by choice + defaults + visible cost.
                              Lives in `lane_runner.LANE_MODELS` (the member's
                              whitelist) + `agents_registry.KERNEL_AGENTS`
                              (the colleague whose engine rides behind a name).

Collapsing the two was the standing error this module ends. A member should
never see `web_search`'s continuation model on a picker, and a fact-extraction
call should never be re-pointed by a member's engine preference. **The boundary
is the point; a registry that serves both populations has rebuilt the spec
sheet ADR-460 deleted.**

The third population, named here so it is not mistaken for a gap:

    THE STEWARD — Freddie. `services/model_selection.py` (ADR-402), Anthropic-
                  direct by ADR-463 D3 (prompt caching the transport cannot
                  carry). Systematic in nature, but it has its OWN table with
                  its own trigger-shape key and round budgets. It is not folded
                  in here: one table per routing key, and Freddie's key is the
                  trigger shape, not the call type.

WHY CALL TYPE IS THE UNIT (and not "tier")
Before this module, nine modules each answered "which model?" locally, and the
REASONING lived only as prose above a constant ("Haiku is sufficient for fact
extraction", "reuses the specialist bounded-loop model"). Tier alone throws
that away — a tier is a VALUE a call type HAS, never an identity you can
attribute a cost to. Keying on the call type gives the reasoning a declared
home and makes `execution_events` answerable: *what did extraction cost this
month?* The `tier` field rides along as the cost dial.

WHY THE VALUES CARRY PROVIDER PREFIXES (ADR-463 D1, applied here)
Every literal this module replaces was a BARE Anthropic id — so the machinery
could not spell a foreign model even in principle. **A dial whose every
position is the same vendor is not a dial.** Values are the `provider/model`
form `LANE_MODELS` and LiteLLM already speak; `strip_provider` (imported from
model_selection — ONE splitter) feeds the Anthropic SDK its own bare id at the
call. At N=1 per row this is byte-identical; what changes is that the table can
now NAME a model it does not yet call.

Env overrides, per deployment, read at CALL time (never import time):

    YARNNN_SYSCALL_{CALL_TYPE}   e.g. YARNNN_SYSCALL_FACT_EXTRACTION

This replaces the ad-hoc `MEMORY_EXTRACTION_MODEL`, which bound TWO unrelated
call types (fact extraction + session summary) to one dial: moving one moved
the other, silently. Two call types, two rows, two dials.

Adding a system call = a row here + a `_BILLING_RATES` row (gate-asserted:
an unpriced model prices at the Sonnet default, which is a silent cost lie).
"""

from __future__ import annotations

import logging
import os
from typing import NamedTuple

logger = logging.getLogger(__name__)


class SystemCall(NamedTuple):
    """One kind of machinery call: its engine, its cost tier, and WHY."""

    model: str   # provider/model — the honest name (ADR-463 D1)
    tier: str    # cheap | standard — the cost dial
    reason: str  # why THIS tier serves THIS call type


#: Cost tiers. Not a model list — a statement about what a call type NEEDS.
TIER_CHEAP = "cheap"        # bounded, mechanical, small output
TIER_STANDARD = "standard"  # judgment, authored prose, multi-round loops

#: THE SYSTEMATIC REGISTRY — the only place a machinery model id appears.
#: Keys are call types (string values double as env-var suffixes).
SYSTEM_CALLS: dict[str, SystemCall] = {
    "wake_triage": SystemCall(
        model="anthropic/claude-haiku-4-5",
        tier=TIER_CHEAP,
        reason=(
            "ADR-296 funnel tier-2: a 10-token wait/observe/escalate verdict on "
            "an idle tick. The whole point is to be cheaper than the wake it "
            "prevents — a standard-tier triage costs more than escalating."
        ),
    ),
    "fact_extraction": SystemCall(
        model="anthropic/claude-haiku-4-5",
        tier=TIER_CHEAP,
        reason="Pulling stated facts out of a transcript is recall, not judgment.",
    ),
    "session_summary": SystemCall(
        model="anthropic/claude-haiku-4-5",
        tier=TIER_CHEAP,
        reason=(
            "Condensing a transcript already in context. Distinct ROW from "
            "fact_extraction though they share a tier today: they are different "
            "call types, and one env dial must never move both (the "
            "MEMORY_EXTRACTION_MODEL collision this registry ends)."
        ),
    ),
    "web_search_continuation": SystemCall(
        model="anthropic/claude-haiku-4-5",
        tier=TIER_CHEAP,
        reason=(
            "Drives Anthropic's server-side web_search tool at max_tokens=50. "
            "The model arbitrates the search loop; it does not author."
        ),
    ),
    "identity_inference": SystemCall(
        model="anthropic/claude-sonnet-5",
        tier=TIER_STANDARD,
        reason=(
            "Authors IDENTITY.md from operator source material at onboarding — "
            "a once-per-workspace call whose output the operator reads as the "
            "system's first impression. Quality dominates cost at N=1."
        ),
    ),
    "recurrence_prompt_inference": SystemCall(
        model="anthropic/claude-sonnet-5",
        tier=TIER_STANDARD,
        reason="Refines a recurrence's standing prompt — authored text that then runs repeatedly.",
    ),
    "connector_derive": SystemCall(
        model="anthropic/claude-sonnet-5",
        tier=TIER_STANDARD,
        reason=(
            "ADR-580: the intake pipeline's distil step for connector lanes — "
            "one bounded turn maintaining a member-read living digest from "
            "platform raw. Authored prose members correct and agents recall; "
            "the new-raw gate + 6h floor bound the call count, so quality "
            "dominates. Machinery, not an app: nobody picks this engine."
        ),
    ),
    "specialist_dispatch": SystemCall(
        model="anthropic/claude-sonnet-5",
        tier=TIER_STANDARD,
        reason=(
            "The sub-LLM seam (bounded loop, 4096 tokens). DORMANT — "
            "VALID_SPECIALIST_ROLES is empty and the tool is unregistered; the "
            "row keeps the seam's engine declared rather than hardcoded."
        ),
    ),
}


def resolve_system_call(call_type: str) -> SystemCall:
    """The engine for a machinery call type. Env override read at CALL time.

    Raises KeyError on an undeclared call type — a caller naming one that does
    not exist is a bug, not a routing decision to paper over with a default
    (the ADR-450 precedent: an unknown recipe is a caller bug).
    """
    call = SYSTEM_CALLS[call_type]
    override = os.environ.get(f"YARNNN_SYSCALL_{call_type.upper()}", "").strip()
    if not override:
        return call
    logger.info(
        "[SYSCALL] %s overridden by env: %s → %s", call_type, call.model, override,
    )
    return call._replace(model=override)


def system_call_model(call_type: str) -> str:
    """The BARE model id for a machinery call type — what an Anthropic-SDK
    caller passes as `model=`. The seam between the table's honest
    `provider/model` name and a vendor SDK that wants its own bare id
    (ADR-463 D1; ONE splitter, in model_selection)."""
    from services.model_selection import strip_provider
    return strip_provider(resolve_system_call(call_type).model)


__all__ = [
    "SYSTEM_CALLS",
    "SystemCall",
    "TIER_CHEAP",
    "TIER_STANDARD",
    "resolve_system_call",
    "system_call_model",
]
