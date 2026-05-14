# ADR-272: Identity-Layer Collapse — System Agent → Ambient Activity, Specialists → Single Production Role

**Status**: **Proposed 2026-05-14** (resolves ADR-271 Threads B + C combined, with Phase 1 BE landing in this ADR and Phase 2 FE sequenced as a follow-on per operator decision)

**Companion ADRs (atomic together — same architectural arc as ADR-271)**:
- ADR-271 — Bundle Authoring Discipline + Identity-Layer Audit (Threads A + D Implemented; B + C resolved here)

**Supersedes**:
- ADR-251 — System Agent + Reviewer as First-Class Surfaces. The roster-card decision is reversed. The `meta-cognitive` DB row stays as the chat-mode LLM substrate but is no longer rendered as a cockpit peer entity.
- ADR-247 — Three-Party Narrative Model (operator + System Agent + Reviewer). Collapses to a two-voice model + ambient mechanical activity stream. The `role='system_agent'` chat-bubble shape dissolves.
- ADR-261 D7 (in scope, not in mechanism) — six universal specialist roles. The mechanism (DispatchSpecialist primitive + headless tool surface) survives unchanged. The roster narrows to one role: `designer`.

**Amends**:
- ADR-176 — Work-First Agent Model (six specialist roles). Four roles dissolve (researcher, analyst, writer, tracker, reporting); one survives (designer). The "universal specialist roster" framing reframes to "production-shape escape hatch."
- ADR-216 — Orchestration vs Judgment vocabulary. Strengthens the orchestration-as-plumbing position; the System Agent label is removed as a cockpit entity. YARNNN-as-orchestration stays as canonical vocabulary for the chat LLM identity.
- ADR-117 — Role-keyed style distillation. With only `designer` surviving as a role, `/workspace/style/{role}.md` collapses to `/workspace/style/designer.md` (or dissolves entirely if asset rendering doesn't accumulate style).

**Preserves**:
- FOUNDATIONS Axiom 2 (Identity) — four identity layers remain: Operator, YARNNN orchestration (chat LLM), Reviewer, persona-bearing Agents (user-authored).
- ADR-194 v2 Reviewer substrate — unchanged.
- ADR-195 v2 money-truth substrate — unchanged.
- ADR-209 Authored Substrate — every revision attributed; ambient activity writes retain their `authored_by` provenance.
- ADR-260 / ADR-261 / ADR-262 — real-time Reviewer loop, recurrences as prompts, output topology — all unchanged.
- ADR-263 — recurrence mode (mechanical vs judgment) — unchanged.
- ADR-264 — SyncPlatformState + substrate-canonical-world axiom — unchanged.
- ADR-271 Threads A + D — mechanical migration + dead-headless-path sweep — both stay landed; this ADR builds on the cleaner picture they produced.

**Dimensional classification**: **Identity** (Axiom 2) primary — restructures which identity layers surface in the cockpit; **Channel** (Axiom 6) secondary — collapses chat bubble shapes and dissolves the System Agent cockpit surface; **Mechanism** (Axiom 5) tertiary — production work moves from sub-LLM dispatch to inline Reviewer execution in all but one case.

---

## 1. Why this ADR

The session-2026-05-14 audit revealed two structural drift patterns that ADR-271 Threads A + D could not fully resolve:

1. **System Agent as a cockpit peer entity (ADR-251) has no LLM identity backing it.** Audit confirmed: `system-agent` is a label used in three places (regex execution router narration, Reviewer-directed action narration via `reviewer_chat_surfacing.py`, cockpit roster card and detail surface). None of these is an LLM. The DB row labeled `role='thinking_partner'` with `agent_class='meta-cognitive'` is the chat-mode LLM substrate (yarnnn.py / feed routing), not a separate executor. The cockpit's depiction of System Agent as a peer of Reviewer mislabels orchestration plumbing as an entity.

2. **The specialist roster (ADR-176 / ADR-261 D7 — six universal roles) is wider than the work demands.** Audit overnight token usage: 4 of 6 roles (tracker, analyst, researcher, plus implicitly reporting and writer never invoked) accounted for 100% of specialist dispatches. Three of those (tracker, analyst, researcher) were dispatched primarily for *mechanical work miscategorized as production* — which ADR-271 Thread A just collapsed at the recurrence level. The remaining live specialist demand sits in production-shape work that genuinely needs a different tool surface (designer for asset rendering) and weak voice-vs-vibe arguments (writer for prose composition).

The first-principles re-test against the bar the operator raised (*"surviving specialist should be true to the standard we're now defining and hardening"*) found:

- **Designer survives all three structural tests** (tool surface meaningfully different — RuntimeDispatch; output size genuinely large — binary assets; latency long enough to warrant non-blocking sub-context — 10-60s renders).
- **Writer fails the tool surface test** (uses WriteFile + read tools, which the Reviewer has already). Voice differentiation is a prompt-level concern (BRAND.md + IDENTITY.md merge), not a separate-LLM concern.
- **Researcher / analyst / tracker / reporting fail multiple tests** — their work is judgment-adjacent (investigation, analysis, accumulation, synthesis) that the Reviewer does inline using the same tool surface.

Independently, the live-invocation audit (commit `54eadf6`, Thread D) confirmed only two LLM-invocation paths exist — scheduler-fired and chat-addressed — and both route through `invoke_reviewer()`. The single LLM identity that holds standing intent on behalf of the operator is the Reviewer. Everything that surfaces as `system_agent` narration is either deterministic dispatch (no LLM) or a render of Reviewer-directed actions (the Reviewer's tool calls). Per the Claude Code analogy: *tool outputs surface as the calling LLM's tool results, not as a separate participant in the conversation.*

This ADR commits to two collapses (System Agent → ambient activity; specialists → single production role), in one BE phase landing now, with the cockpit FE work sequenced as a follow-on phase after BE bakes.

---

## 2. Decisions

### D1 — System Agent dissolves as a cockpit entity; ambient activity replaces it

The `meta-cognitive` DB row persists (it's the chat-mode LLM substrate referenced by `routes/feed.py` for the orchestration profile). The cockpit surface changes:

- **`/agents` roster card for System Agent: REMOVED.** The roster shows Reviewer + user-authored agents only.
- **`/agents?agent=system` detail surface: REMOVED.** No Identity / Mandate / Back Office tabs. The legacy redirects (`?agent=yarnnn → ?agent=system`, `?agent=thinking-partner → ?agent=system`) collapse — these query strings 404 (clean URL surface, no silent forwarding to a dissolved surface).
- **`api/routes/agents.py::list_agents` synthesis**: the YARNNN/system synthesis stops surfacing the meta-cognitive row in the cockpit-facing list response. Reviewer pseudo-agent synthesis (ADR-214) stays — Reviewer is a real identity layer.

Backend writes that previously used `role='system_agent'` on `session_messages` continue to write (no schema change), but the FE renders them as ambient-activity rows in the feed, not as participant bubbles. See D2.

**Singular implementation honored**: there is no parallel "System Agent is sometimes an entity, sometimes activity" rendering. Post-collapse, every system-shaped narration row renders as ambient activity. No conditional code path keyed on legacy compat.

### D2 — Chat narrative collapses to two participant voices + one ambient activity stream

The seven bubble shapes in `MessageDispatch.tsx` (`user-bubble`, `system-agent-bubble`, `system-bubble`, `agent-bubble`, `reviewer-verdict`, `system-event`, `external-event`) collapse to:

- **`user-bubble`** — operator speaks (unchanged).
- **`reviewer-bubble`** — single shape covering both Reviewer verdicts (reactive trigger) and Reviewer addressing turns. The visual treatment may distinguish verdict-shape from address-shape via a `mode` prop on the same component; the underlying `role='reviewer'` is one shape, not two.
- **`agent-bubble`** — user-authored persona-bearing agents (unchanged — preserves future user-authored Agent surface per ADR-216).
- **`system-activity`** — single ambient shape for everything mechanical: regex execution router output, Reviewer-directed action narration (FireInvocation completed, WriteFile written, etc.), mechanical recurrence completions, system events. Background-weight visual treatment (muted color, no avatar, no "speaks" framing). Operator can collapse/filter; default rendering is visible but de-emphasized.
- **`external-event`** — DELETED. Platform-originated events (webhooks etc.) are either dead code (per Thread D's deletion of the Slack event-trigger path) or render as `system-activity` if they survive.

Backend roles on `session_messages`:
- `'user'` — preserved.
- `'reviewer'` — preserved.
- `'agent'` — preserved.
- `'system_agent'` — preserved as a write target by `reviewer_chat_surfacing.py` and `execution_router.py` (BE writers don't change in this phase). FE renders these rows as `system-activity` shape.
- `'assistant'` — legacy compat (per ADR-252 D4 backward-compat note). FE renders as `system-activity`. *No new writes use this role.*
- `'system_event'` / `'external_event'` — FE rendering moves to `system-activity`. BE writers stay as-is for this ADR's BE phase; deprecation of unused roles deferred to FE phase audit.

**Singular implementation honored**: post-FE-phase, exactly four bubble shapes in MessageDispatch (`user-bubble`, `reviewer-bubble`, `agent-bubble`, `system-activity`). No fallback shape for legacy role values — they all dispatch to `system-activity`.

### D3 — VALID_SPECIALIST_ROLES narrows to `{designer}`

`VALID_SPECIALIST_ROLES` in `api/services/primitives/dispatch_specialist.py` shrinks from six entries to one: `{"designer"}`.

Removed roles (with structural rationale per the bar test):

| Role | Tool surface test | Output size test | Latency test | Verdict |
|---|---|---|---|---|
| `researcher` | ⚠ ReadFile/WebSearch/WriteFile — same as Reviewer's surface | small (markdown findings) | seconds, not minutes | Dissolve. Reviewer does investigation inline. |
| `analyst` | ⚠ ReadFile/SearchFiles — same as Reviewer's surface | small (analysis prose) | seconds | Dissolve. Reviewer reads context + writes assessment inline. |
| `writer` | ⚠ ReadFile/WriteFile + BRAND.md — same as Reviewer's surface | small-medium (1-3K prose) | seconds | Dissolve. Voice = prompt-level concern; Reviewer reads BRAND.md and writes in-voice inline. |
| `tracker` | ⚠ Platform tools + WriteFile — Reviewer has both | small per-entity | seconds per entity | Dissolve. Most tracker work was actually mechanical (see ADR-271 Thread A — track-universe / track-regime mechanicalized). Residual tracker dispatches collapse to inline Reviewer-loop tool calls. |
| `reporting` | ⚠ ReadFile/SearchFiles + WriteFile — same as Reviewer | medium (cross-domain synthesis) | seconds | Dissolve. Cross-domain synthesis is what the Reviewer's wakes produce by design. |
| `designer` | ✓ RuntimeDispatch (asset rendering, image gen) | ✓ binary assets, multi-section HTML | ✓ 10-60s renders | **Survives.** |

The bar test (three structural conditions, all-or-nothing) is canonized in this ADR as the discipline for future additions:

> *To enter `VALID_SPECIALIST_ROLES`, a role must clear ALL THREE tests: meaningfully different tool surface from the Reviewer's; output size genuinely crowding judgment context; latency long enough that blocking the Reviewer's loop degrades operator experience. Failing any single test is rejection. Vibe arguments (different voice, different style) are not sufficient — they're prompt-level concerns, not LLM-identity concerns.*

This is the **specialist survival test**. Future ADRs adding roles must explicitly justify against it.

`PRODUCTION_ROLES` registry in `api/services/orchestration.py` shrinks correspondingly: six entries → one (`designer`). The associated playbook content (`_playbook-*.md` files inside each role's `methodology` dict) for the five dissolved roles is deleted.

### D4 — DispatchSpecialist primitive + headless tool surface infrastructure PRESERVED

The mechanism stays. Only the role catalog narrows:

- `DispatchSpecialist` primitive: unchanged.
- `handle_dispatch_specialist`: unchanged except the role-validation set narrows to `{designer}`.
- `HEADLESS_PRIMITIVES`: unchanged. Specialist sub-calls still use this tool surface.
- `_SPECIALIST_FRAME` prompt: unchanged in shape; the role-specific guidance is supplied per-call via `default_instructions` from PRODUCTION_ROLES (now only designer's).
- Three caller surfaces (REVIEWER_PRIMITIVES, CHAT_PRIMITIVES, HEADLESS_PRIMITIVES) all still include DISPATCH_SPECIALIST_TOOL.

**Future-additivity check**: if a future ICP requires a new specialist role (e.g., `coder` for code-generation, `auditor` for compliance review), the addition is mechanical — add an entry to PRODUCTION_ROLES + VALID_SPECIALIST_ROLES, ship the role's methodology playbook, document in the ADR that introduces it. No primitive surface changes, no scaffolding work. The bar test applies — the new role must pass.

### D5 — Imperative collapse: bundle recurrences absorb their specialist work

The alpha-trader bundle's `_recurrences.yaml` is audited for recurrences that previously implied specialist dispatch. For each:

- **`falsify-signals`**: DELETED as a standalone recurrence. The 90-day historical falsification intent moves into `morning-reflection`'s prompt as a precondition the Reviewer checks: *"if `/workspace/research/findings/` is empty AND `_performance.md` has no live outcomes yet, fetch bars and write per-signal findings before reasoning about today's posture."* The Reviewer does this work inline using platform tools + WriteFile directly. No specialist dispatch, no brief boundary.
- **`pre-market-brief`**: Reviewer composes the brief inline using BRAND.md / IDENTITY.md / regime + universe substrate. If a chart asset is part of the brief shape, the Reviewer dispatches `designer` for that one asset; the prose surrounds it.
- **`signal-evaluation`**: Reviewer evaluates signals inline against fresh ticker substrate (which Thread A's mechanical track-universe now populates deterministically). No specialist needed.
- **`morning-reflection` / `morning-calibration` / `weekly-performance-review` / `quarterly-signal-audit`**: judgment-mode wakes, Reviewer composes inline. Charts dispatched to designer if needed.
- **`outcome-reconciliation`**: stays judgment-mode for now; the reconciliation-half computation is judgment-adjacent (deciding when fills satisfy expected outcomes). A future ADR may mechanize the deterministic portion (mirror-half), per ADR-264 §"Reconciliation half."

**No bundle recurrence ships with explicit specialist dispatch in its prompt.** The Reviewer decides at runtime whether `designer` is warranted. The bundle's job is to wake the Reviewer with the right standing intent and substrate context.

### D6 — `/workspace/research/` directory retained; `falsify-signals` substrate moves to inline write target

ADR-270 added `/workspace/research/mandate.md` + `/workspace/specs/falsify-signals.md`. Both stay. The findings directory `/workspace/research/findings/{signal_id}.md` continues to be the write target, but the writes happen inline within `morning-reflection`'s Reviewer wake when the bootstrap precondition fires, rather than in a dedicated `falsify-signals` recurrence dispatch.

This is consistent with ADR-262 (filesystem-native output without registries) — the path topology is workspace-shaped, the writer changes.

### D7 — Doc-radius cascade

This ADR is the canonical place a future reader looks for the System Agent ↔ ambient activity reversal AND the specialist narrowing. The following docs receive companion updates *in the same commit* per CLAUDE.md execution discipline:

- `docs/adr/ADR-271-bundle-and-identity-discipline.md` — Threads B + C marked Implemented, pointing to this ADR.
- `docs/adr/ADR-247-three-party-narrative-model.md` — superseded banner pointing to this ADR (the three-party model collapses).
- `docs/adr/ADR-251-system-agent-reviewer-first-class-surfaces.md` — superseded banner pointing to this ADR (System Agent surface dissolved).
- `docs/adr/ADR-176-work-first-agent-model.md` — amendment note (six roles → one).
- `docs/adr/ADR-216-orchestration-surface-vs-judgment-persona.md` — amendment note (System Agent label removed as cockpit entity; YARNNN-as-orchestration unchanged at the vocabulary level).
- `docs/adr/ADR-261-recurrences-as-prompts.md` — D7 amended note (specialist roster narrows; mechanism unchanged).
- `docs/architecture/FOUNDATIONS.md` — Axiom 2 Identity table updated (System Agent removed as named entity; orchestration layer described as chat LLM identity, not a peer cockpit entity).
- `docs/architecture/LAYER-MAPPING.md` — System Agent vocabulary removed; orchestration-layer description tightened.
- `docs/architecture/GLOSSARY.md` — System Agent entry removed; Specialist entry narrowed to "designer only, escape hatch for production-shape work."
- `docs/architecture/primitives-matrix.md` — VALID_SPECIALIST_ROLES count updated; specialist survival test referenced.
- `CLAUDE.md` — Project Overview / Key terminology blocks updated. Specifically:
  - "PRODUCTION_ROLES" enumeration narrows.
  - "System Agent" no longer a key term; orchestration vocabulary tightens.
- `api/agents/prompts/platforms.py` — production-role enumeration in the prompt narrows to designer.
- `api/agents/prompts/chat/workspace.py` — specialist-roster mention updates (the "Available roles" list collapses to designer + a note that the Reviewer does most production work inline).
- `api/prompts/CHANGELOG.md` — entry per behavioral-artifacts discipline.

---

## 3. What this ADR does NOT do

- **No FE cockpit work in this BE phase**. The `/agents` roster card removal, detail surface removal, chat bubble shape collapse, and legacy redirect handling all ship in a sequenced Phase 2 FE commit after BE bakes. Operator sequencing decision: BE first to validate runtime invariants, FE second once BE is observed in production.
- **No schema changes**. `session_messages.role` constraint stays. `agents.role='thinking_partner'` row stays. No migrations.
- **No primitive registry surgery**. DispatchSpecialist primitive + headless tool surface remain in all three caller surfaces. The mechanism is preserved; only the role catalog narrows.
- **No deletion of `dispatch_specialist.py`**. The file stays; it serves designer dispatch. The role-validation set narrows but the dispatcher's shape doesn't change.
- **No change to FOUNDATIONS axioms**. Axiom 2's four identity layers are preserved; the cockpit surface stops over-instantiating the orchestration layer as two entities.
- **No change to ADR-209 attributed-substrate writes**. `authored_by` provenance on every write is unchanged.
- **No re-introduction of `falsify-signals` substrate machinery**. ADR-270's `/workspace/research/mandate.md` + `specs/falsify-signals.md` stay; only the writer (recurrence vs inline Reviewer wake) changes.
- **No changes to mechanical recurrences from Thread A**. `TrackUniverse` + `TrackRegime` primitives are unchanged; alpha-trader mechanical-mirror recurrences unchanged.

---

## 4. Phase 1 — BE implementation (this ADR commit)

Concrete code changes:

1. **`api/services/primitives/dispatch_specialist.py`**: `VALID_SPECIALIST_ROLES = {"designer"}` (was 6-element set). Tool schema's role enum updated. Docstring rewritten to reflect the survival test + the one-role reality + why other roles dissolved.

2. **`api/services/orchestration.py`**: `PRODUCTION_ROLES` dict shrinks to one entry (`designer`). The five dissolved entries (researcher / analyst / writer / tracker / reporting) and their methodology playbooks are deleted. The `ALL_ROLES` union (SYSTEMIC_AGENTS + PRODUCTION_ROLES) shrinks correspondingly.

3. **`api/agents/prompts/platforms.py`**: production-role enumeration updates to designer-only + a sentence framing inline-Reviewer execution for non-asset production work.

4. **`api/agents/prompts/chat/workspace.py`**: "Available roles" section collapses to designer; the YAML example showing `agents: ["researcher", "writer"]` is replaced with a note that the Reviewer does most production work inline and dispatches `designer` only for asset/render work.

5. **`docs/programs/alpha-trader/reference-workspace/_recurrences.yaml`**: `falsify-signals` recurrence DELETED. `morning-reflection`'s prompt extended with the bootstrap-research precondition. Bundle ships with one fewer recurrence (was 16, now 15).

6. **`docs/programs/alpha-trader/reference-workspace/review/principles.md`**: bootstrap-clause language updated to reference inline-Reviewer falsification (rather than awaiting a falsify-signals dispatch).

7. **Doc-radius cascade** (per D7) applied in the same commit. All listed ADRs and architecture docs updated.

8. **`api/prompts/CHANGELOG.md`** entry per behavioral-artifacts discipline.

9. **Regression gates updated**:
   - `api/test_adr269_capability_flow.py`: production-role expectations updated where the test inspects PRODUCTION_ROLES contents. Mechanical-mirror invariants from Thread A unchanged.
   - `api/test_adr261_phaseB.py`: DispatchSpecialist registry assertions unchanged (primitive surface preserved). VALID_SPECIALIST_ROLES content assertion added.
   - New ADR-272-specific gate (e.g., `api/test_adr272_identity_collapse.py`) asserting `len(VALID_SPECIALIST_ROLES) == 1`, `"designer" in VALID_SPECIALIST_ROLES`, falsify-signals not in bundle, morning-reflection prompt contains bootstrap precondition.

10. **`docs/adr/ADR-271-bundle-and-identity-discipline.md`** status updated: Threads B + C marked Implemented (pointing to this ADR).

---

## 5. Phase 2 — FE implementation (sequenced, separate commit after BE bakes)

Scoped here but not landing in this ADR's commit:

1. **`web/lib/routes.ts`**: `?agent=system` / `?agent=yarnnn` / `?agent=thinking-partner` redirect logic removed. Stale links 404 cleanly.
2. **`web/app/(authenticated)/agents/page.tsx`**: roster card for System Agent removed. `meta-cognitive` branch in detail dispatcher removed. The redirect block (ADR-251 D7) deleted.
3. **`web/components/agents/AgentContentView.tsx`**: `meta-cognitive` branch (`ThinkingPartnerDetail` / System Agent tabs) DELETED. The `cls === 'meta-cognitive'` early-return path is removed; the synthesized `meta-cognitive` row is filtered out at the data layer instead.
4. **`web/components/tp/MessageDispatch.tsx`**: bubble shape consolidation. The four final shapes (`user-bubble`, `reviewer-bubble`, `agent-bubble`, `system-activity`) are the only paths. `system-agent-bubble`, `system-bubble`, `system-event`, `external-event` cases collapse to `system-activity` dispatch.
5. **`web/components/tp/`**: new `SystemActivity` component for the ambient row shape (background-weight visual treatment, no avatar, optional collapse).
6. **Reviewer bubble shape**: unified component handling both verdict-render (current `reviewer-verdict`) and addressing-turn-render (current Reviewer-shaped bubbles). Variant prop dispatches the layout.
7. **Operator-legibility floor** (per the bar): cockpit or `/work` must visibly surface "system activity / recurrence health" before System Agent's roster card removal. Likely candidate: a small "Recent system activity" pane on `/work` list view, or a cockpit-face addition. Decided in Phase 2 design pass before FE code lands.
8. **Test/audit**: end-to-end manual smoke on chat narrative (no missing bubbles), `/agents` roster (Reviewer only on systemic side), `/work` (recurrence health visible), `/agents?agent=system` (404 clean).

---

## 6. Operator-legibility analysis

The strongest counter-argument to System Agent collapse is operator UX: today, an operator opening `/agents?agent=system` sees three tabs describing what the orchestration layer does. Post-collapse, where does that information surface?

Mapping:

| Information today | Where it surfaces post-collapse |
|---|---|
| "Identity" tab (operating contract — System Agent's role) | DELETED — was misleading (no real IDENTITY.md). Orchestration is described in the workspace's MANDATE.md as "how YARNNN operates," not as a peer entity. |
| "Mandate" tab | DELETED — System Agent had no separate mandate from the operator's workspace mandate. |
| "Back Office" tab — recurrence health, schedule, last-run | `/work` list view (mechanical recurrences are first-class items there). Cockpit face for recurrence health if the FE Phase 2 surfaces it as a glance. |
| Recent system activity (run completions, narration) | `system-activity` rows in the feed. Operator scrolls feed to see what just happened. |
| "What is the system doing for me?" framing | The operator's mandate answers this. The recurrences (cron-fired wakes) enact it. The Reviewer judges. There is no peer entity called "the system." |

The collapse is honest only if the Phase 2 FE work ships a clear `/work` or cockpit recurrence-health surface. The operator-legibility floor is **non-negotiable** before the FE phase commits.

---

## 7. The specialist survival test — canonized for future ADRs

Recorded here as the discipline for any future addition to `VALID_SPECIALIST_ROLES`. Future ADRs proposing a new specialist must include an explicit pass against this test.

**Three structural tests, all-or-nothing:**

1. **Tool surface test** — does the role use a meaningfully different tool surface from the Reviewer's? "Meaningfully different" means at least one tool the Reviewer should *not* have in its standing surface (e.g., RuntimeDispatch for asset rendering). A subset of the Reviewer's tools is not different — it's the same surface used differently.

2. **Output size test** — does the role produce outputs large enough to crowd the Reviewer's judgment context? Asset binaries, multi-section composed HTML, raw rendered artifacts: yes. Prose at 1-3K tokens, structured YAML, decisions.md entries: no. The threshold is "would carrying this output break the Reviewer's reasoning window in a way that degrades subsequent judgment quality."

3. **Latency test** — is the typical execution long enough that synchronously blocking the Reviewer's loop degrades operator experience? Asset rendering at 10-60s: yes. Prose composition at 5-10s: no. The threshold is the operator-perceptible "the system feels stuck" point — empirically around 15-20s of unbroken silence on a Reviewer wake.

**A role must pass all three.** Passing one or two is not enough. Vibe arguments (voice, style, brand-fit) are *prompt-level* concerns and do not satisfy any test.

This test is the bar. It does not change without an explicit FOUNDATIONS-level amendment.

---

## 8. Implementation phasing summary

| Phase | Scope | Commit | Validation |
|---|---|---|---|
| Phase 1 (this ADR) | BE: VALID_SPECIALIST_ROLES narrow + PRODUCTION_ROLES shrink + bundle migration + doc cascade | Single atomic commit | Regression gates + alpha-trader scheduler tick post-deploy |
| Phase 2 (separate ADR commit) | FE: cockpit roster card + detail surface removal, chat bubble shape collapse, operator-legibility surface | Single atomic commit, scheduled after Phase 1 bakes ~24h | Manual smoke + regression gates extended |

This ADR's commit is Phase 1. Phase 2 is referenced here for completeness but lands as its own commit on its own day, with a separate ADR follow-on if scope surfaces meaningfully new structure. If Phase 2 is purely FE wiring without new decisions, it lands as a commit referencing this ADR.

---

## 9. Discourse log

This ADR concludes a multi-turn architectural discourse session (2026-05-14) that resolved ADR-271 Threads B + C jointly. The discourse arc:

1. Live invocation audit confirmed only two LLM paths (scheduler + chat), both into the Reviewer.
2. System Agent surface audit revealed: cockpit peer-entity rendering of an LLM-less label.
3. Specialist survival test articulated against the operator's raised bar.
4. Designer survives all three structural tests; writer fails the tool-surface test; researcher / analyst / tracker / reporting all fail multiple tests.
5. Claude Code analogy (single LLM + tool results, no separate participant for "the system") accepted as the destination.
6. ADR-251 reversal accepted as honest because the audit revealed its premise (System Agent as peer entity) was not substrate-backed.
7. ADR-247 reversal (three-party → two-voice + ambient) accepted as the natural consequence.
8. Imperative collapse (Thread B) folds into D5 here — bundle recurrences absorb their specialist work; falsify-signals dissolves into morning-reflection's prompt; no separate Thread B ADR needed.
9. FE phasing sequenced after BE bakes per operator decision (cleaner audit boundary).

The discourse log in ADR-271 §6 documented the earlier turns; this ADR §9 closes the arc.

---

**End of ADR-272 draft. Phase 1 BE implementation follows in the same commit.**
