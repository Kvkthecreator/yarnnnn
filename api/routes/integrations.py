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


async def _fetch_google_calendars(
    user_id: str,
    client_id: str,
    client_secret: str,
    refresh_token: str
) -> list[dict]:
    """
    ADR-046: Fetch list of calendars from Google Calendar API.

    Uses refresh token to get fresh access token, then lists calendars.
    """
    import httpx

    # First, get a fresh access token using refresh token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
        )

        if token_response.status_code != 200:
            raise Exception(f"Failed to refresh token: {token_response.text}")

        access_token = token_response.json().get("access_token")

        # Now list calendars
        calendar_response = await client.get(
            "https://www.googleapis.com/calendar/v3/users/me/calendarList",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"maxResults": 50}
        )

        if calendar_response.status_code != 200:
            raise Exception(f"Failed to list calendars: {calendar_response.text}")

        data = calendar_response.json()
        return data.get("items", [])


async def _fetch_google_calendar_events(
    user_id: str,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    calendar_id: str = "primary",
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    max_results: int = 50
) -> list[dict]:
    """
    ADR-046: Fetch calendar events from Google Calendar API.

    Args:
        user_id: User ID for logging
        client_id: Google OAuth client ID
        client_secret: Google OAuth client secret
        refresh_token: User's refresh token
        calendar_id: Calendar to fetch from (default: "primary")
        time_min: Start time (RFC3339), defaults to now
        time_max: End time (RFC3339), defaults to 7 days from now
        max_results: Maximum events to return

    Returns:
        List of calendar event dicts
    """
    import httpx
    from datetime import datetime, timedelta

    # First, get a fresh access token using refresh token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
        )

        if token_response.status_code != 200:
            raise Exception(f"Failed to refresh token: {token_response.text}")

        access_token = token_response.json().get("access_token")

        # Default time window: now to 7 days from now
        if not time_min:
            time_min = datetime.utcnow().isoformat() + "Z"
        if not time_max:
            time_max = (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"

        # Fetch events
        events_response = await client.get(
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "timeMin": time_min,
                "timeMax": time_max,
                "maxResults": max_results,
                "singleEvents": "true",  # Expand recurring events
                "orderBy": "startTime",
            }
        )

        if events_response.status_code != 200:
            raise Exception(f"Failed to list events: {events_response.text}")

        data = events_response.json()
        return data.get("items", [])


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


# ADR-046: Calendar response models
class CalendarEventResponse(BaseModel):
    """Google Calendar event info."""
    id: str
    title: str
    start: str  # ISO datetime
    end: str  # ISO datetime
    attendees: list[dict] = []
    location: Optional[str] = None
    description: Optional[str] = None
    meeting_link: Optional[str] = None
    recurring: bool = False


class CalendarEventsListResponse(BaseModel):
    """List of calendar events."""
    events: list[CalendarEventResponse]
    calendar_id: str


# ADR-072: Platform content response models
class PlatformContentItem(BaseModel):
    """A single synced content item from platform_content."""
    id: str
    content: str
    content_type: Optional[str] = None  # message, thread_parent, email, page
    resource_id: str
    resource_name: Optional[str] = None
    source_timestamp: Optional[str] = None
    fetched_at: str  # ADR-072: platform_content uses fetched_at
    retained: bool = False  # ADR-072: retention flag
    retained_reason: Optional[str] = None  # ADR-072: why retained (deliverable_execution, signal_processing, tp_session)
    retained_at: Optional[str] = None  # ADR-072: when marked retained
    expires_at: Optional[str] = None  # ADR-072: for ephemeral content, when it expires
    metadata: dict[str, Any] = {}


class PlatformContentResponse(BaseModel):
    """ADR-072: Synced content from platform_content for a platform."""
    items: list[PlatformContentItem]
    total_count: int
    retained_count: int = 0  # ADR-072: count of retained items (accumulation visibility)
    freshest_at: Optional[str] = None
    platform: str


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
    content_stored: int = 0  # ADR-072: items stored to platform_content
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
            "id, platform, status, metadata, last_synced_at, created_at"
        ).eq("user_id", user_id).execute()

        integrations = []
        for row in result.data or []:
            metadata = row.get("metadata", {}) or {}
            integrations.append(IntegrationResponse(
                id=row["id"],
                provider=row["platform"],  # ADR-058: DB column is 'platform'
                status=row["status"],
                workspace_name=metadata.get("workspace_name"),
                last_used_at=row.get("last_synced_at"),  # ADR-058: column renamed
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
        integrations_result = auth.client.table("platform_connections").select(
            "id, platform, status, metadata, landscape, created_at"
        ).eq("user_id", user_id).execute()

        if not integrations_result.data:
            return IntegrationsSummaryResponse(platforms=[], total_deliverables=0)

        platforms = []
        seen_providers: set[str] = set()
        from datetime import timedelta

        for integration in integrations_result.data:
            provider = integration["platform"]  # ADR-058: DB column is 'platform'
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

            # Count recent activity from platform_content (last 7 days)
            # ADR-072: platform_content uses fetched_at
            seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
            activity_result = auth.client.table("platform_content").select(
                "id", count="exact"
            ).eq("user_id", user_id).eq(
                "platform", provider
            ).gte("fetched_at", seven_days_ago).execute()
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
            seen_providers.add(provider)

        # ADR-046/ADR-058: Provider alias — gmail row may also have calendar capability.
        # If a 'gmail' row has 'calendar' in capabilities and no 'google' row exists yet,
        # emit a synthetic 'google' entry so the sidebar Calendar dot shows as connected.
        if "gmail" in seen_providers and "google" not in seen_providers:
            gmail_integration = next(
                (i for i in integrations_result.data if i["platform"] == "gmail"), None
            )
            if gmail_integration:
                gmail_meta = gmail_integration.get("metadata", {}) or {}
                capabilities = gmail_meta.get("capabilities", [])
                # Treat missing capabilities as having both (our scopes always include calendar)
                has_calendar = "calendar" in capabilities or not capabilities
                if has_calendar:
                    platforms.append(PlatformSummary(
                        provider="google",
                        status=gmail_integration["status"],
                        workspace_name=gmail_meta.get("workspace_name"),
                        connected_at=gmail_integration["created_at"],
                        resource_count=0,
                        resource_type="calendars",
                        deliverable_count=0,
                        activity_7d=0,
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

    # ADR-058: gmail may be stored as 'google' and vice versa (OAuth provider alias)
    PROVIDER_ALIASES = {"gmail": ["gmail", "google"], "google": ["google", "gmail"]}
    providers_to_try = PROVIDER_ALIASES.get(provider, [provider])

    try:
        row = None
        for p in providers_to_try:
            result = auth.client.table("platform_connections").select(
                "id, platform, status, metadata, last_synced_at, created_at"
            ).eq("user_id", user_id).eq("platform", p).execute()
            if result.data:
                row = result.data[0]
                break

        if not row:
            raise HTTPException(status_code=404, detail=f"Integration not found: {provider}")

        metadata = row.get("metadata", {}) or {}

        return IntegrationResponse(
            id=row["id"],
            provider=row["platform"],  # ADR-058: DB column is 'platform'
            status=row["status"],
            workspace_name=metadata.get("workspace_name"),
            last_used_at=row.get("last_synced_at"),  # ADR-058: column renamed
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

    # Check if integration exists
    result = auth.client.table("platform_connections").select(
        "id, status, metadata, updated_at"
    ).eq("user_id", user_id).eq("platform", provider).limit(1).execute()

    if not result.data:
        return IntegrationHealthResponse(
            provider=provider,
            status="unhealthy",
            errors=[f"No {provider} integration found. Connect it first."],
            recommendations=[f"Go to Settings → Integrations → Connect {provider}"]
        )

    integration = result.data[0]

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

    try:
        # Delete integration (cascade will handle export preferences)
        result = auth.client.table("platform_connections").delete().eq(
            "user_id", user_id
        ).eq("platform", provider).execute()

        if not result.data:
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

            integration = auth.client.table("platform_connections").select(
                "id, credentials_encrypted, refresh_token_encrypted, metadata, status"
            ).eq("user_id", user_id).eq("platform", provider).limit(1).execute()

            if not integration.data:
                raise HTTPException(
                    status_code=404,
                    detail=f"No {provider} integration found. Please connect first."
                )

            if integration.data[0]["status"] != IntegrationStatus.ACTIVE.value:
                raise HTTPException(
                    status_code=400,
                    detail=f"{provider} integration is {integration.data[0]['status']}. Please reconnect."
                )

            integration_id = integration.data[0]["id"]
            token_manager = get_token_manager()

            # Decrypt tokens
            access_token = token_manager.decrypt(integration.data[0]["credentials_encrypted"])
            refresh_token = token_manager.decrypt(integration.data[0]["refresh_token_encrypted"]) if integration.data[0].get("refresh_token_encrypted") else None

            # Build metadata, adding refresh_token for Gmail (ADR-029)
            metadata = integration.data[0].get("metadata", {}) or {}
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
        ).eq("id", request.deliverable_version_id).limit(1).execute()

        if not version.data:
            raise HTTPException(status_code=404, detail="Deliverable version not found")

        # Get deliverable title
        deliverable = auth.client.table("deliverables").select(
            "title"
        ).eq("id", version.data[0]["deliverable_id"]).limit(1).execute()

        content = version.data[0].get("final_content") or version.data[0].get("draft_content", "")
        title = deliverable.data[0]["title"] if deliverable.data else "YARNNN Export"

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
                "deliverable_id": version.data[0]["deliverable_id"]
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

        # ADR-050: Fetch pages via MCP Gateway (Node.js), not Python MCP client
        from services.mcp_gateway import call_platform_tool, is_gateway_available

        if not is_gateway_available():
            raise HTTPException(
                status_code=503,
                detail="MCP Gateway not available. Please try again later."
            )

        result = await call_platform_tool(
            provider="notion",
            tool="notion-search",
            args={"query": query or ""},
            token=access_token,
            metadata=integration.data[0].get("metadata"),
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Notion search failed: {result.get('error', 'Unknown error')}"
            )

        # Transform to response format - Gateway returns results in 'result' field
        raw_pages = result.get("result", {}).get("results", [])
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

        logger.info(f"[INTEGRATIONS] User {user_id} listed {len(pages)} Notion pages via MCP Gateway")

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


# =============================================================================
# Google Designated Settings (ADR-050 Streamlined Pattern)
# =============================================================================

class GoogleDesignatedSettingsRequest(BaseModel):
    """Request to set designated settings for Google (Gmail/Calendar)."""
    designated_calendar_id: Optional[str] = None
    designated_calendar_name: Optional[str] = None
    designated_email: Optional[str] = None  # ADR-051: User's email for draft recipients


class GoogleDesignatedSettingsResponse(BaseModel):
    """Response with Google designated settings."""
    success: bool
    designated_calendar_id: Optional[str] = None
    designated_calendar_name: Optional[str] = None
    designated_email: Optional[str] = None  # ADR-051: User's email for draft recipients
    message: str


@router.get("/integrations/google/designated-settings")
async def get_google_designated_settings(auth: UserClient) -> GoogleDesignatedSettingsResponse:
    """
    Get the user's designated settings for Google (Calendar).

    ADR-050: Streamlined pattern - user designates a calendar as default
    for TP-created events (like Slack DM to self, Notion designated page).
    """
    user_id = auth.user_id

    try:
        # Try google first, then gmail for legacy
        integration = None
        for provider in ["google", "gmail"]:
            result = auth.client.table("platform_connections").select(
                "id, metadata, status"
            ).eq("user_id", user_id).eq("platform", provider).limit(1).execute()
            if result.data:
                integration = result.data[0]
                break

        if not integration:
            raise HTTPException(
                status_code=404,
                detail="No Google integration found. Please connect first."
            )

        metadata = integration.get("metadata") or {}

        return GoogleDesignatedSettingsResponse(
            success=True,
            designated_calendar_id=metadata.get("designated_calendar_id"),
            designated_calendar_name=metadata.get("designated_calendar_name"),
            designated_email=metadata.get("email"),  # ADR-051: From OAuth or explicit setting
            message="Settings retrieved"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTEGRATIONS] Failed to get Google designated settings for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get settings: {str(e)}")


@router.put("/integrations/google/designated-settings")
async def set_google_designated_settings(
    request: GoogleDesignatedSettingsRequest,
    auth: UserClient
) -> GoogleDesignatedSettingsResponse:
    """
    Set the user's designated settings for Google (Calendar).

    ADR-050: Streamlined pattern - TP will use designated_calendar_id
    as default for creating events.
    """
    user_id = auth.user_id

    try:
        # Try google first, then gmail for legacy
        integration = None
        provider_found = None
        for provider in ["google", "gmail"]:
            result = auth.client.table("platform_connections").select(
                "id, metadata, status"
            ).eq("user_id", user_id).eq("platform", provider).limit(1).execute()
            if result.data:
                integration = result.data[0]
                provider_found = provider
                break

        if not integration:
            raise HTTPException(
                status_code=404,
                detail="No Google integration found. Please connect first."
            )

        if integration["status"] != IntegrationStatus.ACTIVE.value:
            raise HTTPException(
                status_code=400,
                detail=f"Google integration is {integration['status']}. Please reconnect."
            )

        # Update metadata with designated settings
        metadata = integration.get("metadata") or {}
        if request.designated_calendar_id:
            metadata["designated_calendar_id"] = request.designated_calendar_id
        if request.designated_calendar_name:
            metadata["designated_calendar_name"] = request.designated_calendar_name
        if request.designated_email:
            metadata["email"] = request.designated_email  # ADR-051: Allow explicit email setting

        auth.client.table("platform_connections").update({
            "metadata": metadata
        }).eq("id", integration["id"]).execute()

        if request.designated_calendar_id:
            logger.info(f"[INTEGRATIONS] User {user_id} set Google designated calendar: {request.designated_calendar_id}")
        if request.designated_email:
            logger.info(f"[INTEGRATIONS] User {user_id} set Google designated email: {request.designated_email}")

        return GoogleDesignatedSettingsResponse(
            success=True,
            designated_calendar_id=metadata.get("designated_calendar_id"),
            designated_calendar_name=metadata.get("designated_calendar_name"),
            designated_email=metadata.get("email"),
            message="Settings updated"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTEGRATIONS] Failed to set Google designated settings for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")


@router.delete("/integrations/google/designated-settings")
async def clear_google_designated_settings(auth: UserClient) -> GoogleDesignatedSettingsResponse:
    """
    Clear the user's designated settings for Google.
    """
    user_id = auth.user_id

    try:
        # Try google first, then gmail for legacy
        integration = None
        for provider in ["google", "gmail"]:
            result = auth.client.table("platform_connections").select(
                "id, metadata"
            ).eq("user_id", user_id).eq("platform", provider).limit(1).execute()
            if result.data:
                integration = result.data[0]
                break

        if not integration:
            raise HTTPException(
                status_code=404,
                detail="No Google integration found."
            )

        # Remove designated settings from metadata
        # Note: We don't clear email here - that should remain from OAuth
        metadata = integration.get("metadata") or {}
        metadata.pop("designated_calendar_id", None)
        metadata.pop("designated_calendar_name", None)

        auth.client.table("platform_connections").update({
            "metadata": metadata
        }).eq("id", integration["id"]).execute()

        logger.info(f"[INTEGRATIONS] User {user_id} cleared Google designated settings (email preserved)")

        return GoogleDesignatedSettingsResponse(
            success=True,
            designated_calendar_id=None,
            designated_calendar_name=None,
            designated_email=metadata.get("email"),  # Preserve email
            message="Settings cleared"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTEGRATIONS] Failed to clear Google designated settings for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear settings: {str(e)}")


# =============================================================================
# Resource Discovery - Google Calendar Events (ADR-046)
# =============================================================================

class CalendarListResponse(BaseModel):
    """List of available calendars."""
    calendars: list[dict]


@router.get("/integrations/google/calendars")
async def list_google_calendars(
    auth: UserClient
) -> CalendarListResponse:
    """
    ADR-046: List Google Calendars the user has access to.

    Used for:
    - Calendar selection in deliverable creation
    - Meeting prep source configuration
    """
    user_id = auth.user_id
    import os

    try:
        # Get user's Google integration (try google first, then gmail for legacy)
        integration = auth.client.table("platform_connections").select(
            "id, credentials_encrypted, refresh_token_encrypted, status, metadata"
        ).eq("user_id", user_id).eq("platform", "google").limit(1).execute()

        if not integration.data:
            # Try legacy gmail provider
            integration = auth.client.table("platform_connections").select(
                "id, credentials_encrypted, refresh_token_encrypted, status, metadata"
            ).eq("user_id", user_id).eq("platform", "gmail").limit(1).execute()

        if not integration.data:
            raise HTTPException(
                status_code=404,
                detail="No Google integration found. Please connect first."
            )

        if integration.data[0]["status"] != IntegrationStatus.ACTIVE.value:
            raise HTTPException(
                status_code=400,
                detail=f"Google integration is {integration.data[0]['status']}. Please reconnect."
            )

        # Check capabilities
        metadata = integration.data[0].get("metadata", {}) or {}
        capabilities = metadata.get("capabilities", [])
        if capabilities and "calendar" not in capabilities:
            raise HTTPException(
                status_code=400,
                detail="Calendar access not granted. Please reconnect with calendar permissions."
            )

        # Get credentials
        token_manager = get_token_manager()
        refresh_token_encrypted = integration.data[0].get("refresh_token_encrypted")
        if not refresh_token_encrypted:
            raise HTTPException(
                status_code=400,
                detail="Missing refresh token. Please reconnect Google integration."
            )

        refresh_token = token_manager.decrypt(refresh_token_encrypted)
        client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")

        # Fetch calendars
        raw_calendars = await _fetch_google_calendars(
            user_id=user_id,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token
        )

        calendars = [
            {
                "id": cal.get("id"),
                "summary": cal.get("summary", "Untitled Calendar"),
                "primary": cal.get("primary", False),
                "access_role": cal.get("accessRole"),
                "background_color": cal.get("backgroundColor"),
            }
            for cal in raw_calendars
        ]

        logger.info(f"[INTEGRATIONS] User {user_id} listed {len(calendars)} Google calendars")

        return CalendarListResponse(calendars=calendars)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTEGRATIONS] Failed to list Google calendars for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list calendars: {str(e)}")


@router.get("/integrations/google/events")
async def list_google_calendar_events(
    auth: UserClient,
    calendar_id: str = Query("primary", description="Calendar ID to fetch events from"),
    time_min: Optional[str] = Query(None, description="Start time (RFC3339)"),
    time_max: Optional[str] = Query(None, description="End time (RFC3339)"),
    max_results: int = Query(50, description="Maximum events to return", le=250)
) -> CalendarEventsListResponse:
    """
    ADR-046: List calendar events for meeting prep and context.

    Used for:
    - Meeting prep deliverable context
    - Weekly calendar preview
    - 1:1 prep with attendee info

    Default time window is now to 7 days from now.
    """
    user_id = auth.user_id
    import os

    try:
        # Get user's Google integration (try google first, then gmail for legacy)
        integration = auth.client.table("platform_connections").select(
            "id, credentials_encrypted, refresh_token_encrypted, status, metadata"
        ).eq("user_id", user_id).eq("platform", "google").limit(1).execute()

        if not integration.data:
            # Try legacy gmail provider
            integration = auth.client.table("platform_connections").select(
                "id, credentials_encrypted, refresh_token_encrypted, status, metadata"
            ).eq("user_id", user_id).eq("platform", "gmail").limit(1).execute()

        if not integration.data:
            raise HTTPException(
                status_code=404,
                detail="No Google integration found. Please connect first."
            )

        if integration.data[0]["status"] != IntegrationStatus.ACTIVE.value:
            raise HTTPException(
                status_code=400,
                detail=f"Google integration is {integration.data[0]['status']}. Please reconnect."
            )

        # Check capabilities
        metadata = integration.data[0].get("metadata", {}) or {}
        capabilities = metadata.get("capabilities", [])
        if capabilities and "calendar" not in capabilities:
            raise HTTPException(
                status_code=400,
                detail="Calendar access not granted. Please reconnect with calendar permissions."
            )

        # Get credentials
        token_manager = get_token_manager()
        refresh_token_encrypted = integration.data[0].get("refresh_token_encrypted")
        if not refresh_token_encrypted:
            raise HTTPException(
                status_code=400,
                detail="Missing refresh token. Please reconnect Google integration."
            )

        refresh_token = token_manager.decrypt(refresh_token_encrypted)
        client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")

        # Fetch events
        raw_events = await _fetch_google_calendar_events(
            user_id=user_id,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            calendar_id=calendar_id,
            time_min=time_min,
            time_max=time_max,
            max_results=max_results
        )

        # Transform to response format
        events = []
        for event in raw_events:
            # Extract start/end time (can be date or dateTime)
            start = event.get("start", {})
            end = event.get("end", {})
            start_time = start.get("dateTime") or start.get("date", "")
            end_time = end.get("dateTime") or end.get("date", "")

            # Extract attendees
            attendees = [
                {
                    "email": a.get("email"),
                    "display_name": a.get("displayName"),
                    "response_status": a.get("responseStatus"),
                    "organizer": a.get("organizer", False),
                    "self": a.get("self", False),
                }
                for a in event.get("attendees", [])
            ]

            # Extract meeting link (Google Meet, Zoom, etc.)
            meeting_link = None
            if event.get("hangoutLink"):
                meeting_link = event.get("hangoutLink")
            elif event.get("conferenceData", {}).get("entryPoints"):
                for entry in event["conferenceData"]["entryPoints"]:
                    if entry.get("entryPointType") == "video":
                        meeting_link = entry.get("uri")
                        break

            events.append(CalendarEventResponse(
                id=event.get("id", ""),
                title=event.get("summary", "Untitled Event"),
                start=start_time,
                end=end_time,
                attendees=attendees,
                location=event.get("location"),
                description=event.get("description"),
                meeting_link=meeting_link,
                recurring=bool(event.get("recurringEventId")),
            ))

        logger.info(f"[INTEGRATIONS] User {user_id} listed {len(events)} calendar events from {calendar_id}")

        return CalendarEventsListResponse(events=events, calendar_id=calendar_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTEGRATIONS] Failed to list calendar events for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list events: {str(e)}")


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
        integration = auth.client.table("platform_connections").select(
            "id, refresh_token_encrypted, status"
        ).eq("user_id", user_id).eq("platform", "gmail").limit(1).execute()

        if not integration.data:
            raise HTTPException(
                status_code=404,
                detail="No Gmail integration found. Please connect first."
            )

        if integration.data[0]["status"] != IntegrationStatus.ACTIVE.value:
            raise HTTPException(
                status_code=400,
                detail=f"Gmail integration is {integration.data[0]['status']}. Please reconnect."
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
        existing = service_client.table("platform_connections").select("id").eq(
            "user_id", token_data["user_id"]
        ).eq("platform", provider).execute()

        if existing.data:
            user_id = token_data["user_id"]

            # Update existing - clear landscape to force rediscovery from new workspace
            service_client.table("platform_connections").update({
                "credentials_encrypted": token_data["credentials_encrypted"],
                "refresh_token_encrypted": token_data.get("refresh_token_encrypted"),
                "metadata": token_data["metadata"],
                "status": token_data["status"],
                "last_error": None,
                "updated_at": datetime.utcnow().isoformat(),
                # Clear old landscape data so it's refetched from new workspace
                "landscape": None,
                "landscape_discovered_at": None,
            }).eq("id", existing.data[0]["id"]).execute()

            # Purge stale data from old workspace (ADR-072 tables)
            # Delete platform_content from this platform
            service_client.table("platform_content").delete().eq(
                "user_id", user_id
            ).eq("platform", provider).execute()

            # Delete sync_registry entries for this platform
            service_client.table("sync_registry").delete().eq(
                "user_id", user_id
            ).eq("platform", provider).execute()

            # ADR-059: user_context has no inferred/platform-sourced entries; nothing to delete.

            # Invalidate MCP session so it gets recreated with new credentials
            # This is critical when switching workspaces (e.g., different Slack team)
            try:
                mcp_manager = get_mcp_manager()
                import asyncio
                asyncio.create_task(mcp_manager.close_session(user_id, provider))
                logger.info(f"[INTEGRATIONS] Invalidated MCP session for {user_id}:{provider}")
            except Exception as e:
                logger.warning(f"[INTEGRATIONS] Could not invalidate MCP session: {e}")

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
    if provider not in ["gmail", "slack", "notion", "google"]:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    user_id = auth.user_id

    # ADR-058: gmail may be stored as 'google' and vice versa
    PROVIDER_ALIASES = {"gmail": ["gmail", "google"], "google": ["google", "gmail"]}
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
        # Discover landscape from provider
        landscape_data = await _discover_landscape(resolved_provider, user_id, integration.data[0])

        # Note: We do NOT auto-select sources here.
        # User must explicitly select sources in the modal, gated by tier limits.
        # This builds trust by showing the landscape, then letting user choose what to sync.

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
        "resource_id, resource_name, last_synced_at, item_count"
    ).eq("user_id", user_id).eq("platform", resolved_provider).execute()

    sync_by_id = {s["resource_id"]: s for s in (sync_result.data or [])}

    # Build resource list with sync status
    resources = []
    for resource in landscape_data.get("resources", []):
        resource_id = resource.get("id")
        sync_data = sync_by_id.get(resource_id, {})

        # Determine coverage state from sync data
        coverage_state = "covered" if sync_data.get("last_synced_at") else "uncovered"

        resources.append(LandscapeResourceResponse(
            id=resource_id,
            name=resource.get("name", "Unknown"),
            resource_type=resource.get("type", "unknown"),
            coverage_state=coverage_state,
            last_extracted_at=sync_data.get("last_synced_at"),
            items_extracted=sync_data.get("item_count", 0),
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


# =============================================================================
# ADR-052: Platform Context (Synced Content)
# =============================================================================

@router.get("/integrations/{provider}/context")
async def get_platform_context(
    provider: str,
    limit: int = Query(20, ge=1, le=100, description="Max items to return"),
    resource_id: Optional[str] = Query(None, description="Filter by specific resource"),
    auth: UserClient = None
) -> PlatformContentResponse:
    """
    ADR-072: Get synced content from platform_content for a platform.

    This is the actual platform content (messages, emails, pages) that TP knows about.
    Different from landscape (which shows available resources) and memories (user-stated facts).

    Returns recent synced content, ordered by source_timestamp descending.
    """
    if provider not in ["gmail", "slack", "notion", "calendar"]:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    user_id = auth.user_id
    now = datetime.utcnow().isoformat()

    # Build query (ADR-072: include retained OR non-expired)
    query = (
        auth.client.table("platform_content")
        .select("*")
        .eq("user_id", user_id)
        .eq("platform", provider)
        .or_(f"retained.eq.true,expires_at.gt.{now}")
        .order("fetched_at", desc=True)
        .limit(limit)
    )

    if resource_id:
        query = query.eq("resource_id", resource_id)

    result = query.execute()

    # Get total count
    count_query = (
        auth.client.table("platform_content")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("platform", provider)
        .or_(f"retained.eq.true,expires_at.gt.{now}")
    )
    if resource_id:
        count_query = count_query.eq("resource_id", resource_id)

    count_result = count_query.execute()
    total_count = count_result.count or 0

    # ADR-072: Get retained count for accumulation visibility
    retained_count_query = (
        auth.client.table("platform_content")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("platform", provider)
        .eq("retained", True)
    )
    if resource_id:
        retained_count_query = retained_count_query.eq("resource_id", resource_id)
    retained_count_result = retained_count_query.execute()
    retained_count = retained_count_result.count or 0

    # Build response
    items = []
    freshest_at = None

    for row in result.data or []:
        source_ts = row.get("source_timestamp")
        if source_ts and (freshest_at is None or source_ts > freshest_at):
            freshest_at = source_ts

        items.append(PlatformContentItem(
            id=row["id"],
            content=row["content"][:500] if row["content"] else "",  # Truncate for list view
            content_type=row.get("content_type"),
            resource_id=row["resource_id"],
            resource_name=row.get("resource_name"),
            source_timestamp=source_ts,
            fetched_at=row["fetched_at"],  # ADR-072: Use fetched_at
            retained=row.get("retained", False),  # ADR-072: retention flag
            retained_reason=row.get("retained_reason"),  # ADR-072: why retained
            retained_at=row.get("retained_at"),  # ADR-072: when marked retained
            expires_at=row.get("expires_at"),  # ADR-072: expiry for ephemeral content
            metadata=row.get("metadata", {}),
        ))

    logger.info(f"[INTEGRATIONS] User {user_id} fetched {len(items)} content items from {provider} (retained={retained_count})")

    return PlatformContentResponse(
        items=items,
        total_count=total_count,
        retained_count=retained_count,  # ADR-072: accumulation visibility
        freshest_at=freshest_at,
        platform=provider,
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
    mcp_manager = get_mcp_manager()  # For Slack/Notion (MCP protocol)

    if provider in ("gmail", "google"):
        # Gmail/Calendar use GoogleAPIClient (NOT MCP)
        from integrations.core.google_client import get_google_client
        google_client = get_google_client()

        # Get Google credentials (OAUTH_CONFIGS values are OAuthConfig objects, not dicts)
        google_config = OAUTH_CONFIGS.get("google") or OAUTH_CONFIGS["gmail"]
        client_id = google_config.client_id
        client_secret = google_config.client_secret
        refresh_token = token_manager.decrypt(integration["refresh_token_encrypted"])

        resources = []

        # List Gmail labels via GoogleAPIClient
        labels = await google_client.list_gmail_labels(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token
        )

        for label in labels:
            resources.append({
                "id": label.get("id"),
                "name": label.get("name"),
                "type": "label",
                "metadata": {
                    "type": label.get("type"),  # system, user
                    "messageListVisibility": label.get("messageListVisibility"),
                    "labelListVisibility": label.get("labelListVisibility"),
                    "platform": "gmail",
                }
            })

        # ADR-046: Also list calendars if google provider
        if provider == "google":
            try:
                calendars = await _fetch_google_calendars(
                    user_id=user_id,
                    client_id=client_id,
                    client_secret=client_secret,
                    refresh_token=refresh_token
                )
                for cal in calendars:
                    resources.append({
                        "id": cal.get("id"),
                        "name": cal.get("summary", "Untitled Calendar"),
                        "type": "calendar",
                        "metadata": {
                            "primary": cal.get("primary", False),
                            "accessRole": cal.get("accessRole"),
                            "platform": "calendar",
                        }
                    })
            except Exception as e:
                logger.warning(f"[INTEGRATIONS] Failed to list calendars for {user_id}: {e}")
                # Continue without calendars - user may not have calendar scope

        return {"resources": resources}

    elif provider == "slack":
        # Get Slack credentials
        bot_token = token_manager.decrypt(integration["credentials_encrypted"])
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
        # ADR-050: Notion uses Direct API (not MCP Gateway — MCP Gateway only supports Slack)
        from integrations.core.notion_client import get_notion_client

        # Get Notion credentials
        auth_token = token_manager.decrypt(integration["credentials_encrypted"])

        try:
            notion_client = get_notion_client()
            # Empty query returns all accessible pages and databases
            pages = await notion_client.search(access_token=auth_token, query="", page_size=100)
        except Exception as e:
            logger.warning(f"[INTEGRATIONS] Notion search failed during landscape discovery: {e}")
            return {"resources": []}

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
    """User's tier limits and current usage (ADR-053)."""
    tier: str
    limits: dict[str, Any]  # Includes sync_frequency (str) and counts (int)
    usage: dict[str, int]
    next_sync: Optional[str] = None  # ISO timestamp of next scheduled sync


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

    ADR-053: Returns platform resource limits based on user tier,
    current usage counts, and next scheduled sync time.

    Response includes:
    - tier: "free" | "starter" | "pro"
    - limits: slack_channels, gmail_labels, notion_pages, calendars,
              total_platforms, sync_frequency, tp_conversations_per_month,
              active_deliverables
    - usage: Current usage counts for each resource
    - next_sync: ISO timestamp of next scheduled platform sync
    """
    from services.platform_limits import get_usage_summary

    # Get user's timezone from user_context (ADR-059: timezone stored as key='timezone')
    user_tz = "UTC"
    try:
        tz_result = auth.client.table("user_context").select(
            "value"
        ).eq("user_id", auth.user_id).eq("key", "timezone").maybe_single().execute()
        if tz_result.data:
            user_tz = tz_result.data.get("value", "UTC")
    except Exception:
        pass

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

    # Validate against limits
    valid, message, allowed_ids = validate_sources_update(
        auth.client, user_id, provider, request.source_ids
    )

    # Get integration
    integration = auth.client.table("platform_connections").select(
        "id, landscape"
    ).eq("user_id", user_id).eq("platform", provider).limit(1).execute()

    if not integration.data:
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
            selected_sources.append({
                "id": source_id,
                "name": r.get("name", source_id),
                "type": r.get("type", "unknown"),
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

    PROVIDER_ALIASES = {"gmail": ["gmail", "google"], "google": ["google", "gmail"]}
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
        "gmail": "gmail_labels",
        "notion": "notion_pages",
        "google": "gmail_labels",
        "calendar": "calendars",
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
    Trigger an on-demand sync for a platform.

    ADR-043 / DECISION-001: Syncs selected sources only.
    Runs in background, returns immediately.
    """
    from services.job_queue import enqueue_job

    user_id = auth.user_id

    PROVIDER_ALIASES = {"gmail": ["gmail", "google"], "google": ["google", "gmail"]}
    providers_to_try = PROVIDER_ALIASES.get(provider, [provider])

    # Verify integration exists (try aliases)
    integration_row = None
    for p in providers_to_try:
        result = auth.client.table("platform_connections").select(
            "id, status, landscape"
        ).eq("user_id", user_id).eq("platform", p).limit(1).execute()
        if result.data:
            integration_row = result.data[0]
            break

    if not integration_row:
        raise HTTPException(status_code=404, detail=f"No {provider} integration found")

    if integration_row["status"] != "active":
        raise HTTPException(status_code=400, detail=f"{provider} integration is not active")

    # Get selected sources
    landscape = integration_row.get("landscape", {}) or {}
    selected = landscape.get("selected_sources", [])

    if not selected:
        return {
            "success": False,
            "message": "No sources selected. Please select sources first.",
        }

    # Enqueue sync job
    job_id = await enqueue_job(
        "platform_sync",
        user_id=user_id,
        provider=provider,
        selected_sources=[s["id"] for s in selected],
    )

    logger.info(f"[INTEGRATIONS] User {user_id} triggered {provider} sync, job={job_id}")

    return {
        "success": True,
        "job_id": job_id,
        "message": f"Sync started for {len(selected)} {provider} sources",
        "sources_count": len(selected),
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

    # Verify integration exists
    integration = auth.client.table("platform_connections").select(
        "id, status"
    ).eq("user_id", user_id).eq("platform", provider).limit(1).execute()

    if not integration.data:
        raise HTTPException(status_code=404, detail=f"No {provider} integration found")

    # Get sync registry entries for this platform
    sync_result = auth.client.table("sync_registry").select(
        "resource_id, resource_name, last_synced_at, item_count, source_latest_at"
    ).eq("user_id", user_id).eq("platform", provider).execute()

    now = datetime.now(timezone.utc)
    synced_resources = []
    stale_count = 0

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

        synced_resources.append({
            "resource_id": entry.get("resource_id"),
            "resource_name": entry.get("resource_name"),
            "last_synced": last_synced,
            "freshness_status": freshness_status,
            "items_synced": entry.get("item_count", 0),
        })

    return {
        "platform": provider,
        "synced_resources": synced_resources,
        "stale_count": stale_count,
    }
