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

## 6. The authoring width ladder (`edf9508` · `d047580`) — CLOSED, click-passed

Docs and Studio are one component and it was the only major surface doing
responsive purely in raw Tailwind classes. Two thresholds disagreed about what a
tablet is: the shell collapses at `MOBILE_BREAKPOINT_PX` (640); the workbench
switched at `md:` (768), spelled in class strings where nothing reconciled them.

Measured on prod before: at **820px** the toolbar row held `clientW 16` against
`scrollW 274` and painted **260px over the Properties column**; at 768 the canvas
iframe was **177px**; at 500 the row still overflowed 210px *with* the tab bar up,
and 27 controls sat below the 44px touch floor.

The row cannot be made to scroll — its galleries are `absolute top-full`, and the
root's own comment said so while doing nothing about it. Fix: **need less width**.
Four rungs (`full · condensed · two-pane · single-pane`), thresholds declared once
beside the shell's own, read through `useWorkbenchWidth`, which measures the
workbench's **own container** (a surface can be narrow inside a roomy window).
Ordering principle: **the canvas never yields** — it was the sole `flex-1` among
`shrink-0` siblings, so it absorbed every deficit.

**`d047580` is the one worth reading.** `edf9508` shipped tsc 0, build 0, 33/33
gate green — and the tablet layout was byte-identical to the defect. The hook took
a `RefObject` and observed it in `useEffect([ref])`; the surface returns its START
state before the workbench, so the effect's only run saw a null node, bailed, and
never re-ran. Measurement right (819px), derivation right (819 → two-pane), nothing
connecting them. Now a **callback ref**. Every gate assertion tested the
DERIVATION, which was never broken — three assertions added for the WIRING.
**Found by driving the doorway, not by a gate.**

Click-passed on prod at three rungs, both apps, incl. emulated iPad-portrait touch:

| rung | before → after |
|---|---|
| 1440 desktop | unchanged — labels, Properties as a column, overflow 0 |
| 820 + touch | overflow 258 → **0**; every verb **44×44**; canvas 177 → **819** |
| 500 phone | tab bar 34 → **44px**; overflow 210 → **0** |

Docs verified on the same tablet: overflow 0, 44px targets, and correctly **no**
page-grain verbs (`hasNewSlide/hasReArrange: false`) — the mode distinction holds
while the ladder lands on both by construction. Overlay opens, scrim dismisses,
Escape closes, `aria-expanded` tracks. Every glyph-only verb keeps its
`aria-label`.

Canon: AUTHORING.md **rule 15**; compositor.md notes the shell's 640 is the
shell's own. Gate: `web/scripts/gates/authoring_width_ladder.mjs` (36 assertions,
executes the derivation at each boundary; all falsifiers fire, incl. reverting the
threshold to 768).

**OWED: nothing on a real device** — the emulation covers pointer-coarse and the
box model, but not thumb reach on hardware. Worth one pass on your own iPad.
