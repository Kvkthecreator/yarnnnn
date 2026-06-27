"""Host Profiles — the interop-reach registry (ADR-379; absorbs the ADR-372 gate).

A host (the LLM connecting over MCP: ChatGPT, claude.ai, Gemini, Cursor, …) is a
**driver, not a code branch.** The core serves one canonical response; a thin
per-host profile — declared here as data — adapts only the edges that genuinely
differ. The Nth host is a registry entry, not a code change.

A host varies from the core on exactly FOUR dimensions, and only four:

  1. Identity  — how its OAuth client_id / User-Agent / registered name resolves
                 to a canonical short id. → HostProfile.match (this file is the
                 single resolver; mcp_composition._normalize_client_id delegates).
  2. Auth      — OAuth 2.1 dynamic-registration vs static bearer. ALREADY
                 host-agnostic (oauth_provider.py); NOT modeled here — a
                 spec-compliant client logs in with zero new code.
  3. Render    — (a) does it render MCP-Apps widgets? → renders_widgets;
                 (b) in which dialect (resource shape)? → widget_dialect.
  4. Quirks    — per-host workarounds. Added as a field ONLY when a real quirk is
                 found — never speculative.

Everything else — the three verbs, the substrate, the user_id (resolved from the
OAuth token, ADR-310 D4), the provenance mechanism, the ADR-307 gate — is
identical across hosts. Dimensions 2 and the TEXT path of 3 are already
host-agnostic, so a spec-compliant client gets clean text responses with zero new
code (proven live 2026-06-27). This registry makes reach ATTRIBUTED and SAFE
rather than accidental-and-"unknown"; it does not unlock reach (reach is already
there) — it makes it legible and correct.

Design rules that keep it future-proof:
  * Allow-list, text-safe default. renders_widgets is opt-in: an unknown /
    unidentified host gets the text path (which every host renders). The failure
    mode is "no widget" (always safe), never "broken render" — the inverse of a
    deny-list. This is the ADR-372 D4 gate, preserved exactly.
  * One place per host name. A host id appears in code here (the registry) or in
    its dialect adapter (the vendor `_meta` shape, ADR-372 D5). The CI gate
    (test_adr379_host_profiles.py) fails the build if a host name leaks elsewhere.
  * First-wins by registry order (§3.1). Substring match is ordered: the specific
    Claude variants (claude_desktop / claude_code) must be listed so they win over
    the bare anthropic / claude.ai match. The gate freezes the disambiguations.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class HostProfile:
    """A connecting LLM host, declared as data (ADR-379).

    Attributes:
        id:              canonical short id ("chatgpt" | "gemini" | "claude.ai" …).
                         Used for provenance (yarnnn:mcp:<id>) and the render gate.
        match:           substrings tested (case-insensitive) against the host's
                         OAuth client_id / User-Agent / registered client_name.
                         FIRST-WINS by registry order — order matters (§3.1).
        renders_widgets: D3a — True if the host renders MCP-Apps widgets. Default
                         False (the text-safe default; ADR-372 D4 allow-list).
        widget_dialect:  D3b — "openai" | "mcp-apps" | None. Which resource dialect
                         to serve. MUST be set when renders_widgets is True. Selects
                         the adapter + (when §4 lands) the dialect-specific resource
                         URI. Today only "openai" is wired (chatgpt).
        match_excludes:  D1 disambiguation — substrings that DISQUALIFY a match even
                         if `match` hit (e.g. the bare claude.ai profile excludes
                         "desktop"/"code" so the specific variants win). Usually
                         empty; order in HOSTS handles most cases.
    """

    id: str
    match: tuple[str, ...]
    renders_widgets: bool = False
    widget_dialect: str | None = None
    match_excludes: tuple[str, ...] = field(default_factory=tuple)


#: The host registry. ORDER MATTERS — first match wins (§3.1). List the most
#: specific variants before the broad ones. A new host is one entry here.
#:
#: Render state today: ONLY chatgpt renders widgets (validated live; OpenAI Apps
#: SDK dialect — skybridge MIME + openai/* keys). Every other host is text — the
#: text-safe default. Flip renders_widgets + set widget_dialect when a host's
#: widget render is verified end-to-end on that host (and §4 multi-dialect serving
#: exists for any dialect other than "openai").
HOSTS: tuple[HostProfile, ...] = (
    # ChatGPT — the one rendering host today (ADR-372).
    HostProfile("chatgpt", ("chatgpt", "openai"), renders_widgets=True, widget_dialect="openai"),
    # Claude family — specific variants first so they win over the bare claude.ai.
    HostProfile("claude_desktop", ("claude desktop", "claude-desktop")),
    HostProfile("claude_code", ("claude code", "claude-code")),
    # claude.ai connector — opaque OAuth client_id (UUID) + UA without "claude";
    # the DB-backed client_name lookup (mcp_composition) feeds this match on the
    # registered name. Excludes the specific-variant tokens defensively.
    HostProfile(
        "claude.ai",
        ("claude.ai", "claude-ai", "anthropic"),
        match_excludes=("desktop", "code"),
    ),
    # Reach hosts — text today (auth + text path are free); attribution is what the
    # entry adds. Flip render flags when each ships a verified widget spec.
    HostProfile("gemini", ("gemini", "google")),
    HostProfile("cursor", ("cursor",)),
    HostProfile("copilot", ("copilot", "github-copilot", "github copilot")),
    HostProfile("perplexity", ("perplexity",)),
)

#: id → profile (for the gate / dialect resolvers).
_BY_ID: dict[str, HostProfile] = {h.id: h for h in HOSTS}


def resolve_host_id(raw: str | None) -> str | None:
    """Resolve a raw identity string (client_id / UA / registered name) to a host id.

    The SINGLE identity resolver (ADR-379 D1) — replaces the old substring chain.
    First-wins by registry order; a profile matches when any of its `match`
    substrings is present AND none of its `match_excludes` is. Returns None when
    nothing matches (the caller treats None as "unknown").
    """
    if not raw:
        return None
    low = raw.lower()
    for h in HOSTS:
        if any(tok in low for tok in h.match) and not any(x in low for x in h.match_excludes):
            return h.id
    return None


def renders_widgets(host_id: str | None) -> bool:
    """True if this host should receive widget `_meta` (else: text-only path).

    The ADR-372 D4 gate, preserved exactly: allow-list with a text-safe default.
    An unknown / unidentified host (None, "", or an id not in the registry, or a
    registered host with renders_widgets=False) returns False and gets the text
    path, which every host renders.
    """
    if not host_id:
        return False
    h = _BY_ID.get(host_id)
    return bool(h and h.renders_widgets)


def widget_dialect(host_id: str | None) -> str | None:
    """The widget resource dialect for a rendering host (ADR-379 D3b).

    Returns "openai" | "mcp-apps" | None. None for a non-rendering or unknown
    host. Today only "openai" is ever returned (chatgpt); §4 (multi-dialect
    serving) lights up the others when a second rendering host exists.
    """
    if not host_id:
        return None
    h = _BY_ID.get(host_id)
    return h.widget_dialect if (h and h.renders_widgets) else None


#: Backwards-compat shim for the ADR-372 name (the gate set). Derived from the
#: registry so it can never diverge. Prefer `renders_widgets()` in new code.
WIDGET_RENDERING_HOSTS: frozenset[str] = frozenset(
    h.id for h in HOSTS if h.renders_widgets
)
