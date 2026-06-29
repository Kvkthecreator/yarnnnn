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

## The shared 4-value vocabulary (recall + trace)

`recall` reports `confidence`; `trace` reports `resolution`. **Different field names, but ONE shared value scale with identical meaning** — so a single host-side handler works across both. The field is **ALWAYS present** (never absent on a miss).

| Value | Meaning | Host action |
|-------|---------|-------------|
| `high` (recall) / `exact` (trace) | confident hit — recall: dominant/exact; trace: the file's basename IS the subject | use it / narrate |
| `ambiguous` | found multiple, none dominant | surface candidates + ASK / CONFIRM which they mean |
| `weak` | found SOMETHING but low-confidence (recall: below the dominant bar; trace: a single loose FTS mention-match) | a lead, not an answer — confirm / answer cautiously |
| `none` | NOTHING recorded at all (a true miss) | the strongest "nothing here" signal — answer from own knowledge |

> The top value is the one place the two tools' names diverge: `high` reads right for recall ("how confident is this match"), `exact` reads right for trace ("the file IS the subject"). The **lower three** — the ones that gate clarify/confirm/fallback — are identical in name and meaning, which is what a uniform integration handler keys on.

**Two seams this scale closed** (live discrimination test, 2026-06-29 — a host dev writing `switch(confidence)` would have hit both):
1. **Absent-field hole** — the recall miss used to omit `confidence` entirely (→ `undefined`), while trace always returned its field. Now both ALWAYS emit the field.
2. **`weak` overload** — `weak` used to mean "nothing recorded" in trace but "loose-but-present hit" in recall — same word, two host actions. Split: `weak` = a real-but-shaky hit (both tools), `none` = a true miss (both tools).

## How the three current tools satisfy the principle

| Tool | The judgment it makes | Honest-state field | Notes |
|------|----------------------|--------------------|-------|
| **recall** | picks which recorded material matches the subject | `confidence` (4-value, + per-chunk `similarity`) | always present |
| **trace** | resolves the subject to ONE file whose history it returns | `resolution` (4-value) | always present; `exact`≡recall `high` |
| **remember** | captures a raw observation (the seat's derive/place/judge is ASYNC) | `status`: `captured` (raw stored + durable now; not yet placed/judged) | also emits legacy `captured: true` — a back-compat alias the `remember-receipt` widget's type-guard reads; keep both until the widget migrates |

All signals are **derived from data the tool already had** (similarity scores from the semantic search, the resolve-branch taken, the synchronous-vs-async write boundary). None costs an extra LLM call or DB round-trip.

## The failure mode this exists to prevent

The bug that motivated the contract: a tool **crowns one result and presents it as the answer** even when the honest state is "several candidates, none dominant" or "captured but not yet integrated." The caller (host LLM) then trusts the false certainty and does NOT clarify when it should. The fix is never "make YARNNN clarify" (wrong layer) — it's "make YARNNN stop hiding the ambiguity," so the host's existing intelligence can clarify in-conversation.

`trace` was the sharpest case: a wrong trace returns a plausible, authoritative-looking revision history ("here's how your thinking on X evolved") over the wrong file — exactly the differentiator you don't want lying. Hence the `resolution` signal.

## For the next tool added to the toolbox

Before shipping a new MCP tool, answer: *what judgment call does this tool make on the host's behalf, and does the return tell the host it made it?* If the tool ever picks, ranks, resolves, or partially-completes, it owes the host an honest-state field + a one-line instruction (in the tool description) on what to do with each value. The clarify/confirm/expectation-setting act stays the host's. Cost discipline: derive the signal from what you already computed; never add inference to produce it.
