"""HTML report skill — markdown → styled HTML via pandoc."""

import subprocess
import tempfile
from pathlib import Path

# Minimal embedded CSS for clean, readable reports
_DEFAULT_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       max-width: 800px; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; line-height: 1.6; }
h1 { border-bottom: 2px solid #e5e7eb; padding-bottom: 0.5rem; }
h2 { color: #374151; margin-top: 2rem; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
th, td { border: 1px solid #d1d5db; padding: 0.5rem 0.75rem; text-align: left; }
th { background: #f3f4f6; font-weight: 600; }
tr:nth-child(even) { background: #f9fafb; }
code { background: #f3f4f6; padding: 0.125rem 0.25rem; border-radius: 3px; font-size: 0.9em; }
pre { background: #f3f4f6; padding: 1rem; border-radius: 6px; overflow-x: auto; }
blockquote { border-left: 4px solid #d1d5db; margin: 1rem 0; padding: 0.5rem 1rem; color: #6b7280; }
@media print { body { max-width: none; } }
"""


async def render_html(input_data: dict, output_format: str) -> tuple[bytes, str]:
    """
    Render markdown to self-contained HTML report.

    input_data: {"markdown": str, "title": str (optional)}
    output_format: "html"
    Returns: (file_bytes, content_type)
    """
    markdown = input_data.get("markdown", "")
    title = input_data.get("title", "Report")

    if output_format != "html":
        raise ValueError(f"Unsupported report format: {output_format}")

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input.md"
        output_path = Path(tmpdir) / "output.html"
        css_path = Path(tmpdir) / "style.css"

        input_path.write_text(markdown, encoding="utf-8")
        css_path.write_text(_DEFAULT_CSS, encoding="utf-8")

        cmd = [
            "pandoc",
            str(input_path),
            "-o", str(output_path),
            "--standalone",
            "--self-contained",
            f"--metadata=title:{title}",
            f"--css={css_path}",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"pandoc failed: {result.stderr}")

        return output_path.read_bytes(), "text/html"
