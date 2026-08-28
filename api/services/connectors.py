"""Connectors — the connection is a RAIL (ADR-594, on ADR-582's writer thesis).

A connection is the set-up that ALLOWS access: consent (OAuth), credential
custody, and the aperture (``landscape.selected_sources`` — which slices may
be read at all). It carries NO placement choice and NO clock. The whole
feature: connect → select slices → attributed observation files land at the
fixed intake grammar WHEN A CONSUMER ASKS. Zero LLM, zero judgment on this
path. Everything downstream — Strings' connector sources, turn reach
(ADR-585) — is a CONSUMER, wired separately.

ADR-591 retired the clock; ADR-594 built the seam's first caller (a string's
run invokes `run_connector_capture` narrowed to its declared selectors —
"reach with a receipt") and DELETED the destination dial: raw lands at

    inbound/{platform}/{selector}/{stamp}.{ext}

as a LAW for this lane, not a default. The raw layer is addressed by
mechanism; meaning lives at the consumer layer (the string's folder, the
derived brief) — never at the landing address. `settings["connector"]` is an
unread fossil key.

One selection store: ``platform_connections.landscape.selected_sources`` —
the store the selection UI always wrote. The `_watch.yaml` mirror, the
`_captures.yaml` seed-at-select, and the `CaptureConnector` primitive are
DELETED (ADR-582 D2).

Attribution (axioms, unchanged): snapshots are ``system:capture-{platform}``
+ ``revision_kind='observation'`` (the mechanism string ADR-401 D1 named).
The writer NEVER embeds — raw is never ranked into recall (visibility keys
on the ledger's revision_kind, not the path; ADR-423 finished for this lane).

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
        # ADR-615 — reach follows the PRINCIPAL, not the surface. An agent
        # working at its desk is the member, present and driving (the lane
        # stamps `member:{id} via {model}`), so it reaches what the member
        # granted and the member scoped it to. This row is flag-derived for
        # the same reason the `chat` row above is: a hand-kept sentence here
        # would outlive the capability it describes — as the pre-615 wording
        # did, asserting a boundary the code stopped drawing.
        #
        # What stays true in BOTH branches, and is the honest half of the old
        # sentence: an unattended standing run reaches nothing live. Those are
        # toolless by construction (`run_bounded_derive_turn`), so a scoped
        # being gains no reach when nobody is present.
        "agents": (
            f"an agent you scope to {name} reads it while you're working with it — "
            "never on its own schedule, where it reads landed files only"
            if reach_on
            else "no direct platform access — agents read the landed capture files only"
        ),
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


def connection_target(platform: str, metadata: Optional[dict]) -> Optional[str]:
    """WHERE this connection points — the Slack workspace, the Notion
    workspace, the GitHub account. Display-only; never an authorization fact.

    Each provider names its target differently and the FE must not have to
    know that: Slack and Notion write `workspace_name`, GitHub writes
    `login`/`name` (it has ACCOUNTS, not workspaces). Reading one key would
    render a blank label for GitHub — which looks like a broken connection
    rather than a different noun. Resolved server-side, once, so the list row
    and the detail header cannot disagree.

    Returns None when nothing identifies the target; callers omit the label
    rather than printing an empty one.
    """
    md = metadata or {}
    for key in ("workspace_name", "team_name", "login", "name", "account_label"):
        value = md.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


# ---------------------------------------------------------------------------
# Placement (kernel-deterministic — the fixed intake grammar, ADR-594 D1)
# ---------------------------------------------------------------------------


def capture_destination(platform: str, selector: str) -> str:
    """The workspace-relative directory a slice's snapshots land in — the
    intake grammar, a LAW for this lane (ADR-594 D1 deleted the per-connection
    destination dial: ADR-423 re-keyed raw-ness to the ledger and ADR-591
    deleted the retention GC, so a chosen destination had no remaining
    behavior; measured zero uses in production, 2026-08-21)."""
    return f"inbound/{_slugify_selector(platform)}/{_slugify_selector(selector)}"


def snapshot_path(
    platform: str, selector: str, observed_at: str, ext: str = "md",
) -> str:
    """One snapshot's workspace-relative path: {lane}/{stamp}.{ext}."""
    stamp = (observed_at or "").strip() or "unknown"
    ext = (ext or "md").lstrip(".")
    return f"{capture_destination(platform, selector)}/{stamp}.{ext}"


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
    *,
    since: Optional[datetime] = None,
    limit: int = 3,
) -> list[tuple[str, datetime]]:
    """The slice's stamped snapshots newer than `since`, oldest→newest, capped
    at the newest `limit`. Returns (workspace-relative path, stamp) pairs.
    THE one reader consumers share (Strings' connector sources) — a consumer
    reads landed files, never a platform API. Never raises."""
    sub = capture_destination(platform, selector) + "/"
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
# The capture writer — invoked by a consumer, never by a clock (ADR-591 D3)
# ---------------------------------------------------------------------------


class _CaptureAuth:
    """Auth shape for platform-tool calls in the capture walk (the
    `kernel_mirrors._MirrorAuth` precedent).

    The credential posture, decided by ADR-594 D2 (the question ADR-591 D3
    deferred): capture executes under the CONNECTION OWNER's OAuth token via
    this non-agent machinery identity. This is NOT the ADR-577 agent
    fall-through — no LLM holds or steers the credential at any point (the
    tool, its arguments, and the write path are fixed by
    CONNECTOR_CAPTURE_BINDINGS), and an invocation executes the composition
    of two standing human declarations: the operator's aperture at the
    connection × the consumer's declared ask (e.g. a string's designation).
    ADR-577's refusal of agent callers is unchanged at its own chokepoint."""

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
    selectors: Optional[list[str]] = None,
) -> dict:
    """One connection's capture: loop the selected slices through the platform
    read tool, land diff-aware attributed snapshots at the fixed intake lane.
    Returns {success, platform, paths_written, paths_skipped, items, error?}.
    Never raises past its own boundary.

    `selectors` (ADR-594 D2) narrows the walk to the INTERSECTION of the
    caller's ask with the connection's aperture — a consumer can narrow the
    operator's consent, never widen it. A declared-but-unselected selector
    captures nothing (the honest empty, with the aperture as the reason)."""
    from services.platform_tools import handle_platform_tool
    from services.workspace import UserMemory

    plat = (row.get("platform") or "").strip().lower()
    binding = CONNECTOR_CAPTURE_BINDINGS.get(plat)
    if binding is None:
        return {"success": True, "platform": plat, "paths_written": [],
                "paths_skipped": [], "items": 0, "skipped": "no_binding"}

    ids = selected_ids_from_row(row)
    if selectors is not None:
        asked = {str(s).strip() for s in selectors if str(s).strip()}
        ids = [i for i in ids if i in asked]
    if not ids:
        return {"success": True, "platform": plat, "paths_written": [],
                "paths_skipped": [], "items": 0, "skipped": "nothing_selected"}

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
        path = snapshot_path(plat, sel_id, observed_at)

        # Diff baseline = the slice's LATEST snapshot (each run stamps a fresh
        # filename, so a same-path compare would never match): an unchanged
        # world writes nothing — no revision noise, no derive food.
        prev = await read_landed_snapshots(um, plat, sel_id, limit=1)
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




__all__ = [
    "connection_target",
    "CONNECTOR_CAPTURE_BINDINGS",
    "capture_destination",
    "connector_does",
    "connection_row",
    "parse_stamp",
    "read_landed_snapshots",
    "run_connector_capture",
    "selected_ids",
    "selected_ids_from_row",
    "snapshot_path",
]
