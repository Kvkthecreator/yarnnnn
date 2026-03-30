"""PDF/DOCX skill — markdown or HTML → PDF/DOCX via pandoc.

ADR-148: Accepts both markdown and HTML input. HTML is the primary path
(from composed output.html). Markdown is fallback for legacy/direct usage.
"""

import subprocess
import tempfile
from pathlib import Path


async def render_pdf(input_data: dict, output_format: str) -> tuple[bytes, str]:
    """
    Render markdown or HTML to PDF or DOCX.

    input_data: {
        "html": str (preferred — composed HTML from output.html),
        "markdown": str (fallback — raw markdown),
        "title": str (optional)
    }
    output_format: "pdf" or "docx"
    Returns: (file_bytes, content_type)
    """
    html = input_data.get("html", "")
    markdown = input_data.get("markdown", "")
    title = input_data.get("title", "Document")

    if not html and not markdown:
        raise ValueError("Either 'html' or 'markdown' must be provided")

    if output_format not in ("pdf", "docx"):
        raise ValueError(f"Unsupported document format: {output_format}")

    content_types = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / f"output.{output_format}"

        # Prefer HTML input (from composed output.html)
        if html:
            input_path = Path(tmpdir) / "input.html"
            input_path.write_text(html, encoding="utf-8")
            input_format_flag = "-f html"
        else:
            input_path = Path(tmpdir) / "input.md"
            input_path.write_text(markdown, encoding="utf-8")
            input_format_flag = ""

        cmd = [
            "pandoc",
            str(input_path),
            "-o", str(output_path),
            f"--metadata=title:{title}",
            "--standalone",
        ]

        if input_format_flag:
            cmd.extend(input_format_flag.split())

        if output_format == "pdf":
            cmd.extend(["--pdf-engine=pdflatex"])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(f"pandoc failed: {result.stderr}")

        return output_path.read_bytes(), content_types[output_format]
