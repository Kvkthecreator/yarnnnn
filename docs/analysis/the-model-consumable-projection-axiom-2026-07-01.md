# The model-consumable projection: a candidate axiom for how substrate leaves to be read

**Date**: 2026-07-01
**Hat**: B (external developer of the system — analysis + a candidate FOUNDATIONS amendment for ratification). No canon edit and no code change in this doc; it is the discourse base a FOUNDATIONS Derived Principle 34 + conforming ADR would cite.
**Status**: Proposed axiom for operator (KVK) ratification.
**Spine**: the **egress/consumption** member of the perception→substrate→authoring→**consumption** cycle. It completes the triad DP27 (perception/input) · DP31 (citation/output-binding) · DP32 (ledger-intake/retention) with the missing fourth: **how a substrate object is delivered to a model that will read it.**
**Origin**: KVK, escalating the intake discourse to first principles: *"we need to take the discourse to almost a fundamental, axiomatic framing. It should start even outside YARNNN itself — the overall LLM handling, with considerations for future scalability. Can/will LLMs via MCPs receive URL links, access them, read them, other file formats — such that a pure MCP tool just referencing our URL upload actually 'works'? If not, then is the text derivation necessary, and thus handling the wide variety of file types (pptx, xlsx, images, zips, anything at large) all require a deeper level of consideration."*
**Receipts**: MCP spec claims verified against the MCP specification 2025-06-18 (`modelcontextprotocol.io/specification/2025-06-18/server/tools`); model-capability claims verified against Anthropic platform docs (Files API, PDF support) as of 2026-07. Cited inline. YARNNN-side receipts carried from [the intake discourse doc](dumb-intake-and-the-referenceable-raw-lane-2026-07-01.md).

---

## 0. The question, and the one-sentence answer

**KVK's question, exactly:** does the physics of how LLMs consume files through MCP allow a "dumb intake, reference the raw URL" architecture — or is text/image derivation forced, and therefore is format-handling a deep problem YARNNN must own?

**Answer, from the MCP spec + model capabilities, not from YARNNN's code:**

> A bare URL reference (`resource_link`) is **not** a reliable way to get a file's contents into a model. Across MCP hosts, only **inline text** and **inline image/audio bytes** are guaranteed to reach the model; a `resource_link` URI is fetched **at the host's discretion**, and a host **cannot** fetch an authenticated URL it wasn't built to auth against. Therefore: **text (and, for visual documents, image) derivation is FORCED by the protocol, not chosen by YARNNN.** The variety-of-formats problem does not dissolve — it **relocates** into a mandatory derive layer, which every serious LLM platform (including Anthropic's own) is obligated to own. So YARNNN must own a **derive-to-model-consumable-projection** layer; the raw is retained for portability and provenance, but **the projection is what interop serves.**

This is why the previous doc's "Piece B" (the derive step) is not a YARNNN implementation gap — it is a **law of the medium.**

---

## 1. Outside YARNNN: how a model actually receives a file (the physics)

Two independent channels, with different physics. This is the general LLM-handling layer KVK asked to start from.

### 1a. Through MCP — what a tool result can carry (MCP spec 2025-06-18)

A `CallToolResult.content[]` may hold exactly these item types (verbatim from the spec):

| Content type | What reaches the model | Bytes carried? | Reliability |
|---|---|---|---|
| `text` | inline text | n/a | **guaranteed** — every host renders text |
| `image` | **base64 bytes inline** + `mimeType` | yes | **guaranteed** where the host+model accept images |
| `audio` | **base64 bytes inline** + `mimeType` | yes | host+model-dependent |
| **embedded resource** (`type: resource`) | the resource's `text` **or** `blob` field, **inline in the result** | text: yes · blob: yes-if-host-passes-it | host-dependent (blob dropping observed in the wild) |
| **`resource_link`** | **a URI only** — spec: *"a URI that **can be** subscribed to or fetched **by the client**"* | **no bytes** | **NOT guaranteed** — fetch is host-discretionary |

The two load-bearing spec facts:

1. **`resource_link` is a pointer, not content.** The spec's word is *"can be"* fetched by the client — not *will be*. There is **no protocol obligation** for a host to fetch a `resource_link`, and *"Resource links returned by tools are not guaranteed to appear in `resources/list`"*. So a tool that returns a link to a YARNNN blob has **no guarantee** the model ever sees the file.
2. **The host is explicitly allowed to drop content it doesn't understand.** Spec security note: *"Clients SHOULD validate tool results before passing to LLM."* Hosts gate/drop unfamiliar content types — the "MCP resource content silently dropped" class of bug is the observable symptom (open-webui #24038, found in the wild).

**Consequence for the "reference our URL" thesis:** even the *best* case (`resource_link` to a public URL) is host-discretionary; the *actual* case (a signed, time-boxed, auth-scoped Supabase URL) is worse — a host that blindly GETs a URL **carries none of YARNNN's auth**, so the fetch 403s or expires. A bare-URL MCP tool does not reliably work, by construction.

### 1b. Through the model API directly — the conversion boundary still exists

Anthropic's own platform (as of 2026-07) is the strongest existence proof that even a frontier model has a conversion boundary, not "any format raw":

- **Native document blocks**: PDF (multimodal, reads text **and** visual elements <100 pages; text-only >1000; best-effort between), and images (JPG/PNG/GIF/WEBP).
- **Everything else requires conversion**: platform docs — *"For file types that are not supported as document blocks (.csv, .txt, .md, .docx, .xlsx), convert the files to plain text, and include the content directly."* And explicitly: *"Word and PowerPoint require conversion to PDF or plain text before submission."*

So even the model vendor that ships the most native file support **still converts** xlsx/pptx/docx to text/PDF before the model reads them. There is **no world** (2026) in which "hand the model the raw .pptx bytes and it reads them" is universal. The conversion is intrinsic to the medium.

### 1c. The invariant these two channels share

Both channels reduce to the same two model-consumable forms: **text** and **image**. (Audio is a third for audio-native models; irrelevant to documents.) A file is *usable by a model* iff it has been projected to text and/or image. Everything else — PDF, docx, xlsx, pptx, zip, arbitrary binary — is **not** a model input; it is a **container that must be projected first.** This is true through MCP and through the direct API alike. **It is a property of models, not of MCP or of YARNNN.**

---

## 2. The candidate axiom (stated as dully as DP32)

> **A substrate object is delivered to a model only as a model-consumable projection — text, or image. The raw is retained (portability + provenance, DP32); the projection is derived, attributed, and cites the raw (DP32's derive step). What a model reads is never the raw container; it is always a projection of it. Formats are handled by a swappable derive-registry, one strategy per format-family; a format with no registered strategy is retained-but-not-yet-consumable, never silently dropped.**

Two clauses, mirroring DP32's shape:
- **Retention is DP32's job** (raw in, immutable, attributed). This axiom does not re-litigate it.
- **This axiom governs egress**: the *only* thing that crosses the substrate→model boundary is a projection to {text, image}. The `resource_link`-to-raw path is a **best-effort optimization** layered on top for hosts that support it — **never the guarantee.**

The dullness is again the design (KVK's DP32 intuition, applied to egress): the rule has no opinion about what format entered — it says only that *consumption requires projection*, so every new format, every new host, every new model inherits the contract for free. The "variety of formats" scalability worry KVK raised is answered structurally: **variety is contained entirely inside the derive-registry**, which is the one place a format-specific reader ever lives, and it is swappable and additive.

### Why this is the missing member of the perception cycle

FOUNDATIONS already has three sides of a four-sided cycle:

| Member | Boundary it governs | Contract |
|---|---|---|
| **DP27** (Perception Field) | world → substrate (input) | reality enters only as attributed observation |
| **DP32** (ledger-intake) | the observation's **retention** | raw retained + attributed; derive separately + cite |
| **DP31** (citation binds to Source) | claim → world (output-binding) | a shipped claim binds to its real-world Source |
| **DP34 (this)** | substrate → model (**consumption**) | a model reads only a projection {text\|image}, derived + citing the raw |

DP27 is *how the world gets in*. DP32 is *how what got in is kept*. DP31 is *how what we say points back out*. **DP34 is how what we kept is delivered to the thing that reads it.** The cycle closes: perceive → retain → **project-to-consume** → cite. Without DP34, the cycle silently assumed "the substrate object is directly readable," which §1 proves false for every non-text format.

---

## 3. What this forces on YARNNN (the mapping back)

The general axiom lands on YARNNN's intake as three now-**non-optional** obligations (the "three pieces" of the prior doc, re-derived from the medium rather than from YARNNN's code gap):

1. **Retain the raw** (DP32 / prior-doc Piece A) — upload lands the raw blob, immutable, attributed, `content_url`. Portability + provenance. *Necessary but insufficient alone* — §1 proves a retained-only raw is not model-consumable.
2. **Derive the projection** (DP34 / prior-doc Piece B) — a downstream, attributed, citing act projects the raw to {text, image}. **This is FORCED** — it is the only thing a model can read. For text-bearing formats (pdf/docx/txt) the projection is text; for visual documents it may be text+image. This is the derive-registry's job.
3. **Serve the projection over interop; offer the raw as best-effort** (prior-doc Piece C, now correctly demoted) — `recall`/`trace` serve the **text projection** (guaranteed to reach the model). A `resource_link`/embedded-blob to the raw is an **optional enhancement** for hosts that fetch it, never the primary path. The "Dropbox-referenceable raw" ambition is real but is the *garnish*, not the meal — because the medium won't guarantee it.

**The correction to the prior doc:** Piece B is not "the load-bearing half we happen to need"; it is **protocol-mandatory**. And Piece C is not "the bigger ambition" — it is a **best-effort optimization that can never be the guarantee**, so it must never be built as if a raw reference substitutes for a projection.

### The derive-registry (named, scoped minimally per KVK)

The architecture is a **swappable derive-registry** — the mirror image of the output gateway (`render/skills/`, which goes text→pptx/xlsx/pdf); intake needs the same registry going **the other way** (blob→{text\|image}). One strategy per format-family, resolved by MIME/extension, each producing a model-consumable projection + a `derived_from` citation to the raw.

**First implementation scope (minimal, honest):**
- **Text-bearing → text**: `pdf` (pypdf2, already in `documents.py`), `docx`, `txt`, `md`, `csv`. These we already extract; the change is *re-homing* extraction downstream as a derive act, not new capability.
- **Image → image**: pass-through (already model-consumable as base64).
- **Named-but-deferred registry entries** (add on demand, not now): `xlsx` (→ text table or rendered image), `pptx` (→ per-slide text + optional slide images), `zip` (→ expand, then recurse the registry per contained file), scanned/visual PDF (→ page images for multimodal), audio (→ transcript). Each is a registry entry with a known strategy shape; none is built until demand proves it.
- **Unknown format**: **retained-but-not-yet-consumable** — the raw is kept (DP32 honored), a projection is absent, and the file is *legibly* marked "no reader yet" rather than silently dropped or fabricated. This is the axiom's anti-silent-drop clause and the graceful-degradation path that makes "anything at large" safe: an unhandled format is a *known gap*, not a *break*.

The scalability answer KVK asked for: **the format space is unbounded, but the contract is fixed and the handling is localized.** Adding pptx support is adding one registry strategy; it touches nothing else. The substrate model already carries blobs (`content_url`/`content_type`), so no schema work — the derive-registry is pure additive service code, format-family by format-family.

---

## 4. The proposed FOUNDATIONS amendment (for ratification)

**Candidate: Derived Principle 34 (v9.14) — the model-consumable projection.**

> **A substrate object crosses into a model only as a model-consumable projection (text or image); the raw container is retained (DP32) but is never itself the thing read.** Consumption requires projection: a model reads text and images, never arbitrary file formats (a fact of models — true through MCP's `text`/`image` content types and through the direct-API document boundary alike; a `resource_link` to the raw is host-discretionary and auth-blind, never a guarantee). The projection is a **derived, attributed act that cites the raw** (DP32's derive step, here made protocol-mandatory rather than optional). Format variety is contained in a **swappable derive-registry** (one strategy per format-family, the intake mirror of the output gateway); an unregistered format is **retained-but-not-yet-consumable, never silently dropped or fabricated.** The **consumption** member of the perception cycle — DP27 (input) · DP32 (retention) · DP31 (output-binding) · **DP34 (consumption)**. Full derivation: [the model-consumable-projection analysis](../analysis/the-model-consumable-projection-axiom-2026-07-01.md) + MCP spec 2025-06-18 + Anthropic Files/PDF platform docs.

**What it changes in canon:**
- **New DP34** as above; version → **v9.14**.
- **DP32 gets one cross-reference sentence**: its "derive step" is, for any non-text raw, *mandated* by DP34 (not merely permitted) — retention alone never yields a consumable object.
- **No Axiom 1 sub-clause** — this is derived from Axiom 1 (substrate) + Axiom 6 (Channel — egress is a Channel concern) + the empirical medium; it is a Derived Principle, not a new primitive truth. (Same call DP32's analysis made for itself.)
- **No schema change** (blobs already storable via `content_url`).

**What it does NOT touch / explicitly preserves** (the dull-rule dividend): no change to DP27/DP31; no change to the topology (raw still lands in the `inbound/` lane per DP32, or as a `revision_kind` observation post-keystone); no new authorization vocabulary; **no format engine baked into the kernel** — the registry is service-layer and additive, so the kernel stays format-blind. The axiom's simplicity produces the saving: a kernel that says "consumption = projection" needs no per-format machinery of its own.

---

## 5. Open decisions for KVK (before the FOUNDATIONS edit + the conforming ADR)

1. **DP number + altitude** — ratify as **Derived Principle 34** (v9.14), derived from Axiom 1 + Axiom 6? Or does "how substrate is consumed" rise to an **Axiom 6 (Channel) sub-clause** (egress is *the* Channel act)? *(Lean: DP34 — it's derived from Channel + the empirical medium, not a new primitive; mirrors DP32's own "DP not axiom" call.)*
2. **Name** — *"the model-consumable projection"*? Alternatives: *"projection-for-consumption,"* *"the read-projection contract."* *(Lean: keep "model-consumable projection" — it names the constraint, models-read-projections-not-containers.)*
3. **Registry home + first strategies** — confirm the derive-registry is the mirror of `render/skills/`, first scope = {pdf, docx, txt, md, csv → text; image → pass-through}, with xlsx/pptx/zip/audio as named-deferred entries? *(Lean: yes — re-home existing extraction downstream, defer the rest to demand.)*
4. **`resource_link`/embedded-raw over MCP (Piece C)** — ratify as an explicit **best-effort enhancement**, sequenced as its own ADR, never a substitute for the text projection? *(Lean: yes — and its own ADR, touching ADR-379 host-profiles: a host that provably fetches+auths can receive the raw; others get the projection. Host-profile-gated, exactly like the widget-rendering gate.)*
5. **The `.md`-viewer + naming cosmetics** (orthogonal, ship-now) — the frontmatter-renders-as-body-text bug + generic `document.md` naming are independent of all of the above and can ship immediately. Confirm they're split out. *(Lean: yes — don't block small fixes behind the axiom.)*

---

## 6. Recommendation

1. **Ratify DP34** as the consumption member of the perception cycle. It is the axiom KVK's question demands: it starts outside YARNNN (the model/MCP medium), is transport- and format-agnostic, and future-proofs by containing all format variety in one swappable registry.
2. **Re-frame the intake ADR around DP34**: the center of gravity is *the derive-to-projection step* (protocol-mandated), with retention (DP32) as the floor and raw-reference-over-MCP as an explicit best-effort garnish. This corrects the prior doc's "raw referenceable at large" from *primary path* to *optimization*.
3. **Build the derive-registry minimally**, re-homing existing extraction downstream as the first strategies; defer xlsx/pptx/zip/audio to demand; make unknown-format a legible retained-not-consumable state, never a silent drop.
4. **Sequence Piece C (raw-over-MCP) as a host-profile-gated follow-on ADR**, not part of the conformance ship.

The dividend, if DP34 lands: the "any format at large" scalability worry is **structurally bounded** — the kernel stays format-blind, the medium's text/image constraint is honored by construction, an uploaded pptx is a retained raw + a text projection + a cited derivation, and the moat's provenance story (`trace` raw↔projection) holds across every format YARNNN will ever ingest. The dumb intake KVK wants is real; the medium just proves the "smart" half (projection) is not optional but foundational — so we name it as canon rather than rediscover it per format.
