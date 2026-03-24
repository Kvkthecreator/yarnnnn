"""
Pipeline Executor — ADR-137 (v1)

Reads PROCESS.md pipeline definition and executes steps mechanically.
No LLM coordination — steps advance based on dependencies.

The scheduler calls `advance_pipeline()` for each project. The executor:
1. Reads PROCESS.md pipeline + pipeline_state.json
2. Finds the next ready step (completed dependencies)
3. Runs the agent for that step
4. Updates pipeline_state.json
5. Checks if pipeline is complete → deliver

Replaces PM Tier 3 coordination pulse for routine execution.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def parse_pipeline(client: Any, user_id: str, project_slug: str) -> list[dict]:
    """Parse pipeline steps from PROCESS.md.

    Returns list of steps: [{name, agent_slug, depends_on, mode}]
    """
    from services.workspace import ProjectWorkspace

    pw = ProjectWorkspace(client, user_id, project_slug)
    process = await pw.read("PROCESS.md")
    if not process:
        return []

    steps = []
    in_pipeline = False
    for line in process.split("\n"):
        s = line.strip()

        # Detect pipeline/phases section
        if s.startswith("## Pipeline") or s.startswith("## Phases"):
            in_pipeline = True
            continue
        if in_pipeline and s.startswith("## ") and not s.startswith("### "):
            break

        if not in_pipeline:
            continue

        # Parse step lines: "- agent-slug: description"
        if s.startswith("- ") and ":" in s:
            parts = s[2:].split(":", 1)
            agent_slug = parts[0].strip()
            description = parts[1].strip() if len(parts) > 1 else ""

            # Detect PM steps
            mode = None
            if agent_slug == "pm":
                if "compose" in description.lower() or "deliver" in description.lower() or "assemble" in description.lower():
                    mode = "compose"
                elif "evaluat" in description.lower() or "quality" in description.lower():
                    mode = "evaluate"
                elif "reflect" in description.lower():
                    mode = "reflect"
                else:
                    mode = "compose"

            step = {
                "name": agent_slug,
                "agent_slug": agent_slug,
                "description": description,
                "depends_on": steps[-1]["name"] if steps else None,  # sequential by default
            }
            if mode:
                step["mode"] = mode

            steps.append(step)

    return steps


async def read_pipeline_state(client: Any, user_id: str, project_slug: str) -> dict:
    """Read pipeline_state.json."""
    from services.workspace import ProjectWorkspace

    pw = ProjectWorkspace(client, user_id, project_slug)
    raw = await pw.read("memory/pipeline_state.json")
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return {"cycle": 0, "status": "idle", "steps": {}}


async def write_pipeline_state(client: Any, user_id: str, project_slug: str, state: dict) -> None:
    """Write pipeline_state.json."""
    from services.workspace import ProjectWorkspace

    pw = ProjectWorkspace(client, user_id, project_slug)
    await pw.write(
        "memory/pipeline_state.json",
        json.dumps(state, indent=2),
        summary=f"Pipeline cycle {state.get('cycle', '?')}: {state.get('status', '?')}",
        content_type="application/json",
    )


async def advance_pipeline(
    client: Any,
    user_id: str,
    project_slug: str,
) -> dict:
    """Advance the project's pipeline by one step.

    Called by the scheduler for each project on each cycle.
    Returns: {action, step_name, agent_slug, ...} or {action: "idle"}
    """
    from services.workspace import get_agent_slug

    steps = await parse_pipeline(client, user_id, project_slug)
    if not steps:
        return {"action": "idle", "reason": "no pipeline defined"}

    state = await read_pipeline_state(client, user_id, project_slug)
    now = datetime.now(timezone.utc)

    # Check cadence — is the window open?
    if state.get("status") == "delivered":
        # Pipeline completed this cycle — check if cadence allows new cycle
        from services.workspace import ProjectWorkspace
        pw = ProjectWorkspace(client, user_id, project_slug)
        project = await pw.read_project()
        cadence = (project or {}).get("cadence", "")
        last_delivered = state.get("delivered_at")
        if cadence and last_delivered:
            from datetime import timedelta
            cadence_delta = {
                "daily": timedelta(hours=20),
                "weekly": timedelta(days=6),
                "biweekly": timedelta(days=13),
                "monthly": timedelta(days=28),
            }.get(cadence.lower().strip())
            if cadence_delta:
                try:
                    last_dt = datetime.fromisoformat(last_delivered.replace("Z", "+00:00"))
                    if (now - last_dt) < cadence_delta:
                        return {"action": "idle", "reason": f"cadence: {cadence}, next window not open"}
                except (ValueError, TypeError):
                    pass

        # Cadence window open — start new cycle
        state = {
            "cycle": state.get("cycle", 0) + 1,
            "status": "running",
            "started_at": now.isoformat(),
            "steps": {},
        }

    # Initialize cycle if idle
    if state.get("status") == "idle":
        state = {
            "cycle": state.get("cycle", 0) + 1,
            "status": "running",
            "started_at": now.isoformat(),
            "steps": {},
        }

    # Find next ready step
    step_states = state.get("steps", {})

    for step in steps:
        name = step["name"]
        step_status = step_states.get(name, {}).get("state", "waiting")

        if step_status in ("completed", "running"):
            continue

        # Check dependency
        dep = step.get("depends_on")
        if dep and step_states.get(dep, {}).get("state") != "completed":
            continue  # dependency not met

        # This step is ready — execute it
        step_states[name] = {
            "state": "running",
            "started_at": now.isoformat(),
        }
        state["steps"] = step_states
        await write_pipeline_state(client, user_id, project_slug, state)

        logger.info(f"[PIPELINE] {project_slug}: starting step '{name}' (cycle {state['cycle']})")

        return {
            "action": "execute",
            "step_name": name,
            "agent_slug": step["agent_slug"],
            "mode": step.get("mode"),
            "description": step.get("description", ""),
            "cycle": state["cycle"],
        }

    # Check if all steps completed
    all_done = all(
        step_states.get(s["name"], {}).get("state") == "completed"
        for s in steps
    )
    if all_done:
        state["status"] = "delivered"
        state["delivered_at"] = now.isoformat()
        await write_pipeline_state(client, user_id, project_slug, state)
        logger.info(f"[PIPELINE] {project_slug}: cycle {state['cycle']} complete")
        return {"action": "cycle_complete", "cycle": state["cycle"]}

    return {"action": "idle", "reason": "waiting for running steps to complete"}


async def mark_step_completed(
    client: Any,
    user_id: str,
    project_slug: str,
    step_name: str,
    output_preview: str = "",
) -> None:
    """Mark a pipeline step as completed after agent run."""
    state = await read_pipeline_state(client, user_id, project_slug)
    steps = state.get("steps", {})
    now = datetime.now(timezone.utc)

    if step_name in steps:
        steps[step_name]["state"] = "completed"
        steps[step_name]["completed_at"] = now.isoformat()
        if output_preview:
            steps[step_name]["output_preview"] = output_preview[:200]

    state["steps"] = steps
    await write_pipeline_state(client, user_id, project_slug, state)
    logger.info(f"[PIPELINE] {project_slug}: step '{step_name}' completed")
