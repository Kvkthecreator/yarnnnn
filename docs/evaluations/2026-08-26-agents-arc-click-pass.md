# Click-pass — the agents arc (083d25d · 00e30fe · 764c3ec)

**Driven** 2026-08-26 in Chrome against production (`www.yarnnn.com`), principal
`kvkthecreator@yarnnn.com` (rig workspace `bf5b25a9`). Hat-B.

**Verdict: PASS.** 12 checks driven, 12 observed correct, 0 console errors,
0 failing network requests. Two pre-existing defects observed and unchanged
(neither introduced by this arc). One item remains UNDRIVEN by design.

---

## Why this workspace was the right rig

Its persisted Dock (`localStorage` `shell:kept-surfaces`) reads:

```
["chat","text","studio","radar","strings","files","agents"]
```

**`studio` and `radar` are deleted slugs.** This is a genuinely CURATED Dock —
the exact case ADR-592 D-rationale names as the one a `DEFAULT_KEPT_SURFACES`
edit cannot reach (the reseed fires only on byte-equality, which is why
ADR-574's Docs pause never landed). So the roster-exclusion claim was tested
against real drifted state, not a fresh profile.

---

## What was driven

### A. `internal` leaves the roster (ADR-592, commit 764c3ec)

| # | Check | Observed |
|---|---|---|
| A1 | Dock renders the derived pinned set | `Chat · Text · Slides · Strings · Files · Agents` — exactly `is_default_pinned()` |
| A2 | Deleted slugs in persisted state render nothing | `studio` + `radar` present in `kept-surfaces`, **zero ghost icons** |
| A3 | Launcher at-rest omits internal apps | 8 rows; no Sources, no Freddie System Agent |
| A4 | **Flat search does not leak an internal app** | `sources` `system` `freddie` `radar` `docs` → **0 surface rows titled as such** |
| A5 | A4's one hit is a summary match, not a leak | "sources"/"system" match *Workspace Settings* on its summary prose (`…hid Sources`). No row **titled** Sources or Freddie. |

⭐ A4 is the assertion that matters: before this commit, `hidden: true` was the
ONLY thing keeping these two out of flat search, and it was honoured by a single
frontend filter the API never read. They are now absent because the server never
serves them.

### B. The `internal` obligation (redirect stub + auth gate)

| # | Check | Observed |
|---|---|---|
| B1 | `/system-agent` redirects, does not render | → `/workspace-settings` |
| B2 | `/sources` redirects, does not render | → `/chat` |
| B3 | Logged-OUT, 8 stub routes bounce to login | all `307 → /auth/login?next=…` |

B3 covered `/system-agent /sources /budget /mandate /program /autonomy /radar
/docs`. **Five of those were ungated before 083d25d** — this is the fix
observed live, and confirms `internal` did not strip protection from the two
rows that left the roster.

### C. The agents surface (083d25d · 00e30fe)

| # | Check | Observed |
|---|---|---|
| C1 | `/agents` renders the beings | Editor (slides, text) · Supervisor (strings) · Keeper (strings) |
| C2 | Designer correctly withheld | absent — Images is `search-only`, so `is_promoted` is False |
| C3 | Being detail is read-only and says so | "Works in strings · Runs on `anthropic/claude-sonnet-5` · **Comes with yarnnn — this one can't be changed**" |

C3 is `assert_editable`'s posture surfaced honestly at the surface, before any
edit door exists.

### D. Surfaces whose API shape changed (00e30fe)

| # | Check | Observed |
|---|---|---|
| D1 | Danger Zone renders after the field swap | "Delete **0 dated output files and per-run logs**" — the new `work_history_files` |
| D2 | **The re-gated button tracks reality** | "Clear History" disabled at count 0; "Clear Workspace" ENABLED at 29 files |
| D3 | Connectors pane clean after field removal | renders; no agent count anywhere; `/api/integrations/summary` **200** |

⭐ D2 is the defect this arc found: the button was gated on `agent_runs === 0`,
permanently true, so it was **permanently disabled while L1 still deleted real
output folders**. It is now gated on what L1 actually clears. Observed disabled
here for the honest reason (this workspace has no report outputs), not the
structural one.

⭐ D1/D3 also establish that the deploy is STABLE AHEAD OF migration 248 — the
code no longer reads the dropped tables, and nothing 500s while they still
exist.

---

## Health

- **Console:** 0 errors, 0 warnings from app code across the whole run. (One
  bare 404 in the log is this pass's own probe of a non-existent proxy path.)
- **Network:** 31 XHR/fetch, all 200 — including `/api/integrations/summary`
  and `/api/lanes?include_bound=1`, the two whose response shape changed. The
  single 404 is `GET /api/workspace/file?path=/workspace/persona/IDENTITY.md`,
  a missing file on this rig, pre-existing and unrelated.

## Observed, NOT introduced here (carry forward)

1. **Supervisor renders the fallback `Bot` glyph.** Its registry `icon` is
   `clipboard-list`; the FE `ICONS` map in `AgentsSurface.tsx` holds only
   `pen-tool` / `palette` / `archive`. It therefore wears the same glyph as the
   "Nobody yet" empty state. Cosmetic; reported in the audit, not yet fixed.
2. **`homes` renders raw slugs** ("in slides, text") though the app registry
   already carries display titles.

## NOT driven, deliberately

- **`/admin`** — this rig principal is not on `ADMIN_ALLOWED_EMAILS`, so it
  correctly redirects to `/desktop`. The admin field removals are covered by
  `tsc --noEmit` + `next build` + the API gates instead. Driving them needs an
  allowlisted principal.
- **Migration 248** — written, NOT run (no DB URL this session). D1/D3 show the
  code is already correct for the post-drop schema; the migration makes the
  schema agree.
