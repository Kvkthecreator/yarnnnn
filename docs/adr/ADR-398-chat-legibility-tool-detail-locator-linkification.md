# ADR-398: Chat Legibility — Actual-Call Detail, Operator Locator, OS-Owned Linkification

**Status**: Implemented (2026-07-02)
**Date**: 2026-07-02
**Deciders**: KVK + Claude
**Plan context**: the chat-legibility arc surfaced by the operator's live test of the rungs-1+2 Freddie (2026-07-02) — "coherence and expected behavior are closely knit to the actual surfacing"
**Amends**: ADR-351 D4 (the per-tool label map deletion — scope clarified: *invented* labels stay deleted; *actual* call detail is not a label), ADR-023-era `SurfaceContext` (deleted — fossilized pre-ADR-297 schema, ignored by the backend since the bare-kernel floor)
**Preserves**: ADR-042 (tool-call block model — reconnected, not rebuilt), ADR-289 (row grammar), ADR-297/358 (SurfaceLink + window-namespaced params), ADR-202 (deep_links.py stays the external-channel URL source), DP28 (consent line), DP29 (attention routing is OS-owned), DP31 (citations name real sources)

## Context

Three legibility gaps, all confirmed in code:

1. **The live stream hides the work.** The Freddie path emits `tool_start`/`tool_end` with tool name + result summary (`routes/feed.py`), but the FE renders them as only a transient tool-agnostic status line — ADR-351 D4 deleted the FE's per-tool *guess map*, and the actual-call detail went down with it. Meanwhile the Claude Code-style `tool_call` block renderer (ADR-042) sits live in `NarrativeContext` listening for the dead pre-ADR-257 chat surface's events. The operator cannot diagnose agent behavior they cannot see — the act→witness→correct loop is broken at witness.
2. **"Viewing" is dead.** `surface_context` still arrives from the FE but is ignored (`feed.py` bare-kernel floor comment), and its schema is pre-window fossil vocabulary. Freddie does not know what the operator is looking at; "this file" cannot resolve.
3. **Outputs don't link.** Freddie names real paths and proposal ids (DP31) but nothing renders them navigable; `SurfaceLink` + `files.path` (ADR-388) exist but are not joined to chat text.

## Decisions

**D1 — Show the actual calls (amends ADR-351 D4's scope).** The `tool_start` SSE frame gains a compact `input` summary (path/slug/query essentials, server-composed — never full content); the route accumulates a `tool_history` list (`{type:'tool_call', name, input_summary, result_summary}` — the exact ADR-042 reconstruction contract already in `NarrativeContext`) and persists it on the settled Freddie row via `write_freddie_message(tool_history=…)`. The FE maps live `reviewer_progress` tool events into `tool_call` blocks inside the streaming Freddie bubble and renders them as compact dim rows on `FreddieCard` (live and settled). D4's rationale stands: the FE never *invents* meaning from a primitive name; it renders what the runtime *reports*.

**D2 — The operator locator (Viewing, re-founded on ADR-358).** `ChatRequest.surface_context` + the `SurfaceContext` class are DELETED (Singular Implementation). A new optional `locator: str` rides the same request — a short human-readable string the shell composes from the window manager's foregrounded surface + its scoped params (e.g. `files · path=/operation/pricing/q3-decision-notes.md`). It flows into the addressed wake's ask block as ONE line ("The operator is writing from: …"). ~20 tokens; survives any future envelope diet. The FE composes it (the shell knows where the operator stands — DP29); the backend never parses it (opaque situational fact).

**D3 — OS-owned linkification (never prompt-owned).** The FE detects substrate paths and proposal ids in Freddie/system chat text and renders them as `SurfaceLink`s (paths → Files at `files.path`; proposal ids → the decision queue). Zero prompt cost, zero confabulation risk — the model cannot mint a wrong URL because it never authors URLs; it keeps naming real paths (DP31) and the OS routes attention (DP29). No URL-authoring guidance is added to any prompt (the ADR-390 removal-over-addition discipline; the Rung-1 size ratchet enforces it).

## Consequences

- The chat surface shows Freddie's work the way Claude Code shows its own: what ran, on what, and what came back — collapsed, expandable, persisted.
- "This file" resolves; placement/cleanup asks act on where the operator actually is.
- Freddie's outputs become navigable ends of the loop: read the finding → click the file → witness the substrate.
- The fossil `SurfaceContext` schema is gone; `locator` is the single viewing-context carrier.
