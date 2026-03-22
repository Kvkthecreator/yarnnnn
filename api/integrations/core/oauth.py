"""
OAuth flow management for integrations.

Handles OAuth authorization flows for Slack, Notion, etc.
Each provider has specific OAuth requirements and token formats.
"""

import os
import logging
import secrets
from typing import Optional
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx

from .tokens import get_token_manager
from .types import IntegrationProvider, IntegrationStatus

logger = logging.getLogger(__name__)


# =============================================================================
# OAuth Configuration
# =============================================================================

class OAuthConfig:
    """OAuth configuration for a provider."""

    def __init__(
        self,
        provider: str,
        client_id_env: str,
        client_secret_env: str,
        authorize_url: str,
        token_url: str,
        scopes: list[str],
        redirect_path: str,
    ):
        self.provider = provider
        self.client_id = os.getenv(client_id_env, "")
        self.client_secret = os.getenv(client_secret_env, "")
        self.authorize_url = authorize_url
        self.token_url = token_url
        self.scopes = scopes
        self.redirect_path = redirect_path

    @property
    def redirect_uri(self) -> str:
        """Get the full redirect URI."""
        base_url = os.getenv("API_BASE_URL", "https://yarnnn-api.onrender.com")
        return f"{base_url}{self.redirect_path}"

    @property
    def is_configured(self) -> bool:
        """Check if OAuth credentials are configured."""
        return bool(self.client_id and self.client_secret)


# Provider-specific OAuth configs
OAUTH_CONFIGS: dict[str, OAuthConfig] = {
    "slack": OAuthConfig(
        provider="slack",
        client_id_env="SLACK_CLIENT_ID",
        client_secret_env="SLACK_CLIENT_SECRET",
        authorize_url="https://slack.com/oauth/v2/authorize",
        token_url="https://slack.com/api/oauth.v2.access",
        # ADR-027/030/047: Full scopes for reading, listing, and DMs
        scopes=[
            "chat:write",           # Post messages to channels
            "channels:read",        # List public channels
            "channels:history",     # Read public channel messages
            "channels:join",        # Auto-join public channels (for import)
            "groups:read",          # List private channels
            "groups:history",       # Read private channel messages
            "users:read",           # Get user info
            "im:write",             # ADR-047: Open and write to DM channels
        ],
        redirect_path="/api/integrations/slack/callback",
    ),
    "notion": OAuthConfig(
        provider="notion",
        client_id_env="NOTION_CLIENT_ID",
        client_secret_env="NOTION_CLIENT_SECRET",
        authorize_url="https://api.notion.com/v1/oauth/authorize",
        token_url="https://api.notion.com/v1/oauth/token",
        scopes=[],  # Notion doesn't use scopes in the same way
        redirect_path="/api/integrations/notion/callback",
    ),
    # ADR-131: Gmail and Calendar OAuth configs removed (sunset)
}


# =============================================================================
# OAuth State Management
#
# LIMITATION: In-memory state dict. OAuth flows started on one process/instance
# will fail if the callback lands on a different one. Acceptable for single-instance
# Render deployments. If scaling to multiple instances, migrate to Redis or DB.
# =============================================================================

# Maps state -> (user_id, provider, created_at, redirect_to)
_oauth_states: dict[str, tuple[str, str, datetime, Optional[str]]] = {}


def generate_oauth_state(user_id: str, provider: str, redirect_to: Optional[str] = None) -> str:
    """Generate a secure state parameter for OAuth."""
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = (user_id, provider, datetime.now(timezone.utc), redirect_to)

    # Clean up old states (>10 min)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    expired = [k for k, v in _oauth_states.items() if v[2] < cutoff]
    for k in expired:
        del _oauth_states[k]

    return state


def validate_oauth_state(state: str) -> Optional[tuple[str, str, Optional[str]]]:
    """
    Validate and consume an OAuth state.

    Returns (user_id, provider, redirect_to) if valid, None otherwise.
    """
    if state not in _oauth_states:
        return None

    user_id, provider, created_at, redirect_to = _oauth_states[state]

    # Check expiration (10 min)
    if datetime.now(timezone.utc) - created_at > timedelta(minutes=10):
        del _oauth_states[state]
        return None

    # Consume the state (one-time use)
    del _oauth_states[state]
    return (user_id, provider, redirect_to)


# =============================================================================
# OAuth Flow Functions
# =============================================================================

def get_authorization_url(provider: str, user_id: str, redirect_to: Optional[str] = None) -> str:
    """
    Get the OAuth authorization URL for a provider.

    Args:
        provider: Integration provider (slack, notion)
        user_id: User initiating the OAuth flow
        redirect_to: Optional frontend path to return to after OAuth (e.g. "/system")

    Returns:
        Full authorization URL to redirect user to
    """
    config = OAUTH_CONFIGS.get(provider)
    if not config:
        raise ValueError(f"Unknown provider: {provider}")

    if not config.is_configured:
        raise ValueError(f"{provider} OAuth not configured")

    state = generate_oauth_state(user_id, provider, redirect_to)

    if provider == "slack":
        params = {
            "client_id": config.client_id,
            "scope": ",".join(config.scopes),
            "redirect_uri": config.redirect_uri,
            "state": state,
        }
    elif provider == "notion":
        params = {
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "response_type": "code",
            "owner": "user",
            "state": state,
        }
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    return f"{config.authorize_url}?{urlencode(params)}"


async def exchange_code_for_token(
    provider: str,
    code: str,
    state: str
) -> dict:
    """
    Exchange an authorization code for access tokens.

    Args:
        provider: Integration provider
        code: Authorization code from OAuth callback
        state: State parameter for validation

    Returns:
        Dict with token info and metadata to store
    """
    # Validate state
    state_data = validate_oauth_state(state)
    if not state_data:
        raise ValueError("Invalid or expired OAuth state")

    user_id, expected_provider, redirect_to = state_data
    if expected_provider != provider:
        raise ValueError("Provider mismatch in OAuth state")

    config = OAUTH_CONFIGS.get(provider)
    if not config:
        raise ValueError(f"Unknown provider: {provider}")

    async with httpx.AsyncClient() as client:
        if provider == "slack":
            response = await client.post(
                config.token_url,
                data={
                    "client_id": config.client_id,
                    "client_secret": config.client_secret,
                    "code": code,
                    "redirect_uri": config.redirect_uri,
                },
            )
            data = response.json()

            if not data.get("ok"):
                raise ValueError(f"Slack OAuth error: {data.get('error')}")

            # Extract tokens and metadata
            token_manager = get_token_manager()

            # Get authed user info (the human who authorized, not the bot)
            authed_user = data.get("authed_user", {})

            return {
                "user_id": user_id,
                "platform": provider,
                "credentials_encrypted": token_manager.encrypt(data["access_token"]),
                "refresh_token_encrypted": None,  # Slack doesn't use refresh tokens
                "metadata": {
                    "team_id": data.get("team", {}).get("id"),
                    "team_name": data.get("team", {}).get("name"),
                    "workspace_name": data.get("team", {}).get("name"),
                    "bot_user_id": data.get("bot_user_id"),
                    "authed_user_id": authed_user.get("id"),  # User who authorized - for DMs to "self"
                    "scope": data.get("scope"),
                },
                "status": IntegrationStatus.ACTIVE.value,
                "redirect_to": redirect_to,
            }

        elif provider == "notion":
            # Notion uses Basic auth for token exchange
            import base64
            auth = base64.b64encode(
                f"{config.client_id}:{config.client_secret}".encode()
            ).decode()

            response = await client.post(
                config.token_url,
                headers={
                    "Authorization": f"Basic {auth}",
                    "Content-Type": "application/json",
                },
                json={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": config.redirect_uri,
                },
            )
            data = response.json()

            if "error" in data:
                raise ValueError(f"Notion OAuth error: {data.get('error')}")

            token_manager = get_token_manager()
            return {
                "user_id": user_id,
                "platform": provider,
                "credentials_encrypted": token_manager.encrypt(data["access_token"]),
                "refresh_token_encrypted": None,  # Notion tokens don't expire
                "metadata": {
                    "workspace_id": data.get("workspace_id"),
                    "workspace_name": data.get("workspace_name"),
                    "bot_id": data.get("bot_id"),
                    "owner": data.get("owner"),
                },
                "status": IntegrationStatus.ACTIVE.value,
                "redirect_to": redirect_to,
            }

        else:
            raise ValueError(f"Unsupported provider: {provider}")


def get_frontend_redirect_url(
    success: bool,
    provider: str,
    error: Optional[str] = None,
    redirect_to: Optional[str] = None,
) -> str:
    """
    Get the URL to redirect the user to after OAuth.

    ADR-113: Default redirect to /dashboard with provider + status params.
    Auto-selection + sync already kicked off in callback — user lands on
    dashboard to see progress. If redirect_to is provided (e.g. "/system"),
    return there instead — this handles reconnects from other pages.
    On error, redirects to settings page.
    """
    base_url = os.getenv("FRONTEND_URL", "https://yarnnn.com")

    if success:
        redirect_provider = provider
        params = {
            "provider": redirect_provider,
            "status": "connected",
        }
        # Use caller-specified path if provided, otherwise default to /dashboard (ADR-113)
        target_path = redirect_to if redirect_to else "/dashboard"
        return f"{base_url}{target_path}?{urlencode(params)}"
    else:
        # On error, go to settings for troubleshooting
        params = {
            "tab": "integrations",
            "provider": provider,
            "status": "error",
        }
        if error:
            params["error"] = error
        return f"{base_url}/settings?{urlencode(params)}"
