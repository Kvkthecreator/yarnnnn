"""Review policy — ADR-211 Phase 4 D2 + D5 + ADR-217 + ADR-254.

ADR-254: machine-parsed config migrated from .md frontmatter to .yaml files.
- `_principles.yaml` — machine-parsed thresholds (high_impact_threshold_cents,
  auto_approve_below_cents). Read by load_principles() via yaml.safe_load.
- `_autonomy.yaml` — machine-parsed delegation config (level, ceiling_cents,
  never_auto, paused_until, pause_reason, heartbeat_triggers).
  Read by load_autonomy() via yaml.safe_load.

The prose files (principles.md, AUTONOMY.md) are preserved for LLM reading
and human documentation. They are not machine-parsed.

Type validation: `_validate_autonomy_block` and `_validate_principles_block`
coerce and validate every block at read time. Type mismatches are logged as
warnings and replaced with safe defaults (manual/0/empty). This prevents silent
failures in `should_auto_execute_verdict` when YAML values are mis-typed (e.g.
ceiling_cents written as "20000" string instead of 20000 int).

Public API (unchanged signatures, new backing files):
- `load_principles(client, user_id)` → dict keyed by domain
- `load_autonomy(client, user_id)` → dict keyed by domain + default fallback
- `autonomy_for_domain(autonomy, context_domain)` → resolved policy dict
- `principles_for_domain(principles, context_domain)` → resolved principles dict
- `should_auto_execute_verdict(...)` → (bool, reason_str)
"""

from __future__ import annotations

import logging
import re as _re
from typing import Any

import yaml as _yaml

from services.workspace_paths import (
    REVIEW_PRINCIPLES_YAML_PATH,
    SHARED_AUTONOMY_YAML_PATH,
)

logger = logging.getLogger(__name__)

# Path constants — now pointing at .yaml files (ADR-254)
PRINCIPLES_YAML_PATH = f"/workspace/{REVIEW_PRINCIPLES_YAML_PATH}"
AUTONOMY_YAML_PATH = f"/workspace/{SHARED_AUTONOMY_YAML_PATH}"

_DEFAULT_DOMAIN_KEY = "default"
_VALID_AUTONOMY_LEVELS = {"manual", "assisted", "bounded_autonomous", "autonomous"}

# Frontmatter pattern: leading ---\n...\n--- block (tier:, note:, prompt: metadata)
_FM_RE = _re.compile(r"^---\n.*?\n---\n", _re.DOTALL)


def load_workspace_yaml(content: str) -> dict:
    """Parse workspace yaml content, stripping --- frontmatter header if present.

    Workspace yaml files seeded from reference bundles carry a frontmatter block:
        ---
        tier: canon
        note: "..."
        ---
    yaml.safe_load raises ComposerError on multi-document streams. This helper
    strips the frontmatter before parsing so the body document loads cleanly.
    Never raises — returns {} on any parse failure.
    """
    if not content:
        return {}
    cleaned = _FM_RE.sub("", content, count=1)
    # Also strip leading comment lines (# ...)
    lines = [l for l in cleaned.splitlines() if not l.startswith("#")]
    cleaned = "\n".join(lines)
    try:
        return _yaml.safe_load(cleaned) or {}
    except _yaml.YAMLError:
        return {}


# =============================================================================
# Block validators — coerce types at read time, log on mismatch, fail safe
# =============================================================================

def _validate_autonomy_block(block: dict, domain: str) -> dict:
    """Coerce and validate one autonomy domain block.

    Catches the common YAML mis-typing: ceiling_cents written as string
    "20000" instead of int 20000.  A bad ceiling would cause a TypeError
    crash in `should_auto_execute_verdict`.  Log and return safe defaults.
    """
    if not isinstance(block, dict):
        return {}

    result = dict(block)

    # --- level ---
    level = result.get("level", "manual")
    if level not in _VALID_AUTONOMY_LEVELS:
        logger.warning(
            "[REVIEW_POLICY] _autonomy.yaml %s.level=%r not valid — defaulting to manual", domain, level
        )
        result["level"] = "manual"

    # --- ceiling_cents ---
    ceiling_raw = result.get("ceiling_cents")
    if ceiling_raw is not None:
        try:
            result["ceiling_cents"] = int(ceiling_raw)
        except (TypeError, ValueError):
            logger.warning(
                "[REVIEW_POLICY] _autonomy.yaml %s.ceiling_cents=%r not int — removing", domain, ceiling_raw
            )
            del result["ceiling_cents"]

    # --- never_auto ---
    never_auto = result.get("never_auto")
    if never_auto is not None and not isinstance(never_auto, list):
        logger.warning(
            "[REVIEW_POLICY] _autonomy.yaml %s.never_auto expected list — defaulting to []", domain
        )
        result["never_auto"] = []

    return result


def _validate_principles_block(block: dict, domain: str) -> dict:
    """Coerce and validate one principles domain block.

    Catches string-typed threshold values (e.g. auto_approve_below_cents: "20000")
    that would otherwise cause a TypeError crash at comparison time.
    """
    if not isinstance(block, dict):
        return {}

    result = {}
    for key in ("high_impact_threshold_cents", "auto_approve_below_cents"):
        raw = block.get(key)
        if raw is None:
            continue
        try:
            result[key] = int(raw)
        except (TypeError, ValueError):
            logger.warning(
                "[REVIEW_POLICY] _principles.yaml %s.%s=%r not int — ignoring", domain, key, raw
            )

    return result


# =============================================================================
# Public API
# =============================================================================

def load_principles(client: Any, user_id: str) -> dict:
    """Load machine-parsed review thresholds from _principles.yaml (ADR-254).

    Returns a dict keyed by domain:
        {"trading": {"high_impact_threshold_cents": int,
                     "auto_approve_below_cents": int}, ...}

    Values are type-validated via _validate_principles_block — integer fields
    are coerced and mismatches are logged. Empty dict on missing file or parse
    failure. Never raises.
    """
    content = _read_file(client, user_id, PRINCIPLES_YAML_PATH)
    if not content:
        return {}
    parsed = load_workspace_yaml(content)
    return {
        k: _validate_principles_block(v, k)
        for k, v in parsed.items()
        if isinstance(v, dict) and k not in ("tier", "note")
    }


def load_autonomy(client: Any, user_id: str) -> dict:
    """Load delegation declaration from _autonomy.yaml (ADR-254).

    Returns a dict keyed by domain (including the synthetic `default` fallback):
        {"default": {"level": str, "ceiling_cents": int, "never_auto": list,
                     "paused_until": str|None, "pause_reason": str|None,
                     "heartbeat_triggers": list},
         "<domain>": {...per-domain override...}, ...}

    Values are type-validated via _validate_autonomy_block — integer and enum
    fields are coerced and mismatches are logged. Empty dict on missing file or
    parse failure. Never raises.
    """
    content = _read_file(client, user_id, AUTONOMY_YAML_PATH)
    if not content:
        return {}
    parsed = load_workspace_yaml(content)
    return {
        k: _validate_autonomy_block(v, k)
        for k, v in parsed.items()
        if isinstance(v, dict) and k not in ("tier", "note")
    }


def autonomy_for_domain(autonomy: dict, context_domain: str) -> dict:
    """Return the delegation policy for a domain.

    Resolution order:
      1. Per-domain block under `<context_domain>:` if present.
      2. `default:` fallback block if present.
      3. Empty dict (= manual-by-default).
    """
    domain_policy = autonomy.get(context_domain)
    if domain_policy and isinstance(domain_policy, dict):
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
    *,
    principles_policy: dict | None = None,
) -> tuple[bool, str]:
    """Post-judgment binding gate (ADR-229 D1 + ADR-253 D1 + ADR-254 D3).

    Given the Reviewer's verdict and the operator's declared autonomy
    delegation, decide whether the verdict auto-executes (binding) or
    routes to the Queue as advisory (operator clicks).

    Two gates must both pass:
    1. AUTONOMY gate: operator's delegation ceiling (level + ceiling_cents)
    2. PRINCIPLES gate: Reviewer's own auto_approve threshold (principles_policy)

    The stricter of the two wins. Reviewer can be more conservative than
    operator permits; never more permissive.

    Returns (should_execute, reason). `verdict` MUST be one of
    "approve" | "reject" | "defer". Non-approve verdicts always return False.
    """
    # ADR-248 D3: Reviewer-written pause marker — checked before any other gate.
    paused_until_raw = autonomy_policy.get("paused_until")
    if paused_until_raw:
        try:
            from datetime import timezone as _tz, datetime as _dt
            ts_str = str(paused_until_raw)
            if ts_str.endswith("Z"):
                ts_str = ts_str[:-1] + "+00:00"
            paused_until = _dt.fromisoformat(ts_str)
            if paused_until.tzinfo is None:
                paused_until = paused_until.replace(tzinfo=_tz.utc)
            if paused_until > _dt.now(_tz.utc):
                pause_reason = autonomy_policy.get("pause_reason", "Reviewer-initiated pause")
                return (False, f"autonomy_paused until {paused_until.isoformat()} — {pause_reason}")
        except (ValueError, TypeError):
            pass  # Malformed timestamp — ignore

    if verdict == "reject":
        return False, "verdict=reject — Reviewer's own narrowing, never auto-executes"
    if verdict == "defer":
        return False, "verdict=defer — Reviewer surfaced to operator"
    if verdict not in ("approve", "heartbeat"):
        return False, f"verdict={verdict!r} unrecognized — defaulting to non-binding"

    # --- AUTONOMY gate ---
    level = autonomy_policy.get("level", "manual")
    if level == "manual":
        return False, "autonomy.level=manual — operator retains every binding decision"
    if level not in _VALID_AUTONOMY_LEVELS:
        return False, f"autonomy.level={level} unrecognized — defaulting to manual"
    if level == "assisted":
        return False, "autonomy.level=assisted — AI recommends, human binds"

    ceiling = autonomy_policy.get("ceiling_cents")
    if level == "bounded_autonomous" and (ceiling is None or ceiling <= 0):
        return False, "autonomy.level=bounded_autonomous but no ceiling_cents set"

    blocked = autonomy_policy.get("never_auto") or []
    for blocked_fragment in blocked:
        if blocked_fragment and blocked_fragment in action_type:
            return False, f"action_type matches autonomy.never_auto entry '{blocked_fragment}'"

    if reversibility == "irreversible":
        return False, "reversibility=irreversible — irreversible writes always route to operator"

    if level == "bounded_autonomous":
        if estimated_cents is None:
            return False, "proposal has no estimated value — cannot compare against ceiling"
        if abs(estimated_cents) > ceiling:
            return (False, f"estimated ${abs(estimated_cents)/100:.2f} exceeds autonomy ceiling ${ceiling/100:.2f}")

    # --- PRINCIPLES gate (ADR-254 D3) ---
    if principles_policy:
        threshold = principles_policy.get("auto_approve_below_cents")
        if threshold is not None:
            if estimated_cents is None:
                return False, "principles.auto_approve_below_cents set but proposal has no estimated value"
            if abs(estimated_cents) > threshold:
                return (False, f"estimated ${abs(estimated_cents)/100:.2f} exceeds principles threshold ${threshold/100:.2f}")

    # Both gates passed
    reason = (
        f"verdict=approve, autonomy.level={level}"
        + (f" ceiling=${ceiling/100:.2f}" if level == "bounded_autonomous" else "")
        + ", principles gate passed"
    )
    return (True, reason)


# =============================================================================
# Internal file read
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
    except Exception as exc:
        logger.warning("[REVIEW_POLICY] read failed path=%s user=%s: %s", path, user_id[:8], exc)
        return ""
    rows = result.data or []
    if not rows:
        return ""
    return rows[0].get("content") or ""
