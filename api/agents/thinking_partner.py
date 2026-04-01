"""
Thinking Partner Agent - Conversational assistant with unified memory (ADR-005)

ADR-007: Tool use for work authority
ADR-025: Claude Code agentic alignment with skills and todo tracking
ADR-034: Domain-based context scoping (replaces projects)
ADR-036/037: Primitive-based architecture (Read, Write, Edit, etc.)
ADR-059: Modular prompt architecture (tp_prompts/)
"""

import json
from typing import AsyncGenerator, Optional, Any
from dataclasses import dataclass

from agents.base import BaseAgent, AgentResult, ContextBundle
from agents.tp_prompts import build_system_prompt as build_modular_prompt
from agents.tp_prompts.base import SIMPLE_PROMPT
from services.anthropic import (
    chat_completion,
    chat_completion_stream,
    chat_completion_with_tools,
    chat_completion_stream_with_tools,
    ChatResponse,
    StreamEvent,
)
from services.primitives import execute_primitive
from services.primitives.registry import CHAT_PRIMITIVES
from services.commands import detect_command, get_command_prompt_addition, detect_command_hybrid
from services.working_memory import build_working_memory, format_for_prompt
from services.platform_tools import get_platform_tools_for_user


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
    - Source domains: Context that emerged from agent sources (e.g., "Notion: Board Updates")

    ADR-007: Can use tools to manage memories, agents, and work.

    Output: Chat response (text, optionally streamed)

    ADR-059: Prompts now modularized in tp_prompts/ directory.
    ADR-144: Context awareness always injected (graduated, not binary).
    """

    # ADR-059: Prompts are now modularized in tp_prompts/ directory
    SYSTEM_PROMPT = SIMPLE_PROMPT

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        super().__init__(model)
        self.tools = CHAT_PRIMITIVES  # ADR-146: explicit chat registry (was PRIMITIVES)

    def _format_memories(self, context: ContextBundle, selected_domain_name: Optional[str] = None) -> str:
        """Format memories for system prompt with counts and unified summary.

        ADR-034: Uses domain terminology instead of project terminology.
        - user_memories: From default domain (personal/portable facts)
        - project_memories: From source domains (agent-specific context)
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

        # Domain memories (from source domains - agent context)
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
        surface_content: Optional[str] = None,
        selected_domain_name: Optional[str] = None,
        command_prompt: Optional[str] = None,
        injected_context: Optional[dict] = None,
    ) -> list[dict]:
        """Build system prompt as content blocks for prompt caching.

        ADR-059: Uses modular prompts from tp_prompts/ directory.
        ADR-144: Context awareness always injected (graduated, not binary).
        Static sections (identity, tools, behaviors) are cached.
        Dynamic sections (working memory, surface content) are NOT cached.

        Args:
            context: Memory context bundle (legacy)
            include_context: Whether to include memory context
            with_tools: Whether to include tool usage instructions
            surface_content: ADR-023 - Content of what user is currently viewing
            selected_domain_name: ADR-034 - Name of user's selected domain context
            command_prompt: ADR-025 - Skill-specific prompt addition to inject
            injected_context: ADR-058 - Pre-built working memory from build_working_memory()
        """
        # Build context text
        if not include_context:
            context_text = "No context loaded for this conversation."
        elif injected_context:
            # ADR-058: Use pre-built working memory (preferred path)
            context_text = format_for_prompt(injected_context)
        else:
            # Legacy path: format from ContextBundle
            context_text = self._format_memories(context, selected_domain_name)
            if not context_text:
                context_text = "No context available yet. As we chat, I'll learn more about you."

        # ADR-034: Add selected context scope notice at the top
        if selected_domain_name:
            context_scope = f"## Current Context Scope: {selected_domain_name}\n\nThe user has selected \"{selected_domain_name}\" as their current context domain. Context from this domain is loaded above.\n\n---\n\n"
        else:
            context_scope = "## Current Context Scope: Personal\n\nThe user is working in their personal context (default domain). Memories are about the user themselves - their preferences, habits, and general information.\n\n---\n\n"

        context_text = context_scope + context_text

        # ADR-023: Prepend surface content if user is viewing something specific
        if surface_content:
            context_text = f"{surface_content}\n\n---\n\n{context_text}"

        # ADR-059: Use modular prompt builder — returns content blocks
        # ADR-144: Context awareness always included — graduated, not binary
        blocks = build_modular_prompt(
            with_tools=with_tools,
            context=context_text,
        )

        # ADR-025: Inject skill prompt as additional dynamic block
        if command_prompt:
            blocks.append({"type": "text", "text": "\n" + command_prompt})

        return blocks

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
        surface_content = params.get("surface_content")  # ADR-023: What user is viewing
        selected_domain_name = params.get("selected_domain_name")  # ADR-034: Selected context
        scoped_agent = params.get("scoped_agent")  # ADR-087: Agent-scoped context
        # ADR-058: Build working memory (replaces most memory searches)
        # ADR-087: Pass scoped_agent for per-agent instructions + memory injection
        injected_context = None
        try:
            injected_context = await build_working_memory(
                auth.user_id, auth.client, agent=scoped_agent,
            )
        except Exception:
            # Working memory is best-effort; fall back to legacy path
            pass

        # ADR-050: Get platform tools for user's connected integrations
        platform_tools = []
        try:
            platform_tools = await get_platform_tools_for_user(auth)
        except Exception:
            # Platform tools are best-effort
            pass

        # Combine primitives with platform tools
        tools = self.tools + platform_tools

        # ADR-025 + ADR-040: Detect command from user message (hybrid: pattern + semantic)
        active_command, detection_method, confidence = await detect_command_hybrid(task)
        command_prompt = get_command_prompt_addition(active_command) if active_command else None

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
            surface_content=surface_content,
            selected_domain_name=selected_domain_name,
            command_prompt=command_prompt,
            injected_context=injected_context,
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
        else:
            user_content = [{"type": "text", "text": task}]

        # Merge with last message if it's also a user message (e.g., tool_result blocks
        # from the previous turn). Claude API requires strict role alternation.
        if messages and messages[-1].get("role") == "user":
            prev = messages[-1]["content"]
            if isinstance(prev, str):
                prev = [{"type": "text", "text": prev}]
            messages[-1]["content"] = prev + user_content
        else:
            messages.append({"role": "user", "content": user_content})

        # Create tool executor that uses our auth context
        async def tool_executor(tool_name: str, tool_input: dict) -> dict:
            return await execute_primitive(auth, tool_name, tool_input)

        # Use the streaming with tools function
        # tool_choice=auto: model decides when to use tools vs respond directly
        # Prompt guidance in base.py handles when tools are required vs optional
        # ADR-050: Uses combined tools (primitives + platform tools)
        async for event in chat_completion_stream_with_tools(
            messages=messages,
            system=system,
            tools=tools,
            tool_executor=tool_executor,
            model=self.model,
            tool_choice={"type": "auto"},
        ):
            yield event
