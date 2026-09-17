# ADR-623: The Lane Can See What It Reads — Internal Parity for Workspace Images

> **Status**: **Accepted + Implemented** (2026-08-31). Drafted by KVK + Claude.
> **Date**: 2026-08-31
> **Dimension**: **Channel** (Axiom 6 — what a principal can perceive of the substrate) primary; **Substrate** (Axiom 1) untouched — no new storage, no new capability, one already-minted capability finally redeemed.
> **Relates to**: [ADR-621](ADR-621-a-binary-file-is-not-an-empty-file.md) (the external half — whose success created the asymmetry this closes), [ADR-427](ADR-427-binary-native-substrate-and-the-storage-seam.md) §8 + D4 (the binary notice, and the minted serving URL), [ADR-467](ADR-467-app-residency-and-the-cast.md) D4 (one tool surface, every lane), [ADR-411](ADR-411-chat-lanes-and-the-lane-tool-surface.md) (the lane contract), [ADR-395](ADR-395-model-consumable-projection-and-upload-intake-conformance.md) (DP34 — a model reads text and images).
> **Gate**: `api/test_adr623_the_lane_can_see.py` (42/42 — §8 is the 2026-09-17 amendment).
> **Amended**: 2026-09-17 — §8, *the lane can place what it is handed*.

---

## 1. Context — the Editor said it could not see, and it was right

Observed live in the chat surface, 2026-08-31. A member asked the Editor about a
PNG sitting in `marketing/assets/`. It answered:

> *"`ReadFile` confirms the file exists (PNG, ~2.5MB) but its bytes are served
> out-of-band to a viewer — my tools don't get pixel access to a workspace path
> like that. The only way I can actually look at an image is if it's attached
> directly in this conversation."*

**Every word was true, and none of it should have been.** The engine was
vision-capable (`LANE_MODELS[...]["vision"] is True`). The bytes were in the CAS
(2,585,846 of them, byte-verified). And `_mint_cas_url_for_path` — which mints a
serving URL **from a workspace path** — sat one module away, called from exactly
one place: the loop over the member's own attachments.

The agent reasoned correctly from what it was given. The ADR-427 §8 notice it
received ends:

> *"Its bytes are served out-of-band — text tools cannot read them. The file
> surface/viewer serves it via a minted URL."*

**A sentence that names a minted URL and hands over no way to obtain one.** The
lane surface has no fetch verb, so even putting the URL in the tool result would
have been one more step to nowhere.

### 1a. The asymmetry that made this urgent

[ADR-621](ADR-621-a-binary-file-is-not-an-empty-file.md) shipped hours earlier
and gave the **external** MCP surface a working `content_url` on `open`. So a
third-party agent on claude.ai could fetch those bytes, while the **first-party**
Editor, inside our own product, could not.

**External must never be better than internal.** That inversion is the whole
reason this ADR is not a backlog item.

## 2. The one-sentence decision

**A tool read of a viewable image ends in the model seeing the image: the tool
result stays the honest text notice, and the pixels arrive beside it as a vision
message minted through the same seam the member's attachment already uses.**

## 3. D1 — the pixels ride a `user` message, not the tool result

`image_part_for_tool_result(auth, model, name, result)` (`services/lane_runner.py`)
promotes a binary `ReadFile` into:

```python
{"role": "user", "content": [
    {"type": "text", "text": "[Contents of photo.png — the file you just read]"},
    {"type": "image_url", "image_url": {"url": "<minted, ~1h, object-scoped>"}}]}
```

**Why not the tool result.** A `tool` message carries a string. Putting the image
there means base64 — the thing [ADR-621](ADR-621-a-binary-file-is-not-an-empty-file.md)
D2 refuses on measured evidence (Box: corrupted at 175KB, failed at 20MB, because
*"non-deterministic LLM inference can subtly alter characters within the base64
data"*). The content-parts protocol carries images on user/assistant turns; that
is the one shape that can hold them, so that is the shape used.

**Why the text part names the file.** An unlabelled image in a turn that read
several files is ambiguous — the model cannot say which one it is looking at.

**It refuses more than it accepts**, and every refusal is gated: not `ReadFile`,
a failed read, a text file, a non-image binary (a PDF is binary and not viewable),
and an engine whose own `LANE_MODELS` row says it cannot see. A turn that cannot
show the picture proceeds with the notice it already had — **vision is an
enrichment, never a precondition**.

`image/svg+xml` is deliberately **absent** from `VISION_IMAGE_TYPES`: an SVG is
text, so `ReadFile` returns its source, which is strictly more useful to a model
than a rasterization it cannot edit.

## 4. D2 — vision survives the turn (it did not, and silently)

The parts array is deliberately **not** persisted — a signed URL has a 1-hour TTL,
so storing one would rot. But `_fetch_history` also did not select the
`attachments` metadata, so replay dropped the fact entirely:

> A member attaches an image on turn 1, gets an answer about it, and by turn 5
> the model has **no trace it ever existed** — not even the filename. It cannot
> know it has forgotten, so it answers from the surrounding text as though it
> had seen the picture.

**The path is durable; the URL is not.** So history replay now re-mints from the
stored path. The capability is minted per-request either way (ADR-427 D4) —
which is precisely why nothing durable should hold one.

A file that has since moved or been deleted is **named** in the replayed text
(*"an image attached earlier … is no longer available"*), never silently dropped:
"I can no longer see it" is a different answer from never having been shown it.

## 5. D3 — one path→URL resolver, at the seam

Three callers had grown three spellings of the same walk (path → head revision →
blob sha → minted URL), and **they had already drifted**: two passed
`workspace_id` to the mint and one did not. `storage_backend.mint_serving_url_for_path`
is now the single resolver; `routes/lanes.py::_mint_cas_url_for_path` is a
one-line delegation kept for its name at the attachment door.

Authorization is the **scope filter on the path read** — a caller only resolves
files its own `(user_id, workspace_id)` scope reaches; `workspace_id` then
narrows the blob lookup as defence in depth.

`mcp_composition.mint_binary_url` is **not** merged into it: it takes a
`blob_sha` already resolved by `resolve_binary_head`, so routing it through the
path resolver would re-run a query it has already done. Different input, not a
duplicate walk.

⚠️ The first cut of this had `services/lane_runner.py` importing from
`routes/lanes.py` — a layering inversion, and the only one in the codebase.
Moving the walk to the seam removed it; the gate asserts it stays removed.

## 6. D4 — the notice no longer dead-ends

The ADR-427 §8 message now states what is true and what follows:

> *"Binary file (image/png, 2585846 bytes) — it has bytes, not text, so there is
> nothing to read here. This is NOT an empty file. If your engine can see
> images, the picture itself follows in the next message — look at it there
> rather than asking for it to be attached."*

The viewable-type list is **imported from the lane's own declaration**, never
re-spelled, so the notice cannot promise pixels the lane will not send. The
sentence is conditional on the engine because the primitive does not know which
engine is calling — and over-promising to a blind lane would rebuild the dead end
one layer up.

## 7. Consequences

- A lane agent on a vision engine can look at any workspace image by reading it.
  No re-attachment, no member ceremony.
- Internal parity with the external MCP surface is restored.
- One resolver instead of three drifting spellings; one fewer layering inversion.
- Gate: 24/24, falsified four ways — promotion dropped from one loop, a
  non-vision engine promoted anyway, the history re-mint reverted, the resolver
  re-duplicated.

### What this does NOT do

- **No new lane verb.** The surface stays 14 tools (ADR-467 D4). Seeing is a
  property of reading, not a separate act — a `ShowImage` verb would be a second
  way to do what `ReadFile` already does.
- **No PDF/video rendering.** Non-image binaries keep the honest notice; their
  text projection (ADR-395) is the model-consumable form.
- **No image OUTPUT change.** `GenerateImage` is unchanged; it still cannot take
  a source image, so image-to-image editing remains unbuilt.

### Found while gating

- ⭐ The promotion wiring was **silently lost** mid-build (a later edit
  overwrote it) and the production probe still passed, because the probe called
  the promoter directly rather than through a loop. Assertion 3a — *both* loops
  promote — caught it. A helper that is correct and uncalled is the failure mode
  a behavioural probe cannot see.
- ⚠️ `test_adr411_lanes.py::test_round_budget_is_bounded` was **RED at HEAD**,
  pinning the word `"exhausted"` from a cap message rewritten earlier the same
  day. Re-anchored to the behaviour (the turn ends at the cap and says so in
  member-legible words). A gate that pins a spelling goes red on a copy change,
  and a red gate stops being read — which is exactly how ADR-621's defect
  survived.

---

## 8. AMENDMENT 2026-09-17 — the lane can PLACE what it is handed

### 8.1 The defect — the same asymmetry, in the other direction

This ADR fixed a **read that could not end in seeing**. It left standing a
**seeing that could not end in a write**.

A pasted screenshot has been a real workspace file since ADR-555 A2: the
composer uploads it to `inbound/uploads/chat/` *before* the turn is sent, and
the member sees it chipped on their own message. But `_build_turn_message` handed
the model the **pixels** and never the **path**. Observed live, the Editor lane:

> "I can't save images you paste into the chat. My write tools (`WriteFile`,
> `GenerateImage`) create text files or AI-generated images from a prompt;
> there's no path for me to take a pasted screenshot and drop it into the
> filesystem as-is. … you'd need to upload them through the workspace's own
> upload/Downloads flow — once they land as files, I can then read them and move
> or rename them into that folder."

Every clause is what a model with no path would conclude, and the last one
**describes a move it could have made that turn**. The files were in Downloads.
`MoveFile` was on its surface, carries a binary by re-referencing the head blob
(the 2026-08-27 fix), and drags the `.extracted.md` projection sibling with it
(ADR-554 D1). Nothing was missing but the sentence naming where the bytes were.

⭐⭐⭐ **And §1's asymmetry repeated verbatim.** The same member, on the same
workspace, through the MCP connector, saved the same screenshot to
`marketing/assets/screenshots/` in one turn — because that surface names paths.
External must never be better than internal. That it recurred within three weeks
of this ADR closing it says the rule needs a gate, not a principle.

⭐ **The FILE branch had always named its path.** Only the image branch dropped
it, because the pixels feel like the whole message. A per-kind branch is where a
shared fact goes to be stated once and forgotten once.

### 8.2 A2 — one note, both kinds, both entrances

`_attachment_note(path, name, kind)` in `api/routes/lanes.py` is the single
spelling of *where this attachment already is*. It is called from the live turn
(`_build_turn_message`, both branches) and from the replay (`_fetch_history`) —
because the path must survive the turn for exactly the reason §4 says the pixels
must. A lane that can move an attached picture on turn 1 and not on turn 5 has
forgotten half of what an attachment is.

The note states the fact and names the verb; it does not instruct the model how
to feel about it. No new tool, no new capability, no new storage — `MoveFile`
already did all of this.

### 8.3 Found while gating

- ⭐ **A latent hole in §4c.** The vanished-attachment branch rebuilt `parts[0]`
  from the **original** `text`, and the tail fell back to bare `text` when no
  image minted. So with exactly **one** vanished attachment the "no longer
  available" notice was composed and then **thrown away** — the model was
  silently back to answering as if it had never been shown a picture, the exact
  defect §4 exists to prevent. With two, the second overwrote the first. §4c
  passed throughout, because it greps the source for the string. Clauses 8i/8j
  assert the composition instead.
- ⭐ Clauses 8a–8f **drive** `_build_turn_message` rather than read it. A note
  asserted by grep is a note that can be spelled into a docstring and never
  reach a model — which is how the image branch lost its path in the first place.

Falsified: the image note removed (8b/8c red) · the helper re-duplicated per
branch (8g red) · the replay reverted to pixels-only (8h red) · the vanished
notice rebuilt from `text` (8i/8j red). Six of ten proven RED at HEAD before the
fix; 8a/8d/8e/8f are the regression guards on the half that was never broken.
