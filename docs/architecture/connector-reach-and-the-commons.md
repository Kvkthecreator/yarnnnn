# Connector Reach and the Commons — the open question, framed

> **Status**: an OPEN discourse, deliberately unresolved. This document exists so
> the framing survives a closed session: it records what was measured, what was
> decided, what was deliberately deleted, and the one question that must be
> answered before any code is written. **Nothing here is ratified canon** — it is
> the brief for a future ADR.
>
> **Last measured**: 2026-08-18 (ADR-576, ADR-577). Every claim below carries a
> receipt from that audit; re-measure before trusting any of it.

---

## 1. The question, in one sentence

**Why is connector data the only intake in the system that cannot reach the
commons — when the pattern that would carry it there already works beside it?**

That is the whole of it. Everything below is evidence for why that is the right
question, and what a future ADR must decide before answering it.

---

## 2. What was measured (2026-08-18)

### 2a. There is no surface through which an agent can reach a connector

Audited across every consumer surface:

| Surface | Reaches connector APIs? | Why |
|---|---|---|
| Member chat lanes (`run_lane_turn`) | **No** | Closed 9-tool allowlist (`lane_runner.py:148/173`); `lane_tools_openai()` RAISES on any name outside it |
| App lanes (radar · docs · images · Strings · Studio) | **No** | Same closed set; the `app` parameter selects a PROMPT OVERLAY only (`lane_runner.py:838`) |
| Steward (`freddie_agent.py`) | **No** | `FREDDIE_PRIMITIVES + ReturnVerdict` (`:924`) — deliberate, ADR-299 D8 |
| MCP server | **No** | 9 substrate verbs only |
| Capture lane | Yes, but **dormant** | `CONNECTOR_CAPTURE_ENABLED` defaults OFF (ADR-404 D2) |
| Settings picker (`landscape.py`) | **Yes** | Discovery only — never lands substrate, no agent sees it |

The exclusion is stated affirmatively in code, not accidental —
`lane_runner.py:164`: *"Seeing a connector is NOT reaching through one."*

### 2b. Capture is built on the same transport as tool calls, minus the last step

`capture_connector.py:215` calls `handle_platform_tool` — the *same* execution
path a tool call uses. So there are not two mechanisms; there is **one reach
transport and two dispositions of the result**:

- **discard it** (a tool call: data enters a turn's context and dies with it)
- **land it** (capture: raw → `inbound/{platform}/{selector}/{observed_at}.md`)

Capture then stops. `inbound/` is deliberately OUTSIDE `operation/` (quarantine)
and deliberately embed-ineligible (`embed.py:53` — raw is reached by
deterministic key, not ranked). **Nothing promotes it.** The only production
reader of `inbound/{platform}/` is the garbage collector
(`connector_retention.py`).

### 2c. The pattern that works, immediately adjacent

Radar and Strings do the complete loop with HTTP sources:

```
fetch (httpx) → retain raw (inbound/web/{source}/{observed_at}.xml)
              → distil → {hub}/_watch_signal.yaml → the commons reads it
```

Connectors do:

```
read (platform API) → retain raw (inbound/{platform}/{selector}/…) → ∅
```

**`inbound/web/` has live consumers. `inbound/{platform}/` has none.** Adjacent
namespaces, identical shape, one wired and one not.

This is the single most important finding in the file: **derive is not an
unsolved design problem. It is a solved pattern connectors were never wired
into.** A future ADR should be framed as *adopt the working pattern*, not
*invent derive*.

### 2d. Production receipt — the aperture is declared and nothing flows

For the one workspace with all three connectors active:

```
/workspace/operation/_connectors/github/_watch.yaml   2061 bytes, 1 repo selected
/workspace/_captures.yaml                             captures: []   (13 bytes)
inbound/github/**                                     0 files
any github-derived file                               0
```

**The only GitHub artifact in the entire workspace is the selection file
itself.**

---

## 3. ATTRIBUTION — ANSWERED 2026-08-18

> **RESOLVED by the operator**: *"if the system update was via some workspace
> user or principal, that's the update owner for attribution."*
>
> **Raw** stays `system:{mechanism}` + `revision_kind='observation'`.
> **Derived** carries **`system:derive-{lane} on behalf of {owner}`**, where
> `{owner}` is the principal who connected the source
> (`platform_connections.connected_by` — named 3× in canon, never built; build
> it WITH the derive step).
>
> ⭐ This needed no new ontology: it is the **`mcp` lane's shape already in
> production** (identify the CONNECTION, not the transport). ADR-401 D1 stays
> intact — the peripheral never becomes a principal — and ADR-378 §7
> (platform-as-principal) stays closed.
>
> The full contract, including the binding path grammar and the per-lane derive
> rule, is canon at [`intake-pipeline.md`](intake-pipeline.md). **Read that
> first.** What follows is the reasoning that produced the answer, kept because
> the alternatives are worth knowing.

The question was:

> **When derive promotes raw into `operation/`, who authors the derived file?**

The constraints that make this hard, and that a future ADR cannot wave away:

- **ADR-401 D1 §3** keeps peripherals NON-principals. Capture writes are
  `system:capture-{platform}` — *"the peripheral is machinery, not a
  contributor."* It gets no home and no attribution.
- **ADR-378 §7** names **platform-as-principal** as *"the one implementation
  move that makes the intake model and the actor model consistent in code…
  Highest-leverage single change; not decided here."* It is an explicitly
  preserved seam: the `platform` role exists in `principal_grants` as a
  name-only schema slot with zero write path.
- **DP32's gloss** (ADR-401 D1 §4) reads *"every transport is a principal
  writing a raw observation"* as an INTAKE-SHAPE claim (the source is data), not
  a mandate to provision connector principals.

**The precedent was real, and better than expected.** Production shows FOUR
intake lanes, not two, and `mcp` already attributes raw to the connected
principal (`yarnnn:mcp:Claude`) rather than to a mechanism — because an MCP
client is a principal WITH A GRANT (ADR-431), not a peripheral. Connectors
inherit that shape for DERIVED material. The ADR is an extension of existing
practice, not a foundational decision.

⭐ **Correction to an earlier claim in this file**: the split is not
connector-vs-HTTP. It is *which lanes got a derive step* — `uploads` has one
(`system:extract` → `derivation`), `web` has one (radar/Strings distil), `mcp`
correctly needs none, and `slack` is the gap.

---

## 4. What was already decided, and must not be re-litigated

| Decided | Where | Do not reopen |
|---|---|---|
| A human's connector is their ACCOUNT object | ADR-425 D1 | The Connectors pane belongs in the account door |
| Agents hold NO platform credential; the refusal is reachable | **ADR-577 D1/D1.a** | Do not re-add a second credential store piecemeal |
| `platform_connections.workspace_id` = **routing**, never ownership | **ADR-577 D2** | The owner-fill trigger is CORRECT |
| Capture-lane dormancy is a ratified decision, not an oversight | ADR-404 D2 | Turning it on is a decision, not a bug fix |
| A repo/channel selection binds AGENT REACH, not just capture cadence | **ADR-576 D2** | Empty selection = unrestricted |
| One connect verb for all providers; no per-provider modal | ADR-494 D2 | The absence of a modal is the design |
| Reach ≠ authority — every consequential act still passes ADR-307 | ADR-405 / ADR-566 D1 | — |

---

## 5. Named seams — things DELETED that a future ADR may need to recreate

**Recorded so a future session does not rediscover the need and assume nothing
ever existed.** Each was deleted because it was unreachable, not because the
capability is unwanted.

- **`get_platform_tools_for_user`** (`platform_tools.py`) — assembled platform
  tools for "the YARNNN chat-mode agent". **Zero production callers**; its SIX
  tests (across `test_adr304_*` and `test_adr299_*`) passed by
  `inspect.getsource()` on the function body rather than executing it — one even
  asserted source-string ORDERING of code that never ran. **This is the exact seam where chat-reaches-connector would
  land** if that is ever decided. Deleted as dead code; the DECISION it
  anticipated was never made and remains open.
- **`api/services/delivery.py`** (ADR-577) — fetched credentials outside the
  chokepoint, zero importers.
- **The whole `harvest` feature** (`services/harvest.py`, `routes/harvest.py`,
  its router registration, its syscall row) — it was the ONLY live LLM+platform
  path, and it had zero callers: ADR-437 deleted its FE client block, and
  ADR-577 made its one execution path refuse credentials (it ran headlessly).
  **If a "curate connector material into the commons" capability is wanted, it
  is Bucket 1's subject** — recreate it deliberately with a surface, not by
  reviving an orphan.
- **`landscape.refresh_landscape`** — zero references (discovery + smart
  defaults remain live and power the settings picker).
- **`platform_output.generate_platform_output` / `get_slack_digest_prompt`** —
  zero references; `generate_slack_blocks` is the live entry point.
- **Four FE components** — `PlatformFilter`, `PlatformCardGrid`, `PlatformCard`,
  `DestinationSelector`: referenced only by each other.
- **The workspace credential store** (ADR-577 D1/D3) — the pane, route, card,
  and two-store branch. **Re-entry requires the WHOLE** (allocation door +
  workspace RLS + `UNIQUE(workspace_id, platform)` + a workspace-bearing auth
  object + real `own-agent` grants + the pane) **and a DRIVEN TRACE**
  (ADR-577 §7). Partial delivery is what ADR-577 cleaned up.

---

## 6. Also open, smaller, independent

- **`platform_connections.connected_by`** — named by ADR-407 D5, deferred by
  ADR-425 AD5, extended to grants by ADR-431, **never built on this table**.
  Harmless while every connection belongs to the owner; **required the moment a
  non-owner member connects**, or ADR-401 D3 teardown-on-departure cannot
  identify what to revoke.
- **Connector read breadth** (ADR-576 §5) — no commits, PR diffs, file contents,
  or search. A PR is visible as a title, never as a change. Coherent follow-on
  under the narrowed scope.
- **`PLATFORM_REGISTRY` → `CONNECTOR_REGISTRY` collapse** (ADR-576 §5) — the
  former is fossil canon describing the ADR-076-deleted MCP gateway.
- **The GitHub App / fine-grained-PAT migration** (ADR-576 D1) — the correct home
  for restoring PRIVATE-repo reads without any write authority.

---

## 7. How to resume this discourse

1. **Re-measure §2** — these are point-in-time receipts, and the surface roster
   churns fast.
2. **§3 is ANSWERED** (2026-08-18) — attribution is settled and the contract is
   canon at [`intake-pipeline.md`](intake-pipeline.md). The remaining work is
   the derive step itself: a bounded judgment turn reading
   `inbound/{platform}/{selector}/` and writing understanding into the commons,
   authored `system:derive-{lane} on behalf of {owner}`, citing `derived_from`.
   **Build `platform_connections.connected_by` in the same change** — it is the
   `{owner}` record and has been named in canon three times without being built.
3. **Frame the ADR as "connector data reaching the commons"** — not "GitHub
   derive". The gap is uniform across Slack, Notion, and GitHub, and should be
   decided once at the connector layer.
4. **Fix in passing**: the `slack` lane writes `revision_kind='authored'` for
   RAW; raw is an `observation` (intake-pipeline.md §3).
5. **Decide the DISPOSITION question explicitly**: is connector data meant to
   reach the commons as durable substrate (capture→derive, the radar pattern), or
   to reach a TURN as transient context (chat tool calls, the deleted §5 seam),
   or both? These are different products with different attribution consequences,
   and conflating them is what produced four parallel reach implementations.

---

## 8. Receipts index

| Claim | Source |
|---|---|
| No surface reaches connectors | ADR-576 audit; `lane_runner.py:148/164/173/838`, `freddie_agent.py:924` |
| Capture calls the tool transport | `capture_connector.py:215` |
| `inbound/` quarantined + embed-ineligible | `sync_platform_state.py:97`, `embed.py:53` |
| Only GC reads `inbound/{platform}/` | `connector_retention.py:171-186, 210` |
| Radar/Strings loop closes | `radar.py:22-24`, `strings.py:43-44, 540, 561` |
| Selection declared, nothing flows | production query, 2026-08-18 (§2d) |
| Peripheral is a non-principal | ADR-401 D1 §3 |
| Platform-as-principal deferred | ADR-378 §7 |
