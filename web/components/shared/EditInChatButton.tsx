'use client';

/**
 * EditInChatButton — the unified "Edit in chat" affordance (ADR-215 R5).
 *
 * ADR-215 R5: every judgment-shaped mutation uses one label — "Edit in chat" —
 * rendered by this one component. The button seeds the ambient YARNNN rail
 * with a context-specific prompt and defers all further interaction to the
 * conversation.
 *
 * R4 corollary: this button NEVER belongs inside a `+` menu. The `+` menu is
 * a modal launcher only. Chat-shaped mutations live on the object's own detail
 * page as this button.
 *
 * R3 corollary HISTORICAL — superseded by ADR-236 Round 5 Cluster A
 * (2026-04-30). The original R3 said this button never belongs on a substrate
 * file's detail view because substrate files were edited directly on Files
 * via SubstrateEditor (preserving authored_by clarity). ADR-236 Cluster A
 * deleted SubstrateEditor — every file now routes through chat for edits
 * (chat invokes WriteFile per ADR-235; revision-chain attribution is
 * preserved via the same authored_by="operator" path). EditInChatButton is
 * now the canonical mutation surface for ALL operator-authored files,
 * including substrate. The R3 carve-out no longer applies.
 *
 * Two visual variants:
 *   - "default"  — full button with icon + label (the common case)
 *   - "compact"  — icon-only for dense toolbars (e.g. WorkDetail overflow)
 */

import { MessageSquare } from 'lucide-react';

export interface EditInChatButtonProps {
  /** Prompt text to seed the chat rail with. Must be non-empty. */
  prompt: string;
  /** Callback invoked with the prompt. Hosting page routes to sendMessage(). */
  onOpenChatDraft: (prompt: string) => void;
  /** Visual variant. Default: "default". */
  variant?: 'default' | 'compact';
  /** Override aria-label. Defaults to "Edit in chat". */
  ariaLabel?: string;
  /** Disable the button (e.g. while a mutation is pending elsewhere). */
  disabled?: boolean;
}

export function EditInChatButton({
  prompt,
  onOpenChatDraft,
  variant = 'default',
  ariaLabel,
  disabled = false,
}: EditInChatButtonProps) {
  const label = 'Edit in chat';
  const handleClick = () => {
    if (disabled) return;
    onOpenChatDraft(prompt);
  };

  if (variant === 'compact') {
    return (
      <button
        type="button"
        onClick={handleClick}
        disabled={disabled}
        aria-label={ariaLabel ?? label}
        title={label}
        className="inline-flex items-center justify-center w-7 h-7 rounded border border-border text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-50"
      >
        <MessageSquare className="w-3.5 h-3.5" />
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={disabled}
      aria-label={ariaLabel ?? label}
      className="inline-flex items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted/40 hover:text-foreground disabled:opacity-50"
    >
      <MessageSquare className="w-3.5 h-3.5" />
      {label}
    </button>
  );
}
