"""
Agent factory - Creates appropriate agent based on type

ADR-045: Agent types:
- synthesizer: Synthesizes pre-fetched context
- deliverable: Generates deliverables
- report: Generates standalone reports
- chat: Thinking Partner chat agent
"""

from typing import Literal
from .base import BaseAgent


AgentType = Literal["synthesizer", "deliverable", "report", "chat"]


def create_agent(agent_type: str) -> BaseAgent:
    """
    Create agent instance based on type.

    Args:
        agent_type: One of synthesizer, deliverable, report, chat

    Returns:
        Configured agent instance
    """
    if agent_type == "synthesizer":
        from .synthesizer import SynthesizerAgent
        return SynthesizerAgent()
    elif agent_type == "deliverable":
        from .deliverable import DeliverableAgent
        return DeliverableAgent()
    elif agent_type == "report":
        from .report import ReportAgent
        return ReportAgent()
    elif agent_type == "chat":
        from .thinking_partner import ThinkingPartnerAgent
        return ThinkingPartnerAgent()
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")


def get_valid_agent_types() -> list[str]:
    """Get list of valid agent types."""
    return ["synthesizer", "deliverable", "report", "chat"]
