# ADR-224: Kernel / Program Boundary — Template Residue Deletion

> **Status:** Proposed (spec only — code work follows after ratification)
> **Date:** 2026-04-27 (v3 same-day rewrite — see "What changed across versions" below)
> **Authors:** KVK, Claude
> **Implements:** ADR-222 implementation roadmap, ADR 4
> **Related:** ADR-222 (OS framing), ADR-223 (Program Bundle Specification), ADR-188 (registries as templates), ADR-207 (TASK.md as dispatch authority), ADR-152 (Unified Directory Registry), ADR-187 (Trading), ADR-183 (Commerce), FOUNDATIONS Principle 10 (registries are template libraries) + Axiom 1 corollary (substrate grows from work)
> **Supersedes (in part):** none — refines ADR-188's commitment by enforcing it in code
> **Depended on by:** Compositor Layer ADR (forthcoming, ADR 2 — independently reads SURFACES.yaml), Reference-Workspace Activation Flow ADR (forthcoming, ADR 5 — reads bundles for fork-the-reference)

---

## Context

### The substrate-vs-program agnosticism distinction

The architecture's load-bearing distinction, sharpened during this ADR's drafting:

| Layer | Agnosticism | Why |
|---|---|---|
| **Substrate (filesystem, runtime)** | **Fully agnostic.** Materializes from work, not declarations. TASK.md / `_domain.md` / files are the dispatch authority. | Per Axiom 1 + corollary, ADR-188, ADR-207. Pipeline reads what's there; doesn't ask the kernel "is this directory legal." |
| **Program (bundle, declarative)** | **NOT agnostic.** Specific by construction. alpha-trader is *opinionated* about trading-signal / trading directory / read_trading capability. | Per ADR-222 + ADR-223. A program is the opposite of agnostic — it's a curated commitment to a specific operator workflow. |

The kernel shouldn't be agnostic about programs in general (it must know how to host them, render them, scaffold them). But the kernel's *runtime dispatch path* must be agnostic about *which specific program* a workspace is running — `task_pipeline.py` should not branch on `if alpha-trader`. Same for `working_memory.py`, `agent_pipeline.py`, every other dispatch-shaped service.

### Where the boundary problem lives — three specific moments, not "always"

A grep audit (recorded here as fact base) shows where program-shaped templates are *actually consulted* in code today:

**`task_types.TASK_TYPES`** read sites (5):
- `manage_task._handle_create` — type_key convenience expansion when operator/YARNNN passes a shortcut.
- `agent_creation.ensure_infrastructure_agent` — first-task scaffolding for newly-created agents.
- `workspace_init.py` — back-office task scaffolding at signup (back-office is kernel-universal — no bundle read needed here).
- `compose/assembly.py` — `## Page Structure` fallback when TASK.md doesn't declare it.
- `chat.py:966-968` — YARNNN tool handler looks up a type_key when composing tasks.

**`directory_registry.WORKSPACE_DIRECTORIES`** read sites (~6):
- `working_memory.py:473` — discovers actual directories from substrate (`workspace_files` table), then attaches *display metadata* (`temporal` flag) from the registry. **The registry is referential here, not authoritative.** Per the docstring: *"appear automatically as soon as they contain files. No registry update required."*
- `feedback_actuation.py:248,317` — domain_path resolution for actuation rules.
- `integrations.py:2137,2441` — `scaffold_context_domain` at platform connect time.
- Path utility helpers (`get_domain`, `get_domain_folder`, etc.) used in `task_pipeline.py` when reading task-declared domain refs.

**`orchestration.CAPABILITIES`** read sites (1):
- `task_derivation.py:123` — derivation report computation when MANDATE/task changes (per ADR-207 P5).

**`platform_tools.{SLACK,NOTION,GITHUB,COMMERCE,TRADING,EMAIL}_TOOLS`** — read at task execution to assemble tool surface, but tool *definitions* themselves are kernel-shaped code (Anthropic JSON schemas + Python handlers). What gets selected per task is determined by TASK.md `**Required Capabilities:**` — capability gate per ADR-207 P3 — not by the registries.

### What this audit reveals

**No site reads these registries to make a runtime dispatch decision.** Every read is one of:

- **Composition moment** — operator/YARNNN composes a task; consults templates as guidance.
- **Scaffolding moment** — first-write to a directory, first-task for an agent, signup back-office population.
- **Display-metadata moment** — `working_memory` attaches a temporal flag for rendering.
- **Derivation moment** — `task_derivation.py` computes a report.

These are all **specific, contextual, infrequent reads** — not "always-loaded into the dispatch path." This matches what real OSes do: macOS doesn't pre-load Photoshop into the kernel; Photoshop's `.app` bundle is consulted by Launch Services when the user double-clicks the icon, by the dock when displaying it, by the window server at window creation. Three specific moments, not always-merged-into-the-kernel.

### What v1 and v2 got wrong

This ADR took two prior shapes within the same day:

- **v1** assumed registries were dispatch-authoritative; proposed a heavy `program_registry.py` service with `WorkspaceProgramView` union semantics, ~50 call sites threaded with `workspace_id`. Operator caught it (ADR-188 + Axiom 1 corollary contradict the dispatch-authority assumption).
- **v2** corrected the dispatch-authority claim but still proposed a centralized `program_bundles.py` loader with `lru_cache` and merged-view helpers consumed at ~15 sites — a runtime-loaded "merged view" that the audit shows isn't needed. Operator caught it again (the substrate is runtime; the program is declarative; runtime dispatch doesn't need to know about programs).

**v3 (this version)** drops both errors. There is no merged view to compute at runtime. Bundles are read at the specific composition/scaffolding/display moments listed above, by callers that already have workspace context. Each caller reads what it needs, where it needs it. No central loader, no merged-view abstraction, no `workspace_id` plumbing through the runtime path.

The lesson, recorded for future reviews: when an OS metaphor pulls the design toward "always-loaded kernel module" shape, check whether real OSes actually do that. They don't. They consult bundle files at specific moments and the kernel itself stays bundle-agnostic.

---

## Decision

### 1. Boundary classification — what stays, what gets deleted from kernel

Same classification as v2; the *what to delete* answer was already correct. Only the *how to enable bundle reads* answer changes (much smaller in v3).

#### `api/services/task_types.py`

**Stays** (21 entries — kernel-universal templates):

- Back-office (7): `back-office-agent-hygiene`, `back-office-workspace-cleanup`, `back-office-proposal-cleanup`, `back-office-outcome-reconciliation`, `back-office-reviewer-reflection`, `back-office-narrative-digest`, `back-office-reviewer-calibration`.
- Universal anchor (1): `daily-update`.
- Generic knowledge-work (13): `track-competitors`, `track-market`, `track-relationships`, `track-projects`, `research-topics`, `competitive-brief`, `market-report`, `meeting-prep`, `stakeholder-update`, `project-status`, `content-brief`, `launch-material`, `maintain-overview`.

**Deletes** (3 entries — already canonical in bundles):

- `revenue-report` → `docs/programs/alpha-commerce/MANIFEST.yaml` (bundle created `status: deferred` to host it).
- `trading-signal` → `docs/programs/alpha-trader/MANIFEST.yaml` (already declared per ADR-223 alignment).
- `portfolio-review` → `docs/programs/alpha-trader/MANIFEST.yaml`.

#### `api/services/directory_registry.py`

**Stays** (8 entries):

- Universal substrate (2): `uploads`, `_shared`.
- Generic knowledge-work domains (6): `competitors`, `market`, `relationships`, `projects`, `content_research`, `signals`.
- Capability-bundle-owned (3, kept): `slack`, `notion`, `github`. Platform-bot-owned per ADR-158 (`temporal: true`); not program-shaped — any program operator with Slack connected has `/workspace/context/slack/`.

**Deletes** (4 entries — already canonical in bundles):

- `customers`, `revenue` → alpha-commerce (deferred bundle).
- `trading`, `portfolio` → alpha-trader (already declared per ADR-223).

#### `api/services/orchestration.py` `CAPABILITIES`

**Stays** (15 entries — universal cognitive capabilities):

- Reasoning verbs (10): `summarize`, `detect_change`, `alert`, `cross_reference`, `data_analysis`, `investigate`, `produce_markdown`, `web_search`, `read_workspace`, `search_knowledge`.
- Asset/render (5): `chart`, `mermaid`, `image`, `video_render`, `compose_html`.

**Deletes** (9 entries — already canonical in bundle MANIFESTs):

- Platform-connection-bound: `read_slack`, `write_slack`, `read_notion`, `write_notion`, `read_github`, `read_commerce`, `write_commerce`, `read_trading`, `write_trading`.

#### `api/services/platform_tools.py`

**No deletion.** Tool definitions (Anthropic JSON schemas + Python handlers) are kernel-shaped *code*. What's program-specific is *tool availability per program*, declared by the bundle's `capabilities[].requires_connection`. ADR-207 P3 already gates tool surface assembly by capability; this file is unchanged.

### 2. How bundles get read — point-of-use, not centralized

No central `program_registry.py` service. No `program_bundles.py` runtime loader. No merged-view abstraction. Just point-of-use bundle reads at the specific moments where a caller actually needs program-shaped data:

#### A small bundle-reader utility

Single helper module: `api/services/bundle_reader.py` (~30 lines, not 80):

```python
# api/services/bundle_reader.py
# Minimal helper for the few callers that need to read program bundles.
# Lazy file-read with lru_cache. Not a centralized "program runtime."

from pathlib import Path
import yaml
from functools import lru_cache

BUNDLE_ROOT = Path("docs/programs")

@lru_cache(maxsize=32)
def load_manifest(slug: str) -> dict | None:
    """Cached read of docs/programs/{slug}/MANIFEST.yaml. Returns None if absent."""
    path = BUNDLE_ROOT / slug / "MANIFEST.yaml"
    if not path.exists():
        return None
    with path.open() as f:
        return yaml.safe_load(f)


def all_active_bundles() -> list[dict]:
    """Bundles with status='active'. Used by composition-moment callers
    (manage_task type_key lookup, task_derivation report) to discover
    program-shaped templates available to YARNNN's composition reasoning."""
    bundles = []
    for entry in BUNDLE_ROOT.iterdir():
        if not entry.is_dir():
            continue
        m = load_manifest(entry.name)
        if m and m.get("status") == "active":
            bundles.append(m)
    return bundles


def temporal_directory_segments() -> set[str]:
    """Display-metadata helper for working_memory. Returns the union of
    capability-owned directory segments across active bundles, used to
    annotate the directory-listing view with temporal flags."""
    # For now, capability-owned directories live in kernel directory_registry
    # (slack/notion/github with temporal=True). When future bundles declare
    # additional temporal directories, this helper merges them in.
    return set()  # currently empty; bundles don't yet declare temporal directories
```

That's it. No `WorkspaceProgramView`. No `task_types_for_workspace`. No active-program-resolution-per-workspace at runtime. The reader is consulted at exactly the composition/scaffolding/display moments enumerated above.

#### Caller migrations (small, point-of-use)

| Caller | Change |
|---|---|
| `manage_task._handle_create` (type_key lookup) | When `get_task_type(type_key)` returns None, fall through to `bundle_reader.all_active_bundles()` and search their `task_types` lists. Found = use that template; not found = treat the type_key as YARNNN composing from first principles per ADR-188. |
| `agent_creation.ensure_infrastructure_agent` (first-task scaffolding) | Same fallback pattern. |
| `compose/assembly.py` (page_structure fallback) | Same fallback pattern. |
| `chat.py:966-968` (YARNNN type_key tool handler) | Same fallback pattern. |
| `task_derivation.py:123` (CAPABILITIES read) | Reads kernel CAPABILITIES + unions with `bundle_reader.all_active_bundles()` `capabilities[]` declarations when computing the derivation report. |
| `working_memory.py:473` (directory display metadata) | Reads kernel WORKSPACE_DIRECTORIES + unions with `bundle_reader.temporal_directory_segments()`. (Currently this set is empty since slack/notion/github stay in kernel — but future programs declaring temporal directories will route through here.) |
| `feedback_actuation.py:248,317`, `integrations.py:2137,2441`, path utility helpers | **No change.** These read directory metadata for directories already known to exist in substrate. If `customers/` exists in a workspace's `workspace_files`, the helper reads its frontmatter from the file itself — the registry just provides a fallback if no frontmatter is present. Per ADR-188 Phase 2, frontmatter is preferred over registry. |
| `workspace_init.py:364` (back-office scaffolding) | **No change.** Back-office templates are kernel-universal. |
| `delivery.py:729` (`delivery_requires_approval`) | **No change.** Reads kernel-only flags on universal task types. |

Total: ~6 caller updates, each small (a fallback chain in code that was already structured for the not-found case). Not 15. Not 50.

### 3. Active-program semantics simplify

There is no "active program" runtime concept. There are bundles with `status: active`, and there are workspaces that have particular platform connections. Composition-moment callers (manage_task, task_derivation, etc.) consult **all** active bundles and let the substrate-driven runtime decide what's actually used:

- If a workspace has alpaca connected, TASK.md authored declaring `**Required Capabilities:** read_trading`, the dispatch path runs that task. The bundle isn't consulted — the task ran because TASK.md said it should.
- If a workspace has *no* alpaca connection but TASK.md declares `read_trading`, dispatch fails the capability gate (per ADR-207 P3) and the task is rejected. Same outcome regardless of bundle activation.
- If YARNNN composing in chat asks "should I scaffold a trading-signal task?", `manage_task._handle_create` consults active bundles, finds alpha-trader's template, presents it. This is a *composition* read, not a *dispatch* read.

**The bundle's `status: active` flag means "this program's templates are available for YARNNN to compose with."** Not "this program's runtime hooks are loaded." The runtime has no program hooks. Substrate is the dispatch authority.

This is the cleanest expression of the substrate-agnostic + program-specific distinction. The runtime dispatch path is purely substrate-driven (Axiom 1 + ADR-188 + ADR-207). Bundles are templates and reference data consulted at specific moments by specific callers.

### 4. alpha-commerce bundle creation

Same as v2: a `docs/programs/alpha-commerce/` bundle gets created with `status: deferred` to capture the homeless commerce artifacts (commerce_bot, customers/revenue domains, revenue-report task). Bundle is mostly empty per ADR-223 §5 reference-workspace discipline.

The bundle's status is `deferred`, not `active`, because no operator is running alpha-commerce as a primary program. When commerce activates, status flips and (per §3 above) its templates become available to YARNNN composition.

### 5. Migration — atomic single PR

Singular implementation discipline (CLAUDE.md rule 1): kernel deletions and bundle becoming canonical happen in one commit. The PR has three reviewable steps:

**Step 1 — Reader utility + alpha-commerce bundle**
- New `api/services/bundle_reader.py` (~30 lines).
- New `docs/programs/alpha-commerce/` bundle (status: deferred, MANIFEST + minimal SURFACES + reference-workspace placeholder per ADR-223 §5).
- Unit tests for `load_manifest`, `all_active_bundles`, `temporal_directory_segments`.

**Step 2 — Caller updates + kernel deletions (atomic with Step 1)**
- Update ~6 callers with fallback-to-bundle-reader pattern.
- Delete from kernel: 3 TASK_TYPES entries, 4 WORKSPACE_DIRECTORIES entries, 9 CAPABILITIES entries.
- Add test gate `api/test_adr224_kernel_boundary.py` with the three `test_kernel_*_have_no_program_residue` assertions and at least one positive test that alpha-trader's bundle templates are discoverable through `bundle_reader.all_active_bundles()`.

**Step 3 — Documentation sync**
- ADR-152 (Unified Directory Registry): note "Amended by ADR-224 — kernel registry now holds only universal directories; program-specific directories live in bundle MANIFESTs."
- ADR-188 (registries as templates): note "Validated by ADR-224 — boundary now structurally enforced in code via test gate."
- ADR-223: cross-link to ADR-224 for the implementation details.
- `docs/architecture/SERVICE-MODEL.md` Frame 5: note that the boundary is enforced by deletion, with bundles consulted at composition/scaffolding/display moments.
- `docs/architecture/os-framing-implementation-roadmap.md`: ADR 4 → Implemented.
- CLAUDE.md ADR-registry entry for ADR-224 with implementation status.

All three steps in one PR. No phased ship — singular implementation discipline.

### 6. Test coverage

```python
# api/test_adr224_kernel_boundary.py

def test_kernel_task_types_have_no_program_residue():
    from services.task_types import TASK_TYPES
    program_keys = {"trading-signal", "portfolio-review", "revenue-report"}
    leaked = program_keys & set(TASK_TYPES.keys())
    assert not leaked, f"Program-specific TASK_TYPES still in kernel: {leaked}"

def test_kernel_directories_have_no_program_residue():
    from services.directory_registry import WORKSPACE_DIRECTORIES
    program_keys = {"trading", "portfolio", "customers", "revenue"}
    leaked = program_keys & set(WORKSPACE_DIRECTORIES.keys())
    assert not leaked, f"Program-specific directories still in kernel: {leaked}"

def test_kernel_capabilities_have_no_program_residue():
    from services.orchestration import CAPABILITIES
    program_keys = {"read_slack", "write_slack", "read_notion", "write_notion",
                    "read_github", "read_commerce", "write_commerce",
                    "read_trading", "write_trading"}
    leaked = program_keys & set(CAPABILITIES.keys())
    assert not leaked, f"Program-specific capabilities still in kernel: {leaked}"

def test_alpha_trader_bundle_supplies_program_templates():
    """alpha-trader's MANIFEST.yaml is discoverable and provides trading-signal."""
    from services.bundle_reader import all_active_bundles
    bundles = all_active_bundles()
    alpha_trader = next((b for b in bundles if b["slug"] == "alpha-trader"), None)
    assert alpha_trader is not None, "alpha-trader bundle not discoverable"
    task_keys = {t["key"] for t in alpha_trader.get("task_types", [])}
    assert "trading-signal" in task_keys
    assert "portfolio-review" in task_keys

def test_alpha_commerce_bundle_exists_as_deferred():
    """alpha-commerce bundle exists; status='deferred' so its templates
    are not surfaced to composition reasoning until activation."""
    from services.bundle_reader import load_manifest, all_active_bundles
    m = load_manifest("alpha-commerce")
    assert m is not None
    assert m["status"] == "deferred"
    active = [b["slug"] for b in all_active_bundles()]
    assert "alpha-commerce" not in active
```

### 7. What this ADR does NOT specify

- **Compositor implementation.** ADR forthcoming (ADR 2). Reads SURFACES.yaml directly; doesn't depend on this ADR's bundle_reader.
- **Activation flow UI.** ADR forthcoming (ADR 5). Reads bundles for fork-the-reference; doesn't depend on this ADR's bundle_reader either (or could reuse it — decided in ADR 5).
- **alpha-commerce full bundle population.** Bundle ships near-empty per ADR-223 §5; populates when commerce activates.
- **Cross-program declaration conflicts.** Two active bundles declaring the same task_type slug. Not a concern today (only alpha-trader is active; alpha-commerce is deferred). Decided when alpha-commerce activates.

---

## What changed across versions (record for future review)

| Version | Central claim | Refactor scope | Why corrected |
|---|---|---|---|
| **v1** (initial) | Registries are dispatch-authoritative; split into kernel + bundle along boundary | Heavy — `program_registry.py` service with `WorkspaceProgramView` union semantics, `workspace_id` threading through ~50 call sites | Operator pointed at FOUNDATIONS Principle 10 + Axiom 1 corollary + ADR-188 + ADR-207 P4b. Grep audit confirmed: registries are template libraries, not dispatch authorities |
| **v2** (same-day) | Registries are template libraries, but runtime needs merged-view of kernel + active programs | Medium — centralized `program_bundles.py` loader with `lru_cache`, ~15 callers consuming merged views | Operator pointed at the substrate-vs-program agnosticism distinction: substrate is runtime + agnostic; program is declarative + specific. Runtime dispatch doesn't need merged views; no caller actually does at runtime |
| **v3** (current) | Registries are template libraries; bundles consulted at specific composition/scaffolding/display moments only; runtime dispatch is purely substrate-driven | Small — minimal `bundle_reader.py` (~30 lines), ~6 point-of-use caller updates, kernel deletions | The runtime dispatch path was already program-agnostic; v1 and v2 imported "always-loaded kernel module" shape from incomplete OS analogy; v3 matches what real OSes actually do (consult bundle files at specific moments, kernel stays bundle-agnostic) |

The discipline lesson, written in the form most useful for future reviews: when an OS metaphor pulls the design toward "always-loaded kernel module" shape, check whether real OSes actually do that. They don't. macOS doesn't pre-load Photoshop into the kernel; it consults Photoshop's `.app` bundle at specific moments (Launch Services, dock display, window creation). The kernel itself is bundle-agnostic. The same discipline applies here: runtime stays substrate-driven; bundles get read at specific composition/scaffolding/display moments.

---

## Consequences

### Positive

- **Substrate-vs-program agnosticism is structurally enforced.** Runtime dispatch path has zero bundle awareness. Bundles get read at composition/scaffolding/display moments by callers that already have the right context.
- **Refactor is small.** ~30 lines of new code, ~6 caller updates with fallback-to-bundle-reader, 16 dict-entry deletions, 5 test assertions, 1 new bundle. Sized in hours.
- **alpha-commerce gets an architectural home.** The `status: deferred` bundle captures shipped-but-homeless commerce artifacts.
- **Adding a program is purely additive.** alpha-prediction activation = create bundle + populate MANIFEST.yaml. No kernel touch. No `bundle_reader.py` change. Composition-moment callers automatically discover its templates via `all_active_bundles()`.
- **Test gate enforces the boundary going forward.** `test_kernel_*_have_no_program_residue` fails on regression.

### Negative / costs

- **6 caller updates, each adding a fallback chain.** Mechanical but real.
- **`bundle_reader.py` is new infrastructure.** Small (~30 lines) but adds a module to maintain.
- **alpha-commerce bundle creation.** Net new bundle (deferred status, minimal contents).
- **Cache invalidation on bundle file change.** `lru_cache` is fine — bundles are repo-tracked, change at deploy time, not runtime. Revisit if the activation flow ADR (ADR 5) needs runtime mutation.

### Risks

- **Test gate too strict / too loose.** Mitigation: the assertions check dict-key membership specifically, not generic string-presence. Comments and docstrings can mention "trading" without triggering a fail.
- **Caller fallback chain regression.** A future change to `manage_task._handle_create` that drops the fallback would silently break trading-signal lookup. Mitigation: positive test (`test_alpha_trader_bundle_supplies_program_templates`) catches this — if the bundle's templates aren't reachable via the fallback chain, the test fails.
- **Substrate that already references program-shaped directory names continues working post-deletion?** Yes — directory registry deletions are template-residue deletions. Substrate that has `/workspace/context/trading/` populated continues to work because (a) `working_memory.py` discovers directories from filesystem, not from registry, (b) path utility helpers prefer file frontmatter over registry per ADR-188 Phase 2, (c) the alpha-trader bundle declares the trading domain so display metadata is still resolvable. Verified during Step 2 implementation.

---

## Open questions

Explicitly deferred — none gate ratification.

- **`temporal_directory_segments()` future shape.** Currently empty (slack/notion/github stay in kernel as capability-owned). When future bundles declare temporal directories, the helper merges them in. The merge semantics (union, conflict-resolution) decided when the first bundle does so.
- **Bundle reload when files change at runtime.** `lru_cache` is process-lifetime. Compositor + activation flow may want runtime invalidation. Decided in their ADRs.
- **Migration of existing kvk workspace.** kvk's workspace has `/workspace/context/trading/` and `/workspace/context/portfolio/` populated. Per ADR-209 (authored substrate) and ADR-188 Phase 2, these continue to work post-deletion — the directories' `_domain.md` frontmatter (or absence thereof) drives behavior, not the kernel registry. Verified during Step 2.

---

## Decision

**Adopt the kernel/program boundary refactor as defined above.** Kernel registries hold only kernel-universal templates. Program-specific templates live in `docs/programs/{slug}/MANIFEST.yaml`. A minimal `api/services/bundle_reader.py` (~30 lines) provides bundle reads at the few composition/scaffolding/display moments where they're needed. Runtime dispatch path remains purely substrate-driven (no bundle awareness, no merged views, no `workspace_id` threading). Migration is atomic. Test gate enforces the boundary going forward.
