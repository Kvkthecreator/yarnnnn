"""
Slash Commands System (ADR-025 Claude Code Alignment)

Commands are packaged workflows triggered by slash commands or intent recognition.
Each command expands to a system prompt addition that guides TP through a structured process.

Streamlined to use primitives (Read, Write, Edit, List, Search, Execute, Todo, Clarify).
"""

import logging
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Command Definitions - Using Primitives Only
# =============================================================================

COMMANDS: Dict[str, Dict[str, Any]] = {
    # =========================================================================
    # Generic Creation Command
    # =========================================================================
    "create": {
        "name": "create",
        "description": "Create a new agent or memory",
        "trigger_patterns": ["/create"],
        "system_prompt_addition": """
---

## Active Command: Create

User wants to create something. Ask what type with Clarify:

```
Clarify(
  question="What would you like to create?",
  options=["Agent (recurring report)", "Memory (save a fact)"]
)
```

**If agent:** Ask for type, frequency, recipient, then confirm and create.
**If memory:** Ask what to remember, then create.

Keep it simple - one question at a time.
""",
    },

    # =========================================================================
    # Agent Commands (ADR-109: Scope × Skill × Trigger)
    # =========================================================================
    "status": {
        "name": "status",
        "description": "Create a work summary agent — synthesize activity across platforms",
        "trigger_patterns": ["work summary", "status report", "status update", "weekly report", "progress report", "board update", "stakeholder update", "investor update", "create a status", "create status agent", "summarize my work", "platform summary"],
        "skill": "synthesize",
        "system_prompt_addition": """
---

## Active Command: Work Summary

Create a work summary agent — synthesizes activity across the user's connected platforms into a structured report for a specific audience.

**Flow:**
1. Check for duplicates: `List(pattern="agent:*")`
2. If missing recipient, ask: `Clarify(question="Who receives this?", options=["Manager", "Team", "Stakeholders", "Board"])`
3. Ask frequency preference: `Clarify(question="How often?", options=["Daily", "Weekly", "Biweekly", "Monthly"])`
4. Confirm: "I'll create a [frequency] Work Summary for [recipient]. Ready?"
5. On confirmation: `Write(ref="agent:new", content={title, skill: "synthesize", frequency, recipient_name})`
6. Offer first draft

**Defaults:** frequency=weekly, skill=synthesize
""",
    },

    "digest": {
        "name": "digest",
        "description": "Create a platform recap — catch up on everything across a connected platform",
        "trigger_patterns": ["recap", "platform recap", "slack recap", "gmail recap", "notion recap", "email recap", "slack digest", "email digest", "notion summary", "weekly digest", "daily recap", "catch up", "create a recap", "create recap agent", "create a digest", "create digest agent"],
        "skill": "digest",
        "system_prompt_addition": """
---

## Active Command: Recap

Create a recap agent — a platform-wide summary that catches the user up on everything across a connected platform. One recap per platform (not per channel/label/page).

**Flow:**
1. Check for duplicates: `List(pattern="agent:*")` — if a recap already exists for the requested platform, offer to edit it instead
2. Ask platform: `Clarify(question="Which platform do you want to recap?", options=["Slack", "Gmail", "Notion", "Calendar"])`
3. Ask frequency: `Clarify(question="How often?", options=["Daily", "Weekly"])`
4. Confirm: "I'll create a [frequency] [Platform] Recap. Ready?"
5. On confirmation: `Write(ref="agent:new", content={title: "[Platform] Recap", skill: "digest", frequency, primary_platform})` — sources auto-populated with ALL synced sources for that platform
6. Offer first draft

**Important:**
- Title format: "[Platform] Recap" (e.g., "Slack Recap", "Gmail Recap")
- Sources: ALL synced sources for the selected platform — do NOT ask the user to pick individual channels/labels/pages
- One recap per platform per user — check duplicates before creating
- Defaults: frequency=daily, skill=digest
""",
    },

    "brief": {
        "name": "brief",
        "description": "Set up auto meeting prep — every morning, reads your calendar and preps you for the day's meetings",
        "trigger_patterns": ["meeting prep", "auto meeting prep", "calendar prep", "daily briefing", "brief", "meeting brief", "event prep", "call prep", "1:1 prep"],
        "skill": "prepare",
        "system_prompt_addition": """
---

## Active Command: Auto Meeting Prep

Set up daily auto meeting prep — every morning, YARNNN reads the user's Google Calendar and sends a prep briefing with context from Slack, Gmail, and Notion for each meeting ahead.

**Requirements:**
- Google Calendar must be connected. If not, guide the user to connect it first.
- One auto meeting prep per user — if one already exists, explain and offer to update it.

**Flow:**
1. Check for duplicates: `List(pattern="agent:*")` — look for existing prepare skill
2. Verify Google Calendar connection: `List(pattern="connection:*")` — check for google/calendar
3. If no calendar: "Auto Meeting Prep requires Google Calendar. Let's connect it first." → guide to connections
4. Ask delivery time: `Clarify(question="What time should your meeting prep arrive?", options=["7:00 AM", "8:00 AM", "9:00 AM"])`
5. Confirm: "I'll set up Auto Meeting Prep — every morning at [time], you'll get a briefing for the day's meetings. Ready?"
6. On confirmation: `Write(ref="agent:new", content={title: "Auto Meeting Prep", skill: "prepare", frequency: "daily", sources: [all calendar + all connected platform sources]})`

**Important:**
- Title: "Auto Meeting Prep" (fixed — not user-customizable)
- Sources: ALL calendar sources + ALL other connected platform sources (Slack, Gmail, Notion) for cross-platform context about attendees and topics
- One per user — check duplicates before creating
- Defaults: frequency=daily, skill=prepare
""",
    },

    "deep-research": {
        "name": "deep-research",
        "description": "Set up Proactive Insights — watches your platforms and surfaces what matters",
        "trigger_patterns": ["proactive insights", "insights", "deep research", "watch my platforms", "surface insights", "what should I know", "investigate", "research this", "look into", "find out about"],
        "skill": "synthesize",
        "system_prompt_addition": """
---

## Active Command: Proactive Insights

Set up Proactive Insights — YARNNN watches the user's connected platforms for emerging themes, researches them externally, and delivers intelligence the user didn't ask for.

**Flow:**
1. Check for duplicates: `List(pattern="agent:*")` — one per user
2. If duplicate exists, tell the user they already have Proactive Insights set up and offer to open it
3. Confirm: "I'll scan your connected platforms regularly and surface emerging themes with external context. Would you like a daily or weekly pulse?"
4. Ask frequency: `Clarify(question="How often should I check for insights?", options=["Weekly (recommended)", "Daily"])`
5. On confirmation: `Write(ref="agent:new", content={title: "Proactive Insights", skill: "synthesize", mode: "proactive"})`
- Sources: ALL connected platform sources (Slack, Gmail, Notion, Calendar) — for cross-platform signal detection
- One per user — check duplicates before creating
- Defaults: mode=proactive, skill=synthesize, scope=autonomous
- Do NOT ask for a research topic — topic selection is autonomous from platform signals
""",
    },

    # NOTE: monitor, custom, orchestrate commands hidden pre-launch (2026-03-06).
    # Command keys and backend strategies remain — only UI creation paths removed.
    # Restore when: monitor needs real-time infra; custom needs product validation;
    # orchestrate needs power-user adoption.
}


# =============================================================================
# Command Detection & Expansion
# =============================================================================

def detect_command(user_message: str) -> Optional[str]:
    """
    Detect if user message triggers a command.

    Returns command name if detected, None otherwise.

    Detection methods:
    1. Explicit slash command: /board-update, /create
    2. Pattern matching: "board update", "investor update"
    """
    message_lower = user_message.lower().strip()

    # Check for explicit slash command
    if message_lower.startswith("/"):
        # Extract command: "/board-update foo bar" -> "board-update"
        command = message_lower[1:].split()[0] if len(message_lower) > 1 else ""
        if command in COMMANDS:
            return command

    # Check trigger patterns (only if no slash command)
    for cmd_name, cmd_def in COMMANDS.items():
        for pattern in cmd_def.get("trigger_patterns", []):
            if pattern in message_lower:
                return cmd_name

    return None


def get_command_prompt_addition(command_name: str) -> Optional[str]:
    """Get the system prompt addition for a command."""
    cmd = COMMANDS.get(command_name)
    if cmd:
        return cmd.get("system_prompt_addition", "")
    return None


def get_command_info(command_name: str) -> Optional[Dict[str, Any]]:
    """Get full command definition."""
    return COMMANDS.get(command_name)


def list_available_commands() -> list[Dict[str, str]]:
    """List all available commands with their descriptions."""
    return [
        {
            "name": cmd["name"],
            "description": cmd["description"],
            "command": f"/{cmd['name']}",
        }
        for cmd in COMMANDS.values()
    ]


# =============================================================================
# Hybrid Detection (ADR-040)
# =============================================================================

async def detect_command_hybrid(user_message: str) -> Tuple[Optional[str], str, float]:
    """
    Hybrid command detection: pattern matching first, semantic fallback.

    Args:
        user_message: The user's message to analyze

    Returns:
        Tuple of (command_name, detection_method, confidence)
        - command_name: The detected command, or None
        - detection_method: "pattern" | "semantic" | "none"
        - confidence: 1.0 for pattern matches, 0.0-1.0 for semantic
    """
    # Fast path: pattern matching (existing behavior)
    pattern_match = detect_command(user_message)
    if pattern_match:
        logger.debug(f"Command detected via pattern: {pattern_match}")
        return (pattern_match, "pattern", 1.0)

    # Fallback: semantic matching
    try:
        from services.command_embeddings import detect_command_semantic
        semantic_match, confidence = await detect_command_semantic(user_message)
        if semantic_match:
            logger.info(f"Command detected via semantic: {semantic_match} (confidence: {confidence:.3f})")
            return (semantic_match, "semantic", confidence)
    except ImportError:
        # Semantic matching not available
        pass
    except Exception as e:
        # Semantic matching failed (e.g., missing OPENAI_API_KEY) — non-fatal
        logger.debug(f"Semantic command detection failed: {e}")
        pass

    return (None, "none", 0.0)
