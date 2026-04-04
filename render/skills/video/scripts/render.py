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


def _find_remotion_cli() -> str:
    """Find the remotion CLI binary. Checks multiple locations."""
    import shutil
    import glob

    # 1. Composition-local node_modules
    local_bin = COMPOSITION_DIR / "node_modules" / ".bin" / "remotion"
    if local_bin.exists():
        return str(local_bin)

    # 2. Global npm bin (shutil.which)
    global_bin = shutil.which("remotion")
    if global_bin:
        return global_bin

    # 3. Common global npm paths (Debian/Ubuntu variants)
    for path in [
        "/usr/local/bin/remotion",
        "/usr/local/lib/node_modules/.bin/remotion",
        "/usr/local/lib/node_modules/@remotion/cli/remotion",
        "/usr/lib/node_modules/.bin/remotion",
        "/usr/lib/node_modules/@remotion/cli/remotion",
    ]:
        if Path(path).exists():
            return path

    # 4. Search for remotion binary anywhere in common npm dirs
    for pattern in ["/usr/local/lib/node_modules/**/remotion", "/usr/lib/node_modules/**/remotion"]:
        matches = glob.glob(pattern, recursive=True)
        for m in matches:
            if Path(m).is_file() and "cli" in m.lower():
                return m

    # 5. Try npx as last resort
    npx = shutil.which("npx")
    if npx:
        return f"{npx} remotion"

    # Log diagnostic info for debugging
    import os, glob as g
    comp_dir = str(COMPOSITION_DIR)
    nm_exists = (COMPOSITION_DIR / "node_modules").exists()
    global_remotion = g.glob("/usr/local/lib/node_modules/**/*remotion*", recursive=True)[:10]
    logger.error(
        f"[VIDEO] remotion CLI not found. Diagnostics: "
        f"COMPOSITION_DIR={comp_dir}, exists={COMPOSITION_DIR.exists()}, "
        f"node_modules={nm_exists}, "
        f"which_remotion={shutil.which('remotion')}, "
        f"which_npx={shutil.which('npx')}, "
        f"global_remotion={global_remotion}, "
        f"dir_contents={os.listdir(comp_dir) if COMPOSITION_DIR.exists() else 'DIR_MISSING'}"
    )

    raise FileNotFoundError(
        "remotion CLI not found. Ensure @remotion/cli is installed "
        "(npm install -g @remotion/cli or in composition/package.json)"
    )


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
        # Find remotion CLI — try npx first, fall back to node_modules/.bin, then global
        remotion_bin = _find_remotion_cli()
        cmd = [
            remotion_bin, "render",
            "MainComposition",
            output_path,
            f"--props={props_path}",
            "--codec=h264",
            "--log=verbose",
            "--browser-executable=/usr/bin/chromium",
            "--gl=swangle",
        ]

        logger.info(f"[VIDEO] Rendering {total_duration}s video ({width}x{height}, {len(slides)} slides)")

        # Add node_modules/.bin to PATH for composition-local deps
        env = {**subprocess.os.environ}
        node_bin = str(COMPOSITION_DIR / "node_modules" / ".bin")
        env["PATH"] = f"{node_bin}:{env.get('PATH', '')}"

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 min — first render includes TS bundling
            cwd=str(COMPOSITION_DIR),
            env=env,
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
