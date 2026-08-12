/** ADR-560 D1/D2 — the flow document model.
 *
 * The schema is the ONE grammar of the flow medium, derived from the served
 * vocabulary (`GET /api/studio/vocabulary`) rather than hand-listed: the rung
 * set, the recognized kind roster and the token names are inputs, so the
 * kernel registry finally has an EXECUTING reader (the ADR-539 shadow-registry
 * fault, closed for flow). The DOM dialect it parses and serializes is the
 * substrate dialect unchanged (ADR-560 D6): `data-block` kinds on ordinary
 * elements, `data-block-id` identity, `data-*` property tokens.
 *
 * Three invariants live here:
 *  - D3 preservation: markup the model does not understand round-trips
 *    verbatim (the `island` atom; the `wrap` mark) — a save cannot remove an
 *    annotation it cannot have authored, by construction.
 *  - GUARDED_ANNOTATIONS (ADR-547 D3's predicate): every `data-*` attribute
 *    except the runtime's own scaffolding is carried as a model attr.
 *  - The declared normalizations (and no others): out-of-rung headings clamp
 *    (ADR-539 D4), missing/duplicate ids are minted at serialize (ADR-511 D5),
 *    bare elements gain their promoted kind (`normalizeStructure` pass A),
 *    `b/i/strike` normalize to `strong/em/s` (ADR-446 D2), and single-`<p>`
 *    prose wrappers flatten to the paragraph itself (ADR-528: the paragraph
 *    IS the block).
 */

import { Schema } from 'prosemirror-model';
import type { Attrs, NodeSpec, MarkSpec, TagParseRule } from 'prosemirror-model';
import { captureInertHtml } from './sanitize';

export interface FlowSchemaConfig {
  /** The kernel's declared rung set (vocabulary.heading_rungs / FLOW_RUNGS). */
  rungs: number[];
  /** Every kind the served registry declares (vocabulary.blocks[].kind),
   *  used to tell "a kind this schema models" from "a kind preserved as an
   *  island" — both round-trip; only the first is editable. */
  kinds: string[];
}

/** The block-grain property tokens modeled as first-class attrs. Everything
 *  else `data-*` rides the `extra` bag (the GUARDED predicate's tail). */
const MODELED_TOKENS = ['align', 'indent', 'tone'] as const;

const MODELED_DATA = new Set([
  'data-block',
  'data-block-id',
  ...MODELED_TOKENS.map((t) => `data-${t}`),
]);

/** The projection runtime's own scaffolding — never substrate (ADR-547 D3). */
const SCAFFOLDING = new Set(['data-yarnnn-label', 'data-src-html']);

/** Kinds this schema gives a real editable node. The remainder of the served
 *  roster (table, metrics, chart-lead, gallery, button, component, …) are
 *  object-tier islands: preserved, selectable, never internally text-edited
 *  here (figure/chart captions ARE editable via the figure node). */
const TEXT_MODELED = new Set([
  'prose',
  'heading',
  'quote',
  'list',
  'numbered',
  'checklist',
]);

export interface BlockAttrShape {
  id: string | null;
  cls: string | null;
  align: string | null;
  indent: string | null;
  tone: string | null;
  extra: Record<string, string>;
}

const BLOCK_ATTR_SPEC = {
  id: { default: null as string | null },
  cls: { default: null as string | null },
  align: { default: null as string | null },
  indent: { default: null as string | null },
  tone: { default: null as string | null },
  extra: { default: {} as Record<string, string> },
};

function readBlockAttrs(el: Element): BlockAttrShape {
  const extra: Record<string, string> = {};
  for (const name of el.getAttributeNames()) {
    if (MODELED_DATA.has(name) || SCAFFOLDING.has(name)) continue;
    if (name.startsWith('data-')) extra[name] = el.getAttribute(name) ?? '';
  }
  return {
    id: el.getAttribute('data-block-id'),
    cls: el.getAttribute('class'),
    align: el.getAttribute('data-align'),
    indent: el.getAttribute('data-indent'),
    tone: el.getAttribute('data-tone'),
    extra,
  };
}

/** Canonical serialized attribute order: kind, id, class, modeled tokens,
 *  then the extra bag alphabetically. A canonical ORDER is a declared
 *  normalization; the parity gate holds serialization to idempotence and
 *  annotation-set preservation, not to byte order of legacy attrs. */
function writeBlockAttrs(kind: string | null, attrs: Attrs): Record<string, string> {
  const out: Record<string, string> = {};
  if (kind) out['data-block'] = kind;
  if (attrs.id) out['data-block-id'] = attrs.id as string;
  if (attrs.cls) out['class'] = attrs.cls as string;
  for (const t of MODELED_TOKENS) {
    if (attrs[t]) out[`data-${t}`] = attrs[t] as string;
  }
  const extra = (attrs.extra ?? {}) as Record<string, string>;
  for (const k of Object.keys(extra).sort()) out[k] = extra[k];
  return out;
}

/** A div is CONTENT (promotes to prose) only while it holds no block-level
 *  children — `normalizeStructure` pass A/B's predicate, executed at parse. */
const BLOCK_LEVEL_TAGS = new Set([
  'P', 'DIV', 'PRE', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6',
  'BLOCKQUOTE', 'TABLE', 'FIGURE', 'UL', 'OL', 'SECTION', 'MAIN',
  'ARTICLE', 'HEADER', 'FOOTER', 'HR', 'ASIDE', 'DETAILS',
]);
function holdsBlocks(el: Element): boolean {
  return Array.from(el.children).some((c) => BLOCK_LEVEL_TAGS.has(c.tagName));
}

function domDoc(): Document {
  if (typeof document === 'undefined') {
    throw new Error('flow schema needs a DOM document (browser or jsdom)');
  }
  return document;
}

function htmlToElement(html: string): HTMLElement {
  const tpl = domDoc().createElement('template');
  tpl.innerHTML = html;
  return (tpl.content.firstElementChild as HTMLElement) ?? domDoc().createElement('div');
}

export function buildFlowSchema(config: FlowSchemaConfig): Schema {
  const deepest = Math.max(...config.rungs);
  const knownKinds = new Set(config.kinds);

  /** figure/chart: the citation lead is opaque (inert) html; the caption is
   *  editable content. `getAttrs` captures everything except the caption. */
  const figureRule = (kind: 'figure' | 'chart'): TagParseRule => ({
    tag: kind === 'chart' ? 'figure[data-block="chart"]' : 'figure',
    getAttrs: (el: HTMLElement) => {
      const declared = el.getAttribute('data-block');
      if (kind === 'figure' && declared && declared !== 'figure') return false;
      const clone = el.cloneNode(true) as Element;
      clone.querySelector(':scope > figcaption')?.remove();
      const carrier = domDoc().createElement('div');
      carrier.innerHTML = clone.innerHTML;
      const lead = captureInertHtml(carrier);
      return { ...readBlockAttrs(el), kind, lead: lead.slice(5, -6) /* strip <div>…</div> */ };
    },
    contentElement: (el) =>
      (el as Element).querySelector(':scope > figcaption') ??
      domDoc().createElement('figcaption'),
  });

  const nodes: Record<string, NodeSpec> = {
    doc: { content: 'block+' },

    paragraph: {
      group: 'block',
      content: 'inline*',
      attrs: BLOCK_ATTR_SPEC,
      parseDOM: [
        {
          tag: 'p',
          getAttrs: (el: HTMLElement) =>
            el.getAttribute('data-block') === 'heading' ? false : readBlockAttrs(el),
        },
        // A single-<p> prose wrapper flattens to the paragraph itself, keeping
        // the wrapper's identity + tokens (the declared ADR-528 normalization).
        {
          tag: 'div[data-block="prose"]',
          contentElement: 'p',
          getAttrs: (el: HTMLElement) => {
            const kids = Array.from(el.children);
            if (kids.length !== 1 || kids[0].tagName !== 'P') return false;
            return readBlockAttrs(el);
          },
        },
        // A multi-<p> prose wrapper dissolves; its paragraphs stand alone.
        { tag: 'div[data-block="prose"]', skip: true },
        // A bare div holding only inline content promotes to prose
        // (PROMOTE_KIND.DIV) — but never a container, island, or citation.
        {
          tag: 'div',
          priority: 40,
          getAttrs: (el: HTMLElement) => {
            if (el.hasAttribute('data-block') || el.hasAttribute('data-ref')) return false;
            if (holdsBlocks(el)) return false;
            if ((el.textContent ?? '').trim() === '') return false;
            return readBlockAttrs(el);
          },
        },
      ],
      toDOM: (node) => ['p', writeBlockAttrs('prose', node.attrs), 0],
    },

    heading: {
      group: 'block',
      content: 'inline*',
      // rung 0 = the lede (`p.lede[data-block="heading"]`, ADR-518's scaffold):
      // heading KIND without a rung — outside the rung tree by design.
      attrs: { ...BLOCK_ATTR_SPEC, rung: { default: 1 } },
      parseDOM: [
        ...[1, 2, 3, 4, 5, 6].map(
          (level): TagParseRule => ({
            tag: `h${level}`,
            getAttrs: (el: HTMLElement) => ({
              ...readBlockAttrs(el),
              // ADR-539 D4 — intake clamps to the declared rung set.
              rung: config.rungs.includes(level) ? level : deepest,
            }),
          }),
        ),
        {
          tag: 'p[data-block="heading"]',
          priority: 60,
          getAttrs: (el: HTMLElement) => ({ ...readBlockAttrs(el), rung: 0 }),
        },
      ],
      toDOM: (node) => [
        node.attrs.rung ? `h${node.attrs.rung}` : 'p',
        writeBlockAttrs('heading', node.attrs),
        0,
      ],
    },

    pre: {
      group: 'block',
      content: 'text*',
      marks: '',
      code: true,
      defining: true,
      attrs: BLOCK_ATTR_SPEC,
      parseDOM: [{ tag: 'pre', preserveWhitespace: 'full', getAttrs: readBlockAttrs }],
      toDOM: (node) => ['pre', writeBlockAttrs('prose', node.attrs), 0],
    },

    list: {
      group: 'block',
      content: 'list_item+',
      attrs: { ...BLOCK_ATTR_SPEC, kind: { default: 'list' } },
      parseDOM: [
        {
          tag: 'ul',
          getAttrs: (el: HTMLElement) => {
            const declared = el.getAttribute('data-block');
            return {
              ...readBlockAttrs(el),
              kind: declared === 'checklist' ? 'checklist' : 'list',
            };
          },
        },
        {
          tag: 'ol',
          getAttrs: (el: HTMLElement) => ({ ...readBlockAttrs(el), kind: 'numbered' }),
        },
      ],
      toDOM: (node) => [
        node.attrs.kind === 'numbered' ? 'ol' : 'ul',
        writeBlockAttrs(node.attrs.kind as string, node.attrs),
        0,
      ],
    },

    // ADR-546 D2 — an <li> carries NO data-block-id and is not an addressing
    // subject; its depth is the block's rung, read from nesting.
    list_item: {
      content: 'block+',
      defining: true,
      attrs: { cls: { default: null as string | null } },
      parseDOM: [
        { tag: 'li', getAttrs: (el: HTMLElement) => ({ cls: el.getAttribute('class') }) },
      ],
      toDOM: (node) => ['li', node.attrs.cls ? { class: node.attrs.cls } : {}, 0],
    },

    quote: {
      group: 'block',
      content: 'block+',
      defining: true,
      attrs: BLOCK_ATTR_SPEC,
      parseDOM: [{ tag: 'blockquote', getAttrs: readBlockAttrs }],
      toDOM: (node) => ['blockquote', writeBlockAttrs('quote', node.attrs), 0],
    },

    divider: {
      group: 'block',
      atom: true,
      attrs: BLOCK_ATTR_SPEC,
      parseDOM: [{ tag: 'hr', getAttrs: readBlockAttrs }],
      toDOM: (node) => ['hr', writeBlockAttrs('divider', node.attrs)],
    },

    figure_block: {
      group: 'block',
      content: 'figcaption?',
      isolating: true,
      attrs: {
        ...BLOCK_ATTR_SPEC,
        kind: { default: 'figure' },
        lead: { default: '' },
      },
      parseDOM: [figureRule('chart'), figureRule('figure')],
      toDOM: (node) => {
        const el = domDoc().createElement('figure');
        const out = writeBlockAttrs(node.attrs.kind as string, node.attrs);
        for (const [k, v] of Object.entries(out)) el.setAttribute(k, v);
        el.innerHTML = node.attrs.lead as string;
        const caption = domDoc().createElement('figcaption');
        el.appendChild(caption);
        return { dom: el, contentDOM: caption };
      },
    },

    figcaption: {
      content: 'inline*',
      parseDOM: [{ tag: 'figcaption' }],
      toDOM: () => ['figcaption', 0],
    },

    // Callout / toggle / legacy structural containers: kinds Docs no longer
    // OFFERS but whose prose stays editable (ADR-528 D5's promise).
    container: {
      group: 'block',
      content: 'block+',
      defining: true,
      attrs: {
        ...BLOCK_ATTR_SPEC,
        tag: { default: 'div' },
        kind: { default: null as string | null },
      },
      parseDOM: [
        {
          tag: 'aside',
          getAttrs: (el: HTMLElement) => ({
            ...readBlockAttrs(el),
            tag: 'aside',
            kind: el.getAttribute('data-block') ?? 'callout',
          }),
        },
        {
          tag: 'details',
          getAttrs: (el: HTMLElement) => ({
            ...readBlockAttrs(el),
            tag: 'details',
            kind: el.getAttribute('data-block') ?? 'toggle',
          }),
        },
        {
          tag: 'section',
          getAttrs: (el: HTMLElement) => ({
            ...readBlockAttrs(el),
            tag: 'section',
            kind: el.getAttribute('data-block'),
          }),
        },
        {
          tag: 'div',
          priority: 45,
          getAttrs: (el: HTMLElement) => {
            // normalizeStructure pass B: a div enclosing blocks, itself
            // unkinded, is structure. Kinded divs are islands or prose.
            if (el.hasAttribute('data-block') || el.hasAttribute('data-ref')) return false;
            if (!holdsBlocks(el)) return false;
            return { ...readBlockAttrs(el), tag: 'div', kind: null };
          },
        },
      ],
      toDOM: (node) => [
        node.attrs.tag as string,
        writeBlockAttrs(node.attrs.kind as string | null, node.attrs),
        0,
      ],
    },

    // D3 — the preservation atom. Citation islands (table/gallery/standalone
    // data-ref), object kinds without a text interior (metrics, button,
    // component), and every kind the roster may grow later. Verbatim, inert,
    // selectable, movable, deletable — never internally edited, never dropped.
    island: {
      group: 'block',
      atom: true,
      attrs: { html: { default: '' } },
      parseDOM: [
        {
          tag: '[data-ref]',
          priority: 35,
          getAttrs: (el: HTMLElement) => ({ html: captureInertHtml(el) }),
        },
        {
          tag: '[data-block]',
          priority: 30,
          getAttrs: (el: HTMLElement) => {
            const kind = el.getAttribute('data-block') ?? '';
            // Text-modeled kinds and the modeled object kinds are handled by
            // their own rules above; everything else preserves.
            if (TEXT_MODELED.has(kind)) return false;
            if (kind === 'figure' || kind === 'chart' || kind === 'divider') return false;
            if (kind === 'callout' || kind === 'toggle') return false;
            return { html: captureInertHtml(el) };
          },
        },
        // Block-level tags with no better home preserve rather than dissolve.
        ...['address', 'dl', 'nav', 'form', 'video', 'audio', 'canvas', 'svg', 'table'].map(
          (tag): TagParseRule => ({
            tag,
            priority: 30,
            getAttrs: (el: HTMLElement) => ({ html: captureInertHtml(el) }),
          }),
        ),
      ],
      toDOM: (node) => ({ dom: htmlToElement(node.attrs.html as string) }),
    },

    text: { group: 'inline' },
  };

  const marks: Record<string, MarkSpec> = {
    // ADR-446 D2 — the source speaks semantic tags only; b/i normalize here.
    strong: {
      parseDOM: [{ tag: 'strong' }, { tag: 'b' }],
      toDOM: () => ['strong', 0],
    },
    em: {
      parseDOM: [{ tag: 'em' }, { tag: 'i' }],
      toDOM: () => ['em', 0],
    },
    strike: {
      parseDOM: [{ tag: 's' }, { tag: 'strike' }, { tag: 'del' }],
      toDOM: () => ['s', 0],
    },
    code: {
      parseDOM: [{ tag: 'code' }],
      toDOM: () => ['code', 0],
    },
    link: {
      attrs: { href: {}, title: { default: null as string | null } },
      inclusive: false,
      parseDOM: [
        {
          tag: 'a[href]',
          getAttrs: (el: HTMLElement) => ({
            href: el.getAttribute('href'),
            title: el.getAttribute('title'),
          }),
        },
      ],
      toDOM: (mark) => [
        'a',
        mark.attrs.title
          ? { href: mark.attrs.href, title: mark.attrs.title }
          : { href: mark.attrs.href },
        0,
      ],
    },
    // The kernel's span emphasis vocabulary (ADR-527): data-mark / data-highlight.
    mark_token: {
      attrs: { role: {} },
      parseDOM: [
        {
          tag: 'span[data-mark]',
          getAttrs: (el: HTMLElement) => ({ role: el.getAttribute('data-mark') }),
        },
      ],
      toDOM: (mark) => ['span', { 'data-mark': mark.attrs.role }, 0],
    },
    highlight_token: {
      attrs: { role: {} },
      parseDOM: [
        {
          tag: 'span[data-highlight]',
          getAttrs: (el: HTMLElement) => ({ role: el.getAttribute('data-highlight') }),
        },
      ],
      toDOM: (mark) => ['span', { 'data-highlight': mark.attrs.role }, 0],
    },
    // D3's inline tail: an unknown inline wrapper round-trips as a generic
    // mark carrying its tag + attributes, so its TEXT stays editable and its
    // wrapper is never dropped.
    wrap: {
      attrs: { tag: {}, attrsJson: { default: '{}' } },
      excludes: '',
      parseDOM: ['span', 'u', 'small', 'sub', 'sup', 'kbd', 'abbr', 'cite', 'time', 'var', 'samp', 'dfn', 'mark'].map(
        (tag): TagParseRule => ({
          tag,
          priority: 20,
          getAttrs: (el: HTMLElement) => {
            if (tag === 'span' && (el.hasAttribute('data-mark') || el.hasAttribute('data-highlight'))) {
              return false;
            }
            const attrs: Record<string, string> = {};
            for (const name of el.getAttributeNames()) {
              if (name.toLowerCase().startsWith('on')) continue;
              attrs[name] = el.getAttribute(name) ?? '';
            }
            return { tag, attrsJson: JSON.stringify(attrs) };
          },
        }),
      ),
      toDOM: (mark) => [
        mark.attrs.tag as string,
        JSON.parse(mark.attrs.attrsJson as string) as Record<string, string>,
        0,
      ],
    },
  };

  const schema = new Schema({ nodes, marks });
  // Executable content never enters the model at all — consistent with the
  // legacy commit door's sanitizeInner (ADR-446 D2).
  void knownKinds; // roster reserved for kind-aware affordances (turn-into)
  return schema;
}

/** The kinds a flow selection reports as TEXT tier (ADR-525/528). */
export const FLOW_TEXT_NODES = new Set([
  'paragraph',
  'heading',
  'list',
  'quote',
  'pre',
  'container',
  'figcaption',
]);
