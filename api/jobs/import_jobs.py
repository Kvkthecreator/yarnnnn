"""
YARNNN v5 - Integration Import Jobs

Processes context import jobs for Slack/Notion integrations.
Integrated into unified_scheduler.py to run every 5 minutes.

Flow:
1. Query pending import jobs
2. Fetch user's integration credentials
3. Fetch data via MCP (Slack channels, Notion pages)
4. Run ContextImportAgent to extract structured blocks
5. Store results in memories table with source_type='import'
6. Update job status

See ADR-027: Integration Read Architecture
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)


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
    user_id = job["user_id"]
    metadata = integration.get("metadata", {}) or {}

    resource_id = job["resource_id"]
    resource_name = job.get("resource_name", resource_id)
    instructions = job.get("instructions")

    # Decrypt access token
    access_token = token_manager.decrypt(integration["access_token_encrypted"])
    team_id = metadata.get("team_id")

    if not team_id:
        raise ValueError("Slack integration missing team_id")

    # 1. Fetch messages via MCP
    logger.info(f"[IMPORT] Fetching Slack channel: {resource_name}")
    messages = await mcp_manager.get_slack_channel_history(
        user_id=user_id,
        channel_id=resource_id,
        bot_token=access_token,
        team_id=team_id,
        limit=100,
    )

    if not messages:
        return {
            "blocks_created": 0,
            "items_processed": 0,
            "items_filtered": 0,
            "summary": "No messages found in channel",
        }

    # 2. Run agent to extract context
    logger.info(f"[IMPORT] Processing {len(messages)} messages with agent")
    import_result = await agent.import_slack_channel(
        messages=messages,
        channel_name=resource_name,
        instructions=instructions,
    )

    # 3. Store as memories
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

    return {
        "blocks_created": blocks_created,
        "items_processed": import_result.items_processed,
        "items_filtered": import_result.items_filtered,
        "summary": import_result.summary,
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
    user_id = job["user_id"]

    resource_id = job["resource_id"]
    instructions = job.get("instructions")

    # Decrypt access token
    access_token = token_manager.decrypt(integration["access_token_encrypted"])

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
        }

    resource_name = page_content.get("title", "Untitled")

    # 2. Run agent to extract context
    logger.info(f"[IMPORT] Processing page with agent: {resource_name}")
    import_result = await agent.import_notion_page(
        page_content=page_content,
        instructions=instructions,
    )

    # 3. Store as memories
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

    return {
        "blocks_created": blocks_created,
        "items_processed": import_result.items_processed,
        "items_filtered": import_result.items_filtered,
        "summary": import_result.summary,
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
