# ADR-385 — Channels: the perception surface renamed, and external agents made legible as a channel

> **Status**: **Accepted + Implemented** (2026-06-29). FE + one backend file (`api/services/kernel_surfaces.py` — the surface registry that flows to the compositor; the API Render service is touched; no schema, no primitive, no scheduler/MCP/render-gateway change). External Agents re-mounts the existing `WorkspaceMembersCard` over `GET /api/workspace/members` (one body, two views per DP29); no new substrate, no new data path. Gate `api/test_adr385_channels_surface.py`; supersedes + deletes `test_adr370_context_surface.py` + `test_adr377_context_perception_home.py`; legacy gates (338/340_p2/341/347) updated to the new pane homes. `tsc --noEmit` clean. Renames the `context` surface → **`channels`** (the name "Context" is ambiguous — the filesystem, the substrate, and perception are all "context"); refactors its split-nav into two groups, **CHANNELS** (was PERCEPTION) and **ACTIVITY** (was FEED); adds an **External Agents** pane to CHANNELS as a *filtered mount of the already-built Workspace Members card* (`role ∈ {foreign-llm, a2a, platform}`, reading `principal_grants` — NOT a new data source); lands the feed on **Flow** by default; and deletes the now-redundant Workspace-Settings → Perception group. No new substrate, no new endpoint, one new component prop (`roleFilter`).
> **Date**: 2026-06-29
> **Authors**: KVK (operator) + Claude (collaborator)
> **Discourse base**: live screenshot-walk of `/context` (2026-06-29). Operator read: (1) "Feed and Context seem redundant — over-built or legacy?" — finding: *not redundant*, ADR-370 already folded Feed into Context; `/feed` is a redirect stub, `FeedSurface` is one component reused. (2) "the word *context* for a surface is ambiguous — in concept context also includes the file system, which is the Files surface's job." (3) "PERCEPTION should be renamed CHANNELS, and needs a panel for MCP / external LLMs like ChatGPT, Claude." (4) "the in/out arrows icon is good — keep it." (5) "Workspace Settings may not need the Perception group — remove the redundant Connectors and Sources there."
> **Amends**: [ADR-377](ADR-377-context-as-the-perception-home.md) — renames the surface it shaped (`context`→`channels`) and renames its two pane-groups (Perception→**Channels**, Feed/Boundary→**Activity**); preserves ADR-377's core decision (Context/Channels is the canonical perception home that *owns* the connection-read). Adds the External Agents pane ADR-377 did not have. Also reverses ADR-377's RATIFIED Option-A four-pane `connections|sources|emissions|flow` (which dropped "In") — In/Out/Flow are restored as distinct nav items.
> **Amends**: [ADR-370](ADR-370-context-surface-the-operations-boundary.md) — the surface slug it minted (`context`) is renamed; the In/Out/Flow lens model is **preserved as nav items** (operator decision — In/Out/Flow stay distinct because **Out is a different data source**, the emissions ledger, not a filter of the narrative).
> **Builds on**: [ADR-373](ADR-373-multi-principal-workspace-and-the-re-key.md) (grant-consult **now Implemented** — `principal_grants` + `GET /api/workspace/members` + the read-only `WorkspaceMembersCard` that *already renders* `foreign-llm` rows) + [ADR-386](ADR-386-workspace-members-grant-lifecycle.md) (the Workspace Members grant lifecycle / foreign-LLM auto-provision the External Agents view surfaces). This ADR surfaces that existing capability as a perception channel; it does not build new authorization machinery.
> **Preserves**: [ADR-335](ADR-335-perception-field.md) (the Perception field model — this renames the *surface*, not the model), [ADR-299](ADR-299-operator-addressing-writes.md)/[ADR-304] (sends stay system infra; the emissions/Out pane is read-only legibility), [ADR-289](ADR-289-feed-and-conversation-surfaces.md) (Flow row grammar), [ADR-308](ADR-308-redirect-stubs-as-pure-transport.md) (the `/context` + `/feed` legacy routes become pure server redirects), [ADR-297](ADR-297-surfaces-as-substrate-mirror.md) (compositor owns the surface registry; this changes a slug + a body, not the registry contract), [ADR-340](ADR-340-operator-experience-model.md) DP29 ("mirror once, compose few" — the External Agents pane is a *second view* of the one Members substrate, not a parallel mirror).
> **Dimensional classification** (Axiom 0): **Channel** (Axiom 6 — the perception surface's name + structure) — pure presentation/IA; no Substrate, Identity, Trigger, Mechanism, or Purpose change.

---

## 1. The problem (grounded in the walk)

Three distinct issues, only one of which is "redundancy":

1. **"Context" is an ambiguous surface name.** In YARNNN's own vocabulary, *context* is everywhere: the filesystem is context, the substrate is context (`operation/context/`), perception is context. Naming a single surface "Context" collides with the Files surface (the filesystem home) and with the substrate's own `context/` namespace. The name fights the rest of the OS.

2. **Feed vs. Context is NOT redundant — it only looks that way.** ADR-370 already dissolved the Feed *into* this surface. `/feed` is a redirect stub (ADR-308); `FeedSurface` is **one component** mounted in three places (In filtered, Flow unfiltered, Notifications→Activity). There is no second feed to delete. The apparent redundancy is the legacy `FEED` group label sitting inside a surface that is conceptually the boundary. The fix is a *rename*, not a *deletion*.

3. **The perception surface has no home for the interop face.** YARNNN's launch thesis is "one moat, two faces" — the same substrate served in-app (cockpit) and to any external LLM (interop, via MCP). The external LLMs that connect — ChatGPT, Claude, etc. — are *principals of the workspace* (ADR-373 `foreign-llm` grants). They are a perception/channel concern. Today they appear only on Workspace-Settings → Access (the Members roster); they have no presence on the surface that is supposed to be the operation's edge with the outside world.

4. **Workspace-Settings → Perception is now genuine cruft.** ADR-377 D2 already made the Settings Connectors entry a thin *pointer* ("manage connections in Context →") and left Sources as a full duplicate mount. Once the perception home is renamed and owns everything, the whole Settings Perception group is redundant: the Connectors pointer is pure nav-cruft, the Sources card is a literal duplicate.

## 2. The honest finding that makes the design future-proof (External Agents)

The naive build for "an MCP / external-LLM panel" is a new component reading a new data source (e.g. a "distinct MCP authors" query over `workspace_file_versions`). **That would be duplication** — a parallel data source for something the workspace already has a canonical home for.

The audit found the canonical home already exists and is already correct:

- ADR-373 grant-consult is **Implemented**. `principal_grants(principal_id, workspace_id, role, scopes, status, …)` models *every* writer of the commons, where `role ∈ {owner, member, own-agent, foreign-llm, platform, a2a}`. An external LLM connecting via MCP **is a `foreign-llm` principal** — a workspace member, not a separate entity class.
- [`WorkspaceMembersCard.tsx`](../../web/components/workspace-concepts/WorkspaceMembersCard.tsx) **already renders `foreign-llm` rows** — the role enum, the "External LLM" label, the CPU icon, the write-region scope badges, and the humanized-name lookup (from `mcp_oauth_clients`) are all wired. [`GET /api/workspace/members`](../../api/routes/workspace.py) returns all active grants including `foreign-llm`/`platform`/`a2a` with no role filter.
- The card renders for those roles the moment a `foreign-llm` grant is written (ADR-386 grant lifecycle / auto-provision). **The pane appears with no further code change.**

So the External Agents pane is **a filtered view of the one Members substrate**, not a new panel. This is the Singular-Implementation / "mirror once, compose few" (DP29) answer:

> **One substrate (`principal_grants`) → one component (`WorkspaceMembersCard`) → two views**: the full roster on Workspace-Settings → Access, and a `role ∈ {foreign-llm, a2a, platform}` filtered view on Channels.

This also keeps two orthogonal planes from colliding:

| Plane | Question | Substrate | Channels pane |
|---|---|---|---|
| **Connections** | *What feeds the operation?* (data-in transports) | `platform_connections` | Connections, Sources |
| **Members / External Agents** | *Who can write the commons?* (authorship principals) | `principal_grants` | External Agents |

Slack-the-data-feed (Connections) and Claude-the-writing-principal (External Agents) are different facts about different objects. They co-exist in the CHANNELS group without overlap.

## 3. Decisions

### D1 — Rename the surface `context` → `channels`

- Slug `context` → `channels`; route `/context` → `/channels`. Icon **unchanged**: `arrow-left-right` (the in↔out boundary arrows the operator likes). `launcher_tier: primary`, `default_pinned: true` — unchanged.
- `/context` and `/feed` become **pure redirect stubs** (ADR-308): `/context` → `/channels`, `/feed` → `/channels?channels.pane=flow` (param-merge preserved for `?prompt=` deep-links).
- The frontend `SurfaceRegistry` maps `channels` + the legacy `context` + `feed` slugs to the one page component (legacy deck/window state that foregrounds `context`/`feed` mounts the live Channels surface, never an orphaned stub). The backend keeps `feed` + `context` as **search-only legacy alias** surface entries (FE-allowlist↔backend parity).
- `context.pane` query-param namespace → `channels.pane`.

### D2 — Refactor the split-nav into CHANNELS + ACTIVITY

```
⇄ Channels   (/channels, arrow-left-right, primary, pinned)
  CHANNELS                      ← was PERCEPTION
    Connections    — platform data-feeds (ConnectedIntegrationsSection + freshness)
    Sources        — standing web/RSS watches (SourcesCard, ADR-335/336)
    External Agents — MCP / external-LLM principals (WorkspaceMembersCard, roleFilter=[foreign-llm,a2a,platform])
  ACTIVITY                      ← was FEED
    Flow   — the complete narrative (FeedSurface, unfiltered)   ← DEFAULT LANDING PANE
    In     — inbound crossings (FeedSurface, isInbound filter)
    Out    — the emissions / dispatch ledger (EmissionsView)
```

- **Default landing pane → Flow** (the operator wanted the feed on entry, not the connections list).
- **In / Out / Flow kept as distinct nav items** — operator decision. They are *not* collapsed into filter chips because **Out is a genuinely different data source** (`EmissionsView` / `GET /api/emissions`), not a filtered view of the narrative.
- **Drop the "Context" prefix** on labels: "Context In/Out" → "In"/"Out".
- The surface is **Channels**, so the top group is the **CHANNELS** group (was PERCEPTION) and the feed group is **ACTIVITY** (was FEED).

### D3 — External Agents pane = filtered mount of WorkspaceMembersCard

- `WorkspaceMembersCard` gains an optional `roleFilter?: string[]` prop — default (omitted) = all roles (the existing full-roster behavior on Workspace-Settings → Access is unchanged).
- Mounted on Channels with `roleFilter={['foreign-llm', 'a2a', 'platform']}` (external-principal classes — the interop/automation writers, excluding the human `owner`/`member` and the internal `own-agent`).
- Reuses `GET /api/workspace/members` verbatim. **No new endpoint, no new substrate, no new attribution path.**
- The pane states honestly when no external principals are granted ("no external agents have been granted write access yet") — the truth, not a brochure of "known hosts."

### D4 — Delete the Workspace-Settings → Perception group

- Remove the **Connectors** pointer card (pure nav-cruft) and the **duplicate Sources** mount. Both concerns live solely on Channels.
- Workspace Settings is thereby tightened to: **Constitution** (Mandate · Identity · Principles), **Contract** (Budget · Autonomy · Expected Output), **Operation** (Program), and **Access** (Workspace Members). Perception leaves Settings entirely.
- The `connectors`/`sources` pane-grade kernel slugs re-home `pane_of: channels`; their route stubs (`/connectors`, `/sources`) redirect to Channels.

## 4. What this does NOT do

- **Does not build new authorization or provisioning UX.** External Agents is *read-only legibility*; granting/scoping is the ADR-386 lifecycle, unchanged by this ADR.
- **Does not touch the gate, the write path, or attribution.** Pure presentation + IA + one component prop.
- **Does not change `platform_connections`, `principal_grants`, `emissions`, or the narrative envelope.** No schema, no new endpoint.
- **Does not rebuild any inbound store** (ADR-153 / ADR-377 §2 ceiling holds).
- **Does not merge Members and Connections into one model.** They stay orthogonal (§2).

## 5. Rejected / deferred

- **A separate "MCP hosts" panel reading a parallel data source** (distinct `authored_by` over `workspace_file_versions`, or the static ADR-379 host registry as a brochure). **Rejected** — duplicates what `principal_grants` + `WorkspaceMembersCard` already own; fragments the multi-principal roster + violates DP29.
- **Collapsing In/Out/Flow into one feed with filter chips.** Rejected (D2) — Out is a distinct data source.
- **Keeping the name "Context."** Rejected (D1) — the ambiguity with the filesystem + the `context/` substrate namespace is the operator's primary complaint.
- **Host-profile icon/label enrichment of Members rows (ADR-379).** Deferred (additive) — the pane works without it.

## 6. Cascade / blast radius

- **Backend**: `api/services/kernel_surfaces.py` — the `context` entry renamed to `channels`; `feed` + `context` kept as search-only legacy aliases; `connectors`/`sources` re-homed `pane_of: channels`.
- **Frontend surface registry**: `web/components/shell/SurfaceRegistry.tsx` (channels + feed + context → ChannelsPage); `web/types/desk.ts` (slug union + KERNEL_SURFACE_SLUGS); `web/lib/shell/surface-preferences.ts` (`DEFAULT_KEPT_SURFACES = ['channels']`); `web/lib/compositor/surfaceTitle.ts` (feed/context title-alias → channels); `web/components/shell/Desktop.tsx` (first-time check accepts legacy aliases); `web/components/shell/chrome/ChatDrawer.tsx` (supervise-surface set).
- **The surface page**: `web/app/(authenticated)/channels/page.tsx` (new); `context/page.tsx` + `feed/page.tsx` + `sources/page.tsx` + `connectors/page.tsx` redirect stubs → channels.
- **Members card**: `WorkspaceMembersCard.tsx` — `roleFilter?` prop + empty-state overrides (default = all; existing mount unaffected).
- **Settings**: `web/app/(authenticated)/workspace-settings/page.tsx` — Perception group deleted.
- **Canon**: CLAUDE.md surface-model addendum; GLOSSARY (the surface entry); amend-banners on ADR-370 + ADR-377.
- **Gate**: `api/test_adr385_channels_surface.py` (new); superseded `test_adr370` + `test_adr377` deleted; legacy gates (338/340_p2/341/347) updated to the new pane homes.

## 7. Sequencing (doc-first)

1. This ADR (sign-off).
2. The surface rename (D1) + nav refactor (D2) + default-Flow — mechanical, low-risk; redirect stubs preserve all legacy links.
3. The External Agents pane (D3) — the one new view (a prop + a mount).
4. Delete the Settings Perception group (D4).
5. Canon cascade + gate + `tsc --noEmit`.
