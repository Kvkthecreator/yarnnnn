"""
Agent implementations

ADR-061: Two-Path Architecture
- DeliverableAgent: Path B - async deliverable generation
- ThinkingPartnerAgent: Path A - real-time conversation

Legacy agents (SynthesizerAgent, ReportAgent) have been removed.
Legacy type names are mapped to DeliverableAgent for backwards compatibility.
"""

from .base import BaseAgent, AgentResult, ContextBundle, Memory, WorkOutput
from .factory import create_agent, get_valid_agent_types, normalize_agent_type, LEGACY_TYPE_MAP

__all__ = [
    "BaseAgent",
    "AgentResult",
    "ContextBundle",
    "Memory",
    "WorkOutput",
    "create_agent",
    "get_valid_agent_types",
    "normalize_agent_type",
    "LEGACY_TYPE_MAP",
]
