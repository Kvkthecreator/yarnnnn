# ADR-635 — The connector directory is consumed, not authored; reach attaches under the member's grant; a foreign write is the first proposal producer

> **Status**: **Accepted + Implemented** (2026-09-03) — gate-verified (`test_adr635_attached_connectors.py`, 78/78: the attach flow offline against the Notion shape, the three verdicts, the replay, the lane agreement, the seed's provenance, the strip, the deletion) and discovery driven LIVE against `mcp.notion.com`, `mcp.linear.app` (both: dynamic registration + S256) and `mcp.context7.com` (anonymous; its tools listed through the widened client). **Owed**: the browser click-pass of one full attach round-trip (search → connect → authorize → aperture → a lane calling a DIRECT tool → a PROPOSE call landing in the queue), the registry publish and the plugin-directory submission (operator acts). Operator ruling in the four-nouns discourse, aligned in full: *"we should seriously consider taking advantage of connectors handling in a more marketplace style approach… open up that marketplace-like search, select a connector and connect-like convention"* and *"the connector discovery related full scaffolding should ultimately reside in the user settings… discovery is the marketplace, and added connectors stack up as per existing approach."*
> **Disposition** (the intake-pipeline.md §5 rule, declared in the first paragraph): an attached connector is **TURN REACH** — the member's own credential, inside the member's own turn, transient. Its consequential tools are **OUTBOUND through a proposal** — queued, member-executed, receipted. It is **not intake**: nothing lands in the commons unless someone writes it, and an unattended run never holds the credential (ADR-577, unchanged).
> **Dimensional classification** (Axiom 0): **Channel** (Axiom 6 — where the ecosystem is met: the directory and the attach seam) + **Mechanism** (Axiom 5 — which tools a turn holds, and the gate that rules on them). **No Identity change**: an attached connector belongs to the human who attached it, never to an agent or an app. **No Purpose change**: the aperture is consent, never a mandate.
> **Amends**: ADR-420 §10 rule 2 (*"never a catalog"* → never an **authored** catalog; the demand gate lifts) · ADR-585 D2/D4 (the read-only bound holds for the hand-authored trio; an attached server's aperture is member-chosen, tool by tool) · ADR-293 D4 / ADR-307 (a `member:` caller's consequential attached tool engages the gate; the gate was Reviewer-scoped and the Reviewer is retired) · ADR-630 D3 (a skill may declare `metadata.needs`; the parser names what it strips) · ADR-335 D4/D5 (the foreign-watch binding is DELETED — the attached connector is the one MCP binding).
> **Preserves**: FOUNDATIONS DP27 (transport consumed from the ecosystem — this ADR is that sentence enacted for discovery) · ADR-577 (an agent never holds a credential) · ADR-582/594 (a connection is consent + credential + aperture; the aperture is the only per-connection setting) · ADR-615 (reach follows the principal) · ADR-596 D2 / ADR-460 D3.a (authority on grants, declarations and gates — the per-tool mode lives on the connection, never on an agent) · ADR-412 D3 (not a model marketplace — untouched; this is about connectors) · ADR-420 §10 amendment (the moat-leak test governs what yarnnn **seeds**; a member's own attach is uncurated by design).

---

## 1. Context — what changed since ADR-420 refused a catalog

ADR-420 §10 rule 2 (2026-07-08) ruled *"yarnnn ships the attach mechanism + 2–3 known-good starting points, never a catalog"* and paused the mechanism on demand. Two things were true then that are not true now.

**There was no upstream catalog to consume.** Today the MCP registry answers `GET /v0/servers?search=…&version=latest` with entries carrying `remotes[{type: "streamable-http", url}]`, and Anthropic publishes eleven knowledge-work plugins whose `.mcp.json` files name **62 distinct remote endpoints** (measured 2026-09-03 on `anthropics/knowledge-work-plugins@f30dc63`): 51 bare HTTPS URLs, 7 member-supplied, 3 API-key headers, 1 pre-registered client. Sixty of sixty-two are streamable HTTP. The directory exists, vendors maintain their entries, and DP27 already says transport is *"consumed from the ecosystem, never built as a catalog."* A directory **read** from upstream is that sentence; a directory **written** by yarnnn is what ADR-420 refused. The two were one word in July because the first did not exist.

**The auth layer converged on one generic flow.** Probed live 2026-09-03: `mcp.notion.com` and `mcp.linear.app` both answer an unauthenticated probe with `WWW-Authenticate: … resource_metadata=…` (RFC 9728), publish authorization-server metadata (RFC 8414) with a `registration_endpoint` (RFC 7591 dynamic client registration) and `S256` PKCE; `mcp.context7.com` answers anonymously. yarnnn already **implements** that flow as a server (`mcp_server/oauth_provider.py`). It has no client half. One client, keyed by server URL, covers 58 of the 62 endpoints; the remaining four are a header field or a URL the member types.

**The kernel already holds the transport.** `integrations/core/mcp_client.py` (ADR-335) is a streamable-HTTP client that resolved a real GitHub token in June 2026. It was confined to the steward's mechanical watches (`TrackForeign`), which are measured **dead**: the steward retired (ADR-632), the primitive is on no live surface, and production holds **zero** watch-bound rows (`platform_connections.watch_id IS NOT NULL` → 0, 2026-09-03).

**The write side has no answer today, and the code would do what Cowork does.** The permission gate (`resolve_permission`) engages consequential calls only for Reviewer-authored ones (ADR-293 D4); every other caller resolves APPLY. The Reviewer is retired. So a foreign write tool inside a member's turn would execute under their credential with no proposal and no receipt beyond the turn — the collapsed principal the four-nouns discourse named. The proposal queue exists, its FE surface is mounted, `ExecuteProposal` replays through the one gate, and the handoff lists *"no proposal producer exists today"* as owed under ADR-596 D3(d).

## 2. Decisions

### D1 — The connector directory is consumed from the ecosystem, never authored

`services/connector_directory.py::search(q)` merges two upstream sources and returns one normalized shape (`name · title · description · url · category · source`):

- **The MCP registry**, live: `https://registry.modelcontextprotocol.io/v0/servers?search=…&version=latest`, remote streamable-HTTP entries only, cached per process for an hour. A registry outage degrades to the seed, never to an error.
- **The official endpoints seed**: `services/connector_directory_seed.json`, **derived** from `anthropics/knowledge-work-plugins` by `scripts/refresh_connector_directory.py` (every `.mcp.json` server + the category each plugin's `CONNECTORS.md` assigns it), stamped with the upstream repository and commit. The seed is data with provenance in the ADR-376 sense — a raw observation of upstream, re-derivable — not a list yarnnn curates. The gate asserts the provenance stamp and refuses a seed entry with no upstream.

**A member may also paste any URL.** The directory is a discovery affordance in front of the attach seam (ADR-420 §10 rule 3's *"discovery affordances reading the catalog"*), not a precondition of it. If both upstreams vanished, attach still works.

**What the directory is not**: curation (no rankings, no "recommended" beyond the seed's own category), and not a store. ADR-412 D3 and ADR-420 §10 rules 1 and 3 stand. The moat-leak test (ADR-420 §10 amendment) governs what yarnnn would *seed as a starting point*; a member attaching a competing commons is their eyes-open choice, and what a lane makes from it still lands as an attributed revision in *this* commons (ADR-420 D2 step 4).

### D2 — An attached connector is a `platform_connections` row keyed `mcp:{slug}`

No migration. The human's account object (ADR-425), keyed `user_id`, `UNIQUE(user_id, platform)` satisfied by the prefixed key. `credentials_encrypted` holds one encrypted JSON envelope — access token, DCR client id and secret, token endpoint, expiry, resource — `refresh_token_encrypted` the refresh token, `metadata` the server URL, title, category, the server's advertised tool list, and the **aperture**. The row is read through the ONE credential path (`platform_credentials.resolve_platform_credential`, ADR-577), so an agent caller is refused at the same chokepoint that refuses it Slack.

The slug is the seed's short name when attached from the directory (`notion`, `linear`, `context7`) and the sanitized host otherwise. It is data-compat: a lane's tool names ride it.

### D3 — Attach is one generic OAuth 2.1 client, plus one field

`services/attached_connectors.py::begin_attach` discovers the server (RFC 9728 → RFC 8414), registers a client where the server offers it (RFC 7591), and builds a PKCE-S256 authorize URL under the same signed state the hand-authored connectors use (`generate_oauth_state`). The pending row is written first, `status='pending'`, so the callback has one place to complete. `complete_attach` exchanges the code, stores the envelope, lists the server's tools and lands the row `active` **with an empty aperture** (D4). A server that answers anonymously attaches without a redirect. A server that wants a header takes it as one encrypted field at attach. Refresh is transparent at read time (`access_token_for`): an expired token is refreshed through the stored endpoint, and a refresh failure reads as "not connected", never as a traceback in a member's turn.

There is **no per-server code**. Adding a connector is a directory hit or a pasted URL. The hand-authored trio (Slack, Notion, GitHub) and WordPress keep their bespoke clients because they carry things MCP does not: the landscape discovery that makes durable intake selectable, and the publish seam.

### D4 — The aperture is the member's tool allowlist, with a mode per tool; unlisted is denied

**Selection is consent, never a default** (ADR-582, 2026-08-19). An attached connector lands with **no tool exposed**. The member opens the connection and picks, tool by tool, one of three states:

| State | Meaning | Gate verdict |
|---|---|---|
| off (unlisted) | not offered to any turn | **DENY** `attached_tool_outside_aperture` |
| `propose` | offered; every call is queued as an `external-write` proposal the member executes | **QUEUE** `attached_propose` |
| `direct` | offered; runs in the member's turn | **APPLY** `attached_direct` |

The server's `annotations.readOnlyHint` is shown beside each tool as a **hint that informs the member's choice and never decides it** — the MCP SDK's own docstring says clients must never make tool-use decisions from a server's annotations, and yarnnn agrees. This is the ADR-582/594 aperture applied to tools instead of channels, and it is the only per-connection setting, which ADR-594 D1 already allows. The mode lives on the **connection** (the grant side), never on an agent or a skill (ADR-596 D2).

### D5 — The lane holds attached tools under the ecosystem's own name convention

A reach-bearing turn (ADR-585/615: the member present, `TURN_REACH_ENABLED` not darkened) composes the member's attached apertures into the one tool computation (`lane_tool_names` / `lane_tools_openai`, ADR-467 D4 — payload, allowlist and frame prose from one source). Names are `mcp__{slug}__{tool}`, the Claude Code convention, resolved not invented (the ADR-588 rule). Definitions are the server's own `inputSchema`, description prefixed with the server's title. The frame's connector-reach section names each attached server, its tools, and which run directly versus by proposal, in the same affirmative register the trio already has.

### D6 — A consequential attached tool is the first proposal producer

`resolve_permission` gains one branch for `mcp__` names, placed with the other caller-independent branches (before the non-Reviewer short-circuit): an approved replay (`_proposal_id`) applies; otherwise the aperture decides per D4. `execute_primitive` routes DENY to a refusal the model can read, QUEUE to the existing `external-write` enqueue (`effect = {server, tool, preview}`), and APPLY to `run_attached_tool`. `ExecuteProposal` replays the same primitive name through the same gate, so the member's click in the queue is the act, attributed and receipted. This discharges the ADR-596 D3(d) item the handoff owed — the queue's first producer since the steward retired — without a second gate or a second queue.

### D7 — A skill may declare what reach it needs; the parser names what it strips

`metadata.needs: [category, …]` on a `SKILL.md` scopes presentation exactly as `metadata.apps` does (ADR-630 D3 amendment): a skill naming needs is offered in a lane whose member holds an attached connector of one of those categories, withheld-and-counted otherwise. Silence means everywhere. This is the ecosystem's `~~category` placeholder convention (the knowledge-work plugins' `CONNECTORS.md`) as a declaration rather than prose — so a public skill written for "a project tracker" drops into `skills/` unchanged and lights up when one is attached.

`parse_skill` already dropped `allowed-tools`, `model`, `tools` and the other host-specific fields from an imported file, silently. It now returns them as `stripped` and logs them, so an import says what it lost. Prose was never permission (ADR-464 §3); now the strip is visible. This is the R2 seam the four-nouns doc named: an imported artifact's authority claims are discarded and named, never honored as written.

### D8 — The foreign-watch binding is deleted

`TrackForeign`, `services/foreign_read.py` and `_resolve_binding` (ADR-335 Crawl-B) are removed: no live surface offered the primitive after ADR-632, and production holds zero rows behind it. The attached connector is the ONE MCP binding, read through the ONE credential path. `MCPClient` stays, now with one caller class instead of a dead one.

### D9 — yarnnn is a connector in that same directory

The discovery card at `web/app/.well-known/mcp.json` advertised `remember`, `recall` and `trace` — retired without aliases by ADR-543. It no longer enumerates tools at all: the server's `tools/list` is the source of truth and a second copy drifted. A `server.json` (`docs/features/mcp/server.json`, the registry's `2025-12-11` schema) and a Claude Code / Cowork plugin (`plugin/yarnnn/` — a manifest plus an `.mcp.json` pointing at `https://mcp.yarnnn.com`, served by a root marketplace manifest) are committed. Publishing to the registry and submitting to the official plugin directory are operator acts with the operator's credentials; the files are ready and `CONNECTING.md` documents both.

## 3. What this deliberately does not do

- **No durable intake from attached servers.** A capture needs a selector, and MCP has no generic "list the selectable things". Strings keep reading landed captures from the trio. When a member wants a standing read through an attached server, the shape is a member-declared `{server, tool, args}` watch — named here, not built.
- **No agent-level opt-in for attached servers.** ADR-612's per-agent narrowing applies to the trio. An attached server's aperture is already the member's explicit per-tool consent; a second dial over it would be two sources for one fact.
- **No `needs` on apps.** A declaration nobody populates is a tautology (the ADR-592 lesson). Skills carry `needs`; apps do not, until one has a reason to.
- **No skills inside the yarnnn plugin.** The kernel skills speak the lane's verbs (`ReadFile`, `derived_from`); the MCP face speaks `open`/`save`. Shipping them to a host would be a second copy of each skill in a second vocabulary. Deferred until that question is settled.
- **No per-call approval modal.** A `propose` tool queues; the member executes from the queue they already have. Cowork's modal is a host affordance; yarnnn's queue is attributed and receipted.

## 4. What ships

`api/services/connector_directory.py` + `connector_directory_seed.json` + `api/scripts/refresh_connector_directory.py` · `api/services/attached_connectors.py` (discovery, DCR, PKCE, envelope, refresh, aperture, tool defs, dispatch) · `api/routes/attached_connectors.py` at `/api/connectors` (directory · attach · callback · detail · aperture) · the gate branch in `services/primitives/permission.py` + the dispatch branch in `services/primitives/registry.py` · `lane_runner` composes attached tools and the frame section · `services/turn_reach.py` derives them · `list_integrations` and the integrations summary emit `mcp:` rows · `services/skills` `needs` + `stripped` · the settings surface (`ConnectedIntegrationsSection` directory search + attached rows, `AttachedConnectorSubsurface` aperture picker) · the discovery card fix · `plugin/yarnnn/` + root `.claude-plugin/marketplace.json` + `docs/features/mcp/server.json` · `TrackForeign` / `foreign_read.py` DELETED.

**Gates**: `api/test_adr635_attached_connectors.py` (the aperture fails closed; three verdicts; the replay applies; the name convention round-trips; payload, allowlist and prose agree; the seed carries provenance; the parser names its strip; `needs` scopes presentation; the discovery card names no retired verb; the plugin's URL is the MCP URL; the dead binding is gone). Re-anchored: `test_adr585_turn_reach.py`, `test_adr630_skills.py`, `test_adr494_connector_registry.py`.
