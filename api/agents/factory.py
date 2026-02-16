"""
Agent factory - Creates appropriate agent based on type

ADR-061: Two-Path Architecture
- deliverable: DeliverableAgent for Path B (async deliverable generation)
- chat: ThinkingPartnerAgent for Path A (real-time conversation)

Legacy agent types (synthesizer, report, research, content, reporting)
are mapped for backwards compatibility but all resolve to DeliverableAgent.
"""

from typing import Literal
from .base import BaseAgent


# Current valid agent types
AgentType = Literal["deliverable", "chat"]

# Legacy type mappings for backwards compatibility
# These were separate agents but are now handled by DeliverableAgent
LEGACY_TYPE_MAP = {
    "synthesizer": "deliverable",  # Was SynthesizerAgent
    "report": "deliverable",       # Was ReportAgent
    "research": "deliverable",     # Old name for synthesizer
    "content": "deliverable",      # Old name for deliverable
    "reporting": "deliverable",    # Old name for report
}


def normalize_agent_type(agent_type: str) -> str:
    """
    Normalize agent type to current naming.

    Maps legacy names to current types.
    """
    return LEGACY_TYPE_MAP.get(agent_type, agent_type)


def create_agent(agent_type: str) -> BaseAgent:
    """
    Create agent instance based on type.

    Args:
        agent_type: One of deliverable, chat (or legacy names)

    Returns:
        Configured agent instance
    """
    # Normalize legacy types
    normalized_type = normalize_agent_type(agent_type)

    if normalized_type == "deliverable":
        from .deliverable import DeliverableAgent
        return DeliverableAgent()
    elif normalized_type == "chat":
        from .thinking_partner import ThinkingPartnerAgent
        return ThinkingPartnerAgent()
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")


def get_valid_agent_types() -> list[str]:
    """Get list of valid agent types (current names only)."""
    return ["deliverable", "chat"]
