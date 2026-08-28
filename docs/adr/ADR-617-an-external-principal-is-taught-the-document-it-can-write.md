# ADR-617 — An external principal is taught the document it can write

> **Status**: **Accepted + Implemented** (2026-08-28)
> **Amends**: ADR-533 D6 (what does NOT port to the external surface)
> **Builds on**: ADR-440 D5 (the artifact is a projection over living references) ·
> ADR-443 (cite by reference, never by copy) · ADR-512 (the file is the unit of interop) ·
> ADR-543/545 (the file-native verb surface) · ADR-574 §2b (closed 2026-08-28)

## 1. Context — the connector is the reference external principal

The MCP connector is not one integration among several. It composes its self-description
from the **same kernel constants the lane frame uses** (`PARTICIPANT_COMMONS_CONTRACT`,
`_READ_BEFORE_WRITE`, `_ATTRIBUTION_RULE`, `_FILESYSTEM_MODEL`), with the stated intent
that *"a participant is taught one contract whether it is a lane in the webapp or ChatGPT
across an OAuth token"* (ADR-533 D1), and its verbs bind kernel primitives through the
same `execute_primitive` door every internal caller uses (ADR-164/512 D3).

So whatever is true of the connector is the template for **every future external
principal** — A2A, direct-API, another vendor's host. This ADR takes that seriously and
asks the question it implies: *can an external principal understand, and safely edit, the
documents this workspace holds?*

For `.md` the answer was already yes — the Text app is markdown-native precisely to keep
the internal/external gap small, and `PARTICIPANT_FORMAT_DISCIPLINE` already says "prose
documents are .md". For `.html` artifacts the answer was **no**, and the gap was unstated.

## 2. What the evidence said

A live session (2026-08-28) read `operation/yarrnnnn-decl/deck.html` through the
connector and produced a confident, wrong reading of the document.

Measured on the artifact:

```
6 data-ref citations       — 0 resolved on the MCP path
slide 8's chart element    — <div data-ref="…/downturn-outcomes.csv"
                              data-ref-kind="chart"></div>   (inner: '')
the CSV it cites           — Era,Pct of Top 50 Companies Built in Downturn
                             Dot-com bust (2000–02),72  …     (never seen)
workspace-wide citations   — 11 total: 5 pinned, 6 floating
```

The session recommended leading with slide 8 — **a slide whose content it had never
seen** — inferring its quality from a `figcaption`. Nothing in the read was false; the
element was present and empty. The reader had no way to know that empty meant *projected
from a source*, because nothing had ever told it the form exists.

**This is the ADR-373 D6 incorrect-success class**, one layer above the one closed the
same day in ADR-574 §2b: `found: true`, content present, meaning absent. ADR-574's defect
was the body being unreachable; this one is the body being *legible and misleading*.

A second finding, from tracing the write path: the ruling *"never edit a cited object's
content inside the artifact"* is enforced in **three client-side layers** — citation
islands are `contenteditable="false"` (`projection.ts:2178`), the caret is fenced out of
them (`:2192`), and the commit serializer restores them from `data-src-html` before any
write (`readSourceInner`, `:2099-2108`). A human **cannot** make that edit. An MCP
principal can, silently: the substrate accepts it, attributes it, and shows it in history
while `el.innerHTML = csvToTableHtml(...)` (`:395`) overwrites it on every render. The
file and every screen disagree, permanently, with no warning on either side.

The deck already carries this defect: its `table` citation holds 704 characters of inlined
CSV rows — dead bytes, overwritten at each render. Its `chart` citation is correctly empty.
**The empty one is the system working; the full one is the anomaly.**

## 3. D1 — The connector is the reference implementation of an external principal

Ratified as a framing, because it decides where these fixes belong. A rule an external
principal needs goes in a **kernel constant both surfaces compose**, never in the MCP
package. The MCP server is where a rule is *rendered*, never where it is *decided*.

## 4. D2 — The in-document citation grammar PORTS (amending ADR-533 D6)

ADR-533 D6 listed what does not cross to the external surface: the workspace MANDATE, and
*"lane posture overlays, member/model interpolation"*. **The mandate half stands** — its
reasoning (workspace-specific intent must not leave the system into a third-party host's
context on every connection) is correct and untouched here.

But "lane posture overlays" was **one item covering two different things**, and the split
is the whole decision:

| | crosses? | why |
|---|---|---|
| A posture's **turn state** — the live outline, an inlined `_string.yaml` + `CONTRACT.md`, the design-system roster | **No** | workspace-specific, turn-scoped, and would cost a DB read per call |
| A posture's **format grammar** — how a document of this type is structured | **Yes** | not intent at all; the same class as `PARTICIPANT_FILESYSTEM_MODEL`, which always ported |

D6 grouped them on the wrong axis. Its own stated test is *"how the workspace works"
(kernel-universal, shared) vs *"what this workspace is for"* (specific, withheld). The
citation grammar is unambiguously the first.

**`PARTICIPANT_ARTIFACT_CITATION_RULE`** (`services/workspace_paths.py`) is therefore a
kernel constant, composed into the connector instructions beside its siblings. It teaches
the three consequences that matter: a cited element is usually **empty** and that is
correct; the source is **authoritative**, so never write into a citation; keep a citation
**whole**, pin included.

⚠️ It is deliberately distinct from `PARTICIPANT_CITATION_RULE`, and both are needed.
That one is `derived_from` — provenance *between* files, recorded on the write. This one is
`data-ref` — a live projection *inside* a document. Conflating them is exactly how a
participant "helpfully" pastes a CSV's rows into a deck.

**Not done**: calling a lane posture builder from the connector. Every one of the four
registered postures would leak or duplicate — `strings` inlines the member's declaration
and contract bodies, `studio` appends the design-system names and manifest paths, and
`text` echoes the entire document head back (duplicating the payload `open` is already
returning). The constant is the singular seam; the builders stay lane-side.

## 5. D3 — `open` names an artifact's citations

An unresolved citation is invisible in markup. `open` now returns a `citations` rider —
`{path, kind, pinned, projected}` per cited file — and states it in the `explanation` too,
because a host that renders only the sentence would otherwise show a document with holes
and no account of them.

**Paths, never resolved content.** Resolving them server-side would re-copy the bytes the
citation form exists to avoid, and would re-inline on every read what ADR-574's elision
just removed. The caller is told what it has *not* seen and can `open` the cited file —
one more exact read, under its own grant.

A marked `<style>` wearing `data-ref` is **excluded**: it carries the attribute as a
trace/dependents edge, not a projection (the renderer already refuses to resolve into one,
ADR-456 W3). Listing it would send a reader off to a stylesheet manifest.

## 6. D4 — The citation ruling reaches the write doors

Ported from the three client-side layers to the surface built after them. Two guards,
shaped by what each verb honestly knows:

- **`edit` — content-free.** Its contract is that content the client never read is never
  in the payload (ADR-545 D1), and it never fetches the file. So it compares its own
  anchors: a citation present in `old` and absent from `new` is the anchor cutting through
  an island — the same "a `data-ref` can't be halved" refusal the canvas makes.
  **Stated gap**: an `old` lying entirely *inside* an island's body, mentioning no
  `data-ref`, is not catchable here. That case is `save`'s.
- **`save` — span-aware.** It replaces the whole file, so it reads the head and asks
  whether its citations survive: a citation **dropped**, or one whose empty body has been
  **filled in** (the helpful-paste). Only for `.html`; degrades **open** on any read
  failure — a guard that cannot read must not block a legitimate save. It refuses *new*
  damage only, and does not demand a caller repair pre-existing state.

Both return the module's standard refusal shape (`success: false`, `error:
"citation_damage"`, a message naming the remedy — *edit the cited file*).

This required a span-aware parser, `citation_islands()`, placed beside the existing
`extract_data_ref_paths` in `authored_substrate.py` (paths only, which cannot answer
"where does this island end"). It is **not** an HTML parser and deliberately does not use
`lxml`: lxml is importable in the dev venv but **absent from `requirements.txt`**, which is
precisely how a serving path acquires an undeclared dependency. A depth counter answers
the one question asked, and degrades conservatively — an unclosed island reports its span
to the end of the content, making the guard stricter, never looser.

## 7. Consequences

**Positive.** An external principal is now taught the one document form it could
previously damage without knowing; it is told what a document cites and what it has not
seen; and the two write doors enforce a ruling that existed but had no reach here. The
`.md`/`.html` asymmetry becomes honest: Text is native because markdown *is* the format,
Slides is taught because HTML-with-citations is not self-describing.

**Costs, stated.** The connector instructions grow by ~1.4KB — paid once per connection,
against a class of silent corruption. `open` gains a regex pass over content already in
memory. And **the guards are not complete**: `edit` cannot see an anchor wholly inside an
island, and neither door repairs artifacts that already carry inlined citation content
(the live deck is one). Those are stated gaps, not assumed absences.

**Not done.** No `app_for_path` in Python. The `.md`→Text and `_string.yaml`→Strings claims
live only in `web/lib/file-types/index.ts`; the HTML derivation (`extract_template` →
`app_for_layout`) exists server-side and is what this ADR needed. Folding the two TS-only
claims into one Python site is the correct eventual home for a per-app external overlay —
owed, not built, because nothing here required it.

## 8. Key files

`services/workspace_paths.py` (`PARTICIPANT_ARTIFACT_CITATION_RULE`) ·
`services/authored_substrate.py` (`citation_islands`) ·
`services/mcp_composition.py` (`compose_open` rider, `_refuse_citation_damage`,
`_refuse_citation_loss_on_save`) · `mcp_server/server.py` (instructions + `open` schema) ·
`docs/features/mcp/tool-contracts.md`

Gate: `api/test_adr617_the_cited_document_crosses.py`

## 9. The one-line statement

**A surface that can write a document must be taught how that document works — the
citation grammar is how the workspace works, not what it is for, so it crosses.**
