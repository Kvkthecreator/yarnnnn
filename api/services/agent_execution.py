"""
Agent Execution Service - ADR-042 Simplified Flow + ADR-066 Delivery-First

Single Execute call for agent generation with immediate delivery (no approval gate).

Flow:
  Execute(action="agent.generate", target="agent:uuid")
    → check_agent_freshness() (ADR-049)
    → strategy.gather_context() (ADR-045 + ADR-073)
    → generate_draft_inline()
    → mark_content_retained() (ADR-073)
    → record_source_snapshots() (ADR-049)
    → deliver immediately (ADR-066)
    → write activity_log (ADR-090 Phase 3)

ADR-049 Integration:
- Freshness check before generation
- Targeted sync of stale sources
- Source snapshots recorded for audit trail

ADR-066 Integration:
- No governance/approval gate - agents deliver immediately
- Version status: generating → delivered | failed
- Governance field ignored (backwards compatibility)

This module replaces:
- execute_agent_pipeline() - 3-step orchestrator
- execute_gather_step() - separate gather work_ticket
- execute_synthesize_step() - separate synthesize work_ticket
- execute_stage_step() - validation/staging step

Preserves from agent_pipeline.py:
- Role-specific prompts (ROLE_PROMPTS, build_role_prompt)
- Output validation (validate_output)
"""

import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import httpx

logger = logging.getLogger(__name__)

RENDER_SERVICE_URL = os.environ.get("RENDER_SERVICE_URL", "https://yarnnn-render.onrender.com")

# ADR-130: Type-scoped capability check replaces role-based SKILL_ENABLED_ROLES
from services.agent_framework import has_asset_capabilities

async def _fetch_skill_docs() -> Optional[str]:
    """Fetch SKILL.md content from the output gateway for all available skills.

    ADR-118 D.4: Dynamically discovers available skills from render service
    instead of hard-coded type→folder mapping. Falls back gracefully.
    Called during headless system prompt assembly (ADR-118 D.1).
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # ADR-118 D.4: Discover skills dynamically from render service
            type_to_folder = {}
            try:
                resp = await client.get(f"{RENDER_SERVICE_URL}/skills")
                if resp.status_code == 200:
                    data = resp.json()
                    type_to_folder = data.get("type_to_folder", {})
            except Exception:
                pass

            if not type_to_folder:
                # Fallback: known skill folders (graceful degradation)
                for folder in ["pdf", "pptx", "xlsx", "chart"]:
                    type_to_folder[folder] = folder

            # Fetch SKILL.md for each discovered skill
            skill_sections = []
            for skill_type, folder in type_to_folder.items():
                try:
                    resp = await client.get(f"{RENDER_SERVICE_URL}/skills/{folder}/SKILL.md")
                    if resp.status_code == 200:
                        skill_sections.append(resp.text)
                except Exception:
                    continue

            if skill_sections:
                return "\n\n---\n\n".join(skill_sections)
    except Exception as e:
        logger.warning(f"[GENERATE] Failed to fetch skill docs from output gateway: {e}")
    return None

async def _compose_output_html(
    client, user_id: str, agent_slug: str, output_folder: str,
    title: str = "Output", pending_renders: list = None,
) -> Optional[str]:
    """ADR-130 Phase 2: Post-generation compose step.

    Calls /compose on the render service to convert output.md + asset URLs
    into styled HTML. Writes output.html to the output folder.
    Non-fatal — agent run succeeds even if compose fails.
    """
    from services.workspace import AgentWorkspace

    ws = AgentWorkspace(client, user_id, agent_slug)

    # Read the output.md from the output folder
    output_md_path = f"outputs/{output_folder}/output.md"
    md_content = await ws.read(output_md_path)
    if not md_content:
        logger.warning(f"[COMPOSE] No output.md at {output_md_path}")
        return None

    # Build asset references from pending_renders
    assets = []
    for r in (pending_renders or []):
        url = r.get("output_url") or r.get("content_url")
        path = r.get("path", "")
        if url and path:
            # Extract filename from path for ref matching
            ref = path.split("/")[-1] if "/" in path else path
            assets.append({"ref": ref, "url": url})

    # Call /compose endpoint
    try:
        async with httpx.AsyncClient(timeout=30.0) as http:
            headers = {}
            render_secret = os.environ.get("RENDER_SERVICE_SECRET", "")
            if render_secret:
                headers["X-Render-Secret"] = render_secret

            resp = await http.post(
                f"{RENDER_SERVICE_URL}/compose",
                json={
                    "markdown": md_content,
                    "title": title,
                    "layout_mode": "document",  # default; future: infer from content/project
                    "assets": assets,
                    "user_id": user_id,
                },
                headers=headers,
            )

            if resp.status_code != 200:
                logger.warning(f"[COMPOSE] HTTP {resp.status_code}: {resp.text[:200]}")
                return None

            data = resp.json()
            if not data.get("success"):
                logger.warning(f"[COMPOSE] Failed: {data.get('error')}")
                return None

            html = data.get("html", "")
            if not html:
                return None

            # Write output.html to workspace
            html_path = f"outputs/{output_folder}/output.html"
            await ws.write(html_path, html, summary="Composed HTML output")

            return html

    except Exception as e:
        logger.warning(f"[COMPOSE] Request failed: {e}")
        return None


async def _load_pm_project_context(client, user_id: str, project_slug: str) -> dict:
    """
    Load project context for PM agent's prompt injection.

    Provides the PM with layered context matching its cognitive model:
    - Layer 1 (Commitment): PROJECT.md objective completeness
    - Layer 2 (Structure): team composition vs. objective requirements + type registry
    - Layer 3 (Context): platform connections, freshness, relevance to objective
    - Layer 4-5 (Execution): contributor output, work plan, budget

    Returns dict with keys matching PM role prompt template fields.

    ADR-120 + ADR-121 + PM cognitive model v1.0.
    """
    from services.workspace import ProjectWorkspace
    from services.primitives.project_execution import handle_check_contributor_freshness

    pw = ProjectWorkspace(client, user_id, project_slug)

    # Read project identity
    project = await pw.read_project()
    if not project:
        return {
            "project_context": f"Project '{project_slug}' not found.",
            "commitment_assessment": "UNKNOWN — project not found.",
            "structural_assessment": "UNKNOWN — project not found.",
            "context_assessment": "UNKNOWN — project not found.",
            "contributor_status": "Unknown",
            "work_plan": "No work plan.",
            "budget_status": "Unknown",
            "user_shared_files": "",
            "prior_assessment": "",
        }

    # ── Layer 1: Commitment Clarity ──
    objective = project.get("objective", {})
    obj_fields = {
        "deliverable": objective.get("deliverable"),
        "audience": objective.get("audience"),
        "format": objective.get("format"),
        "purpose": objective.get("purpose"),
    }
    missing_obj = [k for k, v in obj_fields.items() if not v or v == "Not specified"]

    project_lines = [
        f"**Title:** {project.get('title', project_slug)}",
        f"**Type:** {project.get('type_key', 'custom')}",
        f"**Deliverable:** {obj_fields['deliverable'] or 'NOT DEFINED'}",
        f"**Audience:** {obj_fields['audience'] or 'NOT DEFINED'}",
        f"**Format:** {obj_fields['format'] or 'NOT DEFINED'}",
        f"**Purpose:** {obj_fields['purpose'] or 'NOT DEFINED'}",
        f"**Contributors:** {len(project.get('contributors', []))}",
    ]
    if project.get("assembly_spec"):
        project_lines.append(f"**Assembly:** {project['assembly_spec'][:200]}")

    if missing_obj:
        commitment = f"INCOMPLETE — missing: {', '.join(missing_obj)}. Cannot reason about what this project needs without a clear objective."
    else:
        commitment = f"CLEAR — deliverable: {obj_fields['deliverable']}, audience: {obj_fields['audience']}, format: {obj_fields['format']}."

    # ── Layer 2: Structural Capacity ──
    # What does the type registry expect vs what we have?
    type_key = project.get("type_key", "custom")
    structural_lines = []
    try:
        from services.project_registry import get_project_type
        type_def = get_project_type(type_key)
        if type_def:
            expected_contributors = type_def.get("contributors", [])
            # Filter out PM from contributors — PM is infrastructure, not a functional contributor (ADR-122)
            all_contributors = project.get("contributors", [])
            actual_contributors = [
                c for c in all_contributors
                if c.get("expected_contribution") != "project coordination"
            ]
            structural_lines.append(f"Project type '{type_key}' expects {len(expected_contributors)} contributor(s).")
            structural_lines.append(f"Currently has {len(actual_contributors)} contributor(s).")

            # Check if expected roles/scopes are covered
            expected_scopes = {c.get("scope") for c in expected_contributors if c.get("scope")}
            expected_roles = {c.get("role") for c in expected_contributors if c.get("role")}

            # Look up actual agent metadata
            actual_agents = []
            for c in actual_contributors:
                agent_slug = c.get("agent_slug", "")
                if not agent_slug:
                    continue
                try:
                    agent_row = client.table("agents").select(
                        "id, title, role, scope, sources, mode"
                    ).eq("user_id", user_id).eq("slug", agent_slug).limit(1).execute()
                    if agent_row.data:
                        actual_agents.append(agent_row.data[0])
                except Exception:
                    pass

            actual_scopes = {a.get("scope") for a in actual_agents if a.get("scope")}
            actual_roles = {a.get("role") for a in actual_agents if a.get("role")}

            missing_scopes = expected_scopes - actual_scopes
            missing_roles = expected_roles - actual_roles

            if missing_scopes:
                structural_lines.append(f"MISSING SCOPES: {', '.join(missing_scopes)} — objective requires these coverage areas but no agent provides them.")
            if missing_roles:
                structural_lines.append(f"MISSING ROLES: {', '.join(missing_roles)} — expected roles not filled.")

            # Special: cross_platform scope needs multiple platforms
            if "cross_platform" in expected_scopes or "cross_platform" in actual_scopes:
                structural_lines.append("CROSS-PLATFORM: this project requires context from multiple platforms to fulfill its objective.")
        else:
            structural_lines.append(f"Custom project (no type registry template).")
    except Exception as e:
        structural_lines.append(f"(Could not load type registry: {e})")

    structural_assessment = "\n".join(structural_lines) if structural_lines else "No structural issues detected."

    # ── Layer 3: Context Adequacy ──
    # What platforms are connected, how fresh, and are they relevant to the objective?
    context_lines = []
    try:
        from services.freshness import calculate_freshness
        from datetime import datetime, timezone as tz

        conn_result = client.table("platform_connections").select(
            "platform, status"
        ).eq("user_id", user_id).order("platform").execute()

        registry_result = client.table("sync_registry").select(
            "platform, last_synced_at"
        ).eq("user_id", user_id).execute()

        max_synced = {}
        for row in (registry_result.data or []):
            p = row.get("platform", "")
            ts = row.get("last_synced_at")
            if ts and (p not in max_synced or ts > max_synced[p]):
                max_synced[p] = ts

        now = datetime.now(tz.utc)
        connected_platforms = []
        for p in (conn_result.data or []):
            pname = p.get("platform", "unknown")
            last_synced = max_synced.get(pname)
            freshness_str = calculate_freshness(last_synced, now)
            connected_platforms.append(f"{pname} ({p.get('status', '?')}, {freshness_str})")

        if connected_platforms:
            context_lines.append(f"Connected platforms: {', '.join(connected_platforms)}")
        else:
            context_lines.append("NO PLATFORMS CONNECTED — agents have no external context to draw from.")

        # Evaluate relevance: does the objective *need* these platforms?
        platform_count = len(conn_result.data or [])
        if "cross_platform" in (actual_scopes if 'actual_scopes' in dir() else set()):
            if platform_count < 2:
                context_lines.append(f"CONTEXT GAP: cross-platform objective requires 2+ platforms, only {platform_count} connected. The project CANNOT fulfill its stated purpose.")
            else:
                context_lines.append(f"Cross-platform coverage: {platform_count} platforms connected.")

    except Exception as e:
        context_lines.append(f"(Could not load platform context: {e})")

    context_assessment = "\n".join(context_lines) if context_lines else "Context status unknown."

    # ── Layer 4-5: Execution State ──
    # Contributor freshness + content (existing logic)
    class _FakeAuth:
        def __init__(self, c, uid):
            self.client = c
            self.user_id = uid
    fake_auth = _FakeAuth(client, user_id)
    freshness = await handle_check_contributor_freshness(fake_auth, {"project_slug": project_slug})

    contributor_lines = []
    for c in freshness.get("contributors", []):
        slug = c["agent_slug"]
        status = "FRESH" if c["is_fresh"] else "STALE"
        days = f" ({c['days_since']}d ago)" if c["days_since"] is not None else " (never contributed)"
        contributor_lines.append(
            f"### {slug}: {status}{days} — expected: {c.get('expected_contribution', 'unspecified')}"
        )

        # ADR-121: Load contribution content excerpt so PM can assess quality
        try:
            files = await pw.list_contributions(slug)
            for f in files:
                if f == "brief.md":
                    continue  # Skip PM's own briefs
                content = await pw.read(f"contributions/{slug}/{f}")
                if content:
                    excerpt = content[:500]
                    if len(content) > 500:
                        excerpt += f"\n... ({len(content)} chars total)"
                    contributor_lines.append(f"**Latest content ({f}):**\n{excerpt}")
        except Exception:
            contributor_lines.append("(Could not load contribution content)")

        # ADR-121: Show existing brief if any
        try:
            brief = await pw.read_brief(slug)
            if brief:
                contributor_lines.append(f"**Active PM brief:** {brief[:200]}")
        except Exception:
            pass

        # ADR-128 Phase 2: Load contributor self-assessment history
        try:
            from services.workspace import AgentWorkspace
            contributor_ws = AgentWorkspace(client, user_id, slug)
            self_assessment = await contributor_ws.read("memory/self_assessment.md")
            if self_assessment and "Not yet assessed" not in self_assessment:
                # Show most recent entry (up to 300 chars)
                contributor_lines.append(f"**Self-assessment (latest):**\n{self_assessment[:300]}")
        except Exception:
            pass

        # ADR-128 Phase 2: Load latest pulse metadata for this contributor
        try:
            pulse_result = (
                client.table("activity_log")
                .select("summary, created_at, metadata")
                .eq("user_id", user_id)
                .eq("event_type", "agent_pulsed")
                .like("summary", f"%{slug}%")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if pulse_result.data:
                pulse = pulse_result.data[0]
                pulse_meta = pulse.get("metadata", {})
                contributor_lines.append(
                    f"**Last pulse:** {pulse.get('created_at', '?')} — "
                    f"decision: {pulse_meta.get('decision', '?')}, "
                    f"tier: {pulse_meta.get('tier', '?')}"
                )
        except Exception:
            pass

    if freshness.get("last_assembly_date"):
        contributor_lines.append(f"\nLast assembly: {freshness['last_assembly_date']}")
    else:
        contributor_lines.append("\nNo assemblies yet.")

    contributor_lines.append(f"All fresh: {'YES' if freshness.get('all_fresh') else 'NO'}")

    # Read work plan + prior quality assessment
    work_plan = await pw.read("memory/work_plan.md")
    quality_assessment = await pw.read("memory/quality_assessment.md")
    if quality_assessment:
        work_plan = (work_plan or "") + f"\n\n---\n\n## Prior Quality Assessment\n{quality_assessment}"

    # ADR-123: Migrate legacy intentions to work_plan if present
    legacy_intentions = project.get("legacy_intentions", [])
    if legacy_intentions and not work_plan:
        lines = ["## Execution Plan (migrated from legacy intentions)"]
        for i in legacy_intentions:
            itype = i.get("type", "recurring")
            desc = i.get("description", "")
            parts = [f"- {itype}: {desc}"]
            if i.get("format"):
                parts.append(f"  format: {i['format']}")
            if i.get("delivery"):
                d = i["delivery"]
                if isinstance(d, dict):
                    parts.append(f"  delivery: {d.get('channel', '')} → {d.get('target', '')}")
            if i.get("budget"):
                parts.append(f"  budget: {i['budget']}")
            lines.extend(parts)
        migrated_plan = "\n".join(lines)
        await pw.write("memory/work_plan.md", migrated_plan,
                        summary="Migrated legacy intentions to work plan",
                        tags=["work_plan", "migration"])
        work_plan = migrated_plan

    # ADR-127: List user_shared/ files so PM can triage
    user_shared_lines = []
    try:
        shared_files = await pw.list("user_shared/")
        for sf in (shared_files or []):
            content = await pw.read(f"user_shared/{sf}")
            excerpt = (content[:300] + f"\n... ({len(content)} chars)") if content and len(content) > 300 else (content or "(empty)")
            user_shared_lines.append(f"- **{sf}**: {excerpt}")
    except Exception:
        pass

    # Work budget status
    budget_status = "Unknown"
    try:
        from services.platform_limits import check_work_budget
        budget_ok, wu_used, wu_limit = check_work_budget(client, user_id)
        pct = int(wu_used / wu_limit * 100) if wu_limit > 0 else 0
        if not budget_ok:
            budget_status = f"EXHAUSTED — {wu_used}/{wu_limit} units used (100%)"
        elif pct >= 80:
            budget_status = f"LOW — {wu_used}/{wu_limit} units used ({pct}%)"
        else:
            budget_status = f"OK — {wu_used}/{wu_limit} units used ({pct}%)"
    except Exception:
        pass

    # Prior project assessment (PM's own evolving cognitive state)
    prior_assessment = await pw.read("memory/project_assessment.md") or ""

    return {
        "project_context": "\n".join(project_lines),
        "commitment_assessment": commitment,
        "structural_assessment": structural_assessment,
        "context_assessment": context_assessment,
        "contributor_status": "\n".join(contributor_lines) if contributor_lines else "No contributors listed.",
        "work_plan": work_plan or "No work plan set.",
        "budget_status": budget_status,
        "user_shared_files": "\n".join(user_shared_lines) if user_shared_lines else "",
        "prior_assessment": prior_assessment,
    }


async def _write_contribution_to_projects(client, user_id: str, agent_slug: str, content: str):
    """
    ADR-121: Write agent output to all projects this agent contributes to.

    Reads memory/projects.json to find project memberships, then writes
    content to /projects/{slug}/contributions/{agent_slug}/output.md.
    This is the bridge between agent output and PM quality assessment.
    """
    from services.workspace import AgentWorkspace, ProjectWorkspace

    ws = AgentWorkspace(client, user_id, agent_slug)
    projects_json = await ws.read("memory/projects.json")
    if not projects_json:
        return

    import json as _json
    try:
        projects = _json.loads(projects_json)
    except _json.JSONDecodeError:
        return

    for project_entry in projects:
        project_slug = project_entry.get("project_slug")
        if not project_slug:
            continue
        try:
            pw = ProjectWorkspace(client, user_id, project_slug)
            await pw.contribute(
                agent_slug=agent_slug,
                filename="output.md",
                content=content,
                summary=f"Latest output from {agent_slug}",
            )
            logger.info(f"[CONTRIB] Wrote {agent_slug} output to project {project_slug}")
        except Exception as e:
            logger.warning(f"[CONTRIB] Failed to write {agent_slug} to {project_slug}: {e}")


async def _maybe_trigger_project_heartbeat(client, user_id: str, agent: dict, agent_slug: str):
    """
    ADR-120/122: After a contributor produces output, check if it belongs to any project.

    Single-contributor projects: inline PM passthrough — skip PM LLM call, deliver
    immediately via _execute_pm_assemble() (which detects single-contributor and
    passes content through without composition).

    Multi-contributor projects: advance PM schedule to now (debounced by 1 hour)
    so PM runs on next scheduler cycle.
    """
    from services.workspace import AgentWorkspace, ProjectWorkspace

    ws = AgentWorkspace(client, user_id, agent_slug)

    # Read agent's project memberships
    projects_json = await ws.read("memory/projects.json")
    if not projects_json:
        return  # Agent isn't in any projects

    import json as _json
    try:
        projects = _json.loads(projects_json)
    except _json.JSONDecodeError:
        return

    if not projects:
        return

    for project_entry in projects:
        project_slug = project_entry.get("project_slug")
        if not project_slug:
            continue

        pw = ProjectWorkspace(client, user_id, project_slug)

        # Read PM agent reference
        pm_json = await pw.read("memory/pm_agent.json")
        if not pm_json:
            continue

        try:
            pm_ref = _json.loads(pm_json)
        except _json.JSONDecodeError:
            continue

        pm_agent_id = pm_ref.get("pm_agent_id")
        if not pm_agent_id:
            continue

        # Check contributor count to decide passthrough vs. full PM run
        contributor_slugs = await pw.list_contributors()
        is_single_contributor = len(contributor_slugs) <= 1

        if is_single_contributor:
            # Single-contributor passthrough: deliver inline, skip PM LLM call
            try:
                pm_agent_result = (
                    client.table("agents")
                    .select("*")
                    .eq("id", pm_agent_id)
                    .eq("user_id", user_id)
                    .maybe_single()
                    .execute()
                )
                if not pm_agent_result or not pm_agent_result.data:
                    continue

                result = await _execute_pm_assemble(
                    client, user_id, pm_agent_result.data,
                    project_slug,
                    pm_agent_result.data.get("type_config") or {"project_slug": project_slug},
                )

                if result.get("success"):
                    logger.info(
                        f"[PM_PASSTHROUGH] Inline delivery for {project_slug} "
                        f"(triggered by {agent_slug}): {result.get('delivery_status', 'no delivery config')}"
                    )
                else:
                    logger.warning(f"[PM_PASSTHROUGH] Failed for {project_slug}: {result.get('error')}")

            except Exception as e:
                logger.warning(f"[PM_PASSTHROUGH] Inline delivery failed for {project_slug}: {e}")
            continue

        # Multi-contributor: advance PM schedule (existing behavior)
        try:
            pm_result = (
                client.table("agents")
                .select("id, last_run_at, next_pulse_at")
                .eq("id", pm_agent_id)
                .eq("user_id", user_id)
                .eq("status", "active")
                .maybe_single()
                .execute()
            )
            if not pm_result or not pm_result.data:
                continue

            pm_agent = pm_result.data
            last_run = pm_agent.get("last_run_at")

            # Debounce: check if PM ran in the last hour
            if last_run:
                last_dt = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
                hours_since = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
                if hours_since < 1:
                    logger.info(
                        f"[PM_HEARTBEAT] Debounce: PM {pm_agent_id} ran {hours_since:.1f}h ago for {project_slug}, skipping"
                    )
                    continue

            # Advance PM schedule to now
            now = datetime.now(timezone.utc).isoformat()
            client.table("agents").update({
                "next_pulse_at": now,
                "updated_at": now,
            }).eq("id", pm_agent_id).execute()

            logger.info(
                f"[PM_HEARTBEAT] ADR-120: Advanced PM {pm_agent_id} for project {project_slug} "
                f"(triggered by {agent_slug})"
            )

        except Exception as e:
            logger.warning(f"[PM_HEARTBEAT] Failed to advance PM for {project_slug}: {e}")


# =============================================================================
# ADR-120 Phase 2: PM Decision Interpreter + Assembly Execution
# =============================================================================


async def _handle_pm_decision(
    client,
    user_id: str,
    agent: dict,
    draft: str,
    type_config: dict,
    version_id: str,
    next_version: int,
    usage: dict,
) -> dict:
    """
    Interpret PM agent's JSON decision and act on it.

    PM outputs structured JSON with actions (ADR-120 + ADR-121):
    - assemble, advance_contributor, wait, escalate, update_work_plan (ADR-120)
    - steer_contributor, assess_quality (ADR-121 — intelligence director)

    Returns result dict with pm_action, success, and action-specific details.
    """
    import json as _json

    project_slug = type_config.get("project_slug", "")

    # Parse PM decision — try raw JSON first, then extract from narrative
    decision = None
    try:
        decision = _json.loads(draft.strip())
    except _json.JSONDecodeError:
        # ADR-121: PM v3.0 sometimes writes narrative preamble before JSON.
        # Extract the outermost JSON object containing "action" by brace-balancing.
        action_pos = draft.find('"action"')
        if action_pos >= 0:
            # Walk backwards to find the opening brace
            start = draft.rfind('{', 0, action_pos)
            if start >= 0:
                # Walk forward balancing braces to find the closing brace
                depth = 0
                in_string = False
                escape = False
                end = None
                for i in range(start, len(draft)):
                    c = draft[i]
                    if escape:
                        escape = False
                        continue
                    if c == '\\' and in_string:
                        escape = True
                        continue
                    if c == '"' and not escape:
                        in_string = not in_string
                        continue
                    if in_string:
                        continue
                    if c == '{':
                        depth += 1
                    elif c == '}':
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break
                if end:
                    try:
                        decision = _json.loads(draft[start:end])
                        logger.info(f"[PM] Extracted JSON from narrative output (brace-balanced)")
                    except _json.JSONDecodeError:
                        pass

    if decision is None:
        # Last resort: infer action from content keywords
        draft_lower = draft.lower()
        if "ready" in draft_lower and "assembl" in draft_lower:
            decision = {"action": "assemble", "reason": "PM indicated readiness for assembly (inferred from narrative output)"}
            logger.info(f"[PM] Inferred 'assemble' from narrative output")
        else:
            logger.warning(f"[PM] Failed to parse PM decision as JSON: {draft[:200]}")
            return {
                "pm_action": "parse_error",
                "success": False,
                "error": "PM output was not valid JSON",
            }

    action = decision.get("action", "unknown")
    reason = decision.get("reason", "")
    target_agent = decision.get("target_agent", "")
    details = decision.get("details", "")

    logger.info(f"[PM] Decision for {project_slug}: action={action}, reason={reason}")

    # ADR-126: Log PM coordination pulse as pm_pulsed event
    try:
        from services.activity_log import write_activity
        await write_activity(
            client=client, user_id=user_id,
            event_type="pm_pulsed",
            summary=f"PM pulsed: {action} — {reason[:80]}" if reason else f"PM pulsed: {action}",
            event_ref=agent.get("id"),
            metadata={"project_slug": project_slug,
                      "action": action,
                      "reason": reason,
                      "tier": 3,
                      "target_agent": target_agent},
        )
    except Exception:
        pass  # Non-fatal

    # ADR-117 Phase 3: Write project_heartbeat activity event
    try:
        from services.activity_log import write_activity
        await write_activity(
            client=client, user_id=user_id,
            event_type="project_heartbeat",
            summary=f"{project_slug} PM checked on contributors — action: {action}",
            event_ref=agent.get("id"),
            metadata={"project_slug": project_slug,
                      "pm_action": action,
                      "reason": reason},
        )
    except Exception:
        pass  # Non-fatal

    # PM cognitive model v1.0: Extract and persist project_assessment to workspace
    project_assessment = decision.get("project_assessment")
    if project_assessment and project_slug:
        try:
            from services.workspace import ProjectWorkspace as _PW
            _pw = _PW(client, user_id, project_slug)
            # Format assessment as readable markdown
            constraint = project_assessment.get("constraint_layer", "?")
            assessment_md = (
                f"# Project Assessment — {project_slug}\n\n"
                f"**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"
                f"**Current Constraint:** Layer {constraint} — {project_assessment.get('constraint_summary', 'unknown')}\n\n"
                f"## Layer Evaluation\n\n"
                f"1. **Commitment:** {project_assessment.get('layer_1_commitment', 'unknown')}\n"
                f"2. **Structure:** {project_assessment.get('layer_2_structure', 'unknown')}\n"
                f"3. **Context:** {project_assessment.get('layer_3_context', 'unknown')}\n"
                f"4. **Quality:** {project_assessment.get('layer_4_quality', 'unknown')}\n"
                f"5. **Readiness:** {project_assessment.get('layer_5_readiness', 'unknown')}\n\n"
                f"**Action taken:** {action} — {reason}\n"
            )
            await _pw.write(
                "memory/project_assessment.md", assessment_md,
                summary=f"PM assessment: constraint at layer {constraint}",
                tags=["project_assessment", "pm"],
            )
            logger.info(f"[PM] Wrote project_assessment.md: constraint_layer={constraint}")
        except Exception as e:
            logger.warning(f"[PM] Failed to write project_assessment.md: {e}")

    # ADR-120 P4: Graceful degradation — override to escalate if budget exhausted
    if action in ("assemble", "advance_contributor") and action != "escalate":
        try:
            from services.platform_limits import check_work_budget
            budget_ok, wu_used, wu_limit = check_work_budget(client, user_id)
            if not budget_ok:
                logger.info(f"[PM] Budget exhausted ({wu_used}/{wu_limit}), overriding {action} → escalate")
                action = "escalate"
                reason = f"Work budget exhausted ({wu_used}/{wu_limit} units). Original action was {decision.get('action')}: {reason}"
                details = "PM paused due to budget exhaustion. Resume when budget resets or is increased."
        except Exception:
            pass  # Non-fatal — proceed with original action

    if action == "assemble":
        try:
            # ADR-121: Pass PM's quality notes to assembly composition
            quality_notes = decision.get("quality_notes", "")
            if quality_notes:
                type_config["quality_notes"] = quality_notes

            # ADR-121 P2: Log if assembling without recent quality assessment
            try:
                from services.workspace import ProjectWorkspace as _PW
                _pw = _PW(client, user_id, project_slug)
                qa = await _pw.read("memory/quality_assessment.md")
                if not qa:
                    logger.info(f"[PM] Assembling {project_slug} without prior quality assessment")
                else:
                    logger.info(f"[PM] Assembling {project_slug} with quality assessment on file")
            except Exception:
                pass

            result = await _execute_pm_assemble(client, user_id, agent, project_slug, type_config)
            # ADR-117 Phase 3: Project activity event
            if result.get("success"):
                try:
                    from services.activity_log import write_activity
                    await write_activity(
                        client=client, user_id=user_id,
                        event_type="project_assembled",
                        summary=f"{project_slug} assembled — delivered to team",
                        event_ref=agent.get("id"),
                        metadata={"project_slug": project_slug,
                                  "assembly_folder": result.get("assembly_folder"),
                                  "delivery_status": result.get("delivery_status")},
                    )
                except Exception:
                    pass  # Non-fatal
            return {
                "pm_action": "assemble",
                "success": result.get("success", False),
                "reason": reason,
                "assembly_folder": result.get("assembly_folder"),
                "delivery_status": result.get("delivery_status"),
                "error": result.get("error"),
            }
        except Exception as e:
            logger.error(f"[PM] Assembly execution failed: {e}")
            return {"pm_action": "assemble", "success": False, "error": str(e)}

    elif action == "advance_contributor":
        try:
            from services.primitives.project_execution import handle_request_contributor_advance

            class _FakeAuth:
                def __init__(self, c, uid):
                    self.client = c
                    self.user_id = uid

            result = await handle_request_contributor_advance(
                _FakeAuth(client, user_id),
                {
                    "project_slug": project_slug,
                    "agent_slug": target_agent,
                    "reason": reason or "PM requested advance",
                },
            )
            # ADR-117 Phase 3: Project activity event
            if result.get("success"):
                try:
                    from services.activity_log import write_activity
                    await write_activity(
                        client=client, user_id=user_id,
                        event_type="project_contributor_advanced",
                        summary=f"{project_slug} PM asked {target_agent} to run now",
                        event_ref=agent.get("id"),
                        metadata={"project_slug": project_slug,
                                  "target_agent_slug": target_agent,
                                  "reason": reason},
                    )
                except Exception:
                    pass  # Non-fatal
            return {
                "pm_action": "advance_contributor",
                "success": result.get("success", False),
                "target_agent": target_agent,
                "reason": reason,
                "message": result.get("message", ""),
            }
        except Exception as e:
            logger.error(f"[PM] Advance contributor failed: {e}")
            return {"pm_action": "advance_contributor", "success": False, "error": str(e)}

    elif action == "steer_contributor":
        # ADR-121: PM writes a contribution brief then advances the contributor
        try:
            from services.workspace import ProjectWorkspace

            brief_content = decision.get("brief", "")
            if not brief_content:
                return {"pm_action": "steer_contributor", "success": False,
                        "error": "No brief content provided in PM decision"}

            pw = ProjectWorkspace(client, user_id, project_slug)
            await pw.write_brief(target_agent, brief_content)
            logger.info(f"[PM] Wrote brief for {target_agent} in {project_slug}")

            # After writing brief, advance the contributor so they run with the new directive
            try:
                from services.primitives.project_execution import handle_request_contributor_advance

                class _FakeAuth:
                    def __init__(self, c, uid):
                        self.client = c
                        self.user_id = uid

                await handle_request_contributor_advance(
                    _FakeAuth(client, user_id),
                    {
                        "project_slug": project_slug,
                        "agent_slug": target_agent,
                        "reason": f"PM steered with brief: {reason[:80]}",
                    },
                )
            except Exception as e:
                logger.warning(f"[PM] Brief written but advance failed: {e}")
                # Brief still written — contributor will pick it up on next scheduled run

            # Activity event
            try:
                from services.activity_log import write_activity
                await write_activity(
                    client=client, user_id=user_id,
                    event_type="project_contributor_steered",
                    summary=f"{project_slug} PM directed {target_agent}: {reason[:60]}",
                    event_ref=agent.get("id"),
                    metadata={"project_slug": project_slug,
                              "target_agent_slug": target_agent,
                              "reason": reason,
                              "brief_excerpt": brief_content[:200]},
                )
            except Exception:
                pass  # Non-fatal

            return {
                "pm_action": "steer_contributor",
                "success": True,
                "target_agent": target_agent,
                "reason": reason,
                "brief_written": True,
            }
        except Exception as e:
            logger.error(f"[PM] Steer contributor failed: {e}")
            return {"pm_action": "steer_contributor", "success": False, "error": str(e)}

    elif action == "assess_quality":
        # ADR-121: PM assessed contribution quality — log assessments, no side effects
        # The assessment itself is the value — PM will follow up with assemble/steer/wait
        assessments = decision.get("assessments", [])
        logger.info(f"[PM] Quality assessment for {project_slug}: {len(assessments)} contributors assessed")

        # Write assessment to project workspace for observability
        try:
            from services.workspace import ProjectWorkspace
            import json as _aq_json

            pw = ProjectWorkspace(client, user_id, project_slug)
            assessment_lines = [
                f"# Quality Assessment — {project_slug}",
                f"\n**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                f"**Reason:** {reason}",
            ]
            for a in assessments:
                slug = a.get("agent_slug", "?")
                verdict = a.get("verdict", "unknown")
                assessment_lines.append(f"\n## {slug}")
                assessment_lines.append(f"- **Coverage:** {a.get('coverage', 'unknown')}")
                assessment_lines.append(f"- **Depth:** {a.get('depth', 'unknown')}")
                assessment_lines.append(f"- **Differentiation:** {a.get('differentiation', 'unknown')}")
                assessment_lines.append(f"- **Verdict:** {verdict}")
                if a.get("notes"):
                    assessment_lines.append(f"- **Notes:** {a['notes']}")

            await pw.write(
                "memory/quality_assessment.md",
                "\n".join(assessment_lines),
                summary=f"Quality assessment: {reason[:80]}",
            )
        except Exception as e:
            logger.warning(f"[PM] Failed to write quality assessment: {e}")

        # Activity event
        try:
            from services.activity_log import write_activity
            verdicts = {a.get("agent_slug", "?"): a.get("verdict", "?") for a in assessments}
            await write_activity(
                client=client, user_id=user_id,
                event_type="project_quality_assessed",
                summary=f"{project_slug} PM assessed quality: {verdicts}",
                event_ref=agent.get("id"),
                metadata={"project_slug": project_slug,
                          "assessments": assessments,
                          "reason": reason},
            )
        except Exception:
            pass  # Non-fatal

        return {
            "pm_action": "assess_quality",
            "success": True,
            "reason": reason,
            "assessments": assessments,
        }

    elif action == "update_work_plan":
        # ADR-120 P4: PM decomposes intent into operational work plan
        try:
            import json as _wp_json
            from services.workspace import ProjectWorkspace

            work_plan_data = decision.get("work_plan", {})
            pw = ProjectWorkspace(client, user_id, project_slug)

            # Format work plan as markdown
            wp_lines = [
                f"# Work Plan — {project_slug}",
                f"\n**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
                f"**Reason:** {reason}",
            ]
            if work_plan_data.get("assembly_cadence"):
                wp_lines.append(f"\n## Assembly Cadence\n{work_plan_data['assembly_cadence']}")
            if work_plan_data.get("budget_per_cycle"):
                wp_lines.append(f"\n## Budget per Cycle\n{work_plan_data['budget_per_cycle']} work units")
            if work_plan_data.get("contributors"):
                wp_lines.append("\n## Contributors")
                for c in work_plan_data["contributors"]:
                    cadence = c.get("expected_cadence", "as needed")
                    skills = ", ".join(c.get("skills", []))
                    focus = ", ".join(c.get("focus_areas", []))
                    line = f"- {c.get('slug', '?')}: cadence={cadence}, skills={skills}"
                    if focus:
                        line += f", focus=[{focus}]"
                    wp_lines.append(line)
            if work_plan_data.get("skill_sequence"):
                wp_lines.append(f"\n## Skill Sequence\n{' → '.join(work_plan_data['skill_sequence'])}")
            if work_plan_data.get("notes"):
                wp_lines.append(f"\n## Notes\n{work_plan_data['notes']}")

            await pw.write(
                "memory/work_plan.md",
                "\n".join(wp_lines),
                summary=f"Work plan: {reason[:80]}",
            )

            logger.info(f"[PM] Work plan written for {project_slug}: {reason}")
            return {"pm_action": "update_work_plan", "success": True, "reason": reason}
        except Exception as e:
            logger.error(f"[PM] Failed to write work plan: {e}")
            return {"pm_action": "update_work_plan", "success": False, "error": str(e)}

    elif action == "triage_file":
        # ADR-127: PM triages a user-shared file — promote to destination or ignore
        try:
            from services.workspace import ProjectWorkspace

            source_file = decision.get("source_file", "")
            destination = decision.get("destination", "")
            action_type = decision.get("action_type", "promote")

            if not source_file:
                return {"pm_action": "triage_file", "success": False, "error": "No source_file specified"}

            pw = ProjectWorkspace(client, user_id, project_slug)

            if action_type == "ignore":
                logger.info(f"[PM] Ignoring user_shared file {source_file} in {project_slug}: {reason}")
                return {"pm_action": "triage_file", "success": True, "action_type": "ignore",
                        "source_file": source_file, "reason": reason}

            if not destination:
                return {"pm_action": "triage_file", "success": False, "error": "No destination for promote"}

            # Read source content
            content = await pw.read(source_file)
            if not content:
                return {"pm_action": "triage_file", "success": False,
                        "error": f"Source file not found: {source_file}"}

            # Write to destination (contributions/, memory/, etc.)
            await pw.write(destination, content,
                           summary=f"Promoted from {source_file}: {reason[:80]}")

            logger.info(f"[PM] Triaged {source_file} → {destination} in {project_slug}")

            # Activity event
            try:
                from services.activity_log import write_activity
                await write_activity(
                    client=client, user_id=user_id,
                    event_type="project_file_triaged",
                    summary=f"{project_slug} PM triaged {source_file} → {destination}",
                    event_ref=agent.get("id"),
                    metadata={"project_slug": project_slug,
                              "source_file": source_file,
                              "destination": destination,
                              "action_type": action_type,
                              "reason": reason},
                )
            except Exception:
                pass  # Non-fatal

            return {
                "pm_action": "triage_file",
                "success": True,
                "action_type": action_type,
                "source_file": source_file,
                "destination": destination,
                "reason": reason,
            }
        except Exception as e:
            logger.error(f"[PM] Triage file failed: {e}")
            return {"pm_action": "triage_file", "success": False, "error": str(e)}

    elif action == "wait":
        logger.info(f"[PM] Waiting on {project_slug}: {reason}")
        return {"pm_action": "wait", "success": True, "reason": reason}

    elif action == "escalate":
        # Write escalation note to project workspace for TP visibility
        try:
            from services.workspace import ProjectWorkspace

            pw = ProjectWorkspace(client, user_id, project_slug)
            await pw.write(
                "memory/escalation.md",
                f"# PM Escalation\n\n**Date:** {datetime.now(timezone.utc).isoformat()}\n"
                f"**Reason:** {reason}\n**Details:** {details}\n",
                summary=f"PM escalation: {reason[:80]}",
            )
        except Exception as e:
            logger.warning(f"[PM] Failed to write escalation note: {e}")

        # ADR-117 Phase 3: Project activity event
        try:
            from services.activity_log import write_activity
            await write_activity(
                client=client, user_id=user_id,
                event_type="project_escalated",
                summary=f"{project_slug} PM needs help — {reason[:80]}",
                event_ref=agent.get("id"),
                metadata={"project_slug": project_slug,
                          "reason": reason,
                          "target_agent": target_agent},
            )
        except Exception:
            pass  # Non-fatal

        logger.info(f"[PM] Escalating {project_slug}: {reason}")
        return {"pm_action": "escalate", "success": True, "reason": reason, "details": details}

    else:
        logger.warning(f"[PM] Unknown action '{action}' for {project_slug}")
        return {"pm_action": action, "success": False, "error": f"Unknown PM action: {action}"}


async def _execute_pm_assemble(
    client,
    user_id: str,
    agent: dict,
    project_slug: str,
    type_config: dict,
) -> dict:
    """
    Execute full assembly pipeline: gather contributions → compose → write → deliver.

    ADR-120 Phase 2: PM decides WHEN; this function decides WHAT.
    """
    from services.workspace import ProjectWorkspace
    from services.supabase import get_service_client as _get_svc

    svc_client = _get_svc()
    pw = ProjectWorkspace(svc_client, user_id, project_slug)

    # 1. Read project identity
    project = await pw.read_project()
    if not project:
        return {"success": False, "error": f"Project not found: {project_slug}"}

    # 2. Gather all contributions
    contributor_slugs = await pw.list_contributors()
    if not contributor_slugs:
        return {"success": False, "error": "No contributions found"}

    contributions = {}
    source_paths = []
    for slug in contributor_slugs:
        files = await pw.list_contributions(slug)
        for f in files:
            if f == "brief.md":
                continue  # ADR-121: Skip PM briefs — they're directives, not content
            content = await pw.read(f"contributions/{slug}/{f}")
            if content:
                contributions.setdefault(slug, []).append({"file": f, "content": content})
                source_paths.append(f"/projects/{project_slug}/contributions/{slug}/{f}")

    if not contributions:
        return {"success": False, "error": "All contribution files are empty"}

    # 2b. Single-contributor passthrough — skip LLM composition for single-agent projects.
    # When there's only one contributor, the contribution IS the output. No synthesis needed.
    all_files = [f for slug_files in contributions.values() for f in slug_files]
    is_passthrough = len(contributions) == 1 and len(all_files) == 1

    if is_passthrough:
        # Passthrough: use contribution content directly, no LLM call
        sole_file = all_files[0]
        composed_text = sole_file["content"]
        pending_renders = None
        logger.info(f"[PM] Single-contributor passthrough for project {project_slug}")
    else:
        # ADR-121: Read quality assessment + quality_notes from PM decision
        quality_assessment = await pw.read("memory/quality_assessment.md")
        if quality_assessment:
            project["quality_notes"] = quality_assessment
        # Also pick up quality_notes from the PM's assemble decision if present
        if type_config.get("quality_notes"):
            project["quality_notes"] = type_config["quality_notes"]

        # 3. Compose assembly via LLM
        try:
            composed_text, comp_usage, pending_renders = await _compose_assembly(
                svc_client, user_id, project, contributions,
            )
        except Exception as e:
            logger.error(f"[PM] Composition LLM call failed: {e}")
            return {"success": False, "error": f"Composition failed: {e}"}

        if not composed_text:
            return {"success": False, "error": "Composition produced empty output"}

    # 4. Determine assembly version number
    existing_assemblies = await pw.list_assemblies()
    version = len(existing_assemblies) + 1

    # 5. Write assembled output
    assembly_folder = await pw.assemble(
        content=composed_text,
        rendered_files=pending_renders if pending_renders else None,
        version=version,
        sources=source_paths,
    )
    if not assembly_folder:
        return {"success": False, "error": "Failed to write assembly folder"}

    logger.info(f"[PM] ADR-120 P2: Assembly v{version} written to /projects/{project_slug}/{assembly_folder}/")

    # ADR-120 Phase 3: Record assembly work units (2 for composition, 0 for passthrough)
    if not is_passthrough:
        try:
            from services.platform_limits import record_work_units as _record_wu_asm
            _record_wu_asm(svc_client, user_id, "assembly", 2, metadata={"project_slug": project_slug, "version": version})
        except Exception:
            pass  # Non-fatal

    # 6. Deliver if project has delivery config
    delivery_status = None
    delivery = project.get("delivery", {})
    if delivery and delivery.get("channel"):
        try:
            from services.delivery import deliver_from_assembly_folder

            # Resolve user email for email delivery
            user_email = get_user_email(svc_client, user_id)
            delivery_result = await deliver_from_assembly_folder(
                client=svc_client,
                user_id=user_id,
                project=project,
                project_slug=project_slug,
                assembly_folder=assembly_folder,
                user_email=user_email,
            )
            delivery_status = delivery_result.status.value if delivery_result else None
            logger.info(f"[PM] Assembly delivery: {delivery_status}")
        except Exception as e:
            logger.warning(f"[PM] Assembly delivery failed (non-fatal): {e}")
            delivery_status = "failed"

    return {
        "success": True,
        "assembly_folder": assembly_folder,
        "version": version,
        "delivery_status": delivery_status,
        "contributors": list(contributions.keys()),
    }


async def _compose_assembly(
    client,
    user_id: str,
    project: dict,
    contributions: dict,
) -> tuple:
    """
    Composition LLM call: combine contributions into a cohesive deliverable.

    Uses chat_completion_with_tools with RuntimeDispatch access for rendered outputs.
    Returns (composed_text, usage, pending_renders).
    """
    from services.anthropic import chat_completion_with_tools
    from services.primitives.registry import (
        get_tools_for_mode,
        create_headless_executor,
    )
    from services.agent_pipeline import ASSEMBLY_COMPOSITION_PROMPT

    import json as _json

    # Build contributions text
    contrib_sections = []
    for slug, files in contributions.items():
        section = f"### Contributor: {slug}\n"
        for f in files:
            section += f"\n**{f['file']}:**\n{f['content']}\n"
        contrib_sections.append(section)
    contributions_text = "\n---\n".join(contrib_sections)

    # Build objective description (ADR-123: renamed from intent)
    objective = project.get("objective", {})
    objective_str = ", ".join(f"{k}: {v}" for k, v in objective.items() if v) or "Not specified"

    # Format composition prompt (ADR-121: v2.0 with quality_notes)
    prompt = ASSEMBLY_COMPOSITION_PROMPT.format(
        title=project.get("title", "Untitled Project"),
        objective=objective_str,
        assembly_spec=project.get("assembly_spec", "Combine contributions into a cohesive deliverable."),
        quality_notes=project.get("quality_notes", "No quality assessment available — compose with best judgment."),
        contributions=contributions_text,
    )

    # Build system prompt with skill docs
    system = """You are composing a project deliverable from multiple agent contributions.

## Output Rules
- Produce a cohesive, well-structured document that integrates all contributions.
- Do not simply concatenate — synthesize and organize for the target audience.
- Use markdown formatting (headers, bullets, tables) for clarity.
- If a rendered format is specified (pptx, pdf, xlsx), use RuntimeDispatch to produce it.
- Always produce a text (markdown) version as the primary output.
- Do not narrate the composition process — just produce the final document."""

    # Add skill docs for RuntimeDispatch access
    skill_docs = await _fetch_skill_docs()
    if skill_docs:
        system += f"""

## Output Skill Documentation
You have access to RuntimeDispatch for producing binary artifacts.
Construct input specs according to these skill instructions:

{skill_docs}

When the project intent specifies a rendered format (PPTX, PDF, XLSX, chart),
use RuntimeDispatch to produce it alongside the text version."""

    # Create executor with RuntimeDispatch access
    # Use a synthetic agent to enable workspace writes for rendered files
    headless_tools = get_tools_for_mode("headless")
    executor = create_headless_executor(client, user_id)

    # Run composition with tool rounds (for RuntimeDispatch)
    messages = [{"role": "user", "content": prompt}]

    total_input_tokens = 0
    total_output_tokens = 0
    composed_text = ""

    for round_num in range(4):  # max 3 tool rounds
        response = await chat_completion_with_tools(
            messages=messages,
            system=system,
            tools=headless_tools,
            model=SONNET_MODEL,
            max_tokens=8000,
        )

        if response.usage:
            total_input_tokens += response.usage.get("input_tokens", 0)
            total_output_tokens += response.usage.get("output_tokens", 0)

        if response.stop_reason in ("end_turn", "max_tokens") or not response.tool_uses:
            composed_text = (response.text or "").strip()
            break

        if round_num >= 3:
            composed_text = (response.text or "").strip()
            break

        # Execute tools
        assistant_content = []
        if response.text:
            assistant_content.append({"type": "text", "text": response.text})
        for tu in response.tool_uses:
            assistant_content.append({
                "type": "tool_use",
                "id": tu.id,
                "name": tu.name,
                "input": tu.input,
            })
        messages.append({"role": "assistant", "content": assistant_content})

        tool_results = []
        for tu in response.tool_uses:
            logger.info(f"[COMPOSE] Tool: {tu.name}({str(tu.input)[:100]})")
            result = await executor(tu.name, tu.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": _json.dumps(result) if isinstance(result, dict) else str(result),
            })
        messages.append({"role": "user", "content": tool_results})

    # Collect rendered files from executor
    pending_renders = getattr(executor, "auth", None)
    pending_renders = getattr(pending_renders, "pending_renders", []) if pending_renders else []

    usage = {"input_tokens": total_input_tokens, "output_tokens": total_output_tokens}
    logger.info(f"[COMPOSE] Composition done: {len(composed_text)} chars, {len(pending_renders)} renders, tokens: {total_input_tokens}/{total_output_tokens}")

    return composed_text, usage, pending_renders


# Model constants
SONNET_MODEL = "claude-sonnet-4-20250514"


def get_user_email(client, user_id: str) -> Optional[str]:
    """Get user's email from auth.users for email-first delivery."""
    try:
        # Query auth.users via Supabase admin API
        result = client.auth.admin.get_user_by_id(user_id)
        if result and result.user and result.user.email:
            return result.user.email
    except Exception as e:
        logger.warning(f"[EXEC] Failed to get user email: {e}")
    return None


async def _resolve_project_delivery(client, user_id: str, agent_id: str) -> Optional[dict]:
    """Resolve delivery config from agent's project (ADR-122: agents produce, projects deliver)."""
    try:
        from services.workspace import AgentWorkspace, get_agent_slug
        import json as _json

        # Look up agent's project membership via workspace memory/projects.json
        agent_data = client.table("agents").select("title").eq("id", agent_id).single().execute()
        if not agent_data.data:
            return None
        slug = get_agent_slug(agent_data.data)
        ws = AgentWorkspace(client, user_id, slug)
        projects_raw = await ws.read("memory/projects.json")
        if not projects_raw:
            return None

        projects = _json.loads(projects_raw)
        if not projects:
            return None

        # Read the first project's delivery config from PROJECT.md
        from services.workspace import ProjectWorkspace
        project_slug = projects[0].get("project_slug")
        if not project_slug:
            return None

        pw = ProjectWorkspace(client, user_id, project_slug)
        project = await pw.read_project()
        if not project:
            return None

        delivery = project.get("delivery", {})
        if delivery and (delivery.get("channel") or delivery.get("target")):
            # Translate PROJECT.md "channel" → destination "platform"
            dest = {}
            if delivery.get("channel"):
                dest["platform"] = delivery["channel"]
            if delivery.get("target"):
                dest["target"] = delivery["target"]
            dest["format"] = "send"
            logger.info(f"[EXEC] ADR-122: Resolved delivery from project '{project_slug}': {dest}")
            return dest
    except Exception as e:
        logger.warning(f"[EXEC] ADR-122: Failed to resolve project delivery: {e}")
    return None


def normalize_destination_for_delivery(
    destination: Optional[dict],
    user_email: Optional[str],
) -> Optional[dict]:
    """
    Normalize destination for delivery, defaulting to user's email.

    ADR-066 email-first: If destination is incomplete or missing target,
    fall back to sending to user's registered email address.

    Args:
        destination: The agent's destination config
        user_email: User's email address

    Returns:
        Normalized destination dict, or None if no valid destination
    """
    # No destination at all - use email delivery via Resend
    if not destination:
        if user_email:
            logger.info(f"[EXEC] No destination - defaulting to email: {user_email}")
            return {
                "platform": "email",
                "target": user_email,
                "format": "send",
            }
        return None

    platform = destination.get("platform")
    target = destination.get("target")

    # Destination has valid target - use as-is
    if target and target not in ("", "dm"):  # "dm" was a placeholder
        return destination

    # Missing or incomplete target - fall back to email
    if user_email:
        logger.info(
            f"[EXEC] Incomplete destination (platform={platform}, target={target}) "
            f"- defaulting to email: {user_email}"
        )
        return {
            "platform": "email",
            "target": user_email,
            "format": "send",
        }

    # No fallback available
    logger.warning(f"[EXEC] Incomplete destination and no user email available")
    return destination


async def get_next_run_number(client, agent_id: str) -> int:
    """Get the next version number for an agent."""
    result = (
        client.table("agent_runs")
        .select("version_number")
        .eq("agent_id", agent_id)
        .order("version_number", desc=True)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]["version_number"] + 1
    return 1


async def create_version_record(
    client,
    agent_id: str,
    version_number: int,
) -> dict:
    """Create a new version record in 'generating' status."""
    version_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    result = (
        client.table("agent_runs")
        .insert({
            "id": version_id,
            "agent_id": agent_id,
            "version_number": version_number,
            "status": "generating",
            "created_at": now,
            # ADR-042: Leave these NULL - grow into schema
            # edit_diff, edit_categories, edit_distance_score,
            # context_snapshot_id, pipeline_run_id
        })
        .execute()
    )

    return result.data[0] if result.data else {"id": version_id}


# Patterns that indicate the model narrated its tool usage instead of producing content
_NARRATION_PATTERNS = [
    "let me check",
    "let me search",
    "let me look",
    "let me read",
    "let me find",
    "let me see what",
    "let me review",
    "let me examine",
    "let me query",
    "let me fetch",
    "now let me",
    "i'll search",
    "i'll check",
    "i'll look",
    "i'll read",
    "i'll review",
    "i will search",
    "i will check",
    "i will read",
    "checking the",
    "searching for",
    "looking for platform content",
    "now i need to",
    "first, i'll",
    "first, let me",
    "i should read",
    "i should check",
    "i need to read",
    "i need to check",
]


def _is_narration(text: str) -> bool:
    """Check if text is tool-use narration rather than substantive content."""
    text_lower = text.lower().strip()
    return any(text_lower.startswith(p) or f"\n{p}" in text_lower for p in _NARRATION_PATTERNS)


def _strip_tool_narration(draft: str) -> str:
    """
    Strip tool-use narration from draft if the output is just narration.

    Catches both short narration (1-3 lines) and longer narration that starts
    with investigation language but never transitions to real content.

    Returns cleaned draft, or empty string if draft was purely narration.
    """
    lines = [line.strip() for line in draft.strip().splitlines() if line.strip()]
    if not lines:
        return ""

    draft_lower = draft.lower()

    # Short narration: 1-3 lines under 30 words
    if len(lines) <= 3 and len(draft.split()) < 30:
        if any(pattern in draft_lower for pattern in _NARRATION_PATTERNS):
            logger.warning(f"[GENERATE] Stripped short tool narration: {draft[:100]}")
            return ""

    # Longer narration: starts with narration pattern AND has no markdown structure
    # (real content has headers, lists, bold text; narration is plain prose about tool use)
    has_structure = any(
        line.startswith("#") or line.startswith("- ") or line.startswith("* ")
        or line.startswith("**") or line.startswith("| ")
        for line in lines
    )
    if not has_structure and _is_narration(draft):
        logger.warning(f"[GENERATE] Stripped unstructured tool narration: {draft[:100]}")
        return ""

    return draft


def _build_headless_system_prompt(
    role: str,
    trigger_context: Optional[dict] = None,
    research_directive: Optional[str] = None,
    agent: Optional[dict] = None,
    user_context: Optional[list] = None,
    workspace_preferences: Optional[str] = None,
    skill_docs: Optional[str] = None,
) -> str:
    """
    Build system prompt for headless mode generation (ADR-080/081/087/101/109/117/118).

    Args:
        role: The agent role (digest, prepare, synthesize, etc.)
        trigger_context: Optional trigger info with signal reasoning
        research_directive: Optional research instruction for research-scope agents
        agent: Optional agent dict with agent_instructions and agent_memory
        user_context: Optional list of user_memory rows (profile + preferences)
        workspace_preferences: Optional workspace memory/preferences.md content (ADR-117)
        skill_docs: Optional SKILL.md content for authorized output skills (ADR-118 D.1)

    Returns:
        Complete system prompt string
    """
    prompt = f"""You are generating a {role} agent.

## Output Rules
- Follow the format and instructions in the user message exactly.
- Be concise and professional — keep content tight and scannable.
- Do not invent information not present in the provided context or your research findings.
- Do not use emojis in headers or content unless the user's preferences explicitly request them.
- Use plain markdown headers (##, ###) and bullet points for structure.
- If the user's context mentions a preference for conciseness, prioritize brevity over completeness."""

    # Inject user context (profile + preferences) for personalized output
    if user_context:
        context_lines = []
        for row in user_context:
            key = row.get("key", "")
            value = row.get("value", "")
            if key in ("name", "role", "company", "timezone"):
                context_lines.append(f"- {key.title()}: {value}")
            elif key.startswith("tone_") or key.startswith("verbosity_"):
                context_lines.append(f"- {key.replace('_', ' ').title()}: {value}")
            elif key.startswith("preference:"):
                context_lines.append(f"- Prefers: {value}")
        if context_lines:
            prompt += "\n\n## User Context\n" + "\n".join(context_lines)

    # ADR-087: Inject agent-scoped instructions and memory
    if agent:
        instructions = (agent.get("agent_instructions") or "").strip()
        if instructions:
            prompt += f"""

## Agent Instructions
The user has set these behavioral directives for this agent:
{instructions}"""

        memory = agent.get("agent_memory") or {}
        memory_parts = []

        # Goal (for goal-mode agents)
        goal = memory.get("goal")
        if goal:
            desc = goal.get("description", "")
            status = goal.get("status", "")
            if desc:
                memory_parts.append(f"**Goal:** {desc}")
                if status:
                    memory_parts.append(f"Goal status: {status}")

        observations = memory.get("observations", [])
        if observations:
            memory_parts.append("**Recent observations:**")
            for obs in observations[-5:]:
                memory_parts.append(f"- {obs.get('date', '')}: {obs.get('note', '')}")

        # Review log (last 3 entries)
        review_log = memory.get("review_log", [])
        if review_log:
            memory_parts.append("**Review history:**")
            for entry in review_log[-3:]:
                memory_parts.append(f"- {entry.get('date', '')}: {entry.get('note', '')}")

        if memory_parts:
            prompt += "\n\n## Agent Memory\n" + "\n".join(memory_parts)

    # ADR-117: Inject learned preferences into system prompt for high salience.
    # Preferences are distilled from edit patterns by feedback_distillation.py
    # and stored in workspace memory/preferences.md.
    if workspace_preferences:
        prompt += f"""

## Learned Preferences (from user edit history)
{workspace_preferences}

Follow these preferences closely — they reflect what the user has consistently edited in past outputs."""

    # ADR-118 D.1: Inject SKILL.md content for authorized output skills.
    # Agents read skill docs to learn how to construct high-quality specs
    # for RuntimeDispatch (same model as Claude Code reading SKILL.md).
    if skill_docs:
        prompt += f"""

## Output Skill Documentation
You have access to RuntimeDispatch for producing binary artifacts.
Construct input specs according to these skill instructions:

{skill_docs}

When producing output that would benefit from a rendered artifact (PDF, PPTX, XLSX, chart),
use RuntimeDispatch with the spec format described above. Always produce a text version
alongside any binary — the text is the feedback surface for user edits."""

    # ADR-081: Research directive overrides default tool guidance
    if research_directive:
        prompt += f"""

## Research Directive
{research_directive}

## Tool Usage
You have investigation tools available: Search, Read, List, WebSearch, GetSystemState.
- Use **WebSearch** to conduct web research as described above.
- Use **Search** or **Read** to cross-reference with the user's platform data if provided.
- Conduct 2-4 targeted searches, then synthesize findings into the agent format.
- After researching, generate the agent in a single pass — do not search further."""
    else:
        prompt += """

## Tool Usage (Headless Mode)
You have read-only investigation tools available: Search, Read, List, WebSearch, GetSystemState.
- Use tools ONLY if the gathered context in the user message is clearly insufficient to produce the agent.
- Prefer generating from the provided context — most agents have enough.
- If you do use a tool, do so in the first turn, then generate in the next.
- NEVER use tools to stall — if context is adequate, generate immediately.
- NEVER narrate your tool usage in the final output. Do not write things like "Let me check..." or "I'll search for..." — your output must be the finished agent content only.

## Empty Context Handling
If the gathered context says "(No context available)" or tools return no results:
- Still produce the agent in the requested format and structure.
- Note briefly that no recent activity was found for the period.
- Do NOT output investigation narration or meta-commentary about missing data.
- A short, properly formatted "no activity" output is always better than a tool-use narrative."""

    # Inject trigger context when available
    if trigger_context:
        trigger_type = trigger_context.get("type", "")

        # Pulse generate: forward the pulse decision context to generation (ADR-126)
        if trigger_type in ("pulse_generate", "proactive_review"):
            # pulse_generate: tier info in trigger_context
            pulse_tier = trigger_context.get("tier", "")
            review_decision = trigger_context.get("review_decision", {})
            review_note = review_decision.get("note", "")
            if review_note:
                prompt += f"\n\n## Pulse Context\nThis agent was triggered by a pulse (tier {pulse_tier}) that found:\n{review_note}\n\nUse this as your starting point — focus on synthesizing insights from the gathered context above rather than re-investigating."

        # Signal processing: forward signal reasoning
        signal_reasoning = trigger_context.get("signal_reasoning", "")
        signal_ctx = trigger_context.get("signal_context", {})
        if signal_reasoning:
            prompt += f"\n\n## Signal Context\nThis agent was triggered by signal processing because:\n{signal_reasoning}"
        if signal_ctx:
            entity = signal_ctx.get("entity", "")
            platforms = signal_ctx.get("platforms", [])
            if entity:
                prompt += f"\nFocus entity: {entity}"
            if platforms:
                prompt += f"\nRelevant platforms: {', '.join(platforms)}"

    return prompt


# =============================================================================
# ADR-128: Contributor Cognitive Model — mandate context + self-assessment
# =============================================================================

async def _build_mandate_context(ws, agent: dict) -> str:
    """
    Build mandate_context string for contributor prompts (ADR-128 Phase 1).

    Reads from workspace:
    - memory/projects.json (project membership + expected contribution)
    - memory/self_assessment.md (last entry only — prevent self-referential loops)

    Returns empty string for non-project agents (graceful degradation).
    """
    import json as _json

    parts = []

    # 1. Project membership + expected contribution
    try:
        projects_raw = await ws.read("memory/projects.json")
        if projects_raw:
            projects = _json.loads(projects_raw)
            if projects:
                p = projects[0]  # Primary project
                parts.append(f"PROJECT: {p.get('title', 'Unknown')}")
                if p.get("expected_contribution"):
                    parts.append(f"YOUR EXPECTED CONTRIBUTION: {p['expected_contribution']}")

                # Read PM brief if available
                project_slug = p.get("project_slug")
                if project_slug:
                    from services.workspace import ProjectWorkspace, get_agent_slug
                    pw = ProjectWorkspace(ws.client, ws.user_id, project_slug)
                    agent_slug = get_agent_slug(agent)
                    try:
                        brief = await pw.read_brief(agent_slug)
                        if brief:
                            parts.append(f"PM DIRECTIVE (contribution brief):\n{brief[:500]}")
                    except Exception:
                        pass
    except Exception as e:
        logger.debug(f"[MANDATE] Projects context unavailable: {e}")

    # 2. Last self-assessment (most recent entry only)
    try:
        self_assessment = await ws.read("memory/self_assessment.md")
        if self_assessment:
            # Extract most recent entry (between first and second ## headers)
            lines = self_assessment.strip().split("\n")
            entry_lines = []
            found_first = False
            for line in lines:
                if line.startswith("## ") and not line.startswith("# Self"):
                    if found_first:
                        break  # Stop at second entry
                    found_first = True
                    entry_lines.append(line)
                elif found_first:
                    entry_lines.append(line)
            if entry_lines:
                parts.append(f"YOUR LAST SELF-ASSESSMENT:\n" + "\n".join(entry_lines))
    except Exception:
        pass

    if not parts:
        return ""

    return "MANDATE CONTEXT (ADR-128):\n" + "\n\n".join(parts)


_ASSESSMENT_BLOCK_RE = re.compile(
    r"\n---\s*\n*## Contributor Assessment.*",
    re.DOTALL,
)

_ASSESSMENT_FIELDS_RE = re.compile(
    r"\*\*Mandate\*\*:\s*(.+?)(?:\n|$)"
    r".*?\*\*Domain Fitness\*\*:\s*(.+?)(?:\n|$)"
    r".*?\*\*Context Currency\*\*:\s*(.+?)(?:\n|$)"
    r".*?\*\*Output Confidence\*\*:\s*(.+?)(?:\n|$)",
    re.DOTALL,
)


def _extract_contributor_assessment(draft: str) -> tuple[str, Optional[dict]]:
    """
    Extract and strip the ## Contributor Assessment block from draft (ADR-128).

    Returns (clean_draft, assessment_dict_or_None).
    """
    match = _ASSESSMENT_BLOCK_RE.search(draft)
    if not match:
        # Try without the --- separator (some models omit it)
        alt_match = re.search(r"\n## Contributor Assessment\b.*", draft, re.DOTALL)
        if not alt_match:
            return draft, None
        match = alt_match

    assessment_text = match.group(0)
    clean_draft = draft[:match.start()].rstrip()

    # Parse the 4 fields
    fields_match = _ASSESSMENT_FIELDS_RE.search(assessment_text)
    if not fields_match:
        return clean_draft, None

    return clean_draft, {
        "mandate": fields_match.group(1).strip(),
        "domain_fitness": fields_match.group(2).strip(),
        "context_currency": fields_match.group(3).strip(),
        "output_confidence": fields_match.group(4).strip(),
    }


async def _append_self_assessment(ws, assessment: dict) -> None:
    """
    Append a new self-assessment entry to memory/self_assessment.md (ADR-128).

    Rolling history: keeps 5 most recent entries (newest first).
    """
    from datetime import datetime, timezone as _tz

    now = datetime.now(_tz.utc)
    date_str = now.strftime("%Y-%m-%d %H:%M")

    new_entry = (
        f"## Run ({date_str})\n"
        f"- **Mandate**: {assessment['mandate']}\n"
        f"- **Domain Fitness**: {assessment['domain_fitness']}\n"
        f"- **Context Currency**: {assessment['context_currency']}\n"
        f"- **Output Confidence**: {assessment['output_confidence']}\n"
    )

    existing = await ws.read("memory/self_assessment.md") or ""

    # Parse existing entries
    header = "# Self-Assessment History\n<!-- Updated each run. Most recent first. Max 5 entries. -->\n\n"

    # Split on ## headers (each entry starts with ##)
    entries = re.split(r"(?=^## )", existing, flags=re.MULTILINE)
    entries = [e.strip() for e in entries if e.strip() and e.strip().startswith("## ")]

    # Prepend new entry, cap at 5
    entries = [new_entry.strip()] + entries[:4]

    content = header + "\n\n".join(entries) + "\n"

    await ws.write(
        "memory/self_assessment.md",
        content,
        summary=f"ADR-128: self-assessment after run ({assessment['output_confidence'][:20]})",
    )


# ADR-109: Scope-aware tool round limits
HEADLESS_TOOL_ROUNDS = {
    "platform":        2,   # Rarely needs tools — context is pre-gathered
    "cross_platform":  3,   # Occasionally useful for cross-referencing
    "knowledge":       3,   # Workspace-driven queries
    "research":        6,   # Needs room for web search + follow-up
    "autonomous":      8,   # Full investigation: workspace + knowledge base + web
}


async def generate_draft_inline(
    client,
    user_id: str,
    agent: dict,
    gathered_context: str,
    trigger_context: Optional[dict] = None,
    research_directive: Optional[str] = None,
    effective_role: Optional[str] = None,
) -> str:
    """
    Generate draft content via agent in headless mode (ADR-080/081).

    The agent has read-only tools (Search, Read, List, WebSearch,
    GetSystemState) available for investigation when gathered context
    is insufficient. Most agents generate in a single turn
    without tool use.

    ADR-042: Replaces execute_synthesize_step(). No separate work_ticket.
    ADR-080: Unified agent in headless mode — chat_completion_with_tools
    with mode-gated primitives.
    ADR-081: Binding-aware tool rounds. Research/hybrid types get higher
    limits and a research_directive so the agent does its own web research.
    """
    from services.anthropic import chat_completion_with_tools
    from services.primitives.registry import (
        get_tools_for_mode,
        create_headless_executor,
    )
    from services.agent_pipeline import (
        build_role_prompt,
        validate_output,
    )

    agent_id = agent.get("id")
    role = effective_role or agent.get("role", "custom")  # ADR-117 Phase 3: duty override
    scope = agent.get("scope", "cross_platform")
    type_config = agent.get("type_config", {})
    recipient_context = agent.get("recipient_context", {})

    # Format recipient context
    recipient_str = ""
    if recipient_context:
        name = recipient_context.get("name", "")
        recipient_role = recipient_context.get("role", "")
        priorities = recipient_context.get("priorities", [])
        if name or recipient_role:
            recipient_str = f"RECIPIENT: {name}"
            if recipient_role:
                recipient_str += f" ({recipient_role})"
            if priorities:
                recipient_str += f"\nPRIORITIES: {', '.join(priorities)}"

    # ADR-117: Preferences read from workspace and injected into system prompt
    # via _build_headless_system_prompt(workspace_preferences=...) for high salience.

    # ADR-106 Phase 2: Load intelligence from workspace (source of truth)
    from services.workspace import AgentWorkspace, get_agent_slug
    ws = AgentWorkspace(client, user_id, get_agent_slug(agent))
    await ws.ensure_seeded(agent)  # Lazy migration from DB columns

    # Read workspace-based intelligence
    ws_instructions = await ws.read("AGENT.md") or ""
    ws_preferences = await ws.read("memory/preferences.md") or ""
    ws_observations = await ws.get_observations()
    ws_review_log = await ws.get_review_log()
    ws_goal = await ws.get_goal()

    # ADR-117 Phase 3: Load duty-specific context if running a non-seed duty
    duty_name = trigger_context.get("duty") if trigger_context else None
    if duty_name:
        duty_context = await ws.read_duty(duty_name)
        if duty_context:
            ws_instructions = ws_instructions + f"\n\n## Active Duty: {duty_name}\n{duty_context}"

    # Build workspace-sourced agent dict for prompt building
    # (replaces reading from agent["agent_instructions"] / agent["agent_memory"])
    workspace_agent = {
        **agent,
        "agent_instructions": ws_instructions,
        "agent_memory": {
            "observations": ws_observations,
            "review_log": ws_review_log,
            **({"goal": ws_goal} if ws_goal else {}),
        },
    }

    # ADR-120: PM agents need project context injected into type_config for build_role_prompt
    if role == "pm" and type_config.get("project_slug"):
        try:
            pm_config = await _load_pm_project_context(client, user_id, type_config["project_slug"])
            type_config = {**type_config, **pm_config}
        except Exception as e:
            logger.warning(f"[GENERATE] PM context injection failed: {e}")

    # ADR-128 Phase 1: Build mandate_context for contributor agents
    if role != "pm":
        mandate_context = await _build_mandate_context(ws, agent)
        type_config = {**type_config, "mandate_context": mandate_context}

    # Build role-specific prompt (user message)
    prompt = build_role_prompt(
        role=role,
        config=type_config,
        agent=workspace_agent,
        gathered_context=gathered_context,
        recipient_text=recipient_str,
    )

    # ADR-108: Read user context from /memory/ files instead of user_memory table
    user_context = None
    try:
        from services.workspace import UserMemory
        um = UserMemory(client, user_id)
        memory_files = um.read_all_sync()
        # Build key-value list matching the shape _build_headless_system_prompt expects
        user_context = []
        profile = UserMemory._parse_memory_md(memory_files.get("MEMORY.md"))
        for k, v in profile.items():
            if v:
                user_context.append({"key": k, "value": v})
        prefs = UserMemory._parse_preferences_md(memory_files.get("preferences.md"))
        for platform, settings in prefs.items():
            if settings.get("tone"):
                user_context.append({"key": f"tone_{platform}", "value": settings["tone"]})
            if settings.get("verbosity"):
                user_context.append({"key": f"verbosity_{platform}", "value": settings["verbosity"]})
        notes = UserMemory._parse_notes_md(memory_files.get("notes.md"))
        for note in notes[:5]:
            user_context.append({"key": f"preference:{note['content'][:40]}", "value": note["content"]})
    except Exception as e:
        logger.warning(f"[GENERATE] Failed to fetch user context: {e}")

    # ADR-130: Fetch SKILL.md for agents with asset capabilities (type-scoped)
    skill_docs = None
    if has_asset_capabilities(role):
        try:
            skill_docs = await _fetch_skill_docs()
        except Exception as e:
            logger.warning(f"[GENERATE] Skill docs fetch failed (non-fatal): {e}")

    # ADR-109: Headless system prompt with workspace-sourced intelligence
    system_prompt = _build_headless_system_prompt(
        role, trigger_context, research_directive, workspace_agent, user_context,
        workspace_preferences=ws_preferences,
        skill_docs=skill_docs,
    )

    # ADR-109: Tool round limit based on scope
    max_tool_rounds = HEADLESS_TOOL_ROUNDS.get(scope, 3)

    # Planner/prepare needs more rounds for per-attendee research + WebSearch
    if role in ("prepare", "planner"):
        max_tool_rounds = max(max_tool_rounds, 5)

    # PM needs tool rounds for project status checks (ADR-120)
    if role == "pm":
        max_tool_rounds = max(max_tool_rounds, 4)

    # ADR-080: Mode-gated tools and executor
    # ADR-092: Pass agent sources so headless RefreshPlatformContent can scope to them
    # ADR-106: Pass agent dict so workspace primitives have agent context
    headless_tools = get_tools_for_mode("headless")
    executor = create_headless_executor(
        client, user_id,
        agent_sources=agent.get("sources"),
        agent=agent,
    )

    import json

    try:
        # ADR-080: Agentic loop — agent can use read-only tools if needed
        messages = [{"role": "user", "content": prompt}]
        tools_used = []  # Track tool names for observability

        # ADR-101: Accumulate token usage across all tool rounds
        total_input_tokens = 0
        total_output_tokens = 0

        for round_num in range(max_tool_rounds + 1):
            response = await chat_completion_with_tools(
                messages=messages,
                system=system_prompt,
                tools=headless_tools,
                model=SONNET_MODEL,
                max_tokens=4000,
            )

            # ADR-101: Track tokens from each round
            if response.usage:
                total_input_tokens += response.usage.get("input_tokens", 0)
                total_output_tokens += response.usage.get("output_tokens", 0)

            # Agent finished or hit token limit — take whatever text exists
            if response.stop_reason in ("end_turn", "max_tokens") or not response.tool_uses:
                draft = response.text.strip()
                if response.stop_reason == "max_tokens":
                    logger.warning("[GENERATE] Headless agent hit max_tokens — draft may be truncated")
                if round_num > 0:
                    logger.info(
                        f"[GENERATE] Headless agent used {round_num} tool round(s): "
                        f"{', '.join(tools_used)}"
                    )
                break

            # Agent wants to use tools — check round limit
            if round_num >= max_tool_rounds:
                logger.warning(
                    f"[GENERATE] Headless agent hit max tool rounds ({max_tool_rounds}), "
                    f"tools used: {', '.join(tools_used)}"
                )
                # If agent has substantive text (not narration) alongside tool calls, use it
                candidate = response.text.strip() if response.text else ""
                if candidate and not _is_narration(candidate):
                    draft = candidate
                    break

                # Force a final synthesis call with no tools available
                logger.info("[GENERATE] Forcing final synthesis call (no tools)")
                messages.append({"role": "assistant", "content": response.text or ""})
                messages.append({"role": "user", "content": "You have reached the tool limit. Please synthesize all the information gathered so far and produce the final output now. Do not request any more tools — produce the deliverable in its full format."})
                final_response = await chat_completion_with_tools(
                    messages=messages,
                    system=system_prompt,
                    tools=[],  # No tools — force text output
                    model=SONNET_MODEL,
                    max_tokens=4000,
                )
                # ADR-101: Track tokens from synthesis call
                if final_response.usage:
                    total_input_tokens += final_response.usage.get("input_tokens", 0)
                    total_output_tokens += final_response.usage.get("output_tokens", 0)
                draft = final_response.text.strip() if final_response.text else ""
                break

            # Build assistant message with tool use blocks
            assistant_content = []
            if response.text:
                assistant_content.append({"type": "text", "text": response.text})
            for tu in response.tool_uses:
                assistant_content.append({
                    "type": "tool_use",
                    "id": tu.id,
                    "name": tu.name,
                    "input": tu.input,
                })
            messages.append({"role": "assistant", "content": assistant_content})

            # Execute tools and collect results
            tool_results = []
            for tu in response.tool_uses:
                tools_used.append(tu.name)
                logger.info(f"[GENERATE] Headless tool: {tu.name}({str(tu.input)[:100]})")
                result = await executor(tu.name, tu.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": json.dumps(result) if isinstance(result, dict) else str(result),
                })

            messages.append({"role": "user", "content": tool_results})
        else:
            # for/else: loop completed without break — safety net
            draft = ""

        if not draft:
            raise ValueError("Agent produced empty draft")

        # Detect critically bad output: tool-use narration leaked into draft
        draft = _strip_tool_narration(draft)

        if not draft:
            raise ValueError("Agent produced only tool-use narration, no actual content")

        # Validate output (non-blocking for soft issues, blocking for critical)
        validation = validate_output(role, draft, type_config)
        if not validation.get("valid"):
            logger.warning(f"[GENERATE] Validation warnings: {validation.get('issues', [])}")

        # Block critically short output and force a retry synthesis
        # PM agents output concise JSON (~10-15 words) — skip retry for them
        word_count = len(draft.split())
        if word_count < 20 and role != "pm":
            logger.warning(f"[GENERATE] Draft critically short ({word_count} words), forcing synthesis retry")
            messages.append({"role": "assistant", "content": draft})
            messages.append({"role": "user", "content": (
                "Your output was too short and incomplete. You MUST produce the full agent content "
                "in the requested format now. If no platform activity was found, still produce a "
                "properly structured output noting the lack of activity. Do not narrate — just write the content."
            )})
            retry_response = await chat_completion_with_tools(
                messages=messages,
                system=system_prompt,
                tools=[],
                model=SONNET_MODEL,
                max_tokens=4000,
            )
            if retry_response.usage:
                total_input_tokens += retry_response.usage.get("input_tokens", 0)
                total_output_tokens += retry_response.usage.get("output_tokens", 0)
            retry_draft = (retry_response.text or "").strip()
            if len(retry_draft.split()) > word_count:
                draft = retry_draft
                logger.info(f"[GENERATE] Synthesis retry produced {len(draft.split())} words")

        # ADR-101: Return draft + token usage for per-agent cost tracking
        usage = {
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
        }
        logger.info(f"[GENERATE] Token usage: {total_input_tokens} in / {total_output_tokens} out")

        # ADR-118 D.3: Collect rendered files accumulated by RuntimeDispatch during generation
        pending_renders = getattr(executor, "auth", None)
        pending_renders = getattr(pending_renders, "pending_renders", []) if pending_renders else []

        return draft, usage, pending_renders

    except Exception as e:
        logger.error(f"[GENERATE] LLM call failed: {e}")
        raise


async def update_version_for_delivery(
    client,
    version_id: str,
    draft_content: str,
    metadata: Optional[dict] = None,
):
    """
    Prepare version for delivery by storing content.

    ADR-066: Versions go directly to delivery, no staged status.
    Status remains 'generating' until delivery completes.
    ADR-101: Optional metadata (tokens, model) stored for cost tracking.
    """
    update = {
        "draft_content": draft_content,
        "final_content": draft_content,  # ADR-066: No editing step, content is final
    }
    if metadata:
        update["metadata"] = metadata
    client.table("agent_runs").update(update).eq("id", version_id).execute()


# =============================================================================
# ADR-118 D.3: Delivery helpers for workspace-based delivery path
# =============================================================================


def _log_export_standalone(client, version_id: str, user_id: str, destination: dict, result) -> None:
    """Log export to export_log table (standalone — not via DeliveryService)."""
    try:
        from integrations.core.types import ExportStatus
        client.table("export_log").insert({
            "agent_run_id": version_id,
            "user_id": user_id,
            "provider": destination.get("platform", "unknown"),
            "destination": destination,
            "status": result.status.value,
            "external_id": result.external_id,
            "external_url": result.external_url,
            "error_message": result.error_message,
            "completed_at": datetime.now(timezone.utc).isoformat() if result.status == ExportStatus.SUCCESS else None,
        }).execute()
    except Exception as e:
        logger.warning(f"[EXEC] Failed to log export: {e}")


async def _notify_delivery(client, user_id: str, agent: dict, destination: dict, result) -> None:
    """Send delivery success notification (ADR-040)."""
    try:
        from services.notifications import notify_agent_delivered
        platform = destination.get("platform", "unknown")
        target = destination.get("target")
        dest_str = platform
        if target:
            dest_str += f" ({target})"
        await notify_agent_delivered(
            db_client=client,
            user_id=user_id,
            agent_id=str(agent.get("id", "")),
            agent_title=agent.get("title", "Agent"),
            destination=dest_str,
            external_url=result.external_url,
            delivery_platform=platform,
        )
    except Exception as e:
        logger.warning(f"[EXEC] Delivery notification failed: {e}")


async def _notify_delivery_failed(client, user_id: str, agent: dict, error: str) -> None:
    """Send delivery failure notification (ADR-040)."""
    try:
        from services.notifications import notify_agent_failed
        await notify_agent_failed(
            db_client=client,
            user_id=user_id,
            agent_id=str(agent.get("id", "")),
            agent_title=agent.get("title", "Agent"),
            error=error,
        )
    except Exception as e:
        logger.warning(f"[EXEC] Failure notification failed: {e}")


# =============================================================================
# ADR-116 Phase 4: Agent Card Auto-Generation
# =============================================================================

def _extract_run_observation(
    draft: str,
    sources_used: list[str],
    items_fetched: int,
    role: str,
) -> str:
    """
    Extract a lightweight observation from a completed run — ADR-117 Phase 2.

    Rule-based, no LLM call. Captures:
    - Topics covered (from markdown headers)
    - Source coverage (which platforms contributed, data volume)
    - Role-specific signals
    """
    parts = []

    # Topic extraction from headers
    headers = re.findall(r"^#+\s+(.+)$", draft, re.MULTILINE)
    if headers:
        # Take up to 5 topic headers, skip generic ones
        topics = [h.strip() for h in headers if len(h.strip()) > 3][:5]
        if topics:
            parts.append(f"Topics: {', '.join(topics)}")

    # Source coverage
    if sources_used:
        parts.append(f"Sources: {', '.join(sources_used)} ({items_fetched} items)")
    else:
        parts.append("No platform sources used")

    # Data volume signal
    word_count = len(draft.split())
    if word_count < 100:
        parts.append("Thin output — limited source data")
    elif word_count > 2000:
        parts.append(f"Dense output ({word_count} words)")

    # Role-specific signals
    if role in ("digest", "briefer") and items_fetched < 5:
        parts.append("Low activity period — few items to brief on")
    elif role in ("synthesize", "analyst") and len(sources_used) < 2:
        parts.append("Cross-platform analysis with limited platform coverage")

    return "; ".join(parts) if parts else f"{role} run completed"


async def _generate_agent_card(client, user_id: str, agent: dict, version_number: int):
    """
    Auto-generate agent-card.json in the agent's workspace after each run.

    The card is a structured, machine-readable identity derived from workspace
    files + database metadata. Consumed by DiscoverAgents, MCP tools, and
    external agents (Claude Desktop, ChatGPT).
    """
    import json
    from services.workspace import AgentWorkspace, get_agent_slug

    agent_id = agent.get("id")
    slug = get_agent_slug(agent)
    ws = AgentWorkspace(client, user_id, slug)

    # Read identity files for card generation
    agent_md = await ws.read("AGENT.md")
    thesis = await ws.read("thesis.md")

    # Extract first paragraph of AGENT.md as description
    description = None
    if agent_md:
        paragraphs = agent_md.strip().split("\n\n")
        # Skip frontmatter/headers, find first real paragraph
        for p in paragraphs:
            stripped = p.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith("---"):
                description = stripped[:300]
                break

    # Compute maturity signals
    run_count = 0
    try:
        run_result = (
            client.table("agent_runs")
            .select("id", count="exact")
            .eq("agent_id", agent_id)
            .execute()
        )
        run_count = run_result.count or 0
    except Exception:
        pass

    # Count knowledge files produced by this agent via metadata RPC
    knowledge_files_count = 0
    try:
        kf_result = client.rpc("search_knowledge_by_metadata", {
            "p_user_id": user_id,
            "p_agent_id": str(agent_id),
            "p_limit": 100,
        }).execute()
        knowledge_files_count = len(kf_result.data or [])
    except Exception:
        pass

    card = {
        "schema_version": "1",
        "agent_id": str(agent_id),
        "title": agent.get("title"),
        "slug": slug,
        "role": agent.get("role"),
        "scope": agent.get("scope"),
        "description": description,
        "thesis_summary": thesis[:300] if thesis else None,
        "sources": agent.get("sources", []),
        "schedule": agent.get("schedule"),
        "maturity": {
            "total_runs": run_count,
            "knowledge_files_produced": knowledge_files_count,
            "latest_version": version_number,
        },
        "last_run_at": agent.get("last_run_at"),
        "interop": {
            "mcp_resource": f"workspace://agents/{slug}/",
            "input_format": "platform_content",
            "output_format": "markdown",
        },
    }

    await ws.write(
        "agent-card.json",
        json.dumps(card, indent=2, default=str),
        summary=f"Agent card for {agent.get('title')} (auto-generated)",
    )
    logger.info(f"[EXEC] ADR-116: Agent card generated for {slug}")


# =============================================================================
# Main Entry Point - ADR-042, ADR-045, ADR-066 Delivery-First
# =============================================================================

async def execute_agent_generation(
    client,
    user_id: str,
    agent: dict,
    trigger_context: Optional[dict] = None,
) -> dict:
    """
    Execute agent generation with immediate delivery (no approval gate).

    ADR-042: Simplified single-call flow
    ADR-109: Strategy selection based on scope
    ADR-049: Context freshness checks and source snapshots
    ADR-066: Delivery-first, no governance - always attempt delivery

    Args:
        client: Supabase client
        user_id: User UUID
        agent: Full agent dict (from database)
        trigger_context: Optional trigger info (schedule, event, manual)

    Returns:
        Result dict with run_id, status, message
        Status is 'delivered' or 'failed' (no 'staged' per ADR-066)
    """
    from services.execution_strategies import get_execution_strategy
    from services.freshness import (
        check_agent_freshness,
        record_source_snapshots,
    )

    agent_id = agent.get("id")
    role = agent.get("role", "custom")
    scope = agent.get("scope", "cross_platform")
    title = agent.get("title", "Untitled")
    trigger_type = trigger_context.get("type", "manual") if trigger_context else "manual"

    # ADR-129: Resolve project_slug for activity event enrichment
    from services.activity_log import resolve_agent_project_slug
    _proj_slug = resolve_agent_project_slug(agent)

    # ADR-117 Phase 3: Resolve duty from trigger_context → effective_role
    # When running a non-seed duty (e.g., monitor on a digest agent), the duty's
    # role determines prompt selection and SKILL.md injection.
    duty_name = trigger_context.get("duty") if trigger_context else None
    effective_role = role  # default: seed role
    if duty_name and duty_name != role:
        # Duty role overrides for prompt + skill injection
        effective_role = duty_name

    logger.info(
        f"[EXEC] Starting: {title} ({agent_id}), "
        f"trigger={trigger_type}, scope={scope}, role={role}"
        + (f", duty={duty_name}" if duty_name else "")
    )

    version = None
    freshness_result = None

    try:
        # ADR-049: Check source freshness before generation
        freshness_result = await check_agent_freshness(client, user_id, agent)
        if not freshness_result["all_fresh"]:
            stale_count = len(freshness_result["stale_sources"])
            never_synced_count = len(freshness_result["never_synced"])
            logger.info(
                f"[EXEC] Freshness: {stale_count} stale, {never_synced_count} never synced"
            )
            # Note: We proceed with generation using available data
            # Targeted sync is handled separately if user requests it

        # 1. Get next version number
        next_version = await get_next_run_number(client, agent_id)

        # 2. Create version record (generating)
        version = await create_version_record(client, agent_id, next_version)
        version_id = version["id"]

        # ADR-117 Phase 3: Tag run with duty name for attribution
        if duty_name:
            try:
                client.table("agent_runs").update(
                    {"duty_name": duty_name}
                ).eq("id", version_id).execute()
            except Exception as e:
                logger.warning(f"[EXEC] duty_name tag failed (non-fatal): {e}")

        # 3. ADR-045: Select and execute strategy for context gathering
        strategy = get_execution_strategy(agent)
        gathered_result = await strategy.gather_context(client, user_id, agent)

        # Convert strategy result to legacy format for compatibility
        gathered_context = gathered_result.content
        context_summary = gathered_result.summary
        context_summary["sources_used"] = gathered_result.sources_used
        context_summary["total_items_fetched"] = gathered_result.items_fetched
        # ADR-049: Include freshness info in summary
        context_summary["freshness"] = {
            "all_fresh": freshness_result["all_fresh"] if freshness_result else True,
            "stale_sources": len(freshness_result["stale_sources"]) if freshness_result else 0,
        }

        # 4. Generate draft inline (ADR-080/081: pass trigger_context + research_directive)
        # ADR-117 Phase 3: effective_role overrides prompt + skill injection for non-seed duties
        research_directive = context_summary.get("research_directive")
        draft, usage, pending_renders = await generate_draft_inline(
            client, user_id, agent, gathered_context,
            trigger_context, research_directive,
            effective_role=effective_role,
        )

        # ADR-128 Phase 1: Extract and strip contributor self-assessment before delivery
        contributor_assessment = None
        if role != "pm":
            draft, contributor_assessment = _extract_contributor_assessment(draft)
            if contributor_assessment:
                logger.info(f"[EXEC] ADR-128: Extracted self-assessment (confidence: {contributor_assessment.get('output_confidence', '?')})")

        # 5. ADR-066: Prepare version for delivery (no staged status)
        # ADR-101: Store execution metadata (tokens, model) on version
        # ADR-049 evolution: Include context provenance for traceability
        version_metadata = {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "model": SONNET_MODEL,
            "platform_content_ids": gathered_result.platform_content_ids,
            "items_fetched": gathered_result.items_fetched,
            "sources_used": gathered_result.sources_used,
            "strategy": context_summary.get("strategy", "unknown"),
            # Persist trigger provenance so runs can be attributed to scheduler/manual/event paths.
            "trigger_type": trigger_type,
        }
        await update_version_for_delivery(client, version_id, draft, metadata=version_metadata)

        # ADR-120 Phase 2: PM agents produce JSON decisions, not deliverable content.
        # Intercept here: parse the decision, act on it, skip normal delivery.
        if role == "pm":
            pm_type_config = agent.get("type_config", {})
            pm_result = await _handle_pm_decision(
                client, user_id, agent, draft, pm_type_config,
                version_id, next_version, usage,
            )

            # Update agent_runs with PM decision metadata
            now = datetime.now(timezone.utc).isoformat()
            pm_metadata = {**version_metadata, "pm_decision": pm_result}
            pm_status = "delivered" if pm_result.get("success", True) else "failed"
            client.table("agent_runs").update({
                "status": pm_status,
                "delivered_at": now,
                "metadata": pm_metadata,
            }).eq("id", version_id).execute()

            # Update last_run_at
            client.table("agents").update({
                "last_run_at": now,
            }).eq("id", agent_id).execute()

            logger.info(
                f"[EXEC] PM complete: {title}, version={next_version}, "
                f"action={pm_result.get('pm_action')}, success={pm_result.get('success')}"
            )

            # Activity log for PM run
            try:
                from services.activity_log import write_activity
                from services.supabase import get_service_client as _get_svc_pm
                _pm_run_meta = {
                    "agent_id": str(agent_id),
                    "version_number": next_version,
                    "role": role,
                    "scope": scope,
                    "strategy": strategy.strategy_name,
                    "final_status": pm_status,
                    "pm_action": pm_result.get("pm_action"),
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                }
                if _proj_slug:
                    _pm_run_meta["project_slug"] = _proj_slug
                await write_activity(
                    client=_get_svc_pm(),
                    user_id=user_id,
                    event_type="agent_run",
                    summary=f"{title} v{next_version} {pm_result.get('pm_action', 'unknown')}",
                    event_ref=version_id,
                    metadata=_pm_run_meta,
                )
            except Exception:
                pass

            # ADR-120 Phase 3: Record work units for PM run
            try:
                from services.platform_limits import record_work_units as _record_wu
                _record_wu(client, user_id, "pm_heartbeat", 1, agent_id=str(agent_id))
            except Exception:
                pass

            # Composer heartbeat (PM runs are significant events)
            try:
                from services.composer import maybe_trigger_heartbeat
                await maybe_trigger_heartbeat(client, user_id, "agent_run_delivered", {
                    "agent_id": str(agent_id), "role": role,
                    "pm_action": pm_result.get("pm_action"),
                })
            except Exception:
                pass

            return {
                "success": pm_result.get("success", True),
                "run_id": version_id,
                "version_number": next_version,
                "status": pm_status,
                "message": f"PM v{next_version}: {pm_result.get('pm_action', 'unknown')} — {pm_result.get('reason', '')}",
                "strategy": strategy.strategy_name,
            }

        # ADR-073: Mark consumed platform content as retained
        if gathered_result.platform_content_ids:
            try:
                from services.platform_content import mark_content_retained
                await mark_content_retained(
                    client,
                    gathered_result.platform_content_ids,
                    reason="agent_execution",
                    ref=version_id,
                )
            except Exception as e:
                logger.warning(f"[EXEC] Failed to mark content retained: {e}")

        # ADR-049: Record source snapshots for audit trail
        # sources_used is a list of strings like "platform:slack", "other:document"
        # Build snapshot from the agent's source configs
        sources_for_snapshot = []
        for source in agent.get("sources", []):
            if source.get("provider") or source.get("platform"):
                sources_for_snapshot.append({
                    "platform": source.get("provider") or source.get("platform"),
                    "resource_id": source.get("resource_id") or source.get("id"),
                    "resource_name": source.get("resource_name") or source.get("name"),
                    "user_id": user_id,
                })
        await record_source_snapshots(
            client, version_id, sources_for_snapshot,
            content_ids=gathered_result.platform_content_ids,
        )

        # 6. Update agent last_run_at
        client.table("agents").update({
            "last_run_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", agent_id).execute()

        # 7. ADR-122: Resolve destination — agent → project → email fallback
        # "Agents produce, projects deliver" — project delivery config takes precedence
        from services.supabase import get_service_client as _get_svc
        user_email = get_user_email(_get_svc(), user_id)
        raw_destination = agent.get("destination")
        destination = raw_destination

        # If agent has no destination, check project delivery config (ADR-122)
        if not destination:
            destination = await _resolve_project_delivery(client, user_id, agent_id)

        # Final fallback: email-first (ADR-066)
        destination = normalize_destination_for_delivery(destination, user_email)

        # 8. ADR-118 D.3: Save output folder BEFORE delivery (with rendered files from RuntimeDispatch)
        # Output folder is the single delivery source. Fatal if this fails.
        from services.workspace import AgentWorkspace, get_agent_slug, KnowledgeBase
        from services.supabase import get_service_client as _get_svc3
        slug = get_agent_slug(agent)
        svc_client = _get_svc3()
        ws = AgentWorkspace(svc_client, user_id, slug)
        output_folder = None

        try:
            output_folder = await ws.save_output(
                content=draft,
                run_id=str(version_id),
                agent_id=str(agent_id),
                version_number=next_version,
                role=role,
                rendered_files=pending_renders if pending_renders else None,
            )
            if output_folder:
                logger.info(
                    f"[EXEC] ADR-118 D.3: Saved output folder at /agents/{slug}/{output_folder}/ "
                    f"({len(pending_renders)} rendered files)"
                )
            else:
                logger.error(f"[EXEC] ADR-118 D.3: save_output returned None — fatal")
        except Exception as e:
            logger.error(f"[EXEC] ADR-118 D.3: Output folder write FAILED (fatal): {e}")
            output_folder = None

        # 9. ADR-107: Write agent output to /knowledge/ filesystem (non-fatal)
        try:
            kb = KnowledgeBase(svc_client, user_id)
            knowledge_path = KnowledgeBase.get_knowledge_path(role, title)
            await kb.write(
                path=knowledge_path,
                content=draft,
                summary=f"{title} v{next_version}",
                metadata={
                    "agent_id": str(agent_id),
                    "run_id": str(version_id),
                    "content_class": KnowledgeBase.CONTENT_CLASS_MAP.get(role, "analyses"),
                    "role": role,
                    "scope": scope,
                    "version_number": next_version,
                },
                tags=[role, agent.get("mode", "recurring")],
            )
            logger.info(f"[EXEC] ADR-107: Stored knowledge at {knowledge_path}")
        except Exception as e:
            logger.warning(f"[EXEC] ADR-107: Failed to store knowledge: {e}")

        # 9b. ADR-130 Phase 2: Compose HTML from output.md + assets (non-fatal)
        from services.agent_framework import has_capability
        if output_folder and role != "pm" and has_capability(role, "compose_html"):
            try:
                composed_html = await _compose_output_html(
                    svc_client, user_id, slug, output_folder,
                    title=title, pending_renders=pending_renders,
                )
                if composed_html:
                    logger.info(f"[EXEC] ADR-130: Composed HTML ({len(composed_html)} chars) for {output_folder}")
            except Exception as e:
                logger.warning(f"[EXEC] ADR-130: Compose failed (non-fatal): {e}")

        # 10. ADR-118 D.3: Deliver from output folder (unified output substrate)
        final_status = "delivered"
        delivery_result = None
        delivery_error = None

        if destination and output_folder:
            logger.info(f"[EXEC] ADR-118 D.3: Delivering from output folder={output_folder}")
            try:
                from services.delivery import deliver_from_output_folder
                delivery_result = await deliver_from_output_folder(
                    client=svc_client,
                    user_id=user_id,
                    agent=agent,
                    output_folder=output_folder,
                    agent_slug=slug,
                    version_id=str(version_id),
                    version_number=next_version,
                    destination=destination,
                )
                if delivery_result.status.value == "success":
                    final_status = "delivered"
                    now = datetime.now(timezone.utc).isoformat()
                    client.table("agent_runs").update({
                        "status": "delivered",
                        "delivered_at": now,
                        "delivery_status": "delivered",
                    }).eq("id", version_id).execute()
                    # Log export + notify (parity with DeliveryService)
                    _log_export_standalone(svc_client, version_id, user_id, destination, delivery_result)
                    await _notify_delivery(svc_client, user_id, agent, destination, delivery_result)
                else:
                    final_status = "failed"
                    delivery_error = delivery_result.error_message
                    client.table("agent_runs").update({
                        "status": "failed",
                        "delivery_status": "failed",
                        "delivery_error": delivery_error,
                    }).eq("id", version_id).execute()
                    await _notify_delivery_failed(svc_client, user_id, agent, delivery_error or "Unknown error")
                logger.info(f"[EXEC] Delivery: {delivery_result.status.value}")
            except Exception as e:
                logger.error(f"[EXEC] Delivery failed: {e}")
                final_status = "failed"
                delivery_error = str(e)
                client.table("agent_runs").update({
                    "status": "failed",
                    "delivery_status": "failed",
                    "delivery_error": delivery_error,
                }).eq("id", version_id).execute()
                await _notify_delivery_failed(svc_client, user_id, agent, delivery_error)
        elif destination and not output_folder:
            # ADR-118 D.3 fallback: output folder failed, deliver from agent_runs (legacy path)
            logger.warning(f"[EXEC] ADR-118 D.3: Output folder unavailable, falling back to agent_runs delivery")
            try:
                from services.delivery import get_delivery_service
                delivery_service = get_delivery_service(client)
                delivery_result = await delivery_service.deliver_version(
                    version_id=version_id,
                    user_id=user_id,
                )
                if delivery_result.status.value == "success":
                    final_status = "delivered"
                    now = datetime.now(timezone.utc).isoformat()
                    client.table("agent_runs").update({
                        "status": "delivered",
                        "delivered_at": now,
                    }).eq("id", version_id).execute()
                else:
                    final_status = "failed"
                    delivery_error = delivery_result.error_message
                    client.table("agent_runs").update({
                        "status": "failed",
                        "delivery_error": delivery_error,
                    }).eq("id", version_id).execute()
                logger.info(f"[EXEC] Fallback delivery: {delivery_result.status.value}")
            except Exception as e:
                logger.error(f"[EXEC] Fallback delivery failed: {e}")
                final_status = "failed"
                delivery_error = str(e)
                client.table("agent_runs").update({
                    "status": "failed",
                    "delivery_error": delivery_error,
                }).eq("id", version_id).execute()
        else:
            # No destination configured - mark as delivered (content generated successfully)
            now = datetime.now(timezone.utc).isoformat()
            client.table("agent_runs").update({
                "status": "delivered",
                "delivered_at": now,
            }).eq("id", version_id).execute()
            logger.info(f"[EXEC] No destination - content ready (version={version_id})")

        # ADR-117 Phase 2: Post-generation self-reflection for all skills
        if final_status == "delivered" and draft:
            try:
                observation = _extract_run_observation(
                    draft, gathered_result.sources_used,
                    gathered_result.items_fetched, role,
                )
                await ws.record_observation(observation, source="self")
                logger.info(f"[EXEC] ADR-117: Recorded self-observation for {title}")
            except Exception as e:
                logger.warning(f"[EXEC] ADR-117: Self-observation failed: {e}")
                # Non-fatal — don't block delivery

        # ADR-128 Phase 1: Append contributor self-assessment to rolling history
        if final_status == "delivered" and contributor_assessment and role != "pm":
            try:
                await _append_self_assessment(ws, contributor_assessment)
                logger.info(f"[EXEC] ADR-128: Appended self-assessment for {title}")
            except Exception as e:
                logger.warning(f"[EXEC] ADR-128: Self-assessment write failed: {e}")
                # Non-fatal

        # ADR-116 Phase 4: Auto-generate agent card after successful run
        if final_status == "delivered":
            try:
                await _generate_agent_card(client, user_id, agent, next_version)
            except Exception as e:
                logger.warning(f"[EXEC] ADR-116: Agent card generation failed: {e}")
                # Non-fatal

        # ADR-133: Nudge project PM when contributor completes a run
        # Sets PM's next_pulse_at to now so it picks up the completion
        if final_status == "delivered" and role != "pm":
            try:
                tc = agent.get("type_config") or {}
                project_slug = tc.get("project_slug")
                if project_slug:
                    # Find PM agent for this project
                    pm_result = svc_client.table("agents").select("id").eq(
                        "user_id", user_id
                    ).eq("role", "pm").eq("status", "active").execute()
                    for pm in (pm_result.data or []):
                        pm_tc = pm.get("type_config") or {}
                        # Check all PMs, set next_pulse_at on the one matching this project
                        pm_full = svc_client.table("agents").select("id, type_config").eq("id", pm["id"]).single().execute()
                        if pm_full.data and (pm_full.data.get("type_config") or {}).get("project_slug") == project_slug:
                            # Nudge PM to 5 min from now (batches multiple contributor completions)
                            nudge_time = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
                            svc_client.table("agents").update({
                                "next_pulse_at": nudge_time,
                            }).eq("id", pm["id"]).execute()
                            logger.info(f"[EXEC] ADR-133: Nudged PM for project {project_slug} (+5m) after {title} completed")
                            break
            except Exception as e:
                logger.warning(f"[EXEC] ADR-133: PM nudge failed (non-fatal): {e}")

            # ADR-135: Contributor reports completion to project chat
            if project_slug:
                try:
                    from services.pm_coordination import contributor_report
                    # Build a brief summary of what was produced
                    word_count = len(draft.split()) if draft else 0
                    summary = f"Run complete — {word_count} words."
                    if contributor_assessment:
                        confidence = contributor_assessment.get("confidence", "")
                        if confidence:
                            summary += f" Confidence: {confidence}."
                    await contributor_report(svc_client, user_id, project_slug, agent, summary)
                except Exception as e:
                    logger.warning(f"[EXEC] ADR-135: Contributor chat message failed (non-fatal): {e}")

        logger.info(
            f"[EXEC] Complete: {title}, version={next_version}, "
            f"status={final_status}, strategy={strategy.strategy_name}"
        )

        # Activity log: record this agent run (ADR-063)
        # Requires service role — activity_log has no user INSERT policy
        try:
            from services.activity_log import write_activity
            from services.supabase import get_service_client as _get_svc2
            _run_meta = {
                "agent_id": str(agent_id),
                "version_number": next_version,
                "role": role,  # ADR-109: For pattern detection
                "scope": scope,
                "strategy": strategy.strategy_name,
                "final_status": final_status,
                "delivery_error": delivery_error,
                "input_tokens": usage.get("input_tokens", 0),  # ADR-101
                "output_tokens": usage.get("output_tokens", 0),  # ADR-101
            }
            # ADR-129: Enrich with project_slug
            if _proj_slug:
                _run_meta["project_slug"] = _proj_slug
            await write_activity(
                client=_get_svc2(),
                user_id=user_id,
                event_type="agent_run",
                summary=f"{title} v{next_version} {final_status}",
                event_ref=version_id,
                metadata=_run_meta,
            )
        except Exception:
            pass  # Non-fatal — never block execution

        # ADR-120 Phase 3: Record work units for delivered agent runs
        if final_status == "delivered":
            try:
                from services.platform_limits import record_work_units
                record_work_units(svc_client, user_id, "agent_run", 1, agent_id=str(agent_id))
            except Exception:
                pass  # Non-fatal

        # ADR-114: Event-driven Composer heartbeat on delivered runs
        if final_status == "delivered":
            try:
                from services.composer import maybe_trigger_heartbeat
                await maybe_trigger_heartbeat(client, user_id, "agent_run_delivered", {
                    "agent_id": str(agent_id), "role": role,
                })
            except Exception as e:
                logger.warning(f"[EXEC] Event heartbeat trigger failed: {e}")

        # ADR-121: Write contributor output to project workspace BEFORE triggering PM.
        # This closes the critical gap where PM couldn't assess contribution quality
        # because contributions never existed in /projects/{slug}/contributions/{agent_slug}/.
        if final_status == "delivered" and role != "pm":
            try:
                await _write_contribution_to_projects(svc_client, user_id, slug, draft)
            except Exception as e:
                logger.warning(f"[EXEC] Project contribution write failed: {e}")

        # ADR-120: Project heartbeat — if this agent contributes to projects,
        # advance the PM's schedule so it runs on next scheduler cycle
        if final_status == "delivered" and role != "pm":
            try:
                await _maybe_trigger_project_heartbeat(client, user_id, agent, slug)
            except Exception as e:
                logger.warning(f"[EXEC] Project heartbeat trigger failed: {e}")

        return {
            "success": final_status == "delivered",
            "run_id": version_id,
            "version_number": next_version,
            "status": final_status,
            "message": f"Run {next_version} {final_status}" + (f": {delivery_error}" if delivery_error else ""),
            "delivery": delivery_result.model_dump() if delivery_result else None,
            "strategy": strategy.strategy_name,  # ADR-045: Track which strategy was used
        }

    except Exception as e:
        logger.error(f"[EXEC] Error: {e}")

        # ADR-066: Mark version as failed (not rejected)
        if version:
            try:
                client.table("agent_runs").update({
                    "status": "failed",
                    "delivery_error": str(e),
                }).eq("id", version["id"]).execute()
            except Exception as e2:
                logger.error(f"Failed to mark version {version['id']} as failed: {e2}")

        return {
            "success": False,
            "run_id": version["id"] if version else None,
            "status": "failed",
            "message": str(e),
        }
