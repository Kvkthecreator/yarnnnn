# ADR-555 — Arrival has a "here", and placement has one law

> **Status**: Accepted (2026-08-12, operator-ratified — *"shift the discussion towards allowing users more easier file moving or pasting from external places"* + sign-off on the four-phase proposal). Phase 2 of the arrival/move proposal.
> **Amends**: [ADR-440](ADR-440-the-studio-the-first-authoring-app.md) D6 (the `STUDIO_ARTIFACT_REGION` fence — relaxed to the organize predicate) · [ADR-395](ADR-395-model-consumable-projection-and-upload-intake-conformance.md) (uploads may land outside `inbound/uploads/`; the lane becomes the DEFAULT, not the law)
> **Preserves**: ADR-424 D1/D2 (one home directory, peer folders) · ADR-422 D2 (raw intake stays immutable; the uploads sublane stays organizable) · ADR-448 / DP32 (an arrival is badged `revision_kind='observation'` — on the ledger) · ADR-549 D3 (the default is where the act is standing) · ADR-554 (the projection follows its raw)
> **Derivation**: the 2026-08-12 arrival/move audit
> **Amended**: 2026-09-16 — the `{principal}/` sublane §1 named as the defect is DROPPED from the path; chat attachments take their own destination; retention stays NONE (see the amendment below).

---

## 1. The defect

**Every OS-file drop ignores which folder is open.**

The canvas drop passes no destination (`files/page.tsx:1219`), the route accepts
none (`routes/documents.py:297-302`), the client sends none
(`client.ts:933-950`), and the modal offers none (`UploadButton.tsx:162-172`).
The destination is fixed three levels down, in `resolve_upload_raw_path`, with
`principal = "operator"` as a literal.

Meanwhile **`New Folder` already honours the open folder** — Finder's rule,
shipped, *in the same file* (`files/page.tsx:1240-1247`). Arrival is the one act
on the surface that ignores where the member is standing.

Worse, dropping an OS file onto a **folder row** in the tree does nothing at
all: the row accepts only `application/x-yarnnn-path` (`WorkspaceTree.tsx:199`),
and the canvas handler is not on the tree pane. The most direct expression of
"put this here" is silently swallowed.

## 2. The question this forces, for the third time

Making the destination caller-supplied means an upload can land in a meaning
folder. That is the same question three verbs have now answered differently:

| Verb | Placement law |
|---|---|
| `create_folder` | `operator_can_organize` — honours ADR-424 D2 peer folders |
| `create_artifact` | fenced to `operation/` (ADR-440 D6) |
| `upload_documents` | fenced to `inbound/uploads/` — **and authorizes nothing at all** |

That last cell is the sharpest finding of the audit. `upload_documents` never
calls `operator_can_organize`, because a hardcoded destination had nothing to
authorize. **The moment a destination becomes caller-supplied it needs one** —
this is precisely the ADR-549 F1 defect (a door that offers what the server
would refuse), and it must not ship twice.

## 3. Decisions

### D1 — An arrival is badged on the ledger, not by its path

The objection to letting uploads land anywhere is that `inbound/` records *what
arrived from outside* (ADR-376 / DP32) — move the file and you lose the fact.

**That fact is already stored somewhere else.** `process_document` writes the
raw with `revision_kind="observation"`, and the code says why, verbatim:

> *"an inbound/ write is an observation — the arrival badge on the ledger, not
> the path."* (ADR-448, closing the ADR-423 D3 gap)

So the arrival record survives placement, and ADR-422 D2 already proved the
point in the other direction: uploads are **organizable**, so a member could
always move one out of the lane the moment after it landed. The lane was never
carrying the fact — it was carrying a default.

**`inbound/uploads/` becomes the DEFAULT destination, not the law.** Non-human
intake (`inbound/slack/`, connectors) is untouched and stays immutable — that is
ADR-422 D2's actual carve, and this ADR does not widen it.

### D2 — One placement law: `operator_can_organize`

Every creation and arrival verb asks the same question of the same predicate.

- `upload_documents` takes an optional destination folder, and **authorizes the
  resolved path** — the check that did not exist because it had nothing to
  check.
- `create_artifact`'s `STUDIO_ARTIFACT_REGION` fence is **relaxed to the same
  predicate**. ADR-440 D6's actual rule — *"the app owns no namespace; projects
  are meaning-placed folders, never `studio/…`"* — is **preserved**, because
  that rule was about not inventing an app-named root, not about confining work
  to `operation/`. A deck in `the-acme-deal/` satisfies D6 exactly.

`STUDIO_ARTIFACT_REGION` survives as the **default home** (ADR-549 D3's third
rung), not as a gate. The FE mirror widens with it — ADR-549 wrote
`defaultDestinationFor` so this needs no edit there.

### D3 — Where an arrival lands, in order

Reusing ADR-549 D3's ladder rather than inventing a second one:

1. **The folder the drop happened on** — a tree folder row, or the folder the
   canvas is showing.
2. **The Documents home** when there is no "here" (Recents, a virtual group, an
   open file).
3. **`inbound/uploads/`** only when the caller supplies nothing at
   all — every non-Files caller, unchanged. (As shipped this was
   `inbound/uploads/{principal}/`; the sublane is dropped by the 2026-09-16
   amendment below — it had one possible value.)

The uploaded file keeps its real filename in a meaning folder. (The
`{principal}/` sublane was a property of the *default* home only, and is gone
entirely as of the 2026-09-16 amendment.)

### D4 — The refusal is visible before the drop, not after

The picker/door must ask the same question the server will. A folder the server
would refuse is not offered as a drop target: the drop-highlight does not arm,
and the modal states the destination it resolved rather than a fixed banner.

This is ADR-549's F1 lesson applied at the arrival door — *permission answers
"may I write here"; the door must ask it before the member commits*.

## 4. What is deliberately not built

- **No change to non-human intake.** `inbound/slack/` and connector lanes stay
  immutable (ADR-422 D2).
- **No `.zip`-into-a-folder expansion semantics change** — a zip still expands
  through the same path, now under the resolved destination.
- **No paste.** Phase 3's sibling; nothing in the audit shows a member reaching
  for it yet.
- **No folder drop / folder upload** (`webkitGetAsEntry`). One arrival shape at
  a time.
- **No backfill.** Files already in `inbound/uploads/` stay there; they are
  organizable and the member moves them if they want to.

## 5. Falsifiers

1. Drop a PDF on the `fundraising/` tree row → it lands in `fundraising/`, not
   `inbound/uploads/`.
2. Drop a PDF on the canvas while `fundraising/` is open → same.
3. Drop on Recents (no "here") → Documents.
4. An upload with no destination supplied (any non-Files caller) → the lane,
   unchanged.
5. A folder the server would refuse (`system/`) does not arm as a drop target,
   and the API refuses it if forced.
6. A deck can be created in `the-acme-deal/` — no 403.
7. The arrival is still badged `revision_kind='observation'` wherever it lands.

## 6. The one-line statement

**An arrival lands where the member put it and is recorded as an arrival by its
ledger badge, not by its address — so placement becomes one law, asked of one
predicate, by every verb that creates or receives a file.**

---

## Amendment — 2026-09-16: the `{principal}/` sublane goes; chat gets a shelf

§1 named the literal and D3 fixed only half of it. The destination became
member-chosen, but with **no** destination the resolver still composed
`inbound/uploads/{principal}/{slug}.{ext}` — and `principal` was the literal
`"operator"`, fixed at the one call site in `process_document`. The sublane
existed so that many principals sharing one intake lane could not collide. It
never had a second value.

**The receipt**: all **67** upload rows in production, across **2** accounts,
sit under the single segment `operator`. A sublane with one possible value
disambiguates nothing. Worse, it is address-shaped: it leaks ADR-373's
principal vocabulary into a path a member reads in Files, promising a
distinction the system does not make. D1 already ruled where an arrival is
recorded — the ledger badge `revision_kind='observation'` — so the address was
never carrying that fact anyway.

### A1 — the default lands in the lane itself

`resolve_upload_raw_path(slug, ext, destination=None)` returns
`/workspace/inbound/uploads/{slug}.{ext}`. The `principal` parameter is
**removed entirely**, not defaulted — an unused parameter is a shim, and there
is one intake shape (singular implementation).

**Attribution is untouched.** Who uploaded is `authored_by` on the revision
(still the operator seat), where it has always belonged. This amendment moves
nothing from the ledger to the path or back; it deletes a path segment that
was duplicating a ledger fact badly.

**No migration, no backfill.** The ~67 rows keep their
`inbound/uploads/operator/...` paths and keep resolving: they are ordinary
`workspace_files` rows under the same lane root, and chat history that
references an attachment BY PATH (`_mint_cas_url_for_path` in
`api/routes/lanes.py`) still finds them. Every rule that touches the lane —
the ADR-422 D2 organizability carve (`INBOUND_UPLOADS_ROOT`),
`is_upload_projection`, `_EMBED_ELIGIBLE_ROOTS` — keys on the
`inbound/uploads/` **prefix**, which does not move. No code parses the path by
segment depth (swept). The gate asserts both shapes stay lane-legal.

### A2 — a chat attachment is deixis, and gets its own shelf

A pasted screenshot or a dropped PDF in a conversation — *"why does this look
wrong"* — is conversational pointing, not authored workspace knowledge. Chat
attachments ride the **same door** as Files uploads
(`LanePanel.addFiles` → `api.documents.upload` → `POST /documents/upload`), so
they were landing beside the files a member deliberately brought in and
filling the curated arrivals folder with scraps.

They now pass `destination = 'inbound/uploads/chat'` (D3's mechanism, no new
one). It stays **under** `inbound/uploads/` deliberately: that prefix is what
the organizability carve, the projection-hiding rule and embed eligibility all
key on, so a chat attachment remains an ordinary, movable, searchable arrival
with its own shelf. D2 authorizes it like any other destination —
`resolve_access(auth, '/workspace/inbound/uploads/chat/x', 'create')` is
**allowed** (driven, not assumed). The attach-from-workspace bind path
(`attachWorkspaceFile`) is a reference to an existing file, not an upload, and
is untouched.

### A3 — retention stays NONE. Do not re-open this.

Recorded here so a future session does not re-litigate it: **there is no TTL,
GC, cron or deletion path for uploads, and none is to be added.**

- ADR-591 already deleted the retention GC. This amendment does not revive it.
- **ADR-623 depends on the bytes being durable.** A vanished image made the
  model answer as if it had seen a picture it never saw; the fix re-mints
  images from the durable path on replay (`api/routes/lanes.py`). Deleting an
  upload re-opens that defect directly.
- The measured cost does not justify the risk: **47 MB over 57 days** from two
  heavy development accounts — roughly **7 GB/year at 50 workspaces**, against
  a **100 GB** included Supabase Pro allowance.

Retention is an operator ruling (2026-09-16), not an oversight.

### Falsifiers (added to §5)

8. An upload with no destination lands at `/workspace/inbound/uploads/{slug}.{ext}` — no `operator/` segment anywhere in the path.
9. `resolve_upload_raw_path` accepts no `principal` parameter at all.
10. A pre-amendment row at `inbound/uploads/operator/q3.pdf` is still organizable, its projection still hidden, its path still resolvable in chat history.
11. A file attached in chat lands under `inbound/uploads/chat/`, and that destination is allowed by `resolve_access` for `create`.
12. The revision for every arrival, at any of these addresses, still carries `revision_kind='observation'` and an `authored_by` naming who uploaded.

**Gate**: `api/test_adr555_arrival_has_a_here.py` (39/39). The amendment's two
shape checks are proven RED against the pre-amendment sublane before green.
