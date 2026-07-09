# The Substrate as a Local-Disk OS: Binary-Native Revisions and the Storage Seam

> **Status**: Analysis / pressure-test (2026-07-09). Doc-first, receipts-backed. Feeds a keystone ADR ([ADR-427](../adr/ADR-427-binary-native-substrate-and-the-storage-seam.md)). No code rides this document.
> **Authors**: KVK, Claude
> **Driver**: the operator's vision — yarnnn must be architected so that, when the time is right, it can **fork/evolve into an on-premise, local-disk OS** where the authoritative substrate is an actual filesystem on the user's own machine (disk-is-truth, Postgres-as-index). The current cloud, text-only form must not foreclose that future.
> **Method**: three-way convergence test — the local-disk vision, [ADR-328](../adr/ADR-328-substrate-portability-invariant.md) (the portability invariant), and the [third-party-video-editor stress test](#) — cross-checked against live code @ main.

---

## 1. The one-paragraph finding

Three independent lines of inquiry — the local-disk-OS vision, the ADR-328 portability audit, and the "can a third party ship a video editor" stress test — **converge on the same wall**: binary assets live in Category 3 (an unversioned `content_url` pointer to a Supabase bucket), entirely outside the authoritative, content-addressed, attributed Category 1. Closing that one wall simultaneously (a) lets a third-party media app work, (b) resolves ADR-328's deliberately-open D8 binary-portability gap, and (c) makes the local-disk fork whole. **One keystone, three payoffs** — the signature of a real load-bearing decision. The keystone is a **content-addressed `StorageBackend` seam** that treats binary as a first-class Category-1 blob, with today's Postgres+bucket as its first driver and a local-disk driver as the second. Build the seam now (cloud driver); the fork becomes a driver swap, not a rewrite — exactly the operator's "storage-abstraction seam now, local later."

---

## 2. The pressure test: does "same architecture, two deployments" survive the fork?

**Verdict: TRUE for the moat (Category 1), by construction; a REBUILD for the cache (Category 2), by design; with exactly ONE hole (binary).**

The fork-survival question was already answered, column-by-column, in [ADR-328](../adr/ADR-328-substrate-portability-invariant.md) (PROPOSED 2026-06-08). This analysis re-verifies it against live code and extends it to the binary + local-disk target. The three-category sort is the fork's blueprint:

| Category | What | Fork behavior | Receipt |
|---|---|---|---|
| **1 — authored truth** | `content` (sha256 CAS in `workspace_blobs`) + the `workspace_file_versions` parent-pointer chain + `authored_by`/`message`/`created_at` | **Survives by construction** — content-addressed blobs + a parent-pointer DAG + attribution IS git's object model; deployment-agnostic | `authored_substrate.py:224` (sha256 CAS), `158_adr209:49` (chain) |
| **2 — reconstructable cache** | `embedding`, tsvector/pgvector indices, `size_bytes`, `head_version_id` | **Rebuilt, never migrated** — dropped on fork, re-derived from Category 1 (SQLite FTS + a local vector store on disk) | ADR-328 audit; `workspace.py:30-51` (embed is metadata-only, re-derivable) |
| **3 — unversioned sidecar** | `summary`, `tags`, `lifecycle`, `content_type`, `metadata`, **`content_url`** | Descriptors on the head row; **`content_url` is the portability gap** — a dangling pointer to a binary not in the export | ADR-328 D8; `112_workspace_content_url.sql` |

The most important fork-survival fact: **the DB-only features one would fear (search, embeddings) are correctly classified as CACHE, not truth** — so the local-disk fork loses no authoritative state by dropping Postgres; it rebuilds the index. This is not aspirational; it is how the code is already reasoned about (ADR-328 generalized the ADR-298 D2 `wake_queue`-is-transient-compute precedent to the embedding/index columns).

**The single gap that all three inquiries hit:** binary. ADR-328 flagged it (D8, left deliberately open "awaiting real pressure"). The video-editor stress test hit it from the app side (a `.mov` write has nowhere true to land). The local-disk vision hits it from the deployment side (you can't put "disk is truth" on a foundation where half the file types aren't on the versioned disk). **The pressure has arrived; D8 is now due.**

---

## 3. The two delegated technical decisions

The operator delegated these with the mandate: *durable, future-proof, scalable, canon-correct.* Both are made here from the audit receipts; both are ratified in the keystone ADR.

### Decision A — Binary content-addressing: **generalize the blob store to bytes-addressed, content-agnostic**

**Chosen: `workspace_blobs` becomes `sha256 → bytes` (text is just UTF-8 bytes); the driver decides where bytes physically live.**

The current store is `sha256 TEXT PRIMARY KEY, content TEXT NOT NULL` and the address is computed `content.encode("utf-8")` (`authored_substrate.py:224`). Text is *already* being hashed as bytes — the `TEXT` column is an implementation choice, not a semantic one. The decision:

- **The blob abstraction is `sha256(bytes) → bytes`.** Text blobs are the `utf-8` case. A `.mov` is the general case. One content-addressed model, no "text lane / binary lane" bifurcation at the *semantic* layer.
- **Physical storage is the driver's business** (Decision B's seam). The **cloud driver** MAY keep small text blobs inline in Postgres for FTS locality and put large/binary blobs in the object store keyed by hash — that is a *driver optimization*, invisible above the seam. The **local driver** puts every blob in a `.blobs/<sha[0:2]>/<sha>` directory — literally git's loose-object layout.
- **The revision chain is unchanged** — `workspace_file_versions.blob_sha` already references a hash; it does not care whether the hash addresses text or video.

Why this over "keep text in DB, binary by-hash in object store" (the two-lane alternative): the two-lane model puts the text/binary split at the *semantic* layer, which then leaks into every caller and every fork-driver ("is this file text or binary?"). Bytes-addressed pushes the split down to a *driver optimization* where it belongs — the moat mechanism (CAS + chain + attribution) is uniform across all file types, which is the durability and canon-correctness the mandate asks for. It is also the only option under which ADR-328 Category 1 stays a single, clean, portable thing.

**Blast radius: small and mechanical.** 43 `write_revision` callers, the majority one-shot scripts + probes; the live service callers pass text and are unaffected (text → `utf-8` bytes is transparent). Binary is *additive* — a new `content_bytes`/`content_ref` path alongside the existing string path, not a rewrite of the string path.

> **Cross-session refinement (2026-07-09):** the seam signature is **stream-first, not bytes-first** — `bytes` in the interface forecloses a 25 GB `.mov` (it must materialize in memory); the streaming/range form is the primitive, `bytes` a wrapper, on both read and write. And the seam's **wire shape is the git-lfs batch API** (pointer-in-tree + bytes-in-CAS + `POST /objects/batch` resolution) — so the cloud driver is an LFS batch server, the local driver is a real `git + git-lfs` repo, and third parties get an off-the-shelf spec instead of a proprietary blob API. Both are folded into [ADR-427](../adr/ADR-427-binary-native-substrate-and-the-storage-seam.md) D2. The bytes-addressed *semantic* decision below stands unchanged.

### Decision B — On-disk authoritative representation: **git-shaped, with literal-git (git + git-lfs) as the reference local driver**

**Chosen: Category 1 serializes to a git-object-shaped on-disk format; the first local-disk driver targets a real git repository as the reference implementation, with the working tree as native files.**

ADR-328 already named "Category 1 exports to git format" as the *falsifiability test* of the portability claim (THESIS Commitment 4). This decision makes the test the target:

- **The on-disk model is git's**: content-addressed loose objects (`.blobs/` = `.git/objects`), a parent-pointer history, attribution as author/message. yarnnn's chain already carries `authored_by` + `message` + `parent_version_id` + `created_at` — a one-to-one map onto git's commit author/message/parent/date.
- **The working tree is native files** — the operator's literal "local-disk OS" ask: on disk, `operation/foo.md` is a real file Finder/any-local-app can open; the moat metadata (revision chain, attribution, blob index) lives in a `.yarnnn/` sidecar directory (git's `.git/`), authoritative and walkable.
- **Reference driver = real git plumbing** where it fits, so the fork rides a proven, ubiquitous, battle-tested object store rather than re-implementing one.

**The honest divergence (this is the load-bearing nuance, not a footnote):** yarnnn's chain is **per-`(user_id, path)`** — each file has its *own* independent parent-pointer DAG — whereas a git commit is a **whole-tree snapshot**. This is confirmed at `authored_substrate.py:160-181` (the head-read query filters `.eq("path", path)`). So yarnnn's model is closer to **per-file version history** (Google-Docs-per-doc) than to git's tree-commit.

This does **not** break the git-shaped decision, but it dictates *how* the mapping works, and the ADR must specify it:
- **Blobs map trivially** — content-addressed bytes are identical in both models.
- **The per-file chain maps to git as a per-file commit lineage** — each yarnnn revision becomes a git commit that touches one path, with `authored_by`→author, `message`→message, `parent_version_id`→parent commit. A git log filtered to one path reproduces the yarnnn chain exactly. (Git supports this natively; `git log -- path` is the per-file view.)
- **What git ADDS for free and yarnnn does not currently have — a whole-tree atomic snapshot — is a GAIN, not a conflict.** The fork can offer tree-snapshots as a superset; the cloud form simply doesn't expose them today. No authoritative state is lost either direction.
- **The single-writer-per-path invariant (ADR-286) + revert-as-write (no merge/CRDT, ADR-406/378) is PRESERVED and is in fact *why* the per-file model is coherent** — yarnnn deliberately has no cross-file atomic transaction to represent, so the absence of tree-commits in the cloud form is by design, not a gap.

Why git-shaped over "files + a custom sidecar manifest": a hand-rolled manifest re-implements exactly what git's object model gives for free (content-addressing, integrity, history walk, dedup), and every re-implementation is a place the portability claim can rot. Git is the most-proven content-addressed history on earth and is *already* named as the ADR-328 export target. Canon-correctness points at git; durability points at git; the only cost is honoring the per-file→per-path-commit mapping, which is specified above.

---

## 4. What this does NOT decide (deferred to the ADR / build)

- **Streaming / range reads / resumable upload** for large binary — the I/O physics a video app needs (stress-test §5 item 5). Named, deferred to a driver-capability, not a Category-1 concern.
- **The app-principal class + app-registration flow** (stress-test §5 item 2) — a grant-model extension, orthogonal to the storage seam; its own ADR.
- **The public app ABI / ADR-413 ratification** (stress-test §5 item 3) — the external contract; rides after the seam exists.
- **When to actually build the local driver.** The keystone builds the *seam* + the cloud driver now. The local driver is the fork, built when the time is right (operator's framing). The seam is the down-payment that keeps the fork cheap.
- **First-party reference media app** (stress-test §5 item 6) — the Preview-equivalent that dogfoods the seam; follows the keystone.

---

## 5. The keystone, stated

> **Generalize the authored substrate's blob layer from text-addressed to bytes-addressed behind a `StorageBackend` seam, so binary becomes a first-class Category-1 citizen (content-addressed, attributed, revisioned, revertible, portable) — with today's Postgres+object-store as the first driver and a git-shaped local-disk driver as the reserved second.**

This is the single change that turns yarnnn from "an OS for text-shaped work" into "an OS for all work," closes ADR-328 D8, and makes the local-disk-OS fork a driver swap. It is the correct next frontier for the substrate — more fundamental, and more defensible, than any surface or chat investment. Proposed as **[ADR-427](../adr/ADR-427-binary-native-substrate-and-the-storage-seam.md)**.
