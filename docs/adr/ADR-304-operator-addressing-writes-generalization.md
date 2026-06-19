# ADR-304: Operator-Addressing Writes Generalization — Slack DM + Notion Comment as System Infrastructure + YARNNN Chat Honors Bundle MANIFEST

**Status**: Implemented 2026-05-27 — Checkpoints 1 + 2 land atomically.

> **Amendment (2026-06-19) — D5 revised: audience-writes are KERNEL-UNIVERSAL, not bundle-MANIFEST-declared.** See [§"Amendment — kernel-universal audience-writes"](#amendment-2026-06-19--kernel-universal-audience-writes) below. The operator confirmed audience-addressing Slack/Notion writes as an **ambient capability** (first-class, no per-program friction), gated by the ADR-307 uniform gate as the safety floor (ambient capability, gated act; NOT ungated). `write_slack` / `write_notion` are re-declared in kernel `CAPABILITIES` with `feeds: action` (⇒ HIGH tier per the 2026-06-19 derived-tier gate), pointing at the new audience-write tools — symmetric with `read_slack` / `read_notion` already being kernel-universal (capability-bundle-shaped, not program-shaped, per ADR-224 §1). D1 (operator-DM/comment stay system infrastructure) and D6 (Reviewer-exclusion) are **preserved verbatim**. This revises D5's "audience-addressing extensions declare via bundle MANIFEST" to "kernel-universal in CAPABILITIES" for these two capabilities; bundle-declared extension remains available for genuinely program-specific audience writes.

**Date**: 2026-05-27

**Authors**: KVK, Claude

**Depends on**: ADR-118 (Skills as Capability Layer), ADR-188 (Domain-Agnostic Framework — bundle MANIFEST as workspace-shape authority), ADR-207 P3 (Capability Availability Gate), ADR-224 (Kernel/Program Boundary), ADR-272 (Specialist Survival Test — five specialists dissolved into Reviewer), ADR-283 (alpha-author bundle), ADR-299 (Operator-Addressing System Infrastructure — `send_operator_email`)

**Amends**: ADR-299 (taxonomy generalized beyond email; D1 distinguishing test now applies to Slack DM + Notion comment)

**Preserves**: Singular Implementation discipline, ADR-272 specialist consolidation (no new specialists introduced), ADR-299 D8 Reviewer-side exclusion (Reviewer's tool surface remains 21 primitives)

**Supersedes**: The structural assumption that `write_slack` / `write_notion` are workspace capabilities. The capability names dissolve from kernel `CAPABILITIES` (the operator-DM Slack send and operator-comment Notion write reclassify as system infrastructure per D1; audience-addressing extensions, when bundles need them, declare new capability keys via MANIFEST per D5 below).

---

## The structural gap the audit surfaced

After ADR-299 named the operator-addressing-system-infrastructure-vs-workspace-capability taxonomy, an audit on Slack + Notion write surfaces found:

1. **The current Slack + Notion writes were misclassified.** `platform_slack_send_message` is scoped to "send to user's own DM so they own the output" (per its description); `platform_notion_create_comment` is scoped to the operator's designated page. Both are structurally *operator-addressing* — addressee resolved from operator-identity, not LLM-supplied. Same shape as `platform_email_send_to_operator`. Both were registered as workspace capabilities (`write_slack` / `write_notion`) only because the operator-addressing-vs-audience-addressing distinction had not yet been named at the time of their registration.
2. **YARNNN chat ignored bundle MANIFEST capability declarations.** `get_platform_tools_for_user` iterated `platform_connections` directly and surfaced every tool of every connected provider. This was structurally different from `get_platform_tools_for_capabilities` (the headless path), which respects the agent's declared capability set + task `required_capabilities`. The asymmetry meant bundles' MANIFEST commitments (e.g., alpha-author declares it does NOT do audience-bearing Slack writes per ADR-283 D7) were silently undermined for the chat path.
3. **The dissolved-specialist re-introduction trap.** Pre-audit instinct was to narrow writes into dedicated `slack_writer` / `notion_writer` sub-specialists. ADR-272's Specialist Survival Test had already evaluated this exact pattern and dissolved five production specialists (researcher / analyst / writer / tracker / reporting); only `designer` survived. Re-introducing platform-specific writer specialists would re-litigate a decision evidence already settled.

## Decision

### D1. Operator-addressing writes are system infrastructure, generalizing ADR-299 D1

Per ADR-299 D1's distinguishing test — *does this address operator-identity or a third party / audience / external counterparty?* — three tools today qualify as **operator-addressing system infrastructure**, registered in `SYSTEM_INFRASTRUCTURE_TOOLS`:

| Tool | Operator-addressing scope | Wire |
|---|---|---|
| `platform_email_send_to_operator` | `auth.users.email` (workspace owner) | System Resend wire (`RESEND_API_KEY`, ADR-040 + ADR-202 wire) |
| `platform_slack_send_message` | User's own Slack DM (`authed_user_id` from integration metadata) | Per-user Slack OAuth wire |
| `platform_notion_create_comment` | User's designated Notion page (`designated_page_id` from integration metadata) | Per-user Notion OAuth wire |

The wire distinction (system-deployed vs per-user-OAuth) is orthogonal to the addressee distinction. What unifies the three under ADR-299 D1's test is the **structural pin to operator-identity at runtime**: each tool either rejects LLM-supplied addressee fields (`platform_email_send_to_operator` per ADR-299 D6) or resolves the addressee from integration metadata authored by the operator (Slack `authed_user_id`, Notion `designated_page_id`). None permit LLM-controlled third-party addressing.

### D2. `write_slack` + `write_notion` capability keys dissolve

Workspace `CAPABILITIES` dict no longer contains `write_slack` or `write_notion`. The operator-addressing scope of `platform_slack_send_message` + `platform_notion_create_comment` is structurally not a workspace capability under D1's test. The capability keys are deleted from:

- `api/services/orchestration.py::CAPABILITIES`
- `api/services/platform_tools.py::PLATFORM_TOOLS_BY_CAPABILITY`
- `api/services/platform_tools.py::CAPABILITY_PROVIDER_MAP`
- `docs/programs/alpha-author/MANIFEST.yaml::capabilities[]` (the sole bundle declaration today)

Bundles that previously declared `write_notion` (alpha-author) lose nothing operationally — the tool surfaces via `SYSTEM_INFRASTRUCTURE_TOOLS` to every agent path that gets system infrastructure (task-bearing surfaces; not the Reviewer per ADR-299 D8). The capability declaration is replaced by the system-infrastructure registration.

### D3. YARNNN chat honors bundle MANIFEST capability declarations

`get_platform_tools_for_user` (the YARNNN chat tool-loading path) is rewritten to match the headless gating semantics:

- **Layer 1**: `SYSTEM_INFRASTRUCTURE_TOOLS` merged unconditionally — same as `get_platform_tools_for_capabilities`. These are the kernel's operating surface; every LLM-invocable agent path that isn't the Reviewer gets them.
- **Layer 2**: workspace capabilities surfaced only if declared by an active program bundle's MANIFEST. Reads `list_bundle_capabilities()` (the union of capability declarations from all active bundles per `bundles_active_for_workspace`), intersects against the kernel's `_resolve_capability` shape, gates on `platform_connections` per `capability_available`.

The pre-rewrite behavior — surfacing every tool of every connected provider unconditionally — is **deleted**. No dual paths. No backwards-compat shim. A workspace with no active program sees Layer 1 only (3 system-infrastructure tools); a workspace with an active program sees Layer 1 + the program's declared capabilities. Tools surface because the bundle declares the capability, not because the operator happens to have an OAuth connection to the provider.

This closes the structural gap audit pressure point #2. Headless and chat now use the same gating semantics:

```
Headless: capability set = role_capabilities + task_required_capabilities
Chat:     capability set = union(active_bundles[].capabilities)
Both:     resolve via _resolve_capability + platform_connections gate
```

The Reviewer is intentionally absent from both paths — it consumes `REVIEWER_PRIMITIVES` directly per ADR-299 D8.

### D4. No new specialists. The Reviewer continues to do investigation, analysis, writing, accumulation, tracking inline.

Per ADR-272's Specialist Survival Test, only `designer` survives as a production-role specialist. This ADR explicitly **does not** introduce `slack_writer` / `notion_writer` / `commerce_writer` / similar platform-targeted specialists. The Reviewer absorbs platform-write decision-making the same way it absorbs other production-shape work — using its own tool surface, inline, not via dispatch. Operator-addressing writes reach the operator through whatever task-bearing agent path produces them; audience-addressing extensions (D5) follow the same execution shape.

The narrowing-via-specialist instinct conflicts with ADR-272's evidence and the design exercise that motivated this ADR explicitly walked away from it after audit. Future ADRs proposing platform-targeted specialists must clear the ADR-272 Specialist Survival Test (tool-surface test, output-size test, latency test) before introduction.

### D5. Audience-addressing extensions, when bundles need them, declare via MANIFEST

When a bundle has a genuine archetypal need for *audience-addressing* writes — channel-sends to shared Slack workspaces, page-creates / block-appends in shared Notion workspaces, newsletter sends, etc. — it declares them as workspace capabilities via MANIFEST. The naming pattern reserves `write_slack` / `write_notion` (and future `write_<platform>` keys) as the namespace for audience-addressing extensions.

Examples that *would* qualify as audience-addressing workspace capabilities:

- `platform_slack_send_to_channel(channel_id, text)` — LLM-supplied channel addressee, third-party-affecting
- `platform_notion_create_page(parent_id, title, content)` — creates new pages in shared workspace
- `platform_notion_append_block(page_id, block_content)` — modifies operator-or-team-owned page content

Each such tool would be registered in the per-provider list (`SLACK_TOOLS` / `NOTION_TOOLS`), associated with a workspace capability key in `PLATFORM_TOOLS_BY_CAPABILITY`, declared in a bundle's MANIFEST `capabilities[]` block. Bundle authors decide whether the bundle's archetype needs them. Headless and chat both gate on the bundle declaration (D3). Reviewer remains excluded (D4 + ADR-299 D8).

ADR-283 step 2 explicitly tracks `write_notion_pages` + `write_email` audience-addressing extensions as a deferred follow-up; that future work lands cleanly under D5.

### D6. Reviewer-side exclusion preserved verbatim

ADR-299 D8's architectural commitment — Reviewer is permanently excluded from `SYSTEM_INFRASTRUCTURE_TOOLS` because tool-list size is empirically corrosive to judgment quality on this surface — applies to **all** entries in the registry, not just `platform_email_send_to_operator`. Today: `REVIEWER_PRIMITIVES` count remains 21 (no Slack DM tool, no Notion comment tool, no operator email tool, by design). Future system-infrastructure additions inherit the exclusion automatically.

### D7. No post-judgment dispatcher in this ADR

The post-judgment dispatcher integration (named in ADR-299 §"Reviewer authority — RESOLVED" + deferred in §"Post-judgment dispatcher integration — DEFERRED") remains deferred. ADR-304 narrows the Slack + Notion writes' architectural classification; it does NOT implement the verdict-coupled delivery hook. When that hook ships, the three system-infrastructure tools (email + Slack DM + Notion comment) all become candidate delivery channels under a single dispatcher pattern.

## Implementation

Singular Implementation discipline — one atomic commit.

### Code

1. **`api/services/platform_tools.py`**:
   - Lift `SLACK_SEND_MESSAGE_TOOL` from `SLACK_TOOLS` list literal to named module-level constant alongside `EMAIL_SEND_TO_OPERATOR_TOOL`.
   - Lift `NOTION_CREATE_COMMENT_TOOL` from `NOTION_TOOLS` list literal to named module-level constant.
   - Remove both from their per-provider lists (`SLACK_TOOLS` shrinks to 2 reads; `NOTION_TOOLS` shrinks to 2 reads). Singular Implementation: each tool defined once.
   - Extend `SYSTEM_INFRASTRUCTURE_TOOLS` to 3 entries: `[EMAIL_SEND_TO_OPERATOR_TOOL, SLACK_SEND_MESSAGE_TOOL, NOTION_CREATE_COMMENT_TOOL]`.
   - Delete `"write_slack"` and `"write_notion"` entries from `PLATFORM_TOOLS_BY_CAPABILITY`.
   - Delete `"write_slack"` and `"write_notion"` entries from `CAPABILITY_PROVIDER_MAP`.
   - Rewrite `get_platform_tools_for_user` to honor bundle MANIFEST declarations (D3 implementation). Lazy-import `bundle_reader.list_bundle_capabilities`; intersect with kernel resolution; gate on `platform_connections` via `capability_available`. Delete the unconditional-per-provider iteration. Updated docstring + log message reflect the new gating semantics.

2. **`api/services/orchestration.py`**:
   - Delete `"write_slack"` and `"write_notion"` entries from `CAPABILITIES` dict (lines ~1150 + ~1160).
   - Replace deleted entries with a comment block citing ADR-304 D2 and noting the reclassification.

### Bundle

3. **`docs/programs/alpha-author/MANIFEST.yaml`**:
   - Remove `capability: write_notion` line from `agents[*].capabilities` (the agent-level capability menu)
   - Remove the full `- key: write_notion` capability declaration from `capabilities[]`.
   - Add comment citing ADR-304 explaining the move to system infrastructure.

4. **`docs/programs/alpha-author/README.md`**:
   - Update capability inventory lines (~75-76) to remove `write_notion`; explain that operator-addressing Notion comments are system infrastructure post-ADR-304.

### Tests

5. **`api/test_adr299_kernel_universal_capability.py`**:
   - Rename `test_system_infrastructure_tools_contains_email_send_to_operator` → `test_system_infrastructure_tools_contains_operator_addressing_writes`; assert all 3 tools present.
   - Add `test_write_slack_and_write_notion_not_in_capabilities` — guards the deletion.
   - Add `test_write_slack_and_write_notion_not_in_resolution_maps` — guards `PLATFORM_TOOLS_BY_CAPABILITY` + `CAPABILITY_PROVIDER_MAP` cleanup.
   - Extend `test_reviewer_primitives_excludes_send_operator_email` → `test_reviewer_primitives_excludes_all_system_infrastructure_tools` (Reviewer exclusion applies to all 3 system-infrastructure tools, not just email).

6. **NEW `api/test_adr304_yarnnn_chat_honors_bundle_manifest.py`**:
   - `test_get_platform_tools_for_user_does_not_iterate_raw_providers` — source-level guard that the pre-rewrite "for provider in connected_providers" pattern is gone from the function body.
   - `test_get_platform_tools_for_user_reads_bundle_capabilities` — source-level guard that `list_bundle_capabilities` or equivalent bundle import is present in the rewritten function.
   - `test_get_platform_tools_for_user_surfaces_system_infrastructure_unconditionally` — Layer 1 invariant.

7. **`api/test_reviewer_formalization.py`**:
   - Extend persona-frame assertion: rather than just acknowledging the email tool's absence, the persona-frame must teach the broader pattern (all operator-addressing system infrastructure is out of the Reviewer's surface by design).

### Docs

8. **`docs/adr/ADR-299-kernel-universal-operator-addressing-capability.md`**:
   - Append §"Generalization landed in ADR-304" subsection (one paragraph) at end, pointing forward. ADR-299 stays the email-specific canonical ADR; ADR-304 generalizes.

9. **`api/prompts/CHANGELOG.md`**:
   - Entry `[2026.05.27.3]` documents the generalization + YARNNN-chat-MANIFEST honoring. LLM-facing because YARNNN chat's tool surface changes shape.

### Validation gate

`python -m pytest api/test_adr299_kernel_universal_capability.py api/test_adr304_yarnnn_chat_honors_bundle_manifest.py api/test_reviewer_formalization.py api/test_adr276_reactive_envelope.py api/test_adr301_reviewer_pulse_envelope.py` — expect all green except the pre-existing `test_persona_frame_no_banned_phrases` ADR-302 regex drift (unrelated; same status as prior commits).

Smoke test: `python api/scripts/operator/email_wire_smoke_test.py kvk` — system Resend wire continues to fire correctly (email infrastructure unchanged).

## Stress-test against the rewrite

**Scenario 1: alpha-author operator with Notion connected, no Slack.**
- Pre-ADR-304: YARNNN chat sees 3 Notion tools (search + get_page + create_comment) via raw provider iteration.
- Post-ADR-304: YARNNN chat sees system-infrastructure (email + Slack DM tool + Notion comment tool — Slack DM is harmless without connection; will fail at handler with clear error if invoked) + zero workspace-capability Notion reads (alpha-author MANIFEST doesn't declare `read_notion`). **Behavior change**: chat loses `platform_notion_search` + `platform_notion_get_page`.
- Architectural correctness: alpha-author's MANIFEST is authoritative about what the workspace does. If the bundle wanted those reads to be available in chat, it would declare `read_notion`. The fix path is to add it to the MANIFEST if alpha-author genuinely needs operator-driven Notion reads in chat; today the bundle's content suggests reads happen via uploads (`read_uploads` declared) not via Notion search.

**Scenario 2: operator with no active program, Slack + Notion connected.**
- Pre-ADR-304: YARNNN chat sees 6 platform tools (3 Slack + 3 Notion).
- Post-ADR-304: YARNNN chat sees 3 system-infrastructure tools (email + Slack DM + Notion comment). **Behavior change**: chat loses reads from both platforms.
- Architectural correctness: pre-activation workspace has no declared shape; the operator hasn't committed to what the workspace does. System-infrastructure-only is the structurally correct surface. To unlock more, the operator activates a program whose MANIFEST declares the needed capabilities.

**Scenario 3: alpha-trader operator with trading + commerce + slack connected.**
- alpha-trader MANIFEST declares `read_trading` + `write_trading`. Not `read_slack` / `read_notion`.
- Post-ADR-304: YARNNN chat sees system-infrastructure (3) + bundle-declared (read_trading + write_trading via the bundle's capability list). **Behavior change**: chat loses Slack reads.
- Architectural correctness: alpha-trader is a trading bundle; chat tooling surface should match the bundle's archetype. If trader operators need Slack reads (operator wants to ask "what did the trading channel say today?"), the bundle declares `read_slack` in MANIFEST.

**Scenario 4: future audience-addressing extension shipped.**
- Operator declares an extension capability via bundle MANIFEST: e.g., alpha-author step 2 adds `write_notion_pages` for shared-Notion drafting.
- Post-ADR-304: extension tool surfaces through Layer 2 of `get_platform_tools_for_user` (bundle-declared) + headless path via `task_required_capabilities`. Reviewer still excluded per D6.
- Architectural correctness: the bundle declares its archetype's reach; chat + headless honor the declaration; Reviewer's judgment quality is preserved regardless of extension count.

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Behavior change breaks an in-flight alpha-author operator workflow that relied on Notion search/get_page reads in chat | Surfaced explicitly in stress-test Scenario 1. Mitigation: if real pressure surfaces, add `read_notion` to alpha-author MANIFEST — that's an additive bundle change requiring no kernel work. The structural improvement (chat honors MANIFEST) is correct; per-bundle declarations adjust as bundles mature. |
| Operators who connect Slack without an active program lose the chat-reachable Slack tools | Same logic applies. Pre-activation surface is intentionally narrow; activate a program whose MANIFEST declares needed capabilities. |
| Bundle authors silently reintroduce `write_slack` / `write_notion` as audience-addressing capability keys | The names are deliberately reserved for audience-addressing extensions per D5. If reintroduced in a MANIFEST today, they would surface to chat + headless (Layer 2 gating works) but **must point to a new tool**, not back to `platform_slack_send_message` / `platform_notion_create_comment` (which are system infrastructure now and registered in `SYSTEM_INFRASTRUCTURE_TOOLS`, not in `PLATFORM_TOOLS_BY_CAPABILITY`). |
| Reviewer-side accidental tool inclusion via a future PR not aware of D6 | Existing test guard `test_reviewer_primitives_excludes_send_operator_email` extends to cover all 3 system-infrastructure tools — `test_reviewer_primitives_excludes_all_system_infrastructure_tools`. Future system-infrastructure additions inherit the guard automatically. |

## Cross-references

- **ADR-299**: operator-addressing system infrastructure framing (email-specific). ADR-304 generalizes its taxonomy.
- **ADR-272**: Specialist Survival Test — the evidence that grounds D4 ("no new specialists").
- **ADR-188**: bundle MANIFEST as workspace-shape authority — the foundation D3 leans on.
- **ADR-224**: kernel/program boundary — capability resolution path (`_resolve_capability`) ADR-304 D3 reuses.
- **ADR-207 P3**: `capability_available` gate — Layer 2 of the rewritten `get_platform_tools_for_user`.
- **ADR-283** D7 + step 2: alpha-author bundle's deferred audience-addressing extensions land cleanly under ADR-304 D5.
- **2026-05-25 v5 canary RESOLUTION**: the empirical basis for D6 (Reviewer surface preserved at 21 primitives; all 3 system-infrastructure tools excluded).

## Amendment (2026-06-19) — kernel-universal audience-writes

**The operator's directive:** make Slack + Notion audience-writes first-class and **kernel-universal** — ambient, no per-program friction — *with* the consequential-action gate as the safety floor. The operator was explicit: "ambient capability, gated act; NOT ungated."

**What changes:** D5's "audience-addressing extensions declare via bundle MANIFEST" is revised. `write_slack` + `write_notion` re-enter kernel `CAPABILITIES` as **kernel-universal** audience-write capabilities:

```python
"write_slack":  {"category": "tool", "runtime": "external:slack",  "feeds": "action",
                 "tools": ["platform_slack_send_to_channel"],
                 "platform_connection_requirement": {"platform": "slack",  "status": "active"}},
"write_notion": {"category": "tool", "runtime": "external:notion", "feeds": "action",
                 "tools": ["platform_notion_create_page", "platform_notion_append_block"],
                 "platform_connection_requirement": {"platform": "notion", "status": "active"}},
```

- **`feeds: action` ⇒ `required_tier` HIGH** (the 2026-06-19 derived-tier gate, ADR-335 amendment). An audience-write is a *primary external action*; only a platform-grade binding satisfies it. The existing first-party Slack/Notion connections backfill to `platform` grade (migration 186), so they pass.
- **Symmetric with the reads.** `read_slack` / `read_notion` are *already* kernel-universal (in `CAPABILITIES`, not bundle-declared) because they are **capability-bundle-shaped, not program-shaped** (ADR-224 §1's explicit carve). The audience-writes inherit the same classification — this is not a kernel/program boundary violation; it is the writes joining the reads where they already live.
- **The gate is the safety floor (ADR-307 Phase 5).** These capabilities surface the new audience-write tools (`external-write` family) to task-bearing agent paths; every call passes `resolve_permission`, which QUEUEs under manual/bounded (operator approves the send from the cockpit) and APPLYs under autonomous. Ambient capability, gated act.

**What is preserved verbatim:**
- **D1 — operator-addressing stays system infrastructure.** `platform_slack_send_message` (operator's own DM) and `platform_notion_create_comment` (operator's designated page) remain in `SYSTEM_INFRASTRUCTURE_TOOLS`. The kernel-universal `write_slack` / `write_notion` point at the **audience** tools, NEVER back at these operator-addressing tools. The addressee distinction (operator-identity vs LLM-supplied audience) is exactly what separates the two families.
- **D6 — Reviewer-exclusion.** The Reviewer has NO platform write tool in `REVIEWER_PRIMITIVES` (neither audience nor capital). It reaches external effect only via `ProposeAction`. Kernel-universal audience-writes surface to task-bearing agent paths via `PLATFORM_TOOLS_BY_CAPABILITY`, never to the Reviewer. Guard: `test_reviewer_primitives_excludes_all_platform_write_tools`.
- **D5's bundle-MANIFEST path remains** for genuinely program-specific audience writes (a bundle can still declare its own `write_<platform>` extension); it is no longer the *only* path for Slack/Notion.

**Receipts:** `api/services/orchestration.py` (`write_slack` / `write_notion` in `CAPABILITIES`, `feeds: action`); regression gate `api/test_adr299_kernel_universal_capability.py` (16/16) — `test_write_slack_and_write_notion_are_kernel_universal_audience_writes`, `test_operator_addressing_writes_stay_system_infrastructure`, `test_reviewer_primitives_excludes_all_platform_write_tools`. The tools + `PLATFORM_TOOLS_BY_CAPABILITY` / `CAPABILITY_PROVIDER_MAP` wiring land in the follow-on tool-build commit (ADR-307 Phase 5 family routing carries them). Builds on [ADR-307 Phase 5](ADR-307-unified-permission-taxonomy.md#phase-5--close-the-platform-write-bypass-2026-06-19) (the uniform gate the safety floor relies on) + [ADR-335 derived-tier amendment](ADR-335-AMENDMENT-derived-trust-tier.md) (`feeds: action` → HIGH).

## Status

**Implemented 2026-05-27** — Checkpoints 1 + 2 land atomically per the second user confirmation. ADR-300 number was taken; this ADR is **ADR-304** in sequence.

**Amended 2026-06-19** — audience-writes made kernel-universal (above). Tools build in the follow-on commit.
