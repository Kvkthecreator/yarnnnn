"""The one edit door for an office file (ADR-671 D3).

EditFile (the lane, headless work) and MCP `edit` (every connected LLM) reach
this; Phase 2's app office modes will too. It reads the head's BYTES, applies
the addressed edits with the format's editor (declared on its registry row),
and lands the result as ONE attributed revision conditional on the head it
read — so a concurrent writer surfaces as a conflict, never a clobber.

Who authored the edit decides how a Word document carries it (D4): a member's
own hand writes clean; anything authored through a model — the member's lane,
an external LLM, an agent — lands as Word tracked changes under the
principal's display name, the same name the history panel shows. A format
without tracked changes carries its attribution on the revision alone.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from services.office.package import OfficeEditError

logger = logging.getLogger(__name__)


def normalize_edits(input: dict) -> List[dict]:
    """EditFile's arguments → the engine's edit list.

    One edit: `anchor={'at': A}` (or `{'after': A}` to insert a paragraph) with
    `old_string` / `new_string` / `style`. Several, as ONE revision: `edits=[{at |
    after, old_string?, new_string?, style?}, …]`.
    """
    raw = input.get("edits")
    if raw is None:
        anchor = input.get("anchor") or {}
        raw = [{
            "at": anchor.get("at"), "after": anchor.get("after"),
            "old_string": input.get("old_string"), "new_string": input.get("new_string"),
            "style": input.get("style"),
        }]
    if not isinstance(raw, list) or not raw:
        raise OfficeEditError("edits must be a non-empty list.")
    out: List[dict] = []
    for e in raw:
        if not isinstance(e, dict):
            raise OfficeEditError("Each edit is an object: {at, old_string?, new_string?, style?}.")
        at, after = e.get("at"), e.get("after")
        if bool(at) == bool(after):
            raise OfficeEditError(
                "An office edit names ONE address: anchor={'at': …} to change an element, or "
                "{'after': 'p12'} to insert a paragraph. The addresses are the labels ReadFile shows."
            )
        new, style = e.get("new_string"), e.get("style")
        if after:
            out.append({"op": "insert", "at": after, "new": new or "", "style": style})
        elif new is None and style:
            out.append({"op": "style", "at": at, "style": style})
        elif new is None:
            raise OfficeEditError(f"The edit at {at} needs new_string (or style).")
        else:
            out.append({"op": "replace", "at": at, "old": e.get("old_string"), "new": new, "style": style})
    return out


async def edit_office_file(
    auth: Any,
    *,
    path: str,
    request: dict,
    authored_by: str,
    message: str,
    author_identity_uuid: Optional[str] = None,
) -> Optional[dict]:
    """Apply EditFile's `request` to the office file at `path` (absolute), in place.

    Returns None when the head is not an office file's bytes (a text file under
    an office name, from before ADR-395 am.2 wrote the format) — the caller then
    edits it as the text it is. Otherwise a result dict; a refusal is
    `{success: False, error, message}` in words the agent and member can act on.
    Raises StaleWriteError when the head moved after it was read.
    """
    from services.authored_substrate import read_revision
    from services.documents import land_binary_revision
    from services.file_formats import office_kind
    from services.principal_display import classify_author, display_author, member_ids_of, resolve_member_names
    from services.storage_backend import get_storage_backend
    from services.supabase import get_service_client

    kind = office_kind(path)
    if kind is None:
        return None
    head = read_revision(auth.client, user_id=auth.user_id, path=path)
    if head is None:
        return {"success": False, "error": "file_not_found",
                "message": f"No file at {path}. EditFile changes an existing file — WriteFile creates one."}
    if head.content or not head.blob_sha:
        return None

    service = get_service_client()
    data = get_storage_backend(service).get_blob(head.blob_sha, workspace_id=getattr(auth, "workspace_id", None))
    tracked = classify_author(authored_by) != "member"
    author = None
    if tracked and kind.tracks_changes:
        names = resolve_member_names(service, member_ids_of(authored_by, author_identity_uuid))
        author = display_author(authored_by, author_identity_uuid=author_identity_uuid, member_names=names)

    try:
        new_bytes, done = kind.apply(data, normalize_edits(request), author=author)
    except OfficeEditError as refused:
        return {"success": False, "error": "office_edit_refused", "message": str(refused)}
    except Exception as exc:  # noqa: BLE001 — a malformed file is a refusal, never a 500
        logger.exception("[OFFICE] edit failed for %s", path)
        return {"success": False, "error": "office_edit_failed",
                "message": f"This {kind.name} could not be edited: {exc}"}

    landed = await land_binary_revision(
        auth,
        path=path,
        data=new_bytes,
        authored_by=authored_by,
        author_identity_uuid=author_identity_uuid,
        message=message,
        summary="; ".join(done),
        expected_parent_version_id=head.id,
    )
    in_file = tracked and kind.tracks_changes
    return {
        "success": True,
        "path": path,
        "applied": done,
        "tracked_changes": in_file,
        "message": (
            f"{len(done)} change(s) to the {kind.name} as one revision; every other "
            "part of the file is as it was."
            + (f" They show in the file as tracked changes by {author}." if in_file else "")
            + " ReadFile again before a further edit — addresses after an insert move."
        ),
        **landed,
    }


__all__ = ["edit_office_file", "normalize_edits"]
