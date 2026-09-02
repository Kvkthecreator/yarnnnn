# ADR-630 — Skills are files: craft lives in the substrate, discovered by description, read on demand

> **Status**: **Accepted + Implemented** (2026-09-02). Operator ruling in the skills discourse: *"aligned on the workspace level, folder framing (and thus, not one folder, not agent-specific)… we'd probably be doing the same thing conceptually [as Claude's skills marketplace] but now with our workspace directory… ensure singular streamlined discipline with code and docs."*
> **Dimensional classification** (Axiom 0): **Substrate** (Axiom 1 — an instruction is a file) + **Mechanism** (Axiom 5 — prompting strategy is which vocabulary the model reaches for; here, which craft it reads before working). No Identity change: a skill never names an agent. No Purpose change: a skill teaches, it never authorizes.
> **Amends**: ADR-450 (the recipe registry becomes the skills folder; D1's "kernel-internal, never substrate" is superseded — kernel skills are code MIRRORED as files) · ADR-562 D4 (a recipe may name a resident — retired: a skill is craft, not identity) · ADR-579 D9 (its reversal condition is met: the brief returns as `summarizing-sources` WITH its door) · ADR-254 (SKILL.md's frontmatter is a named exception) · ADR-464 D3/D4 (skills are workspace-level and read on demand, not per-agent and composed every turn) · ADR-157 (referential playbook injection — the dead first instance is deleted).
> **Preserves**: ADR-601 D1 (the pane's GRAMMAR stays derived from the app's registries — a skill never restates it), ADR-533 (the kernel contract constants), ADR-464 §3 (prose is not permission), ADR-596 D2 (whoever a fact constrains must not be its unguarded author — a skill constrains craft, not reach), ADR-414 D4 (pure genesis — the mirror lands on first use, nothing is seeded at birth), ADR-209 (every mirror write is an attributed revision through the one write path).

## 1. Context — three layers filled the SKILL.md role, none of them a file

Before this ADR the role Claude Code's SKILL.md plays was split across three code homes: the kernel participant constants (universal contract), the app's pane posture (per-app, derived, composed every turn — 87% of a Slides frame), and `DERIVE_RECIPES` (per-task prose, three rows, reachable only through a lane binding at a click door). ADR-464 had built member skills as files in July, per agent and composed into every turn; ADR-599 deleted them with the member-agent machinery. Only the manifests carried the authority risk; the skills left with them.

Tested against the axioms (the 2026-09-02 discourse), a skill is a fact about **work**, not about an agent: it constrains craft, never reach (ADR-464 §3 proved a malicious skill's text reaches the prompt and the tool list does not move); it is derived from nothing, so storing it creates no drift (DP29 applies only to the grammar, which stays code); composing it every turn violates DP22 (ADR-464 D4's own cost argument); and as a file it gains what a Python dict cannot pay — attribution, history, `derived_from` citation from the outputs made under it, and reach by every species of principal through the file verbs (ADR-601 named the MCP gap and did not answer it; ADR-617 later ported the citation grammar on the same reasoning).

The public reference set (fetched 2026-09-02): the Agent Skills spec's portable frontmatter is `name` + `description` (+ optional `license`, `metadata`, `compatibility`, `allowed-tools`); bodies under 500 lines; metadata always loaded, body on trigger, resources on demand. Only five of Anthropic's nineteen public skills are pure work verbs achievable with file verbs, recall, web search and image generation — the rest are format- or code-bound. There is no public summarize, compare, or plan skill; those exist only as docs examples.

## 2. Decisions

### D1 — A skill is a folder holding `SKILL.md`; the description is the door

`{name}/SKILL.md` with frontmatter `name` (equals the folder), `description` (third person, what AND when, the words a member would say, ≤300 characters here so the index stays small), optional `metadata.target` (the output contract in one line). Body under 500 lines: What you produce · Steps · Quality bar · Anti-patterns. References one level deep. This is the Agent Skills convention verbatim, and ADR-254 records `SKILL.md` as a named frontmatter exception, parsed by the one sanctioned regex plus `yaml.safe_load` in `services/skills.parse_skill`.

### D2 — Two homes, one shape; the kernel's copy is code, mirrored as files

- **yarnnn's skills** live in `api/services/skills/{slug}/SKILL.md` — code, shipped with the deploy, under the prompt change protocol and eval probes like every LLM-facing text. They are **mirrored** into every workspace at `system/skills/{slug}/SKILL.md` as `system:kernel-skills` revisions: `system/` is locked for every caller class and outside the operator's organize reach (ADR-320), so the copy is read-only by topology. A tiny `system/skills/_manifest.yaml` records the mirrored version; the per-load check is one small read, and a kernel change writes only the skills whose hash moved. Mirrored on workspace-state load and on every scheduler tick, outside the steward gate. Pure genesis holds: nothing is seeded at birth; the mirror lands on first use.
- **A workspace's own skills** live in `skills/{name}/SKILL.md` — ordinary substrate: attributed, versioned, revertible, exported, forkable (DuplicateFile records the origin in `derived_from`). `creating-skills` teaches the shape.

Version control is the ledger. No semver, no lockfile, no per-workspace enable list (a declaration nobody populates is a tautology — the ADR-592 lesson). A fork cites its origin; "which decks were made under this skill" is a dependents query.

### D3 — Discovery is the index; the body loads on demand

Every lane's frame carries a `## Skills` section: one line per skill — path and description — kernel from code, member from one bounded query (`MEMBER_INDEX_CAP`). The body enters a turn only when the agent reads it.

The index is bounded in BYTES by two budgets, because it is composed every turn and a description is written for discovery (~330 bytes, not a word). `INDEX_CEILING` ratchets the kernel lines — ours, held by the gate; raising it needs the same evidence as adding a prompt instruction, so a longer description displaces another. `MEMBER_INDEX_ALLOWANCE` bounds the member lines at composition, and the lines that do not fit are named as a count the agent follows with `ListFiles skills/` — the same progressive disclosure the index gives skill bodies. Two numbers, not one, because they answer different questions: one ratchets prose we write, the other bounds prose we do not control.

**Amendment (2026-09-02) — the index is scoped by app.** The index was composed identically for every lane, so a Slides pane paid to advertise `writing-a-spec`, and an Images pane the deck skill. The frame already knows the app (its posture is resolved from it), so `metadata.apps` on a skill names the panes it is for: absent means every app, so silence is the open default and no undeclared skill changes meaning. A bound pane sees only what applies; an unbound lane (open chat) sees everything, because that is where a member goes for any kind of work. What is withheld is named with its count and the `ListFiles system/skills/` that reaches it — hidden at PRESENTATION, never at authorization (the ADR-395 precedent): the mirror still lands all eight in every workspace and any of them reads fine. Measured: 2,968 bytes open, 2,414 in Slides, 2,085 in Images (−18% to −29% per turn). Five of the eight are genuinely universal (summarizing, reviewing, comparing, creating-skills, deriving-a-design-system), which is why the saving is not larger — the honest ceiling, not a shortfall.

**Amendment (2026-09-02).** As shipped, the ceiling was asserted in the gate but never enforced at composition, and it was measured against the kernel index alone — while `MEMBER_INDEX_CAP` bounded member LINES, nothing bounded member BYTES. The gate passed because its member fixture used one-character descriptions. Measured: the kernel index is 2,968 bytes of a 3,000 ceiling, so a single realistic member skill reached 3,228 and twenty-four reached 9,222, in every turn of that workspace's lanes. Production held zero member skills, so the defect was latent — it would have fired on the first use of `creating-skills`. Now enforced at composition, with the gate measuring bytes against discovery-grade descriptions.

### D4 — Three doors, one content

The agent reads a skill when the index matches (pull). The lane binding `skill` + `derive_source` opens one deliberately (push — the ADR-450 D3 binding, renamed from `derive_recipe`; the envelope serves `skills`, the Studio landing's Learn-from targets name kernel slugs). The ADR-579 D8 "from sources…" click, when built, seeds the same binding.

### D5 — A skill never names an agent

ADR-562 D4's recipe resident is retired. A skill is craft; identity is the app's (`resident`) or the cast's (ADR-495). No skill frontmatter carries `resident`, and `create_lane` derives no resident from a skill. Authority stays where ADR-596 D2 put it: a skill that claims reach is ignored by the gates.

### D6 — The minimum kernel set, at the work-verb level

Eight, mapped to the public set where one exists: `summarizing-sources` (the docs' summarize example; the deleted `context-brief` returning WITH its door), `writing-updates` (internal-comms), `writing-a-spec` (doc-coauthoring; was `prd`), `presenting-from-sources` (the "present" verb; was `deck`), `reviewing-drafts` (discernment-nudge), `comparing-options` (no public anchor — flagged), `deriving-a-design-system` (brand-guidelines/theme-factory, inverted: derive one, and its output — `design-system/…/SKILL.md` — is itself the workspace's apply-style skill), `creating-skills` (skill-creator, the authoring half). The three migrated bodies are verbatim; the five new ones are unmeasured prose and earn eval probes as they are used.

## 3. What this deliberately does not do

- **The pane posture is untouched.** Moving its craft prose into skills is a second arc under the size ratchet's evidence rule; the grammar it derives never moves.
- **No composite skill.** The operator scoped it out; the leaves it needed are the verb-level set above.
- **No standing-work skills.** The bounded derive turn is toolless; a skill body can be composed into it later, but a standing composite stays closed until the attended act has receipts (ADR-626 D4.b).
- **No FE skills pane.** Kernel skills appear under System files; member skills are ordinary files in Files.

## 4. What shipped

`api/services/skills/` (loader · index · `build_skill_section` · `ensure_kernel_skills` · the tick mirror) + eight `SKILL.md`; `derive_recipes.py` DELETED; the ADR-157 playbook vestige DELETED (`get_type_playbook` family + `PLAYBOOK_METADATA` + the seeding and index blocks in `workspace.py`, zero live callers); `routes/lanes.py` binds `skill`; `lane_runner` composes the index + the skill section; hooks in `routes/workspace.py` + `jobs/unified_scheduler.py`; FE (`client.ts`, `ChatSurface`, `StudioSurface`, `LearnFromFlowModal`) names `skill`; the three stored skill-bound lanes re-slugged. Gate `api/test_adr630_skills.py` (falsified: a body in the index → red; a skill naming a resident → red; the tick mirror moved inside the steward gate → red). Re-anchored: test_adr452/456/562/579/597; test_adr450 deleted with the registry.
