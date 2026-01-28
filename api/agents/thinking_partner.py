"""
Thinking Partner Agent - Conversational assistant
"""

from typing import Optional
from .base import BaseAgent, AgentResult, ContextBundle


class ThinkingPartnerAgent(BaseAgent):
    """
    Conversational assistant that maintains chat history
    and optionally uses project context.

    Output: Chat response (streamed)
    """

    SYSTEM_PROMPT = """You are a thoughtful assistant helping the user think through
problems and ideas. You have access to their project context which you can reference
when relevant.

Guidelines:
- Be conversational but substantive
- Reference context when it's helpful
- Ask clarifying questions when needed
- Help structure thinking, don't just answer

{context}
"""

    def __init__(self, model: str = "claude-3-5-sonnet-20241022"):
        super().__init__(model)
        self.messages: list[dict] = []

    async def execute(
        self,
        task: str,  # User message
        context: ContextBundle,
        parameters: Optional[dict] = None
    ) -> AgentResult:
        """
        Process chat message.

        Args:
            task: User's message
            context: Project context (if include_context=True)
            parameters: Optional - include_context, history

        Returns:
            AgentResult with assistant response
        """
        # TODO: Implement with streaming LLM call
        # 1. Build system prompt with context
        # 2. Append user message to history
        # 3. Call LLM with full history
        # 4. Stream response
        # 5. Append assistant response to history

        include_context = (parameters or {}).get("include_context", True)
        history = (parameters or {}).get("history", [])

        system = self.SYSTEM_PROMPT.format(
            context=self.build_context_prompt(context) if include_context else "No context loaded."
        )

        return AgentResult(
            success=False,
            output_type="text",
            error="Not implemented - add streaming LLM client"
        )
