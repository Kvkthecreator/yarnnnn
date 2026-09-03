"""Attached connectors — an MCP server the member attached, reachable in
their own turn under their own grant (ADR-635).

DISPOSITION (intake-pipeline.md §5, declared here as the ADR requires): an
attached connector is TURN REACH — the member's credential, inside the
member's turn, transient. Its consequential tools are OUTBOUND THROUGH A
PROPOSAL (queued, member-executed, receipted). It is never intake: nothing
lands in the commons unless someone writes it, and an unattended run never
holds the credential (ADR-577 — the same chokepoint refuses agents here).

WHAT AN ATTACHED CONNECTOR IS
One `platform_connections` row keyed `mcp:{slug}` (ADR-635 D2) — the human's
account object (ADR-425), `UNIQUE(user_id, platform)` satisfied by the
prefixed key, no migration. It holds:
  credentials_encrypted     ONE encrypted JSON envelope: the access token,
                            the DCR client id/secret, the token endpoint,
                            the expiry, the resource (and, while pending,
                            the PKCE verifier). Read only through
                            `platform_credentials.resolve_platform_credential`,
                            so an AGENT caller is refused where it is refused
                            Slack.
  refresh_token_encrypted   the refresh token, when the server issued one
  metadata                  server_url · title · name · category · the
                            server's advertised `tools` · the APERTURE

THE APERTURE IS CONSENT, NEVER A DEFAULT (ADR-582, applied to tools).
A fresh attach exposes NO tool. The member picks, tool by tool:
  (unlisted)  → DENY    the tool is not offered to any turn
  "propose"   → QUEUE   every call is an external-write proposal the member
                        executes from the queue (ADR-635 D6 — the first
                        proposal producer since the steward retired)
  "direct"    → APPLY   runs in the member's turn
The server's `readOnlyHint` is shown as a HINT beside the choice and never
decides it — the MCP SDK's own docstring says clients must never make
tool-use decisions from a server's annotations. The mode lives on the
CONNECTION (the grant side), never on an agent or a skill (ADR-596 D2).

ONE GENERIC AUTH FLOW, NO PER-SERVER CODE (ADR-635 D3). RFC 9728 protected-
resource discovery → RFC 8414 authorization-server metadata → RFC 7591
dynamic client registration → PKCE S256 → the same signed state the hand-
authored connectors use. A server that answers anonymously attaches without
a redirect; a server that wants a header takes it as one encrypted field.
Probed live 2026-09-03: Notion and Linear register dynamically with S256;
Context7 answers anonymously.

NAMES ARE THE ECOSYSTEM'S (the ADR-588 rule: resolve, never invent).
A lane sees `mcp__{slug}__{tool}` — the Claude Code convention. The lane
name is DERIVED from the row's tool list at read time; nothing string-
surgeries it back, so a long or odd server tool name round-trips through
the row, never through the name.

This module never composes a frame and never decides a lane's shape: it
answers "what does this member hold, and may this call run" — the lane
runner and the gate ask it.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlencode, urlparse

import httpx

logger = logging.getLogger(__name__)

#: The `platform_connections.platform` prefix for an attached connector.
ATTACHED_PREFIX = "mcp:"
#: The lane-facing tool-name prefix — the ecosystem's convention, adopted.
TOOL_PREFIX = "mcp__"
#: The two ways a tool in the aperture may run (unlisted = denied).
APERTURE_MODES = ("direct", "propose")
#: Provider-facing tool names are bounded at 64 chars by both Anthropic and
#: OpenAI; the lane name is cut + hashed past this, and resolved by lookup.
_MAX_TOOL_NAME = 64
_HTTP_TIMEOUT = httpx.Timeout(15.0, connect=5.0)
#: How long before expiry a token is refreshed proactively.
_REFRESH_SKEW = timedelta(seconds=60)

_SLUG_RX = re.compile(r"[^a-z0-9-]+")
_NAME_RX = re.compile(r"[^A-Za-z0-9_-]+")


# ---------------------------------------------------------------------------
# Keys and names
# ---------------------------------------------------------------------------


def slug_for(server_url: str, hint: Optional[str] = None) -> str:
    """A stable, data-compat slug for one server. The directory's short
    name when it has one (`notion`, `linear`, `context7`), else the host."""
    raw = (hint or "").strip().lower()
    if not raw:
        host = (urlparse(server_url).hostname or "").lower()
        raw = host.removeprefix("mcp.").removeprefix("www.")
        raw = raw.rsplit(".", 1)[0] if raw.count(".") >= 1 else raw
    slug = _SLUG_RX.sub("-", raw).strip("-")
    return slug or "server"


def platform_key(slug: str) -> str:
    return f"{ATTACHED_PREFIX}{slug}"


def is_attached_platform(platform: Optional[str]) -> bool:
    return bool(platform) and str(platform).startswith(ATTACHED_PREFIX)


def slug_from_platform(platform: str) -> str:
    return str(platform)[len(ATTACHED_PREFIX):]


def is_attached_tool(name: Optional[str]) -> bool:
    return bool(name) and str(name).startswith(TOOL_PREFIX)


def lane_tool_name(slug: str, tool: str) -> str:
    """`mcp__{slug}__{tool}`, provider-legal. Past 64 chars the tool part is
    cut and suffixed with a short hash so two long names stay distinct; the
    row's tool list is what maps it back (never string surgery)."""
    part = _NAME_RX.sub("_", tool or "").strip("_") or "tool"
    name = f"{TOOL_PREFIX}{slug}__{part}"
    if len(name) > _MAX_TOOL_NAME:
        digest = hashlib.sha256(tool.encode("utf-8")).hexdigest()[:4]
        head = f"{TOOL_PREFIX}{slug}__"
        keep = _MAX_TOOL_NAME - len(head) - 5
        name = f"{head}{part[:max(keep, 1)]}_{digest}"
    return name


def slug_of_tool_name(name: str) -> Optional[str]:
    """The slug half of a lane tool name, or None if it is not one."""
    if not is_attached_tool(name):
        return None
    rest = name[len(TOOL_PREFIX):]
    slug, sep, _ = rest.partition("__")
    return slug if sep else None


# ---------------------------------------------------------------------------
# The envelope (what lives in credentials_encrypted)
# ---------------------------------------------------------------------------


def _encrypt(payload: dict) -> str:
    from integrations.core.tokens import get_token_manager

    return get_token_manager().encrypt(json.dumps(payload, separators=(",", ":")))


def _decrypt(blob: Optional[str]) -> dict:
    if not blob:
        return {}
    from integrations.core.tokens import get_token_manager

    try:
        raw = get_token_manager().decrypt(blob)
        data = json.loads(raw) if raw else {}
        return data if isinstance(data, dict) else {}
    except Exception as exc:  # noqa: BLE001 — a credential read degrades, never raises
        logger.warning("[ATTACH] envelope decrypt failed: %s", exc)
        return {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Discovery (RFC 9728 → RFC 8414) and registration (RFC 7591)
# ---------------------------------------------------------------------------


def _resource_metadata_url(www_authenticate: str) -> Optional[str]:
    m = re.search(r'resource_metadata="([^"]+)"', www_authenticate or "")
    return m.group(1) if m else None


def _well_known_candidates(server_url: str) -> list[str]:
    """RFC 9728 §3: path-suffixed first, then the host root."""
    u = urlparse(server_url)
    origin = f"{u.scheme}://{u.netloc}"
    path = (u.path or "").rstrip("/")
    out = []
    if path:
        out.append(f"{origin}/.well-known/oauth-protected-resource{path}")
    out.append(f"{origin}/.well-known/oauth-protected-resource")
    return out


def _as_metadata_candidates(issuer: str) -> list[str]:
    """RFC 8414 §3 (path-aware) then the OIDC discovery fallback."""
    u = urlparse(issuer)
    origin = f"{u.scheme}://{u.netloc}"
    path = (u.path or "").rstrip("/")
    out = []
    if path:
        out.append(f"{origin}/.well-known/oauth-authorization-server{path}")
        out.append(f"{origin}{path}/.well-known/openid-configuration")
    out.append(f"{origin}/.well-known/oauth-authorization-server")
    out.append(f"{origin}/.well-known/openid-configuration")
    return out


async def _get_json(http: httpx.AsyncClient, url: str) -> Optional[dict]:
    try:
        r = await http.get(url, headers={"Accept": "application/json"})
        if r.status_code != 200:
            return None
        data = r.json()
        return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001 — discovery is best-effort
        return None


async def discover(server_url: str, *, extra_headers: Optional[dict] = None) -> dict:
    """What this server wants. Returns
    {auth: "none" | "oauth" | "unknown", resource, authorization_servers,
     authorization_endpoint, token_endpoint, registration_endpoint,
     scopes_supported, code_challenge_methods_supported}.

    `auth == "none"` when an unauthenticated initialize succeeds (Context7's
    shape). `"oauth"` when the probe points at protected-resource metadata
    that resolves to an authorization server. `"unknown"` when it answers
    401 but publishes nothing we can follow — the member can still attach
    with a header, or give up honestly.
    """
    out: dict[str, Any] = {"auth": "unknown", "resource": server_url}
    probe_body = {
        "jsonrpc": "2.0", "id": 0, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                   "clientInfo": {"name": "yarnnn", "version": "1"}},
    }
    headers = {"Accept": "application/json, text/event-stream",
               "Content-Type": "application/json"}
    headers.update(extra_headers or {})
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT, follow_redirects=True) as http:
        try:
            probe = await http.post(server_url, json=probe_body, headers=headers)
        except Exception as exc:  # noqa: BLE001
            out["error"] = f"unreachable: {exc}"
            return out
        if probe.status_code == 200:
            out["auth"] = "none"
            return out
        www = probe.headers.get("www-authenticate", "")
        candidates = []
        pointed = _resource_metadata_url(www)
        if pointed:
            candidates.append(pointed)
        candidates.extend(u for u in _well_known_candidates(server_url) if u not in candidates)
        prm = None
        for url in candidates:
            prm = await _get_json(http, url)
            if prm:
                break
        if not prm:
            out["status_code"] = probe.status_code
            return out
        out["resource"] = prm.get("resource") or server_url
        out["scopes_supported"] = prm.get("scopes_supported") or []
        servers = prm.get("authorization_servers") or []
        out["authorization_servers"] = servers
        as_meta = None
        for issuer in servers:
            for url in _as_metadata_candidates(str(issuer)):
                as_meta = await _get_json(http, url)
                if as_meta:
                    break
            if as_meta:
                break
        if not as_meta:
            return out
        out["auth"] = "oauth"
        for key in ("issuer", "authorization_endpoint", "token_endpoint",
                    "registration_endpoint", "code_challenge_methods_supported",
                    "token_endpoint_auth_methods_supported"):
            if key in as_meta:
                out[key] = as_meta[key]
        if not out.get("scopes_supported"):
            out["scopes_supported"] = as_meta.get("scopes_supported") or []
    return out


async def register_client(registration_endpoint: str, redirect_uri: str,
                          scopes: Optional[list] = None) -> dict:
    """RFC 7591 dynamic registration as a PUBLIC client (PKCE carries the
    proof). If the server issues a secret anyway, it is kept and used.

    `scope` is OPTIONAL in RFC 7591 and we long omitted it — but a server may
    require it, and then the refusal reads like policy when it is our request
    that is short a field. Gong answered `invalid_client_metadata: scope is
    required` while advertising `mcp:read mcp:write` in its own
    `scopes_supported` (driven 2026-09-04). Discovery already knows them, so
    send what the server asked for.
    """
    body = {
        "client_name": "yarnnn",
        "client_uri": "https://yarnnn.com",
        "redirect_uris": [redirect_uri],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }
    if scopes:
        body["scope"] = " ".join(str(s) for s in scopes)
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as http:
        r = await http.post(registration_endpoint, json=body,
                            headers={"Accept": "application/json"})
        # A server may refuse a PUBLIC client and want a confidential one with
        # a secret (Gong: `token_endpoint_auth_method is unsupported`, driven
        # 2026-09-04). We already keep and use a secret when one is issued, so
        # the preference for `none` is ours, not a requirement — drop it and
        # let the server pick. One retry, only on that refusal.
        if r.status_code not in (200, 201) and "token_endpoint_auth_method" in r.text:
            retry = {k: v for k, v in body.items() if k != "token_endpoint_auth_method"}
            r = await http.post(registration_endpoint, json=retry,
                                headers={"Accept": "application/json"})
        if r.status_code not in (200, 201):
            raise RuntimeError(f"registration refused ({r.status_code}): {r.text[:200]}")
        data = r.json()
    if not isinstance(data, dict) or not data.get("client_id"):
        raise RuntimeError("registration returned no client_id")
    return {
        "client_id": data["client_id"],
        "client_secret": data.get("client_secret"),
        "token_endpoint_auth_method": data.get("token_endpoint_auth_method") or (
            "client_secret_post" if data.get("client_secret") else "none"
        ),
    }


def _pkce() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


def callback_url() -> str:
    """Where a server sends the member back. The API's own origin, so the
    exchange happens server-side and the token never crosses the browser."""
    # The same variable the hand-authored OAuth configs read (oauth.py).
    base = os.getenv("API_BASE_URL", "https://yarnnn-api.onrender.com").rstrip("/")
    return f"{base}/api/connectors/attach/callback"


# ---------------------------------------------------------------------------
# Rows
# ---------------------------------------------------------------------------

_ROW_COLUMNS = (
    "id, platform, status, metadata, credentials_encrypted, "
    "refresh_token_encrypted, created_at, updated_at"
)


def _scope(user_id: str) -> tuple:
    from services.workspace_context import account_scope_filter

    return account_scope_filter(user_id)


def load_row(client: Any, user_id: str, slug: str) -> Optional[dict]:
    """The row for one attached connector, any status. Never raises."""
    try:
        res = (
            client.table("platform_connections")
            .select(_ROW_COLUMNS)
            .eq(*_scope(user_id))
            .eq("platform", platform_key(slug))
            .limit(1)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[ATTACH] row read failed for %s: %s", slug, exc)
        return None
    rows = res.data or []
    return rows[0] if rows else None


def list_rows(client: Any, user_id: str, *, active_only: bool = True) -> list[dict]:
    """Every attached connector this member holds. Never raises."""
    try:
        q = (
            client.table("platform_connections")
            .select("id, platform, status, metadata, created_at, updated_at")
            .eq(*_scope(user_id))
            .like("platform", f"{ATTACHED_PREFIX}%")
        )
        if active_only:
            q = q.eq("status", "active")
        res = q.order("platform").execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[ATTACH] row list failed: %s", exc)
        return []
    return [r for r in (res.data or []) if is_attached_platform(r.get("platform"))]


def _upsert_row(client: Any, user_id: str, slug: str, fields: dict) -> dict:
    existing = load_row(client, user_id, slug)
    stamped = dict(fields)
    stamped["updated_at"] = _now().isoformat()
    if existing:
        client.table("platform_connections").update(stamped).eq("id", existing["id"]).execute()
        existing.update(stamped)
        return existing
    # `connected_by` — the authorizing member (ADR-431, extended to this table
    # by migration 244, which made it NOT NULL precisely "so a connect door
    # that forgets the stamp fails loudly instead of writing silent
    # unattributable reach"). For an attached connector the authorizing member
    # IS the attaching member: they sign in to the server themselves and the
    # envelope is theirs. Same value as `user_id`, different question.
    stamped.update({
        "user_id": user_id,
        "platform": platform_key(slug),
        "connected_by": user_id,
    })
    res = client.table("platform_connections").insert(stamped).execute()
    rows = res.data or []
    return rows[0] if rows else stamped


def public_view(row: dict) -> dict:
    """What a surface may see: never the envelope."""
    md = row.get("metadata") or {}
    aperture = md.get("aperture") or {}
    tools = md.get("tools") or []
    return {
        "slug": slug_from_platform(row["platform"]),
        "provider": row["platform"],
        "status": row.get("status"),
        "title": md.get("title") or md.get("name") or slug_from_platform(row["platform"]),
        "server_url": md.get("server_url"),
        "category": md.get("category"),
        "auth": md.get("auth"),
        "tools": [
            {
                "name": t.get("name"),
                "lane_name": lane_tool_name(slug_from_platform(row["platform"]), t.get("name") or ""),
                "description": (t.get("description") or "")[:400],
                "read_only_hint": bool((t.get("annotations") or {}).get("readOnlyHint")),
                "mode": aperture.get(t.get("name")),
            }
            for t in tools if t.get("name")
        ],
        "aperture": aperture,
        "exposed": sum(1 for m in aperture.values() if m in APERTURE_MODES),
        "connected_at": row.get("created_at"),
        "last_updated": row.get("updated_at"),
    }


# ---------------------------------------------------------------------------
# Attach
# ---------------------------------------------------------------------------


async def begin_attach(
    auth: Any,
    server_url: str,
    *,
    title: Optional[str] = None,
    slug: Optional[str] = None,
    category: Optional[str] = None,
    header_name: Optional[str] = None,
    header_value: Optional[str] = None,
    redirect_to: Optional[str] = None,
) -> dict:
    """Start attaching one server for the acting member.

    Returns {slug, attached, authorization_url}. `attached` is True when the
    server needed no redirect (anonymous, or header-authenticated) and the
    row is already active with its tools listed — the member picks the
    aperture next. Otherwise `authorization_url` is where to send them.
    """
    from services.platform_credentials import is_agent_caller

    if is_agent_caller(auth):
        raise PermissionError("an agent cannot attach a connector (ADR-577)")
    server_url = (server_url or "").strip()
    if not server_url.startswith("https://"):
        raise ValueError("a connector URL must be https")
    the_slug = slug_for(server_url, slug)
    extra = {header_name: header_value} if (header_name and header_value) else None
    found = await discover(server_url, extra_headers=extra)

    base_md = {
        "server_url": server_url,
        "title": (title or "").strip() or the_slug,
        "name": (title or "").strip() or the_slug,
        "category": (category or "").strip() or None,
        "auth": found.get("auth"),
        "resource": found.get("resource"),
        "aperture": {},
        "tools": [],
    }

    if found.get("auth") == "none" or extra:
        envelope: dict = {}
        if extra:
            envelope = {"header_name": header_name, "header_value": header_value}
        row = _upsert_row(auth.client, auth.user_id, the_slug, {
            "status": "active",
            "credentials_encrypted": _encrypt(envelope) if envelope else None,
            "refresh_token_encrypted": None,
            "metadata": base_md,
        })
        try:
            await refresh_tools(auth, the_slug)
        except Exception as exc:  # noqa: BLE001 — tools can be listed later
            logger.warning("[ATTACH] tool listing failed for %s: %s", the_slug, exc)
        return {"slug": the_slug, "attached": True, "authorization_url": None,
                "auth": found.get("auth")}

    if found.get("auth") != "oauth" or not found.get("authorization_endpoint"):
        raise ValueError(
            "this server requires authentication but publishes no OAuth "
            "metadata yarnnn can follow — attach it with an API key header, "
            "or check the URL"
        )

    redirect_uri = callback_url()
    reg_endpoint = found.get("registration_endpoint")
    if not reg_endpoint:
        raise ValueError(
            "this server does not offer dynamic client registration; a "
            "pre-registered client is not supported yet"
        )
    client_info = await register_client(reg_endpoint, redirect_uri,
                                        found.get("scopes_supported"))
    verifier, challenge = _pkce()
    from integrations.core.oauth import generate_oauth_state

    state = generate_oauth_state(auth.user_id, platform_key(the_slug), redirect_to)
    params = {
        "response_type": "code",
        "client_id": client_info["client_id"],
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "resource": found.get("resource") or server_url,
    }
    scopes = found.get("scopes_supported") or []
    if scopes:
        params["scope"] = " ".join(str(s) for s in scopes)
    pending = {
        "code_verifier": verifier,
        "client_id": client_info["client_id"],
        "client_secret": client_info.get("client_secret"),
        "token_endpoint_auth_method": client_info.get("token_endpoint_auth_method"),
        "token_endpoint": found.get("token_endpoint"),
        "resource": found.get("resource") or server_url,
        "redirect_uri": redirect_uri,
    }
    _upsert_row(auth.client, auth.user_id, the_slug, {
        "status": "pending",
        "credentials_encrypted": _encrypt(pending),
        "refresh_token_encrypted": None,
        "metadata": base_md,
    })
    sep = "&" if "?" in found["authorization_endpoint"] else "?"
    return {
        "slug": the_slug,
        "attached": False,
        "authorization_url": f"{found['authorization_endpoint']}{sep}{urlencode(params)}",
        "auth": "oauth",
    }


def _token_request(pending: dict, grant: dict) -> tuple[dict, Optional[tuple]]:
    """Form body + optional basic auth for the token endpoint."""
    body = dict(grant)
    body["client_id"] = pending["client_id"]
    body["resource"] = pending.get("resource") or ""
    basic = None
    secret = pending.get("client_secret")
    method = pending.get("token_endpoint_auth_method") or "none"
    if secret and method == "client_secret_basic":
        basic = (pending["client_id"], secret)
    elif secret:
        body["client_secret"] = secret
    return body, basic


async def _exchange(pending: dict, grant: dict) -> dict:
    body, basic = _token_request(pending, grant)
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as http:
        r = await http.post(
            pending["token_endpoint"], data=body, auth=basic,
            headers={"Accept": "application/json"},
        )
    if r.status_code != 200:
        raise RuntimeError(f"token endpoint refused ({r.status_code}): {r.text[:200]}")
    data = r.json()
    if not isinstance(data, dict) or not data.get("access_token"):
        raise RuntimeError("token endpoint returned no access_token")
    return data


def _envelope_from_token(pending: dict, token: dict) -> dict:
    expires_in = token.get("expires_in")
    expires_at = None
    if isinstance(expires_in, (int, float)) and expires_in > 0:
        expires_at = (_now() + timedelta(seconds=float(expires_in))).isoformat()
    return {
        "access_token": token["access_token"],
        "token_type": token.get("token_type") or "Bearer",
        "expires_at": expires_at,
        "scope": token.get("scope"),
        "client_id": pending.get("client_id"),
        "client_secret": pending.get("client_secret"),
        "token_endpoint_auth_method": pending.get("token_endpoint_auth_method"),
        "token_endpoint": pending.get("token_endpoint"),
        "resource": pending.get("resource"),
    }


async def complete_attach(service_client: Any, code: str, state: str) -> dict:
    """The callback half: validate the signed state, find the pending row,
    exchange the code, land the row active, list its tools.

    Runs on the SERVICE client (no member session at a redirect), scoped by
    the user_id the state carries — the same posture as the integrations
    callback. Returns {user_id, slug, redirect_to}.
    """
    from integrations.core.oauth import validate_oauth_state

    user_id, platform, redirect_to = validate_oauth_state(state)
    if not is_attached_platform(platform):
        raise ValueError("state was not minted for an attached connector")
    slug = slug_from_platform(platform)
    row = load_row(service_client, user_id, slug)
    if not row or row.get("status") != "pending":
        raise ValueError("no pending attach for this connector")
    pending = _decrypt(row.get("credentials_encrypted"))
    if not pending.get("code_verifier") or not pending.get("token_endpoint"):
        raise ValueError("the pending attach lost its verifier — start again")
    token = await _exchange(pending, {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": pending.get("redirect_uri") or callback_url(),
        "code_verifier": pending["code_verifier"],
    })
    envelope = _envelope_from_token(pending, token)
    from integrations.core.tokens import get_token_manager

    refresh = token.get("refresh_token")
    _upsert_row(service_client, user_id, slug, {
        "status": "active",
        "credentials_encrypted": _encrypt(envelope),
        "refresh_token_encrypted": get_token_manager().encrypt(refresh) if refresh else None,
    })
    try:
        md = dict(row.get("metadata") or {})
        tools = await _list_server_tools(md.get("server_url") or "", envelope)
        md["tools"] = tools
        _upsert_row(service_client, user_id, slug, {"metadata": md})
    except Exception as exc:  # noqa: BLE001 — tools can be listed later
        logger.warning("[ATTACH] tool listing after attach failed for %s: %s", slug, exc)
    return {"user_id": user_id, "slug": slug, "redirect_to": redirect_to}


# ---------------------------------------------------------------------------
# Tokens and tools
# ---------------------------------------------------------------------------


def _auth_headers_from(envelope: dict) -> dict:
    if envelope.get("header_name") and envelope.get("header_value"):
        return {str(envelope["header_name"]): str(envelope["header_value"])}
    if envelope.get("access_token"):
        return {"Authorization": f"Bearer {envelope['access_token']}"}
    return {}


async def _list_server_tools(server_url: str, envelope: dict) -> list[dict]:
    from integrations.core.mcp_client import get_mcp_client

    listed = await get_mcp_client().list_tools(server_url, headers=_auth_headers_from(envelope))
    out = []
    for t in listed:
        out.append({
            "name": t.get("name"),
            "description": (t.get("description") or "")[:1000],
            "input_schema": t.get("input_schema") or {"type": "object"},
            "annotations": t.get("annotations") or {},
        })
    return out


async def _fresh_envelope(auth: Any, slug: str, row: dict) -> Optional[dict]:
    """The envelope with a usable token, refreshing through the stored
    endpoint when expired. None means "not connected" — never a traceback."""
    envelope = _decrypt(row.get("credentials_encrypted"))
    if envelope.get("header_name"):
        return envelope
    if not envelope.get("access_token"):
        # Anonymous server: an empty envelope is a valid one.
        return envelope if (row.get("metadata") or {}).get("auth") == "none" else None
    expires_at = envelope.get("expires_at")
    if expires_at:
        try:
            exp = datetime.fromisoformat(str(expires_at))
        except ValueError:
            exp = None
        if exp and exp - _REFRESH_SKEW <= _now():
            from integrations.core.tokens import get_token_manager

            refresh = None
            if row.get("refresh_token_encrypted"):
                try:
                    refresh = get_token_manager().decrypt(row["refresh_token_encrypted"])
                except Exception:  # noqa: BLE001
                    refresh = None
            if not refresh or not envelope.get("token_endpoint"):
                logger.warning("[ATTACH] %s token expired and cannot refresh", slug)
                return None
            try:
                token = await _exchange(envelope, {
                    "grant_type": "refresh_token", "refresh_token": refresh,
                })
            except Exception as exc:  # noqa: BLE001
                logger.warning("[ATTACH] %s refresh failed: %s", slug, exc)
                return None
            envelope = _envelope_from_token(envelope, token)
            new_refresh = token.get("refresh_token") or refresh
            _upsert_row(auth.client, auth.user_id, slug, {
                "credentials_encrypted": _encrypt(envelope),
                "refresh_token_encrypted": get_token_manager().encrypt(new_refresh),
            })
    return envelope


async def envelope_for(auth: Any, slug: str) -> Optional[tuple[dict, dict]]:
    """(row, envelope) for a call, through the ONE credential path — so an
    agent caller is refused here exactly as it is refused Slack (ADR-577)."""
    from services.platform_credentials import resolve_platform_credential

    cred = resolve_platform_credential(auth, platform_key(slug))
    if not cred:
        return None
    row = load_row(auth.client, auth.user_id, slug)
    if not row or row.get("status") != "active":
        return None
    envelope = await _fresh_envelope(auth, slug, row)
    if envelope is None:
        return None
    return row, envelope


async def refresh_tools(auth: Any, slug: str) -> list[dict]:
    """Re-list the server's tools onto the row. The aperture keeps only the
    tools that still exist, so a renamed tool cannot stay silently exposed."""
    got = await envelope_for(auth, slug)
    if not got:
        raise ValueError("not connected")
    row, envelope = got
    md = dict(row.get("metadata") or {})
    tools = await _list_server_tools(md.get("server_url") or "", envelope)
    names = {t["name"] for t in tools}
    aperture = {k: v for k, v in (md.get("aperture") or {}).items() if k in names}
    md["tools"] = tools
    md["aperture"] = aperture
    _upsert_row(auth.client, auth.user_id, slug, {"metadata": md})
    return tools


def set_aperture(auth: Any, slug: str, aperture: dict) -> dict:
    """The member's consent, tool by tool. Only tools the server advertises,
    only the two modes; anything else is refused rather than stored."""
    from services.platform_credentials import is_agent_caller

    if is_agent_caller(auth):
        raise PermissionError("an agent cannot set an aperture (ADR-577)")
    row = load_row(auth.client, auth.user_id, slug)
    if not row:
        raise ValueError("not connected")
    md = dict(row.get("metadata") or {})
    known = {t.get("name") for t in (md.get("tools") or [])}
    cleaned: dict[str, str] = {}
    for tool, mode in (aperture or {}).items():
        if tool not in known:
            raise ValueError(f"unknown tool: {tool}")
        if mode not in APERTURE_MODES:
            raise ValueError(f"unknown mode for {tool}: {mode}")
        cleaned[tool] = mode
    md["aperture"] = cleaned
    _upsert_row(auth.client, auth.user_id, slug, {"metadata": md})
    return cleaned


# ---------------------------------------------------------------------------
# The surface a turn holds
# ---------------------------------------------------------------------------


def attached_surface(client: Any, user_id: str) -> list[dict]:
    """Every active attached connector with a non-empty aperture, with the
    lane-facing names derived. What the lane runner composes from."""
    out = []
    for row in list_rows(client, user_id):
        md = row.get("metadata") or {}
        aperture = md.get("aperture") or {}
        if not any(m in APERTURE_MODES for m in aperture.values()):
            continue
        slug = slug_from_platform(row["platform"])
        tools = []
        for t in md.get("tools") or []:
            mode = aperture.get(t.get("name"))
            if mode not in APERTURE_MODES:
                continue
            tools.append({
                "name": t.get("name"),
                "lane_name": lane_tool_name(slug, t.get("name") or ""),
                "mode": mode,
                "description": t.get("description") or "",
                "input_schema": t.get("input_schema") or {"type": "object"},
                "read_only_hint": bool((t.get("annotations") or {}).get("readOnlyHint")),
            })
        if tools:
            out.append({
                "slug": slug,
                "title": md.get("title") or slug,
                "category": md.get("category"),
                "server_url": md.get("server_url"),
                "tools": tools,
            })
    return out


def attached_tool_defs(surface: list[dict]) -> list[dict]:
    """Anthropic-format definitions, the server's own schema, the title on
    the description so the model knows which server it is reaching."""
    defs = []
    for server in surface:
        for t in server["tools"]:
            mode_note = (
                " Runs directly in this turn."
                if t["mode"] == "direct"
                else " Each call is queued as a proposal the member executes."
            )
            defs.append({
                "name": t["lane_name"],
                "description": f"[{server['title']}] {t['description']}".strip() + mode_note,
                "input_schema": t["input_schema"],
            })
    return defs


def attached_tool_names(surface: list[dict]) -> tuple:
    return tuple(t["lane_name"] for s in surface for t in s["tools"])


def reach_categories(surface: list[dict]) -> set:
    return {s["category"] for s in surface if s.get("category")}


def resolve_lane_tool(client: Any, user_id: str, name: str) -> Optional[dict]:
    """{slug, tool, mode, row} for a lane tool name — by LOOKUP against the
    row's tool list, never by string surgery. None when unknown."""
    slug = slug_of_tool_name(name)
    if not slug:
        return None
    row = load_row(client, user_id, slug)
    if not row or row.get("status") != "active":
        return None
    md = row.get("metadata") or {}
    aperture = md.get("aperture") or {}
    for t in md.get("tools") or []:
        tool = t.get("name")
        if tool and lane_tool_name(slug, tool) == name:
            return {"slug": slug, "tool": tool, "mode": aperture.get(tool), "row": row}
    return None


def aperture_mode(client: Any, user_id: str, name: str) -> Optional[str]:
    """The gate's question. None = not in the aperture = DENY (fail closed)."""
    hit = resolve_lane_tool(client, user_id, name)
    if not hit:
        return None
    return hit["mode"] if hit["mode"] in APERTURE_MODES else None


async def run_attached_tool(auth: Any, name: str, input: dict) -> dict:
    """Dispatch one call. The gate has already ruled APPLY; this only reaches
    the server under the member's own token and returns the raw result."""
    hit = resolve_lane_tool(auth.client, auth.user_id, name)
    if not hit:
        return {"success": False, "error": "attached_tool_unknown",
                "message": f"{name} is not an attached tool this member holds"}
    got = await envelope_for(auth, hit["slug"])
    if not got:
        return {"success": False, "error": "attached_not_connected",
                "message": f"{hit['slug']} is not connected — reconnect it in Settings → Connectors"}
    row, envelope = got
    server_url = (row.get("metadata") or {}).get("server_url") or ""
    args = {k: v for k, v in (input or {}).items() if not str(k).startswith("_")}
    from integrations.core.mcp_client import get_mcp_client

    try:
        result = await get_mcp_client().call_tool(
            server_url, headers=_auth_headers_from(envelope),
            tool_name=hit["tool"], arguments=args,
        )
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": "attached_call_failed",
                "message": f"{hit['slug']}/{hit['tool']}: {exc}"}
    return {
        "success": not result.is_error,
        "server": hit["slug"],
        "tool": hit["tool"],
        "text": result.text,
        "structured": result.structured,
        "source_ref": result.source_ref(),
        **({"error": "server_reported_error"} if result.is_error else {}),
    }


def write_preview(name: str, input: dict, *, client: Any = None, user_id: Optional[str] = None) -> dict:
    """The external-write proposal's effect preview for an attached call:
    the server, the tool, and the arguments the member is approving."""
    visible = {k: v for k, v in (input or {}).items() if not str(k).startswith("_")}
    slug = slug_of_tool_name(name) or ""
    tool = name
    if client is not None and user_id:
        hit = resolve_lane_tool(client, user_id, name)
        if hit:
            tool = hit["tool"]
    preview = json.dumps(visible, ensure_ascii=False, default=str)
    return {"server": slug, "tool": tool, "title": f"{slug}: {tool}",
            "preview": preview[:280], "arguments": visible}


def frame_section(surface: list[dict], member: str) -> str:
    """The frame's paragraph for attached servers — affirmative either way,
    in the register the trio's reach section already uses."""
    if not surface:
        return ""
    lines = [
        f"ATTACHED SERVERS — {member} attached these MCP servers in Settings → "
        "Connectors and chose, tool by tool, what you may call. The names are "
        "mcp__{server}__{tool}. A tool marked PROPOSE does not run when you call "
        "it: the call is queued as a proposal they execute from their queue — "
        "say so, and do not call it twice. A tool marked DIRECT runs now, under "
        "their own credential. Anything not listed here you cannot reach; say "
        "so plainly rather than inventing a result."
    ]
    for s in surface:
        direct = [t["lane_name"] for t in s["tools"] if t["mode"] == "direct"]
        propose = [t["lane_name"] for t in s["tools"] if t["mode"] == "propose"]
        cat = f" ({s['category']})" if s.get("category") else ""
        parts = []
        if direct:
            parts.append("DIRECT: " + ", ".join(direct))
        if propose:
            parts.append("PROPOSE: " + ", ".join(propose))
        lines.append(f"- {s['title']}{cat} — " + " · ".join(parts))
    return "\n".join(lines)


__all__ = [
    "ATTACHED_PREFIX", "TOOL_PREFIX", "APERTURE_MODES",
    "slug_for", "platform_key", "is_attached_platform", "slug_from_platform",
    "is_attached_tool", "lane_tool_name", "slug_of_tool_name",
    "discover", "register_client", "callback_url",
    "load_row", "list_rows", "public_view",
    "begin_attach", "complete_attach", "refresh_tools", "set_aperture",
    "envelope_for", "attached_surface", "attached_tool_defs",
    "attached_tool_names", "reach_categories", "resolve_lane_tool",
    "aperture_mode", "run_attached_tool", "write_preview", "frame_section",
]
