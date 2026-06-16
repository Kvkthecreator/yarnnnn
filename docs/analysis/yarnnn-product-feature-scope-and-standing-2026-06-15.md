# YARNNN Product Feature Scope & Standing — The First Benchmark

**Status:** Hat B (standing/benchmark capture) — **the baseline, not the verdict.** This doc inventories YARNNN's product feature scope across four axes and records current standing per item from ADR status + code locations. It is the *first benchmark* against which nuances are re-evaluated (a live-code verification pass, FE↔feature gap audit, and domain-boundary review come next). It recommends nothing and amends no canon.
**Date:** 2026-06-15
**Hat:** B
**Authors:** KVK (operator), Claude (collaborator)
**Relationship to the metaphor doc:** [`floor-and-fiduciary-positioning-2026-06-15.md`](floor-and-fiduciary-positioning-2026-06-15.md) is the *lens* (one standpoint — the two-layer split named via OS-floor + fiduciary-seat). **This doc is the overarching framing the lens sits inside:** the comprehensive feature scope and standing. The metaphor is §1 here, deliberately compact; the bulk is the scope (§3–5), the domain separation (§2), and the standing snapshot (§6).

**Grounded in:** ESSENCE v14.1 · THESIS · ADR-332/335 (four flows + perception) · ADR-310/311 (interop) · ADR-320 (five-root topology) · ADR-340 (FE standing loop) · ADR-222 (OS framing) · CLAUDE.md file-location map.

**Standing legend:** ✅ Implemented · ◑ Partial / phased (some sub-parts shipped) · ▷ Declared (canon set, build pending) · ⊘ Deferred (demand-gated). *All standings are ADR-stated or code-location-inferred; the re-evaluation pass verifies against live code — treat this column as the claim to check, not the proven fact.*

---

## 0. How to read this — the four axes

Every feature is located on four orthogonal axes. Confusing them is the historical source of "locally defensible, globally incoherent" (ADR-340's own diagnosis). Keeping them separate is the point of this benchmark.

1. **Layer** — **Floor** (substrate + interop; general-purpose, flow-agnostic medium) vs **Generality** (program + judgment; what activates the operation). ESSENCE's two layers.
2. **Flow** — applies to the Generality only: **1 Perception** (context in) · **2 Work** (out) · **3 Outcomes** (in) · **4 Loop** (calibration). ADR-332. The Floor is *not* a flow; it is what flows inscribe on.
3. **Concern-domain** — the separable areas of the system that should each be scoped on their own (§2). The "separate domain concerns" ask.
4. **Standing** — Implemented / Partial / Declared / Deferred, with code receipts.

The metaphor (§1) is a fifth, optional lens — useful for positioning, not for scoping.

---

## 1. The framing lens (compact — full treatment in the metaphor doc)

Two layers, named once:

- **Floor** = an *operating system*: your authored, attributed, portable filesystem. General-purpose, always-on, valuable before any program. (ADR-222 makes this literal.)
- **Generality** = a *fiduciary + an operation*: activate a program and the floor runs four flows under an independent judgment seat that compounds over tenure.

The decomposition that resolves "general-purpose autonomous self-improving agent":
- **general-purpose** = the Floor · **autonomous** = flows 1→2 on cadence · **self-improving** = flows 3→4 against ground truth.

That is the whole of the metaphor's job here. The rest of this doc is the feature scope.

---

## 2. The concern-domain map (separation of concerns)

The eleven domains YARNNN is actually built from. Each is a distinct concern with its own owner, substrate home, code home, kernel-vs-program status, and standing. This table is the spine; §3–5 expand the rows that carry product surface area.

| # | Concern-domain | What it owns | Substrate root (ADR-320) | Code home | Kernel / Program | Layer | Standing |
|---|---|---|---|---|---|---|---|
| D1 | **Substrate** | Authored, attributed, revisioned filesystem | all five roots | `authored_substrate.py`, `workspace_files`/`_blobs`/`_file_versions` | Kernel | Floor | ✅ |
| D2 | **Interop face** | File+revision primitives over MCP; portability | `operation/` + readable authored substrate | `api/mcp_server/`, `permission.py` gate | Kernel | Floor | ◑ (gate ✅; primitive rebuild phased) |
| D3 | **Perception / context-in** | Watches, observation contract, transports | `operation/{domain}/` | `substrate_abi.watches`, `*_tracker.py`, `recurrence.py` | Kernel slot + Program decl | Generality (flow 1) | ◑ (Crawl-A ✅) |
| D4 | **Execution / work-out** | Recurrences, dispatch, specialists, compose | `operation/` | `invocation_dispatcher.py`, `dispatch_helpers.py`, `scheduling.py`, `dispatch_specialist.py` | Kernel | Generality (flow 2) | ✅ |
| D5 | **Ground-truth / outcomes-in** | Reconciler, outcome candidates, money-truth | `operation/{domain}/_money_truth.md` | `services/outcomes/`, `substrate_abi.ground_truth` | Kernel slot + Program decl | Generality (flow 3) | ◑ (trader ✅; generic slot ▷) |
| D6 | **Calibration / the loop** | Calibration trail, by_signal, attention-pruning | `system/_calibration.md` (live) + money-truth `by_signal` | `mirror_calibration.py` (ADR-327), `ledger.py` | Kernel | Generality (flow 4) | ◑ (alpha live; per-watch Walk-stage) |
| D7 | **Judgment seat (Reviewer)** | Persona, principles, wake, verdicts | `persona/` + `constitution/` | `reviewer_agent.py`, `occupant_contract.py`, `reviewer_envelope.py`, `wake*.py`, `review_proposal_dispatch.py` | Kernel (seat) + Program (persona template) | Generality | ✅ |
| D8 | **Governance** | Autonomy / budget / pace ceilings + write-locks | `governance/` | `workspace_paths.py` (`CALLER_WRITE_POLICY`), `pace.py`, `review_policy.py` | Kernel | Floor boundary | ✅ (lock-gate unified + five-root migrated; ADR-320 banner stale — F1) |
| D9 | **Orchestration surface (YARNNN/feed)** | The chat/feed shell the operator addresses | `system/` (memory) | `api/agents/yarnnn.py`, `routes/feed.py`, `prompts/` | Kernel | both | ✅ |
| D10 | **FE / compositor** | Mirrors, compositions, standing loop, attention | reads all | `web/components/library/`, `web/lib/compositor/`, `content-shapes/`, `kernel_surfaces.py` | Kernel | both | ✅ (ADR-340 P1–P4) |
| D11 | **Program / bundle** | Manifest, surfaces, reference-workspace, activation | forks into all roots | `docs/programs/{slug}/`, `bundle_reader.py`, `programs.py` (fork) | Program | Generality | ✅ (alpha-trader); ◑ (alpha-author flow-3) |

**The separation that matters most:** D1+D2 (Floor) are **kernel, flow-agnostic, general-purpose** — they exist with no program. D3–D7 (the four flows + the seat) are **activated by a program** (D11). D8 is the kernel *boundary* the seat runs inside. D9/D10 are the surfaces. A clean mental model: *D1–D2 is the line; D11 declares what runs on it; D3–D7 is the running operation; D8 is its leash; D9–D10 is how you watch it.*

---

## 3. Layer 1 — the Floor: comprehensive feature scope + standing

The Floor is flow-agnostic. Its features are the substrate (D1), the topology (within D1/D8), and the interop face (D2). It is the general-purpose, always-on half — valuable before any program.

| Feature | What it delivers | FE surface | Interop | Standing | Receipt |
|---|---|---|---|---|---|
| **Authored substrate** | Every file has a declared author; nothing silently lost | Files (mirror, ADR-329) | `ReadFile` returns content + `authored_by` | ✅ | ADR-209 |
| **Content-addressed retention** | Dedup via `workspace_blobs` (sha256) | — | — | ✅ | ADR-209 |
| **Revision chain** | Parent-pointered history per path; walkable | RevisionHistoryPanel | `ListRevisions`/`ReadRevision`/`DiffRevisions` — *the killer interop primitive* | ✅ (interop-exposed P1) | ADR-209 / ADR-311 §3 |
| **Five-root topology** | Directory = permission (`access(2)`); governance/constitution/persona/operation/system | Settings + Files paths | foreign writes locked to commons | ✅ migrated (one `_is_path_locked`; legacy roots gone) — verified 2026-06-16 | ADR-320 |
| **Interop face (portability)** | Kernel file+revision primitives in MCP mode, scoped to commons; protocol-agnostic | (the foreign LLM IS the surface) | `ReadFile`·`ListFiles`·`SearchFiles`·`QueryKnowledge`·`WriteFile`(gated)·revision reads | ◑ gate ✅, rebuild phased (P1 substrate / P2 judgment rider / P3 shared-workspace ⊘) | ADR-310/311 |
| **Write gate (single permission point)** | Every consequential write traverses one ADR-307 gate; foreign caller lock-set | — | foreign `WriteFile` DENYs governance + seat | ✅ | `test_adr310_mcp_write_gate.py` 12/12 |

**Floor standing in one line:** the substrate + attribution + revision chain are **shipped and are the differentiator that exists before any judgment**; the portability *promise* (reach it from any LLM) is **partially shipped** — the safety gate is in, the primitive surface rebuild is the active frontier.

---

## 4. Layer 2 — the Generality: comprehensive feature scope by flow + standing

A program (D11) is a flow-declaration set. Each flow scoped end-to-end: mechanism, substrate root, FE surface, interop exposure, kernel-vs-program split, standing.

### Flow 1 — Perception (context in) · domain D3

| Aspect | Detail |
|---|---|
| Sub-cells (DP26) | self-past (harvest/uploads, ADR-331) · self-present (live reads + operator push, **built**) · world-present (perception field, ADR-335) |
| Mechanism | watch declared → recurrence reads on cadence → **distilled** into attributed observation substrate → wakes on threshold |
| Three-layer cut | Declaration (judgment, sovereign) · Observation contract (attributed/attested/dated/distilled) · Transport (commodity driver) |
| Substrate root | `operation/{domain}/` (e.g. `_universe.yaml` → `{TICKER}.yaml` + `_regime.yaml`) |
| FE surface | program home sections (e.g. `TraderRegime`, `TraderPositions`) — no generic perception dashboard |
| Interop | observations are ordinary attributed substrate → `ReadFile`/`QueryKnowledge` |
| Kernel vs program | kernel slot `substrate_abi.watches` + observation contract; **program declares the watches** |
| Standing | ◑ **Crawl-A ✅** (slot, contract, conformance gate, axiom-text). Crawl-B (MCP client), Walk (registry), Run (Reviewer proposes watches) — ⊘ demand-pulled |

### Flow 2 — Work (out) · domain D4

| Aspect | Detail |
|---|---|
| Mechanism | deliverable specs + capabilities; recurrences fire via `invocation_dispatcher`; specialists as headless sub-LLM calls (`dispatch_specialist`); artifacts compose lazily (ADR-333); consequential acts emit `ProposeAction` |
| Substrate root | `operation/` (specs, reports) |
| FE surface | Files (artifacts) + Home "recent artifacts" slot |
| Interop | composed artifacts + source sub-files readable |
| Kernel vs program | kernel execution engine; program declares specs + capabilities |
| Standing | ✅ mature (kernel-universal artifact acts; trader runs transactional acts via Reviewer-gated proposals) |

### Flow 3 — Outcomes (in) · domain D5

| Aspect | Detail |
|---|---|
| Mechanism | `substrate_abi.ground_truth` slot; reconciler folds outcome candidates; attestation enum (`platform`/`operator`/`agent`) |
| Substrate root | `operation/{domain}/_money_truth.md` |
| FE surface | Home ground-truth hero (generic `GroundTruthHero`, program-bound `TraderMoneyTruth`) |
| Interop | outcome substrate readable; **the coupling term** (neither pure perception nor pure action) |
| Kernel vs program | kernel reconciler + slot; **program declares its ground-truth flavor** (money-truth, publication, revenue) |
| Standing | ◑ trader ✅ (money-truth); generic kernel slot ▷; alpha-author must declare ground-truth (currently the flow-incompleteness gap) |
| Why it is the moat's spine | Axiom 8 — written mechanically by the kernel from reality; the agent cannot author its own grade |

### Flow 4 — The Loop (calibration) · domain D6

| Aspect | Detail |
|---|---|
| Mechanism | outcomes reconcile against Reviewer verdicts → calibration trail densifies (`mirror_calibration.py`, ADR-327); `by_signal` expectancy |
| Substrate root | `system/_calibration.md` (live trail, system-written + seat-read; ADR-327) + money-truth `by_signal`. *Note: `persona/calibration.md` (ADR-320 D6) is seeded but has no live writer — F2 in the domain-boundary review.* |
| FE surface | Home judgment trail + Reviewer detail (`persona/` mirrors) |
| Interop | ADR-311 Phase 2 — reads gain a judgment-standing rider when a verdict exists |
| Kernel vs program | fully kernel (calibration is universal machinery) |
| Standing | ◑ alpha live; perception-under-calibration (does a watch earn its attention?) Walk-stage |
| Why it is "self-improving," precisely | not "learns from feedback" — outcomes the agent cannot author, reconciling against judgment, written by the kernel |

### The judgment seat (D7) — spans flows 2–4

| Aspect | Detail |
|---|---|
| What it is | one persona-bearing seat per workspace; reads proposed acts, renders approve/reject/defer; calibrates over tenure |
| Substrate | `persona/` (IDENTITY, principles, calibration, judgment log, standing intent) + `constitution/` (MANDATE, PRECEDENT) |
| Mechanism | wake sources → `wake_evaluation` funnel → `invoke_reviewer(trigger, context)`; verdict binds via `review_proposal_dispatch` within AUTONOMY |
| FE surface | Reviewer detail (mirrors) + Queue (the consent gate) + Feed (verdicts) |
| Independence | judged against ground truth, not producer agreement; refuses operator's bad impulse (ADR-319) |
| Occupant rotation | seat persists, occupant interchangeable (Principle 14) — human today, AI as it earns it |
| Standing | ✅ live, real-time, central |

**Flow-completeness is the standing diagnosis (ADR-332 D2):** enumerate a program's four flows; the missing one is the gap. **alpha-trader is the only flow-complete instance** (all four run). **alpha-author is flow-3-incomplete** (declares `flows_na.perception`, owes ground-truth). The **bare kernel** is the Floor with zero flows — inspect-only resting state (Direction A).

---

## 5. Front-end ↔ feature wiring (the holistic tie-up)

The FE is scoped by "mirror once, compose few" (ADR-340 / DP29). This table is the explicit surface↔feature↔flow mapping you asked for.

| FE act | Surface | Class | Renders (feature / flow) | Substrate read | Standing |
|---|---|---|---|---|---|
| **Decide** | Queue + attention center | composition + chrome | pending `action_proposals` (flow 2 gate) | `action_proposals` | ✅ |
| **Read** | Feed + attention center | composition + chrome | material narrative since last seen (flows 3+4) | narrative weight (ADR-219) | ✅ |
| **Dwell** | Home | composition | all four flows, program-weighted slots | ground-truth hero, live entities, judgment trail, artifacts, constitution band | ✅ (P4; program slot bindings = program work) |
| **Tune** | System Settings (panes) | mirrors | autonomy / budget / pace / connectors / sources (D8 governance + D3 transports) | `governance/` + bindings | ✅ (P2 fold) |
| **Amend** | Home constitution band → mirrors | composition → mirror | MANDATE / principles / IDENTITY (`constitution/` + `persona/`) | constitution + persona | ✅ (P3 trio) |
| **Setup** | `/setup` (Utilities) | sequence | flow-declaration walking (activate program on Floor) | bundle fork | ✅ (ADR-331) |
| **(escape hatch)** | Files | mirror (L1 raw) | any substrate file, raw — the `/proc` of the OS | all roots | ✅ (ADR-329) |

Two FE classes, both shipped: **mirror surfaces** (one ↔ one substrate concern — complete, neutral, never deleted — the Floor's raw view) and **composition surfaces** (one ↔ one operator act — Home is the front page). **Attention is derived, never stored** (no `notifications` table — pending proposals → Decide badge; material narrative → "what happened"; runway → warnings). **Setup = flow-declaration walking** — the FE moment where the Floor becomes a flow-complete operation.

**The FE-to-feature gap to re-evaluate (named, not resolved):** Home's *program-weighted slot bindings* are program work (ADR-312 contract), so a non-trader program's Home is only as populated as its SURFACES.yaml declares — the FE↔feature completeness of alpha-author's Home is an open audit item.

---

## 6. YARNNN's standing, summarized (the benchmark snapshot)

**What is solid (the Floor + the kernel machinery):**
- Authored substrate, attribution, revision chain: ✅ shipped, and it is the pre-judgment differentiator.
- The execution engine, the judgment seat, governance ceilings, the FE compositor (mirrors + compositions + attention + standing loop): ✅ shipped.
- The four-flow *model* and three of four flows' *kernel slots*: ✅/◑.

**What is partial (the frontier):**
- **Interop face** — gate shipped, primitive-surface rebuild phased (Phase 1 substrate moat is the near-term unlock; Phase 2 judgment rider; Phase 3 shared-workspace deferred). *This is the floor's portability promise, partially owed.*
- **Perception field** — Crawl-A shipped; the MCP-client transport + registry resolution are demand-pulled.
- **Five-root topology** — ✅ migration complete in code (verified 2026-06-16, F1); ADR-320 status banner stale.
- **Ground-truth generalization** — proven for trader, generic slot declared; non-trader programs owe their ground-truth flavor.

**What it means for YARNNN as standing:**
- **One flow-complete operation exists** (alpha-trader). The architecture's thesis is proven in exactly one domain — which is the honest claim THESIS makes (sequencing, not coverage).
- **The Floor is general-purpose and largely shipped; the Generality is program-activated and proven once.** YARNNN stands as: *a working general-purpose floor + one fully-running fiduciary operation + a second (alpha-author) that is flow-incomplete by a declared, nameable gap.*
- **The bare kernel is a legitimate resting state, not a broken state** (Direction A) — but it is inspect-only; an operation requires a program.

**Competitive standing (one line, from ESSENCE/NARRATIVE):** the capability claims (persistent/compounds/autonomous) are commoditized; YARNNN's standing rests on *structure* — authored attributed substrate + an independent judgment seat calibrated against ground truth the agent cannot author. That structure is shipped where it counts (the seat is live) and is the part incumbents structurally won't build.

---

## 7. What this benchmark enables (the re-evaluation hooks)

This doc is the baseline. The nuances to re-evaluate against it, in priority order:

1. **Live-code standing verification** — convert every ◑/▷ in §2–4 into a verified status against the running system (substrate receipts: revision_ids, execution_event ids, conformance-gate results). The benchmark claims; the re-eval proves.
2. **FE↔feature gap audit** — §5's named gap (non-trader Home slot bindings) plus a full surface-by-surface check that every shipped feature has its mirror and every act has its composition.
3. **Domain-boundary review (§2)** — ✅ **DONE 2026-06-16, no blur** — see [`domain-boundary-review-2026-06-16.md`](domain-boundary-review-2026-06-16.md). All three audited seams CLEAN (D3↔D4 watch→recurrence; D6↔D7 calibration write; D8 lock-gate + ownership). Surfaced F1 (D8 standing ◑→✅, corrected here), F2 (dual calibration substrate — `persona/calibration.md` seeded-but-unwritten vs live `system/_calibration.md`; Hat-A reconciliation queued), F3 (budget constant name — verify in step 1 above).
4. **Flow-incompleteness remediation** — alpha-author's flow-3 (ground-truth) declaration; the general four-flow conformance gate's coverage as programs are added.
5. **Interop frontier** — sequence Phase-1 primitive surface (substrate moat) → Phase-2 judgment rider, against the portability promise the positioning leans on.
6. **Positioning hooks** — ✅ RESOLVED 2026-06-15, landed in ESSENCE v14.2 "The Framing Lens (internal)": internal frame only (external lead unchanged); both fiduciaries register-dependent; no FOUNDATIONS Derived Principle.

Once §7.1–7.3 are walked, this benchmark hardens into the canonical scope/standing reference (candidate home: a `docs/architecture/` feature-scope doc, or an extension of SERVICE-MODEL.md), and the positioning hooks (§7.6) feed the ESSENCE/NARRATIVE cascade.

Until then: a benchmark. It records standing; it does not change it.
