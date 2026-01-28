"""
Research Agent - Deep investigation using context
"""

from typing import Optional
from .base import BaseAgent, AgentResult, ContextBundle


class ResearchAgent(BaseAgent):
    """
    Investigates topics using project context as source material.

    Output: Research summary (markdown)
    """

    SYSTEM_PROMPT = """You are a research analyst. Your task is to investigate topics
using the provided context as your primary source material.

Guidelines:
- Cite specific information from the context
- Identify gaps in available information
- Provide structured analysis with clear sections
- Be objective and evidence-based

{context}
"""

    async def execute(
        self,
        task: str,
        context: ContextBundle,
        parameters: Optional[dict] = None
    ) -> AgentResult:
        """
        Execute research task.

        Args:
            task: Research question or topic
            context: Project context to analyze
            parameters: Optional - depth, focus_areas

        Returns:
            AgentResult with markdown research summary
        """
        # TODO: Implement with Anthropic/OpenAI client
        # 1. Build system prompt with context
        # 2. Call LLM with task
        # 3. Return structured result

        system = self.SYSTEM_PROMPT.format(
            context=self.build_context_prompt(context)
        )

        # Placeholder - implement with actual LLM call
        return AgentResult(
            success=False,
            output_type="text",
            error="Not implemented - add Anthropic client"
        )
