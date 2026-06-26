# ADR-374 — Presentation IA: the Substrate Face, and the Steward as a Posture (not a Tab)

> **Status**: **Proposed** (2026-06-26). Doc-first; FE + one backend read (the `kernel_surfaces` registry already drives nav, ADR-373/interop-first-pivot §6). No schema, no primitive, no new substrate.
> **Date**: 2026-06-26
> **Authors**: KVK (operator) + Claude (collaborator)
> **Discourse base**: [`docs/analysis/the-three-rung-framework-and-the-multi-principal-wedge-2026-06-26.md`](../analysis/the-three-rung-framework-and-the-multi-principal-wedge-2026-06-26.md) — Axis 2 (presentation/IA), D1 (no native chat; chat is the steward's interface), and the "agent is a posture the surfaces enter, not a tab" framing. Companion to [`interop-first-pivot-and-agent-gating-2026-06-25`](../analysis/interop-first-pivot-and-agent-gating-2026-06-25.md) (the GTM/strategy side: substrate-forward default, agent-as-gated-beta).
> **Amends**: [ADR-340](ADR-340-operator-experience-model.md) (DP29 "mirror once, compose few" — this ADR settles which composition is the *first* at-rest face when the steward is absent: the substrate boundary, not the operating cockpit), [ADR-312](ADR-312-home-as-composition.md)/[ADR-369](ADR-369-home-split-front-page-and-program-cockpit.md) (Home's substrate-forward empty state is re-affirmed as the *intended default product*, not a degraded ex-cockpit — verification, not rework), [ADR-316](ADR-316-chat-as-dockable-rail.md) (the dockable rail gains an explicit *inert-with-CTA* state when no steward is addressable).
> **Preserves**: [ADR-373](ADR-373-multi-principal-workspace-and-the-re-key.md) (the multi-principal substrate this surfaces), [ADR-370](ADR-370-context-surface-the-operations-boundary.md) (Context = the boundary composition, the membrane's face), [ADR-372](ADR-372-presentation-affordances-interop-face.md) (a DIFFERENT presentation concern — interop-face widget *rendering*; this ADR is *cockpit* IA. No overlap.), [ADR-289](ADR-289-feed-and-conversation-surfaces.md) (the two render grammars — Flow stays typed-row, chat stays bubble-in-rail), [ADR-297](ADR-297-surfaces-as-substrate-mirror.md) (the compositor owns the surface registry; this ADR re-weights `launcher_tier`, it does not author surfaces).
> **Dimensional classification** (Axiom 0): **Channel** (Axiom 6 — what the operator sees, in what priority) over the three-rung framework's presentation axis.

---

## 1. The question this answers

The discourse base named the IA struggle precisely: *"continuously struggling between what to surface, in what priority."* The cause was trying to surface all three rungs (ledger / membrane / steward) as **co-equal tabs**. The framework's Axis-2 lesson — read off git → GitHub → Copilot's *presentation*, not its capability — says they are explicitly **not** co-equal:

- **git presents as infrastructure you don't open** (log/blame on demand) → the **ledger** (Files + revision/trace) is the **floor**, an escape hatch, not a front page.
- **GitHub presents as the home** (the repo page — files + activity) → the **membrane** (the boundary composition) is the **face you land on**.
- **Copilot presents where you work, never as a destination** → the **steward** is a **posture the surfaces enter on activation**, not a fourth tab.

This ADR ratifies that priority so no future session re-flattens the three rungs into co-equal nav and re-creates the struggle.

## 2. The decisions

### D1 — The substrate boundary composition is the at-rest FACE; the steward is not a peer of it

When the steward is absent (base product, or a cold workspace pre-program), the **first at-rest surface is the membrane** — the operation's boundary (Context: In · Out · Flow — ADR-370) and the substrate beneath it (Files — the ledger floor). The operator lands on *"what is my context, what is flowing in and out, what crossed."* This composition must read as a **complete product with zero agent dependency** (interop-first-pivot §4 invariant: the base value loop — connected tools → attributed substrate → served cross-LLM — closes without the Reviewer).

Concretely in the registry ([`kernel_surfaces.py:203`](../../api/services/kernel_surfaces.py#L203)): the `launcher_tier: primary` set, *when the steward is off*, is the membrane+ledger keepers — `context`, `files`, plus the constitution mirrors. The steward-coupled primaries (`home`'s program cockpit, `notifications`, `agents`) are **not** the cold-start face; they light up on activation (D3). (The exact gating mechanism is ADR-375's; this ADR sets the *target IA*, that one sets the *flag*.)

### D2 — No native chat in the base product; chat is the steward's interface, relocated not deleted

The base product (ledger + membrane) has **no chatbox of its own.** YARNNN is *the substrate your existing LLMs share*, not another chat window competing with ChatGPT/Claude (interop-first-pivot §5 decision 1).

**The sunk-cost reconciliation (load-bearing — chat-first UX is heavily committed):** chat-first was the right UI/UX **for the steward**, not the base product. The addressed-wake path ([`feed.py:1126` → `wake_sources.addressed.stream`](../../api/routes/feed.py#L1126)) *is* the Reviewer's interface. So "no native chat in base" **relocates** chat-first to the rung it always belonged to — it is **not thrown away.** The committed work activates in the agent beta, where there is a Reviewer on the other end for it to talk to.

### D3 — The steward is a POSTURE the surfaces enter on activation, NOT a fourth destination

The trap "the agent is bolted on top" must NOT mean "a separate Agent tab you visit" — that re-creates the fourth-co-equal-destination problem one move later. The framework's deeper lesson: **Copilot is not a tab; it is a state the editor enters.** Applied — and this is what ADR-312/367/369 *already built* but had not *named*:

- **Home has no "agent section"; Home is the substrate composition that, when a program activates, the steward acts *through*.** The decision queue is the files/feed surface **gaining a verb** (ADR-367 "operating cockpit, not glance-only"), not a separate surface.
- **ADR-369's split** (kernel front page + additive program cockpit tab *on activation*) **IS** the "agent bolts on" move done correctly: Layer-1 (no program) sees one tab (the substrate face); activate a program → a second tab appears. The cold-start user gets the membrane product; the agent does not crowd the IA until it has something to do.

**This ADR adds no new mechanism — it names the existing shape as correct and forbids re-flattening it.** The one-line correction to the IA instinct: not *"feed/context/files then the agent added on top"* but **"the substrate composition IS the product; the agent is the same composition gaining the ability to act."**

### D4 — The dockable rail has an explicit INERT-WITH-CTA state when no steward is addressable

ADR-316 made chat a dockable command rail over the foregrounded surface. This ADR adds: when there is **no addressable steward** (base product / steward gated off), the rail renders **present-but-inert with an activation CTA** ("connect a program to enable judgment") — the ADR-369 "program tab appears on activation" pattern applied to the rail. This makes the steward a **visible upgrade path**, not a hidden feature, and avoids the dead-end of a chatbox that talks to nothing.

(Sub-decision deliberately left to implementation: inert-rail-with-CTA vs. no-rail-at-all. D4 leans inert-with-CTA for the upgrade-path legibility; a build may choose no-rail if the CTA reads better elsewhere. Either satisfies D2's "no chatbox competing with the LLMs.")

## 3. What this does NOT do

- **Does not author or delete any surface.** It re-weights `launcher_tier` *as a function of steward-presence* and names the at-rest face. The surface registry (ADR-297) is unchanged in shape.
- **Does not change render grammars.** Flow stays typed-row (ADR-289); chat stays bubble-in-rail. No narrative-into-chat merge.
- **Does not overlap with ADR-372.** ADR-372 is interop-face widget *rendering* (how a foreign host draws `trace`); this is *cockpit* IA (what the in-app operator lands on). Different faces of the moat.
- **Does not build the gating flag.** The mechanism that turns steward surfaces on/off is ADR-375. This ADR is the *target IA*; ADR-375 is the *switch*. They ship together but decide different things.
- **Does not re-derive Home.** ADR-312/369 already built the substrate-forward empty state + the additive program cockpit. This ADR *verifies* that reads as the intended default (interop-first-pivot §7 risk 3) and forbids treating it as a degraded cockpit.

## 4. Implementation sequencing (doc-first)

1. This ADR.
2. The `launcher_tier`-by-steward-presence rule (the registry read that yields the membrane-face primary set when the steward is off) — co-designed with ADR-375's flag (the flag is the input; this rule is the IA output).
3. The rail inert-with-CTA state (ADR-316 component gains the no-addressable-steward branch).
4. Verification pass on Home's empty state (ADR-312/369) — confirm it reads as the membrane face, not an ex-cockpit. Likely zero code; a screenshot-walk.

No code until this ADR + ADR-375 ratify together (they share the steward-presence input).

## 5. Rejected alternatives

- **Three co-equal tabs (ledger / membrane / steward as peers).** Rejected — this IS the struggle; the framework's Axis-2 says they are floor / face / posture, not peers.
- **A dedicated Agent tab in the base product.** Rejected (D3) — the fourth-destination trap; the agent is a posture surfaces enter, not a place you go.
- **Keep a thin substrate-assistant chatbox in base.** Rejected (D2) — competes with the LLMs the product is meant to feed; the interop-first-pivot §5 call is no-native-chat.
- **Delete the chat-first work as base-product cruft.** Rejected (D2) — it is the steward's interface, relocated to the agent beta, not sunk cost.
- **Treat Home's empty state as a degraded cockpit needing a redesign.** Rejected (D3/§4) — ADR-312/369 designed it substrate-forward on purpose; this is verification, not rework.
