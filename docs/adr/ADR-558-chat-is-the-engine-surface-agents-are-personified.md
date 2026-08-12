# ADR-558 — Chat is the engine surface; Agents are personified

> **Status**: **Accepted** (2026-08-12, operator-ratified in this session's discourse). Implementation follows in its own commits (§8).
> **Date**: 2026-08-12
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Identity** (Axiom 2 — what a chat *is*) + **Mechanism** (Axiom 5 — the engine choice that was hiding inside an identity question). One door was answering two questions.

**Amends**:
- [ADR-460](ADR-460-agents-one-concept-independent-facts-one-gate.md) **D4** — the chooser at the chat door asked *WHO*. It now asks *WHICH ENGINE*. ADR-460's argument is **preserved and re-scoped**, not reverted (§3): "LLM-routing is not a layman concept" was the right answer to *"what should a member configure before their first message?"* — it was applied to the wrong door.
- [ADR-467](ADR-467-app-residency-and-the-cast.md) **D2** — "the open surface has a cast, not a resident" **stands**. What changes is that the cast is no longer chosen at CREATION; it is joined. D1 (apps declare residents) is untouched.

**Preserves** (load-bearing, untouched): [ADR-495](ADR-495-the-conversation-one-object-one-cast.md) (a Conversation is participants + turns; the cast is species-blind — this ADR *depends* on it), [ADR-408](ADR-408-the-coworking-contract-and-the-three-ai-altitudes.md) D2 (a lane is the member's hands), [ADR-411](ADR-411-chat-lanes-and-the-lane-tool-surface.md) D4 (attribution stays `member:{id} via {model}`), [ADR-556](ADR-556-systematic-calls-and-the-model-selection-boundary.md)/[ADR-557](ADR-557-the-router-chokepoint-and-the-transport-product-split.md) (machinery and transport are unaffected — this is the user-facing track).

---

## 1. Context — the genesis, and the drift back to it

The session opened with an operator request: *members should be able to click and select their preferred LLM model*, with the observation that apps (radar, docs, studio) may have "a model bolted on, which I actually disagree with."

The first audit answered by inventory and got the direction wrong (recorded in ADR-556 §1). Two ADRs of upstream hardening later — machinery separated from user-facing selection (556), the transport's flag made a real gate and verified against live providers (557) — the original question came back, and the operator reframed it in a way neither the audit nor ADR-460 had:

> "maybe agents and chat is doing two things at once? current chat is colluding pre-scaffolded agents with pure chat with LLM engines?"

**The screenshot is the evidence.** `NewChatModal` asks *"Who do you want to talk to?"* and lists, as one flat set of answers: **Lisa** (a member-authored persona), **Thinker / Researcher / Designer / Critic** (kernel characters), each labelled with an engine, and **seulkim88@gmail.com** (a human being).

Four different kinds of thing, one question. A member who came to use GPT-5 is handed a persona; a member who wants a colleague is shown an engine label they did not ask for.

## 2. D1 — Chat is centered on engines; the cast is orthogonal

Three acts, previously fused into one modal, now separated by what they actually decide:

| Act | Question | Where |
|---|---|---|
| **Start a chat** | *which ENGINE?* | the chat door |
| **Bring someone in** | *who is in this room?* | the **cast** (CastBar) — humans and/or agents |
| **Configure a persona** | *who is this colleague?* | **`/agents`** |

**Chat is the raw-LLM surface.** Starting a conversation is choosing an engine — sticky last-used per member, with the full engine list one click away. No persona at creation, ever.

**The cast is untouched and remains the answer to "who is here".** This ADR does NOT remove agents from chat. A member may chat with GPT-5, then pull Critic and a teammate into the same thread. ADR-495's species-blind cast is the mechanism, and it already works this way — the responder is resolved from the cast, with `lane_meta["agent"]` as a fallback the code itself calls "the FALLBACK, not the authority".

**This was the operator's own loosening**, and it is the load-bearing correction to the first draft of this decision:

> "the chat full removal can be than loosened in interpretation, wherein the chat IS centered around engines, and you ARE chatting with multiple participants, all that is possible. but centered around chat is engines optionality, agents are personified"

A stricter reading — *agents cannot participate in chat* — was drafted and **rejected**: it would have retired ADR-495's mixed cast and made "work on this with Critic and my teammate" unrepresentable. Centering is not exclusion.

## 3. D2 — Why this is not a reversion of ADR-460

ADR-460 removed a `<select>` of seven engines because *"LLM-routing is simply NOT a laymen intuitive concept. Pre-configured Agents IS."* That reasoning is **correct and preserved** — it is the reason `/agents` exists, and the reason apps pin residents (ADR-467 D1).

What ADR-460 got wrong is narrower: it assumed **one door**. Given one door, hiding the engine behind a name is right. But there were always two intents:

- *"I want to use GPT-5"* — the engine **is** the choice. Answering with a persona is the abstraction getting in the way.
- *"I want a colleague who pressure-tests"* — the engine is an implementation detail. Answering with a model id is the spec sheet.

**ADR-460 solved the collision by collapsing; this ADR solves it by separating.** Both intents are served, each at its own door, and neither is handed the other's abstraction. The spec sheet does not return: `/agents` still asks WHO, apps still pin residents, and a member who never thinks about engines never has to — the sticky default answers for them.

## 4. D3 — Persona-at-creation is deleted; the cast is the single authority

`lane_meta["agent"]` on an **unbound** lane is a creation-time scalar that ADR-495 D3 already retired into the cast. Keeping both is a dual approach, and it has already produced one live bug (recorded verbatim at `routes/lanes.py:788-793`): an Agent added via CastBar after creation never replied, because the cast said yes and `lane_meta` said nobody.

**The rule, one per surface:**

- **Unbound (chat) lanes** — no `agent` at creation. The cast is the only source of who replies. The create endpoint takes an **engine**.
- **Bound (Studio · Docs · IMAGES) lanes and radar** — keep their resident. Apps have one job, so they pin one colleague (ADR-467 D1). Unchanged.

Existing chat lanes carrying a birth-persona are **deleted, not migrated** — the operator confirmed they are test data, and a migration would preserve a shape this ADR removes.

## 5. D4 — Where information lives

The operator's requirement: *"the split between chat and agents now, and where their information is housed should also be much more clearly separated and managed."*

| | Chat | Agents |
|---|---|---|
| Owns | conversations · engines · the cast | personas · characters · engine overrides |
| Kernel data | `LANE_MODELS` | `KERNEL_AGENTS` · `KERNEL_POSTURES` |
| Member data | `chat_sessions` + `conversation_cast` | `_agent.yaml` folders |
| FE | `components/chat-surface/` | `components/agents/` |

**The roster does not belong to chat.** `AgentCard.tsx` currently lives in `components/chat-surface/` while `AgentsSurface.tsx` lives in `components/agents/` — the persona-editing card is housed in the surface this ADR removes personas from. It moves.

## 6. D5 — Engines are shown with their maker's mark

Wherever an engine is surfaced, it carries the provider's brand icon. Precedent exists (`web/lib/ai-providers/brand-icons.tsx`), but it keys on ADR-379 **host-IDs** (`chatgpt`, `claude.ai`, `gemini`) for MCP connectors — so a `provider/model` → brand mapping is required. Small, real, and named here so it is not mistaken for a drop-in.

An engine-first surface should say whose engine it is.

## 7. Consequences

**Good.** The member who wants GPT-5 gets GPT-5. The member who wants a colleague goes to Agents. Mid-conversation becomes two clearly-priced acts instead of one ambiguous one: changing the ENGINE costs a provider/transcript handoff; changing WHO REPLIES is a cast edit that already works. One authority for the responder, so the CastBar bug class cannot recur.

**Cost.** `NewChatModal` is rewritten. `AgentCard` moves. Existing chat lanes are deleted. A member who liked starting a chat with Critic now starts a chat and adds Critic — one more click, deliberately, because it separates two decisions that were never the same one.

**The trade being accepted.** A conversation no longer has a birth-persona. Its identity is the engine it runs on plus whoever is in the room. That is a real conceptual narrowing of what a lane *is* — and it is the one that matches where multi-participant conversations already went (ADR-495).

**Not decided here.** Switching a live lane's ENGINE mid-conversation (the transcript/provider handoff). The mechanism is understood — provider-shaped transcripts cannot be handed across providers without normalization — but it is deferred to its own ADR with its own evidence. Nothing here blocks it; D1's separation is what makes it a single, well-priced question.

---

**One line**: chat asks which engine, the cast asks who is in the room, `/agents` asks who a colleague is — three questions that one modal was answering at once, and separating them serves both the member who wants a raw engine and the member who wants a named colleague without handing either one the other's abstraction.
