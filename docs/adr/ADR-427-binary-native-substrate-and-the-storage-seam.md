# ADR-427: Binary-Native Substrate and the Storage Seam — the Substrate Becomes an OS for All Work

> **Status**: **Proposed** (2026-07-09) — doc-first, revised same day after a cross-session review. No code rides this ADR; the build is phased in §9 and each phase is its own commit under CHANGELOG discipline. Drafted by KVK + Claude. **This ADR resolves [ADR-328](ADR-328-substrate-portability-invariant.md) D8** (the deliberately-open binary-portability gap) and lands the keystone the [local-disk-OS pressure test](../analysis/substrate-as-local-disk-os-binary-native-and-the-storage-seam-2026-07-09.md) identified.
> **Revision (2026-07-09, cross-session review)**: a parallel discourse (macOS OS-primitives framing + a landscape scan of git-lfs / MCP Apps / RFC 9396 / OpenTimelineIO / Patchwork) surfaced foreclosures that were free to fix pre-Phase-1 and expensive after. Landed: **stream-first seam** (D2 — `bytes` no longer forecloses a 25 GB `.mov`); **the wire shape IS the git-lfs batch API** (D2/D3 — a published spec, not a proprietary blob API); **`content_url` is a minted capability, not a stored column** (D4); **type is derived, never stored** (new D5); **read-side NULL blast radius** gated (§8); **§5a gains its strongest leg** (semantic merge is the app's job) + the declined Patchwork counter-thesis. The strategic note (§11) records that the OS framing does NOT change the external lead.

> **The four-primitive frame (the review's lens, adopted).** macOS enables a third-party Final Cut with exactly four primitives and no more: **(1) byte-range-addressable file identity**; **(2) an open, declarative type system with a conformance DAG** (Apple owns `public.movie`; Adobe owns `.prproj`); **(3) a capability model** — the powerbox: the user's file-pick IS the grant (security-scoped, object-scoped, expiring); **(4) an association table that LAUNCHES a process, never embeds a component.** No composition contract, no widget ABI, no project format, no merge story — *that absence is the platform.* yarnnn adds a **fifth primitive no OS has: the attributed revision.** This ADR builds primitive (1)'s store — and its job is to not accidentally foreclose (1)'s I/O, (2), or (3). Primitives (2)–(4) + the app-principal are named here and land in their own ADRs (§9 phase 5); *the only place novelty budget is spent is primitive #5.*
> **Date**: 2026-07-09
> **Dimension**: **Substrate** (Axiom 1 — what persists, and in what representation) primary; **Channel** (Axiom 6 — the deployment surface: cloud vs local disk) secondary.
> **Derivation**: [substrate-as-local-disk-os-binary-native-and-the-storage-seam-2026-07-09.md](../analysis/substrate-as-local-disk-os-binary-native-and-the-storage-seam-2026-07-09.md) — the three-way convergence (local-disk vision + ADR-328 + video-editor stress test).
> **Relates to**: ADR-209 (Authored Substrate — the blob + revision chain this generalizes), ADR-328 (Portability Invariant — D8 resolved here; the three-category sort is the design basis), ADR-286 (single-writer-per-path — preserved and load-bearing), ADR-406 (stale-parent linearity — extended to binary), ADR-378 (no merge/CRDT — reaffirmed), ADR-395 (upload intake / model-consumable projection — the derived-text projection stays, now alongside a versioned binary), ADR-222 (the literal OS framing this makes true for binary), ADR-417 (generation is rented — the binary that returns now has a home), ADR-373 (workspace-keyed substrate — the blob store is workspace-scoped correctly).
> **Amends**: ADR-209 (the blob layer is re-specified from text-addressed to bytes-addressed behind a driver seam; the revision chain is unchanged), ADR-328 (Category 1 now includes binary; D8 resolved; the git-export test becomes the local-driver target).

---

## 1. Context — the wall three inquiries hit

Three independent lines converge on one gap (the derivation doc has the full receipts):

1. **The local-disk-OS vision** (operator, 2026-07-09): yarnnn must be architected so it can fork/evolve into an **on-premise, local-disk OS** — authoritative substrate = an actual filesystem on the user's machine, Postgres demoted to a derived index. The current cloud, text-only form must not foreclose it. Chosen shape: **storage-abstraction seam now, local driver later; disk is truth.**
2. **[ADR-328](ADR-328-substrate-portability-invariant.md)** already proved the fork mostly survives — Category 1 (authored truth: `content` via sha256 CAS + the revision chain) is portable *by construction* (it is git's object model); Category 2 (embeddings, indices) is reconstructable cache, rebuilt not migrated. But ADR-328 **left D8 deliberately open**: binary assets (`content_url`) live in Category 3, a dangling pointer to a Supabase bucket, **outside** the portable Category 1.
3. **The third-party-video-editor stress test** (2026-07-09) hit the same wall from the app side: a `.mov` write has nowhere true to land — the moat mechanism (attribution, `trace`, revert, CAS, ADR-406 linearity) is **text-only**, and binary is a 25 MB pdf/docx sidelane referenced by an un-versioned `content_url`.

**Same wall, three directions. The pressure ADR-328 D8 waited for has arrived.**

The strategic frame (ESSENCE v15 §The Moat): the moat is *the attributed settlement layer for work* — "nothing reaches durability except as an attributed revision through the one invocation contract." Today that is true only for text. **A moat that covers half the file types is half a moat.**

## 2. The one-sentence decision

**Generalize the authored substrate's blob layer from text-addressed to bytes-addressed behind a `StorageBackend` seam, so binary becomes a first-class Category-1 citizen — content-addressed, attributed, revisioned, revertible, and portable — with today's Postgres+object-store as the first driver and a git-shaped local-disk driver as the reserved second.**

One change, three payoffs: (a) a third-party media app can write a versioned `.mov`; (b) ADR-328 D8 closes; (c) the local-disk fork becomes a driver swap, not a rewrite.

## 3. D1 — The blob layer is bytes-addressed, content-agnostic

The current store is `workspace_blobs(sha256 TEXT PK, content TEXT)` addressed by `content.encode("utf-8")` (`authored_substrate.py:224`). **Text is already hashed as bytes** — the `TEXT` column is an implementation choice, not a semantic one.

- **The blob abstraction becomes `sha256(bytes) → bytes`.** Text blobs are the `utf-8` case; a `.mov` is the general case. **One content-addressed model — no "text lane / binary lane" split at the semantic layer.**
- **Physical placement is the driver's business** (D2). The cloud driver MAY keep small text blobs inline in Postgres (FTS locality) and put large/binary blobs in the object store keyed by hash — a *driver optimization*, invisible above the seam. The local driver puts every blob in `.blobs/<sha[0:2]>/<sha>` — git's loose-object layout.
- **The revision chain is UNCHANGED.** `workspace_file_versions.blob_sha` already references a hash; it does not care whether the hash addresses text or video. Attribution (`authored_by` + `message`), parent-pointers, and the ADR-406 linearity guard apply to a binary revision identically.

**Why bytes-addressed over a two-lane (text-in-DB / binary-in-store) split:** the two-lane model puts the text/binary distinction at the *semantic* layer, where it leaks into every caller and every fork-driver. Bytes-addressed pushes the distinction down to a driver optimization where it belongs; the moat mechanism stays uniform across all file types. It is the only option under which ADR-328 Category 1 remains a single, clean, portable thing.

## 4. D2 — The `StorageBackend` seam is STREAM-FIRST, and its wire shape IS the git-lfs batch API

All blob physical I/O routes through one interface. `write_revision()` and the read path call the seam, never a concrete store. **Two decisions the cross-session review made load-bearing, and both are free only at Phase 1 (declared a "pure refactor"):**

### 4a. Stream is the primitive; `bytes` is the convenience wrapper (correction A)

A `bytes`-in/`bytes`-out signature forces a 25 GB `.mov` to materialize in Python memory to satisfy the interface — foreclosing streaming at the type level, in the exact refactor where the signature costs nothing. **Inverted:** the streaming form is the primitive on BOTH read and write; `bytes` is a thin wrapper for the small-text common case.

```
StorageBackend (the seam — the only code that knows WHERE bytes live)
  # primitives — range/stream, both directions
  open_read_stream(sha, range: Optional[ByteRange] = None) -> AsyncByteStream
  open_write_stream() -> ResumableUpload      # multipart/resumable; returns sha on finalize
  has_blob(sha) -> bool
  # convenience wrappers over the primitives (small-text common case)
  get_blob(sha) -> bytes                       # == read full range
  put_blob(data: bytes) -> str                 # == write stream, one chunk; returns sha
```

This is physics, not preference (the review's receipt): the control plane and the data plane are structurally different protocols. MCP's streamable-http hard-caps messages at 4 MB (python-sdk #1012), has no range requests in the spec, and base64-encodes binary through JSON (+33% overhead). A blob data plane cannot ride the control-plane transport; the seam must express range/resumable from birth. **The interface lands in Phase 1; the driver's streaming *implementation* may still land in Phase 3** — but the signature is not allowed to assume full-materialization.

### 4b. The wire shape is the git-lfs batch API (correction B)

D3 commits to a git-shaped on-disk form and D4 makes `blob_sha` authoritative with a resolved-at-read serving URL. **That is exactly [git-lfs](https://github.com/git-lfs/git-lfs/blob/main/docs/api/batch.md): a pointer in the tree, bytes in a content-addressed store, resolved through the batch API** (`POST /objects/batch` → per-object actions with `href` + `expires_at`). Plain git handles binary badly; *git + git-lfs* is the shape D3 already wants — so the seam adopts the LFS batch API as its wire shape, buying three things at zero cost:

- **`LocalDiskBackend` becomes a real `git + git-lfs` repo**, not a bespoke `.yarnnn/` sidecar format we invent and maintain.
- **`PostgresObjectStoreBackend` becomes an LFS batch server** (presigned URLs with expiry — which it nearly is already; see D4).
- **Any third-party app gets a published spec with off-the-shelf clients in every language**, instead of a yarnnn-proprietary blob API. This strengthens the ADR-328 export test from "exports to git format" to **"IS a git+lfs repo."**

### 4c. The drivers

- **Driver 1 — `PostgresObjectStoreBackend` (cloud, built Phase 1–2).** An LFS batch server: text/small blobs inline in `workspace_blobs.content`; large/binary blobs in the Supabase Storage bucket keyed by sha256, served via presigned range-capable URLs (D4). Refactor of today's behavior behind the interface — the current `_upsert_blob` becomes this driver's write path.
- **Driver 2 — `LocalDiskBackend` (the fork, reserved — NOT built here).** A `git + git-lfs` working tree: native files on disk, blobs in the LFS store, the revision chain + attribution as git history (D3). **The seam is the whole point: the fork is a driver + a wire format we didn't invent, not a rewrite.**

`write_revision`'s four-step sequence (sha → upsert blob → read head → insert revision + advance head) is unchanged; step 1's "upsert blob" becomes a seam call. The ~43 write callers are untouched (text → utf-8 bytes is transparent); binary is an *additive* stream/`content_ref` path alongside the existing string `content`.

## 5. D3 — The on-disk authoritative form is git-shaped

ADR-328 named "Category 1 exports to git format" as the *falsifiability test* of the portability claim. This ADR makes the test the local-driver **target**:

- **Content-addressed loose objects** (`.blobs/` ≈ `.git/objects`), a **parent-pointer history**, **attribution as author/message** — yarnnn's chain already carries `authored_by`/`message`/`parent_version_id`/`created_at`, a 1:1 map onto git's commit author/message/parent/date.
- **The working tree is native files** (the operator's literal "local-disk OS" ask): on disk `operation/foo.md` is a real file any local app opens; the moat metadata lives in `.yarnnn/` (git's `.git/`), authoritative and walkable.
- **Reference driver uses real git plumbing** where it fits — the fork rides the most-proven content-addressed history on earth rather than re-implementing one.

### 5a. The load-bearing divergence: per-path chain vs git's tree-commit

yarnnn's chain is **per-`(user_id, path)`** — each file has its own independent parent-pointer DAG (confirmed `authored_substrate.py:160-181`, the head-read filters `.eq("path", path)`). A git commit is a **whole-tree snapshot**. This is closer to **per-file version history** (Google-Docs-per-doc) than to git's tree-commit. The mapping (which the local driver MUST implement, specified so it is not hand-waved):

- **Blobs map trivially** — content-addressed bytes are identical in both models.
- **Each yarnnn revision → a git commit touching one path** (`authored_by`→author, `message`→message, `parent_version_id`→parent). `git log -- <path>` reproduces the yarnnn per-file chain exactly (git supports the per-file view natively).
- **Git's whole-tree atomic snapshot is a GAIN the fork MAY expose as a superset — not a conflict.** The cloud form simply doesn't have tree-commits today; no authoritative state is lost either direction.
- **This is coherent *because of* ADR-286 (single-writer-per-path) + ADR-378/406 (no merge/CRDT; revert-as-write).** yarnnn deliberately has no cross-file atomic transaction to represent — so the absence of tree-commits in the cloud form is by design, not a gap. The per-file model and the no-merge invariant are the same decision.

### 5b. Why no-merge is correct: semantic merge is the application's job (the strongest leg)

The per-file chain is coherent not only because yarnnn has no cross-file transaction to represent, but because **semantic merge belongs to the application, and the kernel categorically cannot do it.** A video editor knows how to rebase a timeline; a deck editor knows how to reconcile two slide edits; the kernel knows neither and must not pretend to. The division of labor:

- **The kernel provides optimistic concurrency** — the ADR-406 stale-parent 409 is its *complete* contribution. The editor reads a blob at a hash, works, commits against the parent it read, and on a 409 resolves *in its own domain*.
- **The application provides semantic merge.** This is exactly how Postgres works (it hands you a serialization failure, not a merged row) and how git works (it hands you both sides of a binary conflict and gets out of the way).
- **This also disposes of the "hours-long editing session" objection** — it is *already answered by ADR-406*: the editor never holds the file open across the session; it reads a hash, works locally, and commits against that parent. A 409 means someone else committed meanwhile, and the editor rebases. No lock, no held transaction, no kernel merge.

**The live counter-thesis, named and explicitly declined:** [Ink & Switch's Patchwork / Automerge](https://www.inkandswitch.com/patchwork/) (active through 2026 — "universal version control" via CRDT documents, code *and* data merged automatically at the substrate). It is a real, serious alternative that pushes merge *down* into the kernel. yarnnn declines it deliberately: a substrate-level CRDT merge (a) cannot know the application's semantics (a timeline rebase is not a text-CRDT merge), (b) contradicts ADR-378's no-CRDT invariant and ADR-286's single-writer discipline, and (c) trades the legible, attributable, revertible revision chain for an emergent merged state no one authored. yarnnn's bet is the opposite: *the kernel stays dumb about merge on purpose, so the application stays in control and the attribution stays honest.* A reader will raise Patchwork; declining it explicitly is stronger than ignoring it.

**Why git-shaped over a custom sidecar manifest:** a hand-rolled manifest re-implements what git's object model gives free (content-addressing, integrity, history walk, dedup); every re-implementation is a place the portability claim rots. Canon-correctness (ADR-328's own export test), durability, and scale all point at git; the only cost is honoring the per-file→per-path-commit mapping above.

## 6. D4 — Category re-sort (amends ADR-328)

- **Binary content moves Category 3 → Category 1.** A binary asset is now a content-addressed blob in the revision chain, attributed and portable — no longer a dangling `content_url` sidecar. The authoritative reference is `blob_sha`. **ADR-328 D8 is resolved.**
- **`content_url` is DELETED as a column — it is a minted capability, not stored state (correction C).** A presigned, object-scoped, expiring URL is a *security-scoped bookmark* — the powerbox primitive (macOS primitive #3). **A cached capability is a leaked capability**, so it must not survive as a column in *any* category (it is not Category-2 cache — it is not state at all). It becomes a **per-request, per-principal, TTL'd response field**, minted at read time from `(blob_sha, principal, active grant)` by the LFS-batch serving path (D2b). Its authority, expiry, and object-scope are computed each request; nothing durable holds a live URL.
  - *Blast radius the retirement carries (enumerated — 11 non-test files):* `routes/{documents,workspace,agents}.py`, `services/{workspace,authored_substrate,documents,delivery}.py`, `services/primitives/embed.py`, `services/compose/{task_html,assembly,manifest}.py`. Each read site that today reads a stored `content_url` must instead mint one from `blob_sha` at request time. This is Phase-2/3 work with a named surface, not an incidental column drop.
  - *Forward pointer (the app-principal ADR):* mint these under **OAuth 2.1 + [RFC 9396 Rich Authorization Requests](https://datatracker.ietf.org/doc/rfc9396/)** — RAR exists precisely to express "this client, these objects, these actions," which is the powerbox shape. yarnnn already runs OAuth 2.1 for MCP; this is a scope-shaped extension, not a new system. (If offline-verifiable, delegatable grants matter for the local-disk fork, [UCAN](https://ucan.xyz/) is the philosophically-aligned alternative — flagged for the app-principal ADR, not decided here.)
- **`workspace_files.content` (the TEXT denorm) is explicitly Category 2 — cache (correction E).** The ADR-209 Phase-5 denormalized `content` column (retained for FTS/embedding locality) is a *second place bytes live above the seam*, and it is TEXT — it goes NULL for binary. Classifying it as Category-2 cache makes the text-only assumption explicit and droppable, rather than a silent invariant binary breaks. The authoritative content is always the blob via `blob_sha`; `content` is a rebuildable text-only projection.
- **The derived-text projection (ADR-395) stays** — a video/PDF still gets a text projection for search/model-consumption, now as a *sibling Category-1 file* citing the binary blob (ADR-376 ledger-intake: the binary is the observation, the projection is the derived citing act). The binary is no longer *replaced* by its projection; both are versioned.
- **Category 2 (embeddings, indices, the `content` denorm) and the rest of Category 3 (summary/tags/lifecycle/metadata) are otherwise unchanged.** (`content_type` leaves Category 3 — see D5.)

## 6b. D5 — Type is DERIVED, never stored (correction D — the type-system decision the ADR was missing)

The original draft had no type-system decision, and `content_type` was misfiled. Receipt: `services/workspace.py:33` → `content_type: str = "text/markdown"` — **caller-supplied, defaulted, unversioned, sitting in Category 3 next to `summary` and `tags`.** But **type is what determines which app opens the file** (macOS primitive #2). If type is a descriptor a caller happens to pass, then (i) no third-party app can reliably resolve what it's looking at, and (ii) the local-disk fork exports files whose types don't survive.

**Decision: type is DERIVED, never stored** — from path extension + magic bytes + a **declared conformance DAG** (the UTI model; [shared-mime-info](https://specifications.freedesktop.org/shared-mime-info-spec/shared-mime-info-spec-latest.html) is the reference data shape). Derived ⇒ **free, portable, and Category-1-by-construction** (it is a pure function of the blob + path, both already Category 1). `content_type` leaves Category 3 — it is not stored state at all.

**The load-bearing corollary (the platform boundary):** yarnnn declares the **MEDIA types it owns** (`public.movie`, `public.image`, `application/pdf`) and **MUST NOT declare the PROJECT / timeline format.** A third-party editor brings its own type; it declares conformance to `application/json` and *every JSON viewer still opens it* — exactly how Adobe owns `.prproj` on macOS while it still conforms to a public base type. This is the primitive-#2 discipline: **yarnnn owns the base media types; it never owns an app's project format.**

**Why this cleaves correctly (the [OpenTimelineIO](https://opentimeline.io/) lesson):** a video is not a special case — it is the *union of the two ordinary cases*. The **structured timeline** is small, text-shaped, and belongs in the revision chain (Category 1 text); the **media** is immutable, huge, and belongs in the CAS (Category 1 blob). The type system + the blob store together already handle video *without a video-specific concept* — which is the proof the four primitives are sufficient.

This also **corrects Phase 3's "MIME allowlist" line**, which presumed stored types: with type derived, the "allowlist" is a *conformance-DAG* question (which base types does yarnnn declare?), not a stored-string gate.

## 7. What this ADR does NOT do

- **Does not build the local-disk driver** — Driver 2 is reserved; the fork is built when the time is right (operator's framing). This ADR builds the *seam* + the cloud driver, the down-payment that keeps the fork cheap.
- **Does not add streaming / range reads / resumable upload IMPLEMENTATION** — the *interface* is stream-first from Phase 1 (D2a, non-negotiable); the driver's streaming *implementation* is deferred to Phase 3. The signature must not assume full-materialization.
- **Does not add the app-principal class or app-registration flow** — the grant-model extension a third-party app needs (stress-test §5.2) is orthogonal; its own ADR.
- **Does not ratify ADR-413 / build a public app ABI** — the external contract rides after the seam exists.
- **Does not build a first-party media app** — the Preview-equivalent that dogfoods the seam follows the keystone.
- **Does not change the revision chain, single-writer-per-path, or the no-merge invariant** (ADR-286/378/406 preserved and reaffirmed as *why* §5a is coherent).
- **Does not raise the upload size cap or add media MIME types by itself** — those are Phase-3 consequences of the seam, not the seam.

## 8. The read-side blast radius (correction E — undercounted in the draft)

The original §8 said "43 `write_revision` callers, text path transparent." **True for WRITES. False for READS.** `workspace_files.content` is `TEXT NOT NULL DEFAULT ''` (migration `100:26`) — it **goes NULL/empty for binary** — and there are **52 `.select(...content...)` sites across 30+ files** (`working_memory`, `compose/*`, `embed`, `freddie_envelope`, `recurrence`, `review_policy`, `wake`, `lane_runner`, …). Phase 2's gate ("a binary revision round-trips through `trace` + revert") **will not catch a null-deref** in any of those readers.

**Phase-2 gate added:** every `.content` reader either (a) handles the None/empty-for-binary case, or (b) is explicitly *text-only-by-contract* and asserts `content_type` conforms to `text/*` (D5-derived) before reading. A CI ratchet enumerates `.content` read sites and requires each to be classified. This is the read-side twin of the write-path chokepoint — the text-only assumption is made explicit and guarded, not left to break silently on the first binary file.

## 9. Consequences

- **The moat covers all file types.** `trace`, attribution, revert, and correction-compounding apply to a video, an image, a dataset — not just `.md`. "The system of record where human and AI work settles" becomes literally true for every kind of work.
- **The local-disk fork is de-risked to a driver.** The single largest architectural risk to the on-premise vision (a cloud-Postgres-coupled substrate) is removed at the seam, before the coupling deepens — and the fork inherits a *published wire format* (git-lfs), not a bespoke one.
- **Third-party and first-party media apps share one contract** — the same `StorageBackend` (LFS-batch-shaped) + revision chain hosts yarnnn's reference viewer and someone else's editor.
- **Cost:** the seam is a refactor of the existing blob path (low write-risk — 43 callers, text path transparent) + a genuinely new binary-blob path + the read-side classification pass (§8). The git-mapping, stream-first, and type-derivation disciplines are design-time cost paid in this ADR, not runtime cost.

## 10. Sequencing (phased; each phase its own commit)

1. **The seam (stream-first, LFS-shaped) + cloud driver refactor** — introduce `StorageBackend` with the stream-first signature (D2a) and the git-lfs batch wire shape (D2b); port `_upsert_blob`/blob-read behind it as `PostgresObjectStoreBackend`. **The range/stream *interface* lands here** (driver impl may be a stub returning the full range); text behavior byte-identical. Gate: existing substrate tests green + a seam-contract test asserting the signature is stream-first. *No behavior change — pure refactor.*
2. **Binary as a Category-1 blob + read-side classification** — `write_revision` accepts a binary stream; binary blobs get parent-pointers + attribution + ADR-406 linearity; `blob_sha` is the authoritative binary reference; `content_url` becomes a minted response field (D4); `workspace_files.content` classified Category-2 (D4). **The §8 `.content`-reader classification pass + ratchet.** `content_type` derivation (D5) lands here. Gate: a binary revision round-trips through `trace` + revert AND every `.content` reader is classified.
3. **Media intake + serving** — replace the upload cap + stored-MIME gate (`documents.py:77-78`) with a conformance-DAG check (D5) for versioned binary; implement the driver's range-read/resumable-write (the D2a impl deferred from Phase 1); serving mints per-request LFS-batch URLs. Gate: a real image/video uploads, versions, streams, and serves.
4. **Doc cascade** — ADR-328 status → "D8 resolved by ADR-427"; ESSENCE §The Moat gains "every file type, not just text"; FOUNDATIONS Axiom 1 storage-agnostic clause points at the seam; GLOSSARY gains "StorageBackend / bytes-addressed blob / Category-1 binary / derived-type / minted capability."
5. **Reserved (the fork + the other primitives — each its own ADR when the time is right):**
   - `LocalDiskBackend` = a real **`git + git-lfs`** working tree (not a bespoke `.yarnnn/`).
   - **The app-principal grant class + public app ABI** — *forward pointer (correction I): none of the four macOS primitives needs an invented protocol.* Type = IANA media types + a UTI-style conformance DAG (D5). Data plane = the git-lfs batch API (D2b). Powerbox = OAuth 2.1 + RFC 9396 RAR (or UCAN if offline/delegatable grants matter for the fork). Association = launch-by-redirect carrying a scoped grant (OAuth authorization-code as `exec()`); on the web, `registerProtocolHandler()` + the PWA File Handling API (`file_handlers` manifest key) are LaunchServices-for-the-web (Chromium-only, standardization bumpy — verify current status). Concurrency = expose ADR-406 as HTTP `ETag`/`If-Match` and every HTTP client understands the model for free. **The only place novelty budget is spent is primitive #5, the attributed revision — everything else is a boring decade-old standard.**
   - **First-party reference apps** — *forward pointer (correction J): the discipline that makes first-party apps legitimate rather than platform-killing is that they are built on EXACTLY the public contract, zero private API* (Preview is legitimate because it uses the same association table, type declarations, and sandbox any third party would). **CI-enforceable test (a ratchet, which this repo already runs): can your own viewer be deleted and replaced by a third party's, with no kernel change? Yes → OS. No → product.** Build them as the **forcing function** for the ABI — you cannot design the type system, grant granularity, or range API in the abstract. **Correct first pair is NOT video:** (i) a *read-only viewer of a type you don't author* (PDF/image) — exercises type declaration + blob range read + no write path; (ii) an *editor of a structured file* (markdown, or a JSON timeline) — exercises revision write + CAS + 409 + attribution + `trace`.

## 11. Strategic note — the OS framing does NOT change the external lead (correction H)

The open fork this discourse flagged — *"does yarnnn-as-OS become the product's external lead, contradicting ESSENCE v15 / ADR-380 §5's host-elsewhere posture?"* — **dissolves once the capability model is real, and the answer is: keep the current lead.**

If the data plane is LFS-shaped, the grant is RAR-shaped, and the association *launches* rather than *embeds*, then apps run **anywhere** — and the substrate is still where work settles. Two facts from the landscape scan reinforce this:

- **MCP Apps shipped 2026-01-26** as the first official MCP extension (`ui://` + `_meta.ui.resourceUri` + sandboxed iframe + JSON-RPC/postMessage), merging MCP-UI and OpenAI's Apps SDK into one standard, live in Claude, ChatGPT, VS Code, and Goose. Host-elsewhere just got **cheaper and cross-client** — this *reinforces* ESSENCE v15's lead, it does not contradict it.
- **But MCP Apps is the wrong shape for hosting a third-party editor *into* yarnnn.** There, yarnnn is the *server* and Anthropic/OpenAI/Microsoft are the *hosts* — a component ABI owned by the hosts (the OLE/OpenDoc/Bonobo/KParts lineage, all of which died). It cannot be how a third party ships a video editor into yarnnn; the four primitives (launch, not embed) are. The two coexist: MCP Apps carries yarnnn's *reach into other hosts*; the primitives carry *other apps' reach into yarnnn's substrate.*

**Therefore: yarnnn-as-OS is an INTERNAL architecture truth, not an external positioning change.** "Portable memory that follows you" and "the OS where work settles" are the same claim from the app side and the substrate side. **Keep ESSENCE v15's lead; ship the seam.**

*Secondary consequence (a line for ADR-372/379): MCP Apps standardized `ui://`, so the per-host widget gating in the ADR-379 host-profiles registry may now be collapsible — check whether that gating exists only because ChatGPT and Claude diverged, since that reason has expired.*

## 12. The one-line statement

**The substrate stops being an OS for text-shaped work and becomes an OS for all work — by making binary a first-class content-addressed, attributed revision behind a stream-first, git-lfs-shaped storage seam whose second driver is the local disk, with type derived and capabilities minted, never stored.**
