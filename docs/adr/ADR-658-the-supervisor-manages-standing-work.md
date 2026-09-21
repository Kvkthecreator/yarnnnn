# ADR-658 — The Supervisor manages standing work: the app is the door a member can reach

> **Status**: **Accepted + Implemented** (2026-09-19; Proposed 2026-09-18) — supersedes **ADR-656** (the Supervisor app,
> Phases 1–2). **Amendment 1** (2026-09-19, below the decisions): the audit of this ADR's own claims, the
> operator's registry framing ruled, and three additions — D6 the detail, D7 the pre-shaped starts, the
> mirror/composition split. Gate: `api/test_adr658_standing_work_surface.py`.
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
- Live prod, re-run 2026-09-19: **0 standing declarations** (0 archived too), `tasks` holds 0 rows, and the
  newest standing receipt is 2026-09-06 — six runs in thirty days, all of one folder the operator has
  since removed.
- ⚠️ *"nothing lists what they have declared"* (the draft's wording) **overstated** — the Notifications
  window's **Standing work** pane (ADR-639 D4) lists declarations with Run now and Pause, and Reach shows
  which declarations read through a connection. What is missing is a **door**, a **detail**, and a home
  that is not a window about *what already happened*. Amendment A1.5 rules the shape.

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
| *"keep a weekly brief of my team's channels"* | `sources: [{connector: slack, selector: C0123}]`, `schedule: "0 9 * * 1"`, `target: brief.md` |
| *"track my MRR daily"* | `target: metrics.csv`, `shape.columns: [date, mrr]` |
| *"watch these pages and keep a brief"* | `sources: [{url: …}]`, `target: brief.md` |

Each is a verb + a connected system + a cadence. The app is where they are created, seen, paused and
read. ⚠️ A connector source is one the kernel holds a **capture binding** for — Slack, Notion and GitHub
today (`CONNECTOR_CAPTURE_BINDINGS`); an attached MCP server is reach for a *turn*, not a source for a
run (`_reach_connector_sources` answers `no_binding`). The first draft's `mcp:shopify` example promised
what the kernel refuses and is corrected here. **This is what "an evolved plugin" means here** — the connector supplies reach, the declaration
supplies the verb and the cadence, the derivation supplies the worker.

---

## Amendment 1 (2026-09-19) — the audit, the operator's registry framing, and three additions

> Operator, 2026-09-19: *"we should assess if we should implement a dedicated registry for tasks … tasks
> can be dedicated a dedicated domain or data handling scope … the architecture … scheduling, automation,
> connectors, should be first class and thus a container … [the registry] can either be pre-determined
> handling (much like a scaffolding of plugins) or a builder … display this information within the
> supervisor app much like a cockpit showing the list of tasks, then route into per task details, where you
> configure and manage."*

### A1.1 The registry exists, and it is DERIVED — a second one is refused

What the framing asks for — a first-class, listable, addressable unit that binds scheduling, connectors
and an executor — is what a standing declaration already IS, and its registry is already two things: the
substrate row (`{folder}/_standing.yaml` + `CONTRACT.md`, attributed and versioned — Axiom 1) and the thin
index `tasks` (`kind='standing'`), materialized from discovery and *"fully reconstructable from filesystem
state"* (ADR-231 D4 Path B; ADR-639 D3). A dedicated registry table or object would be a second authority
over the same fact — the two-authorities defect `supervisor_state.py` itself cites (ADR-495 D3) — and
reopens ADR-231 D4 with no new evidence. **So: first-class, yes — it already is. A dedicated store, no.**

Two vocabulary rulings ride with this. *Task* was dissolved by ADR-231 D8 and is a banned synonym in
member copy (VOICE §1.10 names *recurrence, task, scheduled action* as three words for one thing); the
member's word is **standing work**, the file is **instructions**, the cadence is **on a schedule**. And the
*scope* the framing asks for is the folder (ADR-384: directory is meaning; ADR-569 D1/D2: one declaration
per folder, the writer confined to its designated leaf) — nothing is minted for it.

### A1.2 The container's three legs are the declaration's own fields

| the framing | the field | the mechanism |
|---|---|---|
| inputs — connectors, context in | `sources[]` | a connector slice at the connection's aperture (ADR-594 D2, reach with a receipt) or an HTTP pull; raws retained under `inbound/` (DP32) |
| orchestration and intelligence | `app` → the derived executor · `CONTRACT.md` | the standing frame + the craft skill, one bounded judgment turn (ADR-639 D1/D2; ADR-618) |
| communication and display | `target` · the ledger | the kept file with `derived_from` citing the raws; `standing-sweep:` / `standing-write:` receipts; this surface |

⚠️ **One correction to "multi-agent orchestration"**: a declaration has exactly ONE executor, derived from
the target's type (§4). There is no orchestrator over other agents and no fan-out — that is ADR-596 D1's
deliberate limit, not a gap. The Claude-Projects analogue (a container whose context is shared across
sessions) is the **workspace itself** (ADR-411; ADR-656 D4), so no per-item memory store is built either.

### A1.3 D7 — scaffold AND builder; the scaffold is DERIVED from reach

The builder is D4's door. The scaffold is the **pre-shaped start**: a verb bound to a connection the member
already holds. A start is derived at read time from the acting workspace's connections ∩
`CONNECTOR_CAPTURE_BINDINGS` (the platforms a capture binding exists for), carrying the binding's own
`reads` sentence and the selectors chosen at that connection's aperture (`landscape.selected_sources`) —
never a hand-typed template table. The ADR-657 lesson applies verbatim: when a screen asks a human to type
what the system already knows, the knowledge is missing upstream. `GET /api/standing/starts` serves them;
the door opens pre-filled from one; an HTTP start is always offered; with nothing connected, the empty
state names Reach as the next step. A door-created declaration carries `fire_on_activation: true`, so its
first run fires on the next tick rather than at the first cron boundary — the member sees the file
change within minutes, which is the whole first impression.

### A1.4 D6 — the cockpit routes into a detail

§7's `work` band is the list. The framing's *"route into per task details, where you configure and
manage"* is added as **D6**, with canon precedent: ADR-231 D7's *detail mode* (the declaration, its runs
filtered by slug, the latest output, edit affordances) over the successor object. ADR-639 D4 deleted the
strings pane's composed view as chrome (*sources as parties · consumers · head facts · seeds*); D6 is not
that. It is bounded to the declaration's own facts:

- `GET /api/standing/{topic}` — the summary, the instructions text, the recent runs from the ledger, and
  the derived minder.
- `PATCH /api/standing/{topic}` widens from `paused` to the composer's own fields (`schedule · sources ·
  shape · target`); every write is `compose_standing_yaml` → `parse_standing_yaml` → `write_revision`,
  **refused by problem name before anything lands**. The route's earlier refusal to widen guarded against
  rebuilding a form ADR-567 D3 replaced; D4 has already made direct manipulation a door, so the fields are
  editable where they are created. Pausing a declaration already in a problem state stays allowed.
- `DELETE /api/standing/{topic}` — retire (§6.2, A1.6).
- Instructions are edited as the file they are (`PATCH /api/workspace/file`), never through a second
  door; the detail links to that edit.

### A1.5 The roster has a mirror already — and that is not the defect

§1.1's draft claim is corrected above. ADR-340 D1 settles the shape: the Notifications pane is the
**mirror** (complete, neutral, never deleted); this app is the **composition** (the door, the starts, the
detail); and by ADR-340 D8 — *one body, two mounts* — the row is one shared component
(`web/components/standing/StandingRow.tsx`). Nothing is rendered twice by two codes; the mirror's empty
state names this app as where standing work is set up.

### A1.6 The tombstone hazard, driven

`write_revision` on an archived path UPDATES the row and leaves `lifecycle='archived'` unless told
otherwise — so a retire-then-recreate would land the new declaration in Trash: undiscovered, silently never
run, with a roster that says nothing. Ruled: retire is `archive_live_file` on `_standing.yaml` alone (the
one delete — ADR-209-attributed, Trash-restorable; the instructions and the target untouched), and the
door writes with `lifecycle="active"` (restore-as-write, the `restore_live_file` shape). The gate drives
create → retire → create on a client that models Trash and asserts the second declaration is live and
discovered. `_move_file`'s own tombstone blindness stays the separate open item it already is.

### A1.7 Gate findings at baseline

`test_adr639_standing_work.py` was **RED at baseline** — three checks stale since ADR-656 revived
`supervisor` (*the register is exactly {editor, designer, blogger}* · *supervisor does not resolve* · *the
apps are exactly {slides, text, images, blogger}*). ADR-656 §9 did not list it. Amended here to the live
truth. Baselines run, not read: `test_agent_registry` 145/145 · `test_adr653` 94/94 · `test_adr592` 45/45 ·
`test_adr338` 17/17 · `test_adr297` 161/0.

### A1.8 The manual run could double-fire — driven, and closed at the door

The click-pass found it with money on it. The door arms a new declaration (`fire_on_activation`), so the
production scheduler drained it at **04:27:25 UTC**; the member's Run now click landed six seconds later
and the declaration ran **twice** — two sweeps, two judgment turns, two derivation revisions of `brief.md`,
two charges ($0.0139 + $0.0095). ADR-618 D2's claim did not hold across the two doors: `claim_run` is a CAS
against the value **its caller read**, and a caller that reads *after* the drain's claim reads the drain's
**sentinel** — which still equals itself, so the manual claim succeeds. The door makes this race likely
(create → the tick fires within the minute → the member clicks), so it is closed here rather than named:
`_claim_in_flight` refuses when the stored `next_run_at` is one the schedule **could not have produced** —
in the future, and not `compute_next_run_at`'s boundary for this declaration (a minute's tolerance). A due
row and the ordinary armed row both stay claimable, because Run now is table stakes. Driven three ways in
the gate with a spy in place of the sweep, and falsified RED. ⚠️ The drain's own side still trusts the CAS
alone; it has one instance, so nothing double-fires there today — named, not built.

> **Superseded 2026-09-20 by ADR-659 D1.** *Named, not built* was wrong: driven, the drain's materializer
> OVERWROTE an in-flight sentinel and a second claim succeeded mid-run — the mirror of this race. Both have one
> cause (the claim lived in `next_run_at`, the column the materializer owns), so the claim is now its own
> column and a lock (`tasks.claimed_until`, migration 258), and `_claim_in_flight` — this section's heuristic —
> is **deleted**. The three arms above are re-expressed against the lock in this ADR's gate (121/121).

### A1.9 Bands ARRIVE independently, not only degrade independently

The first cut awaited the surface's three reads together. On the click-pass the mentions read took **23
seconds**, and it held the roster — and even an opened detail — behind one spinner: the app's reason,
waiting on the band least likely to have anything in it. Each read now lands on its own; a band whose
read is still out says *Loading…* itself; an opened detail reads only its own route. Measured: the cockpit
rendered **3.9 s** after the dock click, against 23 s+ before. ⚠️ Why the mentions read is that slow from a
cold local API is the shared-service-client item already open in SESSION-HANDOFF, not this ADR's.

### A1.10 The click-pass, driven (2026-09-19)

An isolated headless Chrome (another session held the shared DevTools profile), logged in through the app's
own `/auth/callback?token_hash=` path, against a local API on the production database:

- the empty state offered **four derived starts** — Slack, Notion, GitHub, a web page — from the operator's
  live connections; a connection with nothing chosen says so and points at Reach instead of offering an
  empty picker;
- the door refused `deck.pptx` in the member's words, then created `click-pass-brief/brief.md` (revision
  `a760ff2b`); the detail showed the file, **Editor looks after this**, *Every weekday at 09:00 ·
  Asia/Seoul*, the source and the instructions;
- Run now wrote the file — a real HTTP pull and one bounded judgment turn; `brief.md` cites its source —
  and the detail listed the runs from the ledger;
- Pause (`7851a277`) and Resume (`b0454afd`) landed as attributed revisions of the declaration;
- the **mirror** (bell → Open Notifications → Standing work) listed the same row with the same minder and
  names the Supervisor as where standing work is set up;
- Retire (`db92b610`) archived `_standing.yaml` alone: `brief.md` and `CONTRACT.md` stayed `active` with
  their chains, the index row was gone, and the cockpit returned to the empty state with its starts.

⚠️ **Two things the drive found that are not this ADR's**, recorded in SESSION-HANDOFF: a cold load of
`/supervisor` (or `/notifications?…`) can foreground the shell's *remembered* window instead of the one
the URL names — the race `route-sync.ts` says it closes; and the click-pass folder is left in the
operator's workspace for them to trash.


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
- **D6**: the detail serves the instructions text and the runs from the ledger for exactly that topic; a
  widened PATCH that would produce a problem is refused by name and writes nothing; retiring archives the
  declaration only and the tasks index drops the row.
- **D7**: the starts are derived from connections that hold a capture binding — an attached MCP row or an
  unbound platform yields none; the HTTP start is always present.
- **A1.5**: the mirror and the composition mount one row component; the mirror keeps its three verbs.
- **A1.8**: Run now against a row the drain holds is the honest no-op — no second sweep; the ordinary armed
  row and a due row still run by hand.
- **A1.9**: the surface's three reads are never awaited together, and an opened detail is never held behind
  the bands' wait.
- A browser click-pass: create a declaration from the app, see it listed with its connector, cadence
  and derived minder, open its detail, pause it, run it now, read the target it wrote, and retire it
  without destroying the file.

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

---

## Amendment 2 (2026-09-21) — the design pass: the cockpit reads as one, and a gate that had gone blind

**Status**: implemented. Gate `api/test_adr658_standing_work_surface.py` **121/121**, proven RED on a
falsified catalog before the green was trusted; the surface driven in a real browser (light, dark, 390px).

### A2.0 — ⚠️ THE GATE WAS RED AGAINST A CORRECT PRODUCT

Found at the start of this pass: **six checks failing, nothing wrong with the product.** ADR-660 moved
every member-facing sentence to `web/messages/{en,ko}.json`, leaving `t('section.needsYouEmpty')` at the
render site. Six copy checks grepped English sentences in `.tsx` files — *"Nothing is waiting on you."*,
*"Nothing runs on its own yet."*, the door's first-run promise, the retire confirm's *"stay"*, the
derived minder's *"looks after this"* — and all six were still exactly what a member READ. The gate could
no longer see them.

⭐ **The lesson, stated so it generalises**: an ADR rules what a member READS, so its copy checks must
resolve keys the way the runtime does. `_words(rel)` in the gate now collects a component's
`useTranslations` namespaces, resolves every `t('key')` against the catalog (including the template-key
branches under a stem), and asserts over the resolved sentences. A copy change that breaks the promise
still fails; a rename or a move to the catalog does not. **This is the third instance of the family**
"a gate green (or red) against nothing" in this repo's ledger — here the failure was loud rather than
silent, which is the only reason it was cheap.

### A2.1 — Band 2 was a constant, and now holds its three ruled states (APP-BUILDER-UX §4.1)

`surface.minder` rendered one unchanging sentence whether five pieces of work were running, one was
failing, or none existed. **A band that cannot change cannot be wrong, and it also cannot be trusted** —
a member learns in a week that it never says anything, which is the "surfaces noise to prove it is alive"
failure arriving by the other door. `web/components/supervisor/MinderBand.tsx` renders §4.1 as written:

| State | Renders | When |
|---|---|---|
| Resting | `Supervisor looks after this.` + a steady dot | the default |
| Working | `Supervisor is updating brief.md.` + `WorkingGlyph` (ADR-651) | a run is in flight |
| Raising | `brief.md can't run until its instructions are fixed.` + **Open** | a declaration is blocked |

**§4.2's rule is honoured, not approximated.** *Raise only what changes what she would do next* — so a
FAILED RUN is not a raise (runs fail transiently; the row says so in its own line) and only `problem`,
which a member must act on, reaches band 2. At most one raise, structurally: the band takes the first
blocked declaration and a count carries the rest. **Derived from the roster the surface already holds —
no fourth read**, so it cannot become the slow band that holds the cockpit (the 2026-09-19 lesson).

### A2.2 — The status spine: one derived state, one badge, three mounts

`standingState()` + `StandingStateBadge` in `StandingRow.tsx`. Ordered `attention > paused > running >
resting`, because a member scanning a cockpit asks *is anything wrong?* first — a paused row that also
cannot run reads **Needs fixing**, since resuming it would not make it work. DP29: every input is already
served (`problem`, `paused`, the ledger row); a stored status column would be a second truth that drifts.
The dot carries the state and the word repeats it — colour alone is not a status.

### A2.3 — ⭐ DRIVEN, NOT READ: a blocked row promised a next run

The row and the detail both rendered `next_run_at` for a declaration with a `problem`. The server is
right to serve it (it is when the schedule next comes round), but on screen **"Needs fixing" sat beside
"next Sep 21, 11:34 AM"** — a false promise a member plans around. Found by driving fixtures through a
real browser; reading the component does not surface it, because each line is individually correct.
Both sites now suppress it, and the detail's **Next** field says `Not until it's fixed`.

Also driven: the raise line truncated to *"…can't run until its ins…"* at 390px, losing the one thing it
exists to say. Band 2 is one RAISE, not one physical line — it wraps.

### A2.4 — The rest of the pass

- **The door has a fixed place.** *New standing work* moved to band 1; inside the work band it shifted
  with the band's contents and vanished entirely while the roster read was out.
- **A disabled Start says why.** Six fields gate it and the door said nothing — a member facing a
  full-looking form and a dead button could not learn that a Slack channel was never chosen in Reach.
  The footer names the FIRST thing missing, in field order, so following it always makes progress.
- **The door closes.** Escape (the idiom on ~20 modals; this one shipped without it, so the first modal
  a member meets was the one that trapped them), backdrop click, `role="dialog"` + `aria-modal`.
- **The starts wear their connectors' real faces** via the one identity resolver (`ConnectorAvatar`),
  so the Slack picked here is visibly the Slack connected in Reach.
- **The row's verbs recede** to `opacity-70`, returning on hover AND `focus-within` — a control that
  appears only on hover is unreachable without a mouse.
- **Supervisor takes the agent violet** in the Dock (`surface-icons.tsx`); it had no accent row and
  rendered neutral grey. Not amber: the surface sits inches from the AttentionCenter, and an app
  permanently wearing the attention hue reads as a standing alarm.

### A2.5 — What was NOT done, and why

The three bands and the four section kinds are unchanged: APP-BUILDER-UX §2.2 fixes the frame and §5
rules the vocabulary grows on demand from a real app. This pass is polish **within** the canon — no new
kind, no layout prop, no fourth band. Raising the frame is an ADR amendment, not a design session.

---

## Amendment 3 (2026-09-21) — the door is two steps, and a start wears its connector's face

**Status**: implemented. Gate **131/131**, the two new arms proven RED on the exact bugs they guard.
Driven in a real browser: the picker, the door, and the nested folder picker.

### A3.1 — ⚠️ THE STARTS WERE REACHABLE EXACTLY ONCE

The pre-shaped starts (D7) lived only in the work band's EMPTY STATE. The moment a member had their
first piece of standing work that screen was gone, and with it every start — the only remaining
entrance was *New standing work*, which opened a **blank form**. A member with one piece of work had a
strictly worse creation path than a member with none, and D7's whole argument (the next step, pre-shaped
from what they already connected) applied only at minute zero.

The house gesture for creation is a modal that shows **choices, never form fields**, and opens a focused
form once one is picked — `NewArtifactModal` (ADR-452 v2) is that pattern's tenant.
`web/components/supervisor/StartPicker.tsx` follows it: *what should it keep current?* → pick → name it.

**The empty state keeps its cards**, because D7 rules that screen shows the next step pre-shaped and
hiding it behind a button would be a regression at exactly the moment it matters. Clicking one lands on
the same door's second step — **one creation path, two entrances**, never two divergent lists.

### A3.2 — ⭐ A PLATFORM KEY IS NOT A DIRECTORY KEY: the lettermark that shipped

A start's `connector` is a **platform key** (`slack` · `notion` · `github`) — `_CONNECTOR_STARTS` is
keyed by the capture binding's platform. The first cut passed `connectorKey={s.connector}` to
`ConnectorAvatar`, which routes to `KEY_MARKS` — **an empty table**. It typechecked, it built, and it
rendered a derived LETTERMARK ("S" on a hashed tone) beside a card reading *"Keep a brief of your Slack
channels current"*, while `CONNECTOR_REGISTRY` had held the real Slack mark all along.

Nothing failed. The defect was visible only by LOOKING at the rendered chip — the same class of failure
`lib/connectors/marks.tsx` was written to end, arriving through the resolver rather than through a
fabricated path. `StartMark.tsx` now resolves the platform key through `connectorMeta` →
`override={meta.brand}`, the path Reach (`ReachConnected.tsx:315`) and the finder
(`FindConnectorModal.tsx:539`) already take. One connector, one face, everywhere. A start with no
connector (a web page, a workspace path) takes a neutral chip carrying its own kind's glyph — honest,
never a fabricated mark.

### A3.3 — ⭐ DRIVEN: a nested dialog that never dimmed the one beneath it

The door's folder picker sits on top (later in DOM order) but its BACKDROP shares `Z_CONFIRM_BACKDROP`
with the dialog it was opened from, so the backdrop renders BEHIND that dialog: the form stayed at full
contrast and the two read as one confused layer. **This is house-wide, not this surface's bug** — the
identical structure ships in `NewArtifactModal`.

`WorkspacePickerModal` takes a `nested` flag that lifts it to a new `Z_NESTED_*` tier (520/521): above
the confirm tier, **below `Z_TOAST`** so a nested picker can never hide its own failure message. The
default is unchanged, because raising it would lift the standalone callers (Open…, Move to…) above
toasts where nothing is wrong today. The Supervisor door passes `nested`; `NewArtifactModal` is left for
its own owner and is named here so the next session finds it rather than rediscovers it.

### A3.4 — The door's shape follows the house

`NewStandingWorkModal` now portals to `document.body` on the shared z-tiers, like every other create
door — a bare `z-50` inside a pane's stacking context is how a dialog ends up under the thing that
opened it. Its header **names the chosen start and wears its mark**, so a member who picked Slack sees
that this form is the Slack one rather than an unrelated screen.

### A3.5 — The literal-copy meter, twice

Both new components tripped the ADR-660 meter with **pure `t()` calls**: a multi-line ternary inside JSX
reads as literal copy once `{…}` is stripped, leaving bare identifiers. Hoisting the ternary to a
`const` above the JSX fixes the reading without changing a rendered byte. Recorded because it will
recur: **the meter measures JSX text shape, not English**, and the fix is always the hoist, never a
raised ceiling. 274 → 262, the ceiling held.

---

## Amendment 4 (2026-09-21) — one list, one place; and the copy cut to its slots

**Status**: implemented. Gate **132/132** (two arms rewritten and proven RED), ADR-660 47/47 with the
literal-copy ceiling **ratcheted 262 → 258**, voice clean, build clean, driven.

### A4.1 — ⚠️ THE STARTS WERE RENDERED TWICE

am.3 put the starts in the picker and left them in the empty state, reasoning that D7 rules that screen
shows the next step pre-shaped. Driven, that reads as a defect: the empty state listed all five cards,
and clicking one opened a modal showing **the same five cards again**, stacked over the ones just
clicked. Two copies of one list are two things to keep in step, and one of them is always wrong.

**The list lives in the picker. The empty state is the door to it** — a real empty state now: title, one
sentence, one primary action (plus Reach when nothing is connected). D7 is still satisfied, because the
next step is still named and still one click from pre-shaped starts; it simply is not transcribed twice.
Removing the duplicate took 4 lines off the ADR-660 meter, and the ceiling ratcheted with it.

### A4.2 — The copy, cut to its slots (VOICE §1–§2)

The surface had grown the house style's two failure modes: an empty-state title over budget, and hints
that stacked a second clause explaining a mechanism. Measured against VOICE §2 and cut:

| | was | now |
|---|---|---|
| empty title (≤ 4 words) | "Nothing runs on its own yet." (5) | **"Nothing runs yet"** (3) |
| empty body | "Pick a start below. It runs on a schedule and keeps one file current." | "Set up work that keeps a file current on a schedule." |
| work intro | "Files kept current on a schedule. Open one to see its runs and instructions." | "Open one to see its runs and instructions." — the heading already says the rest |
| door subtitle | "One file, kept current on a schedule. The first run starts within a few minutes." | "The first run starts within a few minutes." |
| where hint | "A folder of its own. New or existing, one piece of standing work per folder." | "A folder of its own, new or existing." |
| instructions hint | "Saved next to the file. Every run follows it, and you can change it any time." | "Every run follows this. Change it any time." |
| retire confirm | 113 chars, three clauses | "The file and its history stay. You can set it up again later." |
| `sources_invalid` · `source_cycle` · `missing_target` | 69–111 chars with parentheticals | 54–77, one idea per sentence |

Both locales moved together; Korean was rewritten rather than trimmed, since a clause cut in English is
not a clause cut in Korean.

### A4.3 — ⭐ A GATE THAT PINS PROSE LOSES AN ARGUMENT WITH THE STYLE GUIDE

The empty-state arm asserted the exact string `"Nothing runs on its own yet."`, so it failed on an edit
that made the title **shorter and correct**. Rewritten to assert the PROMISE D7 actually rules — the
screen names the next step (a door, and Reach when nothing is connected) and never says "No items" —
plus a new arm measuring the title against its **slot budget** (≤ 4 words) rather than its wording.
The same lesson as am.2's blind copy checks, from the other direction: there the gate could not see the
copy, here it saw it too precisely.

---

## Amendment 5 (2026-09-21) — sources are a LIST, as the kernel always allowed

**Status**: implemented. Gate **142/142**, five new arms proven RED on the real regressions. Driven:
four channels seeded, a cross-platform mix built, a structured target held to one.

### A5.1 — ⚠️ THE DOOR NARROWED WHAT THE KERNEL HAD ALWAYS ACCEPTED

Operator question: *"the set-up seems to orient towards one intake — one Slack, to one output.
shouldn't it be multi?"* Audited, and the answer is that **it already was, everywhere except the door**:

| | |
|---|---|
| `_MAX_SOURCES_PROSE = 12` | a prose file may declare up to twelve sources |
| `_reach_connector_sources` | groups selectors **per platform** and loops — cross-platform by construction |
| `sources` in `DECLARATION_KEYS` | PATCHable since ADR-658 D6 |
| `StandingSummary.sources` | a list; the detail pane already `.map`ped it |

The narrowing was three mutually-exclusive tabs each composing a **one-element array**, and a prefill
that seeded `selectors[0]`. A member picks four channels at the connection's aperture in Reach, Reach
says four, and the brief reads **one** — a silent narrowing of their own stated choice. ADR-658's own
worked example, *"keep a weekly brief of my team's channel**s**"*, was unbuildable through the only door
that builds it.

`SourceList.tsx` makes sources a list in both places that own them: the door composes 1..N, and the
detail can **change** them (they were read-only, so a mis-picked channel had no repair short of retiring
the work and building it again).

### A5.2 — The server's rules, mirrored — never invented

`_classify_sources` is the authority and refuses BY NAME; the client's job is only to keep a member from
reaching a refusal they could not have predicted:

- **md** — 1..12, any mix of connection · path · page.
- **csv · json · txt** — **exactly one**, and a file rather than a folder. So a structured target seeds
  one slice (not four), hides the count, disables *Add a source*, and says why **before** the refusal.

⭐ The mirrored cap has a gate arm that reads `_MAX_SOURCES_PROSE` **out of the Python** and asserts the
TypeScript agrees. A constant copied across a language boundary drifts, and the drift's symptom is a
refusal a member cannot predict from the UI they were shown.

### A5.3 — ⭐ DRIVEN: a control that lied about its own selection

The slice `<select>` displayed `free[0]` whenever the stored selector was not in the current
connection's free list — but the **state kept the old value**. Switching Slack → Notion and pressing Add
therefore re-added *a Slack channel already in the list*: the control showed "Roadmap" and added
"#general". Found by driving the real flow and reading the rendered list, not the counter — the count
went 4 → 5, which looks exactly like success.

`effectiveSelector` is now what the control displays AND what it adds. **What a member sees selected is
what gets added; anything else is a lie the control tells about itself.**

### A5.4 — What was NOT changed

No server change: the composer, the parser and the validator were already list-shaped, and one of them
becoming two is the drift `DECLARATION_KEYS` exists to end. The structured-format rule is kept exactly,
not relaxed — it is a rule, not a limitation to route around.
