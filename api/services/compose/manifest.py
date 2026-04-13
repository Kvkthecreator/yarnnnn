"""
sys_manifest.json — ADR-170 compose substrate.

Provenance record written to every output folder. Enables:
- Revision-as-composition: which sections are stale since last run?
- Asset tracking: root (durable) vs derivative (generated), status per asset
- Cross-run continuity: what existed before, what changed

Schema:

{
  "run_id": "2026-04-10T09:30:00Z",
  "task_slug": "competitive-brief",
  "surface_type": "report",
  "sections": {
    "executive-summary": {
      "kind": "narrative",
      "produced_at": "2026-04-10T09:30:00Z",
      "source_files": ["/workspace/context/competitors/_synthesis.md"],
      "source_updated_at": "2026-04-09T18:00:00Z"
    },
    "competitor-profiles": {
      "kind": "entity-grid",
      "produced_at": "2026-04-10T09:30:00Z",
      "source_files": [
        "/workspace/context/competitors/openai/profile.md",
        "/workspace/context/competitors/anthropic/profile.md"
      ],
      "source_updated_at": "2026-04-10T08:00:00Z"
    }
  },
  "assets": {
    "openai-favicon.png": {
      "kind": "root",
      "source_path": "/workspace/context/competitors/assets/openai-favicon.png",
      "content_url": "https://...",
      "fetched_at": "2026-04-08T12:00:00Z"
    },
    "market-pos.svg": {
      "kind": "derivative",
      "render_skill": "chart",
      "produced_at": "2026-04-10T09:30:00Z",
      "source_files": ["/workspace/context/competitors/*/analysis.md"]
    }
  },
  "entity_count": 3,
  "domain_freshness": {
    "competitors": "2026-04-10T08:00:00Z",
    "signals": "2026-04-09T22:00:00Z"
  },
  "generation_gaps": {
    "competitor-profiles": "skipped:section-current",
    "hero_image": "skipped:asset-exists",
    "signal-timeline": "missing:no-source-data"
  }
}

generation_gaps — forward-looking handoff note to the next run (ADR-173 Phase 3).
Keys: section slugs from page_structure, plus special keys (hero_image, derivative_charts).
Values: "<status>:<reason>" strings.

Status codes:
  produced    — generated this run
  skipped     — existed and was current; not regenerated
  missing     — DELIVERABLE.md or page_structure declared it; agent did not produce it
  partial     — section exists but flagged as incomplete by agent reflection

Reason codes:
  section-current     — source files unchanged since last run
  asset-exists        — asset already present in outputs/latest/
  no-source-data      — no source files found in context_reads domains
  first-run           — no prior manifest existed
  forced              — steering.md required regeneration
  feedback            — user feedback or TP evaluation triggered update
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


@dataclass
class SectionProvenance:
    kind: str                          # section kind (narrative, entity-grid, etc.)
    produced_at: str                   # ISO timestamp of when this section was generated
    source_files: list[str]            # workspace_files paths this section read from
    source_updated_at: Optional[str]   # most recent updated_at among source files


@dataclass
class AssetRecord:
    kind: str                          # "root" | "derivative"
    # Root assets
    source_path: Optional[str] = None  # workspace_files path (root assets)
    content_url: Optional[str] = None  # public URL (root assets)
    fetched_at: Optional[str] = None   # when fetched (root assets)
    # Derivative assets
    render_skill: Optional[str] = None # skill used to generate (derivative)
    produced_at: Optional[str] = None  # when generated (derivative)
    source_files: list[str] = field(default_factory=list)  # source data files


@dataclass
class SysManifest:
    run_id: str                        # ISO timestamp of this run
    task_slug: str
    surface_type: str
    sections: dict[str, SectionProvenance] = field(default_factory=dict)
    assets: dict[str, AssetRecord] = field(default_factory=dict)
    entity_count: int = 0
    domain_freshness: dict[str, str] = field(default_factory=dict)  # domain → latest updated_at
    # ADR-173 Phase 3: forward-looking handoff to next run.
    # Maps section slugs / asset keys → "<status>:<reason>" strings.
    # e.g. {"hero_image": "skipped:asset-exists", "competitor-profiles": "produced"}
    generation_gaps: dict[str, str] = field(default_factory=dict)

    def to_json(self) -> str:
        def _serialize(obj):
            if isinstance(obj, (SectionProvenance, AssetRecord, SysManifest)):
                return asdict(obj)
            raise TypeError(f"Not serializable: {type(obj)}")
        return json.dumps(asdict(self), indent=2, default=str)

    def is_section_stale(self, section_key: str) -> bool:
        """A section is stale if its source files were updated after it was produced.

        If source_updated_at is None (section reads from entity_pattern with no explicit
        reads_from, or source files weren't resolved), defer to domain-level freshness
        check in classify_revision_scope — do not assume stale.
        """
        section = self.sections.get(section_key)
        if not section or not section.produced_at:
            return True  # no provenance at all → assume stale
        if not section.source_updated_at:
            return False  # no source file timestamps — defer to domain freshness check
        return section.source_updated_at > section.produced_at


def read_manifest(content: str) -> Optional[SysManifest]:
    """Parse a sys_manifest.json string into a SysManifest object.

    Returns None if parsing fails — callers treat missing manifest as first run.
    """
    if not content:
        return None
    try:
        data = json.loads(content)
        sections = {}
        for key, sec in data.get("sections", {}).items():
            sections[key] = SectionProvenance(
                kind=sec.get("kind", "narrative"),
                produced_at=sec.get("produced_at", ""),
                source_files=sec.get("source_files", []),
                source_updated_at=sec.get("source_updated_at"),
            )
        assets = {}
        for name, asset in data.get("assets", {}).items():
            assets[name] = AssetRecord(
                kind=asset.get("kind", "derivative"),
                source_path=asset.get("source_path"),
                content_url=asset.get("content_url"),
                fetched_at=asset.get("fetched_at"),
                render_skill=asset.get("render_skill"),
                produced_at=asset.get("produced_at"),
                source_files=asset.get("source_files", []),
            )
        return SysManifest(
            run_id=data.get("run_id", ""),
            task_slug=data.get("task_slug", ""),
            surface_type=data.get("surface_type", "report"),
            sections=sections,
            assets=assets,
            entity_count=data.get("entity_count", 0),
            domain_freshness=data.get("domain_freshness", {}),
            generation_gaps=data.get("generation_gaps", {}),
        )
    except Exception:
        return None


def make_manifest(
    task_slug: str,
    surface_type: str,
    sections: dict[str, SectionProvenance],
    assets: dict[str, AssetRecord],
    entity_count: int,
    domain_freshness: dict[str, str],
    generation_gaps: Optional[dict[str, str]] = None,
) -> SysManifest:
    """Build a new SysManifest for this run.

    generation_gaps (ADR-173 Phase 3): forward-looking handoff dict.
    Maps section/asset keys → "<status>:<reason>" for the next run to read.
    """
    return SysManifest(
        run_id=datetime.now(timezone.utc).isoformat(),
        task_slug=task_slug,
        surface_type=surface_type,
        sections=sections,
        assets=assets,
        entity_count=entity_count,
        domain_freshness=domain_freshness,
        generation_gaps=generation_gaps or {},
    )
