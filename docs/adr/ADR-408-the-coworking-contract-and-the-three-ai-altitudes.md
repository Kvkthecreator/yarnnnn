# ADR-408: The Coworking Contract and the Three AI Altitudes

**Status**: Accepted (2026-07-06, operator-ratified — "ready to execute"). **D3 Implemented same day**: kernel seed gains the `substrate: {delegation: autonomous}` per-class block (`DEFAULT_AUTONOMY_YAML`); `load_autonomy` parses it; new `autonomy_for_substrate()` resolves substrate → default; the permission gate's substrate branch consumes it (capital dispatch + ask-gate untouched); the 5 live steward-default workspaces flipped via `write_revision` one-shot (`scripts/oneshot/adr408_d3_steward_dial_substrate_autonomous.py`, attributed `system:adr408-d3`, revision receipts logged; program/operator-authored files untouched by marker check). Gate `api/test_adr408_d3_steward_dial.py` 11/11 — capital stays fail-closed, legacy files fall back to default, pause + never_auto still queue. D4 spike, D5 surfaces, D6 lanes proceed per §8.
**D4 spike PASSED — LiteLLM ratified (2026-07-06)**: litellm lib-mode in `api/requirements.txt`; `services/model_router.py` behind `MODEL_ROUTER_ENABLED` (default OFF, read at call time, lazy import); first routed call = session-summary (`services/session_continuity.py`, non-tool-loop Altitude-2 — the SSE tool loop is the D6 lanes build). Both spike criteria verified with prod receipts: (a) cost mirror — router reports, the one ledger records; routed tokens priced by `compute_cost_usd_inclusive` exactly (`cost_usd` MATCH on anthropic/claude-haiku + openai/gpt-4o-mini live calls; LiteLLM's own cost figure is log-only, never written — ADR-396 one-ledger held); (b) attribution — `principal_id` + `workspace_id` land on the `execution_events` row (the member's embodiment, D2). Gate `api/test_adr408_d4_router_spike.py` 14/14 incl. the steward-never-routes altitude boundary (freddie_agent/model_routing stay router-free — Anthropic remains Altitude 1's model). Spike findings for the lanes build: `execution_events` has NO model column (the `model` kwarg feeds rate lookup only — per-lane model legibility needs a column or metadata); the haiku `_BILLING_RATES` row (1.60/8.00) is 2x of $0.80/$4.00 while provider list is $1/$5 — rate-table drift surfaced by the router's mirror, operator decision. Rode along: the feed.py inline-summary NameError fix (summaries silently never generated since the ADR-291 wiring).
**Amended by ADR-413 (2026-07-06)**: the D4 router's scope is re-derived — LiteLLM is the driver for the TOOL-LOOP PROTOCOL CLASS (chat-completions-shaped engines), not "the language capability"; the driver boundary is interaction protocol, never modality. D4's mechanics (spike, cost-mirror, one ledger) are unchanged.
**Date**: 2026-07-06
**Dimension**: Identity (Axiom 2 — who acts, at which altitude) + Purpose (Axiom 3 — what binds when) + Mechanism (Axiom 5 — which intelligence runs where)
**Relates to**: ADR-405 (witness dial — D1 restates it as product posture), ADR-407 (three-scope taxonomy — the substrate this contract runs on), ADR-380/381/382/383 (activation ladder, Freddie, persona-agent seats, consistent agent framework — D2 completes their boundary cleanup), ADR-373/386 (grants — D4's helper attribution), ADR-310/311/368 (interop faces — D4 touches the tool-surface question)
**Amends**: ADR-383 (the agent-universal file set is re-read as *per-altitude*: Freddie carries the steward subset operationally, not the full persona/budget/autonomy load-out), ADR-380 D3 (harness honesty resolved by relocation rather than annotation)

---

## 1. Evidence — the 2026-07-05/06 two-account walk

First live walk of the multi-principal workspace (owner `kvkthecreator` + member
`seulkim88`, one commons), run after ADR-407 Phases 0–5 landed. Findings:

1. **The substrate works.** The member reached the commons (files, agents,
   proposals, activity), held their own chat thread with the steward (Phase 4
   per-(workspace, principal) sessions working as designed), and the member's
   steward-mediated write queued with correct attribution
   (`agent:system-agent`, structurally distinct from operator writes).
2. **The member's agency got mediated by the wrong dial.** The member asked
   Freddie to edit; Freddie's write queued as a proposal — because *Freddie's*
   delegation is `manual` (the ADR-380 Rung-1 clock), not because the member
   is a member. The surface never distinguishes "your act — binds now" from
   "the agent's act — queued by *its* dial." The operator read it as a
   permission question; it was an agent-autonomy question wearing the
   permission UI.
3. **The peer flow is illegible.** What the member did reached the owner as
   scattered witness notifications, not as a readable "what happened in this
   workspace, by whom" narrative (the known ADR-407 Phase-4b gap, now
   observed). The member's chat with the steward is correctly private; the
   *work* it produced has no shared home.
4. **The walk surfaced the real question**: with two humans live, "whose AI is
   this, and whose agency is acting" became the product's central ambiguity
   within minutes. This ADR answers it.

## 2. D1 — The coworking contract (the product posture)

**The workspace is a coworking commons, not an approval hierarchy.** This
restates ratified mechanics (ADR-405) as product law, so no surface builds
the other model by accident:

- A principal acting **within their grant binds immediately** (after-witness).
  The peers are *told*, never asked. There is no owner-review lane for member
  work, and none may be introduced. Figma's social model over the macOS data
  model (ADR-407 D2): free-for-all within granted regions, trust carried by
  attribution + revertibility + witness, not by gates.
- The **grant is the only boundary between humans**: members write the
  operational commons; the constitutional regions (`governance/ constitution/
  persona/ contract/`) remain the owner's. Region boundaries, not act review.
- **Approval queues belong to agents, not to members.** A queue entry means
  "an agent whose dial is at before-witness decided something" — never "a
  human's work awaits a superior." Surfaces must render these as different
  things (walk finding 2).

## 3. D2 — The three AI altitudes (the boundary cleanup)

The walk's ambiguity is resolved by naming three distinct kinds of AI, each
with a different relationship to identity, autonomy, persona, and budget.
Today's code trans-fuses machinery across them (ADR-383 gave every agent the
full file set; ADR-380 D3 admitted mandate/autonomy are degenerate on
Freddie). The taxonomy:

| | **Altitude 1: the System Agent (Freddie)** | **Altitude 2: seat-level AI helpers** | **Altitude 3: persona agents** |
|---|---|---|---|
| What it is | The workspace's OS agent — ONE per workspace | Each member's chosen model(s), working *as that member's hands* | Principal-grade judgment entities, on par with humans |
| Cardinality | 1 per workspace, N sessions (one thread per member) | N per member (chat-thread model, MCP connections) | 0..N per workspace (ADR-382, deferred) |
| Identity | `agent:system-agent` — its own attribution | **The member's** — acts attribute under the member's grant (the member's embodiment, DP17 generalized) | Its own principal + grant |
| Persona | None (steward role, not a persona; kernel steward-mandate only) | None (generic model + tool surface) | **Yes** — IDENTITY.md, the ADR-383 full file set lives HERE |
| Autonomy dial | Yes — its own (D3 sets the default) | No dial of its own — bounded by the member's grant; member acts bind after-witness | Yes — per-agent, under the Rung-2 track-record clock |
| Budget | Draws the workspace pool, metered as itself | Draws per D4 (router key = the metering point) | Own allocation (ADR-391 Layer ②, built when this tier builds) |
| Canon home | ADR-381 | This ADR (D4) | ADR-382 |

**Consequences (the cleanup):**

- **Freddie is confirmed as ONE agent with MANY sessions** — the same
  colleague holding a separate DM thread with each member (the ADR-407
  Phase-4 session model is exactly this). Not one-Freddie-per-user: its job
  is the *commons'* coherence, and per-user stewards would fight over one
  filesystem. (Operational note: the ADR-298 single-lane wake drain
  serializes the workspace's steward work; concurrent addressed turns from
  two members contend on one lane — acceptable now, a named scaling seam.)
- **The persona/mandate/autonomy/budget load-out is Altitude-3 machinery.**
  Freddie *carries* the universal files (ADR-383's one-file-structure stands)
  but operationally exercises only the steward subset. The ADR-383 §"frame
  re-carve" (remove capital-judgment residue from the system agent's frame)
  is re-affirmed as owed work under this ADR's banner.
- **Altitude-2 helpers are NOT principals.** A member's ChatGPT/Gemini/Claude
  acting through the member's seat attributes as the member (with transport
  provenance, e.g. `member:{id} via {model}`) — it holds no independent
  grant, persona, or dial. This is the load-bearing simplification: it means
  routing N models to seats requires NO new principal machinery. (A member's
  *standing* MCP connection that acts unattended remains a foreign-llm grant
  per ADR-373/386 — the existing model, now needing the per-member binding.)

## 4. D3 — The steward's dial inverts: hands, not gatekeeper

Freddie's default delegation moves `manual` → **`autonomous` for the
substrate family**. The operator's walk-informed ruling: the system agent is
"hands to execution" — a true assistant at the UX + data-handling level, for
every member — and gating its reversible substrate work makes every member's
steward interaction feel like filing a request with the owner.

Why this is safe and canon-consistent, not a loosening of the ladder:

- ADR-380's deferral line is autonomy over **consequential** action. The
  substrate family is reversible by construction (ADR-209 revision chain +
  revert-as-write, ADR-406 linearity). The **capital / external-write /
  consequential families stay gated exactly as today** — the ADR-307 gate and
  the QUEUE are untouched for them.
- The topology locks are unaffected: locked roots (`governance/` etc.) DENY
  regardless of dial. Autonomy widens *within* permission, never through it.
- ADR-405 D3 is the compensating control: every steward substrate act is
  attributed, ledgered, and after-witness-emitted. The operator still
  witnesses everything — *after*, like a member's act. This IS the witness
  dial doing its job, applied to the steward.
- Mechanically this is a default change, not architecture:
  `_autonomy.yaml` delegation default (kernel seed + existing workspaces via
  operator-initiated reapply), and the walk-finding-2 surface fix renders
  agent-queued acts distinctly wherever any remain.

## 5. D4 — Seat-level model routing: buy, not build

The seat-level lane (each member choosing the model that powers their thread
and helpers) rides an **existing open-source router rather than in-house
provider plumbing**. Requirements the router must satisfy:

1. One API shape over many providers (Anthropic/OpenAI/Google/open-weights),
   so the chat path and helper tool-loop are provider-blind.
2. Per-key/per-seat **cost attribution** we can mirror into
   `execution_events` (the single meter, ADR-396 double-charge invariant —
   the router must not become a second ledger; it reports, our ledger
   records).
3. BYOK optionality (a member/workspace bringing their own provider key)
   without changing the call path.
4. Self-hostable on the existing Render footprint (no new vendor on the
   critical path).

**Primary candidate: LiteLLM** (self-hosted proxy — provider-unified API,
per-key budgets/tracking, fallbacks, BYOK-friendly, OSS). **Alternative:
OpenRouter** (hosted, fastest to ship, but adds a vendor + per-token margin on
the critical path and weakens requirement 4). **Decision gate**: a spike
behind a flag — route ONLY the chat-thread model call for one test seat
through the router, verify cost-mirroring into `execution_events` and the
attribution shape from D2, then ratify the pick. The API lane (not MCP) is
the working direction per the operator's host-capability constraint (Gemini
web offers no connectors — MCP reach is host-bounded, the router is not).

**How helpers latch onto the filesystem** (the under-represented piece the
operator named): a routed model gets (a) the **file-verb tool surface**
(ReadFile/WriteFile/EditFile/SearchFiles/ListFiles + revisions) executed
server-side under the member's auth — the same `execute_primitive` path, so
grants/gates/attribution apply for free; and (b) a **workspace conventions
document** (an `AGENTS.md`-shaped projection of the substrate taxonomy +
file-format discipline, generated per workspace) injected at session start so
any generic model can work the filesystem competently. This reopens ADR-368's
supersession of the raw-verb face **as a tiered surface** (intent verbs for
casual memory use; raw verbs + conventions for working seats) — the tool
surface's own ADR follows the spike.

## 6. D5 — Surface consequences (first-cut relocation)

The walk confirms the ADR-407 relocation table; ordered:

1. **The shared timeline (Phase 4b)** — a workspace "what happened, by whom"
   composition derived from the attributed ledgers (never a chat table),
   actor-grouped, the member-visible home of steward/autonomous work. This is
   the single highest-leverage fix from the walk.
2. **Act-vs-agent disambiguation** — proposal surfaces label queue entries as
   the *agent's* dial product; member acts never render as "pending
   approval." (Mostly moot for substrate after D3.)
3. **Attribution-forward passes** on Files/Recents/Home (who touched what as
   primary metadata) and the ambient which-workspace indicator.
4. Owner/member view split on Settings (constitutional panes read-only or
   hidden for members) — currently implicit via grant failure, should be
   explicit UI.

## 6b. D6 — Chat lanes: N model-pinned threads over one shared memory (added 2026-07-06)

Operator-ratified refinement of the seat-level chat shape. A model picker on
a single pane is rejected — it reads as "switching engines over the same
chat app." The seat-level surface is **lanes**:

- **The steward thread stays singular** — one per member per workspace, the
  OS terminal, outside the lane system. No multi-chat exists at Altitude 1.
- **Helper lanes are N per member**, each a named conversation **pinned to a
  model** (Gemini lane for docs, Claude lane for code, ChatGPT lane for
  images, an on-prem endpoint lane for sensitive material — LiteLLM's
  custom-endpoint support makes on-prem the same router config, tier-gated
  with BYOK). Schema: `conversation`-scope `chat_sessions` rows per member
  (already supported); the lane's model binding is session metadata; the FE
  drawer gains a lane list. Bounds are UX, not policy (soft cap +
  auto-archive via the existing session-summary machinery); lanes run through
  the router in parallel and never touch the steward's single-lane drain.
- **The contract that makes this model-agnostic co-work rather than a chat
  app with a dropdown: lanes are isolated conversations; the workspace is
  the shared memory.** A lane's model never reads another lane's transcript —
  it reads what the other lane *wrote to the commons*, with attribution.
  Cross-model collaboration happens through the filesystem (the D4 tool
  surface + conventions doc), which is the product thesis applied to chat.
- **Shared multi-user chatrooms are explicitly NOT built.** The shared
  space's canonical form is the commons + the ledger-derived timeline
  (D5.1); a chatroom would reintroduce chat-as-shared-narrative-source,
  which ADR-407 D6 rejected. Revisit only on demonstrated demand, as
  sessions with N participant grants — a different product muscle
  (presence/turn-taking), deliberately deferred with ADR-373's collaboration
  layer.

Sequencing within the lane work: finish the single-thread experience first
(session-boundary legibility, history surfacing, per-workspace drawer
behavior — the current unresolved tail), then lanes ship WITH the D4 router
spike (a lane is the router's natural unit of use).

Pricing for seats + lanes: **ADR-409** (per-seat Type-B — this ADR carries no
pricing).

## 7. What this ADR does NOT do

- No Altitude-3 build (ADR-382 stays deferred; this ADR only assigns the
  machinery there conceptually).
- No change to the consequential gate, capital path, or topology locks.
- No pricing decision (per-seat lands with the seat-level lane's own ADR;
  ADR-396 stands until then).
- No outbound a2a orchestration (ADR-404's honesty line stands — models come
  IN to seats).
- No merge/CRDT/presence (ADR-373 rejection stands).

## 8. Sequencing

1. Ratify D1/D2 (this document).
2. D3 dial default + walk-finding-2 surface labels (small).
3. D5.1 shared timeline (Phase 4b) — prerequisite for the seat-level lane to
   be *visible* co-work.
4. D4 router spike behind a flag → tool-surface ADR + pricing ADR follow the
   spike's evidence.
5. ADR-383 frame re-carve rides along when the steward's prompt is next
   touched (CHANGELOG discipline applies).
