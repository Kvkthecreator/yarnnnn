# Session handoff — 2026-08-17

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
