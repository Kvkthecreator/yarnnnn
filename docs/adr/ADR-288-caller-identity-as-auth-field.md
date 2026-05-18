# ADR-288: Caller Identity as First-Class Auth Field + Vocabulary Closure Pass + Kernel Money-Truth De-instancing

## Status

Proposed (2026-05-18)

## Companion canon

- FOUNDATIONS Axiom 2 (Identity layer) — the caller-identity field operationalizes the canonical attribution taxonomy
- FOUNDATIONS Axiom 8 (Ground-Truth Substrate) — Phase 3 enforces the kernel/instance vocabulary discipline declared by ADR-282 at every kernel-prompt surface
- ADR-209 (Authored Substrate) — `authored_by` taxonomy: `operator | yarnnn:<model> | agent:<slug> | specialist:<role> | reviewer:<identity> | system:<actor>`
- ADR-251 (System Agent + Reviewer as first-class surfaces) — historical `authored_by` revision rows immutable; this ADR changes the default for *new* writes only
- ADR-267 (P&L unification — money-truth substrate) — renamed `_performance.md` → `_money_truth.md` everywhere it ships substrate; Phase 2 finishes the internal field-name + helper + docstring residue
- ADR-280 (Substrate ABI + workspace guide) — bundle's `_workspace_guide.md` is the authoritative carrier of program-specific substrate paths; kernel prompts MUST defer to it rather than hardcoding instance paths
- ADR-282 (Axiom 8 kernel/instance vocabulary discipline) — Phase 3 enforces the discipline rule at kernel-prompt surfaces that ADR-282 named but did not enforce
- ADR-283 (alpha-author bundle) — concrete non-monetary program whose Reviewer was being shipped alpha-trader's money-truth vocabulary as if it were kernel
- Sibling discipline arc: ADR-274 (Schedule fail-fast on missing `authored_by`) + ADR-276 (canonical governance-envelope helper) + ADR-286 (single-writer per substrate path)

## Context

### The pattern being closed

ADR-274, ADR-276, and ADR-286 each closed a different shape of the same anti-pattern: a runtime concern that had leaked across N compensating sites collapsed to a single canonical declaration at the boundary.

| ADR | Concern | Before | After |
|---|---|---|---|
| ADR-274 | Trigger-authoring attribution on Schedule | Schedule accepted missing `authored_by`; callers may or may not pass it | Fail-fast contract + dispatch-layer injection at known caller boundaries |
| ADR-276 | Reactive-trigger governance envelope | Inline 9-path gather in `routes/feed.py`; reactive trigger had no envelope at all | Single canonical helper `load_reviewer_governance_envelope()` called by both addressed + reactive paths |
| ADR-286 | Substrate writes for kernel-default paths | 10 paths dual-written + 4 rescue patches in `is_skeleton_content` + 1 bundle_owned_paths skip block | Single writer per path; kernel-default rescue patches deleted |

This ADR finishes the symmetric arc for the substrate-write *authorship* concern.

### What Sunday's wake exposed

The 2026-05-17 18:01 UTC `weekly-performance-review` fire produced a structurally-excellent `standing_intent.md` (ADR-284 Phase 2 contract honored). But the revision row was attributed `authored_by="yarnnn:chat"` instead of `reviewer:ai:reviewer-sonnet-v8` as ADR-284 D2 expected. Audit trail says "YARNNN chat surface wrote this file." Reality: the Reviewer wrote it during a reactive judgment cycle.

### Where the leak lives in code

Audit of every `authored_by` write site found three groups:

**Group A — Explicit attribution where it matters** (correct, no change):
- `routes/{documents,memory,workspace}.py` operator-initiated saves → `"operator"`
- `routes/{feed,programs}.py` + `services/{programs,workspace,invocation_dispatcher,review_proposal_dispatch,authored_substrate,outcomes/*}.py` system writes → `"system:<actor>"` per ADR-209 taxonomy
- `services/mcp_composition.py` MCP-tool writes → `"yarnnn:mcp"`
- `services/review_proposal_dispatch.py:672` Reviewer execute-proposal → `f"reviewer:{REVIEWER_MODEL_IDENTITY}"`

**Group B — Two Schedule-only injection patches compensating from the agent layer**:
- `agents/yarnnn.py:454` — `if tool_name == "Schedule" and not tool_input.get("authored_by"): tool_input["authored_by"] = "operator"`
- `agents/reviewer_agent.py:1180` — `if name == "Schedule" and not inp.get("authored_by"): inp["authored_by"] = f"reviewer:{REVIEWER_MODEL_IDENTITY}"`

**Group C — One default fall-through site at the substrate primitive**:
- `services/primitives/workspace.py:571` — `resolved_author = authored_by or "yarnnn:chat"`
- `services/primitives/workspace.py:156` (tool schema docstring documenting the default to the LLM)

Three sites all closing the same hole from different angles. ADR-274 closed it for Schedule; ADR-286 hasn't touched it; the WriteFile default still falls through to a hardcoded string regardless of caller identity.

### Why a path-aware patch is the wrong shape

The natural "small fix" — add a second special-case in `reviewer_agent.py:1180` that injects `reviewer:...` on WriteFile under `/workspace/review/` — re-creates the consumer-side ownership knowledge that ADR-286 just spent effort eliminating. Same anti-pattern, different layer:

- **ADR-286 anti-pattern**: kernel rescue patches in `is_skeleton_content` knew about specific paths
- **Path-aware authored_by patch anti-pattern**: dispatch-loop conditional in the Reviewer agent knows about specific paths

Both leak path-ownership knowledge into a runtime conditional. The role taxonomy already declares the right answer: `reviewer-workbench` (ADR-281 §3) is the role for `review/standing_intent.md`, `review/notes.md`, `working/`. The single-writer is the Reviewer. The attribution invariant follows from the *caller*, not from the *path*.

### The money-truth vocabulary residue

ADR-267 (2026-05-12) renamed `_performance.md` → `_money_truth.md` everywhere it ships substrate. The substrate file, the cockpit API route, the FE component, and most prompt text all migrated cleanly. Internal Python field names + one dead helper + 3-4 stale docstrings did not.

Live audit of surviving residue:

| Site | What | Severity |
|---|---|---|
| `agents/reviewer_agent.py:156` | `performance_md: str` field on `ReviewerContext` TypedDict | Internal field name |
| `agents/reviewer_agent.py:774-775` | `ctx.get("performance_md")` reads field, renders heading `_money_truth.md` | Same field name |
| `services/review_proposal_dispatch.py:348/372` | local `performance_md = _read_workspace_file(...)`; envelope key `"performance_md": performance_md` | Same field name |
| `services/reviewer_envelope.py:120` | docstring claims envelope key is `performance_md` | Stale docstring |
| `services/conventions.py:31/35/183/200` | `path_for_performance()` helper returning `/workspace/context/{domain}/_performance.md` | **Path string wrong** (file doesn't exist post-ADR-267) |
| `services/orchestration.py:541/549/567/575/594/617/990` | Prompt text mentions ground truth in `_performance.md` | Path string in prompt — LLM sees wrong path |

`path_for_performance()` has zero live callers — dead helper. The Reviewer's envelope key `performance_md` loads the correct file (`_money_truth.md`) but the field name lies about what the file is. The Reviewer's reasoning prompt sees `_money_truth.md` correctly in the heading but the orchestration prompts still tell it the path is `_performance.md`.

Pure-internal residue. No operator-visible behavior. Cleanup completes ADR-267's canon-to-runtime migration.

### The kernel money-truth de-instancing residue (added after Phase-2 audit)

ADR-282 (2026-05-15) named the discipline rule: `money-truth` is alpha-trader's instance-level term; the kernel-level concept is **ground-truth substrate** (FOUNDATIONS Axiom 8). The vocabulary discipline propagated through canonical docs (FOUNDATIONS, GLOSSARY, THESIS) but did NOT propagate through the kernel-prompt surfaces that ship to every Reviewer at every wake. Live audit of those surfaces:

| Site | What | Severity |
|---|---|---|
| `services/orchestration.py::DEFAULT_REVIEW_IDENTITY_MD` (L530+) | Kernel-default Reviewer IDENTITY ships "(money-truth in `_performance.md`)" + "approve-correct rate against money-truth" + concrete substrate paths (`_performance.md`, `_risk.md`, `_operator_profile.md`) to **every workspace**, including alpha-author | **HIGH — kernel violation** |
| `services/orchestration.py::DEFAULT_REVIEW_PRINCIPLES_MD` (L570+) | Kernel-default Reviewer principles cite "_performance.md" as defer condition + "outcomes reconciled in `_performance.md`" | **HIGH — kernel violation** |
| `agents/cockpit_awareness.py:60-80` | Reviewer cockpit-awareness prompt section lists `_money_truth.md` + `_money_truth_summary.md` as "Domain substrate" / "Cross-cutting" — shipped to every Reviewer at every wake regardless of program | **HIGH — kernel violation** |
| `agents/cockpit_awareness.py:148-159` | Empty-state guidance: "Missing _money_truth.md → say no track record" — kernel prompt assumes money-truth defines emptiness | **HIGH — kernel violation** |
| `agents/prompts/tools_core.py:173/252/269/278` | Shared YARNNN prompt prescribes `_money_truth.md` as canonical Reviewer surface + "Capital-EV reasoning against `_money_truth.md`" | **HIGH — kernel violation** |

For alpha-author (Netflix screenplay workspace, per ADR-283) the Reviewer wakes today and gets shipped: a kernel-default IDENTITY that says it reasons against "money-truth in `_performance.md`"; a cockpit-awareness prompt listing `_money_truth.md` as canonical substrate; a tools_core prompt saying its deliverable shape includes `_money_truth.md`. None of which exist for alpha-author. The kernel is silently treating alpha-trader's instance vocabulary as universal.

This is the same anti-pattern shape as Phase 1's `yarnnn:chat` default and ADR-286's kernel rescue patches: **kernel-level surface compensating for what it doesn't know about a specific program by hardcoding that program's vocabulary as kernel default.** ADR-280's `_workspace_guide.md` (bundle-shipped, forked at activation, declares the bundle's `substrate_abi`) is the canonical carrier of program-specific substrate paths. The kernel-prompt surfaces MUST defer to it.

### Why three cleanups belong in one ADR

All three arise from the same diagnosis: **canon evolves, runtime is patched in place, residue accumulates as drift between names and substrate.** All three are post-canon-evolution cleanups. All three honor singular-implementation discipline. All three are pure-internal (no schema change, no data migration; Phase 3 changes operator-visible LLM behavior in a *correcting* direction — the Reviewer stops being shipped vocabulary that doesn't match its program). Doing them in one ADR means one canonical artifact, one regression-gate file, three CHANGELOG entries.

They are NOT the same architectural concern — Phase 1 is a new auth contract; Phase 2 is hygiene; Phase 3 closes a kernel-vs-program boundary violation. The ADR splits them into three phases so each architectural concern lands as a distinct commit with its own diff and regression gate. ADR-284 Phase 1/2 pattern, extended.

## Decisions

### D1 — `caller_identity` is a first-class field on the auth namespace

Every auth-construction site sets `caller_identity` as it builds the namespace. The string conforms to the ADR-209 taxonomy (`operator | yarnnn:<model> | agent:<slug> | specialist:<role> | reviewer:<identity> | system:<actor>`).

Auth construction sites and their `caller_identity` values:

| Site | When | `caller_identity` |
|---|---|---|
| `agents/yarnnn.py::tool_executor` (chat-mode, operator-mediated) | Operator types into the Feed; YARNNN dispatches | `"operator"` (operator typed it; YARNNN dispatches on their behalf — matches existing Schedule injection at line 454) |
| `agents/reviewer_agent.py::invoke_reviewer` (Reviewer wake — any trigger) | Reactive / addressed / scheduled wake | `f"reviewer:{REVIEWER_MODEL_IDENTITY}"` |
| `services/primitives/registry.py::HeadlessAuth.__init__` (specialist dispatch) | Headless sub-LLM call via DispatchSpecialist | `f"specialist:{role}"` (role read from agent context if present, else `"specialist:unknown"` — telemetry-flagged) |
| `services/invocation_dispatcher.py::_MechanicalAuth` (mechanical recurrence) | Cron-fired mechanical recurrence (e.g., SyncPlatformState) | `"system:<recurrence-slug>"` (already the case for individual writes; this surfaces it on the auth) |
| `mcp_server/server.py` (MCP tool entry) | Claude.ai / external LLM via MCP | `"yarnnn:mcp"` (matches existing explicit attribution at `mcp_composition.py:677`) |

### D2 — Substrate primitives default `authored_by` from `auth.caller_identity`

`services/primitives/workspace.py::handle_write_file` line 571 changes from:

```python
resolved_author = authored_by or "yarnnn:chat"
```

to:

```python
resolved_author = authored_by or getattr(auth, "caller_identity", None) or "system:unknown"
```

LLM-supplied `authored_by` still wins (operator-explicit attribution at route-handler boundaries continues to pass `authored_by="operator"`). The fall-through `"system:unknown"` is a telemetry tripwire — emitting it means an auth-construction site forgot D1; alerts on log. Should never fire in practice.

### D3 — The two Schedule-only injection patches at the agent layer are DELETED

`agents/yarnnn.py:447-456` (12 lines including comment + injection) — DELETED. The auth's `caller_identity="operator"` propagates to Schedule via D2.

`agents/reviewer_agent.py:1173-1181` (9 lines including comment + injection) — DELETED. The auth's `caller_identity=f"reviewer:{REVIEWER_MODEL_IDENTITY}"` propagates to Schedule via D2.

The two sites become deletable because D2 handles them. Singular-implementation discipline honored: one resolution site, not three.

### D4 — `yarnnn:chat` string disappears from live code

Replace in `services/primitives/workspace.py:156` (tool schema docstring): *"defaults to 'yarnnn:chat' if omitted"* → *"defaults to the caller identity from auth (typically 'operator' from chat, 'reviewer:...' from Reviewer wake, 'specialist:...' from sub-LLM dispatch)"*.

Replace in `services/primitives/workspace.py:568-571` (inline comment) accordingly.

ADR-251's "historical `yarnnn:chat` revision rows are immutable" preserved — we change defaults for *new* writes only, no migration of existing rows.

### D5 — Envelope key `performance_md` → `ground_truth_md` (kernel-universal slot name)

Reasoned from first principles: the envelope key is a **kernel-level slot** declared in kernel code (`_UNIVERSAL_ENVELOPE_DECLS` + `_build_user_message`); bundles declare what fills it. Per ADR-282's discipline rule (kernel speaks in kernel concepts; instances speak in instance vocabulary), the slot name should describe the kernel concept (ground-truth substrate per FOUNDATIONS Axiom 8), not carry alpha-trader instance vocabulary.

`performance_md` is neither the kernel concept ("ground-truth substrate") nor the alpha-trader instance ("money-truth"); it is ADR-267 residue — the pre-rename file path `_performance.md` baked into the slot name when the substrate file was renamed to `_money_truth.md`. The alpha-trader bundle author wrote a defensive comment claiming `performance_md` is "instance-agnostic," but the comment rationalizes preserved-continuity rather than declares a principled name. First-principles answer: rename the slot to `ground_truth_md` (kernel concept) and delete the rationalizing comment.

**Kernel code** (4 files):

1. `services/reviewer_envelope.py` — `_UNIVERSAL_ENVELOPE_DECLS` entry key + helper return-dict key + docstring → `ground_truth_md`
2. `agents/reviewer_agent.py:156` — `ReviewerContext.performance_md` → `ground_truth_md`
3. `agents/reviewer_agent.py:774-775` — reader updated; heading content stays bundle-instance-aware (kernel can render generic heading; bundle's `_workspace_guide.md` directs Reviewer to read its specific file)
4. `services/review_proposal_dispatch.py:348-372` — local var + envelope dict key → `ground_truth_md`

**Bundle MANIFESTs** (5 files — atomic rename in same commit):

1. `docs/programs/alpha-trader/MANIFEST.yaml` — `key: performance_md` → `key: ground_truth_md`; defensive "instance-agnostic" comment DELETED (slot name now matches the kernel concept; no rationalization needed)
2. `docs/programs/alpha-author/MANIFEST.yaml` — same
3. `docs/programs/alpha-commerce/MANIFEST.yaml` — same
4. `docs/programs/alpha-defi/MANIFEST.yaml` — same
5. `docs/programs/alpha-prediction/MANIFEST.yaml` — same

**No bundle ABI version bump needed**: no consumer outside the kernel reads the envelope key name. Kernel reads its own keys; bundles declare them; the loop matches names. Atomic rename = clean state.

**Alpha-trader's substrate file `_money_truth.md` does NOT rename** — that file is alpha-trader instance vocabulary per ADR-282 D8 and stays. The slot name (`ground_truth_md`) is the kernel concept; the file path (`context/trading/_money_truth.md`) is the alpha-trader instance.

### D6 — `path_for_performance()` helper DELETED

Zero live callers (verified via grep). Singular-implementation discipline: dead code is deleted, not preserved. `services/conventions.py` line ~182-200 block goes.

### D7 — Stale docstrings + non-prompt path-strings updated

The split principle: **docstring examples that cite a concrete file path use the instance file name (`_money_truth.md`) because they are naming the actual file; kernel slot names use the kernel concept (`ground_truth_md`) because they are naming the abstract role.**

Phase 2 docstring updates use the instance file name where they describe alpha-trader file shape:

- `services/conventions.py` module docstring path table (lines 31, 35) — `performance: /workspace/context/{domain}/_performance.md` → row deleted (bundles declare their own substrate paths; conventions.py is module-doc-only after dead-helper deletion)
- `services/narrative.py:23`, `services/execution_router.py:223`, `services/primitives/dispatch_specialist.py:96`, `services/primitives/revisions.py:58`, `services/outcomes/reconciler.py:115` — all docstring path examples; `_performance.md` → `_money_truth.md` (instance vocabulary is correct here — these docstrings explain alpha-trader-shaped code paths)
- `api/scripts/seed_seulkim_substrate.py:28/186` + `api/scripts/oneshot/phaseB_unify_recurrences.py:127/131/132` — one-shot scripts already executed; update path references for archival correctness

**`services/orchestration.py` prompt text** (lines 541, 549, 567, 575, 594, 617, 990) — moved to Phase 3 (kernel-prompt de-instancing). These are not stale-path docstrings; they are kernel-default prompt content shipped to the LLM, and the right framing is "ground-truth substrate per Axiom 8 + your bundle's `_workspace_guide.md`" — Phase 3 handles them properly.

### D8 — Phase 3 — Kernel money-truth de-instancing

Per FOUNDATIONS Axiom 8 + ADR-282 vocabulary discipline: kernel-prompt surfaces speak in `ground-truth substrate` (kernel concept); bundles declare what their ground-truth instance is via `_workspace_guide.md` (per ADR-280). Singular-implementation: no hardcoded instance paths in kernel prompts; the bundle-shipped guide is the sole carrier.

**`services/orchestration.py::DEFAULT_REVIEW_IDENTITY_MD`** — rewrite to speak in ground-truth substrate. Where it says "money-truth in `_performance.md`" → "ground-truth substrate per Axiom 8 (your bundle's `_workspace_guide.md` declares the instance)". Where it lists concrete domain-substrate paths (`_performance.md`, `_risk.md`, `_operator_profile.md`) → abstract to "domain substrate per your `_workspace_guide.md`." Where it says "approve-correct rate against money-truth" → "approve-correct rate against ground-truth substrate."

**`services/orchestration.py::DEFAULT_REVIEW_PRINCIPLES_MD`** — same treatment. Remove specific `_performance.md` references; "When deferring because _performance.md is empty" → "When deferring because ground-truth substrate is empty" with the bundle-shipped principles overlaying with the instance-specific guidance.

**`agents/cockpit_awareness.py:60-80`** — the "Domain substrate" + "Cross-cutting" sections that today hardcode `/context/{domain}/_money_truth.md` + `/context/_money_truth_summary.md`. Delete the hardcoded paths. Replace with a single line pointing at `_workspace_guide.md` as the authoritative substrate-topology source. The Reviewer already reads `_workspace_guide.md` at every wake per ADR-280; the cockpit-awareness prompt should defer to it, not duplicate it.

**`agents/cockpit_awareness.py:148-159`** — empty-state guidance section. "Missing _money_truth.md" + "Reasoning about per-signal performance" + reconciler/`by_signal` paragraphs are all alpha-trader instance vocabulary in kernel prose. Replace with generic empty-state posture: "When ground-truth substrate is missing or stale, surface the gap rather than fabricate — your bundle's `_workspace_guide.md` declares what your ground-truth substrate is."

**`agents/prompts/tools_core.py:173`** — "If `_money_truth.md` hasn't been reconciled in three days, flag staleness" — alpha-trader instance specifics in shared YARNNN prompt. Delete; let the bundle's `_workspace_guide.md` or operator's MANDATE encode staleness expectations.

**`agents/prompts/tools_core.py:252/269`** — "Reviewer reasons against `_money_truth.md`" / "Capital-EV reasoning against `_money_truth.md`" → "Reviewer reasons against ground-truth substrate (per Axiom 8 + the bundle's `_workspace_guide.md`)." The "Capital-EV" phrasing is alpha-trader instance reasoning shape; kernel prompt should say "ground-truth-grounded reasoning."

**`agents/prompts/tools_core.py:278`** — "Deliverables — proposals awaiting review, briefs, weekly reviews, `_money_truth.md`" — `_money_truth.md` is an alpha-trader instance file, not a universal deliverable shape. Remove from kernel; let bundles enumerate their deliverables.

**`agents/reviewer_agent.py:33/463`** — docstrings. Update for ADR-282 vocabulary alignment (kernel docstrings should say "ground-truth substrate per Axiom 8" not "money-truth in `_performance.md`").

This is operator-visible LLM behavior change in a correcting direction: alpha-author's Reviewer stops being shipped alpha-trader's vocabulary; alpha-trader's Reviewer continues to read `_money_truth.md` (via its bundle's `_workspace_guide.md`).

### D9 — `api/prompts/CHANGELOG.md` entries per execution-discipline rule 7

Phase 1 entry: caller_identity threading + WriteFile default resolution change + Schedule injection deletion at yarnnn.py + reviewer_agent.py + tool schema docstring change.

Phase 2 entry: `performance_md` → `money_truth_md` field rename + stale `_performance.md` docstring corrections + dead helper deletion.

Phase 3 entry: kernel-prompt money-truth de-instancing — `DEFAULT_REVIEW_IDENTITY_MD` + `DEFAULT_REVIEW_PRINCIPLES_MD` + `cockpit_awareness.py` + `tools_core.py` rewritten to speak in ground-truth substrate, with bundle `_workspace_guide.md` as authoritative carrier of instance paths.

### D10 — Regression gate at `api/test_adr288_caller_identity.py`

Phase 1 assertions:

- Every auth-construction site sets `caller_identity` (grep test enforces — no `SimpleNamespace(client=...)` or `HeadlessAuth(...)` without `caller_identity` field).
- `handle_write_file` default resolution reads `auth.caller_identity` when `authored_by` not supplied.
- No live-code grep match for `yarnnn:chat` outside test fixtures.
- Schedule injection patches at `agents/yarnnn.py` + `agents/reviewer_agent.py` are deleted (grep test).

Phase 2 assertions extend:

- No live-code grep match for `performance_md` as a Python identifier (field name + variable name + dict key).
- No live-code grep match for `path_for_performance` (helper deleted).
- Live-code grep for `_performance.md` returns only allow-listed archival references.

Phase 3 assertions extend:

- `services/orchestration.py::DEFAULT_REVIEW_IDENTITY_MD` + `DEFAULT_REVIEW_PRINCIPLES_MD` contain zero `_money_truth.md` or `_performance.md` string literals.
- `services/orchestration.py::DEFAULT_REVIEW_IDENTITY_MD` + `DEFAULT_REVIEW_PRINCIPLES_MD` mention `ground-truth substrate` (at least once each) — positive assertion that the de-instancing landed.
- `agents/cockpit_awareness.py` contains zero `_money_truth.md` string literals.
- `agents/cockpit_awareness.py` mentions `_workspace_guide.md` as the substrate-topology source.
- `agents/prompts/tools_core.py` contains zero `_money_truth.md` string literals.
- `agents/reviewer_agent.py` docstrings updated to ADR-282 vocabulary (no kernel-level "money-truth" claims; instance-pointer phrasings allowed).

### D11 — Out of scope (deferred)

- **Migration of historical `yarnnn:chat` revision rows.** ADR-251 froze these as immutable revision-chain data. Untouched. The FE's `formatHeadAuthor()` mapping in `ContentViewer.tsx` (ADR-236) continues to handle the `yarnnn:` prefix for both old and new rows.
- **New caller identities beyond ADR-209 taxonomy.** No new prefixes. The six existing (`operator`, `yarnnn:<model>`, `agent:<slug>`, `specialist:<role>`, `reviewer:<identity>`, `system:<actor>`) stay.
- **Resolver-pattern alternative.** Considered: `resolve_caller_identity(auth)` helper that maps existing auth-shape signals (`reviewer_caller=True` → `"reviewer:..."`, presence of `agent_slug` → `"agent:..."`). Rejected because it re-creates the consumer-side caller-knowledge that ADR-286 spent effort eliminating. Explicit-at-construction-site honors the canonical arc.
- **Substrate path changes.** `_money_truth.md` is canonized by ADR-267 and stays. ADR-282 D8 preserves alpha-trader instance code unchanged. This ADR only stops misnaming internal fields/helpers/docstrings and stops hardcoding instance paths into kernel prompts.
- **Code-level rename of `_money_truth.md` to `_ground_truth.md`.** Considered and rejected — would reverse ADR-282 D8 which explicitly preserves instance-level identifiers (`_money_truth.md`, `services/outcomes/*.py`, `TraderMoneyTruth.tsx`, `cockpit.money_truth` binding key, `/api/cockpit/money-truth` route). Alpha-trader's instance vocabulary is correct for alpha-trader; the violation was kernel-level hardcoding, not instance-level naming.
- **Bundle `substrate_abi` schema extensions.** Today's `_workspace_guide.md` carries `path_zones` + `reviewer_wake_envelope` per ADR-280; we don't add new schema fields here. If Phase 3's de-instancing surfaces a need for explicit `ground_truth_substrate_paths` declaration in the guide, that's a future ADR — for now the bundle's prose body + existing `path_zones` carry it.
- **Reviewer behavioral changes.** Sunday's wake produced excellent standing_intent.md content; the attribution prefix was wrong but the behavior was right. Phase 1+2 fix audit-trail without touching behavior. Phase 3 fixes Reviewer perception of what its substrate is (correcting direction: alpha-author Reviewer stops seeing alpha-trader vocabulary), but the persona-frame posture (active-principal, standing-intent contract) is preserved.

## Cascade plan (three atomic commits)

### Phase 1 — Caller identity as first-class auth field

One commit:

- `services/primitives/registry.py::HeadlessAuth.__init__` — add `caller_identity` parameter (defaults derived from `agent`/`task_slug` shape)
- `services/invocation_dispatcher.py::_MechanicalAuth.__init__` — add `caller_identity` parameter; site at line 715 sets it to `f"system:{recurrence.slug}"`
- `agents/yarnnn.py` — auth namespace gains `caller_identity="operator"`; Schedule injection block at 447-456 DELETED
- `agents/reviewer_agent.py:1026-1034` — auth namespace gains `caller_identity=f"reviewer:{REVIEWER_MODEL_IDENTITY}"`; Schedule injection block at 1173-1181 DELETED
- `mcp_server/server.py` + `services/mcp_composition.py` — auth construction at MCP boundary sets `caller_identity="yarnnn:mcp"` (replaces three explicit per-call passes at composition.py:677/683/687)
- `services/primitives/workspace.py:156` (tool docstring) — updated per D4
- `services/primitives/workspace.py:568-571` (inline comment + default) — updated per D2/D4
- `api/test_adr288_caller_identity.py` — regression gate
- `api/prompts/CHANGELOG.md` — Phase 1 entry

### Phase 2 — Envelope key `performance_md` → `ground_truth_md` + stale `_performance.md` docstring residue

One commit, atomic across kernel + 5 bundle MANIFESTs:

- `services/reviewer_envelope.py` — `performance_md` envelope key + docstring → `ground_truth_md`
- `agents/reviewer_agent.py:156` — `ReviewerContext.performance_md` → `ground_truth_md`
- `agents/reviewer_agent.py:774-775` — reader updated
- `services/review_proposal_dispatch.py:348-372` — local var + envelope dict key → `ground_truth_md`
- `docs/programs/{alpha-trader,alpha-author,alpha-commerce,alpha-defi,alpha-prediction}/MANIFEST.yaml` — bundle declarations `key: performance_md` → `key: ground_truth_md`; alpha-trader's defensive "instance-agnostic" comment DELETED
- `services/conventions.py` — `path_for_performance()` DELETED; module docstring updated
- `services/{narrative,execution_router,primitives/dispatch_specialist,primitives/revisions,outcomes/reconciler}.py` — stale docstring path references `_performance.md` → `_money_truth.md`
- `api/scripts/` archival path references updated
- `api/test_adr288_caller_identity.py` extends — Phase 2 assertions
- `api/prompts/CHANGELOG.md` — Phase 2 entry

Phase 2 closes two ADR-267 + ADR-282 residues: the kernel envelope-key naming carries alpha-trader instance vocabulary (`performance` was alpha-trader's pre-rename file name); the stale `_performance.md` docstrings reference a file that doesn't exist post-ADR-267. Phase 3 handles the larger kernel-prompt de-instancing where the violation is the use of `_money_truth.md` itself in kernel-level prose.

### Phase 3 — Kernel money-truth de-instancing

One commit:

- `services/orchestration.py::DEFAULT_REVIEW_IDENTITY_MD` — rewritten per D8 (ground-truth substrate framing; concrete instance paths removed; bundle `_workspace_guide.md` pointer)
- `services/orchestration.py::DEFAULT_REVIEW_PRINCIPLES_MD` — rewritten per D8
- `agents/cockpit_awareness.py:60-80` — domain substrate section rewritten; pointer to `_workspace_guide.md` instead of hardcoded paths
- `agents/cockpit_awareness.py:148-159` — empty-state guidance rewritten to ground-truth substrate framing
- `agents/prompts/tools_core.py` — four sites (L173/252/269/278) updated per D8
- `agents/reviewer_agent.py` — docstring sites (L33/463) updated for ADR-282 vocabulary alignment
- `api/test_adr288_caller_identity.py` extends — Phase 3 assertions (positive + negative grep tests on the de-instanced surfaces)
- `api/prompts/CHANGELOG.md` — Phase 3 entry

Phase 3 changes operator-visible LLM behavior in a correcting direction: alpha-author's Reviewer (post-ADR-283) stops being shipped alpha-trader's vocabulary as kernel default. Alpha-trader's Reviewer continues to read `_money_truth.md` (via its bundle's `_workspace_guide.md`'s `path_zones` declarations + the persona-frame in its bundle's `IDENTITY.md` + `principles.md`).

## Test plan

Phase 1 regression gate `api/test_adr288_caller_identity.py`:

- Construct each of five auth namespaces; assert `caller_identity` field present
- Mock `handle_write_file` call with reviewer auth + no explicit `authored_by`; assert revision row carries `reviewer:...` attribution (not `yarnnn:chat`)
- Mock with operator route handler + explicit `authored_by="operator"`; assert override still wins
- Grep test: no live-code match for `yarnnn:chat` string outside this ADR + fixtures
- Grep test: `agents/yarnnn.py:454-456` Schedule injection block absent
- Grep test: `agents/reviewer_agent.py:1175-1181` Schedule injection block absent

Phase 2 regression gate extends:

- Grep test: no live-code match for Python identifier `performance_md` (field name, variable name, dict key)
- Grep test: no live-code match for function name `path_for_performance`
- Grep test: `_performance.md` string occurs only in allow-listed archival one-shot scripts
- Grep test: prompt text in `orchestration.py` mentions `_money_truth.md`, never `_performance.md`

Sibling ADRs regression-gated green pre-commit per cascade discipline:
- ADR-274 (Schedule trigger-authoring) — Schedule still fail-fast on missing `authored_by`; D1+D2 ensure it never reaches the failure path
- ADR-276 (reactive envelope) — governance-envelope helper untouched
- ADR-281 (single-writer judgment_log) — writer enforcement untouched
- ADR-284 (standing_intent) — substrate contract untouched; only the attribution prefix changes
- ADR-286 (kernel/program substrate boundary) — single-writer-per-path discipline reinforced (this ADR finishes the same arc at the authorship layer)

## Why this is structurally right

The compositional arc (ADR-274 → ADR-276 → ADR-286 → ADR-288) is: every runtime concern that leaked across N compensating sites collapses to a single canonical declaration at the boundary. Trigger-authoring (274) declares `authored_by` is required; governance envelope (276) declares one helper threads it; substrate single-writer (286) declares one path = one writer; **caller identity (288) declares one auth = one identity**. The four together close the substrate-write-attribution surface to a clean shape: every write is attributed, every attribution is sourced from the auth's caller_identity, every auth has caller_identity set at construction time, every write goes through the single path-owner.

The vocabulary-cleanup half (`performance_md` → `money_truth_md` + dead helper deletion + prompt path-strings) is the smaller-scoped completion of ADR-267's canon migration. It's not new architecture — it's hygiene that bundles cleanly with the caller-identity work because both are post-canon-evolution residue cleanups landing in adjacent files with shared regression gates.

After this ADR: the only `yarnnn:chat` strings in the codebase are in the workspace_file_versions table (immutable historical data per ADR-251) and FE label-mapping (which already handles `yarnnn:*` prefix generically). The only `performance_md` Python identifiers are gone. The Reviewer's audit trail tells the truth: when Sonnet wakes for kvk's signal-evaluation Monday 13:45 UTC, its standing_intent.md write will carry `authored_by="reviewer:ai:reviewer-sonnet-v8"`. Three compensating patches collapse to one declaration. One more leak closes; one more line of the canon → runtime correspondence holds true.
