# ADR-338 — The Management Plane: Operating the Operation Is First-Class Product Surface

**Status:** **Accepted (2026-06-11)** — framing + program-of-work ADR. No code lands in this ADR; the implementation session is scoped by the carry-over prompt in the ratifying session and begins with the FE management-surface audit.
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
