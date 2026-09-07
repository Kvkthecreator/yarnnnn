# Session handoff — 2026-08-18/20

Delete a PART in the commit that absorbs it — not the whole file. Parts A–F are prior sessions' owed items and are still open.

---

# Part W — the click-pass Reach was owed, and what looking found (2026-09-07)

Parts U (Reach) and V both ended "⚠️ the browser click-pass is OWED — the
Reach chrome has not been LOOKED AT." It has now. Two of the three owed
items pass; looking found one real bug that no gate could have caught.

## A — the two sessions reconcile

`test_adr643_one_decider` (18, pytest-shaped — it prints nothing when run as
a script, which is why it can look silent), `test_adr644` (53) and
`test_adr642` (51) are **green together at one HEAD**, exit 0 each. They had
never been run in one sitting after both sessions finished. No file overlap
beyond the handoff and the ledger.

Receipts re-verified, not taken on trust: `services/reach_status.py` and the
`reach` kernel row exist; `queue/page.tsx` is a `redirect()` stub;
`connector_does` survives only as its epitaph in two comments;
`lane_runner.py:1117` calls `frame_paragraph(`; CLAUDE.md is 49,999 chars
(50,662 BYTES — the ratchet measures chars, so "measure in chars" is load-
bearing, not pedantry).

## B — the click-pass

**B1 · /reach × 3 panes × 2 themes — PASSES.** Connected shows the five
expected rows; Slack's Agents line reads exactly *"read only — 2 read tools;
cannot send"* and its Writes line names the member's door. WordPress renders
a **fourth** phrasing — *"no reach — this connection carries only your own
clicks"* — correctly, because it has no read tools at all: the structure is
deriving per-connection prose, not filling a template. Leaving and Crossed
render correctly in both themes; Crossed shows the three WordPress receipts
with `publicly_readable: false` rendered as the amber member-legible sentence
*"Live on the site, but no reader can reach it yet"*, and the uploads as
arrivals. Direction markers (↗ LEFT cyan / ↙ ARRIVED teal) stay clear of the
reserved red/amber.

**B2 · the editor re-asked to send to Slack — PASSES.** Live on the deploy
(API on `bafb6bc`, which carries 32fc0ed):

> *"Sending has to happen from your side, in the Text pane's Send to Slack
> action, not through me."*

No "check Settings", no "steward" (a role ADR-632 retired). It names the
member's actual door from its frame, without calling a tool first. The
transcript still holds the pre-deploy answer directly above it — *"worth
checking Settings … or asking your steward"* — so the same lane, same file,
same question, is the before/after pair. ADR-644 verified end to end.

**B3 · one real Slack send — NOT DONE.** Deliberately deferred: it posts to
a real channel, and I have no standing authorization to publish outward on
the operator's behalf. It needs the operator's own click (or an explicit
instruction naming the channel).

## The bug that looking found

`/reach?reach.pane=crossed` cold-loaded onto **Leaving**, rewriting the
address bar to `?reach.pane=leaving` under the member. Every shared or
bookmarked pane deep-link was broken. `reconcileUrl` merged
`{...incoming, ...remembered}` — the remembered pane outranked the link just
pasted — while the capture block four lines above already stated the intended
rule ("we must adopt it, not blow it away").

It hid because the surfaces people actually share (Text, Images) carry their
file in an EPHEMERAL key that is stripped from `remembered` before the merge:
document links worked while every pane link silently did not. Verified live —
`text.file` survived the same cold load that dropped `reach.pane`.

Fixed at `4283039`, and the query half now agrees with the pathname half,
which settled the same question on 2026-08-20 (the URL is EXPLICIT INTENT).
The merge is extracted pure into `route-sync.resolveSurfaceParams` beside its
sibling so the gate EXECUTES the precedence — a reordered spread is invisible
to a substring check. Falsified against the pre-fix order: 27/28, exactly the
reported-bug check goes red.

**Verified fixed live** (Vercel, 14:22): `?reach.pane=crossed` holds and
renders Crossed; a bare `/reach` still restores the remembered pane (no
regression); and `?reach.pane=connected` beats a freshly-remembered `crossed`
— the exact case that was broken. Web lane marked validated.

**The lesson, and it is the arc's own:** three sessions of gates went green
over this. A gate cannot see a wrong pane, and neither could tsc. Only the
click found it — the same shape as ADR-641's "a colour decision has to be
LOOKED AT" and yesterday's optional-permission-field regression.

## C — the three baseline-red gates: RETIRE, with the drift derived away

`aea2638`. The ruling: retire the recurrence assertions (ADR-603 D5 deleted
the concept — a mirror must exist to be fronted, so there was nothing to
re-anchor onto), and replace every hand-spelled roster literal with the
ADR-592 derivation.

Reading them showed the red was a **queue of stale slugs, not one**: at the
pre-arc commit they failed on `queue`; re-anchoring that line only advanced
the failure to `recurrence`. Behind it:

- ADR-340's search-only set named **six** slugs that no longer exist and
  missed **three** that do — drift in BOTH directions, which is exactly why a
  one-directional check never caught it (the ADR-636 lesson, recurring).
- ADR-349's `main()` called `test_agents_upgraded()`, a name that no longer
  existed, so the gate **crashed before its last two tests** — hiding for ~7
  weeks that `agents` was re-promoted to primary on 2026-07-16.
- ADR-340's constitution-band block read `HomeHeader.tsx`, deleted with Home
  by ADR-435. `_read` returns `""` for a missing file, so three "deleted"
  checks passed **vacuously** while the one positive check failed.

Two real defects fixed rather than asserted around: `AttentionCenter`'s
`goTo` union still offered `'tune'`, a pane key ADR-639 renamed to
`'standing'` (a silent no-op navigation had anything called it); and ADR-346
asserted mounts that ADR-639/642 had replaced.

Both new derivations are falsified in both directions — demote a tier while
its stage stays primary → red; add a served primary-stage row with no tier →
red (the direction the drift used).

**`sources` (owed item 6) needs no ruling — it is already discharged.**
It looked like an ADR-592 violation only because the gates read the raw
`KERNEL_SURFACES` constant. `internal` rows are retained there BY DESIGN (the
slug must resolve for its redirect stub) and removed by
`kernel_surface_entries()`. `/sources` is already a redirect stub with no FE
registry row, no slug in the union, no middleware line. The tier contract is
about what a member can reach, so the gates now read the served roster.

## Still owed

1. **B3** — one real Slack send, to a channel the operator names (their click).
2. The remote binding ADR (a file that knows its remote) — two tenants now.
3. WordPress's D8 read-back (`read_post` behind the seam + a canary).
4. ADR-635's distribution: registry publish, plugin-directory submission,
   the attach click-pass (operator acts).
5. Carried since Part O: `projection.ts`'s second CSV parser · a Files door
   for declaring standing work · blogger's standing leg.

## Baseline-red, NOT touched (pre-existing, verified by stash)

`test_adr297_navigation_enactment` · `test_adr340_p2_settings_fold`
(`autonomy`/`budget` panes deleted) · `test_adr422_files_legibility`. Same
stale-roster family as the three above; each needs its own ruling. They were
red before this session's first edit — confirmed by stashing and re-running,
not assumed.

---

# Part V — ADR-644: one reach status (2026-09-07)

Operator, after the Reach click-pass showed the surface and the editor
disagreeing: *"agents and display should reference the same status …
permissions edited elsewhere … no different from Claude/ChatGPT
connectors. Aligned in full."*

**Shipped.** `services/reach_status.py` — ONE structure per first-party
connection (`platform_reach` · `reach_status` · `connection_rows`) with two
renderers (`describe` = the member face on Connectors + Reach;
`frame_paragraph` = the lane frame's reach section, all four ADR-535 states
+ one line per connection naming the read tools, any composed write tool
with its gate mode, and the member's door). `list_integrations` returns the
same rows (description rewritten, CHANGELOG `[2026.09.07.7]`).
**Deleted**: `connector_does`, the three hand-written reach branches + the
`.6` sentence, `PUBLISH_VERBS` (→ `PUBLISH_DOORS`), the commerce/trading
branches of the tool result, the second `platform_connections` read in the
LIST route and the tool handler. ADR-635's `attached_surface` is the
sibling structure for attached rows, untouched.

**The precedent for the next face**: anything that tells a member OR an
agent what a connection lets a turn do reads `reach_status`. A new sentence
anywhere else is the fifth face.

Verification: `test_adr644` (driven: four states through the generator;
tool result + LIST route compared row for row to the structure; the
write-tool falsifier flips every face) · 535 · 585 · 628 · 582 · 642 · 577 ·
the two prompt ratchets · the CLAUDE.md ratchet · next build · the frame
paragraph driven on prod read-only.

⚠️ Owed with Part U (Reach): the browser click-pass of Reach × 3 panes ×
2 themes; the editor re-asked to send the doc to Slack (it should now name
the Send to Slack door from its frame, not from a tool call).

---

# Part U (Reach) — ADR-642 Reach + Slack, the second outbound tenant (2026-09-07; the parallel session's Part U, the access decider, is below)

Operator, after a strategic discourse (*am I steering wrong, given the labs'
agents becoming the hands on Office/Figma?*): *"proceed with 2–3 … reach and
outbound can drastically 'feel different to the user, even our first real
customer' from day one."* Distribution (ADR-635 owed) deliberately follows.

## The read that produced it

Axiom-0 census of the live roster: five What-surfaces, one Who, one When,
one How, **zero Where at the front door**. ESSENCE's moat sentence is a
Channel claim. Since 2026-07-09 commits touching the studio apps outnumber
the interop face ~4:1 — the summer built five What-surfaces on the one
altitude the OS analysis (§4, same day) said not to. Not a wrong vision; a
drifted roadmap. The apps FREEZE at reference depth (the agent-native
format for unattended work + a viewer), the interop face leads.

## Shipped

- **ADR-642** — `reach`, PRIMARY kernel surface, cyan. Connected (integrations
  LIST now serves `does` + capture freshness + which declarations read the
  connection) · Leaving (`QueueBody families={['external-write','capital']}`)
  · Crossed (`GET /workspace/timeline?lens=boundary`, receipts parsed from
  the sidecar, material). `queue` absorbed: stub → `/reach?reach.pane=leaving`,
  middleware, `DOCK_RETIRED_SLUGS`, To-do escape hatch re-pointed. Dock:
  `DEFAULT_KEPT_SURFACES` +reach and a reseed generation.
- **ADR-628 amendment 3** — Slack in `services/publish.py`: prose only
  (by extension, before the read), mrkdwn contract, join-before-post
  (`join_channel`'s FIRST caller — it had none), refusal codes mapped,
  **D8 read-back mechanized** (`matched|differs|unreadable` on the receipt).
  `SendToSlack` on the Text pane only. Two Slack writers PINNED (seam +
  the ADR-304 tool handler).
- **`connector_does` writes from the publish seam AND the LIVE surface** —
  it said *"nothing — yarnnn never writes to Slack"*; my first fix read the
  capability registry and claimed an agent proposal path, which the
  operator's first click-pass falsified within the hour (the editor,
  asked to send a doc to Slack: *"I cannot post"* — true; the lane composes
  read rosters only; `write_slack` is a registry fossil of the deleted task
  pipeline). Now derived from `turn_reach_tool_names`, driven both ways.
  The lane frame names the member's door (CHANGELOG `[2026.09.07.6]`).
  Scope legibility fixed the same pass: Connected = the viewer's account
  connections; Leaving + Crossed = this workspace; each pane says so.
- Fixed en route: `StudioPublish`'s raw `<a href>` to Connectors (the nav
  gate had been red on it since 2026-09-01) → `navigateToSurface`.

## Verification

```
test_adr642 (51) · test_adr628 (74, §8 new) · 592 (43) · 636 · 641 · 338 · 297_phase1 · 297_nav ·
nav_no_cross · auth surface + page · 582 · 639 · 635 (89) · 577 · 427 · 494 · 576 — all GREEN
next build exit 0 (/reach 10 kB, /queue a 414 B stub) · routes gated locally (307 → login; API 401)
DRIVEN on prod (read-only, service client): boundary lens 40 rows — 3 WordPress receipts attached
(material), uploads/captures as arrivals (routine); no lens → 0 receipts, invocations back.
BASELINE-RED, untouched: test_adr346/349/340 on ADR-603's `recurrence` (their queue lines re-anchored).
```

⚠️ **The browser click-pass is OWED.** The chrome-devtools profile was held by
a parallel session's Chrome (pid 75971, 13:28, `--remote-debugging-pipe`);
a fresh profile has no session; the CLI is not installed. The composer's
heading bug (`*H*` re-read as italic → `_H_`) was caught by the gate's
fixture, not by eyes — the Reach chrome itself has not been LOOKED AT
(ADR-641's lesson). First thing next session: open `/reach` on the deploy in
both themes, all three panes; then the Text pane → Send to Slack… against a
real channel (needs Render's key; local cannot decrypt) and read the receipt
on Crossed.

## OWED

1. The click-pass above (Reach × 3 panes × 2 themes; one real Slack send).
2. The remote binding ADR (a file that knows its remote) — now has a second
   tenant to bind to.
3. WordPress's read-back (D8 still unmet for it); phase (b)'s narrow identity.
4. ADR-635's distribution: registry publish, plugin-directory submission,
   the attach click-pass.
5. `test_adr346/349/340`: retire or re-anchor on ADR-603 with a ruling.
6. `sources` (ADR-335 bundle watches, hidden since ADR-425): delete or
   re-home — a separate ruling (ADR-642 §4).

---

# Part U — the access decision gets one decider (2026-09-07)

Operator, on the audit: *"I just want to make sure our implementation doesn't
result downstream, to create similar divergences. And thus, a more singular,
long standing solution and conceptual framing that will be future proof."*

The audit's four findings are symptoms. The subject is the recurrence, and it
has a name.

## The mechanism

ADR-501 wrote the lesson down: *"a permission fix must enumerate the doors, not
the deciders."* It enumerated the TWO doors it knew about and shipped.
`test_adr570` then ratcheted those two BY NAME. **Enumeration is not a
structure — it is a to-do list that expires silently**, and a hand-named
ratchet cannot go red for a door nobody added to it. Seven more doors were
written afterwards; the gate stayed green through all of them.

⭐⭐ **A carve law is not an authorization check.** `operator_can_organize`
looks like permission (bool on a path, callers raise 403) but is a
filesystem-INTEGRITY rule about path SHAPE, identical for every principal.
`constitution/` `persona/` `governance/` `contract/` all PASS it deliberately.
A door asking only it has asked nothing about the caller.

## Shipped

| | |
|---|---|
| `151f71d` | ADR-501's sweep re-pointed at standing work (radar deleted) — 23/23, was 20/23 |
| `a3b2ecb` | ADR-535 re-cut across all four reach states; found a branch that had **never executed** — 35/35, was 19/21 |
| `940c400` | the audit |
| `cf8bf18` | **D1** — 7 doors + 1 loop gained the consult; the ratchet DISCOVERS the roster |
| `873e153` | **ADR-643** + ledger |
| `3f9dffd` | **D2** — `services/access.py`; the stale N=1 premise corrected |

⭐⭐⭐ **The discovery gate found FOUR doors the manual audit missed** —
`move_folder_route` · `create_folder` · `create_artifact` ·
`set_default_design_system_route` — on the commit that introduced it. If a
future change adds a name to a literal roster in
`test_adr501_every_door_asks.py`, the gate has been defeated: fix the door.

⭐⭐ **Driving the decider found a bug reading it would not have.**
`may_edit_as_prose` routed at the `write` verb, so a `.md` under raw `inbound/`
reported EDITABLE, against ADR-422 D2. The FE's own `isArrival` check was right
about that one; it is the `system/` carve it omits.

## ADR-643 COMPLETE — D1 through D6 (`332bf1b`, `d3dd403`)

**D3** — `access_summary` rides `/workspace/tree`, `/workspace/file` and
`/workspace/roots`; `ownership.ts` and its three re-derivations DELETED.
⚠️ An ABSENT decision reads as PERMITTED everywhere — offer the act, let the
door explain (ADR-400 A1 preserved). `_access_or_none` degrades to `None` and
the gate asserts it can never degrade to a permissive dict.

**D4** — `isShapeCarved` adds the missing `system/` carve so
`resolveSurfaceApplication`'s comment becomes true; `isTextEditable` is shared
with the Recents filter that had the same omission. `ProseCanvas` gains
`readOnly` on a CodeMirror **Compartment** (the extension list is memoised on
`[]`, so a plain extension could not change without remounting and dropping the
caret). Both `readOnly` and `editable` are set — the first alone leaves a caret
that silently eats keystrokes.

**D5** — `/workspace/system/` out of `editable_prefixes`.

**D6** — all nine doors call `resolve_access` by verb.

### ⭐⭐⭐ THE SAME SHAPE, THREE LEVELS UP, IN ONE ARC

1. **The doors** — hand-composed, seven of nine asked half the question.
2. **The gate's own roster** — `ROUTE_MODULES` was a literal 3-tuple, so
   `routes/images.py` was never scanned and my falsifier for it passed GREEN.
   Discovering the module list found two more live doors: `images.compose` and
   `standing_work.update_standing` (a declaration schedules UNATTENDED spend).
3. **The fixtures** — `test_adr400`'s `_Auth` carried no `caller_identity`, so
   `_caller_class` resolved it to the **agent** class: the tests measured a
   member's ceiling while claiming to assert the operator's reach. Invisible
   while the door asked only the principal-blind carve law.

**A discovery gate with a hand-listed corpus is a hand-listed gate.**

### Three gates went red on the change that removed the drift they guarded

`test_adr555` ×2 pinned the SPELLING `operator_can_organize(`; the doors now
ask the decider, which composes that law **with** the grant — strictly more.
`test_adr400`'s fixture, above. All re-pointed, none satisfied.

## ✅ CLICK-PASSED live (2026-09-07, Render `dep-daf9ns942hec73d174pg`)

```
GET /workspace/file  system/skills/writing-a-spec/SKILL.md
    → access {may_write:false, may_organize:false, may_edit_as_prose:false,
              code:"system_managed", reason:"“SKILL.md” is used by the system…"}  ✅
GET /workspace/tree  root=/workspace/governance
    → both rows carry access; may_write TRUE (owner), may_organize FALSE
      (machine leaf), may_edit_as_prose FALSE (not prose) — three DIFFERENT
      answers on one row, which is the point ✅
/text  system/skills/…/SKILL.md   canvas contenteditable="false", banner shows
                                  the SERVER's sentence ✅ (screenshotted)
/text  operation/engineering/ownership.md   editable, no banner ✅
```

⚠️ **`constitution/MANDATE.md` stays editable for the OWNER — correct, not a
miss.** ADR-320 says constitution is the operator's own intent. The bug was
never "the owner can edit it"; it was that Text could not tell the owner from
anyone else.

## ⚠️ ONE REGRESSION FOUND BY THE CLICK-PASS, FIXED, AWAITING ITS BUILD

Right-click `governance/_autonomy.yaml` → Rename opened the RENAME MODAL where
it used to explain the carve. The decision rode the row correctly (verified in
the live React tree: both children carry `code:"machine_config"`) and was
dropped one layer later — every organize verb REBUILDS its target at the
menu/hook boundary, and a rebuilt object carries only the keys it was written
with. The guard saw `access: undefined` → "unknown → offer the act".

⭐⭐⭐ **A permission fact that is OPTIONAL BY DESIGN cannot be type-checked into
place.** It must be optional (an undecorated row has to degrade to asking), so
`tsc` is blind to a surface that forgets it and the server still refuses, so
nothing errors. Only driving the gesture shows it. The FE has no equivalent of
the backend's discovery ratchet.

Fixed in `3774a5b`: `FileMenuTarget` — the ONE shape every file surface builds
— gains the field; Files' four rebuild sites go through one `withAccess`
helper; TextEditor + Studio's three artifact verbs pass the loaded decision.
Studio's recents feed deliberately passes none (a revision list, not a tree
row) with the reason in a comment.

**✅ VERIFIED LIVE** after its build landed:

```
/files governance → right-click _autonomy.yaml → Rename…
   → “_autonomy.yaml” can’t be changed / “…is a settings file the system needs
     in this exact place. Moving, renaming, or deleting it isn’t allowed.”
     rename modal did NOT open ✅ (screenshotted)
/files operation/engineering → right-click review-conventions.md → Rename…
   → rename modal opens, no carve dialog ✅  (the non-vacuous twin: a blanket
     refusal would have satisfied the check above and been wrong)
```

⚠️ Vercel builds take ~12 min and the API deploys separately on Render. A
click-pass run before the FE build lands reads as a defect in code that is
correct — it cost two false diagnoses here.

⭐⭐⭐ **Do NOT check "is it deployed" by curling the page and grepping its
chunks.** A Next.js route lists **zero** `/_next/static/chunks/*.js` in its
served HTML (they load dynamically), so that loop searches an EMPTY corpus and
reports "not deployed" with total confidence. Mine ran 600s and said exactly
that about code I had already driven working in the browser. Ask the browser
instead:

```js
performance.getEntriesByType('resource')
  .filter(e => /_next\/static\/chunks\/.*\.js$/.test(e.name))   // 48, vs curl's 0
```

then fetch those and grep. **A negative from a search is worthless until you
know the corpus was non-empty** — and when a probe disagrees with a driven
gesture, suspect the probe.

## THE RECEIPT THAT MATTERS

Driven against REAL production grant rows, not a stub:

```
live grant classes:  mcp 12 · operator 11 · agent 6
  agent  constitution/MANDATE.md   OLD trash=ALLOWED → NOW 403
  agent  persona/IDENTITY.md       OLD trash=ALLOWED → NOW 403
  mcp    constitution/MANDATE.md   OLD trash=ALLOWED → NOW 403
  mcp    persona/IDENTITY.md       OLD trash=ALLOWED → NOW 403
```

**18 non-owner principals could destroy what they could not write.** Closed.

## NEXT

1. Old item, now stale — was: click-pass once `dep-daf9ns942hec73d174pg` is live: `/text` on
   `constitution/MANDATE.md` (banner + no caret), `/files` on `governance/`
   (menu still offers, dialog still explains), and a `system/skills/**`
   SKILL.md (must NOT route to Text at all).
2. The remaining hand-composition: `services/upload_tickets.py:119` still
   calls `operator_can_organize` directly — it is a service, not a door, but it
   answers a placement question and should ask the decider.

## SUPERSEDED — the pre-D6 next-steps (rulings already taken)

1. **D3** — serve `access_summary` on the file + tree payloads; **DELETE**
   `web/lib/workspace/ownership.ts` and the three re-derivations in
   `web/lib/file-types/index.ts` (`resolveSurfaceApplication`,
   `isArtifactCandidate`) and `TextSurface.tsx:89`. Operator ruling: *server
   decides, client is told*. ⚠️ Files' Windows-Explorer model (offer the verb,
   explain the refusal) is PRESERVED — it was never the problem; only the
   source of the explanation changes.
2. **D4** — Text routes only prose AND renders read-only what the viewer cannot
   write (operator ruling: *both*). AMENDS ADR-572 D8, does not overturn it:
   still ONE canvas, still no modes, one state driven by the served decision.
   `ProseCanvas` gains the `readOnly` it deliberately lacks.
3. **D5** — `editable_prefixes` deleted or conjoined in `edit_workspace_file`
   (it re-admits `/workspace/system/` one line after the carve law rejects it;
   the refusal works today only by accident of `CALLER_WRITE_POLICY`).
4. Then move the eight backend doors onto `resolve_access`, one per commit,
   deleting each hand-composition as it moves (no shims).

## Baseline-red, NOT this work (identical with changes stashed)

`test_adr422_files_legibility` 1/23 · `test_adr386_member_lifecycle` 1/17 ·
`test_folder_verbs_and_download` (script-style, collects 0 under pytest).

## Still owed from Part T

`projection.ts`'s second CSV parser · a Files door for declaring standing work ·
blogger's standing leg · the `/images` export click-pass (item C, unrun).

---

# Part T — the owed list, closed (2026-09-07)

Operator: *"lets do the remaining owed, pending items."* Six items, one commit
each would have been ceremony; one commit, six receipts.

## 1. `assembling-a-composite-document` — measured: NULL, rank 2

Capture: [`analysis/assembling-a-composite-document-measured-2026-09-07.md`](analysis/assembling-a-composite-document-measured-2026-09-07.md).
24-row CSV, the ask naming the subject word for word, ARM B = the slug
withheld from the in-process kernel index, n=3/arm interleaved, purged after.

```
rows_copied_fraction   A 0.292/0.250/0.292 (0.278)   B 0.292/0.250/0.333 (0.292)   p = 0.500
read the skill         A 0/3   B 0/3        provenance line (posture)   A 2/3   B 3/3
```

⭐⭐⭐ **The craft is the model's own.** Both arms wrote the same document to
the paragraph: three Q3 rows under the provenance line, Q2 and the prior
year in prose, a standup figure marked as *not* from the metrics file — the
skill's step 5, done by an arm that never read the skill. And naming the
subject did not reach the body (0/3): the description states the craft, so
the lane conforms without reading (Part M, third sighting). `_INDEX_RANK` → 2
(measured-null); kept, never pruned on a score. CHANGELOG `[2026.09.07.3]`.
⚠️ My log filter (`grep -v "^\s+"`) erased every per-trial line; only the
left-aligned summary survived. Filter tracebacks by token, not indentation.

## 2. The reach receipt (Part P owed 1) — BUILT

`_reach_connector_sources` returns a per-platform receipt (`captured` ·
`unchanged` · `unreadable` · `nothing_selected` · `no_binding` ·
`unconnected` · `fresh` · `raised`) and the sweep names it: *"no landed
snapshot — reach unreadable (…)"*. The run's `no_sources_fetched` result
carries `reach` + `errors`. "Did not move" and "could not be read" are now
different strings on the ledger. ADR-594 D2 carries the note.

## 3. The GitHub aperture (Part P owed 2) — the honest string at the door

No commit tool exists (`platform_github_*`: issues · repos · readme ·
metadata · releases), so the binding was NOT widened. `StandingSource.reads`
serves the binding's own `reads` statement; the roster shows it per connector
source; the declaring skill says to check it before declaring (no
per-connector string duplicated into prose).

## 4. The `ADR-411 D4` phantom — SWEPT

33 sites / 26 files → `ADR-408 D2 · ADR-460` (the member-embodiment
attribution is ADR-408 D2, preserved by ADR-460; ADR-411 has no numbered
decisions). Lines that DESCRIBE the phantom (handoffs, ADR-640's finding, the
analysis that found it) kept; ADR-411 gains a banner so the next reader
learns why "D4" resolves to nothing.

## 5. `agent-composition.md` §3.2.1 — RE-CUT

Now a destination per KIND of fact (grammar → registries via the posture ·
how an artifact works → the app's posture · the participant contract →
kernel constants · reach → gates · craft with a contract → a skill · a
program's judgment → its `principles.md`, vestigial · pedagogy → the guide ·
anything a gate enforces → nothing), the diagnostic test, the evidence bar,
and the two observed failures (a fact written twice drifts; a fact written
nowhere an engine reads is a fact the engine does not have). The pre-ADR-632
partition is kept verbatim as the historical record. CLAUDE.md's pointer
dropped its warning.

## 6. ADR-640 D2's two rows — BUILT

`craft` (kernel skills whose apps meet the agent's: Designer 4 · Editor 11 ·
Blogger 7, a presentation of `_applies_to`) and `tending` (declarations whose
`resolve_executor` is the agent, read ONCE per envelope from the same
discovery the drain runs) ride the agents payload; two read-only rows on the
agent's page, every entry a Files door. Gate §5: both derivations asserted,
no ledger read, and neither key is a request field on any route.

## Verification

```
test_adr640 GREEN (§5 new) · test_adr639 · test_adr618 · test_adr630 (147) · test_author_grammar
test_adr624 · test_claude_md_ratchet · probe/eval staleness gates · web build green · tsc clean
BASELINE-RED, not this work's (identical at HEAD): test_adr535 (2/21) · test_adr501 (reads the
deleted routes/radar.py). Recorded, not fixed — each needs its own ruling.
```

## ✅ CLICK-PASSED live (2026-09-07, after `cbcc73d`; Render `dep-daf29tnavr4c73blevbg` live, Vercel `main-app-59a52978`)

```
/agents            roster renders (Designer · Editor · Blogger) — the first snapshot caught the LOADING frame,
                   whose copy is "Could not load this." (initial state null); the surface itself was fine
/agents?agent=editor   Craft row: 11 skills in rank order (deriving-a-design-system · presenting-from-sources ·
                   writing-a-spec · … · assembling-a-composite-document · comparing-options · …), each a Files door ✅
                   "Keeps current" row ABSENT — correctly: the workspace holds ZERO declarations. The ledger shows
                   `operation/fundraising/_standing.yaml` "retired at operator request" at 02:36:29 and a
                   `_lifecycle-probe-2026-09-07/` declaration created/archived/cleaned at 02:48–02:49 — the
                   PARALLEL SESSION is working the standing lifecycle on prod right now. `tasks` (kind=standing): 0 rows.
                   The derivation is proven by gate §5; the row will appear with the next live declaration.
roster reads line  no connector source is declared live, so nothing to see; composed locally through `_summarize`:
                   github → "issue and pull-request activity (latest 50, all states) from each selected repo", url → null ✅
```

⚠️ **A loading state that reads as a failure.** `AgentsSurface` starts `agents` at
`null` and renders "Could not load this." until the fetch resolves — the same
sentence as a real failure. A snapshot taken on navigation read it as a defect
for one round. Not changed here (it is a copy choice, and the fetch is fast);
noted so the next click-pass waits a beat.

## OWED

1. `test_adr501_read_path_binding.py` reads `routes/radar.py`, deleted with
   ADR-603 D5 — a gate that cannot run; re-point or retire with a ruling.
2. `test_adr535_connector_visibility.py` 2/21 red at baseline — read the two.
3. Carried from Part O (still open, untouched here): `projection.ts`'s second
   CSV parser · a Files door for declaring · blogger's standing leg.
4. `./relative` image paths in markdown — refused in D5; only if asked.

---

# Part S — composition-by-reference: Stage 1 answered, three decisions SHIPPED (2026-09-07)

Commit `94aa578` (+ the docs commit that absorbs `docs/SESSION-NEXT-PROMPT.md`,
now deleted). Operator: *"aligned in full … delegate implementation details …
singular streamlined discipline … can commit push to main with quick testing."*

## What Stage 1 returned (drove it rather than reading about it)

A `.md` never passes through `projection.ts` — it is drawn by `ProseCanvas`
(the ONE surface since ADR-572 D8) and `MarkdownRenderer` (thumbnail + print
only). So the old thesis's `data-ref`-for-Text half is DEAD: a `data-ref` in
markdown is inert markup. **But ADR-572 D17/D18 had already ruled the markdown
composition grammar** — image by workspace path, diagram as a mermaid fence,
CSV as a GFM snapshot under `_From `path` · snapshot YYYY-MM-DD_` — and the
two bound Text drives that "retyped the CSV" produced exactly the toolbar's own
snapshot shape minus the provenance line. The claim-grain citation the carry-
over prompt was reaching for existed; nothing told the lane.

Measured: `text_pane_posture` (1,349 B) named none of the three forms; the
lane frame, standing frame and connector carry only `derived_from`; the `.md`
grammar lived in three FE insert functions where no engine could read it.
Prod, reproduced through CodeMirror's own input path: mermaid ✅ svg · CSV
snapshot ✅ table · `![laptop](…png)` ❌ underlined word, real `<img>` = 0.

## The three decisions, each shipped with its receipt

**1. The canvas draws the image (ADR-590 D5).** ⭐⭐⭐ D17 shipped Insert →
Image ONE DAY after D8 made the canvas the only surface, and gated it (17g)
against `MarkdownRenderer` — the face D8 had just demoted. Three weeks, gate
green, no picture. ADR-590's own census of "eleven rendered things" had no
image row. Now: `ImageWidget` (block figure with alt caption + the shared edit
affordance; inline at text height), resolution moved to ONE function
(`lib/workspace/imageUrl.ts`) both faces call, `blobUrl` gone from both. And
**the reveal returns**: D3's `collapseFence` effect was never dispatched
anywhere — an opened diagram stayed as source until reload. A revealed block
now folds back when the caret leaves it (opening places the caret inside).
Gate: 17g = the one resolver reached by both faces; **17h mounts the canvas**
and counts the `<img>`. *A gate that names a component proves the component,
not the surface.*

**2. The posture carries the grammar — and it works.** +584 B, consequence
stated (the line IS the citation; a `data-ref` in `.md` is inert). Driven on
prod, same fixture and ask as the two failing runs, `run_lane_turn` with the
real Editor engine, each trial in its own folder, purged after (18 rows → 0):

```
provenance_line_present   treated 3/3   control 0/2   → exact permutation p = 0.100 (the n=3 floor)
t1–t3: rounds 4, figures 1,850/2,310/3,040 present, q3.csv named, skill NOT read
```

Receipt shape (t1): the table, then `_From `…/q3.csv` · snapshot 2026-09-07_`,
the argument in prose around it. **Not promoted to a kernel constant** — the
one query first: five connector-authored `marketing/strategy/*.md` read for
the same failure; every figure-bearing one names its sources near the figures
(the connector's host already does this). CHANGELOG `[2026.09.07.2]`; first
posture byte ceiling (2,100; 1,933 at ship).

**3. ADR-475 §13's opt-in, built.** `POST /api/images/export` lands the
browser's raster at `{artboard folder}/exports/{stem}.png` as
`revision_kind="derivation"` + `derived_from=[artboard]` — a STABLE path, so a
re-export is a new revision and a document's `![alt](path)` keeps resolving.
"Save PNG to workspace" beside "Download PNG"; one rasterizer feeds both. The
server still never rasterizes. Executing gate in `test_adr475` (lands,
derivation edge, binary lane, 422/404/403 refusals write nothing).

## Method findings

- ⭐⭐⭐ **A gate red at baseline hides the failure behind it.** `test_adr475`
  was 0/1 at HEAD: the compose handler's draw gate 402'd the fake user, and
  behind THAT sat ADR-568's keyless refusal (`no_provider_key`). Neither was
  this arc's, both were stubbed where the handler reaches them; 58/58.
- ⭐⭐ **A background shell is not your shell.** `pnpm` is not installed at all
  (the build runs via `npm run build`), and `node` lives only in
  `/opt/homebrew/bin` — the first background run reported "exit 0" for a build
  that never started, and every node-mounted probe in two gates went red for
  the same reason. `export PATH=/opt/homebrew/bin:$PATH` first; and a sweep
  that fails everything is a broken sweep, again.
- ⭐⭐ **The router flags live on Render, not in `.env`.** A laptop probe that
  drives `run_lane_turn` needs `MODEL_ROUTER_ENABLED=1` + `LANES_ENABLED=1`
  in-process, or every trial "fails" with a refusal that looks like a result.
- ⭐ **The DevTools `type_text` tool scrambles markdown punctuation** in
  CodeMirror; drive the canvas with `execCommand('insertText')` from
  `evaluate_script`. The prod bundle hides `cmView`.
- An object literal key cannot be a concatenated string. One syntax slip took
  the build AND both canvas gates red at once; `tsc --noEmit` is the 30-second
  check before a 6-minute build.

## Verification

```
api: test_adr571 (277 ok, incl. 2d/2e/2f + 17g/17h/17h1/17h2) · test_adr590 (20/20)
     test_adr475 (58/58, was 0/1) · test_adr472_endpoints_execute · test_adr632 (73)
     test_adr630 (147) · test_adr606 · test_claude_md_ratchet · probe/eval staleness gates
web: npm run build green (the mermaid/langium warning is pre-existing) · tsc clean
prod: the posture drive above (3/3). CLICK-PASS: see below.
```

## ✅ CLICK-PASSED live (2026-09-07, prod, DevTools browser as the operator)

Driven on `/agents/_adr427-phase2-test/scratch.md` (restored after) and the
`operation/untitled-image/image.html` artboard:

```
canvas   ![A laptop](marketing/assets/…laptop.png)   → figure.cm-mdImage, <img> 864×1184 loaded, caption, edit affordance   ✅
         ![ball](…yarnball…png) inside a sentence    → span.cm-mdImageInline, <img> 1254×1254 loaded                        ✅
         source line hidden; mermaid svg + snapshot table still render beside them                                            ✅
reveal   press "Edit image" → the line opens (cm-mdFenceOpen), figure count 0                                                ✅
         ⚠️ first pass showed "A laptop" — the preview pass still hid the URL → fixed in 8f14a3c (17h3 asserts the path)
collapse ArrowDown off the line → figure count 1, image still decoded                                                       ✅
         re-verified on the 8f14a3c bundle: the open line reads `![…](operation/untitled-image/exports/image.png)` ✅, and
         a real ArrowDown folds it back to the figure ✅ (a synthetic KeyboardEvent does NOT move CodeMirror's caret — use press_key)
export   Export → "Save PNG to workspace" → "Saved to workspace ✓" in 2.5 s                                                   ✅
         ⚠️ first pass: POST /api/images/export died CORS-less = an unhandled 500. The handler wrote the binary with the
         member's JWT; the private CAS bucket refuses it (the compose leaves' 2026-07-21 lesson, and test_adr475's own
         comment). Fixed in e6f6893 — service client for the write, the member's client for the existence read; the gate
         now captures WHICH client reached the write (it had dropped `_db` and passed 58/58 against the defect).
ledger   operation/untitled-image/exports/image.png · 98,022 B · image/png · head a4fc9fb9
         revision_kind='derivation' · derived_from=['/workspace/operation/untitled-image/image.html'] · authored_by operator ✅
loop     ![WORK DIFFERENT — exported from the artboard](operation/untitled-image/exports/image.png) in the Text doc
         → figure 688×688 on the canvas, natural 2160×2160 (1080² at 2×)                                                    ✅
```

⭐⭐⭐ **The exported PNG was BLANK — and so was every "Download PNG" since
2026-07-22.** The screenshot showed the figure's 688×688 box as white; the DOM
said the image was decoded at 2160×2160 — and both were right: sampled in-page,
**0 non-white pixels of 291,600**. Then the SHIPPED Download PNG on the pre-fix
bundle, saved to `~/Downloads` and sampled with Pillow: **98,022 bytes, the same
size, 0 non-white of 291,600.** The rasterizer snapshots a host pinned at
`position:fixed; left:-99999px`, and html-to-image copies the host's computed
style onto the clone it draws inside an SVG foreignObject — so the whole stage
rendered 99,999px outside the canvas. Fixed in `861d176` (the clone gets
`position:static` at 0,0; the live host stays off-screen). *Nobody could see it
while the raster only ever left as a download — a stage with neither a receipt
nor a refusal. Landing it in the workspace made it a file the substrate can
show, and the first one it showed was empty.* Also a correction to my own
read: I first called the white capture a "stale frame from a backgrounded tab".
It was a true frame of a white image; the edit affordance is hover-only, which
is why it appeared only in the third capture. **"Decoded" is not "shows
something" — sample the pixels.**

**After `861d176` (bundle `1e72c370`):** Save PNG → "Saved to workspace ✓" in
5.0 s → head `5755a2ca`, `derivation`, parent `a4fc9fb9` (a re-export is a new
REVISION of the same path ✅) → the Text doc's `![…](…/exports/image.png)` figure
sampled in-page: **4,767,867 B · 2160×2160 · 274,679 of 291,600 non-white** ✅.
Screenshot: the composed artboard, in the document, as a picture.

The composite skill's craft question (copy the few figures the argument uses,
not the whole table) is unexercised by a 3-row fixture — carried in OWED.

## OWED (this Part)

1. **Measure the composite-document skill** (still rank 1, unmeasured; the
   posture now carries the shape, so the skill's remaining value is the
   judgment — "keep the copy small" — which t1–t3 did NOT exercise: all three
   copied the whole 3-row table, which is fine at 3 rows and is the thing to
   measure at 30).
2. `./relative` image paths in markdown — refused in D5 (both faces fail
   alike); open it only if asked.
2b. ✅ **CLOSED by observation.** The exported artboard's headline ("DON'T COPY
   PASTE FOR A LIVING") is not in the canvas's a11y tree, which raised the
   question of whether the raster draws a hidden layer. One screenshot of the
   canvas: the same headline, same placement — the three rail rows named
   "Heading" are those lines, and the a11y tree simply omits them. The export
   matches the canvas; nothing to chase.
3. Carried: `agent-composition.md` §3.2.1 re-cut · the standing run's reach
   receipt · the GitHub aperture · the `ADR-411 D4` phantom (33 sites) ·
   ADR-640 D2's two derived rows.

---

# Part R — `composing-an-image` measured bound; the index admits by evidence (2026-09-07)

Closes Part Q owed 1 and 2. Commit `9499432`. Capture:
[`docs/analysis/composing-an-image-in-a-bound-lane-2026-09-07.md`](analysis/composing-an-image-in-a-bound-lane-2026-09-07.md).

## 1 — the bound-lane probe (Part Q owed 1) — DONE

Verified first that the missing piece was real: `studio_pane_posture` composes
**17,475 bytes** carrying `data-x`/`data-z` for a bound lane and nothing
unbound. Fixture built through production's own path (`build_skeleton` +
`stage_root_attrs`), not hand-rolled.

```
             positioned_frac (pre-registered)      read the skill
ARM A index  1.00 / 0.00 / 0.50   mean 0.500       3/3
ARM B none   0.00 / 0.00 / 0.00   mean 0.000       0/3
exact permutation p = 4/20 = 0.200
```

⭐⭐⭐ **Does NOT clear the n=3 floor of 0.100** — the floor needs perfect
separation and **trial 2 broke it from the treated side**. All six runs
completed (no exclusions — binding the lane removed probe 8's starvation).

⭐⭐⭐ **Why it disobeyed a rule it had just read**: the agent stamps `data-z`
exactly when layers OVERLAP and omits it otherwise. Coherent visual reasoning,
and wrong — the rule serves the **layer rail**, not the picture. **A CONTRACT
SKILL MUST CARRY ITS CONSEQUENCE, NOT JUST ITS RULE.** An unmotivated
unconditional rule loses to visible local reasoning ~2/3 of the time. Step 2
amended; the "layers stacked at the same `z`" anti-pattern DROPPED (it
contradicts ADR-633 §5b — a tie is legitimate).

⭐ **Discovery vs compliance are separate things and only the first is
reliable.** 3/3 vs 0/3 reach, and the compliance gap still runs entirely in the
skill's favour — but "directionally strong, not separated" is what the capture
says, and the rank table says it too (`composing-an-image` is deliberately
rank 1, not rank 0).

## 2 — the index admits by EVIDENCE (unplanned, and the more useful half)

Adding a twelfth skill **evicted `writing-a-spec`** — our best-evidenced skill
(7/7/7 vs 1/0/2) — from the Text index. The budget admits alphabetically and
truncates the tail.

⭐⭐⭐ **`UNBOUND_INDEX_CEILING` had already been RAISED TWICE for exactly this**
— its own comments say so ("drops real skills by ALPHABETICAL ACCIDENT";
"withheld the eleventh skill by alphabetical accident"). A budget that evicts
by alphabet evicts at random with respect to what the row is worth, and raising
the ceiling buys one skill while leaving the next eviction just as arbitrary.

`_INDEX_RANK` / `_index_rank`: measured-to-separate (0) → unmeasured (1) →
measured-null (2), alphabet as tiebreak only. **No ceiling was raised.** Sizes:
unbound 3,819/4,000 · text 3,199/3,400 · slides 2,762 · images 1,750 · blogger
2,762. A slug moves rank only with a capture behind it.

## 3 — the composite-document skill (Part Q owed 2) — SHIPPED UNMEASURED

⭐⭐⭐ **The boundary ruling was made on the wrong posture, and this is the
finding to carry.** I ruled it by reading `_blocks_grammar(app)` — 18 kinds
with worked markup, so the skill could name no tag. **True of slides/images/
blogger; FALSE of Text.** `text_pane_posture` is **1,347 bytes** of plain prose
(*"No block grammar, no Studio machinery"*), and `all_layouts()` shows Text
owns **no artifact layout at all** (deck→slides, post→blogger, image→images).
**A posture read for one app was generalised to a registry of apps** — invisible
because it ran the right direction for three of four, and the fourth was the
one I scoped to.

Rewritten for prose against the observed failure (two bound Text runs retyped a
CSV's figures with the source uncited). **Ships at rank 1, unmeasured** — two
drives that never reached it are evidence of the gap, not that the skill fills
it.

## Method findings

- ⭐⭐⭐ **A scorer can read the PROMPT instead of the artifact.** My first pass
  reported 21 `data-block` kinds in the output; they were in the skeleton's own
  **stylesheet**, and 21 is the *slides* roster — which should have been the
  tell. Sanity-check any count that matches a table you did not expect.
- ⭐⭐⭐ **On macOS, clearing `__pycache__` in the tree does NOT clear Python's
  bytecode cache.** It lives in `~/Library/Caches/com.apple.python/<abs path>/`.
  A falsification edit's stale `.pyc` survived `find api -name __pycache__ -delete`
  and made a correct source file (`0`) import as the falsified value (`2`) — the
  AST literal and the runtime dict disagreed on a bare import. Verified by
  comparing `ast.literal_eval` against the live object.
- ⭐⭐ **A gate can assert a CENSUS while the code beside it proves truncation.**
  `test_adr630` tested self-truncation with 20 fake skills **and** asserted the
  real index lists every skill. Both could only hold while the roster fit; the
  12th made the second false and the gate went red on correct code.
- ⭐ **The confirming first trial did not replicate, for the third arc running.**
  t1 was a perfect 1.00-vs-0.00 — exactly the shape that gets written up as
  p=0.100 if the probe stops there.

## Verification

9/9 green, scoped to what the change reaches (no runtime path outside skills/
index composition is touched):

```
cd api && python3 test_adr630_skills.py    # 147/147, incl. new §3a-rank
  test_adr632_the_seat_retires · test_adr639_standing_work
  test_adr640_no_agent_record  · test_agent_registry (125/125)
  test_adr633_the_artboard_is_layers · test_adr606_pane_sees_the_member
  test_adr636_app_declaration_parity · test_claude_md_ratchet
```

Ranking falsified in-process (demote `writing-a-spec` → evicted → restore →
returns). Probe artifacts purged from the prod workspace (verified 0 remaining).

## OWED (this Part)

1. **Measure the composite-document skill** — needs an ask that names its
   subject (neither drive reached it) plus an arm comparison. It is rank 1 until
   then.
2. **`agent-composition.md` §3.2.1 still needs its post-steward re-cut** (Part Q
   owed 3, untouched). CLAUDE.md routes every prompt-change session there.
3. Carried, still open: the standing run's reach receipt · the GitHub aperture ·
   the `ADR-411 D4` phantom (33 sites / 26 files → ADR-408/460) · ADR-640 D2's
   two derived rows, if wanted.
4. ✅ **`operation/fundraising/market-sizing/` — CLOSED by observation
   (2026-09-07).** There is no such folder. The live substrate holds
   `operation/fundraising/market-sizing-reference.md` with its declaration at
   `operation/fundraising/_standing.yaml` (the workspace's ONE standing
   declaration), next run 2026-10-01. Parts P/Q described a probe folder that
   does not exist — nothing to keep or unwind. ⚠️ *An owed item phrased from
   what a probe was believed to have done outlived the thing it described;
   the check was one query.*

---

# Part Q — what a skill is FOR: contract, not craft (2026-09-04)

Direct sequel to Part P's Thesis A, which found the skills index had **no
measurable effect on output quality** over three skills. That was real and
incomplete: those three teach craft a frontier model already has. The operator
asked whether to prune the weak skills and drop the index. Both steps run in
full; the answer to both is **no**, and the second reversed the hypothesis the
early evidence supported.

Commits: `8c696ad` (code + capture) · `df797d2` (canon hardening).
Capture: [`docs/analysis/what-a-skill-is-for-contract-vs-craft-2026-09-04.md`](analysis/what-a-skill-is-for-contract-vs-craft-2026-09-04.md).

## Step 1 — which skills earn their bytes

Real `run_lane_turn` against live prod, ARM A = live frame, ARM B = the same
frame with `skills_index_section` → `""`. **One PRE-REGISTERED measure per
skill**, taken from its own `SKILL.md` before any data existed; every other
column printed *exploratory*.

⭐⭐⭐ **A skill pays when it carries a right answer THE MODEL HAS NO PRIOR FOR
— one of this workspace's own shapes.**

| separates | null |
|---|---|
| `writing-a-spec` 7/7/7 sections vs 1/0/2 — **p=0.100**, the exact-permutation floor at n=3 | `reviewing-drafts` · `writing-updates` |
| `deriving-a-design-system` 15/18/17 kernel CSS vars vs 7/0 — **p=0.100** | `comparing-options` · `summarizing-sources` |
| `presenting-from-sources` CSV beside the deck | `keeping-a-file-current` · `declaring-standing-work` |

⭐⭐⭐ **The failure is SILENT, which is why a skill can never be pruned on a
quality score.** `design_systems.py` discovers a system BY the presence of
`_design.yaml`; a folder without it is invisible to the platform while looking
like a plausible folder of CSS. The skills worth keeping are precisely the ones
whose absence a reader cannot see. **Nothing was deleted** — a null is an
argument about the current engine, not the file, and `LANE_MODELS` makes a
weaker one live.

⚠️ **`composing-an-image` is NOT MEASURABLE unbound**, not null: it defers its
token grammar to the pane posture, which `authoring.py` composes only for an
artifact-bound lane. It read the skill and refused to invent a coordinate
grammar — correct under a starved harness. **Owed: a bound-lane probe.**

## Step 2 — the roster stays

Three arms × four skills × three trials: full roster · a **360-byte pointer**
("list `system/skills/` and read the one that matches", naming no skill) ·
nothing.

```
A roster   3,312 B   reached the skill 100%   writing-a-spec 7/7 · 7/7 · 7/7
T pointer    360 B   reached the skill  58%                  1/7 · 0/7 · 7/7
B nothing      0 B   reached the skill  42%                  0/7 · 0/7 · 0/7
```

A vs T p=0.038; ⭐⭐⭐ **T vs B p=0.682 — the pointer is INDISTINGUISHABLE FROM
NOTHING.** ARM T produced the contract exactly when it happened to read the
skill. The roster buys the RELIABILITY of the read, and on a shape-carrying
skill **the read IS the outcome**. Argue the ceilings on **reach-rate, never
byte count** (receipt now lives on `INDEX_CEILING`).

⚠️ **This inverted the early hypothesis.** An unaided arm really does find a
skill by listing the folder — but only when the ask names the skill's own
subject (*"make that a reusable thing"* → `creating-skills`). Generalising from
that one case would have cut 3,000 bytes and taken contract compliance 100% →
58%, silently.

## What shipped

`8c696ad` — the split + its consequence in the `services/skills/` docstring;
the three-arm receipt on `INDEX_CEILING`; **new §"What makes a skill worth
writing"** in `creating-skills/SKILL.md` (the actionable half, so the next
author reads it before writing); CHANGELOG `[2026.09.04.3]`. Every composed
index is **byte-identical** — edits touch bodies and comments, never a
`description`.

`df797d2` — canon hardened where a future session would read the stale claim:
ADR-630 amendment banner (D6's *"unmeasured prose"* is now measured);
**GLOSSARY's Skill row, which said "never contract" and read backwards**;
`lane-frame.md` §7b gains the reach receipt; `agent-composition.md` §3.2.1
flagged — CLAUDE.md sends every prompt-change session there and it predates
skills, partitioning against a persona-frame in the deleted `api/agents/`;
CLAUDE.md's protocol bullet names the skill as a destination.

## Method findings (three arcs' worth, all the same shape)

⭐⭐⭐ **A skill makes an agent do MORE — search for evidence, look for the
referent, refuse to invent a grammar. An A/B that scores completion naively
systematically penalises the arm that is behaving correctly.** Three of four
harness defects did exactly this:
- the **round cap measured itself** (`_LANE_MAX_ROUNDS=8`: the arm following
  "evidence per criterion" ran out and scored 0 files against one that just
  wrote — raised to 16 for the probe);
- a **non-completion is not a zero** (two runs hunting a design system the
  probe's own purge had deleted — *the treatment created the starvation*);
- a skill **writes outside the run folder** (`skills/{name}/`), so its output
  was neither captured nor purged and the control read it as an example;
- **a shared parent folder is a shared example shelf** — an opaque name hides a
  run from a sibling listing, not from the ROOT listing agents actually do.

⭐⭐ **Distrust the confirming first trial.** Part P's 22-vs-5 citation gap
reached p=0.500 by n=6. One pre-registered measure per arm, everything else
labelled exploratory, is what stops that.

## OWED (this Part)

1. **`composing-an-image` in a BOUND Images lane** — the only kernel skill still
   unmeasured, and the probe design that would do it is understood.
2. **The nested-document / composite-artifact skill** the operator raised (a
   document with a table, images, context-specific components). It is a
   CONTRACT skill — the category with evidence — but needs a ruling first: the
   *judgment* goes in the skill, the *tag vocabulary* stays in the posture
   (ADR-601 D1), or it becomes a second home for a fact (the ADR-562 failure).
3. **`agent-composition.md` §3.2.1 deserves a real re-cut** for the post-steward
   frame; `df797d2` only flagged it. CLAUDE.md still routes every prompt-change
   session there.
4. Carried from Part P and still open: the reach receipt
   (`_reach_connector_sources` catches an exception a never-raising writer
   cannot throw) · the GitHub aperture (issues+PRs cannot observe a commit-only
   repo) · the `ADR-411 D4` phantom citation (33 sites, 26 files → ADR-408/460)
   · ~~`operation/fundraising/market-sizing/`~~ (**CLOSED 2026-09-07 — no such
   folder exists; see Part R owed 4**) · ADR-640 D2's two derived rows, if wanted.

---

# Part P — the two theses tested: skills discovery, and the Agents page (2026-09-04)

Follow-up audit to ADR-639. Two rulings, each with a falsifier that was
actually run. Capture:
[`docs/analysis/skills-discovery-and-the-agents-page-2026-09-04.md`](analysis/skills-discovery-and-the-agents-page-2026-09-04.md).

## Thesis A — "skills as files let agents compose documents in a rich way"

**Ruling: discovery works; the composition claim is NOT supported.** Real
`run_lane_turn` against live prod, 3 asks × 2 arms (ARM B = the identical
frame with `skills_index_section` → `""`), n=6/arm on the one ask that does
not saturate the round cap, plus a 3×2 clean-folder rerun.

- **Discovery: real.** Skill body read in **6/10** ARM-A runs vs **1/10**
  ARM-B. In a cold folder ARM A reaches the skill in 1 round, ARM B in 4.
- **Composition quality: null.** Inline citations **p = 0.500** (exact
  permutation, 924 splits); `derived_from` 2.00 vs **2.50** (against);
  sources read identical; rounds identical. ⭐⭐⭐**Five runs produced
  BYTE-IDENTICAL declarations with the index on and off** — same SHA-256 on
  both `_standing.yaml` and `CONTRACT.md`.
- ⭐⭐⭐**The measured effect is on the REFUSAL, not the output.** In the clean
  folders ARM A wrote nothing in 2/3 runs because it *asked the member for the
  cadence* — which is `declaring-standing-work` step 2 and its anti-pattern
  *"a schedule tighter than anyone reads (every run spends the member's
  balance)"*. ARM B guessed weekly and wrote, 3/3. That is the ADR-633 §5a
  effect, and it protects spend rather than prose.
- ⭐⭐⭐**The load-bearing mechanism is the MIRROR, not the index.** ARM B found
  both skills by `ListFiles system/` in 3/3 cold runs. Do not propose saving
  frame bytes by dropping the mirror and keeping the index — that is backwards.
- **Argue the ceilings on rounds and refusals from here**, never on quality.

## Thesis B — "evolve the Agents page in full"

**Ruling: no evolution of shape. → ADR-640 (`test_adr640_no_agent_record.py`).**

Six facts audited by counting callers. Three are already served (who · which
app · what it learned). Two are derivable-but-unserved and now PERMITTED
read-only (**craft**: skills whose `metadata.apps` meet the agent's apps —
Designer 4 · Editor 10 · Blogger 7; **tending**: declarations whose
`resolve_executor` is it — both live ones → `editor`). **The sixth is
REFUSED and that refusal is the ADR.**

⭐⭐⭐**A truthful per-agent history is not summable in the present tense.** The
only agent-shaped join is lossy (162/200 ledger rows carry `session_id`) and
**historically correct in the way that makes aggregation false**: 25 lanes
truthfully read `app='text' agent='designer'`, all dated 08-14→20, because
**ADR-602 moved Text to Editor on 08-24**. My first reading called them a
stamping defect; they are nothing of the kind. "Designer — 25 documents" is
true about August and false about now, and a roster has no honest place to say
which.

⭐**Citation hygiene**: `member:{id} via {model}` is cited **33× across 26
files as "ADR-411 D4"** — and ADR-411 has **no numbered decisions**. It is
ADR-408's rule, preserved by ADR-460. *A citation that resolves to a file but
not to a decision reads as verified.* Owed, not swept.

## OWED item 1 from Part O — SETTLED, and both hypotheses were wrong

Not "writes only on change" and not "degrades silently". **The binding reads
issues and PRs, never commits** (`platform_github_get_issues`), and
`Kvkthecreator/yarnnnn` has had **no issue or PR since 2026-07-08** while
committing to `main` daily — verified against the live GitHub API. The reach
ran, hashed identical bytes, and correctly skipped.

⭐⭐⭐**The real defect is the receipt, and it is structural.**
`run_connector_capture` documents itself as *never raising*; the only handler
in `_reach_connector_sources` is `except Exception`. **The failure mode the
writer actually produces is unloggable by construction**, and its rich return
(`paths_written` / `paths_skipped` / `error`) is discarded. That is why the
04:26Z `standing-sweep` receipt says `status='success'`, 1,001 ms, with no
field that could hold a reach outcome — a run whose sources all failed and one
whose sources were all unchanged emit byte-identical receipts.
⭐ *A `try/except Exception` around a function documented never to raise is not
error handling; it is a comment that reads like error handling.*

## Method findings worth carrying

- **The first trial confirmed the thesis and was a false positive** (22 vs 5
  citations → p = 0.500 by n=6). Distrust the confirming first run.
- **The substrate is a craft-transmission channel** — every later trial read an
  earlier ARM's output as an example. Scope every artifact per arm, or the null
  result is manufactured.
- **Score completion before speed** — ARM A "won" latency 3/3 by not finishing.
- ⭐**A background job you stopped reading is not one that stopped — and
  killing the parent does not reap the child.** A plausible `259 PASS / 108
  FAIL` baseline was wrong: three stray `test_adr209_*` processes from aborted
  runs were still writing revisions to the same prod workspace and reading each
  other's. Check for CHILDREN, not just the driver.
- ⭐⭐**Scope verification to what the change can reach.** This arc alters **no
  runtime code** (three docs + one new gate), so a 367-gate sweep could not
  regress anything and its reds are all environmental. Two sweeps were burned
  before noticing. The 15 gates covering the touched surfaces were run
  uncontested and all pass; **no full-sweep figure is claimed here, because
  none was honestly obtained.**

## Verification

No runtime code changed (three docs + one new gate file), so verification is
scoped to the surfaces the change reaches. **15/15 green, run uncontested:**

```
cd api && python3 test_adr640_no_agent_record.py    # NEW — every section falsified individually
                  test_agent_registry.py            # 125/125
                  test_adr639_standing_work.py   test_adr630_skills.py
                  test_adr624_the_being_has_a_home.py   test_adr631_vocabulary.py
                  test_adr618_standing_spend_gate.py    test_adr606_pane_sees_the_member.py
                  test_adr636_app_declaration_parity.py test_adr632_the_seat_retires.py
                  test_adr533_participant_contract.py   test_adr558_chat_is_engines.py
                  test_adr614_cast_follows_the_registration.py
                  test_adr612_agent_connector_opt_in.py test_claude_md_ratchet.py
```

ADR-640 gate falsification (each applied, observed red for the stated reason,
reverted): a `last_active` key on `_agents_payload` → 2 red · `run_history` in
`AGENT_ROW_KEYS` → red · a `.eq("agent",` on `execution_events` → red · an
impure `resolve_executor` → red.

## OWED

1. **The reach receipt** — read `run_connector_capture`'s return into the sweep
   receipt so "did not move" and "could not be read" stop looking identical
   (ADR-594's seam).
2. **The GitHub aperture** — issues+PRs cannot observe a commit-only repo.
   Widen the binding, or surface the binding's own honest `reads` string at the
   declaration door.
3. **The `ADR-411 D4` phantom** — 33 sites, 26 files → cite ADR-408/460.
4. ~~**`operation/fundraising/market-sizing/`**~~ — **CLOSED 2026-09-07: the
   folder does not exist.** The file is at
   `operation/fundraising/market-sizing-reference.md`, declared at
   `operation/fundraising/_standing.yaml`. The original entry, preserved as
   written: the probe moved the operator's
   REAL `market-sizing-reference.md` into its own folder with a correct
   monthly declaration (3 verified source URLs), now live (next run
   2026-10-01). **Left deliberately**; keep or unwind is the operator's call.
   All other probe artifacts removed (34 files, 6 index rows).
5. **Orphan `tasks` rows** survive a deleted `_standing.yaml` — inert
   (`_due_standing` skips them), hygiene only.
6. **ADR-640 D2's two derived rows**, if wanted — one commit, both derivations
   already pure.
7. Carried from Part O, still open: `projection.ts`'s second CSV parser (2);
   a Files door for declaring (3); blogger's standing leg (4).

---

# Part O — ADR-639: standing work is a kernel lane; strings + Supervisor dissolved (2026-09-04)

The apps · agents · skills · envelope audit (operator: *"is the concept closer to
just spinning up sub agents and skills"*) tested the thesis and found it HALF
right: strings was SEVEN things wearing one name, and none of them dissolves
into an agent. The full clean-up shipped in this arc — ADR-639 is the record.

**What moved.** `services/strings.py` → `services/standing_work.py` (the
maintained file, `_standing.yaml` + `CONTRACT.md`, `kind='standing'`,
`system:standing`); the run's system prompt is `lane_runner.build_standing_frame`
(the lane frame minus tools/reach/cast/focus/register/index, plus the kernel JOB
and the `keeping-a-file-current` skill BODY); two kernel skills
(`keeping-a-file-current` [text] · `declaring-standing-work` universal); ONE
drain loop in `scheduling.py` (`claim_run` · `record_run` · `drain_due`) that
capture rides too; `routes/standing_work.py` = roster + Pause + Run now at
`/api/standing`; the Notifications **Standing work** pane. DELETED: the strings
app/surface/pane (1,645 lines), `routes/strings.py`, `standing_declarations.py`
(zero callers), the Supervisor row, the Files "Keep this current…" door, the
steward fossil `StandingBand`, four gates whose subject is gone.

## ⭐⭐⭐ Findings worth carrying

- **The standing run composed a SECOND envelope** outside the one composition
  site — no commons contract, no citation rule, no mandate head — and nobody
  had decided that. A frame composed away from its module loses clauses silently.
- **n=2 existed for the DRAINER, not the declaration.** Capture ran a byte-twin
  loop on the same table since July; ADR-603 D6 waited for a "second kind" that
  (blogger) has opposite cardinality and would have split the shape. Generalise
  on the axis that has evidence.
- **Three gate checks matched their own documentation** (a comment naming the
  retired slug / glyph / file) before asserting the ROW. Assert the mechanism.
- **The budget loop reserved an overflow line for the LAST admission**, which
  can never need one — an eleventh skill that fit was withheld. Fixed beside the
  ceiling raises (bound 3,000→3,400, open 3,400→4,000, both with the receipt).
- **A widened sweep found a real second CSV parser** in
  `web/components/workspace/viewers/projection.ts` (`parseCsv` + `splitCsvLine`).
  ADR-571's ONE-parser law names it; recorded OWED, not asserted (a gate red on a
  defect the arc does not fix teaches the wrong lesson).

## Verification (the standing set at ship)

```
cd api && python3 test_adr639_standing_work.py          # new — D1..D5, every check falsified
cd api && python3 test_adr630_skills.py                  # 11 kernel skills, every lane under its ceiling
cd api && python3 test_agent_registry.py                 # {editor, designer, blogger}
cd api && python3 test_adr632_the_seat_retires.py        # §5 ratchets (conventions 683/900)
cd web && node_modules/.bin/next build                   # exit 0
```
34 affected gates re-anchored and green; full sweep diffed against a HEAD
worktree (see the ledger entry for the counts). Pre-existing reds, untouched:
`test_adr297` (sources/program parity + a raw anchor in StudioPublish),
`test_adr573` §5 (CONNECTING.md verb roster), `test_voice_no_kernel_nouns_in_copy`
(8 admin-page nouns).

## Data + deploy sequence (ADR-639 §4)

1. Migration **251** (`funnel_decision` gains `standing`) — APPLIED 2026-09-04
   before the deploy (dry-run clean, then real).
2. Code deployed (this Part's commit).
3. Migration **252** (rename `_string.yaml` → `_standing.yaml` on files +
   versions; re-key the one `tasks` row; re-stamp the strings lanes `app: text`)
   — apply AFTER the API deploy is live: `scripts/db/run-migration.sh --dry-run`
   then real. Measured before writing: 1 declaration · 1 index row · 2 revisions
   · 18 ledger rows (untouched) · 7 cast rows (untouched).
4. **DRIVEN 2026-09-04 04:26–04:28Z** (migration 252 applied 04:26Z; API deploy
   `dep-dad4foajnfac73e74uag` live 04:25:37Z). `GET /api/standing` served the
   roster with `app: text` DERIVED and the pre-rename `string-write` row as
   `last_run` (the legacy prefix reads history). `POST …/run` → 200 in 47s,
   `revision e55e09d8`, ledger `standing-sweep` (mechanical) + `standing-write`
   (judgment, claude-sonnet-5, **$0.0829**, `funnel_decision='standing'`,
   `principal_id=owner`); the revision is `system:standing` / `derivation` /
   `derived_from=[inbound/github/…/2026-08-28T01:45:25Z.md]`, message *"kept
   'application-copy-bank.md' current (standing run, 1 source)"*. The scheduler
   cron ticks on the new code every minute (`_standing.yaml` LIKE-scan → index →
   due scan → `[SCHED] tick complete`, no tracebacks). **Browser pass** (minted
   link, isolated context): Notifications → Standing work renders the row
   (target · cadence · next Sep 5 1:00 PM · 1 source · Run now · Pause · *"Ran —
   the file was updated · Sep 4, 1:27 PM"*); the Dock shows no Strings.

   **The craft, evaluated (ADR-633 §5a — noticed / refused, not "was it read").**
   The old posture reported `no_change` on 09-03 and 09-04 04:01 against the
   SAME landed snapshot; the new frame (skill body + contract + mandate head)
   ADDED the one section CONTRACT.md names as the run's responsibility ("What's
   been built"), which the file did not have at all, as 22 terse bullets with
   11 inline citations to the repo's PRs — the contract's own shape ("briefly,
   in the same voice, cite"). So the skill changed what the run NOTICED: the gap
   between the contract's named section and the file. Two caveats, both honest:
   (a) the material was **7 days stale** — the reach found the GitHub connection
   active and the newest snapshot older than the freshness floor, yet no new
   snapshot landed (see OWED 2); (b) some bullets restate PR-era claims that
   canon has since retired (recurrences, `/schedule`) — the run is faithful to
   its source, and the source is stale; that is (a) again, not the craft.

## OWED

1. ~~**The GitHub reach landed no fresh snapshot**~~ — **SETTLED in Part P**
   (2026-09-04). Neither hypothesis was right: the binding reads issues and PRs,
   never commits, and the repo has had no issue/PR since 2026-07-08 while
   committing to `main` daily. The reach ran and correctly skipped an unchanged
   snapshot. The real defect is the **receipt** — `except Exception` around a
   writer documented never to raise — and the **aperture**. Both re-owed in
   Part P.
2. **`projection.ts` second CSV parser** — fold into `markdownEdits.parseCsv`
   with a `maxRows` option; then widen `test_adr571` 18L's sweep back to the whole
   components tree.
3. **A Files door for declaring** (right-click → open the file's Text pane with
   "keep this current" seeded) — one commit if demand names it (ADR-639 D6).
4. **Blogger's standing leg** — its own parser (a generator's `NO_CHANGE` means
   "no post this week"), riding `drain_due`; ADR-628 phase (b) conditions.
5. ~~**Drive `keeping-a-file-current`** as craft~~ — **DONE in Part P**. Driven
   as an A/B (index composed vs suppressed) across three asks. Answer: it
   changed what the agent **REFUSED** (asked for the cadence rather than
   guessing one that spends the balance) and did **not** measurably change what
   it produced (five runs, byte-identical declarations across both arms;
   citations p = 0.500).
6. Absorbed from earlier Parts: OWED "strings ledger rows carry no
   `principal_id`" (already stamped — every `record_execution_event` in the
   standing module carries it; `test_adr445_principal_attribution` green) and
   Part N items 3–4 (the blogger declaration is item 4 here; "supervisor-
   scheduled publish" reads "a standing run's publish" — there is no Supervisor).

---

# Part N — the outbound seam DRIVEN: ADR-628 D6/D7/D8 (2026-09-03)

`6b3565d` — the click-pass ADR-627/628 left owed since 09-01 ran, twice.

**Drive 1 (post 6, live).** Transport sound on the first attempt: site listing,
credential, blogger-only guard, platform call, attributed receipt — the first
`_publish.yaml` row workspace-wide. **Composition** — the one stage with
neither a receipt nor a refusal — failed 3 ways and reported success: 33,978
bytes in, 39,706 out, body = doctype + `<head>` + stylesheet published AS PROSE.

⭐⭐⭐ **WordPress strips `<style>` TAGS but KEEPS THEIR TEXT** — with its
typographic filter applied to the code. A local dry run cannot predict what a
platform does to bytes it receives; only a round-trip can.

⭐⭐ **The audit question is "which stage can neither refuse nor receipt?"** —
not "which stage is complex?". Every guarded stage worked first try.

⭐ **The gate certified its own fixture**: it composed only
`build_skeleton("post")`, which ALWAYS has `<main>`, so all three defects passed
clean. And when I added assertions, TWO of them passed vacuously until the
fixture carried a `<style>` INSIDE the content root and a quote-abutting
`data-` attribute — falsify every new assertion individually.

**Fix (D6/D7/D8).** The three-regex chain DELETED: content root `<main>` →
`<article>` → `<body>`, transport-hostile elements dropped WHOLE, and a
**refusal** where the fallback used to be. Receipt now carries
`publicly_readable` (D7) and `derived_from` (D8).

**Drive 2 (post 7, draft, post-deploy):** 216 bytes composed (was 39,706);
amber banner renders "Your site is not launched yet…"; deployed sites endpoint
returns `"public":false`; receipt row 2 carries both new fields with
`revision_kind='derivation'`.

## OWED

1. **Delete malformed post 6** on yarnnn9 (live-but-private). The WP client has
   no delete verb BY DESIGN — manual step in the WP dashboard.
2. **Mechanize the read-back.** D8's round-trip is half-done: what was SENT is
   verified, what WordPress STORED is not (a draft reads empty
   unauthenticated; the authenticated read needs `INTEGRATION_ENCRYPTION_KEY`,
   Render-only). A `read_post` verb + canary is phase (b)'s precondition.
3. **`test_adr577` §6 is pre-existing RED** (confirmed at HEAD, not this arc):
   the allowlist cites `services/freddie_envelope.py` and
   `services/primitives/system_state.py` — both deleted by ADR-632 — and
   `routes/agent_connectors.py` is an unlisted reader.
4. **Next: the blogger rebuild** (operator-aligned, not started) —
   `sources → judgment → composition → draft → publish`, with strings as
   REFERENCE not substrate. The reason is cardinality: strings maintains ONE
   file forever, blogger GENERATES many. ADR-569 D1's named-deferred refusal of
   authoring artifacts was a *revision* collision and does not bind a
   generator. Two rulings still open: is `draft` a PLACE or a STATUS FIELD, and
   does unattended `live` belong in the target design at all?

---

# Part N — the connector directory + attached connectors: ADR-635 (2026-09-03)

## What shipped

| Commit | What |
|---|---|
| (docs) | **ADR-635** ratified doc-first: the connector directory is CONSUMED (the MCP registry live + a seed DERIVED from `anthropics/knowledge-work-plugins` with repo+commit provenance), never authored; an **attached connector** is a `platform_connections` row keyed `mcp:{slug}` (no migration) attached by ONE generic OAuth 2.1 flow (RFC 9728 → 8414 → 7591 DCR → PKCE S256); the **aperture** is per-tool consent on the connection (`direct` · `propose` · unlisted = DENY); a `propose` call is the proposal queue's first producer since the steward retired. Banners on ADR-420 §10 (the demand gate lifts), ADR-585 D2/D4, ADR-293 D4, ADR-630 D3, ADR-356 (superseded); connectors.md §5a; intake-pipeline §5; lane-frame §3; GLOSSARY v3.7 (three rows + the dispositions row is now THREE); ADR-LEDGER; CLAUDE.md; SCHEMA-NOTES; primitives-matrix deleted ledger. |
| (code) | `services/attached_connectors.py` (discovery · DCR · PKCE · envelope · refresh · aperture · tool defs · dispatch) · `services/connector_directory.py` + `connector_directory_seed.json` (55 servers @ `f30dc63b`) + `scripts/refresh_connector_directory.py` · `routes/attached_connectors.py` at `/api/connectors` · the gate branch (`permission.py`, before the non-Reviewer free-pass) + the dispatch branch (`registry.py`) · `lane_runner` composes the surface into payload, allowlist, frame and the skills index from ONE read · `mcp_client` accepts header/no auth and returns annotations · `list_integrations` + the integrations list/summary emit `mcp:` rows · skills `metadata.needs` + `stripped` · Settings → Connectors: **Find a connector** (search + paste), attached rows, `AttachedConnectorSubsurface` (the aperture) · the discovery card no longer names `remember`/`recall`/`trace` · `plugin/yarnnn/` + root `.claude-plugin/marketplace.json` + `docs/features/mcp/server.json` · **DELETED**: `TrackForeign`, `services/foreign_read.py`, `scripts/mcp_crawlb_increment1.py` (no live surface; 0 watch rows in prod). |

## Verification (the standing set at ship)

```
cd api && python3 test_adr635_attached_connectors.py   # 78/78 — attach flow offline (Notion shape), 3 verdicts + replay, lane agreement, seed provenance, strip, deletion, canon
cd api && python3 test_adr585_turn_reach.py test_adr630_skills.py test_adr494_connector_registry.py test_adr612_agent_connector_opt_in.py test_adr577_credential_claim.py test_adr632_the_seat_retires.py   # all green
cd web && node_modules/.bin/next build                  # exit 0
```
Live receipts (2026-09-03, `.venv-mcp`): `discover()` against mcp.notion.com → oauth, DCR, S256 · mcp.linear.app → oauth, DCR, S256, scopes read/write · mcp.context7.com → anonymous; `list_tools` on Context7 through the widened client returned `resolve-library-id`, `query-docs` with `readOnlyHint` carried.
Pre-existing reds, NOT this arc's (verified at HEAD in a worktree): `test_adr535` §3 "states the EDGE" (the phrase lives in the no-reach branch; ADR-615 lit reach by default) · `test_adr373_rekey` under the 3.9 venv (mcp_server/auth.py is 3.10+ syntax; green under `.venv-mcp`).

## OWED

1. **Browser click-pass of one full attach** — STILL OWED, but its preconditions are now driven (`docs/evaluations/sessions/adr635-attach-click-pass-2026-09-03.md`, commit `3611c2a`). Remaining: Settings → Connectors → Find a connector → Linear → Connect → authorize → land on the connection page → set one tool DIRECT and one PROPOSE → in /chat call the DIRECT tool (expect the result) and the PROPOSE tool (expect "queued for you" + a row in the queue) → Approve from the queue → the replay runs. **Settled, do not re-check**: `API_BASE_URL` needs NO Render change — `callback_url()` defaults to the public API origin and Linear accepted DCR against that exact URI (client_id `IGP4f79KmQrvFVt7`), so the redirect-URI mismatch that would only surface mid-consent is falsified; both API and web are deployed at `02162fc`; the doors answer 200/401/307-with-a-readable-error unauthenticated. **Baseline for the receipts**: `platform_connections` has zero `mcp:%` rows and `action_proposals` has zero `family='external-write'` rows, so the run's rows are unambiguous. Blocked only on the human OAuth consent (and, this session, on the devtools Chrome profile being held by another client).
2. **Publish**: `docs/features/mcp/server.json` to the MCP registry (`mcp-publisher`, namespace `com.yarnnn` needs DNS verification) and the plugin to the official directory (the submission form). Both are operator acts.
3. **Seed refresh cadence**: re-run `scripts/refresh_connector_directory.py` when upstream moves; the diff is the change. Twelve seed servers carry no category (upstream's table did not name them).
4. **Durable intake from an attached server** — named, not built (a member-declared `{server, tool, args}` watch; ADR-635 §3).
5. The API's Python on Render: `mcp>=1.28` installs there, so it is ≥3.10; the local `api/venv` is 3.9 and cannot import the SDK — the attach seam imports it lazily and the gate holds the client rule statically under 3.9.

---

# Part M — the vocabulary / skills / steward-retirement arc: ADR-630/631/632 (2026-09-02)

## What shipped (three commits on main)

| Commit | What |
|---|---|
| `99a0a13` | **ADR-631** — one noun for the agent (*being* retired), one noun for the pane (*desk* retired → **pane** + **app**); ONE roster `agents` with ONE relation `apps` on the lanes envelope; `apps_for_agent` replaces three registry fns; "External Agents" → connected principals |
| `6dd5b8d` | **ADR-630** — skills are files: `api/services/skills/{slug}/SKILL.md` (8 kernel skills at the work-verb level, mapped to Anthropic's public set), MIRRORED into every workspace at `system/skills/` (manifest-cheap, first-use), a `## Skills` index in every lane frame (byte-ceilinged), the lane binding `skill` + `derive_source`; `derive_recipes.py` + the ADR-157 playbook family DELETED; the three stored skill-bound lanes re-slugged in prod |
| (this commit) | **ADR-632** — the steward retires in full: `agents/`, the wake stack, the review seat, the envelope, kernel mirrors, the steward's model table, `routes/feed.py`, the steward-only primitives + the three LLM rosters, the FE narrative context / transcript / drawer / mascot, 26 probes, ~60 tests, 11 canon docs archived to `previous_versions/` |

## ⭐⭐⭐ Findings worth carrying

- **The strings + capture lanes were NESTED inside the steward's `if is_agent_enabled():` block.** A flag meant for a dormant steward could switch off the one lane with production tenants. They now run unconditionally, each behind only its own flag.
- **Four modules on the naive deletion manifest were not stack**: `narrative.py`, `capabilities.py`, `substrate_reapply.py`, and two symbols of `model_selection.py` (`strip_provider` + `accept_model_override` → now in `system_calls.py`). The audit-then-cut order paid for itself.
- **A restored census gate found a real gap**: `test_adr445_principal_attribution` crashed at HEAD on a missing `harvest.py` and never reached its walk; un-crashed, it reports `services/strings.py` records a costed ledger row without `principal_id`. Not this arc's defect; see OWED.
- **The `.next/types/` cache pins deleted routes** — a stale generated type dir fails `tsc` after a page is deleted; remove the dir (the build regenerates it).

## Verification (the standing set at ship)

```
cd api && python3 test_adr632_the_seat_retires.py   # 73/73 — includes the two live frame ratchets (conventions scaffold 666/900 · studio posture 10,566/11,000)
cd api && python3 test_adr630_skills.py             # 87/87
cd api && python3 test_adr631_vocabulary.py         # 34/34
cd api && python3 test_agent_registry.py            # 136/136
cd web && node_modules/.bin/next build              # exit 0
```
~60 gates re-anchored (they pinned the rosters, the feed router, the wake modules, or the drawer); ~55 gates deleted whose subject was the steward. A full-suite sweep at ship: 217/374 green; the reds were baselined against a HEAD worktree (`scratchpad/full-sweep-baseline.log`) — the ADR-338/340/341/346/347/349 launcher/settings gates, the studio-drift gates, radar, docs-app and `test_claude_md_ratchet` were already red at HEAD.

## OWED

1. **Render env strip** (operator, dashboard): `AGENT_ENABLED`, `YARNNN_MODEL_{ADDRESSED,PROPOSAL,RECURRENCE}`, `YARNNN_ROUNDS_*` on the API + Scheduler services — no reader remains. The Render MCP can only MERGE env vars, so this is a dashboard step.
2. **Migration**: drop `wake_queue` (15,388 rows, no reader) and the recurrence `tasks` index (0 live readers after ADR-632; `capture` rows use their own kind-scoped scheduler — verify `services/capture/scheduling.py` before dropping the table rather than the recurrence rows). `chat_sessions.cancellation_requested` is a dead column.
3. **`services/strings.py` ledger rows carry no `principal_id`** — stamp the workspace owner (ADR-445) at the two `record_execution_event` sites, or declare why not. `test_adr445_principal_attribution` is the receipt.
4. **ADR-596 D3 phase (d)** — review as a grant + policy declaration. The queue, `ProposeAction`/`ReturnVerdict`, and the autonomy/budget dials stand; the operator is the verdict-giver; no proposal producer exists today.
5. **Drive the skills**: open a bound Slides lane, ask for a deck from three sources, watch whether the index makes the agent read `system/skills/presenting-from-sources/SKILL.md` and whether outputs cite it in `derived_from`. The five new skill bodies are unmeasured prose.
6. **ADR-579 D8** "from sources…" — the click door for the skill binding.
7. **`test_claude_md_ratchet`** was red at HEAD (52.7K > 50K) and this arc grew CLAUDE.md; the fix is moving reference rows to ADR-LEDGER, not raising the ceiling.
8. Carried from Part L: the WordPress publish click-pass · the `post.html` 0-byte read · the 31-Aug egress spike attribution.

---

# Part L — the Blogger/Designer arc: ADR-627/628/629 (2026-09-01/02) — CLOSE-OUT

## ✅ RESOLVED — a paid top-up never reached the balance (2026-09-02)

Operator topped up **$25.00** and the balance did not move. Cause: the Lemon
Squeezy store had **TWO webhooks registered for the same events** —
`https://api.ep-0.com/webhooks/lemonsqueezy` (stale, not ours, no `/api`
prefix) beside the live `yarnnn-api.onrender.com` one. Order **2216529** was
routed to the stale host, which answered an HTML **503**.

⭐⭐⭐ **A webhook that never arrives is invisible BY CONSTRUCTION.** No request
in the Render access log, no row in any table, no error anywhere — the *absence*
of a log line was the only evidence, and it reads identically to "nobody paid".
`balance_transactions` had **never held a single `kind='topup'` row** in its
entire history. The operator found it by noticing the number was unchanged.

⭐ **Resend does not re-route.** It replays a delivery to *the endpoint that
delivery belongs to*, so pressing it twice only hit the dead host again. Editing
the live webhook's event list doesn't help either — the order was dispatched at
05:00 and routing was decided then. Deleting the stale hook cannot recover an
already-dispatched order; it can only be repaired by hand.

**Three commits:**

| Commit | What |
|---|---|
| `3553545` | `grant_balance` is **idempotent on `lemon_order_id`** — LS retries non-2xx deliveries and Resend exists; each replay used to add the money again. This is what made the hand-repair safe *while the healthy webhook stayed eligible to retry the same order*. |
| `87a7fac` | Order credited: `37.0904 → 62.0904`, one `kind=topup` row at `07:45:39Z`. Replay asserted **on the real row** — second call moved nothing. One-shot script then deleted. |
| `da47091` | **The silence itself, closed.** A top-up checkout now leaves a durable `topup_checkout_created` row (the promise); `_undelivered_topup` reads the gap between that and the credit it should have produced, and surfaces `undelivered_topup` on the billing card beside the seat-sync banner. Gate 25/25, falsified 6 ways. |

⭐⭐ **The detector reads a GAP, not an event.** You cannot detect a missing
webhook from the events it failed to write — so record the *promise* (the
checkout we mint) and diff it against the *credit*. Counts by TIME, never order
id: the undelivered order's id is exactly what we never learned.

⭐ **Follows the ADR-445 seat-drift precedent exactly** — and that precedent's
own comment names this very failure class ("rows have been landing since the
reconciliation layer shipped and NOTHING read them; discovered only by
hand-querying the table"). Same shape: durable row → status field → banner,
both halves best-effort, cleared by a later success so it can't become furniture.

⭐ **Trap:** `api/scripts/operator/` shadows the stdlib `operator` module — any
script run with `api/scripts/` as cwd dies on `from operator import eq`. Run
from `api/`.

⚠️ The stale hook received **14 events to yarnnn's 7**. Since no `topup` row
existed before this repair, any earlier orders it swallowed were also never
credited — worth a pass over LS order history for charges that never became
balance.

## ✅ RESOLVED — Supabase egress 402 (was URGENT; closed 2026-09-02)

The project was restricted with **402 exceed_egress_quota** (8.78/5GB), taking
REST + auth down. Operator upgraded to Pro; service restored. Three fixes
shipped in `8feb68f`, gate `api/test_egress_bounds.py` (10/10, falsified):

- **Counting is not fetching.** `select("*", count="exact")` on `workspace_files`
  transferred **7,940,121 bytes** where a head-count transfers **47**
  (~169,000x), ~10x per Settings load. 2 of 5 sites counted rows they were
  about to DELETE. The gate found a 3rd count site the manual sweep missed.
- **A re-minted signed URL is a new cache key** ⇒ the provider re-fetches.
- **4 polls** no longer run in hidden tabs.

⚠️ **The 5.7GB 31-Aug spike is still UNATTRIBUTED.** Vision-replay was named,
then MEASURED and withdrawn (7 image msgs ever · 38MB CAS total · ~46MB/export
· 65 exec events — every path 1-2 orders too small). 31-Aug 1h log counts: API
Gateway 8.5k · **Storage 1.0k** · Auth 32 · Postgres 24 · PostgREST 5 (errors
only). 1k storage reqs x ~0.91MB mean binary ≈ **~900MB in ONE window** ⇒
STORAGE is the leading suspect, not the count defect (stored SIZE 54MB ≠
request COUNT — that is what fooled the first read). OWED: re-run the log view
on **API Gateway + Storage, full day of 31 Aug, by path + response size** (the
PostgREST pane is error-level, not access logs) · image downscale bound ·
`/workspace/roots` 5k-row 30s scan @38KB/call (needs an RPC).

## What shipped (all pushed to main, all deployed)

| Commit | What |
|---|---|
| `c7d1d3d` | ADR-627 — Blogger app + being; `post` medium resurrected (band family); retired slugs article/page/web → post; gates re-anchored (2 were red-at-HEAD since ADR-599) |
| `cad1fef` | ADR-628 ratified — the OUTBOUND disposition (third, after INTAKE + TURN REACH) |
| `deb430a` | ADR-629 — full placement + `badge:"beta"` (presentation-only field); blogger+images → stage primary; ADR-488 hold closed; latent `pinned==tier` pin re-anchored in test_adr297+test_adr592 |
| `557be1c` | Click-pass run record — Blogger driven live end to end (docs/evaluations/2026-09-01-adr627-629-blogger-click-pass-run1.md) |
| `916f409` | ADR-628 phase (a) BUILT — WordPress first tenant; seam `services/publish.py`; exporter fossil DELETED (0 callers); Publish door on Blogger; net −81 lines |

Operator has since: registered the WordPress.com app ("yarnnn-api",
developer.wordpress.com) and set `WORDPRESS_CLIENT_ID`/`SECRET` on **both**
API + Scheduler Render services (scheduler copy is inert today, forward-
compatible with phase (b)). API redeployed 2026-09-02 00:06 (trigger:
manual, live) — that deploy is the env-var receipt; a FUNCTIONAL probe was
blocked by the Supabase 402 above.

## Verification (the standing set — all green at `94009a4`)

```
cd api && python3 test_adr627_blogger_pairing.py      # 26/26
cd api && python3 test_adr628_outbound_publish.py     # 28/28 (seam driven w/ stubs)
cd api && python3 test_agent_registry.py              # 136+
cd api && python3 test_adr592_app_stage.py            # 45/45
cd api && python3 test_adr582_connectors.py           # re-anchored off the fossil
cd api && python3 test_adr494_connector_registry.py   # +wordpress
cd web && node_modules/.bin/next build                # exit 0
```
Pre-existing reds NOT this arc's (stash-verified): test_adr338 pane-set (1) ·
test_adr577 §6 agent_connectors allowlist (1).

## OWED

1. **WordPress publish click-pass** — connect (consent screen), pick site,
   publish the ADR-627 post live, verify `_publish.yaml` receipt + the post
   URL; also drive the unconnected + no-sites panel states.
   *Verified 2026-09-02:* connected, token decrypts, `yarnnn9.wordpress.com`
   (id 257108137) visible to the seam; no-sites panel click-passed; **no
   reconnect needed after site creation** — global scope worked as designed.
   Remaining: the publish act itself. **Operator decision owed:** publish the
   ADR-627 scaffold as-is, have the session write a real body first
   (recommended), or write it yourself.
2. ⚠️ **`post.html` reads 0 bytes over the API while the row holds ~35KB**
   (found 2026-09-02, NOT chased). `GET /api/workspace/file` returned 0 bytes
   for `/workspace/operation/adr627-click-pass-post/post.html`; that row's
   `content` is **36,410 bytes** over PostgREST (service key, verified live
   2026-09-02). The same row carries **`content_type: "text/markdown"` on an
   `.html` artifact** (`updated_at` 2026-09-01T03:17:26Z). Either half can
   silently break a publish — the seam ships an empty body, or the wrong
   medium. **Handle before or immediately after the publish click-pass.**
   Start at `GET /api/workspace/file` and `write_revision`'s content_type
   derivation; suspect the ADR-621 binary/empty classification seam.
3. **First real `blogger` standing declaration** (ADR-603's owed second kind)
   — compose-only; publishing stays member-clicked until phase (b).
4. **Phase (b)** (supervisor-scheduled publish) — begins ONLY on phase (a)
   receipts via ADR-628 amendment: a string's run + narrow non-agent identity
   `system:publish-wordpress`, balance-checked, receipted, bounded. The
   operator's instinct ("scheduled jobs via supervisor need headless-like
   workflows") is exactly this — do NOT reach for a general headless auth
   (three lanes voted narrow; ADR-626 D4.b).
5. **The undelivered-top-up banner is unproven in the browser** (`da47091`).
   Mechanism is gated 25/25 + falsified 6 ways, but the banner has never
   rendered live — and it CANNOT be seen today, because the only checkout that
   would trip it predates the `topup_checkout_created` row it needs. To drive
   it: mint a top-up checkout, abandon it, wait out
   `TOPUP_DELIVERY_GRACE_MINUTES` (30), load Billing. Also worth a pass over LS
   order history for **earlier orders the stale `api.ep-0.com` hook swallowed**
   (it took 14 events to yarnnn's 7; no `topup` row existed before 2026-09-02,
   so any it ate were never credited either).
6. Carried from the arc: fresh-principal default-Dock observation · IMAGES
   compose loop post-promotion · Ghost as second connector (deferred) ·
   Substack read-side into strings (their Publisher API is read/analytics).

---


# Part G — the git-at-any-scale arc: ledger receipts, the export door, danger-zone cleanup (2026-08-20)

## What shipped

| Commit | What |
|---|---|
| `91fe2f6` | docs: authored-substrate — replay invariant measured, taxonomy re-synced, the no-compiler argument |
| `3751783` | blog: "Knowledge Work Has No Compiler" + **remark-gfm wired** (tables rendered as raw `\|---\|` on the live site; 4 posts) |
| `c6e9fcc` | feat: the export gets a door — Download Workspace card + purge confirm names the remedy |
| `7cc83a6` | fix: 168/1,613 export commits dated 1970 (py3.9 `fromisoformat`) |
| `d2c1281` | refactor: danger-zone condense — User Settings' dead L1/L2 plumbing deleted (net −81) |
| `5e76e3d` | fix: purge acts on the workspace it was asked about, and fails CLOSED |
| `99f5d51` | chore: api + web lanes validated |

## Measured facts (production, 2026-08-20)

- **Replay is clean**: 391/391 live files byte-identical to their head blob;
  0 dangling parents, 0 forked chains, 0 unattributed of 1,928 revisions.
  `workspace_files.content` is a genuine cache, not a second source of truth.
- **Concurrency is a real CAS** — migration 197's partial UNIQUE on
  `parent_version_id`. Not the read-then-insert it looks like.
- Attribution residue: 8 free-text `authored_by` rows, 2026-07-07→07-16, door
  since closed by `is_valid_author`. **They stay** — rewriting history to tidy
  the census trades the invariant for its appearance.
- Author census: operator 986 · system 769 · member 67 · yarnnn 56 · freddie 31.
  Machinery authors ~40% and touches more distinct paths (201) than the
  operator (141).
- 160 revision chains have no live file (the L1 orphan condition, below).

## RESOLVED 2026-08-21 — the "unattributed destruction" item is WITHDRAWN

The three items previously listed here as "needs a DECISION" were re-examined
with the operator on 2026-08-21. **Item 1 was over-framed and is withdrawn;
items 2 and 3 dissolve with it.** Recorded so a future session does not
re-inherit the framing as an open gap.

**1. "Destructive paths are unattributed." WITHDRAWN.** The attribution axiom
("every change is signed by whoever made it") is about the COMMONS AND ITS
CONTENTS — so collaborators can trust what they read and can walk its history.
Purge is the operator ENDING the thing; the axiom does not extend to "the act
of ending the record is itself a record". A delete is supposed to leave
nothing — that is what makes it a real delete rather than a soft one.

The proposed fix was arguably worse than the gap: a durable out-of-workspace
destruction log is RETAINED DATA ABOUT A WORKSPACE AFTER THE OPERATOR ASKED
FOR IT TO BE GONE — in tension with our own privacy page ("Nothing expires on
a schedule…") and something a GDPR-style erasure request would make us
justify rather than celebrate.

The practical need it was really serving — "can support tell whether the
operator cleared it, or whether we lost it?" — is ALREADY MET server-side:
`workspace_delete.py:162,177` log actor + workspace on soft-delete/restore,
and `workspace_purge.py` logs the L2 scope. No table, no retention, no UI.

**2. L1 orphans revision chains** (160 live). Correct-as-designed for a light
L1 and not worth a schema change; if the copy overpromises, that is a copy
fix, not an architecture one.

**3. `execution_events` destroyed by purge.** Precisely: L2 (clear workspace)
PRESERVES it — only the ADR-578 FULL PURGE destroys it, forced by a `NO
ACTION` FK, and that path ENDS the workspace. A cost ledger for a workspace
that no longer exists has no consumer, so this is not in tension with ADR-291.
(An earlier note conflated the L2 and purge paths.)

**Current verified state:** purge/clear owner-gated (`workspaces.owner_id` or
an explicit `workspace:clear` scope; prod: 0 grants carry it) + typed
confirmation on the irreversible acts; delete reversible with restore; billing
history survives L2. A normal, complete SaaS deletion story. Nothing to build.

## OWED — click-passes (mechanism verified, browser path not)

- **Download Workspace**: engine driven against the real 299-file workspace
  (1,613 commits, `git fsck --strict` clean, `git shortlog` names every
  principal). NOT clicked in a browser — the route streams a zip, and a
  `Content-Disposition`/CORS detail behaves differently there than in curl.
- Danger-zone condense (both doors after the cleanup).
- Everything in MEMORY.md still marked OWED from prior arcs.

## Gate notes

- `test_adr476_purge_scope` D3 pinned `?pane=danger` — a spelling the app has
  never used. RED since written. Re-anchored + falsified.
- `test_adr501_read_path_binding` pinned `resolve_purge_workspace(user_id)` in
  the `clear_integrations` window and read the fail-closed hardening as a
  regression. Re-anchored to accept either spelling.
- New: `api/test_purge_scope_and_failclosed.py` 8/8, each fix falsified against
  the real pre-fix code.

---

# Part F — ADR-586: the one-door rebuild (2026-08-19; BUILT + CLICK-PASSED)

**Built at `af92564`; DRIVEN at `d10c092`.** The whole door was click-passed on
a real deck and a real flow doc — run record:
`docs/evaluations/2026-08-19-adr586-one-door-click-pass-run1.md` (15 steps,
both halves per step, scope + non-coverage declared).

**PASS**: the category rail with medium ordering (deck leads Slide, flow leads
Text and has no Slide at all) · schematic galleries · a Stat insert landing in
the slide the header named, drawn by the kernel with the delta themed by the
palette marks · right-click tiers expanding INLINE at the bottom edge with the
box re-measuring upward (125→352px, top 647→421, never off-screen) · contextual
Update pre-expanded with the meter badge as the only mechanical/metered seam ·
the bottom sheet as one component + class fork · the FULL ADR-583 loop: lane
composes a contract-clean `*.component.html` → it appears "shared" in the
Components gallery → insert cites it directly (pin = head revision, attributed
`member:… via …`) → editing the SOURCE moves the citing artifact (GROWTH/$79)
while the pin stays the fallback, exactly as D4's "reference, never copy" says.

**ONE defect found by driving and fixed in-run (`d10c092`)**: the named target
did not COMPOSE — "ADD — INTO AFTER THE SELECTED BLOCK" on every block-selected
open, both housings, both media. The header hard-coded "into" while the block
branch of `resolveInsertTarget` already returned a prepositional phrase. Each
branch now owns its preposition; the header states the label verbatim.
`test_adr586_one_door.py` 27→31 (both new checks falsified against real breaks);
`test_adr509_insert_route.py` re-anchored off the pinned spelling that read the
correction as a violation.

## Verification (the standing set)

```
cd api && python3 test_adr586_one_door.py            # 31/31
cd api && python3 test_adr583_component_library.py   # 28/28
cd api && python3 test_adr581_medium_regroup.py      # 13/13
cd api && python3 test_adr579_verb_grammar.py        # 16/16
cd api && python3 test_adr509_insert_route.py        # 37/37
cd api && python3 test_studio_slash_anywhere.py      # 51/51
cd api && python3 test_adr462_context_menu.py        # 49/54 — the 5 fails are PRE-EXISTING (another arc's)
cd web && node_modules/.bin/next build               # 172/172 (was 171 — a concurrent lane added a page)
```

⚠️ `test_eval_suite_gate.py` (PYTEST, not script-run) has **2 pre-existing
failures** in the `adr518-*` manifests — mutating steps with no `restore:`,
last touched at `95922dd`. Owned by the ADR-518 arc, not the insert lane.

## Owed

- **Logo-row height preset** — NOT RUN: the rig has 0 images, so the multi-pick
  has nothing to pick (its empty state was driven and teaches correctly). Needs
  an image in the workspace.
- **The in-frame right-click gesture itself** — the parent half (positioning,
  tiers, re-measure) is probed; the in-frame hit-test is inferred (opaque-origin
  ceiling, playbook §2). Operator-packet lane if it needs probing.
- ADR-581 D5 the app split · 579 D7 pane turns · **D8 "from sources…"** (583's
  named front door) · flow medium at narrow width.

---

# Part E — ADR-579/581/583: the verb-grammar arc (2026-08-19; D4 + 583 ABSORBED)

**Owner: the insert/verb-grammar lane.** The D4 build spec this part carried is
**EXECUTED** in the commit that rewrote this section — ADR-581 D4 shipped: five
registry rows (stat · comparison · timeline · person composed; logo-row cited →
ADD), kernel CSS v19 written against the v18 child-inset geometry, icons, the
logo-row multi-pick (gallery machinery, kind kept at the terminal), and the
D4.a decisions recorded in the ADR (turn-into refused for composed; UPDATE =
existing tier + tone token; delta via palette marks; columns by auto-fit).
Arc commits before it: `9b901e4` (579 ratified) · `a73bdef` (provenance
grouping) · `ea5aa52` (toolbar verbs) · `e6d2319` (verb doors) · `25e7d3f` +
`8bceaec` (581 D2/D3, renumbered from the 580 collision).

**ADR-583 landed same day (operator-ruled after the D4 discourse): a component
is a workspace FILE** (`*.component.html`, cited like a CSV/image — the
library). The colour law recut (never a raw colour/face/radius; geometry free,
homed in component files); the `component` kind re-cut to `cites="fragment"`
(fourth citation value → lands in ADD by construction); projection inlines
through the shared executable strip (live + pinned); picker lists the library;
the compose/reverse-engineer act is a posture-taught JOB on the designer (no
new app). **The catalog is CAPPED** — a new registry row needs a click-door
gap, never a component need. ⚠️ ADR-582 was TAKEN by the connector lane
mid-session — 583 verified at commit time; 584+ can collide the same way.

## Verification (the standing set)

```
cd api && python3 test_adr583_component_library.py  # 28/28
cd api && python3 test_adr581_medium_regroup.py     # 13/13
cd api && python3 test_adr579_verb_grammar.py       # 16/16
cd api && python3 test_adr509_insert_route.py       # 37
cd api && python3 test_adr538_block_classification.py  # 64/64
cd api && python3 test_adr539_vocabulary_declares.py   # 41/41
cd api && python3 test_adr462_context_menu.py       # 49/54 — the 5 fails are PRE-EXISTING at HEAD (verified in a clean worktree)
cd web && node_modules/.bin/next build              # 171/171; `pnpm` NOT on PATH
```

## Traps this arc paid for

- ⭐⭐⭐ **Verify the ADR number at COMMIT time** (`ls docs/adr | sort -V | tail`):
  two lanes shipped two different ADR-580s to main within hours; the medium regroup
  is now ADR-581. With parallel lanes live, 582+ can collide the same way.
- ⭐⭐ **Concurrent lanes commit mid-session**: stage by explicit pathspec, verify
  with `git log -S"<your string>"`. This arc's build once broke on ANOTHER lane's
  in-flight `projection.ts` backticks-in-OBJECT_SCRIPT — verify your own build in an
  isolated worktree (HEAD + your files) before diagnosing your code.
- ⭐ **Gate craft**: two of my own checks matched my own comments (the retired header
  quoted in a comment; a label in the file docstring) — anchor on WIRED handlers
  (`run(onCheck)`), and never quote retired strings in comments.

## Owed (the arc's remaining ledger)

**The click-pass this section owed is RUN** (2026-08-19, run record
`docs/evaluations/2026-08-19-adr586-one-door-click-pass-run1.md`): the D4 kinds
were driven (a Stat inserted, drawn by the kernel, delta themed by the palette
marks) and the 583 compose→cite→edit-source loop closed end to end. The
toolbar topology it describes below is ADR-586's now, not the 579 triad's.

Remaining:

- **ADR-581 D5** the Deck/Articles app split (phased; the mechanism — `apps`
  column + `register_app` — already exists).
- **ADR-579 D7** pane structured turns (seed → receipt; coarse grain only)
  · **D8** file-altitude ADD/NEW with "from sources…" (the multi-source derive,
  and ADR-583 D5's named front door).
- **Logo-row height preset** — still unexercised: the rig has 0 images.

# Part D — ADR-575: the document hears other principals before it collides

**The operator drove the deployed surface and found a logic collision.** One
screenshot carried three claims that cannot all be true:

| The surface said | Actually true |
|---|---|
| *"Someone else revised this document"* | there had been a 409 |
| **`Editing…`** (copy means *nothing is at risk*) | autosave was **suspended** |
| **`No revisions yet.`** | **four** revisions existed in production |

Their diagnosis was right and better than mine: *"most likely the way the
autosave to features and thus artifact mutation is handled."*

## ⭐⭐⭐ The turn that made this worth doing

I proposed two repairs (refresh the revision, fix the copy). **The operator
refused the symptom fix and asked for the benchmark** — *"how does Notion handle
their multi-user workspace to artifacts?"* That overturned the framing:

- **Notion never shows a "choose whose version wins" dialog for prose.** Text
  merges; only non-text properties are LWW.
- **"Last edited by" is PUSHED** — MessageStore sends a *version number*, the
  client refetches what went stale. The push is an invalidation signal, never
  content.
- **ADR-572 D7's premise was false.** It said a 409 "cannot be re-applied
  without inventing a merge". **Merging prose is the most solved problem, not
  the least** — OT and sequence CRDTs operate on flat character sequences, which
  is exactly what a `.md` is. Blocks add the *harder* problem (tree moves).
  **Fourth instance this arc of a constraint read as a ceiling.**

What blocks genuinely buy, and we cannot have: **conflict-domain partitioning**
(Figma — a conflict needs *same property, same object*; a markdown string is one
object with one property) and **stable anchors**. So we cannot have edits that
never meet. We can have edits we *hear about* before they meet.

**The conflict banner was the cost of not listening**, handed to the member as a
decision.

## What shipped

- **Migration 240** publishes `workspace_file_versions` to `supabase_realtime`.
  ⭐ Verified against production FIRST: the publication carried only
  `chat_sessions` + `session_messages`, so a subscription would have delivered
  **nothing while reporting `SUBSCRIBED`**.
- **`useFileRevisionsRealtime`** — second tenant of the primitive
  `use-session-messages-realtime.ts` already declared reusable. Server-side
  filter on `path=eq.…`.
- ⭐ **The own-write echo rule.** Every autosave INSERTs a row that comes back
  down the channel; without the filter the surface announces the member's own
  typing as a peer edit ~2s after every pause.
- **Revision-only refresh on save** — `reloadKey` would re-fire `setText` and
  destroy a keystroke landing during the refetch (the D12 shape, already shipped
  once here).
- **A peer write branches on unsaved text**: none → reload silently; unsaved →
  notify, never touch the document.
- **`Paused — resolve above`** so the header says one thing at a time.

Whole-document CAS is **unchanged** — the 409 still asks, but becomes rare.

## ⭐⭐ RLS was falsified, not assumed

In a `ROLLBACK` txn as the real principal: 6 workspaces / 1758 revisions exist;
member `2be30ac5…` sees **2 / 1517** (owner ∪ one grant); a principal with no
grants sees **0**. Publishing widens *when* a member finds out, never *what*
they may see. The migration also **refuses to publish if RLS is off**.

## ⭐⭐⭐ Gate craft — 9 falsifiers, two findings

- **19g catches a temporal-dead-zone throw that `tsc` passes CLEAN.**
  `ownRevisions` is written by `commit` and must be declared above it; the
  broken form throws on first save with a green typecheck **and** a green
  `next build`. I verified `tsc` exits 0 on it.
- **19j passed its own falsification** (NINTH this arc). It required
  `pg_publication_tables` + `RAISE EXCEPTION` anywhere in the migration —
  deleting the whole verify block left both tokens in the **sibling RLS block**.
  Now extracts the branch.

## Part D verification

```
cd api && python3 test_adr571_text_app.py            # 232/232, SCRIPT-STYLE
cd api && python3 -m pytest test_lane_artifacts.py test_adr570_member_prose_door.py -q   # 19
cd api && python3 test_adr562_app_owned_config.py    # GREEN
node web/lib/file-types/__gate_adr514_d2.mjs         # 41/41, from REPO ROOT
cd web && node_modules/.bin/next build               # 171/171, tsc clean
```

## Part D owed — a TWO-PRINCIPAL click-pass

This is the one thing gates cannot do. Two browsers, two principals:

1. B saves → A's `LAST EDITED` updates **without A reloading**; A's document
   reloads silently (A had not typed).
2. A types, then B saves → A sees the notice, **A's text is still there**,
   `Keep writing` dismisses it.
3. A saves normally → **no** peer notice (the echo rule).
4. Force a 409 → header reads `Paused — resolve above`; both exits work.
5. Network tab during typing: one WebSocket, **no** `getFile` per save.

⚠️ A peer lane committed into this tree mid-session (`9fe241c`, `1d81883` —
the latter touched `TextEditor.tsx` in the Properties FILE row, disjoint from
this work). Stage by explicit pathspec; verify with `git log -S`.

---

# Part C — ADR-572 D18: the CSV question, answered by measuring first

**The operator asked whether a CSV-sourced table is structurally impossible in
markdown. It is not — and D17's `❌` was too strong.** The refusal had collapsed
three different things into one verdict.

| | What is in the file | Verdict |
|---|---|---|
| **Snapshot** — rows as GFM + an italic source note | the ROWS | ✅ **shipped** |
| **Automatically live** | a POINTER (= Docs' `data-ref`) | ❌ unchanged |
| **`csv-table` fence** — rows + `source=`, refresh on demand | the ROWS | ⚖️ offered, **declined** |

The surviving refusal is the middle row, and it is D17's own reason: a
self-updating table must hold a pointer instead of rows, which is exactly the
empty-container shape ADR-574 names as a reason Docs paused.

## ⭐⭐⭐ The finding worth carrying

**Nothing had to be built to answer the question.** `/studio/citable` already
served the workspace's CSVs (`tables`, beside `images`), `StudioCitablePicker`
already carried the title *"Insert a table from a CSV"* for Docs, and
`GET /api/workspace/file` already returned content by path. The machinery was
shipped; only *what goes in the file* was ever open.

**Checking that BEFORE writing the refusal is what turned a feasibility claim
into a design choice.** This is D13/D15's rule applied one step earlier —
*execute the thing you are calling impossible* — and it is the third time this
arc that a recorded "limitation" was a constraint under-read.

⭐ The fence option's cost was **larger than I first stated**: our own
`MarkdownRenderer` matches `/language-(\w+)/`, which `csv-table source=…` does
not satisfy — so it needs a handler in the shared renderer *and* a canvas
widget, not one. Corrected to the operator before they chose.

## What shipped

`Table from CSV` in both doors (toolbar + `/csv`), reusing the image picker
with `cites='source'`. It writes a real GFM table under
`_From `data/q3.csv` · snapshot 2026-08-17_`.

- **A snapshot's defect is SILENCE, not staleness** — rows that look live and
  are not. The provenance line is ordinary italic prose in the document (no
  `data-*`), so a connector reads it, a member can edit it, and the freeze is a
  stated fact. Re-running the insert is the refresh.
- **One quote-aware parser, not two.** Strings had its own copy; a naive
  `split(',')` makes `"Kim, Kevin"` two cells and shifts every later column
  *silently*, and an unescaped `|` ends the cell. Folded into the pure module
  where the gate **calls** it.
- **The only insert that awaits I/O**, so it reads the document from the canvas
  at apply time — the captured string would delete typing done during the fetch
  (the D12 shape, already shipped once here). A failed read inserts **nothing**
  rather than asserting "that file is empty".

## ⭐⭐⭐ Gate craft — two more, from ten falsifiers

- **An EIGHTH check passed its own falsification.** 18k required `setCsvError`
  + the error copy; gutting the catch body left the setter in its own
  `useState`/timeout and the copy in the JSX. → now reads the **catch body**
  and asserts no insert happens there. Same class as 17f, 11h, 11L.
- **⭐⭐ 18c FAILED against CORRECT output** — it split on a bare `|`, counting
  an escaped `\|` as a cell boundary, i.e. asserting the very corruption the
  escape prevents. **The gate was wrong, not the code.** It now counts
  boundaries the way GFM does, with a control proving it measures alignment and
  not "did it split at all".

## Part C verification

```
cd api && python3 test_adr571_text_app.py            # 221/221, SCRIPT-STYLE
cd api && python3 -m pytest test_lane_artifacts.py test_adr570_member_prose_door.py -q   # 19
cd api && python3 test_adr562_app_owned_config.py    # GREEN
node web/lib/file-types/__gate_adr514_d2.mjs         # 41/41, from REPO ROOT
cd web && node_modules/.bin/next build               # 171/171, tsc clean
```

⚠️ **A transient `tsc` failure in `viewers/projection.ts` was NOT a defect** —
the peer lane was mid-write in that file and the reported error line moved
between two runs seconds apart. It landed as `9fe241c` and builds clean.
**Before diagnosing a parse error in a file you did not touch, check whether
another lane is writing it.**

## Part C owed

- **Click-pass D18**: `/csv` → pick a CSV → the rows land as a grid under the
  source note; then a CSV with a quoted comma and an embedded `|`, to see the
  escape hold on the real surface.
- Everything owed by Parts A and B below is unchanged.

---

# (earlier parts)

**Two lanes ran concurrently today and both landed.** They touch disjoint files
except `ADR-LEDGER.md`, where both entries coexist (verified). Read whichever
part matches your next task; the shared residuals are consolidated at the end
of Part A.

- **Part A — ADR-572 D10**: the Text app's second operator click-pass (`f852c82`).
- **Part B — the MCP connector audit**: ADR-563/573 (`ec58956`, `116792d`).

---

# Part A — ADR-572 D10: the operator's second click-pass

`f852c82`. **Five operator findings diagnosed, fixed, gated and pushed.** Two
were structural (a face split, and a false premise inside a ratified decision);
three were surface defects. None were visible to `next build`, to `tsc`, or to
the 128 gate checks that were green over them.

## What shipped

| # | Operator's words | What it actually was |
|---|---|---|
| 1 | *"the table render doesn't show the rendered style on the editor"* | **Two hand-maintained faces**, drifted. The table was only where it showed. |
| 2 | *"the tool bar inserts don't work for an empty line"* | One predicate bug, three call sites. |
| 3 | *"do we need a distinct save button?"* | **D5's premise about Docs was factually false.** |
| 4 | *"the ... file handling is not available. colour and highlight, also not available"* | A real gap **and** a correct-but-invisible refusal. |
| 5 | *"the design system application also please double check"* | The canvas was reading a token namespace its medium cannot have. |

New module: `web/components/text/readingFace.ts` — the ONE reading-face
declaration both renderers derive from.

## ⭐⭐⭐ The two findings worth carrying forward

**1. A refusal documented only in canon is invisible.** ADR-572 §3.1 refused
colour/highlight for good reasons and said, in writing, that it wanted the
absence *"named rather than leaving the absence to look like an oversight"* —
then named it only in the ADR. The operator opened the pane and read it as a
gap, exactly as predicted. Docs prints its refusals **in the pane**; Text now
does too. **If an absence is deliberate, the surface has to say so where the
absence is felt.**

**2. A ratified decision can rest on a false premise about a neighbouring
module.** D5 justified Text's Save button by asserting Docs "autosaves with no
CAS". Docs' `writeAndAdvance` is a queued CAS commit per operation with a 409
refetch-and-retry. Docs had everything the button was justified by and still
had no button. **Text was not more careful than Docs — it was less capable, and
it handed the member the difference as a chore** (the ADR-550→551 shape: a live,
correct mechanism in the wrong housing). Sibling of Part B's *"a ratified ADR is
evidence of a decision, never of an implementation"*: **verify the claim an ADR
makes about its neighbour, not only the decision it draws from it.**

## The parent-tag trap (D10.a), named so it is not re-set

`tags.heading1` is `t(heading)` — a **child** of `tags.heading`. Tag inheritance
flows parent→child, so a rule on the child **never** matches a node tagged with
the bare parent. `@lezer/markdown` tags a **table header** with exactly that
bare `heading`. Measured, not read:

```
heading (table header) -> NO CLASS (unstyled)
heading1               -> ͼo
content (table cell)   -> NO CLASS (unstyled)
atom (task marker)     -> NO CLASS (unstyled)
```

Same shape as D1's `prose-sm`/`prose-base` collision: **a rule that looks like
it covers the case and doesn't.**

## The type-token finding (D10.b) is subtler than "a missing token"

`--font-serif` **is** a real token — an **artifact-skin** token (`skinVars.ts`),
declared by an applied design system and parsed at runtime by `skinVarMap()`. It
exists only inside a skinned Docs artifact. **A `.md` has no skin**, so in Text
that var could never resolve; the inline fallback always won while Tailwind's
`font-serif` took its stock stack. Two faces on one document, by construction.
The fix declares an **app** type vocabulary distinct from the **artifact** one.

## ⭐⭐⭐ Gate craft — two checks passed their own falsification

Both caught only because every new check was falsified. Same error, one screen
apart:

- **11h** asserted `"var(--font-serif)" in tailwind.config.ts`. Repointing
  `serif` at `["Georgia","serif"]` left the string present **in the check's own
  explanatory comment** and in the `mono:` line beside it. → now extracts the
  per-key value.
- **11L** required `openMenuFromButton` **and** `"File actions"`. Deleting the
  `aria-label` left `title="File actions"` behind. → now matches the wired
  `onClick` and the mounted menu node.

**Fourth and fifth occurrences this arc** of an assertion matching a
*decoration* of the behaviour rather than the behaviour. (Part B hit the same
shape independently — see its gate-craft note.)

Also worth keeping: **11a's falsification is what proves it tests the table.**
Removing the plugin fails 11a while `canvas_styled` stays `True` — without that
control, 11a could have been passing on "did anything render at all".

## Part A verification

```
cd api && python3 test_adr571_text_app.py            # 160/160, SCRIPT-STYLE (pytest = false pass)
cd api && python3 -m pytest test_lane_artifacts.py test_adr570_member_prose_door.py -q   # 19
cd api && python3 test_adr562_app_owned_config.py    # script-style
node web/lib/file-types/__gate_adr514_d2.mjs         # 41/41, from REPO ROOT
cd web && node_modules/.bin/next build               # `pnpm` NOT on PATH; 171/171 pages
```

⚠️ **`__gate_adr514_d2.mjs` prints a stray `Node.js v25.1.0` line after its
summary.** It exits 0 and reports `ALL PASS — 41/41`. A `tail -3` on it looks
like a crash and is not one — **read the summary line or the exit code**, not
the tail. (Nearly reported as a false negative this session.)

## Part A owed — the D10 click-pass

Everything was gated by mounting the real components and executing the real
functions, but **not driven on production**. Drive it **cold**:

1. Open a document with a table → it reads as a **grid**, not raw pipes.
2. Caret on an **empty line** → bulleted list / task list / quote → each inserts
   its marker with the caret ready to type.
3. Type, then **stop** → the header goes `Editing…` → `Saving…` → `Saved` within
   ~2s. **There is no Save button** — confirm nothing reads as lost.
4. Properties → the **`⋯`** beside the filename → Copy link / Duplicate /
   Rename / Move / Move to Trash.
5. Properties → **Appearance** → the refusal reads as a decision, not a gap.

## Traps Part A paid for

- ⭐⭐⭐ **A green gate is not a rendered surface** (fifth time). Five defects,
  128 green checks, clean `tsc` and clean `next build` across all of them. §11
  now mounts the real canvas in jsdom, because a source grep cannot see which
  CSS class a tag resolved to.
- ⭐⭐ **Check the detector before trusting a negative** — a passing gate's
  trailing output read as a crash.
- ⭐⭐ **A concurrent lane can land work in your tree.** The MCP files present at
  this session's start were committed by the Part B lane mid-flight; `git add -A`
  would have swept them. Staged by explicit pathspec, verified with
  `git log -S"<my string>"`.

---

# Part B — the MCP connector audit, and what it produced

The audit asked: **does the connector show user
information and let you select a workspace — in the OAuth flow, and in the app?**
Four items shipped; one was **deliberately dropped after measurement**, and that
is the most reusable finding here. (Lane commits: `52b6538`, `3803c5b`,
`ec58956`, `116792d`.)

> The prior handoff (ADR-572 D8, `dbccbd1`) is **ABSORBED**. Two of its owed
> items are now CLOSED by this session — the stranded-row backfill (audited, not
> needed) and "a connector cannot NAME a workspace" (ADR-573). Its remaining
> item, the Print/PDF click-pass, is carried forward below.

## ⭐⭐⭐ The correction that opened this session — carry it

The audit's first finding was **WRONG**. I reported that MCP requests fall
through to a per-principal default with `workspace_id` unset — a real defect,
**fixed at `e0fa233` five hours before this session started**. I read the
*fixed* file and did not notice the D6 block inside it.

**A file read mid-session is evidence of that moment only.** A peer lane was
committing into the same working tree throughout. Before auditing anything, run
`git log --oneline -10` for work that landed after your context was built.

The paired lesson, from the parallel lane: **a ratified ADR is evidence of a
decision, never of an implementation.** D6 was ratified, cross-referenced,
written in the tense of intent — and never built.

## What shipped

### 1. ADR-373 D6's stranded-row backfill — AUDITED, not needed (`4b550bc`)

The prior handoff warned pre-fix connector rows were stranded and needed a
backfill. **Counted against production: they aren't.** 53 MCP-authored versions
across 4 workspaces; exactly **2 sit in a workspace their author doesn't own**,
and both are `Documents/d6-probe-2.md` — the D6 probe itself, caught by the bug
it was probing. **Zero NULL-`workspace_id` rows** on either substrate table.

⭐ **The published remediation query could never have run**: it selected
`authored_by FROM workspace_files`, and that column lives on
`workspace_file_versions`. **A query that errors on contact is worse than no
query — it reads as a discharged obligation.** Replaced with a runnable form
that also answers what the original couldn't: *does each row's workspace belong
to its author?*

No bulk UPDATE run, none warranted. Deleting the two probe rows would rewrite an
attributed revision chain (ADR-209) to tidy test files.

### 2. ADR-563 consent screen — who, where, what (`52b6538`)

The screen named the client and redirect host, then printed a **fixed sentence
wrong twice over**: *"read and write your memory"* — `memory` is pre-ADR-512
vocabulary (the unit of interop is the FILE), and a legacy `read` token can also
**DELETE** files and mint share links granting **MEMBER** access. Neither was
mentioned. ADR-563 made the tiers *enforced*; the consent surface never showed
them.

It also never said **which account** the bind would use (identity comes from the
JWT — on a shared browser, that is approving as someone else), nor **which
workspace**.

⭐ Tier definitions moved to **`api/services/mcp_scopes.py`**: the API serves the
consent screen and **cannot import `mcp_server.auth`** (py3.9 venv + py3.11-only
`mcp` SDK — the same constraint that put `delete_tokens_for_client` in
`services/principal_grants.py`). `auth.py` re-exports them. A route-side copy
would have rebuilt the pre-563 defect at the surface: a label free to disagree
with the check.

### 3. Members pane — the connection's verb tier (`3803c5b`)

The pane showed only the **path** axis (ADR-532 read/write regions). Production
carries **both** `read` (legacy full) and `files:read` tokens today, and they
rendered identically. Now its own line — merging it into the zone chips would
imply one narrows the other, and it doesn't: a connector scoped to `Documents`
can still hold a token that deletes and shares within it.

### 4. ADR-573 — the connector is bound to a workspace at consent (`ec58956`)

⭐⭐⭐ **The demand was measured, not assumed.** Exactly one production principal
reaches two workspaces: owns `My Workspace`, holds an active member grant into
the shared `yarnnn workspace`. **All three of their connector writes landed in
the owner workspace** — the commons their membership exists FOR was
*unaddressable* from the connector.

The operator now picks at consent; stamped on the code, carried to **both**
tokens, read per request.

- **A stamp NARROWS, never grants** — routed through the same
  `resolve_workspace_for_principal` the JWT door uses, and
  `principal_reaches_workspace` is uncached, so a member revoked *after* their
  token was minted loses reach on their next call.
- **NULL is not a missing value; it is "the principal's default."** All **421**
  live pre-573 tokens carry it. **No backfill** — stamping them would *freeze* a
  default that may legitimately move. Nothing repointed on deploy day.
- The binding **rides the refresh token**, or silent rotation un-binds every live
  connector with nobody acting (the ADR-386 D1.a shape).

## ⭐⭐⭐ The item I DROPPED — and why it matters more than the ones I built

I had recommended threading `workspace_id` into `AgentWorkspace`: it re-derives
on every call, while `AuthenticatedClient`'s own docstring says to derive once
and thread. It **reads** like an un-swept second path. Measured before "fixing":

- the owner branch is `lru_cache`d — a repeat call is a dict lookup, not a query;
- the uncached branch needs a principal with an active grant and **no owned
  workspace** — **production count: 0**.

~90 construction sites, zero behaviour change, zero queries saved. **Dropped**,
with the rationale and the reversing condition recorded *in
`api/services/workspace.py`* so it is not re-proposed from the shape alone.

**Measure the exposure before paying for the cleanup.** A pattern that looks
wrong is not the same as a pattern that costs anything.

## Gate craft this session paid for

- ⭐⭐⭐ **A falsifier FAILED and exposed a worthless check.** My FE grants check
  grepped `"grants"` and `".map("` independently; replacing `info.grants.map(…)`
  with `[].map(…)` left both tokens present, so **a screen rendering nothing read
  green**. Now matches the iteration over the payload. *A co-occurrence check
  cannot defend a specific site.*
- ⭐⭐ **Moving a definition can blind a gate.** ADR-563's AST loader keeps only
  `Assign` nodes, so an `import` re-export is invisible to it. It errored
  honestly — the dangerous version passes on a stale copy. It now follows the
  definitions to their new home, and calls the **shipped** `satisfied_by` rather
  than re-deriving containment (a gate that re-implements a rule can only prove
  the rule agrees with itself).
- ⭐⭐ **`bound_workspace_id` initialized inside the `try`** would raise
  `UnboundLocalError` on the stdio/static-bearer path, which takes the *except*
  branch. Caught while writing; now gated by AST.
- ⭐ **A comment can satisfy a check about behaviour.** My own explanatory comment
  quoting the banned copy failed the "copy is deleted" check. The gate was right.

## Verification that must stay green

```
cd api && /tmp/mcpenv/bin/python3.11 test_adr573_connector_workspace_binding.py  # 18/18
cd api && python3 test_adr563_consent_discloses.py                              # 23/23
cd api && /tmp/mcpenv/bin/python3.11 test_adr563_mcp_scope_enforcement.py       # 16/16
cd api && /tmp/mcpenv/bin/python3.11 test_adr373_rekey.py                       # 20/20
cd api && python3 test_adr373_sweep_spine.py                                    # 26/26
cd api && python3 test_security_2026_08_01_fixes.py                             # ALL PASS
cd web && node_modules/.bin/next build                                          # 171/171
```

⭐ Anything importing `mcp_server/*` needs **py3.11** (`/tmp/mcpenv`); the API
venv is 3.9 and dies at import on a `str | None` default annotation.
⭐ `test_adr404_member_invites.py` has **1 PRE-EXISTING failure** — verified by
stashing this work and re-running, not assumed.
⭐ Migrations run through `scripts/db/run-migration.sh` (`--dry-run` first); the
runner's exit code is **not** verification — read the live object back.

## Still OWED

1. **ADR-573 operator click-pass** — re-authorize a connector, pick the *second*
   workspace, prove the write lands there. The one principal who can drive it is
   `2be30ac5…` (owns `My Workspace`, member of `yarnnn workspace`).
2. **ADR-563 consent click-pass** — read the new screen on a real re-authorize:
   account, workspace, real tier, legacy-full warning.
3. **Print/PDF click-pass** (carried from ADR-572) — a native modal the harness
   cannot dismiss. Two minutes of operator time: Text → Export → Print/PDF →
   confirm the A4 page reads as a document.
4. **The connector is still not TOLD which workspace it is in.** ADR-533 D6
   refuses to export workspace *intent* into a third-party context window;
   whether the workspace **name** — as distinct from its mandate — should cross
   that line is **unaddressed**. Note the instructions string is composed at
   **import time**, so per-connection identity would have to be a **resource**,
   never the instructions.

## Deferred, deliberately — named so it is not re-discovered as novel

- **A per-verb `workspace` argument** was considered and rejected in ADR-573 §2:
  nine signatures change, the **model** becomes the chooser (a wrong guess writes
  to the wrong commons with full attribution), and ADR-512 D5's
  `yarnnn://workspace/…` grammar has no workspace slot.
- **`context-brief`** (carried from ADR-572) — in
  `api/services/derive_recipes.py`, targets markdown, resident `scout`, **zero FE
  consumers**. Text is its natural home; it needs its own decision about where a
  derived brief lands.

---

# Part H — ADR-592: an app declares how far along it is (2026-08-21)

## What shipped

`stage` — one field per kernel surface row (`internal | search-only | beta |
primary`, `services/app_stage.py`), from which `launcher_tier` +
`default_pinned` are DERIVED. Enforced at `kernel_surface_entries()`, the same
chokepoint ADR-375 §6 #4 uses for the steward.

- **Radar DELETED** — service, router, surface, registry row, app registration,
  API namespace, scheduler lane, its gate. Deleted rather than staged because
  its sweep was **metered spend on a clock**.
- **Docs `stage: internal`** — implementation intact (Studio parameterized),
  exposure gone. `/docs` → `/text`, `/radar` → `/files`, both stubs.

## The finding this came from

ADR-574 D2 declared Docs paused on 2026-08-17. Four days later it was still
fully reachable. Two mechanisms:
- `maybeReseedDock` only fires on **byte-equality** with the previous default,
  so any curated Dock keeps the icon permanently.
- `search-only` hides a tile at rest and nothing else — the route rendered,
  flat search matched `summary`, and a `document` double-click opened it.

Hence: `internal` removes the row from the **served roster** (nav is
backend-driven), which is the only spelling that reaches a curated Dock.

## ⚠️ The obligation `internal` carries

`middleware.ts` derives `SURFACE_PREFIXES` from the roster, so **a slug that
leaves the roster leaves the auth gate with it**. An internal app's route must
be a redirect stub AND hand-listed in the middleware. I nearly shipped this
wrong: a stash cycle silently reverted the middleware edit and the gate passed
green against an unprotected `/docs` until a falsifier caught it.

## Measured

- Gates: `test_adr592_app_stage.py` 35/35, falsified 3 ways (un-hide docs;
  unprotect the route; flatten the stage default — the last reproduces a real
  bug I hit, which promoted 27 surfaces to the Dock).
- 574 → 18/18, 518 → 36/36, 562/569/571/472/558 green, FE build green.
- **Pre-existing red, NOT introduced** (measured at `b0d03a6`):
  `test_adr297_phase1` 186/1 and `test_adr338_surface_registry_parity` 12/3 —
  every failure names `autonomy`.
- ADR-574 D3's recorded trap does NOT fire: `resolvedMode` comes from the
  LAYOUT vocabulary, not the app, and `document` still declares `mode: flow`.

## OWED

- **Operator (KVK)**: the Radar substrate. Workspace
  `d5b9029b-bd4e-4757-9fcb-e2b139fd4913` — 21 briefs under
  `operation/ai-frontier/briefs/` + `_radar.yaml`/`_watch_signal.yaml` there and
  under `operation/fundraising/deck-new-test/`. Workspace
  `bf5b25a9-477f-462e-b7f3-65812f489411` — `operation/desk-e2e/` declarations.
  Deleting the topic folder takes the briefs; delete only the `_*.yaml` to keep
  them. (The code change already stops the spend.)
- **Click-pass**: `/docs` + `/radar` redirect while logged in; logged-out both
  bounce to login (the auth pairing); no Docs/Radar icon on a CURATED Dock.
- **Staging envs** — discussed, not started. Separate ADR; needs a call on
  Supabase branching vs. a second project.
- `kind='radar'` rows in `tasks` are inert; harmless, could be swept later.

---

# Part H — a paged surface always names the page (2026-08-28)

Audit of a live turn: the Editor was asked to split "this slide", said **slide
6** for the slide the member was standing on (7), and then made the **right
edit anyway**. Both halves have one cause — it was never told where the member
was standing, so the number was narration and `data-block-id` was the operation.

## What shipped

Three layers had to line up for the silence; the fix holds each.

| Layer | Defect | Fix |
|---|---|---|
| Runtime | `reportScroll` bound to the `scroll` event + `stageShow` only — a deck the member never scrolled reported **nothing** | report on ARRIVAL (`setTimeout(reportScroll, 0)`) + after a restore |
| Declaration | with no selection and no viewport, StudioSurface fell to `document` scope — false on a paged artifact, not merely quiet | page grain is the FLOOR when `resolvedMode === 'paged'` |
| Renderer | `build_focus_line` renders `document` as `""` | **unchanged — correct**, and what makes the layer above load-bearing |

Judgment taken: **incident, not re-architecture.** ADR-522's declare-don't-scrape
contract is sound — Text and Strings hardcode `viewport: null` because they have
no page unit, and their `document` scope is truthful silence. Studio is the only
surface that can be silently wrong. The alternatives were all worse: enumerating
slides into the posture puts deck structure in the kernel (ADR-222); scraping the
viewport is the ADR-398 D2 locator ADR-522 replaced; storing slide ordinals is a
second source of truth against DOM order, walking back `3abfe20`.

`resolvedMode`, never `layoutMode` — the latter defaults to `'flow'` until the
vocabulary answers, so it would assert a page grain for an artifact not yet known
to have one (the ADR-480 reasoning at the same seam).

## The gate the old one couldn't be

`test_paged_focus_is_never_silent.py` — falsified **5 ways**, each red on its own
assertion: drop the arrival report · drop the restore report · revert the paged
floor (reproduces the original defect) · read `layoutMode` instead of
`resolvedMode` · drop `resolvedMode` from the dep array.

⭐⭐⭐ **`test_adr522_focus_declaration.py` certified the defect's own shape.** Its
assertion `"D5 document scope renders nothing (no finer grain to report)"` is
true for Text/Strings and **false for a deck** — and every focus dict it builds
already has `page_index` set, so it never exercised the state the incident was.
Rationale corrected in place; the renderer assertion stays (it pins the RENDERER,
and the declaration's obligation is now gated separately).

⭐ Two gate defects found in the writing: a 2000-char lookback window
false-flagged the restore call (proximity ≠ scope — now brace depth); and the
runtime region is **inside a template literal**, so backticks in my comment
terminated the string and broke the build. FE build green in an isolated
worktree (HEAD + my 2 files); the first "failure" was a missing `.env.local`,
not the change.

## OWED

- **Click-pass** (not driven in a browser): open a deck scrolled to a mid slide
  WITHOUT scrolling, ask "split this slide", confirm the Editor names the right
  one. The mechanism is gated; the browser path is not.
- **Two index spaces feed one `page_index`** — `currentSlideIndex()` counts
  `section.slide`; the pointer runtime's `pageIndexOf` counts
  `STRUCTURAL_PAGE_SEL` (`'section.slide, :is(body, main, article) > section'`).
  They agree on a pure deck and diverge on one bare `<section>` — so "slide 7"
  could mean different slides depending on whether the member clicked or
  scrolled. The rail uses the wide selector, the in-canvas `7 / 7` counter the
  narrow one. Deliberately NOT bundled here: collapsing them touches the rail,
  the stage counter and `arrangedPageAt`'s fallback ladder — a measured change.
- **Block scope drops the slide** — `build_focus_line`'s block branch names the
  block and never mentions `page_index`, though the FE populates it. A real gap,
  but a grain-composition question, not this viewport one.
- **Page scope sends no id** — `StudioSurface.tsx` hardcodes `id: null` for page
  grain, yet pages carry `data-block-id` since ADR-519. The one grain that gets a
  number gets no stable address — the same position-vs-identity failure
  `3abfe20` closed inside `artifactOps`.

---

# Part I — the Update door is deleted; the re-arrange comes home (2026-08-28)

**ADR-616.** Operator: *"completely delete the update button and its subfeatures.
any absorption required… streamlined and singular implementation discipline."*

## What the audit found before cutting

Update rendered **six act rows** over five rungs. Five were `onOpenPane(scope)` —
and the mount was `{ void sc; setRightTab('design'); }`. **A five-rung ladder
whose answer nothing read.** `StudioDesignTab` derives its own scope
(`scopeOf`, :1417), so those rows were one action wearing six labels.

⭐⭐⭐ **ADR-589's premise had expired.** Its §1 defect ("typography/palette/design
system have no entrance") became false independently: the pane renders them at
`document` scope whenever nothing is selected. It built a second door to a room
that already had one; ADR-613 then removed the judged verbs, leaving a
target-disambiguator for acts with nothing to disambiguate.

⭐⭐⭐ **The one row that could NOT go**: `handleApplyArrangement` had exactly one
caller and had already moved twice (out of the pane 2026-07-21, out of the
toolbar by ADR-589 D3). Add's gallery is a **different verb** — `onPick` →
`insertArrangement` (new page) vs re-lay this one, carrying content, dissolving
groups, running the ADR-479 placement judgment. Deleting blind would have taken
slide re-arrangement out of the product with nothing failing at build time.

## Shipped

- **D1** — `StudioUpdateMenu.tsx` + `updateLadder.ts` deleted; button, `onUpdateBlock`,
  `hasBlockSelection`, `hasPageAnchor`, `planning`, `updateMenu` state,
  `openUpdateDoor`, `retargetToRung` and the gesture's `!updateMenu` clause gone.
  `PaneScope`/`selection.ts` **survive** — the pane always derived its own.
- **D2** — the gallery is home in the pane's PAGE scope, above Layout.
  `arrangementCarryNote` **moved** with its one consumer (un-exported).
  `planning`/"Refining…" followed the act it describes.
- **D4** — the sparkle measures the **canvas column**, not `window.innerWidth`.
  This is the OUTER half of what `5abdce9` fixed on the inside. Both hosts
  supply it (Slides: `canvasWrapRef`; Text: `view.scrollDOM`).

## Gates

`test_adr616_update_door_deleted.py` — falsified **5 ways**: the act loses its
mount · the sparkle reverts to window arithmetic · the carry-note is left in two
homes · a row discards its scope again (`void sc`) · a second mount appears.
The one-mount check **globs the whole authoring tree** — a site-specific check
cannot see a second mount reappear elsewhere.

⭐⭐⭐ `test_adr589_update_matrix.py` **deleted with its subject**. Two dependent
gates read `StudioUpdateMenu.tsx` and would have passed **vacuously** (or
crashed) once the file was gone — `test_adr586_one_door.py` and
`test_adr612_judged_gesture.py` now assert the absence directly. ADR-612's gate
caught a real break: it pinned the suppression string `!slash && !citePicker &&
!updateMenu && !ctxMenu`; the roster shrank, so it now asserts the RULE plus
`"updateMenu" not in surface`.

FE build green (isolated worktree, HEAD + 7 files); tsc clean; ADR-589 marked
superseded with the reason.

## OWED

- **Click-pass** — not driven. Check: re-arrange from the pane (incl. a slotless
  arrangement's carry note and the "Refining…" state); the sparkle beside a deck
  selection with the pane OPEN, and again with it CLOSED; Text's sparkle at the
  right margin of the reading column.
- **Right-click menu clean-up** — operator-scoped as sequential, deliberately
  not bundled here.
- **ADR-589 D6's cited cell** (`edit source · swap citation · refresh pin`) was
  never built and is still unbuilt. It is owed against the PANE now, not the
  deleted door.
- **`document` rung's affordance** — the rail was the only *labelled* route to
  artifact scope from a live selection. The state stays reachable (empty-canvas
  click, `onPointClear`) and the pane names what to do there; if the operator
  wants it labelled, that is a pane-side crumb, not a door.

---

# Part J — the "+ Add" that did nothing, and the menu's families (2026-08-28)

Operator: *"when i created a new slide, the +Add like section was created, but
then the +Add doesn't work at all… most likely mismatch in implementation."*
Right on both counts.

## The dead "+ Add" — one attribute, three layers

ADR-544 D2 migrated the region grain `data-slot` → `data-area`. D7 states the
rule the migration left: **every consumer reads BOTH**. Every consumer did —
except `normalizeStructure`'s container predicate (`artifactOps.ts` Pass B),
which tested `data-slot` alone and **predated the migration** (written
2026-08-09; the rest of that file learned `data-area` on 08-19).

⭐⭐⭐ That straggler was **the pass that MINTS IDS**. So it did not mis-label —
it decided whether a region could be ADDRESSED:
- kernel emits only `data-area` → every **EMPTY** Area went unstamped;
- a **FILLED** region was caught by the other clause and worked — which is why
  it read as "new slides are broken" rather than as one attribute;
- the runtime draws "+ Add" **only inside an empty region** — exactly the
  unstamped set;
- `onAddHere` then returned **silently** for want of a `containerId`, never
  reaching `applyOp`'s honest shared error.

⭐⭐⭐ **An existing gate REQUIRED the defect**: `test_adr466_mode_native.py`
asserted the literal `"el.hasAttribute('data-slot')" in ops` under the label
*"an EMPTY declared region still gets identity"* — enforcing the bug and
blocking the fix, while reading GREEN. Re-anchored to the invariant.

**Shipped**: `REGION_SEL` in `structureLabels.ts` (one spelling); Pass B and
`countGroupsOnPage` (a 2nd straggler — Areas counted as authored groups, so the
carry note promised a false ungrouping) both read it; 4 hand-spelled pairs
converged; the runtime draws the BUTTON only where an id exists (bounds stay
wider — a button that does nothing is worse than no button); `onAddHere`
reports instead of returning bare.

## ADR-619 — the menu's families (operator, mid-turn)

Copy nests with Duplicate/Delete (it was stranded above Paste, whose subject is
the CLIPBOARD not the block). `Update ▸` deleted in full — three unrelated
families (Turn into · Move · Bring) under a verb naming none, each already
self-gated, now flat. Rewrite added as a **second entrance** to the floating
gesture's identical workflow; `seedRewrite` is the ONE producer, the menu reads
its own context target (never the rect — a rect-keyed row is inert on message
timing, the same silent class as above).

⭐⭐ Two gates had pinned SPELLINGS: 586's `<Flyout open={` **>= 3** (with a
comment citing the ADR-584 lesson against hand-kept counts — then failing on the
2nd correct deletion), and 612's `"Rewrite…" not in block_menu`. Both
re-anchored to invariants, not relaxed.

⭐ **ADR-618 was claimed by a peer lane mid-session** — renumbered to 619.

## Gates

`test_region_grain_is_one_selector.py` (falsified 5×) ·
`test_adr619_menu_families.py` (falsified 5×). ⭐Two of my own assertions were
too weak and were caught BY falsifying: a substring check that the guard's own
attribute-setter satisfied, and an ordering check against a mention that moved
with the guard (fixed by asserting the guard appears exactly once).

FE build green (isolated worktree, HEAD + 5 files); tsc clean; `test_adr466`
holds at its **10 pre-existing** failures.

## OWED

- **Click-pass**: create a slide → "+ Add" in an empty region inserts text;
  a MEDIA region still routes to the picker; right-click shows Copy/Duplicate/
  Delete together, flat Turn into/Move/Bring, and Rewrite seeding the composer
  identically to the sparkle.
- **The Add surface is NOT one mechanism** (mapped, not fixed): 5 doors, 6
  terminal ops, 4 target-resolution schemes, 2 taxonomies of one vocabulary
  (`categorizeBlockRows` for toolbar+right-click vs `groupBlockRows` for slash).
  ⭐**New-slide rail uses `anchor` (selection only) while the block rails beside
  it use `resolveInsertTarget()` (with viewport fallback)** — same popover, two
  answers to "where": on a deck paged to slide 2 with nothing selected, a block
  lands on slide 2 and a New slide lands at the END. ⭐**Paste ignores
  page/slide anchoring** and lands on the last slide. Both are real, both
  deliberately out of this scope.
- **~18 other silent no-op guards** on the insert paths (each an early `return`
  with no feedback); only `onAddHere` was fixed here.

---

# Part K — ADR-620: Compose is Rewrite at slide grain (2026-08-28)

Operator: *"the Add related details seem to only scaffold skeleton components…
similar to rewrite, we could have AI related compose"* → then *"can we have a
dedicated component… something that feels more first class and visual."*

## The finding

`+ Add` stamps registry fragments whose bytes are LITERAL (`42%`, `label`).
Correct for a CATALOG gesture — the member knows the noun — and unable to serve
an INTENT. Rewrite is judged/seeded/receipted and stops at the block.

⭐⭐⭐ **Not the re-arrange re-framed** (the operator's proposal, checked and
corrected): `applyArrangementPlan` MOVES existing nodes (`returnToFlow(b);
target.appendChild(b)`) — a PERMUTATION, which is exactly why it can promise
total coverage and fall back to a mechanical ladder. A compose has no such
floor, and its planner resolves **Designer** deliberately ("machinery that
happens to plan layout, not the desk's voice") while a member-facing slide act
is the **Editor**. Re-arrange is the narrowest member of the family, not the
frame for it.

## ⭐⭐⭐ Built, then DELETED before shipping

A first cut built `/studio/compose/plan` + a validator + `applyComposePlan` — a
faithful mirror of ADR-479. **A second write path** (ADR-462 D1). The lane
ALREADY has EditFile-with-anchor, the block grammar in the posture, and one
attributed write. Deleted whole; Compose is Rewrite's machinery unchanged.

## Shipped

- **D1** `compose` = 4th seed verb, slide grain. Page's own id + `page_index`.
- **D2** the colleague writes through the lane. No endpoint, no applier.
- **D3** `remove` is the member's PERMISSION, riding the seed, rendered in the
  frame in **BOTH** directions (an absent instruction is not a prohibition).
- **D4** the chip GROWS A BODY (slide's blocks by kind + the D3 toggle), never
  a modal — a modal covers the slide being described and has no transcript.
  ⭐The DOOR is the **pane's page scope**, not a floating sparkle: the runtime
  reports a rect for blocks and ranges, never a page.
- **D5** `+ Add` untouched — the catalog of things that EXIST.
- Extracted `_meter_plan` (one billing invariant, one home).

## ⭐⭐ Latent defect surfaced

`_seed_line` read the page grain as `page is not None and not bid` — "no block
id" standing in for the grain, true ONLY because pre-620 nothing at page grain
carried one. A composed slide carries the page's id (ADR-519), so it would have
said **"the slide block"**. Fixed in the frame AND the chip (they must read
identically before/after Send) and gated together.

## Gates

`test_adr620_compose_at_slide_grain.py`, falsified **5×** (additive case goes
silent · noun proxy restored · a second producer · plan endpoint returns · chip
noun diverges). ⭐**The gate caught my own D2 violation**: my first `composeSlide`
called `seedComposer` directly — a second producer — and it went red.

⭐⭐ `test_adr579_d7_structured_turns.py` was **PRE-EXISTING RED** (verified at
HEAD): it pinned the door ROSTER (`3× ask` + `rewrite` + `check`) and ADR-613
deleted Ask/Check from Slides. Failing since 613, unread. Re-anchored to D7's
actual claim (a door passes a TYPED target).

FE build green (isolated worktree); tsc clean; prompt ratchets pass.

## ✅ CLICK-PASSED live (2026-08-28, prod, isolated Chrome profile)

Driven end to end on `operation/yarnnnn-decl/deck.html`, slide 1:

| Claim | Observed |
|---|---|
| D4 door in the pane's page scope | `SLIDE 1` → **"Compose this slide…"** |
| D4 chip grew a body | `Compose · slide 1 · AI` + **"On it now: figure, heading, heading, heading, prose"** |
| D3 additive is the DEFAULT | `Fill in what's missing: aria-pressed=true` |
| D3 toggle works both ways | flipped to Replace and back, `aria-pressed` tracked |
| §5 the noun fix | reads **"slide 1"**, never "the slide block" — the live proof of the page-grain fix |
| D1 the seed crosses | transcript stamp reads **`Compose · slide 1`** on the member's row |
| D2 the colleague writes via the lane | Editor: *"The subtitle is t3"* → `read a file · revised a file` |
| D3 additive HELD | subtitle rewritten; **all 5 blocks survived** (nothing removed) |

Result: *"Why the founders who stay in a contraction end up owning the next
cycle."* → *"Founders who stay in the contraction own the next cycle."*

⭐ Harness notes: your Chrome runs a shared profile and is UNATTACHABLE — launch
an own-profile instance (`--user-data-dir`) and drive raw CDP; never kill
theirs. Chrome 152 needs `"--remote-allow-origins=*"` (quote it — zsh globs the
`*`). A rail-card click NAVIGATES but does not select; the pane reaches page
scope only from a canvas click. `Enter` must go through
`Input.dispatchKeyEvent`, not a synthetic `KeyboardEvent`.

## OWED
- **Receipt card** — D4 names one; the transcript currently renders the composed
  turn like any lane write (`artifactWrite="none"` in Studio, so the canvas IS
  the receipt). Decide whether a page-grain card earns its place.
- **Text has no Compose** — the verb is medium-agnostic but only Slides declares
  a door. A section-grain compose in Text is the obvious sibling.
