# Implementation Scope — ADR-373 Grant-Consult (backend + frontend + validation)

**Date**: 2026-06-29
**Hat**: A (system editor — implementation scoping). **This is a scope, not a spec to follow blindly.** Every claim below was checked against the live codebase + DB on 2026-06-29, but the implementing session MUST run its own audit (see §0) — this is a foundational, pre-launch refactor and the cost of a wrong assumption is high. Where this doc is uncertain, it says so; treat those as audit targets, not facts.
**Purpose**: scope wiring ADR-373's per-principal **grant-consult** at the permission gate — the load-bearing half of ADR-373 that did not ship with the re-key (migration 189). It is (a) a pre-launch blocker in its own right and (b) the hard prerequisite for the re-founding ([ADR-384](../adr/ADR-384-the-re-founding-meaning-folders-permission-as-metadata.md) §7).

---

## 0. MANDATORY first step for the implementing session — audit before you build

Do NOT start from this doc's claims. Verify them. This refactor touches the write-gate every primitive flows through; a wrong assumption ships a permission bug. The audit checklist (each is a question to answer with a receipt, not to assume):

1. **Is the gate still pure-prefix?** Read `_caller_class` + `_is_path_locked` (`api/services/primitives/workspace.py:1761`) and `resolve_permission` (`api/services/primitives/permission.py:201`). Confirm nothing already consults `principal_grants`. (This doc claims: pure-prefix, grants read only by `test_adr373_rekey.py`. Verify.)
2. **What does `AuthenticatedClient` carry?** (`api/services/supabase.py:48`). This doc claims: `caller_identity` + `workspace_id` present, **no `principal_id`**. Verify — the consult needs a principal identity to key the grant lookup, and if it's absent that's a real sub-task.
3. **What is actually in `principal_grants`?** This doc claims: one `owner` row per workspace, `scopes` NULL, `granted_by='system:adr373-backfill'`. Verify with a live query — the consult's fallback semantics depend on it (NULL scopes MUST fall back to class-default = today's behavior).
4. **How does a non-human principal map to a `principal_id`?** (human = `auth.users.id`; MCP = OAuth `client_id`; agent = slug). This doc does NOT fully resolve this — it is the genuine open design question (§3). Audit `resolve_request_client` (`api/mcp_server/auth.py`) + ADR-288 caller-identity.
5. **What is the test baseline?** Find + run `test_adr373_rekey.py`, `test_adr320_*`, `test_adr307_*` (the gate tests). Know what green looks like BEFORE changing the gate. Re-run after every step.
6. **Is there an active ADR-373-Phase-2 / grants lane?** (Concurrent-lane check — the tree has been busy. Confirm no one else is mid-flight on the gate.)

If the audit contradicts this doc, **trust the audit and flag the discrepancy** — this doc is 2026-06-29's read, and the tree moves.

---

## 1. What "grant-consult" is (the one-sentence definition)

Today the gate authorizes at **class** granularity: `_caller_class(auth)` collapses the caller to one of 5 keys (`operator | reviewer | mcp | agent | system`), and `_is_path_locked` prefix-matches that class against `CALLER_WRITE_POLICY`. The grant-consult makes the gate authorize at **principal** granularity: resolve the caller's row in `principal_grants` → read its `scopes` → use that; **fall back to the class default when there is no grant or `scopes` is NULL.** Attribution is already per-principal (ADR-288); this brings *authorization* to the same granularity (ADR-373 D2). One function + one table (ADR-373 §4 "Gate / grant" row).

**The safety invariant** (the thing that makes this shippable): a principal with no explicit grant, or a grant with NULL scopes, inherits its class default — **today's exact behavior.** The N=1 owner (every live workspace, scopes NULL) must behave byte-identically after the consult lands. Prove this with a regression before touching anything else.

---

## 2. Backend scope (the core — reversible, additive, test-gated)

Sequenced cheapest-and-safest first. Each step ends green before the next.

1. **Resolve a `principal_id` onto `AuthenticatedClient`** (if §0.2 confirms it's absent). The consult needs to key the grant lookup. Human → `auth.users.id`; MCP → OAuth `client_id`; agent → slug; system → unchanged. **This is the genuine design sub-task (§3)** — do not hand-wave it.
2. **Add the grant-consult to the gate.** `_caller_class` (or a new `_resolve_grant`) reads `principal_grants(principal_id, workspace_id, status='active') → scopes`; `_is_path_locked` uses the grant's scopes when present, else the class default. Keep `CALLER_WRITE_POLICY` (ADR-373 D3 — it IS the class-default table, not deleted).
3. **The fallback regression is the safety gate.** A test proving: owner with NULL scopes → identical decisions to today across all roots and caller-classes. This is the test that lets the change ship.
4. **The grant-honored test** — a principal WITH an explicit narrowing grant (e.g. scopes=`['operation/']`) is denied a write outside it and allowed inside it. This proves the consult actually does something.
5. **Performance**: the gate runs on every consequential write — confirm the grant lookup is indexed (`idx_principal_grants_principal` exists) and consider caching per (principal, workspace) within a request, as `resolve_owner_workspace_id` already caches.

**Do NOT, in this work**: re-home any path, change the six roots, add `revision_kind`/`derived_from`, or touch the re-founding. The grant-consult is ADR-373's, standalone. The re-founding builds on it LATER (ADR-384 §7).

---

## 3. The genuine open design question (audit + decide, don't assume)

**How does each principal class map to a `principal_id` the grant lookup can key on?** This is under-specified in ADR-373 and is the one real design call:

- **human/owner** — `auth.users.id` (a UUID; matches the backfilled `principal_id`). Probably clean.
- **foreign-llm (MCP)** — the OAuth `client_id`? the derived client name? `resolve_request_client` resolves identity per-request (ADR-310 D4) — what stable string keys the grant? **Audit `mcp_server/auth.py` + ADR-371.**
- **agent / own-agent** — the agent slug? Does an internal agent even have a `principal_grants` row today, or only the owner does? (Live data: only `owner` rows exist — so agents currently fall through to class-default, which is correct for N=1.)
- **The decision**: for the launch floor, it may be sufficient that ONLY the owner has a grant row and everyone else falls to class-default (matching today). The richer per-principal grants are ADR-373 D4's "additive post-launch." **Confirm with the operator whether the launch floor is "owner-grant-consulted, others class-default" or "all principals grant-consulted"** — this scopes the work materially.

---

## 4. Frontend scope (net-new — larger unknown, scope conservatively)

**Audit finding: there is essentially NO permission/grant/member FE surface today** (a grep found only unrelated `context`/`queue` pages). So FE here is net-new, and the honest move is to scope it to what the backend floor actually needs, not to build a full team-management UI speculatively.

The FE question is: **what does the operator need to SEE and DO about grants at launch?** Likely minimal (matching ADR-373 D4's "schema ships, provisioning UX is post-launch"):

- **Read (probably yes)**: surface *that* a workspace is multi-principal-capable — who has a grant, what they can write — as a legibility surface (the ADR-338 management-plane idiom). Even at N=1 (owner only) this is a coherent "who can touch this workspace" view.
- **Write / provisioning (probably defer)**: the invite-a-member / issue-a-grant flow is ADR-373 D4's explicitly post-launch UX. Do NOT build it unless the operator says multi-human is a launch requirement.

**The FE sub-decision the operator must make** (surface it, don't assume): is the launch FE *read-only grant legibility* (small, matches the floor) or *grant provisioning* (large, D4 says post-launch)? Default recommendation: **read-only legibility at launch.** Tie into the existing Context surface (ADR-377, the perception home) or Workspace Settings, not a net-new top-level surface.

---

## 5. Testing & validation scope

Three tiers, in order:

1. **Unit / gate regression (the floor)** — the §2.3 fallback-identity test + the §2.4 grant-honored test. These are the must-haves; the change does not ship without them green.
2. **Integration** — a real primitive write (`WriteFile` via `execute_primitive`) under (a) owner/NULL-scope → allowed as today; (b) a principal with a narrowing grant → denied outside scope. Proves the consult works end-to-end through the real gate, not just the unit.
3. **Live validation (the confidence mark)** — against the live N=1 workspaces: after the consult lands, run a battery of real writes and confirm ZERO behavior change for the owner (the safety invariant). Substrate-receipts: query `workspace_file_versions` before/after, confirm identical write-acceptance. The competing-principal case (a second real principal) is **untested until one exists** (ADR-373 D5 / triple-check R4) — name this as a known validation gap, do not fake it.

**The validation philosophy** (operator's framing): testing/validation ARE the confidence marks that the refactor is correct. The gate is the highest-blast-radius function in the system — over-test it. A green fallback-regression is what earns the right to ship.

---

## 6. Sequence (the whole arc)

```
0. AUDIT (§0) — verify this doc against live code+DB; know the green baseline
1. BACKEND — principal_id resolution → grant-consult → fallback regression (the floor)
   → grant-honored test → perf check.  SHIP when fallback-regression is green.
2. FRONTEND — read-only grant legibility (confirm scope with operator first; defer provisioning)
3. VALIDATION — unit → integration → live N=1 zero-behavior-change battery
4. THEN (separate, later) — the re-founding builds on this (ADR-384 §7); NOT this session
```

## 7. What this session is NOT

- Not the re-founding (ADR-384) — this is its prerequisite, built standalone.
- Not the full ADR-373 re-key sweep — the substrate-keying (118 sites) already landed (migration 189); this is only the grant-consult half.
- Not member-provisioning UX (ADR-373 D4 — post-launch unless the operator says otherwise).
- Not a blind execution of this doc — §0 audit first; trust receipts over this doc where they differ.
