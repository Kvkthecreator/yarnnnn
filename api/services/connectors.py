"""Connectors — a connector is a WRITER, not a pipeline (ADR-582).

The whole feature: connect (OAuth) → select slices → attributed observation
files land at the destination on a cadence. Zero LLM, zero judgment, zero
derive obligation on this path. Everything downstream — the digest
(`connector_derive`, opt-in via settings), radar/Strings sources, future
turn-reach — is a CONSUMER, wired separately.

One selection store: ``platform_connections.landscape.selected_sources`` —
the store the selection UI always wrote. The `_watch.yaml` mirror, the
`_captures.yaml` seed-at-select, and the `CaptureConnector` primitive are
DELETED (ADR-582 D2); per-connection knobs live in
``platform_connections.settings["connector"]``:

    {cadence, destination, digest, last_capture_at}

Destination (D3): unset → the intake grammar
``inbound/{platform}/{selector}/{stamp}.{ext}`` (the DEFAULT, not a law).
Filing WITHIN the destination stays deterministic — a peripheral has no
judgment to place with; flexibility is the operator's at wiring time.

Attribution (axioms, unchanged): snapshots are ``system:capture-{platform}``
+ ``revision_kind='observation'`` (the mechanism string ADR-401 D1 named).
The writer NEVER embeds — raw is never ranked into recall, wherever it lands
(visibility keys on the ledger's revision_kind, not the path; ADR-423
finished for this lane).

This module deliberately carries no module-level ``services.*`` imports (the
radar cycle-free property).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Per-platform read bindings — the ENTIRE per-platform "architecture"
# (moved from connector_watch, ADR-582 D2; established ADR-394/401 Phase 4)
# ---------------------------------------------------------------------------

CONNECTOR_CAPTURE_BINDINGS: dict[str, dict] = {
    "slack": {
        "read_tool": "platform_slack_get_channel_history",
        "selector_arg": "channel_id",
        "tool_args": {"limit": 50},
        # 15 min balances chat freshness against per-channel API volume.
        "cadence": "@every 15min",
        "display_name": "Slack Channel Capture",
        # The operator-facing statement of what the read tool above actually
        # does — lives ON the binding so the display cannot drift from it.
        "reads": "channel history (latest 50 messages) from each selected channel",
    },
    "notion": {
        # Landscape selection ids are page UUIDs (landscape.py) — exactly
        # platform_notion_get_page's selector.
        "read_tool": "platform_notion_get_page",
        "selector_arg": "page_id",
        "cadence": "@every 1h",
        "display_name": "Notion Page Capture",
        "reads": "page content from each selected page",
    },
    "github": {
        # Landscape selection ids are owner/repo full names (landscape.py) —
        # exactly platform_github_get_issues' selector. state=all captures
        # the full recent activity picture (opens, closes, merges).
        "read_tool": "platform_github_get_issues",
        "selector_arg": "repo",
        "tool_args": {"state": "all", "limit": 50},
        "cadence": "@every 1h",
        "display_name": "GitHub Repo Capture",
        "reads": "issue and pull-request activity (latest 50, all states) from each selected repo",
    },
}

_PLATFORM_DISPLAY = {"slack": "Slack", "notion": "Notion", "github": "GitHub"}


def connector_does(platform: str) -> Optional[dict]:
    """The three capability facts the detail page states — DERIVED from the
    machinery that enacts them, never a parallel copy that can drift:

      reads  — the capture binding's own statement of its read tool
      writes — whether an exporter is registered for the platform (the only
               write path; operator-initiated, never scheduled)
      agents — the ADR-577 refusal: agents hold no platform credential and
               the lane allowlists exclude platform tools; consumers read
               LANDED files only (ADR-582 D6)

    Facts, not controls — there is no per-tool enforcement point on the
    outbound side to bind dials to (the OAuth scope is the platform's
    control; ours is species-level). None for an unbound platform."""
    plat = (platform or "").strip().lower()
    binding = CONNECTOR_CAPTURE_BINDINGS.get(plat)
    if binding is None:
        return None
    try:
        from integrations.exporters import get_exporter_registry
        can_export = get_exporter_registry().get(plat) is not None
    except Exception:  # noqa: BLE001 — a registry hiccup must not claim a write path
        can_export = False
    name = _PLATFORM_DISPLAY.get(plat, plat)
    try:
        from services.turn_reach import is_turn_reach_enabled
        reach_on = is_turn_reach_enabled()
    except Exception:  # noqa: BLE001
        reach_on = False
    return {
        "reads": binding["reads"],
        "writes": (
            f"only when you export a document to {name} — your action, never scheduled"
            if can_export
            else f"nothing — yarnnn never writes to {name}"
        ),
        # ADR-585: chat turn reach — the member's OWN connection, inside their
        # own turn, read-only and transient. Derived from the deploy flag so
        # the fact flips the day the capability does.
        #
        # D5 (the engine disclosure) is the SECOND sentence, and it lives here
        # rather than on the chat surface for two reasons: this row is already
        # flag-derived (a hand-kept copy at the new-chat door could disagree
        # with the capability it describes), and a standing exposure fact
        # belongs where the connection is GRANTED, not repeated at every
        # conversation until it stops being read. A lane's engine is
        # member-chosen and may be any provider (ADR-558/559), so reaching a
        # connection sends its content there — the same exposure as pasting,
        # which is the comparison that makes it legible.
        "chat": (
            f"your chat can read {name} through your own connection — "
            "read-only, in the turn, nothing saved unless you ask. "
            "What it reads goes to the engine you picked for that chat, "
            "the same as pasting it in"
            if reach_on
            else "chat cannot reach platforms on this deployment"
        ),
        "agents": "no direct platform access — agents read the landed capture files only",
    }

#: Bounded cadence choices (floor 15min) — the guardrail on API volume.
CONNECTOR_CADENCE_CHOICES: tuple = (
    "@every 15min",
    "@every 1h",
    "@every 6h",
    "@every 24h",
)

_CADENCE_SECONDS = {
    "@every 15min": 15 * 60,
    "@every 1h": 3600,
    "@every 6h": 6 * 3600,
    "@every 24h": 24 * 3600,
}

_DEFAULT_SELECTOR = "inbox"


def _slugify_selector(value: str) -> str:
    """One safe path segment from a channel/page/repo id. Mirrors the historic
    inbound sub-lane convention so pre-582 raw and post-582 raw file together
    (lowercase, hyphenated, no slashes — `owner/repo` stays ONE segment)."""
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return s or _DEFAULT_SELECTOR


# ---------------------------------------------------------------------------
# Selection + settings — the one store (ADR-582 D2)
# ---------------------------------------------------------------------------


def selected_ids_from_row(row: dict) -> list[str]:
    """The selected slice ids from a connection row's landscape. Pure."""
    landscape = row.get("landscape") or {}
    selected = landscape.get("selected_sources") or []
    return [
        str(s.get("id")).strip()
        for s in selected
        if isinstance(s, dict) and str(s.get("id", "")).strip()
    ]


def connection_row(client: Any, user_id: str, platform: str) -> Optional[dict]:
    """The platform's connection row (landscape + settings + connected_by),
    or None when unconnected. THE shared row read for consumers that need the
    destination/settings (the digest, Strings' connector sources). Never
    raises."""
    try:
        rows = (
            client.table("platform_connections")
            .select("user_id, platform, landscape, settings, connected_by, status")
            .eq("user_id", user_id)
            .eq("platform", (platform or "").strip().lower())
            .limit(1)
            .execute()
        ).data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[CONNECTORS] connection read failed %s/%s: %s",
                       user_id[:8], platform, exc)
        return None
    return rows[0] if rows else None


async def selected_ids(client: Any, user_id: str, platform: str) -> list[str]:
    """The selected slice ids for a platform — reads the ONE selection store
    (`landscape.selected_sources`). Empty when unconnected or nothing
    selected. Never raises."""
    try:
        rows = (
            client.table("platform_connections")
            .select("landscape")
            .eq("user_id", user_id)
            .eq("platform", (platform or "").strip().lower())
            .limit(1)
            .execute()
        ).data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[CONNECTORS] selection read failed %s/%s: %s",
                       user_id[:8], platform, exc)
        return []
    return selected_ids_from_row(rows[0]) if rows else []


def connector_settings(row: dict) -> dict:
    """The connection's connector-settings object, defaults applied. Pure.

    {cadence, destination, digest, last_capture_at} — cadence defaults to the
    platform binding's; destination None = the intake-grammar default lane;
    digest defaults False (the ADR-582 D5 demotion: derive is opt-in).
    """
    plat = (row.get("platform") or "").strip().lower()
    binding = CONNECTOR_CAPTURE_BINDINGS.get(plat, {})
    raw = ((row.get("settings") or {}).get("connector")) or {}
    cadence = raw.get("cadence")
    if cadence not in CONNECTOR_CADENCE_CHOICES:
        cadence = binding.get("cadence", "@every 1h")
    dest = raw.get("destination")
    dest = dest.strip().strip("/") if isinstance(dest, str) and dest.strip() else None
    return {
        "cadence": cadence,
        "destination": dest,
        "digest": bool(raw.get("digest", False)),
        "last_capture_at": raw.get("last_capture_at"),
    }


def _validate_destination(value: Any) -> Optional[str]:
    """Normalize + validate an operator destination folder. None/empty → None
    (the intake-grammar default lane). ValueError on a shape that could escape
    the workspace or break the deterministic per-selector filing."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("destination must be a folder path string")
    dest = value.strip().strip("/")
    if not dest:
        return None
    if len(dest) > 120:
        raise ValueError("destination is too long (max 120 characters)")
    if "\\" in dest or any(ord(c) < 32 for c in dest):
        raise ValueError("destination contains invalid characters")
    if any(seg in ("", ".", "..") for seg in dest.split("/")):
        raise ValueError("destination must be a plain folder path (no . or ..)")
    return dest


def update_connector_settings(
    client: Any, user_id: str, platform: str, patch: dict,
) -> Optional[dict]:
    """Merge a patch into settings["connector"] on the connection row.

    THE validation chokepoint for the three ADR-582 dials — every caller
    (route, scheduler stamp) goes through here, so a knob cannot be stored in
    a shape the walk would misread. Validates cadence against
    CONNECTOR_CADENCE_CHOICES, destination via _validate_destination (both
    ValueError on bad input); coerces digest to bool. Returns the stored
    connector object, or None when the platform is not connected."""
    if "cadence" in patch and patch["cadence"] not in CONNECTOR_CADENCE_CHOICES:
        raise ValueError(
            f"invalid cadence {patch['cadence']!r}; "
            f"choices: {', '.join(CONNECTOR_CADENCE_CHOICES)}"
        )
    if "destination" in patch:
        patch = {**patch, "destination": _validate_destination(patch["destination"])}
    if "digest" in patch:
        patch = {**patch, "digest": bool(patch["digest"])}
    plat = (platform or "").strip().lower()
    rows = (
        client.table("platform_connections")
        .select("id, settings")
        .eq("user_id", user_id)
        .eq("platform", plat)
        .limit(1)
        .execute()
    ).data or []
    if not rows:
        return None
    settings = rows[0].get("settings") or {}
    connector = dict(settings.get("connector") or {})
    connector.update({k: v for k, v in patch.items()})
    settings["connector"] = connector
    client.table("platform_connections").update({"settings": settings}).eq(
        "id", rows[0]["id"]
    ).execute()
    return connector


# ---------------------------------------------------------------------------
# Placement (kernel-deterministic within the operator's chosen destination)
# ---------------------------------------------------------------------------


def capture_destination(platform: str, selector: str, settings: dict) -> str:
    """The workspace-relative directory a slice's snapshots land in.

    Operator-set destination folder when declared; otherwise the intake
    grammar's default lane. Either way the per-selector sub-directory and
    stamped filenames are deterministic — flexibility is at wiring time,
    never at write time (ADR-582 D3)."""
    plat = _slugify_selector(platform)
    sel = _slugify_selector(selector)
    dest = settings.get("destination")
    base = dest if dest else f"inbound/{plat}"
    return f"{base}/{sel}"


def snapshot_path(
    platform: str, selector: str, observed_at: str, settings: dict, ext: str = "md",
) -> str:
    """One snapshot's workspace-relative path: {destination}/{stamp}.{ext}."""
    stamp = (observed_at or "").strip() or "unknown"
    ext = (ext or "md").lstrip(".")
    return f"{capture_destination(platform, selector, settings)}/{stamp}.{ext}"


def parse_stamp(name: str) -> Optional[datetime]:
    """The observed-at instant from a snapshot filename, or None. Tolerates
    both live spellings — `2026-07-03T06:40:31Z` and compact
    `2026-08-17T210044Z`. Pure."""
    stem = name.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    m = re.match(r"^(\d{4}-\d{2}-\d{2})T(\d{2}):?(\d{2}):?(\d{2})Z$", stem)
    if not m:
        return None
    try:
        return datetime.fromisoformat(
            f"{m.group(1)}T{m.group(2)}:{m.group(3)}:{m.group(4)}+00:00"
        )
    except ValueError:
        return None


async def read_landed_snapshots(
    um: Any,
    platform: str,
    selector: str,
    settings: dict,
    *,
    since: Optional[datetime] = None,
    limit: int = 3,
) -> list[tuple[str, datetime]]:
    """The slice's stamped snapshots newer than `since`, oldest→newest, capped
    at the newest `limit`. Returns (workspace-relative path, stamp) pairs.
    THE one reader consumers share (the digest, Strings' connector sources) —
    a consumer reads landed files, never a platform API. Never raises."""
    sub = capture_destination(platform, selector, settings) + "/"
    try:
        names = await um.list(sub)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[CONNECTORS] list %s failed: %s", sub, exc)
        return []
    stamped: list[tuple[str, datetime]] = []
    for n in names or []:
        if not n or n.endswith("/") or "/" in n:
            continue
        at = parse_stamp(n)
        if at is None:
            continue
        if since is not None and at <= since:
            continue
        stamped.append((f"{sub}{n}", at))
    stamped.sort(key=lambda p: p[1])
    return stamped[-max(1, limit):]


# ---------------------------------------------------------------------------
# The capture walk — the scheduler-tick entry point (ADR-582 D4)
# ---------------------------------------------------------------------------


def _cadence_due(settings: dict, now: datetime) -> bool:
    """Whether the connection's capture is due. Pure — the whole cadence law."""
    last = settings.get("last_capture_at")
    if not last:
        return True
    try:
        last_at = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
    except ValueError:
        return True
    interval = _CADENCE_SECONDS.get(settings.get("cadence"), 3600)
    return (now - last_at) >= timedelta(seconds=interval)


class _CaptureAuth:
    """Auth shape for platform-tool calls in the capture walk (the
    `kernel_mirrors._MirrorAuth` precedent)."""

    def __init__(self, user_id: str, client: Any):
        self.user_id = user_id
        self.client = client
        self.caller_identity = "system:connector-capture"


def _serialize_snapshot(payload: Any) -> str:
    """Markdown-friendly serialization: a string body passes through; a
    structured result wraps as YAML frontmatter (the historic snapshot shape,
    kept so pre- and post-582 snapshots diff against each other)."""
    import json

    import yaml

    if isinstance(payload, str):
        return payload
    try:
        fm = yaml.safe_dump(payload, sort_keys=False, default_flow_style=False,
                            allow_unicode=True)
        return f"---\n{fm}---\n"
    except Exception:  # noqa: BLE001
        return json.dumps(payload, indent=2, sort_keys=False, default=str)


async def run_connector_capture(
    client: Any, user_id: str, row: dict, *, observed_at: str,
) -> dict:
    """One connection's capture: loop the selected slices through the platform
    read tool, land diff-aware attributed snapshots at the destination.
    Returns {success, platform, paths_written, paths_skipped, items, error?}.
    Never raises past its own boundary."""
    from services.platform_tools import handle_platform_tool
    from services.workspace import UserMemory

    plat = (row.get("platform") or "").strip().lower()
    binding = CONNECTOR_CAPTURE_BINDINGS.get(plat)
    if binding is None:
        return {"success": True, "platform": plat, "paths_written": [],
                "paths_skipped": [], "items": 0, "skipped": "no_binding"}

    ids = selected_ids_from_row(row)
    if not ids:
        return {"success": True, "platform": plat, "paths_written": [],
                "paths_skipped": [], "items": 0, "skipped": "nothing_selected"}

    settings = connector_settings(row)
    auth = _CaptureAuth(user_id, client)
    um = UserMemory(client, user_id)
    written: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []
    items = 0

    for sel_id in ids:
        call_args = {**(binding.get("tool_args") or {}),
                     binding["selector_arg"]: sel_id}
        try:
            result = await handle_platform_tool(auth, binding["read_tool"], call_args)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{sel_id}:tool_raised")
            logger.warning("[CONNECTORS] %s read %s(%s) raised: %s",
                           plat, binding["read_tool"], sel_id, exc)
            continue
        if not isinstance(result, dict) or not result.get("success", False):
            err = (result or {}).get("error") if isinstance(result, dict) else "tool_failed"
            errors.append(f"{sel_id}:{err}")
            continue

        content = _serialize_snapshot(result.get("result", {}))
        path = snapshot_path(plat, sel_id, observed_at, settings)

        # Diff baseline = the slice's LATEST snapshot (each run stamps a fresh
        # filename, so a same-path compare would never match): an unchanged
        # world writes nothing — no revision noise, no derive food.
        prev = await read_landed_snapshots(um, plat, sel_id, settings, limit=1)
        prev_content = None
        if prev:
            try:
                prev_content = await um.read(prev[-1][0])
            except Exception:  # noqa: BLE001
                prev_content = None
        items += 1
        if prev_content is not None and prev_content == content:
            skipped.append(path)
            continue

        # The writer signs as the mechanism and marks the ledger; it NEVER
        # embeds — raw is keyed, not ranked, wherever the destination is.
        await um.write(
            path,
            content,
            summary=f"capture:{plat}",
            authored_by=f"system:capture-{plat}",
            message=f"captured {plat} '{sel_id}' @ {observed_at}",
            revision_kind="observation",
        )
        written.append(path)

    all_errored = bool(errors) and not written and not skipped
    return {
        "success": not all_errored,
        "platform": plat,
        "paths_written": written,
        "paths_skipped": skipped,
        "items": items,
        "error": ("; ".join(errors[:5]) if all_errored else None),
    }


async def drain_due_connector_captures(client: Any) -> tuple[int, int, int]:
    """Walk active content-platform connections; capture every one whose
    cadence is due. Returns (found, succeeded, failed). Runs inside the
    scheduler's CONNECTOR_CAPTURE_ENABLED block (ADR-404 D2). Never raises."""
    from services.telemetry import record_execution_event

    try:
        conns = (
            client.table("platform_connections")
            .select("id, user_id, platform, landscape, settings, connected_by")
            .eq("status", "active")
            .execute()
        ).data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[CONNECTORS] connections query failed: %s", exc)
        return 0, 0, 0

    now = datetime.now(timezone.utc)
    observed_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    found = succeeded = failed = 0

    for row in conns:
        plat = (row.get("platform") or "").strip().lower()
        user_id = row.get("user_id")
        if not user_id or plat not in CONNECTOR_CAPTURE_BINDINGS:
            continue
        if not selected_ids_from_row(row):
            continue
        settings = connector_settings(row)
        if not _cadence_due(settings, now):
            continue
        found += 1
        try:
            result = await run_connector_capture(client, user_id, row,
                                                 observed_at=observed_at)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            logger.exception("[CONNECTORS] capture raised %s/%s: %s",
                             user_id[:8], plat, exc)
            continue

        ok = bool(result.get("success"))
        succeeded += 1 if ok else 0
        failed += 0 if ok else 1

        # Stamp the cadence clock (even on failure — a dead peripheral must
        # not be hammered at tick frequency; the health signal says why).
        try:
            update_connector_settings(client, user_id, plat,
                                      {"last_capture_at": observed_at})
        except Exception as exc:  # noqa: BLE001
            logger.warning("[CONNECTORS] cadence stamp failed %s/%s: %s",
                           user_id[:8], plat, exc)

        # Health signal — the steward envelope's reader is unchanged.
        try:
            from services.capture.declarations import write_capture_signal
            await write_capture_signal(
                client, user_id, slug=f"capture-{plat}",
                status="ok" if ok else "error",
                observed_at=observed_at,
                items=result.get("items"),
                target=(result.get("paths_written") or [None])[0],
                last_error=(str(result.get("error"))[:500]
                            if result.get("error") else None),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[CONNECTORS] signal write failed %s/%s: %s",
                           user_id[:8], plat, exc)

        record_execution_event(
            client, user_id=user_id, slug=f"capture-{plat}",
            mode="mechanical", trigger_type="capture",
            status="success" if ok else "failed",
            error_reason=None if ok else (result.get("error") or "capture_failed"),
            funnel_decision="capture",
            principal_id=row.get("connected_by") or user_id,
        )

    return found, succeeded, failed


__all__ = [
    "CONNECTOR_CADENCE_CHOICES",
    "CONNECTOR_CAPTURE_BINDINGS",
    "capture_destination",
    "connector_does",
    "connector_settings",
    "drain_due_connector_captures",
    "parse_stamp",
    "read_landed_snapshots",
    "run_connector_capture",
    "selected_ids",
    "selected_ids_from_row",
    "snapshot_path",
    "update_connector_settings",
]
