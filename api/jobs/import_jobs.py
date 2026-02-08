"""
YARNNN v5 - Integration Import Jobs

Processes context import jobs for Slack/Notion integrations.
Integrated into unified_scheduler.py to run every 5 minutes.

Flow:
1. Query pending import jobs
2. Fetch user's integration credentials
3. Fetch data via MCP (Slack channels, Notion pages)
4. Run ContextImportAgent to extract structured blocks
5. Optionally run StyleLearningAgent to extract communication style (Phase 5)
6. Store results in memories table with source_type='import'
7. Update job status

See ADR-027: Integration Read Architecture
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)


async def store_style_memory(
    supabase_client,
    user_id: str,
    profile,  # StyleProfile from style_learning.py
    job_id: str,
) -> bool:
    """
    Store a style profile as a user-scoped memory.

    Style memories are always user-scoped (project_id = NULL) because
    communication style follows the user across all projects.

    Returns True if stored successfully.
    """
    from agents.integration.style_learning import (
        style_profile_to_memory_content,
        style_profile_to_source_ref,
    )

    try:
        memory_data = {
            "user_id": user_id,
            "project_id": None,  # User-scoped (portable)
            "content": style_profile_to_memory_content(profile),
            "source_type": "import",
            "source_ref": {
                **style_profile_to_source_ref(profile),
                "job_id": job_id,
            },
            "importance": 0.8,  # High importance for style
            "tags": ["style", profile.platform, profile.context],
        }

        supabase_client.table("memories").insert(memory_data).execute()

        logger.info(
            f"[STYLE] Stored {profile.platform} style profile for user "
            f"(confidence: {profile.confidence})"
        )
        return True

    except Exception as e:
        logger.error(f"[STYLE] Failed to store style memory: {e}")
        return False


async def get_pending_import_jobs(supabase_client) -> list[dict]:
    """
    Query import jobs that are pending and ready to process.

    Returns jobs with status='pending' ordered by created_at.
    """
    result = (
        supabase_client.table("integration_import_jobs")
        .select("*")
        .eq("status", "pending")
        .order("created_at", desc=False)
        .limit(10)  # Process in batches
        .execute()
    )

    return result.data or []


async def recover_stale_processing_jobs(supabase_client, stale_minutes: int = 10) -> int:
    """
    Reset jobs stuck in 'processing' status back to 'pending'.

    This is a safety net for jobs that started processing but failed
    (e.g., due to server restart) without updating their status.

    Args:
        supabase_client: Supabase client
        stale_minutes: Jobs processing longer than this are considered stale

    Returns:
        Number of jobs recovered
    """
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_minutes)

    # Find stale processing jobs
    result = (
        supabase_client.table("integration_import_jobs")
        .select("id, started_at")
        .eq("status", "processing")
        .lt("started_at", cutoff.isoformat())
        .execute()
    )

    stale_jobs = result.data or []

    if not stale_jobs:
        return 0

    # Reset them to pending
    job_ids = [job["id"] for job in stale_jobs]

    for job_id in job_ids:
        supabase_client.table("integration_import_jobs").update({
            "status": "pending",
            "started_at": None,
            "progress": 0,
            "error_message": "Job was stuck in processing - retrying",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", job_id).execute()

        logger.info(f"[IMPORT] Recovered stale job {job_id}")

    return len(job_ids)


async def get_user_integration(supabase_client, user_id: str, provider: str) -> Optional[dict]:
    """Get user's integration credentials for a provider."""
    result = (
        supabase_client.table("user_integrations")
        .select("id, access_token_encrypted, refresh_token_encrypted, metadata, status")
        .eq("user_id", user_id)
        .eq("provider", provider)
        .single()
        .execute()
    )

    return result.data if result.data else None


async def update_job_status(
    supabase_client,
    job_id: str,
    status: str,
    result: Optional[dict] = None,
    error: Optional[str] = None
):
    """Update import job status and result."""
    update_data = {
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    if status == "processing":
        update_data["started_at"] = datetime.now(timezone.utc).isoformat()
    elif status in ("completed", "failed"):
        update_data["completed_at"] = datetime.now(timezone.utc).isoformat()

    if result is not None:
        update_data["result"] = result
    if error is not None:
        update_data["error_message"] = error

    supabase_client.table("integration_import_jobs").update(update_data).eq(
        "id", job_id
    ).execute()


async def update_job_progress(
    supabase_client,
    job_id: str,
    progress: int,
    phase: str,
    items_total: int = 0,
    items_completed: int = 0,
    current_resource: Optional[str] = None,
) -> None:
    """
    ADR-030: Update job progress details for real-time tracking.

    Args:
        progress: 0-100 percentage
        phase: 'fetching' | 'processing' | 'storing'
        items_total: Total items to process
        items_completed: Items completed so far
        current_resource: Name of current resource being processed
    """
    progress_details = {
        "phase": phase,
        "items_total": items_total,
        "items_completed": items_completed,
        "current_resource": current_resource,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    supabase_client.table("integration_import_jobs").update({
        "progress": min(max(progress, 0), 100),
        "progress_details": progress_details,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", job_id).execute()


async def update_coverage_state(
    supabase_client,
    user_id: str,
    provider: str,
    resource_id: str,
    resource_name: str,
    coverage_state: str,
    scope: dict,
    items_extracted: int,
    blocks_created: int,
) -> None:
    """
    ADR-030: Update coverage state for a resource after extraction.

    Upserts integration_coverage record with extraction results.
    """
    try:
        # Check if exists
        existing = (
            supabase_client.table("integration_coverage")
            .select("id")
            .eq("user_id", user_id)
            .eq("provider", provider)
            .eq("resource_id", resource_id)
            .execute()
        )

        coverage_data = {
            "coverage_state": coverage_state,
            "scope": scope,
            "last_extracted_at": datetime.now(timezone.utc).isoformat(),
            "items_extracted": items_extracted,
            "blocks_created": blocks_created,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if existing.data:
            supabase_client.table("integration_coverage").update(coverage_data).eq(
                "id", existing.data[0]["id"]
            ).execute()
        else:
            coverage_data.update({
                "user_id": user_id,
                "provider": provider,
                "resource_id": resource_id,
                "resource_name": resource_name,
                "resource_type": "label" if provider == "gmail" else "channel" if provider == "slack" else "page",
            })
            supabase_client.table("integration_coverage").insert(coverage_data).execute()

        logger.info(f"[COVERAGE] Updated {provider}/{resource_id} -> {coverage_state}")

    except Exception as e:
        logger.warning(f"[COVERAGE] Failed to update coverage state: {e}")


async def store_memory_blocks(
    supabase_client,
    user_id: str,
    project_id: Optional[str],
    blocks: list,
    source_ref: dict
) -> int:
    """
    Store extracted context blocks as memories.

    Args:
        supabase_client: Supabase client
        user_id: User ID
        project_id: Optional project ID for scoping
        blocks: List of ContextBlock objects from the agent
        source_ref: Provenance info (platform, resource_id, job_id)

    Returns:
        Number of memories created
    """
    if not blocks:
        return 0

    # Map block types to importance scores
    importance_map = {
        "decision": 0.9,
        "action_item": 0.8,
        "technical": 0.7,
        "context": 0.6,
        "person": 0.7,
    }

    memories_to_insert = []
    for block in blocks:
        memories_to_insert.append({
            "user_id": user_id,
            "project_id": project_id,
            "content": block.content,
            "source_type": "import",
            "source_ref": {
                **source_ref,
                "block_type": block.block_type,
                "metadata": block.metadata,
            },
            "importance": importance_map.get(block.block_type, 0.5),
            "tags": [block.block_type],  # Tag with block type
        })

    result = supabase_client.table("memories").insert(memories_to_insert).execute()

    return len(result.data) if result.data else 0


async def process_slack_import(
    supabase_client,
    job: dict,
    integration: dict,
    mcp_manager,
    agent,
    token_manager,
) -> dict:
    """Process a Slack channel import job."""
    from agents.integration.style_learning import StyleLearningAgent
    from agents.integration.platform_semantics import extract_slack_channel_signals
    from services.ephemeral_context import store_slack_context_batch

    user_id = job["user_id"]
    metadata = integration.get("metadata", {}) or {}

    resource_id = job["resource_id"]
    resource_name = job.get("resource_name", resource_id)
    instructions = job.get("instructions")

    # Check if style learning is requested (from job config)
    config = job.get("config") or {}
    learn_style = config.get("learn_style", False)
    style_user_id = config.get("style_user_id")  # Slack user ID to analyze

    # ADR-030: Get scope parameters
    scope = job.get("scope") or {}
    max_items = scope.get("max_items", 200)

    # Decrypt access token
    access_token = token_manager.decrypt(integration["access_token_encrypted"])
    team_id = metadata.get("team_id")

    if not team_id:
        raise ValueError("Slack integration missing team_id")

    # ADR-030: Update progress - fetching phase
    await update_job_progress(
        supabase_client,
        job["id"],
        progress=10,
        phase="fetching",
        items_total=max_items,
        items_completed=0,
        current_resource=resource_name,
    )

    # 1. Fetch messages via MCP
    logger.info(f"[IMPORT] Fetching Slack channel: {resource_name} (max: {max_items})")
    messages = await mcp_manager.get_slack_channel_history(
        user_id=user_id,
        channel_id=resource_id,
        bot_token=access_token,
        team_id=team_id,
        limit=max_items,
    )

    if not messages:
        return {
            "blocks_created": 0,
            "items_processed": 0,
            "items_filtered": 0,
            "summary": "No messages found in channel",
            "style_learned": False,
        }

    # ADR-030: Update progress - processing phase
    await update_job_progress(
        supabase_client,
        job["id"],
        progress=50,
        phase="processing",
        items_total=len(messages),
        items_completed=0,
        current_resource=resource_name,
    )

    # 2. ADR-031: Extract platform-semantic signals
    logger.info(f"[IMPORT] Extracting platform-semantic signals from {len(messages)} messages")
    channel_signals = extract_slack_channel_signals(messages)

    logger.info(
        f"[IMPORT] Signals: {len(channel_signals['hot_threads'])} hot threads, "
        f"{len(channel_signals['unanswered_questions'])} unanswered, "
        f"{len(channel_signals['action_items'])} action items"
    )

    # 3. Run agent to extract context (decisions, action items, etc.)
    logger.info(f"[IMPORT] Processing {len(messages)} messages with agent")
    import_result = await agent.import_slack_channel(
        messages=messages,
        channel_name=resource_name,
        instructions=instructions,
    )

    # ADR-030: Update progress - storing phase
    await update_job_progress(
        supabase_client,
        job["id"],
        progress=75,
        phase="storing",
        items_total=len(import_result.blocks) if import_result.blocks else 0,
        items_completed=0,
        current_resource=resource_name,
    )

    # 4. ADR-031: Store raw messages to ephemeral_context (with signals)
    ephemeral_stored = await store_slack_context_batch(
        db_client=supabase_client,
        user_id=user_id,
        channel_id=resource_id,
        channel_name=resource_name,
        messages=messages,
    )
    logger.info(f"[IMPORT] Stored {ephemeral_stored} messages to ephemeral_context")

    # ADR-030: Update progress
    await update_job_progress(
        supabase_client,
        job["id"],
        progress=85,
        phase="storing",
        items_total=len(import_result.blocks) if import_result.blocks else 0,
        items_completed=0,
        current_resource=resource_name,
    )

    # 5. Store extracted blocks as memories (for long-term context)
    project_id = job.get("project_id")
    blocks_created = await store_memory_blocks(
        supabase_client,
        user_id=user_id,
        project_id=project_id,
        blocks=import_result.blocks,
        source_ref={
            "platform": "slack",
            "resource_id": resource_id,
            "resource_name": resource_name,
            "job_id": job["id"],
        },
    )

    # ADR-030: Update progress - nearly complete
    await update_job_progress(
        supabase_client,
        job["id"],
        progress=95,
        phase="storing",
        items_total=blocks_created,
        items_completed=blocks_created,
        current_resource=resource_name,
    )

    # 4. Optionally learn style from user's messages (Phase 5)
    style_learned = False
    style_confidence = None

    if learn_style:
        try:
            # Filter to user's messages if style_user_id provided
            user_messages = messages
            if style_user_id:
                user_messages = [m for m in messages if m.get("user") == style_user_id]

            if len(user_messages) >= 5:
                logger.info(f"[STYLE] Learning style from {len(user_messages)} messages")
                style_agent = StyleLearningAgent()
                profile = await style_agent.analyze_slack_messages(
                    messages=user_messages,
                    user_name=metadata.get("user_name"),
                )

                style_learned = await store_style_memory(
                    supabase_client,
                    user_id=user_id,
                    profile=profile,
                    job_id=job["id"],
                )
                style_confidence = profile.confidence
            else:
                logger.info(f"[STYLE] Skipping - only {len(user_messages)} user messages (need 5+)")
        except Exception as e:
            logger.warning(f"[STYLE] Style learning failed (non-fatal): {e}")

    # ADR-030: Update coverage state
    await update_coverage_state(
        supabase_client,
        user_id=user_id,
        provider="slack",
        resource_id=resource_id,
        resource_name=resource_name,
        coverage_state="partial",  # Slack is always partial (time-based)
        scope=scope,
        items_extracted=len(messages),
        blocks_created=blocks_created,
    )

    return {
        "blocks_created": blocks_created,
        "ephemeral_stored": ephemeral_stored,  # ADR-031
        "items_processed": import_result.items_processed,
        "items_filtered": import_result.items_filtered,
        "summary": import_result.summary,
        "style_learned": style_learned,
        "style_confidence": style_confidence,
        # ADR-031: Include signal summaries
        "signals": {
            "hot_threads": len(channel_signals["hot_threads"]),
            "unanswered_questions": len(channel_signals["unanswered_questions"]),
            "stalled_threads": len(channel_signals["stalled_threads"]),
            "action_items": len(channel_signals["action_items"]),
            "decisions": len(channel_signals["decisions"]),
        },
    }


async def process_notion_import(
    supabase_client,
    job: dict,
    integration: dict,
    mcp_manager,
    agent,
    token_manager,
) -> dict:
    """Process a Notion page import job."""
    from agents.integration.style_learning import StyleLearningAgent
    from services.ephemeral_context import store_notion_context

    user_id = job["user_id"]

    resource_id = job["resource_id"]
    instructions = job.get("instructions")

    # Check if style learning is requested (from job config)
    config = job.get("config") or {}
    learn_style = config.get("learn_style", False)

    # ADR-030: Get scope parameters
    scope = job.get("scope") or {}
    max_depth = scope.get("max_depth", 2)
    max_pages = scope.get("max_pages", 10)

    # Decrypt access token
    access_token = token_manager.decrypt(integration["access_token_encrypted"])

    # ADR-030: Update progress - fetching phase
    await update_job_progress(
        supabase_client,
        job["id"],
        progress=10,
        phase="fetching",
        items_total=1,
        items_completed=0,
        current_resource=resource_id,
    )

    # 1. Fetch page via MCP
    logger.info(f"[IMPORT] Fetching Notion page: {resource_id}")
    page_content = await mcp_manager.get_notion_page_content(
        user_id=user_id,
        page_id=resource_id,
        auth_token=access_token,
    )

    if not page_content:
        return {
            "blocks_created": 0,
            "items_processed": 0,
            "items_filtered": 0,
            "summary": "Page not found or empty",
            "style_learned": False,
        }

    resource_name = page_content.get("title", "Untitled")

    # ADR-030: Update progress - processing phase
    await update_job_progress(
        supabase_client,
        job["id"],
        progress=50,
        phase="processing",
        items_total=1,
        items_completed=0,
        current_resource=resource_name,
    )

    # 2. Run agent to extract context
    logger.info(f"[IMPORT] Processing page with agent: {resource_name}")
    import_result = await agent.import_notion_page(
        page_content=page_content,
        instructions=instructions,
    )

    # ADR-030: Update progress - storing phase
    await update_job_progress(
        supabase_client,
        job["id"],
        progress=75,
        phase="storing",
        items_total=len(import_result.blocks) if import_result.blocks else 0,
        items_completed=0,
        current_resource=resource_name,
    )

    # ADR-031: Store page content to ephemeral_context
    ephemeral_id = await store_notion_context(
        db_client=supabase_client,
        user_id=user_id,
        page_id=resource_id,
        page_title=resource_name,
        content=page_content.get("content", ""),
        metadata={
            "last_edited": page_content.get("last_edited"),
            "child_pages": len(page_content.get("child_pages", [])),
        },
    )
    logger.info(f"[IMPORT] Stored Notion page to ephemeral_context: {ephemeral_id}")

    # ADR-030: Update progress
    await update_job_progress(
        supabase_client,
        job["id"],
        progress=85,
        phase="storing",
        items_total=len(import_result.blocks) if import_result.blocks else 0,
        items_completed=0,
        current_resource=resource_name,
    )

    # 3. Store extracted blocks as memories (for long-term context)
    project_id = job.get("project_id")
    blocks_created = await store_memory_blocks(
        supabase_client,
        user_id=user_id,
        project_id=project_id,
        blocks=import_result.blocks,
        source_ref={
            "platform": "notion",
            "resource_id": resource_id,
            "resource_name": resource_name,
            "job_id": job["id"],
        },
    )

    # ADR-030: Update progress - nearly complete
    await update_job_progress(
        supabase_client,
        job["id"],
        progress=95,
        phase="storing",
        items_total=blocks_created,
        items_completed=blocks_created,
        current_resource=resource_name,
    )

    # 4. Optionally learn style from page content (Phase 5)
    style_learned = False
    style_confidence = None

    if learn_style and page_content.get("content"):
        try:
            logger.info(f"[STYLE] Learning documentation style from Notion page")
            style_agent = StyleLearningAgent()
            profile = await style_agent.analyze_notion_content(
                pages=[page_content],
                user_name=None,
            )

            style_learned = await store_style_memory(
                supabase_client,
                user_id=user_id,
                profile=profile,
                job_id=job["id"],
            )
            style_confidence = profile.confidence
        except Exception as e:
            logger.warning(f"[STYLE] Style learning failed (non-fatal): {e}")

    # ADR-030: Update coverage state
    await update_coverage_state(
        supabase_client,
        user_id=user_id,
        provider="notion",
        resource_id=resource_id,
        resource_name=resource_name,
        coverage_state="covered",  # Single page = covered
        scope=scope,
        items_extracted=1,  # Single page
        blocks_created=blocks_created,
    )

    return {
        "blocks_created": blocks_created,
        "ephemeral_stored": 1,  # ADR-031: Single page stored
        "items_processed": import_result.items_processed,
        "items_filtered": import_result.items_filtered,
        "summary": import_result.summary,
        "style_learned": style_learned,
        "style_confidence": style_confidence,
    }


async def process_gmail_import(
    supabase_client,
    job: dict,
    integration: dict,
    mcp_manager,
    agent,
    token_manager,
) -> dict:
    """
    Process a Gmail import job (ADR-029).

    Supports importing:
    - inbox: Recent messages from inbox
    - thread:<id>: Specific email thread
    - query:<query>: Messages matching Gmail search query
    """
    import os
    from agents.integration.style_learning import StyleLearningAgent
    from services.ephemeral_context import store_gmail_context_batch

    user_id = job["user_id"]
    metadata = integration.get("metadata", {}) or {}

    resource_id = job["resource_id"]  # "inbox", "thread:abc123", or "query:from:sarah"
    resource_name = job.get("resource_name", resource_id)
    instructions = job.get("instructions")

    # Check if style learning is requested
    config = job.get("config") or {}
    learn_style = config.get("learn_style", False)

    # ADR-030: Get scope parameters
    scope = job.get("scope") or {}
    recency_days = scope.get("recency_days", 7)
    max_items = scope.get("max_items", 100)

    # Get OAuth credentials
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError("Google OAuth not configured")

    # Decrypt refresh token
    refresh_token = token_manager.decrypt(integration["refresh_token_encrypted"])
    if not refresh_token:
        raise ValueError("Gmail integration missing refresh token")

    # Parse resource type
    if resource_id.startswith("thread:"):
        thread_id = resource_id.split(":", 1)[1]
        logger.info(f"[IMPORT] Fetching Gmail thread: {thread_id}")

        thread_data = await mcp_manager.get_gmail_thread(
            user_id=user_id,
            thread_id=thread_id,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
        )
        messages = thread_data.get("messages", [])

    else:
        # Default: list messages (inbox or query)
        # ADR-030: Build query with recency filter
        base_query = None
        if resource_id.startswith("query:"):
            base_query = resource_id.split(":", 1)[1]
        elif resource_id != "inbox":
            base_query = resource_id  # Treat as query

        # Add recency filter to query
        from datetime import timedelta
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=recency_days)
        date_filter = f"after:{cutoff_date.strftime('%Y/%m/%d')}"

        if base_query:
            query = f"{base_query} {date_filter}"
        else:
            query = date_filter

        logger.info(f"[IMPORT] Fetching Gmail messages: {query} (max: {max_items})")

        messages = await mcp_manager.list_gmail_messages(
            user_id=user_id,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            query=query,
            max_results=max_items,
        )

    if not messages:
        return {
            "blocks_created": 0,
            "items_processed": 0,
            "items_filtered": 0,
            "summary": "No messages found",
            "style_learned": False,
        }

    # Fetch full message content for each message
    # ADR-030: Respect max_items from scope (capped at 50 for performance)
    fetch_limit = min(max_items, 50)
    messages_to_fetch = messages[:fetch_limit]
    total_messages = len(messages_to_fetch)

    # ADR-030: Update progress - fetching phase
    await update_job_progress(
        supabase_client,
        job["id"],
        progress=10,
        phase="fetching",
        items_total=total_messages,
        items_completed=0,
        current_resource=resource_name,
    )

    full_messages = []
    for idx, msg in enumerate(messages_to_fetch):
        msg_id = msg.get("id")
        if msg_id:
            try:
                full_msg = await mcp_manager.get_gmail_message(
                    user_id=user_id,
                    message_id=msg_id,
                    client_id=client_id,
                    client_secret=client_secret,
                    refresh_token=refresh_token,
                )
                full_messages.append(full_msg)

                # Update progress every 5 messages or at the end
                if (idx + 1) % 5 == 0 or idx == total_messages - 1:
                    fetch_progress = 10 + int((idx + 1) / total_messages * 40)  # 10-50%
                    await update_job_progress(
                        supabase_client,
                        job["id"],
                        progress=fetch_progress,
                        phase="fetching",
                        items_total=total_messages,
                        items_completed=idx + 1,
                        current_resource=resource_name,
                    )
            except Exception as e:
                logger.warning(f"[IMPORT] Failed to fetch message {msg_id}: {e}")

    # ADR-030: Update progress - processing phase
    await update_job_progress(
        supabase_client,
        job["id"],
        progress=55,
        phase="processing",
        items_total=len(full_messages),
        items_completed=0,
        current_resource=resource_name,
    )

    # Run agent to extract context
    logger.info(f"[IMPORT] Processing {len(full_messages)} Gmail messages with agent")
    import_result = await agent.import_gmail_messages(
        messages=full_messages,
        source_name=resource_name,
        instructions=instructions,
    )

    # ADR-030: Update progress - storing phase
    await update_job_progress(
        supabase_client,
        job["id"],
        progress=75,
        phase="storing",
        items_total=len(import_result.blocks) if import_result.blocks else 0,
        items_completed=0,
        current_resource=resource_name,
    )

    # ADR-031: Store raw messages to ephemeral_context
    ephemeral_stored = await store_gmail_context_batch(
        db_client=supabase_client,
        user_id=user_id,
        label=resource_name,
        messages=full_messages,
    )
    logger.info(f"[IMPORT] Stored {ephemeral_stored} emails to ephemeral_context")

    # ADR-030: Update progress
    await update_job_progress(
        supabase_client,
        job["id"],
        progress=85,
        phase="storing",
        items_total=len(import_result.blocks) if import_result.blocks else 0,
        items_completed=0,
        current_resource=resource_name,
    )

    # Store extracted blocks as memories (for long-term context)
    project_id = job.get("project_id")
    blocks_created = await store_memory_blocks(
        supabase_client,
        user_id=user_id,
        project_id=project_id,
        blocks=import_result.blocks,
        source_ref={
            "platform": "gmail",
            "resource_id": resource_id,
            "resource_name": resource_name,
            "job_id": job["id"],
        },
    )

    # ADR-030: Update progress - nearly complete
    await update_job_progress(
        supabase_client,
        job["id"],
        progress=95,
        phase="storing",
        items_total=blocks_created,
        items_completed=blocks_created,
        current_resource=resource_name,
    )

    # Optionally learn style from email content
    style_learned = False
    style_confidence = None

    if learn_style and len(full_messages) >= 5:
        try:
            logger.info(f"[STYLE] Learning email style from {len(full_messages)} messages")
            style_agent = StyleLearningAgent()
            profile = await style_agent.analyze_email_messages(
                messages=full_messages,
                user_email=metadata.get("email"),
            )

            style_learned = await store_style_memory(
                supabase_client,
                user_id=user_id,
                profile=profile,
                job_id=job["id"],
            )
            style_confidence = profile.confidence
        except Exception as e:
            logger.warning(f"[STYLE] Style learning failed (non-fatal): {e}")

    # ADR-030: Update coverage state
    await update_coverage_state(
        supabase_client,
        user_id=user_id,
        provider="gmail",
        resource_id=resource_id,
        resource_name=resource_name,
        coverage_state="partial" if recency_days < 90 else "covered",
        scope=scope,
        items_extracted=len(full_messages),
        blocks_created=blocks_created,
    )

    return {
        "blocks_created": blocks_created,
        "ephemeral_stored": ephemeral_stored,  # ADR-031
        "items_processed": import_result.items_processed,
        "items_filtered": import_result.items_filtered,
        "summary": import_result.summary,
        "style_learned": style_learned,
        "style_confidence": style_confidence,
    }


async def process_import_job(supabase_client, job: dict) -> bool:
    """
    Process a single import job.

    Fetches data via MCP, runs agent, stores memories.
    Returns True if successful.
    """
    from integrations.core.client import get_mcp_manager
    from integrations.core.tokens import get_token_manager
    from agents.integration.context_import import ContextImportAgent

    job_id = job["id"]
    user_id = job["user_id"]
    provider = job["provider"]

    logger.info(f"[IMPORT] Processing job {job_id} ({provider})")

    # Mark as processing
    await update_job_status(supabase_client, job_id, "processing")

    try:
        # Get user's integration credentials
        integration = await get_user_integration(supabase_client, user_id, provider)

        if not integration:
            raise ValueError(f"No {provider} integration found for user")

        if integration.get("status") != "active":
            raise ValueError(f"{provider} integration is {integration.get('status')}, not active")

        # Initialize managers
        mcp_manager = get_mcp_manager()
        token_manager = get_token_manager()
        agent = ContextImportAgent()

        # Process based on platform
        if provider == "slack":
            result = await process_slack_import(
                supabase_client, job, integration, mcp_manager, agent, token_manager
            )
        elif provider == "notion":
            result = await process_notion_import(
                supabase_client, job, integration, mcp_manager, agent, token_manager
            )
        elif provider == "gmail":
            # ADR-029: Gmail import support
            result = await process_gmail_import(
                supabase_client, job, integration, mcp_manager, agent, token_manager
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        # Mark as completed
        await update_job_status(
            supabase_client,
            job_id,
            "completed",
            result=result,
        )

        logger.info(
            f"[IMPORT] ✓ Completed job {job_id}: "
            f"{result.get('blocks_created', 0)} blocks created, "
            f"{result.get('items_processed', 0)} items processed"
        )
        return True

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[IMPORT] ✗ Failed job {job_id}: {error_msg}")

        await update_job_status(
            supabase_client,
            job_id,
            "failed",
            error=error_msg,
        )
        return False
