# The Files Model — A Directory Is Meaning; Permission, Lifecycle, and Provenance Are Metadata

**Date**: 2026-07-08
**Hat**: A (system canon — a first-principles design note deriving the target Files model).
**Status**: **Design note — for ratification.** States the axiom and derives the target from it, so the Files surface stops being organized by kernel architecture and starts being organized by what the work means to the operator. Commits no code. It **re-frames** the in-flight ADR-423 (`revision_kind`) and **sequences** toward — never re-derives — the per-file permission direction ADR-384 already ratified.
**Participants**: KVK (operator) + Claude (collaborator).
**Method note (operator instruction)**: reasoned from first principles — *what a directory is for* — not from the smaller change to current canon. Where the conclusion contradicts the live six-root layout, that is recorded as a finding.

---

## 0. What this note decides (and what it does not)

**Decides:** the Files surface — and the substrate namespace beneath it — is organized by **meaning to the operator**. Three *kinds* of category exist in the system; **only one belongs in the namespace as a folder**. The other two (lifecycle/disposition, and kernel-bootstrap residue) become, respectively, **derived views over metadata** and **a minimal, collapsed, path-anchored residue**. This is the balance between "flat and agnostic" and "some categorization is intuitive" — it says *which* categorization is a folder and which is a lens. The namespace-worthy kind uses the **two Finder-standard anchors** — **`Documents/`** (what you author + keep, holding the operator's meaning-folders) and **`Downloads/`** (what arrived, unifying the two raw lanes) — layman-legible names in place of the invented `operation/`/`uploads/`/`inbound/` (§3a).

**Does NOT decide:** the permission model (per-file grant is ADR-384's, referenced not re-opened); the migration mechanism for legacy `operation/` content (ADR-384 §7 step 6, the unscriptable operator-judgment step); the schema for `revision_kind` beyond what ADR-423 already specs. This note is the *organizing axiom*; those are its downstream builds.

**The two ratified inputs it sits on** (not re-litigated):
- **ADR-384** (the re-founding) — the filesystem is organized by meaning; permission is `defaulted-by-meaning, owned-by-grant`; provenance is a `revision_kind`. This note is that ADR's *Files-surface + category-theory* half, made concrete.
- **The live gate is still ADR-320 root-topology** (verified 2026-07-08: `_is_path_locked` matches a path's top-level root against a per-caller locked-prefix table; the per-principal consult narrows *by root*, not by file; at N=1 every write falls through to the pure-prefix path). **Per-file permission is ratified direction, not yet code.** This note assumes that direction and asks the *separate* question it makes urgent: **what does a directory mean once it no longer gates?**

---

## 1. The bare question

Strip away the six roots, strip away ADR-320. When the operator looks at their
workspace, and when any actor goes to organize a file: **what is a directory
FOR?**

There is exactly one answer that survives first principles: **a directory is an
act of grouping things that belong together — its meaning is "these are about
the same thing."** That is the entire reason `ls` is legible. You read the
folder names and you understand the work. A directory is a *meaning-grouping
primitive*.

Everything else a directory has ever been asked to carry — *who may write here*
(permission), *what state is this in* (lifecycle: live / trashed / draft),
*where did this come from* (provenance: authored / observed / derived) — is a
**property of the file, the writer, or the revision**, not a property of
*location*. Loading any of them onto the directory makes one mechanism serve two
orthogonal goals that pull apart; and when they conflict — the instant more than
one principal, one lifecycle, or one provenance touches one topic — **meaning
loses**, because the other job is *enforced* and meaning is mere convention.

## 2. The symptom, observed

A live `ls /workspace` returns the **judgment seat's anatomy**, not the
operator's work:

```
constitution/  governance/  persona/  operation/  system/  contract/  inbound/  uploads/
```

The operator opens Files expecting to see *what they are working on* and sees
*how the kernel is structured*. `operation/` — "the work" — is one node among
seven kernel-shaped siblings, three of which (`governance/`, `system/`,
`persona/` for a bare workspace) they may never legitimately touch. **Permission
and architecture won the top of the tree; the operator's view of their own work
lost.** That is not a UX nit; it is the two-jobs conflation of §1, rendered.

The ADR-422 pass (shipped 2026-07-08) treated the *legibility* of this — three
honest affordances for the not-freely-editable states, the developer `sys` word
removed. That was correct and shippable, but it was **palliative**: it made the
wrong-shaped tree *readable*, not *right-shaped*. This note is the structural
cure ADR-422's own §6 pointed at.

## 3. The three kinds of category (the load-bearing distinction)

Not all categorization is the same. The operator's instinct — *"even a trash
can, or the macOS sidebar, makes things more intuitive"* — is correct, and the
reason it is correct is that **Trash is not a directory.** It is a *disposition*
rendered as a view. macOS is the counter-design to the six roots: **Favorites**,
**Locations**, **Tags**, **Recents**, **Trash** in the Finder sidebar are
**dispositions and lenses layered over one filesystem** — you never navigate
*into* a permission class or a lifecycle state; `~/Documents` is the sole
meaning-grouping, and iCloud's cloud-glyph is *metadata rendered as an
affordance*, not a folder named `not-downloaded/`.

So there are three kinds, and each has exactly one right home:

| Kind | Examples | Belongs in | Why |
|---|---|---|---|
| **① Meaning grouping** (operator-authored) | `Documents/` (holding `the-acme-deal/`, `household/`, …) + `Downloads/` (the raw-arrival zone) | **The namespace** — real folders the operator makes + names | This is what a directory IS. Fully agnostic — the kernel names only the two Finder-standard anchors; everything inside `Documents/` is the operator's. |
| **② Lifecycle / disposition** (a fact about the file's state) | Trash, Recents, (future: Drafts) | **Metadata → a derived VIEW** | A lens over a flag, not a place. **Trash already works exactly this way** (`lifecycle='archived'` + `TrashView`); Recents too (`updated_at` + `RecentRevisions`). The pattern exists — it must be *generalized*, not invented. |
| **③ Kernel-bootstrap residue** (paths the kernel reads by fixed name) | `governance/_autonomy.yaml`, `system/`, per-agent homes `agents/{slug}/` | **A minimal path-anchored residue** — structural, but tiny + collapsed | ADR-384 D2 proved this is *irreducible*: the kernel locates its own grant/floor by fixed path, and an empty locked region has no file-metadata to protect (only the path can). It stays topological — but it is `.app`-internals, not the top of the operator's tree. |

**The whole answer is in this table.** "Flat and agnostic" applies to ①. "Some
categorization is intuitive" is satisfied by ② *as views, not folders*. And ③ is
the honest, minimal, hidden exception ADR-384's triple-check already carved. The
balance is not a compromise between flat and structured; it is **putting each of
the three kinds in the layer that fits it.**

### 3a. The Finder vocabulary — benchmark the analogy all the way (2026-07-09)

Kind ① has **two** namespace anchors, and the OS analogy names both better than
YARNNN's invented words (`uploads/`, `operation/`, `inbound/`) ever did. Finder's
words carry meaning a layman already holds — so we adopt them rather than mint
our own:

- **Documents** = *what you author and keep* — the home of your actual work. In
  YARNNN this is the authored substrate: what chat/agents/you produce (today's
  `operation/`), and **the operator's meaning-folders live *inside* it**
  (`Documents/the-acme-deal/`), exactly as real folders live in `~/Documents`.
- **Downloads** = *what arrived from outside, that you didn't author* — the raw
  inbox you triage from. In YARNNN this **unifies the two raw lanes**:
  `uploads/` (human drops) **and** `inbound/` (machine/external arrivals — MCP,
  connectors). They are the *same concept* (arrived-not-authored); Finder gives
  it one word. An `inbound/` item is distinguished *within* Downloads by its
  `revision_kind='observation'` metadata (the ADR-423 reframe, §5) — a badge, not
  a subfolder.

The load-bearing discipline (the one place the analogy misleads if taken
loosely): **NOT "everything goes to Downloads."** In Finder, authored documents
go to Documents; only *arrivals* go to Downloads. That arrived-vs-authored split
IS the meaning the two words carry — collapsing to one bucket loses it. So the
two anchors are not alternatives; they are the two halves of kind ①:
**Documents for what you make, Downloads for what arrives.** This retires the
note's earlier invented "Records" term — "Downloads" is the layman-legible name
for the same view.

## 4. The target Files model

Derived directly from §3:

```
OPERATOR TREE  (kind ①: the two Finder-standard namespace anchors)
  Documents/                   ← what you author + keep (today's operation/);
    the-acme-deal/                the operator's meaning-folders live INSIDE it
    household/
    yarnnn-product/
  Downloads/                   ← what ARRIVED (didn't author): unifies uploads/
    (a PDF you dropped)           (human drops) + inbound/ (machine/external);
    (an MCP observation) ⬇        an arrival is badged by revision_kind, not
                                  split into a subfolder

VIEWS          (kind ②: metadata lenses — the generalized Trash pattern)
  ▸ Recents    (updated_at desc)               ← exists (RecentRevisions)
  ▸ Trash      (lifecycle = 'archived')        ← exists (TrashView)
  (an optional "Arrivals" lens = revision_kind='observation' can cross-cut
   Downloads if useful, but the ZONE is Downloads — a place, kind ①)

SYSTEM         (kind ③: kernel residue — ONE collapsed disclosure, not 5 roots)
  ▸ System files  (governance/ · system/ · agents/{slug}/ homes · constitution/
                   + persona/ for the steward)   ← "Show system files" model:
                   present, reachable, deep-linkable, but folded out of the way
```

Three properties of this target:

1. **The operator's tree is agnostic** — the kernel names only the two
   Finder-standard anchors (`Documents/`, `Downloads/`); everything inside
   `Documents/` is theirs. `the-acme-deal/` is a meaning-folder they author;
   ADR-384's meaning-folders, realized, with a familiar home.
2. **Arrived-vs-authored is a place; finer disposition is a view.** The big
   split (did I make this, or did it arrive?) earns a *folder* because it is the
   first thing a person sorts by — that is why Finder gives Downloads its own
   place. Within Downloads, *how* it arrived (human upload vs machine
   observation) is `revision_kind` metadata — a badge, optionally an "Arrivals"
   lens, never a subfolder. Trash + Recents stay pure views (they cross-cut both
   anchors). So `inbound/` the **directory** dissolves — its files land in
   `Downloads/` and carry their `revision_kind` — the re-founding honored with a
   layman-legible name.
3. **The kernel residue is honest and hidden** — not deleted (ADR-384 D2 says it
   can't be), but collapsed into one "System files" disclosure at the bottom,
   the way an OS hides `/etc` and `.app` internals behind "Show system files."

## 5. What this does to ADR-423 (`revision_kind`) — the reframe

ADR-423 was scoped last turn as "the ledger-intake fold — tag intake writers
`'observation'`, rewire `trace`." The value objection was real: for the MCP
`remember` lane no derive step exists, so `revision_kind='derivation'` would be
written by nothing, and it read as *laying substrate for an absent consumer*.

**This note re-frames it and resolves the objection.** The point of
`revision_kind='observation'` is **not** the (absent) observation-vs-derivation
distinction. The point is that it is **the mechanism that lets `inbound/` stop
being its own provenance-directory and fold into `Downloads/` (the arrival zone)
as an ordinary file carrying an arrival badge** — the §3a unification. That
payoff is real, immediate, and independent of any derive step:

- Today `inbound/` is a **separate folder** fragmenting the operator's tree by
  provenance, sitting apart from `uploads/` even though both are *arrivals* — the
  exact §1 conflation (provenance-as-location), doubled.
- After ADR-423, `revision_kind='observation'` is a **flag** an arrival carries;
  `uploads/` + `inbound/` unify under one **`Downloads/`** anchor (a place, kind
  ①); the machine-vs-human arrival distinction is the badge (optionally an
  "Arrivals" cross-cutting lens), not two folders. The `inbound/` *directory*
  dissolves the way the re-founding says it must — and the operator gets one
  familiar "things that arrived" home.

So ADR-423 is worth doing — but its *ADR framing should be updated* from "the
ledger-intake fold (for a future derive step)" to **"provenance becomes a
lifecycle-class flag so the two raw lanes unify under `Downloads/` and intake
stops being its own namespace."** The `'derivation'` value stays reserved (§7 of
ADR-423) for when a derive step is real; it is not the justification. The
justification is the category move.

**Revised recommendation on 423:** proceed (reversing last turn's
lean-to-defer), under the reframed rationale. The *visible* proof is the
`Downloads/` unification (an `inbound/` file shows in Downloads with an arrival
badge, not in a separate root) — the commit *shows* a provenance-directory
became a badge, not just adds a column. The `trace` behavior-preservation gate
(byte-identical on a fixture chain) stands.

**Sequencing note:** the *full* `Downloads/`/`Documents/` rename is step 3-adjacent
(an FE tree reshape + a root-label change) — ADR-423 lands the column + the
unification *mechanism*; the operator-facing `Downloads/`/`Documents/` labels can
ride the same tree-reshape that collapses the kernel residue (§6 step 3), since
both are the "rename + regroup the derived tree" motion over ADR-388's
already-derived tree. They are naturally one FE pass.

## 6. Sequencing (how the target lands without a flag-day)

The target (§4) is an endpoint; it lands incrementally, cheapest-and-safest
first, each step shippable alone:

1. **[SHIPPED] ADR-422** — legibility affordances over the *current* roots. Done.
2. **[NEXT] ADR-423 reframed** — `revision_kind='observation'` (the arrival
   badge) + rewire `trace` to read the column. The mechanism that lets the two
   raw lanes unify. Additive, reversible, one migration.
3. **The Finder-vocabulary tree reshape** (kind ① labels + kind ③ collapse, one
   FE pass) — an FE reshape of ADR-388's *already-derived* tree:
   **(a)** `operation/` renders as **`Documents/`** (the operator's meaning-folders
   nested inside); `uploads/` + `inbound/` render unified as **`Downloads/`** (the
   arrival zone, arrival-type by the ADR-423 badge). **(b)** `governance/`,
   `system/`, agent-homes (+ steward `persona/`/`constitution/`) fold under one
   collapsed **"System files"** disclosure sorted last. **FE-only, no permission
   change, no substrate move** — it re-labels + re-groups the derived tree
   (ADR-388 D1). This is the single highest-impact fix for the §2 symptom and
   needs no schema. (The two halves — rename anchors, collapse residue — are one
   "regroup the derived tree" motion, so they ship together.)
4. **[ADR-384 proper] Meaning-folder re-homing** (kind ①, the *inside* of
   `Documents/`) — re-group `Documents/` (today `operation/`) content into
   operator-authored meaning-folders. This is the **unscriptable per-workspace
   operator-judgment step** (ADR-384 §7 step 6) — deferred, bounded by N=small
   pre-launch, each workspace an operator decision. The per-file permission model
   (ADR-384 D1) is its prerequisite and is referenced, not re-derived here.

Steps 2 and 3 are buildable now and together deliver most of the operator-felt
fix (arrivals unified under a familiar `Downloads/`, work under `Documents/`,
system-collapsed) **without** the unscriptable step 4. That is the balance: the
operator's tree gets dramatically more agnostic and intuitive *before* the hard
re-homing, because two of the three category-kinds (② lifecycle, ③ residue) plus
the kind-① *anchors* move mechanically, and only the *inside* of `Documents/`
(the meaning-folders) needs the per-workspace judgment.

## 7. Why this is safe to ratify

It is the **forced consequence of ADR-384** (already ratified) applied to the
Files surface + the category question ADR-384 named but did not tabulate. It
re-opens no permission decision (§0). It generalizes a pattern *already live*
(Trash/Recents as views). Its two near-term steps (423-reframed, system-collapse)
are additive/FE-only/reversible. And it honestly names the one step that can't be
scripted (§6 step 4) as the operator's, deferred. The axiom — **directory =
meaning; permission + lifecycle + provenance = metadata; three category-kinds,
one namespace-worthy** — is the organizing principle every downstream Files
decision is written against.
