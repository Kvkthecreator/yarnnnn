"""
Researcher Agent - Web Research via Anthropic Native Tools

ADR-045: Type-Aware Orchestration - Phase 2

Uses Anthropic's native web_search tool (server-side) to perform research.
This agent gathers external context for research-type deliverables.

NOTE: Unlike other agents, this uses server-side tools that Anthropic executes.
The web_search tool is handled by Anthropic's infrastructure, not our code.
"""

import logging
from typing import Optional
from dataclasses import dataclass

from services.anthropic import get_anthropic_client

logger = logging.getLogger(__name__)


# Anthropic's native web_search tool definition
# This is a server-side tool - Anthropic handles the search
WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    # Optional: can add allowed_domains, blocked_domains, max_uses, user_location
}


@dataclass
class ResearchResult:
    """Result from research agent."""
    content: str  # Formatted research findings
    sources: list[str]  # URLs cited
    search_queries: list[str]  # Queries used
    success: bool
    error: Optional[str] = None


RESEARCHER_SYSTEM_PROMPT = """You are a Research Agent specializing in web research for business intelligence.

**Your Mission:**
Conduct focused web research to gather relevant information for the given research task.
You have access to web_search which searches the internet for current information.

**Research Approach:**
1. Analyze the research question carefully
2. Formulate 2-4 focused search queries to gather relevant information
3. Use web_search to find current, authoritative sources
4. Synthesize findings into a structured research summary

**Output Format:**
After completing your research, provide a structured summary:

## Research Summary
[Brief overview of what you found]

## Key Findings
- [Finding 1 with source]
- [Finding 2 with source]
- [Finding 3 with source]

## Sources
[List all URLs you referenced]

## Confidence
[Your confidence in the findings: High/Medium/Low with brief explanation]

**Quality Standards:**
- Focus on recent, authoritative sources
- Cross-reference important claims
- Acknowledge gaps in available information
- Be specific about what sources say vs. your analysis
"""


class ResearcherAgent:
    """
    Agent that performs web research using Anthropic's native tools.

    ADR-045 Phase 2: Tool-equipped agent for research strategy.

    Unlike work agents that use submit_output, this agent uses the
    native web_search tool and returns structured research results.
    """

    AGENT_TYPE = "researcher"

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model = model
        self.client = get_anthropic_client()

    async def research(
        self,
        topic: str,
        context: Optional[str] = None,
        max_searches: int = 5,
    ) -> ResearchResult:
        """
        Conduct web research on a topic.

        Args:
            topic: The research question or topic
            context: Optional additional context (e.g., user's specific focus)
            max_searches: Maximum number of web searches allowed

        Returns:
            ResearchResult with findings and sources
        """
        logger.info(f"[RESEARCHER] Starting research: {topic[:50]}...")

        # Build the research prompt
        user_prompt = f"""Research Task: {topic}"""

        if context:
            user_prompt += f"""

Additional Context:
{context}"""

        user_prompt += """

Please conduct focused web research on this topic. Use web_search to find relevant, current information.
After your research, provide a structured summary of your findings."""

        messages = [{"role": "user", "content": user_prompt}]
        sources = []
        search_queries = []

        try:
            # Call Anthropic API with web_search tool
            # The server handles the actual web searches
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=RESEARCHER_SYSTEM_PROMPT,
                tools=[WEB_SEARCH_TOOL],
                messages=messages,
            )

            # Process response - extract text and track sources
            content_parts = []

            for block in response.content:
                if block.type == "text":
                    content_parts.append(block.text)
                elif block.type == "server_tool_use":
                    # Server tool use - track the query
                    if block.name == "web_search":
                        query = block.input.get("query", "")
                        if query:
                            search_queries.append(query)
                            logger.info(f"[RESEARCHER] Search query: {query}")
                elif block.type == "web_search_tool_result":
                    # Extract sources from results
                    if hasattr(block, 'content'):
                        for result in block.content if isinstance(block.content, list) else [block.content]:
                            if hasattr(result, 'url'):
                                sources.append(result.url)

            # Handle multi-turn if needed (when model continues after tool use)
            while response.stop_reason == "tool_use":
                # Reconstruct message for continuation
                assistant_content = []
                tool_results = []

                for block in response.content:
                    if block.type == "text":
                        assistant_content.append({"type": "text", "text": block.text})
                    elif block.type == "server_tool_use":
                        assistant_content.append({
                            "type": "server_tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        })
                    elif block.type == "web_search_tool_result":
                        # Server tool results are auto-included
                        pass

                messages.append({"role": "assistant", "content": response.content})

                # Continue the conversation
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=RESEARCHER_SYSTEM_PROMPT,
                    tools=[WEB_SEARCH_TOOL],
                    messages=messages,
                )

                # Collect additional content
                for block in response.content:
                    if block.type == "text":
                        content_parts.append(block.text)
                    elif block.type == "server_tool_use":
                        if block.name == "web_search":
                            query = block.input.get("query", "")
                            if query:
                                search_queries.append(query)
                    elif block.type == "web_search_tool_result":
                        if hasattr(block, 'content'):
                            for result in block.content if isinstance(block.content, list) else [block.content]:
                                if hasattr(result, 'url'):
                                    sources.append(result.url)

                # Safety: limit iterations
                if len(search_queries) >= max_searches:
                    break

            # Combine all text content
            research_content = "\n\n".join(content_parts)

            logger.info(
                f"[RESEARCHER] Complete: queries={len(search_queries)}, "
                f"sources={len(sources)}, content_len={len(research_content)}"
            )

            return ResearchResult(
                content=research_content,
                sources=list(set(sources)),  # Deduplicate
                search_queries=search_queries,
                success=True,
            )

        except Exception as e:
            logger.error(f"[RESEARCHER] Failed: {e}", exc_info=True)
            return ResearchResult(
                content="",
                sources=[],
                search_queries=search_queries,
                success=False,
                error=str(e),
            )


async def research_topic(
    topic: str,
    context: Optional[str] = None,
    max_searches: int = 5,
) -> ResearchResult:
    """
    Convenience function to perform web research.

    Args:
        topic: Research question or topic
        context: Optional additional context
        max_searches: Maximum number of searches

    Returns:
        ResearchResult with findings
    """
    agent = ResearcherAgent()
    return await agent.research(topic, context, max_searches)
