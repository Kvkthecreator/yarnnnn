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
    → single work_ticket, single version row

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


async def create_work_ticket(
    client,
    user_id: str,
    deliverable_id: str,
    version_id: str,
) -> dict:
    """
    Create a single work ticket for the generation.

    ADR-042: No chaining (depends_on_work_id=NULL), no pipeline_step.
    """
    ticket_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    result = (
        client.table("work_tickets")
        .insert({
            "id": ticket_id,
            "user_id": user_id,
            "task": "deliverable.generate",
            "agent_type": "deliverable",
            "status": "running",
            "deliverable_id": deliverable_id,
            "deliverable_version_id": version_id,
            "started_at": now,
            # ADR-042: Explicitly NULL - no chaining
            "depends_on_work_id": None,
            "pipeline_step": None,
            "chain_output_as_memory": False,
        })
        .execute()
    )

    return result.data[0] if result.data else {"id": ticket_id}


async def log_execution_inputs(
    ticket_id: str,
    deliverable: dict,
    context_summary: dict,
):
    """
    Log execution inputs to work_execution_log for debugging.

    ADR-042: Replaces full context snapshots with lightweight input logging.
    Uses service role client — work_execution_log has no user INSERT policy.
    """
    try:
        from services.supabase import get_service_client
        service_client = get_service_client()
        service_client.table("work_execution_log").insert({
            "ticket_id": ticket_id,
            "stage": "started",
            "message": f"Generating {deliverable.get('deliverable_type', 'custom')} deliverable",
            "metadata": {
                "deliverable_id": deliverable.get("id"),
                "deliverable_type": deliverable.get("deliverable_type"),
                "sources_count": len(deliverable.get("sources", [])),
                "context_summary": context_summary,
            },
        }).execute()
    except Exception as e:
        logger.warning(f"[EXEC] Failed to log inputs: {e}")


def _build_headless_system_prompt(
    deliverable_type: str,
    trigger_context: Optional[dict] = None,
) -> str:
    """
    Build system prompt for headless mode generation (ADR-080).

    The headless agent has read-only tools (Search, Read, List, WebSearch,
    GetSystemState) available for investigating when gathered context is
    insufficient. The system prompt instructs the agent on when and how
    to use them.

    Args:
        deliverable_type: The deliverable type (status_report, etc.)
        trigger_context: Optional trigger info with signal reasoning

    Returns:
        Complete system prompt string
    """
    prompt = f"""You are generating a {deliverable_type} deliverable.

## Output Rules
- Follow the format and instructions in the user message exactly.
- Be concise and professional — keep content tight and scannable.
- Do not invent information not present in the provided context.
- Do not use emojis in headers or content unless the user's preferences explicitly request them.
- Use plain markdown headers (##, ###) and bullet points for structure.
- If the user's context mentions a preference for conciseness, prioritize brevity over completeness.

## Tool Usage (Headless Mode)
You have read-only investigation tools available: Search, Read, List, WebSearch, GetSystemState.
- Use tools ONLY if the gathered context in the user message is clearly insufficient to produce the deliverable.
- Prefer generating from the provided context — most deliverables have enough.
- If you do use a tool, do so in the first turn, then generate in the next.
- Maximum 3 tool rounds. After that, generate with whatever context you have.
- NEVER use tools to stall — if context is adequate, generate immediately."""

    # Inject signal reasoning when available
    if trigger_context:
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


# ADR-080: Maximum tool rounds in headless mode
HEADLESS_MAX_TOOL_ROUNDS = 3


async def generate_draft_inline(
    client,
    user_id: str,
    deliverable: dict,
    gathered_context: str,
    trigger_context: Optional[dict] = None,
) -> str:
    """
    Generate draft content via agent in headless mode (ADR-080).

    The agent has read-only tools (Search, Read, List, WebSearch,
    GetSystemState) available for investigation when gathered context
    is insufficient. Most deliverables generate in a single turn
    without tool use.

    ADR-042: Replaces execute_synthesize_step(). No separate work_ticket.
    ADR-080: Unified agent in headless mode — chat_completion_with_tools
    with mode-gated primitives and max 3 tool rounds.
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
    prompt = build_type_prompt(
        deliverable_type=deliverable_type,
        config=type_config,
        deliverable=deliverable,
        gathered_context=gathered_context,
        recipient_text=recipient_str,
        past_versions=past_versions,
    )

    # ADR-080: Headless system prompt with tool usage instructions
    system_prompt = _build_headless_system_prompt(deliverable_type, trigger_context)

    # ADR-080: Mode-gated tools and executor
    headless_tools = get_tools_for_mode("headless")
    executor = create_headless_executor(client, user_id)

    try:
        # ADR-080: Agentic loop — agent can use read-only tools if needed
        messages = [{"role": "user", "content": prompt}]

        for round_num in range(HEADLESS_MAX_TOOL_ROUNDS + 1):
            response = await chat_completion_with_tools(
                messages=messages,
                system=system_prompt,
                tools=headless_tools,
                model=SONNET_MODEL,
                max_tokens=4000,
            )

            if response.stop_reason == "end_turn" or not response.tool_uses:
                # Agent is done — extract text
                draft = response.text.strip()
                if round_num > 0:
                    logger.info(f"[GENERATE] Headless agent used {round_num} tool round(s)")
                break

            # Agent wants to use tools — execute them
            if round_num >= HEADLESS_MAX_TOOL_ROUNDS:
                # Hit limit — use whatever text the agent produced
                logger.warning(f"[GENERATE] Headless agent hit max tool rounds ({HEADLESS_MAX_TOOL_ROUNDS})")
                draft = response.text.strip() if response.text else ""
                break

            # Build assistant message with tool use blocks
            import json
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
                logger.info(f"[GENERATE] Headless tool: {tu.name}({str(tu.input)[:100]})")
                result = await executor(tu.name, tu.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": json.dumps(result) if isinstance(result, dict) else str(result),
                })

            messages.append({"role": "user", "content": tool_results})
        else:
            # for/else: loop completed without break — shouldn't happen but be safe
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


async def update_version_staged(
    client,
    version_id: str,
    draft_content: str,
):
    """
    DEPRECATED: Use update_version_for_delivery instead.

    Legacy function kept for backwards compatibility.
    ADR-066 removed staged status in favor of direct delivery.
    """
    now = datetime.now(timezone.utc).isoformat()

    client.table("deliverable_versions").update({
        "status": "staged",
        "draft_content": draft_content,
        "staged_at": now,
    }).eq("id", version_id).execute()


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


async def complete_work_ticket(
    client,
    ticket_id: str,
    result: dict,
):
    """Mark work ticket as completed."""
    now = datetime.now(timezone.utc).isoformat()

    # Update ticket status (result stored in execution log instead)
    client.table("work_tickets").update({
        "status": "completed",
        "completed_at": now,
    }).eq("id", ticket_id).execute()

    # Log completion with result details
    try:
        client.table("work_execution_log").insert({
            "ticket_id": ticket_id,
            "stage": "completed",
            "message": "Generation complete",
            "metadata": result,
        }).execute()
    except Exception:
        pass


async def fail_work_ticket(
    client,
    ticket_id: str,
    error_message: str,
):
    """Mark work ticket as failed."""
    now = datetime.now(timezone.utc).isoformat()

    client.table("work_tickets").update({
        "status": "failed",
        "completed_at": now,
        "error_message": error_message,
    }).eq("id", ticket_id).execute()

    # Log failure
    try:
        client.table("work_execution_log").insert({
            "ticket_id": ticket_id,
            "stage": "failed",
            "message": error_message,
        }).execute()
    except Exception:
        pass


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
    ticket = None
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

        # 3. Create single work ticket (no chaining)
        ticket = await create_work_ticket(client, user_id, deliverable_id, version_id)
        ticket_id = ticket["id"]

        # 4. ADR-045: Select and execute strategy for context gathering
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

        # 5. Log inputs for debugging
        await log_execution_inputs(ticket_id, deliverable, context_summary)

        # 6. Generate draft inline (ADR-080: pass trigger_context for signal reasoning)
        draft = await generate_draft_inline(client, user_id, deliverable, gathered_context, trigger_context)

        # 7. ADR-066: Prepare version for delivery (no staged status)
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

        # 8. Complete work ticket
        await complete_work_ticket(client, ticket_id, {
            "draft_length": len(draft),
            "sources_used": context_summary.get("sources_used", []),
        })

        # 9. Update deliverable last_run_at
        client.table("deliverables").update({
            "last_run_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", deliverable_id).execute()

        # 10. ADR-066: Always attempt delivery (no governance check)
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
            except Exception:
                pass

        # Mark ticket as failed
        if ticket:
            try:
                await fail_work_ticket(client, ticket["id"], str(e))
            except Exception:
                pass

        return {
            "success": False,
            "version_id": version["id"] if version else None,
            "status": "failed",
            "message": str(e),
        }
