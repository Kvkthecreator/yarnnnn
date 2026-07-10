"""BYOK — bring-your-own-key: the workspace-scoped LLM provider key (ADR-439).

The enterprise-tier capability where the WORKSPACE's own provider key powers the
member chat lanes (Altitude-2, ADR-408). When engaged, those lane calls resolve to
the customer's key and draw NOTHING from the workspace pool (ADR-409 D2); the
steward (Freddie, embeddings, judgment) always runs on our platform keys (ADR-409
D3), so the meter stays honest.

Scope (ADR-439 D1): ONE key per WORKSPACE, owner-managed. Not per-member (rejected,
§2). Stored as three columns on `workspaces` (migration 213): `byok_enabled` (the
default-OFF toggle), `byok_provider` (which provider), `byok_key_encrypted` (Fernet
ciphertext via the existing TokenManager / INTEGRATION_ENCRYPTION_KEY — no new
crypto). The plaintext key never leaves this module + the router call site.

Availability is gated on tier (`tier_byok_available` — enterprise-only); this module
handles STORAGE + RESOLUTION and does not itself re-check the tier gate (the route
that writes does, and a non-enterprise workspace simply never has the toggle on).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# The providers a BYOK key may be for — the LANE_MODELS prefixes (ADR-411 D5).
# A key is provider-specific: the resolver only returns it for a matching model.
BYOK_PROVIDERS = ("anthropic", "openai", "gemini", "deepseek")


def provider_from_model(model: str) -> str:
    """The provider prefix of a LANE_MODELS string ('anthropic/claude-…' →
    'anthropic'). Bare names (no '/') return themselves."""
    return model.split("/", 1)[0] if "/" in model else model


def get_byok_key(client: Any, workspace_id: Optional[str], provider: str) -> Optional[str]:
    """Resolve the workspace's BYOK plaintext key for a provider, or None.

    Returns the decrypted key IFF the workspace has BYOK enabled AND a stored key
    for exactly this provider. None means "use the managed default" — the byte-
    identical lower-tier path (our keys). Fail-safe to None on any error: a resolver
    failure must never break a member's turn; it falls back to managed metering.

    This is the ONE read the lane runner calls per turn. Keep it cheap + total.
    """
    if not workspace_id:
        return None
    try:
        result = (
            client.table("workspaces")
            .select("byok_enabled, byok_provider, byok_key_encrypted")
            .eq("id", workspace_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            return None
        row = rows[0]
        if not row.get("byok_enabled"):
            return None
        if row.get("byok_provider") != provider:
            return None  # a key for a different provider doesn't apply to this model
        ciphertext = row.get("byok_key_encrypted")
        if not ciphertext:
            return None
        from integrations.core.tokens import get_token_manager
        return get_token_manager().decrypt(ciphertext)
    except Exception as e:
        logger.warning(f"[BYOK] get_byok_key failed for workspace {workspace_id}: {e}")
        return None


def get_byok_status(client: Any, workspace_id: Optional[str]) -> dict:
    """The legibility view for the FE (never returns the key or ciphertext).

    Shape: {enabled: bool, provider: str|None, configured: bool}. `configured` is
    True iff a key is stored (so the FE can show 'key set' without exposing it)."""
    default = {"enabled": False, "provider": None, "configured": False}
    if not workspace_id:
        return default
    try:
        result = (
            client.table("workspaces")
            .select("byok_enabled, byok_provider, byok_key_encrypted")
            .eq("id", workspace_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            return default
        row = rows[0]
        return {
            "enabled": bool(row.get("byok_enabled")),
            "provider": row.get("byok_provider"),
            "configured": bool(row.get("byok_key_encrypted")),
        }
    except Exception as e:
        logger.warning(f"[BYOK] get_byok_status failed for workspace {workspace_id}: {e}")
        return default


def set_byok_key(
    client: Any,
    workspace_id: str,
    provider: str,
    plaintext_key: str,
) -> None:
    """Store a workspace's BYOK key for a provider (encrypted) and enable the toggle.

    The caller (the route) is responsible for the tier gate + auth. `provider` must
    be one of BYOK_PROVIDERS. Raises ValueError on a bad provider or empty key so
    the route returns a clean 400."""
    if provider not in BYOK_PROVIDERS:
        raise ValueError(f"unknown BYOK provider {provider!r}; expected one of {BYOK_PROVIDERS}")
    if not plaintext_key or not plaintext_key.strip():
        raise ValueError("BYOK key is empty")
    from integrations.core.tokens import get_token_manager
    ciphertext = get_token_manager().encrypt(plaintext_key.strip())
    (
        client.table("workspaces")
        .update(
            {
                "byok_enabled": True,
                "byok_provider": provider,
                "byok_key_encrypted": ciphertext,
            }
        )
        .eq("id", workspace_id)
        .execute()
    )


def set_byok_enabled(client: Any, workspace_id: str, enabled: bool) -> None:
    """Toggle BYOK on/off without changing the stored key. Turning it OFF reverts
    the workspace to the managed default (our keys) while KEEPING the key on file
    so the operator can re-enable without re-entering it."""
    (
        client.table("workspaces")
        .update({"byok_enabled": bool(enabled)})
        .eq("id", workspace_id)
        .execute()
    )


def clear_byok_key(client: Any, workspace_id: str) -> None:
    """Remove the stored key and disable BYOK (a full teardown)."""
    (
        client.table("workspaces")
        .update(
            {
                "byok_enabled": False,
                "byok_provider": None,
                "byok_key_encrypted": None,
            }
        )
        .eq("id", workspace_id)
        .execute()
    )


__all__ = [
    "BYOK_PROVIDERS",
    "provider_from_model",
    "get_byok_key",
    "get_byok_status",
    "set_byok_key",
    "set_byok_enabled",
    "clear_byok_key",
]
