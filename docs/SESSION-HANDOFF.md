# Session handoff — 2026-08-13 (the data-handling honesty arc, ADR-561 + ADR-563)

`origin/main`. Two ADRs shipped. The operator asked for a marketing audit on
data handling; it surfaced a false *mechanism*, and that fix became ADR-563.

> **Renumbered at close.** This arc's second ADR drafted as 562; a concurrent
> lane (app-owned AI config) had staged **562** first, so mine moved to **563**.
> The lesson is already in canon — *verify the ADR number AT COMMIT TIME*. Note
> the blanket rename briefly rewrote the OTHER lane's CLAUDE.md row; caught and
> restored. When renumbering, scope the sed to your own files.

## 1. What landed

| Commit | What |
|---|---|
| `01c2ccc` | **ADR-561** — four false marketing claims retracted; blob deletion wired into L5; `/privacy-architecture` rebuilt + footer-linked |
| `03d0251` | **ADR-563** — MCP scopes were decorative; three additive tiers enforced at the chokepoint |

## 2. The finding worth carrying

**The engineering was more honest than the copy.** ADR-478 D2 explicitly refused
the 30-day retention timer the privacy page promised. The audit's other three
falsehoods were the same shape — copy written *about* the architecture rather
than *against* it. The tell was that the site contradicted itself: the landing
chips advertised Gemini while `/privacy` named only Anthropic + OpenAI.

Then the audit found a false *mechanism*: `valid_scopes=["read"]` was the only
MCP scope and **nothing read `token.scopes`** — a token labelled read could
`delete` and mint a member-grant `share` link, and that label reached the
consent screen. Fixed additively so no live connector breaks (`read` retained as
the legacy full-access grant).

## 3. Owed

**From ADR-561:**
- `workspace_blobs` still carries `USING (true)` from migration 158 — never
  dropped. Any authenticated user knowing a SHA-256 can read any blob row.
  Named on the data page as current work; owed as a migration.
- **Conversation export** — the git export omits conversations, so "it's all
  yours to export" stays qualified.
- **Click-pass** on the changed marketing pages (`/`, `/privacy`,
  `/privacy-architecture`, `/faq`). `next build` is green; nothing was driven.

**From ADR-563:**
- **A client that actually requests the narrow scopes.** Enforcement is live but
  every live token holds the legacy grant, so *nothing is yet restricted in
  practice* — the mechanism is correct and unexercised in production.
- Consent-screen copy in operator language (`files:read` is not a sentence).
- `MCP_BEARER_TOKEN` static path — one hardcoded `MCP_USER_ID`, full access.

**Housekeeping:**
- **CLAUDE.md is at ~49.9K against a 50K ceiling.** I reclaimed a pre-existing
  breach (50,242 at HEAD) by moving ADR-209's closed phase history to the
  ledger, but the headroom is thin and the file wants a real ablation pass.
  ⚠️ The ratchet is **pytest-style** — `python3 test_claude_md_ratchet.py`
  exits 0 without running anything. Use `python3 -m pytest`.

## 4. Verification notes for the next session

- `test_adr563_mcp_scope_enforcement.py` is **script-style** (`python3`), like
  ADR-474/476/478. Under pytest it reports a false PASS.
- The ADR-563 runtime proof needs py3.11 + the MCP SDK (`/tmp/mcpenv`); system
  python3 is 3.9. App deps must be installed until `mcp_server.server` imports.
- ADR-476's gate is **16/17 — the one red is pre-existing** (an account-settings
  UI check), verified against a clean tree. Don't chase it as a regression.
