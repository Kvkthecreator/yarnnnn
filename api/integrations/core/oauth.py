"""
OAuth flow management for integrations.

Handles OAuth authorization flows for Slack, Notion, etc.
Each provider has specific OAuth requirements and token formats.
"""

import base64
import binascii
import hashlib
import hmac
import json
import os
import logging
import secrets
from typing import Optional
from datetime import datetime, timezone
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
    # ADR-147: GitHub platform integration
    "github": OAuthConfig(
        provider="github",
        client_id_env="GITHUB_CLIENT_ID",
        client_secret_env="GITHUB_CLIENT_SECRET",
        authorize_url="https://github.com/login/oauth/authorize",
        token_url="https://github.com/login/oauth/access_token",
        # ADR-576 D1 — GitHub is a READ connector. `repo` (full read+write on
        # every private repo: code, secrets, Actions, force-push, ref deletion)
        # was held under the D9 write-ready invariant for a `write_github`
        # capability that has never existed. The write path it justified
        # (github_client.create_issue) had zero callers and is deleted.
        #
        # Trade recorded in the ADR: `public_repo` covers PUBLIC repos only.
        # Private-repo metadata is unreachable on a classic OAuth app by any
        # scope narrower than `repo`, so private repos leave the read surface.
        # Restoring them belongs to the GitHub App / fine-grained-PAT migration
        # (ADR-576 §5), which grants metadata:read + contents:read WITHOUT any
        # write authority — not to re-widening this list.
        scopes=[
            "repo:status",  # commit statuses (read)
            "public_repo",  # public repo metadata, issues, releases (read)
            "read:org",     # org-team repo visibility (see list_repos affiliation)
            "read:user",    # user profile info (login/id/avatar) — oauth.py callback
        ],
        redirect_path="/api/integrations/github/callback",
    ),
    # ADR-353 §15a: Reddit OAuth (BYO-credentials — operator/YARNNN registers a
    # Reddit app; §16 BYO-cred path). Token lands in platform_connections;
    # the Composio driver executes with it (Phase-1: YARNNN owns auth, Composio
    # owns execution — there is NO first-party reddit client).
    "reddit": OAuthConfig(
        provider="reddit",
        client_id_env="REDDIT_CLIENT_ID",
        client_secret_env="REDDIT_CLIENT_SECRET",
        authorize_url="https://www.reddit.com/api/v1/authorize",
        token_url="https://www.reddit.com/api/v1/access_token",
        scopes=[
            "identity",   # who the connected account is (metadata)
            "submit",     # submit posts (write_reddit)
            "read",       # read comments/listings (read_reddit / perceive)
        ],
        redirect_path="/api/integrations/reddit/callback",
    ),
    # ADR-131: Gmail and Calendar OAuth configs removed (sunset)
}


# =============================================================================
# ADR-392 D9 — write-ready-by-construction invariant
#
# A connection is BOTH a peripheral-for-context-in (ADR-392) and a driver-for-
# work-out (ADR-353): an active platform_connections row satisfies both the
# read_{platform} (feeds: context) and write_{platform} (feeds: action)
# capabilities on the same gate (orchestration.py CAPABILITIES). So the OAuth
# connect flow MUST request the read+write scope UNION — otherwise a later
# write_{platform} is capability-available but FAILS at execution for lack of the
# write scope, forcing a re-auth. The connect flow requesting write scopes up
# front is what makes a connection write-ready by construction.
#
# ADR-576 D1.a — the invariant is BIDIRECTIONAL. It is not "a write capability
# implies its scope"; it is "a write capability and its write scope imply each
# other". The original one-directional form was structurally blind in the other
# direction: GitHub held `repo` (force-push on every private repo) for a
# `write_github` capability that never existed, and nothing could notice —
# `connection_is_write_ready` only fails when a capability LACKS its scope.
#
# The reverse half is a GATE assertion, not a runtime branch (an over-broad
# grant is a review-time defect, not a request-time one): see
# test_adr576_github_connector.py, which derives BOTH directions from
# CAPABILITIES + WRITE_SCOPE_MARKERS so neither list can drift alone.
#
# Today the forward half holds for the first-party providers (slack: chat:write
# + im:write; notion: app-level, no per-OAuth scope; github: no write capability,
# so no marker). This map makes the invariant EXPLICIT and the validator below
# GUARDS the forward half: adding a provider that ships a write_{platform}
# capability but read-only OAuth scopes fails the check loudly instead of
# shipping a connection that can't write. `None` = no write scope is claimed —
# either the authority is not expressed as an OAuth scope (notion's app-level
# model; a Composio-BYO provider whose scopes it owns), or the provider ships no
# write capability at all (github) — exempt either way.
WRITE_SCOPE_MARKERS: dict[str, Optional[list[str]]] = {
    "slack": ["chat:write", "im:write"],
    # ADR-576 D1 — GitHub ships NO write_github capability, so it declares no
    # write scope. This is an exemption by absence-of-capability, distinct from
    # notion's exemption by not-scope-expressed. D1.a makes the invariant
    # BIDIRECTIONAL: a marker here with no write_{platform} capability now
    # fails CI, so this entry cannot silently regrow a scope nothing exercises.
    "github": None,
    "notion": None,   # write authority set at the Notion app level, not per-OAuth
    "reddit": ["submit"],
}


def connection_is_write_ready(provider: str) -> bool:
    """Does provider's OAuth config request enough scope to accommodate its
    kernel-universal write_{platform} capability (ADR-392 D9)?

    True when: the provider is exempt (marker is None — write not scope-expressed),
    OR at least one of its write-scope markers is present in its configured scopes.
    A provider with NO OAuth config is trivially not write-ready.
    """
    cfg = OAUTH_CONFIGS.get(provider)
    if cfg is None:
        return False
    markers = WRITE_SCOPE_MARKERS.get(provider, None)
    if markers is None:
        # Either explicitly exempt, or an unknown provider with no declared marker
        # (treated as exempt — no write capability assumed until declared).
        return True
    return any(any(m in s for s in cfg.scopes) for m in markers)


# =============================================================================
# OAuth State Management (ADR-531)
#
# The state parameter is SELF-CARRYING: a signed token holding its own payload,
# not a lookup key into server memory. The predecessor was a module-global dict,
# which made a successful callback conditional on landing in the same process
# that issued the state — false on every redeploy (prod deploys from `main`),
# and false ~(1 - 1/N) of the time under multi-worker serving. That produced
# "Invalid or expired OAuth state" with no way to distinguish a lost state from
# an expired one.
#
# Shape: base64url(payload_json) + "." + base64url(HMAC-SHA256(payload)).
# Signed with INTEGRATION_ENCRYPTION_KEY — already required at boot (main.py)
# and already present on API + Scheduler, so this adds no env var and no table.
# The key is used as opaque HMAC key material here; this neither performs nor
# weakens the Fernet token encryption that owns the same secret.
#
# CSRF protection is unchanged in kind: the payload carries a 32-byte nonce and
# the signature makes the whole token unforgeable without the server secret.
#
# Not one-time-use. The dict version consumed state on read; a signed token
# cannot without the storage this removes. The exposure is a replay of the SAME
# user's own authorization inside the TTL window, which re-runs an idempotent
# upsert for that user — meaningfully narrower than the outage it replaces.
# =============================================================================

OAUTH_STATE_TTL_SECONDS = 600  # 10 minutes — a consent flow, not a session


class OAuthStateError(ValueError):
    """An OAuth state failed validation.

    `reason` names WHICH failure occurred, so a redirect and a log line can say
    something diagnosable instead of collapsing malformed / tampered / expired
    into one string.
    """

    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason


def _oauth_state_signing_key() -> bytes:
    key = os.getenv("INTEGRATION_ENCRYPTION_KEY")
    if not key:
        # Boot already requires this (main.py). Failing loudly here beats
        # signing with a default nobody rotates.
        raise RuntimeError(
            "INTEGRATION_ENCRYPTION_KEY is required to sign OAuth state"
        )
    return key.encode("utf-8")


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def generate_oauth_state(user_id: str, provider: str, redirect_to: Optional[str] = None) -> str:
    """Mint a signed, self-carrying state parameter for an OAuth flow.

    The token survives redeploys and multi-instance serving because it holds
    its own payload — no server-side lookup is involved.
    """
    payload = {
        "uid": user_id,
        "prv": provider,
        "rdr": redirect_to,
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "nonce": secrets.token_urlsafe(24),
    }
    body = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature = hmac.new(
        _oauth_state_signing_key(), body.encode("ascii"), hashlib.sha256
    ).digest()
    return f"{body}.{_b64url_encode(signature)}"


def validate_oauth_state(state: str) -> tuple[str, str, Optional[str]]:
    """Verify a signed state and return (user_id, provider, redirect_to).

    Raises OAuthStateError with a specific `reason` on failure:
      malformed  — not a signed token at all (truncated / wrong shape)
      bad_signature — signature mismatch (tampered, or a different deploy secret)
      expired    — issued more than OAUTH_STATE_TTL_SECONDS ago
    """
    if not state or state.count(".") != 1:
        raise OAuthStateError("malformed", "OAuth state is malformed")

    body, provided_signature = state.split(".", 1)

    expected = hmac.new(
        _oauth_state_signing_key(), body.encode("ascii"), hashlib.sha256
    ).digest()
    try:
        provided = _b64url_decode(provided_signature)
    except (ValueError, binascii.Error):
        raise OAuthStateError("malformed", "OAuth state is malformed")

    # Constant-time — a signature check that leaks timing is not a check.
    if not hmac.compare_digest(expected, provided):
        raise OAuthStateError("bad_signature", "OAuth state signature is invalid")

    try:
        payload = json.loads(_b64url_decode(body))
    except (ValueError, binascii.Error):
        raise OAuthStateError("malformed", "OAuth state is malformed")

    issued_at = payload.get("iat")
    if not isinstance(issued_at, int):
        raise OAuthStateError("malformed", "OAuth state is malformed")

    age = datetime.now(timezone.utc).timestamp() - issued_at
    if age > OAUTH_STATE_TTL_SECONDS:
        raise OAuthStateError(
            "expired",
            "OAuth state expired — the connection took too long to authorize",
        )

    user_id = payload.get("uid")
    provider = payload.get("prv")
    if not user_id or not provider:
        raise OAuthStateError("malformed", "OAuth state is malformed")

    return (user_id, provider, payload.get("rdr"))


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
    elif provider == "github":
        # ADR-147: GitHub OAuth — standard OAuth 2.0 with scope
        params = {
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "scope": " ".join(config.scopes),
            "state": state,
        }
    elif provider == "reddit":
        # ADR-353 §15a: Reddit OAuth — response_type=code, space-joined scopes,
        # duration=permanent to receive a refresh token (Reddit access tokens
        # expire in 1h; refresh keeps the connection alive without re-auth).
        params = {
            "client_id": config.client_id,
            "response_type": "code",
            "state": state,
            "redirect_uri": config.redirect_uri,
            "duration": "permanent",
            "scope": " ".join(config.scopes),
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
    # Validate state — raises OAuthStateError (a ValueError) naming the reason.
    user_id, expected_provider, redirect_to = validate_oauth_state(state)
    if expected_provider != provider:
        raise OAuthStateError(
            "provider_mismatch", "OAuth state was issued for a different provider"
        )

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

        elif provider == "github":
            # ADR-147: GitHub token exchange
            # Must request JSON response (GitHub defaults to form-encoded)
            response = await client.post(
                config.token_url,
                headers={"Accept": "application/json"},
                data={
                    "client_id": config.client_id,
                    "client_secret": config.client_secret,
                    "code": code,
                    "redirect_uri": config.redirect_uri,
                },
            )
            data = response.json()

            if "error" in data:
                raise ValueError(f"GitHub OAuth error: {data.get('error_description', data.get('error'))}")

            token_manager = get_token_manager()

            # Fetch user profile for metadata
            user_response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"token {data['access_token']}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            user_data = user_response.json() if user_response.status_code == 200 else {}

            return {
                "user_id": user_id,
                "platform": provider,
                "credentials_encrypted": token_manager.encrypt(data["access_token"]),
                "refresh_token_encrypted": (
                    token_manager.encrypt(data["refresh_token"])
                    if data.get("refresh_token")
                    else None
                ),
                "metadata": {
                    "login": user_data.get("login"),
                    "github_user_id": user_data.get("id"),
                    "avatar_url": user_data.get("avatar_url"),
                    "name": user_data.get("name"),
                    "scope": data.get("scope"),
                    "token_type": data.get("token_type"),
                },
                "status": IntegrationStatus.ACTIVE.value,
                "redirect_to": redirect_to,
            }

        elif provider == "reddit":
            # ADR-353 §15a: Reddit token exchange — HTTP Basic auth
            # (client_id:secret), a descriptive User-Agent is REQUIRED by Reddit
            # or the request is rejected/ratelimited. duration=permanent (set at
            # authorize time) returns a refresh_token.
            import base64
            basic = base64.b64encode(
                f"{config.client_id}:{config.client_secret}".encode()
            ).decode()
            response = await client.post(
                config.token_url,
                headers={
                    "Authorization": f"Basic {basic}",
                    "User-Agent": "yarnnn/1.0 (alpha-author publishing; ADR-353)",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": config.redirect_uri,
                },
            )
            data = response.json()
            if "error" in data or "access_token" not in data:
                raise ValueError(
                    f"Reddit OAuth error: {data.get('error', 'no access_token in response')}"
                )

            token_manager = get_token_manager()

            # Fetch the connected account's identity for metadata (who posts).
            me = await client.get(
                "https://oauth.reddit.com/api/v1/me",
                headers={
                    "Authorization": f"Bearer {data['access_token']}",
                    "User-Agent": "yarnnn/1.0 (alpha-author publishing; ADR-353)",
                },
            )
            me_data = me.json() if me.status_code == 200 else {}

            return {
                "user_id": user_id,
                "platform": provider,
                "credentials_encrypted": token_manager.encrypt(data["access_token"]),
                "refresh_token_encrypted": (
                    token_manager.encrypt(data["refresh_token"])
                    if data.get("refresh_token")
                    else None
                ),
                "metadata": {
                    "reddit_username": me_data.get("name"),
                    "reddit_id": me_data.get("id"),
                    "scope": data.get("scope"),
                    "token_type": data.get("token_type"),
                    "expires_in": data.get("expires_in"),
                },
                "status": IntegrationStatus.ACTIVE.value,
                "redirect_to": redirect_to,
            }

        else:
            raise ValueError(f"Unsupported provider: {provider}")


# The Connectors pane, spelled as the frontend actually reads it. ADR-358 D6
# namespaces the account door's pane under `settings.pane`; a flat `?tab=` is a
# legacy alias whose value must still be a real pane key. ADR-531: the error
# branch used to emit `tab=integrations` — not a pane the settings page accepts
# (ALL_PANES is ["account", "connectors"]), so every failed OAuth silently fell
# back to the Account pane and the operator never saw the door they came from.
CONNECTORS_PANE_PATH = "/settings?settings.pane=connectors"


def get_frontend_redirect_url(
    success: bool,
    provider: str,
    error: Optional[str] = None,
    error_reason: Optional[str] = None,
    redirect_to: Optional[str] = None,
) -> str:
    """
    Get the URL to redirect the user to after OAuth.

    Default redirect to /workfloor with provider + status params (ADR-139).
    Auto-selection + sync already kicked off in callback — user lands on
    workfloor to see bootstrap progress. If redirect_to is provided,
    return there instead — this handles reconnects from other pages.

    On error, returns to the CONNECTORS pane (ADR-531) carrying provider +
    status + error, and `error_reason` — a stable machine token the pane maps
    to recovery copy, so the operator-facing text never depends on parsing a
    human sentence.
    """
    base_url = os.getenv("FRONTEND_URL", "https://yarnnn.com")

    if success:
        redirect_provider = provider
        params = {
            "provider": redirect_provider,
            "status": "connected",
        }
        # Use caller-specified path if provided, otherwise default to /workfloor
        target_path = redirect_to if redirect_to else "/workfloor"
        # Handle redirect_to that already has query params (e.g. /settings?settings.pane=connectors)
        separator = "&" if "?" in target_path else "?"
        return f"{base_url}{target_path}{separator}{urlencode(params)}"

    # On error, land back on the Connectors pane — the door the operator
    # actually came from, where the failed connector's row is visible.
    params = {
        "provider": provider,
        "status": "error",
    }
    if error:
        params["error"] = error
    if error_reason:
        params["error_reason"] = error_reason
    return f"{base_url}{CONNECTORS_PANE_PATH}&{urlencode(params)}"
