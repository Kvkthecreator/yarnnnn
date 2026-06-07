# Reviewer Rename — Full Blast-Radius Map

> **Status**: Discourse / analysis. NOT canon. Companion to the DRAFT ADR-326 (de-naming the personified judgment seat). This document is the *evidentiary map* the ADR's decision rests on; it does not itself decide the name.
> **Date**: 2026-06-07
> **Authors**: KVK, Claude
> **Method**: every touchpoint below was grep-located 2026-06-07 against the working tree. Counts are at-time-of-scan; they drift, so the ADR's sequencing gate (ADR-326 §Migration) re-runs the sweep at execution time. No file below was edited — this is a map, not a migration.
> **Companion**: [ADR-326](../adr/ADR-326-denaming-the-personified-judgment-seat.md) (the decision). Prior rename precedents this map reuses: [ADR-201](../adr/ADR-201-team-rename-and-cross-linking.md) (layered-naming-by-audience), [ADR-265](../adr/ADR-265-activity-surface-rename-and-mode-discriminator.md) (surface rename + redirect stub), [ADR-282](../adr/ADR-282-axiom-8-ground-truth-rename.md) (canon-doc cascade + grep-gate + historical-ADR exemption).

---

## 0. Why this map exists separately from the ADR

The ADR makes one decision (the name) and one plan (the phased migration). This document is the **400+-reference enumeration** behind that plan, classified into three buckets so the migration is mechanical rather than exploratory. The same separation ADR-320's scope-amendment used (the post-ratification impact scan that surfaced Points 10–11) — a major rename earns a dedicated map because the cost of an *incomplete* sweep is a half-renamed surface that silently renders empty (ADR-320 Point 10: "the cockpit reads moved files and silently renders empty").

The three buckets, defined once and used throughout:

| Bucket | Definition | Migration treatment |
|---|---|---|
| **LABEL-rename** | Operator-facing strings, routes, nav, component identifiers whose audience is the operator. The word "Reviewer" the operator *reads*. | **Moves** to the new name in the atomic rename commit. |
| **code-slug-stays** | Internal enum values, DB column values, `authored_by` revision prefixes, filesystem path slugs, model-identity strings. Data-compat, never operator-surfaced. The same class as `thinking_partner` / `meta-cognitive` / `specialist:<role>` in the GLOSSARY Exceptions table. | **Stays.** Added to the GLOSSARY Exceptions table with the same rationale (migration cost ≫ reader benefit; never surfaced outside internals). |
| **canon-doc-edit** | Architecture docs, FOUNDATIONS/THESIS/GLOSSARY, the reviewer-* canon trio. The word "Reviewer" used as a *concept name* in prose. | **Cascades** per the ADR-282 discipline-rule pattern: rename where the prose means the *entity*, preserve where it means the *first Purpose* (review) or is a historical artifact. |

The load-bearing distinction — the one this whole rename pivots on — is **LABEL vs code-slug**. ADR-201 §6 canonized it as *layered-naming-by-audience*: the URL/nav is operator-vocabulary, the components/types/DB are substrate-vocabulary, each named for its consumer. The Reviewer rename is the same move at larger scale: the operator-facing label moves; the `role='reviewer'` / `authored_by="reviewer:…"` / `agent_class='reviewer'` data slugs stay.

---

## 1. The four-way distinction (read this before the buckets)

> **Updated 2026-06-07 after the ADR-326 discourse resolved the name.** The v1 of this section conflated "seat" and "entity" into one bullet — the exact conflation the operator's pushback corrected. They are *different*: the **seat** is an architectural abstraction (gets no operator name); the **operator-facing entity** is the named Persona. Four nameable things, the rename touches exactly one (deletes "Reviewer" from the operator surface; coins no new noun).

1. **The architectural seat** — the slot that persists while occupants rotate (Derived Principle 14 / ADR-315). **Gets NO operator-facing name** — "seat" is *technical* canon, the operator never says it. The rename does NOT touch it; "seat"/"occupant" survive as architectural vocabulary. *(This is the bullet v1 got wrong by trying to "name the seat.")*
2. **The operator-facing entity** — the personified judgment the operator relies on and talks about ("my ___ approved the trade"). Today labeled "Reviewer". **This is the ONLY thing the rename touches** — and the resolution is: it IS the named **Persona** (the operator authors + names it "Simons"); "Reviewer" is *deleted* with no coined replacement noun.
3. **The occupant's persona name** — operator-authored, per-workspace, lives in `persona/IDENTITY.md` (e.g., "Simons", "Buffett"). Already named, already operator-controlled, already surfaced ("Simons approved" via `web/lib/reviewer-persona.ts`). **The rename does NOT touch this.** This is what the blog post *Name Your Reviewer* is about — the operator names their Persona.
4. **The implementation slugs** — `role='reviewer'`, `agent_class='reviewer'`, `authored_by="reviewer:…"`, `REVIEWER_MODEL_IDENTITY="ai:reviewer-sonnet-v8"`, `/agents?agent=reviewer`, `reviewer_agent.py`. Data-compat code-slugs. **The rename does NOT touch these** (code-slug-stays).

The published marketing already operationalizes #2-vs-#3: *"Name Your Reviewer… Should Have A Persona"* = the operator names their Persona (#3), under the entity-label "Reviewer" (#2). **The de-naming resolution promotes "Persona" from #3's character-label to #2's entity-label** — the operator names a Persona, and that named Persona *is* the entity (no separate "Reviewer" entity-word above it). The character-word and the entity-word merge cleanly because they were always pointing at the same personified judgment. Everything in the buckets below is sorted against this: delete "Reviewer" where it meant #2; keep everything else.

---

## 2. LABEL-rename bucket (the operator reads these)

These move to the new seat-label in the atomic rename commit (ADR-326 §Migration). All are frontend or operator-facing.

### 2.1 Routes + route constants (`web/lib/routes.ts`)

| Location | Current | Classification | Note |
|---|---|---|---|
| `routes.ts:86` | `REVIEWER_ROUTE = "/agents?agent=reviewer"` | LABEL (constant) + code-slug (the `agent=reviewer` query value) | **Split decision.** The *constant name* `REVIEWER_ROUTE` → new-name route. The *query-param value* `agent=reviewer` is a code-slug (matches `agent_class='reviewer'` backend synthesis in `routes/agents.py:584`) — keeping it avoids a backend enum change. Precedent: ADR-251 kept `?agent=reviewer` as a bookmark-safety redirect target even while relabeling. **Recommended: relabel the constant, keep the query slug + add a bookmark-safety redirect** (the new label's deep-link resolves; `?agent=reviewer` 301s to it — ADR-201 §2 redirect-stub pattern). |
| `routes.ts:18` | comment `// /review deleted; Reviewer lives at /agents?agent=reviewer.` | canon-doc-edit (comment) | Update comment to new label. |
| `web/lib/supabase/middleware.ts` | `PROTECTED_PREFIXES` / redirect entries referencing reviewer route | LABEL | Add new deep-link; keep `?agent=reviewer` as legacy redirect (ADR-265 D1 pattern). |

### 2.2 Components — operator-visible labels + display strings

| Location | Current role | Classification | Note |
|---|---|---|---|
| `web/lib/agent-identity.ts` | `ROLE_META` registry entry for `reviewer` (display name, tagline, color, icon) | LABEL (display values) + code-slug (the `reviewer` key) | The **key** `reviewer` stays (matches `agent_class`); the **display name + tagline** strings move. Same split as ADR-251's `display_name` change without touching the role enum. |
| `web/components/agents/AgentContentView.tsx` | dispatches `agent_class='reviewer'` → reviewer detail; renders class label | LABEL (label string) + code-slug (dispatch key) | Dispatch key stays; the rendered class label string moves. |
| `web/components/agents/ReviewerActivityPanel.tsx` | component file + operator-facing panel title | LABEL | Component file *name* is substrate-vocabulary (ADR-201 §6 — may stay `Reviewer*`); the **panel title string** the operator reads moves. **Decision deferred to ADR-326 D-naming-policy**: ADR-201 kept `Agent*` component names; this map recommends the same — keep `Reviewer*.tsx` filenames, move only the rendered strings. |
| `web/components/agents/ReviewerCapabilitiesPanel.tsx` | same as above | LABEL (strings) + component-name-stays | Same policy. |
| `web/components/tp/ReviewerCard.tsx` | renders the verdict card; `ReviewerVerdictRenderer` | LABEL (card label) + component-name-stays | Card *label* moves; component name stays per layered-naming. |
| `web/components/tp/MessageDispatch.tsx` | `reviewer-verdict` message shape dispatch (`msg.role === 'reviewer'`) | code-slug (dispatch on `role='reviewer'`) | **Stays** — `role='reviewer'` is a `session_messages` data value (api side). The *rendered* persona label inside the bubble already comes from `reviewer-persona.ts` (occupant name), so the seat-label that appears is minimal. |
| `web/components/tp/MessageRow.tsx` | row wrapper, weight gating for reviewer rows | code-slug (role check) | Stays. |
| `web/lib/reviewer-persona.ts` | reads `persona/IDENTITY.md`, extracts occupant name | NOT-IN-SCOPE (occupant name, #1 above) + path-slug | The path `/workspace/persona/IDENTITY.md` is already de-name-compatible (ADR-320 D2b). The *fallback* string `"your Reviewer"` (when no persona authored) is a LABEL → moves. The file name `reviewer-persona.ts` is substrate-vocabulary → may stay. |
| `web/components/library/HomeHeader.tsx` | Constitution band — "Reviewer persona" label | LABEL | Operator reads it; moves. |
| `web/components/agents/page.tsx` | roster: systemic-agent card label for the seat; `?agent=reviewer` redirect handling | LABEL (card label) + code-slug (param) | Card label moves; param-redirect stays. |
| `web/components/feed/InvocationCard.tsx`, `web/components/feed-surface/WorkspaceContextOverlay.tsx`, `web/components/tp/ProposalCard.tsx`, `web/components/shell/chrome/ChatDrawer.tsx` | reviewer-attributed strings / labels | LABEL (where operator-read) + code-slug (role checks) | Per-occurrence triage at migration time; role-check logic stays, displayed strings move. |
| route pages: `web/app/(authenticated)/principles/page.tsx`, `files/page.tsx`, `agents/[id]/page.tsx` | "Reviewer" in headings / breadcrumbs | LABEL | Move. |

### 2.3 The frontend hardcoded-path debt (ADR-320 Point 10 overlap — verify, don't re-migrate)

ADR-320 Point 10 already migrated the *path* references (`review/` → `persona/`). The rename touches the *displayed labels* in those same files, not the paths. Verify ADR-320's path migration landed (it is a prerequisite — see ADR-326 sequencing gate) before relabeling, or the relabel commit collides with in-flight path edits.

---

## 3. code-slug-stays bucket (data-compat — never moves)

These are the same class as the GLOSSARY Exceptions table entries (`thinking_partner`, `meta-cognitive`, `specialist:<role>`). The ADR adds them to that table with identical rationale: **cross-cutting enum / data-format slug, renaming requires coordinated Python + TS + revision-backfill with zero user-visible benefit.**

| Slug | Location(s) | Why it stays |
|---|---|---|
| `role='reviewer'` | `session_messages.role` CHECK constraint (migration, ADR-237); `services/narrative.py:271`; `services/working_memory.py:1621`; `services/reviewer_chat_surfacing.py`; `web/components/tp/MessageDispatch.tsx` dispatch; `web/types/desk.ts` role union; `api/test_adr237_chat_role_grammar.py` | Chat-narrative role discriminator. Renaming = migration on `session_messages` CHECK + every dispatch site + historical rows. ADR-237 locked the six-role grammar (`user / assistant / system / reviewer / agent / external`). The operator never sees the literal `reviewer` — they see the rendered persona name (occupant) + the seat-label string. **Exact precedent: `role='thinking_partner'`** which the GLOSSARY Exceptions table keeps for the identical reason. |
| `agent_class='reviewer'` | `api/routes/agents.py:564,574,584` (Reviewer pseudo-agent synthesis, ADR-214); `web/types/index.ts` agent_class union; `AgentContentView` dispatch | Cross-cutting enum (Python → API → TS union → dispatch). Same shape as `meta-cognitive` in the Exceptions table. Maps to the new seat-label at the display layer; the enum stays. |
| `authored_by="reviewer:{identity}"` | `services/reviewer_audit.py:472`; `api/agents/cockpit_awareness.py:164`; ADR-209 revision records (immutable history); `web/components/workspace/RevisionHistoryPanel.tsx` author-tag rendering | Revision-chain data format. **Immutable** for historical revisions per ADR-209 (same as `authored_by="yarnnn:"` and `authored_by="specialist:<role>"` already in the Exceptions table). Renaming the prefix would orphan every historical revision's attribution. |
| `REVIEWER_MODEL_IDENTITY = "ai:reviewer-sonnet-v8"` | `api/agents/occupant_contract.py:49` | Occupant-identity string baked into `authored_by` attribution. Part of the published occupant-contract ABI (ADR-315). Bumping the version is normal occupant rotation; renaming `ai:reviewer-` is a data-format break. Stays. |
| `agents.role` DB value `thinking_partner` (adjacent) | already in Exceptions table | Not a reviewer slug, but the precedent the reviewer slugs follow. |
| filesystem path `persona/` | `workspace_paths.py`, `reviewer-seat-substrate.md`, etc. | Already chosen by ADR-320 D7 to be *de-name-compatible* — it denotes the detached judge regardless of the final name. **No move needed** — the rename was anticipated by the directory name. This is the single most important pre-positioning: the substrate path is already neutral. |
| `?agent=reviewer` query value | `routes.ts:86`, `routes/agents.py` synthesis | Matches `agent_class='reviewer'`. Kept as bookmark-safety redirect target (ADR-201 §2 / ADR-251 pattern). |

### 3.1 Module + test filenames (api/) — code-slug-stays by ADR-201 §6

`reviewer_agent.py`, `reviewer_agent_sections.py`, `reviewer_agent_compat.py`, `reviewer_envelope.py`, `reviewer_audit.py`, `reviewer_chat_surfacing.py`, `occupant_contract.py` (defines `REVIEWER_MODEL_IDENTITY`), and the test gates (`test_reviewer_*.py`, `test_adr301_reviewer_*`, etc.). Per ADR-201 §6 layered-naming, **code/module names are substrate-vocabulary and stay.** Renaming `reviewer_agent.py` → `{newname}_agent.py` would touch every import site (the four kernel callers per the occupant-contract: `services/programs.py`, `routes/feed.py`, `services/wake.py`, `services/review_proposal_dispatch.py`) plus the ADR-315 contract docs, for zero operator benefit. The occupant *implementation* keeps its name; only the operator-facing label moves. (A future L3 package carve — ADR-315 D6 — is the natural moment to reconsider module names, and it is independently deferred.)

---

## 4. canon-doc-edit bucket (prose concept-name)

The ADR-282 discipline is the template: **rename where the prose means the entity; preserve where it means the first Purpose (review) or is a historical artifact.** Counts at scan (2026-06-07): `docs/architecture/` 28 files mention "Reviewer"; `docs/adr/` 125 files; `docs/programs/` 61 files.

### 4.1 Core canon (the entity-name carriers — these cascade in the rename commit)

| Doc | What "Reviewer" is doing | Treatment |
|---|---|---|
| `FOUNDATIONS.md` Derived Principle 25 | Already states the entity is a "detached, personified judgment seat" and that *"Reviewer names its first Purpose, not the entity itself."* | **The de-naming's anchor.** DP25 already did the conceptual work; the rename *completes* it by giving the entity a name. Light edit: name the entity where DP25 currently says "the entity is the detachment + personification." Version bump. |
| `FOUNDATIONS.md` Derived Principle 21 | "Reviewer formalization" — the seven structural claims | Rename the *entity* references; "review" as the Purpose stays. |
| `FOUNDATIONS.md` Derived Principle 24 (ADR-319) | "The Reviewer owns the operation's governing intent…" | **Stewardship elevation — see §6.** This is now ownership, not review. Strong motivation for the rename; the prose should name the *owner*, not the *reviewer*. |
| `FOUNDATIONS.md` Derived Principle 14/15 | "Agent seats persist; occupants rotate" — Reviewer as canonical seat | Rename entity references; seat≠occupant framing preserved. |
| `THESIS.md` Commitment 2 | "Independent judgment — the reviewer is a durable role" | Per the discourse §4: independence travels with *detachment*, not the word "review." Rename the entity; the independence claim is unaffected. |
| `GLOSSARY.md` | `Reviewer` entry (L208), `Reviewer seat` (L210), `Reviewer identity` (L261), Constitution band reference (L56) | **The single vocabulary home** (ADR-282 D6 pattern). New entity-name entry; `Reviewer` becomes "the first Purpose / legacy label" cross-reference. Add the code-slugs (`role='reviewer'`, `agent_class='reviewer'`, `authored_by="reviewer:"`) to the **Exceptions table** (§3 above). |
| `reviewer-seat-substrate.md` | seat canon — "the Reviewer seat" throughout | Rename entity references to the new seat-name; the seat≠occupant split (the doc's whole purpose) is preserved. Filename: substrate-vocabulary, **may stay** `reviewer-seat-substrate.md` or move — ADR-326 D-naming-policy decides (recommend: rename the canon-trio filenames since they are concept docs, not code, unlike api/ modules). |
| `reviewer-occupant.md` | occupant canon | Same treatment. |
| `reviewer-occupant-contract.md` | published ABI (ADR-315) | The ABI *symbols* (`ReviewerContext`, `REVIEWER_MODEL_IDENTITY`) are code-slugs and stay; the prose entity-name moves. |
| `agent-composition.md` §3.2.1 / §4.4 | persona-frame partition; near-full self-amendment authority | Entity references rename; the partition discipline is name-agnostic. |
| `LAYER-MAPPING.md` | authoritative Agent/Orchestration taxonomy — "Reviewer is the sole systemic persona-bearing Agent" | Rename entity references. |

### 4.2 Historical ADRs (~125 mention Reviewer) — NOT edited (ADR-282 D8 / ADR-259 precedent)

Per the established precedent (ADR-282 D8, ADR-259, GLOSSARY Exceptions table row for historical ADRs): **historical ADRs are dated artifacts; they are not rewritten when terms change.** The ~50+ ADRs that say "Reviewer" (ADR-194, 195, 211, 212, 217, 247, 248, 251, 252, 253, 256, 258, 273, 280, 281, 282, 284, 285, 295, 306, 307, 315, 319, 320, …) stand as records of the decisions in force at their time. The supersession (ADR-326) is the record. A retroactive vocabulary banner is *optional* on the highest-traffic ones (ADR-194, ADR-315, ADR-319, ADR-320) per the ADR-259 banner pattern — the ADR decides.

### 4.3 Programs (~61 files mention reviewer) — bundle reference-workspaces

`docs/programs/{alpha-trader,alpha-author,…}/reference-workspace/persona/` (already re-rooted by ADR-320) + `principles.md` + `MANIFEST.yaml` `reviewer_wake_envelope` substrate-ABI block + SURFACES.yaml. The substrate *paths* are already neutral (`persona/`). The bundle prose that says "Reviewer" is operator-canon (forked into workspaces) → cascades with the canon docs. The `reviewer_wake_envelope` MANIFEST key is a code-slug-class identifier (read by `services/bundle_reader.py`) → **stays** (ADR-282 D10 precedent: SURFACES binding keys are instance-level operational identifiers, preserved).

### 4.4 Published blog posts — operator-facing content, NOT edited

Three published posts carry "reviewer" in the slug + title:
- `content/posts/name-your-reviewer.md` — *"Name Your Reviewer: Why AI Judgment Should Have A Persona"*
- `content/posts/you-dont-need-more-models-you-need-a-reviewer.md` — *"You Don't Need More Models. You Need A Reviewer."*
- `content/posts/the-reviewer-seat-is-what-single-agent-architectures-cant-add.md` — *"The Reviewer Seat Is What Single-Agent Architectures Can't Add"*

Per ADR-282 (does-not-edit blog posts using `money-truth`) + ADR-259 (historical-artifact precedent): **published posts are dated content, not edited.** They are part of the public record at their publication date. **However** — and this is a first-class motivation for the name decision (§6, and ADR-326 §Name-Decision) — these posts are *active marketing* and the word "Reviewer" is doing *positioning* work, not just labeling. The rename either (a) keeps "Reviewer" as the public-facing word and renames only the internal/cockpit entity (a *narrower* rename), or (b) commits to re-positioning future content under the new word while the published posts stand as the historical-name record. **This is the single biggest strategic input to the name choice** and the ADR must decide it explicitly. The blog is not a blast-radius cost to clean up — it is *evidence about whether "Reviewer" is the right word at all*, because it is the word that already tested in market.

---

## 5. Count summary (the honest scope, scan 2026-06-07)

| Surface | Reference count | Dominant bucket |
|---|---|---|
| `docs/adr/` | 125 files | canon-doc-edit (mostly historical → NOT edited per §4.2) |
| `api/` (.py) | 167 files | code-slug-stays (modules, role checks, attribution) |
| `web/` (.ts/.tsx) | 61 files | mixed — LABEL (strings) + code-slug (role/class dispatch) |
| `docs/programs/` | 61 files | canon-doc-edit (bundle prose) + code-slug (MANIFEST keys) |
| `docs/architecture/` | 28 files | canon-doc-edit (the entity-name carriers, §4.1) |
| `content/posts/` | 3 files | NOT edited; strategic input (§4.4) |

**The honest reading of these counts**: the *raw* number is large (~400+ references), but the *migration* number is small. The vast majority are either **code-slug-stays** (the data slugs the ADR adds to the Exceptions table — they don't move) or **historical artifacts** (ADRs + blog posts — not edited). The actual moving parts are: ~15-20 frontend display strings (§2.2), ~10 core canon docs (§4.1), the GLOSSARY entry + Exceptions additions, and route-constant relabel + redirect stub. That is an ADR-201-class single-commit-plus-cascade, not an ADR-320-class multi-phase migration — **because ADR-320 already did the hard part** (re-rooting `review/` → `persona/` so the substrate paths are name-neutral, and the data slugs were always going to stay).

---

## 6. The stewardship elevation (ADR-319) as name-weight (the motivation, not a bucket)

This is not a touchpoint — it is *why the name now matters more than when ADR-320 D7 deferred it.*

When D7 was written (2026-06-05), the entity's job, in canon, was still primarily *reviewing proposed actions* — verdicts on `action_proposals`. "Reviewer" was a Purpose-label that, while incomplete (discourse §4), was at least *accurate* to the dominant activity.

**ADR-319 (also 2026-06-05, ratified) changed the entity's job description at kernel altitude.** Derived Principle 24: the entity now *owns* the operation's governing intent and *revises it against ground truth at two altitudes* — within the intent (the compliance/review loop) AND on the intent (the ownership loop: re-declaring the mandate when reconciled reality falsifies it). The entity is *the operator's installed principal*, the same principal one wake later, with consequence-anchored urgency and stewardship-deferred-is-stewardship-denied discipline.

A *reviewer* checks someone else's work. A *steward / principal / owner* holds the mandate and revises it. **The word "Reviewer" now names the entity's *first sub-goal* (altitude-1 compliance), not its job (altitude-2 ownership).** The mismatch the discourse §4 flagged ("Reviewer labels a Purpose, not the axiom") became sharper after ADR-319: the entity's load-bearing property is now *stewardship/ownership*, and "review" is one altitude of it.

This is the ADR-326 motivation: **the rename is no longer a tidiness pass; it is a correction of a name that now actively under-describes the entity's canonical authority.** The name must denote the *detachment + personification + ownership* (from which both independence AND stewardship follow), not the review function.

---

## 7. Sequencing dependency (why this map ships before the rename executes)

Two backend streams are in flight at scan time and saturate exactly the surface a rename would touch:

1. **The primitive-evolution arc ADR-321–325** (path-native file primitives, entity-layer pruning, persona-frame collapse finish, InferContext dissolution, Embed primitive). These touch `reviewer_agent.py`, the primitives registry, `REVIEWER_PRIMITIVES`, the persona-frame sections, and `InferContext` (which has identity-inference targeting `persona/IDENTITY.md`). A rename commit landing mid-arc would collide on the same files.
2. **A self-writing E2E validation** saturating the eval core + reviewer invocation path.

The rename **must not execute until both have landed** (ADR-326 §Sequencing Gate). This map exists *now* so the design is settled and the execution is a known-quantity single commit the moment the gate opens — exactly the ADR-236 Rule 8 "draft → implement → land just-in-time" discipline, applied to a high-blast-radius rename. The map is the draft; the ADR is the decision; the execution waits for the gate.

---

## 8. Provenance

- Code/canon receipts (grep-located 2026-06-07 on branch `docs/adr-326-denaming-the-judgment-seat`): `web/lib/routes.ts` (REVIEWER_ROUTE + AGENTS_ROUTE), `web/lib/agent-identity.ts` (ROLE_META), `web/lib/reviewer-persona.ts` (occupant-name resolution, `persona/IDENTITY.md` path), `web/components/agents/{ReviewerActivityPanel,ReviewerCapabilitiesPanel,AgentContentView}.tsx`, `web/components/tp/{ReviewerCard,MessageDispatch,MessageRow}.tsx`, `api/agents/occupant_contract.py` (REVIEWER_MODEL_IDENTITY), `api/routes/agents.py:564-584` (agent_class='reviewer' synthesis), `api/services/reviewer_audit.py:472` (authored_by prefix), `api/services/narrative.py:271` + `working_memory.py:1621` (role='reviewer'), `content/posts/{name-your-reviewer,you-dont-need-more-models-you-need-a-reviewer,the-reviewer-seat-is-what-single-agent-architectures-cant-add}.md`.
- Canon receipts: FOUNDATIONS Derived Principle 25 (entity is detached personified judgment seat; "Reviewer names its first Purpose") + DP24 (stewardship/ownership) + DP21 (formalization) + DP14/15 (seat≠occupant); GLOSSARY Reviewer/Reviewer-seat/Reviewer-identity entries + Exceptions table (`thinking_partner` / `meta-cognitive` / `specialist:<role>` precedent); reviewer-seat-substrate.md (`persona/` re-root, ADR-320), reviewer-occupant.md, reviewer-occupant-contract.md (ABI symbols as code-slugs).
- Precedent ADRs: ADR-201 (layered-naming-by-audience §6 + redirect-stub §2), ADR-265 (surface rename + redirect + PROTECTED_PREFIXES), ADR-282 (canon cascade + discipline-rule + grep-gate + historical-ADR exemption D8 + does-not-edit-blog), ADR-251 (kept `?agent=reviewer` as bookmark-safety while relabeling display_name), ADR-320 D7 (de-naming scoped out; `persona/` chosen de-name-compatible), ADR-319 (stewardship elevation).
