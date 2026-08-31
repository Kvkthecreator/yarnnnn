# ADR-621: A Binary File Is Not an Empty File — and the Connector Says So

> **Status**: **Accepted + Implemented** (2026-08-31). Drafted by KVK + Claude.
> **Date**: 2026-08-31
> **Dimension**: **Channel** (Axiom 6 — how the substrate is served to a foreign principal) primary; **Substrate** (Axiom 1 — what persists) secondary, and unchanged: this ADR adds no storage capability.
> **Relates to**: [ADR-427](ADR-427-binary-native-substrate-and-the-storage-seam.md) (binary-native substrate — §8's read-side rule is what this enforces; D4's minted URL is what it serves), [ADR-543](ADR-543-the-interop-surface-speaks-the-kernel-verbs.md) / [ADR-545](ADR-545-the-interop-binding-completes-edit-delete-move-changes-honest-save.md) (the file-native verb surface this repairs), [ADR-373](ADR-373-workspace-as-binding-unit.md) D6 (the incorrect-success class), [ADR-574](ADR-574-the-view-is-not-the-file.md) (`complete_for_write`, the field this ADR stops lying), [ADR-510](ADR-510-one-binary-lane-and-the-portability-export.md) (one binary lane), [ADR-395](ADR-395-model-consumable-projection-and-upload-intake-conformance.md) (Piece C — amended here).
> **Amends**: ADR-395 Piece C (the deferral's rationale is re-grounded on measured evidence and the piece is CLOSED, not merely deferred).

---

## 1. Context — the connector reported 32 files as empty

A marketing session produced video and image assets and tried to file them into
the workspace through the MCP connector. The transcripts (`.md`) saved. The
binaries could not — `save` takes a `content` string. Reasonable so far.

Then the operator opened an image that was *already* in the workspace:

```
open("marketing/assets/chatgpt-image-aug-20-2026-at-10-26-47-am.png")
  → success: true, found: true, content: "",
    content_chars: 0, stored_chars: 0, complete_for_write: TRUE
```

The file holds **902,508 bytes** in the CAS (`cas/38/38e0a34e…`,
`content_type: image/png`, byte-verified by fetching the blob). The substrate was
entirely correct. The **read** was not: every machine-readable field said "empty
file", and the caller had no way to tell "empty" from "bytes I cannot
represent". That is the [ADR-373](ADR-373-workspace-as-binding-unit.md) D6
incorrect-success class, on the primary external read door.

Census at the time of the audit: **32 live binary files**, every one answering
this way. The word `binary` appeared **zero times** in the 1,840-line interop
composition layer.

### 1a. It was a data-loss door, not only a bad read

`complete_for_write` is ADR-574's field, and it means *"you now hold the whole
file"*. On a 902KB PNG it answered **true**. So a caller following the documented
read-before-write contract exactly — open, then save with the returned
`base_revision` — would write `""` over a binary head.

Every existing guard was structurally blind to it:

| Guard | Why it missed |
|---|---|
| ADR-545 D4 size guard | reads `content_bytes`, which is **0** for a CAS head (the bytes are in the blob, not the denorm), so `0 > 24000` is False |
| ADR-574 elision guard | keys on a marker comment only Studio artifacts carry |
| ADR-406 linearity | a *correct* CAS on the wrong content is still the wrong content |

The result would be an empty TEXT revision at the head of a binary chain — the
exact corruption ADR-427's own implementation notes record as **already fixed
once**, in `routes/documents.py`. The same class re-appeared at a different door
because nothing generalized the lesson.

### 1b. Root cause: a classification that did not move with its file

ADR-427 §8 built the guard that should have caught this — a CI ratchet requiring
every `.content` reader to be classified `binary-aware`, `safe-on-empty`,
`text-only-by-contract`, or `non-substrate`. `mcp_composition.py` was classified:

```python
"services/mcp_composition.py": "safe-on-empty",   # recall/compose: an empty body contributes nothing
```

**That was true when written.** The file then composed *supporting* context for
recall/trace, where an empty body genuinely contributes nothing. ADR-543/545 then
rebuilt the same file into `open` — the primary external read door — where an
empty body does not contribute nothing: **it is the whole answer.** The
classification never moved with the file's job.

Worse, the ratchet was **RED at the time of the audit** (4 unclassified readers,
4 stale entries for files migration 248 had deleted). A red ratchet stops being
read, so the stale reason survived unchallenged.

**The generalizable lesson:** this map classifies *what a reader does*. A reader
whose job changes must be **re-asked**, not inherited. A classification is an
assertion with an expiry date, and nothing was checking the date.

## 2. The one-sentence decision

**A binary file answers as a binary file — `found`, typed, sized, and fetchable
through a minted URL — and the text write door refuses it rather than destroying
its bytes; bytes cross the wire beside the control channel, never through it.**

## 3. D1 — `open` answers binary honestly, and `found: true` is correct

`resolve_binary_head(auth, abs_path)` is the single resolver. It discriminates on
**`workspace_blobs.storage_key`** — set by the CAS lane, NULL by the inline text
lane — and *never* on empty content, because a genuinely empty text file is a
real thing and must stay one. (The gate falsifies exactly this: an empty `.md`
must not be reported as binary.)

`open` returns:

```json
{ "success": true, "found": true, "binary": true,
  "content": null, "content_type": "image/png", "byte_size": 902508,
  "complete_for_write": false,
  "content_url": "https://…(≈1h, object-scoped)",
  "authored_by": "…", "history": [ … ] }
```

Three deliberate choices:

- **`found: true`.** The file exists, is addressable, and can be acted on — it is
  simply not readable *as text*. Contrast the ADR-588 folder branch, which
  returns `found: false` because a folder is not a file at all. Saying
  `found: false` here would trade one wrong answer for another and send a caller
  hunting for a file that is right there.
- **`content: null`, never `""`.** An empty string *is* the defect: it renders as
  an empty file in every consumer.
- **`complete_for_write: false`.** The load-bearing field. It is the signature a
  caller uses for "I hold the whole file", and answering `true` over bytes never
  sent is what made `save` a data-loss door.

Attribution and history ride the binary answer exactly as they do for text
(ADR-311 D3). A binary file has authorship like any other file, and provenance is
precisely what a plain storage connector cannot show.

## 4. D2 — the bytes ride a minted URL, beside the wire and never through it

`mint_binary_url` is the third caller of ADR-427 D4's `mint_serving_url`, after
the browser file surface and lane vision attachments. The capability is minted
per request, object-scoped, ~1h TTL; **nothing durable holds a live URL.**

**Why a URL and not the bytes** — this is the industry's settled answer, not a
local preference:

- MCP's control plane is not a data plane (ADR-427 §4a). Base64 inflates ~33%,
  the python SDK 413s at 4 MB, and practical host ceilings run 52KB–512KB.
- **Box shipped base64 first and measured it failing**: it "uploaded a corrupted
  file at 175 KB and entirely failed at 20MB", and named the decisive cause —
  *"non-deterministic LLM inference can subtly alter characters within the base64
  data."* **Bytes routed through a sampled token stream are not safe.** They
  replaced it with signed URLs so "no binary data enters the LLM context window".
- Dropbox's own MCP server: `CreateFile` is *"inline UTF-8 content up to 5 MB"*;
  downloads are *"a temporary, single-use download link"*. Notion: *"This tool
  does not fetch arbitrary URLs or return binary files. For larger or binary
  attachments, use the signed file URL."*

**`ResourceLink` and `ImageContent` were considered and REFUSED.** The MCP spec
permits both in tool results, but Anthropic's own MCP connector throws
`UnsupportedMCPValueError` on resource links (*"resolve resource links with your
MCP client before converting"*), and `ImageContent` requires base64 — the
corruption vector above. A plain JSON `content_url` field is strictly better: no
host can choke on it, and any code-executing host can fetch it. Adopt them only
when a host is *measured* to redeem them.

## 5. D3 — `save` refuses a binary head, and intent cannot override it

`save` writes text. A whole-file text save over a binary head replaces bytes with
text and destroys the file, so it is refused with
`error: "binary_file_not_writable"`, naming the type and size.

**`confirm_full_replace` cannot override it.** That flag means "I mean to replace
the whole file" — a statement about **intent**. This refusal is about
**capability**: the text lane cannot represent these bytes, so no version of this
write preserves them. An intent flag must never be able to confirm an
impossibility. (Same shape as ADR-574's elision guard, one step stronger: that
one is *unreadable* content, this is *unrepresentable* content.)

Both doors share **one** resolver. Two readers of one fact drift, and only one
stays honest — which is the whole history recorded in §1b.

## 6. D4 — `list` marks binary and reports the blob's true size

A listing is where a caller decides *which* file to open, so an unmarked `0`
sends it to open a file it cannot read and cannot distinguish from an empty one.
The head's blob is joined into the existing query — **one round trip for N
files** (the ADR-339 perception-economics rule), never a per-row probe.

## 7. D5 — binary WRITE through MCP stays closed, and ADR-395 Piece C is CLOSED

ADR-395 Piece C (host-gated raw reference + interop binary) was **deferred**
pending *"a live fetch-and-auth test against a real host… C is unblocked only
once that test passes for at least one host."*

**That test has now been run publicly, by Box, and it failed** (§4). The
deferral's original reasons included "no demonstrated demand", which the
marketing session retires — but the *medium* reason is stronger than the demand
reason ever was, and it does not expire. Piece C is therefore **closed on the
read side by D1/D2 above** (the raw reference now ships as `content_url`, ungated
because plain JSON needs no host capability), and **closed on the write side**:

- MCP tool **results** may carry base64; MCP tool **inputs** have no blob type at
  all — base64-in-a-string is convention, not spec. MCP's own File Uploads
  working group exists because of this asymmetry.
- yarnnn's MCP server is **remote streamable-HTTP** (Render). It cannot read a
  caller's local disk, so the stdio pattern (AWS, Azure, filesystem servers) is
  unavailable by deployment position.

**This is a refusal of a MEDIUM, not of a capability.** The substrate is fully
binary-native (ADR-427); the browser upload door writes 25MB documents and 100MB
media today; internal producers write bytes server-side (`GenerateImage` →
`write_revision(content_bytes=…)`). Nothing here forecloses a future
presigned-upload handshake — the shape Box, Notion and SEP-2631 converge on — and
§8 names it as the reserved next step.

**What a participant CAN do with a binary file today**: open it (typed, sized,
fetchable), list it, search it via its ADR-395 text projection, move, rename,
delete, and walk its attributed history. Only *writing its bytes* is closed.

## 8. Reserved — the presigned upload handshake (NOT built here)

Named so it is not re-derived from scratch: a `request_upload(path, content_type,
size)` verb minting a short-lived scoped **upload** URL, redeemed by whoever holds
the bytes (a host that executes code, a CLI, a browser), landing through the
existing `/documents/upload` pipeline — type derived from bytes, never
caller-declared. It needs its own ADR: it is a new capability class and a real
risk surface (a scoped write door into the commons), and Box ships its equivalent
**admin-gated and default-off**. Not in scope here.

## 9. Consequences

- A connected LLM can finally see the binary in a workspace it is a principal of
  — including artifacts internal agents authored, which read as empty before.
- One live data-loss path is closed, with `confirm_full_replace` explicitly
  unable to reopen it.
- The ADR-427 §8 ratchet is **green again** (48 enumerated, 48 classified) and
  `mcp_composition.py` is `binary-aware`, so this class of drift fails CI.
- `open`'s and `save`'s advertised descriptions state the binary contract, so a
  caller learns it at the door rather than from a refusal.
- Gate: `api/test_adr621_binary_is_not_empty.py` (19/19), falsified four ways —
  seam absent, `complete_for_write` reverted, the override re-enabled, and the
  discriminator changed to empty-content.
