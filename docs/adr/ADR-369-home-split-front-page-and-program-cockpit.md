# ADR-369 — The Home Split: a kernel-shaped front page and a program-shaped cockpit (one surface, two tabs)

> **Status:** **Accepted + Implemented (2026-06-25).** FE-only structural change: the `home` surface gains an internal segmented control and its slots redistribute across two composition bodies (kernel-shaped vs program-shaped). No schema, primitive, backend, or Render-service change. **Consciously reverses** ADR-312's one-composition unification (§1) — the operator ratified the reversal as "the first-principled correct one."
>
> **Implementation (2026-06-25):** `HomeRenderer` gained the segmented control + the `home.tab` window-namespaced param (`useSurfaceParam('home')`, default `home`, SSR-safe). Two composition bodies extracted (Singular Implementation — slots MOVED, not rebuilt): `HomeFrontPage` (the §D4 kernel slots: constitution band → decision queue [acts in place] → visual recents → recent artifacts → judgment trail) + `ProgramCockpit` (the relocated `StandingBand` head + the `program_sections` dispatch). New `HomeRecents` (the §D4/§D6 visual recents) reuses the Files-recents data source (`api.workspace.recentRevisions`), distinct from `KernelRecentArtifacts`. The program tab is additive (renders only on `active_bundles`), labeled from the active bundle's MANIFEST title (ADR-222 — no kernel program noun). Gates: `api/test_adr369_home_split.py` (7/7) + sibling-gate updates for the relocation (`test_adr367_home_cockpit.py`, `test_adr312_home_as_composition.py` repointed to the extracted bodies; `test_adr331_setup_rendering.py` CTA read repointed) — full affected set `test_adr369/367/312/350 -q` = 37/37 PASS; `tsc --noEmit` clean; nav cross-surface ratchet green. Files: `web/components/library/HomeRenderer.tsx` (modified) + `web/components/library/kernel-home/{HomeFrontPage,ProgramCockpit,HomeRecents}.tsx` (new).
> **Date:** 2026-06-25
> **Authors:** KVK (operator) + Claude (collaborator)
> **Discourse base:** the operator's two-tab regroup (2026-06-25) — *"split Home into a general (default) Home tab and a program tab; the existing scatter between generic and program-specific information gets split; some content spills over but the layout/components should be separated. The reason is both developer division-of-concerns and the first-time user — if it's ambiguous to code, it's ambiguous to users."* Plus the home-home content direction: *notifications as one of the first sections, then a more visual re-representation of the Files "Recents" concept.*
> **Reverses:** [ADR-312](ADR-312-home-as-composition.md) D1's *one-composition* thesis (the cockpit dissolves into a single Home that morphs substrate-forward → operation-forward). The kernel/program *slot-ownership* seam ADR-312 drew (kernel renders the universal slots; the program declares `home.program_sections`) is **preserved and promoted** — this ADR makes that existing seam navigational. ADR-312's progressive-density answer to the cold-start question is preserved differently (§D2: the program tab is additive, appearing on activation).
> **Amends:** [ADR-367](ADR-367-home-as-operating-cockpit.md) — the cockpit *density* and the ADR-350 standing band relocate from Home to the program tab (the standing obligation is program-shaped, §D5); ADR-367's *"acts in place"* principle is **preserved** and now spans both tabs wherever a consequential affordance lives (Home keeps it on the kernel-universal decision queue). [ADR-349](ADR-349-launcher-ia-re-sort.md) (the `home` launcher tile is unchanged — the split is intra-surface, not a new launcher destination, §D2).
> **Preserves:** [ADR-222](ADR-222-agent-native-operating-system-framing.md) (the kernel names a generic program-composition tab; the **program** names + shapes it via its MANIFEST — no program noun hardcoded in the kernel), [ADR-307](ADR-307-unified-permission-taxonomy.md) (one gate, one queue), [ADR-358](ADR-358-layout-mode-canvas-vs-desktop.md) D6 (the tab state is a window-namespaced param `home.tab`), [ADR-346](ADR-346-operation-composition-surface.md)/[ADR-349](ADR-349-launcher-ia-re-sort.md) (Notifications stays the breadth act-workbench), ESSENCE two-layer model (the split *expresses* Layer 1 / Layer 2 navigationally).
> **Dimensional classification:** **Channel** (Axiom 6 — the spatial arrangement of the operator's surfaces) projected through **Identity** (Axiom 2 — kernel-shaped vs program-shaped authorship of each slot).

---

## 1. The reversal, stated honestly

ADR-312 D1 unified the cockpit into **one** Home composition — a single surface that is substrate-forward when empty and operation-forward when a program runs — and superseded ADR-228/273 (the program-shaped cockpit surface) to do it. The unification's virtue was that the operator never chooses a tab and never faces an empty second surface.

This ADR re-splits. The justification is the operator's own diagnostic, which is sound: **the kernel/program seam already exists in the code** — `HomeRenderer` renders the kernel-universal slots itself; the program-shaped slots come from `SURFACES.yaml home.program_sections`. The two are interleaved in one surface today, which means the surface's layout mixes two authorship origins with no visible boundary. *"If it's ambiguous to code, it's ambiguous to users."* Making the existing code seam a navigational boundary is a division-of-concerns win for the developer and a legibility win for the first-time operator — and it lets the generic Home be **identical regardless of program**, the most learnable possible default.

This is not anti-canon: it is ADR-228/273's program-cockpit instinct returning as an **additive tab within the one Home surface**, rather than as the morphing of a single composition. ADR-312 was right that the *generic* front page is a kernel composition; this ADR adds that the *program-shaped* cockpit deserves its own register beside it.

## 2. The decision

### D1 — The split axis is *kernel-shaped vs program-shaped* (the layout/component seam), not strictly Layer-1/Layer-2

The two tabs divide on **who shapes the slot** — the kernel (same rendering for every workspace) vs the active program (declared via `home.program_sections`). This is the axis that determines *layout and components*, which is the operator's stated concern.

It correlates with ESSENCE's Layer-1 (substrate floor) / Layer-2 (program) seam but is **not identical** — and they diverge in exactly one slot, the **constitution band** (the mandate). Declaring a mandate is "Layer 2" in the product story, but the band's *rendering shape is kernel-generic* (a mandate one-liner + autonomy posture, rendered identically for any program by `HomeHeader`). **Tiebreaker: a slot follows its rendering shape, not its product layer.** So the constitution band — kernel-shaped — stays on **Home**. Naming this rule is the first-principled crux: the split is about *shape*, because shape is what the operator sees and what the code separates.

### D2 — Mechanism: one `home` surface, an internal segmented control

`slug: home`, route `/home`, `HomeRenderer` — **unchanged as a surface.** It gains a segmented control at its head with two tabs:

- **Home** (default) — the kernel-shaped front page.
- **‹Program›** — the program-shaped cockpit, **labeled by the active program** (`MANIFEST.display_name`; e.g. "Alpha Trader"). Per ADR-222 the kernel provides a generic program-composition tab; the program names and fills it. Generic fallback label "Operation" only if a program declares none.

Tab state is a **window-namespaced param** `home.tab ∈ {home, <program-slug>}` (ADR-358 D6), default `home`, SSR-safe (server renders the default; the post-mount effect applies the stored/param choice). The program tab is **additive**: when no program is activated it does not render (Home-only) — preserving ADR-312's cold-start virtue (no empty second surface; Layer-1 operators see exactly one tab). The `home` launcher tile is unchanged (the split is intra-surface; not a second launcher destination).

### D3 — Slot allocation

| Slot | Shape | Tab |
|---|---|---|
| Constitution band | kernel (HomeHeader) | **Home** (shape tiebreaker, §D1) |
| Decision queue (acts in place) | kernel-universal (ADR-307) | **Home** |
| Recents (visual) | kernel (substrate changes) | **Home** (§D4/D6) |
| Recent artifacts | kernel (delivered outputs) | **Home** |
| Judgment trail | kernel (persona seat ledger) | **Home** |
| Ground-truth hero | program-declared | **‹Program›** |
| Live entities | program-declared | **‹Program›** |
| Standing obligation | program-derived (owed-output) | **‹Program›** (relocates from Home — §D5) |
| Dense program detail (positions, expectancy, watch) | program-shaped | **‹Program›** (program-bundle scoped) |

Content may still be program-*flavored* on Home (a trade proposal in the decision queue): the *queue* is kernel-shaped (Home), the *proposal body* is the program's (rendered in the shared modal). Shape decides the tab; flavor does not.

### D4 — The Home (front-page) tab: order

Per the operator's direction, the Home tab is a calm Layer-1 front page, ordered for "what needs me / what's been happening":

1. **Constitution band** (thin — the operation's charter / activation entry).
2. **Notifications** — the decision queue, acting in place (ADR-367). First substantive section: what needs your OK.
3. **Recents (visual)** — a card/visual re-representation of the Files "Recents" (recent attributed substrate changes), richer than the Files table.
4. **Recent artifacts** — delivered outputs ("the dividends").
5. **Judgment trail** — the Reviewer's recent calls.

### D5 — The standing obligation relocates to the program tab (amends ADR-367)

ADR-367 §D4 placed the ADR-350 `StandingBand` (owed-vs-actual + standing intent) on Home's head. The standing obligation is **program-derived** (budget→pace × *mandate*→output kind+volume × bar — ADR-344/DP30), so under the shape axis it is program-shaped and moves to the **‹Program›** tab head. ADR-367's *"acts in place"* principle is unchanged and now spans both tabs: Home acts in place on the decision queue; the program tab acts in place on its own consequential affordances. Home is the calm front page; the **program tab is the dense operating cockpit** ("robust and detailed, acts in place" — the cockpit density relocates here).

### D6 — Recents vs recent artifacts

These are distinct and both stay on Home: **Recents** = broad recent *substrate changes* (the Files-recents data, visualized); **recent artifacts** = the narrow set of *delivered outputs* (the "dividends," ADR-312 slot #5). They render as two sections (recency-broad vs delivered-narrow), not merged — merging would hide the "what did the operation ship" signal inside "what changed."

### D7 — Three act-bearing surfaces, justified

The split yields three surfaces that can act: **Home** (front-page decide-in-place on the kernel queue), **‹Program›** (operate the program deeply), **Notifications** (the breadth queue/activity/schedule workbench). This is deliberate tiering, not duplication — each owns a distinct primary job and interaction altitude (front-page glance-and-clear · deep operate · breadth workbench), the same Control-Center/System-Settings principle ADR-367 §D3 ratified. The ADR records the division so the three never collapse into "three places that do the same thing."

## 3. What this does NOT do

- **Does not add a launcher destination** — the split is intra-surface (`home.tab`); the `home` tile is unchanged.
- **Does not hardcode a program noun** — the program tab is a generic kernel slot the active program names + shapes (ADR-222).
- **Does not change the gate, queue, schema, primitives, backend, or any Render service** — FE-only.
- **Does not demote Notifications** — it stays the breadth act-workbench (ADR-367 §D3).
- **Does not leave an empty second view at cold start** — the program tab is additive, appearing only on activation (ADR-312's cold-start virtue preserved).

## 4. Doc cascade (same commit as implementation)

- **New:** this ADR.
- **Amend banners:** ADR-312 (one-composition reversed → two-tab split; the kernel/program slot seam promoted to navigational), ADR-367 (cockpit density + standing band relocate to the program tab; "acts in place" spans both tabs), ADR-349 (home tile unchanged — note the intra-surface split).
- **FOUNDATIONS DP29:** second amendment — a composition surface may host **two registers via an internal tab** when one register is kernel-shaped and the other program-shaped; the split axis is rendering-shape (the layout/component seam), with the program register additive on activation.
- **GLOSSARY:** the **Home** entry gains the two-tab structure (front page / program cockpit) + the shape-axis rule.
- **CLAUDE.md:** surface-model addendum + ADR ledger.
- **No CHANGELOG** — no prompt/tool change.

## 5. Implementation outline (Implemented 2026-06-25)

FE-only, Singular Implementation:
- `HomeRenderer` gains a segmented control + `home.tab` param (`useSurfaceParam('home')`), default `home`; the program tab renders only when `active_bundles` is non-empty, labeled from the bundle MANIFEST.
- Two composition bodies extracted: `HomeFrontPage` (kernel slots, the §D4 order) and `ProgramCockpit` (the `home.program_sections` dispatch + the relocated `StandingBand`). The existing `dispatchComponent(section.kind)` path moves into `ProgramCockpit`.
- `StandingBand` moves from Home's head to `ProgramCockpit`'s head (ADR-367 §D4 mount relocates).
- New `HomeRecents` (visual) — reuses the Files-recents data source; distinct from `KernelRecentArtifacts`.
- Gate `api/test_adr369_home_split.py` (FE source-guards): home.tab param + default; program tab additive (hidden without active bundle); kernel slots on the Home body, program_sections + StandingBand on the program body; `home` launcher tile unchanged.
- `tsc --noEmit` clean; sibling gates (ADR-312/350/367) updated for the relocation.

## 6. Related

- [ADR-312](ADR-312-home-as-composition.md) — Home as composition (the one-composition thesis this splits)
- [ADR-367](ADR-367-home-as-operating-cockpit.md) — Home as operating cockpit (density + standing band relocate to the program tab; "acts in place" preserved)
- [ADR-222](ADR-222-agent-native-operating-system-framing.md) — kernel/program boundary (the program names its own tab)
- [ADR-358](ADR-358-layout-mode-canvas-vs-desktop.md) — window-namespaced params (`home.tab`)
- [ADR-346](ADR-346-operation-composition-surface.md) / [ADR-349](ADR-349-launcher-ia-re-sort.md) — Notifications (the breadth workbench, preserved)
- [ESSENCE](../ESSENCE.md) — the two-layer model the split expresses navigationally
