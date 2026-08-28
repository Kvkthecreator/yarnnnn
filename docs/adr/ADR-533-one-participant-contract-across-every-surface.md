# ADR-533 — One Participant Contract: The Commons Etiquette Is Singular Across Every Surface

> **Status**: **Accepted — operator-ratified 2026-08-07** (the internal-envelope vs
> interop-envelope audit session: read both surfaces → found the fired falsifier →
> shape delegated, two decisions taken by the operator).
> **Date**: 2026-08-07
> **Authors**: KVK (operator) + Claude (collaborator)
> **Hat**: A (kernel constants + the interop binding + the OpenAI Apps presentation layer)
> **Dimensions**: Substrate (Axiom 1 — how a participant is taught the filesystem) +
> Identity (Axiom 2 — what a principal is told about its own reach) + Channel (Axiom 6 —
> how one contract binds per surface)

**Amends**: [ADR-424](ADR-424-pure-os-filesystem-model.md) **D5 only** — the "no change to
`mcp_server/`" exclusion, whose own stated falsifier has fired (§2). ADR-424's D1 home
model, D2 peers ruling, D3 `home` parameterization, and D4 four-envelope collapse are
**unchanged and re-ratified**; this ADR extends D1's reach to the fifth envelope. ·
[ADR-512](ADR-512-the-file-is-the-unit-of-interop.md) (the connector `instructions` block
it authored gains the commons contract + a derived verb table; §5 adds the missing
`derived_from` authoring path to `save`) · [ADR-372](ADR-372-presentation-affordances-interop-face.md)
/ [ADR-379](ADR-379-host-profiles.md) (the widget roster gains the three ADR-512 file
verbs — §6).
**Relates to**: ADR-411 (the lane conventions projection this ADR generalizes) ·
ADR-408 D2 (the altitude boundary this ADR does **not** cross) · ADR-448 (the
`derived_from` reference edge) · ADR-368 Correction 1 (the compound-binding constraint,
preserved) · ADR-504 (the interop principal invariant) · FOUNDATIONS DP33 (collapse
disagreeing prose to data).

---

## 1. Context — three surfaces, one etiquette, three authors of it

YARNNN teaches an LLM participant how to behave in the commons in three places:

| Surface | Where the teaching lives | Who authored it |
|---|---|---|
| Lane (webapp chat · Studio · Docs) | `lane_runner._CONVENTIONS_FRAME` + `build_lane_conventions()` | yarnnn |
| Wake spine (scheduled/unattended) | `freddie_agent._compute_minimal_frame()` + the wake envelope | yarnnn |
| Interop (ChatGPT · Claude.ai · any MCP host) | `mcp_server.server.instructions=` | yarnnn (hand-authored, sharing nothing with the other two) |

The first two are a documented altitude split (ADR-408 D2) and are **not** the subject of
this ADR. The third is the finding: the interop surface hand-authors its own etiquette
prose, and that prose has drifted from — and is materially thinner than — what every
other participant is told.

This matters because of what changed underneath it. When the interop face was three
memory verbs, "the external LLM writes by meaning through `remember`" was a complete
account of its reach. ADR-512 made it six verbs including `save` — **an authenticated,
CAS-guarded file write into the shared commons**. A principal that can overwrite a named
document is a participant in the commons, not a diary user, and it is currently the only
participant never taught the commons contract.

The operator's framing, which this ADR adopts: *regardless of whether you use yarnnn in
the housed webapp or elsewhere, the experience should be as close to identical as
possible.*

## 2. The fired falsifier (why this is not a re-litigation of ADR-424 D5)

ADR-424 D5 explicitly excluded the interop surface, on the operator's own correction:

> "The external LLM is told nothing about the filesystem today (three verbs, "durable
> memory"). Per the operator's correction, that is **already the pure-OS end state** for
> the external surface … **Explicitly: no change to `mcp_server/` or the verb docstrings.**"

That was correct for the surface as it stood. D5 also wrote its own falsifier in the
same breath:

> "(Should the ADR-311 raw-primitive interop ever wire WriteFile over MCP, it inherits
> the D1 model like any participant — but that is not this ADR.)"

**The condition has occurred.** ADR-512 §8a shipped `save`, and
`mcp_composition.compose_save()` dispatches `execute_primitive(auth, "WriteFile", …)` —
WriteFile over MCP, precisely the named trigger. The exclusion was scoped to a surface
that no longer exists.

Two disciplines are re-confirmed by how this was found:

- **A documented limitation is not a gate.** D5 named its own voiding condition in prose;
  nothing enforced it, so the condition fired silently and the exclusion outlived its
  premise by five days. The remedy is §7's ratchet, not more prose.
- **The audit that found it began by misreading it.** The first pass called F1 "a live
  violation of DP33" from the *constant's docstring* without reading the ADR that scoped
  it. The correction — exclusion, not violation; falsifier fired, not rule broken — is
  the load-bearing distinction, and it is why this ADR *amends* D5 rather than asserting
  it was always wrong.

## 3. D1 — The commons contract is kernel data, composed per surface

The etiquette every participant needs is **one set of clauses**, authored once as kernel
constants beside `PARTICIPANT_FILESYSTEM_MODEL` (the DP33 "collapse to data" move that
ADR-424 D1 already established for the filesystem model):

| Constant | Clause |
|---|---|
| `PARTICIPANT_FILESYSTEM_MODEL` | *(exists, ADR-424 D1)* where / whether / who |
| `PARTICIPANT_COMMONS_CONTRACT` | the workspace is shared + versioned; peers collaborate **through files, not transcripts**; read before writing |
| `PARTICIPANT_ATTRIBUTION_RULE` | every write is attributed + versioned; revertible, never silently destructive |
| `PARTICIPANT_CITATION_RULE` | when authoring **from** another file, cite it via `derived_from` |
| `PARTICIPANT_FORMAT_DISCIPLINE` | prose is `.md`; machine config is `_*.yaml` and is not hand-authored unsolicited |

**Each surface composes from these constants; no surface re-authors a clause.** The
composition differs — that is correct and deliberate, because the surfaces genuinely
differ (a lane has a member, a model, a MANDATE, and five primitive verbs over eight
rounds; an interop host has a foreign frame, an unknown model, and six compound verbs in
one round). What must not differ is the *content of a clause*.

**Rejected: one shared `build_participant_conventions()` both surfaces call.** It forces
a single prose body across two genuinely different tool surfaces, and the tool line would
need parameterizing regardless. The "Four verbs / six verbs" drift (§4) is exactly what
happens when prose stops tracking its actual surface; a single body makes that harder to
keep honest, not easier. Singular **source**, per-surface **shape**.

## 4. D2 — The verb table is derived, never hand-written

The connector `instructions` block today opens `"…Four verbs:"` and then enumerates
**six** (`open · remember · recall · trace · save · share`). It has been shipping to every
connected host since `save` and `share` landed.

The lane already solved this class of bug and documented why:

> `tools_line = " · ".join(lane_tool_names())` — "Derived from the same `lane_tool_names`
> the payload + the loop's allowlist read, so the prose can never claim a surface the
> model wasn't handed (the Scout bug's prose half)." — `lane_runner.py:355-362`

**The interop verb table is derived from the registered tool set**, by the same rule. A
count in prose is a hand-maintained duplicate of a fact the server already holds; it is
removed, not corrected. Adding a seventh verb must not require editing prose that
announces how many verbs there are.

## 5. D3 — `derived_from` is authorable from every surface that can write

The citation edge is currently **read-only on the interop surface**:

- The lane frame *teaches* it (`lane_runner.py:271-274`) and `WriteFile` *supports* it
  (`primitives/workspace.py:170`, `:878`, `:980`, `:1037`).
- `compose_save()` builds its `WriteFile` input as
  `{scope, path, content, mode, message, expected_parent_version_id}` — **no
  `derived_from`** (`mcp_composition.py:1290`).
- `save` and `remember` expose no `derived_from` parameter.
- Meanwhile MCP *reads* the edge extensively (`recall`/`trace`: `:414`, `:426`, `:951-977`).

This is backwards. The interop surface is **the one place foreign material arrives** — a
host reasoning over a document the user pasted, then saving a derived version, is the
paradigm case for citation — and it is the only writing surface that cannot record where
its content came from. `save` gains an optional `derived_from`, threaded to the primitive
that already accepts it, and the citation clause (D1) tells the host to use it.

**`remember` is deliberately excluded, and the reason is load-bearing.** It writes
`revision_kind='observation'` — a *raw arrival* in the inbound lane (ADR-376/DP32,
ADR-423). A raw observation is by definition **not** made from a workspace file; it is
what enters from outside. Giving it a citation edge would invite hosts to manufacture
provenance for material that has none, which corrupts the very edge D3 exists to make
trustworthy. `save` authors *derivations* and cites; `remember` records *arrivals* and
does not. The asymmetry is the ontology, not an omission.

Two parsers, each owning its grammar, neither duplicating the other: `parse_file_reference`
(interop) resolves the `yarnnn://` handle; `normalize_workspace_ref` (ledger, ADR-448)
owns `/workspace/` prefixing. A citation that fails to parse is **dropped, never fatal** —
a malformed reference must not cost the user their write. The edge is provenance, not a gate.

Ratified consequence: an interop-authored derivation joins the same reference graph the
Files surface renders and the delete-guard warns against — instead of arriving as an
orphan.

## 6. D4 — The presentation roster covers the verb roster (the second-order pass)

The OpenAI Apps / MCP-Apps widget layer is frozen at the **pre-ADR-512 verb set**:

| Verb | Widget | Era |
|---|---|---|
| `remember` | `remember-receipt` | memory-era (ADR-368) |
| `recall` | `recall-cards` | memory-era |
| `trace` | `trace-timeline` | memory-era |
| `open` | — | ADR-512 |
| `save` | — | ADR-512 §8a |
| `share` | — | ADR-465/512 |

ChatGPT is the only host with `renders_widgets=True` (`hosts.py`). So on the one surface
that renders richly, **the three memory verbs render as cards and the three file verbs
render as bare text** — the OpenAI Apps face still presents yarnnn as a memory product,
the costume ADR-512 §10 declared ended on 2026-07-30.

The presentation *architecture* is not at fault and is not changed: host-as-data, one
adapter file per dialect, the `test_adr379_host_profiles.py` name-leak gate. The gap is
**roster coverage**.

**Not every verb earns a widget — and that is the layer's own doctrine**, stated in
`affordances.py` since ADR-372: *"a tool with no entry is text-only (the default, valid on
every host)."* So D4 is not "widget everything"; it is "every verb has a **declared**
rendering decision." Two get widgets, one is declared text-only:

| Verb | Decision | Why |
|---|---|---|
| `save` | `save-receipt` | The verb's most important outcome is the **conflict** (`stale_write` / `base_required`): someone else holds the head, here is who, when, what they called it, and what to do. Four facts the user must act on, which a chat host renders as a paragraph they skim past. |
| `open` | `file-header` | Renders the file's **identity** — whose version this is, when, how many attributed revisions — and deliberately **not** its content. The content is the host's to render (it does that better); the attribution is what a plain storage connector cannot show at all. |
| `share` | **text-only, declared** | The result is a link plus a reach level: one line the host relays verbatim. A widget for a URL is ceremony — an iframe the user must look at to read what the sentence already said. |

The text-only choice is recorded in `affordances.TEXT_ONLY` **with its reason**, and the
D5 ratchet asserts every rostered verb is in `AFFORDANCES` *or* `TEXT_ONLY` (exactly one,
never both, never neither). This is the point: a deliberate text-only decision and an
unfinished one are indistinguishable in an empty map, and the gate makes them distinct.
Moving a verb between the two maps is the entire cost of adding or dropping a widget.

**Sequencing is load-bearing**: D4 ships **after** D1–D3. A widget renders a contract; the
`save` widget must render the contract `save` actually has (including `derived_from`),
not the one it had before this ADR.

**The host gate still covers the new pointers.** ADR-372 D4's live break — claude.ai does
NOT ignore a widget pointer; it fetches and fails on it — applies to any newly-advertised
widget. Verified: `strip_widget_meta` removes every `openai/*` + `ui` key from both new
tool definitions for `claude.ai` and for unidentified hosts, and `renders_widgets` remains
True only for `chatgpt`. The text path is unchanged on every other host.

## 7. D5 — The ratchet, and what it must not become

ADR-424's gate (`test_adr424_pure_os_filesystem.py`) asserts four envelopes carry the D1
model and contains **no interop assertion** — faithful to D5, and now stale. The gate is
extended to the fifth envelope.

The ratchet asserts, per surface:

1. Each participant-facing envelope **imports** the D1 constants rather than restating a
   clause inline.
2. The interop verb table is **derived** from the registered tool set — no hand-written
   count, no hand-written verb list.
3. Every write-capable surface threads `derived_from` to the primitive.
4. Every registered verb has a presentation entry **or** an explicit declared
   text-only reason — exactly one, never both, never neither. Every declared widget
   resolves to a registered `Widget` whose bundle is actually built (a dangling id
   would 500 at resource-read time on a live host).

**What it must not be**: a gate that pins a spelling. Prior gates in this codebase have
gone void by asserting an expression's first token or matching their own explanatory
comment. These assert *structure* — that a constant is imported, that a list is derived,
that a parameter is threaded — never the prose those things produce. A clause must stay
editable without going red.

## 8. D6 — The external surface stays thin (what does NOT port)

The lane injects a 40-line MANDATE head as read-only orientation. **It does not port**,
by operator decision.

The distinction is principled, not a size compromise: **the commons contract is how the
workspace works** (true of every workspace, kernel-universal, therefore a constant) —
**the MANDATE is what this workspace is for** (workspace-specific intent). The first is
etiquette a participant needs to behave correctly anywhere. The second is proprietary
context that would leave the system into a third-party host's window on every connection,
for a benefit no verb requires.

This preserves ADR-424 D5's *instinct* (the external surface stays specificity-light)
while correcting its *scope* (a write-capable participant is owed the etiquette). Also
explicitly not ported: lane posture overlays (agent · studio · design-system · derive),
the member/model interpolation, and anything at Altitude 1.

> **AMENDED 2026-08-28 by [ADR-617](ADR-617-an-external-principal-is-taught-the-document-it-can-write.md) D2.**
> The MANDATE ruling above is **unchanged**. What ADR-617 splits is the "lane posture
> overlays" item, which covered two different things on the wrong axis:
>
> - a posture's **turn state** (the live outline, an inlined `_string.yaml` +
>   `CONTRACT.md`, the design-system roster) — workspace-specific and turn-scoped;
>   **stays withheld**, exactly as this section intends;
> - a posture's **format grammar** — how a document of that type is structured. This is
>   not intent at all. By D6's own test (*"how the workspace works"* vs *"what this
>   workspace is for"*) it is the first, and it is the same class as
>   `PARTICIPANT_FILESYSTEM_MODEL`, which always ported.
>
> The measured cost of withholding it: an external principal that can `save` an `.html`
> artifact had never been taught that a `data-ref` element is a live projection — so it
> read an empty cited block as an empty slide (the ADR-373 D6 incorrect-success class),
> and could paste a cited file's bytes into a document where the renderer silently
> overwrites them. `PARTICIPANT_ARTIFACT_CITATION_RULE` now crosses as a **kernel
> constant both surfaces compose** — never by calling a lane posture builder from the
> connector, which would leak exactly the turn state this section protects.

> **Open framing debt (operator, 2026-08-07, at ratification)**: the vocabulary this
> section leans on — **MANDATE** as the workspace's declared intent, and **Freddie** as
> the wake-spine occupant (§9) — is **outdated concept-work pending its own discourse**.
> D6's *decision* (the external surface does not receive workspace-specific intent) is
> ratified and implementable regardless of what that intent-carrier ends up being called
> or how it is modeled. What is deferred is the framing, not the ruling. Re-read this
> section and §9 after that discourse; if the concept dissolves or is renamed, D6's
> boundary re-states in the successor vocabulary — it does not lapse.

## 9. Explicitly out of scope

- **The wake spine (Altitude 1).** `freddie_agent` / `wake.py` / `wake_drainer` /
  `review_proposal_dispatch` are **untouched**. An early pass of this audit reported
  `invoke_freddie` as having zero production callers; that was a grep error — it has four
  live call sites and is drained by the deployed scheduler. Any sunset of that tree needs
  its own evidence and its own ADR, and must not ride along on a parity change.
- **The compound-vs-primitive verb shape.** ADR-368 Correction 1 (consumer hosts get
  server-composed compound tools) stands. This ADR makes the two surfaces teach the same
  etiquette; it does **not** re-cut the interop verb surface to the lane's five primitives.
  That remains evidence-gated per ADR-512 §9.
- **The `_workspace_guide.md` bundle prose** — unchanged (ADR-424 D6's deferral holds).

## 10. Rejected alternatives

- **One shared builder for both surfaces** (§3) — forces one prose body across two
  genuinely different tool surfaces; re-creates the drift class it claims to fix.
- **Leave the interop surface thin, as ADR-424 D5 ruled** — D5's own falsifier fired; a
  principal that can CAS-overwrite a named document is owed the contract.
- **Port the MANDATE too** (§8) — workspace-specific intent into a third-party window,
  for no verb's benefit.
- **Fix the "Four verbs" count in prose** — corrects the instance, preserves the class.
  The count is derived (D2) or it is not there.
- **Widgets first, contract second** — a widget would render a contract about to change.

## 11. The one-line statement

**The commons etiquette is one set of clauses authored once as kernel data and composed
per surface — so a participant is taught the same contract whether it is a lane in the
webapp or ChatGPT on the other side of an OAuth token; what varies per surface is the
binding and the grant, never what the participant is told the commons is.**

---

## 12. Live verification (2026-08-07, prod, deploy `2aa8c25`)

Run from Claude Code over the yarnnn MCP connector against production — a real
foreign principal (`yarnnn:mcp:Claude`) writing into the operator's own workspace,
not a fixture.

| Check | Result | Receipt |
|---|---|---|
| `recall` on an unrecorded subject | `confidence: "ambiguous"` — surfaced candidates, invented nothing | 5 chunks, none dominant |
| `save` (create) | attributed revision | `f8c6b43a-021b-458f-9de8-4f17498bf15d` |
| `save` (blind overwrite) | **refused** | `base_required` + `current_head{revision_id, authored_by: "yarnnn:mcp:Claude", when}` |
| `open` | exact content + attribution + chain | `authored_by`, `last_updated`, `history[].message` all present |
| `save` (correct base) | CAS cycle completes | `846c8ad6-fbbf-4bb5-8f7d-7c227159d389` |
| `trace` | `resolution: "exact"`, 2 revisions with unified diff | both attributed |

Artifact: `/workspace/operation/notes/adr-533-interop-parity-probe.md`.

**Why the refusal is the load-bearing receipt.** D4's `save-receipt` widget exists
to render the conflict state, and this probe proves the shape is real: the refusal
returns exactly the four facts the card draws (who holds the head, when, what they
called it, that nothing was overwritten). The widget renders returned substrate,
and the substrate is confirmed present.

### Not verified

- **No host has DRAWN either new widget.** Bundles built, resources registered,
  `strip_widget_meta` verified to remove every `openai/*` + `ui` key for non-ChatGPT
  hosts — but rendering is only observable in ChatGPT, and this session could not
  open one. This is the D4 click-pass and it remains **owed**.
- **The `derived_from` parameter was not exercised live.** The calling host's tool
  schemas were captured before the deploy, so the session's `save` had no
  `derived_from` field to pass. The parameter is gate-covered (accepted, threaded
  into the `WriteFile` input, exposed on the tool) but has not made a real citation
  edge across the wire. Owed on the next connector session.
- **The composed `instructions` were not observed as a host received them.** The
  render is verified locally (4,450 chars, every clause verbatim); no host has
  confirmed what it was actually served.

---

## 13. The discovery contract — we told every host our tools never change

> **Amendment, 2026-08-07**, same session. Found because the operator reconnected
> ChatGPT after the D1–D4 push and still saw the *memory-era* three verbs. This is a
> distinct root cause from §1–§12 (that was *what a participant is told*; this is
> *whether a host ever re-reads it*), recorded here rather than as its own ADR because
> it is the same surface and the same session's work.

### 13a. The finding — two hosts, two vintages, one server

The operator's instinct was right that this was not a plain cache flush, and the
decisive move was theirs: **test the host that works.**

| Host | Verbs seen | `save` carried `derived_from`? | Manifest frozen |
|---|---|---|---|
| claude.ai | all six | **no** | after Aug 3, before Aug 7 04:34 |
| ChatGPT | three (`recall`/`remember`/`trace`) | n/a | on or before **Aug 2** |

Same server, same deploy, same `tools/list`. Ruled out with receipts: the deploy was
live (`2c94789`, Render API); `list_tools` only strips widget `_meta` and never removes
a tool; no `defer_loading` anywhere; both hosts authenticate and call tools
successfully; and `open`/`save`/`share` shipped **Aug 2–3**, days before this session.

### 13b. Root cause — ours, read from the pinned SDK

Read from the `mcp 1.28.0` wheel, confirmed against installed **1.29.0** (what prod
resolves to):

1. `lowlevel/server.py` — `NotificationOptions.__init__` defaults `tools_changed: bool = False`.
2. `lowlevel/server.py` — `ToolsCapability(listChanged=notification_options.tools_changed)`.
3. `fastmcp/server.py:759,848` + `streamable_http_manager.py:200,302` — every transport
   calls `create_initialization_options()` **with no arguments**, so it always received
   the all-`False` default.

**⇒ every `initialize` advertised `capabilities.tools.listChanged: false`.**

A host told the tool list is immutable is *entitled* to cache it forever. **Neither
ChatGPT nor claude.ai was misbehaving — they believed us.** The defect is a declaration
we never made deliberately; it was an SDK default we inherited by never passing the
argument.

### 13c. D1 — Declare the tool list volatile

`create_initialization_options` is overridden on the **lowlevel server instance** —
the single seam all four SDK call sites route through, so stdio, SSE, and both
streamable-HTTP paths are covered by one override. An explicit caller-supplied
`NotificationOptions` is still honored.

Verified against the real SDK: `listChanged=False` → `listChanged=True`, and the live
`mcp_server.server` module reports `tools capability: listChanged=True` with all six
verbs registered.

### 13d. D2 — The runbook, because the declaration cannot reach backwards

**`listChanged` alone does not fix this, and claiming otherwise would be the dishonest
version of this amendment.** Our tool surface changes only on **deploy**, and a deploy
replaces the process and drops every live session — there is no session alive to receive
a notification about the change that just happened. `listChanged` exists for servers
whose tools change *mid-session* (runtime registration); ours do not.

So D1 makes us honest going forward and lets a compliant host re-check on its next
connect. Getting an **already-stale** host unstuck is a human step, and it is now
documented per host in [CONNECTING.md](../features/mcp/CONNECTING.md) §"The surface
changed" — including the correction that reconnecting is often *not* enough for ChatGPT
(that doc previously claimed disconnect+reconnect refreshes the list; the operator's
own experience falsified it).

### 13e. Rejected — emit `send_tool_list_changed()` on session start

A host that has just run `initialize` already holds the current list, so firing at
startup re-delivers what it just fetched: motion that reads as a fix and changes
nothing. The D5 ratchet asserts this call is **absent** (matched against
comment-stripped source — asserting on the bare name, then on `name(`, each matched
this paragraph's own explanatory prose in turn).

### 13f. Verified live on a refreshed host (2026-08-07, post-deploy)

The operator refreshed the claude.ai/Desktop connector after `58d175e`. Receipts:

- **The refresh reached the CURRENT deploy, not an older vintage.** Six verbs alone
  would not prove this — `open`/`save`/`share` shipped Aug 2–3, so a stale manifest
  looks identical in a verb list. The distinguishing tell is the parameter added at
  04:34, and the refreshed host reports it:
  `save(reference, content, base_revision, derived_from, message)`.
- **D3's asymmetry confirmed from the outside.** The same host reports `derived_from`
  present on `save` and **absent** on `remember` (which takes only `content` + `about`)
  — the raw-arrival-is-not-a-derivation ruling (§5), observed rather than asserted.
- **Our `ToolAnnotations` are load-bearing in a real permissions UI.** Claude Desktop's
  Connectors panel groups the surface by our declared hints: *Read-only (3)* = Open ·
  Recall · Trace (`readOnlyHint=True`); *Write/delete (3)* = Remember · Save · Share
  (`readOnlyHint=False`). The ADR-372 annotation audit shows up as the user's permission
  control, not just metadata.
- **A host's tool search can fail while the tool is present.** The assisting model first
  reported the yarnnn tools as unavailable, then retracted: *"I was wrong last turn. The
  yarnnn tools were available the whole time — my tool searches just failed to surface
  them."* This is the §13f self-report caveat firing in the wild, and it is exactly why
  CONNECTING.md tells the user to have the host *call* a verb rather than trust its
  inventory.

### 13f-bis. Correction — ChatGPT's staleness had a SECOND, different cause

The §13b root cause (`listChanged: false`) is real and explains claude.ai. It does **not**
explain ChatGPT, and the D2 runbook's original ChatGPT row was wrong.

The operator's own hypothesis was correct: **ChatGPT pins a version snapshot of a
dev-mode connector** (`Version Id: asdk_app_v_…`, `Review status: development`). A deploy
never reaches that snapshot, and **remove + re-add does not help — it re-pins the same
snapshot.** Only the dashboard's **`Refresh`** action pulls the current manifest; the
`Version notes` field bumps (`dev-3` → `dev-4`) when it lands.

**This was already documented in our own repo and I missed it while auditing.**
`docs/features/mcp/SUBMISSION.md` §4 carries it as a labelled gotcha that cost a previous
session ~a day — including the explicit line "Reconnecting (remove + re-add) does NOT do
this." I read `mcp_server/`, the SDK wheel, and the presentation layer, but never the
ChatGPT-specific doc sitting beside them. The audit's own lesson applies to itself:
*consult the canonical home before re-deriving.*

Confirmed live after Refresh: ChatGPT's panel now lists `open` (badged `READ` /
`OPEN WORLD` — our `ToolAnnotations` rendering in a second host's UI) alongside the rest
of the current surface.

**Consequence for D2**: the runbook is per-host because the *mechanisms differ*, not just
the click path — claude.ai caches a manifest, ChatGPT pins a version. CONNECTING.md now
says so, and tells the reader to verify against a build-specific field (`save`'s
`derived_from`; `confidence` in `recall`'s description) rather than trusting a toast.

### 13g. Still not verified

- **Whether the refresh was CAUSED by `listChanged: true`.** A host re-read the list and
  got current — but the operator also triggered the refresh manually, so the mechanism is
  confirmed while the *cause* is not attributed. D2's runbook stands either way.
- **ChatGPT.** Unretested since the fix; it held the oldest manifest (pre-Aug-2).
- **The raw wire `tools/list` frame.** Needs a live OAuth token; unauthenticated root
  returns `401 invalid_token`. Every host reading here — pre-refresh and post — is a
  host's *report* of its schema, not a captured frame. §13f's receipts are strong
  because they are specific and falsifiable (a named parameter present on one verb and
  absent on another), not because they are wire captures.
- **Whether a full remove/re-add clears ChatGPT's cache.** Untested — the operator
  doubted it, which is what prompted this audit.

> **The self-report caveat, twice earned.** ChatGPT's original three-verb message and
> the assisting model's later retraction (*"my tool searches just failed to surface
> them"*) are the same failure mode: a model's inventory of its own tools is a
> hypothesis. Both times the resolution came from something checkable — the claude.ai
> comparison, the SDK source, a named parameter — never from an assistant's account of
> itself. Keep that ordering.
