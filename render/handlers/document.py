"""Document handler — markdown → PDF/DOCX via pandoc."""

import subprocess
import tempfile
from pathlib import Path


async def render_document(input_data: dict, output_format: str) -> tuple[bytes, str]:
    """
    Render markdown to PDF or DOCX.

    input_data: {"markdown": str, "title": str (optional)}
    output_format: "pdf" or "docx"
    Returns: (file_bytes, content_type)
    """
    markdown = input_data.get("markdown", "")
    title = input_data.get("title", "Document")

    if output_format not in ("pdf", "docx"):
        raise ValueError(f"Unsupported document format: {output_format}")

    content_types = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input.md"
        output_path = Path(tmpdir) / f"output.{output_format}"

        input_path.write_text(markdown, encoding="utf-8")

        cmd = [
            "pandoc",
            str(input_path),
            "-o", str(output_path),
            f"--metadata=title:{title}",
            "--standalone",
        ]

        if output_format == "pdf":
            cmd.extend(["--pdf-engine=pdflatex"])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"pandoc failed: {result.stderr}")

        return output_path.read_bytes(), content_types[output_format]
