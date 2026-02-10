"""
Skills System (ADR-025 Claude Code Alignment)

Skills are packaged workflows triggered by slash commands or intent recognition.
Each skill expands to a system prompt addition that guides TP through a structured process.

This mirrors Claude Code's skill system where /commit, /review-pr, etc. are packaged
workflows that expand to detailed instructions + expected tool sequences.

Tier 1 Integration (Plan Mode, Assumption Checking, Todo Revision):
- All skills now follow plan mode discipline
- Assumption checks are required before creating entities
- Plans can be revised when assumptions fail

ADR-040 Enhancement: Semantic Skill Matching
- Hybrid detection: pattern matching first (fast), semantic fallback (higher recall)
- Embeddings enable natural language skill activation for variations not in patterns
"""

import logging
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Shared Skill Patterns (ADR-025 Tier 1)
# =============================================================================

SKILL_PLAN_MODE_HEADER = """
### Plan Mode Active (ADR-025 v2 - Phase Workflow)

This skill follows the phased workflow pattern:

| Phase | Marker | Description |
|-------|--------|-------------|
| Planning | `[PLAN]` | Parse request, check assumptions, gather info |
| Approval | `[GATE]` | **STOP** - summarize plan, get user confirmation |
| Execution | `[EXEC]` | Create entities (only after gate approval) |
| Validation | `[VALIDATE]` | Verify results, offer next steps |

### Critical: Approval Gate

**The `[GATE]` step is a HARD STOP.** When you reach it:
1. Mark `[GATE]` todo as `in_progress`
2. Use `respond()` to summarize what you'll create
3. Use `clarify("Ready to create?", ["Yes, create it", "Let me adjust..."])`
4. **WAIT for user response** - do NOT proceed to `[EXEC]`

### Assumption Checks (During `[PLAN]` Phase)

Before the gate, verify:
- **Project context**: `list_projects()` - does expected project exist?
- **No duplicates**: `list_deliverables()` - is there already a similar deliverable?

If checks fail:
- Revise todos to add clarification/creation steps
- Inform user: "I don't see [X]. Should I create it, or use [alternative]?"
- Use `clarify()` to get direction
- Keep the `[GATE]` step - just add more `[PLAN]` steps before it
"""

SKILL_TODO_TEMPLATE = """
### Todo Tracking (v2 - with Phase Markers)

Start with these todos (adjust based on what user already provided):
```
todo_write([
  {{content: "[PLAN] Parse request & identify gaps", status: "completed", activeForm: "Parsing request"}},
  {{content: "[PLAN] Check project context", status: "in_progress", activeForm: "Checking context"}},
  {{content: "[PLAN] Gather missing details", status: "pending", activeForm: "Gathering details"}},
  {{content: "[GATE] Confirm setup with user", status: "pending", activeForm: "Awaiting confirmation"}},
  {{content: "[EXEC] Create deliverable", status: "pending", activeForm: "Creating deliverable"}},
  {{content: "[VALIDATE] Offer first draft", status: "pending", activeForm: "Offering first draft"}}
])
```

**Phase Rules:**
- `[PLAN]` - Gathering info, checking assumptions. Can proceed automatically.
- `[GATE]` - **HARD STOP.** Use `clarify("Ready to proceed?", [...])` and WAIT for user.
- `[EXEC]` - Only execute AFTER user confirms at gate.
- `[VALIDATE]` - Verify results, offer next steps.

**General Rules:**
- Update todos as you progress
- If assumption check fails, revise the todo list (add steps)
- Mark "Check project context" complete even if it reveals issues - the check was done
- **Never skip the `[GATE]` phase before `[EXEC]`**
"""


# =============================================================================
# Skill Definitions
# =============================================================================

SKILLS: Dict[str, Dict[str, Any]] = {
    "board-update": {
        "name": "board-update",
        "description": "Create a recurring board update deliverable",
        "trigger_patterns": ["board update", "investor update", "board report", "investor report"],
        "deliverable_type": "board_update",
        "system_prompt_addition": f"""
---

## Active Skill: Board Update Creation
{SKILL_PLAN_MODE_HEADER}

### Skill-Specific Flow

**Step 1: Parse & Check Context**

Extract from user message:
- Recipient: ___ (board, specific investor name)
- Company/project: ___
- Frequency: ___ (default: monthly)

Then immediately run assumption check:
- `list_projects()` to verify project context exists

**Step 2: Handle Gaps & Assumption Results**

If project doesn't exist:
→ Revise todos, offer to create project or use Personal context

If details missing:
→ Use `clarify()` to ask for recipient, company name

**Step 3: Confirm Before Creating**

After gathering info, confirm with `respond()`:
```
"I'll set up a Monthly Board Update for [recipient] using your [project] context.
Drafts ready on the 1st of each month. Ready to create?"
```

**STOP and wait for confirmation.**

**Step 4: Create & Offer Draft**

After user confirms:
1. `list_deliverables()` - verify no duplicate
2. `create_deliverable(...)`
3. `respond()` - confirm creation, offer `run_deliverable()`
{SKILL_TODO_TEMPLATE}
""",
    },

    "status-report": {
        "name": "status-report",
        "description": "Create a recurring status report deliverable",
        "trigger_patterns": ["status report", "weekly report", "progress report", "status update"],
        "deliverable_type": "status_report",
        "system_prompt_addition": f"""
---

## Active Skill: Status Report Creation
{SKILL_PLAN_MODE_HEADER}

### Skill-Specific Flow

**Step 1: Parse & Check Context**

Extract from user message:
- Recipient: ___ (manager, team, specific person)
- Frequency: ___ (default: weekly)
- Focus areas: ___

Then run assumption check:
- `list_projects()` to verify project context if mentioned

**Step 2: Handle Gaps & Assumption Results**

If recipient missing or vague:
→ Use `clarify()`: "Who should receive this report?"

If project mentioned but doesn't exist:
→ Revise todos, offer to create or use Personal

**Step 3: Confirm Before Creating**

After gathering info, confirm with `respond()`:
```
"I'll set up a Weekly Status Report for [recipient], ready every Monday at 9am. Sound good?"
```

**STOP and wait for confirmation.**

**Step 4: Create & Offer Draft**

After user confirms:
1. `list_deliverables()` - verify no duplicate
2. `create_deliverable(...)`
3. `respond()` - confirm creation, offer `run_deliverable()`
{SKILL_TODO_TEMPLATE}
""",
    },

    "research-brief": {
        "name": "research-brief",
        "description": "Create a recurring research brief deliverable",
        "trigger_patterns": ["research brief", "competitive intel", "market research", "competitor analysis", "competitor brief"],
        "deliverable_type": "research_brief",
        "system_prompt_addition": f"""
---

## Active Skill: Research Brief Creation
{SKILL_PLAN_MODE_HEADER}

### Skill-Specific Flow

**Step 1: Parse & Check Context**

Extract from user message:
- Research focus: ___ (competitors, market, technology)
- Specific companies: ___
- Frequency: ___ (default: weekly)

Then run assumption check:
- `list_projects()` to verify project context if research is project-specific

**Step 2: Handle Gaps & Assumption Results**

If focus is vague (just "competitors"):
→ Use `clarify()`: "Which competitors should I track?"

If project context needed but doesn't exist:
→ Revise todos, offer to create or proceed without

**Step 3: Confirm Before Creating**

After gathering info, confirm with `respond()`:
```
"I'll set up a Weekly Research Brief tracking [focus/competitors]. Ready to create?"
```

**STOP and wait for confirmation.**

**Step 4: Create & Offer Draft**

After user confirms:
1. `list_deliverables()` - verify no duplicate
2. `create_deliverable(...)`
3. `respond()` - confirm creation, offer `run_deliverable()`
{SKILL_TODO_TEMPLATE}
""",
    },

    "stakeholder-update": {
        "name": "stakeholder-update",
        "description": "Create a recurring stakeholder update deliverable",
        "trigger_patterns": ["stakeholder update", "client update", "client report", "stakeholder report"],
        "deliverable_type": "stakeholder_update",
        "system_prompt_addition": f"""
---

## Active Skill: Stakeholder Update Creation
{SKILL_PLAN_MODE_HEADER}

### Skill-Specific Flow

**Step 1: Parse & Check Context**

Extract from user message:
- Stakeholder name: ___
- Relationship: ___ (client, executive, partner)
- Frequency: ___

Then run assumption check:
- `list_projects()` to verify project context if stakeholder is project-specific

**Step 2: Handle Gaps & Assumption Results**

If stakeholder name missing:
→ Use `clarify()`: "Who is this update for?"

If project context needed but doesn't exist:
→ Revise todos, offer to create or use Personal

**Step 3: Confirm Before Creating**

After gathering info, confirm with `respond()`:
```
"I'll set up a [frequency] update for [stakeholder]. Ready to create?"
```

**STOP and wait for confirmation.**

**Step 4: Create & Offer Draft**

After user confirms:
1. `list_deliverables()` - verify no duplicate
2. `create_deliverable(...)`
3. `respond()` - confirm creation, offer `run_deliverable()`
{SKILL_TODO_TEMPLATE}
""",
    },

    "meeting-summary": {
        "name": "meeting-summary",
        "description": "Create a recurring meeting summary deliverable",
        "trigger_patterns": ["meeting summary", "meeting notes", "meeting recap", "standup notes"],
        "deliverable_type": "meeting_summary",
        "system_prompt_addition": f"""
---

## Active Skill: Meeting Summary Creation
{SKILL_PLAN_MODE_HEADER}

### Skill-Specific Flow

**Step 1: Parse & Check Context**

Extract from user message:
- Meeting name/type: ___
- Frequency: ___
- Recipients: ___

Then run assumption check:
- `list_projects()` if meeting is project-specific

**Step 2: Handle Gaps & Assumption Results**

If meeting name/type missing:
→ Use `clarify()`: "What meeting is this for?"

If project context needed but doesn't exist:
→ Revise todos, offer alternatives

**Step 3: Confirm Before Creating**

After gathering info, confirm with `respond()`:
```
"I'll set up a meeting summary for your [meeting name], generated [frequency]. Sound good?"
```

**STOP and wait for confirmation.**

**Step 4: Create & Offer Draft**

After user confirms:
1. `list_deliverables()` - verify no duplicate
2. `create_deliverable(...)`
3. `respond()` - confirm creation, offer `run_deliverable()`
{SKILL_TODO_TEMPLATE}
""",
    },

    # =========================================================================
    # Beta Tier Skills (ADR-019)
    # =========================================================================

    "newsletter-section": {
        "name": "newsletter-section",
        "description": "Create a recurring newsletter section deliverable",
        "trigger_patterns": ["newsletter", "newsletter section", "weekly digest", "founder letter", "product update"],
        "deliverable_type": "newsletter_section",
        "tier": "beta",
        "system_prompt_addition": f"""
---

## Active Skill: Newsletter Section Creation (Beta)
{SKILL_PLAN_MODE_HEADER}

### Skill-Specific Flow

**Step 1: Parse & Check Context**

Extract from user message:
- Newsletter name: ___
- Section type: ___ (intro, main story, roundup, outro)
- Audience: ___
- Frequency: ___

**Step 2: Handle Gaps**

If newsletter name or section type missing:
→ Use `clarify()`: "What type of newsletter section is this?"

**Step 3: Confirm Before Creating**

```
"I'll set up a [frequency] [section type] for your [newsletter name]. Sound good?"
```

**Step 4: Create & Offer Draft**

After confirmation: `create_deliverable()` → `respond()` with offer
{SKILL_TODO_TEMPLATE}
""",
    },

    "changelog": {
        "name": "changelog",
        "description": "Create a recurring changelog/release notes deliverable",
        "trigger_patterns": ["changelog", "release notes", "version update", "product release", "what's new"],
        "deliverable_type": "changelog",
        "tier": "beta",
        "system_prompt_addition": f"""
---

## Active Skill: Changelog Creation (Beta)
{SKILL_PLAN_MODE_HEADER}

### Skill-Specific Flow

**Step 1: Parse & Check Context**

Extract from user message:
- Product name: ___
- Audience: ___ (developers, end users, mixed)
- Frequency: ___
- Format: ___ (technical, user-friendly, marketing)

**Step 2: Handle Gaps**

If product name or audience missing:
→ Use `clarify()`: "Who is the primary audience for these release notes?"

**Step 3: Confirm Before Creating**

```
"I'll set up [frequency] release notes for [product], written for [audience]. Ready to create?"
```

**Step 4: Create & Offer Draft**

After confirmation: `create_deliverable()` → `respond()` with offer
{SKILL_TODO_TEMPLATE}
""",
    },

    "one-on-one-prep": {
        "name": "one-on-one-prep",
        "description": "Create a recurring 1:1 meeting prep deliverable",
        "trigger_patterns": ["1:1 prep", "one on one prep", "1-1 prep", "one-on-one", "meeting prep for"],
        "deliverable_type": "one_on_one_prep",
        "tier": "beta",
        "system_prompt_addition": f"""
---

## Active Skill: One-on-One Prep Creation (Beta)
{SKILL_PLAN_MODE_HEADER}

### Skill-Specific Flow

**Step 1: Parse & Check Context**

Extract from user message:
- Report/person name: ___
- Relationship: ___ (direct report, skip level, mentee)
- Frequency: ___
- Focus areas: ___

**Step 2: Handle Gaps**

If person's name or relationship missing:
→ Use `clarify()`: "What's your relationship with this person?"

**Step 3: Confirm Before Creating**

```
"I'll set up [frequency] 1:1 prep for your meetings with [name]. Ready to create?"
```

**Step 4: Create & Offer Draft**

After confirmation: `create_deliverable()` → `respond()` with offer
{SKILL_TODO_TEMPLATE}
""",
    },

    "client-proposal": {
        "name": "client-proposal",
        "description": "Create a recurring client proposal deliverable",
        "trigger_patterns": ["client proposal", "project proposal", "sow", "scope of work", "proposal for"],
        "deliverable_type": "client_proposal",
        "tier": "beta",
        "system_prompt_addition": f"""
---

## Active Skill: Client Proposal Creation (Beta)
{SKILL_PLAN_MODE_HEADER}

### Skill-Specific Flow

**Step 1: Parse & Check Context**

Extract from user message:
- Client name: ___
- Service/project type: ___
- Proposal type: ___ (new engagement, expansion, renewal)
- Include pricing: ___

**Step 2: Handle Gaps**

If client name or service type missing:
→ Use `clarify()`: "What type of proposal is this?"

**Step 3: Confirm Before Creating**

```
"I'll set up a proposal template for [client] covering [service type]. Ready to create?"
```

**Step 4: Create & Offer Draft**

After confirmation: `create_deliverable()` → `respond()` with offer
{SKILL_TODO_TEMPLATE}
""",
    },

    "performance-review": {
        "name": "performance-review",
        "description": "Create a recurring performance self-assessment deliverable",
        "trigger_patterns": ["performance review", "self assessment", "self-assessment", "quarterly review", "annual review"],
        "deliverable_type": "performance_self_assessment",
        "tier": "beta",
        "system_prompt_addition": f"""
---

## Active Skill: Performance Self-Assessment Creation (Beta)
{SKILL_PLAN_MODE_HEADER}

### Skill-Specific Flow

**Step 1: Parse & Check Context**

Extract from user message:
- Review period: ___ (quarterly, semi-annual, annual)
- Role level: ___
- Frequency: ___

**Step 2: Handle Gaps**

If review period missing:
→ Use `clarify()`: "What review period is this for?"

**Step 3: Confirm Before Creating**

```
"I'll set up a [period] self-assessment template. Ready to create?"
```

**Step 4: Create & Offer Draft**

After confirmation: `create_deliverable()` → `respond()` with offer
{SKILL_TODO_TEMPLATE}
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


# =============================================================================
# Hybrid Detection (ADR-040)
# =============================================================================

async def detect_skill_hybrid(user_message: str) -> Tuple[Optional[str], str, float]:
    """
    Hybrid skill detection: pattern matching first, semantic fallback.

    This provides the best of both approaches:
    - Pattern matching is fast and precise for known phrases
    - Semantic matching catches natural language variations

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
    # Import here to avoid circular dependency and lazy-load embeddings
    from services.skill_embeddings import detect_skill_semantic

    semantic_match, confidence = await detect_skill_semantic(user_message)
    if semantic_match:
        logger.info(f"Skill detected via semantic: {semantic_match} (confidence: {confidence:.3f})")
        return (semantic_match, "semantic", confidence)

    return (None, "none", 0.0)
