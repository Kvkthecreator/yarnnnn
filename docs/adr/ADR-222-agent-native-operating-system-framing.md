# ADR-222: Agent-Native Operating System Framing

**Status:** Proposed (framing) → Implementation ADRs follow
**Date:** 2026-04-27
**Authors:** KVK, Claude
**Related:** FOUNDATIONS.md (axiom hardening), GLOSSARY.md (vocabulary), SERVICE-MODEL.md (model alignment), docs/programs/ (program bundles), docs/analysis/external-oracle-thesis-2026-04-26.md (discourse arc)
**Supersedes (in part):** None structurally; reframes much
**Amends:** ADR-167 v2 (list/detail surfaces), ADR-186 (prompt profiles), ADR-205 (workspace primitive collapse)

---

## Context

Across two months of architectural work the project has converged on a set of artifacts that, taken together, look exactly like an operating system in the precise technical sense — kernel, syscall surface, filesystem, daemons, shell, userspace. The vocabulary the project has been using ("substrate," "primitives," "workspace," "program") is structurally faithful to that mapping but has been treated as project-internal language rather than as the literal OS-architecture concepts they correspond to.

The discourse this ADR concludes (see `docs/analysis/external-oracle-thesis-2026-04-26.md` §11 + the conversation that followed) surfaced two questions in sequence:

1. *How does the platform handle vertical specialization without sacrificing the agnostic substrate?*
2. *Is "workspace type" / "workspace mode" the right naming for that specialization layer?*

The answer to (1) is a **composition layer** that reads program-shipped surface declarations and renders the cockpit accordingly — universal substrate primitives, universal CRUD modals, universal component library, with declarative composition specs as the only specialization point.

The answer to (2) is *no*: workspaces don't have types — they **run programs**. The naming impulse came from a missing conceptual frame. Once the OS framing is committed, the naming question dissolves: the workspace's type is implicit in which program it runs, exactly as a Mac doesn't have a "Photoshop type" just because Photoshop is open.

This ADR commits the OS framing as canonical so the vocabulary, the kernel boundary, and the program-bundle/compositor architecture all become first-class.

---

## Decision

**YARNNN is canonized as an agent-native operating system.**

The framing is literal, not metaphorical: every box in OS architecture has a corresponding YARNNN artifact. The vocabulary, layering rules, and architectural disciplines of OS design apply directly.

### The full mapping

| OS concept | YARNNN equivalent | Status |
|---|---|---|
| **Kernel** — privileged core mediating everything | Substrate primitives + axioms + filesystem + task pipeline + privileged daemons (Reviewer, back-office tasks) | Shipped |
| **Filesystem** — kernel-managed persistent storage | `workspace_files` + ADR-209 authored substrate (versioned, attributed, retained) | Shipped |
| **System call surface (syscall ABI)** — userspace's only invokable entry to the kernel | The primitive matrix (ADR-168) — `CHAT_PRIMITIVES` + `HEADLESS_PRIMITIVES` registries | Shipped |
| **Daemon / privileged process** — runs with elevated authority, system-wide | Reviewer (judgment authority), back-office tasks (per ADR-164) | Shipped |
| **Shell** — the interactive interface to the kernel | YARNNN chat agent (`api/agents/yarnnn.py`) — application code, not kernel, per ADR-205 | Shipped |
| **Init system** — bootstraps a userspace | `workspace_init.py` (signup-time scaffolding) | Shipped |
| **Application / Program** — runs in userspace, declares what it needs | A program (alpha-trader is the first; alpha-prediction + alpha-defi are reference SPECs) | Just landed (e094d98) |
| **Application bundle** — declarative package: manifest + resources + UI declaration | `docs/programs/{program}/` (README is manifest; reference-workspace is bundled resources; SURFACES manifest will declare UI) | Bundle convention partially landed; SURFACES manifest deferred to implementation ADR |
| **Compositor / window manager** — reads application UI declarations and renders the screen | The composition layer — FE infrastructure that resolves a program's composition manifest against substrate paths and produces the rendered cockpit | **Not yet built — implementation ADR forthcoming** |
| **Composition manifest** — the file an app ships declaring its surface composition | `SURFACES.yaml` (or equivalent), shipped in the program bundle | **Convention not yet defined — implementation ADR forthcoming** |
| **Userspace / user's home directory** — per-user state and preferences | An operator's `/workspace/` | Shipped |
| **Per-user customization layer** — user overrides of application defaults | Workspace-level composition overlay (`/workspace/SURFACES.yaml` override) | **Not yet built** |
| **Shared system libraries (libc, libGL)** — reusable across applications | Universal component library (`web/components/library/` — to be formalized) | Partial; convention not yet formal |
| **Distribution** — curated set of (kernel + apps + DE + defaults) | A program is a YARNNN distribution — kernel-shared, program-curated | Implicit in program bundle convention |

Every row on the right has either been built or is named in this ADR's implementation roadmap. Nothing on the left is unrepresented.

### Vocabulary commitments

The OS framing graduates the following to canonical vocabulary. These names are added to `GLOSSARY.md` in the same commit chain as this ADR:

| Term | Meaning | Replaces / sharpens |
|---|---|---|
| **Kernel** | The substrate layer: filesystem + primitives + axioms + privileged daemons. Domain-agnostic by construction. | Sharpens "substrate" — both terms remain valid; "kernel" is the macro frame, "substrate" is the technical implementation. |
| **Syscall ABI** (informal: syscall surface) | The primitive matrix as the only invokable boundary userspace has to the kernel. | Sharpens "primitive matrix" — same artifact, OS-faithful framing. |
| **Program** | An application that runs in YARNNN userspace. Currently: alpha-trader (built), alpha-prediction (reference SPEC), alpha-defi (reference SPEC). | Already adopted in `docs/programs/`; this ADR ratifies it. |
| **Program bundle** | The declarative package shipping a program: manifest + reference workspace + composition manifest + dependencies. Lives at `docs/programs/{program}/`. | New canonical term. Equivalent to `.app` (macOS), `.deb` (Debian), `.apk` (Android). |
| **Program manifest** | The top-level declaration in a program bundle (currently `README.md` at bundle root). Names what the program is, what kernel features it depends on, what surfaces it commits to, success bar. | New canonical term. Equivalent to `Info.plist` (macOS), `AndroidManifest.xml` (Android), `manifest.json` (Chrome extensions). |
| **Composition manifest** | The bundle-shipped declarative spec for surface composition (`SURFACES.yaml` or equivalent — exact format defined by implementation ADR). | New canonical term. Replaces would-have-been "workspace type" / "workspace mode." |
| **Compositor** | The FE/API infrastructure that resolves a program's composition manifest against the operator's workspace substrate and renders the cockpit. | New canonical term for an architectural layer that has been implicit and unnamed. |
| **System component library** | The universal FE component library (`web/components/library/`) — building blocks composition manifests reference. | New canonical name. Equivalent to shared system libraries. |
| **Userspace** (informal) / **Workspace** (canonical) | The operator's `/workspace/` — per-operator state, owned by the operator, not by the kernel. | Sharpens "workspace" — both remain valid; "userspace" is the OS-framing word. |
| **Workspace overlay** | Operator-authored deltas to a program's composition manifest, lives at `/workspace/SURFACES.yaml`. | New canonical term. Equivalent to a user's customized DE preferences. |
| **Distribution** (informal) | A program understood as a curated bundle of (composition manifest + reference substrate + dependencies + commitments) on top of the YARNNN kernel. Same kernel; different program → different distribution. | New informal term; not required for technical work but useful for positioning. |

The retired-vocabulary candidates (rejected as housing for this layer):

- **Workspace type / workspace kind** — rejected. Workspaces don't have types; they run programs. (See "Why workspace type was wrong housing" below.)
- **Workspace mode** — rejected. Implies switchability that doesn't exist (a trader workspace doesn't switch into a commerce workspace at runtime), and conflates Identity with Channel.

### Why workspace type was wrong housing

A workspace's "type" would have been a flag the kernel sets to gate behavior. This requires the kernel to know about specific programs (a kernel branch on `if workspace.type == "trader"`). That violates the OS discipline: kernels don't know applications. Linux's kernel has no concept of "this is Firefox" — Firefox builds itself out of kernel primitives.

Under the OS framing, the kernel doesn't gate by program. It exposes a uniform substrate API. The **compositor** (a separate architectural layer, not the kernel) reads the workspace's program declaration and resolves the composition manifest against substrate. The kernel stays agnostic; the compositor stays application-aware. Type tags become unnecessary because the workspace's program declaration *is* the implicit type, and the compositor — not the kernel — is what reads it.

This separation is load-bearing. Without it, every new program would tempt kernel hooks. With it, adding a program is purely additive: a new bundle, possibly new system component library entries, no kernel touch.

---

## Kernel boundary — what's in, what's out

This ADR commits a precise definition of the kernel boundary. All future architectural work is reviewed against it.

### In the kernel (universal, never specialized)

- **Filesystem** — `workspace_files`, the authored substrate revision graph (ADR-209), path conventions, lifecycle states.
- **Syscall ABI** — the primitive matrix (ADR-168). Exact set of primitives invokable by the chat shell, headless task pipeline, MCP, and any future caller.
- **Task pipeline** — `task_pipeline.py` execution loop (ADR-141). Mechanical scheduling, generation dispatch, output persistence, delivery.
- **Privileged daemons** — Reviewer (ADR-194 v2), back-office tasks (ADR-164), reconciler (ADR-195 v2).
- **Shell** — YARNNN chat agent (`api/agents/yarnnn.py`). Platform-fixed voice, no workspace-authored persona, application code that uses the kernel like any other application.
- **Init system** — `workspace_init.py`. Idempotent signup-time scaffolding.
- **Axioms** — FOUNDATIONS.md axioms 0–9. The architectural conscience.
- **Universal substrate paths** — `/workspace/memory/`, `/workspace/uploads/`, `/workspace/review/`, `/workspace/context/_shared/`, `/agents/`, `/tasks/`. Universal because every workspace, regardless of program, has these.

### In the compositor (universal infrastructure that reads program-specific declarations)

- **Composition resolver** — given workspace + program declaration, produces the rendered surface tree. Uses universal components from the library; reads workspace substrate.
- **System component library** — universal FE building blocks: `MetricCardRow`, `ChecklistRender`, `EntityGrid`, `ChartFromCSV`, `MarkdownRender`, file viewers, principle editors, mandate editors, etc. Built once, used by any program's composition manifest.
- **Workspace overlay merger** — reads `/workspace/SURFACES.yaml` overrides on top of program-default composition manifest.

### In program bundles (specialization lives here)

- **Program manifest** (`docs/programs/{program}/README.md`) — what the program is, what kernel features it requires, success bar, OS dependencies, phase milestones.
- **Composition manifest** (`docs/programs/{program}/SURFACES.yaml` or equivalent) — what the cockpit looks like for this program.
- **Reference workspace** (`docs/programs/{program}/reference-workspace/`) — bundled starter substrate operators fork on activation.
- **Program-specific context-domain conventions** — when a program's reference workspace declares `customers/`, `portfolio/`, `trading/`, those naming conventions are part of the program bundle, not the kernel registry.
- **Program-specific task type catalog** — the curated task templates that program operators commonly fork from (e.g., `trading-digest`, `revenue-report`). The kernel exposes the task primitive; programs ship the templates.

### Refactor implications (deferred to implementation ADR)

The current codebase has program-specific declarations colocated with kernel-universal ones in several services. The kernel boundary above implies splitting:

- **`api/services/directory_registry.py`** — split into kernel-universal directories (memory, uploads, review, _shared) and program-specific directories declared in program bundles.
- **`api/services/task_types.py`** — split into kernel-universal task types (back-office, daily-update) and program-specific task types declared in program bundles.
- **`api/services/orchestration.py`** — `AGENT_TEMPLATES` keeps universal roles (the universal six + thinking_partner + reviewer); program-specific agent configurations move to program bundles.
- **`api/services/platform_tools.py`** — `TRADING_TOOLS`, `COMMERCE_TOOLS`, `SLACK_TOOLS`, etc. become program-bundle declarations (a program declares which platform tool surfaces it requires) rather than universal registries.

These refactors do not block the framing ADR. They are the next implementation ADR's scope.

---

## Architectural disciplines this commits

If the OS framing is canonical, certain disciplines follow automatically. They are listed here so future ADRs can be reviewed against them.

1. **Kernel changes are sacred.** Substrate primitives, axioms, filesystem layout — modifying these requires ADRs and review against all reference programs (alpha-trader + alpha-prediction + alpha-defi SPECs). The litmus test from `docs/programs/README.md` applies.

2. **Programs do not modify the kernel.** A program's needs that require kernel changes graduate to ADRs that justify the kernel change as universally serving all reference programs. Program-specific kernel hooks are a design failure.

3. **The shell is application code.** YARNNN's chat agent uses the same syscall surface every application does. No privileged shortcuts. ADR-205 already honored this; the OS framing names why it matters.

4. **The compositor reads, never authors.** The compositor produces views of substrate; it doesn't write to substrate. Substrate writes go through the syscall surface (primitives) like any other authoring action. (Workspace overlay is itself a substrate file authored by the operator — the compositor reads it, doesn't write it.)

5. **System component library is additive-only.** Components added to serve one program become available to all programs. Removing a component is breaking and requires deprecation discipline.

6. **Program bundles are versioned in-repo.** `docs/programs/{program}/` is git-tracked, reviewable in PR. No runtime program registry is required — programs are declared by their bundle's existence in the repo.

7. **Distribution identity is bundle identity.** "What is alpha-trader?" is answered by reading the bundle. Marketing surfaces, public-readable artifacts, and operator activation flows all read from the bundle. There is no separate "alpha-trader product spec" living outside the bundle.

8. **Workspace state is operator property.** The kernel does not own a workspace's content; the operator does. ADR-209 authored substrate already enforces attribution; the OS framing names *why* — userspace is user-owned, kernel does not write to it without the operator's syscall.

---

## Implementation ADRs this implies

The framing this ADR commits requires implementation work to land fully. Each implementation ADR is its own decision; this ADR sketches their scope, not their content.

### ADR-XXX: Program Bundle Specification (forthcoming)

Defines the precise format of a program bundle: manifest schema, composition manifest format (likely YAML, structure TBD), reference workspace conventions, dependency declaration, lifecycle states (active program / reference SPEC / deferred). Ratifies `docs/programs/` as the canonical bundle root.

### ADR-XXX: Compositor Layer (forthcoming)

Defines the FE/API infrastructure that resolves composition manifests. Composition resolver, component binding model, workspace overlay merge semantics, surface-archetype rendering (Document / Dashboard / Queue / Briefing / Stream from ADR-198). Ships as new infrastructure; supersedes ad-hoc per-route layout code.

### ADR-XXX: Kernel / Program Boundary Refactor (forthcoming)

The actual code refactor: split `directory_registry.py`, `task_types.py`, `orchestration.py`, `platform_tools.py` along the boundary defined in this ADR. Move program-specific declarations into program bundles. Rewire callers. Test on alpha-trader as the live program.

### ADR-XXX: System Component Library Convention (forthcoming, possibly folded into the Compositor ADR)

Names the convention for `web/components/library/` — what's in, what's out, registration model, versioning expectations.

### ADR-XXX: Reference-Workspace Activation Flow (forthcoming, dependent on Bundle Spec)

Defines the operator activation flow: program selection → reference-workspace import → differential-authoring conversation. Likely lives in `workspace_init.py`'s program-aware extension. This is the implementation half of the lived↔reference loop sketched earlier in the discourse.

### ADR-XXX: Reference-Reflexive Loop (forthcoming, dependent on Activation Flow)

Defines the back-office task that graduates lived workspace patterns to reference workspace canon (`back-office-reference-graduation`). Includes redaction discipline, graduation criteria, approval flow.

---

## Consequences

### Positive

- **Architectural vocabulary becomes precise.** "Kernel," "compositor," "program bundle" are well-understood OS-architecture terms; using them reduces the burden of architectural communication and makes the design legible to anyone with technical literacy.
- **Naming traps dissolve.** Workspace type / mode / kind / class debates are settled — the OS framing answers all of them by saying *workspaces run programs; the program is the implicit type; specialization happens at the compositor*.
- **Specialization without fragmentation.** Vertical specialization (alpha-trader cockpit feeling like a trader's environment) is achieved by composition manifests in program bundles, not by branching the kernel. The substrate stays general; verticality lives in declarative bundle artifacts.
- **Adding programs is purely additive.** A new program is a new bundle; possibly new system component library entries; no kernel touch.
- **Cross-operator compounding has a structural home.** The lived↔reference graduation loop becomes "kvk's lived workspace generates updates to alpha-trader's bundle, which propagates to all forked workspaces." Same architecture, multi-tenant by construction.
- **Positioning sharpens.** "YARNNN is an agent-native operating system; programs run on it" is honest, defensible, and structurally distinct from "AI productivity tool" or "agent platform."

### Negative / costs

- **Real refactor work follows.** The kernel/program boundary refactor (separate ADR) is meaningful — splitting registries that currently colocate kernel and program-specific declarations is real engineering, even though the user has explicitly approved being aggressive about pre-launch architectural changes.
- **Compositor build is real infrastructure.** The composition manifest format, the resolver, the overlay merger, the FE binding model — all are new architecture. Estimated multiple weeks of build at the level of detail required.
- **Documentation update is broad.** Many existing docs reference "substrate" without the OS framing, "workspace" without the userspace framing, etc. This ADR commits to updating only the load-bearing canonical docs (FOUNDATIONS, GLOSSARY, SERVICE-MODEL, CLAUDE.md) in the same commit chain; other docs absorb the vocabulary as they are touched.
- **Risk of premature OS-purism.** Real OS architecture has decades of precedent and refinement YARNNN doesn't have. Adopting the framing imposes some discipline (kernel boundary, syscall ABI, application isolation) but should not be allowed to import disciplines that don't serve YARNNN's actual needs (e.g., process isolation, paging, TLB management). The mapping is faithful where it serves; OS purism is not the point.

### Risks

- **Over-naming.** Adding "kernel," "compositor," "userspace," etc. to vocabulary creates new terms to maintain. The mitigation: only the load-bearing terms are added to GLOSSARY; "kernel" is informal-canonical (alongside "substrate" as technical-canonical), "compositor" is needed for the new layer, "program bundle" is needed for the new artifact. Other terms (userspace, distribution, etc.) are informal aids, not glossary entries.
- **Documentation drift.** The OS vocabulary lands in canonical docs but may not propagate to ADRs and feature docs immediately. The mitigation: this ADR commits only the load-bearing canonical docs; drift is accepted; future doc-touches absorb the vocabulary as they happen.
- **Implementation-ADR sequencing.** The framing ADR (this one) is meaningful only if the implementation ADRs follow. The mitigation: a roadmap doc lands in the same commit chain (`docs/architecture/os-framing-implementation-roadmap.md`) so the deferred work is visible and trackable.

---

## Implementation roadmap (sketched)

Tracked in detail in `docs/architecture/os-framing-implementation-roadmap.md` (lands in the same commit chain). Summary sequence:

1. **This ADR + canonical doc updates** (current commit chain) — vocabulary, axiom, glossary, SERVICE-MODEL, CLAUDE.md, programs/ alignment, roadmap doc.
2. **Program Bundle Specification ADR** — formalizes composition manifest format, manifest schema, reference workspace conventions.
3. **Compositor Layer ADR + build** — FE/API infrastructure that resolves composition manifests. Significant engineering.
4. **Kernel/Program Boundary Refactor ADR + build** — split registries, move program-specific declarations into bundles.
5. **Reference-Workspace Activation Flow ADR + build** — operator activation as fork-the-reference + differential authoring.
6. **Reference-Reflexive Loop ADR + build** — back-office graduation task.

Steps 2–4 can be parallelized in some order; step 5 depends on 2; step 6 depends on 5. Step 1 is what this commit chain delivers.

---

## Why now

The discourse arc since 2026-04-15 has been narrowing on the right architectural shape. The OS/program separation landed last week. The composition layer was identified yesterday. The naming question (workspace type/mode) surfaced today. Each step has been a sharpening, not a pivot.

The OS framing is the conceptual frame that resolves all three. Naming it now — before the implementation ADRs — keeps the implementation work disciplined and prevents premature commitment to mechanisms (workspace types, mode flags) that the framing makes unnecessary.

Pre-launch, pre-users, all data is test data. The cost of formalizing this framing now is documentation work; the cost of formalizing it later is the same documentation work plus undoing whatever ad-hoc concepts grew in the gap. Now is cheaper.

---

## Open questions

These are explicitly deferred — none gate the framing ADR.

- **Composition manifest format precise spec** — YAML, JSON, embedded markdown blocks, custom DSL? Decided in the Program Bundle Specification ADR.
- **Surface-archetype layering** — how composition manifests express the five surface archetypes (Document / Dashboard / Queue / Briefing / Stream from ADR-198). Decided in the Compositor Layer ADR.
- **Multi-program operators** — operator running both alpha-trader and alpha-commerce. Workspace overlay model handles single-program override; multi-program is its own design question. Defer until alpha-commerce activates.
- **Public-readable program bundle rendering** — letting marketing surfaces render reference workspaces as public demos. Real possibility, not blocking.
- **Cross-program system component contributions** — when a future program needs a component that doesn't exist in the library, how is it added? Likely PR convention; formalized in the System Component Library ADR or folded into the Compositor ADR.

---

## Decision

**Adopt the agent-native operating system framing as canonical.** Vocabulary, kernel boundary, program bundle convention, and compositor layer become first-class architectural concepts. FOUNDATIONS gains an axiom or derived principle locking the framing. GLOSSARY adds the OS vocabulary. SERVICE-MODEL aligns to the OS architecture description. Implementation work proceeds via subsequent ADRs as roadmapped.
