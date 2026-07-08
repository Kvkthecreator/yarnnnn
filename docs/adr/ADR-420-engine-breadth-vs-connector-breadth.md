# ADR-420: Engine Breadth vs Connector Breadth — How Capability Returns, Rented

**Status**: Accepted (2026-07-08, operator-ratified) — **doc-first, general principle, demand-gated.** No code rides this ADR; every build item is deferred to its own future commit (the ADR-413/414/417 discipline). This ADR decides *which of the two rented-capability paths yarnnn builds first when demand arrives* (connector breadth, D1) and *what the connector-onto-a-lane surface is* (D2), argues the two deliberate reversals that path requires (ADR-411 D3 + ADR-413 D5.2, D3) honestly rather than slipping them, and — the product half (D5/§10) — settles what yarnnn *sells*: **the commons is the product; engines are table stakes, not a marketplace; recommendation is a thin hint, never a curation service.** Carries the model + connector seed lists and the layman pitch.
> **§10 Amendment (2026-07-08)** — the **engine breadth** half (§10 rule 1: the model seed set) is **IMPLEMENTED** (Gemini Flash/Pro, GPT-5, DeepSeek shipped + streaming; CHANGELOG `2026.07.08.4–.6`). The **connector breadth** half is **PAUSED (demand-gated, operator ruling)**: no demonstrated demand yet, so no connector mechanism is built. The seed list is **corrected** — Higgsfield is **retracted** (it is a *competing commons*, not a dumb peripheral; the moat-leak test in §10's amendment governs). First moat-safe connector when demand arrives = a **dumb search API** (Exa/Tavily), never a smart-workspace platform. See §10 Amendment.
**Date**: 2026-07-08
**Dimension**: Mechanism (Axiom 5 — which intelligence runs where, and *who operates the engine's lifecycle*) + Identity (Axiom 2 — whose grant the capability acts under) + Channel (Axiom 6 — where the ecosystem is met)
**Relates to**: ADR-413 (the invocation contract + protocol drivers — this ADR adds the orthogonal *who-operates-the-driver* axis it did not draw), ADR-417 (generation is rented not owned — this ADR decides *how* rented, and finds the purest form), ADR-411 (the lane tool surface — D3 is the lock this ADR narrowly reverses), ADR-408 D4 (the router — the engine-breadth path for tool-loop engines, already built), ADR-402 (model routing as kernel data — the steward's engine, untouched), ADR-401 (the connection lifecycle — the inbound peripheral, distinguished from the outbound connector here), ADR-373/386 (grants — the boundary a lane's connector reach inherits), ADR-310/311 (the interop face — MCP as a protocol yarnnn already speaks, now pointed outward), ADR-396 (one meter — the metering line the connector boundary respects), ADR-376 (ledger-intake — the provenance-as-data pattern the generated artifact inherits)
**Amends (as ratified direction; the mechanical amendment lands with the build ADR)**: ADR-411 D3 (the lane tool surface is redrawn to *the five file verbs + the member's own attached MCP connectors under the member's grant* — and never yarnnn-authored orchestration primitives), ADR-413 D5.2 (in-thread multi-protocol work is licensed for *exactly one case* — the member-attached MCP connector reached through the outbound MCP client yarnnn already runs, under the member's grant; the async-job-driver widening D5.2 anticipated stays deferred and may never come due)

---

## 1. Context — the forward question ADR-417 deferred

ADR-417 retired the in-house render service on the principle **"generation is rented, not owned."** It killed the deployment and named the forward question but did not answer it: *how does generation — and capability more broadly — return, rented?* This ADR answers it, and generalizes the answer past generation (per the operator's scope ruling: the general "rent all engines" principle, generation as the triggering example).

The strategic frame is ESSENCE v15's Moat: *"the engines are fungible precisely because the memory is not… every new frontier engine deepens the commons it works through while remaining swappable."* The invocation contract (ADR-413: projection in → attributed revision out → one ledger) is the moat's mechanism. **Both rented-capability paths below enter through that one contract** — which is exactly why they are data-shaped, not architecture-shaped, and why adding either does not touch the moat.

## 2. The axis ADR-413 did not draw

ADR-413 gave us the **protocol driver** axis — *how* you integrate an engine (tool-loop / async-job / stateful-session / sync-query, physics-derived, content-blind). It is the right cut for the driver seam. But it is silent on a second, orthogonal question this discourse is about: **who operates the driver, and who owns the engine's lifecycle — yarnnn, or the member?**

Two engines can share a protocol class yet sit on opposite sides of this axis. The sharpened cut (the operator's, refining the §10 provider-adapter sketch in the ADR-413 derivation doc, where Higgsfield and Seedance were mistakenly the *same video slot at two granularities*):

| | **Engine breadth** (yarnnn-operated) | **Connector breadth** (member-operated) |
|---|---|---|
| What it is | A raw engine yarnnn adds behind a protocol driver | A platform the member attaches over MCP, reachable *onto a lane* |
| Who owns the lifecycle | **yarnnn** — rate rows, provider SDK, BYOK keys, deprecation churn | **the member + the platform** — the async-job/session physics lives *behind the MCP boundary*; yarnnn builds no driver |
| Where it lives | `LANE_MODELS` / the ADR-413 engine catalog / a protocol driver | a grant + a tool the lane composes at turn time; **zero yarnnn engine code** |
| Triggering example | BytePlus Seedance (a raw video engine) | Higgsfield (`higgsfield.ai/mcp` — generation behind MCP) |
| Cost of adding one | honest new code (or a catalog row, if the driver already exists) | a connector attach + a grant — the platform runs the physics |

The load-bearing distinction: **you cannot "connect onto" Gemini — Gemini *is* the lane** (a tool-loop engine yarnnn drives directly). You *can* connect onto Higgsfield, because Higgsfield is a platform on the far side of an MCP boundary that brings its *own* async-job driver. Seedance and Higgsfield are therefore **two sides of this axis, not one slot at two granularities.** Naming the axis is this ADR's first act; the §10 sketch's modality-adapter framing is superseded by ADR-413's protocol drivers *plus* this ADR's operator axis.

## 3. D1 — Connector breadth is the default; engine breadth is the reserved fallback

**The purest form of "rented" (ADR-417) is not *yarnnn rents the engine and resells it through a driver it maintains* (engine breadth) — it is *the member rents the engine directly and yarnnn never touches the async-job driver at all* (connector breadth).** Connector breadth pushes the *entire* generation-engine lifecycle across the connector boundary: no rate rows for it, no provider SDK, no deprecation churn, and — decisively for a solo founder — **yarnnn never builds an async-job driver.** ADR-413 D5.1 reserved that driver as "the first new protocol driver, when generation demand arrives"; connector breadth makes that reservation potentially **never come due.**

Therefore the ratified default inverts the instinct of the §10 provider-adapter table:

- **Connector-first.** When a member wants a generative (or browser/search/design) capability, the default path is: the member attaches the platform's MCP connector (under their own account/key), and the lane composes it. yarnnn integrates *nothing engine-specific*.
- **Engine breadth only when forced**, gated behind connector breadth failing, in exactly two cases:
  - **(a) No connector exists** for a proven-demand engine, *and* the demand justifies yarnnn owning its async-job (or session) driver. This is ADR-413 D5.1's reserved driver, unchanged — it arrives with its own ADR carrying the D1 invocation contract at birth.
  - **(b) It is a tool-loop chat/reasoning engine a member wants to pin as a lane** — where "connect onto" is meaningless (you can't connect onto Gemini; Gemini is the lane). This is the *existing* `LANE_MODELS`/router path (ADR-408 D4 / ADR-411), already built. Adding a new chat engine here is a catalog row, not new architecture.

Case (b) is not new territory; case (a) is demand-gated and reserved. So the only genuinely-new path this ADR opens is **connector breadth**, and §4–§6 specify it.

## 4. D2 — The connector-onto-a-lane surface (what it is, unbuilt)

The concrete deliverable, specified now, built on demand. It leans entirely on machinery canon already has — this is why it is cheap:

1. **The member attaches an MCP connector.** yarnnn already speaks MCP both ways: as a *server* (the interop face, ADR-310/311 — external LLMs connect *into* yarnnn) **and as a *client*** — the in-kernel `MCPClient` (`api/integrations/core/mcp_client.py`, ADR-335 Crawl-B) already connects *out* to external MCP servers. Today that outbound client is deliberately confined to **mechanical standing-watches** (`TrackForeign` / `foreign_read.py` — a bounded, deterministic read, "never a foreign tool injected into a judgment tool loop"). Connector breadth does not build a new client; it **composes the existing outbound transport into the lane loop** — pointing a client yarnnn already runs at the member's attached platform (Higgsfield, etc.), authorized under the member's own credentials/key with that platform.
2. **The attached connector is bound to the member, not the workspace.** It is member-experience scope (ADR-407 `(workspace_id, principal_id)`), like a lane itself — the member's own tool, reachable from the member's own lanes. It is **not** a `platform_connections` OAuth *capability* binding (`watch_id = NULL` — the Slack/Notion perception intake, `system:`-attributed, ADR-401's peripheral, the operation's *senses*) and **not** a `foreign-llm` `principal_grant` (ADR-386 — an external LLM writing the commons as a principal). The nearest existing shape is the `platform_connections` **watch binding** (`watch_id`-set + `attestation_grade`, migration 186) that `TrackForeign` already uses for outbound MCP servers — but *that* one is steward-side and mechanical. This is a **third use of it**: a *member-owned, lane-reachable outbound capability*. Naming it distinctly is load-bearing (ADR-401 D1's peripheral-not-principal discipline extends: this connector is neither perception nor principal — it is the member's reach, extended).
3. **The lane composes it at turn time.** A lane's tool surface (ADR-411 D3, the five file verbs) gains the member's attached MCP connectors, composed into the tool list alongside the file verbs when the turn is built — never stored, DP29. The lane model can then call Higgsfield the way it calls WriteFile: through the tool loop.
4. **The generated artifact lands in the commons as an attributed revision.** The lane takes the connector's result (a video URL, an image) and writes it to a workspace file through WriteFile — attributed `member:{id} via {model}` (ADR-411 D4), with the generating platform recorded as provenance-data on the revision (the ADR-376 ledger-intake pattern: *the source is data, carried in revision metadata, not in the author field*). The moat is untouched: **nothing reaches durability except as an attributed revision through the one invocation contract.**

## 5. D3 — The two reversals, argued (not slipped)

Connector breadth reverses two deliberate locks. This ADR's job is to argue them; both reversals are **narrow and principled**, not a loosening.

### 5a. ADR-411 D3 — the lane's five-verb lock

ADR-411 D3 locked the lane surface to *exactly five file verbs* — "hands on the filesystem, not a seat at the orchestration table." Reaching a member-attached MCP connector is a sixth kind of tool. The reversal is safe because the lock's *purpose* is preserved:

- The five-verb lock forbade giving a generic model a **seat at the orchestration table** — Schedule, DispatchSpecialist, platform *sends*, entity verbs. Those are yarnnn-authored orchestration primitives that would let a helper *drive the operation.*
- A member-attached MCP connector is categorically different: it is **the member's own authorized capability, reached under the member's own grant.** ADR-411 D4 already ratified the governing principle — *"the lane's reach is exactly the member's reach."* A member who has attached Higgsfield to their own account **can already invoke it**; letting their lane reach it grants the lane *no authority the member lacks* — it lets the member's hands use a tool the member owns. The lane gains reach, never orchestration authority.

The redrawn line (amending ADR-411 D3): **the lane tool surface is the five file verbs + the member's own attached MCP connectors under the member's grant — and never yarnnn-authored orchestration primitives.** Schedule/DispatchSpecialist/platform-send/entity verbs stay off the lane, exactly as before.

### 5b. ADR-413 D5.2 — in-thread multi-protocol work

ADR-413 D5.2 said in-thread multi-protocol work is NOT licensed — *"widening [the five-verb surface] is a policy change with its own ADR when a driver exists to widen toward."* This ADR is that ADR, and it satisfies D5.2's own condition in the strongest possible way:

- **The driver exists — on the platform's side of the MCP boundary, not in yarnnn.** yarnnn is not widening toward an async-job driver *it built*; it is widening toward the member's *own attached tool*, reached through **MCP, a transport yarnnn already runs a client for** (`mcp_client.py`, ADR-335). A member-attached MCP connector is not a new driver *class* to build — it is the existing outbound MCP client, today walled off from every tool loop, composed into the lane loop under the member's grant.
- This is why connector breadth is *more* "buy not build" than the async-job driver D5.2 anticipated ever was: D5.2 imagined yarnnn eventually building the driver; connector breadth means **yarnnn never builds it** — and the transport is already in the repo. The widening D5.2 guarded against (yarnnn owning multi-protocol *execution* machinery) does not happen — the platform owns the async-job physics; yarnnn owns only the tool-loop round that calls it.

The licensed widening is therefore **exactly one case**: the member-attached MCP connector, reached through the already-spoken MCP transport, under the member's grant. The general async-job-driver widening (engine breadth case (a), D1) stays deferred and, if connector breadth suffices, never comes due.

## 6. D4 — Metering and attribution across the connector boundary

Stated explicitly, because the boundary is where the accounting could go wrong:

- **Generation cost lands on the platform's side / the member's key — yarnnn does not meter it.** When a lane invokes Higgsfield-over-MCP, the generation dollars are billed by Higgsfield to the member's Higgsfield account (or their BYOK). yarnnn *cannot* meter that spend, and *should not* — ADR-396's one meter is yarnnn's own LLM judgment invocations, not the connector's compute.
- **yarnnn meters only its own lane rounds.** This is already ADR-411 D5 — each lane round is one metered judgment invocation on the one ledger (`execution_events`, slug `lane`, `principal_id` = the member). The connector call is a **tool result flowing back into a round**; the round is metered (the lane model reasoned and decided to call the connector), the connector's own async-job compute is not. This is **clean, not a hole**: it is exactly the ADR-396 carve already in force — yarnnn meters LLM judgment; a connector's compute is the platform's business, off yarnnn's ledger *by design*, the same way mechanical perception sync is $0.
- **Attribution stays honest.** The durable artifact enters as a `member:{id} via {model}` revision (ADR-411 D4). The generating platform rides as provenance-data on that revision (ADR-376 — *the source is data*), so `trace` can show *this artifact was generated via Higgsfield, written by member X's Claude lane* — which is precisely the attribution wedge the moat sells, extended cleanly across the connector boundary.

## 7. Honest divergences and open seams

Recorded so the argument stands without over-claiming:

1. **The outbound MCP client already exists — the new code is the composition, not the client.** Contrary to a natural assumption, yarnnn is *not* only an MCP server: `mcp_client.py` (ADR-335 Crawl-B) already connects out, and `platform_connections` already carries an outbound MCP watch binding (`watch_id`-set, migration 186). But both are **deliberately walled off from every LLM tool loop** — the outbound path is a mechanical, deterministic standing-watch read, kept out of the steward's and the lane's tool surfaces by design (`track_foreign.py`: "not in CHAT/HEADLESS/FREDDIE primitives"). Connector breadth's real new code is therefore narrower and more precisely a *policy reversal*: **composing that existing transport into the lane loop under the member's grant, and un-walling the lane surface to reach it** (the §5a/§5b reversals). One client for all connectors (MCP is uniform); the machinery mostly exists; the decision is whether a lane may reach it.
2. **The member-attach/authorization surface** (how a member attaches an outbound MCP connector *for interactive lane use*, stores the credential/key, and manages it) is unspecified here beyond "member-experience scope, member-owned." Today `watch_id` bindings are set only steward-side by a validation script — there is no member-facing attach route. It reuses the connection + grant shape (ADR-373/386/401) conceptually but is a distinct third use (§4.2); its own surface is design work for the build ADR.
3. **BYOK for connectors** rides the same tier lever as lane BYOK (ADR-409, demand-gated) — the member's key with the platform is the connector's cost basis; yarnnn's tiering governs *lane rounds*, not connector spend.
4. **Discovery** (helping members find which connector serves "I need a hero video") is the ADR-413 D5.4 / intent-vocabulary layer — a creation-moment affordance reading the catalog, not a standing marketplace (the ADR-412 D3 guardrail: yarnnn is an operating environment, not a model marketplace).
5. **Engine breadth case (a)** — yarnnn owning a raw async-job/session driver — is not killed, only demoted to the fallback and demand-gated behind connector breadth. If a proven-demand engine has no MCP connector, D1(a) + ADR-413 D5.1 govern its arrival.

## 8. What this ADR does NOT do

- **No code, schema, migration, or flag.** Doc-first; connector breadth's build (the outbound MCP client, the attach surface, the lane composition) is gated to its own ADR-when-demand.
- **Does not compose the outbound MCP client into the lane loop** (§7.1 — the client already exists and is walled off from tool loops; un-walling it under the member's grant is the build, deferred to its ADR).
- **Does not widen the lane surface to yarnnn-authored orchestration primitives** (§5a — Schedule/DispatchSpecialist/platform-send/entity verbs stay off; only *the member's own attached MCP connectors* are added).
- **Does not touch the steward** (ADR-402 — Freddie is Anthropic-only, no generation, no connectors; connector breadth is an Altitude-2 lane capability, member-owned).
- **Does not meter connector compute** (§6 — yarnnn meters lane rounds only; the ADR-396 one-meter invariant is *tightened*, not stretched).
- **Does not revive the render service or any in-house generation engine** (ADR-417 stands; engine breadth case (a) is a driver over a *rented* engine, still not an owned engine).
- **Does not decide the connector attach/authorization UX** (§7.2 — build-ADR scope).
- **Does not add a new principal kind, altitude, or autonomy dial** (the connector is the member's reach extended, not a principal — §4.2).

## 9. Sequencing (when demand arrives)

1. **Connector breadth first** (D1). The build ADR specifies: the member-facing attach/authorization surface (the third use, §4.2), the lane-turn tool composition (member's connectors + five file verbs) that un-walls the *existing* outbound MCP client (`mcp_client.py`) under the member's grant, and the §5a/§5b surface reversal. It carries the invocation contract at birth (ADR-413 D1) and the §6 metering line.
2. **Engine breadth (case a) only if a proven-demand engine has no connector** — ADR-413 D5.1's async-job driver, its own ADR.
3. **Discovery affordances** (§7.4) ride the connector-breadth build as creation-moment recommendations, reading the ADR-413 catalog — never a standing marketplace.
4. **Doc cascade** (with the first build commit): ESSENCE §The Moat gains the connector-boundary line (engines fungible includes member-attached connectors); the ADR-413 catalog gains the operator-axis note (engine rows carry an operated-by tag); GLOSSARY gains "engine breadth / connector breadth" + "outbound MCP connector" entries.

## 10. D5 — Product posture: the commons is the product; engines are table stakes, not a marketplace

The architecture (§2–§9) forces a product decision the operator raised (2026-07-08): *with a growing set of models and connectors, is yarnnn selling "the most engines," or "which engine to use," as a service?* **Ratified: neither.** Both framings make yarnnn a **model marketplace** — and the marketplace is a red ocean (OpenRouter owns "the most"; every router startup and listicle owns "which one") and, worse, it is **off-moat**: it stakes the brand on engine breadth, the single most fungible layer in the stack (ESSENCE §The Moat: *engines commoditize on a quarterly cycle*). The guardrail already exists (ADR-412 D3: *yarnnn is an operating environment, not a model marketplace*); this decision makes it strategy, not just chrome.

**The product is the commons — the attributed, accumulating, owned workspace.** Engines and connectors are **table stakes that remove an objection** ("but I like Gemini for X"), never the value sold. The posture in three rules:

1. **Provide *enough*, not *the most*.** The engine bar is *"does its absence lose a user?"* — not *"is it good?"* Because adding a tool-loop engine is near-free (`LANE_MODELS` row + `_BILLING_RATES` row + provider key — the ADR-402 data pattern), this is a low-stakes, reversible set, not a bet. The seed set (build-time, demand-orderable):
   - **Google Gemini (Flash + Pro)** — the one frontier lab with zero representation today; the highest-leverage single add (answers "I use Gemini," an objection currently unanswerable).
   - **A frontier OpenAI model** (GPT-4o full / GPT-5-class) — today only the cheap `gpt-4o-mini` exists; completing mini→full closes the "toy OpenAI" gap.
   - **One open-weights / cost-floor lane** (DeepSeek / Llama-class endpoint) — the differentiated "cheap / sovereign / on-prem-adjacent" lane ADR-408 D6 imagined; says yarnnn isn't locked to the expensive US labs.
   
   Roughly **6 total lanes across the four frontier sources + a floor** — one lane per *reason a user would leave*, not one per model that exists. Past this, **BYOK (ADR-409) is the pressure valve**: the member brings their own key rather than yarnnn maintaining the row, so engine breadth stays small forever and connector breadth + BYOK absorb the long tail.

2. **Connectors are member-owned capability, not a curated store.** yarnnn ships the *attach mechanism* (§4) + **2–3 known-good starting points**, never a catalog. The seed seams (both, order at build time per the operator's ruling): **media generation** (Higgsfield covers image + video over one MCP — the clearest post-ADR-417 "buy not build" win) and **live-web / search** (a browser-automation or search MCP — arguably higher daily-work leverage for the trader/author users than a hero video, and it exercises the ADR-413 stateful-session + sync-query classes). Everything past the 2–3 seeds is the member attaching their own MCP, uncurated.

3. **Recommendation is a thin creation-moment hint, never a maintained service.** A light suggestion at the create-a-lane / reach-for-generation moment ("most people pin Flux for images") reading the ADR-413 catalog is welcome UX (ADR-413 D5.4). yarnnn does **not** maintain rankings, comparisons, or a "best model per task" curation product — that is the router-startup treadmill (models leapfrog monthly; a curation brand rots at churn speed) and it is someone else's business. **Recommendation is polish; the commons is the product.**

**The layman pitch that falls out of this** (the operator's "how do we explain it" question): the models/connectors are the invisible *how*; the owned accumulating commons is the *what*.

> *"yarnnn is one workspace where your work with AI piles up instead of disappearing. Use Claude, Gemini, GPT, image tools — whatever's best; they all write into the same place, and it remembers who did what. You own it, you can see how it changed, and you can take it with you."*

None of those sentences claims "the most models" or "we tell you which to use." The engine plurality is framed as **"it works with your favorite tool, so you never choose us *over* it"** — which protects the portability + accountability wedges rather than diluting them into a store.

### §10 Amendment (2026-07-08) — the moat-leak test + the demand-gate, before any connector builds

Re-examination of the §10 rule-2 connector seeds surfaced a distinction the original text missed, and it corrects the seed list. **Higgsfield is retracted as a seed.**

**The smart-workspace-vs-dumb-peripheral test.** §2 modeled a connector as a *dumb capability* on the far side of MCP (prompt in → artifact out, stores nothing about the user). But some "connectors" are not dumb capabilities — they are **competing commons**: platforms that are themselves versioned, searchable, collaborative asset stores, exposing a slice over MCP as their *own* distribution face (exactly yarnnn's interop-face move, ADR-310/311). **Higgsfield is one** — its own product copy is "a unified workspace… searchable, versioned assets… shared team workspaces… every generation and version accessible without exporting," plus an LLM "orchestration layer." When a lane calls such a platform, the *interesting* artifact — the versioned asset, the project, the prompt history — **accumulates on the platform's side; yarnnn gets back a URL.** For a product whose entire moat is *"the memory is not fungible,"* routing work through a competing memory leaks the moat in the wrong direction: the user's accumulation lands in the competitor's tank, not the commons.

The test, now the governing rule for any connector seed: **"Does the connector accumulate the user's work on its own side?"**
- **Yes → a competing commons.** Do NOT seed it. Connecting it pipes accumulation out of the commons (Higgsfield, Figma, Notion-as-workspace, Runway-with-projects). If ever connected, it must be a deliberate, eyes-open decision to be a client of a competitor — not a default.
- **No → a true peripheral.** Safe to seed. It computes and returns; the result lands in *yarnnn's* files, attributed — accumulation stays in the right commons. Raw search (Exa/Tavily/Brave — sync-query, stores nothing about you), raw image/async endpoints (Flux/Replicate *direct API*, not the workspace product), raw transcription.

**Corrected seed list**: the first moat-safe connector is a **dumb search API** (Exa/Tavily/Brave — sync-query, fits the lane tool loop exactly like `SearchFiles`, highest daily-work value for trader/author users). Raw media (Flux/Replicate *direct*, not Higgsfield) is a candidate second. **Higgsfield/media-workspaces are excluded** by the test above.

**The demand-gate holds — connectors are PAUSED (operator ruling 2026-07-08).** ADR-420 is doc-first/demand-gated by construction, and there is no demonstrated demand yet (lanes + the ADR-420 §10 models + streaming shipped 2026-07-08; no user has hit "I wish my lane could reach X"). Building connector infrastructure now is supply ahead of demand. **The connector mechanism (ADR-424+) is not built until real demand names the first capability** — and when it does, the moat-leak test picks the seed, never flashiness. The protocol-fit note stands as secondary: a sync-query search connector slots into the lane loop unchanged, an async-job media connector fights the synchronous loop (ADR-413 D4) and waits for its own driver discourse.
