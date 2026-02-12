"""
OAuth flow management for integrations.

Handles OAuth authorization flows for Slack, Notion, etc.
Each provider has specific OAuth requirements and token formats.
"""

import os
import logging
import secrets
from typing import Optional
from datetime import datetime, timedelta
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
    # ADR-029: Gmail integration (legacy, redirects to google)
    "gmail": OAuthConfig(
        provider="gmail",
        client_id_env="GOOGLE_CLIENT_ID",
        client_secret_env="GOOGLE_CLIENT_SECRET",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        scopes=[
            # Gmail: Full access for context + deliverable export
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.compose",
            "https://www.googleapis.com/auth/gmail.modify",
            # Calendar: Full access for context + event creation
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.events.readonly",
            "https://www.googleapis.com/auth/calendar.events",
        ],
        redirect_path="/api/integrations/gmail/callback",
    ),
    # ADR-046: Google integration (unified Gmail + Calendar)
    # This is the preferred provider name going forward
    "google": OAuthConfig(
        provider="google",
        client_id_env="GOOGLE_CLIENT_ID",
        client_secret_env="GOOGLE_CLIENT_SECRET",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        scopes=[
            # Gmail: Full access for context + deliverable export
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.compose",
            "https://www.googleapis.com/auth/gmail.modify",
            # Calendar: Full access for context + event creation
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.events.readonly",
            "https://www.googleapis.com/auth/calendar.events",
        ],
        redirect_path="/api/integrations/google/callback",
    ),
}


# =============================================================================
# OAuth State Management (in-memory for simplicity, could use Redis)
# =============================================================================

# Maps state -> (user_id, provider, created_at)
_oauth_states: dict[str, tuple[str, str, datetime]] = {}


def generate_oauth_state(user_id: str, provider: str) -> str:
    """Generate a secure state parameter for OAuth."""
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = (user_id, provider, datetime.utcnow())

    # Clean up old states (>10 min)
    cutoff = datetime.utcnow() - timedelta(minutes=10)
    expired = [k for k, v in _oauth_states.items() if v[2] < cutoff]
    for k in expired:
        del _oauth_states[k]

    return state


def validate_oauth_state(state: str) -> Optional[tuple[str, str]]:
    """
    Validate and consume an OAuth state.

    Returns (user_id, provider) if valid, None otherwise.
    """
    if state not in _oauth_states:
        return None

    user_id, provider, created_at = _oauth_states[state]

    # Check expiration (10 min)
    if datetime.utcnow() - created_at > timedelta(minutes=10):
        del _oauth_states[state]
        return None

    # Consume the state (one-time use)
    del _oauth_states[state]
    return (user_id, provider)


# =============================================================================
# OAuth Flow Functions
# =============================================================================

def get_authorization_url(provider: str, user_id: str) -> str:
    """
    Get the OAuth authorization URL for a provider.

    Args:
        provider: Integration provider (slack, notion)
        user_id: User initiating the OAuth flow

    Returns:
        Full authorization URL to redirect user to
    """
    config = OAUTH_CONFIGS.get(provider)
    if not config:
        raise ValueError(f"Unknown provider: {provider}")

    if not config.is_configured:
        raise ValueError(f"{provider} OAuth not configured")

    state = generate_oauth_state(user_id, provider)

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
    elif provider in ("gmail", "google"):
        # ADR-029/046: Google OAuth with offline access for refresh token
        # Supports both Gmail and Calendar scopes
        params = {
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(config.scopes),
            "access_type": "offline",  # Required for refresh token
            "prompt": "consent",  # Force consent to get refresh token
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

    user_id, expected_provider = state_data
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
                "provider": provider,
                "access_token_encrypted": token_manager.encrypt(data["access_token"]),
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
                "provider": provider,
                "access_token_encrypted": token_manager.encrypt(data["access_token"]),
                "refresh_token_encrypted": None,  # Notion tokens don't expire
                "metadata": {
                    "workspace_id": data.get("workspace_id"),
                    "workspace_name": data.get("workspace_name"),
                    "bot_id": data.get("bot_id"),
                    "owner": data.get("owner"),
                },
                "status": IntegrationStatus.ACTIVE.value,
            }

        elif provider in ("gmail", "google"):
            # ADR-029/046: Google OAuth token exchange (Gmail + Calendar)
            response = await client.post(
                config.token_url,
                data={
                    "client_id": config.client_id,
                    "client_secret": config.client_secret,
                    "code": code,
                    "redirect_uri": config.redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            data = response.json()

            if "error" in data:
                raise ValueError(f"Google OAuth error: {data.get('error_description', data.get('error'))}")

            token_manager = get_token_manager()

            # Get user info from Google
            user_info_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {data['access_token']}"}
            )
            user_info = user_info_response.json()

            # Calculate token expiry
            expires_in = data.get("expires_in", 3600)
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            # ADR-046: Determine capabilities from granted scopes
            granted_scope = data.get("scope", "")
            capabilities = []
            if "gmail" in granted_scope:
                capabilities.append("gmail")
            if "calendar" in granted_scope:
                capabilities.append("calendar")

            return {
                "user_id": user_id,
                "provider": provider,
                "access_token_encrypted": token_manager.encrypt(data["access_token"]),
                "refresh_token_encrypted": token_manager.encrypt(data["refresh_token"]) if data.get("refresh_token") else None,
                "metadata": {
                    "email": user_info.get("email"),
                    "name": user_info.get("name"),
                    "picture": user_info.get("picture"),
                    "scope": granted_scope,
                    "expires_at": expires_at.isoformat(),
                    "capabilities": capabilities,  # ADR-046: Track enabled capabilities
                },
                "status": IntegrationStatus.ACTIVE.value,
            }

        else:
            raise ValueError(f"Unsupported provider: {provider}")


def get_frontend_redirect_url(success: bool, provider: str, error: Optional[str] = None) -> str:
    """
    Get the URL to redirect the user to after OAuth.

    ADR-057: Redirects to dashboard for streamlined onboarding flow.
    The dashboard will show the source selection modal automatically.
    On error, redirects to settings page.
    """
    base_url = os.getenv("FRONTEND_URL", "https://yarnnn.com")

    if success:
        # ADR-057: Redirect to dashboard with provider param
        # PlatformSyncStatus will detect this and show source selection modal
        params = {
            "provider": provider,
            "status": "connected",
        }
        return f"{base_url}/dashboard?{urlencode(params)}"
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
