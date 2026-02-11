"""
Agent implementations

ADR-045: Agent types renamed for clarity:
- SynthesizerAgent: Synthesizes pre-fetched context (formerly ResearchAgent)
- DeliverableAgent: Generates deliverables (formerly ContentAgent)
- ReportAgent: Generates standalone reports (formerly ReportingAgent)
- ThinkingPartnerAgent: Conversational assistant
"""

from .base import BaseAgent, AgentResult, ContextBundle, Memory, WorkOutput
from .factory import create_agent, get_valid_agent_types, normalize_agent_type

__all__ = [
    "BaseAgent",
    "AgentResult",
    "ContextBundle",
    "Memory",
    "WorkOutput",
    "create_agent",
    "get_valid_agent_types",
    "normalize_agent_type",
]
