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
 */

import { useCallback, useRef, useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { cn } from '@/lib/utils';

export function CopyField({
  value,
  label,
  hint,
  className,
}: {
  /** The exact string that lands on the clipboard. */
  value: string;
  /** Accessible name for the field — what the operator is copying. */
  label: string;
  /** Optional line under the field: what this string is FOR. */
  hint?: string;
  className?: string;
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
