# Architecture Decision Records

ADRs document significant architectural decisions made during development.

## Active ADRs

These are the current, active decision records that define yarnnn's architecture. Ordered by concern area.

### Foundation (Schema, Memory, Content)

| ADR | Title | Status |
|-----|-------|--------|
| [059](ADR-059-simplified-context-model.md) | Simplified Context Model | Accepted |
| [064](ADR-064-unified-memory-service.md) | Unified Memory Service | Accepted |
| [067](ADR-067-session-compaction-architecture.md) | Session Compaction & Continuity | Implemented |
| [072](archive/ADR-072-unified-content-layer-tp-execution-pipeline.md) | Unified Content Layer & TP Execution Pipeline | **Superseded by ADR-153** |

### Platform Sync & Integrations

| ADR | Title | Status |
|-----|-------|--------|
| [075](ADR-075-mcp-connector-architecture.md) | MCP Connector Architecture | Implemented |
| [076](ADR-076-eliminate-mcp-gateway.md) | Eliminate MCP Gateway (Direct API) | Implemented |
| [077](archive/ADR-077-platform-sync-overhaul.md) | Platform Sync Overhaul | **Superseded by ADR-153** |
| [085](archive/ADR-085-refresh-platform-content-primitive.md) | RefreshPlatformContent Primitive | **Superseded by ADR-153** |
| [086](ADR-086-sync-failure-visibility.md) | Sync Failure Visibility | Implemented |
| [100](ADR-100-simplified-monetization.md) | Simplified Monetization (2-tier) | Implemented |
| [112](ADR-112-sync-efficiency-concurrency-control.md) | Sync Efficiency & Concurrency Control | Implemented |
| [113](ADR-113-auto-source-selection.md) | Auto Source Selection | Implemented |

### Agent Framework & Execution

| ADR | Title | Status |
|-----|-------|--------|
| [080](ADR-080-unified-agent-modes.md) | Unified Agent Modes | Implemented |
| [081](ADR-081-execution-path-consolidation.md) | Execution Path Consolidation | Implemented |
| [087](ADR-087-workspace-scoping-architecture.md) | Workspace Scoping Architecture | Implemented |
| [088](archive/ADR-088-input-gateway-work-serialization.md) | Input Gateway & Work Serialization | Phase 1 Implemented |
| [090](archive/ADR-090-work-tickets-consolidation.md) | Work Tickets Consolidation | Phases 1-3 Complete |
| [092](ADR-092-agent-intelligence-mode-taxonomy.md) | Agent Intelligence & Mode Taxonomy | Phase 5 Implemented |
| [101](ADR-101-agent-intelligence-model.md) | Agent Intelligence Model | Implemented |
| [102](archive/ADR-102-yarnnn-content-platform.md) | Yarnnn Content Platform | Implemented |
| [103](archive/ADR-103-agentic-framework-reframe.md) | Agentic Framework Reframe | Implemented |
| [104](ADR-104-agent-instructions-unified-targeting.md) | Agent Instructions as Unified Targeting | Implemented |
| [105](ADR-105-instructions-chat-surface-migration.md) | Instructions to Chat Surface Migration | Implemented |
| [109](ADR-109-agent-framework.md) | Agent Framework — Scope × Role × Trigger | Implemented (pending role rename) |

### Workspace, Skills & Output

| ADR | Title | Status |
|-----|-------|--------|
| [106](ADR-106-agent-workspace-architecture.md) | Agent Workspace Architecture | Phase 1 Complete |
| [107](archive/ADR-107-knowledge-filesystem-architecture.md) | Knowledge Filesystem Architecture | Implemented |
| [108](archive/ADR-108-user-memory-filesystem-migration.md) | User Memory Filesystem Migration | Implemented |
| [116](ADR-116-agent-identity-inter-agent-knowledge.md) | Agent Identity & Inter-Agent Knowledge | Implemented |
| [118](ADR-118-skills-as-capability-layer.md) | Skills as Capability Layer | Phase A+B+C Implemented, D Proposed |
| [119](ADR-119-workspace-filesystem-architecture.md) | Workspace Filesystem Architecture | Proposed |

### Composer & Agent Lifecycle

| ADR | Title | Status |
|-----|-------|--------|
| [110](ADR-110-onboarding-bootstrap.md) | Onboarding Bootstrap | Implemented |
| [111](archive/ADR-111-agent-composer.md) | Agent Composer | Implemented (dissolved by ADR-156) |
| [114](ADR-114-composer-substrate-aware-assessment.md) | Composer Substrate-Aware Assessment | **Superseded by ADR-156** |
| [115](ADR-115-composer-workspace-density-model.md) | Composer Workspace Density Model | Proposed |
| [117](ADR-117-agent-feedback-substrate-developmental-model.md) | Agent Feedback Substrate & Developmental Model | Proposed (identity split clarified by ADR-189) |
| [156](ADR-156-composer-sunset.md) | Composer Sunset — Single Intelligence Layer | Phase 1 Implemented |

### Three-Layer Cognition Evolution (ADR-138 → ADR-189)

The current cognitive architecture evolved through a series of decisions. ADR-189 is the current canonical reference; the preceding ADRs remain as historical record of how we got there.

| ADR | Title | Status |
|-----|-------|--------|
| [138](ADR-138-agents-as-work-units.md) | Agents as Work Units — Project Layer Collapse | Phases 1-4 Implemented |
| [164](ADR-164-back-office-tasks-tp-as-agent.md) | Back Office Tasks — TP as Agent | Phase 4 Implemented |
| [176](ADR-176-work-first-agent-model.md) | Work-First Agent Model | Implemented (Decision 1 superseded by ADR-189) |
| [186](ADR-186-tp-prompt-profiles.md) | TP Prompt Profiles | Phase 1-3 Implemented |
| [188](ADR-188-domain-agnostic-framework.md) | Domain-Agnostic Framework — Registries as Template Libraries | Phases 1-2 Implemented (Phase 3+ completed by ADR-205) |
| [189](ADR-189-three-layer-cognition.md) | Three-Layer Cognition — YARNNN, Specialists, Agents | Proposed — canonical (Phase 2 pragmatic preservation reversed by ADR-205) |
| [205](ADR-205-primitive-collapse.md) | Workspace Primitive Collapse — YARNNN as Sole Persistent Identity | Backend Implemented, F1+F2+F5 Shipped (F2 framing extended by ADR-206) |
| [206](ADR-206-operation-first-scaffolding.md) | Operation-First Scaffolding — Intent / Deliverables / Operation | Phases 1-3 Implemented — refined by ADR-207 |
| [207](ADR-207-primary-action-centric-workflow.md) | Primary-Action-Centric Workflow — Mandate, Loop, Capabilities | **Proposed — canonical operator workflow** |
| [208](archive/ADR-208-workspace-git-backend.md) | Workspace Git Backend for Operator-Authored Files | **Withdrawn (superseded by ADR-209)** |

---

## The Modern Era (ADR-209 → 425)

> **Read this first.** This is the index for the current era — authored substrate, the OS framing, the Reviewer loop, the three altitudes, and the coworking commons. It is grouped by **arc**, not by number. The spine documents ([ESSENCE](../ESSENCE.md) · [THESIS](../architecture/THESIS.md) · [FOUNDATIONS](../architecture/FOUNDATIONS.md) · [LAYER-MAPPING](../architecture/LAYER-MAPPING.md)) are the canon; these ADRs are the decision log beneath them.
>
> **Status legend:** a bare status (`Implemented` / `Accepted` / `Proposed`) means live canon. `⛔ Superseded by ADR-N` means the *whole* ADR is dead history — read the successor. `Live · <clause> → ADR-N` means the ADR is live but one clause/mechanism was later superseded or amended (read both). Most ADRs in a given arc are intermediate steps toward the arc's live endpoint (flagged **★ ENDPOINT**). *Doc-first ADRs ship no code; their status is the decision, not a deploy.*

### Authored substrate + kernel-boundary (209–212, 220, 286, 320–328)

The moat's substrate floor and the permission topology it stands on.

| ADR | Title | Status |
|-----|-------|--------|
| [209](ADR-209-authored-substrate.md) | Authored Substrate — attributed, parent-pointered, retained | **★ Implemented (moat floor)** |
| [211](ADR-211-reviewer-substrate-phase-4.md) | Reviewer Substrate — Phase 4 Completion | Implemented |
| [212](ADR-212-layer-mapping-correction.md) | Layer Mapping Correction | Implemented |
| [220](ADR-220-authored-substrate-in-directory-registry.md) | Authored Substrate in the Directory Registry | Implemented |
| [286](ADR-286-kernel-program-substrate-single-writer.md) | Single-Writer Per Path | **★ Implemented** |
| [320](ADR-320-constitution-region-topological-cut.md) | Permission Topology: Five Roots, One Gate, `access(2)` | **★ Implemented** |
| [321](ADR-321-topology-native-file-primitives.md) | Topology-Native File Primitives | Implemented |
| [322](ADR-322-entity-layer-pruning.md) | Entity-Layer Pruning — a `/proc` over the filesystem | Implemented |
| [323](ADR-323-finish-the-persona-frame-collapse.md) | Finish the Persona-Frame Collapse | Implemented |
| [324](ADR-324-infercontext-dissolution.md) | InferContext Dissolution | Implemented |
| [325](ADR-325-embed-as-gated-primitive.md) | Embed as a Gated Primitive | Implemented |
| [328](ADR-328-substrate-portability-invariant.md) | Substrate Portability Invariant | Proposed · D8 resolved by ADR-427 |
| [427](ADR-427-binary-native-substrate-and-the-storage-seam.md) | Binary-Native Substrate + the Storage Seam (local-disk keystone) | **★ Proposed (keystone)** |

### OS framing + programs + compositor (222–230, 242, 273, 312)

Kernel / program / userspace; bundles; the compositor; the cockpit → Home arc.

| ADR | Title | Status |
|-----|-------|--------|
| [222](ADR-222-agent-native-operating-system-framing.md) | Agent-Native Operating System Framing | **★ Live canon** |
| [223](ADR-223-program-bundle-specification.md) | Program Bundle Specification | Implemented |
| [224](ADR-224-kernel-program-boundary-refactor.md) | Kernel / Program Boundary — Template Residue Deletion | Implemented |
| [225](ADR-225-compositor-layer.md) | Compositor Layer — Declarative Surface Composition | Implemented |
| [226](ADR-226-reference-workspace-activation-flow.md) | Reference-Workspace Activation Flow | Implemented |
| [227](ADR-227-task-capability-tool-augmentation.md) | Task Capability Tool Augmentation | Implemented |
| [228](archive/ADR-228-cockpit-as-delegation-posture.md) | Cockpit as Operation — Four Faces | ⛔ Superseded by ADR-312 (framing) |
| [229](ADR-229-judgment-first-dispatch-and-generative-defer.md) | Judgment-First Dispatch + Generative Defer | Implemented |
| [230](ADR-230-persona-program-registry-unification.md) | Persona-Program Registry Unification | Implemented |
| [242](ADR-242-cockpit-bundle-components-alpha-trader-pass.md) | Cockpit Bundle Components — alpha-trader Pass | Implemented |
| [273](archive/ADR-273-cockpit-refactor-program-section-split.md) | Cockpit Refactor — Kernel/Program Section Split | ⛔ Superseded by ADR-312 |
| [312](ADR-312-home-as-composition.md) | Home as Composition — Six Kernel Slots | **★ Live endpoint** |

### Task sunset + recurrences (231, 233, 235, 260–263, 268–270)

Tasks dissolved into mandate-driven recurrences; the single execution shape.

| ADR | Title | Status |
|-----|-------|--------|
| [231](ADR-231-task-abstraction-sunset.md) | Task Abstraction Sunset | Live · shape enum → ADR-261 |
| [233](ADR-233-shape-driven-invocation-lifecycle.md) | Shape-Driven Invocation Lifecycle | Live · routing → ADR-260/261/262 |
| [235](ADR-235-update-context-dissolution.md) | UpdateContext Dissolution + ManageRecurrence + ManageAgent | Implemented |
| [260](ADR-260-real-time-reviewer-loop.md) | Real-Time Reviewer Loop | **★ Implemented (−8,342 LOC)** |
| [261](ADR-261-recurrences-as-prompts.md) | Recurrences as Prompts — Single Execution Shape | **★ Implemented** |
| [262](ADR-262-output-topology-and-specs.md) | Output Topology and Specs | Implemented |
| [263](ADR-263-recurrence-mode-mechanical-vs-judgment.md) | Recurrence Mode — Mechanical vs Judgment | Proposed |
| [268](ADR-268-market-context-aware-recurrences.md) | Market-Context-Aware Recurrences | Proposed |
| [269](ADR-269-capability-flow-wiring.md) | Capability-Flow Wiring | Proposed |
| [270](ADR-270-fire-on-activation-recurrences.md) | Fire-on-Activation Recurrences | Proposed |

### Reviewer loop + persona-frame (218, 247–258, 274–276, 284–285, 290, 295, 301–306, 314–315, 318–319, 326)

The Reviewer's chat/loop evolution — heavily self-superseding. **Live endpoint = 260/261/262 (above).** The Reviewer canon now lives in [reviewer-seat-substrate.md](../architecture/reviewer-seat-substrate.md) + siblings, not these ADRs.

| ADR | Title | Status |
|-----|-------|--------|
| [218](archive/ADR-218-persona-reflection.md) | Persona Reflection — Reviewer Self-Evolution | ⛔ Superseded by ADR-256 |
| [247](archive/ADR-247-three-party-narrative-model.md) | Three-Party Narrative Model | ⛔ Superseded by ADR-272 |
| [248](ADR-248-periodic-reviewer-pulse.md) | Periodic Reviewer Pulse | Live · D1/D2 → ADR-261 |
| [251](archive/ADR-251-system-agent-reviewer-first-class-surfaces.md) | System Agent + Reviewer as First-Class Surfaces | ⛔ Superseded by ADR-272 |
| [252](archive/ADR-252-reviewer-primary-intelligence.md) | Reviewer as Primary Intelligence | ⛔ Superseded by ADR-256 |
| [253](ADR-253-reviewer-substrate-native-agent.md) | Reviewer as Substrate-Native Agent | Live · D5 → ADR-296 |
| [254](ADR-254-file-format-discipline.md) | File Format Discipline — Prose vs. Structured Data | **★ Live (the .md/.yaml rule)** |
| [256](ADR-256-unified-reviewer-invocation.md) | Unified Reviewer Invocation | Implemented |
| [258](ADR-258-reviewer-as-personified-chat-mode-operator.md) | Reviewer as Personified Chat-Mode Operator | Implemented |
| [274](ADR-274-reviewer-cadence-self-awareness.md) | Trigger-Authoring Implementation | Implemented |
| [275](ADR-275-introspection-cadence-reviewer-authored.md) | Introspection Cadence is Reviewer-Authored | Implemented |
| [276](ADR-276-reactive-trigger-envelope-governance-preload.md) | Reactive-Trigger Envelope Governance Pre-Load | Implemented |
| [284](ADR-284-standing-intent-substrate-and-occupant-envelope.md) | Standing Intent as First-Class Reviewer Substrate | Implemented |
| [285](ADR-285-holistic-wake-envelope.md) | Holistic Wake Envelope | Live · D1–D4 → ADR-301 |
| [290](ADR-290-reviewer-lifecycle-posture-and-residue-cleanup.md) | Reviewer Lifecycle Posture in Principles | Implemented |
| [295](ADR-295-reviewer-self-amendment-discipline.md) | Reviewer Self-Amendment Discipline | Implemented |
| [301](ADR-301-reviewer-pulse-envelope.md) | Reviewer Pulse Envelope | Implemented |
| [302](ADR-302-prompt-envelope-discipline.md) | Prompt-Envelope Discipline | Implemented |
| [303](ADR-303-reviewer-posture-taxonomy.md) | Reviewer Posture Taxonomy | Implemented |
| [305](ADR-305-principles-md-rewrite-against-partition-discipline.md) | `principles.md` Rewrite Against Partition Discipline | Implemented |
| [306](ADR-306-persona-frame-collapse.md) | Persona-Frame Collapse (~36K → ~3.5K) | **★ Implemented** |
| [314](ADR-314-substrate-conditional-posture.md) | Substrate-Conditional Posture | Implemented |
| [315](ADR-315-reviewer-occupant-contract.md) | Reviewer Occupant Contract (seat ≠ occupant) | **★ Implemented** |
| [318](ADR-318-agentic-wake-posture.md) | Agentic Wake Posture — a wake is a situation | Implemented |
| [319](ADR-319-stewardship-of-intent-against-ground-truth.md) | Stewardship of Intent against Ground Truth (DP24) | **★ Implemented** |
| [216](ADR-216-orchestration-surface-vs-judgment-persona.md) | Orchestration Surface vs Judgment Persona | **★ Live taxonomy (see LAYER-MAPPING)** |
| [272](ADR-272-identity-collapse-system-agent-and-specialist.md) | Identity-Layer Collapse — System Agent + Specialist | **★ Implemented** |
| [326](ADR-326-denaming-the-personified-judgment-seat.md) | De-naming the Judgment Seat ("Reviewer" → relabel) | Draft |

### Wake architecture + budget/pace (248, 296, 298, 300, 313, 327, 359–364)

Event-driven wake, the queue/drainer, and cost governance collapsing to one `_budget.yaml`.

| ADR | Title | Status |
|-----|-------|--------|
| [296](ADR-296-continuous-judgment-cycle.md) | Wake Is Event-Driven and Evaluation-Gated | **★ Implemented (v2)** |
| [298](ADR-298-reviewer-wake-queue-and-pace.md) | Reviewer Wake Queue + Pace Dial | **★ Implemented** |
| [300](archive/ADR-300-pace-as-atomic-kernel-surface.md) | Pace as Atomic Kernel Surface | ⛔ Superseded by ADR-327 |
| [313](archive/ADR-313-fire-frequency-gate-partition.md) | Fire-Frequency Gate Partition | ⛔ Superseded by ADR-327 |
| [327](ADR-327-budget-and-the-self-improving-loop.md) | Budget and the Self-Improving Loop — Pace Retires | **★ Implemented** |
| [359](archive/ADR-359-the-occasion-of-work-wake-shape.md) | The Occasion of Work — Wake-Shape as Computed Structure | ⛔ Superseded by ADR-360 |
| [360](ADR-360-the-wake-is-a-pre-authored-ask.md) | A Wake Is a Pre-Authored Ask | **★ Implemented (the ask re-founding)** |
| [361](ADR-361-verdict-rule-binding.md) | Verdict→Rule Binding | Proposed |
| [362](ADR-362-inspector-auditor-seat.md) | The Inspector/Auditor Seat | Proposed |
| [363](ADR-363-wake-context-handling.md) | Wake Context Handling — cross-wake memory | Accepted |
| [364](ADR-364-the-reflection-organ.md) | The Reflection Organ — close the intent→outcome loop | Accepted |

### Permission / cost / pricing (291–293, 307, 334, 391, 396, 409, 416)

One gate, one ledger, and the long pricing arc.

| ADR | Title | Status |
|-----|-------|--------|
| [291](ADR-291-unified-cost-ledger.md) | Unified Cost Ledger | **★ Implemented (one ledger)** |
| [292](ADR-292-continuous-substrate-reapply.md) | Operator-Initiated Versioned Substrate Update | Implemented |
| [293](ADR-293-governance-operational-substrate-taxonomy.md) | Governance / Operational Substrate Taxonomy | Implemented |
| [307](ADR-307-unified-permission-taxonomy.md) | Unified Permission Taxonomy (DP23) | **★ Implemented (one gate)** |
| [334](archive/ADR-334-per-operation-pricing.md) | Per-Operation Pricing — Delegation-Tiered Seats | ⛔ Superseded by ADR-396 (launch model) |
| [391](ADR-391-budget-balance-and-the-three-layer-cost-model.md) | Budget, Balance, and the Three-Layer Cost Model | Live · pricing D4/D6 → ADR-396 |
| [396](ADR-396-the-pricing-model-type-b-subscription-over-the-metered-balance.md) | The Pricing Model — Type-B Subscription | **★ Implemented** · pricing shape → ADR-409 |
| [409](ADR-409-per-seat-type-b-pricing.md) | Per-Seat Type-B Pricing | Accepted · demand-gated |
| [416](ADR-416-the-workspace-as-billing-unit-and-the-witness-metering-split.md) | The Workspace as the Billing Unit + Witness/Metering | **★ Implemented** |

### Interop / moat (169-era → 310–311, 368, 371–372, 379)

The one moat, two faces; the memory-first interop surface.

| ADR | Title | Status |
|-----|-------|--------|
| [310](ADR-310-judged-substrate-interop-face.md) | Judged Substrate, Served Everywhere | Live · D5 amended by ADR-373 |
| [311](archive/ADR-311-primitive-interop-surface.md) | The Primitive Interop Surface | ⛔ Superseded by ADR-368 |
| [368](ADR-368-memory-first-interop-surface.md) | The Memory-First Interop Surface — remember / recall / trace | **★ Live endpoint** |
| [402](ADR-402-model-routing-as-kernel-data.md) | Model Routing as Kernel Data (Freddie on Sonnet) | Implemented |
| [403](ADR-403-the-envelope-collapse-lands.md) | The Envelope Collapse Lands | Implemented |
| [371](ADR-371-mcp-self-contained-auth-boundary.md) | The MCP Service as a Self-Contained Auth Boundary | Implemented |
| [372](ADR-372-presentation-affordances-interop-face.md) | Presentation Affordances on the Interop Face (ChatGPT widget) | Implemented |
| [379](ADR-379-host-profiles-the-interop-reach-registry.md) | Host Profiles — the Interop-Reach Registry | Implemented |

### Ground-truth + perception + programs (195-era → 267, 282–283, 287, 317, 330, 332, 335–336, 342–345, 353–357)

Ground-truth substrate, the perception field, dormancy/aperture/standing-obligation, external hands.

| ADR | Title | Status |
|-----|-------|--------|
| [267](ADR-267-pnl-unification-money-truth-substrate.md) | P&L Unification + Money-Truth Substrate Collapse | Implemented |
| [282](ADR-282-axiom-8-ground-truth-rename.md) | Axiom 8 — Ground-Truth Substrate Rename | Implemented |
| [283](ADR-283-alpha-author-bundle.md) | alpha-author Bundle (second program) | Implemented |
| [287](ADR-287-bundle-conformance-discipline.md) | Bundle Conformance Discipline | Implemented |
| [330](ADR-330-ground-truth-intake.md) | Ground-Truth Intake — beyond platform APIs | Implemented |
| [332](ADR-332-four-flow-completeness-model.md) | Four-Flow Operation Completeness Model (DP26) | Accepted (framing) |
| [335](ADR-335-perception-field.md) | The Perception Field (Axiom 1 §8 + DP27) | **★ Implemented** |
| [336](ADR-336-web-rss-standing-watch.md) | The Web/RSS Standing Watch — TrackWebSources | Implemented |
| [342](ADR-342-dormancy-as-ground-truth-evidence.md) | Dormancy as Ground-Truth Evidence (DP24 v9.6) | Implemented |
| [343](ADR-343-aperture-floor-as-kernel-derivable-principle.md) | Aperture/Floor as a Kernel-Derivable Principle (DP24 v9.7) | Implemented |
| [344](ADR-344-standing-obligation-operability-self-check.md) | The Standing Obligation (DP30 v9.8) | Implemented |
| [345](ADR-345-expected-output-contract.md) | Expected Output — the declared output contract | Implemented |
| [353](ADR-353-composio-as-driver-backend.md) | Composio as the Driver Backend for External Hands | Accepted |
| [354](ADR-354-recurrence-prompt-collapse-and-perception-field-discipline.md) | Recurrence-Prompt Collapse + Perception-Field Discipline | Implemented |
| [355](ADR-355-the-agent-authors-full-autonomy-full-accountability.md) | The Agent Authors — Full Autonomy, Full Accountability | Implemented |
| [356](ADR-356-trackforeign-repo-watch-crawl-b-increment-b.md) | TrackForeign + the Repository Watch | Implemented |
| [357](ADR-357-citation-binds-to-source-not-internal-path.md) | A Citation Binds a Claim to its Source | Implemented |

### Surfaces / experience / management plane (213–215, 236–246, 259, 265–266, 277, 288–289, 297, 308–309, 316, 329, 331, 337–341, 346–352, 358, 365–370, 374, 377, 385, 387–388, 398–400, 410, 415, 418–422)

The compositor-era FE frontier — surfaces mirror substrate, the management plane, Files, the operator experience model.

| ADR | Title | Status |
|-----|-------|--------|
| [213](ADR-213-surface-pull-composition.md) | Surface-Pull Composition | Implemented |
| [214](ADR-214-agents-page-consolidation.md) | Agents Page Consolidation | Implemented |
| [215](ADR-215-surface-contracts-and-crud-principles.md) | Surface Contracts and CRUD Principles | Implemented |
| [236](ADR-236-frontend-cockpit-coherence-pass.md) | Frontend Cockpit Coherence Pass (umbrella) | Implemented |
| [237](ADR-237-chat-role-based-design-system.md) | Chat Role-Based Design System | Live · visual grammar → ADR-258 |
| [240](archive/ADR-240-onboarding-as-activation.md) | Onboarding as Activation | ⛔ Superseded by ADR-244 |
| [244](ADR-244-workspace-settings-surface.md) | Workspace Settings Surface — Program Lifecycle | Implemented |
| [245](ADR-245-frontend-kernel-three-layer-content-rendering.md) | Frontend Kernel — Three-Layer Content Rendering | **★ Live FE kernel model** |
| [259](ADR-259-feed-surface.md) | Feed Surface | Implemented |
| [277](ADR-277-feed-emission-policy.md) | Feed Emission Policy — One Canonical Home | Implemented |
| [289](ADR-289-feed-and-conversation-surfaces.md) | Feed and Conversation Surfaces (render grammars) | Implemented |
| [297](ADR-297-surfaces-as-substrate-mirror.md) | Surfaces as Substrate Mirror | **★ Implemented** |
| [308](ADR-308-redirect-stubs-as-pure-transport.md) | Redirect Stubs as Pure Transport | Implemented |
| [309](ADR-309-two-registers-settings-and-applications.md) | Two Registers — Settings and Applications | Implemented |
| [316](ADR-316-chat-as-dockable-rail.md) | Chat as a Dockable Rail | Implemented |
| [329](ADR-329-files-as-first-class-work-legibility-surface.md) | Files as the Operator's Substrate Surface | Implemented |
| [331](ADR-331-setup-as-rendering.md) | Setup-as-Rendering — the `/setup` Sequence Surface | Implemented |
| [337](ADR-337-file-layer-verb-completion.md) | File-Layer Verb Completion | Implemented |
| [338](ADR-338-management-plane.md) | The Management Plane (DP28) | **★ Implemented** |
| [339](ADR-339-working-tree-perception-economics.md) | Working-Tree Perception Economics | Implemented |
| [340](ADR-340-operator-experience-model.md) | The Operator Experience Model (DP29) | **★ Accepted (capstone)** |
| [341](ADR-341-two-settings-doors.md) | Two Settings Doors | Implemented · → ADR-347 |
| [346](ADR-346-operation-composition-surface.md) | The Operation Surface — a composition window | Implemented |
| [347](ADR-347-one-settings-door-account-to-usermenu.md) | One Settings Door | Implemented |
| [349](ADR-349-launcher-ia-re-sort.md) | Launcher IA Re-Sort | Implemented |
| [358](ADR-358-layout-mode-canvas-vs-desktop.md) | Layout Mode — Canvas vs Desktop | Implemented |
| [365](ADR-365-register-follows-consumer.md) | Register Follows Consumer | Implemented |
| [367](ADR-367-home-as-operating-cockpit.md) | Home as Operating Cockpit | Implemented |
| [369](ADR-369-home-split-front-page-and-program-cockpit.md) | The Home Split — kernel front page + program cockpit | Implemented |
| [370](ADR-370-context-surface-the-operations-boundary.md) | Context — the operation's boundary surface | Implemented · → ADR-385/415 |
| [377](ADR-377-context-as-the-perception-home.md) | Context as the Perception Home | Live · amended by ADR-385 |
| [385](ADR-385-channels-the-perception-and-principal-surface.md) | Channels — the perception + principal surface | Implemented · → ADR-415 |
| [388](ADR-388-files-as-a-filesystem-native-surface.md) | Files as a Filesystem-Native Surface | Implemented |
| [398](ADR-398-chat-legibility-tool-detail-locator-linkification.md) | Chat Legibility | Implemented |
| [399](ADR-399-the-turn-artifact-append-only-within-one-narrative-entry.md) | The Turn Artifact — Append-Only | Implemented |
| [400](ADR-400-the-two-principal-files-surface.md) | The Two-Principal Files Surface | Implemented |
| [410](ADR-410-attention-derives-from-the-timeline.md) | Attention Derives From the Timeline | Live · one dial → ADR-412 |
| [415](ADR-415-dissolve-channels-activity-is-the-what-happened-surface.md) | Dissolve Channels — Activity is the one "what happened" surface | **★ Implemented** |
| [418](ADR-418-system-agent-pane-purification-freddie-owns-only-its-dials.md) | System-Agent Pane Purification | Implemented |
| [419](archive/ADR-419-constitution-is-per-agent-the-workspace-has-no-constitution.md) | Constitution Is Per-Agent | ⛔ Superseded by ADR-421 |
| [421](ADR-421-the-workspace-has-no-constitution-surface.md) | The Workspace Has No Constitution Surface | **★ Implemented** |
| [422](ADR-422-files-surface-non-editable-state-affordances.md) | Files-Surface Non-Editable-State Affordances | Proposed |

### Interop-first launch + multi-principal + re-founding (373–384, 389–390)

The launch arc: the substrate served to external agents, the `user_id → workspace_id` re-key, and the first-principles re-founding.

| ADR | Title | Status |
|-----|-------|--------|
| [373](ADR-373-multi-principal-workspace-and-the-re-key.md) | The Multi-Principal Workspace + the `user_id → workspace_id` re-key | **★ Accepted (foundational pre-launch)** |
| [374](ADR-374-presentation-ia-substrate-face-and-the-steward-posture.md) | Presentation IA — the Substrate Face + the Steward Posture | Accepted |
| [375](ADR-375-phase-1-substrate-for-humans-and-external-agents.md) | Phase 1 — Substrate Operated by Humans AND External Agents | Accepted · refined by ADR-380 |
| [376](ADR-376-ledger-intake-raw-observation-vs-derived-substrate.md) | Ledger Intake — Raw Observation vs Derived Substrate (DP32) | **★ Implemented** |
| [378](ADR-378-the-workspace-as-the-outermost-unit.md) | The Workspace is the Outermost Unit | Accepted |
| [380](ADR-380-the-activation-ladder-and-the-judgment-deferral-line.md) | The Activation Ladder — the Judgment Deferral Line | **★ Accepted (launch posture)** |
| [381](ADR-381-freddie-the-rung-1-substrate-steward.md) | Freddie — the Rung-1 Substrate Steward | **★ Accepted** |
| [382](ADR-382-persona-agent-seats-the-rung-2-judgment-layer.md) | Persona-Agent Seats — the Rung-2 Judgment Layer | Accepted (deferred, name-only) |
| [383](ADR-383-the-consistent-agent-framework-and-mandate-as-purpose.md) | The Consistent Agent Framework + MANDATE as Purpose | Proposed |
| [384](ADR-384-the-re-founding-meaning-folders-permission-as-metadata.md) | The Re-Founding — Meaning-Folders, Permission as Metadata | Doc-direction (not ratified) |
| [386](ADR-386-workspace-members-the-grant-lifecycle.md) | Workspace Members — the Grant Lifecycle | Implemented |
| [387](ADR-387-agent-governance-on-the-agent-pane.md) | Agent Governance on the Agent's Pane | Implemented |
| [389](ADR-389-principal-vs-peripheral-and-the-steward-shaped-envelope.md) | Principal vs Peripheral + the Steward-Shaped Envelope | Implemented |
| [390](ADR-390-the-steward-envelope-removal-pass.md) | The Steward Envelope Removal Pass | **★ Implemented** |

### Connectors / capture (392–395, 401)

The connector lane + capture pipeline — **DORMANT** behind `CONNECTOR_CAPTURE_ENABLED` (ADR-404).

| ADR | Title | Status |
|-----|-------|--------|
| [392](ADR-392-the-connector-lane.md) | The Connector Lane | Implemented · lane dormant |
| [393](ADR-393-the-perception-capture-pipeline.md) | The Perception/Capture Pipeline | Implemented · lane dormant |
| [394](ADR-394-connector-capture-the-reader.md) | Connector Capture — the Reader | Implemented · lane dormant |
| [395](ADR-395-model-consumable-projection-and-upload-intake-conformance.md) | The Model-Consumable Projection + Upload Intake | Implemented |
| [401](ADR-401-the-connection-lifecycle.md) | The Connection Lifecycle — the peripheral as first-class | Proposed |

### The coworking week + pure workspace (404–414, 417, 420, 423–425) — **the live frontier**

The commons-first launch, the witness dial, the three altitudes/chromes, the pure workspace (program-as-hire), and rented engines. **Read [ADR-414](ADR-414-the-pure-workspace-genesis-system-agent-program-as-hire.md) first — it's the umbrella.**

| ADR | Title | Status |
|-----|-------|--------|
| [404](ADR-404-the-commons-first-launch.md) | The Commons-First Launch — the capture lane goes dormant | **★ Accepted** |
| [405](ADR-405-the-witness-dial.md) | The Witness Dial — permission=grant, autonomy=witness-timing | **★ Accepted** |
| [406](ADR-406-stale-parent-rejection.md) | Stale-Parent Rejection (optimistic concurrency) | Implemented |
| [407](ADR-407-the-three-scope-taxonomy.md) | The Three-Scope Taxonomy (DP35) | **★ Implemented** |
| [408](ADR-408-the-coworking-contract-and-the-three-ai-altitudes.md) | The Coworking Contract + the Three AI Altitudes | **★ Accepted** |
| [411](ADR-411-chat-lanes-and-the-lane-tool-surface.md) | Chat Lanes and the Lane Tool Surface | Accepted |
| [412](ADR-412-three-altitudes-three-chromes.md) | Three Altitudes, Three Chromes | **★ Accepted** |
| [413](ADR-413-invocation-contract-protocol-drivers-workspace-runtime.md) | The Invocation Contract + Protocol Drivers + Workspace Runtime | **★ Accepted (doc-first)** |
| [414](ADR-414-the-pure-workspace-genesis-system-agent-program-as-hire.md) | The Pure Workspace — Genesis, System Agent, Program-as-Hire | **★ Accepted (umbrella)** |
| [417](ADR-417-retire-the-render-service-generation-is-rented-not-owned.md) | Retire the Render Service — Generation is Rented | Accepted |
| [420](ADR-420-engine-breadth-vs-connector-breadth.md) | Engine Breadth vs Connector Breadth | Accepted · engines shipped, connectors paused |
| [423](ADR-423-revision-kind-the-observation-derivation-flag.md) | `revision_kind` — the observation/derivation flag | Accepted |
| [424](ADR-424-the-pure-os-filesystem-model-for-all-participants.md) | The Pure-OS Filesystem Model for All Participants | Accepted |
| [425](ADR-425-the-credential-is-an-account-object.md) | The Credential Is an Account Object | Proposed |
| [426](ADR-426-freddie-system-agent-its-own-settings-door.md) | Freddie System Agent — Its Own Settings Door | Accepted |
| [429](ADR-429-the-three-axis-pricing-model-workspace-base-human-seats-pooled-meter.md) | The Three-Axis Pricing Model — Workspace Base · Human Seats · Pooled Meter | Accepted |

> **ADRs not listed above** (a handful of intermediate steps: 217, 234, 238–239, 241, 243, 246, 249–250, 255, 264–266, 271–272, 281, 288, 294, 299, 304, 366, 397, 402–403) exist in `docs/adr/` and are Implemented/absorbed intermediate decisions — read the file directly if you touch that surface.

---

### Canonical Terminology

| Document | Purpose |
|----------|---------|
| [GLOSSARY.md](../architecture/GLOSSARY.md) | **Canonical terminology** (ratified by ADR-189). One word, one concept, one layer. |

## Canonical Architecture Docs (the spine — read these before the ADRs)

The ADRs are the decision log; the spine documents are the canon. For product/architecture questions, read the spine first:

| Document | Purpose |
|----------|---------|
| [ESSENCE.md](../ESSENCE.md) | Product essence + the moat (v15 — the system of record where human and AI work settles) |
| [THESIS.md](../architecture/THESIS.md) | The four commitments + the two-order re-derivation |
| [FOUNDATIONS.md](../architecture/FOUNDATIONS.md) | Six dimensions, the axioms, the derived principles (live canon) |
| [LAYER-MAPPING.md](../architecture/LAYER-MAPPING.md) | The three AI altitudes — the authoritative acting-entity taxonomy |
| [SERVICE-MODEL.md](../architecture/SERVICE-MODEL.md) | The execution/service model |
| [GLOSSARY.md](../architecture/GLOSSARY.md) | Canonical terminology — one word, one concept, one layer |
| [reviewer-seat-substrate.md](../architecture/reviewer-seat-substrate.md) | The judgment seat canon |
| [primitives-matrix.md](../architecture/primitives-matrix.md) | The live primitive reference (substrate × mode × capability) |

## Conventions

- **Sequential numbering** — don't reuse numbers; ADRs are an immutable decision log.
- **Mark superseded ADRs on the Status line**: `Status: Superseded by ADR-XXX` (a ⚠ banner at the top is good, but the *Status line* must also carry it so a status grep catches it — that discipline lapsed across 209–425 and was re-applied 2026-07-09).
- **Whole-ADR supersession** → stamp `Superseded`; **partial** (a clause/mechanism only) → keep the ADR live and note `Live · <clause> → ADR-N`.
- **Archive when fully absorbed** — move to `archive/` only when the entire ADR is dead history *and* nothing references it as a live clause. When in doubt, stamp in place; don't move (moving breaks path references).
- **Group by arc, not number** — the modern-era index above is grouped by concern; keep new ADRs in their arc.
- **Reference the spine** (above) for living specifications, not the ADRs.

## Full index — ADRs not covered by the curated arcs above

The arc-grouped index above is *curated*: it carries the supersession verdicts and
the arc endpoints. It does not list every ADR. The table below closes that gap so
no decision is invisible — **228 ADRs, including the entire 428→565 band, were
absent from this file before 2026-08-13.** Rows here are title-only: for an ADR's
status, open it. When an ADR earns a verdict (⛔ superseded, ★ endpoint), promote
it into the arc index above rather than annotating it here.

| ADR | Title |
|-----|-------|
| [128](ADR-128-multi-agent-coherence-protocol.md) | Multi-Agent Coherence Protocol |
| [129](ADR-129-activity-scoping-two-tier-model.md) | Activity Scoping — Two-Tier Model |
| [130](ADR-130-html-native-output-substrate.md) | HTML-Native Output Substrate — Three-Registry Architecture |
| [131](ADR-131-gmail-calendar-sunset.md) | Gmail & Calendar Sunset — Platform Hierarchy Realignment |
| [139](ADR-139-workfloor-task-surface-architecture.md) | Workfloor + Task Surface Architecture |
| [141](ADR-141-unified-execution-architecture.md) | Unified Execution Architecture — Mechanical Scheduling, LLM Generation |
| [142](ADR-142-unified-filesystem-architecture.md) | Unified Filesystem Architecture |
| [143](ADR-143-agent-methodology-layer.md) | Agent Playbook Layer |
| [144](ADR-144-inference-first-shared-context.md) | Inference-First Shared Context |
| [145](ADR-145-task-type-registry-premeditated-orchestration.md) | Task Type Registry — Pre-Meditated Orchestration |
| [146](ADR-146-primitive-hardening.md) | Primitive Hardening — Consolidation & Design Principles |
| [147](ADR-147-github-platform-integration.md) | GitHub Platform Integration |
| [148](ADR-148-output-artifact-architecture.md) | Output Architecture — Assets, Composition, Repurpose |
| [149](ADR-149-task-lifecycle-architecture.md) | Task Lifecycle Architecture — TP as Context Manager |
| [151](ADR-151-shared-knowledge-domains.md) | Shared Context Domains — Workspace as Accumulated Intelligence |
| [152](ADR-152-unified-directory-registry.md) | Unified Directory Registry — Single Source of Truth for Workspace Filesystem |
| [153](ADR-153-platform-content-sunset.md) | Platform Content Sunset — Task-First External Data Flow |
| [154](ADR-154-execution-boundary-reform.md) | Execution Boundary Reform — Who / What / How File Separation |
| [155](ADR-155-workspace-inference-onboarding.md) | Workspace-Wide Inference & Onboarding Experience |
| [157](ADR-157-fetch-asset-skill.md) | Fetch-Asset Skill — External Asset Acquisition for Context Substrate |
| [158](ADR-158-external-context-access-authority-model.md) | External Context Access — Platform Bot Ownership Model |
| [159](ADR-159-filesystem-as-memory.md) | Filesystem-as-Memory — Referential Context Injection |
| [161](ADR-161-daily-update-anchor.md) | Daily Update as Anchor — The Heartbeat Artifact |
| [162](ADR-162-inference-hardening.md) | Inference Hardening — Evaluation, Gap Detection, Upload Triggering, Visibility |
| [163](ADR-163-surface-restructure.md) | Surface Restructure — Chat as Home, Work as First-Class, Activity Absorbed |
| [165](ADR-165-workspace-state-surface.md) | Workspace State Surface |
| [167](ADR-167-list-detail-surfaces.md) | List/Detail Surfaces with Kind-Aware Detail |
| [168](ADR-168-primitive-matrix.md) | Primitive Matrix — Two Axes, Entity/File/Action Families, Finish ADR-146 |
| [169](ADR-169-mcp-context-hub.md) | MCP as Context Hub — Three-Tool Surface for Cross-LLM Continuity |
| [170](ADR-170-compose-substrate.md) | Compose Substrate — Filesystem-to-Output Assembly Layer |
| [171](ADR-171-token-spend-metering.md) | Token Spend Metering — Universal Usage-Based Pricing |
| [172](ADR-172-usage-first-billing.md) | Usage-First Billing — Balance Model |
| [173](ADR-173-accumulation-first-execution.md) | Accumulation-First Execution |
| [174](ADR-174-filesystem-native-workspace.md) | Filesystem-Native Workspace — Discovery, Search, and Conventions |
| [177](ADR-177-section-kind-rendering.md) | Section Kind Rendering — Unified Parse+Render |
| [178](ADR-178-task-creation-routes.md) | Task Creation Routes — Context-Driven and Output-Driven Scaffolding |
| [179](ADR-179-system-event-cards.md) | System Event Cards — Chat as Event Log |
| [180](ADR-180-work-context-surface-split.md) | Work/Context Surface Split — Task-Scoped vs. Workspace-Scoped |
| [181](ADR-181-source-agnostic-feedback-layer.md) | Source-Agnostic Feedback Layer |
| [182](ADR-182-pre-gather-pipeline-optimization.md) | Pre-Gather Pipeline Optimization — Mechanical Context Assembly |
| [183](ADR-183-commerce-substrate.md) | Commerce Substrate — Provider-Agnostic Business Layer |
| [184](ADR-184-product-health-metrics.md) | Product Health Metrics — Revenue as First-Class Perception |
| [185](ADR-185-distribution-derivatives.md) | Distribution Derivatives — Rich Post-Pipeline Repackaging |
| [187](ADR-187-trading-integration-alpaca.md) | Trading Integration — Alpaca as Execution Platform |
| [190](ADR-190-inference-driven-scaffold-depth.md) | Inference-Driven Scaffold Depth |
| [191](ADR-191-polymath-operator-icp-domain-stress-discipline.md) | Polymath Operator ICP + Domain Stress Discipline |
| [192](ADR-192-write-primitive-coverage-expansion.md) | Write Primitive Coverage Expansion — Trading Sophistication + Risk Gate + Commerce Ops + |
| [193](ADR-193-propose-action-approval-loop.md) | ProposeAction Primitive + Approval Loop |
| [194](ADR-194-pluggable-reviewer-and-impersonation.md) | Reviewer Layer + Operator Impersonation |
| [195](ADR-195-outcome-attribution-substrate.md) | Money-Truth Substrate — `_performance.md` as Canonical Home |
| [196](ADR-196-user-memory-table-sunset.md) | `user_memory` Table Sunset |
| [197](ADR-197-filesystem-documents-migration.md) | `filesystem_documents` → `/workspace/uploads/` Migration |
| [198](ADR-198-surface-archetypes.md) | The Cockpit — Operator-Centric Service Model + Surface Archetypes |
| [199](ADR-199-overview-surface.md) | Overview Surface — Cockpit Home (`/overview`) |
| [200](ADR-200-review-surface.md) | Review Surface — Reviewer Identity + Principles + Decisions Chronicle |
| [201](ADR-201-team-rename-and-cross-linking.md) | Team Destination — `/agents` → `/team` Rename + Work Cross-Linking |
| [202](ADR-202-external-channel-discipline.md) | External Channel Discipline — Expository Pointers, No Replacement UX |
| [203](ADR-203-first-run-guidance-layer.md) | First-Run Guidance Layer — Overview as the Cold-Start Surface |
| [204](ADR-204-workspace-intelligence-cockpit.md) | Workspace Intelligence Cockpit — Overview as Synthesis Surface |
| [217](ADR-217-workspace-autonomy-substrate.md) | Workspace Autonomy Substrate — Single Authoring Mouth for Delegation |
| [219](ADR-219-invocation-narrative-implementation.md) | Invocation and Narrative — Implementation |
| [221](ADR-221-layered-context-strategy.md) | Layered Context Strategy — Filesystem-Native Narrative Rollup + In-Session Compaction Su |
| [234](ADR-234-chat-file-layer-reach.md) | Chat File Layer Reach — Read/Write/Search/List on workspace_files |
| [238](ADR-238-autonomy-mode-fe-consumption.md) | Autonomy-Mode FE Consumption — Shared Parser, Hook, First Consumer |
| [239](ADR-239-trader-cockpit-coherence-pass.md) | Trader Cockpit Coherence Pass — Decisions Parser Unification |
| [241](ADR-241-single-cockpit-persona.md) | Single Cockpit Persona — Reviewer Collapses Into Thinking Partner |
| [243](ADR-243-schedule-surface.md) | Schedule Surface — Cadence-Framed Sibling of /work |
| [246](ADR-246-tp-meta-awareness-workspace-surface.md) | TP Meta-Awareness of the Workspace Settings Surface |
| [249](ADR-249-operator-primary-runtime.md) | Operator as Primary Runtime Entity — Autonomy as User Approval Degree |
| [249](ADR-249-two-intent-file-handling.md) | Two-Intent File Handling — Ephemeral vs Persistent |
| [250](ADR-250-execution-telemetry.md) | Execution Telemetry — Sentry + Postgres Event Ledger + Spend Guard |
| [255](ADR-255-narrative-surface-simplification.md) | Narrative Surface Simplification |
| [264](ADR-264-substrate-canonical-world-and-syncplatformstate.md) | Substrate-Canonical-World — External State Mediation as Mechanical Primitives |
| [265](ADR-265-activity-surface-rename-and-mode-discriminator.md) | Activity Surface Rename + Mode Discriminator on execution_events |
| [266](ADR-266-workspace-surface-content-discipline.md) | `/workspace` Surface: Content Discipline + Program Drawer Collapse |
| [271](ADR-271-bundle-and-identity-discipline.md) | Bundle Authoring Discipline + Identity-Layer Audit |
| [281](ADR-281-substrate-canonical-substrate-only-prompts.md) | Substrate-Canonical, Substrate-Only Prompts — The Kernel Does Not Compute for the Prompt |
| [288](ADR-288-caller-identity-as-auth-field.md) | Caller Identity as First-Class Auth Field + Vocabulary Closure Pass + Kernel Money-Truth |
| [294](ADR-294-operator-proxy-and-observation-discipline.md) | Operator-Proxy Capability + Observation Discipline |
| [299](ADR-299-kernel-universal-operator-addressing-capability.md) | Operator-Addressing System Infrastructure — `send_operator_email` |
| [304](ADR-304-operator-addressing-writes-generalization.md) | Operator-Addressing Writes Generalization — Slack DM + Notion Comment as System Infrastr |
| [317](ADR-317-daily-pnl-post-judgment-dispatcher.md) | Daily P&L Post-Judgment Dispatcher — Reviewer Triggers, Dispatcher Sends |
| [333](ADR-333-compose-as-lazy-projection.md) | Compose as a Lazy Projection: Rewiring the Orphaned Production Half |
| [348](ADR-348-expected-output-fe.md) | Expected Output, Operator-Facing: the contract pane in the one Settings door |
| [350](ADR-350-standing-obligation-as-rendered-surface.md) | The Standing Obligation as a rendered surface: the operation's owed-vs-actual, surfaced  |
| [351](ADR-351-in-flight-invocation-rendering.md) | In-flight invocation rendering: the operator watches the Reviewer reason, not a loading  |
| [352](ADR-352-ask-as-governance-derived-outcome.md) | Ask-vs-Act as a Governance-Derived Outcome (Clarify joins the uniform gate) |
| [366](ADR-366-autonomy-mode-as-execution-breadth.md) | Autonomy Mode as Execution Breadth: the grant/contract split |
| [397](ADR-397-addressed-turn-ceremony-right-sizing.md) | Addressed-Turn Ceremony Right-Sizing — the Wake Liturgy is Reactive-Scoped |
| [428](ADR-428-retire-the-eager-foreign-write-derive-wake.md) | Retire the Eager Foreign-Write Derive Wake |
| [430](ADR-430-system-agent-pane-purification-follow-on.md) | System Agent Pane Purification Follow-On (Autonomy · Budget · Activity) |
| [431](ADR-431-the-connecting-member-owns-the-mcp-grant.md) | The Connecting Member Owns the MCP Grant: Foreign-LLM Principals Are Per-Member, Not Per |
| [432](ADR-432-the-operation-group-resolution-brand-and-program-post-pure-workspace.md) | The OPERATION Group Resolution: Brand and Program Post-Pure-Workspace |
| [433](ADR-433-the-freddie-budget-pane-is-pace-not-a-dollar-envelope.md) | The Freddie Budget Pane Is Pace, Not a Dollar Envelope |
| [434](ADR-434-the-powerbox-read-write-scope-gate.md) | The Powerbox: the read+write, arbitrary-depth, two-axis scope gate |
| [435](ADR-435-delete-the-home-surface.md) | Delete the Home surface |
| [436](ADR-436-the-app-registry-frame-agnostic-renderers.md) | The App Registry: frame-agnostic renderers behind a code-seeded table |
| [437](ADR-437-the-activation-model-discovery-cold-landing-and-the-shared-artifact-wedge.md) | The Activation Model: Discovery, Cold Landing, and the Shared-Artifact Wedge |
| [438](ADR-438-the-layout-mode-collapse-two-modes-one-open-contract.md) | The Layout-Mode Collapse: two modes with honest jobs, one context-derived open contract |
| [439](ADR-439-byok-key-scope-and-the-enterprise-tier-gate.md) | BYOK key scope, the enterprise tier, and the pre-lane metering floor |
| [440](ADR-440-the-studio-the-first-authoring-app.md) | The Studio: the first authoring app (the second app class) |
| [441](ADR-441-the-conversation-mount-contract.md) | The conversation-mount contract: one thread renderer per altitude, citations resolve in  |
| [442](ADR-442-the-surface-bar-two-chrome-authorities.md) | The surface bar: two chrome authorities, one declaration contract |
| [443](ADR-443-the-artifact-write-render-slot.md) | The artifact-write render slot: a mount declares how a lane's writes render |
| [443](ADR-443-the-studio-axiomatic-model-blocks-layouts-seven-operations.md) | The Studio axiomatic model: blocks, layouts, and the seven operations |
| [444](ADR-444-the-mechanical-layer-executing-toolbar-and-slide-masters.md) | The mechanical layer: an executing toolbar, slide masters, and the two write paths |
| [445](ADR-445-the-two-axis-pricing-collapse-seats-and-the-pooled-meter.md) | The Two-Axis Pricing Collapse: Seats + the Pooled Meter |
| [446](ADR-446-the-studio-direct-edit-runtime.md) | The Studio direct-edit runtime: editing the projection, writing the source |
| [447](ADR-447-the-arrangement-layer-composition-grammar.md) | The arrangement layer: composition as a first-class, per-type, nested grammar |
| [448](ADR-448-the-reference-edge-derived-from-on-the-ledger.md) | The Reference Edge — `derived_from` on the Ledger, the Derive Step, and "Learn From" |
| [449](ADR-449-the-design-system-contract-skin-as-workspace-convention.md) | The Design-System Contract — Skin as a Workspace Convention, Cited by Reference |
| [450](ADR-450-the-derive-recipe-registry-learn-from.md) | The Derive-Recipe Registry — "Learn From" as a Kernel Verb with Kernel Recipes |
| [451](ADR-451-open-by-format-the-surface-owning-app.md) | Open-by-Format — the Surface-Owning App |
| [452](ADR-452-the-studio-landing-learn-from-as-a-creation-path.md) | The Studio Landing — "Learn From" Is a Creation Path, Not a File Operation |
| [453](ADR-453-the-studio-property-layer-tokens-design-tab-verbs.md) | The Studio property layer: tokens-not-pixels, the Design tab, and the grain-aligned verb |
| [454](ADR-454-the-two-verb-experience-converse-and-make-ambient-steward.md) | The Two-Verb Experience — Converse and Make, and the Ambient Steward |
| [455](ADR-455-document-grain-tokens-file-verbs-navigable-outline.md) | Document-grain tokens, the file-verb completion, and the navigator that earns its place |
| [456](ADR-456-the-studio-horizon-markdown-ruling-builder-grammar.md) | The Studio horizon: the markdown ruling, the Notion/builder gap carve, and the wave plan |
| [457](ADR-457-think-and-make-the-service-model.md) | Think and Make — the Service Model |
| [458](ADR-458-the-studio-hover-layer-and-the-one-settings-home.md) | The Studio hover layer and the one settings home |
| [459](ADR-459-the-artifact-reads-as-what-it-is.md) | The artifact reads as what it is: kind is lifted, name is the namespace, the format is n |
| [460](ADR-460-agents-one-concept-independent-facts-one-gate.md) | Agents: One Concept, Independent Facts, One Gate |
| [461](ADR-461-bounded-continuous-geometry-a-slide-has-a-frame.md) | Bounded-continuous geometry: a slide has a frame, a page has a viewport |
| [462](ADR-462-the-block-context-menu-and-the-metered-badge.md) | The block context menu: two entrances, one badge, a neutral page |
| [463](ADR-463-capability-not-vendor-the-model-agnostic-carve.md) | Capability, not Vendor: the model-agnostic carve |
| [464](ADR-464-skills-the-convention-without-the-engine.md) | Skills: the convention, without the engine that killed it |
| [465](ADR-465-share-the-membership-primitive-and-the-two-doors-unification.md) | Share: the membership primitive, and the two-doors unification |
| [466](ADR-466-the-mode-native-carve-one-grammar-n-native-editors.md) | The mode-native carve: one grammar, N native editors |
| [467](ADR-467-app-residency-and-the-cast.md) | App residency and the cast: apps have residents, the open surface offers the roster |
| [468](ADR-468-images-decomposed-generation-on-a-layered-object-substrate.md) | IMAGES: decomposed generation onto a layered object substrate |
| [469](ADR-469-the-name-is-lifted-the-path-is-a-key.md) | The name is lifted, the path is a key |
| [470](ADR-470-new-hands-over-the-workbench.md) | New hands over the workbench |
| [471](ADR-471-the-canvas-mode-a-staged-frame-for-composed-visuals.md) | The canvas mode: a staged frame for composed visuals |
| [472](ADR-472-images-as-a-first-class-app.md) | IMAGES as a First-Class App — the Housing Carve and the Composition→Raster Model |
| [473](ADR-473-document-types-and-open-with.md) | Document Types and "Open With" — LaunchServices for Artifacts |
| [474](ADR-474-content-inherits-the-files-scope.md) | Content inherits the file's scope |
| [475](ADR-475-decomposed-generation.md) | Decomposed generation: one prompt becomes a composition |
| [476](ADR-476-purge-is-workspace-scoped.md) | Purge is workspace-scoped, and its surfaces say so |
| [477](ADR-477-the-block-keyboard.md) | The block keyboard: an empty block closes, a selected block acts |
| [478](ADR-478-permanent-delete-and-the-trash-contract.md) | Permanent delete, and the Trash contract |
| [479](ADR-479-rearrange-as-planned-judgment.md) | Re-arrange as planned judgment: the AI places, the mechanism applies |
| [480](ADR-480-the-editing-grain-a-document-is-one-writing-surface.md) | The editing grain: a document is one writing surface |
| [481](ADR-481-the-flow-chrome-rebuild-a-blank-document-is-a-blank-page.md) | The flow chrome rebuild: a blank document is a blank page |
| [482](ADR-482-the-flow-completion-pass-insert-parity-and-the-mode-race.md) | The flow completion pass: insert parity, chrome scope, and the mode race |
| [483](ADR-483-the-name-is-what-the-member-typed.md) | The name is what the member typed: the lift's last caller, and the IME's Enter |
| [484](ADR-484-the-cue-that-boxed-prose-and-leaked-into-substrate.md) | The cue that boxed prose, and leaked into the substrate |
| [485](ADR-485-the-frame-a-percent-is-a-percent-of.md) | The frame a percent is a percent of |
| [486](ADR-486-ai-radar-the-standing-app.md) | AI Radar — the Standing App (Making Perceive Felt) |
| [487](ADR-487-the-design-system-reaches-the-editing-grammar.md) | The design system reaches the editing grammar: the playable ramp, semantic variants, and |
| [488](ADR-488-images-goes-internal-the-unveil-bar-is-polish-parity.md) | IMAGES Goes Internal: the Unveil Bar Is Polish Parity |
| [489](ADR-489-attention-weight-the-third-axis.md) | Attention Weight — the Third Axis of the One Derivation |
| [490](ADR-490-two-free-seats-and-the-payg-margin.md) | Two Free Seats + the Pay-As-You-Go Margin: the Allowance Retires |
| [491](ADR-491-the-settings-doors-recut.md) | The Settings Doors Re-Cut: Billing Behind the Workspace Door, the Governance Panes Colla |
| [492](ADR-492-chat-is-the-communication-app.md) | Chat Is the Communication App — Rooms, Mentions, Comments on One Conversation Grammar |
| [493](ADR-493-projects-the-co-work-state-desk.md) | Projects — the Co-Work State Desk, and the Work-Unit as a Declaration With an Owner |
| [494](ADR-494-the-connector-registry-and-the-door-that-opens-itself.md) | The Connector Registry Is Singular, and a Door Opens Itself |
| [495](ADR-495-the-conversation-one-object-one-cast.md) | The Conversation — One Object, One Cast, One Visibility Question |
| [496](ADR-496-a-members-own-connections-answer-on-the-account-door.md) | A Member's Own Connections Answer on the Account Door |
| [497](ADR-497-the-rendered-role-vocabulary-matches-what-can-exist.md) | The Rendered Role Vocabulary Matches What Can Exist |
| [498](ADR-498-the-invite-names-the-wrong-account-and-email-gets-a-shell.md) | The Invite Names the Wrong Account, and Transactional Email Gets One Shell |
| [499](ADR-499-a-stale-workspace-pin-self-heals.md) | A Stale Workspace Pin Self-Heals |
| [500](ADR-500-the-roster-follows-the-binding.md) | The Roster Follows the Binding, and a Failed Act Leaves No Orphan |
| [501](ADR-501-the-read-path-follows-the-binding-and-the-ceiling-follows-the-grant.md) | The Read Path Follows the Binding, and the Ceiling Follows the Grant |
| [502](ADR-502-a-conversation-with-people-is-direct.md) | A Conversation With People Is Direct: the Reply Set Derives From the Cast |
| [503](ADR-503-the-wallet-follows-the-grant.md) | The Wallet Follows the Grant: One Per-Role Billing Display |
| [504](ADR-504-the-interop-principal-invariant.md) | The Interop Principal Invariant: an External LLM Is a First-Class Principal in the Ledge |
| [505](ADR-505-the-three-type-cut-and-the-one-insert-grammar.md) | The three-type cut: one medium per type, one insert grammar |
| [506](ADR-506-the-insert-door.md) | The insert door: a button in the centre, one gesture underneath |
| [507](ADR-507-the-acts-are-open-think-make-perceive.md) | The acts are open: Think · Make · Perceive, and the pipeline retires |
| [508](ADR-508-the-gtm-canon-boundary.md) | The GTM-Canon Boundary: Where Marketing Canon and Kernel Canon Meet |
| [509](ADR-509-the-insert-route-follows-the-medium.md) | The insert route follows the medium: the slash is flow's, the mouse is paged's |
| [510](ADR-510-one-binary-lane-and-the-portability-export.md) | One binary lane, and the portability export ships |
| [511](ADR-511-the-conventional-substrate.md) | The conventional substrate: selection derives from structure, not from annotation |
| [512](ADR-512-the-file-is-the-unit-of-interop.md) | The File Is the Unit of Interop: One Verb Contract, Species-Blind, Bound Per Channel |
| [513](ADR-513-the-public-artifact-view.md) | The Public Artifact View: the Attribution Walk as the Landing Page |
| [514](ADR-514-the-file-verb-completion-duplicate-as-derivation.md) | The File-Verb Completion — Duplicate as Derivation |
| [515](ADR-515-addressing-is-not-granting.md) | Addressing Is Not Granting: the acts the Share button collapsed |
| [516](ADR-516-layout-is-one-mechanism-the-pane-convergence.md) | Layout is one mechanism: the pane convergence, and the legible container |
| [517](ADR-517-grants-govern-share-executes.md) | Grants govern, share executes: the workspace reach model made honest |
| [518](ADR-518-docs-and-studio-the-writing-app-and-the-layout-app.md) | Docs and Studio — the Writing App and the Layout App |
| [519](ADR-519-the-object-hierarchy-and-the-pane-grammar.md) | The object hierarchy is four grains, and the pane speaks one grammar |
| [520](ADR-520-the-stage-view-and-the-adjustable-container.md) | The stage view, the adjustable container, and the pane as the structure's home |
| [521](ADR-521-the-flow-benchmark-notions-scope-the-continuous-surfaces-mechanics.md) | The flow benchmark — Notion's scope, the continuous surface's mechanics |
| [522](ADR-522-the-focus-declaration-what-the-member-is-looking-at.md) | The focus declaration — what the member is looking at, declared once, spoken by every ap |
| [523](ADR-523-the-history-is-a-lineage-not-a-pile-of-snapshots.md) | The history is a lineage, not a pile of snapshots — undo/redo at the grain the member ed |
| [524](ADR-524-the-canvas-is-patched-not-rebuilt.md) | The canvas is patched, not rebuilt — and a judgment shows its work early |
| [525](ADR-525-the-selection-carries-its-tier.md) | The selection carries its tier — one answer, read by every surface |
| [526](ADR-526-the-document-shows-its-shape.md) | The document shows its shape — the outline the member never got |
| [527](ADR-527-the-emphasis-tier-read-off-the-bar.md) | The emphasis tier — read off the bar |
| [528](ADR-528-a-range-is-not-a-block-the-continuous-document.md) | A range is not a block: the continuous document |
| [529](ADR-529-one-share-act-one-link-two-readers.md) | One share act, one link, two readers |
| [530](ADR-530-the-projection-is-a-property-of-the-file.md) | The projection is a property of the file, and the link has a machine address |
| [531](ADR-531-the-shared-artifact-is-indexable.md) | The shared artifact is indexable: the conscious accommodation |
| [531](ADR-531-the-state-carries-itself-and-a-failure-is-visible.md) | The OAuth state carries itself, and a failed connection says so |
| [532](ADR-532-the-access-pane-shows-the-grant-that-exists.md) | The Access Pane Shows the Grant That Exists |
| [533](ADR-533-one-participant-contract-across-every-surface.md) | One Participant Contract: The Commons Etiquette Is Singular Across Every Surface |
| [534](ADR-534-the-share-link-is-a-standing-address.md) | The share link is a standing address, and an honest one when it breaks |
| [535](ADR-535-a-bound-connector-is-visible-to-the-members-lane.md) | A bound connector is visible to the member's lane |
| [536](ADR-536-the-list-is-a-kind-and-align-comes-home.md) | The list is a kind, and align comes home |
| [537](ADR-537-the-share-sheet-asks-what-you-are-doing.md) | The share sheet asks what you are doing: the link tab and the people tab |
| [538](ADR-538-a-block-is-classified-by-what-it-cites.md) | A block is classified by what it cites — and the motion ceiling is declarative |
| [539](ADR-539-the-vocabulary-declares-behavior.md) | The vocabulary declares behavior — a kind carries its tier, its tags, its conversions, a |
| [540](ADR-540-a-retired-document-does-not-commit.md) | A retired document does not commit — the teardown write-back |
| [541](ADR-541-the-selection-algebra-a-ranges-subjects-are-its-covered-blocks.md) | The selection algebra — a range's subjects are its covered blocks, and every verb entran |
| [542](ADR-542-a-token-declares-where-and-when-scope-and-grain.md) | A token declares WHERE and WHEN — `applies` splits into scope and grains |
| [543](ADR-543-the-interop-surface-speaks-the-kernel-verbs.md) | The interop surface speaks the kernel's verbs — remember/recall/trace retire into the fi |
| [544](ADR-544-the-containment-law-slide-layout-area-block.md) | The containment law — every block lives in an Area, and position is a place in the hiera |
| [545](ADR-545-the-interop-binding-completes-edit-delete-move-changes-honest-save.md) | The interop binding completes — edit · delete · move, a change feed, and the honest save |
| [546](ADR-546-the-rung-law-a-document-is-a-tree-of-text.md) | The rung law — a document is a tree of text, and the law forks from Studio's |
| [547](ADR-547-the-flow-write-grain-a-commit-reports-typing-not-everything.md) | The flow write grain — a commit reports TYPING, not everything |
| [548](ADR-548-the-scope-doorway-the-helper-existed-the-gate-did-not.md) | The scope doorway — the helper existed, the gate did not |
| [549](ADR-549-a-creation-act-names-its-object.md) | A creation act names its object |
| [550](ADR-550-the-members-pane-says-where-you-stand-and-the-dial-says-what-it-governs.md) | The members pane says where you stand, and the dial says what it governs |
| [551](ADR-551-autonomy-is-a-property-of-an-agent-not-of-the-workspace.md) | Autonomy is a property of an agent, not of the workspace |
| [552](ADR-552-direct-manipulation-where-members-look.md) | Direct manipulation where members actually look |
| [553](ADR-553-the-file-set-and-the-way-out-of-it.md) | The file set, and the way out of it |
| [554](ADR-554-the-derivation-follows-its-source.md) | A derivation follows its source, and hides by its edge |
| [555](ADR-555-arrival-has-a-here.md) | Arrival has a "here", and placement has one law |
| [556](ADR-556-systematic-calls-and-the-model-selection-boundary.md) | Systematic calls and the model-selection boundary |
| [557](ADR-557-the-router-chokepoint-and-the-transport-product-split.md) | The router chokepoint, and the transport/product split |
| [558](ADR-558-chat-is-the-engine-surface-agents-are-personified.md) | Chat is the engine surface; Agents are personified |
| [559](ADR-559-the-engine-registry-currency-retirement-availability.md) | The engine registry: currency, retirement, availability |
| [560](ADR-560-the-document-model-flow-editing-leaves-the-dom.md) | The document model — flow editing gets a model, and the DOM becomes a view |
| [561](ADR-561-the-marketing-surface-states-only-what-the-code-does.md) | The marketing surface states only what the code does |
| [562](ADR-562-an-apps-ai-configuration-is-declared-where-the-app-lives.md) | An app's AI configuration is declared where the app lives |
| [563](ADR-563-the-mcp-scope-authorizes-it-does-not-decorate.md) | The MCP scope authorizes; it does not decorate |
| [564](ADR-564-meaning-criterion-selection-the-context-frame.md) | Meaning · Criterion · Selection — the context frame for unattended intake |
| [565](ADR-565-the-living-report-radar-recut.md) | The Living Report — the radar re-cut, staged by source class |

## Archived ADRs (pre-209 history)

Decisions from earlier phases (ADR-001 → ADR-058, plus fully-superseded later decisions) are in [`archive/`](archive/) — preserved for historical reference. The pre-208 active index above covers the ADR-059 → 208 band; the modern-era index (209 → 425) is grouped by arc.
