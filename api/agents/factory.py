"""
Agent factory - Creates appropriate agent based on type

ADR-045: Updated agent types to reflect actual function:
- synthesizer: Synthesizes pre-fetched context (formerly "research")
- deliverable: Generates deliverables (formerly "content")
- report: Generates standalone reports (formerly "reporting")
- chat: Thinking Partner chat agent

Legacy type names are supported for backwards compatibility with
existing database records but will be migrated.
"""

from typing import Literal
from .base import BaseAgent


# New canonical types
AgentType = Literal["synthesizer", "deliverable", "report", "chat"]

# Legacy mappings for backwards compatibility
LEGACY_TYPE_MAP = {
    "research": "synthesizer",
    "content": "deliverable",
    "reporting": "report",
}


def create_agent(agent_type: str) -> BaseAgent:
    """
    Create agent instance based on type.

    Args:
        agent_type: One of synthesizer, deliverable, report, chat
                   Legacy types (research, content, reporting) are mapped
                   to new types for backwards compatibility.

    Returns:
        Configured agent instance
    """
    # Map legacy types to new types
    canonical_type = LEGACY_TYPE_MAP.get(agent_type, agent_type)

    if canonical_type == "synthesizer":
        from .synthesizer import SynthesizerAgent
        return SynthesizerAgent()
    elif canonical_type == "deliverable":
        from .deliverable import DeliverableAgent
        return DeliverableAgent()
    elif canonical_type == "report":
        from .report import ReportAgent
        return ReportAgent()
    elif canonical_type == "chat":
        from .thinking_partner import ThinkingPartnerAgent
        return ThinkingPartnerAgent()
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")


def get_valid_agent_types() -> list[str]:
    """Get list of valid agent types (new canonical names)."""
    return ["synthesizer", "deliverable", "report", "chat"]


def normalize_agent_type(agent_type: str) -> str:
    """Normalize legacy agent type to new canonical type."""
    return LEGACY_TYPE_MAP.get(agent_type, agent_type)
