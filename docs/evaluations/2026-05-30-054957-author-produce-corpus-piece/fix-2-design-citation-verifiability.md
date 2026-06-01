# Fix 2 design — Citation-Verifiability Rule (substrate-honest redesign)

**Date**: 2026-06-01
**Hat**: A (system fix — lands in alpha-author `principles.md` + spec) with the redesign rationale (Hat-B) alongside.
**Status**: DESIGN + implementation this session.
**Addresses**: `findings.md` §2 + `findings-p6-fix-validation.md` §2 (completing audit approves fabricated citations).

> **Operator decision (2026-06-01)**: proceed, shape = **verifiability-gate → defer**.

---

## Why the PRIOR Fix 2 was wrong (substrate-reality check)

The parent `findings.md` §2 recommended: *"pre-ship: every cited ADR/file ref must resolve to a real file matching the claim."* Before writing it, I checked the substrate: **the alpha-author workspace has ZERO ADR files** (`0` of 67 workspace_files). The Reviewer cannot resolve `ADR-254` against `docs/adr/` — that corpus is not in the workspace, and it *shouldn't* be (alpha-author is an operation about *authoring YARNNN content*; the ADR corpus is a fact about the *piece's subject*, not the operation's substrate).

So "resolve every ADR ref against the real corpus" is **unenforceable** — a rule that looks like a fix but can never fire, creating false confidence the audit checks citations. Worse than no rule.

**The honest reframe**: the Reviewer reasons against *workspace substrate*. It cannot verify a citation is *correct* without the corpus. What it CAN do is recognize an **unverifiable load-bearing claim** and refuse to bless it — routing verification to the one party who can do it (the operator). That is the verifiability-gate shape.

---

## The rule (four-field shape, §1 pre-ship audit path)

### Rule: citation-verifiability

- **Substrate read**: the draft's prose + `profile.md` Continuity Threads, scanned for external factual references — claims of the form "ADR-NNN says/does X", file-path references (`docs/...`, `api/...`), and external URLs (`github.com/...`, etc.) — AND the workspace substrate the Reviewer can actually read (`/workspace/**`).
- **Pass condition**: every external factual reference is EITHER (a) traceable to workspace substrate the Reviewer can read and confirm, OR (b) not load-bearing to the piece's thesis (decorative mention). A piece with zero external factual references passes trivially.
- **Verdict on fail**: `defer` with directive. When the piece rests on external references the Reviewer cannot verify from workspace substrate (the typical case: ADR citations, github URLs — the workspace has no ADR corpus), the directive names them and asks the operator to confirm each resolves to a real source matching the claim before ship. *"This piece's thesis rests on N external references (ADR-209, ADR-254, ...) and M URLs I cannot verify from workspace substrate. Confirm each resolves to a real source whose content matches the claim — or revise. I will not bless an unverified citation as architecture-grounded."* Additionally `reject` (not defer) when the references are **internally inconsistent** (e.g., "five live ADRs" followed by a list of seven — a self-contradiction visible without the corpus) or use an **invented path shape** that contradicts a convention the workspace declares.

**Why defer, not reject, for the unverifiable case**: the Reviewer's epistemic limit is real — it genuinely cannot tell a correct citation from a plausible-but-wrong one without the corpus. `reject` would punish correct citations it merely can't see; `defer` correctly says "I can't verify this; the operator can." This is the honest verdict for an epistemic-limit gate. The internal-inconsistency case IS rejectable because that contradiction is visible from the draft alone.

**Relationship to `_editorial.md` #3** ("architecture-grounded over speculation — every claim grounded in shipped ADRs"): that editorial principle is the *intent*; this rule is its *enforcement at the Reviewer's actual epistemic boundary*. The Reviewer can't confirm grounding it can't read — so it gates rather than rubber-stamps.

---

## Substrate drift discovered (out of scope, banked for separate sync)

While checking the live workspace's `principles.md`, found it is an **OLDER fork (148 lines)** that predates the 2026-05-29 persona-frame-collapse migration — it LACKS the bundle's (192-line) §0 (Clarify posture) and §3.5 (self-amendment/anti-patterns/independence) sections, and still points reasoning-posture at the persona-frame `_compute_*` sections (the pre-collapse model).

**This is NOT fixed here** — re-syncing the whole file would conflate a citation-rule addition with a persona-frame-collapse migration (two unrelated changes; Singular-Implementation discipline says keep them separate). The citation rule is added surgically to **§1 in both** the bundle and the live copy, so it lands regardless of the §0/§3.5 drift. The full live-vs-bundle principles.md re-sync is a **separate follow-up** (banked here; a future session should re-fork the live principles.md to the post-collapse bundle shape).

---

## Validation plan

Re-fire the moat pre-ship-audit (autonomy=autonomous, audit completes per Fix 1). Expected: the audit now **DEFERS** (not approves) on the moat-thesis, citing the 7 unverifiable ADR references + the invented github URLs, with the operator-confirm directive. Receipt = a judgment_log verdict with `defer` + the citation directive, and (under autonomous) the piece does NOT auto-ship. This is the "catch" the §2 question asked for — and the clean contrast with the prior APPROVE.
