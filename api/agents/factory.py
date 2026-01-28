"""
Agent factory - Creates appropriate agent based on type
"""

from typing import Literal
from .base import BaseAgent


def create_agent(agent_type: Literal["research", "content", "reporting", "chat"]) -> BaseAgent:
    """
    Create agent instance based on type.

    Args:
        agent_type: One of research, content, reporting, chat

    Returns:
        Configured agent instance
    """
    if agent_type == "research":
        from .research import ResearchAgent
        return ResearchAgent()
    elif agent_type == "content":
        from .content import ContentAgent
        return ContentAgent()
    elif agent_type == "reporting":
        from .reporting import ReportingAgent
        return ReportingAgent()
    elif agent_type == "chat":
        from .thinking_partner import ThinkingPartnerAgent
        return ThinkingPartnerAgent()
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")
