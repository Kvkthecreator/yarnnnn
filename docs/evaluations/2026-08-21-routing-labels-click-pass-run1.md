# Click-pass run record — engine labels, /engines, admin cost endpoint

**Date**: 2026-08-21
**Commits under test**: `b0d03a6` (labels, /engines, fallback layer) + `02b1cf4`
(override validator, dead-endpoint deletion). Both confirmed **live** on
`srv-d5sqotcr85hc73dpkqdg` before driving; Vercel FE confirmed live behaviourally
(the removed LMArena link was absent from the rendered page).
**Principal**: owner (`kvkthecreator@yarnnn.com`), single principal — see
NON-COVERAGE.
**Instrument**: Claude in Chrome (browser lane).

Per BROWSER-CLICK-PASS-PLAYBOOK §1, every step below records BOTH halves.
Steps marked SUBSTRATE-VIA-API record the server's own rendered output rather
than a `psql` row (no DB credentials in this session — declared, not hidden).

---

## Step 1 — /engines: LMArena removed in full

**DOM.** `https://yarnnn.com/engines` renders (title "Choosing an engine | yarnnn"
— an app marker, so we reached the app, not a bot-challenge page). Scripted DOM
query returns:
- `mentionsLMArena: false`, `lmarenaHref: false` — zero occurrences in text OR
  in any `<a href>`.
- Outbound list is exactly: Artificial Analysis + Anthropic + OpenAI + Google +
  DeepSeek + xAI. All five providers in `LANE_MODELS` still represented.
- Headings intact: "Why we don't rank them here" · "The part that doesn't move" ·
  "Where the current numbers live" · "Your own workspace is the better benchmark".
- Singular copy live: `"This is independent of us"` present, plural
  `"These are independent of us"` absent.

**SUBSTRATE.** Gate `engines-page-providers.test.mjs` 7/7 green, including the
new assertion that lmarena STAYS removed. **Falsified**: re-adding lmarena while
removing artificialanalysis fails the gate (exit 1, "missing outbound source:
artificialanalysis.ai").

**PASS.**

---

## Step 2 — the engine picker shows versioned labels

**DOM.** `/chat` → "New lane" → dialog "Which engine?". Real DOM state query
(NOT an a11y snapshot — playbook §2), 9 rows:

| label | disabled | aria-disabled | last used | brand svg |
|---|---|---|---|---|
| Claude Opus 5 | false | false | — | yes |
| Claude Sonnet 5 | false | false | — | yes |
| Claude Haiku 4.5 | false | false | — | yes |
| GPT-5 | false | false | — | yes |
| GPT-4o mini | false | false | — | yes |
| Gemini 2.5 Pro | false | false | — | yes |
| Gemini 3.5 Flash Lite | false | false | — | yes |
| DeepSeek V4 Flash | false | false | **yes** | yes |
| Grok 4.6 | false | false | — | yes |

- Every offered engine carries a VERSION. Compare the pre-fix screenshot:
  "Claude Opus" · "Gemini Flash" · "DeepSeek" · "Grok".
- **No retired engine leaked to the door** — 9 offered, 3 retired absent.
- `last used` on exactly ONE row, matching
  `localStorage['yarnnn.chat.lastEngine'] = 'deepseek/deepseek-chat'`, and that
  row is 8th — confirming the badge does NOT reorder or pre-select. (The
  NewChatModal header comment claimed "pre-selects" until `b0d03a6`; the
  observed behaviour is badge-only, which the corrected comment now states.)

**SUBSTRATE.** Labels are server-supplied from `LANE_MODELS` via `/api/lanes`;
the FE holds no label table for the chooser. Gate `lane-model-labels.test.mjs`
5/5 (cover · verbatim-match · uniqueness · version-present).

**PASS.**

---

## Step 3 — the versioned label reaches ATTRIBUTION (the defect this fixed)

**DOM.** Picked "Claude Sonnet 5". Lane created
(`?chat.lane=2f5574b1-…`). Header, lane-list row, and the empty-state sentence
all read "Claude Sonnet 5", including the attribution promise verbatim:

> "This conversation is private to this lane. The work it produces lands in the
> shared workspace files, **attributed to you via Claude Sonnet 5**."

`localStorage` updated to `anthropic/claude-sonnet-5` only AFTER the lane
created successfully.

**SUBSTRATE-VIA-API.** Drove a real turn ("write a file at
operation/routing-click-pass.md"). The turn ran, called `wrote a file`, and the
artifact card rendered:

> `operation/routing-click-pass.md` · Markdown · **· you via Claude Sonnet 5**

That string is composed SERVER-side by `principal_display.model_display` off
`LANE_MODELS`. Before `b0d03a6` it would have read "you via Claude Sonnet" —
indistinguishable from a revision authored by the RETIRED `claude-sonnet-4-6`.
The file also appears on `/files` (Recents) and `/activity`.

**Collision check**: regex for a bare `via Claude Sonnet` (not followed by a
version) returns FALSE on `/files` and on `/activity`. The ledger collision is
gone in production.

**PASS — this is the step the whole change existed for.**

---

## Step 4 — the dead admin cost endpoint is gone, the live one is not

**DOM.** `/admin` redirects this principal to `/desktop` (not an admin account),
so the admin surface itself was NOT observed. Declared as non-coverage below.

**SUBSTRATE-VIA-API.** Status codes distinguish deleted-vs-protected:

| endpoint | status | meaning |
|---|---|---|
| `/api/admin/token-usage?days=7` | **404** | route no longer registered — DELETED |
| `/api/admin/execution-stats` | **401** | route EXISTS, correctly requires admin auth |

The two different codes are the point: a blanket 401/404 on both would not have
distinguished "deleted" from "auth-gated". Locally, `admin.router.routes` was
enumerated: `/token-usage` absent; `/execution-stats` and `/export/report`
present.

**PASS.**

---

## Step 5 — cleanup (and a correction worth recording)

Moved `operation/routing-click-pass.md` to Trash through the Files context menu
(a confirm dialog appeared first: "It stays recoverable — you can restore it
from Trash any time"). Trash pane then showed
`operation/routing-click-pass.md · deleted 2026-08-21 · by You` with
Restore/Delete.

⭐ **A wrong read, caught by driving.** After the delete I checked Recents, saw
the entry still listed, and initially read it as "the delete did not take". It
had taken — **Recents is a CHANGE-HISTORY view, and a deletion is itself a
change**, so the entry correctly persists there. Only opening Trash settled it.
Inferring from the wrong pane would have produced a false defect report.

**PASS.**

---

## NON-COVERAGE (declared, not hidden)

1. **Single principal.** Owner only. The label change is not principal-scoped
   (it is one server-side table), so a member pass would exercise the same code
   path — but this is not a two-principal pass and must not be cited as one.
2. **The admin SURFACE was never rendered.** This account is not an admin, so
   the deleted "Token Usage & Cost" card was verified by route status + local
   router enumeration, NOT by seeing the page without it. An admin-account pass
   is still owed to confirm the remaining cards render intact.
3. **No `psql` receipts.** No DB credentials in this session. Substrate claims
   rest on server-composed output (the attribution string, the Trash row), which
   is one inferential step short of reading `workspace_file_versions`.
4. **The env-override validator was NOT exercised in production.** It is proven
   by a 12/12 gate falsified in both directions locally, but no
   `YARNNN_SYSCALL_*` typo was set on a live Render service — deliberately: the
   dials are shared infrastructure and a live mis-set would affect real turns.
5. **DeepSeek + xAI still render the generic Cpu glyph** (no vendored brand
   mark). Observed, unchanged by this work, and a design call rather than a bug.
