# Claude Operator Access — How Claude Acts on Behalf of KVK

> **Status**: Canonical. Covers how any Claude session (Code, Cowork,
> future MCP integrations, etc.) acts on behalf of KVK for the Alpha-1
> personas without repeated auth rederivation.
> **Scope**: Alpha-1 (both personas, alpha-trader + alpha-commerce).
> Extensible to future alpha phases and additional personas.
> **Related**: [OPERATOR-HARNESS.md](./OPERATOR-HARNESS.md) (machinery),
> [ALPHA-1-PLAYBOOK.md](./ALPHA-1-PLAYBOOK.md) (rules of engagement),
> [personas.yaml](./personas.yaml) (persona registry).

---

## Purpose

When KVK writes "Claude, go do X on the alpha-trader account," that
sentence needs to mean something concrete. This doc makes it concrete.

Three things get pinned here:

1. **Which access mode is in use** for the current Claude session
2. **How auth is established** in that mode (no reinventing per session)
3. **What Claude can and cannot do** once authenticated

A fourth section covers **future connection considerations** — MCP,
browser automation, additional personas — so this doc stays relevant
as the set of ways-Claude-connects grows.

---

## Three access modes

Claude can act on the alpha accounts in three distinct ways. Every
session is in one of these modes.

### Mode 1 — Headless Operator (direct API, no browser)

**When:** Claude Code session (this session) + any future MCP-based
session where Claude speaks to YARNNN's prod API directly.

**What Claude has:**
- `SUPABASE_SERVICE_KEY` in env (from `docs/database/ACCESS.md`)
- Harness scripts in `api/scripts/alpha_ops/` (mint_jwt, connect,
  verify, reset)
- Direct Postgres read via `.venv/bin/python` + `psycopg2`
- Direct prod HTTP API call via `ProdClient` in `_shared.py`

**What Claude does not have:**
- A web browser
- A rendered cockpit surface
- The ability to click a ProposalCard or navigate `/overview`

**Auth pattern:**
```bash
# Mint a persona JWT (1-hour lifetime)
export JWT=$(.venv/bin/python api/scripts/alpha_ops/mint_jwt.py alpha-trader)

# Hit any authenticated endpoint
curl -s -H "Authorization: Bearer $JWT" \
  https://yarnnn-api.onrender.com/api/tasks | jq
```

No password flow, no browser session, no OAuth handoff. The
service-key-minted JWT is valid for an hour; re-mint if a 401 surfaces.

**Canonical session-start ritual for Mode 1:**
```bash
cd /Users/macbook/yarnnn
.venv/bin/python api/scripts/alpha_ops/verify.py --all
```

If green, proceed. If red, investigate before any operator action.

### Mode 2 — Cockpit Operator (authenticated web session)

**When:** Claude Cowork (Chrome-extension Claude) + future Playwright
or browser-automation-equipped Claude sessions. Not this Code session.

**What Claude has:**
- Actual browser (Chrome via Cowork, or headless via Playwright)
- Ability to log in with persona credentials from 1Password
- Rendered cockpit surfaces — can see `/overview`, click
  ProposalCards, read Review chronicle, inspect Context files via the
  UI

**What Claude does not have (vs Mode 1):**
- Service-key DB reads (web session can only see what the UI exposes)
- Direct API call bypass — must go through the UI unless augmented

**Auth pattern:**
1. KVK pulls persona credentials from 1Password
2. KVK either (a) starts the browser session and logs in, then hands
   Claude Cowork the ready tab, or (b) pastes credentials to Cowork
   and instructs "log in as alpha-trader"
3. Cookie-based session lasts per the web app's session policy

**When Mode 2 is best:**
- Testing cockpit UX friction (the point of Alpha-1 observation)
- Exercising flows that only make sense visually (empty states,
  layout, rail-expansion behavior)
- Interacting with things that don't have API endpoints yet

**When Mode 2 is overkill:**
- Verifying invariants (Mode 1's `verify.py` is faster + more exact)
- Programmatic platform-connect (Mode 1's `connect.py` is idempotent)
- Destructive ops (Mode 1's `reset.py --confirm` has a gate; the UI
  doesn't)

### Mode 3 — Conversational Partner (no session at all)

**When:** Any session where Claude does not have an authenticated
path to the account. Fallback mode.

**What Claude has:**
- Access to this repo (docs, ADRs, harness code, playbook)
- Ability to reason, draft, propose
- Ability to write observation notes + ADR drafts

**What Claude does not have:**
- Anything authenticated to the alpha accounts

**Pattern:**
- KVK is in the cockpit (or on the platform), observes state, narrates
  to Claude: "AAPL bracket proposal just fired, expectancy 0.9R, Signal 1"
- Claude reasons against declared signals, `_performance.md` context
  from the observation, risk parameters from the playbook
- Claude recommends: approve / escalate / reject + reasoning
- **KVK executes** — Claude cannot

**When Mode 3 is right:**
- KVK wants a second opinion before an irreversible action (always
  escalated to KVK per the anti-discretion ladder anyway)
- Policy edits to `_risk.md` / `principles.md` / `_operator_profile.md`
  — these require persona-identity changes which are never Claude's
  unilateral decision
- Long-form architecture conversations that would happen here in
  Code anyway

---

## Mode-to-discretion mapping

Each mode has a different autonomy ceiling. The playbook's anti-discretion
ladder (§6) is the same rule set; what changes is whether Claude has the
path to act on it at all.

| Action | Mode 1 (headless) | Mode 2 (cockpit) | Mode 3 (conversational) |
|---|---|---|---|
| Read any substrate file | ✅ via service key or JWT | ✅ via Context browser in UI | KVK describes; Claude reasons |
| Read `decisions.md`, `_performance.md` | ✅ | ✅ | KVK describes |
| Run `verify.py --all` | ✅ — this is Mode 1's superpower | ❌ not the right tool; use the UI or Mode 1 | ❌ KVK runs; Claude interprets output |
| Approve reversible proposal meeting all five conditions | ✅ via `/api/proposals/{id}/approve` | ✅ via Queue card | ❌ KVK clicks; Claude advises |
| Reject any proposal | ✅ same via API | ✅ via Queue | ❌ KVK clicks |
| Approve irreversible proposal | ❌ always escalates regardless of mode | ❌ always escalates | ❌ always KVK |
| Trigger task manually | ✅ via `/api/tasks/{slug}/run` | ✅ via Work detail | ❌ KVK triggers |
| Edit `_risk.md`, `principles.md`, `_operator_profile.md`, IDENTITY.md | ❌ never Claude unilaterally | ❌ never Claude unilaterally | ❌ never Claude unilaterally |
| Dissolve / archive / pause agent | ❌ escalate | ❌ escalate | ❌ escalate |
| Write observation note to `docs/alpha/observations/` | ✅ (this is a repo commit) | ✅ (same — repo commit, any mode) | ✅ |
| Connect platform (Alpaca / LS / future) | ✅ via `connect.py` | ✅ via Integrations UI | ❌ KVK initiates |
| Reset persona | ✅ via `reset.py --confirm` | ⚠️ no UI equivalent; use Mode 1 | ❌ KVK via Mode 1 |

**Rule of thumb:** the discretion ladder in the playbook §6 is the *ceiling*
(what Claude is *allowed* to do). The mode determines the *floor* (what
Claude *can physically* do). Neither overrides the other — action requires
both.

---

## Auth details per mode (cheat sheet)

### Mode 1 auth requirements

- `SUPABASE_SERVICE_KEY` env var set (source: `docs/database/ACCESS.md`,
  stored in shell env or `api/.env`)
- Python deps: `psycopg2-binary`, `pyyaml`, `python-dotenv`, `httpx`
  (in `.venv`; install with
  `.venv/bin/pip install psycopg2-binary pyyaml python-dotenv httpx`
  if a fresh venv)
- For `connect.py` only: persona platform creds as env vars per
  `personas.yaml` `credentials_env` block (values from 1Password)

### Mode 2 auth requirements

- 1Password access to shared vault `YARNNN Alpha-1`:
  - `alpha-trader.yarnnn-login` (email + password)
  - `alpha-commerce.yarnnn-login` (email + password)
- Browser with working cookies (Cowork provides this; Playwright
  provides this with more control)
- YARNNN web app URL (`app.yarnnn.com` or wherever prod lives)

### Mode 3 auth requirements

None. This is "Claude reading the repo + this conversation" and nothing
more.

---

## Future connection considerations

The alpha will outgrow the three modes above. This section names the
extensions we expect, so when they ship, they slot in cleanly.

### MCP as a fourth path

**Status:** existing infrastructure, not yet used for alpha operation.

YARNNN has an MCP server (ADR-075 + ADR-169) at
`https://yarnnn-mcp-server.onrender.com` that exposes three intent-shaped
tools (`work_on_this`, `pull_context`, `remember_this`) over
`QueryKnowledge` + `UpdateContext` primitives. MCP is a cross-LLM
consumption + contribution path — foreign LLMs (Claude.ai, ChatGPT,
Gemini) reach YARNNN substrate through it.

**What this could enable for alpha:** Claude in ChatGPT or Claude.ai
could consult the alpha personas' context mid-conversation. For example,
a strategy discussion with KVK elsewhere could pull `_performance.md`
attribution via `pull_context` to ground the discussion in real
money-truth.

**What blocks it today:** alpha accounts would need to enable MCP
authentication (OAuth 2.1 flow per ADR-075), and the MCP tool surface
is consultation-shaped not operator-shaped — no approve/reject
primitives via MCP per ADR-168 boundaries. MCP is for context-pulling,
not cockpit-operating.

**When this becomes relevant:** post-alpha-2, when we want external
LLM sessions (Claude.ai desktop, ChatGPT) to reason over the alpha
substrate without re-narrating everything. Likely Alpha-3 territory.

### Browser automation (Playwright-equipped Claude)

**Status:** not in scope for Alpha-1. Plausible for Alpha-1.5+.

A Playwright-equipped Claude Code session would be functionally Mode
2 without the Cowork dependency — more controllable, scriptable,
repeatable. It would unlock autonomous cockpit operation (log in,
navigate to Queue, inspect proposal, click approve) within this Code
session rather than delegating to Cowork.

**When this becomes relevant:** if observation shows Mode 2 operations
are frequent enough that Cowork dependency becomes a friction — at
that point, worth bringing Playwright-equipped Claude into the loop.

### Additional personas

**Status:** future. Alpha-1 ships with two personas. Alpha-1.5
(if scoped) or Alpha-3 (external operators) may add more.

**How to add:** append to `personas.yaml`. Harness scripts pick up
new entries by slug. No code changes. See
[OPERATOR-HARNESS.md](./OPERATOR-HARNESS.md) "When the harness needs
extending."

### Per-persona JWT cache

**Status:** not built. Noted for if Mode 1 usage increases.

`mint_jwt.py` is invoked each time a JWT is needed; JWTs are 1-hour.
If a session makes many calls, caching JWTs (keyed by persona + expiry)
would be a small efficiency win. Trivial to add; not built because
current usage doesn't warrant it.

### Impersonation chrome for operator switching

**Status:** scaffolded per ADR-194 v2 Phase 2b (`can_impersonate` flag
+ workspace persona column) but no admin UI yet.

Future: an admin with `can_impersonate=true` could log into any
persona workspace through a persona switcher and operate it with
appropriate audit tagging. At that point, Mode 2 becomes: "KVK logs
into one account, switches to any persona via chrome, operates." No
separate logins per persona.

**When this becomes relevant:** once the total persona count grows
past ~3-4 accounts — juggling separate logins becomes friction-worthy.

---

## Operational rules of thumb

### "What mode am I in right now?"

- If you're reading this in Claude Code (VSCode extension or CLI) → **Mode 1**
- If you're in Claude Cowork (Chrome extension) → **Mode 2**
- If you're in Claude.ai or ChatGPT without MCP → **Mode 3**
- If you're a future Claude with Playwright → **Mode 2 upgraded**
- If MCP is connected for alpha → **Mode 1 with consultation scope**

### "KVK just said 'go do X on alpha-trader.' What do I do?"

1. Classify `X`: action type (read / write / approve / edit-identity /
   destroy), reversibility, required mode
2. If X is an edit to identity files (`IDENTITY.md`, `_risk.md`,
   `principles.md`, `_operator_profile.md`) → **never; propose edit
   to KVK, wait for ratification**
3. If X is irreversible → **never; escalate to KVK with full context**
4. If X is reversible and within current mode's capability → **act,
   log action to observation note**
5. If X is reversible but requires a mode Claude doesn't have right
   now → **explain which mode is needed; offer Mode 3 reasoning in
   the interim**

### "I'm about to act autonomously. Quick gate check."

Before every autonomous action, Claude verifies in order:

1. **Mode capability** — can I actually do this in my current mode?
2. **Discretion ladder** — does this pass playbook §6 five-condition
   test?
3. **Audit trail** — will this action be legibly attributed in
   `decisions.md` / `activity_log` / observation notes?
4. **Reversibility** — is this reversible or irreversible per ADR-193
   classification?

If all four checks pass → act. If any fails → escalate or explain to
KVK why Claude is waiting.

---

## When this doc needs updating

- **New access mode** (Playwright, MCP-for-operation, etc.) → add to
  §Three-access-modes, update the mode-to-discretion table, add an
  auth-requirements entry
- **New persona** → `personas.yaml` auto-propagates; this doc only
  changes if the new persona has a structurally different access
  pattern (e.g., Shopify OAuth vs API key)
- **Playbook §6 discretion ladder changes** → reflect here in the
  mode-to-discretion table
- **Future connection considerations section** should stay append-only
  — delete nothing; mark entries as implemented, in-progress, or
  deferred

---

## One-sentence summary for any future session

> Claude has three access modes to the alpha personas (headless via
> harness, cockpit via browser, conversational via no auth). Today
> Code sessions run in Mode 1; the harness at
> `api/scripts/alpha_ops/` is how Mode 1 authenticates. Mode 2 requires
> browser (Cowork / Playwright). Mode 3 is the fallback when no auth
> path exists. Discretion ceiling is [ALPHA-1-PLAYBOOK.md §6](./ALPHA-1-PLAYBOOK.md#6-claudes-rules-of-engagement);
> mode determines the floor.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-21 | v1 — Initial. Three access modes (Headless / Cockpit / Conversational) with per-mode auth, capability, and discretion mapping. Future connection section covers MCP, Playwright, additional personas, JWT caching, impersonation chrome. Explicit rules of thumb for "what mode am I in" + "about-to-act gate check." |
