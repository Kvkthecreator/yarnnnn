# ADR-543: The interop surface speaks the kernel's verbs — remember/recall/trace retire into the file-native contract

> **Status**: **Accepted + Implemented** (2026-08-10) — operator-directed ("go
> away from the prior remember recall trace in FULL. singular streamlined
> implementation into our current internal tooling approach which is file
> native"). **Completed by
> [ADR-545](ADR-545-the-interop-binding-completes-edit-delete-move-changes-honest-save.md)
> (same day)**: the write-side kernel verbs (`edit`/`delete`/`move`, ADR-337)
> bind, `list` gains the change feed, `save` gains the truncation guard — the
> roster grows to nine.
> **Date**: 2026-08-10
> **Dimension**: **Channel** (the MCP binding of the kernel contract) primary;
> a **Substrate** consequence (the phantom "memory" object and its resolution
> machinery die).
> **Authors**: KVK (operator) + Claude (collaborator)
> **Relates to**: ADR-512 D3 (the kernel verb contract — read · write · **list**
> · search · revisions · share · trace; every surface a binding), ADR-368 (the
> memory-first verb cut this supersedes at the verb layer), ADR-376 §5 (the
> capture/understanding split — retained as a convention, released from a verb),
> ADR-169 (the intent-shaped ancestor, already historical), ADR-533 (participant
> contract + §13 manifest caching — the migration mechanics), ADR-428 (the
> derive wake already retired — remember's last coupling), ADR-424 D1
> (`PARTICIPANT_FILESYSTEM_MODEL` — the taught model this roster finally matches).

---

## 1. Context — a fossil record wearing one manifest

An external principal (Claude on claude.ai, 2026-08-10 session) audited the
connector from the outside and reported two findings that check out exactly
against the code:

1. **Nothing enumerates a directory.** The roster is `open · remember · recall
   · trace · save · share`; `open /workspace` returns `found: false` by design
   ("open never guesses"). The only discovery lane is `recall`, which is
   semantic — you can only find files whose *topic* you can already guess. The
   principal reconstructed the tree from recall hits and said so: "it's
   inferred, not listed."
2. **ADR-512 D3 names `list` as a Layer-1 kernel verb and declares every
   surface a binding of the contract.** The MCP binding shipped read (`open`),
   write (`save`), search (`recall`), provenance (`trace`), share — and never
   bound `list`. No ADR records a decision to exclude it. It fell through the
   strata.

The strata are the deeper problem. The surface is three eras deep:

- **ADR-169**: the connector was a *memory feature* — `work_on_this`,
  `pull_context`, `remember_this`.
- **ADR-368**: re-cut to `remember / recall / trace`, memory-first by explicit
  decision.
- **ADR-512/513/533**: identity flipped to *shared attributed workspace — "not
  a memory feature"* — and added `open / save / share`, clean kernel bindings,
  **alongside** the memory verbs rather than through them.

One manifest, two ontologies. The instructions teach a pure-OS home directory
(ADR-424 D1) while `remember`'s own docstring says "save something into the
user's durable YARNNN memory." A host LLM cannot tell whether it is holding a
filesystem or a memory plugin — and measurably, neither could the external
principal.

The internal contract has none of these concepts. Internally, memory *is
files* (`WriteFile` appends under `memory/`, ADR-064 as amended by ADR-156);
the chat surface holds `ReadFile / WriteFile / EditFile / SearchFiles /
ListFiles` + the revisions primitives. The kernel never had a memory object.

**The tax of the phantom object.** Because `remember` presents "a memory"
instead of "a file at a path," every verb that meets the object needs bespoke
machinery: `recall` runs a deterministic `resolve_memory_path()` round-trip
before real search; `trace` derives its own fetch key via `resolve_trace_path`
(the two "must stay slug-symmetric or the round-trip breaks" — the code's own
words); the docstrings then narrate the seams. ADR-512 D3 names the rule being
violated: *a compound may never introduce an object the contract doesn't
have.* Under the hood the migration already happened — ADR-376 made `remember`
an attributed raw file at `inbound/mcp/{client}/{slug}.md`; ADR-428 retired
its derive wake. Only the presentation still speaks the dead ontology.

## 2. D1 — One ontology: the interop surface is a binding of the kernel file contract

The memory ontology retires **in full** at the interop surface. Every verb
reads, writes, enumerates, searches, or histories *files at paths*; every
receipt names the path it touched. No verb presents an object the kernel
contract does not have. The connector's identity (ADR-512: the shared,
attributed workspace) and its vocabulary now agree.

## 3. D2 — The roster: `open · list · search · save · history · share`

Six verbs, each a binding of a kernel verb, each mapped one-to-one onto the
internal tooling it mirrors:

| Verb | Kernel verb (ADR-512 D3) | Internal analog | Change |
|---|---|---|---|
| `open` | read | `ReadFile` (+ revisions summary) | Unchanged. Exact-file read; still never guesses. |
| `list` | list | `ListFiles` | **NEW** — closes the unbound-verb gap. Enumerate a folder: children with kind, last author, last-updated. `list` on the root is the tree's front door. |
| `search` | search | `SearchFiles` / `QueryKnowledge` composition | **Replaces `recall`.** Search the filesystem by meaning; returns paths + excerpts + the existing `confidence` signal (the `ambiguous` → ask-the-user contract ports verbatim). The deterministic memory round-trip is deleted — nothing writes to a phantom object anymore. |
| `save` | write | `WriteFile` (CAS via `base_revision`) | Unchanged mechanics. **Absorbs `remember`'s job** — see D3. |
| `history` | revisions + provenance | `ListRevisions` / `ReadRevision` / `DiffRevisions` composition | **Replaces `trace`.** The history of one *file*: who changed it, when, what changed. The "or recorded fact" dual object dies; `resolve_trace_path` dies with it. |
| `share` | share (the grant act, ADR-465 D1) | the share/grant machinery | Unchanged. The one deliberately external-supplemental verb — internal principals are already in the workspace; an external principal needs the door verb. |

Compound composition survives (ADR-368 Correction 1 stands: a consumer chat
host gets few, server-composed compound tools). What changes is that every
compound now composes **only** contract objects.

## 4. D3 — `remember` dissolves into `save` + the taught model

`remember`'s two real properties are preserved without the verb:

- **The ambient-capture behavior** ("don't wait for the user to say remember
  this") is *instructions*, not a verb. The connector instructions gain one
  clause: when the user concludes something worth keeping and no document is
  in hand, save it — by meaning, like any participant; a conversational
  observation with no better home goes under **Downloads** (the arrived-from-
  outside lane the filesystem model already teaches).
- **The capture/understanding split (ADR-376 §5)** is retained as *convention
  + grant*, released from the verb. `save` already writes attributed revisions
  wherever the grant allows — ADR-512 crossed that line deliberately. The
  distinguished remember-only path helper (`resolve_remember_path` →
  `inbound/mcp/{client}/{slug}.md`) is deleted; the ADR-307 gate at
  `execute_primitive` remains the sole authority on reach, unchanged.

`remember`, `dispatch_remember_this`, `resolve_memory_path`,
`resolve_remember_path`, `resolve_trace_path`, and the `compose_recall`
deterministic round-trip are all deleted. Singular implementation: **no
aliases, no shims** — a host holding a stale manifest gets tool-not-found on
the dead verbs until it reconnects (ADR-533 §13 made us honest about
volatility; CONNECTING.md §"The surface changed" documents the human step).

## 5. D4 — Presentation roster follows the verb roster (ADR-533 D4)

- `file-header` (open) and `save-receipt` (save) survive unchanged.
- `trace-timeline` → `history-timeline`; `recall-cards` → `search-results`
  (widget dirs + `build.mjs` roster + `presentation/registry.py` +
  `affordances.py`).
- `remember-receipt` is deleted.
- `list` ships text-first; its affordance entry (even if text-only) must exist
  so the ADR-533 D4 roster-coverage gate stays a real gate.

## 6. D5 — Documentation re-cut (the cleanup half)

The memory vocabulary is swept from every operator- and host-facing doc:

- `docs/features/mcp/` — all 8: `README.md`, `tool-contracts.md`,
  `workflows.md`, `architecture.md`, `CONNECTING.md`, `SUBMISSION.md`,
  `honest-state-contract.md` (the `captured → remembered` status vocabulary
  re-cuts to save's file-native receipt), `presentation.md`.
- `docs/architecture/GLOSSARY.md` — the Rung-0 activation-ladder entry names
  "`remember`/`recall`/`trace` + connectors + files" as the substrate wedge;
  re-word to the file-native roster.
- `CLAUDE.md` — the MCP Server + MCP Composition rows still describe the
  ADR-169 surface (`work_on_this` / `pull_context` / `remember_this`,
  `classify_memory_target`); both rows re-cut to this ADR.
- `docs/architecture/ADR-LEDGER.md` — absorb this ADR; status banners on
  ADR-368 (superseded at the verb layer) and a pointer on ADR-376 §5.
- Server-side prose: `_INTEROP_VERBS`, `_build_interop_instructions()`, every
  tool docstring — one ontology throughout.

## 7. What does NOT change

OAuth/auth (ADR-075/531), grants + member provisioning (ADR-386/431),
attribution (`yarnnn:mcp:{client}`, ADR-288), the ADR-307 consequential gate,
the presentation adapter mechanics (ADR-533 D4 hosts/adapters), the retired
derive wake (ADR-428), export (ADR-510), `share` (ADR-513/517/534/537), and
the internal primitive registry — the kernel is untouched; this ADR moves the
*binding* onto it.

## 8. Implementation scope (phased)

1. **Verb re-cut** — `api/mcp_server/server.py` (roster, tool defs,
   instructions), `api/services/mcp_composition.py` (`compose_list` NEW,
   `compose_search` from `compose_recall` minus round-trip, `compose_history`
   from `compose_trace` minus fetch-key machinery; delete the D3 list).
2. **Presentation + widgets** — registry/affordances re-cut; widget dirs
   renamed/deleted/built (`api/mcp_server/widgets/`).
3. **Tests** — retire `test_adr368_memory_surface.py` into
   `test_adr543_file_native_surface.py`; extend `test_adr512_{open,save}_verb`
   siblings for `list`/`search`/`history`; update
   `test_adr533_participant_contract.py`; sweep the ~10 other test files that
   reference the old names.
4. **Docs sweep** — §6 in full, same arc as the code (doc-first where the doc
   is canon).
5. **Deploy + probe** — Render deploy of yarnnn-mcp-server; reconnect a live
   host; drive the six verbs from an external principal (the E2E closed loop —
   this repo's own MCP connection is the test rig). The click-pass criterion:
   an external principal can *enumerate* the tree it previously had to infer.

## 9. Risks, named

- **Stale-manifest breakage is chosen, not accidental** — dead verbs 404 for
  connected hosts until reconnect. Acceptable under singular-implementation
  discipline; CONNECTING.md carries the step.
- **ChatGPT app submission** (SUBMISSION.md) references tool names —
  renaming the surface may require resubmission; check before the deploy
  phase.
- **`search` quality inherits `recall`'s** — the round-trip deletion removes
  the save-then-recall determinism crutch; the naturalized-subject fuzzy path
  must carry alone. The old Finding-1 regression case re-runs as a
  search-by-meaning case against a file saved via `save`.
