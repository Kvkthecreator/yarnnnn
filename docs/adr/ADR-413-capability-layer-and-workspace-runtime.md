# ADR-413: The Capability Layer and the Workspace Runtime

**Status**: Proposed (2026-07-06) — doc-first. Cross-checks the operator's external-discourse document against ratified canon and ratifies the genuinely new decisions; no code rides this ADR (every horizon item is demand-gated to its own ADR).
**Date**: 2026-07-06
**Dimension**: Mechanism (Axiom 5 — which intelligence runs where, and through what adapter) + Channel (Axiom 6 — where the ecosystem is met) + Substrate (Axiom 1 — the runtime the workspace mounts)
**Relates to**: ADR-412 (three chromes — this extends its D4 work-first axis into a full three-axis taxonomy), ADR-411 (lanes — D3 tool surface + D6 conventions doc, here canonized as the *mount*), ADR-408 (D2 altitudes + D4 router — D2 below scopes the router permanently), ADR-402 (steward model policy), ADR-396 (one meter — the constraint every future adapter inherits), ADR-118/130 (render skills — the pre-existing capability adapters), ADR-335 (transports as peripherals/drivers — the same shape, inbound), ADR-222 (kernel/syscall framing — the runtime thesis is its Altitude-2 application)
**Derivation**: [`docs/analysis/ai-native-shell-workbench-capability-platform-2026-07-06.md`](../analysis/ai-native-shell-workbench-capability-platform-2026-07-06.md) (operator-authored, preserved verbatim)

---

## 1. Context — what the discourse document is, and how canon receives it

The operator's document reframes yarnnn as an **AI-native operating
environment**: Freddie as the shell, Chat as the cognitive workbench, the
workspace as the shared substrate everything interfaces into, an explicit
capability layer between intent and provider, and a workspace *runtime*
(mount, not prompt) as the execution contract every reasoning engine enters.

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

**Genuinely new (ratified below as D1–D4):** the three-axis
Work/Capability/Provider taxonomy as *named* canon; LiteLLM's permanent
scope boundary; the runtime/behavior separation and the mount vocabulary;
model-choice-as-product-law with its altitude asymmetry.

**Horizon (named + deferred in D5):** non-language capability adapters,
in-thread multi-capability work, behavioral skill packs, ecosystem
discovery surfaces.

## 2. D1 — Work, Capability, Provider: three axes, never collapsed

ADR-412 D4 ratified *work-first, model-as-metadata* for lane organization.
This ADR extends it to the full taxonomy:

- **Work** — how the member organizes; the enduring identity ("the investor
  deck"). Surfaces sort and name by it. Already the law on the Chat surface.
- **Capability** — the *kind* of act requested (language, images, video,
  audio, code, browser, design, search). Kernel-named, program-neutral,
  stable across provider churn — the ADR-222 rule (kernel names the
  category, never the instance) applied to the Mechanism dimension. The
  render service's skills (ADR-118/130: chart/image/pdf producers behind
  `RuntimeDispatch`) are the pre-existing instances of this layer; the
  perception field's driver-class transports (ADR-335) are its inbound
  mirror. The layer is being *named*, not invented.
- **Provider** — the chosen implementation (Claude, GPT, Gemini, Flux,
  Runway, ElevenLabs…). Explicit, member-chosen where member-facing,
  rendered as metadata (chips, `via ‹provider›` attribution), never the
  organizing namespace (ADR-412 D4, generalized from models to providers).

No abstraction may collapse two of these axes. In particular: a provider
is never a capability ("Midjourney" is not "images"), and a capability is
never an organizing surface ("Images" is not a folder of the member's
work).

## 3. D2 — LiteLLM is the language-capability adapter, permanently

ADR-408 D4 ratified LiteLLM as the router; this ADR fixes its **scope
ceiling**: LiteLLM is the provider adapter *for the language capability
only* — authentication, normalization, streaming, transport. It is not the
platform abstraction, and non-language capabilities are never forced
through an LLM-shaped interface. Each future capability gets its own
adapter seam (images, video, audio, design/MCP, browser), built when its
demand arrives.

Two constraints every future adapter inherits at birth:

1. **One meter** (ADR-396): the adapter reports, `execution_events`
   records; a provider enters an adapter only WITH a rate row — the
   ADR-411 D5 no-silent-default-pricing rule, generalized from models to
   providers. An adapter must never become a second ledger.
2. **Attribution** (ADR-408 D2/ADR-411 D4): capability acts invoked as a
   member's hands attribute as the member's embodiment
   (`member:{id} via {provider}` — the existing form generalizes);
   workspace writes flow through `execute_primitive` under the member's
   grant, same as file verbs.

## 4. D3 — The workspace runtime: mount, don't prompt

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
- **One runtime, N providers**: every language provider receives the same
  mount regardless of destination (the router is transport, D2).

## 5. D4 — Model choice is product law, with an altitude asymmetry

- **Altitude 2 (lanes/workbench)**: provider choice is explicit and
  member-owned. Creation-time selection stands (shipped);
  **recommendations may inform, concealment may not** — no automatic
  routing of a member's lane to a model they didn't choose. Recommendation
  UX (suggested models per kind of work) is a welcome additive layer at
  the creation moment.
- **Altitude 1 (the steward)**: the inverse, deliberately. Freddie's
  engine is a kernel choice (ADR-402: one model, routed-never,
  `steward-never-routes` gate) — the shell is not provider-plural, and no
  picker appears on it. User agency over engines is a *workbench* right,
  not a *shell* right; the asymmetry is the altitude taxonomy doing its
  job.

## 6. D5 — Horizons: named, deferred, demand-gated

1. **Non-language capability adapters** (images, video, audio,
   design/MCP, browser) — each arrives with its own ADR, carrying the D2
   constraints. The render service's existing skills are the seam to
   extend, not bypass.
2. **In-thread multi-capability work** (one lane invoking image/video/
   design acts) — explicitly NOT licensed by this ADR: the lane tool
   surface is exactly the five file verbs (ADR-411 D3, "hands on the
   filesystem, not a seat at the orchestration table"). Widening it is a
   policy change with its own ADR when a capability adapter exists to
   widen toward.
3. **Behavioral skill packs** (architecture.md / copywriting.md-shaped
   behavior extensions for lanes) — the D3 runtime/behavior separation
   reserves their layer; unbuilt.
4. **Ecosystem discovery** (model recommendations, capability
   comparisons, templates, curated starting points) — welcome as
   *creation-moment* affordances first. The ADR-412 D3 guardrail extends:
   yarnnn is an operating environment, not a model marketplace — discovery
   serves starting work, and a standing "browse the ecosystem" surface is
   demand-gated.

## 7. §5 — Honest divergences from the discourse document

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
4. **"A single work thread may include image/video/browser acts"** —
   direction, not current mechanics (D5.2 above); the five-verb lane
   surface stands until a capability adapter and its ADR arrive.
5. **"Freddie should feel infrastructural rather than conversational"** —
   confirmed as chrome posture (ADR-412 D2), with the note that the rail
   *is* an addressed conversation (the OS terminal); infrastructural means
   its placement and singularity, not the absence of dialogue.

## 8. What this ADR does NOT do

- No code, schema, or prompt change (the mount's current text stands; a
  trim/rename pass rides the next time `lane_runner.py` is touched, with
  CHANGELOG discipline).
- No new provider or capability integration.
- No lane tool-surface widening (ADR-411 D3 stands).
- No steward engine change (ADR-402 stands).
- No new stored artifact (the manifest stays a composition — DP29).
- No pricing change (adapters inherit ADR-396; per-seat stays ADR-409).
