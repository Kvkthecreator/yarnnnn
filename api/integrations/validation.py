"""
Integration Validation - ADR-047

Validation tests run during onboarding to discover platform quirks
before they surface in production.

Usage:
    from integrations.validation import validate_integration, IntegrationHealth

    result = await validate_integration(auth, "slack")
    print(result.to_dict())
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
import logging

from .platform_registry import get_platform_config, validate_params

logger = logging.getLogger(__name__)


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class CapabilityStatus:
    """Status of a single capability test."""
    name: str
    status: str  # "ok", "failed", "skipped", "unknown"
    tested_at: Optional[datetime] = None
    error: Optional[str] = None
    details: dict = field(default_factory=dict)


@dataclass
class IntegrationHealth:
    """Health status of a platform integration."""
    provider: str
    status: str  # "healthy", "degraded", "unhealthy", "unknown"
    validated_at: Optional[datetime] = None
    capabilities: dict[str, CapabilityStatus] = field(default_factory=dict)
    quirks_discovered: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to API response format."""
        return {
            "provider": self.provider,
            "status": self.status,
            "validated_at": self.validated_at.isoformat() if self.validated_at else None,
            "capabilities": {
                name: {
                    "status": cap.status,
                    "tested_at": cap.tested_at.isoformat() if cap.tested_at else None,
                    "error": cap.error,
                    **cap.details,
                }
                for name, cap in self.capabilities.items()
            },
            "quirks_discovered": self.quirks_discovered,
            "errors": self.errors,
            "recommendations": self.recommendations,
        }


# =============================================================================
# Validation Functions
# =============================================================================

async def validate_integration(auth: Any, provider: str) -> IntegrationHealth:
    """
    Run validation tests for a platform integration.

    This should be called after OAuth completes to verify the integration works.

    Args:
        auth: Auth context with user_id and client
        provider: Platform provider name (slack, gmail, notion)

    Returns:
        IntegrationHealth with detailed test results
    """
    health = IntegrationHealth(
        provider=provider,
        status="unknown",
        validated_at=datetime.now(timezone.utc),
    )

    config = get_platform_config(provider)
    if not config:
        health.status = "unknown"
        health.errors.append(f"Unknown provider: {provider}")
        return health

    try:
        # 1. Validate auth/credentials
        auth_result = await _test_auth(auth, provider, config)
        health.capabilities["auth"] = auth_result

        if auth_result.status != "ok":
            health.status = "unhealthy"
            health.errors.append(f"Auth failed: {auth_result.error}")
            return health

        # 2. Test read capabilities
        read_result = await _test_read(auth, provider, config)
        health.capabilities["read"] = read_result

        # 3. Test write capabilities (if safe)
        write_result = await _test_write(auth, provider, config, read_result.details)
        health.capabilities["write"] = write_result

        # 4. Determine overall status
        statuses = [cap.status for cap in health.capabilities.values()]
        if all(s == "ok" for s in statuses):
            health.status = "healthy"
        elif any(s == "failed" for s in statuses):
            health.status = "degraded"
        else:
            health.status = "healthy"

        # 5. Add known quirks from registry
        health.quirks_discovered = config.get("quirks", [])

        # 6. Generate recommendations
        health.recommendations = _generate_recommendations(health, config)

    except Exception as e:
        logger.error(f"[VALIDATION] Error validating {provider}: {e}")
        health.status = "unhealthy"
        health.errors.append(str(e))

    return health


async def _test_auth(auth: Any, provider: str, config: dict) -> CapabilityStatus:
    """Test authentication is valid."""
    result = CapabilityStatus(
        name="auth",
        status="unknown",
        tested_at=datetime.now(timezone.utc),
    )

    try:
        # Check integration exists and is active
        integration = auth.client.table("platform_connections").select(
            "status, metadata"
        ).eq("user_id", auth.user_id).eq("platform", provider).single().execute()

        if not integration.data:
            result.status = "failed"
            result.error = f"No {provider} integration found"
            return result

        if integration.data.get("status") != "active":
            result.status = "failed"
            result.error = f"Integration status is {integration.data.get('status')}, expected 'active'"
            return result

        # Check required metadata
        metadata = integration.data.get("metadata", {}) or {}
        auth_config = config.get("auth", {})
        required_metadata = auth_config.get("metadata_required", [])

        missing = [k for k in required_metadata if not metadata.get(k)]
        if missing:
            result.status = "failed"
            result.error = f"Missing metadata: {', '.join(missing)}"
            return result

        result.status = "ok"
        result.details = {"metadata_keys": list(metadata.keys())}

    except Exception as e:
        result.status = "failed"
        result.error = str(e)

    return result


async def _test_read(auth: Any, provider: str, config: dict) -> CapabilityStatus:
    """Test read capabilities (list resources)."""
    result = CapabilityStatus(
        name="read",
        status="unknown",
        tested_at=datetime.now(timezone.utc),
    )

    try:
        if provider == "slack":
            result = await _test_slack_read(auth, result)
        elif provider == "gmail":
            result = await _test_gmail_read(auth, result)
        elif provider == "notion":
            result = await _test_notion_read(auth, result)
        else:
            result.status = "skipped"
            result.details["reason"] = "No read test for this provider"

    except Exception as e:
        result.status = "failed"
        result.error = str(e)

    return result


async def _test_slack_read(auth: Any, result: CapabilityStatus) -> CapabilityStatus:
    """Test Slack read capabilities."""
    from integrations.core.client import get_mcp_manager
    from integrations.core.tokens import get_token_manager

    # Get credentials
    integration = auth.client.table("platform_connections").select(
        "credentials_encrypted, metadata"
    ).eq("user_id", auth.user_id).eq("platform", "slack").single().execute()

    if not integration.data:
        result.status = "failed"
        result.error = "No Slack integration"
        return result

    token_manager = get_token_manager()
    access_token = token_manager.decrypt(integration.data["credentials_encrypted"])
    team_id = integration.data.get("metadata", {}).get("team_id")

    if not team_id:
        result.status = "failed"
        result.error = "Missing team_id in metadata"
        return result

    # Try listing channels
    mcp = get_mcp_manager()
    channels = await mcp.list_slack_channels(
        user_id=auth.user_id,
        bot_token=access_token,
        team_id=team_id,
    )

    result.status = "ok"
    result.details = {
        "channels_found": len(channels),
        "first_channel": channels[0] if channels else None,
    }

    return result


async def _test_gmail_read(auth: Any, result: CapabilityStatus) -> CapabilityStatus:
    """Test Gmail read capabilities."""
    import os
    from integrations.core.client import get_mcp_manager
    from integrations.core.tokens import get_token_manager

    # Get credentials
    integration = auth.client.table("platform_connections").select(
        "credentials_encrypted, metadata"
    ).eq("user_id", auth.user_id).eq("platform", "gmail").single().execute()

    if not integration.data:
        result.status = "failed"
        result.error = "No Gmail integration"
        return result

    metadata = integration.data.get("metadata", {}) or {}
    refresh_token = metadata.get("refresh_token")

    if not refresh_token:
        result.status = "failed"
        result.error = "Missing refresh_token in metadata"
        return result

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        result.status = "failed"
        result.error = "Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET"
        return result

    # Try listing messages
    mcp = get_mcp_manager()
    messages = await mcp.list_gmail_messages(
        user_id=auth.user_id,
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token,
        max_results=1,
    )

    result.status = "ok"
    result.details = {
        "messages_found": len(messages),
        "can_list": True,
    }

    return result


async def _test_notion_read(auth: Any, result: CapabilityStatus) -> CapabilityStatus:
    """Test Notion read capabilities."""
    from integrations.core.client import get_mcp_manager
    from integrations.core.tokens import get_token_manager

    # Get credentials
    integration = auth.client.table("platform_connections").select(
        "credentials_encrypted"
    ).eq("user_id", auth.user_id).eq("platform", "notion").single().execute()

    if not integration.data:
        result.status = "failed"
        result.error = "No Notion integration"
        return result

    token_manager = get_token_manager()
    access_token = token_manager.decrypt(integration.data["credentials_encrypted"])

    # ADR-050: Search pages via MCP Gateway (Node.js), not Python MCP client
    from services.mcp_gateway import call_platform_tool, is_gateway_available

    if not is_gateway_available():
        result.status = "failed"
        result.error = "MCP Gateway not available"
        return result

    gateway_result = await call_platform_tool(
        provider="notion",
        tool="notion-search",
        args={"query": ""},
        token=access_token,
        metadata=integration.data.get("metadata"),
    )

    if not gateway_result.get("success"):
        result.status = "failed"
        result.error = gateway_result.get("error", "Notion search failed")
        return result

    pages = gateway_result.get("result", {}).get("results", [])
    if not isinstance(pages, list):
        pages = []

    result.status = "ok"
    result.details = {
        "pages_found": len(pages),
        "first_page": pages[0] if pages else None,
    }

    return result


async def _test_write(
    auth: Any,
    provider: str,
    config: dict,
    read_details: dict
) -> CapabilityStatus:
    """
    Test write capabilities.

    Note: We don't actually send messages in validation - we just verify
    the path would work (credentials valid, target exists).
    """
    result = CapabilityStatus(
        name="write",
        status="unknown",
        tested_at=datetime.now(timezone.utc),
    )

    # For now, just mark as skipped with note
    # Real write tests would send to a test channel/draft
    result.status = "skipped"
    result.details = {
        "reason": "Write test skipped (would send actual message)",
        "recommendation": "Test manually with platform.send to a test channel",
    }

    # Could add dry-run validation here:
    # - Validate channel exists (Slack)
    # - Validate email format (Gmail)
    # - Validate page access (Notion)

    return result


def _generate_recommendations(health: IntegrationHealth, config: dict) -> list[str]:
    """Generate recommendations based on validation results."""
    recommendations = []

    # Check for common issues
    for cap_name, cap in health.capabilities.items():
        if cap.status == "failed":
            if "team_id" in (cap.error or ""):
                recommendations.append(
                    "Re-authenticate Slack to ensure team_id is captured"
                )
            if "refresh_token" in (cap.error or ""):
                recommendations.append(
                    "Re-authenticate Gmail with offline access to get refresh_token"
                )

    # Add platform-specific recommendations
    if config.get("quirks"):
        recommendations.append(
            f"Review known quirks in docs/integrations/QUIRKS.md"
        )

    return recommendations


# =============================================================================
# Quick Validation (for runtime use)
# =============================================================================

def quick_validate_send_params(provider: str, params: dict) -> tuple[bool, list[str]]:
    """
    Quick validation of platform.send parameters.

    Use this in Execute primitive before attempting to send.

    Returns:
        (is_valid, list_of_errors)
    """
    return validate_params(provider, params)
