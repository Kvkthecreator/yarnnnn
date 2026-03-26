"""
Thinking Partner Prompt Modules (ADR-059: Modular Prompt Architecture)

Prompts are split into composable sections for maintainability:
- base.py: Core identity and style
- tools.py: Tool documentation (Read, Write, Search, etc.)
- platforms.py: Platform-specific tools (Slack, Notion, Gmail, Calendar)
- behaviors.py: Behavioral guidelines (Search→Read→Act, resilience, etc.)
- onboarding.py: Context awareness (always-on, graduated)

Usage:
    from agents.tp_prompts import build_system_prompt
"""

from .base import BASE_PROMPT, SIMPLE_PROMPT
from .tools import TOOLS_SECTION
from .platforms import PLATFORMS_SECTION
from .behaviors import BEHAVIORS_SECTION
from .onboarding import CONTEXT_AWARENESS


def build_system_prompt(
    *,
    with_tools: bool = False,
    context: str = "",
) -> str:
    """
    Build the full system prompt from modular sections.

    Args:
        with_tools: Include tool documentation
        context: Working memory / context section

    Returns:
        Complete system prompt string
    """
    if not with_tools:
        # Simple prompt without tools
        return SIMPLE_PROMPT.format(context=context)

    # Full prompt with tools
    # ADR-144: CONTEXT_AWARENESS always included — TP uses working memory
    # context_readiness signals to judge what guidance to offer.
    sections = [
        BASE_PROMPT,
        BEHAVIORS_SECTION,
        TOOLS_SECTION,
        PLATFORMS_SECTION,
        CONTEXT_AWARENESS,
    ]

    prompt = "\n\n".join(sections)
    prompt = prompt.replace("{context}", context)

    return prompt
