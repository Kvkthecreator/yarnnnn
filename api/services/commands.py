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
    # Task Commands (ADR-138/140: Task-centric workflow)
    # =========================================================================
    "task": {
        "name": "task",
        "description": "Create a new task — assign recurring work to an agent",
        "trigger_patterns": ["/task", "create a task", "new task", "assign work", "set up a task"],
        "system_prompt_addition": """
---

## Active Command: Create Task

User wants to create a task (recurring work assigned to an agent).

**Flow:**
1. Ask what they need: `Clarify(question="What work do you need done?", options=["Weekly recap", "Research report", "Content/document", "Platform monitoring"])`
2. Based on choice, pick the right agent from their roster:
   - Research/monitoring/tracking → Research Agent
   - Reports/updates/decks → Content Agent
   - GTM/campaigns → Marketing Agent
   - Relationships/follow-ups → CRM Agent
   - Slack automation → Slack Bot
   - Notion automation → Notion Bot
3. Ask schedule: `Clarify(question="How often?", options=["Daily", "Weekly", "Monthly", "One-time"])`
4. Ask delivery if relevant: email, Slack, download
5. Confirm and create with `CreateTask(title=..., agent_slug=..., schedule=..., delivery=...)`

Keep it simple — one question at a time. The agent already exists in their roster.
""",
    },

    "recap": {
        "name": "recap",
        "description": "Set up a platform recap — daily or weekly catch-up from Slack or Notion",
        "trigger_patterns": ["recap", "platform recap", "slack recap", "notion recap", "slack digest", "notion summary", "weekly digest", "daily recap", "catch up", "create a recap", "digest"],
        "system_prompt_addition": """
---

## Active Command: Recap

Create a recurring recap task assigned to the Research Agent (or Slack/Notion Bot if platform-specific).

**Flow:**
1. Ask platform: `Clarify(question="Which platform?", options=["Slack", "Notion", "Both"])`
2. Ask frequency: `Clarify(question="How often?", options=["Daily", "Weekly"])`
3. Confirm and create:
   `CreateTask(title="[Platform] Recap", agent_slug="research-agent", schedule=..., objective={deliverable: "Platform recap", audience: "You", purpose: "Stay on top of activity"})`

**Defaults:** frequency=daily, agent=research-agent
""",
    },

    "summary": {
        "name": "summary",
        "description": "Create a work summary — synthesize activity into a report",
        "trigger_patterns": ["work summary", "status report", "status update", "weekly report", "progress report", "board update", "stakeholder update", "investor update", "summarize my work"],
        "system_prompt_addition": """
---

## Active Command: Work Summary

Create a recurring summary task assigned to the Content Agent.

**Flow:**
1. Ask audience: `Clarify(question="Who is this for?", options=["Manager", "Team", "Board", "Investors"])`
2. Ask frequency: `Clarify(question="How often?", options=["Weekly", "Biweekly", "Monthly"])`
3. Confirm and create:
   `CreateTask(title="[Frequency] [Audience] Summary", agent_slug="content-agent", schedule=..., objective={deliverable: "Work summary", audience: ..., format: "Document"})`

**Defaults:** frequency=weekly, agent=content-agent
""",
    },

    "research": {
        "name": "research",
        "description": "Set up research tracking — monitors topics and surfaces insights",
        "trigger_patterns": ["proactive insights", "insights", "deep research", "watch my platforms", "surface insights", "investigate", "research this", "look into", "find out about", "track competitors", "competitive intel"],
        "system_prompt_addition": """
---

## Active Command: Research

Create a research task assigned to the Research Agent.

**Flow:**
1. Ask what to research: "What topic or domain should I track?"
2. Ask frequency: `Clarify(question="How often?", options=["Weekly (recommended)", "Daily", "Monthly"])`
3. Confirm and create:
   `CreateTask(title="[Topic] Research", agent_slug="research-agent", schedule=..., objective={deliverable: "Research report", purpose: "Track and analyze [topic]"})`

**Defaults:** frequency=weekly, agent=research-agent
""",
    },

    # =========================================================================
    # Agent Management (secondary — roster usually covers needs)
    # =========================================================================
    "create": {
        "name": "create",
        "description": "Create a new agent (most users don't need this — your team is pre-built)",
        "trigger_patterns": ["/create", "create agent", "new agent"],
        "system_prompt_addition": """
---

## Active Command: Create Agent

User wants to create a new agent. Most users already have a full roster (6 agents).
Check their roster first — they probably just need a task on an existing agent.

1. Check roster: `List(pattern="agent:*")`
2. If all 6 exist, suggest creating a task instead: "You already have a full team. Want me to assign a task to one of them?"
3. If they insist on a new agent: `Clarify(question="What type?", options=["Research", "Content", "Marketing", "CRM"])`
4. Create: `CreateAgent(title=..., role=...)`
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
