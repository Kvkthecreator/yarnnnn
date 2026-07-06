# ADR-412: The Viewer Parameter — one commons, N first-person renderings

**Status**: Proposed (2026-07-06) — the surface/UX discourse deliverable after ADR-407/408/411 (the multi-principal state). Ratification also flips ADR-410 → Accepted (D5 below).
**Date**: 2026-07-06
**Dimension**: Channel (Axiom 6 — whose eyes a surface renders for) + Identity (Axiom 2 — first-person resolution of actors)
**Relates to**: ADR-410 (attention rework — stands as-is, becomes this model's attention chapter; shares machinery per D5), ADR-408 (D1 coworking contract — D1/D3 here are its rendering law; D5 surface list — absorbed into this sequencing), ADR-407 (D2 macOS-not-Figma — the shell model this completes; D10 cascade — D7 rides it), ADR-405 (witness dial — the no-species-law this extends to affordances), ADR-411 (member-embodiment attribution — D2 gives it first-person resolution), ADR-340/367/369 (DP29 compositions + Home tiering — preserved; §9-descendant recomposition gated by D6)
**Amends**: ADR-408 D5 (the "first-cut relocation" list is superseded by this ADR's D2/D3/D6 partition and sequencing), ADR-388 D3 (the attribution module gains a viewer-aware resolution layer above the sync labeler)

---

## 1. Context — what the two-account state actually broke

The multi-principal substrate is live (ADR-407 all phases; ADR-408 D3/D5.1/D5.2;
ADR-411 lanes) and the surface system was built one era earlier, for one
viewer. The audit receipts:

1. **Exactly one FE component is viewer-aware**: `UserMenu.tsx` (the
   workspace switcher). No other surface, slot, or affordance knows who is
   looking.
2. **First-person resolution is missing, not attribution.** The shared
   attribution module (ADR-388 D3) already carries *actor* and *transport* —
   `member:{id} via {model}` renders — but only as the generic
   "Member (via GPT-4o mini)": it is a sync string labeler with no viewer
   identity and no roster, so it cannot say "You via GPT-4o mini" or
   "seulkim88 edited …". The carried-over framing ("surfaces don't carry
   viewer/actor/transport") over-counts: actor and transport are solved
   wherever the module is mounted. **The one missing axis is the viewer.**
3. **Affordances render owner-shaped for everyone.** The Home constitution
   band offers "Help me author my mandate" drafts to any principal
   (`HomeHeader.tsx`); a bare workspace shows the activation CTA to a fresh
   member; Workspace Settings shows constitutional panes whose writes will
   fail at the gate. The walk's finding 2 (ADR-408 §1) was this class: the
   UI presenting a permission reality it doesn't understand.
4. **The bell misinforms** (ADR-410 §1 — the sharpest instance, already
   diagnosed and sequenced).
5. An invited member lands on `/home` (`web/app/invite/[token]/page.tsx`) —
   the right surface, wearing the wrong (owner-onboarding) affordances.

Failures 2–5 are two kinds, and the distinction drives everything below:
**correctness** (the surface renders something false or self-referential for
a non-owner viewer) vs **composition** (the surface might *weight* things
differently for different principals). Correctness is built now; composition
is evidence-gated (D6).

## 2. D1 — The model: one surface set; the viewer is a parameter, never a fork

Every principal gets the **same surfaces, same slots, same launcher** — there
is no member view, no member composition set, no owner dashboard. What varies
per viewer is exactly two things:

- **First-person resolution**: the viewer's own acts render as "You"
  (including embodiments — "You via GPT-4o mini"); peers render by name;
  self-acts are excluded from attention (ADR-405 D4 / ADR-410 D1).
- **Grant-derived affordances**: an authoring/consequential affordance
  renders only when the viewer's grant covers the region it writes. Reads
  are universal — every member reads the whole commons (ADR-407 content
  scope), including the constitution.

Never **data divergence**: all viewers read the same rows; a surface never
filters *content* by viewer (only attention, which is viewer-relative by
definition). This is ADR-407 D2's macOS model finished: N first-person
shells means N values of a *parameter* over one rendering system —
macOS renders the same Finder for every account and derives affordances
from permissions. A distinct member composition would be ADR-408 D1's
approval hierarchy creeping back in through the UI (members as guests in
someone else's app), and a second surface set to maintain.

**The no-species-law extends to affordances** (the UI twin of ADR-405):
no affordance may key on a role enum ("is owner") — it keys on the grant's
coverage of the target region. The membership read already carries role +
scopes; the FE derives "can author here" from that, so narrowed grants and
future roles render correctly for free. (The server gate remains the
enforcement; FE gating is legibility, never security.)

## 3. D2 — The viewer-resolution layer (the one shared build)

A single FE context provides `{ viewerPrincipalId, roster }` — the roster
from `GET /api/workspace/members` (one fetch per workspace bind), each entry
principal id → display name + role + scopes. Above the sync attribution
labeler, a viewer-aware resolver:

- `operator`-class + member acts resolve against the roster and the viewer:
  "You" / "You via GPT-4o mini" / "seulkim88" / "seulkim88 via GPT-4o mini".
- Non-human classes pass through the existing labeler (Freddie, host names,
  agents) — one module, one added layer, no parallel implementation
  (ADR-388 D3 discipline).

Consumers: the workspace timeline slot, Files/Recents/revision panels, the
bell (ADR-410 D1/D4 — actor≠viewer filtering and actor-first vocabulary both
require exactly this layer), Notifications, proposal attribution. **This is
the machinery ADR-410 and the viewer pass share; it is a prerequisite of
ADR-410's own gate criteria, which is why one session owns both (D5).**

## 4. D3 — Grant-derived affordance pass (correctness, not redesign)

The known owner-shaped affordances re-derive from the viewer's grant:

- **Constitution band**: the mandate read is universal (the charter is the
  first thing a member should read); the author/edit chat-draft affordances
  render only with constitutional coverage. Bare workspace: a member sees
  "the owner hasn't declared a mandate yet" state, not the activation CTA.
- **Activation CTA / setup entry**: constitutional — renders per grant.
- **Workspace Settings**: constitutional panes render read-only (visible,
  honest, labeled) for principals without coverage — explicit UI instead of
  the current implicit grant-failure (ADR-408 D5 item 4, absorbed here).
- **Member first-boot falls out** — no onboarding flow is built. A fresh
  member lands on `/home` and the same front page is already the right
  landing once D2/D3 render it honestly: the charter (read), who's here
  (D4), what's been happening (the timeline slot), what wants witness (the
  decision queue). The invite-accept redirect stands.

## 5. D4 — The ambient commons context

Two small chrome reads, both fed by the D2 context (no new fetch):

- **Which-workspace indicator**: ambient, always visible when N>1 bindings
  exist (the switcher shows this only on open today; the walk showed the
  workspace you're *in* must be glanceable, not discoverable).
- **Who's here**: a compact roster read (humans + AI members at their
  altitudes) — the one genuinely *new* composition element this ADR admits,
  because a commons whose membership is invisible outside Settings → Access
  fails the fresh-member landing. Minimal form (avatars/labels, deep-link to
  the Access roster); NOT presence (no online state — ADR-373 rejection
  stands; this is membership, a slow fact).

## 6. D5 — ADR-410 stands as-is; one session owns it plus the viewer layer

ADR-410 is confirmed untouched — its five decisions are all
viewer-parameterized already and nothing in this model amends them. It is
this ADR's *attention chapter*, not a casualty of the larger frame.
Ratifying this ADR flips ADR-410 → Accepted. Build sequencing (one session):

1. D2 viewer-resolution layer (roster context + viewer-aware attribution).
2. ADR-410 §5 steps 1–4 riding on it (hygiene sweep, bell re-source,
   in_app retirement, vocabulary pass).
3. D4 ambient indicators (small; same context).
4. D3 affordance pass (constitution band, activation CTA, Settings panes).
5. ADR-410 D5 (Notifications re-mount) trails, per its own sequencing.

Gate: ADR-410's gate, plus a fresh-member walk — an invited member lands on
Home and sees the charter without authoring affordances, who's here, the
peer/agent timeline, and their own lane writes as "You via ‹model›".

## 7. D6 — Recomposition is evidence-gated (confirmed)

The prior session's recommendation is confirmed: launcher IA re-sort under
the member lens, Home slot re-weighting, and any member-shaped composition
are **deferred on lived two-account evidence** — the D2–D4 correctness pass
must land first, because today's friction reports are contaminated by
rendering bugs (a member can't tell what the launcher should show them while
the bell shows them their own echo). Evidence now accrues for free:
member_state cursors, the timeline, and the attributed ledgers make member
usage observable, DP29-derived. Trigger: recurring friction from real member
sessions after the correctness pass — not speculation. (ADR-340 §9's original
launcher item stays CLOSED per ADR-349; this names its possible successor and
declines to open it.)

## 8. D7 — Placements (riding threads, not this ADR's build)

- **Chat drawer single-thread tail** (session-boundary legibility, history,
  per-workspace drawer behavior): stays with the lanes lane (ADR-408 D6
  named it prerequisite polish) — not attention machinery.
- **Per-actor / per-model Usage view**: held for ADR-409 (seat GA) — the
  ledger columns (`principal_id`, `model`, `workspace_id`) make it
  buildable any time, DP29-compliant, if legibility demand arrives earlier.
- **FOUNDATIONS**: the viewer-parameter clause (D1) joins the *owed*
  ADR-407 D10 cascade (DP17 amendment + DP35 candidate) — one doc pass,
  not a new number.

## 9. What this ADR does NOT do

- No member-specific surface set, composition, or launcher (D1 forbids it).
- No role-enum keying anywhere in the FE — grants only.
- No presence, realtime, or live cursors (ADR-373 rejection stands; D4's
  who's-here is membership, not presence).
- No stored read-state beyond the member_state cursor (DP29; ADR-410 §4).
- No pricing surfaces (ADR-409 demand-gated).
- No launcher re-sort or Home re-weighting now (D6 gates them).
- No change to grants, gates, or any backend authorization path — this is
  rendering; the membership endpoint already returns what D2 needs.
