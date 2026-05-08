# ADR-258: Reviewer as Personified Chat-Mode Operator — Curated Primitive Scope, Attribution-Anchored Safety, Per-Action Narration

> **⚠ Amended by [ADR-261](ADR-261-recurrences-as-prompts.md) (2026-05-08).** `REVIEWER_PRIMITIVES` curated subset is preserved as the authority for what the Reviewer can call. Three updates: (1) `Schedule` (renamed from `ManageRecurrence`) is **added** to `REVIEWER_PRIMITIVES` — recurrences are now Reviewer-self-scheduled future wake-ups, not operator-authorship territory. (2) `DispatchSpecialist` (new) is added — Reviewer-only primitive for invoking focused-prompt specialist sub-LLM-calls. (3) `Compose` (new — also a structural-trigger default per ADR-262 D4) is added. The operator-authorship-boundary framing of ADR-258 D9 is preserved for substrate files (MANDATE, IDENTITY, principles, AUTONOMY, BRAND, CONVENTIONS, PRECEDENT, _operator_profile, _risk) — `DEFAULT_REVIEWER_WRITE_LOCKS` continues to apply.

> **⚠ Vocabulary update (2026-05-08, [ADR-259](ADR-259-feed-surface.md))**: "Chat-Mode Operator" in the title and references to "chat surface" / "the chat" below are preserved as period vocabulary. The operator-facing surface is now "the Feed." The `chat` permission mode survives as runtime characteristic per ADR-259 D2 — that's why "chat-mode" appears in the title; it describes the runtime, not the surface. Architectural decisions (curated primitives, lock policy, per-action narration, persona-bearing autonomous-operator framing) are unchanged.

**Status**: Implemented 2026-05-08 (revised same day after first deploy — see Revision below)

---

## Revision (2026-05-08, post-deploy refinement)

The first version of D1 gave the Reviewer the full `CHAT_PRIMITIVES` set (26 tools). That was over-broad — it conflated the Reviewer (operator personified, judgment seat) with YARNNN-the-orchestration-surface (executor of operator intent).

The right structural split, by physical-world analogy: the operator (human OR personified) does not directly call operator-authorship primitives that shape the operation (creating recurrences, restructuring domains, re-inferring identity). A human Simons-style supervisor reads reports, writes their own notebook, directs subordinates to fire procedures or submit proposals, asks the operator when in doubt — but doesn't restructure the operation themselves.

**Three changes locked in:**

1. **Curated `REVIEWER_PRIMITIVES` registry** (16 tools, subset of `CHAT_PRIMITIVES`). All read primitives + `WriteFile` (lock-gated) + `FireInvocation` + `ProposeAction` + `Clarify` + `ReturnVerdict`. Excludes operator-authorship primitives (`InferContext`, `InferWorkspace`, `ManageDomains`, `ManageAgent`, `ManageRecurrence`, `RuntimeDispatch`, `RepurposeOutput`, `EditEntity`, `ExecuteProposal`, `RejectProposal`).

2. **`DEFAULT_REVIEWER_WRITE_LOCKS` constant** (in `services/workspace_paths.py`). Encodes the operator-authorship boundary as a default lock set for Reviewer writes: MANDATE, AUTONOMY (md + yaml), IDENTITY, BRAND, CONVENTIONS, PRECEDENT, `_operator_profile.md`, `_risk.md`. Operator can extend via `_locks.yaml::locked_paths` or override defaults via `_locks.yaml::unlocked_paths`. The lock check `_is_path_locked_for_reviewer` reads defaults + adds + subtracts unlocks. Reviewer attempting a locked write gets a clear error suggesting Clarify or substrate-note instead.

3. **Per-action System Agent narration during the loop, not post-hoc lump.** The chat reads as a conversation between two participants: Reviewer narrates intent in first-person persona voice; System Agent narrates each consequential successful action when it fires. New shared helper `services/reviewer_chat_surfacing.py::narrate_reviewer_action` + `surface_reviewer_actions`. Wired into all four trigger paths (addressed via in-event handler in `chat.py`; heartbeat/proposal/reflection via `surface_reviewer_actions` post-invocation).

The *spirit* of the original ADR-258 is preserved: Reviewer is a chat-mode autonomous operator, attribution + revision-chain + AUTONOMY gating are the safety story (not access control), `_locks.yaml` is operator-authored access policy. What changed is the *scope* of primitives (curated subset, not full chat) and the *narrative shape* (per-action conversation, not post-hoc lump).

---

**Status (original)**: Implemented 2026-05-08
**Supersedes**: Portions of ADR-247 D4 (the "Reviewer has no primitives" / "no LLM tool surface" framing — both are now retired). Folds in ADR-253 D2 (directives become tool calls during a defer turn — same shape, no parallel mechanism). Amends ADR-256 (preserves trigger taxonomy + unified entry point; replaces hand-rolled tool dispatch with canonical registry calls; replaces curated tool subset with full chat-mode scope).
**Preserves**: ADR-209 (Authored Substrate — attribution + revision chain are load-bearing here), ADR-194 v2 (Reviewer seat + occupant model), ADR-229 D1 (judgment-first ordering), ADR-248 (periodic pulse, AUTONOMY pause writes), ADR-253 D1 + D3 + D5 (execution authority, lifecycle posture, heartbeat triggers), ADR-256 D1 (unified entry point + four trigger shapes).

---

## Problem

Across ADRs 247, 253, and 256 we accumulated three different framings of the Reviewer's primitive surface. Each was a partial answer; together they were inconsistent.

**ADR-247 D4** said the Reviewer has no LLM tool surface — pure judgment, just `return_review_decision`. The independence claim was that absence of primitives prevents capture by producers.

**ADR-253 D2** corrected the execution-authority confusion (the Reviewer's verdict already binds via the dispatcher) and introduced **directives** as a structured output channel: the Reviewer's verdict can include `fire_invocation | write_file | clarify` directives that the dispatcher executes through canonical primitive handlers. This kept the LLM tool-surface narrow while giving the Reviewer real action authority — but only on the proposal trigger.

**ADR-256** unified the four invocation shapes (proposal/heartbeat/reflection/addressed) into one `invoke_reviewer()` function with a tool-use loop — but the implementation rebuilt a parallel set of five tools (`ReadFile`, `FireInvocation`, `ProposeAction`, `WriteFile`, `ReturnVerdict`) inside `reviewer_agent.py` with hand-rolled dispatch in `_dispatch_tool_call()`. The Reviewer didn't call the canonical primitive registry; it had its own.

The production trace from 2026-05-08 (alpha-trader-2 addressed turn) made the consequences visible: the Reviewer guessed `_operator_profile.md` lived at `/workspace/context/trading/signals/_operator_profile.md` — the canonical `ReadFile` handler would have rejected that path, but the parallel handler accepted the call and returned "not found." Three rounds wasted on path-guessing, no `ReturnVerdict` ever called, "Reviewer returned no response" surfaced to the operator.

The deeper problem: the architecture is built around **attribution + revision chain + AUTONOMY gating** as the safety story (ADR-209 + AUTONOMY.md). Every prior framing of the Reviewer was reaching for **access control as the safety story** — narrow primitives, scope ceilings, parallel handlers. Access control duplicates work the substrate already does; it also misframes the Reviewer's role.

The Reviewer is not a verdict-rendering function. It is **the operator's installed judgment character with full delegated authority within AUTONOMY ceiling**. Like the operator themselves, it can read substrate, write substrate, commission work, propose actions, and ask questions. Independence means *judgment evaluated against money-truth, not against producer agreement* (ADR-253's correction to THESIS Commitment 2). It does not require absence of primitives.

---

## Decision

### D1 — Reviewer is a `chat`-mode caller of the canonical primitive registry

The Reviewer uses `chat` permission mode. Same `CHAT_PRIMITIVES` registry as YARNNN. Same `execute_primitive()` dispatch path. Same handlers, same path normalization, same attribution flow.

There is **no `reviewer` permission mode**, **no curated `REVIEWER_PRIMITIVES` list**, and **no parallel tool-dispatch table** in `reviewer_agent.py`. Singular implementation: one registry, one handler set, one dispatch path.

The Reviewer's tool surface is exactly `CHAT_PRIMITIVES`, which today includes (26 tools): `LookupEntity`, `ListEntities`, `SearchEntities`, `EditEntity`, `GetSystemState`, `ReadFile`, `WriteFile`, `SearchFiles`, `ListFiles`, `WebSearch`, `list_integrations`, `InferContext`, `InferWorkspace`, `ManageDomains`, `ManageAgent`, `ManageRecurrence`, `FireInvocation`, `RepurposeOutput`, `RuntimeDispatch`, `ProposeAction`, `ExecuteProposal`, `RejectProposal`, `Clarify`, `ListRevisions`, `ReadRevision`, `DiffRevisions`. Plus `ReturnVerdict` (Reviewer-specific, see D4).

### D2 — Safety story = attribution + revision chain + AUTONOMY gating

Three load-bearing mechanisms, all already shipped:

1. **Attribution** (ADR-209). Every workspace mutation carries `authored_by="reviewer:{occupant}"` in the revision chain. Operator can see what the Reviewer did, when, and why (revision message). Inspectable in the Files page revision history panel.
2. **Revision chain** (ADR-209). Every prior state is retained. The operator can revert any Reviewer-authored revision through the same `WriteFile` primitive. Nothing the Reviewer writes is destructive.
3. **AUTONOMY gating** (ADR-217 + ADR-229 D1 + ADR-248). Capital-bearing actions flow through `should_auto_execute_verdict()` which checks `paused_until`, AUTONOMY level, ceiling, and Reviewer's own `auto_approve_below_cents`. Both AUTONOMY (operator's ceiling) and principles (Reviewer's discipline) must permit.

These three together replace the access-control mechanisms prior framings reached for. **The Reviewer can write anywhere; the operator sees everything; AUTONOMY governs what auto-fires; revision chain makes every act reversible.**

### D3 — Operator-authored access policy via `_locks.yaml` (optional, default-empty)

The operator may declare path-level write locks in `/workspace/_shared/_locks.yaml`. When the Reviewer calls `WriteFile`, the handler reads `_locks.yaml` (cheap; cached per request) and rejects writes targeting locked paths with the error message `"this path is operator-locked; propose changes via Clarify or ProposeAction instead"`.

```yaml
# /workspace/_shared/_locks.yaml — optional operator-authored access policy
locked_paths:
  - context/_shared/MANDATE.md
  - context/_shared/AUTONOMY.md
  - context/_shared/IDENTITY.md
```

**Default is no `_locks.yaml`, no locks, full Reviewer write access.** This is opt-in — operators who want a tight ship lock specific files; operators who want a fluid Reviewer leave the file absent. The platform does not decide. The operator decides their own access policy by editing a file. This file is itself authored substrate; locking can be revised, attributed, reverted like anything else.

The frontend Files page surfaces a small lock-toggle icon next to each operator-authored file — clicking toggles the entry in `_locks.yaml`. Same canonical write path; no special API.

`_locks.yaml` applies only to Reviewer writes (`authored_by` starts with `reviewer:`). Operator writes are never blocked by it. Other agents' writes are out of scope for this ADR — handled by their existing scope conventions.

### D4 — Tool-use loop: 8 rounds, calls `execute_primitive()` from canonical registry

`invoke_reviewer()` runs a bounded tool-use loop with up to **8 rounds** (raised from the 3-round bound in ADR-256's first implementation — full primitive scope needs more rounds for legitimate exploration: discover → read → read-revisions → act → close).

Each round:
1. Send messages + system prompt + full `CHAT_PRIMITIVES` set + `ReturnVerdict` tool to the model
2. Round 0: `tool_choice={"type": "any"}` to force entry into the loop
3. Subsequent rounds: `tool_choice={"type": "auto"}`
4. For each tool call: dispatch through `execute_primitive()` from `services.primitives.registry` — exact same path YARNNN uses
5. If the call is `ReturnVerdict`, capture the verdict and exit
6. If the round produces text-only output (no tool calls), fall back to `stand_down` constructed from the text

`ReturnVerdict` is a Reviewer-specific tool not in `CHAT_PRIMITIVES`. It is added to the tool list at invocation time alongside the canonical chat primitives. Its schema accepts `verdict | reasoning | confidence | proposals (reflection only) | evidence_summary (reflection only)`. The model is instructed (in the system prompt) to call it last to close the loop.

Cost: Sonnet at 8 rounds × ~2K tokens worst case ≈ $0.10/invocation. Haiku at 8 rounds × ~2K ≈ $0.01/invocation. Median is much lower (typical: 2–4 rounds).

### D5 — Cockpit-awareness section is generated, not authored

The Reviewer's system prompt has three structural sections:
1. **Persona frame** (stable prose) — operating posture, missing-substrate handling, voice discipline
2. **Cockpit awareness** (generated) — composed at module import time from `services.workspace_paths` constants and the `CHAT_PRIMITIVES` registry. New file: `api/agents/cockpit_awareness.py` exporting `build_cockpit_section()`.
3. **Trigger framing** (stable prose) — what's pre-loaded for this trigger, what the Reviewer should do

Generated cockpit awareness eliminates drift: when a primitive is renamed, a path constant changes, or a tool description is updated, the Reviewer's system prompt regenerates automatically on next deploy. Developer doesn't have to remember to update prompt text.

Composition reads from canonical sources only. If a path constant moves, the prompt moves with it. If a primitive is added to `CHAT_PRIMITIVES`, the Reviewer learns about it on next deploy. **Drift-resistant by construction.**

### D6 — Lifecycle archive AUTONOMY gating (extended `should_auto_execute_verdict`)

Today's `should_auto_execute_verdict()` is capital-action focused (proposal execution). Lifecycle archive operations (`ManageRecurrence(action="archive")`, `ManageAgent(action="archive")`) on operator-created entities should also flow through an AUTONOMY gate.

This gate applies to **all chat-mode callers** (not Reviewer-specific). YARNNN-orchestration archiving an operator-created recurrence flows through the same gate. Same principle, same code path, no Reviewer-special-casing.

Default policy: archive of operator-created entities requires AUTONOMY ≥ `bounded_autonomous`. Below that, the action becomes a `defer + clarify` rather than executing. Implementation detail: archive handlers consult `should_auto_execute_lifecycle_action()` (new function in `review_policy.py`); if not permitted, return an error the caller surfaces as a Clarify.

This is recorded as a follow-on commitment, not implemented in the same commit as the rest of ADR-258 (it's a small extension scope).

### D7 — Single output type: `ReviewerOutput` (preserved from ADR-256 D5)

```python
class ReviewerOutput(TypedDict, total=False):
    verdict: str          # approve|reject|defer|no_change|narrow|relax|character_note|pause_autonomy|stand_down
    reasoning: str        # persona-voice explanation, written to decisions.md verbatim
    confidence: str       # low | medium | high
    actions_taken: list   # tool calls made during the loop (audit trail derived from execute_primitive returns)
    proposals: list       # reflection trigger only — framework change proposals
    evidence_summary: str # reflection trigger only — substrate citations
```

Callers route on `verdict`. `actions_taken` is a flattened audit log of the canonical primitives the Reviewer called during its loop, with their results. This replaces ADR-253 D2's separate `directives[]` field — the Reviewer's tool calls during a defer turn ARE its directives. Same shape, no parallel mechanism. ADR-253 D2 is folded in.

### D8 — Trigger taxonomy preserved

Four triggers from ADR-256 D1 unchanged: `proposal | heartbeat | reflection | addressed`. They differ only in what gets pre-loaded into the user message:

- `proposal` — proposal_row + governance + domain substrate
- `heartbeat` — trigger_slug + signal_files + governance + domain substrate
- `reflection` — recent_decisions + performance_summary + governance
- `addressed` — user_message + conversation_window + workspace_state + governance + domain substrate

Same entity, same tool surface, same loop, different opening context. The four triggers represent FOUNDATIONS Axiom 4's trigger sub-shapes; the entity is one (Axiom 2 Identity).

### D9 — `WriteFile` handler gains lock-aware enforcement when caller is Reviewer

The `handle_write_file` handler (in `services.primitives.workspace`) checks `auth.reviewer_caller` flag. When `True`:
1. Read `/workspace/_shared/_locks.yaml` (cached per request via auth-scoped memo)
2. Parse `locked_paths` list
3. If target path matches any locked entry, return `{"success": False, "error": "operator_locked", "message": "..."}`
4. Otherwise proceed with normal write

The flag is set by `invoke_reviewer()` when constructing the auth context for primitive dispatch. No global state. No new permission mode. Just a single field on the auth namespace that the handler consults.

---

## Implementation Plan (this commit)

1. **`api/agents/cockpit_awareness.py`** (new, ~120 lines): `build_cockpit_section(allowed_tool_names)` composes from `CHAT_PRIMITIVES` and `workspace_paths` constants. Pure function, no I/O.

2. **`api/agents/reviewer_agent.py`** (rewrite): Delete `_TOOLS` array (~150 lines), delete `_dispatch_tool_call()` (~120 lines). New flow:
   - `_SYSTEM_PROMPT` becomes `_PERSONA_FRAME` + `build_cockpit_section()` + `_TRIGGER_FRAMING`
   - `invoke_reviewer()` builds auth context with `reviewer_caller=True`
   - Tool list = `CHAT_PRIMITIVES + [RETURN_VERDICT_TOOL]`
   - Loop calls `execute_primitive(auth, name, input)` from canonical registry
   - 8 rounds max
   - Tool call response collation: capture results, accumulate into `actions_taken`, exit on `ReturnVerdict`

3. **`api/services/primitives/workspace.py`** (`handle_write_file`): Check `auth.reviewer_caller` flag; if True, read `/workspace/_shared/_locks.yaml`, parse, enforce.

4. **`api/services/primitives/registry.py`**: Add `reviewer_caller: bool = False` field to whatever auth shape the handlers expect (typically a SimpleNamespace).

5. **`docs/architecture/primitives-matrix.md`**: Rewrite Reviewer row in three-party ownership table — "chat-mode caller, full `CHAT_PRIMITIVES` set, `_locks.yaml` enforces operator-authored access policy, attribution mandatory."

6. **`docs/adr/ADR-247-three-party-narrative-model.md`**: Add superseded note on D4 paragraph linking to ADR-258.

7. **`docs/adr/ADR-253-reviewer-substrate-native-agent.md`**: Add note on D2 — directive output mechanism is now expressed as the Reviewer's tool calls during a defer turn (canonical primitives, not parallel structured field). D1, D3, D5 preserved.

8. **`api/prompts/CHANGELOG.md`**: Entry for unified prompt with generated cockpit awareness.

9. **`CLAUDE.md`**: ADR-258 entry in the ADR list.

Net diff: ~270 lines deleted from `reviewer_agent.py`, ~120 lines added (`cockpit_awareness.py`), ~30 lines added across `workspace.py` (lock enforcement) + docs. Net negative.

---

## What this ADR closes

**Behavioral fix**: the alpha-trader-2 addressed-turn failure ("Reviewer returned no response") was the production symptom of the parallel-dispatch architecture. With canonical primitives, path normalization works correctly; with full primitive scope, the Reviewer can `ListFiles` to discover instead of guessing; with revision-aware reads, the Reviewer can see substrate history. The class of "wrong path" bugs disappears.

**Architectural simplification**: one primitive registry, one dispatch path, one safety story (attribution + revision + AUTONOMY). Three previous framings collapse into one canonical answer. ~270 lines of parallel implementation deleted.

**Cold-start dissolution**: with full primitive scope and filesystem-native meta-awareness, the Reviewer handles missing substrate the same way Claude Code handles missing CLAUDE.md — read the substrate, see what's there, act accordingly. No "first run" state machine, no onboarding gate, no lifecycle column. The substrate is the lifecycle.

**Drift resistance**: cockpit awareness composed from canonical sources at module load time. Path constants change → prompt regenerates. Primitive added → Reviewer learns about it on next deploy. Developer cannot accidentally stale-inline a path or tool name.

---

## What this ADR does not close (follow-ons)

- **D6 lifecycle AUTONOMY gating** — extension of `should_auto_execute_verdict()` for archive actions. Small follow-on commit.
- **Frontend Files page lock-toggle UI** — small affordance to write `_locks.yaml`. UI work, follow-on.
- **`_locks.yaml` schema validation** — the file is operator-authored markdown-adjacent YAML; if malformed, the handler treats it as no locks (fail-open since the safety story is attribution-anchored, not lock-anchored). Could add a frontend validator later.

---

## Decision log (this thread, condensed)

The architecture round-tripped through several framings before landing here:

1. **ADR-247 D4** (April 2026) — "Reviewer has no primitives" — load-bearing on absence
2. **ADR-253** (May 2026) — corrected: Reviewer has no LLM tool surface but binds execution; introduced `directives` for substrate work on defer
3. **ADR-256** (May 8, 2026) — unified four functions into `invoke_reviewer()` with curated 5-tool parallel set; production failed
4. **ADR-258** (May 8, 2026) — Reviewer is a chat-mode caller of the canonical registry; full primitive scope; attribution + revision + AUTONOMY is the safety story; operator-authored `_locks.yaml` for opt-in carveouts; cockpit awareness generated from canonical sources

The throughline: the architecture has always been built around attribution + reversibility (ADR-209). Each prior framing reached for access-control mechanisms that duplicated what the substrate already does. ADR-258 lets the substrate do its job.
