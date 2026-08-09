# Session handoff — 2026-08-09

`origin/main` @ `d99dbf8`. Working tree clean, local in sync with remote.
All ADR-538 gates PASS; `next build` clean.

## Shipped this session

**ADR-538 — a block is classified by what it cites** (`d99dbf8`).
Opened as a service-model discourse (what IS the core flow for Docs/Studio),
landed as a substrate ruling. The operator's prompt was a Claude Design
artifact beside our own deck: *"mostly flat, or images, or svgs… I notice that
there are dynamic and animated."*

- **D1** — a block is classified by **what it CITES and what DRAWS it**, never
  by how it looks. `data` cites a SOURCE and is projected · `media` cites a
  PICTURE · `content` cites nothing. The groups were a topic label; now a rule
  with a diagnostic.
- **D2** — `chart` was the flatness. Filed `data` while citing
  `./assets/chart.svg` (a photograph of data) **and** sitting in
  `MEDIA_BLOCK_KINDS` — the registry confessing what the label denied. Now
  cites a `.csv`, drawn by `csvToChartHtml` beside `csvToTableHtml`. The FE
  insert door had it worse: picking "Chart" **seeded the chat** to author an
  SVG, at two sites. Deleted; chart joins `PICKER_KINDS`.
  (`metrics` re-filed `data`→`content` in the same motion — the gate caught it.)
- **D3/D4** — a `component` kind (the composed card) and the kernel's **first
  motion**, declarative-only, opt-in behind `data-motion`, under a
  `prefers-reduced-motion` guard. Kernel CSS **15 → 16**.

`test_adr538_block_classification.py` **59/59**, 3 falsifiers executed.

## ⚠️ OWED

1. **The ADR-538 click-pass.** Gates prove the room, not the doorway.
   - In **Studio**: `/` → **Chart** must open the **CSV picker** (not seed the
     chat). Pick a CSV → the chart draws. Insert a **Component**.
   - **There are no CSVs in the live workspace** (0 at audit) — upload one
     first, or the picker correctly shows "No CSV files in the workspace yet."
   - Confirm a `data-motion` element animates in a **share view** (`sandbox=""`).
2. **Two inherited click-passes**, still owed: ADR-536 (align/indent — SINGLE
   caret; it withdraws over a multi-block range by design) and ADR-537 (the
   share sheet's two tabs, reuse-first link, Revoke).
3. **Unexplained: OAuth state error on prod** (carried from 2026-08-08).
   `…/settings?provider=notion&status=error&error=Invalid+or+expired+OAuth+state&docs.file=…`
   An OAuth callback and a docs-file address collided in one URL. ADR-531
   territory. **Not investigated.**

## Notes for whoever picks this up

- **The studio-era gate baseline is RED**: 15 gates fail at `main` and failed
  identically before ADR-538 (verified by stashing). Do not read "the suite is
  failing" as a signal — measure the **delta** by stashing only your paths.
- **ADR-453 has one pre-existing failure** (`valid_applies` is stale since
  ADR-525's `block-staged`/`block-flow`). Deliberately NOT fixed inside ADR-538
  — repairing it silently in an unrelated commit would hide a real debt.
- **The next honest question** is `metrics` citing a **cell**: a headline number
  as a defensible attributed claim. It needs **sub-file addressing**, which the
  substrate does not have (ADR-528's finding). Named in ADR-538 §D1, not
  smuggled in — it wants its own ADR.
- Falsifier 2 in ADR-538 is a live bet: **0 artifacts cite a `.csv` today**. If
  none do a quarter from now, `chart` should honestly re-merge into `media`.
