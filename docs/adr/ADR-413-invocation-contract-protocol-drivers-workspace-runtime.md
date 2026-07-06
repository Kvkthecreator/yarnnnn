# ADR-413: The Invocation Contract, Protocol Drivers, and the Workspace Runtime

**Status**: Accepted (2026-07-06, operator-ratified — "proceed with implementation regrounded on our framing") — doc-first. **v2 same day**: the operator challenged v1's D2 ("LiteLLM is the language-capability adapter") and, beneath it, capability-as-adapter-boundary; the challenge held under first-principles re-derivation, and D1/D2/D5 are re-cut on the protocol axis (§2 records the derivation; v1's modality cut is preserved there as the rejected alternative). No code rides this ADR (every horizon item is demand-gated to its own ADR).
**Date**: 2026-07-06
**Dimension**: Mechanism (Axiom 5 — which intelligence runs where, and through what driver) + Channel (Axiom 6 — where the ecosystem is met) + Substrate (Axiom 1 — the runtime the workspace mounts)
**Relates to**: ADR-412 (three chromes — work-first organizing extended here), ADR-411 (lanes — D3 tool surface + D6 conventions doc, canonized as the *mount*), ADR-408 (D2 altitudes + D4 router — the router's scope re-derived below), ADR-402/379 (model routing + host profiles as data registries — the catalog generalizes them), ADR-396 (one meter — the constraint every driver inherits), ADR-395/DP34-candidate (model-consumable projection — the inbound half of the invocation contract), ADR-335 (driver-class transports — the same cut, inbound), ADR-118/130 (render skills — the pre-existing async-job driver), ADR-222 (kernel/syscall framing — the runtime thesis is its Altitude-2 application)
**Derivation**: [`docs/analysis/ai-native-shell-workbench-capability-platform-2026-07-06.md`](../analysis/ai-native-shell-workbench-capability-platform-2026-07-06.md) (operator-authored, preserved verbatim)

---

## 1. Context — what the discourse document is, and how canon receives it

The operator's document reframes yarnnn as an **AI-native operating
environment**: Freddie as the shell, Chat as the cognitive workbench, the
workspace as the shared substrate everything interfaces into, a capability
layer between intent and provider, and a workspace *runtime* (mount, not
prompt) as the execution contract every reasoning engine enters.

Cross-checked against canon, the material sorts into three buckets:

**Already ratified (confirmed, no new decision needed):**

| Discourse claim | Canon home |
|---|---|
| Freddie is the shell, infrastructural, operates the environment | ADR-222 (shell) + ADR-381 (steward) + ADR-412 D1/D2 (rail-only chrome) |
| Chat is a dedicated workbench surface; work-first; model as metadata | ADR-412 D3/D4 — **shipped** (§10 steps 1–2, 2026-07-06) |
| The workspace is the center; chats/agents/Freddie/files are interfaces into one substrate | ESSENCE + ADR-310/311 (one moat, two faces) + the ADR-411 contract |
| Explicit model selection at creation | ADR-411 (lane pinned at creation; `LANE_MODELS` whitelist) — shipped mechanism |
| LiteLLM is transport, not context construction | ADR-408 D4 (router reports, the ledger records; yarnnn owns the envelope) |
| Placement teaches ontology | ADR-412 D1 |
| Mount, don't describe; the filesystem teaches; keep it small | ADR-411 D6 — the shipped `_CONVENTIONS_FRAME` is already mount-shaped (~35 lines of environment declaration, composed per turn, never stored) + the ratified removal-over-addition envelope lesson (ADR-390) |

**Genuinely new (ratified below as D1–D4):** the invocation contract as
the kernel-level primitive; protocol classes (not modality) as the driver
boundary; the engine catalog as data; the runtime/behavior separation and
the mount vocabulary; model-choice-as-product-law with its altitude
asymmetry.

**Horizon (named + deferred in D5):** the async-job driver and further
protocol drivers, in-thread multi-protocol work, behavioral skill packs,
ecosystem discovery surfaces.

## 2. The derivation — why the driver boundary is protocol, not modality

v1 of this ADR scoped LiteLLM "to the language capability, permanently"
and made *capability* (language/images/video/audio) the adapter boundary.
The operator's challenge: is modality the right domain separation at all?
Re-derived from first principles, it is not, for two objective reasons:

1. **Modality is a payload property, and it is dissolving at the engine
   level.** Frontier "language" engines natively emit images and audio,
   consume video, and drive computers. A taxonomy that assigns engines to
   modality boxes puts the same engine in four boxes within a year. The
   discourse doc's own principle — *capabilities outlive providers* — is
   true, but it does not follow that capability should be a *code*
   boundary: what the payload means does not determine how you integrate.
2. **The claim was factually wrong about LiteLLM on day one.** LiteLLM is
   not a language library — it ships `image_generation()`, `speech()`,
   `transcription()`, `embedding()`. Its real boundary was never
   "language"; it is a *protocol*: the chat-completions-shaped world.

What actually determines integration shape — the thing domain separation
exists to serve — is the **interaction protocol**, and protocols derive
from physics and economics (latency, statefulness, artifact size,
accounting unit), not from content. There are only about four:

| Protocol class | Shape | Instances today |
|---|---|---|
| **Tool-loop engine** | streamed turns; tool calls back into our surface; token accounting | every chat-completions provider (what the ADR-408 D4 router drives) |
| **Async job** | submit → poll/webhook → artifact | video/image generation, TTS batches — the render service (ADR-118/130) already has this shape in-house |
| **Stateful session** | environment-attached, long-lived | browser automation, computer use |
| **Sync query** | request → structured result | search, embeddings |

This is how operating systems cut device drivers — block vs character vs
network, by I/O discipline, never by content type; the kernel has no
"music driver." Under this cut: a **new modality** (3D, molecules, robot
plans) lands in an existing protocol class with a new payload tag — no new
architecture; a **new interaction physics** (e.g. realtime bidirectional
sessions) earns a new class — which is exactly when new code is honest.
ADR-335 already made this cut for inbound perception (driver-class
transports, transport-blind judgment); this ADR extends the same axiom
outbound.

## 3. D1 — Four layers: contract, drivers, catalog, vocabulary

The durable separation, derived rather than asserted:

1. **The invocation contract** (kernel, invariant, modality-blind). Every
   external engine invocation is: a principal acting under a grant,
   through the ADR-307 gate where consequential; **inputs reach the engine
   only as substrate projections** (the candidate-DP34/ADR-395 axiom —
   this contract is its Mechanism-dimension sibling: projection governs
   what goes in, the contract governs what an invocation *is*); **outputs
   reach durability only as attributed revisions** (`member:{id} via
   {engine}` generalizes the ADR-411 form); **cost lands on the one
   ledger** (ADR-396) with a rate row required before an engine is
   invocable (the ADR-411 D5 rule, generalized). The contract is the same
   for every protocol class, forever — this is what makes the rest data.
2. **Protocol driver classes** (few, physics-derived — §2's table). The
   only code seams. A driver implements one class's mechanics (streaming
   loop / job lifecycle / session management / query) against the
   invocation contract. Provider SDKs and routers are implementation
   details *inside* a driver, swappable without canon change.
3. **The engine catalog** (data, never code). One registry of engine rows:
   protocol class, **payload tags** (what it consumes/emits — modalities
   live HERE, plural per engine, so multimodal convergence is a
   non-event), rate row, hosting/BYOK, recommendation tags. This
   generalizes the registries canon already keeps as data: ADR-402 model
   routing, ADR-379 host profiles, `LANE_MODELS` + `_BILLING_RATES`.
4. **Intent vocabulary** (UX). "I need a hero video" resolves to a catalog
   query plus recommendations. **"Capability" survives here** — the
   operator-facing word for payload/intent metadata, load-bearing for the
   picker and discovery, and *never* an adapter boundary or an organizing
   namespace for the member's work.

The organizing axes of v1 that survive unchanged: **Work** is how members
organize (ADR-412 D4); **Provider/engine** is the explicit, member-chosen
implementation, rendered as metadata. What v1 called the capability layer
splits honestly into layer 3 (payload tags) + layer 4 (intent words).

## 4. D2 — The router is the tool-loop driver; scope follows protocol

ADR-408 D4's router (LiteLLM) is re-scoped **by protocol, not modality**:
it is the driver implementation for the **tool-loop engine class** — every
provider speaking the chat-completions shape rides it, whatever payloads
that provider emits. Where LiteLLM happens to cover adjacent sync-query
endpoints (embeddings) it may be used for convenience *inside* those
drivers; that is an implementation choice, not canon.

The anti-goal that motivated v1 survives, strengthened into a falsifiable
mechanical rule: **never force an async-job or stateful-session engine
through the tool-loop protocol** (no polling loops cosplaying as chat
turns, no sessions serialized into completions). Job-shaped and
session-shaped engines get their own drivers (D5) — the render service is
the in-house precedent for the job driver's shape.

## 5. D3 — The workspace runtime: mount, don't prompt

Ratified principle: **do not prompt a model into believing it has a
workspace; launch it into one.** The prompt is today's compatibility
transport for a runtime declaration; the runtime is the architectural
primitive (the ADR-222 kernel/syscall framing applied at Altitude 2 — the
primitive matrix is the syscall ABI; the lane's five file verbs are its
process's file descriptors).

Concretely, the ADR-411 D6 conventions doc is canonized as the **mount**:

- **The mount is environment declaration, not behavior**: where am I, what
  persists, what are my tools, whose hands am I, what regions exist. The
  shipped `_CONVENTIONS_FRAME` already has this shape and size; this ADR
  ratifies its *discipline* — the mount stays minimal, and growth pressure
  is met by removal-over-addition (the ADR-390 dilution lesson is the
  standing prior).
- **Composed, never stored** (DP29) — unchanged from ADR-411 D6. The
  "Workspace Manifest" of the discourse doc is this composition's
  conceptual name, not a new file.
- **Runtime and behavior are separate systems** — the DP22 partition
  (the persona-frame carries only the model↔runtime interface contract;
  rules of judgment live in substrate) applied at Altitude 2: the mount
  never carries writing style, domain expertise, or reasoning posture.
  Behavior arrives later as skill packs (D5 horizon), layered *after* the
  mount, never inside it.
- **One runtime, N engines**: every tool-loop engine receives the same
  mount regardless of destination (the driver is transport, D2); future
  drivers project the same contract in their class's native shape.

## 6. D4 — Model choice is product law, with an altitude asymmetry

- **Altitude 2 (lanes/workbench)**: engine choice is explicit and
  member-owned. Creation-time selection stands (shipped);
  **recommendations may inform, concealment may not** — no automatic
  routing of a member's lane to an engine they didn't choose.
  Recommendation UX (suggested engines per kind of work, driven by the
  catalog's payload + recommendation tags) is a welcome additive layer at
  the creation moment.
- **Altitude 1 (the steward)**: the inverse, deliberately. Freddie's
  engine is a kernel choice (ADR-402: one model, routed-never,
  `steward-never-routes` gate) — the shell is not provider-plural, and no
  picker appears on it. User agency over engines is a *workbench* right,
  not a *shell* right; the asymmetry is the altitude taxonomy doing its
  job.

## 7. D5 — Horizons: named, deferred, demand-gated

1. **The async-job driver** — the first new protocol driver, when
   image/video/audio generation demand arrives; one driver serves every
   job-shaped engine, extending (not bypassing) the render service's
   existing seam. Each driver arrives with its own ADR, carrying the D1
   contract at birth. The stateful-session driver (browser/computer use)
   follows the same rule, later.
2. **In-thread multi-protocol work** (one lane invoking generation or
   session acts) — explicitly NOT licensed by this ADR: the lane tool
   surface is exactly the five file verbs (ADR-411 D3, "hands on the
   filesystem, not a seat at the orchestration table"). Widening it is a
   policy change with its own ADR when a driver exists to widen toward.
3. **Behavioral skill packs** (architecture.md / copywriting.md-shaped
   behavior extensions for lanes) — the D3 runtime/behavior separation
   reserves their layer; unbuilt.
4. **Ecosystem discovery** (engine recommendations, comparisons,
   templates, curated starting points) — welcome as *creation-moment*
   affordances first, reading the catalog. The ADR-412 D3 guardrail
   extends: yarnnn is an operating environment, not a model marketplace —
   discovery serves starting work, and a standing "browse the ecosystem"
   surface is demand-gated.

## 8. Honest divergences from the discourse document

Recorded so the verbatim base can stand unedited:

1. **"Each conversation operates against the same shared workspace rather
   than owning isolated context"** — right thesis, one nuance kept sharp:
   lane *transcripts* ARE isolated and private (the ADR-411 contract's
   first half; ADR-407 member-experience scope). What is shared is the
   filesystem the lanes work through. The sentence must never be read as
   "lanes share conversational context."
2. **The workspace tree listing "Chats" as a workspace constituent** —
   chats are member-experience scope (`(workspace_id, principal_id)`,
   ADR-407 D6), not workspace content; they are an *interface into* the
   commons, not commons substrate. The tree reads correctly as an
   interface list, not a scope registry.
3. **"The mount should remain extremely small"** — already true in the
   shipped implementation; this ADR ratifies the discipline rather than
   demanding a rebuild. The current mount carries slightly more than the
   addendum's four-line minimum (region taxonomy, attribution + witness
   facts, format discipline) — retained deliberately: those ARE
   environment, not behavior.
4. **"LiteLLM is simply the language-provider adapter"** — the direction
   (LiteLLM must not become the platform abstraction) is confirmed; the
   *cut* is corrected by §2: LiteLLM's boundary is the tool-loop protocol
   class, not the language modality, and capability-as-adapter-boundary is
   replaced by protocol drivers + a data catalog. The discourse doc's
   §9–§10 capability/adapter tables read, post-correction, as the
   *catalog's* content (payload tags + engine rows), not as code
   structure.
5. **"A single work thread may include image/video/browser acts"** —
   direction, not current mechanics (D5.2 above); the five-verb lane
   surface stands until a driver and its ADR arrive.
6. **"Freddie should feel infrastructural rather than conversational"** —
   confirmed as chrome posture (ADR-412 D2), with the note that the rail
   *is* an addressed conversation (the OS terminal); infrastructural means
   its placement and singularity, not the absence of dialogue.

## 9. What this ADR does NOT do

- No code, schema, or prompt change (the mount's current text stands; a
  trim/rename pass rides the next time `lane_runner.py` is touched, with
  CHANGELOG discipline).
- No new engine, driver, or catalog build (the catalog exists today as
  `LANE_MODELS` + `_BILLING_RATES` + ADR-402/379 registries; unifying them
  into one engine catalog is implementation work gated to the first
  non-tool-loop driver's ADR).
- No lane tool-surface widening (ADR-411 D3 stands).
- No steward engine change (ADR-402 stands).
- No new stored artifact (the manifest stays a composition — DP29).
- No pricing change (drivers inherit ADR-396; per-seat stays ADR-409).
