"""
Skills System (ADR-025 Claude Code Alignment)

Skills are packaged workflows triggered by slash commands or intent recognition.
Each skill expands to a system prompt addition that guides TP through a structured process.

Streamlined to use primitives (Read, Write, Edit, List, Search, Execute, Todo, Clarify).
"""

import logging
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Skill Definitions - Using Primitives Only
# =============================================================================

SKILLS: Dict[str, Dict[str, Any]] = {
    # =========================================================================
    # Generic Creation Skill
    # =========================================================================
    "create": {
        "name": "create",
        "description": "Create a new deliverable or memory",
        "trigger_patterns": ["/create"],
        "system_prompt_addition": """
---

## Active Skill: Create

User wants to create something. Ask what type with Clarify:

```
Clarify(
  question="What would you like to create?",
  options=["Deliverable (recurring report)", "Memory (save a fact)"]
)
```

**If deliverable:** Ask for type, frequency, recipient, then confirm and create.
**If memory:** Ask what to remember, then create.

Keep it simple - one question at a time.
""",
    },

    # =========================================================================
    # Deliverable Type Skills (ADR-093: 7 purpose-first types)
    # =========================================================================
    "status": {
        "name": "status",
        "description": "Create a work summary deliverable — synthesize activity across platforms",
        "trigger_patterns": ["work summary", "status report", "status update", "weekly report", "progress report", "board update", "stakeholder update", "investor update", "create a status", "create status deliverable", "summarize my work", "platform summary"],
        "deliverable_type": "status",
        "system_prompt_addition": """
---

## Active Skill: Work Summary

Create a work summary deliverable — synthesizes activity across the user's connected platforms into a structured report for a specific audience.

**Flow:**
1. Check for duplicates: `List(pattern="deliverable:*")`
2. If missing recipient, ask: `Clarify(question="Who receives this?", options=["Manager", "Team", "Stakeholders", "Board"])`
3. Ask frequency preference: `Clarify(question="How often?", options=["Daily", "Weekly", "Biweekly", "Monthly"])`
4. Confirm: "I'll create a [frequency] Work Summary for [recipient]. Ready?"
5. On confirmation: `Write(ref="deliverable:new", content={title, deliverable_type: "status", frequency, recipient_name})`
6. Offer first draft

**Defaults:** frequency=weekly, type=status
""",
    },

    "digest": {
        "name": "digest",
        "description": "Create a platform recap — catch up on everything across a connected platform",
        "trigger_patterns": ["recap", "platform recap", "slack recap", "gmail recap", "notion recap", "email recap", "slack digest", "email digest", "notion summary", "weekly digest", "daily recap", "catch up", "create a recap", "create recap deliverable", "create a digest", "create digest deliverable"],
        "deliverable_type": "digest",
        "system_prompt_addition": """
---

## Active Skill: Recap

Create a recap deliverable — a platform-wide summary that catches the user up on everything across a connected platform. One recap per platform (not per channel/label/page).

**Flow:**
1. Check for duplicates: `List(pattern="deliverable:*")` — if a recap already exists for the requested platform, offer to edit it instead
2. Ask platform: `Clarify(question="Which platform do you want to recap?", options=["Slack", "Gmail", "Notion", "Calendar"])`
3. Ask frequency: `Clarify(question="How often?", options=["Daily", "Weekly"])`
4. Confirm: "I'll create a [frequency] [Platform] Recap. Ready?"
5. On confirmation: `Write(ref="deliverable:new", content={title: "[Platform] Recap", deliverable_type: "digest", frequency, primary_platform})` — sources auto-populated with ALL synced sources for that platform
6. Offer first draft

**Important:**
- Title format: "[Platform] Recap" (e.g., "Slack Recap", "Gmail Recap")
- Sources: ALL synced sources for the selected platform — do NOT ask the user to pick individual channels/labels/pages
- One recap per platform per user — check duplicates before creating
- Defaults: frequency=daily, type=digest
""",
    },

    "brief": {
        "name": "brief",
        "description": "Set up auto meeting prep — every morning, reads your calendar and preps you for the day's meetings",
        "trigger_patterns": ["meeting prep", "auto meeting prep", "calendar prep", "daily briefing", "brief", "meeting brief", "event prep", "call prep", "1:1 prep"],
        "deliverable_type": "brief",
        "system_prompt_addition": """
---

## Active Skill: Auto Meeting Prep

Set up daily auto meeting prep — every morning, YARNNN reads the user's Google Calendar and sends a prep briefing with context from Slack, Gmail, and Notion for each meeting ahead.

**Requirements:**
- Google Calendar must be connected. If not, guide the user to connect it first.
- One auto meeting prep per user — if one already exists, explain and offer to update it.

**Flow:**
1. Check for duplicates: `List(pattern="deliverable:*")` — look for existing brief type
2. Verify Google Calendar connection: `List(pattern="connection:*")` — check for google/calendar
3. If no calendar: "Auto Meeting Prep requires Google Calendar. Let's connect it first." → guide to connections
4. Ask delivery time: `Clarify(question="What time should your meeting prep arrive?", options=["7:00 AM", "8:00 AM", "9:00 AM"])`
5. Confirm: "I'll set up Auto Meeting Prep — every morning at [time], you'll get a briefing for the day's meetings. Ready?"
6. On confirmation: `Write(ref="deliverable:new", content={title: "Auto Meeting Prep", deliverable_type: "brief", frequency: "daily", sources: [all calendar + all connected platform sources]})`

**Important:**
- Title: "Auto Meeting Prep" (fixed — not user-customizable)
- Sources: ALL calendar sources + ALL other connected platform sources (Slack, Gmail, Notion) for cross-platform context about attendees and topics
- One per user — check duplicates before creating
- Defaults: frequency=daily, type=brief
""",
    },

    "deep-research": {
        "name": "deep-research",
        "description": "Set up Proactive Insights — watches your platforms and surfaces what matters",
        "trigger_patterns": ["proactive insights", "insights", "deep research", "watch my platforms", "surface insights", "what should I know", "investigate", "research this", "look into", "find out about"],
        "deliverable_type": "deep_research",
        "system_prompt_addition": """
---

## Active Skill: Proactive Insights

Set up Proactive Insights — YARNNN watches the user's connected platforms for emerging themes, researches them externally, and delivers intelligence the user didn't ask for.

**Flow:**
1. Check for duplicates: `List(pattern="deliverable:*")` — one per user
2. If duplicate exists, tell the user they already have Proactive Insights set up and offer to open it
3. Confirm: "I'll scan your connected platforms regularly and surface emerging themes with external context. Would you like a daily or weekly pulse?"
4. Ask frequency: `Clarify(question="How often should I check for insights?", options=["Weekly (recommended)", "Daily"])`
5. On confirmation: `Write(ref="deliverable:new", content={title: "Proactive Insights", deliverable_type: "deep_research", mode: "proactive"})`
- Sources: ALL connected platform sources (Slack, Gmail, Notion, Calendar) — for cross-platform signal detection
- One per user — check duplicates before creating
- Defaults: mode=proactive, type=deep_research
- Do NOT ask for a research topic — topic selection is autonomous from platform signals
""",
    },

    # NOTE: watch, custom, coordinator skills hidden pre-launch (2026-03-06).
    # Type keys and backend strategies remain — only UI creation paths removed.
    # Restore when: watch needs real-time infra; custom needs product validation;
    # coordinator needs power-user adoption.
}


# =============================================================================
# Skill Detection & Expansion
# =============================================================================

def detect_skill(user_message: str) -> Optional[str]:
    """
    Detect if user message triggers a skill.

    Returns skill name if detected, None otherwise.

    Detection methods:
    1. Explicit slash command: /board-update, /create
    2. Pattern matching: "board update", "investor update"
    """
    message_lower = user_message.lower().strip()

    # Check for explicit slash command
    if message_lower.startswith("/"):
        # Extract command: "/board-update foo bar" -> "board-update"
        command = message_lower[1:].split()[0] if len(message_lower) > 1 else ""
        if command in SKILLS:
            return command

    # Check trigger patterns (only if no slash command)
    for skill_name, skill_def in SKILLS.items():
        for pattern in skill_def.get("trigger_patterns", []):
            if pattern in message_lower:
                return skill_name

    return None


def get_skill_prompt_addition(skill_name: str) -> Optional[str]:
    """Get the system prompt addition for a skill."""
    skill = SKILLS.get(skill_name)
    if skill:
        return skill.get("system_prompt_addition", "")
    return None


def get_skill_info(skill_name: str) -> Optional[Dict[str, Any]]:
    """Get full skill definition."""
    return SKILLS.get(skill_name)


def list_available_skills() -> list[Dict[str, str]]:
    """List all available skills with their descriptions."""
    return [
        {
            "name": skill["name"],
            "description": skill["description"],
            "command": f"/{skill['name']}",
        }
        for skill in SKILLS.values()
    ]


# =============================================================================
# Hybrid Detection (ADR-040)
# =============================================================================

async def detect_skill_hybrid(user_message: str) -> Tuple[Optional[str], str, float]:
    """
    Hybrid skill detection: pattern matching first, semantic fallback.

    Args:
        user_message: The user's message to analyze

    Returns:
        Tuple of (skill_name, detection_method, confidence)
        - skill_name: The detected skill, or None
        - detection_method: "pattern" | "semantic" | "none"
        - confidence: 1.0 for pattern matches, 0.0-1.0 for semantic
    """
    # Fast path: pattern matching (existing behavior)
    pattern_match = detect_skill(user_message)
    if pattern_match:
        logger.debug(f"Skill detected via pattern: {pattern_match}")
        return (pattern_match, "pattern", 1.0)

    # Fallback: semantic matching
    try:
        from services.skill_embeddings import detect_skill_semantic
        semantic_match, confidence = await detect_skill_semantic(user_message)
        if semantic_match:
            logger.info(f"Skill detected via semantic: {semantic_match} (confidence: {confidence:.3f})")
            return (semantic_match, "semantic", confidence)
    except ImportError:
        # Semantic matching not available
        pass
    except Exception as e:
        # Semantic matching failed (e.g., missing OPENAI_API_KEY) — non-fatal
        logger.debug(f"Semantic skill detection failed: {e}")
        pass

    return (None, "none", 0.0)
