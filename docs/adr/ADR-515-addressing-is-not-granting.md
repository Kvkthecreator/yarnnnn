# ADR-515 — Addressing Is Not Granting: the acts the Share button collapsed

**Status**: **Accepted + Implemented 2026-08-06** — D1/D2/D7 executed by
[ADR-529](ADR-529-one-share-act-one-link-two-readers.md) (the singular `ShareDialog` on the
`FileVerbs` bundle; `Share…` stops copying on click; the Files over-grant dies by construction).
**D8 was executed earlier** by [ADR-517](ADR-517-grants-govern-share-executes.md) D7 (the dead
`POST /api/share` deleted). **§6 open question 1** ("can a viewer grant a share?") was **ratified
`no`** by ADR-517 D3. **Still open**: D3/D4 (the `Copy AI reference` move + the internal-referral
ADR), D5 (Export's honest-copy pass), the D6 seam, and §6 questions 2–3 — all carried forward as
named-owed in ADR-529 §5 rather than silently dropped.
_Originally:_ Proposed (2026-08-03; **materially amended 2026-08-04** — §2.0 replaces the first
draft's invented three-act reshuffle with the measured two-mount carve, and D6 adds the
flow-vs-rail division. Doc-first: no code has moved.)
**Date**: 2026-08-03 (amended 2026-08-04)
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A (system canon — real-operator-facing)
**Dimension**: Identity (Axiom 2 — who may reach what) + Channel (Axiom 6 — the doors a file
travels through)

**Amends**:
- **ADR-465 D1** (Share is the membership primitive) — preserved and *narrowed*. Share remains
  the membership primitive; this ADR establishes that **most of what the Share button is used
  for is not membership at all**, and stops it minting grants nobody asked for.
- **ADR-512** (the file is the unit of interop) — its verb-ontology axiom is extended: the unit
  a principal is handed is the file's **address**, and addressing is not granting.
- **ADR-437 D4 / ADR-513** — the transport (`/s/{token}`, the public view) is unchanged.

**Preserves**: ADR-373 (the grant is the authorization fact) · ADR-378 (the workspace is the
outermost unit) · ADR-431 (the connecting member owns the MCP grant) · ADR-404 (we relay a link,
we never send on someone's behalf) · ADR-510 (git export is the egress lane) · ADR-514 D2.6 (the
verb bundle is threaded whole, so a new verb reaches every mount).

---

## 1. Context — the flow the button was never designed for

The operator's framing, which is the spine of this ADR:

> *"a shared artifact can be easily accessed and read via MCP for an external ChatGPT or Claude
> session, worked on there, then can update (WriteFile) back when they are done. OR, internally,
> nudge someone to look at it?"*

Two flows. Neither is a membership act. Both are served today by a button that mints membership.

### 1.1 What the Files Share button actually does

One click → a `/s/{token}` link is minted → a toast reads *"Share link copied — anyone with it
can join the workspace."* No dialog, no choice, no recipient, no review. The role defaults to
`member`, so **every use grants full workspace access**, and the toast reports a decision the
operator was never asked to make. (Studio's popover does offer Full-access / View-only, but it
is Studio-only, dismisses on outclick, and sits fused with Export.)

### 1.2 The measured fact that reframes the design

For both flows the operator named, **the reach already exists**:

| Flow | Grant needed? | Receipt |
|---|---|---|
| File → ChatGPT/Claude via MCP, worked on, written back | **No** | `CALLER_WRITE_POLICY["mcp"]` locks only `governance/ contract/ constitution/ persona/ system/`. A connected AI with a workspace grant already reaches every `operation/` file. |
| Nudge a teammate to look at a file | **No** | They hold a member grant with class-default scopes (ADR-373 D3). They can already open it. |
| Someone with no grant at all | **Yes** | The only case that must mint. |

So in two of the three cases, pressing Share **creates an access relationship that already
existed**, and in the internal case it can only over-grant (a `member` link handed to an existing
member is a no-op at best; handed onward it is a leak).

> **The scarce thing inside a workspace is not reach. It is ADDRESSING.** The AI cannot act on a
> file it cannot name; the teammate cannot look at a file nobody pointed them to. Both need the
> file's *address*, not a grant. The Share button answers a question these flows never asked.

This is also why the Figma share modal — considered as a reference and set aside — is the wrong
template. Figma's modal is a permissions surface because in Figma reach is genuinely scarce.
Here, permission is mostly already settled and the missing gesture is *pointing*.

## 2. The axiom

> **Addressing is not granting. Handing someone the name of a file is a different act from
> giving them the right to reach it — and a third act, taking bytes out, gives up both
> attribution and recall. One button must not perform all three.**

### 2.0 The carve this rides on (measured, not invented)

**Amended 2026-08-04** after the operator asked whether the layering was actually right and sent
the Studio header screenshot. Re-reading `StudioSurface.tsx` rather than a summary of it: the
three verbs mount in **two different places**, carved by different ADRs —

| Mount | Verbs | Carved by |
|---|---|---|
| Header cluster (`StudioShareExport`, line 2482) | `share` · `copyAiRef` · `print` | ADR-458 D3 / ADR-466 D6 — document-global **boundary acts**, "where the eye is" |
| Properties File card (`fileVerbs`, line 2762) | `copyLink` · duplicate · move · trash | ADR-455 — the artifact **as a file object** |

**That carve is right, and an earlier draft of this ADR would have overridden it.** The header
groups Share with Export because *both are boundary acts* — the file crossing out of the
workspace, one way or another. The File card groups Copy link with Duplicate/Move/Trash because
*those act on the file as an object*. Two coherent questions, correctly separated by scope.

The prior draft proposed a three-act taxonomy (refer / hand off / grant) and reshuffled verbs
across both mounts to fit it. That repeats the mistake ADR-514 D2 already corrected once:
**inventing a taxonomy instead of reading the mechanism that exists.** This ADR does not
re-carve. It fixes the one placement the carve does not explain.

**The actual defect** is narrow: `copyArtifactLink` and `copyAiReference` are the *same act* —

```
copyArtifactLink → /desktop?studio.file=…    an address for a human
copyAiReference  → yarnnn://workspace/…      an address for an AI
```

Both copy an address to the clipboard. Neither grants anything. Neither exports anything. Yet one
sits beside Export and the other beside Trash. **That split has no basis** — it is the only
grouping in the surface that the scope-carve cannot account for, and it is the whole fix.

`shareArtifact` genuinely does belong beside Export: both are boundary acts. The header cluster
stays as it is.

### 2.1 The acts, and which group each falls in

The three acts below are the *semantics*; §2.0's two mounts are the *placement*. Refer and Hand
off are addressing (File-card group); Grant and Export are boundary (header group). The taxonomy
explains the carve — it does not replace it.

| Act | Mints a grant? | Recipient | The unit handed over | Revocable |
|---|---|---|---|---|
| **Refer** | no | a principal who already has reach (teammate) | an in-app link | n/a — nothing granted |
| **Hand off** | no | a connected AI, on its existing grant (ADR-431) | the `yarnnn://` handle | n/a — the grant is separate |
| **Grant** | **yes** | someone with no reach | a `/s/{token}` capability link | **yes** |
| *(Export)* | no | anyone | **bytes** | **never** |

Only **Grant** has consequences that need confirming. Refer and Hand off are addressing acts:
cheap, safe, reversible by doing nothing. Export is the opposite of all three and is treated as
such (D5).

## 3. Decisions

### D1 — Two groups by scope; only the boundary group gets a dialog

The single `Share…` entry point is replaced by named acts in the TWO existing scope groups
(§2.0). The carve is preserved; one verb moves:

**Addressing acts — the File-card group** (ADR-455 scope: the artifact as a file object). Cheap,
safe, grant nothing, need no dialog:

- **Copy link** — the in-app deep link. For a principal who already has reach.
- **Copy AI reference** — the `yarnnn://workspace/…` handle, for a connected AI to `open` → work
  → `save` back. **This is the one verb that moves** (§2.0): out of the header's boundary
  cluster, onto the File card beside Copy link, where its twin already lives.

**Boundary acts — the header cluster** (ADR-458 D3 / ADR-466 D6 scope: the file crossing out).
Consequential, and they stay exactly where they are:

- **Share…** — grants reach. Revocable. **The only act that mints, and the only one with a
  dialog** (D2).
- **Export** — bytes leave. Irreversible (D5).

`Share…` no longer copies anything on click. The word "Share" is reserved for the act that
changes who can reach the file, which is what makes the word mean something.

**Both groups reach every surface through the ADR-514 D2.6 `FileVerbs` bundle**, so Files, the
tree, the grid, Studio and a future Chat `createfile` inherit them together. Studio's header
cluster is the document-scope *presentation* of the boundary group, not a second implementation.

### D2 — Share is a modal, because granting is consequential

A dedicated, dismissible-only-by-choice modal — not a toast, not an outclick popover. It carries:

- **The choice, stated as consequence** — Full access ("they can work in your workspace") vs
  View-only ("they see this artifact and its history; they cannot change it"). No default fires
  without a click.
- **This file's active links, with revoke in place** — so the operator sees what they have
  already handed out before handing out more, and can take it back here.

**Not in the modal: the standing grant state.** An earlier draft had the modal render "who can
reach this" — every principal, their axes, the connected AIs. That **duplicates the rail** (D6)
and mis-scopes the dialog: the operator is mid-act, deciding one link, not auditing the commons.
Get Info already answers "who can reach this file" (ADR-512 D6) and `WorkspaceMembersCard`
already answers "what does this principal reach." The modal answers only *"what am I about to
hand out, and what have I handed out already."*

**Not in the modal: Export.** See D5.

### D3 — Hand off to an AI is an addressing act, not a share

**Operator-ratified direction (2026-08-03), superseding this ADR's own first draft.** The earlier
draft made "share to an AI" the same act as sharing with a person, on species-blindness grounds.
That was wrong *for this mechanism*: no grant is minted, nothing becomes revocable, and the
connector's reach was already established at connect time (ADR-431). Calling it Share would
overload the exact word this ADR is sharpening.

Species-blindness is preserved where it is true — the file, the verbs, and the attribution are
identical for an AI principal (ADR-512). What differs is that **this particular act grants
nothing**, so it belongs beside Copy link, not inside the grant dialog.

`Copy AI reference` therefore moves out of Export (where it is mis-filed today — it is not
egress) and becomes a peer addressing verb available on every file surface, not Studio alone.

### D4 — Internal referral gets its own deliberation

**Operator ruling (2026-08-03): "maybe the internal also requires its own deliberation."**
Agreed, and scoped out of this ADR deliberately.

`Copy link` (D1) is the *weakest* form of a nudge: it is passive, and the teammate still has to
be told through some other channel. The real internal gesture is more likely a **nudge that
lands where they will see it** — a chat mention, a notification, an inbox item — which touches
the conversation and notification surfaces, not the share sheet.

This ADR ships `Copy link` on every surface (parity with Studio, closing a real gap) and names
the referral question as **owed to its own ADR**. Nothing here forecloses it.

### D5 — Export is a separate affordance, never inside the share modal

**Operator ruling (2026-08-03).** Print/PDF, PNG, and `GET /workspace/export` (ADR-510) stay in
their own control, structurally outside the Share modal — not merely a divider inside it. The
boundary is then impossible to mistake by construction: you cannot confuse a revocable grant with
an irreversible copy if they never appear in the same surface.

Export's own copy states what it is: *bytes that leave, with no attribution and no way back.*

### D6 — The grant is a SUB-STEP in the flow; the rail owns the standing state

**Operator framing (2026-08-03):** *"the grant and permission like consideration can also be a
sub-feature within the major flows? and thus, what kind of share dictates that alongside a
separate rail dedicated to handling grants, permissions?"* — ratified, and it resolves the
layering question this ADR had left implicit.

Grant is not a sibling of the addressing acts. It is a **precondition** each act either already
satisfies or does not:

| Act | Recipient | Reach precondition | If unsatisfied |
|---|---|---|---|
| Copy link | teammate | already a member (ADR-373 D3 class-default) ✅ | — |
| Copy AI reference | connected AI | granted at connect (ADR-431) ✅ | say so, and route to the rail |
| **Share…** | someone with no reach | **not satisfied** ❌ | **minting is how it satisfies it** |

So `Share…` is not a third kind of thing — it is *the addressing act whose precondition is not
met*, and the grant appears **inline, only when actually needed**, because the operator is
mid-act. That is the sub-feature framing, and it is why the grant lives in the flow rather than
being punted to a settings page.

**The rail is `WorkspaceMembersCard`** (Workspace Settings → Access), which already exists and is
more capable than this ADR first credited: it governs humans *and* MCP connectors as peers, and
already does invite / narrow / revoke (ADR-386, ADR-431 D3, ADR-415 D3). It is not rebuilt here.

The division:

> **The flow grants reach as a step toward addressing something. The rail governs reach as a
> standing fact, decoupled from any one file.**

**The seam** (currently undefined, and defined here): when an act's precondition fails, it must
say so and point at the rail — *"No AI is connected to this workspace"* → Access — rather than
failing silently or copying a handle nobody can use.

**Known half-view, NOT closed here:** the rail shows reach as workspace *regions* and never
per-file; Get Info shows per-file reach and never per-principal. Two half-views of one relation,
uncrosslinked. Naming it as owed; closing it is not this ADR's job.

### D7 — The Files over-grant dies as a consequence

Files' `Share…` calls `createShare(path, name)` with no role → always `member` → the toast in
§1.1. Under D1/D2 there is one grant dialog and it always asks. The over-grant is closed by the
design rather than patched, and the fix reaches every surface at once because the verbs ride the
D2.6 bundle.

### D8 — Delete the dead `share` endpoint

`POST /api/share` (`share_file_global`, ADR-127) writes an upload to `/user_shared/` and has **no
FE caller**. It squats the product's most load-bearing word while doing something unrelated.
Singular Implementation: delete it.

## 4. What this does NOT do

- **No new transport.** `workspace_shares`, `workspace_invites`, and the OAuth grant hook stand.
- **No invite/share merge.** An earlier draft claimed "Invite is Share bound to an email — a
  presentation difference." **That was wrong and the correction is load-bearing:**
  `create_invite` has **no `artifact_path`** — invites are workspace-scoped only, so
  "invite this person to *this file*" has no backing today. The two doors never merged because a
  capability is missing, not because the vocabulary drifted. Extending invites to carry an
  artifact scope is a real change with a migration, and it is **not** in this ADR.
- **No notification/nudge system** (D4).
- **No org-above-workspace.** ADR-378 holds.

## 5. Phases

Ordered so each phase is independently shippable and the riskiest surface change lands last.

1. **D8** — delete the dead `POST /api/share` (isolated, no dependents).
2. **D3 + D1 (addressing group)** — `Copy AI reference` leaves the header cluster for the File
   card beside `Copy link`; both join the `FileVerbs` bundle so they reach every surface, not
   Studio alone. This is the §2.0 fix and touches no grant path.
3. **D7 + D2** — `Share…` stops copying on click and opens the modal (choice + this file's links
   + revoke). Closes the Files over-grant by construction.
4. **D6 seam** — an act whose reach precondition fails says so and routes to the rail.
5. **D5** — Export's honest copy pass.

## 6. Open questions for ratification

1. **Can a `viewer` grant a share?** Their axes are `write_scopes=[]`,
   `read_scopes=[artifact]`, but `create_share` requires only *a* grant — so a read-only holder
   can today mint a **member** link. That is an escalation door.
   Recommendation: **a viewer may not grant.** Needs a ruling; it is live in production.
2. **Does `Copy link` need to differ for a principal who lacks reach?** Copying an in-app link
   and sending it to a stranger yields a 403, not a grant — correct, but silent. Should the
   affordance notice?
3. **Folder-level grant.** ADR-514 D2.3 made a folder *referenceable*. The grant model supports
   a path prefix; the UI has never offered it.

## 7. The one-line statement

**Addressing is not granting: point at a file freely, hand its name to an AI freely, and reserve
the word "share" — and a dialog — for the one act that changes who can reach it.**
