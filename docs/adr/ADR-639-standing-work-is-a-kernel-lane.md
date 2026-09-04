# ADR-639: Standing work is a kernel lane, not an app — strings and Supervisor dissolve

> **Status**: **Accepted + Implemented** (2026-09-04). Operator ruling in the apps · agents · skills · envelope audit: *"aligned in full … ensure singular streamlined discipline with code and docs, scoping in deletion and clean-up of code where warranted to avoid future ambiguity … really do the full clean-up (absorption, deletion of strings and supervisor per your provided approach and recommendation)."* The audit's assessment and the operator's decision on the one point it deferred (Supervisor's fate) are both recorded here.
> **Dimensional classification** (Axiom 0): **Mechanism** (Axiom 5 — the standing run composes through the lane module; craft moves to skills) + **Identity** (Axiom 2 — no agent is named for standing work; the executor derives from what the file is) + **Trigger** (Axiom 4 — one drain loop for every unattended kind). **Substrate**: the declaration file is renamed to the concept it carries.
> **Builds on**: ADR-569 (the maintained file — the *mechanism* survives whole) · ADR-603 (the standing declaration; D2 — the agent is DERIVED) · ADR-610 (*a being is someone a member meets; work nobody watches is a daemon*) · ADR-618 (bounded by the pool) · ADR-630 (skills are files; §3 named the standing-work skill and deferred it) · ADR-632 (the steward retired — two live execution paths) · ADR-634 (the frame is cacheable) · ADR-615 (a clock plus a credential stays impossible structurally) · [the four-nouns analysis](../analysis/the-four-nouns-and-the-collapsed-principal-2026-09-03.md) §5.4 R1.
> **Supersedes**: ADR-569 D6 + D7 (the Strings app, the Keeper colleague, the desk) · ADR-603 D3 + D4 (Supervisor; the Supervisor app) · ADR-604 (strings is Supervisor's desk) · ADR-610 D1/D4/D5 (Supervisor holds the app whole) · ADR-595 (the tending surface) · ADR-603 D6's *sequencing* (strings dissolves upward *after* a second declaration kind — executed now, on the evidence in §1.3).
> **Preserves**: ADR-569 D1 (designation, not file-type, is the boundary), D3 (write confinement + the loud shape refusal), D4 (execution rides the thin `tasks` index) · ADR-603 D1 + D2 (the declaration shape; *a declaration never names an agent*) · ADR-618 D1–D3 (the pool gate before the fetch; the manual door claims; the ledger writes with the service client) · ADR-596 D1/D2 (authority on declarations and gates, never on an agent) · ADR-626 D4.a (orchestration is declaration-mediated) · ADR-628 D3/D5 (phase (b)'s narrow identity; no publish from chat).
> **Gate**: `api/test_adr639_standing_work.py` (new); re-anchored gates listed in §6.

---

## 1. Context — the audit, and what the code admitted

The operator asked whether strings should be absorbed into agents, with recurring, multi-file, update-and-reference handling becoming skill-like for every agent, and whether strings and Supervisor survive as standalone concepts. The audit (2026-09-04) read the canon, drove two code surveys, and compared the shape to Claude Code's sub-agent · skill · cron model.

### 1.1 The altitude map

| Layer | Question | yarnnn before this ADR | Claude Code | State |
|---|---|---|---|---|
| Identity | who speaks | one register, identity-only rows | agent-type `.md` with per-type memory | settled |
| Capability | what a pane does | `register_app` + posture | none; a plugin is a namespace | settled |
| Craft | how work is done | `SKILL.md`, index + on-demand body | same shape | settled, **attended only** |
| Envelope | what the model sees | one composition site, cache-marked | static / boundary / dynamic | settled **for attended turns**; the standing run had a second envelope |
| Declaration | what must stay true, when | `_string.yaml` + `CONTRACT.md`, one kind | `{cron, prompt}`, no contract | n=1; the rule module unwired |
| Clock | who fires it | two drainers, byte-twins | 1s scheduler into the REPL queue | duplicated |
| Gate | may it happen unattended | balance · confinement · shape · toolless | permission rules, attended only | strings-specific code |
| Surface | where standing work is managed | `StringsSurface` | `/tasks`, `/loop` | named after its first instance |

### 1.2 Six findings, with receipts

1. **The standing run composed a second prompt envelope** — `resident_character + _STANDING_RUN_POSTURE` (`strings.py:1151`), outside `build_lane_conventions`. No commons contract, no citation rule, no mandate head. lane-frame.md's *"one composition site"* was true of attended turns only. This is the seam ADR-630 §3 named and deferred.
2. **Skills could not reach the standing run.** `run_bounded_derive_turn` takes a model, a system string and one user message; it never touched the skills loader and had no tool to read a body. A maintain-one-file skill would have been unreachable from the one place it applies.
3. **The declaration rule was unwired, and its one instance disagreed with it.** `DECLARATION_KEYS` named `subject` and `app`; the shipped parser read `target`, `schedule`, `sources`, `shape`, `paused` and **no `app`**. `resident_for_declaration` had zero production callers. ADR-627 D4's *"a declaration naming `app: blogger` works the day this ships"* was true at the derivation function and false at the drain: nothing would have discovered it.
4. **n=2 existed for the DRAINER, not for the declaration.** Capture ran the same discover → index → CAS-claim → run → record loop on the same `tasks` table with its own grammar (`slug` · `primitive` · `schedule`) and its own byte-twin of `claim_*`/`record_*`. Blogger — the named second kind — has **opposite cardinality** (revise one head forever vs. generate a new post each cycle — the ADR-627/628 blogger rebuild finding) and would not have validated the shape; it would have split it. So ADR-603 D6's gate, as written, could never fire clean.
5. **Supervisor was a posture string.** Its row was identical in shape to every other agent's; no code branched on its slug; the receipt face *"Supervisor kept …"* was a string literal beside `authored_by="system:strings"`. Re-pointing strings to Editor would have changed one visible thing: Supervisor leaving the Agents pane. The comparison is telling — Claude Code's `coordinator/` is also a prompt mode with no mechanics. Neither system has a coordinator that IS anything but posture.
6. **`standing_executor` was empty on every row** — a seam held for a case that has not arrived. It stays (ADR-610 D2's reasoning is unchanged; a mechanism is not wrong because its first filling was), but it is the third thing in this area that existed for a case that had not come.

### 1.3 The thesis, tested — strings decomposes into seven parts

| Part | Where it lands | Why |
|---|---|---|
| **Declaration** (`target · sources · schedule · CONTRACT.md`) | **substrate**, beside the file | already file-first; not an agent property (ADR-596 D2 houses the clock on declarations); not a skill (a skill teaches, it never authorizes — ADR-630) |
| **Clock** (discover · index · claim · drain) | **kernel daemon** | where ADR-610 put Keeper's mechanics; faceless |
| **Gates** (confinement raises · shape refuses · balance refuses · toolless) | **kernel gates** | a skill can only ask; the toolless run is the STRUCTURAL guard that a clock and a credential never meet (`lane_runner.py:554`). *"An agent in a lane turn on a schedule"* is a recurrence with tools — the steward's wake, deleted by ADR-632 |
| **Run posture** (fold don't append · preserve corrections · cite inline · NO_CHANGE) | **a skill** | its own comment: *"job instruction all along"* (`strings.py:790`) |
| **Pane posture** (the three files, the grammar, setting up, managing) | **a skill**, unscoped | the same shape as `creating-skills`; offered everywhere, "keep this current" said in Text has Editor write the declaration beside the file |
| **Surface** (what stands, what ran, what changed) | **a system view** in Notifications | ADR-603 D4's lens was right; ADR-604 folded it into strings only because one kind made it a duplicate |
| **Resident** | **none** | §2 D4 |

So: strings the *craft* dissolves into skills; strings the *mechanism* dissolves into the kernel daemon and its gates; strings the *pane* becomes the standing-work view. **None of it dissolves into agents.** What "absorbed into agents" was reaching for is *any agent can do it* — true once the craft is a skill and the executor derives from what the file is.

**Claude Code confirms the attended half and refutes the unattended half.** A lane turn is a query loop, an app resident is an agent-type definition with durable identity, skills are skills; the one structural gap is agent-spawns-agent with a return value (ADR-626 D4.b, about delegation, not standing work). But Claude Code's cron is a cron string and a prompt on disk, fired into the ordinary loop with full tools, bound to no agent, carrying no contract and no state between firings — exactly the recurrence ADR-603 retired, safe there only because a human sits at the terminal when it fires. The June re-founding analysis already derived this: stop-on-silence is catastrophic under an absent principal. The contract is what yarnnn has and Claude Code does not, and the four-nouns bet rides on it.

---

## 2. Decisions

### D1 — The standing run composes through the lane module

`services/lane_runner.py::build_standing_frame(client, user_id, *, model, executor, job, skill)` — beside `build_lane_conventions`, sharing its constants and its character door:

- **kept**: the commons contract (ADR-533 D1), the citation rule, the mandate head (read-only orientation — the standing run never had it), the executor's character via `build_agent_posture` (the same door every lane uses);
- **removed, because false for this run**: the tools line (there are none), the reach section (there is none — stated affirmatively: *this run reaches nothing live*), the cast (there is no room), the focus (there is no member standing anywhere), the register clause (there is no reply — ADR-638 D2 scopes it to lanes), the skills INDEX (a door is useless to a caller with no ReadFile);
- **added**: the kernel JOB (target · root · the output contract — return the full file or exactly `NO_CHANGE`; the sentinel is parsed, so it is a machine contract, not craft) and the craft skill's **BODY**, composed by the push door (ADR-630 D4) because a toolless turn cannot pull it.

The frame is ratcheted (`STANDING_FRAME_CEILING`, measured at ship) and cache-marked like every other (ADR-634); a standing run is one round, so the marker costs ~25% on the frame's few thousand bytes against a message that carries up to 40K of material — accepted, not optimized.

**The rule**: the lane module is the one place a model is told how this workspace works. A second envelope elsewhere is how the standing run lost the mandate head and the citation rule without anyone deciding it should.

### D2 — Craft is a skill; the two Python postures are DELETED

Two kernel skills (`api/services/skills/`, mirrored like the rest):

- **`keeping-a-file-current`** — `metadata.apps: [text]`. The craft `_STANDING_RUN_POSTURE` carried: fold rather than append, prune what stopped being true, preserve the member's corrections, cite each new claim inline, name a source/contract disagreement rather than paper over it, and report `NO_CHANGE` honestly. The standing run composes its body by binding; a Text turn on a kept file is offered it by the index.
- **`declaring-standing-work`** — universal (no `apps`). What `_STANDING_PANE_FRAME` taught: the three files, the strict declaration grammar, read-it-back, setting up (contract before cadence; never invent source URLs), managing (pause, re-source, tighten), and the law (only the designated target is ever a standing writer's target).

The two constants and `build_standing_run_posture` / `build_strings_pane_posture` are deleted. What stays in code is the OUTPUT CONTRACT — parsed, therefore machine — and the per-run facts (target, root, format) the job frame carries.

**The index ceilings move with a receipt.** `_STANDING_PANE_FRAME` was ~3,000 bytes composed into EVERY strings turn and `_STANDING_RUN_POSTURE` ~1,600 into every prose run; both leave the frame. Two discovery-grade index lines (~340 bytes each) arrive where they apply. Measured at ship with all eleven kernel skills listed: open chat 3,947 · text 3,327 · slides 2,659 · blogger 2,659 · images 1,647 — so `INDEX_CEILING` moves 3,000 → 3,400 (a Text pane applies nine skills and at 3,000 withheld two by alphabetical accident) and `UNBOUND_INDEX_CEILING` 3,400 → 4,000 (at 3,400 the open lane withheld the eleventh). Net prose per turn falls; the gate's rule (tighten a description before raising a ceiling) is unchanged, and the audit fixed the budget loop's phantom reserve on the last admission beside the raise.

### D3 — One declaration grammar, one drain loop

**The declaration is `_standing.yaml`**, beside its subject, with `CONTRACT.md` unchanged. Keys — and this set IS the parser's whitelist, so the rule can no longer drift from the instance:

```yaml
target: application-copy-bank.md   # the designated leaf — this folder, one segment
app: text                          # OPTIONAL. Explicit wins; absent → derived from the target's type
schedule: "0 13 * * *"             # UTC cron | @-semantic | list
paused: false
sources:                           # HTTP pull, or a connector slice (ADR-594 D2)
  - id: repo
    connector: github
    selector: Kvkthecreator/yarnnnn
shape: {}                          # structured formats only (csv columns / json keys)
```

**`app` derives from the target's type when absent** — prose (`md`/`txt`) → `text`, the ADR-602 D7 rule one layer up (*the app follows the artifact*). Structured formats run mechanically (fetch → map → validate → write, zero LLM) and need no executor. ADR-603 D2 holds exactly: **a declaration never names an agent** — the executor is `app → standing_executor_for_app → agents_registry` and no key may spell an agent's slug (gated). The 72-line `standing_declarations.py` — a rule with no reader — folds into `services/standing_work.py`; `DECLARATION_KEYS` lives beside the parser that enforces it.

**Kind, slugs, ledger, attribution**: `kind='standing'` on the `tasks` index, slug `standing:{topic}`, ledger rows `standing-sweep:{topic}` / `standing-write:{topic}` with `funnel_decision='standing'` (migration 251 adds the value — **applied BEFORE the code ships**, the migration-249 lesson: a lane's ledger marker is part of standing it up), attribution `system:standing`. Historical rows keep `string`/`system:strings`; they are read with a named legacy prefix and display-resolved (D5). The one live declaration and its index row are renamed by migration 252 after deploy (§4).

**One drain loop.** `services/scheduling.py` — already the home of `compute_next_run_at` and `preserve_due_commitment` — gains the loop both lanes ran as twins: `claim_run` (kind-scoped CAS), `record_run` (advance, clears the sentinel), `drain_due(client, kind, *, due, run)`. `services/capture/scheduling.py` loses `claim_capture_run` / `record_capture_run`; `services/capture/drainer.py` and `services/standing_work.py` are adapters that supply discovery and the run body. **The general engine ADR-603 D6 waited for is the LOOP, and it had n=2 all along.** The declaration SHAPE stays one parser: blogger's standing leg (opposite cardinality) brings its own parser and rides the same loop — which is what generalizing on the right axis looks like.

### D4 — The strings app, its pane, its routes and the Supervisor agent are DELETED

**The app.** `register_app("strings")` and `_strings_pane_posture` leave `services/apps/__init__.py`; the `strings` surface row leaves `KERNEL_SURFACES`; `/strings` becomes an ADR-308 redirect stub → `/notifications?notifications.pane=standing`, hand-listed in `lib/supabase/middleware.ts` (the ADR-592 obligation). The FE `AppDescriptor`, the Dock pin, the surface params, the `_string.yaml` declaration-routing claim, the `strings` API namespace and `StringsSurface.tsx` (1,645 lines) are deleted; `DOCK_RETIRED_SLUGS` gains the slug so a persisted pin renders no ghost (the radar precedent; no reseed generation).

**Each act the pane offered, found before cutting** (the ADR-616 discipline — count callers, not labels):

| Act | Handler | Fate |
|---|---|---|
| list what stands | `GET /api/strings` | **survives** → `GET /api/standing`, rendered by the Notifications **Standing work** pane |
| Run now | `POST …/run` | **survives** → `POST /api/standing/{topic}/run` (the ADR-618 claim unchanged) |
| Pause / Resume | `PATCH …` | **survives** → `PATCH /api/standing/{topic}` |
| designate (picker + Files "Keep this current…") | `navigateToSurface('strings', …)` — one caller | **survives as a conversation**: `declaring-standing-work` is in every index. The Files door is deleted; a door that opens the file's Text pane with the ask seeded is owed if wanted, not built here |
| sources as parties · consumers · head facts · contract render · seeds | the composed `GET /api/strings/{topic}` view | **deleted with the pane** (ADR-595 D3 chrome). Files shows the folder's three files; the ledger shows the runs |

**`StandingBand` is deleted too.** It read `persona/standing_intent.md` — the Reviewer's standing intent, retired with the steward (ADR-632) — and rendered nothing when both its reads were empty, which is every workspace. A steward fossil in the slot where "standing" now means declarations is exactly the ambiguity this ADR exists to remove.

**Supervisor.** ADR-603 D3 held it up on two arguments. *"Orchestration is continuously edited and wants a conversation"* is met by any resident holding `declaring-standing-work`, in the pane where the file lives. *"Familiarity — a named colleague for coordination"* is a product claim, and the operator ruled on it. ADR-610's own test then applies: **a being is someone a member MEETS; work nobody watches is a daemon.** With declaring a skill and the pane gone, Supervisor was what Keeper was — a name on a receipt. The row leaves `agents_registry.AGENTS`; the live pairing is Editor → slides · text, Designer → images, Blogger → blogger. The `clipboard-list` icon row and the landing-page card go with it.

**What a deleted agent leaves legible.** Seven cast rows and five transcript rows carry `supervisor`; two revisions carry `system:strings`. None is rewritten (ADR-460 D2: the fact is the ledger). `HISTORICAL_AGENT_NAMES` in the register resolves a retired slug to the name it signed as — the `freddie:` precedent, one hop further — so a transcript still says "Supervisor" where Supervisor spoke. The lanes stamped `app: strings` are re-stamped `app: text` (migration 252: their artifacts are prose, and a Text lane on that file IS the same conversation), after which ADR-614's read-time re-seating answers with Editor, exactly as it did for `keeper`.

### D5 — Attribution and display

New writes attribute `system:standing` (raws as observations, the leaf as a derivation citing them — ADR-569 D3 unchanged). `system:strings` on historical rows is display-resolved to **Standing work** at both display sites (`principal_display.py`, `attribution.ts`) — the `system:radar` → Researcher shape, without a name to costume, because there is no longer a being to name. The receipt message reads *"kept 'x.md' current (standing run, N sources)"*: the fact, not a face.

### D6 — What this deliberately does NOT do

- **No blogger standing leg.** It is owed its own parser (a generator's `NO_CHANGE` means "no post this week", a different thing) under ADR-627/628's phase (b) conditions; it rides `drain_due` when it lands.
- **No Files door.** Named above; a right-click that opens the file's Text pane with the ask seeded is one commit if demand names it.
- **No per-format canvas, no consumers view.** Reading happens at the file's own surface (ADR-595 D1's one true sentence survives its surface).
- **`standing_executor` stays on `register_app`** (ADR-610 D2). Empty on every row; the seam is real.
- **`keeping-a-file-current` is unmeasured prose until driven.** §4 drives one run through the new frame before this ADR closes; whether the skill changed what the run *noticed* and *refused* (ADR-633 §5a's two questions) is the measure, not whether it was read.

---

## 3. The rule this ADR leaves behind

> **Standing work is a kernel lane, not an app.** What a member declares lives beside the file; what runs it is a daemon; how it is done is a skill; who does it derives from what the file is. Nothing in that sentence is an agent, and a proposal that answers "who keeps this current?" with a name has put authority on an agent (ADR-596 D2).

---

## 4. Sequencing, data, and the drive

1. Migration **251** (`funnel_decision` gains `standing`) — applied before the deploy.
2. The backend + FE ship (this arc's commits).
3. Migration **252** — after the deploy: `_string.yaml` → `_standing.yaml` on `workspace_files` + `workspace_file_versions` (the path is the file's identity; its history moves with it), the `tasks` row re-keyed (`kind`, `slug`, `declaration_path`), `context_metadata.lane.app` `strings` → `text` on the stamped lanes. Measured before writing: 1 declaration · 1 index row · 2 revisions · 18 ledger rows (untouched) · 7 cast rows (untouched) · the lanes (counted in the migration's own comment).
4. **Drive — DONE 2026-09-04 04:26–04:28Z.** Migration 251 applied before the deploy (`7dcd2e8`, API live 04:25:37Z), 252 after (1 declaration · 2 versions · 1 index row · 6 lanes re-stamped `app: text`). `GET /api/standing` served the roster with `app: text` derived; `POST /api/standing/operation%2Ffundraising/run` → 200 in 47s, revision `e55e09d8`: `standing-sweep` + `standing-write` (judgment, claude-sonnet-5, $0.0829, `funnel_decision='standing'`, owner `principal_id`), `authored_by='system:standing'`, `revision_kind='derivation'`, `derived_from=[the landed GitHub snapshot]`, message *"kept 'application-copy-bank.md' current (standing run, 1 source)"*. The scheduler cron ticks on the new code (`_standing.yaml` scan → index → due → `[SCHED] tick complete`). Browser pass: the Notifications **Standing work** pane renders the declaration with Run now · Pause and *"Ran — the file was updated"*; the Dock carries no Strings. **Craft (ADR-633 §5a):** where the old posture reported `no_change` twice on the same snapshot, the framed run added the one section CONTRACT.md names as its responsibility, 22 cited bullets — the skill changed what the run NOTICED. Caveat recorded in the handoff: the material was a week stale (the GitHub reach landed no fresh snapshot — ADR-594's seam, owed).

---

## 5. Consequences

- One envelope module, two frames that share every constant; the standing run gains the mandate head and the citation rule it never had.
- Craft is discoverable, forkable and attributed (ADR-630's whole argument) for standing work as for everything else. ~4,600 bytes of always-composed Python prose leave the frame.
- One drain loop; a third unattended kind is an adapter, not a twin.
- The register is three rows, each met at a pane. GLOSSARY: **Strings**, **Supervisor**, **Keeper** are historical; **Standing work** is canonical.
- The four-nouns analysis' R1 (*generalizing from n=1*) is discharged on the axis that had evidence, and its review trigger 1 (*a second standing-declaration instance ships*) is re-read: the second instance of the LOOP shipped in 2026-07 as capture; the second instance of the SHAPE is still owed and will be a different shape.

## 6. Gates

`api/test_adr639_standing_work.py` — new; every check falsified by construction:

- D1: the standing frame composes the commons contract, citation rule, mandate head and the executor's character; carries NO tools line, reach, cast, focus, register clause or skills index; carries the job and the skill BODY; its scaffold is under `STANDING_FRAME_CEILING`; the run calls it (AST) and never composes a system string of its own.
- D2: both skills load with the declared scoping; the index ceilings hold for every lane; the two posture constants are gone.
- D3: `app` derives `text` for prose and explicit wins; no `DECLARATION_KEYS` member is an agent slug and an `agent:` key is inert residue; `kind='standing'`, the slugs and the attribution; `drain_due` is the one loop and both lanes call it (the twin functions are gone); migration 251 carries the value.
- D4: `AGENTS == {editor, designer, blogger}`; `all_apps() == {slides, text, images, blogger}`; no `strings` surface row; `/strings` is a stub and is hand-listed; the FE row, pin, params, claim, namespace and component are gone; the Standing work pane exists; `StandingBand` is gone; `HISTORICAL_AGENT_NAMES` resolves `supervisor`.
- D5: `system:strings` and `system:standing` both display as Standing work at both sites.

Re-anchored: `test_agent_registry` · `test_adr562_app_owned_config` · `test_adr597_resident_derivation` · `test_adr614_cast_follows_the_registration` · `test_adr618_standing_spend_gate` · `test_adr631_vocabulary` · `test_adr612_agent_connector_opt_in` · `test_adr591_no_pull_job` · `test_adr580_connector_derive` · `test_adr582_connectors` · `test_adr628_outbound_publish` · `test_adr636_app_declaration_parity` · `test_adr632_the_seat_retires` · `test_adr606_pane_sees_the_member` · `test_adr630_skills` · `test_lane_payload_shape_is_one_shape` · `test_adr624_the_being_has_a_home`. Deleted with their subject: `test_adr569_strings` · `test_adr603_standing_declaration` · `test_adr595_tending_surface` · `test_adr595_desk_is_one_surface`.
