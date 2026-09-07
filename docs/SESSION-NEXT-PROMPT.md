# Carry-over prompt — audit the Reach / one-reach-status arc, then click-pass it

> Written 2026-09-07 at `32fc0ed`. Paste the block below as the next session's
> opening prompt. It asks the session to front-load its own context and audit
> the day's work rather than trust this summary of it. It replaces the
> 2026-09-07 morning prompt (`2f32b21`), which the day absorbed.

---

## The prompt

You are picking up a YARNNN session after a two-session 2026-09-07 arc. **Do
not take this prompt as fact — it is one session's account of itself, and a
second session was committing in the same checkout all afternoon.** Front-load
your own context first, in this order, and verify every claim you intend to
build on against its receipt (a commit, a file, a gate run with its exit code,
a query):

1. `docs/SESSION-HANDOFF.md` — Parts **V**, **U (Reach)**, **U** (the parallel
   session's — the ADR-643 access decider) and **T**, top of file, newest
   first. Two parts are both titled U; the retitled one is mine.
2. `git log --oneline -30 --format='%h %ad %an %s' --date=format:%H:%M`.
   ⚠️ **Two sessions committed interleaved** — mine are `72f4549`, `b7c1cc0`,
   `32fc0ed`; the other's are the ADR-643 chain (`3f9dffd` … `8147e86`) plus
   `a3b2ecb`/`940c400`. Run `git status` before touching anything; stage by
   explicit path; never `git add -A`.
3. The canon this arc wrote: `docs/adr/ADR-642-the-boundary-has-a-door.md`,
   `docs/adr/ADR-644-one-reach-status.md`, and amendment 3 of
   `docs/adr/ADR-628-the-outbound-disposition.md`. Then
   `api/prompts/CHANGELOG.md` `[2026.09.07.6]` and `[.7]` (the reach section
   of the lane frame changed twice; `.7` supersedes `.6`).
4. The verification radar the SessionStart hook prints, and
   `.claude/validation-ledger.json` — it says which lanes are DUE.
5. `docs/architecture/ADR-LEDGER.md` entries 642 · 643 · 644 (the last three
   lines) for the rationale in one screen each.

### What the arc claims it shipped (verify each; a claim without its receipt is narrative)

| Claim | Receipt to check |
|---|---|
| **Reach** is a PRIMARY kernel surface at `/reach` with Connected · Leaving · Crossed; the `queue` surface is absorbed (stub → `/reach?reach.pane=leaving`) | `services/kernel_surfaces.py` row `reach`; `web/app/(authenticated)/reach/page.tsx`; `web/app/(authenticated)/queue/page.tsx` is a `redirect()`; `test_adr642_reach.py` (51) |
| Crossed is the ONE timeline under `?lens=boundary` (observations in, `_publish.yaml` receipts + decided boundary proposals out), receipts attached, weighted material | `routes/workspace.py::get_workspace_timeline` `lens=`; `receipt_for_revision`; test_adr642 D2 (the fake FILTERS on the predicates it is handed) |
| **Slack is the second outbound tenant**: prose only, join-before-post, refusals mapped, **D8 read-back mechanized** (`matched\|differs\|unreadable`), `SendToSlack` on the Text pane by mount | `services/publish.py::publish_file_to_slack`, `compose_slack_message`; `routes/publish.py`; `web/components/authoring/SendToSlack.tsx`; `test_adr628_outbound_publish.py` §8 (74) |
| **ONE reach structure** (ADR-644): `services/reach_status.py` — facts derived once; `describe` = the member face, `frame_paragraph` = the agent face, `list_integrations` = the same rows; `connector_does` and the three hand-written reach branches DELETED | `grep -rn connector_does api/services api/routes` → only the epitaph; `lane_runner.py` calls `frame_paragraph(`; `test_adr644_one_reach_status.py` (53) — the tool result and the LIST route are compared row for row to the structure |
| No first-party platform has a live agent write path (`write_slack` is a registry fossil of the deleted task pipeline) — the surface, the frame and the tool result all say the agent cannot send and name the member's door | test_adr644 D1: the falsifier patches a write tool into `turn_reach_tool_names` and every face flips |
| Scope legibility: Connected is the VIEWER's account connections; Leaving + Crossed are THIS WORKSPACE's | the pane subtitles in `reach/page.tsx`; the kernel row summary |
| CLAUDE.md brought under its 50,000-char ceiling (it was 52,309 at the morning's HEAD) by moving row narrative to the ledger | `python -m pytest api/test_claude_md_ratchet.py` — **49,999 chars, zero headroom**: adding a row means trimming one |
| `StudioPublish`'s raw anchor to Connectors → `navigateToSurface` (the nav gate had been red on it since 2026-09-01) | `test_nav_no_cross_surface_router_push.py` |

**Two things this arc got wrong and corrected the same day — check the corrections held:** (1) ADR-642 D5's first cut read the capability registry and claimed an agent proposal path for Slack; the operator's click-pass falsified it within the hour. (2) `test_adr582` 7n was RED between `72f4549` and `b7c1cc0` while my log grep reported it green — a `grep` for a summary line that happens to print a PASS line last is not a result. **Read exit codes, never the last line.**

### The audit — do this before building anything

**A. Reconcile with the parallel session (ADR-643).** It rebuilt the access
decision (`routes/workspace.py` gained `access` on the file response; the
organize verbs; `web/lib/workspace/ownership.ts` DELETED; a live FE regression
found and fixed at `3774a5b`). None of its files overlap mine except the
handoff and the ledger, where each session appended its own hunk. Confirm at
your HEAD that `test_adr643_one_decider.py`, `test_adr644` and `test_adr642`
are all green together — they have never been run in one sitting after both
sessions finished.

**B. The click-pass that is OWED — the one thing nobody has looked at.**
The DevTools MCP browser profile was held all afternoon by the other session's
Chrome (`--remote-debugging-pipe`, not attachable; `ps aux | grep
chrome-devtools-mcp/chrome-profile` and check for a live `claude` process
before assuming it is stale). When you have the browser, on the deploy:
1. `/reach` — all three panes, both themes. A colour decision has to be
   looked at; 23/23 green over a rainbow spine happened four days ago.
   Connected: five rows expected (GitHub · Linear attached/pending · Slack ·
   Notion · WordPress); Slack's Agents line should read *"read only — 2 read
   tools; cannot send"*. Leaving: the boundary families only. Crossed: three
   WordPress receipts from 2026-09-03/04 with `publicly_readable: false`, and
   the uploads as arrivals.
2. `/text?text.file=operation%2Fprd-for-yarnnn%2Fclaudesession.md` → ask the
   editor *"can you send this to my Slack channel"*. It should decline and
   name **Send to Slack on this pane** from its frame — not "check Settings",
   and not by calling a tool first. If it still says Settings, the deploy is
   stale or the reach section is not composed: check Render's deploy for
   `32fc0ed` and `{connector_reach_section}` in `_CONVENTIONS_FRAME`.
3. Send to Slack… for real, on a prose file, to a public channel. Read the
   receipt: `read_back: matched`, the permalink, `folded`. Then Crossed should
   show it with the verdict. (Local cannot do this — the encryption key lives
   only on Render; a local API boots with a throwaway Fernet key and every
   connection reads "not connected".)

**C. Three gates red at the committed baseline, untouched by design:**
`test_adr346_operation_composition.py`, `test_adr349_launcher_ia.py`,
`test_adr340_p3_launcher.py` all `KeyError` on `recurrence` (ADR-603 D5,
2026-08-24). Their `queue` lines were re-anchored to ADR-642; the
`recurrence` rot needs one ruling: retire the three with a ledger line, or
re-anchor them on ADR-603. Method: `git show HEAD:api/<gate> > api/_base.py`,
run from `api/`, delete — prove the red predates you before ruling.

**D. Then the owed list, in this order, each its own commit:**
1. B (the click-pass), with a handoff Part and validation-ledger marks.
2. C (the three gates), one ruling.
3. **The remote binding ADR** — a file that knows its remote, pull + push
   through the proposal queue. It now has two outbound tenants to bind to;
   it is composition-by-reference (Part S) extended past the workspace
   boundary. Write it doc-first; do not build until the operator rules.
4. WordPress's D8 read-back (`read_post` behind the seam + a canary) — the
   last precondition for phase (b) on that tenant.
5. ADR-635's distribution: the registry publish, the plugin-directory
   submission, the attach click-pass. Operator acts; sequenced after Reach
   by ruling.
6. `sources` (the ADR-335 bundle-watch row, hidden since ADR-425): delete or
   re-home, one ruling (ADR-642 §4).
7. Carried since Part O: `projection.ts`'s second CSV parser · a Files door
   for declaring standing work · blogger's standing leg.

### What would change the plan

- **A fifth face.** Any sentence anywhere that tells a member or an agent
  what a connection lets a turn do and does not render `reach_status` — in
  a skill, a posture, a settings pane, the MCP server — is the defect ADR-644
  exists to end. Route it through the structure; do not edit the sentence.
- `test_adr644` D1's falsifier red → something composes a write tool into a
  live loop. That is a REAL change in reach; find who and why before touching
  the gate.
- `test_adr535` red → the four reach states' prose moved. The fragments it
  asserts live in `reach_status.frame_paragraph` now; fix there.
- The Reach chrome reads wrong on screen → fix the component; the gates are
  green and cannot see colour, spacing or an empty state that says the wrong
  thing.

### Method notes that cost this arc real time

- ⚠️ **Read gate exit codes.** `venv/bin/python gate.py > out; echo $?` — a
  `tail -1 | grep PASS` reported `test_adr582` green while 7n was red.
- ⚠️ **A gate that greps its own documentation goes red on the sentence
  explaining the rule** — three sightings today (`useEffect` in a stub's
  docblock, a quoted `href` in a code comment, a semicolon in an older
  union comment). Strip comments before any substring check; describe a
  removed literal, never quote it.
- ⚠️ **A multi-pass text transform must emit placeholders for any form a
  later pass reads** (`## H` → `*H*` → re-read as italic → `_H_`). The gate's
  fixture that carries every rule at once is what caught it.
- ⚠️ **A registry row is not a live path.** Derive "can X do Y" from the
  composition site (`turn_reach_tool_names`, `lane_tool_names`), never from
  `PLATFORM_TOOLS_BY_CAPABILITY` or `orchestration.CAPABILITIES` — both still
  carry rows for the deleted task pipeline.
- ⚠️ **`test_adr577` has TWO allowlists** (`PRINCIPAL_LESS_CREDENTIAL_READS`
  exempts a reader; `ENUMERATION_ONLY` checks it never grows a credential
  column). A new enumeration reader goes in both; a reader that stops reading
  leaves both.
- ⚠️ **CLAUDE.md is at 49,999 / 50,000 chars.** A new row means compressing
  an old one to its starred instructions — the ledger already carries the
  narrative. Measure in chars (`len(open(...).read())`), not bytes.
- ⚠️ **A background Bash shell has a different PATH.** `pnpm` is not on it —
  build with `npm run build` from `web/`; `node` is in `/opt/homebrew/bin`.
  `cd` persists between calls — use absolute paths. The API refuses to boot
  locally without `INTEGRATION_ENCRYPTION_KEY`; export a throwaway Fernet key
  for a local click-pass only, never write it to `.env`.
- The `MEMORY.md` index is compacted to 15 KB; keep one line per entry.

**Start with A and B. Commit each ruling on its own. Push when green.**
