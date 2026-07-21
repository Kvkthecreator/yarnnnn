"""Decomposition — a prompt becomes a NAMED LAYER PLAN (ADR-475, ADR-468 D3 §1).

This is step 1 of the workflow and the one that carries the thesis: the member
writes one sentence, and what comes back is not an image but a **composition**
— an explicit, legible, member-visible set of named objects.

    "a launch ad for our serum: headline, hero shot, warm background"
      → [background · hero-product · headline · subhead · cta]

The plan is "legible, member-visible work, not hidden orchestration" (D3), and
the way this codebase keeps that promise is structural: **the object tree IS
the plan.** There is no plan format, no intermediate document, nothing to keep
in sync — decomposition returns layers, `compose_layers` turns them into the
markup, and the markup is the only artifact. ADR-456 already ruled on the
alternative (a projection must never become a second source).

── TWO PATHS TO A PLAN, ONE SHAPE OUT ───────────────────────────────────────
`plan_layers` is JUDGMENT: the resident (Designer, ADR-468 D5) reads the brief
and decides what objects a good ad has. That is a real design act and belongs
to an agent, not to a rule table.

`heuristic_plan` is MECHANISM: a deterministic decomposition that runs with no
model, no key, and no network. It exists for three honest reasons —

  1. the endpoint must work when the router is off or the call fails, and a
     composition one layer lighter beats a 500 (ADR-468 D4's "fallback is
     never a dead end");
  2. the gate must assert composition shape without a billable call;
  3. this build stage deliberately reads what the MARKUP needed, and a
     deterministic plan keeps that reading uncontaminated (ADR-472 D6).

Both return the same `list[Layer]`, so everything downstream is blind to which
ran. That is what makes the model swap a one-line change later.

Canonical reference: docs/adr/ADR-475-decomposed-generation.md
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from services.images.generate import Layer

logger = logging.getLogger(__name__)


#: The layout the heuristic composes: a poster's classic reading order, top to
#: bottom, with the subject occupying the lower two-thirds. These numbers are
#: NOT a design system — they are one honest arrangement that produces a
#: readable ad, and ADR-472 D6 is explicit that the vocabulary of composition
#: must fall out of real work rather than be legislated up front.
#:
#: ⚠️ NON-TEXT LAYERS CARRY `h` (ADR-475, found by the first ad). The kernel's
#: measure rule is `height: var(--yh, auto)` — and `auto` on an ABSOLUTELY
#: POSITIONED, EMPTY element is ZERO. A background div and a cut-out figure
#: have no text to give them intrinsic height, so without `h` they render at
#: 0px: the first composed ad came out as floating text on a blank stage, with
#: every layer correctly placed and two of them invisible.
#:
#: This is a property of leaving the flow, not a kernel defect — a block IN
#: flow gets its height from content, and these have none. Text layers still
#: omit `h` deliberately: their content IS their height, and pinning it would
#: clip a headline that wraps to two lines.
_HEURISTIC_GEOMETRY = {
    "background": {"x": 0, "y": 0, "w": 100, "h": 100, "z": 0},
    "headline":   {"x": 8, "y": 10, "w": 84, "z": 3},
    "subhead":    {"x": 8, "y": 26, "w": 70, "z": 3},
    "subject":    {"x": 20, "y": 36, "w": 60, "h": 58, "z": 1},
    "cta":        {"x": 8, "y": 84, "w": 60, "z": 3},
}


def heuristic_plan(brief: str) -> list[Layer]:
    """A deterministic five-object composition from a one-line brief.

    The decomposition rule is the ADR-468 D3 routing table applied literally:
    a surface (CSS — free), a subject (one rented call), and real text. The
    copy is LIFTED from the brief rather than invented — a mechanical
    decomposition has no business writing marketing prose, and a headline that
    honestly echoes the member's own words is better than a plausible-sounding
    one they did not ask for.
    """
    text = (brief or "").strip()
    # The first clause before a colon/dash is the member's subject; the rest is
    # their instruction list. "a launch ad for our serum: headline, hero shot"
    # → subject "a launch ad for our serum".
    head = re.split(r"[:—–-]", text, maxsplit=1)[0].strip() or "Untitled"
    headline = head[:1].upper() + head[1:] if head else "Untitled"

    return [
        {
            "role": "background",
            "kind": "surface",
            # A wash is expressible, so it is CSS and costs nothing. This is
            # the routing rule earning its keep on the very first layer.
            "style": (
                "background:linear-gradient(160deg,"
                "var(--accent,#e8d5c4),var(--page-bg,#fffdf9))"
            ),
            **_HEURISTIC_GEOMETRY["background"],
        },
        {
            "role": "subject",
            "kind": "subject",
            "prompt": f"{head}, isolated on a transparent background, product photography",
            **_HEURISTIC_GEOMETRY["subject"],
        },
        {
            "role": "headline",
            "kind": "text",
            "tag": "h1",
            "text": headline,
            **_HEURISTIC_GEOMETRY["headline"],
        },
        {
            "role": "subhead",
            "kind": "text",
            "tag": "p",
            "text": text if text and text != head else "",
            **_HEURISTIC_GEOMETRY["subhead"],
        },
        {
            "role": "cta",
            "kind": "text",
            "tag": "p",
            "text": "Learn more",
            **_HEURISTIC_GEOMETRY["cta"],
        },
    ]


#: What the resident is asked for. It describes the ROUTING RULES rather than a
#: schema of roles, because the roles are the design decision being delegated —
#: prescribing them would turn a judgment act back into a rule table.
_PLAN_SYSTEM = """You are Designer, composing an image as LAYERED OBJECTS.

Return ONLY a JSON array of layer objects. No prose, no code fence.

Each layer: {"role", "kind", ...} where kind is exactly one of:
  "text"    — real text. ALWAYS use this for any words in the image; never ask
              for text inside a generated picture. Add "text" (the copy) and
              "tag" ("h1" | "h2" | "p").
  "surface" — a background/wash/shape expressible in CSS. Add "style" (a CSS
              declaration string, e.g. "background:linear-gradient(...)").
              Prefer this over generating a picture whenever it can be said in
              CSS — it is free, editable, and wears the workspace's tokens.
  "subject" — a photographic/illustrated SUBJECT that must be generated. Add
              "prompt" describing the subject ALONE on a transparent
              background, so it composes over the surface.

Geometry on every layer, as percentages of the frame:
  "x","y" (top-left, 0-95), "w" (width, 10-100), "z" (stacking, 0-20;
  higher is in front — put the background at 0).
  "h" (height, 10-100) — REQUIRED on "surface" and "subject" layers, which
  have no text to give them height and render as nothing without it. A
  full-bleed background is x:0 y:0 w:100 h:100. Omit "h" on text layers: the
  copy's own height is correct, and pinning it clips a headline that wraps.

Compose like a poster: one visual statement, generous margins, a clear
reading order. Use as many or as few layers as the brief actually needs."""


def _coerce(raw: list) -> list[Layer]:
    """Validate + clamp a model-authored plan into the Layer shape.

    A model's JSON is UNTRUSTED INPUT: it reaches markup, and markup reaches
    other principals. Every field is checked and every number clamped to the
    kernel's own measure bounds (`STUDIO_MEASURES`), so a hallucinated
    `"x": 4000` degrades to a placed object rather than one off the stage.
    """
    out: list[Layer] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        kind = item.get("kind")
        if kind not in ("text", "surface", "subject"):
            continue
        layer: Layer = {
            "role": str(item.get("role") or f"layer-{len(out) + 1}")[:64],
            "kind": kind,
        }
        if kind == "text":
            layer["text"] = str(item.get("text") or "")[:2000]
            tag = str(item.get("tag") or "p")
            layer["tag"] = tag if tag in ("h1", "h2", "h3", "p") else "p"
        elif kind == "surface":
            layer["style"] = str(item.get("style") or "")[:500]
        else:
            prompt = str(item.get("prompt") or "").strip()
            if not prompt:
                continue  # a subject with no prompt is not a renderable leaf
            layer["prompt"] = prompt[:1000]

        for key, lo, hi in (
            ("x", 0, 95), ("y", 0, 95), ("w", 10, 100), ("h", 10, 100), ("z", 0, 20)
        ):
            val = item.get(key)
            if isinstance(val, (int, float)):
                layer[key] = max(lo, min(hi, int(val)))

        # The zero-height guarantee (ADR-475). The system prompt asks for `h`
        # on non-text layers; this MAKES IT TRUE, because a prompt instruction
        # is a request and a composition that silently renders nothing is the
        # worst failure this app has — it looks like it worked.
        #
        # The fallback is the layer's own width, which for a subject preserves
        # the square-ish box a cut-out usually wants, and for a surface is
        # overridden to full-bleed (a wash that covers less than the stage it
        # backs is nearly always a planning slip, not an intent).
        if kind in ("surface", "subject") and "h" not in layer:
            layer["h"] = 100 if kind == "surface" else int(layer.get("w") or 60)
        out.append(layer)
    return out


async def plan_layers(brief: str, *, model: Optional[str] = None) -> list[Layer]:
    """The resident's layer plan, falling back to the heuristic.

    The fallback is not a degraded mode to apologize for — per ADR-468 D4 a
    composition must never dead-end, so every failure path here lands a real,
    editable, one-layer-lighter composition instead of an error.
    """
    # OUTSIDE the try, deliberately. Inside it, a typo'd symbol (this line said
    # `AGENTS` for one revision) would be swallowed by the fallback and look
    # exactly like "the router is off" — the resident would never plan again
    # and nothing would say so. A broken import is a bug, not a fallback
    # condition; only the CALL is allowed to fail soft.
    from services.agents_registry import KERNEL_AGENTS
    from services.model_router import model_router_enabled, route_completion

    try:
        if not model_router_enabled():
            logger.info("[IMAGES] router off — heuristic plan")
            return heuristic_plan(brief)

        engine = model or KERNEL_AGENTS["designer"]["model"]
        completion = await route_completion(
            engine,
            [{"role": "user", "content": f"Compose this image:\n\n{brief}"}],
            system=_PLAN_SYSTEM,
            max_tokens=2048,
            timeout=45.0,
        )
        text = (completion.text or "").strip()
        # Models fence JSON despite instructions; take the outermost array.
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            logger.warning("[IMAGES] plan had no JSON array — heuristic")
            return heuristic_plan(brief)
        layers = _coerce(json.loads(match.group(0)))
        if not layers:
            logger.warning("[IMAGES] plan coerced to zero layers — heuristic")
            return heuristic_plan(brief)
        return layers
    except Exception as exc:  # noqa: BLE001 — any failure falls back, by design
        logger.warning("[IMAGES] plan failed (%s) — heuristic", exc)
        return heuristic_plan(brief)
