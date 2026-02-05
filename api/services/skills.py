"""
Skills System (ADR-025 Claude Code Alignment)

Skills are packaged workflows triggered by slash commands or intent recognition.
Each skill expands to a system prompt addition that guides TP through a structured process.

This mirrors Claude Code's skill system where /commit, /review-pr, etc. are packaged
workflows that expand to detailed instructions + expected tool sequences.
"""

from typing import Optional, Dict, Any


# =============================================================================
# Skill Definitions
# =============================================================================

SKILLS: Dict[str, Dict[str, Any]] = {
    "board-update": {
        "name": "board-update",
        "description": "Create a recurring board update deliverable",
        "trigger_patterns": ["board update", "investor update", "board report", "investor report"],
        "deliverable_type": "board_update",
        "system_prompt_addition": """
---

## Active Skill: Board Update Creation

You are helping the user create a recurring board update deliverable.

**Use todo_write to track your progress through this workflow:**

```
todo_write([
  {content: "Parse intent", status: "completed", activeForm: "Parsing intent"},
  {content: "Gather required details", status: "in_progress", activeForm: "Gathering required details"},
  {content: "Confirm deliverable setup", status: "pending", activeForm: "Confirming deliverable setup"},
  {content: "Create deliverable", status: "pending", activeForm: "Creating deliverable"},
  {content: "Offer first draft", status: "pending", activeForm: "Offering first draft"}
])
```

Update todos as you progress. Only ONE task should be `in_progress` at a time.

**Required information to gather:**
- Recipient name (e.g., "Marcus Webb", "the board", "investors")
- Company/project name (check existing projects first with list_projects)
- Frequency (default: monthly on 1st at 9am)
- Company stage (seed, Series A, etc.) — helpful for setting tone

**Workflow:**
1. Parse user's initial request - extract any details they've already provided
2. Use clarify() or respond() to gather missing required info
3. Confirm the full setup with respond() before creating
4. Create with create_deliverable(deliverable_type="board_update", ...)
5. Offer to generate first draft with run_deliverable

**Board updates typically include:**
- Executive Summary
- Key Metrics & KPIs
- Progress & Milestones
- Challenges & Risks
- Asks & Support Needed
- Outlook & Next Period

**Don't guess - use clarify() for missing required info.**
""",
    },

    "status-report": {
        "name": "status-report",
        "description": "Create a recurring status report deliverable",
        "trigger_patterns": ["status report", "weekly report", "progress report", "status update"],
        "deliverable_type": "status_report",
        "system_prompt_addition": """
---

## Active Skill: Status Report Creation

You are helping the user create a recurring status report deliverable.

**Use todo_write to track your progress through this workflow:**

```
todo_write([
  {content: "Parse intent", status: "completed", activeForm: "Parsing intent"},
  {content: "Gather required details", status: "in_progress", activeForm: "Gathering required details"},
  {content: "Confirm deliverable setup", status: "pending", activeForm: "Confirming deliverable setup"},
  {content: "Create deliverable", status: "pending", activeForm: "Creating deliverable"},
  {content: "Offer first draft", status: "pending", activeForm: "Offering first draft"}
])
```

**Required information to gather:**
- Recipient name (e.g., "Sarah", "my manager", "the team")
- Frequency (default: weekly on Monday at 9am)
- Focus areas (optional: what should be covered)

**Workflow:**
1. Parse user's initial request - extract any details they've already provided
2. Use clarify() or respond() to gather missing required info
3. Confirm the full setup with respond() before creating
4. Create with create_deliverable(deliverable_type="status_report", ...)
5. Offer to generate first draft

**Don't guess - use clarify() for missing required info.**
""",
    },

    "research-brief": {
        "name": "research-brief",
        "description": "Create a recurring research brief deliverable",
        "trigger_patterns": ["research brief", "competitive intel", "market research", "competitor analysis", "competitor brief"],
        "deliverable_type": "research_brief",
        "system_prompt_addition": """
---

## Active Skill: Research Brief Creation

You are helping the user create a recurring research brief deliverable.

**Use todo_write to track your progress through this workflow:**

```
todo_write([
  {content: "Parse intent", status: "completed", activeForm: "Parsing intent"},
  {content: "Gather required details", status: "in_progress", activeForm: "Gathering required details"},
  {content: "Confirm deliverable setup", status: "pending", activeForm: "Confirming deliverable setup"},
  {content: "Create deliverable", status: "pending", activeForm: "Creating deliverable"},
  {content: "Offer first draft", status: "pending", activeForm: "Offering first draft"}
])
```

**Required information to gather:**
- Research focus (competitors, market trends, technology, specific companies)
- Frequency (default: weekly)
- Data sources or areas to monitor (optional)

**Workflow:**
1. Parse user's initial request - extract any details they've already provided
2. Use clarify() or respond() to gather missing required info
3. Confirm the full setup with respond() before creating
4. Create with create_deliverable(deliverable_type="research_brief", ...)
5. Offer to generate first draft

**Don't guess - use clarify() for missing required info.**
""",
    },

    "stakeholder-update": {
        "name": "stakeholder-update",
        "description": "Create a recurring stakeholder update deliverable",
        "trigger_patterns": ["stakeholder update", "client update", "client report", "stakeholder report"],
        "deliverable_type": "stakeholder_update",
        "system_prompt_addition": """
---

## Active Skill: Stakeholder Update Creation

You are helping the user create a recurring stakeholder update deliverable.

**Use todo_write to track your progress through this workflow:**

```
todo_write([
  {content: "Parse intent", status: "completed", activeForm: "Parsing intent"},
  {content: "Gather required details", status: "in_progress", activeForm: "Gathering required details"},
  {content: "Confirm deliverable setup", status: "pending", activeForm: "Confirming deliverable setup"},
  {content: "Create deliverable", status: "pending", activeForm: "Creating deliverable"},
  {content: "Offer first draft", status: "pending", activeForm: "Offering first draft"}
])
```

**Required information to gather:**
- Recipient/stakeholder name
- Relationship (client, partner, executive, etc.)
- Frequency (default: weekly)
- What they care about most (progress, metrics, blockers, etc.)

**Workflow:**
1. Parse user's initial request - extract any details they've already provided
2. Use clarify() or respond() to gather missing required info
3. Confirm the full setup with respond() before creating
4. Create with create_deliverable(deliverable_type="stakeholder_update", ...)
5. Offer to generate first draft

**Don't guess - use clarify() for missing required info.**
""",
    },

    "meeting-summary": {
        "name": "meeting-summary",
        "description": "Create a recurring meeting summary deliverable",
        "trigger_patterns": ["meeting summary", "meeting notes", "meeting recap", "standup notes"],
        "deliverable_type": "meeting_summary",
        "system_prompt_addition": """
---

## Active Skill: Meeting Summary Creation

You are helping the user create a recurring meeting summary deliverable.

**Use todo_write to track your progress through this workflow:**

```
todo_write([
  {content: "Parse intent", status: "completed", activeForm: "Parsing intent"},
  {content: "Gather required details", status: "in_progress", activeForm: "Gathering required details"},
  {content: "Confirm deliverable setup", status: "pending", activeForm: "Confirming deliverable setup"},
  {content: "Create deliverable", status: "pending", activeForm: "Creating deliverable"},
  {content: "Offer first draft", status: "pending", activeForm: "Offering first draft"}
])
```

**Required information to gather:**
- Meeting name/type (e.g., "Weekly team standup", "1:1 with Sarah")
- Frequency (when does the meeting occur?)
- Who receives the summary
- Key sections to include (action items, decisions, discussion points)

**Workflow:**
1. Parse user's initial request - extract any details they've already provided
2. Use clarify() or respond() to gather missing required info
3. Confirm the full setup with respond() before creating
4. Create with create_deliverable(deliverable_type="meeting_summary", ...)
5. Offer to generate first draft

**Don't guess - use clarify() for missing required info.**
""",
    },
}


# =============================================================================
# Skill Detection & Expansion
# =============================================================================

def detect_skill(user_message: str) -> Optional[str]:
    """
    Detect if user message triggers a skill.

    Returns skill name if detected, None otherwise.

    Detection methods:
    1. Explicit slash command: /board-update
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
