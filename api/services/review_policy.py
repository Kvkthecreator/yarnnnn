"""Review policy — ADR-211 Phase 4 D2 + D5 + ADR-217 delegation split.

Reads two operator-authored files and provides the gating helpers dispatch
uses to decide whether the current Reviewer occupant may auto-act:

- `/workspace/review/principles.md` — Reviewer-seat framework (operator-
  authored, seat-bound). Narrative posture + decision categories +
  per-domain `high_impact_threshold_cents` (a *principle* about what
  outcomes are significant enough to route to task-level feedback per
  ADR-195 Phase 5). Slow-moving; captures what the operator *believes*
  about good judgment.
- `/workspace/context/_shared/AUTONOMY.md` — Workspace delegation
  declaration (ADR-217, operator-authored, workspace-scoped — NOT
  Reviewer-owned). Per-domain `level` + `ceiling_cents` + `never_auto`
  under a `default:` fallback block. Fast-moving; captures how much
  autonomy the operator *grants* today as calibration accumulates.

The two-file split lives on different axes (principles = Purpose at the
agent level, framework the persona applies; autonomy = Purpose at the
workspace level, operator's delegation ceiling). Principles can *narrow*
autonomy (add defer conditions in the Reviewer agent's reasoning) but
can never *widen* it — the servant can be more conservative than the
master permits, never more permissive.

Public API:

- `load_principles(client, user_id)` — dict keyed by domain, currently
  carries `high_impact_threshold_cents` per domain.
- `load_autonomy(client, user_id)` — dict keyed by domain (including the
  synthetic `default` fallback) with `level`, `ceiling_cents`, `never_auto`.
  Replaces the retired `load_modes()` per ADR-217 D3.
- `autonomy_for_domain(autonomy, context_domain)` — resolves a domain to
  its specific policy, falling back to the `default` block if no
  per-domain override exists.
- `is_eligible_for_auto_approve(autonomy_policy, action_type, estimated_cents,
  reversibility)` — the dispatch gate. Reads AUTONOMY (not principles) —
  auto-approve eligibility is the operator's delegation ceiling.

Parser contract (unchanged structure, widened to handle block-list YAML
and inline `#` comments per the 681368c hardening pass):
- Never raises; on parse failure returns empty policy.
- Recognizes both commented-out (`<!-- ... -->`) and active YAML blocks.
- Only accepts known fields per policy-type. Unknown fields ignored.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from services.workspace_paths import REVIEW_PRINCIPLES_PATH, SHARED_AUTONOMY_PATH

logger = logging.getLogger(__name__)


# Path constants (re-exported for backward-compat; prefer importing from
# workspace_paths directly).
PRINCIPLES_PATH = f"/workspace/{REVIEW_PRINCIPLES_PATH}"
# ADR-217: Autonomy delegation moved from /workspace/review/modes.md to
# /workspace/context/_shared/AUTONOMY.md. Operator-authored workspace
# declaration; the Reviewer reads it but does not own it.
AUTONOMY_PATH = f"/workspace/{SHARED_AUTONOMY_PATH}"


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
# AUTONOMY.md — operator's delegation declaration (ADR-217)
# -----------------------------------------------------------------------------
#: Known per-domain keys parseable from AUTONOMY.md. Shorter names than the
#: retired modes.md schema — the file's scope narrowed to pure delegation.
#: `scope` (redundant with the domain key itself) and `on_behalf_posture`
#: (Reviewer's verdict presentation derives from IDENTITY + principles,
#: not a separate axis) were dropped per ADR-217 D3.
_KNOWN_AUTONOMY_KEYS = {
    "level",          # manual | assisted | bounded_autonomous | autonomous
    "ceiling_cents",  # int — threshold for bounded_autonomous
    "never_auto",     # list[str] — action_type fragments always deferred
    "paused_until",   # ISO-8601 str — ADR-248 D3: Reviewer-written pause marker
    "pause_reason",   # str — ADR-248 D3: human-readable reason for the pause
}

#: Synthetic domain key the parser treats as the fallback policy. When a
#: proposal's context domain isn't present in AUTONOMY.md, the Reviewer
#: dispatcher uses the `default` block. Matches the AUTONOMY.md
#: authoring shape declared in ADR-217 D2.
_DEFAULT_DOMAIN_KEY = "default"

_VALID_AUTONOMY_LEVELS = {"manual", "assisted", "bounded_autonomous", "autonomous"}


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


def load_autonomy(client: Any, user_id: str) -> dict:
    """Load the operator's delegation declaration from AUTONOMY.md (ADR-217).

    Returns a dict keyed by domain (including the synthetic `default`
    fallback key):
        {"default": {"level": str, "ceiling_cents": int, "never_auto": list[str]},
         "<domain>": {...per-domain override...}, ...}

    Empty dict on missing file, parse failure, or no active delegation.
    Never raises. Replaces the retired load_modes() per ADR-217 D3 —
    autonomy is operator-authored workspace delegation, not Reviewer-
    owned operational config.
    """
    content = _read_file(client, user_id, AUTONOMY_PATH)
    return _parse_keyed_yaml(content, _KNOWN_AUTONOMY_KEYS, "autonomy")


def autonomy_for_domain(autonomy: dict, context_domain: str) -> dict:
    """Return the delegation policy for a domain (ADR-217).

    Resolution order:
      1. Per-domain block under `<context_domain>:` if present.
      2. `default:` fallback block if present.
      3. Empty dict (= manual-by-default under is_eligible_for_auto_approve).

    Equivalent of modes_for_domain() under the retired modes.md schema.
    """
    domain_policy = autonomy.get(context_domain)
    if domain_policy:
        return domain_policy
    return autonomy.get(_DEFAULT_DOMAIN_KEY) or {}


def principles_for_domain(principles: dict, context_domain: str) -> dict:
    """Return the principles for a domain, or empty dict."""
    return principles.get(context_domain) or {}


def should_auto_execute_verdict(
    autonomy_policy: dict,
    verdict: str,
    action_type: str,
    estimated_cents: int | None,
    reversibility: str,
) -> tuple[bool, str]:
    """Post-judgment binding gate (ADR-229 D1).

    Given the Reviewer's verdict and the operator's declared autonomy
    delegation, decide whether the verdict auto-executes (binding) or
    routes to the Queue as advisory (operator clicks).

    This function runs AFTER the Reviewer renders judgment, not before.
    Pre-ADR-229 the function was named `is_eligible_for_auto_approve` and
    ran as a pre-judgment gate that prevented Sonnet from running on
    proposals outside the autonomy ceiling — wasting the Reviewer's
    calibration on the proposals where calibration matters most. Under
    ADR-229 D1, judgment runs first; this gate filters whether the
    judgment binds.

    Returns (should_execute, reason). `verdict` MUST be one of
    "approve" | "reject" | "defer". Non-approve verdicts always return
    `(False, ...)`: reject is the Reviewer's own narrowing (terminal),
    defer routes to the operator (or to a generative followup per D2).
    Only `approve` proceeds through the autonomy filter.

    Per ADR-217 D4, the Reviewer's principles.md can narrow this result
    (the verdict itself may be defer/reject due to narrowing) but never
    widen it. The strictest of (verdict, autonomy ceiling) wins.

    Pre-ADR-229 callers used `is_eligible_for_auto_approve(autonomy_policy,
    action_type, estimated_cents, reversibility)`. That function is
    DELETED — singular implementation rule. New callers must pass the
    verdict; the renamed function is the single binding gate.
    """
    # ADR-248 D3: Reviewer-written pause marker — checked before any other gate.
    # The Reviewer's periodic reflection can write paused_until to AUTONOMY.md when
    # it detects drift. If set and in the future, all proposals route to Queue
    # regardless of level. Expiry is time-based — no second write needed to un-pause.
    paused_until_raw = autonomy_policy.get("paused_until")
    if paused_until_raw:
        try:
            from datetime import timezone as _tz
            from datetime import datetime as _dt
            ts_str = str(paused_until_raw)
            if ts_str.endswith("Z"):
                ts_str = ts_str[:-1] + "+00:00"
            paused_until = _dt.fromisoformat(ts_str)
            if paused_until.tzinfo is None:
                paused_until = paused_until.replace(tzinfo=_tz.utc)
            now_utc = _dt.now(_tz.utc)
            if paused_until > now_utc:
                pause_reason = autonomy_policy.get("pause_reason", "Reviewer-initiated pause")
                return (
                    False,
                    f"autonomy_paused until {paused_until.isoformat()} — {pause_reason}",
                )
            # paused_until is in the past — silently ignore, continue normal gating
        except (ValueError, TypeError):
            pass  # Malformed timestamp — ignore and proceed

    # ADR-229 D1: non-approve verdicts never auto-execute.
    if verdict == "reject":
        return False, "verdict=reject — Reviewer's own narrowing, never auto-executes"
    if verdict == "defer":
        return False, "verdict=defer — Reviewer surfaced to operator (or to generative followup per D2)"
    if verdict != "approve":
        return False, f"verdict={verdict!r} unrecognized — defaulting to non-binding"

    # verdict == "approve" — apply autonomy filter on the Reviewer's approve.

    # Operational gate 1: level must permit auto-action.
    level = autonomy_policy.get("level", "manual")
    if level == "manual":
        return False, "autonomy.level=manual — Reviewer approved, but operator retains every binding decision"
    if level not in _VALID_AUTONOMY_LEVELS:
        return False, f"autonomy.level={level} unrecognized — defaulting to manual"
    # `assisted` = AI recommends, human renders verdict. Not auto-approve.
    if level == "assisted":
        return False, "autonomy.level=assisted — AI recommends, human binds"

    # Operational gate 2: threshold-based (bounded_autonomous) or unbounded (autonomous).
    ceiling = autonomy_policy.get("ceiling_cents")

    if level == "bounded_autonomous":
        if ceiling is None or ceiling <= 0:
            return False, "autonomy.level=bounded_autonomous but no ceiling_cents set"
    # level == "autonomous" — no threshold gate; thresholds apply only to bounded.

    # Operational gate 3: never_auto.
    blocked = autonomy_policy.get("never_auto") or []
    for blocked_fragment in blocked:
        if blocked_fragment and blocked_fragment in action_type:
            return False, f"action_type matches autonomy.never_auto entry '{blocked_fragment}'"

    # Operational gate 4: reversibility (irreversible writes always defer).
    if reversibility == "irreversible":
        return False, "reversibility=irreversible — irreversible writes always route to operator"

    # Operational gate 5: threshold check (bounded_autonomous only).
    if level == "bounded_autonomous":
        if estimated_cents is None:
            return False, "proposal has no estimated value — cannot compare against ceiling"
        if abs(estimated_cents) > ceiling:
            return (
                False,
                f"estimated ${abs(estimated_cents)/100:.2f} exceeds autonomy "
                f"ceiling ${ceiling/100:.2f}",
            )
        return (
            True,
            f"verdict=approve within autonomy ceiling (${abs(estimated_cents)/100:.2f} "
            f"≤ ${ceiling/100:.2f}), reversibility={reversibility}, "
            f"level=bounded_autonomous, action_type not blocked",
        )

    # autonomy == "autonomous"
    # level == "autonomous"
    return (
        True,
        f"verdict=approve, autonomy.level=autonomous for this domain, "
        f"reversibility={reversibility}, action_type not blocked",
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
        if key == "never_auto":
            return [str(item).strip() for item in raw if str(item).strip()]
        return None

    # Integer keys
    if key in ("ceiling_cents", "high_impact_threshold_cents"):
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None
    # List keys (inline form only)
    if key == "never_auto":
        raw = raw.strip()
        if raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1]
            items = [it.strip() for it in inner.split(",") if it.strip()]
            return items
        return [raw]
    # Enum string keys
    if key == "level":
        raw = raw.strip().strip('"\'')
        return raw if raw in _VALID_AUTONOMY_LEVELS else None
    return None
