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
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Request
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
# ContextImportAgent DELETED (ADR-153 + ADR-156: platform data flows through task execution)

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

# _process_import_job_background DELETED (ADR-153 + ADR-156)
# Platform data flows through task execution (Monitor Slack, Monitor Notion),
# not background import jobs. See ADR-153 for the explicit sunset decision.


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
# Legacy Import Compatibility Models
# Retained only so deprecated endpoints and response shapes stay stable.
# =============================================================================

class ImportConfigRequest(BaseModel):
    """Legacy configuration shape for deprecated import endpoints."""
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
    """Legacy request shape for deprecated context import endpoint."""
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
    """Legacy status shape for deprecated import jobs."""
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
    """Legacy list shape for deprecated import jobs."""
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

        # Derive last_used_at from resource bookkeeping in sync_registry
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

        # ADR-131: Google/Gmail removed. ADR-147: GitHub added. ADR-183: Commerce added.
        SUPPORTED_PLATFORMS = {"slack", "notion", "github", "commerce"}

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
            if provider not in SUPPORTED_PLATFORMS:
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
                "github": "repositories",
                "commerce": "products",
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

        # Emit platform summaries in stable order
        for provider in ("slack", "notion", "github"):
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
) -> dict:
    """DEPRECATED (ADR-153/156): Import jobs sunset. Returns empty list."""
    return {"jobs": [], "deprecated": True}


@router.get("/integrations/import/{job_id}")
async def get_import_job(job_id: str, auth: UserClient) -> dict:
    """DEPRECATED (ADR-153/156): Import jobs sunset."""
    return {"deprecated": True, "message": "Import jobs have been replaced by monitoring tasks."}


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

        # Derive last_used_at from resource bookkeeping in sync_registry
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
) -> dict:
    """
    DEPRECATED (ADR-153 + ADR-156): Platform data flows through task execution.
    Use Monitor Notion task type instead of import jobs.

    Retained as endpoint to prevent frontend 404s. Returns deprecation message.
    """
    # ADR-153 + ADR-156: Import jobs sunset.
    # Platform data flows through task execution (Monitor Notion task type).
    return {
        "deprecated": True,
        "message": "Import jobs have been replaced by digest tasks. Create a 'notion-digest' task instead.",
    }


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
# Platform Digest Task Scaffolding
# =============================================================================

_PROVIDER_TO_DIGEST = {
    "slack": {"type_key": "slack-digest", "slug": "slack-sync", "title": "Slack Sync", "bot_slug": "slack-bot"},
    "notion": {"type_key": "notion-digest", "slug": "notion-sync", "title": "Notion Sync", "bot_slug": "notion-bot"},
    "github": {"type_key": "github-digest", "slug": "github-sync", "title": "GitHub Sync", "bot_slug": "github-bot"},
}


async def _scaffold_platform_digest_task(
    client: Any,
    user_id: str,
    provider: str,
    smart_selected: list[dict],
) -> None:
    """Auto-create a platform digest task when a platform is connected.

    The task is created as paused with no sources selected — the user picks
    sources on the task page and activates. Idempotent: skips if the task
    slug already exists.
    """
    digest_info = _PROVIDER_TO_DIGEST.get(provider)
    if not digest_info:
        return

    slug = digest_info["slug"]

    # Idempotent: skip if already exists
    existing = client.table("tasks").select("id").eq("user_id", user_id).eq("slug", slug).execute()
    if existing.data:
        logger.info(f"[INTEGRATIONS] Platform digest task '{slug}' already exists, skipping scaffold")
        return

    from services.task_types import build_task_md_from_type, build_deliverable_md_from_type
    from services.task_workspace import TaskWorkspace
    from services.schedule_utils import calculate_next_run_at, get_user_timezone

    user_timezone = get_user_timezone(client, user_id)
    now = datetime.utcnow()

    row = {
        "user_id": user_id,
        "slug": slug,
        "mode": "recurring",
        "status": "paused",  # User must pick sources and activate
        "schedule": "daily",
        "next_run_at": None,  # No next run until activated
    }
    insert_result = client.table("tasks").insert(row).execute()
    if not insert_result.data:
        raise RuntimeError(f"Failed to insert platform digest task: {slug}")

    task_md = build_task_md_from_type(
        type_key=digest_info["type_key"],
        title=digest_info["title"],
        slug=slug,
        schedule="daily",
        delivery="none",
        agent_slugs=[digest_info["bot_slug"]],
    )
    tw = TaskWorkspace(client, user_id, slug)
    await tw.write("TASK.md", task_md, summary=f"Platform digest task: {digest_info['title']}")

    deliverable_md = build_deliverable_md_from_type(digest_info["type_key"])
    if deliverable_md:
        await tw.write("DELIVERABLE.md", deliverable_md, summary=f"Quality contract: {digest_info['title']}")

    logger.info(
        f"[INTEGRATIONS] Scaffolded platform digest task '{slug}' (paused) "
        f"for {provider} user {user_id[:8]}"
    )


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

        # Reactivate the platform-bot agent if it was previously paused (e.g. by
        # clear_integrations). ADR-140 roster invariant: bots are part of the
        # pre-scaffolded roster, so we flip status rather than re-create.
        _PROVIDER_TO_BOT_ROLE = {
            "slack": "slack_bot",
            "notion": "notion_bot",
            "github": "github_bot",
        }
        bot_role = _PROVIDER_TO_BOT_ROLE.get(provider)
        if bot_role:
            try:
                service_client.table("agents").update(
                    {"status": "active"}
                ).eq("user_id", token_data["user_id"]).eq("role", bot_role).eq(
                    "status", "paused"
                ).execute()
            except Exception as reactivate_err:
                logger.warning(
                    f"[INTEGRATIONS] Failed to reactivate {bot_role} for "
                    f"{token_data['user_id']}: {reactivate_err}"
                )

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
                    # ADR-172: No source limits — max_sources is a UX heuristic only
                    max_sources = 50

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

                    # Auto-scaffold a platform digest task (paused, needs source setup).
                    # The user lands on the task page to pick sources and activate.
                    if smart_selected:
                        try:
                            await _scaffold_platform_digest_task(
                                service_client,
                                user_id_for_auto,
                                provider,
                                smart_selected,
                            )
                        except Exception as scaffold_err:
                            logger.warning(
                                f"[INTEGRATIONS] Platform digest task scaffold failed "
                                f"for {provider}: {scaffold_err}"
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
    if provider not in ["slack", "notion", "github"]:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}. Supported: Slack, Notion, GitHub.")

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
            # ADR-079: Smart auto-selection — no tier limit (ADR-172)
            from services.landscape import compute_smart_defaults
            max_sources = 50  # UX heuristic only, not enforcement

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

    # Compute recommended IDs (ADR-079 smart defaults) for UI grouping — no tier limit
    from services.landscape import compute_smart_defaults
    max_sources = 50  # UX heuristic only

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
    """User's balance and subscription status (ADR-172: usage-first billing)."""
    balance_usd: float
    spend_usd: float
    is_subscriber: bool
    subscription_plan: Optional[str] = None
    next_refill: Optional[str] = None


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
    Get user's balance and subscription status (ADR-172: usage-first billing).

    Returns:
    - balance_usd: effective remaining balance (balance - spend since last refill)
    - spend_usd: total token spend this month
    - is_subscriber: whether user has an active Pro subscription
    - subscription_plan: 'pro' | 'pro_yearly' | None
    - next_refill: ISO timestamp of next subscription billing (if subscriber)
    """
    from services.platform_limits import get_usage_summary

    summary = get_usage_summary(auth.client, auth.user_id)

    return UserLimitsResponse(
        balance_usd=summary["balance_usd"],
        spend_usd=summary["spend_usd"],
        is_subscriber=summary["is_subscriber"],
        subscription_plan=summary.get("subscription_plan"),
        next_refill=summary.get("next_refill"),
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
    # ADR-172: No source limits — accept all requested source IDs
    user_id = auth.user_id
    allowed_ids = request.source_ids
    providers_to_try = PROVIDER_ALIASES.get(provider, [provider])

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
        success=True,
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
    Get resource coverage / freshness status for a platform.

    Returns timestamp/error information for each tracked resource.
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


# =============================================================================
# Commerce Connection — ADR-183 (API key auth, not OAuth)
# =============================================================================

class CommerceConnectRequest(BaseModel):
    """Request to connect a commerce platform via API key."""
    api_key: str


@router.post("/integrations/commerce/connect")
async def connect_commerce(
    request: CommerceConnectRequest,
    auth: UserClient,
):
    """
    Connect a commerce platform using API key (ADR-183).

    Unlike OAuth flows (Slack, Notion, GitHub), commerce uses direct API key auth.
    This endpoint validates the key, encrypts it, stores the connection, and
    scaffolds the Commerce Bot + context domains.
    """
    from integrations.core.lemonsqueezy_client import get_commerce_client
    from services.directory_registry import scaffold_context_domain

    user_id = auth.user_id
    token_manager = get_token_manager()
    commerce_client = get_commerce_client()

    # 1. Validate the API key
    try:
        store_info = await commerce_client.validate_key(request.api_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2. Encrypt and store the connection
    encrypted_key = token_manager.encrypt(request.api_key)
    service_client = get_service_client()

    existing = service_client.table("platform_connections").select("id").eq(
        "user_id", user_id
    ).eq("platform", "commerce").execute()

    metadata = {
        "store_name": store_info.get("store_name", ""),
        "email": store_info.get("email", ""),
        "provider": "lemonsqueezy",
    }

    if existing.data:
        service_client.table("platform_connections").update({
            "credentials_encrypted": encrypted_key,
            "metadata": metadata,
            "status": "active",
        }).eq("id", existing.data[0]["id"]).execute()
        connection_id = existing.data[0]["id"]
        logger.info(f"[INTEGRATIONS] Updated commerce connection for {user_id}")
    else:
        insert_result = service_client.table("platform_connections").insert({
            "user_id": user_id,
            "platform": "commerce",
            "credentials_encrypted": encrypted_key,
            "metadata": metadata,
            "status": "active",
        }).execute()
        connection_id = insert_result.data[0]["id"] if insert_result.data else None
        logger.info(f"[INTEGRATIONS] Created commerce connection for {user_id}")

    # 3. Activate Commerce Bot (reactivate if paused)
    service_client.table("agents").update(
        {"status": "active"}
    ).eq("user_id", user_id).eq("role", "commerce_bot").eq(
        "status", "paused"
    ).execute()

    # 4. Scaffold commerce context domains (idempotent)
    await scaffold_context_domain(service_client, user_id, "customers")
    await scaffold_context_domain(service_client, user_id, "revenue")

    return {
        "id": connection_id,
        "platform": "commerce",
        "provider": "lemonsqueezy",
        "status": "active",
        "store_name": metadata.get("store_name"),
    }


# =============================================================================
# Commerce Webhooks — ADR-183 Phase 2
# =============================================================================

@router.post("/webhooks/commerce/lemonsqueezy")
async def handle_commerce_webhook(request: "Request"):
    """
    Handle Lemon Squeezy webhook events for content commerce (ADR-183).

    Writes subscriber/order events directly to workspace files — no intermediate
    staging table (ADR-153 principle). All agents see updated data on next run.

    NOTE: This is for the USER's LS account (content commerce), NOT YARNNN's
    own billing (which uses routes/subscription.py).
    """
    import hashlib
    import hmac
    import json

    from fastapi import Request
    from services.workspace import UserMemory
    from datetime import datetime, timezone

    body = await request.body()
    signature = request.headers.get("X-Signature", "")

    # Verify webhook signature using the commerce connection's webhook secret
    # For Phase 2, we trust the source (LS webhook IPs) — signature verification
    # is added when the user configures their webhook secret in settings.

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_name = payload.get("meta", {}).get("event_name", "")
    custom_data = payload.get("meta", {}).get("custom_data", {})

    # Resolve workspace from custom_data (set during checkout creation)
    # or from the store → platform_connections lookup
    user_id = custom_data.get("user_id")

    if not user_id:
        # Try to find user by store_id from LS payload
        store_id = str(payload.get("data", {}).get("attributes", {}).get("store_id", ""))
        if store_id:
            service_client = get_service_client()
            result = service_client.table("platform_connections").select(
                "user_id"
            ).eq("platform", "commerce").eq("status", "active").execute()

            # Match by store metadata — iterate connections
            for conn in (result.data or []):
                user_id = conn.get("user_id")
                break  # For now, first match (single-user system)

    if not user_id:
        logger.warning(f"[COMMERCE_WEBHOOK] No user_id found for event: {event_name}")
        return {"status": "ok", "message": "No user_id resolved"}

    attrs = payload.get("data", {}).get("attributes", {})
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d %H:%M")

    service_client = get_service_client()
    um = UserMemory(service_client, user_id)

    logger.info(f"[COMMERCE_WEBHOOK] {event_name} for user {user_id}")

    # Route by event type → write to workspace files
    if event_name == "subscription_created":
        email = attrs.get("user_email", "unknown")
        name = attrs.get("user_name", email.split("@")[0])
        product = attrs.get("product_name", "Unknown")
        slug = _slugify_customer(email)

        await um.write(
            f"context/customers/{slug}/profile.md",
            (
                f"# {name}\n\n"
                f"## Status\nActive subscriber\n\n"
                f"## Plan & Revenue\n- Product: {product}\n"
                f"- Status: active\n- Since: {date_str}\n\n"
                f"## Contact\n- Email: {email}\n"
            ),
            summary=f"New subscriber: {email} → {product}",
        )
        await um.write(
            f"context/customers/{slug}/history.md",
            f"# History — {name}\n\n- {date_str}: Subscribed to {product}\n",
            summary=f"Subscriber history: {email}",
        )

    elif event_name == "subscription_cancelled":
        email = attrs.get("user_email", "unknown")
        slug = _slugify_customer(email)

        # Append cancellation to history
        existing = await um.read(f"context/customers/{slug}/history.md")
        if existing:
            updated = existing.rstrip() + f"\n- {date_str}: Cancelled subscription\n"
            await um.write(
                f"context/customers/{slug}/history.md",
                updated,
                summary=f"Subscriber cancelled: {email}",
            )

        # Update profile status
        existing_profile = await um.read(f"context/customers/{slug}/profile.md")
        if existing_profile:
            updated_profile = existing_profile.replace(
                "Active subscriber", "Cancelled"
            ).replace("- Status: active", "- Status: cancelled")
            await um.write(
                f"context/customers/{slug}/profile.md",
                updated_profile,
                summary=f"Subscriber status → cancelled: {email}",
            )

    elif event_name == "subscription_payment_success":
        email = attrs.get("user_email", "unknown")
        slug = _slugify_customer(email)

        existing = await um.read(f"context/customers/{slug}/history.md")
        if existing:
            updated = existing.rstrip() + f"\n- {date_str}: Payment successful\n"
            await um.write(
                f"context/customers/{slug}/history.md",
                updated,
                summary=f"Payment received: {email}",
            )

    elif event_name == "subscription_payment_failed":
        email = attrs.get("user_email", "unknown")
        slug = _slugify_customer(email)

        existing = await um.read(f"context/customers/{slug}/history.md")
        if existing:
            updated = existing.rstrip() + f"\n- {date_str}: ⚠ Payment failed\n"
            await um.write(
                f"context/customers/{slug}/history.md",
                updated,
                summary=f"Payment failed: {email}",
            )

    elif event_name == "order_created":
        email = attrs.get("user_email", "unknown")
        name = attrs.get("user_name", email.split("@")[0])
        total = attrs.get("total", 0)
        currency = attrs.get("currency", "USD")
        slug = _slugify_customer(email)

        # Create or update customer profile
        existing_profile = await um.read(f"context/customers/{slug}/profile.md")
        if not existing_profile:
            await um.write(
                f"context/customers/{slug}/profile.md",
                (
                    f"# {name}\n\n"
                    f"## Status\nCustomer (one-time purchase)\n\n"
                    f"## Plan & Revenue\n- Total spent: ${total / 100:.2f} {currency}\n\n"
                    f"## Contact\n- Email: {email}\n"
                ),
                summary=f"New customer: {email}",
            )

        # Append to history
        existing_history = await um.read(f"context/customers/{slug}/history.md")
        entry = f"- {date_str}: Purchased — ${total / 100:.2f} {currency}\n"
        if existing_history:
            updated = existing_history.rstrip() + f"\n{entry}"
        else:
            updated = f"# History — {name}\n\n{entry}"
        await um.write(
            f"context/customers/{slug}/history.md",
            updated,
            summary=f"Order from {email}: ${total / 100:.2f}",
        )

    return {"status": "ok", "event": event_name}


def _slugify_customer(email: str) -> str:
    """Convert email to a filesystem-safe slug."""
    import re
    # Use the local part of the email, lowercased, non-alnum → dash
    local = email.split("@")[0].lower()
    slug = re.sub(r"[^a-z0-9]+", "-", local).strip("-")
    return slug or "unknown"


# =============================================================================
# Trading Connection — ADR-187 (API key + secret auth, same pattern as Commerce)
# =============================================================================

class TradingConnectRequest(BaseModel):
    """Request to connect a trading platform via API key + secret."""
    api_key: str
    api_secret: str
    paper: bool = True
    market_data_key: Optional[str] = None


@router.post("/integrations/trading/connect")
async def connect_trading(
    request: TradingConnectRequest,
    auth: UserClient,
):
    """
    Connect a trading platform using API key + secret (ADR-187).

    Same pattern as Commerce (ADR-183): validates credentials, encrypts,
    stores connection, activates Trading Bot, scaffolds context domains.
    """
    from integrations.core.alpaca_client import get_trading_client
    from services.directory_registry import scaffold_context_domain

    user_id = auth.user_id
    token_manager = get_token_manager()
    trading_client = get_trading_client()

    # 1. Validate the credentials
    try:
        account_info = await trading_client.validate_credentials(
            request.api_key, request.api_secret, request.paper,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2. Encrypt and store the connection (key:secret as single encrypted string)
    encrypted_credentials = token_manager.encrypt(
        f"{request.api_key}:{request.api_secret}"
    )
    service_client = get_service_client()

    metadata = {
        "provider": "alpaca",
        "paper": request.paper,
        "account_number": account_info.get("account_number", "")[-4:],  # last 4 only
        "account_status": account_info.get("status", ""),
    }
    if request.market_data_key:
        metadata["market_data_key"] = request.market_data_key

    existing = service_client.table("platform_connections").select("id").eq(
        "user_id", user_id
    ).eq("platform", "trading").execute()

    if existing.data:
        service_client.table("platform_connections").update({
            "credentials_encrypted": encrypted_credentials,
            "metadata": metadata,
            "status": "active",
        }).eq("id", existing.data[0]["id"]).execute()
        connection_id = existing.data[0]["id"]
        logger.info(f"[INTEGRATIONS] Updated trading connection for {user_id}")
    else:
        insert_result = service_client.table("platform_connections").insert({
            "user_id": user_id,
            "platform": "trading",
            "credentials_encrypted": encrypted_credentials,
            "metadata": metadata,
            "status": "active",
        }).execute()
        connection_id = insert_result.data[0]["id"] if insert_result.data else None
        logger.info(f"[INTEGRATIONS] Created trading connection for {user_id}")

    # 3. Activate Trading Bot (reactivate if paused)
    service_client.table("agents").update(
        {"status": "active"}
    ).eq("user_id", user_id).eq("role", "trading_bot").eq(
        "status", "paused"
    ).execute()

    # 4. Scaffold trading context domains (idempotent)
    await scaffold_context_domain(service_client, user_id, "trading")
    await scaffold_context_domain(service_client, user_id, "portfolio")

    return {
        "id": connection_id,
        "platform": "trading",
        "provider": "alpaca",
        "status": "active",
        "paper": request.paper,
        "account_number": metadata.get("account_number"),
    }


@router.patch("/integrations/trading/connect")
async def update_trading_connection(
    request: Request,
    auth: UserClient,
):
    """
    Update trading connection metadata (e.g., paper-to-live transition).

    ADR-187 Decision 7: flip `paper` flag to switch between paper and live.
    """
    body = await request.json()
    service_client = get_service_client()

    existing = service_client.table("platform_connections").select(
        "id, metadata"
    ).eq("user_id", auth.user_id).eq("platform", "trading").eq(
        "status", "active"
    ).single().execute()

    if not existing.data:
        raise HTTPException(status_code=404, detail="No active trading connection")

    metadata = existing.data.get("metadata") or {}

    if "paper" in body:
        metadata["paper"] = bool(body["paper"])
    if "market_data_key" in body:
        metadata["market_data_key"] = body["market_data_key"]

    service_client.table("platform_connections").update({
        "metadata": metadata,
    }).eq("id", existing.data["id"]).execute()

    logger.info(
        f"[INTEGRATIONS] Updated trading metadata for {auth.user_id}: "
        f"paper={metadata.get('paper')}"
    )

    return {
        "id": existing.data["id"],
        "platform": "trading",
        "provider": "alpaca",
        "status": "active",
        "paper": metadata.get("paper"),
    }
