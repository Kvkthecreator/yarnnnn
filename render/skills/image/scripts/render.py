"""
Image generation skill — prompt → PNG/JPG via Google Gemini.

ADR-157: Replaces Pillow text+rectangles card generator.
Uses gemini-2.5-flash-image for AI image generation (500 free/day).

Style presets ensure professional business output quality.
"""

import base64
import io
import os
import logging

logger = logging.getLogger(__name__)

# Gemini model for image generation
MODEL = "gemini-2.5-flash-preview-image-generation"

# Style presets — injected as prompt suffixes for consistent quality
STYLE_PRESETS = {
    "professional": "clean professional style, corporate aesthetic, minimal, high quality",
    "minimal": "minimalist design, clean lines, generous whitespace, modern",
    "technical": "technical diagram style, clear labels, structured layout, precise",
    "editorial": "editorial illustration, magazine quality, sophisticated composition",
    "abstract": "abstract visualization, geometric shapes, modern art style",
}

# Supported aspect ratios
VALID_ASPECT_RATIOS = {
    "1:1", "3:2", "2:3", "4:3", "3:4", "16:9", "9:16", "4:5", "5:4",
}

MAX_PROMPT_LENGTH = 2000


async def render_image(input_data: dict, output_format: str) -> tuple[bytes, str]:
    """Generate an image from a text prompt via Gemini.

    input_data: {
        "prompt": str,           # Required: what to generate
        "aspect_ratio": str,     # Optional: "1:1", "16:9", etc. Default: "1:1"
        "style": str,            # Optional: preset name or custom style text
        "size": str,             # Optional: "512", "1K", "2K". Default: "1K"
    }
    output_format: "png" or "jpg"
    Returns: (file_bytes, content_type)
    """
    from google import genai
    from google.genai import types

    if output_format not in ("png", "jpg"):
        raise ValueError(f"Unsupported format: {output_format}. Use 'png' or 'jpg'.")

    prompt = input_data.get("prompt", "")
    if not prompt:
        raise ValueError("prompt is required")
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise ValueError(f"Prompt too long: {len(prompt)} chars (max {MAX_PROMPT_LENGTH})")

    aspect_ratio = input_data.get("aspect_ratio", "1:1")
    if aspect_ratio not in VALID_ASPECT_RATIOS:
        aspect_ratio = "1:1"

    style = input_data.get("style", "professional")

    # Inject style preset into prompt
    if style in STYLE_PRESETS:
        prompt = f"{prompt}. Style: {STYLE_PRESETS[style]}"
    elif style and style != "none":
        # Custom style text
        prompt = f"{prompt}. Style: {style}"

    mime_type = "image/png" if output_format == "png" else "image/jpeg"

    # Call Gemini
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not configured on render service")

    client = genai.Client(api_key=api_key)

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )
    except Exception as e:
        error_msg = str(e)
        if "SAFETY" in error_msg.upper() or "BLOCKED" in error_msg.upper():
            raise ValueError(f"Image generation blocked by safety filter. Try rephrasing: {error_msg}")
        raise ValueError(f"Gemini image generation failed: {error_msg}")

    # Extract image from response
    if not response.candidates:
        raise ValueError("No image generated — empty response from Gemini")

    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.data:
            image_bytes = part.inline_data.data
            if isinstance(image_bytes, str):
                image_bytes = base64.b64decode(image_bytes)
            return image_bytes, mime_type

    raise ValueError("No image data in Gemini response — model may have returned text only")
