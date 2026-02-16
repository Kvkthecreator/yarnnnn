"""
Web Research Service - ADR-061 Two-Path Architecture

Provides web research capabilities using Anthropic's native web_search tool.
Used by execution strategies (ResearchStrategy, HybridStrategy) for
research-type deliverables.

This was extracted from agents/researcher.py as part of ADR-061 cleanup.
The ResearcherAgent class pattern wasn't being used - only this function.
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
}


@dataclass
class ResearchResult:
    """Result from web research."""
    content: str  # Formatted research findings
    sources: list[str]  # URLs cited
    search_queries: list[str]  # Queries used
    success: bool
    error: Optional[str] = None


RESEARCH_SYSTEM_PROMPT = """You are a Research Agent specializing in web research for business intelligence.

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


async def research_topic(
    topic: str,
    context: Optional[str] = None,
    max_searches: int = 5,
    model: str = "claude-sonnet-4-20250514",
) -> ResearchResult:
    """
    Conduct web research on a topic using Anthropic's native web_search tool.

    Args:
        topic: Research question or topic
        context: Optional additional context
        max_searches: Maximum number of searches
        model: Claude model to use

    Returns:
        ResearchResult with findings
    """
    logger.info(f"[WEB_RESEARCH] Starting research: {topic[:50]}...")

    client = get_anthropic_client()

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
        response = await client.messages.create(
            model=model,
            max_tokens=4096,
            system=RESEARCH_SYSTEM_PROMPT,
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
                        logger.info(f"[WEB_RESEARCH] Search query: {query}")
            elif block.type == "web_search_tool_result":
                # Extract sources from results
                if hasattr(block, 'content'):
                    for result in block.content if isinstance(block.content, list) else [block.content]:
                        if hasattr(result, 'url'):
                            sources.append(result.url)

        # Handle multi-turn if needed (when model continues after tool use)
        while response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            # Continue the conversation
            response = await client.messages.create(
                model=model,
                max_tokens=4096,
                system=RESEARCH_SYSTEM_PROMPT,
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
            f"[WEB_RESEARCH] Complete: queries={len(search_queries)}, "
            f"sources={len(sources)}, content_len={len(research_content)}"
        )

        return ResearchResult(
            content=research_content,
            sources=list(set(sources)),  # Deduplicate
            search_queries=search_queries,
            success=True,
        )

    except Exception as e:
        logger.error(f"[WEB_RESEARCH] Failed: {e}", exc_info=True)
        return ResearchResult(
            content="",
            sources=[],
            search_queries=search_queries,
            success=False,
            error=str(e),
        )
