# Gate census — every API gate red at a clean HEAD (2026-09-13)

**Hat**: B. **Method**: every `api/test_*.py` run in isolation with a per-file timeout — pytest-shaped files
through pytest (43 red of 156), script-shaped files as scripts (58 red of 108). The class is a
FIRST GLANCE from the verdict line, not a ruling; each red needs its own ruling (re-anchor when the rule
survives, delete when the subject is gone), and a ruling lowers this list in the same commit.

Rulings already applied this day: `test_adr388` re-anchored (14/14) · `test_adr322` deleted (its subject, the
entity layer, is gone) · `test_adr477` re-pointed to the moved StudioCanvas · `test_adr647` derived from the
one-home rule · `test_eval_suite_gate` green (browser manifests restorable) · `test_adr565` + `test_adr567`
deleted (their subject, the radar app, was deleted by 15403f1 on 2026-08-21 — "radar deleted, docs hidden") ·
`test_quality_e2e` deleted (a smoke test of the task pipeline ADR-231 dissolved; it imported `services.task_types`) · the seven `test_studio_*` gates re-anchored (2026-09-13): six failures were one root cause — write messages and the crumb label became `${app.label}` (ADR-636/599) — plus the shared submit rule (ADR-483 D3), the explicit host of `splitHalves`, the sixth reload site (the member-pressed reload control); the flow-root Tab checks retired (ADR-560 D8) and the toolbar's gallery-dismissal check retired (ADR-586 D1/616 D1/589 D3) — every re-anchor falsified in-process · `test_adr455` re-anchored (19/19): the navigator's desktop toggle is a pane slot gated by `threeColumn` (ADR-511/516), not `md:hidden`; falsified · `test_adr456_studio_wave2` re-anchored (21/21): the format bar is ADR-521's two-pass applier (`applyToggle`/`applyCode`, `execCommand(cmd)`), the write-door normalisation is ADR-527's table, turn-into is `turnBlockInto` through `applyOp` at both sites; three falsified · `test_adr458` re-anchored (13/13): the Design tab's rename field rides the shared submit rule (ADR-483 D3), not a local isComposing; falsified · `test_adr449` re-anchored: the design-system section composes in `studio_pane_posture` (ADR-606 D3) and lane_runner reaches that builder only under `if artifact_path:`; the var-editor invariant asserted on whitespace-normalised source; falsified by direct evaluation · `test_adr452` re-anchored, one check STRICTER: the surface map is derived from the app descriptors (ADR-636 D3, Slides owns html), the carve is `isShapeCarved` with the resolver's null return as the load-bearing line, and the double-click reads `detail` AND the path anchor (7d38ad5); falsified · `test_adr472_images` re-pinned to the BETA state (28/28): ADR-629 D3 closed ADR-488's hold — primary, default-pinned, in the Dock, wearing `badge: beta` (a fourth check, the honesty mechanism); the decision the handoff owed · `test_trash_visibility` re-anchored (12/12): the routes delegate to the ONE delete and ONE restore in the substrate, so the lifecycle literals are asserted on `archive_live_file` / `restore_live_file` bodies (never the file — its docstrings spell them); falsified · `test_adr443` re-anchored (178/178): the block set re-pinned at 21 (ADR-581 D4's five deck-native kinds) and the fourth citation kind (ADR-583 `fragment` → group `component`); LAYOUTS held ⊇ per ADR-459 D3; the New-‹noun› gallery followed ADR-579 D6.a into the New door and the Layout gallery ADR-589 D3 into the Properties pane (polarity flipped: the toolbar must not re-mount it); the width ladder is container-measured; three checks retired — the Ask affordance and the auto-seed wording (ADR-613) and the Freddie FAB (ADR-632); four falsified · `test_adr459` green with NO change: its meta-check was right — it held the ADR-443 gate to ⊇ on the layout set, and the target was fixed under ADR-443's ruling · `test_adr453` re-anchored (40/40): the page-verb pair dissolved into two homes — the Layout gallery with its carry note in the Properties pane (ADR-589 D3), New ‹noun› in the New door (ADR-579 D6.a); the toolbar carries neither; falsified · `test_adr466` re-anchored (77/77): `staged` → `artboard` (ADR-633) on x/y/z, `[data-slot]` → `[data-area]` (ADR-544 D2) in the kernel position rule, 16:9 pinned in the kernel CSS the skin only narrates, the role reader on the region grain, the modifier-click split into ⇧ and ⌘, the gallery's one mount flipped to the Properties pane; the PowerPoint-pair check retired (ADR-589 D3 + 616 D1); falsified · `test_adr462` re-anchored (53/53): the context mark routes through ADR-525 D2's one selection chokepoint, the frame noun is app-declared (ADR-633 D3), the carry and the source read ride REGION_SEL (ADR-544 D2), Check and Ask left the menu (ADR-613) while Rewrite re-entered as ADR-619 D2's second door and its producer must stay WIRED; the Update-tier check retired (ADR-619 D1); falsified.
Environment, not defects:
`test_adr573_connector_workspace_binding` and `test_adr584` are py3.11-only (green under `python3.11`).

| gate | shape | first-glance class | verdict line |
|---|---|---|---|
| `test_action_feedback_layer.py` | pytest | drift — re-anchor or retire (needs its own ruling) | 2 failed, 3 passed in 0.27s |
| `test_adr209_no_filename_versioning.py` | script | drift — re-anchor or retire (needs its own ruling) | ✗ FAIL — 4 banned-pattern references in live code. |
| `test_adr209_phase1.py` | pytest | collection error — fixture or import | 11 errors in 0.07s |
| `test_adr209_phase2.py` | pytest | collection error — fixture or import | 9 errors in 0.07s |
| `test_adr209_phase3.py` | pytest | live/slow — hits the network or DB; not a source gate |  |
| `test_adr209_phase4.py` | pytest | live/slow — hits the network or DB; not a source gate |  |
| `test_adr209_phase5.py` | pytest | live/slow — hits the network or DB; not a source gate |  |
| `test_adr224_kernel_boundary.py` | pytest | drift — re-anchor or retire (needs its own ruling) | 5 failed, 6 passed in 0.48s |
| `test_adr230_bundle_substrate.py` | pytest | drift — re-anchor or retire (needs its own ruling) | 2 failed, 6 passed in 0.30s |
| `test_adr235_update_context_dissolution.py` | pytest | drift — re-anchor or retire (needs its own ruling) | 2 failed, 11 passed in 0.36s |
| `test_adr237_chat_role_grammar.py` | pytest | drift — re-anchor or retire (needs its own ruling) | 6 failed, 1 passed in 0.09s |
| `test_adr239_decisions_parser_unification.py` | pytest | drift — re-anchor or retire (needs its own ruling) | 4 failed, 2 passed in 0.09s |
| `test_adr241_single_cockpit_persona.py` | pytest | drift — re-anchor or retire (needs its own ruling) | 4 failed, 4 passed in 0.09s |
| `test_adr242_phase1_cockpit_money_truth.py` | pytest | drift — re-anchor or retire (needs its own ruling) | 2 failed, 4 passed in 0.08s |
| `test_adr244_workspace_settings_surface.py` | script | drift — re-anchor or retire (needs its own ruling) | FAIL  assertion_10_settings_workspace_tab_wired: Settings page must import WorkspaceSectio |
| `test_adr245_three_layer_model.py` | pytest | drift — re-anchor or retire (needs its own ruling) | 8 failed, 14 passed in 1.03s |
| `test_adr299_kernel_universal_capability.py` | pytest | drift — one check behind | 1 failed, 12 passed in 0.20s |
| `test_adr307_permission_taxonomy.py` | pytest | drift — re-anchor or retire (needs its own ruling) | 2 failed, 15 passed in 0.35s |
| `test_adr320_permission_topology.py` | pytest | drift — re-anchor or retire (needs its own ruling) | 2 failed, 13 passed in 0.28s |
| `test_adr339_perception_economics.py` | script | drift — re-anchor or retire (needs its own ruling) | ADR-339 gate: 23 passed, 2 failed |
| `test_adr340_d8_machinery_fold.py` | pytest | drift — one check behind | 1 failed, 5 passed in 0.08s |
| `test_adr340_p4_legibility.py` | pytest | drift — one check behind | 1 failed, 3 passed in 0.08s |
| `test_adr341_two_settings_doors.py` | pytest | drift — re-anchor or retire (needs its own ruling) | 2 failed, 4 passed in 0.09s |
| `test_adr347_one_settings_door.py` | pytest | drift — one check behind | 1 failed, 6 passed in 0.08s |
| `test_adr373_rekey.py` | pytest | drift — one check behind | 1 failed, 17 passed in 0.80s |
| `test_adr373_sweep_spine.py` | pytest | drift — one check behind | 1 failed, 6 passed in 0.83s |
| `test_adr379_host_profiles.py` | script | drift — re-anchor or retire (needs its own ruling) | PASS  6 strip_widget_meta drops openai/* + ui.resourceUri, keeps domain/csp (the discovery |
| `test_adr386_member_lifecycle.py` | pytest | drift — one check behind | 1 failed, 12 passed, 4 skipped in 0.80s |
| `test_adr396_type_b_billing.py` | script | drift — a few checks behind the live surface | ADR-396 gate: 36/37 PASS |
| `test_adr412_chat_surface.py` | pytest | drift — re-anchor or retire (needs its own ruling) | 4 failed, 4 passed in 0.11s |
| `test_adr414_phase_d.py` | pytest | drift — one check behind | 1 failed, 3 passed in 0.13s |
| `test_adr414_phase_f_dp35.py` | pytest | drift — re-anchor or retire (needs its own ruling) | 2 failed, 1 passed in 1.25s |
| `test_adr415_channels_dissolved.py` | pytest | drift — re-anchor or retire (needs its own ruling) | 3 failed, 8 passed in 0.14s |
| `test_adr427_reader_classification.py` | script | drift — re-anchor or retire (needs its own ruling) | ADR-427 reader-classification ratchet: FAIL |
| `test_adr445_cap_choke_point.py` | script | drift — one check behind | ADR-445 §9 choke-point gate: 13 passed, 1 failed |
| `test_adr469_name_is_lifted.py` | script | CRASH — the gate reports nothing (moved path / deleted module) | KeyError: 'document' |
| `test_adr479_arrangement_plan.py` | script | drift — a few checks behind the live surface | FAIL: 19/22 checks |
| `test_adr480_flow_editing_grain.py` | script | drift — a few checks behind the live surface | 27/30 checks passed |
| `test_adr481_flow_chrome.py` | script | drift — a few checks behind the live surface | 24/25 checks passed |
| `test_adr482_flow_completion.py` | script | drift — re-anchor or retire (needs its own ruling) | 46/54 checks passed |
| `test_adr483_name_lift_and_ime.py` | script | drift — a few checks behind the live surface | ADR-483: 14/17 passed |
| `test_adr484_flow_chrome_leak.py` | script | drift — a few checks behind the live surface | ADR-484: 13/14 passed |
| `test_adr494_connector_registry.py` | script | drift — re-anchor or retire (needs its own ruling) | ✓ FE exports OFFERED_CONNECTORS derived from status |
| `test_adr496_my_ai_connections.py` | script | drift — re-anchor or retire (needs its own ruling) | FAILED 4 check(s): ['the account door renders the REAL roster component, not a twin', 'the |
| `test_adr500_roster_binding.py` | script | drift — re-anchor or retire (needs its own ruling) | FAILED 3 check(s): ['the created lane is tracked before the second call', 'a failed partic |
| `test_adr502_503_gate.py` | pytest | drift — one check behind | 1 failed, 14 passed in 0.82s |
| `test_adr520_stage_and_container.py` | script | drift — re-anchor or retire (needs its own ruling) | FAILED |
| `test_adr531_oauth_state_and_error_surface.py` | pytest | drift — re-anchor or retire (needs its own ruling) | 5 failed, 19 passed in 0.37s |
| `test_adr557_router_hardening.py` | script | drift — re-anchor or retire (needs its own ruling) | ok   no unclassified routed caller appeared |
| `test_adr573_connector_workspace_binding.py` | script | CRASH — the gate reports nothing (moved path / deleted module) | TypeError: unsupported operand type(s) for ¦: 'type' and 'NoneType' |
| `test_adr573_no_stale_deferral_claims.py` | script | drift — re-anchor or retire (needs its own ruling) | ✓ 3. no present-tense 'selection is deferred' claim survives on the MCP surface |
| `test_adr579_verb_grammar.py` | script | drift — a few checks behind the live surface | FAIL: 15/17 checks |
| `test_adr584_connector_names_its_workspace.py` | script | drift — re-anchor or retire (needs its own ruling) | PASS  D1. whoami is in the _INTEROP_VERBS roster  (roster: 10 verbs) |
| `test_adr590_rendered_face.py` | script | drift — re-anchor or retire (needs its own ruling) | ADR-590 gate FAILED — 2/20 |
| `test_adr612_agent_connector_opt_in.py` | script | drift — re-anchor or retire (needs its own ruling) | [LANE] reach opt-in lookup failed for editor: opt-in store unavailable |
| `test_adr614_cast_follows_the_registration.py` | script | drift — re-anchor or retire (needs its own ruling) | ADR-614 gate RED — 3 failing: |
| `test_adr631_vocabulary.py` | script | drift — re-anchor or retire (needs its own ruling) | 34 passed, 2 failed |
| `test_adr640_no_agent_record.py` | script | drift — re-anchor or retire (needs its own ruling) | RED — ADR-640: 1 check(s) failed |
| `test_agent_registry.py` | script | drift — re-anchor or retire (needs its own ruling) | ✓ a retired slug still resolves the name it signed as (display only) |
| `test_alpha_trader_pipeline_e2e.py` | script | drift — re-anchor or retire (needs its own ruling) | FAIL  STAGE C — client_order_id round-tripped the proposal_id (P&L attribution) — None |
| `test_authored_by_narrative.py` | pytest | drift — one check behind | 1 failed, 5 passed in 0.08s |
| `test_boot_import_cost.py` | script | drift — one check behind | 5 passed, 1 failed |
| `test_commit_f_autonomy_alignment.py` | pytest | drift — re-anchor or retire (needs its own ruling) | 8 failed, 3 passed in 4.32s |
| `test_files_selection_model.py` | script | drift — re-anchor or retire (needs its own ruling) | PASS  13d. both views keep a ring as the selected affordance |
| `test_folder_verbs_and_download.py` | script | drift — re-anchor or retire (needs its own ruling) | PASS  11. the client exposes restoreTrashGroup |
| `test_global_locator_strip.py` | pytest | drift — one check behind | 1 failed, 9 passed in 0.11s |
| `test_governance_verbs_are_owner_gated.py` | pytest | drift — re-anchor or retire (needs its own ruling) | 2 failed, 6 passed in 0.35s |
| `test_launch_lands_on_the_surface.py` | script | drift — re-anchor or retire (needs its own ruling) | RESULT: FAIL |
| `test_platform_registry.py` | pytest | drift — one check behind | 1 failed, 8 passed in 0.18s |
| `test_recents_view_unified.py` | pytest | drift — re-anchor or retire (needs its own ruling) | 2 failed, 2 passed in 0.08s |
| `test_resend_webhooks.py` | pytest | collection error — fixture or import | 1 error in 0.44s |
| `test_settings_polish_2026_08_21.py` | script | drift — re-anchor or retire (needs its own ruling) | FAIL  the page's own fallback agrees with it  the page would load one pane's data while th |
| `test_smart_defaults.py` | pytest | drift — one check behind | 1 failed, 7 passed in 0.09s |
| `test_supabase_client_teardown.py` | pytest | drift — re-anchor or retire (needs its own ruling) | 2 failed, 1 passed in 0.77s |
| `test_url_honest_to_foreground.py` | pytest | drift — one check behind | 1 failed, 6 passed in 0.08s |
| `test_voice_no_kernel_nouns_in_copy.py` | pytest | drift — one check behind | 1 failed in 2.14s |
| `test_workspace_file_path_normalization.py` | pytest | drift — one check behind | 1 failed, 2 passed in 0.08s |

## The shapes that recur

- **Studio-era gates (ADR-443…484, `test_studio_*`, `test_trash_visibility`)** — a dozen gates each a few checks
  behind: the Studio was re-cut by ADR-633/636/646 and these pin the pre-cut chrome. One re-anchor session, or one
  retirement ruling, per ADR.
- **ADR-209 phases 1–5** — the CLOSED ADR's phase gates hit the database (errors + timeouts); they are live
  probes wearing test names. Move under `scripts/operator/` or delete.
- **Retired-model gates** (`test_adr237_chat_role_grammar`, `test_adr241`, `test_adr245`, `test_commit_f_autonomy`,
  `test_quality_e2e` on `services.task_types`, `test_adr565/567` on `services.radar`) — the subject is deleted
  canon; delete the gate or re-point it at the ruling that deleted its subject.
- **Settings/shell gates** (`test_adr340_*`, `test_adr341`, `test_adr347`, `test_adr244`, `test_settings_polish`)
  — the pane model moved (ADR-491 D1); re-anchor to the live pane registry.

