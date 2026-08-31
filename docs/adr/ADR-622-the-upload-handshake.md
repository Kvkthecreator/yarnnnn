# ADR-622: The Upload Handshake — the Control Channel Mints, the Data Channel Carries

> **Status**: **Accepted + Implemented** (2026-08-31). Drafted by KVK + Claude.
> **Date**: 2026-08-31
> **Dimension**: **Channel** (Axiom 6 — how a foreign principal reaches the substrate) primary; **Substrate** (Axiom 1) untouched — this ADR adds a DOOR, not a storage capability.
> **Relates to**: [ADR-621](ADR-621-a-binary-file-is-not-an-empty-file.md) (the read half; §8 reserved exactly this), [ADR-427](ADR-427-binary-native-substrate-and-the-storage-seam.md) (binary-native substrate + D4's minted capability), [ADR-395](ADR-395-model-consumable-projection-and-upload-intake-conformance.md) (the upload pipeline this reuses; Piece C closed by ADR-621), [ADR-555](ADR-555-arrival-has-a-here.md) (a caller-supplied destination needs an authorization), [ADR-331](ADR-331-setup-as-rendering.md) D5 (the ONE upload endpoint), [ADR-512](ADR-512-the-file-is-the-unit-of-interop.md) D2 (one verb ontology, per-principal grants), [ADR-563](ADR-563-the-mcp-scope-authorizes-it-does-not-decorate.md) (verb scoping).
> **Migration**: `250_adr622_upload_tickets.sql` (applied 2026-08-31).

---

## 1. Context — a principal that holds bytes has no door

[ADR-621](ADR-621-a-binary-file-is-not-an-empty-file.md) made the connector
*honest* about binary: `open` names the type and size and hands back a minted
serving URL, and `save` refuses a binary head rather than destroying its bytes.
That closed the read half and a live data-loss path. It left the other half
open, and named it (§8, "Reserved"): **a principal that holds bytes still cannot
put them in the workspace.**

The substrate has never been the obstacle. It is fully binary-native (ADR-427):
the browser upload door writes 25MB documents and 100MB media today, and internal
producers write bytes server-side (`GenerateImage` → `write_revision(content_bytes=…)`).
What is missing is a door for a principal that is neither a browser session nor
an in-process producer.

**Why the connector cannot simply carry them:**

- **Bytes through a token stream corrupt.** Box shipped base64-over-MCP, measured
  it, and published the result: *"uploaded a corrupted file at 175 KB and
  entirely failed at 20MB"*, with the cause named — *"non-deterministic LLM
  inference can subtly alter characters within the base64 data."* This is not a
  size limit that grows out; the characters themselves change.
- **The spec has no input side.** MCP tool RESULTS may carry base64
  (`ImageContent`, `BlobResourceContents`); tool INPUTS have no blob type at all.
  MCP's own File Uploads working group exists because of this asymmetry.
- **Our server is remote.** `yarnnn-mcp-server.onrender.com` is streamable-HTTP
  on Render. It cannot read a caller's disk, so the stdio pattern (AWS's
  `aws s3 cp`, Azure's `--local-file-path`) is unavailable by deployment position.

## 2. The one-sentence decision

**The control channel mints a short-lived, single-use, destination-frozen
capability; a separate authenticated HTTP channel carries the bytes into the ONE
existing upload pipeline.**

This is not a local invention. Box (`get_upload_url`), Notion
(`create-file-upload` → `upload_url`), S3 (`s3_presign_put`), Microsoft Graph
(`createUploadSession`) and the in-flight SEP-2631 all converge on it: **the
control channel carries a handle; a separate authenticated channel carries the
bytes.**

## 3. D1 — the ticket is a ROW, not a signed string

A JWT-shaped ticket would have been fewer moving parts and is the wrong answer:
**statelessness is exactly what makes a token replayable.** Single-use is the
property that makes a write capability safe to hand out, and it cannot be
enforced without state. A row also revokes (delete it) and audits (who minted,
what it wrote), neither of which a signed string does.

`workspace_upload_tickets`: `token` (opaque, `secrets.token_urlsafe(32)`),
`user_id` (the owning human — the write is attributed to them), `minted_by` (the
principal string: provenance, **never** an authorization input), `destination`,
`filename`, `declared_bytes`, `expires_at` (1h, matching the ADR-427 D4 serving
URL), `redeemed_at`, `written_path`. **Service-role only, no user policy** — a
ticket is a secret, and listing secrets is the one thing no policy here should
permit.

## 4. D2 — the ticket points at a yarnnn endpoint, NEVER at a bucket

Supabase offers `create_signed_upload_url`, which writes straight into storage.
Using it would have been fewer lines and is **refused**, because bytes arriving
in a bucket bypass every guarantee the upload door provides:

| Bypassed | Why it matters |
|---|---|
| type derived from BYTES (ADR-427 D5) | the caller's declared type becomes trusted — a payload named `.md` |
| the size caps | 25MB doc / 100MB media unenforced |
| `write_revision` (ADR-209) | the single write path, skipped |
| attribution | no signed revision, no history |
| ADR-395 text projection | the file is never searchable |

Something would then have to reconcile the bucket with the substrate — **a second
intake path**, which CLAUDE.md's Singular Implementation rule forbids and which
would drift the moment either side changed. `POST /api/uploads/{token}` redeems
through `_process_single_upload`, the same function the browser upload calls.
**One pipeline, reached through one more door.**

## 5. D3 — authorization happens at MINT and is FROZEN into the ticket

ADR-555's finding: *"the moment a destination becomes caller-supplied it needs an
authorization."* Here the caller-supplied moment is the **mint**, so that is
where `operator_can_organize` runs — the same gate, on the same normalized path,
as the browser upload door, so the two cannot disagree about where a principal
may write.

**The redeemer then supplies bytes and nothing else.** Filename, destination and
owner all come from the ticket row, not from the redemption request. This is the
security property that makes a credential-less endpoint safe: a leaked ticket is
bounded to **exactly the one write its minter was already allowed to make**. Had
the destination been a request parameter, a leaked ticket would be a general
write door into the commons.

The redemption endpoint takes **no session**, deliberately: the whole point is
that the party holding the bytes (a CLI, a code-executing host, `curl`) is not
the party holding the workspace credential. The ticket *is* the authorization.

## 6. D4 — the claim is a compare-and-set, and the ticket is spent by the ATTEMPT

```python
.update({"redeemed_at": now}).eq("token", tok).is_("redeemed_at", "null")
```

A read-then-write loses the race: two concurrent redemptions both read
`redeemed_at IS NULL`, both proceed, and one ticket writes two files. The UPDATE
returns the row it actually changed — the same CAS discipline `write_revision`
uses for the revision chain (ADR-406) and `wake_queue` uses for its lock.

The claim happens **before** the bytes are processed. A claim-on-success would
leave a failed-midway upload replayable, which is precisely the window single-use
exists to close.

A failed claim names **which** of the three states it hit — unknown, already
redeemed (with the path it wrote), or expired. An opaque "invalid" would send a
caller retrying something that can never work (the ADR-373 D6 rule: name the
state).

## 7. D5 — `request_upload` is scoped `files:write`

Minting a ticket touches no file, and is still a write: the capability's whole
purpose is to land an attributed revision. Gating the ticket **below** the write
it authorizes would be a door around `files:write`. It is `SCOPE_WRITE`, beside
`save`/`edit`/`delete`/`move`.

**Rendering story** (ADR-533 D4): `TEXT_ONLY`, with a written reason. The result's
value is in being **run** — by the model where it can execute shell, by the user
otherwise — so it must be text both can read and copy. A widget would also imply
the host can perform the upload, which is exactly what it cannot do.

**The answer states its own limit.** A chat-only host cannot redeem the ticket,
so the explanation says so plainly and tells the model to hand the command over
rather than claim success. Box ships its equivalent gated to agentic hosts for
the same reason; we serve it to every host and let the answer be honest about who
can act on it.

## 8. Consequences

- A connected LLM can put a non-text file into the workspace for the first time —
  via a command it runs itself (code-executing hosts) or hands to the operator.
- The same ticket serves a CLI or plain `curl` with no MCP involved at all, which
  is the path that actually solves bulk local-asset upload.
- No second intake: one pipeline, one set of caps, one attribution story.
- **A stdio helper is NOT needed for this** and is not built. It remains an
  option for local-disk convenience on desktop hosts (ADR-621 §8 discussion), but
  it would redeem *this* ticket rather than replace it.
- Gate: `api/test_adr622_upload_handshake.py` (27/27), falsified four ways — CAS
  removed (**produced a real replay**), mint-time authorization dropped,
  destination unfrozen, verb scoped read.
- ⚠️ Found while gating: `test_adr563_mcp_scope_enforcement.py` parsed the verb
  roster with `[a-z]+`, so **any underscore-named verb was invisible to the scope
  gate** — it would have passed while `request_upload` shipped ungated. Widened
  to `\w`; the gate now sees all 11 verbs.

## 9. What this does NOT do

- **No resumable / chunked upload.** One POST, one file, capped at the existing
  100MB media limit. Graph's `createUploadSession` and Drive's resumable protocol
  exist for GB-scale files; nothing here forecloses adding one, and no demand has
  shown up for it.
- **No multi-file ticket.** One ticket, one file — the bound that makes a leaked
  ticket harmless. A batch would need its own reasoning about partial redemption.
- **No host gating.** Box gates theirs admin-side, default-off. We serve the verb
  to every host because the *answer* is honest about who can redeem it, and
  because the ticket's blast radius is one authorized write. Revisit if abuse
  appears.
