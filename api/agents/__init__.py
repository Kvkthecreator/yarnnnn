"""
Agent implementations

- ThinkingPartnerAgent: Real-time TP conversation agent
- Base classes: BaseAgent, ContextBundle, Memory (shared types)
- Integration agents: DELETED (ADR-153 — platform data flows through task execution)
"""

from .base import BaseAgent, AgentResult, ContextBundle, Memory

__all__ = [
    "BaseAgent",
    "AgentResult",
    "ContextBundle",
    "Memory",
]
