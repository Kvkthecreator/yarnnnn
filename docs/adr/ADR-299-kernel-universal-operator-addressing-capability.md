# ADR-299: Operator-Addressing System Infrastructure — `send_operator_email`

**Status**: Implemented 2026-05-27 (second-pass rewrite incorporates the 2026-05-25 v5 canary resolution as D8 architectural commitment; Reviewer-side exclusion is permanent by design, no pending experiment).

**Date**: 2026-05-27 (second-pass rewrite). Original ADR 2026-05-22, corrected four times in Discovery notes 1–4 (2026-05-24 / 2026-05-25), Discovery 4 Path A reverted 2026-05-25 with same-day v5 canary confirming hypothesis A. First-pass rewrite 2026-05-27 carried forward pre-resolution "open question" framing in error; second-pass rewrite (this) corrects it.

**Authors**: KVK, Claude

**Depends on**: ADR-040 (operator notification emails), ADR-118 (Skills as Capability Layer), ADR-192 (Resend integration), ADR-202 (External Channel Discipline / daily-update emails), ADR-217 (AUTONOMY gating), ADR-222 (OS framing), ADR-224 (Kernel/Program Boundary), ADR-269 (Capability Flow Wiring), ADR-275 (operator-authored `_preferences.yaml`), ADR-283 (alpha-author bundle)

**Amends**: ADR-283 D7 (audience-bearing rejection still holds; operator-addressing system infrastructure is a separate surface)

**Preserves**: Singular Implementation discipline, kernel/program boundary, FOUNDATIONS Axiom 1, ADR-118 capability layer semantics

**Supersedes**: All four Discovery notes from the prior shape of this ADR, the "kernel-universal capability" framing, the parallel registry / always-surface-pass-over-CAPABILITIES implementation, AND the "Reviewer authority — open question" framing that the 2026-05-27 first-pass rewrite preserved unnecessarily. The 2026-05-25 v5 canary [evaluation finding](../observations/2026-05-25-042346-adr299-always-surface-resolution/RESOLUTION.md) had already confirmed hypothesis A (tool perturbation collapses Reviewer judgment quality) and recommended permanent exclusion of `platform_email_send_to_operator` from the Reviewer's tool surface; the first-pass rewrite carried forward the pre-resolution framing in error. This rewrite incorporates the v5 finding as the architectural commitment in D8.

---

## The previous framing was wrong. The rewrite is in the title.

`send_operator_email` was registered as a **capability** ("kernel-universal capability" — a new class introduced by the original ADR-299). That framing collapsed two distinct architectural categories:

1. **Workspace capabilities** — declarative metadata describing work the workspace can declare it needs. Cognitive descriptors (`summarize`, `data_analysis`), internal-tool surfaces (`web_search`), asset-production dispatches (`chart`, `mermaid`, `image`, `video_render`), platform-integration surfaces (`read_slack`, `write_notion`). All live in `CAPABILITIES`. All describe **work being done *for* the workspace** — rendered, queried, summarized, written, dispatched.
2. **System infrastructure** — internal plumbing the kernel uses to operate. The Postgres database. The LLM API client. The yarnnn-render Docker service. The substrate filesystem. The cron scheduler. **The system Resend wire** — already in use for ADR-040 notifications and ADR-202 daily-update emails, both of which are called directly from kernel code paths and were never in `CAPABILITIES`.

`send_operator_email` is system infrastructure, not a workspace capability. The work being done is **the system speaking *as itself* to the operator-identity** — using environment-shared infrastructure (the system Resend wire, identical to ADR-040 + ADR-202) with the addressee structurally resolved to `auth.users.email` for the workspace owner. The wire and the addressee are both determined outside any workspace declaration. It does not describe work done for the workspace; it describes the system addressing its operator.

The only reason `send_operator_email` ended up in `CAPABILITIES` and not alongside ADR-040 + ADR-202 was the **invocation pattern**: the Reviewer/agent's decision to send is an LLM-judgment moment rather than a kernel-deterministic trigger. ADR-040 fires automatically on notification events; ADR-202 fires automatically from the daily-update task pipeline; ADR-299 fires when an agent decides to call a tool. Identical infrastructure, identical wire, identical addressee resolution discipline — different invocation shape.

The previous framing's misclassification produced four cascading Discovery-note corrections (class name, wire choice, resolution path, Reviewer surface) that all addressed the wrong layer. Each note correctly identified that the *implementation* was misaligned with the *intent*, but treated the intent as fixed and the implementation as needing patching. The intent itself was the bug. The rewrite below relocates the entity to its correct architectural home and removes the resulting layer cascade in one motion.

## Decision

### D1. Taxonomy: workspace capability vs. system infrastructure

The kernel registers two distinct categories of LLM-invokable surfaces:

**Workspace capabilities** — `CAPABILITIES` in `api/services/orchestration.py`. Declarative metadata describing work the workspace can declare it needs. Bundles list capability keys in `MANIFEST.yaml::capabilities`; tasks list them in TASK.md `## Required Capabilities`. The kernel's job is to honor those declarations during dispatch. Single axis of variation: **does this capability require an operator-connected third-party account (`platform_connection_requirement: {platform: ..., status: active}`) or not (`None`)?** Connection-required entries flow through `platform_connections` gating; no-connection entries surface directly. All entries describe work *for* the workspace.

**System infrastructure** — kernel plumbing the system uses to operate. Not registered in `CAPABILITIES`. Not bundle-declared. Not capability-gated. Already in production at multiple call sites: the Postgres connection (every primitive), the LLM API client (every agent / Reviewer / specialist invocation), the yarnnn-render Docker service (RuntimeDispatch dispatch), the **system Resend wire** (ADR-040 notifications, ADR-202 daily-update emails, this ADR's `send_operator_email`), the cron scheduler, the substrate filesystem. System infrastructure is invoked from kernel code paths — sometimes deterministically (notification triggers, daily-update cron), sometimes by LLM judgment (`send_operator_email`). The invocation shape is orthogonal to the architectural classification.

The distinguishing question for any new LLM-invokable surface is:

> **Does this describe work being done *for* the workspace (declared, dispatched, gated by workspace state), or is it the system speaking *as itself* through environment-shared infrastructure (kernel-owned wire, addressee determined outside workspace declaration)?**

If for-the-workspace → `CAPABILITIES`. If system-as-itself → system infrastructure.

### D2. `SYSTEM_INFRASTRUCTURE_TOOLS` — explicit registry naming the existing pattern

The kernel has been using system-Resend-via-`RESEND_API_KEY` since ADR-040 + ADR-202, but those call sites are direct (function call from notification trigger / daily-update task) and the pattern was never named. ADR-299 introduces an LLM-invoked surface over the same infrastructure, and that makes the pattern explicit enough to need a registry.

**New constant** in `api/services/platform_tools.py`:

```python
SYSTEM_INFRASTRUCTURE_TOOLS: list[dict] = [
    EMAIL_SEND_TO_OPERATOR_TOOL,
]
```

Single entry today. The registry exists so future LLM-invokable system-infrastructure surfaces have a documented home and a discipline rule for what belongs: **only LLM-invokable surfaces over environment-shared infrastructure where the addressee/target is determined outside workspace declaration.** Direct call sites (ADR-040 notifications, ADR-202 daily-update emails) stay direct — they don't surface to any LLM, so registry inclusion would be ceremony without purpose.

The registry's responsibility is **surfacing** to LLM tool-use loops. ADR-040 and ADR-202 share the *infrastructure* (system Resend wire) but not the *surface* (they're not in any LLM's tool list); inclusion in `SYSTEM_INFRASTRUCTURE_TOOLS` is gated on the latter.

### D3. Tool surfacing path — `SYSTEM_INFRASTRUCTURE_TOOLS` merged explicitly, not derived

`get_platform_tools_for_capabilities` is rewritten. The previous "loop over kernel `CAPABILITIES` dict and surface entries with `platform_connection_requirement is None`" always-surface pass is deleted — that filter was the mechanism by which the misclassification leaked into runtime. Without it, kernel `CAPABILITIES` entries like `summarize` or `chart` would be incorrectly surfaced unconditionally to every agent on every wake.

New shape:

```python
async def get_platform_tools_for_capabilities(auth, capabilities):
    # Workspace capabilities — explicit declaration required, gated on platform_connections
    tools_from_capabilities = []
    for cap in (capabilities or []):
        provider = CAPABILITY_PROVIDER_MAP.get(cap)
        if provider and provider in connected_providers:
            tools_from_capabilities.extend(PLATFORM_TOOLS_BY_CAPABILITY.get(cap, []))

    # System infrastructure — always surfaced, no declaration required
    tools_from_infrastructure = list(SYSTEM_INFRASTRUCTURE_TOOLS)

    return _dedup_preserving_order(tools_from_infrastructure + tools_from_capabilities)
```

Two source layers, one resolution function, one return list. Each layer's inclusion criterion is explicit and structural: workspace capabilities require declaration + provider gate; system infrastructure surfaces unconditionally because it's part of the kernel's operating surface.

`runtime: "kernel"` as a value on the `CAPABILITIES` dict is deleted. That sentinel was the mechanism by which `send_operator_email` declared "I'm not really a workspace capability"; now that it has its own home, the sentinel becomes unused, and `runtime` values reduce to the actual runtimes that dispatch workspace work (`internal | python_render | external:slack | external:notion | external:github`).

### D4. `_preferences.yaml::operator_notifications:` schema unchanged; comment rationale rewritten

The bundle reference workspaces' `operator_notifications:` block shape is correct under the new framing. Each entry's `slug` / `description` / `cadence_hint` / `active` carries the operator's standing approval to fire `platform_email_send_to_operator` for that notification class. The opt-in IS the authorization (per the framework below in D5).

The schema's comment block, however, was written under the prior framing and contains two stale claims that contradict the live code:

1. *"Operator-addressing capabilities (per ADR-299 D1, operator-addressing class)"* — the entity is no longer classified as a capability.
2. *"Wire-gate still applies: requires an active Resend connection per ADR-192 Phase 4. When Resend isn't connected, the tool degrades silently"* — the live code uses the system Resend wire (`RESEND_API_KEY` env var); no `platform_connections` row required; the tool never degrades on "missing connection."

Both bundle reference workspaces (`alpha-author`, `alpha-trader`) get their comment blocks rewritten in the same commit as the code rewrite. The YAML shape under the comments stays exactly as-is.

### D5. Authorization model: `_preferences.yaml` opt-in is observability authorization

System infrastructure that addresses the operator-identity does **not** route through the AUTONOMY ceiling (ADR-217 + ADR-249). AUTONOMY gates *consequential actions* — third-party-affecting writes that move capital, change external-counterparty state, bind publication. Operator-self-addressing observability sends do not move capital and do not bind publication.

The authorization model:

- The operator declares `operator_notifications.{slug}.active: true` in `_preferences.yaml` — that declaration **is** the standing approval to fire `platform_email_send_to_operator` for that notification class. Per ADR-275, operator authority on `_preferences.yaml` is structural; reviewer reconciles cadence preferences via `Schedule()` calls but does not author the preferences themselves.
- AUTONOMY `delegation: manual` does NOT block these — the operator already approved them by declaring the preference. AUTONOMY scoping is for third-party-affecting writes only.
- Default-off: bundle-shipped entries ship `active: false` to avoid spamming any operator before they've consented. The operator flips `active: true` per workspace.
- Absent `_preferences.yaml::operator_notifications` block → the Reviewer/agent should not fire `platform_email_send_to_operator`. The system surface is available but unused. (The Reviewer's persona-frame teaches this discipline per D7 below.)

This authorization model is identical in spirit to how ADR-040 + ADR-202 already operate — both fire emails to the operator without per-action AUTONOMY click, both gated by operator-side configuration (notification subscriptions for ADR-040; daily-update task active state for ADR-202). The pattern was already canonical; ADR-299 names it.

### D6. Addressee structurally pinned to operator-identity

`platform_email_send_to_operator` accepts `subject` and `html`. It does **not** accept `to`, `cc`, `bcc`, `from_email`, or `from_name` — any LLM attempt to supply these returns a structured error.

The addressee resolves at send-time from `auth.users.email` for the workspace owner via `get_user_email(auth.client, auth.user_id)`. Never cached, never substrate-stored, never LLM-supplied. The structural pin is the load-bearing property that distinguishes `send_operator_email` from audience-bearing email surfaces (`platform_email_send`, `platform_email_send_bulk` in bundle-specific commerce capabilities per ADR-192 Phase 4): operator-addressing infrastructure cannot be abused to address third parties, by tool-schema construction.

The `Reply-To` header is pinned to the operator's own email so any reply lands in their inbox naturally; `From` defaults to `yarnnn <noreply@yarnnn.com>` via the `RESEND_FROM_EMAIL` env var (canonical with ADR-040 + ADR-202).

### D7. Persona-frame teaches the system-infrastructure framing

The Reviewer's persona-frame (`api/agents/reviewer_agent.py::_PERSONA_FRAME`) section currently introducing the tool gets rewritten under the new framing. The shape of the rewrite:

- Names `platform_email_send_to_operator` as **operator-addressing system infrastructure** — distinguishing it from substrate writes (where the Reviewer speaks as itself), capital actions (third-party-affecting, AUTONOMY-gated), and audience-bearing email (bundle-specific commerce capability).
- Cites the system Resend wire's existing call sites (ADR-040, ADR-202) so the Reviewer perceives this as established infrastructure, not a novel surface.
- Names `_preferences.yaml::operator_notifications.{slug}.active: true` as the operator's standing approval — distinct from AUTONOMY gating.
- Reaffirms the discipline rule: observability sends fire when the cycle produces material worth surfacing; routine no-material cycles do not warrant an email even if cadence_hint moment is right.

Persona-frame rewrite is bundled in the same commit as the code rewrite per Singular Implementation + the Prompt Change Protocol (CHANGELOG entry required).

### D8. The Reviewer is permanently excluded from `SYSTEM_INFRASTRUCTURE_TOOLS` by architectural design

The Reviewer's tool surface is built from `REVIEWER_PRIMITIVES` in `api/services/primitives/registry.py`, not from `get_platform_tools_for_capabilities`. `EMAIL_SEND_TO_OPERATOR_TOOL` is **not in `REVIEWER_PRIMITIVES` and will not be added** — this is the load-bearing architectural commitment, not a deferred decision.

**The evidence**: the 2026-05-25 v5 canary ([RESOLUTION.md](../observations/2026-05-25-042346-adr299-always-surface-resolution/RESOLUTION.md)) ran the structural variable isolation across three cycles on the same substrate, hook, and prompt — only the tool count varied. The comparison:

| Cycle | Tool surface size | LLM rounds | Output tokens | Substrate writes | Verdict |
|---|---|---|---|---|---|
| v3 baseline | 21 (no tool) | 10 | 6,139 | judgment_log + standing_intent | reject |
| v4 with tool | 22 (with tool) | 4 | 1,577 | **none** | **stand_down** |
| v5 reverted | 21 (no tool) | 12 | 14,615 | judgment_log + standing_intent | reject_publication |

Adding the 22nd tool — particularly one carrying strong "explicit action with consequence" framing — collapsed Reviewer output by ~74% and produced an escape-hatch `stand_down` verdict with zero substrate writes. Reverting restored substantive judgment (in fact exceeded v3 baseline by 2.4x output). Substrate receipts: `execution_events` rows v3 `252e75f6`, v4 `58d325df`, v5 `1e9ac22c`.

**The architectural distinction**: there are two structurally different classes of LLM-invocable agent surfaces in the system, and they have different tolerances for tool-list size:

| Class | Agents | Primary task | Tool-list sensitivity |
|---|---|---|---|
| **Task-bearing** | YARNNN chat, headless specialists (researcher/writer/analyst/tracker/designer/reporting), headless task pipeline | Tool-use IS the work (dialogue, production, action) | Low — adding tools is in-distribution |
| **Judgment-bearing** | Reviewer | Substrate evaluation under judgment-shaped prompt; tool-use is corrosive to the primary task | High — empirically validated; v4 evidence shows the 21→22 transition is load-bearing for this surface |

`SYSTEM_INFRASTRUCTURE_TOOLS` surfaces unconditionally to task-bearing agents because tool-use IS their work. The Reviewer is judgment-bearing; tool-use degrades its primary task. The curated `REVIEWER_PRIMITIVES` design from ADR-258 revised was made for this reason, and the v4/v5 data confirms the rationale empirically.

**Operator-addressing notifications tied to Reviewer verdicts** belong on a post-judgment dispatcher hook, not in the Reviewer's tool surface. The pattern already exists: `services/notifications.py` fires on `action_proposals` arrivals (per ADR-040); the same shape applied to Reviewer verdict landing in substrate would read `/workspace/review/judgment_log.md` + `/workspace/review/standing_intent.md` + the operator's `_preferences.yaml::operator_notifications` block and dispatch out-of-band. Out of scope for this ADR but explicitly named as the correct integration path for that use case.

**Re-introduction guardrail**: should a future architectural need genuinely require the Reviewer to invoke an additional tool (operator-addressing or otherwise), the discipline from [RESOLUTION.md §"Discipline lesson"](../observations/2026-05-25-042346-adr299-always-surface-resolution/RESOLUTION.md) applies — measure verdict-quality regression against the baseline tool surface via N≥3 canaries before the addition is accepted as net-positive. A capability's structural reachability is not sufficient justification for inclusion; verdict-quality preservation is the load-bearing constraint.

The agent path (non-Reviewer LLM tool-use) **does** surface `platform_email_send_to_operator` unconditionally via the `SYSTEM_INFRASTRUCTURE_TOOLS` merge in `get_platform_tools_for_capabilities` and `get_platform_tools_for_user` (D3). The architecture is structurally complete across all four agent surfaces.

## Implementation

Singular Implementation discipline: this rewrite lands as **one atomic commit**. No dual paths, no backwards-compat shim, no parallel registries. The four Discovery notes' code is the legacy being replaced.

### Code rewrite

1. **`api/services/orchestration.py`** — delete the `send_operator_email` entry from `CAPABILITIES` dict (lines 1234–1240). The `runtime: "kernel"` value disappears from the codebase. No replacement; the entry's content moves to `EMAIL_SEND_TO_OPERATOR_TOOL` (where it already lives) and the merge logic in `SYSTEM_INFRASTRUCTURE_TOOLS`.

2. **`api/services/platform_tools.py`** —
   - Delete `"send_operator_email": ["platform_email_send_to_operator"]` from `PLATFORM_TOOLS_BY_CAPABILITY` (line ~983–984).
   - Add `SYSTEM_INFRASTRUCTURE_TOOLS = [EMAIL_SEND_TO_OPERATOR_TOOL]` constant after the `EMAIL_TOOLS` list (with explanatory header comment).
   - Rewrite `get_platform_tools_for_capabilities`:
     - Delete the "always-surface pass" that loops over kernel `CAPABILITIES` (lines ~1095–1115).
     - Replace with explicit `SYSTEM_INFRASTRUCTURE_TOOLS` merge before the wire-gated capabilities pass.
     - Final return: `SYSTEM_INFRASTRUCTURE_TOOLS` tools first (sorted by tool name for determinism), then wire-gated workspace capability tools.
   - Tool definition comment block at line ~813–825 rewritten to reflect system-infrastructure framing.

3. **`api/services/primitives/registry.py`** — comment block at line ~426 documenting the Reviewer-side exclusion is rewritten to cite D8's architectural-commitment framing. `EMAIL_SEND_TO_OPERATOR_TOOL` import remains absent; `REVIEWER_PRIMITIVES` count remains 21.

4. **`api/agents/reviewer_agent.py`** — `_PERSONA_FRAME` section at lines 758–790 rewritten per D7 above.

5. **`api/test_adr299_kernel_universal_capability.py`** — every test renamed + assertion + docstring rewritten:
   - File NOT renamed (filename is a stable URL; the H1 title is canonical; reference path stays consistent with the 6 Hat-B evaluation citations).
   - Module docstring rewritten under the new framing.
   - `test_send_operator_email_in_capabilities_dict` → `test_send_operator_email_not_in_capabilities_dict` with **inverted assertion** — the new shape requires `"send_operator_email" not in CAPABILITIES`.
   - `test_email_tools_exposes_send_to_operator_with_constrained_schema` survives verbatim (the tool definition shape is unchanged).
   - `test_handler_refuses_llm_supplied_addressee_fields` survives verbatim (the handler shape is unchanged — D6).
   - `test_resolution_send_operator_email_not_in_provider_map` survives verbatim (the entry was never in `CAPABILITY_PROVIDER_MAP`).
   - `test_resolution_surfaces_send_operator_email_unconditionally` rewritten to assert surfacing happens via `SYSTEM_INFRASTRUCTURE_TOOLS` merge (not via always-surface over `CAPABILITIES`).
   - `test_reviewer_primitives_excludes_send_operator_email` (renamed from `_path_a_revert` suffix — the exclusion is no longer a revert, it's the architectural commitment per D8) — guards Reviewer surface exclusion.
   - `test_resolution_does_not_have_parallel_kernel_universal_precheck` → `test_resolution_uses_system_infrastructure_tools_merge` — the parallel-pre-check guard is reframed as a positive assertion that the merge path is the one resolution mechanism.
   - `test_bundle_capability_resolution_not_regressed` survives verbatim.
   - `test_addressee_class_distinguishes_operator_from_audience` rewritten under the new vocabulary — the operator/audience distinction is now expressed structurally (system infrastructure vs workspace capability), not via an `addressee_class` field that no longer exists.
   - New test: `test_runtime_kernel_sentinel_deleted_from_capabilities` — guards against the `runtime: "kernel"` value reappearing.

6. **`docs/programs/alpha-author/reference-workspace/context/_shared/_preferences.yaml`** — comment block at lines 41–73 rewritten per D4.

7. **`docs/programs/alpha-trader/reference-workspace/context/_shared/_preferences.yaml`** — comment block at lines 50–83 rewritten per D4.

8. **`api/test_reviewer_formalization.py`** — two docstring prose mentions at lines 231 + 272 updated to the new framing (no assertion changes; docstrings only).

9. **`api/prompts/CHANGELOG.md`** — new entry `[2026.05.27.N]` documenting the persona-frame rewrite per Prompt Change Protocol.

### What does NOT change

- The tool's wire (system Resend via `api/jobs/email.py::send_email`) — unchanged. Discovery 2's wire correction is structurally correct under the new framing.
- The tool's handler (`_handle_email_tool` `send_to_operator` branch at line ~2334) — unchanged. Early return + addressee resolution from `auth.users.email` + LLM-supplied addressee rejection all preserved.
- The tool's name (`platform_email_send_to_operator`) — unchanged. The `platform_*` prefix is now slightly imprecise (this is system infrastructure, not a platform integration), but renaming the tool would cascade across persona-frame + CHANGELOG history + Hat-B evaluation references for negligible benefit. The prefix is grandfathered in the same spirit as the `services/platform_tools.py` filename.
- `_preferences.yaml::operator_notifications:` schema shape — unchanged.
- ADR-040 + ADR-202 call sites — unchanged. They were already correct.
- Render service env vars — unchanged. `RESEND_API_KEY` + `RESEND_FROM_EMAIL` are already deployed for ADR-040 + ADR-202; this rewrite does not add any new env vars.
- Database schema — unchanged. No migration needed.

### Validation gate

`python api/test_adr299_kernel_universal_capability.py` — all 11 tests (10 surviving + 1 new) pass. Adjacent gates that must continue passing: `api/test_reviewer_formalization.py`, `api/test_adr276_reactive_envelope.py`, `api/test_adr301_reviewer_pulse_envelope.py`. No env-var change → no Render parity check needed.

## Stress-test against the rewrite

The framing was stress-tested by walking each `platform_connection_requirement: None` entry in `CAPABILITIES` and asking the D1 distinguishing question. Results:

| Entry | Category | Stays in CAPABILITIES? |
|---|---|---|
| `summarize`, `detect_change`, `alert`, `cross_reference`, `data_analysis`, `investigate`, `produce_markdown` | Cognitive descriptors — declarative metadata, no tool | **Yes.** Bundles declare cognitive shapes their work needs; team composition matches. |
| `web_search`, `read_workspace`, `search_knowledge` | Declarative pointers to LLM primitives (`WebSearch`, `ReadFile`, `QueryKnowledge`) — actual surfacing happens via `CHAT_PRIMITIVES`/`HEADLESS_PRIMITIVES`/`REVIEWER_PRIMITIVES` | **Yes.** Bundle/task declaration metadata, not load-bearing for runtime surfacing. (Flagged as a follow-up: these entries may be vestigial declarations worth simplifying, but the simplification is independent of this rewrite.) |
| `chart`, `mermaid`, `image`, `video_render` | Asset-production dispatches → `RuntimeDispatch` → yarnnn-render service | **Yes.** The yarnnn-render *service* is system infrastructure (Docker deployment); the *capability to dispatch chart-rendering for the workspace's deliverable* is workspace-shaped work. |
| `compose_html` | Post-generation pipeline step (ADR-213), no tool, automatic | **Yes** (but flagged as possibly vestigial — nothing dispatches to it as a tool; the entry may be inert metadata). Out of scope for this rewrite. |
| `send_operator_email` | System infrastructure: system speaks as itself to operator-identity via environment-shared Resend wire | **No.** Moves to `SYSTEM_INFRASTRUCTURE_TOOLS`. |

`send_operator_email` is the lone outlier. The taxonomy split is sharp and well-populated on the workspace-capability side; the system-infrastructure side has one entry today and a documented home for future entries.

The orthogonal precedent — ADR-040 notifications and ADR-202 daily-update emails — confirms the framing. Both use the same Resend wire, both fire from kernel code paths, neither is registered as a capability. ADR-299's contribution is naming the pattern explicitly and adding the first LLM-invokable surface to it.

## Reviewer authority — RESOLVED

The 2026-05-25 v5 canary ([RESOLUTION.md](../observations/2026-05-25-042346-adr299-always-surface-resolution/RESOLUTION.md)) confirmed hypothesis A (tool perturbation) and the architectural commitment is now load-bearing in D8 above: the Reviewer is permanently excluded from `SYSTEM_INFRASTRUCTURE_TOOLS` because the judgment-bearing surface is qualitatively more sensitive to tool-list size than task-bearing surfaces. This is not a deferred question; it is an evidence-confirmed structural design.

The 2026-05-27 first-pass rewrite of this ADR mistakenly preserved a pre-resolution "open question" framing — the v5 canary had already run and confirmed hypothesis A on 2026-05-25, but the rewrite carried forward the pre-resolution paragraph unchanged. That framing is now retired. The pre-existing exclusion of `EMAIL_SEND_TO_OPERATOR_TOOL` from `REVIEWER_PRIMITIVES` is the architectural commitment, not a pending experiment.

**Operator-addressing notifications tied to Reviewer verdicts**, when needed, belong on a post-judgment dispatcher hook that reads the verdict from substrate (`/workspace/review/judgment_log.md` + `/workspace/review/standing_intent.md`) and the operator's `_preferences.yaml::operator_notifications` block. The pattern already exists at `services/notifications.py` for `action_proposals` arrivals (ADR-040). Out of scope for this ADR but explicitly named as the correct integration path. The L6 capital-execution branch on alpha-author per the original [2026-05-22 motivating evaluation](../observations/2026-05-22-052244-l6-variant-f-clause-validation/) closes via this post-judgment hook design, not via Reviewer tool invocation.

**Discipline for future Reviewer surface changes** (per [RESOLUTION.md §"Discipline lesson"](../observations/2026-05-25-042346-adr299-always-surface-resolution/RESOLUTION.md)): structural reachability is not sufficient justification for tool inclusion. Verdict-quality regression must be measured against the baseline tool surface via N≥3 canaries before any addition is accepted. The default for Reviewer surface changes is "no" until verdict-quality evidence supports otherwise. The 21→22 transition's measured 74% output collapse is the canonical demonstration of why this discipline exists.

## Post-judgment dispatcher integration — DEFERRED

The architectural commitment in D8 + §"Reviewer authority — RESOLVED" names a **post-judgment dispatcher hook** as the correct integration path for operator-addressing notifications tied to Reviewer verdicts. Implementation of that hook is **deferred** as of 2026-05-27 pending a broader strategic discussion.

**Deferral rationale**. The ADR-299 design exercise produced two generalizable architectural lessons that extend beyond email:

1. **Two-class agent surface distinction** (D8) — task-bearing vs judgment-bearing agents have qualitatively different tolerances for tool-list size. Tool surfacing decisions for any new integration must respect this distinction, not just email.
2. **System infrastructure vs workspace capability** (D1) — environment-deployed kernel plumbing exposed as LLM tools is a distinct architectural class from bundle-declared workspace capabilities. The taxonomy applies to any new infrastructure exposure, not just email.

The natural next discussion these lessons inform is **the broader question of how the Reviewer's verdicts reach operators across multiple delivery channels** — email being one, but Notion / Slack workspace integrations being structurally similar (operator-addressing channels, environment-deployed wires, post-judgment delivery). Designing the email dispatcher in isolation would either (a) prematurely lock in a v1 design the broader discussion would supersede, or (b) require a v2 refactor that defeats Singular Implementation.

The deferral is not a gap in canon — D8 + §"Reviewer authority — RESOLVED" are the load-bearing architectural commitments and they stand without the dispatcher implementation. The L6 capital-execution branch on alpha-author per the original [2026-05-22 motivating evaluation](../observations/2026-05-22-052244-l6-variant-f-clause-validation/) closes whenever the broader operator-channel-integration discussion concludes and the dispatcher (or its multi-channel successor) ships.

**What stays out of scope under this deferral**:

- New module `services/reviewer_email_dispatch.py` or equivalent
- Match logic for `_preferences.yaml::operator_notifications` against Reviewer verdict events
- Per-channel fan-out beyond email (Notion, Slack, etc.)
- Composition templates for verdict-derived notification content
- Match-criteria schema extensions (e.g., per-entry `triggers_on:` field)

**What stays in scope and shipped under this ADR**:

- Workspace-capability vs system-infrastructure taxonomy (D1)
- `SYSTEM_INFRASTRUCTURE_TOOLS` registry + agent-path surfacing (D2, D3)
- Operator-identity addressee structural pin (D6)
- `_preferences.yaml::operator_notifications` schema in both bundles (D4) — opt-in shape is stable; the consumers can grow without schema churn
- Reviewer-side exclusion from `SYSTEM_INFRASTRUCTURE_TOOLS` (D8) — v5-canary-evidence-confirmed architectural commitment
- Future Reviewer surface change discipline (verdict-quality canary protocol)

When the broader operator-channel-integration discussion concludes, the dispatcher implementation lands as its own ADR (or as a substantive §"Implementation" addition to this ADR), referencing back to this deferral note. Until then, operator-addressing notifications tied to Reviewer verdicts are observable in substrate (`/workspace/review/judgment_log.md`, surfaced in the cockpit Stream archetype per ADR-198) and via the existing cockpit surfaces — out-of-band channel delivery is the deliberate gap.

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| `SYSTEM_INFRASTRUCTURE_TOOLS` becomes a dumping ground | Discipline rule (D2): LLM-invokable surfaces only; environment-shared infrastructure only; addressee/target determined outside workspace declaration. Direct call sites stay direct. New entries require ADR amendment. |
| Operator-addressing emails become noise, get marked-as-read, loop breaks | Default-off via `_preferences.yaml::operator_notifications.{slug}.active: false`. Operator opts in per workspace per notification class. No platform-default subscriptions. |
| Tool gets re-used as audience-bearing surface | Schema enforces structural pin (no `to`, `cc`, `bcc`, `from_email`, `from_name` fields accepted — D6). Handler rejects at runtime. Source-level test guards against schema drift. |
| Per-workspace operator-email duplication when operator runs multiple workspaces | Downstream product-design problem (digest roll-up, subject-line prefixing); capability ships unchanged; UX iteration handles spam-fatigue. |
| Bundle MANIFEST authors try to redeclare `send_operator_email` | The capability key no longer exists in `CAPABILITIES`; bundle MANIFEST validation will reject the unknown capability at activation time. Documentation steers bundle authors to declare only audience-bearing email capabilities (bundle-specific). |

## Cross-references

- **Existing system Resend wire call sites**: ADR-040 (`services/notifications.py`), ADR-202 (`services/daily_update_email.py`). Both fire from kernel code paths; both use `RESEND_API_KEY` env var; neither is registered as a capability. This rewrite makes the pattern they established explicit.
- **Resend integration ADR**: ADR-192 Phase 4 (`api/integrations/core/resend_client.py`) — the *per-user OAuth* audience-bearing wire, distinct from the system wire `send_operator_email` uses.
- **Capability flow**: ADR-269 (`get_platform_tools_for_agent`) — the agent-path resolution entry point that this rewrite touches.
- **AUTONOMY gating**: ADR-217 + ADR-249 — gates consequential actions (third-party-affecting); operator-self-addressing observability is structurally outside this gate per D5.
- **Bundle MANIFEST schema**: ADR-118, ADR-224 — bundle capabilities + kernel/program boundary discipline.
- **Operator preferences substrate**: ADR-275 — operator authority on `_preferences.yaml`; Reviewer reconciles cadence preferences via `Schedule()` but does not author the preferences.
- **Path A revert observation**: [`docs/evaluations/2026-05-25-042346-adr299-always-surface-resolution/`](../observations/2026-05-25-042346-adr299-always-surface-resolution/) — Hat-B finding that triggered the revert.
- **L6 capital-execution validation** (substrate-continuity branch on alpha-author): [`docs/evaluations/2026-05-22-052244-l6-variant-f-clause-validation/`](../observations/2026-05-22-052244-l6-variant-f-clause-validation/) — the discourse that originally motivated this ADR. Closure of the substrate-continuity branch is no longer gated on Reviewer tool invocation (per D8 + §"Reviewer authority — RESOLVED"); the correct integration path is the post-judgment dispatcher hook reading verdict substrate + operator preferences. Scope of that integration is out of scope for this ADR but the path is explicitly named.
- **alpha-author bundle**: ADR-283 D7 + Discovery Note 2 — audience-bearing email rejection holds; operator-addressing system infrastructure is a separate surface inheritable by every bundle without MANIFEST declaration.

## Implementation history (superseded)

The original ADR-299 (2026-05-22) framed `send_operator_email` as a "kernel-universal capability" — a new architectural class introduced alongside existing workspace capabilities. Four Discovery notes corrected layers of the resulting cascade:

- **Discovery note 1** (2026-05-24): Class-name redundancy. The "kernel-universal" name was reused without checking the existing `CAPABILITIES` dict structure; the genuine novelty was the addressee-class distinction (operator-identity vs audience), not the kernel-vs-bundle housing. Class renamed "operator-addressing." Parallel registry `KERNEL_UNIVERSAL_CAPABILITIES` deleted.
- **Discovery note 2** (2026-05-24): Wire redundancy. Phase 1 had wired the tool to the per-user OAuth Resend (ADR-192 Phase 4) when the correct wire (system Resend, ADR-040 + ADR-202) was already deployed. Wire rewired; `runtime: "kernel"` sentinel added to `CAPABILITIES` entry; `platform_connection_requirement: None`.
- **Discovery note 3** (2026-05-25): Resolution-path gap. The runtime never surfaced the capability to substrate-event wakes (which hardcode `capabilities=[]`). Always-surface pass added that looped over kernel `CAPABILITIES` filtering by `platform_connection_requirement is None`.
- **Discovery note 4** (2026-05-25): Reviewer-surface gap. The Reviewer's tool surface is `REVIEWER_PRIMITIVES`, not `get_platform_tools_for_capabilities`; the tool was never in `REVIEWER_PRIMITIVES`. Tool added. Path A revert followed same-day (next entry).
- **Discovery 4 Path A revert + v5 resolution** (2026-05-25): Canary v4 produced `stand_down` instead of `defer`/`reject`; hypothesis A (tool perturbation) chosen for isolation. `EMAIL_SEND_TO_OPERATOR_TOOL` removed from `REVIEWER_PRIMITIVES`. Discovery 3's always-surface fix kept. The same-day v5 canary on the 21-tool surface produced `reject_publication` with 14,615 output tokens — hypothesis A CONFIRMED (full evidence trail in [RESOLUTION.md](../observations/2026-05-25-042346-adr299-always-surface-resolution/RESOLUTION.md)). What was framed as a "revert pending validation" became the architectural commitment within the same day. The 2026-05-27 first-pass rewrite of this ADR carried forward the pre-resolution "open question" framing in error; the second-pass rewrite incorporates the v5 finding as D8.

The 2026-05-27 rewrite supersedes the entire "kernel-universal capability" framing and the parallel-registry-then-always-surface-pass implementation. The four Discovery notes' lessons fold into one structural insight: **the original ADR was correctly identifying that the entity didn't fit the existing capability layer, but it relocated within the capability layer instead of relocating out of it.** The correct relocation is to system infrastructure (a category that already existed implicitly via ADR-040 + ADR-202; this ADR names it).

What's preserved from the prior shape:
- D2 (tool wrap with structural addressee pin) → D6 in the rewrite.
- D3 (audience-vs-operator distinction) → still load-bearing; lives in §"Decision" framing.
- D4 (observability authorization model) → D5 in the rewrite.
- Discovery 2's wire choice (system Resend) → §"Decision" assumes this throughout.
- Discovery 4 Path A revert + 2026-05-25 v5 canary resolution → D8 (architectural commitment) + §"Reviewer authority — RESOLVED."

What's superseded:
- D1 (kernel-universal capability class) → DELETED. Workspace capabilities are a single-axis taxonomy; system infrastructure is a separate category.
- D5 (parallel registry, then in-place CAPABILITIES entry) → DELETED. Entry moves to `SYSTEM_INFRASTRUCTURE_TOOLS`.
- D6 (per-bundle vs kernel-universal placement argument) → DELETED. System infrastructure is not bundle-declared at all; the kernel-vs-bundle axis doesn't apply.
- D7 (scope limits) → folded into §"Risks + mitigations" + §"Decision" framing.
- Discovery 3's always-surface-over-CAPABILITIES pass → DELETED. Replaced by explicit `SYSTEM_INFRASTRUCTURE_TOOLS` merge.
- `runtime: "kernel"` sentinel value → DELETED. Was a code-level signal that the entry didn't fit; entry's correct home doesn't need a sentinel.

The Hat-B evaluation findings that referenced the prior shape are historical artifacts and remain accurate to their moment per the Two-Hats discipline. Their file paths to ADR-299 stay correct (the filename is the stable URL; the H1 title is the canonical name).

## Generalization landed in ADR-304

The taxonomy this ADR established (system infrastructure vs workspace capability + Reviewer judgment-bearing exclusion per D8) was generalized to two other operator-addressing writes on 2026-05-27 via [ADR-304](ADR-304-operator-addressing-writes-generalization.md). `platform_slack_send_message` (operator's own Slack DM) and `platform_notion_create_comment` (operator's designated Notion page) both pass the D1 distinguishing test — addressee structurally pinned to operator-identity — and reclassify from workspace capabilities (`write_slack` / `write_notion`) into `SYSTEM_INFRASTRUCTURE_TOOLS`. ADR-304 also closes the YARNNN-chat-vs-bundle-MANIFEST gap the audit surfaced (chat now honors bundle capability declarations the same way the headless path does). ADR-299 stays the canonical email-specific ADR + taxonomy framing source; ADR-304 generalizes the pattern. Future operator-addressing channel additions (push, SMS, etc.) follow the same shape per ADR-304 D5 + D6.
