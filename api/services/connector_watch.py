"""Connector watch declarations — the Phase-2 (Select) substrate (ADR-392 D7).

A platform connection is a PERIPHERAL (ADR-389); which channels/pages/labels
of it are in the operation's perception aperture is a DECLARATION (DP27 — watches
are declared, never crawled), the peripheral analogue of the web-source
`_sources.yaml` (ADR-336). The four-phase connector lane (ADR-392 D1):

    1 Connect  — OAuth (platform_connections row)
    2 Select   — THIS: an operator-authored watch declaration
    3 Capture  — SyncPlatformState(capture=...) reads the declaration, mirrors
                 the selected slices' raw into inbound/{platform}/{selector}/
    4 Derive   — a separate act distils into operation/, citing the raw

The declaration lives at a KERNEL-UNIVERSAL path (connectors are not bundle-
scoped; ADR-353 §15.2 — read_slack/write_slack are `orchestration.py::CAPABILITIES`,
`feeds: context|action`):

    operation/_connectors/{platform}/_watch.yaml

`_`-prefixed → machine-parsed (ADR-254). Operator/steward-authored config; the
capture recurrence reads it. Shape (mirrors `_sources.yaml`):

    selections:
      - id: C0123ABC          # channel/page/label/repo id (the SELECTOR)
        name: "#daily-work"    # display (optional)
        selected: true         # in/out toggle
      - id: C0456DEF
        name: "#random"
        selected: false

`selected: true` entries are what Phase 3 walks. This module is the single
read/write home for the declaration — the API writes it from the selection UI
(D7 FE), the capture recurrence reads it.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)


CONNECTOR_WATCH_ROOT = "operation/_connectors"


def watch_declaration_path(platform: str) -> str:
    """The workspace-relative path of a platform's connector-watch declaration."""
    plat = (platform or "").strip().lower()
    return f"{CONNECTOR_WATCH_ROOT}/{plat}/_watch.yaml"


def _serialize(selections: list[dict]) -> str:
    """Render the declaration yaml (operator-readable, machine-parseable)."""
    return yaml.safe_dump(
        {"selections": selections},
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
    )


async def write_selection(
    client: Any,
    user_id: str,
    platform: str,
    selections: list[dict],
    *,
    authored_by: str = "operator",
) -> str:
    """Author the connector-watch declaration for a platform (ADR-392 D7 Phase 2).

    `selections` is a list of {id, name?, selected} dicts — the operator's
    in/out choice over the platform's discovered resources. Written via the
    single write path (ADR-209) at the kernel-universal declaration path.

    Returns the path written. Idempotent-friendly: a re-write with identical
    content is diff-skipped by the substrate layer.
    """
    from services.workspace import UserMemory

    path = watch_declaration_path(platform)
    # Normalize: keep only the load-bearing fields, coerce selected→bool.
    normalized = [
        {
            "id": str(s.get("id", "")).strip(),
            "name": (s.get("name") or "").strip() or None,
            "selected": bool(s.get("selected", False)),
        }
        for s in (selections or [])
        if str(s.get("id", "")).strip()
    ]
    content = _serialize(normalized)
    um = UserMemory(client, user_id)
    await um.write(
        path,
        content,
        summary=f"connector-watch:{platform}",
        authored_by=authored_by,
        message=f"select {platform} sources ({sum(1 for s in normalized if s['selected'])} in scope)",
    )
    logger.debug("[CONNECTOR_WATCH] wrote %s (%d selections)", path, len(normalized))
    return path


async def read_selection(
    client: Any,
    user_id: str,
    platform: str,
) -> list[dict]:
    """Read a platform's connector-watch declaration (all selections).

    Returns the full selections list (both in- and out-of-scope). Empty list
    when the declaration does not exist yet. Never raises.
    """
    from services.workspace import UserMemory

    path = watch_declaration_path(platform)
    um = UserMemory(client, user_id)
    try:
        body = await um.read(path)
    except Exception:
        body = None
    if not body:
        return []
    try:
        parsed = yaml.safe_load(body) or {}
    except Exception as exc:  # noqa: BLE001
        logger.warning("[CONNECTOR_WATCH] parse failed for %s: %s", path, exc)
        return []
    selections = parsed.get("selections")
    return selections if isinstance(selections, list) else []


async def read_selected_ids(
    client: Any,
    user_id: str,
    platform: str,
) -> list[str]:
    """The `selected: true` selector ids — what Phase 3 (Capture) walks.

    This is the consumer surface: SyncPlatformState's capture recurrence reads
    these to know which channels/pages/labels to mirror into inbound/{platform}/.
    """
    selections = await read_selection(client, user_id, platform)
    return [
        str(s["id"]).strip()
        for s in selections
        if isinstance(s, dict) and s.get("selected") and str(s.get("id", "")).strip()
    ]


# ---------------------------------------------------------------------------
# Seed-at-select — the connector capture declaration (ADR-394 D2)
#
# Connectors are KERNEL-UNIVERSAL (a bare workspace connects Slack with no
# bundle), so their capture declaration can't ship in a bundle. But *whether*
# to capture a selected channel has no judgment in it — the capture is a
# deterministic function of (platform, selected ids). So the declaration is
# SEEDED at select-time: when the operator saves a watch with ≥1 selection, we
# idempotently upsert a `capture-{platform}` entry into /workspace/_captures.yaml
# naming CaptureConnector; a deselect-to-empty pauses it. Deterministic Python,
# zero LLM, no new primitive (ADR-394 §2 D2 — NOT a captures-authoring primitive).
# ---------------------------------------------------------------------------

# Per-platform read-tool binding: how CaptureConnector reads each platform's
# selected slices. Kernel-universal (beside orchestration.py::CAPABILITIES'
# read_slack/read_notion/read_github), NOT bundle-scoped. Slack is the first
# connector with a selection UI; Notion/GitHub bindings land with their UIs
# (ADR-394 §6). A platform absent from this table has no seedable capture yet.
CONNECTOR_CAPTURE_BINDINGS: dict[str, dict] = {
    "slack": {
        "read_tool": "platform_slack_get_channel_history",
        "selector_arg": "channel_id",
        "tool_args": {"limit": 50},
        # Kernel default cadence for chat-channel freshness; operator-tunable
        # later by editing _captures.yaml directly. 15 min balances freshness
        # against per-channel API volume.
        "schedule": "@every 15min",
        "display_name": "Slack Channel Capture",
    },
}


def connector_capture_slug(platform: str) -> str:
    """The stable capture slug for a platform's connector capture."""
    return f"capture-{(platform or '').strip().lower()}"


def _build_capture_primitive(platform: str, binding: dict) -> str:
    """Render the `@primitive: CaptureConnector(...)` directive for a platform."""
    import json as _json

    args = [
        f'platform="{platform}"',
        f'read_tool="{binding["read_tool"]}"',
        f'selector_arg="{binding["selector_arg"]}"',
    ]
    tool_args = binding.get("tool_args")
    if tool_args:
        # Compact JSON is valid YAML flow-mapping — the lane's directive parser
        # (services.capture.lane.parse_primitive_directive) handles it.
        args.append(f"tool_args={_json.dumps(tool_args)}")
    joined = ",\n        ".join(args)
    return f"@primitive: CaptureConnector(\n        {joined}\n      )\n"


async def seed_connector_capture(
    client: Any,
    user_id: str,
    platform: str,
    *,
    selected_count: int,
) -> Optional[str]:
    """Idempotently ensure the connector capture declaration (ADR-394 D2).

    Called from the PUT-selection route after the watch declaration is written.
    Upserts a `capture-{platform}` entry into /workspace/_captures.yaml naming
    CaptureConnector, then materializes the capture index so the drainer sees
    it. When `selected_count == 0` the entry is PAUSED (kept for legibility —
    "watched, nothing in scope" — but the scheduler leaves next_run_at None).

    Single-writer (ADR-286): this is the sole writer of `capture-{platform}`
    slugs. Bundle-shipped capture entries (other slugs) are never touched — the
    upsert replaces only the connector slug in the parsed list.

    Returns the slug touched, or None when the platform has no capture binding
    (Notion/GitHub before their UIs ship) — a no-op, not an error. Best-effort:
    the caller wraps this so a seed failure never fails the selection save.
    """
    from services.workspace import UserMemory
    from services.conventions import CAPTURES_PATH
    from services.capture.scheduling import materialize_capture_index

    plat = (platform or "").strip().lower()
    binding = CONNECTOR_CAPTURE_BINDINGS.get(plat)
    if not binding:
        logger.debug(
            "[CONNECTOR_CAPTURE] no capture binding for %s — nothing to seed", plat
        )
        return None

    slug = connector_capture_slug(plat)
    rel = CAPTURES_PATH.lstrip("/").removeprefix("workspace/")
    um = UserMemory(client, user_id)

    # Read the current _captures.yaml (empty for a bare workspace, or a forked
    # bundle's file). Parse to a list of entry dicts; replace/insert only OUR
    # slug; re-serialize. We keep the raw entry dicts (not CaptureDeclaration)
    # so bundle entries round-trip byte-for-byte.
    try:
        body = await um.read(rel)
    except Exception:
        body = None

    entries: list[dict] = []
    if body and body.strip():
        try:
            parsed = yaml.safe_load(body) or {}
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[CONNECTOR_CAPTURE] _captures.yaml parse failed for %s: %s — "
                "refusing to seed (would clobber unparseable operator file)",
                user_id[:8], exc,
            )
            return None
        if isinstance(parsed, dict):
            existing = parsed.get("captures") or parsed.get("entries") or []
        elif isinstance(parsed, list):
            existing = parsed
        else:
            existing = []
        entries = [e for e in existing if isinstance(e, dict)]

    our_entry = {
        "slug": slug,
        "schedule": binding["schedule"],
        "primitive": _build_capture_primitive(plat, binding),
        "display_name": binding.get("display_name", f"{plat.title()} Capture"),
    }
    # Deselect-to-empty pauses (kept for legibility, scheduler skips it).
    if selected_count <= 0:
        our_entry["paused"] = True

    # Replace our slug if present, else append — leaving all other entries intact.
    replaced = False
    new_entries: list[dict] = []
    for e in entries:
        if e.get("slug") == slug:
            new_entries.append(our_entry)
            replaced = True
        else:
            new_entries.append(e)
    if not replaced:
        new_entries.append(our_entry)

    content = yaml.safe_dump(
        {"captures": new_entries},
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
    )
    await um.write(
        rel,
        content,
        summary=f"connector-capture:{plat}",
        authored_by="system:connector-seed",
        message=(
            f"{'pause' if selected_count <= 0 else 'seed'} {slug} "
            f"({selected_count} selected)"
        ),
    )

    # Materialize the capture index so the drainer sees the new/updated row.
    try:
        await materialize_capture_index(client, user_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[CONNECTOR_CAPTURE] materialize_capture_index failed for %s/%s: %s",
            user_id[:8], slug, exc,
        )

    logger.info(
        "[CONNECTOR_CAPTURE] %s %s (%d selected) for %s",
        "paused" if selected_count <= 0 else "seeded", slug, selected_count,
        user_id[:8],
    )
    return slug


async def remove_connector_capture(
    client: Any,
    user_id: str,
    platform: str,
) -> Optional[str]:
    """Remove the connector's capture declaration on disconnect (ADR-401 D3).

    The teardown counterpart of `seed_connector_capture` — the same single
    writer of `capture-{platform}` slugs (ADR-286). Disconnect deletes the
    connection row (credentials); the capture entry is MACHINE state and is
    removed with it (a permanently-skipping entry is an orphan, not a pause;
    seed-at-select recreates it on reconnect+select). The operator-authored
    `_watch.yaml` declaration and the `inbound/` raw are deliberately KEPT —
    the declaration makes reconnect restore perception without re-declaring,
    and raw ages out mechanically under the retention GC (D4).

    Not gated on CONNECTOR_CAPTURE_BINDINGS — the entry is removed by slug
    regardless, so a platform whose binding was later retired still tears
    down cleanly. Returns the slug removed, or None when there was nothing
    to remove (missing file / absent entry / unparseable file — all no-ops;
    unparseable is left untouched, same refusal as the seed). Best-effort:
    the caller wraps this so a teardown failure never fails the disconnect.
    """
    from services.workspace import UserMemory
    from services.conventions import CAPTURES_PATH
    from services.capture.scheduling import materialize_capture_index

    plat = (platform or "").strip().lower()
    slug = connector_capture_slug(plat)
    rel = CAPTURES_PATH.lstrip("/").removeprefix("workspace/")
    um = UserMemory(client, user_id)

    try:
        body = await um.read(rel)
    except Exception:
        body = None
    if not body or not body.strip():
        return None

    try:
        parsed = yaml.safe_load(body) or {}
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[CONNECTOR_CAPTURE] _captures.yaml parse failed for %s: %s — "
            "refusing teardown (would clobber unparseable operator file)",
            user_id[:8], exc,
        )
        return None

    if isinstance(parsed, dict):
        existing = parsed.get("captures") or parsed.get("entries") or []
    elif isinstance(parsed, list):
        existing = parsed
    else:
        existing = []
    entries = [e for e in existing if isinstance(e, dict)]

    remaining = [e for e in entries if e.get("slug") != slug]
    if len(remaining) == len(entries):
        return None  # nothing to remove

    content = yaml.safe_dump(
        {"captures": remaining},
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
    )
    await um.write(
        rel,
        content,
        summary=f"connector-capture:{plat}",
        authored_by="system:connector-teardown",
        message=f"remove {slug} on {plat} disconnect",
    )

    # Materialize so the index drops the row (declaration no longer exists).
    try:
        await materialize_capture_index(client, user_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[CONNECTOR_CAPTURE] materialize_capture_index failed for %s/%s: %s",
            user_id[:8], slug, exc,
        )

    logger.info("[CONNECTOR_CAPTURE] removed %s for %s", slug, user_id[:8])
    return slug


__all__ = [
    "CONNECTOR_WATCH_ROOT",
    "watch_declaration_path",
    "write_selection",
    "read_selection",
    "read_selected_ids",
    "CONNECTOR_CAPTURE_BINDINGS",
    "connector_capture_slug",
    "seed_connector_capture",
    "remove_connector_capture",
]
