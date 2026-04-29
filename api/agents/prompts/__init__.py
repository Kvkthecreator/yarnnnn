from __future__ import annotations
"""
YARNNN Prompt Modules (ADR-059 + ADR-186 + ADR-189 + ADR-233 Phase 1).

ADR-059: Prompts are split into composable sections.
ADR-186: Two chat prompt profiles — workspace (full scope) and entity (scoped).
ADR-189: Directory renamed tp_prompts/ → yarnnn_prompts/.
ADR-233: Directory renamed yarnnn_prompts/ → prompts/ with chat/ + headless/
         subdirectories. Profile axis extended from 2 chat profiles to 5
         unified profiles. Single resolver `build_prompt(profile_key, ...)`.

Profile keys (5 total):
  chat/workspace        — onboarding, task catalog, team composition, creation
  chat/entity           — feedback routing, evaluation, agent identity management
  headless/deliverable  — recurring report composition (replacive, gap-filling)
  headless/accumulation — entity tracking + domain synthesis (additive)
  headless/action       — action proposal (propose, do not execute)

MAINTENANCE shape has no LLM call, no profile.

Chat shared sections:
  base.py       — chat identity + tone
  tools_core.py — primitive docs, domain terms, workforce model
  platforms.py  — platform tools

Chat profile-specific sections (under chat/):
  workspace.py  — onboarding, task catalog, team composition, creation routes
  entity.py     — feedback routing, evaluation, agent identity management
  activation.py — ADR-226 activation overlay
  onboarding.py — CONTEXT_AWARENESS for workspace profile

Headless sections (under headless/):
  base.py         — HEADLESS_BASE_BLOCK (output rules, conventions, accumulation-first)
  deliverable.py  — DELIVERABLE_POSTURE
  accumulation.py — ACCUMULATION_POSTURE
  action.py       — ACTION_POSTURE
"""

from .base import BASE_PROMPT, SIMPLE_PROMPT
from .tools_core import TOOLS_CORE
from .platforms import PLATFORMS_SECTION
from .chat.workspace import WORKSPACE_BEHAVIORS
from .chat.entity import ENTITY_BEHAVIORS

# Legacy imports — kept for any callers that reference them directly.
# onboarding.py still defines CONTEXT_AWARENESS for the workspace profile.
from .chat.onboarding import CONTEXT_AWARENESS

# ADR-226: activation overlay — appended to workspace profile when the
# workspace has been forked from a program bundle but MANDATE.md is still
# skeleton (operator hasn't authored their edge yet).
from .chat.activation import ACTIVATION_OVERLAY

# ADR-233 Phase 1: headless shape postures + universal base block.
from .headless.base import HEADLESS_BASE_BLOCK
from .headless.deliverable import DELIVERABLE_POSTURE
from .headless.accumulation import ACCUMULATION_POSTURE
from .headless.action import ACTION_POSTURE


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


# ---------------------------------------------------------------------------
# ADR-233 Phase 1 — Unified prompt resolver
# ---------------------------------------------------------------------------

# Map of headless profile keys to their posture string. Posture is a
# cognitive-job framing prepended to the cached HEADLESS_BASE_BLOCK so the LLM
# knows what kind of work it's doing before it reads the universal output rules.
HEADLESS_POSTURES: dict[str, str] = {
    "headless/deliverable": DELIVERABLE_POSTURE,
    "headless/accumulation": ACCUMULATION_POSTURE,
    "headless/action": ACTION_POSTURE,
}


def build_headless_system_block(profile_key: str) -> str:
    """Assemble the headless static system block for a given shape posture.

    ADR-233 Phase 1. The static block is the cached half of the headless
    prompt: shape posture (~150 words framing the cognitive job) + universal
    `HEADLESS_BASE_BLOCK` (output rules, conventions, accumulation-first,
    tool usage, visual assets, empty-context handling).

    The caller (`dispatch_helpers.build_task_execution_prompt`) is responsible
    for assembling the dynamic half (per-task context, deliverable spec,
    feedback, etc.) and applying the cache_control marker.

    Args:
        profile_key: One of "headless/deliverable", "headless/accumulation",
                     "headless/action".

    Returns:
        The static system block as a single string.
    """
    if profile_key not in HEADLESS_POSTURES:
        raise ValueError(
            f"Unknown headless profile key: {profile_key!r}. "
            f"Expected one of: {sorted(HEADLESS_POSTURES.keys())}"
        )
    posture = HEADLESS_POSTURES[profile_key]
    return f"{posture}\n\n{HEADLESS_BASE_BLOCK}"


# Public registry of valid profile keys. Imported by tests as the source of
# truth for what profiles exist.
PROFILE_KEYS: tuple[str, ...] = (
    "chat/workspace",
    "chat/entity",
    "headless/deliverable",
    "headless/accumulation",
    "headless/action",
)


def build_prompt(profile_key: str, **kwargs):
    """Unified prompt assembler dispatching on profile key.

    ADR-233 Phase 1: single entry point for every profile in the system.
    Chat profiles return a list of content blocks (cached + dynamic) for the
    Anthropic system parameter. Headless profiles return a single string —
    the caller wraps it in a content block with its own dynamic content
    (per-task context, deliverable spec, feedback) and applies cache_control.

    Args:
        profile_key: One of PROFILE_KEYS.
        **kwargs: Profile-specific arguments. For chat profiles: forwarded to
                  `build_system_prompt`. For headless profiles: ignored
                  (posture is static; dynamic content is the caller's job).

    Returns:
        For chat profiles: list of content blocks.
        For headless profiles: static system block as string.
    """
    if profile_key == "chat/workspace":
        return build_system_prompt(profile="workspace", **kwargs)
    if profile_key == "chat/entity":
        return build_system_prompt(profile="entity", **kwargs)
    if profile_key.startswith("headless/"):
        return build_headless_system_block(profile_key)
    raise ValueError(
        f"Unknown profile key: {profile_key!r}. Expected one of: {list(PROFILE_KEYS)}"
    )
