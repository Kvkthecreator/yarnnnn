"""
Content Agent - Content creation from context
"""

from typing import Optional
from .base import BaseAgent, AgentResult, ContextBundle


class ContentAgent(BaseAgent):
    """
    Creates content using project context for voice, facts, and style.

    Output: Content draft (markdown or structured)
    """

    SYSTEM_PROMPT = """You are a content creator. Your task is to create content
using the provided context for accuracy, voice, and style guidance.

Guidelines:
- Match the tone and style from context examples
- Use facts and data from the context
- Create engaging, well-structured content
- Cite sources when using specific information

{context}
"""

    async def execute(
        self,
        task: str,
        context: ContextBundle,
        parameters: Optional[dict] = None
    ) -> AgentResult:
        """
        Execute content creation task.

        Args:
            task: Content brief or description
            context: Project context for voice/facts
            parameters: Optional - format, length, tone

        Returns:
            AgentResult with content draft
        """
        # TODO: Implement with Anthropic/OpenAI client

        system = self.SYSTEM_PROMPT.format(
            context=self.build_context_prompt(context)
        )

        return AgentResult(
            success=False,
            output_type="text",
            error="Not implemented - add LLM client"
        )
