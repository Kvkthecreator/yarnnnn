# Alpha-1 Operator Harness

> **Status**: Canonical. Both KVK and Claude use this harness identically.
> **Rule**: If you find yourself hand-rolling JWT minting, hand-writing
> verification SQL, or copy-pasting credentials into ad-hoc scripts for
> Alpha-1 personas — stop and use the harness instead. If the harness
> doesn't do what you need, extend the harness.
> **See also**: [CLAUDE-OPERATOR-ACCESS.md](./CLAUDE-OPERATOR-ACCESS.md)
> for the access model (which session uses which mode, what Claude can
> and can't do, how future connection paths fit in). This harness is
> the machinery for Mode 1 (headless). Mode 2 (cockpit) + Mode 3
> (conversational) are covered there.

This is the operator entry point for Alpha-1. It turns the per-session
rituals we used to bootstrap the two personas into a small set of
commands, so neither KVK nor Claude has to re-derive auth, persona
identifiers, payload shapes, or verification invariants each time.

## What's in the harness

| File | Purpose |
|---|---|
| `docs/alpha/personas.yaml` | Persona registry. No secrets. Single source of truth for slug → email → user_id → workspace_id → expected invariants. |
| `api/scripts/alpha_ops/_shared.py` | Helpers: registry loader, JWT minter (Supabase admin OTP flow), prod API client with auth injected. |
| `api/scripts/alpha_ops/mint_jwt.py` | Prints a fresh 1-hour JWT for a persona. Pipeable. |
| `api/scripts/alpha_ops/connect.py` | Calls the prod `/integrations/{trading,commerce}/connect` endpoint, reading creds from env vars. |
| `api/scripts/alpha_ops/verify.py` | Read-only invariant check against the persona's expected shape in `personas.yaml`. |
| `api/scripts/alpha_ops/reset.py` | Calls prod `DELETE /account/reset`. Requires `--confirm`. Destructive. |

## Where secrets live

Nothing secret is committed. The harness assumes two things exist outside
the repo:

1. **Supabase service key** (admin DB access, JWT minting):
   - Source: `docs/database/ACCESS.md`
   - Env var: `SUPABASE_SERVICE_KEY`
   - KVK keeps the value; Claude reads from env per session.

2. **Persona external creds** (Alpaca paper API keys per persona):
   - Source: `api/.env.alpha-ops` — gitignored file at the repo root.
     The canonical home for alpha persona credentials.
   - Env var names are defined in `docs/alpha/personas.yaml` under each
     persona's `credentials_env` block:
     - `kvk` → `KVK_ALPACA_KEY` + `KVK_ALPACA_SECRET`
     - `alpha-trader` → `ALPHA_TRADER_ALPACA_KEY` + `ALPHA_TRADER_ALPACA_SECRET`
     - `alpha-trader-2` → `ALPHA_TRADER_2_ALPACA_KEY` + `ALPHA_TRADER_2_ALPACA_SECRET`

3. **Production `INTEGRATION_ENCRYPTION_KEY`** (Fernet key that encrypts
   creds in `platform_connections`):
   - Source: Render env on `yarnnn-api` + `yarnnn-unified-scheduler`.
   - Neither KVK nor Claude reads this directly. The connect scripts POST
     plaintext creds to prod over TLS; Render encrypts them there. The
     blast radius of a leaked service key stays at "can read DB rows" —
     it doesn't extend to "can decrypt every persona's Alpaca account."

### `api/.env.alpha-ops` shape

```bash
# Supabase service key (read SUPABASE_SERVICE_KEY value from docs/database/ACCESS.md)
SUPABASE_SERVICE_KEY=...

# Per-persona Alpaca paper creds (only present for personas you operate)
KVK_ALPACA_KEY=PK...
KVK_ALPACA_SECRET=...

ALPHA_TRADER_ALPACA_KEY=PK...
ALPHA_TRADER_ALPACA_SECRET=...

ALPHA_TRADER_2_ALPACA_KEY=PK...
ALPHA_TRADER_2_ALPACA_SECRET=...
```

The file is gitignored via an explicit entry in `.gitignore`
(`api/.env.alpha-ops`). Don't rename it, don't move it — `.gitignore`
matches this exact path, and any deviation risks accidental commit.

### Session-start ritual (KVK or Claude)

```bash
cd /Users/macbook/yarnnn

# Source the alpha-ops env file for any session that runs connect.py or
# verify.py --cost (which needs SUPABASE_SERVICE_KEY). verify.py without
# --cost is read-only over the prod API and doesn't need the secret key.
set -a; source api/.env.alpha-ops; set +a

# Sanity check the persona registry + workspace shape
.venv/bin/python -m api.scripts.alpha_ops.verify --all
```

Source the env file only when you need it. Don't `source` it during
day-to-day API development — you don't want persona creds sitting in
random Python shells longer than the operator-task that needs them.

## Commands

All commands are run from the repo root. The scripts add their own
directory to `sys.path` so direct invocation (`python scripts/alpha_ops/X.py`)
works without needing to mark `api/` as a package.

### Verify both personas are healthy

```bash
python api/scripts/alpha_ops/verify.py --all
python api/scripts/alpha_ops/verify.py --all --cost              # + cost-truth rollup
python api/scripts/alpha_ops/verify.py alpha-trader-2 --cost --cost-days 30
```

Read-only. No JWT required (uses the service key). Prints pass/fail per
invariant per persona. Non-zero exit if anything is off.

`--cost` appends a per-workspace LLM cost rollup over the window
(default 7 days, override with `--cost-days N`): window total + daily
breakdown + per-recurrence breakdown. This is the surface for SCOPE.md
success-contract dimension 2 (cost-truth). The contract evaluation at
end of paper-discipline phase compares money-truth (`_money_truth.md`
cumulative net P&L) vs. `--cost --cost-days 90 total`.

Run this:

- At the start of any alpha session, as a sanity check
- Before and after every ADR-affecting change to `workspace_init.py`,
  `orchestration.py`, `recurrence.py` (post-ADR-231 successor to the
  deleted `task_types.py`), `directory_registry.py`, `integrations.py`
  (the files whose behavior determines what a cold-start workspace
  looks like)

**Scope note (Objective A only):** `verify.py` validates **system-level
shape** — agent count, bot activations, scaffolded recurrences (post-ADR-231:
the `essential` task flag was dropped by migration 164; recurrence presence
is verified by walking the recurrence-declaration substrate or querying the
thin `tasks` scheduling-index), platform connections, core files,
context-domain presence. It is Objective-A tooling per
[DUAL-OBJECTIVE-DISCIPLINE.md](./DUAL-OBJECTIVE-DISCIPLINE.md).

It does **NOT** validate Objective-B (money-truth / per-signal
performance / Reviewer calibration against outcomes). A green
`verify.py --all` means "the workspace is structurally healthy"; it
does NOT mean "the book is growing" or "signals are producing edge."

For Objective-B reads, use direct `_money_truth.md` inspection via
Mode 1 (service-key Postgres read against `workspace_files`) or Mode 2
(Context browser in the cockpit). A dedicated Objective-B harness tool
(`perf.py` or similar) is a known gap — will be built when weekly B
reports surface a repeated read-pattern worth scripting.

### Mint a fresh JWT

```bash
export JWT=$(python api/scripts/alpha_ops/mint_jwt.py alpha-trader)
curl -s -H "Authorization: Bearer $JWT" \
  https://yarnnn-api.onrender.com/api/memory/user/onboarding-state | jq
```

JWTs last ~1 hour. Mint a new one if you get a 401.

### Connect platform creds

```bash
# Source the alpha-ops env file first (provides the api_key + api_secret
# env vars named in personas.yaml::credentials_env).
set -a; source api/.env.alpha-ops; set +a

python -m api.scripts.alpha_ops.connect kvk
python -m api.scripts.alpha_ops.connect alpha-trader
python -m api.scripts.alpha_ops.connect alpha-trader-2
```

Idempotent — the prod connect endpoints upsert. Safe to re-run to rotate
a key. If the env vars are missing the script fails fast with a pointer
back to `.env.alpha-ops`.

### Reset a persona to cold-start

```bash
# Destroys agents, tasks, workspace_files, platform_connections, chat history.
# Then synchronously rescaffolds: 1 agent (YARNNN per ADR-205) + workspace
# skeletons + bundle fork if the prior MANDATE.md carried a program marker
# (ADR-244 D4 — active_program_slug preserved across L4 reset).
python api/scripts/alpha_ops/reset.py alpha-trader --confirm
python api/scripts/alpha_ops/connect.py alpha-trader        # re-attach Alpaca
python api/scripts/alpha_ops/verify.py  alpha-trader        # confirm invariants
```

### Activate a persona's program (post-reset, or first-time)

L4 reset only re-forks the bundle when the **pre-purge** MANDATE.md carried the program marker (`# Mandate — <slug> (template)`). If the marker is absent (operator overwrote it, never activated, or the workspace was created before bundle activation existed), L4 falls back to kernel-default skeletons. In that case, run the canonical activation harness per [ADR-230](../adr/ADR-230-persona-program-registry-unification.md):

```bash
# Forks docs/programs/{program}/reference-workspace/ into the persona's
# /workspace/, applies persona-specific overrides at
# docs/alpha/personas/{slug}/overrides/ (if any), pre-creates specialist
# agent rows, optionally connects platform creds.
# Idempotent — re-running preserves operator-customized content.
python -m api.scripts.alpha_ops.activate_persona --persona alpha-trader-2
# Or --dry-run to preview without writing:
python -m api.scripts.alpha_ops.activate_persona --persona alpha-trader-2 --dry-run
# Or --skip-connect if creds aren't handy:
python -m api.scripts.alpha_ops.activate_persona --persona alpha-trader-2 --skip-connect
```

Per the 2026-05-11 fix in [ADR-226 amendment](../adr/ADR-226-reference-workspace-activation-flow.md#status), the fork primitive now calls `materialize_scheduling_index` inline — the `tasks` scheduling index is populated immediately and `verify.py` sees the recurrences without a scheduler-tick wait.

**End-to-end persona cold-bootstrap** (when L4 reset's auto-refork doesn't fire — e.g. operator's MANDATE.md was kernel-default pre-reset):

```bash
python -m api.scripts.alpha_ops.reset alpha-trader-2 --confirm
python -m api.scripts.alpha_ops.activate_persona --persona alpha-trader-2 --skip-connect
python -m api.scripts.alpha_ops.connect alpha-trader-2
python -m api.scripts.alpha_ops.verify  alpha-trader-2
```

## Shared-access discipline (KVK ↔ Claude)

The whole point of this harness is that **either operator** (KVK or Claude)
can run the same commands and get identical results. Concretely:

- **Persona identity is registry-backed.** Claude doesn't need to remember
  what `seulkim88@gmail.com`'s user_id is, and neither does KVK — the
  yaml is the canonical answer.
- **Auth is scripted.** Nobody mints a JWT by hand. Nobody writes the
  magic-link OTP flow inline anymore. It happens via `mint_jwt.py`.
- **Verification is declarative.** The expected shape of a healthy
  persona is data in `personas.yaml`, not prose in a session transcript.
  When the expected shape changes (e.g. the bundle adds a new
  recurrence to `_recurrences.yaml`), update `scaffolded_recurrences`
  in the yaml — don't update prose.
- **Destruction requires intent.** `reset.py` refuses without `--confirm`.
  `purge_user_data.py` (older, lower-level) stays in place for the rare
  case where we need surgical deletion below the `/account/reset`
  endpoint.

## Steered session pattern

The harness commands above are the *machinery*. This section names the
*discipline* of using them in a closed-loop steered session — where
KVK directs the work top-down and Claude operates the harness while
narrating each consequential action so KVK can intervene, redirect,
or rewind.

This pattern is distinct from the bottom-up rituals of the
[alpha-operator subagent](../../.claude/agents/alpha-operator.md) (daily
sanity check, EOD scan, weekly report). Subagent rituals are *recurring
work the system needs done regardless of intent*. Steered sessions are
*top-down investigations of a stated objective*. Both use the same
harness; they differ in driver.

Three commitments make a session "steered":

### S1 — Stated objective at the top

Every steered session opens with one written sentence: "this session
confirms / measures / discriminates X." If the objective can't fit in
one sentence, the session is two sessions — split it. The stated
objective becomes the title of the iteration's observation seed (see
S3).

### S2 — Narrate-before-act on consequential actions

Before any state-mutating or judgment-affecting action — `reset.py`,
`connect.py`, firing an `external_action` recurrence, posting an
addressed feed turn on the persona's behalf — Claude emits a one-line
narration in the chat with:

- **What** I'm about to do (the command or the verb)
- **Why** it serves the stated objective
- **Expected observable** (what KVK should see change)
- **Rollback** (what undoes this if needed)

This is the steering interface. KVK reads, redirects if wrong, or lets
it run. Post-hoc narration is too late — the steering wheel has to be
*ahead* of the wheels.

Read-only actions (verify.py, judgment_log.md reads, token_usage queries)
don't need pre-narration; their cost of error is zero. Authority axiom
applies: standing authority over what's possible per the mode-1 matrix
does NOT collapse with invocation authorization for a specific turn.
See [CLAUDE-OPERATOR-ACCESS.md §"Architectural authority vs invocation
authorization"](./CLAUDE-OPERATOR-ACCESS.md#architectural-authority-vs-invocation-authorization-the-axiom).

### S3 — Three-layer observation captured to an observation file

A steered session produces an observation file at
`docs/alpha/observations/{YYYY-MM-DD}-iter{N}-{slug}-{persona}.md`
seeded at the start of the session with the stated objective + procedure
+ expected observable per layer, then filled in during/after the run.

The three layers — *code* (yarnnn correctness), *system* (yarnnn-as-used),
*outcomes* (paper Alpaca P&L when applicable) — are the axes of the
DUAL-OBJECTIVE three-axis schema applied to a single iteration's narrow
objective. Each invariant the iteration tests gets observed at each
layer where it touches.

Two failure modes the observation-file seed prevents:

- **Drift to whatever was easiest to look at.** Naming expected
  observable per layer up-front means "we didn't look at the outcome
  layer" becomes a visible gap, not a silent omission.
- **Forgotten objective.** Re-reading the seed at the end of the
  session catches "we ended up debugging a side-quest instead of
  confirming the stated objective" before the observation gets
  written up as if the objective was met.

### When the steered-session pattern is overkill

- Subagent rituals (already bottom-up + scripted)
- Code-only work that doesn't touch live persona state
- Ad-hoc grep / read / explore against the repo

When in doubt: if the session ends with a `--confirm` flag pressed or
a feed message posted as the persona, it should have been steered. If
not, the pattern is overkill.

### Cross-references

- [DUAL-OBJECTIVE-DISCIPLINE.md](./DUAL-OBJECTIVE-DISCIPLINE.md) — three-axis schema the per-layer observation grid extends from; §"Named failure classes" for the canonical "no trades" four-way disambiguation
- [CLAUDE-OPERATOR-ACCESS.md](./CLAUDE-OPERATOR-ACCESS.md) — authority/authorization axiom that governs narrate-before-act
- [.claude/agents/alpha-operator.md](../../.claude/agents/alpha-operator.md) — the bottom-up sibling of this pattern

## Known drifts (documented, not fixed)

1. **`_risk.md` path lacks leading slash.** `api/services/risk_gate.py:48`
   defines `RISK_MD_PATH = "workspace/context/trading/_risk.md"`. Every
   other workspace path uses a leading `/`. The file on disk matches the
   constant so nothing is broken — but this is inconsistent with ADR-119
   path conventions. Flagged in `personas.yaml` for `alpha-trader`. Fix
   is a separate concern.

2. **`connect_commerce` asymmetry (low-priority).** Per SCOPE.md alpha-commerce is `deferred`; this drift is no longer alpha-blocking. Will need verification when alpha-commerce graduates from `deferred` (currently a `deferred` bundle at `docs/programs/alpha-commerce/`).

## When the harness needs extending

- New persona → add entry to `personas.yaml`, done. Scripts pick it up.
- New invariant → add to `expected:` in the persona's yaml; `verify.py`
  grows a check if the shape is new.
- New prod endpoint alpha ops need to hit → add a thin method to
  `ProdClient` in `_shared.py`, don't inline the URL in a one-off script.
- New platform (e.g. Shopify for Alpha-2) → `personas.yaml` gains a
  `shopify` platform kind; `connect.py`'s `_build_payload` grows a branch;
  `verify.py` picks up the new expected shape automatically.

## Pointer into the playbook

This harness is the operational machinery behind
[ALPHA-1-PLAYBOOK.md §4 Setup Sequence](./ALPHA-1-PLAYBOOK.md#4-setup-sequence)
and §6 "Rules of engagement". If you're reading the playbook and find a
gap between "KVK does X manually" and "Claude does X with credentials"
that the harness could automate — that's a harness-extension signal.

## Revision history

| Date | Change |
|------|--------|
| 2026-05-13 | Added §"Steered session pattern" between "Shared-access discipline" and "Known drifts". Names the top-down counterpart to the bottom-up alpha-operator subagent rituals: stated objective at the top (S1), narrate-before-act on consequential actions (S2), three-layer observation captured to an observation file (S3). The pattern uses the same harness machinery; what differs is the driver (KVK directs top-down vs. system needs done bottom-up). Triggered by KVK's 2026-05-13 request to operate iteratively across code / system-as-used / outcome layers under explicit steering, after the Reviewer dispatcher trilogy made E2E aliveness from cold-start the load-bearing next observation. First iteration of the pattern: [observations/2026-05-13-iter1-e2e-aliveness-kvk.md](./observations/2026-05-13-iter1-e2e-aliveness-kvk.md). |
