"""
Compose Assembly — ADR-170 Phase 2+3.

Pre-generation: build_generation_brief()
  Reads page_structure from the task type registry, queries the workspace
  filesystem for what actually exists (entities, assets, staleness), and
  produces a structured generation brief for the LLM.

  The brief tells the LLM:
  - Which sections to write (from page_structure)
  - What data exists per section (entities, synthesis files)
  - Which assets are available to reference
  - What is stale vs current since last run (via sys_manifest.json)

  This is where tenure compounds: a workspace with 10 entities and 3 prior
  runs produces a richer brief than a first-run workspace.

Post-generation (Phase 3): parse + folder build
  Parses LLM output into section partials, copies/links assets, composes
  index.html, writes sys_manifest.json.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Pre-generation: Generation Brief
# =============================================================================

async def build_generation_brief(
    client,
    user_id: str,
    task_slug: str,
    task_info: dict,
    prior_manifest=None,  # SysManifest | None
) -> str:
    """Build the generation brief for a produces_deliverable task.

    ADR-170 RD-2: The generation brief is the compose function's primary output.
    It structures what the LLM will write — which sections, what data, what assets.

    Args:
        client: Supabase client
        user_id: User ID
        task_slug: Task slug
        task_info: Parsed TASK.md dict (from parse_task_md)
        prior_manifest: SysManifest from previous run, or None for first run

    Returns:
        Generation brief string to inject into the user message before generation.
        Empty string if task has no page_structure (graceful fallback).
    """
    from services.task_types import get_task_type

    type_key = task_info.get("type_key", "")
    task_type_def = get_task_type(type_key) if type_key else None
    if not task_type_def:
        return ""

    page_structure = task_type_def.get("page_structure")
    if not page_structure:
        return ""  # No structure declared → LLM organizes freely (context tasks, etc.)

    surface_type = task_info.get("surface_type") or task_type_def.get("surface_type", "report")
    context_reads = task_info.get("context_reads", [])

    # Query filesystem state for each domain in context_reads
    domain_state = await _query_domain_state(client, user_id, context_reads)

    # Build section briefs
    section_briefs = []
    for section_def in page_structure:
        brief = await _build_section_brief(
            client, user_id, section_def, domain_state, prior_manifest
        )
        if brief:
            section_briefs.append(brief)

    if not section_briefs:
        return ""

    # Build asset inventory — what root assets exist across all context domains
    asset_inventory = _build_asset_inventory(domain_state)

    # Compose the full brief
    lines = [
        f"## Output Structure ({surface_type})",
        "",
        "Your output MUST follow this section structure exactly. Each section is typed — ",
        "produce content that matches the section kind's data contract.",
        "",
    ]

    # Staleness summary if we have a prior run
    if prior_manifest:
        stale_sections = [
            s["title"] for s in page_structure
            if prior_manifest.is_section_stale(_slug(s["title"]))
        ]
        if stale_sections:
            lines += [
                f"**Changed since last run:** {', '.join(stale_sections)} — focus revision here.",
                "",
            ]
        else:
            lines += [
                "**No domain changes detected since last run.** Emphasize continuity — ",
                "note what remains stable, update with any new signals.",
                "",
            ]

    # Section-by-section brief
    for brief in section_briefs:
        lines.append(brief)
        lines.append("")

    # Asset inventory
    if asset_inventory:
        lines += [
            "## Available Assets",
            "These visual assets exist in the workspace. Reference them by embedding their content_url:",
            "",
        ]
        lines += asset_inventory

    # Surface-type formatting guidance
    surface_guidance = _surface_formatting_guidance(surface_type)
    if surface_guidance:
        lines += ["", "## Surface Formatting", surface_guidance]

    return "\n".join(lines)


async def _query_domain_state(
    client,
    user_id: str,
    context_reads: list[str],
) -> dict:
    """Query workspace_files to understand current domain state.

    Returns a dict keyed by domain with:
    - entities: list of {slug, primary_file_path, updated_at}
    - synthesis_files: list of {path, updated_at}
    - assets: list of {filename, path, content_url, updated_at}
    - latest_updated_at: most recent update in domain
    """
    from services.directory_registry import (
        get_domain_folder, get_synthesis_content, WORKSPACE_DIRECTORIES,
    )

    state = {}

    for domain_key in context_reads:
        folder = get_domain_folder(domain_key)
        if not folder:
            state[domain_key] = _empty_domain_state()
            continue

        prefix = f"/workspace/{folder}"
        domain_def = WORKSPACE_DIRECTORIES.get(domain_key, {})

        try:
            # Fetch all files in this domain
            result = (
                client.table("workspace_files")
                .select("path, content_url, updated_at")
                .eq("user_id", user_id)
                .like("path", f"{prefix}/%")
                .order("updated_at", desc=True)
                .limit(100)
                .execute()
            )
            rows = result.data or []
        except Exception as e:
            logger.debug(f"[COMPOSE] Domain query failed for {domain_key}: {e}")
            state[domain_key] = _empty_domain_state()
            continue

        synthesis_info = get_synthesis_content(domain_key)
        synthesis_filename = synthesis_info[0] if synthesis_info else None

        synthesis_files = []
        asset_files = []
        entity_slugs = set()
        entity_files = []

        for row in rows:
            path = row.get("path", "")
            rel = path[len(prefix):].lstrip("/")  # relative to domain folder

            # Synthesis files (e.g. _synthesis.md, _tracker.md, _landscape.md)
            if synthesis_filename and rel == synthesis_filename:
                synthesis_files.append({
                    "path": path,
                    "updated_at": row.get("updated_at", ""),
                })
                continue

            # Assets subfolder
            if rel.startswith("assets/"):
                asset_files.append({
                    "filename": rel[len("assets/"):],
                    "path": path,
                    "content_url": row.get("content_url"),
                    "updated_at": row.get("updated_at", ""),
                })
                continue

            # Entity files: {entity-slug}/{filename}.md
            parts = rel.split("/")
            if len(parts) == 2 and parts[1].endswith(".md"):
                entity_slug = parts[0]
                entity_slugs.add(entity_slug)
                entity_files.append({
                    "slug": entity_slug,
                    "file": parts[1],
                    "path": path,
                    "updated_at": row.get("updated_at", ""),
                })

        # Determine latest updated_at across all domain files
        all_updated = [r.get("updated_at", "") for r in rows if r.get("updated_at")]
        latest_updated = max(all_updated) if all_updated else ""

        state[domain_key] = {
            "entities": list(entity_slugs),
            "entity_files": entity_files,
            "synthesis_files": synthesis_files,
            "assets": asset_files,
            "latest_updated_at": latest_updated,
        }

    return state


def _empty_domain_state() -> dict:
    return {
        "entities": [],
        "entity_files": [],
        "synthesis_files": [],
        "assets": [],
        "latest_updated_at": "",
    }


async def _build_section_brief(
    client,
    user_id: str,
    section_def: dict,
    domain_state: dict,
    prior_manifest,
) -> str:
    """Build a brief for one section from page_structure."""
    kind = section_def.get("kind", "narrative")
    title = section_def.get("title", "Section")
    reads_from = section_def.get("reads_from", [])
    entity_pattern = section_def.get("entity_pattern")
    section_assets = section_def.get("assets", [])

    lines = [f"### {title} (`{kind}`)"]

    # What data this section should draw from
    data_lines = _resolve_reads_from(reads_from, domain_state)
    if data_lines:
        lines.append("**Data sources:**")
        lines += data_lines

    # Entity-grid: list available entities
    if kind == "entity-grid" and entity_pattern:
        domain_key = _domain_from_pattern(entity_pattern)
        if domain_key and domain_key in domain_state:
            entities = domain_state[domain_key].get("entities", [])
            if entities:
                lines.append(f"**{len(entities)} entities available:** {', '.join(sorted(entities))}")
                lines.append(
                    "Produce one card per entity. Card format: name + one-line description + "
                    "key fact + status badge (if applicable)."
                )
            else:
                lines.append("**No entities yet.** Note this domain is being bootstrapped.")

    # Asset guidance
    root_assets = [a for a in section_assets if a.get("type") == "root"]
    derivative_assets = [a for a in section_assets if a.get("type") == "derivative"]

    if root_assets:
        for asset_spec in root_assets:
            pattern = asset_spec.get("pattern", "")
            domain_key = _domain_from_path(pattern)
            if domain_key and domain_key in domain_state:
                available = [
                    a for a in domain_state[domain_key].get("assets", [])
                    if _matches_glob(a["filename"], pattern.split("/")[-1])
                ]
                if available:
                    lines.append(
                        f"**Root assets available ({len(available)}):** "
                        + ", ".join(a["filename"] for a in available[:5])
                        + ". Embed using their content_url."
                    )

    if derivative_assets:
        for asset_spec in derivative_assets:
            render = asset_spec.get("render", "chart")
            lines.append(
                f"**Include a {render} asset:** Produce structured data "
                f"(markdown table or ```mermaid block) — it will be auto-rendered."
            )

    # Staleness signal
    if prior_manifest:
        section_key = _slug(title)
        if prior_manifest.is_section_stale(section_key):
            lines.append("**⟳ Stale** — source data changed since last run. Regenerate fully.")
        else:
            lines.append("**✓ Current** — minimal changes needed. Update only new signals.")

    # Kind-specific output contract
    contract = _kind_output_contract(kind)
    if contract:
        lines.append(f"**Output contract:** {contract}")

    return "\n".join(lines)


def _resolve_reads_from(reads_from: list[str], domain_state: dict) -> list[str]:
    """Map reads_from paths to what actually exists in the filesystem."""
    lines = []
    for path_pattern in reads_from:
        domain_key = _domain_from_path(path_pattern)
        if not domain_key or domain_key not in domain_state:
            lines.append(f"- `{path_pattern}`")
            continue

        dstate = domain_state[domain_key]

        # Synthesis file reference
        synth = dstate.get("synthesis_files", [])
        if synth and "_synthesis" in path_pattern or "_tracker" in path_pattern:
            updated = synth[0].get("updated_at", "")[:10] if synth else ""
            freshness = f" (updated {updated})" if updated else ""
            lines.append(f"- `{path_pattern}`{freshness} — {len(synth)} file(s)")
        else:
            # Entity or signal files
            entity_files = dstate.get("entity_files", [])
            matching = [
                f for f in entity_files
                if _path_matches_pattern(f["path"], path_pattern)
            ]
            if matching:
                slugs = sorted(set(f["slug"] for f in matching))
                lines.append(f"- `{path_pattern}` — {', '.join(slugs[:5])}" +
                              (f" +{len(slugs)-5} more" if len(slugs) > 5 else ""))
            else:
                lines.append(f"- `{path_pattern}` (no files yet)")

    return lines


def _build_asset_inventory(domain_state: dict) -> list[str]:
    """List all root assets available across all context domains."""
    lines = []
    for domain_key, dstate in domain_state.items():
        assets = dstate.get("assets", [])
        if not assets:
            continue
        for asset in assets[:10]:  # cap at 10 per domain
            filename = asset.get("filename", "")
            url = asset.get("content_url", "")
            if url:
                lines.append(f"- `{filename}`: `{url}`")
    return lines


def _surface_formatting_guidance(surface_type: str) -> str:
    """Brief LLM-facing guidance on formatting for this surface type."""
    guidance = {
        "report": (
            "Write for sequential reading. Use ## headers for section titles. "
            "Narrative prose with supporting data. Charts and tables inline between paragraphs."
        ),
        "deck": (
            "Write for presentation. Each ## section becomes a full-screen slide. "
            "One core idea per section — no more than 3 bullet points. "
            "Lead with the headline, support with 2-3 data points."
        ),
        "dashboard": (
            "Write for at-a-glance scanning. Lead each section with the key number or status. "
            "Use metric-card format: **Metric Name:** value | delta. "
            "Avoid long prose — every sentence should be scannable in 5 seconds."
        ),
        "digest": (
            "Write for quick triage. Bullet points only — no paragraphs. "
            "Lead with what's new, skip what hasn't changed. "
            "Keep the full output under 600 words."
        ),
        "workbook": (
            "Data-first. Lead each section with a table. "
            "Narrative explains the table — not the other way around. "
            "Include column headers and units."
        ),
    }
    return guidance.get(surface_type, "")


# =============================================================================
# Kind output contracts — what each section kind expects from the LLM
# =============================================================================

def _kind_output_contract(kind: str) -> str:
    contracts = {
        "narrative": "Flowing prose paragraphs. 150–400 words. Optional pull quote.",
        "metric-cards": (
            "2–4 KPI items. Format each as: `**Label:** value (delta)`. "
            "Include units. Delta as +/-% or +/-N."
        ),
        "entity-grid": (
            "One entry per entity. Format: `### Entity Name\\n"
            "One-line description. Key fact. Status badge.`"
        ),
        "comparison-table": (
            "Markdown table. Entities as columns, attributes as rows. "
            "Use ✓/✗ or RAG (🟢/🟡/🔴) for status cells."
        ),
        "trend-chart": (
            "Markdown table with time-series data (date column + metric column). "
            "Platform will render as line chart."
        ),
        "distribution-chart": (
            "Markdown table with categories + values. "
            "Platform will render as bar or pie chart."
        ),
        "timeline": (
            "Chronological list. Format each: `**YYYY-MM-DD** — Description (source).`"
        ),
        "status-matrix": (
            "Markdown table. Entities as rows, criteria as columns. "
            "Status: 🟢 healthy / 🟡 at risk / 🔴 blocked / – unknown."
        ),
        "data-table": "Markdown table with headers and typed columns. Include units.",
        "callout": (
            "Single insight, warning, or recommendation. "
            "Format: `> **[Insight/Warning/Recommendation]:** Body text (source).`"
        ),
        "checklist": (
            "Action items or criteria. Format: `- [ ] Item text (owner, due date if known).`"
        ),
    }
    return contracts.get(kind, "")


# =============================================================================
# Helpers
# =============================================================================

def _slug(title: str) -> str:
    """Convert section title to a slug key for manifest lookups."""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def _domain_from_path(path: str) -> Optional[str]:
    """Extract domain key from a path pattern like 'competitors/_synthesis.md'."""
    if not path:
        return None
    parts = path.split("/")
    # e.g. "competitors/_synthesis.md" → "competitors"
    # e.g. "competitors/*/" → "competitors"
    return parts[0] if parts else None


def _domain_from_pattern(pattern: str) -> Optional[str]:
    """Extract domain from entity_pattern like 'competitors/*/'."""
    return _domain_from_path(pattern)


def _path_matches_pattern(path: str, pattern: str) -> bool:
    """Simple glob matching for path patterns."""
    # Normalize: strip leading /workspace/context/ prefix from path for matching
    # Pattern is relative to domain: "competitors/*/analysis.md"
    domain = _domain_from_path(pattern)
    if not domain:
        return False
    # Check domain appears in path
    if f"/context/{domain}/" not in path and f"/{domain}/" not in path:
        return False
    # Check file suffix if pattern ends with a filename
    if not pattern.endswith("*/") and not pattern.endswith("*"):
        suffix = pattern.split("/")[-1]
        if suffix and not path.endswith(suffix):
            return False
    return True


def _matches_glob(filename: str, pattern: str) -> bool:
    """Match a filename against a simple glob pattern like '*-favicon.png'."""
    if not pattern or pattern == "*":
        return True
    if pattern.startswith("*"):
        return filename.endswith(pattern[1:])
    if pattern.endswith("*"):
        return filename.startswith(pattern[:-1])
    return filename == pattern


# =============================================================================
# Post-generation: Parse draft into section partials (Phase 3)
# =============================================================================

def parse_draft_into_sections(
    draft: str,
    page_structure: list[dict],
) -> dict[str, dict]:
    """Parse LLM draft output into per-section content partials.

    Splits on ## headers that match declared page_structure section titles.
    Returns a dict keyed by section slug with:
      - kind: section kind from page_structure
      - title: section title
      - content: section markdown content (header included)
      - char_count: content length signal

    Unmatched sections (LLM added extras) are included under their own slug.
    Declared sections with no matching content get an empty string.

    ADR-170 RD-3: section partials are the atomic units of revision routing.
    """
    if not page_structure:
        return {}

    # Build title → kind map from page_structure (case-insensitive match)
    declared = {
        s["title"].lower().strip(): {
            "kind": s.get("kind", "narrative"),
            "title": s["title"],
            "reads_from": s.get("reads_from", []),
        }
        for s in page_structure
    }

    # Split draft on ## headers (top-level sections only — ### stays inside)
    # Pattern: line starting with exactly ## (not ###)
    section_pattern = re.compile(r'^(##\s+.+)$', re.MULTILINE)
    splits = section_pattern.split(draft)

    # splits alternates: [preamble, header, content, header, content, ...]
    sections_out: dict[str, dict] = {}

    # Any content before the first ## header (preamble) — attach to first section or discard
    preamble = splits[0].strip() if splits else ""

    i = 1
    while i + 1 < len(splits):
        header_line = splits[i].strip()   # e.g. "## Executive Summary"
        content = splits[i + 1]
        i += 2

        # Extract title from header (strip ## prefix)
        raw_title = re.sub(r'^##\s+', '', header_line).strip()
        # Strip any markdown formatting from title (bold, backtick)
        clean_title = re.sub(r'[*`_]', '', raw_title).strip()
        slug = _slug(clean_title)

        # Match against declared sections
        matched = declared.get(clean_title.lower())
        kind = matched["kind"] if matched else "narrative"
        canonical_title = matched["title"] if matched else raw_title

        full_content = f"{header_line}\n{content}".rstrip()

        sections_out[slug] = {
            "kind": kind,
            "title": canonical_title,
            "content": full_content,
            "char_count": len(full_content),
        }

    # Ensure all declared sections appear in output (even if LLM missed them)
    for title, decl in declared.items():
        slug = _slug(decl["title"])
        if slug not in sections_out:
            sections_out[slug] = {
                "kind": decl["kind"],
                "title": decl["title"],
                "content": "",
                "char_count": 0,
            }

    return sections_out


def build_post_generation_manifest(
    task_slug: str,
    surface_type: str,
    sections_parsed: dict[str, dict],
    domain_state: dict,
    task_info: dict,
    run_started_at: Optional[str] = None,
) -> "SysManifest":
    """Build a SysManifest from the post-generation parsed sections.

    Called immediately after parse_draft_into_sections() to record provenance.
    The manifest is written to outputs/{date}/sys_manifest.json.

    Args:
        task_slug: Task slug
        surface_type: Surface type (report | deck | dashboard | digest | workbook)
        sections_parsed: Output of parse_draft_into_sections()
        domain_state: Output of _query_domain_state() (same as brief build)
        task_info: Parsed TASK.md dict
        run_started_at: ISO timestamp of run start (defaults to now)

    Returns:
        SysManifest ready to serialize to JSON.
    """
    from services.compose.manifest import SysManifest, SectionProvenance, make_manifest

    now = run_started_at or datetime.now(timezone.utc).isoformat()

    # Build section provenance
    sections: dict = {}
    page_structure = task_info.get("page_structure") or []
    structure_map = {
        _slug(s["title"]): s for s in page_structure
    }

    for slug, sec in sections_parsed.items():
        struct = structure_map.get(slug, {})
        reads_from = struct.get("reads_from", [])

        # Collect source file paths that this section reads from
        source_files = []
        source_updated_ats = []
        for path_pattern in reads_from:
            domain_key = _domain_from_path(path_pattern)
            if domain_key and domain_key in domain_state:
                dstate = domain_state[domain_key]
                # Synthesis files
                for sf in dstate.get("synthesis_files", []):
                    if sf["path"] not in source_files:
                        source_files.append(sf["path"])
                        if sf.get("updated_at"):
                            source_updated_ats.append(sf["updated_at"])
                # Entity files matching pattern
                for ef in dstate.get("entity_files", []):
                    if _path_matches_pattern(ef["path"], path_pattern):
                        if ef["path"] not in source_files:
                            source_files.append(ef["path"])
                            if ef.get("updated_at"):
                                source_updated_ats.append(ef["updated_at"])

        source_updated_at = max(source_updated_ats) if source_updated_ats else None

        sections[slug] = SectionProvenance(
            kind=sec["kind"],
            produced_at=now,
            source_files=source_files[:20],  # cap
            source_updated_at=source_updated_at,
        )

    # Build asset records for root assets seen in domain state
    assets: dict = {}
    for domain_key, dstate in domain_state.items():
        for asset in dstate.get("assets", []):
            filename = asset.get("filename", "")
            if filename and asset.get("content_url"):
                from services.compose.manifest import AssetRecord
                assets[filename] = AssetRecord(
                    kind="root",
                    source_path=asset.get("path"),
                    content_url=asset.get("content_url"),
                    fetched_at=asset.get("updated_at"),
                )

    # Domain freshness
    domain_freshness = {
        domain: dstate.get("latest_updated_at", "")
        for domain, dstate in domain_state.items()
        if dstate.get("latest_updated_at")
    }

    # Entity count: total unique entities across all domains
    entity_count = sum(
        len(dstate.get("entities", []))
        for dstate in domain_state.values()
    )

    return make_manifest(
        task_slug=task_slug,
        surface_type=surface_type,
        sections=sections,
        assets=assets,
        entity_count=entity_count,
        domain_freshness=domain_freshness,
    )
