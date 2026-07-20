# ADR-467 — App residency and the cast: apps have residents, the open surface offers the roster

> **Status**: **Accepted** (2026-07-20, operator-ratified in the per-agent-hardening macro discourse). Doc-first; code lands in the Designer hardening pass + named follow-on commits (§7).
> **Date**: 2026-07-20
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Identity** (Axiom 2 — which named hand a surface fronts) with a **Channel** consequence (where each colleague is addressed) and a **Substrate** consequence (the uniform lane tool surface, D4).

**Amends**:
- [ADR-463](ADR-463-capability-not-vendor-the-model-agnostic-carve.md) **D4** — the per-Agent `tools` field is retired; the lane tool surface becomes **uniform** (D4 here). ADR-463's **D4.a ceiling survives intact and strengthened**: it stops guarding per-agent variance and becomes the growth guard on the one uniform surface (a name may enter only from `READ_ONLY_PRIMITIVES`).
- [ADR-460](ADR-460-the-agent-registry.md) — the registry gains a *reading*: the kernel roster is the **cast of the open surface**; an app-level **residency** fact (D1) is layered beside it. The D3.a cliff, the row shapes, and the member-agent widening are untouched.

**Preserves** (load-bearing, untouched):
- [ADR-440](ADR-440-the-studio-the-first-authoring-app.md) **D3** — "the mind is a **bound lane**, not an agent" stands. Residency names the *default colleague* the app's lane carries; the lane remains the mechanism. The refused direction stays refused: an agent is never *confined* to an app (the `bound_only` correction of 2026-07-16 is re-ratified).
- [ADR-457](ADR-457-think-and-make-the-service-model.md) — the Think·Make verb pair, the two-front guard, and D1's caveat ("the verb names the north star, not the exhaustive job list") are the *premises* of D2 here.
- [ADR-307](ADR-307-unified-permission-taxonomy.md) — the one consequential gate. D4 makes explicit what was always true: the gate, not the per-agent allowlist, is the safety boundary.
- AGENT-TAXONOMY §4 — the classification rule (addressed operation / posture / gesture) is unchanged; D3 adds the residency test *beside* it, not over it.

---

## 1. Context — the macro question, and what the audit found

The per-agent hardening arc (audit + worksheet, `docs/analysis/base-agent-hardening-audit-and-discourse-2026-07-18.md` + `per-agent-hardening-worksheet-2026-07-19.md`) paused on the operator's macro challenge: *is the 4-character roster + model-decoupling even the right mix?* The independent re-audit (2026-07-20) surfaced three facts that reframed it:

1. **The codebase holds two contradictory positions on capability.** The Designer row states the principle — *"EVERY AGENT CAN MAKE THINGS… **Capability is uniform; character is the differentiator**"* (`agents_registry.py:150-156`) — while ten lines up, Scout's `tools` field makes capability non-uniform (ADR-463 D4). Both are ratified; they cannot both hold.
2. **The per-agent capability plane is a bug factory with no safety payoff.** The only real defect this arc ever found (Scout's declared-but-undispatchable tools, fixed `5ba26e1`) existed *because* there was a per-agent allowlist to get wrong — and a second latent instance of the same class was found in the re-audit: `lane_tools_openai`'s hardcoded `by_name` dict silently drops any future grant outside its seven schemas (`lane_runner.py:186-212`), so the next per-agent grant (the worksheet's revision-reads candidates) reproduces the Scout bug in mirror form. Meanwhile the safety argument for withholding is empty by construction: every grantable tool is *derived* non-consequential (`permission.py::READ_ONLY_PRIMITIVES` — the ADR-307 gate's own set). The allowlist was never the boundary; the gate was.
3. **Each base agent's distinction is owned by another layer.** Researcher's = tools (uniformable) + a posture line. Designer's = the Studio binding — which the code itself insists is *"a fact about the LANE, not about Designer."* Thinker's = nothing (the default with a name). Critic's = a stance (already re-typed as a posture). The operations taxonomy is a sound *classification* rule but supplied no *membership* rule — nothing said when a character earns a kernel row.

The operator then supplied the missing rule from the app layer: Studio is architecturally an **app** (ADR-440 "the second app class"; ADR-451 the surface-owning app for `.html`; ADR-457 D6 the MacWrite/MacPaint doctrine), and it is **already mapped to Designer** — `agent: 'designer'` hardcoded at both lane-creation sites (`StudioSurface.tsx:264`, `:2136`). The mapping is real, live, and **one-directional**: the app pins its colleague; the colleague is never confined to the app. This ADR canonizes that direction and derives the roster's growth rule from it.

## 2. D1 — Residency is an app-layer fact

**An authoring app declares its resident agent.** The resident is the colleague the app's bound lane carries by default — today: **Studio → `designer`**. The declaration moves out of the two hardcoded strings in `StudioSurface.tsx` into a small app-layer declaration (an `AUTHORING_APPS` table beside the ADR-436 viewer registry: `{id, resident}`), consumed by every bound-lane create site. IMAGES (ADR-468) adds its row when it ships.

The direction is the whole decision, restated so it cannot drift:

- **App → agent** (the default colleague): ratified, live, now declared. ✅
- **Agent → app** (confinement): refused — twice already (ADR-440 D3; the `bound_only` removal), re-ratified here. An agent is an ordinary member-hand everywhere; you can chat with Designer, hire your own based on it. ❌

Residency changes *no runtime mechanism*: the lane remains the mind (ADR-440 D3), the lane row persists the agent, attribution stays `member:{id} via {model}`. Residency is a creation-time default made legible — nothing more.

## 3. D2 — The open surface has a cast, not a resident

Chat is **not** Thinker's app, and gets **no** resident. The operator's argument, checked against canon and confirmed: chat is the member's-hands surface (ADR-408 A2), the open commons room — the OS's Finder/Terminal, not an app with one job. ADR-457 D1 says it itself: chat retains the operational jobs *as means*. An app has one job, so it pins one resident; the open surface has all jobs, so it offers the **roster** — the faces picker at the chat door is the correct architecture *as shipped*, not a gap awaiting a default.

The deep-work symmetry that seals it: deep-*make*'s output has a dedicated surface (Studio); deep-*think*'s output already has one too — **the settled file in the commons** (think → settle → make, ADR-457 D2). No "deep Think app" is invented ahead of demand; if one is ever demanded, it arrives under D3's rule like any other app, with its resident.

## 4. D3 — The roster's growth rule: residents arrive with apps

The taxonomy's classification rule (AGENT-TAXONOMY §4) stands unchanged — a base row still requires an irreducible **addressed operation**. This ADR adds the membership discipline the taxonomy lacked:

- A new **resident** arrives only *with* a new first-party app (the MacWrite/MacPaint doctrine applied to the roster: each app ships with its colleague). One agent may hold multiple residencies (Designer resides in Studio *and* IMAGES — same addressed operation, two apps).
- A new **output shape** (image, video, deck…) is a **modality of Designer's make** — Axis-1, re-affirmed. "Image maker" is not an agent (ADR-468 D5 applies this).
- A new **stance** is a posture (`KERNEL_POSTURES`) or a member skill — never a row.

Today's ledger under this rule: **Designer** is the only resident (Studio). **Thinker, Researcher, Critic** are the cast of the open surface — addressable characters, no app, and that is a *stable* state, not a deficiency. The roster does not shrink; it stops being asked to justify itself by persona taste.

## 5. D4 — Capability goes uniform

**The per-agent `tools` field is deleted. Every lane serves the same tool surface: the five file verbs + `QueryKnowledge` + `WebSearch` — the seven, uniformly.**

- **Why uniform**: resolves the §1.1 contradiction in favor of the code's own stated principle; kills the Scout-bug class *structurally* (no per-agent variance → nothing to disagree about → the `by_name` latent bug dies unexercised); and ends the withholding absurdity — `QueryKnowledge` is the semantic recall we ship to strangers over MCP (ADR-368) while our own Thinker could only grep. Character remains the differentiator: Researcher's search-order discipline lives on in its posture, where the taxonomy says distinction belongs.
- **Why seven, not the full sixteen-primitive read pool**: tool-choice quality on small engines degrades with surface width, and the remaining reads (entity/revision/introspection) have no demonstrated lane job. The pool stays available — but any addition is a *uniform* addition, evidence-gated, entering through the D4.a ceiling (`READ_ONLY_PRIMITIVES` derivation, retained as the growth guard and CI-asserted).
- **What survives of ADR-463 D4**: the ceiling (D4.a), the schema-derivation discipline, and the three-way invariant (payload == allowlist == prompt), which simplifies to one set for every lane and generalizes in the gate from "scout + plain lane" to *all* lanes. `lane_tools_openai` gains a loud-failure guard: a surface name with no schema is an error, never a silent drop.
- **What members feel**: Thinker, Designer, Critic (and every member-authored colleague) gain recall + web. The prompt's `## Your tools` line stays honest automatically (it already derives from the same source, `5ba26e1`).

## 6. D5 — Sequencing: the Designer pass is next; Think is not

The next hardening pass runs on **Designer** — under this ADR that means the Studio lane's *composed mind* (Designer character + studio posture + design-system section + derive section), worksheet-procedure, opening with the first-ever observed bound-Studio turn. The pass now shapes the resident of **two** apps (ADR-468). No Think-side work is scheduled: D2 canonized the chat door as-is.

## 7. Implementation ledger (each its own commit; none in this doc commit)

1. `api/services/agents_registry.py` — delete `tools` from the scout row + `AGENT_ROW_KEYS`; retire `resolve_agent_tools` per-agent resolution (the uniform surface is a lane_runner constant; the D4.a derivation moves to the gate + a loud composition guard).
2. `api/services/lane_runner.py` — `LANE_SURFACE_EXTRA = ("QueryKnowledge", "WebSearch")` uniform; `lane_tool_names`/`lane_tools_openai`/both loop allowlists/`tools_line` read it; schema-miss becomes loud. `api/prompts/CHANGELOG.md` entry (the `## Your tools` line changes for non-scout lanes).
3. `web/` — `AUTHORING_APPS` declaration (`{id: 'studio', resident: 'designer'}`); both `StudioSurface.tsx` create sites consume it.
4. `api/test_agent_registry.py` — invariant generalized (every kernel character + member agents: payload == allowlist == prompt == the uniform seven); uniform-extra ⊆ `READ_ONLY_PRIMITIVES` asserted.
5. Worksheet updated as passes run (Designer first — order note landed with this ADR).

## The one-line statement

**Apps have residents and the open surface has a cast: an authoring app declares the colleague its bound lane carries (Studio→Designer — the app pins the agent, never the reverse), chat keeps its roster door with no default, a kernel agent earns residency only by an app arriving to house it while output shapes stay Designer's modalities and stances stay postures, and capability goes uniform at seven tools for every lane (the gate was always the boundary; the per-agent allowlist was only ever a bug factory) — so character, not configuration, is what distinguishes the colleagues.**
