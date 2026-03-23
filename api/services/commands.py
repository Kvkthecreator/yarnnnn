"""
Slash Commands System (ADR-025 Claude Code Alignment)

Commands are packaged workflows triggered by slash commands or intent recognition.
Each command expands to a system prompt addition that guides TP through a structured process.

Two categories:
1. Agent creation commands — structured flows to create recurring agents
2. Capability commands — surface TP's built-in abilities (search, sync, memory, web research)
"""

import logging
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Command Definitions
# =============================================================================

COMMANDS: Dict[str, Dict[str, Any]] = {
    # =========================================================================
    # Agent Creation Commands (ADR-109: Scope × Skill × Trigger)
    # =========================================================================
    "create": {
        "name": "create",
        "description": "Create a new recurring agent",
        "trigger_patterns": ["/create"],
        "system_prompt_addition": """
---

## Active Command: Create Agent

User wants to create an agent. Guide them through setup:

1. Ask what kind: `Clarify(question="What should this agent do?", options=["Platform recap", "Work summary", "Research & insights"])`
2. Based on choice, ask platform/frequency/recipient as needed
3. Confirm and create with `CreateAgent(...)`

Keep it simple — one question at a time.
""",
    },

    "summary": {
        "name": "summary",
        "description": "Create a work summary agent — synthesize activity across platforms",
        "trigger_patterns": ["work summary", "status report", "status update", "weekly report", "progress report", "board update", "stakeholder update", "investor update", "create a status", "create status agent", "summarize my work", "platform summary"],
        "role": "analyst",
        "system_prompt_addition": """
---

## Active Command: Work Summary

Create a work summary agent — analyzes activity across the user's connected platforms into a structured report for a specific audience.

**Flow:**
1. Check for duplicates: `List(pattern="agent:*")`
2. If missing recipient, ask: `Clarify(question="Who receives this?", options=["Manager", "Team", "Stakeholders", "Board"])`
3. Ask frequency preference: `Clarify(question="How often?", options=["Daily", "Weekly", "Biweekly", "Monthly"])`
4. Confirm: "I'll create a [frequency] Work Summary for [recipient]. Ready?"
5. On confirmation: `CreateAgent(title="Work Summary", role="analyst", frequency=..., recipient_name=...)`
6. Offer first draft

**Defaults:** frequency=weekly, role=analyst
""",
    },

    "recap": {
        "name": "recap",
        "description": "Create a platform recap — catch up on everything across a connected platform",
        "trigger_patterns": ["recap", "platform recap", "slack recap", "notion recap", "slack digest", "notion summary", "weekly digest", "daily recap", "catch up", "create a recap", "create recap agent", "create a digest", "create digest agent", "digest"],
        "role": "briefer",
        "system_prompt_addition": """
---

## Active Command: Recap

Create a briefer agent — a platform-wide summary that catches the user up on everything across a connected platform. One briefer per platform (not per channel/label/page).

**Flow:**
1. Check for duplicates: `List(pattern="agent:*")` — if a briefer already exists for the requested platform, offer to edit it instead
2. Ask platform: `Clarify(question="Which platform do you want to recap?", options=["Slack", "Notion"])`
3. Ask frequency: `Clarify(question="How often?", options=["Daily", "Weekly"])`
4. Confirm: "I'll create a [frequency] [Platform] Recap project. Ready?"
5. On confirmation: `CreateAgent(title="[Platform] Briefer", role="briefer", frequency=..., sources=[all synced sources for platform])`
6. Offer first draft

**Important:**
- Agent title format: "[Platform] Briefer" (e.g., "Slack Briefer", "Notion Briefer")
- Sources: ALL synced sources for the selected platform — do NOT ask the user to pick individual channels/pages
- One briefer per platform per user — check duplicates before creating
- Defaults: frequency=daily, role=briefer
""",
    },

    # ADR-131: "prep" command deleted (Calendar sunset — no meeting prep without calendar data)

    "research": {
        "name": "research",
        "description": "Set up Proactive Insights — watches your platforms and surfaces what matters",
        "trigger_patterns": ["proactive insights", "insights", "deep research", "watch my platforms", "surface insights", "what should I know", "investigate", "research this", "look into", "find out about"],
        "role": "analyst",
        "system_prompt_addition": """
---

## Active Command: Proactive Insights

Set up Proactive Insights — YARNNN watches the user's connected platforms for emerging themes, researches them externally, and delivers intelligence the user didn't ask for.

**Flow:**
1. Check for duplicates: `List(pattern="agent:*")` — one per user
2. If duplicate exists, tell the user they already have Proactive Insights set up and offer to open it
3. Confirm: "I'll scan your connected platforms regularly and surface emerging themes with external context. Would you like a daily or weekly pulse?"
4. Ask frequency: `Clarify(question="How often should I check for insights?", options=["Weekly (recommended)", "Daily"])`
5. On confirmation: `CreateAgent(title="Proactive Insights", role="synthesize", mode="proactive")`
- Sources: ALL connected platform sources (Slack, Notion) — for cross-platform signal detection
- One per user — check duplicates before creating
- Defaults: mode=proactive, role=synthesize, scope=autonomous
- Do NOT ask for a research topic — topic selection is autonomous from platform signals
""",
    },

    # =========================================================================
    # Capability Commands — surface TP's built-in abilities
    # =========================================================================
    "search": {
        "name": "search",
        "description": "Search across your connected platforms (Slack, Notion)",
        "trigger_patterns": ["search my platforms", "find in slack", "find in notion", "search for", "look up"],
        "system_prompt_addition": """
---

## Active Command: Platform Search

User wants to search their connected platform data.

Use `Search(query="...", scope="platform_content")` to find relevant content. If results seem stale, use `RefreshPlatformContent(platform="...")` first, then search again.

Ask the user what they're looking for if not clear from context. You can filter by platform: `Search(query="...", scope="platform_content", platform="slack")`.
""",
    },

    "sync": {
        "name": "sync",
        "description": "Refresh platform data — pull latest from Slack or Notion",
        "trigger_patterns": ["sync my", "refresh my", "update my", "pull latest", "resync"],
        "system_prompt_addition": """
---

## Active Command: Platform Sync

User wants fresh data from their platforms.

Use `RefreshPlatformContent(platform="...")` to pull the latest. If user doesn't specify a platform, check which are connected with `list_integrations()` and ask which to refresh, or refresh all.

Report back what was synced and how many items were updated.
""",
    },

    "memory": {
        "name": "memory",
        "description": "Save a preference, fact, or instruction to your memory",
        "trigger_patterns": ["remember that", "save to memory", "note that", "keep in mind"],
        "system_prompt_addition": """
---

## Active Command: Save Memory

User wants to save something to their persistent memory.

Use `SaveMemory(content="...", entry_type="...")` where entry_type is one of: fact, preference, instruction.

If the user's intent is clear, save immediately and confirm. If ambiguous, ask what they'd like to remember.
""",
    },

    "web": {
        "name": "web",
        "description": "Search the web for current information, news, or research",
        "trigger_patterns": ["search the web", "web search", "google", "look up online", "what's happening with", "latest news"],
        "system_prompt_addition": """
---

## Active Command: Web Search

User wants information from the web (not their own platforms).

Use `WebSearch(query="...", context="...", max_results=5)` to find current information. Summarize findings concisely.

Good for: current events, competitor research, technical docs, industry trends.
""",
    },
}


# =============================================================================
# Command Detection & Expansion
# =============================================================================

def detect_command(user_message: str) -> Optional[str]:
    """
    Detect if user message triggers a command.

    Returns command name if detected, None otherwise.

    Detection methods:
    1. Explicit slash command: /recap, /summary, /search
    2. Pattern matching: "slack recap", "work summary", "search my platforms"
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
        if semantic_match and semantic_match in COMMANDS:
            logger.info(f"Command detected via semantic: {semantic_match} (confidence: {confidence:.3f})")
            return (semantic_match, "semantic", confidence)
        elif semantic_match:
            logger.warning(f"Semantic match '{semantic_match}' not in COMMANDS — skipping")
    except ImportError:
        # Semantic matching not available
        pass
    except Exception as e:
        # Semantic matching failed (e.g., missing OPENAI_API_KEY) — non-fatal
        logger.debug(f"Semantic command detection failed: {e}")
        pass

    return (None, "none", 0.0)
