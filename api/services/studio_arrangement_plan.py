"""ADR-479 — Re-arrange as planned judgment.

Re-laying a page used to climb a ladder of proxies: a figure seeks a media Area,
else a same-named source Area wins, else everything falls into the first body
Area, else REFUSE. Each rung stands in for a question none of them asks — *given
this content and this target layout, where does each piece belong?*

So the placement decision becomes a judgment and the write stays mechanism. The
model reads the page's blocks and the target arrangement's DECLARED Areas (both
already kernel data) and returns a PLAN — an Area per block, never markup:

    {"placements": [{"block_id": "h1", "area": "heading"}, ...]}

ADR-544 D6 — the vocabulary is AREAS (roles: heading|body|media|aside). This
module taught the model a `flow` role the substrate no longer has, so the
judgment reasoned in one vocabulary while the document spoke another. The
promise it exists to keep — every block accounted for, exactly once — is
unchanged; only the words are.

The plan is then validated against the closed vocabulary (§D2) and applied
mechanically by the FE. Non-determinism is quarantined in a proposal that must
pass a total-coverage check before it can touch substrate; the same plan always
produces the same HTML.

The fallback is the pre-existing mechanical ladder on the FE — per ADR-468 D4 a
composition must never dead-end, so a refusal, a cold router, or an exhausted
balance still re-lays the page (degraded, never dead).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

#: The judgment's whole job, stated once. It plans PLACEMENT — it never writes
#: markup, never invents content, never renames an Area. The closed vocabulary is
#: handed to it per call (the arrangements are kernel data, ADR-224), so a new
#: arrangement is a registry row and this prompt never changes.
#:
#: ADR-544 D6 — the vocabulary here is AREAS, not slots, and the roles are the
#: closed set heading|body|media|aside. Pre-544 this prompt taught a `flow` role
#: that the substrate no longer has, so the model was reasoning in one vocabulary
#: while the document spoke another — the same one-layer-above fault the
#: containment law closed at the surface, left open at the AI seam.
_PLAN_SYSTEM = """You place existing content blocks into a layout's named Areas.

The structure is four grains: SLIDE (or band) → LAYOUT → AREA → BLOCK. Every
block lives in exactly one Area; your whole job is to say WHICH.

You are given:
  • BLOCKS — the blocks currently on a page: an id, a kind (heading, paragraph,
    figure, gallery, stat, quote, list, table…), and a short text excerpt.
  • AREAS — the Areas the target layout declares: a name, a role, and sometimes
    a place. The role is the Area's identity:
      'heading' anchors the page title
      'body'    takes prose and everything else
      'media'   takes figures and galleries
      'aside'   takes supporting matter beside the body (a caption, a note)
    'place' (left/center/right) tells same-role Areas apart.

Return ONLY a JSON object, no prose, no code fence:

  {"placements": [{"block_id": "<id>", "area": "<area name>"}, ...]}

Rules:
  • EVERY block id you were given must appear EXACTLY ONCE. Never drop a block,
    never invent an id, never repeat one. Content is never lost in a re-layout.
  • Use only Area names from AREAS. Never invent an Area.
  • A figure or gallery belongs in a 'media' Area when one exists.
  • A heading block belongs in a 'heading' Area when one exists.
  • Otherwise judge by MEANING, which is the reason you are here rather than a
    name match: put content where a reader would expect it. In a two-column or
    comparison layout, split the material so the columns balance and so related
    blocks stay together — a stat with the sentence that frames it, a figure with
    its caption. Respect the source's intent when it is legible (content that sat
    side-by-side usually still belongs side-by-side), but prefer the placement
    that reads best in the TARGET layout.
"""


def build_plan_request(blocks: list[dict], areas: list[dict]) -> str:
    """The user message: the page's blocks and the target's declared Areas."""
    def _block_line(b: dict) -> str:
        text = (b.get("text") or "").replace("\n", " ").strip()
        if len(text) > 160:
            text = text[:157] + "…"
        return f'  - id={b.get("id")} kind={b.get("kind") or "content"} text="{text}"'

    def _area_line(s: dict) -> str:
        # ADR-544 D2 — `body` is the default role, not `flow` (which the role set
        # no longer contains). `place` rides along so the model can tell
        # same-role Areas apart, which is the one job the authored name has.
        line = f'  - name={s.get("name")} role={s.get("role") or "body"}'
        place = s.get("place")
        return f"{line} place={place}" if place else line

    return (
        "BLOCKS:\n"
        + ("\n".join(_block_line(b) for b in blocks) or "  (none)")
        + "\n\nAREAS:\n"
        + ("\n".join(_area_line(s) for s in areas) or "  (none)")
    )


def validate_plan(
    placements: list[dict],
    blocks: list[dict],
    areas: list[dict],
) -> Optional[list[dict]]:
    """ADR-479 D2 — reject, never render.

    A plan is admissible only if it names real Areas, names real blocks, and
    accounts for EVERY block exactly once (total coverage). That last clause is
    what retires the content-destruction class: ADR-462 D9's invariant hardens
    from "refuse when unmappable" to "account for every block, always".

    ADR-544 D6 — the model now answers with `area`. `slot` is still READ off an
    inbound placement (a model mid-rollout, a cached completion), but the
    normalized output speaks one key so the FE has one thing to apply. The
    coverage invariant is untouched: this ADR changed the vocabulary, never the
    promise that content survives a re-layout.

    Returns the normalized placements, or None when the plan is inadmissible
    (the caller falls back to the mechanical ladder).
    """
    area_names = {str(s.get("name")) for s in areas if s.get("name")}
    block_ids = [str(b.get("id")) for b in blocks if b.get("id")]
    if not block_ids:
        return []  # nothing to carry — a vacuously valid plan
    if not area_names:
        return None  # a layout with nowhere to put content cannot receive it

    seen: set[str] = set()
    out: list[dict] = []
    for p in placements or []:
        if not isinstance(p, dict):
            return None
        bid = str(p.get("block_id") or "")
        area = str(p.get("area") or p.get("slot") or "")
        if bid not in block_ids:
            return None  # invented or stale block id
        if area not in area_names:
            return None  # invented Area
        if bid in seen:
            return None  # a block placed twice
        seen.add(bid)
        out.append({"block_id": bid, "area": area})

    if seen != set(block_ids):
        return None  # a block went unplaced — the destruction bug's signature
    return out


async def plan_arrangement(
    blocks: list[dict],
    areas: list[dict],
) -> tuple[Optional[list[dict]], Optional[object]]:
    """Plan a placement per block, or None to fall back to the mechanism.

    Returns `(placements, completion)`. `placements is None` means "the FE
    should use its mechanical ladder" — a refusal, not an error. `completion` is
    the RoutedCompletion when a call was actually made, so the CALLER meters it
    exactly once: `route_completion` reports usage but never ledgers (ADR-396 —
    one meter, one ledger; a second recording here would double-charge).
    """
    if not blocks:
        return [], None
    if not areas:
        return None, None

    # OUTSIDE the try, deliberately (the ADR-475 lesson) — and so is the LOOKUP
    # below. Inside it, a symbol or a slug that no longer resolves is swallowed
    # by the fallback and looks exactly like "the router is off": the planner
    # silently never plans again. Not hypothetical — ADR-599 moved `designer`
    # between registers while this line subscripted a register by name, and
    # Slides arranged mechanically in production until ADR-600 found it. A
    # missing being is a BUG THAT RAISES; only the CALL may fail soft.
    from services.agents_registry import resolve_agent
    from services.model_router import model_router_enabled, route_completion

    # ADR-600 D4 — resolve the BEING, never a container.
    engine = resolve_agent("designer")["model"]

    completion = None
    try:
        if not model_router_enabled():
            logger.info("[STUDIO] router off — mechanical arrangement")
            return None, None

        # Slides' resident is EDITOR since ADR-602 D1; this planner still
        # resolves `designer` deliberately — arrangement planning is MACHINERY
        # that happens to plan layout, not the desk's voice (ADR-602 D2).
        # The `model` PARAMETER is removed
        # (2026-08-21): no caller passed it, and it was the same
        # caller-supplied-engine door `routes/images.py` closed on
        # `ComposeRequest.model` — reaching `route_completion` without the
        # LANE_MODELS membership check or the ADR-439 §4 billing gate.
        completion = await route_completion(
            engine,
            [{"role": "user", "content": build_plan_request(blocks, areas)}],
            system=_PLAN_SYSTEM,
            max_tokens=1500,
            timeout=30.0,
        )
        text = (completion.text or "").strip()
        # Models fence JSON despite instructions; take the outermost object.
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            logger.warning("[STUDIO] arrangement plan had no JSON — mechanical")
            return None, completion
        raw = json.loads(match.group(0))
        placements = validate_plan(raw.get("placements") or [], blocks, areas)
        if placements is None:
            logger.warning("[STUDIO] arrangement plan failed validation — mechanical")
            return None, completion
        return placements, completion
    except Exception as exc:  # noqa: BLE001 — any failure falls back, by design
        logger.warning("[STUDIO] arrangement plan failed (%s) — mechanical", exc)
        # A call that happened still costs, even if its output was unusable —
        # the caller meters `completion` regardless of the plan's fate.
        return None, completion
