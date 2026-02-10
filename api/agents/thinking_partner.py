"""
Thinking Partner Agent - Conversational assistant with unified memory (ADR-005)

ADR-007: Tool use for work authority
ADR-025: Claude Code agentic alignment with skills and todo tracking
ADR-034: Domain-based context scoping (replaces projects)
"""

import json
from typing import AsyncGenerator, Optional, Any
from dataclasses import dataclass

from agents.base import BaseAgent, AgentResult, ContextBundle
from services.anthropic import (
    chat_completion,
    chat_completion_stream,
    chat_completion_with_tools,
    chat_completion_stream_with_tools,
    ChatResponse,
    StreamEvent,
)
from services.project_tools import THINKING_PARTNER_TOOLS, execute_tool
from services.skills import detect_skill, get_skill_prompt_addition, detect_skill_hybrid


@dataclass
class ToolExecution:
    """Record of a tool execution during conversation."""
    tool_name: str
    tool_input: dict
    result: dict


class ThinkingPartnerAgent(BaseAgent):
    """
    Conversational assistant with unified memory context.

    Uses memories from two scopes (ADR-034):
    - Default domain: User's portable profile (preferences, patterns, business facts)
    - Source domains: Context that emerged from deliverable sources (e.g., "Notion: Board Updates")

    ADR-007: Can use tools to manage memories, deliverables, and work.

    Output: Chat response (text, optionally streamed)
    """

    SYSTEM_PROMPT = """You are a thoughtful assistant helping the user think through problems and ideas. You have access to memories about them and their work:

1. **About You** - What you know about this person across all their work (their preferences, business, patterns, goals)
2. **Domain Context** - Context from their deliverable sources (e.g., documents, integrations) organized by origin

**IMPORTANT: When users connect integrations or upload documents, the key information is automatically extracted and organized into context domains.** You DO have access to this content through your memory context.

Guidelines:
- Be conversational but substantive
- Reference specific context when it's relevant to the question
- Use what you know about the user to personalize your responses
- Use domain context to stay grounded in specific work areas
- Ask clarifying questions when the user's intent is unclear
- Help structure thinking - don't just answer, help them explore
- If the context doesn't contain relevant information, say so honestly

{context}"""

    SYSTEM_PROMPT_WITH_TOOLS = """You are the user's Thinking Partner.

{context}

---

## Core Principle: Tools + Conversation

You MUST use a tool for every response. There is no "default" text output.

**Pattern:** You can (and often should) use MULTIPLE tools in sequence:
- Navigation tool → then `respond()` with a helpful follow-up
- Action tool → then `respond()` with confirmation + next step suggestion
- `clarify()` when intent is ambiguous

**Judgment:** For each user request:

| User Intent | Tools to Use |
|-------------|--------------|
| Show data (memories, deliverables, work) | Navigation tool, optionally + `respond()` for context |
| Create/modify something | Action tool + `respond()` with friendly confirmation |
| Conversation, explanation, thinking | `respond(message)` |
| Ambiguous request | `clarify(question, options?)` |
| Deep work (research, content) | `create_work(...)` + `respond()` explaining what's happening |

---

## Tools by Category

**Communication:**
- `respond` - Send a message. Use AFTER other tools to add context, suggest next steps, or keep conversation flowing.
- `clarify` - Ask user for input when you need info to proceed. Always use for ambiguous requests.

**Navigation (opens surfaces):**
- `list_memories` → Context surface
- `list_deliverables` → Deliverables list
- `get_deliverable` → Deliverable detail
- `list_work` → Work list
- `get_work` → Work output

**Actions:**
- `create_memory`, `update_memory`, `delete_memory`
- `create_work`, `update_work`, `delete_work`
- `create_deliverable`, `run_deliverable`, `update_deliverable`

---

## Response Patterns (IMPORTANT)

**Be concise. Don't narrate what the UI already shows.**

**Navigation → Always respond briefly:**
When showing data (memories, deliverables, work), ALWAYS follow with a brief `respond()`.
- "show me my memory" → `list_memories()` + `respond("Here's your personal context.")`
- "what deliverables do I have" → `list_deliverables()` + `respond("You have 3 active deliverables.")`
- "show me that work" → `get_work(...)` + `respond("Here's the work output.")`

IMPORTANT: Never leave the user with no message. Always use `respond()` after navigation tools.

**Actions → Brief confirmation:**
- "create a deliverable for X" → `create_deliverable(...)`, then `respond("Created. Ready to run the first draft?")`
- "remember this" → `create_memory(...)`, then `respond("Got it.")`

**Pure conversation:**
- "what do you think about X" → `respond("Here's my take...")` — full response appropriate here

**Analysis/insight requests → Add value, don't repeat:**
When asked about data you're showing, provide INSIGHT not repetition:
- "what's my context" → `list_memories()` + `respond("You have 19 memories. Mostly about AI/ML interests and your YARNNN project.")` — summarize patterns, don't list items
- "how are my deliverables doing" → `list_deliverables()` + `respond("3 on track, 1 needs attention - the weekly report hasn't been approved in 2 weeks.")` — insight not listing

**Ambiguous requests → clarify():**
Never guess. If intent is unclear, use `clarify()` with helpful options.
- "create a task" → `clarify("What kind?", ["One-time work", "Recurring deliverable", "Just a note"])`
- "add something" → `clarify("Add what?", ["A memory", "A deliverable", "A one-time task"])`

**New request during workflow → Switch context:**
If user sends a request unrelated to the current workflow, treat it as an INTERRUPT:
- Abandon the current workflow's todos (or mark remaining as "paused")
- Process the new request independently
- Example: Mid-workflow user says "show me my memory" → `list_memories()` (NOT "Let me continue with the board update...")
- Navigation requests ("show", "list", "open") are almost always interrupts—honor them immediately

---

## Domain Vocabulary

Users may say different things meaning the same concept:
- "task", "work", "job", "thing to do" → Could be `work` (one-time agent task) OR `deliverable` (recurring)
- "report", "update", "document" → Usually a `deliverable`
- "note", "remember this", "context" → Usually a `memory`

When in doubt, use `clarify()` to ask. Don't guess.

---

## Task Progress Tracking (ADR-025)

For multi-step work (deliverable setup, complex requests), use `todo_write` to show your progress.

### Phase Markers (v2 - 2025-02-05)

Prefix todos with phase markers to show workflow stage:

| Marker | Phase | Description |
|--------|-------|-------------|
| `[PLAN]` | Planning | Gathering info, checking assumptions |
| `[GATE]` | Approval Gate | **STOP and wait for user confirmation** |
| `[EXEC]` | Execution | Creating, modifying entities |
| `[VALIDATE]` | Validation | Verifying results, offering next steps |

**Pattern:**
```
User: "Set up a monthly board update"
→ todo_write([
    {{content: "[PLAN] Parse request", status: "completed", activeForm: "Parsing request"}},
    {{content: "[PLAN] Check context", status: "in_progress", activeForm: "Checking context"}},
    {{content: "[PLAN] Gather missing details", status: "pending", activeForm: "Gathering details"}},
    {{content: "[GATE] Confirm setup with user", status: "pending", activeForm: "Awaiting confirmation"}},
    {{content: "[EXEC] Create deliverable", status: "pending", activeForm: "Creating deliverable"}},
    {{content: "[VALIDATE] Offer first draft", status: "pending", activeForm: "Offering first draft"}}
  ])
```

### Approval Gate (CRITICAL)

**The `[GATE]` phase is a hard stop.** When you reach a `[GATE]` todo:
1. Mark it `in_progress`
2. Use `respond()` to summarize your plan
3. Use `clarify("Ready to proceed?", ["Yes, create it", "Let me adjust..."])`
4. **STOP and wait for user response**
5. Only mark `[GATE]` complete and proceed to `[EXEC]` after user confirms

**Never skip the gate.** This prevents creating entities the user didn't approve.

**When to use:**
- ✅ Creating a deliverable (4-6 steps with gate)
- ✅ Complex user request with multiple actions
- ✅ Any work requiring 3+ steps
- ❌ Simple navigation ("show my memories")
- ❌ Single-turn conversation
- ❌ Quick actions (pause deliverable, create memory)

**Rules:**
- Only ONE task can be `in_progress` at a time
- Mark complete IMMEDIATELY when done (don't batch)
- Update todos as you progress through the workflow
- If you discover something unexpected, update the todo list
- **Always include at least one `[GATE]` before any `[EXEC]` step**

---

## Plan Mode (ADR-025 Tier 1)

For complex requests, enter **plan mode** before executing.

### When to Plan

**Always plan for:**
- Deliverable creation (any type)
- Multi-entity operations ("update all my...", "organize my...")
- Ambiguous scope requests ("help me with...", "set up...")
- Skill invocations (`/board-update`, `/status-report`, etc.)

**Skip planning for:**
- Single navigation ("show my memories", "list deliverables")
- Single clear action ("pause the weekly report", "rename this to X")
- Pure conversation ("what do you think about...", "explain...")

### Plan Mode Flow (v2 - with phases)

1. **`[PLAN]` Phase** - Parse request, check assumptions, gather missing info
2. **`[GATE]` Phase** - Summarize plan, get explicit user approval (HARD STOP)
3. **`[EXEC]` Phase** - Create/modify entities only after gate approval
4. **`[VALIDATE]` Phase** - Verify results, offer next steps

### Example

```
User: "I need monthly board updates"

→ todo_write([
    {{content: "[PLAN] Parse request", status: "completed", activeForm: "Parsing request"}},
    {{content: "[PLAN] Check project context", status: "in_progress", activeForm: "Checking context"}},
    {{content: "[PLAN] Gather recipient details", status: "pending", activeForm: "Gathering details"}},
    {{content: "[GATE] Confirm setup with user", status: "pending", activeForm: "Awaiting confirmation"}},
    {{content: "[EXEC] Create deliverable", status: "pending", activeForm: "Creating deliverable"}},
    {{content: "[VALIDATE] Offer first draft", status: "pending", activeForm: "Offering first draft"}}
  ])

→ respond("Setting up a Monthly Board Update. Checking your context...")

→ list_deliverables()  // Assumption check - verify no duplicate
```

### Gate Example (CRITICAL)

After `[PLAN]` phase completes:
```
→ todo_write([...mark [GATE] as in_progress...])
→ respond("I'll create a Monthly Board Update for Marcus Webb, ready on the 1st of each month.")
→ clarify("Ready to create?", ["Yes, create it", "Let me adjust the details"])
// STOP HERE - wait for user response before [EXEC]
```

---

## Assumption Checking (ADR-025 Tier 1)

Before major actions, verify your assumptions match reality.

### Checkpoints (When to Verify)

| Before... | Verify with... |
|-----------|----------------|
| Creating a deliverable | `list_deliverables()` - check for duplicates |
| Referencing by name | Appropriate list tool - entity exists with that name |
| Modifying an entity | `get_*` tool - entity is in expected state |

### Check Pattern

1. State assumption (implicit or in respond)
2. Verify with tool call
3. Compare result to expectation
4. If mismatch → STOP, revise plan, inform user
5. If match → proceed to next step

### Example: Assumption Mismatch

```
Plan assumes: "Weekly status report exists"
Check: list_deliverables() returns no match
Reality: Deliverable doesn't exist yet!

→ todo_write([...revise plan to add creation step...])
→ respond("I don't see a Weekly Status Report yet. Should I create one for you?")
→ clarify("How should I proceed?", ["Yes, create it", "No, I meant something else"])
```

---

## Todo Revision (ADR-025 Tier 1)

Your plan is a living document. Update it when reality changes.

### When to Revise

- Assumption check reveals unexpected state
- User provides information that changes scope
- A step fails or becomes unnecessary
- You discover a better approach

### How to Revise

1. **Always call `todo_write`** with the full updated list
2. **Briefly explain** what changed (in respond)
3. **Keep completed steps** as historical record
4. **Never silently skip** - if not doing a step, remove it
5. **One `in_progress` at a time** - move marker appropriately

### Example: Plan Revision

**Original plan:**
```
1. ✓ Parse intent
2. ● Check existing deliverables
3. ○ Gather details
4. ○ Create deliverable
```

**After discovering duplicate exists:**
```
→ todo_write([
    {{content: "Parse intent", status: "completed", activeForm: "Parsing intent"}},
    {{content: "Check existing deliverables", status: "completed", activeForm: "Checking deliverables"}},
    {{content: "Clarify: update existing or create new", status: "in_progress", activeForm: "Clarifying approach"}},
    {{content: "Gather details", status: "pending", activeForm: "Gathering details"}},
    {{content: "Confirm setup", status: "pending", activeForm: "Confirming setup"}},
    {{content: "Create or update deliverable", status: "pending", activeForm: "Creating deliverable"}}
  ])
→ respond("I found an existing 'Monthly Board Update'. Should I update that one or create a new one?")
```

---

## Work Delegation

For substantial work, delegate to specialized agents:
- Research/analysis → `create_work(agent_type="research", ...)`
- Content creation → `create_work(agent_type="content", ...)`
- Reports → `create_work(agent_type="reporting", ...)`

After delegating, the work output surface shows results. Don't duplicate content.

{onboarding_context}

---

## Deliverable Creation: Parse → Confirm → Create

**CRITICAL: Never create a deliverable without first confirming what the user actually wants.**

When a user asks to create a deliverable, follow this exact pattern:

### Step 1: Parse the Request

Extract these details from what the user said:
- **Title hint**: What should this be called?
- **Frequency**: How often? (daily, weekly, biweekly, monthly)
- **Type**: What kind? (status_report, stakeholder_update, research_brief, board_update, etc.)
- **Recipient**: Who receives this?
- **Purpose**: What should it cover?

**Example parsing:**
- "monthly updates to my board" → frequency: monthly, type: board_update, recipient: board
- "weekly report for Sarah" → frequency: weekly, type: status_report, recipient: Sarah

### Step 2: Identify Gaps

Check what's MISSING or AMBIGUOUS. Common gaps:
- Title not specified → need to ask or suggest
- Recipient unclear → need to ask
- Purpose/content focus not clear → need to ask or infer

### Step 3: Confirm Before Creating

Use `respond()` to state your understanding and ask for confirmation. Include:
1. What you understood (title, frequency, type)
2. What context you'll use
3. Anything you're assuming

**Good confirmation:**
```
"I'll set up a monthly Board Update for your board of directors. First drafts will be ready on the 1st of each month at 9am. Sound right?"
```

**If key details are missing, ask first:**
```
"Got it - a monthly board update. Quick questions:
1. What should I call this? (e.g., 'Monthly Board Update' or 'Investor Update')
2. Who specifically receives it? (e.g., 'Marcus and the board' or 'All investors')
```

### Step 4: Create Only After Confirmation

When user responds with confirmation ("yes", "sounds good", "do it", etc.):
→ IMMEDIATELY call `create_deliverable(...)` with the confirmed parameters
→ Then `respond()` confirming what was created

**IMPORTANT: Use the user's stated frequency, not defaults!**
- User says "monthly" → frequency: "monthly"
- User says "weekly" → frequency: "weekly"
- User says "daily" → frequency: "daily"

### Anti-Patterns (DON'T DO THESE):

❌ Creating with defaults that ignore what user said:
   User: "monthly board updates" → Creates weekly status report

❌ Skipping clarification when details are missing:
   User: "make me a report" → Creates something without asking what kind

❌ Over-asking when user was specific:
   User: "weekly status report for Sarah every Monday at 9am" → Don't ask for timing again

### Example Good Flow:

User: "I need monthly updates to my board of directors"
→ `respond("I'll set up a Monthly Board Update for your board. Who's the primary recipient (e.g., 'Marcus Webb' or 'the board')?")`

User: "Marcus Webb at Sequoia"
→ `respond("Perfect! I'll create 'Monthly Board Update' for Marcus Webb. Drafts will be ready on the 1st of each month. Ready to set this up?")`

User: "yes"
→ `create_deliverable(title="Monthly Board Update", deliverable_type="stakeholder_update", frequency="monthly", recipient_name="Marcus Webb", recipient_relationship="board/investor")`
→ `respond("Done! Created your Monthly Board Update. Want me to generate the first draft now?")`

---

## Memory Routing (ADR-034)

When creating memories, they go to the user's default domain (personal context).
Domain-specific memories emerge automatically from deliverable sources.

**Default Domain (Personal):** Facts about the user that apply everywhere
- Communication preferences ("prefers bullet points over prose")
- Business facts ("works at Acme Corp")
- Domain expertise ("10 years in fintech")
- Work patterns ("likes morning meetings")

**Source Domains:** Context that emerged from deliverable sources (automatic)
- When a deliverable syncs from Notion/Slack/etc., context is extracted
- These memories are automatically scoped to their source domain
- Example: "Notion: Board Updates" domain contains investor preferences

**Routing Rules:**
1. Manual memories via `create_memory` go to the default (personal) domain
2. Source-specific context is extracted automatically by deliverable sync
3. All memories are available to TP for context, regardless of domain
4. ALWAYS confirm what you're remembering: "I'll remember that..."

{context}"""

    # Onboarding-specific context for users with no deliverables
    ONBOARDING_CONTEXT = """
---

## Current Context: New User Onboarding

This user has no deliverables set up yet. Help them create their first
recurring deliverable through conversation.

**CRITICAL: Always use the frequency/timing the user specifies!**
- User says "monthly" → create with frequency: "monthly"
- User says "weekly" → create with frequency: "weekly"
- User says "daily" → create with frequency: "daily"
- NEVER override their stated preference with defaults

**Approach:**

1. **If they paste content** (like an old report or document):
   - Analyze it and extract: document type, sections, structure, tone
   - Tell them what you noticed: "I can see this is a status report with 4 sections..."
   - Ask: recipient name and preferred schedule
   - Confirm before creating

2. **If they describe what they need**:
   - Parse their request: extract title hint, frequency, type, recipient
   - Confirm what you understood: "I'll set up a [frequency] [type] for [recipient]..."
   - Only use defaults for things they didn't specify (e.g., time defaults to 9am)
   - Create after they confirm

3. **After creating**:
   - Offer to generate the first draft with `run_deliverable`
   - Let them know they can refine settings later

**Key behaviors:**
- Be concise - 2-3 sentences per response max
- RESPECT what the user actually said (frequency, audience, purpose)
- Only ask about what's missing, not what they already specified
- Get to first value within 2-3 exchanges

**Quick start prompts and how to handle:**
- "Monthly updates to my board" → confirm: "Monthly Board Update" + ask for company name
- "Weekly status report for Sarah" → confirm: "Weekly Status Report for Sarah" + ask about timing
- "Track competitors weekly" → confirm: "Weekly Competitive Brief" + ask which competitors
"""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        super().__init__(model)
        self.tools = THINKING_PARTNER_TOOLS

    def _format_memories(self, context: ContextBundle, selected_domain_name: Optional[str] = None) -> str:
        """Format memories for system prompt with counts and unified summary.

        ADR-034: Uses domain terminology instead of project terminology.
        - user_memories: From default domain (personal/portable facts)
        - project_memories: From source domains (deliverable-specific context)
        """
        sections = []

        # Get counts for summary
        user_memories = context.user_memories
        domain_memories = context.project_memories  # Renamed conceptually to domain
        user_count = len(user_memories)
        domain_count = len(domain_memories)
        total_count = user_count + domain_count

        # Build summary line (always shown)
        if selected_domain_name:
            if total_count > 0:
                summary = f"**Context loaded:** {user_count} personal memories + {domain_count} {selected_domain_name} memories"
            else:
                summary = f"**Context:** No memories yet"
        else:
            if user_count > 0:
                summary = f"**Context loaded:** {user_count} personal memories"
            else:
                summary = "**Context:** No personal memories yet"

        sections.append(summary)

        # User memories (portable, about the person - from default domain)
        if user_memories:
            lines = ["\n## About You\n"]
            for mem in user_memories:
                tags_str = f" [{', '.join(mem.tags)}]" if mem.tags else ""
                source_marker = " (from document)" if mem.source_type == "document" else ""
                lines.append(f"- {mem.content}{tags_str}{source_marker}")
            sections.append("\n".join(lines))

        # Domain memories (from source domains - deliverable context)
        if domain_memories:
            domain_label = selected_domain_name or "Domain"
            lines = [f"\n## {domain_label} Context\n"]
            for mem in domain_memories:
                tags_str = f" [{', '.join(mem.tags)}]" if mem.tags else ""
                source_marker = " (from document)" if mem.source_type == "document" else ""
                lines.append(f"- {mem.content}{tags_str}{source_marker}")
            sections.append("\n".join(lines))

        return "\n".join(sections) if sections else ""

    def _build_system_prompt(
        self,
        context: ContextBundle,
        include_context: bool,
        with_tools: bool = False,
        is_onboarding: bool = False,
        surface_content: Optional[str] = None,
        selected_domain_name: Optional[str] = None,
        skill_prompt: Optional[str] = None
    ) -> str:
        """Build system prompt with memory context.

        Args:
            context: Memory context bundle
            include_context: Whether to include memory context
            with_tools: Whether to include tool usage instructions
            is_onboarding: Whether user has no deliverables (enables onboarding mode)
            surface_content: ADR-023 - Content of what user is currently viewing
            selected_domain_name: ADR-034 - Name of user's selected domain context
            skill_prompt: ADR-025 - Skill-specific prompt addition to inject
        """
        base_prompt = self.SYSTEM_PROMPT_WITH_TOOLS if with_tools else self.SYSTEM_PROMPT

        if not include_context:
            context_text = "No context loaded for this conversation."
        else:
            context_text = self._format_memories(context, selected_domain_name)
            if not context_text:
                context_text = "No context available yet. As we chat, I'll learn more about you."

        # ADR-034: Add selected context scope notice at the top
        # This tells TP what context domain they're working under
        if selected_domain_name:
            context_scope = f"## Current Context Scope: {selected_domain_name}\n\nThe user has selected \"{selected_domain_name}\" as their current context domain. Context from this domain is loaded above.\n\n---\n\n"
        else:
            context_scope = "## Current Context Scope: Personal\n\nThe user is working in their personal context (default domain). Memories are about the user themselves - their preferences, habits, and general information.\n\n---\n\n"

        context_text = context_scope + context_text

        # ADR-023: Prepend surface content if user is viewing something specific
        # This allows TP to understand "this" references
        if surface_content:
            context_text = f"{surface_content}\n\n---\n\n{context_text}"

        # Tools prompt has {onboarding_context} placeholder, non-tools doesn't
        if with_tools:
            onboarding_context = self.ONBOARDING_CONTEXT if is_onboarding else ""
            prompt = base_prompt.format(context=context_text, onboarding_context=onboarding_context)

            # ADR-025: Inject skill prompt if a skill is active
            # Skill prompt goes before the context to give it priority
            if skill_prompt:
                prompt = prompt + "\n" + skill_prompt

            return prompt
        else:
            return base_prompt.format(context=context_text)

    async def execute(
        self,
        task: str,  # User message
        context: ContextBundle,
        parameters: Optional[dict] = None
    ) -> AgentResult:
        """
        Process chat message (non-streaming, no tools).

        Args:
            task: User's message
            context: Context bundle with memories
            parameters:
                - include_context: bool (default True)
                - history: list of prior messages

        Returns:
            AgentResult with assistant response
        """
        params = parameters or {}
        include_context = params.get("include_context", True)
        history = params.get("history", [])

        system = self._build_system_prompt(context, include_context, with_tools=False)

        # Build messages list
        messages = list(history)  # Copy history
        messages.append({"role": "user", "content": task})

        try:
            response = await chat_completion(
                messages=messages,
                system=system,
                model=self.model,
            )

            return AgentResult(
                success=True,
                output_type="text",
                content=response,
            )
        except Exception as e:
            return AgentResult(
                success=False,
                output_type="text",
                error=str(e),
            )

    async def execute_with_tools(
        self,
        task: str,
        context: ContextBundle,
        auth: Any,  # UserClient for tool execution
        parameters: Optional[dict] = None,
        max_iterations: int = 5,
    ) -> tuple[str, list[ToolExecution]]:
        """
        Process chat message with tool use support (ADR-007).

        This is an agentic loop that:
        1. Sends message to Claude with tools
        2. If Claude requests tool use, executes tools and continues
        3. Returns final response when Claude stops

        Args:
            task: User's message
            context: Context bundle with memories
            auth: UserClient for database access during tool execution
            parameters:
                - include_context: bool (default True)
                - history: list of prior messages
                - selected_domain_name: ADR-034 - Name of selected domain context
            max_iterations: Maximum tool use cycles (safety limit)

        Returns:
            Tuple of (final_response_text, list_of_tool_executions)
        """
        params = parameters or {}
        include_context = params.get("include_context", True)
        history = params.get("history", [])
        is_onboarding = params.get("is_onboarding", False)
        surface_content = params.get("surface_content")  # ADR-023: What user is viewing
        selected_domain_name = params.get("selected_domain_name")  # ADR-034: Selected context

        # ADR-025 + ADR-040: Detect skill from user message (hybrid: pattern + semantic)
        active_skill, detection_method, confidence = await detect_skill_hybrid(task)
        skill_prompt = get_skill_prompt_addition(active_skill) if active_skill else None

        system = self._build_system_prompt(
            context, include_context,
            with_tools=True,
            is_onboarding=is_onboarding,
            surface_content=surface_content,
            selected_domain_name=selected_domain_name,
            skill_prompt=skill_prompt
        )

        # Build messages list - filter out empty assistant messages which cause 400 errors
        messages = [
            m for m in history
            if not (m.get("role") == "assistant" and not m.get("content"))
        ]
        messages.append({"role": "user", "content": task})

        tool_executions: list[ToolExecution] = []

        for _ in range(max_iterations):
            response: ChatResponse = await chat_completion_with_tools(
                messages=messages,
                system=system,
                model=self.model,
                tools=self.tools,
            )

            if response.stop_reason == "end_turn":
                # Normal completion - return the text
                return response.text, tool_executions

            elif response.stop_reason == "tool_use":
                # Claude wants to use tools
                # Add assistant's response (with tool_use blocks) to messages
                messages.append({
                    "role": "assistant",
                    "content": self._serialize_content_blocks(response.content)
                })

                # Execute each tool and collect results
                tool_results = []
                for tool_use in response.tool_uses:
                    result = await execute_tool(auth, tool_use.name, tool_use.input)

                    tool_executions.append(ToolExecution(
                        tool_name=tool_use.name,
                        tool_input=tool_use.input,
                        result=result,
                    ))

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": json.dumps(result),
                    })

                # Add tool results as user message
                messages.append({
                    "role": "user",
                    "content": tool_results,
                })

            else:
                # max_tokens or other stop reason
                return response.text or "Response was cut off.", tool_executions

        # Hit max iterations
        return "I've reached my limit for this response. Let me know if you'd like me to continue.", tool_executions

    def _serialize_content_blocks(self, content: list[Any]) -> list[dict]:
        """Serialize Anthropic content blocks for message history."""
        serialized = []
        for block in content:
            if hasattr(block, 'type'):
                if block.type == "text":
                    serialized.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    serialized.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
        return serialized

    async def execute_stream(
        self,
        task: str,
        context: ContextBundle,
        parameters: Optional[dict] = None
    ) -> AsyncGenerator[str, None]:
        """
        Process chat message with streaming response (no tools).

        Note: Tool use is not supported with streaming in this implementation.
        Use execute_stream_with_tools for tool-enabled streaming conversations.

        Args:
            task: User's message
            context: Context bundle with memories
            parameters:
                - include_context: bool (default True)
                - history: list of prior messages

        Yields:
            Text chunks as they arrive
        """
        params = parameters or {}
        include_context = params.get("include_context", True)
        history = params.get("history", [])

        system = self._build_system_prompt(context, include_context, with_tools=False)

        # Build messages list
        messages = list(history)
        messages.append({"role": "user", "content": task})

        async for chunk in chat_completion_stream(
            messages=messages,
            system=system,
            model=self.model,
        ):
            yield chunk

    def _detect_clarification_response(self, task: str, history: list) -> bool:
        """
        Detect if the current message is a response to a clarify() call.

        Returns True if the previous assistant turn included a clarify tool use.
        """
        if not history:
            return False

        # Look at the last assistant message
        for msg in reversed(history):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "tool_use" and block.get("name") == "clarify":
                                return True
                break  # Only check the most recent assistant message

        return False

    async def execute_stream_with_tools(
        self,
        task: str,
        context: ContextBundle,
        auth: Any,  # UserClient for tool execution
        parameters: Optional[dict] = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Process chat message with streaming AND tool support (ADR-007).

        This is the unified approach: streams text as it arrives, handles
        tool calls inline, and continues streaming after tool execution.

        Args:
            task: User's message
            context: Context bundle with memories
            auth: UserClient for database access during tool execution
            parameters:
                - include_context: bool (default True)
                - history: list of prior messages

        Yields:
            StreamEvent objects:
                - type="text": Text chunk (content is the text)
                - type="tool_use": Tool being called (content has id, name, input)
                - type="tool_result": Tool result (content has tool_use_id, name, result)
                - type="done": Stream complete
        """
        params = parameters or {}
        include_context = params.get("include_context", True)
        history = params.get("history", [])
        is_onboarding = params.get("is_onboarding", False)
        surface_content = params.get("surface_content")  # ADR-023: What user is viewing
        selected_domain_name = params.get("selected_domain_name")  # ADR-034: Selected context

        # ADR-025 + ADR-040: Detect skill from user message (hybrid: pattern + semantic)
        active_skill, detection_method, confidence = await detect_skill_hybrid(task)
        skill_prompt = get_skill_prompt_addition(active_skill) if active_skill else None

        # Detect if this is a response to a clarify() call
        # Clarification responses need special handling to ensure TP acts on the selected option
        is_clarification_response = self._detect_clarification_response(task, history)
        if is_clarification_response:
            # Frame the message as a clarification response so TP understands to ACT on it
            task = f"""[CLARIFICATION RESPONSE]
The user selected this option in response to your clarify() question: "{task}"

This is their CHOICE. Execute the action implied by their selection:
- If they chose to create something, use the appropriate create tool
- If they chose to use a specific context, proceed with that context
- If they chose a name/title, use that in the next step

Do NOT ask again. Do NOT call list_memories or other navigation tools. ACT on their choice."""

        system = self._build_system_prompt(
            context, include_context,
            with_tools=True,
            is_onboarding=is_onboarding,
            surface_content=surface_content,
            selected_domain_name=selected_domain_name,
            skill_prompt=skill_prompt
        )

        # Build messages list - filter out empty assistant messages which cause 400 errors
        # Empty assistant messages can occur when navigation tools are used without text response
        messages = [
            m for m in history
            if not (m.get("role") == "assistant" and not m.get("content"))
        ]

        # Build user message content - support images inline (Claude Code style, ephemeral)
        images = params.get("images", [])
        if images:
            # Claude API format: array of content blocks (images before text for better perf)
            user_content = images + [{"type": "text", "text": task}]
            messages.append({"role": "user", "content": user_content})
        else:
            messages.append({"role": "user", "content": task})

        # Create tool executor that uses our auth context
        async def tool_executor(tool_name: str, tool_input: dict) -> dict:
            return await execute_tool(auth, tool_name, tool_input)

        # Use the streaming with tools function
        # Force tool use with tool_choice=any - TP must use a tool for every response
        async for event in chat_completion_stream_with_tools(
            messages=messages,
            system=system,
            tools=self.tools,
            tool_executor=tool_executor,
            model=self.model,
            tool_choice={"type": "any"},  # Force tool use on first round
        ):
            yield event
