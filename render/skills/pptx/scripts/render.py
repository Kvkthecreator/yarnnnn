"""PPTX skill — slide spec → PPTX via python-pptx."""

import io
from pptx import Presentation
from pptx.util import Inches, Pt


async def render_pptx(input_data: dict, output_format: str) -> tuple[bytes, str]:
    """
    Render a slide spec to PPTX.

    input_data: {
        "title": str,
        "subtitle": str (optional),
        "slides": [
            {"title": str, "content": str, "layout": "content" (optional)},
            ...
        ]
    }
    output_format: "pptx"
    Returns: (file_bytes, content_type)
    """
    if output_format != "pptx":
        raise ValueError(f"Unsupported presentation format: {output_format}")

    title = input_data.get("title", "Presentation")
    slides = input_data.get("slides", [])

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # Title slide
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = title
    if slide.placeholders[1]:
        slide.placeholders[1].text = input_data.get("subtitle", "")

    # Content slides
    for slide_data in slides:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = slide_data.get("title", "")

        content = slide_data.get("content", "")
        body = slide.placeholders[1]
        tf = body.text_frame
        tf.clear()

        for i, line in enumerate(content.split("\n")):
            if i == 0:
                tf.text = line.strip()
            else:
                p = tf.add_paragraph()
                p.text = line.strip()
                p.font.size = Pt(18)

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue(), "application/vnd.openxmlformats-officedocument.presentationml.presentation"
