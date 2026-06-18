# ADR-341 — Two Settings Doors: System Settings + Workspace Settings

**Status:** **Accepted + Implemented (2026-06-18)** — same session. Gate `api/test_adr341_two_settings_doors.py` 43/43. Sibling gates updated to the two-door contract + green: ADR-340 P2 78/78 · P3 19/19 · ADR-338 parity 15/15 · ADR-338 sources 37/37; untouched siblings green (ADR-340 P1/P4/D8, ADR-312, ADR-327, ADR-297). `tsc --noEmit` clean. Implementation refinement vs the drafted D2: the constitution panes reuse the existing `*Card` full variants (window→pane, ADR-340 P2 pattern) rather than building "read summary + Files deep-link" — same read-mostly intent, zero new components (see D2).

**Date:** 2026-06-18
**Deciders:** KVK (operator) + Claude (collaborator)
**Hat:** A (system canon)

> **Discourse base:** live launcher walk against the founder's own eyes (continuing the ADR-340 operator-experience arc). The presenting instinct: "carve out a Workspace Settings alongside System Settings, and move workspace-related sub-surfaces over." Grounded against the ADR-320 five-root substrate topology, the instinct resolves to a real seam.

**Amends:** ADR-340 D4 (the "one System Settings door" consolidation — this ADR splits it into two coherent doors and adds a launcher tier for them). ADR-297 (launcher tier model gains a `configure` tier).
**Preserves:** ADR-312 D5 (the constitution stays **first-class on the Home band**; the Workspace Settings constitution panes are a *read/manage* destination, not a replacement of the band — two surfaces, two jobs, like macOS wallpaper shows on the Desktop and is set in System Settings). ADR-309/312 three-register model (registers stay **code-level taxonomy**; the two doors are an operator-facing *view* over registers, not a register change — ADR-340's "registers stop being the user-facing sort key" principle is honored). ADR-244/ADR-206 D6 (substrate authoring stays in chat/Files; Settings is read-mostly with zero inline substrate editors). ADR-320 (the five-root permission topology is the *grouping rationale*). ADR-331 (Setup stays a window-grade Sequence surface in Utilities).

---

## 1. Problem statement

ADR-340 D4 consolidated the seven `os-config` launcher tiles into **one** System Settings door, on the macOS principle "depth under one well-named door is cheap; top-level breadth is expensive." That was the right move against the launcher-as-wall symptom. But the single door conflates **two genuinely different objects** that the substrate already separates:

- **The OS governing the agent** — Autonomy, Budget. Program-agnostic, machine-level, identical in every workspace regardless of which program runs. The operator does not author these to *declare what the workspace is*; they set guardrails on the agent's behavior. Substrate root: `governance/` (operator-only ceilings the agent runs under but **cannot write** — ADR-320).
- **This operation's configuration** — Program (which operation runs), Connectors + Sources (what it perceives), and the Constitution (Mandate / Identity / Principles — what it's *for*). Workspace-specific, changes per program. Substrate roots: `constitution/` + `operation/` + `persona/` (the agent **amends** these — ADR-320).

The macOS analogy that justified "one door" does not actually say *everything* lives behind System Settings: a Mac has **System Settings** (the machine — network, battery, privacy) *and*, per-app, **app Preferences** (that app's own config). YARNNN's `os-config` register was wearing one coat over two objects. ADR-320 already drew the boundary as a *permission* line (`governance/` agent-can't-write vs `constitution/`+`operation/` agent-amends); the launcher just didn't reflect it.

The seam is real and substrate-backed. The fix is two doors, each internally coherent — not depth-under-one-door, because these are two objects, not one object with sub-sections.

## 2. Decision

### D1 — Two top-level Settings doors

| Door | Object | Substrate roots | Panes |
|---|---|---|---|
| **System Settings** | the OS — program-agnostic, machine-level | `governance/` + account | **Governance:** Autonomy · Budget · **General:** Billing · Usage · Account |
| **Workspace Settings** | this operation — what I'm running | `constitution/` + `operation/` + `persona/` | **Constitution:** Mandate · Identity · Principles · **Operation:** Program · **Perception:** Connectors · Sources |

The connectors-ambiguity that "one door" worried about (is Connectors a system thing or a workspace thing?) resolves cleanly: connectors/sources are *what this operation perceives* → Workspace Settings. They bind transports the operation declares, not machine-level OS config.

### D2 — Constitution panes reuse the existing read-cards; no new editors

The pinned decision was "read-only summary + deep-link to Files." Implementation found a cleaner realization that satisfies the same intent with **zero new components**: the constitution surfaces (`mandate`/`identity`/`principles`) were already window-grade thin `SurfacePage` wrappers around `MandateCard` / `IdentityBrandCard` / `PrinciplesCard` **full variants** — read-mostly cards that self-fetch and render the file with an "Edit via chat" affordance. ADR-341 makes these surfaces **pane-grade** (exactly as ADR-340 P2 did for budget/autonomy/program): their `/mandate` etc. routes become ADR-308 redirect stubs → `/workspace-settings?pane=…`; their standalone page components are **deleted**; the existing cards render inside the Workspace Settings **Constitution** panes via `SurfaceRegistry`. This is consistent with ADR-244 read-mostly + ADR-206 D6 (authoring stays in chat/Files) + ADR-244 D7 (no inline substrate editors in Settings) — the cards are read-views, not editors.

The constitution band on Home is **unchanged** (ADR-312 D5 preserved): `HomeHeader.tsx` consumes the cards directly, not the deleted `/mandate` routes, so the first-class band door survives. Workspace Settings is the durable read/manage *pane* door; the band is the cold-start activation door. Two doors, two jobs.

This also resolves the registry-parity invariant ("a pane-grade slug must not carry a window component"): post-ADR-341 the constitution surfaces are pure panes, their window components gone.

### D3 — A new `configure` launcher tier holds both doors

ADR-340 P3's at-rest launcher tiers (`primary` / `system` / `utilities` / `search-only`) gain a **`configure`** tier between Workspace (primary) and Utilities, holding both Settings doors. The `system` tier is retired as a single-member tier — System Settings moves to `configure`. At-rest launcher:

```
WORKSPACE   Home · Feed · Queue · Files          (the loop: dwell/read/decide/artifacts)
CONFIGURE   System Settings · Workspace Settings  (tune the machine / shape the operation)
UTILITIES   Setup · Activity · Recurrence · Agents (the Activity-Monitor class)
```

Pane-grade surfaces stay `search-only` (found by flat search; their door is their parent container). Constitution panes (mandate/identity/principles) become `pane_of: "workspace-settings"`, joining the search-only class — their *band* door (Home) is unchanged; their *pane* door is Workspace Settings.

### D4 — Registers stay code taxonomy; doors are a view over them

No register change (ADR-340 principle: registers stopped being the user-facing sort key). The three registers (`intent` / `os-config` / `application`) are unchanged. Door membership is expressed entirely through `pane_of` (which container a pane folds into) — `pane_of: "settings"` (System Settings) vs `pane_of: "workspace-settings"` (Workspace Settings). A pane's register is orthogonal to its door, exactly as pane-grade was orthogonal to register in ADR-340 P2.

### D5 — Singular Implementation: one pane-container shell, two mounts

The two doors do **not** become two near-duplicate 1000-line page components. The settings page refactors to a shared pane-container shell parameterized by its pane set; `/settings` and `/workspace-settings` each mount it with their own `PANE_GROUPS`. The pane→parent resolution (`foregroundSurface` reading `pane_of`, the viewport filtering pane-grade slugs, the redirect-stub pattern) is **already generic** in the codebase (`useSurfacePreferences.tsx:478` reads `entry?.pane_of` with no hardcoded `"settings"`) — adding a second container is registry data + one mount, not new machinery.

### D6 — Pane re-homing + redirect stubs

Panes moving from System Settings to Workspace Settings (`program`, `connectors`, `sources`) change `pane_of: "settings"` → `pane_of: "workspace-settings"`. Their legacy `/settings?pane=…` deep-links continue to resolve via the canonical param (`?pane=` on the new container); the old window routes stay ADR-308 redirect stubs (now → the appropriate door). `foregroundSurface('connectors')` keeps working pane-blind — it resolves to whichever parent the registry declares.

## 3. What this is NOT

- Not a register change (D4). The `intent`/`os-config`/`application` taxonomy is untouched.
- Not constitution-moves-off-Home (D2 + ADR-312 D5 preserved). The band stays; the panes are an additional read/manage door.
- Not inline substrate editors (D2 + ADR-244 D7). Constitution panes are read + link-out.
- Not a relitigation of ADR-340's mirror/composition model. Both Settings doors are *mirror* surfaces (one substrate concern per pane); this ADR only re-groups which mirrors live behind which door.

## 4. Consequences

- **Cost paid:** one additional top-level launcher row (the `configure` tier has two members instead of `system`'s one). Accepted deliberately: the two doors are two objects, and the substrate (ADR-320 roots) backs the split. The "which door?" guess is resolved by the object distinction (am I governing the agent, or configuring the operation?), which is sharper than the per-pane guess "one door" would have left.
- **Gain:** the operation's configuration (program/connectors/sources) + constitution get a coherent home that names the operator's intent ("shape my operation"); System Settings becomes pure OS-governance. The sidebar sections mirror the ADR-320 permission topology, so the door structure teaches the lock model for free.
- **Constitution gets a Settings home** (read/manage) alongside the Home band — closing the orphan the ADR-340 Stage-1 eval flagged (constitution reachable only via the band).

## 5. Implementation

- `api/services/kernel_surfaces.py` — new `workspace-settings` container surface (`launcher_tier: configure`, `register: application` — it's a windowed app like `settings`); `settings` retitled, `launcher_tier: system` → `configure`; `program`/`connectors`/`sources` re-parented `pane_of: "workspace-settings"`; `mandate`/`identity`/`principles` gain `pane_of: "workspace-settings"` (search-only, band door unchanged). Tier docstring updated (`system` → `configure`).
- `web/components/shell/Launcher.tsx` — `KERNEL_TIER_GROUPS` gains `configure`; `system` removed.
- `web/app/(authenticated)/settings/` — refactor to a shared `<PaneContainer paneGroups={…} />` shell; `/settings` (System Settings) + `/workspace-settings` (Workspace Settings) each mount it. Constitution panes render read-view + Files/chat link-outs.
- `web/lib/api/client.ts` + route stubs — redirect stubs for re-homed routes.
- `api/test_adr341_two_settings_doors.py` — regression gate (two container surfaces; correct pane parentage; `configure` tier holds both; `system` tier retired; registers unchanged; constitution band door preserved).

Gates to keep green: ADR-340 (P1–P4), ADR-312, ADR-338, ADR-297, ADR-327, `tsc --noEmit`.
