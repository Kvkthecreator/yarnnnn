"""
Integration Routes

Manage third-party integrations (Slack, Notion, etc.) via MCP.
See ADR-026 for architectural decisions.

Endpoints:
- GET /integrations - List user's connected integrations
- GET /integrations/:provider - Get specific integration details
- DELETE /integrations/:provider - Disconnect an integration
- POST /integrations/:provider/export - Export content to provider
- GET /integrations/:provider/destinations - List available destinations (channels, pages)
"""

import logging
from typing import Optional, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.supabase import UserClient
from integrations.core.tokens import get_token_manager
from integrations.core.client import get_mcp_manager, MCP_AVAILABLE
from integrations.core.types import (
    IntegrationProvider,
    IntegrationStatus,
    ExportStatus,
)

logger = logging.getLogger(__name__)

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

    The destination format depends on the provider:
    - Slack: { "channel_id": "C123..." }
    - Notion: { "page_id": "..." }
    """
    user_id = auth.user_id

    if not MCP_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Integration service unavailable (MCP not installed)"
        )

    try:
        # 1. Get user's integration (with encrypted tokens)
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

        # 2. Get deliverable version content
        version = auth.client.table("deliverable_versions").select(
            "id, content, deliverable_id"
        ).eq("id", request.deliverable_version_id).single().execute()

        if not version.data:
            raise HTTPException(status_code=404, detail="Deliverable version not found")

        # Get deliverable title
        deliverable = auth.client.table("deliverables").select(
            "title"
        ).eq("id", version.data["deliverable_id"]).single().execute()

        content = version.data["content"]
        title = deliverable.data["title"] if deliverable.data else "YARNNN Export"

        # 3. Decrypt tokens
        token_manager = get_token_manager()
        access_token = token_manager.decrypt(integration.data["access_token_encrypted"])
        metadata = integration.data.get("metadata", {}) or {}

        # 4. Export via MCP
        mcp = get_mcp_manager()

        if provider == "slack":
            channel_id = request.destination.get("channel_id")
            if not channel_id:
                raise HTTPException(status_code=400, detail="channel_id required for Slack")

            team_id = metadata.get("team_id")
            if not team_id:
                raise HTTPException(status_code=400, detail="Slack integration missing team_id")

            result = await mcp.export_to_slack(
                user_id=user_id,
                channel=channel_id,
                content=content,
                bot_token=access_token,
                team_id=team_id
            )

        elif provider == "notion":
            page_id = request.destination.get("page_id")
            if not page_id:
                raise HTTPException(status_code=400, detail="page_id required for Notion")

            result = await mcp.export_to_notion(
                user_id=user_id,
                parent_id=page_id,
                title=title,
                content=content,
                auth_token=access_token
            )

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

        # 5. Log the export
        log_entry = {
            "deliverable_version_id": request.deliverable_version_id,
            "user_id": user_id,
            "provider": provider,
            "destination": request.destination,
            "status": result.status.value,
            "error_message": result.error_message,
            "external_id": result.external_id,
            "external_url": result.external_url,
            "completed_at": datetime.utcnow().isoformat() if result.status == ExportStatus.SUCCESS else None
        }
        auth.client.table("export_log").insert(log_entry).execute()

        # 6. Update last_used_at
        auth.client.table("user_integrations").update({
            "last_used_at": datetime.utcnow().isoformat()
        }).eq("id", integration.data["id"]).execute()

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


# =============================================================================
# List Destinations (Channels, Pages, etc.)
# =============================================================================

@router.get("/integrations/{provider}/destinations")
async def list_destinations(
    provider: str,
    auth: UserClient
) -> DestinationsListResponse:
    """
    List available export destinations for a provider.

    - Slack: Returns channels the bot can post to
    - Notion: Returns pages/databases the integration has access to
    """
    user_id = auth.user_id

    # TODO: Implement destination listing via MCP
    # This requires calling list_channels or similar tools

    raise HTTPException(
        status_code=501,
        detail="Destination listing not yet implemented"
    )


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
