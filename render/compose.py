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

import base64
import io
import re
from pydantic import BaseModel
from typing import Optional

import markdown
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class SectionContent(BaseModel):
    """ADR-177: Pre-parsed section with kind metadata. Sent by _compose_and_persist()."""
    kind: str = "narrative"  # narrative | callout | checklist | metric-cards | entity-grid |
                             # comparison-table | status-matrix | data-table | timeline |
                             # trend-chart | distribution-chart
    title: str
    content: str


class ComposeRequest(BaseModel):
    markdown: str = ""          # flat markdown fallback (used when sections absent)
    title: str = "Output"
    surface_type: str = "report"  # report | deck | dashboard | digest | workbook | preview | video
    assets: list[dict] = []  # [{ref: "chart.svg", url: "https://..."}]
    brand_css: Optional[str] = None
    user_id: Optional[str] = None
    # ADR-177 Phase D1: pre-parsed sections with kind metadata
    sections: list[SectionContent] = []  # when non-empty, compose from sections not flat markdown


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
  margin: 1.5rem 0;
  display: block;
}

/* Image with caption (from alt text) */
figure {
  margin: 1.5rem 0;
  text-align: center;
}
figure img {
  margin: 0 auto 0.5rem;
}
figcaption {
  font-size: 0.825rem;
  color: var(--text-muted);
  font-style: italic;
}

/* Video embeds */
video {
  max-width: 100%;
  height: auto;
  border-radius: var(--radius);
  margin: 1.5rem 0;
  display: block;
  background: var(--surface);
}

/* Mermaid diagram container */
pre.mermaid {
  background: transparent;
  border: none;
  padding: 1rem 0;
  text-align: center;
  overflow: visible;
}

@media print {
  body { font-size: 11pt; }
  a { color: inherit; }
  video { display: none; }
}
"""

DOCUMENT_CSS = """
.document {
  max-width: min(800px, 100%);
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
  padding: 4rem clamp(2rem, 8vw, 8rem);
  scroll-snap-align: start;
  position: relative;
}

.slide:not(:last-child)::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: clamp(2rem, 8vw, 8rem);
  right: clamp(2rem, 8vw, 8rem);
  border-bottom: 1px solid var(--border);
}

.slide-title {
  text-align: center;
  padding: 6rem clamp(2rem, 8vw, 8rem);
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
  max-width: 100%;
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
  grid-template-columns: repeat(auto-fit, minmax(min(320px, 100%), 1fr));
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
  max-width: 100%;
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

# Email mode: inline-safe CSS for email clients (Gmail, Outlook, Apple Mail).
# No CSS variables, no flexbox/grid, no prefers-color-scheme, no external fonts.
EMAIL_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  font-size: 14px;
  line-height: 1.6;
  color: #1a1a1a;
  background: #ffffff;
  -webkit-font-smoothing: antialiased;
}

h1, h2, h3, h4, h5, h6 { line-height: 1.3; font-weight: 600; color: #1a1a1a; }
h1 { font-size: 22px; margin-bottom: 16px; }
h2 { font-size: 18px; margin-top: 24px; margin-bottom: 12px; }
h3 { font-size: 16px; margin-top: 20px; margin-bottom: 8px; }
h4 { font-size: 15px; margin-top: 16px; margin-bottom: 8px; color: #4b5563; }

p { margin-bottom: 14px; }

a { color: #1a56db; text-decoration: none; }

strong { font-weight: 600; color: #1a1a1a; }

ul, ol { margin-bottom: 14px; padding-left: 24px; }
li { margin-bottom: 6px; }

table {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  font-size: 13px;
}
th, td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}
th {
  font-weight: 600;
  color: #4b5563;
  background: #f9fafb;
  border-bottom: 2px solid #e5e7eb;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

code {
  background: #f3f4f6;
  padding: 1px 4px;
  border-radius: 3px;
  font-family: Monaco, Menlo, monospace;
  font-size: 13px;
}

pre {
  background: #f9fafb;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 12px 0;
  border: 1px solid #e5e7eb;
}
pre code { background: none; padding: 0; }

blockquote {
  border-left: 3px solid #1a56db;
  margin: 16px 0;
  padding: 10px 16px;
  color: #4b5563;
  background: #e1effe;
  border-radius: 0 6px 6px 0;
}

hr {
  border: none;
  border-top: 1px solid #e5e7eb;
  margin: 24px 0;
}

img {
  max-width: 100%;
  height: auto;
  border-radius: 6px;
  margin: 16px 0;
  display: block;
}
"""

EMAIL_LAYOUT_CSS = """
.email-body {
  max-width: 600px;
  margin: 0 auto;
  padding: 24px 20px;
}

.email-body h1 {
  padding-bottom: 12px;
  border-bottom: 1px solid #e5e7eb;
  margin-bottom: 20px;
}

.email-subtitle {
  color: #9ca3af;
  font-size: 12px;
  margin-top: -16px;
  margin-bottom: 24px;
}

.email-footer {
  margin-top: 32px;
  padding-top: 20px;
  border-top: 1px solid #e5e7eb;
  text-align: center;
}

.email-footer a.feedback-btn {
  display: inline-block;
  background: #111;
  color: #fff;
  padding: 10px 24px;
  text-decoration: none;
  border-radius: 9999px;
  font-weight: 500;
  font-size: 14px;
}

.email-footer .hint {
  color: #9ca3af;
  font-size: 12px;
  margin-top: 12px;
}

.email-footer .meta {
  color: #9ca3af;
  font-size: 11px;
  margin-top: 12px;
}
.email-footer .meta a { color: #9ca3af; }
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

    Post-processes for rich content rendering:
    - Mermaid code blocks → mermaid.js-compatible divs
    - Images with alt text → figure + figcaption
    - Video links (.mp4, .webm) → <video> elements
    """
    _MD.reset()
    html = _MD.convert(md_text)

    # Mermaid: <pre><code class="language-mermaid"> → <pre class="mermaid">
    html = re.sub(
        r'<pre><code class="language-mermaid">(.*?)</code></pre>',
        r'<pre class="mermaid">\1</pre>',
        html,
        flags=re.DOTALL,
    )

    # Images with alt text → figure + figcaption (skip empty alt or "image")
    def _img_to_figure(match):
        full = match.group(0)
        alt = re.search(r'alt="([^"]*)"', full)
        if alt and alt.group(1) and alt.group(1).lower() not in ("image", "img", ""):
            return f'<figure>{full}<figcaption>{alt.group(1)}</figcaption></figure>'
        return full

    html = re.sub(r'<img [^>]+>', _img_to_figure, html)

    # Video links: <img> with .mp4/.webm src → <video> element
    html = re.sub(
        r'<img\s+(?:[^>]*?)src="([^"]*\.(?:mp4|webm))"(?:[^>]*?)(?:alt="([^"]*)")?[^>]*/?>',
        r'<video controls preload="metadata" src="\1" title="\2"></video>',
        html,
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
                wide = "<table" in content or "<img" in content or "dashboard-wide-hint" in content
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
        wide = "<table" in content or "<img" in content or "dashboard-wide-hint" in content
        cls = "card card-wide" if wide else "card"
        cards.append(f'<div class="{cls}">\n{content}\n</div>')

    preamble_html = "\n".join(preamble) if preamble else ""
    grid_html = f'<div class="dashboard-grid">\n{"".join(cards)}\n</div>' if cards else ""

    return f'<div class="dashboard">\n<h1>{_esc(title)}</h1>\n{preamble_html}\n{grid_html}\n</div>'


def _apply_data_layout(html_body: str, title: str) -> str:
    """Wrap HTML in data view layout — optimized for tables."""
    return f'<div class="data-view">\n<h1>{_esc(title)}</h1>\n{html_body}\n</div>'


def _apply_email_layout(html_body: str, title: str) -> str:
    """Wrap HTML in email-safe layout — max 600px, inline-friendly, with footer."""
    return f'<div class="email-body">\n<h1>{_esc(title)}</h1>\n{html_body}\n</div>'


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


def _wrap_email_document(body_html: str, css: str, title: str) -> str:
    """Produce a complete HTML document for email — no external scripts, no mermaid.js."""
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

# ADR-170: surface_type vocabulary → layout implementation mapping.
# Seven surface types map to the four current layout implementations.
# preview + video use report layout until Phase 6 (view-time rendering).
_SURFACE_CSS = {
    "report": DOCUMENT_CSS,
    "deck": PRESENTATION_CSS,
    "dashboard": DASHBOARD_CSS,
    "digest": EMAIL_LAYOUT_CSS,   # scannable, mobile-friendly (same as email layout)
    "workbook": DATA_CSS,
    "preview": DOCUMENT_CSS,      # Phase 6: platform-framed cards
    "video": DOCUMENT_CSS,        # Phase 6: Remotion scene graph
}

_SURFACE_FN = {
    "report": _apply_document_layout,
    "deck": _apply_presentation_layout,
    "dashboard": _apply_dashboard_layout,
    "digest": _apply_email_layout,    # scannable grouped stream
    "workbook": _apply_data_layout,
    "preview": _apply_document_layout,
    "video": _apply_document_layout,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _render_metric_cards(content: str) -> str:
    """ADR-177 Phase 5b: metric-cards kind → responsive card grid.

    Expected agent output format (flexible):
      **Label**: value
      Label: value
      - **Label**: value  (with leading dash)
    Each line becomes one card.
    """
    cards = []
    for line in content.splitlines():
        line = line.strip().lstrip("- ").strip()
        if not line:
            continue
        # Try **label**: value or label: value
        m = re.match(r'\*{0,2}([^*:]+)\*{0,2}\s*:\s*(.*)', line)
        if m:
            label = m.group(1).strip()
            value = m.group(2).strip()
        else:
            # Treat whole line as value
            label = ""
            value = line
        label_html = f'<div class="mc-label">{_esc(label)}</div>' if label else ""
        cards.append(
            f'<div class="mc-card">{label_html}'
            f'<div class="mc-value">{_esc(value)}</div></div>'
        )
    return f'<div class="metric-cards">\n{"".join(cards)}\n</div>'


def _render_entity_grid(content: str) -> str:
    """ADR-177 Phase 5b: entity-grid kind → entity cards with property rows.

    Expected agent output format:
      ## Entity Name
      **Property**: value
      **Property**: value

    or flat list:
      - **Entity Name** — tagline / description
    """
    # Check if it's a list of entities (no ## headings) or structured blocks
    if "## " not in content:
        # Flat list → simple cards
        md_html = _render_markdown_to_html(content)
        # Wrap each <li> block as a card via post-processing
        # Convert <ul><li>...</li></ul> → card grid
        cards = re.findall(r'<li>(.*?)</li>', md_html, re.DOTALL)
        if cards:
            card_html = "".join(
                f'<div class="eg-card">{c}</div>' for c in cards
            )
            return f'<div class="entity-grid">{card_html}</div>'
        return f'<div class="entity-grid">{md_html}</div>'

    # Structured blocks: split at ## headings
    blocks = re.split(r'(?m)^##\s+', content)
    card_htmls = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        entity_name = lines[0].strip()
        props = []
        desc_lines = []
        for line in lines[1:]:
            line = line.strip()
            m = re.match(r'\*{0,2}([^*:]+)\*{0,2}\s*:\s*(.*)', line)
            if m:
                props.append((m.group(1).strip(), m.group(2).strip()))
            elif line:
                desc_lines.append(line)
        prop_rows = "".join(
            f'<div class="eg-prop"><span class="eg-key">{_esc(k)}</span>'
            f'<span class="eg-val">{_esc(v)}</span></div>'
            for k, v in props
        )
        desc_html = ""
        if desc_lines:
            desc_html = f'<p class="eg-desc">{_esc(" ".join(desc_lines))}</p>'
        card_htmls.append(
            f'<div class="eg-card">'
            f'<div class="eg-name">{_esc(entity_name)}</div>'
            f'{desc_html}{prop_rows}</div>'
        )
    return f'<div class="entity-grid">{"".join(card_htmls)}</div>'


def _render_comparison_table(content: str) -> str:
    """ADR-177 Phase 5b: comparison-table kind → table with first-column highlighting.

    Accepts markdown table format — renders with comparison-table CSS class that
    highlights the first (label/entity) column distinctly.
    """
    html = _render_markdown_to_html(content)
    # Add comparison-table class to <table>
    html = html.replace("<table>", '<table class="comparison-table">', 1)
    return html


def _render_status_matrix(content: str) -> str:
    """ADR-177 Phase 5b: status-matrix kind → status badge rows.

    Expected agent output format:
      - [done] Task name: optional note
      - [in-progress] Task name: optional note
      - [blocked] Task name: note
      - [pending] Task name
    Status values: done, complete, in-progress, progress, blocked, pending, skip, na
    """
    STATUS_CLASSES = {
        "done": "sm-done", "complete": "sm-done", "completed": "sm-done",
        "in-progress": "sm-progress", "progress": "sm-progress", "active": "sm-progress",
        "blocked": "sm-blocked", "block": "sm-blocked",
        "pending": "sm-pending", "todo": "sm-pending", "planned": "sm-pending",
        "skip": "sm-skip", "na": "sm-skip", "n/a": "sm-skip",
    }
    rows = []
    for line in content.splitlines():
        line = line.strip().lstrip("- ").strip()
        if not line:
            continue
        # Try [status] label: note
        m = re.match(r'\[([^\]]+)\]\s+(.*?)(?::\s*(.*))?$', line)
        if m:
            raw_status = m.group(1).strip().lower()
            label = m.group(2).strip()
            note = (m.group(3) or "").strip()
        else:
            # No status bracket — treat as pending
            raw_status = "pending"
            label = line
            note = ""
        css_class = STATUS_CLASSES.get(raw_status, "sm-pending")
        display_status = raw_status.replace("-", " ").title()
        note_html = f'<span class="sm-note">{_esc(note)}</span>' if note else ""
        rows.append(
            f'<div class="sm-row">'
            f'<span class="sm-badge {css_class}">{_esc(display_status)}</span>'
            f'<span class="sm-label">{_esc(label)}</span>'
            f'{note_html}</div>'
        )
    return f'<div class="status-matrix">{"".join(rows)}</div>'


def _render_data_table(content: str) -> str:
    """ADR-177 Phase 5b: data-table kind → dense numeric table.

    Accepts markdown table format. Adds data-table CSS class for numeric styling
    (tabular nums, tighter cells, sticky header).
    """
    html = _render_markdown_to_html(content)
    html = html.replace("<table>", '<table class="data-table">', 1)
    return html


def _render_timeline(content: str) -> str:
    """ADR-177 Phase 5b: timeline kind → vertical timeline entries.

    Expected agent output format:
      - **2024-Q1**: Event description
      - **Jan 2024**: Event description
      YYYY-MM-DD: description
      or plain list items — each item becomes a timeline entry.
    """
    entries = []
    for line in content.splitlines():
        line = line.strip().lstrip("- ").strip()
        if not line:
            continue
        # Try **date**: description or date: description
        m = re.match(r'\*{0,2}([^*:]+?)\*{0,2}\s*:\s*(.*)', line)
        if m:
            date = m.group(1).strip()
            desc = m.group(2).strip()
        else:
            date = ""
            desc = line
        date_html = f'<div class="tl-date">{_esc(date)}</div>' if date else ""
        entries.append(
            f'<div class="tl-entry">'
            f'<div class="tl-marker"></div>'
            f'<div class="tl-content">{date_html}'
            f'<div class="tl-desc">{_esc(desc)}</div></div></div>'
        )
    return f'<div class="timeline">{"".join(entries)}</div>'


# CSS for structured-data kinds (appended to BASE_CSS for section-rendered documents)
STRUCTURED_DATA_CSS = """
/* metric-cards */
.metric-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(160px, 100%), 1fr));
  gap: 1rem;
  margin: 1.5rem 0;
}
.mc-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.25rem 1rem;
  text-align: center;
}
.mc-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
}
.mc-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

/* entity-grid */
.entity-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(260px, 100%), 1fr));
  gap: 1rem;
  margin: 1.5rem 0;
}
.eg-card {
  background: var(--brand-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.25rem;
}
.eg-name {
  font-weight: 600;
  font-size: 1rem;
  margin-bottom: 0.5rem;
  color: var(--text-primary);
}
.eg-desc {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin-bottom: 0.75rem;
}
.eg-prop {
  display: flex;
  gap: 0.5rem;
  font-size: 0.8125rem;
  margin-bottom: 0.25rem;
}
.eg-key {
  color: var(--text-muted);
  min-width: 80px;
  flex-shrink: 0;
}
.eg-val { color: var(--text-primary); }

/* comparison-table */
table.comparison-table td:first-child,
table.comparison-table th:first-child {
  font-weight: 600;
  background: var(--surface);
  color: var(--text-primary);
  border-right: 2px solid var(--border);
  min-width: 120px;
}

/* data-table */
table.data-table {
  font-size: 0.8125rem;
  font-variant-numeric: tabular-nums;
}
table.data-table td { padding: 0.4rem 0.75rem; }

/* status-matrix */
.status-matrix { margin: 1.5rem 0; display: flex; flex-direction: column; gap: 0.5rem; }
.sm-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  background: var(--surface);
  border-radius: calc(var(--radius) / 2);
  border: 1px solid var(--border-light);
}
.sm-badge {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0.2rem 0.5rem;
  border-radius: 9999px;
  flex-shrink: 0;
}
.sm-done    { background: #d1fae5; color: #065f46; }
.sm-progress{ background: #dbeafe; color: #1e40af; }
.sm-blocked { background: #fee2e2; color: #991b1b; }
.sm-pending { background: #f3f4f6; color: #4b5563; }
.sm-skip    { background: #f3f4f6; color: #9ca3af; }
.sm-label { font-size: 0.9rem; font-weight: 500; flex: 1; }
.sm-note { font-size: 0.8rem; color: var(--text-muted); }

/* timeline */
.timeline { margin: 1.5rem 0; position: relative; padding-left: 1.5rem; }
.timeline::before {
  content: '';
  position: absolute;
  left: 6px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--border);
}
.tl-entry {
  position: relative;
  display: flex;
  gap: 1rem;
  margin-bottom: 1.25rem;
}
.tl-marker {
  position: absolute;
  left: -1.5rem;
  top: 4px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--brand-primary);
  border: 2px solid var(--brand-bg);
  flex-shrink: 0;
}
.tl-date {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--brand-primary);
  margin-bottom: 0.2rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.tl-desc { font-size: 0.9rem; color: var(--text-secondary); }

/* Phase 5d: surface×kind overrides */
/* dashboard: wide-hint signals card-wide layout for the layout function */
.dashboard-wide-hint { grid-column: 1 / -1; }

/* deck: section wrapper carries kind metadata for slide sizing */
.deck-section { width: 100%; }

/* section wrappers */
.section-callout {
  background: var(--brand-primary-light);
  border-left: 4px solid var(--brand-primary);
  padding: 1rem 1.25rem;
  border-radius: 0 var(--radius) var(--radius) 0;
  margin: 1.5rem 0;
}
.section-checklist { margin: 1.5rem 0; }
.section-narrative { margin: 1.5rem 0; }
"""


def _parse_chart_content(content: str, kind: str) -> dict:
    """Parse agent section content into chart data spec.

    Accepts two formats:
    1. Structured key: value + data lines:
       x_label: Month
       y_label: Revenue ($K)
       Jan 2024: 45
       Feb 2024: 52
       ...

    2. Markdown table (for multi-series):
       | Label | Series A | Series B |
       | Jan   | 45       | 30       |

    Returns a dict compatible with render_chart() input_data.
    """
    lines = [l.strip() for l in content.splitlines() if l.strip()]

    # Detect markdown table
    if any(l.startswith("|") for l in lines):
        table_lines = [l for l in lines if l.startswith("|") and not re.match(r'\|[-| :]+\|', l)]
        if len(table_lines) >= 2:
            headers = [h.strip() for h in table_lines[0].split("|") if h.strip()]
            labels = []
            datasets_raw: dict[str, list] = {h: [] for h in headers[1:]}
            for row_line in table_lines[1:]:
                cells = [c.strip() for c in row_line.split("|") if c.strip()]
                if not cells:
                    continue
                labels.append(cells[0])
                for i, series_name in enumerate(headers[1:]):
                    try:
                        val = float(cells[i + 1].replace(",", "").replace("%", "").strip())
                    except (IndexError, ValueError):
                        val = 0.0
                    datasets_raw[series_name].append(val)
            chart_type = "line" if kind == "trend-chart" else "bar"
            return {
                "chart_type": chart_type,
                "title": "",
                "labels": labels,
                "datasets": [{"label": k, "data": v} for k, v in datasets_raw.items()],
            }

    # Structured key: value format
    meta: dict = {}
    data_points: list[tuple[str, float]] = []
    for line in lines:
        m = re.match(r'^([^:]+):\s*(.+)$', line)
        if not m:
            continue
        key = m.group(1).strip()
        val_str = m.group(2).strip()
        if key.lower() in ("title", "x_label", "y_label", "chart_type", "label"):
            meta[key.lower()] = val_str
            continue
        # Try numeric value → data point
        try:
            val = float(val_str.replace(",", "").replace("%", "").strip())
            data_points.append((key, val))
        except ValueError:
            pass

    chart_type = "line" if kind == "trend-chart" else "bar"
    if "chart_type" in meta:
        chart_type = meta["chart_type"]

    series_label = meta.get("label", "Value")
    return {
        "chart_type": chart_type,
        "title": meta.get("title", ""),
        "labels": [p[0] for p in data_points],
        "datasets": [{"label": series_label, "data": [p[1] for p in data_points]}],
        "x_label": meta.get("x_label", ""),
        "y_label": meta.get("y_label", ""),
    }


def _render_chart_kind(section: "SectionContent") -> str:
    """ADR-177 Phase 5c: Render trend-chart / distribution-chart via matplotlib.

    Parses agent section content, generates a PNG, embeds as base64 data URI.
    Falls back to markdown rendering if parsing yields no data points.
    """
    kind = section.kind
    try:
        spec = _parse_chart_content(section.content, kind)
        labels = spec.get("labels", [])
        datasets = spec.get("datasets", [])

        if not labels or not datasets or not datasets[0].get("data"):
            raise ValueError("no data points parsed")

        chart_type = spec.get("chart_type", "bar")
        title_text = spec.get("title", section.title or "")

        # Style: clean, minimal, matches brand colors
        plt.rcParams.update({
            "font.family": "DejaVu Sans",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.3,
            "axes.facecolor": "#f9fafb",
            "figure.facecolor": "#ffffff",
        })

        fig, ax = plt.subplots(figsize=(9, 4.5))

        brand_colors = ["#1a56db", "#60a5fa", "#3b82f6", "#93c5fd", "#bfdbfe"]

        if chart_type == "line":
            for i, ds in enumerate(datasets):
                color = brand_colors[i % len(brand_colors)]
                ax.plot(
                    labels, ds["data"],
                    marker="o", linewidth=2, markersize=5,
                    color=color, label=ds.get("label", ""),
                )
        elif chart_type in ("bar", "distribution-chart"):
            import numpy as np
            x = range(len(labels))
            bar_width = 0.8 / max(len(datasets), 1)
            for i, ds in enumerate(datasets):
                color = brand_colors[i % len(brand_colors)]
                offsets = [xi + (i - len(datasets) / 2 + 0.5) * bar_width for xi in x]
                ax.bar(offsets, ds["data"], bar_width, color=color,
                       label=ds.get("label", ""), alpha=0.85)
            ax.set_xticks(list(x))
            ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=9)
        elif chart_type == "pie":
            ax.pie(
                datasets[0]["data"],
                labels=labels,
                colors=brand_colors[: len(labels)],
                autopct="%1.0f%%",
                startangle=90,
            )

        if title_text:
            ax.set_title(title_text, fontsize=12, fontweight="bold", pad=12)
        if spec.get("x_label") and chart_type != "pie":
            ax.set_xlabel(spec["x_label"], fontsize=9)
        if spec.get("y_label") and chart_type != "pie":
            ax.set_ylabel(spec["y_label"], fontsize=9)
        if len(datasets) > 1:
            ax.legend(fontsize=9, framealpha=0.7)

        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=144, bbox_inches="tight")
        plt.close(fig)

        png_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        alt = _esc(section.title or title_text or kind)
        return (
            f'<div class="section-kind-{kind} chart-embed" data-kind="{kind}">'
            f'<img src="data:image/png;base64,{png_b64}" alt="{alt}" '
            f'style="width:100%;max-width:720px;height:auto;border-radius:8px;margin:1rem auto;display:block;">'
            f'</div>\n'
        )

    except Exception:
        # Graceful fallback: markdown with data-kind attribute
        body = _render_markdown_to_html(section.content)
        title_html = f"<h2>{_esc(section.title)}</h2>\n" if section.title else ""
        return f'<div class="section-kind-{kind}" data-kind="{kind}">{title_html}{body}</div>\n'


def _render_section_to_html(section: "SectionContent", surface_type: str = "report") -> str:
    """ADR-177 Phase 5b+5d: Render a single section to HTML based on kind and surface.

    Markdown kinds: narrative, callout, checklist → python-markdown.
    Structured-data kinds: metric-cards, entity-grid, comparison-table,
      status-matrix, data-table, timeline → component HTML generators.
    Chart kinds: trend-chart, distribution-chart → matplotlib PNG (Phase 5c).
    Surface×kind overrides (Phase 5d):
      - deck: each section wrapped in <section class="slide"> for scroll-snap
      - dashboard: chart/table sections get card-wide class hint
    """
    kind = section.kind
    content = section.content
    title_html = f"<h2>{_esc(section.title)}</h2>\n" if section.title else ""

    # --- Markdown kinds ---
    if kind == "narrative":
        body = _render_markdown_to_html(content)
        inner = f'<div class="section-narrative">{title_html}{body}</div>\n'

    elif kind == "callout":
        body = _render_markdown_to_html(content)
        inner = f'<div class="section-callout">{title_html}{body}</div>\n'

    elif kind == "checklist":
        body = _render_markdown_to_html(content)
        inner = f'<div class="section-checklist">{title_html}{body}</div>\n'

    # --- Structured-data kinds ---
    elif kind == "metric-cards":
        inner = f'<div class="section-kind-metric-cards" data-kind="metric-cards">{title_html}{_render_metric_cards(content)}</div>\n'

    elif kind == "entity-grid":
        inner = f'<div class="section-kind-entity-grid" data-kind="entity-grid">{title_html}{_render_entity_grid(content)}</div>\n'

    elif kind == "comparison-table":
        inner = f'<div class="section-kind-comparison-table" data-kind="comparison-table">{title_html}{_render_comparison_table(content)}</div>\n'

    elif kind == "status-matrix":
        inner = f'<div class="section-kind-status-matrix" data-kind="status-matrix">{title_html}{_render_status_matrix(content)}</div>\n'

    elif kind == "data-table":
        inner = f'<div class="section-kind-data-table" data-kind="data-table">{title_html}{_render_data_table(content)}</div>\n'

    elif kind == "timeline":
        inner = f'<div class="section-kind-timeline" data-kind="timeline">{title_html}{_render_timeline(content)}</div>\n'

    # --- Chart kinds → matplotlib PNG embedded as base64 (Phase 5c) ---
    elif kind in ("trend-chart", "distribution-chart"):
        inner = f'{title_html}{_render_chart_kind(section)}'

    # --- Unknown kinds → markdown fallback with data-kind ---
    else:
        body = _render_markdown_to_html(content)
        inner = f'<div class="section-kind-{kind}" data-kind="{kind}">{title_html}{body}</div>\n'

    # --- Phase 5d: surface×kind overrides ---
    if surface_type == "deck":
        # Wrap in slide container — presentation layout will re-split at <h2>,
        # but since section content has no h2 (title is in title_html which is already h2),
        # and we emit sections without an outer h2, the existing _apply_presentation_layout
        # will treat each emitted h2 as a slide boundary. This is correct behavior.
        # For sections with no title_html (no h2 emitted), deck layout wraps as-is.
        # We add data-kind so deck renderer can apply slide sizing hints.
        inner = inner.rstrip("\n")
        inner = f'<div data-kind="{kind}" class="deck-section">{inner}</div>\n'

    elif surface_type == "dashboard":
        # Chart and table kinds get card-wide hint for the dashboard grid.
        # metric-cards and entity-grid have their own grids and don't need card-wide.
        wide_kinds = {"trend-chart", "distribution-chart", "comparison-table",
                      "data-table", "timeline"}
        if kind in wide_kinds:
            inner = inner.rstrip("\n")
            inner = f'<div class="dashboard-wide-hint">{inner}</div>\n'

    return inner


def compose_html(
    md_text: str,
    title: str = "Output",
    surface_type: str = "report",
    assets: list[dict] | None = None,
    brand_css: str | None = None,
    sections: list | None = None,  # ADR-177: list[SectionContent] when available
) -> str:
    """Compose markdown + assets into a styled, self-contained HTML document.

    ADR-170: surface_type is the visual paradigm (report | deck | dashboard |
    digest | workbook | preview | video). Each maps to a layout implementation.

    ADR-177 Phase D1: when sections is non-empty, render section-by-section
    using kind-specific renderers instead of flat markdown. Phase D2 will extend
    each kind renderer; Phase D1 ensures the pipeline ordering is correct and
    kind metadata flows through.

    Args:
        md_text: Markdown source content (used when sections is empty/None).
        title: Document title (appears in <title> and heading).
        surface_type: Visual paradigm. One of: report, deck, dashboard, digest,
            workbook, preview, video.
        assets: List of {ref, url} dicts for resolving local asset paths.
        brand_css: Optional CSS string for brand overrides.
        sections: Pre-parsed SectionContent list from _compose_and_persist().

    Returns:
        Complete HTML document string.
    """
    # digest surface uses the email-safe rendering path (no JS, mobile-first)
    is_email_style = surface_type in ("digest",)

    # ADR-177 Phase D1: section-aware rendering path
    if sections:
        section_html_parts = []
        for sec in sections:
            part = _render_section_to_html(sec, surface_type=surface_type)
            if assets:
                part = _resolve_asset_urls(part, assets)
            if is_email_style:
                part = re.sub(
                    r'<pre class="mermaid">(.*?)</pre>',
                    r'<pre><code>\1</code></pre>',
                    part,
                    flags=re.DOTALL,
                )
            section_html_parts.append(part)
        html_body = "\n".join(section_html_parts)
    else:
        # 1. Markdown → HTML fragment (flat path — no sections declared)
        html_body = _render_markdown_to_html(md_text)

        # 2. Resolve asset URLs
        if assets:
            html_body = _resolve_asset_urls(html_body, assets)

        # 3. Digest/email-style: strip mermaid code blocks (no JS) — show as code instead
        if is_email_style:
            html_body = re.sub(
                r'<pre class="mermaid">(.*?)</pre>',
                r'<pre><code>\1</code></pre>',
                html_body,
                flags=re.DOTALL,
            )

    # 4. Apply surface layout
    layout_fn = _SURFACE_FN.get(surface_type, _apply_document_layout)
    body_html = layout_fn(html_body, title)

    # 5. Assemble CSS: digest uses email-safe base (no CSS variables), others use BASE_CSS
    if is_email_style:
        surface_css = _SURFACE_CSS.get(surface_type, EMAIL_LAYOUT_CSS)
        css_parts = [EMAIL_CSS, surface_css]
    else:
        surface_css = _SURFACE_CSS.get(surface_type, DOCUMENT_CSS)
        css_parts = [BASE_CSS, surface_css]
    # Inject structured-data component CSS when rendering via sections (Phase 5b)
    if sections:
        css_parts.append(STRUCTURED_DATA_CSS)
    if brand_css:
        css_parts.append(f"\n/* Brand overrides */\n{brand_css}")
    full_css = "\n".join(css_parts)

    # 6. Wrap in full HTML document (digest/email-style skips mermaid.js script)
    if is_email_style:
        return _wrap_email_document(body_html, full_css, title)
    return _wrap_full_document(body_html, full_css, title)
