"""
Reporting Agent - Structured report generation
"""

from typing import Optional
from .base import BaseAgent, AgentResult, ContextBundle


class ReportingAgent(BaseAgent):
    """
    Generates structured reports (PPTX, PDF) from context.

    Output: Report file
    """

    SYSTEM_PROMPT = """You are a business analyst creating executive reports.
Your task is to synthesize the provided context into a structured report.

Guidelines:
- Create clear, actionable insights
- Use data and evidence from context
- Structure with executive summary, findings, recommendations
- Keep language concise and professional

{context}
"""

    async def execute(
        self,
        task: str,
        context: ContextBundle,
        parameters: Optional[dict] = None
    ) -> AgentResult:
        """
        Execute report generation task.

        Args:
            task: Report brief
            context: Project context for data/insights
            parameters: Optional - format (pptx, pdf), template

        Returns:
            AgentResult with file path to generated report
        """
        # TODO: Implement with LLM + python-pptx/reportlab
        # 1. Generate report structure with LLM
        # 2. Create file with appropriate library
        # 3. Upload to Supabase storage
        # 4. Return file URL

        output_format = (parameters or {}).get("format", "pptx")

        return AgentResult(
            success=False,
            output_type="file",
            error=f"Not implemented - add {output_format} generation"
        )
