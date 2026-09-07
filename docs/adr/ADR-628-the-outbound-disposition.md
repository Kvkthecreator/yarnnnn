# ADR-628: The outbound disposition — a post leaves the workspace

**Status**: Ratified 2026-09-01 (design; operator-aligned). **Phase (a) BUILT
same day**: WordPress is the first tenant. **Phase (a) DRIVEN 2026-09-03**
(second amendment): one real post published + receipted; composition found
unsafe and rebuilt as a contract (D6/D7). Phase (b) stays SHUT — its
precondition is now named (D8), not merely "receipts exist".

## Amendment — 2026-09-01: phase (a) built, WordPress the first tenant

Operator ruling (same day): lock WordPress. The reasoning, recorded: it is the
only candidate high on all four axes the objective needs — layman-attractive
(largest installed base of people who *have* a blog), layman-connectable
(WordPress.com's OAuth2 flow is the same one-click connector gesture as
Slack/Notion), long-standing (a decade-stable REST write contract, backed by
open source — the anti-Medium property), and wide (one client covers
wordpress.com + Jetpack-connected sites). Substack is the more attractive
*brand* and has **no write API** (its new Publisher API is read/analytics —
noted as a strings opportunity, not a publish target); Ghost is the better API
with the smaller base (second connector); Dev.to/Hashnode are the wrong
audience.

**The three-state connect story** (a member does NOT need a pre-existing
site — but WordPress always publishes TO a site):

1. has a site → OAuth connect, pick it at publish time, done;
2. has a WordPress.com login, no site → a free `name.wordpress.com` site is
   ~2 clicks on their side, once — after which they never manage anything;
3. has nothing → the authorize page doubles as signup, which lands them in
   state 2.

The fully-invisible upgrade (yarnnn mints the site during connect via the
undocumented `sites/new`) is historically whitelisted to Automattic's own
clients — confirm with Automattic before designing around it; do not promise
it. And the refusal that pairs with this: **yarnnn never hosts blogs**
(`yarnnn.com/@user` is owning a publishing platform — the ADR-417 class);
the state-zero fallback is the already-shipped Share link.

**What the build found**: `integrations/exporters/` (the ADR-028
DestinationExporter ABC + Slack/Notion/Download exporters) was a FOSSIL —
its one `.deliver()` caller was deleted 2026-08-26 with a comment claiming
"live delivery paths" that do not exist, and `connector_does` was citing it
to print member-facing copy promising an export capability no route could
perform. Deleted whole; the copy now tells the truth. The phase (a) seam is
**`services/publish.py`** — new, narrow, ADR-628-shaped — with
`integrations/core/wordpress_client.py` beneath it and
`POST /api/publish/wordpress` as the one member-clicked door. The receipt is
a `_publish.yaml` sidecar beside the post (machine format per ADR-254),
written through `write_revision` as the member's own act.

**Builds on** `docs/architecture/intake-pipeline.md` §5 (a reach proposal must
declare its disposition in its first paragraph) · ADR-577 (the credential
claim: an agent caller is refused) · ADR-594 D2 (reach with a receipt: the
seam's caller is a string's run) · ADR-591 (no clock on a connection) ·
ADR-460 D3.a (consequential external authority is unrepresentable on a being).

## Amendment — 2026-09-03: phase (a) DRIVEN. Composition is the unsafe stage.

The click-pass ADR-627/628 left owed has run. A real post left the workspace
for a real platform: `operation/test-article-2/article.html` →
`https://yarnnn9.wordpress.com/2026/09/03/test-article/` (post_id 6,
`status=publish`), receipted at `operation/test-article-2/_publish.yaml`, the
first row that sidecar has ever held workspace-wide.

**Transport is sound. Composition is not.** Every stage that carries a
receipt or a refusal worked on the first attempt — the site listing resolved
state 1 against the live API, the member's credential decrypted, the
blogger-only guard accepted the legacy `article` through its ADR-627 D1
alias, the platform call returned, and `write_revision` landed the sidecar
attributed `operator`. The one stage with **neither a receipt nor a refusal**
— turning an artifact into platform content — failed three independent ways
and reported success.

That asymmetry is the finding, and it is what gates phase (b). The other
stages announce their failures; composition cannot, because it has no
contract to violate. A standing declaration built on this composer would be
a machine for reliably publishing malformed posts, each with a receipt saying
it worked — and an outbound act is irrevocable in the world.

### What the drive found

**F1 — the `<main>` fallback publishes the entire document.** The composer
read `<main>`'s inner HTML and fell back to the RAW DOCUMENT when absent.
The legacy outward artifacts wrap their content in `<body><article>`, not
`<main>` (the native `post` scaffold uses `<main>`; the pre-ADR-627 ones do
not), so the fallback fired and doctype + `<head>` + `<style>` became the post
body: 33,978 bytes in, 39,706 out. **The artifact is 98% stylesheet** — its
real markup is 597 bytes. A fallback that degrades to "everything" is the
ADR-548 lesson exactly: a plausible default hiding the bug it should surface.

**F2 — WordPress strips `<style>` tags but KEEPS THEIR TEXT.** This is worse
than local inspection predicted and could not have been found without a real
platform call. The stylesheet did not vanish; it published as prose, with the
platform's typographic filter applied to the code — `:root { --ink: #1a1a1a; }`
as body paragraphs, `'Times New Roman'` smart-quoted to `&#8216;…&#8217;`,
`aside[data-block="callout"]` as visible text. **A local dry run cannot
predict what a platform does to bytes it receives.**

**F3 — the `data-*` strip misses CSS attribute selectors.** The pattern
required leading whitespace (`\s+data-…`); CSS writes `[data-block="callout"]`,
so 220 occurrences survived. Harmless once F1 is fixed (they only appear
inside the stylesheet that should never have crossed) — but it is the third
independent failure of the same three-regex chain, which is the argument
against regexes here rather than against this one pattern.

**F4 — "Published ✓" while no reader can read it.** The site was in
"coming soon" mode. The platform genuinely accepted the post and the receipt
is honest about what the API returned — but the member's actual goal, a
readable post, was not met, and the surface reported plain success with a
link that shows a placeholder. The ADR-373 D6 incorrect-success class, in the
outbound direction.

**F5 — the gate certified its own fixture.** `test_adr628` composed
`build_skeleton("post", …)`, which ALWAYS carries `<main>`, so all three
composition defects passed clean. A probe whose only input is the happy shape
proves the happy shape.

### D6 — Composition is a contract, and a non-conforming artifact is REFUSED

The three-regex chain is DELETED, not patched. In its place the composer
states what a publishable post is — a document whose content root is
locatable and whose transport-hostile matter (`<style>`, `<script>`, `<head>`)
is removed by structure rather than by pattern — and **refuses** anything it
cannot compose, with a member-readable reason. A refusal is a correct outcome
here; an incorrect success is not, and only one of the two is recoverable
once the post is in the world.

The content root resolves `<main>` → `<article>` → `<body>`, in that order,
covering the legacy shape ADR-627 D1 promised would keep working. When none
resolves, the act is refused rather than degraded — there is no
"publish the whole file" branch, and the absence of that branch is the fix.

### D7 — The receipt records what the READER gets, not only what the API said

A receipt that says `status: publish` while the site is private is true and
useless. The receipt carries the site's visibility alongside the platform's
answer, and the surface tells the member when a published post is not
publicly reachable (F4). This is the ADR-445 seat-drift shape once more:
record the fact, surface the gap, clear it on a later success.

### Post-fix verification — the second drive (2026-09-03, deploy `6b3565d`)

The fixed seam was driven again on the SAME artifact, as a draft (post 7):

| | post 6 (before) | post 7 (after) |
|---|---|---|
| composed | 39,706 bytes | **216 bytes** |
| body | doctype + `<head>` + stylesheet-as-prose | header · standfirst · byline · prose · h2 |
| `publicly_readable` | absent | **`false`**, and the panel says so in amber |
| `derived_from` | *(empty)* | `["…/article.html"]`, `revision_kind='derivation'` |

The deployed `GET /api/publish/wordpress/sites` returns
`{"id":"257108137","name":"yarnnn9","url":…,"public":false}` — D7 confirmed at
the wire, not merely in a gate.

⚠️ **The read-back half of D8's round-trip is NOT yet mechanized.** Post 7 is a
draft, and an unauthenticated read returns an empty body — which reads
identically to "clean". The authenticated read needs
`INTEGRATION_ENCRYPTION_KEY`, which lives only on Render by design, so a local
verifier cannot perform it. The claim "post 7 stored clean" is therefore
**unverified at the platform**: what is verified is what was SENT (216 bytes,
recomputed with the deployed composer) and every receipt field. Mechanizing the
read-back — a `read_post` verb behind the seam, exercised by a canary — is
phase (b)'s precondition and is owed before any unattended publish.

### D8 — Phase (b) stays SHUT, and its precondition is now named

The original text gated phase (b) on "phase (a) has produced real receipts."
It has: one. That is necessary and NOT sufficient, and this amendment
supersedes the loose reading. Phase (b) additionally requires **composition
fidelity demonstrated by round-trip** — publish, read the stored post back
from the platform, and diff against what was sent. F2 is unfindable any other
way, and unattended publishing multiplies exactly the class of defect that
only a round-trip reveals.

The `derived_from` edge is also owed before phase (b): the published post
today cites nothing. Strings already writes `derived_from=[raws]` for its
standing writes; a post produced from sources on a schedule must carry the
same edge, or "what was this made from?" becomes unanswerable at the moment
it becomes irrevocable.

## Amendment — 2026-09-07: Slack, the second tenant; D8's read-back MECHANIZED

**Disposition** (the first-paragraph rule): OUTBOUND, phase (a) — a
member-clicked, receipted, irrevocable act through the one seam. Nothing here
runs unattended; phase (b) stays SHUT (D8, restated below with what remains).

**Why Slack, and not Notion.** ADR-420 §10's moat-leak test governs what
yarnnn SEEDS as a first-party tenant: *does the platform accumulate the
member's work on its own side?* Notion-as-workspace is named there as a
competing commons; a channel message is delivery, not accumulation — the file
stays here, attributed, and a copy goes where the team reads. Slack passes.
It is also the connection every knowledge team already holds, the OAuth is
the one-click gesture already shipped, and `chat:write` is already granted
(the 2026 reality check D4 asked for, run: no scope widening, no re-consent).
Operator ruling in the 2026-09-07 discourse: *"reach and outbound … can
drastically feel different to the user, even our first real customer, from
day one."*

**What the seam gains** (`services/publish.py`, gate-pinned):

- `PUBLISH_TARGETS` = `{wordpress, slack}`, with `PUBLISH_VERBS` naming each
  door (publish · send a file). `connector_does` derives its writes fact
  from this set AND the LIVE lane tool surface (ADR-642 D5, corrected on the
  first click-pass): `platform_slack_send_to_channel` survives in the
  capability registry from the deleted task pipeline, but no live tool loop
  composes it, so no agent can post to Slack — the copy says so and names
  the member's door. The lane frame says the same (CHANGELOG
  `[2026.09.07.6]`).
- **The composition contract, Slack edition (D6)**: a channel post IS
  prose. The composer takes a `.md`/`.txt` file — any other type is refused
  at the act, by extension, before composition (a `post` is WordPress's
  shape; a deck, a stage, a binary have no channel form) — strips
  frontmatter and HTML, escapes what Slack requires escaped, and emits
  mrkdwn (headings → bold lines, `**` → `*`, `*`/`_` → `_`, links →
  `<url|text>`, bullets → `•`, tables → a code block, rules dropped, fenced
  code kept verbatim). It REFUSES an empty result and a result over
  `chat.postMessage`'s documented 40,000-character ceiling, with the count.
  It records `folded` (over 4,000 characters Slack hides the rest behind
  "Show more") — sent and readable-at-a-glance stay two facts (the D7
  shape).
- **Join before post.** The install carries `chat:write` but not
  `chat:write.public`, so the app must be IN a channel to post there.
  `join_channel` existed with zero callers; the seam is its first: a public
  channel is joined at the act, a private channel the app is not in is
  REFUSED with the remedy named (`/invite @yarnnn`). Slack's own refusals
  (`msg_too_long`, `is_archived`, `restricted_action`, …) are mapped to
  member-readable reasons, never surfaced raw.
- **The channel is chosen AT THE ACT** (ADR-594 D1 — never stored on the
  connection), from `conversations.list`, which now carries `is_member` so
  the picker can say which private channels need the invite first.
- **D8's read-back is MECHANIZED for this tenant.** After the post the seam
  reads the stored message back (`conversations.history` at that exact
  `ts`, inclusive) and diffs it against what was sent:
  `read_back: matched | differs | unreadable`, with the sizes on a mismatch.
  The receipt carries it. This is the round-trip D8 named as phase (b)'s
  precondition — met for Slack, still owed for WordPress (its authenticated
  read needs the encryption key that lives only on Render).
- **The receipt** (`_publish.yaml` beside the file, the member's own
  attributed write, `derived_from=[file]`): `platform: slack`, channel id
  and name, `ts`, the permalink (`chat.getPermalink`, best-effort), `at`,
  the character count, `folded`, `read_back`, `composer_version`.

**The door**: `SendToSlack` on the Text pane only (app-scoped by MOUNT, the
`StudioPublish` precedent) — the file's own pane, where the member stands on
it (D2). Three connect states (not connected → Connectors; connected with no
channels; the picker), the act, the receipt with the read-back verdict. The
open chat still carries no publish verb (D5).

**What phase (b) still needs**, so the bar does not drift with the second
tenant: (1) the narrow non-agent identity `system:publish-{platform}` (D3);
(2) a declaration contract that names the publish explicitly (D3); (3) the
round-trip for WHICHEVER tenant a declaration would publish to — met for
Slack by this amendment, unmet for WordPress. Receipts alone are not the bar.

**Gate**: `test_adr628_outbound_publish.py` §8 — the Slack composer contract
(a fixture carrying every rule, the refusal table), the seam DRIVEN with
fakes (join-before-post on a public channel, the private-channel refusal, a
platform refusal mapped, the read-back verdicts `matched` and `differs`, the
receipt fields, `derived_from`), `post_message`'s caller set pinned to the
seam + the ADR-304 tool handler and nothing else, the FE door on the Text
pane alone.

## The disposition

Canon recognizes two dispositions of platform reach, both **inward**:

| Disposition | Shape | Canon |
|---|---|---|
| INTAKE | durable, inbound — observations land at the fixed lane | intake-pipeline |
| TURN REACH | transient, inbound — a turn reads, nothing lands | ADR-615 |
| **OUTBOUND** | **content leaves the workspace for an external platform** | **this ADR** |

Outbound is not a mirror of intake. An intake defect is recoverable (a bad
observation is a revision; delete it). An outbound act is **irrevocable in the
world** — a published post is cached, syndicated, read. That asymmetry drives
every decision below.

## Decisions

### D1 — The connection stays a rail; publishing is a CONSUMER's act

ADR-582's sentence holds unchanged: a connection is consent + credential +
aperture. A **publish target** is a connection whose aperture includes an
outbound verb. No per-connection settings (ADR-594 D1 stands) — *what* gets
published and *when* lives at the consumer (a declaration, or a member's
click), never on the connection row.

### D2 — Phase (a): the member carries the post across

v1 publish is a **member-clicked act on a workspace artifact**: the member
stands on a `post`, the surface offers "Publish to {target}", the API
performs the platform call with the member's own credential
(`platform_credentials.py`, the ONE path — the caller is the member, so
ADR-577's agent-refusal is never in question), and the receipt lands as an
attributed revision on the post (frontmatter or sidecar: platform, URL,
timestamp). The autonomy cliff is not approached: no agent decides to
publish, so nothing needs a dial.

### D3 — Phase (b): automation follows the capture precedent exactly

When a standing declaration is trusted to publish without a click, the
mechanism is ADR-594 D2's shape, outbound: the seam's caller is **a string's
run**, the identity is a **narrow non-agent system identity**
(`system:publish-{platform}` — the ADR-626 D4.b finding is the law here:
every live unattended lane grew its OWN narrow auth, and three lanes voting
the same way is the design), the act is **balance-checked before the call**
(ADR-618), **receipted** (execution event + the D2 revision), and
**bounded** (one post per run; no fan-out). The declaration's contract must
name the publish explicitly — a declaration that says "keep the drafts
folder true" never publishes.

Phase (b) does not begin until phase (a) has produced real receipts, and it
begins with an ADR amendment recording that evidence.

### D4 — Platform-generic, and the first paragraph rule

The seam is named by DISPOSITION, never by tenant (the intake-pipeline rule:
never name a lane after its first consumer). Candidate first targets, with
the 2026 reality stated: **Medium's public API stopped issuing integration
tokens years ago and is effectively closed** — it is not a viable first
target despite being the category's name. Viable: **Ghost** (Admin API,
first-class), **Dev.to/Forem**, **Hashnode** (GraphQL), **WordPress REST**.
The first target is chosen when phase (a) is built, against a real account
the operator holds; this ADR deliberately does not pick.

### D5 — What is refused

- **No bucket, no bypass**: the publish call goes through the platform's
  authenticated API from the yarnnn API service — never a pre-signed upload,
  never a client-side post (the ADR-622 shape: the control channel is ours).
- **No agent-held credential, ever** — phase (b)'s identity is non-agent
  system machinery; ADR-577's guard is untouched.
- **No publish from chat**: a turn that could publish is a turn that could be
  prompted into publishing. Phase (a) is a surface act; phase (b) is a
  declaration's run. The open conversational surface never carries the verb.

## Consequences

- ADR-627's Blogger ships with zero outbound reach and loses nothing by it.
- `connectors.md` gains the third disposition row when phase (a) builds (the
  doc change rides the build commit, not this one — a doc describing an
  unbuilt seam as live is the ADR-573 "ratified ≠ implemented" trap).
- The retention/pricing questions (does a publish receipt carry a disposition
  owed?) are deferred to phase (a) with the build.

## Gate

`test_adr628_outbound_publish.py` (arrived with phase (a), per the original
plan). Its first assertion is D5's: no module under `api/` performs an
outbound platform write outside the `services/publish.py` seam — which now
also pins the exporter fossil's grave.
