"""
folder_organize — a folder verb is a FAN-OUT over its subtree, not one act.

Since ADR-588 a folder is a MARKER ROW (`content_type='inode/directory'`) plus
whatever files share its path prefix. There is no folder object holding
children, so "rename this folder", "move this folder", "move this folder to
Trash" cannot be one row-update: each is a fan-out that must touch every file
under the prefix, one attributed revision at a time, through the ONE write path
(ADR-209). That is the whole reason these three verbs were missing from
`FileContextMenu` until now — the gap was structural, not an oversight.

Three properties this module is responsible for, and each one exists because
the absent version of it is a defect the operator would meet:

  1. ENUMERATION IS SHARED between the preflight COUNT and the ACT. The menu
     label reads "Move to Trash (40 items)", so the number the operator is shown
     and the number the act performs must come from the same walk — a count
     computed by a second, subtly different query is a blast-radius promise the
     act does not keep.

  2. LOCKED CHILDREN ARE REPORTED, NEVER SILENTLY SKIPPED. `operator_can_organize`
     refuses `system/`, raw `inbound/` (except `inbound/uploads/`), and
     `_*.yaml`/`_*.json` leaves. A folder holding any of those can only be
     PARTIALLY organized. Every function here returns the locked set alongside
     the moved set, so the surface can say "38 moved to Trash · 2 are managed by
     the system and stayed." Following the set-Move precedent (ADR-553 D2's
     commitMoveMany), which already reports which half landed — not a second
     report shape.

  3. TRASH GROUPS BY THE DELETED ROOT. Fanning 40 files into Trash as 40 loose
     rows makes the folder unrecoverable as a folder: the operator would have to
     restore 40 times and rebuild the shape by hand. So each archived row carries
     a grouping key naming the folder that was trashed, and Trash reads it back
     as ONE restorable unit.

     The key lives in `workspace_files.metadata['trashed_with']` — deliberately
     NOT a new column. Two reasons: (a) it is per-ROW presentation state about
     one archive act, which is exactly what that JSONB is for, and (b) a column
     would need a migration against live substrate for a grouping affordance, on
     a table whose write path is already the most-guarded seam in the system.
     Written with a READ-MERGE-WRITE, following the launch-handler precedent
     (`routes/documents.py::set_launch_handler`): a blind replace would destroy a
     file's Open-With binding on its way to the Trash, and restoring it would
     bring back a file that had forgotten how to open.

Non-goals, stated so a later reader does not read them as omissions:
  - No bulk primitive. Move fans out through `MoveFile` (the ONE mover,
    `primitives/workspace.py::handle_move_file`) file by file. Inventing a bulk
    mover would mean inventing partial-failure semantics the single mover
    already has.
  - Non-transactional, like every other multi-file act here. A half-landed fan
    is reported honestly rather than pretended away.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from services.workspace_paths import (
    operator_can_organize,
    folder_marker_path,
    is_folder_marker,
)

logger = logging.getLogger(__name__)

#: The metadata key naming the folder a file was trashed AS PART OF. Absent on
#: a file trashed on its own — which is exactly how Trash tells a grouped
#: archive from a loose one, with no second flag to keep in sync.
TRASHED_WITH_KEY = "trashed_with"

#: Hard ceiling on one fan-out. A folder verb is an operator gesture, not a
#: migration; past this the honest answer is to refuse and say so rather than
#: half-perform a thousand-file act inside one request. Sized well above any
#: hand-organized folder and well below anything that would time out.
MAX_FAN_OUT = 500


class FolderTooLarge(Exception):
    """A folder holds more rows than one gesture may fan out over."""

    def __init__(self, count: int):
        self.count = count
        super().__init__(
            f"This folder holds {count} items — more than a single action can "
            f"move at once (limit {MAX_FAN_OUT})."
        )


def _scope(query, user_id: str, workspace_id: Optional[str]):
    from services.workspace_context import substrate_scope_filter

    return query.eq(*substrate_scope_filter(user_id, workspace_id))


def normalize_folder(path: str) -> tuple[str, str]:
    """A folder path in any spelling → (absolute folder path, marker path).

    The folder itself is returned WITHOUT a trailing slash (the addressing
    form used by every prefix query below); the marker is the trailing-slash
    row `folder_marker_path` mints. Both spellings are needed in the same
    breath everywhere here, so they are resolved once, together.
    """
    marker = folder_marker_path(path)          # "/workspace/deals/acme/"
    abs_folder = marker.rstrip("/")            # "/workspace/deals/acme"
    return abs_folder, marker


def enumerate_subtree(
    client: Any,
    *,
    user_id: str,
    workspace_id: Optional[str],
    folder_path: str,
) -> dict:
    """Walk a folder's live subtree ONCE, and split it the way every caller needs.

    Returns::

        {
          "folder": "/workspace/deals/acme",
          "marker": "/workspace/deals/acme/",     # None when no marker row exists
          "files":  [ ...paths the operator may organize... ],
          "locked": [ ...paths operator_can_organize refuses... ],
          "markers":[ ...nested folder markers, incl. this folder's own... ],
        }

    `files` is what the count reports and the act performs; `locked` is what the
    honest report names. Nested MARKERS are carried separately from files
    because they are directories, not documents: they must travel with the fan
    (a moved folder keeps its empty sub-folders) but must never be counted as
    "items" to the operator — a folder is not a thing you deleted, it is where
    the things were.

    Archived rows are excluded: a subtree walk answers about the LIVE folder.
    """
    abs_folder, marker = normalize_folder(folder_path)

    rows = (
        _scope(
            client.table("workspace_files").select("path, content_type"),
            user_id,
            workspace_id,
        )
        .or_(f"path.eq.{marker},path.like.{abs_folder}/%")
        .or_("lifecycle.is.null,lifecycle.neq.archived")
        .limit(MAX_FAN_OUT + 1)
        .execute()
    ).data or []

    files: list[str] = []
    locked: list[str] = []
    markers: list[str] = []
    marker_present = False

    for row in rows:
        p = row.get("path") or ""
        if is_folder_marker(p, row.get("content_type")):
            markers.append(p)
            if p == marker:
                marker_present = True
            continue
        # A folder's own marker is a directory; a file under a locked prefix is
        # the operator's honest partial. Both are decided by the SAME predicate
        # the routes use — this module never re-derives the carve.
        (files if operator_can_organize(p) else locked).append(p)

    return {
        "folder": abs_folder,
        "marker": marker if marker_present else None,
        "files": sorted(files),
        "locked": sorted(locked),
        # DEEPEST FIRST. A move writes the destination then tombstones the
        # source; ordering markers deepest-first means a nested folder's marker
        # is handled before its parent's, so no step ever addresses a marker
        # under a prefix that has already moved.
        "markers": sorted(markers, key=lambda p: p.count("/"), reverse=True),
    }


def assert_within_limit(subtree: dict) -> None:
    """Refuse a fan-out larger than one gesture should perform."""
    total = len(subtree["files"]) + len(subtree["locked"]) + len(subtree["markers"])
    if total > MAX_FAN_OUT:
        raise FolderTooLarge(total)


def _merge_metadata_trashed_with(
    client: Any,
    *,
    user_id: str,
    workspace_id: Optional[str],
    path: str,
    root: str,
) -> None:
    """Stamp `metadata['trashed_with'] = root` WITHOUT clobbering the rest.

    Read-merge-write, following `set_launch_handler`. A blind
    `update({"metadata": {...}})` would drop a file's Open-With binding on the
    way to Trash — the file would come back from Restore having forgotten how
    to open, which is a worse defect than the one grouping fixes.

    Metadata-only, so it mints no revision: this is the ADR-209 declared
    exception (a metadata update that does not mutate content), the same
    footing `set_launch_handler` stands on. The ARCHIVE itself is the attributed
    act, and it already happened through `write_revision`.
    """
    rows = (
        _scope(
            client.table("workspace_files").select("metadata"), user_id, workspace_id
        )
        .eq("path", path)
        .limit(1)
        .execute()
    ).data or []
    metadata = dict((rows[0].get("metadata") if rows else None) or {})
    metadata[TRASHED_WITH_KEY] = root
    _scope(
        client.table("workspace_files").update({"metadata": metadata}),
        user_id,
        workspace_id,
    ).eq("path", path).execute()


def trash_folder(
    client: Any,
    *,
    user_id: str,
    workspace_id: Optional[str],
    folder_path: str,
    author_identity_uuid: Optional[str] = None,
) -> dict:
    """Move a folder to Trash — one attributed archive revision PER FILE.

    Preserves ADR-209 exactly as the single-file delete does: nothing is
    removed, each row gets a new `lifecycle='archived'` revision attributed to
    the operator, and every one is restorable. The folder's own marker is
    archived too (otherwise the emptied folder would linger in the tree as a
    ghost the operator cannot remove).

    Every archived row is stamped with the deleted ROOT so Trash can show the
    folder as ONE restorable unit rather than N loose rows.

    Returns `{root, archived: [...], locked: [...]}` — the honest partial.
    """
    from services.authored_substrate import write_revision

    subtree = enumerate_subtree(
        client, user_id=user_id, workspace_id=workspace_id, folder_path=folder_path
    )
    assert_within_limit(subtree)

    root = subtree["folder"]
    # `archived` counts FILES only, and `markers_archived` the directories.
    # A folder is not an item you deleted, it is where the items were — counting
    # it would make "40 items" disagree with the 38 files the operator saw.
    archived: list[str] = []
    markers_archived: list[str] = []
    file_set = set(subtree["files"])

    # Files first, then markers (deepest-first) — a folder's marker is the last
    # thing to go, so the subtree never reads as an empty named folder mid-fan.
    targets = list(subtree["files"]) + list(subtree["markers"])

    for path in targets:
        row = (
            _scope(
                client.table("workspace_files").select(
                    "content, head_version_id, content_type"
                ),
                user_id,
                workspace_id,
            )
            .eq("path", path)
            .limit(1)
            .execute()
        ).data
        if not row:
            continue
        try:
            write_revision(
                db_client=client,
                user_id=user_id,
                workspace_id=workspace_id,
                path=path,
                **_content_form_for_head(client, user_id, workspace_id, row[0]),
                authored_by="operator",
                author_identity_uuid=author_identity_uuid,
                message=f"Archived by operator (folder moved to trash: {root})",
                lifecycle="archived",
                content_type=row[0].get("content_type"),
            )
        except Exception as exc:  # noqa: BLE001 — reported, never swallowed
            logger.error("[FOLDER_ORGANIZE] archive failed for %s: %s", path, exc)
            continue
        _merge_metadata_trashed_with(
            client,
            user_id=user_id,
            workspace_id=workspace_id,
            path=path,
            root=root,
        )
        (archived if path in file_set else markers_archived).append(path)

    return {
        "root": root,
        "archived": archived,
        "markers_archived": markers_archived,
        "locked": subtree["locked"],
    }


def _content_form_for_head(
    client: Any, user_id: str, workspace_id: Optional[str], row: dict
) -> dict:
    """The content form that preserves a file's head blob verbatim (ADR-427 §4c).

    A byte-for-byte peer of `routes/documents.py::_content_form_for_head`, but
    reading through the service client + workspace scope this module already
    holds. Re-writing the TEXT denorm instead would put an EMPTY text revision
    at the head of every binary chain the fan touches — a folder of images would
    come back from Restore as a folder of empty files.
    """
    head_id = row.get("head_version_id")
    if head_id:
        try:
            head = (
                client.table("workspace_file_versions")
                .select("blob_sha")
                .eq("id", head_id)
                .limit(1)
                .execute()
            ).data
            if head and head[0].get("blob_sha"):
                return {"content_ref": head[0]["blob_sha"]}
        except Exception as exc:  # noqa: BLE001 — fall back to the denorm
            logger.warning("[FOLDER_ORGANIZE] head blob lookup failed: %s", exc)
    return {"content": row.get("content", "") or ""}


def restore_group(
    client: Any,
    *,
    user_id: str,
    workspace_id: Optional[str],
    root: str,
    author_identity_uuid: Optional[str] = None,
) -> dict:
    """Restore every file archived as part of one folder-trash act.

    The inverse of `trash_folder`, addressed by the SAME grouping key: it
    restores exactly the rows that act stamped, so a file the operator trashed
    separately after the folder went is not swept back in by a prefix match.
    Clears the key as it goes — a restored file is no longer part of a trashed
    group, and leaving the stamp would make a second, unrelated trash of one of
    those files reappear inside a folder group it has nothing to do with.
    """
    from services.authored_substrate import write_revision

    rows = (
        _scope(
            client.table("workspace_files").select(
                "path, content, head_version_id, content_type, metadata"
            ),
            user_id,
            workspace_id,
        )
        .eq("lifecycle", "archived")
        .contains("metadata", {TRASHED_WITH_KEY: root})
        .limit(MAX_FAN_OUT)
        .execute()
    ).data or []

    restored: list[str] = []
    for row in rows:
        path = row.get("path") or ""
        if not path:
            continue
        try:
            write_revision(
                db_client=client,
                user_id=user_id,
                workspace_id=workspace_id,
                path=path,
                **_content_form_for_head(client, user_id, workspace_id, row),
                authored_by="operator",
                author_identity_uuid=author_identity_uuid,
                message=f"Restored from trash (folder: {root})",
                lifecycle="active",
                content_type=row.get("content_type"),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("[FOLDER_ORGANIZE] restore failed for %s: %s", path, exc)
            continue
        metadata = dict(row.get("metadata") or {})
        metadata.pop(TRASHED_WITH_KEY, None)
        _scope(
            client.table("workspace_files").update({"metadata": metadata}),
            user_id,
            workspace_id,
        ).eq("path", path).execute()
        restored.append(path)

    return {"root": root, "restored": restored}


async def move_folder(
    auth: Any,
    *,
    subtree: dict,
    new_folder: str,
) -> dict:
    """Move (or RENAME — the same act with a new leaf) a folder's whole subtree.

    Fans out over `MoveFile`, the ONE mover: each file gets a revision at its
    new path and a tombstone at the old, refusing to overwrite. There is no
    second write path here, deliberately — `handle_move_file` also carries an
    upload's `.extracted.md` projection along with its raw (ADR-554 D1), and a
    bespoke bulk mover would silently drop that.

    `new_folder` is the ABSOLUTE destination folder path (`/workspace/...`).
    Rename is not a separate branch: renaming `deals/acme` to `deals/acme-corp`
    is a move to a sibling path, so one implementation serves both verbs and
    there is no second place for the two to drift.

    SEQUENTIAL, not parallel — the same reason `commitMoveMany` is (ADR-553 D2):
    concurrent writes into one destination race on `destination_exists`, and the
    loser's 409 would read to the operator as a random failure.

    Returns `{moved, failed, locked}`. Non-transactional like every other
    multi-file act on this surface; a half-landed fan is REPORTED, not hidden.
    """
    from services.primitives.registry import execute_primitive

    src_root = subtree["folder"]
    dst_root = new_folder.rstrip("/")

    # `moved` counts FILES only. A folder marker is a directory, not an item
    # the operator moved — inflating the report with markers would make
    # "Moved 12 items" disagree with the 10 files they can see.
    moved: list[str] = []
    failed: list[str] = []
    markers_moved: list[str] = []

    # Files first, then the markers deepest-first, so a nested folder's marker
    # is never addressed under a prefix that has already moved out from under it.
    for path in list(subtree["files"]):
        if not path.startswith(src_root + "/"):
            continue
        new_path = dst_root + path[len(src_root):]
        result = await execute_primitive(
            auth, "MoveFile", {"path": path, "new_path": new_path, "scope": "workspace"}
        )
        if isinstance(result, dict) and result.get("success"):
            moved.append(new_path)
        else:
            failed.append(path)

    # Folder MARKERS travel by hand, not through MoveFile: a marker is a
    # zero-byte directory row, and the `WriteFile`-shaped guards the mover
    # inherits are written for documents. Re-minting the marker at the
    # destination and archiving the source keeps the operator's empty
    # sub-folders — which a files-only fan would silently discard.
    from services.authored_substrate import write_revision
    from services.workspace_paths import FOLDER_MARKER_CONTENT_TYPE

    client = auth.client
    workspace_id = getattr(auth, "workspace_id", None)
    for marker in list(subtree["markers"]):
        if marker.rstrip("/") == src_root:
            new_marker = dst_root + "/"
        elif marker.startswith(src_root + "/"):
            new_marker = dst_root + marker[len(src_root):]
        else:
            continue
        try:
            write_revision(
                db_client=client,
                user_id=auth.user_id,
                workspace_id=workspace_id,
                path=new_marker,
                content="",
                content_type=FOLDER_MARKER_CONTENT_TYPE,
                authored_by="operator",
                author_identity_uuid=auth.user_id,
                message=f"Folder moved: {src_root} -> {dst_root}",
            )
            write_revision(
                db_client=client,
                user_id=auth.user_id,
                workspace_id=workspace_id,
                path=marker,
                content="",
                content_type=FOLDER_MARKER_CONTENT_TYPE,
                authored_by="operator",
                author_identity_uuid=auth.user_id,
                message=f"Folder moved away: {src_root} -> {dst_root}",
                lifecycle="archived",
            )
            markers_moved.append(new_marker)
        except Exception as exc:  # noqa: BLE001 — reported, never swallowed
            logger.error("[FOLDER_ORGANIZE] marker move failed for %s: %s", marker, exc)
            failed.append(marker)

    return {
        "moved": moved,
        "failed": failed,
        "locked": subtree["locked"],
        "markers_moved": markers_moved,
    }
