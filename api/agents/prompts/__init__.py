from __future__ import annotations
"""
YARNNN Prompt Modules (ADR-233 Phase 1 + bare-kernel product floor 2026-06-01).

The chat-profile half of this module was deleted by the bare-kernel product-floor
ratification (Direction A — program-activation is the floor; no freehand
conversational onboarding). The `YarnnnAgent` chat surface and its workspace /
entity prompt profiles died with ADR-257 (System Agent LLM stream removed); the
ADR-226 activation overlay died with them (it was only ever engaged by the dead
YarnnnAgent path). See docs/architecture/bare-kernel-product-floor-2026-06-01.md.

What remains is the LIVE headless path — the DispatchSpecialist surface. The
Reviewer composes its own system prompt in `agents/reviewer_agent.py` and does
not route through this module.

Profile keys (3 — headless only):
  headless/deliverable  — recurring report composition (replacive, gap-filling)
  headless/accumulation — entity tracking + domain synthesis (additive)
  headless/action       — action proposal (propose, do not execute)

MAINTENANCE shape has no LLM call, no profile.

Headless sections (under headless/):
  base.py         — HEADLESS_BASE_BLOCK (output rules, conventions, accumulation-first)
  deliverable.py  — DELIVERABLE_POSTURE
  accumulation.py — ACCUMULATION_POSTURE
  action.py       — ACTION_POSTURE
"""

# ADR-233 Phase 1: headless shape postures + universal base block.
from .headless.base import HEADLESS_BASE_BLOCK
from .headless.deliverable import DELIVERABLE_POSTURE
from .headless.accumulation import ACCUMULATION_POSTURE
from .headless.action import ACTION_POSTURE


# Map of headless profile keys to their posture string. Posture is a
# cognitive-job framing prepended to the cached HEADLESS_BASE_BLOCK so the LLM
# knows what kind of work it's doing before it reads the universal output rules.
HEADLESS_POSTURES: dict[str, str] = {
    "headless/deliverable": DELIVERABLE_POSTURE,
    "headless/accumulation": ACCUMULATION_POSTURE,
    "headless/action": ACTION_POSTURE,
}


def build_headless_system_block(profile_key: str) -> str:
    """Assemble the headless static system block for a given shape posture.

    ADR-233 Phase 1. The static block is the cached half of the headless
    prompt: shape posture (~150 words framing the cognitive job) + universal
    `HEADLESS_BASE_BLOCK` (output rules, conventions, accumulation-first,
    tool usage, visual assets, empty-context handling).

    The caller (`dispatch_helpers.build_task_execution_prompt`) is responsible
    for assembling the dynamic half (per-task context, deliverable spec,
    feedback, etc.) and applying the cache_control marker.

    Args:
        profile_key: One of "headless/deliverable", "headless/accumulation",
                     "headless/action".

    Returns:
        The static system block as a single string.
    """
    if profile_key not in HEADLESS_POSTURES:
        raise ValueError(
            f"Unknown headless profile key: {profile_key!r}. "
            f"Expected one of: {sorted(HEADLESS_POSTURES.keys())}"
        )
    posture = HEADLESS_POSTURES[profile_key]
    return f"{posture}\n\n{HEADLESS_BASE_BLOCK}"


# Public registry of valid profile keys. Imported by tests as the source of
# truth for what profiles exist. Chat profiles removed per the bare-kernel
# product-floor ratification (2026-06-01).
PROFILE_KEYS: tuple[str, ...] = (
    "headless/deliverable",
    "headless/accumulation",
    "headless/action",
)


def build_prompt(profile_key: str, **kwargs):
    """Unified prompt assembler dispatching on profile key.

    Post-bare-kernel-floor: only headless profiles remain. Headless profiles
    return a single string — the caller wraps it in a content block with its
    own dynamic content (per-task context, deliverable spec, feedback) and
    applies cache_control.

    Args:
        profile_key: One of PROFILE_KEYS (all `headless/*`).
        **kwargs: Ignored (headless posture is static; dynamic content is the
                  caller's job).

    Returns:
        The static headless system block as a string.
    """
    if profile_key.startswith("headless/"):
        return build_headless_system_block(profile_key)
    raise ValueError(
        f"Unknown profile key: {profile_key!r}. Expected one of: {list(PROFILE_KEYS)}"
    )
