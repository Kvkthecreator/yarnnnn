"""Folder verbs — the fan-out half of the working-tree analogy (ADR-337 amended).

`DeleteFolder` and `MoveFolder` complete the verb set ADR-337 set out to
complete. They are DECLARED here and BOUND to `services/folder_organize.py` —
the same fan-out the Files surface calls — so a folder verb is one act with one
implementation, whoever pulls the lever.

WHY THESE EXIST (2026-08-21)

A member asked their lane to delete a folder and was told the workspace
primitives "only operate file-by-file rather than recursively wiping whole
directory trees", and was advised to run `rm -rf` in a terminal instead. Both
halves were wrong. The fan-out existed (shipped `360ea4c`, the Files surface has
had Rename / Move / Move-to-Trash on folders since); and `rm -rf` on the repo
would not have touched these files at all — the substrate is Postgres, not disk.

ADR-337 predicted this failure exactly, in the passage that rules out a `Bash`
primitive:

    "It is also why missing verbs hurt so much here — there is no shell escape
     hatch — which argues for COMPLETING THE VERB SET, not adding the hatch."

WHY NO EXTRA GATE (the reassessment that produced this file)

The first design instinct was to make a lane's folder-delete queue for approval,
or cap its fan-out below the operator's. Both were rejected on ADR-337's own
first principles: **the descriptive names ARE the safety model**, and the safety
here is structural, not procedural. `trash_folder` writes one attributed
`lifecycle='archived'` revision PER FILE — nothing is removed, every row is
restorable, and the group restores as ONE unit. That makes it *safer* than the
`rm -rf` the model reached for, and safer than `WriteFile`, which can truncate a
file's content and flows freely. Gating the safest destructive verb in the
system while the lossy one runs unimpeded is incoherence, not caution.

So: same fan-out, same `MAX_FAN_OUT`, same locked-children report, same Trash
grouping — for the operator's click and the lane's tool call alike. The honesty
mechanism is the RESULT (`{archived, locked}` / `{moved, failed, locked}`), not
a ceremony in front of the act.

WHY DISTINCT VERBS RATHER THAN A FOLDER-AWARE `DeleteFile`

Blast radius must be legible in the verb the model CHOOSES and in the narration
the operator later READS. `DeleteFile` on a folder path would make the
transcript lie about what happened — and primitive names leak into feed
narration, revision messages and the proposals queue (Derived Principle 12).

NAMES OURS, CONTRACTS BORROWED — ADR-337's decision rule, held verbatim:
`DeleteFolder` / `MoveFolder` continue ADR-168's `*File`/`*Folder` family
naming (never `rm -r` / `mv`, which would import POSIX priors — flags, globs —
that do not exist here). The input schemas mirror the file verbs the model
already knows, so the trained prior transfers for free.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


DELETE_FOLDER_TOOL = {
    "name": "DeleteFolder",
    "description": """Move a whole FOLDER to Trash — one attributed revision per file inside it.

Deletion is a VIEW change, not information loss, exactly as DeleteFile: every
file gets an archive revision recording who deleted it and when, the revision
chain is retained, and the entire folder restores as ONE unit from Trash.

Use for substrate hygiene at folder grain: a superseded topic folder, a dead
scratch directory, a project that has ended. For a single file use DeleteFile —
this verb's blast radius is the whole subtree.

Files the operator may not organize (system paths, raw arrivals, machine
config) are REFUSED and REPORTED rather than silently skipped: the result names
them in `locked`, so say so ("19 moved to Trash · 2 are managed by the system
and stayed") instead of claiming a clean sweep.

Refuses a folder larger than a single gesture should move (500 items) rather
than half-performing it.

  DeleteFolder(path='operation/ai-frontier')""",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": (
                    "The folder to move to Trash, workspace-relative or absolute "
                    "(same addressing as DeleteFile). A trailing slash is optional."
                ),
            },
            "message": {
                "type": "string",
                "description": "Why this folder is going (recorded on each revision; optional).",
            },
        },
        "required": ["path"],
    },
}


MOVE_FOLDER_TOOL = {
    "name": "MoveFolder",
    "description": """Move or RENAME a whole FOLDER — the same act, addressed differently (ADR-337 D3 at folder grain).

Move   = a new_path under a different parent.
Rename = a new_path with the same parent and a new leaf.

Fans out over MoveFile: each file lands an attributed revision at its new path
and a tombstone at the old, refusing to overwrite an existing destination.
Nested empty folders travel with it.

Locked children are REFUSED and REPORTED in `locked`, never silently skipped;
a partially-landed move is reported in `failed` rather than hidden.

  MoveFolder(path='operation/acme', new_path='operation/deals/acme')""",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The folder's current path (same addressing as MoveFile).",
            },
            "new_path": {
                "type": "string",
                "description": (
                    "The folder's NEW path. A sibling path with a new leaf is a rename — "
                    "one verb serves both."
                ),
            },
            "message": {
                "type": "string",
                "description": "Why this folder is moving (recorded on each revision; optional).",
            },
        },
        "required": ["path", "new_path"],
    },
}


def _abs(path: str) -> str:
    p = (path or "").strip()
    if not p:
        return ""
    return p if p.startswith("/") else "/" + p


def _partial_report(performed: int, locked: list, verb: str) -> str:
    """The operator-facing sentence for a fan that could not be whole.

    One composer for both verbs — the ADR-553 D2 partial-report shape, so the
    lane's wording and the Files surface's cannot drift into two dialects of
    the same fact.
    """
    msg = f"{performed} {verb}"
    if locked:
        msg += (
            f" · {len(locked)} "
            f"{'is' if len(locked) == 1 else 'are'} managed by the system and stayed"
        )
    return msg


async def handle_delete_folder(auth: Any, input: dict) -> dict:
    """Move a folder to Trash, fanning out over its subtree.

    Binds `folder_organize.trash_folder` — the SAME call `POST
    /documents/folder/trash` makes for the operator's click. There is no second
    implementation here deliberately: a bespoke lane-side fan would drift from
    the surface's on grouping, locked-path handling, or the marker archive.
    """
    from services.folder_organize import FolderTooLarge, trash_folder
    from services.workspace_paths import operator_can_organize

    abs_path = _abs(input.get("path", ""))
    if not abs_path:
        return {"success": False, "error": "missing_path", "message": "path is required"}

    if not operator_can_organize(abs_path):
        return {
            "success": False,
            "error": "locked_path",
            "message": f"{abs_path} is managed by the system and can't be moved to Trash.",
        }

    try:
        result = trash_folder(
            auth.client,
            user_id=auth.user_id,
            workspace_id=getattr(auth, "workspace_id", None),
            folder_path=abs_path,
            author_identity_uuid=getattr(auth, "user_id", None),
        )
    except FolderTooLarge as exc:
        return {"success": False, "error": "folder_too_large", "message": str(exc)}
    except Exception as exc:  # pragma: no cover — surfaced, never swallowed
        logger.warning("[DeleteFolder] %s failed: %s", abs_path, exc)
        return {"success": False, "error": "delete_folder_failed", "message": str(exc)}

    archived, locked = result["archived"], result["locked"]
    return {
        "success": True,
        "root": result["root"],
        "archived": archived,
        "locked": locked,
        "message": _partial_report(len(archived), locked, "moved to Trash"),
        "note": "Restorable from Trash as one unit — the revision chain is retained.",
    }


async def handle_move_folder(auth: Any, input: dict) -> dict:
    """Move or rename a folder, fanning out over its subtree.

    Binds `folder_organize.move_folder` — the same call the operator's click
    makes, which itself fans out over the `MoveFile` primitive (the ONE mover,
    so an upload's `.extracted.md` projection travels with its raw per ADR-554).
    """
    from services.folder_organize import (
        FolderTooLarge,
        assert_within_limit,
        enumerate_subtree,
        move_folder,
    )
    from services.workspace_paths import operator_can_organize

    abs_path = _abs(input.get("path", ""))
    abs_dst = _abs(input.get("new_path", ""))
    if not abs_path or not abs_dst:
        return {
            "success": False,
            "error": "missing_path",
            "message": "path and new_path are required",
        }

    # BOTH ends are checked, like MoveFile's dual-path gate (ADR-337 D3): moving
    # a folder INTO system territory is as much a lock breach as moving one out.
    for p, which in ((abs_path, "source"), (abs_dst, "destination")):
        if not operator_can_organize(p):
            return {
                "success": False,
                "error": "locked_path",
                "message": f"{p} is managed by the system and can't be a move {which}.",
            }

    try:
        subtree = enumerate_subtree(
            auth.client,
            user_id=auth.user_id,
            workspace_id=getattr(auth, "workspace_id", None),
            folder_path=abs_path,
        )
        assert_within_limit(subtree)
        result = await move_folder(auth, subtree=subtree, new_folder=abs_dst)
    except FolderTooLarge as exc:
        return {"success": False, "error": "folder_too_large", "message": str(exc)}
    except Exception as exc:  # pragma: no cover — surfaced, never swallowed
        logger.warning("[MoveFolder] %s → %s failed: %s", abs_path, abs_dst, exc)
        return {"success": False, "error": "move_folder_failed", "message": str(exc)}

    moved, failed, locked = result["moved"], result["failed"], result.get("locked", [])
    out = {
        "success": True,
        "path": abs_path,
        "new_path": abs_dst,
        "moved": moved,
        "failed": failed,
        "locked": locked,
        "message": _partial_report(len(moved), locked, "moved"),
    }
    if failed:
        # A half-landed fan is REPORTED, never hidden — the same rule the
        # service holds itself to (it is non-transactional by design).
        out["message"] += f" · {len(failed)} could not move"
    return out


__all__ = [
    "DELETE_FOLDER_TOOL",
    "MOVE_FOLDER_TOOL",
    "handle_delete_folder",
    "handle_move_folder",
]
