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
) -> list[dict]:
    """
    Build the full system prompt as content blocks for prompt caching.

    Static sections (identity, tools, behaviors) are cached via cache_control.
    Dynamic sections (working memory context) are NOT cached — they change per turn.

    Args:
        with_tools: Include tool documentation
        context: Working memory / context section

    Returns:
        List of content blocks for the Anthropic system parameter
    """
    if not with_tools:
        # Simple prompt without tools — all dynamic (contains context)
        return [{"type": "text", "text": SIMPLE_PROMPT.format(context=context)}]

    # Full prompt with tools
    # Static: identity + behaviors + tools + platforms + context awareness
    # These sections are identical across turns within a session (~10K tokens).
    static_sections = [
        BASE_PROMPT,
        BEHAVIORS_SECTION,
        TOOLS_SECTION,
        PLATFORMS_SECTION,
        CONTEXT_AWARENESS,
    ]
    static_prompt = "\n\n".join(sections for sections in static_sections)
    # Remove the {context} placeholder from static — context goes in dynamic block
    static_prompt = static_prompt.replace("{context}", "")

    # Dynamic: working memory context (changes per turn)
    return [
        {
            "type": "text",
            "text": static_prompt,
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": f"\n\n## Working Memory & Context\n{context}" if context else "",
        },
    ]
