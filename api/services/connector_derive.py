"""Connector derive — the digest, an OPT-IN consumer of landed connector
files (ADR-580, demoted by ADR-582 D5).

Built by ADR-580 as the intake pipeline's mandatory distil stage; re-cut by
ADR-582: the connector itself is a WRITER (`services/connectors.py`), and
this module is one CONSUMER among several — it runs only for connections with
``settings.connector.digest = true``, so "connect Slack" carries zero LLM
spend on its critical path. The shape is unchanged: the same bounded turn
radar and Strings run for the web lane.

One derive = ONE bounded, tool-less judgment turn per watched
``(platform, selector)`` (the shared ``derive_turn`` — ADR-580 D6), reading
the sub-lane's fresh raw plus the current digest, and maintaining ONE living
digest file:

    operation/_connectors/{platform}/{selector}.md

- **Living** (ADR-565 D1 shape): a fixed leaf whose history is the revision
  chain; members correct it like any file and corrections compound.
- **Embed-eligible** (under ``operation/``): this is what makes the material
  reachable by ranked recall — the whole point of stage 2 (intake-pipeline.md
  §1: without distil, ``inbound/`` is unreachable by design).
- **Cited** (ADR-448): the turn's consumed raw paths ride both the ledger
  ``derived_from`` edge and a head-anchored ``derived_from:`` block in the
  content — the block is what ``gather_cited_raw_paths`` reads, so cited raw
  is never pruned by the retention GC while the digest still stands on it.

Attribution (intake-pipeline.md §3, physically encoded per ADR-580 D4):

    authored_by          = "system:derive-{platform}"   (the mechanism)
    author_identity_uuid = platform_connections.connected_by   (the owner)

The ratified sentence — ``system:derive-{lane} on behalf of {owner}`` — is
COMPOSED AT DISPLAY (``principal_display.display_author``), never stored: a
raw UUID must not ride the ``authored_by`` string (the ``_scrub`` law), and a
display name stored at write time would freeze a name that moves.

Pace (the ADR-401 D5 amendment, preserved): derive cadence is DECOUPLED from
capture cadence. A selector derives at most once per ``DERIVE_MIN_INTERVAL_HOURS``
and only when raw NEWER than the deriver's own last write exists — a quiet
world costs $0, and capture chatter can never multiply judgment spend.

Trigger (ADR-591): there is NO drain. This module's writer is invoked by a
consumer; the walker that ran it on a tick is deleted. The pace law
(``is_due``) survives as a SPEND GUARD for whatever calls it. Historic note:
the drain used to run inside the scheduler's ``CONNECTOR_CAPTURE_ENABLED``
block (ADR-404 D2) — capture and derive are one lane, and flipping the flag
remains one operator decision.

This module deliberately carries no module-level ``services.*`` imports (the
radar cycle-free property).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


#: The deriver's floor between turns for one selector. Capture runs at
#: 15min–1h (CONNECTOR_CAPTURE_BINDINGS); the digest follows at most 4×/day.
DERIVE_MIN_INTERVAL_HOURS = 6

#: The attribution prefix — `system:derive-{platform}` (intake-pipeline.md §3).
DERIVE_AUTHOR_PREFIX = "system:derive-"

NO_CHANGE_SENTINEL = "NO_CHANGE"

_DIGEST_MAX_TOKENS = 2000
_DERIVE_TIMEOUT_S = 120.0
#: Newest raw snapshots consumed per turn; each capped so a busy channel
#: cannot blow the context.
_RAW_SNAPSHOTS_PER_TURN = 3
_RAW_CHARS_PER_SNAPSHOT = 40_000


# ---------------------------------------------------------------------------
# Placement (kernel-deterministic — the model never holds these levers)
# ---------------------------------------------------------------------------


#: The digests' home — beside the connectors' operating files (ADR-580 D3).
DIGEST_ROOT = "operation/_connectors"


def digest_path(platform: str, selector: str) -> str:
    """Where a selector's living digest lives — /workspace-absolute.

    One prose leaf per watched selector under the connectors' operating home,
    slugified by the SAME function that names the capture sub-lane so digest ↔
    raw correspond byte-for-byte. NOT `_`-prefixed: the digest is operator/LLM
    prose (ADR-254), never machine-parsed.
    """
    from services.connectors import _slugify_selector

    plat = _slugify_selector(platform)
    sel = _slugify_selector(selector)
    return f"/workspace/{DIGEST_ROOT}/{plat}/{sel}.md"


def parse_stamp(name: str) -> Optional[datetime]:
    """Re-export — the one stamp parser lives in `services.connectors`
    (ADR-582: one reader for landed snapshots, shared by every consumer)."""
    from services.connectors import parse_stamp as _parse
    return _parse(name)


def is_due(
    newest_raw_at: Optional[datetime],
    last_derive_at: Optional[datetime],
    now: datetime,
    *,
    min_interval_hours: int = DERIVE_MIN_INTERVAL_HOURS,
) -> bool:
    """Whether one selector's derive should run. Pure — the whole pace law.

    Due iff raw exists, it is NEWER than the deriver's own last write (a quiet
    world costs $0), and the min interval since that write has passed (capture
    chatter can never multiply judgment spend — the ADR-401 D5 lesson).
    A member's edit of the digest neither hastens nor delays the clock: the
    clock is the DERIVER's last write, not the file's.

    ADR-591 deleted the WALKER that called this on a tick; the law itself is
    KEPT deliberately. It was never a schedule — it is a SPEND GUARD, and a
    consumer-invoked derive (D3) needs it more than a cron did: a caller in a
    loop is exactly the shape "capture chatter multiplies judgment spend"
    describes. Whatever calls `run_connector_derive` gates on this first.
    """
    if newest_raw_at is None:
        return False
    if last_derive_at is None:
        return True
    if newest_raw_at <= last_derive_at:
        return False
    return (now - last_derive_at) >= timedelta(hours=min_interval_hours)


def build_connector_derive_posture(platform: str, selector: str) -> str:
    """The turn's job posture. Machinery — no resident character (ADR-580 D7);
    the digest speaks in the workspace's neutral register."""
    plat = (platform or "").strip().lower()
    return (
        f"You maintain the workspace's living digest of one {plat} slice "
        f"('{selector}'). You read raw platform observations the capture lane "
        "retained and keep ONE digest document current for the workspace's "
        "members and agents.\n\n"
        "The digest's contract:\n"
        "- Lead with a `# ` title naming the platform and slice, then the "
        "current picture: decisions, open threads, notable changes — what a "
        "member joining today should know. Recent developments go under a "
        "`## Recent developments` heading, newest first.\n"
        "- STRICTLY source-grounded: only what the raw observations state. "
        "Never speculate, never editorialize, never import outside knowledge.\n"
        "- Revise the CURRENT DIGEST in place — integrate, prune stale "
        "entries, keep it readable in one sitting. Return the full revised "
        "document.\n"
        f"- If the fresh raw contains nothing substantive, reply exactly "
        f"{NO_CHANGE_SENTINEL}.\n"
        "- Do NOT emit a `derived_from:` header or any provenance block — "
        "the system stamps provenance.\n"
        "- No preamble, no code fence around the document."
    )


def strip_provenance_header(content: str) -> str:
    """Drop the head-anchored ``derived_from:`` block (and its blank-line tail)
    so the model reads the digest's PROSE, not the machine header it must not
    reproduce. Pure; returns content unchanged when no header leads it."""
    lines = (content or "").split("\n")
    if not lines or not lines[0].strip().startswith("derived_from:"):
        return content or ""
    i = 1
    while i < len(lines) and re.match(r"\s*-\s+\S", lines[i]):
        i += 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    return "\n".join(lines[i:])


# ---------------------------------------------------------------------------
# The derive act — one selector, one bounded turn
# ---------------------------------------------------------------------------


def _last_derive_at(client: Any, user_id: str, digest_abs: str) -> Optional[datetime]:
    """The deriver's own last write to this digest (ledger truth, not file
    mtime — a member's edit must not move the pace clock)."""
    try:
        rows = (
            client.table("workspace_file_versions")
            .select("created_at")
            .eq("user_id", user_id)
            .eq("path", digest_abs)
            .like("authored_by", f"{DERIVE_AUTHOR_PREFIX}%")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        ).data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[CONNECTOR_DERIVE] last-derive query failed for %s: %s",
                       digest_abs, exc)
        return None
    if not rows:
        return None
    try:
        return datetime.fromisoformat(rows[0]["created_at"].replace("Z", "+00:00"))
    except (KeyError, ValueError, AttributeError):
        return None


async def _fresh_raw(
    um: Any, platform: str, selector: str, since: Optional[datetime],
    settings: Optional[dict] = None,
) -> list[tuple[str, datetime]]:
    """The slice's landed snapshots newer than `since` — THE shared reader
    (`connectors.read_landed_snapshots`, ADR-582 D6): destination-aware,
    oldest→newest, capped at the newest ``_RAW_SNAPSHOTS_PER_TURN``."""
    from services.connectors import read_landed_snapshots

    return await read_landed_snapshots(
        um, platform, selector, settings or {},
        since=since, limit=_RAW_SNAPSHOTS_PER_TURN,
    )


async def run_connector_derive(
    client: Any,
    user_id: str,
    platform: str,
    selector: str,
    *,
    connected_by: Optional[str],
    settings: Optional[dict] = None,
) -> dict:
    """One selector's derive: fresh raw + current digest → one bounded turn →
    the living digest, cited and attributed. Returns {success, platform,
    selector, digest_path?, revision_id?, no_change?, error_reason?}. Never
    raises past its own boundary."""
    from services.telemetry import record_execution_event
    from services.workspace import UserMemory
    from services.system_calls import resolve_system_call
    from services.derive_turn import run_bounded_derive_turn

    plat = (platform or "").strip().lower()
    slug = f"connector-derive:{plat}/{selector}"
    now = datetime.now(timezone.utc)
    um = UserMemory(client, user_id)
    digest_abs = digest_path(plat, selector)

    last_at = _last_derive_at(client, user_id, digest_abs)
    raws = await _fresh_raw(um, plat, selector, last_at, settings)
    if not raws:
        return {"success": True, "platform": plat, "selector": selector,
                "no_change": True, "skipped": "no_new_raw"}

    bodies: list[tuple[str, str]] = []
    for rel, _at in raws:
        try:
            body = await um.read(rel)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[CONNECTOR_DERIVE] read %s failed: %s", rel, exc)
            continue
        if body:
            bodies.append((rel, body[:_RAW_CHARS_PER_SNAPSHOT]))
    if not bodies:
        return {"success": False, "platform": plat, "selector": selector,
                "error_reason": "raw_unreadable"}

    current = None
    try:
        rows = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", digest_abs)
            .limit(1)
            .execute()
        ).data or []
        current = rows[0].get("content") if rows else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("[CONNECTOR_DERIVE] digest read failed for %s: %s",
                       digest_abs, exc)

    material = "\n\n".join(
        f"RAW OBSERVATION ({rel}):\n{body}" for rel, body in bodies
    )
    user_msg = (
        (f"THE CURRENT DIGEST:\n\n{strip_provenance_header(current)}\n\n"
         if current and current.strip() else
         "THERE IS NO DIGEST YET — this is the slice's first derive. Write "
         "the baseline digest from the raw observations.\n\n")
        + f"THE FRESH RAW OBSERVATIONS (just captured):\n\n{material}\n"
    )

    call = resolve_system_call("connector_derive")
    derive_started = datetime.now(timezone.utc)
    turn = await run_bounded_derive_turn(
        model=call.model,
        system=build_connector_derive_posture(plat, selector),
        user_msg=user_msg,
        max_tokens=_DIGEST_MAX_TOKENS,
        timeout=_DERIVE_TIMEOUT_S,
        no_change_tokens=(NO_CHANGE_SENTINEL,),
    )
    derive_ms = int((datetime.now(timezone.utc) - derive_started).total_seconds() * 1000)

    if turn.status == "router_disabled":
        record_execution_event(
            client, user_id=user_id, slug=slug,
            mode="judgment", trigger_type="scheduled", status="skipped",
            error_reason="router_disabled",
            funnel_decision="connector-derive",
            principal_id=connected_by or user_id,
        )
        return {"success": False, "platform": plat, "selector": selector,
                "error_reason": "router_disabled"}
    if turn.status == "raised":
        record_execution_event(
            client, user_id=user_id, slug=slug,
            mode="judgment", trigger_type="scheduled", status="failed",
            error_reason="derive_raised", error_detail=(turn.error or "")[:500],
            duration_ms=derive_ms, funnel_decision="connector-derive",
            principal_id=connected_by or user_id,
        )
        return {"success": False, "platform": plat, "selector": selector,
                "error_reason": "derive_raised"}
    if turn.status == "no_change":
        record_execution_event(
            client, user_id=user_id, slug=slug,
            mode="judgment", trigger_type="scheduled", status="skipped",
            error_reason="no_change", model=turn.ledger_model,
            duration_ms=derive_ms, funnel_decision="connector-derive",
            principal_id=connected_by or user_id, **turn.usage,
        )
        return {"success": True, "platform": plat, "selector": selector,
                "no_change": True}

    # Provenance header (head-anchored — what gather_cited_raw_paths reads;
    # the same block write_revision lifts into the ledger edge) + the body.
    raw_abs = [f"/workspace/{rel}" for rel, _ in bodies]
    content = (
        "derived_from:\n"
        + "".join(f"- {p}\n" for p in raw_abs)
        + "\n"
        + turn.text
        + ("\n" if not turn.text.endswith("\n") else "")
    )

    from services.authored_substrate import write_revision
    revision_id = write_revision(
        client,
        user_id=user_id,
        path=digest_abs,
        content=content,
        # The mechanism is the author; the OWNER rides author_identity_uuid.
        # Display composes the ratified "on behalf of" sentence (ADR-580 D4);
        # a raw UUID never rides the authored_by string.
        authored_by=f"{DERIVE_AUTHOR_PREFIX}{plat}",
        author_identity_uuid=connected_by,
        message=(f"derived the {plat} '{selector}' digest "
                 f"({len(bodies)} raw observation{'s' if len(bodies) != 1 else ''})"),
        revision_kind="derivation",
        derived_from=raw_abs,
    )

    try:
        from services.primitives.workspace import _embed_workspace_file
        await _embed_workspace_file(client, user_id, digest_abs, content)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[CONNECTOR_DERIVE] embed failed for %s: %s", digest_abs, exc)

    record_execution_event(
        client, user_id=user_id, slug=slug,
        mode="judgment", trigger_type="scheduled", status="success",
        model=turn.ledger_model, duration_ms=derive_ms,
        funnel_decision="connector-derive",
        principal_id=connected_by or user_id, **turn.usage,
    )
    logger.info("[CONNECTOR_DERIVE] %s/%s → %s (rev %s)",
                user_id[:8], slug, digest_abs, revision_id[:8])
    return {"success": True, "platform": plat, "selector": selector,
            "digest_path": digest_abs, "revision_id": revision_id}




__all__ = [
    "DERIVE_AUTHOR_PREFIX",
    "DERIVE_MIN_INTERVAL_HOURS",
    "NO_CHANGE_SENTINEL",
    "build_connector_derive_posture",
    "digest_path",
    "is_due",
    "parse_stamp",
    "run_connector_derive",
    "strip_provenance_header",
]
