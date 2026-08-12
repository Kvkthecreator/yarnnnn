/** ADR-560 D6 — the model ↔ substrate round-trip.
 *
 * The model owns the flow REGION (`<main>`/`<article>` inner, ADR-480's
 * region), never the shell: the doctype, `<head>`, root tokens and the region
 * element itself stay strings, spliced by `replaceRegionInner`. Serialization
 * is deterministic and canonical; the id discipline (`normalizeStructure`
 * pass C — every block subject carries a unique `data-block-id`, minted in
 * document order, first-wins dedup) runs on the serialized DOM, so a fresh
 * document converges on its first write exactly as the legacy seam promised
 * (migration-by-use, ADR-209).
 */

import { DOMParser as PMDOMParser, DOMSerializer, Node as PMNode } from 'prosemirror-model';
import type { Schema } from 'prosemirror-model';

function domDoc(): Document {
  if (typeof document === 'undefined') {
    throw new Error('flow roundtrip needs a DOM document (browser or jsdom)');
  }
  return document;
}

export const FLOW_REGION_SEL = 'main, article';

/** Parse a flow region's inner HTML into a model document. */
export function parseRegion(schema: Schema, regionInner: string): PMNode {
  const host = domDoc().createElement('main');
  host.innerHTML = regionInner;
  return PMDOMParser.fromSchema(schema).parse(host, { preserveWhitespace: true });
}

/** The subjects the id discipline addresses (normalizeStructure pass C):
 *  every kinded block, every identified element, minus citation islands
 *  (which keep whatever identity they carry) and minus <li> (ADR-546 D2). */
function mintIds(region: HTMLElement): void {
  const seen = new Set<string>();
  const used = new Set(
    Array.from(region.querySelectorAll('[data-block-id]')).map(
      (el) => el.getAttribute('data-block-id') ?? '',
    ),
  );
  const fresh = (): string => {
    for (let i = 0; i < 10_000; i++) {
      const id = `b${Math.random().toString(36).slice(2, 6)}`;
      if (!used.has(id)) {
        used.add(id);
        return id;
      }
    }
    return `b${used.size.toString(36)}${Math.random().toString(36).slice(2, 4)}`;
  };
  for (const el of Array.from(region.querySelectorAll('[data-block], [data-block-id]'))) {
    if (el.hasAttribute('data-ref')) {
      const kept = el.getAttribute('data-block-id');
      if (kept) seen.add(kept);
      continue;
    }
    const id = el.getAttribute('data-block-id');
    if (!id || seen.has(id)) {
      const minted = fresh();
      el.setAttribute('data-block-id', minted);
      seen.add(minted);
    } else {
      seen.add(id);
    }
  }
}

/** The ownership rule, applied at serialize: an element INSIDE a kinded block
 *  carries no grammar/identity of its own (`normalizeStructure`'s
 *  `insideOwned` — a nested annotated element rides its parent). The model
 *  stamps every paragraph/list it serializes; this pass removes the stamps
 *  the legacy dialect never wrote, so simple lists, quotes and callout
 *  interiors round-trip byte-stably. Citation islands keep their identity
 *  (pass C's data-ref carve). */
function normalizeOwnership(region: HTMLElement): void {
  for (const el of Array.from(
    region.querySelectorAll('[data-block] [data-block], [data-block] [data-block-id]'),
  )) {
    if (el.hasAttribute('data-ref')) continue;
    el.removeAttribute('data-block');
    el.removeAttribute('data-block-id');
  }
}

/** The model holds `list_item > paragraph …` (a paragraph is where inline
 *  content lives); the substrate dialect writes `<li>text</li>`. Unwrap the
 *  single leading paragraph when nothing but nested lists follow it and the
 *  paragraph carries no attributes of its own. */
function tightenListItems(region: HTMLElement): void {
  for (const li of Array.from(region.querySelectorAll('li'))) {
    const kids = Array.from(li.children);
    const first = kids[0];
    if (!first || first.tagName !== 'P') continue;
    if (first.getAttributeNames().length > 0) continue;
    if (!kids.slice(1).every((k) => k.tagName === 'UL' || k.tagName === 'OL')) continue;
    while (first.firstChild) li.insertBefore(first.firstChild, first);
    first.remove();
  }
}

/** Serialize a model document to the flow region's inner HTML. */
export function serializeRegion(schema: Schema, doc: PMNode): string {
  const host = domDoc().createElement('main');
  const fragment = DOMSerializer.fromSchema(schema).serializeFragment(doc.content, {
    document: domDoc(),
  });
  host.appendChild(fragment);
  normalizeOwnership(host);
  tightenListItems(host);
  mintIds(host);
  return host.innerHTML;
}

/** Splice a serialized region back into the whole artifact string. The shell
 *  (doctype, head, root attrs, the region element and its own attributes) is
 *  untouched — the model never speaks for what it does not hold. */
export function replaceRegionInner(artifactHtml: string, regionInner: string): string {
  const parsed = new DOMParser().parseFromString(artifactHtml, 'text/html');
  const region = parsed.querySelector(FLOW_REGION_SEL);
  if (!region) return artifactHtml;
  region.innerHTML = regionInner;
  return '<!doctype html>\n' + (parsed.documentElement?.outerHTML ?? artifactHtml);
}

/** Read the flow region's inner HTML out of the whole artifact string. */
export function readRegionInner(artifactHtml: string): string | null {
  const parsed = new DOMParser().parseFromString(artifactHtml, 'text/html');
  const region = parsed.querySelector(FLOW_REGION_SEL);
  return region ? region.innerHTML : null;
}
