'use client';

/**
 * CopyField — a value the operator is meant to take away (ADR-587).
 *
 * One shape for "here is a string, carry it elsewhere": readOnly, monospace,
 * select-on-focus, a Copy button that confirms. Lifted from ShareDialog's
 * `linkField`, which had the pattern right and kept it private.
 *
 * The clipboard-denial fallback is the load-bearing part. `navigator.clipboard`
 * rejects under a denied permission, a non-secure origin, and in some embedded
 * webviews — and a Copy button that swallows that rejection reports success
 * while the clipboard still holds whatever it held before. That is the
 * incorrect-success class: the operator pastes a stale value into a chat and
 * blames the file. On rejection we SELECT the text instead, so ⌘C works and
 * the failure is visible rather than silent.
 *
 * The field renders the value it is given. Deciding WHICH spelling of a path
 * to hand over (relative vs the `yarnnn://` handle) belongs to the caller and
 * to `lib/interop/fileHandle`, never here.
 *
 * Two variants, ONE mechanism (ADR-587 D8):
 *   - `boxed` (default) — the bordered input + Copy button. For a properties
 *     block or a dialog, where the value is a row of its own.
 *   - `inline` — monospace text with a copy glyph that appears on hover. For a
 *     metadata strip, where a bordered box would out-weigh the title above it.
 * The variant is PRESENTATION only: same clipboard call, same denial fallback,
 * same selection behavior. A second component would have been a second place
 * for the fallback to be forgotten.
 */

import { useCallback, useRef, useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { cn } from '@/lib/utils';

export function CopyField({
  value,
  label,
  hint,
  className,
  variant = 'boxed',
}: {
  /** The exact string that lands on the clipboard. */
  value: string;
  /** Accessible name for the field — what the operator is copying. */
  label: string;
  /** Optional line under the field: what this string is FOR. */
  hint?: string;
  className?: string;
  /** Presentation only — see the note above. */
  variant?: 'boxed' | 'inline';
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [copied, setCopied] = useState(false);

  const copy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Denied / insecure origin / webview — hand the operator the selection
      // so ⌘C still works. Never report a copy that did not happen.
      inputRef.current?.select();
    }
  }, [value]);

  if (variant === 'inline') {
    return (
      <span className={cn('group relative inline-flex max-w-full items-center gap-1.5 align-middle', className)}>
        {/* The same hidden input the boxed variant focuses on a clipboard
            denial. Without it the inline variant would have NO fallback — it
            would silently do nothing where the boxed one hands over a
            selection, and the two variants would disagree about the one
            behaviour that matters most. */}
        <input
          ref={inputRef}
          readOnly
          value={value}
          tabIndex={-1}
          aria-hidden="true"
          className="pointer-events-none absolute h-px w-px opacity-0"
        />
        <span className="truncate font-mono text-[11px] text-muted-foreground" title={value}>
          {value}
        </span>
        <button
          type="button"
          onClick={() => void copy()}
          aria-label={`Copy ${label}`}
          title={`Copy ${label}`}
          className="shrink-0 rounded p-0.5 text-muted-foreground/60 opacity-0 transition-opacity hover:text-foreground focus:opacity-100 group-hover:opacity-100"
        >
          {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
        </button>
        {copied && <span className="shrink-0 text-[10px] text-muted-foreground">Copied</span>}
      </span>
    );
  }

  return (
    <div className={cn('flex flex-col gap-1', className)}>
      <div className="flex items-center gap-1.5">
        <input
          ref={inputRef}
          readOnly
          value={value}
          onFocus={(e) => e.currentTarget.select()}
          className="min-w-0 flex-1 rounded-md border border-border bg-background px-2.5 py-1.5 font-mono text-xs text-foreground outline-none focus:border-primary"
          aria-label={label}
        />
        <button
          type="button"
          onClick={() => void copy()}
          className="inline-flex shrink-0 items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs text-foreground transition-colors hover:bg-muted/60"
        >
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      {hint && <p className="text-[11px] leading-snug text-muted-foreground">{hint}</p>}
    </div>
  );
}
