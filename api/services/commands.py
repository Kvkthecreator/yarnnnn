"""
Slash Commands System (ADR-025 Claude Code Alignment)

Commands are packaged workflows triggered by slash commands or intent recognition.
Each command expands to a system prompt addition that guides YARNNN through a structured process.

Two categories:
1. Agent creation commands — structured flows to create recurring agents
2. Capability commands — surface YARNNN's built-in abilities (search, sync, memory, web research)
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
        "description": "Create a new task — pick a deliverable type or describe custom work",
        "trigger_patterns": ["/task", "create a task", "new task", "assign work", "set up a task", "I want a", "deliver me", "produce a"],
        "system_prompt_addition": """
---

## Active Command: Create Task (ADR-145: Task Type Registry)

User wants to create a task. Use the task type registry to match their need to a concrete deliverable type.

**Available task types:**
- competitive-intel-brief — Competitive analysis with charts (Research → Content, weekly)
- market-research-report — Deep-dive investigation (Research → Content, monthly)
- industry-signal-monitor — Industry scan + deep-dives (Marketing → Research, weekly)
- due-diligence-summary — Company/opportunity investigation (Research → Content, on-demand)
- meeting-prep-brief — Relationship context + external research (CRM → Research, on-demand)
- stakeholder-update — Board/leadership update with KPIs (Research → Content, monthly)
- relationship-health-digest — Interaction patterns from Slack (Slack Bot → CRM, weekly, requires Slack)
- project-status-report — Cross-platform status synthesis (Slack Bot → CRM → Content, weekly, requires Slack)
- slack-recap — Decisions, action items, discussions (Slack Bot, daily/weekly, requires Slack)
- notion-sync-report — What changed in Notion (Notion Bot, weekly, requires Notion)
- content-brief — Research-backed blog/content draft (Research → Content, on-demand)
- launch-material — GTM positioning + polished output (Marketing → Content, on-demand)
- gtm-tracker — Competitive moves + feature matrices (Marketing → Content, weekly)

**Flow:**
1. Understand what they need. Match to a type_key above.
2. Ask for focus/topic if applicable: "What specific area should this cover?"
3. Confirm schedule (use type's default unless they specify otherwise)
4. Create: `ManageTask(action="create", title="...", type_key="...", focus="...")`

If their need doesn't match any type, fall back to custom: `ManageTask(action="create", title="...", agent_slug="...", objective={...})`

Keep it simple — one question at a time. Prefer type_key over manual agent_slug.
""",
    },

    "recap": {
        "name": "recap",
        "description": "Set up a platform recap — daily or weekly catch-up from Slack or Notion",
        "trigger_patterns": ["recap", "platform recap", "slack recap", "notion recap", "slack digest", "notion summary", "weekly digest", "daily recap", "catch up", "create a recap", "digest"],
        "system_prompt_addition": """
---

## Active Command: Recap

Create a Slack or Notion recap using registered task types.

**Flow:**
1. Ask platform: `Clarify(question="Which platform?", options=["Slack", "Notion", "Both"])`
2. Ask frequency: `Clarify(question="How often?", options=["Daily", "Weekly"])`
3. Create using type_key:
   - Slack: `ManageTask(action="create", title="Daily Slack Recap", type_key="slack-recap", schedule="daily")`
   - Notion: `ManageTask(action="create", title="Weekly Notion Sync", type_key="notion-sync-report")`
   - Both: create both tasks

**Note:** Slack/Notion types require the platform to be connected. If not connected, prompt user to connect first.
""",
    },

    "summary": {
        "name": "summary",
        "description": "Create a work summary — synthesize activity into a report",
        "trigger_patterns": ["work summary", "status report", "status update", "weekly report", "progress report", "board update", "stakeholder update", "investor update", "summarize my work"],
        "system_prompt_addition": """
---

## Active Command: Work Summary

Create a stakeholder report or project status using registered task types.

**Flow:**
1. Ask audience: `Clarify(question="Who is this for?", options=["Board/Investors", "Leadership", "Team"])`
2. Based on audience:
   - Board/Investors/Leadership → `ManageTask(action="create", title="Monthly Stakeholder Report", type_key="stakeholder-update")`
   - Team → `ManageTask(action="create", title="Weekly Project Status", type_key="project-status")`
3. Ask for any focus customization

**Defaults:** stakeholder-update=monthly, project-status=weekly
""",
    },

    "research": {
        "name": "research",
        "description": "Set up research tracking — monitors topics and surfaces insights",
        "trigger_patterns": ["proactive insights", "insights", "deep research", "watch my platforms", "surface insights", "investigate", "research this", "look into", "find out about", "track competitors", "competitive intel"],
        "system_prompt_addition": """
---

## Active Command: Research

Create a research task using registered task types. Match to the best type:

- Competitive tracking → `ManageTask(action="create", title="...", type_key="competitive-intel-brief", focus="...")`
- Market/industry research → `ManageTask(action="create", title="...", type_key="market-research-report", focus="...")`
- Industry monitoring → `ManageTask(action="create", title="...", type_key="industry-signal-monitor", focus="...")`
- GTM tracking → `ManageTask(action="create", title="...", type_key="gtm-tracker", focus="...")`
- Due diligence → `ManageTask(action="create", title="...", type_key="due-diligence-summary", focus="...")`

**Flow:**
1. Ask what to research: "What topic or domain?"
2. Match to best type_key
3. Ask frequency if default isn't right
4. Create with focus parameter

**Defaults:** competitive-intel-brief=weekly, market-research-report=monthly
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

User wants to create a new Agent. Under ADR-189 (authored-team model), Agents are the user's
— built through conversation, each scoped to a specific domain of the user's work. The user
starts with zero Agents and builds the team as work intents emerge.

Your job is to help the user author an Agent that matches the work they're describing.

1. Understand the domain — what does this Agent need to know or track? (competitors, clients,
   market trends, product launches, specific projects, etc.)
2. Clarify the role — ask briefly only if the work intent is unclear: `Clarify(question="What
   kind of work?", options=["Researcher", "Analyst", "Writer", "Tracker", "Designer"])`.
   Otherwise infer from conversation.
3. Create: `ManageAgent(action="create", title="<user's language>", role="<role>")`. Use the
   user's own words for the title — this is their Agent, it should sound like theirs.
4. Confirm and suggest a first task: once the Agent exists, the natural next step is
   describing what work it should do. Offer a concrete task idea based on the domain.

Notes:
- Specialists (Researcher, Analyst, Writer, Tracker, Designer, Reporting) are YARNNN's palette
  — you draft them into Teams per task. They are NOT user-visible Agents. Do not suggest the
  user "create a Researcher Agent" unless they mean a specific domain-scoped worker.
- Platform Bots (Slack, Notion, GitHub, Commerce, Trading) activate on platform connection.
  If a user wants to "add Slack," route them to connect rather than creating an Agent.
""",
    },

    # =========================================================================
    # Capability Commands — surface YARNNN's built-in abilities
    # =========================================================================
    "search": {
        "name": "search",
        "description": "Search across workspace context domains and knowledge",
        "trigger_patterns": ["search my platforms", "find in slack", "find in notion", "search for", "look up"],
        "system_prompt_addition": """
---

## Active Command: Search

User wants to search their workspace data.

Use `SearchEntities(query="...", scope="all")` to find relevant content across entities, or `QueryKnowledge(query="...")` for semantic search over accumulated context domains.
Use `QueryKnowledge(query="...")` for semantic search across accumulated knowledge.

Ask the user what they're looking for if not clear from context.
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

Use `UpdateContext(target="memory", text="...")` to save to the user's persistent memory.

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
