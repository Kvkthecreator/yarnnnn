# ADR-399: The Turn Artifact — Append-Only Within One Narrative Entry

**Status**: Implemented (2026-07-02)
**Date**: 2026-07-02
**Deciders**: KVK + Claude
**Context**: the operator's live observation, same day ADR-398 shipped: while a Freddie turn streams, the chat "writes, then delete-rewrites" — and the operator's stated assurance requirement: *"everything is captured and persistent in the chat."* Guiding principle set by the operator: future-proof + so obvious a casual non-technical person "just gets it."
**Amends**: ADR-351 Phase 2 (the transient streaming bubble + settle-by-history-reload — DELETED), ADR-398 D1 (the trail becomes the full turn artifact: reasoning + calls)
**Preserves**: ADR-289 (one invocation = one narrative entry — the grammar every mount depends on), ADR-042 (block model), ADR-360 (close contract), the moat framing (durable attributed memory — now embodied by the chat surface itself)

## The diagnosis

The "delete-rewrite" was real and by design: the FE streamed the model's interim per-round reasoning into a bubble styled as *the message*, then on settle **dropped the bubble and reloaded history from the DB**, whose row carried only the final report. Nothing was wrongly lost — but the UI presented process in the message's register and then visibly destroyed it, violating the deepest contract a layman knows (a message, once shown, never disappears) and contradicting the product's own pitch (everything captured, attributed, persistent).

## The decision analysis (compact)

Three candidate models against the operator's principle:

| | Settle-replace (pre-399) | Claude Code literal (row per fragment) | **ChatGPT-shaped (chosen)** |
|---|---|---|---|
| Streamed content never vanishes (the layman contract) | ✗ | ✓ | ✓ |
| Everything captured + persistent (the moat, the operator's assurance) | ✗ | ✓ | ✓ |
| One invocation = one narrative entry (ADR-289; Flow/Activity stay readable) | ✓ | ✗ | ✓ |
| Answer legible at a glance for a casual person | ✓ | ✗ (15 gray rows/turn, answer buried) | ✓ |

Claude Code's append-only *transcript* is the right **invariant** with the wrong **granularity** for a narrative-of-record product: it's a developer transcript. The layman's actual reference for AI chat is ChatGPT/Claude.ai — hundreds of millions of users trained on: *one response per turn; what streams stays; process (thinking, tool use) renders as visually distinct, collapsible, persisted sub-sections of that same turn.* That is the future-proof choice precisely because it adopts the interaction grammar the market is standardizing on while leaving the narrative substrate untouched.

**Decision: append-only *within* one persisted turn-artifact.**

## Mechanics

- **D1 — The trail is the turn artifact.** The route's ADR-398 trail generalizes to one ordered list: `metadata.tool_history` = `[{type:'reasoning', text} | {type:'tool_call', name, input_summary, result_summary}]`. Text the model emits *before* a tool call is interim reasoning and is persisted in place; the text trailing the last call is the report (the row's `content`) and is never duplicated into the trail. Legacy consumers filter `type=='tool_call'` and are unaffected; freddie-role rows never enter `build_history_for_claude`'s structured path.
- **D2 — Live rendering is append-only.** Streaming text renders into the bubble; when a tool call arrives, the open text block is *re-typed* to a `thinking` block (same content, dimmer register) — visually declaring "this was process" without removing a character. Tool rows append where they happen. The trailing text streams as the report.
- **D3 — Settle happens in place.** On `reviewer_response`, the FE swaps the trailing live text for the authoritative final text (the same words) and keeps everything else. The `fetchAndSetHistory()` settle-reload — the visible delete-rewrite — is **deleted** (both sites: the in-stream handler and the post-stream `reviewerFired` tail). The DB row, persisted with the identical trail, reconciles on the next natural history load, pixel-equivalent.
- **D4 — Settled cards replay the same artifact.** History reconstruction maps the trail *in order* (reasoning → collapsible dim disclosure, tool_call → compact row) so a turn reads identically live, on reload, and six months later — the trace property demonstrated in every message.

## Consequences

- The narrative grammar is untouched: one Freddie turn = one row, every mount (Flow, Activity) unchanged; the row simply got richer (~a few KB of process metadata).
- The chat surface now embodies the moat: what the operator watched is exactly what is stored, attributed, and expandable forever.
- Cost: negligible (metadata on an existing row; no new tables, events, or rows).
- Follow-on (deferred, named): the four SYSTEM narration rows per turn now partially duplicate the trail in the chat mount; whether chat collapses them into the trail is a separate rendering decision — they remain the consequential-action ledger for other mounts.
