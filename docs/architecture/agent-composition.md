# Agent Composition — the frame, what an agent reads, and where prose goes

> **Status**: Canonical.
> **Audience**: Engineers touching the lane frame, an app's posture, the participant constants, a skill, or an ADR that reshapes what an agent reads.
> **Purpose**: Single reference for how YARNNN composes an agent's turn — what enters the prompt and from where, what the agent reads at reasoning time and may write, where a sentence of prompt prose belongs, and how the composition is versioned.
> **Version**: v2.0 (2026-09-12 — the post-steward recut, ADR-596/630/632/634/638/648; v1 archived verbatim at [previous_versions/agent-composition-v1-2026-09-12.md](previous_versions/agent-composition-v1-2026-09-12.md))

---

## 1. Why this doc exists

The prompt layer moved fast: ADR-306 collapsed the persona frame, ADR-411 made lanes, ADR-533 made the participant contract kernel data, ADR-596 recut the agent, ADR-630 made craft a skill, ADR-632 deleted the steward's frame, ADR-634/647/648 bounded what a turn costs. Each ADR records one decision; `api/prompts/CHANGELOG.md` records each edit. Neither says *how an agent is composed today*. This doc does.

It answers, in order: what enters a turn's prompt and from where (§3.1–3.2); where a sentence of prompt prose belongs (§3.3 — the partition CLAUDE.md sends every session to); whether the assembled whole still tells one story (§3.4); what an agent reads and may write (§4); how the composition is versioned (§5).

---

## 2. The layers

Two kinds of actor (FOUNDATIONS Axiom 2, v10; ADR-596 D1):

- **Agents** — identity ⊕ character ⊕ engine, and nothing else. One register: `AGENTS` in `api/services/agents_registry.py` (Designer · Editor · Blogger today); an app names one of them its **resident** (`register_app(resident=…)`, ADR-562), and many-to-one is free (Editor → text · slides). Authority, reach, clock, purpose and judgment live on grants, declarations and gates — never on the agent.
- **Machinery** — kernel code executing unconditionally, attributed `system:*`: the drain loop, capture, the mirrors, the gates. Trusted because it is reviewed as code.

The **member** is the principal; a **lane** is how they act through an agent, under their own grant. Nothing an agent's own files say can widen what it may do (ADR-460 D3.a).

---

## 3. Composition

### 3.1 The lane frame (attended) — `build_lane_conventions`, `api/services/lane_runner.py`

Composed at turn time, derived-never-stored (a stored copy would drift), from the `_CONVENTIONS_FRAME` template in this order:

| # | Section | Composed from | Rule |
|---|---|---|---|
| 1 | **The address** — *You are {engine}, working inside a YARNNN workspace as {member}'s hands* | `LANE_MODELS[model].label`; the member's label | the engine rides behind the agent's name (ADR-460); the member is named |
| 2 | **The commons contract** — read-before-write · the attribution rule (*"{member} via {model}"*) · the citation rule | `PARTICIPANT_COMMONS_CONTRACT` and siblings in `api/services/workspace_paths.py` (ADR-533 D1) | kernel data; the frame never restates a clause inline — `test_adr533_participant_contract.py` asserts the composed output carries each verbatim |
| 3 | **The filesystem model** + the reach sentence (*your reach is exactly the member's grant*) | `PARTICIPANT_FILESYSTEM_MODEL` (ADR-424/588) | Documents / Downloads are told names; the kernel resolves them at one chokepoint |
| 4 | **Your tools** — one line naming the surface | `lane_tool_names(reach, platforms, attached)`: `LANE_TOOL_NAMES` (the file + folder verbs) + `LANE_SURFACE_EXTRA` (QueryKnowledge · WebSearch · list_integrations · GenerateImage) + the member's turn reach (ADR-615) + attached connectors' tools (ADR-635) | ONE computation feeds the declared payload, the execution allowlist and this prose (ADR-467 D4); uniform for every lane and every agent |
| 5 | **The reach section** — the turn's edge + one line per connection; the attached section | `reach_status.frame_paragraph` (ADR-644) + `attached_connectors.frame_section` (ADR-635 D5) | rendered from the ONE reach structure the member's Reach page and `list_integrations` also read; never hand prose |
| 6 | **Format discipline** | `PARTICIPANT_FORMAT_DISCIPLINE` (ADR-254) | |
| 7 | **Talking to {member}** | `PARTICIPANT_REGISTER` (ADR-638) | structure rules, A/B-validated (0.00 vs 2.08 leaks/reply); governs the address, never the work; lanes only |
| 8 | **Who else is here** — the cast, when the room holds more than two | `_build_cast_section` (ADR-495 D3) | species-blind; empty for a cast of one |
| 9 | **The workspace's mandate** — the first 40 lines of `constitution/MANDATE.md`, when present | `_read_workspace_file` | read-only orientation; workspace intent stays on the surface that carries it (ADR-533 D6) |
| 10 | **Posture** — the agent's character; then the app's job; then the member's place; then a skill-bound lane's derive section | `build_agent_posture(slug, as_name)` (the register; an app may rename its resident, ADR-562 D6) → `posture_for_app(app)` (`register_app(posture=…)`, ADR-606 D3; the bound artifact's head is read ONCE here) → `_compose_focus_section` (ADR-606 D1) → `build_skill_section` (ADR-450/630) | the character precedes the job; every binding APPENDS (an `=` here once ate the colleague's character); the focus is a fact about the MEMBER, rendered at one kernel site |
| 11 | **Skills** — the INDEX only | `skills_index_section(member_skills, app, reach)` (ADR-630) | descriptions only, scoped by app and by attached reach, bounded in BYTES (two budgets); a body enters the turn when the agent reads it (DP22) |

After the frame comes the message history, clamped **oldest-first** in chars (`_clamp_history_chars`, ADR-648 — the cache matches a prefix, so a middle-drop costs more than it saves). The frame is the cached prefix; caching lives ONLY in `model_router._build_messages` (ADR-634/647). A binary `ReadFile` on a viewable image appends the pixels as a user-message image part, never base64 in the tool result (ADR-623).

### 3.2 The standing frame (unattended) — `build_standing_frame` + `_STANDING_JOB`

The lane frame **minus** what a toolless run and an absent principal make false, **plus** what only a run can carry (ADR-639 D1):

- **kept** — the commons contract; the attribution rule (*this run's revision attributes as standing work on {member}'s declaration*); the citation rule (the kernel records the `derived_from` edge from the declared sources); the mandate head; the executor's character (`build_agent_posture` — the same door every lane uses; the executor is the agent the declaration DERIVED from the target's type, never named — ADR-603 D2);
- **removed** — the tools line (there are none), the reach section (*this run reaches nothing live*, said affirmatively), the cast, the focus, the register (there is no reply — ADR-638 D2), the skills index (a door is useless to a caller with no ReadFile);
- **added** — the kernel JOB (`_STANDING_JOB` in `api/services/standing_work.py`: the per-run facts + the output contract) and the craft skill's BODY, pushed in because a toolless turn cannot pull it (ADR-630 D4; a missing skill degrades craft, never correctness).

Ratcheted like the lane frame (`test_adr639_standing_work.py`); cache-marked like every frame (ADR-634).

### 3.3 Partition discipline — where prompt prose goes

> CLAUDE.md's Prompt change protocol sends every session here for *"where does this prose go"*. The composition sites are the lane frame (`build_lane_conventions`), the standing frame, the app postures (`register_app(posture=…)`), the kernel participant constants (`api/services/workspace_paths.py`) and the skills (`api/services/skills/`).

**The one-line statement.** *A sentence goes where the fact it states is
owned, and it is written once.* Grammar is owned by a registry, the contract
by the kernel, reach by a gate, an artifact's working by its app, craft by a
skill, and a program's judgment by its own file. The frame carries only what
none of those can: the address (who is speaking to whom, under what grant).

**The destinations, by the kind of fact.**

| The fact is… | It lives in | Composed by | Evidence it belongs there |
|---|---|---|---|
| **Grammar** — the tags, attributes and block vocabulary of an app's artifact | the app's registries (`_blocks_grammar`, layouts, measures) | the app's posture, DERIVED — never restated in prose | ADR-601 D1; a skill that named a tag was a second home for a fact (Part Q) |
| **How an app's artifact WORKS** — what the file format carries by reference, how a copy is made honest | the app's posture (`register_app(posture=…)`, ADR-606 D3) | the lane frame, for that app's bound lanes only | The Text lesson, 2026-09-07: markdown's three reference forms lived in three FE insert functions where no engine could read them; +584 B in `text_pane_posture` drove the provenance line 3/3 vs 0/2 |
| **The participant contract** — commons, citation edge, attribution, filesystem model, register | the kernel constants in `services/workspace_paths.py` (ADR-533 D1, ADR-638) | every lane, every connector, the standing frame | ADR-617 D2: a rule about HOW A DOCUMENT WORKS is kernel-universal; ADR-638's register measured 0.00 vs 2.08 leaks/reply |
| **Reach** — what a turn may touch | the gates (`resolve_turn_reach`, `lane_tool_names`, the grant) | the tool surface, and ONE derived paragraph in the frame — `reach_status.frame_paragraph`, rendered from the same structure the member's Connectors page, Reach and `list_integrations` render (ADR-644); never hand prose | ADR-464 §3: prose is not permission |
| **Craft** — how a kind of work is done well | a **skill** (`services/skills/{slug}/SKILL.md`, ADR-630), and ONLY when it carries a shape the model has no prior for: this workspace's own file, attribute or place | the index line in the frame; the body on demand (DP22) | `writing-a-spec` 7/7/7 vs 1/0/2 (p=0.100); craft a frontier model already holds measured flat in both arms (Part Q). A contract skill carries its CONSEQUENCE, not just its rule (Part R) |
| **A program's rules of judgment** | the program's own `principles.md` (four-field shape below) | *no live composition site since ADR-632* — still read by `judgment_log.py` / `conventions.py`; vestigial-but-present | Retained as the record; a program that returns will need a site, not a rule |
| **Substrate pedagogy** — what a kernel file is for | `_workspace_guide.md` (ADR-281) | the commons contract's pointer | The frame does not re-narrate what the guide teaches |
| **Anything a gate enforces** | code | nothing — the tool result reports the refusal | A lock, a budget, a scope: no prose needed (ADR-352 moved asking from persuasion to the gate) |

**The diagnostic test** (use this when uncertain): *Which of these would a
reader have to open to check the sentence is true?* Put the sentence there.
If the answer is "none — it is true of every turn regardless of app or
program", it is a kernel constant; if "the app's registry", derive it; if
"a gate", delete it; if "this workspace's own shape", it is a skill; if "the
frame itself", it is the address and belongs in the frame — and only then.

**The evidence bar is the same for every destination** (DP22, ADR-306; the
Prompt Change Protocol in CLAUDE.md): a **repeated, observed failure** named
in `api/prompts/CHANGELOG.md`, a size ratchet that is not raised to make room,
and — for a frame or posture clause — an A/B whose null is stated before it
runs. A composition gate proves a clause is COMPOSED; only a probe proves it
WORKS (ADR-365 shipped a ratified directive an A/B later falsified).

**Two failures this partition exists to prevent, both observed:**
- *A fact written twice drifts.* `PARTICIPANT_ARTIFACT_CITATION_RULE` is the
  `.html` citation grammar for every surface; the Studio posture carries the
  same grammar with worked markup for its own lanes — the constant states the
  form, the posture teaches the use, and a test pins that they agree.
- *A fact written nowhere an engine reads is a fact the engine does not have.*
  The three markdown reference forms were ruled (ADR-572 D17/D18), built
  (three toolbar doors) and gated — and no lane knew them, because a toolbar
  is not a composition site.

#### The four-field rule shape

A rule of judgment, wherever it lives (a program's `principles.md`, a skill that carries a contract), has four fields: a **name**; the **substrate it reads against**; a **pass condition**; the **consequence** on fail. A rule with no substrate anchor is floating — either runtime interface (→ the frame) or pedagogy (→ the guide, a skill). The pre-ADR-632 partition this shape came from — a program's `principles.md` against the steward's persona-frame — is archived verbatim with v1; do not derive current placement from it.

### 3.4 Composed coherence

Partition (§3.3) keeps each piece in its lane. Coherence asks whether the **assembled whole** still tells one story consistent with FOUNDATIONS: an agent is the member's hands in a shared commons, acting under the member's grant; it writes only to the commons and only through attributed tool calls; it never schedules, dispatches, or reaches out on its own (Axiom 1 §4 — the substrate is the bus; Axiom 2 — an agent holds no authority). A document set can pass the partition and fail this: every clause in its lane, yet the frame implying two action-grammars. **The model resolves a contradiction toward the more vivid, more repeated grammar — usually the wrong one** (the 2026-05-29 confabulation finding, archived with v1).

**Diagnostic**: read the assembled frame as one document. Does it tell a single story about (a) what the agent is, (b) how it acts, (c) where its agency ends?

**Enforcement is layered.** Structural gates assert the composed OUTPUT carries each clause (`test_adr533_participant_contract.py`, `test_adr638_register.py`, the size ratchets in `test_adr632_the_seat_retires.py` §5, `test_adr630_skills.py`). A composition gate proves a clause is COMPOSED; only a probe proves it WORKS — ADR-365 shipped a ratified directive an A/B later falsified, and ADR-638's register only earned its bytes by measuring.

---

## 4. What an agent reads, and what it may write

### 4.1 Reads — attended

| What | How | Note |
|---|---|---|
| the bound artifact's head | read once into the frame; re-read every turn | the OBJECT comes from the substrate, the PLACE from the focus declaration (ADR-452/606) |
| the workspace's mandate | the frame's orientation section | first 40 lines only |
| any file | `ReadFile` — capped, with a notice and a real `offset` | ADR-648: the clip is not the feature, the notice is |
| the commons by meaning | `QueryKnowledge` · `SearchFiles` · `ListFiles` | |
| its own memory | `agents/{slug}/memory/` — ordinary substrate it also writes | ADR-624 |
| a kernel skill's body | `ReadFile` of `system/skills/{slug}/SKILL.md` | ADR-630 |
| the web; the member's connections | `WebSearch`; turn reach under the member's own credential | ADR-615/577 — an agent is refused a credential of its own |
| an image | the pixels ride a user-message image part | ADR-623 |

### 4.2 Reads — unattended

The target's head and the declared sources, in the message; nothing else (toolless — ADR-603/639).

### 4.3 Writes

Every write is an attributed revision through `write_revision` (ADR-209): `member:{user_id} via {model}` in a lane, `system:standing` for a run. What an agent MAY write is the member's grant, decided at one chokepoint (ADR-643), minus the locked residue — its own grant sidecars, `system/`, the principal homes (ADR-624). A write on an artifact is a judged act (ADR-612/613). A consequence beyond the substrate — executing a proposal, publishing — is the member's click or the witness gate (ADR-307/405/628); an agent never binds it alone.

### 4.4 Two axes, stated once — authority vs vocabulary

**Authority** (what it may write) is the grant — never a primitive. **Vocabulary** (the tool surface) is uniform for every lane and every agent (`lane_tool_names`, ADR-467 D4) and deliberately small: the 2026-05-25 canary measured a single added tool collapsing output ~74%. Widening authority is a grant decision; adding a tool spends judgment bandwidth and needs its own evidence. A request phrased *"the agent should be able to do X"* almost always resolves to the grant and almost never needs a tool. The seat-era third axis — a posture of stewardship over the operation's mandate — is retired: judgment is never on the agent (ADR-596 D1).

---

## 5. Versioning + iteration discipline

### 5.1 The engine, not an identity string

An engine is a row in `LANE_MODELS` (`api/services/lane_runner.py`, ADR-559): a `provider/model` id, a label, `vision`, and `retired` for a superseded engine (routable, gone from the door, its `_BILLING_RATES` row kept). The member picks the colleague and the engine rides behind the name (ADR-460), persisted on the lane as a historical fact — never re-derived. What an app's resident runs is a `register_app` change on the server (ADR-562), never a caller-supplied id. Availability has three observed reasons — `no_provider_key` · `unpriced` · `upstream_refused` — and an unavailable engine is served greyed with its reason, never filtered.

### 5.2 CHANGELOG entries

Every change to a frame, a posture, the participant constants, a skill or a tool definition lands an entry in `api/prompts/CHANGELOG.md` per CLAUDE.md's Prompt change protocol: prepended, newest first, naming the **repeated, observed** failure it fixes, the expected behavior change and the gate. The file holds the newest two months; older months are frozen under `api/prompts/archive/` (`api/test_prompt_changelog_discipline.py`).

### 5.3 ADR pattern for composition changes

An ADR that touches composition (a frame, a posture, a constant, a skill, the tool surface) **cites this doc, amends it in the same commit**, adds the CHANGELOG entry, runs the ratchets (`test_adr632_the_seat_retires.py` §5, `test_adr630_skills.py`) — and, for a frame or posture clause, states its A/B null before it runs. Adding is the last resort; raising a ceiling needs the same evidence as adding a clause, named in the raising commit (ADR-306, DP22).

### 5.4 Singular implementation

One composition site per frame; one home per fact (§3.3). Dual paths at composition drift silently — the three hand-written reach branches disagreed with the member's surface within an hour of shipping (ADR-644), which is why the reach section is rendered from one structure now.

### 5.5 When to bump this doc

A new composition site; a new destination in the partition table; a change to the frame's section order; a third frame (which would be an adapter on one of these two, not a twin).

---

## 6. Appendix — ADR reference map (live)

ADR-209 (authored substrate) · 306 (the frame collapse) · 411 (lanes) · 460 (one concept, independent facts, one gate) · 467 (the uniform surface) · 495 (the cast) · 533 (the participant contract as data) · 559 (the engine registry) · 562 (app-owned AI config) · 596 (the agent) · 600/601 (one register; provenance) · 603 (the standing declaration) · 606 (the focus declaration) · 615 (reach follows the principal) · 623 (the lane can see) · 624 (the agent's home) · 630 (skills) · 632 (the steward retires) · 634/647 (caching) · 635 (attached connectors) · 638 (the register) · 639 (the standing frame) · 643 (one access decider) · 644 (one reach status) · 648 (the context budget). The v1 map (ADR-106 … 315) is archived with v1.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-24 | v1 — initial. Two-layer model, per-agent composition for YARNNN + Reviewer + domain Agents, operator↔Reviewer symmetry, versioning discipline (ADR-217 Commit 4). |
| 2026-09-07 | §3.2.1 re-cut for the post-steward frame (ADR-632): the partition's destinations become the lane frame, the postures, the kernel constants, the gates and the skills. |
| 2026-09-12 | v2.0 — **the post-steward recut (ADR-596/632).** §3 restated as the two live frames composed section by section from code; the partition kept verbatim; composed coherence restated for the lane; §4 the reads and writes of an agent under a grant; §5 the engine registry in place of identity strings. The Reviewer/YARNNN/production-role composition, the operator↔Reviewer symmetry and the three-axis self-amendment model are archived verbatim at previous_versions/agent-composition-v1-2026-09-12.md. |
