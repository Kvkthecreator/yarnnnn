"""
Context Domain Registry — ADR-151: Shared Context Domains (v1)

Version: 1.0 (2026-03-31)
Changelog:
  v1.0 (2026-03-31) — Initial: 6 domains (competitors, market, relationships,
                       projects, content, signals). ADR-151.

The third registry alongside Agent Types (ADR-140) and Task Types (ADR-145).
Governs the workspace's accumulated context structure at /workspace/context/.

Domains are context categories, not task types. "Competitors" is a domain.
"Competitive intelligence brief" is a task type that reads/writes the competitors domain.

Design principles:
  1. Domains are context categories — what the system accumulates
  2. Domains have entity structure — per-entity subfolders with templated files
  3. Domains have synthesis files — cross-entity summaries (_-prefixed)
  4. Assets are domain-scoped — co-located with the context they represent
  5. Domains grow dynamically — registry is starting set, TP can add more
  6. Signal log is cross-domain — temporal events from any domain

Expansion process:
  1. Add domain dict to CONTEXT_DOMAINS below
  2. Update task types that should read/write the new domain (context_reads/context_writes)
  3. Update docs/architecture/workspace-conventions.md with new domain
  4. Increment version comment above
  5. Add entry to this file's changelog header

Current ICP: solo founder / small team. Domains designed for this persona.
Subject to expansion for enterprise, multi-team, or industry-specific use cases.

Canonical reference: docs/adr/ADR-151-shared-knowledge-domains.md
"""

from __future__ import annotations

from typing import Any, Optional


# =============================================================================
# Context Domain Registry
# =============================================================================

CONTEXT_DOMAINS: dict[str, dict[str, Any]] = {

    # ── Intelligence Domains ──

    "competitors": {
        "display_name": "Competitors",
        "description": "Companies and products we compete with",
        "entity_type": "company",
        "folder": "competitors",
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
        "display_name": "Market",
        "description": "Market segments, sizing, trends, and opportunities",
        "entity_type": "segment",
        "folder": "market",
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

    # ── Relationship Domains ──

    "relationships": {
        "display_name": "Relationships",
        "description": "People and organizations we work with",
        "entity_type": "contact",
        "folder": "relationships",
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

    # ── Operational Domains ──

    "projects": {
        "display_name": "Projects",
        "description": "Internal initiatives, workstreams, and milestones",
        "entity_type": "project",
        "folder": "projects",
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

    # ── Content Domains ──

    "content": {
        "display_name": "Content",
        "description": "Research, drafts, and creative work in progress",
        "entity_type": "topic",
        "folder": "content",
        "entity_structure": {
            "research.md": "# Research — {name}\n\n## Key Points\n\n## Sources\n\n## Audience Considerations\n",
            "outline.md": "# Outline — {name}\n\n## Key Messages\n\n## Structure\n\n## Tone\n",
        },
        "entity_assets": [],
        "synthesis_file": None,
        "synthesis_template": None,
        "shared_assets": [],
    },

    # ── Temporal Domain ──

    "signals": {
        "display_name": "Signals",
        "description": "Temporal signal log — what happened when, across all domains",
        "entity_type": None,  # Not entity-based — date-based
        "folder": "signals",
        "entity_structure": None,
        "synthesis_file": None,
        "synthesis_template": None,
        "signal_log": True,  # Date-stamped files: {YYYY-MM-DD}.md
        "shared_assets": [],
    },
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_domain(domain_key: str) -> Optional[dict[str, Any]]:
    """Look up a context domain by key. Returns None if not found."""
    return CONTEXT_DOMAINS.get(domain_key)


def list_domains() -> list[dict[str, Any]]:
    """List all context domains with their keys."""
    return [{"domain_key": k, **v} for k, v in CONTEXT_DOMAINS.items()]


def get_domain_folder(domain_key: str) -> Optional[str]:
    """Get the workspace folder path for a domain. Returns 'context/{folder}'."""
    domain = CONTEXT_DOMAINS.get(domain_key)
    if not domain:
        return None
    return f"context/{domain['folder']}"


def get_entity_template(domain_key: str, entity_name: str) -> dict[str, str]:
    """Get templated entity files for a domain, with {name} replaced.

    Returns dict of {filename: content} ready to write.
    """
    domain = CONTEXT_DOMAINS.get(domain_key)
    if not domain or not domain.get("entity_structure"):
        return {}
    return {
        filename: template.replace("{name}", entity_name)
        for filename, template in domain["entity_structure"].items()
    }


def get_synthesis_content(domain_key: str) -> Optional[tuple[str, str]]:
    """Get the synthesis file path and template for a domain.

    Returns (filename, template) or None.
    """
    domain = CONTEXT_DOMAINS.get(domain_key)
    if not domain or not domain.get("synthesis_file"):
        return None
    return (domain["synthesis_file"], domain["synthesis_template"] or "")


async def scaffold_all_domains(client, user_id: str) -> list[str]:
    """Scaffold all context domains for a workspace at onboarding.

    Creates /workspace/context/{domain}/ with synthesis files for all domains
    in the registry. Idempotent — skips domains already scaffolded.

    Called during user onboarding (alongside agent roster scaffold).
    Returns list of domain keys that were newly scaffolded.

    Args:
        client: Supabase service client
        user_id: User UUID
    """
    from services.workspace import UserMemory
    import logging

    logger = logging.getLogger(__name__)
    um = UserMemory(client, user_id)
    scaffolded = []

    for domain_key, domain in CONTEXT_DOMAINS.items():
        folder = f"context/{domain['folder']}"

        # Check if already scaffolded
        synthesis = domain.get("synthesis_file")
        if synthesis:
            existing = await um.read(f"{folder}/{synthesis}")
            if existing:
                continue  # Already scaffolded

        # Scaffold synthesis file
        if synthesis and domain.get("synthesis_template"):
            await um.write(
                f"{folder}/{synthesis}",
                domain["synthesis_template"],
                summary=f"Context domain scaffold: {domain_key}",
            )

        # For signals domain, scaffold today's empty file
        if domain.get("signal_log"):
            from datetime import datetime, timezone
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            signal_path = f"{folder}/{today}.md"
            existing_signal = await um.read(signal_path)
            if not existing_signal:
                await um.write(
                    signal_path,
                    f"# Signals — {today}\n<!-- Cross-domain temporal signal log. Any task can append. -->\n",
                    summary=f"Signal log scaffold: {today}",
                )

        scaffolded.append(domain_key)
        logger.info(f"[DOMAIN_REGISTRY] Scaffolded context domain: {domain_key}")

    return scaffolded
