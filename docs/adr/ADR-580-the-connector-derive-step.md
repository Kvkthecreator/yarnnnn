# ADR-580: The Connector Derive Step — connector data reaches the commons

> **Status**: Implemented 2026-08-18 (built + gated + migration 244 applied; the
> lane ships DORMANT behind `CONNECTOR_CAPTURE_ENABLED` — ADR-404 D2 stands, and
> flipping the flag remains a separate operator decision). Pending operator
> ratification of the decisions below; the code is flag-inert until then.
>
> **Dimensional classification (Axiom 0)**: **Mechanism** (Axiom 5 — the distil
> step the connector lanes lacked) + **Substrate** (where derived understanding
> lands) + **Trigger** (the derive pace law).
>
> **Closes**: the open brief
> [`connector-reach-and-the-commons.md`](../architecture/connector-reach-and-the-commons.md).
> **Contract**: [`intake-pipeline.md`](../architecture/intake-pipeline.md)
> (ratified 2026-08-18) — this ADR builds the one stage that document names as
> missing.
> **Amends**: ADR-394 D3 (§D2 below) and ADR-392 §74's letter (§D3 below).

---

## 1. Context — measured, not narrated

The intake pipeline (`retain → distil → signal → read`) ran complete for the
`web` and `uploads` lanes and half-complete for connectors: capture retained
raw at `inbound/{platform}/{selector}/{stamp}.{ext}` and **nothing promoted
it** — the only production reader of `inbound/{platform}/` was the retention
GC. Measured 2026-08-18 (brief §2, re-verified this session): the one
workspace with all three connectors active held a 2061-byte watch declaration,
`captures: []`, zero `inbound/github/` files, zero derived files.

Two ratified theories explain the gap, and both failed the same way:

- **ADR-394 D3** ratified derive "by reference": *the seat's existing
  derive-and-cite act — nothing to build.* In seven weeks the seat never
  engaged connector raw once. A ratified ADR is evidence of a decision, never
  of an implementation (the ADR-373 D6 lesson); D3 was a **documented property
  no path established** (the ADR-577 class).
- **ADR-401 D5** (before its 2026-07-03 amendment) fired a derive wake per
  capture run — and coupled judgment spend to capture cadence (~$60/day on an
  unchanged world). The amendment retired the wake; nothing replaced it.

Meanwhile the working pattern ran daily beside the gap: radar and Strings each
do fetch → retain → **one bounded judgment turn** → living file → commons.

## 2. Decisions

### D1 — Disposition: durable substrate; the transient seam stays closed

Connector data reaches the commons as **durable substrate** (capture →
derive), the radar pattern. Live tool-call reach from a turn (the deleted
`get_platform_tools_for_user` seam, brief §5) is **not** rebuilt: every
decided constraint refuses it — the closed lane allowlists (`lane_runner`),
the steward's closed primitive set (ADR-299 D8), and ADR-577 D1 (agents hold
no platform credential). The derive step needs **no credential at all**: it
reads `inbound/` substrate the capture lane already retained — the only thing
touching a platform API remains deterministic, credentialed machinery. The
named seam stays named; reopening it is its own future decision.

### D2 — The derive step is a standing bounded turn (amends ADR-394 D3)

`services/connector_derive.py`. One derive = **one bounded, tool-less
judgment turn** per watched `(platform, selector)` — the shared derive turn
(D6) reading the sub-lane's fresh raw plus the current digest, returning the
revised digest or the exact token `NO_CHANGE`.

ADR-394 D3's "nothing to build" is amended, not repudiated: the seat MAY still
derive-and-cite when its judgment engages raw (that act needed no new step and
still needs none). What D3 cannot carry is the **lane guarantee** — stage 2 of
the intake contract, "without a distil step, material in `inbound/` is
unreachable by the commons by design." A guarantee needs a standing mechanism,
and seven weeks of zero derived files is the receipt that engagement-only was
not one.

The **pace law** preserves the ADR-401 D5 amendment (`is_due`, pure):

- due only when raw **newer than the deriver's own last digest write** exists
  (a quiet world costs $0 — no turn, no tokens);
- at most once per `DERIVE_MIN_INTERVAL_HOURS` (6) per selector — capture
  cadence (15min–1h) can never multiply judgment spend;
- a member's edit of the digest neither hastens nor delays the clock (the
  clock is the deriver's ledger row, not the file's mtime);
- the capture lane still **wakes no one** — the drain runs on the scheduler
  tick, after the capture drain, inside the same `CONNECTOR_CAPTURE_ENABLED`
  block (capture and derive are one lane; flipping it is one decision).

### D3 — The digest: one living file per watched selector (amends ADR-392 §74's letter)

```
operation/_connectors/{platform}/{selector}.md
```

Beside the platform's `_watch.yaml`, slugified by the same function that names
the inbound sub-lane, prose (no underscore — ADR-254), **embed-eligible**
(under `operation/` — this is what makes stage 4 real), a **fixed leaf** whose
history is the revision chain (ADR-565 D1), member-correctable like any file.

ADR-392 §74 refused "an `operation/slack/` tree — meaning-organized, not
platform-organized." Its target was unbounded platform mirroring, and that
refusal **stands**: raw stays quarantined in `inbound/`, and nothing here
grows with message volume. What this ADR adds is **bounded**: one living
digest per operator-watched selector, living in the connector's own operating
home (`operation/_connectors/` — where the watch declaration already lives),
exactly as radar's report lives in its hub. Subject-placement of durable
insights remains a judgment act — the seat or an app authoring meaning-placed
files **citing the digest** — which is D3's letter honored where it was aimed.

Every digest revision cites the raw it consumed, twice deliberately: the
ledger `derived_from` edge (ADR-448) and a head-anchored `derived_from:` block
in the content — the block is what `gather_cited_raw_paths` reads, so **cited
raw is never pruned** while the digest stands on it, and superseded raw ages
out mechanically when a later revision stops citing it (the revision chain
keeps the historical edge for `trace`).

### D4 — Attribution: the ratified sentence, physically encoded

intake-pipeline.md §3 ratified `system:derive-{lane} on behalf of {owner}`.
The physical encoding follows the ledger's existing architecture (the MCP
lane's identity-rider precedent, stamped since 2026-08-10):

```
authored_by          = "system:derive-{platform}"            (the mechanism)
author_identity_uuid = platform_connections.connected_by     (the owner)
```

The sentence is **composed at display** (`principal_display.display_author`),
never stored: a raw UUID must not ride `authored_by` (`_scrub` would degrade
it, and species classification would leak it), and a display name stored at
write time would freeze a name that legitimately moves. An unresolvable owner
degrades to the plain mechanism string — never a UUID.

### D5 — `platform_connections.connected_by` is built (migration 244)

Named by ADR-407 D5, deferred by ADR-425 AD5, extended to grants by ADR-431 —
never built on this table until now. `uuid REFERENCES auth.users(id)`,
backfilled `= user_id` (measured: every live connection was made by its
owner), **NOT NULL** so a connect door that forgets the stamp fails loudly.
All four insert sites in `routes/integrations.py` stamp it. This is the
`{owner}` record the attribution rides, and the record ADR-401 D3
teardown-on-departure needs the day a non-owner member connects.

### D6 — One turn implementation: `services/derive_turn.py`

Radar shipped the bounded-turn shape; Strings copied it; the connector derive
would have been the third copy — the exact drift this arc exists to prevent.
The turn's **mechanics** (router gate → completion → fence strip → honest
no-change detection) now live in one module; radar, Strings, and the connector
derive all route through it, and each lane keeps what is genuinely its own
(input assembly, posture, placement, write confinement, metering taxonomy).
The ADR-557 D1 guard moved with the call: the shared turn pre-checks the
transport flag, and every lane meters `router_disabled` as configuration,
never as a failed derive. Gate: no lane module calls `route_completion`
directly (`test_adr580_connector_derive.py` §5).

### D7 — The engine is machinery: a `SYSTEM_CALLS` row

`connector_derive` → `anthropic/claude-sonnet-5`, tier standard, env dial
`YARNNN_SYSCALL_CONNECTOR_DERIVE`. The digest is not an app with a resident
(nobody picks this engine; ADR-556's boundary) — it is intake machinery whose
output members read and correct, so quality dominates within a call count the
pace law already bounds. Covered per-row by `test_adr556_system_calls.py`.

### D8 — The 48 slack raw rows are relabeled (migration 244)

`revision_kind` `'authored'` → `'observation'` for
`authored_by='system:sync-platform-state'` under `inbound/` — exactly the 48
rows measured. They predate ADR-423's vocabulary (last written 2026-07-03;
the writer was fixed 2026-07-09 by `f355d26`) and were mislabeled by migration
208's blanket `DEFAULT 'authored'` backfill. Content, authorship, and parent
pointers untouched — a classification flag corrected to the truth the
vocabulary now expresses; ADR-209 intact. **The live writer needed no fix** —
the brief's "the slack lane writes `authored`" was true of the data, not the
code (re-measured this session; the distinction matters because the contract
gate holds writers, and migrations hold rows).

## 3. What this deliberately does not do

- **Does not flip `CONNECTOR_CAPTURE_ENABLED`** — dormancy is ratified
  (ADR-404 D2); the lane is built and gated, and turning it on is the
  operator's decision, made with billing eyes open.
- **Does not give any turn live platform reach** (D1) — the named seam stays
  named.
- **Does not derive the `mcp` lane** — an MCP write is already meaningful
  authored prose (intake-pipeline.md §4); `mcp` not deriving remains correct.
- **Does not add per-connector FE surface** — the digest is an ordinary file
  on the Files surface; a dedicated view is follow-on, not foundation.

## 4. Verification

```
cd api && python3 test_adr580_connector_derive.py      # 33/33 — every §3/§4/§5 check falsified against a broken shape
cd api && python3 test_adr556_system_calls.py          # 63/63 — the new row priced + reasoned
cd api && python3 test_intake_pipeline_contract.py     # 11/11
cd api && python3 test_adr557_router_hardening.py      # 19/19 — roster fixed (pre-existing crash on the ADR-562 move)
cd api && python3 test_adr486_radar.py                 # radar over the shared turn
cd api && python3 test_adr569_strings.py               # strings over the shared turn
```

Migration 244: dry-run showed `UPDATE 3` + `UPDATE 48` (the exact measured
counts), applied, live objects read back: `connected_by` NOT NULL and stamped
on all 3 connections; slack inbound rows all `observation`.

Falsifiers run (each restored by backup-copy): UUID embedded in `authored_by`
→ 4 checks fail; scheduler call un-gated → 4b fails; call deleted → 4a+4b
fail; content citation dropped → 3g fails; pace floor deleted → 2d fails; a
lane calling `route_completion` directly → §5 fails. One falsifier was itself
falsified: `await route_completion` without parentheses is a name, not a
`Call` — the falsifier was rewritten as a genuine call before the check was
trusted.
