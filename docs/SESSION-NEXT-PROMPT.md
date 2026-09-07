# Carry-over prompt — audit the 2026-09-07 arc, then pick up what it left

> Written 2026-09-07 at `13ba1db`. Paste the block below as the next session's
> opening prompt. It asks the session to front-load its own context and audit
> the day's work rather than trust this summary of it.

---

## The prompt

You are picking up a YARNNN session after a long 2026-09-07 arc. **Do not take
this prompt as fact — it is one session's account of itself.** Front-load your
own context first, in this order, and verify every claim you intend to build
on against its receipt (a commit, a file, a gate, a query):

1. `docs/SESSION-HANDOFF.md` — Parts **T**, **S** and **R** (top of file, newest
   first). T is the owed list closed; S is the composition thread shipped and
   click-passed; R is the skills measurement they grew from.
2. `git log --oneline -15 --format='%h %ad %s' --date=format:%H:%M`. ⚠️ **A
   parallel session commits in THIS checkout** (`9705b35` "a declaration in
   Trash must not be discovered" landed between two of mine). Run
   `git status` before touching anything, never `git add -A` without reading
   it, and check authorship/time before assuming a change is yours to build on.
3. `api/prompts/CHANGELOG.md` entries `[2026.09.07.1–3]` — the prompt-layer
   changes and the measurements behind them.
4. The three analysis captures dated 2026-09-07 in `docs/analysis/`.
5. `.claude/validation-ledger.json` and the verification radar the SessionStart
   hook prints — it tells you which lanes are DUE.

### What the arc claims it shipped (verify each)

| Claim | Receipt to check |
|---|---|
| The Text canvas draws a markdown image (figure + inline), one shared resolver for both faces, a revealed block returns on caret-leave | ADR-590 D5; `web/lib/workspace/imageUrl.ts`; `test_adr571` §17g/17h/17h3 (mounts the canvas) |
| The Text posture carries the three markdown reference forms; driven 3/3 vs 0/2 on prod | `services/apps/text.py`; `[2026.09.07.2]`; `test_adr571` §2d–2f (ceiling 2,100; 1,933 at ship) |
| `POST /api/images/export` lands the browser's raster beside the artboard as a derivation, stable path | `routes/images.py`; `test_adr475` (59/59, was 0/1 at baseline); ledger row `operation/untitled-image/exports/image.png` |
| **Every Download PNG since 2026-07-22 was blank white** — fixed by positioning the clone on-canvas | `861d176`; ADR-475 §13 note; the export re-sampled 274,679/291,600 non-white |
| `assembling-a-composite-document` measured NULL (p=0.500, read 0/3 both arms) → rank 2 | `docs/analysis/assembling-a-composite-document-measured-2026-09-07.md`; `_INDEX_RANK` |
| The standing sweep's receipt names the reach outcome; `StandingSource.reads` serves the binding's statement | `services/standing_work.py::_reach_outcome`; `routes/standing_work.py`; ADR-594 D2 note |
| ADR-640 D2 built: `craft` + `tending` on the agents payload, two read-only rows | `routes/lanes.py::_tending_by_agent`; `services/skills.craft_for_agent`; `test_adr640` §5 |
| `ADR-411 D4` swept to `ADR-408 D2 · ADR-460` at 33 sites; §3.2.1 re-cut | `grep -rn "ADR-411 D4"` should hit only lines that describe the phantom; `docs/architecture/agent-composition.md` |

### The audit — do this before building anything

**A. Reconcile with the parallel session.** Read `9705b35` and anything after
it. It changed `services/standing_work.py` discovery and extended
`test_adr639`; my reach-receipt edits (`_reach_outcome`, `receipts[plat]`) are
in the same module and survived the merge (`test_adr639` green at `13ba1db`).
Confirm that is still true at your HEAD, and confirm the live workspace's
standing state: at 02:36 the one declaration (`operation/fundraising/
_standing.yaml`) was "retired at operator request" and a
`_lifecycle-probe-2026-09-07/` declaration was created/archived/cleaned at
02:48. `tasks` (kind=standing) had 0 rows. **Do not create declarations on
prod without checking what that session is doing.**

**B. Two gates red at the committed baseline** (proved red at HEAD before this
arc touched anything; recorded, not fixed):
- `test_adr501_read_path_binding.py` reads `routes/radar.py`, deleted with
  ADR-603 D5. A gate that cannot run. Re-point at what ADR-501 D-whatever now
  binds to, or retire it with a one-line ruling in the ADR-LEDGER.
- `test_adr535_connector_visibility.py` fails 2 of 21. Read the two; they may
  be the same ADR-603 D5 fallout or a real regression nobody has looked at.
Method: always run the committed version (`git show HEAD:api/<gate> >
api/_base.py`, run from `api/`, delete) before ruling a red as baseline.

**C. Look at the day's surfaces once, as the operator would.** The DevTools
MCP browser is authenticated on prod. Open `/text` on a document with an
image line, `/images?images.file=operation/untitled-image/image.html` →
Export → *Save PNG to workspace*, and `/agents?agent=editor`. Sample the PNG's
pixels (fetch → `createImageBitmap` → `getImageData`); *decoded* is not
*shows something*. ⚠️ `AgentsSurface` renders "Could not load this." during
its initial fetch — the same sentence as a real failure. Wait a beat before
reading a snapshot as a defect; and decide whether that copy should change.

**D. Then the owed list, in this order**, each with its own commit:
1. The two baseline-red gates (B).
2. Carried from Part O, untouched all day: `projection.ts`'s second CSV parser
   (the Text app lifted a quote-aware one into `markdownEdits.ts`; the
   projection still has the line-split one) · a Files door for declaring
   standing work · blogger's standing leg.
3. `./relative` image paths in markdown — refused in ADR-590 D5 (both faces
   fail alike); open it only if the operator asks.

### What would change the plan

- The parallel session has moved standing-work discovery in a way that makes
  `_tending_by_agent` (routes/lanes.py) read the wrong set → fix there, not
  by re-deriving; the gate is `test_adr640` §5.
- A red in `test_adr571` §17h — the canvas mount — means the image widget
  regressed; do not re-point the gate at the renderer (that is exactly the
  defect it was written against).
- A blank PNG from a *different* artboard → the clone-positioning fix is
  incomplete; sample before believing a download.

### Method notes that cost this arc real time

- ⚠️ **A background Bash shell has a different PATH.** `pnpm` is not installed
  (build with `npm run build`), `node` lives only in `/opt/homebrew/bin`; a
  gate that mounts the canvas errors opaquely without it. `export
  PATH=/opt/homebrew/bin:$PATH` first. And `cd` persists between calls — use
  absolute paths.
- ⚠️ **The router flags live on Render, not `.env`.** A laptop probe driving
  `run_lane_turn` needs `MODEL_ROUTER_ENABLED=1` and `LANES_ENABLED=1`
  in-process, or every trial "fails" with a refusal that looks like a result.
- ⚠️ **A log filter by indentation erases receipts.** `grep -v "^\s+"` dropped
  every per-trial line of a probe. Filter tracebacks by token; `tee` the raw.
- Drive CodeMirror with `document.execCommand('insertText')` from
  `evaluate_script`; the DevTools `type_text` tool scrambles markdown
  punctuation, a synthetic `KeyboardEvent` does not move the caret (use
  `press_key`), and the prod bundle hides `cmView`.
- A gate that aborts on its first failure hides every failure behind it
  (`test_adr475` had two, stacked). Stub external gates (spend, keys) at the
  module the handler imports from.
- A capture of a page can be a true frame of a white image. When a DOM probe
  and a screenshot disagree, suspect the CONTENT before the capture.

**Start with A and B. Commit each ruling on its own. Push when green.**
