# ADR-392 — The Connector Lane: connectors are the third context-in transport, made to conform

> **Status**: **Accepted** (2026-07-01) — **raw-lane mechanism ratified as Option A** (`inbound/` namespace, ship-now; §3). Doc-first; each implementation limb lands in its own sequenced commit (§5). **Substrate + Trigger + Mechanism dimensions** — it re-targets one primitive's write (Substrate/Trigger) and splits capture from derive (Mechanism); it changes **no** write gate, **no** schema, and adds **no** new primitive.
>
> **↳ The Phase-3 Capture lane is built by [ADR-393](ADR-393-the-perception-capture-pipeline.md) (Implemented 2026-07-01).** ADR-393 gives *all* deterministic intake — connector captures AND the trader/author state-mirrors + perception watches — a distinct pipeline (`services.capture`) outside the wake funnel, and narrows recurrences to judgment-only. It **confirms §4/§7 here**: the trader mirrors are NOT migrated to `inbound/` (their `write_to`-direct `operation/` target is permanent, ADR-376 §63); they only move their *dispatch home* (recurrence → capture lane), a Trigger-dimension re-home orthogonal to the Substrate path. The remaining connector-specific limbs (D3/D4 selection surface, D8 retention GC scheduler-wiring, D9 OAuth scopes, §5 step-8 derive) are unchanged by ADR-393 — it built the lane those run on.
> **Date**: 2026-07-01
> **Authors**: KVK (operator) + Claude (collaborator)
> **Discourse base**: the operator connected Slack, asked Freddie to read a channel, hit "Connected · never synced · 0 sources," and read the connector domain as half-wired — needing *"an axiomatic way of handling connectors … dedicated lane … singular, future-proof,"* with the intake-vs-understanding overlap flagged as *"vague and dangerous"* and the filesystem-bloat risk called out explicitly. The load-bearing question: *"how is a platform connection writing channel history fundamentally different from an MCP-AI writing documents into the substrate?"*
> **Scoping doc**: [connectors-at-large-first-principles-2026-07-01](../analysis/connectors-at-large-first-principles-2026-07-01.md) (the full derivation + receipts).
> **Amends**: [ADR-264](ADR-264-substrate-canonical-world-and-syncplatformstate.md) — `SyncPlatformState` re-targets the raw capture lane instead of writing `operation/` directly; its dual-surface + diff-awareness + per-item iteration are preserved. [ADR-113](ADR-113-auto-source-selection.md) — the OAuth-callback `selected_sources` annotation becomes a live *watch declaration* (Phase 2) with a consumer, not a dead landscape field.
> **Applies**: [ADR-376](ADR-376-ledger-intake-raw-observation-vs-derived-substrate.md)/DP32 (the ledger-intake axiom — `retain + attribute + cite`) to the one context-in transport that never conformed to it. [ADR-335](ADR-335-perception-field.md)/DP27 (watches are declared, never crawled — Phase 2 is a peripheral watch declaration). [ADR-389](ADR-389-principal-vs-peripheral-and-the-steward-shaped-envelope.md) (a connection is a peripheral, judged for health not honesty — unchanged; this ADR gives the peripheral its missing intake limb).
> **Preserves**: `platform_connections` as a credential DB row (Axiom 1 four-row-kinds); the LLM-callable `platform_*` tool surface (ADR-264 D4 ad-hoc-lookup dual); the single write path `write_revision()` (ADR-209 — capture and derive are both ordinary attributed revisions, no new write path); `CALLER_WRITE_POLICY` (no change — `inbound/` is already unlocked for `system:` callers).
> **Complements (does NOT re-open)**: [ADR-353](ADR-353-composio-as-driver-backend.md) — a connection is TWO flows of one thing (ADR-332): a peripheral-for-context-in (this ADR: capture→derive) AND a driver-for-work-out (ADR-353: mechanical execution). ADR-353 settled connection *creation* / discovery / kernel-vs-Composio / where-a-connection-maps; this ADR adds only the context-in half + the one OAuth-scope gap (D9). [ADR-332](ADR-332-four-flow-completeness-model.md)/DP26 (the four-flow model — connectors span context-in + work-out). [ADR-304](ADR-304-operator-addressing-writes.md) (`write_{platform}` kernel-universal, `feeds: action` — the outbound capability D9 pre-provisions).
> **Coordinates with (does not collide)**: [the re-founding keystone](../analysis/the-re-founding-meaning-folders-and-permission-as-metadata-2026-06-29.md) / FOUNDATIONS v9.13 — the raw-lane *mechanism* (namespace vs `revision_kind`) is the one open decision below; the *invariant* is identical across both, so the four-phase model is mechanism-agnostic. [ADR-391](ADR-391-budget-balance-and-the-three-layer-cost-model.md) — the retention-window dial (D8) is built here as a substrate-read policy and left pricing-ready; the tier→max-window *mapping* is deferred to the pricing session (no pricing code here).
> **Dimensional classification** (Axiom 0): **Substrate** (Axiom 1 §9 — where connector context lands) + **Trigger** (Axiom 4 — capture cadence) + **Mechanism** (Axiom 5 — the capture/derive split at the deterministic↔judgment seam).

---

## 1. Why this ADR

YARNNN has three context-in transports. Two of them — MCP (`remember`) and web/RSS (`TrackWebSources`) — were reconciled to the ledger-intake axiom (ADR-376, 2026-06-26): each **captures** a raw observation into a quarantined lane (`inbound/mcp/…`, `inbound/web/…`, immutable, attributed) and then, as a **separate** act, **derives** understanding into `operation/`, citing the raw (`derived_from`). Raw is never rewritten in place.

The third transport — **platform connections** (Slack/Notion/GitHub/broker, mediated by `SyncPlatformState`, ADR-264) — never conformed. `SyncPlatformState` predates the axiom by six weeks and writes **straight to `operation/`**, fusing capture and derive into one step with no raw lane and no `derived_from` (`api/services/primitives/sync_platform_state.py:307-314`). And it is invoked in exactly one place — the alpha-trader bundle, for `platform_trading_*` (`docs/programs/alpha-trader/reference-workspace/_recurrences.yaml:43-71`). So in a bare/steward workspace, connecting Slack does nothing but store a token and list channel *names*: no content ever reaches substrate, and the steward honestly reports it has nothing to read.

**This ADR makes the lone non-conformer conform.** The answer to the operator's load-bearing question — *is a connection writing channel history different from an MCP-AI writing a document?* — is **no, they are the same context-in contract at the ledger floor** (ADR-376/DP32); they diverge only in transport (API pull vs LLM push) and volume (a firehose vs an occasional dump). So connectors get the same four-phase lane, plus the one thing their volume raises that the other two never did: a retention/GC answer.

## 2. The decision

### D1 — Connectors are the third instance of one context-in contract, not a new class

The connector lane is **four phases**, each in one Axiom-0 dimension, each with exactly one writer. No new primitive, no new class — connectors inherit the contract MCP + web already honor:

| Phase | Dimension | Writer | Substrate effect |
|---|---|---|---|
| **1 Connect** | Identity / auth | OAuth callback (`system`) | `platform_connections` row (credential — a permitted DB kind, unchanged) |
| **2 Select** | Purpose (declaration) | operator (chat/UI) | a **watch declaration** — "these channels/pages are in my perception aperture" (DP27: declared, never crawled). Replaces the dead `landscape.selected_sources`. |
| **3 Capture** | Trigger + Substrate | `system:sync-platform-state` (mechanical recurrence) | **raw** into the capture lane (`retain + attribute`) — **NOT** `operation/` |
| **4 Derive** | Mechanism (judgment) | steward (Freddie) / headless deriver, on a wake | **derived** understanding into `operation/`, `cite`-ing the raw (`derived_from`) — the **only** phase that touches `operation/` |

The "vague and dangerous overlap" the operator named dissolves at Phase 3↔4: capture and derive become **two revisions by two writers**, not one fused write. Capture is dumb, mechanical, zero-LLM ("closer to a primitive"). Derive is the judgment act ("pure context play"). They are never the same write.

### D2 — `SyncPlatformState` re-targets the raw capture lane (amends ADR-264)

`SyncPlatformState`'s job is unchanged in spirit (mirror external state into substrate) but its **target** moves: it writes the raw lane (Phase 3), never `operation/` directly. A **separate** derive step (Phase 4 — a `judgment`-mode recurrence or a steward wake reading the raw) does the `operation/` write with `derived_from`. Preserved verbatim: the ADR-264 D4 dual-surface (the LLM-callable `platform_*` tool stays the ad-hoc-lookup companion), diff-awareness, per-item iteration, `write_revision` as the single write path, the `system:sync-platform-state` attribution.

**No write-gate change.** `inbound/` is already unlocked for `system:` callers (`CALLER_WRITE_POLICY["system"] = ()`, `api/services/workspace_paths.py:374`; `INBOUND_ROOT` exists at line 92). Phase 3 is already permitted — only the primitive's *routing* changes.

### D3 — Selection is a declaration with a consumer (amends ADR-113)

The OAuth callback's `compute_smart_defaults` → `landscape.selected_sources` (`api/routes/integrations.py:1482-1491`) is today a dead annotation. Phase 2 gives it a consumer: it becomes (or seeds) an operator-authored **watch declaration** — the peripheral analogue of the DP27 web-watch — that Phase 3's capture recurrence reads to know *which* channels to sync. Selection says *what slice is perceived*; it triggers nothing. "Ask Freddie to read #daily-work" is what authors a Phase-2 declaration + a Phase-3 recurrence.

### D4 — The bloat answer: quarantine + distill + un-defer GC

Connectors are the first **high-volume** transport, so the bloat discipline the operator demanded is first-class scope, not an afterthought:

1. **Raw is quarantined outside `operation/`** — the capture lane is not read by the steward's compact-index or the program's Home composition by default. A firehose channel does not dilute reasoning context. (This *reverses* today's behavior, where `SyncPlatformState` writes into `operation/` and every synced item is context-window-eligible — the dilution the operator fears is the current state, not a risk of the new lane.)
2. **Only the distilled derived understanding enters `operation/`** — Phase 4 is a summary sized to what a derive act cited, bounded by judgment, not by throughput.
3. **`inbound/` GC un-defers for the connector volume class.** ADR-376 §8 DEFERRED raw-lane GC (named trigger: "measured growth"). **Slack-scale volume is that trigger.** A retention policy on the capture lane (age-based / size-capped / derive-then-prune) is in this ADR's scope; the default may be generous, but the *mechanism* is named here rather than left deferred.

### D5 — The honest-UI contract (mechanism-independent)

The Connectors UI implies auto-sync that does not exist ("Connected · never synced · 0 sources"; `web/components/settings/ConnectedIntegrationsSection.tsx:46,301`; content is never read — `api/services/landscape.py:66-89` lists names only). The honest contract: **connecting makes a platform *available*; a declaration + a capture recurrence makes it *read*.** The copy must stop promising Phase 3+4 at Phase 1. This fix is independent of the mechanism decision and may land early.

### D6 — Per-connector raw directory (clarification, no new decision)

Each connector's raw lane is `inbound/{platform}/{selector}/{observed_at}.{ext}` — a dedicated per-platform directory, parallel to the live `inbound/mcp/{client}/` and `inbound/web/{source}/`. `{selector}` is the per-channel/page/label sub-lane (single-writer by construction). The raw dump lives there, immutable, never rewritten; only the derived distillation leaves for `operation/`. Under Option B (§3) the address becomes an `observation`-kind revision, but the quarantine-from-`operation/` property is identical.

### D7 — The selection surface: Phase 2 is a per-platform management subsurface writing a watch declaration

The per-connection channel/page/label setup is **Phase 2 (Select)**, and it needs a real surface + declaration substrate that today is a UI *promise* with no component (`ConnectedIntegrationsSection.tsx:712` says "Use 'Manage' to pick which channels…" — no Manage exists) and a dead data slot (`landscape.selected_sources`, no consumer).

- **Surface**: Channels surface → Connections pane → click a connected platform → a **per-platform selection subsurface** (the `landscape.resources` list with per-item in/out toggles). One level down, on the Channels surface (ADR-385), as the operator scoped.
- **Substrate**: the selection is a **watch declaration** (DP27 — declared, never crawled), the peripheral analogue of the web-watch. It gives `selected_sources` its consumer. It names *what slice is perceived*; it triggers nothing.
- **NOT a new `operation/` domain**: the connector's data does not create an `operation/slack/` tree. Raw → `inbound/slack/`; derived → subject-placed in `operation/` (meaning-organized, not platform-organized). Platform structure lives only in the quarantined raw lane. This is the anti-bloat discipline restated.

### D8 — Retention window: a substrate-read anti-bloat dial, pricing-ready (un-defers ADR-376 §8 GC)

The capture lane carries a **configurable retention window** — the un-defer of ADR-376 §8's raw-lane GC, made an operator dial:

- A per-workspace (eventually per-connection) `retention_days: <int>` in substrate (`governance/_retention.yaml` or a field on the watch declaration), **read at GC time — not a hard-coded enum**. The 7/14/30 are UI presets, not the only allowed values. Kernel default: generous (recommend 30 days).
- ~~**Derive-then-prune**: raw is GC'd only after it has been derived-and-cited; never GC a raw a derived act still needs.~~ **AMENDED by [ADR-401](ADR-401-the-connection-lifecycle.md) D4 (2026-07-02)** — this sentence was self-contradictory (its first clause says prune-iff-cited; its second says a cited raw is still needed) and the code shipped the first reading, which both breaks provenance (pruning raw a `derived_from`/trace chain points at) and never prunes in practice (nothing is cited until derive fires → the dial and the ADR-396 tier gate were no-ops). The ratified polarity is ADR-394 D4's, **evidence-bounded retention**: a **cited** raw is evidence and is **never** pruned; **un-cited** raw past the `retention_days` window is presumed noise and ages out. Unknown citation state (the gather failed) prunes nothing — fail-safe.
- **Pricing hook (mechanic here, mapping deferred)**: retention-window is a natural commons-scale **tier axis** (parallel to ADR-391's # principals · # connectors · autonomy-ceiling). This ADR builds the mechanic as a **read-one-value** policy so the pricing session can gate max-window-per-tier without touching GC code. **No pricing code here** — just the clean seam, documented so the pricing session inherits it ready.

### D9 — New-connection creation is ADR-353's domain; this ADR adds only the context-in half + write-scope pre-provisioning

The "kernel-vs-Composio ambiguity" for *creating* connections is **already resolved by [ADR-353](ADR-353-composio-as-driver-backend.md)** (Accepted 2026-06-22). This ADR does not re-open it; it names the relationship and closes one scope gap:

- **A connection is two flows of one thing** (ADR-332): a **peripheral-for-context-in** (this ADR — capture→derive) AND a **driver-for-work-out** (ADR-353 — mechanical execution behind `handle_platform_tool()`). Complementary, not competing. Naming this *is* the streamline the operator asked for.
- **Discovery / kernel-vs-Composio / where-a-connection-maps** are settled by ADR-353 §15 (demand-driven, never catalog-browse; the `feeds:` altitude test decides kernel-universal vs bundle-specific; Composio replaces only the execution layer, kernel keeps the whole surface). Not re-litigated here.
- **Downstream-write pre-provisioning is already modeled by construction**: an active `platform_connections` row satisfies both `read_{platform}` (`feeds: context`) and `write_{platform}` (`feeds: action`) capabilities — same `platform_connection_requirement` gate (`orchestration.py:1339-1361`), per-act-governed by ADR-307 + AUTONOMY. The connection *is* the grant; no separate roles layer is needed.
- **The one gap this ADR names**: OAuth **scope** granularity. If connect requests read-only scopes, a later `write_{platform}` is capability-available but fails at execution. **The connect flow must request the union of read+write scopes the platform's kernel-universal capabilities declare** (`api/integrations/core/oauth.py` per-provider `scopes`), so a connection is write-ready by construction — the operator's "accommodate downstream writes" requirement, met with the existing capability model, not a new permission mechanism.

## 3. The open decision — raw-lane mechanism (scope both, ratify one)

The four-phase model is mechanism-agnostic (`retain + attribute + cite` holds either way). But the raw's *storage shape* forks, because the re-founding (FOUNDATIONS v9.13, ratified, impl-deferred to a flag-day mode) is migrating exactly this:

| | **Option A — `inbound/` namespace (ship-now)** | **Option B — `revision_kind` (end-state)** |
|---|---|---|
| Raw lands at | `inbound/slack/{channel}/{observed_at}.md` — sibling of the live `inbound/mcp/` + `inbound/web/` | an `observation`-kind revision on the meaning-file; no `inbound/` |
| Derive | steward writes `operation/`, `derived_from` → raw path | `derivation`-kind revision on the same file, `derived_from` → observation revision-id |
| Shippable | **today** — `INBOUND_ROOT` exists, `inbound/` unlocked for `system:`, zero write-policy change | blocked on the flag-day migration mode |
| Singular-with | byte-identical to the two conformed transports **now** | the re-founding end-state (provenance as revision metadata) |
| Migration debt | shared, named, already-planned (migrates with MCP+web on flag-day) | none |
| Couples to | nothing new | the single-writer relaxation (folding raw into the meaning-file manufactures the multi-principal same-path write the steward-seat merge owns — Axiom 1 §6 amendment) |

**Decision: Option A (ratified 2026-07-01).** It makes connectors *singular with MCP + web today*, adds **no new** migration debt (the `inbound/`→`revision_kind` flip is shared with two live lanes and already on the re-founding ledger), and de-risks the connector fix from the flag-day timeline — the operator's Slack problem is real *now*, and B holds the fix hostage to an unscheduled migration. The invariant is identical across A and B, so the four-phase model and the derive discipline don't change when the mechanism flips — only the raw's address does.

Connectors enrol in the re-founding flag-day A→B flip alongside `inbound/mcp/` + `inbound/web/` (§5 step 8) — no connector-specific migration work.

## 4. What this preserves (compatibility)

- **`platform_connections` stays** — connection = peripheral = auth infra; a credential row is a permitted DB kind. Unchanged.
- **Platform tools stay** — `handle_platform_tool` + the `platform_slack_*` surface are the ad-hoc-lookup dual of `SyncPlatformState` (ADR-264 D4). Freddie can still call `platform_slack_get_channel_history` mid-loop for a one-off. The lane is for *systematic* intake; the tool is for *ad-hoc* lookup.
- **ADR-209 write path unchanged** — capture and derive are both ordinary `write_revision()` calls.
- **alpha-trader's live recurrences are NOT migrated — the two-mode split makes this correct.** `SyncPlatformState` has two distinct uses: (1) **ground-truth state mirror** (the trader's `platform_trading_*` positions/account/orders — the mirrored broker state IS the Reviewer's canonical world-model, read directly; ADR-264's original purpose + Axiom 8 ground-truth) and (2) **connector context-in** (Slack/Notion channel content → distilled; the `capture` mode). ADR-376 §63 is explicit that ground-truth intake is **NOT forced into an `inbound/` lane it doesn't need**. So the trader keeps its direct-`operation/` writes via the legacy `write_to` path — which is not a "migration window" but the **permanent, correct** shape for state mirrors. Every live bundle `SyncPlatformState` is a `platform_trading_*` mirror (verified: zero connector-context-in sync recurrences ship), so there is nothing to migrate. The `capture` mode (D2) serves the connector-context-in use; `write_to`-direct serves the ground-truth-mirror use. Both are permanent.
- **ADR-389/390 steward envelope unchanged** — the `peripheral_field_fact` already perceives connection *health*; this ADR gives the peripheral the *content* limb its health status was pointing at.

## 5. Implementation sequence (each limb its own commit, gated on ratification + mechanism)

0. **(Prereq)** ADR-353 is already Accepted — the creation/discovery/execution half is canon. This sequence is the context-in half only.
1. **Ratify** this ADR + the mechanism decision (A recommended). No code until then.
2. **Honest-UI copy fix** (D5, mechanism-independent) — with the ADR or just after.
3. **`SyncPlatformState` → raw lane** (D2, Option A) — the one primitive re-target; write-policy untouched. CHANGELOG entry (primitive behavior change). Test gate: capture lands in `inbound/{platform}/{selector}/`, derive step writes `operation/` with `derived_from`, round-trip `trace` walks the chain.
4. **Selection subsurface → watch declaration** (D3 + D7) — the per-platform Manage subsurface on the Channels Connections pane; write a watch declaration; give `selected_sources` its Phase-2 consumer; the capture recurrence reads it.
5. **Retention-window dial** (D8) — substrate-read `retention_days` + derive-then-prune GC on the capture lane; UI presets (7/14/30) over a dynamic value; leave the pricing tier-map seam documented for the pricing session.
6. **OAuth write-scope pre-provisioning** (D9) — connect flow requests the read+write scope union the platform's kernel-universal capabilities declare, so connections are write-ready by construction.
7. **~~Migrate alpha-trader~~ — CANCELLED.** The trader mirrors are ground-truth state (Axiom 8), not connector context-in (§4); ADR-376 §63 keeps them out of `inbound/`. Their `write_to`-direct write is permanently correct. Nothing to migrate.
8. **Wire the derive step + scheduler GC** — the capture recurrence lands raw; a derive act distils into `operation/` with `derived_from`; the scheduler runs `prune_raw_lane(cited_paths=...)`. The one remaining code limb after the primitives.
9. **Enroll connectors in the re-founding flag-day** (A→B mechanism flip) with `inbound/mcp/` + `inbound/web/` — cohort migration, no connector-specific work.

## 6. Anti-conflation summary (Axiom 0 dimensional check)

Primary dimensions: **Substrate** (Axiom 1 §9 — connector context lands in the raw lane, then a distilled derive in `operation/`) + **Trigger** (Axiom 4 — capture on a declared mechanical cadence) + **Mechanism** (Axiom 5 — the load-bearing move is splitting one fused write into a deterministic capture + a judgment derive).

Secondary and explicitly preserved: **Identity** (Axiom 2 — capture stays `system:sync-platform-state`; derive is steward/deriver-attributed — no new identity class); **Purpose** (Axiom 3 — Phase 2 selection is an operator declaration, DP27). No dimension spans without necessity: the capture/derive split is precisely a Mechanism-axis cut (deterministic vs judgment), which is why fusing them was the drift and splitting them is the fix.
