"""
Agent implementations

4 agent types:
- ResearchAgent: Deep investigation using context
- ContentAgent: Content creation from context
- ReportingAgent: Structured report generation
- ThinkingPartnerAgent: Conversational assistant
"""

from .base import BaseAgent, AgentResult, ContextBundle, Memory, WorkOutput
from .factory import create_agent

__all__ = [
    "BaseAgent",
    "AgentResult",
    "ContextBundle",
    "Memory",
    "WorkOutput",
    "create_agent",
]
