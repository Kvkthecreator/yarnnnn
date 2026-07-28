# ADR-493: Projects — the Co-Work State Desk, and the Work-Unit as a Declaration With an Owner

**Status:** Proposed (drafted 2026-07-28 from the Lane-2 Projects discourse over
`docs/analysis/projects-the-cowork-state-surface-consideration-2026-07-28.md`; **direction only —
no code, no schema, no build rides this ADR.** Every position below awaits operator ratification;
the ratification points are enumerated in §9. The consideration doc's §1 operator framing —
true human+AI co-work, species-blind principals over the attributed commons — is this ADR's
premise, not one of its questions.)
**Dimensions:** Substrate (primary — Axiom 1: the one new declared object) + Identity (Axiom 2 —
whose work a unit is) + Channel (Axiom 6 — the desk and the My-Work derivation) + Trigger
(Axiom 4 — what makes a unit move)
**Relates to:** ADR-231 D4 (the thin-index precedent), ADR-486 (Radar — the file-shaped-app-state
precedent this ADR's ontology follows), ADR-460/467 (agents = named hands, no standing intent on
rows — the fact that re-cuts the §4 crux), ADR-405/410/489 (the attention rails; the declared
amendment below), ADR-492 (rooms/mentions — the sibling app-layer ADR; sequencing §8), ADR-434
(powerbox — what access modes are already expressible), ADR-448 (reference edges — completion
receipts), ADR-407/DP35 (scope taxonomy; My-Work as per-viewer derivation), ADR-344/345 +
ADR-382/383 (standing obligation / expected output / per-agent mandate — explicitly NOT moved by
this ADR).
**Amends (conditional — these lock only with ratification AND land only with the build):**
- **ADR-410 §2** — the closed source-list widens a second time (ADR-492 D3 declared the first):
  "what wants me" gains **open work-units owned by the viewer** as a To-do source, derived at read
  time from the work-unit substrate — no inbox table, no per-unit read flags. To-do membership
  keys on the unit's *state* (open); the unseen count on the *cursor* — two distinct facts, per
  the ADR-492 §7 rule, so a unit never silently clears by scroll-by.
- **ADR-489 D1** — the weight table gains work-unit rows: a state transition on a unit the viewer
  owns → **material** to that viewer; transitions on other units → **routine**; any machine
  bookkeeping around units (`_`-prefixed state files, index writes) → **housekeeping** (already
  covered by the existing basename rule, `api/services/attention.py:62-74`).

**Supersedes nothing.** ADR-120–137/138 remain deleted history; per the operator's ruling they are
architectural FYI, not an approach precedent — this ADR neither revives nor answers them.

---

## 1. Context — what the audit actually found

The consideration doc's mapping table claimed "most of the reference product is already built as
OS." The 2026-07-28 implementation audit (four receipted passes: work-unit machinery, attention
rails, grants/powerbox, reference edges) confirmed that — and sharpened two facts the doc had
softer:

**1a. The asymmetry is deeper than "no human side."** No human-assignable commitment object
exists anywhere in the repo (grep across `api/` + `web/` for assignee/assigned_to/my_work/
commitment: zero object hits; every "assignment" in code binds a *recurrence to the agent that
executes it* — `web/components/work/WorkDetail.tsx:57,99`). But the agent side has no assignable
work-unit either: **standing intent attaches to declarations, never to agents** — by ratified
design (`api/services/agents_registry.py:15-35`: kernel Agents hold "NO standing intent… no wake
source, no mandate, no autonomy dial"; ADR-486 D3: "standing intent lives on the declaration,
never on an agent"). "Assign work to an Agent" is not a routing act into agent machinery; it is
*authoring a declaration* that fires under a character.

**1b. The standing-work substrate is declaratively near-empty.** Prod
`/workspace/_recurrences.yaml` = `[]`; the `tasks` scheduling index holds zero judgment rows
(ADR-486 §2 receipts). The live standing work is radar hubs. This kills the "ship views first"
MVP reading (§7).

**1c. The desks question is mis-posed.** The Agents surface today is identity + capability only —
deliberately (`web/app/(authenticated)/agents/page.tsx:10-21`, rewritten 2026-07-16: "every pane
is identity or capability, never authority"). Standing-work legibility lives on search-only
surfaces (`web/components/work/`, chrome gated off). There is no agent-mandate desk for Projects
to absorb or duel with — there is **one desk missing**, not two to reconcile.

**1d. The rails are ready and the discipline is known.** The timeline derives from exactly three
ledgers (`api/routes/workspace.py:1010-1099`); the To-do rail from exactly one
(`api/routes/proposals.py:187-196`); weight extends at one pure classifier
(`api/services/attention.py:36-76`); the per-viewer cursor is `member_state['attention']`. A new
attention source composes (a parallel query + a classifier branch) and must declare its ADR-410 §2
amendment — done in this ADR's header.

**1e. Access is further along than assumed.** The powerbox already gives arbitrary-depth,
two-axis, per-principal path scoping (`api/services/primitives/workspace.py:2120-2151,2278-2303`).
What does NOT exist: a region-first ACL object, DB-RLS read isolation (RLS SELECT is
workspace-scoped with no path predicate — migration `189:164-185`), and any grant concept of
"approval." §6 maps the modes honestly.

## 2. D1 — The work-unit is the third kind of an existing family

The one genuinely new object is **not** a new "task system." The substrate already declares work
in files and lets the kernel move it:

| Kind | Declaration | What makes it move |
|---|---|---|
| Recurrence | `/workspace/_recurrences.yaml` entry (`slug · schedule · prompt`) | a cron (`kind='judgment'` index slice) |
| Radar hub | `operation/{topic}/_radar.yaml` (topic · sources · cadence) | a cadence (`kind='radar'` index slice) |
| **Work-unit (new)** | a file in a project's meaning-folder (owner · state · intent) | **an owner** — a principal's commitment |

One family, one new kind. **Work is declared in files; the kinds differ only in what makes them
move.** A work-unit is a declaration whose trigger is a person's commitment rather than a clock —
which is why it needs no scheduler, no wake source, and no new kernel primitive.

Species-blind by construction, with the one honest asymmetry named:

- **Member-owned** — a commitment. Recording it, taking it, moving its state, completing it are
  attributed revisions; peers are *told, never asked* (ADR-408), because the rails carry
  attributed acts for free.
- **Agent-owned** — an execution binding: a character (the radar resident pattern,
  `api/services/radar.py:85-104`) + a prompt/recipe, **plus a trigger** (a schedule or hook — i.e.
  the unit composes with the existing declaration kinds). **The trigger-honesty rule:** an
  agent-owned unit with no trigger never runs — the never-ambient invariant (ADR-492 D2) means
  nothing fires without a human act. Such a unit is a member commitment in costume ("I will run
  this with Scout") and the desk must render it as one, not as delegated work in flight.

No agent row gains any field for this (the ADR-460 D3.a discipline): assignment lives on the
declaration side, exactly where recurrences and hubs already keep it.

## 3. D2 — The seam ruling: people vs work, not seat vs state

The consideration doc's §4 crux (Option A: Projects absorbs the agent desk / Option B: two desks)
dissolves under 1c. The seam this ADR proposes:

- **Agents desk = people.** Identity, character, engine, capability — its live shape, unchanged.
- **Projects desk = work.** The state of everything declared and in flight — work-units,
  recurrences, radar sweeps — with their execution evidence (runs, artifacts, edges) composed in.

Option A's named risk ("re-centralizing what ADR-382/383 per-agent-ized") does not arise: per-
agent governance files (`agents/{slug}/MANDATE.md` et al., read via `resolve_judgment_home`,
`api/services/working_memory.py:145-153`) stay per-agent substrate, rendered wherever the agent is
inspected. The desk composes **views over declarations and evidence; it never owns governance.**
Option B's risk ("two half-desks") does not arise either, because the second desk it feared —
Agents-as-mandate-desk — never existed in live code.

## 4. D3 — Ontology: file-shaped, Radar-patterned, no index until a walker needs one

- **A project is a meaning-folder** (the ADR-457 D4 `operation/{topic}/` convention — the same
  folder can host a radar hub *and* work: a project that watches and works is one folder). The
  scope object is a declaration file in it; work-units are files under it. Directory is meaning;
  everything else is metadata (the Files-model axiom).
- **Every state transition is a revision** through the one write door — attribution, message,
  timeline, bell, weight, and witness email all ride for free (the rails audit, 1d). No
  app-owned notification path exists or is permitted.
- **No DB table in v1.** Members have no cron; listing rides discovery (the radar
  `discover_radar_hubs` LIKE-scan precedent, `api/services/radar.py:224-258`). If a due-date nudge
  or agent-trigger later wants the scheduler, the ratified pattern is a `kind='work'` slice of the
  thin `tasks` index (ADR-231 D4; radar took exactly this path) — additive, reconstructable,
  never authoritative.
- **File formats decided at build under §9 discipline** (machine-parsed state → `_*.yaml`; no new
  YAML-frontmatter `.md`). This ADR fixes the *shape* (one file, one revision chain per unit), not
  the serialization.
- **Completion honesty — species-blind, evidence-forward.** Completion is always an attributed
  revision. Citing outputs is always possible (`derived_from` on the completion revision — the
  ADR-448 edge; `list_dependents` then answers "which units cite this artifact",
  `api/services/authored_substrate.py:1143-1241`) and never mandatory. Execution evidence renders
  when it exists — a unit executed by invocations carries structural receipts (runs + edges exist
  as ledger facts); a directly-asserted completion carries the witnessed act. The desk renders
  *attested-with-receipts* vs *asserted-and-witnessed* as facts about the unit, *never as a rule
  keyed on species* (ADR-405 D1) — and the floor never moves: receipts are never demanded of
  anyone as a completion gate (that is the quota/Goodhart pressure the kernel refuses), and
  "verified" is never fabricated where only assertion exists.
- **Honest ceiling, named:** a project-wide provenance rollup ("all edges under this folder") is
  a missing read shape — edges answer exact-path, HEAD-only questions today (the reference-edge
  audit). v1 reads per-unit edges (N small); a subtree edge query is future work, not assumed.

## 5. D4 — Views: My-Work is a derivation, and the third source is declared

- **My-Work** = work-units where owner = viewer. A per-viewer derivation over workspace-scoped
  substrate, composed at read time (the shipped pattern: workspace-scoped queries +
  viewer-resolution FE-side + the single `member_state['attention']` cursor). Never a second
  store (DP29/DP35).
- **"What wants me"** gains open-units-owned-by-viewer as its third source — declared in this
  ADR's Amends block per the ADR-410 §2 widening discipline (ADR-492 D3 is the template and the
  second source; neither is built yet — see §8). Composition point is known and clean: a parallel
  source query + the badge sum (`web/components/shell/AttentionCenter.tsx:188,286`) + one
  `classify_weight` branch.
- Custom fields, boards, filters = app-level view configuration over the same substrate
  (the `LANE_MODELS`/`DERIVE_RECIPES` precedent line) — never kernel schema.

## 6. D5 — Access: grants or nothing, with the ceilings named

- **v1 projects are workspace-public** — the commons default (broad grant, ADR-408 free-for-all
  within granted regions; the ADR-465 share posture).
- **Write-restricting a project region is expressible today**, per principal, at arbitrary depth
  (`write_scopes=['operation/{topic}/']`, powerbox).
- **Read-secure is app-layer only** — the powerbox read gate is real in the primitives, but DB
  RLS SELECT carries no path predicate (migration `189:164-185`): a "secure project" is not a
  hard DB boundary today. Named honestly; a region-first ACL object and RLS path isolation are
  their own future ADR if demanded — **not smuggled in here**.
- **"Approval-required" is refused as an access mode.** Approval is not membership; it is the
  witness dimension (ADR-307/405). If a per-region witness posture is ever wanted, it is an
  autonomy-dial discourse, not a Projects feature.
- **No app-owned membership, ever** — the §5 caution ratified as a binding constraint. Project
  participation *is* grant reach; the app adds no membership table.

## 7. D6 — The MVP: the human work-unit is the demand-generator, not the deferrable half

The consideration doc's §6.6 asked whether v1 is just views over existing agent mandates. **The
audit refutes it**: prod recurrences are `[]`; the only live standing work is radar. A views-only
MVP composes an empty desk. The Radar arc already taught the answer (engine idle → build the
authoring path, R1): **the MVP is the scope folder + the work-unit (both species) + the My-Work
derivation.** Humans commit constantly; agents fire on few declarations — the human commitment
object is what populates the desk and makes the agent-side composition worth looking at.

## 8. D7 — Noun and sequencing

- **Noun**: keep **"Projects"** member-facing — the layman word, in the vocabulary discipline of
  rooms/members/invite/keep/share and hubs/sweeps/briefs. The ADR-119/138 collision is docs
  archaeology (`/projects/` paths deleted eras ago; no live operator ever saw them). Internal
  object names avoid the `tasks`-table collision (`work_unit`, project scope). Operator may
  override the noun at ratification — it is a title edit, not a re-decision.
- **Sequencing**: direction ratifies now; **build does not jump the wave queue.** Rooms are step
  4 of the ADR-460 §8 program (W0 + settle + registry shipped). Projects does not depend on the
  Conversation object (no rooms prerequisite in its mechanics), but its attention amendment
  should land in the same disciplined motion as ADR-492 D3's when either builds — two declared
  sources, one widening discipline. Placement relative to the Studio multi-user wave is the
  operator's resourcing call at ratification.

## 9. Ratification points

1. **D1** — the work-unit as the third declaration kind (declaration-with-an-owner; one family
   with recurrences and hubs; no new agent facts; the trigger-honesty rule for agent-owned units).
2. **D2** — the seam ruling: Agents = people, Projects = work; the desk composes views over
   declarations + evidence, never owns governance. (This re-cuts the consideration doc's §4
   Option A/B framing; ratifying D2 closes that crux.)
3. **D3** — file-shaped ontology per the Radar precedent; no DB index in v1 (`kind='work'` slice
   named as the future pattern); completion honesty as written (species-blind, evidence-forward,
   floor never moves).
4. **D4** — My-Work as per-viewer derivation; the declared ADR-410 §2 / ADR-489 D1 amendments in
   the header (the third To-do source).
5. **D5** — access = grants only; v1 workspace-public; read-secure ceiling named and deferred;
   approval-mode refused as membership; no app-owned membership (binding).
6. **D6** — MVP shape: scope + work-unit (both species) + My-Work; views-only MVP refuted.
7. **D7** — the noun ("Projects") and the wave placement.
8. The §5 cautions of the consideration doc (views-and-acts-only; storage = the commons; no
   kernel primitives) adopted as binding constraints on the build ADR/wave that follows.
