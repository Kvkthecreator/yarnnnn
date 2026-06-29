# The honest-state contract — how every MCP tool reports to the host LLM

> **Status**: design principle (2026-06-29), derived from the recall/trace/remember work.
> **Scope**: the interop face (`api/mcp_server/` + `compose_*` in `services/mcp_composition.py`).
> **Canon it rests on**: ADR-368 D1 (the bright line — recall returns material, the host explains), ADR-310 (one moat, two faces — the wedge is a *connector*, not the agent).

## The principle (one line)

**YARNNN is the memory connector, not the agent in the conversation. Every tool reports honest state and lets the HOST LLM decide and act — it never clarifies, guesses, or talks to the user itself, and it never launders uncertainty into false confidence.**

The human is talking to ChatGPT / Claude / Gemini. That host is the only thing that can see "what the user just said," so every *conversational act* (clarify, confirm, set expectations, fall back) belongs to the host. YARNNN's job is to hand the host an honest enough picture that it can make those calls well — and to never make them *for* it by hiding information.

## The reusable 3-check test (apply to every tool, existing and new)

A tool return is correct iff it passes all three:

1. **Honest state, no laundering.** If the tool made a judgment call — picked one of several candidates, resolved fuzzily, captured-but-not-yet-processed — it must SAY SO in the payload. Never present a guess or a partial as certainty. A confident-looking wrong answer is worse than an honest "I'm not sure which."
2. **The act belongs to the host.** YARNNN reports; the host decides to use / clarify / confirm / retry / fall back. YARNNN never authors conversational behavior (it can't see the conversation).
3. **Zero added inference.** Surface signals already computed. Don't spin up a YARNNN-side LLM to do what the host's existing turn already covers. The clarify/confirm happens in the host turn the user already paid for.

## How the three current tools satisfy it

| Tool | The judgment it makes | Honest-state field | What the host does with it |
|------|----------------------|--------------------|----------------------------|
| **recall** | picks which recorded material matches the subject | `confidence`: `high` \| `ambiguous` \| `weak` (+ per-chunk `similarity`) | `high` → use it; `ambiguous` → surface candidates + ASK which they mean; `weak` → treat as loose / answer from own knowledge |
| **trace** | resolves the subject to ONE file whose history it returns | `resolution`: `exact` \| `ambiguous` \| `weak` | `exact` → narrate the history; `ambiguous` → CONFIRM it's the right thing before narrating; `weak` → nothing recorded |
| **remember** | captures a raw observation (the seat's derive/place/judge is ASYNC) | `status`: `captured` (raw stored + durable now; not yet placed/judged) | set the expectation "saved — filed + checked in a moment"; don't promise it's organized/validated yet |

All three signals are **derived from data the tool already had** (similarity scores from the semantic search, the resolve-branch taken, the synchronous-vs-async write boundary). None costs an extra LLM call or DB round-trip.

## The failure mode this exists to prevent

The bug that motivated the contract: a tool **crowns one result and presents it as the answer** even when the honest state is "several candidates, none dominant" or "captured but not yet integrated." The caller (host LLM) then trusts the false certainty and does NOT clarify when it should. The fix is never "make YARNNN clarify" (wrong layer) — it's "make YARNNN stop hiding the ambiguity," so the host's existing intelligence can clarify in-conversation.

`trace` was the sharpest case: a wrong trace returns a plausible, authoritative-looking revision history ("here's how your thinking on X evolved") over the wrong file — exactly the differentiator you don't want lying. Hence the `resolution` signal.

## For the next tool added to the toolbox

Before shipping a new MCP tool, answer: *what judgment call does this tool make on the host's behalf, and does the return tell the host it made it?* If the tool ever picks, ranks, resolves, or partially-completes, it owes the host an honest-state field + a one-line instruction (in the tool description) on what to do with each value. The clarify/confirm/expectation-setting act stays the host's. Cost discipline: derive the signal from what you already computed; never add inference to produce it.
