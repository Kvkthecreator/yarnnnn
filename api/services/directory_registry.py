"""
Workspace Directory Registry — ADR-152: Unified Directory Registry (v1)

Version: 1.0 (2026-03-31)
Changelog:
  v1.0 (2026-03-31) — Initial: unified registry absorbing CONTEXT_DOMAINS from ADR-151.
                       Three directory types: user_contributed (uploads), context (6 domains),
                       output (reports, briefs). Replaces domain_registry.py.

Single source of truth for ALL workspace content directories. Governs:
  /workspace/uploads/    — user-contributed reference material
  /workspace/context/    — agent-accumulated intelligence substrate (6 domains)
  /workspace/outputs/    — agent-produced synthesized deliverables

Three directory types:
  user_contributed — user uploads, permanent, not agent-managed
  context          — agent-accumulated, entity-structured, grows with execution
  output           — agent-produced, deliverable documents promoted from tasks

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
        "entity_assets": ["logo.png"],
        "synthesis_file": "_landscape.md",
        "synthesis_template": (
            "# Competitive Landscape\n\n"
            "## Market Map\n\n"
            "## Key Trends\n\n"
            "## Our Position\n"
        ),
        "shared_assets": ["competitor-matrix.svg"],
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
        "entity_assets": [],
        "synthesis_file": "_overview.md",
        "synthesis_template": (
            "# Market Overview\n\n"
            "## Landscape Summary\n\n"
            "## Cross-Segment Patterns\n\n"
            "## Strategic Implications\n"
        ),
        "shared_assets": ["market-map.svg"],
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
        "entity_assets": [],
        "synthesis_file": "_portfolio.md",
        "synthesis_template": (
            "# Relationship Portfolio\n\n"
            "## Health Overview\n\n"
            "## At-Risk\n\n"
            "## Follow-Up Priorities\n"
        ),
        "shared_assets": [],
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
        "entity_assets": ["roadmap.svg"],
        "synthesis_file": "_status.md",
        "synthesis_template": (
            "# Project Portfolio Status\n\n"
            "## Overall Health\n\n"
            "## Active Blockers\n\n"
            "## Resource Needs\n"
        ),
        "shared_assets": ["project-roadmap.svg"],
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
        "entity_assets": [],
        "synthesis_file": None,
        "synthesis_template": None,
        "shared_assets": [],
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
        "shared_assets": [],
    },

    # ── Output Categories (agent-produced deliverables) ──

    "reports": {
        "type": "output",
        "path": "outputs/reports",
        "display_name": "Reports",
        "description": "Recurring reports, stakeholder updates, status summaries",
        "managed_by": "agent",
        "naming_convention": "{task_slug}-{date}.md",
        "index_file": "_index.md",
        "index_template": (
            "# Reports\n\n"
            "<!-- Auto-updated. Most recent first. -->\n"
        ),
    },

    "briefs": {
        "type": "output",
        "path": "outputs/briefs",
        "display_name": "Briefs",
        "description": "Meeting prep, intel briefs, on-demand summaries",
        "managed_by": "agent",
        "naming_convention": "{task_slug}-{date}.md",
        "index_file": "_index.md",
        "index_template": (
            "# Briefs\n\n"
            "<!-- Auto-updated. Most recent first. -->\n"
        ),
    },

    "content_output": {
        "type": "output",
        "path": "outputs/content",
        "display_name": "Content",
        "description": "Blog posts, launch materials, creative deliverables",
        "managed_by": "agent",
        "naming_convention": "{task_slug}-{date}.md",
        "index_file": "_index.md",
        "index_template": (
            "# Content\n\n"
            "<!-- Auto-updated. Most recent first. -->\n"
        ),
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


def get_entity_template(key: str, entity_name: str) -> dict[str, str]:
    """Get templated entity files for a context directory, with {name} replaced."""
    d = WORKSPACE_DIRECTORIES.get(key)
    if not d or not d.get("entity_structure"):
        return {}
    return {
        filename: template.replace("{name}", entity_name)
        for filename, template in d["entity_structure"].items()
    }


def get_synthesis_content(key: str) -> Optional[tuple[str, str]]:
    """Get the synthesis file path and template for a context directory."""
    d = WORKSPACE_DIRECTORIES.get(key)
    if not d or not d.get("synthesis_file"):
        return None
    return (d["synthesis_file"], d.get("synthesis_template") or "")


def get_output_category_path(category: str) -> Optional[str]:
    """Get the workspace-relative path for an output category."""
    d = WORKSPACE_DIRECTORIES.get(category)
    if d and d.get("type") == "output":
        return d["path"]
    return None


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
                if existing:
                    continue
                template = directory.get("synthesis_template") or ""
                await um.write(f"{path}/{synthesis}", template,
                              summary=f"Directory scaffold: {key}")

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
