# ADR-529 — One share act, one link, two readers

**Status**: Accepted (2026-08-06, operator-delegated — the operator front-loaded the arc, ratified
the assessment's direction verbatim (*"this is what i had in mean"*) and delegated execution:
*"the approach details, from the docs and ADR handling, to sequencing commit push to main post
quick testing and validation, alongside any doc and code singular streamlining implementation
discipline and thus clean-up, delete legacy or dual approaches"*).
**Date**: 2026-08-06
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A (system canon — real-operator-facing)
**Dimension**: Channel (Axiom 6 — the doors a file travels through, and what a reader on the far
side of one actually receives) + Identity (Axiom 2 — who may reach what)

**Executes**: **ADR-515 D1/D2/D7** (the Share modal; the addressing/boundary carve; the Files
over-grant dying by construction) — ADR-515 sat `Proposed` since 2026-08-03 with no code moved,
and **ADR-517 D9 bullet 1** explicitly deferred the FE convergence to it. This ADR is that
execution, plus the two defects the execution surfaced that ADR-515 did not know about (§2).

**Amends**:
- **ADR-513 D3** — the public view's rendering discipline gains a **representation** axis. The
  projection (D2) is unchanged, byte for byte; what changes is that the same projection may be
  served as HTML *or* as markdown, chosen by the reader. §3 D2 states why this is a
  representation change and not a boundary change.
- **ADR-515 §2.0 / D1** — the two-mount carve is **preserved** (the header cluster keeps Share ·
  Export; the File card keeps the addressing verbs). What this ADR adds is that the *header*
  Share and the *File-card* Share are one component, not two — ADR-515 named the modal but not
  its singularity across mounts.
- **ADR-517 D5** — its named "dead defence, retires in the FE phase" (`shareKey()` in
  `NodeDetailsPanel.tsx`) is executed here. This is that FE phase.

**Preserves**: ADR-373 (the grant is the authorization fact) · ADR-378 (workspace outermost) ·
ADR-405 (species-blind) · ADR-513 D1/D2/D4 (the token is the capability; the narrow projection;
dark means dark) · ADR-514 D2.6 (the verb bundle is threaded whole) · ADR-517 (grants govern,
share executes — the backend floor is untouched by this ADR).

> **AMENDED 2026-08-06 by [ADR-530](ADR-530-the-projection-is-a-property-of-the-file.md)** — D2/D3
> were **right in shape and wrong in source**.
>
> Both served `artifact_content` — the file's **raw container** — so they satisfied DP34 only for
> formats that happen to already be text. Verified on prod against a `.md` artifact and declared
> closed; the operator then hit the *same class of refusal* with an `.html` share, whose content
> lives inside `<iframe srcDoc sandbox="">` and is opaque to every non-browser reader. The
> markdown lane had the mirror defect (it fenced `<!doctype html><style>…`).
>
> The deeper finding: `artifact_kind` was derived from a **filename suffix**, so every non-`.html`
> file was asserted to be text and a shared PDF/XLSX/ZIP had its **raw bytes emitted into a
> `<pre>`** — DP34's diagnostic test failing verbatim.
>
> ADR-530 re-sources both lanes from the file's **model-consumable projection** (one registry, one
> seam) and adds the machine address (`/s/{token}.txt`). **D1/D4/D5 — the ShareDialog, the four
> deletions, the hierarchy — are unaffected and stand.**

> **AMENDED 2026-08-07 by [ADR-534](ADR-534-the-share-link-is-a-standing-address.md)** — D1's four
> contents stand; their **order of authority** changes.
>
> D1 named the minted URL (item 2) and this file's active links (item 3) as separate tiers, and the
> implementation followed: a link minted ten seconds ago got a labeled field with a Copy control,
> while a link minted last week — the same object, still live, still resolving current content —
> got a footer row whose only affordance was **Revoke**. On a file that already had a link, the
> primary button read *"Create another"*, so the path of least resistance was duplication.
>
> ADR-534 makes the dialog **open on the link that exists** (reuse keyed on (path, role)), makes
> every listed link copyable, and makes a share whose file was moved or deleted go honestly
> **dark** rather than rendering a blank 200. **D2/D3/D5 are untouched.**

---

## 1. Context — the operator's report, and what was actually wrong

The operator's framing, which is the spine of this ADR:

> *"the current mechanism for share on files and studio surface is still not converged to a
> single mental model and thus front end handling (albeit they are different builds or
> components, the concept should feel the same for the user regardless of ANY surface), and i
> think that's a good rule of thumb."*

And, separately, on the artifact the link produces:

> *"is the existing share or can it be singular approach for BOTH humans AND llms (singular URL,
> accommodative to both). and thus, the current human visible surface seems to have too much
> weight on the attribution or log like information."*

Both reports are correct. The first was already diagnosed and ratified (ADR-515) and never built.
The second was not known, and its cause is not the one the symptom suggests.

### 1.1 The convergence gap — measured, three surfaces, three implementations

| Surface | Gesture | Role choice | Shows the URL | Shows existing links |
|---|---|---|---|---|
| Files (`files/page.tsx::handleShare`) | one click → mints **and copies** | **none — always `member`** | no | no |
| Studio (`StudioShareExport.tsx`) | outclick-dismissible popover | Full / View-only | no | no |
| Properties (`NodeDetailsPanel::FileShares`) | — | — | — | **yes, list + revoke** |

Three fragments of one act. None is complete; no two agree. Two consequences worth stating
because they are not cosmetic:

- **Files over-grants on every use.** No role parameter → `member` → the toast *"Share link
  copied — anyone with it can join the workspace"* reports a decision the operator was never
  asked to make. This is ADR-515 §1.1, still live.
- **Studio's own copy is false.** It says *"Manage or revoke shares from Files"*; management
  lives in the Properties panel. A surface pointing at the wrong surface is the tell that the
  act has no home.

### 1.2 The link defect — a receipted diagnosis, and the symptom lies

The operator pasted a live share link into ChatGPT and received: *"this appears to be a private
Yarnnn share link, so I can't view its contents … the server intentionally prevents anyone…"*

That reads as a permissions failure. It is not. Probed live 2026-08-06:

- `GET https://yarnnn-api.onrender.com/api/s/{token}` → **`200`**, full `artifact_content` +
  `walk`, no auth. ADR-513 works exactly as designed.
- `GET https://www.yarnnn.com/s/{token}` with a bot UA → the HTML contains **`Loading…`** and
  nothing else. The page is `"use client"` and fetches in `useEffect`
  (`web/app/s/[token]/page.tsx:83`).
- `<title>` is the generic marketing title; `og:url` is `https://yarnnn.com` — the landing card,
  not the artifact.

**So the model received a blank page and inferred a policy from it.** The refusal was a
hallucination over an empty shell. The link is public; it is simply illegible to any reader that
does not execute JavaScript — which is every LLM fetcher, every Slack/Notion/iMessage unfurler,
and every preview crawler.

> **The finding**: "share with a link" is true at the API and false at the URL. The public
> boundary ADR-513 opened is real, and nothing that reads the web can see through it.

A third, smaller defect found in the same pass: the page sets `robots: index, follow` and `/s` is
absent from `robots.txt`, while the API correctly sets `X-Robots-Tag: noindex`. ADR-513 D4's
capability discipline holds at the API and leaks at the HTML layer.

### 1.3 On "too much attribution weight" — the operator is right about the symptom, and the fix is hierarchy

The instinct to cut the walk should be **refused**, and the reason matters: the attribution walk
is ADR-513's entire thesis (*"the moat demonstrated on contact"*) and the one thing that makes a
yarnnn link different from a Google Docs link. Remove it and the surface is a worse Google Doc.

But the report is still correct, because the *layout* is wrong for the job: the artifact, the
walk, and the join card render as three peer cards of equal weight, so a reader's eye is asked to
treat "who changed this" as co-equal with "what this is." **The information is right; the
hierarchy is absent.** That is D5.

## 2. The axiom

> **One act, one component, every surface. One link, two representations, one projection. The
> artifact is what a reader came for; its attribution is the proof, not the payload.**

## 3. Decisions

### D1 — `ShareDialog` is one component, threaded through the verb bundle

A single `web/components/workspace/ShareDialog.tsx` is the **only** place a share is minted in the
cockpit. It mounts from the `FileVerbs` bundle (ADR-514 D2.6), so Files, the tree, the RecentsView
grid, the ContentViewer listing and Studio all inherit the identical act — the operator's rule of
thumb (*"the concept should feel the same for the user regardless of ANY surface"*) made
structural rather than aspirational.

It is a **modal**, not a popover: dismissible by choice (Escape / Cancel / the close control),
never by an incidental outclick. Granting is governance (ADR-517 §1.3); a governance act that
vanishes when the mouse slips is misreporting its own weight.

It carries exactly four things:

1. **The two shapes, stated as consequence** — Full access (*"they can work in your workspace"*)
   vs View-only (*"they see this file and its history; they cannot change it"*). **No default
   fires without a click**, which is what kills the Files over-grant (ADR-515 D7).
2. **The URL, rendered visibly** in a readable, selectable field with an explicit Copy control —
   the operator's *"even explicitly show the URL Link with clear buttons or displays … should be
   very up-front and center."* A link the operator cannot see is a link they cannot verify,
   re-copy, or reason about.
3. **This file's active links, with revoke in place** — so the operator sees what they have
   already handed out before handing out more.
4. **Nothing else.** Not the standing grant state (that is the rail — ADR-515 D2/D6, and
   duplicating it mis-scopes the dialog), not Export (ADR-515 D5 — the boundary must be
   impossible to confuse by construction).

**`Share…` no longer copies on click.** The word is reserved for the act that changes who can
reach the file (ADR-515 D1), and the act now always asks.

### D2 — One URL, two representations: content negotiation, not a second link

A reader that cannot run JavaScript gets the artifact as **markdown**; a browser gets the page.
**Same token, same capability, same revocation, same projection.**

- `GET /api/s/{token}` with `Accept: text/markdown` (or `?format=md`) returns the ADR-513 D2
  projection rendered as markdown: the artifact's content, preceded by a short header (name,
  workspace) and followed by the walk as a compact attributed list.
- The document body is **the same `artifact_content`**, subject to the same `PUBLIC_CONTENT_CAP`,
  drawn from the same service-client read.

**Why this amends ADR-513 D3 and not D2** — the distinction is load-bearing, because D2 states
that additions to the public payload must be deliberate. Nothing is added: the field set is
byte-identical to the JSON projection. What changes is the *serialization*. A representation
change carries no new information across the boundary, so the boundary is not moved. Stated
explicitly so that a future session cannot mistake this for a widening precedent.

**Why not a second link.** A `/s/{token}.md` sibling, an "AI link" beside a "human link", or a
second token class would each mint a second thing to revoke, a second thing to explain, and a
second thing to drift. The operator's question was *"can it be singular"* — it can, and content
negotiation is the mechanism that already exists for exactly this. (Note: `/s/{token}.md`
currently returns `200` as the Next.js catch-all 404 shell — a lie that this ADR also closes, by
making the suffix real via the `?format=md` route rather than leaving a soft-404 squatting a
plausible URL.)

### D3 — The `/s/{token}` page is server-rendered

The page fetches its preview **on the server** and ships the artifact in the initial HTML. The
client component survives only for the interactive shell (the accept action, the walk's
expand/collapse) — the read path is server-side.

Consequences, each of which is the point:

- An LLM fetcher, a Slack unfurler and a crawler all receive the document.
- `<title>` and OG tags are derived from the real `artifact_name` + `workspace_name`, so a paste
  into any channel shows what was shared rather than the marketing card.
- The page emits `noindex, nofollow` and `/s` is added to `robots.txt` — closing ADR-513 D4's
  HTML-layer leak. **A capability link must be legible to a reader who was handed it and invisible
  to one who was not**; those are not in tension, and today the page has them exactly backwards.

The error states (404 / 410 / revoked) render server-side too, so a revoked link is honestly dark
to a fetcher rather than an eternal `Loading…`.

### D4 — Deletions (Singular Implementation, and the whole point of the arc)

Converging without deleting would leave four ways to share instead of three. Deleted, not
deprecated:

| Deleted | Where | Why |
|---|---|---|
| The one-click mint-and-copy | `files/page.tsx::handleShare` | Replaced by the dialog. This is the over-grant. |
| The share panel + its two buttons + `runShare`/`sharing`/`shareState`/`sharedMode` state | `StudioShareExport.tsx` | Studio mounts the shared dialog. `StudioShareExport` keeps **Export only** and is renamed to match what it is. |
| The `FileShares` block (list + revoke) | `NodeDetailsPanel.tsx` | Moves into the dialog — the operator manages links where they mint them, not in a second surface. |
| `shareKey()` | `NodeDetailsPanel.tsx` | ADR-517 D5's named dead defence: paths are canonical-absolute at the write since migration 234. Executing the retirement it was promised. |
| The false *"Manage or revoke shares from Files"* copy | `StudioShareExport.tsx` | The surface it named was never the surface that managed shares. |

The `share` MCP verb, `createShare`/`listShares`/`revokeShare` in the API client, and every
backend path are **untouched** — one transport, now with one cockpit face.

### D5 — The public view is re-weighted: artifact dominant, attribution proven not paraded

The walk **stays** (§1.3). Its presentation changes:

- **The artifact is the page** — full width, dominant, the first and largest thing.
- **The walk collapses to one line** — a single attributed summary (*"3 changes · Researcher,
  Claude, you"*) that expands to the full list on click. The proof is present on contact, in a
  glance rather than a ledger.
- **The join card becomes a quiet footer**, not a peer column.

Same information, same projection, correct weight — the operator's *"minimal approach aside from
the content or artifact itself"* without giving up the thing the surface exists to demonstrate.

### D6 — What this ADR does NOT do

- **No backend authorization change.** ADR-517 is the floor and it is correct; this arc does not
  touch `assert_may_mint_share`, the RLS policies, the role model, or revoke authority.
- **No new transport, no second token class, no artifact-scoped access object** (ADR-513 D5,
  ADR-437 D4.3).
- **No projection widening** (D2) — the markdown representation carries the ADR-513 D2 field set
  and nothing more.
- **No merge of share and invite.** ADR-515 §4's correction stands: `create_invite` has no
  `artifact_path`, so the two doors cannot merge without a migration. Not here.
- **No internal-referral / nudge system** — ADR-515 D4 named it owed to its own ADR; still owed.
- **No rate limiter on the public route** — ADR-513 D5 named it owed; still owed, and now
  slightly more owed because SSR makes the surface cheaper to scrape. Named, not silently skipped.
- **No `share_mint_policy` dial UI** — ADR-517 D9; the dial works, its surface is still owed.
- **No folder-level grant** — ADR-515 §6 q3, still open.

## 4. Phases (each its own commit; ordered so the live defect lands first)

1. **D3 + the robots leak** — SSR the `/s/{token}` page, honest title/OG, `noindex`. Independent
   of everything else and fixes a user-visible failure the operator hit in production.
2. **D2** — content negotiation on `GET /api/s/{token}`.
3. **D1 + D4** — the `ShareDialog`, threaded through `FileVerbs`; the four deletions.
4. **D5** — the public-view hierarchy pass.
5. **Canon** — this ADR + ADR-513 amendment banner + ADR-515 status close + `grants-and-reach.md`
   + ADR-LEDGER.

## 5. Open questions (named, not closed here)

1. **Does `Copy link` need to notice when its recipient lacks reach?** (ADR-515 §6 q2, inherited.)
   With one dialog, the natural answer is *"the dialog is where you go when addressing is not
   enough"* — but the affordance is still silent about it. Unresolved.
2. **Should the markdown representation carry the walk at all?** D2 says yes (it is the
   projection, and an LLM summarizing a document benefits from knowing who wrote what). If the
   footer proves noisy in practice, dropping it is a representation change, not a boundary one.
3. **The half-view seam** (ADR-515 D6): the rail shows reach per-principal, Get Info shows it
   per-file, and they remain uncrosslinked. Untouched here.

## 6. The one-line statement

**Share becomes one act with one component on every surface — always asking, always showing the
link it minted — and the link it mints becomes one URL that a human opens and a machine can
actually read, with the attribution proven on contact instead of paraded.**
