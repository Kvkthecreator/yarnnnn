"""
Deliverable Execution Service - ADR-042 Simplified Flow + ADR-066 Delivery-First

Single Execute call for deliverable generation with immediate delivery (no approval gate).

Flow:
  Execute(action="deliverable.generate", target="deliverable:uuid")
    → check_deliverable_freshness() (ADR-049)
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
- No governance/approval gate - deliverables deliver immediately
- Version status: generating → delivered | failed
- Governance field ignored (backwards compatibility)

This module replaces:
- execute_deliverable_pipeline() - 3-step orchestrator
- execute_gather_step() - separate gather work_ticket
- execute_synthesize_step() - separate synthesize work_ticket
- execute_stage_step() - validation/staging step

Preserves from deliverable_pipeline.py:
- Type-specific prompts (TYPE_PROMPTS, build_type_prompt)
- Output validation (validate_output)
- Past versions context (get_past_versions_context)
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

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


def normalize_destination_for_delivery(
    destination: Optional[dict],
    user_email: Optional[str],
) -> Optional[dict]:
    """
    Normalize destination for delivery, defaulting to user's email.

    ADR-066 email-first: If destination is incomplete or missing target,
    fall back to sending to user's registered email address.

    Args:
        destination: The deliverable's destination config
        user_email: User's email address

    Returns:
        Normalized destination dict, or None if no valid destination
    """
    # No destination at all - use email (aliased to gmail exporter)
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


async def get_next_version_number(client, deliverable_id: str) -> int:
    """Get the next version number for a deliverable."""
    result = (
        client.table("deliverable_versions")
        .select("version_number")
        .eq("deliverable_id", deliverable_id)
        .order("version_number", desc=True)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]["version_number"] + 1
    return 1


async def create_version_record(
    client,
    deliverable_id: str,
    version_number: int,
) -> dict:
    """Create a new version record in 'generating' status."""
    version_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    result = (
        client.table("deliverable_versions")
        .insert({
            "id": version_id,
            "deliverable_id": deliverable_id,
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




def _build_headless_system_prompt(
    deliverable_type: str,
    trigger_context: Optional[dict] = None,
    research_directive: Optional[str] = None,
    deliverable: Optional[dict] = None,
    user_context: Optional[list] = None,
    learned_preferences: Optional[str] = None,
) -> str:
    """
    Build system prompt for headless mode generation (ADR-080/081/087/101).

    ADR-101 prompt composition order:
      1. Output Rules
      2. User Context (profile + preferences from user_memory)
      3. Directives (deliverable_instructions)
      4. Memory (observations, goal, review_log)
      5. Feedback (learned preferences from past version edits)
      6. Tool Usage guidance
      7. Trigger Context (signal/proactive)

    Args:
        deliverable_type: The deliverable type (digest, brief, status, etc.)
        trigger_context: Optional trigger info with signal reasoning
        research_directive: Optional research instruction for research/hybrid types
        deliverable: Optional deliverable dict with deliverable_instructions and deliverable_memory
        user_context: Optional list of user_memory rows (profile + preferences)
        learned_preferences: Optional formatted string from get_past_versions_context()

    Returns:
        Complete system prompt string
    """
    prompt = f"""You are generating a {deliverable_type} deliverable.

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

    # ADR-087: Inject deliverable-scoped instructions and memory
    if deliverable:
        instructions = (deliverable.get("deliverable_instructions") or "").strip()
        if instructions:
            prompt += f"""

## Deliverable Instructions
The user has set these behavioral directives for this deliverable:
{instructions}"""

        memory = deliverable.get("deliverable_memory") or {}
        memory_parts = []

        # Goal (for goal-mode deliverables)
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
            prompt += "\n\n## Deliverable Memory\n" + "\n".join(memory_parts)

    # ADR-101: Inject learned preferences (feedback from past version edits)
    if learned_preferences:
        prompt += f"\n\n## Learned Preferences\n{learned_preferences}"

    # ADR-081: Research directive overrides default tool guidance
    if research_directive:
        prompt += f"""

## Research Directive
{research_directive}

## Tool Usage
You have investigation tools available: Search, Read, List, WebSearch, GetSystemState.
- Use **WebSearch** to conduct web research as described above.
- Use **Search** or **Read** to cross-reference with the user's platform data if provided.
- Conduct 2-4 targeted searches, then synthesize findings into the deliverable format.
- After researching, generate the deliverable in a single pass — do not search further."""
    else:
        prompt += """

## Tool Usage (Headless Mode)
You have read-only investigation tools available: Search, Read, List, WebSearch, GetSystemState.
- Use tools ONLY if the gathered context in the user message is clearly insufficient to produce the deliverable.
- Prefer generating from the provided context — most deliverables have enough.
- If you do use a tool, do so in the first turn, then generate in the next.
- NEVER use tools to stall — if context is adequate, generate immediately."""

    # Inject trigger context when available
    if trigger_context:
        trigger_type = trigger_context.get("type", "")

        # Proactive review: forward the review decision note to generation
        if trigger_type == "proactive_review":
            review_decision = trigger_context.get("review_decision", {})
            review_note = review_decision.get("note", "")
            if review_note:
                prompt += f"\n\n## Review Context\nThis deliverable was triggered by a proactive review pass that found:\n{review_note}\n\nUse this as your starting point — investigate these themes further with your tools."

        # Signal processing: forward signal reasoning
        signal_reasoning = trigger_context.get("signal_reasoning", "")
        signal_ctx = trigger_context.get("signal_context", {})
        if signal_reasoning:
            prompt += f"\n\n## Signal Context\nThis deliverable was triggered by signal processing because:\n{signal_reasoning}"
        if signal_ctx:
            entity = signal_ctx.get("entity", "")
            platforms = signal_ctx.get("platforms", [])
            if entity:
                prompt += f"\nFocus entity: {entity}"
            if platforms:
                prompt += f"\nRelevant platforms: {', '.join(platforms)}"

    return prompt


# ADR-080 + ADR-081: Binding-aware tool round limits
HEADLESS_TOOL_ROUNDS = {
    "platform_bound":  2,   # Rarely needs tools — context is pre-gathered
    "cross_platform":  3,   # Occasionally useful for cross-referencing
    "research":        6,   # Needs room for web search + follow-up
    "hybrid":          6,   # Web research + platform investigation
}


async def generate_draft_inline(
    client,
    user_id: str,
    deliverable: dict,
    gathered_context: str,
    trigger_context: Optional[dict] = None,
    research_directive: Optional[str] = None,
) -> str:
    """
    Generate draft content via agent in headless mode (ADR-080/081).

    The agent has read-only tools (Search, Read, List, WebSearch,
    GetSystemState) available for investigation when gathered context
    is insufficient. Most deliverables generate in a single turn
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
    from services.deliverable_pipeline import (
        build_type_prompt,
        validate_output,
        get_past_versions_context,
    )

    deliverable_id = deliverable.get("id")
    deliverable_type = deliverable.get("deliverable_type", "custom")
    type_config = deliverable.get("type_config", {})
    recipient_context = deliverable.get("recipient_context", {})

    # Format recipient context
    recipient_str = ""
    if recipient_context:
        name = recipient_context.get("name", "")
        role = recipient_context.get("role", "")
        priorities = recipient_context.get("priorities", [])
        if name or role:
            recipient_str = f"RECIPIENT: {name}"
            if role:
                recipient_str += f" ({role})"
            if priorities:
                recipient_str += f"\nPRIORITIES: {', '.join(priorities)}"

    # Get past versions context for feedback patterns
    past_versions = await get_past_versions_context(client, deliverable_id) if deliverable_id else ""

    # Build type-specific prompt (user message)
    # ADR-101: past_versions moved to system prompt as learned_preferences
    prompt = build_type_prompt(
        deliverable_type=deliverable_type,
        config=type_config,
        deliverable=deliverable,
        gathered_context=gathered_context,
        recipient_text=recipient_str,
        past_versions="",
    )

    # Fetch lightweight user context for personalized headless output
    user_context = None
    try:
        user_ctx_result = client.table("user_memory").select(
            "key, value"
        ).eq("user_id", user_id).in_(
            "key", [
                "name", "role", "company", "timezone",
                "tone_slack", "tone_gmail", "verbosity_slack", "verbosity_gmail",
            ]
        ).limit(10).execute()
        # Also get preference: entries
        pref_result = client.table("user_memory").select(
            "key, value"
        ).eq("user_id", user_id).like("key", "preference:%").limit(5).execute()
        user_context = (user_ctx_result.data or []) + (pref_result.data or [])
    except Exception as e:
        logger.warning(f"[GENERATE] Failed to fetch user context: {e}")

    # ADR-080/081/087/101: Headless system prompt with tool usage, research directive,
    # deliverable-scoped instructions + memory, learned preferences, and user context
    system_prompt = _build_headless_system_prompt(
        deliverable_type, trigger_context, research_directive, deliverable, user_context,
        learned_preferences=past_versions,
    )

    # ADR-081: Binding-aware tool round limit
    classification = deliverable.get("type_classification", {})
    binding = classification.get("binding", "cross_platform")
    max_tool_rounds = HEADLESS_TOOL_ROUNDS.get(binding, 3)

    # Brief (meeting prep) needs more rounds for per-attendee research + WebSearch
    if deliverable_type == "brief":
        max_tool_rounds = max(max_tool_rounds, 5)

    # ADR-080: Mode-gated tools and executor
    # ADR-092: Pass deliverable sources so headless RefreshPlatformContent can scope to them
    headless_tools = get_tools_for_mode("headless")
    executor = create_headless_executor(client, user_id, deliverable_sources=deliverable.get("sources"))

    import json

    try:
        # ADR-080: Agentic loop — agent can use read-only tools if needed
        messages = [{"role": "user", "content": prompt}]
        tools_used = []  # Track tool names for observability

        for round_num in range(max_tool_rounds + 1):
            response = await chat_completion_with_tools(
                messages=messages,
                system=system_prompt,
                tools=headless_tools,
                model=SONNET_MODEL,
                max_tokens=4000,
            )

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
                draft = response.text.strip() if response.text else ""
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

        # Validate output (non-blocking - just log warnings)
        validation = validate_output(deliverable_type, draft, type_config)
        if not validation.get("valid"):
            logger.warning(f"[GENERATE] Validation warnings: {validation.get('issues', [])}")

        return draft

    except Exception as e:
        logger.error(f"[GENERATE] LLM call failed: {e}")
        raise


async def update_version_for_delivery(
    client,
    version_id: str,
    draft_content: str,
):
    """
    Prepare version for delivery by storing content.

    ADR-066: Versions go directly to delivery, no staged status.
    Status remains 'generating' until delivery completes.
    """
    client.table("deliverable_versions").update({
        "draft_content": draft_content,
        "final_content": draft_content,  # ADR-066: No editing step, content is final
    }).eq("id", version_id).execute()


# =============================================================================
# Main Entry Point - ADR-042, ADR-045, ADR-066 Delivery-First
# =============================================================================

async def execute_deliverable_generation(
    client,
    user_id: str,
    deliverable: dict,
    trigger_context: Optional[dict] = None,
) -> dict:
    """
    Execute deliverable generation with immediate delivery (no approval gate).

    ADR-042: Simplified single-call flow
    ADR-045: Strategy selection based on type_classification.binding
    ADR-049: Context freshness checks and source snapshots
    ADR-066: Delivery-first, no governance - always attempt delivery

    Args:
        client: Supabase client
        user_id: User UUID
        deliverable: Full deliverable dict (from database)
        trigger_context: Optional trigger info (schedule, event, manual)

    Returns:
        Result dict with version_id, status, message
        Status is 'delivered' or 'failed' (no 'staged' per ADR-066)
    """
    from services.execution_strategies import get_execution_strategy
    from services.freshness import (
        check_deliverable_freshness,
        record_source_snapshots,
    )

    deliverable_id = deliverable.get("id")
    deliverable_type = deliverable.get("deliverable_type", "custom")
    title = deliverable.get("title", "Untitled")
    trigger_type = trigger_context.get("type", "manual") if trigger_context else "manual"
    classification = deliverable.get("type_classification", {})
    binding = classification.get("binding", "cross_platform")

    logger.info(
        f"[EXEC] Starting: {title} ({deliverable_id}), "
        f"trigger={trigger_type}, binding={binding}"
    )

    version = None
    freshness_result = None

    try:
        # ADR-049: Check source freshness before generation
        freshness_result = await check_deliverable_freshness(client, user_id, deliverable)
        if not freshness_result["all_fresh"]:
            stale_count = len(freshness_result["stale_sources"])
            never_synced_count = len(freshness_result["never_synced"])
            logger.info(
                f"[EXEC] Freshness: {stale_count} stale, {never_synced_count} never synced"
            )
            # Note: We proceed with generation using available data
            # Targeted sync is handled separately if user requests it

        # 1. Get next version number
        next_version = await get_next_version_number(client, deliverable_id)

        # 2. Create version record (generating)
        version = await create_version_record(client, deliverable_id, next_version)
        version_id = version["id"]

        # 3. ADR-045: Select and execute strategy for context gathering
        strategy = get_execution_strategy(deliverable)
        gathered_result = await strategy.gather_context(client, user_id, deliverable)

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
        research_directive = context_summary.get("research_directive")
        draft = await generate_draft_inline(
            client, user_id, deliverable, gathered_context,
            trigger_context, research_directive,
        )

        # 5. ADR-066: Prepare version for delivery (no staged status)
        await update_version_for_delivery(client, version_id, draft)

        # ADR-073: Mark consumed platform content as retained
        if gathered_result.platform_content_ids:
            try:
                from services.platform_content import mark_content_retained
                await mark_content_retained(
                    client,
                    gathered_result.platform_content_ids,
                    reason="deliverable_execution",
                    ref=version_id,
                )
            except Exception as e:
                logger.warning(f"[EXEC] Failed to mark content retained: {e}")

        # ADR-049: Record source snapshots for audit trail
        # sources_used is a list of strings like "platform:slack", "other:document"
        # Build snapshot from the deliverable's source configs
        sources_for_snapshot = []
        for source in deliverable.get("sources", []):
            if source.get("type") == "integration_import":
                sources_for_snapshot.append({
                    "platform": source.get("provider"),
                    "resource_id": source.get("resource_id"),
                    "resource_name": source.get("resource_name"),
                    "user_id": user_id,
                })
        await record_source_snapshots(client, version_id, sources_for_snapshot)

        # 6. Update deliverable last_run_at
        client.table("deliverables").update({
            "last_run_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", deliverable_id).execute()

        # 7. ADR-066: Always attempt delivery (no governance check)
        # Email-first: normalize/fallback to user's email if destination incomplete
        # get_user_email requires service role (auth.admin API)
        from services.supabase import get_service_client as _get_svc
        user_email = get_user_email(_get_svc(), user_id)
        raw_destination = deliverable.get("destination")
        destination = normalize_destination_for_delivery(raw_destination, user_email)

        # Update deliverable with normalized destination if it changed
        if destination and destination != raw_destination:
            try:
                client.table("deliverables").update({
                    "destination": destination,
                }).eq("id", deliverable_id).execute()
                logger.info(f"[EXEC] Updated deliverable destination to email-first default")
            except Exception:
                pass  # Non-fatal

        final_status = "delivered"
        delivery_result = None
        delivery_error = None

        if destination:
            logger.info(f"[EXEC] ADR-066 delivery-first: delivering version={version_id}")

            try:
                from services.delivery import get_delivery_service
                delivery_service = get_delivery_service(client)
                delivery_result = await delivery_service.deliver_version(
                    version_id=version_id,
                    user_id=user_id,
                )
                if delivery_result.status.value == "success":
                    final_status = "delivered"
                    # Update version status to delivered
                    now = datetime.now(timezone.utc).isoformat()
                    client.table("deliverable_versions").update({
                        "status": "delivered",
                        "delivered_at": now,
                    }).eq("id", version_id).execute()
                else:
                    final_status = "failed"
                    delivery_error = delivery_result.error_message
                    client.table("deliverable_versions").update({
                        "status": "failed",
                        "delivery_error": delivery_error,
                    }).eq("id", version_id).execute()
                logger.info(f"[EXEC] Delivery: {delivery_result.status.value}")
            except Exception as e:
                logger.error(f"[EXEC] Delivery failed: {e}")
                final_status = "failed"
                delivery_error = str(e)
                client.table("deliverable_versions").update({
                    "status": "failed",
                    "delivery_error": delivery_error,
                }).eq("id", version_id).execute()
        else:
            # No destination configured - mark as delivered (content generated successfully)
            now = datetime.now(timezone.utc).isoformat()
            client.table("deliverable_versions").update({
                "status": "delivered",
                "delivered_at": now,
            }).eq("id", version_id).execute()
            logger.info(f"[EXEC] No destination - content ready (version={version_id})")

        logger.info(
            f"[EXEC] Complete: {title}, version={next_version}, "
            f"status={final_status}, strategy={strategy.strategy_name}"
        )

        # Activity log: record this deliverable run (ADR-063)
        # Requires service role — activity_log has no user INSERT policy
        try:
            from services.activity_log import write_activity
            from services.supabase import get_service_client as _get_svc2
            await write_activity(
                client=_get_svc2(),
                user_id=user_id,
                event_type="deliverable_run",
                summary=f"{title} v{next_version} {final_status}",
                event_ref=version_id,
                metadata={
                    "deliverable_id": str(deliverable_id),
                    "version_number": next_version,
                    "deliverable_type": deliverable_type,  # ADR-064: For pattern detection
                    "strategy": strategy.strategy_name,
                    "final_status": final_status,
                    "delivery_error": delivery_error,
                },
            )
        except Exception:
            pass  # Non-fatal — never block execution

        return {
            "success": final_status == "delivered",
            "version_id": version_id,
            "version_number": next_version,
            "status": final_status,
            "message": f"Version {next_version} {final_status}" + (f": {delivery_error}" if delivery_error else ""),
            "delivery": delivery_result.model_dump() if delivery_result else None,
            "strategy": strategy.strategy_name,  # ADR-045: Track which strategy was used
        }

    except Exception as e:
        logger.error(f"[EXEC] Error: {e}")

        # ADR-066: Mark version as failed (not rejected)
        if version:
            try:
                client.table("deliverable_versions").update({
                    "status": "failed",
                    "delivery_error": str(e),
                }).eq("id", version["id"]).execute()
            except Exception as e2:
                logger.error(f"Failed to mark version {version['id']} as failed: {e2}")

        return {
            "success": False,
            "version_id": version["id"] if version else None,
            "status": "failed",
            "message": str(e),
        }
