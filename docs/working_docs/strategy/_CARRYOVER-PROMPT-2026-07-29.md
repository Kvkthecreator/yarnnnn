# Carryover prompt — paste into Claude Code at `~/yarnnn`

---

Read `docs/working_docs/strategy/CANON-LOCK-2026-07-29.md` first and in full. It is the operator-ratified source of truth for yarnnn's one-liner, ICP, GTM motion, and activation model as of 2026-07-29. Everything below derives from it. Where any existing doc disagrees with it, the existing doc is wrong.

Supporting context, in this order (read the first two, skim the third and fourth):
- `docs/working_docs/strategy/CANON-ADOPTED-2026-07-29.md` — the reasoning behind the locked hero and its second-order implications
- `docs/working_docs/strategy/GTM-RECUT-PROPOSAL-2026-07-29.md` — the drift ledger: what was stale and why, with ADR citations
- `docs/working_docs/strategy/ICP-ONELINER-DISCOURSE-2026-07-29.md` — the one-liner census and the four axes
- `docs/working_docs/strategy/ONELINER-ICP-GTM-PROPOSAL-2026-07-29.md` — the first proposal; its §2 is superseded by CANON-ADOPTED, the rest stands
- `docs/working_docs/strategy/_DOC-STATUS-INDEX-2026-07-29.md` — status of every file in that folder

## Background you need

`docs/working_docs/strategy/` had zero commits between 2026-06-10 and 2026-07-29 while 168 ADRs landed (ADR-330 → ADR-501). The GTM docs describe a product and a price list that no longer exist. On 2026-07-29 a drift pass applied DOC-STATUS banners to the stale docs (banners only, no rewrites) and locked a new canon. **Your job is to execute the rewrites the banners were holding open.**

The single biggest change: **the ICP inverted.** Every old doc describes a solo operator of a bounded operation. Current canon describes a plural-AI user in a multi-principal commons, where the second principal is usually a second *surface* (an external LLM over the interop face), not a second person.

## Tasks, in order

### 1. `docs/ESSENCE.md` → v17

Two changes, no more:

**(a)** Add a `## The Canon Sentences` section near the top, immediately after Core Thesis, installing the four slots from CANON-LOCK §1 with their audience labels, plus the maintenance rule: *one sentence per slot; a new candidate replaces, never accumulates.*

**(b)** Re-cut `## Canonical Positioning`. It currently still carries the ADR-380 §5 substrate-led lead (*"The authored, portable substrate leads — defended by `trace`"*), which the v16/ADR-457 amendment deliberately left in place pending this pass — see ADR-457 §10.3, deferred item 3. Replace the lead with the locked product sentence and hero. **Preserve** the retired-copy-seeds block below the line for lineage.

Do not touch §The Moat, §The Desk, §What Stays Constant, or the amendment banners. Add a v17 banner in the existing house style, citing CANON-LOCK and ADR-457 §10.3.

### 2. `docs/working_docs/strategy/ICP.md` → new file

Does not exist yet — that is the proximate cause of the drift (the ICP lived as §2 of a positioning doc, so it drifted invisibly). Write it from CANON-LOCK §2:

- The premise: the unit of value is a commons; the unit of arrival is a person (ADR-465: *"a one-member commons is a diary"*)
- The triad — plural · consequential · continuing — with *plural* explained as the load-bearing one
- The three species of second principal, **including the binding honesty rule** that desk agents are the member's hands and are never marketed as colleagues (ADR-460)
- The anti-ICP (the single-AI user), implicit-qualification posture
- A stub section for concrete demographics, marked `OWED — requires founder validation`, listing exactly what must be filled: age, income, company size, AI spend, **which AIs and how many**, tool stack, switch trigger, decision channels
- An `## Update when` clause naming the ADR dimensions that force a re-read: Identity (Axiom 2), Purpose (Axiom 3), Channel (Axiom 6)

### 3. `docs/NARRATIVE.md` → v6

Full re-cut, keeping the six-beat structure. Read the existing DOC-STATUS banner for the beat-by-beat verdict, then:

- **Beat 1** — the ownership hook: *"Every AI keeps its own copy of your work. You don't."* The ratings-agency/self-audit argument moves to Beat 5 as defensibility.
- **Beat 2** — proof of demand: the funded memory-layer category (Mem0/Zep/Cognee) plus the co-work signal.
- **Beat 3** — the product: the locked hero and subhead. **Name verbs and surface categories, never the app roster** (the Dock changed three times in fourteen days; ADR-486's canonical desk sentence names Images, which ADR-488 hid four days later).
- **Beat 4** — the insight, narrowed: *execution commoditizes; the shared, attributed record compounds.* Judgment is the deferred deepening, not the revelation.
- **Beat 5** — the moat, plus the new load-bearing sentence: *the moat turns on with the second principal.* The attribution walk (deck slide 9) is the visual.
- **Beat 6** — the corrected motion per CANON-LOCK §3.1. This explicitly overrules the ratified *"never a volume play"* sentence; say so in the banner rather than editing quietly.

Add a new section the old version lacks: **The honest open question** — the acquisition wedge, per ADR-457 D6, which requires it be named rather than assumed.

**Preserve verbatim**: the bare-capability anti-pattern and the demo-that-requires-tenure anti-pattern. Both are more binding now, not less.

Replace the DOC-STATUS banner with a normal v6 header.

### 4. `docs/working_docs/strategy/GTM_POSITIONING.md` → v5

Keep the section skeleton. Per its own DOC-STATUS banner: replace §1, §2, §5, §6; revise §3 and §4.

- §1 — the locked canon sentences
- §2 — points at `ICP.md`, plus the messaging cut per species
- §3 — act-shape map: keep Artifact/Transaction/Message, **add a row for think → settle**, demote Transaction (it depends on the Rung-2 layer ADR-380 §5 deferred)
- §4 — add the third competitive camp (AI-retrofitted workspaces: Notion/Slack/Google) per CANON-LOCK §3.3
- §5 — motion and pricing per CANON-LOCK §3.1 and §3.5
- §6 — activation per CANON-LOCK §4, pointing at GROWTH-LOOP.md
- §7 — reset open items; seed from CANON-LOCK §9

**Preserve verbatim**: the mechanism discipline and the posture rule in §4 (*never argue capability; differentiate on structure, ownership, accountability*).

### 5. `docs/working_docs/go-to-market/GROWTH-LOOP.md` → new file

Replaces the archived `ACTIVATION_100USERS.md`. Write from CANON-LOCK §4:

- Activated = the first co-work moment (two distinct principals with attributed revisions on the same file)
- Two channels only (ADR-437); **cold discovery leads with the MCP door**, CTA *"Co-work with the AI you already use"*
- The loop diagram: MCP door → the desk → the share link / acquire → retain → expand
- What activation is **not** (no wizard, no constitution, no program pick, no roster, no first-task ceremony)
- Metrics per §4.4, with empty tracking tables — **and a note that the two prior activation plans were written and never run**
- The named build dependency (§4.5): ADR-437 Phase C is now on the critical path, and the connector attach path (ADR-494) must be a sixty-second act or the lead door is aspiration
- The falsifiers per CANON-LOCK §8, **including the correction owed to ADR-457 D8.3** — as written it would fire on success

### 6. `docs/monetization/STRATEGY.md`

Do **not** rewrite. Keep the DOC-STATUS banner. Add one line under it pointing at CANON-LOCK §3.5 for the customer-facing pricing facts.

### 7. Housekeeping

- Update `docs/working_docs/strategy/_DOC-STATUS-INDEX-2026-07-29.md` to reflect the new files and the new statuses.
- Check `README.md` at the repo root — it still says *"an AI Work Platform where deep context understanding enables superior agent supervision"*, which is supervision-era. Update the one-line description to the locked product sentence. Nothing else in the README.
- Grep the repo for the retired phrases in CANON-LOCK §5 and report (do **not** auto-edit) anything you find in `web/` copy or `content/`. That is a separate pass.

## Rules

- **Do not touch any ADR, `docs/architecture/*`, or `docs/adr/*`.** This is a GTM-doc pass. The one exception is §8 below.
- Every claim you write must trace to CANON-LOCK or to a cited ADR. If you find yourself asserting something neither supports, stop and flag it.
- Do not invent numbers. Pricing facts come from CANON-LOCK §3.5 only.
- Keep the existing house style: version banners with dates and ADR citations, `**Supersedes**` / `**Amends**` lines, tables over prose for status.
- Preserve, do not delete, retired-copy blocks — they carry lineage.

## 8. One ADR to draft (do not implement)

Draft `docs/adr/ADR-502-the-interop-principal-invariant.md` as **Proposed**, taking the next free number if 502 is taken. It should state one thing: **an external LLM reaching the commons over the interop face is a first-class principal in the ledger** (`foreign-llm` / `a2a` per ADR-445), and this may not be collapsed into member attribution the way ADR-460 collapsed kernel Agents into *the member's hands*.

Rationale to include: the locked product sentence (*"work with ChatGPT, Gemini, and Claude together"*) and the activation model both depend on this. If it collapses, the claim becomes one principal wearing three faces and the GTM loses its ledger backing. Cite CANON-LOCK §2.2, §7, ADR-445, ADR-460, ADR-465.

Mark it clearly as awaiting operator ratification. Do not change any code or any other ADR.

## When done

1. `git add` the changed and new docs.
2. Commit to `main` with a message in the repo's house style — the log uses lowercase-scoped subjects, e.g. `docs(canon): the one-liner lock — ICP, GTM, and activation re-cut`.
3. `git push origin main`.
4. Report back: files changed, anything in CANON-LOCK you could not honour, and anything you found that contradicts it.
