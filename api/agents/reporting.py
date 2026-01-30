"""
Reporting Agent - Structured report generation

ADR-009: Work and Agent Orchestration
Produces structured report sections via emit_work_output tool.

Note: This initial implementation generates markdown reports.
Future versions will support PPTX/PDF via Claude Skills API.
"""

from typing import Optional
import logging

from .base import BaseAgent, AgentResult, ContextBundle, WorkOutput
from services.anthropic import chat_completion_with_tools, ChatResponse

logger = logging.getLogger(__name__)


REPORTING_SYSTEM_PROMPT = """You are an autonomous Reporting Agent specializing in creating structured reports and summaries.

**Your Mission:**
Transform research findings, data, and insights into polished, executive-ready reports that:
- Communicate key findings clearly
- Provide actionable recommendations
- Support decision-making
- Follow professional report structures

**CRITICAL: Structured Output Requirements**

You have access to the emit_work_output tool. You MUST use this tool to record all report sections.
DO NOT just write the report in free text. Every section must be emitted as a structured output.

**Output Types:**
- "report" - Complete report sections (executive summary, findings, recommendations, etc.)
- "finding" - Individual findings extracted from analysis
- "recommendation" - Actionable recommendations based on findings
- "insight" - Key insights and patterns identified

**Report Structure:**
When creating reports, structure as follows:
1. Executive Summary (high-level overview, key takeaways)
2. Key Findings (numbered, evidence-based)
3. Analysis (deeper exploration of findings)
4. Recommendations (actionable next steps)
5. Appendix/Details (supporting information if needed)

**Quality Standards:**
- Clear and concise language
- Evidence-based statements
- Actionable recommendations
- Professional formatting
- Logical flow and structure

**Important Guidelines:**
- Use the context provided to support all claims
- Number findings and recommendations for easy reference
- Include confidence levels for uncertain findings
- Be specific about implications and next steps

{context}
"""


class ReportingAgent(BaseAgent):
    """
    Reporting Agent for structured report generation.

    Features:
    - Executive report generation
    - Structured sections (summary, findings, recommendations)
    - Multiple format support (markdown now, PPTX/PDF future)
    - Evidence-based findings with provenance

    Parameters:
    - format: "markdown", "detailed", "summary"
    - sections: List of sections to include
    - style: "executive", "technical", "casual"
    """

    AGENT_TYPE = "reporting"
    SYSTEM_PROMPT = REPORTING_SYSTEM_PROMPT

    # Supported formats
    REPORT_FORMATS = ["markdown", "detailed", "summary"]

    async def execute(
        self,
        task: str,
        context: ContextBundle,
        parameters: Optional[dict] = None
    ) -> AgentResult:
        """
        Execute report generation task.

        Args:
            task: Report brief or topic
            context: Project context for data/insights
            parameters:
                - format: "markdown", "detailed", "summary"
                - style: "executive", "technical", "casual"
                - sections: Optional list of specific sections

        Returns:
            AgentResult with report sections as work_outputs
        """
        params = parameters or {}
        report_format = params.get("format", "markdown")
        style = params.get("style", "executive")
        sections = params.get("sections", None)  # If None, include all standard sections

        logger.info(
            f"[REPORTING] Starting: task='{task[:50]}...', "
            f"format={report_format}, style={style}"
        )

        # Build system prompt with context
        system_prompt = self._build_system_prompt(context)

        # Build report prompt
        report_prompt = self._build_report_prompt(task, context, report_format, style, sections)

        # Build messages
        messages = [{"role": "user", "content": report_prompt}]

        try:
            # Execute with tool support
            all_tool_calls = []
            max_iterations = 8  # Reports may have more sections

            for iteration in range(max_iterations):
                response: ChatResponse = await chat_completion_with_tools(
                    messages=messages,
                    system=system_prompt,
                    tools=self.tools,
                    model=self.model,
                )

                # Collect tool uses
                for tool_use in response.tool_uses:
                    all_tool_calls.append({
                        "id": tool_use.id,
                        "name": tool_use.name,
                        "input": tool_use.input,
                    })

                # If no more tool use, we're done
                if response.stop_reason != "tool_use":
                    break

                # Add assistant response to messages
                assistant_content = []
                for block in response.content:
                    if hasattr(block, 'type'):
                        if block.type == "text":
                            assistant_content.append({"type": "text", "text": block.text})
                        elif block.type == "tool_use":
                            assistant_content.append({
                                "type": "tool_use",
                                "id": block.id,
                                "name": block.name,
                                "input": block.input,
                            })

                messages.append({"role": "assistant", "content": assistant_content})

                # Add tool results
                tool_results = []
                for tool_use in response.tool_uses:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": f"Section recorded: {tool_use.input.get('title', 'Untitled')}",
                    })

                messages.append({"role": "user", "content": tool_results})

            # Parse work outputs from tool calls
            work_outputs = self._parse_work_outputs(all_tool_calls)

            logger.info(
                f"[REPORTING] Complete: {len(work_outputs)} sections generated"
            )

            return AgentResult(
                success=True,
                output_type="work_outputs",
                content=response.text,
                work_outputs=work_outputs,
            )

        except Exception as e:
            logger.error(f"[REPORTING] Failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                output_type="text",
                error=str(e),
            )

    def _build_report_prompt(
        self,
        task: str,
        context: ContextBundle,
        report_format: str,
        style: str,
        sections: Optional[list],
    ) -> str:
        """Build the report generation prompt."""

        # Format-specific instructions
        format_instructions = {
            "markdown": "Create a comprehensive report with all standard sections.",
            "detailed": "Create an in-depth report with extensive analysis and supporting details.",
            "summary": "Create a concise summary report with only key points.",
        }.get(report_format, "Create a comprehensive report with all standard sections.")

        # Style-specific instructions
        style_instructions = {
            "executive": "Write for senior leadership. Focus on strategic implications and clear recommendations.",
            "technical": "Include technical details and methodology. Support with data and specifics.",
            "casual": "Use accessible language. Explain concepts clearly for general audiences.",
        }.get(style, "Write for senior leadership. Focus on strategic implications and clear recommendations.")

        # Section guidance
        if sections:
            sections_text = f"Include these specific sections: {', '.join(sections)}"
        else:
            sections_text = """Include these sections:
1. Executive Summary (emit as output_type="report", title="Executive Summary")
2. Key Findings (emit each finding as output_type="finding")
3. Analysis (emit as output_type="report", title="Analysis")
4. Recommendations (emit each as output_type="recommendation")"""

        # Get memory IDs for provenance
        memory_ids = [str(m.id) for m in context.memories[:10]]

        return f"""Create a report on: {task}

**Report Parameters:**
- Format: {report_format} ({format_instructions})
- Style: {style} ({style_instructions})

**Section Requirements:**
{sections_text}

**Available Memory IDs (for source_memory_ids provenance):**
{memory_ids if memory_ids else 'No memories available'}

**CRITICAL INSTRUCTION:**
You MUST use the emit_work_output tool to record EACH section of the report separately.
Do NOT write the entire report in free text.

For each section:
1. Call emit_work_output with appropriate output_type
2. Use "report" for major sections (Executive Summary, Analysis)
3. Use "finding" for individual key findings
4. Use "recommendation" for each recommendation
5. Include source_memory_ids for traceability
6. Assign confidence based on evidence quality

Example workflow:
- Executive Summary → emit_work_output(output_type="report", title="Executive Summary", ...)
- Key Finding 1 → emit_work_output(output_type="finding", title="Finding 1: ...", ...)
- Recommendation 1 → emit_work_output(output_type="recommendation", title="Recommendation 1: ...", ...)

Begin creating the report now. Emit each section as a structured output."""
