# ADR-568 — The capability resolver, and image generation from chat

> **Status**: **Accepted** (2026-08-13, operator-ratified in this session's discourse). Implementation follows in its own commits (§9).
> **Date**: 2026-08-13
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Mechanism** (Axiom 5 — who serves a capability the chat engine cannot). Not Identity: nothing here changes what a chat *is*, who is in it, or which engine holds it.

**Extends** (the pattern, not a new one):
- [ADR-463](ADR-463-capability-not-vendor-the-model-agnostic-carve.md) **D2** — the capability seam. `serve_search` already answers "the agent asks for a capability and the KERNEL decides who serves it." This ADR adds a second capability through the same door; it invents nothing.
- [ADR-450](ADR-450-the-derive-recipe-registry-learn-from.md) — *servers are data; a second one is a row and a function.* Followed literally: one server, one home, one named seam.

**Preserves** (load-bearing, untouched):
- [ADR-558](ADR-558-chat-is-the-engine-surface-agents-are-personified.md) **D1/D4** — chat centers on the ENGINE; `LANE_MODELS` stays the chat-engine chooser and gains no rows for image models. An image engine is not a conversational engine and must never appear at that door.
- [ADR-417](ADR-417-retire-the-render-service-generation-is-rented-not-owned.md) — generation is **rented, not owned**. This ADR rents a second capability; yarnnn still hosts no generation engine.
- [ADR-467](ADR-467-app-residency-and-the-cast.md) **D4** — lane capability is UNIFORM. `GenerateImage` is added for every lane and every Agent, or not at all.
- [ADR-559](ADR-559-the-engine-registry-currency-retirement-availability.md) **D1.a/D3** — standing list price; availability is served with a reason, never hidden.
- [ADR-562](ADR-562-an-apps-ai-configuration-is-declared-where-the-app-lives.md) **D2/D3** — an app's AI configuration is declared in the app's own module.

---

## 1. Context — the question, and the wrong answer I nearly shipped

The session began with an engine addition (xAI grok-4.6, `b762844`) and the operator's follow-on:

> *"do we actually have image-providing engines set-up. if not? maybe that's the next re-shuffling of llm engines we provide."*

The first two answers were both wrong, and recording why is the point of this section.

**Wrong answer #1: "we have no image generation."** False. [`services/apps/images/generate.py`](../../api/services/apps/images/generate.py) has a real rented driver — `GeminiBackend` against `gemini-2.5-flash-image` over direct REST (ADR-076 pattern), behind a per-leaf `GenerationBackend` ABC, selected when `GEMINI_API_KEY` is present. ADR-417 was honored, not violated.

**Wrong answer #2: a modality-typed registry contract across four tables.** The operator asked whether chat, agents, apps and generation should converge on "a singular registry architecture," and the collaborator drafted a shared contract with a `modality` field spanning `LANE_MODELS`, `KERNEL_AGENTS`, `_APP_REGISTRY` and a new `GENERATION_BACKENDS`. The operator then challenged it directly:

> *"my proposal was based on the assumption that image generation was a 'tool' calling from the chat session… if in that case couldn't we still sustain our current architecture? because… a multi-modal chat (say voice in the future, video in the future) may become too complex?"*

The operator was right, and the refutation was already in the codebase. **ADR-463 D2's `serve_search` is the pattern**, and its own docstring states the rule this ADR merely re-applies:

> *"Model-agnostic does not mean vendor-capability-free; it means the agent asks for a capability and the KERNEL decides who serves it."*

A modality taxonomy across four registries is **architecture ahead of evidence** — the exact failure ADR-450 names. The honest scope is one row and one function.

**Cross-vendor was never the hard part.** It already works: `WebSearch`'s docstring records the bug the seam fixed — *"'give Scout web search' silently meant 'make Gemini call Claude'."* A Gemini-driven lane holding an Anthropic-served capability is the shipped, tested state. Grok-on-text reaching a Gemini-served image generator is the same shape, not a new one.

**This is also the conventional approach.** OpenAI's Responses API attaches an image-generation *tool* to a mainline chat model, and "the tool handles GPT Image model selection" — a tool with a resolver behind it. Anthropic resolves server-side tools platform-side. Gemini alone emits image tokens natively, and even there it is a different model id. No major vendor unified its registries by modality; each made the second modality a tool with a resolver. Our `serve_search` seam already matches that convention.

---

## 2. D1 — Generation is a CAPABILITY, resolved by the kernel

A new resolver, `services/capabilities.py::serve_generation`, structurally identical to `serve_search`:

- **One server today: `gemini`.** `_GENERATION_SERVER_DEFAULT = "gemini"`, overridable by the EXISTING `IMAGES_GENERATION_ENGINE` (kept, not renamed — ADR-475's gate pins its stub-forcing behaviour, and inventing `YARNNN_GENERATION_SERVER` beside it would be two names for one fact).
- **An unknown server raises**, and the error names the fix. Copied deliberately from `serve_search`'s reasoning: *"silently falling back to the default would let a deployment believe it had switched vendors while every [call] still went to [the incumbent] — and the bill would say so long after the belief set."*
- **The caller is blind to who served.** The result carries the server's identity for provenance (ADR-468 D4), never the caller's assumption.

**Why a resolver rather than a registry.** ADR-450: servers are data; a second one is a row and a function. There is one image server. Giving it a registry with availability rows, a chooser and a gate would be a table with one occupant — and would invite the ADR-558 error of surfacing it at a door where a member cannot chat with it. When a second server arrives, it is a branch here plus its function, exactly as `serve_search` documents.

**`GenerationBackend` stays.** The ABC in `apps/images/generate.py` is the *driver* contract (per-leaf, `cutout`); `serve_generation` is the *kernel* seam that picks a driver. Same relationship `serve_search` has with `_execute_web_search`.

## 3. D2 — Image generation is priced, and its unavailability is typed

Two defects inherited from the fixed-engine era, both instances of failures this canon already names.

**D2.a — the cost is a guess.** `IMAGES_GENERATION_COST_USD` defaults to `0.08` inside the driver. ADR-559 D1.a made standing list price a rule with a stated rationale; a hardcoded per-image figure sitting outside that rule is the same silent-margin-leak failure one layer down. The figure moves to `services/telemetry.py` beside `_BILLING_RATES` — one home for "what a call costs" — as `_IMAGE_RATES`, keyed by generation model, carrying **standing list price**. The env override is deleted: it is the promo-rate hazard by another name.

**D2.b — the stub is silent.** With no `GEMINI_API_KEY`, `_default_backend()` returns `StubBackend` and generation *succeeds* with a placeholder PNG. Within a test that is correct and stays. In production it is `feedback_gate_pinned_spelling_hides_dead_call`: the operation reports success and the defect only surfaces at the glass. Contrast the care ADR-559 D3 took to make a dark **text** engine legible.

**The rule:** `generation_availability()` returns the ADR-559 D3 `(available, reason)` shape — `no_provider_key` | `unpriced` | `upstream_refused` — and `serve_generation` **refuses** when unavailable rather than substituting a placeholder. `StubBackend` is reachable only by explicit selection (`IMAGES_GENERATION_ENGINE=stub`), which ADR-475's gate already exercises. A member gets a legible refusal; nobody gets a placeholder that composes as though it worked.

## 4. D3 — `GenerateImage` on the lane surface, and the D4.a ceiling

`GenerateImage` joins `LANE_SURFACE_EXTRA`, uniform for every lane and every Agent (ADR-467 D4). This is the decision that delivers the operator's original observation — that on ChatGPT/Claude/Gemini, image generation appears to live inside the one chat.

**It is CONSEQUENTIAL, and the ceiling is amended, not bent.** ADR-467 D4.a asserts `LANE_SURFACE_EXTRA ⊆ READ_ONLY_PRIMITIVES`. `GenerateImage` spends money and lands a revision; adding it to `READ_ONLY_PRIMITIVES` to satisfy a subset check would be defeating a gate to pass it — precisely the "never pin a spelling; assert behaviour" lesson. Instead the ceiling is restated to what it always meant:

> Every name in `LANE_SURFACE_EXTRA` is either in `READ_ONLY_PRIMITIVES` **or** in `LANE_ARTIFACT_VERBS`. A surface name that is in neither is an error.

`GenerateImage` therefore joins `LANE_ARTIFACT_VERBS`, which is already the right place: it is the set whose successful calls land an attributed revision the member should SEE (the artifact card). Nothing about the permission gate changes — consequential primitives gate exactly as before (ADR-307 D1).

**Where the image lands.** `write_revision(content_bytes=…)` — the ONE binary substrate lane (ADR-510), which gives attribution, versioning, and the timeline for free. Path: `uploads/generated/{slug}-{revision}.png`, in Downloads-adjacent territory because it *arrived* from outside (ADR-552's arrival framing) rather than being authored in place. It is a normal file: citable, movable, deletable, and `derived_from` the conversation that produced it.

## 5. D4 — What this ADR explicitly does NOT do

- **No image model enters `LANE_MODELS`.** ADR-558 D1 stands: that door asks which engine holds the conversation, and an image model cannot hold one.
- **No `modality` field, no shared registry contract.** Refused as architecture ahead of evidence (§1). Voice and video, when they come, are a row and a function each — not a redesign.
- **No `vision:` migration.** The flag keeps its meaning (accepts image INPUT) because nothing here changes input handling.
- **No second FE rendering rule.** `GenerateImage` produces a file; the artifact card already renders files.

## 6. Consequences

**Good.** Cross-vendor composition becomes the normal case, not an edge: a member on Grok, Claude or DeepSeek gets image generation served by Gemini without any of those engines knowing. The `$0.08` guess and the silent placeholder both die. Voice/video have a named path.

**Costs, stated honestly.** `LANE_SURFACE_EXTRA` grows by one, which is a real prompt-surface addition under ADR-467 D4's "uniform addition, evidence-gated" rule — the evidence is this ADR's §1. The D4.a ceiling is restated, which means the gate must be *rewritten*, not merely re-run; a restated ceiling that nobody re-derives is how ceilings rot (ADR-323's rule).

**Risk accepted.** A member can now spend money from a chat turn. That is what the permission gate is for, and `GenerateImage` is consequential precisely so the gate sees it.

## 7. Alternatives rejected

| Alternative | Why not |
|---|---|
| Modality-typed contract across four registries | Architecture ahead of evidence (ADR-450). Large upfront cost to serve one modality; the operator's complexity objection was correct. |
| Put image models in `LANE_MODELS` | Re-creates the ADR-558 §1 defect — a door offering an "engine" a member cannot chat with. |
| A `GENERATION_BACKENDS` registry with availability rows + a chooser | A table with one occupant. ADR-450 says row + function until there is a second server. |
| Leave generation app-only (status quo) | Fails the operator's actual question: the ChatGPT-like feel requires chat to reach the capability. |
| Keep the stub fallback in prod | Reports success on a defect; the failure surfaces at the glass. |

## 8. Falsifiers

- A lane whose engine is not Gemini generates an image → cross-vendor composition works. **If it cannot, D1 is wrong.**
- `GEMINI_API_KEY` absent → the member sees a typed refusal, **not** a placeholder. **If a placeholder composes, D2.b is unimplemented.**
- `IMAGES_GENERATION_ENGINE=bogus` → loud raise, no silent stub substitution. **If it silently serves, the resolver copied the shape but not the discipline.**
- Every `LANE_SURFACE_EXTRA` name is read-only **or** an artifact verb. **A name in neither means the restated ceiling is decorative.**
- The generation cost comes from a priced table, not an env var. **An env override surviving means D2.a is unimplemented.**

## 9. Implementation scope

1. `services/capabilities.py` — `serve_generation`, `generation_server()`, `generation_availability()`.
2. `services/telemetry.py` — `_IMAGE_RATES` + `image_generation_cost_usd()`; delete the env-var cost.
3. `services/apps/images/generate.py` — driver reads the priced table; `_default_backend()` no longer silently stubs.
4. `services/primitives/generate_image.py` — the primitive + its schema; registry wiring.
5. `services/lane_runner.py` — `GenerateImage` into `LANE_SURFACE_EXTRA` + `LANE_ARTIFACT_VERBS`.
6. Gates — restate D4.a (`test_agent_registry.py`, `test_adr535`), and a new `test_adr568_capability_resolver.py` carrying §8's falsifiers.

⚠️ `test_adr566_workspace_credential.py:342` pins `LANE_SURFACE_EXTRA == ("QueryKnowledge", "WebSearch", "list_integrations")` by exact tuple. That gate belongs to an in-flight lane; it reads a legitimate addition as a violation (the recorded `feedback_gate_pinned_spelling_hides_dead_call` shape) and must be re-derived, not deleted — **coordinate before editing another lane's gate.**
