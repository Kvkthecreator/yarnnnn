"""
Thinking Partner Agent - Conversational assistant with unified memory (ADR-005)
"""

from typing import AsyncGenerator, Optional
from agents.base import BaseAgent, AgentResult, ContextBundle
from services.anthropic import chat_completion, chat_completion_stream


class ThinkingPartnerAgent(BaseAgent):
    """
    Conversational assistant with unified memory context.

    Uses memories from two scopes:
    - User memories: What YARNNN knows about the user (portable across projects)
    - Project memories: What's specific to this project

    Output: Chat response (text, optionally streamed)
    """

    SYSTEM_PROMPT = """You are a thoughtful assistant helping the user think through problems and ideas. You have access to memories about them and their work:

1. **About You** - What you know about this person across all their work (their preferences, business, patterns, goals)
2. **Project Context** - What's specific to this current project (requirements, facts, guidelines)

Guidelines:
- Be conversational but substantive
- Reference specific context when it's relevant to the question
- Use what you know about the user to personalize your responses
- Use project context to stay grounded in this specific work
- Ask clarifying questions when the user's intent is unclear
- Help structure thinking - don't just answer, help them explore
- If the context doesn't contain relevant information, say so honestly

{context}"""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        super().__init__(model)

    def _format_memories(self, context: ContextBundle) -> str:
        """Format memories for system prompt."""
        sections = []

        # User memories (portable, about the person)
        user_memories = context.user_memories
        if user_memories:
            lines = ["## About You\n"]
            for mem in user_memories:
                tags_str = f" [{', '.join(mem.tags)}]" if mem.tags else ""
                lines.append(f"- {mem.content}{tags_str}")
            sections.append("\n".join(lines))

        # Project memories (task-specific)
        project_memories = context.project_memories
        if project_memories:
            lines = ["## Project Context\n"]
            for mem in project_memories:
                tags_str = f" [{', '.join(mem.tags)}]" if mem.tags else ""
                lines.append(f"- {mem.content}{tags_str}")
            sections.append("\n".join(lines))

        return "\n\n".join(sections) if sections else ""

    def _build_system_prompt(self, context: ContextBundle, include_context: bool) -> str:
        """Build system prompt with memory context."""
        if not include_context:
            return self.SYSTEM_PROMPT.format(context="No context loaded for this conversation.")

        context_text = self._format_memories(context)

        if not context_text:
            context_text = "No context available yet. As we chat, I'll learn more about you and this project."

        return self.SYSTEM_PROMPT.format(context=context_text)

    async def execute(
        self,
        task: str,  # User message
        context: ContextBundle,
        parameters: Optional[dict] = None
    ) -> AgentResult:
        """
        Process chat message (non-streaming).

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

        system = self._build_system_prompt(context, include_context)

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

    async def execute_stream(
        self,
        task: str,
        context: ContextBundle,
        parameters: Optional[dict] = None
    ) -> AsyncGenerator[str, None]:
        """
        Process chat message with streaming response.

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

        system = self._build_system_prompt(context, include_context)

        # Build messages list
        messages = list(history)
        messages.append({"role": "user", "content": task})

        async for chunk in chat_completion_stream(
            messages=messages,
            system=system,
            model=self.model,
        ):
            yield chunk
