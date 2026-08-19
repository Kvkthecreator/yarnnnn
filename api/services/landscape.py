"""
Landscape Discovery Service

Discovers available resources (channels, pages) from connected platforms.
Used by:
- GET /integrations/{provider}/landscape (on-demand from context page)
- Platform worker (after content sync to keep landscape fresh)

ADR-079's smart scoring survives ONLY as the `recommended` badge on the
landscape response. Auto-SELECTION is DELETED (2026-08-19): a selection is
operator consent — the capture writer's mandate and (ADR-576) a reach bound —
never a heuristic's pre-check.

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

        # A failed search RAISES (the route 502s with a reconnect hint). It used
        # to be swallowed into {"resources": []} — which made a revoked token
        # indistinguishable from "zero pages shared", and turned the operator's
        # Refresh into a loop that re-ran the same silent failure. An honest
        # empty is only the SUCCESS case: a valid token that enumerates nothing
        # (Notion grants access page-by-page).
        notion_client = get_notion_client()
        # ADR-077: Paginated search for full workspace discovery
        pages = await notion_client.search_paginated(
            access_token=auth_token, query="", max_results=500
        )

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

        # Same discipline as the notion branch: a failed listing RAISES rather
        # than masquerading as an empty landscape.
        repos = await github_client.list_repos(token=token, max_repos=200)

        if isinstance(repos, dict) and repos.get("error"):
            raise RuntimeError(f"GitHub repo listing failed: {repos.get('error')}")

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
    ADR-079 scoring: rank sources by likely relevance. Since the 2026-08-19
    auto-selection deletion this feeds ONLY the `recommended` badge on the
    landscape response — the result is never written into selected_sources.
    Returns a list of source objects ({"id": ..., "name": ..., "type": ...,
    "platform": ...}).

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


