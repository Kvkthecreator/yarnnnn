"""
Workspace Directory Registry — ADR-152: Unified Directory Registry (v2)

Version: 3.0 (2026-04-04)
Changelog:
  v3.0 (2026-04-04) — ADR-158: Platform observation domains (slack, notion, github).
                       Temporal context directories owned by platform bots. Per-source
                       entity structure (channel/page/repo subfolders with _tracker.md).
                       temporal: True flag distinguishes from canonical domains.
  v2.1 (2026-04-03) — ADR-157: assets/ subfolder for each entity-bearing context domain.
                       First-class, visible directory for visual assets (favicons, charts,
                       generated images). Replaces entity_assets/shared_assets documentation
                       with live assets_folder convention. Scaffolded at onboarding.
  v2.0 (2026-04-01) — ADR-154: Entity tracker (_tracker.md) for entity-bearing domains.
                       Pipeline-maintained materialized view of domain contents.
                       get_tracker_template(), has_entity_tracker(), build_tracker_md() added.
  v1.0 (2026-03-31) — Initial: unified registry absorbing CONTEXT_DOMAINS from ADR-151.
                       Three directory types: user_contributed (uploads), context (6 domains),
                       output (reports, briefs). Replaces domain_registry.py.

Single source of truth for ALL workspace content directories. Governs:
  /workspace/uploads/    — user-contributed reference material
  /workspace/context/    — agent-accumulated intelligence substrate (9 domains)

Two directory types:
  user_contributed — user uploads, permanent, not agent-managed
  context          — agent-accumulated, entity-structured, grows with execution

Context domains split into two classes:
  canonical  — durable, steward-owned (competitors, market, relationships, projects, content_research, signals)
  temporal   — platform observations, bot-owned (slack, notion, github) — marked with temporal: True

Design principles:
  1. One registry governs all workspace directories
  2. Type field (user_contributed/context/output) determines behavior
  3. Context directories have entity structure — per-entity subfolders
  4. Output directories have category structure — by deliverable type
  5. Directories grow dynamically — registry is starting set, TP can add more
  6. Signal log is cross-domain — temporal events from any context domain

Malleability:
  - Registry KEYS are stable identifiers (e.g., "reports", "competitors")
  - display_name, description, and path can be user-customized by TP at runtime
  - Task types reference keys, not paths — renaming a path doesn't break references
  - Entity structure templates are starting points — agents create beyond them
  - TP can add new directories dynamically (new context domains, output categories)

Expansion process:
  1. Add directory dict to WORKSPACE_DIRECTORIES below
  2. Set type: user_contributed | context | output
  3. For context: define entity_structure, synthesis_file
  4. For output: define naming_convention, index_file
  5. Update task types (context_reads/context_writes/output_category)
  6. Update docs/architecture/workspace-conventions.md
  7. Increment version comment above

Current ICP: solo founder / small team. Subject to expansion.

Canonical references:
  - docs/adr/ADR-152-unified-directory-registry.md
  - docs/architecture/workspace-conventions.md
  - docs/architecture/registry-matrix.md
"""

from __future__ import annotations

from typing import Any, Optional


# =============================================================================
# Workspace Directory Registry
# =============================================================================

WORKSPACE_DIRECTORIES: dict[str, dict[str, Any]] = {

    # ── User-Contributed ──

    "uploads": {
        "type": "user_contributed",
        "path": "uploads",
        "display_name": "Uploads",
        "description": "User-uploaded reference material (PDFs, docs, images)",
        "managed_by": "user",
    },

    # ── Context Domains (agent-accumulated intelligence) ──

    "competitors": {
        "type": "context",
        "path": "context/competitors",
        "display_name": "Competitors",
        "description": "Companies and products we compete with",
        "managed_by": "agent",
        "entity_type": "company",
        "entity_structure": {
            "profile.md": "# {name}\n\n## Overview\n\n## Funding & Size\n\n## Leadership\n",
            "signals.md": "# Signals — {name}\n<!-- Dated findings, newest first -->\n",
            "product.md": "# Product — {name}\n\n## Offering\n\n## Pricing\n\n## Recent Changes\n",
            "strategy.md": "# Strategy — {name}\n\n## Positioning\n\n## Threat Assessment\n\n## Opportunities\n",
        },
        "assets_folder": True,
        "synthesis_file": "landscape.md",
        "synthesis_template": (
            "# Competitive Landscape\n\n"
            "## Market Map\n\n"
            "## Key Trends\n\n"
            "## Our Position\n"
        ),
        "tracker_file": "_tracker.md",
    },

    "market": {
        "type": "context",
        "path": "context/market",
        "display_name": "Market",
        "description": "Market segments, sizing, trends, and opportunities",
        "managed_by": "agent",
        "entity_type": "segment",
        "entity_structure": {
            "analysis.md": "# {name}\n\n## Market Size & Growth\n\n## Key Players\n\n## Trends\n\n## Opportunities\n",
        },
        "assets_folder": True,
        "synthesis_file": "overview.md",
        "synthesis_template": (
            "# Market Overview\n\n"
            "## Landscape Summary\n\n"
            "## Cross-Segment Patterns\n\n"
            "## Strategic Implications\n"
        ),
        "tracker_file": "_tracker.md",
    },

    "relationships": {
        "type": "context",
        "path": "context/relationships",
        "display_name": "Relationships",
        "description": "People and organizations we work with",
        "managed_by": "agent",
        "entity_type": "contact",
        "entity_structure": {
            "profile.md": "# {name}\n\n## Role & Company\n\n## How We Know Them\n\n## Notes\n",
            "history.md": "# Interaction History — {name}\n<!-- Dated, newest first -->\n",
            "open-items.md": "# Open Items — {name}\n\n## Follow-ups Due\n\n## Commitments Made\n",
        },
        "assets_folder": True,
        "synthesis_file": "portfolio.md",
        "synthesis_template": (
            "# Relationship Portfolio\n\n"
            "## Health Overview\n\n"
            "## At-Risk\n\n"
            "## Follow-Up Priorities\n"
        ),
        "tracker_file": "_tracker.md",
    },

    "projects": {
        "type": "context",
        "path": "context/projects",
        "display_name": "Projects",
        "description": "Internal initiatives, workstreams, and milestones",
        "managed_by": "agent",
        "entity_type": "project",
        "entity_structure": {
            "status.md": "# {name}\n\n## Current State\n\n## Progress\n\n## Blockers\n\n## Next Steps\n",
            "milestones.md": "# Milestones — {name}\n\n## Achieved\n\n## Upcoming\n",
        },
        "assets_folder": True,
        "synthesis_file": "status.md",
        "synthesis_template": (
            "# Project Portfolio Status\n\n"
            "## Overall Health\n\n"
            "## Active Blockers\n\n"
            "## Resource Needs\n"
        ),
        "tracker_file": "_tracker.md",
    },

    "content_research": {
        "type": "context",
        "path": "context/content",
        "display_name": "Content Research",
        "description": "Research, drafts, and creative work in progress",
        "managed_by": "agent",
        "entity_type": "topic",
        "entity_structure": {
            "research.md": "# Research — {name}\n\n## Key Points\n\n## Sources\n\n## Audience Considerations\n",
            "outline.md": "# Outline — {name}\n\n## Key Messages\n\n## Structure\n\n## Tone\n",
        },
        "assets_folder": True,
        "synthesis_file": None,
        "synthesis_template": None,
        "tracker_file": "_tracker.md",
    },

    "signals": {
        "type": "context",
        "path": "context/signals",
        "display_name": "Signals",
        "description": "Temporal signal log — what happened when, across all domains",
        "managed_by": "agent",
        "entity_type": None,
        "entity_structure": None,
        "synthesis_file": None,
        "synthesis_template": None,
        "signal_log": True,
    },

    # ── Platform Observation Domains (ADR-158: temporal, bot-owned) ──
    # Temporal awareness from external platforms. NOT canonical — TP reads these
    # for situational awareness, but they don't feed into steward domains
    # automatically. Each bot owns one platform directory.
    # Cross-pollination into canonical domains is explicitly out of scope.

    "slack": {
        "type": "context",
        "path": "context/slack",
        "display_name": "Slack",
        "description": "Temporal observations from Slack channels — decisions, signals, activity",
        "managed_by": "agent",
        "temporal": True,
        "ttl_days": 14,  # Slack is high-volume stream — 2 weeks of relevance
        "entity_type": "channel",
        "entity_structure": {
            "latest.md": (
                "# {name}\n\n"
                "<!-- Most recent observation from this channel -->\n"
                "<!-- Updated by Slack Bot digest task -->\n"
            ),
        },
        "synthesis_file": None,
        "synthesis_template": None,
        "tracker_file": "_tracker.md",
    },

    "notion": {
        "type": "context",
        "path": "context/notion",
        "display_name": "Notion",
        "description": "Temporal observations from Notion pages — changes, updates, content state",
        "managed_by": "agent",
        "temporal": True,
        "ttl_days": 30,  # Notion changes are slower — 1 month of relevance
        "entity_type": "page",
        "entity_structure": {
            "latest.md": (
                "# {name}\n\n"
                "<!-- Most recent observation from this page -->\n"
                "<!-- Updated by Notion Bot digest task -->\n"
            ),
        },
        "synthesis_file": None,
        "synthesis_template": None,
        "tracker_file": "_tracker.md",
    },

    "github": {
        "type": "context",
        "path": "context/github",
        "display_name": "GitHub",
        "description": "Temporal observations + reference data from GitHub repos — issues, PRs, releases, README, metadata",
        "managed_by": "agent",
        "temporal": True,
        "ttl_days": 30,  # Activity is temporal (14d), but reference files are durable (no expiry) — use 30d as soft ceiling
        "entity_type": "repo",
        "entity_depth": 2,  # owner/repo — two-level entity slug
        "entity_structure": {
            # Temporal (updated every cycle)
            "latest.md": (
                "# {name} — Activity\n\n"
                "<!-- Issues, PRs, and activity from this repo -->\n"
                "<!-- Updated by GitHub Bot every digest cycle -->\n"
            ),
            "releases.md": (
                "# {name} — Releases\n\n"
                "<!-- Recent releases and what shipped -->\n"
                "<!-- Updated by GitHub Bot every digest cycle -->\n"
            ),
            # Reference (updated on first run + weekly refresh)
            "readme.md": (
                "# {name} — README Summary\n\n"
                "<!-- What this project is, key features, target audience -->\n"
                "<!-- Updated by GitHub Bot on first run + weekly -->\n"
            ),
            "metadata.md": (
                "# {name} — Repository Metadata\n\n"
                "<!-- Description, topics, language, stars, license -->\n"
                "<!-- Updated by GitHub Bot on first run + weekly -->\n"
            ),
        },
        "synthesis_file": None,
        "synthesis_template": None,
        "tracker_file": "_tracker.md",
    },
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_directory(key: str) -> Optional[dict[str, Any]]:
    """Look up a workspace directory by key. Returns None if not found."""
    return WORKSPACE_DIRECTORIES.get(key)


def list_directories(dir_type: Optional[str] = None) -> list[dict[str, Any]]:
    """List workspace directories, optionally filtered by type.

    Args:
        dir_type: None (all), "user_contributed", "context", or "output"
    """
    result = []
    for key, d in WORKSPACE_DIRECTORIES.items():
        if dir_type and d.get("type") != dir_type:
            continue
        result.append({"key": key, **d})
    return result


def get_directory_path(key: str) -> Optional[str]:
    """Get the workspace-relative path for a directory. Returns e.g. 'context/competitors'."""
    d = WORKSPACE_DIRECTORIES.get(key)
    return d["path"] if d else None


# Backwards-compatible aliases for callers still using domain_registry names
def get_domain(key: str) -> Optional[dict[str, Any]]:
    """Alias for get_directory — backwards compat with domain_registry callers."""
    d = WORKSPACE_DIRECTORIES.get(key)
    return d if d and d.get("type") == "context" else None


def get_domain_folder(key: str) -> Optional[str]:
    """Alias for get_directory_path — backwards compat with domain_registry callers."""
    return get_directory_path(key)


def get_entity_depth(key: str) -> int:
    """Get entity path depth for a domain. Default 1, GitHub is 2 (owner/repo)."""
    d = WORKSPACE_DIRECTORIES.get(key)
    return d.get("entity_depth", 1) if d else 1


def get_entity_template(key: str, entity_name: str) -> dict[str, str]:
    """Get templated entity files for a context directory, with {name} replaced."""
    d = WORKSPACE_DIRECTORIES.get(key)
    if not d or not d.get("entity_structure"):
        return {}
    return {
        filename: template.replace("{name}", entity_name)
        for filename, template in d["entity_structure"].items()
    }


def get_entity_stub_content(
    domain_key: str,
    entity_name: str,
    known_facts: list[str] | None = None,
    source: str = "inferred",
) -> dict[str, str]:
    """Get entity template files enriched with known facts and source tags.

    ADR-155: Creates entity stubs with inferred content + gap markers.
    First section gets known_facts injected; remaining sections get [Needs research].

    Args:
        domain_key: Registry key (e.g., "competitors")
        entity_name: Display name for the entity
        known_facts: List of facts inferred from identity
        source: Source tag (inferred|user_stated|researched)

    Returns:
        {filename: enriched_content} dict
    """
    from datetime import datetime, timezone

    base_templates = get_entity_template(domain_key, entity_name)
    if not base_templates:
        return {}

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    source_tag = f"<!-- source: {source} | date: {date_str} -->"
    facts_text = ""
    if known_facts:
        facts_text = "\n".join(f"- {f}" for f in known_facts)
        facts_text = f"\n{facts_text}\n\n[Inferred from workspace identity — needs research to verify and expand]"
    else:
        facts_text = "\n[Inferred from workspace identity — needs research]"

    enriched = {}
    for i, (filename, template) in enumerate(base_templates.items()):
        content = f"{source_tag}\n{template}"
        if i == 0:
            # First file (usually profile.md/analysis.md): inject facts into first section
            # Find the first ## section and append facts after its header
            sections = content.split("\n## ")
            if len(sections) >= 2:
                # Inject facts after first section header
                first_section_lines = sections[1].split("\n", 1)
                header = first_section_lines[0]
                rest = first_section_lines[1] if len(first_section_lines) > 1 else ""
                sections[1] = f"{header}\n{facts_text}\n{rest}"
                content = "\n## ".join(sections)

            # Mark remaining empty sections with [Needs research]
            content = _mark_empty_sections(content)
        else:
            # Non-primary files: mark all sections as needing research
            content = _mark_empty_sections(content)

        enriched[filename] = content

    return enriched


def _mark_empty_sections(content: str) -> str:
    """Add [Needs research] to sections that have headers but no content."""
    import re
    lines = content.split("\n")
    result = []
    for i, line in enumerate(lines):
        result.append(line)
        # If this is a section header and next line is empty or another header
        if line.startswith("## ") and not line.startswith("## Overview"):
            # Check if section body is empty
            next_content = ""
            for j in range(i + 1, min(i + 3, len(lines))):
                stripped = lines[j].strip()
                if stripped and not stripped.startswith("#") and not stripped.startswith("<!--"):
                    next_content = stripped
                    break
            if not next_content:
                result.append("[Needs research]")
                result.append("")
    return "\n".join(result)


def get_synthesis_content(key: str) -> Optional[tuple[str, str]]:
    """Get the synthesis file path and template for a context directory."""
    d = WORKSPACE_DIRECTORIES.get(key)
    if not d or not d.get("synthesis_file"):
        return None
    return (d["synthesis_file"], d.get("synthesis_template") or "")


def get_output_category_path(category: str) -> Optional[str]:
    """DEPRECATED (ADR-154): Output categories removed. Tasks own their outputs."""
    return None


def has_assets_folder(key: str) -> bool:
    """Check if a context domain has an assets/ subfolder (ADR-157)."""
    d = WORKSPACE_DIRECTORIES.get(key)
    return bool(d and d.get("assets_folder"))


def get_assets_path(key: str) -> Optional[str]:
    """Get the workspace-relative path to a domain's assets/ folder.

    Returns e.g. 'context/competitors/assets' or None.
    """
    d = WORKSPACE_DIRECTORIES.get(key)
    if not d or not d.get("assets_folder"):
        return None
    return f"{d['path']}/assets"


def has_entity_tracker(key: str) -> bool:
    """Check if a context domain has an entity tracker (_tracker.md)."""
    d = WORKSPACE_DIRECTORIES.get(key)
    return bool(d and d.get("tracker_file"))


def get_tracker_path(key: str) -> Optional[str]:
    """Get the full workspace-relative path to a domain's _tracker.md."""
    d = WORKSPACE_DIRECTORIES.get(key)
    if not d or not d.get("tracker_file"):
        return None
    return f"{d['path']}/{d['tracker_file']}"


def build_tracker_md(domain_key: str, entities: list[dict]) -> str:
    """Build _tracker.md content from a list of entity dicts.

    ADR-154: Pipeline-maintained materialized view. Never LLM-generated.

    Args:
        domain_key: Domain registry key (e.g., "competitors")
        entities: List of dicts with keys: slug, name, last_updated, files, status

    Returns:
        Formatted markdown string for _tracker.md
    """
    d = WORKSPACE_DIRECTORIES.get(domain_key, {})
    display_name = d.get("display_name", domain_key.title())
    entity_type = d.get("entity_type", "entity")

    lines = [f"# Entity Tracker — {display_name}\n"]

    if entities:
        lines.append("| Slug | Last Updated | Files | Status |")
        lines.append("|------|-------------|-------|--------|")
        for e in entities:
            slug = e.get("slug", "?")
            updated = e.get("last_updated", "—")
            files = ", ".join(e.get("files", [])) if e.get("files") else "—"
            status = e.get("status", "active")
            lines.append(f"| {slug} | {updated} | {files} | {status} |")
    else:
        lines.append(f"_No {entity_type} entities tracked yet._")

    # Domain health summary
    total = len(entities)
    active = sum(1 for e in entities if e.get("status") == "active")
    stale = sum(1 for e in entities if e.get("status") == "stale")
    discovered = sum(1 for e in entities if e.get("status") == "discovered")

    lines.append(f"\n## Domain Health")
    lines.append(f"- Total entities: {total}")
    lines.append(f"- Active: {active}")
    if stale:
        lines.append(f"- Stale: {stale}")
    if discovered:
        lines.append(f"- Discovered (not yet profiled): {discovered}")

    synthesis = d.get("synthesis_file")
    if synthesis:
        lines.append(f"- Synthesis file: {synthesis}")

    return "\n".join(lines) + "\n"


# Keep CONTEXT_DOMAINS as a filtered view for callers that need only context dirs
CONTEXT_DOMAINS = {k: v for k, v in WORKSPACE_DIRECTORIES.items() if v.get("type") == "context"}


async def scaffold_all_directories(client, user_id: str) -> list[str]:
    """Scaffold all workspace directories at onboarding.

    Creates synthesis files for context domains and empty markers for output categories.
    Idempotent — skips already-scaffolded directories.

    Called during user onboarding (alongside agent roster scaffold).
    Returns list of directory keys that were newly scaffolded.
    """
    from services.workspace import UserMemory
    import logging

    logger = logging.getLogger(__name__)
    um = UserMemory(client, user_id)
    scaffolded = []

    for key, directory in WORKSPACE_DIRECTORIES.items():
        dir_type = directory.get("type")
        path = directory["path"]

        if dir_type == "context":
            # Scaffold synthesis file for context domains
            synthesis = directory.get("synthesis_file")
            if synthesis:
                existing = await um.read(f"{path}/{synthesis}")
                if not existing:
                    template = directory.get("synthesis_template") or ""
                    await um.write(f"{path}/{synthesis}", template,
                                  summary=f"Directory scaffold: {key}")

            # ADR-157: Scaffold assets/ folder for domains that support visual assets
            if directory.get("assets_folder"):
                assets_path = f"{path}/assets/.gitkeep"
                existing_assets = await um.read(assets_path)
                if not existing_assets:
                    await um.write(assets_path,
                                  "# Assets\n\nVisual assets for this domain (favicons, charts, diagrams).\n",
                                  summary=f"Assets folder scaffold: {key}")

            # ADR-154: Scaffold _tracker.md for entity-bearing domains
            tracker = directory.get("tracker_file")
            if tracker:
                tracker_path = f"{path}/{tracker}"
                existing_tracker = await um.read(tracker_path)
                if not existing_tracker:
                    tracker_content = build_tracker_md(key, [])
                    await um.write(tracker_path, tracker_content,
                                  summary=f"Entity tracker scaffold: {key}")

            # Signal domains get today's file
            if directory.get("signal_log"):
                from datetime import datetime, timezone
                today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                signal_path = f"{path}/{today}.md"
                existing_signal = await um.read(signal_path)
                if not existing_signal:
                    await um.write(signal_path,
                                  f"# Signals — {today}\n<!-- Cross-domain temporal signal log. -->\n",
                                  summary=f"Signal log scaffold: {today}")

            scaffolded.append(key)

        elif dir_type == "output":
            # No pre-scaffold needed for output directories — created when first output promotes
            pass

        elif dir_type == "user_contributed":
            # No pre-scaffold — user uploads create files
            pass

        logger.info(f"[DIRECTORY_REGISTRY] Scaffolded: {key}")

    return scaffolded
