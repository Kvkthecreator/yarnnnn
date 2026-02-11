"""
Execution Strategies - ADR-045 Type-Aware Orchestration

Determines HOW a deliverable is executed based on its type_classification.binding.

Strategies:
- platform_bound: Single platform gatherer → DeliverableAgent
- cross_platform: Parallel platform gatherers → DeliverableAgent
- research: (Future) Web researcher → ResearchSynthesizer
- hybrid: (Future) Research + Platform → HybridSynthesizer

Phase 1: Strategy selection and parallel fetching
Phase 2: Tool-equipped agents (web.search, web.fetch)
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

    Phase 2: Will use web.search and web.fetch tools.
    Currently falls back to cross-platform behavior.
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
        # Phase 1: Fall back to cross-platform
        # Phase 2: Add WebSearch/WebFetch when primitives are ready
        logger.info("[RESEARCH] Research strategy not yet implemented, falling back to cross-platform")

        fallback = CrossPlatformStrategy()
        result = await fallback.gather_context(client, user_id, deliverable)
        result.summary["strategy"] = "research (fallback: cross_platform)"
        result.summary["note"] = "WebSearch/WebFetch not yet implemented"

        return result


class HybridStrategy(ExecutionStrategy):
    """
    Strategy for hybrid deliverables.

    Combines research (web) with platform grounding.
    Phase 2: Will use web tools + platform fetch in parallel.
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
        # Phase 1: Fall back to cross-platform
        logger.info("[HYBRID] Hybrid strategy not yet implemented, falling back to cross-platform")

        fallback = CrossPlatformStrategy()
        result = await fallback.gather_context(client, user_id, deliverable)
        result.summary["strategy"] = "hybrid (fallback: cross_platform)"
        result.summary["note"] = "Web research not yet implemented"

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
