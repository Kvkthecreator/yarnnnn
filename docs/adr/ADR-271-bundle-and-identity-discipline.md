# ADR-271: Bundle Authoring Discipline + Identity-Layer Audit

**Status**: **Resolved 2026-05-14.** Threads A + D Implemented in commits `2430622` + `54eadf6` respectively. Threads B + C jointly resolved by [ADR-272](ADR-272-identity-collapse-system-agent-and-specialist.md) Phase 1 BE (same day). FE collapse work sequenced as ADR-272 Phase 2 follow-on.
**Author**: KVK + Claude (discourse session 2026-05-14)
**Companion observation**: [2026-05-13-activation-fire-wiring.md](../alpha/observations/2026-05-13-activation-fire-wiring.md) (cold-start audit that surfaced the symptoms this ADR diagnoses)

**Amends (pending discourse outcome)**:
- ADR-251 — System Agent + Reviewer as First-Class Surfaces — whether System Agent survives as a cockpit entity is open.
- ADR-261 D7 — Specialists as tools — whether DispatchSpecialist survives, narrows, or collapses is open.
- ADR-263 — Recurrence mode (mechanical vs judgment) — bundle-side migration pass.
- ADR-270 — Fire-on-activation recurrences — `falsify-signals` recurrence may be deleted (intent collapses into morning-reflection).
- ADR-247 D4 — Primitive ownership table — Class A / Class B annotation revisited if System Agent dissolves.

**Preserves**:
- FOUNDATIONS Axioms 0–9 (no axiom-level changes).
- ADR-194 v2 Reviewer substrate.
- ADR-195 v2 money-truth substrate.
- ADR-209 Authored Substrate.
- ADR-264 SyncPlatformState primitive + mechanical-mode dispatch path.
- The four-tab cockpit (`Feed | Work | Agents | Files`) per ADR-214.

**Dimensional classification**: **Mechanism** (Axiom 5) primary — collapses unprincipled judgment-mode work into mechanical primitives; **Identity** (Axiom 2) secondary — audits whether System Agent and Specialist warrant being separate identity-layer entities; **Channel** (Axiom 6) tertiary — bundle-authoring discipline affects which entities surface on `/agents`.

---

## 1. Why this ADR

The cold-start audit on 2026-05-13 surfaced three drift patterns that share a single architectural root cause. They survive every conceptual framing we considered (Claude-Code metaphor, Reviewer-imperative-flow, three-party narrative model) — they're worth fixing regardless of which framing wins. The drift patterns:

1. **Mechanical work expressed as judgment.** Bundled recurrences `track-universe`, `track-regime`, and `falsify-signals` are declared `mode: judgment` despite their work being deterministic (fetch platform data → transform → write substrate). Each fire costs ~$0.30–$0.80 in LLM tokens for work that should cost $0. This violates ADR-263 §"Why this rewrite" — which named `track-universe` as the canonical mismatch case — even though ADR-263 was authored explicitly to solve this class of drift.

2. **Imperative flow encoded as separate recurrences instead of inline Reviewer composition.** The alpha-trader bundle ships ~16 recurrences pre-declaring each step of the trading day's flow (pre-market brief → signal evaluation → track positions → outcome reconciliation, plus bootstrap recurrences like `falsify-signals`). Most of these are imperative steps the Reviewer could compose inline from a smaller set of wake-points, given the Reviewer already has `Schedule`, `FireInvocation`, and `DispatchSpecialist` in its tool surface (ADR-261 D4 + D7). The bundle encodes structure where it should encode prompts. This violates ADR-261's load-bearing principle (*"framework prescribes minimally, operator/bundle authors prompts that encode intent"*).

3. **Specialists and System Agent surface as identity-layer entities but lack standing identity at the LLM-execution layer.** ADR-251 reinstated System Agent as a first-class cockpit entity with its own roster card, Identity tab, Mandate tab, and Back Office tab. But mechanically, the System Agent shares the chat-mode LLM identity (`yarnnn.py`) — there's no `SystemAgent` class, no separate system prompt, no separate identity file. The "System Agent runs back-office work" framing in the FE is misleading: every `mode: judgment` recurrence in the back-office set (`morning-reflection`, `morning-calibration`, `proposal-cleanup`, `narrative-digest`, `outcome-reconciliation`) wakes the **Reviewer**, not a System Agent LLM. The Reviewer narrates *as* System Agent at the surface layer (`role='system_agent'` chat bubbles). Similarly, specialists have role-keyed style files (`/workspace/style/{role}.md` per ADR-117) but no IDENTITY.md, no standing intent, no persistent persona.

Each drift pattern is locally explainable. Together, they form a coherent gap: **the bundle authors and the cockpit FE encode identity/structure beyond what the LLM-execution layer actually instantiates.** This makes the system harder to reason about, more expensive to run, and brittle in specific ways the cold-start audit exposed (specialist briefs lose write directives; pre-declared recurrences fail to compose into the user's actual intent; back-office work is more expensive than it needs to be).

---

## 2. Decision (proposed, open for discourse)

This ADR commits to three threads. Threads A and B are mechanical refactors that enact what canon already says — they survive every framing we considered. Thread C is an identity-layer question genuinely open for discourse.

### Thread A (Implemented 2026-05-14) — Mechanical migration of deterministic recurrences

**Implementation summary (2026-05-14)**:

Two new dispatcher-only mechanical primitives shipped:
- `TrackUniverse` (`api/services/primitives/track_universe.py`): fetches Alpaca 1Day bars per ticker in `_universe.yaml`, computes SMA/RSI/ATR/volume indicators in pure Python, writes one `{TICKER}.yaml` per ticker. Zero LLM cost.
- `TrackRegime` (`api/services/primitives/track_regime.py`): fetches VIXY + SPY 1Day bars, computes VIX-regime-active predicate + trend regime, writes `_regime.yaml`. Reads operator-tunable thresholds from `regime-state.md` spec doc at runtime. Zero LLM cost.

Both primitives:
- Registered in `HANDLERS` only — NOT in CHAT_PRIMITIVES / HEADLESS_PRIMITIVES / REVIEWER_PRIMITIVES per ADR-264 D3 (mechanical primitives are dispatcher-only).
- Self-load credentials from `platform_connections.platform='trading'`. Return `error='capability_missing'` cleanly when no active connection.
- Write substrate via `write_revision(authored_by="system:track-universe" | "system:track-regime")` per ADR-209 attributed-substrate discipline.
- Recover code originally landed by ADR-253 + ADR-254 that was swept by ADR-261 Phase B. The deletion was wrong-shaped for these specific recurrences — ADR-263 §"Why this rewrite" explicitly named `track-universe` as the canonical mechanical-vs-judgment mismatch case.

Alpha-trader bundle migrated:
- `track-universe` recurrence: `mode: judgment` → `mode: mechanical`. Prompt collapsed from a ~30-line judgment brief to one line: `@primitive: TrackUniverse()`. Deleted: `required_capabilities: [read_trading]`, `max_rounds: 12`.
- `track-regime` recurrence: `mode: judgment` → `mode: mechanical`. Prompt collapsed from ~45 lines to `@primitive: TrackRegime()`. Deleted: `required_capabilities: [read_trading]`. Stale-fallback behavior preserved (the primitive's `_emit_stale_fallback` path).

Test gate updates:
- `test_adr269_capability_flow.py`: `track-universe` and `track-regime` moved from "judgment-mode with required_capabilities" expectations to "mechanical-mirror" class (alongside track-positions / track-account / track-orders). 111/111 assertions pass (was 108 — added 3 mechanical-mode invariants).
- `test_adr261_phaseB.py`: 62/62 pass (primitive surface invariants unchanged).

Cost & reliability impact (alpha-trader bundle):
- Eliminated up to 4 judgment-mode Reviewer wakes per RTH day (3× track-universe per RTH + 1× track-regime). At today's audit-measured ~$0.30-$0.80 per wake, ~$1.50-$5/day saved per active workspace.
- More importantly: eliminated the failure class where the specialist exited early without calling WriteFile. The substrate writes are now deterministic; no brief-composition discipline required.
- Cold-start activation: track-universe + track-regime now fire mechanically within 1-3 seconds of activation, producing per-ticker + regime substrate before the first signal-evaluation fire.

What this thread did NOT do (deliberate):
- No change to `falsify-signals` (it's the bootstrap research recurrence; Thread B will address whether it survives as a recurrence or collapses into morning-reflection's prompt).
- No new dispatcher-side capability gate for `TrackUniverse`/`TrackRegime` (they self-handle via credential load returning `capability_missing` — same pattern as `SyncPlatformState`-via-dispatcher would, just inside the primitive instead of in the dispatcher's `_required_platform_for_primitive` helper).
- No removal of `SyncPlatformState` (it remains the canonical pure-mirror primitive for simpler shapes — TrackUniverse/TrackRegime are the fetch-plus-compute cousins ADR-264 §"Reconciliation half" anticipated).

---

### Thread A (original proposal text, preserved for trace) — Mechanical migration of deterministic recurrences

Decisions:

- **A1**: `track-account`, `track-orders`, `track-positions` stay `mode: mechanical` (already correct).
- **A2**: `track-regime` migrates `mode: judgment` → `mode: mechanical`. Implementation: a new deterministic executor at `services/back_office/regime_tracker.py` (or similar; placement decided in implementation phase) that fetches VIXY + SPY 1-Day bars via the existing Alpaca client, computes the deterministic regime predicate (active/inactive based on SMA-20 threshold + scalar), and writes `/workspace/context/trading/_regime.yaml` with the same schema the LLM produces today. Zero LLM cost.
- **A3**: `track-universe` migrates `mode: judgment` → `mode: mechanical`. Needs the same shape — fetch per-ticker bars, compute SMA(20)/SMA(50)/RSI(14)/ATR(14)/volume-vs-30d, write `/workspace/context/trading/{ticker}.yaml`. Either reuse a single executor parameterized over universe members, or compose `SyncPlatformState` invocations with a deterministic transform stage between fetch and write.
- **A4**: This may warrant **one new mechanical primitive** beyond `SyncPlatformState`. ADR-264 §"Reconciliation half" reserved this gap explicitly. Working name: `SyncWithCompute` (or similar — final name picked in implementation). Shape: `(tool=platform_*, transform=<named deterministic fn>, write_to=<path template>, diff_aware=true)`. The `transform` function is registered in a small Python-side registry alongside the primitive — same registry pattern that `HANDLERS` uses today. If ADR-271 D-A4 is accepted, the primitive lands; if it isn't, the executors are bespoke Python in `back_office/`. The former is more extensible; the latter is less infrastructure.
- **A5**: Bundle PROMPT for each migrated recurrence becomes the `@primitive: ...` directive (matching the existing `track-account` shape). No more prose.

Cost impact: saves ~7 judgment-mode Reviewer wakes per day on the alpha-trader bundle (4× `track-universe` per RTH + 1× `track-regime` + 1× `outcome-reconciliation`-mirror-half + activation fires). At today's audit-measured cost (~$0.30–$0.80 per wake), roughly $2–$5/day saved per active alpha-trader workspace. More importantly: eliminates the failure class where the Reviewer or its dispatched specialist exits without writing substrate.

### Thread B (commit-ready) — Imperative collapse of bootstrap recurrences

Decisions:

- **B1**: Delete `falsify-signals` as a standalone recurrence. The 90-day historical falsification intent moves into `morning-reflection`'s prompt as a precondition the Reviewer checks: *"if `/workspace/research/findings/` is empty and `_performance.md` has no live outcomes yet, the Reviewer fetches bars and writes findings before reasoning about today's posture."* The Reviewer composes the flow inline using `DispatchSpecialist(role="researcher", brief=...)` (if Thread C keeps specialists) OR by calling platform tools and WriteFile directly (if Thread C collapses specialists).
- **B2**: Audit every alpha-trader recurrence whose prompt body is essentially *"dispatch a specialist to do X."* If any other recurrences match this shape (e.g., pre-market-brief composing a deliverable), collapse them into adjacent judgment wake-points the same way. Concrete audit done in implementation phase, not pre-emptively here.
- **B3**: The remaining recurrence set after B1+B2 should be roughly:
  - **Mechanical wake-points** (zero LLM): `track-account`, `track-orders`, `track-positions`, `track-universe`, `track-regime`, mirror-half of `outcome-reconciliation` — all `mode: mechanical`.
  - **Judgment wake-points** (Reviewer wake): `morning-reflection`, `morning-calibration`, `signal-evaluation`, `pre-market-brief`, `proposal-cleanup`, `narrative-digest`, `weekly-performance-review`, `quarterly-signal-audit` — all `mode: judgment`. The Reviewer composes whatever sub-flow is warranted inside each wake-point's loop.
  - **No "wake to dispatch one specialist" recurrences**. Imperative sub-steps live inside judgment wake-points' prompts.

Cost impact: removes 1+ activation-fire judgment wakes; more importantly, eliminates the brief-composition failure class where the Reviewer composes a specialist brief that drops the operator's WriteFile directive.

### Thread D (Implemented 2026-05-14) — Dead-headless-path sweep

Surfaced during the live-path audit subsequent to threads A/B/C drafting: the pre-ADR-261 task pipeline scaffolding (Slack-event webhook → trigger_dispatch → event_triggers → execute_agent_generation → generate_draft_inline) is wired in code but has **zero live invocations in production**. Specifically:

- `agent_runs` table: 0 rows total in this database (the headless task pipeline's output target).
- `event_trigger_log` table: 0 rows.
- `platform_connections` for Slack: zero across all alpha-trader workspaces. The only Slack-shaped connection in the entire database is one Notion connection on a non-alpha user.
- The headless task pipeline survives in code only because the deletion pass for ADR-141 + ADR-261 missed the Slack-event entry path.

Decision: delete the entire scaffold in one commit. **Singular implementation discipline** — the live paths are (1) scheduler → invocation_dispatcher → invoke_reviewer (recurrence fire) and (2) chat feed → execution_router OR invoke_reviewer (chat addressing); no third path.

Files deleted:

- `api/services/agent_execution.py` (~1450 LOC — generate_draft_inline, execute_agent_generation, _build_headless_system_prompt, helpers)
- `api/services/event_triggers.py` (~400 LOC — PlatformEvent, handle_slack_event, execute_event_triggers)
- `api/services/trigger_dispatch.py` (~100 LOC — dispatch_trigger)
- `api/test_adr049_freshness.py`, `api/test_adr118_d3_output_substrate.py`, `api/test_adr143_methodology_feedback.py`, `api/test_output_validation.py`, `api/test_structural_overhaul.py` (tests for the deleted code paths)

Files modified:

- `api/routes/webhooks.py` — Slack event handler (`process_slack_event`, `handle_slack_events`, `verify_slack_signature`) + their imports removed. `send_slack_notification` preserved (used by user-signup handler).
- `api/services/orchestration_prompts.py` — stale `_build_headless_system_prompt` reference comment updated.
- `CLAUDE.md` File Locations table — agent_execution.py entry replaced with deletion note.
- `docs/database/SCHEMA.md` — `agent_run` event_type writer column updated to reflect deletion.

Regression gates pass post-deletion:
- `api/test_adr261_phaseB.py` — 62/62 (Specialist + dispatch + Reviewer primitive surface)
- `api/test_adr269_capability_flow.py` — 108/108 (capability flow through DispatchSpecialist)

Note: `api/test_recent_commits.py` had a pre-existing `NameError` unrelated to this sweep (confirmed by `git stash` + retest).

The live-invocation surface after Thread D:

| Path | Entry point | LLM identity | Use today |
|---|---|---|---|
| 1. Recurrence fire (judgment) | scheduler → `invocation_dispatcher.dispatch` → `invoke_reviewer(trigger='reactive')` | Reviewer (Haiku) | All overnight activity |
| 2. Recurrence fire (mechanical) | scheduler → `invocation_dispatcher.dispatch` → `_dispatch_mechanical` → primitive handler | None (deterministic) | `track-account`, etc. |
| 3. Chat addressing | feed → `execution_router` (regex, no LLM) OR `invoke_reviewer(trigger='addressed')` | Reviewer (Haiku) when LLM needed | User-driven |
| 4. Specialist sub-call | from inside Reviewer's loop → `handle_dispatch_specialist` | Specialist (Sonnet, headless tool surface) | Inside Reviewer waves only |

No fifth path. Heuristic-shaped argument for Thread C reframing strengthened: with the headless task pipeline gone, "headless mode" is a runtime characteristic that exists in exactly one place (specialist sub-calls), and "System Agent" is a narrative label, not an executor.

---

### Thread C (open for discourse) — Identity-layer audit

The first two threads survive every framing. This thread is the genuinely open architectural question raised by your audit: **given that System Agent shares the chat LLM identity and Specialists have no standing identity, do they warrant being separate identity-layer entities at all?**

Three options on the table, each defensible:

#### Option C1 — Status quo preserved, with sharpened framing only

Keep System Agent as a cockpit entity (ADR-251 surface). Keep `DispatchSpecialist` and the six universal specialist roles (ADR-261 D7 + ADR-176). Sharpen the Reviewer's system prompt to:

- Default to doing production work inline (do not reach for DispatchSpecialist unless context-isolation, tool-surface scoping, or round-budget bounding is genuinely warranted)
- Treat specialists as escape-hatch tools (rare invocation, not default execution path)
- Be explicit that brief composition is part of the Reviewer's tool-call contract (per ADR-261 D7: brief carries everything the specialist needs)

Cockpit posture: System Agent surface stays. Specialist cards (if any) stay. Operating contracts in the FE stay accurate ("System Agent does X" framing remains, but the FE acknowledges that mechanically the Reviewer wakes for back-office judgment work).

Cost: 0 LOC delete, ~200 LOC Reviewer-prompt sharpening, no schema changes, no FE changes.

Honest trade-off: preserves architectural surface but the underlying LLM-identity reality stays at one chat + one Reviewer. The cockpit's depiction of System Agent as a peer entity becomes a *narrative convenience* — the operator sees three participants (themselves + Reviewer + System Agent) but two of those three share an LLM. This is acceptable if we're willing to commit to the framing.

#### Option C2 — System Agent dissolves; specialists narrow to genuine escape-hatch

Delete System Agent as a cockpit entity. The `/agents` page roster becomes one card (Reviewer) plus any user-authored domain agents. The DB row for `thinking_partner` is preserved (it's the chat-mode LLM substrate) but no longer surfaces as a roster peer.

Keep `DispatchSpecialist` but narrow `VALID_SPECIALIST_ROLES` to the cases where context-isolation or tool-surface scoping is genuinely load-bearing:

- `researcher` survives (large-context investigation work — web searches plus substrate writes can crowd judgment context)
- `designer` survives (asset rendering — separate tool surface entirely, RuntimeDispatch)
- `writer` survives only if distinct-voice prose composition is genuinely required (currently uncertain; alpha-trader doesn't exercise it)
- `analyst`, `tracker`, `reporting` — likely dissolve. Their work is what the Reviewer would do inline anyway.

Cockpit posture: Reviewer is the only systemic entity. Specialists don't have roster cards (consistent — they have no standing identity). The cockpit shows the Reviewer's recent activity, including specialist sub-calls within Reviewer waves.

Cost: ~1500 LOC delete across FE + canon docs (the System Agent FE surface is meaningful), ~300 LOC narrow `dispatch_specialist.py`, ADR-251 amended (System Agent surface deleted), ADR-247 D4 / D7 / D8 simplified.

Honest trade-off: more honest to the LLM-execution layer; ships less surface; closes the gap between cockpit framing and execution reality. Requires re-naming work in chat narration (`role='system_agent'` bubbles either rename to `role='reviewer'` for Reviewer-directed actions, or rename to a less-loaded label like `role='system'` for pure mechanical narration).

#### Option C3 — Maximal collapse: delete System Agent AND DispatchSpecialist

Delete System Agent as a cockpit entity (same as C2). Additionally, delete the `DispatchSpecialist` primitive entirely. Delete `VALID_SPECIALIST_ROLES`. The Reviewer becomes the only LLM identity for all judgment + production work. When production work is heavy (research, asset rendering), the Reviewer either:

- Calls platform tools + WriteFile + RuntimeDispatch directly within its own loop (longer loops, larger windows)
- Uses `Schedule` to author a separate fire-once judgment recurrence with a focused prompt, which spawns a fresh Reviewer context (effectively the same shape as "specialist sub-call" but using the Reviewer's identity in a clean window)

Cockpit posture: one entity (Reviewer). No specialist concept anywhere. Maximally Claude-Code-pure.

Cost: ~2500–3500 LOC delete across primitives + FE + canon docs (DispatchSpecialist's call chain, the role registry in `orchestration.py::PRODUCTION_ROLES`, the FE roster + ROLE_GUIDANCE_REGISTRY, ADR-176 amended, ADR-261 D7 superseded, ADR-251 amended).

Honest trade-off: maximum singularity (one LLM identity, one execution path). Genuinely loses context-budget-isolation as a structural property — heavy production work crowds judgment context until/unless we re-introduce sub-context mechanisms. Most aggressive; biggest cockpit surface loss; cleanest mental model.

#### Discourse questions Thread C must resolve

The discourse should not pick an option without first answering:

1. **Is context-budget-isolation a load-bearing property?** Specifically: when the Reviewer does the work `falsify-signals` does inline (5 tickers × 90 days × R-multiple computation), does the resulting context window meaningfully degrade judgment quality on the *same* Reviewer wave, or is the work bounded enough that the Reviewer's window absorbs it? If the latter, C3's risk is small. If the former, C2 is the floor.

2. **Is the System Agent surface earning its keep?** Operators see it on `/agents`. Does the cockpit-as-operation reading (ADR-228) justify a peer entity that doesn't have a separate LLM identity? Or is the System Agent surface an artifact of an earlier framing (ADR-251 was committed when the Reviewer was still being collapsed under YARNNN — context has shifted)?

3. **What about future systemic Agents?** ADR-216 + FOUNDATIONS Axiom 2 imagine future systemic Agents (Auditor, Advocate, etc.) as additional persona-bearing members. If those eventually land, do they live "under" System Agent or alongside Reviewer? If alongside, System Agent's "infrastructure peer" framing weakens further.

4. **Async / parallel work** — does any planned alpha-trader workflow need actual parallel execution (`asyncio.gather` over N concurrent specialist calls)? If yes, that's a separate primitive (not what DispatchSpecialist offers today, which is synchronous). If no, the C3 loss-of-async claim is moot.

---

## 3. What this ADR does NOT do

- **Does not commit to a Thread C option.** Threads A + B are ratifiable on their own; Thread C is the discourse object.
- **Does not change primitive registry shape until Thread C resolves.** No new primitives lifted/dropped yet beyond the potential `SyncWithCompute` in Thread A.
- **Does not touch FOUNDATIONS.md.** No axiom-level changes; this is bundle + identity-layer hygiene, not foundational reform.
- **Does not change schema.** No DB migrations required for Threads A + B. Thread C C2/C3 may delete the `thinking_partner` agent row's cockpit visibility but the row itself stays (the chat LLM identity uses it).
- **Does not address pricing/cost accounting.** The token_usage cache-discount finding from the audit is parked per session instruction (functionality first).

---

## 4. Implementation phasing (assuming all three threads adopted)

The phasing is sequential because Threads B and C depend on Thread A's mechanical migrations landing.

### Phase 1 — Thread A (mechanical migration)

1. Decide A4 (new primitive vs bespoke executors).
2. Implement deterministic executors for `track-universe` + `track-regime`.
3. Migrate the two recurrences in `_recurrences.yaml` to `mode: mechanical` with `@primitive: ...` prompts.
4. Verify on seulkim88 cold-start: confirm zero Reviewer wakes for mechanical recurrences, substrate writes land deterministically.
5. CHANGELOG entry. Test gate (extend `test_adr269_capability_flow.py` or a new regression suite asserting mechanical-mode-no-LLM invariant).

### Phase 2 — Thread B (imperative collapse)

1. Delete `falsify-signals` recurrence from bundle.
2. Extend `morning-reflection`'s prompt with the bootstrap-research precondition (operator-authored; bundle change only).
3. Audit remaining recurrences for "wake to dispatch one specialist" shapes; collapse any that match.
4. Verify on seulkim88: morning-reflection wakes, Reviewer detects empty findings, composes the falsification flow inline.

### Phase 3 — Thread C (identity-layer; only if discourse picks C2 or C3)

If **C1** picked: no Phase 3 implementation. Reviewer-prompt sharpening lands as a Phase 2 sub-commit.

If **C2** picked:
1. Delete System Agent roster card + detail surface from FE.
2. Update `role='system_agent'` writers — rename label or collapse to `role='reviewer'` for Reviewer-directed action narration.
3. Narrow `VALID_SPECIALIST_ROLES` to surviving roles.
4. Delete `PRODUCTION_ROLES` entries for dissolved specialists.
5. ADR-251 amended; ADR-176 amended; ADR-247 D4 simplified.

If **C3** picked:
1. All of C2 above, plus:
2. Delete `DispatchSpecialist` primitive entirely (`api/services/primitives/dispatch_specialist.py`, registry entries, all 3 primitive sets).
3. Delete `PRODUCTION_ROLES` registry.
4. Reviewer prompt + role guidance updated to reflect single-LLM-identity model.
5. ADR-261 D7 superseded; ADR-176 substantially amended; ADR-117 role-keyed style distillation reframed (style files become workspace-level rather than role-keyed).

---

## 5. Doc-radius impact

Threads A + B (mechanical refactor + imperative collapse):

- `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml` — primary change site
- `docs/programs/alpha-trader/reference-workspace/research/mandate.md` — possibly deleted with falsify-signals collapse
- `docs/programs/alpha-trader/reference-workspace/specs/falsify-signals.md` — possibly deleted
- `docs/programs/alpha-trader/reference-workspace/review/principles.md` — bootstrap-clause text revised to reflect inline-research path
- `docs/architecture/primitives-matrix.md` — `SyncWithCompute` (or equivalent) added if A4 adopts a new primitive
- `docs/architecture/SERVICE-MODEL.md` — execution-flow Frame updated to reflect mechanical-mode dominance in alpha-trader
- `docs/adr/ADR-263-recurrence-mode-mechanical-vs-judgment.md` — implementation status updated (alpha-trader bundle now compliant)
- `docs/adr/ADR-270-fire-on-activation-recurrences.md` — companion note that falsify-signals is deleted; activation-fire flag stays valid for the surviving mechanical recurrences
- `api/prompts/CHANGELOG.md` — entry for prompt-shape changes
- `api/test_adr271_*.py` — new regression test if/when this ADR lands
- `CLAUDE.md` — alpha-trader ADR summary block updated

Thread C (if adopted beyond C1):

- `docs/adr/ADR-251-system-agent-reviewer-first-class-surfaces.md` — amended or superseded
- `docs/adr/ADR-247-three-party-narrative-model.md` — three-party model reframes to two-party + system narration
- `docs/adr/ADR-261-recurrences-as-prompts.md` — D7 (specialists-as-tools) superseded if C3
- `docs/adr/ADR-176-work-first-agent-model.md` — universal specialist roster reframed
- `docs/architecture/LAYER-MAPPING.md` — entity taxonomy updated
- `docs/architecture/GLOSSARY.md` — System Agent + Specialist entries updated or removed
- `docs/architecture/FOUNDATIONS.md` — Axiom 2 (Identity) layer descriptions updated
- `web/lib/agent-identity.ts` + `web/components/agents/AgentContentView.tsx` — cockpit surface changes
- `web/app/(authenticated)/agents/page.tsx` — roster shape

---

## 6. Discourse log (this session)

This ADR was authored after a multi-turn audit session that:

1. Audited overnight execution against the carry doc's claims; falsified the carry doc's "track-universe doesn't write substrate" claim (it self-healed on periodic fire) but confirmed `falsify-signals` substrate-production failure.
2. Confirmed `record_token_usage` over-bills cached calls (parked for separate work).
3. Established that every overnight execution was `trigger=reactive, sub_shape=recurrence_fire` — no operator chat, no proposal arrivals, no orders placed.
4. Surfaced the mechanical-vs-judgment mismatch as the structural root cause of the falsify-signals failure (not brief composition, as the carry doc framed it).
5. Surfaced the broader pattern: alpha-trader bundle is anchored in a pre-ADR-261 worldview where recurrences pre-declare imperative steps instead of being wake-points for inline composition.
6. Audited System Agent and DispatchSpecialist in code: discovered System Agent shares the chat LLM identity (no separate LLM), and DispatchSpecialist is synchronous-blocking within the Reviewer's loop (no async benefit).
7. Caught and corrected my own framing error: ADR-251 reinstated System Agent as a cockpit entity (real FE surface), not just narration dressing. Operator-provided screenshot of `/agents?agent=system` was the corrective evidence.

The session converged on: Threads A + B are ratifiable now (singular-implementation discipline applies regardless of identity-layer outcome); Thread C is genuinely open and worth a focused discourse session before committing.

---

## 7. Open questions held over for discourse

1. Pick a Thread C option, or defer Thread C and ship A + B first.
2. If Thread C picks C2 or C3, what is the migration story for in-flight alpha-trader operator habits / muscle memory?
3. A4: new primitive vs bespoke executors for the deterministic transforms.
4. Should the audit also check kvk's workspace (the other alpha-trader persona) for the same bundle shape — and if it has diverged, which version is canonical?
5. Does morning-reflection's prompt-extension for the bootstrap-research case need its own ADR, or is it a bundle change documented under ADR-271?

---

**End of ADR-271 draft.** Open for discourse before any commit.
