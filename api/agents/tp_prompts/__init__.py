"""
Thinking Partner Prompt Modules (ADR-059: Modular Prompt Architecture)

Prompts are split into composable sections for maintainability:
- base.py: Core identity and style
- tools.py: Tool documentation (Read, Write, Search, etc.)
- platforms.py: Platform-specific tools (Slack, Notion, Gmail, Calendar)
- behaviors.py: Behavioral guidelines (Search→Read→Act, resilience, etc.)
- onboarding.py: New user onboarding context

Usage:
    from agents.tp_prompts import build_system_prompt
"""

from .base import BASE_PROMPT, SIMPLE_PROMPT
from .tools import TOOLS_SECTION
from .platforms import PLATFORMS_SECTION
from .behaviors import BEHAVIORS_SECTION
from .onboarding import ONBOARDING_CONTEXT


def build_system_prompt(
    *,
    with_tools: bool = False,
    is_onboarding: bool = False,
    context: str = "",
    onboarding_context: str = "",
) -> str:
    """
    Build the full system prompt from modular sections.

    Args:
        with_tools: Include tool documentation
        is_onboarding: Include onboarding guidance
        context: Working memory / context section
        onboarding_context: Onboarding-specific context (if is_onboarding)

    Returns:
        Complete system prompt string
    """
    if not with_tools:
        # Simple prompt without tools
        return SIMPLE_PROMPT.format(context=context)

    # Full prompt with tools
    sections = [
        BASE_PROMPT,
        BEHAVIORS_SECTION,
        TOOLS_SECTION,
        PLATFORMS_SECTION,
    ]

    # Add onboarding if applicable
    if is_onboarding:
        sections.append(ONBOARDING_CONTEXT)

    # Combine sections
    prompt = "\n\n".join(sections)

    # Insert context placeholder
    prompt = prompt.replace("{context}", context)
    prompt = prompt.replace("{onboarding_context}", onboarding_context if is_onboarding else "")

    return prompt
