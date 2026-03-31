"""
Integration Routes

Manage third-party integrations (Slack, Notion, etc.) via MCP.
See ADR-026 for architectural decisions.

Endpoints:
- GET /integrations - List user's connected integrations
- GET /integrations/:provider - Get specific integration details
- DELETE /integrations/:provider - Disconnect an integration
- POST /integrations/:provider/export - Export content to provider
- GET /integrations/:provider/destinations - List available destinations
- GET /integrations/:provider/authorize - Initiate OAuth flow
- GET /integrations/:provider/callback - OAuth callback (redirect from provider)
"""

import logging
from typing import Optional, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from services.supabase import UserClient, get_service_client
from integrations.core.tokens import get_token_manager
from integrations.core.slack_client import get_slack_client
from integrations.core.oauth import (
    get_authorization_url,
    exchange_code_for_token,
    get_frontend_redirect_url,
    OAUTH_CONFIGS,
)
from integrations.core.types import (
    IntegrationProvider,
    IntegrationStatus,
    ExportStatus,
)
from agents.integration import ContextImportAgent

logger = logging.getLogger(__name__)

# =============================================================================
# Provider Alias Resolution
# =============================================================================
# ADR-131: Gmail and Calendar sunset — only Slack and Notion remain.
PROVIDER_ALIASES: dict[str, list[str]] = {
    "slack": ["slack"],
    "notion": ["notion"],
    "github": ["github"],  # ADR-147
}


# =============================================================================
# Background Import Processing
# =============================================================================

async def _process_import_job_background(job_id: str, job_data: dict):
    """
    Process an import job in the background.

    This runs as a FastAPI BackgroundTask, providing immediate feedback to users
    while processing happens asynchronously. The cron job serves as a safety net
    for any jobs that fail to start this way.

    Args:
        job_id: The import job ID
        job_data: The job data dict (as inserted into DB)
    """
    from jobs.import_jobs import process_import_job

    try:
        # Get service client for background processing
        service_client = get_service_client()

        # Fetch the full job record
        result = service_client.table("integration_import_jobs").select("*").eq(
            "id", job_id
        ).limit(1).execute()

        if not result.data:
            logger.error(f"[IMPORT_BG] Job {job_id} not found")
            return

        job = result.data[0]

        # Process the job
        logger.info(f"[IMPORT_BG] Starting background processing for job {job_id}")
        success = await process_import_job(service_client, job)

        if success:
            logger.info(f"[IMPORT_BG] ✓ Completed job {job_id}")
        else:
            logger.warning(f"[IMPORT_BG] ✗ Job {job_id} failed (check job status for details)")

    except Exception as e:
        logger.error(f"[IMPORT_BG] Unexpected error processing job {job_id}: {e}")
        # Try to mark job as failed
        try:
            service_client = get_service_client()
            service_client.table("integration_import_jobs").update({
                "status": "failed",
                "error_message": f"Background processing error: {str(e)}"
            }).eq("id", job_id).execute()
        except Exception:
            pass  # Best effort


# =============================================================================
# Notion Helper Functions
# =============================================================================

def _extract_notion_title(page: dict) -> str:
    """Extract title from Notion page object."""
    # Notion API returns title in properties.title or properties.Name
    props = page.get("properties", {})

    # Try common title property names
    for key in ["title", "Title", "Name", "name"]:
        if key in props:
            title_prop = props[key]
            if isinstance(title_prop, dict):
                # Handle rich text array format
                title_array = title_prop.get("title") or title_prop.get("rich_text", [])
                if isinstance(title_array, list) and title_array:
                    return title_array[0].get("plain_text", "Untitled")
            elif isinstance(title_prop, str):
                return title_prop

    return "Untitled"


def _extract_notion_parent_type(page: dict) -> str:
    """Extract parent type from Notion page object."""
    parent = page.get("parent", {})
    if "workspace" in parent:
        return "workspace"
    elif "page_id" in parent:
        return "page"
    elif "database_id" in parent:
        return "database"
    return "unknown"


router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================

class IntegrationResponse(BaseModel):
    """User-facing integration information."""
    id: str
    provider: str
    status: str
    workspace_name: Optional[str] = None
    last_used_at: Optional[datetime] = None
    created_at: datetime


class IntegrationListResponse(BaseModel):
    """List of user's integrations."""
    integrations: list[IntegrationResponse]


class ExportRequest(BaseModel):
    """Request to export content."""
    agent_run_id: str
    destination: dict[str, Any]  # Provider-specific (channel_id, page_id, etc.)


class ExportResponse(BaseModel):
    """Result of an export operation."""
    status: str
    external_id: Optional[str] = None
    external_url: Optional[str] = None
    error_message: Optional[str] = None


class DestinationResponse(BaseModel):
    """Available export destination."""
    id: str
    name: str
    type: str  # 'channel', 'page', 'database'
    metadata: dict[str, Any] = {}


class DestinationsListResponse(BaseModel):
    """List of available destinations."""
    destinations: list[DestinationResponse]


class SlackChannelResponse(BaseModel):
    """Slack channel info for resource discovery."""
    id: str
    name: str
    is_private: bool
    num_members: int
    topic: Optional[str] = None
    purpose: Optional[str] = None


class SlackChannelsListResponse(BaseModel):
    """List of Slack channels."""
    channels: list[SlackChannelResponse]


class NotionPageResponse(BaseModel):
    """Notion page info for resource discovery."""
    id: str
    title: str
    parent_type: str  # 'workspace', 'page', 'database'
    last_edited: Optional[str] = None
    url: Optional[str] = None


class NotionPagesListResponse(BaseModel):
    """List of Notion pages."""
    pages: list[NotionPageResponse]


# ADR-153: PlatformContentItem and PlatformContentResponse DELETED — platform_content sunset


# =============================================================================
# Import Job Models
# =============================================================================

class ImportConfigRequest(BaseModel):
    """Configuration options for import jobs."""
    learn_style: bool = False  # Extract communication style from content
    style_user_id: Optional[str] = None  # For Slack: filter to specific user's messages


class ImportScopeRequest(BaseModel):
    """
    ADR-030: Scope parameters for context extraction.
    """
    recency_days: int = 7  # How far back to go
    max_items: int = 100  # Maximum items to fetch
    include_threads: bool = True  # Slack: expand thread replies


class StartImportRequest(BaseModel):
    """Request to start a context import job."""
    resource_id: str  # channel_id or page_id
    resource_name: Optional[str] = None  # #channel-name or Page Title
    project_id: Optional[str] = None  # Optional project to associate
    instructions: Optional[str] = None  # User guidance for the agent
    config: Optional[ImportConfigRequest] = None  # Style learning and other options
    scope: Optional[ImportScopeRequest] = None  # ADR-030: Extraction scope


class ImportJobResultResponse(BaseModel):
    """Result details for a completed import job."""
    blocks_extracted: int = 0  # ADR-038: renamed from blocks_created (no longer stored to memories)
    content_stored: int = 0  # Legacy field — kept for API compat
    items_processed: int = 0
    items_filtered: int = 0
    summary: Optional[str] = None
    style_learned: bool = False
    style_confidence: Optional[str] = None  # high, medium, low


class ImportJobProgressDetails(BaseModel):
    """ADR-030: Progress details for real-time tracking."""
    phase: str  # fetching, processing, storing
    items_total: int = 0
    items_completed: int = 0
    current_resource: Optional[str] = None
    updated_at: Optional[str] = None


def _parse_import_result(result_dict: Optional[dict]) -> Optional[ImportJobResultResponse]:
    """Parse raw result dict from DB into typed response."""
    if not result_dict:
        return None
    return ImportJobResultResponse(
        # ADR-038: Support both old and new field names for backwards compatibility
        blocks_extracted=result_dict.get("blocks_extracted", result_dict.get("blocks_created", 0)),
        ephemeral_stored=result_dict.get("ephemeral_stored", 0),
        items_processed=result_dict.get("items_processed", 0),
        items_filtered=result_dict.get("items_filtered", 0),
        summary=result_dict.get("summary"),
        style_learned=result_dict.get("style_learned", False),
        style_confidence=result_dict.get("style_confidence"),
    )


def _parse_progress_details(progress_dict: Optional[dict]) -> Optional[ImportJobProgressDetails]:
    """Parse raw progress_details dict from DB into typed response."""
    if not progress_dict:
        return None
    return ImportJobProgressDetails(
        phase=progress_dict.get("phase", "processing"),
        items_total=progress_dict.get("items_total", 0),
        items_completed=progress_dict.get("items_completed", 0),
        current_resource=progress_dict.get("current_resource"),
        updated_at=progress_dict.get("updated_at"),
    )


class ImportJobResponse(BaseModel):
    """Status of an import job."""
    id: str
    provider: str
    resource_id: str
    resource_name: Optional[str] = None
    status: str  # pending, processing, completed, failed
    progress: int = 0
    progress_details: Optional[ImportJobProgressDetails] = None  # ADR-030
    result: Optional[ImportJobResultResponse] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ImportJobsListResponse(BaseModel):
    """List of import jobs."""
    jobs: list[ImportJobResponse]


# =============================================================================
# List Integrations
# =============================================================================

@router.get("/integrations")
async def list_integrations(auth: UserClient) -> IntegrationListResponse:
    """
    List all of user's connected integrations.
    Returns only active integrations with sanitized data (no tokens).
    """
    user_id = auth.user_id

    try:
        result = auth.client.table("platform_connections").select(
            "id, platform, status, metadata, created_at"
        ).eq("user_id", user_id).execute()

        # Derive last_used_at from sync_registry (source of truth)
        registry_result = auth.client.table("sync_registry").select(
            "platform, last_synced_at"
        ).eq("user_id", user_id).execute()
        max_synced: dict[str, str] = {}
        for reg in (registry_result.data or []):
            p = reg.get("platform", "")
            ts = reg.get("last_synced_at")
            if ts and (p not in max_synced or ts > max_synced[p]):
                max_synced[p] = ts

        integrations = []
        for row in result.data or []:
            metadata = row.get("metadata", {}) or {}
            platform = row["platform"]
            integrations.append(IntegrationResponse(
                id=row["id"],
                provider=platform,  # ADR-058: DB column is 'platform'
                status=row["status"],
                workspace_name=metadata.get("workspace_name"),
                last_used_at=max_synced.get(platform),
                created_at=row["created_at"]
            ))

        return IntegrationListResponse(integrations=integrations)

    except Exception as e:
        logger.error(f"[INTEGRATIONS] Failed to list integrations for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list integrations")


# =============================================================================
# Integration Summary (ADR-033: Dashboard Platform Cards)
# IMPORTANT: Must be defined BEFORE /{provider} route to avoid path collision
# =============================================================================

class PlatformSummary(BaseModel):
    """Summary of a single platform integration for Dashboard cards."""
    provider: str
    status: str  # active, error, expired
    workspace_name: Optional[str] = None
    connected_at: datetime
    resource_count: int = 0
    resource_type: str = ""  # channels, labels, pages
    agent_count: int = 0
    activity_7d: int = 0  # messages/emails/updates in last 7 days


class IntegrationsSummaryResponse(BaseModel):
    """
    ADR-033: Summary of all integrations for Dashboard platform cards.

    Provides aggregated stats for each connected platform:
    - Connection status
    - Resource counts (channels, labels, pages)
    - Agent counts targeting this platform
    - Recent activity from ephemeral context
    """
    platforms: list[PlatformSummary]
    total_agents: int = 0


@router.get("/integrations/summary")
async def get_integrations_summary(auth: UserClient) -> IntegrationsSummaryResponse:
    """
    Get summary of all integrations for Dashboard platform cards.

    ADR-033 Phase 1: Returns aggregated stats for each connected platform
    to power the Dashboard's forest view.
    """
    user_id = auth.user_id

    try:
        # Get all integrations
        integrations_result = auth.client.table("platform_connections").select(
            "id, platform, status, metadata, landscape, created_at"
        ).eq("user_id", user_id).execute()

        if not integrations_result.data:
            return IntegrationsSummaryResponse(platforms=[], total_agents=0)

        platforms: list[PlatformSummary] = []
        from datetime import timedelta
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()

        # ADR-131: Only Slack and Notion remain — no Google/Gmail alias resolution needed
        def _is_active(row: dict[str, Any]) -> bool:
            return row.get("status") == IntegrationStatus.ACTIVE.value

        def _pick_preferred(existing: Optional[dict[str, Any]], candidate: dict[str, Any]) -> dict[str, Any]:
            if not existing:
                return candidate
            if _is_active(candidate) and not _is_active(existing):
                return candidate
            if _is_active(candidate) == _is_active(existing):
                if str(candidate.get("created_at") or "") >= str(existing.get("created_at") or ""):
                    return candidate
            return existing

        canonical_integrations: dict[str, dict[str, Any]] = {}
        for integration in integrations_result.data:
            provider = integration["platform"]
            if provider not in {"slack", "notion"}:
                continue
            canonical_integrations[provider] = _pick_preferred(
                canonical_integrations.get(provider),
                integration,
            )

        def _count_agents(provider: str) -> int:
            # ADR-138: destination column dropped. Count all active agents instead.
            # Task-level delivery config will be in TASK.md (Phase 3+).
            result = auth.client.table("agents").select(
                "id", count="exact"
            ).eq("user_id", user_id).neq(
                "status", "archived"
            ).execute()
            return result.count or 0

        def _count_activity(provider: str) -> int:
            # ADR-153: platform_content sunset — return 0, activity tracked via tasks now
            return 0

        def _resource_count_for(provider: str, integration: dict[str, Any]) -> int:
            landscape = integration.get("landscape", {}) or {}
            selected_sources = landscape.get("selected_sources", []) or []
            resources = landscape.get("resources", []) or []
            return len(selected_sources) if selected_sources else len(resources)

        def _to_summary(provider: str, integration: dict[str, Any]) -> PlatformSummary:
            metadata = integration.get("metadata", {}) or {}
            resource_type = {
                "slack": "channels",
                "notion": "pages",
            }.get(provider, "resources")

            return PlatformSummary(
                provider=provider,
                status=integration["status"],
                workspace_name=metadata.get("workspace_name"),
                connected_at=integration["created_at"],
                resource_count=_resource_count_for(provider, integration),
                resource_type=resource_type,
                agent_count=_count_agents(provider),
                activity_7d=_count_activity(provider),
            )

        # Emit platform summaries in stable order (ADR-131: Slack + Notion only)
        for provider in ("slack", "notion"):
            integration = canonical_integrations.get(provider)
            if integration:
                platforms.append(_to_summary(provider, integration))

        # Total agents count
        total_result = auth.client.table("agents").select(
            "id", count="exact"
        ).eq("user_id", user_id).execute()
        total_agents = total_result.count or 0

        return IntegrationsSummaryResponse(
            platforms=platforms,
            total_agents=total_agents
        )

    except Exception as e:
        logger.error(f"[INTEGRATIONS] Failed to get summary for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get integrations summary")


# =============================================================================
# Import Jobs - List (must be before /{provider} to avoid route collision)
# =============================================================================

@router.get("/integrations/import")
async def list_import_jobs(
    auth: UserClient,
    status: Optional[str] = Query(None, description="Filter by status"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    limit: int = Query(20, le=100)
) -> ImportJobsListResponse:
    """
    List user's import jobs.

    Note: This route must be defined before /integrations/{provider} to avoid
    FastAPI matching '/integrations/import' as provider='import'.
    """
    user_id = auth.user_id

    try:
        query = auth.client.table("integration_import_jobs").select(
            "*"
        ).eq("user_id", user_id).order("created_at", desc=True).limit(limit)

        if status:
            query = query.eq("status", status)
        if provider:
            query = query.eq("platform", provider)

        result = query.execute()

        jobs = [
            ImportJobResponse(
                id=job["id"],
                provider=job["provider"],
                resource_id=job["resource_id"],
                resource_name=job.get("resource_name"),
                status=job["status"],
                progress=job.get("progress", 0),
                progress_details=_parse_progress_details(job.get("progress_details")),  # ADR-030
                result=_parse_import_result(job.get("result")),
                error_message=job.get("error_message"),
                created_at=job["created_at"],
                started_at=job.get("started_at"),
                completed_at=job.get("completed_at"),
            )
            for job in (result.data or [])
        ]

        return ImportJobsListResponse(jobs=jobs)

    except Exception as e:
        logger.error(f"[INTEGRATIONS] Failed to list import jobs for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list import jobs")


@router.get("/integrations/import/{job_id}")
async def get_import_job(
    job_id: str,
    auth: UserClient
) -> ImportJobResponse:
    """
    Get status of an import job.
    """
    user_id = auth.user_id

    try:
        result = auth.client.table("integration_import_jobs").select(
            "*"
        ).eq("id", job_id).eq("user_id", user_id).limit(1).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Import job not found")

        job = result.data[0]

        return ImportJobResponse(
            id=job["id"],
            provider=job["provider"],
            resource_id=job["resource_id"],
            resource_name=job.get("resource_name"),
            status=job["status"],
            progress=job.get("progress", 0),
            progress_details=_parse_progress_details(job.get("progress_details")),  # ADR-030
            result=_parse_import_result(job.get("result")),
            error_message=job.get("error_message"),
            created_at=job["created_at"],
            started_at=job.get("started_at"),
            completed_at=job.get("completed_at"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTEGRATIONS] Failed to get import job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get import job")


# =============================================================================
# Export History
# NOTE: This must be before /integrations/{provider} to avoid path parameter matching
# =============================================================================

@router.get("/integrations/history")
async def get_export_history(
    auth: UserClient,
    agent_id: Optional[str] = None,
    limit: int = 20
) -> dict:
    """
    Get export history for the user.
    Optionally filter by agent.
    """
    user_id = auth.user_id

    try:
        query = auth.client.table("export_log").select(
            "id, provider, status, external_url, created_at, "
            "agent_run_id"
        ).eq("user_id", user_id).order("created_at", desc=True).limit(limit)

        if agent_id:
            # Filter by agent (need to join through versions)
            versions = auth.client.table("agent_runs").select(
                "id"
            ).eq("agent_id", agent_id).execute()

            if versions.data:
                version_ids = [v["id"] for v in versions.data]
                query = query.in_("agent_run_id", version_ids)

        result = query.execute()

        return {
            "exports": result.data or [],
            "total": len(result.data or [])
        }

    except Exception as e:
        logger.error(f"[INTEGRATIONS] Failed to get history for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get export history")


# =============================================================================
# Get Specific Integration
# =============================================================================

@router.get("/integrations/{provider}")
async def get_integration(
    provider: str,
    auth: UserClient
) -> IntegrationResponse:
    """
    Get details for a specific integration.
    """
    user_id = auth.user_id

    providers_to_try = PROVIDER_ALIASES.get(provider, [provider])

    try:
        row = None
        for p in providers_to_try:
            result = auth.client.table("platform_connections").select(
                "id, platform, status, metadata, created_at"
            ).eq("user_id", user_id).eq("platform", p).execute()
            if result.data:
                row = result.data[0]
                break

        if not row:
            raise HTTPException(status_code=404, detail=f"Integration not found: {provider}")

        metadata = row.get("metadata", {}) or {}
        platform = row["platform"]

        # Derive last_used_at from sync_registry (source of truth)
        from services.freshness import get_platform_freshness_from_registry
        last_synced = await get_platform_freshness_from_registry(
            auth.client, user_id, platform
        )

        return IntegrationResponse(
            id=row["id"],
            provider=platform,  # ADR-058: DB column is 'platform'
            status=row["status"],
            workspace_name=metadata.get("workspace_name"),
            last_used_at=last_synced,
            created_at=row["created_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTEGRATIONS] Failed to get {provider} for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get integration")


# =============================================================================
# Integration Health Check - ADR-047
# =============================================================================

class IntegrationHealthResponse(BaseModel):
    """Health status of an integration."""
    provider: str
    status: str  # healthy, degraded, unhealthy, unknown
    validated_at: Optional[str] = None
    capabilities: dict[str, Any] = {}
    quirks_discovered: list[str] = []
    errors: list[str] = []
    recommendations: list[str] = []


@router.get("/integrations/{provider}/health")
async def check_integration_health(
    provider: str,
    auth: UserClient,
    validate: bool = Query(False, description="Run full validation (slower)")
) -> IntegrationHealthResponse:
    """
    Check health of a platform integration.

    ADR-047: Platform Integration Validation

    Quick check (default): Verifies integration exists and is active
    Full validation (validate=true): Runs capability tests

    Returns:
        Health status with capability details and recommendations
    """
    from integrations.validation import validate_integration
    from integrations.platform_registry import get_platform_config

    user_id = auth.user_id
    providers_to_try = PROVIDER_ALIASES.get(provider, [provider])

    # Check if integration exists (try all alias candidates)
    integration = None
    for p in providers_to_try:
        result = auth.client.table("platform_connections").select(
            "id, status, metadata, updated_at"
        ).eq("user_id", user_id).eq("platform", p).limit(1).execute()
        if result.data:
            integration = result.data[0]
            break

    if not integration:
        return IntegrationHealthResponse(
            provider=provider,
            status="unhealthy",
            errors=[f"No {provider} integration found. Connect it first."],
            recommendations=[f"Go to System → Integrations → Connect {provider}"]
        )

    if integration.get("status") != "active":
        return IntegrationHealthResponse(
            provider=provider,
            status="unhealthy",
            errors=[f"Integration status is '{integration.get('status')}', expected 'active'"],
            recommendations=["Reconnect the integration"]
        )

    # Quick check - just verify basic status
    if not validate:
        config = get_platform_config(provider)
        return IntegrationHealthResponse(
            provider=provider,
            status="healthy",
            validated_at=integration.get("updated_at"),
            quirks_discovered=config.get("quirks", []) if config else [],
            recommendations=["Run with ?validate=true for full capability check"]
        )

    # Full validation
    try:
        health = await validate_integration(auth, provider)
        return IntegrationHealthResponse(**health.to_dict())

    except Exception as e:
        logger.error(f"[INTEGRATIONS] Health check failed for {provider}: {e}")
        return IntegrationHealthResponse(
            provider=provider,
            status="unknown",
            errors=[f"Validation error: {str(e)}"]
        )


# =============================================================================
# Disconnect Integration
# =============================================================================

@router.delete("/integrations/{provider}")
async def disconnect_integration(
    provider: str,
    auth: UserClient
) -> dict:
    """
    Disconnect an integration.
    Deletes stored tokens and export preferences.
    """
    user_id = auth.user_id
    providers_to_try = PROVIDER_ALIASES.get(provider, [provider])

    try:
        result_data = None
        for p in providers_to_try:
            result = auth.client.table("platform_connections").delete().eq(
                "user_id", user_id
            ).eq("platform", p).execute()
            if result.data:
                if result_data is None:
                    result_data = []
                result_data.extend(result.data)

        if not result_data:
            raise HTTPException(status_code=404, detail=f"Integration not found: {provider}")

        logger.info(f"[INTEGRATIONS] User {user_id} disconnected {provider}")

        # Activity log: record integration disconnection (ADR-063)
        try:
            from services.activity_log import write_activity
            import asyncio
            asyncio.create_task(write_activity(
                client=get_service_client(),
                user_id=user_id,
                event_type="integration_disconnected",
                summary=f"Disconnected {provider.title()}",
                metadata={"provider": provider},
            ))
        except Exception:
            pass  # Non-fatal

        return {"success": True, "message": f"Disconnected {provider}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTEGRATIONS] Failed to disconnect {provider} for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to disconnect integration")


# =============================================================================
# Export to Provider
# =============================================================================

@router.post("/integrations/{provider}/export")
async def export_to_provider(
    provider: str,
    request: ExportRequest,
    auth: UserClient
) -> ExportResponse:
    """
    Export an agent version to a provider.

    ADR-028: Uses the unified DestinationExporter infrastructure.

    The destination format depends on the provider:
    - Slack: { "channel_id": "C123..." } or { "target": "C123..." }
    - Notion: { "page_id": "..." } or { "target": "..." }
    - Download: {} (no destination needed)
    """
    from integrations.exporters import get_exporter_registry, ExporterContext

    user_id = auth.user_id
    providers_to_try = PROVIDER_ALIASES.get(provider, [provider])
    registry = get_exporter_registry()

    # Get exporter for this platform
    exporter = registry.get(provider)
    if not exporter:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider: {provider}. Available: {registry.list_platforms()}"
        )

    try:
        # 1. Get auth context if needed
        context = None
        integration_id = None

        if exporter.requires_auth:
            integration_row = None
            for p in providers_to_try:
                _result = auth.client.table("platform_connections").select(
                    "id, credentials_encrypted, refresh_token_encrypted, metadata, status"
                ).eq("user_id", user_id).eq("platform", p).limit(1).execute()
                if _result.data:
                    integration_row = _result.data[0]
                    break

            if not integration_row:
                raise HTTPException(
                    status_code=404,
                    detail=f"No {provider} integration found. Please connect first."
                )

            if integration_row["status"] != IntegrationStatus.ACTIVE.value:
                raise HTTPException(
                    status_code=400,
                    detail=f"{provider} integration is {integration_row['status']}. Please reconnect."
                )

            integration_id = integration_row["id"]
            token_manager = get_token_manager()

            # Decrypt tokens
            access_token = token_manager.decrypt(integration_row["credentials_encrypted"])
            refresh_token = token_manager.decrypt(integration_row["refresh_token_encrypted"]) if integration_row.get("refresh_token_encrypted") else None

            metadata = integration_row.get("metadata", {}) or {}

            context = ExporterContext(
                user_id=user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                metadata=metadata
            )
        else:
            # Non-auth exporters (download)
            context = ExporterContext(
                user_id=user_id,
                access_token="",
                metadata={}
            )

        # 2. Get agent version content
        version = auth.client.table("agent_runs").select(
            "id, final_content, draft_content, agent_id"
        ).eq("id", request.agent_run_id).limit(1).execute()

        if not version.data:
            raise HTTPException(status_code=404, detail="Agent version not found")

        # Get agent title
        agent = auth.client.table("agents").select(
            "title"
        ).eq("id", version.data[0]["agent_id"]).limit(1).execute()

        content = version.data[0].get("final_content") or version.data[0].get("draft_content", "")
        title = agent.data[0]["title"] if agent.data else "YARNNN Export"

        # 3. Normalize destination format for exporters
        # Support both legacy format (channel_id, page_id) and new format (target)
        destination = _normalize_destination(provider, request.destination)

        # Validate destination
        if not exporter.validate_destination(destination):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid destination for {provider}"
            )

        # 4. Deliver via exporter
        result = await exporter.deliver(
            destination=destination,
            content=content,
            title=title,
            metadata={
                "agent_run_id": request.agent_run_id,
                "agent_id": version.data[0]["agent_id"]
            },
            context=context
        )

        # 5. Log the export
        log_entry = {
            "agent_run_id": request.agent_run_id,
            "user_id": user_id,
            "provider": provider,
            "destination": destination,
            "status": result.status.value,
            "error_message": result.error_message,
            "external_id": result.external_id,
            "external_url": result.external_url,
            "completed_at": datetime.utcnow().isoformat() if result.status == ExportStatus.SUCCESS else None
        }
        auth.client.table("export_log").insert(log_entry).execute()

        # 6. Update last_synced_at for auth integrations (ADR-058: column renamed)
        if integration_id:
            auth.client.table("platform_connections").update({
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", integration_id).execute()

        logger.info(f"[INTEGRATIONS] User {user_id} exported to {provider}: {result.status.value}")

        return ExportResponse(
            status=result.status.value,
            external_id=result.external_id,
            external_url=result.external_url,
            error_message=result.error_message
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTEGRATIONS] Export to {provider} failed for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


def _normalize_destination(provider: str, destination: dict[str, Any]) -> dict[str, Any]:
    """
    Validate and normalize destination format (ADR-028).

    Expected format: { "platform": "slack", "target": "C123", "format": "message" }
    """
    if "platform" not in destination or "target" not in destination:
        raise ValueError("Destination must include 'platform' and 'target' fields")

    return {
        "platform": destination["platform"],
        "target": destination["target"],
        "format": destination.get("format", "default"),
        "options": destination.get("options", {})
    }


# =============================================================================
# Resource Discovery - Slack Channels
# =============================================================================

@router.get("/integrations/slack/channels")
async def list_slack_channels(
    auth: UserClient
) -> SlackChannelsListResponse:
    """
    List Slack channels the bot can access.

    Used for:
    - Export destination picker
    - Context import source selection
    """
    user_id = auth.user_id

    try:
        # Get user's Slack integration
        integration = auth.client.table("platform_connections").select(
            "id, credentials_encrypted, status"
        ).eq("user_id", user_id).eq("platform", "slack").limit(1).execute()

        if not integration.data:
            raise HTTPException(
                status_code=404,
                detail="No Slack integration found. Please connect first."
            )

        if integration.data[0]["status"] != IntegrationStatus.ACTIVE.value:
            raise HTTPException(
                status_code=400,
                detail=f"Slack integration is {integration.data[0]['status']}. Please reconnect."
            )

        # Get integration metadata for team_id
        integration_full = auth.client.table("platform_connections").select(
            "metadata"
        ).eq("user_id", user_id).eq("platform", "slack").limit(1).execute()

        metadata = integration_full.data[0].get("metadata", {}) or {}
        team_id = metadata.get("team_id")
        if not team_id:
            raise HTTPException(status_code=400, detail="Slack integration missing team_id")

        # Decrypt access token
        token_manager = get_token_manager()
        access_token = token_manager.decrypt(integration.data[0]["credentials_encrypted"])

        # Fetch channels via Direct API
        slack_client = get_slack_client()
        raw_channels = await slack_client.list_channels(bot_token=access_token)

        # Transform to response format
        channels = [
            SlackChannelResponse(
                id=ch.get("id", ""),
                name=ch.get("name", ""),
                is_private=ch.get("is_private", False),
                num_members=ch.get("num_members", 0),
                topic=ch.get("topic", {}).get("value") if isinstance(ch.get("topic"), dict) else None,
                purpose=ch.get("purpose", {}).get("value") if isinstance(ch.get("purpose"), dict) else None,
            )
            for ch in raw_channels
        ]

        logger.info(f"[INTEGRATIONS] User {user_id} listed {len(channels)} Slack channels via MCP")

        return SlackChannelsListResponse(channels=channels)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTEGRATIONS] Failed to list Slack channels for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list channels: {str(e)}")


# =============================================================================
# Resource Discovery - Notion Pages
# =============================================================================

@router.get("/integrations/notion/pages")
async def list_notion_pages(
    auth: UserClient,
    query: Optional[str] = Query(None, description="Search query to filter pages")
) -> NotionPagesListResponse:
    """
    List Notion pages the integration can access.

    Used for:
    - Export destination picker
    - Context import source selection
    """
    user_id = auth.user_id

    try:
        # Get user's Notion integration
        integration = auth.client.table("platform_connections").select(
            "id, credentials_encrypted, status"
        ).eq("user_id", user_id).eq("platform", "notion").limit(1).execute()

        if not integration.data:
            raise HTTPException(
                status_code=404,
                detail="No Notion integration found. Please connect first."
            )

        if integration.data[0]["status"] != IntegrationStatus.ACTIVE.value:
            raise HTTPException(
                status_code=400,
                detail=f"Notion integration is {integration.data[0]['status']}. Please reconnect."
            )

        # Decrypt access token
        token_manager = get_token_manager()
        access_token = token_manager.decrypt(integration.data[0]["credentials_encrypted"])

        # ADR-076: Fetch pages via Direct API
        from integrations.core.notion_client import get_notion_client

        notion_client = get_notion_client()
        raw_pages = await notion_client.search(
            access_token=access_token,
            query=query or "",
        )
        if not isinstance(raw_pages, list):
            raw_pages = []

        pages = [
            NotionPageResponse(
                id=page.get("id", ""),
                title=_extract_notion_title(page),
                parent_type=_extract_notion_parent_type(page),
                last_edited=page.get("last_edited_time"),
                url=page.get("url"),
            )
            for page in raw_pages
            if page.get("object") == "page"  # Filter to pages only
        ]

        logger.info(f"[INTEGRATIONS] User {user_id} listed {len(pages)} Notion pages")

        return NotionPagesListResponse(pages=pages)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTEGRATIONS] Failed to list Notion pages for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list pages: {str(e)}")


# =============================================================================
# Notion Designated Page (ADR-050 Streamlined Pattern)
# =============================================================================

class DesignatedPageRequest(BaseModel):
    """Request to set designated output page for Notion."""
    page_id: str
    page_name: Optional[str] = None


class DesignatedPageResponse(BaseModel):
    """Response after setting designated page."""
    success: bool
    designated_page_id: Optional[str] = None
    designated_page_name: Optional[str] = None
    message: str


@router.get("/integrations/notion/designated-page")
async def get_notion_designated_page(auth: UserClient) -> DesignatedPageResponse:
    """
    Get the user's designated output page for Notion.

    ADR-050: Streamlined pattern - user designates a page as their
    "YARNNN inbox" where TP can write outputs (like Slack DM to self).
    """
    user_id = auth.user_id

    try:
        integration = auth.client.table("platform_connections").select(
            "id, metadata, status"
        ).eq("user_id", user_id).eq("platform", "notion").limit(1).execute()

        if not integration.data:
            raise HTTPException(
                status_code=404,
                detail="No Notion integration found. Please connect first."
            )

        metadata = integration.data[0].get("metadata") or {}
        designated_page_id = metadata.get("designated_page_id")
        designated_page_name = metadata.get("designated_page_name")

        if designated_page_id:
            return DesignatedPageResponse(
                success=True,
                designated_page_id=designated_page_id,
                designated_page_name=designated_page_name,
                message="Designated page is set"
            )
        else:
            return DesignatedPageResponse(
                success=True,
                designated_page_id=None,
                designated_page_name=None,
                message="No designated page set"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTEGRATIONS] Failed to get Notion designated page for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get designated page: {str(e)}")


@router.put("/integrations/notion/designated-page")
async def set_notion_designated_page(
    request: DesignatedPageRequest,
    auth: UserClient
) -> DesignatedPageResponse:
    """
    Set the user's designated output page for Notion.

    ADR-050: Streamlined pattern - TP will use this page as the default
    parent for creating new pages or adding comments.
    """
    user_id = auth.user_id

    try:
        # Get current integration
        integration = auth.client.table("platform_connections").select(
            "id, metadata, status"
        ).eq("user_id", user_id).eq("platform", "notion").limit(1).execute()

        if not integration.data:
            raise HTTPException(
                status_code=404,
                detail="No Notion integration found. Please connect first."
            )

        if integration.data[0]["status"] != IntegrationStatus.ACTIVE.value:
            raise HTTPException(
                status_code=400,
                detail=f"Notion integration is {integration.data[0]['status']}. Please reconnect."
            )

        # Update metadata with designated page
        metadata = integration.data[0].get("metadata") or {}
        metadata["designated_page_id"] = request.page_id
        if request.page_name:
            metadata["designated_page_name"] = request.page_name

        auth.client.table("platform_connections").update({
            "metadata": metadata
        }).eq("id", integration.data[0]["id"]).execute()

        logger.info(f"[INTEGRATIONS] User {user_id} set Notion designated page: {request.page_id}")

        return DesignatedPageResponse(
            success=True,
            designated_page_id=request.page_id,
            designated_page_name=request.page_name,
            message="Designated page updated"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTEGRATIONS] Failed to set Notion designated page for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set designated page: {str(e)}")


@router.delete("/integrations/notion/designated-page")
async def clear_notion_designated_page(auth: UserClient) -> DesignatedPageResponse:
    """
    Clear the user's designated output page for Notion.
    """
    user_id = auth.user_id

    try:
        integration = auth.client.table("platform_connections").select(
            "id, metadata"
        ).eq("user_id", user_id).eq("platform", "notion").limit(1).execute()

        if not integration.data:
            raise HTTPException(
                status_code=404,
                detail="No Notion integration found."
            )

        # Remove designated page from metadata
        metadata = integration.data[0].get("metadata") or {}
        metadata.pop("designated_page_id", None)
        metadata.pop("designated_page_name", None)

        auth.client.table("platform_connections").update({
            "metadata": metadata
        }).eq("id", integration.data[0]["id"]).execute()

        logger.info(f"[INTEGRATIONS] User {user_id} cleared Notion designated page")

        return DesignatedPageResponse(
            success=True,
            designated_page_id=None,
            designated_page_name=None,
            message="Designated page cleared"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTEGRATIONS] Failed to clear Notion designated page for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear designated page: {str(e)}")


    # ADR-131: Google designated settings routes removed (Gmail/Calendar sunset)



# ADR-131: Google designated-settings, calendar, events, and Gmail import routes removed

@router.post("/integrations/notion/import")
async def start_notion_import(
    request: StartImportRequest,
    auth: UserClient,
    background_tasks: BackgroundTasks
) -> ImportJobResponse:
    """
    Start a context import from a Notion page.

    Creates a background job that:
    1. Fetches page content (including child pages)
    2. Runs ContextImportAgent to extract structured context
    3. Stores results as context_sources

    The job runs async; poll GET /integrations/import/{job_id} for status.
    """
    user_id = auth.user_id

    try:
        # Get user's Notion integration
        integration = auth.client.table("platform_connections").select(
            "id, credentials_encrypted, status"
        ).eq("user_id", user_id).eq("platform", "notion").limit(1).execute()

        if not integration.data:
            raise HTTPException(
                status_code=404,
                detail="No Notion integration found. Please connect first."
            )

        if integration.data[0]["status"] != IntegrationStatus.ACTIVE.value:
            raise HTTPException(
                status_code=400,
                detail=f"Notion integration is {integration.data[0]['status']}. Please reconnect."
            )

        # Use resource_name if provided, otherwise use resource_id as fallback
        # (Background job processor will resolve the actual page title via MCP)
        resource_name = request.resource_name or request.resource_id

        # Build config dict from request
        config_dict = {}
        if request.config:
            config_dict["learn_style"] = request.config.learn_style
            # style_user_id not applicable for Notion (no per-user filtering)

        # ADR-030: Build scope dict with defaults (Notion-specific params)
        scope_dict = {
            "max_depth": 2,  # How deep to traverse child pages
            "max_pages": 10  # Maximum pages to extract
        }
        if request.scope:
            # Notion reuses max_items as max_pages
            scope_dict["max_pages"] = request.scope.max_items

        # Create import job
        job_data = {
            "user_id": user_id,
            "provider": "notion",
            "resource_id": request.resource_id,
            "resource_name": resource_name,
            # project_id removed - ADR-058: column no longer exists in table
            "instructions": request.instructions,
            "config": config_dict if config_dict else None,
            "scope": scope_dict,  # ADR-030
            "status": "pending",
            "progress": 0,
        }

        result = auth.client.table("integration_import_jobs").insert(job_data).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create import job")

        job = result.data[0]

        style_note = " (with style learning)" if config_dict.get("learn_style") else ""
        logger.info(f"[INTEGRATIONS] User {user_id} started Notion import job {job['id']}{style_note}")

        # Trigger background processing immediately
        background_tasks.add_task(_process_import_job_background, job["id"], job_data)

        return ImportJobResponse(
            id=job["id"],
            provider="notion",
            resource_id=job["resource_id"],
            resource_name=job.get("resource_name"),
            status=job["status"],
            progress=job.get("progress", 0),
            created_at=job["created_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTEGRATIONS] Failed to start Notion import for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start import: {str(e)}")


# =============================================================================
# List Destinations (Legacy/Generic)
# =============================================================================

@router.get("/integrations/{provider}/destinations")
async def list_destinations(
    provider: str,
    auth: UserClient
) -> DestinationsListResponse:
    """
    List available export destinations for a provider.

    DEPRECATED: Use provider-specific endpoints instead:
    - GET /integrations/slack/channels
    - GET /integrations/notion/pages
    """
    user_id = auth.user_id

    # Redirect to provider-specific endpoints
    if provider == "slack":
        result = await list_slack_channels(auth)
        return DestinationsListResponse(
            destinations=[
                DestinationResponse(
                    id=ch.id,
                    name=f"#{ch.name}",
                    type="channel",
                    metadata={"is_private": ch.is_private, "num_members": ch.num_members}
                )
                for ch in result.channels
            ]
        )
    elif provider == "notion":
        result = await list_notion_pages(auth)
        return DestinationsListResponse(
            destinations=[
                DestinationResponse(
                    id=p.id,
                    name=p.title,
                    type="page",
                    metadata={"parent_type": p.parent_type, "url": p.url}
                )
                for p in result.pages
            ]
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")


# =============================================================================
# OAuth Flow - Initiate
# =============================================================================

@router.get("/integrations/{provider}/authorize")
async def initiate_oauth(
    provider: str,
    auth: UserClient,
    redirect_to: Optional[str] = Query(None, description="Frontend path to return to after OAuth (e.g. /system)"),
) -> dict:
    """
    Initiate OAuth flow for a provider.

    Returns the authorization URL to redirect the user to.
    The frontend should open this URL in a popup or redirect.

    Pass redirect_to to control where the user lands after OAuth completes.
    Defaults to /dashboard (ADR-110 bootstrap flow).
    """
    user_id = auth.user_id

    # Check if provider is supported
    if provider not in OAUTH_CONFIGS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    config = OAUTH_CONFIGS[provider]
    if not config.is_configured:
        raise HTTPException(
            status_code=503,
            detail=f"{provider} OAuth not configured. Missing credentials."
        )

    try:
        auth_url = get_authorization_url(provider, user_id, redirect_to=redirect_to)
        logger.info(f"[INTEGRATIONS] User {user_id} initiating {provider} OAuth")
        return {"authorization_url": auth_url}

    except Exception as e:
        logger.error(f"[INTEGRATIONS] OAuth initiation failed for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# OAuth Flow - Callback
# =============================================================================

@router.get("/integrations/{provider}/callback")
async def oauth_callback(
    provider: str,
    background_tasks: BackgroundTasks,
    code: str = Query(..., description="Authorization code from provider"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    error: Optional[str] = Query(None, description="Error from provider"),
    error_description: Optional[str] = Query(None),
) -> RedirectResponse:
    """
    OAuth callback endpoint.

    This is called by the provider (Slack, Notion) after user authorizes.
    Exchanges the code for tokens, stores them, and redirects to frontend.
    """
    # Handle OAuth errors from provider
    if error:
        logger.warning(f"[INTEGRATIONS] OAuth error from {provider}: {error} - {error_description}")
        return RedirectResponse(
            url=get_frontend_redirect_url(False, provider, error_description or error)
        )

    try:
        # Exchange code for tokens
        token_data = await exchange_code_for_token(provider, code, state)

        # Store in database using service role (no auth context in callback)
        service_client = get_service_client()

        # Upsert integration (update if exists, insert if not)
        existing = service_client.table("platform_connections").select("id").eq(
            "user_id", token_data["user_id"]
        ).eq("platform", provider).execute()

        if existing.data:
            user_id = token_data["user_id"]

            # Update existing - clear landscape to force rediscovery from new workspace
            update_data = {
                "credentials_encrypted": token_data["credentials_encrypted"],
                "metadata": token_data["metadata"],
                "status": token_data["status"],
                "last_error": None,
                "updated_at": datetime.utcnow().isoformat(),
                # Clear old landscape data so it's refetched from new workspace
                "landscape": None,
                "landscape_discovered_at": None,
            }
            # Only overwrite refresh_token if the new OAuth response actually has one.
            if token_data.get("refresh_token_encrypted"):
                update_data["refresh_token_encrypted"] = token_data["refresh_token_encrypted"]

            service_client.table("platform_connections").update(
                update_data
            ).eq("id", existing.data[0]["id"]).execute()

            # ADR-153: platform_content table removed. Only sync_registry cleanup needed.
            # Delete sync_registry entries for this platform
            service_client.table("sync_registry").delete().eq(
                "user_id", user_id
            ).eq("platform", provider).execute()

            # ADR-059: user_memory has no inferred/platform-sourced entries; nothing to delete.

            logger.info(f"[INTEGRATIONS] Updated {provider} for user {user_id}, purged old workspace data")
        else:
            # Insert new
            service_client.table("platform_connections").insert({
                "user_id": token_data["user_id"],
                "platform": provider,  # ADR-058: column is 'platform', not 'provider'
                "credentials_encrypted": token_data["credentials_encrypted"],
                "refresh_token_encrypted": token_data.get("refresh_token_encrypted"),
                "metadata": token_data["metadata"],
                "status": token_data["status"],
            }).execute()

            logger.info(f"[INTEGRATIONS] Connected {provider} for user {token_data['user_id']}")

        # Activity log: record integration connection (ADR-063)
        try:
            from services.activity_log import write_activity
            import asyncio
            asyncio.create_task(write_activity(
                client=service_client,
                user_id=token_data["user_id"],
                event_type="integration_connected",
                summary=f"Connected {provider.title()}",
                metadata={"provider": provider},
            ))
        except Exception:
            pass  # Non-fatal

        # ADR-113: Auto-discover landscape + auto-select sources + kick off sync
        # This eliminates the manual source-selection prerequisite.
        try:
            user_id_for_auto = token_data["user_id"]

            # Re-read the integration row (we just upserted it)
            auto_result = service_client.table("platform_connections").select(
                "id, credentials_encrypted, refresh_token_encrypted, metadata, landscape"
            ).eq("user_id", user_id_for_auto).eq("platform", provider).limit(1).execute()

            if auto_result.data:
                integration_row = auto_result.data[0]

                from services.landscape import discover_landscape, compute_smart_defaults
                from services.platform_limits import get_limits_for_user, PROVIDER_LIMIT_MAP

                landscape_data = await discover_landscape(provider, user_id_for_auto, integration_row)

                if landscape_data.get("resources"):
                    # Compute smart defaults within tier limits
                    limits = get_limits_for_user(service_client, user_id_for_auto)
                    limit_field = PROVIDER_LIMIT_MAP.get(
                        provider,
                        "slack_channels"
                    )
                    max_sources = getattr(limits, limit_field, 5)
                    if max_sources == -1:
                        max_sources = 999

                    smart_selected = compute_smart_defaults(
                        provider, landscape_data["resources"], max_sources
                    )
                    landscape_data["selected_sources"] = smart_selected

                    # Store landscape + selected sources
                    service_client.table("platform_connections").update({
                        "landscape": landscape_data,
                        "landscape_discovered_at": datetime.utcnow().isoformat(),
                    }).eq("id", integration_row["id"]).execute()

                    logger.info(
                        f"[INTEGRATIONS] ADR-113: Auto-selected {len(smart_selected)} sources "
                        f"for {provider} user {user_id_for_auto[:8]}"
                    )

                    # ADR-153: Platform sync removed. Platform data flows through tracking tasks.
                    # Auto-sync disabled — user creates monitoring tasks post-connection.
                    if smart_selected:
                        logger.info(
                            f"[INTEGRATIONS] ADR-153: Platform connected ({provider}), "
                            f"{len(smart_selected)} sources selected. Create tracking task to begin accumulation."
                        )
                else:
                    logger.info(
                        f"[INTEGRATIONS] ADR-113: No resources discovered for {provider} "
                        f"user {user_id_for_auto[:8]}, skipping auto-selection"
                    )
        except Exception as e:
            # Non-fatal: auto-selection is best-effort. User can still select manually.
            logger.warning(f"[INTEGRATIONS] ADR-113: Auto-selection failed for {provider}: {e}")

        # Redirect to frontend with success
        return RedirectResponse(
            url=get_frontend_redirect_url(True, provider, redirect_to=token_data.get("redirect_to"))
        )

    except ValueError as e:
        logger.warning(f"[INTEGRATIONS] OAuth validation error: {e}")
        return RedirectResponse(
            url=get_frontend_redirect_url(False, provider, str(e))
        )
    except Exception as e:
        logger.error(f"[INTEGRATIONS] OAuth callback error for {provider}: {e}")
        return RedirectResponse(
            url=get_frontend_redirect_url(False, provider, "Failed to connect. Please try again.")
        )


# =============================================================================
# ADR-030: Landscape Discovery & Coverage
# =============================================================================

class LandscapeResourceResponse(BaseModel):
    """A resource in the platform landscape."""
    id: str
    name: str
    resource_type: str  # 'label', 'channel', 'page', 'database'
    coverage_state: str = "uncovered"  # uncovered, partial, covered, stale, excluded
    last_extracted_at: Optional[datetime] = None
    items_extracted: int = 0
    metadata: dict[str, Any] = {}
    last_error: Optional[str] = None
    last_error_at: Optional[datetime] = None
    recommended: bool = False


class LandscapeResponse(BaseModel):
    """Platform landscape with coverage summary."""
    provider: str
    discovered_at: Optional[datetime] = None
    resources: list[LandscapeResourceResponse]
    coverage_summary: dict[str, Any] = {}


class CoverageUpdateRequest(BaseModel):
    """Request to update coverage state for a resource."""
    coverage_state: str  # 'excluded' to mark as not relevant, 'uncovered' to reset


@router.get("/integrations/{provider}/landscape")
async def get_landscape(
    provider: str,
    refresh: bool = Query(False, description="Force refresh from provider"),
    auth: UserClient = None
) -> LandscapeResponse:
    """
    Get the platform landscape with coverage information.

    ADR-030: Shows all available resources (labels, channels, pages) and their
    extraction coverage state. Helps users understand what YARNNN knows vs. doesn't know.

    If landscape hasn't been discovered or refresh=True, fetches from provider.
    """
    if provider not in ["slack", "notion"]:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}. ADR-131: Only Slack and Notion are supported.")

    user_id = auth.user_id

    providers_to_try = PROVIDER_ALIASES.get(provider, [provider])

    # Get integration (try aliases)
    integration = None
    resolved_provider = provider
    for p in providers_to_try:
        result = auth.client.table("platform_connections").select(
            "id, credentials_encrypted, refresh_token_encrypted, metadata, landscape, landscape_discovered_at"
        ).eq("user_id", user_id).eq("platform", p).limit(1).execute()
        if result.data:
            integration = result
            resolved_provider = p
            break

    if not integration or not integration.data:
        raise HTTPException(status_code=404, detail=f"No {provider} integration found")

    # Check if we need to discover
    # ADR-030: Also trigger discovery if landscape is empty or has no resources
    landscape = integration.data[0].get("landscape")
    is_empty_landscape = not landscape or not landscape.get("resources")
    needs_discovery = refresh or is_empty_landscape

    if needs_discovery:
        # Discover landscape from provider (shared service)
        from services.landscape import discover_landscape
        try:
            landscape_data = await discover_landscape(resolved_provider, user_id, integration.data[0])
        except Exception as e:
            logger.error(f"[LANDSCAPE] Discovery failed for {provider} user {user_id[:8]}: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Failed to discover {provider} resources: {str(e)[:200]}. "
                       "This may indicate expired OAuth tokens. Try reconnecting the integration."
            )

        # Preserve existing selected_sources through refresh
        # selected_sources can be dicts ({"id": ..., "name": ...}) or plain strings
        existing_selected = (landscape or {}).get("selected_sources", [])
        if existing_selected:
            new_resource_ids = {r["id"] for r in landscape_data.get("resources", [])}
            landscape_data["selected_sources"] = [
                s for s in existing_selected
                if (s.get("id") if isinstance(s, dict) else s) in new_resource_ids
            ]
        else:
            # ADR-079: Smart auto-selection for first-time landscape discovery
            from services.landscape import compute_smart_defaults
            from services.platform_limits import get_limits_for_user, PROVIDER_LIMIT_MAP

            limits = get_limits_for_user(auth.client, user_id)
            limit_field = PROVIDER_LIMIT_MAP.get(
                resolved_provider,
                "slack_channels"
            )
            max_sources = getattr(limits, limit_field, 5)
            if max_sources == -1:
                max_sources = 999  # unlimited

            smart_selected = compute_smart_defaults(
                resolved_provider,
                landscape_data.get("resources", []),
                max_sources,
            )
            landscape_data["selected_sources"] = smart_selected
            logger.info(
                f"[LANDSCAPE] Auto-selected {len(smart_selected)} sources for "
                f"{resolved_provider} user {user_id[:8]}"
            )

        # Store landscape snapshot
        auth.client.table("platform_connections").update({
            "landscape": landscape_data,
            "landscape_discovered_at": datetime.utcnow().isoformat()
        }).eq("id", integration.data[0]["id"]).execute()

        discovered_at = datetime.utcnow()
    else:
        landscape_data = integration.data[0].get("landscape", {})
        discovered_at = integration.data[0].get("landscape_discovered_at")

    # Get sync records for this provider (ADR-058)
    sync_result = auth.client.table("sync_registry").select(
        "resource_id, resource_name, last_synced_at, item_count, last_error, last_error_at"
    ).eq("user_id", user_id).eq("platform", resolved_provider).execute()

    sync_by_id = {s["resource_id"]: s for s in (sync_result.data or [])}

    def _sync_variants(resource_id: Optional[str]) -> list[str]:
        """Return ID variants to tolerate legacy/normalized sync IDs."""
        if not resource_id:
            return []
        return [resource_id]

    # Build resource list with sync status
    resources = []
    for resource in landscape_data.get("resources", []):
        resource_id = resource.get("id")
        sync_data = {}
        for candidate_id in _sync_variants(resource_id):
            if candidate_id in sync_by_id:
                sync_data = sync_by_id[candidate_id]
                break

        # Determine coverage state from sync data
        coverage_state = "covered" if sync_data.get("last_synced_at") else "uncovered"

        resources.append(LandscapeResourceResponse(
            id=resource_id,
            name=resource.get("name", "Unknown"),
            resource_type=resource.get("type", "unknown"),
            coverage_state=coverage_state,
            last_extracted_at=sync_data.get("last_synced_at"),
            items_extracted=sync_data.get("item_count", 0),
            metadata=resource.get("metadata", {}),
            last_error=sync_data.get("last_error"),
            last_error_at=sync_data.get("last_error_at"),
        ))

    # Compute recommended IDs (ADR-079 smart defaults) for UI grouping
    from services.landscape import compute_smart_defaults
    from services.platform_limits import get_limits_for_user, PROVIDER_LIMIT_MAP

    limits = get_limits_for_user(auth.client, user_id)
    limit_field = PROVIDER_LIMIT_MAP.get(provider, "slack_channels")
    max_sources = getattr(limits, limit_field, 5)
    if max_sources == -1:
        max_sources = 999

    recommended_sources = compute_smart_defaults(
        resolved_provider,
        landscape_data.get("resources", []),
        max_sources,
    )
    recommended_ids = {s["id"] for s in recommended_sources}

    for r in resources:
        r.recommended = r.id in recommended_ids

    # Get coverage summary
    summary_result = auth.client.rpc("get_coverage_summary", {
        "p_user_id": user_id,
        "p_provider": provider
    }).execute()

    coverage_summary = summary_result.data[0] if summary_result.data else {}

    return LandscapeResponse(
        provider=provider,
        discovered_at=discovered_at,
        resources=resources,
        coverage_summary=coverage_summary
    )


# =============================================================================
# ADR-052: Platform Context (Synced Content)
# =============================================================================

# ADR-153: /integrations/{provider}/context endpoint DELETED — platform_content sunset.
# Platform data flows through tasks into workspace context domains.


@router.patch("/integrations/{provider}/coverage/{resource_id}")
async def update_coverage(
    provider: str,
    resource_id: str,
    request: CoverageUpdateRequest,
    auth: UserClient = None
) -> dict[str, Any]:
    """
    Update sync state for a resource.

    ADR-058: Allows users to mark resources as excluded (not relevant)
    or reset them to uncovered. Uses sync_registry.sync_metadata.
    """
    if request.coverage_state not in ["excluded", "uncovered"]:
        raise HTTPException(
            status_code=400,
            detail="coverage_state must be 'excluded' or 'uncovered'"
        )

    user_id = auth.user_id

    # Check if sync record exists
    existing = auth.client.table("sync_registry").select("id, sync_metadata").eq(
        "user_id", user_id
    ).eq("platform", provider).eq("resource_id", resource_id).execute()

    if existing.data:
        # Update existing record's metadata
        metadata = existing.data[0].get("sync_metadata", {}) or {}
        metadata["excluded"] = request.coverage_state == "excluded"
        auth.client.table("sync_registry").update({
            "sync_metadata": metadata,
        }).eq("id", existing.data[0]["id"]).execute()
    else:
        # Insert new record with exclusion state
        auth.client.table("sync_registry").insert({
            "user_id": user_id,
            "platform": provider,
            "resource_id": resource_id,
            "sync_metadata": {"excluded": request.coverage_state == "excluded"}
        }).execute()

    return {"success": True, "resource_id": resource_id, "coverage_state": request.coverage_state}


# =============================================================================
# ADR-043: User Limits & Source Selection
# =============================================================================

class UserLimitsResponse(BaseModel):
    """User's tier limits and current usage. Subscription + work credits model."""
    tier: str
    limits: dict[str, Any]  # sync_frequency (str), monthly_messages, monthly_credits, active_tasks, etc.
    usage: dict[str, Any]   # credits_used, monthly_messages_used, active_tasks, etc.
    next_sync: Optional[str] = None


class SelectedSourcesRequest(BaseModel):
    """Request to update selected sources for a platform."""
    source_ids: list[str]


class SelectedSourcesResponse(BaseModel):
    """Response with updated sources."""
    success: bool
    selected_sources: list[dict[str, Any]]
    message: str


@router.get("/user/limits")
async def get_user_limits(auth: UserClient) -> UserLimitsResponse:
    """
    Get user's tier limits and current usage.

    Returns subscription + work credits model:
    - tier: "free" | "pro"
    - limits: monthly_messages, monthly_credits, active_tasks, sources, sync_frequency
    - usage: credits_used, monthly_messages_used, active_tasks, source counts
    - next_sync: ISO timestamp of next scheduled platform sync
    """
    from services.platform_limits import get_usage_summary

    # ADR-108: timezone from /memory/MEMORY.md
    user_tz = "UTC"
    try:
        from services.workspace import UserMemory
        um = UserMemory(auth.client, auth.user_id)
        profile = UserMemory._parse_memory_md(um.read_sync("MEMORY.md"))
        user_tz = profile.get("timezone") or "UTC"
    except Exception as e:
        logger.debug(f"Failed to fetch user timezone: {e}")

    summary = get_usage_summary(auth.client, auth.user_id, user_tz)

    return UserLimitsResponse(
        tier=summary["tier"],
        limits=summary["limits"],
        usage=summary["usage"],
        next_sync=summary.get("next_sync"),
    )


@router.put("/integrations/{provider}/sources")
async def update_selected_sources(
    provider: str,
    request: SelectedSourcesRequest,
    auth: UserClient
) -> SelectedSourcesResponse:
    """
    Update selected sources for a platform.

    ADR-043: Validates against user's tier limits. If over limit,
    truncates to max allowed and returns warning.

    Sources are stored in platform_connections.landscape.selected_sources.
    """
    from services.platform_limits import validate_sources_update

    user_id = auth.user_id
    providers_to_try = PROVIDER_ALIASES.get(provider, [provider])

    # Validate against limits
    valid, message, allowed_ids = validate_sources_update(
        auth.client, user_id, provider, request.source_ids
    )

    # Get integration (resolve alias to DB platform, try all candidates)
    integration = None
    for p in providers_to_try:
        result = auth.client.table("platform_connections").select(
            "id, landscape"
        ).eq("user_id", user_id).eq("platform", p).limit(1).execute()
        if result.data:
            integration = result
            break

    if not integration or not integration.data:
        raise HTTPException(status_code=404, detail=f"No {provider} integration found")

    # Get current landscape
    landscape = integration.data[0].get("landscape", {}) or {}
    resources = landscape.get("resources", [])

    # Build selected sources list from allowed IDs
    selected_sources = []
    resource_map = {r.get("id"): r for r in resources}
    for source_id in allowed_ids:
        if source_id in resource_map:
            r = resource_map[source_id]
            platform = r.get("metadata", {}).get("platform") or provider
            selected_sources.append({
                "id": source_id,
                "name": r.get("name", source_id),
                "type": r.get("type", "unknown"),
                "platform": platform,
            })

    # Update landscape with selected sources
    landscape["selected_sources"] = selected_sources
    auth.client.table("platform_connections").update({
        "landscape": landscape,
    }).eq("id", integration.data[0]["id"]).execute()

    logger.info(f"[INTEGRATIONS] User {user_id} updated {provider} sources: {len(selected_sources)} selected")

    return SelectedSourcesResponse(
        success=valid,
        selected_sources=selected_sources,
        message=message,
    )


@router.get("/integrations/{provider}/sources")
async def get_selected_sources(
    provider: str,
    auth: UserClient
) -> dict[str, Any]:
    """
    Get currently selected sources for a platform.

    ADR-043: Returns the sources currently enabled for sync/context gathering.
    """
    user_id = auth.user_id

    providers_to_try = PROVIDER_ALIASES.get(provider, [provider])

    integration_data = None
    for p in providers_to_try:
        result = auth.client.table("platform_connections").select(
            "landscape"
        ).eq("user_id", user_id).eq("platform", p).limit(1).execute()
        if result.data:
            integration_data = result.data[0]
            break

    if not integration_data:
        raise HTTPException(status_code=404, detail=f"No {provider} integration found")

    landscape = integration_data.get("landscape", {}) or {}
    selected = landscape.get("selected_sources", [])

    # ADR-043: Tier limits for source count
    from services.platform_limits import get_usage_summary
    summary = get_usage_summary(auth.client, user_id)
    limit_field = {
        "slack": "slack_channels",
        "notion": "notion_pages",
    }.get(provider, "slack_channels")
    limit = summary["limits"].get(limit_field, 1)

    return {
        "sources": selected,
        "limit": limit,
        "can_add_more": len(selected) < limit,
    }


@router.post("/integrations/{provider}/sync")
async def trigger_platform_sync(
    provider: str,
    auth: UserClient,
    background_tasks: BackgroundTasks
) -> dict[str, Any]:
    """
    ADR-153: Platform sync sunset. This endpoint is deprecated.
    Platform data flows through tracking tasks into context domains.
    """
    return {
        "success": False,
        "error": "deprecated",
        "message": "Platform sync is deprecated (ADR-153). Create a monitoring task and trigger it instead.",
    }


@router.get("/integrations/{provider}/sync-status")
async def get_platform_sync_status(
    provider: str,
    auth: UserClient,
) -> dict[str, Any]:
    """
    Get sync status for a platform.

    ADR-049: Context Freshness Model
    Returns freshness information for each synced resource.
    """
    from datetime import timezone

    user_id = auth.user_id
    providers_to_try = PROVIDER_ALIASES.get(provider, [provider])

    # Verify integration exists (try all alias candidates)
    integration = None
    for p in providers_to_try:
        result = auth.client.table("platform_connections").select(
            "id, status"
        ).eq("user_id", user_id).eq("platform", p).limit(1).execute()
        if result.data:
            integration = result
            break

    if not integration or not integration.data:
        raise HTTPException(status_code=404, detail=f"No {provider} integration found")

    # Get sync registry entries for this platform (ADR-086: include error fields)
    sync_result = auth.client.table("sync_registry").select(
        "resource_id, resource_name, last_synced_at, item_count, source_latest_at, last_error, last_error_at"
    ).eq("user_id", user_id).eq("platform", provider).execute()

    now = datetime.now(timezone.utc)
    synced_resources = []
    stale_count = 0
    error_count = 0

    for entry in (sync_result.data or []):
        last_synced = entry.get("last_synced_at")
        freshness_status = "unknown"

        if last_synced:
            if isinstance(last_synced, str):
                last_synced_dt = datetime.fromisoformat(last_synced.replace("Z", "+00:00"))
            else:
                last_synced_dt = last_synced

            hours_since = (now - last_synced_dt).total_seconds() / 3600

            if hours_since < 1:
                freshness_status = "fresh"
            elif hours_since < 24:
                freshness_status = "recent"
            else:
                freshness_status = "stale"
                stale_count += 1
        else:
            freshness_status = "unknown"
            stale_count += 1

        last_error = entry.get("last_error")
        if last_error:
            error_count += 1

        synced_resources.append({
            "resource_id": entry.get("resource_id"),
            "resource_name": entry.get("resource_name"),
            "last_synced": last_synced,
            "freshness_status": freshness_status,
            "items_synced": entry.get("item_count", 0),
            "last_error": last_error,
            "last_error_at": entry.get("last_error_at"),
        })

    return {
        "platform": provider,
        "synced_resources": synced_resources,
        "stale_count": stale_count,
        "error_count": error_count,
    }
