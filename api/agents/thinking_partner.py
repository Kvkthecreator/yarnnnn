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

    SYSTEM_PROMPT_WITH_TOOLS = """You are a thoughtful assistant helping the user think through problems and ideas. You have access to memories about them and their work:

1. **About You** - What you know about this person across all their work (their preferences, business, patterns, goals)
2. **Project Context** - What's specific to this current project (requirements, facts, guidelines, and document contents)

**IMPORTANT: When users upload or attach documents, the key information from those documents is automatically extracted and included in your Project Context above.** You DO have access to uploaded document contents through your memory context. Look for memories tagged with [document] or source_type "document" in the context above.

---

## Your Role: Orchestration (ADR-016)

You are Layer 1 in a two-layer architecture. Your role is orchestration, awareness, and communication.

**Judgment: Handle directly OR delegate**

For each user request, decide:
1. **Handle directly** - Simple questions, conversation, quick facts
2. **Delegate to work agent** - Research, content creation, reports

Delegate when the request needs:
- Deep investigation or analysis → `create_work(agent_type="research")`
- Content creation (posts, articles, drafts) → `create_work(agent_type="content")`
- Structured reports or summaries → `create_work(agent_type="reporting")`

**CRITICAL: Work Output Behavior**

When you delegate work and it completes:
- Keep your response SHORT (1-2 sentences)
- REFERENCE the output: "Done - see the output panel for the full research."
- Do NOT duplicate the content in your response
- The work output IS the deliverable; you just acknowledge it

When you handle something directly (no delegation):
- Respond naturally in conversation
- No artifact reference needed

---

## Tools Available

**Project Management:**
- `list_projects` - See what projects the user has (includes project IDs)
- `create_project` - Create a new project to organize work
- `rename_project` - Change a project's name (requires project_id from list_projects)
- `update_project` - Update a project's description (requires project_id from list_projects)

**Work Delegation (ADR-017 Unified Model):**
- `create_work` - Create work for a specialized agent
  - Use `frequency="once"` for immediate one-time work (default)
  - Use `frequency="daily at 9am"` or similar for recurring work
  - Set `run_first=true` to also execute recurring work immediately
- `list_work` - List work (one-time and recurring)
- `get_work` - Get work details and all outputs
- `update_work` - Pause/resume, change frequency, update task
- `delete_work` - Remove work and all outputs

---

## Tool Usage Rules

1. When the user mentions a project by name and wants to modify it, IMMEDIATELY call `list_projects` first to get the project_id
2. Do NOT ask clarifying questions about project details when you can look them up with tools
3. If the user asks to "rename my X project" - call list_projects, find X, then call rename_project

Project organization guidelines:
- Create projects when the user explicitly asks, OR when a distinct topic/goal emerges
- Before creating/renaming, check existing projects with list_projects to avoid duplicates
- Always tell the user when you modify a project and why
- Keep project names short and descriptive (2-5 words)
- Don't create projects for one-off questions or casual conversation

---

## Communication Guidelines

- Be conversational but substantive
- Reference specific context when it's relevant
- Use what you know about the user to personalize responses
- Help structure thinking - don't just answer, help them explore
- If context doesn't contain relevant information, say so honestly
- When work fails, explain the error clearly and suggest next steps

{context}"""

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
        with_tools: bool = False
    ) -> str:
        """Build system prompt with memory context."""
        base_prompt = self.SYSTEM_PROMPT_WITH_TOOLS if with_tools else self.SYSTEM_PROMPT

        if not include_context:
            return base_prompt.format(context="No context loaded for this conversation.")

        context_text = self._format_memories(context)

        if not context_text:
            context_text = "No context available yet. As we chat, I'll learn more about you and this project."

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

        system = self._build_system_prompt(context, include_context, with_tools=True)

        # Build messages list
        messages = list(history)
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

        system = self._build_system_prompt(context, include_context, with_tools=True)

        # Build messages list
        messages = list(history)
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
