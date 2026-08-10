# The honest-state contract — how every MCP tool reports to the host LLM

> **Status**: design principle (2026-06-29), re-grounded by ADR-543 (2026-08-10 —
> the file-native re-cut narrowed the fuzzy surface to one verb).
> **Scope**: the interop face (`api/mcp_server/` + `compose_*` in `services/mcp_composition.py`).
> **Canon it rests on**: ADR-368 D1 (the bright line — search returns material, the host explains), ADR-310 (one moat, two faces — the connector is a *connector*, not the agent), ADR-543 (exact-vs-fuzzy is the verb split).

## The principle (one line)

**YARNNN is the workspace connector, not the agent in the conversation. Every tool reports honest state and lets the HOST LLM decide and act — it never clarifies, guesses, or talks to the user itself, and it never launders uncertainty into false confidence.**

The human is talking to ChatGPT / Claude / Gemini. That host is the only thing that can see "what the user just said," so every *conversational act* (clarify, confirm, set expectations, fall back) belongs to the host. YARNNN's job is to hand the host an honest enough picture that it can make those calls well — and to never make them *for* it by hiding information.

## The reusable 3-check test (apply to every tool, existing and new)

A tool return is correct iff it passes all three:

1. **Honest state, no laundering.** If the tool made a judgment call — ranked several candidates, matched fuzzily — it must SAY SO in the payload. Never present a guess or a partial as certainty. A confident-looking wrong answer is worse than an honest "I'm not sure which."
2. **The act belongs to the host.** YARNNN reports; the host decides to use / clarify / confirm / retry / fall back. YARNNN never authors conversational behavior (it can't see the conversation).
3. **Zero added inference.** Surface signals already computed. Don't spin up a YARNNN-side LLM to do what the host's existing turn already covers.

## How the split simplifies honesty (ADR-543)

The file-native re-cut made exact-vs-fuzzy a **verb boundary**, which collapses
most of the honest-state surface into two simple shapes:

- **Exact verbs** (`open`, `history`) make no judgment call — a reference names
  one file, and a miss is `found: false`. Nothing to launder.
- **Enumeration** (`list`) returns what exists — `count`, plus `truncated: true`
  when the subtree exceeded the cap (silent truncation would read as "that's
  everything").
- **The one fuzzy verb** (`search`) reports **`confidence`** — the 4-value
  scale below, ALWAYS present (never absent on a miss; the pre-2026-06-29
  miss-path dropped the field entirely, and a host's `switch(confidence)` hit
  `undefined`).

## The 4-value `confidence` vocabulary (search)

| Value | Meaning | Host action |
|-------|---------|-------------|
| `high` | confident hit — dominant top score, or a single hit | use it |
| `ambiguous` | found multiple, none dominant | surface candidates + ASK / CONFIRM which they mean |
| `weak` | found SOMETHING but low-confidence (below the dominant bar) | a lead, not an answer — confirm / answer cautiously |
| `none` | NOTHING matched at all (a true miss) | the strongest "nothing here" signal — answer from own knowledge, or `list` what exists |

Derived from the similarity scores the search already computed — zero extra
inference or DB cost. `weak` and `none` are deliberately distinct: `weak` is a
real-but-shaky hit; `none` is a true miss. Overloading one word for both was a
live seam (2026-06-29).

## The failure mode this exists to prevent

The bug that motivated the contract: a tool **crowns one result and presents it
as the answer** even when the honest state is "several candidates, none
dominant." The caller (host LLM) then trusts the false certainty and does NOT
clarify when it should. The fix is never "make YARNNN clarify" (wrong layer) —
it's "make YARNNN stop hiding the ambiguity," so the host's existing
intelligence can clarify in-conversation.

The sharpest historical case: the pre-ADR-543 `trace` verb resolved a *topic*
to a file fuzzily and could return a plausible, authoritative-looking revision
history over the wrong file — exactly the differentiator you don't want lying.
ADR-543 removed that failure mode structurally: `history` takes an exact
reference and cannot resolve the wrong file, only miss honestly.

## A refusal is an honest state — and it must be distinguishable from silence

The contract has a second edge, found live on 2026-08-10: **an honest refusal and a
call that never arrived look the same in a chat window, and mean opposite things.**

Every yarnnn refusal is a *structured* result — an `error` code, a message, and
usually the fix (`base_required` returns the head revision id to retry with;
`old_string_not_found` says re-open and re-anchor; `destination_exists` says delete
first). That structure is the honest-state contract applied to failure: the tool
declined, said so, and said why.

A host-side block carries **no `error` code** — it is prose from the client
("blocked by safety checks", "the tool has been disabled"), and yarnnn never saw the
request. Measured that day: ChatGPT blocked `edit` and `move` while `save`, `delete`
and `history` succeeded seconds apart in the same conversation; the server logs
recorded **no request at all** for the two blocked verbs.

**The discipline this imposes on us**: never report a host-side block as a yarnnn
error, and never let a tool return prose-only failure. A failure with no code is
indistinguishable from a failure that never reached us — which is precisely the
false-certainty this document exists to prevent, pointed at the error path instead
of the result path. The operator-facing version of this test lives in
[CONNECTING.md](CONNECTING.md) §"Did yarnnn refuse, or did your host never call?".

> Corollary, and it is a real constraint: **do not reshape a verb to satisfy a
> host's classifier.** `edit` is anchored so unread content is never at risk; `move`
> refuses to overwrite; `save` refuses a blind overwrite. Loosening those to get
> past a client-side gate would trade a real safety property for a cosmetic one.

## For the next tool added to the toolbox

Before shipping a new MCP tool, answer: *what judgment call does this tool make
on the host's behalf, and does the return tell the host it made it?* If the
tool ever picks, ranks, resolves, or partially-completes, it owes the host an
honest-state field + a one-line instruction (in the tool description) on what
to do with each value. Prefer making the verb exact (no judgment to report)
over adding a confidence channel. Cost discipline: derive the signal from what
you already computed; never add inference to produce it.
