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
- **Migration 248** — ✅ APPLIED later the same day (`26972aa`). See the
  addendum below.

---

# Addendum — migration 248 applied, and the 500 it exposed

**Applied** 2026-08-26 via `scripts/db/run-migration.sh`. Verified independently
after: 0 of 8 relations · 0 of 9 FK columns · 0 of 6 functions remain; the three
live tables untouched (action_proposals 125 · chat_sessions 122 ·
execution_events 571 — unchanged).

## ⚠️ It caused a real production 500, and green gates did not see it

`GET /api/feed/history` returned 500: the DEPLOYED handler filtered
`chat_sessions` on `.is_("agent_id","null")` — the column just dropped. The
repair was written in my working tree and simply **not staged**.

Everything I had checked passed *while production was 500ing*:
- gates read source text and never execute a query,
- an API boot resolves routes and never calls a handler.

**Blast radius was established by driving, not assumed**: `/api/lanes` and the
lane transcript returned 200 and chat rendered, because the ADR-411 lane path
does not use that endpoint. Only that one endpoint was affected.

Fixed, deployed (`dep-da775q67bikc73fi3krg`, live 05:02Z) and re-driven:
`/api/feed/history` **200**, chat transcript renders, Danger Zone unchanged
("Delete 0 dated output files…" / 29 workspace files).

## What --dry-run caught before any of that

Three defects the audit had missed, none visible to a row count or code grep:
`agent_role_metrics` is a **VIEW** not a table (`DROP TABLE` on a view errors);
**three more tables** carry agent FK columns (the audit's `pg_depend` query
walked views, not constraints); and **six SQL functions** that cannot drop
together — a row-type function must precede its table, a trigger function must
follow it.

The file also carried its own `BEGIN`/`COMMIT` and was correctly **refused** by
the runner. After the dry run I re-queried to prove the rollback: the trailing
`WARNING: there is no transaction in progress` is expected `DO`-block noise but
is also the signature of a rollback that did nothing.
