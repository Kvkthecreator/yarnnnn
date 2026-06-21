# ADR-351 — In-flight invocation rendering: the operator watches the Reviewer reason, not a loading blob

**Status:** **Accepted (2026-06-21)** — **Phase 1 (backend streaming) Implemented**; Phase 2 (frontend in-flight render) + Phase 3 (reactive/scheduled streaming, deferred) Proposed. Phase 1 gate `api/test_adr351_streaming_tools.py` (8/8); sibling gates ADR-291/247/289/276/303 green (59/59). Phase 2 gate `web/test/adr351-inflight-render.test.ts` to author. Closes the ADR-260 §D6 spec/implementation divergence (the streaming half was specified, never built — see §1).

> **Phase 1 implementation note (2026-06-21):** `services/anthropic.py::chat_completion_with_tools_stream` (tool-aware streaming, returns the identical `ChatResponse`); `agents/reviewer_agent.py` addressed path routes to it and emits `text_delta` via the existing `event_callback`; `services/wake.py::stream_addressed_wake` relays `text_delta` as a distinct SSE type; `routes/feed.py` forwards it to the HTTP client. The terminal `reviewer_response` SSE event is now a persist+finalize, not the first appearance of the reasoning text. **Phase 2 is the FE render** (live-appending Reviewer bubble on first `text_delta`, the three-state thinking/streaming/settled grammar of D3, and deleting the `NarrativeContext.tsx:848-866` tool-name label map of D4) — the SSE carries the deltas today; the FE does not yet append them to a live bubble. Until Phase 2, the operator-visible behavior is unchanged (the FE still renders on `reviewer_response`); Phase 1 is the substrate that makes the live render possible.
**Date:** 2026-06-21
**Deciders:** KVK (operator) + Claude (collaborator)
**Hat:** A (system canon)

> **Discourse base:** the operator ran a sample addressed turn ("Can you put in a trade order, I want one even as a test") and disliked the in-flight experience — *"I didn't like the loading, streaming implications that seem to just summarize as reading substrate."* Three complaints, confirmed against the wire: (1) the in-flight state is opaque/generic, (2) the answer arrives all-at-once / late, (3) no boundary between thinking / streaming / settled. The screenshot's *answer* was good (a deliberated current-state + two-options reasoning block); the *experience of waiting for it* was a single relabeled spinner, then a block that popped in whole.

**Supersedes-by-fulfillment:** ADR-260 §D6 (the six-phase real-time-handoff spec — its render grammar is correct and preserved; this ADR makes the **streaming substrate** that §D6 assumed actually exist, and corrects the two commitments §D6 claimed were shipped but the audit found unbuilt: §D6.1 intent-narration-before-action and the Reviewer-reasoning stream).
**Extends:** ADR-289 (feed vs conversation render grammars — adds the *in-flight* lifecycle the settled-row grammar never specified), ADR-318 (the wake is a multi-phase situation: perceive → reason forward → decide → act — this ADR renders that shape), ADR-296 (wake architecture — addressed is the SSE-streamed wake source).
**Bounded by:** ADR-338 / DP28 (the consent line — render the *shape* of judgment, never raw mechanism: "Reviewer is checking whether any signal is firing" is legal; `ReadFile(path=…)` / tool JSON / Haiku tier-2 eval calls are below the line and stay invisible), ADR-306/323 (persona-frame ceiling — intent-narration is persona-authored at runtime, not new frame prose).
**Folds in:** ADR-350 (the Standing band) as the **settled-state sibling** of this in-flight work — §7. ADR-350 renders the operation's standing obligation *at rest*; this ADR renders a single cycle *in flight*. One invocation-rendering canon, two registers.

---

## 1. The finding — ADR-260 §D6 specified this; the implementation never delivered the streaming half

The audit traced one addressed turn end-to-end. The verdict is a **spec/implementation divergence**, not a missing design. ADR-260 §D6 already canonized the experience the operator is asking for — six legible phases, "the operator sees every handoff, there are no hidden steps," persona-narration of intent *before* each action. The code does not deliver it:

| ADR-260 §D6 specifies | What the code does | Receipt |
|---|---|---|
| §D6.1 — Reviewer **narrates intent before each action** ("Checking signal state… Reading workspace state now…") | The Reviewer's LLM call is **blocking** (`client.messages.create()`, not `.stream()`). Nothing narrates until the cycle ends. §D6.1's "already in the prompt" claim was never reachable — there is no pre-action emit point. | `anthropic.py:257`; `reviewer_agent.py:1161` |
| The Reviewer's **reasoning streams** (the §D6 worked example shows it building turn by turn) | Entire reasoning arrives in **one atomic `reviewer_response` event** at cycle-end. No token deltas for the Reviewer path. | `wake.py:1735-1742` |
| §D6.3 — transient cognition status, **specific** ("Reviewer is reading signals/ih-3.yaml…") | Generic tool-name → frontend-invented **"Reviewer is reading substrate…"** copy from a tool-name map. This is the literal "summarizes as reading substrate" the operator disliked. | `NarrativeContext.tsx:848-849` |
| §D6.5 — Reviewer's read-back is a **bubble** that fills in | **No streaming placeholder** for the Reviewer. The bubble appears only *after* `reviewer_response`, then `fetchAndSetHistory()` reloads from DB and it pops in whole. | `NarrativeContext.tsx:668, 868-874` |

The three operator complaints map exactly onto the divergence:
1. **Opaque/generic** → the only in-flight signal is one relabeled spinner, because reasoning doesn't stream and tool-calls surface only as *completed* events, never as *intended* ones.
2. **All-at-once / late** → the LLM call literally blocks; the whole deliberation generates, then drops in one event. Nothing builds because nothing streams.
3. **No thinking/streaming/settled boundary** → there's a thinking spinner and a settled card, but **no streaming state between them** for the Reviewer (the System Agent path *has* one — `stream_start` + text deltas; the Reviewer path skips `stream_start` entirely, `NarrativeContext.tsx:667-668`).

**Why the divergence existed:** `chat_completion_stream` (`anthropic.py:261`) is **tool-less**. The Reviewer loop needs tools, so it took the blocking `chat_completion_with_tools` (`:257`). No one wrote a *tool-aware* streaming variant, so §D6's streaming spec had no substrate to render. ADR-260 §D6 is correct as a render grammar; it just assumed a stream that was never plumbed.

## 2. The principle — an invocation is an operation the operator watches, not a message that arrives

Canon already holds the frame (invocation-and-narrative.md §1: "one cycle of the six dimensions"; ADR-318: "a wake is a situation, not a task"). A Reviewer cycle is a **perceive → reason → decide → act** traversal. The operator should *watch that traversal happen*, in the Reviewer's own voice, bounded by the consent line — not stare at a spinner and receive a finished essay.

The fidelity target (operator's "full" choice): **the reasoning streams token-by-token, AND the Reviewer narrates its intent between tool rounds in persona voice.** Both halves, because each fixes a different complaint — streaming fixes "all-at-once/late," intent-narration fixes "opaque/generic."

## 3. Decision

### D1 — A tool-aware streaming LLM call (the crux backend change)

Add `chat_completion_with_tools_stream(...)` to `anthropic.py` — `client.messages.stream(...)` *with* `tools=` — yielding a typed event stream: `text_delta` (reasoning tokens as they generate), `tool_use_start` (the model committed to a tool, with name + the persona's narrated intent for it), `tool_use_complete`, `message_stop` (with `stop_reason` + usage). `invoke_reviewer` (`reviewer_agent.py`) switches the addressed path from the blocking `chat_completion_with_tools` to this streaming variant. **The blocking call is deleted from the addressed path** (Singular Implementation — no dual call sites; the reactive/scheduled non-SSE paths keep blocking until a later phase, see §6). The round loop, bound (ADR-260 §D8: addressed ≤ 12 rounds), and `ReturnVerdict` close are unchanged — only the per-round call streams.

### D2 — Intent-narration is persona-authored, emitted before the action (fulfills §D6.1)

Per round, *before* a tool executes, the Reviewer's streamed reasoning preceding the `tool_use` block **is** the intent-narration ("Let me check whether any signal is firing before I can size this"). The stream surfaces it as a persona bubble that *builds* as tokens arrive, then the tool runs. This is the §D6.1 commitment finally made real: the narration is the Reviewer's own first-person reasoning streaming out, not a frontend tool-name map. **No new frame prose** (ADR-306/323 ceiling preserved) — the persona already reasons aloud; we stop swallowing it until cycle-end.

### D3 — Three legible in-flight states, consent-line-bounded (fixes complaint 3)

The frontend renders exactly three states, with visible boundaries:

- **Thinking** — between send and first token. A brief, honest "Reviewer is considering…" (not a phase claim it can't yet make).
- **Streaming** — the persona bubble fills token-by-token (reasoning) interleaved with **transient cognition status** for the *current* read, specific to what's being perceived but **named as judgment, not mechanism** (ADR-338 DP28): "Checking the signal conditions" — *not* "Reading signals/ih-3.yaml," *never* the tool JSON. The transient status replaces itself per cognition step (§D6.3) and does not persist as a feed row.
- **Settled** — `ReturnVerdict` fired; the bubble stops growing, the cognition status clears, the action chips (proposal / clarify / schedule) render. The boundary is explicit: a settled cycle looks different from a streaming one (no caret, no transient status, action affordances present).

### D4 — Kill the "reading substrate" tool-name map (Singular Implementation)

`NarrativeContext.tsx:848-866`'s frontend-invented tool→label map ("Reviewer is reading substrate…" etc.) is **deleted**. It was a stand-in for narration that now arrives from the persona itself (D2). The frontend renders what the Reviewer *says* it's doing; it stops guessing from tool names. This removes the exact copy the operator named.

### D5 — Below-the-line mechanism stays invisible (ADR-338 DP28 guard)

The stream carries reasoning + judgment-shaped intent. It does **not** carry: raw tool inputs/JSON, cognition tool *names* as such (ReadFile/SearchFiles), Haiku tier-2 evaluation calls, index materialization, mirror refreshes (`is_mirror_refresh_action`, `wake.py:1654`). The consent-line test (ADR-338 D3): if a step shows *what the Reviewer is perceiving/deciding* → render it as the persona's words; if it's *mechanical substrate plumbing within already-granted scope* → it stays below the line. Cognition tool events still drive the transient status's *existence* (something is being perceived) but the *label* is the persona's reasoning, never the tool.

## 4. What this does NOT do
- **Does not change the render grammars** (ADR-289) — Feed stays bubble-free typed events; Conversation stays bubbles. This adds the in-flight *lifecycle* both grammars were missing.
- **Does not expose mechanism** (ADR-338 DP28) — §D5 is the hard guard.
- **Does not add frame prose** (ADR-306/323) — intent-narration is the persona reasoning aloud, already in the model's behavior; we stop buffering it.
- **Does not touch the consent gate or the queue** (ADR-307) — actions still flow through the same gate; this is Channel-dimension (how a cycle *renders while running*), not Purpose/Substrate.
- **Does not change the round bound, close semantics, or autonomy** (ADR-260 §D8 / ADR-345 witness reframe) — a streamed cycle is the same cycle, watched.
- **Does not make reactive/scheduled wakes stream to a live operator** — those have no addressed SSE listener; their settled rows are unchanged (§6 sequences a later unification if demand appears).

## 5. Why a new ADR (not just an ADR-260 amendment)
ADR-260 §D6 is a *render grammar* that assumed a stream. The missing piece is **backend streaming substrate** (D1) — a load-bearing change to the hottest path (`invoke_reviewer` + `wake.py` + `anthropic.py`) that touches the LLM-call contract itself. That deserves its own ratified decision with its own gate, not a footnote on a year-old ADR. ADR-260 §D6's grammar is preserved and cited; this ADR supersedes-by-fulfillment the two commitments it claimed shipped but the audit found unbuilt (§D6.1 + the reasoning stream).

## 6. Implementation sketch + sequencing
- **`api/services/anthropic.py`** — new `chat_completion_with_tools_stream()` (`client.messages.stream(tools=…)`); yields typed events (`text_delta` / `tool_use_start` / `tool_use_complete` / `message_stop` + usage). Usage captured from the final `message_stop` (streaming returns usage at stop) — preserves the ADR-291 one-cost-ledger write.
- **`api/agents/reviewer_agent.py`** — addressed path of `invoke_reviewer` consumes the streaming call; emits `text_delta` and per-round intent via the existing `event_callback` (`reviewer_agent.py:1078-1087`) so `wake.py` can relay it. Round loop / bound / `ReturnVerdict` unchanged.
- **`api/services/wake.py`** — `stream_addressed_wake` gains a `text_delta` SSE event type (relaying reasoning tokens) alongside the existing `progress`/`agent_narration`/`reviewer_response`/`done`. The terminal `reviewer_response` becomes a *finalize* (persist + actions), not the *first* appearance of the reasoning text.
- **`web/contexts/NarrativeContext.tsx`** — handle `text_delta` for the Reviewer (mirror the System Agent's existing incremental append, `:684-700`); insert a streaming Reviewer placeholder on first token (the missing `stream_start` analog, `:667-668`); **delete** the tool-name label map (`:848-866`, per D4).
- **`web/components/tp/ConversationPanel.tsx` + `FeedTimeline.tsx`** — the three-state render (D3): thinking / streaming-with-transient-cognition / settled, with explicit visual boundaries.
- **Sequencing:** Phase 1 = backend streaming call + addressed path + SSE event (D1–D2). Phase 2 = frontend three-state render + map deletion (D3–D4). Phase 3 (deferred, demand-pulled) = whether reactive/scheduled wakes observed by a live operator should stream too (out of scope here; their settled rows are fine).
- **Gates:** `api/test_adr351_streaming_tools.py` (the streaming call yields ordered text-then-tool events; usage captured at stop; no dual blocking call on the addressed path). `web/test/adr351-inflight-render.test.ts` (three states render distinctly; no "reading substrate" string survives; cognition status shows judgment-copy not tool names — DP28 guard).
- **Dimensional classification:** **Channel** (Axiom 6 — how an invocation renders *while running*) projected through **Mechanism** (Axiom 5 — the streaming-vs-blocking LLM-call shape). Renders **Identity** (the persona reasoning aloud); changes neither **Purpose** nor **Substrate**.

## 7. Relationship to ADR-350 (the settled-state sibling)
ADR-350 renders the operation's **standing obligation at rest** (owed-vs-actual, the long-standing to-do, on Notifications → To do). ADR-351 renders a **single cycle in flight** (the Reviewer reasoning toward a decision, on the Conversation/Feed). Together they are the two registers of one invocation-rendering canon: *what the operation is on the hook for over its tenure* (350) and *what it is doing about it right now* (351). Neither touches the consent gate or substrate; both are Channel-dimension. ADR-350 stays Proposed and independent — but they should land as one coherent experience pass, because the operator's underlying ask ("how does the chat capture both real-time and long-standing?") is answered only by both.

## 8. Receipts

| Claim | Receipt |
|---|---|
| Reviewer LLM call is blocking, not streaming | `anthropic.py:257` (`messages.create`), called from `reviewer_agent.py:1161` |
| Reasoning arrives in one atomic event at cycle-end | `wake.py:1735-1742` (`reviewer_response` yielded once after `ReturnVerdict`) |
| "reading substrate" is frontend-invented, not persona | `NarrativeContext.tsx:848-849` (tool-name → label map) |
| No streaming placeholder for the Reviewer path | `NarrativeContext.tsx:667-668` ("Reviewer turns never reach stream_start") + `:868-874` (history reload) |
| A tool-less streaming call already exists (the gap is tool-awareness) | `anthropic.py:261-289` (`chat_completion_stream`, no `tools=`) |
| §D6 specified the experience incl. intent-narration-before-action | ADR-260 §D6.1 + §D6.3 + "the operator sees every handoff. There are no hidden steps." |
| Consent line forbids raw mechanism, permits judgment-shape | ADR-338 D3 / DP28 (above-line = perception/decision; below-line = mechanical enactment) |
| A wake is a multi-phase situation, not a one-shot prompt | ADR-318 D1 (perceive → reason forward → decide → act) |
| Intent-narration needs no new frame prose | ADR-260 §D6.1 ("already in the prompt"); ADR-306/323 ceiling preserved |
