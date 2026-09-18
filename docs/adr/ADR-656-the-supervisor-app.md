# ADR-656 — The Supervisor app: one app, one agent, and the first composed kernel surface

> **Status**: **Accepted + Phases 1–2 Implemented** (2026-09-18). Phase 1 = the AGENT and the APP
> (row · module · registration · job overlay · surface row). **Phase 2 = the SURFACE** — three
> declared sections, dispatched by kind, and the app UNVEILED (`stage: primary`, pinned, routed).
> **MEMORY and ROUTING remain named and not built** (§8.2, §8.4).
> **Date**: 2026-09-18
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Identity** (Axiom 2 — a fourth agent) + **Channel**
> (Axiom 6 — the first surface whose shape is DECLARED rather than mirrored). **No authority
> change**: every reach decision stays on grants and gates.
>
> **Derivation**: [the-supervisor-and-the-room](../analysis/the-supervisor-and-the-room-2026-09-18.md)
> — derived from the member's chair and two market benchmarks, collision-checked in its §7.
> **Scope ruling**: its §15 — *one app, one agent, and the app-builder is postponed indefinitely.*

**Reopens** — explicitly, with the reason on the record:
- **[ADR-639](ADR-639-standing-work-is-a-kernel-lane.md) D4** deleted the `supervisor` agent with
  the strings app. §2 argues why this is a different agent rather than a reversal.

**Preserves** (load-bearing, untouched):
- **ADR-460 D3.a / ADR-596** — no being holds authority over another. §4 is the whole reconciliation.
- **ADR-624** — memory is flat, in the being's home. §5.
- **ADR-411** — *lanes are isolated conversations; the workspace is the shared memory.* §5.
- **ADR-639** — standing work is a kernel lane, not an app. §6 keeps them apart deliberately.
- **ADR-464** — the member's copy is a folder; the kernel's is code. §3.

---

## 1. The problem

A member doing ongoing work across more than one thread has four wants, and none of them needs a
population to be true:

| The want | The name |
|---|---|
| *"I don't want to re-explain the context every time."* | **memory** |
| *"I don't want to decide which of my threads this belongs in."* | **routing** |
| *"I want to see everything about this concern in one place."* | **the container** |
| *"I want someone who knows what's going on across it."* | **the supervisor** |

⭐ The last two are one object seen from two sides. **A container with no supervisor is a folder; a
supervisor with no container is a chatbot with opinions about your other chats.** Both benchmarks
the analysis reads (Claude Projects redesigned · Grok Bot) ship them together and neither ships one
without the other.

YARNNN has threads (lanes), a library (the filesystem, and the stronger version), and a
multi-party room (ADR-626/495) that is built and barely entered. It has **no memory writer, no
reader, and nothing that routes.**

---

## 2. D1 — The supervisor RETURNS, and the difference from ADR-639 is the subject

ADR-639 D4 deleted a `supervisor` agent, and its finding stands verbatim: it *"was a posture string
— no code branched on its slug"*, the audit found strings was **seven things wearing one name**,
and none of them dissolved into an agent.

**That is a verdict on a MECHANISM whose material was one desk's STANDING DECLARATIONS.**

| | ADR-639's supervisor | This one |
|---|---|---|
| Material | standing declarations on one desk | the member's **work in flight** |
| Does the member meet it? | no — a receipt-signer | **yes** — the resident of a pane they open |
| What it holds | nothing (a posture string) | the shape of what is underway |
| Authority | none, and nothing to have authority over | none; routing is over lanes, never beings |

⭐⭐⭐ **ADR-610's rule is the test, and this passes it**: *a being is someone a member MEETS.* The
deleted supervisor failed it. This one is the resident of an app the member opens, which is why the
revival is admissible rather than a re-litigation.

⚠️ **The prior deletion is not itself the argument either way.** The operator's instruction was
explicit — *prior deletes are not a reason not to try again* — and the corresponding discipline is
that **a deletion closes the mechanism it measured**; re-opening requires new evidence. The new
evidence is that there is now parallel work to supervise, and there was not.

### 2.1 The name, argued rather than avoided

ADR-603 D3 raised the risk and answered it, and the answer holds for a kernel row: every other
resident is named for a **craft** (Editor · Designer · Blogger) while a manager-word names a **role
over others** — the exact reading D3.a forbids, *taught by the name itself*. It is admissible
because **its material (oversight of declared work) reads as a craft rather than a command
relation.**

⚠️ **An earlier pass of this discourse reached for "coordinator" to dodge the risk. That was the
wrong move and is recorded as such**: if a name carries a risk, the FRAME must make it safe — not
the vocabulary make the risk unsayable. §4 does that work, and the word is the operator's.

---

## 3. D2 — It is a KERNEL app, and that follows from the scope

The operator's scope: **one app, one agent, and the app-builder postponed indefinitely.** A member
authors no app — so ADR-464's line decides the rest: *the member's copy is a folder; the kernel's
is code.* One app that nobody authors is a Python module.

**What this buys**: the ADR-460 D3.a cliff at its strongest — a member cannot author the being at
all. **What it costs, recorded rather than glossed**: a member cannot shape their supervisor by
talking to it. ADR-653 D6's *"editing is chat"* does not apply here. Given up deliberately.

The member-authored layer ADR-653 shipped is **deleted**, census-first, in ADR-653 §13.

---

## 4. D3 — Routing is over LANES, never over beings

> **The supervisor decides WHERE work goes. It never decides WHO may do what.**

*"Supervisor assigns this to Editor"* is authority over a **being** — unrepresentable (ADR-596 D1).
*"Supervisor opens a thread about X, and that thread's resident derives from the app that owns it"*
is authority over a **declaration**, which is ADR-596 D2's own sentence and the distinction ADR-603
D3 already drew correctly.

Three things hold the line, and none is prose:

1. **The thread's resident DERIVES** (ADR-597 D1, `app_for_lane` → `resident_for_app`). Nothing
   the supervisor can reach names an agent.
2. **No verb takes an agent slug.** The routing act is mechanically *"stamp this lane with its
   app"* — one existing field, `context_metadata.lane.app`.
3. **The posture is written so only the admissible sentence is sayable**, and the gate asserts the
   TEXT — no other agent's name, no assign/delegate/instruct/direct verb — because there is no
   field to check.

### 4.1 An agent cannot open a lane, and that is settled

Driven (analysis §10): a conversation row has **exactly one writer**, behind a human JWT; the
unattended path is toolless by construction; there is no conversational verb in the lane tool set;
and RLS ANDs `is_workspace_member`, whose own comment reads *"Membership = a HUMAN role only (AI
principals are not members)."*

⭐ **So the supervisor routes AS THE MEMBER'S HANDS, inside a turn the member began.** A lane
stamps `member:{id} via {model}` and `is_agent_caller` is explicitly False for it — *"a lane is the
member's hands"*. Nothing wakes on its own initiative and no agent holds a grant.

⚠️ **Direct-open vs propose-and-click is a DEMAND question, not an authority one**, and the click
version ships first because it is the cheaper measurement. Eight primitives are already
*"registered, no live surface"*; the demand behind a new conversational verb today is one analysis
document (ADR-337 D6's bar, the ADR-225 lesson).

---

## 5. D4 — Memory: the workspace is shared; the agent's is PRIVATE JUDGMENT

The GLOSSARY already ruled the first half, canonically (ADR-411):

> *"Lanes are isolated conversations; **the workspace is the shared memory** — models collaborate
> through the filesystem with attribution, never through each other's transcripts."*

⭐⭐⭐ **YARNNN made the ruling Claude Projects makes, and made it the other way.** Projects gives
threads a memory store the product manages; YARNNN gives them the filesystem. So **there is no
shared-memory store to build** — the concern's memory is the app's own folder, already versioned,
attributed and revertible.

That leaves the second half, and they are **two objects** rather than one location to choose:

| | What it is | Where |
|---|---|---|
| the concern's memory | the work — files, notes, decisions | `supervisor/` (and wherever the work belongs) |
| the agent's memory | what it LEARNED about doing this work well | `agents/supervisor/memory/` |

**Ruled: the agent's memory holds PRIVATE JUDGMENT — corrections, preferences, patterns it should
not need told twice — and never context.** Three consequences:

1. ⭐ **It stays small by construction.** Judgment is bounded by how much a member has corrected;
   context would grow with the work and re-open the budget problem ADR-648 closed.
2. **ADR-624 is preserved.** Flat, in the being's home, keyed by slug. One agent, one memory.
3. **It is legible** — a workspace file the member can read and correct. No benchmark's managed
   memory store has that property.

⚠️ **Not built. `agents/{slug}/memory/` still has zero writers and zero readers**, and who may READ
the judgment file is open (§8).

---

## 6. D5 — Standing work stays a kernel lane, and this app does not claim it

The supervisor's subject is **attended** work — what the member is doing now. ADR-639's ruling
stands unchanged: standing work is a kernel lane whose executor derives from the kept file's type.

⚠️ The app registration deliberately declares **no `standing_executor`**. The field exists
(ADR-604 D2) and filling it would re-merge the distinction ADR-639 drew at the cost of exactly the
confusion this ADR spent §2 separating.

⚠️ **The unattended half has its own gap, named so it is not merged by accident**: zero live
standing declarations, and a source predicate that structurally cannot name a workspace region — so
standing work can only watch the outside world. **A different problem.**

---

## 7. D6 — The first COMPOSED kernel surface

The surface row declares `register: "composition"` — the first kernel row to do so, and what makes
ADR-653 D3.a's promotion load-bearing rather than decorative.

⭐ **It is possible because `is_composition()` reads the REGISTER FIELD, never the app's
provenance.** Driven: a kernel row declaring it validates, classifies as a composition, and would
be exposed. So the composed-surface layer survived the member-app deletion intact.

ADR-435 deleted the last composition (Home) for being *"in practice a glorified redirect"* — its
slots each deep-linked to a mirror that already owned the concept. **This one redirects to nothing**:
Files shows files, Chat shows conversations, Notifications shows what happened, and none of them
answers *what is underway*.

⚠️ **Born `stage: internal`, with NO route and NO launcher tier.** Both keys land in the commit that
ships the sections. `test_adr592_app_stage` caught the first draft claiming a route with no page
behind it — the empty-window class (`connectors`, ADR-653 §10.1), and the gate is why it never
shipped.

---

## 8. What is open

1. ✅ **The sections — SHIPPED 2026-09-18 (§11).** Re-derived rather than inherited:
   `needs-you` · `threads` · `note`. ADR-653's `files` and `recent` were deliberately NOT carried,
   and `threads` is the one new kind — the reason this app is not a redirect.
2. ⭐⭐ **Memory's writer and reader** (§5). Nothing accumulates until they exist.
3. ⭐ **Who may read the judgment file.** It is protected today (`_is_foreign_agent_home`). Whether
   the member reads it by default, the supervisor surfaces it, or it stays background is undecided.
4. **Routing's shape** (§4.1) — propose-and-click first; the verb only on measured demand.
5. **How the supervisor learns what a thread did.** If the workspace is the shared memory, a thread
   reports by writing a file and the supervisor reads the folder. Whether that is enough to be
   useful, or a thread owes an explicit summary, is a design question.
6. **Will a member want a multi-party room?** ADR-626 built one and it is barely entered. This frame
   bets the supervisor supplies the missing *reason*. ⚠️ Unproven, and **not settleable from this
   product's own traffic** — YARNNN is pre-user, and its existing chats are the operator's own.

---

## 9. Gate

`api/test_agent_registry.py` (145/145) carries the row's assertions — the roster-movement line
EDITED rather than bypassed, and ADR-639's anti-resurrection check replaced with the four
assertions that make the revival safe: no authority key, `offered: False`, `kernel: True`, and the
posture TEXT naming no other agent and carrying no assigning verb.

`api/test_adr592_app_stage.py` (46/46) holds the internal-at-birth discipline;
`api/test_adr297_phase1.py` (160/160) the surface-row shape; `api/test_adr338_surface_registry_parity.py`
(17/0) the three-way lockstep; `api/test_adr653_the_member_app_layer_is_gone.py` (75/75) the
composed-surface layer's survival.

**Driven live, not read**: `POST /lanes {app: "supervisor"}` → 200, Supervisor seated in the cast,
and the turn answered in the declared character — *"I keep track of what work is currently underway
across the workspace — which pieces are moving, which are waiting on you, and where each one lives
or belongs."* The surfaces payload correctly withholds the app (19 rows, supervisor absent).

---

## 10. The one-line statement

**The Supervisor is a kernel app and its one agent: it holds the shape of what is underway, routes
work into threads as the member's hands rather than on its own initiative, keeps private judgment
in its own home while the workspace stays the shared memory, and renders the first surface in
YARNNN whose shape is declared rather than mirrored — because a container with no one minding it is
a folder, and someone minding work with nowhere to stand is a chatbot with opinions about your
other chats.**


---

## 11. Phase 2 — the surface, and the vocabulary it actually needed (2026-09-18)

### 11.1 The sections were DERIVED, not inherited

ADR-653's first cut (`files` · `recent` · `needs-you` · `note`) was designed for a **member app over
a folder**. The supervisor's material is **work in flight**, so the cut was re-derived from what the
app must answer rather than carried over:

| The band-3 question | kind | Source — all of it already built |
|---|---|---|
| *what is waiting on me?* | `needs-you` | `mentions.list_mentions` — the ADR-605/637 attention derivation, one cursor |
| *what is underway?* | **`threads`** | the member's conversations (`chat_sessions` + cast), resident DERIVED per row |
| *what did we decide?* | `note` | one rendered `.md` (`supervisor/DECISIONS.md`) |

**Deliberately NOT carried, and the growth rule is why** (*a kind is added when a real app needs it
and cannot be served*):

- **`files`** — the supervisor owns no folder of work. Its own folder holds notes *about* the work;
  a file list of that answers nothing a member asks.
- **`recent`** — *"what moved"* is the timeline's job (Notifications). ⭐ Duplicating it here is
  **exactly the "glorified redirect" ADR-435 deleted the last composition for being.**

⭐ **`threads` is the one NEW kind, and it is why this app is not a redirect.** No other surface
shows work in flight: Files shows files, Chat shows one conversation, Notifications shows what
already happened. Its demand is this app — the growth rule satisfied, not bypassed.

### 11.2 Nothing here is a new source of truth

Each band is a **reading** of a ledger other surfaces already read. `needs-you` reuses
`list_mentions` rather than re-deriving "unresolved": ADR-637 gives attention ONE cursor, and a
second reader with its own opinion would make the badge and the band disagree — the two-authorities
defect ADR-495 D3 records for the cast.

⚠️ **Every band degrades CLOSED and INDEPENDENTLY.** Driven with a dead client: all three return
their own empty rather than raising. A pane that goes dark because a mention query timed out has
told the member their work vanished.

### 11.3 The unveil is a PAIRING, and the registry makes it structural

`stage` · `launcher_tier` · `route` moved together, in this commit, with the surface. They had to:
ADR-297's required-field check exempts `route` only for a **dormant** row — one carrying neither —
so **half a door is not expressible**. That is the registry enforcing the pairing rather than a
session remembering it.

⭐ **Three gates caught three real defects in the first draft**, and each was a contradiction rather
than a typo:

1. `test_adr592_app_stage` — the row claimed a route and a tier with no page behind either (the
   `connectors` empty-window class, ADR-653 §10.1).
2. `test_adr297_phase1` + the stage gate — `default_pinned: False` **argued with its own stage**.
   The pin is DERIVED (`is_default_pinned` reads the stage: `primary` ⇒ pinned), so a declared
   `False` was the hand-kept drift the derivation exists to end. A row does not get to disagree with
   itself.
3. The same pair — `DEFAULT_KEPT_SURFACES` (the Dock's hand-kept default) was stale against the
   derivation, and the gate named which of the two was wrong.

### 11.4 What the surface does, and the one thing it does not

Its only act is **opening a thread** — a navigation (`navigateToSurface('chat', { lane })`), never a
mutation. The supervisor does the work of no thread, and the surface is built so that is the only
thing it *can* do.

⚠️ **An unfiled thread says so**: a thread whose `app` is empty renders *"not filed yet"* rather
than hiding. That empty string is the routing gap (§4) made visible — a member who can see what is
unplaced can place it, and the supervisor can propose where.

### 11.5 Click-passed

Driven in a browser against the rig workspace: all three bands render, `needs-you` shows its resting
copy (*"Nothing is waiting on you"* — a complete sentence, not *"No items"*), `threads` lists 19
conversations with app · agent derived per row and three reading *"not filed yet"*, and `note` shows
its honest empty. Clicking a thread navigates to `/chat?chat.lane={id}`.

⚠️ **One thing the pass could NOT confirm**: the chat destination rendered *"Chat is not enabled"*
because **another session's API server held port 8000** with lanes off. The navigation itself is
verified (the URL carries the lane id) and the backend was driven directly instead — 19 threads,
correct derivation, and degrade-closed proven with a dead client.

