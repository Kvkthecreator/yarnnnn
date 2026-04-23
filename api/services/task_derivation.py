"""
Task Derivation — minimum task set from Mandate + platform connections + existing tasks.

ADR-207 Phase 5: Before YARNNN calls `ManageTask(action="create")`, it should
build a derivation report that makes over-scaffolding and under-scaffolding
visible. The report shows:

  1. **Mandate** — Primary Action + success criteria + boundary conditions.
  2. **Capability surface** — which platform capabilities are currently
     available (per `platform_connections` + ADR-207 P3 gate).
  3. **Existing tasks** — slug, required_capabilities, context_reads/writes,
     declared loop role. What's already covered.
  4. **Coverage gaps** — Primary Action needs a Proposer; Proposer reads
     context paths that need maintenance (Sensor tasks); outcomes need
     reconciliation; operator needs decision-support instruments.

YARNNN consumes this report, shows the operator the proposed chain, confirms,
then calls `ManageTask(action="create")` for each approved task.

This is **not a new primitive** — it's a pure helper. No LLM call, no
side effects. The caller (YARNNN chat turn or a future MCP tool) is the
single intelligence layer that interprets the report and asks the operator.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


# Loop roles per ADR-207 D1 + D8. Labeled on each proposed/existing task so
# the operator sees the chain: Sensor → Proposer → Reviewer → Reconciler.
LOOP_ROLES = ("sensor", "proposer", "reviewer", "reconciler", "learner", "decision-support")


def _loop_role_for(task_row: dict, task_md: str) -> str:
    """Classify an existing task by its declared shape.

    Heuristic — reads TASK.md metadata fields (already parsed into `task_md`
    for inspection) and the `tasks.slug` to label loop role. The label is
    advisory; operators can override.
    """
    slug = (task_row.get("slug") or "").lower()
    md = task_md or ""

    # Back-office = reconciler class (outcome-reconciliation, hygiene, cleanup)
    if slug.startswith("back-office-"):
        if "outcome" in slug:
            return "reconciler"
        return "decision-support"  # hygiene/cleanup are maintenance, surface as decision-support

    # Tasks that emit proposals → Proposer
    if re.search(r"^\*\*Emits Proposal:\*\*\s*true", md, re.MULTILINE | re.IGNORECASE):
        return "proposer"

    # Explicit Required Capabilities that write externally → proposer-adjacent
    # (actual proposer uses ProposeAction + dry-run). Still label proposer
    # because the write capability makes it Loop-arrow 3/6.
    if re.search(r"^\*\*Required Capabilities:\*\*.*write_", md, re.MULTILINE):
        return "proposer"

    # Context-writing tasks → sensor (fills accumulated context domain)
    if re.search(r"^\*\*Context Writes:\*\*\s*\S", md, re.MULTILINE):
        # Don't downgrade a proposer if both context_writes and write_ capability
        # are present — proposer already returned above.
        return "sensor"

    # Read-only deliverable producers → decision-support
    return "decision-support"


def _read_mandate(client: Any, user_id: str) -> str:
    """Return MANDATE.md content or empty string. Skeleton placeholder treated as empty."""
    try:
        # Avoid circular import — imported lazily
        from services.workspace_paths import SHARED_MANDATE_PATH
        row = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", f"/workspace/{SHARED_MANDATE_PATH}")
            .limit(1)
            .execute()
        )
        if not row.data:
            return ""
        content = row.data[0].get("content") or ""
        if "not yet declared" in content:
            return ""
        return content
    except Exception as e:
        logger.warning(f"[TASK_DERIVATION] MANDATE.md read failed: {e}")
        return ""


def _active_platforms(client: Any, user_id: str) -> list[str]:
    """Return the list of platforms (strings) with status='active'."""
    try:
        rows = (
            client.table("platform_connections")
            .select("platform")
            .eq("user_id", user_id)
            .eq("status", "active")
            .execute()
        )
        return sorted({r.get("platform") for r in (rows.data or []) if r.get("platform")})
    except Exception as e:
        logger.warning(f"[TASK_DERIVATION] platform_connections read failed: {e}")
        return []


def _available_platform_capabilities(active_platforms: list[str]) -> list[str]:
    """Return capability names available to the user given active platforms.

    Reads CAPABILITIES registry (ADR-207 P3). Internal capabilities
    (platform_connection_requirement=None) are always available and not
    listed here — the report focuses on what the connections unlocked.
    """
    try:
        from services.agent_orchestration import CAPABILITIES
    except Exception:
        return []
    available: list[str] = []
    for name, cap in CAPABILITIES.items():
        req = cap.get("platform_connection_requirement")
        if req and req.get("platform") in active_platforms:
            available.append(name)
    return sorted(available)


def _list_tasks(client: Any, user_id: str) -> list[dict]:
    """Return task rows with slug, status, mode, schedule, plus TASK.md content."""
    try:
        rows = (
            client.table("tasks")
            .select("id, slug, status, mode, schedule")
            .eq("user_id", user_id)
            .execute()
        )
        result = []
        for r in (rows.data or []):
            task_md = _read_task_md(client, user_id, r["slug"])
            result.append({
                **r,
                "task_md": task_md,
                "loop_role": _loop_role_for(r, task_md),
                "required_capabilities": _extract_metadata_list(task_md, "Required Capabilities"),
                "context_reads": _extract_metadata_list(task_md, "Context Reads"),
                "context_writes": _extract_metadata_list(task_md, "Context Writes"),
            })
        return result
    except Exception as e:
        logger.warning(f"[TASK_DERIVATION] tasks read failed: {e}")
        return []


def _read_task_md(client: Any, user_id: str, slug: str) -> str:
    """Read /tasks/{slug}/TASK.md content or empty."""
    try:
        row = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", f"/tasks/{slug}/TASK.md")
            .limit(1)
            .execute()
        )
        if row.data:
            return row.data[0].get("content") or ""
    except Exception:
        pass
    return ""


def _extract_metadata_list(task_md: str, field_name: str) -> list[str]:
    """Pull `**{field_name}:** a, b, c` as a list. Empty if missing or 'none'."""
    if not task_md:
        return []
    pattern = rf"^\*\*{re.escape(field_name)}:\*\*\s*(.+)$"
    m = re.search(pattern, task_md, re.MULTILINE)
    if not m:
        return []
    raw = m.group(1).strip()
    if not raw or raw.lower() == "none":
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def build_derivation_report(client: Any, user_id: str) -> str:
    """Return a markdown derivation report for YARNNN's use before task scaffolding.

    Shape:
      # Task Derivation Report

      ## Mandate
      <content or 'NOT AUTHORED — operator must author before scaffolding'>

      ## Capability Surface
      - Active platforms: slack, commerce
      - Unlocked capabilities: read_slack, write_slack, read_commerce, ...

      ## Existing Tasks (N)
      - sensor: slack-awareness — read_slack, summarize → writes slack
      - proposer: daily-proposal — write_commerce (reads customers, revenue)
      - reconciler: back-office-outcome-reconciliation (commerce)
      - decision-support: weekly-revenue-report — writes none

      ## Coverage Gaps
      - Primary Action implies a Proposer with write_{platform} — none present yet.
      - Proposer will need to read context domains X, Y — ensure a Sensor task
        fills each before Proposer fires.
      - Outcome reconciliation — already materialized on platform-connect (ADR-206).

    YARNNN reads this, shows the operator the chain, confirms, then scaffolds
    the minimum set via ManageTask(action="create") calls.
    """
    mandate = _read_mandate(client, user_id)
    platforms = _active_platforms(client, user_id)
    capabilities = _available_platform_capabilities(platforms)
    tasks = _list_tasks(client, user_id)

    lines: list[str] = ["# Task Derivation Report", ""]

    # Section 1: Mandate
    lines.append("## Mandate")
    if not mandate:
        lines.append("NOT AUTHORED — operator must author MANDATE.md "
                     "via `UpdateContext(target='mandate')` before scaffolding. "
                     "The hard gate in ManageTask(create) will reject otherwise.")
    else:
        lines.append(mandate.strip())
    lines.append("")

    # Section 2: Capability surface
    lines.append("## Capability Surface")
    if platforms:
        lines.append(f"- Active platforms: {', '.join(platforms)}")
    else:
        lines.append("- Active platforms: (none) — platform-gated capabilities unavailable.")
    if capabilities:
        lines.append(f"- Unlocked platform capabilities: {', '.join(capabilities)}")
    else:
        lines.append("- Unlocked platform capabilities: (none beyond internal ones — "
                     "web_search, summarize, produce_markdown, ...).")
    lines.append("")

    # Section 3: Existing tasks, labeled by loop role
    lines.append(f"## Existing Tasks ({len(tasks)})")
    if not tasks:
        lines.append("- (none yet — every task proposed here is a new scaffold.)")
    else:
        # Group by loop_role
        by_role: dict[str, list[dict]] = {}
        for t in tasks:
            by_role.setdefault(t["loop_role"], []).append(t)
        for role in LOOP_ROLES:
            group = by_role.get(role, [])
            if not group:
                continue
            lines.append(f"### {role}")
            for t in group:
                caps = ", ".join(t["required_capabilities"]) or "(none declared)"
                reads = ", ".join(t["context_reads"]) or "(none)"
                writes = ", ".join(t["context_writes"]) or "(none)"
                status = t.get("status", "?")
                mode = t.get("mode", "?")
                sched = t.get("schedule") or "on-demand"
                lines.append(f"- `{t['slug']}` [{status}, {mode}, {sched}] — "
                             f"caps: {caps} · reads: {reads} · writes: {writes}")
    lines.append("")

    # Section 4: Coverage-gap hints (heuristic — YARNNN interprets)
    lines.append("## Coverage Gap Hints")
    if not mandate:
        lines.append("- Block: author Mandate first. Nothing below matters until the "
                     "Primary Action is declared.")
    else:
        # Heuristic gap checks
        has_proposer = any(t["loop_role"] == "proposer" for t in tasks)
        has_sensor = any(t["loop_role"] == "sensor" for t in tasks)
        has_decision_support = any(
            t["loop_role"] == "decision-support" and not t["slug"].startswith("back-office-")
            for t in tasks
        )

        if not has_proposer:
            lines.append("- No Proposer task yet. Mandate's Primary Action "
                         "needs an Agent that evaluates Rules against accumulated "
                         "context and emits proposals via `ProposeAction`. "
                         "Check Mandate — does it name a write capability "
                         "(submit_order, create_product, send_message)? If so, a "
                         "Proposer must exist before the Loop can close.")
        if not has_sensor:
            lines.append("- No Sensor task yet. Proposers need accumulated context; "
                         "Sensors maintain it. Propose a tracker + `read_{platform}` + "
                         "context_writes task for each domain the Proposer will read.")
        if not has_decision_support:
            lines.append("- No decision-support task yet. Operators benefit from "
                         "periodic readouts of `_performance.md` + key context "
                         "(e.g. weekly-revenue-report). Not required, but common.")
        # Reconciliation hint
        if "commerce" in platforms or "trading" in platforms:
            reconciler_exists = any(
                t["slug"] == "back-office-outcome-reconciliation" for t in tasks
            )
            if not reconciler_exists:
                lines.append("- Outcome reconciliation should materialize automatically "
                             "on platform-connect (ADR-205/206). If missing, inspect "
                             "`services/workspace_init.materialize_back_office_task` "
                             "or re-run the platform connect.")

    lines.append("")
    lines.append("---")
    lines.append("_Generated by `services.task_derivation.build_derivation_report` "
                 "(ADR-207 Phase 5). YARNNN reads this report before any "
                 "`ManageTask(action='create')` call and confirms the chain "
                 "with the operator._")

    return "\n".join(lines)
