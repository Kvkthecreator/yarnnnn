"""
Thinking Partner Agent - Conversational assistant with context
"""

from typing import AsyncGenerator, Optional
from agents.base import BaseAgent, AgentResult, ContextBundle
from services.anthropic import chat_completion, chat_completion_stream


class ThinkingPartnerAgent(BaseAgent):
    """
    Conversational assistant that uses project context.

    Output: Chat response (text, optionally streamed)
    """

    SYSTEM_PROMPT = """You are a thoughtful assistant helping the user think through problems and ideas. You have access to their project context which contains knowledge they've accumulated.

Guidelines:
- Be conversational but substantive
- Reference specific context when it's relevant to the question
- Ask clarifying questions when the user's intent is unclear
- Help structure thinking - don't just answer, help them explore
- If the context doesn't contain relevant information, say so honestly

{context}"""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        super().__init__(model)

    def _build_system_prompt(self, context: ContextBundle, include_context: bool) -> str:
        """Build system prompt with or without context."""
        if include_context and context.blocks:
            context_section = self.build_context_prompt(context)
        else:
            context_section = "No project context loaded for this conversation."

        return self.SYSTEM_PROMPT.format(context=context_section)

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
            context: Project context
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
            context: Project context
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
