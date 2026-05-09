"""Review policy — ADR-261 D5 rederived shape.

ADR-261 D5: AUTONOMY rederived from first principles. AUTONOMY's only job
is to gate **consequential actions** the Reviewer takes within a session.
Consequential = capital-moving + irreversible-external-write. Everything else
(reads, scheduling self-wakeups via Schedule, writing to own substrate,
ProposeAction queueing for operator review) is unrestricted because it's all
observable + reversible via the revision chain (ADR-209).

The new `_autonomy.yaml` schema:

    default:
      delegation: bounded   # manual | bounded | autonomous
      ceiling_cents: 20000   # used when bounded; ignored for manual/autonomous

    domains:
      trading:
        delegation: bounded
        ceiling_cents: 20000
      commerce:
        delegation: manual

    paused_until: null
    pause_reason: null

Delegation enum:
- `manual`     — every consequential action queues for operator approval.
- `bounded`    — auto-approve up to `ceiling_cents`, queue above.
- `autonomous` — auto-approve every consequential action (operator opt-in
                  for full autonomy).

Deleted fields (per ADR-261 D5):
- `level` field (renamed to `delegation`)
- `assisted` value (folded into `manual` — same effective behavior)
- `bounded_autonomous` value (renamed to `bounded`)
- `auto_approve_below_cents` — folded into `ceiling_cents` under `bounded`
- `never_auto` — folded into `manual` delegation
- `heartbeat_triggers` — gone with ADR-260 D4 (heartbeat trigger deleted)

`paused_until` + `pause_reason` survive (per ADR-248 D3+D4) — when non-null,
AUTONOMY is effectively `manual` regardless of declared `delegation`.

The prose files (`AUTONOMY.md`, `principles.md`) are preserved for LLM
reading and human documentation. They are not machine-parsed.

Public API:
- `load_principles(client, user_id)` → dict keyed by domain
- `load_autonomy(client, user_id)` → {"default": {...}, "domains": {<name>: {...}},
                                       "paused_until": ..., "pause_reason": ...}
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

# Path constants
PRINCIPLES_YAML_PATH = f"/workspace/{REVIEW_PRINCIPLES_YAML_PATH}"
AUTONOMY_YAML_PATH = f"/workspace/{SHARED_AUTONOMY_YAML_PATH}"

_DEFAULT_DOMAIN_KEY = "default"

# ADR-261 D5: 3-value delegation enum (was 4 under ADR-211).
_VALID_DELEGATION_LEVELS = {"manual", "bounded", "autonomous"}

# Frontmatter pattern: leading ---\n...\n--- block
_FM_RE = _re.compile(r"^---\n.*?\n---\n", _re.DOTALL)


def load_workspace_yaml(content: str) -> dict:
    """Parse workspace yaml content, stripping --- frontmatter header if present.

    Workspace yaml files seeded from reference bundles carry a frontmatter block
    (`tier:`, `note:`, `prompt:`). yaml.safe_load raises on multi-document
    streams; this helper strips the frontmatter before parsing.
    Never raises — returns {} on any parse failure.
    """
    if not content:
        return {}
    cleaned = _FM_RE.sub("", content, count=1)
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
    "20000" instead of int 20000.  Log and return safe defaults on mismatch.
    """
    if not isinstance(block, dict):
        return {}

    result = dict(block)

    # --- delegation ---
    delegation = result.get("delegation", "manual")
    if delegation not in _VALID_DELEGATION_LEVELS:
        logger.warning(
            "[REVIEW_POLICY] _autonomy.yaml %s.delegation=%r not valid — defaulting to manual",
            domain, delegation,
        )
        result["delegation"] = "manual"

    # --- ceiling_cents ---
    ceiling_raw = result.get("ceiling_cents")
    if ceiling_raw is not None:
        try:
            result["ceiling_cents"] = int(ceiling_raw)
        except (TypeError, ValueError):
            logger.warning(
                "[REVIEW_POLICY] _autonomy.yaml %s.ceiling_cents=%r not int — removing",
                domain, ceiling_raw,
            )
            del result["ceiling_cents"]

    return result


def _validate_principles_block(block: dict, domain: str) -> dict:
    """Coerce and validate one principles domain block.

    ADR-261 D5: `auto_approve_below_cents` deleted — folded into `ceiling_cents`
    under `bounded` delegation. `high_impact_threshold_cents` survives for
    ADR-181 routing of high-impact outcomes to feedback substrate.
    """
    if not isinstance(block, dict):
        return {}

    result = dict(block)
    for key in ("high_impact_threshold_cents",):
        raw = result.get(key)
        if raw is not None:
            try:
                result[key] = int(raw)
            except (TypeError, ValueError):
                logger.warning(
                    "[REVIEW_POLICY] _principles.yaml %s.%s=%r not int — removing",
                    domain, key, raw,
                )
                del result[key]
    return result


# =============================================================================
# Loaders
# =============================================================================

def load_principles(client: Any, user_id: str) -> dict:
    """Load Reviewer principles from `_principles.yaml`.

    Returns a dict keyed by domain (including the synthetic `default` fallback):
        {"default": {"high_impact_threshold_cents": int}, ...}

    Empty dict on missing file or parse failure. Never raises.
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
    """Load delegation declaration from `_autonomy.yaml` (ADR-261 D5 shape).

    Returns:
        {
          "default": {"delegation": str, "ceiling_cents": int|None},
          "domains": {"<domain>": {"delegation": str, "ceiling_cents": int|None}},
          "paused_until": str|None,
          "pause_reason": str|None,
        }

    Empty dict on missing file or parse failure. Never raises.
    """
    content = _read_file(client, user_id, AUTONOMY_YAML_PATH)
    if not content:
        return {}
    parsed = load_workspace_yaml(content)

    out: dict = {
        "default": {},
        "domains": {},
        "paused_until": parsed.get("paused_until"),
        "pause_reason": parsed.get("pause_reason"),
    }

    default_block = parsed.get("default")
    if isinstance(default_block, dict):
        out["default"] = _validate_autonomy_block(default_block, "default")

    raw_domains = parsed.get("domains") or {}
    if isinstance(raw_domains, dict):
        for k, v in raw_domains.items():
            if isinstance(v, dict):
                out["domains"][k] = _validate_autonomy_block(v, k)

    return out


def autonomy_for_domain(autonomy: dict, context_domain: str) -> dict:
    """Return the delegation policy for a domain.

    Resolution order: `domains.<context_domain>` → `default` → `{}`.
    Mixes in workspace-wide `paused_until` + `pause_reason` so callers see
    the full effective policy in one resolved block.
    """
    if not autonomy:
        return {}
    domains = autonomy.get("domains") or {}
    if context_domain and context_domain in domains:
        block = dict(domains[context_domain])
    else:
        block = dict(autonomy.get("default") or {})
    # Mix in workspace-wide pause fields so should_auto_execute_verdict sees them.
    if autonomy.get("paused_until") is not None:
        block.setdefault("paused_until", autonomy.get("paused_until"))
    if autonomy.get("pause_reason") is not None:
        block.setdefault("pause_reason", autonomy.get("pause_reason"))
    return block


def principles_for_domain(principles: dict, context_domain: str) -> dict:
    """Return Reviewer principles for a domain.

    Resolution order: `<context_domain>` → `default` → `{}`.
    """
    if not principles:
        return {}
    if context_domain and context_domain in principles:
        return principles[context_domain]
    return principles.get(_DEFAULT_DOMAIN_KEY) or {}


# =============================================================================
# Decision gate — single AUTONOMY ceiling check (ADR-261 D5 collapse)
# =============================================================================

def should_auto_execute_verdict(
    autonomy_policy: dict,
    verdict: str = "approve",
    *,
    action_type: str = "",
    estimated_cents: int | None = None,
    reversibility: str = "reversible",
    principles_policy: dict | None = None,  # accepted for legacy callsites; unused post-ADR-261 D5
    paused_until: str | None = None,
    pause_reason: str | None = None,
) -> tuple[bool, str]:
    """Decide whether a Reviewer verdict auto-executes (per ADR-261 D5).

    One gate: operator's delegation level + ceiling. The Reviewer's verdict
    must be `approve` (`reject`/`defer` always route through operator); the
    delegation policy then permits or denies execution.

    Returns (should_execute, reason).
    """
    # --- pause check (ADR-248 D3 mechanism preserved) ---
    # paused_until / pause_reason may come either as explicit kwargs (newer
    # callers) or be mixed into autonomy_policy by autonomy_for_domain.
    pu = paused_until or autonomy_policy.get("paused_until")
    pr = pause_reason or autonomy_policy.get("pause_reason")
    if pu:
        try:
            from datetime import timezone as _tz, datetime as _dt
            ts_str = str(pu)
            if ts_str.endswith("Z"):
                ts_str = ts_str[:-1] + "+00:00"
            paused_dt = _dt.fromisoformat(ts_str)
            if paused_dt.tzinfo is None:
                paused_dt = paused_dt.replace(tzinfo=_tz.utc)
            if paused_dt > _dt.now(_tz.utc):
                reason_msg = pr or "Reviewer-initiated pause"
                return (False, f"autonomy_paused until {paused_dt.isoformat()} — {reason_msg}")
        except (ValueError, TypeError):
            pass  # malformed timestamp — ignore

    # --- verdict gate ---
    if verdict == "reject":
        return False, "verdict=reject — Reviewer's own narrowing, never auto-executes"
    if verdict == "defer":
        return False, "verdict=defer — Reviewer surfaced to operator"
    if verdict != "approve":
        return False, f"verdict={verdict!r} unrecognized — defaulting to non-binding"

    # --- delegation gate ---
    delegation = autonomy_policy.get("delegation", "manual")
    if delegation == "manual":
        return False, "autonomy.delegation=manual — operator retains every binding decision"
    if delegation not in _VALID_DELEGATION_LEVELS:
        return False, f"autonomy.delegation={delegation!r} unrecognized — defaulting to manual"

    if reversibility == "irreversible":
        return False, "reversibility=irreversible — irreversible writes always route to operator"

    if delegation == "autonomous":
        return True, "verdict=approve, autonomy.delegation=autonomous — auto-execute"

    # delegation == "bounded"
    ceiling = autonomy_policy.get("ceiling_cents")
    if ceiling is None or ceiling <= 0:
        return False, "autonomy.delegation=bounded but no ceiling_cents set"
    if estimated_cents is None:
        return False, "proposal has no estimated value — cannot compare against ceiling"
    if abs(estimated_cents) > ceiling:
        return (
            False,
            f"estimated ${abs(estimated_cents)/100:.2f} exceeds autonomy ceiling ${ceiling/100:.2f}",
        )

    return (
        True,
        f"verdict=approve, autonomy.delegation=bounded ceiling=${ceiling/100:.2f} — within ceiling",
    )


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
