# ADR-514: The File-Verb Completion — Duplicate as Derivation

**Status**: **D1 Implemented** (2026-08-03) · **D2 OPEN — the framing is being re-cut**
(operator, 2026-08-03: the "intent-claim" framing below is the WRONG frame — think closer to a
pure-OS, file-native approach. D2 as written is preserved only as the rejected first attempt; do
not build from it. The forcing case it identifies is real; the modelling is not.)
**Date**: 2026-08-03
**Dimension**: Substrate (a new kernel verb) + Channel (which app claims a file, and for what)

**Amends**: ADR-451 (the "Open with" picker deferral resolves — but the second claimant is a
*relationship*, not a second renderer) · ADR-436 (the app registry's row gains an intent) ·
ADR-473 D2 (the runtime-learned kind→app table gains a second axis) · ADR-448 (the reference
edge gains its first operator-initiated producer)
**Preserves**: ADR-400 Amendment 1 (the optimistic model — the FE offers, the backend decides) ·
ADR-209 (`write_revision` stays the single write path) · ADR-452 D5 ("Learn from" is a creation
act homed on the Studio landing, not a file operation)

**Deferred to a separate lane** (operator ruling, 2026-08-03): the **boundary acts** — Share
wiring on Files, Copy AI reference, Copy link. They are held for full discourse *after* this
ADR's items stabilize and deploy. See §6.

---

## Context — what the audit found

A 2026-08-03 audit of the Files right-click menu against the kernel's verb surface (prompted by
the operator observing that recently-developed kernel actions were not reflected in the menu)
produced a full inventory. The result was better than feared in one direction and worse in
another.

**Healthy — genuinely singular implementations:**

- Rename / Move / Trash: `useFileOrganizeVerbs` is one hook, called by both the Files page and
  the Studio surface. The "SAME shared implementation" claim in its header was *tested*, not
  trusted, and it holds — a fix to the rename path reaches both surfaces.
- `FileContextMenu` + the `FileVerbs` bundle: one menu, four mount sites (left tree, RecentsView
  grid, ContentViewer listing, Studio recents).
- Properties: `PropertiesModal` wraps `NodeDetailsPanel`, which carries the ADR-512 D6 reach rows
  ("Who can reach this") and per-file share management. This DID land on Files.

**The pattern of failure:** verbs *born in Files* were properly shared. Verbs *born in Studio*
were authored as local callbacks inside `StudioSurface.tsx` and never lifted into the seam. Four
verbs sit in that class. Three of them (the boundary acts) are deferred by §6. The fourth —
**duplicate** — turns out not to have a kernel to be lifted *to*.

### The duplicate finding

`StudioSurface.tsx::duplicateArtifact` is a client-side re-implementation of a verb the kernel
does not have. There is no `DuplicateFile` primitive in `services/primitives/registry.py`; there
is no duplicate/copy route. The browser-side implementation:

1. Probes `getFile` up to five times looking for a free `-copy` suffix — a TOCTOU race (two
   duplicates in flight both see the same suffix free), and a hard cap at five copies.
2. Is `.html`-only by construction (`artifactPath.replace(/\.html$/, '')`), so it structurally
   cannot duplicate `_watch.yaml`, a `.md`, or an upload.
3. **Passes no `derived_from`** — so every duplicate made to date is an attribution orphan. The
   ADR-448 reference edge exists precisely to record "this content was made from that content,"
   and the one operator gesture that is *definitionally* a derivation does not use it.

Point 3 is the load-bearing one. Under FOUNDATIONS' attribution axiom, a file that came from
another file and does not say so is a hole in the record — not a missing convenience.

---

## D1 — `DuplicateFile` becomes a kernel primitive

A new primitive in the registry. **Duplicate, not copy** — the name is chosen against three
existing meanings of "copy" in this codebase (`copyLink`, `copyAiRef`, and the block-clipboard
`onCopy` in `StudioBlockMenu`), all of which mean *put a reference on the clipboard*. A fourth
"Copy" meaning *write a new attributed file* would collide. "Duplicate" also names the truth:
under ADR-209 a file is a revision chain, and the new file is a **derivation with an attributed
parent**, not a byte-identical clone with no lineage.

Contract:

- **Server-side suffix resolution.** The kernel picks the free name in one query against
  `workspace_files`, not an N-round client probe. No arbitrary cap.
- **Format-agnostic.** Operates on the path's extension generically, whatever it is. `_watch.yaml`
  duplicates to `_watch-copy.yaml`.
- **Writes `derived_from`.** The new revision records its parent path per ADR-448, so `trace` on
  the duplicate walks back to the original. This is the correctness fix, not a feature.
- **Goes through `write_revision`.** No second write door (ADR-209). The ADR-320 caller-class
  lock-set applies unchanged — a duplicate into a locked root is refused like any other write.
- **Attribution is the acting principal**, via the ADR-288 path — a duplicate is an authored act,
  not a system act.

`StudioSurface.tsx::duplicateArtifact` is **deleted**, not left alongside (Singular
Implementation). Studio's File card calls the shared verb like every other surface.

Open question for implementation (not blocking ratification): whether duplicating a *folder* is
in scope. Recommendation: **no** for v1 — a folder duplicate is a recursive multi-write with its
own failure semantics, and no observed demand. Files-only, stated as a limit.

## D2 — Open With  ⚠️ **REJECTED FRAMING — preserved as the first attempt, do not build**

> **Operator ruling (2026-08-03):** *"inherit via intent is the wrong framing. think closer to
> pure OS, file-native approach."* The section below models the problem as apps declaring an
> *intent* toward a file (edit/reason/observe) — a claim taxonomy layered over two registries.
> That is the frame being rejected. What survives is the **forcing case** (§D2-context: the
> second claimant is not a second renderer) and the **honest gap** (Chat has no receiving
> contract). The re-cut happens before any D2 code lands.
>
> Recorded because a rejected attempt is evidence: the next pass should be able to see what was
> tried and why it read as un-OS-like, rather than re-deriving it.

### (rejected) The app registry's row gains an INTENT

ADR-451 D3 deferred the "Open with" picker "until a second installed app claims the same format,"
and built for that future correctly: `resolveApps` already returns an *ordered list*, and ADR-473
D2 made the kind→app table runtime-learned so a program-shipped type routes without an FE deploy.

**The deferral's forcing case has arrived — in a shape ADR-451 did not anticipate.** It assumed
the second claimant would be another *renderer* (a rival viewer for `.html`). The operator's
actual case is "Open with Chat" beside "Open with Studio" — and Chat is not a renderer. Chat does
not draw `_watch.yaml`; it *reasons about* it. That is a second **relationship** to the same file,
not a second rendering of it.

So the registry row widens from *"this app renders this format"* to *"this app claims this file,
for this relationship."* Claim kinds, v1:

| Intent | Meaning | Claimant |
|---|---|---|
| `edit` | opens the file as an authoring canvas | Studio, Images |
| `reason` | takes the file as material to think about | Chat |
| `observe` | opens the file's standing view | Radar (the ADR-486 declaration claim) |

The default remains the highest-ranked claim for the file's type — so today's single-claim files
open exactly as they do now, byte-identical. **"Open With" renders only when a file has more than
one claim**, which is precisely ADR-436's stance ("render only when `length > 1`") reached at last
by a real case rather than a hypothetical one.

This preserves the macOS reference the operator cited: Finder lists Preview *and* Photoshop for a
`.png` because both open it — differently. It does not list every installed app.

### The receiving contract (the honest gap)

`navigateToSurface('chat')` exists but **takes no file parameter**. Studio and Images receive a
file through a window-namespaced param (`studio.file`, `images.file`); Chat has no equivalent.
So "Open with Chat" is not merely a registry row — it needs Chat to accept a file as an open
target.

The natural shape, and the one this ADR proposes: **opening a file with Chat starts a turn with
that file bound** — the same *bind* (not upload, not copy) that ADR-512 D6 already built for
attach-from-workspace in the composer. The file arrives as a chip referencing its existing path.
This reuses a shipped mechanism rather than inventing a second one.

This is the piece most likely to want operator discourse; it is called out here rather than
buried in implementation.

## D3 — What is deliberately NOT built

- **No per-file default overrides** ("always open this file with X"). macOS has it; we have no
  demand signal, and it needs a persistence story. Deferred, explicitly.
- **No third-party app rows.** The one-file ratchet (`apps.tsx` header) stays red until an
  App(principal) ADR flips it. Intent-claims widen the row's *shape*, not who may write rows.
- **No folder duplicate** (see D1).
- **The boundary acts** — see §6.

---

## §6 — The deferred lane: the boundary acts

Held by operator ruling (2026-08-03) for full discourse after this ADR's items stabilize and
deploy. Recorded here so the deferral is deliberate and the findings are not lost:

1. **Share wiring on Files.** The two-shape share sheet EXISTS and is correct
   (`StudioShareExport` — Full access / View-only, with honest per-mode consequence copy, landed
   at `d0a8b10`). The defect is that Files' right-click Share… does **not** route to it: it calls
   `createShare(path, name)` with no role, so it silently mints a **full-access member grant** and
   copies. ADR-465 D3's premise is that "just look at this" must never over-grant; the one surface
   reachable by right-click always over-grants. **This is a live over-grant defect, not a polish
   item** — it should be weighed accordingly when the lane opens.
   - Note for that discourse: the sheet currently lives in `StudioShareExport` beside Export
     (Print/PDF, PNG — Studio-specific). Lifting Share means extracting the sheet and leaving
     Export behind.
   - Note on gates: `test_adr465_share_as_view.py` check 5b ("client sends role on createShare")
     passes today because it inspects the *client function* and Studio's caller. It cannot see the
     Files caller. A per-site enumeration gate is owed —
     the counting-gate-cannot-defend-a-per-site-invariant class.
2. **Copy AI reference** (the `yarnnn://workspace/…` handle, ADR-512 D5) — exists only in Studio
   (`copyAiReference`). Files has no way to hand a file to an outside AI, which is the primary
   interop gesture.
3. **Copy link** (the in-app member deep-link) — same shape, Studio-only.

All three are *wiring* gaps over shipped, correct implementations. None needs a new kernel verb.

---

## Consequences

- One new kernel primitive (`DuplicateFile`), one deleted client-side re-implementation.
- Every duplicate made from ratification forward records its parent; **existing duplicates stay
  orphaned** (no backfill — the origin was never captured and cannot be inferred).
- The Files menu gains Duplicate and (where a file has >1 claim) Open With.
- ADR-451's picker deferral closes; ADR-436's `length > 1` condition becomes reachable.
- Chat gains a file-open contract, reusing the ADR-512 D6 bind.

## Gates owed

- Executing gate for `DuplicateFile`: format-agnostic (assert a non-`.html` path duplicates),
  `derived_from` written (assert the edge lands), suffix resolution server-side (assert no client
  probe), and the ADR-320 lock-set still refuses a locked root.
- A gate asserting `StudioSurface.tsx` no longer contains a local duplicate implementation
  (Singular Implementation, enforced).
- Registry gate: every claim row declares an intent; the picker renders iff `claims.length > 1`.
