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

### CRITICAL: Do NOT call create_deliverable() until the user explicitly confirms!

**This is a CONVERSATION, not a single action.** You MUST:
1. Ask clarifying questions FIRST
2. Wait for user's response
3. Confirm your understanding
4. Only create after user says "yes" or similar

### Step 1: Parse & Identify Gaps (DO THIS NOW)

Extract what the user provided:
- Recipient: ___
- Company/project: ___
- Frequency: ___

**If ANY of these are missing or unclear, you MUST use clarify() to ask.**

### Step 2: Ask Clarifying Questions

Use clarify() with helpful options. Example:
```
clarify(
  question="A few quick questions to set this up right:\\n1. Who receives this update? (e.g., 'Marcus Webb', 'Board of Directors')\\n2. What company/project is this for?",
  options=["I'll provide details", "Use my existing project context"]
)
```

**STOP HERE and wait for user response.** Do not proceed to Step 3 until user answers.

### Step 3: Confirm Before Creating

After user provides info, confirm with respond():
```
respond("Got it! I'll set up a monthly board update for [recipient] using your [project] context. Ready to create it?")
```

**STOP HERE and wait for user to confirm.** Only proceed if they say "yes", "sounds good", "do it", etc.

### Step 4: Create & Offer First Draft

Only NOW call create_deliverable(), then offer run_deliverable().

### Todo Tracking

Track progress with todo_write:
```
todo_write([
  {content: "Parse user request", status: "in_progress", activeForm: "Parsing user request"},
  {content: "Ask clarifying questions", status: "pending", activeForm: "Asking clarifying questions"},
  {content: "Get user confirmation", status: "pending", activeForm: "Getting user confirmation"},
  {content: "Create deliverable", status: "pending", activeForm: "Creating deliverable"},
  {content: "Offer first draft", status: "pending", activeForm: "Offering first draft"}
])
```
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

### CRITICAL: Do NOT call create_deliverable() until the user explicitly confirms!

**This is a CONVERSATION, not a single action.** You MUST:
1. Ask clarifying questions FIRST
2. Wait for user's response
3. Confirm your understanding
4. Only create after user says "yes" or similar

### Step 1: Parse & Identify Gaps (DO THIS NOW)

Extract what the user provided:
- Recipient: ___
- Frequency: ___
- Focus areas: ___

**If recipient is missing or vague, you MUST use clarify() to ask.**

### Step 2: Ask Clarifying Questions

Use clarify() with helpful options. Example:
```
clarify(
  question="Who should receive this status report?",
  options=["My manager", "My team", "A specific person (I'll provide the name)"]
)
```

**STOP HERE and wait for user response.** Do not proceed to Step 3 until user answers.

### Step 3: Confirm Before Creating

After user provides info, confirm with respond():
```
respond("I'll set up a weekly status report for [recipient], ready every Monday at 9am. Sound good?")
```

**STOP HERE and wait for user to confirm.**

### Step 4: Create & Offer First Draft

Only NOW call create_deliverable(), then offer run_deliverable().

### Todo Tracking

Track progress with todo_write:
```
todo_write([
  {content: "Parse user request", status: "in_progress", activeForm: "Parsing user request"},
  {content: "Ask clarifying questions", status: "pending", activeForm: "Asking clarifying questions"},
  {content: "Get user confirmation", status: "pending", activeForm: "Getting user confirmation"},
  {content: "Create deliverable", status: "pending", activeForm: "Creating deliverable"},
  {content: "Offer first draft", status: "pending", activeForm: "Offering first draft"}
])
```
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

### CRITICAL: Do NOT call create_deliverable() until the user explicitly confirms!

**This is a CONVERSATION, not a single action.** You MUST:
1. Ask clarifying questions FIRST
2. Wait for user's response
3. Confirm your understanding
4. Only create after user says "yes" or similar

### Step 1: Parse & Identify Gaps (DO THIS NOW)

Extract what the user provided:
- Research focus: ___
- Specific companies/competitors: ___
- Frequency: ___

**If focus is vague (e.g., just "competitors"), you MUST use clarify() to ask which ones.**

### Step 2: Ask Clarifying Questions

Use clarify() with helpful options. Example:
```
clarify(
  question="What should this research brief focus on?",
  options=["Specific competitors (I'll name them)", "General market trends", "Technology developments", "All of the above"]
)
```

**STOP HERE and wait for user response.**

### Step 3: Confirm Before Creating

After user provides info, confirm with respond():
```
respond("I'll set up a weekly research brief tracking [focus]. Ready to create it?")
```

**STOP HERE and wait for user to confirm.**

### Step 4: Create & Offer First Draft

Only NOW call create_deliverable(), then offer run_deliverable().

### Todo Tracking

Track progress with todo_write:
```
todo_write([
  {content: "Parse user request", status: "in_progress", activeForm: "Parsing user request"},
  {content: "Ask clarifying questions", status: "pending", activeForm: "Asking clarifying questions"},
  {content: "Get user confirmation", status: "pending", activeForm: "Getting user confirmation"},
  {content: "Create deliverable", status: "pending", activeForm: "Creating deliverable"},
  {content: "Offer first draft", status: "pending", activeForm: "Offering first draft"}
])
```
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

### CRITICAL: Do NOT call create_deliverable() until the user explicitly confirms!

**This is a CONVERSATION, not a single action.** You MUST:
1. Ask clarifying questions FIRST
2. Wait for user's response
3. Confirm your understanding
4. Only create after user says "yes" or similar

### Step 1: Parse & Identify Gaps (DO THIS NOW)

Extract what the user provided:
- Stakeholder name: ___
- Relationship: ___
- Frequency: ___

**If stakeholder name is missing, you MUST use clarify() to ask.**

### Step 2: Ask Clarifying Questions

Use clarify() with helpful options. Example:
```
clarify(
  question="Who is this update for?",
  options=["A client", "An executive/leadership", "A partner", "Someone else (I'll specify)"]
)
```

**STOP HERE and wait for user response.**

### Step 3: Confirm Before Creating

After user provides info, confirm with respond():
```
respond("I'll set up a [frequency] update for [stakeholder]. Ready to create it?")
```

**STOP HERE and wait for user to confirm.**

### Step 4: Create & Offer First Draft

Only NOW call create_deliverable(), then offer run_deliverable().

### Todo Tracking

Track progress with todo_write:
```
todo_write([
  {content: "Parse user request", status: "in_progress", activeForm: "Parsing user request"},
  {content: "Ask clarifying questions", status: "pending", activeForm: "Asking clarifying questions"},
  {content: "Get user confirmation", status: "pending", activeForm: "Getting user confirmation"},
  {content: "Create deliverable", status: "pending", activeForm: "Creating deliverable"},
  {content: "Offer first draft", status: "pending", activeForm: "Offering first draft"}
])
```
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

### CRITICAL: Do NOT call create_deliverable() until the user explicitly confirms!

**This is a CONVERSATION, not a single action.** You MUST:
1. Ask clarifying questions FIRST
2. Wait for user's response
3. Confirm your understanding
4. Only create after user says "yes" or similar

### Step 1: Parse & Identify Gaps (DO THIS NOW)

Extract what the user provided:
- Meeting name/type: ___
- Frequency: ___
- Recipients: ___

**If meeting name or frequency is missing, you MUST use clarify() to ask.**

### Step 2: Ask Clarifying Questions

Use clarify() with helpful options. Example:
```
clarify(
  question="What meeting is this for?",
  options=["Team standup", "1:1 meeting", "Project sync", "Other (I'll specify)"]
)
```

**STOP HERE and wait for user response.**

### Step 3: Confirm Before Creating

After user provides info, confirm with respond():
```
respond("I'll set up a meeting summary for your [meeting name], generated [frequency]. Sound good?")
```

**STOP HERE and wait for user to confirm.**

### Step 4: Create & Offer First Draft

Only NOW call create_deliverable(), then offer run_deliverable().

### Todo Tracking

Track progress with todo_write:
```
todo_write([
  {content: "Parse user request", status: "in_progress", activeForm: "Parsing user request"},
  {content: "Ask clarifying questions", status: "pending", activeForm: "Asking clarifying questions"},
  {content: "Get user confirmation", status: "pending", activeForm: "Getting user confirmation"},
  {content: "Create deliverable", status: "pending", activeForm: "Creating deliverable"},
  {content: "Offer first draft", status: "pending", activeForm: "Offering first draft"}
])
```
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
