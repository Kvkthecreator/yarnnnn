"""
Execution Strategies - ADR-109 Scope-Based Routing

Determines HOW an agent is executed based on its scope (ADR-109).

Reporter strategies (platform dump → generate):
- platform: Single platform reader → headless agent
- cross_platform: Multi-platform reader → headless agent

Reasoning strategies (workspace → agent queries → generate):
- knowledge: Load workspace context, agent drives own knowledge base queries
- research: Platform grounding + research_directive → headless agent uses WebSearch
- autonomous: Full workspace-driven investigation (ADR-106 AnalystStrategy)

ADR-073: All platform reads come from platform_content (no live API calls).
ADR-106: Reasoning agents load workspace state instead of receiving platform dumps.
ADR-081: Research strategies pass a research_directive to the headless agent.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class GatheredContext:
    """Result of context gathering."""
    content: str
    summary: dict = field(default_factory=dict)
    sources_used: list[str] = field(default_factory=list)
    items_fetched: int = 0
    errors: list[str] = field(default_factory=list)
    platform_content_ids: list[str] = field(default_factory=list)  # ADR-073: for retention


class ExecutionStrategy(ABC):
    """Base class for execution strategies."""

    @abstractmethod
    async def gather_context(
        self,
        client,
        user_id: str,
        agent: dict,
    ) -> GatheredContext:
        """Gather context according to strategy."""
        pass

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Name of this strategy for logging."""
        pass


class PlatformBoundStrategy(ExecutionStrategy):
    """
    Strategy for platform-scope agents (e.g., digest).
    Fetches from one platform, uses platform-specific synthesis.
    """

    @property
    def strategy_name(self) -> str:
        return "platform"

    async def gather_context(
        self,
        client,
        user_id: str,
        agent: dict,
    ) -> GatheredContext:
        from services.platform_content import get_content_summary_for_generation

        sources = agent.get("sources", [])
        # Infer primary platform from sources (first provider found)
        primary_platform = None
        for s in sources:
            p = s.get("provider")
            if p:
                primary_platform = p
                break
        agent_id = agent.get("id")

        context_parts = []
        result = GatheredContext(content="", summary={"strategy": self.strategy_name})

        # Filter sources to primary platform
        # The "google" connection provides both "gmail" and "calendar" content,
        # so a source with provider="google" should match primary_platform="calendar" or "gmail"
        google_platforms = {"gmail", "calendar"}

        # Include sources with type="integration_import" or sources missing the type field
        # (untyped sources are treated as integration_import with a warning)
        def _is_integration(s):
            return s.get("type") == "integration_import" or (not s.get("type") and s.get("provider"))

        def _matches_platform(s):
            return (
                s.get("provider") == primary_platform
                or (s.get("provider") == "google" and primary_platform in google_platforms)
            )

        untyped = [s for s in sources if not s.get("type") and s.get("provider")]
        if untyped:
            logger.warning(
                f"[PLATFORM_BOUND] {len(untyped)} sources missing 'type' field — "
                f"treating as integration_import: {[s.get('provider') for s in untyped]}"
            )

        platform_sources = [
            s for s in sources
            if _is_integration(s) and _matches_platform(s)
        ]

        if not platform_sources and sources:
            platform_sources = [s for s in sources if _is_integration(s)]
            logger.info(f"[PLATFORM_BOUND] No {primary_platform} sources, using all {len(platform_sources)} integration sources")

        # ADR-073: Read from platform_content instead of live API calls
        if platform_sources:
            try:
                content_text, content_ids = await get_content_summary_for_generation(
                    db_client=client,
                    user_id=user_id,
                    agent_sources=platform_sources,
                )
                if content_text:
                    context_parts.append(content_text)
                    result.platform_content_ids = content_ids
                    result.items_fetched = len(content_ids)
                    providers = {s.get("provider", "unknown") for s in platform_sources}
                    result.sources_used = [f"platform:{p}" for p in providers]
            except Exception as e:
                result.errors.append(f"Failed to read platform_content: {e}")
                logger.warning(f"[PLATFORM_BOUND] platform_content read error: {e}")

        # Add user memories
        memories = await _get_user_memories(client, user_id)
        if memories:
            context_parts.append(f"[USER CONTEXT]\n{memories}")

        # Add past version feedback
        past_context = await _get_past_versions_context(client, agent_id)
        if past_context:
            context_parts.append(past_context)

        result.content = "\n\n---\n\n".join(context_parts) if context_parts else "(No context available)"
        result.summary["sources_used"] = result.sources_used
        result.summary["items_fetched"] = result.items_fetched
        result.summary["primary_platform"] = primary_platform

        logger.info(
            f"[PLATFORM_BOUND] Gathered: platform={primary_platform}, "
            f"sources={len(result.sources_used)}, items={result.items_fetched}"
        )

        return result


class CrossPlatformStrategy(ExecutionStrategy):
    """
    Strategy for cross_platform agents (e.g., status, brief, watch).
    Fetches from multiple platforms in parallel, then synthesizes.
    """

    @property
    def strategy_name(self) -> str:
        return "cross_platform"

    async def gather_context(
        self,
        client,
        user_id: str,
        agent: dict,
    ) -> GatheredContext:
        from services.platform_content import get_content_summary_for_generation

        sources = agent.get("sources", [])
        agent_id = agent.get("id")

        result = GatheredContext(content="", summary={"strategy": self.strategy_name})

        integration_sources = [s for s in sources if s.get("type") == "integration_import"]
        other_sources = [s for s in sources if s.get("type") != "integration_import"]

        # Warn about sources missing the type field — these get silently dropped
        untyped = [s for s in sources if not s.get("type") and s.get("provider")]
        if untyped:
            logger.warning(
                f"[CROSS_PLATFORM] {len(untyped)} sources missing 'type' field — "
                f"treating as integration_import: {[s.get('provider') for s in untyped]}"
            )
            integration_sources.extend(untyped)

        providers = list({s.get("provider", "unknown") for s in integration_sources})

        logger.info(
            f"[CROSS_PLATFORM] Reading platform_content for {len(providers)} providers: {providers}"
        )

        context_parts = []

        # ADR-073: Single read from platform_content (no live API calls)
        if integration_sources:
            try:
                content_text, content_ids = await get_content_summary_for_generation(
                    db_client=client,
                    user_id=user_id,
                    agent_sources=integration_sources,
                )
                if content_text:
                    context_parts.append(content_text)
                    result.platform_content_ids = content_ids
                    result.items_fetched = len(content_ids)
                    result.sources_used = [f"platform:{p}" for p in providers]
            except Exception as e:
                result.errors.append(f"Failed to read platform_content: {e}")
                logger.warning(f"[CROSS_PLATFORM] platform_content read error: {e}")

        # Handle non-integration sources (documents, descriptions)
        for source in other_sources:
            source_content = await _fetch_other_source(client, source)
            if source_content:
                context_parts.append(source_content)
                result.sources_used.append(f"other:{source.get('type')}")

        # Add user memories
        memories = await _get_user_memories(client, user_id)
        if memories:
            context_parts.append(f"[USER CONTEXT]\n{memories}")

        # Add past version feedback
        past_context = await _get_past_versions_context(client, agent_id)
        if past_context:
            context_parts.append(past_context)

        result.content = "\n\n---\n\n".join(context_parts) if context_parts else "(No context available)"
        result.summary["sources_used"] = result.sources_used
        result.summary["items_fetched"] = result.items_fetched
        result.summary["providers_fetched"] = providers

        logger.info(
            f"[CROSS_PLATFORM] Gathered: providers={providers}, "
            f"sources={len(result.sources_used)}, items={result.items_fetched}"
        )

        return result


class ResearchStrategy(ExecutionStrategy):
    """
    Strategy for research agents.

    ADR-081: No longer runs web research during context gathering.
    Gathers optional platform grounding, then passes a research_directive
    so the headless agent uses WebSearch during generation.
    """

    @property
    def strategy_name(self) -> str:
        return "research"

    async def gather_context(
        self,
        client,
        user_id: str,
        agent: dict,
    ) -> GatheredContext:
        title = agent.get("title", "")
        description = agent.get("description", "")
        sources = agent.get("sources", [])

        result = GatheredContext(content="", summary={"strategy": self.strategy_name})
        context_parts = []

        # 1. Optional: Get platform grounding from sources (if any configured)
        integration_sources = [s for s in sources if s.get("type") == "integration_import"]
        if integration_sources:
            logger.info(f"[RESEARCH] Adding platform grounding from {len(integration_sources)} sources")
            platform_strategy = CrossPlatformStrategy()
            platform_result = await platform_strategy.gather_context(client, user_id, agent)

            if platform_result.content and platform_result.content != "(No context available)":
                context_parts.append(f"[PLATFORM GROUNDING]\n{platform_result.content}")
                result.sources_used.extend(platform_result.sources_used)
                result.items_fetched += platform_result.items_fetched
                result.platform_content_ids.extend(platform_result.platform_content_ids)

        # 2. Add user memories
        memories = await _get_user_memories(client, user_id)
        if memories:
            context_parts.append(f"[USER CONTEXT]\n{memories}")

        # 3. Add past version feedback
        past_context = await _get_past_versions_context(client, agent.get("id"))
        if past_context:
            context_parts.append(past_context)

        result.content = "\n\n---\n\n".join(context_parts) if context_parts else "(No platform context available — use WebSearch for research.)"

        # ADR-081: Build research directive for headless agent
        result.summary["research_directive"] = _build_research_directive(title, description)
        result.summary["sources_used"] = result.sources_used
        result.summary["items_fetched"] = result.items_fetched

        logger.info(
            f"[RESEARCH] Context gathered (ADR-081): "
            f"platform_sources={len(result.sources_used)}, "
            f"research_directive=yes"
        )

        return result


class AnalystStrategy(ExecutionStrategy):
    """
    Strategy for reasoning agents (ADR-106).

    Instead of pre-gathering a platform content dump, loads the agent's
    workspace context (thesis, memory, observations) and lets the agent
    drive its own knowledge base queries via QueryKnowledge + Search primitives.

    Used by: deep_research (proactive insights), watch, custom reasoning agents.
    """

    @property
    def strategy_name(self) -> str:
        return "analyst"

    async def gather_context(
        self,
        client,
        user_id: str,
        agent: dict,
    ) -> GatheredContext:
        from services.workspace import AgentWorkspace, get_agent_slug

        title = agent.get("title", "")
        description = agent.get("description", "")
        agent_id = agent.get("id")

        result = GatheredContext(content="", summary={"strategy": self.strategy_name})
        context_parts = []

        # 1. Load agent workspace context (thesis + memory + feedback + working notes)
        ws = AgentWorkspace(client, user_id, get_agent_slug(agent))
        workspace_context = await ws.load_context()

        if workspace_context:
            context_parts.append(f"[AGENT WORKSPACE]\n{workspace_context}")
            result.sources_used.append("workspace")

        # 2. Add user memories (same as other strategies)
        memories = await _get_user_memories(client, user_id)
        if memories:
            context_parts.append(f"[USER CONTEXT]\n{memories}")

        # 3. Add past version feedback
        past_context = await _get_past_versions_context(client, agent_id)
        if past_context:
            context_parts.append(past_context)

        # 4. Build research directive so agent knows to use QueryKnowledge + WebSearch
        research_directive = _build_analyst_directive(title, description)
        result.summary["research_directive"] = research_directive

        result.content = "\n\n---\n\n".join(context_parts) if context_parts else "(No workspace context yet — this is a fresh agent. Use QueryKnowledge to explore the knowledge base and WebSearch for external research.)"
        result.summary["sources_used"] = result.sources_used
        result.summary["items_fetched"] = result.items_fetched
        result.summary["has_workspace"] = bool(workspace_context)

        logger.info(
            f"[ANALYST] Gathered: workspace={'yes' if workspace_context else 'empty'}, "
            f"title={title[:40]}"
        )

        return result


def _build_analyst_directive(title: str, description: str) -> str:
    """
    Build a directive for analyst/reasoning agents (ADR-106).

    Tells the agent to drive its own investigation via workspace + knowledge base,
    rather than passively synthesizing a pre-gathered dump.
    """
    directive = f"You are an autonomous analyst agent. Your domain: {title}"
    if description:
        directive += f"\n{description}"
    directive += """

Investigation approach:
- Start from your workspace context (thesis, observations, working notes)
- Use **QueryKnowledge** to search the user's synced platforms (Slack, Gmail, Notion, Calendar) for relevant evidence
- Use **WebSearch** for external context and trends
- Focus on what's genuinely significant — not everything that exists
- After investigating, update your workspace:
  - Write refined thesis to thesis.md (your evolving domain understanding)
  - Save research notes to working/{topic}.md
  - Append key observations to memory/observations.md
- Then generate your output based on what you found"""
    return directive


def _build_research_directive(title: str, description: str) -> str:
    """
    Build a research directive string for the headless agent (ADR-081).

    This replaces the standalone RESEARCH_SYSTEM_PROMPT from web_research.py.
    The headless agent receives this and uses WebSearch to investigate.
    """
    directive = f"This agent requires web research. Use WebSearch to investigate.\n\nResearch objective: {title}"
    if description:
        directive += f"\n{description}"
    directive += """

Research approach:
- Formulate 2-4 focused search queries based on the objective
- Search for current, authoritative sources
- Cross-reference important claims across multiple sources
- If platform context is provided, incorporate relevant internal data
- Acknowledge gaps in available information"""
    return directive


# =============================================================================
# Strategy Selection
# =============================================================================

def get_execution_strategy(agent: dict) -> ExecutionStrategy:
    """
    Select execution strategy based on agent scope (ADR-109).

    Scope directly maps to strategy:
    - platform → PlatformBoundStrategy (single platform dump)
    - cross_platform → CrossPlatformStrategy (multi-platform dump)
    - knowledge → AnalystStrategy (workspace-driven queries)
    - research → ResearchStrategy (platform + WebSearch)
    - autonomous → AnalystStrategy (full workspace-driven investigation)

    Args:
        agent: Agent dict with scope and skill columns

    Returns:
        Appropriate ExecutionStrategy instance
    """
    scope = agent.get("scope", "cross_platform")

    strategy_map = {
        "platform": PlatformBoundStrategy,
        "cross_platform": CrossPlatformStrategy,
        "knowledge": AnalystStrategy,
        "research": ResearchStrategy,
        "autonomous": AnalystStrategy,
    }

    strategy_class = strategy_map.get(scope, CrossPlatformStrategy)
    strategy = strategy_class()

    logger.info(f"[STRATEGY] Selected: {strategy.strategy_name} for scope={scope}")

    return strategy


# =============================================================================
# Helper Functions
# =============================================================================

async def _get_user_memories(client, user_id: str) -> str:
    """Get user context entries for prompt injection. ADR-108: reads /memory/notes.md."""
    try:
        from services.workspace import UserMemory
        um = UserMemory(client, user_id)
        content = await um.read("notes.md")
        if not content:
            return ""
        notes = UserMemory._parse_notes_md(content)
        return "\n".join(f"- {n['content']}" for n in notes)
    except Exception as e:
        logger.warning(f"[STRATEGY] Failed to fetch user context: {e}")
        return ""


async def _get_past_versions_context(client, agent_id: str) -> str:
    """Get past version feedback for learning."""
    if not agent_id:
        return ""

    try:
        from services.agent_pipeline import get_past_versions_context
        return await get_past_versions_context(client, agent_id)
    except Exception as e:
        logger.warning(f"[STRATEGY] Failed to get past versions: {e}")
        return ""


async def _fetch_other_source(client, source: dict) -> str:
    """Fetch non-integration sources (documents, descriptions)."""
    source_type = source.get("type")

    if source_type == "document":
        doc_id = source.get("document_id")
        if doc_id:
            try:
                result = (
                    client.table("filesystem_documents")
                    .select("filename, extracted_text")
                    .eq("id", doc_id)
                    .single()
                    .execute()
                )
                if result.data:
                    doc = result.data
                    text = doc.get("extracted_text", "")[:5000]
                    return f"[DOCUMENT: {doc.get('filename')}]\n{text}"
            except Exception as e:
                logger.warning(f"[STRATEGY] Failed to fetch document {doc_id}: {e}")

    elif source_type == "description":
        desc = source.get("value", "")
        if desc:
            return f"[SOURCE DESCRIPTION]\n{desc}"

    return ""
