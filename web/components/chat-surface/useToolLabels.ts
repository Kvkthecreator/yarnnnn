'use client';

/**
 * useToolLabels — ADR-660. `toolLabels.ts` resolves a primitive name to a
 * catalog key; this words it. One hook so the streaming steps and the settled
 * footer cannot drift into two spellings of the same verb.
 */

import { useTranslations } from 'next-intl';
import { RECEIPT_LABEL_NS, TOOL_LABEL_NS, sentenceCase, type ToolLabelRef } from './toolLabels';

export function useToolLabels() {
  const t = useTranslations(TOOL_LABEL_NS);
  const tReceipt = useTranslations(RECEIPT_LABEL_NS);
  /** A ref's line, sentence-cased. A fallback (an unknown verb from a newer
   *  roster) is already humanized and carries no catalog entry to look up. */
  return (ref: ToolLabelRef): string =>
    ref.key === undefined
      ? ref.fallback
      : sentenceCase((ref.receipt ? tReceipt : t)(ref.key, ref.args));
}
