# ADR-449: The Design-System Contract — Skin as a Workspace Convention, Cited by Reference

> **Amended by ADR-453** (2026-07-13): the D5 named handoff LANDS — the mechanical picker lives in
> the Design tab's document scope (discovery on `GET /studio/vocabulary`, composition via
> `GET /studio/design-systems/resolve`, apply/remove through the one mechanical door). The
> cascade order gains a middle layer: unmarked layout style < `data-kernel` (ADR-453 tokens) <
> `data-skin` (this ADR) — the skin still wins.

**Status**: Accepted (2026-07-12, operator-ratified direction — the third step of the
[load-bearing-files note](../analysis/load-bearing-files-are-a-graph-fact-the-reference-edge-derive-step-and-design-system-2026-07-12.md) §6,
unblocked by ADR-447's ratification). Fills the **Skin** layer ADR-447 D1 explicitly named
out-of-scope. v1 is the workspace-side contract + the bound-lane consumption face; the mechanical
picker UI is a **named handoff** to the ADR-447 D7 inspector (its files are in-flight in a
concurrent implementation pass — this ADR deliberately touches none of them).
**Date**: 2026-07-12
**Dimension**: Substrate (Axiom 1 — the design system is ordinary meaning-foldered substrate; the
artifact carries its skin declaration in its own DOM) + Mechanism (the apply is a deterministic
rule) + Channel (the bound-lane posture).

**Amends**: ADR-443/444 (the layout-switch rule "replace the `<style>` skin" refines to "replace
the UNMARKED style element" — the artifact now has two style regions, D2) · ADR-447 (fills the
named-out-of-scope fourth layer; assigns the picker to the D7 inspector's Design section).
**Preserves**: ADR-448 (the reference edge is CONSUMED, not extended — the skin citation is an
ordinary `data-ref` the write-door lift already records) · ADR-209/444 (no new write path — the
lane applies through its file verbs; the future mechanical apply goes through the same one door) ·
ADR-414 (pure genesis — no design system is seeded; the kernel ships the category, never an
instance) · ADR-434 (protection stays the powerbox grant; a design system earns no folder class) ·
ADR-443 R1 (the DOM is the model — the skin declaration lives in the artifact, no sidecar).

---

## 1. Context — the Skin layer is named but unbuilt; the operator's case is concrete

ADR-447 D1's four-layer table names **Skin — "how it looks (design system)", annotation `<style>`,
out of scope**. As committed, an artifact has exactly ONE `<style>` carrying the *layout's*
structural + visual CSS, rewritten wholesale on a layout switch — there is nowhere for a
workspace-owned visual identity to live, and nothing that survives a layout switch.

The operator's concrete case: a design system exported from another tool (tokens/, styles.css,
components/, guidelines/, a manifest) that downstream Studio artifacts should be "based on" — the
canonical **load-bearing shared document**. The load-bearing-files note ruled what its "managed
architecture" is: a meaning-folder + a consumption contract + reference edges + optional powerbox
narrowing — never a kernel file-type or a protected folder class.

## 2. The decision in one sentence

**A design system is an ordinary meaning-folder identified by a `_design.yaml` manifest; an
artifact wears it as a second, MARKED style element (`<style data-skin="true"
data-ref="<manifest path>">`) that overlays the layout's skin, survives layout switches, and —
because the declaration is an ordinary `data-ref` — lands the ADR-448 reference edge on every
write; v1's consumption face is the bound lane (posture-taught, executed with its own file
verbs), and the picker UI is handed to the ADR-447 D7 inspector.**

## 3. Decisions

### D1 — A design system is a manifest-identified meaning-folder (no kernel registry, no seeding)

Any workspace folder containing a **`_design.yaml`** manifest is a design system:

```yaml
name: YARNNN Design System        # display name
css:                              # ordered, folder-relative CSS sources
  - styles.css
  - tokens/colors.css
```

Machine-parsed per the §9 file-format discipline (`_*.yaml`, `load_workspace_yaml`). The folder
lives wherever the operator's meaning puts it (a peer home like `design-system/`, or inside a
project folder — the path carries no semantics). **Nothing is seeded** (ADR-414): the kernel names
the category; the operator (or a lane, deriving the manifest FROM the folder's files and citing
them — ADR-448 dogfood) authors the instance. Discovery = the manifest search; there is no
registry row to maintain.

### D2 — The artifact wears its skin as a second, marked, cited style element

The artifact's `<head>` now has two style regions with distinct owners:

| Element | Owner | Replaced by |
|---|---|---|
| `<style>` (unmarked) | the kernel layout (`STUDIO_LAYOUTS[...].skin` + shared CSS) | a layout switch |
| `<style data-skin="true" data-ref="<manifest path>">` | the workspace design system | a design-system apply |

The marked element sits **last in `<head>`** — the workspace's visual identity overrides the
layout's defaults by cascade order, no `!important` machinery. `data-ref` points at the
**manifest** (the design system's identity file); `data-ref-rev` may pin the applied revision
(optional in v1). Because the declaration is an ordinary `data-ref`, **the ADR-448 write-door lift
records the edge automatically** on every artifact write: the manifest's dependents are the
artifacts wearing it, the Files delete-confirm warns before it is trashed, and `trace` walks
artifact → design system. No new mechanism — the contract is one attribute.

### D3 — The apply is a deterministic rule (executable spec, one write door)

Applying design system S to artifact H: **replace H's existing `<style data-skin…>` element with
S's composed element (manifest's `css` sources concatenated in order); if none exists, insert it
immediately before `</head>`. A layout or arrangement switch replaces only the UNMARKED style
element and never touches the marked one** (the amendment to ADR-443/444's switch rule). The rule
ships as a pure function (`services/design_systems.py::apply_skin_to_html`) so the lane's
behavior, the future mechanical apply, and the gate all share one spec. Removing a design system =
removing the marked element (an ordinary edit).

### D4 — v1's consumption face is the bound lane (posture-taught, file-verb-executed)

When (and only when) the workspace contains at least one design system, the bound-lane posture
gains an additive **Design system** section (composed in `lane_runner` beside the Studio posture —
NOT in `services/studio.py`, whose posture frame is in-flight in the ADR-447 pass): it names the
workspace's design system(s) by manifest path and teaches the D2/D3 contract — read the manifest +
its css with your file verbs, apply via the marked element, cite via `data-ref`, never drop the
marked element on a layout switch. No design system → no section (zero prompt cost — the
envelope-dilution discipline). The operator's v1 path is therefore: drop the folder in, get a
manifest written, tell the Studio lane "use the workspace design system."

### D5 — The picker UI is the ADR-447 D7 inspector's Design section (named handoff)

The mechanical face — list design systems, thumbnail/preview, one-click apply through the CAS
door — belongs in the D7 contextual inspector beside Arrange, served registry-shaped like
arrangements. It is **not built here**: the inspector and `services/studio.py` are actively under
construction in the ADR-447 pass. What this ADR guarantees the inspector: discovery
(`find_design_systems`), resolution (`resolve_design_system`), composition
(`compose_skin_element`), and the apply rule (`apply_skin_to_html`) are already server-side pure
functions it can wire without re-deriving the contract.

### D6 — Named-deferred

- **Kernel preset skins** (a curated default gallery) — only if demanded; the category ships
  empty by design.
- **Pin semantics UX** (`data-ref-rev` stamping + "update to latest" affordance) — rides the
  inspector.
- **Per-design-system write-narrowing** — already possible today (one powerbox grant row on the
  folder's objects, ADR-434); a recipe, not a build.
- **The Files "referenced by" badge** — the dependents endpoint exists (ADR-448); the badge is a
  Files-surface pass.

## 4. Cascade / blast radius

- **New**: `api/services/design_systems.py` (manifest parse · discovery · resolve · compose ·
  apply rule · posture section) + `api/test_adr449_design_system.py`.
- **Edited**: `api/services/lane_runner.py` (one additive posture-section call for bound lanes);
  `api/prompts/CHANGELOG.md`.
- **Deliberately NOT touched** (in-flight ADR-447 files): `api/services/studio.py`,
  `api/routes/studio.py`, `docs/design/STUDIO.md`, `web/components/studio/*` — STUDIO.md's Skin
  row flips from "out of scope" to a pointer here as part of the D7 pass or a follow-on doc
  commit once that file is released.
- **Schema**: none. **Migrations**: none. **New endpoints**: none (the posture builder queries
  server-side; the inspector wires endpoints when it lands).

## 5. Why this shape

The alternatives the note already rejected stay rejected: a kernel skin registry would make the
kernel ship instances (ADR-222/343 violation); a protected `design-system/` folder class would
re-import permission-as-location; a sidecar "which skin" table would break DOM-is-the-model. One
manifest convention, one marked element, one ordinary `data-ref` — the design system becomes
exactly as load-bearing as the graph says it is, visibly (dependents), protectably (powerbox),
and portably (the artifact carries its own declaration).
