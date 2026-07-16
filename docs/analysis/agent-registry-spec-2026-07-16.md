# The Agent Registry — Spec

**Status**: Spec, ready to build. Implements [ADR-460](../adr/ADR-460-agents-one-concept-independent-facts-one-gate.md) **D4** (the registry) + **D3.a** (the structural cliff), sequenced as step 3 by ADR-460 §8 — after settle, before cast-in-a-room.
**Date**: 2026-07-16
**Relates to**: ADR-460 (the whole model) · ADR-411 D1/D5 (`LANE_MODELS` — the seed this grows) · ADR-450 (`DERIVE_RECIPES` — the pattern's other instance) · ADR-402 (routing is kernel data, not identity) · ADR-222 (kernel names the category, never the instance) · ADR-408 D2 (the not-a-principal claim, preserved on the vector).

---

## 1. What this is, in one line

> **Replace the model dropdown with a person.** `LANE_MODELS` grows from `{id, label, vision}` into a set of **named, pre-configured Agents** — and the member picks *who to talk to*, not *which engine to route to*.

The operator's cut, verbatim:

> "LLM-routing is simply NOT a laymen intuitive concept. Pre-configured Agents IS... yarnnn's internal system and codebase is about providing the base-default agents... Agents are agents, chat rooms are chat rooms, Agent configurations are separate."

## 2. The gesture this replaces (the receipt)

`GET /api/lanes` serves `models: [{id, label, vision}]` from `LANE_MODELS`, and `ChatSurface.tsx:284` renders it as a `<select>`:

```
Claude Sonnet │ Claude Haiku │ GPT-4o mini │ GPT-5 │ Gemini Flash │ Gemini Pro │ DeepSeek
```

**That is the spec sheet.** It asks the member to know which engine is good at what — expert-mode ceremony, and exactly the "command line" feel ADR-457 D8's falsifier 1 warns about. Choosing between "Gemini Pro" and "GPT-5" is a question nobody outside this industry can answer, and it is asked *before the first message*, when the member knows least.

The replacement asks a question anyone can answer: **who do you want to work with?**

## 3. D1 — The row shape

`services/agents_registry.py::KERNEL_AGENTS` — kernel constants, the ADR-450 pattern:

```python
{
  "slug":          "scout",              # stable id (the API/persistence key)
  "name":          "Scout",              # the operator-facing name
  "blurb":         "Digs through…",      # ONE line: what they're for, in the member's words
  "icon":          "compass",            # lucide key — the face
  "model":         "gemini/gemini-2.5-flash",   # ← the Mechanism fact, now BEHIND the name
  "posture":       "…",                  # the turn-time overlay (their working character)
  "token_profile": 4096,
}
```

**No `tools` field in v1.** ADR-460 D4 named `tools` in the row shape, and the build says defer it: every lane gets the same five file verbs (ADR-411 D3), no Agent needs a different set yet, and a per-Agent tool scope with one value is a field that lies about being a choice. It lands when a second value exists. *(Spec-vs-build divergence recorded honestly rather than shipping a decorative field.)*

**NO authority field — the ADR-460 D3.a cliff, made structural.** There is no key for consequential authority, and its absence is enforced by the gate. Kernel Agents are addressed-only hands *by construction*: the authority is **unrepresentable**, not merely unset. An Agent that would take consequential action is not a registry row with a flag flipped — it needs the ADR-307 gate, a mandate, an autonomy dial, and the record. **A future session that adds an authority field to this registry has violated ADR-460.** This is that ratchet.

## 4. D2 — The base set: "provide enough, not the most"

The ADR-420 §10 discipline (`LANE_MODELS`' own rule: *"one lane per reason a user would leave, not one per model that exists"*), applied one level up. **Agents are named for the WORK, never for the engine** — the engine is the fact behind the name.

| Agent | For | Engine | Why this engine |
|---|---|---|---|
| **Sonnet** *(the default)* | thinking through a problem, writing, judgment | `anthropic/claude-sonnet-4-6` | the frontier reasoner; the current default lane model |
| **Scout** | fast lookups, quick reads, "what does this say?" | `gemini/gemini-2.5-flash` | fast + cheap; the throughput lane |
| **Critic** | pressure-testing an idea, finding the hole | `openai/gpt-5` | a genuinely different training lineage — the value is the *disagreement*, which is the whole reason a second vendor is on the desk |

**Three, not seven.** Seven engines is a spec sheet; three characters is a team. The remaining `LANE_MODELS` rows stay routable (the registry does not delete them — §6) but leave the picker.

**Naming honesty (the one live tension):** "Sonnet" is an engine name, and this spec just argued engines aren't identities. It stays as the default's name for one reason — the operator knows it and it is the workspace's incumbent default; renaming the thing you already talk to is a cost with no payoff today. **Named as a wart, not defended.** Scout/Critic are named for their work; if a rename pass ever runs, the default is the row to fix.

## 5. D3 — What an Agent is NOT (the boundaries that keep this cheap)

- **Not a principal.** Attribution stays **`member:{user_id} via {model}`** — byte-identical to today. No `principal_grants` row, never on the ADR-431 roster. The face is an Agent; the ledger says your hands. *(ADR-408 D2's load-bearing claim, preserved on the vector.)*
- **Not standing intent.** Fires only when addressed. No wake sources, no mandate, no autonomy dial (§3).
- **Not a persona-agent seat** (ADR-382 / Rung 2). The distinguishing fact is the ADR-307 consequential gate, not the presence of a proper noun — a named preset is not a seat.
- **Not a new object.** An Agent slug is a value in `lane_meta`; the lane is unchanged. No table, no migration.

## 6. D4 — Persistence: the slug rides beside the model, and the model stays authoritative

`lane_meta` gains `agent: "scout"`. The `model` key **stays and stays authoritative** — every runtime path (`run_lane_turn_stream`, settle, the ledger, BYOK resolution, the unpriced gate) keys on `model` and none of them change.

Why both, rather than deriving the model from the slug at turn time:

- **Existing lanes keep working.** The 7 live lanes have `model` and no `agent`. They resolve to their model exactly as today and simply render an engine label — no backfill, no guessing (the W0 lesson).
- **A registry edit can't rewrite history.** If `Scout`'s engine changes from Flash to Pro next month, a lane created as Scout-on-Flash *ran on Flash*, and its ledger rows say Flash. Deriving at turn time would retroactively lie about what ran. **The slug is the face; the model is the fact; the fact is recorded.**
- **The `posture` is composed at turn time from the slug** (the ADR-411 D6 derived-never-stored pattern) — that one *should* follow the registry, because it is not a historical fact about what ran; it is how the Agent works *now*.

## 7. D5 — The API + FE change

**API** — `GET /api/lanes` gains `agents: [{slug, name, blurb, icon}]` beside the existing `models`. **`models` STAYS** (D6 keeps every model routable; the Files/Studio bound-lane paths and the `model` filter facet read it). `POST /api/lanes` accepts `agent` **or** `model`; `agent` resolves to its model server-side and both land in `lane_meta`. An unknown slug is a 422 (the ADR-450 precedent: an unknown recipe is a caller bug).

**FE** — the `<select>` of engines becomes a row of **Agent chips** (icon + name), with the blurb as the title. The lane's chip shows the Agent's name, not the engine's. *(The engine stays legible — a member who wants to know what's under Scout can see it in the lane detail; the point is that they are never *asked* to choose it.)*

## 8. Build order

1. `api/services/agents_registry.py` — `KERNEL_AGENTS` + `get_agent(slug)` + `list_agents()` (the `DERIVE_RECIPES` module shape, verbatim).
2. `routes/lanes.py` — `agents` on the envelope; `agent` accepted at create → resolves to model + lands in `lane_meta`.
3. `lane_runner.py` — compose the Agent's `posture` at turn time from `lane_meta["agent"]`, beside the existing Studio/derive overlays.
4. FE — `agents` on the payload; chips replace the `<select>`; the lane chip names the Agent.
5. Gate `api/test_agent_registry.py`: **the D3.a ratchet** (no authority-shaped key in any row, asserted against a banned-name list); every Agent's model is in `LANE_MODELS` and is priced (the ADR-439 rule); attribution is still `member:… via {model}`; Agents are not principals; a lane with no `agent` still runs (the no-backfill path).
6. Prod probe: create a lane as an Agent, run a turn, confirm the ledger reads `member:… via {the Agent's model}`.

## 9. Receipts (built 2026-07-16)

**Gate**: `api/test_agent_registry.py` — **43/43 PASS**, led by the D3.a ratchet (14 banned authority-shaped words checked against every row's keys **and** against `AGENT_ROW_KEYS` itself; plus "every row carries ONLY the allowed keys," so a new key is a deliberate act that trips the gate). Siblings: adr411 · adr440 · settle 41/41 · w0 21/21 all green. **`test_adr412_chat_surface` FAILS — pre-existing, reproduced on clean HEAD in a worktree** ("the Brand pane still gates on operation/ coverage" — another lane's, untouched by this work).

**FE**: `✓ Compiled successfully` in a clean HEAD worktree — **after the build caught a real gap** the gate could not: `api.lanes.list()`'s return type didn't declare `agents`, so the FE's `LaneData` cast failed to typecheck. Fixed in the client. *(This is the `next build`-not-`tsc` lesson paying for itself again.)*

**Live probe** — the chooser, the posture, a real turn, the ledger:

```
=== the chooser payload (what the member sees) ===
  Sonnet   brain    — Thinks a problem through with you — writing, judgment, hard calls.
  Scout    compass  — Digs through material fast — lookups, quick reads, what does this say?
  Critic   swords   — Pressure-tests an idea — finds the hole before it costs you.

=== a real turn as Critic (engine behind the name: openai/gpt-5) ===
  Q: "In one sentence: is 'we should ship fast' a good principle?"
  A: "No—on its own it optimizes for motion over value, degrades quality and trust,
      piles up hidden debt, and usually slows you later unless constrained by clear
      quality gates, validation, and rollback."

=== the ledger ===
  slug=lane  model=gpt-5  3896 in / 562 out  $0.010490
```

**What the receipts prove:**
- **The Agent is real, not a label.** Critic answered like Critic — a flat "No—" and the strongest objection, not a balanced survey. The posture composed from the *slug* at turn time and visibly changed the output's character.
- **The face/fact split holds end-to-end.** The member picked "Critic"; the ledger recorded `gpt-5`. Nobody chose an engine; the engine is still exactly what got recorded (§6's whole argument, live).
- **Not-a-principal is unchanged.** Attribution reads `member:2abf3f96… via openai/gpt-5` — byte-identical shape to pre-registry lanes.

**A false alarm worth recording**: the first probe returned empty text and no `gpt-5` ledger row. Not a bug — `MODEL_ROUTER_ENABLED` is off in the local `.env`, and `run_lane_turn` correctly refused with `{"error": "router_disabled"}`. The turn is *supposed* to refuse. Re-probed with the flag on. *(Chasing this was right: an empty result that looks like a silent failure must be explained, not assumed benign.)*

**Not covered**: the FE chips under a human click (compiles clean; the picker wants an eye), and per-workspace Agents (deliberately unbuilt — the ADR-450 later-widening).

## 10. One-line statement

**The Agent registry is the model dropdown with a person in front of it: three named characters over three engines, the slug for the face and the model for the fact, no field for authority — and nobody routes, because you just talk to someone.**
