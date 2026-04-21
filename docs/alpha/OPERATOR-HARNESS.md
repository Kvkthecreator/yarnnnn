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

Nothing secret is committed. The harness assumes three things exist outside
the repo:

1. **Supabase service key** (admin DB access, JWT minting):
   - Source: `docs/database/ACCESS.md`
   - Env var: `SUPABASE_SERVICE_KEY`
   - Shared by: KVK (password manager) + Claude (reads from env per session)

2. **Persona external creds** (Alpaca paper keys, LemonSqueezy API key):
   - Source: 1Password vault `YARNNN Alpha-1` (entries named in `personas.yaml` `vault_entry`)
   - Env vars (names defined in `personas.yaml` under `credentials_env`):
     - `ALPHA_TRADER_ALPACA_KEY`
     - `ALPHA_TRADER_ALPACA_SECRET`
     - `ALPHA_COMMERCE_LEMONSQUEEZY_KEY`

3. **Production `INTEGRATION_ENCRYPTION_KEY`** (the Fernet key that
   encrypts creds in `platform_connections`):
   - Source: Render env on `yarnnn-api` + `yarnnn-unified-scheduler`
   - Neither you nor Claude ever reads this directly. The connect scripts
     POST plaintext creds to prod over TLS; Render encrypts them there.
     This is by design — the blast radius of a leaked service key stays
     at "can read DB rows" and doesn't extend to "can decrypt every
     persona's Alpaca account".

### Recommended session-start ritual (KVK or Claude)

```bash
cd /Users/macbook/yarnnn/api

# Make sure .env has SUPABASE_SERVICE_KEY. For connect operations also load:
export ALPHA_TRADER_ALPACA_KEY='PKB3...'       # 1Password > alpha-trader.alpaca-paper
export ALPHA_TRADER_ALPACA_SECRET='GYVQ...'
export ALPHA_COMMERCE_LEMONSQUEEZY_KEY='eyJ0...'  # 1Password > alpha-commerce.lemonsqueezy
```

Pragmatic tip: keep a small `api/.env.alpha-ops` (gitignored — the repo
`.gitignore` already excludes `.env*`) that exports the above. Source it
when you need connect operations. Don't source it during day-to-day API
development — you don't want persona creds sitting in random Python shells.

## Commands

All commands are run from the repo root. The scripts add their own
directory to `sys.path` so direct invocation (`python scripts/alpha_ops/X.py`)
works without needing to mark `api/` as a package.

### Verify both personas are healthy

```bash
python api/scripts/alpha_ops/verify.py --all
```

Read-only. No JWT required (uses the service key). Prints pass/fail per
invariant per persona. Non-zero exit if anything is off.

Run this:

- At the start of any alpha session, as a sanity check
- Before and after every ADR-affecting change to `workspace_init.py`,
  `agent_framework.py`, `task_types.py`, `directory_registry.py`,
  `integrations.py` (the files whose behavior determines what a
  cold-start workspace looks like)

### Mint a fresh JWT

```bash
export JWT=$(python api/scripts/alpha_ops/mint_jwt.py alpha-trader)
curl -s -H "Authorization: Bearer $JWT" \
  https://yarnnn-api.onrender.com/api/memory/user/onboarding-state | jq
```

JWTs last ~1 hour. Mint a new one if you get a 401.

### Connect platform creds

```bash
# Requires env vars named in personas.yaml credentials_env.
python api/scripts/alpha_ops/connect.py alpha-trader
python api/scripts/alpha_ops/connect.py alpha-commerce
```

Idempotent — the prod connect endpoints upsert. Safe to re-run to rotate
a key.

### Reset a persona to cold-start

```bash
# Destroys agents, tasks, workspace_files, platform_connections, chat history.
# Then synchronously rescaffolds the full alpha roster.
python api/scripts/alpha_ops/reset.py alpha-trader --confirm
python api/scripts/alpha_ops/connect.py alpha-trader        # re-attach Alpaca
python api/scripts/alpha_ops/verify.py  alpha-trader        # confirm invariants
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
  When the expected shape changes (e.g. `connect_commerce` starts
  scaffolding a `commerce-digest` task), update `scaffolded_tasks` in
  the yaml — don't update prose.
- **Destruction requires intent.** `reset.py` refuses without `--confirm`.
  `purge_user_data.py` (older, lower-level) stays in place for the rare
  case where we need surgical deletion below the `/account/reset`
  endpoint.

## Known drifts (documented, not fixed)

1. **`_risk.md` path lacks leading slash.** `api/services/risk_gate.py:48`
   defines `RISK_MD_PATH = "workspace/context/trading/_risk.md"`. Every
   other workspace path uses a leading `/`. The file on disk matches the
   constant so nothing is broken — but this is inconsistent with ADR-119
   path conventions. Flagged in `personas.yaml` for `alpha-trader`. Fix
   is a separate concern.

2. **`connect_commerce` doesn't scaffold `commerce-digest`.**
   `connect_trading` scaffolds a `trading-sync` task (paused, pending
   source selection). `connect_commerce` scaffolds only the context
   domains. Asymmetry between ADR-183 and ADR-187. Flagged in
   `personas.yaml` — will surface as alpha friction when KVK tries to
   activate commerce sync and can't find the task.

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
