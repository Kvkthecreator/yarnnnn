# Keystone — The Re-Founding: Meaning-Folders, and Permission/Provenance as Metadata

**Date**: 2026-06-29
**Hat**: A (system canon — the keystone the axiom-layer cascade derives from).
**Status**: **Keystone analysis — for ratification.** This is **Phase 0** of a canon-hardening cascade (FOUNDATIONS → architecture → ESSENCE/NARRATIVE → ADRs → design/analysis). It is the **single upstream source** every downstream edit is written *against*. It commits **no** canon change and migrates **no** substrate; it states the re-founding from first principles so it can be stress-tested in isolation before any axiom is touched.
**Participants**: KVK (operator) + Claude (collaborator).
**Method note (operator instruction)**: the keystone was reasoned **from first principles** — *what is true*, not *what is the smaller change to existing canon*. Where the conclusion contradicts current canon, that is recorded as a finding, not avoided. The "is it already stated" question is deliberately set aside; the test is entailment, not precedent.

---

## 0. What this doc decides (and what it explicitly does not)

**Decides (the keystone):** the workspace filesystem is organized by **meaning to the operator**; **permission and provenance are metadata** carried on files, writers, and revisions — **never** structure imposed on the namespace. This retires the **six semantic-class roots as a permission topology** (FOUNDATIONS Axiom 1 seventh sub-clause + Derived Principle 25) and the **`inbound/` raw lane as a provenance namespace** (Axiom 1 ninth sub-clause + Derived Principle 32 mechanism), folding both into the one ledger (ADR-209) as **metadata**.

**Does NOT decide:** the migration mechanism, the schema, the new axiom wording, or the Freddie/persona substrate layout. Those are downstream phases. This doc establishes *that the re-founding is true and why*; the cascade establishes *how it lands*.

**The four ratified inputs it sits on** (not re-litigated here):
- The single-filesystem direction ([ADR-378](../adr/ADR-378-the-workspace-as-the-outermost-unit.md) rationale) — recorded as direction, deferred to a refactor. This doc is that refactor's first-principles spine.
- The multi-principal commons ([ADR-373](../adr/ADR-373-multi-principal-workspace-and-the-re-key.md)) — the workspace is N principals writing one commons.
- The ledger-intake invariant ([ADR-376](../adr/ADR-376-ledger-intake-raw-observation-vs-derived-substrate.md), DP32) — `retain + attribute + cite`. **Preserved as an invariant; its `inbound/` mechanism is what this re-homes.**
- Freddie as the workspace agent ([the two-order direction](freddie-as-the-workspace-agent-and-the-two-order-agent-model-2026-06-27.md)) — system management vs. judgment, two orders of agent.

---

## 1. The bare question (stripped of canon)

When any actor — a human, Freddie, a persona agent, an external agent, a platform — goes to write a file, **what should decide whether the write is allowed?** Strip away ADR-320, strip away what is written. There are exactly two candidate answers:

- **(A) The path decides.** Permission is a property of *location*. To know if you may write, check *where* the file sits. ("You may write under `governance/`, not `persona/`.")
- **(B) The file and the writer decide.** Permission is a property of *the thing and the actor*. To know if you may write, check *what it is and who you are*. ("This file is Freddie's; you are an external agent; you may not.")

The current canon is **(A)** — Axiom 1 seventh sub-clause: *"the directory the path lives in determines the writer-class permission… the agent OS's `access(2)`."* The keystone claim is that **(A) is a single-principal artifact that the multi-principal commons already invalidated, and (B) is forced.** Three independent first-principles tests, each sufficient on its own.

---

## 2. Test 1 — does path-based permission survive multiple principals? (the decisive one)

The multi-principal commons (ADR-373) is **defined** by many actors writing the **same meaning-folders**: a human writes to `the-acme-deal/`, an external agent contributes to `the-acme-deal/`, Freddie derives understanding into `the-acme-deal/`, a persona agent writes judgment there. That co-writing of one topic-folder by many principals *is the feature*.

Now apply **(A) path-decides** to it. The directory `the-acme-deal/` grants write to exactly **one** writer-class — that is what *"the directory determines the writer"* means. So under (A), one of two things must happen:

1. **Everyone who writes `the-acme-deal/` has identical permission** → there is no per-principal control → the multi-principal authorization model (ADR-373's per-principal grant) **cannot be expressed**. The model collapses to single-class-per-folder.
2. **The folder is split by writer** → `the-acme-deal/freddie/`, `the-acme-deal/external/`, `the-acme-deal/human/` → which is **exactly the `inbound/` mistake and the per-agent-subtree mistake**, re-appearing *because the permission model forces it*. The namespace fragments by author, and "the Acme deal" is no longer one place.

Both outcomes are failures. Therefore: **path-based permission and a shared multi-principal commons are mutually exclusive.** You cannot have both. The instant more than one principal writes one folder, *"the directory determines who may write"* becomes a contradiction.

Under **(B) file/writer-decides**, the same scenario is trivial: every file in `the-acme-deal/` carries an owner; every revision carries an author (ADR-209 `authored_by`); the per-principal grant (ADR-373) says *"external agents may contribute observations but not overwrite Freddie's derived files."* Many principals, one folder, full per-principal control.

**Conclusion of Test 1:** the multi-principal commons *requires* permission-on-the-file. This is not a preference — it is **entailed by a decision already ratified** (ADR-373). The path-based model was coherent only in the single-principal world it was born in (one user + one Reviewer, where *"who writes `persona/`"* had exactly one answer). ADR-373 killed that premise; DP25's topology axiom has not yet caught up to its own sibling. **(B) is forced.**

---

## 3. Test 2 — what is a directory *for*?

Independent of permission: what is the *nature* of a folder? A folder is **an act of grouping things that belong together** — its meaning is *"these are about the same thing."* That is the entire reason `ls` is legible: you read the folder names and you understand the work.

Loading permission onto the folder makes one mechanism carry **two orthogonal jobs**: *group by meaning* AND *gate by authority*. These pull in opposite directions:

- **Grouping** wants *"put everything about the Acme deal together"* — many authors, one place.
- **Gating** wants *"put everything only-Freddie-may-write together"* — one author-class, one place.

The moment they conflict — which is the moment more than one principal touches one topic — **the folder cannot serve both, and meaning loses to permission** (permission is *enforced*; meaning is mere convention). This is not hypothetical: a live `ls /workspace` on the kvk workspace returns **12 architecture-shaped roots** (`governance/`, `constitution/`, `persona/`, `operation/`, `contract/`, `system/`, `inbound/`, + stray files) instead of meaning-shaped folders. **Permission won; the operator's view of their own work lost.** That is the symptom of the conflation, observed.

Unix is the counter-design: the directory tree is organized by *kind of thing* (`/etc`, `/usr`, `/var`), ownership is a *metadata fact* (`/home/alice` groups by *whose*, an owner field), and access rides on *owner + mode bits* (file metadata) — **not** on the path-prefix being a permission class. The schemes that conflated path and permission (ACL-by-location) are the ones that became unmanageable. **A directory is fundamentally a meaning-grouping primitive; overloading it with permission corrupts the one thing it is for.**

---

## 4. Test 3 — provenance (the `inbound/` half)

Same structure, same answer. Raw-vs-derived is a *property of a contribution*: *"this is what landed; that is what we made of it."* Is it a property of *where the contribution sits* (a lane — `inbound/` vs `operation/`), or of *the contribution itself*?

A contribution is fundamentally **an event in a file's history** — and history is the revision chain (ADR-209 `workspace_file_versions`). *"Raw"* and *"derived"* are two **kinds of event** on one file's timeline:

```
the-acme-deal/datastore-decision.md
  rev1  yarnnn:mcp:claude   [observation]   "Initial lean: DynamoDB"
  rev2  yarnnn:mcp:claude   [observation]   "Reconsidering — Postgres cheaper"
  rev3  yarnnn:mcp:claude   [observation]   "Decision: Postgres. Final."
  rev4  freddie:<id>        [derivation]    "Filed: datastore = Postgres (cost+joins)"
```

Putting raw and derived in two *places* (`inbound/` + `operation/`) is the **same category error** as Test 2: encoding a property-of-the-contribution as a property-of-location. The revision **already** exists as the natural home; the lane is **redundant with it**. `trace` (DP32's sole consumer — the moat headline *which principal contributed each version, how the seat reconciled them*) does not need a raw *lane*; it needs the **revision chain marked by kind**, which costs **one flag** (`revision_kind ∈ {observation, derivation}`) on a row that already carries `authored_by`.

**The DP32 invariant is fully preserved** — `retain + attribute + cite`:
- **retain** — the observation revision is immutable in the chain (ADR-209 never rewrites a revision); nothing is lost.
- **attribute** — `authored_by` on the revision (already there).
- **cite** — `derived_from` becomes a property of the **derivation revision** (it references the observation revision-id it was built from), not a frontmatter line in a separate-lane file. The structured `derived_from` (DP32 D3) survives byte-for-byte as metadata; only its *home* moves from a parallel file to the revision that earned it.

**Evidence** (perception's cited bytes, DP32 D5) is an **attachment to the derivation revision** — reachable *through* the judgment via `trace` — **not** a sibling `inbound/web/` tree. The "raw lane is evidence, not a crawl archive" rule is preserved; its mechanism becomes "evidence hangs off the derivation that cited it."

**Conclusion of Test 3:** provenance is a property of revisions, not paths. `inbound/` re-homes into the ledger as a `revision_kind` flag + `derived_from` on the derivation revision. **DP32 the invariant survives; DP32 the `inbound/` mechanism dissolves.**

---

## 5. The keystone result (the three tests converge)

From first principles, ignoring precedent:

> **Permission and provenance are properties of files, writers, and revisions — never of directories. A directory's one true job is to group by meaning. Therefore the filesystem is organized by what the work *means to the operator*; the six semantic-class roots and the `inbound/` lane both dissolve into the one ledger as metadata.**

The tell that this is **true and not merely nicer**: it is **entailed**. You do not get to choose it independently of decisions already made —
- the **multi-principal commons** (ADR-373) *requires* permission-on-the-file (Test 1);
- the **nature of a directory** *forbids* the meaning/permission overload (Test 2);
- the **nature of a contribution** *locates* raw-vs-derived in the revision, not a lane (Test 3).

The re-founding is the **forced consequence of commitments already ratified.** Choosing the six roots would mean *keeping a permission model that contradicts ADR-373.* That is the strongest kind of first-principles result: not *"this is the better option,"* but *"the alternative is incoherent with what you already decided."*

---

## 6. Why this is the SAME move four times (the unification — the coherence proof)

The re-founding is not a fifth decision bolted on; it is the **fourth application of one operation** that produced the whole architecture: *collapse a category into data, and put what's left in the right layer.*

| The collapse | "N becomes data" | What was left → where it goes |
|---|---|---|
| **Intake** (ADR-376/DP32) | "MCP vs connector vs upload" → *the source is data* | raw-vs-derived → **a `revision_kind` flag** (Test 3) |
| **Principals** (ADR-373) | "personal vs team" → *the principal count is data* | who-may-write → **per-principal grant on the file** (Test 1) |
| **Agents** (Freddie, 2026-06-27) | "one fused Reviewer" → *the agent count is data* | system-management vs judgment → **two orders of agent** |
| **Filesystem** (this keystone) | "kernel roots vs work folders" → *meaning is the only organizer* | permission/provenance → **metadata, not namespace** |

Four collapses, one operation. The re-founding is what makes the first three **land in one place**: the ledger (ADR-209) becomes the single carrier of *content + history + attribution + permission + provenance-kind + citation* — and the namespace, freed of all of it, carries only meaning. **This is the holistic form the whole vision was reaching for** — `the substrate IS the bus` (Axiom 1 fourth sub-clause) taken to completion: every kernel concern rides the revision; nothing rides the path except meaning.

---

## 7. What it costs (honest — the things the re-founding must answer for)

Stated so the parallel stress-test attacks them deliberately, not by surprise:

1. **Single-writer-per-path (ADR-286, Axiom 1 sixth sub-clause) must relax** to **single-current-state, many-attributed-revisions.** Today single-writer forbids two principals on one path; the commons needs many. The relaxation is safe because *the revision chain serializes writes* (no concurrent-overwrite; each write is an ordered, attributed revision) — so it is **not** a merge/CRDT layer (the dull-rule dividend survives: ADR-373 D5 single-head-per-path holds; what relaxes is *single-author*-per-path, not *single-head*-per-path). **This is the load-bearing claim to stress-test hardest.**
2. **Permission becomes a per-file/per-grant lookup, not a pure prefix check.** Today `_is_path_locked(caller_class, path)` is a pure-prefix property (DP25 — no filename in the lock logic; ADR-366 preserved this deliberately). The re-founding moves the lock to *file owner + writer grant*. The cost: the gate consults file-metadata, not just the path string. The benefit: it expresses what the prefix never could (per-principal, per-file authority). **Open: does a default still derive from meaning-folder convention (cheap common case), with per-file override the exception? Almost certainly yes — but name it.**
3. **The constitution/governance protections (the locks that matter) must survive as metadata.** The genuinely load-bearing locks — the GRANT (`_autonomy`, `_budget` — ADR-366), the per-act floor (ADR-343), `system/` — are *real* and must not weaken. The re-founding keeps them as **owner/lock metadata on those files**, not as directory prefixes. The aperture/floor split (DP24/ADR-343) is preserved: the floor stays inviolable, now enforced by file-lock metadata rather than path-prefix. **The protection is identical; its mechanism moves from path to file.**
4. **The raw verbatim is one revision back, not a separate file.** An agent wanting to re-derive reads a specific revision (`ReadRevision`, ADR-209) rather than open an `inbound/` file. Covered by existing primitive; a read-a-version op, not a read-a-file op.
5. **Migration is large.** Every substrate path re-homes; the gate, the wake envelope, the fork, all readers, the FE, the bundles, the live workspaces. This is an ADR-320-class migration (the very migration that *installed* the six roots — now reversed). The cost is real and is the implementation audit's to scope; this doc only establishes the direction is *true*, not *cheap*.

---

## 8. What the re-founding does NOT break (preservations — to forestall false alarms)

- **DP32 `retain + attribute + cite`** — preserved as an invariant; only `inbound/`-as-lane dissolves (§4).
- **ADR-209 authored substrate** — *strengthened*; it becomes the single carrier of every kernel concern. The single write path `write_revision()` is unchanged in shape.
- **ADR-373 multi-principal + per-principal grant** — *enabled* (Test 1); the re-founding is what lets the grant actually express per-principal authority.
- **The aperture/floor split + the real locks (DP24/DP23/ADR-343/ADR-366)** — preserved as file-metadata (§7.3); the *protection* is identical, the *mechanism* moves path→file.
- **ADR-378 ceiling** — untouched; the re-founding is *inside* the workspace; the workspace stays the outermost unit.
- **Freddie / two-order agents** — *cleanly enabled*: Freddie's home + persona-agent homes are meaning-grouped principal homes (grouped by *whose*, like `/home/alice`), with their write-protection as owner-metadata — exactly the model this keystone establishes.
- **No merge/CRDT, no new authz vocabulary, no format engine** — the DP32 dull-rule dividend survives intact (§7.1).

---

## 9. The cascade this keystone feeds (the phases — for the downstream sessions)

This doc is Phase 0. The dependency-ordered cascade it gates (each phase doc-only, ratified before the next opens — axiom-layer edits must not be parallelized, they drift):

```
0. THIS DOC — the first-principles re-founding (the upstream source)            ← ratify before Phase 1
1. FOUNDATIONS — amend Axiom 1 sixth+seventh sub-clauses (permission = metadata,
   directory = meaning); retire/rewrite DP25; fold DP32's inbound/ into a
   revision-kind model; add the four-fold "collapse the category" principle
2. ARCHITECTURE — authored-substrate.md (ledger carries permission+provenance) →
   GLOSSARY topology table → reviewer-seat → its Freddie successor →
   LAYER-MAPPING → primitives-matrix
3. ESSENCE + NARRATIVE — the moat sentence, the Freddie repositioning, the
   three-layer model (DERIVED from the settled axioms, never leading them)
4. ADRs — the re-founding ADR (ADR-380+); the Freddie ADR; amend-banners on
   ADR-320, ADR-376 (inbound/), ADR-286 (strict single-writer)
5. design/ + analysis/ — supersession banners + reconciliation
```

**The one discipline that makes an axiom-layer change safe:** doc-only, phase-gated, dependency-ordered, ratified per phase. No code in any of it — implementation is the *separate* mode, entered only after the canon settles. A parallel-agent workflow would *hurt* here (axiom edits drift against each other); this is sequential and human-paced by design.

---

## 10. The one-line statement (for the parallel stress-test to attack)

> **The workspace is one ledger and one meaning-organized namespace. Every kernel concern — content, history, attribution, permission, provenance-kind, citation, evidence — is metadata on files and revisions. The directory tree carries only what the work means to the operator. The six semantic-class roots and the `inbound/` lane were single-principal artifacts; the multi-principal commons makes permission-on-the-file and provenance-in-the-revision not a preference but an entailment.**
