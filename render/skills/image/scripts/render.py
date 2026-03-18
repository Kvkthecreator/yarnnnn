"""Image composition skill — layout spec → PNG/JPG via Pillow."""

import io
from PIL import Image, ImageDraw, ImageFont

# Layout presets: name → (width, height)
_LAYOUTS = {
    "card": (1200, 630),
    "banner": (1200, 300),
    "square": (1080, 1080),
}

# DejaVu Sans is bundled in the Docker image (fonts-dejavu apt package)
_FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color (#RRGGBB) to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load DejaVu Sans font at given size."""
    path = _FONT_BOLD if bold else _FONT_REGULAR
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        # Fallback to default if DejaVu not available (e.g., local dev)
        return ImageFont.load_default()


async def render_image(input_data: dict, output_format: str) -> tuple[bytes, str]:
    """
    Compose an image from layout spec.

    input_data: {
        "layout": "card"|"banner"|"square" (optional),
        "width": int, "height": int (optional, override layout),
        "background": "#hex" (optional),
        "elements": [
            {"type": "text", "content": str, "x": int, "y": int, ...},
            {"type": "rect", "x": int, "y": int, "width": int, "height": int, "color": "#hex"},
        ]
    }
    output_format: "png" or "jpg"
    Returns: (file_bytes, content_type)
    """
    if output_format not in ("png", "jpg"):
        raise ValueError(f"Unsupported image format: {output_format}")

    content_types = {"png": "image/png", "jpg": "image/jpeg"}

    # Canvas dimensions
    layout = input_data.get("layout", "card")
    default_w, default_h = _LAYOUTS.get(layout, (1200, 630))
    width = input_data.get("width", default_w)
    height = input_data.get("height", default_h)

    if width > 4096 or height > 4096:
        raise ValueError("Maximum canvas size is 4096x4096")

    # Create canvas
    bg_color = _hex_to_rgb(input_data.get("background", "#ffffff"))
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Render elements in order
    for elem in input_data.get("elements", []):
        elem_type = elem.get("type")

        if elem_type == "text":
            font = _get_font(elem.get("font_size", 24), elem.get("bold", False))
            color = _hex_to_rgb(elem.get("color", "#000000"))
            draw.text((elem["x"], elem["y"]), elem["content"], fill=color, font=font)

        elif elem_type == "rect":
            color = _hex_to_rgb(elem.get("color", "#000000"))
            x, y = elem["x"], elem["y"]
            draw.rectangle([x, y, x + elem["width"], y + elem["height"]], fill=color)

    # Export
    buf = io.BytesIO()
    if output_format == "jpg":
        img.save(buf, format="JPEG", quality=90)
    else:
        img.save(buf, format="PNG")

    return buf.getvalue(), content_types[output_format]
