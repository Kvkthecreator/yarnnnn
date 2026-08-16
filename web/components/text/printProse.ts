'use client';

/**
 * printProse — Print / PDF for a markdown document (ADR-572 D4).
 *
 * ## Why this only became possible now
 *
 * ADR-571 shipped Export with Download-.md and Copy-AI-reference, and stated
 * plainly that print was withheld because "a prose document has no rendered
 * form, so print-to-PDF would be printing a textarea." That was true then. The
 * reading face (`ProseReader`) removes the blocker: there is now a rendered
 * form, so the same technique Docs uses becomes available one medium down.
 *
 * ## The technique is Docs', unchanged
 *
 * `StudioSurface::exportPrint` resolves the artifact to an HTML string, injects
 * an A4 print stylesheet, and hands it to a hidden iframe's `print()`. Nothing
 * about that is HTML-artifact-specific — it needs *a string of HTML*. Docs gets
 * its string from the artifact projection; Text gets its string by rendering
 * the markdown through the SAME renderer the canvas uses. One pipeline, two
 * consumers: what you print is what you were reading.
 *
 * The print sheet is a paper face, not the screen face — it names real serif
 * families (the screen's `font-serif` token doesn't exist in the iframe), sets
 * black-on-white, and adds the orphan/widow and break-after rules a screen
 * never needs. Nothing here writes to the file.
 */

import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';

/**
 * The paper stylesheet. Tailwind's `prose` classes do not exist inside the
 * print iframe (no stylesheet is carried over), so the document is styled from
 * scratch here on plain tags — which is also why the markup is rendered
 * WITHOUT the screen skin's class soup.
 */
const PRINT_CSS = `
  @page { size: A4; margin: 18mm; }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: #fff; color: #111;
    font-family: Georgia, 'Iowan Old Style', 'Times New Roman', serif;
    font-size: 11.5pt; line-height: 1.6;
  }
  main { max-width: 100%; }
  h1, h2, h3, h4, h5, h6 {
    font-family: Georgia, 'Iowan Old Style', 'Times New Roman', serif;
    font-weight: 600; line-height: 1.25; margin: 1.6em 0 0.5em;
    /* A heading must never be the last thing on a page. */
    break-after: avoid-page; page-break-after: avoid;
  }
  h1 { font-size: 21pt; margin-top: 0; }
  h2 { font-size: 16pt; }
  h3 { font-size: 13pt; }
  h4 { font-size: 11.5pt; }
  p, li { orphans: 3; widows: 3; }
  p { margin: 0 0 0.85em; }
  ul, ol { margin: 0 0 0.85em; padding-left: 1.4em; }
  li { margin: 0.2em 0; }
  blockquote {
    margin: 1em 0; padding-left: 1em;
    border-left: 2px solid #bbb; color: #444;
  }
  hr { border: 0; border-top: 1px solid #ccc; margin: 1.8em 0; }
  a { color: #111; text-decoration: underline; }
  code, pre { font-family: 'SFMono-Regular', Menlo, Consolas, monospace; font-size: 9.5pt; }
  pre {
    background: #f6f6f6; padding: 0.8em; border-radius: 4px;
    white-space: pre-wrap; word-wrap: break-word; break-inside: avoid-page;
  }
  table {
    border-collapse: collapse; width: 100%; margin: 1em 0;
    font-size: 10pt; break-inside: avoid-page;
  }
  th, td { border: 1px solid #bbb; padding: 5px 8px; text-align: left; }
  th { background: #f2f2f2; font-weight: 600; }
  img, svg { max-width: 100%; height: auto; }
`;

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

/**
 * Render the document and hand it to the browser's print-to-PDF.
 *
 * Mirrors Docs' `exportPrint` including the 60s grace before removing the
 * frame — the print dialog blocks in some browsers and not others, and
 * removing the frame under a modal dialog cancels the job.
 */
export function printProse(text: string, documentTitle: string): void {
  // The same renderer the canvas uses; no skin classes, because the print
  // sheet styles bare tags. Mermaid blocks render client-side after mount and
  // so cannot appear in a static string — they degrade to their source, which
  // is the honest fallback (the diagram's own text) rather than a blank.
  const body = renderToStaticMarkup(
    createElement(MarkdownRenderer, { content: text, scale: 'inherit' }),
  );
  const html =
    '<!doctype html><html><head><meta charset="utf-8">' +
    `<title>${escapeHtml(documentTitle)}</title>` +
    `<style>${PRINT_CSS}</style></head><body><main>${body}</main></body></html>`;

  const frame = document.createElement('iframe');
  frame.style.cssText = 'position:fixed;right:0;bottom:0;width:0;height:0;border:0;';
  frame.srcdoc = html;
  frame.onload = () => {
    try {
      frame.contentWindow?.focus();
      frame.contentWindow?.print();
    } finally {
      setTimeout(() => frame.remove(), 60_000);
    }
  };
  document.body.appendChild(frame);
}
