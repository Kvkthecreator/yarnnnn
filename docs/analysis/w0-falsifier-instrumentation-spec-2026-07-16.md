# W0 — The ADR-457 D8 Falsifier Instrumentation Spec

**Status**: Spec, ready to build. Doc-first; the code is one field + three call sites + one read-only query module (§5).
**Date**: 2026-07-16
**Owner-pass**: ADR-457 D8 ("Falsifiers — instrumented, not vibes"), sequenced as **W0** by [ADR-460](../adr/ADR-460-agents-one-concept-independent-facts-one-gate.md) §8 — it lands **before** the settle verb.
**Relates to**: ADR-457 D3/D8 · ADR-460 §8 (the sequence) · ADR-411 D1/D5 (the lane) · ADR-440 D3 (the Studio binding) · ADR-450 D3 (the derive binding) · ADR-291/396 (the one cost ledger — this spec adds **no second ledger**) · DP29 (derived-never-stored).

---

## 1. Why W0 is first, and why its window closes

ADR-457 D8 declares three falsifiers to be evaluated 60–90 days after the chat waves ship. **Falsifier 2 is "the settle verb goes unused after honest staging."** That falsifier is only meaningful against a **pre-settle baseline** — how the desk was used *before* the verb existed. Instrument after settle ships and the baseline is unrecoverable: there is no way to reconstruct "what did usage look like before" from a ledger that wasn't recording the distinction.

The subtler trap, and the reason this is not merely "do it early": **an unbuilt verb reads null, and null is not evidence of non-adoption.** If a future session queries settle-usage today it gets zero — and zero is indistinguishable from "shipped and ignored," which is exactly what falsifier 2 fires on. Instrumenting first is what makes the eventual zero *mean* something.

## 2. The premise check — D8 is **half right** (the finding)

D8 says the three signals are *"all readable from `execution_events` + session counts, no new telemetry system."* Verified against the live DB (2026-07-16). **The claim holds for two falsifiers and fails for one**, and the failure is narrow and fixable.

**Receipt A — the ledger cannot tell chat from Studio:**

```
slug  | mode     | trigger_type | rows | first      | last
lane  | judgment | addressed    |  55  | 2026-07-06 | 2026-07-15
```

Every chat turn **and** every Studio bound-lane turn writes `slug="lane"`. They are the same row. Falsifier 1 ("sessions concentrate in Studio and chat is used only as a command line") requires telling them apart. **As of today, falsifier 1 is not measurable.**

**Receipt B — the fact exists, one table over:**

```
session_type | model  | bound_studio | derive | count
lane         | sonnet | t            | f      |   5     ← Studio bound lanes
lane         | sonnet | f            | f      |   1     ← a real chat lane
lane         | sonnet | t            | t      |   1     ← a derive lane
```

`chat_sessions.context_metadata->'lane'->>'artifact_path'` **is** the surface discriminator (ADR-440 D3: "a lane with a binding is a *studio* lane"). The code knows which surface asked, at the call site, and throws the fact away at the ledger.

**Receipt C — the two tables cannot be joined.** `\d execution_events` has **no session/lane id column**. `agent_run_id` exists but `grep -c agent_run_id api/services/lane_runner.py` → **0**: lanes never write it. The surface fact lives in `chat_sessions`; the turn/cost fact lives in `execution_events`; **nothing connects them.**

**Receipt D — falsifier 3 IS measurable today**, from a third home — the revision ledger's attribution:

```
authored_by                                        | count (30d)
operator                                           | 144
yarnnn:mcp:claude-desktop                          |  13
yarnnn:mcp:Claude                                  |   6
member:2abf3f96-… via anthropic/claude-sonnet-4-6  |   6
```

`yarnnn:mcp:*` (the hum) vs `member:* via *` + `operator` (the desk) is exactly falsifier 3's cut, already recorded. **No change needed.**

**Conclusion:** the three falsifiers have **three different data homes** — and only one of them needs code.

| | Falsifier | Home | Status |
|---|---|---|---|
| **1** | chat-as-command-line-only | `execution_events` ⋈ `chat_sessions` | **BLOCKED** — no join key (§3 fixes) |
| **2** | settle unused | `execution_events` (a settle slug) | **PENDING** — needs settle to exist; baseline needs §3 |
| **3** | MCP ≫ desk | `workspace_file_versions.authored_by` | **MEASURABLE NOW** — query only |

## 3. D1 — The fix: one nullable column, three call sites

**Add `execution_events.session_id uuid NULL`** (migration). It is the join key that reconnects a metered turn to the surface that asked for it.

Why this and not the alternatives:

- **Not a `surface` enum column.** That would store a *derived* fact (DP29: derived-never-stored). "Is this a Studio lane" is derivable from the session's binding; storing the derivation invites the two copies to disagree. Store the **identity** (which session), derive the **class** (which surface) at read time.
- **Not a second ledger.** ADR-396's DOUBLE-CHARGE INVARIANT: `get_effective_balance` sums ONE ledger. This adds a nullable FK to the existing row; it does not add a spend surface. Byte-identical cost behavior.
- **Not `agent_run_id` reuse.** That column means "an agent run" and lanes are not agent runs; overloading it would make two concepts share a column — the exact dilution ADR-460 just spent an ADR removing.

**Call sites (3):** `record_execution_event(session_id=...)` gains the kwarg; `lane_runner.py` passes the lane id at both of its two `record_execution_event` calls (streaming + non-streaming, lines ~457 and ~641). The `session_id` is already in scope at both.

**Backfill: none.** The 55 pre-existing `lane` rows stay NULL and are honestly unclassifiable — they predate the instrument. **Do not guess them.** A NULL means "recorded before W0," which is a true statement; a backfilled guess would be a fabricated baseline, which is the precise thing this spec exists to prevent.

**Cost:** one nullable column, one kwarg, two call sites, zero behavior change, zero new tables.

## 4. D2 — The surface taxonomy (derived at read time)

From the joined row, the surface derives — **kernel-named, never guessed**:

| Surface | Derivation |
|---|---|
| **think** (chat) | `session_type='lane'` AND `artifact_path IS NULL` AND `derive_recipe IS NULL` |
| **make** (Studio bound lane) | `session_type='lane'` AND `artifact_path IS NOT NULL` AND `derive_recipe IS NULL` |
| **derive** | `derive_recipe IS NOT NULL` (ADR-450 D3) |
| **steward** | `session_type='thinking_partner'` (the ambient rail, ADR-454) |
| **unclassified** | `session_id IS NULL` — pre-W0 rows. Reported as its own bucket, **never folded into another.** |

The `unclassified` bucket is load-bearing: a metric that silently drops unknowns reads as coverage it doesn't have. It shrinks to irrelevance on its own as post-W0 rows accumulate.

## 5. D3 — The read surface: a query module, not a dashboard

**`api/services/falsifiers.py`** — read-only, no new storage, no UI. Three functions, one per falsifier, each returning a plain dict with its own counts + window. Callable from a script; a surface later if wanted.

- `falsifier_1_surface_mix(client, workspace_id, days)` → turns per surface (§4) + the `unclassified` count. **Fires when:** think-surface turns collapse toward zero while make holds. *Note the honest asymmetry: this measures turns, not sessions — D8 says "sessions concentrate," and turns are the better proxy (a session left open isn't use). Documented, not silently substituted.*
- `falsifier_2_settle_adoption(client, workspace_id, days)` → settle acts vs think-turns, i.e. the rate at which thinking becomes record. **Pre-settle it returns `settles=0, staged=False`** — the explicit "the verb does not exist yet" signal, so a zero can never be misread as rejection. Flips to `staged=True` when the settle slug first appears.
- `falsifier_3_hum_vs_desk(client, workspace_id, days)` → `authored_by` split: `yarnnn:mcp:*` (hum) vs `operator` + `member:*` (desk), from `workspace_file_versions` (Receipt D). **Works today, no dependency on §3.**

**Discipline:** every function reports its **window** and its **unclassified/unstaged** count alongside the number. A falsifier that can't say what it didn't see is a vibe with a decimal point.

## 6. What this does NOT do

- **No new telemetry system** (D8's constraint, honored — one nullable column on the existing ledger).
- **No second cost ledger; no change to `cost_usd`, `get_effective_balance`, or the ADR-396 invariant.** Cost behavior byte-identical.
- **No UI.** A script-callable module. Falsifiers are read at evaluation time (60–90d), not watched.
- **No backfill, no guessing** (§3).
- **No judgment on the bet.** It builds the instrument; it does not read it. Reading it is the 60–90d pass.

## 7. Build order

1. Migration: `ALTER TABLE execution_events ADD COLUMN session_id uuid NULL;` (+ index `(workspace_id, session_id)` if the read proves slow — measure, don't presume).
2. `telemetry.record_execution_event(session_id=None)` kwarg → row.
3. `lane_runner.py` — pass the lane id at both call sites.
4. `services/falsifiers.py` — the three read functions.
5. Gate `api/test_w0_falsifiers.py`: surface derivation over fixtures (all five §4 classes incl. `unclassified`); falsifier 2 returns `staged=False` pre-settle; falsifier 3 splits hum/desk correctly; **no second ledger** (assert `get_effective_balance` unchanged — the ADR-396 ratchet).
6. Prod probe: run all three, receipt the numbers into this file's §8.

## 8. Receipts (built 2026-07-16)

**Gate**: `api/test_w0_falsifiers.py` — **21/21 PASS** (surface derivation over all five classes incl. `unclassified`; the derive-wins-over-make ordering; the join key end-to-end; falsifier 2's `staged` separation; the ADR-396 read-only ratchet).

**Migration 216**: applied to prod — `ALTER TABLE` / `COMMENT` / `CREATE INDEX`, no backfill.

**Live probe** (workspace `d5b9029b`, 90d window, `read_all`):

```json
"falsifier_1": { "turns_by_surface": { "think": 0, "make": 0, "derive": 0,
                                       "steward": 0, "unclassified": 55 },
                 "classified_turns": 0, "unclassified_turns": 55 }
"falsifier_2": { "staged": false, "settles": 0, "think_turns": 0,
                 "settles_per_think_turn": null }
"falsifier_3": { "hum_writes": 7, "desk_writes": 110, "system_writes": 238,
                 "hum_to_desk_ratio": 0.064 }
```

**Reading the receipts — the instrument is honest about its own blindness:**

- **Falsifier 1: `unclassified: 55`, classified 0.** Correct, not broken. All 55 lane rows predate migration 216 and are genuinely unclassifiable; the instrument says so rather than guessing. This number is the **proof the no-backfill decision was right** — had we guessed, falsifier 1 would today report a confident surface mix derived from nothing. It starts classifying at the next lane turn and this bucket decays into irrelevance.
- **Falsifier 2: `staged: false`.** The verb does not exist. This is the distinction the whole W0-before-settle sequencing exists to create: the zero is labelled "not built yet," so it can never be misread as "shipped and ignored."
- **Falsifier 3: hum/desk = 0.064** — a REAL signal, available today with no dependency on 216. **The hum does not dwarf the desk; the desk out-writes it ~16:1** (110 desk vs 7 MCP). Note `system_writes: 238` dominates both — the operation's own machinery, correctly reported as neither hum nor desk. *This is a reading of an N=1 dogfood workspace, not of "real users" (D8's phrasing) — it does not fire the falsifier, it establishes the baseline the 60–90d pass will read against.*

**Not covered**: a live post-216 lane turn writing a non-NULL `session_id` end-to-end (needs a real chat turn against the deployed API). The path is gate-asserted at every hop; the prod confirmation rides the next chat smoke.

## 9. One-line statement

**Three falsifiers, three data homes: falsifier 3 already works off attribution, falsifier 1 is blocked on a missing join key between the metered turn and the surface that asked for it, and falsifier 2 needs both that key and a verb that does not exist yet — so W0 is one nullable column, two call sites, and three read functions that always report what they could not see.**
