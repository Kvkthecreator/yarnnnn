"""
Thinking Partner Agent - Conversational assistant with unified memory (ADR-005)

ADR-007: Tool use for project authority
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


@dataclass
class ToolExecution:
    """Record of a tool execution during conversation."""
    tool_name: str
    tool_input: dict
    result: dict


class ThinkingPartnerAgent(BaseAgent):
    """
    Conversational assistant with unified memory context.

    Uses memories from two scopes:
    - User memories: What YARNNN knows about the user (portable across projects)
    - Project memories: What's specific to this project

    ADR-007: Can use tools to query and manage projects.

    Output: Chat response (text, optionally streamed)
    """

    SYSTEM_PROMPT = """You are a thoughtful assistant helping the user think through problems and ideas. You have access to memories about them and their work:

1. **About You** - What you know about this person across all their work (their preferences, business, patterns, goals)
2. **Project Context** - What's specific to this current project (requirements, facts, guidelines, and document contents)

**IMPORTANT: When users upload or attach documents, the key information from those documents is automatically extracted and included in your Project Context above.** You DO have access to uploaded document contents through your memory context.

Guidelines:
- Be conversational but substantive
- Reference specific context when it's relevant to the question
- Use what you know about the user to personalize your responses
- Use project context to stay grounded in this specific work
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
| Show data (memories, projects, work) | Navigation tool, optionally + `respond()` for context |
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
- `list_projects` → Projects list

**Actions:**
- `create_project`, `rename_project`, `update_project`
- `create_memory`, `update_memory`, `delete_memory`
- `create_work`, `update_work`, `delete_work`
- `create_deliverable`, `run_deliverable`, `update_deliverable`

---

## Response Patterns (IMPORTANT)

**Navigation → ALWAYS follow with respond():**
Every navigation tool MUST be followed by `respond()` to provide context. Never navigate silently.
- "show me my memory" → `list_memories()`, then `respond("Here's everything I remember about you. Want to add something?")`
- "what deliverables do I have" → `list_deliverables()`, then `respond("You have 3 active deliverables. The weekly report is due tomorrow.")`
- "open that project" → `get_project(...)`, then `respond("Here's the project. What would you like to do with it?")`

**Actions → ALWAYS confirm with respond():**
Every action tool MUST be followed by `respond()` with confirmation and suggested next step.
- "create a project for X" → `create_project(...)`, then `respond("Done! Want to add some context or create a deliverable for it?")`
- "remember this" → `create_memory(...)`, then `respond("Got it, I'll remember that. Anything else?")`

**Pure conversation:**
- "what do you think about X" → `respond("Here's my take on X...")`

**Ambiguous requests → ALWAYS clarify():**
Never guess. If intent is unclear, use `clarify()` with helpful options.
- "create a task" → `clarify("What kind of task?", ["One-time work item", "Recurring deliverable (like a weekly report)", "Just a reminder/note"])`
- "add something" → `clarify("What would you like to add?", ["A memory/note for me to remember", "A new project", "A new deliverable"])`
- "help me with this" → `clarify("What would you like help with?", [...relevant options...])`

---

## Domain Vocabulary

Users may say different things meaning the same concept:
- "task", "work", "job", "thing to do" → Could be `work` (one-time agent task) OR `deliverable` (recurring)
- "report", "update", "document" → Usually a `deliverable`
- "note", "remember this", "context" → Usually a `memory`
- "project", "workspace", "area" → A `project`

When in doubt, use `clarify()` to ask. Don't guess.

---

## Work Delegation

For substantial work, delegate to specialized agents:
- Research/analysis → `create_work(agent_type="research", ...)`
- Content creation → `create_work(agent_type="content", ...)`
- Reports → `create_work(agent_type="reporting", ...)`

After delegating, the work output surface shows results. Don't duplicate content.

{onboarding_context}

---

## Deliverable Creation: Context Assurance Pattern

When creating a deliverable, state the context you'll use and wait for confirmation before creating.

**The Pattern:**

1. **Infer the context** - Based on conversation, existing projects, or user's current surface
2. **State it explicitly** - "I'll use your [X] context for this. Ready to create it?"
3. **Wait for confirmation** - User says yes/ok/sounds good/let's do it
4. **Create immediately** - Call `create_deliverable(...)` right away after confirmation

**Recognizing Confirmation:**

When user responds with ANY of these, IMMEDIATELY call `create_deliverable`:
- "ok" / "okay" / "yes" / "sure" / "sounds good" / "let's do it" / "go ahead"
- "that works" / "perfect" / "do it" / "create it" / "set it up"
- Any affirmative response that doesn't explicitly change the context

DO NOT ask additional clarifying questions after user confirms. Just create the deliverable.

**Example Flow:**

User: "I need a weekly report for the board"
→ `respond("I'll set up a weekly board report using your TechStart Board context - that includes your investor updates and quarterly metrics. Ready to create it?")`

User: "ok, let's do that"
→ `create_deliverable(...)` ← IMMEDIATELY create, don't clarify again!

**When context is ambiguous (ONLY if you truly don't know):**

If user has multiple relevant contexts and hasn't indicated which:
→ `clarify("Which context should I use for this?", ["TechStart Board", "Personal context", "Create new"])`

**After creation - always state what was used:**

→ `respond("Done! I've created 'Weekly Board Update' using your TechStart Board context. First draft will be ready Monday at 9am.")`

---

## Memory Routing (ADR-024)

When creating or extracting memories, ALWAYS determine the appropriate scope:

**User-scoped (Personal):** Facts about the user that apply everywhere
- Communication preferences ("prefers bullet points over prose")
- Business facts ("works at Acme Corp")
- Domain expertise ("10 years in fintech")
- Work patterns ("likes morning meetings")

**Project-scoped:** Information specific to one initiative
- Requirements ("report needs 3 sections")
- Deadlines ("due Tuesday")
- Client details ("client prefers formal tone")
- Task-specific context

**Routing Rules:**
1. If user is viewing/working in a project, default to that project
2. If content clearly applies across all work, use Personal
3. When uncertain, use `clarify()`: "Should I save this to your personal context or to [Project Name]?"
4. ALWAYS state your routing decision: "I'll save this to [Personal/Project Name]..."

Use `suggest_project_for_memory` when you need help determining the best project.

---

## Project Guidelines

- `list_projects` first when user mentions project by name
- Create projects only when explicitly asked or distinct topic emerges
- Keep names short (2-5 words)

{context}"""

    # Onboarding-specific context for users with no deliverables
    ONBOARDING_CONTEXT = """
---

## Current Context: New User Onboarding

This user has no deliverables set up yet. Your primary goal is to help them
create their first recurring deliverable through conversation.

**Approach:**

1. **If they paste content** (like an old report or document):
   - Analyze it and extract: document type, sections, structure, tone, typical length
   - Tell them what you noticed: "I can see this is a weekly status report with 4 sections..."
   - Ask 1-2 quick questions: recipient name and preferred timing
   - Use `create_deliverable` to set it up

2. **If they describe what they need**:
   - Ask 1-2 clarifying questions maximum: who receives it, when should drafts be ready
   - Use sensible defaults (weekly, Monday 9am, professional tone)
   - Create the deliverable quickly - don't over-configure

3. **After creating**:
   - Offer to generate the first draft immediately with `run_deliverable`
   - Let them know they can refine settings later

**Key behaviors:**
- Be concise - 2-3 sentences per response max
- Extract structure from examples rather than asking users to define it
- Get to first value (created deliverable) within 2-3 exchanges
- Don't ask for information you can infer or use defaults for

**Quick start prompts the user might send:**
- "Weekly status report for my manager" → ask for manager's name and timing
- "Monthly investor update" → ask about company/project name and timing
- "Track competitors weekly" → ask which competitors to monitor
"""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        super().__init__(model)
        self.tools = THINKING_PARTNER_TOOLS

    def _format_memories(self, context: ContextBundle, selected_project_name: Optional[str] = None) -> str:
        """Format memories for system prompt with counts and unified summary."""
        sections = []

        # Get counts for summary
        user_memories = context.user_memories
        project_memories = context.project_memories
        user_count = len(user_memories)
        project_count = len(project_memories)
        total_count = user_count + project_count

        # Build summary line (always shown)
        if selected_project_name:
            if total_count > 0:
                summary = f"**Context loaded:** {user_count} personal memories + {project_count} {selected_project_name} memories"
            else:
                summary = f"**Context:** No memories yet for Personal or {selected_project_name}"
        else:
            if user_count > 0:
                summary = f"**Context loaded:** {user_count} personal memories"
            else:
                summary = "**Context:** No personal memories yet"

        sections.append(summary)

        # User memories (portable, about the person)
        if user_memories:
            lines = ["\n## About You\n"]
            for mem in user_memories:
                tags_str = f" [{', '.join(mem.tags)}]" if mem.tags else ""
                source_marker = " (from document)" if mem.source_type == "document" else ""
                lines.append(f"- {mem.content}{tags_str}{source_marker}")
            sections.append("\n".join(lines))

        # Project memories (task-specific)
        if project_memories:
            project_label = selected_project_name or "Project"
            lines = [f"\n## {project_label} Context\n"]
            for mem in project_memories:
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
        selected_project_name: Optional[str] = None
    ) -> str:
        """Build system prompt with memory context.

        Args:
            context: Memory context bundle
            include_context: Whether to include memory context
            with_tools: Whether to include tool usage instructions
            is_onboarding: Whether user has no deliverables (enables onboarding mode)
            surface_content: ADR-023 - Content of what user is currently viewing
            selected_project_name: ADR-024 - Name of user's selected project context
        """
        base_prompt = self.SYSTEM_PROMPT_WITH_TOOLS if with_tools else self.SYSTEM_PROMPT

        if not include_context:
            context_text = "No context loaded for this conversation."
        else:
            context_text = self._format_memories(context, selected_project_name)
            if not context_text:
                context_text = "No context available yet. As we chat, I'll learn more about you and this project."

        # ADR-024: Add selected context scope notice at the top
        # This tells TP what context basket they're working under
        if selected_project_name:
            context_scope = f"## Current Context Scope: {selected_project_name}\n\nThe user has selected \"{selected_project_name}\" as their current context. When they ask about context, refer to this. New memories and deliverables should default to this project.\n\n---\n\n"
        else:
            context_scope = "## Current Context Scope: Personal\n\nThe user is working in their personal context (no specific project selected). Memories are about the user themselves - their preferences, habits, and general information.\n\n---\n\n"

        context_text = context_scope + context_text

        # ADR-023: Prepend surface content if user is viewing something specific
        # This allows TP to understand "this" references
        if surface_content:
            context_text = f"{surface_content}\n\n---\n\n{context_text}"

        # Tools prompt has {onboarding_context} placeholder, non-tools doesn't
        if with_tools:
            onboarding_context = self.ONBOARDING_CONTEXT if is_onboarding else ""
            return base_prompt.format(context=context_text, onboarding_context=onboarding_context)
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
                - selected_project_name: ADR-024 - Name of selected project context
            max_iterations: Maximum tool use cycles (safety limit)

        Returns:
            Tuple of (final_response_text, list_of_tool_executions)
        """
        params = parameters or {}
        include_context = params.get("include_context", True)
        history = params.get("history", [])
        is_onboarding = params.get("is_onboarding", False)
        surface_content = params.get("surface_content")  # ADR-023: What user is viewing
        selected_project_name = params.get("selected_project_name")  # ADR-024: Selected context

        system = self._build_system_prompt(
            context, include_context,
            with_tools=True,
            is_onboarding=is_onboarding,
            surface_content=surface_content,
            selected_project_name=selected_project_name
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
        selected_project_name = params.get("selected_project_name")  # ADR-024: Selected context

        system = self._build_system_prompt(
            context, include_context,
            with_tools=True,
            is_onboarding=is_onboarding,
            surface_content=surface_content,
            selected_project_name=selected_project_name
        )

        # Build messages list - filter out empty assistant messages which cause 400 errors
        # Empty assistant messages can occur when navigation tools are used without text response
        messages = [
            m for m in history
            if not (m.get("role") == "assistant" and not m.get("content"))
        ]
        messages.append({"role": "user", "content": task})

        # Create tool executor that uses our auth context
        async def tool_executor(tool_name: str, tool_input: dict) -> dict:
            return await execute_tool(auth, tool_name, tool_input)

        # Use the streaming with tools function
        async for event in chat_completion_stream_with_tools(
            messages=messages,
            system=system,
            tools=self.tools,
            tool_executor=tool_executor,
            model=self.model,
        ):
            yield event
