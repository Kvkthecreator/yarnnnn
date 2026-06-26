# The ledger-intake axiom: raw observation vs derived substrate

**Date**: 2026-06-26
**Hat**: B (external developer of the system — analysis + a candidate axiom for ratification). No canon edit in this doc; it is the discourse base a FOUNDATIONS amendment + conforming ADRs would cite.
**Status**: Proposed axiom for operator (KVK) ratification. System-wide, not MCP-scoped.
**Spine**: the **ledger** rung of [the three-rung framework](the-three-rung-framework-and-the-multi-principal-wedge-2026-06-26.md) — this doc supplies that rung's *missing invariant*. The `uploads/` precedent and ADR-330 ground-truth intake are the two paths that already obey it (receipts in §3).
**Supersedes**: the MCP-scoped predecessor `mcp-raw-intake-vs-processed-substrate-2026-06-26.md` (same finding, one altitude too low — kept only as the worked MCP instance, §5).
**Receipts**: all intake-path claims verified against the live repo 2026-06-26 (`mcp_composition.py`, `track_web_sources.py`, `outcomes/reconciler.py`, `workspace_paths.py`, `directory_registry.py`). Cited inline.

**Origin**: KVK, after the MCP raw-vs-processed discussion, escalated the premise: *"if this needs to be more axiomatic and system-wide (not just MCP but the actual service) — fundamentally defining our way of context-in handling at large. The approach should be axiomatic and almost too simple; that straightforwardness, almost dull, may be the winning solution that blankets the wide-reaching scope and future-proofs."* And: *"rewrite system-wide, then re-group to see if the current files-to-directory handling is right — we may need to revisit the pure `operation/memory/` approach (or not)."*

---

## 1. The axiom (stated as plainly and dully as possible)

> **Every contribution to the substrate enters as an attributed raw observation. What the workspace makes of it is a separate, attributed, derived act. The raw is never rewritten; the derived always cites its source.**

Two clauses. It names no transport (MCP, connector, upload, web, A2A), no format, no principal, no the-Reviewer-specifically. It is a statement about **how reality enters the kernel** — the altitude of FOUNDATIONS Axiom 1 (substrate) and the perception field (DP27). It is, almost exactly, ADR-330's outcome-attestation discipline **generalized from outcomes to all context-in**.

The dullness is the design. KVK's intuition is correct and worth making explicit: a rule this simple **blankets the entire context-in surface with one shape**, which is precisely why it future-proofs — it has no opinion about what is entering or who is sending it, so new transports, formats, and principals inherit it for free.

### Why this is the ledger's *missing* invariant (the reconciliation with the three-rung doc)

The three-rung framework names Rung 1 "git minus branches": content-addressed (`workspace_blobs` by sha256), parent-pointered (`workspace_file_versions`), attributed (`authored_by` + `message`, required, single write path). All true. But it omits one git property the ledger does **not** yet have:

**In git, a commit never silently overwrites what it records.** The raw object is immutable; derived state (a working tree, a merge result) is a *separate* object that points back to its inputs. You can always recover *what was committed* distinct from *what was made of it*.

YARNNN's ledger has attribution but **not** the raw/derived separation. When the Reviewer "places" an MCP dump by rewriting it in place, the head revision becomes `reviewer:ai` and the foreign origin is demoted to a parent-pointer — recoverable, but no longer the object's identity. The axiom adds the one git property the ledger is missing. Its payoff is the moat claim made *literally* true at the data layer: the three-rung doc's moat sentence —

> *"which principal — human, agent, platform, or foreign model — contributed each version, and how the seat reconciled them"*

— is only **approximately** true today (via in-place edit history). Under the axiom it is **structurally** true: the raw observation is one object (the contributor's), the reconciliation is another (the seat's), and `trace` walks the citation between them. **The axiom is what turns the ledger's headline property from "approximately legible" to "structurally legible."**

### Why it is the substrate twin of the multi-principal model

The three-rung doc's D2 made one dull simplification for *principals*: **"one model; the principal count is data."** Personal is N=1; team is N humans; platform-only is 0 humans + K platforms. One model, parameterized.

This axiom is the same move for *intake*: **one intake model; the source is data.** MCP-from-claude.ai, Slack-sync, a human upload, a web watch, an A2A agent payload, a CSV of outcomes — all are *a principal writing a raw observation into the commons*. One mechanism (land raw, attributed, immutable → derive processed, attributed, citing), parameterized by principal and transport. The two axioms are siblings: **authorization is per-principal (D4); intake is per-observation (this doc); both collapse an N-shaped problem into one shape where N is data.**

---

## 2. What "context-in" actually is, system-wide (not just MCP)

The premise expansion KVK asked for. Context enters the substrate through **six** transports today (with A2A spec'd as the seventh). Each is a principal contributing an observation:

| Transport | Principal | What enters | Service or MCP |
|---|---|---|---|
| MCP `remember` | foreign LLM (`yarnnn:mcp:claude.ai`) | a text claim | MCP |
| Platform connectors | platform (`platform:slack`, `platform:notion`) | synced messages/pages | **service** |
| Human upload | operator (`operator`) | PDFs/docs/images | service (`uploads/`) |
| Web/RSS watch (ADR-335/336) | system transport (`system:track-web-sources`) | fetched web content | service (perception) |
| Ground-truth intake (ADR-330) | platform/operator/agent (attested) | outcome events | service |
| Chat (addressed) | operator (`operator`) | typed messages | service |
| *A2A (spec'd, ADR-370-auth D3)* | *agent (`a2a:<id>`)* | *structured payloads* | *MCP/direct* |

KVK's point lands here: **MCP is one of seven.** An intake discipline that lives only in the MCP layer is a discipline in the wrong place. The axiom must govern the *ledger*, and every transport conforms to it — which is exactly the "system-wide, not just MCP" altitude.

---

## 3. The audit: is the current directory handling right? (the receipt that proves the axiom is real)

This is the "re-group to see if the files-to-directory handling is right" task. I tested all four substrate-writing intake paths against the axiom. **The result is the strongest possible evidence the axiom is load-bearing: two paths already obey it and are clean; two violate it and exhibit exactly the predicted symptoms.**

| Path | Raw lands where | Derived lands where | Obeys axiom? | Symptom if not |
|---|---|---|---|---|
| **Uploads** (human) | `uploads/{file}` — immutable, `managed_by: user`, agent-unmanaged, outside the topology cut ([workspace_paths.py:46–48](../../api/services/workspace_paths.py#L46)) | reasoned-against; never rewritten | ✅ **clean** | — |
| **Ground-truth** (ADR-330) | raw outcome events (attested `platform\|operator\|agent`) | `operation/{domain}/_money_truth.md`, *regenerated* by the reconciler ([reconciler.py:8](../../api/services/outcomes/reconciler.py#L8)) | ✅ **clean** | — |
| **MCP `remember`** | `operation/memory/{slug}.md` ([mcp_composition.py:240](../../api/services/mcp_composition.py#L240)) | *the same file, rewritten in place* by the placement wake ([mcp_composition.py:514](../../api/services/mcp_composition.py#L514), ADR-368 D5) | ❌ **conflated** | provenance muddied — head is `reviewer:ai`, foreign origin demoted to a parent-pointer; `trace`'s cross-principal story is approximate, not structural |
| **Web/RSS watch** (ADR-335/336) | **nothing** — the fetch happens, only the *distilled signal* `_watch_signal.yaml` is written ([track_web_sources.py:13–14, 152](../../api/services/primitives/track_web_sources.py#L13)) | `_watch_signal.yaml` | ❌ **raw discarded** | no source of record at all — you can never `trace` *why* a signal said what it said; the observation that drove a judgment is gone |

### Reading the audit

- **The two clean paths are not coincidence — they are the axiom already discovered twice.** `uploads/` (the human raw lane) and ground-truth reconciliation (the attested raw→folded lane) each independently arrived at "keep the raw, derive separately." The system *already believes this* in the two places it thought hardest about intake. The axiom is just naming what those two paths share and demanding the other transports match.
- **The two violations have *different* failure modes, both bad:** MCP **conflates** (raw becomes the derived object, identity lost on rewrite); perception **discards** (raw never persists, so the derived signal is unfalsifiable — you cannot audit a watch). Under the axiom, both are fixed by the *same* rule: persist the raw observation, attributed, immutably; derive separately, citing.
- **So the answer to "is the directory handling right?" is: no, and specifically in the two places the axiom is violated.** It is right where the axiom is (already) obeyed.

---

## 4. The `operation/memory/` re-examination (KVK: "revisit the pure operation/memory approach, or not")

Direct answer: **`operation/memory/` is the wrong shape under the axiom — not because the *location* is bad, but because it is a single namespace doing two jobs.**

Today `operation/memory/{slug}.md` is **both**:
1. the **raw inbox** where the foreign dump lands (capture), AND
2. sometimes the **derived home** where the Reviewer decides the memory belongs (when placement is "leave in inbox").

The axiom forbids one namespace being both. A raw lane must be immutable and source-attributed; a derived home is rewritten and seat-attributed. `operation/memory/` is being asked to be both at once, which is exactly why the placement step has to *rewrite in place* — there is nowhere else for the derived object to go.

### The shape the axiom implies (and its reconciliation with the topology)

A **raw observation lane** distinct from **derived substrate**, system-wide:

- **Raw lane** — one home for *all* attributed raw observations, regardless of transport. Candidate name: an **`inbound/`** root (machine-and-external-contributed), sibling to `uploads/` (human-contributed) — both *outside* the constitution/operation/governance topology cut, both immutable-at-the-raw-layer, both reasoned-against. Structure: `inbound/{transport}/{principal}/{timestamp}-{slug}.{ext}` — e.g. `inbound/mcp/claude.ai/2026-06-26-acme-corp.md`, `inbound/slack/general/...`, `inbound/web/{source}/...`. Append-only. `authored_by` = the contributing principal. **This is the source of record.**
  - Note the elegant consequence: **`uploads/` becomes the N=human case of `inbound/`.** Human upload and machine observation are the same kind of thing (raw contributed reference material) differing only in principal — the *exact* "one model, the source is data" collapse the axiom predicts. Whether to literally merge `uploads/` into `inbound/uploads/` or keep them as siblings is a §6 open question; the *model* unifies them either way.
- **Derived substrate** — the workspace's understanding, in `operation/` (and the program's structured tree). Written by the seat (or a derive step), `authored_by` = `reviewer:ai` / `system:<deriver>`, **citing** the raw observation it derived from. This is where placement-by-judgment writes its result — but now it *writes a new citing object* instead of *rewriting the raw dump*.

### Why `inbound/` and not "just fix operation/memory/"

Because the axiom is system-wide, the raw lane must serve *all seven transports*, not just MCP. `operation/memory/` is an MCP-shaped name in an operation-shaped root. `inbound/` (or `observations/`) is transport-neutral and principal-organized — it can hold the Slack sync, the web watch's fetched content, the A2A payload, and the MCP dump under one disciplined namespace. **Revisiting `operation/memory/` is not a local rename; it is replacing an MCP-special-case with the general raw lane the axiom requires.** That is the "re-group the directory handling" KVK asked for, done at the right altitude.

### The honest "or not" (where the axiom might over-reach)

KVK left the door open ("or not"), so the counter-case, fairly stated:
- **Ground-truth doesn't use a file-based raw lane** — it folds raw *events* (DB-shaped, attested) into a summary file. So "raw observation" is sometimes a *row*, not a *file*. The axiom should say **raw is retained and attributed**, not **raw is always a file in `inbound/`**. The lane is the *common case* (unstructured contributions); structured attested intake (outcomes) may keep its event-row raw form. The axiom governs the *invariant* (retain + attribute + cite); the *mechanism* (file vs row) is per-transport. This keeps the axiom dull and avoids forcing outcomes into a file lane they don't need.
- **Perception's "discard" might be intentional for high-volume feeds** (you may not want to retain every RSS poll). The axiom's answer: retain the *observations that drove a derived act*, not every byte fetched. A watch that distills 100 articles to one signal should retain the articles it *cited*, not all 100. This bounds the raw lane's growth and keeps it honest (the raw lane is the evidence behind derived acts, not a crawl archive).

So the axiom holds, but its *mechanism clause* is "retain + attribute + cite," not "every transport writes a file to `inbound/`." That nuance is what keeps it dull-but-correct rather than dull-but-wrong.

---

## 5. The MCP instance (the worked example, demoted from spine to example)

The MCP raw-vs-processed case (the predecessor doc) is now **one instance of the axiom**, and a clean one to ship first because the seam is already half-built:

- The per-principal `remember` files (`operation/memory/{slug}.md`) **are already the raw lane** — they just aren't named as one, aren't immutable, and live under the wrong (MCP-special-case) namespace.
- The Reviewer's placement wake **is already the derive step** — it just *rewrites* instead of *citing*.
- The three-rung doc's §7.3 (steward-as-arbiter, closed-by-construction) **depends on this exact separation**: it says contributions stay separate (different paths, per-principal) and the steward merges them into *its own* `reviewer:` revision. **That placed file IS the derived substrate; the per-principal contribution files ARE the raw lane.** The axiom doesn't add a system to §7.3 — it *names the two halves §7.3 already relies on* and makes the raw half immutable.

So MCP conformance is: route raw dumps to `inbound/mcp/{client}/...` (immutable), change the placement wake from *move/rewrite* to *derive-and-cite* into `operation/`, and re-spec `recall`/`trace` to read derived-first with raw-as-citation. This is the smallest first slice and the one with a live test already (commit `4946a45`).

---

## 6. Implications across the architecture (the "totality" — honest cost)

The axiom is constitution-level, so its blast radius is wide but — like the re-key in the three-rung doc — concentrated at seams the architecture already half-cut.

| Surface | Implication |
|---|---|
| **FOUNDATIONS** | A new derived principle (or Axiom 1 clause): *context-in = attributed raw observation; understanding = derived citing act; raw never rewritten*. This is the canon home KVK chose. |
| **Topology (DP25/ADR-320)** | A raw root (`inbound/`) joins `uploads/` outside the constitution/operation cut; `CALLER_WRITE_POLICY` grants each principal-class write to *its own* raw sublane. Small, precedented (uploads already sits there). |
| **All 7 transports** | Each conforms: MCP (rewrite→derive-cite), perception (retain cited observations), connectors (sync lands raw in `inbound/{platform}/`, derive into `operation/`), uploads (already conformant — becomes the human case), ground-truth (already conformant — retains event-rows), chat, A2A. **The conformance is the work; the axiom is the spec.** |
| **`recall`/`trace`** | Read derived-first, raw-as-citation; `trace` walks raw↔derived (the structural cross-principal chain). Re-spec, not rebuild. |
| **Embedding** | Embed the *derived* layer (the understanding is what fuzzy recall ranks); raw is path/citation-addressed (a receipt, not a knowledge object). |
| **Four-flow model (ADR-332/DP26)** | "context-in" finally has a first-class shape — *the raw lane is what context-in writes*; the derive step is the context-in→work boundary. The axiom may be the cleanest formalization of DP26's first flow. |
| **Three-rung framework** | Supplies the ledger rung's missing invariant; makes the moat sentence structurally (not approximately) true; §7.3's steward-merge gains its named two halves. |

**What it does NOT touch / explicitly saves** (the dull-rule dividend): no merge/CRDT (raw lanes are per-principal, single-writer — same saving the three-rung doc claims); no new authorization vocabulary (per-principal grant already covers who-writes-which-raw-sublane); no format engine (raw lane is format-agnostic by construction — the "variety of formats" problem *dissolves* rather than needing a handler). The axiom's simplicity is what produces these savings: a rule that doesn't care what's entering can't generate format-specific or merge-specific machinery.

---

## 7. Recommendation

1. **Ratify the axiom into FOUNDATIONS** (KVK's chosen home) as a derived principle: *the ledger-intake invariant — attributed raw observation in, derived citing act out, raw never rewritten*. State the **invariant** (retain + attribute + cite), not the mechanism (file-vs-row, `inbound/` specifics) — keep it dull and transport-agnostic so all seven transports inherit it.
2. **It is the discourse twin of the three-rung doc's re-key ADR** — sibling axioms (per-observation intake ‖ per-principal authorization), both collapsing N to "N is data." Sequence them together; the re-key ADR's §7.3 arbiter *cites* this axiom as the thing that makes its two halves (raw contributions ‖ derived merge) real.
3. **Conformance is per-transport, sliceable.** The cheapest honest first slice is MCP (§5 — seam half-built, live test exists): route raw to `inbound/mcp/`, derive-and-cite into `operation/`, re-spec `recall`/`trace`. Each other transport conforms as its own follow-on, all against the one ratified invariant. **Audit-driven order**: fix the two *violating* paths (MCP, perception) first — they have symptoms; the two *conformant* paths (uploads, ground-truth) need only be *recognized* as instances, not changed.

---

## Open questions for KVK (before the FOUNDATIONS amendment)

1. **Axiom vs Derived Principle**: does this rise to an Axiom 1 *clause* (it's about how reality enters the substrate — arguably foundational), or a new Derived Principle under Axiom 1? (Lean: DP — it's derived from Axiom 1 + the perception field DP27, not a new primitive truth.)
2. **`inbound/` vs merge into `uploads/`**: one raw root with `uploads/` folded in as the human case (`inbound/uploads/`), or `inbound/` (machine/external) sibling to `uploads/` (human), kept separate for the managed_by line? (Lean: siblings first — least disruption to the shipped `uploads/` semantics — with the *model* unified even if the namespaces aren't.)
3. **The mechanism clause**: confirm the axiom governs "retain + attribute + cite" (invariant) and leaves "file vs event-row" to the transport — so ground-truth keeps its event-row raw form and isn't forced into a file lane. (Lean: yes — this is what keeps it dull-correct.)
4. **Perception retention bound**: retain *cited* observations (the evidence behind a derived act), not every fetched byte. Agreed bound? (Lean: yes — the raw lane is evidence, not a crawl archive.)
5. **Derive-step authorship**: when the seat derives `operation/...` from a raw observation, the citation back to the raw — structured field (a `derived_from: <path>` / revision-id, so `trace` walks it mechanically) or prose? (Lean: structured — it's what makes the multi-stage `trace` chain real, same point as the predecessor doc's Q5.)
