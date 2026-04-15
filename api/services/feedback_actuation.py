"""
Feedback Actuation — ADR-181 Phase 2.

Evaluates accumulated feedback entries against actuation rules and executes
qualifying workspace mutations. This is the bridge between feedback-as-information
and feedback-as-action.

Two processing tiers:
  Tier 1 (injection): _extract_recent_feedback() reads last 3 entries into prompt.
         Handled by task_pipeline.py — unchanged by this module.
  Tier 2 (actuation): THIS MODULE reads all entries, matches rules, checks
         thresholds, executes mutations.

Actuation rules are deterministic Python — no LLM cost. Rules match on the
Action: line in feedback entries. User-sourced actions actuate at threshold 1
(explicit intent). System-sourced actions accumulate at threshold 3 (distinguish
transient noise from real drift).

Called from _post_run_domain_scan() in task_pipeline.py, after system
verification writes, before awareness.md write.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Actuation rule registry
# ---------------------------------------------------------------------------

@dataclass
class ActuationRule:
    """A single actuation rule that matches feedback Action: lines."""
    name: str
    pattern: str           # regex pattern to match against Action: line content
    user_threshold: int    # entries needed from user sources to actuate
    system_threshold: int  # entries needed from system sources to actuate
    executor: str          # function name in this module to call


FEEDBACK_ACTUATION_RULES: list[ActuationRule] = [
    ActuationRule(
        name="remove_entity",
        pattern=r"remove entity (\S+)/(\S+)",
        user_threshold=1,
        system_threshold=999,  # system doesn't directly request removal
        executor="_actuate_remove_entity",
    ),
    ActuationRule(
        name="stale_entity",
        pattern=r"flag stale entity (.+?)(?:\s*\|)",
        user_threshold=1,
        system_threshold=3,
        executor="_actuate_stale_entity",
    ),
    ActuationRule(
        name="restore_entity",
        pattern=r"restore entity (\S+)/(\S+)",
        user_threshold=1,
        system_threshold=999,  # system doesn't restore
        executor="_actuate_restore_entity",
    ),
    ActuationRule(
        name="expand_coverage",
        pattern=r"expand coverage (\S+)",
        user_threshold=1,
        system_threshold=2,
        executor=None,  # No mutation — prompt amplification only
    ),
]


# ---------------------------------------------------------------------------
# Source classification
# ---------------------------------------------------------------------------

_USER_SOURCES = {"user_conversation", "user_edit"}
_SYSTEM_SOURCES = {"system_verification", "system_lifecycle", "evaluation"}


def _classify_source(entry: str) -> str:
    """Classify a feedback entry as 'user' or 'system' from its source: tag."""
    source_match = re.search(r"source:\s*(\S+)", entry)
    if source_match:
        source = source_match.group(1).rstrip(")")
        if source in _USER_SOURCES:
            return "user"
    return "system"


# ---------------------------------------------------------------------------
# Entry parsing
# ---------------------------------------------------------------------------

def _parse_action_line(entry: str) -> Optional[str]:
    """Extract the Action: line content from a feedback entry."""
    for line in entry.split("\n"):
        stripped = line.strip().lstrip("- ")
        if stripped.startswith("Action:"):
            return stripped[len("Action:"):].strip()
    return None


def _parse_entries(feedback_content: str) -> list[dict]:
    """Parse feedback.md into structured entries with source and action."""
    entries = re.split(r"(?=^## )", feedback_content, flags=re.MULTILINE)
    parsed = []
    for entry in entries:
        entry = entry.strip()
        if not entry or not entry.startswith("## "):
            continue
        action = _parse_action_line(entry)
        source_class = _classify_source(entry)
        parsed.append({
            "raw": entry,
            "action": action,
            "source_class": source_class,
        })
    return parsed


# ---------------------------------------------------------------------------
# Core evaluation
# ---------------------------------------------------------------------------

async def evaluate_actuation_rules(
    tw,
    task_slug: str,
    task_info: dict,
) -> list[dict]:
    """Evaluate all feedback entries against actuation rules.

    Returns list of actuation results (for logging to awareness.md).
    """
    from services.feedback_distillation import _read_task_feedback

    feedback_content = await _read_task_feedback(tw)
    if not feedback_content or feedback_content.strip() == "# Task Feedback":
        return []

    entries = _parse_entries(feedback_content)
    if not entries:
        return []

    actuations: list[dict] = []

    for rule in FEEDBACK_ACTUATION_RULES:
        if rule.executor is None:
            continue  # Prompt-amplification-only rules — no mutation

        # Collect matching entries grouped by target (the regex capture)
        matches_by_target: dict[str, list[dict]] = {}
        for entry in entries:
            if not entry["action"]:
                continue
            m = re.search(rule.pattern, entry["action"])
            if m:
                target_key = m.group(0)  # Full match as grouping key
                if target_key not in matches_by_target:
                    matches_by_target[target_key] = []
                matches_by_target[target_key].append({
                    **entry,
                    "match_groups": m.groups(),
                })

        # For each target, check if threshold is met
        for target_key, target_entries in matches_by_target.items():
            user_count = sum(1 for e in target_entries if e["source_class"] == "user")
            system_count = sum(1 for e in target_entries if e["source_class"] == "system")

            should_actuate = (
                user_count >= rule.user_threshold
                or system_count >= rule.system_threshold
            )

            # User override check: if there's a contradicting user entry
            # (e.g., "restore" when trying to "stale_entity"), suppress
            if rule.name == "stale_entity" and should_actuate:
                # Check for user-sourced restore or keep entries for same entity
                entity_ref = target_entries[0]["match_groups"][0] if target_entries[0]["match_groups"] else ""
                for entry in entries:
                    if entry["source_class"] == "user" and entry["action"]:
                        if re.search(r"restore entity|keep tracking", entry["action"], re.IGNORECASE):
                            if entity_ref and entity_ref in entry["action"]:
                                should_actuate = False
                                break

            if should_actuate:
                match_groups = target_entries[0]["match_groups"]
                source_class = "user" if user_count >= rule.user_threshold else "system"
                try:
                    executor_fn = globals().get(rule.executor)
                    if executor_fn:
                        result = await executor_fn(tw, match_groups, task_info)
                        actuations.append({
                            "rule": rule.name,
                            "target": target_key,
                            "source": source_class,
                            "count": user_count + system_count,
                            "result": result,
                        })
                except Exception as e:
                    logger.warning(
                        f"[ACTUATION] Executor {rule.executor} failed for "
                        f"{target_key}: {e}"
                    )
                    actuations.append({
                        "rule": rule.name,
                        "target": target_key,
                        "source": source_class,
                        "error": str(e),
                    })

    return actuations


# ---------------------------------------------------------------------------
# Actuation executors
# ---------------------------------------------------------------------------

async def _actuate_remove_entity(
    tw, match_groups: tuple, task_info: dict
) -> dict:
    """Soft-retire an entity. Reuses ManageDomains remove logic."""
    domain_key = match_groups[0] if len(match_groups) > 0 else ""
    slug = match_groups[1] if len(match_groups) > 1 else ""
    if not domain_key or not slug:
        return {"success": False, "error": "missing domain/slug from action line"}

    from services.workspace import UserMemory
    from services.directory_registry import (
        get_tracker_path, build_tracker_md, has_entity_tracker,
        WORKSPACE_DIRECTORIES,
    )
    from services.primitives.scaffold import _scan_domain_entities

    if domain_key not in WORKSPACE_DIRECTORIES:
        return {"success": False, "error": f"unknown domain: {domain_key}"}

    um = UserMemory(tw._db, tw._user_id)
    domain_path = WORKSPACE_DIRECTORIES[domain_key]["path"]

    # Add deprecation marker to profile.md
    primary_path = f"{domain_path}/{slug}/profile.md"
    existing = await um.read(primary_path)
    if existing and "<!-- status: inactive -->" not in existing:
        await um.write(
            primary_path,
            f"<!-- status: inactive -->\n{existing}",
            summary=f"ADR-181 actuation: soft-retired {domain_key}/{slug}",
        )

    # Rebuild tracker
    if has_entity_tracker(domain_key):
        tracker_path = get_tracker_path(domain_key)
        if tracker_path:
            entity_list = await _scan_domain_entities(um, domain_path, domain_key)
            tracker_content = build_tracker_md(domain_key, entity_list)
            await um.write(tracker_path, tracker_content,
                          summary=f"Tracker rebuild after actuation: remove {slug}")

    logger.info(f"[ACTUATION] Soft-retired entity {domain_key}/{slug}")
    return {"success": True, "action": "remove", "domain": domain_key, "slug": slug}


async def _actuate_stale_entity(
    tw, match_groups: tuple, task_info: dict
) -> dict:
    """Soft-retire a stale entity — same as remove but with stale-specific logging."""
    # match_groups[0] is the full entity ref like "acme-corp (competitors)"
    entity_ref = match_groups[0] if match_groups else ""

    # Parse "slug (domain_key)" format from stale entity strings
    m = re.match(r"(\S+)\s*\((\S+)\)", entity_ref)
    if not m:
        return {"success": False, "error": f"cannot parse entity ref: {entity_ref}"}

    slug = m.group(1)
    domain_key = m.group(2)

    # Delegate to remove logic
    result = await _actuate_remove_entity(
        tw, (domain_key, slug), task_info
    )
    if result.get("success"):
        result["reason"] = "stale_retirement"
    return result


async def _actuate_restore_entity(
    tw, match_groups: tuple, task_info: dict
) -> dict:
    """Restore an inactive entity by removing the status marker."""
    domain_key = match_groups[0] if len(match_groups) > 0 else ""
    slug = match_groups[1] if len(match_groups) > 1 else ""
    if not domain_key or not slug:
        return {"success": False, "error": "missing domain/slug from action line"}

    from services.workspace import UserMemory
    from services.directory_registry import (
        get_tracker_path, build_tracker_md, has_entity_tracker,
        WORKSPACE_DIRECTORIES,
    )
    from services.primitives.scaffold import _scan_domain_entities

    if domain_key not in WORKSPACE_DIRECTORIES:
        return {"success": False, "error": f"unknown domain: {domain_key}"}

    um = UserMemory(tw._db, tw._user_id)
    domain_path = WORKSPACE_DIRECTORIES[domain_key]["path"]

    # Remove deprecation marker from profile.md
    primary_path = f"{domain_path}/{slug}/profile.md"
    existing = await um.read(primary_path)
    if existing and "<!-- status: inactive -->" in existing:
        restored = existing.replace("<!-- status: inactive -->\n", "").replace("<!-- status: inactive -->", "")
        await um.write(
            primary_path,
            restored,
            summary=f"ADR-181 actuation: restored {domain_key}/{slug}",
        )

    # Rebuild tracker
    if has_entity_tracker(domain_key):
        tracker_path = get_tracker_path(domain_key)
        if tracker_path:
            entity_list = await _scan_domain_entities(um, domain_path, domain_key)
            tracker_content = build_tracker_md(domain_key, entity_list)
            await um.write(tracker_path, tracker_content,
                          summary=f"Tracker rebuild after actuation: restore {slug}")

    logger.info(f"[ACTUATION] Restored entity {domain_key}/{slug}")
    return {"success": True, "action": "restore", "domain": domain_key, "slug": slug}


# ---------------------------------------------------------------------------
# Entry age-out
# ---------------------------------------------------------------------------

def age_out_system_entries(feedback_content: str, max_system_age_runs: int = 3) -> str:
    """Remove system verification entries older than N runs.

    ADR-181: System entries are transient signals — if not actuated after
    max_system_age_runs, they've either been resolved or accumulated enough
    to trigger actuation. User entries persist until inference distills them.

    The run count is approximated by entry position: entries are newest-first,
    and each run writes at most ~5 system entries. We keep the first
    (max_system_age_runs * 5) system entries and drop the rest.

    User entries are never aged out by this function.
    """
    if not feedback_content or not feedback_content.strip():
        return feedback_content

    entries = re.split(r"(?=^## )", feedback_content, flags=re.MULTILINE)
    header_parts = []
    entry_parts = []

    for part in entries:
        part = part.strip()
        if not part:
            continue
        if part.startswith("## "):
            entry_parts.append(part)
        else:
            header_parts.append(part)

    # Separate user and system entries
    kept: list[str] = []
    system_count = 0
    max_system_entries = max_system_age_runs * 5

    for entry in entry_parts:
        source_class = _classify_source(entry)
        if source_class == "system":
            system_count += 1
            if system_count <= max_system_entries:
                kept.append(entry)
            # else: aged out
        else:
            kept.append(entry)  # User entries always kept

    header = header_parts[0] if header_parts else "# Task Feedback\n<!-- Source-agnostic feedback layer. Newest first. ADR-181. -->"
    if not kept:
        return header + "\n"

    return header + "\n\n" + "\n\n".join(kept) + "\n"
