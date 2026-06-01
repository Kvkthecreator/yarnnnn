"""
Agent implementations

- Base classes: BaseAgent, ContextBundle, Memory (shared types — still consumed
  by reviewer_agent type hints + integration agents)
- YarnnnAgent: DELETED (bare-kernel product floor, 2026-06-01 — the chat surface
  died with ADR-257; see docs/architecture/bare-kernel-product-floor-2026-06-01.md)
- Integration agents: DELETED (ADR-153 — platform data flows through task execution)
"""

from .base import BaseAgent, AgentResult, ContextBundle, Memory

__all__ = [
    "BaseAgent",
    "AgentResult",
    "ContextBundle",
    "Memory",
]
