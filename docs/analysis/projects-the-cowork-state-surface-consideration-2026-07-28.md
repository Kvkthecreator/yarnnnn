# Projects — the Co-Work State Surface (CONSIDERATION, NOT RATIFIED)

**Status: consideration capture, 2026-07-28. Deliberately NOT finalized, NOT an ADR, NO build
implied.** This document exists to hold the operator's framing and the first-principles mapping
so the next discourse starts from state, not from scratch. Nothing below is canon; if the
direction survives discourse, it graduates to a direction ADR with its own ratification points.

**Reference:** NAVER WORKS Project (naver.worksmobile.com/products/naver-works/project/) —
screenshots reviewed 2026-07-28: spaces with breadcrumbed projects; multiple views per project
(list · status board · timeline · custom "뷰 추가"); task cards carrying assignees, deadlines,
attachments, links, comment counts; a cross-project "내 업무" (My Tasks) personal dashboard;
custom fields (single/multi select, date, status, text, number, URL, checkbox, member); project
access modes (public / approval-required / secure); multi-project tagging; email-to-task;
activity history.

---

## 1. The operator's framing (the overarching approach)

> The current standing concept must be **true co-work between AI and humans** — the yarnnn
> service model is fundamentally a human-and-AI co-workspace. Users, state management, and views
> must be centered on that framework.

Two corollaries the operator set explicitly:

1. **This is not the PM-era concept revisited.** ADR-120–137 (projects/PM layer) and ADR-138
   (its deletion) are **referential only** — FYI for architectural/technical considerations
   (see §5), **not** the overarching approach. The prior build was human-team PM with an AI
   assistant bolted on; this consideration is a surface where humans and agents are peers in
   shared state. Different question; the old answer neither endorses nor forbids it.
2. **The content/state carve stands** (from the 2026-07-28 discourse): the Confluence-analog
   (content housing) is NOT this — content is the kernel commons, gardened by the steward,
   mirrored by Files. This consideration is about the **state half**: shared work, its owners,
   its transitions, its visibility.

## 2. The first-principles mapping — what each Naver-Works object becomes in a co-workspace

The exercise that makes this yarnnn-native rather than a clone: for each object in the
reference, ask what it becomes when participants are **principals** (humans and agents,
species-blind per ADR-405 D1) over an **attributed commons**.

| Naver Works object | Co-workspace re-founding | What already exists |
|---|---|---|
| Project / space | A **scope over the commons**: intent + participants + work-units + artifacts + trail. Not a container that owns content. | Grants (participants), reference edges (artifacts), ledgers (trail). Missing: the scope object + work-units. |
| Task + assignee | The **species-blind work-unit** — the genuinely new object. Assigned to a member → a human commitment, witnessed by peers (ADR-408: told, never asked). Assigned to an Agent → routes into the machinery that already exists (mandate / recurrence / queue); the agent's "acceptance" is its standing work. | Agent side: mandates, recurrences, expected output, standing obligation (DP30). Human side: nothing — no human-assignable commitment object exists. |
| Status columns / board | **State transitions as attributed acts.** A status change is authored substrate (who moved it, when, why) — which means the timeline, the bell, weight (ADR-489), and witness email all ride for free, zero new notification machinery. | The rails (ADR-405/410/489). Missing: the state object they'd carry. |
| My Tasks (내 업무) | A **per-viewer derivation** (DP35 viewer parameter): "work-units where assignee = me," computed, never a second store. Plausibly a third "what wants me" source after proposals and mentions. | The derivation pattern (bell, timeline). |
| Custom fields | **App-level view configuration** — never kernel schema. The kernel names the category; the app/member configures instances (the `LANE_MODELS`/`DERIVE_RECIPES` precedent line). | The precedent. |
| Access modes (public/approval/secure) | **OS grants scoped to the project region** — the powerbox (ADR-434) already scopes by path/region. No app-owned membership, ever. | Grants + powerbox. |
| Attachments / links | **Reference edges** (ADR-448) — a task cites the artifact; nothing is copied into a silo. "Attachment count" is a graph-degree fact. | Shipped. |
| Activity history | **The ledger.** Exists; the project view filters it by scope. | Shipped (timeline). |
| Email-to-task | A capture/perception concern (the dormant connector lane, ADR-401) or an MCP act — an intake question, not a projects question. | Scoped elsewhere. |

Reading the table honestly: **most of the reference product is already built as OS**, which is
the strongest signal the operator's app-layer instinct is right. The app would contribute
exactly what the OS/app rule allows — *views and acts* — plus **one** new substrate concept:
the work-unit with a species-blind assignee, and the project scope that groups them.

## 3. What makes this NOT Naver Works (the co-work differentia)

If the surface is worth building, it is because of what a human-only PM tool structurally
cannot do:

1. **Agents are real assignees.** Assigning a column of work to an Agent is not a label — it
   binds to execution machinery (a mandate/recurrence with expected output), and the agent's
   progress is *evidenced* (runs, artifacts, outcomes), not self-reported.
2. **"Done" can carry receipts.** An agent's completion cites its outputs (reference edges,
   ground-truth attestation where the domain has it); a human's completion is a witnessed act.
   State is closer to *attested* than *asserted* — the anti-Goodhart posture the kernel already
   holds (floors never move to close gaps).
3. **The steward gardens state.** Freddie can *propose* transitions from observed acts ("the
   artifact this task cites landed and was cited onward — mark done?") through the ADR-307
   gate. In Naver Works a PM chases status; here the substrate already knows.
4. **Provenance is native.** Every artifact a project touches carries its derivation history;
   "what was this decision based on" is a graph query, not archaeology.

## 4. The relationship to the Agents desk (open, and the crux)

The 2026-07-28 discourse first framed the state surface as "the Agents surface matured"
(mandates + witness). The operator's co-work correction widens it: humans hold work-units too.
The open design question is which composition owns which:

- **Option A — one surface**: Projects *is* the operating desk; agent mandates and human
  commitments are two assignee kinds in one view.
- **Option B — two surfaces**: Agents stays the seat/mandate desk (who is hired, how they're
  governed); Projects is the shared state view that *composes over* both agent standing work
  and human commitments.

Not decided here. Note only that Option A risks re-centralizing what ADR-382/383 deliberately
per-agent-ized (mandate, expected output), while Option B risks two half-desks.

## 5. Architectural FYI (subordinate, per the operator's ruling — technical reference only)

- **ADR-120–137 → ADR-138**: the prior project layer sat as *kernel hierarchy* (new coordination
  primitives between workspace and work) and was deleted whole. The surviving technical caution,
  not an approach verdict: **an app adds views and acts, never kernel primitives; members/access
  are the OS's (grants); storage is the commons.** If "project" needs its own membership model
  or its own notification path, it is smuggling OS into an app.
- **The Radar precedent (ADR-486)** is the likely substrate shape: app state as commons files
  (`_radar.yaml` analog — e.g. a project scope file + work-unit files) with a thin scheduling/
  index table only where the walker needs one (the `tasks`-index precedent, ADR-231 D4). File-
  shaped work-units get attribution, revisions, reference edges, and Files-mirror legibility for
  free.
- **Attention**: task assignment → the mentioned-member pattern (ADR-492 D3's To-do derivation
  extends naturally); state transitions → ADR-489 weight (a transition on *your* work-unit is
  material to you, routine to others). No new notification machinery is needed or permitted.
- **Naming**: "project" collides with the deleted ADR-119/138 era (`/projects/` paths existed);
  if the concept ratifies, choose the noun deliberately.

## 6. Open questions for the next discourse (deliberately unanswered)

1. The work-unit's substrate form — file-shaped (Radar precedent) vs table-backed index vs both.
2. Option A vs B in §4 (one desk or two).
3. Does an assigned work-unit enter "what wants me," and with what resolution semantics?
4. The human-commitment object's honesty model — what does "done" mean without receipts, and is
   witness enough?
5. Sequencing — ADR-492's rooms/mentions (communication) almost certainly precede this
   (coordination presumes a place to talk); where does this sit relative to the chat waves and
   the Studio multi-user wave?
6. Whether the MVP is actually just: project scope + My-Work derivation + agent work-units
   composed from existing mandates — i.e., ship the *views* before inventing the human
   work-unit at all.

**Next step when taken up:** operator discourse over §4 and §6 → if ratified, a direction ADR
(with the §5 cautions as constraints) → build inside whatever wave it's assigned. Until then,
this document is the standing record of the consideration and nothing more.
