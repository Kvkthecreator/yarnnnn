#!/usr/bin/env python3
"""Generate the kernel agent faces (ADR-641 amendment).

WHY A GENERATOR AND NOT ONLY THE PNGs. The faces are yarnnn's own marks: a
tinted disc carrying the agent's Lucide glyph, in the hue of the app it lives
in. Keeping the SOURCE beside the output means a re-icon, a palette change or
a new agent is a re-run rather than a hand-drawn asset nobody can reproduce.
The PNGs ARE committed — they ship with the deploy and nothing at runtime
depends on this script; this file is how they came to be and how to change them.

The path geometry is Lucide's own, copied from the same `lucide-react` build
the Agents page renders, so a face and its roster glyph cannot drift apart.

DEPENDENCIES, deliberately pure-Python: pillow + svgpathtools. The first cut
used cairosvg, which needs a native libcairo the API image does not carry —
an asset regenerated only on machines with a system library is an asset that
silently stops being regenerable. Stroking the paths ourselves keeps this
runnable anywhere the API already runs.

Usage:  python3 api/services/agent_faces/_generate.py
"""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw
from svgpathtools import parse_path

HERE = Path(__file__).resolve().parent

S = 512            # emitted size — retina for the 56px `lg` face
SS = 4             # supersample factor, for clean curves at every render size
W = S * SS
GLYPH_FRAC = 0.54  # glyph box as a fraction of the disc
VIEWBOX = 24.0     # Lucide's coordinate space
STROKE = 1.9       # Lucide stroke-width, in viewBox units

#: slug -> (disc tint, glyph ink). The hue is the APP's own accent
#: (`resolveSurfaceAccent`): Images rose, Slides/Text sky, Blogger emerald.
#: A face is a PICTURE, so per-agent colour is legitimate here — the CLASS hue
#: (violet) stays on the fallback initial, which is a class marker, not a face.
SPECS: dict[str, tuple[str, str]] = {
    "designer": ("#fde8ec", "#e11d48"),
    "editor":   ("#e0f0fc", "#0284c7"),
    "blogger":  ("#dcf6eb", "#059669"),
}

#: Lucide 24x24 geometry, verbatim. `paths` are stroked; `dots` are filled
#: circles (Lucide draws the palette's wells as filled <circle> elements).
GLYPHS: dict[str, dict] = {
    "designer": {
        "paths": [
            "M12 22a1 1 0 0 1 0-20 10 9 0 0 1 10 9 5 5 0 0 1-5 5h-2.25a1.75 "
            "1.75 0 0 0-1.4 2.8l.3.4a1.75 1.75 0 0 1-1.4 2.8z",
        ],
        # Lucide draws these at r=.5 with a fill; at a 24px face that is a
        # sub-pixel speck, so the wells disappear exactly where the palette
        # most needs to read as a palette. Nudged to .9 — still Lucide's
        # positions, legible at every size we render.
        "dots": [(13.5, 6.5, 0.9), (17.5, 10.5, 0.9),
                 (6.5, 12.5, 0.9), (8.5, 7.5, 0.9)],
    },
    "editor": {
        "paths": [
            "M15.707 21.293a1 1 0 0 1-1.414 0l-1.586-1.586a1 1 0 0 1 0-1.414"
            "l5.586-5.586a1 1 0 0 1 1.414 0l1.586 1.586a1 1 0 0 1 0 1.414z",
            "M18 13l-1.375-6.874a1 1 0 0 0-.746-.776L3.235 2.028a1 1 0 0 0"
            "-1.207 1.207L5.35 15.879a1 1 0 0 0 .776.746L13 18",
            "M2.3 2.3l7.286 7.286",
        ],
        "dots": [(11, 11, 2)],   # the nib's eye — stroked, not filled
        "dots_stroked": True,
    },
    "blogger": {
        "paths": [
            "M12.67 19a2 2 0 0 0 1.416-.588l6.154-6.172a6 6 0 0 0-8.49-8.49"
            "L5.586 9.914A2 2 0 0 0 5 11.328V18a1 1 0 0 0 1 1z",
            "M16 8 2 22",
            "M17.5 15H9",
        ],
        "dots": [],
    },
}


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _draw_glyph(d: ImageDraw.ImageDraw, spec: dict, ink, box: int, off: int) -> None:
    """Stroke every path by walking it and drawing round-capped segments.

    Round joins/caps come free: each sample is drawn as a disc of the stroke
    width, which is exactly what `stroke-linecap="round"` means.
    """
    scale = box / VIEWBOX
    r = max(1, int(STROKE * scale / 2))

    def px(z) -> tuple[float, float]:
        return (off + z.real * scale, off + z.imag * scale)

    for dstr in spec["paths"]:
        path = parse_path(dstr)
        for seg in path:
            # Sample density from the segment's own length — short segments
            # need few samples, long curves need many, and neither should be
            # guessed at a fixed number.
            try:
                n = max(2, int(seg.length() * scale / 1.5))
            except Exception:
                n = 24
            pts = [px(seg.point(i / n)) for i in range(n + 1)]
            d.line(pts, fill=ink, width=r * 2, joint="curve")
            for p in (pts[0], pts[-1]):     # round caps
                d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=ink)

    for (cx, cy, cr) in spec.get("dots", []):
        x, y = px(complex(cx, cy))
        rr = cr * scale
        if spec.get("dots_stroked"):
            d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=ink, width=r * 2)
        else:
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=ink)


def main() -> None:
    for slug, (bg, ink_hex) in SPECS.items():
        disc = Image.new("RGB", (W, W), _hex(bg))
        d = ImageDraw.Draw(disc)
        box = int(W * GLYPH_FRAC)
        _draw_glyph(d, GLYPHS[slug], _hex(ink_hex), box, (W - box) // 2)

        mask = Image.new("L", (W, W), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, W - 1, W - 1], fill=255)
        out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        out.paste(disc.resize((S, S), Image.LANCZOS), (0, 0),
                  mask.resize((S, S), Image.LANCZOS))
        out.save(HERE / f"{slug}.png")
        print(f"wrote {slug}.png")


if __name__ == "__main__":
    main()
