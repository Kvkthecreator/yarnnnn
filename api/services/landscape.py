"""
Landscape Discovery Service

Discovers available resources (channels, pages) from connected platforms.
Used by:
- GET /integrations/{provider}/landscape (on-demand from context page)
- Platform worker (after content sync to keep landscape fresh)

ADR-079: Smart auto-selection — when landscape is first discovered and no
sources are selected, auto-selects the most valuable sources up to tier limit.

ADR-131: Gmail and Calendar sunset — only Slack and Notion remain.

No LLM calls — purely platform API reads.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _extract_notion_title(page: dict) -> str:
    """Extract title from Notion page object."""
    props = page.get("properties", {})
    for key in ["title", "Title", "Name", "name"]:
        if key in props:
            title_prop = props[key]
            if isinstance(title_prop, dict):
                title_array = title_prop.get("title") or title_prop.get("rich_text", [])
                if isinstance(title_array, list) and title_array:
                    return title_array[0].get("plain_text", "Untitled")
            elif isinstance(title_prop, str):
                return title_prop
    return "Untitled"


def _extract_notion_parent_type(page: dict) -> str:
    """Extract parent type from Notion page object."""
    parent = page.get("parent", {})
    if "workspace" in parent:
        return "workspace"
    elif "page_id" in parent:
        return "page"
    elif "database_id" in parent:
        return "database"
    return "unknown"


async def discover_landscape(provider: str, user_id: str, integration: dict) -> dict:
    """
    Discover resources from a provider.

    Args:
        provider: Platform name (slack, notion)
        user_id: User UUID
        integration: Row from platform_connections with credentials

    Returns:
        {"resources": [{"id": "...", "name": "...", "type": "...", "metadata": {...}}]}
    """
    from integrations.core.tokens import get_token_manager

    token_manager = get_token_manager()

    if provider == "slack":
        from integrations.core.slack_client import get_slack_client

        bot_token = token_manager.decrypt(integration["credentials_encrypted"])
        slack_client = get_slack_client()

        # ADR-077: Use paginated channel list for full discovery
        channels = await slack_client.list_channels_paginated(bot_token=bot_token)

        resources = []
        for channel in channels:
            resources.append({
                "id": channel.get("id"),
                "name": f"#{channel.get('name', '')}",
                "type": "channel",
                "metadata": {
                    "is_private": channel.get("is_private", False),
                    "num_members": channel.get("num_members", 0),
                    "topic": channel.get("topic"),
                    "purpose": channel.get("purpose"),
                }
            })

        return {"resources": resources}

    elif provider == "notion":
        from integrations.core.notion_client import get_notion_client

        auth_token = token_manager.decrypt(integration["credentials_encrypted"])

        try:
            notion_client = get_notion_client()
            # ADR-077: Paginated search for full workspace discovery
            pages = await notion_client.search_paginated(
                access_token=auth_token, query="", max_results=500
            )
        except Exception as e:
            logger.warning(f"[LANDSCAPE] Notion search failed: {e}")
            return {"resources": []}

        resources = []
        for page in pages:
            resources.append({
                "id": page.get("id"),
                "name": _extract_notion_title(page),
                "type": "page" if page.get("object") == "page" else "database",
                "metadata": {
                    "parent_type": _extract_notion_parent_type(page),
                    "last_edited": page.get("last_edited_time"),
                    "url": page.get("url")
                }
            })

        return {"resources": resources}

    elif provider == "github":
        # ADR-147: GitHub landscape discovery — list user's repos
        from integrations.core.github_client import get_github_client

        token = token_manager.decrypt(integration["credentials_encrypted"])
        github_client = get_github_client()

        try:
            repos = await github_client.list_repos(token=token, max_repos=200)
        except Exception as e:
            logger.warning(f"[LANDSCAPE] GitHub repo listing failed: {e}")
            return {"resources": []}

        if isinstance(repos, dict) and repos.get("error"):
            logger.warning(f"[LANDSCAPE] GitHub API error: {repos}")
            return {"resources": []}

        resources = []
        for repo in repos:
            if not isinstance(repo, dict):
                continue
            full_name = repo.get("full_name", "")
            if not full_name:
                continue
            resources.append({
                "id": full_name,
                "name": full_name,
                "type": "repository",
                "metadata": {
                    "description": repo.get("description") or "",
                    "language": repo.get("language"),
                    "is_fork": repo.get("fork", False),
                    "is_archived": repo.get("archived", False),
                    "open_issues": repo.get("open_issues_count", 0),
                    "stars": repo.get("stargazers_count", 0),
                    "updated_at": repo.get("updated_at", ""),
                    "is_private": repo.get("private", False),
                    "owner_type": "user" if repo.get("owner", {}).get("type") == "User" else "org",
                },
            })

        return {"resources": resources}

    return {"resources": []}


def compute_smart_defaults(
    provider: str,
    resources: list[dict],
    max_sources: int,
) -> list[dict]:
    """
    ADR-079 + ADR-113: Auto-select the most valuable sources up to tier limit.

    Called when landscape is first discovered and no sources are selected,
    or when backfilling existing users. Returns a list of selected source
    objects ({"id": ..., "name": ..., "type": ..., "platform": ...}).

    Uses only metadata already available from landscape discovery (zero extra
    API calls). The agent decides what's important within synced content —
    this function only decides which sources to sync.

    Selection heuristics per platform:
    - Slack: Score by work-signal (name patterns, purpose text, member count).
             Deprioritize social/noise channels. Boost team/project channels.
    - Notion: Boost databases and workspace-level pages over nested untitled pages.
              Sort by last_edited within tiers.
    """
    if not resources:
        return []

    selected = []

    if provider == "slack":
        ranked = _score_slack_channels(resources)
        for r in ranked[:max_sources]:
            selected.append({
                "id": r["id"],
                "name": r.get("name", ""),
                "type": r.get("type", "channel"),
                "platform": "slack",
            })

    elif provider == "notion":
        ranked = _score_notion_pages(resources)
        for r in ranked[:max_sources]:
            selected.append({
                "id": r["id"],
                "name": r.get("name", ""),
                "type": r.get("type", "page"),
                "platform": "notion",
            })

    elif provider == "github":
        # ADR-147: Score repos by relevance for solo founders
        ranked = _score_github_repos(resources)
        for r in ranked[:max_sources]:
            selected.append({
                "id": r["id"],
                "name": r.get("name", ""),
                "type": "repository",
                "platform": "github",
            })

    return selected


# =============================================================================
# Slack Channel Scoring
# =============================================================================

# Channels whose names match these patterns are likely social/noise — deprioritize
_SLACK_NOISE_PATTERNS = {
    "random", "social", "watercooler", "off-topic", "offtopic",
    "fun", "music", "pets", "food", "games", "memes", "sports",
    "books", "movies", "photos", "birthdays", "celebrations",
}

# Channels whose names match these patterns are likely work-relevant — boost
_SLACK_WORK_PATTERNS = {
    "team", "eng", "engineering", "product", "design", "ops", "devops",
    "infrastructure", "infra", "security", "data", "analytics", "platform",
    "backend", "frontend", "mobile", "api", "deploy", "release",
    "incident", "oncall", "on-call", "alerts", "monitoring",
    "standup", "stand-up", "sync", "all-hands", "allhands",
    "announcements", "announce", "general", "company", "org",
    "leadership", "exec", "strategy", "planning", "roadmap",
    "project", "sprint", "launch", "growth", "marketing", "sales",
    "support", "customers", "feedback", "hiring", "recruiting",
}

# Purpose/topic text signals that suggest work channels
_SLACK_WORK_KEYWORDS = {
    "project", "team", "sprint", "deploy", "release", "incident",
    "standup", "sync", "updates", "decisions", "planning", "roadmap",
    "engineering", "product", "design", "support", "customers",
}

# Purpose/topic text signals that suggest noise channels
_SLACK_NOISE_KEYWORDS = {
    "fun", "random", "off-topic", "social", "non-work", "watercooler",
    "memes", "pets", "games", "music", "food",
}


def _score_slack_channels(resources: list[dict]) -> list[dict]:
    """
    Score Slack channels by work-relevance using available metadata.

    Scoring (higher = more likely to be selected):
    - Base: num_members (normalized, minor factor)
    - Boost: channel name matches work patterns (+3)
    - Boost: purpose/topic text contains work keywords (+2)
    - Penalty: channel name matches noise patterns (-5)
    - Penalty: purpose/topic text contains noise keywords (-3)
    - Penalty: private channels with <3 members (-1, likely DM-like)
    """
    scored = []
    max_members = max(
        (r.get("metadata", {}).get("num_members", 0) for r in resources),
        default=1,
    ) or 1  # avoid division by zero

    for r in resources:
        meta = r.get("metadata", {})
        name = r.get("name", "").lower().lstrip("#")
        num_members = meta.get("num_members", 0)
        is_private = meta.get("is_private", False)
        purpose = (meta.get("purpose") or "").lower() if isinstance(meta.get("purpose"), str) else ""
        topic = (meta.get("topic") or "").lower() if isinstance(meta.get("topic"), str) else ""
        context_text = f"{purpose} {topic}"

        # Base score: member count normalized to 0-2 range
        score = (num_members / max_members) * 2

        # Name-based signals
        name_parts = set(name.replace("-", " ").replace("_", " ").split())
        if name_parts & _SLACK_WORK_PATTERNS:
            score += 3
        if name_parts & _SLACK_NOISE_PATTERNS:
            score -= 5

        # Purpose/topic text signals
        context_words = set(context_text.replace("-", " ").replace("_", " ").split())
        if context_words & _SLACK_WORK_KEYWORDS:
            score += 2
        if context_words & _SLACK_NOISE_KEYWORDS:
            score -= 3

        # Private channels with very few members are likely DM-like
        if is_private and num_members < 3:
            score -= 1

        scored.append((score, r))

    # Sort by score descending, then by member count as tiebreaker
    scored.sort(key=lambda x: (x[0], x[1].get("metadata", {}).get("num_members", 0)), reverse=True)
    return [r for _, r in scored]


# =============================================================================
# Notion Page Scoring
# =============================================================================

def _score_notion_pages(resources: list[dict]) -> list[dict]:
    """
    Score Notion pages by likely relevance using available metadata.

    Scoring:
    - Boost: databases over pages (+3, databases are usually project trackers / meeting notes)
    - Boost: workspace-level pages (+2, top-level = org-important)
    - Penalty: Untitled pages (-3, usually scratch / empty)
    - Base: last_edited recency (more recent = more relevant)
    """
    scored = []

    for r in resources:
        meta = r.get("metadata", {})
        name = r.get("name", "")
        resource_type = r.get("type", "page")
        parent_type = meta.get("parent_type", "")
        edited = meta.get("last_edited", "") or ""

        score = 0

        # Type: databases are typically higher-value (project boards, wikis, trackers)
        if resource_type == "database":
            score += 3

        # Hierarchy: workspace-level pages are usually important
        if parent_type == "workspace":
            score += 2

        # Name quality
        if name.startswith("Untitled") or not name.strip():
            score -= 3

        scored.append((score, edited, r))

    # Sort by score descending, then by last_edited descending (recent first)
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [r for _, _, r in scored]


# =============================================================================
# GitHub Repo Scoring (ADR-147)
# =============================================================================

def _score_github_repos(resources: list[dict]) -> list[dict]:
    """
    Score GitHub repos by relevance for solo founders.

    Scoring:
    - Boost: user-owned (not fork, not archived) (+3)
    - Boost: has open issues (+1, signals active work)
    - Boost: recently updated (+2 if updated in last 30d)
    - Penalty: forks (-4)
    - Penalty: archived (-5)
    - Base: stars as tiebreaker
    """
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    thirty_days_ago = (now - timedelta(days=30)).isoformat()
    scored = []

    for r in resources:
        meta = r.get("metadata", {})
        score = 0

        # Fork / archive penalties
        if meta.get("is_archived"):
            score -= 5
        if meta.get("is_fork"):
            score -= 4

        # Owner boost (user-owned, not fork)
        if meta.get("owner_type") == "user" and not meta.get("is_fork"):
            score += 3

        # Active work signals
        open_issues = meta.get("open_issues", 0)
        if open_issues > 0:
            score += 1
        if open_issues > 5:
            score += 1

        # Recency boost
        updated = meta.get("updated_at", "")
        if updated and updated >= thirty_days_ago:
            score += 2

        scored.append((score, meta.get("stars", 0), r))

    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [r for _, _, r in scored]


async def refresh_landscape(
    client,
    user_id: str,
    provider: str,
    integration: dict,
) -> bool:
    """
    Refresh landscape for a platform, preserving selected_sources.

    Called after content sync to keep the landscape in sync with
    the actual platform state.

    Args:
        client: Supabase service-role client
        user_id: User UUID
        provider: Platform name
        integration: Row from platform_connections

    Returns:
        True if landscape was updated, False on error
    """
    try:
        new_landscape = await discover_landscape(provider, user_id, integration)

        if not new_landscape.get("resources"):
            logger.info(f"[LANDSCAPE] No resources discovered for {provider} user {user_id[:8]}, skipping update")
            return False

        # Re-read selected_sources from DB (not the stale integration dict)
        # to avoid overwriting user changes made during sync
        fresh = client.table("platform_connections").select(
            "landscape"
        ).eq("id", integration["id"]).limit(1).execute()

        fresh_landscape = (fresh.data[0].get("landscape") or {}) if fresh.data else {}
        selected_sources = fresh_landscape.get("selected_sources", [])

        # Filter out stale source IDs that no longer exist in the new landscape
        # selected_sources can be dicts ({"id": ..., "name": ...}) or plain strings
        new_resource_ids = {r["id"] for r in new_landscape["resources"]}
        valid_sources = [
            s for s in selected_sources
            if (s.get("id") if isinstance(s, dict) else s) in new_resource_ids
        ]

        if len(valid_sources) < len(selected_sources):
            removed = len(selected_sources) - len(valid_sources)
            logger.info(f"[LANDSCAPE] Pruned {removed} stale source(s) for {provider} user {user_id[:8]}")

        # ADR-079: If no sources are selected after pruning, auto-select smart defaults
        if valid_sources:
            new_landscape["selected_sources"] = valid_sources
        else:
            from services.platform_limits import get_limits_for_user, PROVIDER_LIMIT_MAP
            limits = get_limits_for_user(client, user_id)
            limit_field = PROVIDER_LIMIT_MAP.get(provider, "slack_channels")
            max_sources = getattr(limits, limit_field, 5)
            if max_sources == -1:
                max_sources = 999
            smart_selected = compute_smart_defaults(
                provider, new_landscape["resources"], max_sources
            )
            new_landscape["selected_sources"] = smart_selected
            logger.info(
                f"[LANDSCAPE] Auto-selected {len(smart_selected)} sources for "
                f"{provider} user {user_id[:8]} (no prior selection)"
            )

        client.table("platform_connections").update({
            "landscape": new_landscape,
            "landscape_discovered_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", integration["id"]).execute()

        logger.info(
            f"[LANDSCAPE] Refreshed {provider} for user {user_id[:8]}: "
            f"{len(new_landscape['resources'])} resources, "
            f"{len(new_landscape.get('selected_sources', []))} selected"
        )
        return True

    except Exception as e:
        logger.warning(f"[LANDSCAPE] Refresh failed for {provider} user {user_id[:8]}: {e}")
        return False
