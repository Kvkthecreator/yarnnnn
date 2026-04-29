"""Headless prompt profiles (ADR-233 Phase 1).

Three shape postures + universal `HEADLESS_BASE_BLOCK`. The dispatcher's
`build_task_execution_prompt` composes them via the unified
`prompts.build_prompt(profile_key, ...)` resolver in the parent package.

Profiles:
  headless/deliverable  — recurring report composition (replacive, gap-filling)
  headless/accumulation — entity tracking + domain synthesis (additive)
  headless/action       — action proposal (propose, do not execute)

MAINTENANCE shape has no LLM call, no profile here.
"""

from .base import HEADLESS_BASE_BLOCK
from .deliverable import DELIVERABLE_POSTURE
from .accumulation import ACCUMULATION_POSTURE
from .action import ACTION_POSTURE

__all__ = [
    "HEADLESS_BASE_BLOCK",
    "DELIVERABLE_POSTURE",
    "ACCUMULATION_POSTURE",
    "ACTION_POSTURE",
]
