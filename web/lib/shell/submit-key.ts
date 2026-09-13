/**
 * submit-key — the ONE rule for "did the member press Enter to submit?"
 *
 * ## The defect this ends
 *
 * Twenty `onKeyDown` handlers across this app asked `e.key === 'Enter'` and
 * acted on it. Not one of them checked `isComposing`: a repo-wide grep for that
 * property returned only TypeScript's own `lib.dom.d.ts`.
 *
 * On an IME keyboard — Korean, Japanese, Chinese — Enter does double duty. While
 * a composition session is open it COMMITS the candidate text, and the browser
 * still fires `keydown` with `key === 'Enter'`. The member is choosing a
 * syllable; the app reads a submit.
 *
 * So composing 한글 in the chat composer SENT the message mid-word. The same
 * Enter renamed a lane, created a folder, invited a member, added a source —
 * every one of those handlers fired on the commit keystroke, and every one of
 * them looked correct in review because the bug is in a property nobody wrote.
 *
 * The browser gives two signals and both are needed: `isComposing` is the
 * standard one, and `keyCode === 229` is the legacy sentinel some IMEs (older
 * Android, a few desktop Korean IMEs) still report INSTEAD of setting the flag.
 * Checking only the first leaves those keyboards broken; that is why this is a
 * named helper and not an inline `&&`.
 *
 * ## Why a module and not twenty inline guards
 *
 * `useAutoResize` is the precedent — extracted because the composer-growth rule
 * was being re-derived per surface and drifting. A rule with twenty spellings
 * has twenty chances to be forgotten at the twenty-first call site, and this one
 * is invisible to tsc, to `next build`, and to every gate that does not type in
 * Korean. One home, one import, one thing to get right.
 *
 * Pure and total: no React, no DOM reads, no I/O — so a gate can CALL it.
 */

/** The shape both React's synthetic event and a native KeyboardEvent satisfy. */
export interface SubmitKeyEvent {
  key: string;
  shiftKey?: boolean;
  /** Set during an IME composition session. */
  isComposing?: boolean;
  /** Legacy IME sentinel — some keyboards report this INSTEAD of isComposing. */
  keyCode?: number;
  /** React's synthetic event carries the browser's event here. */
  nativeEvent?: { isComposing?: boolean; keyCode?: number };
}

/** The legacy "IME is processing this key" sentinel. */
const IME_KEYCODE = 229;

/**
 * Is this keystroke part of an in-flight IME composition?
 *
 * True means the member is still assembling a character and the key belongs to
 * the keyboard, not to the app. Reads the native event too: React's synthetic
 * event does surface `isComposing`, but a handler may be given either shape,
 * and the legacy keyCode only ever appears on the native one.
 */
export function isComposingKey(e: SubmitKeyEvent): boolean {
  return (
    e.isComposing === true ||
    e.nativeEvent?.isComposing === true ||
    e.keyCode === IME_KEYCODE ||
    e.nativeEvent?.keyCode === IME_KEYCODE
  );
}

/**
 * Does this keystroke mean "submit now"?
 *
 * Enter, not during a composition. Shift+Enter is excluded by default because
 * every multi-line composer in this app spells a newline that way; pass
 * `allowShift` for a single-line control where Shift+Enter has no other meaning
 * and should still submit.
 */
export function isSubmitKey(e: SubmitKeyEvent, { allowShift = false } = {}): boolean {
  if (e.key !== 'Enter') return false;
  if (isComposingKey(e)) return false;
  return allowShift || !e.shiftKey;
}

/**
 * Is the member typing on a SOFT keyboard — one with no Shift+Enter?
 *
 * A multi-line composer that submits on Enter needs an escape hatch for the
 * newline, and on every desktop that hatch is Shift+Enter. A touch keyboard has
 * no modifier row: there is no Shift+Enter to press, so Enter-to-send leaves NO
 * gesture that inserts a line break. That is why a second bullet could not be
 * typed into the chat composer at all — the first Enter shipped the message.
 *
 * The test is `(pointer: coarse)`, not a width or a user-agent string. Width
 * lies (a narrow desktop window is not a phone) and UA sniffing rots. `pointer`
 * reports the PRIMARY input's precision, which is exactly the question being
 * asked: a phone and a tablet report `coarse`; a laptop reports `fine`; an iPad
 * with a keyboard attached reports `fine` and correctly keeps Enter-to-send.
 *
 * SSR-safe: with no `window` it reports false, so the server renders the
 * desktop rule and hydration does not flip a gesture under the member's hands.
 */
export function prefersSoftKeyboard(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false;
  return window.matchMedia('(pointer: coarse)').matches;
}
