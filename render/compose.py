"""
HTML Composition Engine — ADR-130 Phase 1.

Converts structured markdown + asset references into styled, self-contained HTML.
Three layout modes: document (default), presentation, dashboard.
Brand CSS injection for custom styling.

This is the primary output rendering path for YARNNN agents.
All agent output flows through this engine; legacy format exports (PDF, XLSX)
are mechanical downstream conversions from this HTML.
"""

from __future__ import annotations

import re
from pydantic import BaseModel
from typing import Optional

import markdown


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ComposeRequest(BaseModel):
    markdown: str
    title: str = "Output"
    layout_mode: str = "document"  # document | presentation | dashboard | data
    assets: list[dict] = []  # [{ref: "chart.svg", url: "https://..."}]
    brand_css: Optional[str] = None
    user_id: Optional[str] = None


class ComposeResponse(BaseModel):
    success: bool
    html: Optional[str] = None
    output_url: Optional[str] = None
    content_type: str = "text/html"
    size_bytes: Optional[int] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# CSS constants
# ---------------------------------------------------------------------------

BASE_CSS = """
:root {
  --brand-primary: #1a56db;
  --brand-primary-light: #e1effe;
  --brand-font: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
  --brand-bg: #ffffff;
  --text-primary: #111827;
  --text-secondary: #4b5563;
  --text-muted: #9ca3af;
  --border: #e5e7eb;
  --border-light: #f3f4f6;
  --surface: #f9fafb;
  --radius: 8px;
  color-scheme: light dark;
}

@media (prefers-color-scheme: dark) {
  :root {
    --brand-bg: #0a0a0a;
    --text-primary: #e5e7eb;
    --text-secondary: #9ca3af;
    --text-muted: #6b7280;
    --border: #27272a;
    --border-light: #18181b;
    --surface: #18181b;
    --brand-primary: #60a5fa;
    --brand-primary-light: #1e3a5f;
  }
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: var(--brand-font);
  color: var(--text-primary);
  background: var(--brand-bg);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

h1, h2, h3, h4, h5, h6 { line-height: 1.3; font-weight: 600; }
h1 { font-size: 2rem; margin-bottom: 1rem; }
h2 { font-size: 1.5rem; margin-top: 2rem; margin-bottom: 0.75rem; color: var(--text-primary); }
h3 { font-size: 1.25rem; margin-top: 1.5rem; margin-bottom: 0.5rem; }
h4 { font-size: 1.1rem; margin-top: 1.25rem; margin-bottom: 0.5rem; color: var(--text-secondary); }

p { margin-bottom: 1rem; }

a { color: var(--brand-primary); text-decoration: none; }
a:hover { text-decoration: underline; }

strong { font-weight: 600; }

ul, ol { margin-bottom: 1rem; padding-left: 1.5rem; }
li { margin-bottom: 0.25rem; }

table {
  width: 100%;
  border-collapse: collapse;
  margin: 1.5rem 0;
  font-size: 0.925rem;
}
th, td {
  padding: 0.625rem 0.875rem;
  text-align: left;
  border-bottom: 1px solid var(--border);
}
th {
  font-weight: 600;
  color: var(--text-secondary);
  background: var(--surface);
  border-bottom: 2px solid var(--border);
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}
tr:hover { background: var(--border-light); }

code {
  background: var(--surface);
  padding: 0.125rem 0.375rem;
  border-radius: 4px;
  font-size: 0.875em;
  font-family: 'SF Mono', 'Fira Code', monospace;
}

pre {
  background: var(--surface);
  padding: 1rem;
  border-radius: var(--radius);
  overflow-x: auto;
  margin: 1rem 0;
  border: 1px solid var(--border);
}
pre code { background: none; padding: 0; }

blockquote {
  border-left: 3px solid var(--brand-primary);
  margin: 1.5rem 0;
  padding: 0.75rem 1.25rem;
  color: var(--text-secondary);
  background: var(--brand-primary-light);
  border-radius: 0 var(--radius) var(--radius) 0;
}

hr {
  border: none;
  border-top: 1px solid var(--border);
  margin: 2rem 0;
}

img {
  max-width: 100%;
  height: auto;
  border-radius: var(--radius);
  margin: 1rem 0;
}

@media print {
  body { font-size: 11pt; }
  a { color: inherit; }
}
"""

DOCUMENT_CSS = """
.document {
  max-width: 800px;
  margin: 0 auto;
  padding: 3rem 2rem;
}

.document h1 {
  border-bottom: 2px solid var(--border);
  padding-bottom: 0.75rem;
  margin-bottom: 1.5rem;
}

.document .subtitle {
  color: var(--text-muted);
  font-size: 1.1rem;
  margin-top: -1rem;
  margin-bottom: 2rem;
}

@media print {
  .document { max-width: none; padding: 0; }
}
"""

PRESENTATION_CSS = """
.presentation {
  max-width: 100%;
  scroll-snap-type: y mandatory;
}

.slide {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 4rem 8rem;
  scroll-snap-align: start;
  position: relative;
}

.slide:not(:last-child)::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 8rem;
  right: 8rem;
  border-bottom: 1px solid var(--border);
}

.slide-title {
  text-align: center;
  padding: 6rem 8rem;
}

.slide-title h1 {
  font-size: 3rem;
  border: none;
  margin-bottom: 1rem;
}

.slide-title .subtitle {
  font-size: 1.5rem;
  color: var(--text-muted);
}

.slide h2 {
  font-size: 2rem;
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: var(--brand-primary);
}

.slide p { font-size: 1.25rem; }
.slide li { font-size: 1.25rem; margin-bottom: 0.5rem; }
.slide table { font-size: 1.05rem; }

.slide img {
  max-height: 50vh;
  object-fit: contain;
  margin: 1.5rem auto;
  display: block;
}

@media print {
  .slide {
    min-height: auto;
    page-break-after: always;
    padding: 2rem;
  }
  .slide::after { display: none; }
}
"""

DASHBOARD_CSS = """
.dashboard {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.dashboard > h1 {
  margin-bottom: 2rem;
  border-bottom: 2px solid var(--border);
  padding-bottom: 0.75rem;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1.5rem;
}

.card {
  background: var(--brand-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.card h2 {
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin: 0 0 1rem 0;
  border-bottom: 1px solid var(--border-light);
  padding-bottom: 0.5rem;
}

.card-wide {
  grid-column: 1 / -1;
}

.card table { margin: 0; }
.card img { margin: 0.5rem 0; }

@media print {
  .dashboard-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
"""

DATA_CSS = """
.data-view {
  max-width: 1100px;
  margin: 0 auto;
  padding: 2rem;
}

.data-view h1 {
  margin-bottom: 1.5rem;
  border-bottom: 2px solid var(--border);
  padding-bottom: 0.75rem;
}

.data-view table {
  font-size: 0.875rem;
}

.data-view th {
  position: sticky;
  top: 0;
  background: var(--surface);
  z-index: 1;
}

.data-view td {
  font-variant-numeric: tabular-nums;
}

@media print {
  .data-view { max-width: none; padding: 0; }
}
"""


# ---------------------------------------------------------------------------
# Markdown → HTML rendering
# ---------------------------------------------------------------------------

_MD = markdown.Markdown(
    extensions=["tables", "fenced_code", "toc", "nl2br", "sane_lists"],
    output_format="html",
)


def _render_markdown_to_html(md_text: str) -> str:
    """Convert markdown text to HTML fragment using Python-Markdown.

    Post-processes mermaid code blocks into mermaid.js-compatible divs.
    """
    _MD.reset()
    html = _MD.convert(md_text)

    # Convert <pre><code class="language-mermaid">...</code></pre>
    # to <pre class="mermaid">...</pre> for mermaid.js rendering
    html = re.sub(
        r'<pre><code class="language-mermaid">(.*?)</code></pre>',
        r'<pre class="mermaid">\1</pre>',
        html,
        flags=re.DOTALL,
    )

    return html


# ---------------------------------------------------------------------------
# Asset URL resolution
# ---------------------------------------------------------------------------

def _resolve_asset_urls(html: str, assets: list[dict]) -> str:
    """Replace local asset references with resolved URLs.

    assets: [{"ref": "assets/chart.svg", "url": "https://storage.../chart.svg"}, ...]
    Matches src="..." and href="..." attributes.
    """
    for asset in assets:
        ref = asset.get("ref", "")
        url = asset.get("url", "")
        if ref and url:
            html = html.replace(f'src="{ref}"', f'src="{url}"')
            html = html.replace(f"src='{ref}'", f"src='{url}'")
            html = html.replace(f'href="{ref}"', f'href="{url}"')
            html = html.replace(f"href='{ref}'", f"href='{url}'")
    return html


# ---------------------------------------------------------------------------
# Layout mode transformations
# ---------------------------------------------------------------------------

def _apply_document_layout(html_body: str, title: str) -> str:
    """Wrap HTML in document layout structure."""
    return f'<div class="document">\n<h1>{_esc(title)}</h1>\n{html_body}\n</div>'


def _apply_presentation_layout(html_body: str, title: str) -> str:
    """Split HTML at h2/hr boundaries into slide sections."""
    # Split the HTML fragment at <h2> and <hr> boundaries
    # Each h2 starts a new slide; content before first h2 is the title slide
    parts = re.split(r'(<h2[^>]*>.*?</h2>|<hr\s*/?>)', html_body, flags=re.DOTALL)

    slides: list[str] = []
    current_slide: list[str] = []
    is_first = True

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if re.match(r'<hr\s*/?>', part):
            # HR = slide break
            if current_slide:
                cls = "slide slide-title" if is_first else "slide"
                content = "\n".join(current_slide)
                slides.append(f'<section class="{cls}">\n{content}\n</section>')
                current_slide = []
                is_first = False
        elif re.match(r'<h2[^>]*>', part):
            # H2 = start new slide, flush previous
            if current_slide:
                cls = "slide slide-title" if is_first else "slide"
                content = "\n".join(current_slide)
                slides.append(f'<section class="{cls}">\n{content}\n</section>')
                current_slide = []
                is_first = False
            current_slide.append(part)
        else:
            current_slide.append(part)

    # Flush remaining content
    if current_slide:
        cls = "slide slide-title" if is_first else "slide"
        content = "\n".join(current_slide)
        slides.append(f'<section class="{cls}">\n{content}\n</section>')

    # If no slides were created (no h2/hr in content), wrap everything as one slide
    if not slides:
        slides = [f'<section class="slide slide-title">\n<h1>{_esc(title)}</h1>\n{html_body}\n</section>']
    else:
        # Prepend title slide if first slide doesn't have the title
        first = slides[0]
        if "slide-title" in first and f"<h1>" not in first:
            slides[0] = first.replace(
                '<section class="slide slide-title">\n',
                f'<section class="slide slide-title">\n<h1>{_esc(title)}</h1>\n',
            )

    return f'<div class="presentation">\n{"".join(slides)}\n</div>'


def _apply_dashboard_layout(html_body: str, title: str) -> str:
    """Arrange content into dashboard grid cards, split by h2 sections."""
    # Split at h2 boundaries — each section becomes a card
    parts = re.split(r'(<h2[^>]*>.*?</h2>)', html_body, flags=re.DOTALL)

    preamble: list[str] = []
    cards: list[str] = []
    current_card: list[str] = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if re.match(r'<h2[^>]*>', part):
            # Flush previous card
            if current_card:
                content = "\n".join(current_card)
                wide = "<table" in content or "<img" in content
                cls = "card card-wide" if wide else "card"
                cards.append(f'<div class="{cls}">\n{content}\n</div>')
                current_card = []
            current_card.append(part)
        else:
            if not current_card and not cards:
                preamble.append(part)
            else:
                current_card.append(part)

    # Flush remaining card
    if current_card:
        content = "\n".join(current_card)
        wide = "<table" in content or "<img" in content
        cls = "card card-wide" if wide else "card"
        cards.append(f'<div class="{cls}">\n{content}\n</div>')

    preamble_html = "\n".join(preamble) if preamble else ""
    grid_html = f'<div class="dashboard-grid">\n{"".join(cards)}\n</div>' if cards else ""

    return f'<div class="dashboard">\n<h1>{_esc(title)}</h1>\n{preamble_html}\n{grid_html}\n</div>'


def _apply_data_layout(html_body: str, title: str) -> str:
    """Wrap HTML in data view layout — optimized for tables."""
    return f'<div class="data-view">\n<h1>{_esc(title)}</h1>\n{html_body}\n</div>'


# ---------------------------------------------------------------------------
# Full document wrapper
# ---------------------------------------------------------------------------

def _wrap_full_document(body_html: str, css: str, title: str) -> str:
    """Produce a complete <!DOCTYPE html> document with mermaid.js support."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)}</title>
<style>
{css}
</style>
</head>
<body>
{body_html}
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<script>
  mermaid.initialize({{
    startOnLoad: true,
    theme: window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'default',
    flowchart: {{ useMaxWidth: true, htmlLabels: true }},
    securityLevel: 'loose',
  }});
</script>
</body>
</html>"""


def _esc(text: str) -> str:
    """Minimal HTML entity escaping for safe title injection."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ---------------------------------------------------------------------------
# Layout mode CSS mapping
# ---------------------------------------------------------------------------

_LAYOUT_CSS = {
    "document": DOCUMENT_CSS,
    "presentation": PRESENTATION_CSS,
    "dashboard": DASHBOARD_CSS,
    "data": DATA_CSS,
}

_LAYOUT_FN = {
    "document": _apply_document_layout,
    "presentation": _apply_presentation_layout,
    "dashboard": _apply_dashboard_layout,
    "data": _apply_data_layout,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose_html(
    md_text: str,
    title: str = "Output",
    layout_mode: str = "document",
    assets: list[dict] | None = None,
    brand_css: str | None = None,
) -> str:
    """Compose markdown + assets into a styled, self-contained HTML document.

    Args:
        md_text: Markdown source content.
        title: Document title (appears in <title> and heading).
        layout_mode: One of document, presentation, dashboard, data.
        assets: List of {ref, url} dicts for resolving local asset paths.
        brand_css: Optional CSS string for brand overrides.

    Returns:
        Complete HTML document string.
    """
    # 1. Markdown → HTML fragment
    html_body = _render_markdown_to_html(md_text)

    # 2. Resolve asset URLs
    if assets:
        html_body = _resolve_asset_urls(html_body, assets)

    # 3. Apply layout mode
    layout_fn = _LAYOUT_FN.get(layout_mode, _apply_document_layout)
    body_html = layout_fn(html_body, title)

    # 4. Assemble CSS: base + layout + brand
    layout_css = _LAYOUT_CSS.get(layout_mode, DOCUMENT_CSS)
    css_parts = [BASE_CSS, layout_css]
    if brand_css:
        css_parts.append(f"\n/* Brand overrides */\n{brand_css}")
    full_css = "\n".join(css_parts)

    # 5. Wrap in full HTML document
    return _wrap_full_document(body_html, full_css, title)
