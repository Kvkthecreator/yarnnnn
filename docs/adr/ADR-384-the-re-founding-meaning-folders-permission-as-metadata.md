# ADR-384 — The Re-Founding: Meaning-Folders, Permission/Provenance as Metadata (the decision record + implementation spec)

> **Status**: **Accepted** (2026-06-29) — doc-first; the **decision record** for the re-founding (the keystone is its first-principles derivation; this is the ratifiable ADR + the implementation spec). FOUNDATIONS v9.13 already landed the axiom amendments (Phase 1); this ADR is the cascade's ADR-layer record (Phase 4). **No code in this commit.** The implementation is a **separate, sequenced mode (§7)** with a named prerequisite (ADR-373 grant-consult) and an **irreducible per-workspace operator-judgment step** the adversarial triple-check proved cannot be scripted.
> **Date**: 2026-06-29
> **Authors**: KVK (operator) + Claude (collaborator)
> **Discourse base**: [the re-founding keystone](../analysis/the-re-founding-meaning-folders-and-permission-as-metadata-2026-06-29.md) (the first-principles derivation, ratified-with-revisions) + [the adversarial triple-check findings](../analysis/keystone-triple-check-FINDINGS-2026-06-29.md) (REVISE-FIRST → the corrected statement; substrate receipts R1–R5).
> **Ratifies**: FOUNDATIONS v9.13 (Axiom 1 sixth + seventh + ninth sub-clause amendments + Derived Principle 25 minimized + Derived Principle 33 added). This ADR is the decision record those axiom edits reference.
> **Amends**: [ADR-320](ADR-320-constitution-region-topological-cut.md) (topology-IS-permission → minimized to the path-anchored residue, for the commons), [ADR-376](ADR-376-ledger-intake-raw-observation-vs-derived-substrate.md) (the `inbound/` raw *lane* → a revision-kind; the `retain + attribute + cite` invariant is PRESERVED), [ADR-286](ADR-286-kernel-program-substrate-single-writer.md) (single-writer-per-path → single-head-many-authors *for the commons*; kernel/bundle/system paths unchanged).
> **Depends on**: [ADR-373](ADR-373-multi-principal-workspace-and-the-re-key.md) — the per-principal grant is the *runtime authority* this ADR's "owned-by-grant" rests on. **373's schema is live (migration 189, backfilled); 373's grant-CONSULT is now WIRED (Implemented 2026-06-29) — the gate consults `principal_grants` per-principal and falls back to `CALLER_WRITE_POLICY` (the class-default), with the owner/NULL-scope path proven byte-identical (99/0). This ADR's hard prerequisite (§7) is SATISFIED.** The remaining §7 steps (metadata carriers, defaulted-by-meaning gate, inbound/ fold, reader re-point, the operator-judgment re-home) are the separate re-founding mode — NOT this session.
> **Preserves**: [ADR-209](ADR-209-authored-substrate.md) (the single write path + the revision chain — the ledger is *extended*, not replaced), [ADR-378](ADR-378-the-workspace-as-the-outermost-unit.md) (the topology ceiling — the single-writer relaxation is conditioned on the single-substrate topology; federation re-opens it), [ADR-343](ADR-343-aperture-floor-kernel-derivable.md)/[ADR-366](ADR-366-autonomy-mode-as-execution-breadth.md) (the GRANT + per-act floor — the irreducible lock, kept as the path-anchored residue).
> **Dimensional classification** (Axiom 0): **Substrate** (Axiom 1 — how state is organized + how kernel concerns are carried).

---

## 1. The decision in one sentence

**The workspace filesystem is organized by *meaning to the operator*; for the work-commons, permission is `defaulted-by-meaning, owned-by-grant` (a per-file grant the meaning-folder defaults at creation, the file's own grant authoritative at runtime) and provenance is a `revision-kind` (observation vs derivation) on the one meaning-file; permission + provenance ride the ledger, the namespace carries only meaning *plus a minimal path-anchored residue* — the kernel-read GRANT/floor/`system/` and the principal-homes — that the kernel's own bootstrap mechanisms make irreducible.**

## 2. Why this is the corrected statement (not the absolutism)

The keystone first stated it absolutely — *"permission/provenance are never on the namespace."* The **adversarial triple-check returned REVISE-FIRST**: the thesis (commons → meaning + per-file grant; provenance → revision-kind) survived all five attacks, but the absolutism was **falsified at two boundaries the keystone's own preserved mechanisms force open**:

- **The file-creation boundary** — a not-yet-existing file carries *no metadata to read*. The gate deciding whether a low-trust principal may *create* `governance/evil.yaml` has nothing but the path. File-metadata cannot protect a non-existent file; only the path can.
- **The kernel's fixed-path grant read** — the kernel *locates its own breadth/budget/floor* by fixed path (`load_autonomy` → `governance/_autonomy.yaml`; the wake envelope reads named paths, ADR-281). Protecting the grant means protecting *that path* — which is topology.

So the corrected, ratifiable statement is **`defaulted-by-meaning, owned-by-grant`**, with a **minimal path-anchored residue**. The corrected entailment (triple-check Attack B): ADR-373 forbids permission living *solely* in the namespace — it does **not** forbid permission being *ever* in it (ADR-373 D3 keeps `CALLER_WRITE_POLICY` as the per-class default; per-principal grants narrow within). The directory becomes a **birth-time default-stamp**, not a runtime-permission-source.

## 3. The decisions (mirroring the FOUNDATIONS v9.13 amendments)

### D1 — The work-commons: permission is per-file grant, defaulted-by-meaning, owned-by-grant
The meaning-folder a file is born in supplies a **create-time default grant** stamped onto the new file; the **file's own grant** is the runtime authority. The gate reads the file's grant for edit/delete, not the prefix. (Axiom 1 seventh sub-clause amendment.)

### D2 — The minimal path-anchored residue stays topological
Two regions keep `_is_path_locked`'s prefix gate: **(a) the kernel-read GRANT + per-act floor + `system/`** (fixed-path read + the empty-region create-guard), and **(b) the principal-homes** (`persona/`, `agents/{slug}/` — fixed identity homes, owner-metadata, the `/home/alice` model). **DP25 dissolves for the commons; it survives, minimized, for the residue.**

### D3 — Provenance is a revision-kind, not a namespace
Raw-vs-derived folds from the `inbound/` *lane* into a **`revision_kind`** (`observation` | `derivation`) on the one meaning-file; the derivation carries **`derived_from`** (the observation revision-id(s) it was built from). DP32's `retain + attribute + cite` is **unchanged** — only its home moves namespace → revision. (Axiom 1 ninth sub-clause amendment.)

### D4 — Single-writer relaxes to single-head-many-authors, for the commons
The commons relaxes to **single current-state, many attributed revisions**: single-*head*-per-path preserved (ADR-209 CAS); single-*author* released. A genuine same-path semantic contradiction **relocates the merge into the steward seat** (the next head revision, a judgment act / wake). **Conditioned on the single-substrate topology** (ADR-378; federation re-opens it). Kernel/bundle/`system/` paths stay strict single-writer. (Axiom 1 sixth sub-clause amendment.)

### D5 — The unifying operation (DP33)
This is the fourth application of *collapse the category into data, layer what remains* (intake → revision-kind; principals → per-file grant; agents → two orders; filesystem → meaning + metadata). The coherence proof that the four macro decisions are one operation at four scales.

## 4. The substrate receipts that shape the implementation (live, 2026-06-29)

| Receipt | Finding | Implementation consequence |
|---|---|---|
| **R1** | 12 workspaces, all **N=1** (one `owner` principal each); the multi-principal commons is **schema-live but entirely unexercised** | The re-founding's payoff is **forward-looking** — at N=1 the directory does all the work; nothing pressures the model today. The migration is safe-but-not-yet-load-bearing. |
| **R2** | the live gate is **100% pure-prefix**; `principal_grants` is read only by a test — the grant-consult is **NOT wired** | **The hard prerequisite**: "owned-by-grant" cannot be implemented until 373's grant-consult lands. That is 373's Phase 2, not this ADR's invention. |
| **R3** | the floor lock has held perfectly and is **path-derived**; 0 reviewer writes to `governance/` of 739 | The residue carve (D2) is correct — the floor's protection is irreducibly path-anchored; do not weaken it. |
| **R4** | co-writing of one path is real but at the **attribution** layer (same principal's embodiments), not the **principal** layer | The competing-independent-principal same-path merge (D4's hard case) is **untested in substrate**; it is a runtime question, validated only when a real second principal exists. |
| **R5** | `inbound/` files already accrete revisions, single-author | The fold (D3) is mechanically sound; folding them *into* the meaning-file's chain is what ends their isolation (couples D3 to D4). |

## 5. What this does NOT do

- **No code, no schema, no gate change in this commit.** The live gate stays pure-prefix.
- **Does not retire DP25** — minimizes it (the seat thesis + required-region + grant/contract refinement survive).
- **Does not break DP32** — `retain + attribute + cite` is preserved; only the raw-lane *mechanism* folds to revision-kind.
- **Does not decide the per-workspace meaning-folder grouping** — that is the operator/steward's irreducible judgment (§7, the triple-check's Attack E).
- **Does not universalize the single-writer relaxation** — it is conditioned on the single-substrate topology (federation, the ADR-378 deferred axis, re-opens it).

## 6. The doc cascade (where this ADR sits)

The re-founding is a phased, dependency-ordered, doc-only-then-code cascade (keystone §9):

```
Phase 0  keystone (ratified-with-revisions + triple-check)          ✓
Phase 1  FOUNDATIONS v9.13 (the axiom amendments)                   ✓
Phase 2  architecture (authored-substrate + GLOSSARY topology)      ✓
Phase 3  ESSENCE + NARRATIVE (the moat/positioning, derived)        — sequence after the ADR-381/383 ESSENCE lane settles
Phase 4  THIS ADR + amend-banners on ADR-320/376/286                ← here
Phase 5  design/ + analysis/ reconciliation
— then —
IMPLEMENTATION (the separate mode, §7)
```

## 7. Implementation spec (the separate mode — sequenced, with the prerequisite + the non-scriptable step named)

**This is the honest decomposition.** It is *not* a clean test-gated march; it has a prerequisite and a step only the operator can do. Sequenced cheapest-and-safest first:

1. **[PREREQUISITE — ADR-373 Phase 2] Wire the grant-consult. ✅ SATISFIED 2026-06-29.** `services/primitives/workspace.py::_is_path_locked_for_principal(auth, path)` reads `principal_grants` (the per-principal grant, keyed via the uniform `services/supabase.py::resolve_principal_id(auth)`) before falling back to `CALLER_WRITE_POLICY` (the class-default `_is_path_locked`). Both gate sites in `resolve_permission` route through it. Reversible, additive, test-gated — `api/test_adr373_grant_consult.py` (20/20); the fallback-identity regression proves owner/NULL-scope is byte-identical (99/0 across all 11 live owner grants). **The "owned-by-grant" runtime authority this ADR rests on is now live.** Receipts: [`docs/analysis/adr373-grant-consult-AUDIT-FINDINGS-2026-06-29.md`](../analysis/adr373-grant-consult-AUDIT-FINDINGS-2026-06-29.md). (R2 is now stale — the gate is no longer pure-prefix; it consults the grant, falling back to prefix.)
2. **[ADDITIVE SCHEMA] Add the metadata carriers.** Migration 191+: `revision_kind` (`observation`|`derivation`, default `derivation` for back-compat) + `derived_from` on `workspace_file_versions`; a per-file `grant` field on `workspace_files` (nullable — null = inherit the meaning-folder default). **Reversible, additive, test-gated.** No behavior change until readers consult them.
3. **[GATE] Defaulted-by-meaning, owned-by-grant + the residue carve.** The gate reads the file's grant for edit/delete (commons), the meaning-folder default at create, and keeps the prefix lock for the residue (D2). **Test-gated; the residue regression is the safety-critical gate** (0 foreign writes to `governance/`; create-into-empty-locked-region still DENIED).
4. **[PROVENANCE] Fold `inbound/` → revision-kind.** Route raw intake to an `observation`-kind revision on the meaning-file; the derive step authors a `derivation`-kind revision with `derived_from`; re-spec `trace`/`recall` to walk revision-kind. **Couples to step 6 (the fold manufactures same-path multi-principal writes — D4).**
5. **[READERS] Re-point everything that reads the old paths** — the wake envelope (ADR-281 named-path reads), the fork, `workspace_paths.py` constants, `CALLER_WRITE_POLICY`, the FE, the bundles. **Flag-day-shaped per workspace** (paths are system-wide identifiers — the envelope read + bundle ship-path + lock prefix must move atomically).
6. **[MIGRATION — the irreducible operator step] Re-home `operation/` into meaning-folders.** The kernel files (MANDATE, the grant, principal-homes) have fixed targets and migrate mechanically. But re-grouping `operation/` content (domains, reports, signals) into **operator-meaning-folders** (`the-acme-deal/`, …) **cannot be scripted** — the triple-check (Attack E) proved it is a *steward judgment act, per the thesis that only the operator/steward decides meaning*. Acceptable as a flag-day **because N=12 pre-launch** (the ADR-373 §2 / ADR-286 D8 precedent), bounded by 12 atomic per-workspace cutovers — **each requiring an operator/steward decision on its own meaning-grouping.**

**The two implementation-phase open questions** (named, deferred to code): (a) the per-file grant's exact representation (a column vs. a sidecar) — implementation's call; (b) the competing-independent-principal same-path merge (D4's hard case) — only validatable when a real second principal exists (R4), so it is a runtime question, not a doc one.

## 8. Why this is safe to ratify now (despite being unbuilt)

The re-founding is the **forced consequence of commitments already ratified** (ADR-373 multi-principal + ADR-378 ceiling): keeping the old topology would mean keeping a permission model that contradicts ADR-373. The triple-check corrected the *statement* (defaulted-by-meaning, not absolutism) without falsifying the *direction*. Ratifying the ADR + axioms now (doc) while sequencing the code behind its prerequisite (§7) is the keystone's own discipline: canon settles first, implementation is the separate mode. The schema is already partly there (373's re-key); the migration is cheapest pre-launch; the one step that can't be automated is honestly named as the operator's.
