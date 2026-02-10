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
    # Deliverable Types
    # =========================================================================
    "board-update": {
        "name": "board-update",
        "description": "Create a recurring board update deliverable",
        "trigger_patterns": ["board update", "investor update", "board report", "investor report"],
        "deliverable_type": "board_update",
        "system_prompt_addition": """
---

## Active Skill: Board Update

Create a board/investor update deliverable.

**Flow:**
1. Check for duplicates: `List(pattern="deliverable:*")`
2. If missing recipient, ask: `Clarify(question="Who receives this?", options=["Board of directors", "Lead investor", "All investors"])`
3. Confirm: "I'll create a monthly Board Update for [recipient]. Ready?"
4. On confirmation: `Write(ref="deliverable:new", content={title, deliverable_type: "stakeholder_update", frequency: "monthly", recipient_name})`
5. Offer first draft: "Created. Generate first draft now?"

**Defaults:** frequency=monthly, type=stakeholder_update
""",
    },

    "status-report": {
        "name": "status-report",
        "description": "Create a recurring status report deliverable",
        "trigger_patterns": ["status report", "weekly report", "progress report", "status update"],
        "deliverable_type": "status_report",
        "system_prompt_addition": """
---

## Active Skill: Status Report

Create a status report deliverable.

**Flow:**
1. Check for duplicates: `List(pattern="deliverable:*")`
2. If missing recipient, ask: `Clarify(question="Who receives this?", options=["Manager", "Team", "Stakeholders"])`
3. Confirm: "I'll create a weekly Status Report for [recipient]. Ready?"
4. On confirmation: `Write(ref="deliverable:new", content={title, deliverable_type: "status_report", frequency: "weekly", recipient_name})`
5. Offer first draft

**Defaults:** frequency=weekly, type=status_report
""",
    },

    "research-brief": {
        "name": "research-brief",
        "description": "Create a recurring research brief deliverable",
        "trigger_patterns": ["research brief", "competitive intel", "market research", "competitor analysis", "competitor brief"],
        "deliverable_type": "research_brief",
        "system_prompt_addition": """
---

## Active Skill: Research Brief

Create a research/competitive intelligence deliverable.

**Flow:**
1. Check for duplicates: `List(pattern="deliverable:*")`
2. If missing focus, ask: `Clarify(question="What should I research?", options=["Competitors", "Market trends", "Technology"])`
3. Confirm: "I'll create a weekly Research Brief on [focus]. Ready?"
4. On confirmation: `Write(ref="deliverable:new", content={title, deliverable_type: "research_brief", frequency: "weekly"})`
5. Offer first draft

**Defaults:** frequency=weekly, type=research_brief
""",
    },

    "stakeholder-update": {
        "name": "stakeholder-update",
        "description": "Create a recurring stakeholder update deliverable",
        "trigger_patterns": ["stakeholder update", "client update", "client report", "stakeholder report"],
        "deliverable_type": "stakeholder_update",
        "system_prompt_addition": """
---

## Active Skill: Stakeholder Update

Create a stakeholder/client update deliverable.

**Flow:**
1. Check for duplicates: `List(pattern="deliverable:*")`
2. If missing stakeholder, ask: `Clarify(question="Who is this for?", options=["Client", "Executive", "Partner"])`
3. Confirm: "I'll create a [frequency] update for [stakeholder]. Ready?"
4. On confirmation: `Write(ref="deliverable:new", content={title, deliverable_type: "stakeholder_update", frequency, recipient_name})`
5. Offer first draft

**Defaults:** frequency=weekly, type=stakeholder_update
""",
    },

    "meeting-summary": {
        "name": "meeting-summary",
        "description": "Create a recurring meeting summary deliverable",
        "trigger_patterns": ["meeting summary", "meeting notes", "meeting recap", "standup notes"],
        "deliverable_type": "meeting_summary",
        "system_prompt_addition": """
---

## Active Skill: Meeting Summary

Create a meeting summary deliverable.

**Flow:**
1. Check for duplicates: `List(pattern="deliverable:*")`
2. If missing meeting type, ask: `Clarify(question="What meeting?", options=["Standup", "Team sync", "1:1", "All-hands"])`
3. Confirm: "I'll create a [frequency] summary for [meeting]. Ready?"
4. On confirmation: `Write(ref="deliverable:new", content={title, deliverable_type: "meeting_summary", frequency})`
5. Offer first draft

**Defaults:** frequency=weekly, type=meeting_summary
""",
    },

    # =========================================================================
    # Beta Tier Skills
    # =========================================================================
    "newsletter-section": {
        "name": "newsletter-section",
        "description": "Create a recurring newsletter section deliverable",
        "trigger_patterns": ["newsletter", "newsletter section", "weekly digest", "founder letter", "product update"],
        "deliverable_type": "newsletter_section",
        "tier": "beta",
        "system_prompt_addition": """
---

## Active Skill: Newsletter Section (Beta)

Create a newsletter section deliverable.

**Flow:**
1. Check for duplicates: `List(pattern="deliverable:*")`
2. Ask section type: `Clarify(question="What section?", options=["Intro/letter", "Main story", "Product updates", "Roundup"])`
3. Confirm and create with `Write(ref="deliverable:new", ...)`

**Defaults:** frequency=weekly, type=newsletter_section
""",
    },

    "changelog": {
        "name": "changelog",
        "description": "Create a recurring changelog/release notes deliverable",
        "trigger_patterns": ["changelog", "release notes", "version update", "product release", "what's new"],
        "deliverable_type": "changelog",
        "tier": "beta",
        "system_prompt_addition": """
---

## Active Skill: Changelog (Beta)

Create a changelog/release notes deliverable.

**Flow:**
1. Check for duplicates: `List(pattern="deliverable:*")`
2. Ask audience: `Clarify(question="Who's the audience?", options=["Developers", "End users", "Mixed"])`
3. Confirm and create with `Write(ref="deliverable:new", ...)`

**Defaults:** frequency=weekly, type=changelog
""",
    },

    "one-on-one-prep": {
        "name": "one-on-one-prep",
        "description": "Create a recurring 1:1 meeting prep deliverable",
        "trigger_patterns": ["1:1 prep", "one on one prep", "1-1 prep", "one-on-one", "meeting prep for"],
        "deliverable_type": "one_on_one_prep",
        "tier": "beta",
        "system_prompt_addition": """
---

## Active Skill: 1:1 Prep (Beta)

Create a 1:1 meeting prep deliverable.

**Flow:**
1. Check for duplicates: `List(pattern="deliverable:*")`
2. Ask relationship: `Clarify(question="Who's this with?", options=["Direct report", "Manager", "Skip level", "Mentee"])`
3. Confirm and create with `Write(ref="deliverable:new", ...)`

**Defaults:** frequency=weekly, type=one_on_one_prep
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

    return (None, "none", 0.0)
