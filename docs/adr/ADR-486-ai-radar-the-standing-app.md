# ADR-486: AI Radar — the Standing App (Making Perceive Felt)

> **Status**: **Proposed** (2026-07-24) — doc-first; no code ships with this ADR. The name **"AI Radar" is provisional** (operator: run with it for now, subject to change; a rename before implementation is a title edit, not a re-decision).
> **Date**: 2026-07-24
> **Dimension**: **Trigger** (Axiom 4 — self-running vs addressed) primary; **Channel** (Axiom 6 — a new app on the desk) secondary; **Substrate** (Axiom 1 — accumulation + derivation over a meaning-folder) tertiary.
> **Relates to**: ADR-457 (Think·Make — this adds the third felt verb; §6 amends its investment-priority *narrowly*), ADR-335/336 (perception field / TrackWebSources — the watch machinery this fronts), ADR-401 (D5 named the derive gap; Phase 3 is this ADR's R0), ADR-404 (capture-lane dormancy — explicitly **not** reversed here), ADR-296/298 (wake architecture — the spine this reuses), ADR-435 (Home deleted — the drift guard's origin), ADR-405 (witness dial — how standing output reaches the member), ADR-460 (agents: no-authority discipline — preserved structurally), ADR-333 (compose as lazy projection — made real for folders), ADR-423/448 (`revision_kind` / `derived_from` — the ledger vocabulary the loop writes), ADR-468/472 (the Images unveil rule — the sequencing precedent), ADR-198 (Dashboard archetype), AGENT-TAXONOMY.md (monitor: "the one arguable 5th verb," resolved out of the agent tier, never out of the product).

---

## 1. Context — the third verb has an engine and no body

ADR-457 named five acts — **perceive · think · make · settle · govern** — and observed that two are felt: Think (`/chat`) and Make (`/studio`, `/images`). The desk sentence is "a desk with two verbs over a commons that remembers."

The 2026-07-24 discourse started as "should we carve a research app?" and resolved against it on the addressed reading (research-as-conversation is a posture of Think — the Researcher agent; a research surface would own no artifact grammar and rebuild the second-AI-door problem). The operator then re-cut the question onto a different dimension:

> "what if a dedicated app closer to tracking, or research hub, where-in the fundamental added difference is that it's **self-running** (either cron jobs or recurrences) layered on top of dashboard like features, the substrate to support it… both a cumulative, substrate management, and dashboard analytics and insights like centered app."

That is not a variant of chat. It is the **Trigger axis** — the only cell of the desk no app owns. Chat, Studio, and Images are all addressed: nothing happens until a member acts. The proposal is the app whose defining property is that it runs while the member is away — **perceive, made felt**. The operator ratified the direction and the subject-first carve (§4 D2) in discourse on 2026-07-24.

AGENT-TAXONOMY had already flagged this shape as the one genuine exception in the verb space: *"monitor = the ONE arguable 5th [verb], BUT needs standing intent which base agents lack → resolves OUT of the base tier."* It resolved out of the **agent** tier. It never resolved out of the **product**. Standing work was left homeless, not refuted. This ADR gives it a home — and puts the standing intent where it always belonged: on a **declaration**, not an agent (§4 D3).

## 2. The receipts — the standing engine is built, live, and idle

Audited 2026-07-24 (code + prod DB). The finding in one sentence: **the plumbing (schedule → fire → invoke → intake → derive → embed) is ~80% live; the missing ~20% is precisely the autonomous seam.**

| Subsystem | State | Evidence |
|---|---|---|
| Scheduler cron → wake queue → drainer → `invoke_freddie` | **LIVE** (gated `AGENT_ENABLED`, default ON) | `render.yaml:72-74` (`*/5` cron), `unified_scheduler.py:337,342,460-466`, `wake.py:121,653` |
| Recurrence schema + walker + next-run | **LIVE** | `recurrence.py:1-44`, `scheduling.py` |
| Declared recurrences in prod | **ZERO** — the engine idles | `/workspace/_recurrences.yaml` = `[]`; `tasks` scheduling index: 0 rows; last `cron_tick` wake **2026-06-29** |
| `TrackWebSources` (ADR-336) | **CALLABLE, DORMANT** (rides the capture lane) | `primitives/track_web_sources.py:100`, `registry.py:597` |
| Capture lane | **DORMANT** by ratified decision | `CONNECTOR_CAPTURE_ENABLED` default OFF (ADR-404 D2), `connector_capture_gating.py:49-53` |
| Watch authoring | **NO in-product writer** — watches are bundle-shipped only | `routes/sources.py` reads, never writes; `_sources.yaml`/`_watch.yaml` seeded by bundle fork |
| A "derive" wake source | **DOES NOT EXIST** | five sources only: `cron_tick · addressed · proposal_arrival · substrate_event · manual_fire` (`wake_sources/__init__.py:7-11`); ADR-401 Phase 3 unbuilt |
| Retention / cited-path GC | **MOOT** until derive fires | `connector_retention.py:174-176` — nothing derives → `cited_paths=∅` → nothing pruned |
| Folder-scoped composed view | **DOES NOT EXIST** | `compose/engine.py:1262` composes sections→HTML (has a `dashboard` mode); no lazy projection over a folder (ADR-333 is doc-only here) |
| Standing-work surfaces | all **search-only**, chrome largely `STEWARD_CHROME_ENABLED`-gated off | `kernel_surfaces.py:330-384,670-703` (notifications · recurrence · queue · activity) |
| Settle — the derive pattern | **LIVE, human-gesture only** | `settle.py:125-163` (topic ladder), `:347` (`revision_kind="derivation"` + `derived_from`), `:353` (embed) |

The ledger tells the same story from the substrate side (prod, 2026-07-24):

- Revisions by kind: **828 authored · 36 observation · 19 derivation.**
- Every `observation` traces to a human act (35 `operator` uploads, 1 MCP `remember`). Zero from any standing watch.
- Every `derivation` traces to a human act (settle clicks, member lane turns, upload extraction via `system:extract`). **Zero unaddressed derivations, ever** (post-migration-208).
- The one standing chain that ever ran: `derive-capture-slack` fired **24 times through 2026-07-03** — then the capture lane went dormant (ADR-404) and the workspace's last standing act is that date. (Those writes predate migration 208, hence carry no `revision_kind` tag.)

The honest one-line state: **yarnnn has a working standing engine that has been declaratively empty and observably silent since early July.** This ADR is the decision about what body that engine gets.

## 3. First principles — what distinguishes AI Radar from every existing app

The decisive question, as in ADR-472: **what is the artifact, and what does the system own?**

| Layer | Chat (Think) | Studio / Images (Make) | **AI Radar (Perceive)** |
|---|---|---|---|
| Trigger | addressed — a member speaks | addressed — a member edits/prompts | **standing — a declaration fires on cadence** |
| Artifact | the lane (transcript; record only via settle) | the file (document / composition) | **the hub — a meaning-folder that thickens: watches + observations + cited briefs + a composed view** |
| Felt unit | the reply · the settle beat | the artifact | **the brief — a derived, cited "what changed" note** |
| Relevance | this conversation | this artifact | **cumulative — the accumulation moat made visible** |
| Grammar owned | dialogue + settle | flow / paged / canvas composition | **watch declarations + accumulation + dashboard composition (the ADR-198 Dashboard archetype, reborn scoped)** |

Three of five layers diverge from everything on the dock; the two that converge (attributed revisions on one ledger; residency of kernel colleagues) are exactly the shared kernel — the same boundary shape the Images carve cut along.

**Why this is not the cockpit returning.** The supervision-era product (Home, ADR-312/367; deleted ADR-435) was a *workspace-global* composition — one front page for the whole operation, governance-forward. A hub is **topic-scoped and plural**: "a radar on competitor X," "a radar on this market." Member-created, many per workspace, each over one meaning-folder. Scope is the difference between the graveyard (Home, Feed, Context, Channels-flow — four deletions of workspace-global ambient composition) and the living precedent (Studio artifacts — scoped, plural, member-owned).

## 4. Decisions

### D1 — AI Radar is the standing app: topic hubs on the desk

A first-class app in the ADR-472 sense — its own surface, route, and eventually dock icon (sequenced by D7) — whose unit is the **hub**:

- A hub = one meaning-folder (`operation/{topic}/` per the ADR-457 D4 convention) carrying: **watch declarations** (what to look at) + a **cadence** (when to sweep) + accumulating **observations** (`revision_kind="observation"`, attributed intake) + derived **briefs** (`revision_kind="derivation"` + `derived_from`, cited, embedded) + a **composed view** rendered on read (D5).
- Vocabulary (member-facing): the **sweep** (a scheduled fire), the **brief** (the derived insight — "Radar delivers briefs"), the **hub** (the topic). "Put it on your radar" is the member gesture, in words a layman already owns.
- The name "AI Radar" is provisional per the status banner. The *shape* — standing, topic-scoped, cumulative, composed — is the decision.

### D2 — Subject-first, never source-first: platform upkeep is excluded

Two candidate modes were weighed and deliberately split:

1. **Platform upkeep** ("what happened in my Slack/Notion") — source-first, workspace-global, recency-dominant, commodity (every platform ships native recaps of its own silo). **Excluded.** It has the Home/Feed failure shape (workspace-global ambient composition, deleted four times), it depends on the capture lane whose dormancy is a ratified launch decision (ADR-404 — re-lighting it is its own discourse and **this ADR does not flip `CONNECTOR_CAPTURE_ENABLED`**), and it is the weakest competitive ground.
2. **Topic hubs** ("what do we know about X, and what changed") — subject-first, cumulative, cross-source, attributed. **This is the app.**

The reconciliation is already canon: a connection is a **peripheral, never the center** (ADR-401 D1). When capture re-lights, a platform connection re-enters as *a source feeding a hub* — one more row in a hub's watch declaration — not as an inbox. Connection management stays in the management plane (ADR-338).

**The standing rule this D binds: the app must never become an inbox.** Any pane whose organizing key is a *source* rather than a *subject* is this decision violated.

### D3 — Standing intent lives on the declaration, never on an agent

The hub's cadence + watches are **declarations** (the recurrence/watch shape the kernel already parses), authored by the member through the app (R1). The kernel fires them; an invocation with the Researcher posture executes the sweep; the witness dial (ADR-405) governs how the member hears about output (notification after-witness by default — a sweep's brief is a read/derive act, nothing to approve).

Explicitly preserved:

- **ADR-460's no-authority discipline is untouched.** No agent object gains a standing-intent field, an authority field, or any new key. The Trigger fact rides the declaration — where `_recurrences.yaml` has always carried it. (AGENT-TAXONOMY's "monitor needs standing intent which base agents lack" stays true; the *product* gets monitoring without the *agent tier* changing.)
- **The ADR-307 cliff is never approached.** The loop is watch → observe → derive → compose: reads, intake, derivation, projection. No consequential external action exists anywhere in it. A future hub feature that wants to act outward (post the brief to Slack, trade on the signal) is a *different decision* that goes through the gate — it does not ride in on this app.

### D4 — The standing derive organ: the missing seam, built on the settle pattern

The load-bearing build. Today every derivation in prod traces to a human act; ADR-401 D5, ADR-457 D3, and the axiomatic roster derivation all independently located the same gap — *the chain breaks at derive*. Settle covered the addressed instance (a member clicks "keep this"). AI Radar builds the **unaddressed instance**:

- A sweep fires (cron_tick on the hub's declaration) → intake lands observations (TrackWebSources for web sources now; connectors later per D2) → a **standing derive** runs: distill what changed against what the hub already holds → land a brief as `revision_kind="derivation"` + `derived_from=[observations…]`, placed by the settle ladder's deterministic placement (`settle.py:125-163` — the hub folder *is* rung 1), embedded (`_embed_workspace_file` — retrieval), metered on the one ledger.
- Division of labour follows settle exactly: **the model distills, the kernel places** — one bounded invocation, deterministic placement, never overwrites, always cites.
- This also un-moots retention: once derives cite, `cited_paths` populates and the ADR-401 D4 retention polarity fix becomes real rather than theoretical.

The felt unit of the whole app is this brief. If the brief isn't worth opening, nothing else in the app matters (D8 measures exactly this).

### D5 — The composed view is derived, never stored

The hub's dashboard is a **lazy projection over the hub folder** (ADR-333 made real): watches + latest briefs + deltas + sweep health, composed at read time from substrate and ledger, cached content-addressed if needed, **never a stored dashboard state**. DP29 (derived-never-stored) is the line between this and the cockpit: Home died partly because composition drifted into stored state and hardcoded program nouns. The projector reads the folder and the ledger; it authors nothing.

`compose/engine.py`'s dashboard mode (metric-cards, status-matrix, data-table) is the rendering vocabulary; the folder-scoped projector in front of it is new (R2).

### D6 — Drift guards and the narrow ADR-457 amendment

- **Cockpit guard**: hubs are topic-scoped and plural. The moment a single hub composes the whole workspace — or the app grows a workspace-global "overview" — Home has been rebuilt and this ADR violated.
- **Inbox guard**: D2's standing rule (no source-keyed organizing surface).
- **Consumption guard**: accumulation is never the demo. The app leads with briefs (derived, cited, readable), never folder listings or counts. Era-1's failure was accumulation nobody felt.
- **ADR-457 amendment (narrow)**: the five-acts model and the two-layer statement stand unchanged. What amends is the *investment posture only*: the hum's **felt form** joins the desk as the third verb — perceive. This is an amendment, not a reversal: ADR-457's demotion of the Era-1 interop-first identity stays; its D8 falsifiers stay armed; the two-front resourcing guard (chat shallow / Studio deep) widens consciously to admit a third deep app, which is a real resourcing decision this ADR makes explicit rather than drifts into.
- Desk sentence, once the app is real: *Chat thinks, Studio and Images make, Radar watches — two hands and a watchman over a commons that remembers.*

### D7 — Sequencing under the unveil rule (the Images precedent)

ADR-468 D1: **an app unveils only when its distinctive capability works.** A Radar dock icon over a broken chain is the worst possible layman first impression ("the self-running thing that doesn't run"). Order:

- **R0 — the standing derive fires** (D4): the derive seam built; **one topic hub run end-to-end headless as a Hat-B evaluation with receipts** — a declared watch → a scheduled sweep → observations land → a brief lands cited + embedded → the ledger shows the first unaddressed `derivation` in the workspace's history. No surface, no FE. This is the value unlock ADR-401 Phase 3 named.
- **R1 — the watch-authoring path**: the first in-product writer of hub declarations (today zero exist — everything is bundle-shipped). A member declares a hub: topic + sources + cadence. Attributed revision through the one door.
- **R2 — the humble view**: the folder-scoped lazy projection (D5), mounted modestly (a hub-typed folder view reachable from Files) — the felt loop proven before any launcher real estate.
- **R3 — the unveil**: surface row, route, dock icon, `launcher_tier: primary` — only after R0–R2 are real and D8's window has data.

### D8 — Falsifiers, pre-registered before build (the W0 discipline)

Defined now so the baseline exists and null is never misread (an unbuilt verb reads 0; 0 must never be misread as "shipped and ignored"):

1. **Hubs created** — do members declare hubs at all? (R1 instrument: declaration writes per member.)
2. **Briefs opened** — are derived briefs read within N days of landing? If briefs go unopened across the window, the felt unit failed: do not GTM-lead with Radar, and revisit D4's brief shape before the unveil.
3. **Hubs alive at 30d** — declared cadences still firing vs paused/abandoned. Abandonment ≫ creation means the standing promise doesn't hold attention: the app stays at R2.
4. **Sweep→brief yield** — sweeps that produce a brief vs empty sweeps. A chronically empty hub is the dormancy question (DP24 territory), and the aperture answer belongs to the hub's watch set, never to faking output.

Measurement rides the existing instruments: `execution_events` (sweep + derive slugs, one cost ledger), `workspace_file_versions` (`revision_kind`, `derived_from`), and the W0 `session_id`/falsifier read layer.

## 5. What this ADR does NOT decide

- **The final name.** "AI Radar" is the working title; renaming before R3 is a title edit.
- **Capture-lane re-light.** `CONNECTOR_CAPTURE_ENABLED` stays as ADR-404 left it. R0–R2 run on web watches (TrackWebSources), member uploads, MCP arrivals, and the commons itself — all live today. Connectors-as-hub-sources is a follow-on that engages ADR-404 on its own terms.
- **Rooms / multi-member hubs.** A hub is workspace substrate, so it is already shared at the commons level; shared *conversation* about a hub waits on the rooms decision (chat-think discourse, held open).
- **Outward action from a hub.** Anything consequential-external is a separate, gate-crossing decision (D3).
- **Pricing surface.** Standing metered judgment has obvious subscription legibility ("30 briefs this month"); engaging ADR-429 waits for R3.

## 6. Dimensional classification

**Trigger** (primary — the first app whose defining property is standing fire) · **Channel** (a new app + its surfaces) · **Substrate** (observation/derivation accumulation over meaning-folders; the reference-edge graph does the citing) · **Purpose** (the perceive act made felt) · **Mechanism** (sweep = mechanical zero-LLM intake where possible; derive = one bounded judgment invocation) · **Identity** (unchanged — no new agent facts; Researcher posture executes sweeps under the member's grant, attributed).
