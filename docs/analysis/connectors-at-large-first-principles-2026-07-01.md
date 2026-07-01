# Connectors at Large — a first-principles pass on external context-in

> **Date**: 2026-07-01. **Status**: analysis / direction — scopes the thing to be ratified; the ratification is **[ADR-392](../adr/ADR-392-the-connector-lane.md)** (drafted alongside this doc). Doc-first; the code lands in follow-on commits gated to the ADR.
> **Origin**: the operator connected Slack, asked Freddie to read a channel, and hit "Connected · never synced · 0 sources." The blank-panel bug was a `session_messages` CHECK-constraint miss (closed, commit `35c044a`). The *real* finding is that the connector domain is half-wired — and the operator's read is that it needs its own axiomatic lane, "singular, future-proof," aligned with the service model + filesystem Phase-1, rather than a patch.
> **Companion receipts**: [perception-and-the-principal-commons](perception-and-the-principal-commons-first-principles-2026-06-30.md) (the principal-vs-peripheral taxonomy, ratified as ADR-389); [ADR-376](../adr/ADR-376-ledger-intake-raw-observation-vs-derived-substrate.md) (the ledger-intake axiom this doc applies to connectors); [the re-founding keystone](the-re-founding-meaning-folders-and-permission-as-metadata-2026-06-29.md) (the mechanism migration this doc must not collide with).

This doc draws the line first, then says what follows for the connector lane, the `SyncPlatformState` primitive, the surface, and the bloat/GC question. It does **not** prescribe the implementation shape unilaterally — the raw-lane *mechanism* (namespace vs revision-kind) is scoped both ways and the commit is deferred to ADR-392 ratification (the operator's call).

---

## 1. The question, stated precisely

When an operator connects Slack (or Notion, GitHub, a broker) to a workspace, three distinct things are happening, and today they are **fused into one ambiguous motion**:

1. **Connection (setup)** — an OAuth handshake stores an encrypted credential. This is auth infrastructure.
2. **Selection (secondary setup)** — *which* channels/pages/repos are in scope. Slack has hundreds of channels; the operator wants two.
3. **Context-intake (the ongoing play)** — the connected+selected slice's *content* becoming readable substrate the operation reasons over.

The operator's thesis: these three need **a dedicated, singular lane** with clean seams, because the current overlap between "selection" and "intake" — and between "intake" (mechanical) and "understanding" (a Freddie/LLM judgment act) — is *"vague and dangerous."* And downstream of all of it: the intake content has *"potential for un-necessary bloat of the filesystem"* (performance, cost, context dilution), which is a fourth thing that needs an explicit answer.

The load-bearing sub-question the operator posed: **how is a platform connection writing channel history fundamentally different from an MCP-AI writing documents into the substrate?** Answer that, and the connector model falls out.

---

## 2. The answer: connectors are the third transport of one context-in contract — and the *only* one not yet conformed to it

YARNNN has exactly **three context-in transports**. Trace each to the substrate:

| Transport | Capture (raw) lands at | Attributed as | Derive step (understanding) | Conforms to ADR-376? |
|---|---|---|---|---|
| **MCP LLM** (`remember`) | `inbound/mcp/{client}/{slug}.md` | `yarnnn:mcp:{client}` | integrity wake → steward derives into `operation/`, `derived_from` cites the raw | ✅ **Implemented** (2026-06-26) |
| **Web/RSS source** (`TrackWebSources`) | `inbound/web/{source}/{observed_at}.xml` | `system:track-web-sources` | distilled `_watch_signal.yaml` carries `derived_from` block-list citing the raws | ✅ **Implemented** (2026-06-26) |
| **Platform connection** (Slack/Notion/broker; `SyncPlatformState`) | — *no raw lane* — | `system:sync-platform-state` writes **straight to `operation/`** | — *fused into capture; no separate derive; no `derived_from`* — | ❌ **The lone violator** |

The receipts:
- MCP two-phase split: `api/services/mcp_composition.py:343-375` (capture) + `:351-356, 403-464` (derive-and-cite).
- Web two-phase split: `api/services/primitives/track_web_sources.py:54-60, 172, 191`.
- Connector single-phase collapse: `api/services/primitives/sync_platform_state.py:307-314` — `write_revision` targets `write_to` directly (an `operation/…` path in every live usage), attributed `system:sync-platform-state`, **no `inbound/`, no `derived_from`**.

**This is the answer to the operator's load-bearing question.** A platform connection writing channel history and an MCP-LLM writing a document are *the same kind of thing at the ledger floor* — both are context-in transports that (per ADR-376/DP32) must `retain + attribute + cite`: a raw observation in, a separate derived citing act out, the raw never rewritten. The operator's instinct — "I'm not sure Sources/Connections are different from an MCP-AI writing a document" — is **correct**. They aren't. They diverge only in *transport* (an API pull vs an LLM push) and in *volume* (a chatty channel vs an occasional `remember`), not in *contract*.

`SyncPlatformState` predates ADR-376 (it is ADR-264, 2026-05-10; the ledger-intake axiom is 2026-06-26). It was never reconciled to the axiom the other two transports were fixed to honor. **That non-conformance IS the "vague and dangerous overlap" the operator sensed** — connectors collapse capture and derive into one step and skip the raw lane, which is exactly the pre-ADR-376 conflation ("one namespace doing two jobs") the axiom exists to forbid.

### The principal-vs-peripheral placement (ADR-389/390)

A connection is a **peripheral** — a driver-class transport with no intent, attributed to the `system:` mechanism that operated it, judged by the steward for **health** (live? expired? stale?), never for **honesty** (there is no "who" behind a broker API to lie about who it is). This is settled canon (ADR-389 D1; ADR-335 "transports are peripherals"). The steward already *perceives* the connection's existence + health via the `peripheral_field_fact` in its wake envelope (`api/services/freddie_envelope.py:800-868`).

But — the precise gap — **the peripheral field shows the connection's status; it does not create the connection's content.** The envelope's own docstring says a connection "*via SyncPlatformState* mirrors external state into substrate" (`freddie_envelope.py:814-817`) — but that `via` is the path nobody walks for Slack. The steward sees `slack · status: active` with no substrate behind it. **The taxonomy is complete; the connector's intake path is the missing limb.** Web/RSS got its intake path (ADR-335/336); platform connections only got theirs *buried inside the alpha-trader bundle*, for `platform_trading_*` only.

---

## 3. The four-phase connector lane (the singular model)

The operator asked for a dedicated lane that separates the concerns. The Six Dimensions (Axiom 0) give the seams; the ledger-intake axiom (ADR-376) gives the capture/derive split. The connector lane is **four phases, each in one dimension, each with one writer**:

```
 Phase        Dimension (Axiom 0)     Writer                     Substrate effect
 ───────────  ──────────────────────  ─────────────────────────  ─────────────────────────────
 1 CONNECT    Identity / auth         OAuth callback (system)    platform_connections row (a
                                                                  permitted DB kind — credential)
 2 SELECT     Purpose (declaration)   operator (via chat/UI)     a WATCH DECLARATION in substrate
                                                                  — "these channels are in my
                                                                  perception aperture" (DP27:
                                                                  declared, never crawled)
 3 CAPTURE    Trigger + Substrate     system:sync-platform-state RAW into the capture lane
              (mechanical, no LLM)    (mechanical recurrence)    (retain + attribute) — NOT
                                                                  operation/
 4 DERIVE     Mechanism (judgment)    steward (Freddie) or a     DERIVED understanding into
              (separate act)          deriver, on a wake         operation/, cite-ing the raw
                                                                  (derived_from) — the ONLY step
                                                                  that touches operation/
```

The seams the operator wanted are now sharp:

- **Selection is a declaration, not a sync.** Phase 2 writes an operator-authored watch declaration (the Purpose dimension) — a peripheral analogue of the DP27 web-watch. It says *what slice is perceived*; it triggers nothing. This is the clean home for "which Slack channels / Notion pages," and it kills the dead `selected_sources` annotation (`landscape.selected_sources` today has no consumer — `api/routes/integrations.py:1482-1491`).
- **Capture is dumb and mechanical.** Phase 3 is a `mechanical`-mode recurrence (ADR-263) invoking `SyncPlatformState`. It retains raw; it does not interpret. Zero LLM. This is the "closer-to-a-primitive" half the operator distinguished from "context play."
- **Derive is the judgment act.** Phase 4 is the *separate* step where Freddie (or a headless deriver) reads the raw and writes understanding into `operation/`, citing it. This is the "pure context play" half. **The dangerous overlap dissolves because capture and derive are now two revisions by two writers, not one fused write.**

Every seam already has canonical precedent — this is not a new architecture, it is *making connectors conform to the one every other transport already follows*.

---

## 4. The bloat / dilution question — the model contains it *if* connectors are forced through it

The operator's fourth concern (performance, cost, context dilution) is real and is *why the two-phase split matters most for connectors specifically*. Slack is the first **high-volume** transport — MCP `remember` and web feeds are low-volume; a chatty channel synced on a tight cadence is a firehose. The lane contains the blast radius on three axes:

1. **The raw lane is quarantined outside `operation/`.** Raw Slack lands in the capture lane (`inbound/slack/…` under the current mechanism), which the steward's compact-index and the program's Home composition **do not read by default**. A firehose channel does not dilute `operation/` context or bloat the reasoning window. (Contrast today: `SyncPlatformState` writes *into* `operation/`, so every synced item is context-window-eligible — the dilution the operator fears is the *current* behavior, not a risk of the new lane.)
2. **Only the distilled derived understanding enters `operation/`.** Phase 4 is a *summary*, sized to what a derive act chose to cite — not the raw stream. Context dilution is bounded by judgment, not by channel throughput.
3. **`inbound/` GC is the one genuinely-new requirement connectors raise.** ADR-376 §8 explicitly **DEFERRED** raw-lane GC ("raw is permanent, no GC — named trigger: measured growth") because MCP + web volume never triggered it. **Slack-scale volume is that trigger.** Connectors are the reason to un-defer it. This is a first-class part of the connector scope, not an afterthought — a retention policy on the capture lane (age-based, size-capped, or derive-then-prune) belongs in ADR-392's scope even if the *default* is generous.

**The discipline the operator wanted — no un-necessary filesystem bloat — is exactly what the raw-lane split delivers, and it is the strongest single argument for conforming connectors to ADR-376 rather than leaving them writing to `operation/`.**

---

## 5. The one mechanism decision — scoped both ways, deferred to ratification

Everything above is **mechanism-agnostic**: the invariant (`retain + attribute + cite`, four-phase lane, quarantined raw) holds regardless of *how* the raw is stored. But the raw-lane *storage shape* has an open fork the operator must decide at ADR-392 ratification, because the re-founding (FOUNDATIONS v9.13, ratified-with-revisions, **implementation deferred to a flag-day mode**) is mid-migration on exactly this point.

### Option A — current `inbound/` namespace lane (ship-now)

Design connectors against today's mechanism: raw lands at `inbound/slack/{channel}/{observed_at}.md`, a sibling of the *already-live* `inbound/mcp/` and `inbound/web/` lanes.

- **Pro**: shippable today; **byte-identical in shape** to the two conformed transports (maximally *singular* with what exists); `INBOUND_ROOT` already exists (`api/services/workspace_paths.py:92`), `inbound/` is already write-permitted for `system:` callers (`CALLER_WRITE_POLICY["system"] = ()` — no lock; line 374), so **zero write-policy change** — only a routing change inside `SyncPlatformState`.
- **Con**: the re-founding will migrate `inbound/`-as-namespace → `revision_kind` on the meaning-file's chain (ADR-376 as amended by ADR-384). Connectors would carry the same small, *named*, already-planned migration debt the other two lanes carry — they migrate together on flag-day.

### Option B — post-re-founding `revision_kind` (end-state)

Design connectors against the end-state: raw capture = an `observation`-kind revision on the meaning-file; derive = a `derivation`-kind revision on the same file, `derived_from` → the observation revision-id. No `inbound/` namespace.

- **Pro**: no migration debt; the most future-proof; provenance rides revision metadata (the re-founding's thesis).
- **Con**: blocked on the flag-day migration mode landing; connectors can't fully ship until then; the scoping becomes "the connector chapter of the re-founding" rather than a standalone streamline. Also re-opens the single-writer relaxation coupling (folding raw *into* the meaning-file manufactures the multi-principal same-path write the steward-seat merge must own — FOUNDATIONS Axiom 1 sixth sub-clause amendment).

### Recommendation

**Ship Option A now, migrate with the cohort.** Rationale: (1) it makes connectors *singular with MCP + web today* — three transports, one lane shape — which is the operator's "singular" goal met immediately; (2) the migration debt is not connector-specific — it's shared with two already-live lanes and already on the re-founding's ledger, so conforming connectors to `inbound/` *adds no new debt*, it just enrolls connectors in a migration that was going to happen anyway; (3) it de-risks the connector fix from the flag-day timeline — the operator's Slack problem is real *now*, and Option B holds the fix hostage to an unscheduled migration. The invariant is identical across A and B, so nothing about the four-phase model or the derive discipline changes when the mechanism flips — only the raw's *address* does.

ADR-392 records both, recommends A, and leaves the final commit to ratification per the operator's explicit "scope both, decide at ratification."

---

## 6. The mental-model fix (independent of the mechanism decision)

The Connectors UI says Slack is for "Team collaboration and context" (`web/components/settings/ConnectedIntegrationsSection.tsx:301`) and shows "Connected · never synced · 0 sources" (`relativeTime()` → "never synced", line 46). The connect-once-reads-automatically framing **implies auto-sync that does not exist** — connecting stores a token and discovers channel *names* (`api/services/landscape.py:66-89` lists channels; never reads content), then stops at the deleted-scaffold comment (`api/routes/integrations.py:1498`).

Whichever way the four-phase lane is built, the honest operator contract is: **connecting makes a platform *available*; a declaration + a capture recurrence makes it *read*.** In the steward model, "connect then ask Freddie to read #daily-work" is the intended path — Phase 2 (select) + Phase 3 (capture) are what "ask Freddie to read it" should *author*. The UI must stop promising Phase 3+4 at Phase 1. This copy fix is correct regardless of A-vs-B and can land early; ADR-392 names it as part of the connector contract.

---

## 7. What this does NOT change (compatibility)

- **`platform_connections` stays** — a credential row is a permitted DB kind (Axiom 1; SERVICE-MODEL "four DB row kinds"). Connection = peripheral = auth infra. Unchanged.
- **Platform tools stay** — `handle_platform_tool` and the LLM-callable `platform_slack_*` surface are the ad-hoc-lookup dual of `SyncPlatformState` (ADR-264 D4). Freddie can still call `platform_slack_get_channel_history` mid-loop for a one-off. The lane is for *systematic* intake; the tool is for *ad-hoc* lookup. Both survive.
- **`SyncPlatformState`'s job is unchanged in spirit** — mirror external state into substrate. What changes is its *target*: it routes to the raw lane (Phase 3), and a *separate* derive step (Phase 4) does the `operation/` write. Its ADR-264 dual-surface, diff-awareness, and per-item iteration are all preserved.
- **alpha-trader's live recurrences** — `platform_trading_*` writes currently land in `operation/` directly. They are the migration's first customer: their `SyncPlatformState` lines re-target the raw lane and a derive recurrence is added. This is a bundle-scoped follow-on, not a kernel breaking change (the primitive keeps working; the bundle re-authors its recurrences).

---

## 8. Operator's four consideration points (folded in 2026-07-01)

The operator raised four sharpening questions after the first pass. Each is answered here with receipts; each lands a decision in ADR-392.

### 8.1 — "Does every connector get a dedicated `inbound/{platform}/` directory where the raw dumps live?" (clarification)

**Yes — under Option A (ship-now).** Each connector's raw capture lane is `inbound/{platform}/{selector}/{observed_at}.{ext}`, exactly parallel to the two live transports:

```
inbound/
  mcp/{client}/{slug}.md          ← LIVE (MCP remember)
  web/{source}/{observed_at}.xml  ← LIVE (TrackWebSources)
  slack/{channel}/{observed_at}.md    ← NEW (this ADR)
  notion/{page}/{observed_at}.md      ← NEW
  gmail/{label}/{observed_at}.md      ← NEW
```

The `{selector}` segment is the per-channel/per-page/per-label sub-lane — the same `{client}`/`{source}` sub-lane pattern the live transports use (single-writer by construction; `system:sync-platform-state` attributed). The raw dump lives here, immutable, never rewritten. Only the **derived** distillation (Phase 4) leaves `inbound/` for `operation/`. Under Option B (post-re-founding) the *address* changes to an `observation`-kind revision on the meaning-file, but the operator-facing mental model is identical: raw is quarantined from `operation/` either way.

### 8.2 — Per-connection channel/page/label setup + management (the selection surface)

**This is Phase 2 (Select), and it currently exists as a data slot + a UI promise but no UI.** The receipts:
- The Connections pane copy already *promises* it: *"Use 'Manage' to pick which channels, pages, or repos it should read"* (`web/components/settings/ConnectedIntegrationsSection.tsx:712`) — but there is **no Manage component**; the pane only connects/reconnects/disconnects.
- The data slot exists: `landscape.selected_sources` (`api/routes/integrations.py:1482-1491`), populated by `compute_smart_defaults` at OAuth, **with no consumer**.
- The discovery data exists: `discover_landscape` returns the full channel/page list (`api/services/landscape.py:66-89`).

**The operator's read is correct: this is a dedicated per-platform management surface, one level down from the Connections pane, on the Channels surface.** The model:

- **Home**: Channels surface → **Connections** pane (the existing `arrow-left-right` surface, ADR-385) → click a connected platform → a **per-platform selection drawer/subsurface** (Slack channels / Notion pages / Gmail labels / GitHub repos). This is the `landscape.resources` list with a per-item in/out toggle.
- **What it writes**: the selection is a **watch declaration** (DP27 — declared, never crawled) that becomes the *consumer* of `selected_sources`. It is the peripheral analogue of the web-watch declaration. It names *what slice is perceived*; it does not itself sync.
- **What consumes it**: Phase 3's capture recurrence reads the declaration to know which `{selector}`s to walk into `inbound/{platform}/`.

This is a genuine new **surface + declaration substrate**, and it is the missing bridge between "connected" and "read." It is NOT a new *domain* in the `operation/` sense — the raw lands in `inbound/`, and the derived understanding lands wherever the derive act places it in `operation/` (by subject, per the meaning-organized filesystem, not per-platform). **Selection ≠ a platform-named operation folder.** The connector's data does not create a `operation/slack/` tree; it creates `inbound/slack/` (raw) + subject-placed derived files. This is the anti-bloat discipline restated: platform structure lives in the quarantined raw lane, meaning-structure lives in `operation/`.

### 8.3 — Retention optionality (7/14/30-day) as the anti-bloat mechanic + a pricing hook

The operator wants a **configurable retention window** on the capture lane, with defaults, dynamically changeable (not hard-coded), and *ready to be wired into pricing in a later session*. This is the un-defer of ADR-376 §8's raw-lane GC, made a first-class operator dial.

**The mechanic (scoped here, wired later):**
- A per-workspace (eventually per-connection) **retention policy** on `inbound/{platform}/`: `retention_days: <int>` with a kernel default. Raw observations older than the window are GC'd **after** they have been derived-and-cited (never GC raw a derived act still points at, unless the derived copy is self-sufficient — the safe default is derive-then-prune).
- **Not a fixed enum in code** — a value in substrate (`governance/_retention.yaml` or a field on the watch declaration), read at GC time. The 7/14/30 are *presets the UI offers*, not the only allowed values. Default: a generous kernel floor (recommend 30 days) so no operator loses data silently.
- **The pricing hook (documented, deferred to the pricing session):** retention window is a natural **tier axis** — longer raw retention = more storage = a higher tier, exactly parallel to the ADR-391 commons-scale tiering direction. The mechanic must expose retention as a **read-one-value** policy so the pricing layer can gate the *maximum allowed* window per tier without touching the GC code. ADR-391's "balance = workspace's, envelopes = principals'" model already has the shape; retention-window-as-tier-axis slots in as a commons-scale dimension (# principals · # connectors · autonomy-ceiling · **raw-retention-window**). **This session builds the mechanic (a substrate-read retention value + GC honoring it); the pricing session sets the tier→max-window mapping.** No pricing code here — just the clean seam.

### 8.4 — New-connection creation: the kernel-vs-Composio ambiguity + downstream-write pre-provisioning

The operator flagged a "weird ambiguity between kernel projects and Composio utilization" for *creating* connections, and wants (a) the creation/discovery workflow streamlined and (b) new connections to **pre-provision downstream write scopes** for agents ("pre-advanced permissions and roles," not strictly context-in).

**(a) The ambiguity is already substantially resolved by ADR-353** (Composio-as-driver-backend, Accepted 2026-06-22) — the operator may not have had it in view. The settled canon:
- **Discovery is demand-driven, never catalog-browse** (ADR-353 §15.1): a connection is added because *a program declares it needs an action against a platform* (`dependencies.lean` in a MANIFEST, a live recurrence hitting a `[CONNECTION-DEMAND]` gap, or a four-flow design). Composio's 1,000+ catalog is the **supply-check consulted last**, never browsed cold. (OS analogy: you plug in a device; the OS has the driver or installs one — you don't browse the driver DB.)
- **Kernel-vs-Composio is not the fork; the fork is first-party-vs-driver *execution*** (ADR-353 §2-3): the kernel *always* owns the surface (tool names, capability-gating, the ADR-307 gate, attribution, substrate writes). Composio only replaces the *mechanical execution layer* behind `handle_platform_tool()`. Slack/Notion/GitHub stay first-party *for now* (they have non-driver callers — landscape sync, exporters); **new** platforms with no first-party client get wired via Composio with zero client code.
- **Where a new connection maps** is decided by the `feeds:` altitude test (ADR-353 §15.2), NOT by "kernel vs Composio": **kernel-universal** capabilities (`read_slack`/`write_slack`, `feeds: context|action`, generic hands many programs reuse) live in `orchestration.py::CAPABILITIES`; **program-specific** capabilities (`read_trading`, whose data IS the ground-truth) live in the bundle `MANIFEST.yaml`. The operator's "project-type-specific" instinct is *correct for program-defining connections, not for universal ones* — the two-home split is the answer, `feeds:` is the decider.

**What this ADR adds to ADR-353**: nothing to the *execution* seam (that's settled) — only the **context-in half**. ADR-353 is about connectors as *hands* (outbound execution); this ADR is about connectors as *perception* (inbound capture→derive). They are the two flows of one connection (ADR-332 four-flow model): **a connection is simultaneously a peripheral-for-context-in (this ADR) and a driver-for-work-out (ADR-353).** The ADRs are complementary, not competing — and naming that relationship *is* the streamline the operator asked for.

**(b) Downstream-write pre-provisioning is already modeled by construction** — the concern is largely solved, with one real gap:
- An active `platform_connections` row satisfies **both** the read capability (`read_slack`, `feeds: context`) **and** the write capability (`write_slack`, `feeds: action`) — both gate on the same `platform_connection_requirement: {platform: slack, status: active}` (`api/services/orchestration.py:1339-1361`). So connecting Slack *already* pre-authorizes downstream agent writes to Slack, gated per-act by ADR-307. There is no separate "advanced permission" step to build — the connection *is* the grant, and the ADR-307 gate + AUTONOMY mode govern how far each write binds.
- **The one real gap is scope-granularity at OAuth time.** A connection is provisioned with whatever OAuth *scopes* the initial handshake requested. If the connect flow requests read-only Slack scopes, a later `write_slack` capability is gated-available but will *fail at execution* for lack of the write scope. **So "pre-advanced permissions" means: request the union of read+write scopes the platform's capabilities imply at connect time**, so the connection can accommodate downstream writes without a re-auth. This is an OAuth-scope-request decision (`api/integrations/core/oauth.py` `scopes` per provider), not a new permission mechanism. ADR-392 names it: **the connect flow should request the full read+write scope set the platform's kernel-universal capabilities declare, so a connection is write-ready by construction** — matching the operator's "connection can accommodate downstream writes" requirement without inventing a roles layer the capability model already provides.

---

## 9. Recommended sequence

0. **(Prereq) Read ADR-353** — the connection-creation / Composio / discovery half is already canon; this arc is only the context-in half. Don't re-litigate the execution seam.
1. **Ratify the four-phase connector lane** (ADR-392, doc-first) — the capture/derive split, selection-as-declaration, the raw-lane invariant connectors must honor, the bloat/GC scope, the mechanism decision (A recommended). No code moves until this ratifies.
2. **Land the honest-UI copy fix** (low-risk, mechanism-independent) — can go with the ADR or just after.
3. **Route `SyncPlatformState` through the raw lane** (Option A) — the one primitive change; write-policy needs no touch. Add the derive step as a `judgment`-mode recurrence or a steward wake.
4. **Un-defer `inbound/` GC** for the connector volume class — a retention policy on the capture lane.
5. **Migrate alpha-trader's recurrences** to the two-phase shape (bundle follow-on).
6. **Enroll connectors in the re-founding flag-day** (A→B mechanism flip) alongside `inbound/mcp/` + `inbound/web/` — no connector-specific work, just cohort migration.

The discipline that governs this: **connectors are not a new transport class — they are the third instance of a context-in contract two other transports already honor.** The whole scope is "make the lone non-conformer conform, and answer the one thing it raises that the others didn't (volume → GC)." That is a streamline, not an invention — exactly the singular, future-proof shape the operator asked for.
