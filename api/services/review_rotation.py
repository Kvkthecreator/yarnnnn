"""Review seat occupant rotation — ADR-211 D4.

The atomic three-step operation that changes who fills the Reviewer seat:

    1. Read current OCCUPANT.md (source of truth for previous occupant)
    2. Write new OCCUPANT.md with new occupant identity + activated_at + config
    3. Append a handoffs.md entry recording from/to/trigger/authorized_by/reason

Per FOUNDATIONS Derived Principle 14 ("Roles persist; occupants rotate"), the
rotation is a SUBSTRATE WRITE, not a dependency injection, not a feature flag.
The seat's occupant is whatever OCCUPANT.md says it is; rotation is the act
of changing what OCCUPANT.md says. Nothing else needs to change in code.

Per ADR-211 D4 triggers:
  - operator-initiated (primary) — via chat with YARNNN, authored_by = user
  - system-scaffold — signup only, authored_by = system (lives in workspace_init)
  - system-fallback — deferred (requires calibration data; out of Phase 4 main)

Per ADR-211 D4 authorization:
  - operator may rotate freely between occupant classes they have access to
  - impersonated:* requires users.can_impersonate (schema check — out of
    this module's scope; callers enforce)
  - external:* requires provisioned adapter — no adapters ship in Phase 4,
    so external rotations are accepted structurally but no dispatch path
    exists for them

No ABC, no interface, no plugin protocol. Rotation is a file write.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from services.workspace_paths import REVIEW_OCCUPANT_PATH, REVIEW_HANDOFFS_PATH

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Occupant-class taxonomy (mirrors reviewer-substrate.md §OCCUPANT.md)
# -----------------------------------------------------------------------------
_OCCUPANT_PREFIXES = ("human:", "ai:", "external:", "impersonated:")


def is_valid_occupant_identity(identity: str) -> bool:
    """Validate an occupant identity string against the canonical taxonomy.

    Accepts:
        human:<user_id>
        ai:<model>-<version>
        external:<service>-<identifier>
        impersonated:<admin_user_id>-as-<persona_slug>
    """
    if not identity or not isinstance(identity, str):
        return False
    if not any(identity.startswith(p) for p in _OCCUPANT_PREFIXES):
        return False
    # After the prefix there must be at least one character
    _, _, rest = identity.partition(":")
    return bool(rest.strip())


def occupant_class(identity: str) -> str | None:
    """Return the occupant class (prefix) of an identity, or None if invalid."""
    if not is_valid_occupant_identity(identity):
        return None
    return identity.split(":", 1)[0]


# -----------------------------------------------------------------------------
# Current-occupant read
# -----------------------------------------------------------------------------

async def read_current_occupant(um: Any) -> dict[str, Any]:
    """Read OCCUPANT.md and return the parsed frontmatter + narrative.

    Returns a dict with:
        occupant: str  (current occupant identity)
        occupant_class: str  (human | ai | external | impersonated)
        activated_at: str  (ISO-8601)
        activated_by: str  (system | human:<user_id>)
        config: dict  (occupant-class-specific config)
        raw: str  (raw file content — preserved for writing narrative)

    Returns an empty-occupant dict if file missing or unparseable.
    Never raises.
    """
    try:
        content = await um.read(REVIEW_OCCUPANT_PATH)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[REVIEW_ROTATION] OCCUPANT.md read failed: %s", exc)
        content = None

    if not content:
        return _empty_occupant_dict()

    try:
        return _parse_occupant_md(content)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[REVIEW_ROTATION] OCCUPANT.md parse failed; returning empty: %s",
            exc,
        )
        return _empty_occupant_dict()


def _empty_occupant_dict() -> dict[str, Any]:
    return {
        "occupant": "",
        "occupant_class": "",
        "activated_at": "",
        "activated_by": "",
        "config": {},
        "raw": "",
    }


def _parse_occupant_md(content: str) -> dict[str, Any]:
    """Parse OCCUPANT.md YAML frontmatter. Minimal parser — no PyYAML dep."""
    parsed = _empty_occupant_dict()
    parsed["raw"] = content

    # Locate YAML frontmatter between leading `---` and next `---`
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?", content, flags=re.DOTALL)
    if not m:
        return parsed

    frontmatter = m.group(1)
    # Line-by-line key: value (one level deep for config dict)
    in_config = False
    config: dict[str, Any] = {}

    for raw_line in frontmatter.split("\n"):
        line = raw_line.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue

        if line.startswith(("  ", "\t")) and in_config:
            km = re.match(r"^\s+([a-z][a-z0-9_]*)\s*:\s*(.+?)\s*$", line)
            if km:
                config[km.group(1)] = km.group(2).strip()
            continue

        in_config = False
        km = re.match(r"^([a-z][a-z0-9_]*)\s*:\s*(.*?)\s*$", line)
        if not km:
            continue
        key, raw_value = km.group(1), km.group(2)

        if key == "config":
            # Either empty {} or nested block
            if raw_value.strip() in ("{}", ""):
                config = {}
            in_config = raw_value.strip() not in ("{}",)
            continue

        if key in ("occupant", "occupant_class", "activated_at", "activated_by"):
            parsed[key] = raw_value.strip().strip('"\'')

    parsed["config"] = config

    # Derive occupant_class from identity if missing
    if not parsed["occupant_class"] and parsed["occupant"]:
        oc = occupant_class(parsed["occupant"])
        if oc:
            parsed["occupant_class"] = oc

    return parsed


# -----------------------------------------------------------------------------
# The rotation primitive — three-step atomic operation
# -----------------------------------------------------------------------------

async def rotate_occupant(
    um: Any,
    new_occupant_identity: str,
    *,
    authorized_by: str,
    trigger: str,
    reason: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Rotate the Reviewer seat to a new occupant.

    Per ADR-211 D4, a rotation is a three-step atomic operation:
      1. Read current OCCUPANT.md (source of truth for previous occupant)
      2. Write new OCCUPANT.md
      3. Append handoffs.md entry

    Args:
        um: UserMemory (or equivalent) workspace handle with `.read()` and
            `.write()` async methods operating on workspace paths.
        new_occupant_identity: identity string matching the canonical taxonomy
            (human:<uid> | ai:<model>-<ver> | external:<svc>-<id> | impersonated:<a>-as-<p>).
        authorized_by: identity of who authorized this rotation
            (system | human:<user_id>). Distinct from the new occupant.
        trigger: short machine-readable tag — signup, operator_command,
            system_fallback, impersonation_activated, etc.
        reason: optional operator-provided rationale for the handoff log.
        config: occupant-class-specific configuration (e.g., for ai:* this
            might include confidence_threshold, model parameters).

    Returns a dict:
        {
            "rotated": bool,  # True if state actually changed
            "from": str,      # previous occupant identity (empty on first scaffold)
            "to": str,        # new occupant identity
            "at": str,        # ISO-8601 timestamp of the rotation
            "reason": str,    # human-readable description of what happened
        }

    Never raises. On validation failure or write failure returns rotated=False
    with reason populated.
    """
    # Validate the target
    if not is_valid_occupant_identity(new_occupant_identity):
        return {
            "rotated": False,
            "from": "",
            "to": new_occupant_identity,
            "at": "",
            "reason": f"invalid occupant identity '{new_occupant_identity}' — must match human:<id> | ai:<model>-<ver> | external:<svc>-<id> | impersonated:<a>-as-<p>",
        }

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # 1. Read current occupant
    current = await read_current_occupant(um)
    previous_identity = current.get("occupant") or ""

    # Short-circuit: same occupant, same config — no rotation needed
    if previous_identity == new_occupant_identity and (config or {}) == current.get("config", {}):
        return {
            "rotated": False,
            "from": previous_identity,
            "to": new_occupant_identity,
            "at": current.get("activated_at") or now,
            "reason": "occupant already active with matching config — no rotation",
        }

    oc = occupant_class(new_occupant_identity) or ""

    # 2. Write new OCCUPANT.md
    new_content = _render_occupant_md(
        occupant=new_occupant_identity,
        occupant_class=oc,
        activated_at=now,
        activated_by=authorized_by,
        config=config or {},
    )
    try:
        await um.write(
            REVIEW_OCCUPANT_PATH,
            new_content,
            summary=f"Rotate Reviewer seat: {previous_identity or '(none)'} → {new_occupant_identity}",
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("[REVIEW_ROTATION] OCCUPANT.md write failed: %s", exc)
        return {
            "rotated": False,
            "from": previous_identity,
            "to": new_occupant_identity,
            "at": now,
            "reason": f"OCCUPANT.md write failed: {exc}",
        }

    # 3. Append handoffs.md entry
    entry = _render_handoff_entry(
        ts=now,
        from_identity=previous_identity,
        to_identity=new_occupant_identity,
        trigger=trigger,
        authorized_by=authorized_by,
        reason=reason,
    )
    try:
        existing_handoffs = await um.read(REVIEW_HANDOFFS_PATH) or ""
        new_handoffs = (existing_handoffs.rstrip() + "\n\n" + entry + "\n") if existing_handoffs else entry + "\n"
        await um.write(
            REVIEW_HANDOFFS_PATH,
            new_handoffs,
            summary=f"Handoff: {previous_identity or '(none)'} → {new_occupant_identity} ({trigger})",
        )
    except Exception as exc:  # noqa: BLE001
        # OCCUPANT.md already updated — handoff log is advisory but important.
        # Log the failure; return rotated=True (the seat IS rotated) with a
        # warning in reason.
        logger.error("[REVIEW_ROTATION] handoffs.md append failed: %s", exc)
        return {
            "rotated": True,
            "from": previous_identity,
            "to": new_occupant_identity,
            "at": now,
            "reason": f"rotated but handoff log append failed: {exc}",
        }

    logger.info(
        "[REVIEW_ROTATION] rotated user seat: %s → %s (trigger=%s, authorized_by=%s)",
        previous_identity or "(none)",
        new_occupant_identity,
        trigger,
        authorized_by,
    )

    return {
        "rotated": True,
        "from": previous_identity,
        "to": new_occupant_identity,
        "at": now,
        "reason": f"rotated {previous_identity or '(none)'} → {new_occupant_identity} (trigger={trigger})",
    }


# -----------------------------------------------------------------------------
# Rendering helpers
# -----------------------------------------------------------------------------

def _render_occupant_md(
    *,
    occupant: str,
    occupant_class: str,
    activated_at: str,
    activated_by: str,
    config: dict[str, Any],
) -> str:
    """Render OCCUPANT.md content with the given frontmatter."""
    config_block = "config: {}"
    if config:
        config_lines = ["config:"]
        for k, v in config.items():
            config_lines.append(f"  {k}: {v}")
        config_block = "\n".join(config_lines)

    frontmatter = (
        f"---\n"
        f"occupant: {occupant}\n"
        f"occupant_class: {occupant_class}\n"
        f"activated_at: {activated_at}\n"
        f"activated_by: {activated_by}\n"
        f"{config_block}\n"
        f"---\n"
    )
    body = (
        "\n"
        "# Review Seat — Current Occupant\n"
        "\n"
        "This file declares who currently fills the Reviewer seat. The seat is\n"
        "the architectural role (see `IDENTITY.md`); the **occupant** is who\n"
        "fills it right now. Per FOUNDATIONS Derived Principle 14, the seat\n"
        "persists and the occupant rotates.\n"
        "\n"
        "Rotation is a substrate write, not a code change. Change the\n"
        "`occupant:` field in the frontmatter (via chat with YARNNN or by\n"
        "direct edit) to rotate. Every rotation appends to `handoffs.md`.\n"
        "\n"
        "Occupant-class taxonomy:\n"
        "- `human:<user_id>` — the operator via approval UX\n"
        "- `ai:<model>-<version>` — a YARNNN-internal AI reviewer\n"
        "- `external:<service>-<identifier>` — an external AI service via adapter\n"
        "- `impersonated:<admin>-as-<persona>` — admin alpha-stress-testing\n"
    )
    return frontmatter + body


def _render_handoff_entry(
    *,
    ts: str,
    from_identity: str,
    to_identity: str,
    trigger: str,
    authorized_by: str,
    reason: str | None,
) -> str:
    """Render a handoffs.md log entry."""
    lines = [
        f"## {ts} — {trigger}",
        "",
        f"- **From**: `{from_identity}`" if from_identity else "- **From**: (none)",
        f"- **To**: `{to_identity}`",
        f"- **Trigger**: {trigger}",
        f"- **Authorized by**: {authorized_by}",
    ]
    if reason:
        lines.append(f"- **Reason**: {reason}")
    lines.append(f"- **Decisions.md range**: from {ts} onward")
    return "\n".join(lines)
