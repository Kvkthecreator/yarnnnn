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

## Core Principle: Every Output is a Tool

You MUST use a tool for every response. There is no "default" text output.

**Judgment:** For each user request, choose ONE action:

| User Intent | Tool |
|-------------|------|
| Conversation, explanation, thinking | `respond(message)` |
| Need more info before acting | `clarify(question, options?)` |
| Show data (memories, projects, work) | Navigation tools → opens surface |
| Create/modify something | Action tools |
| Deep work (research, content) | `create_work(...)` |

---

## Tools by Category

**Communication:**
- `respond` - Send a message (use for explanations, answers, thinking aloud)
- `clarify` - Ask user for input (use when you need info to proceed)

**Navigation (opens surfaces - NO text summary needed):**
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

## Response Rules

**Navigation tools:** The UI shows the data. Say nothing or one short acknowledgment.
- "show me my memory" → `list_memories` (surface shows data, you say nothing extra)
- "what deliverables do I have" → `list_deliverables` (surface shows them)

**Action tools:** Brief confirmation only.
- "create a project for X" → `create_project` then `respond("Created.")`

**Conversation:** Use `respond` with your full message.
- "what do you think about X" → `respond("Here's my take on X...")`

**Need clarity:** Use `clarify`.
- "add this to my project" → `clarify("Which project?", ["Project A", "Project B"])`

---

## Work Delegation

For substantial work, delegate to specialized agents:
- Research/analysis → `create_work(agent_type="research", ...)`
- Content creation → `create_work(agent_type="content", ...)`
- Reports → `create_work(agent_type="reporting", ...)`

After delegating, the work output surface shows results. Don't duplicate content.

{onboarding_context}

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

    def _format_memories(self, context: ContextBundle) -> str:
        """Format memories for system prompt."""
        sections = []

        # User memories (portable, about the person)
        user_memories = context.user_memories
        if user_memories:
            lines = ["## About You\n"]
            for mem in user_memories:
                tags_str = f" [{', '.join(mem.tags)}]" if mem.tags else ""
                source_marker = " (from document)" if mem.source_type == "document" else ""
                lines.append(f"- {mem.content}{tags_str}{source_marker}")
            sections.append("\n".join(lines))

        # Project memories (task-specific)
        project_memories = context.project_memories
        if project_memories:
            lines = ["## Project Context\n"]
            for mem in project_memories:
                tags_str = f" [{', '.join(mem.tags)}]" if mem.tags else ""
                source_marker = " (from document)" if mem.source_type == "document" else ""
                lines.append(f"- {mem.content}{tags_str}{source_marker}")
            sections.append("\n".join(lines))

        return "\n\n".join(sections) if sections else ""

    def _build_system_prompt(
        self,
        context: ContextBundle,
        include_context: bool,
        with_tools: bool = False,
        is_onboarding: bool = False,
        surface_content: Optional[str] = None
    ) -> str:
        """Build system prompt with memory context.

        Args:
            context: Memory context bundle
            include_context: Whether to include memory context
            with_tools: Whether to include tool usage instructions
            is_onboarding: Whether user has no deliverables (enables onboarding mode)
            surface_content: ADR-023 - Content of what user is currently viewing
        """
        base_prompt = self.SYSTEM_PROMPT_WITH_TOOLS if with_tools else self.SYSTEM_PROMPT

        if not include_context:
            context_text = "No context loaded for this conversation."
        else:
            context_text = self._format_memories(context)
            if not context_text:
                context_text = "No context available yet. As we chat, I'll learn more about you and this project."

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
            max_iterations: Maximum tool use cycles (safety limit)

        Returns:
            Tuple of (final_response_text, list_of_tool_executions)
        """
        params = parameters or {}
        include_context = params.get("include_context", True)
        history = params.get("history", [])
        is_onboarding = params.get("is_onboarding", False)
        surface_content = params.get("surface_content")  # ADR-023: What user is viewing

        system = self._build_system_prompt(
            context, include_context,
            with_tools=True,
            is_onboarding=is_onboarding,
            surface_content=surface_content
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

        system = self._build_system_prompt(
            context, include_context,
            with_tools=True,
            is_onboarding=is_onboarding,
            surface_content=surface_content
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
