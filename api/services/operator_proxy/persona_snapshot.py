"""Persona snapshot/restore — the Concern-2 instrument (discourse §2a).

Captures + restores the 7 PERSONA_FILES (the agent's accumulated LEARNING state:
IDENTITY, principles, judgment_log, OCCUPANT, handoffs, reflection, standing_intent).
Replaces the one-way destructive wipe with checkpoint+restore, enabling three
replay modes over the same substrate (discourse §2a):

  - isolated     — restore to a CLEAN snapshot before each fire (single-wake
                   isolation, the ADR-360 behavioral mode; reversible).
  - seeded       — restore to a HAND-AUTHORED snapshot, fire once (continuity).
  - accumulating — NEVER restore between fires; memory grows across N wakes
                   (the unattended-soak / tenure mode — the SUSTAIN claim).

Pure Hat-B developer toolchain (operator_proxy) — NO kernel change, no canon.
It snapshots ONLY persona/ (the agent's learning state). It deliberately does
NOT snapshot the corpus (operation/) — the corpus accumulating across wakes is
PART OF the soak signal, not state to reset.

Attribution: every restore write is `operator-proxy:persona-snapshot:acting-as-{persona}`
per ADR-294 D2 (the operator's voice, replaying its own substrate).
"""

from __future__ import annotations

import asyncio
from typing import Any

from services.workspace_paths import PERSONA_FILES


def _full(path: str) -> str:
    return path if path.startswith("/workspace/") else f"/workspace/{path.lstrip('/')}"


def snapshot_persona(client: Any, user_id: str) -> dict[str, str | None]:
    """Capture the current content of all PERSONA_FILES.

    Returns {bare_path: content_or_None}. None means the file is absent (a
    clean baseline) — restore re-creates that absence by deleting.
    """
    blob: dict[str, str | None] = {}
    for path in PERSONA_FILES:
        res = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", _full(path))
            .limit(1)
            .execute()
        )
        rows = res.data or []
        blob[path] = (rows[0].get("content") if rows else None)
    return blob


async def restore_persona(
    client: Any,
    user_id: str,
    blob: dict[str, str | None],
    *,
    persona: str = "unknown",
) -> dict[str, str]:
    """Write the snapshot back. A file that was absent in the snapshot is
    DELETED (restoring the clean baseline's absence); a file with content is
    re-written via write_revision (revision chain preserved per ADR-209).

    Returns {bare_path: "written:<rev8>" | "deleted" | "absent"}.
    """
    from services.authored_substrate import write_revision

    author = f"operator-proxy:persona-snapshot:acting-as-{persona}"
    loop = asyncio.get_running_loop()
    result: dict[str, str] = {}

    for path, content in blob.items():
        full = _full(path)
        if content is None:
            # Snapshot had this file absent → restore the absence.
            def _del(p: str = full) -> None:
                client.table("workspace_files").delete().eq("user_id", user_id).eq("path", p).execute()
            await loop.run_in_executor(None, _del)
            result[path] = "deleted"
            continue
        rev = await loop.run_in_executor(
            None,
            lambda p=full, ct=content: write_revision(
                client, user_id=user_id, path=p, content=ct,
                authored_by=author, message="persona-snapshot restore (replay baseline)",
            ),
        )
        result[path] = f"written:{(rev or '')[:8]}"
    return result
