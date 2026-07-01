# ADR-395 — The Model-Consumable Projection: upload intake conformance (retain raw · derive projection · host-gated raw reference)

> **Status**: **Accepted** (canon ratified 2026-07-01 — **Phase 0 done**: FOUNDATIONS Derived Principle 34 landed at v9.14 + the DP32 cross-reference sentence). Phases 1–3 (code) remain to build. Ratifies **FOUNDATIONS Derived Principle 34** (the model-consumable projection — the consumption member of the perception cycle) and conforms the **human-upload** transport to it — the last context-in transport DP32 named but the code never fixed. **Substrate + Channel dimensions** (Axiom 1 — how an uploaded file is retained + derived; Axiom 6 — how a substrate object egresses to a model). Adds **one new primitive** (`ExtractTextFromBlob`), **one new capability flag** on the host profile, and **populates an existing-but-unused column** (`workspace_files.content_url`). Changes **no** existing write gate and **no** attribution taxonomy.
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

- **NEW primitive `ExtractTextFromBlob`** in `api/services/primitives/` — takes `{storage_path | content_url, write_to}`, reads the blob, runs the **existing** `extract_text()` (`api/services/documents.py:62` — pdf/docx/txt dispatch, *reused verbatim*), and `write_revision`s the **text projection** to a derived path with `derived_from: <raw inbound path>`, then `_embed_workspace_file`s it (the projection is the embeddable text — closes the searchability gap). Registers in `HANDLERS` + `HEADLESS_PRIMITIVES` + `FREDDIE_PRIMITIVES` (NOT `CHAT_PRIMITIVES` — same policy as `SyncPlatformState`/`CaptureConnector`).
- **Inline-mechanical trigger** (refined 2026-07-01, Phase-1 implementation) — the derive fires **inline in the upload request**, right after the raw-blob write, via `execute_primitive(auth, "ExtractTextFromBlob", …)`. Zero-LLM, deterministic, same request — so the file is searchable the instant upload returns (no scheduler lag). This **refines** the ADR's earlier "capture-lane hook" language: the ADR-393 capture *lane* is built for **scheduled/cadenced** captures declared in `_captures.yaml` (a recurring watch); an **upload is a synchronous one-shot**, so forcing it through the async scheduler would be a category error (a one-shot event dressed as a recurring declaration) and would open a search-lag gap between upload and derive. Both paths run the *same* `ExtractTextFromBlob` primitive (Singular Implementation) — the connector case invokes it from the capture lane on cadence, the upload case invokes it inline on arrival; the primitive is trigger-agnostic (it never reads the clock; `observed_at`/the raw path are caller-supplied). The derive is still **capture-*class*** in the ADR-393 sense (mechanical, wakes no one, zero-LLM); only its *dispatch home* is the request path, not the scheduler.
- **Registry seam** — `ExtractTextFromBlob` is the first entry of the **derive-registry** (D2). MIME→strategy: `{pdf,docx,txt,md,csv}→text`; `image/*`→pass-through (already model-consumable); `{xlsx,pptx,zip,audio}`→**named-deferred** (registry entries with a known strategy shape, built on demand — until then, **retained-but-not-yet-consumable**, legibly marked).

**NEW in B**: the `ExtractTextFromBlob` primitive (thin — wraps existing `extract_text`), its capture-lane registration, and the on-arrival trigger. **The extractor logic is reused, not rebuilt.**

### Piece C — host-gated MCP raw reference (the best-effort garnish)

- **`api/mcp_server/presentation/hosts.py:47`** — add capability flag to `HostProfile`: `can_fetch_signed_urls: bool = False` (sibling of the existing `renders_widgets` — same ADR-379 data-registry pattern). Set `True` only for hosts proven to fetch+auth (start conservative: none, or gate behind a verified profile). Add helper `can_fetch_signed_urls(host_id) -> bool` (mirrors `renders_widgets`, lines 127–152).
- **NEW service helper** `create_signed_url_for_storage_path(client, storage_path, expires_in=3600)` in `api/services/documents.py` — wraps the storage `create_signed_url` (today only inline in the HTTP route `routes/documents.py:321`). One hour expiry (matches the route).
- **`api/mcp_server/server.py:104` `_present()`** — when (1) the result references a file with `content_url` AND (2) `can_fetch_signed_urls(client_name)` is `True`, **append** a `resource_link` (or embedded `type:resource` with the signed URL) to `content[]` — *alongside*, never *instead of*, the text projection. When the gate is `False`, the model gets the text projection only (the guarantee). This exactly parallels the existing `_meta` widget gate (host-gated enhancement, text-safe default).
- **`api/services/mcp_composition.py:768–993`** (recall/trace) — surface `content_url` on the result chunk so `_present` can build the reference. Today recall/trace return `path`+`excerpt`; add the raw reference when present + gated.

**NEW in C**: the `can_fetch_signed_urls` flag + helper, the service-level signed-URL helper, the `resource_link` assembly in `_present`, and surfacing `content_url` through recall/trace. **All host-gated and text-safe by default — a host that fails the gate is unaffected.**

---

## 5. Implementation phases (the move-to-implementation sequence)

Ordered so each phase is independently shippable and search never breaks:

1. **Phase 0 — canon** (doc-only): ratify DP34 into FOUNDATIONS (v9.14) + the DP32 cross-reference sentence + this ADR to Accepted. *No code.*
2. **Phase 1 — A (retain raw)** + **B (derive projection)** together, because A-alone regresses search (a raw with no projection is unsearchable — the whole point of B). Migration/backfill: existing `uploads/*.md` (extracted-text) files stay valid; new uploads take the raw+projection shape. The FE Files-tree `uploads/`→`inbound/uploads/` move ships with this phase (or a compatibility alias during transition).
3. **Phase 2 — C (host-gated raw reference)**: the `HostProfile` flag (default-off for all hosts until one is verified), the signed-URL helper, the `_present` `resource_link` assembly. Ships dark (gate off) → enable per host as fetch+auth is verified. **Zero risk to non-gated hosts.**
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
