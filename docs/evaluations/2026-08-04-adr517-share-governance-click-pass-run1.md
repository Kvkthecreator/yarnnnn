# ADR-517 share-governance click-pass — run 1 (2026-08-04)

**Suite**: `eval-suites/adr517-share-governance-click-pass.yaml` (suite gate 5/5 before the run)
**Instrument**: Claude in Chrome (chrome-devtools MCP), one isolated context per principal
(`owner` / `guest`), anon lanes via curl on the wire; substrate via psql.
**Principals**: owner kvkthecreator@yarnnn.com (67c5c637…) · guest testacct@yarnnn.com
(500f3ae7…) — identity re-asserted from the session JWT in each context before any observation.
**Deploys verified live BEFORE the pass**: API `529bc39` (dep-d9oncb3bc2fs739l1dkg, Render);
FE verified **behaviorally** mid-pass (the viewer-count and Viewer roster label render — both
ship in bbebbda, so Vercel is at/after it).
**Migration state**: 234 applied + verified pre-pass; **235 authored, dry-run, applied and
re-probed DURING the pass** (the finding below).

## Verdict: PASS WITH ONE FOUND-AND-FIXED DEFECT (all 10 run lanes green at end-state)

The defect was caught by exactly the discipline the playbook prescribes — the substrate half
of a ceiling step, executed against the real policy set rather than the migration text.

---

## Per-step verdicts

| # | Step | DOM/wire half | Substrate half | Verdict |
|---|---|---|---|---|
| 1 | owner-mints-viewer-share-from-studio | Popover offers Full-access + View-only with consequence copy; View-only clicked | 1 active row: `role=viewer`, `shared_by=owner`, `artifact_path=/workspace/operation/untitled-deck/deck.html` — **canonical ABSOLUTE from a relative-sending origin** (D5 write-normalizer live) | **PASS** |
| 2 | anon-preview-serves-with-capability-headers | curl: 200 + `cache-control: no-store` + `x-robots-tag: noindex, nofollow`; body = artifact + 6-entry attribution walk, `role: viewer` | rig active grants still 1 — previewing minted nothing | **PASS** |
| 3 | guest-accepts-viewer-link | Accept page honest for the shape: "read-only" label, "View read-only" button, walk rendered | New ACTIVE grant `role='viewer'`, `write_scopes={}`, `read_scopes={/workspace/operation/untitled-deck/deck.html}`, `granted_by=share-view:owner` — **the D1 receipt; pre-517 this row said `member`**. Old revoked member row untouched | **PASS** |
| 4 | viewer-reaches-switcher-and-roster | Guest `/api/workspace/memberships`: rig present with `role: "viewer"` (D6 — the pre-517 filter dropped viewers). Owner user-menu: "2 people". Owner roster: `testacct — Viewer — Write: read-only`, governable (Manage present) | roster API returns the viewer row | **PASS** |
| 5 | viewer-mint-refused-at-server | Guest wire POST `/api/workspace/shares {role:member}` → **403**, server's words legible: *"A view-only grant cannot create share links (ADR-517: minting a grant is governance — ask the workspace owner)"* | active shares still 1 — no second row | **PASS** — the §6.1 escalation door is closed in production |
| 6 | viewer-write-refused-at-db | psql role-simulation as guest (`SET ROLE authenticated` + `request.jwt.claims`) INSERT into rig workspace_files | **FIRST RUN: FAILED — `INSERT 0 1`.** See finding. After migration 235: **`ERROR: new row violates row-level security policy`** + owner positive control still inserts + viewer SELECT still returns 6 (read reach intact) | **PASS after fix** |
| 7 | viewer-revoke-refused | Guest wire POST revoke on owner's share → **403** *"Only the workspace owner or the link's creator may revoke it"* | owner's share still `active` | **PASS** |
| 8 | dead-endpoint-is-gone | curl POST `/api/share` → **404** | 0 new `/user_shared/` rows | **PASS** |
| 9 | owner-revokes-via-get-info | Get Info renders WHO CAN REACH (owner can-edit + testacct viewer read-only) AND "View-only link" row with Revoke — the canonical-spelling row FOUND (the 740f726 defect class, clean); Revoke clicked | share row → `revoked` | **PASS** |
| 10 | revoked-link-goes-dark-with-headers | curl → **410** + BOTH capability headers on the error | — | **PASS** |
| 11 | cleanup-revoke-viewer-grant-and-reassert-baseline | Rail's own owner-gated endpoint (`/api/workspace/members/{pid}/revoke` → 200) — see instrument note | ALL baseline numbers restored (below) | **PASS** |

## The finding — legacy user_id RLS policies bypassed BOTH membership and the viewer exclusion

Step 6's first execution **succeeded where it must refuse**: a viewer-role principal's direct
INSERT into `workspace_files` landed (rolled back by the probe's own transaction; the live
tree was never touched — file count 6 throughout).

**Root cause** (from `pg_policies`, not migration text): the pre-ADR-373 single-principal
policies survive on every command — `"Users can insert own workspace files"` has
`WITH CHECK (user_id = auth.uid())` with **no workspace constraint**. Permissive policies OR
together, so it bypassed the Members predicate AND migration 234's `role <> 'viewer'`. Worse
than the viewer lane: **any authenticated principal could insert a row into ANY workspace** by
stamping their own uid (a cross-workspace write door for direct PostgREST callers). The same
pattern existed on `workspace_file_versions` (`"Authenticated users can insert own workspace
file versions"`). Migration 198 had marked these "transition — either grants access" and they
were never dropped.

**Why nothing else caught it**: the unit gate (test_adr517 F2) asserts the *migration text*;
the migration-234 verification queried only the `Members%` policies. Both were green while the
live policy SET disagreed — the exact "app-layer scoping is HALF a sweep / a text gate checks
text" lesson, now with an RLS-layer instance: **a policy audit must enumerate `pg_policies`,
not the migrations that created them.**

**Fix**: migration 235 (`235_adr517_drop_legacy_user_id_policies.sql`) drops all six legacy
`user_id`-keyed policies (4 on workspace_files, 2 on workspace_file_versions). Post-373 they
guarded nothing legitimate: every row carries workspace_id (189 re-key); owners pass the owner
branch; members the grant branch. Dry-run → applied live → **re-probed three ways**: viewer
INSERT refused (42501), owner INSERT allowed (positive control — the instrument can still
distinguish), viewer SELECT intact (read reach preserved).

## What was NOT run (recorded per §7)

- **dial-owner-only lane** — needs a write-holding member this cut does not mint; the dial's
  decision table is covered by the executed unit gate (test_adr517 A4). Owed to the
  member-pair run alongside the ADR-515 FE phases.
- **Files one-click member mint** (ADR-515 D7) — known, unchanged by ADR-517, closed by
  ADR-515 phases 3+; not retested.
- **Instrument notes**: (a) step 6 ran as psql role-simulation (`SET ROLE authenticated` +
  `request.jwt.claims`), not wire PostgREST — same policies evaluated, same role GRANTs; the
  anon-key wire variant is a nice-to-have, not a gap in the RLS conclusion. (b) step 11's
  DOM half degraded: the desktop shell kept the settings window unfocused after the Files
  detour, so the revoke ran through the rail's own owner-gated endpoint (wire, 200) instead of
  the roster button; the roster's render half was already covered by step 4. (c) Navigating
  to `/workspace-settings` and `/files` by URL renders whatever window the shell restores —
  reach panes through the user menu / dock, not the address bar (playbook-worthy nuance).

## Baseline re-assert (end of pass)

| Receipt | Baseline | End | |
|---|---|---|---|
| rig active grants | 1 (owner) | 1 (owner) | ✓ |
| guest active grants anywhere | 0 | 0 (viewer grant revoked; the two revoked rows are the historical ledger) | ✓ |
| rig active shares | 0 | 0 (minted link revoked in step 9) | ✓ |
| rig dial | write-holders | write-holders | ✓ |
| rig workspace_files | 6 | 6 | ✓ |
| live ws (d5b9029b-bd4e…) grants | — (read-only guardrail) | kvkthecreator@gmail.com + seulkim88 both active, untouched | ✓ |

Every delta of the pass is accounted for: 1 share row minted→revoked, 1 grant row
minted→revoked, migrations 234 (pre-pass) + 235 (mid-pass fix) applied. No unexplained drift.
