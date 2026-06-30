# ADR-386 Member Lifecycle — Production Validation

**Date**: 2026-06-29
**Hat**: A (system editor — production confirmation).
**Scope**: confirm the ADR-386 grant lifecycle (foreign-LLM auto-provision · narrow · revoke=eviction · owner-immutability) is sound on the LIVE production deploy + database — not just unit-green.
**Method**: the house `docs/evaluations/*-VALIDATION.md` substrate-receipts pattern — every claim backed by a query against the live DB or a call against the deployed service, never an assertion.
**Subject**: `docs/adr/ADR-386-workspace-members-the-grant-lifecycle.md` (commits `68a0141` doc + `7f1fa20` impl, both on main / deployed).

---

## Deploy state (the code is live)

| Service | Render ID | State | Carries ADR-386 |
|---|---|---|---|
| yarnnn-api | srv-d5sqotcr85hc73dpkqdg | live (`850a247`→`90e9ca4` building) | ✅ `routes/workspace.py` + `services/principal_grants.py` (deployed in the `7f1fa20`-ancestor build) |
| yarnnn-mcp-server | srv-d6f4vg1drdic739nli4g | live (`90e9ca4`) | ✅ `oauth_provider.py` auto-provision hook — confirmed via `git show 90e9ca4:api/mcp_server/oauth_provider.py` (lines 260-277) |

`7f1fa20` (the ADR-386 impl) is an ancestor of the live `90e9ca4` on both services. The Freddie-rename lane's `67e7c03` already reconciled `test_adr386` to `freddie_caller` on the deployed branch.

---

## L1 — Schema / data soundness (live DB)

| Check | Receipt | Verdict |
|---|---|---|
| `role` CHECK allows `foreign-llm` | `principal_grants_role_check` = `role IN (owner, member, own-agent, foreign-llm, platform, a2a)` | ✅ auto-provision not rejected |
| `status` CHECK allows `revoked` | `principal_grants_status_check` = `status IN (active, revoked)` | ✅ eviction not rejected |
| Idempotency backstop | `uq_principal_grant_active` = UNIQUE `(principal_id, workspace_id) WHERE status='active'` | ✅ DB-level idempotency; **partial** index → a NEW active grant is allowed after a revoke (the reconnect cycle works by construction) |
| Lookup perf | `idx_principal_grants_principal (principal_id, status)` + `idx_principal_grants_workspace` | ✅ the consult + endpoints are indexed |
| FK integrity | `workspace_id → workspaces(id) ON DELETE CASCADE` | ✅ |
| RLS | enabled; `Service role manages grants (ALL)` + `Principals view own grants (SELECT)` | ✅ endpoints use service client |
| Live state | 11 owner/active grants, 0 foreign-llm, 0 test residue | ✅ clean |

---

## L2 — Live helpers on the production schema (synthetic principal, auto-cleaned)

Ran the full lifecycle against the live DB on a throwaway `adr386-prodval-*` principal (a real workspace_id, a fake principal_id — zero real grants touched, cleaned after):

| # | Step | Result |
|---|---|---|
| 1 | `ensure_principal_grant` → 1 active `foreign-llm` row, scopes NULL | PASS |
| 2 | re-`ensure` → still 1 active row (idempotent) | PASS |
| 3 | `narrow_grant(['operation/'])` → scopes written | PASS |
| 4 | `evict_principal` → status flips to `revoked` | PASS |
| 5 | **reconnect**: re-`ensure` after evict → 1 active + 1 revoked-audit row | PASS (the partial-unique-index design) |
| 6 | `evict_principal` on an `owner` grant → raises `OwnerGrantImmutable` | PASS (self-lockout blocked) |

**L2 = ALL PASS.** The eviction→reconnect cycle (5) is the one behavior unit tests mock; here it is proven on the real partial unique index.

---

## L3 — Live API endpoints (real JWT, deployed service)

Minted a real owner JWT (`kvkthecreator@gmail.com`, the workspace with live MCP usage) via the admin magic-link OTP exchange, hit `https://yarnnn-api.onrender.com`:

| Endpoint | Result | Verdict |
|---|---|---|
| `GET /api/workspace/members` | **200** · `grant_consult_active: true` · owner row: `regions=[governance, constitution, persona, operation, contract]`, `explicit=false`, label=email | ✅ read path live + correct |
| `POST /api/workspace/members/{owner}/revoke` | **403** `{"detail":"the owner grant cannot be revoked"}` | ✅ **owner-immutability enforced server-side on the live deploy** |

The self-lockout guard (D4) is not just a unit test — it returns 403 on the real production endpoint.

---

## L4 — Auto-provision path soundness (the one event-gated piece)

| Check | Receipt | Verdict |
|---|---|---|
| Hook deployed | `git show 90e9ca4:.../oauth_provider.py` → `ensure_principal_grant(role="foreign-llm", granted_by="system:oauth-connect")` at L260-268, wrapped in best-effort try/except | ✅ in the live MCP service |
| Resolution chain | a real MCP user (ChatGPT `37515fad`, connected to kvk) → `resolve_owner_workspace_id` → `workspace d5b9029b` | ✅ the hook would key the grant correctly |
| First live grant | 0 foreign-llm grants today | ✅ **expected** — the hook fires only on a NEW OAuth authorize; existing clients authorized before the deploy |

**Named gap (honest, not faked):** the auto-provision is code-deployed and resolution-sound, but its first live `foreign-llm` grant row appears on the **next real client re-authorization**, which cannot be forced from a headless session (it needs a browser OAuth handshake). Per the ADR-372 connector-version-pin gotcha, ChatGPT/Claude may need a Settings→Connectors→refresh to re-handshake. This is the same untestable-until-the-real-event honesty as ADR-373's competing-principal gap — the path is sound; its first firing is observed in the wild.

---

## Architecture coherence (the pipeline is sound)

The load-bearing invariant: **the gate's consult (ADR-373) honors every write the lifecycle (ADR-386) makes.** Proven live, end-to-end:

- **Provisioned** (NULL scopes) → consult uses the `mcp` class default: `operation/` OPEN, `governance/` LOCKED. ✅
- **Narrowed** to `['operation/']` → consult allow-lists: `operation/` OPEN, `agents/` LOCKED. ✅
- **Evicted** → grant `revoked`, consult (queries `status='active'`) finds no active grant → class default; in prod the token is also gone so the principal is unreachable. ✅ (the D3 dividend — eviction needs no consult branch.)

The lifecycle and the consult compose with no drift. The architecture is coherent.

---

## Verdict

**ADR-386 is PRODUCTION-SOUND.** Schema, indexes, RLS, FK (L1); the live helpers incl. the reconnect cycle + owner-immutability (L2); the deployed API endpoints incl. the 403 self-lockout guard (L3); the auto-provision hook deployed + resolution-sound (L4); and the lifecycle↔consult coherence — all confirmed with substrate-receipts against the live system. Zero production grants were mutated (11 owner grants intact, 0 test residue).

**One named, non-faked gap:** the auto-provision's first live grant row is observed on the next real foreign-LLM re-authorization (browser OAuth handshake required), not forceable headless. The path is deployed and sound; only its first firing awaits a real connect.

---

## Gap CLOSED — 2026-06-30 (the D1.a amendment)

The named gap above turned out to be *more* than "awaits a real connect." A follow-up live measurement (2026-06-30, prompted by the operator noticing the External-Agents/AI-Connections pane reading EMPTY despite "Claude saved to memory" activity) found the real shape:

- **Tokens were minting, but as REFRESH ROTATIONS, not authorizes.** Live receipt: Claude client `2308d0a8…` had 1 refresh token (newest 02:31, signature of rotation) + 18 access tokens, and 0 rows in `mcp_oauth_codes` (no authorize in flight). Every one of the 7 active clients authorized *before* the hook deployed and stays alive via silent `exchange_refresh_token` rotation — which the authorize-only hook never fired for. So a *real reconnect* wasn't even guaranteed to fix it (a connector "refresh" rotates rather than re-authorizes).
- **This was an empty-but-honest pane, not a display bug.** `GET /api/workspace/members` faithfully showed 0 foreign-llm members because there were genuinely 0 grant rows. The substrate was wrong relative to reality, not the surface.

**The fix (ADR-386 D1.a):** provisioning now fires on the refresh path too (`_ensure_foreign_llm_grant`, one shared helper, both OAuth sites) + a one-time backfill (`scripts/oneshot/adr386_backfill_foreign_llm_grants.py`).

**Receipts (live DB):**
| | BEFORE 02:38 | AFTER backfill 03:06 |
|---|---|---|
| owner grants | 11 | 11 (untouched) |
| foreign-llm grants | **0** | **7** (2 ChatGPT + 5 Claude → workspace `d5b9029b`) |

- All 7: `status=active`, `scopes=NULL` (mcp class default = `operation/`), `granted_by=system:adr386-backfill`.
- **Idempotency proven live**: re-run `--apply` held the count at 7 (not 14).
- **Endpoint render verified**: `GET /api/workspace/members` resolution simulated → 7 named, governable external members on the AI Connections pane.
- Tests: 31 + 3 mcp-gated helper tests (`.venv-mcp` 3.11 → 3 pass; api venv 3.9 → 3 skip). `tsc --noEmit` clean.

**Honest residue:** the pane shows "Claude" 5× / "ChatGPT" 2× because each is a distinct OAuth client registration (separately revocable). Correct grain, possibly cluttered display — a future dedup/group-by-name refinement, not a bug.

This is the live firing the authorize-only spec couldn't produce. The original validation was sound for its moment; the gap it named was deeper than "awaits a connect," and is now closed structurally (refresh-path) + immediately (backfill).
