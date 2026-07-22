"""Decomposed generation — the AI-native image workflow (ADR-475, ADR-468 D3).

ONE PROMPT DOES NOT GENERATE ONE IMAGE — IT GENERATES A COMPOSITION.

    "a launch ad: headline, hero shot of the product, warm background"
      → background   (a CSS wash — expressible, so never generated)
      → hero-product (a generated cut-out, one rented call, cited as a file)
      → headline     (real text, wearing workspace tokens)
      → subhead      (real text)
      → cta          (real text)

and it lands not as one opaque raster but as five independently-addressable,
positioned, regenerable objects on the attributed substrate.

── WHY THIS SHAPE ───────────────────────────────────────────────────────────
The dividend is the moat's, not the editor's: "change the headline" is a text
edit; "make the background warmer" is a token change; "re-roll the product
shot" replaces ONE leaf's cited asset. The hero survives all three. Every step
is an attributed revision, so `trace` works per object.

Canva's AI is bolted onto a proprietary document. Ours is native because the
document IS the substrate the lane already knows how to edit (ADR-443).

── THE THREE ROUTING RULES (ADR-468 D3 step 2) ──────────────────────────────
A layer's KIND decides how it is produced, and the rules are ordered by cost:

    text        → a real text block. NEVER raster. Generated in-image type is
                  the single most reliable quality failure in image models,
                  and text-as-text is simultaneously the editability win and
                  the brand win (it wears ADR-453 tokens).
    surface     → CSS/SVG where expressible (gradients, washes, solids). A
                  generated raster ONLY where it is not. Free beats rented.
    subject     → a generated CUT-OUT (ADR-468 D4): the subject alone, on a
                  transparent ground, so it COMPOSES. One rented call per
                  raster leaf — never one call for the whole canvas, which is
                  the flat-image failure this whole app refuses.

── THE ENGINE IS RENTED, AND HERE IT IS STUBBED ─────────────────────────────
ADR-417's principle ("generation is rented, not owned") holds: yarnnn hosts no
generation or matting engine. `GenerationBackend` is the driver seam; a vendor
is a config swap, never a code change.

The default driver is `StubBackend` — deterministic, offline, free. This is a
DELIBERATE sequencing choice (ADR-472 D6): decomposed generation must drive
the object model, not be fitted to one designed in the abstract, and a real
vendor's prompt-engineering would contaminate the reading of what the markup
actually needed. The stub produces honest, visibly-placeholder leaves that
compose exactly as real ones will; swapping the driver changes the BYTES at
the leaves and nothing else about the composition.

Canonical reference: docs/adr/ADR-475-decomposed-generation.md
"""

from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod
from typing import Literal, Optional, TypedDict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# The layer plan (ADR-468 D3 step 1) — the object tree IS the plan.
# ---------------------------------------------------------------------------
#
# There is NO separate plan format. The decomposition emits the composition
# directly, because a plan that is not the document is a second source of
# truth about the same thing, and ADR-456 already ruled on that class of
# mistake (markdown is a PROJECTION, never a second source). What follows is
# the in-flight shape of one layer between decomposition and markup — it is
# never persisted, never served, and never round-tripped.

LayerKind = Literal["text", "surface", "subject"]

#: Roles are a VOCABULARY, not an enum the kernel enforces. ADR-472 D6 is
#: explicit that the role set must fall out of real ads rather than precede
#: them, so an unrecognized role composes fine — it is a name on an object,
#: and naming is the point. These six are what the first ad actually needed.
KNOWN_ROLES = ("background", "subject", "headline", "subhead", "cta", "logo")


class Layer(TypedDict, total=False):
    """One object in the composition, before it becomes markup."""
    role: str            # "headline", "hero-product" — the object's NAME
    kind: LayerKind      # how it is produced (the routing rule)
    text: str            # kind="text": the actual copy
    prompt: str          # kind="subject": what to generate
    style: str           # kind="surface": the CSS the wash resolves to
    x: int               # percent of frame — the ADR-461 measures
    y: int
    w: int
    z: int
    tag: str             # kind="text": h1 / h2 / p — the block's element
    ground: str          # "dark" | "light" — the STAGE's ground, not the
                         # layer's; carried here because any layer may be the
                         # one that declares it (ADR-475 §12)


class GeneratedAsset(TypedDict):
    """What a backend returns for one raster leaf."""
    data: bytes
    content_type: str
    model: str           # the engine that made it — rides onto the element
    prompt: str          # the prompt that made it — rides onto the element
    cost_usd: float      # what the rented call cost (0.0 = free driver); the
                         # orchestrator ledgers any non-zero cost per leaf


# ---------------------------------------------------------------------------
# The engine seam (ADR-417 discipline, ADR-427 StorageBackend precedent).
# ---------------------------------------------------------------------------


class GenerationBackend(ABC):
    """Rent one raster leaf.

    Deliberately per-LEAF, not per-canvas: the interface itself refuses the
    flat-image shape. A driver that could only produce whole compositions
    cannot satisfy this contract, which is the point.
    """

    #: The driver's identity, recorded on every element it produces so a leaf
    #: always says which engine made it (ADR-468 D4 provenance).
    name: str = "abstract"

    @abstractmethod
    def generate(
        self,
        *,
        prompt: str,
        width: int,
        height: int,
        cutout: bool = False,
    ) -> GeneratedAsset:
        """Produce ONE raster leaf.

        `cutout=True` asks for the subject ALONE on a transparent ground
        (ADR-468 D4). A driver whose engine cannot isolate a subject is
        expected to chain a rented matting step — the CONTRACT is that subject
        leaves arrive composable; the provider chain is implementation.
        """
        raise NotImplementedError


class StubBackend(GenerationBackend):
    """The offline driver: deterministic, free, and honestly a placeholder.

    It emits a real PNG (a flat-colour tile whose hue is DERIVED FROM the
    prompt, so different subjects are visibly different objects and the same
    prompt is byte-identical across runs — which is what makes the CAS dedup
    property observable in tests).

    It is not pretending to be an image model. A placeholder that LOOKS
    generated would make the first ad's reading dishonest; one that looks like
    a placeholder keeps attention on the composition, which is what this stage
    of the build is for.
    """

    name = "stub"

    def generate(
        self,
        *,
        prompt: str,
        width: int,
        height: int,
        cutout: bool = False,
    ) -> GeneratedAsset:
        digest = hashlib.sha256(prompt.encode("utf-8")).digest()
        rgb = (digest[0], digest[1], digest[2])
        return {
            "data": _solid_png(width, height, rgb),
            "content_type": "image/png",
            "model": f"stub:{'cutout' if cutout else 'raster'}",
            "prompt": prompt,
            "cost_usd": 0.0,
        }


def _solid_png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    """A minimal valid PNG of one colour, written by hand.

    No Pillow, no numpy: this is the stub driver, and pulling an imaging
    dependency into the API for placeholder tiles would be a real cost for a
    temporary need. PNG's spec makes the honest version short — zlib is stdlib
    and the scanline format is one filter byte per row.
    """
    import struct
    import zlib

    w = max(1, min(int(width), 2048))
    h = max(1, min(int(height), 2048))
    row = b"\x00" + bytes(rgb) * w          # filter byte 0 (None) + RGB pixels
    raw = row * h

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))  # 8-bit RGB
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b"")
    )


# ---------------------------------------------------------------------------
# The rented engine (ADR-475 vendor commit — Gemini, direct REST per ADR-076).
# ---------------------------------------------------------------------------


class GeminiBackend(GenerationBackend):
    """The rented driver: Gemini's image-output models over their REST API.

    Direct httpx against `generativelanguage.googleapis.com` (the ADR-076
    pattern — direct API clients, no gateway; no new SDK dependency). One call
    per LEAF, exactly as the seam demands.

    Two disciplines the driver owns:

    - **Aspect, not pixels.** The API takes an aspect-ratio hint, not a pixel
      size; the requested width/height map to the nearest supported ratio and
      the kernel's `data-w`/`data-h` measures do the actual sizing on the
      stage. The rented pixels are a source the composition scales — same as
      any cited image.
    - **The cut-out is prompt-engineered, honestly.** `cutout=True` asks for
      the subject isolated on a plain white ground (asking image models for
      "transparent" famously yields painted checkerboards). True alpha matting
      is a NAMED FOLLOW-ON — a second rented step behind this same contract
      ("subject leaves arrive composable; the provider chain is
      implementation"). Until then a cut-out composes as a clean white-ground
      card, which is honest and visible, never silently wrong.
    """

    name = "gemini"

    #: Supported aspect hints (the model's own vocabulary).
    _RATIOS = (
        ("1:1", 1.0), ("4:3", 4 / 3), ("3:4", 3 / 4), ("16:9", 16 / 9), ("9:16", 9 / 16),
    )

    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        cost_usd: Optional[float] = None,
        timeout: float = 90.0,
    ) -> None:
        import os

        self._api_key = api_key
        self.model = model or os.getenv("IMAGES_GENERATION_MODEL", "gemini-2.5-flash-image")
        # ADR-396 discipline: the ledger records what the call is billed at.
        # Image generation has no token count in our rate table, so the driver
        # carries a per-image figure (list ≈ $0.04; the platform's standard 2×
        # rate → $0.08 default), env-overridable when the vendor reprices.
        self._cost_usd = (
            cost_usd
            if cost_usd is not None
            else float(os.getenv("IMAGES_GENERATION_COST_USD", "0.08"))
        )
        self._timeout = timeout

    def _aspect(self, width: int, height: int) -> str:
        target = (width / height) if height else 1.0
        return min(self._RATIOS, key=lambda r: abs(r[1] - target))[0]

    def generate(
        self,
        *,
        prompt: str,
        width: int,
        height: int,
        cutout: bool = False,
    ) -> GeneratedAsset:
        import base64

        import httpx

        subject = prompt.strip()
        engineered = (
            f"{subject}. The subject alone, fully in frame, isolated on a plain "
            "solid pure-white background. No text, no watermark, no border, "
            "clean studio product-photography lighting."
            if cutout
            else f"{subject}. No text, no watermark."
        )
        body = {
            "contents": [{"parts": [{"text": engineered}]}],
            "generationConfig": {
                "responseModalities": ["IMAGE"],
                "imageConfig": {"aspectRatio": self._aspect(width, height)},
            },
        }
        resp = httpx.post(
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent",
            headers={"x-goog-api-key": self._api_key, "Content-Type": "application/json"},
            json=body,
            timeout=self._timeout,
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"gemini generate {resp.status_code}: {resp.text[:300]}"
            )
        payload = resp.json()
        for cand in payload.get("candidates") or []:
            for part in (cand.get("content") or {}).get("parts") or []:
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    return {
                        "data": base64.b64decode(inline["data"]),
                        "content_type": inline.get("mimeType")
                        or inline.get("mime_type")
                        or "image/png",
                        "model": self.model,
                        "prompt": prompt,
                        "cost_usd": self._cost_usd,
                    }
        # A 200 with no image part (safety block, text-only answer) is a
        # per-leaf failure the orchestrator already handles by skipping.
        raise RuntimeError(
            f"gemini generate returned no image part: {str(payload)[:300]}"
        )


#: The active driver. A module-level singleton the way the storage seam does
#: it — swapping engines is this one binding, plus that driver's key/cost
#: discipline. Nothing else in the workflow knows which engine ran.
#:
#: Resolution is LAZY and env-driven (the vendor commit): with a
#: GEMINI_API_KEY present the rented driver is the default; without one — or
#: with IMAGES_GENERATION_ENGINE=stub forced — the offline stub serves, which
#: is what keeps every gate green with no key and no network.
_BACKEND: Optional[GenerationBackend] = None


def _default_backend() -> GenerationBackend:
    import os

    engine = (os.getenv("IMAGES_GENERATION_ENGINE") or "").strip().lower()
    if engine == "stub":
        return StubBackend()
    key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if key and engine in ("", "gemini"):
        return GeminiBackend(api_key=key)
    if engine and engine != "gemini":
        logger.warning("[IMAGES] unknown IMAGES_GENERATION_ENGINE=%r — using stub", engine)
    return StubBackend()


def get_backend() -> GenerationBackend:
    global _BACKEND
    if _BACKEND is None:
        _BACKEND = _default_backend()
    return _BACKEND


def set_backend(backend: GenerationBackend) -> None:
    """Swap the driver (the vendor wiring point; tests use it too)."""
    global _BACKEND
    _BACKEND = backend


# ---------------------------------------------------------------------------
# Composition — the plan becomes markup (ADR-468 D3 step 4).
# ---------------------------------------------------------------------------
#
# Every layer lands as a block on the staged frame, carrying the SHARED object
# layer's measures (`services/studio.py::STUDIO_MEASURES`, grain
# `block-staged`): data-x/data-y position it, data-w sizes it, data-z stacks
# it, and the `--yx/--yy/--yw/--yz` custom properties carry the values. IMAGES
# invents no geometry vocabulary — it consumes the kernel's, which is exactly
# what ADR-472 D2 bought by making the object layer shared rather than forked.


def _esc(text: str) -> str:
    """Escape for HTML text content + double-quoted attribute values.

    Composition writes member prose and MEMBER-SUPPLIED PROMPTS into markup
    that other principals read; an unescaped quote would break out of an
    attribute and an unescaped angle bracket out of a text node. The substrate
    is a multi-principal commons (ADR-373), so this is a boundary, not a
    nicety.
    """
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _geometry(layer: Layer) -> tuple[str, list[str]]:
    """The block's geometry as (attribute markers, style properties).

    The ATTRIBUTE is the marker a reader/migration/renderer keys on; the
    custom PROPERTY is the value CSS consumes. Writing one without the other
    is the bug the ADR-461 measures are shaped to prevent, so they are emitted
    here together or not at all.

    Returned SPLIT rather than pre-joined so a caller that also has its own
    style to contribute (a surface's CSS wash) folds into ONE style attribute
    instead of emitting a second one that the browser silently drops.
    """
    attrs: list[str] = []
    props: list[str] = []
    # `h` is here for the reason ADR-475 records: a POSITIONED, EMPTY element
    # resolves `height: auto` to ZERO, so a background or a cut-out without it
    # is placed perfectly and renders as nothing.
    for key, var in (("x", "--yx"), ("y", "--yy"), ("w", "--yw"), ("h", "--yh")):
        val = layer.get(key)
        if val is not None:
            attrs.append(f'data-{key}="{int(val)}"')
            props.append(f"{var}:{int(val)}%")
    z = layer.get("z")
    if z is not None:
        attrs.append(f'data-z="{int(z)}"')
        props.append(f"--yz:{int(z)}")
    return (" " + " ".join(attrs) if attrs else ""), props


def _provenance(asset: GeneratedAsset) -> str:
    """The generation facts, on the element (ADR-468 D4).

    A generated leaf says what made it and from what, in the markup itself —
    the `data-ref` pattern's generation sibling. This is what makes per-object
    re-rolling native and attributed: the prompt that made this leaf is ON the
    leaf, so regenerating is reading an attribute, not remembering a session.
    """
    return (
        f' data-gen-prompt="{_esc(asset["prompt"])}"'
        f' data-gen-model="{_esc(asset["model"])}"'
    )


def compose_layers(layers: list[Layer], assets: dict[str, tuple[str, str, GeneratedAsset]]) -> str:
    """The layer plan → the staged frame's inner markup.

    `assets` maps a layer's role to its (path, revision_id, asset) triple for
    raster leaves — cited by path + head revision (ADR-440 D5), never inlined
    as bytes, which is the D2 rule that keeps the document text substrate.
    """
    out: list[str] = []
    for i, layer in enumerate(layers):
        bid = f"g{i + 1}"
        role = _esc(layer.get("role", f"layer-{i + 1}"))
        attrs, props = _geometry(layer)
        kind = layer.get("kind", "text")

        if kind == "text":
            # Real text, always (ADR-468 D2). The block is a `heading` because
            # that is the kernel's text-block kind; the TAG carries the
            # typographic level, and the design system's tokens dress it.
            tag = layer.get("tag", "p")
            style = f' style="{";".join(props)}"' if props else ""
            out.append(
                f'<{tag} data-block="heading" data-block-id="{bid}" '
                f'data-role="{role}"{attrs}{style}>'
                f'{_esc(layer.get("text", ""))}</{tag}>'
            )
        elif kind == "surface":
            # Expressible → CSS, and NO rented call is made. The cheapest
            # correct production wins; a gradient is not an image model's job.
            # The wash folds into the SAME style attribute as the measures —
            # a second style attribute would be silently dropped.
            wash = layer.get("style", "")
            joined = ";".join(props + ([wash] if wash else []))
            style = f' style="{_esc(joined)}"' if joined else ""
            out.append(
                f'<div data-block="figure" data-block-id="{bid}" '
                f'data-role="{role}" data-surface="css"{attrs}{style}></div>'
            )
        else:  # subject — a cited, generated raster leaf
            cited = assets.get(layer.get("role", ""))
            if not cited:
                # A leaf whose generation failed is SKIPPED, not faked: the
                # composition lands one object lighter and honestly, rather
                # than carrying a broken citation the renderer would 404 on.
                logger.warning("[IMAGES] no asset for subject layer %r — skipped", role)
                continue
            path, rev, asset = cited
            style = f' style="{";".join(props)}"' if props else ""
            out.append(
                f'<figure data-block="figure" data-block-id="{bid}" '
                f'data-role="{role}"{attrs}{style}>'
                f'<img data-ref="{_esc(path)}" data-ref-rev="{_esc(rev)}" '
                f'alt="{_esc(layer.get("prompt", role))}"{_provenance(asset)}>'
                f"</figure>"
            )
    return "\n  ".join(out)
