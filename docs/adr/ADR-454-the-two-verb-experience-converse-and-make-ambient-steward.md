# ADR-454: The Two-Verb Experience — Converse and Make, and the Ambient Steward

> **Verb pair renamed by [ADR-457](ADR-457-think-and-make-the-service-model.md) (2026-07-14): Converse · Make → Think · Make** — both verbs now name the job (this ADR's "Converse" named the medium). ADR-457 is the service-model capstone: it adds the five-act derivation, the pipeline (think → settle → make), the settle verb, the think-home convention, and the desk/record two-layer statement (ESSENCE v16). Everything else here — the census, the seam rule, the ambient steward — stands.

**Status**: Accepted (2026-07-13, operator-ratified — "fully aligned… it's ratification of the
subtraction arc"). This ADR names the experience model the 435→452 subtraction arc converged on,
rather than deciding a new one: the shell has exactly **two acting surfaces** — chat (Converse)
and Studio (Make) — everything else is legibility or configuration; and the steward's persona
chrome retires while the steward function continues unchanged.
**§7 item 1 RESOLVED same day (operator: "the freddie posture is not that complicated since I
agree")** — the **mascot posture**: Freddie stays the named steward in narrative (ESSENCE v15.1),
brand (the `/freddie` landing survives, copy aligned to ambient — no "ask him" affordance
claims), and the ledger (`freddie:` attribution untouched); he is never a fronted chat character.
Cascade: ESSENCE v15.1 · GLOSSARY v3.2 (chrome-home line + altitude table) · `/freddie` +
capability copy de-chat-ified. Items 2–4 (artifact comments · presence · the `.md` bench) remain
open for the focused discourse.
**Date**: 2026-07-13
**Dimension**: Channel (the experience census — which surfaces carry the operator's acts) +
Identity (which actor fronts chrome).

**Amends**: ADR-340 / FOUNDATIONS DP29 (the standing loop gains **Make**; the census re-derives
around two acting surfaces — third amendment) · ADR-412 D1/D2 (the rail stays Freddie's voice
*when chrome-lit*; the chrome is now gated off by default) · ADR-426 (the "Freddie System Agent"
door is reversed — the two dials re-home to Workspace Settings; the door row goes hidden) ·
ADR-414 D3 (the *collapse* — one system agent — stands untouched; the *fronting* — a summonable
persona chat as default chrome — retires).
**Preserves**: ADR-441 (the A1/A2 thread seam is wire protocol and does not merge; hiding A1's
chrome touches no machinery) · the Studio arc ADR-440→453 (this ADR consumes it, changes none of
it) · ADR-410 (attention derives from the timeline; **attribution keeps the name "Freddie"** —
actor-first ledger rows are exactly where a named steward earns its keep) · ADR-405 (the witness
dial semantics; the queue stays, already unbranded) · ADR-375 §6 `AGENT_ENABLED` (the *function*
gate — untouched and orthogonal to the new *chrome* gate).

---

## 1. Context — the arc was already drawing this

Read as one motion, the recent surface ADRs all subtract toward the same shape: ADR-435 deleted
Home (the one composition); ADR-415 dissolved Channels into Activity; ADR-421/425/432/437
emptied Workspace Settings to a single Access group and deleted Setup; ADR-412 shrank Freddie's
chrome to the rail alone; ADR-451 routed `.html` out of Files into Studio; ADR-452 gave Studio a
chat-less creation landing. What is left standing is **two verbs and three ledgers**: two places
the operator *does* something (chat, Studio) and the places they *read what happened or tune the
machine* (Files, Activity/Notifications, the settings doors).

Underneath the IA motion is a product-model shift this ADR makes explicit: **the human's own
work became first-class input to the ledger.** The cockpit-era model (agents produce, operator
supervises) put the operator's acts at Decide/Read/Tune; direct edit (ADR-446), the mechanical
toolbar (ADR-444), and the bound lane (ADR-440) put the operator's *making* on the ledger as
attributed revisions. ESSENCE v15's moat statement — *the system of record where human and AI
work settles* — was written for the interop face; Studio is the in-app face finally embodying
it. A settlement layer needs a place where work is done, not only judged.

One precision the census keeps: Studio is primary for the **dividend class** (composed `.html`
artifacts). The **asset** (substrate `.md`, uploads, retained observations) is worked
conversationally and mirrored by Files. ESSENCE's quad maps onto the surfaces: **chat works the
asset; Studio works the dividends.** Studio does not claim `.md` — the ADR-440 drift guard
(TextEdit, not Word) and this asset/dividend seam are the same discipline.

## D1 — The two-verb model

The operator experience is carried by two acting surfaces:

- **Converse — `/chat`.** The workspace's room. Workspace-scoped conversation: ask, derive,
  learn-from (non-artifact recipes), organize, remember, multi-file operations, uploads. The
  unbound A2 lane — the member's hands over the whole commons.
- **Make — `/studio`.** The artifact's bench. Artifact-scoped: creation grid, learn-from
  (artifact recipes), direct edit, mechanical verbs, the Design tab, the bound lane.

**One conversation substrate, two scopes.** The bound lane is ordinary ADR-411 lane machinery
plus a binding field (ADR-440 D3) — there are not two chat systems and there must never be. The
seam rule: *a conversation about one open artifact lives in Studio's right column; everything
else lives in `/chat`.* Entry points compose (creation grid and Files' open verb into Studio;
learn-from recipes land by target class; deep-links between the two), but the scope decides the
surface, not the feature.

## D2 — The census, re-derived (DP29 third amendment)

DP29's standing loop (Decide · Read · Dwell · Tune · Amend · Setup) was derived for the
supervision product and has no authoring act. It gains **Make** — the operator authoring work
that settles onto the ledger — carried by Studio (and by the lanes' file verbs at conversation
scope). The census restated:

- **Acting surfaces (compositions)**: `chat`, `studio`. The launcher's primary tier is exactly
  these two plus Files.
- **Legibility (mirrors + the attention composition)**: `files` (the Finder), `notifications`
  (bell-fronted; Decide lives here as the To-do pane), `activity` (the what-happened trail).
- **Configuration doors**: `workspace-settings` (the operation), `settings` (the account/human).
  Two doors again — the third (ADR-426) is reversed by D4.
- **`agents`** stays registered for the Altitude-3 horizon (hired persona agents are *visible
  actors* with mandates and track records); it is not part of the two-verb story at Rung 1.

## D3 — The ambient steward: persona chrome retires, function continues

"Freddie" names four different things in the UX today, and they get four different answers:

1. **The persona chrome** — the FAB ("Ask Freddie"), the rail (ChatDrawer), the FreddieCard
   conversation — **hidden**. The steward becomes a daemon the operator meets in the ledger, not
   a fronted chat character. Rationale: (a) two chat entries presented the A1/A2 wire seam
   (ADR-441) as two visible chatbots the operator must distinguish — an IA bug, not a feature;
   (b) ADR-380 D3 harness honesty — a stakeless steward fronted as the most visible agent
   inverts the eventual value hierarchy (hired A3 agents are the visible actors; the steward is
   OS plumbing); (c) the steward's user-facing asks ("organize this," "where is X") are file
   verbs and derives the A2 lane already has under the member's grant.
2. **The dials** (autonomy, budget) — **survive, re-homed** to Workspace Settings as an
   unbranded System group (D4).
3. **The witness queue** — **survives untouched.** Already unbranded (ADR-410's ban did the
   work); Notifications' To-do pane remains the before-witness surface while the dial is below
   autonomous.
4. **Attribution** — **keeps the name.** Ledger rows ("Freddie derived…", `freddie:` author
   prefix) are the correct, derived form of the steward's presence (ADR-410 actor-first). Hiding
   the chrome does not de-name the author string; whether the name itself changes is the
   narrative-posture regroup, deliberately out of scope here.

**Mechanism — a chrome gate, not the function gate.** `web/lib/steward-chrome.ts` exports
`STEWARD_CHROME_ENABLED = false` (hide-not-delete, the `CONNECTOR_CAPTURE_ENABLED` posture; one
const flip re-lights everything). It gates: the Desktop FAB render; the drawer's open state
(`ShellChromeContext` forces `drawerOpen=false` and no-ops the toggle, suppressing both the
persisted-open posture and the rail-mode default-open). The drawer body, `NarrativeContext`, the
A1 thread machinery, and the addressed-wake backend path stay fully intact — the steward remains
addressable over the interop face and by a future re-light. This is deliberately **distinct from
`AGENT_ENABLED`** (ADR-375 §6), which turns the steward *function* off; here the steward keeps
waking, deriving, placing, and arbitrating — only its persona chrome hides.

## D4 — The door reversal (ADR-426 → hidden; dials re-home)

ADR-426 carved a third settings door ("Freddie System Agent") four days ago; the two-verb census
reverses it — three sibling doors was the persona-fronting shape, and the door mixed one live
concern (two dials) with persona pedagogy (About/Capabilities/Health/Activity panes):

- `budget` + `autonomy` registry rows: `pane_of: system-agent` → `workspace-settings`,
  `pane_group: "System"`. Workspace Settings renders Access (Members) + System (Autonomy ·
  Budget) — the pane bodies are the same `SystemAgentPanes` components (Singular Implementation;
  the group moves again, not duplicated). `foregroundSurface('autonomy'|'budget')` deep-links
  resolve there with unchanged call sites (pane resolution is registry-driven).
- The `system-agent` row: `hidden: True` (the ADR-425 D2 sources precedent — hide-not-delete),
  `launcher_tier: search-only`; the slug leaves the FE navigable allowlist
  (`web/types/desk.ts`) and the FE `SurfaceRegistry` map; the Launcher's
  `system-agent-config` tier-group entry is removed.
- `/system-agent` becomes a `next.config.js` redirect → `/workspace-settings?pane=autonomy`
  (ADR-308 pure transport; the page component is deleted, the ADR-385 follow-on precedent); the
  middleware protected-prefix entry is removed.
- The About/Capabilities/Activity pane bodies are **dormant-retained** in
  `SystemAgentPanes.tsx` (unreferenced but kept for the narrative-posture regroup and any
  re-light; the ADR-418 expected-output precedent).
- The `/agents` governor frame line updates its pointer (dials → Workspace Settings → System).

## D5 — What does not change

- The steward function: wakes, placement, derives, intake, multi-principal arbitration,
  persona-agent governance (ADR-381 D5). No backend behavior change of any kind.
- The witness-dial semantics (ADR-405) and the proposal queue.
- `AGENT_ENABLED` and `STEWARD_SURFACE_SLUGS` (the function gate) — orthogonal, untouched.
- Attribution vocabulary (`freddie:` prefix, "Freddie" actor rows in Activity).
- The Studio arc — this ADR positions it; it does not modify it.
- The A2 lanes, model routing, metering, grants — untouched.

## D6 — SERVICE-MODEL re-cut

`docs/architecture/SERVICE-MODEL.md` "What YARNNN Is" (last touched v1.8, 2026-05-20 — two
pivots stale: still cockpit-led) is rewritten to the settlement + two-verb form: the workspace
where human and AI work settles; two acting surfaces (Converse, Make); Files/Activity as
legibility; the steward as an ambient daemon; supervision (the cockpit) re-framed as the
Altitude-3 deepening, not the lead. Deep rewrites of the rest of that document are deferred —
the intro is the load-bearing claim.

## 7. Deferred — the regroup items (named, not decided)

1. **Narrative posture** — ~~mascot vs full de-front~~ **RESOLVED 2026-07-13 (same day): the
   mascot posture.** Freddie keeps the name in narrative, brand, and the ledger; no fronted chat
   character. Landed: ESSENCE v15.1 (ambient-steward amendment) · GLOSSARY v3.2 (chrome-home +
   altitude-table amendments) · `/freddie` page copy de-chat-ified ("Ask him and he looks it up"
   → capture framing; "when you ask" → ambient framing) — the page itself survives as the brand
   surface, its honesty band unchanged. NARRATIVE.md needed nothing (zero Freddie references);
   `agent-identity.ts` + `freddie-persona.ts` needed nothing (attribution machinery — the name
   stays). Any future full de-front would be a new decision, not this ADR's.
2. **Artifact-anchored shared discussion** (the real multi-user gap): bound lanes are
   member-private (ADR-407), so two members co-working on one artifact have no shared
   conversation surface. The candidate shape is comments-as-substrate — attributed, on the
   ledger, block-addressable via `data-block-id`. Its own ADR.
3. **Presence** — "someone else has this artifact open" soft-awareness (never merge/CRDT —
   ADR-406 reaffirmed).
4. **The `.md` authoring question** — whether prose substrate ever gets a bench of its own.
   Default answer: no; chat + viewers carry the asset (the drift guard).

## Key files

Docs: this ADR · `docs/architecture/FOUNDATIONS.md` (DP29 third amendment, v9.17) ·
`docs/architecture/SERVICE-MODEL.md` (intro re-cut) · amendment banners on ADR-412 + ADR-426.
FE: `web/lib/steward-chrome.ts` (new — the chrome gate) · `web/components/shell/Desktop.tsx`
(FAB gated) · `web/components/shell/ShellChromeContext.tsx` (drawer force-closed under the
gate) · `web/components/shell/Launcher.tsx` (tier group removed) · `web/types/desk.ts` (slug
leaves the allowlist) · `web/components/shell/SurfaceRegistry.tsx` (mapping removed) ·
`web/app/(authenticated)/system-agent/page.tsx` (deleted → `next.config.js` redirect) ·
`web/app/(authenticated)/workspace-settings/page.tsx` (System group) ·
`web/app/(authenticated)/agents/page.tsx` (pointer) · `web/middleware` protected list.
Backend: `api/services/kernel_surfaces.py` (pane re-home + hidden row; **no behavior change**).
Gates: `api/test_adr341_two_settings_doors.py` · `api/test_adr347_one_settings_door.py` ·
`api/test_adr338_surface_registry_parity.py` (assertions re-pointed to this ADR).
