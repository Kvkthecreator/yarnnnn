# The Supervisor, from first principles — an audit of whether the architecture can carry it

> **Status**: evaluation record (Hat B). A finding recommends; the fix lands under Hat A, by ADR.
> **Date**: 2026-09-20 · HEAD `2516a6a` · production re-queried the same day.
> **Prompted by** — operator, 2026-09-20: *"the prior session is leaning too heavily on prior ADR decisions
> instead of approaching the supervisor concept from first principles … a rather half measure approach where
> we really should be developing towards a concept that actually achieves the intent and objective of the
> supervisor and its supervisor app … long standing, orchestration from intake to compose or execution and the
> cockpit/dashboard (app) to manage it."*
> **Verdict**: the thesis holds. §2 is the receipt, §3 shows why it happened, §4–5 are what to build.

This is the second time the operator has made this correction on this arc (the first:
`the-supervisor-and-the-room-2026-09-18.md` §13). It is recorded as method, not only as a finding: §3.

---

## 1. The standard — derived from the chair, not from the canon

Strip every ADR. A member with ongoing work says: *"I have work that keeps happening. Things come in — from
my systems, the web, what I and my AIs drop here. Something gets made, or something gets done. Over and over,
and it should get better. Set it up once, show it to me in one place, tell me what needs me."*

That sentence has five load-bearing parts. A Supervisor that lacks one is not a smaller Supervisor; it is a
different, lesser thing:

| # | Capability | The member's words |
|---|---|---|
| 1 | **Intake** | *things come in* — from outside **and** from what is already in my workspace |
| 2 | **Flow** | *over and over* — one piece of work feeds the next; a chain, not a list |
| 3 | **Output** | *something gets made* (compose) *or gets done* (execute) |
| 4 | **Attention** | *tell me what needs me* — fed by the work itself |
| 5 | **Cockpit** | *show it to me in one place* — what exists, what ran, what each run produced, what it cost |

---

## 2. Expected vs observed — the scorecard

Every row verified against code or production on 2026-09-20; none is taken from a doc's claim.

| # | Expected | Observed | Receipt |
|---|---|---|---|
| 1 | Work reads the world and the workspace | **The world only, and narrowly.** A source is an `http(s)` URL or a `{connector, selector}` slice for exactly three platforms. **A workspace file or folder is not expressible** — uploads, what an outside AI saves over MCP, another piece of work's output, the accumulated commons: all unreadable unattended. One unrecognised source invalidates the whole declaration | `_classify_sources` / `_is_http_source` / `_is_connector_source`, `standing_work.py:230-282`; `CONNECTOR_CAPTURE_BINDINGS` = slack · notion · github; attached MCP → `no_binding`, `connectors.py:324-327` |
| 2 | One piece of work feeds the next | **No flow exists.** A declaration cannot name another's target, so nothing chains. Each declaration is an island | same predicate; the write is confined to one leaf, `_assert_standing_write` |
| 3a | Compose — documents, decks, posts, images | **One `.md`/`.csv`/`.json`/`.txt`, whole-file, ≤ 4096 output tokens** (~12–16 KB) — an eighth of what the same agent authors attended (32 000). Deck · post · image targets refused `unsupported_format` | `SUPPORTED_FORMATS`, `_STANDING_MAX_TOKENS`; driven: `deck.html`/`post.html`/`hero.png` → `unsupported_format` |
| 3b | Execute — a send, a publish, an update | **Nothing.** A run ends in a file or `NO_CHANGE`. It cannot even *propose* an act for the member to bind, though the proposal queue is live (`action_proposals`, `ProposeAction`, `POST /proposals/{id}/approve`) and ESSENCE Loop 2 step 3 promises exactly that | `run_standing_sweep` is a straight line: gate → fetch → one derive → write → meter |
| 4 | Attention fed by the work | **`needs-you` reads chat @-mentions.** A failed run, a refused shape, an exhausted balance, a declaration in a problem state — none reaches the band. The band and the work do not touch | `supervisor_state._needs_you` → `mentions.list_mentions` only |
| 5 | A cockpit over the work | **A roster and a form.** "Runs" are rows of the COST ledger — step · status · cost — with **no link to the revision the run wrote**, so the cockpit cannot show what a run produced. No view of how work relates (there is no relation to view) | `_recent_runs` selects `slug, status, created_at, error_reason, cost_usd` from `execution_events` |
| — | The Supervisor agent knows its job | **Its job text never mentions standing work** — zero occurrences of *standing · declar · schedule*. It still carries ADR-656's subject (threads, splitting asks). ADR-658 replaced the surface's vocabulary and left the resident's | `build_supervisor_posture()` driven and counted |
| — | Production | **0 live declarations, 0 index rows.** The only runs since 2026-09-06 are the click-pass's own | queried 2026-09-20 |

**Score: the door half of (5), and a thin slice of (1) and (3a).** What shipped as ADR-658 is a well-made CRUD
surface over a lane whose unit is *"keep one short text file current from the outside world."* That unit cannot
express *"manage my shop"*, the ADR's own motivating sentence (its §7.1 had to retract the Shopify example).
The door is sound and is kept. The room behind it is the half measure.

---

## 3. Why it happened — law versus habit

ADR-658 asked *"what does the canon permit?"* and built exactly that. The better question is *"which of these
limits is a law?"* Read for their **stated reasons**, almost none are:

| Limit | Decided | The recorded reason | What it is |
|---|---|---|---|
| Worker derived, never assigned | ADR-596 D1 · 460 D3.a | authority on a being is unrepresentable | **LAW** (Axiom 2) |
| No agent commands an agent | ADR-596 D2 · 626 D4.a | *"agents do not orchestrate agents; declarations do"* | **LAW** — and note what it *permits* |
| No consequence binds unwitnessed | DP23 · ADR-307/405 | the member is never structurally absent | **LAW** |
| No member credential without the member | ADR-577 · 645 D1 | a credential carries identity; attribution is the moat | **LAW** |
| State lives in files, not per-run rows | Axiom 1 | computation is stateless | **LAW** |
| One drain loop, one envelope, one write path | DP7 · ADR-639 D1 · 209 | singular implementation | **LAW** (constrains *how*) |
| Toolless unattended turn | ADR-639 §1.3 | *"a clock and a credential never meet"* | guards **credentials**, not cognition — a read-only, substrate-only toolset collides with no stated rule (DP23: *"reads … never gate"*) |
| One round per run | ADR-580 D2 | — | a *consequence* of toolless; never ruled on its own |
| Sources are URL or connector only | ADR-569 · 582 D6 | — | **never ruled.** A workspace source was not refused; it was not thought of. Named as a gap three times (ADR-656 D5, the handoff, the 09-18 analysis §8) and built by no one |
| md · csv · json · txt only; one per folder | ADR-569 D1/D2 | *"refused loudly, until a real case demands more"* | **demand-pull deferral**, in its own words |
| A new file each run (a generator) | ADR-603 D1 · 639 D6 | *"named, not solved — needs its second instance"* | **deferral** |
| Cron + manual only | Axiom 4 · ADR-428 · 632 · 603 D5 | $0.22 no-op wakes · a dormant stack that could still spend · a clock with no contract | **three cost incidents**, canonised. The surviving *principle* is "no schedule without a contract" |
| No unattended outbound | ADR-645 §7 · 628 D8 | — | **precondition-gated, successor already designed** (workspace-owned identity; `system:publish-{platform}`) |

**The real prohibitions are one family: nothing on a being, nothing bound unwitnessed, nothing signed by the
wrong person.** Everything else that makes the lane narrow is a deferral that says so, a consequence of the
credential guard, or a scar from a cost incident — and FOUNDATIONS itself points the other way (Axiom 5, *the
loosening rule*: *"Mechanism loosens over time … gated by grants, the witness gate and contracts"*; Open
Question 3 asks when the next loosening step comes).

⚠️ **The method finding.** In a pre-user product, demand-pull (ADR-337 D6) answers every proposal with *"nobody
asked"* — so applied to the product's own core loop it is a ratchet that only tightens. Production holds zero
declarations; read as demand it says *build nothing*, read as a defect it says *the unit is not worth
declaring*. §13.1 of the 09-18 analysis already ruled which reading is admissible. ESSENCE v20→v21 shows the
same ratchet at the top: *"an operation that runs in your absence"* was revised **down** to *"files that stay
current on a schedule"* to match the implementation.

---

## 4. The concept — orchestration is AUTHORED, not performed

The five capabilities do not need an orchestrator agent, a task table, or a wake stack — the three things the
canon was right to delete. They need one idea the canon already holds and never applied here:

> **The substrate is the bus** (FOUNDATIONS Axiom 1). Standing work is `make` for knowledge work: a **target**,
> its **prerequisites**, a **recipe** (the contract + the derived worker), and a clock. Today a prerequisite may
> only be the outside world. Let it be a workspace path, and the rest follows.

- **Intake** — a source may be a file or a folder: `inbound/uploads/`, what an outside AI saved, a connector's
  landed captures, any part of the commons. Pre-gathered mechanically, so the turn stays toolless and the
  credential guard is untouched.
- **Flow** — A's target is B's source. Orchestration is a **graph of declarations over files**: *capture →
  digest → report*. No agent commands an agent (ADR-626 D4.a, to the letter: *declarations do*). The graph is
  derived from the declarations at read time — no store, no second authority.
- **Pace** — a run whose prerequisites have not moved since its last write is skipped mechanically, at **$0**,
  *before* the paid turn. This is `make`'s one rule, and it is ADR-580 D2's pace law generalised. It stays
  schedule-drained, so **Axiom 4 is not amended** — yet a tight schedule now behaves like an arrival trigger
  without being one, and it removes today's waste (every tick of a prose declaration is a paid turn whether or
  not anything changed; the no-op is detected *after* the spend).
- **Execute** — a declaration may end in a **proposed act** (*send this brief to #team*), which waits in
  `needs-you`. The member's click binds it, with the member's credential, the member present — which is the
  publish route as it already works. No unattended outbound is needed for this, and ESSENCE Loop 2 step 3
  becomes true for the first time.
- **Attention** — `needs-you` reads the work: a refused run, a problem declaration, a waiting proposal.
  Derived from the roster and the ledger; no new store.
- **Cockpit** — the roster becomes the graph; a run shows the revision it wrote (the `system:standing`
  derivation on the target — already in the chain, never joined).
- **The Supervisor agent** — its job is re-derived: it is the **author of the plan**. In an attended turn, as
  the member's hands, it turns *"keep a weekly shop report and send it to the team"* into a small graph of
  declarations, reads them back, and explains a failure from the ledger. The agent authors; the kernel
  performs; the cockpit shows. That is a supervisor with no authority over any being — the frame makes the name
  safe (ADR-656 D1.1), rather than the narrowness making the name empty.

---

## 5. What to build, in order

Each step is an ordinary ADR against a *constrained* design. None reopens ADR-596 D1, amends an axiom, or adds a
table.

| Step | Build | Unlocks | Touches |
|---|---|---|---|
| **0** ✅ | *(shipped — ADR-659 D1–D3)* Run honesty: the truncation refusal (ADR-618 am.1) · the claim out of `next_run_at` (§6.2) · run → revision join · `app:` may not name an app that executes nothing (§6.3) | the cockpit stops lying | ADR-618 · 658 |
| **1** ✅ | *(shipped — ADR-659 D4/D5/D7)* **Workspace sources** — `{path}` file or folder; bounded read; cycle refused as a named problem; a declaration may not source its own target | intake (1) and flow (2) in one change | ADR-569/639 source grammar |
| **2** ✅ | *(shipped — ADR-659 D6)* **The pace rule** — skip at $0 when no prerequisite moved; downstream comes due when upstream wrote | chains that cost nothing idle; near-arrival latency | `scheduling.py` due-condition; Axiom 4 untouched |
| **3** | **Attention reads the work**; the Supervisor's job text re-derived; the cockpit draws the graph | (4) and (5) | ADR-658 D5 · the posture (prompt protocol) |
| **4** | **The proposed act** — a declaration's optional closing step enqueues to the existing queue | execute (3b), witnessed | ADR-307/405 · 628 |
| **5** | Compose targets (deck · post) and the generator cardinality; the 4096 ceiling (sectioned writes) | compose (3a) in full | ADR-569 D1 collision · 639 D6 |

Steps 1–2 are the hinge: small in code (one source predicate, one due-condition), and they convert the lane
from *"watch a URL"* to *"run my work"*. Step 5 is last deliberately — it is the only one with a real unsolved
design problem (an unattended writer inside an authoring surface's document model).

---

## 6. Findings driven this session

1. **A kept file that outgrew the ceiling was silently decapitated and metered `success`** — and the next run
   read the stump as the current file. Driven, fixed, gated 18/18, falsified RED 15/18. ADR-618 Amendment 1.
2. **The drain's materializer overwrites an in-flight claim sentinel.** The carry-over asked whether the
   drain trusting the CAS alone is *"a named limit or a defect"*: **a defect.** Driven on an in-memory index: a
   never-run door-created declaration (`fire_on_activation`) is claimed → the next tick's
   `materialize_standing_index` reads the future sentinel, `preserve_due_commitment` declines to keep it, and
   the row is rewritten to `now` → due again → a second claim **succeeds** while the first run is in flight.
   Exposure: a member's Run now on a never-run declaration, overlapping a tick. It is the mirror of ADR-658
   A1.8, and the root cause is shared: the claim is stored in the column the materializer owns, because a run
   has no state of its own. Fix belongs in step 0 (a `claimed_until` on the index row — a legal lean pointer).
3. **`app: supervisor` resolves the Supervisor as an executor** (`resolve_executor` → `supervisor`), against
   its own registration comment and ADR-658 D3. The guard is only the *absence* of `standing_executor`, which
   the resident fallback defeats. `request.app` is free text at the door.
4. **The carry-over's claim *"only the Text app has a standing executor"* is false** — no app declares one;
   all five resolve through the resident fallback. The executor selects a *character*, never a capability.
5. **Connector capture has no driver.** `run_connector_capture`'s only caller is the standing sweep, so with
   zero declarations nothing is captured from any connected platform. *Perceive* is dormant, not idle.
6. `test_adr557_router_hardening.py` now **crashes** (`FileNotFoundError: decompose.py`) — the census lists it
   as drift; it has since decayed to reporting nothing.

**Not reproduced, not fixed, per the carry-over's own instruction**: the cold-URL foreground race (a). It needs
a browser session on the operator's shell row; nothing here theorises about it.
