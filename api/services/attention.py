"""Attention weight — the third axis of the one derivation (ADR-489).

FOUNDATIONS Axiom 9: logging is complete; rendering weight (material /
routine / housekeeping) is UI policy. DP29 routes attention over that weight
taxonomy — this module is where the taxonomy is finally computed. Pure
derivation at read time from facts the ledgers already carry (attribution,
path, ADR-423 revision_kind, invocation mode/status); nothing is stored.

Consumed by GET /api/workspace/timeline, which stamps every TimelineEntry.
The bell mounts material only; the Notifications workbench defaults to
material + routine with the complete record one click away (ADR-489 D2).
"""

from __future__ import annotations

from typing import Optional

MATERIAL = "material"
ROUTINE = "routine"
HOUSEKEEPING = "housekeeping"


def _root_group(path: str) -> str:
    """The path's operator zone (work / arrival / system) via WORKSPACE_ROOTS.

    Unknown roots read as 'work' — a future meaning-folder must never be
    silently demoted to housekeeping (fail-open, ADR-489 D2).
    """
    from services.workspace_paths import WORKSPACE_ROOTS

    root = path.lstrip("/").split("/", 1)[0]
    meta = WORKSPACE_ROOTS.get(root)
    return (meta or {}).get("group", "work")


def classify_weight(
    kind: str,
    *,
    path: Optional[str] = None,
    revision_kind: Optional[str] = None,
    mode: Optional[str] = None,
    status: Optional[str] = None,
) -> str:
    """Classify one timeline entry's attention weight (ADR-489 D1).

    First match wins; anything unrecognized is material (fail-open — a new
    entry kind is never silently hidden from attention).
    """
    if kind == "proposal":
        # A witness event — before-witness demands, after-witness informs.
        return MATERIAL

    if kind == "invocation":
        if status == "failed":
            return MATERIAL  # failures demand attention regardless of mode
        if mode == "judgment":
            # The run is legibility; its material OUTPUT surfaces separately
            # as a revision row (a NO_BRIEF/skipped judgment run stays quiet).
            return ROUTINE
        return HOUSEKEEPING  # mechanical — sync/capture/index machinery

    if kind == "revision":
        basename = (path or "").rstrip("/").rsplit("/", 1)[-1]
        if basename.startswith("_"):
            # Machine-parsed state (§9 file discipline) — reconstructable
            # bookkeeping; the audit's literal symptom rows land here.
            return HOUSEKEEPING
        if path and _root_group(path) == "system":
            return HOUSEKEEPING  # kernel-bootstrap residue zone
        if revision_kind == "observation":
            # A retained raw arrival (DP32 ledger-intake) — legible, not
            # demanding; the derivation citing it is the material act.
            return ROUTINE
        return MATERIAL  # authored acts + derivations, by any principal

    return MATERIAL
