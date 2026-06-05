/**
 * Content-shape render helpers (ADR-266 D5).
 *
 * Pure-TS string utilities for the render contract that L3 cards must honor:
 *   - Inline markdown is either parsed (rich) or stripped (plain). Never
 *     leaked as literal characters in operator-facing strings.
 *   - File paths (backtick-wrapped or absolute slashes) are stripped from
 *     extracted prose per ADR-244 D7 ("no file paths visible").
 *   - First-sentence extraction is the canonical degradation path when a
 *     parser cannot find a structured Primary Action / declaration.
 *
 * No React. Cards import these and pass results to inline markdown
 * renderers (markdown-to-jsx etc.) or render as plain text.
 */

/** Strip inline markdown (bold, italic, code-spans) from a string and
 *  return plain text. Leaves bullet markers and other line-leading syntax
 *  untouched — those are handled at the line level by parsers. */
export function stripInlineMarkdown(s: string): string {
  if (!s) return s;
  return (
    s
      // Bold: **text** or __text__ → text
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/__([^_]+)__/g, '$1')
      // Italic: *text* or _text_ → text  (only when not part of bold)
      .replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, '$1')
      .replace(/(?<!_)_([^_]+)_(?!_)/g, '$1')
      // Inline code: `text` → text. We strip rather than render <code>
      // because the chief leakage we're closing is backtick-wrapped file
      // paths (ADR-244 D7). If a card ever wants <code>, it should call
      // parseInlineMarkdown instead.
      .replace(/`([^`]+)`/g, '$1')
  );
}

/** Strip absolute /workspace/-prefixed file paths from a string per
 *  ADR-244 D7 ("no file paths visible"). Replaces the path with a
 *  generic noun so the surrounding sentence still reads.
 *
 *  Examples:
 *    "rules in `/workspace/...risk.md`" → "rules in (workspace file)"
 *    "see /workspace/constitution/MANDATE.md for"
 *      → "see (workspace file) for"
 *
 *  Backtick-wrapped paths are caught here too; the backticks themselves
 *  are then removed by stripInlineMarkdown when callers chain both. */
export function stripWorkspacePaths(s: string): string {
  if (!s) return s;
  return s
    // Backtick-wrapped /workspace/... paths
    .replace(/`\/workspace\/[^`]+\.[a-z0-9]+`/gi, '(workspace file)')
    // Backtick-wrapped relative paths to known config files
    .replace(/`\/?([_a-z]+\/)*_?[A-Z_]+\.[a-z]+`/g, '(workspace file)')
    // Bare /workspace/... paths (no backticks)
    .replace(/\/workspace\/[A-Za-z0-9._\-/]+\.[a-z0-9]+/gi, '(workspace file)');
}

/** Extract the first sentence of a string, trimmed. "First sentence"
 *  is the substring up to the first `. `, `! `, `? `, or end-of-string,
 *  whichever comes first.
 *
 *  Used by L3 cards in the schema-absent fallback path (ADR-266 D4) —
 *  when a parser cannot find a structured Primary Action, the card
 *  shows the first sentence of the file as a degraded headline.
 *
 *  Note: the period-followed-by-space heuristic intentionally treats
 *  abbreviations (e.g. "U.S.") as sentence enders. The cost is mild
 *  truncation in rare cases; the benefit is no NLP dependency. */
export function firstSentence(s: string): string {
  if (!s) return s;
  const trimmed = s.trim();
  const m = trimmed.match(/^[^.!?]*[.!?]/);
  return m ? m[0].trim() : trimmed;
}

/** Compose the three cleanup passes a card typically wants on extracted
 *  prose: strip workspace paths, strip inline markdown, collapse whitespace.
 *  Result is plain text safe to render in any operator-facing context. */
export function cleanProse(s: string): string {
  if (!s) return s;
  return stripInlineMarkdown(stripWorkspacePaths(s))
    .replace(/\s+/g, ' ')
    .trim();
}
