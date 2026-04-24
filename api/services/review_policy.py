"""Review policy — ADR-211 Phase 4 D2 + D5.

Reads the operator's declared framework and operational modes from the
Reviewer seat's substrate (`/workspace/review/principles.md` and
`/workspace/review/modes.md`), and provides the gating helpers that
dispatch uses to decide whether the current occupant may auto-act.

**Split from the former `review_principles.py`** per ADR-211 D2:

- `principles.md` holds the operator's declared review FRAMEWORK —
  narrative posture + decision category definitions + per-domain
  `high_impact_threshold_cents` (a *principle* about what outcomes
  are significant enough to route to task-level feedback per ADR-195
  Phase 5). Changes slowly; it captures what the operator *believes*.
- `modes.md` holds OPERATIONAL modes — autonomy level × scope ×
  on-behalf posture + per-domain `auto_approve_below_cents` +
  `never_auto_approve`. Changes faster; it captures how much autonomy
  the operator *grants* today as calibration accumulates.

This file parses both and exposes:

- `load_principles(client, user_id)` — dict keyed by domain, currently
  carries `high_impact_threshold_cents` per domain.
- `load_modes(client, user_id)` — dict keyed by domain with the modes
  schema: autonomy_level, scope, on_behalf_posture, auto_approve_below_cents,
  never_auto_approve.
- `is_eligible_for_auto_approve(modes_policy, action_type, estimated_cents,
  reversibility)` — the dispatch gate. Reads MODES (not principles) —
  auto-approve is operational, not principled.

Parser contract (unchanged from the prior `review_principles.py`):
- Never raises; on parse failure returns empty policy.
- Recognizes both commented-out (`<!-- ... -->`) and active YAML blocks.
- Only accepts known fields per policy-type. Unknown fields ignored.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from services.workspace_paths import REVIEW_PRINCIPLES_PATH, REVIEW_MODES_PATH

logger = logging.getLogger(__name__)


# Path constants (re-exported for backward-compat; prefer importing from
# workspace_paths directly).
PRINCIPLES_PATH = f"/workspace/{REVIEW_PRINCIPLES_PATH}"
MODES_PATH = f"/workspace/{REVIEW_MODES_PATH}"


# -----------------------------------------------------------------------------
# principles.md — declared framework keys
# -----------------------------------------------------------------------------
#: Known per-domain keys parseable from principles.md.
_KNOWN_PRINCIPLES_KEYS = {
    # ADR-195 Phase 5: threshold above which reconciled outcomes in this
    # domain route to the originating task's feedback.md as system_outcome
    # entries. Declared as a principle because it expresses *what the
    # operator considers high-impact*, not an operational autonomy gate.
    "high_impact_threshold_cents",
}


# -----------------------------------------------------------------------------
# modes.md — operational configuration keys
# -----------------------------------------------------------------------------
#: Known per-domain keys parseable from modes.md.
_KNOWN_MODES_KEYS = {
    "autonomy_level",       # manual | assisted | bounded_autonomous | autonomous
    "scope",                # list of domain slugs (e.g., [commerce])
    "on_behalf_posture",    # silent_defer | recommend | shortlist
    "auto_approve_below_cents",  # int — operational threshold for auto-act
    "never_auto_approve",        # list[str] — action_type fragments always deferred
}

_VALID_AUTONOMY_LEVELS = {"manual", "assisted", "bounded_autonomous", "autonomous"}
_VALID_POSTURES = {"silent_defer", "recommend", "shortlist"}


# =============================================================================
# Public API
# =============================================================================

def load_principles(client: Any, user_id: str) -> dict:
    """Load the operator's declared review framework from principles.md.

    Returns a dict keyed by domain:
        {"<domain>": {"high_impact_threshold_cents": int, ...}, ...}

    Empty dict on missing file, parse failure, or no active principles.
    Never raises.
    """
    content = _read_file(client, user_id, PRINCIPLES_PATH)
    return _parse_keyed_yaml(content, _KNOWN_PRINCIPLES_KEYS, "principles")


def load_modes(client: Any, user_id: str) -> dict:
    """Load the operator's declared operational modes from modes.md.

    Returns a dict keyed by domain:
        {"<domain>": {
            "autonomy_level": str,
            "scope": list[str],
            "on_behalf_posture": str,
            "auto_approve_below_cents": int,
            "never_auto_approve": list[str],
        }, ...}

    Empty dict on missing file, parse failure, or no active modes.
    Never raises.
    """
    content = _read_file(client, user_id, MODES_PATH)
    return _parse_keyed_yaml(content, _KNOWN_MODES_KEYS, "modes")


def modes_for_domain(modes: dict, context_domain: str) -> dict:
    """Return the modes for a domain, or empty dict (= manual by default)."""
    return modes.get(context_domain) or {}


def principles_for_domain(principles: dict, context_domain: str) -> dict:
    """Return the principles for a domain, or empty dict."""
    return principles.get(context_domain) or {}


def is_eligible_for_auto_approve(
    modes_policy: dict,
    action_type: str,
    estimated_cents: int | None,
    reversibility: str,
) -> tuple[bool, str]:
    """Given a domain's operational modes and a proposal, decide whether the
    AI occupant may auto-act. Reads MODES (not principles) — auto-approve
    is operational config, not declared principle.

    Returns (eligible, reason). Reason is always populated — used in the
    AI occupant's reasoning trail.
    """
    # Operational gate 1: autonomy level must permit auto-action.
    autonomy = modes_policy.get("autonomy_level", "manual")
    if autonomy == "manual":
        return False, "autonomy_level=manual — every verdict defers to human occupant"
    if autonomy not in _VALID_AUTONOMY_LEVELS:
        return False, f"autonomy_level={autonomy} unrecognized — defaulting to manual"
    # `assisted` = AI recommends, human renders verdict. Not auto-approve.
    if autonomy == "assisted":
        return False, "autonomy_level=assisted — AI recommends, human renders verdict"

    # Operational gate 2: threshold-based (bounded_autonomous) or unbounded (autonomous).
    threshold = modes_policy.get("auto_approve_below_cents")

    if autonomy == "bounded_autonomous":
        if threshold is None or threshold <= 0:
            return False, "autonomy_level=bounded_autonomous but no auto_approve_below_cents threshold set"
    # autonomy == "autonomous" — no threshold gate; thresholds apply only to bounded.

    # Operational gate 3: never_auto_approve.
    blocked = modes_policy.get("never_auto_approve") or []
    for blocked_fragment in blocked:
        if blocked_fragment and blocked_fragment in action_type:
            return False, f"action_type matches never_auto_approve entry '{blocked_fragment}'"

    # Operational gate 4: reversibility (irreversible writes always defer).
    if reversibility == "irreversible":
        return False, "reversibility=irreversible — irreversible writes always defer to human"

    # Operational gate 5: threshold check (bounded_autonomous only).
    if autonomy == "bounded_autonomous":
        if estimated_cents is None:
            return False, "proposal has no estimated value — cannot compare against threshold"
        if abs(estimated_cents) > threshold:
            return (
                False,
                f"estimated ${abs(estimated_cents)/100:.2f} exceeds auto_approve "
                f"threshold ${threshold/100:.2f}",
            )
        return (
            True,
            f"within auto_approve threshold (${abs(estimated_cents)/100:.2f} "
            f"≤ ${threshold/100:.2f}), reversibility={reversibility}, "
            f"autonomy=bounded_autonomous, action_type not blocked",
        )

    # autonomy == "autonomous"
    return (
        True,
        f"autonomy_level=autonomous for this domain, reversibility={reversibility}, "
        f"action_type not blocked",
    )


# =============================================================================
# Internal parsing
# =============================================================================

def _read_file(client: Any, user_id: str, path: str) -> str:
    """Read a workspace_files row's content. Empty string on any failure."""
    try:
        result = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", path)
            .limit(1)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[REVIEW_POLICY] load failed path=%s user=%s: %s",
            path, user_id[:8], exc,
        )
        return ""
    rows = result.data or []
    if not rows:
        return ""
    return rows[0].get("content") or ""


def _parse_keyed_yaml(content: str, known_keys: set[str], label: str) -> dict:
    """Parse a minimal YAML-subset from the file, filtered to known keys.

    Format supported:
      <domain>:
        <key>: <scalar>              # inline `# comment` tolerated
        <key>: [a, b, c]             # inline list form
        <list_key>:                  # block list form
          - item1
          - item2

    Both plain and `<!-- ... -->`-commented YAML are parsed — default
    files ship with thresholds commented out; operator uncomments to
    activate. Same behavior both sides of the comment boundary.
    """
    if not content:
        return {}

    cleaned = re.sub(r"<!--(.*?)-->", r"\1", content, flags=re.DOTALL)

    policies: dict[str, dict] = {}
    current_domain: str | None = None
    pending_list_key: str | None = None        # set when we see `<key>:` with no value (block-list start)
    pending_list_indent: int = 0
    pending_list: list[str] = []

    def _flush_pending() -> None:
        nonlocal pending_list_key, pending_list, pending_list_indent
        if pending_list_key and current_domain and pending_list_key in known_keys:
            parsed = _parse_value(pending_list_key, pending_list)
            if parsed is not None:
                policies[current_domain][pending_list_key] = parsed
        pending_list_key = None
        pending_list = []
        pending_list_indent = 0

    for raw_line in cleaned.split("\n"):
        line = raw_line.rstrip()
        stripped = line.strip()

        # Block-list continuation (before blank/comment skip, so we still
        # consume list items and flush when we see a non-list sibling).
        if pending_list_key and stripped.startswith("- "):
            # accept item if indent is deeper than the block-list key's indent
            indent = len(line) - len(line.lstrip())
            if indent > pending_list_indent:
                # strip leading "- " and any trailing inline `#` comment
                item = stripped[2:].split("#", 1)[0].strip().strip('"\'')
                if item:
                    pending_list.append(item)
                continue
            else:
                _flush_pending()

        if not stripped or stripped.startswith("#"):
            if pending_list_key:
                _flush_pending()
            continue

        # Top-level domain declaration
        if not line.startswith((" ", "\t")):
            if pending_list_key:
                _flush_pending()
            m = re.match(r"^([a-z][a-z0-9_\-]*)\s*:\s*$", line)
            if m:
                current_domain = m.group(1)
                policies.setdefault(current_domain, {})
                continue
            current_domain = None
            continue

        # Indented key line within the current domain
        if current_domain is None:
            continue

        # Case A: `<key>:` alone on a line → block-list start
        m_empty = re.match(r"^(\s+)([a-z][a-z0-9_]*)\s*:\s*$", line)
        if m_empty:
            if pending_list_key:
                _flush_pending()
            indent, key = len(m_empty.group(1)), m_empty.group(2)
            if key in known_keys:
                pending_list_key = key
                pending_list_indent = indent
                pending_list = []
            continue

        # Case B: `<key>: <value>` on a single line (strip trailing inline `#` comment)
        m = re.match(r"^\s+([a-z][a-z0-9_]*)\s*:\s*(.+?)\s*$", line)
        if not m:
            continue
        key, raw_value = m.group(1), m.group(2)
        # Drop inline `# ...` comment from scalar value (YAML convention)
        if "#" in raw_value:
            raw_value = raw_value.split("#", 1)[0].rstrip()
        if key not in known_keys:
            continue

        parsed = _parse_value(key, raw_value)
        if parsed is not None:
            policies[current_domain][key] = parsed

    # End-of-content flush (block-list as last thing in file)
    if pending_list_key:
        _flush_pending()

    # Drop domains with no recognized policies
    return {d: p for d, p in policies.items() if p}


def _parse_value(key: str, raw: Any) -> Any:
    """Parse a known key's raw value. Returns None if unparseable.

    `raw` is usually a scalar string from the parser's same-line case,
    but for block-list keys the parser passes a list of items already
    split by the `- ` prefix (see _parse_keyed_yaml).
    """
    # Block-list case: parser handed us the collected list items directly.
    if isinstance(raw, list):
        if key in ("never_auto_approve", "scope"):
            return [str(item).strip() for item in raw if str(item).strip()]
        return None

    # Integer keys
    if key in ("auto_approve_below_cents", "high_impact_threshold_cents"):
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None
    # List keys (inline form only)
    if key in ("never_auto_approve", "scope"):
        raw = raw.strip()
        if raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1]
            items = [it.strip() for it in inner.split(",") if it.strip()]
            return items
        return [raw]
    # Enum string keys
    if key == "autonomy_level":
        raw = raw.strip().strip('"\'')
        return raw if raw in _VALID_AUTONOMY_LEVELS else None
    if key == "on_behalf_posture":
        raw = raw.strip().strip('"\'')
        return raw if raw in _VALID_POSTURES else None
    return None
