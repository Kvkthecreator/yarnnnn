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
        "description": "Create a recurring status update deliverable",
        "trigger_patterns": ["status report", "status update", "weekly report", "progress report", "board update", "stakeholder update", "investor update", "create a status", "create status deliverable", "create a status update"],
        "deliverable_type": "status",
        "system_prompt_addition": """
---

## Active Skill: Status Update

Create a status update deliverable — a regular cross-platform summary for a person or audience.

**Flow:**
1. Check for duplicates: `List(pattern="deliverable:*")`
2. If missing recipient, ask: `Clarify(question="Who receives this?", options=["Manager", "Team", "Stakeholders", "Board"])`
3. Confirm: "I'll create a weekly Status Update for [recipient]. Ready?"
4. On confirmation: `Write(ref="deliverable:new", content={title, deliverable_type: "status", frequency: "weekly", recipient_name})`
5. Offer first draft

**Defaults:** frequency=weekly, type=status
""",
    },

    "digest": {
        "name": "digest",
        "description": "Create a recurring digest deliverable",
        "trigger_patterns": ["slack digest", "channel digest", "inbox brief", "email digest", "notion summary", "calendar preview", "weekly digest", "create a digest", "create digest deliverable"],
        "deliverable_type": "digest",
        "system_prompt_addition": """
---

## Active Skill: Digest

Create a digest deliverable — a regular synthesis of what's happening in a specific place (Slack channel, email inbox, Notion page, calendar).

**Flow:**
1. Check for duplicates: `List(pattern="deliverable:*")`
2. Ask source: `Clarify(question="What should this digest cover?", options=["Slack channel", "Email inbox", "Notion page", "Calendar"])`
3. Confirm: "I'll create a [frequency] Digest from [source]. Ready?"
4. On confirmation: `Write(ref="deliverable:new", content={title, deliverable_type: "digest", frequency, sources})`
5. Offer first draft

**Defaults:** frequency=weekly, type=digest
""",
    },

    "brief": {
        "name": "brief",
        "description": "Create a brief deliverable for a specific event or situation",
        "trigger_patterns": ["meeting brief", "meeting prep", "event prep", "call prep", "1:1 prep", "one on one prep", "meeting summary", "one-on-one", "create a brief", "create brief deliverable"],
        "deliverable_type": "brief",
        "system_prompt_addition": """
---

## Active Skill: Brief

Create a brief deliverable — a situation-specific document before a key event (meeting, call, presentation).

**Flow:**
1. Check for duplicates: `List(pattern="deliverable:*")`
2. Ask event: `Clarify(question="What's this brief for?", options=["Recurring 1:1", "Team sync", "Client call", "Presentation"])`
3. Confirm: "I'll create a [frequency] brief for [event]. Ready?"
4. On confirmation: `Write(ref="deliverable:new", content={title, deliverable_type: "brief", frequency})`
5. Offer first draft

**Defaults:** frequency=weekly, type=brief
""",
    },

    "deep-research": {
        "name": "deep-research",
        "description": "Create a deep research deliverable",
        "trigger_patterns": ["research brief", "deep research", "competitive intel", "market research", "competitor analysis", "competitor brief", "create a deep research", "create deep research deliverable"],
        "deliverable_type": "deep_research",
        "system_prompt_addition": """
---

## Active Skill: Deep Research

Create a deep research deliverable — a bounded investigation into a specific topic, then done.

**Flow:**
1. Check for duplicates: `List(pattern="deliverable:*")`
2. If missing focus, ask: `Clarify(question="What should I research?", options=["Competitors", "Market trends", "Technology", "Industry"])`
3. Confirm: "I'll create a Deep Research report on [focus]. Ready?"
4. On confirmation: `Write(ref="deliverable:new", content={title, deliverable_type: "deep_research", mode: "goal"})`
5. Offer first draft

**Defaults:** mode=goal (runs once to completion), type=deep_research
""",
    },

    "watch": {
        "name": "watch",
        "description": "Create a watch deliverable for ongoing domain monitoring",
        "trigger_patterns": ["watch brief", "intel brief", "competitive watch", "monitor", "keep an eye on", "intelligence brief", "create a watch", "create watch deliverable"],
        "deliverable_type": "watch",
        "system_prompt_addition": """
---

## Active Skill: Watch

Create a watch deliverable — standing-order intelligence on a domain you can't monitor full-time.

**Flow:**
1. Check for duplicates: `List(pattern="deliverable:*")`
2. Ask domain: `Clarify(question="What domain should I watch?", options=["Competitors", "Industry news", "Customer signals", "Regulatory changes"])`
3. Confirm: "I'll create a Watch brief for [domain]. Ready?"
4. On confirmation: `Write(ref="deliverable:new", content={title, deliverable_type: "watch", mode: "proactive"})`
5. Offer first draft

**Defaults:** mode=proactive, type=watch
""",
    },

    "custom": {
        "name": "custom",
        "description": "Create a custom deliverable with user-defined intent",
        "trigger_patterns": ["newsletter", "changelog", "release notes", "client proposal", "custom deliverable", "create a custom", "create custom deliverable"],
        "deliverable_type": "custom",
        "system_prompt_addition": """
---

## Active Skill: Custom

Create a custom deliverable — the user defines exactly what they want.

**Flow:**
1. Check for duplicates: `List(pattern="deliverable:*")`
2. Ask for description: `Clarify(question="Describe what this deliverable should produce", options=[])`
3. Confirm: "I'll create a Custom deliverable: [description]. Ready?"
4. On confirmation: `Write(ref="deliverable:new", content={title, deliverable_type: "custom", description})`
5. Offer first draft

**Defaults:** frequency=weekly, type=custom
""",
    },

    "coordinator": {
        "name": "coordinator",
        "description": "Create a coordinator deliverable that manages other deliverables",
        "trigger_patterns": ["coordinator", "create a coordinator", "create coordinator deliverable", "orchestrator", "auto-create deliverables"],
        "deliverable_type": "coordinator",
        "system_prompt_addition": """
---

## Active Skill: Coordinator

Create a coordinator deliverable — a meta-agent that watches a domain and creates or triggers other deliverables when conditions are met.

**Flow:**
1. Check for duplicates: `List(pattern="deliverable:*")`
2. Ask domain: `Clarify(question="What domain should this coordinator watch?", options=["Meeting prep", "Project updates", "Customer signals", "Custom domain"])`
3. Ask rules: "What should trigger it to create child deliverables?"
4. Confirm: "I'll create a Coordinator for [domain]. Ready?"
5. On confirmation: `Write(ref="deliverable:new", content={title, deliverable_type: "coordinator", mode: "coordinator"})`

**Defaults:** mode=coordinator (proactive, no fixed schedule), type=coordinator
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
    except Exception as e:
        # Semantic matching failed (e.g., missing OPENAI_API_KEY) — non-fatal
        logger.debug(f"Semantic skill detection failed: {e}")
        pass

    return (None, "none", 0.0)
