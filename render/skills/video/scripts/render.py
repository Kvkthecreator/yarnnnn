"""
Video render skill — short-form video generation via Remotion.

ADR-157: Agnostic slide-based composition. Slides contain positioned
elements with layout modes and transitions. Agent decides content;
Remotion handles timing, animation, and rendering.

Constraints:
- Max 30 seconds duration
- Max 8 slides
- Silent (no audio)
- 1080p resolution (landscape or portrait)
"""

import json
import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_DURATION_SECONDS = 30
MAX_SLIDES = 8
FPS = 30

# Remotion composition project directory
COMPOSITION_DIR = Path(__file__).parent.parent / "composition"


async def render_video(input_spec: dict, output_format: str) -> tuple[bytes, str]:
    """Render a short-form video from slide-based specifications.

    input_spec: {
        "title": str,
        "orientation": "landscape" | "portrait",
        "theme": {"background": str, "foreground": str, "accent": str, "muted": str},
        "slides": [
            {
                "layout": "center" | "stack" | "split",
                "duration": int (seconds),
                "transition": "fade" | "slide-left" | "slide-up" | "cut",
                "elements": [
                    {"type": "heading", "text": str, "size": str},
                    {"type": "text", "text": str, "size": str, "color": str},
                    {"type": "value", "text": str, "size": str},
                    {"type": "badge", "text": str, "color": str},
                    {"type": "list", "items": [str]},
                    {"type": "divider"},
                    {"type": "spacer", "height": int},
                ]
            }
        ]
    }
    output_format: Must be "mp4"
    Returns: (file_bytes, content_type)
    """
    if output_format != "mp4":
        raise ValueError(f"Video only supports mp4 output, got: {output_format}")

    # Validate slides
    slides = input_spec.get("slides", [])
    if not slides:
        raise ValueError("Video requires at least 1 slide")
    if len(slides) > MAX_SLIDES:
        raise ValueError(f"Video has {len(slides)} slides, maximum is {MAX_SLIDES}")

    # Validate total duration
    total_duration = sum(s.get("duration", 4) for s in slides)
    if total_duration > MAX_DURATION_SECONDS:
        raise ValueError(
            f"Total duration ({total_duration}s) exceeds maximum of {MAX_DURATION_SECONDS}s"
        )

    orientation = input_spec.get("orientation", "landscape")
    width = 1920 if orientation == "landscape" else 1080
    height = 1080 if orientation == "landscape" else 1920

    total_frames = total_duration * FPS

    # Theme defaults
    theme = input_spec.get("theme", {})
    default_theme = {
        "background": "#0f172a",
        "foreground": "#ffffff",
        "accent": "#3b82f6",
        "muted": "#94a3b8",
    }
    merged_theme = {**default_theme, **theme}

    # Build props for Remotion
    props = {
        "title": input_spec.get("title", "Video"),
        "slides": slides,
        "theme": merged_theme,
        "width": width,
        "height": height,
        "fps": FPS,
    }

    # Write props to temp file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as props_file:
        json.dump(props, props_file)
        props_path = props_file.name

    # Output temp file
    with tempfile.NamedTemporaryFile(
        suffix=".mp4", delete=False
    ) as out_file:
        output_path = out_file.name

    try:
        # Use shell=True to inherit full PATH (npx installed globally via npm)
        cmd = (
            f"npx remotion render MainComposition {output_path}"
            f" --props={props_path}"
            f" --codec=h264"
            f" --log=error"
        )

        logger.info(f"[VIDEO] Rendering {total_duration}s video ({width}x{height}, {len(slides)} slides)")

        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(COMPOSITION_DIR),
        )

        if result.returncode != 0:
            error_msg = result.stderr[:500] if result.stderr else "Unknown error"
            logger.error(f"[VIDEO] Remotion stderr: {result.stderr[:1000]}")
            raise RuntimeError(f"Remotion render failed: {error_msg}")

        output_bytes = Path(output_path).read_bytes()
        if not output_bytes:
            raise RuntimeError("Remotion produced empty output")

        logger.info(f"[VIDEO] Rendered {len(output_bytes)} bytes ({total_duration}s, {len(slides)} slides)")
        return output_bytes, "video/mp4"

    finally:
        Path(props_path).unlink(missing_ok=True)
        Path(output_path).unlink(missing_ok=True)
