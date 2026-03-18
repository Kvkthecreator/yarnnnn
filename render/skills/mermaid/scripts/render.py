"""Mermaid diagram skill — mermaid syntax → PNG/SVG via mermaid-cli (mmdc)."""

import subprocess
import tempfile
from pathlib import Path


async def render_mermaid(input_data: dict, output_format: str) -> tuple[bytes, str]:
    """
    Render a Mermaid diagram to PNG or SVG.

    input_data: {"mermaid": str, "title": str (optional)}
    output_format: "png" or "svg"
    Returns: (file_bytes, content_type)
    """
    mermaid_src = input_data.get("mermaid", "")
    if not mermaid_src.strip():
        raise ValueError("Empty mermaid source")

    if output_format not in ("png", "svg"):
        raise ValueError(f"Unsupported diagram format: {output_format}")

    content_types = {
        "png": "image/png",
        "svg": "image/svg+xml",
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input.mmd"
        output_path = Path(tmpdir) / f"output.{output_format}"

        input_path.write_text(mermaid_src, encoding="utf-8")

        cmd = [
            "mmdc",
            "-i", str(input_path),
            "-o", str(output_path),
            "-b", "transparent",
        ]

        if output_format == "png":
            cmd.extend(["-s", "2"])  # 2x scale for crisp rendering

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"mermaid-cli failed: {result.stderr}")

        return output_path.read_bytes(), content_types[output_format]
