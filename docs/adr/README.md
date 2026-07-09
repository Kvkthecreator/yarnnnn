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
| [072](ADR-072-unified-content-layer-tp-execution-pipeline.md) | Unified Content Layer & TP Execution Pipeline | **Superseded by ADR-153** |

### Platform Sync & Integrations

| ADR | Title | Status |
|-----|-------|--------|
| [075](ADR-075-mcp-connector-architecture.md) | MCP Connector Architecture | Implemented |
| [076](ADR-076-eliminate-mcp-gateway.md) | Eliminate MCP Gateway (Direct API) | Implemented |
| [077](ADR-077-platform-sync-overhaul.md) | Platform Sync Overhaul | **Superseded by ADR-153** |
| [085](ADR-085-refresh-platform-content-primitive.md) | RefreshPlatformContent Primitive | **Superseded by ADR-153** |
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
| [088](ADR-088-input-gateway-work-serialization.md) | Input Gateway & Work Serialization | Phase 1 Implemented |
| [090](ADR-090-work-tickets-consolidation.md) | Work Tickets Consolidation | Phases 1-3 Complete |
| [092](ADR-092-agent-intelligence-mode-taxonomy.md) | Agent Intelligence & Mode Taxonomy | Phase 5 Implemented |
| [101](ADR-101-agent-intelligence-model.md) | Agent Intelligence Model | Implemented |
| [102](ADR-102-yarnnn-content-platform.md) | Yarnnn Content Platform | Implemented |
| [103](ADR-103-agentic-framework-reframe.md) | Agentic Framework Reframe | Implemented |
| [104](ADR-104-agent-instructions-unified-targeting.md) | Agent Instructions as Unified Targeting | Implemented |
| [105](ADR-105-instructions-chat-surface-migration.md) | Instructions to Chat Surface Migration | Implemented |
| [109](ADR-109-agent-framework.md) | Agent Framework — Scope × Role × Trigger | Implemented (pending role rename) |

### Workspace, Skills & Output

| ADR | Title | Status |
|-----|-------|--------|
| [106](ADR-106-agent-workspace-architecture.md) | Agent Workspace Architecture | Phase 1 Complete |
| [107](ADR-107-knowledge-filesystem-architecture.md) | Knowledge Filesystem Architecture | Implemented |
| [108](ADR-108-user-memory-filesystem-migration.md) | User Memory Filesystem Migration | Implemented |
| [116](ADR-116-agent-identity-inter-agent-knowledge.md) | Agent Identity & Inter-Agent Knowledge | Implemented |
| [118](ADR-118-skills-as-capability-layer.md) | Skills as Capability Layer | Phase A+B+C Implemented, D Proposed |
| [119](ADR-119-workspace-filesystem-architecture.md) | Workspace Filesystem Architecture | Proposed |

### Composer & Agent Lifecycle

| ADR | Title | Status |
|-----|-------|--------|
| [110](ADR-110-onboarding-bootstrap.md) | Onboarding Bootstrap | Implemented |
| [111](ADR-111-agent-composer.md) | Agent Composer | Implemented (dissolved by ADR-156) |
| [114](ADR-114-composer-substrate-aware-assessment.md) | Composer Substrate-Aware Assessment | **Superseded by ADR-156** |
| [115](ADR-115-composer-workspace-density-model.md) | Composer Workspace Density Model | Proposed |
| [117](ADR-117-agent-feedback-substrate-developmental-model.md) | Agent Feedback Substrate & Developmental Model | Proposed (identity split clarified by ADR-189) |
| [156](ADR-156-composer-sunset-single-intelligence-layer.md) | Composer Sunset — Single Intelligence Layer | Phase 1 Implemented |

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
| [208](ADR-208-workspace-git-backend.md) | Workspace Git Backend for Operator-Authored Files | **Withdrawn (superseded by ADR-209)** |

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
| [328](ADR-328-substrate-portability-invariant.md) | Substrate Portability Invariant | Proposed |

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
| [228](ADR-228-cockpit-as-delegation-posture.md) | Cockpit as Operation — Four Faces | ⛔ Superseded by ADR-312 (framing) |
| [229](ADR-229-judgment-first-dispatch-and-generative-defer.md) | Judgment-First Dispatch + Generative Defer | Implemented |
| [230](ADR-230-persona-program-registry-unification.md) | Persona-Program Registry Unification | Implemented |
| [242](ADR-242-cockpit-bundle-components-alpha-trader-pass.md) | Cockpit Bundle Components — alpha-trader Pass | Implemented |
| [273](ADR-273-cockpit-refactor-program-section-split.md) | Cockpit Refactor — Kernel/Program Section Split | ⛔ Superseded by ADR-312 |
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
| [218](ADR-218-persona-reflection.md) | Persona Reflection — Reviewer Self-Evolution | ⛔ Superseded by ADR-256 |
| [247](ADR-247-three-party-narrative-model.md) | Three-Party Narrative Model | ⛔ Superseded by ADR-272 |
| [248](ADR-248-periodic-reviewer-pulse.md) | Periodic Reviewer Pulse | Live · D1/D2 → ADR-261 |
| [251](ADR-251-system-agent-reviewer-first-class-surfaces.md) | System Agent + Reviewer as First-Class Surfaces | ⛔ Superseded by ADR-272 |
| [252](ADR-252-reviewer-primary-intelligence.md) | Reviewer as Primary Intelligence | ⛔ Superseded by ADR-256 |
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
| [300](ADR-300-pace-as-atomic-kernel-surface.md) | Pace as Atomic Kernel Surface | ⛔ Superseded by ADR-327 |
| [313](ADR-313-fire-frequency-gate-partition.md) | Fire-Frequency Gate Partition | ⛔ Superseded by ADR-327 |
| [327](ADR-327-budget-and-the-self-improving-loop.md) | Budget and the Self-Improving Loop — Pace Retires | **★ Implemented** |
| [359](ADR-359-the-occasion-of-work-wake-shape.md) | The Occasion of Work — Wake-Shape as Computed Structure | ⛔ Superseded by ADR-360 |
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
| [334](ADR-334-per-operation-pricing.md) | Per-Operation Pricing — Delegation-Tiered Seats | ⛔ Superseded by ADR-396 (launch model) |
| [391](ADR-391-budget-balance-and-the-three-layer-cost-model.md) | Budget, Balance, and the Three-Layer Cost Model | Live · pricing D4/D6 → ADR-396 |
| [396](ADR-396-the-pricing-model-type-b-subscription-over-the-metered-balance.md) | The Pricing Model — Type-B Subscription | **★ Implemented** · pricing shape → ADR-409 |
| [409](ADR-409-per-seat-type-b-pricing.md) | Per-Seat Type-B Pricing | Accepted · demand-gated |
| [416](ADR-416-the-workspace-as-billing-unit-and-the-witness-metering-split.md) | The Workspace as the Billing Unit + Witness/Metering | **★ Implemented** |

### Interop / moat (169-era → 310–311, 368, 371–372, 379)

The one moat, two faces; the memory-first interop surface.

| ADR | Title | Status |
|-----|-------|--------|
| [310](ADR-310-judged-substrate-interop-face.md) | Judged Substrate, Served Everywhere | Live · D5 amended by ADR-373 |
| [311](ADR-311-primitive-interop-surface.md) | The Primitive Interop Surface | ⛔ Superseded by ADR-368 |
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
| [240](ADR-240-onboarding-as-activation.md) | Onboarding as Activation | ⛔ Superseded by ADR-244 |
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
| [419](ADR-419-constitution-is-per-agent-the-workspace-has-no-constitution.md) | Constitution Is Per-Agent | ⛔ Superseded by ADR-421 |
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

## Archived ADRs (pre-209 history)

Decisions from earlier phases (ADR-001 → ADR-058, plus fully-superseded later decisions) are in [`archive/`](archive/) — preserved for historical reference. The pre-208 active index above covers the ADR-059 → 208 band; the modern-era index (209 → 425) is grouped by arc.
