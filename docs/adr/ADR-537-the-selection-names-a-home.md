# ADR-537 — The selection names a home: two topologies of arrival

**Status**: Draft (Proposed 2026-08-08 — NOT ratified; operator review required). Originates from an operator-requested first-principles audit of the platform-connection / intake machinery. §2 is the audit (receipts, no decisions); §5 is the proposal. Nothing here ships until ratified.

**Amends (proposed)**:
- [ADR-392](ADR-392-the-connector-lane.md) D3/D7 — the watch declaration gains a third coordinate (*where the derived understanding belongs*), and D7's "no platform-shaped trees in `operation/`" gets its enforcement device instead of only its prohibition.
- [ADR-394](ADR-394-connector-capture-the-reader.md) D3 — derive stays the seat's act, but gains a declared routing input and a wake source, closing the "structurally unowned" gap ADR-401 D5 named.
- [ADR-494](ADR-494-the-connector-registry-is-singular.md) D1 — the registry entry gains a `topology` field.

**Preserves (explicitly untouched)**:
- [ADR-404](ADR-404-the-commons-first-launch.md) D2 — the capture lane stays dormant behind `CONNECTOR_CAPTURE_ENABLED`; this ADR adds **no new flag** and does not flip the existing one.
- [ADR-420](ADR-420-engine-breadth-vs-connector-breadth.md) §10 — the connector-breadth demand-gate. §6 argues why it does not bind here (ADR-535 §2's ruling: a gate binds where its *reasoning* reaches — this ADR deepens the three live connectors' intake semantics and builds no new connector).
- [ADR-425](ADR-425-the-credential-is-an-account-object.md) — the credential stays an account object; the mapping proposed here is workspace substrate, exactly like the `_watch.yaml` it extends.
- [ADR-535](ADR-535-a-bound-connector-is-visible-to-the-members-lane.md) §7 — no lane gains connector *content* reach; the permission-rung blocker (D4) stands.
- [ADR-376](ADR-376-the-ledger-intake-axiom.md) / DP32 — retain + attribute + cite. Raw is never re-homed; the home names where the *derived, citing* object lands.
- `docs/design/connection-manager.md` — the connector is the health unit; **no per-selector status grain** is introduced.

---

## 1. The question

The operator asked, in substance:

> The filesystem- and attribution-native substrate exists. Platform connections exist. But there are **two modes** of external platform: a GitHub repository is *contained* — the external unit is itself one coherent context. Slack and Notion are *dispersed* — one connection spans many unrelated topics consolidated under one external workspace. Should the intake — the scoping of the outside platform's structure onto designated spots in the filesystem — be an explicitly managed, dedicated workflow, such that interactive updates can drive subsequent actions and recommendations? And which prior fragments of this idea are still in place, outdated, or sunset?

This ADR answers in three parts: the audit (§2), the first-principles derivation (§3–4), and the proposal (§5).

## 2. The audit — what is actually there

Three sweeps (live machinery, intake lanes, decision history) on 2026-08-08 @ `8a49ca8`. Receipts are `file:line` in the working tree.

### 2.1 The ratified lane vs the running system

[ADR-392](ADR-392-the-connector-lane.md) ratified a four-phase lane — **Connect · Select · Capture · Derive** — and it is canon, unrevoked. The running system implements it like this:

| Phase | Canon | Running state |
|---|---|---|
| 1 Connect | OAuth → `platform_connections` row (account object, ADR-425) | **Live.** `api/integrations/core/oauth.py:66-126` (4 configs: slack/notion/github + an orphaned `reddit`), signed self-carrying state per ADR-531. |
| 2 Select | Operator authors a watch declaration | **Live.** `PUT /api/integrations/{provider}/sources` → `operation/_connectors/{platform}/_watch.yaml` (`api/services/connector_watch.py:65-105`), `authored_by="operator"`, full discovered set with explicit `selected: true/false`. |
| 3 Capture | Raw into `inbound/{platform}/{selector}/{observed_at}` | **Built, dormant.** `CONNECTOR_CAPTURE_ENABLED` defaults off (`api/services/connector_capture_gating.py:49-58`); the select-time seed is skipped (`api/routes/integrations.py:2206-2213`); the scheduler drain never runs (`api/jobs/unified_scheduler.py:335-346`). Per ADR-494 §1c the capture signal froze 2026-07-03. |
| 4 Derive | The seat derives-and-cites raw into `operation/` | **Never implemented as a mechanism.** Ratified "by reference" as the seat's on-engagement act with zero new code (ADR-394 D3); ADR-401 D5 records *no derive has ever fired outside test fixtures*. The eager derive-wake was retired (`api/services/capture/lane.py:331-343`). |

Net: **a member can select channels/pages/repos today, save a real declaration, and nothing will ever read them** — and even with the flag on, raw would accumulate in quarantine with no owned path to meaning, until the retention GC (which prunes *uncited* raw past the window, `api/services/connector_retention.py:159-230`) deleted all of it, since nothing ever cites it. The lane's two halves cancel: capture without derive is a leak with a timer.

### 2.2 Three parallel scoping stores, one write, swallowed exceptions

`PUT .../sources` (`api/routes/integrations.py:2111-2226`) writes the same selection to three places in sequence:

1. `platform_connections.landscape.selected_sources` (JSONB) — the UI cache. ADR-392 D3 already called it "a dead annotation"; it is still what `GET .../sources` reads back (`:2256`).
2. `operation/_connectors/{platform}/_watch.yaml` — the authoritative declaration (versioned, attributed). Written best-effort in a `try/except` (`:2187`).
3. `/workspace/_captures.yaml` `capture-{platform}` entry — machine state. Best-effort *and* skipped while dormant (`:2206-2218`).

Both mirror steps swallow exceptions, so the three stores can silently diverge — and the read path for the UI is store #1 while the read path for capture is store #2 (`api/services/primitives/capture_connector.py:194`).

### 2.3 The connect flow's silent break

The ADR-113 auto-discovery block in the OAuth callback (`api/routes/integrations.py:1650-1697`) imports `get_limits_for_user, PROVIDER_LIMIT_MAP` from `services.platform_limits` (`:1664`) — **neither symbol exists**; `platform_limits.py` was long since repurposed into the billing/balance service (ADR-396/291). The import raises unconditionally, a bare `except` eats it, and every fresh connect leaves `landscape` NULL until the operator happens to open the Manage drill-in. The same dead import kills `landscape.refresh_landscape` (`api/services/landscape.py:472`), which additionally has zero callers. So the ADR-113 promise — connect auto-discovers and auto-selects — has been silently false for some time. (Adjacent, already-tracked: the 2026-08-08 handoff records an unexplained prod `Invalid or expired OAuth state` on a Notion connect — ADR-531 territory, listed here only for audit completeness.)

### 2.4 Four platform registries, one gated

1. `api/services/connector_registry.py::CONNECTOR_REGISTRY` — the ADR-494 offered set (slack/notion/github live; commerce/trading retired). **The only one CI-paired with the frontend.**
2. `api/integrations/core/oauth.py::OAUTH_CONFIGS` — slack/notion/github/**reddit**. `GET /integrations/reddit/authorize` works today (no `_reject_if_retired` on authorize/callback, only on the two API-key connect routes `:2601`, `:2907`) — a connectable provider that no surface will ever render.
3. `api/integrations/platform_registry.py::PLATFORM_REGISTRY` — slack/notion only; consumed by the health probe's quirks.
4. `api/services/platform_tools.py::PLATFORM_TOOLS_BY_PROVIDER` — eight families including sunset/retired ones.

### 2.5 The write-less table read by five surfaces

`sync_registry` is written by **nothing** (the capture lane deliberately doesn't touch it — `web/components/settings/ConnectedIntegrationsSection.tsx:40-47` says so in a comment) yet still read by `routes/integrations.py:325` (`last_used_at`), `:1851` (`coverage_state` — permanently `"uncovered"`), `:2419` (`/sync-status`), `primitives/system_state.py`, and `working_memory.py:1059`. Every consumer derives freshness from a table nothing populates.

### 2.6 The unmarked side doors

While the front door is dormant, three live/latent lanes move platform-shaped content **without** the lane's provenance discipline:

- **MCP `save`** (`api/services/mcp_composition.py:1224-1360`): a foreign LLM can land a pasted Slack thread or Notion page at any non-locked path as `revision_kind='authored'` — indistinguishable on the ledger from the member's own work. Only `remember` routes to the arrivals lane.
- **Harvest** (`api/services/harvest.py`, route live, FE removed): writes platform content to the pre-ADR-320 shape `operation/context/{domain}/…` (`:419`), attributed `agent:harvest`, no raw retained, no `derived_from`, default-`authored`.
- **`TrackForeign`** (`api/services/primitives/track_foreign.py:315-350`): distills GitHub content straight to `distills_to` with no `inbound/` raw, no `revision_kind`, no `derived_from` — the falsifiability property `TrackWebSources` has (`track_web_sources.py:51-66`) is absent here.

By contrast the **radar/web lane is the healthy reference implementation**: declared hub → raw retained (`inbound/web/…`, `observation`) → distilled signal → cited brief (`derivation`, `derived_from=[signal, *raws]`), running deliberately outside the connector flag (`api/services/radar.py:38-48`, ADR-486).

### 2.7 Vestigial inventory (condensed)

- Dead columns: `platform_connections.settings` (0 refs), `sync_in_progress`/`sync_started_at` (migration 109, 0 refs).
- Dead table: `integration_import_jobs` (exists, zero reads/writes).
- Deprecated endpoint stubs kept for 404-avoidance: `/integrations/import`, `/integrations/import/{id}`, `/integrations/notion/import`, `/integrations/{provider}/sync`, `/integrations/{provider}/destinations`.
- Zero-caller code: `landscape.refresh_landscape`, `platform_tools.get_platform_tools_for_user` (its chat surface is gone), the Notion designated-page routes (no FE caller), `platform_limits.SYNC_SCHEDULES`/`should_sync_now`.
- Orphaned FE: `PlatformCardGrid.tsx`, `agents/SourcePicker.tsx`, `DestinationSelector.tsx`; `web/app/(authenticated)/integrations/[provider]/page.tsx:8-12` still redirects to the ADR-207-dissolved `slack-bot` agent; eight orphaned `api.integrations.*` client methods.
- Scope-filter drift (ADR-425 violation): `freddie_envelope.py:927` and `working_memory.py:1053,1061` query the account-scoped `platform_connections`/`sync_registry` with `substrate_scope_filter` instead of `account_scope_filter`.
- Retention polarity: ADR-401 D4's "bug-grade Phase 0" fix (prune uncited, keep cited forever) has no ledger record of landing before the lane went dormant.
- `directory_registry.py` (v4.0) still declares platform-bot temporal domains (`operation/{slack,notion,github}/`) that ADR-392 D7 forbids; sole consumer is the harvest prompt.

### 2.8 Doc drift

- `docs/database/SCHEMA.md` documents dropped `platform_content` and dropped `last_synced_at` as live.
- `GLOSSARY.md:319,328,513` — dissolved Channels surface described as live; "five platform connections" contradicts ADR-494 D2; no entries for Connector / Connection / Peripheral / Downloads / Documents / Capture despite ADR-424 §95 and ADR-420 §9.4 owing them.
- `docs/design/WORKSPACE.md` (v3.0) lists a `/connectors` route and Lemon Squeezy / Alpaca — three contradictions with ADR-425 + ADR-494.
- ADR-415 is headed `Proposed` while implemented in code, and its D2 (connector placement) was reversed a day later by ADR-425 — a citation trap for future drafts.

**Audit verdict.** The operator's hypothesis is confirmed, but with a precise shape: the fragments are not competing implementations of intake — canon is remarkably singular (ADR-392/393/394/401 form one coherent contract). The fragmentation is (a) *residue* from the three dead eras (sync-pipeline, platform-content, platform-bots) that ADR-153 and successors sunset without full sweeps, and (b) one **structural hole in the living canon**: the declaration says *what* to read and *how often* — it has never said *where the understanding belongs*, and the phase that was supposed to answer that (Derive) is owned by no mechanism.

## 3. First principles

From the axioms the substrate already lives by:

1. **Reality enters only as attributed observation** (ADR-335 / DP27, Axiom 1 §8): watches are *declared, never crawled*. A declaration is substrate — authored, attributed, revisioned.
2. **Retain + attribute + cite** (ADR-376 / DP32): raw in as `observation`, understanding out as a *derived, citing* act; raw never rewritten.
3. **The filesystem is organized by meaning to the operator** (ADR-384, ADR-424): path *is* meaning; Documents holds authored work, Downloads holds what arrived; platform structure is quarantined to the raw lane and never becomes an `operation/` tree (ADR-392 D7).
4. **A citation binds to the world** (ADR-357 / DP31): the `source_ref` is the external address (channel id, page id, repo path), never the internal copy.
5. **The commons is multi-principal and every write is signed** (ADR-373/378, ADR-405): a mapping decision is an authored act with an author, not configuration in a JSONB blob.

Now derive the shape of an intake declaration from these. To move external content to *meaning*, the system must know three coordinates:

- **What** to read — the source selection. Declared today (`_watch.yaml`).
- **How often** — cadence. Declared today (`_captures.yaml`, operator-tunable).
- **Where it belongs** — the meaning-home of the *derived* understanding. **Declared nowhere.**

The third coordinate was deferred to Derive-as-judgment: the seat would read raw and decide placement on engagement. That is a defensible design for genuinely novel arrivals — but as the *only* mechanism it fails structurally, because for the overwhelmingly common case the operator already knows the answer at select-time (*#launch-planning is about the launch; that repo is the codebase*), and the system throws that knowledge away. The declaration captures intent about attention but not about meaning — so raw piles up meaning-less, derive has no routing input, and the GC's evidence rule eventually destroys what nothing cited. The hole is not a missing feature on top of the lane; it is a **missing coordinate in the lane's own declaration**.

## 4. The two topologies of arrival

The operator's observation, sharpened into an architectural property:

**Container-grain platforms.** A GitHub repository is externally *pre-scoped*: the platform's own unit of organization coincides with a workspace subject. One repo ≈ one meaning. The landscape discovery already returns containers (`full_name` repos — `api/services/landscape.py:121-162`), and the capture binding already reads at container grain (`platform_github_get_issues` keyed by `repo`, `connector_watch.py:191-195`). For these, the what→where mapping is nearly the identity function: it can be *defaulted* and merely confirmed.

**Commons-grain platforms.** A Slack workspace or a Notion workspace is externally the *same kind of thing yarnnn itself is* — a multi-topic commons. The connection is to the roof; the meaning lives in the sub-contexts (channels, page subtrees), and those map **many-to-many** onto the workspace's meaning folders: three channels may feed one project; one channel may feed none. For these, scoping *is* the mapping, and a flat checkbox list — today's SCOPE section (`ManageConnectionSubsurface.tsx:408-459`) — structurally cannot express it. It can only say "read this," never "this belongs to that."

The system already half-knows the distinction — selector grain differs per platform (`channel_id` / `page_id` / `repo`), Notion once had a `designated_page` concept, GitHub discovery returns containers while Slack discovery returns rooms — but nothing declares it, so every surface and every default treats the two topologies identically.

## 5. The proposal

Six decisions. D5 is bug-grade and unconditional; D1–D4 and D6 are the design and ship dormant behind the existing flag.

### D1 — The selection names a home

The watch declaration gains the third coordinate. Each selection may carry a `home`: the meaning-folder path where *derived* understanding from that source belongs.

```yaml
# operation/_connectors/slack/_watch.yaml
selections:
  - id: C0123ABC
    name: "#launch-planning"
    selected: true
    home: "operation/product-launch/"     # ← the new coordinate
  - id: C0456DEF
    name: "#random"
    selected: true                         # homeless selection stays legal:
                                           # raw lands in Downloads, nothing derives
```

Properties, each forced by §3:

- The mapping is **authored substrate** — written through the existing versioned path (`write_selection`, `authored_by` = the acting member), revisioned, walkable, correctable. Not a JSONB annotation.
- **Raw is never re-homed.** Capture still writes only to the quarantined raw lane with `revision_kind='observation'` (ADR-423). `home` routes the *derivation* — the new, citing object — which is exactly the DP32 split.
- A `home` must be a meaning folder (Documents subtree or peer meaning-folder), never a platform-shaped path. This turns ADR-392 D7 from a prohibition into a mechanism: platform trees can't leak into `operation/` because the only door from raw to `operation/` is a declared meaning target.
- Homeless selections are first-class, not errors: "watch this, I don't know where it belongs yet" is a legitimate declaration, and its raw is legible in Downloads (ADR-394 D3's "raw sitting un-derived *is* the legible state" survives for exactly this case).

### D2 — The registry declares topology

`CONNECTOR_REGISTRY` entries gain `topology: "container" | "commons"` (github → container; slack, notion → commons), CI-paired to the frontend like every other registry field (ADR-494 D1 discipline).

Topology drives defaults and surface shape, not capability:

- **container** — the select surface proposes `home` per container by default (repo → a meaning folder named for the subject the repo serves), one confirmation gesture. The mapping conversation is skippable because the external unit already carries its meaning.
- **commons** — the select surface becomes a *mapping* surface: sources grouped under the homes they feed (existing folders offered, new folder creatable in place), with "watch only" (homeless) as an explicit column rather than the silent default. This is the "dedicated workflow" the operator asked for — and it is a workflow over exactly one substrate file.

### D3 — Derive gets its owner

Two halves, matching the two knowledge states:

- **Routed derive (mechanical trigger, judgment act).** When a capture lands for a selection that has a `home`, the lane emits a substrate-event wake proposal (the existing `_hooks.yaml` / wake-funnel machinery — no new invocation path) naming the raw revision and its declared home. Freddie's engagement then does what ADR-394 D3 always said derive is: reads raw, writes the derived object **into the declared home** with `derived_from=[raw]` and the world `source_ref` (DP31), `revision_kind='derivation'`. The declaration supplies routing; the seat supplies judgment. Cited raw becomes evidence the GC protects (ADR-401 D4) — the leak-with-a-timer from §2.1 closes.
- **Recommended mapping (the interactive loop).** For homeless arrivals, Freddie's engagement may *propose* a mapping — "the last week of `#launch-planning` reads like `operation/product-launch/`; bind it?" — surfaced through the ordinary proposal/act machinery. Acceptance writes the `home` back into `_watch.yaml` as an attributed revision, and the next capture routes mechanically. This is the operator's "interactive updates dictate subsequent actions and recommendations," grounded: recommendations *compound into declarations*, and the ledger shows who bound what, when, and why.

The radar lane (ADR-486) is the proof this shape works end-to-end: declared hub → raw → cited, kernel-placed derivation. D3 is the connector lane catching up to its own sibling.

### D4 — One scoping store

`operation/_connectors/{platform}/_watch.yaml` becomes the *only* store of the selection. `GET /integrations/{provider}/sources` reads the declaration (falling back to the JSONB once, for migration); `landscape.selected_sources` is no longer written; the two best-effort `try/except`s around the mirror writes are removed so a failed declaration write fails the request instead of silently diverging the stores. `landscape` (the JSONB) remains what it actually is — a discovery cache — and nothing else.

### D5 — Phase 0 hygiene (unconditional, independent of D1–D4)

Bug-grade and residue items from §2, each safe regardless of whether this ADR ratifies:

1. Fix or honestly delete the ADR-113 auto-discovery block: the dead `platform_limits` import (`routes/integrations.py:1664`, `landscape.py:472`) makes it unreachable today. If auto-discovery stays, source the smart-defaults cap locally; if not, delete the block and the dead `refresh_landscape`.
2. Retire the `sync_registry` reads (five surfaces deriving freshness from a write-less table) or repoint them at the capture signal per ADR-401 D6; drop `/sync-status`.
3. Registry hygiene: guard `authorize`/`callback` with the ADR-494 offered set (closing the orphaned-`reddit` door), and fold `platform_registry.py`'s residual duties toward `CONNECTOR_REGISTRY`.
4. Fix the ADR-425 scope-filter drift (`freddie_envelope.py:927`, `working_memory.py:1053,1061` → `account_scope_filter`).
5. Confirm/land the ADR-401 D4 retention-polarity Phase 0.
6. Delete: deprecated endpoint stubs, `integration_import_jobs`, dead columns (`settings`, `sync_in_progress`, `sync_started_at`), orphaned FE components + the `slack-bot` redirect, orphaned client methods, `platform_limits`'s vestigial sync helpers.
7. Sweep the §2.6 side doors toward the intake discipline: harvest either retires or writes through retain+attribute+cite; `TrackForeign` retains raw + kinds like `TrackWebSources`; MCP `save` of external material remains out of scope here but is flagged for the interop canon.
8. Doc updates owed regardless: SCHEMA.md, GLOSSARY (add Connector/Connection/Peripheral/Downloads/Documents/Capture; fix :319/:328/:513), design/WORKSPACE.md connector rows, ADR-415 status banner.

### D6 — Staging

D1–D4 ship **behind the existing `CONNECTOR_CAPTURE_ENABLED`**, exactly where the lane already sleeps (ADR-404 D2 untouched, ADR-494 D6's honest-copy rule continues to apply to any surface change). The point is not to wake the lane now; it is that *when* the commons-first sequencing says wake it, it wakes into a lane whose declaration is complete — scoped, homed, derive-owned — instead of the current quarantine-and-forget. The mapping surface (D2) may ship visible-but-honest earlier (a declaration is real substrate even while capture sleeps — that is already true of `_watch.yaml` today), at operator discretion.

## 6. What this deliberately does not reopen

- **Connector breadth** (ADR-420 §10): no new connector, no member-attached MCP mechanism. The demand-gate's reasoning — don't build supply for unproven connector demand — does not reach a decision about the *declaration semantics* of the three connectors already offered (ADR-535 §2's reasoning-reach ruling).
- **Lane content reach** (ADR-535 §7): no lane gains `platform_*` tools; the permission-rung precondition stands.
- **Per-selector health** (`connection-manager.md`): the connector remains the health unit. A `home` is a routing declaration, not a status grain.
- **Workspace-shared / agent-owned credentials** (ADR-425 D3, ADR-496 §5): reserved, untouched.
- **Platform-as-principal** (ADR-401 D1): the connection stays a peripheral; captures stay `system:`-attributed; the *member* authors the mapping.
- **The `inbound/` → Downloads dissolution** (ADR-384 D3 / ADR-423): unimpeded — D1 routes derivations, never raw, so the raw lane's namespace can dissolve into `revision_kind` on its own schedule.

## 7. Open questions for the operator

1. **Home granularity for commons platforms**: is a Notion *page subtree* (a page id and its descendants) an acceptable selection unit, or do we stay at flat page grain as discovered today? (Capture binding reads per `page_id` either way.)
2. **Default homes for container platforms**: derive the proposed folder name from the repo name, or always ask? (D2 assumes propose-and-confirm.)
3. **Recommendation cadence**: should homeless-arrival mapping proposals ride ordinary Freddie engagement only (zero new wakes), or is a low-frequency standing nudge acceptable?
4. **Harvest**: retire outright, or rebuild on the lane (declare → capture → routed derive) as the interactive "bring in my reality" front-end?
5. **Sequencing**: Phase 0 (D5) is committable piecemeal now. Should D1+D4 (declaration shape + single store) land dormant ahead of any UX work, so the substrate contract settles first?
