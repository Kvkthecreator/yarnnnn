# ADR-350 — The Standing Obligation as a rendered surface: the operation's owed-vs-actual, surfaced above the queue

**Status:** **Proposed (2026-06-21)** — design; FE-only, no schema/primitive change. Gate `web/test/adr350-standing-band.test.ts` (to author). Closes the ADR-344 §8 surfacing gap ("the standing obligation is diagnosed silently") and the audit finding below.
**Date:** 2026-06-21
**Deciders:** KVK (operator) + Claude (collaborator)
**Hat:** A (system canon)

> **Discourse base:** the operator's question — *"do we have a clear, long-standing updated todos we can actively show on the chat layout? … our chat is a feed of not just real-time 'working' but long-standing autonomous activity — how do we fundamentally handle realtime streaming alongside concepts that are probably notifications alongside system-update wake outputs?"* — grounded against the Claude-Desktop "Updated todos" screenshot. The grounding correction (below) is the whole ADR: the screenshot's todos are a *per-turn agent scratchpad*; YARNNN's equivalent is a *tenure-scoped owed-output the Reviewer already derives every wake* (ADR-344) — borrowing the widget without the meaning would import a session-scoped affordance onto tenure-scoped substrate. The right move is to render **our** concept.

**Extends:** ADR-344 / Derived Principle 30 (the standing obligation — the Reviewer derives owed-output and classifies a shortfall every wake; this ADR gives that derivation an operator-facing **render** without changing what the Reviewer computes), ADR-345 (Expected Output is the *declared* referent + the autonomy-as-witness reframe — the panel reads `_expected_output.yaml` and frames a shortfall as a to-do, never a block), ADR-340 / DP29 ("mirror once, compose few" — this is a **composition**, one surface ↔ one operator act, not a new mirror), ADR-349 D2 (the panel mounts inside the existing **Notifications** composition's "To do" pane; no new launcher tile).
**Preserves:** ADR-344 §7 ("No new primitive, schema, or table" — the obligation stays *derived*, never persisted as a structured record; the panel reads only substrate that already exists), ADR-307 (one gate, one queue — the band sits *above* `action_proposals`, never replaces the consent gate), ADR-320 (topology — the panel **reads** persona-region substrate, the operator never writes it there), ADR-289 (the Feed stays bubble-free typed-event grammar — this ADR adds nothing to the Feed body), ADR-275 D1 (any organ the Reviewer authors to close a (B) gap is still Reviewer-authored, surfaced as standing intent — the panel renders that intent, it does not author it).

---

## 1. The audit (the half the operator was right about, and the half that reframes the answer)

The operator asked whether YARNNN has a "long-standing updated todos" it can show on the chat layout, analogous to Claude Desktop's "Updated todos" panel.

**It does — but it is almost entirely backend cognition today, never rendered.** The audit, with receipts:

| Concept | Substrate | What it is | Rendered today? |
|---|---|---|---|
| **Expected Output** (ADR-345, DP30) | `governance/_expected_output.yaml` (`GOVERNANCE_EXPECTED_OUTPUT_PATH`, `workspace_paths.py:90`) + `constitution/MANDATE.md ## Expected Output` | The *declared* contract — what the operation owes (kind · delivery-cadence · bar) | ✅ Yes — `ExpectedOutputCard.tsx` in the **Workspace Settings** door only |
| **Standing-obligation check** (ADR-344, DP30) | *derived live at wake* (budget→pace × mandate→volume × bar); never persisted (ADR-344 §7) | The Reviewer's wake-time *actual-vs-owed* check + the (A) quiet-world / (B) structurally-can't classifier | ❌ **No** — pure Reviewer cognition; lands in the judgment narrative, never surfaced as a standing fact |
| **Standing Intent** (ADR-296) | `persona/standing_intent.md` (`PERSONA_STANDING_INTENT_PATH`, `workspace_paths.py:127`) | What the Reviewer is *watching for* / the (B) gap it re-raises each wake until resolved — the closest thing to a durable "to-do" | ⚠️ File exists; **not surfaced** anywhere in `web/` |
| **Wake Queue** (ADR-298) | `wake_queue` (transient compute) | What is pending/locked to run | ⚠️ Only `queue_depth` as a binary glance in `BudgetStatusItem.tsx` — "1 wake pending" |

So the "long-standing to-do list" **exists as a derivation the Reviewer performs every wake, and the operator never sees it.** ADR-344 §8 named this as future work; it was diagnosed silently, landing in the judgment narrative and (for a (B) gap) in `standing_intent.md` — a prose file with no render path. There is no "updated todos" panel analog.

**The grounding correction.** Claude Desktop's "Updated todos" is the *model's plan for the turn it is executing right now* — ephemeral, single-session, scratchpad. YARNNN's equivalent is the **standing obligation**: tenure-scoped, derived from the mandate, re-confronted every wake. Importing the *widget* without the *meaning* would misframe a tenure obligation as a session task list. This ADR renders the obligation YARNNN actually holds.

## 2. The transport problem is already solved — this is a *surface* gap, not a streaming gap

The operator's secondary worry — "how do we handle realtime streaming alongside notifications alongside system-update wake outputs?" — is **already settled at the transport + grammar layers**, and the ADR records this so the surface work doesn't re-solve it:

- **Three grammars, deliberately split** (not one feed): the **Feed** (`/feed`, typed event cards, *no bubbles* per ADR-289 D1 — "the Feed is not a conversation"), the **Conversation** (the dockable rail, ADR-316 — bubble grammar, filtered to `pulse='addressed'`, SSE-streamed via `stream_addressed_wake`), and **Notifications** (`/notifications`, ADR-349 — the composition fronting To do / Activity / Schedule; "the window = the bell, one object at two zooms").
- **Realtime + async already land live**: addressed cycles stream via SSE; autonomous wakes (`cron_tick` / `substrate_event` / `proposal_arrival`) push via Supabase Realtime on `session_messages` (`use-session-messages-realtime.ts`) — the operator sees substrate writes as they happen, not on refresh.

The gap is not *how activity arrives*. It is that **the standing state the activity is in service of is invisible** — the operator sees a stream of beats but never the obligation those beats are (or aren't) discharging. This ADR adds the missing *standing* register; it touches no transport.

## 3. Decision — the Standing band, mounted above the To-do queue

A **Standing band** renders at the head of the **Notifications → "To do"** pane (`resolve` key; `notifications/page.tsx:45-54,86-132`), *above* the discrete `action_proposals` list (`QueueBody.tsx`). One composition (DP29 "compose few"), one operator act (Decide), one new register on a surface that already exists. No launcher tile, no route, no mirror.

The band answers, in the operator's words, **"what is this operation on the hook for, and is it on track?"** — and it composes only substrate that already exists (ADR-344 §7 holds — nothing new is computed or stored):

**Read 1 — the contract (what it owes).** From `governance/_expected_output.yaml` via the existing `web/lib/content-shapes/expected-output.ts::parse()` + `formatExpectedOutputSummary()` (`expected-output.ts:124,224`). Renders the one-line promise: *"Owes: a piece, biweekly (a floor-gated cadence, not a quota)."* When the file is absent, the band renders the **derived-by-default** state (ADR-344 §2: derivation is the default; explicit is opt-in) — "No explicit contract; the Reviewer derives owed-output from budget + mandate" with a link to declare one (`ExpectedOutputCard`). The band never invents a number the operator didn't declare.

**Read 2 — the standing gap (why it's not on track), when one is open.** From `persona/standing_intent.md` (`PERSONA_STANDING_INTENT_PATH`). When the Reviewer has classified a **(B) structurally-can't** gap (ADR-344 §3–4) and re-raised it as standing intent, the band surfaces it as the **deepest to-do**: *"This operation cannot reach its mandate as configured — [the Reviewer's stated gap]. It has offered: [author a compose organ within the floor] · [or feed it drafts]. Decide →"* This is the literal "long-standing updated todo" — and it is *more* load-bearing than any single proposal, because it is the operation telling the operator it cannot reach its own mandate. When `standing_intent.md` is empty/absent, the band shows the on-track state (Read 1 only).

**Frame — a shortfall is a to-do, never a block (ADR-345 autonomy-as-witness).** The band's copy obeys the witness reframe (`ADR-345 §4`; `permission.py:162-256`): a gap is *the operation surfacing what it decided it needs*, not *the agent stuck waiting for permission*. The autonomous operation always works the full job; the band shows where a standing decision is owed to the operator, framed as Decide, consistent with QUEUE = "decided, awaiting witness" — never "blocked."

### What the band is NOT
- **Not the Reviewer's per-wake scratchpad.** No turn-level plan, no streaming task checklist — that is the Claude-Desktop affordance this ADR explicitly declines (§1 grounding correction). The band is tenure-state, refreshed when substrate changes, not a live-typing surface.
- **Not a new computed record.** It reads `_expected_output.yaml` + `standing_intent.md` + (for the on-track line) recent execution already available to the pane. It does **not** persist an owed-vs-actual artifact (ADR-344 §7).
- **Not a writable persona surface.** The operator reads the standing gap and acts via the *offered* affordances (Decide → approve the Reviewer's compose-organ proposal, or open Expected Output to declare a contract). The operator never edits `standing_intent.md` — that is persona-region, Reviewer-authored (ADR-320; ADR-275 D1).
- **Not a Feed change.** ADR-289's bubble-free typed-event Feed body is untouched.

## 4. Why Notifications → To do is the right home (not the Feed, not a new surface)

- **The Feed is the *record*; the band is the *standing state*.** ADR-289 D1 makes the Feed a chronological typed-event timeline — beats that happened. The standing obligation is not a beat; it is the *condition the beats serve*. Putting it in the Feed would either bury it (scrolls away — the exact failure ADR-344 §4 names for one-shot surfacing) or violate the timeline grammar. The "To do" pane is where *open decisions* live; an unmet obligation is the deepest open decision.
- **DP29 "compose few" forbids a new surface.** A dedicated "Standing" launcher tile would be breadth-for-its-own-sake (the anti-pattern ADR-349 D6 just removed by dissolving Utilities). The obligation composes onto the act it belongs to — Decide.
- **The "two zooms" already exist.** ADR-349 D2 made the top-bar Attention bell and the Notifications surface "one object at two zooms." The Standing band gets a one-line glance in the bell's To-do summary (e.g. *"1 standing gap + 2 proposals"*) and full render in the surface — reusing the existing glance/surface pair, no new chrome.

## 5. Scope boundary
- **FE-only.** No new primitive, route, table, or column (ADR-344 §7 preserved). The band is a new component in the existing `resolve` pane reading two existing substrate paths through one existing parser (`expected-output.ts`) and one new trivial `standing_intent.md` reader (prose → render; no schema).
- **No backend reasoning change.** The Reviewer's wake-time derivation + (A)/(B) classifier (ADR-344 §3) is unchanged; this ADR renders its *durable output* (`standing_intent.md`) and the *declared contract*, nothing more.
- **Does not author or edit persona substrate** (ADR-320 / ADR-275 D1) — render-only of `standing_intent.md`.
- **Does not touch the Feed body, the Conversation rail, or any transport** (§2) — the streaming/realtime layer is already complete.
- **Does not change the consent gate** (ADR-307) — the band sits above `action_proposals`; the proposals still flow through the same one queue.

## 6. Implementation sketch (for the FE pass that follows this Proposed)
- `web/components/queue/StandingBand.tsx` (new) — reads `governance/_expected_output.yaml` (via `expected-output.ts::parse` + `formatExpectedOutputSummary`) + `persona/standing_intent.md`; renders the contract line + (when open) the standing-gap to-do with the Reviewer's offered affordances; absent-contract → derived-default copy + "Declare" link to `ExpectedOutputCard`.
- `web/app/(authenticated)/notifications/page.tsx` — mount `StandingBand` at the head of the `resolve` pane render (above `QueueBody`).
- `web/components/shell/AttentionCenter.tsx` — extend the To-do glance summary to count an open standing gap alongside pending proposals (the bell zoom of the same object, ADR-349 D2).
- Backend read surface: confirm the existing pane data load exposes `governance/_expected_output.yaml` + `persona/standing_intent.md` to the client (both are ReadFile-reachable; no new endpoint if the pane already hydrates workspace files — verify and add a thin read if not).
- `web/test/adr350-standing-band.test.ts` (new) — three states: (i) explicit contract + no gap → on-track line only; (ii) explicit contract + open (B) gap → standing to-do with offered affordances; (iii) absent contract → derived-default copy + Declare link. Assert no write affordance on `standing_intent.md`.
- **Dimensional classification:** **Channel** (Axiom 6 — a new standing *register* on an existing surface) projected through **Purpose** (Axiom 3 — the operator's "is my operation on track" act). Renders **Identity** (the Reviewer's standing intent) and **Substrate** (the declared contract); computes neither.

## 7. Receipts

| Claim | Receipt |
|---|---|
| Standing obligation is derived every wake, never persisted | ADR-344 §3 + §7 ("No new primitive, schema, or table") |
| The (B) gap is re-raised as *standing* intent, not a one-shot note | ADR-344 §4 item 2 ("standing — re-raised each wake … via `standing_intent.md`") |
| `standing_intent.md` path + region | `PERSONA_STANDING_INTENT_PATH = "persona/standing_intent.md"` (`workspace_paths.py:127`); persona-region, Reviewer-authored (ADR-320) |
| Expected-output contract path + parser exist | `GOVERNANCE_EXPECTED_OUTPUT_PATH = "governance/_expected_output.yaml"` (`workspace_paths.py:90`); `expected-output.ts::parse` (`:124`) + `formatExpectedOutputSummary` (`:224`) |
| Derivation is default; explicit declaration is opt-in | ADR-344 §2 ("derivation is the default, so every existing workspace inherits the posture without a substrate migration") |
| A shortfall is a Decide, never a block | ADR-345 §4 ("QUEUE … means 'the agent decided, and this beat surfaces before it binds'"); `permission.py:162-256` |
| Notifications → To do (`resolve`) is the consent-gate pane | `notifications/page.tsx:45-54,86-132`; `QueueBody.tsx`; ADR-349 D2 (panes `resolve`/`understand`/`tune` unchanged) |
| Transport for realtime + async is already complete | ADR-289 (grammars) + ADR-316 (rail) + `use-session-messages-realtime.ts` (Supabase Realtime push) |
| A new surface would violate "compose few" | ADR-340 D1 / DP29; ADR-349 D6 (Utilities dissolved as breadth-for-its-own-sake) |
