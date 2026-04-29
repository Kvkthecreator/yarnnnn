from __future__ import annotations
"""
YARNNN Prompt Modules (ADR-059 + ADR-186 + ADR-189)

ADR-059: Prompts are split into composable sections.
ADR-186: Two prompt profiles — workspace (full scope) and entity (scoped).
ADR-189: Directory renamed tp_prompts/ → yarnnn_prompts/. User-facing "TP"
         retired in favor of "YARNNN" throughout prompt contents.

Profile-aware assembly:
  build_system_prompt(profile="workspace", ...)  → onboarding, task catalog, creation
  build_system_prompt(profile="entity", ...)     → feedback routing, evaluate/steer/complete

Shared sections (both profiles):
  base.py       — identity + tone
  tools_core.py — primitive docs, domain terms, workforce model
  platforms.py  — platform tools

Profile-specific sections:
  workspace.py  — onboarding, task catalog, team composition, creation routes
  entity.py     — feedback routing, evaluation, agent identity management
"""

from .base import BASE_PROMPT, SIMPLE_PROMPT
from .tools_core import TOOLS_CORE
from .platforms import PLATFORMS_SECTION
from .workspace import WORKSPACE_BEHAVIORS
from .entity import ENTITY_BEHAVIORS

# Legacy imports — kept for any callers that reference them directly.
# onboarding.py still defines CONTEXT_AWARENESS for the workspace profile.
from .onboarding import CONTEXT_AWARENESS

# ADR-226: activation overlay — appended to workspace profile when the
# workspace has been forked from a program bundle but MANDATE.md is still
# skeleton (operator hasn't authored their edge yet).
from .activation import ACTIVATION_OVERLAY


def build_system_prompt(
    *,
    with_tools: bool = False,
    context: str = "",
    profile: str = "workspace",
    entity_preamble: str = "",
    activation_active: bool = False,
) -> list[dict]:
    """
    Build the full system prompt as content blocks for prompt caching.

    ADR-186: Profile-aware assembly.
      - profile="workspace": full behavioral guidance (onboarding, creation, catalog)
      - profile="entity": scoped behavioral guidance (feedback, evaluate, steer)

    Static sections (identity, tools, behaviors) are cached via cache_control.
    Dynamic sections (working memory context, entity preamble) are NOT cached.

    Args:
        with_tools: Include tool documentation
        context: Working memory / context section
        profile: "workspace" or "entity" — determines behavioral sections
        entity_preamble: For entity profile — TASK.md, run log, output preview

    Returns:
        List of content blocks for the Anthropic system parameter
    """
    if not with_tools:
        # Simple prompt without tools — all dynamic (contains context)
        return [{"type": "text", "text": SIMPLE_PROMPT.format(context=context)}]

    # Profile-specific behavioral assembly
    if profile == "entity":
        static_sections = [
            BASE_PROMPT,
            ENTITY_BEHAVIORS,
            TOOLS_CORE,
            PLATFORMS_SECTION,
        ]
    else:
        # Default: workspace profile (full guidance)
        static_sections = [
            BASE_PROMPT,
            WORKSPACE_BEHAVIORS,
            TOOLS_CORE,
            PLATFORMS_SECTION,
            CONTEXT_AWARENESS,
        ]
        # ADR-226: when activation is active (workspace forked, MANDATE.md
        # still skeleton), append the differential-authoring overlay so
        # YARNNN walks the operator through the `authored` tier files.
        if activation_active:
            static_sections.append(ACTIVATION_OVERLAY)

    static_prompt = "\n\n".join(section for section in static_sections)
    # Remove the {context} placeholder from static — context goes in dynamic block
    static_prompt = static_prompt.replace("{context}", "")

    # Build dynamic section
    dynamic_parts = []
    if entity_preamble:
        dynamic_parts.append(f"\n\n## Entity Context\n{entity_preamble}")
    if context:
        dynamic_parts.append(f"\n\n## Working Memory & Context\n{context}")
    dynamic_text = "".join(dynamic_parts)

    return [
        {
            "type": "text",
            "text": static_prompt,
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": dynamic_text,
        },
    ]
