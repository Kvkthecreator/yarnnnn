# Session handoff — 2026-08-12 (scope taxonomy + settings surface)

`origin/main` @ `9a09275`. Four commits, all **deployed live** and three of the
four **operator-confirmed on prod screenshots**.

Absorbs the prior ADR-546/544 handoff, whose open items are unchanged and
re-listed in §4.

## 1. What landed

| Commit | What | Confirmed |
|---|---|---|
| `def247b` | **ADR-548** — the scope doorway: 8 member-blind substrate reads + the AST gate that catches them | gates |
| `a4544ce` | **ADR-548 D8** — the contextvar never arrives; 46 sites pass the binding | ✅ operator (member sees the full roster) |
| `8cd9bcc` | **ADR-550** — the members pane says where you stand | ✅ operator (owner header) |
| `9a09275` | **ADR-551** — autonomy is a property of an agent, not the workspace | ✅ operator (group gone) |

### The arc in one line

The operator's framing — *nouns/commons are workspace-level, chats are verbs and
user-based* — **was already canon** (ADR-407 D1, near-verbatim). So the work was
drift-hunting, not law-writing. The verb axis needed nothing.

## 2. The two findings worth carrying

**ADR-548 D8 — a fallback that degrades to a PLAUSIBLE value.**
`substrate_scope_filter(auth.user_id)` with no second argument leans on a
contextvar rung. `get_user_client` is a **sync generator**, so FastAPI runs it in
a threadpool and the async handler reads `None` — resolution falls through to
owner-resolution and serves **the caller's own workspace**. Every query
succeeded; a member just saw less than they should. Diagnosed in one read
because `[SCOPE] … ws=<bound> scope=<actually read>` already existed and the two
disagreed — beside a comment saying they never could.

> **More surfaces should log the bound scope beside the resolved one.** That one
> line turned an invisible class of bug into a five-second diagnosis.

**ADR-551 — "is the mechanism live?" ≠ "is this the right owner?"**
ADR-550 D2 refused the autonomy removal with *correct* evidence and was reversed
the next day. A mechanism can be perfectly live and still be surfaced in the
wrong place. The tell was inside D2's own text: it listed three defects in the
control and still concluded *keep*.

## 3. OWED — two click-passes, both gate-unverifiable

1. **`?workspace-settings.pane=danger`** from the account door's "Clear workspace
   content" link. The shell reads only `{windowSlug}.pane=`; the fix is read off
   the code path and never driven. Two sibling links worked **by luck** (each
   named its door's default pane), so a pass must confirm the *danger* one
   specifically lands on Danger Zone, not Members.
2. **The members header as seulkim88.** The owner side is confirmed. The member
   side is the one that differs: the chip should read *"You're the member"* with
   the narrower hint (*"Only the owner can invite people or change access"*),
   and the workspace name must match the switcher.

Also: `/autonomy` and `/system-agent` now redirect to `/workspace-settings`
(they pointed at the removed pane param) — worth one click.

**The MCP browser lane could not attach this session** — the live Chrome holds
the `chrome-devtools-mcp` profile (`--isolated` or a stopped browser is needed),
and parallel sessions were running. Not attempted rather than reported green.

## 4. Also open (inherited, not this session's)

- ADR-546's click-pass (Tab-nest three deep; select across a heading) + the span
  READBACK (`currentOf` over a mixed-alignment span).
- ADR-544's click-pass; ADR-541 / 539 / 542 click-passes.
- ADR-550 D3's `substrate:`-before-`default:` asymmetry — **moot at the surface**
  now (no pane to be wrong), live for whoever builds the per-agent dial.
- The per-agent autonomy dial, when ADR-382 builds the roster. ADR-551 D5's
  inverted gate (`test_adr238`) is the checkpoint that work must re-cut.
- The prod OAuth-state error (ADR-531 territory) — still uninvestigated.

## 5. Landmarks

- **Scope gates must be run PER-FILE.** `test_adr407_phase2/3` fail only when run
  in the same pytest process as `test_adr373_sweep_spine` — event-loop
  pollution, reproduced identically on a clean baseline. A combined run lies.
- **Baseline reds NOT to claim as yours**: `adr293_governance_taxonomy` (1),
  `commit_f_autonomy_alignment` (8, imports the long-renamed
  `should_auto_execute_verdict`), `adr512_d6_getinfo` (8/9), the ADR-209 guard
  (2 hits, both in `ADR-LEDGER.md` **prose**). All confirmed by stash-baseline.
- **Do NOT delete `governance/_autonomy.yaml`** as cleanup. It has no operator
  surface since ADR-551 but is still read server-side; deleting it queues every
  steward write. The warning is now at the top of `services/review_policy.py` —
  the pane was mis-audited as dead twice, because there is no `/autonomy` API
  route and `grep api/routes/` therefore reads as dead.
- **A concurrent lane was active in this tree all session** (ADR-549, the create
  door). It claimed ADR-549 while this lane was mid-flight — caught by
  re-checking the number at commit time. Its in-progress edits twice broke the
  shared `next build`; each time its files were stashed, this lane's build
  verified, and its work restored intact. Commit with explicit pathspecs.
