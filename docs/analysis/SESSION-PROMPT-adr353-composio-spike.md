# SESSION PROMPT — ADR-353 Composio driver spike (copy-paste into Claude Code)

> Carry-over prompt generated 2026-06-22 from the positioning + driver-layer discourse. Paste the block below into Claude Code. It is scoped to a **spike**, not a migration.

---

You are working in the YARNNN codebase. We are evaluating adopting **Composio** as the driver backend for external platform actions ("the hands"), behind YARNNN's existing primitive contract.

**Read first (source of truth):**
- `docs/adr/ADR-353-composio-as-driver-backend.md` — the decision (Status: **Proposed**), boundary, seams, phasing, scope, and §12 ratification criteria.
- `docs/analysis/positioning-discourse-seat-as-asset-2026-06-22.md` — §6.6 (kernel vs commodity drivers; *drive the mechanical, never rent the judgment*) + Appendix B.
- `CLAUDE.md` execution disciplines — especially Singular Implementation, "check ADRs first," Render Service Parity, Prompt Change Protocol, ADR-307 (permission gate), ADR-209 (authored substrate single write path), Pitfall #4 (no silent success).

**Framing — this is a SPIKE, not a migration.** Do NOT delete any first-party client. Do NOT flip any default. Build the new path behind a feature flag, alongside the existing one, prove it, and write a findings report. Whether to adopt (and then delete first-party code) is KVK's decision *after* the spike.

**Hard invariants — do not violate:**
1. Do NOT modify `resolve_permission` (`api/services/primitives/permission.py`), `write_revision` (`api/services/authored_substrate.py`), or capability-gating (`capability_available` in `api/services/orchestration.py` + `platform_connections`). Composio is an executor *behind* the existing gate, never a gate itself.
2. Attribution stays in the kernel: action results are authored via `write_revision` as `agent:{slug}` / `system:*`, exactly as today. Composio never reaches the substrate.
3. **Capital family is OUT of scope** (trading/Alpaca, commerce *writes*). Spike only the read + external-write family. **Start with Slack.**
4. **No silent success** (Pitfall #4): map Composio errors to the existing handler return shape; never report success on failure.
5. Keep it swappable: Composio is one implementation behind a driver interface; reverting must be a config change, not a refactor.

**Spike tasks, in order:**
1. **Coverage check.** For currently connected platforms (Slack first; then Notion, GitHub), confirm Composio exposes the *specific verbs* our capabilities use — not just the platform. Examples to verify: Slack `send_to_channel`/`post_message`; Notion `append_block`/`create_page`/`create_comment`/`search`; GitHub list repos/issues/PRs + readme. Produce a verb-by-verb coverage matrix. Flag any connector that requires "bring-your-own developer credentials."
2. **Consumption protocol decision.** Decide whether the driver consumes Composio via its **MCP interface** or its **REST/SDK**. Record the tradeoff (MCP = protocol-clean, swappable with any MCP server; SDK = simpler, more coupled) and pick one for the spike with a one-paragraph rationale.
3. **Build `api/services/composio_driver.py`** with a clean, swappable interface, e.g.:
   `async def execute(provider: str, verb: str, payload: dict, *, token: str, user_id: str) -> dict` returning `{"success": bool, "result": dict | None, "error": str | None}` — mirroring the return shape of the existing `_handle_*_tool` functions so `handle_platform_tool` can route to it transparently.
4. **Wire behind a flag.** In `handle_platform_tool` (`api/services/platform_tools.py`), add a branch gated by an env flag (`COMPOSIO_DRIVER_ENABLED`) + a per-provider allowlist that routes **Slack only** to `composio_driver`, leaving every other provider on the first-party path. Default **OFF**.
5. **Token path (Phase 1).** Fetch the per-user encrypted token from `platform_connections`, decrypt via the existing `TokenManager` (`api/integrations/core/tokens.py`), and pass plaintext to the driver for the single call. Composio holds no tenant state.
6. **Multi-tenant isolation test (HARD GATE — ADR-353 §12.6).** Connect **two distinct test users'** Slack accounts; with the flag on, execute the same action for each; prove each runs against its own credentials with **zero cross-tenant leakage** (Composio entity == YARNNN `user_id`). This is the load-bearing test — the failure that bites only after implementation.
7. **Parity + error-shape test.** Run identical inputs through the first-party path vs the Composio path; compare results, latency, and error shapes. Force an auth failure and a rate-limit; confirm no silent success and that errors surface as QUEUE/retry, never false success.
8. **Cost note.** Record Composio's per-action cost and how it would meter against `execution_events` (ADR-291). Note only — do not build metering.
9. **Render parity note.** Document that `COMPOSIO_API_KEY` would belong on `yarnnn-api` + `yarnnn-unified-scheduler` (NOT mcp-server / render). Do NOT set production env in the spike.

**Deliverable.** Write a findings report to `docs/analysis/SESSION-FINDINGS-adr353-composio-spike-2026-06-22.md` (or append a `## Spike results` section to ADR-353) covering: the coverage matrix, the consumption-protocol decision, the two-user isolation result, parity/error results, cost, and a clear **RATIFY / DON'T-RATIFY** recommendation against ADR-353 §12. Update ADR-353 `Status` only if KVK approves.

**Stop conditions.** If Composio lacks coverage for Slack's needed verbs, OR the two-user isolation test fails — **STOP and report**; do not proceed to wider wiring. Deleting first-party clients is a separate, post-ratification change; do not do it in this session.

**Discipline reminders.** Keep both paths until ratified (singular implementation applies to the *final* state, not the spike). Update docs alongside code. If you touch any prompt or tool-definition text, follow the Prompt Change Protocol (`api/prompts/CHANGELOG.md`).
