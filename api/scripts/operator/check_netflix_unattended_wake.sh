#!/usr/bin/env bash
# Hat-B capture probe — ADR-345 unattended-cadence + Expected-Output behavioral proof.
#
# Reads the netflix-script-author (owner 23cc7951..., workspace 341ec5b9...)
# substrate AFTER an unattended judgment-mode cron wake to answer:
#   1. Did the judgment wake escalate (not balance_exhausted-skip)?   <- top-up worked
#   2. What did the Reviewer decide — author a compose organ, Clarify, or hold?
#   3. Did it emit the spurious "what cadence?" Clarify (the ADR-345 missing-contract
#      symptom the declared _expected_output.yaml is supposed to dissolve)?
#
# Run this AFTER 2026-06-24 05:00 UTC (outcome-reconciliation) or
# 2026-06-25 12:00 UTC (corpus-coherence-check, the cleanest judgment read).
#
# Substrate-receipts discipline: every claim must trace to an execution_event id,
# a revision id, or a proposal id. Quote them verbatim in any finding.

set -euo pipefail
PSQL="postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"
NETFLIX="23cc7951-b6c7-471c-ac38-657d931db6f7"
WS="341ec5b9-1cb6-4178-993e-94c7842d33b1"

echo "================ NETFLIX UNATTENDED-WAKE CAPTURE ($(date -u +%Y-%m-%dT%H:%M:%SZ)) ================"

echo "--- 1. Effective balance (must be > 0 for judgment wakes to run) ---"
psql "$PSQL" -c "SELECT get_effective_balance('$NETFLIX'::uuid) AS effective_balance, (SELECT balance_usd FROM workspaces WHERE id='$WS') AS raw_balance;"

echo "--- 2. Recent wakes (look for judgment-mode status=success, NOT balance_exhausted) ---"
psql "$PSQL" -c "SELECT created_at, slug, mode, status, error_reason, funnel_decision, ROUND(cost_usd::numeric,4) AS cost FROM execution_events WHERE user_id='$NETFLIX' ORDER BY created_at DESC LIMIT 10;"

echo "--- 3. Pending proposals / Clarify (ADR-345 missing-contract symptom = a 'what cadence?' Clarify) ---"
psql "$PSQL" -c "SELECT created_at, status, primitive, family, left(reviewer_reasoning, 120) AS reasoning FROM action_proposals WHERE user_id='$NETFLIX' ORDER BY created_at DESC LIMIT 6;"

echo "--- 4. Did the Reviewer author a compose organ? (new producer recurrence in the index) ---"
psql "$PSQL" -c "SELECT slug, status, schedule, last_run_at FROM tasks WHERE user_id='$NETFLIX' ORDER BY slug;"

echo "--- 5. Reviewer judgment trail (standing_intent + judgment_log + _recurrences revisions since the wake) ---"
psql "$PSQL" -c "SELECT created_at, authored_by, left(message, 80) AS message, path FROM workspace_file_versions WHERE user_id='$NETFLIX' AND (path LIKE '%standing_intent%' OR path LIKE '%judgment_log%' OR path LIKE '%_recurrences%') ORDER BY created_at DESC LIMIT 8;"

echo "================ END CAPTURE ================"
echo "READ: a clean ADR-345 close = a judgment wake with status=success (NOT balance_exhausted),"
echo "the Reviewer classifying the (B) structurally-can't shortfall and authoring a compose recurrence"
echo "WITHIN the floor — and NO spurious 'what cadence?' Clarify (the declared _expected_output dissolves it)."
