# Discourse capture — The Operator Experience Model: Mirrors, Compositions, and Attention

**Date:** 2026-06-12
**Participants:** KVK (operator/founder) + Claude (collaborator)
**Status:** Discourse capture — **ratified same day as [ADR-339](../adr/ADR-339-operator-experience-model.md)** (the operator experience model; FOUNDATIONS Derived Principle 29 + GLOSSARY v2.7), which absorbs the ADR reserved by [ADR-338 §7.4](../adr/ADR-338-management-plane.md). This document is the discourse trace; ADR-339 is the decision record.
**Hat:** A-adjacent (canon discourse; the ratification lands in an ADR).

> **Trigger:** Walking the live launcher (17 surfaces, grouped Constitution / Applications / System Settings) against the founder's own eyes: *"even for me, I'm confused where I'm supposed to look for work. Queue, feed, activity, recurrence seem similar yet different… the constitution surfaces seem like flat set-ups."* Plus the standing question already recorded at ADR-338 §7 (consequence-legibility), which this discourse generalizes.

---

## §1 The presenting symptom

Three observations, all from the builder's own first-person use:

1. **No obvious "where do I look for work."** Queue / Feed / Activity / Recurrence read as similar-yet-different; the operator cannot tell which to check, when, or why.
2. **Constitution surfaces feel flat.** Mandate / Principles / Identity are correct in content but read as static file renderings sitting at the top of the launcher as if they were daily destinations.
3. **The launcher reads as a wall of peer tiles.** Pieces present, cohesion absent — despite every individual surface having an ADR, a substrate, a register, and a passing gate.

## §2 Diagnosis: macro, not bottom-up — the three layers of the OS analogy

The per-surface ambiguity is **derivative**: each pane is locally defensible; the whole doesn't cohere. That is the signature of a missing macro decision, not of N small misalignments. ADR-338 §7.4 already froze bottom-up patching ("no more panes, no consequence-copy bolted on piecemeal"). This discourse locates the missing macro decision precisely.

The macOS analogy (ADR-222 system side, ADR-338 D2 experience side) has three layers; only one is mined:

| Layer | Content | Status |
|---|---|---|
| **1. Structural** — where things live | kernel/shell/userspace (ADR-222), registers (ADR-309/312), App Store / Drivers / Settings / Permission-dialog map (ADR-338 D2) | **Mined and sound.** Not reopened. |
| **2. Pedagogical** — how consequence is taught | Night-Shift-style consequence previews, Installer preview, Setup Assistant sequencing | **Named, undecided** (ADR-338 §7 A/B). Resolved here as a corollary — see §7. |
| **3. Experiential** — where the operator *dwells*, and how often each surface is visited | Activity-centric, not surface-centric: dwell ~95% / visit settings rarely / pass through setup once | **Unmined. This is the north-star gap.** |

Receipts that the gap is Layer 3:

- **The launcher's grouping is the system's self-description, not the operator's task-description.** `web/components/shell/Launcher.tsx:62-64` groups verbatim by architectural register (`intent` → "Constitution", `application` → "Applications", `os-config` → "System Settings"). Registers (ADR-309/312) exist to keep the *codebase* honest — kernel taxonomy leaking into the experience layer.
- **Surface census inverted vs. the metaphor.** 10 of 17 windowed surfaces are constitution/config; a Mac's surface-time is ~95% apps-and-documents. Partly honest (management plane is where trust is manufactured, ADR-338 D1); partly an artifact of substrate-mirroring promoting every governance yaml to a launcher-level tile.
- **D2's own map mislocates the Queue.** ADR-338 D2 names the Queue "the permission dialog" — but on a real OS, permission dialogs are *push, not pull*. YARNNN makes its most consequential consent surface a destination you must remember to visit.

## §3 The axiomatic finding: two surface classes

**The surface census has two classes that canon never separated:**

- **Mirrors** — one surface ↔ one substrate concern. Complete, neutral, faithful. ADR-297 ("surfaces as substrate mirror") built this class *exhaustively*: sources, autonomy, budget, principles, files, activity, recurrence, agents… Mirrors are correct and need no rework. They are the `/proc` and `ls` of the OS.
- **Compositions** — one surface ↔ one operator-**act**. Selective, opinionated, program-weighted, synthesized over many substrates. Exactly **one** exists: Home (ADR-312, six kernel slots composed over present constituents). **Operator correction (same discourse): Home is the proof of the *pattern*, not a finished instance** — it is directionally right yet still unclear "what I can do and where it leads." See §6b.

The incoherence is not a property mirrors lack — it is a *layer* with one inhabitant. The launcher confusion, the queue/feed/activity blur, and the "flat constitution" feeling are the same defect: **mirrors carrying experience weight only compositions can carry.** The constitution panes feel flat because they are file renderings; their composition already exists and works — the Home constitution band.

This is **ADR-245's L1/L3 discipline lifted one level**. ADR-245, at the file level: L1 raw view is the escape hatch; L3 structured affordance is the operator interface. The launcher today is L1-weighted at the *experience* level. The rule generalizes: mirrors are the escape hatch; compositions are the interface.

**No new noun above "program" is needed.** The founder's instinct ("apps that use the system configurations") is satisfied by the existing ADR-312 contract — kernel owns act-shaped slots; programs weight, label, shape them; kernel never invents a program noun — *extended from Home to the other acts of the loop*. Inventing a "pure program" layer would duplicate.

## §4 The standing loop, derived (resolving generality-vs-bias)

Worry raised: declaring an operator standing loop might over-bias a product that, like macOS, should serve unbounded user shapes. Resolution: **macOS serves a billion user-shapes; macOS itself does not** — apps do. The OS commits to a tiny biased set of universal *acts* (launch, open, respond-to-dialog, configure, file). The desktop metaphor was an enormous opinion that generalized because it was an ontology of *acts on work artifacts*, not a persona.

YARNNN's standing loop is likewise **not a persona bet — it is the operator-facing dual of already-ratified structure**:

- The four flows (DP26) say what the operation does: context in → work out → outcomes in → the loop.
- The consent line (ADR-338 D3) says which moments belong to the operator.

Cross them and the acts fall out mechanically, persona-free:

| Act | What it is | Frequency | macOS analog |
|---|---|---|---|
| **Decide** | consent moments — queued proposals, attestations | as-routed | permission dialog / badges |
| **Read** | what happened since I last looked | daily | (Notification Center + the document you're in) |
| **Dwell** | where the operation stands | daily | Desktop / the open app |
| **Tune** | adjust granted allowances (autonomy, budget, sources, connectors) | occasional | System Settings |
| **Amend** | constitution authorship (mandate, principles, identity) | rare | — (more first-class than any Mac analog; lives on Home's constitution band) |
| **Setup** | become operational | once, re-enterable | Setup Assistant (ADR-331, already built) |

The *content* of each act is program-specific; the *shape* is kernel. The bias is derivable from the architecture's invariants, so it cannot paint the product into a use-case corner.

## §5 Attention routing is an OS responsibility, not a surface

Why Queue / Feed / Activity / Recurrence blur: all four are *time-shaped reads over the operation's events*, distinguished only by **which substrate they mirror** (`action_proposals` / narrative / `execution_events` / recurrence index) — a distinction only the system cares about. The operator's questions are act-shaped: *what demands me? what's the story? is the machinery healthy? what's on the calendar?*

The OS-grade resolution is **three attention channels**, none of which is a new subsystem:

1. **Badges / menu-bar vitals** — persistent, glanceable (seed already shipped: ADR-338 menu-bar vitals; principle now named).
2. **A notification-center composition** — one pull surface aggregating push events ("what wants me since I last looked"), every item a deep-link into its real home (Queue item / Feed entry / pane). Pure routing; owns no content.
3. **Dialogs** — in-the-moment consent only when the operator is actively present (rare; asynchronous-first product).

**Binding discipline — attention is derived, never stored.** No `notifications` table (that would be the ADR-153 shape of mistake: shadow state). The derivation substrate already exists and is ratified:

- pending `action_proposals` → the Decide badge;
- the narrative **weight taxonomy** (material / routine / housekeeping, ADR-219; mechanical fires silent per ADR-277) → "material events since last seen" *is* the notification feed, pre-classified;
- budget runway + capability gaps → the warning class.

Consequence: **mirrors stop being attention destinations.** Queue remains the full decide surface — but you arrive by routing, not by remembering. Activity and Recurrence reclassify honestly as **utilities** (Activity Monitor is real, complete, and not in your face).

**Scope-stability verdict (operator question, second round):** the attention layer is implementable *now*, independent of how the remaining open decisions land. Its two stable invariants — channel shapes (badge / center / dialog) and the derive-never-store discipline — do not move under any branch of the launcher-IA, Home-re-derivation, or Settings-nesting decisions; the center routes *into* Queue/Feed/panes whichever shape they take.

**Top-bar placement (decided this discourse, grounded in `web/components/shell/system-status/`):** the existing `SystemStatusCluster` (ADR-297 D20) is the macOS *menu-bar extras / Control Center* analog — standing **state** (Autonomy, Budget, Balance, Connections). The attention center is a *different* chrome role — **events demanding me** (Notification Center) — and must be a separate top-bar item, not an overload of a status chip: one new attention item (badge count = pending proposals + warnings; dropdown = the derived center, every row a deep-link). Two consolidations make room and remove the redundancy the operator flagged:
- **Budget absorbs Balance.** `BudgetStatusItem` (wallet, ADR-327 — envelope + queue depth) and `BalanceStatusItem` (card — account funds) are two money chips side-by-side; runway is only honest as *envelope paired with funds* (ADR-327 D8's own logic extended). One money chip: budget window + balance + observed burn; Billing settings remains the popover footer + UserMenu link. Cluster shrinks 4 → 3 (Autonomy · Money/Runway · Connections) + the new attention item.
- **UserMenu stays account-only** (profile, billing, sign-out) — it is not an attention or state channel.

## §6 Nesting and the five chrome roles

**System Settings consolidation (ratify-worthy):** the seven os-config launcher tiles (budget, autonomy, program, settings, connectors, sources, setup-reference) fold into **one** System Settings surface with sidebar panes, second-order grouped:

- **Perception & transports** (drivers): Connectors, Sources
- **Governance** (dials): Autonomy, Budget
- **Program** (lifecycle): Program management, Setup re-entry
- **General**: account/settings

macOS goes third-order (General → About / Software Update / Storage) without confusion: **depth under one well-named door is cheap; breadth at the top level is expensive.** The current launcher pays the expensive kind.

**The five-chrome-roles observation:** macOS separates **Dock** (few, pinned, primary) · **menu bar** (vitals) · **Spotlight** (everything, flat, searchable) · **Launchpad** (all apps, grouped) · **System Settings** (nested config). YARNNN's launcher currently performs Dock + Launchpad + Spotlight + settings-map at once. A flat searchable list is *fine* for the Spotlight role — flatness is only fatal in the Dock role, which the launcher is also carrying. The fix is therefore **both** of the candidate moves, because they are one move seen from two sides: nesting (System Settings consolidation) is what makes the launcher re-sort possible.

**Target top-level IA (sketch, ~17 → ~7):**

> **Home · Feed · Queue · Files** (the loop: dwell / read / decide / artifacts) · **System Settings** (one door, nested panes) · **Utilities** (Setup, Activity, Recurrence, Agents — present, searchable, de-prioritized)

**Setup demotion (operator-proposed, second round; macOS receipt accepted):** Setup Assistant is not in the Dock, and Migration Assistant literally lives in `/Applications/Utilities` — re-enterable setup has no claim to primary placement. `/setup` keeps its three entry paths — first-run redirect (unchanged, ADR-331), System Settings → Program pane ("re-run setup"), and launcher search — and lists under Utilities. Its Sequence-composition nature (ADR-331) is unchanged; only its nav tier moves.

with **Constitution reached through its composition** (Home constitution band, ADR-312 slot #1) rather than as three peer tiles — resolving the "flat set-ups" feeling without touching the panes' content.

## §6b Home: proof of the pattern, not its finished instance — and why the chicken-and-egg resolves

Operator pushback recorded verbatim: Home is *directionally* correct but not "fine as is" — it is still unclear what the operator can do there and where it leads; and it will remain a moving target until the mirror/composition/OS framing hardens. Two clarifications dissolve the apparent circularity:

**1. The dependency is one-directional, not circular.** The framing (act-set, mirror/composition classes, attention routing) does not depend on Home being good — it was derived from the four flows × the consent line (§4) and from the census (§8). Home's final shape, conversely, *does* depend on the framing. So the ordering is: harden the frame (the ADR) → Home becomes **derivable** rather than designed. Chicken-and-egg only appears when both are treated as design questions; one of them is a derivation.

**2. Why Home felt right and still confuses — the same diagnosis at one level down.** ADR-312's six slots map almost 1:1 onto the act-set this discourse derived: constitution band → **Amend**, decision queue slot → **Decide**, judgment trail → **Read**, ground-truth hero + live entities → **Dwell**, recent artifacts → **Files**. Home accidentally encoded the standing loop before the loop was named — that is why it is directionally correct. But its slots are **renderings without act-affordances**: they show state and do not route into the act (weak deep-links, no "decide here / tune there" carry-through). This is the §7-of-ADR-338 gap recurring at the composition level — the slot shows *presence* but not *what I can do about it*.

**Derived target (for the ADR, not for piecemeal fixing now):** Home is the **front page of the compositions** — the desktop. Each slot is the glanceable head of one act with a route into that act's surface (macOS widget contract: show state, deep-link into the app). Under that contract Home stops being a moving target: its slot-set, ordering, and affordances all fall out of the act-set, and programs keep weighting them per the existing ADR-312 contract.

## §7 Candidate derived principle

> **Mirror once, compose few.** Every substrate concern earns exactly one mirror surface — complete, neutral, the escape hatch (ADR-297's discipline). The operator experience is carried by a small fixed set of **act-shaped compositions** — kernel-owned, program-weighted (ADR-312's discipline, generalized) — one per act of the operator's standing loop, which is itself derived from the four flows × the consent line, not from a persona. Compositions foreground; mirrors are reachable from compositions, never the default. Attention-routing (what demands the operator now) is an OS responsibility — derived from substrate, never stored — not a destination.

Properties: (a) retroactively explains why Home works and the launcher doesn't; (b) makes the launcher IA *derivable* instead of debatable; (c) resolves ADR-338 §7's A/B as a corollary — teaching lives where acts live: the guided flow (`/setup`) teaches consent moments once in sequence (model B), standing panes carry consequence-previews generalized from the D4.5 installer pattern, and the composition shows consequence while the mirror shows mechanism.

## §8 Surface census (all 17, classified)

| Surface | Register | Class | Disposition under target IA |
|---|---|---|---|
| home | application | **composition** (proof of pattern; re-derivation pending, §6b) | Primary — Dwell; becomes the compositions' front page |
| feed | application | mirror of narrative; act-adjacent (Read/Converse) | Primary — Read |
| queue | application | mirror of `action_proposals`; coincides with the Decide act | Primary — Decide (badge-routed) |
| files | application | mirror (L1 by definition, ADR-245/329); coincides with Finder act | Primary — Artifacts |
| setup | os-config | sequence composition (ADR-331) | Utilities; entered via first-run redirect + Settings→Program + search |
| agents | application | mirror (roster) | Utilities |
| activity | application | mirror (`execution_events`) | Utilities (Activity Monitor) |
| recurrence | application | mirror (recurrence index + wake telemetry) | Utilities |
| mandate | intent | mirror (MANDATE.md) | Behind Home constitution band |
| principles | intent | mirror (principles.md + `_principles.yaml`) | Behind Home constitution band |
| identity | intent | mirror (IDENTITY.md) | Behind Home constitution band |
| autonomy | os-config | mirror (`_autonomy.yaml`) | Settings pane — Governance |
| budget | os-config | mirror (`_budget.yaml` + balance) | Settings pane — Governance |
| sources | os-config | mirror (`_sources.yaml`) | Settings pane — Perception & transports |
| connectors | os-config | mirror (`platform_connections`) | Settings pane — Perception & transports |
| program | os-config | mirror/reference (ADR-244 lifecycle) | Settings pane — Program |
| settings | os-config | mirror (account/general) | Settings pane — General (likely becomes the container) |

Borderline cases (feed, queue, files) are mirrors that *coincide* with acts — the classes are not exclusive; coincidence is what earns a mirror primary placement.

## §9 Open decisions reserved for the ADR + disposition

The ratifying ADR (the one ADR-338 §7.4 reserved, widened to the operator experience model) must decide:

1. **Ratify the principle (§7)** — likely as a FOUNDATIONS Derived Principle + GLOSSARY entries (mirror surface / composition surface / attention routing).
2. **The act-set and its composition slots** — confirm Decide/Read/Dwell/Tune/Amend/Setup as kernel act-shapes; which get dedicated compositions vs. coinciding mirrors.
3. **Attention channels** — vitals badge spec + notification-center composition (derived from weights + queue + runway; explicitly no stored notification state); whether Feed or a top-bar dropdown carries the center role.
4. **System Settings consolidation mechanics** — os-config surfaces move from window-grade to pane-grade: `kernel_surfaces` registry implications (parent/pane concept vs. surface absorption), summon-index, `navigateToSurface` params. Registers (ADR-309/312) stay as code taxonomy; they stop being the user-facing sort key.
5. **Launcher re-sort** — foreground acts; Spotlight-flat search retained; Constitution demoted from top-level tiles to the Home band route.
6. **ADR-338 §7 A/B** — absorbed: B for teaching (guided flow), consequence-previews on standing panes (D4.5 installer pattern generalized).
7. **Whether Queue remains a window** or becomes primarily dialog/center-routed with the window as the full-decide fallback.
8. **Home re-derivation (§6b)** — ratify Home as the compositions' front page: slot-set = projections of the act-set, each slot carrying the act's affordance + route (widget contract: show state, deep-link into the act). ADR-312's program-weighting contract unchanged. Until then Home is explicitly a known-moving target; no slot-level patching.

**Discipline holding until ratification (extends ADR-338 §7.4):** no new launcher-level surfaces, no piecemeal launcher re-grouping, no notification state of any kind. The Hat-B evaluation reserved by §7.4 remains the right pre-measurement, with its criterion widened: not only *"can the operator infer what a management act changes downstream"* but also *"can the operator infer, from the launcher alone, what to do next and why"* — the Layer-3 test.

**Dimensional note:** primarily **Purpose** (Axiom 3 — the operator's ontology of acts) projected through **Channel** (Axiom 6). Preserves ADR-222 (structural OS map untouched), ADR-297 (mirrors stay singular and complete), ADR-312 (composition contract generalized, not changed), ADR-331 (setup as the teaching sequence), ADR-338 D1–D6.
