# ADR-395 — The Model-Consumable Projection: upload intake conformance (retain raw · derive projection · host-gated raw reference)

> **Status**: **Accepted** (canon ratified 2026-07-01 — **Phase 0 done**: FOUNDATIONS Derived Principle 34 landed at v9.14 + the DP32 cross-reference sentence. **Phase 1 (A+B) shipped to main 2026-07-01** [commit `542740e`/merge `d45d0b0`]: raw blob lands at `inbound/uploads/{principal}/{slug}.{ext}` via `content_url` [stable `/api/documents/blob` redirect]; `ExtractTextFromBlob` primitive derives the co-located `.extracted.md` text projection citing the raw via `derived_from`, invoked INLINE [refined from "capture-lane hook" — an upload is one-shot, zero-LLM in-request]. **Phase-1 completeness closeout (2026-07-02)**: an audit found two shipped defects the initial land missed — (i) the projection landed at `inbound/uploads/*.extracted.md`, a lane that was NOT embed-eligible (roots were `operation/`+`uploads/` only) AND outside `QueryKnowledge`'s hard `/workspace/operation/` search prefix, so the projection was never embedded and was unreachable by `recall` — the §4-Piece-B "closes the searchability gap" claim was aspirational, not real. Fixed: `inbound/uploads/` added to `_EMBED_ELIGIBLE_ROOTS` + a shared `is_searchable_root` predicate, and `handle_query_knowledge`'s default (no-domain) sweep now spans the searchable surface (unscoped RPC + post-filter to searchable roots) rather than locking to `operation/`. (ii) `GET /documents/{path}/download` read `storage_path` only from frontmatter, which the new raw rows don't carry (storage is in `content_url`), so Download 404'd for every new upload — fixed to resolve `storage_path` from `content_url` first, legacy-frontmatter fallback retained. A dedicated `test_adr395_model_consumable_projection.py` gate now drives the real `process_document`+`ExtractTextFromBlob` path and asserts the projection is embed-eligible+recall-reachable — the regression guard the ADR-331 gate (which mocks `process_document`) could not provide. **Embedding-over-reach correction (2026-07-02)**: an OpenAI-quota outage (surfaced by live E2E validation) exposed that the intake path had drifted toward embedding-first coupling, against ADR-325's ratified discipline (*embedding is enrichment; the mechanical floor is load-bearing*). Two corrections, per the operator's re-derivation: (i) **recall is now mechanical-first** — `handle_query_knowledge` runs the free BM25 full-text path first and escalates to the paid semantic embed ONLY when BM25 comes up empty (confines the un-metered embedding COGS — the pricing carve's B′ line — to genuinely-fuzzy queries, and keeps the recall hot path off the external rate-limited API); (ii) **the upload embed is now DEFERRED** — `ExtractTextFromBlob` gains an `embed` flag (default true); `process_document` passes `embed=False` + reports `embed_pending`, and the upload route schedules the embed via FastAPI `BackgroundTasks` AFTER the response, so a rate-limited/slow OpenAI call never blocks or breaks the upload (the projection is BM25-searchable the instant the response returns; the embedding enrichment catches up). ADR-325's upload auto-embed exception (D6, operator-initiated, not Reviewer-gated) is PRESERVED — only its *timing* moves from synchronous to deferred. Gate 21/21 (adds deferred-embed + mechanical-first assertions). **Phase 2 [C] is CLOSED by ADR-621** (§4/§7 — the medium reason does not expire). **Phase 3 SHIPPED 2026-09-21 as Amendment 1 (§8)**: the intake door drops its format allowlist entirely (D8 — acceptance is conformance to `public.data`), a file with no projection is RETAINED and carries a legible marker instead of failing the upload (D9), and `xlsx`/`pptx` join the text family while the `docx` extractor is REPAIRED of silent table/header loss (D10). §8.7 scopes the sandbox horizon without adopting it. Gate 42/42, falsified six ways. **Amendment 2 (2026-09-23, §11) — the format harness**: office files first-class on demand from beta members. Phase 1 SHIPPED: ONE server format registry (`api/services/file_formats.py`, D14) replacing five hand-kept extension tables; view kinds + per-file export targets served on `GET /workspace/file` (D15/D16); `.doc` stops claiming readability (D17); HWP/HWPX read in-process (D18). Phase 2 (client viewers) and phase 3 (the outbound writer, then its skill) build against it.). Ratifies **FOUNDATIONS Derived Principle 34** (the model-consumable projection — the consumption member of the perception cycle) and conforms the **human-upload** transport to it — the last context-in transport DP32 named but the code never fixed. **Substrate + Channel dimensions** (Axiom 1 — how an uploaded file is retained + derived; Axiom 6 — how a substrate object egresses to a model). Adds **one new primitive** (`ExtractTextFromBlob`), **one new capability flag** on the host profile, and **populates an existing-but-unused column** (`workspace_files.content_url`). Changes **no** existing write gate and **no** attribution taxonomy.
> **Date**: 2026-07-01
> **Authors**: KVK (operator) + Claude (collaborator)
> **Discourse base**: the operator's escalation of the upload-`.md`-not-`.pdf` observation to first principles — *"start outside YARNNN, the overall LLM handling: can LLMs via MCP receive URL links, read them, other formats — such that a pure reference-our-URL MCP tool works? If not, is text derivation necessary + does file-variety (pptx/xlsx/images/zips) need deeper consideration?"* Verified against the **MCP spec 2025-06-18** + **Anthropic Files/PDF platform docs (2026-07)**. Two analysis docs: [the-model-consumable-projection-axiom](../analysis/the-model-consumable-projection-axiom-2026-07-01.md) (the axiom) + [dumb-intake-and-the-referenceable-raw-lane](../analysis/dumb-intake-and-the-referenceable-raw-lane-2026-07-01.md) (the intake gap it grew from).
> **Builds on / ratified framing**: [ADR-376](ADR-376-ledger-intake-raw-observation-vs-derived-substrate.md) / DP32 (`retain + attribute + cite` — this ADR is the upload instance; retain = A, derive-and-cite = B) + [ADR-393](ADR-393-the-perception-capture-pipeline.md) (the mechanical capture lane B's derive step registers in) + [ADR-379](ADR-379-host-profiles-the-interop-reach-registry.md) (host-as-data registry — C's gate is a sibling capability flag to `renders_widgets`) + [ADR-209](ADR-209-authored-substrate.md) (`write_revision` single write path — the raw blob is an ordinary attributed revision that additionally carries `content_url`).
> **Sibling**: [ADR-394](ADR-394-connector-capture-the-reader.md) (Proposed) — the **connector** instance of the same DP34 pattern (retain platform raw + derive by reference); ADR-395 is the **upload** instance. Both preserve ADR-376's derive-as-separate-act; they must stay coherent (one principle, two transports).
> **Amends**: [ADR-249](ADR-249-two-intent-file-handling.md) — the persistent-upload path (eager text-extraction *as* the substrate object, raw orphaned in storage) is superseded: extraction becomes a **separate downstream derive act**, and the raw blob becomes a **first-class `content_url` revision**. The two-intent (ephemeral vs persistent) distinction ADR-249 drew is preserved; only the *how-persistent-uploads-are-stored* half changes.
> **Dimensional classification** (Axiom 0): **Channel** (Axiom 6 — the load-bearing claim: a substrate object crosses into a model only as a projection {text|image}; egress is a Channel act with a hard medium constraint) + **Substrate** (Axiom 1 — retain the raw, derive the projection citing it).

---

## 1. Why this ADR — the medium won't let intake be dumb-and-nothing-else

An operator uploaded a PDF. It landed as `document.md` (extracted text), with the raw PDF orphaned in Supabase storage and a metadata header rendering as visible body text. The operator's instinct was right — *intake should be the dumbest possible pipe; process downstream* (ADR-376/393). But the follow-up guard was the load-bearing one: **"whatever lands in inbound can and should be easily referenceable via MCP to other connectors or at large (think Dropbox). Else discourse."**

The discourse found that **"dumb intake, reference the raw"** fails **at the protocol layer**, not at YARNNN's code:

**MCP spec 2025-06-18 — a tool result reliably delivers only `text` + `image`/`audio` base64 to the model.** A `resource_link` is *"a URI that **can be** ... fetched **by the client**"* — host-discretionary, **not** a guarantee, **not** in the `resources/list` contract, and a host that blindly GETs a URL **carries none of YARNNN's auth** (signed URLs 403/expire). Hosts are explicitly permitted to drop content they don't understand (*"Clients SHOULD validate tool results before passing to LLM"* — the "resource silently dropped" bug in the wild).

**Anthropic's own API — even the most file-native frontier platform converts before reading.** PDF is native (multimodal <100pp); everything else — *"Word and PowerPoint require conversion to PDF or plain text before submission"*; *".csv, .txt, .md, .docx, .xlsx → convert to plain text."*

**The invariant both channels share:** a model reads **text and images**, never arbitrary containers. So **text/image derivation is FORCED by the medium** — the "variety of formats" problem does not *dissolve* (as ADR-376's dull-rule dividend hoped for intake); it **relocates** into a mandatory derive layer. The `resource_link`-to-raw path survives only as a **best-effort, host-gated garnish** — never the guarantee.

This ADR names the constraint as canon (DP34) and conforms uploads to it.

---

## 2. Ratifiable canon — FOUNDATIONS Derived Principle 34 (v9.14)

*(Drop-in block. On ratification this becomes DP34 in `FOUNDATIONS.md`, with the version-header line appended and DP32 gaining the one cross-reference sentence in §2.1.)*

> 34. **The model-consumable projection: substrate crosses into a model only as text or image, never as the raw container** (2026-07-01, ADR-395) — A substrate object is delivered to a language model **only as a model-consumable projection — text, or image** (audio for audio-native models). The **raw container is retained** (Derived Principle 32 — immutable, attributed) but is **never itself the thing read**: consumption requires projection, because a model reads text and images and *not* arbitrary file formats. This is a **fact of the medium, not of YARNNN** — it holds through MCP (a `CallToolResult` reliably carries only `text`/`image`/`audio` content; a `resource_link` URI is host-discretionary and auth-blind, never a guarantee) *and* through the direct model API (even the most file-native vendor converts docx/xlsx/pptx to text/PDF before the model reads). The projection is a **derived, attributed act that cites the raw** (Derived Principle 32's derive step — here made **protocol-mandatory** for any non-text raw, not merely permitted): retention alone never yields a consumable object. **Format variety is contained in a swappable derive-registry** — one strategy per format-family (the intake mirror of the output gateway `render/skills/`, running blob→{text|image} where the gateway runs text→{pptx,xlsx,pdf}); a format with **no registered strategy is retained-but-not-yet-consumable — legibly marked, never silently dropped or fabricated** (the anti-silent-drop clause + the graceful-degradation path that makes "any format at large" safe: an unhandled format is a *known gap*, not a break). A raw-container **reference over interop** (`resource_link`/embedded blob) is a **best-effort enhancement for hosts that provably fetch-and-auth it** (host-profile-gated, ADR-379) — **never a substitute** for the text projection the model is guaranteed to read. **This is the consumption member of the perception cycle**: Derived Principle 27 fixes how reality *enters* (input), Derived Principle 32 fixes how the observation is *retained* (retention), Derived Principle 31 fixes how a claim *exits* citing its Source (output-binding), and **this fixes how the retained object is *delivered to the model that reads it*** (consumption) — the four close the perceive→retain→consume→cite loop. **The dull-rule dividend**: the kernel stays **format-blind** (it says only "consumption = projection"; all format-specific machinery lives in the service-layer registry, additive per format-family); no schema change (blobs already storable via `content_url`); no new authorization vocabulary. **Diagnostic test**: a path that hands a model the raw bytes of a non-text/non-image container and assumes it is read; a path that returns a `resource_link` to an authed blob and treats it as delivered; a derive step whose projection omits its `derived_from` citation to the raw; or an unhandled format that is silently dropped rather than marked retained-not-consumable — each violates this principle. **Composes with** Derived Principle 32 (its retain half; this is its consume half — the derive step DP32 permits, this makes protocol-mandatory), Derived Principle 27 + 31 (the input + output-binding members of the same cycle), Axiom 6 (Channel — egress is a Channel act; the medium's text/image constraint is a Channel invariant), ADR-379 (the host-profile gate the raw-reference enhancement rides), ADR-393 (the mechanical capture lane the derive step registers in), ADR-394 (the connector instance of the same retain-then-project pattern). **Canon source**: [ADR-395](../adr/ADR-395-model-consumable-projection-and-upload-intake-conformance.md) + [the model-consumable-projection analysis](../analysis/the-model-consumable-projection-axiom-2026-07-01.md) + MCP spec 2025-06-18 + Anthropic Files/PDF platform docs.

**Version-header append** (to the `> **Date**:` line): *"; **v9.14 Derived Principle 34 — the model-consumable projection: substrate crosses into a model only as text or image; the raw container is retained (DP32) but never itself read; the projection is a derived citing act (protocol-mandatory for non-text raw); format variety is contained in a swappable derive-registry; unregistered = retained-but-not-yet-consumable, never dropped; a raw reference over interop is a host-gated best-effort garnish, never a substitute; the consumption member of the perception cycle DP27·DP32·DP31·DP34 (ADR-395) 2026-07-01"*.

**DP32 cross-reference sentence** (append to DP32's body): *"For any **non-text** raw, the derive step this principle permits is **mandated** by Derived Principle 34 (a model reads only a projection {text|image}, never the container) — retention alone never yields a consumable object."*

---

## 3. Decisions (all ratified by the operator 2026-07-01)

| # | Decision | Chosen |
|---|---|---|
| **D1** | Canon altitude + name | **Derived Principle 34**, name *"the model-consumable projection"* (derived from Axiom 1 + Axiom 6; not a new axiom — mirrors DP32's own DP-not-axiom call) |
| **D2** | Who derives the projection (Piece B) | **Mechanical extract, downstream** — a deterministic zero-LLM capture-class step (ADR-393 lane); the existing pypdf2/docx/txt extraction re-homed as the derive act. Judgment-derivation (summarize/place) is additive, later |
| **D3** | Where raw + projection land | **Raw at `inbound/uploads/{principal}/{slug}.{ext}` via `content_url` (immutable); the text projection cites it via `derived_from`.** Uploads become the "N=human case of `inbound/`" (ADR-376 §4); the shipped `uploads/` root is retired (topology + FE-tree change) |
| **D4** | First-ship scope | **A+B+C together** — retain-raw + mechanical-derive + the host-gated MCP raw-reference in one pass |
| **D5** | Projection target (derived from D2/D3) | The mechanical projection lands as a sibling derived file citing the raw; the **MCP-parity `operation/` placement** (seat-derived understanding) stays the *additive judgment layer*, not this ship (D2 = mechanical-first) |

---

## 4. The three pieces (exact seams — receipts verified 2026-07-01)

DP34 lands on uploads as three obligations. Seam map below; **"NEW"** flags what must be built from scratch.

### Piece A — retain the raw blob (`content_url`), immutable

Today the upload writes **extracted text** to `/workspace/uploads/{slug}.md` and stashes the raw only as a `storage_path:` **string in frontmatter** — the `workspace_files.content_url` **column is never populated**. Conformance:

- **`api/routes/documents.py:112`** — `storage_path = f"{user_id}/{document_id}/original.{file_type}"` (raw blob upload — *unchanged*, already correct).
- **`api/services/documents.py`** — the write target moves from `/workspace/uploads/{slug}.md` (extracted text) to **`/workspace/inbound/uploads/{principal}/{slug}.{ext}`** carrying **`content_url` = the blob reference**, `content` empty (or a short caption), `content_type` = the real MIME. `authored_by` = the uploading principal (`operator`, or the ADR-373 principal).
- **`api/services/authored_substrate.py:297,393`** — `write_revision(..., content_url=..., content_type=...)` **already accepts these params** (ready to receive — no change). *Populating the column is the A-change.*
- **`api/services/workspace_paths.py`** — add the `inbound/uploads/` path convention (INBOUND lane already exists at `INBOUND_ROOT`; `uploads/` folds under it per D3).

**NEW in A**: none structurally — A is *wiring `content_url` through the existing write path* + the path move. The `uploads/`→`inbound/uploads/` topology change touches `workspace_paths.py` + the FE tree (WORKSPACE_ROOTS / the Files explorer) + `OPERATOR_DELETABLE_PREFIX` + `managed_by:user` semantics (these move with the lane).

### Piece B — derive the text projection (mechanical, capture-class), citing the raw

- **NEW primitive `ExtractTextFromBlob`** in `api/services/primitives/` — takes `{storage_path | content_url, write_to}`, reads the blob, runs the **existing** `extract_text()` (`api/services/documents.py:62` — pdf/docx/txt dispatch, *reused verbatim*), and `write_revision`s the **text projection** to a derived path with `derived_from: <raw inbound path>`, then `_embed_workspace_file`s it (the projection is the embeddable text — closes the searchability gap **iff its lane is embed-eligible + inside the recall search surface; the Phase-1 closeout added `inbound/uploads/` to both — see the status banner**). Registers in `HANDLERS` + `HEADLESS_PRIMITIVES` + `FREDDIE_PRIMITIVES` (NOT `CHAT_PRIMITIVES` — same policy as `SyncPlatformState`/`CaptureConnector`).
- **Inline-mechanical trigger** (refined 2026-07-01, Phase-1 implementation) — the derive fires **inline in the upload request**, right after the raw-blob write, via `execute_primitive(auth, "ExtractTextFromBlob", …)`. Zero-LLM, deterministic, same request — so the file is searchable the instant upload returns (no scheduler lag). This **refines** the ADR's earlier "capture-lane hook" language: the ADR-393 capture *lane* is built for **scheduled/cadenced** captures declared in `_captures.yaml` (a recurring watch); an **upload is a synchronous one-shot**, so forcing it through the async scheduler would be a category error (a one-shot event dressed as a recurring declaration) and would open a search-lag gap between upload and derive. Both paths run the *same* `ExtractTextFromBlob` primitive (Singular Implementation) — the connector case invokes it from the capture lane on cadence, the upload case invokes it inline on arrival; the primitive is trigger-agnostic (it never reads the clock; `observed_at`/the raw path are caller-supplied). The derive is still **capture-*class*** in the ADR-393 sense (mechanical, wakes no one, zero-LLM); only its *dispatch home* is the request path, not the scheduler.
- **Registry seam** — `ExtractTextFromBlob` is the first entry of the **derive-registry** (D2). MIME→strategy: `{pdf,docx,txt,md,csv}→text`; `image/*`→pass-through (already model-consumable); `{xlsx,pptx,zip,audio}`→**named-deferred** (registry entries with a known strategy shape, built on demand — until then, **retained-but-not-yet-consumable**, legibly marked).

**NEW in B**: the `ExtractTextFromBlob` primitive (thin — wraps existing `extract_text`), its capture-lane registration, and the on-arrival trigger. **The extractor logic is reused, not rebuilt.**

### Piece C — host-gated MCP raw reference (the best-effort garnish)

- **`api/mcp_server/presentation/hosts.py:47`** — add capability flag to `HostProfile`: `can_fetch_signed_urls: bool = False` (sibling of the existing `renders_widgets` — same ADR-379 data-registry pattern). Set `True` only for hosts proven to fetch+auth (start conservative: none, or gate behind a verified profile). Add helper `can_fetch_signed_urls(host_id) -> bool` (mirrors `renders_widgets`, lines 127–152).
- **NEW service helper** `create_signed_url_for_storage_path(client, storage_path, expires_in=3600)` in `api/services/documents.py` — wraps the storage `create_signed_url` (today only inline in the HTTP route `routes/documents.py:321`). One hour expiry (matches the route).
- **`api/mcp_server/server.py:104` `_present()`** — when (1) the result references a file with `content_url` AND (2) `can_fetch_signed_urls(client_name)` is `True`, **append** a `resource_link` (or embedded `type:resource` with the signed URL) to `content[]` — *alongside*, never *instead of*, the text projection. When the gate is `False`, the model gets the text projection only (the guarantee). This exactly parallels the existing `_meta` widget gate (host-gated enhancement, text-safe default).
- **`api/services/mcp_composition.py:768–993`** (recall/trace) — surface `content_url` on the result chunk so `_present` can build the reference. Today recall/trace return `path`+`excerpt`; add the raw reference when present + gated.

**NEW in C**: the `can_fetch_signed_urls` flag + helper, the `resource_link` assembly in `_present`, and surfacing `content_url` through recall/trace. **All host-gated and text-safe by default — a host that fails the gate is unaffected.** (The service-level `create_signed_url_for_storage_path` helper C planned for was **already built in Phase 1** — Piece A's stable blob route reuses it — so C's remaining scope shrank.)

### ⚠️ Piece C is CLOSED (2026-08-31, ADR-621) — read this before the deferral below

**The deferral rationale that follows is preserved as written, but Piece C is no
longer open.** [ADR-621](ADR-621-a-binary-file-is-not-an-empty-file.md) resolves
it in both directions:

- **Read side — SHIPPED, in a better shape than C specified.** C proposed a
  host-gated `resource_link` in `_present()`. That shape is refused: Anthropic's
  MCP connector throws `UnsupportedMCPValueError` on resource links, and
  `ImageContent` requires base64. The raw reference ships instead as a plain
  `content_url` field on `open` (ADR-621 D2) — **ungated**, because plain JSON
  needs no host capability, which is what C's `can_fetch_signed_urls` flag
  existed to negotiate. **The `HostProfile` flag is NOT built and should not be:
  there is nothing left for it to gate.**
- **Write side — CLOSED on the medium.** C's unblock condition was reason 4
  below: *"a live fetch-and-auth test against a real host"*. That test has now
  been run publicly — Box shipped base64-over-MCP, measured it corrupting a file
  at 175 KB and failing outright at 20 MB, and replaced it with signed URLs. The
  condition is met with a NEGATIVE result. Reason 3 ("no demonstrated demand")
  has since been retired by a real operator need, but reason 4 is the stronger
  one and does not expire.

The reserved successor is a presigned **upload** handshake (ADR-621 §8) — its own
ADR, not a revival of C.

### Piece C is DEFERRED — the explicit rationale (2026-07-01)

C is **named-but-not-built**, and deliberately so — recorded here so it is not picked up prematurely:

1. **The medium does not guarantee it works.** DP34's whole finding is that a `resource_link` over MCP is **host-discretionary and auth-blind** — the spec gives no promise a host fetches it, and a host that does carries none of YARNNN's auth (the signed URL is time-boxed + scoped). So C is, by the axiom's own logic, the *least certain* piece: it is a best-effort garnish, never the guarantee. Building it on the *assumption* that a host will fetch-and-auth is exactly the kind of speculation the axiom warns against.
2. **A+B already delivered the guaranteed path.** The text projection (Piece B, shipped) is the model-consumable form that *is* guaranteed to reach any host through `recall`/`trace`. C adds only the raw-blob *reference* on top — value only when the operator genuinely needs the original bytes over interop, which the text does not currently block.
3. **No demonstrated demand.** C is the "referenceable at large / Dropbox" ambition. No operator or connector is asking for the raw file over MCP today; agents read the text. Per ADR-380 §5 (build-when-demanded), C waits for a concrete host + use-case.
4. **It needs an empirical prerequisite, not a code assumption.** Before C ships, the honest first step is a **live fetch-and-auth test** against a real host (does ChatGPT / claude.ai actually GET a `resource_link` to a signed URL, and does the fetch carry auth?). That test — not an ADR paragraph — determines whether C is even realizable, and which host profiles get `can_fetch_signed_urls = True`. **C is unblocked only once that test passes for at least one host.**

The stability audit (2026-07-01) confirmed A+B + the surrounding MCP/file scope are stable, so nothing depends on C. When demand + an empirical host result arrive, C is a small, well-scoped, host-gated addition on top of the Phase-1 seams (the raw is already a first-class `content_url` revision — the one structural prerequisite A guaranteed).

---

## 5. Implementation phases (the move-to-implementation sequence)

Ordered so each phase is independently shippable and search never breaks:

1. **Phase 0 — canon** (doc-only): ratify DP34 into FOUNDATIONS (v9.14) + the DP32 cross-reference sentence + this ADR to Accepted. *No code.*
2. **Phase 1 — A (retain raw)** + **B (derive projection)** together, because A-alone regresses search (a raw with no projection is unsearchable — the whole point of B). Migration/backfill: existing `uploads/*.md` (extracted-text) files stay valid; new uploads take the raw+projection shape. The FE Files-tree `uploads/`→`inbound/uploads/` move ships with this phase (or a compatibility alias during transition).
3. **Phase 2 — C (host-gated raw reference)** — **DEFERRED** (see the Piece-C deferral rationale above): gated on demand + an empirical host fetch-and-auth test, not built on assumption. When unblocked: the `HostProfile` flag (default-off), the `_present` `resource_link` assembly, `content_url` surfaced through recall/trace. Ships dark (gate off) → enable per host as fetch+auth is verified. **Zero risk to non-gated hosts.**
4. **Phase 3 — registry expansion** (demand-gated): add `xlsx`/`pptx`/`zip`/`audio` derive strategies as demand proves them; each is one registry entry.
5. **Orthogonal, ship-anytime** (not gated on any of the above): the two cosmetics — (a) the frontmatter-renders-as-body-text viewer bug, (b) the generic `document.md` naming (derive from `original_filename`). These are pure FE/naming fixes and can ship immediately, independent of the whole refactor.

---

## 6. What this preserves / does not touch (the discipline check)

- **No write-gate change** (ADR-307) — the raw revision and the derived projection both flow through `write_revision`, gated as today.
- **No attribution taxonomy change** (ADR-209) — raw = uploading principal; projection = `system:extract` (mechanical) — same split as MCP's `yarnnn:mcp:{client}` raw / `reviewer:ai` derived.
- **No schema change** — `content_url`/`content_type` columns already exist; A populates them.
- **Kernel stays format-blind** (DP34 dull-rule) — every format-specific reader lives in the service-layer registry, additive.
- **Composes with ADR-394** — connector-read and upload-read are two instances of DP34's retain-then-project; they share the "derive is a separate act" discipline and must not drift.
- **The re-founding keystone** (ADR-384, unratified) — this ADR targets the **shipped `inbound/` lane**, not the keystone's `revision_kind` fold. When the keystone ratifies, `inbound/uploads/` migrates with every other `inbound/` path uniformly — DP34 is orthogonal to that fold (it governs *egress-to-model*, not *raw-vs-derived namespace*).

---

## 7. Open items before Phase 1 code

1. **Projection path shape** (D5 detail) — the mechanical text projection: a sibling under `inbound/uploads/` (raw + `.txt` projection co-located), or a derived file elsewhere citing the raw? *(Lean: sibling projection co-located with the raw, `derived_from` citation — simplest, keeps raw+projection atomic; the additive seat-derive into `operation/` layers on later per D2.)*
2. **On-arrival trigger** — an upload is one-shot, not cadenced; confirm the derive fires via a substrate-event hook (ADR-296 wake source) on `inbound/uploads/` writes, dispatched to the capture lane's mechanical dispatch (zero-LLM), NOT the judgment wake funnel.
3. **`can_fetch_signed_urls` initial set** — ship Phase 2 with the flag **off for all hosts** (pure dark launch), then verify ChatGPT/claude.ai fetch+auth behavior empirically before flipping any on. *(Lean: yes — default-deny, verify-then-enable, exactly the `renders_widgets` rollout shape.)*
4. **Backfill** — leave existing extracted-text `uploads/*.md` as-is (valid substrate), or re-shape them to raw+projection? *(Lean: leave as-is — they are already consumable; new uploads take the new shape. No destructive migration.)*

---

## 8. Amendment 1 (2026-09-21) — Phase 3 lands, and the door opens to everything

> **Status**: **Accepted + Implemented** (2026-09-21). Operator-directed from
> pre-trial colleague feedback: *"they want to use it but it doesn't accommodate
> their existing files"*, then the frame — *"what if we allow upload of the file
> types, in fact open that up as much as possible. really become THE file system
> native."*

### 8.1 Context — the deferral was never exercised, because the door refused first

Phase 3 ("registry expansion: xlsx/pptx/zip/audio, demand-gated", §5.4) was
written as though a deferred format would *arrive and be marked*. The audit found
it never could. Three gates sat in front of the registry, and the file died at the
first:

| Gate | Site | Verdict on `.xlsx` |
|---|---|---|
| FE `accept` | `UploadButton.tsx:37`, `LanePanel.tsx:1823` | not offered in the picker |
| `_DOC_MIMES` allowlist | `routes/documents.py:124` | **rejected** — "Unsupported file type" |
| the 50-char floor | `services/documents.py:221` | **whole upload fails** — "No text could be extracted" |

So `registry_strategy("xlsx") == "deferred"` was true and **unreachable**. The
anti-silent-drop clause — *"a format with no registered strategy is
retained-but-not-yet-consumable, legibly marked, never silently dropped"* — had
no production path on the upload door. It was not a silent drop; it was a loud
refusal, which is a different defect and a worse one: the bytes never landed at
all.

⭐ **The generalizable lesson**: a degradation path that no input can reach is not
a degradation path. D3's marker (ADR-530) worked on the SHARE door because a
deferred file could already be *in* the substrate; on the UPLOAD door nothing
could get in to degrade.

### 8.2 D8 — acceptance is conformance to `public.data`, and that is everything

The intake verdict (§D5 / ADR-427 Phase 3) stops enumerating a document set. It
asks the one conformance question the DAG already answers:

```python
accepted = conforms_to(mime, "public.data")   # the root — always True
```

`_DOC_MIMES` is **deleted**, not widened. A widened allowlist is the same defect
with a longer list, and it is the shape that produced this bug: every new format
needs a person to remember a second place. `content_types.py` already declares
`xlsx`/`pptx` in `_ZIP_EXT_MIMES` and already conforms them to `public.data` —
the kernel knew these formats before the door did.

The FE `accept` attributes are **removed entirely** rather than widened, for the
same reason: they were a third home for a decision the registry owns, and they
had already drifted from each other (the Files picker offered `.zip`; the chat
composer did not).

**What still refuses**, and why each is a real limit rather than a taste:

- **size** — `MAX_FILE_SIZE` 25MB / `MAX_MEDIA_SIZE` 100MB, unchanged.
- **emptiness** — under 10 bytes, unchanged.
- **placement** — `operator_can_organize` (ADR-555 D2), unchanged.

Acceptance is no longer a statement about format. It is a statement about size
and authority, which is what a filesystem's door is actually for.

### 8.3 D9 — a file with no projection is RETAINED, and says so

The 50-char extraction floor fails the whole upload. That floor was correct when
every accepted format had a text strategy; with the door open it is the exact
inversion of DP34's anti-silent-drop clause, so it is **removed as a rejection**
and re-expressed as a projection outcome.

The pipeline splits what the floor conflated — *"can I read this?"* and
*"should this file exist?"*:

- `strategy == "text"` **and** text extracted → raw + `.extracted.md` projection,
  as today.
- `strategy == "passthrough"` (image) → raw only, as today.
- `strategy == "deferred"`, **or** a text-family file whose extraction came back
  empty → **the raw lands**, and a co-located `.extracted.md` carries the
  ADR-530 D3 marker: `derived_from`, the filename, and a NOTE stating the format
  is retained and not yet machine-readable. **No fabricated content.**

The marker is the same shape ADR-530 D3 established on the share door, so there
is one spelling of "retained-not-consumable" in the codebase, not two.

⭐ **An extraction failure is now a property of the projection, never a verdict on
the file.** A scanned PDF that yields no text is a real file the member can see,
open, download, move and share — it is simply not yet readable by a model, and it
says so in a file the agent can read.

### 8.4 D10 — the registry grows by three, in-process, no sandbox

`xlsx` and `pptx` leave `_DEFERRED_FORMATS` and join `_TEXT_FORMATS`:

- **`xlsx`** — `openpyxl` (already in `requirements.txt`, previously used only by
  `routes/admin.py`). Each sheet becomes `## {sheet name}` + tab-separated rows.
  Formulas read as their cached values; empty trailing rows/columns are trimmed.
- **`pptx`** — `python-pptx` (new dependency). Each slide becomes `## Slide {n}`
  + every shape's text frame in document order + speaker notes.
- **`docx`** — the extractor is **repaired, not added**. It walked
  `doc.paragraphs` only, which silently drops **tables, headers and footers**. A
  contract or spec sheet is mostly tables; this was live data loss dressed as a
  successful upload, and it is the likeliest cause of the colleague feedback that
  opened this amendment. It now walks the body in document order (paragraphs and
  tables interleaved, via the underlying XML child order) plus per-section
  headers and footers.

**Why a library and not a sandbox.** The frontier platforms handle `.xlsx` by
running Python in a code interpreter; the container never reaches the model. That
is DP34 confirmed from outside, not a different architecture — but their
mechanism is arbitrary code execution, which yarnnn does not have and is not
acquiring here. Deterministic extraction is a **library call**, and the
precedent is ADR-417 §2c, which ruled compose *"moves in-API as a library, NOT
retired"*. The sandbox question — pivot tables, chart rendering, "reformat this
deck" — is real, has genuine security weight, and belongs in its own ADR. It is
NOT smuggled in as a skill import: an imported `xlsx` skill would instruct an
agent to execute Python it cannot execute, and a skill's failure is silent.

### 8.5 What this does NOT do

- **No round-trip.** Edits land in the `.extracted.md` projection; the `.docx`
  is never rewritten. Office formats are read-in, not edited-in-place.
- **No outbound `.docx`/`.pptx` writer.** ADR-417 §2b's ruling stands — if
  downloadable export returns it is an in-API library call, demand-gated, and
  nobody has asked.
  **→ Amended by §11 (am.2, 2026-09-23): the demand gate FIRED** — beta members
  asked. The writer is built as the in-API library call this bullet named; see
  D16.
- **No Google Drive.** A Google Doc has no bytes to upload; that is a connector
  question under ADR-657's two lanes, and ADR-131 sunset the Google tools for
  reasons that need re-reading before anyone proposes them again.
- **No sandbox / code interpreter.** §8.4.
- **No schema change, no new primitive, no write-gate change.** The registry is
  three entries and one predicate.

### 8.6 Gate

`test_adr395_model_consumable_projection.py`, extended: the format matrix asserts
`xlsx`/`pptx` are `text` and reachable through the real door; `_DOC_MIMES` is
asserted absent; the deferred-marker branch is driven over an unknown extension
and asserts the raw landed AND the marker cites it; the docx extractor is driven
over a real table-bearing document and asserts the table text survives.

### 8.7 The sandbox horizon — scoped, NOT adopted (operator-directed, 2026-09-21)

§8.4 rules that deterministic extraction is a library call and that the sandbox
question belongs in its own ADR. This section records **what that question is**
and **what it would cost**, so a future session inherits the analysis rather than
re-deriving it. It changes nothing decided above. **Nothing here is adopted, no
vendor is chosen, and no work is authorized by this section.**

#### What a sandbox would buy that a library cannot

The library ceiling is *read the file's text*. Everything past that needs code
execution against the bytes:

| Capability | Library | Sandbox |
|---|---|---|
| Read a sheet's values | ✅ am.1 D10 | ✅ |
| Read slide text + notes | ✅ am.1 D10 | ✅ |
| Read a table in a contract | ✅ am.1 D10 | ✅ |
| Pivot / aggregate / recompute a workbook | ❌ | ✅ |
| Render a chart from a sheet | ❌ (ADR-417 §2a retired generation) | ✅ |
| OCR a scanned PDF (today: am.1 D9 marker) | ❌ | ✅ |
| Author a real `.docx`/`.pptx` back out | ❌ (ADR-417 §2b) | ✅ |
| Arbitrary member-directed file work | ❌ | ✅ |

This is the same split the frontier platforms live on: their `xlsx`/`pptx`/`docx`
skills are **instructions for driving a code interpreter**, not model knowledge.
Importing such a skill without the interpreter ships instructions that cannot
execute, and a skill's failure is silent — which is why §8.4 refuses that route.

#### The candidate shape, and one concrete price

`boat.dev` (by ASCII, YC-backed) was the operator's reference point, read
2026-09-21. It is representative of the category rather than a selection:
persistent Ubuntu VMs, SSH/SCP, Docker inside, snapshot + disk-level fork,
per-second billing, CLI + HTTP API + Python/TS SDKs, `--json` on every command.
Published price **$0.036/hour** for 4 vCPU / 8 GB against a **$20/month minimum**
(≈555 hours); 100–2,000 concurrent sandboxes by plan; **EU-only regions**
(Germany, Finland, France); default TTL 1 hour, overrideable; sandboxes can be
created `no-env` so they carry none of the account's secrets. Peers named on
their own comparison page: E2B, Daytona, Modal, Vercel Sandbox, Cloudflare,
Codespaces, Runloop, Freestyle, Blaxel, Novita, exe.dev, Islo.

**These figures are the vendor's own marketing claims, read once and unverified
by us.** They are recorded to make the order of magnitude concrete — the monthly
floor is a rounding error against one seat of lane spend, so **cost is not what
makes this hard.**

#### What actually makes it hard — and what a future ADR must answer

1. **It is a new execution boundary, and the kernel has none today.** Every
   primitive runs in-process under the caller's grant. A sandbox is the first
   place where *arbitrary code runs on a member's bytes*, so the whole of
   ADR-405's grant model has to be re-asked in a context it was never written
   for. This is the real cost, and it is not measured in dollars.
2. **Render parity breaks.** CLAUDE.md fixes three services and states *"all
   execution is inline: no worker, no Redis."* An external sandbox is a fourth
   execution home and the first one outside Render. ADR-417 decommissioned
   `yarnnn-render` precisely to stop paying for a standing service; re-adding one
   needs to answer why this is not that mistake repeated. (Per-second billing on
   an ephemeral VM is a genuinely different shape from a standing service — but
   the argument has to be made, not assumed.)
3. **Data residency becomes a stated property.** Member bytes would leave
   Supabase for a third party in a named jurisdiction. Today the workspace's
   answer to "where is my data" is one sentence; this makes it two.
4. **Attribution must survive the boundary.** ADR-209 says every mutation is
   attributed and parent-pointered through `write_revision`. Work done inside a
   sandbox has to come back as an attributed revision by a named principal, not
   as an anonymous blob — and the sandbox is outside the process that holds the
   grant.
5. **Sandbox output is untrusted input.** Anything returning from it is data,
   never instruction, and must not reach a lane frame as though it were
   substrate.

#### The trigger to revisit

Not cost, and not capability envy. **A member asking, more than once, for
something that needs execution** — recompute this sheet, OCR this scan, give me
this back as a deck. Until then the am.1 D9 marker is the honest answer: the file
is retained, it is not yet readable, and the product says so.

⭐ **Recorded so it is not re-derived, and not so it is picked up.** The cheap
half (§8.2–8.4) ships now and covers the observed feedback; the expensive half
has a named trigger and an ADR of its own when that trigger fires.

### 8.8 The click-pass (2026-09-21) — driven, and what it found

Four files dragged through the real Files door on a real workspace
(`bf5b25a9`), chosen so each exercises one decision:

| File | Before am.1 | Observed |
|---|---|---|
| `q3-forecast.xlsx` | **refused at the door** | raw + projection, 18 words, both sheets |
| `roadmap.pptx` | **refused at the door** | raw + projection, 16 words, slide + speaker notes |
| `acme-contract.docx` | accepted, **table+header silently dropped** | raw + projection, **22 words** — table rows and `ACME CONFIDENTIAL` present |
| `design.sketch` | **refused at the door** | raw (`application/octet-stream`) + **marker**, 0 words |

Receipts: the four `[DOCUMENTS] Uploaded` log lines (the `.sketch` one reading
`(marker, 0 words)` after `[EXTRACT] … retained-not-consumable (sketch) —
marking`), and the landed `workspace_files` rows read back — every projection
carrying `derived_from:` to its raw, the marker carrying its NOTE and no
fabricated content. Recents went 21 → 25 with type-aware glyphs per format; the
four `.extracted.md` siblings stayed hidden (ADR-554 D2). A `.sketch` opens to a
named, attributed, downloadable file with an honest "can't preview here" —
**D9's whole point: a file yarnnn cannot read is not a dead end.**

**⭐ What only the click-pass could find — the caption outlived the filter.**
The drop zone read **"PDF · DOCX · TXT · MD · ZIP 형식"**, a hardcoded
`files.upload.formats` string in both catalogs. D8 deleted the `accept`
attributes; nothing deletes a sentence. The door took every file while the
sentence beside it named five — and its sibling `agentsCanRead` ("Your agents
can read these files") became a false promise the moment a deferred format could
land. Both reworded: the caption states the real limit (**"Any file, up to
25MB"**), and the promise is scoped ("most formats… anything they can't is kept
in full"). No gate could see this: the strings are correct English and correct
Korean, they resolve, they render, and `tsc` has no opinion about whether a
sentence is true. This is the ADR-593 *fixing the picture leaves the caption*
class, on the door this amendment just opened.

**Also corrected**: `_BINARY_TEXT_FAMILY` in `machine_projection.py` still read
`{pdf, docx, doc}`. Its two new members were reachable only through the
`content is None` branch, which answers identically — so nothing was wrong
today, but a set whose whole job is to record *which formats must never have
their raw bytes emitted as text* cannot omit two of them and stay trustworthy.
Verified pre-existing and unchanged for `.pdf`/`.docx`: all four answer
`deferred` at that boundary, as they did before.

**Owed, and deliberately not built here**: a member sees the same "can't preview
here" for `.sketch` (which yarnnn genuinely cannot read) as for `.xlsx` (which it
now reads well). The distinction exists in the substrate — one has a marker, the
other a projection — and is not surfaced. That is a Files-viewer question, not an
intake one.

---

## 9. Amendment 1, D11 (2026-09-21) — a member can tell "unreadable" from "read fine"

> Operator-directed, closing the §8.8 "owed" item in the same arc.

### 9.1 The defect the click-pass named

`.sketch` and `.xlsx` both terminate at `DownloadTerminal` and, before this,
read **identically**: *"Preview not available inline · Open or download this
file…"*. That sentence is true of both and answers neither. The two files are in
opposite states — yarnnn cannot read the `.sketch` at all, and reads the `.xlsx`
perfectly well (D10) — and the member had no way to tell.

⭐ **The viewer was asked a question it cannot answer.** A renderer's question is
*"can I DRAW this?"*, and for every binary the answer is no. The member's
question is *"does my agent know what is in this file?"* — which is the
**derive-registry's** question, not the renderer's. Two different questions
wearing one sentence.

### 9.2 D11 — the server answers, the client renders

`readable_state()` in `api/services/documents.py` is the single resolver, beside
the registry it consults. Three values:

| Value | Meaning | Example |
|---|---|---|
| `read` | a projection exists and carries the file's words | `.xlsx` · `.pptx` · `.docx` · a text PDF |
| `unread` | retained in full; yarnnn cannot read it | `.sketch` · a scanned PDF · `.zip` |
| `native` | the file IS its own content — nothing owed, nothing missing | `.png` · `.mp4` · `.md` |

It ships as `FileResponse.readable`, decorated at `GET /api/workspace/file` by
`_readable_or_none`. **Same contract as `access` (ADR-643 D3): the server
decides, the client reads, and `None`/`undefined` means UNKNOWN — the viewer
then says nothing rather than guessing.**

**Why not in the client.** Deciding this in TypeScript means a second copy of
`registry_strategy` — and a second home for that rule is precisely the split
that let the upload door and the derive-registry disagree for months (§8.1). The
gate asserts the viewer consumes `file.readable` and **names no format**, so a
future session cannot quietly rebuild the registry there.

**The marker is the discriminator.** A projection and a D9 marker are both
`.extracted.md` rows citing the same raw; what separates them is the marker's
`NOTE:` token. That token is `_MARKER_TOKEN`, held beside the writer that emits
it, and the gate feeds `_deferred_note()`'s **real** output through the resolver
rather than inventing marker text of its own — a gate that writes its own
fixture passes while the real writer drifts.

**The conservative default.** No projection in hand → `unread`. Telling a member
their agent can read a file it cannot is the failure that matters; the reverse
is merely modest.

**Cost**: one indexed lookup on a path that is a pure function of the raw's
(`upload_projection_path`), and only for a file that could owe a projection —
prose, images and media answer `native` without touching the database. The
decoration never raises: a failure degrades to `None`, never to a 500 on a read.

### 9.3 Driven

Resolver over the six real files from §8.8: `.xlsx`/`.pptx`/`.docx` → `read`,
`.sketch` → `unread`, `.png`/`.md` → `native`. In the browser, the two files
that read identically yesterday now say opposite and true things —
*"에이전트가 이 파일의 내용을 읽을 수 있어요"* on the `.xlsx`,
*"그대로 보관했어요 — 다만 이 형식은 아직 에이전트가 읽지 못해요"* on the
`.sketch`. A `.png` routes to the image viewer and never reaches this line, so
`native` adds nothing by construction.

Gate: `test_adr395` **54/54** (5 new arms), falsified four ways — the marker
token stops discriminating · no-projection defaults to `read` · the viewer
re-derives from a format name · the route drops the decoration. ADR-660 47/47,
voice 0, affected set 97/97, `next build` exit 0.

### 9.4 Also corrected — the blueprint disagreed with the services it describes

Verifying "does `python-pptx` reach both services" found `render.yaml`'s cron
block wrong in two ways against the LIVE `crn-d604uqili9vc73ankvag`: schedule
`*/5` where live runs `*/1`, and **no `buildCommand` at all** where live has
always carried one. Nothing was broken in production — both services deploy from
the repo on `main`, not from the blueprint — but a redeploy *from this file*
would have produced a scheduler with no dependencies installed. Both reconciled.

The dependency question itself is **closed with a receipt, not an inference**:
both services run `pip install -r api/requirements.txt`, and both build logs
show `python-pptx-1.0.2` installed on `d5c3ac5`. ⭐A build command is not proof
that a package installed; the build log is.

---

## 10. Amendment 1, D12–D13 (2026-09-21) — the terminal shows the words, and opens the door

> Operator question, from a screenshot of a `.pptx`: *"how do we render or even
> not-show that which we don't have a dedicated render or preview for?"*
> (The screenshot's own error was a dead local dev server — `ContentViewer`'s
> generic network branch, not a format fault.)

### 10.1 Neither render nor hide — a third answer

**Hiding is wrong on this ADR's own terms.** ADR-621 fought to make a binary
answer as a real file: found, typed, sized, attributed, fetchable. A member who
uploaded a deck must see it exists and get it back. An empty screen would
recreate the "32 files reported as empty" defect from the other direction.

**Rendering is premature.** Drawing `.docx`/`.xlsx`/`.pptx` in-browser means a
heavy client-side parser or an image-conversion service — the latter being the
sandbox §8.7 just scoped and declined. And it buys a picture of content we
**already extracted the text of**.

> **Amended by §11.2 (am.2, 2026-09-23).** This paragraph put two different
> things in one sentence. An image-conversion service IS the §8.7 sandbox and
> stays declined. A client-side parser is not: it runs deterministic code the
> member's own browser already trusts, over bytes the member already holds, and
> crosses no execution boundary. "Premature" was a demand judgment, and the
> demand arrived. D15 builds the viewers; the projection preview (D12) stays as
> the honest fallback wherever a renderer cannot draw a file.

⭐ **The third answer: we cannot DRAW your deck, so we show what it SAYS.** The
projection is already sitting beside the raw. Serving it is the honest preview —
no parser, no conversion service, no sandbox.

### 10.2 D13 — the panel that gives the instruction gets the door

`DownloadTerminal` read *"Open or download this file to inspect it"* and offered
**neither**. Download lived only in the Files right-click menu and Properties,
neither reachable from the panel giving the instruction. **Advice without a
door** — the same shape as the ADR-427/510 defect where a null resolver meant
the menu entry simply did not render.

The button routes through `resolveDownload` — the ONE resolver, shared with the
menu and Properties, which spans the text and CAS lanes and carries the
substrate's own filename. Rebuilding the href here is precisely the bug that
module exists to fix, so the gate asserts the terminal calls the resolver and
never reaches for `blobUrl`. Minted object URLs are revoked on unmount.

**Also deleted: `needsBlob`.** Declared on `AppRegistration`, set on all eight
rows, and **read by nothing** — every renderer decides for itself through
`useSignedBlobUrl`. ⭐A field every row must keep correct and no code consults is
a fact waiting to go stale.

### 10.3 D12 — the extracted text rides the file read

`GET /workspace/file` already fetches the projection row to answer D11, so its
text returns with the verdict rather than costing a second round trip:
`projection_preview` + `projection_truncated` beside `readable`.

Three decisions worth recording:

- **The header is stripped.** A projection opens with `derived_from: <raw>` and
  a `# <filename>` title — both written for the reference edge (ADR-448), both
  noise to a member looking at that very file. ⭐The stripper stops at the first
  real line rather than FILTERING `# ` lines, because a heading lower in the
  document is content: filtering would silently delete a deck's slide titles.
  The gate asserts exactly that.
- **Only a `read` file carries one.** `unread` carries none — its NOTE is
  already the sentence the viewer shows, and serving it as a "preview" would
  print the same fact twice. `native` carries none: the file is its own preview.
- **Bounded at 4000 chars**, cut on a paragraph break when one is near the end.
  A 200-page PDF's projection has no business inflating every file read; the
  whole text stays reachable through recall and the sibling row.

### 10.4 Driven

`.pptx` → download button + "이 파일의 내용" showing the slide text and speaker
notes; the download resolved **200 OK** through the shared resolver.
`.docx` → the contract's **table and header visible to the member** — the exact
content the pre-am.1 extractor silently dropped, which closes the loop on the
feedback that opened this amendment. `.sketch` → button, and **no preview
section**, because there are no words to show.

Gate `test_adr395` **60/60** (6 new arms), falsified four ways — the stripper
filters every `# ` line · the preview is served for every verdict · the terminal
loses its download · `needsBlob` returns. The D11 route arm was **re-cut, not
routed around**: it pinned the exact call spelling, which D12 changed while
making it more correct (the ADR-658 am.4 lesson — a gate that pins prose loses an
argument with the product); it now pins the mechanism. ADR-660 47/47, voice 0,
affected set 98/98, `next build` exit 0.

### 10.5 The topic closes here

Inbound office formats are done: the door takes everything (D8), nothing is
silently dropped (D9), xlsx/pptx/docx are read correctly (D10), the member can
tell readable from not (D11), sees the words (D12) and can save the file (D13).

**Still deliberately not built**, each with its reason above: no round-trip
editing · no outbound `.docx`/`.pptx` writer (ADR-417 §2b) · no Google Drive
(a connector question; ADR-131 sunset the Google tools — read why first) · no
visual/thumbnail preview and no sandbox (§8.7, with a named trigger).

> **Amended by §11 (am.2, 2026-09-23)** — the topic re-opened on demand. Visual
> preview (D15) and the outbound writer (D16) are now BUILT; round-trip editing,
> Google Drive and the sandbox remain not built, with their reasons unchanged
> (§11.6).

---

## 11. Amendment 2 (2026-09-23) — the format harness: office files, first-class

> Operator-ratified from beta-member feedback: *office files (docx/pptx/xlsx)
> must be handled first-class.* This is a **demand gate firing**, not a
> reversal — every item below was named in §8.5/§10.5 as "not built, until
> asked", and it was asked.

### 11.1 What am.1 built, and what it deferred

Am.1 shipped INBOUND only: the door takes every file (D8), nothing is dropped
(D9), xlsx/pptx/docx are read (D10), a member can tell readable from not
(D11), sees the extracted words (D12) and can save the file (D13). It declined
four things: (a) visual viewers (§10.1), (b) an outbound writer (ADR-417 §2b),
(c) round-trip editing, (d) a sandbox (§8.7). Am.2 builds (a) and (b) and keeps
(c) and (d) declined.

It is delivered in three phases, and this amendment is the contract all three
build against:

| Phase | Builds | Reads from this amendment |
|---|---|---|
| 1 (this commit) | the format registry, the served fields, HWP/HWPX, the `.doc` fix | — |
| 2 | client renderers for `spreadsheet` / `wordprocessing` / `presentation` | D15's kind names |
| 3 | the outbound writer (a new attributed revision), then its skill | D16's `export_as` |

### 11.2 The distinction §10.1 missed — rendering is not the sandbox

§10.1 declined in-browser rendering by pairing it with the image-conversion
service in one sentence, and then declined both for the sandbox's reasons.
They are different acts:

| | Client-side parser (am.2 builds) | Conversion service / sandbox (still declined) |
|---|---|---|
| Where it runs | the member's browser | a server yarnnn would operate or rent |
| What it executes | deterministic library code shipped in the bundle | arbitrary conversion, or arbitrary code |
| Execution boundary | none new — the same trust as every other component | a new one (§8.7's first cost) |
| Render parity | unchanged | a fourth execution home (§8.7) |
| Data leaves Supabase | no — bytes already in the member's hands | yes |

None of §8.7's five costs attach to the left column. What §10.1 correctly
observed — that a picture of a deck buys less than its words — still holds as a
FALLBACK, and D12's projection preview stays exactly where it is for any file a
renderer cannot draw. The Render API stays `runtime: python` native; no Docker,
no LibreOffice (out of scope, and it would BE the conversion service).

### 11.3 D14 — ONE format registry, kernel-owned

**The defect.** Format knowledge lived in five hand-kept copies that had each
drifted:

| Deleted | Where | What it was |
|---|---|---|
| `_TEXT_FORMATS` · `_PASSTHROUGH_FORMATS` · `_DEFERRED_FORMATS` | `primitives/extract_text_from_blob.py` | the derive-registry verdicts |
| `_ZIP_EXT_MIMES` + the `_EXT_MIMES` literal + concrete `_CONFORMS` rows | `content_types.py` | MIME + conformance |
| the `extract_text` if-chain | `documents.py` | the parser table |
| `IMAGE_TYPES` + `upload_mime` | `documents.py` | **dead** — no caller remained |
| `_MIME_EXTS` | `routes/documents.py` | MIME → ext, already missing xlsx/pptx |
| `_BINARY_TEXT_FAMILY` | `machine_projection.py` | "text family, binary bytes" — still listing `doc` |

⭐ **The drift was already live**: `_TEXT_FORMATS` listed `doc` while the
parser behind it (python-docx) cannot open an OLE `.doc` at all — one table's
row claiming what another table's parser could not do. That is §8.1's split
(the door and the registry disagreeing) at a smaller scale.

**The decision.** `api/services/file_formats.py` holds `FORMATS`: one frozen
`FileFormat` row per format —

```python
FileFormat(exts, mime, base, projection, view,
           extractor=None, zip_container=False, export_as=())
```

— and every reader derives from it: `content_types` builds its extension,
zip-container and conformance tables from the rows; `registry_strategy` reads
`projection`; `extract_text` calls the row's `extractor` (no row, or no
extractor, is utf-8 text); `machine_projection` asks `is_binary_text_family`
(a text projection AND a byte parser — derived, so it cannot omit a member);
the upload route asks `ext_for_mime`. `registry_strategy` MOVED here from the
primitive, and its four importers were updated — no alias left behind.

**Why its own module and not `content_types.py`.** A row carries its extractor,
a callable in `documents.py`; the byte-sniffing module must stay a pure
function with no service dependency. The import runs one way: content_types →
file_formats → documents, whose module scope imports nothing from `services`.

**What stays client-side, deliberately.** The React component that draws a
view kind (ADR-436's `APPS` table): the server names the KIND, never the
component. And `FileIcon` / `NodeDetailsPanel`'s "Kind" labels: presentation
for tree rows that are never fetched, covering formats the registry does not
declare (`.xls`, `.ppt`, `.doc`), with no capability riding on them.

**Behaviour preserved, with three deliberate exceptions**: `.doc` (D17), the
Hancom pair (D18), and `.markdown` (now an alias of `md`, so it is read rather
than marked — it was simply never listed). Newly declared MIMEs (`tsv`, `avif`,
`bmp`, `ico`, `m4v`, `mkv`, `avi`, `flac`, `aac`) derive to their real types
where they previously fell back to `text/markdown` or `octet-stream`; each was
already drawn by the client under the same kind.

### 11.4 D15 — the view kind is SERVED; the client's guess is held to it

`GET /workspace/file` serves `view` beside `readable` — the same contract as
`access` (ADR-643 D3) and `readable` (D11): the server decides, the client
reads, `None` means the registry does not declare the format.

**View kinds declared now** (phase 2 builds the renderers):

| Format | `view` | Named after |
|---|---|---|
| `.xlsx` | `spreadsheet` | OOXML `spreadsheetml` |
| `.docx` | `wordprocessing` | OOXML `wordprocessingml` |
| `.pptx` | `presentation` | OOXML `presentationml` |
| `.hwp` · `.hwpx` · `.zip` | `download` | the terminal (projection preview shows) |

Every other declared format serves the kind the client already used
(`markdown`, `html`, `image`, `video`, `audio`, `pdf`, `csv`, `text`).

**The client.** `resolveViewerApplication(path, contentType, served?)` in
`web/lib/file-types/index.ts` returns the served kind when it is a known
`ViewerApplication`, and otherwise falls back to its extension rules.
`resolveApp` / `resolveApps` (`apps.tsx`) and `describeViewerApplication`
take the same third argument; `FileBody`, `FileMeta`, `ContentViewer`,
`ArtifactCard` and `ArtifactThumb` pass `file.view`. A kind with no registered
renderer resolves to `download.terminal` — so declaring the office kinds before
phase 2 changes nothing a member sees today: those files still reach the
terminal and its extracted-words preview.

**Why the client keeps an extension fallback at all.** Tree rows, the context
menu's Open With and thumbnails resolve a kind WITHOUT fetching the file. The
fallback is therefore a cache of the registry, and a cache drifts (ADR-658
am.5: a mirrored constant needs a gate arm that reads the ORIGINAL). The gate
**executes** the TS function (sucrase-transpiled, as ADR-571's probe does) for
every extension the registry declares and asserts the pre-fetch guess equals
the served kind — a file cannot draw one way in a tree row and another once
opened. Building it found one: `.hwp`/`.hwpx` resolved to `text` before a
fetch; both joined the client's binary terminal list.

**Also deleted: `viewerNeedsBlob`** — exported, called by nothing; the am.1
`needsBlob` finding, one file over.

### 11.5 D16 — the outbound writer's contract: `export_as`, per file

`GET /workspace/file` serves `export_as: ExportTarget[]` — the formats THIS
file can be written as. Per FILE, not per format: a Slides deck and a blog post
are both `.html`, and only the deck can become a `.pptx`, which the file's own
declared type (`data-template`, ADR-459) decides.

A row declares `export_as=(ExportTarget(to, when_app=None), …)`; `when_app`
narrows a target to an artifact whose type is owned by that app (ADR-473
`kinds_for_app`). Declared today:

| Source | Targets |
|---|---|
| `.md` / `.markdown` | `docx` |
| `.html` / `.htm` | `docx`; `pptx` when the artifact's type is owned by `slides` |
| `.csv` | `xlsx` |

`[]` = none; `null` only when the decoration failed (the client offers no
"save as", and never guesses one). **Every target must be a format yarnnn
reads back** — the gate asserts it — so an export never mints a file that
immediately takes the "cannot read" marker.

**What phase 3 builds against this**: an in-API library (python-docx /
python-pptx / openpyxl, already dependencies — ADR-417 §2c's "a library, not a
service") that writes the target as a NEW attributed revision through
`write_revision`, `derived_from` the source (DP32 — the export cites what it
was made from, and ADR-554's derivation edge follows it). Member-facing
"save/download as", reading `file.export_as`; and agent-reachable. **Skills
come after tools**: a skill for the writer lands only once an agent actually
holds the capability — an imported skill instructing an act the agent cannot
perform fails silently (am.1 §8.4's `xlsx` skill lesson).

**ADR-417 §2b's demand gate is recorded as fired** (a note there points here):
its own ruling was *"if downloadable export returns, it returns as an in-API
library call, never as a standing deployed service"* — which is exactly D16.

### 11.6 D17 — `.doc` stops claiming readability

`doc` leaves the text family. python-docx cannot open the OLE `.doc` format, so
every `.doc` went to a parser that always failed and then to the D9 marker,
while the registry said it was readable. It is now an undeclared format:
deferred, marked, downloadable — the registry no longer overstates. Legacy
`.xls`/`.ppt` were never declared and are unchanged. (The operator ruled `.doc`
reading itself not worth building; this is the truth fix only.)

### 11.7 D18 — HWP and HWPX, in-process

Beta members include Korean teams, for whom Hancom's word processor is the
default document format. Both variants were cheap enough to build in-process,
so both are in:

- **HWPX** (`extract_text_from_hwpx`) — a zip of OWPML XML. Walks
  `Contents/section{N}.xml` in NUMERIC section order (`section10` after
  `section2` — string order is wrong, and the gate proves it), a paragraph's own
  `t` runs as one block, a table as TSV rows. A table sits INSIDE a run of its
  anchoring paragraph, so collecting every `t` under a `p` would print each
  cell twice; the walker treats nested content as its own blocks. Parsed by
  lxml with entity resolution and network access OFF — the gate feeds it an
  external-entity declaration and asserts nothing was fetched.
- **HWP 5.x** (`extract_text_from_hwp`) — an OLE compound file, read with
  `olefile` (pure Python, one new dependency in `api/requirements.txt`, which
  both the API and the scheduler install from). `FileHeader` bit 0 =
  compressed (raw deflate), bit 1 = password. Section streams are a flat run of
  tagged records; `HWPTAG_PARA_TEXT` (67) payloads are UTF-16LE with control
  codes: codes 1–9, 11–12, 14–23 occupy EIGHT units and are skipped (a tab, 9,
  is kept as `\t`), the rest one unit. Table cells are paragraphs too, so they
  read in document order. A password-protected or distribution-locked file has
  no readable body and returns EMPTY — the upload then takes the D9 marker,
  never a projection of noise.
- Both inflate under a 64 MB ceiling (`_MAX_INFLATED_BYTES`) — past it, a
  25 MB upload is a decompression bomb, not a document, and reads as empty.

Both declare `view: download`: no client renderer is planned, and the
projection preview (D12) shows the words.

⚠️ **Owed**: both fixtures are BUILT in the gate (an OWPML zip; a real OLE
compound file written byte-for-byte), because Hancom Office is not available to
this session. A click-pass with a Hancom-authored `.hwp` and `.hwpx` is owed
before this is called verified on real files.

### 11.8 What stays deferred, and why

- **Round-trip in-place editing** — an edit lands in the projection; the
  `.docx` is never rewritten. D16 writes a NEW revision from a SOURCE the
  member authored (md/html/csv); it does not rewrite an uploaded office file.
- **The sandbox** — declined, trigger unchanged (§8.7: a member asking twice for
  something that needs execution).
- **A conversion service / LibreOffice** — it would be the sandbox under another
  name (§11.2).
- **Legacy `.doc` / `.xls` / `.ppt` reading** — operator-ruled not worth it.
- **Finding, not fixed here**: `json`/`yaml`/`tsv` read `deferred` — a JSON upload
  takes a "cannot read" marker although its bytes are text. Pre-existing and
  unchanged by am.2 (the table preserved every verdict it did not rule on);
  now a one-token change in one row when someone rules on it.

### 11.9 Gate

`api/test_adr395_model_consumable_projection.py` **79/79** (60 → 79: 19 new
arms, plus the verdict matrix extended with `doc`/`hwp`/`hwpx`). Each new arm
was **proven RED by breaking the product in place**, twelve ways: `doc` back in
the docx row · the client's xlsx guess drifts · the served view loses to the
content type · the route drops the format fields · the HWPX walker prints
nested cells into the paragraph · HWP wide controls read as one unit ·
`_BINARY_TEXT_FAMILY` returns · `extract_text` re-grows an if-chain · HWPX
loses its zip-container flag · `pptx` offered for every `.html` · an export
target yarnnn cannot read back · an office extension literal outside the
registry. ⭐**The zip-container arm stayed GREEN on its first falsification**:
it was conditioned on the row's own `zip_container` flag, so deleting the flag
also deleted the assertion. Re-cut to name the zip formats independently.

Also re-cut, not routed around: `test_adr530_machine_projection.py` was RED
against a correct product twice over — D1b still asserted
`registry_strategy("xlsx") == "deferred"` (stale since am.1 D10), and three
arms read `page.tsx` / `route.ts`, renamed to `*.web.tsx` / `*.web.ts` by
ADR-661 (`d8b1542`), so the gate CRASHED and reported nothing. Now 26/26.
