# ADR-510 — One binary lane, and the portability export ships

- **Status**: **Accepted + Implemented** (2026-08-01, operator-directed — *"lets do the
  binary lane split clean up and ADR export"* — against the 2026-07-31 import/export
  boundary audit's receipted findings.)
- **Date**: 2026-08-01
- **Dimension**: Substrate (Axiom 1 — where binary bytes are authoritative) + Channel
  (ADR-328 D4 — export as the portability surface). No schema change, no migration, no
  new primitive.
- **Amends / resolves**:
  - **ADR-462 D13** — the design-system import's binary lane (documents bucket + stored
    `content_url`) is **deleted**, replaced by the one door's binary lane
    (`write_revision(content_bytes=…)` → the ADR-427 CAS seam). D13's *citation-not-inline*
    principle survives; only the transport is re-cut.
  - **ADR-328 D4 (PROPOSED → this ships it)** — the Category-1 git export exists:
    `GET /api/workspace/export`. Q1's "Phase 2, possibly its own follow-on ADR" — this is
    that ADR.
  - **ADR-328 D8 (OPEN → resolved)** — the binary-portability gap closes by **option (c)**
    for substrate binaries (ADR-427 already brought binaries into Category 1; this ADR
    migrates the one writer still on the legacy lane and repairs the live divergence).
    Legacy raw-lane rows that remain are handled by the **declared-omission discipline**
    (D8's binding rule) — named in the export manifest, never silently absent.

---

## Context — the lane divergence (receipts: the 2026-07-31 audit)

The design-system importer (`design_system_import.py`, shipped 2026-07-16 at `4fe9eec`)
wrote binaries through the only binary lane that existed that day: the ADR-395 `documents`
bucket, with a stored `content_url` and a version chain recording the **empty sha**
(`e3b0c442…`) by design. Four days later (`de53ca4`, 2026-07-20) ADR-427 Phase 2 opened the
substrate's own binary lane — CAS marker rows behind the storage seam — and the importer
was never migrated. Result, receipted live:

- **Serving never broke** — the projection resolves `content_url` and the bucket had the
  bytes. Ten bucket objects, all full-size.
- **The substrate's own record of every imported binary was EMPTY.** `is_binary` is
  `bool(storage_key)`, so revision reads saw empty text, and a Category-1 export would
  have shipped **nothing** for them. The divergence *is* the import/export fault line.
- A prior repair attempt (2026-07-31) wrote a **truncated** Pacifico into the CAS —
  196,608 of 315,408 bytes, exactly 192KB, byte-compare-verified a prefix — the precise
  silent-half-landing failure class this arc exists to prevent.

Two binary lanes, each half-authoritative, is a Singular Implementation violation at the
storage layer. And ADR-328's portability claim (*"the single sharpest technical
differentiator YARNNN has"*, THESIS Commitment 4) had **no falsifying artifact** — no
export existed (`GET /authored/{slug}/export` is an ADR-417 410-tombstone;
`POST /integrations/{provider}/export` is channel delivery, not portability).

## Decisions

### D1 — One binary lane: substrate binaries live in the CAS, full stop.

`write_revision(content_bytes=…)` is the only way binary bytes enter the workspace. The
design-system importer's bucket lane (`_put_binary`, `binary_mime`,
`FONT_UPLOAD_SUPPORTED`, the `fonts_deferred` receipt field) is **deleted**. Binaries land
as `revision_kind="observation"` revisions on the service client (seam-managed storage,
same as uploads — `routes/documents` precedent); type is derived from the bytes at the
door (ADR-427 D5); the serving URL is minted at read (D4), never stored. A binary that
fails to land is **named in the receipt's warnings** — the import still lands the rest.

The `documents` bucket remains what ADR-395 made it: the legacy raw-upload lane, serving
existing rows. No new writer targets it from the design-system path.

### D2 — The FE serving fork: minted URLs pass through.

`GET /workspace/file` returns either a legacy stored `/api/documents/blob?storage_path=…`
reference or a **minted absolute URL** for a CAS head (ADR-427 D4). `blobUrl()` rejects
absolute URLs by design, so every CAS-lane citation silently fell to the catch and never
rendered. `projection.ts` now forks through one helper (`servingUrl`): absolute → as-is,
relative → authenticated resolve. Three sites (skin `url()`s, `<img data-ref>`, cited
backgrounds); `FileTile`/`useSignedBlobUrl` already had the fork.

### D3 — The portability export ships: `GET /api/workspace/export`.

Category 1 leaves as a **plain git repository inside a zip** — blobs → git objects, the
revision chain → linear commit history (`authored_by` → author, identity uuid → email
local-part, `message` → message, `created_at` → date), live files → working tree, plus a
v2 index so `git status` is clean on arrival. Pure-Python loose-object writer
(`services/export/git_export.py`) — no git binary, no dependency, verified by an
independent re-parser AND `git fsck --strict` in the gate. A final **reconcile commit**
prunes hard-deleted paths from the tree while their history remains (named in its own
commit message). Delivered as a route, not a primitive (ADR-328 Q2 — operator
sovereignty, not an LLM tool). An FE download affordance is owed separately; the route is
the sovereignty guarantee.

### D4 — The manifest declares what it omits (ADR-328 D8's binding discipline).

`EXPORT-MANIFEST.md` rides beside the repo at the zip root and names every omission
class: Category-2 reconstructable caches; Category-3 sidecar descriptors; non-substrate
state (conversations, events, grants); **legacy raw-lane binaries** whose bytes never
entered Category 1 (listed by path); CAS read failures (listed); and, for a
powerbox-narrowed principal, the **count** of revisions outside their read grant (count,
never names). Silent omission would make "portable" a lie.

### D5 — The live divergence is repaired (receipts).

Executed 2026-08-01 against workspace `d5b9029b-bd4e-4757-9fcb-e2b139fd4913`, full bytes
sourced from the documents bucket, written through the one door, stale `content_url`
sidecars cleared:

| Asset | New head revision | byte_size |
|---|---|---|
| `assets/brand/og-card.png` | `74bfa98f-af31-455d-9e50-ffc7f39e0c7f` | 578,839 |
| `assets/fonts/Pacifico-Regular.ttf` | `71afb389-e8aa-4ae7-90a7-d18f36a1de7f` | **315,408** (supersedes the truncated 196,608 blob) |
| `assets/logos/yarnnn-mark-dark.png` | `f28de2d8-abfb-4592-af45-6da7a43b7d4f` | 226,660 |
| `assets/logos/yarnnn-mark-thread.png` | `0c999a80-0075-4b35-9e5f-04249796cd2a` | 158,295 |
| `assets/logos/yarnnn-mark.png` | `e84ae793-a9bc-4f10-8166-49b284471329` (already correct — no new write) | 106,686 |

End-to-end serving probe: mint → fetch → 315,408 bytes for the repaired font. Remaining
cruft, deliberately untouched: the `design-system/yarnnn-zip-probe/` rows (a 2026-07-16
probe import) and their bucket objects — deletion is lifecycle machinery (ADR-476/478),
out of this ADR's scope; they now surface honestly in any export manifest as legacy
raw-lane binaries.

## Gates

- `api/test_adr510_one_binary_lane.py` — EXECUTES the import against recording fakes:
  binaries as `content_bytes` on the service client, nothing touches a bucket, a failed
  binary is named. Falsified red (revision_kind ablation) and against the pre-510 code by
  construction.
- `api/test_adr510_git_export.py` — independent loose-object re-parse (chain, trees,
  bytes, index checksum) + `git fsck --strict` / `git log` / empty `git status --porcelain`
  when git is present + D4's declared-omissions assertions. Falsified red via a tree-sort
  ablation (`git fsck: treeNotSorted`).
- `api/test_adr449_design_system.py` — the D13 pins re-cut to the one-lane invariant
  (no bucket revival in the module; failed binaries warn).

## What this is NOT

- **NOT a migration of the documents bucket.** Legacy raw uploads keep serving via
  `content_url`; they enter exports as declared omissions until (if ever) a bulk
  re-lane is worth its cost. The one *writer* on the legacy lane is what this deletes.
- **NOT git as the store.** ADR-208 stays withdrawn; Postgres remains the host
  (ADR-328 D4's already-settled split — git is the export format only).
- **NOT the full ADR-328 Phase 1 canon package.** FOUNDATIONS DP26 / GLOSSARY
  category vocabulary / the D3 reconstruction guard remain owed to ADR-328's own
  ratification; this ADR ships D4 + resolves D8 without pre-empting that write.
