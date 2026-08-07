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
**roster coverage**. The file verbs get widgets covering open (the exact-version read),
save (the attributed write receipt, including the `stale_write` conflict state — the one
outcome a host most needs to render legibly), and share (the minted link + its reach).

**Sequencing is load-bearing**: D4 ships **after** D1–D3. A widget renders a contract; the
`save` widget must render the contract `save` actually has (including `derived_from`),
not the one it had before this ADR.

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
4. Every registered verb has a presentation entry or an explicit declared exemption.

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
