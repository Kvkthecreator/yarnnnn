"""Review Principles parser — ADR-194 v2 Phase 3.

Reads `/workspace/review/principles.md` and extracts the per-domain
auto-approve thresholds the operator has declared. Those thresholds
gate whether the AI Reviewer may auto-approve a proposal without
human confirmation.

`principles.md` is **operator-editable** (scaffolded at signup with
thresholds commented out per ADR-194 Phase 1). The file contains:
- free-form markdown narrative describing review posture
- YAML-in-code-block sections (inside `<!-- ... -->` comments or
  fenced blocks) with per-domain thresholds

Per FOUNDATIONS v6.0 Axiom 3 (Purpose — intent lives in substrate),
this file IS the declared review framework. Parsing is never
speculative: if the operator did not declare a threshold, the
default is `auto_approve=False` — safe default, seat defers to human.

Parser contract:
- Never raises; on parse failure returns empty policy (everything defers).
- Recognizes both commented-out (`<!-- ... -->`) and active YAML blocks —
  principals.md ships with commented-out defaults the operator uncomments
  to activate them.
- Only accepts known fields (`auto_approve_below_cents`, `never_auto_approve`).
  Unknown fields are ignored, not errored — forward-compatible with future
  policy additions.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


PRINCIPLES_PATH = "/workspace/review/principles.md"


#: Known per-domain policy keys. Unknown keys under a domain are ignored.
_KNOWN_POLICY_KEYS = {
    "auto_approve_below_cents",
    "never_auto_approve",
    # ADR-195 Phase 5: threshold above which reconciled outcomes in this
    # domain route to the originating task's feedback.md as system_outcome
    # entries. Not set / <=0 → no high-impact entries written.
    "high_impact_threshold_cents",
}


def load_principles(client: Any, user_id: str) -> dict:
    """Load the operator's declared review framework.

    Returns a dict of shape:
      {
          "<domain-slug>": {
              "auto_approve_below_cents": int | None,
              "never_auto_approve": list[str],  # action_type fragments
          },
          ...
      }

    Empty dict on missing file, parse failure, or no active policies.
    Never raises.
    """
    try:
        result = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", PRINCIPLES_PATH)
            .limit(1)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[REVIEW_PRINCIPLES] load failed for user=%s: %s", user_id[:8], exc,
        )
        return {}

    rows = result.data or []
    if not rows:
        return {}
    content = rows[0].get("content") or ""
    return parse_principles_md(content)


def parse_principles_md(content: str) -> dict:
    """Parse principles.md content into a policy dict.

    Tolerates commented-out YAML (ships that way by default) and
    active YAML. Ignores narrative prose.
    """
    if not content:
        return {}

    # Strip HTML comments (`<!-- ... -->`) that may wrap the YAML block.
    # The default scaffold ships thresholds commented-out; operators
    # activate them by uncommenting. Both states are parseable.
    cleaned = re.sub(r"<!--(.*?)-->", r"\1", content, flags=re.DOTALL)

    # Now scan for top-level domain keys. Format is a minimal YAML
    # subset, parsed line-by-line — no PyYAML dep required. Shape:
    #   <domain>:
    #     auto_approve_below_cents: <int>
    #     never_auto_approve: [<action>, <action>]
    policies: dict[str, dict] = {}
    current_domain: str | None = None

    for raw_line in cleaned.split("\n"):
        line = raw_line.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue

        # Top-level domain declaration: "domain:" at column 0 (no leading whitespace)
        # The domain key is a kebab-case or snake_case slug, no colons inside.
        if not line.startswith((" ", "\t")):
            m = re.match(r"^([a-z][a-z0-9_\-]*)\s*:\s*$", line)
            if m:
                current_domain = m.group(1)
                policies.setdefault(current_domain, {})
                continue
            # Anything else at column 0 that isn't a domain header — resets context
            current_domain = None
            continue

        # Indented key: value within the current domain
        if current_domain is None:
            continue
        m = re.match(r"^\s+([a-z][a-z0-9_]*)\s*:\s*(.+?)\s*$", line)
        if not m:
            continue
        key, raw_value = m.group(1), m.group(2)
        if key not in _KNOWN_POLICY_KEYS:
            continue

        parsed = _parse_value(key, raw_value)
        if parsed is not None:
            policies[current_domain][key] = parsed

    # Drop domains with no recognized policies
    return {d: p for d, p in policies.items() if p}


def _parse_value(key: str, raw: str) -> Any:
    """Parse a known key's raw value. Returns None if unparseable."""
    if key in ("auto_approve_below_cents", "high_impact_threshold_cents"):
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None
    if key == "never_auto_approve":
        # Accept bracketed list: [a, b, c]
        raw = raw.strip()
        if raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1]
            items = [it.strip() for it in inner.split(",") if it.strip()]
            return items
        # Fallback: single value
        return [raw]
    return None


def policy_for_domain(policies: dict, context_domain: str) -> dict:
    """Return the policy for a domain, or empty dict (= no auto-approve)."""
    return policies.get(context_domain) or {}


def is_eligible_for_auto_approve(
    policy: dict,
    action_type: str,
    estimated_cents: int | None,
    reversibility: str,
) -> tuple[bool, str]:
    """Given a domain policy and a proposal, decide whether AI auto-approve
    is permitted. Returns (eligible, reason).

    Reason is an operator-readable explanation, always populated — used
    in the AI reviewer's reasoning trail.
    """
    threshold = policy.get("auto_approve_below_cents")
    if threshold is None or threshold <= 0:
        return False, "no auto_approve_below_cents threshold declared for this domain"

    blocked = policy.get("never_auto_approve") or []
    for blocked_fragment in blocked:
        if blocked_fragment and blocked_fragment in action_type:
            return False, f"action_type matches never_auto_approve entry '{blocked_fragment}'"

    if reversibility == "irreversible":
        return False, "reversibility=irreversible — irreversible writes always defer to human"

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
        f"action_type not blocked",
    )
