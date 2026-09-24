# Access is brokered, never held — the member's credentials and the browser as gateway

**Date**: 2026-09-24 · **Status**: PARKED — discussed with the operator, nothing built, nothing ratified
**Occasion**: after ADR-662 D15 (the extension is the one executor) and ADR-664 (the browser is reach),
the operator asked whether yarnnn should treat the member's logins and credentials as first-class — a
competitor was observed centring "one vault" password handling for its sandboxed agent — on the thesis that
**user access is the single gateway that makes agents and workflows powerful, and may become the bottleneck.**
**Parked because**: the operator chose to refocus on browser workflows and the Supervisor first (ADR-665).
Pick this up when a workflow is first observed stopping at a sign-in wall, or a vault opens a door (§5).

---

## 0. The one-paragraph answer

The browser matters because it is **where the member's access already lives**: every site they are signed
into, with no per-platform integration. There are two ways to hand an agent that access — bring the agent to
the access (yarnnn: the extension in the member's own Chrome) or bring the access to the agent (a vault feeding
a sandboxed browser). A sandbox *needs* a vault because it has no sign-ins; ADR-662 D15 chose the member's
Chrome so yarnnn never would. The proposed position: **yarnnn never holds a member's secret; it brokers a
sign-in to the member's own password manager, which fills outside the agent's view on the member's approval;
an unattended run never releases a credential.**

## 1. The two shapes

| | Agent goes to the access (yarnnn today) | Access goes to the agent (vault + sandbox) |
|---|---|---|
| Authority lives | in the member's Chrome, as sessions | in a vault, as secrets; a remote browser logs in |
| yarnnn holds | nothing — a password field's value never leaves the page (ADR-662 D15) | the secrets, or keys to them |
| Uptime | while the member's Chrome is on | always |
| Login friction | none — already signed in | 2FA, new-device and datacentre-IP checks |
| Worst breach | bounded to one machine; sessions expire | every password of every member |

A per-member vault used only for that member's own work is **not** ADR-645 D1's model (A) — (A) is one
member's credential backing everyone else's acts. The real canon collision is **attendance**: a clock acting
with a member's authority (ADR-615/639; ADR-645 §7 — *"unattended work has no outbound reach"*). Note that
ADR-665 option B already crosses that line through the member's own Chrome; custody is the only difference.

## 2. What the providers ship (checked 2026-09-24)

| Provider | Where it fills | Open to yarnnn? | Unattended? |
|---|---|---|---|
| 1Password for Claude (Jul 2026) | locally — 1Password's extension fills the member's Chrome "outside the agent's view" | no — Anthropic only; "designed to extend to any browser-based agent", no programme announced | no — one biometric approval per task, "no standing access" |
| 1Password Agentic Autofill | remote browser (Browserbase) | early access, partner-only | no — approval per fill |
| Bitwarden Agent Access SDK (Mar 2026) | open protocol, JIT, end-to-end encrypted | yes, but alpha — "not for production … or autonomous access" | no |
| Auth0 Token Vault | OAuth tokens for APIs, not passwords | yes | yes — but it is the connector layer, not the browser |

**Every provider requires a present human to release a credential.** The industry has converged on it. A
vault therefore removes the *attended* bottleneck (a session expired, a site not signed into, a 2FA prompt)
and does **not** remove the unattended one.

Sources: [1Password for Claude](https://1password.com/press/2026/july/1password-for-claude) ·
[Agentic Autofill docs](https://www.1password.dev/agentic-autofill) ·
[Bitwarden Agent Access SDK](https://bitwarden.com/blog/introducing-agent-access-sdk/) ·
[Auth0 Token Vault](https://auth0.com/ai/docs/intro/token-vault)

## 3. The proposed position (not ratified)

1. **yarnnn never holds a member's secret** — no password, no OTP seed, not even encrypted. Extends ADR-645 D2
   from tokens to passwords.
2. **yarnnn brokers, never reads.** One provider-neutral act in the browser vocabulary — *sign in here*: the
   executor recognises a sign-in wall, pauses the agent, and hands it off — to the member's vault when an
   integration exists, otherwise to the member themselves in the agent's tab (works today, no vendor). The
   model learns only signed-in / not.
3. **An unattended run never releases a credential.** A workflow that meets a sign-in wall stops and surfaces
   in the Supervisor as *needs you to sign in to X*, resuming on the member's tap (ADR-665's proposal queue).
   Unattended reach comes from routes needing no login at run time: connections, workspace-owned identities
   (ADR-645 §7), long-lived sessions on a machine the member keeps on.
4. **Vendors are adapters, added when a door opens** — 1Password first when it opens to third parties;
   Bitwarden's SDK as the open fallback once out of alpha.
5. **ADR-662 D15 amended narrowly**: the agent still may not browse a password manager's website (stays
   default-denied); a vault's extension filling on the member's approval is a different, new door.
6. **Later**: move the connector OAuth tokens (`platform_connections`) to a token vault, taking that custody
   off yarnnn too.
7. **Shared workspaces**: access stays per member, never pooled — a workspace-level vault is model (A) rebuilt.
   The Supervisor shows whose access a workflow runs on; when a member leaves, their access leaves.

## 4. Adjacent points from the same discussion (belong to ADR-665's revision)

- A browser workflow should be **standing work with a new executor**, keeping `CONTRACT.md` load-bearing —
  a `WORKFLOW.md` procedure on a schedule with no contract is ADR-603 D5's retired recurrence.
- **No task table** (ADR-231's sunset); instead an outward browser act must reach a workspace-visible record —
  today its receipt lives only in the member's private lane (`metadata.receipts`, `api/routes/lanes.py`).
- **Per-workflow site scopes**: unattended, a steered run must reach only the sites its declaration names.
- **Transport**: the pending act is an in-memory future (`_TURNS`, `api/services/client_tools.py`); an
  unattended run needs the executor holding its own connection and the pending act in shared state.

## 5. When to unpark

- The first measured workflow runs stopped for sign-in — count them before spending on a vendor.
- 1Password opens its local agent integration to third parties, or Bitwarden's SDK leaves alpha.
- A member asks for yarnnn to "remember" a password — the answer is §3.1, stated from here.

Ratifying means an ADR ("access is brokered, never held") amending ADR-662 D15 beside ADR-645, with a gate
arm that no secret-shaped value is written to the substrate or a table.
