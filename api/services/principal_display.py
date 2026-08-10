"""Principal display — the ONE server-side resolution of a stored principal
into a display form (2026-08-10, the identity-rendering pass).

The ledger stores identity canonically (ADR-209/410/411): `authored_by` carries
the species taxonomy (`VALID_AUTHOR_PREFIXES` in authored_substrate.py) and
`author_identity_uuid` carries WHICH human, as a separate column. What was
missing is a server-side display layer: the desk resolved through
`web/lib/workspace/attribution.ts` while the MCP surface emitted stored strings
verbatim — raw member UUIDs and legacy `<email> via <model>` rows crossed the
boundary, and the same revision rendered differently per surface.

This module is the single resolution point. Both the MCP compositions
(`list` / `open` / `history` / `save` conflicts) and the desk's revision
endpoints attach display through it, so the same revision never renders two
ways. It REUSES the two existing label tables rather than minting new ones:
`principal_grants._PROVIDER_LABELS` (host-id → name) and
`lane_runner.LANE_MODELS` (model slug → label).

Display rules (operator-specified):
  human direct            → "Kevin"                      (species: member)
  human via their agent   → "Kevin via Claude Sonnet"    (hands; still the member)
  external LLM principal  → "Claude (via MCP)"           (a separate principal)
  steward                 → "Freddie"
  system lanes            → as-is ("system:radar", "operator-proxy:…")
  unresolvable human      → "a workspace member"         (NEVER a UUID or email)

The species distinction (ADR-460: the member's hands vs an external principal)
must survive display — `classify_author` returns it alongside, and the display
strings themselves keep the three species distinguishable at a glance.

This is presentation only. The stored `authored_by` / `author_identity_uuid`
are never rewritten.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Iterable, Mapping, Optional

logger = logging.getLogger(__name__)

_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
)
_EMAIL_RE = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")

#: The honest degrade for an unresolvable human. Never a UUID, never an email.
UNRESOLVED_MEMBER = "a workspace member"


# ---------------------------------------------------------------------------
# Species classification (the ADR-460 distinction, machine-legible)
# ---------------------------------------------------------------------------

def classify_author(authored_by: Optional[str]) -> str:
    """The species of a stored principal string.

    'member'           — a human acting directly (operator / bare member / uuid)
    'member-via-agent' — a human's agent hands (member:{id} via {model}, ADR-411)
    'external-llm'     — a foreign LLM principal (yarnnn:mcp:{host})
    'steward'          — the system agent (freddie:/reviewer:)
    'agent'            — a persona agent / specialist
    'system'           — system lanes, dispatcher, operator-proxy, yarnnn:{model}
    'unknown'          — outside the taxonomy (legacy rows)
    """
    a = (authored_by or "").strip()
    if not a:
        return "system"
    if a == "operator" or _UUID_RE.fullmatch(a):
        return "member"
    if a.startswith("member:"):
        return "member-via-agent" if " via " in a else "member"
    if a.startswith("yarnnn:mcp:"):
        return "external-llm"
    if a.startswith(("freddie:", "reviewer:")):
        return "steward"
    if a.startswith(("agent:", "specialist:", "a2a:")):
        return "agent"
    if a.startswith(("system:", "dispatcher:", "operator-proxy:", "yarnnn:", "platform:")):
        return "system"
    # Legacy free-text (e.g. "<email> via <model>", pre-ADR-411): a human's
    # lane write from the era before the taxonomy closed.
    if " via " in a:
        return "member-via-agent"
    return "unknown"


# ---------------------------------------------------------------------------
# The two label tables (reused, not duplicated)
# ---------------------------------------------------------------------------

def model_display(model_slug: Optional[str]) -> str:
    """provider/model slug → display label. One table: lane_runner.LANE_MODELS.

    Unknown slugs strip the provider prefix (mirrors the FE fallback) so a new
    model degrades readably ("anthropic/x-9" → "x-9"), never to a raw slug with
    provider noise.
    """
    slug = (model_slug or "").strip()
    if not slug:
        return ""
    from services.lane_runner import LANE_MODELS
    label = LANE_MODELS.get(slug, {}).get("label")
    if label:
        return label
    return slug.split("/", 1)[1] if "/" in slug else slug


def host_display(raw_host: Optional[str]) -> str:
    """MCP host tail → display name, normalized through the ADR-379 registry.

    Handles both the well-formed tails ("chatgpt", "claude.ai") and the legacy
    unmapped registered-name rows ("Claude" — stored capitalized before the
    claude alias fix): lowercase → resolve_host_id → provider label; a host the
    registry doesn't know is title-cased, never emitted raw-cased.
    """
    raw = (raw_host or "").strip()
    if not raw:
        return "Unknown"
    from mcp_server.presentation.hosts import resolve_host_id
    from services.principal_grants import provider_label
    host_id = resolve_host_id(raw)
    if host_id:
        label = provider_label(host_id)
        if label:
            return label
    return raw.replace("-", " ").replace("_", " ").title()


# ---------------------------------------------------------------------------
# Member name resolution (uuid → display name; cached)
# ---------------------------------------------------------------------------

#: uuid → (name-or-None, resolved-at). Names change rarely; 5-minute TTL keeps
#: a burst of compositions from hammering the auth admin API.
_NAME_CACHE: dict[str, tuple[Optional[str], float]] = {}
_NAME_TTL_S = 300.0


def _name_from_admin_user(u: Any) -> Optional[str]:
    """Display name from an auth admin user record: metadata name first, then
    the email local-part (a handle, not an address), else None."""
    user = getattr(u, "user", None) or u
    meta = getattr(user, "user_metadata", None) or {}
    for key in ("full_name", "name", "preferred_username", "user_name"):
        val = meta.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    email = getattr(user, "email", None)
    if isinstance(email, str) and "@" in email:
        local = email.split("@", 1)[0].strip()
        if local:
            return local
    return None


def resolve_member_names(client: Any, member_ids: Iterable[str]) -> dict[str, str]:
    """uuid → display name for every id that resolves. Missing ids are simply
    absent (callers degrade to UNRESOLVED_MEMBER). Best-effort: an admin-API
    failure never breaks the read that asked. Requires a service-key client
    (both the MCP auth client and the routes' service client are)."""
    out: dict[str, str] = {}
    now = time.monotonic()
    for mid in {m for m in member_ids if m}:
        cached = _NAME_CACHE.get(mid)
        if cached and (now - cached[1]) < _NAME_TTL_S:
            if cached[0]:
                out[mid] = cached[0]
            continue
        name: Optional[str] = None
        try:
            u = client.auth.admin.get_user_by_id(mid)
            name = _name_from_admin_user(u)
        except Exception as exc:  # noqa: BLE001 — humanization is best-effort
            logger.debug("[PRINCIPAL_DISPLAY] name lookup failed for %s: %s", mid[:8], exc)
        _NAME_CACHE[mid] = (name, now)
        if name:
            out[mid] = name
    return out


def member_ids_of(
    authored_by: Optional[str], author_identity_uuid: Optional[str] = None
) -> list[str]:
    """The member uuids a row's display needs — for batching resolve calls."""
    ids: list[str] = []
    if author_identity_uuid:
        ids.append(str(author_identity_uuid))
    a = (authored_by or "").strip()
    if a.startswith("member:"):
        tail = a[len("member:"):]
        head = tail.split(" via ", 1)[0].strip()
        if head:
            ids.append(head)
    elif _UUID_RE.fullmatch(a):
        ids.append(a)
    return ids


# ---------------------------------------------------------------------------
# The resolver
# ---------------------------------------------------------------------------

def _scrub(text: str) -> str:
    """Last-resort hygiene for out-of-taxonomy strings: if the string carries a
    UUID or an email, it does not cross a boundary — degrade whole."""
    if _UUID_RE.search(text) or _EMAIL_RE.search(text):
        return UNRESOLVED_MEMBER
    return text


def display_author(
    authored_by: Optional[str],
    *,
    author_identity_uuid: Optional[str] = None,
    member_names: Optional[Mapping[str, str]] = None,
) -> str:
    """The display form of a stored principal. Never emits a UUID or an email.

    `member_names` is the batched uuid→name map (resolve_member_names); pass it
    when rendering many rows so resolution happens once per read, not per row.
    """
    names = member_names or {}
    a = (authored_by or "").strip()
    species = classify_author(a)

    if species == "member":
        # Direct human act. Identity rides author_identity_uuid (ADR-410) for
        # `operator` rows, or the string itself for member:/bare-uuid forms.
        mid = None
        if a.startswith("member:"):
            mid = a[len("member:"):].split(" via ", 1)[0].strip()
        elif _UUID_RE.fullmatch(a):
            mid = a
        elif author_identity_uuid:
            mid = str(author_identity_uuid)
        return names.get(mid or "", UNRESOLVED_MEMBER) if (mid or a == "operator") else UNRESOLVED_MEMBER

    if species == "member-via-agent":
        # The member's hands (ADR-411/460): still the member, transport named.
        if a.startswith("member:"):
            tail = a[len("member:"):]
            mid, model = (tail.split(" via ", 1) + [""])[:2]
            who = names.get(mid.strip()) or (
                names.get(str(author_identity_uuid)) if author_identity_uuid else None
            ) or UNRESOLVED_MEMBER
        else:
            # Legacy free-text "<email> via <model>" (pre-ADR-411, write door
            # now rejects it). The email never crosses; the era's rows had no
            # identity uuid, so degrade the who and keep the transport.
            model = a.split(" via ", 1)[1]
            who = (
                names.get(str(author_identity_uuid), UNRESOLVED_MEMBER)
                if author_identity_uuid else UNRESOLVED_MEMBER
            )
        label = model_display(model.strip())
        return f"{who} via {label}" if label else who

    if species == "external-llm":
        return f"{host_display(a[len('yarnnn:mcp:'):])} (via MCP)"

    if species == "steward":
        return "Freddie"

    if species == "agent":
        if a.startswith("agent:"):
            return f"Agent ({a[len('agent:'):]})"
        if a.startswith("specialist:"):
            return f"Specialist ({a[len('specialist:'):]})"
        return "Agent (A2A)"

    if species == "system":
        if a.startswith("yarnnn:") and not a.startswith("yarnnn:mcp:"):
            return "YARNNN"
        return a or "system"

    return _scrub(a)


def display_for_rows(
    client: Any,
    rows: Iterable[Mapping[str, Any]],
    *,
    authored_by_key: str = "authored_by",
    identity_key: str = "author_identity_uuid",
) -> dict[int, str]:
    """Batched display for revision-shaped rows: one name-resolution pass, then
    per-row display. Returns {index: display} in input order."""
    rows = list(rows)
    ids: list[str] = []
    for r in rows:
        ids.extend(member_ids_of(r.get(authored_by_key), r.get(identity_key)))
    names = resolve_member_names(client, ids) if ids else {}
    return {
        i: display_author(
            r.get(authored_by_key),
            author_identity_uuid=r.get(identity_key),
            member_names=names,
        )
        for i, r in enumerate(rows)
    }
