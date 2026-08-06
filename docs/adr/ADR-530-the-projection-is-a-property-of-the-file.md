# ADR-530 — The projection is a property of the file, and the link has a machine address

**Status**: Accepted (2026-08-06, operator-ratified — the two open rulings in §6 were put to the
operator and both landed; the arc scope was set as *"proceed in full … streamline both docs and
code as per prior discipline"*).
**Date**: 2026-08-06
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A (system canon — real-operator-facing)
**Dimension**: Channel (Axiom 6 — how substrate crosses out to a reader that is not a browser) +
Substrate (Axiom 1 — what a file *is* to a machine)

**Conforms to (does not invent)**: **Derived Principle 34** (ADR-395) — *substrate crosses into a
model only as text or image, never as the raw container*; a format with no registered strategy is
**retained-but-not-yet-consumable, legibly marked, never silently dropped or fabricated**. And
**Derived Principle 32** (ADR-376) — the derive is an attributed act citing its raw. This ADR
adds no principle. It closes a **conformance gap** against principles already ratified, and fixes
the addressing question DP34 does not speak to.

**Amends**:
- **ADR-529 D2/D3** — the share boundary's representation work was right in shape and wrong in
  source: it serialized `artifact_content` (raw bytes) rather than a projection, so it satisfied
  DP34 only for formats that happen to already be text. §1.2 is the receipt.
- **ADR-513 D2** — the public projection's `artifact_content` field is **re-sourced**, not
  widened: what crosses is now the file's model-consumable projection rather than its raw
  container. For a `.md` file these are byte-identical; for `.html` they differ, and for an XLSX
  the old behavior was a DP34 violation.
- **ADR-512 D5** — the handle grammar gains its complement. `yarnnn://workspace/{path}` names a
  file **for a principal who holds a grant** and "carries no authorization"; a share link is the
  opposite case (authorization carried *in* the URL, holder has no grant). Two addressing needs;
  D5 answered one. This answers the other.

**Preserves**: ADR-513 D1/D3/D4 (the token is the capability; **member HTML renders exclusively in
`sandbox=""` and is never inlined**; dark means dark) · ADR-517 (grants govern) · ADR-404 (no
outbound A2A — this makes yarnnn's *inbound* face resolvable, it does not call out) · ADR-395 D2
(the swappable derive-registry is the one home for format variety).

---

## 1. Context — a real defect, found by the operator, in the arc that was supposed to fix it

### 1.1 The report

ADR-529 shipped and was verified on prod against a **`.md`** artifact. The operator then pasted a
**`.html`** share link into ChatGPT and got the same class of refusal the whole arc existed to
eliminate: *"I still can't access the shared document … the `/s/...` share endpoint isn't exposing
its content to external fetchers."*

### 1.2 The receipt, and the honest correction

Probed live 2026-08-06 on `https://yarnnn.com/s/-4xdTHS7RU2NHDQfd6Hav26Tynv86Non`:

- SSR **works** — the page server-renders, the title is honest (`document-copy.html — shared on
  yarnnn`), OG is correct, `noindex` is set. ADR-529 D3 is not at fault.
- And the artifact is **still unreadable**, because `artifact_kind == "html"` routes it into
  `<iframe srcDoc sandbox="">` — correct for humans (ADR-513 D3, and non-negotiable: there is no
  sanitizer) and **opaque to every non-browser reader**.
- Text visible to a fetcher, extracted by stripping the `srcDoc` payload:
  `"document-copy.html — shared on yarnnn · shared from My Workspace · read-only · Every change,
  signed · 12 changes · operator · View read-only"` — **chrome and attribution, zero document.**
- The markdown lane had the mirror defect: it fenced the raw container, so an LLM asking for
  markdown received `<!doctype html><style>:root{--ink:#1a1a1a}…` — safe, and useless.

**The prior session's verification claimed the defect was closed. It was closed for one kind and
not the other, because the check tested one artifact and generalized.** Recorded here because the
same error is in the *code*: §1.3.

### 1.3 The deeper finding — the kind space was never a kind space

`preview_share` derived kind from a **filename suffix**:

```python
out.artifact_kind = "html" if leaf.lower().endswith((".html", ".htm")) else "text"
```

So *everything that is not `.html` is asserted to be text* — a shared PDF, PNG, XLSX or ZIP all
fall through to `"text"` and their **raw bytes are emitted into a `<pre>`**. That is DP34's
diagnostic test failing verbatim: *"a path that hands a model the raw bytes of a
non-text/non-image container and assumes it is read … violates this principle."*

And it is DP33's category error in miniature — a *kind of thing* encoded as a **string test at one
call site** instead of read from **one dispatcher**. The iframe opacity is one symptom; the
suffix-sniff is the disease.

> **The reframe (operator, ratified)**: *"projection should be first class and property of the
> file itself."* Consumption-is-projection is not a share feature. Sharing is merely the first
> consumer that exposed the gap; MCP `open`, the markdown lane, uploads and every future binding
> want the same object.

## 2. The axiom (restating DP34 at the boundary, not adding to it)

> **A file's model-consumable projection is a property of the file, derived through one registry,
> never re-derived per consumer — and a capability link exposes it at an address the outside world
> can reach without being told how.**

## 3. Decisions

### D1 — Kind comes from the registry, never from a suffix test

`registry_strategy(file_type)` (`services/primitives/extract_text_from_blob.py`, ADR-395 D2 entry
1) becomes the **single dispatcher** for "what can a model do with this?", returning
`text | passthrough | deferred`. The share boundary calls it; no call site re-derives kind.

`html` joins `_TEXT_FORMATS` (with `htm`). It is the registry's natural next entry: additive, one
strategy per format-family, exactly the growth DP34 designs for.

### D2 — `html→text` is EXTRACTION, not sanitization — and the distinction is load-bearing

The projection strips markup to recover text. **This is not a sanitizer and must never be read as
one.** ADR-513 §1's finding stands unchanged: there is no HTML sanitizer in this codebase, and
member HTML is arbitrary HTML+JS.

The two are different acts with different outputs:

| | Sanitization (**we do not do this**) | Extraction (**this ADR**) |
|---|---|---|
| Output | *markup*, believed safe, to be rendered | *text*, never rendered as markup |
| Failure mode | a missed vector executes | a missed tag reads as prose |
| Trust required | high — it gates execution | none — nothing is executed |

`<script>` bodies, `<style>` bodies, comments and attributes are **dropped** (they are not the
document's prose); the remaining text nodes are joined with block-level structure preserved as
newlines. **Because the output is inserted only as text — never as `innerHTML`, never into a
`srcDoc`, never unescaped — a missed edge case degrades legibility, never safety.**

**The iframe is untouched.** Human rendering still goes exclusively through `sandbox=""` (ADR-513
D3). This ADR adds a *second, textual* channel beside it for readers that are not browsers. A
future session must not read this as permission to inline.

### D3 — Unhandled kinds are marked, never dumped

`deferred` → the boundary returns **no content** and says so:
*"This file type can't be previewed yet — open it in yarnnn to view it."*

This is DP34's anti-silent-drop clause, and it is what makes "any format at large" safe: an
unhandled format becomes a **known gap**, not a break and not a wall of bytes. It also
retroactively fixes the XLSX/ZIP/PDF cases that §1.3 was silently mishandling.

`passthrough` (images) needs no projection — DP34 says images are already model-consumable. v1
returns the honest marker rather than a fabricated text projection; the image's own delivery is
D6's named-deferred work.

### D4 — The share link's machine address: one resource, negotiated; one alias, declared

Derived from what the outside world *is*, not from preference:

**HTTP content negotiation is the native mechanism.** `Accept:` is how the web has always
expressed "one resource, many representations." Any agent that speaks HTTP correctly gets text
with no yarnnn-specific knowledge. Minting a *separate* URL as the primary answer would make a
representation into a second identity — the DP33 category error again (representation is data
about the *request*, not structure in the *namespace*).

**But agents in the wild paste; they do not negotiate.** The §1.1 receipt is the proof: ChatGPT
sent `text/html` and got what a browser gets. A mechanism nothing exercises is a mechanism that
does not exist. `llms.txt` became a convention precisely because it is *pasteable, guessable,
linkable* — a human can hand it to an agent deliberately.

Both are true, and they are not in tension — one is the protocol, the other the affordance over
it:

1. **`/s/{token}` is the one canonical resource**, negotiating on `Accept` (shipped by ADR-529
   D2, now fed the projection).
2. **`/s/{token}.txt` is an ALIAS, not a second resource** — same token, same capability, same
   revocation, same lifecycle. It carries `Link: <…/s/{token}>; rel="canonical"` so no crawler,
   cache or agent treats it as separate content.
3. **Discovery is declared, not guessed** — the HTML page carries
   `<link rel="alternate" type="text/plain" href="/s/{token}.txt">`. This is the convention the
   web already has and that this codebase already speaks (`.well-known/mcp.json`). We are not
   inventing a dialect.

**Why `.txt` and not `.md`**: the projection is DP34's **text** strategy. Naming it `.md` claims a
format guarantee the registry does not make — a PDF's projection is not markdown. `.txt` is honest
about what DP34 actually promises.

**A2A**: this does not breach ADR-404's deferral. Nothing calls out. It makes yarnnn's *inbound*
face resolvable by any future agent protocol, because a capability URL returning text on request
is the lowest common denominator every protocol can consume — and a future A2A binding resolves
the same address, exactly as ADR-512 D5 anticipated for `yarnnn://`.

### D5 — The walk is the BOUNDARY's editorial choice, not the file's property

**Operator ruling.** The file's projection is **content only** — a projection is what the file
*is* to a machine, and its authorship is not part of its text. The **share boundary** appends the
attribution walk, because demonstrating the moat on contact is ADR-513's editorial decision about
*that surface*, not a fact about the file.

Consequence worth stating: when the projection later becomes a stored substrate object (D6), it
stores content only, and every consumer that wants attribution reads it from the revision chain
where it already lives. No duplication, one source of truth.

### D6 — v1 derives on read; stored projections are the named scaling step

**v1 (this ADR): derive-on-read.** The boundary computes the projection per request through the
registry. Ships now, no schema, no migration, no backfill.

**Named, not built: the projection as a cited substrate object.** DP32/ADR-395's own pattern is a
derived file carrying `derived_from` — attributed, cacheable, traceable, computed once at write
and available to every consumer without recompute. That is the conformant end state and the
scaling answer for large files and hot links.

**The v1 must not foreclose it**, so the boundary calls **one function**
(`project_for_machine(path, content, file_type)`) that today computes and tomorrow may read a
stored projection. One seam, one swap.

This is also what makes ADR-512 D5's reserved `@{revision_id}` form reachable later: a projection
that is a substrate object can be revision-pinned; one computed inline cannot.

### D7 — What this deliberately does NOT do

- **No sanitizer** (D2) — and no loosening of the `sandbox=""` rendering path (ADR-513 D3).
- **No projection widening at the boundary** — the ADR-513 D2 field set is unchanged; one field is
  re-sourced.
- **No sub-part addressing** — an embedded figure inside a document is not individually
  addressable. Named as the composition step `derived_from` would carry; the operator scoped v1
  to text explicitly.
- **No image delivery over the share boundary** — `passthrough` is honestly marked in v1.
- **No `.txt` alias on the authenticated file plane** (operator ruling: scoped to `/s/` for v1).
  Extending it crosses the auth boundary and deserves its own deliberate yes.
- **No outbound A2A** (ADR-404).
- **No second extraction implementation** — if a strategy is needed, it lands in the registry.

## 4. Phases (each its own commit)

1. **D1 + D2** — `html`/`htm` join the registry; the extractor lands beside the existing ones;
   `project_for_machine` is the one seam (D6).
2. **D3 + the boundary re-source** — `preview_share` consumes the projection; deferred kinds are
   marked; the markdown lane stops fencing raw containers.
3. **D4** — the `.txt` alias, the canonical `Link` header, the `rel="alternate"` discovery tag.
4. **Gates + canon** — the ADR-530 suite with falsifiers; this ADR; ledger; `grants-and-reach.md`.

## 5. The one-line statement

**A file's projection is what it is to a machine — derived once through one registry, honest when
a format has no strategy yet — and a share link exposes it both the way the web asks (`Accept`)
and the way an agent pastes (`.txt`), so the outside world can read shared work without being told
how.**
