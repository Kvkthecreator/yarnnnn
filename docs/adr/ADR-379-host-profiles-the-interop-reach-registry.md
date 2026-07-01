# ADR-379 — Host Profiles: the Interop-Reach Registry

> **Status**: **Accepted / Implemented** (doc-first 2026-06-27; code landed same arc — `api/mcp_server/presentation/hosts.py` carries the `HostProfile` data-registry + `renders_widgets`/`widget_dialect` gates, guarding both the MCP response and discovery surfaces; test gate `test_adr379_host_profiles.py`. Status synced 2026-07-01 after the ADR-395 stability audit confirmed the implementation is complete and coherent.)
> **Authors**: KVK, Claude
> **Supersedes / amends**: amends **ADR-372** (the per-host widget gate `WIDGET_RENDERING_HOSTS` is absorbed into a fuller Host-Profile registry; `presentation/hosts.py` grows from a flag into the registry). Preserves ADR-368 (the three verbs + the recall bright-line), ADR-310/311 (one moat, two faces), ADR-075/371 (OAuth/transport + self-contained auth boundary), ADR-222 (kernel boundary — the registry lives entirely in the interop face).
> **Related**: ADR-335 (Perception Field — "transports are peripherals, driver-class, transport-blind judgment"; this ADR applies the same driver-class shape to the *outbound* host surface), ADR-162 (provenance stamping — the registry feeds `yarnnn:mcp:<host>` attribution), ADR-373 (multi-principal — a host is a principal class; this ADR is how the substrate learns *which* host is calling).
> **Canonical feature doc**: [`docs/features/mcp/presentation.md`](../features/mcp/presentation.md) §6 (Host Profiles).

---

## 1. The decision this ADR ratifies

The interop face must scale to **N LLM hosts** (Gemini, Cursor, Copilot, Perplexity, Claude Desktop, any spec-compliant MCP client) connecting to the **same three verbs** (`remember`/`recall`/`trace`) over the **same judged substrate**. The thesis is "one memory for every AI you use" (ADR-310) — reach is the product, not a feature.

The blocker is not capability — it is **shape**. Today a host's identity is scattered across the MCP layer: a substring chain in `_normalize_client_id` (identity), a flag set `WIDGET_RENDERING_HOSTS` (render gate), a single global `RESOURCE_MIME` + an always-on OpenAI overlay (render dialect). Supporting host #3 means hunting those sites down. That is the deny-list mentality in disguise: it held for two hosts (one mind held both), and it breaks at five.

**This ADR ratifies: a host is a *driver*, not a code branch.** The core serves one canonical response; a thin per-host **Host Profile** — declared as data in one registry — adapts only the edges that genuinely differ. The Nth host is a registry entry, not a code change. When a host needs behavior the registry cannot express as data, that is a signal the *canonical response* is wrong, not that the host needs a special case (the lesson the 2026-06-27 outputSchema bug taught: push the fix into the canonical shape, never branch the host).

## 2. The model — a host varies on exactly four dimensions, and only four

Every other thing a host touches is identical: same verbs, same substrate, same `user_id` (resolved from the OAuth token, ADR-310 D4), same provenance *mechanism*, same gate (ADR-307). A host differs on:

| # | Dimension | What varies | Where it lives today | Registry resolution |
|---|-----------|-------------|---------------------|---------------------|
| **1** | **Identity** (who is calling) | how the OAuth `client_id` / UA / registered name resolves to a short id | `_normalize_client_id` substring chain (`mcp_composition.py`) | `HostProfile.match` tuples — the registry is the single resolver |
| **2** | **Auth** (how it logs in) | OAuth 2.1 dynamic-registration vs static bearer | `oauth_provider.py` — **already host-agnostic** | **nothing to add** — a spec-compliant client registers + logs in with zero new code |
| **3** | **Render** (text vs widget, and which dialect) | (a) does it render MCP-Apps widgets? (b) in what resource dialect? | (a) `WIDGET_RENDERING_HOSTS`; (b) global `RESOURCE_MIME="text/html+skybridge"` + always-on `openai` overlay | (a) `HostProfile.renders_widgets`; (b) `HostProfile.widget_dialect` → selects an adapter + a dialect-specific resource URI |
| **4** | **Quirks** (per-host workarounds) | e.g. Claude Desktop's JSON-string coercion; future surprises | scattered / SDK-internal | a profile field *only when a quirk is discovered* — never speculative |

**The de-risking fact:** dimensions 2 (auth) and the *text path* of 3 are **already host-agnostic**. A spec-compliant MCP client gets clean text responses today with zero code — the text path was proven live 2026-06-27. The only thing missing for reach is dimension 1 (an unrecognized host attributes as `"unknown"`) and dimension 3b (a second rendering host with a non-OpenAI dialect cannot be served from the one hardwired resource). So this ADR makes reach **attributed and safe** rather than **accidental and anonymous** — it does not unlock reach (reach is already there); it makes reach *legible and correct*.

## 3. The Host Profile registry

`presentation/hosts.py` grows from a flag into the registry — one declared table, one resolver:

```python
@dataclass(frozen=True)
class HostProfile:
    id: str                          # canonical short id: "chatgpt" | "gemini" | "claude.ai" | ...
    match: tuple[str, ...]           # substrings tested against client_id / UA / registered name (D1)
    renders_widgets: bool = False    # D3a — the gate (ADR-372, text-safe default = False)
    widget_dialect: str | None = None  # D3b — "openai" | "mcp-apps" | None; selects adapter + resource URI
    # D2 (auth) is NOT here — host-agnostic in oauth_provider.
    # D4 (quirks) added as fields ONLY when a real quirk is found.

HOSTS: tuple[HostProfile, ...] = (
    HostProfile("chatgpt",        ("chatgpt", "openai"),        renders_widgets=True,  widget_dialect="openai"),
    HostProfile("claude.ai",      ("claude.ai", "claude-ai", "anthropic"), renders_widgets=False),
    HostProfile("claude_desktop", ("claude desktop", "claude-desktop")),
    HostProfile("claude_code",    ("claude code", "claude-code")),
    HostProfile("gemini",         ("gemini", "google")),
    HostProfile("cursor",         ("cursor",)),
    HostProfile("copilot",        ("copilot", "github-copilot")),
    HostProfile("perplexity",     ("perplexity",)),
)
```

The registry exposes:
- `resolve_host_id(raw: str) -> str | None` — the **single** identity resolver (replaces `_normalize_client_id`'s chain; both `derive_client_name` and `derive_client_name_from_token` route through it).
- `renders_widgets(host_id: str | None) -> bool` — the gate (ADR-372 contract preserved exactly: allow-list, text-safe default).
- `widget_dialect(host_id: str | None) -> str | None` — selects the adapter + resource URI for a rendering host.

**Adding Gemini is one line** (already in the table above). It connects (auth — free), gets text (render text path — free), and now attributes as `yarnnn:mcp:gemini` in `trace` (identity — what the entry adds). When Gemini ships a widget spec, flip `renders_widgets=True`, set `widget_dialect="mcp-apps"`, and §4 serves it.

### 3.1 The `anthropic`-substring ordering caveat (preserved from the live finding)

`_normalize_client_id` had a deliberate ordering: `claude.ai`/`anthropic` (but not "desktop") → `claude.ai`; `claude`+`desktop` → `claude_desktop`; `claude`+`code` → `claude_code`. The registry MUST preserve this: a substring match is **first-wins by registry order**, and the more specific Claude variants must be tested such that `claude_desktop`/`claude_code` win over the bare `anthropic`/`claude.ai` match. The CI gate (§5) asserts the known disambiguations resolve correctly so this ordering can never silently regress.

### 3.2 The widget gate spans THREE surfaces, not one (live finding 2026-06-27)

ADR-372's gate withheld the widget pointer from the tool **response** (`_present`). That is necessary but **not sufficient** — a host discovers widgets on two surfaces *before* any response runs, and claude.ai followed those to a render failure ("Unsupported UI resource content format" on `remember-receipt.html`, live):

| Surface | When | What leaked | Gate |
|---------|------|-------------|------|
| **Response** | `tools/call` | the `_meta.ui.resourceUri` pointer on the result | `_present()` (ADR-372) — already gated |
| **Discovery** | `tools/list` | the tool def's `openai/outputTemplate` → the host resolves it to the `ui://` resource and fetches it | `HostGatedFastMCP.list_tools` — **new** |
| **Read** | `resources/read` | the served widget resource itself (skybridge MIME + `openai/*` `_meta`) | `HostGatedFastMCP.read_resource` — **new** |

So the original "the tool-DEFINITION `_meta` is harmless namespaced metadata a non-OpenAI host ignores" reasoning (ADR-372 D4 follow-on) was **falsified for claude.ai**: the connector reads `openai/outputTemplate`, fetches the resource, and renders it. The fix gates all three surfaces on the **same** `hosts.renders_widgets(host)` decision:

- **`HostGatedFastMCP`** (a `FastMCP` subclass — `list_tools`/`read_resource` overrides) resolves the request host (`auth.resolve_request_host_id`, best-effort, fail-closed to text) and, for a non-widget host, **strips** `openai/*` + `ui.resourceUri` from tool-def `_meta` and serves the widget resource as **plain `text/html` with no `openai/*`** — so the host receives a non-renderable resource and shows nothing instead of erroring.
- The stripping primitive (`registry.strip_widget_meta`) + the URI set (`WIDGET_URIS`) + the downgraded MIME (`TEXT_RESOURCE_MIME`) live in the presentation layer (D5). A host name appears nowhere in the gate — only `renders_widgets`.
- A **widget host (chatgpt)** is untouched on all three surfaces: full `openai/*` binding + skybridge MIME flow through.

**Why a subclass and not the decorators:** FastMCP bakes `_meta` at registration (`@mcp.tool`/`@mcp.resource`), and `tools/list`/`resources/read` have no per-tool hook for per-host `_meta`. Overriding the two `FastMCP` methods is the one contained seam that sees the request context. The host resolver on the discovery path is cheap-first (substring on the token `client_id`, catching ChatGPT with zero DB) and falls back to the DB-backed registered-name lookup only when needed (claude.ai's opaque UUID).

## 4. Multi-dialect resource serving (the one piece of new engineering — DEFERRED)

This is the only dimension that is not "move existing logic into the registry." Today the widget resource is served at one URI with one MIME (`text/html+skybridge`, OpenAI-specific). A second rendering host with a different dialect (e.g. open MCP-Apps `text/html;profile=mcp-app`) cannot be served from that one resource. The fix is the one the registry's own comment already names: **serve each widget at N URIs, one per dialect** —

```
ui://yarnnn/trace-timeline.openai.html      (mimeType text/html+skybridge)
ui://yarnnn/trace-timeline.mcp-apps.html    (mimeType text/html;profile=mcp-app)
```

— and `_present()` selects the URI matching the calling host's `widget_dialect`. The widget *bundle* is the same React build; only the served `_meta` envelope + MIME differ per dialect.

**Deferred until a second rendering host actually exists** (YAGNI — building two dialects with only one consumer is speculative). But the registry shape **anticipates** it now (`widget_dialect` is a field from day one, the gate already keys on the profile) so the seam is pre-cut and we never re-architect under pressure. Until then: only `chatgpt` has `renders_widgets=True`, so only the `openai` dialect is ever served — identical to today.

## 5. The structural guarantee — a CI gate so scattering can't creep back

Per the OS discipline (host names live in exactly one place — ADR-372 D5), a regression gate asserts:

1. **No host-name string literal appears outside the registry** in the MCP layer (the identity chain, the gate set, the dialect global — all gone; `openai` survives only inside its adapter file, per ADR-372 D5).
2. **Every `renders_widgets=True` profile declares a `widget_dialect`** (a rendering host with no dialect is a serve-time failure).
3. **The known disambiguations resolve** (`claude.ai`→`claude.ai`, `claude desktop`→`claude_desktop`, `chatgpt`→`chatgpt`, `gemini`→`gemini`, an unknown UA→`None`) — §3.1's ordering, frozen.
4. **The ADR-372 gate contract holds** (allow-list, text-safe default: `chatgpt` renders, everyone else does not until they declare it).

This is what keeps the Nth host a data entry: the gate fails the build if a host name leaks into code, forcing it back into the registry.

## 6. What this ADR explicitly does NOT do (scope discipline)

- **It does not change the auth FLOW.** Dimension 2 is already host-agnostic; no `oauth_provider.py` / OAuth change. (It *does* add one read-only helper, `auth.resolve_request_host_id`, that reads the existing token to identify the host for the §3.2 gate — identity resolution, not an auth-flow change.) The static-bearer single-user pin — `MCP_USER_ID` — is noted as the one non-multi-user auth case, relevant when reach includes team/shared use, but that is ADR-373's territory, not this one.
- **It does not build multi-dialect serving** (§4 deferred).
- **It does not add a non-MCP route** (REST/SDK/Action — a different protocol face; out of scope, the "Surface" axis we set aside).
- **It does not touch the kernel or `api/services/*` core.** The registry lives entirely in `api/mcp_server/presentation/` (ADR-222 boundary; ADR-372 D5).
- **It does not change the three verbs or the recall bright-line** (ADR-368 preserved).

## 7. Implementation surface

| Concern | File | Change |
|---------|------|--------|
| The registry | `api/mcp_server/presentation/hosts.py` | `HostProfile` + `HOSTS` table + `resolve_host_id` / `renders_widgets` / `widget_dialect` |
| Identity resolution | `api/services/mcp_composition.py` | `_normalize_client_id` delegates to `resolve_host_id` (single resolver; both `derive_*` callers unchanged in signature) |
| Response gate (existing) | `api/mcp_server/server.py` | `_present()` already calls `renders_widgets`; passes the host's `widget_dialect` |
| **Discovery + read gate (§3.2)** | `api/mcp_server/server.py` | `HostGatedFastMCP(FastMCP)` — `list_tools` / `read_resource` overrides strip widget `_meta` + downgrade the resource MIME for a non-widget host |
| Host resolver for the gate | `api/mcp_server/auth.py` | `resolve_request_host_id()` — best-effort, cheap-first, fail-closed-to-text |
| Strip primitive + URI set | `api/mcp_server/presentation/registry.py` | `strip_widget_meta` + `WIDGET_URIS` + `TEXT_RESOURCE_MIME`; `tool_response_meta` gains a `dialect` param (only `openai` wired until §4) |
| CI gate | `api/test_adr379_host_profiles.py` | §5 assertions + the §3.2 three-surface gate (assertions 6, 7) |
| Canon | `docs/features/mcp/presentation.md` §5.1 | the Host-Profile model |

Doc-first per CLAUDE.md: this ADR, then `presentation.md` §6, then code, then the gate.
