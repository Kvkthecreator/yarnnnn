# ADR-349 — Launcher IA Re-Sort: the at-rest launcher is the standing loop + two settings doors

**Status:** **Accepted + Implemented (2026-06-19)** — same session. Closes the ADR-340 §9 deferred follow-on ("launcher IA re-sort ~17→~7") and ADR-346 §9 ("Queue window fate"). Gate `api/test_adr349_launcher_ia.py`. Sibling gates updated (ADR-340 P3, ADR-346, ADR-347, ADR-340 P1). `tsc --noEmit` clean (my files).
**Date:** 2026-06-19
**Deciders:** KVK (operator) + Claude (collaborator)
**Hat:** A (system canon)

> **Discourse base:** the operator's launcher walk against the live Launchpad — "feed, recurrence and queue are now in operations… step back in full… what survives is Workspace (Home/Operation/Files) + the two settings doors; Setup absorbed; Agents absorbed-or-upgraded." Grounded against the live registry (the mirrors were *fronted* by Operation per ADR-346, not absorbed) before resolving.

**Closes:** ADR-340 §9 open follow-on (launcher IA re-sort), ADR-346 §9 (Queue window fate).
**Amends:** ADR-346 (the `operation` surface renames to `Notifications` — operator decision, §D2), ADR-347 D3 (the one-`configure`-tier launcher collapse is partially re-split into two settings rows — operator decision, §D4), ADR-340 P3 (the at-rest tier set is re-derived), ADR-340 D1 (mirrors stay "mirror once" — reachable by flat search — but lose their Utilities-tile prominence).
**Preserves:** ADR-346 D1 (the mirrors are NOT deleted — Feed/Queue/Recurrence remain complete window surfaces, now reached by flat search + fronted by the Notifications composition), ADR-307 (one gate, one queue), ADR-331 (Setup stays a re-enterable Sequence surface — only its launcher prominence drops), ADR-340 D1 "mirror once, compose few," DP29.

---

## 1. The premise, corrected before building

The operator's read — "Feed/Recurrence/Queue are now in Operations" — is **half-right and the half matters**. Per ADR-346 D1 the Operation composition **reuses the mirror BODY components** (one body, two mounts) but the mirrors were **NOT absorbed**: they stay complete, standalone window surfaces (the escape hatch, the `/proc` of the OS). At ADR-348's close they sat demoted in a `utilities` launcher tier. So the correct framing is: **fronted, not absorbed** — and the re-sort question is whether they earn an at-rest launcher tile at all, given a composition already fronts them.

The answer (ADR-340 D1 "compose few"): no. A composition fronts them; the mirrors are summoned by name (flat search), not browsed. The `utilities` tier dissolves.

## 2. Decisions

### D1 — At-rest launcher = the standing loop + two settings doors

```
WORKSPACE           Home · Notifications · Files · Agents
WORKSPACE SETTINGS  Workspace Settings
SYSTEM SETTINGS     System Settings
```

Everything else (Feed, Queue, Recurrence, Activity, Setup, the constitution + contract + perception panes) is **`search-only`** — present in the registry, found by typing (ADR-340 D5 "search stays flat"), never an at-rest tile. The launcher at rest is 6 tiles across 3 groups; flat search remains exhaustive.

### D2 — `operation` → `Notifications` (the window = the bell, one name, two zooms)

The Operation composition surface and the topbar Attention bell are **the same object at two zooms** (ADR-346 §5a unified their vocabulary: To do · Activity · Coming up). To finish the streamline, they take **one name**: **Notifications**. The bell is the glance; the window is the full surface. Title/label/route rename `operation` → `notifications`; the bell header and "Open →" link rename to match. The **pane keys** (`resolve`/`understand`/`tune`) and the ADR-340 D2 act identities (Decide/Read/Tune) are **unchanged**.

**One name, one icon (icon unification, 2026-06-19):** the rename gave the two zooms one *name* but left them two *glyphs* — the AttentionCenter rendered `Bell` while the surface declared `icon_key: "gauge"` (a vestige of the ADR-327-retired `/pace` surface), so the Launcher tile + Dock icon read as a gauge while the top-bar glance read as a bell. "Same object at two zooms" requires one glyph too. The surface's `icon_key` becomes **`bell`** (new registry entry mapping to the same lucide `Bell` the AttentionCenter uses); the top-bar glance, the Launcher tile, and the Dock icon now all carry the Bell. The orphaned `gauge` mapping (no surface declared it after this) is deleted per Singular Implementation.

> **On-record dissent (operator overrode):** the collaborator argued against "Notifications" — the surface is where the operator *approves capital actions* (the ADR-307 consent gate) and *tunes schedules* (mutations); only 1 of its 3 panes is passive receipt, so "Notifications" names an action surface as a dismissable tray. The operator held the call after the argument. Recorded so the rationale isn't lost; the decision is the operator's.

### D3 — Agents upgrades to the Workspace (primary) tier

Agents (the Reviewer + user-authored domain Agents roster — "who acts on your behalf") joins Home · Notifications · Files as a primary standing-loop surface. Rationale: the persona-bearing judgment seat is the moat (ESSENCE; the "one moat" framing) — "who acts for me" is first-class, not a utility to bury. (Upgrade, not absorb — ADR-340 §9's "Agents absorbed-or-upgraded" resolves to upgrade.)

### D4 — Two settings rows (re-splits ADR-347 D3's launcher collapse)

The at-rest launcher shows **two** settings groups: **Workspace Settings** (the operation — constitution/contract/program/perception) and **System Settings** (the account — billing/usage/privacy). This is an operator decision that partially reverses ADR-347 D3 (which collapsed both into one `configure` tier with the account moved off-launcher to the UserMenu).

- The `workspace-settings` slug stays the operation door (launcher title "Workspace Settings").
- The `settings` slug (retitled "Account" by ADR-347) **re-promotes to a launcher door titled "System Settings"** and is **re-named back from "Account" → "System Settings."** It remains *also* reachable from the UserMenu (the account affordance is preserved — two doors to one window is fine; the avatar menu and the launcher both point at it).

> **Tension noted:** ADR-347's case was that two settings *objects* don't need two launcher *groups* (breadth-for-its-own-sake). The operator's call here is that the operation-vs-machine distinction is worth two at-rest rows. The substrate split (ADR-320 governance/ vs constitution/+operation/+persona/) backs either projection; this is a Channel-dimension presentation choice, not a substrate change. ADR-347's editability rule (§3) and the pane homing are unchanged — only the *launcher grouping* re-splits.

### D5 — Setup absorbed (off the launcher)

Setup (the ADR-331 guided Sequence) leaves the launcher (`search-only`). Its re-entry doors are unchanged and sufficient: the empty-Home constitution-band CTA (first run) + the Workspace Settings → Program "re-run setup" link (ADR-331 D2 "re-enterable any time") + flat search. Setup is a *motion you re-enter*, not a surface you dwell in — it doesn't earn an at-rest tile.

### D6 — The Utilities tier dissolves

With the mirrors → search-only, Setup → search-only, and Agents → primary, the `utilities` tier has no members and is removed. The launcher tier-group fallback for an un-tiered navigable surface changes from "dump in Utilities" to "treat as search-only" (don't surface at rest) — a registry omission should hide a surface from the at-rest launcher, not invent a tile in a dead group.

## 3. Tier model (post-ADR-349)

| `launcher_tier` | Members | At-rest |
|---|---|---|
| `primary` | home · notifications · files · agents | Workspace group |
| `workspace-config` | workspace-settings | Workspace Settings group |
| `system-config` | settings (the account/System Settings door) | System Settings group |
| `search-only` | feed · queue · recurrence · activity · setup · all panes | hidden; flat search only |

(`configure` — ADR-347's single merged tier — is retired; `workspace-config`/`system-config` return per D4.)

## 4. What this does NOT do

- Does not delete any mirror (ADR-346 D1) — Feed/Queue/Recurrence keep their windows, routes, deep-links; they lose only the at-rest tile.
- Does not change the Notifications panes' bodies, keys, or routing (D2 is a rename + the act identities hold).
- Does not change substrate, permissions (ADR-320), the gate (ADR-307), or any backend execution path — Channel-dimension projection only.
- Does not touch the UserMenu's account affordance (the account window stays reachable from the avatar AND the new System Settings launcher door).

## 5. Implementation

- `api/services/kernel_surfaces.py` — `operation`→`notifications` (slug/title/route); `agents` tier → `primary`; `feed`/`queue`/`recurrence` tier → `search-only`; `setup` tier → `search-only`; `settings` tier `search-only`→`system-config` + title "Account"→"System Settings"; `workspace-settings` tier `configure`→`workspace-config`; notifications `icon_key` `gauge`→`bell` (§D2 icon unification).
- `web/lib/shell/surface-icons.tsx` — register `bell` → lucide `Bell` (the AttentionCenter's glyph); delete the orphaned `gauge` mapping + import (no surface declares gauge after notifications moves off it).
- `web/components/shell/Launcher.tsx` — `KERNEL_TIER_GROUPS` → Workspace / Workspace Settings / System Settings; Utilities removed; un-tiered fallback → hidden-at-rest.
- `web/components/shell/AttentionCenter.tsx` — header + "Open →" → "Notifications"; routes to `notifications` slug.
- `web/app/(authenticated)/notifications/page.tsx` — renamed from `operation/`; `web/app/(authenticated)/operation/` → ADR-308 redirect stub → `/notifications`.
- `web/types/desk.ts` + `SurfaceRegistry.tsx` + any `navigateToSurface('operation')` / `foregroundSurface('operation')` call sites → `notifications`.
- `api/test_adr349_launcher_ia.py` (new) + sibling-gate updates.

**Dimensional classification:** **Channel** (Axiom 6) projected through **Purpose** (Axiom 3 — the operator's at-rest ontology). Closes ADR-340 §9.
