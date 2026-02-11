"""
Execution Strategies - ADR-045 Type-Aware Orchestration

Determines HOW a deliverable is executed based on its type_classification.binding.

Strategies:
- platform_bound: Single platform gatherer → DeliverableAgent
- cross_platform: Parallel platform gatherers → DeliverableAgent
- research: Web researcher (Anthropic native) → DeliverableAgent
- hybrid: Research + Platform in parallel → DeliverableAgent

Phase 1 ✅: Strategy selection and parallel fetching
Phase 2 ✅: Web research via Anthropic's native web_search tool
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
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


class ExecutionStrategy(ABC):
    """Base class for execution strategies."""

    @abstractmethod
    async def gather_context(
        self,
        client,
        user_id: str,
        deliverable: dict,
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
    Strategy for platform_bound deliverables.

    Single platform focus (e.g., slack_channel_digest, gmail_inbox_brief).
    Fetches from one platform, uses platform-specific synthesis.
    """

    @property
    def strategy_name(self) -> str:
        return "platform_bound"

    async def gather_context(
        self,
        client,
        user_id: str,
        deliverable: dict,
    ) -> GatheredContext:
        from services.deliverable_pipeline import fetch_integration_source_data

        classification = deliverable.get("type_classification", {})
        primary_platform = classification.get("primary_platform")
        sources = deliverable.get("sources", [])
        last_run_at = _parse_last_run_at(deliverable.get("last_run_at"))
        deliverable_id = deliverable.get("id")

        context_parts = []
        result = GatheredContext(content="", summary={"strategy": self.strategy_name})

        # Filter sources to primary platform
        platform_sources = [
            s for s in sources
            if s.get("type") == "integration_import"
            and s.get("provider") == primary_platform
        ]

        if not platform_sources and sources:
            # Fallback: use all integration sources
            platform_sources = [
                s for s in sources if s.get("type") == "integration_import"
            ]
            logger.info(f"[PLATFORM_BOUND] No {primary_platform} sources, using all {len(platform_sources)} integration sources")

        # Fetch from platform sources
        for idx, source in enumerate(platform_sources):
            try:
                fetch_result = await fetch_integration_source_data(
                    client=client,
                    user_id=user_id,
                    source=source,
                    last_run_at=last_run_at,
                    deliverable_id=deliverable_id,
                    source_index=idx,
                )
                if fetch_result.content:
                    provider = source.get("provider", "unknown")
                    context_parts.append(f"[{provider.upper()} DATA]\n{fetch_result.content}")
                    result.sources_used.append(f"platform:{provider}")
                    result.items_fetched += fetch_result.items_fetched
            except Exception as e:
                result.errors.append(f"Failed to fetch {source.get('provider')}: {e}")
                logger.warning(f"[PLATFORM_BOUND] Source fetch error: {e}")

        # Add user memories
        memories = await _get_user_memories(client, user_id)
        if memories:
            context_parts.append(f"[USER CONTEXT]\n{memories}")

        # Add past version feedback
        past_context = await _get_past_versions_context(client, deliverable_id)
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
    Strategy for cross_platform deliverables.

    Fetches from multiple platforms in parallel, then synthesizes.
    Used for status_report, weekly_status, project_brief, etc.
    """

    @property
    def strategy_name(self) -> str:
        return "cross_platform"

    async def gather_context(
        self,
        client,
        user_id: str,
        deliverable: dict,
    ) -> GatheredContext:
        from services.deliverable_pipeline import fetch_integration_source_data

        sources = deliverable.get("sources", [])
        last_run_at = _parse_last_run_at(deliverable.get("last_run_at"))
        deliverable_id = deliverable.get("id")

        result = GatheredContext(content="", summary={"strategy": self.strategy_name})

        # Group sources by provider for parallel fetching
        integration_sources = [s for s in sources if s.get("type") == "integration_import"]
        other_sources = [s for s in sources if s.get("type") != "integration_import"]

        # Group integration sources by provider
        sources_by_provider: dict[str, list] = {}
        for source in integration_sources:
            provider = source.get("provider", "unknown")
            if provider not in sources_by_provider:
                sources_by_provider[provider] = []
            sources_by_provider[provider].append(source)

        logger.info(
            f"[CROSS_PLATFORM] Fetching from {len(sources_by_provider)} providers in parallel: "
            f"{list(sources_by_provider.keys())}"
        )

        # Create async tasks for each provider
        async def fetch_provider_sources(provider: str, provider_sources: list) -> tuple[str, list[str], int, list[str]]:
            """Fetch all sources for a provider, return (content, sources_used, items, errors)."""
            parts = []
            sources_used = []
            items = 0
            errors = []

            for idx, source in enumerate(provider_sources):
                try:
                    fetch_result = await fetch_integration_source_data(
                        client=client,
                        user_id=user_id,
                        source=source,
                        last_run_at=last_run_at,
                        deliverable_id=deliverable_id,
                        source_index=idx,
                    )
                    if fetch_result.content:
                        parts.append(fetch_result.content)
                        sources_used.append(f"platform:{provider}")
                        items += fetch_result.items_fetched
                except Exception as e:
                    errors.append(f"{provider}: {e}")

            content = f"[{provider.upper()} DATA]\n" + "\n\n".join(parts) if parts else ""
            return content, sources_used, items, errors

        # Execute all providers in parallel
        tasks = [
            fetch_provider_sources(provider, provider_sources)
            for provider, provider_sources in sources_by_provider.items()
        ]

        context_parts = []
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for res in results:
                if isinstance(res, Exception):
                    result.errors.append(str(res))
                    continue

                content, sources_used, items, errors = res
                if content:
                    context_parts.append(content)
                result.sources_used.extend(sources_used)
                result.items_fetched += items
                result.errors.extend(errors)

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
        past_context = await _get_past_versions_context(client, deliverable_id)
        if past_context:
            context_parts.append(past_context)

        result.content = "\n\n---\n\n".join(context_parts) if context_parts else "(No context available)"
        result.summary["sources_used"] = result.sources_used
        result.summary["items_fetched"] = result.items_fetched
        result.summary["providers_fetched"] = list(sources_by_provider.keys())

        logger.info(
            f"[CROSS_PLATFORM] Gathered: providers={list(sources_by_provider.keys())}, "
            f"sources={len(result.sources_used)}, items={result.items_fetched}"
        )

        return result


class ResearchStrategy(ExecutionStrategy):
    """
    Strategy for research deliverables.

    ADR-045 Phase 2: Uses Anthropic's native web_search tool via ResearcherAgent.
    Gathers external context through web research, optionally combined with
    platform grounding.
    """

    @property
    def strategy_name(self) -> str:
        return "research"

    async def gather_context(
        self,
        client,
        user_id: str,
        deliverable: dict,
    ) -> GatheredContext:
        from agents.researcher import research_topic

        title = deliverable.get("title", "")
        description = deliverable.get("description", "")
        task = deliverable.get("task", deliverable.get("title", ""))
        sources = deliverable.get("sources", [])

        # Build research topic from deliverable
        research_topic_str = task or title
        if description:
            research_topic_str += f"\n\nContext: {description}"

        logger.info(f"[RESEARCH] Starting web research: {research_topic_str[:50]}...")

        result = GatheredContext(content="", summary={"strategy": self.strategy_name})
        context_parts = []

        # 1. Conduct web research using Anthropic's native web_search
        try:
            research_result = await research_topic(
                topic=research_topic_str,
                max_searches=5,
            )

            if research_result.success and research_result.content:
                context_parts.append(f"[WEB RESEARCH]\n{research_result.content}")
                result.sources_used.extend([f"web:{url}" for url in research_result.sources[:5]])
                result.summary["search_queries"] = research_result.search_queries
                result.summary["web_sources_count"] = len(research_result.sources)
                logger.info(
                    f"[RESEARCH] Web research complete: "
                    f"queries={len(research_result.search_queries)}, "
                    f"sources={len(research_result.sources)}"
                )
            elif research_result.error:
                result.errors.append(f"Web research failed: {research_result.error}")
                logger.warning(f"[RESEARCH] Web research error: {research_result.error}")

        except Exception as e:
            result.errors.append(f"Web research exception: {e}")
            logger.error(f"[RESEARCH] Web research failed: {e}")

        # 2. Optional: Get platform grounding from sources (if any configured)
        integration_sources = [s for s in sources if s.get("type") == "integration_import"]
        if integration_sources:
            logger.info(f"[RESEARCH] Adding platform grounding from {len(integration_sources)} sources")
            # Use cross-platform strategy for platform sources
            platform_strategy = CrossPlatformStrategy()
            platform_result = await platform_strategy.gather_context(client, user_id, deliverable)

            if platform_result.content and platform_result.content != "(No context available)":
                context_parts.append(f"[PLATFORM GROUNDING]\n{platform_result.content}")
                result.sources_used.extend(platform_result.sources_used)
                result.items_fetched += platform_result.items_fetched

        # 3. Add user memories
        memories = await _get_user_memories(client, user_id)
        if memories:
            context_parts.append(f"[USER CONTEXT]\n{memories}")

        # 4. Add past version feedback
        past_context = await _get_past_versions_context(client, deliverable.get("id"))
        if past_context:
            context_parts.append(past_context)

        result.content = "\n\n---\n\n".join(context_parts) if context_parts else "(No context available)"
        result.summary["sources_used"] = result.sources_used
        result.summary["items_fetched"] = result.items_fetched

        logger.info(
            f"[RESEARCH] Context gathered: web_sources={result.summary.get('web_sources_count', 0)}, "
            f"platform_sources={len([s for s in result.sources_used if s.startswith('platform:')])}"
        )

        return result


class HybridStrategy(ExecutionStrategy):
    """
    Strategy for hybrid deliverables.

    ADR-045 Phase 2: Combines web research with platform grounding in parallel.
    Web research and platform fetching run concurrently for efficiency.
    """

    @property
    def strategy_name(self) -> str:
        return "hybrid"

    async def gather_context(
        self,
        client,
        user_id: str,
        deliverable: dict,
    ) -> GatheredContext:
        from agents.researcher import research_topic

        title = deliverable.get("title", "")
        description = deliverable.get("description", "")
        task = deliverable.get("task", deliverable.get("title", ""))

        # Build research topic
        research_topic_str = task or title
        if description:
            research_topic_str += f"\n\nContext: {description}"

        logger.info(f"[HYBRID] Starting parallel web research + platform fetch: {research_topic_str[:50]}...")

        result = GatheredContext(content="", summary={"strategy": self.strategy_name})
        context_parts = []

        # Run web research and platform fetching in parallel
        async def do_web_research():
            try:
                return await research_topic(topic=research_topic_str, max_searches=3)
            except Exception as e:
                logger.error(f"[HYBRID] Web research failed: {e}")
                return None

        async def do_platform_fetch():
            try:
                platform_strategy = CrossPlatformStrategy()
                return await platform_strategy.gather_context(client, user_id, deliverable)
            except Exception as e:
                logger.error(f"[HYBRID] Platform fetch failed: {e}")
                return None

        # Execute in parallel
        web_result, platform_result = await asyncio.gather(
            do_web_research(),
            do_platform_fetch(),
            return_exceptions=True,
        )

        # Process web research results
        if web_result and not isinstance(web_result, Exception):
            if web_result.success and web_result.content:
                context_parts.append(f"[WEB RESEARCH]\n{web_result.content}")
                result.sources_used.extend([f"web:{url}" for url in web_result.sources[:5]])
                result.summary["search_queries"] = web_result.search_queries
                result.summary["web_sources_count"] = len(web_result.sources)
            elif web_result.error:
                result.errors.append(f"Web research failed: {web_result.error}")
        elif isinstance(web_result, Exception):
            result.errors.append(f"Web research exception: {web_result}")

        # Process platform results
        if platform_result and not isinstance(platform_result, Exception):
            if platform_result.content and platform_result.content != "(No context available)":
                context_parts.append(f"[PLATFORM DATA]\n{platform_result.content}")
                result.sources_used.extend(platform_result.sources_used)
                result.items_fetched += platform_result.items_fetched
                result.summary["platform_providers"] = platform_result.summary.get("providers_fetched", [])
        elif isinstance(platform_result, Exception):
            result.errors.append(f"Platform fetch exception: {platform_result}")

        # Add user memories (already included in platform_result, but add if no platform sources)
        if not platform_result or isinstance(platform_result, Exception):
            memories = await _get_user_memories(client, user_id)
            if memories:
                context_parts.append(f"[USER CONTEXT]\n{memories}")

        # Add past version feedback
        past_context = await _get_past_versions_context(client, deliverable.get("id"))
        if past_context:
            context_parts.append(past_context)

        result.content = "\n\n---\n\n".join(context_parts) if context_parts else "(No context available)"
        result.summary["sources_used"] = result.sources_used
        result.summary["items_fetched"] = result.items_fetched

        logger.info(
            f"[HYBRID] Context gathered: web_sources={result.summary.get('web_sources_count', 0)}, "
            f"platform_sources={len([s for s in result.sources_used if s.startswith('platform:')])}"
        )

        return result


# =============================================================================
# Strategy Selection
# =============================================================================

def get_execution_strategy(deliverable: dict) -> ExecutionStrategy:
    """
    Select execution strategy based on type_classification.binding.

    Args:
        deliverable: Deliverable dict with type_classification

    Returns:
        Appropriate ExecutionStrategy instance
    """
    classification = deliverable.get("type_classification", {})
    binding = classification.get("binding", "cross_platform")

    strategy_map = {
        "platform_bound": PlatformBoundStrategy,
        "cross_platform": CrossPlatformStrategy,
        "research": ResearchStrategy,
        "hybrid": HybridStrategy,
    }

    strategy_class = strategy_map.get(binding, CrossPlatformStrategy)
    strategy = strategy_class()

    logger.info(f"[STRATEGY] Selected: {strategy.strategy_name} for binding={binding}")

    return strategy


# =============================================================================
# Helper Functions
# =============================================================================

def _parse_last_run_at(last_run_at) -> Optional[datetime]:
    """Parse last_run_at string to datetime."""
    if not last_run_at or not isinstance(last_run_at, str):
        return None

    try:
        if last_run_at.endswith("Z"):
            last_run_at = last_run_at[:-1] + "+00:00"
        return datetime.fromisoformat(last_run_at)
    except (ValueError, TypeError):
        return None


async def _get_user_memories(client, user_id: str) -> str:
    """Get relevant user memories for context."""
    try:
        result = (
            client.table("memories")
            .select("content, tags")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .in_("source_type", ["user_stated", "chat", "conversation", "preference"])
            .order("importance", desc=True)
            .limit(20)
            .execute()
        )

        if not result.data:
            return ""

        lines = []
        for mem in result.data:
            content = mem.get("content", "")
            tags = mem.get("tags", [])
            if tags:
                lines.append(f"- {content} [{', '.join(tags)}]")
            else:
                lines.append(f"- {content}")

        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"[STRATEGY] Failed to fetch memories: {e}")
        return ""


async def _get_past_versions_context(client, deliverable_id: str) -> str:
    """Get past version feedback for learning."""
    if not deliverable_id:
        return ""

    try:
        from services.deliverable_pipeline import get_past_versions_context
        return await get_past_versions_context(client, deliverable_id)
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
                    client.table("documents")
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

    elif source_type == "url":
        url = source.get("value", "")
        if url:
            # Phase 2: Use WebFetch primitive
            return f"[URL SOURCE: {url}]\n(URL fetching deferred to Phase 2)"

    return ""
