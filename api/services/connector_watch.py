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


__all__ = [
    "CONNECTOR_WATCH_ROOT",
    "watch_declaration_path",
    "write_selection",
    "read_selection",
    "read_selected_ids",
]
