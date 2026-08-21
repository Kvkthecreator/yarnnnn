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
from services.workspace_context import substrate_scope_filter, account_scope_filter
# ADR-494 D1 — the single offered-connector source (mirrors the FE registry;
# drift is CI-gated by api/test_adr494_connector_registry.py).
from services.connector_registry import (
    CONNECTOR_PROVIDERS,
    CONNECTOR_REGISTRY,
    is_offered,
)
from integrations.core.tokens import get_token_manager
from integrations.core.oauth import (
    get_authorization_url,
    exchange_code_for_token,
    get_frontend_redirect_url,
    OAUTH_CONFIGS,
)
from integrations.core.types import (
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


router = APIRouter()


def _reject_if_retired(provider: str) -> None:
    """Refuse a NEW connection to a retired connector (ADR-494 D2).

    One guard, derived from the one registry — so retiring the Nth connector is
    a status change in `services.connector_registry`, never a hand-edit here.
    Retired providers stay READABLE and DISCONNECTABLE (an existing connection
    is a fact the operator must still see and be able to revoke); only the
    connect verb closes.
    """
    if not is_offered(provider):
        raise HTTPException(
            status_code=410,
            detail=(
                f"The {provider} connector is retired and no longer accepts new "
                "connections. Existing connections remain readable and can be "
                "disconnected."
            ),
        )


# =============================================================================
# Response Models
# =============================================================================

class IntegrationResponse(BaseModel):
    """User-facing integration information."""
    id: str
    provider: str
    status: str
    workspace_name: Optional[str] = None
    # WHERE this connection points, resolved server-side across the
    # per-provider metadata shapes (Slack/Notion write `workspace_name`,
    # GitHub writes `login` — it has accounts, not workspaces). The list row
    # shows this so the operator can tell WHICH Slack a connection is, before
    # drilling in. Display-only; never an authorization fact.
    target: Optional[str] = None
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


# =============================================================================
# List Integrations
# =============================================================================

@router.get("/integrations")
async def list_integrations(auth: UserClient) -> IntegrationListResponse:
    """
    List all of user's connected integrations.
    Returns only active integrations with sanitized data (no tokens).
    """
    from services.connectors import connection_target

    user_id = auth.user_id

    try:
        result = auth.client.table("platform_connections").select(
            "id, platform, status, metadata, created_at"
        ).eq(*account_scope_filter(user_id)).execute()

        # Derive last_used_at from resource bookkeeping in sync_registry
        registry_result = auth.client.table("sync_registry").select(
            "platform, last_synced_at"
        ).eq(*account_scope_filter(user_id)).execute()
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
                target=connection_target(platform, metadata),
                last_used_at=max_synced.get(platform),
                created_at=row["created_at"]
            ))

        return IntegrationListResponse(integrations=integrations)

    except Exception as e:
        logger.error(f"[INTEGRATIONS] Failed to list integrations for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list integrations")


# =============================================================================
# ADR-577 D3 — the workspace-credentials route is DELETED.
#
# It served ADR-566 D5's pane: "what this workspace's AGENTS act through". The
# store it read is withdrawn (ADR-577 D1) — it was unfillable (this route was
# GET-only; no allocation door was ever built), mis-filled (migration 201's
# owner-fill trigger stamps every human connect with a workspace_id), and so the
# pane rendered the OWNER'S PERSONAL TOKENS as workspace agent credentials.
# Do not reinstate without the whole of ADR-577 §7.
# =============================================================================

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
        ).eq(*account_scope_filter(user_id)).execute()

        if not integrations_result.data:
            return IntegrationsSummaryResponse(platforms=[], total_agents=0)

        platforms: list[PlatformSummary] = []
        from datetime import timedelta
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()

        # ADR-494 D1 — the recognized set is DERIVED from the one registry
        # (services.connector_registry), never re-listed here. The former
        # `SUPPORTED_PLATFORMS` literal was the second of two sources; deleted.
        # Retired providers stay recognized so an existing connection is still
        # readable + disconnectable.
        SUPPORTED_PLATFORMS = CONNECTOR_PROVIDERS

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
            ).eq(*substrate_scope_filter(user_id)).neq(
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
                target=connection_target(platform, metadata),
                connected_at=integration["created_at"],
                resource_count=_resource_count_for(provider, integration),
                resource_type=resource_type,
                agent_count=_count_agents(provider),
                activity_7d=_count_activity(provider),
            )

        # Emit platform summaries in stable order.
        #
        # ADR-494 D3 — this loop used to iterate a hardcoded
        # `("slack", "notion", "github")` tuple: the THIRD offered-set list, and
        # a live bug. A connected commerce/trading connection was never emitted,
        # so the frontend (which keys connectedness off this summary) rendered it
        # under "New connection" even while connected. Iterating the registry
        # fixes that by construction — every recognized provider that has a row
        # is reported, retired ones included (they exist, so they must be
        # reportable; they are simply not OFFERED).
        for provider in CONNECTOR_REGISTRY:
            integration = canonical_integrations.get(provider)
            if integration:
                platforms.append(_to_summary(provider, integration))

        # Total agents count
        total_result = auth.client.table("agents").select(
            "id", count="exact"
        ).eq(*substrate_scope_filter(user_id)).execute()
        total_agents = total_result.count or 0

        return IntegrationsSummaryResponse(
            platforms=platforms,
            total_agents=total_agents
        )

    except Exception as e:
        logger.error(f"[INTEGRATIONS] Failed to get summary for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get integrations summary")


# =============================================================================
# Capture Lane State (must be before /{provider} to avoid route collision)
# =============================================================================

@router.get("/integrations/capture-lane")
async def get_capture_lane_state(auth: UserClient) -> dict[str, Any]:
    """
    Workspace-level capture-lane state — ADR-404 D2 (2026-07-04 amendment).

    ADR-591 deleted the connector walk and its flag, so there is no longer a
    deploy-level switch that decides whether a connector is configurable:
    configuring a connector is not running one (D4). The field is kept and
    pinned False so a not-yet-deployed client reading it still resolves to
    "no background schedule is running", which is TRUE and always will be —
    captures happen when a consumer asks (D3). Zero-DB.
    """
    return {"connector_capture_enabled": False}


# =============================================================================
# Retention window (ADR-392 D8)
#
# MUST be registered BEFORE `/integrations/{provider}` below: FastAPI resolves
# routes in registration order, and the single-segment `{provider}` catch-all
# would otherwise swallow the literal `/integrations/retention` (binding
# provider="retention" → 404 "No retention integration found"). The `retention`
# path has no provider segment, so it belongs above the catch-all.
# =============================================================================

class RetentionRequest(BaseModel):
    retention_days: int


@router.get("/integrations/retention")
async def get_retention(auth: UserClient) -> dict[str, Any]:
    """The workspace-level raw-capture retention window (ADR-392 D8).

    Reads governance/_retention.yaml `retention_days`. Workspace-scoped (one
    window for all connectors' raw lanes) — the mechanic the FE dial edits. NOT
    provider-scoped; ADR-392 D8's per-connection retention is the deferred
    'eventually'. Returns the declared value + the kernel default + the UI presets.
    """
    from services.connector_retention import read_retention_days, DEFAULT_RETENTION_DAYS
    from services.billing_tiers import get_tier, tier_retention_max_days

    days = await read_retention_days(auth.client, auth.user_id)
    tier = get_tier(auth.client, auth.user_id)
    tier_max = tier_retention_max_days(tier)
    return {
        # The DECLARED window (what the dial edits), and the effective window the
        # GC honors — the declared value clamped to the tier ceiling (ADR-396 gate 1).
        "retention_days": days,
        "effective_days": min(days, tier_max),
        "default_days": DEFAULT_RETENTION_DAYS,
        "tier": tier,
        "tier_max_days": tier_max,
        "presets": [p for p in (7, 14, 30, 90) if p <= tier_max],
    }


@router.put("/integrations/retention")
async def update_retention(request: RetentionRequest, auth: UserClient) -> dict[str, Any]:
    """Author the workspace-level raw-capture retention window (ADR-392 D8).

    Writes governance/_retention.yaml. Clamps to a 1-day floor AND to the
    subscription tier ceiling (ADR-396 gate 1) — a free-tier operator can declare
    at most the free ceiling; the declared value is stored clamped so the dial and
    the GC agree. governance/ is operator-authored, so authored_by='operator'.
    """
    from services.connector_retention import write_retention_days
    from services.billing_tiers import retention_max_days_for_user

    tier_max = retention_max_days_for_user(auth.client, auth.user_id)
    requested = min(request.retention_days, tier_max)
    written = await write_retention_days(auth.client, auth.user_id, requested)
    clamped = written < request.retention_days
    return {"retention_days": written, "success": True, "clamped": clamped, "tier_max_days": tier_max}


class ConnectorSettingsRequest(BaseModel):
    """The connector's per-connection settings. Partial: only the fields
    present are written. extra="forbid" so a stale FE field is refused
    loudly, never silently dropped (the ADR-562 lesson).

    ADR-591 retired `cadence` (no clock to compare it against) and `digest`
    (its walker is deleted). Under extra="forbid" a stale caller sending
    either now gets a 422 — deliberately: a dial that no longer controls
    anything must fail loudly, not appear to work."""

    model_config = {"extra": "forbid"}

    destination: Optional[str] = None


@router.put("/integrations/{provider}/connector-settings")
async def update_connector_settings_route(
    provider: str,
    request: ConnectorSettingsRequest,
    auth: UserClient,
) -> dict[str, Any]:
    """Set the connector's per-connection settings (ADR-582 D3, narrowed by
    ADR-591 to one): destination — where snapshots land; empty → the
    intake-grammar default lane.

    400 on an invalid destination; 404 when the platform is not connected.
    """
    from services.connectors import connector_settings, update_connector_settings

    patch = request.model_dump(exclude_unset=True)
    # destination=null is a real instruction (reset to the default lane), so
    # it survives the None filter that guards partial writes.
    patch = {
        k: v for k, v in patch.items()
        if v is not None or k == "destination"
    }
    if not patch:
        raise HTTPException(status_code=400, detail="No settings provided.")

    db_platform = PROVIDER_ALIASES.get(provider, [provider])[0]
    try:
        touched = update_connector_settings(
            auth.client, auth.user_id, db_platform, patch,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if touched is None:
        raise HTTPException(
            status_code=404, detail=f"No {provider} connection found.",
        )
    # Echo the normalized, defaults-applied view (what a consumer will read),
    # not the raw patch.
    stored = connector_settings({"platform": db_platform,
                                 "settings": {"connector": touched}})
    return {
        "success": True,
        "provider": provider,
        "settings": {"destination": stored["destination"]},
    }


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
            ).eq(*account_scope_filter(user_id)).eq("platform", p).execute()
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
        ).eq(*account_scope_filter(user_id)).eq("platform", p).limit(1).execute()
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
    Disconnect an integration (teardown contract per ADR-401 D3 / ADR-582).

    Deletes the connection row — and with it the selection + connector
    settings, which live ON the row (ADR-582 D2: credential gone means
    aperture gone; a fresh connect is a fresh selection). The landed raw is
    deliberately KEPT (it ages out mechanically under the retention GC;
    cited raw stays as evidence).
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

        # ADR-582 D2: no capture-entry teardown needed — selection, settings,
        # and cadence lived ON the deleted row; the capture walk simply stops
        # finding the connection on the next tick.

        # ADR-207 P4a: Platform Bots dissolved. OAuth disconnect no longer
        # deletes a bot agent row — the row doesn't exist. The platform
        # capability (read_slack, write_slack, ...) simply becomes unavailable
        # via `capability_available()`, and any task declaring it in
        # `**Required Capabilities:**` fails fast with "connect slack first".
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
                ).eq(*account_scope_filter(user_id)).eq("platform", p).limit(1).execute()
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
            url=get_frontend_redirect_url(
                False,
                provider,
                error_description or error,
                error_reason="provider_denied",
            )
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
            # ⚠️ Write only columns platform_connections actually has. This dict
            # carried a `last_error: None` from the original user_integrations
            # schema (migration 023); platform_connections has no such column, so
            # PostgREST refused the WHOLE update (PGRST204) — every RE-connect
            # exchanged a fresh token and then dropped it (prod receipt
            # 2026-08-19 04:28:23, notion).
            update_data = {
                "credentials_encrypted": token_data["credentials_encrypted"],
                "metadata": token_data["metadata"],
                "status": token_data["status"],
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
                # ADR-580 D5: the connecting principal — the attribution
                # record derived material rides "on behalf of" (ADR-407 D5,
                # named 3× in canon before being built here).
                "connected_by": token_data["user_id"],
            }).execute()

            logger.info(f"[INTEGRATIONS] Connected {provider} for user {token_data['user_id']}")

        # ADR-207 P4a: Platform Bots dissolved. OAuth connect no longer
        # creates a bot agent row. Platform capabilities unlock the moment
        # the connection goes active — enforced by `capability_available()`
        # at task dispatch, not by per-platform agent scaffolding.

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

        # Auto-discover the landscape so the detail page opens populated.
        # ⚠️ Discovery only — NEVER auto-select. ADR-113's smart auto-selection
        # is DELETED (2026-08-19): a selection is CONSENT — the capture writer's
        # mandate and (per ADR-576) a reach bound — and a heuristic pre-checking
        # 50 sources fabricated that consent at a moment nothing consumed it,
        # to be enacted whenever the capture flag flips. Selection starts empty;
        # only the operator fills it. Smart defaults survive as the
        # `recommended` BADGE on the landscape response, never as a pre-check.
        try:
            user_id_for_auto = token_data["user_id"]

            # Re-read the integration row (we just upserted it)
            auto_result = service_client.table("platform_connections").select(
                "id, credentials_encrypted, refresh_token_encrypted, metadata, landscape"
            ).eq(*account_scope_filter(user_id_for_auto)).eq("platform", provider).limit(1).execute()

            if auto_result.data:
                integration_row = auto_result.data[0]

                from services.landscape import discover_landscape

                landscape_data = await discover_landscape(provider, user_id_for_auto, integration_row)
                service_client.table("platform_connections").update({
                    "landscape": landscape_data,
                    "landscape_discovered_at": datetime.utcnow().isoformat(),
                }).eq("id", integration_row["id"]).execute()
                logger.info(
                    f"[INTEGRATIONS] Discovered {len(landscape_data.get('resources', []))} "
                    f"resources for {provider} user {user_id_for_auto[:8]} (no auto-selection)"
                )
        except Exception as e:
            # Non-fatal: discovery is best-effort here; the detail page re-runs it.
            logger.warning(f"[INTEGRATIONS] Post-connect discovery failed for {provider}: {e}")

        # Redirect to frontend with success
        return RedirectResponse(
            url=get_frontend_redirect_url(True, provider, redirect_to=token_data.get("redirect_to"))
        )

    except ValueError as e:
        # ADR-531: OAuthStateError carries WHICH state failure occurred. Logging
        # the reason separates a deploy-lost state from a slow consent flow from
        # a tampered token — three causes the old single message conflated.
        reason = getattr(e, "reason", "invalid_request")
        logger.warning(
            f"[INTEGRATIONS] OAuth validation error for {provider} "
            f"(reason={reason}): {e}"
        )
        return RedirectResponse(
            url=get_frontend_redirect_url(False, provider, str(e), error_reason=reason)
        )
    except Exception as e:
        logger.error(f"[INTEGRATIONS] OAuth callback error for {provider}: {e}")
        return RedirectResponse(
            url=get_frontend_redirect_url(
                False,
                provider,
                "Failed to connect. Please try again.",
                error_reason="unexpected",
            )
        )


# =============================================================================
# ADR-030: Landscape Discovery
# (The coverage half died with the sync lane — 2026-08-19 sweep: nothing wrote
# sync_registry.last_synced_at any more, so coverage_state was permanently
# "uncovered" and no FE component read it.)
# =============================================================================

class LandscapeResourceResponse(BaseModel):
    """A resource in the platform landscape."""
    id: str
    name: str
    resource_type: str  # 'channel', 'page', 'database', 'repository'
    metadata: dict[str, Any] = {}
    recommended: bool = False


class LandscapeResponse(BaseModel):
    """Platform landscape."""
    provider: str
    discovered_at: Optional[datetime] = None
    resources: list[LandscapeResourceResponse]


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
        ).eq(*account_scope_filter(user_id)).eq("platform", p).limit(1).execute()
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

        # Preserve existing selected_sources through refresh (drop only ids the
        # re-discovered landscape no longer offers). An EMPTY selection stays
        # empty: ADR-079/113 smart auto-selection is DELETED (2026-08-19) — a
        # selection is operator consent, never a heuristic's pre-check. Smart
        # defaults survive only as the `recommended` badge below.
        existing_selected = (landscape or {}).get("selected_sources", [])
        if existing_selected:
            new_resource_ids = {r["id"] for r in landscape_data.get("resources", [])}
            landscape_data["selected_sources"] = [
                s for s in existing_selected
                if (s.get("id") if isinstance(s, dict) else s) in new_resource_ids
            ]

        # Store landscape snapshot
        auth.client.table("platform_connections").update({
            "landscape": landscape_data,
            "landscape_discovered_at": datetime.utcnow().isoformat()
        }).eq("id", integration.data[0]["id"]).execute()

        discovered_at = datetime.utcnow()
    else:
        landscape_data = integration.data[0].get("landscape", {})
        discovered_at = integration.data[0].get("landscape_discovered_at")

    resources = [
        LandscapeResourceResponse(
            id=resource.get("id"),
            name=resource.get("name", "Unknown"),
            resource_type=resource.get("type", "unknown"),
            metadata=resource.get("metadata", {}),
        )
        for resource in landscape_data.get("resources", [])
    ]

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

    return LandscapeResponse(
        provider=provider,
        discovered_at=discovered_at,
        resources=resources,
    )


# =============================================================================
# ADR-052: Platform Context (Synced Content)
# =============================================================================

# ADR-153: /integrations/{provider}/context endpoint DELETED — platform_content sunset.
# Platform data flows through tasks into workspace context domains.


# =============================================================================
# ADR-043: User Limits & Source Selection
# =============================================================================

class UserLimitsResponse(BaseModel):
    """Workspace balance + subscription tier (ADR-396: Type-B subscription).

    PER-ROLE SPLIT (2026-07-29, operator-observed): the WALLET (remaining
    dollars, top-up pool) is billing-authority information — the same
    authority `/subscription/status` 403s on. A member's UserMenu was showing
    the shared workspace's "$X left" while the Billing pane refused them the
    same fact. So: dollar fields are None unless `billing_authority`; the
    plan `tier` and `spend_usd` stay (a workspace fact + activity-shaped
    consumption, member-visible per DP29 commons legibility); and the two
    BOOLEAN balance states ride for everyone — an empty pool stops every
    member's work, so the fact that it is low/exhausted is commons-legible
    even when the number is not.
    """
    balance_usd: Optional[float] = None
    spend_usd: float
    raw_balance_usd: Optional[float] = None
    allowance_usd: Optional[float] = None
    topup_balance_usd: Optional[float] = None
    tier: str = "free"
    is_subscriber: bool
    subscription_plan: Optional[str] = None
    next_refill: Optional[str] = None
    # The caller's billing authority in the ACTING workspace (owner OR the
    # `billing` grant scope — services.principal_grants.has_billing_authority,
    # the same verdict the Billing pane's 403 derives from).
    billing_authority: bool = True
    # Dollar-free balance states, computed server-side so member surfaces can
    # warn without the wallet: exhausted = hard-stopped at zero; low = under
    # the $1 runway threshold the attention bell warns at.
    balance_exhausted: bool = False
    balance_low: bool = False


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
    - balance_usd: effective remaining balance (raw − spend since anchor)
    - spend_usd: total token spend since the current balance anchor.
      spend_usd + balance_usd == raw_balance_usd (single-window reconcile)
    - raw_balance_usd: total grants/top-ups before spend is netted
    - is_subscriber: whether user has an active Pro subscription
    - subscription_plan: 'pro' | 'pro_yearly' | None
    - next_refill: ISO timestamp of next subscription billing (if subscriber)
    """
    from services.platform_limits import get_usage_summary
    from services.principal_grants import has_billing_authority
    from services.workspace_context import effective_workspace_id

    summary = get_usage_summary(auth.client, auth.user_id)

    # Per-role wallet split (see UserLimitsResponse docstring): the dollar
    # figures ship only to billing authority; the boolean states ship to all.
    authority = True
    try:
        ws = effective_workspace_id(auth.user_id, getattr(auth, "workspace_id", None))
        if ws:
            authority = has_billing_authority(auth.user_id, ws)
    except Exception:  # noqa: BLE001 — display split, never block the read
        authority = True

    balance = float(summary["balance_usd"])
    return UserLimitsResponse(
        balance_usd=balance if authority else None,
        spend_usd=summary["spend_usd"],
        raw_balance_usd=summary["raw_balance_usd"] if authority else None,
        allowance_usd=summary.get("allowance_usd", 0.0) if authority else None,
        topup_balance_usd=summary.get("topup_balance_usd", 0.0) if authority else None,
        tier=summary.get("tier", "free"),
        is_subscriber=summary["is_subscriber"],
        subscription_plan=summary.get("subscription_plan"),
        next_refill=summary.get("next_refill"),
        billing_authority=authority,
        balance_exhausted=balance <= 0,
        balance_low=0 < balance <= 1.0,
    )


# ⭐ A field the service computes but the response model does not DECLARE is
# silently DROPPED by FastAPI serialization — the surface then reads as a stale
# API with no error anywhere. That is exactly how the ADR-396 §11 fields
# (trend_days / by_model / spend_usd / pct_runs) reached production computed,
# serialized away, and invisible. When the service's dict grows a key, these
# models MUST grow it too.
class UsageWorkItem(BaseModel):
    slug: str
    runs: int
    cost_usd: float
    pct: int          # share of SPEND
    pct_runs: int = 0  # share of RUNS — a different denominator (ADR-396 §11)


class UsageTrendPoint(BaseModel):
    date: str
    cost_usd: float
    runs: int = 0
    failed: int = 0


class UsageActivity(BaseModel):
    runs: int
    success_rate: Optional[int] = None
    avg_cost_usd: float
    failed: int
    spend_usd: float = 0.0


class UsageModelItem(BaseModel):
    """Spend by engine (ADR-556/559: the engine is the cost driver)."""
    model: str
    runs: int
    cost_usd: float
    pct: int


class UsageDetailResponse(BaseModel):
    """Spend breakdown + trend + activity for the Usage tab (ADR-172 surface).

    Derived entirely from execution_events over the current balance anchor
    window — by_work totals reconcile with /user/limits spend_usd.
    """
    by_work: list[UsageWorkItem]
    trend: list[UsageTrendPoint]
    trend_days: int = 0
    by_model: list[UsageModelItem] = []
    activity: UsageActivity


@router.get("/user/usage-detail")
async def get_user_usage_detail(auth: UserClient) -> UsageDetailResponse:
    """Spend-by-work-item + spend trend + activity summary.

    Read-only aggregation over execution_events (ADR-291 cost ledger).
    Powers the expanded Usage tab below the balance meter. Zero new logging.
    """
    from services.platform_limits import get_usage_detail

    detail = get_usage_detail(auth.client, auth.user_id)
    return UsageDetailResponse(**detail)


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
        ).eq(*account_scope_filter(user_id)).eq("platform", p).limit(1).execute()
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

    # ADR-582 D2: landscape.selected_sources (written above) IS the one
    # selection store. The `_watch.yaml` substrate mirror and the
    # `_captures.yaml` seed-at-select are DELETED — the capture walk
    # (services/connectors.py) reads the landscape row directly on the
    # scheduler tick.

    logger.info(f"[INTEGRATIONS] User {user_id} updated {provider} sources: {len(selected_sources)} selected")

    return SelectedSourcesResponse(
        success=True,
        selected_sources=selected_sources,
        message=f"{len(selected_sources)} source(s) selected",
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
        ).eq(*account_scope_filter(user_id)).eq("platform", p).limit(1).execute()
        if result.data:
            integration_data = result.data[0]
            break

    if not integration_data:
        raise HTTPException(status_code=404, detail=f"No {provider} integration found")

    landscape = integration_data.get("landscape", {}) or {}
    selected = landscape.get("selected_sources", [])

    # ADR-172: source-count tiering removed — balance_usd is the single gate, so
    # there is no per-source limit. Selection is a declaration, not a quota. The FE
    # consumes only `sources`; `limit`/`can_add_more` are retained (unbounded) for
    # response-shape compatibility.
    return {
        "sources": selected,
        "limit": None,
        "can_add_more": True,
    }


@router.get("/integrations/{provider}/capture-signal")
async def get_capture_signal(
    provider: str,
    auth: UserClient,
) -> dict[str, Any]:
    """Declared × observed for a connector's capture lane (ADR-393 D3, re-cut by ADR-582).

    Joins two reads:
      - DECLARED — the selection, from the ONE store
        (platform_connections.landscape.selected_sources, ADR-582 D2): which
        selectors (channels/pages/repos) the operator put in scope. This is
        the "what should be perceived" half.
      - OBSERVED — the per-declaration health blocks in _capture_signal.yaml
        (written by the capture walk, ADR-393): status · observed_at · items ·
        last_error. This is the "what was actually captured, and how fresh" half.

    The FE renders each selected selector with its freshness (or "not reading yet"
    when no capture has run for it). Honest by construction: a connector with no
    capture recurrence scheduled shows every selector as un-observed — connecting +
    selecting makes a platform AVAILABLE; a capture recurrence makes it READ
    (ADR-392 D5).

    ADR-401 Phase 1 — the drill-in's one round-trip also carries the ACCESS +
    CADENCE facts the Manage screen renders:
      - `granted_scopes` — the OAuth consent fact (metadata.scope, comma-joined
        at exchange for Slack/GitHub; Notion grants app-level access → []).
      - `connection` — {workspace_name, connected_at} for the header line.
      - `capture` — {schedule, paused}; paused = empty selection (ADR-582:
        there is no seeded entry any more).
      - `settings` — the surviving connector dial {destination} (ADR-591
        retired cadence + digest with the walker), defaults applied; null
        when unconnected.
      - `does` — the capability facts {reads, writes, agents}, derived from
        the capture binding + exporter registry + the ADR-577 refusal.
      - `agent_enabled` — the deploy-level gate (ADR-375 D4): when False,
        captures never run regardless of cadence; the FE must say so rather
        than imply reads are happening.

    Returns:
      {
        "provider": str,
        "declared": [{id, name, selected}],   # every selectable, with in/out state
        "observed": {slug: {status, observed_at, items, last_error, target}},
        "workspace_capture_count": int,        # captures with any observed block
        "granted_scopes": [str],
        "connection": {workspace_name, connected_at} | None,
        "capture": {schedule, paused} | None,
        "settings": {destination, last_capture_at} | None,
        "does": {reads, writes, agents} | None,
        "agent_enabled": bool,
      }
    """
    from services.agent_gating import is_agent_enabled
    from services.capture.declarations import read_capture_signal
    from services.connectors import connection_target, connector_does, connector_settings

    db_platform = PROVIDER_ALIASES.get(provider, [provider])[0]

    # DECLARED — the selection, from the ONE store (ADR-582 D2:
    # landscape.selected_sources; the _watch.yaml mirror is deleted). Shape
    # preserved for the FE: [{id, name, selected}] — every selectable resource
    # with its in/out state.
    declared: list[dict[str, Any]] = []
    conn_row: Optional[dict[str, Any]] = None
    try:
        rows = (
            auth.client.table("platform_connections")
            .select("landscape, settings, metadata, created_at, platform")
            .eq(*account_scope_filter(auth.user_id))
            .eq("platform", db_platform)
            .limit(1)
            .execute()
        ).data or []
        conn_row = rows[0] if rows else None
        if conn_row:
            landscape = conn_row.get("landscape") or {}
            selected = {
                str(s.get("id")) for s in (landscape.get("selected_sources") or [])
                if isinstance(s, dict) and s.get("id")
            }
            declared = [
                {"id": r.get("id"), "name": r.get("name", r.get("id")),
                 "selected": str(r.get("id")) in selected}
                for r in (landscape.get("resources") or [])
                if r.get("id")
            ]
    except Exception as exc:  # noqa: BLE001 — declaration read is best-effort
        logger.warning("[INTEGRATIONS] capture-signal: selection read failed for %s: %s", provider, exc)

    # OBSERVED — the capture health signal (workspace-wide; the FE matches
    # per-selector by convention or shows the workspace capture health).
    try:
        signal = await read_capture_signal(auth.client, auth.user_id)
        observed = signal.get("captures") or {} if isinstance(signal, dict) else {}
    except Exception as exc:  # noqa: BLE001
        logger.warning("[INTEGRATIONS] capture-signal: signal read failed for %s: %s", provider, exc)
        observed = {}

    # ACCESS — the connection row's consent facts. `metadata.scope` is written
    # at OAuth exchange (Slack oauth.py:345, GitHub :436); Notion stores none.
    granted_scopes: list[str] = []
    connection: Optional[dict[str, Any]] = None
    if conn_row:
        md = conn_row.get("metadata") or {}
        scope_str = md.get("scope") or ""
        granted_scopes = [s.strip() for s in scope_str.split(",") if s.strip()]
        connection = {
            "workspace_name": md.get("workspace_name"),
            # Same resolver the LIST row uses, so the two faces of one
            # connection cannot name their target differently.
            "target": connection_target(db_platform, md),
            "connected_at": conn_row.get("created_at"),
        }

    # SETTINGS — the connection's own dials (ADR-582 D3, narrowed by ADR-591).
    # `connector_settings` returns {destination, last_capture_at} and nothing
    # else: ADR-591 deleted the clock, so `cadence` and `digest` have no source
    # to read. Reading them here raised KeyError for every CONNECTED provider
    # (an unconnected one returns early), 500ing a call both callers swallow.
    # The retired `capture` block went with them — it carried `schedule` off
    # the same deleted cadence, and no caller ever read it.
    settings_obj: Optional[dict[str, Any]] = None
    if conn_row:
        cs = connector_settings(conn_row)
        settings_obj = {
            "destination": cs["destination"],
        }

    return {
        "provider": provider,
        "declared": declared,
        "observed": observed,
        "workspace_capture_count": len(observed),
        "granted_scopes": granted_scopes,
        "connection": connection,
        "settings": settings_obj,
        # The capability facts (reads / writes / agents) — derived server-side
        # from the machinery that enacts them (binding · exporter registry ·
        # the ADR-577 refusal), so the display can never drift from the code.
        "does": connector_does(db_platform),
        "agent_enabled": is_agent_enabled(),
        # ADR-591: there is no capture flag. Pinned False — kept only so a
        # not-yet-deployed client still reads "nothing runs on a schedule",
        # which is permanently true. Remove once no client reads it.
        "connector_capture_enabled": False,
    }


# =============================================================================
# Commerce Connection — ADR-183 (API key auth, not OAuth)
# =============================================================================

class CommerceConnectRequest(BaseModel):
    """Request to connect a commerce platform via API key."""
    api_key: str


class EmailConnectRequest(BaseModel):
    """Request to connect an email provider (Resend) via API key (ADR-192 Phase 4)."""
    api_key: str
    from_email: Optional[str] = None   # e.g. "team@company.com" — requires verified domain in Resend
    from_name: Optional[str] = None    # e.g. "Company Name"
    reply_to: Optional[str] = None     # where customer replies go


@router.post("/integrations/email/connect")
async def connect_email(
    request: EmailConnectRequest,
    auth: UserClient,
):
    """Connect an email provider (Resend) via API key (ADR-192 Phase 4).

    Validates the Resend key, encrypts + stores the connection. Sender
    identity (from_email, from_name, reply_to) is optional — if the user
    has no verified domain in Resend, sends fall back to the shared
    `onboarding@resend.dev` sender for alpha use.

    No OAuth. No domain verification enforced at connect time — the user
    can connect first, verify their domain later in Resend, then update
    their connection metadata.
    """
    from integrations.core.resend_client import get_resend_client

    user_id = auth.user_id
    token_manager = get_token_manager()
    resend = get_resend_client()

    # 1. Validate the API key
    try:
        validation = await resend.validate_key(request.api_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2. Encrypt + store
    encrypted_key = token_manager.encrypt(request.api_key)
    service_client = get_service_client()

    existing = service_client.table("platform_connections").select("id").eq(
        "user_id", user_id
    ).eq("platform", "email").execute()

    metadata = {
        "provider": "resend",
        "from_email": request.from_email,
        "from_name": request.from_name,
        "reply_to": request.reply_to,
        "verified_domains": [
            d["name"] for d in validation.get("domains", [])
            if d.get("status") == "verified"
        ],
        "has_verified_domain": validation.get("has_verified_domain", False),
    }

    if existing.data:
        service_client.table("platform_connections").update({
            "credentials_encrypted": encrypted_key,
            "metadata": metadata,
            "status": "active",
        }).eq("id", existing.data[0]["id"]).execute()
        connection_id = existing.data[0]["id"]
        logger.info(f"[INTEGRATIONS] Updated email (Resend) connection for {user_id}")
    else:
        insert_result = service_client.table("platform_connections").insert({
            "user_id": user_id,
            "platform": "email",
            "credentials_encrypted": encrypted_key,
            "metadata": metadata,
            "status": "active",
            "connected_by": user_id,  # ADR-580 D5
        }).execute()
        connection_id = insert_result.data[0]["id"] if insert_result.data else None
        logger.info(f"[INTEGRATIONS] Created email (Resend) connection for {user_id}")

    return {
        "id": connection_id,
        "platform": "email",
        "provider": "resend",
        "status": "active",
        "has_verified_domain": metadata["has_verified_domain"],
        "verified_domains": metadata["verified_domains"],
        "sender_fallback_active": not metadata["has_verified_domain"],
    }


@router.post("/integrations/commerce/connect")
async def connect_commerce(
    request: CommerceConnectRequest,
    auth: UserClient,
):
    """
    Connect a commerce platform using API key (ADR-183).

    Unlike OAuth flows (Slack, Notion, GitHub), commerce uses direct API key auth.
    This endpoint validates the key, encrypts it, and stores the connection.
    (ADR-207 P4a: the Commerce Bot this docstring once claimed to scaffold was
    dissolved — the stale claim is corrected here.)

    ADR-494 D2 — commerce is RETIRED: NEW connections are refused. The endpoint
    is not deleted, because the Lemon Squeezy webhook below is an independent
    live path and an existing connection must stay readable/disconnectable.
    """
    _reject_if_retired("commerce")

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
            "connected_by": user_id,  # ADR-580 D5
        }).execute()
        connection_id = insert_result.data[0]["id"] if insert_result.data else None
        logger.info(f"[INTEGRATIONS] Created commerce connection for {user_id}")

    # ADR-207 P4a: Commerce Bot dissolved. read_commerce / write_commerce
    # capabilities unlock the moment the connection is active.

    # ADR-261 D6 §4: lazy back-office materialization on platform connect
    # is deleted. Outcome-reconciliation, reviewer-calibration, and
    # freddie-reflection are operator-authored (or bundle-seeded) entries
    # in /workspace/_recurrences.yaml — the operator opts in by activating
    # a program bundle that ships them, or authors them via Schedule().

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

    import os

    body = await request.body()
    signature = request.headers.get("X-Signature", "")

    # Verify the Lemon Squeezy webhook signature (HMAC-SHA256 of the raw body
    # with the store's signing secret). Security (2026-08-01): previously this
    # trusted any caller, so an attacker could POST a forged payload with an
    # arbitrary custom_data.user_id and write files into that victim's
    # workspace. We now FAIL CLOSED — no valid signature, no write.
    webhook_secret = os.environ.get("LEMONSQUEEZY_WEBHOOK_SECRET", "")
    if not webhook_secret:
        # Not a live capability without the secret configured. Refuse rather
        # than silently accepting unauthenticated writes.
        logger.error("[COMMERCE_WEBHOOK] LEMONSQUEEZY_WEBHOOK_SECRET unset — rejecting webhook")
        raise HTTPException(status_code=503, detail="Webhook signature verification not configured")

    expected = hmac.new(webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    if not signature or not hmac.compare_digest(expected, signature):
        logger.warning("[COMMERCE_WEBHOOK] Invalid webhook signature — rejecting")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

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
            f"operation/customers/{slug}/profile.md",
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
            f"operation/customers/{slug}/history.md",
            f"# History — {name}\n\n- {date_str}: Subscribed to {product}\n",
            summary=f"Subscriber history: {email}",
        )

    elif event_name == "subscription_cancelled":
        email = attrs.get("user_email", "unknown")
        slug = _slugify_customer(email)

        # Append cancellation to history
        existing = await um.read(f"operation/customers/{slug}/history.md")
        if existing:
            updated = existing.rstrip() + f"\n- {date_str}: Cancelled subscription\n"
            await um.write(
                f"operation/customers/{slug}/history.md",
                updated,
                summary=f"Subscriber cancelled: {email}",
            )

        # Update profile status
        existing_profile = await um.read(f"operation/customers/{slug}/profile.md")
        if existing_profile:
            updated_profile = existing_profile.replace(
                "Active subscriber", "Cancelled"
            ).replace("- Status: active", "- Status: cancelled")
            await um.write(
                f"operation/customers/{slug}/profile.md",
                updated_profile,
                summary=f"Subscriber status → cancelled: {email}",
            )

    elif event_name == "subscription_payment_success":
        email = attrs.get("user_email", "unknown")
        slug = _slugify_customer(email)

        existing = await um.read(f"operation/customers/{slug}/history.md")
        if existing:
            updated = existing.rstrip() + f"\n- {date_str}: Payment successful\n"
            await um.write(
                f"operation/customers/{slug}/history.md",
                updated,
                summary=f"Payment received: {email}",
            )

    elif event_name == "subscription_payment_failed":
        email = attrs.get("user_email", "unknown")
        slug = _slugify_customer(email)

        existing = await um.read(f"operation/customers/{slug}/history.md")
        if existing:
            updated = existing.rstrip() + f"\n- {date_str}: ⚠ Payment failed\n"
            await um.write(
                f"operation/customers/{slug}/history.md",
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
        existing_profile = await um.read(f"operation/customers/{slug}/profile.md")
        if not existing_profile:
            await um.write(
                f"operation/customers/{slug}/profile.md",
                (
                    f"# {name}\n\n"
                    f"## Status\nCustomer (one-time purchase)\n\n"
                    f"## Plan & Revenue\n- Total spent: ${total / 100:.2f} {currency}\n\n"
                    f"## Contact\n- Email: {email}\n"
                ),
                summary=f"New customer: {email}",
            )

        # Append to history
        existing_history = await um.read(f"operation/customers/{slug}/history.md")
        entry = f"- {date_str}: Purchased — ${total / 100:.2f} {currency}\n"
        if existing_history:
            updated = existing_history.rstrip() + f"\n{entry}"
        else:
            updated = f"# History — {name}\n\n{entry}"
        await um.write(
            f"operation/customers/{slug}/history.md",
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

    Same pattern as Commerce (ADR-183): validates credentials, encrypts, and
    stores the connection. (ADR-207 P4a: the Trading Bot this docstring once
    claimed to activate was dissolved — the stale claim is corrected here.)

    ADR-494 D2 — trading is RETIRED: NEW connections are refused. Its only
    capture path was the alpha-trader bundle's SyncPlatformState mirrors, which
    need a hire with no operator surface (ADR-414 D5 / ADR-382). The endpoint
    survives so an existing connection stays readable/disconnectable and so an
    alpha-trader re-hire can re-light it with a one-word change.
    """
    _reject_if_retired("trading")

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
            "connected_by": user_id,  # ADR-580 D5
        }).execute()
        connection_id = insert_result.data[0]["id"] if insert_result.data else None
        logger.info(f"[INTEGRATIONS] Created trading connection for {user_id}")

    # ADR-207 P4a: Trading Bot dissolved. read_trading / write_trading
    # capabilities unlock the moment the connection is active.

    # ADR-261 D6 §4: lazy back-office materialization on platform connect
    # is deleted. Outcome-reconciliation, reviewer-calibration, and
    # freddie-reflection are bundle-seeded entries in
    # /workspace/_recurrences.yaml when the operator activates a program
    # (e.g. alpha-trader); operators without a bundle author them via
    # Schedule(action='create', ...) on demand.

    # 4. Scaffold trading context domains (idempotent)
    await scaffold_context_domain(service_client, user_id, "trading")
    await scaffold_context_domain(service_client, user_id, "portfolio")

    # 5. ADR-207 P4a: auto trading-digest task scaffold DELETED. YARNNN
    # proposes trading-domain tasks (digest, signal, execute) based on the
    # operator's Mandate and risk principles.

    # 6. ADR-192 Phase 5: scaffold default _risk.md if absent.
    # Conservative defaults. User is expected to review + adjust before
    # enabling autonomous execution. Without this file, autonomous orders
    # fail-closed (per risk_gate.py).
    risk_md_created = await _scaffold_risk_md(service_client, user_id)

    return {
        "id": connection_id,
        "platform": "trading",
        "provider": "alpaca",
        "status": "active",
        "paper": request.paper,
        "account_number": metadata.get("account_number"),
        "risk_md_scaffolded": risk_md_created,
    }


async def _scaffold_risk_md(service_client: Any, user_id: str) -> bool:
    """Create /workspace/operation/trading/_risk.md with conservative defaults.

    Idempotent: returns False if the file already exists. Returns True
    if newly created. Non-fatal: connection succeeds even if scaffold
    fails (worst case user sets params manually later).

    Called from the trading connect endpoint (ADR-192 Phase 5) so every
    trader gets a starting risk posture immediately.
    """
    try:
        from services.risk_gate import RISK_MD_PATH, scaffold_default_risk_md

        # Check existence. Workspace-keyed (ADR-407 D1): this is the
        # idempotency guard, and `write_revision` below already keys the
        # workspace — a caller-keyed probe could miss an existing file and
        # scaffold defaults over the workspace's real risk posture.
        existing = service_client.table("workspace_files").select("id").eq(
            *substrate_scope_filter(user_id)
        ).eq("path", RISK_MD_PATH).limit(1).execute()
        if existing.data:
            logger.info(f"[TRADING] _risk.md already exists for {user_id}; skipping scaffold")
            return False

        # Create with conservative defaults (ADR-209: through Authored Substrate).
        from services.authored_substrate import write_revision

        content = scaffold_default_risk_md()
        write_revision(
            service_client,
            user_id=user_id,
            path=RISK_MD_PATH,
            content=content,
            authored_by="system:trading-risk-scaffold",
            message="scaffold _risk.md with conservative defaults",
            summary="Default risk parameters (conservative). Review + adjust before autonomous trading.",
            content_type="text/markdown",
        )
        logger.info(f"[TRADING] Scaffolded _risk.md with conservative defaults for {user_id}")
        return True
    except Exception as e:
        logger.warning(f"[TRADING] _risk.md scaffold failed for {user_id}: {e}")
        return False


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
    ).eq(*account_scope_filter(auth.user_id)).eq("platform", "trading").eq(
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
