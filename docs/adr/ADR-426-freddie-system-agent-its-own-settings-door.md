# ADR-426: Freddie System Agent — Its Own Settings Door

**Status**: Accepted (2026-07-09, operator-ratified — "separate carve out, same leveling plane as Workspace Settings, separately dedicated for Freddie System Agent"; label ruled "Freddie System Agent"). Doc-first with its code in the same pass; a single FE + registry + gate change pushed to main. **Amended same day (§7)**: the door wears Freddie's mascot mark; the Capabilities pane is retired and replaced by an About pane.
**Date**: 2026-07-09
**Dimension**: Channel (Axiom 6 — where the system agent's config lives in the shell) + Identity (Axiom 2 — the system agent given its own door, at the workspace-settings plane)
**Relates to**: ADR-412 D5 (the System Agent group placement this amends), ADR-418 (the pane-set purification this carries forward — the same four panes, new home), ADR-349 D4 (the two-settings-door launcher re-split this extends to a third door), ADR-341/347 (the SettingsPaneShell one-door model — a third mount), ADR-381 D1 (Freddie the entity; its chrome home is the rail), ADR-414 D2 (the steward's two dials — the door's content)
**Amends**: ADR-412 D5 (the System Agent group leaves Workspace Settings and becomes its own window-grade door; the "role-not-proper-noun" label ruling is reversed — see D3), ADR-418 (the four-pane System Agent group re-homes intact from a Workspace Settings group to a standalone door), ADR-340 P3 / ADR-349 D4 (a third at-rest launcher settings tier joins `workspace-config` + `system-config`)

---

## 1. Context — one door holding two altitudes

Workspace Settings (ADR-347, the one operation-settings door) accreted a
**System Agent** group in ADR-412 D5: the steward Freddie's config panes
(re-homed off the `/agents` roster). ADR-418 purified that group to Freddie's
genuine surface — its two operator-tunable dials (Autonomy = the witness dial,
Budget = the allocation; ADR-414 D2) plus two read-only legibility panes
(Capabilities · Activity).

The operator, reading the live door, observed the residual altitude blur: the
sidebar mixes **what this workspace is and how it runs** (Brand · Program ·
Members · Billing · Usage) with **the system agent's own configuration**
(Autonomy · Budget · Capabilities · Activity). Those are two different objects.
Workspace Settings answers "what is this operation"; the System Agent group
answers "how is Freddie configured." A user opening Workspace Settings to change
the plan or invite a member should not have to visually parse past Freddie's
dials — and vice versa.

This is the same altitude-separation motion the surrounding band has been making
all week: ADR-421 pulled the *constitution* out of the workspace surface because
it belongs to an agent, not the workspace. ADR-412 D5 pulled Freddie's panes off
the *staff roster* because the system agent belongs on the system layer, not
among Altitude-3 hires. **This ADR completes the pattern: Freddie's config leaves
the workspace-operation door and gets a door of its own — on the same plane.**

ADR-412 D5 placed the panes *inside* Workspace Settings as a **convenience**
("Freddie's inspection surface belongs on the system layer" — and Workspace
Settings was the nearest system-layer door). That was the right v1 mount. It was
never a claim that Freddie's dials are a *workspace-operation* concern; they are
not. The clean expression is a dedicated door.

## 2. The move — a third settings door on the launcher plane

The launcher's at-rest IA already carries two settings doors as sibling tiers
(ADR-349 D4): `workspace-config` → **Workspace Settings** (the operation) and
`system-config` → **User Settings** (the human/account). This ADR adds a **third
sibling tier** at the same plane: `system-agent-config` → **Freddie System
Agent** (the system agent).

```
LAUNCHER (at rest)
──────────────────
WORKSPACE
  Home · Chat · Files

WORKSPACE SETTINGS          (workspace-config)
  Brand · Program · Members · Billing · Usage

FREDDIE SYSTEM AGENT        (system-agent-config)   ← new door
  Autonomy · Budget · Capabilities · Activity

USER SETTINGS               (system-config)
  Account · Connectors
```

Three doors, one plane, each answering a distinct question: *the operation*
(Workspace Settings) · *the system agent* (Freddie System Agent) · *the human*
(User Settings).

## 3. Decisions

**D1 — Freddie's config becomes its own window-grade surface.** A new kernel
surface: `slug: system-agent`, `route: /system-agent`, `register: application`
(a windowed app like `workspace-settings` / `settings`), `archetype: dashboard`.
Its own at-rest launcher tier `system-agent-config`, rendered as the launcher
group **"Freddie System Agent"** immediately after Workspace Settings. It mounts
the shared `SettingsPaneShell` (`windowSlug="system-agent"`) with the four
`SYSTEM_AGENT_PANE_GROUP` panes — the SAME `SystemAgentPanes` bodies ADR-412 D5 /
ADR-418 defined (Singular Implementation; one home per pane — the group leaves
Workspace Settings, it is not duplicated).

**D2 — The pane rows re-point to the new parent.** The `budget` and `autonomy`
kernel-surface rows change `pane_of: "workspace-settings"` →
`pane_of: "system-agent"` and `pane_group: "System Agent"` →
`pane_group: "Freddie System Agent"`. `foregroundSurface('autonomy' | 'budget')`
now resolves to the Freddie System Agent door + `?system-agent.pane=…` — call
sites stay pane-blind (registry-driven resolution, ADR-340 P2), so the Home
autonomy badge deep-link (`foregroundSurface('autonomy')`) heals with the
re-point, unchanged. `capabilities` + `activity` stay door-local pane keys (no
registry row — as before; they ride the page's `PANE_GROUPS`).

**D3 — The door carries the proper noun: "Freddie System Agent."** This reverses
ADR-412 D5 / ADR-418's explicit "the door carries the ROLE, Freddie stays on the
rail" ruling. That ruling held while the panes were a *group inside* a workspace
door (a group named "Freddie System Agent" beside "Operation" and "Access" would
have read redundantly, and mixing the proper noun into the workspace-settings
sidebar muddied the container's identity). Once the panes get their **own door**,
the proper noun is the clearest label — the operator asked for it by name, and a
door titled "System Agent" alone reads more abstract than the entity users
actually hold in mind ("Freddie"). The rail (ADR-412 D1 — Freddie's conversational
chrome home) is **untouched**: this is a *settings door*, not a second
conversational entry point. "Never a launcher tile" in ADR-412 D1 governs the
*conversational entity* (talking to Freddie = the rail only); a config door for
Freddie's dials is the system-layer inspection surface D5 already ratified —
this ADR only gives it its own frame and its own name.

**D4 — Workspace Settings loses the System Agent group.** The
`SYSTEM_AGENT_PANE_GROUP` import + group + the `SYSTEM_AGENT_PANE_KEYS` render
branch are removed from `workspace-settings/page.tsx`. Its remaining groups
(Operation · Access · Billing) are now homogeneously about the operation + the
workspace. Its `defaultPane` moves off the dormant `"mandate"` (ADR-421) to
`"brand"` (the first live pane).

**D5 — The surface is steward-coupled.** `system-agent` joins
`STEWARD_SURFACE_SLUGS` — when `AGENT_ENABLED` is off (the ADR-375 interop-first
deploy), the system agent has no dials to tune, so its door filters out of the
registry with the rest of the steward-coupled surfaces. Backend-driven nav → zero
FE change (ADR-375 §6 chokepoint #4).

## 4. What this does NOT do

- **No change to the panes themselves.** Autonomy · Budget · Capabilities ·
  Activity are the ADR-418 set, rendered by the same components (`AutonomyCard` /
  `BudgetCard` / `FreddieCapabilitiesPanel` / `FreddieActivityPanel`). Only their
  container window changes.
- **No backend behavior change.** `_autonomy.yaml` / `_budget.yaml` substrate,
  the region locks, the envelope reads are untouched. Channel-dimension placement
  only. The one backend change is the registry rows (D1/D2/D5).
- **No touch to the rail.** ADR-412 D1's Freddie-rail (the conversational chrome
  home) and its FAB behavior are unchanged. Freddie speaks on the rail; Freddie
  is *configured* on this door.
- **No new pane, dial, or capability.** No new autonomy level, no new legibility
  read. The four panes are the existing four.
- **No per-agent (Altitude-3) surface.** The hired-agent config surfaces stay
  ADR-382-deferred. This is the SYSTEM agent (Altitude 1 / Freddie), not a hire.

## 5. Gate updates

The pane-parent + tier assertions move from `pane_of: workspace-settings` /
`pane_group: System Agent` to `pane_of: system-agent` /
`pane_group: Freddie System Agent`, and a third settings tier joins the launcher.
Updated gates:

- `test_adr338_surface_registry_parity` — the pane set drops `budget`/`autonomy`
  from the workspace-settings parent expectation; the three-way parity
  (`navigable == allowlist`, `registry == allowlist − panes`) now includes the
  new window-grade `system-agent` in registry + allowlist.
- `test_adr340_p3_launcher` — a third settings tier `system-agent-config`; the
  Launcher declares the "Freddie System Agent" group.
- `test_adr349_launcher_ia` — `system-agent-config == {system-agent}`;
  `system-agent` is window-grade.
- `test_adr347_one_settings_door` / `test_adr341_two_settings_doors` /
  `test_adr340_p2_settings_fold` / `test_adr412_chat_surface` — `budget`/`autonomy`
  now `pane_of: system-agent`, grouped "Freddie System Agent"; the new door mounts
  `SYSTEM_AGENT_PANE_GROUP` + `renderSystemAgentPane`; `foregroundSurface('autonomy')`
  resolves into the new door.

The three-way parity invariant (`navigable == allowlist`,
`registry == allowlist − panes`) holds with `system-agent` added to navigable +
allowlist + registry (it is window-grade, so it carries a window component).

---

## 7. Amendment (2026-07-09) — the mascot mark + About replaces Capabilities

Two operator-requested refinements landed the same day the door shipped, once
the door was live and legible:

**7.1 — The door wears Freddie's own mark.** The `system-agent` row's `icon_key`
changed `shield-check` → `freddie`. `shield-check` was generic and collided with
the Autonomy pane's own glyph; the door now carries the **Freddie mascot**
(`FreddieAvatar` — the Frankenstein/cryptopunks face already on the chat-rail
FAB, ChatDrawer, and FreddieCard), so the same mark reads as "Freddie"
everywhere the entity appears (launcher tile · dock icon · page header). Because
the mascot is a custom SVG (not a lucide glyph), `resolveSurfaceIcon` gains a
`freddie` special-case returning a still (`animate={false}`) mascot, and its
return type widens `LucideIcon` → `SurfaceIcon = ComponentType<{ className? }>`
(every call site only passes `className`, so this is the honest contract). Motion
is the "working" signal in the Freddie design system, so the surface tile renders
the still face — it does not perpetually animate.

**7.2 — Capabilities retired; About added.** The Capabilities pane read
`/workspace/operation/specs/*.md` ("the Reviewer's capability library" — quality
contracts for producing recurring outputs). That is a **pre-ADR-414 concept**:
post-ADR-414 the specs library is a *hired* Altitude-3 agent's operation concern,
not the system agent's, and the pane wrongly invited the operator to configure
output specs *for the steward* — which the steward does not produce. It also read
as "you configure the system agent's capabilities," cutting against the ADR-414
truth that Freddie's character is a kernel constant the operator tunes but never
authors. **Retired** (Singular Implementation — deleted: the `FreddieCapabilitiesPanel`
component, the `api.agents.reviewerCapabilities()` client method, and the
`GET /api/agents/freddie/capabilities` backend route + its spec-parsing helpers).

In its place, a read-only **About** pane (`FreddieAboutPanel`) — who Freddie is
(the system agent / substrate steward), what it does *not* do (no consequential
external action), and the one thing the operator should take away: **you tune
Freddie (Autonomy · Budget), you do not author its character.** The prose mirrors
the canonical steward identity (`DEFAULT_STEWARD_IDENTITY_MD`); since that persona
is a kernel constant (nothing to fetch or edit), the copy lives FE-side rather
than behind a new endpoint. New pane order: **About · Autonomy · Budget ·
Activity**; the door's `defaultPane` becomes `about` (the door opens on the
explanation).

No gate changes were needed — no gate asserted the Capabilities pane or the
`shield-check` icon; the pane-set/parity gates key on `AutonomyCard`/`BudgetCard`
presence and `SYSTEM_AGENT_PANE_GROUP` mounting, all unchanged. `tsc --noEmit`
clean; the six door gates stay green.
