'use client';

/**
 * usePopoverDismissal — the ONE dismissal contract for every top-bar chrome
 * popover (2026-07-01 unification).
 *
 * Before: UserMenu, AttentionCenter, StatusItemPopover, and the TopBar dock
 * context menu each hand-rolled the same click-outside + Escape effect — four
 * near-identical copies, drifting in small ways (UserMenu listened even while
 * closed and had no Escape; the others gated on open + closed on Escape via one
 * or two effects). This is the Singular Implementation of that pattern.
 *
 * Contract: while `active`, a mousedown outside `ref` OR (unless disabled) an
 * Escape keypress calls `onDismiss`. Listeners are only attached while active —
 * nothing runs when the popover is closed.
 *
 * @param ref        container element; a mousedown inside it does NOT dismiss.
 * @param active     whether the popover is open (bool, or `state != null`).
 * @param onDismiss  called to close it (`() => setIsOpen(false)` etc.).
 * @param opts.escape  close on Escape. Default true.
 */

import { useEffect, type RefObject } from 'react';

export function usePopoverDismissal(
  ref: RefObject<HTMLElement | null>,
  active: boolean,
  onDismiss: () => void,
  opts?: { escape?: boolean }
) {
  const escape = opts?.escape ?? true;

  useEffect(() => {
    if (!active) return;

    const onMouseDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onDismiss();
      }
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onDismiss();
    };

    document.addEventListener('mousedown', onMouseDown);
    if (escape) document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onMouseDown);
      if (escape) document.removeEventListener('keydown', onKeyDown);
    };
  }, [ref, active, onDismiss, escape]);
}
