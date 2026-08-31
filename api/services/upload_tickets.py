"""Upload tickets — the ADR-622 handshake for adding bytes to the workspace.

WHY THIS EXISTS. The connector speaks text. It cannot carry bytes: base64
through a token stream is measured to corrupt (Box: a file corrupted at 175KB,
failed outright at 20MB, cause named as "non-deterministic LLM inference can
subtly alter characters within the base64 data"), the MCP control plane is not a
data plane (ADR-427 §4a), and MCP tool INPUTS have no blob type at all. On top of
that, yarnnn's MCP server is REMOTE (streamable-HTTP on Render) and therefore
cannot read a caller's local disk the way a stdio server can.

THE SHAPE, which is the industry's converged answer (Box, Notion, Dropbox, S3,
SEP-2631) and not a local invention:

    control channel  →  mint a short-lived scoped capability   (this module)
    data channel     →  PUT/POST the bytes against it          (routes/uploads.py)

⭐⭐⭐ THE TICKET POINTS AT A YARNNN ENDPOINT, NEVER AT A BUCKET. Supabase can
mint a signed upload URL straight into storage, and using it would have been
fewer lines — but bytes arriving in a bucket bypass every guarantee the upload
door provides: the type verdict derived FROM THE BYTES (ADR-427 D5, never the
caller's declared type), the size caps, `write_revision` (ADR-209's single write
path), attribution, and the ADR-395 text projection that makes the file
searchable. Something would then have to reconcile the bucket with the substrate
— a SECOND intake path, which is precisely what CLAUDE.md's Singular
Implementation rule forbids. One pipeline, reached through one more door.

⭐⭐ AUTHORIZATION HAPPENS AT MINT, AND IS FROZEN INTO THE TICKET. The
destination is checked against `operator_can_organize` before the row is written,
then stored. The redeemer supplies bytes and nothing else — it cannot choose,
move, or widen the destination. This is deliberate: the redeemer authenticates
with a SECRET, not with a session, so it must not be able to make authorization
decisions. (Compare ADR-555's finding: "the moment a destination becomes
caller-supplied it needs an authorization" — here the caller-supplied moment is
the mint, so that is where the check lives.)
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

#: How long a ticket lives. Matches the ADR-427 D4 serving URL, and for the same
#: reason: a capability that outlives the conversation that minted it is a
#: standing write door into the commons.
TICKET_TTL_SECONDS = 3600

#: Refused at MINT time so a caller learns the limit before transferring
#: anything. The REAL enforcement is `_process_single_upload`'s cap, applied to
#: the actual bytes — this is the fast-fail courtesy, never the guard.
MAX_DECLARED_BYTES = 100 * 1024 * 1024  # the ADR-331 media cap


class TicketError(Exception):
    """A ticket could not be minted or redeemed. Carries a caller-safe reason."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def mint_upload_ticket(
    service: Any,
    *,
    user_id: str,
    workspace_id: Optional[str],
    filename: str,
    minted_by: str,
    destination: Optional[str] = None,
    declared_bytes: Optional[int] = None,
) -> dict:
    """Mint a single-use capability to add ONE file. Raises TicketError.

    `minted_by` is provenance (which principal asked), never authorization —
    the grant was checked against `user_id` before this is called, and the
    destination is authorized here.
    """
    fname = (filename or "").strip().strip("/")
    if not fname or "/" in fname or "\\" in fname or ".." in fname:
        raise TicketError(
            "invalid_filename",
            "Pass a bare filename with an extension (e.g. `promo.mp4`) — the "
            "folder is the `destination`, not part of the name.",
        )

    if declared_bytes is not None:
        try:
            declared_bytes = int(declared_bytes)
        except (TypeError, ValueError):
            raise TicketError("invalid_size", "size_bytes must be a number.")
        if declared_bytes <= 0:
            raise TicketError("invalid_size", "size_bytes must be greater than zero.")
        if declared_bytes > MAX_DECLARED_BYTES:
            raise TicketError(
                "too_large",
                f"{declared_bytes:,} bytes is over the {MAX_DECLARED_BYTES // (1024*1024)}MB "
                "limit for a single upload.",
            )

    # ⭐ The destination is authorized HERE and frozen into the row. Same
    # normalization + same gate as the browser upload door, so the two cannot
    # disagree about where a principal may write (ADR-555).
    dest = (destination or "").strip().strip("/")
    if dest.startswith("workspace/"):
        dest = dest[len("workspace/"):]
    if dest:
        if ".." in dest:
            raise TicketError("invalid_destination", "Invalid destination folder.")
        from services.workspace_paths import operator_can_organize

        if not operator_can_organize(f"/workspace/{dest}/x"):
            raise TicketError(
                "destination_denied",
                f"Files can't be added to `{dest}` — that location is managed by "
                "the system. Choose a folder you author into.",
            )

    token = secrets.token_urlsafe(32)
    expires = _now() + timedelta(seconds=TICKET_TTL_SECONDS)
    row = {
        "workspace_id": workspace_id,
        "token": token,
        "user_id": user_id,
        "minted_by": minted_by,
        "destination": dest or None,
        "filename": fname,
        "declared_bytes": declared_bytes,
        "expires_at": expires.isoformat(),
    }
    try:
        service.table("workspace_upload_tickets").insert(row).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[UPLOAD-TICKET] mint failed for %s: %s", fname, exc)
        raise TicketError("mint_failed", "Could not create the upload ticket.")

    logger.info("[UPLOAD-TICKET] minted for %s by %s → %s", fname, minted_by, dest or "(intake)")
    return {"token": token, "expires_at": expires, "filename": fname, "destination": dest or None}


def claim_upload_ticket(service: Any, token: str) -> dict:
    """Atomically claim a ticket for redemption. Raises TicketError.

    ⭐⭐⭐ THE CLAIM IS A COMPARE-AND-SET, NOT A READ-THEN-WRITE. Single-use is
    the property that makes a write capability safe to hand out, and a
    read-then-update loses the race: two concurrent redemptions both read
    `redeemed_at IS NULL` and both proceed, so one ticket writes two files. The
    UPDATE below filters on `redeemed_at IS NULL` and returns the row it
    actually changed — the same CAS discipline `write_revision` uses for the
    revision chain (ADR-406) and `wake_queue` uses for its lock.

    Claiming BEFORE the bytes are processed is deliberate: a ticket is spent by
    the ATTEMPT, not by the success. The alternative (claim on success) leaves a
    failed-midway upload replayable, which is exactly the window a single-use
    capability exists to close.
    """
    tok = (token or "").strip()
    if not tok:
        raise TicketError("missing_token", "No upload ticket supplied.")

    try:
        claimed = (
            service.table("workspace_upload_tickets")
            .update({"redeemed_at": _now().isoformat()})
            .eq("token", tok)
            .is_("redeemed_at", "null")
            .gt("expires_at", _now().isoformat())
            .execute()
        ).data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[UPLOAD-TICKET] claim failed: %s", exc)
        raise TicketError("claim_failed", "Could not redeem the upload ticket.")

    if claimed:
        return claimed[0]

    # Nothing claimed. Distinguish the three reasons — an opaque "invalid" makes
    # a caller retry a ticket that can never work (ADR-373 D6: name the state).
    try:
        existing = (
            service.table("workspace_upload_tickets")
            .select("redeemed_at, expires_at, written_path")
            .eq("token", tok)
            .limit(1)
            .execute()
        ).data or []
    except Exception:  # noqa: BLE001
        existing = []

    if not existing:
        raise TicketError("unknown_ticket", "That upload ticket does not exist.")
    row = existing[0]
    if row.get("redeemed_at"):
        raise TicketError(
            "already_redeemed",
            "That upload ticket was already used"
            + (f" (it wrote `{row['written_path']}`)" if row.get("written_path") else "")
            + ". Tickets are single-use — ask for a new one to upload again.",
        )
    raise TicketError(
        "expired",
        "That upload ticket has expired. Ask for a new one — tickets are "
        f"short-lived ({TICKET_TTL_SECONDS // 60} minutes) on purpose.",
    )


def record_ticket_result(service: Any, ticket_id: str, written_path: Optional[str]) -> None:
    """Record what the redemption wrote. Best-effort — never breaks an upload
    that already landed (the file exists either way; this is the audit trail)."""
    try:
        (
            service.table("workspace_upload_tickets")
            .update({"written_path": written_path})
            .eq("id", ticket_id)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("[UPLOAD-TICKET] result record failed for %s: %s", ticket_id, exc)


__all__ = [
    "TICKET_TTL_SECONDS",
    "MAX_DECLARED_BYTES",
    "TicketError",
    "mint_upload_ticket",
    "claim_upload_ticket",
    "record_ticket_result",
]
