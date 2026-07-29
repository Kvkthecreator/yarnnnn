# ADR-501 — The Read Path Follows the Binding, and the Ceiling Follows the Grant

**Status**: Accepted (2026-07-29, operator-commissioned surfacing audit — "every surface must answer: which workspace am I bound to, and what does this principal's grant in it permit?"). Implemented same day.
**Date**: 2026-07-29
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A
**Dimension**: Substrate (Axiom 1 — one binding, one authority) + Identity (Axiom 2 — the grant, never the species)
**Relates to**: ADR-373 (the re-key; the D3 role→class table this ADR makes enforced), ADR-405 (no rule keys on species — the test: which grant, which act-class), ADR-407 (three scopes), ADR-476 (purge re-key — completed here), ADR-499/500 + commits e9931b7/b1a0cf0 (the write-path binding fixes this audit follows), ADR-486 (radar, the largest miss)
**Amends**: nothing ratified. Enforces ADR-373 D3 as written; completes the ADR-373 Phase-1 read sweep.

---

## 1. Context — the audit after the write-path fixes

Three same-day fixes (ADR-499, ADR-500, e9931b7) established that the workspace binding was systematically fragile at N>1. This ADR is the commissioned full-surface audit of the READ/surfacing path, run against the two live workspaces (`d5b9029b` owner+member, `4ca9c664` solo). The audit's clean findings first, because they bound the blast radius:

- **Transport is clean.** Every FE request rides `getAuthHeaders()` (the one `X-Workspace-Id` attach point); both halves of the e9931b7 fix (direct + feed-proxy) hold; there are no browser-side table reads outside one Realtime hook.
- **The rebind invariant holds.** All four rebind sites hard-navigate; module caches are binding-keyed (ADR-500 pattern); shell/attention state is workspace-suffixed client-side and workspace×principal server-side.
- **The `substrate_scope_filter` spine covers** files, documents, studio, images, agents, recurrences, proposals, timeline, narrative, member_state, billing.

What remained were endpoints the ADR-373 sweep missed — all invisible at N=1 — and one genuine permission hole.

## 2. D1 — The ceiling follows the grant (the permission hole)

The roster (`GET /workspace/members`) displays a member's default write reach from the ADR-373 D3 role→class table (`member → agent` class → `["operation/"]`, "the member ceiling"). **The gate never read that table.** Its NULL-scope fallback keyed on the transport string `caller_identity`, which is `"operator"` for every human browser session (`supabase.py` dataclass default) and for `member:` lane writes (ADR-411 D4). Since NULL scopes is the mint default for every invite and share, a member's effective reach was **operator-class** — locked from `system/` only. Live receipt: the member grant in `d5b9029b` has NULL scopes; a member could write `governance/`, `constitution/`, `persona/`, `contract/` while the Access pane said `operation/`.

**Fix** (`services/primitives/workspace.py::_is_path_locked_for_principal`): when the write axis is NULL and a grant row exists, the class default derives from the grant's **role** via the D3 table — the SAME table the roster displays (`services/principals.py::role_class`, the singular mapping). Two guards:

- The substitution applies **only when the transport class is already `operator`** (a human session or a member's lane). Freddie/system callers also resolve their principal to the owner's user_id (`resolve_principal_id`: "the seat acts for the owner"), so an unconditional role-derived class would hand the steward the owner grant's operator class and *widen* it into `governance/`. Non-operator transport classes keep their own policy row.
- Owner is byte-identical by construction (`owner → operator` on both paths).

This also dissolves the `_ROLE_TO_CLASS` (member→agent) vs `_caller_class` (member→operator) divergence: the gate and the pane now read one table for humans.

## 3. D2 — The read-scoping sweep (what ADR-373 Phase 1 missed)

Each endpoint moves to the existing spine — no new mechanism:

| Surface | Was | Now |
|---|---|---|
| Radar (all 4 routes + discovery `.get(user_id)`) | `auth.user_id` — surface **dark for members**, 409 dedupe blind (a member create silently overwrote the workspace's declaration at the same path) | `_acting_owner(auth)` — the radar stack is owner-keyed end-to-end (discovery grouping, kind='radar' index, sweep contract "user_id = workspace owner UUID"), so the route resolves the acting workspace's owner once (the `routes/feed.py:1044` seam) |
| `GET /workspace/nav` recurrences | `.eq("user_id", …)` while the rest of the handler was workspace-scoped — nav contradicted `/api/recurrences` | `_substrate_scope_filter(auth)` (tasks rows are trigger-stamped with workspace_id) |
| `GET /execution-events` (/activity) + scheduler heartbeat | user-scoped — /activity showed 1 row where `/workspace/timeline` showed 206 (live receipt) | `substrate_scope_filter` — the two views of one ledger agree |
| `GET /emissions` | user-scoped — empty Out lens for members | acting-workspace-owner keyed (both ledgers are written by the owner-keyed wake stack; neither carries a filterable workspace column) |
| alpha-trader evaluator status | user-scoped `tasks` read | `substrate_scope_filter` |
| Danger-zone stats + L3 platform-context purge | user-scoped counts/deletes under a workspace-scoped gate (ADR-476) — the preview counted the caller's rows, the L3 revision purge left member rows | `_purge_scope`/`resolve_purge_workspace` threaded through `_count_workspace_paths`, `_delete_workspace_file_versions_by_path`, the stats endpoint, and `clear_integrations` — preview, gate, and blast radius agree |
| `load_principal_roster` | `resolve_owner_workspace_id(user_id)` unconditionally (correct-by-coincidence: every live caller passes the owner id) | `effective_workspace_id(user_id)` — binding-aware, owner fallback |

## 4. D3 — The affordance reads the verdict, not the label

`WorkspaceDangerZone` predicted clear-authority from `role === "owner"` — a false negative for a `workspace:clear`-scoped non-owner (ADR-405 violation shape: a permission decision in a role costume). `GET /workspace/memberships` now carries `can_clear`, computed by the same `has_workspace_clear_authority` the purge gate enforces; the FE reads it. Best-effort open on probe failure — the gate still enforces.

## 5. Dead code deleted (singular implementation)

- `web/lib/entity-cache.ts` — zero importers; an unkeyed module cache, the exact ADR-500 defect shape waiting to be revived.
- `resolveContentUrl` in `web/lib/workspace/upload-frontmatter.ts` — zero call sites; built an unauthenticated, binding-less URL while documenting itself as the sanctioned pattern (the live path is `api.documents.blobUrl`).

## 6. Deliberately deferred (documented, not dropped)

- **GrantGate covers 1 of 7 declared regions** (`SystemAgentPanes` `governance/` only). With D1 the gate now 403s correctly, so the gap is legibility (no advance read-only shell), not enforcement. Wire remaining regions when their editors are next touched.
- **`chat_sessions`/`session_messages` RLS is workspace-blind** (`user_id = auth.uid()` only). The live Realtime path subscribes to the member's OWN session (per-member feed sessions are the ADR-408 design), so there is no cross-principal leak; the residual exposure is a revoked member's supabase-js read access to their own historical sessions. An RLS tightening needs care (policy subqueries vs grants RLS) and its own change.
- The `('owner','member')` human predicate spelled in two tiers (`ChatSurface` + `lanes.py`), and the invite/BYOK hard `owner_id` gates lacking the `has_*_authority` scope-extension shape — pattern debt, consistent today.

## 6a. Completion pass — what the Hat-B probe found (2026-07-29, same day)

The source-anchored gates all passed and three defects survived them. A probe
driving the **live** API as both real principals (`api/scripts/operator/
probe_adr501_503_member_session.py` — harness JWT mint, real `X-Workspace-Id`)
found them in one run. Recorded here because each is a *class*, not an
incident:

1. **The gate was on one door.** D1 landed in
   `_is_path_locked_for_principal`, which only the PRIMITIVE path consults.
   `PATCH /api/workspace/file` — the editor every browser uses — has its own
   editable-prefix list (an "is this file operator-editable at all" check,
   never per-principal) and wrote straight through. The member PATCHed
   `constitution/MANDATE.md` and got 200. Both doors now consult the one gate.
   **Lesson: a permission fix must enumerate the doors, not the deciders.**
2. **RLS defeated the read sweep from underneath.** D2 moved the ledgers onto
   the workspace spine; `execution_events` / `activity_log` / `tasks` still
   carried `auth.uid() = user_id` SELECT policies, so the correct filter
   returned nothing for a member. `workspace_files` had a grant-aware policy
   since migration 189 — which is exactly why Files worked and these didn't.
   **Migration 227** adds an additive, read-only SELECT policy to each,
   bounded by migration 221's recursion-safe `is_workspace_member()`.
   **Lesson: an application-layer scoping change is only half the sweep; the
   row-level policy is the other half.**
3. **Radar's discovery grouped by the file's AUTHOR**, so an owner-authored hub
   was unreachable for a member. Now scans the acting workspace and groups by
   that workspace's OWNER — the key both the request path and the scheduler
   already look up by. (Its owner lookup needs the SERVICE client: `workspaces`
   RLS is `owner_id = auth.uid()`, so a member resolving their own granted
   workspace's owner read zero rows and fell back to the author — the join key
   missed and the list stayed empty even though the member could read the
   declaration file itself.)
4. **The explicit binding must be PASSED, not inferred.** Five route call sites
   invoked `effective_workspace_id(user_id)` without `auth.workspace_id` — the
   value `get_user_client` had already resolved fail-closed from
   `X-Workspace-Id`. Dropping the strongest signal left resolution to the
   contextvar, so a member resolved their OWN workspace and every conversation
   in the shared one 404'd.

**The shape underneath three of these four**: an application layer that
authorizes correctly, sitting on an RLS policy written when a workspace had
exactly one human. Each returned EMPTY rather than an error, so every
application-level check passed. `workspace_files` had received a grant-aware
policy back in migration 189 — which is precisely why Files worked and made the
rest look like isolated bugs rather than one class. **When a multi-principal
read comes back empty rather than erroring, read `pg_policies` before reading
more application code.**

5. **`acting_workspace_owner` carried both defects at once** — and was the real
   cause of the radar red (finding 3's fix was one layer short). It inferred
   the binding *and* read owner-only `workspaces` with the caller's client, so
   for a member both halves failed silently and it returned the **member** as
   "the owner" — a key nothing downstream had filed anything under. Now takes
   the explicit binding and the service client.

   *Process note worth keeping*: finding 3 shipped on sound reasoning and the
   probe stayed red. Executing `discover_radar_hubs` locally proved it correct
   in isolation, which is what located the upstream helper. **A red tells you
   where, not that your fix was wrong — execute the unit you just fixed before
   looking further.**

## 6b. The probe as a standing asset

`api/scripts/operator/probe_adr501_503_member_session.py` stays in the tree. It
drives the live API as both real principals (harness JWT mint, real
`X-Workspace-Id`) and asserts the whole member session end to end: binding,
the write ceiling, the wallet split, and the direct-conversation contract.
Re-run it after any change to grants, RLS, or workspace resolution — it is the
only check in the repo that can see all four layers at once.

## 7. Validation

**Final: the probe passes 22/22 against production** (`acc73fb` live,
2026-07-29). Positive receipts: member write to `constitution/` + `persona/`
refused 403 while the owner's is allowed 200 · the wallet split holds at the
wire with the Billing pane's 403 agreeing · both principals read the same
ledger (10/10) and the same radar hubs · a direct conversation broadcasts with
`direct: true` and no engine text, both participants read the same one-row
transcript, authorship is stamped, and a cross-author edit is refused 422.

**Negative receipts (the ones that matter — every fix here WIDENED reach):**
an unbound member sees only her own workspace (radar 0 · events 2 · roster 1 ·
lanes 1), and a forged `X-Workspace-Id` naming a workspace she holds no grant
in is refused **403**. Migration 227's policies are additive and read-only;
`principal_grants` remains the sole authority.

- `api/test_adr501_read_path_binding.py` — behavioral gate on D1 (the gate function executed with member/owner/no-grant/freddie-shaped auths) + sweep assertions.
- Existing gates re-run green: ADR-373 grant-consult, ADR-499, ADR-500.
- `tsc --noEmit` + `next build` green.
- Live receipts in the audit transcript: grant state, 205/1 event split, 180-file owner-keyed substrate, radar hub row.
