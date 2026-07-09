# ADR-424: The Pure-OS Filesystem Model — One Home Directory, No Privileged Roots, for Every Participant

**Status**: Accepted (2026-07-09, operator-ratified — "scope is right"; D3 line confirmed: parameterize `conventions.py` + peer capability + envelope collapse now, full program-relocation deferred). Doc-first; the code lands phased under it (D5.cascade). A Substrate + Identity ADR that finishes a migration already underway: the workspace filesystem is a **home directory** every participant shares, with **no privileged kernel "work root"** and **no per-envelope root enumeration**. It is a **subtraction** — removing the specificity that four envelopes still hardcode inconsistently — toward the deferral precedent two envelopes already set (`_workspace_guide.md`, ADR-280/281/323). It ratifies the peer-folder capability the Files-model note established and removes the one rule (`lane_runner.py` "Never invent new top-level directories") that directly forbids it.
**Date**: 2026-07-09
**Dimension**: Substrate (Axiom 1 — how the filesystem is named + presented) + Identity (Axiom 2 — the model is identical for every participant: operator, Freddie, hired agents, external LLMs)
**Relates to**: the Files-model note (`docs/analysis/the-files-model-directory-is-meaning-everything-else-is-metadata-2026-07-08.md` — the axiom this makes participant-facing) + ADR-422/423 + the Documents/Downloads reshape (the operator-facing half; this is the participant-facing half); ADR-384 (the re-founding — meaning-folders + permission-as-metadata; this is its envelope/participant consequence); ADR-280/281/323 (the `_workspace_guide.md` deferral + the persona-frame collapse — the precedent this extends); ADR-320 (the topology lock — PRESERVED as the permission mechanism, but no longer the *taught mental model*); ADR-414 (Altitude-3 hires own `agents/{slug}/` homes — reconciled: a program is a participant that writes into homes + keeps its internals in its own home)
**Amends**: the four inline root-enumerations (`freddie_agent.py` frame, `primitives/workspace.py` tool descriptions, `dispatch_specialist.py` frame, `lane_runner.py` hands frame) — each replaced by the one home-directory model; `conventions.py` (the `operation/`-hardcoded builders — parameterized to a home, default preserved); the operator-facing labels already shipped (Documents/Downloads)
**Preserves**: ADR-320 permission topology (the gate is UNCHANGED — permission still derives from the path root; this ADR changes what participants are *told*, not what the gate *enforces*); ADR-286 single-writer; ADR-209 attribution; the systematic write homes (program output still has a definite home — see D3); the external MCP surface (already pure — see D5)

---

## 1. Context — a migration half-done, and an inconsistency it left

The operator's direction (2026-07-09): *think in pure OS terms.* On a real machine there is no privileged "app work root" that is a peer of `~/Documents`; every participant — you, another user, an app, a daemon — writes into one filesystem by **path** (meaning), governed by **permission** (a grant) and **attribution** (who did it). The path is just meaning; specialness is a category error.

A full-repo evaluation (2026-07-09, envelope-by-envelope — the method was *evaluate current state, do not presume change*) found that YARNNN has **already been moving this way**, but stopped halfway:

- **Already pure (subtraction already done):** Freddie's cockpit block and the headless base prompt had their inline filesystem topology **deleted** (ADR-281/323) and now **defer to one per-workspace data file**, `/workspace/_workspace_guide.md` (read at every wake). The kernel system prompt no longer teaches paths. This is the pure-OS pattern, already precedent.
- **Already pure (nothing to change):** the **external MCP surface teaches no filesystem model at all** — the server instructions + `remember`/`recall`/`trace` docstrings are pure "durable memory, three verbs"; no roots, no `operation/`, no `inbound/`. Per the operator's correction (*the envelope shouldn't be about specificity*), this is **correct as-is** — the external model writes by meaning through the verbs; it is told nothing privileged. **D5: no change.**
- **NOT yet pure (the inconsistency):** **four** envelopes still each re-author their own root enumeration inline, and *they disagree*:
  - `agents/freddie_agent.py` `_compute_minimal_frame` (5 roots, omits `contract/`),
  - `services/primitives/workspace.py` tool descriptions — "the five roots" in 5 places (the most-reused copy: every LLM that gets the file primitives reads it),
  - `services/primitives/dispatch_specialist.py` `_SPECIALIST_FRAME` ("your output goes to `operation/reports/{slug}/`"),
  - `services/lane_runner.py` `_CONVENTIONS_FRAME` (`operation/` + `memory/` + `uploads/` + 4 roots — a *different* set, and the one that says **"Never invent new top-level directories"**).

None agree on `contract/` or `memory/`. This is four sources of truth for one filesystem model — the exact "lingering ambiguity" the singular-implementation discipline exists to prevent.

## 2. The decision in one sentence

**The workspace filesystem is a home directory (`~`) presented to every participant through ONE model — Documents (the authored-work home), Downloads (arrivals), and operator/AI-authored peer folders, all at the root; permission is a grant, attribution is who, path is meaning — and no participant's envelope enumerates kernel roots or names a privileged "work root"; the four inline enumerations collapse to the one shared model (the `_workspace_guide.md` deferral precedent, extended), the external surface stays pure, and the gate is unchanged.**

## 3. Decisions

### D1 — One home-directory model, authored once, referenced everywhere

The filesystem mental model is stated **once** — as the pure-OS home directory — and every participant that needs it references that one statement rather than re-authoring a root list. The home model:

- **`~` is the workspace root.** A flat namespace of *homes*.
- **Documents** — the system-provided home for authored work with no more specific home (the path formerly `operation/`; the label already shipped). Not a privileged kernel root; the *default* home, the way `~/Documents` is a default, not a container.
- **Downloads** — the system-provided home for what arrived (uploads + MCP/connector intake; `revision_kind='observation'` badges an arrival).
- **Peer folders** — operator- OR AI-authored top-level folders (`the-acme-deal/`), peers of Documents, writable by every participant the grant permits (already true; D2).
- **System files** — kernel residue (governance/system/persona/…), present but folded away; not part of the participant's working model.
- **The rule:** write by meaning (path); the grant says whether you may; attribution says you did. **No participant is told "your work goes to root X."**

The singular home for this prose is the extension of the existing deferral target. Two candidate implementations (decided at build time, D6-deferred): (i) a kernel constant the four envelopes import instead of hand-authoring (the `DP33` "collapse to data" move), or (ii) extend the `_workspace_guide.md` deferral to the four remaining envelopes. The evaluation prefers **a kernel constant** for the kernel-universal model (Documents/Downloads/peers/grant/attribution is true on *every* workspace, so it is a constant, not per-workspace data — DP33), with `_workspace_guide.md` continuing to carry *program-specific* substrate structure on top.

### D2 — Peer folders are ratified; the "never invent directories" rule is removed

The Files-model note established (verified in substrate) that an unknown top-level root is **writable by every caller** (the gate lists *locked* prefixes; an unmapped root falls through) and **renders as a peer of Documents** (the `root_metadata` fallback → `work` zone). This ADR **ratifies** that as intended, not incidental: **any participant the grant permits may create a top-level peer folder by writing a file into it** — the OS model (you don't ask permission to `mkdir ~/projects`).

`services/lane_runner.py:175`'s **"Never invent new top-level directories"** is **removed** — it directly contradicts the peer-folder model (it was a single-principal-era guard). A lane hand, like any participant, may file work into a meaning-named peer folder within its grant.

### D3 — Program output has a home; it is not a privileged root

Reconciling with ADR-414 (a program is an Altitude-3 hire): a program is a **participant**, and like any participant it writes in two places —

- its **work product** (reports, authored pieces, domain context *about the operator's things*) belongs in the **operator's homes** — Documents or a peer folder (`the-acme-deal/`), by meaning, and
- its **own internals** (its persona, principles, judgment log, dials) live in **its own home**, `agents/{slug}/` (ADR-414) — the app's `~/Library/{app}` equivalent.

`operation/` was the single-principal era's "the one program's work root." In the home model it is **just the Documents home** (authored work with no more specific home). `services/conventions.py`'s builders are **parameterized to a `home` argument, default `operation`** (byte-identical for every current caller — one resolver, not a parallel set), so a workflow *can* target a peer home when its work has a more specific meaning-home, while the default stays. **Domain-derivation + ground-truth keying stay on the Documents home this pass** (a program's structured domain tree is coherent there); relocating a whole program's domain/ground-truth into an arbitrary peer is the ADR-414-adjacent follow-on (D6), not this ADR — it collides with the `agents/{slug}/` home direction and needs its own reconciliation.

### D4 — The four inline enumerations collapse to the one model

Each of the four is edited to **stop enumerating kernel roots** and instead carry the home model (D1):

- **`primitives/workspace.py` tool descriptions** (the most-reused, the one every file-primitive LLM reads): the "five roots" enumeration + the `operation/{domain}/` worked examples become the home model — write by meaning; Documents is the default authored home; the grant governs; do not hand-author into System files. No root list.
- **`freddie_agent.py` frame**: the topological write-boundary sentence stays *as a permission fact* (the gate is real) but reframes to "you write by meaning; the grant locks System files + the governance dials; everything else is yours" — no five-root recital.
- **`dispatch_specialist.py`**: "your output goes to `operation/reports/{slug}/`" → "write your output into the home the brief names (Documents by default; a peer folder when the brief gives one)" — the brief carries the concrete path (it already does), the frame stops privileging `operation/`.
- **`lane_runner.py` hands**: the divergent `operation/`+`memory/`+`uploads/` list → the one home model; the "never invent directories" rule removed (D2).

### D5 — The external MCP surface stays pure (no change)

The external LLM is told nothing about the filesystem today (three verbs, "durable memory"). Per the operator's correction, that is **already the pure-OS end state** for the external surface — it writes by meaning through `remember`, the placement/derive machinery is internal, and telling it about roots would *add* specificity, the opposite of this ADR. **Explicitly: no change to `mcp_server/` or the verb docstrings.** (Should the ADR-311 raw-primitive interop ever wire WriteFile over MCP, it inherits the D1 model like any participant — but that is not this ADR.)

### D6 — Named out of scope (the follow-ons)

- **The peer-folder create *affordances*** — an operator "New Folder" at the root (Files surface) + confirming/guiding agent+chat peer writes. Small, already-permitted; ships **under** this ADR once the model is ratified (it is the concrete capability the model authorizes).
- **Full program relocation** — parameterizing `extract_domain_from_path` + ground-truth keying + compose so a program's *entire* domain/outcome tree can live in an arbitrary peer. Collides with ADR-414's `agents/{slug}/` homes; needs its own reconciliation. Deferred.
- **The `_workspace_guide.md` prose** (bundle-authored, outside `api/`) — if D1 lands as a kernel constant, the bundle guides drop their root-topology prose and keep only program-specific structure. A bundle-doc pass, sequenced after the kernel constant.

## 4. What this does NOT do

- **No gate change.** ADR-320's `_is_path_locked` is untouched — permission still derives from the path root. This ADR changes what participants are *told*, not what the gate *enforces*. (Documents = `operation/` at the path level; the label is display + prose, the path is the same.)
- **No substrate move.** `operation/` stays the canonical path; "Documents" is its participant-facing name. No file relocates.
- **No new privileged root.** The opposite — it removes the privilege `operation/` carried in the prose.
- **No external-surface change** (D5).
- **No program-relocation** (D6).

## 5. Cascade / blast radius (when the code lands, phased under this ADR)

- **Kernel model constant** (D1): a new singular home-model string (or the extension of the guide deferral).
- **Four envelope edits** (D4): `primitives/workspace.py` (tool descriptions — carries `api/prompts/CHANGELOG.md` per the Prompt Change Protocol), `freddie_agent.py`, `dispatch_specialist.py`, `lane_runner.py`. Each: remove the root enumeration, reference the model. Coherence tests + a Hat-B eval on Freddie's frame (the envelope shrink must hold the sentinels).
- **`conventions.py`** (D3): `home` parameter, default `operation`, byte-identical for 19 callers.
- **`lane_runner.py`** (D2): remove "never invent directories."
- **Docs**: this ADR; the Files-model note (participant-facing half added); CLAUDE.md (the four-source→one-model note); GLOSSARY (Documents/Downloads/peer-folder terms).
- **Gate**: a source-guard that no envelope enumerates kernel roots (the singular-model ratchet — the anti-drift guard); `tsc`/pytest.

## 6. Why doc-first, and why subtraction

This is doc-first per repo discipline: it touches four LLM-facing envelopes + the write-home convention + Freddie's frame at once, and the Prompt Change Protocol requires the model change be recorded and evaluated, not slipped in. And it is deliberately framed as **subtraction**: the pure-OS model is *less* special-casing, not more — the win is that four disagreeing root lists become one home model (or zero, deferring to the shared source), the external surface that was already pure stays pure, and the gate that already works is untouched. The operator's correction — *the envelope shouldn't be about specificity* — is the whole thesis: the participant is told how the home directory works once, generically, and writes by meaning like any actor on any OS.
