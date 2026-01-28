"""
Agent implementations

4 agent types:
- ResearchAgent: Deep investigation using context
- ContentAgent: Content creation from context
- ReportingAgent: Structured report generation
- ThinkingPartnerAgent: Conversational assistant
"""

from .base import BaseAgent, AgentResult, ContextBundle
from .factory import create_agent

__all__ = ["BaseAgent", "AgentResult", "ContextBundle", "create_agent"]
