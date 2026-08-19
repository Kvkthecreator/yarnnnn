# The Intake Pipeline — how anything from outside reaches the commons

> **Status**: DESCRIPTIVE CANON of existing practice, ratified 2026-08-18 as the
> contract for future intake lanes. The four-stage shape and the path grammar are
> **binding**; the tenant roster is **not** (§2).
>
> This document names a pipeline that already exists and had no canonical
> description. Four independent implementations converged on the same shape
> without a shared contract — that convergence is the evidence it is real, and
> the absence of a written contract is why a fifth (connectors) was built as a
> parallel lane instead of a tenant.

---

## 1. The shape

Everything that enters the workspace from outside — a web feed, a platform API,
a human's upload, a connected LLM — follows the same four stages:

```
1. RETAIN    raw lands immutable, attributed, at a deterministic path
2. DISTIL    a bounded judgment turn reads raw and produces understanding
3. SIGNAL    the understanding lands in the commons, citing its raw source
4. READ      the commons is reachable by ordinary substrate verbs
```

Stage 1 is **mandatory**. Stages 2–3 are **per-lane decisions with a stated
reason** (§4). Stage 4 is a consequence, not a step.

### The path grammar (binding)

```
inbound/{lane}/{selector}/{stamp}.{ext}
```

| Segment | Means | Examples |
|---|---|---|
| `lane` | **how it arrived** — the transport class | `web` · `slack` · `uploads` · `mcp` |
| `selector` | **which slice** of that source | a channel id · a feed slug · a principal |
| `stamp` | **when** it was observed | `2026-08-17T210044Z` |

Verified against production (2026-08-18) — all four live lanes already conform:

```
inbound/web/simonwillison/2026-08-17T210044Z.xml
inbound/slack/c0a6p2ws4hl/2026-07-03T06:40:31Z.md
inbound/uploads/operator/image-5.png
inbound/mcp/claude/yarnnn-canon-lock.md
```

⚠️ **Drift note**: `workspace_paths.py:141` documents this as
`inbound/{transport}/{principal}/{slug}.md`. That was accurate when uploads and
mcp were the only lanes (their selector IS a principal). For `web` and `slack`
the middle segment is a **source selector**, not a principal. `{selector}` is
the general form; `{principal}` is the special case. Correct the constant's
comment before relying on it.

### `inbound/` is a quarantine lane

- **OUTSIDE `operation/`** — raw never mixes with authored understanding.
- **Immutable** — reasoned against, never rewritten. (`inbound/uploads/` is
  deliberately carved back out: the operator owns what they uploaded and may
  reorganize it — ADR-395 / ADR-422 D2.)
- **Embed-ineligible** (`embed.py:53`) — raw is reached by deterministic key,
  never ranked into recall. Only derived understanding is embedded.

This is what makes stage 2 necessary rather than optional-in-spirit: **without a
distil step, material in `inbound/` is unreachable by the commons by design.**

---

## 2. Tenants change; the pipeline does not

**The tenant roster is not part of the contract.** As of 2026-08-18 the live
lanes are `web`, `slack`, `uploads`, `mcp` — and that list is expected to churn.
Lanes will be added, renamed, merged, and deleted. The surface roster above them
churns faster still (Home and Channels were both deleted after long stints in
CLAUDE.md).

Consequences, stated so they are not rediscovered:

- **`inbound/web/` is not "radar's directory."** It is the HTTP-fetch lane.
  Radar and Strings are current tenants. Either could be deleted without the
  lane moving.
- **Do not name a lane after its first consumer.** Name it after *how material
  arrives*. A constant named for its first feature hides the blast radius when
  the second arrives.
- **An app declares WHAT it watches; the pipeline decides HOW that is fetched.**
  An app watching an RSS feed and the same app watching a Slack channel should
  differ in one source declaration, not in a code path.
- **The scaling test**: you must be able to add a lane without touching any app,
  and an app without touching any lane. Where that fails, coupling has been
  introduced — and that coupling is what produced four parallel platform-reach
  implementations (`landscape.py`, `platform_tools.py`, capture, the deleted
  harvest), none of which shared a line.

---

## 3. Attribution

`revision_kind` (ADR-423) already carries the distinction and is the vocabulary
to use: **`observation`** for raw, **`derivation`** for derived, **`authored`**
for a principal's own writing.

### Raw — attributed to the MECHANISM

Raw stays `system:{mechanism}` (ADR-288, ADR-401 D1: the peripheral is
machinery, not a contributor). Live precedent:

| Lane | `authored_by` | `revision_kind` |
|---|---|---|
| `web` | `system:track-web-sources` | `observation` |
| `slack` | `system:sync-platform-state` | `observation` |
| `uploads` | `operator` | `observation` |
| `mcp` | `yarnnn:mcp:Claude` / `:chatgpt` | `observation` + `authored` |

Two lanes are deliberate exceptions, not drift to be normalized:

- **`uploads`** — a human genuinely authored the arrival. The operator IS the
  contributor.
- **`mcp`** — the connected principal is named because it is a **principal with
  a grant** (ADR-431), not a peripheral. An MCP write is that principal's act.

The `slack` lane's 48 historical `'authored'` rows were relabeled
`'observation'` by migration 244 (ADR-580 D8) — they predated ADR-423's
vocabulary and were mislabeled by migration 208's backfill default; the live
writer had already been fixed by `f355d26` (2026-07-09).

### Derived — attributed to the mechanism, ON BEHALF OF the connection owner

```
system:derive-{lane} on behalf of {owner}
```

**Ratified 2026-08-18.** The reasoning, which should survive the decision:

- The **machinery** wrote the sentences. A derived file authored `member:kevin`
  would read on the workspace timeline as "Kevin wrote this" for text a
  distillation turn produced — a small lie of exactly the kind ADR-577 removed.
- The **owner** is nonetheless real and load-bearing: a specific principal
  connected the source and declared its scope. Their reach is why the material
  is here at all. Provenance must record them.
- This keeps **ADR-401 D1 intact** (the peripheral never becomes a principal)
  and leaves **ADR-378 §7** (platform-as-principal) closed. It needed no new
  ontology.
- It is **not novel** — it is the `mcp` lane's shape (identify the connection,
  not the transport) applied to derived material.

**`platform_connections.connected_by` is the record of `{owner}`.** Named by
ADR-407 D5, deferred by ADR-425 AD5, extended to grants by ADR-431 — **built
by ADR-580 D5 (migration 244)**, with the derive step, as this document asked.

**Physical encoding (ADR-580 D4)**: the sentence is composed at DISPLAY, never
stored. On the ledger, `authored_by = "system:derive-{lane}"` (the mechanism)
and the owner rides `author_identity_uuid = connected_by` — the MCP lane's
identity-rider shape. A raw UUID never rides the `authored_by` string
(`principal_display._scrub` law); a stored display name would freeze a name
that moves.

Every derived file carries `derived_from` citing its raw source (ADR-209). The
GC is evidence-bounded on that edge: cited raw is never pruned.

---

## 4. Derive is per-lane, with a reason

Whether a lane distils is a decision, and the reason must be stated:

| Lane | Derives? | Why |
|---|---|---|
| `web` | **yes** | RSS/Atom is machine-shaped; unusable until distilled |
| `uploads` | **yes** | `system:extract` → `derivation` (text out of blobs) |
| `mcp` | **no** | an MCP write is already meaningful authored prose — there is nothing to distil |
| `slack` / `notion` / `github` | **yes** (ADR-580) | `services/connector_derive.py` — one bounded turn per watched selector maintains `operation/_connectors/{platform}/{selector}.md`, citing the raw; dormant with the capture lane (ADR-404 D2) |

**`mcp` not deriving is correct.** The connector gap this table once named is
closed by [ADR-580](../adr/ADR-580-the-connector-derive-step.md); the brief
that framed it ([`connector-reach-and-the-commons.md`](connector-reach-and-the-commons.md))
is retained as the discourse record.

This is why the contract binds stages 1 and 4 but not 2–3: a rule that every
lane must derive would make `mcp`'s correct shape a defect.

---

## 5. The two dispositions of platform reach

One transport, two dispositions — **named vocabulary**, added 2026-08-19 after
the operator re-hit the ambiguity that produced four parallel reach
implementations. The line between them is the line between this architecture
and "conventional MCP connectors" on other platforms:

| | **Intake** (this document) | **Turn reach** (NOT built) |
|---|---|---|
| The question | "the workspace **stays current** with the platform" | "ask the platform something **now**" |
| Shape | standing: retain → distil → signal → read | a tool call inside one conversation turn |
| Where the result lives | the commons — attributed, versioned, compounding | the turn's context — **dies with the turn** |
| Who drives | the scheduler; no human in the loop | a member, conversationally |
| Cost bound | the pace law (new-raw gate + floor) | per-turn; unbounded unless designed |
| Credentials | deterministic capture machinery only — no LLM turn ever holds one | needs its own ADR-577-compatible answer |
| Status | **live** (dormant behind `CONNECTOR_CAPTURE_ENABLED`) | a **named seam** (`connector-reach-and-the-commons.md` §5) — deleted as unreachable, deliberately not rebuilt |

Conventional MCP connectors elsewhere are **turn reach** — that is the
industry norm, and YARNNN's divergence from it is deliberate: an autonomous
agent has no member-driven turn to put transient context into, and only intake
feeds the record. The two dispositions share one transport
(`handle_platform_tool` — capture literally calls it) and can coexist; turn
reach can be **added** beside intake later, but the attributed record cannot be
recovered retroactively if intake wasn't running — the asymmetry that makes
intake the default and turn reach the opt-in.

**The rule**: any proposal touching platform reach declares its disposition in
its first paragraph. A proposal that cannot say which it serves is both at
once, and is re-running the conflation.

---

## 6. What this does not decide

- **Whether to open the turn-reach seam** (§5). Its surface, its ADR-577
  answer, and its cost bound are a future ADR's subject.
- **Which lanes exist.** By §2, deliberately.
- **The connector derive step itself** — built by
  [ADR-580](../adr/ADR-580-the-connector-derive-step.md) against this
  document's contract; the framing discourse is
  `connector-reach-and-the-commons.md`.

---

## 7. Receipts

| Claim | Source |
|---|---|
| Four live lanes, uniform grammar | production query, 2026-08-18 (§1) |
| Raw is quarantined + embed-ineligible | `workspace_paths.py:140`, `embed.py:53` |
| `uploads` carved out of immutability | ADR-395, ADR-422 D2 |
| `revision_kind` vocabulary | ADR-423, `authored_substrate.py:221` |
| Peripheral is not a principal | ADR-401 D1 §3 |
| MCP principal holds a grant | ADR-431 |
| `connected_by` named 3×, built with the derive step | ADR-407 D5 · ADR-425 AD5 · ADR-431 · **ADR-580 D5 (mig 244)** |
