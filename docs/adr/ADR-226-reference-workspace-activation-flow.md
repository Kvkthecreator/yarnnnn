# ADR-226: Reference-Workspace Activation Flow

> **Status:** **Phase 1 Implemented 2026-04-27. Phase 2 FE shipped via ADR-240 (2026-04-29) and reshaped into permanent surface via ADR-244 (2026-05-01).** Backend implementation shipped: `_fork_reference_workspace` + `_strip_tier_frontmatter` + `_is_skeleton_content` helpers in `workspace_init.py`; `_classify_activation_state` signal in `working_memory.py`; `ACTIVATION_OVERLAY` prompt in `yarnnn_prompts/activation.py` + `build_system_prompt(activation_active=...)` wiring; `GET /api/programs/activatable` + `POST /api/programs/activate` endpoints; 15/15 ADR-226 test gate passing (36/36 combined with ADR-224 + ADR-225). End-to-end smoke validated against kvk's real workspace: 8 files forked from alpha-trader bundle, frontmatter stripped, ADR-209 attribution captured (`authored_by="system:bundle-fork"` + tier-aware messages), idempotent re-fork (zero wasted revisions when content matches), operator-authored content preserved on re-run.
>
> **2026-05-01 amendment (ADR-244):** v3's deferred deactivation gap closed via `POST /api/programs/deactivate` (soft — drops MANDATE.md marker, body preserved per ADR-209). v3's "operator who skips at signup and connects platform later doesn't get fork" gap closed via the permanent `Settings → Workspace` surface — operators can activate or switch programs at any time, not only at signup. L2/L4 purges (`routes/account.py::clear_workspace` + `reset_account`) now preserve `active_program_slug` pre-purge and re-fork the bundle during reinit so the workspace reset doesn't silently drop program activation.
> **Date:** 2026-04-27
> **Authors:** KVK, Claude
> **Implements:** ADR-222 implementation roadmap, ADR 5a (the universal OS-level activation flow). ADR 5b — kvk's alpha-trader dogfooding bootstrap — is intentionally NOT this ADR; it is a separate workstream tracked at `docs/alpha/personas/alpha-trader/BOOTSTRAP.md`. See "Why this ADR is split from dogfooding" below.
> **Related:** ADR-222 (OS framing), ADR-223 (Program Bundle Specification — three-tier file categorization that this ADR's copy logic honors), ADR-224 (Kernel/Program Boundary), ADR-225 (Compositor Layer — bundle-supplied chrome the activated workspace inherits), ADR-205 (Workspace Primitive Collapse — minimum substrate at signup), ADR-206 (Operation-First Scaffolding — workspace materializes through user action), FOUNDATIONS Axiom 1 corollary (substrate grows from work, not from signup scaffolding) + Principle 16 (program selection is the implicit type)
> **Depended on by:** Reference-Reflexive Loop ADR (forthcoming, ADR 6 — graduation flows back through the same reference structure this ADR consumes)
> **Supersedes (in part):** none structurally; extends `workspace_init.initialize_workspace`

---

## Why this ADR is split from dogfooding

A discourse pass clarified that two activation flows had been bundled together as "ADR 5":

**Flow A — OS-level activation flow** (this ADR, **ADR 5a / ADR-226**):
- Universal. Runs for every operator of every program at signup.
- Operator selects a program; `workspace_init` reads the program's `reference-workspace/`; copies tier-categorized files into operator's `/workspace/`; YARNNN runs a differential-authoring conversation walking through `authored` tier files.
- Independent of which operator. Independent of which program (works for alpha-trader today, alpha-prediction or alpha-defi when activated).

**Flow B — kvk's alpha-trader dogfooding bootstrap** (NOT this ADR — `docs/alpha/personas/alpha-trader/BOOTSTRAP.md` runbook):
- Persona-layer. Specific to kvk's existing workspace + alpaca paper account.
- Authoring kvk's real `_operator_profile.md`, `_risk.md`, `principles.md`. Wiring alpaca paper trades. Validating the loop closes end-to-end.
- This is dogfooding work to validate the framework; it is not OS-architecture work.

Bundling them into one ADR risks designing OS-level infrastructure for kvk-specific reality, accidentally fitting the OS to one operator. The split keeps each concern principled. **Anything kvk's dogfooding surfaces that the OS *actually* needs becomes its own ADR, justified by demand, not bundled into ADR-226.** Same discipline that produced the v1→v2→v3 corrections on ADR-224 and ADR-225.

---

## Context

ADR-223 specifies `reference-workspace/` as a bundled-starter-substrate directory with three-tier file categorization (`canon` / `authored` / `placeholder` per the 2026-04-27 amendment). ADR-225 ships the compositor that renders bundle-supplied chrome into the cockpit. **What's missing**: the flow that takes a fresh signup, asks the operator which program they're running, and forks the reference workspace into their `/workspace/`.

Today (post-ADR-205 + ADR-206), `workspace_init.initialize_workspace(client, user_id, browser_tz)` scaffolds:
- One YARNNN agent row (role=`thinking_partner`, origin=`system_bootstrap`).
- Shared context skeletons (`/workspace/context/_shared/IDENTITY.md`, `BRAND.md`, `CONVENTIONS.md`) — kernel defaults, not program-shaped.
- YARNNN memory skeletons (`/workspace/memory/awareness.md`, etc.).
- Reviewer substrate stub at `/workspace/review/`.
- Signup balance audit trail (ADR-172).

These are **kernel-universal** scaffolds — they run for every workspace regardless of program. Per ADR-205 + ADR-206, the workspace is "textually present + structurally empty" after init. This stays correct.

What ADR-226 adds: **an optional program-selection layer** on top. When the operator picks a program (today: only alpha-trader; degenerate but real), the kernel-universal scaffolding still runs, then the bundle's `reference-workspace/` is forked into `/workspace/` honoring the three-tier categorization, then YARNNN's differential-authoring conversation walks the `authored` tier files.

Operators who skip the program selection (or are signing up before any program activates) get the kernel-universal-only flow that ADR-205/206 already ships. **This ADR does NOT change the no-program flow.** It adds the with-program flow as a strict superset.

### What "activation" means precisely

> An operator's workspace is **activated for a program** when (a) the bundle's reference-workspace files have been forked into `/workspace/`, (b) the bundle's required platform_connections are connected (per ADR-224 §3 capability-implicit activation, what makes the compositor surface bundle chrome), and (c) at minimum the `authored` tier MANDATE.md is non-skeleton.

(a) is the substrate fork (this ADR). (b) is platform connection (existing OAuth flows, no change). (c) is the operator authoring through YARNNN (this ADR's prompt overlay).

A workspace can be in any combination of these states. `(a) ∧ ¬(b)` = forked but compositor renders generic kernel chrome (no bundle is *active* per ADR-224 §3 because no platform is connected). `(a) ∧ (b) ∧ ¬(c)` = bundle is active, compositor renders bundle chrome, but the operator hasn't authored their edge — empty Performance band, MANDATE.md still has skeleton. `(a) ∧ (b) ∧ (c)` = fully activated; the loop runs.

This ADR ships infrastructure for (a) + (c). (b) is unchanged.

---

## Decision

### 1. Single user selection at signup: program (optional)

Per Axiom 1 corollary + Principle 16: the operator's choice is *which program*. Everything else flows from that.

Mechanism:
- Existing `/api/onboarding` flow (or signup post-step) gains an optional `program_slug` step.
- The selection UI lists active bundles (`MANIFEST.yaml.status === 'active'`). With one active program today (alpha-trader), the UI is a single-card selection plus a "skip — generic workspace" option.
- When alpha-prediction or alpha-defi activate, the UI surfaces all active programs with their oracle profile + capital threshold. Operator picks one.
- No selection = no program activation. Operator's workspace is generic per ADR-205/206 — they can author manually or activate later by connecting a platform that matches a bundle's `requires_connection`.

Critical: **program selection is an annotation, not a precondition.** A workspace without a program selection is fully legitimate — it just won't get bundle-shaped chrome until something triggers activation (platform connection, explicit later selection, etc.).

### 2. `workspace_init` extension — `initialize_workspace(client, user_id, browser_tz, program_slug=None)`

Single entry point. New optional parameter. Atomic execution.

```python
# api/services/workspace_init.py — extension sketch

async def initialize_workspace(
    client: Any,
    user_id: str,
    browser_tz: str | None = None,
    program_slug: str | None = None,  # NEW per ADR-226
) -> dict:
    # Phase 1-3: kernel-universal scaffolding (UNCHANGED per ADR-205/206)
    await _scaffold_yarnnn_agent_row(client, user_id, browser_tz)
    await _scaffold_kernel_universal_substrate(client, user_id)  # IDENTITY.md skeleton, etc.
    await _scaffold_signup_balance(client, user_id)

    # Phase 4 (NEW per ADR-226): program activation, optional
    if program_slug:
        await _fork_reference_workspace(client, user_id, program_slug)

    return {"user_id": user_id, "activated_program": program_slug, ...}


async def _fork_reference_workspace(client, user_id: str, program_slug: str) -> None:
    """Per ADR-226: copy bundle's reference-workspace/ into operator's
    /workspace/, honoring three-tier file categorization (ADR-223 §5):
    - canon files: copied verbatim, frontmatter stripped
    - authored files: copied with skeleton + prompt scaffolding,
      frontmatter stripped from operator-visible content but tier+prompt
      preserved internally for the differential-authoring conversation
    - placeholder files: copied empty/skeleton, frontmatter stripped

    All copies go through services.authored_substrate.write_revision per
    ADR-209, with authored_by="system:bundle-fork" + message identifying
    the source bundle + reference-workspace path.

    Files-not-in-reference do NOT get scaffolded. The reference is
    authoritative for what the workspace starts with.
    """
    from services.bundle_reader import _load_manifest
    manifest = _load_manifest(program_slug)
    if not manifest or manifest.get("status") not in ("active", "deferred"):
        # Defensive — UI should not allow non-activatable selection,
        # but if it slips through, fail closed.
        raise ValueError(f"Bundle '{program_slug}' is not activatable.")

    bundle_root = _BUNDLE_ROOT / program_slug / "reference-workspace"
    if not bundle_root.is_dir():
        return  # Bundle has no reference-workspace (deferred bundle minimum case)

    for src_path in bundle_root.rglob("*.md"):
        if src_path.name == "README.md" and src_path.parent == bundle_root:
            continue  # bundle-meta, not a workspace file
        relative = src_path.relative_to(bundle_root)
        target_path = f"/workspace/{relative}".replace("\\", "/")
        tier, body = _strip_tier_frontmatter(src_path.read_text())
        await write_revision(
            client=client,
            user_id=user_id,
            path=target_path,
            content=body,
            authored_by="system:bundle-fork",
            message=f"Forked from {program_slug} reference-workspace tier={tier}",
        )
```

The fork is **idempotent for canon tier** (re-running activation re-copies canon — operator's canon edits are revision-tracked, can be reverted) and **non-destructive for authored tier** (re-running activation does NOT overwrite operator-authored content; only re-applies if operator's file is still skeleton). Implementation detail of `_fork_reference_workspace` to be settled in code — the spec discipline is "activation is safe to re-run."

### 3. YARNNN differential-authoring conversation

After fork, YARNNN engages the operator in a structured walk through `authored` tier files. This is the conversation Phase that gets the operator from "structurally complete workspace" to "operationally activated workspace."

Mechanism:
- New YARNNN prompt overlay: `api/agents/yarnnn_prompts/activation.py` (or extension to existing `onboarding.py`).
- Activated when `workspace_init` returns `activated_program=<slug>` AND `/workspace/context/_shared/MANDATE.md` is still skeleton (placeholder content unchanged from bundle).
- The overlay is **profile-aware** per ADR-186: applies to the `workspace` profile when the operator first lands on `/chat`.
- Conversation shape: *"Welcome to {program.title}. Your workspace is now structured for {program.tagline}. Before we run the loop, let's author the parts that are yours — your edge, your principles, your delegation ceiling. I'll walk you through them one at a time."*
- Walks `authored` tier files in declared order: MANDATE → IDENTITY → principles.md → (others as the bundle declares). Each file's `prompt:` frontmatter field becomes the YARNNN question.
- Operator's responses route through existing `UpdateContext` primitive — no new primitive. YARNNN authors on the operator's behalf via the standard path; operator approves or edits inline.
- Conversation exits when all required `authored` files are non-skeleton. YARNNN signals "your workspace is activated" and the cockpit shifts from onboarding mode to operating mode.

The conversation is NOT mandatory. Operators who close the chat or skip can come back; the overlay re-engages when YARNNN sees skeleton MANDATE.md on next session start. **Singular Implementation**: there is exactly one path that authors `authored` tier files — UpdateContext. Activation does not introduce a parallel write path.

### 4. Three-tier copy discipline (per ADR-223 §5)

| Tier | What `_fork_reference_workspace` does | What YARNNN's overlay does | Re-run safety |
|---|---|---|---|
| **`canon`** | Copy verbatim (frontmatter stripped). `authored_by="system:bundle-fork"`. | Does not prompt. Operator may overwrite later via UpdateContext like any other file. | Re-running fork re-applies canon (operator's edits preserved as prior revisions per ADR-209). |
| **`authored`** | Copy with skeleton + prompt scaffolding (frontmatter stripped). `authored_by="system:bundle-fork"`. | Walks operator through filling in (MANDATE first, then IDENTITY, principles, etc.). Each file's `prompt:` frontmatter drives the question. | Re-running fork checks if operator file is still skeleton; only re-applies if yes. Non-destructive of operator content. |
| **`placeholder`** | Copy empty/skeleton (frontmatter stripped). `authored_by="system:bundle-fork"`. | Does not prompt. Substrate accumulates from work over time. | Re-running fork does not touch operator-modified placeholder files. |

The activation flow's correctness depends on tier metadata being honest in the bundle. ADR-223's amendment makes the tier a per-file frontmatter field; this ADR is its consumer.

### 5. Cockpit transition: onboarding → operating

After activation, the cockpit shifts presentation:

- **Pre-activation** (no program selected, or fresh signup pre-fork): kernel-universal cockpit. No bundle banner, no pinned tasks, generic empty states.
- **Post-fork-pre-author** `(a) ∧ ¬(c)`: cockpit shows bundle chrome (via compositor) but operator surfaces show "Author your MANDATE.md to begin" pointer. The Performance band shows "No trades yet — author your edge hypothesis to start."
- **Post-author-pre-platform** `(a) ∧ (c) ∧ ¬(b)`: workspace is operationally authored but platform isn't connected. Cockpit prompts platform connection. (For alpha-trader: alpaca.)
- **Fully activated** `(a) ∧ (b) ∧ (c)`: bundle chrome renders against operator content. The compositor's `current_phase` overlay applies (alpha-trader observation phase shows "Paper-only..." banner). The loop runs.

These states are *not* explicit modes in code. They emerge from the substrate state (does MANDATE.md have skeleton content? is alpaca in `platform_connections`?). The cockpit reads substrate; substrate state determines what surfaces show. **No state machine, no activation_status column on workspaces.**

### 6. Re-activation — no separate path

What if an operator activated alpha-trader at signup, then later decides they're actually running alpha-prediction (when it activates)? Or what if the bundle ships v2 of its reference-workspace and an operator's lived workspace is on v1?

This ADR's answer: **no special re-activation flow.** Operator authors over time per Axiom 1 corollary. Bundle versioning + lived-workspace evolution is ADR 6 (Reflexive Loop) territory, not ADR 5a's. If an operator wants to "switch programs," they connect the new program's platform; the compositor's `bundles_active_for_workspace()` per ADR-224 surfaces the new bundle's chrome; the operator authors the new program's `authored` tier files via YARNNN as they would have at signup. Same path, just later. The fork can be re-run idempotently per §4.

### 7. What this ADR explicitly does NOT do

- **Does not introduce program-switching mid-stream.** Operators run programs; if they want to change, they author over time via the same primitive paths.
- **Does not pre-create tasks at activation.** Per ADR-205/206 + Axiom 1 corollary, tasks materialize from work. The reference-workspace ships zero `tasks/` content for a reason.
- **Does not pre-create user-authored agents.** Per ADR-205, signup scaffolds exactly one agent (YARNNN). Operator-authored agents materialize through chat post-activation.
- **Does not address kvk's existing-workspace bootstrap** — see `docs/alpha/personas/alpha-trader/BOOTSTRAP.md` (the dogfooding runbook).
- **Does not address bundle versioning** — when a bundle ships v2, operators on v1 are not auto-migrated. Deferred to ADR 6 + a future bundle-version-management ADR.
- **Does not address multi-program operators** — operator running both alpha-trader and alpha-commerce. Defer until alpha-commerce activates and the second-program scenario actually exists.

---

## Implementation plan (after ratification)

Atomic single PR per the migration discipline. Three reviewable steps.

### Step 1 — `workspace_init` extension + tier-aware fork

- `api/services/workspace_init.py` extended: `initialize_workspace` gains optional `program_slug` parameter.
- New helper `_fork_reference_workspace(client, user_id, program_slug)` reads bundle's `reference-workspace/` files, strips tier frontmatter, writes to operator's `/workspace/` via existing `services.authored_substrate.write_revision` with `authored_by="system:bundle-fork"`.
- New helper `_strip_tier_frontmatter(text)` — small parser, removes the `tier:` + `prompt:` + `note:` + `optional:` fields the bundle uses.
- Idempotency: re-running fork checks if operator's file is skeleton (matches bundle's body) or authored (differs); preserves authored content per ADR-209 revision chain.
- Unit tests for tier parsing + idempotency + write attribution.

### Step 2 — YARNNN activation prompt overlay

- New file `api/agents/yarnnn_prompts/activation.py` (or extension to `onboarding.py`) with the differential-authoring conversation pattern.
- Activation: applied when `_get_workspace_state()` shows `activated_program` set + MANDATE.md is skeleton.
- Walks `authored` tier files in bundle-declared order. Each file's `prompt:` becomes the YARNNN question; operator's response routes through `UpdateContext`.
- Conversation exits when all required-and-non-optional `authored` files are non-skeleton.
- `api/prompts/CHANGELOG.md` entry per the prompt-change protocol.

### Step 3 — Onboarding UI for program selection

- Existing onboarding flow (or post-signup welcome step) gains optional program-selection card.
- UI lists `MANIFEST.yaml.status === 'active'` bundles via a new (or extended) endpoint — likely reuses `/api/programs/surfaces` or a sibling `/api/programs/activatable` returning bundle metadata only.
- Operator picks one or skips. Selection threads to `initialize_workspace(program_slug=...)`.

### Step 4 — Documentation sync

- ADR-205 amended-by note (signup gains optional program activation; kernel-universal flow unchanged).
- ADR-206 amended-by note (activation Phase 4 added on top of Phases 1-3).
- ADR-223 cross-link (the three-tier categorization this ADR consumes).
- ADR-225 cross-link (compositor reads activated bundle's surfaces; bundle activation triggers chrome render).
- `docs/architecture/SERVICE-MODEL.md` Frame 5: activation flow row → Implemented.
- Roadmap → ADR 5 reframed as ADR 5a (this ADR) + 5b (kvk dogfooding); 5a marked Implemented.
- CLAUDE.md ADR-registry entry.
- New `docs/alpha/personas/alpha-trader/BOOTSTRAP.md` (per the split — separate workstream).

All four steps in one PR.

---

## Test coverage

```python
# api/test_adr226_activation.py

def test_initialize_workspace_no_program_runs_kernel_universal_only():
    """Per ADR-205/206 + ADR-226: workspace_init without program_slug
    does NOT fork any reference-workspace. Generic workspace per existing
    behavior."""
    # ... mock client, call initialize_workspace(client, user_id) with no program_slug
    # assert /workspace/context/_shared/MANDATE.md is skeleton (kernel default)
    # assert no /workspace/context/_shared/AUTONOMY.md (alpha-trader's canon file)


def test_initialize_workspace_with_alpha_trader_forks_reference():
    """Per ADR-226: workspace_init with program_slug='alpha-trader' forks
    the bundle's reference-workspace into /workspace/."""
    # ... mock, call initialize_workspace(client, user_id, program_slug='alpha-trader')
    # assert /workspace/context/_shared/MANDATE.md contains the bundle's authored
    # template body (skeleton + prompt scaffolding)
    # assert /workspace/context/_shared/AUTONOMY.md exists (canon tier)
    # assert /workspace/review/IDENTITY.md exists (canon tier)


def test_fork_strips_tier_frontmatter_from_operator_visible_content():
    """Per ADR-223 §5 + ADR-226 §4: tier frontmatter is bundle-only.
    Operator's /workspace/ files do NOT contain tier:/prompt:/note: keys."""
    # ... after fork, read /workspace/context/_shared/MANDATE.md content
    # assert "tier: authored" NOT in content
    # assert "prompt:" NOT in first 100 chars (bundle-only metadata stripped)


def test_fork_attributes_writes_to_system_bundle_fork():
    """Per ADR-226 §2: fork writes go through write_revision with
    authored_by='system:bundle-fork'. ADR-209 revision chain captures
    the activation event."""
    # ... after fork, query workspace_file_versions for /workspace/context/_shared/MANDATE.md
    # assert latest revision's authored_by == 'system:bundle-fork'
    # assert message references program_slug


def test_fork_is_idempotent_for_canon_tier():
    """Per ADR-226 §4: re-running fork re-applies canon files. Operator
    edits preserved as prior revisions in the chain (ADR-209)."""
    # ... fork once, operator edits CONVENTIONS.md, fork again
    # assert /workspace/context/_shared/CONVENTIONS.md content matches bundle (re-applied)
    # assert revision chain has both operator-edit + re-fork as separate revisions


def test_fork_preserves_operator_authored_content():
    """Per ADR-226 §4: re-running fork does NOT overwrite authored tier
    files that the operator has filled in."""
    # ... fork once, operator authors MANDATE.md with real content via UpdateContext, fork again
    # assert MANDATE.md still contains operator's authored content


def test_inactive_or_missing_bundle_fails_closed():
    """Per ADR-226 §2: fork rejects bundles that don't exist or have
    status != active|deferred."""
    # ... call initialize_workspace(program_slug='nonexistent') — should raise
    # assert ValueError raised
```

---

## Consequences

### Positive

- **Empty-state-as-onboarding largely solved.** Operator's `/workspace/` is structurally complete from minute one. The remaining empty states ("no trades yet") are honest and meaningful, not infrastructural.
- **Adding a program is purely additive (activation side, too).** alpha-prediction activation = its bundle becomes activatable in the program-selection UI; nothing else in workspace_init or YARNNN prompts changes. Same boundary ADR-224 enforced at the data layer + ADR-225 enforced at the dispatch layer, now extended to activation.
- **Universal flow.** Same activation path serves kvk, future alpha-trader operators, and alpha-prediction-when-activated operators. No program-specific code in `workspace_init.py`.
- **Cockpit operating-mode shift is substrate-driven.** No state-machine, no `activation_status` column. Cockpit reads substrate; substrate state determines what shows.
- **Singular Implementation honored.** Activation introduces zero parallel paths. Forking writes through `write_revision` (existing). Operator authoring routes through `UpdateContext` (existing). YARNNN prompt is a new content file but lives in the existing `yarnnn_prompts/` tree.
- **Re-activation is the same path, run later.** No separate "switch program" flow. Same primitives, same fork, same conversation; only the trigger timing differs.

### Negative / costs

- **Real engineering scope.** New `_fork_reference_workspace` helper, new `_strip_tier_frontmatter` parser, YARNNN activation prompt content (likely ~200-400 lines), onboarding UI for program selection. Sized in days, not hours.
- **Onboarding UI is net new surface.** Today no signup-time program-selection step exists. Building it requires layout + interaction + state plumbing. Manageable but real.
- **YARNNN prompt is a versioned artifact.** New prompt content goes through the prompt-change protocol (CHANGELOG.md entry, behavior expectations, version comment).
- **Tier frontmatter stripping needs to be precise.** Mistakes here leak bundle metadata into operator's workspace (visible in /context file viewer). Test coverage is the safeguard.

### Risks

- **YARNNN activation prompt drift.** New prompt content is a behavioral surface; over time it accretes opinions. Mitigation: same prompt-change protocol as ADR-186 prompt profiles; CHANGELOG.md entries on every change.
- **Operators who skip program selection then connect a platform later.** Today they get a generic workspace with bundle chrome (via ADR-225 compositor, since `bundles_active_for_workspace` resolves bundle on platform connection). They do NOT get the reference-workspace fork — they only get the cockpit chrome. Mitigation: future ADR can address "post-hoc activation" if pressure surfaces; for now, the gap is honest (operator made their choice at signup).
- **Bundle re-fork on a re-run.** `_fork_reference_workspace` running idempotently on canon tier means operator's canon edits get a "re-fork" revision in the chain. ADR-209 captures this; could be surprising to operators who thought their CONVENTIONS.md edit was sticky. Mitigation: documented behavior, revision history is visible, operator can revert. Real edge case but small.
- **Tier metadata correctness depends on bundle authors.** A bundle author who declares MANDATE as `tier: canon` (instead of `authored`) breaks the operator's authoring flow. Mitigation: ADR-223 amendment + bundle-validation script (forthcoming) catches obvious tier mistakes.

---

## Open questions

Explicitly deferred — none gate ratification.

- **Skip-then-activate-later UX.** Operator skips program selection at signup, connects alpaca three days later. Today (with this ADR shipped), bundle chrome appears via compositor but reference-workspace is NOT forked. Should there be an explicit "activate alpha-trader for this workspace" affordance? Defer until evidence the gap matters.
- **Bundle v2 migration.** When alpha-trader's reference-workspace ships v2, operators on v1 don't auto-migrate. Deferred to a future bundle-version-management ADR.
- **Activation completion criteria.** §3 says "MANDATE.md is non-skeleton" suffices to exit the conversation. Should it require all `authored` tier files? IDENTITY.md is genuinely optional for some operators. Per-file `optional: true` frontmatter (already shown in BRAND.md template) handles this — the conversation skips optional files. Concrete edge cases settled at implementation time.
- **Multi-program operator.** Defer per "What this ADR explicitly does NOT do."

---

## Decision

**Adopt the universal reference-workspace activation flow as defined above.** `workspace_init.initialize_workspace` extends with optional `program_slug` parameter; when present, forks the bundle's reference-workspace honoring three-tier categorization (ADR-223 §5); writes go through `write_revision` with `authored_by="system:bundle-fork"`; YARNNN runs a differential-authoring conversation walking through `authored` tier files in declared order, surfacing each file's `prompt:` as the question; operator responses route through `UpdateContext` (existing primitive). Cockpit operating-mode shifts are substrate-driven (no state machine). Re-activation is the same path, run later. The kvk-specific dogfooding workstream is intentionally NOT in scope here — it lives at `docs/alpha/personas/alpha-trader/BOOTSTRAP.md`.
