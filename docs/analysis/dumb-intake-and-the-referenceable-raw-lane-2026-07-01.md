# Dumb intake and the referenceable raw lane: what "raw in, derive downstream" actually costs

**Date**: 2026-07-01
**Hat**: B (external developer of the system — analysis + a candidate ADR spec for ratification). No canon edit and no code change in this doc; it is the discourse base the conforming ADR would cite.
**Status**: Proposed direction for operator (KVK) ratification.
**Spine**: the **ledger-intake axiom** ([ADR-376](../adr/ADR-376-ledger-intake-raw-observation-vs-derived-substrate.md) / FOUNDATIONS DP32) + the **perception/capture pipeline** ([ADR-393](../adr/ADR-393-the-perception-capture-pipeline.md)). This doc supplies the missing conformance for **one transport the axiom names but the code never fixed: human upload.**
**Origin**: KVK, after uploading a PDF and seeing it land as a derived `document.md` (extracted text) rather than the raw file: *"I thought our approach to the file system — the upload and context-in, especially intake — should be the dumbest, most straightforward way possible; processing happens downstream, either by explicit YARNNN internally OR host LLM for MCPs. This means the filesystem substrate needed to handle different file types / blobs?"* And, decisively: *"the pure dumb path thus needs to ensure the downstream impact. Whatever is landed in inbound can and should be easily referenceable via an MCP to other connectors or at large (think Dropbox). Else we need to discourse."*
**Receipts**: all claims verified against the live repo 2026-07-01 (`documents.py`, `mcp_composition.py`, `primitives/workspace.py`, `wake.py`, `embeddings.py`, `routes/documents.py`). Cited inline.

---

## 0. The one-sentence finding

> Making upload intake "dumb" (land the raw blob, defer extraction) is **correct per the ratified axiom** — but the axiom silently assumes a **derive step and a serving layer** that, for uploads, **do not exist**. Ship dumb-intake alone and the file becomes a **write-only orphan** (not searchable, not recallable, not referenceable over MCP). So the real unit of work is not "stop extracting"; it is **three coordinated pieces**, and the operator's Dropbox-referenceability requirement is the hardest of them.

The dullness KVK wants is right. The cost is that the dullness has to be paid for *downstream* — and downstream is currently empty for this transport.

---

## 1. Where the canon and the code diverge

### What the canon says (ratified)

**ADR-376 / DP32** — *"Every contribution to the substrate enters as an attributed raw observation; what the workspace makes of it is a separate, attributed, derived act; the raw is never rewritten and the derived always cites its source — `retain + attribute + cite`, system-wide across every context-in transport."*

**ADR-393** — capture is *"the retain-and-attribute half; derive stays a separate act"*; intake is a mechanical, zero-LLM lane, and processing is a downstream, separately-attributed act.

Both point exactly where KVK points: **intake is dumb; derivation is downstream.**

### What the code does (upload)

`api/services/documents.py::_process_single_upload` does **eager extraction at intake**:

- [documents.py:176](../../api/services/documents.py#L176) — `text, unit_count = await extract_text(file_content, file_type)` (pypdf2 / docx / txt) runs **at upload time**.
- [documents.py:198–207](../../api/services/documents.py#L198) — `write_revision(...)` writes the **extracted text** to `/workspace/uploads/{slug}.md` with a YAML frontmatter header (`original_filename`, `mime_type`, `storage_path`, `extraction_method`, …).
- The **raw binary IS stored** — but only in Supabase storage (`storage_path`), referenced from the `.md`'s frontmatter. It is **not** a first-class substrate revision.

This is governed by [ADR-249](../adr/ADR-249-two-intent-file-handling.md) (Two-Intent File Handling, Implemented 2026-05-06), which **predates DP32** and never engages the intake axiom — it solves *ephemeral vs persistent intent*, not *raw vs derived*. So the upload path isn't defying a decision; it's just **older than the axiom that now governs it.**

### The asymmetry, stated plainly

| Transport | Raw lands as… | Derived lands as… | Conforms to DP32? |
|---|---|---|---|
| **MCP `remember`** | `inbound/mcp/{client}/{slug}.md` — immutable, `authored_by: yarnnn:mcp:{client}` ([mcp_composition.py:308,352](../../api/services/mcp_composition.py#L308)) | seat derives into `operation/`, citing via `derived_from:` ([mcp_composition.py:403–417](../../api/services/mcp_composition.py#L403)) | ✅ (fixed by ADR-368/376) |
| **Human upload** | *nothing on-substrate* — extracted text IS the substrate file; the binary is orphaned in storage | *(no derive step — the extracted `.md` is the terminal artifact)* | ❌ conflates: derived-at-intake, raw never a revision |

ADR-376 §3's audit table *lists uploads as ✅ conformant* — but read the fine print: it describes uploads as *"`uploads/{file}` — immutable"* (**the raw file is the substrate object**). That is **not what the code does.** The doc described the *intended* raw lane; the code extracts. **The ✅ is aspirational, not actual.** This doc closes that gap.

---

## 2. Why "just stop extracting" breaks everything (the KVK downstream-impact test)

KVK's guard — *"whatever is landed in inbound can and should be easily referenceable"* — is the correct gate, and the code fails it. If upload lands a raw PDF blob (via `content_url`) with empty `content`, here is the exact reachability, verified:

### (a) Invisible to MCP callers / other connectors
The MCP read surface (`recall` / `trace` / `QueryKnowledge`) reads the **`content` column only**. `QueryKnowledge` returns `content[:500]` previews ([primitives/workspace.py] QueryKnowledge). **No MCP tool references `content_url`** — there is no "give me the blob / a signed URL" tool. A blob with empty `content` is **unreferenceable over MCP.** → *This is the exact thing KVK requires and it does not exist.*

### (b) Invisible to in-app fuzzy search
Embedding is text-only: `_embed_workspace_file` calls `get_embedding(content)` ([primitives/workspace.py:30–48](../../api/services/primitives/workspace.py#L30)) — it embeds the `content` string. A blob has no text → no embedding → **not fuzzy-searchable / recallable.** Reachable only by **exact path/key** (the deterministic `recall` slug-resolve, [mcp_composition.py:330–336](../../api/services/mcp_composition.py#L330)).

### (c) No derive step exists for uploads
MCP has a placement-wake (inbound → seat derives → `operation/`, citing). **Uploads have no equivalent** — no wake, no promotion, no extraction-as-a-separate-act. `wake.py::_embed_derived_files` embeds what the *seat* derived into `operation/`; it does not read blobs or extract from uploads ([wake.py:1028](../../api/services/wake.py#L1028)). So a dumb-landed upload would sit **inert forever** — nothing ever makes it searchable.

### (d) Blob serving exists, but only in-app
`GET /api/documents/{path}/download` mints a signed URL via `create_signed_url` ([routes/documents.py:293,323](../../api/routes/documents.py#L293)) — but it is **authenticated, in-app, upload-path-specific** (reads `storage_path` from the `.md` frontmatter). It is **not exposed over MCP**, and there is **zero precedent** for cross-connector (Dropbox-style) blob reference anywhere in the codebase.

**Conclusion of the test:** dumb-intake-alone converts an upload from "extracted-and-searchable" to "raw-and-orphaned." That is a *regression*, not a conformance. KVK's guard correctly rejects it.

---

## 3. The three pieces (the actual unit of work)

"Raw in, derive downstream, referenceable at large" decomposes into three coordinated pieces. Piece A is what feels like "the change"; B and C are what make A not-a-regression.

### Piece A — Dumb intake (the raw lane)
Upload lands the **raw file itself** at `inbound/uploads/{principal}/{slug}.{ext}`, immutable, `authored_by: operator` (or the uploading principal, per ADR-373), the blob stored by reference via `content_url`. No extraction at intake. This is the direct sibling of the MCP `remember` raw lane — *"one intake model; the source is data"* (ADR-376 §1). **~1 file** (`documents.py`), plus the `inbound/uploads/` path convention (`workspace_paths.py`).
*Alone: an orphan.*

### Piece B — The derive step (what makes A searchable)
A **separate, downstream, citing act** that reads the raw blob → extracts text → writes a **derivation** (populates searchable `content` + embeds), citing the raw via `derived_from:`. Two honest sub-questions:
- **Who derives?** (i) A *mechanical* extract step (pure Python, zero-LLM — the pypdf2 we already have, just re-homed downstream as a capture-class act per ADR-393); or (ii) the *seat/Freddie* deriving understanding by judgment (the MCP model). **Lean: mechanical extract for text-bearing formats (pdf/docx/txt) — it is deterministic make-AI-ready, not judgment; ADR-393 §2 is the precedent (extraction is capture-class, not a wake).** Judgment-derivation (summarize/place) can layer on top additively.
- **Where does the derived text land?** `operation/…` (the MCP model — a citing understanding) or a derived sidecar next to the raw? **Lean: follow the MCP model — derive into `operation/` citing the raw** — so uploads and MCP share one derive shape (Singular Implementation).

This is the **new** capability. It is small (the extractor exists) but load-bearing: **B is the piece that keeps search working.** Without B, A is (a)+(b)+(c) above.

### Piece C — Referenceable at large (the Dropbox ask)
An **MCP-exposed blob reference** — a tool (or a field on `recall`/an existing read verb) that returns a **signed URL / stable reference** to a `content_url` blob, so ChatGPT / Claude / a future connector can *reach the raw file itself*, not just its derived text. This is **genuinely new interop capability** and touches the host-profile / interop canon (ADR-379). **Lean: this is its own ADR** — it is the "referenceable at large" ambition, distinct from the intake conformance (A+B). It should not gate A+B, but A+B should be built so C slots in (i.e. the raw MUST be a first-class `content_url` revision, which A already ensures — that is *why* A lands the blob on-substrate rather than orphaning it in storage).

**The dependency chain:** C needs A (a first-class blob revision to reference). B needs A (a raw to derive from). A alone regresses. So the honest minimum conformant ship is **A+B**; C is the operator's larger vision and its own ratification.

---

## 4. What this says about "does the substrate handle blobs?"

Yes — and it already half-does. `workspace_files` carries `content_url` + `content_type` ([authored_substrate.py:237–274](../../api/services/authored_substrate.py#L237)); the output gateway's rendered artifacts already use `content_url`. So **the substrate model does not need a new "file-type engine"** — a revision can carry a blob by reference today. The *"variety of formats"* problem **dissolves** rather than needing a handler (exactly ADR-376 §6's "dull-rule dividend"): intake stops caring what the bytes are; the derive step (B) is the only place that ever needs a format-specific reader, and it is downstream and swappable.

The re-founding keystone ([ADR-384](../adr/ADR-384-the-re-founding-meaning-folders-permission-as-metadata.md), **doc-only, NOT ratified**) would later fold the `inbound/` *lane* into a `revision_kind` (`observation | derivation`) *metadata flag* on the one meaning-file. **This doc deliberately targets the ADR-376 `inbound/` lane (shipped canon), not the keystone flag (unratified)** — per the operator's decision. When the keystone ratifies, `inbound/uploads/` migrates alongside every other `inbound/` path uniformly; building against the shipped lane now incurs no extra churn versus any other transport.

---

## 5. Open decisions for KVK (before the ADR)

1. **Scope of the first ADR** — ratify **A+B** as the conformance (dumb intake + a derive step that keeps search working), with **C (MCP blob reference / Dropbox-referenceability) as a named follow-on ADR**? Or spec all three in one? *(Lean: A+B is the honest conformant unit; C is the vision and its own ADR — but A must be built blob-first so C is unblocked.)*
2. **Who derives (Piece B)** — mechanical extract (deterministic, capture-class per ADR-393) for text-bearing formats, with judgment-derivation additive? Or seat-derives-everything (the pure MCP model)? *(Lean: mechanical extract — extraction is make-AI-ready mechanics, not judgment.)*
3. **Where derived text lands (Piece B)** — into `operation/` citing the raw (uploads share the MCP derive shape), or a derived sidecar beside the raw? *(Lean: `operation/`, Singular Implementation with MCP.)*
4. **`uploads/` vs `inbound/uploads/`** — does the human upload lane become `inbound/uploads/{principal}/` (the axiom's "N=human case of `inbound/`"), or stay `uploads/` as a sibling raw root? *(Lean: `inbound/uploads/` — one raw model, source-is-data; matches ADR-376 §4. Note this retires the shipped `uploads/` root — a topology + FE-tree change, and `OPERATOR_DELETABLE_PREFIX`/`managed_by:user` semantics move with it.)*
5. **Blob attribution + principal** — `authored_by: operator` today; under ADR-373 multi-principal, the uploading principal. Confirm the raw revision's `authored_by` is the uploader, and the derivation's is `system:extract` / `freddie:<id>`. *(Lean: yes — mirrors MCP's `yarnnn:mcp:{client}` raw / `reviewer:ai` derived split.)*
6. **The `.md` viewer bug (orthogonal, ship-now-able)** — independent of A/B/C: today the upload's YAML frontmatter renders as **visible body text** in the file viewer (operator-observed), and the file is named the generic `document.md`. These are two small FE/naming fixes that do **not** depend on the intake refactor and could ship immediately if desired. *(Flagged so they don't get blocked behind the big ADR.)*

---

## 6. Recommendation

1. **Write the ADR against A+B** (the honest conformant unit), naming **C as an explicit, sequenced follow-on** ("Referenceable Raw — the blob-reference surface over MCP") so the Dropbox ambition is on the record without gating the conformance. Build A **blob-first** (raw as a first-class `content_url` revision) precisely so C is unblocked later.
2. **Piece B is the load-bearing half** — the ADR's center of gravity is *the derive step*, not the intake change. "Stop extracting at intake" is one line; "extraction becomes a downstream citing act that keeps recall working" is the design. Frame the ADR that way.
3. **Sequence with the keystone, don't wait on it.** Target the shipped `inbound/` lane; the keystone's `revision_kind` fold is a later uniform migration across all transports, not a blocker for this one.
4. **Split the two cosmetic viewer/naming fixes out** (§5.6) — they're real, small, and independent; don't let them ride the big ADR.

The dividend, if A+B+C land: an uploaded PDF is a **first-class attributed raw observation**, its extracted understanding is a **separate citing derivation**, and the raw itself is **referenceable by any connector** — the same shape as every other context-in transport, and the literal realization of KVK's "dumbest possible intake, everything downstream." The moat sentence ("which principal contributed each version, and how the seat reconciled them") becomes true for uploads too, not just MCP.
