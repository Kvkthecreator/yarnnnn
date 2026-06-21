/**
 * Constants for the ADR-350 Standing band.
 *
 * PERSONA_STANDING_INTENT_PATH mirrors api/services/workspace_paths.py
 * `PERSONA_STANDING_INTENT_PATH = "persona/standing_intent.md"` (ADR-284) —
 * the Reviewer's forward-looking working state. Workspace-relative (the
 * getFile caller prefixes "/workspace/").
 */
export const PERSONA_STANDING_INTENT_PATH = 'persona/standing_intent.md';

/** Operator-facing hint pointing at where the output contract is declared
 *  (the ExpectedOutputCard in the Contract group of Workspace Settings). */
export const EXPECTED_OUTPUT_SETTINGS_HINT = 'Declare one in Workspace Settings → Contract.';
