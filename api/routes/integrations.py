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
from integrations.core.client import get_mcp_manager, MCP_AVAILABLE
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
        ).single().execute()

        if not result.data:
            logger.error(f"[IMPORT_BG] Job {job_id} not found")
            return

        job = result.data

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
    deliverable_version_id: str
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
    include_sent: bool = True  # Gmail: include sent messages
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
    ephemeral_stored: int = 0  # ADR-038: items stored to ephemeral_context
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
        result = auth.client.table("user_integrations").select(
            "id, provider, status, metadata, last_used_at, created_at"
        ).eq("user_id", user_id).execute()

        integrations = []
        for row in result.data or []:
            metadata = row.get("metadata", {}) or {}
            integrations.append(IntegrationResponse(
                id=row["id"],
                provider=row["provider"],
                status=row["status"],
                workspace_name=metadata.get("workspace_name"),
                last_used_at=row.get("last_used_at"),
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
    deliverable_count: int = 0
    activity_7d: int = 0  # messages/emails/updates in last 7 days


class IntegrationsSummaryResponse(BaseModel):
    """
    ADR-033: Summary of all integrations for Dashboard platform cards.

    Provides aggregated stats for each connected platform:
    - Connection status
    - Resource counts (channels, labels, pages)
    - Deliverable counts targeting this platform
    - Recent activity from ephemeral context
    """
    platforms: list[PlatformSummary]
    total_deliverables: int = 0


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
        integrations_result = auth.client.table("user_integrations").select(
            "id, provider, status, metadata, landscape, created_at"
        ).eq("user_id", user_id).execute()

        if not integrations_result.data:
            return IntegrationsSummaryResponse(platforms=[], total_deliverables=0)

        platforms = []
        for integration in integrations_result.data:
            provider = integration["provider"]
            metadata = integration.get("metadata", {}) or {}
            landscape = integration.get("landscape", {}) or {}
            resources = landscape.get("resources", [])

            # Determine resource type name
            resource_type = {
                "slack": "channels",
                "gmail": "labels",
                "notion": "pages",
                "google": "calendars"
            }.get(provider, "resources")

            # Count deliverables targeting this platform
            deliverables_result = auth.client.table("deliverables").select(
                "id", count="exact"
            ).eq("user_id", user_id).contains(
                "destination", {"platform": provider}
            ).execute()
            deliverable_count = deliverables_result.count or 0

            # Count recent activity from ephemeral_context (last 7 days)
            from datetime import timedelta
            seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
            activity_result = auth.client.table("ephemeral_context").select(
                "id", count="exact"
            ).eq("user_id", user_id).eq(
                "platform", provider
            ).gte("created_at", seven_days_ago).execute()
            activity_7d = activity_result.count or 0

            platforms.append(PlatformSummary(
                provider=provider,
                status=integration["status"],
                workspace_name=metadata.get("workspace_name"),
                connected_at=integration["created_at"],
                resource_count=len(resources),
                resource_type=resource_type,
                deliverable_count=deliverable_count,
                activity_7d=activity_7d
            ))

        # Total deliverables count
        total_result = auth.client.table("deliverables").select(
            "id", count="exact"
        ).eq("user_id", user_id).execute()
        total_deliverables = total_result.count or 0

        return IntegrationsSummaryResponse(
            platforms=platforms,
            total_deliverables=total_deliverables
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
            query = query.eq("provider", provider)

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
        ).eq("id", job_id).eq("user_id", user_id).single().execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Import job not found")

        job = result.data

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

    try:
        result = auth.client.table("user_integrations").select(
            "id, provider, status, metadata, last_used_at, created_at"
        ).eq("user_id", user_id).eq("provider", provider).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail=f"Integration not found: {provider}")

        row = result.data[0]
        metadata = row.get("metadata", {}) or {}

        return IntegrationResponse(
            id=row["id"],
            provider=row["provider"],
            status=row["status"],
            workspace_name=metadata.get("workspace_name"),
            last_used_at=row.get("last_used_at"),
            created_at=row["created_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTEGRATIONS] Failed to get {provider} for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get integration")


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

    try:
        # Delete integration (cascade will handle export preferences)
        result = auth.client.table("user_integrations").delete().eq(
            "user_id", user_id
        ).eq("provider", provider).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail=f"Integration not found: {provider}")

        logger.info(f"[INTEGRATIONS] User {user_id} disconnected {provider}")

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
    Export a deliverable version to a provider.

    ADR-028: Uses the unified DestinationExporter infrastructure.

    The destination format depends on the provider:
    - Slack: { "channel_id": "C123..." } or { "target": "C123..." }
    - Notion: { "page_id": "..." } or { "target": "..." }
    - Download: {} (no destination needed)
    """
    from integrations.exporters import get_exporter_registry, ExporterContext

    user_id = auth.user_id
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
            if not MCP_AVAILABLE:
                raise HTTPException(
                    status_code=503,
                    detail="Integration service unavailable (MCP not installed)"
                )

            integration = auth.client.table("user_integrations").select(
                "id, access_token_encrypted, refresh_token_encrypted, metadata, status"
            ).eq("user_id", user_id).eq("provider", provider).single().execute()

            if not integration.data:
                raise HTTPException(
                    status_code=404,
                    detail=f"No {provider} integration found. Please connect first."
                )

            if integration.data["status"] != IntegrationStatus.ACTIVE.value:
                raise HTTPException(
                    status_code=400,
                    detail=f"{provider} integration is {integration.data['status']}. Please reconnect."
                )

            integration_id = integration.data["id"]
            token_manager = get_token_manager()

            # Decrypt tokens
            access_token = token_manager.decrypt(integration.data["access_token_encrypted"])
            refresh_token = token_manager.decrypt(integration.data["refresh_token_encrypted"]) if integration.data.get("refresh_token_encrypted") else None

            # Build metadata, adding refresh_token for Gmail (ADR-029)
            metadata = integration.data.get("metadata", {}) or {}
            if provider == "gmail" and refresh_token:
                metadata["refresh_token"] = refresh_token

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

        # 2. Get deliverable version content
        version = auth.client.table("deliverable_versions").select(
            "id, final_content, draft_content, deliverable_id"
        ).eq("id", request.deliverable_version_id).single().execute()

        if not version.data:
            raise HTTPException(status_code=404, detail="Deliverable version not found")

        # Get deliverable title
        deliverable = auth.client.table("deliverables").select(
            "title"
        ).eq("id", version.data["deliverable_id"]).single().execute()

        content = version.data.get("final_content") or version.data.get("draft_content", "")
        title = deliverable.data["title"] if deliverable.data else "YARNNN Export"

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
                "deliverable_version_id": request.deliverable_version_id,
                "deliverable_id": version.data["deliverable_id"]
            },
            context=context
        )

        # 5. Log the export
        log_entry = {
            "deliverable_version_id": request.deliverable_version_id,
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

        # 6. Update last_used_at for auth integrations
        if integration_id:
            auth.client.table("user_integrations").update({
                "last_used_at": datetime.utcnow().isoformat()
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
    Normalize legacy destination format to new ADR-028 format.

    Supports both:
    - Legacy: { "channel_id": "C123" } or { "page_id": "..." }
    - New: { "platform": "slack", "target": "C123", "format": "message" }
    """
    # If already in new format, return as-is
    if "platform" in destination and "target" in destination:
        return destination

    # Convert legacy format
    if provider == "slack":
        return {
            "platform": "slack",
            "target": destination.get("channel_id") or destination.get("target"),
            "format": destination.get("format", "message"),
            "options": destination.get("options", {})
        }
    elif provider == "notion":
        return {
            "platform": "notion",
            "target": destination.get("page_id") or destination.get("target"),
            "format": destination.get("format", "page"),
            "options": destination.get("options", {})
        }
    elif provider == "download":
        return {
            "platform": "download",
            "target": None,
            "format": destination.get("format", "markdown"),
            "options": {}
        }
    elif provider == "gmail":
        # ADR-029: Gmail destination normalization
        return {
            "platform": "gmail",
            "target": destination.get("to") or destination.get("recipient") or destination.get("target"),
            "format": destination.get("format", "send"),  # send, draft, reply
            "options": {
                "cc": destination.get("cc"),
                "subject": destination.get("subject"),
                "thread_id": destination.get("thread_id"),
            }
        }

    # Unknown provider, pass through
    return {
        "platform": provider,
        "target": destination.get("target"),
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
        integration = auth.client.table("user_integrations").select(
            "id, access_token_encrypted, status"
        ).eq("user_id", user_id).eq("provider", "slack").single().execute()

        if not integration.data:
            raise HTTPException(
                status_code=404,
                detail="No Slack integration found. Please connect first."
            )

        if integration.data["status"] != IntegrationStatus.ACTIVE.value:
            raise HTTPException(
                status_code=400,
                detail=f"Slack integration is {integration.data['status']}. Please reconnect."
            )

        # Get integration metadata for team_id
        integration_full = auth.client.table("user_integrations").select(
            "metadata"
        ).eq("user_id", user_id).eq("provider", "slack").single().execute()

        metadata = integration_full.data.get("metadata", {}) or {}
        team_id = metadata.get("team_id")
        if not team_id:
            raise HTTPException(status_code=400, detail="Slack integration missing team_id")

        # Decrypt access token
        token_manager = get_token_manager()
        access_token = token_manager.decrypt(integration.data["access_token_encrypted"])

        # Fetch channels via MCP
        mcp = get_mcp_manager()
        raw_channels = await mcp.list_slack_channels(
            user_id=user_id,
            bot_token=access_token,
            team_id=team_id
        )

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
        integration = auth.client.table("user_integrations").select(
            "id, access_token_encrypted, status"
        ).eq("user_id", user_id).eq("provider", "notion").single().execute()

        if not integration.data:
            raise HTTPException(
                status_code=404,
                detail="No Notion integration found. Please connect first."
            )

        if integration.data["status"] != IntegrationStatus.ACTIVE.value:
            raise HTTPException(
                status_code=400,
                detail=f"Notion integration is {integration.data['status']}. Please reconnect."
            )

        # Decrypt access token
        token_manager = get_token_manager()
        access_token = token_manager.decrypt(integration.data["access_token_encrypted"])

        # Fetch pages via MCP
        mcp = get_mcp_manager()
        raw_pages = await mcp.search_notion_pages(
            user_id=user_id,
            auth_token=access_token,
            query=query
        )

        # Transform to response format (MCP result structure may vary)
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

        logger.info(f"[INTEGRATIONS] User {user_id} listed {len(pages)} Notion pages via MCP")

        return NotionPagesListResponse(pages=pages)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTEGRATIONS] Failed to list Notion pages for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list pages: {str(e)}")


# =============================================================================
# Import Jobs - Start Import
# =============================================================================

@router.post("/integrations/slack/import")
async def start_slack_import(
    request: StartImportRequest,
    auth: UserClient,
    background_tasks: BackgroundTasks
) -> ImportJobResponse:
    """
    Start a context import from a Slack channel.

    Creates a background job that:
    1. Fetches messages from the channel
    2. Runs ContextImportAgent to extract structured context
    3. Stores results as context_sources

    The job runs async; poll GET /integrations/import/{job_id} for status.
    """
    user_id = auth.user_id

    try:
        # Get user's Slack integration
        integration = auth.client.table("user_integrations").select(
            "id, access_token_encrypted, status"
        ).eq("user_id", user_id).eq("provider", "slack").single().execute()

        if not integration.data:
            raise HTTPException(
                status_code=404,
                detail="No Slack integration found. Please connect first."
            )

        if integration.data["status"] != IntegrationStatus.ACTIVE.value:
            raise HTTPException(
                status_code=400,
                detail=f"Slack integration is {integration.data['status']}. Please reconnect."
            )

        # Use resource_name if provided, otherwise use resource_id as fallback
        # (Background job processor will resolve the actual channel name via MCP)
        resource_name = request.resource_name or f"#{request.resource_id}"

        # Build config dict from request
        config_dict = {}
        if request.config:
            config_dict["learn_style"] = request.config.learn_style
            if request.config.style_user_id:
                config_dict["style_user_id"] = request.config.style_user_id

        # ADR-030: Build scope dict with defaults
        scope_dict = {
            "recency_days": 7,
            "max_items": 200,
            "include_threads": True
        }
        if request.scope:
            scope_dict["recency_days"] = request.scope.recency_days
            scope_dict["max_items"] = request.scope.max_items
            scope_dict["include_threads"] = request.scope.include_threads

        # Create import job
        job_data = {
            "user_id": user_id,
            "provider": "slack",
            "resource_id": request.resource_id,
            "resource_name": resource_name,
            "project_id": request.project_id,
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
        logger.info(f"[INTEGRATIONS] User {user_id} started Slack import job {job['id']}{style_note}")

        # Trigger background processing immediately
        background_tasks.add_task(_process_import_job_background, job["id"], job_data)

        return ImportJobResponse(
            id=job["id"],
            provider="slack",
            resource_id=job["resource_id"],
            resource_name=job.get("resource_name"),
            status=job["status"],
            progress=job.get("progress", 0),
            created_at=job["created_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTEGRATIONS] Failed to start Slack import for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start import: {str(e)}")


# =============================================================================
# Import Jobs - Gmail (ADR-029)
# =============================================================================

@router.post("/integrations/gmail/import")
async def start_gmail_import(
    request: StartImportRequest,
    auth: UserClient,
    background_tasks: BackgroundTasks
) -> ImportJobResponse:
    """
    Start a context import from Gmail.

    ADR-029: Gmail as full integration platform.

    Resource ID formats:
    - "inbox" - Recent inbox messages
    - "thread:<thread_id>" - Specific email thread
    - "query:<gmail_query>" - Messages matching search (e.g., "from:sarah@company.com")

    Creates a background job that:
    1. Fetches messages via MCP
    2. Runs ContextImportAgent to extract structured context
    3. Optionally learns email style (if config.learn_style=true)
    4. Stores results as memories
    """
    user_id = auth.user_id

    try:
        # Get user's Gmail integration
        integration = auth.client.table("user_integrations").select(
            "id, refresh_token_encrypted, status"
        ).eq("user_id", user_id).eq("provider", "gmail").single().execute()

        if not integration.data:
            raise HTTPException(
                status_code=404,
                detail="No Gmail integration found. Please connect first."
            )

        if integration.data["status"] != IntegrationStatus.ACTIVE.value:
            raise HTTPException(
                status_code=400,
                detail=f"Gmail integration is {integration.data['status']}. Please reconnect."
            )

        # Parse resource name for display
        resource_id = request.resource_id
        if resource_id == "inbox":
            resource_name = request.resource_name or "Inbox"
        elif resource_id.startswith("thread:"):
            resource_name = request.resource_name or f"Email Thread"
        elif resource_id.startswith("query:"):
            query = resource_id.split(":", 1)[1]
            resource_name = request.resource_name or f"Search: {query[:30]}..."
        else:
            resource_name = request.resource_name or resource_id

        # Build config dict
        config_dict = {}
        if request.config:
            config_dict["learn_style"] = request.config.learn_style

        # ADR-030: Build scope dict with defaults
        scope_dict = {
            "recency_days": 7,
            "max_items": 100,
            "include_sent": True
        }
        if request.scope:
            scope_dict["recency_days"] = request.scope.recency_days
            scope_dict["max_items"] = request.scope.max_items
            scope_dict["include_sent"] = request.scope.include_sent

        # Create import job
        job_data = {
            "user_id": user_id,
            "provider": "gmail",
            "resource_id": resource_id,
            "resource_name": resource_name,
            "project_id": request.project_id,
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
        logger.info(f"[INTEGRATIONS] User {user_id} started Gmail import job {job['id']}{style_note}")

        # Trigger background processing immediately
        background_tasks.add_task(_process_import_job_background, job["id"], job_data)

        return ImportJobResponse(
            id=job["id"],
            provider="gmail",
            resource_id=job["resource_id"],
            resource_name=job.get("resource_name"),
            status=job["status"],
            progress=job.get("progress", 0),
            created_at=job["created_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTEGRATIONS] Failed to start Gmail import for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start import: {str(e)}")


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
        integration = auth.client.table("user_integrations").select(
            "id, access_token_encrypted, status"
        ).eq("user_id", user_id).eq("provider", "notion").single().execute()

        if not integration.data:
            raise HTTPException(
                status_code=404,
                detail="No Notion integration found. Please connect first."
            )

        if integration.data["status"] != IntegrationStatus.ACTIVE.value:
            raise HTTPException(
                status_code=400,
                detail=f"Notion integration is {integration.data['status']}. Please reconnect."
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
            "project_id": request.project_id,
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
# Export History
# =============================================================================

@router.get("/integrations/history")
async def get_export_history(
    auth: UserClient,
    deliverable_id: Optional[str] = None,
    limit: int = 20
) -> dict:
    """
    Get export history for the user.
    Optionally filter by deliverable.
    """
    user_id = auth.user_id

    try:
        query = auth.client.table("export_log").select(
            "id, provider, status, external_url, created_at, "
            "deliverable_version_id"
        ).eq("user_id", user_id).order("created_at", desc=True).limit(limit)

        if deliverable_id:
            # Filter by deliverable (need to join through versions)
            versions = auth.client.table("deliverable_versions").select(
                "id"
            ).eq("deliverable_id", deliverable_id).execute()

            if versions.data:
                version_ids = [v["id"] for v in versions.data]
                query = query.in_("deliverable_version_id", version_ids)

        result = query.execute()

        return {
            "exports": result.data or [],
            "total": len(result.data or [])
        }

    except Exception as e:
        logger.error(f"[INTEGRATIONS] Failed to get history for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get export history")


# =============================================================================
# OAuth Flow - Initiate
# =============================================================================

@router.get("/integrations/{provider}/authorize")
async def initiate_oauth(
    provider: str,
    auth: UserClient
) -> dict:
    """
    Initiate OAuth flow for a provider.

    Returns the authorization URL to redirect the user to.
    The frontend should open this URL in a popup or redirect.
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
        auth_url = get_authorization_url(provider, user_id)
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
        existing = service_client.table("user_integrations").select("id").eq(
            "user_id", token_data["user_id"]
        ).eq("provider", provider).execute()

        if existing.data:
            # Update existing
            service_client.table("user_integrations").update({
                "access_token_encrypted": token_data["access_token_encrypted"],
                "refresh_token_encrypted": token_data.get("refresh_token_encrypted"),
                "metadata": token_data["metadata"],
                "status": token_data["status"],
                "last_error": None,
                "updated_at": datetime.utcnow().isoformat(),
            }).eq("id", existing.data[0]["id"]).execute()

            logger.info(f"[INTEGRATIONS] Updated {provider} for user {token_data['user_id']}")
        else:
            # Insert new
            service_client.table("user_integrations").insert({
                "user_id": token_data["user_id"],
                "provider": provider,
                "access_token_encrypted": token_data["access_token_encrypted"],
                "refresh_token_encrypted": token_data.get("refresh_token_encrypted"),
                "metadata": token_data["metadata"],
                "status": token_data["status"],
            }).execute()

            logger.info(f"[INTEGRATIONS] Connected {provider} for user {token_data['user_id']}")

        # Redirect to frontend with success
        return RedirectResponse(
            url=get_frontend_redirect_url(True, provider)
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
    if provider not in ["gmail", "slack", "notion"]:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    user_id = auth.user_id

    # Get integration
    integration = auth.client.table("user_integrations").select(
        "id, access_token_encrypted, refresh_token_encrypted, metadata, landscape, landscape_discovered_at"
    ).eq("user_id", user_id).eq("provider", provider).single().execute()

    if not integration.data:
        raise HTTPException(status_code=404, detail=f"No {provider} integration found")

    # Check if we need to discover
    # ADR-030: Also trigger discovery if landscape is empty or has no resources
    landscape = integration.data.get("landscape")
    is_empty_landscape = not landscape or not landscape.get("resources")
    needs_discovery = refresh or is_empty_landscape

    if needs_discovery:
        # Discover landscape from provider
        landscape_data = await _discover_landscape(provider, user_id, integration.data)

        # Store landscape snapshot
        auth.client.table("user_integrations").update({
            "landscape": landscape_data,
            "landscape_discovered_at": datetime.utcnow().isoformat()
        }).eq("id", integration.data["id"]).execute()

        discovered_at = datetime.utcnow()
    else:
        landscape_data = integration.data.get("landscape", {})
        discovered_at = integration.data.get("landscape_discovered_at")

    # Get coverage records for this provider
    coverage_result = auth.client.table("integration_coverage").select(
        "*"
    ).eq("user_id", user_id).eq("provider", provider).execute()

    coverage_by_id = {c["resource_id"]: c for c in (coverage_result.data or [])}

    # Build resource list with coverage
    resources = []
    for resource in landscape_data.get("resources", []):
        resource_id = resource.get("id")
        coverage = coverage_by_id.get(resource_id, {})

        resources.append(LandscapeResourceResponse(
            id=resource_id,
            name=resource.get("name", "Unknown"),
            resource_type=resource.get("type", "unknown"),
            coverage_state=coverage.get("coverage_state", "uncovered"),
            last_extracted_at=coverage.get("last_extracted_at"),
            items_extracted=coverage.get("items_extracted", 0),
            metadata=resource.get("metadata", {})
        ))

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


async def _discover_landscape(provider: str, user_id: str, integration: dict) -> dict:
    """
    Discover resources from a provider.

    Returns landscape data structure:
    {
        "resources": [
            {"id": "...", "name": "...", "type": "label|channel|page", "metadata": {...}}
        ]
    }
    """
    token_manager = get_token_manager()
    mcp_manager = get_mcp_manager()

    if provider == "gmail":
        # Get Gmail credentials (OAUTH_CONFIGS values are OAuthConfig objects, not dicts)
        gmail_config = OAUTH_CONFIGS["gmail"]
        client_id = gmail_config.client_id
        client_secret = gmail_config.client_secret
        refresh_token = token_manager.decrypt(integration["refresh_token_encrypted"])

        # List labels
        labels = await mcp_manager.list_gmail_labels(
            user_id=user_id,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token
        )

        resources = []
        for label in labels:
            resources.append({
                "id": label.get("id"),
                "name": label.get("name"),
                "type": "label",
                "metadata": {
                    "type": label.get("type"),  # system, user
                    "messageListVisibility": label.get("messageListVisibility"),
                    "labelListVisibility": label.get("labelListVisibility")
                }
            })

        return {"resources": resources}

    elif provider == "slack":
        # Get Slack credentials
        bot_token = token_manager.decrypt(integration["access_token_encrypted"])
        team_id = integration.get("metadata", {}).get("team_id", "")

        # List channels
        channels = await mcp_manager.list_slack_channels(
            user_id=user_id,
            bot_token=bot_token,
            team_id=team_id
        )

        resources = []
        for channel in channels:
            resources.append({
                "id": channel.get("id"),
                "name": f"#{channel.get('name', '')}",
                "type": "channel",
                "metadata": {
                    "is_private": channel.get("is_private", False),
                    "num_members": channel.get("num_members", 0),
                    "topic": channel.get("topic", {}).get("value"),
                    "purpose": channel.get("purpose", {}).get("value")
                }
            })

        return {"resources": resources}

    elif provider == "notion":
        # Get Notion credentials
        auth_token = token_manager.decrypt(integration["access_token_encrypted"])

        # Search for pages
        pages = await mcp_manager.search_notion_pages(
            user_id=user_id,
            auth_token=auth_token
        )

        resources = []
        for page in pages:
            resources.append({
                "id": page.get("id"),
                "name": _extract_notion_title(page),
                "type": "page" if page.get("object") == "page" else "database",
                "metadata": {
                    "parent_type": _extract_notion_parent_type(page),
                    "last_edited": page.get("last_edited_time"),
                    "url": page.get("url")
                }
            })

        return {"resources": resources}

    return {"resources": []}


@router.patch("/integrations/{provider}/coverage/{resource_id}")
async def update_coverage(
    provider: str,
    resource_id: str,
    request: CoverageUpdateRequest,
    auth: UserClient = None
) -> dict[str, Any]:
    """
    Update coverage state for a resource.

    ADR-030: Allows users to mark resources as excluded (not relevant)
    or reset them to uncovered.
    """
    if request.coverage_state not in ["excluded", "uncovered"]:
        raise HTTPException(
            status_code=400,
            detail="coverage_state must be 'excluded' or 'uncovered'"
        )

    user_id = auth.user_id

    # Check if coverage record exists
    existing = auth.client.table("integration_coverage").select("id").eq(
        "user_id", user_id
    ).eq("provider", provider).eq("resource_id", resource_id).execute()

    if existing.data:
        # Update
        auth.client.table("integration_coverage").update({
            "coverage_state": request.coverage_state,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", existing.data[0]["id"]).execute()
    else:
        # Insert
        auth.client.table("integration_coverage").insert({
            "user_id": user_id,
            "provider": provider,
            "resource_id": resource_id,
            "coverage_state": request.coverage_state
        }).execute()

    return {"success": True, "resource_id": resource_id, "coverage_state": request.coverage_state}
