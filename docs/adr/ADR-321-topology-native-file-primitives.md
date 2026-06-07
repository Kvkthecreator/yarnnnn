# ADR-321 — Topology-Native File Primitives: the Five-Root Filesystem as the Agent's Address Space

> **Status**: DRAFT (2026-06-07). Proposed by Claude, pending KVK ratification. Companion to ADR-320 (five-root permission topology) — this ADR finishes the topology migration on the *primitive* side that ADR-320 finished on the *gate* side. **Scope sharpened 2026-06-07** after the [primitive-surface-grounding discourse](../analysis/primitive-surface-grounding-2026-06-07.md): D5 now deletes the vestigial `context` substrate *family* (not merely the `scope='context'` enum value), and the canon-drift fixes the discourse surfaced are folded in (§Canon-drift below). This ADR is the **first** in the post-ADR-320 surface re-grounding arc — followed by ADR-322 (entity-layer pruning), ADR-323 (finish the persona-frame collapse), ADR-324 (InferContext *dissolution* — the operator's reconsideration resolved the earlier "deferred derive-producer" horizon into a concrete deletion), and ADR-325 (Embed as a gated primitive — the fundamental make-AI-ready operation the reconsideration surfaced). Sequencing rationale: §Relationship.
> **Date**: 2026-06-07
> **Authors**: KVK, Claude
> **Upstream**: ADR-320 (the gate became `access(2)`; this ADR asks whether the *syscalls* should become path-native to match) + the prompt-envelope alignment pass (2026.06.07.2 CHANGELOG) that surfaced a *second wave* of `context/`-root drift living inside the primitive tool descriptions themselves + the [primitive-surface-grounding discourse](../analysis/primitive-surface-grounding-2026-06-07.md) (the evidence base: Authored Substrate is decisively first-class — 100% of content writes via `write_revision` — which is *why* the `context` family is vestigial and the destination is "one authored write, one two-rank read").
> **Dimensional classification**: **Mechanism** (Axiom 5 — primitives are the vocabulary of the Mechanism dimension; FOUNDATIONS Derived Principle 9) primary + **Substrate** (Axiom 1 — the file layer addresses the filesystem) + **Channel** (Axiom 6 — the LLM-facing tool description IS the legible interface).
> **Canon backing**: ADR-222 + Derived Principle 16 (literal OS framing) — ADR-320 made the *permission model* `access(2)`; this ADR asks whether the *file syscalls* should become path-native like a real OS's `open`/`read`/`write`/`stat`, dropping the `scope` indirection.

---

## The one-sentence thesis

**ADR-320 made the workspace a real five-root filesystem and made the gate `access(2)`, but the file-layer primitives — the agent's actual syscalls — still speak a pre-topology `scope` enum (`workspace | agent | context`) whose `context` value hardcodes a root that ADR-320 dissolved.** The fix is to make the file primitives path-native (the path IS the address — grep/bash, not a `scope` indirection), so the syscall surface matches the topology the gate already enforces.

---

## Context — the gap ADR-320 left on the primitive side

ADR-320's claim-tiering was careful: the **gate** became topological (`_is_path_locked(caller_class, path)` over a per-caller prefix table). But the migration swept *path constants*, *the gate*, *the wake envelope*, *the persona-frame*, *readers*, *bundles*, and *the FE*. It did **not** sweep the **file-layer primitive tool descriptions** — the LLM-facing `WriteFile` / `ReadFile` / `SearchFiles` / `ListFiles` / `QueryKnowledge` schemas in `api/services/primitives/workspace.py`. Those primitives are the agent's syscall ABI (ADR-222: "the primitive matrix is the syscall ABI"). They are still pre-topology. Receipts:

1. **The `scope` enum encodes a dissolved root.** `WriteFile.scope` is `{workspace, agent, context}`. `scope='context'` is documented as "writes to `/workspace/context/{domain}/`" (`workspace.py:148`) and the handler resolves `domain_folder = get_domain_folder(domain) or f"context/{domain}"` (`workspace.py:628`). **ADR-320 moved domain context to `operation/{domain}/`.** So `scope='context'` writes to an orphaned root the readers (reviewer envelope, working_memory, cockpit_awareness) no longer consult — the exact silent-data-loss class the 2026.06.07.2 prompt fix caught in `dispatch_specialist`, but baked into a *primitive* instead of a prompt.

2. **Every `context/` example in the file primitives is stale.** `SearchFiles` example `path_prefix='context/'` (`workspace.py:200`); `ListFiles` example `path='context/'  # context domains` (`workspace.py:256`); `QueryKnowledge` "use ListFiles on `/workspace/context/`" (`workspace.py:217`); `read.py:124` `/workspace/context/{domain}/_recurring.yaml`; `search.py:30-31` `/workspace/context/**` and `/workspace/context/{domain}/_recurring.yaml`. The model reads these descriptions and reproduces the dead root. The 2026.06.07.2 grep gate cleared the *agent-frame* prompts; it did not touch the *primitive* descriptions because those weren't in the prompt-alignment scope.

3. **The primitives-matrix still lists `context` as a substrate family.** `docs/architecture/primitives-matrix.md` "Dimensional framing" table: `Substrate family column (entity / file / context / lifecycle / action / interaction / external / introspection)`. The `context` family was the pre-ADR-320 separate-root concept; under five roots, "context domain" is just `operation/{domain}/` — a path under the `operation` root, not a separate substrate class.

The gate is internally consistent (ADR-320). The syscalls that hit the gate are not. An agent that obeys the `WriteFile` description writes to `context/{domain}/`; the gate (`agent` caller locked from `governance/ constitution/ persona/ system/`) **lets that write succeed** because `context/` matches none of the locked prefixes — and it lands nowhere any reader looks. Topology-as-permission works; topology-as-addressing does not yet.

---

## The grep/bash analogy (the design north star)

The operator's framing question: *should our primitives become more fundamental — like grep and bash?* The analogy is exact and now load-bearing because ADR-320 made it true:

- **Claude Code has no `scope` enum.** `Read`/`Write`/`Grep`/`Glob`/`bash` take **paths**. The path *is* the scope. `Read("/etc/hosts")` and `Read("./src/main.py")` are the same syscall; the directory disambiguates. There is one address space; the filesystem topology *is* the scoping.
- **Before ADR-320, YARNNN could not do this.** The workspace root mixed `/etc`-class, `~/.config`-class, and `~/Documents`-class in `context/_shared/` (ADR-320's own indictment). With no clean topology, a `scope` enum was a *reasonable compensation* — it told the primitive which semantic bucket to resolve a relative path against, because the path prefix alone could not.
- **After ADR-320, the compensation is dead weight.** The five roots ARE the semantic buckets, and they're *in the path*. `WriteFile(path='operation/competitors/acme/signals.md')` is unambiguous. `scope='context', domain='competitors', path='acme/signals.md'` is the same write expressed through an indirection that (a) re-derives a root the path already names and (b) names the *wrong* root (`context/` not `operation/`).

The grep/bash insight, stated as the rule this ADR proposes: **the path is the address; the root in the path is the scope; the gate derives permission from the root.** One address space, no `scope` indirection, syscalls that look like `open(2)`/`read(2)`/`write(2)` over `/workspace/`.

---

## Decision (proposed) — path-native file primitives, `scope` retired to a compatibility shim then deleted

> All decisions are PROPOSED. The cardinality of the change is deliberately staged so the high-blast-radius `scope` deletion is separable from the low-risk description sweep.

### D1 — The file primitives take workspace-relative paths; the root in the path is authoritative.
`ReadFile`, `WriteFile`, `SearchFiles`, `ListFiles` accept a `path` that is workspace-relative under `/workspace/` (e.g. `operation/competitors/acme/signals.md`, `persona/standing_intent.md`, `system/notes.md`). The top-level segment IS the root; the gate (`_is_path_locked`, ADR-320) reads it. No primitive re-derives a root from a `scope` value. This is the grep/bash shape: the path is the address.

### D2 — `scope='context'` is DELETED (it names a dissolved root).
`scope='context'` + `domain=` resolved to `/workspace/context/{domain}/`, which ADR-320 moved to `operation/{domain}/`. There is no longer a `context/` root for it to address. Callers say `WriteFile(path='operation/{domain}/...')`. The `domain` parameter and `get_domain_folder()` indirection dissolve — a domain is just a path segment under `operation/`. **This is the load-bearing correction**; it removes the silent-data-loss path, not merely a stale example.

### D3 — `scope='agent'` is PRESERVED but reframed as a distinct address space, not a peer of the five roots.
`scope='agent'` addresses `/workspace/agents/{slug}/` — the per-agent private root that ADR-320 explicitly left *out* of the five-root constitution/operation cut (`workspace_paths.py`: "agents/ is per-agent ... not part of the constitution/operation cut"). It is a genuinely different address space (per-agent, slug-scoped, requires agent context to resolve `{slug}`), so it stays as an explicit scope — the way `~user/` is a distinct namespace from `/`. **Open question (see below): could `scope='agent'` also collapse into path-native `agents/{slug}/...`?** Leaning yes for symmetry, but it requires the caller to know its own slug; deferred to keep this ADR's cut clean.

### D4 — The `scope` parameter narrows from a 3-value enum to a 2-value enum (`workspace | agent`), default `workspace`; then a follow-on may delete it entirely.
After D2, `scope` has two values: `workspace` (the five-root address space, default) and `agent` (the per-agent address space). This is no longer a *semantic-bucket selector* (the old `context` job) — it is an *address-space selector* between the shared filesystem and the per-agent filesystem. If D3's open question resolves to "collapse `agents/` into path-native too," `scope` deletes entirely and the file primitives become pure `path`-takers (full grep/bash parity). Staging it this way keeps the risky deletion out of the description-sweep commit.

### D5 — The `context` substrate family in primitives-matrix collapses; its members re-home.
"Context domain" was a separate substrate-family concept because it had a separate root. Under five roots it is `operation/{domain}/` — a `file`-family path under the `operation` root. The matrix's substrate-family enum **drops `context`**, and its three members re-home (per the discourse §3):
- `WriteFile(scope='context')` → `file` family (D2 deletes the scope value entirely).
- `Schedule` → `lifecycle` family (where it already belongs).
- `InferContext` → **dissolved entirely** by ADR-324 (the operator's reconsideration found it is an application-level workflow — LLM-merge into two identity/brand files — with only two callers, not a primitive). For *this* ADR it simply leaves the `context` family; ADR-324 then removes it as a primitive (relocating its merge to a dispatch helper). The `context` family loses its last member.

`QueryKnowledge` stays a distinct *primitive* (semantic-rank composition over `operation/{domain}/` accumulated context — a real different mechanism, ADR-151), but it is a `file`-family primitive that ranks semantically, not a `context`-family primitive.

### D6 — `QueryKnowledge` and the domain-discovery prose re-root.
`QueryKnowledge` description ("use ListFiles on `/workspace/context/`") → `/workspace/operation/`. The "domains are filesystem-discovered" prose points at `operation/`. `SearchFiles`/`ListFiles`/`ReadFile` examples re-rooted `context/` → `operation/`. This is the description-sweep half — low risk, mechanical, ships first.

---

## Canon-drift (surfaced by the discourse; split into fix-now vs ships-with-implementation)

The discourse surfaced that `primitives-matrix.md` had drifted from ADR-320. The drift splits cleanly on a discipline line — *does the doc misdescribe current code, or correctly describe current-but-soon-to-change code?*

**Fixed now (pure doc bugs — the doc said the wrong thing about *current* code; landed 2026-06-07 with this ADR draft):**
- `primitives-matrix.md:97` claimed a `work` entity type. The live `ENTITY_TYPES` (`refs.py:71-88`) has no `work` — it's `agent, version, platform, session, document, task`. Corrected.
- `primitives-matrix.md:289-290` said `InferContext` writes `context/_shared/IDENTITY.md` / `BRAND.md`. The live code (`infer_context.py:122`) *already* writes `persona/IDENTITY.md` / `operation/BRAND.md` (ADR-320). Corrected to match running code.

**Ships with implementation (NOT fixed now — the doc correctly describes *current* code that this ADR changes):**
- `primitives-matrix.md:99,244,309,329-330,535` describe `scope='context'` → `/workspace/context/{domain}/`. The code *still resolves there* (`workspace.py:628`, `get_domain_folder() or f"context/{domain}"`). Editing the doc ahead of the code would make it lie about current state. These re-root to `operation/` **in the same commit** as the D2 handler change — doc and code move together (CLAUDE.md §1 docs-alongside-code).

---

## What this is NOT

- **NOT a new primitive.** No `grep`/`bash`/`glob` primitive is added. The bet is *narrower*: the existing file primitives become path-native. (A separate question — "should YARNNN expose a raw `Glob` or a `bash`-equivalent?" — is explicitly out of scope; the current `SearchFiles` (BM25) + `ListFiles` (path enumeration) + `QueryKnowledge` (semantic) trio covers the read surface. Adding a shell-exec primitive to a substrate that is Postgres-backed `workspace_files`, not a POSIX FS, would be a category error — there is no shell.)
- **NOT a gate change.** ADR-320's `_is_path_locked` is correct and untouched. This ADR makes the *callers* of the gate speak the gate's language.
- **NOT a re-rooting.** ADR-320 did the re-rooting. This is the syscall-ABI cleanup ADR-320 deferred.
- **NOT an MCP-surface change.** ADR-169's three intent-shaped MCP tools (`work_on_this`/`pull_context`/`remember_this`) compose over `QueryKnowledge`/`WriteFile`/`InferContext`; they don't expose `scope`. They inherit the re-rooting for free once the primitives re-root.

---

## Claim tiering (what is forced vs. chosen)

Mirroring ADR-320's discipline so future pushback isn't foreclosed by false necessity:

- **FORCED (by ADR-320 — already-ratified canon):** `scope='context'` addresses a root that no longer exists. This is not a design choice; it is a *bug* against ratified topology. D2 + D6 are corrections, not proposals — the only question is the migration shape, not the destination.
- **DP16-GROUNDED (sound while we hold the OS frame):** the grep/bash north star — that file syscalls should be path-native (the path is the address). Forced *if* we hold Derived Principle 16's literal-OS commitment; revisable only if that framing is revised. D1 + D5 rest here.
- **DESIGN CHOICE (selected, not forced):** whether `scope` narrows to 2-value (D4) or deletes entirely (D3's open question); whether `scope='agent'` collapses into path-native `agents/{slug}/`. Defensible either way; staged conservatively.

The `context`-root deletion is non-negotiable (ADR-320 forces it); the full `scope`-deletion is a chosen elegance goal, stageable.

---

## Stress-test residue

- **The relative-path ambiguity `scope` was solving.** Pre-ADR-320, `WriteFile(path='acme/signals.md')` was genuinely ambiguous (which bucket?) — `scope` disambiguated. Post-D1, `path='operation/competitors/acme/signals.md'` is unambiguous *because the root is in the path*. The ambiguity `scope` existed to resolve is dissolved by the topology, not papered over. ✅
- **Callers that pass `domain=` separately.** `directory_registry.py`, `compose/assembly.py`, and ~11 sites in `workspace.py` reference `scope='context'`/`domain`/`get_domain_folder`. Migration: each becomes a `path='operation/{domain}/...'` construction. Bounded, greppable, single-PR. (Sized in the impact scan below.)
- **The per-agent `agents/{slug}/` address space.** Genuinely distinct (slug-scoped, needs agent context). D3 preserves it as an explicit scope; the symmetry-completion (collapse it too) is deferred, not rejected. ✅
- **MCP foreign callers.** `yarnnn:mcp` writes only `operation/` (ADR-320 `CALLER_WRITE_POLICY`). Path-native `WriteFile(path='operation/...')` is exactly what the gate permits — no special MCP path. ✅
- **`QueryKnowledge` is not just renamed prose.** It is a real distinct mechanism (vector-rank over accumulated domain context). D5 reclassifies its *substrate family* (context→file) without touching its *mechanism*; it stays a separate primitive. ✅

---

## Scope / blast radius

Smaller than ADR-320 (this is the cleanup ADR-320 deferred, not a new cut). Two-commit shape:

**Commit A — description sweep (D6, low risk, ships first):** re-root every `context/` → `operation/` in the LLM-facing tool descriptions: `workspace.py` (WriteFile/SearchFiles/ListFiles/QueryKnowledge examples + scope docs), `read.py:124`, `search.py:30-31`, primitives-matrix substrate-family note. No handler logic changes; no caller changes. Pure prompt-surface alignment (companion to 2026.06.07.2). Gated by a grep regression check: zero `context/` (as a workspace root) in any live primitive description.

**Commit B — `scope='context'` deletion + caller migration (D1-D5, the real change):**
1. `WriteFile` schema: drop `context` from the `scope` enum + drop `domain` param; reframe `scope` doc to address-space-selector (`workspace`/`agent`).
2. `handle_write_file`: delete the `scope=='context'` branch (`domain_folder = get_domain_folder(...)`, the `missing_domain` error, the `context/{domain}` default). Callers pass `path='operation/{domain}/...'`.
3. Migrate ~3 caller modules (`directory_registry.py`, `compose/assembly.py`, plus internal `workspace.py` call-sites) off `scope='context'`.
4. primitives-matrix: drop `context` substrate family; update the WriteFile/QueryKnowledge rows.
5. Regression gate `api/test_adr321_path_native_primitives.py`: (a) no `scope='context'` in any live caller; (b) WriteFile enum is `{workspace, agent}`; (c) a `WriteFile(path='operation/{domain}/x.md')` resolves to the same physical path the old `scope='context', domain` did (behavioral equivalence); (d) the gate still locks `agent`-caller from the four non-operation roots; (e) grep gate — zero `context/` workspace-root references in `api/services/primitives/`.

**Doc cascade:** primitives-matrix.md (substrate-family enum + WriteFile/QueryKnowledge rows + a header note citing this ADR), `api/prompts/CHANGELOG.md` (Commit A is a prompt change), workspace-conventions / SERVICE-MODEL primitive references if they name `scope='context'`.

**Immutable-history note:** applied migrations naming `context/` paths are not edited (migration history is immutable, per ADR-320's own discipline); live data already moved to `operation/` by ADR-320's P3 migration script.

---

## OS mapping (Derived Principle 16 — closing the loop ADR-320 opened)

| ADR-320 (the gate) | ADR-321 (the syscalls) | OS counterpart |
|---|---|---|
| `_is_path_locked(caller, path)` | path-native `ReadFile`/`WriteFile`/`SearchFiles`/`ListFiles` | `access(2)` is checked *by* `open(2)`/`write(2)` — same path, one address space |
| five-root prefix table | the root in the path *is* the scope | `/etc` vs `~/.config` vs `~/Documents` — the directory disambiguates, no `scope` flag |
| `scope='context'` → `/workspace/context/{domain}/` | DELETED — `path='operation/{domain}/...'` | a syscall addressing a directory that was `rm -rf`'d would `ENOENT`; ours silently succeeds into the void — *worse* than a real OS, which is the bug |

ADR-320 made permission topological; an OS also makes *addressing* topological (you don't pass a "scope" to `open` — you pass a path). This ADR finishes the analogy: the file primitives become `open`/`read`/`write`/`stat` over `/workspace/`, and the gate ADR-320 built is the `access(2)` they implicitly call.

---

## Relationship to other ADRs

- **Completes** ADR-320 (gate became topological; syscalls now match) and ADR-168 (the `Read→ReadFile` / `Write→WriteFile` naming reform — this is its topology-native sequel).
- **Amends** primitives-matrix.md (substrate-family enum: drop `context`) and ADR-235 ("Option A" two-scope `workspace`/`agent` model — `context` was a third scope that D2 deletes; ADR-235's Option A is *sharpened*, the `context` third scope it carried dissolves into `workspace` + a path).
- **Preserves** ADR-151 (`QueryKnowledge` semantic-rank mechanism — reclassified, not removed), ADR-169 (MCP intent tools compose over re-rooted primitives unchanged), ADR-209 (attribution unchanged), ADR-307 (the unified permission gate is unchanged; this changes what callers *pass*, not how the gate *resolves*).

---

## Open questions (deferred, named so they're known-intentional)

1. **Does `scope='agent'` collapse into path-native `agents/{slug}/...`?** (D3) — leaning yes for full grep/bash parity, but requires the caller to resolve its own slug into the path; deferred to a follow-on so this ADR's cut stays clean.
2. **Is there a `Glob`/pattern-list primitive worth adding?** — explicitly out of scope; `ListFiles(path=)` + `SearchFiles(query=, path_prefix=)` cover the surface today. Revisit only if agents demonstrably need glob patterns the prefix model can't express.
3. **No `bash`-equivalent.** Substrate is `workspace_files` (Postgres), not a POSIX FS — there is no shell to exec. The grep/bash analogy is about *addressing shape* (path-native syscalls), not about literally adding shell exec. Named so the analogy isn't over-read.
