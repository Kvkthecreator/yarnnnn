"""
Video render skill — short-form video generation via Remotion.

Produces MP4 clips (15-30s max) from structured scene specifications.
Calls `npx remotion render` via subprocess with a JSON props file.

Constraints:
- Max 30 seconds duration
- Max 5 scenes
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
MAX_SCENES = 8
FPS = 30

# Remotion composition project directory
COMPOSITION_DIR = Path(__file__).parent.parent / "composition"


async def render_video(input_spec: dict, output_format: str) -> tuple[bytes, str]:
    """Render a short-form video from scene specifications.

    Args:
        input_spec: Scene-based video specification (see SKILL.md)
        output_format: Must be "mp4"

    Returns:
        (file_bytes, content_type) tuple

    Raises:
        ValueError: If input is invalid or exceeds constraints
    """
    if output_format != "mp4":
        raise ValueError(f"Video only supports mp4 output, got: {output_format}")

    # Validate constraints
    duration = input_spec.get("duration_seconds", 15)
    if duration > MAX_DURATION_SECONDS:
        raise ValueError(f"Video duration {duration}s exceeds maximum of {MAX_DURATION_SECONDS}s")

    scenes = input_spec.get("scenes", [])
    if not scenes:
        raise ValueError("Video requires at least 1 scene")
    if len(scenes) > MAX_SCENES:
        raise ValueError(f"Video has {len(scenes)} scenes, maximum is {MAX_SCENES}")

    # Validate total scene duration matches
    total_scene_duration = sum(s.get("duration", 3) for s in scenes)
    if total_scene_duration > MAX_DURATION_SECONDS:
        raise ValueError(
            f"Total scene duration ({total_scene_duration}s) exceeds "
            f"maximum of {MAX_DURATION_SECONDS}s"
        )

    orientation = input_spec.get("orientation", "landscape")
    width = 1920 if orientation == "landscape" else 1080
    height = 1080 if orientation == "landscape" else 1920

    total_frames = total_scene_duration * FPS

    # Write props to temp file for Remotion
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as props_file:
        json.dump({
            "title": input_spec.get("title", "Video"),
            "scenes": scenes,
            "width": width,
            "height": height,
            "fps": FPS,
        }, props_file)
        props_path = props_file.name

    # Output temp file
    with tempfile.NamedTemporaryFile(
        suffix=".mp4", delete=False
    ) as out_file:
        output_path = out_file.name

    try:
        # Call Remotion CLI
        cmd = [
            "npx", "remotion", "render",
            str(COMPOSITION_DIR / "src" / "index.ts"),
            "MainComposition",
            output_path,
            f"--props={props_path}",
            f"--width={width}",
            f"--height={height}",
            f"--fps={FPS}",
            f"--frames={total_frames}",
            "--codec=h264",
            "--log=error",
        ]

        logger.info(f"[VIDEO] Rendering {total_scene_duration}s video ({width}x{height})")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,  # 3 min timeout for rendering
            cwd=str(COMPOSITION_DIR),
        )

        if result.returncode != 0:
            error_msg = result.stderr[:500] if result.stderr else "Unknown error"
            raise RuntimeError(f"Remotion render failed: {error_msg}")

        # Read output file
        output_bytes = Path(output_path).read_bytes()
        if not output_bytes:
            raise RuntimeError("Remotion produced empty output")

        logger.info(f"[VIDEO] Rendered {len(output_bytes)} bytes")
        return output_bytes, "video/mp4"

    finally:
        # Cleanup temp files
        Path(props_path).unlink(missing_ok=True)
        Path(output_path).unlink(missing_ok=True)
