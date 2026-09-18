# ADR-658 — The Supervisor manages standing work: the app is the door a member can reach

> **Status**: **Proposed** (2026-09-18) — supersedes **ADR-656** (the Supervisor app, Phases 1–2).
> **Date**: 2026-09-18
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **What** (the work itself — the material a member manages).
> **No authority change**: the worker is DERIVED and displayed, never stored. No agent slug is
> written anywhere by this ADR, and no kernel rule is reopened. See §4.

**Supersedes** — [ADR-656](ADR-656-the-supervisor-app.md) in full. Its machinery is largely kept
(§8 is the explicit keep/delete census); its *vocabulary* is replaced, because the vocabulary was
derived from what the SYSTEM has rather than what a MEMBER does. §2 is the receipt.

**Reverses one ruling, explicitly** — ADR-656 **D5** (*"standing work stays a kernel lane, and this
app does not claim it"*). Standing work remains a kernel lane. What changes is that this app becomes
its **surface**. §5 argues why D5 was the wrong call under the connector framing, and why reversing
it costs no kernel change.

**Preserves** (load-bearing, untouched):
- **ADR-639** — standing work IS a kernel lane: `{folder}/_standing.yaml` + `CONTRACT.md`, drained by
  the ONE loop in `scheduling.py`. This ADR adds no second executor and no second drain.
- **ADR-596 D1 / ADR-460 D3.a** — consequential authority over a *being* stays unrepresentable. §4
  is careful: "minded by Editor" is a **read-time derivation**, not a stored assignee.
- **ADR-569 D1** — un-designated files are never a standing writer's target. Designation stays the
  member's explicit act; this ADR gives that act a door, it does not remove it.
- **ADR-411** — the workspace IS the shared memory. No memory store is built here.
- **ADR-435** — a composition that is a glorified redirect gets deleted. §7 states the test this
  surface must pass and how it passes it.

---

## 1. The problem

ADR-656 shipped a Supervisor app whose three bands are `needs-you` (unresolved mentions), `threads`
(the member's chat conversations) and `note` (a rendered `.md`). Each band is a sound reading of a
real ledger. The app is nonetheless close to useless to the person it is for, and the reason is
structural rather than cosmetic.

**A non-technical member opening yarnnn for the first time sees three empty bands.** They have no
mentions. They have no threads — `threads` reads `chat_sessions`, so it is empty until they have
already held conversations. `DECISIONS.md` has no writer (ADR-656 §8 names this openly), so band 3
renders its honest empty forever. The app's first impression is an apology.

That is a symptom. The disease is the **vocabulary's derivation**: `needs-you`, `threads` and `note`
are the nouns the *substrate* had lying around. None of them is a noun a member would say. Asked what
they want from a workspace that runs agents, a layman says *manage my shop*, *keep my weekly report
current*, *tell me when something needs me* — **verbs bound to a system they already use**.

> Operator, 2026-09-18: *"think in terms of core combinations (much like an evolved plugin) of what
> we expect to see if we thought of core verbs associated with connectors (like manage my shop is
> shopify and processes with agents, etc.)"*

The framing is the correction. The unit of work is not a generic task. It is **a verb bound to a
connected system, worked by an agent, on a cadence** — and the member manages its lifecycle.

### 1.1 The receipt that makes this urgent

The mechanism for exactly that already exists and **nobody can reach it**:

- `api/services/standing_work.py` takes a `connector` source, a `schedule`, a `CONTRACT.md`, and
  derives its worker from the target's type. That IS "manage my shop, weekly".
- `GET /api/standing` (list), `PATCH /api/standing/{topic}` (pause/resume), `POST
  /api/standing/{topic}/run` (run now) all ship.
- **There is no create route.** `web/lib/api/client.ts:977` says so in its own comment: *"no create
  route"*.
- `docs/SESSION-HANDOFF.md` has carried *"a Files door for declaring standing work"* as open debt
  **since 2026-09-04** — two weeks.
- Live prod: **0 standing declarations**.

⚠️ **The gap is NOT that creation is impossible — that framing is wrong and was corrected during
this ADR's own drafting.** A member can create a declaration today by *asking in chat*: the
`declaring-standing-work` skill writes `CONTRACT.md` + `_standing.yaml` beside the file, reads them
back, and the kernel picks the declaration up within minutes. That path works and is kept.

**The gap is that the path is conversational-only.** It is reachable exactly when a member already
knows standing work exists and knows to ask for it. Nothing in the product shows them that it
exists, nothing lists what they have declared, and nothing lets them create one by direct
manipulation. For a non-technical member opening yarnnn for the first time, a capability reachable
only by naming it unprompted is indistinguishable from a capability that is absent — and the
receipt is **0 live declarations against a lane that is drained on schedule**.

So this ADR builds a **door and a display**, not a mechanism. The conversational path stays; it is
one of the two ways in, and for tuning a contract in the member's own words it is the better one.

---

## 2. Why ADR-656's vocabulary is replaced rather than extended

ADR-656 §11.1 argued — correctly, and the argument still holds — that a composed app's sections must
be DERIVED from what the app must answer, never inherited. It then derived them from the wrong
question. It asked *"what is underway in this system?"* and answered with the system's own objects.
The member's question is *"what work do I have, and is it being done?"*

Adding a fourth section would not fix this. A member would still open to three empty bands plus one
live one, which is the defect with a workaround stapled to it. The vocabulary is replaced.

⭐ **This is the growth rule cutting both ways.** ADR-656 §11.1 used it to REFUSE inherited kinds
(`files`, `recent`). The same rule refuses kinds that answer nothing a member asks — and `threads`,
a list of chat conversations, is one. `threads` is **deleted**, and with it the only reason
`supervisor_state._threads` exists.

⚠️ **What is NOT the defect, and is not re-litigated**: ADR-656 D4 (memory is the workspace; the
agent's is private judgment) and its refusal to build a memory store were reasoned and remain right.
D3's routing analysis is likewise preserved and, in fact, load-bearing here — §4 is built on it.

---

## 3. D1 — The unit of work is a STANDING DECLARATION, surfaced in the member's words

A member manages **pieces of standing work**. One piece is:

| What the member sees | What it IS |
|---|---|
| a name — *"Weekly shop report"* | the folder holding the declaration |
| what it works from — *"Shopify"* | `sources[].connector` (ADR-582 D6 / 594 D2) |
| when — *"Mondays, 9am"* | `schedule` (cron in the workspace's timezone) |
| what it must stay true to | `CONTRACT.md` (prose, never machine-parsed) |
| what it produces | `target` — the designated leaf, kept current |
| who is minding it | **derived** — see §4 |
| whether it is running | `paused` / `paused_until` |

**No new table, no new object, no new executor.** Every column above is a field the kernel already
parses (`DECLARATION_KEYS = {target, app, schedule, sources, shape, paused, paused_until}`). The app
is a *surface over a mechanism that already runs* — which is the only kind of composition ADR-435
permits.

The CRUD and lifecycle the operator asked for map onto it exactly:

- **create** — the missing verb. §6.
- **read** — `GET /api/standing` (ships).
- **update** — pause/resume via `PATCH` (ships); contract edits are file edits through the one
  write path (`write_revision`), which is where they belong.
- **delete** — retiring a declaration, §6.2.
- **run now** — `POST /api/standing/{topic}/run` (ships).

---

## 4. D2 — The worker is DERIVED and DISPLAYED, never stored

> **The card says "minded by Editor". The row stores no agent.**

A member needs to see who is minding a piece of work — that is the legibility the operator asked
for, and a board where nobody owns anything is not legible. But a **stored assignee is authority
over a being** (ADR-596 D1), which ADR-656 D3 correctly refused.

The kernel already resolves this, and has since ADR-604 D2:

```
target's type → its app → that app's standing executor
    api/services/authoring.py:standing_executor_for_app()
    (falls back: standing_executor → resident)
```

So **"who is minding this" is a read-time derivation over material that is already stored.** The
declaration names an *app* (or derives one from the target's type); the app declares its executor;
the surface renders that agent's name and face.

This buys three things a stored assignee would cost:

1. **No kernel rule is reopened.** No verb takes an agent slug; no field holds one. ADR-596 D1 and
   ADR-656 D3 stand unamended.
2. **A renamed or retired agent heals automatically.** A stored assignee leaves dangling rows —
   precisely what ADR-632's retirement of the seat had to clean up by hand.
3. **One source of truth.** A derived-plus-override scheme would be the two-authorities defect
   `supervisor_state.py` itself cites (ADR-495 D3). It is refused here.

⚠️ **The honest limit, stated rather than slipped**: a member cannot say *"no, Editor should do this
one instead"*. Work is routed by **what the material is**, not by picking a being. If real demand
appears for per-item override, it is a **new ADR against ADR-596 D1 with evidence** — not a field
quietly added here. The bar is ADR-337 D6 (demand-pull), and today the demand is one design
conversation.

---

## 5. D3 — This app CLAIMS standing work as its surface, reversing ADR-656 D5

ADR-656 D5 refused standing work on the reasoning that *"the supervisor's subject is ATTENDED work
— what the member is doing now — and standing work is a kernel lane with its own executor"*, and
that an app claiming both would re-merge ADR-639's distinction.

**That reasoning conflated two different things: running work and surfacing it.** ADR-639's
distinction is about *what executes* — and it is fully preserved. Standing work is still drained by
the ONE loop in `scheduling.py`, by an executor derived from the target's type, composed through the
standing frame. This app executes nothing.

What ADR-656 D5 got wrong is that it left the kernel's recurring-work lane **with no member-facing
surface at all** — and the receipts in §1.1 are what that cost: zero declarations, a create door
missing, two weeks of carried debt. An app whose stated subject is *"what is underway"* that
excludes *the only work that runs on its own* was answering its own question incompletely.

⭐ **Under the connector framing the reversal is obvious**: *"manage my shop, weekly"* is a standing
declaration with a connector source. If the Supervisor does not surface it, nothing does.

**What stays split** (ADR-639, intact): the app registration still declares **no `standing_executor`
of its own** — the supervisor does not execute standing work, it *surfaces* it. The executor is
derived per declaration from the target's app. Surfacing and executing stay different acts.

---

## 6. D4 — The create door, and what it may not do

The missing verb. A member names a piece of work in their own words and the app composes the
declaration.

### 6.1 The shape

`POST /api/standing` — takes `{folder, target, schedule, app?, sources?, shape?, contract}` and
writes `_standing.yaml` + `CONTRACT.md` through **`write_revision()`, the one write path** (ADR-209).
The composer already exists in part: `routes/standing_work.py:compose_standing_yaml()`.

⚠️ **One composer, not two.** The door and the `declaring-standing-work` skill must emit the same
YAML from the same code — `compose_standing_yaml` is that code, and the door calls it rather than
formatting its own. Two authoring paths that each know the file format is exactly the drift
`DECLARATION_KEYS` was created to end (a rule module said `subject` while the file said `target`).
The gate asserts both paths produce a declaration the one parser accepts.

Two rules the door does not get to bend:

1. **Designation stays explicit (ADR-569 D1).** The member names the target leaf. The door does not
   infer a file to start overwriting, and an un-designated file is never a target.
2. **Format scope is enforced (ADR-639 D1).** `md · csv · json · txt` only. Designating a deck or an
   image stage is refused by name (`unsupported_format`), not silently allowed.

### 6.2 Retiring

Deleting a declaration deletes `_standing.yaml`. **The target file is NOT deleted** — it is the
member's work and keeps its full revision history. Retiring standing work stops it being *kept
current*; it does not destroy what was made. The confirm copy must say so in those words.

⚠️ **The tombstone hazard is real and named**: `move`/upload treat a deleted path as occupied (open
item in SESSION-HANDOFF; `_move_file` selects on path with no tombstone filter). A retire-then-
recreate of the same folder will burn the name. Either the retire path hard-deletes the row, or the
door refuses a name already tombstoned with an honest message. **This must be driven, not reasoned
about** — it is the exact defect class already on record.

---

## 7. D5 — The surface, and the ADR-435 test

The composition register and its declared-section dispatch are **kept** — they are the machinery
ADR-656 built, they work, and they are what a declared surface needs. Only the section vocabulary
changes:

```
work        what standing work do I have, and is it running?   (NEW — the app's reason)
needs-you   what is waiting on me?                             (KEPT — ADR-637's one cursor)
note        what did we decide?                                (KEPT — a rendered .md)
```

`threads` is **deleted**. `work` is the one new kind and it satisfies the growth rule the same way
`threads` claimed to: no existing kind shows standing work, and nothing else in the product does.

**The ADR-435 test** — *does this redirect to something that already owns the concept?* Files shows
files, not what keeps them current. Reach shows connections, not the work done through them. Chat
shows one conversation. Notifications shows what already happened. **Nothing shows the work itself**,
and that is why this surface is not a glorified redirect.

⭐ **And on day one it is not empty.** A member who has connected Shopify and declared one piece of
work sees it immediately. That is the whole difference from ADR-656.

### 7.1 The connector combination, made concrete

| The member says | The declaration |
|---|---|
| *"keep a weekly report on my shop"* | `sources: [{connector: mcp:shopify}]`, `schedule: "0 9 * * 1"`, `target: report.md` |
| *"track my MRR daily"* | `target: metrics.csv`, `shape.columns: [date, mrr]` |
| *"watch these pages and keep a brief"* | `sources: [{url: …}]`, `target: brief.md` |

Each is a verb + a connected system + a cadence. The app is where they are created, seen, paused and
read. **This is what "an evolved plugin" means here** — the connector supplies reach, the declaration
supplies the verb and the cadence, the derivation supplies the worker.

---

## 8. What is kept, and what is deleted

**Kept** (ADR-656's machinery, working, reused):
- the `supervisor` AGENTS row and its character
- the kernel app registration + posture (`services/apps/supervisor.py`), with D3's authority limits
- the `composition` surface register and `is_composition()` (`kernel_surfaces.py`)
- the declared-section dispatch and its honest amber miss (`SupervisorSection.tsx`)
- the degrade-closed band pattern — one band's failure never blanks the surface
- `needs-you` and `note`, unchanged

**Deleted** (singular implementation — CLAUDE.md discipline 2, no shims):
- the `threads` section kind, its renderer, and `supervisor_state._threads`
- the `THREAD_CAP` constant and the `chat_sessions` read behind it
- ADR-656's §4 routing-proposal design — **not yet built**, and now unnecessary: routing stamped a
  lane with its app, which was a workaround for lanes being the unit. Declarations carry their app
  directly. Nothing is deleted from the codebase here; a planned direction is withdrawn.

**Not built, and named so it is not silently assumed**: `DECISIONS.md` still has no writer. The
`note` band renders its honest empty until the member or the supervisor writes one. That remains
correct, not a gap to rush.

---

## 9. Consequences

- The kernel's recurring-work lane gets its first member-facing door, and the 2026-09-04 debt closes.
- A first-time member can reach a live, useful surface without authoring YAML.
- The connector framing gets its expression: reach (ADR-642/657) and work (ADR-639) meet in one place.
- **Cost, stated**: a member cannot assign work to a chosen agent (§4). This is deliberate and
  reversible only by a new ADR with evidence.
- **Cost, stated**: `supervisor/DECISIONS.md` remains writer-less.

---

## 10. Verification

Gate: `api/test_adr658_standing_work_surface.py` (to be written with the implementation).

- A created declaration round-trips: the door writes `_standing.yaml` + `CONTRACT.md` through
  `write_revision`, and `GET /api/standing` reads back exactly what was declared — **driven, not read**.
- **No agent slug is stored anywhere** by the create path — asserted over the written YAML and the
  row, since §4 is the ADR's central authority claim. The displayed worker is asserted to come from
  `standing_executor_for_app`, by falsifying the derivation and watching the label change.
- The parser whitelist holds: a declaration carrying a key outside `DECLARATION_KEYS` is refused.
- ADR-569 D1: an un-designated file is never written; designating an unsupported format is refused
  **by name** (`unsupported_format`), not silently dropped.
- Retire does **not** delete the target file, and its revision history survives — driven against a
  real revision chain.
- The tombstone interaction (§6.2) is **driven**: retire, then re-create the same folder name, and
  assert either a clean re-create or an honest refusal — never a burned name.
- `threads` is gone: the kind, its renderer and `_threads` are absent, and the surface renders the
  three declared sections. An undrawable kind still renders the amber miss.
- Every band still degrades closed and independently.
- A browser click-pass: create a declaration from the app, see it listed with its connector, cadence
  and derived minder, pause it, run it now, and read the target it wrote.

### 10.1 Gates this ADR inherits rather than owns

ADR-656 wrote **no gate of its own** — its §9 borrows five existing ones. So superseding it orphans
nothing, but the `threads` deletion and the section-vocabulary change land inside gates this ADR
does not own, and each must be re-run and amended in the same commit:

- `api/test_agent_registry.py` — carries the supervisor row's assertions (no authority key,
  `offered: False`, `kernel: True`, posture text naming no agent and carrying no assigning verb).
  **145/145 green at baseline, verified by running it** (script-shaped — `pytest` collects 0 tests
  from it and reports nothing; run it as `python3 test_agent_registry.py` and read the count).
  ⚠️ An earlier handoff note called this gate RED; that note is **stale** — `85ca14e` repaired the
  collection crash, and `decompose.py` now survives only in a comment explaining its deletion.
- `api/test_adr338_surface_registry_parity.py` — the three-way lockstep. The surface row survives
  (the app keeps its slug, route and tier); only its sections change.
- `api/test_adr653_the_member_app_layer_is_gone.py` — the composed-surface layer's survival. The
  composition register KEEPS its tenant here, so this must stay green unchanged; if it reddens, the
  keep/delete census in §8 is wrong.
- `api/test_adr592_app_stage.py` · `api/test_adr297_phase1.py` — stage and surface-row shape.

---

## 11. The one-line statement

**The Supervisor is where a member creates, sees and manages the work that runs on its own — a verb
bound to a connected system, minded by an agent the workspace derives.**
