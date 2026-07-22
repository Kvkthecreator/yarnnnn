"""ADR-479 — Re-arrange as planned judgment.

Re-laying a page used to climb a ladder of proxies: a figure seeks a media slot,
else a same-named source slot wins, else everything falls into the first flow
slot, else REFUSE. Each rung stands in for a question none of them asks — *given
this content and this target layout, where does each piece belong?*

So the placement decision becomes a judgment and the write stays mechanism. The
model reads the page's blocks and the target arrangement's DECLARED slots (both
already kernel data) and returns a PLAN — a slot per block, never markup:

    {"placements": [{"block_id": "h1", "slot": "heading"}, ...]}

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
#: markup, never invents content, never renames a slot. The closed vocabulary is
#: handed to it per call (the arrangements are kernel data, ADR-224), so a new
#: arrangement is a registry row and this prompt never changes.
_PLAN_SYSTEM = """You place existing content blocks into a layout's named slots.

You are given:
  • BLOCKS — the blocks currently on a page: an id, a kind (heading, paragraph,
    figure, gallery, stat, quote, list, table…), and a short text excerpt.
  • SLOTS — the slots the target layout declares: a name and a role
    ('heading' anchors the title, 'media' takes figures/galleries, 'flow' takes
    prose and everything else).

Return ONLY a JSON object, no prose, no code fence:

  {"placements": [{"block_id": "<id>", "slot": "<slot name>"}, ...]}

Rules:
  • EVERY block id you were given must appear EXACTLY ONCE. Never drop a block,
    never invent an id, never repeat one. Content is never lost in a re-layout.
  • Use only slot names from SLOTS. Never invent a slot.
  • A figure or gallery belongs in a 'media' slot when one exists.
  • A heading block belongs in a 'heading' slot when one exists.
  • Otherwise judge by MEANING, which is the reason you are here rather than a
    name match: put content where a reader would expect it. In a two-column or
    comparison layout, split the material so the columns balance and so related
    blocks stay together — a stat with the sentence that frames it, a figure with
    its caption. Respect the source's intent when it is legible (content that sat
    side-by-side usually still belongs side-by-side), but prefer the placement
    that reads best in the TARGET layout.
"""


def build_plan_request(blocks: list[dict], slots: list[dict]) -> str:
    """The user message: the page's blocks and the target's declared slots."""
    def _block_line(b: dict) -> str:
        text = (b.get("text") or "").replace("\n", " ").strip()
        if len(text) > 160:
            text = text[:157] + "…"
        return f'  - id={b.get("id")} kind={b.get("kind") or "content"} text="{text}"'

    def _slot_line(s: dict) -> str:
        return f'  - name={s.get("name")} role={s.get("role") or "flow"}'

    return (
        "BLOCKS:\n"
        + ("\n".join(_block_line(b) for b in blocks) or "  (none)")
        + "\n\nSLOTS:\n"
        + ("\n".join(_slot_line(s) for s in slots) or "  (none)")
    )


def validate_plan(
    placements: list[dict],
    blocks: list[dict],
    slots: list[dict],
) -> Optional[list[dict]]:
    """ADR-479 D2 — reject, never render.

    A plan is admissible only if it names real slots, names real blocks, and
    accounts for EVERY block exactly once (total coverage). That last clause is
    what retires the content-destruction class: ADR-462 D9's invariant hardens
    from "refuse when unmappable" to "account for every block, always".

    Returns the normalized placements, or None when the plan is inadmissible
    (the caller falls back to the mechanical ladder).
    """
    slot_names = {str(s.get("name")) for s in slots if s.get("name")}
    block_ids = [str(b.get("id")) for b in blocks if b.get("id")]
    if not block_ids:
        return []  # nothing to carry — a vacuously valid plan
    if not slot_names:
        return None  # a layout with nowhere to put content cannot receive it

    seen: set[str] = set()
    out: list[dict] = []
    for p in placements or []:
        if not isinstance(p, dict):
            return None
        bid = str(p.get("block_id") or "")
        slot = str(p.get("slot") or "")
        if bid not in block_ids:
            return None  # invented or stale block id
        if slot not in slot_names:
            return None  # invented slot
        if bid in seen:
            return None  # a block placed twice
        seen.add(bid)
        out.append({"block_id": bid, "slot": slot})

    if seen != set(block_ids):
        return None  # a block went unplaced — the destruction bug's signature
    return out


async def plan_arrangement(
    blocks: list[dict],
    slots: list[dict],
    *,
    model: Optional[str] = None,
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
    if not slots:
        return None, None

    # OUTSIDE the try, deliberately (the ADR-475 lesson): a typo'd symbol here
    # would otherwise be swallowed by the fallback and look exactly like "the
    # router is off" — the planner would silently never plan again. A broken
    # import is a bug, not a fallback condition; only the CALL may fail soft.
    from services.agents_registry import KERNEL_AGENTS
    from services.model_router import model_router_enabled, route_completion

    completion = None
    try:
        if not model_router_enabled():
            logger.info("[STUDIO] router off — mechanical arrangement")
            return None, None

        engine = model or KERNEL_AGENTS["designer"]["model"]
        completion = await route_completion(
            engine,
            [{"role": "user", "content": build_plan_request(blocks, slots)}],
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
        placements = validate_plan(raw.get("placements") or [], blocks, slots)
        if placements is None:
            logger.warning("[STUDIO] arrangement plan failed validation — mechanical")
            return None, completion
        return placements, completion
    except Exception as exc:  # noqa: BLE001 — any failure falls back, by design
        logger.warning("[STUDIO] arrangement plan failed (%s) — mechanical", exc)
        # A call that happened still costs, even if its output was unusable —
        # the caller meters `completion` regardless of the plan's fate.
        return None, completion
