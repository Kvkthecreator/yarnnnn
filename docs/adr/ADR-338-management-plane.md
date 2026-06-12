# ADR-338 — The Management Plane: Operating the Operation Is First-Class Product Surface

**Status:** **Accepted (2026-06-11)** — framing + program-of-work ADR. **D4 program of work IMPLEMENTED 2026-06-11** — all 7 FE items shipped (FE audit → IA decision → builds). See the companion [ADR-338 FE plan](ADR-338-management-plane-fe-plan.md) for the audit receipts, the IA decision (the management plane coheres on the existing os-config register + menu-bar vitals — no new container), per-item interaction contracts, and the build log (gates: 136 assertions across 6 ADR-338 gates; ADR-297 parity 147/147; ADR-287 conformance 16/16). **§7 (added 2026-06-12) recorded a STANDING OPEN QUESTION — RESOLVED same day by [ADR-340](ADR-340-operator-experience-model.md)** (the operator experience model): teaching = guided flow (model B, the Setup-Assistant analog) + consequence previews on standing panes (the D4.5 installer pattern generalized); `/sources` folds into the System Settings pane-fold rather than holding standalone primary placement. §7 preserved below as the question's trace.
**Date:** 2026-06-11
**Deciders:** KVK (operator) + Claude (collaborator)
**Hat:** A (system canon)

> **Discourse base:** the 2026-06-11 MacBook-analogy discourse (operator: "this in itself is a whole setup and app-management-like practice… our investment surrounding this architecture should be even purer"), following the persona stretch-map and the anr-scout journey week. **The empirical trigger**: every operator act in the validated journey — declaring watch sources, approving the proposal queue, graduating delegation, accelerating cadence, topping runway — ran through psql + Python harness scripts because the cockpit surface for it is thin or missing. A real operator cannot do what the developer harness did. Two of the week's genuine findings (the schema-inert `_autonomy.yaml` edit with its duplicate-key shadow; the NULL-content proposal approved blind) are precisely the failure class a management surface eliminates.

**Extends:** ADR-222 (the OS framing gains its *user-experience half* — see D2), ADR-245 (Phase 4's missing-L3-affordance list is elevated from tail-end backlog to a named program of work and extended), ADR-332/335/336 (the four flows gain their operator-facing projection).
**Preserves:** ADR-206 D6 (CRUD split), ADR-244 (Settings→Workspace as permanent lifecycle surface), ADR-320 ("onboarding is their first authoring, not a phase"), ADR-331 (`/setup` as flow-walking), ADR-307 (one gate, one queue), Derived Principle 12 (channel legibility gates autonomy) — this ADR names the pattern those decisions were each an instance of.

---

## 1. The decision in one paragraph

The four flows (DP26) have an operator-facing projection that is not itself a flow: **the management plane** — the standing set of surfaces through which the operator owns the operation. Context-in projects as source/watch management; work-out as deliverable specs and preferences; outcomes-in as attestation, import, and verdicts; the loop as delegation dials, budget, and calibration reads. The management plane is **first-class product surface, not setup overhead to be automated away**. Treating it as compressible "onboarding friction" was the framing error this ADR retires; the prior instinct ("make it part of setup; the agent handles it") remains correct only *below the consent line* (D3).

## 2. D1 — The management plane, named

**The management plane is the operator's half of the product.** YARNNN's product has two halves: the *operation* (the kernel + program running unattended — built, validated, soaking) and the *operationship* (the operator's standing practice of owning it: installing, granting, declaring, approving, tuning, reading). The second half is where trust is manufactured. A consumer who cannot see and work the management plane is not an operator — they're a bystander to an automation, and bystanders churn the first time something surprises them.

## 3. D2 — The OS-experience vocabulary (ADR-222's missing half)

ADR-222 made the OS framing literal on the *system* side (kernel / syscall ABI / shell / userspace / applications / compositor). This ADR extends it to the *experience* side, same literalness:

| Mac experience | YARNNN management plane | Substrate it fronts |
|---|---|---|
| **App Store** | Program catalog + activation (Settings→Workspace, ADR-244; `/setup` flow-walk, ADR-331) | bundles, MANIFEST, fork |
| **Installer** ("what this app needs") | Activation sequence surfacing the bundle's flows, capabilities, watches before fork | four-flow declarations |
| **Drivers** | Transport bindings: platform connectors + (Crawl-B) MCP server bindings + watch sources | `platform_connections`, `_sources.yaml` |
| **System Settings panes** | The governance dials: Autonomy/delegation, Budget, Preferences, Pace-class controls | `governance/*.yaml` |
| **Permission dialog** | The Queue — approve/reject with the *diff shown* (ADR-307 family-shaped rendering) | `action_proposals` |
| **Finder** | Files (L1 raw view, ADR-245) | `workspace_files` |
| **Activity Monitor** | Schedule/recurrence health + execution reads | `tasks` index, `execution_events` mirrors |

The **App Store + drivers view survives as standing vocabulary** (operator-ratified): programs are apps you install; transports are drivers you bind; both are deliberate, legible, owned acts. A driver install got *simpler* over macOS's life but never *invisible-without-consent* — that's the design north star.

## 4. D3 — The consent line (the discipline that prevents over-rotation)

The reframe does NOT mean "add ceremony." The Mac's lesson is **legible and owned, not laborious**. The line, already implicit in canon, now explicit:

- **Above the line — judgment and trust acts get first-class surface**: activating a program, binding a transport/driver, declaring watch sources (a portfolio of attention), granting/graduating delegation, setting budget, approving a queued diff, attesting an outcome. These are consent moments; compressing them into invisible automation destroys ownership and (per DP12) caps the autonomy an operator will ever grant.
- **Below the line — mechanical enactment stays invisible**: the fork, the fetch, the distillation, index materialization, mirrors, reconciliation mechanics. Nobody watches a driver copy files.

**Diagnostic test**: if an act changes *what the operation is allowed to do or perceive*, it belongs above the line (surface). If it changes *what the substrate currently says* within already-granted allowances, it belongs below (automation + revision chain).

## 5. D4 — The program of work (elevation, not invention)

ADR-245 Phase 4 already named missing L3 affordances ("autonomy toggle, principles thresholds editor, risk envelope editor"). This ADR **elevates that list from tail-end hygiene to a named FE program — peer in priority with the ADR-336 P4 interest-scout bundle** (a consumer program without a management plane recreates the harness-dependency this week exposed) — and extends it with the journey-week gaps:

1. **Sources/watch editor** — the `_sources.yaml` pane (the drivers view for the standing watch); declared-vs-observed health inline (Check-7 shape).
2. **Delegation dial** — `_autonomy.yaml` as a Settings pane (level + never_auto guards), making the schema-inert-edit and duplicate-key failure classes structurally impossible.
3. **Queue diff previews** — family-shaped proposal rendering per ADR-307, so a NULL-content write is *visible* at approval time.
4. **Budget/runway pane** — `_budget.yaml` + balance, with observed burn.
5. **Program management** — extend ADR-244's Workspace surface toward the installer shape (show the bundle's four-flow declaration before activation).
6. ADR-245 P4's original three (autonomy toggle shipped as PoC; principles thresholds; risk envelope).

All of these are L3 affordances over existing parsers/contracts (ADR-245's machinery) — **no new kernel**. The implementation session begins with an FE audit (what exists per surface vs this list, consent-line classification), then sequences builds.

## 6. What this ADR does NOT do

- Does not add ceremony below the consent line, revert any automation shipped this week, or slow the mechanical paths.
- Does not build the FE program here (audit-first; separate session).
- Does not introduce a new architectural layer — the management plane is *Channel-dimension projection* (Axiom 6), rendered by the existing compositor + L1/L2/L3 model (ADR-245).
- Does not rename existing surfaces; it names the program of work that fills them.

**Dimensional classification**: **Channel** (Axiom 6, primary) + **Purpose** (Axiom 3 — the operator's ontology of ownership). Canonized as FOUNDATIONS **Derived Principle 28** + GLOSSARY v2.6 ("Management plane" + App Store/driver vocabulary rows) in the same commit.

---

## 7. Standing question (opened 2026-06-12): the consequence-legibility gap — and where the OS analogy points

> **Status: RESOLVED (2026-06-12) by [ADR-340](ADR-340-operator-experience-model.md) D7** — the synthesis this section's §7.3 hypothesized: teaching lives in the guided flow (`/setup`, model B); standing panes carry consequence previews (the installer pattern generalized); the framing decision §7.2 demanded landed as the mirror/composition model (FOUNDATIONS Derived Principle 29). The section is preserved verbatim below as the question's trace and forcing evidence.

The D4 program shipped (all 7 items — see [the FE plan + build log](ADR-338-management-plane-fe-plan.md)). Walking the live Sources surface against a real operator's eyes surfaced a gap that the regression gates could not: **the surfaces are legible about the *mechanism* and silent about the *consequence*.**

### 7.1 The gap, concretely

The Sources pane renders `_sources.yaml` faithfully — an input box, the watch's cadence pointer (`· track-sources`), an empty/observed state. What it does **not** convey:

- **What the field *is* in the operator's ontology.** "RSS feed URL" is the mechanism. The operator's concept is *"a website I'm telling my agent to keep an eye on."* The surface speaks the file's language, not the operator's.
- **The downstream chain.** Declaring a source has real, traceable consequences (all verified in substrate): the `track-sources` recurrence fetches it on cadence → distills into `_watch_signal.yaml` → that file sits in the **Reviewer's wake envelope** → so the agent reasons against it at every wake → which shapes what it proposes → which lands in the Queue. The surface shows step 1 and a faint trace of step 2; steps 3–6 are invisible. An operator cannot infer that *what they type here becomes their agent's perception, daily.*

This is not an ADR-338 regression — **D3 (the consent line) explicitly demands legibility**, and "legible" must include legibility-of-consequence, not just legibility-of-mechanism. The shipped surfaces delivered the mechanism half of D3 and under-delivered the consequence half. The same gap is latent in Autonomy, Budget, and Principles — every yaml-backed pane presents a file, not a consequence.

### 7.2 The higher-level question this forces

The cheap fix (add "what this does / what happens next" copy to each pane) is real but treats the symptom. The operator's intuition — and the reason this is recorded as an ADR section, not a backlog ticket — is that the **framing needs a higher-altitude FE-experience decision** the D4 program did not make:

**Where does the management plane *teach*?** Two candidate models, currently un-chosen:

- **(A) Standing reference surfaces** (what shipped). Each concern is an os-config pane you return to. Teaching, if any, lives in the pane's own copy. Risk: panes accumulate into death-by-a-thousand-config-screens; the operator meets each pane cold, with no moment that explains the consequence in context.
- **(B) Taught-in-context, then graduates to reference.** The consequence is taught *at the moment of first use* — inside the guided flow (`/setup`, the Sequence surface, ADR-331 "bring in reality" step) — where "add a source → here's what your agent now perceives" can be shown as cause-and-effect. The standing pane becomes the *return-to-tune* surface only after the operator has been taught once.

Choosing A vs. B (or a synthesis) reshapes all four panes at once. It is a Purpose-dimension question (the operator's ontology of ownership, Axiom 3) wearing a Channel-dimension costume.

### 7.3 The hint in the MacBook/OS analogy (D2's unexploited half)

D2 mapped the *system* side of the Mac experience (App Store / Installer / Drivers / System Settings panes / Permission dialog). The build consumed the **structural** half of that map (where things live). It left the **pedagogical** half unmined — and that is where the better answer likely resides:

- **macOS System Settings panes don't just hold config — they show what the setting *affects*.** Toggle "Night Shift" and you see a live preview + "from sunset to sunrise." The pane teaches the consequence at the point of the control. Our panes show the control and hide the consequence.
- **The Installer (D2's "what this app needs") *previews before it commits*** — and ADR-338 D4.5 *did* build this (the four-flow `FlowPreview` panel). That preview pattern — "here's what this will do, shown before you commit" — is exactly the consequence-legibility the *other* panes lack. The installer got it; the standing panes didn't. The analogy already contains the answer; it was applied unevenly.
- **macOS Setup Assistant teaches the consequential acts once, in sequence** (this is model B above). The Mac doesn't drop a new user onto a wall of System Settings panes — it walks the consent moments (Apple ID, iCloud, Touch ID) in a guided flow, *then* leaves the panes as reference. ADR-331's `/setup` Sequence surface is the YARNNN analog and is the natural venue for option B.

**Hypothesis to test (not yet decided):** the management plane's teaching belongs in the guided flow (the Setup Assistant analog), with the standing panes carrying a *consequence preview* (the Installer/Night-Shift analog) rather than bare file rendering. The structural OS map (D2) is sound; what's missing is its **pedagogical** application — *legible-and-owned* (D3) requires the operator to *see the consequence at the moment of the act*, which the App Store/Installer/Setup-Assistant experience does deliberately and our panes do not yet.

### 7.4 Disposition

- This question is **owned by the next management-plane ADR** (un-numbered; to be drafted when KVK chooses a direction). That ADR should: (a) pick A / B / synthesis for where teaching happens; (b) decide whether the standing panes carry a consequence-preview affordance generalized from the D4.5 installer pattern; (c) re-evaluate whether a standalone `/sources` surface earns its place or folds into the guided flow.
- The right vehicle to *measure* the gap before deciding is a **Hat-B evaluation** (`docs/evaluations/…-management-plane-consequence-legibility/`) with the criterion "a real operator can infer, from the surface alone, what a management act changes downstream" — expected vs. observed, walked against the anr-scout workspace. That finding becomes the next ADR's forcing evidence.
- Until that ADR: **no more management panes are added, and no consequence-copy is bolted on piecemeal** — the fix is a framing decision, and bolting copy onto four panes independently would entrench model A by default. Recorded here so the default doesn't win by inertia.

**Dimensional note:** the open question is primarily **Purpose** (Axiom 3 — the operator's ontology, the "why this matters to me" the panes must carry) projected through **Channel** (Axiom 6 — where and how it's shown). It does not reopen any D1–D6 decision; it names the un-made FE-experience decision those decisions left standing.
