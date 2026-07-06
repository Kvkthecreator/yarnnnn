# ADR-411: Chat Lanes and the Lane Tool Surface

**Status**: Accepted (2026-07-06) — implements ADR-408 D6 on the spike-ratified router (ADR-408 D4, LiteLLM)
**Date**: 2026-07-06
**Dimension**: Channel (Axiom 6 — where the member meets their helpers) + Identity (Axiom 2 — the member's embodiment acting) + Mechanism (Axiom 5 — which model runs the lane)
**Relates to**: ADR-408 (D2 altitudes, D4 router, D6 lanes — the ratified shape this implements), ADR-405 (witness dial — lane writes bind after-witness), ADR-407 (Phase 4 (workspace, principal) sessions — the lane's scope), ADR-373/386 (grants — the lane's boundary), ADR-209 (attribution — the lane's author string), ADR-396 (one meter — lane rounds are LLM judgment invocations)
**Amends**: ADR-209 (author taxonomy gains the `member:` prefix), ADR-320 (caller-class table gains the member-embodiment mapping)
**Amended by ADR-412 (2026-07-06)**: the lane strip leaves the chat drawer — the Chat surface (ADR-412 D3) is the lanes' chrome home; lane MECHANICS here are unchanged. **Amended by ADR-413 (2026-07-06)**: the D6 conventions doc is canonized as the MOUNT (environment declaration, composed never stored; runtime/behavior separation — behavior packs never ride it).

---

## 1. What this implements

ADR-408 D6 ratified the shape: **N model-pinned helper threads per member,
over one shared memory** — lanes are isolated conversations; the workspace
is the shared memory; cross-model collaboration happens through the
filesystem with attribution, never through each other's transcripts. The
steward thread stays singular and outside the lane system.

This ADR records the implementation decisions D6 left open (session
encoding, turn transport, the tool surface, attribution, cost, the
conventions doc) — the "tool surface's own ADR" that ADR-408 D4 said
follows the spike.

## 2. D1 — Lane encoding: no new tables, no migration

A lane is a `chat_sessions` row: `session_type='lane'`,
`context_metadata.lane = {name, model}` (the D6 "session metadata" model
binding), scoped (workspace, principal) exactly like every session post
ADR-407 Phase 4. Lane messages are `session_messages` rows via the
existing `append_session_message` RPC (roles `user`/`assistant`).
Archive = `status='archived'`. The lane list is a filtered read of the
member's sessions in the acting workspace.

## 3. D2 — The lane turn: non-streaming, bounded tool loop

`POST /api/lanes/{id}/messages` runs one turn: persist the member's
message → tool loop over `route_completion` (the ADR-408 D4 router;
LiteLLM translates OpenAI-format tools per provider) → persist and return
the assistant reply. Non-streaming JSON in v1 — a lane is a working
thread, not the steward's SSE terminal; streaming is additive later.
Round ceiling 8 (a cost ceiling, not a behavioral constraint — ADR-402
posture). Lanes never touch the steward's ADR-298 single-lane wake drain;
they run on the request path, in parallel, per member.

**Gate**: lanes exist only where `MODEL_ROUTER_ENABLED` is on — the
router is the lane's engine. `GET /api/lanes` reports `enabled` so the FE
shows the lane strip only when the engine is live.

## 4. D3 — The lane tool surface: five file verbs under the member's grant

A lane model gets exactly the file-verb surface (ADR-408 D4's ratified
attach): **ReadFile · WriteFile · EditFile · SearchFiles · ListFiles** —
executed server-side through `execute_primitive` under the member's auth,
so grants, the permission gate, and attribution apply for free. No entity
verbs, no Schedule, no DispatchSpecialist, no platform tools — a helper
is hands on the filesystem, not a seat at the orchestration table. The
tool definitions are the registry's own (converted Anthropic→OpenAI
format mechanically); no parallel definitions.

## 5. D4 — Attribution: the member's embodiment (`member:` prefix)

Lane acts attribute as **`member:{user_id} via {model}`** — the ADR-408
D2 ratified shape (the helper is the member's embodiment, not a
principal). Two one-line taxonomy changes:

- `VALID_AUTHOR_PREFIXES` gains `member:` (ADR-209 amendment).
- `_caller_class` maps `member:` → **operator class** (ADR-320
  amendment): the embodiment writes under the *member's* grant — the
  grant consult (ADR-373) resolves the member's `principal_grants` row by
  `principal_id` and narrows per-principal; the class default is the
  human default. The grant is the only boundary (ADR-408 D1) — a lane
  write the member could not make is denied; a lane write the member
  could make binds immediately, after-witness (ADR-405), and lands on the
  workspace timeline via the revision ledger like any member act.

The lane's reach is exactly the member's reach — the operator class is
not topology-locked (the owner owns the constitutional regions), so an
owner's lane can write what the owner can, revertible and witnessed; a
member-role principal's lane is bounded by their grant like the member
themselves. The conventions doc (D6) instructs helpers away from
constitutional regions as posture, not as enforcement. No new autonomy
dial: Altitude-2 helpers have no dial of their own (ADR-408 D2).

## 6. D5 — Cost: every lane round is a metered judgment invocation

Each router round records `execution_events` (slug `lane`, addressed,
tokens + normalized `ledger_model`, `principal_id` = the member) — the
one meter (ADR-396), priced by the one cost function (ADR-291 D2). The
lane model registry (`LANE_MODELS` in `services/lane_runner.py`) is the
creation-time whitelist; a model enters it only WITH a `_BILLING_RATES`
row (the D4 spike's no-silent-default-pricing rule). Anthropic remains
the steward's model (Altitude 1, ADR-402); Anthropic models in lanes are
ordinary Altitude-2 citizens.

## 7. D6 — The conventions doc: an AGENTS.md-shaped projection, composed not stored

Every lane turn's system prompt carries a kernel-composed projection of
how to work this workspace: the commons contract (read before writing;
durable knowledge belongs in files, not transcripts), the tool surface,
the root taxonomy (which regions are working substrate vs constitutional),
the attribution + witness facts, and the workspace's MANDATE head (read
live from `constitution/MANDATE.md`). Composed at turn time from kernel
constants + substrate — never a stored file (DP29 derived-never-stored;
storing it would create a second pedagogy file to drift against
`_workspace_guide.md`). Program bundles deepen it later by shipping their
own section; the kernel block is program-neutral (ADR-222).

## 8. What this ADR does NOT do

- No shared multi-user chatrooms (ADR-408 D6 rejection stands).
- No streaming lane transport in v1 (additive).
- No standing/unattended lane execution — a lane acts only on the
  member's addressed turn (an unattended helper is a foreign-llm grant,
  ADR-373/386, or a persona agent, ADR-382).
- No per-lane budget envelopes (lanes draw the workspace pool; per-seat
  pricing is ADR-409, demand-gated).
- No BYOK wiring yet (the router supports per-call keys; the tier lever
  lands with ADR-409).
