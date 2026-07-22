"""Permanent delete — the terminal, unrecoverable removal of a trashed file.

ADR-478. Delete has been trash-not-erase since ADR-329: it archives (a new
`lifecycle='archived'` revision), reversible via restore. This module adds the
SECOND, terminal step — remove a file that is already in the trash for good.

The contract (ADR-478 D3): **unrecoverable, not unremembered.** The two words are
in tension and the resolution is exact: ADR-209 protects that the ledger never
LIES, not that every path's rows live forever.

  - The deleted path's namespace row (`workspace_files`) goes.
  - The deleted path's revision chain (`workspace_file_versions`) goes — a
    surviving chain is a resurrection vector, so keeping it would make "permanent"
    false. This is the ONE place a member act removes revisions, bounded to
    exactly the path being destroyed.
  - NO other path's revisions are touched — `trace` on every surviving file stays
    complete and true. That is the immutability that matters.
  - Content (`workspace_blobs`, row + bucket object) goes — but only the blobs no
    OTHER path's revision still cites (21 blobs live are shared across paths;
    over-deleting would strand an unrelated live file).

Guards, enforced by the CALLER (routes/documents.py), not here:
  - owner-grade authority (ADR-478 D4 — destroys shared content),
  - the file must actually be archived (only trash is permanently deletable),
  - no live file may cite it via derived_from (ADR-478 D5).

This module is the mechanical body: given a resolved, authorized, archived path,
remove what D3 says to remove and leave the ledger intact.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _blob_still_cited_elsewhere(
    client: Any, workspace_id: Optional[str], user_id: str, sha: str, exclude_path: str
) -> bool:
    """True if any revision of a DIFFERENT path in this workspace cites `sha`.

    Reference-counting at the revision level: a blob is content-addressed and
    (ADR-474 D3, live) shared across paths whenever two files hold identical
    bytes — kernel seeds, empty files, a copied artifact. Deleting the blob
    while another live path's revision points at it would strand that file's
    content. Scoped to the workspace (the blob's owner unit).
    """
    q = client.table("workspace_file_versions").select("id").eq("blob_sha", sha)
    q = q.eq("workspace_id", workspace_id) if workspace_id else q.eq("user_id", user_id)
    rows = q.neq("path", exclude_path).limit(1).execute().data
    return bool(rows)


def permanently_delete_file(
    client: Any,
    *,
    user_id: str,
    workspace_id: Optional[str],
    path: str,
) -> dict:
    """Terminally remove an archived file. ADR-478 D3.

    Order (each step safe on its own):
      1. Gather the file's distinct blob_shas from its revision chain.
      2. Delete the namespace row (nulling head_version_id first — the FK).
      3. Delete the revision chain FOR THIS PATH (ADR-478 D3 — a surviving chain
         is a resurrection vector; "permanent" forbids it). No other path's rows
         are touched, so trace on every surviving file stays complete.
      4. For each blob no other path still cites, delete it through the storage
         seam (row + bucket object, last-owner-only — ADR-474 §4).

    Returns a summary: {rows, revisions, blobs}.
    """
    from services.storage_backend import get_storage_backend

    def _scope(q: Any) -> Any:
        return q.eq("workspace_id", workspace_id) if workspace_id else q.eq("user_id", user_id)

    # 1. the blobs this path's chain references
    revs = _scope(
        client.table("workspace_file_versions").select("id, blob_sha").eq("path", path)
    ).execute().data or []
    shas = {r["blob_sha"] for r in revs if r.get("blob_sha")}

    # 2. drop the namespace row (null the head FK first — ADR-209 order)
    _scope(
        client.table("workspace_files").update({"head_version_id": None}).eq("path", path)
    ).execute()
    _scope(client.table("workspace_files").delete().eq("path", path)).execute()

    # 3. drop this path's revision chain (see design note)
    _scope(client.table("workspace_file_versions").delete().eq("path", path)).execute()

    # 4. collect the blobs nothing else cites — AFTER the chain is gone, so the
    #    "cited elsewhere" test sees the true remaining graph
    backend = get_storage_backend(client)
    blobs_removed = 0
    for sha in shas:
        if _blob_still_cited_elsewhere(client, workspace_id, user_id, sha, path):
            continue
        try:
            if backend.delete_blob(sha, workspace_id=workspace_id):
                blobs_removed += 1
        except Exception as exc:  # noqa: BLE001 — a blob left behind is collectable, never a breach
            logger.warning(f"[PERMADELETE] blob delete failed for {sha[:12]}: {exc}")

    logger.info(
        f"[PERMADELETE] {path} — 1 row, {len(revs)} revisions, {blobs_removed} blobs (user {user_id})"
    )
    return {"rows": 1, "revisions": len(revs), "blobs": blobs_removed}
