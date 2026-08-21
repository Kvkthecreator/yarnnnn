/**
 * The conversation's COLUMN — the one measure every part of a chat composes on.
 *
 * A transcript is prose, and prose has a comfortable line length regardless of
 * how much room the window has. Edge-to-edge, a maximised chat set a line of
 * assistant text at ~1800px — roughly three times the measure typography has
 * converged on — and the eye loses its place returning to the next line.
 *
 * Declared HERE rather than inside `LanePanel` because three siblings compose
 * it and they live in two files: the header strip (`ConversationHeader`), the
 * transcript, and the composer (`LanePanel`). It began as a private constant in
 * `LanePanel`, which is exactly why the header kept spanning the full pane while
 * the conversation under it was centred — the strip could not see the number.
 * That is the same drift the pane contract exists to end (PANES.md §9: chrome
 * centres on the canvas column, not on the pane), one surface over.
 *
 * Set WIDER than the document measure (`FACE.measure`, 46rem ≈ 736px) on
 * purpose. A document is serif at a reading size; a transcript is sans at UI
 * size with bubbles, a gutter and an avatar rail, so the same character count
 * needs more room.
 *
 * It is a MAX, not a width — which is the whole small-screen story. Below it the
 * column IS the pane, so nothing changes on a phone, inside the chat drawer, or
 * in a bound app's 380px side pane.
 */
export const CONVERSATION_COLUMN_PX = 820;
