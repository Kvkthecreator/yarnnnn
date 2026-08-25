# Layer-1 click-pass, run 1 — G2 driven in production (2026-08-26)

**Lane**: surface (browser). **Target**: notifications Layer-1 G1–G4 at `4f81bf8`.
**Principals**: `kvkthecreator@yarnnn.com` (owner, rig `bf5b25a9`) ·
`testacct@yarnnn.com` (member instrument), one isolated browser context each,
identity re-asserted from the page before every observation.

## Verdict

**G2 (ADR-608, membership joins the timeline) PASSES on both halves**, driven
through the real invite → accept lifecycle. Two defects found, neither in G2's
own derivation; one of them **falsifies a claim the ADR-608 gate makes in prose**.

## What was driven

| Step | DOM half | Substrate half |
|---|---|---|
| Baseline | owner timeline: 60 entries, **0 membership** | 4 grants on rig, **0 qualifying** |
| Invite | `POST /workspace/members/invite` → 200, real link | invite row `pending` |
| Accept (guest clicks "Accept invite") | redirected into workspace | grant `member/active` @ 23:30:41 |
| Owner observes | **"testacct joined the workspace · member · Aug 26, 8:30 AM"** at top of Activity; name resolved, no UUID, no `member:` prefix leak | timeline API: exactly 1 `membership`, `weight=material` |
| Revoke (restore) | — | qualifying back to **0**; owner grant intact |

**The baseline was the discriminating case.** `testacct` already held TWO
revoked grants on this rig (2026-07-31, 2026-08-04). Both stayed invisible
throughout, and the owner's founding grant never appeared. ADR-608's two
refusals — joins-only, and owner-genesis-is-not-arrival — hold against live
data, not just in the gate. On revoke the row's `created_at` stayed 23:30:41
and simply left the derivation: no wrong-timed "left" was emitted.

## Finding 1 — self-suppression is claimed in the gate but absent from the ledger

`test_adr608_membership_on_the_timeline.py` asserts `actor_id=pid` rides along
"so the viewer layer resolves + **self-suppresses**". Only half is true.

- `AttentionCenter.tsx:312` filters `.filter(({ who }) => !who.isSelf)` — the
  **bell** does suppress.
- `ActivityLedger.tsx:150` maps every entry through `resolveActorForViewer`
  and **never filters on `isSelf`** — the **Activity workbench** does not.

`resolveActorForViewer` returns `{label, isSelf}`; it *labels*, it does not
filter. Confirmed against the API: requesting the rig workspace as the joiner
returns their OWN membership row (`actor_id` == own principal id), unsuppressed.
A joiner viewing that workspace's Activity ledger sees **"You joined the
workspace"**.

**Why the first observation looked like a pass** — and this is the lesson: the
joiner's default binding is their OWN (empty) workspace, so the row was absent
**for the wrong reason**. The check passed vacuously. Only re-issuing with
`X-Workspace-Id: bf5b25a9` exposed it.

## Finding 2 — post-accept staleness (pre-existing, not a Layer-1 regression)

Immediately after accept, the member's first page load produced a wall of 403s
(`mentions`, `proposals`, `members`, `user/limits`, `member-state/*`), and
`/workspace/timeline` returned **both 200 and 403 in the same load**. Body:
`No active grant into workspace bf5b25a9` — for a principal who held an active
grant on exactly that workspace.

Diagnosis: **transient propagation race**, self-healing, server behaving
fail-closed and correctly (`principal_reaches_workspace`, ADR-499's known
stale-pin shape). Re-issued later: 200. Related staleness in the same window —
the workspace switcher omitted the just-joined workspace until a reload
(`useWorkspaceMemberships` is module-cached, "one fetch per page life", by
design), and the bell rendered rig rows while the workbench showed "Nothing here
yet". After reload + Retry, the switcher listed
**"kvkthecreator@yarnnn.com's workspace · 2 people (Member)"** correctly.

Not authorization; a first-run experience gap for a brand-new member.

## Guardrails re-asserted (not assumed)

- Owner grant on `bf5b25a9` untouched and `active`.
- Qualifying membership grants restored to 0 = baseline.
- Owner timeline re-queried post-restore: 0 membership rows.
- No live-workspace principal used; rig only.

## Not covered by this run

- **G1** (stamp at the write chokepoint), **G3** (realtime badge latency),
  **G4** (own-chip, DM wording, outsider add-door) — not driven. G3 in
  particular needs a mention *sent* while a recipient watches.
- **G5** suppression live-proof — still unbuilt.
