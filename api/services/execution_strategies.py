"""
Execution Strategies - ADR-045 Type-Aware Orchestration + ADR-073 Unified Fetch + ADR-081 Consolidation

Determines HOW a deliverable is executed based on its type_classification.binding.

Strategies:
- platform_bound: Single platform reader → headless agent
- cross_platform: Multi-platform reader → headless agent
- research: Platform grounding + research_directive → headless agent uses WebSearch (ADR-081)
- hybrid: Platform context + research_directive → headless agent uses WebSearch (ADR-081)

ADR-073: All platform reads come from platform_content (no live API calls).
ADR-081: Research/hybrid strategies no longer call web_research.py. Instead they pass
a research_directive to the headless agent, which uses the WebSearch primitive directly.
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

    Single platform focus (e.g., slack_channel_digest, gmail_inbox_brief,
    meeting_prep, weekly_calendar_preview).
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
        from services.platform_content import get_content_summary_for_generation

        classification = deliverable.get("type_classification", {})
        primary_platform = classification.get("primary_platform")
        sources = deliverable.get("sources", [])
        deliverable_id = deliverable.get("id")

        context_parts = []
        result = GatheredContext(content="", summary={"strategy": self.strategy_name})

        # Filter sources to primary platform
        # The "google" connection provides both "gmail" and "calendar" content,
        # so a source with provider="google" should match primary_platform="calendar" or "gmail"
        google_platforms = {"gmail", "calendar"}

        platform_sources = [
            s for s in sources
            if s.get("type") == "integration_import"
            and (
                s.get("provider") == primary_platform
                or (s.get("provider") == "google" and primary_platform in google_platforms)
            )
        ]

        if not platform_sources and sources:
            platform_sources = [
                s for s in sources if s.get("type") == "integration_import"
            ]
            logger.info(f"[PLATFORM_BOUND] No {primary_platform} sources, using all {len(platform_sources)} integration sources")

        # ADR-073: Read from platform_content instead of live API calls
        if platform_sources:
            try:
                content_text, content_ids = await get_content_summary_for_generation(
                    db_client=client,
                    user_id=user_id,
                    deliverable_sources=platform_sources,
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
        from services.platform_content import get_content_summary_for_generation

        sources = deliverable.get("sources", [])
        deliverable_id = deliverable.get("id")

        result = GatheredContext(content="", summary={"strategy": self.strategy_name})

        integration_sources = [s for s in sources if s.get("type") == "integration_import"]
        other_sources = [s for s in sources if s.get("type") != "integration_import"]

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
                    deliverable_sources=integration_sources,
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
        past_context = await _get_past_versions_context(client, deliverable_id)
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
    Strategy for research deliverables.

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
        deliverable: dict,
    ) -> GatheredContext:
        title = deliverable.get("title", "")
        description = deliverable.get("description", "")
        sources = deliverable.get("sources", [])

        result = GatheredContext(content="", summary={"strategy": self.strategy_name})
        context_parts = []

        # 1. Optional: Get platform grounding from sources (if any configured)
        integration_sources = [s for s in sources if s.get("type") == "integration_import"]
        if integration_sources:
            logger.info(f"[RESEARCH] Adding platform grounding from {len(integration_sources)} sources")
            platform_strategy = CrossPlatformStrategy()
            platform_result = await platform_strategy.gather_context(client, user_id, deliverable)

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
        past_context = await _get_past_versions_context(client, deliverable.get("id"))
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


class HybridStrategy(ExecutionStrategy):
    """
    Strategy for hybrid deliverables.

    ADR-081: Gathers platform context, then passes a research_directive
    so the headless agent combines web research with platform grounding.
    No separate web research call — the agent handles both.
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
        title = deliverable.get("title", "")
        description = deliverable.get("description", "")

        logger.info(f"[HYBRID] Gathering platform context: {title[:50]}...")

        # Delegate platform context gathering to CrossPlatformStrategy
        platform_strategy = CrossPlatformStrategy()
        result = await platform_strategy.gather_context(client, user_id, deliverable)

        # Override strategy name
        result.summary["strategy"] = self.strategy_name

        # ADR-081: Build research directive for headless agent
        result.summary["research_directive"] = _build_research_directive(title, description)

        logger.info(
            f"[HYBRID] Context gathered (ADR-081): "
            f"platform_sources={len(result.sources_used)}, "
            f"items={result.items_fetched}, research_directive=yes"
        )

        return result


def _build_research_directive(title: str, description: str) -> str:
    """
    Build a research directive string for the headless agent (ADR-081).

    This replaces the standalone RESEARCH_SYSTEM_PROMPT from web_research.py.
    The headless agent receives this and uses WebSearch to investigate.
    """
    directive = f"This deliverable requires web research. Use WebSearch to investigate.\n\nResearch objective: {title}"
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

async def _get_user_memories(client, user_id: str) -> str:
    """Get user context entries for prompt injection."""
    try:
        # ADR-059: Read from user_context (fact/instruction/preference keys)
        result = (
            client.table("user_context")
            .select("key, value")
            .eq("user_id", user_id)
            .limit(20)
            .execute()
        )

        if not result.data:
            return ""

        lines = []
        for row in result.data:
            key = row.get("key", "")
            value = row.get("value", "")
            if key.startswith(("fact:", "instruction:", "preference:")):
                lines.append(f"- {value}")

        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"[STRATEGY] Failed to fetch user context: {e}")
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

    elif source_type == "url":
        url = source.get("value", "")
        if url:
            # Phase 2: Use WebFetch primitive
            return f"[URL SOURCE: {url}]\n(URL fetching deferred to Phase 2)"

    return ""
