"""
Deliverable Execution Service - ADR-042 Simplified Flow

Single Execute call for deliverable generation, replacing the 3-step pipeline.

Flow:
  Execute(action="deliverable.generate", target="deliverable:uuid")
    → check_deliverable_freshness() (ADR-049)
    → sync_stale_sources() if needed (ADR-049)
    → gather_context_inline()
    → generate_draft_inline()
    → record_source_snapshots() (ADR-049)
    → single work_ticket, single version row

ADR-049 Integration:
- Freshness check before generation
- Targeted sync of stale sources
- Source snapshots recorded for audit trail

This module replaces:
- execute_deliverable_pipeline() - 3-step orchestrator
- execute_gather_step() - separate gather work_ticket
- execute_synthesize_step() - separate synthesize work_ticket
- execute_stage_step() - validation/staging step

Preserves from deliverable_pipeline.py:
- Source fetching utilities (fetch_integration_source_data)
- Type-specific prompts (TYPE_PROMPTS, build_type_prompt)
- Output validation (validate_output)
- Haiku extraction (extract_with_haiku)
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# Model constants
SONNET_MODEL = "claude-sonnet-4-20250514"


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
    client,
    ticket_id: str,
    deliverable: dict,
    context_summary: dict,
):
    """
    Log execution inputs to work_execution_log for debugging.

    ADR-042: Replaces full context snapshots with lightweight input logging.
    """
    try:
        client.table("work_execution_log").insert({
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


async def gather_context_inline(
    client,
    user_id: str,
    deliverable: dict,
) -> tuple[str, dict]:
    """
    Gather context from all sources inline.

    ADR-042: Replaces execute_gather_step(). No separate work_ticket.

    Returns:
        Tuple of (gathered_context_string, context_summary_dict)
    """
    from services.deliverable_pipeline import (
        fetch_integration_source_data,
        extract_with_haiku,
    )

    sources = deliverable.get("sources", [])
    last_run_at = deliverable.get("last_run_at")
    deliverable_id = deliverable.get("id")

    context_parts = []
    context_summary = {
        "sources_used": [],
        "total_items_fetched": 0,
    }

    # Parse last_run_at for delta extraction
    if last_run_at and isinstance(last_run_at, str):
        try:
            if last_run_at.endswith("Z"):
                last_run_at = last_run_at[:-1] + "+00:00"
            last_run_at = datetime.fromisoformat(last_run_at)
        except (ValueError, TypeError):
            last_run_at = None

    # Process each source
    for idx, source in enumerate(sources):
        source_type = source.get("type")

        if source_type == "integration_import":
            # Fetch from platform integration
            result = await fetch_integration_source_data(
                client=client,
                user_id=user_id,
                source=source,
                last_run_at=last_run_at,
                deliverable_id=deliverable_id,
                source_index=idx,
            )
            if result.content:
                provider = source.get("provider", "unknown")
                context_parts.append(f"[{provider.upper()} DATA]\n{result.content}")
                context_summary["sources_used"].append(f"platform:{provider}")
                context_summary["total_items_fetched"] += result.items_fetched

        elif source_type == "url":
            # URL-based source (existing logic)
            url = source.get("value", "")
            if url:
                context_parts.append(f"[URL SOURCE: {url}]\n(URL fetching not implemented in simplified flow)")
                context_summary["sources_used"].append(f"url:{url[:50]}")

        elif source_type == "document":
            # Document reference
            doc_id = source.get("document_id")
            if doc_id:
                try:
                    doc_result = (
                        client.table("filesystem_documents")
                        .select("filename, extracted_text")
                        .eq("id", doc_id)
                        .single()
                        .execute()
                    )
                    if doc_result.data:
                        doc = doc_result.data
                        text = doc.get("extracted_text", "")[:5000]
                        context_parts.append(f"[DOCUMENT: {doc.get('filename')}]\n{text}")
                        context_summary["sources_used"].append(f"document:{doc.get('filename')}")
                except Exception as e:
                    logger.warning(f"[GATHER] Failed to fetch document {doc_id}: {e}")

        elif source_type == "description":
            # Manual description
            desc = source.get("value", "")
            if desc:
                context_parts.append(f"[SOURCE DESCRIPTION]\n{desc}")
                context_summary["sources_used"].append("description")

    # Get user memories
    memories = await _get_relevant_memories(client, user_id, deliverable)
    if memories:
        context_parts.append(f"[USER CONTEXT]\n{memories}")
        context_summary["memories_count"] = memories.count("\n") + 1

    # Get past version feedback
    from services.deliverable_pipeline import get_past_versions_context
    past_context = await get_past_versions_context(client, deliverable_id)
    if past_context:
        context_parts.append(past_context)

    gathered_context = "\n\n---\n\n".join(context_parts) if context_parts else "(No context available)"

    return gathered_context, context_summary


async def _get_relevant_memories(client, user_id: str, deliverable: dict) -> str:
    """Get relevant user knowledge for context."""
    try:
        # Get user knowledge entries (ADR-058)
        result = (
            client.table("knowledge_entries")
            .select("content, tags, entry_type")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .order("importance", desc=True)
            .limit(20)
            .execute()
        )

        if not result.data:
            return ""

        memory_lines = []
        for mem in result.data:
            content = mem.get("content", "")
            tags = mem.get("tags", [])
            if tags:
                memory_lines.append(f"- {content} [{', '.join(tags)}]")
            else:
                memory_lines.append(f"- {content}")

        return "\n".join(memory_lines)

    except Exception as e:
        logger.warning(f"[GATHER] Failed to fetch memories: {e}")
        return ""


async def generate_draft_inline(
    client,
    user_id: str,
    deliverable: dict,
    gathered_context: str,
) -> str:
    """
    Generate draft content with single LLM call.

    ADR-042: Replaces execute_synthesize_step(). No separate work_ticket.
    """
    from services.anthropic import chat_completion
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

    # Build type-specific prompt
    prompt = build_type_prompt(
        deliverable_type=deliverable_type,
        config=type_config,
        deliverable=deliverable,
        gathered_context=gathered_context,
        recipient_text=recipient_str,
        past_versions=past_versions,
    )

    # Generate draft
    system_prompt = f"""You are generating a {deliverable_type} deliverable.
Follow the format and instructions exactly.
Be concise and professional.
Do not invent information not present in the provided context."""

    try:
        draft = await chat_completion(
            messages=[{"role": "user", "content": prompt}],
            system=system_prompt,
            model=SONNET_MODEL,
            max_tokens=4000,
        )
        draft = draft.strip()

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
    """Update version to staged status with draft content."""
    now = datetime.now(timezone.utc).isoformat()

    client.table("deliverable_versions").update({
        "status": "staged",
        "draft_content": draft_content,
        "staged_at": now,
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
# Main Entry Point - ADR-042 Simplified Execution + ADR-045 Type-Aware Strategies
# =============================================================================

async def execute_deliverable_generation(
    client,
    user_id: str,
    deliverable: dict,
    trigger_context: Optional[dict] = None,
) -> dict:
    """
    Execute deliverable generation with type-aware strategy selection.

    ADR-042: Simplified single-call flow
    ADR-045: Strategy selection based on type_classification.binding
    ADR-049: Context freshness checks and source snapshots

    Args:
        client: Supabase client
        user_id: User UUID
        deliverable: Full deliverable dict (from database)
        trigger_context: Optional trigger info (schedule, event, manual)

    Returns:
        Result dict with version_id, status, draft, message
    """
    from services.execution_strategies import get_execution_strategy
    from services.freshness import (
        check_deliverable_freshness,
        record_source_snapshots,
    )

    deliverable_id = deliverable.get("id")
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
        await log_execution_inputs(client, ticket_id, deliverable, context_summary)

        # 6. Generate draft inline
        draft = await generate_draft_inline(client, user_id, deliverable, gathered_context)

        # 7. Update version → staged
        await update_version_staged(client, version_id, draft)

        # ADR-049: Record source snapshots for audit trail
        sources_for_snapshot = []
        for source in gathered_result.sources_used:
            sources_for_snapshot.append({
                "platform": source.get("provider") or source.get("platform"),
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

        # 10. Handle full_auto governance (ADR-028)
        governance = deliverable.get("governance", "manual")
        destination = deliverable.get("destination")
        final_status = "staged"
        delivery_result = None

        if governance == "full_auto" and destination:
            logger.info(f"[EXEC] Full-auto: auto-approving version={version_id}")

            # Auto-approve
            now = datetime.now(timezone.utc).isoformat()
            client.table("deliverable_versions").update({
                "status": "approved",
                "final_content": draft,
                "approved_at": now,
            }).eq("id", version_id).execute()
            final_status = "approved"

            # Trigger delivery
            try:
                from services.delivery import get_delivery_service
                delivery_service = get_delivery_service(client)
                delivery_result = await delivery_service.deliver_version(
                    version_id=version_id,
                    user_id=user_id,
                )
                if delivery_result.status.value == "success":
                    final_status = "delivered"
                logger.info(f"[EXEC] Delivery: {delivery_result.status.value}")
            except Exception as e:
                logger.error(f"[EXEC] Delivery failed: {e}")

        logger.info(
            f"[EXEC] Complete: {title}, version={next_version}, "
            f"status={final_status}, strategy={strategy.strategy_name}"
        )

        return {
            "success": True,
            "version_id": version_id,
            "version_number": next_version,
            "status": final_status,
            "draft": draft if final_status == "staged" else None,
            "message": f"Version {next_version} ready for review" if final_status == "staged" else f"Version {next_version} delivered",
            "delivery": delivery_result.model_dump() if delivery_result else None,
            "strategy": strategy.strategy_name,  # ADR-045: Track which strategy was used
        }

    except Exception as e:
        logger.error(f"[EXEC] Error: {e}")

        # Mark version as rejected
        if version:
            try:
                client.table("deliverable_versions").update({
                    "status": "rejected",
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
            "status": "rejected",
            "message": str(e),
        }
