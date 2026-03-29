"""
Inline Asset Rendering — ADR-148 Phase 2 (Render)

Post-generation, extracts renderable content from agent markdown output:
- Markdown tables with numeric data → chart render via render service
- Mermaid code blocks → diagram render via render service

Renders assets, uploads to storage, inserts rendered URLs back into markdown.
Zero LLM cost. Mechanical extraction and rendering.

The agent writes naturally (tables, mermaid). This module handles rendering.
"""

import logging
import os
import re
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

RENDER_SERVICE_URL = os.environ.get("RENDER_SERVICE_URL", "https://yarnnn-render.onrender.com")
RENDER_SERVICE_SECRET = os.environ.get("RENDER_SERVICE_SECRET", "")


# =============================================================================
# Table Detection + Chart Rendering
# =============================================================================

def _extract_numeric_tables(markdown: str) -> list[dict]:
    """Extract markdown tables that contain numeric data (chart candidates).

    Returns list of {start, end, title, headers, rows, chart_type}.
    """
    tables = []
    # Match markdown tables: | header | header | \n |---|---| \n | cell | cell |
    table_pattern = re.compile(
        r'((?:^.*\n)?)'  # optional preceding line (potential title)
        r'(\|[^\n]+\|\n'  # header row
        r'\|[-:\| ]+\|\n'  # separator row
        r'(?:\|[^\n]+\|\n?)+)',  # data rows
        re.MULTILINE
    )

    for match in table_pattern.finditer(markdown):
        preceding = match.group(1).strip()
        table_text = match.group(2).strip()
        full_match_start = match.start()
        full_match_end = match.end()

        lines = table_text.strip().split("\n")
        if len(lines) < 3:  # header + separator + at least 1 data row
            continue

        # Parse header
        headers = [h.strip() for h in lines[0].strip("|").split("|")]

        # Parse data rows (skip separator)
        rows = []
        for line in lines[2:]:
            cells = [c.strip() for c in line.strip("|").split("|")]
            rows.append(cells)

        # Check if any column has numeric data
        has_numeric = False
        for row in rows:
            for cell in row:
                # Strip formatting characters
                cleaned = re.sub(r'[*_$%,+\s]', '', cell)
                try:
                    float(cleaned)
                    has_numeric = True
                    break
                except (ValueError, TypeError):
                    pass
            if has_numeric:
                break

        if not has_numeric:
            continue

        # Infer chart type
        chart_type = _infer_chart_type(headers, rows)

        # Extract title from preceding line (## Header or **Bold** text)
        title = ""
        if preceding:
            title_match = re.search(r'#+\s+(.+)', preceding)
            if title_match:
                title = title_match.group(1).strip()
            elif preceding.startswith("**") and preceding.endswith("**"):
                title = preceding.strip("*").strip()
            else:
                title = preceding[:80]

        tables.append({
            "start": full_match_start,
            "end": full_match_end,
            "title": title,
            "headers": headers,
            "rows": rows,
            "chart_type": chart_type,
            "raw": table_text,
        })

    return tables


def _infer_chart_type(headers: list[str], rows: list[list[str]]) -> str:
    """Infer the best chart type from table structure."""
    if len(rows) <= 6:
        # Check if values look like percentages or part-of-whole
        for row in rows:
            for cell in row:
                if "%" in cell:
                    return "pie" if len(rows) <= 5 else "bar"

    # Check for time-series indicators in headers
    time_indicators = ["date", "month", "quarter", "year", "week", "q1", "q2", "q3", "q4",
                       "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    for h in headers:
        if any(t in h.lower() for t in time_indicators):
            return "line"

    return "bar"


def _table_to_chart_spec(table: dict) -> dict:
    """Convert parsed table to render service chart spec."""
    headers = table["headers"]
    rows = table["rows"]
    chart_type = table["chart_type"]

    # First column = labels, remaining columns = datasets
    labels = [row[0] for row in rows if len(row) > 0]

    datasets = []
    for col_idx in range(1, len(headers)):
        data = []
        for row in rows:
            if col_idx < len(row):
                # Extract numeric value
                cleaned = re.sub(r'[*_$%,+\s]', '', row[col_idx])
                try:
                    data.append(float(cleaned))
                except (ValueError, TypeError):
                    data.append(0)
            else:
                data.append(0)
        datasets.append({
            "label": headers[col_idx] if col_idx < len(headers) else f"Series {col_idx}",
            "data": data,
        })

    return {
        "chart_type": chart_type,
        "title": table.get("title", ""),
        "labels": labels,
        "datasets": datasets,
    }


# =============================================================================
# Mermaid Block Extraction
# =============================================================================

def _extract_mermaid_blocks(markdown: str) -> list[dict]:
    """Extract ```mermaid code blocks from markdown."""
    blocks = []
    pattern = re.compile(r'```mermaid\s*\n(.*?)\n```', re.DOTALL)

    for match in pattern.finditer(markdown):
        blocks.append({
            "start": match.start(),
            "end": match.end(),
            "diagram": match.group(1).strip(),
        })

    return blocks


# =============================================================================
# Render Service Calls
# =============================================================================

async def _render_chart(chart_spec: dict, user_id: str) -> Optional[str]:
    """Call render service to produce a chart. Returns storage URL or None."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as http:
            headers = {}
            if RENDER_SERVICE_SECRET:
                headers["X-Render-Secret"] = RENDER_SERVICE_SECRET

            resp = await http.post(
                f"{RENDER_SERVICE_URL}/render",
                json={
                    "type": "chart",
                    "input": chart_spec,
                    "output_format": "svg",
                    "user_id": user_id,
                },
                headers=headers,
            )

            if resp.status_code != 200:
                logger.warning(f"[RENDER_ASSETS] Chart render HTTP {resp.status_code}")
                return None

            data = resp.json()
            return data.get("output_url") or data.get("url")

    except Exception as e:
        logger.warning(f"[RENDER_ASSETS] Chart render failed: {e}")
        return None


async def _render_mermaid(diagram: str, user_id: str) -> Optional[str]:
    """Call render service to produce a mermaid diagram. Returns storage URL or None."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as http:
            headers = {}
            if RENDER_SERVICE_SECRET:
                headers["X-Render-Secret"] = RENDER_SERVICE_SECRET

            resp = await http.post(
                f"{RENDER_SERVICE_URL}/render",
                json={
                    "type": "mermaid",
                    "input": {"diagram": diagram},
                    "output_format": "svg",
                    "user_id": user_id,
                },
                headers=headers,
            )

            if resp.status_code != 200:
                logger.warning(f"[RENDER_ASSETS] Mermaid render HTTP {resp.status_code}")
                return None

            data = resp.json()
            return data.get("output_url") or data.get("url")

    except Exception as e:
        logger.warning(f"[RENDER_ASSETS] Mermaid render failed: {e}")
        return None


# =============================================================================
# Main Entry Point
# =============================================================================

async def render_inline_assets(
    markdown: str,
    user_id: str,
) -> tuple[str, list[dict]]:
    """Extract and render inline assets from agent markdown output.

    ADR-148 Phase 2: Post-generation render phase.
    - Extracts markdown tables with numeric data → renders as charts
    - Extracts mermaid code blocks → renders as SVG diagrams
    - Inserts rendered asset URLs back into markdown

    Args:
        markdown: Agent output markdown
        user_id: For scoping storage uploads

    Returns:
        (enriched_markdown, rendered_assets)
        - enriched_markdown: markdown with rendered asset images inserted
        - rendered_assets: list of {type, url, title} for manifest
    """
    rendered_assets = []
    enriched = markdown

    # Track replacements (process in reverse order to preserve positions)
    replacements = []

    # 1. Extract and render mermaid blocks
    mermaid_blocks = _extract_mermaid_blocks(markdown)
    for block in mermaid_blocks:
        url = await _render_mermaid(block["diagram"], user_id)
        if url:
            rendered_assets.append({"type": "diagram", "url": url, "title": "diagram"})
            replacements.append({
                "start": block["start"],
                "end": block["end"],
                "replacement": f'![diagram]({url})',
            })
            logger.info(f"[RENDER_ASSETS] Mermaid diagram rendered: {url}")

    # 2. Extract and render numeric tables as charts
    tables = _extract_numeric_tables(markdown)
    for table in tables:
        chart_spec = _table_to_chart_spec(table)
        url = await _render_chart(chart_spec, user_id)
        if url:
            rendered_assets.append({
                "type": "chart",
                "url": url,
                "title": table.get("title", "chart"),
                "chart_type": table["chart_type"],
            })
            # Insert chart image ABOVE the table (table stays for data reference)
            replacements.append({
                "start": table["start"],
                "end": table["start"],  # insert before, don't replace table
                "replacement": f'![{table.get("title", "chart")}]({url})\n\n',
            })
            logger.info(f"[RENDER_ASSETS] Chart rendered ({table['chart_type']}): {url}")

    # Apply replacements in reverse order (to preserve positions)
    for r in sorted(replacements, key=lambda x: x["start"], reverse=True):
        enriched = enriched[:r["start"]] + r["replacement"] + enriched[r["end"]:]

    if rendered_assets:
        logger.info(f"[RENDER_ASSETS] Rendered {len(rendered_assets)} assets ({len(mermaid_blocks)} diagrams, {len(tables)} charts)")
    else:
        logger.info(f"[RENDER_ASSETS] No renderable assets found (tables: {len(tables)}, mermaid: {len(mermaid_blocks)})")

    return enriched, rendered_assets
