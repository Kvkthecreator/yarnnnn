/** ADR-560 D5 — the flow op surface, re-expressed as transactions.
 *
 * Every op keeps its ADR-ratified semantics (turn-into, block tokens, the
 * ADR-521 D3 format tier's Word rule + heading exemption, ADR-546 D4's
 * Tab-steps-the-rung) — implemented against the model, never the DOM. The
 * selection payloads the chrome consumes (yarnnn-point / yarnnn-range shapes)
 * are DERIVED here from the editor state, so the pane, the crumb and the menu
 * read the same facts they always did.
 */

import { DOMParser as PMDOMParser } from 'prosemirror-model';
import type { Node as PMNode, Schema, Attrs, ResolvedPos } from 'prosemirror-model';
import { NodeSelection, TextSelection, Plugin } from 'prosemirror-state';
import type { Command, EditorState, Transaction } from 'prosemirror-state';
import { sinkListItem, liftListItem } from 'prosemirror-schema-list';
import { closeHistory } from 'prosemirror-history';
import { toggleMark } from 'prosemirror-commands';

/** One covered block's rung — StudioCanvas's RangeRung shape (ADR-546 D3). */
export interface FlowRangeRung {
  heading: number | null;
  nesting: number;
  text?: string;
}

/** The yarnnn-point payload's flow subset (StudioCanvas PointerEvent2). */
export interface FlowPointPayload {
  tag: string;
  text: string;
  dataRef: string | null;
  blockId: string | null;
  blockKind: string | null;
  slideIndex: null;
  pageIndex: null;
  slot: null;
  arrange: null;
  label: string | null;
  headingId: string | null;
  headingText: string | null;
  tier: 'text' | 'object' | null;
}

const TEXT_KIND_OF: Record<string, string> = {
  paragraph: 'prose',
  heading: 'heading',
  quote: 'quote',
  pre: 'prose',
  container: 'container',
};

/** The substrate kind a model node speaks as (for payloads + turn-into). */
export function kindOfNode(node: PMNode): string {
  if (node.type.name === 'list') return node.attrs.kind as string;
  if (node.type.name === 'figure_block') return node.attrs.kind as string;
  if (node.type.name === 'divider') return 'divider';
  if (node.type.name === 'island') {
    const m = /data-block="([^"]+)"/.exec(node.attrs.html as string);
    return m ? m[1] : 'island';
  }
  if (node.type.name === 'container') return (node.attrs.kind as string | null) ?? 'container';
  return TEXT_KIND_OF[node.type.name] ?? node.type.name;
}

export function isObjectNode(node: PMNode): boolean {
  return node.type.name === 'island' || node.type.name === 'divider' || node.type.name === 'figure_block';
}

/** Walk the doc's top-level blocks (the addressing floor — ADR-511 D3). */
export function topBlocks(doc: PMNode): Array<{ node: PMNode; pos: number }> {
  const out: Array<{ node: PMNode; pos: number }> = [];
  doc.forEach((node, offset) => out.push({ node, pos: offset }));
  return out;
}

export function findBlockById(
  doc: PMNode,
  blockId: string,
): { node: PMNode; pos: number } | null {
  let found: { node: PMNode; pos: number } | null = null;
  doc.descendants((node, pos) => {
    if (found) return false;
    if (node.attrs && node.attrs.id === blockId) {
      found = { node, pos };
      return false;
    }
    return true;
  });
  return found;
}

/** The rung a top-level block carries (ADR-546 D1: heading rung; a list's
 *  interior nesting is per-item and reported as 0 at the block grain). */
function rungOf(node: PMNode): FlowRangeRung {
  if (node.type.name === 'heading' && (node.attrs.rung as number) > 0) {
    return { heading: node.attrs.rung as number, nesting: 0, text: node.textContent.slice(0, 120) };
  }
  return { heading: null, nesting: node.attrs?.indent ? Number(node.attrs.indent) : 0 };
}

/** The top-level blocks a selection intersects, in document order. */
export function coveredBlocks(state: EditorState): Array<{ node: PMNode; pos: number }> {
  const { from, to } = state.selection;
  const out: Array<{ node: PMNode; pos: number }> = [];
  state.doc.forEach((node, offset) => {
    const end = offset + node.nodeSize;
    if (end > from && offset < to) out.push({ node, pos: offset });
  });
  return out;
}

/** The yarnnn-range payload: covered block ids + their rungs (ADR-546 D3).
 *  Empty when the selection is collapsed — the range collapsed to a caret. */
export function rangePayload(state: EditorState): { blockIds: string[]; rungs: FlowRangeRung[] } {
  if (state.selection.empty) return { blockIds: [], rungs: [] };
  const covered = coveredBlocks(state).filter(({ node }) => !!node.attrs?.id || !isObjectNode(node));
  return {
    blockIds: covered.map(({ node }) => (node.attrs?.id as string | null) ?? ''),
    rungs: covered.map(({ node }) => rungOf(node)),
  };
}

/** The enclosing heading at-or-above a position (ADR-522 D4 — "this section"). */
function enclosingHeading(doc: PMNode, pos: number): { id: string | null; text: string | null } {
  let id: string | null = null;
  let text: string | null = null;
  doc.forEach((node, offset) => {
    if (offset > pos) return;
    if (node.type.name === 'heading' && (node.attrs.rung as number) > 0) {
      id = (node.attrs.id as string | null) ?? null;
      text = node.textContent.slice(0, 200);
    }
  });
  return { id, text };
}

/** The yarnnn-point payload for the block holding the caret / node selection. */
export function pointPayload(
  state: EditorState,
  labels?: Record<string, string>,
): FlowPointPayload | null {
  const sel = state.selection;
  let node: PMNode | null = null;
  let pos = 0;
  if (sel instanceof NodeSelection) {
    node = sel.node;
    pos = sel.from;
  } else {
    // The TOP-LEVEL block holding the caret (depth 1) — the addressing floor.
    const $from: ResolvedPos = sel.$from;
    if ($from.depth >= 1) {
      node = $from.node(1);
      pos = $from.before(1);
    }
  }
  if (!node) return null;
  const kind = kindOfNode(node);
  const object = isObjectNode(node);
  const heading = enclosingHeading(state.doc, pos);
  let tag = 'p';
  if (node.type.name === 'heading') tag = (node.attrs.rung as number) > 0 ? `h${node.attrs.rung}` : 'p';
  else if (node.type.name === 'list') tag = node.attrs.kind === 'numbered' ? 'ol' : 'ul';
  else if (node.type.name === 'quote') tag = 'blockquote';
  else if (node.type.name === 'divider') tag = 'hr';
  else if (node.type.name === 'figure_block') tag = 'figure';
  else if (node.type.name === 'island') {
    const m = /^<([a-z0-9-]+)/i.exec(node.attrs.html as string);
    tag = m ? m[1].toLowerCase() : 'div';
  }
  const refMatch = node.type.name === 'island' || node.type.name === 'figure_block'
    ? /data-ref="([^"]+)"/.exec(
        (node.type.name === 'island' ? (node.attrs.html as string) : (node.attrs.lead as string)) ?? '',
      )
    : null;
  return {
    tag,
    text: node.textContent.slice(0, 200),
    dataRef: refMatch ? refMatch[1] : null,
    blockId: (node.attrs?.id as string | null) ?? null,
    blockKind: kind,
    slideIndex: null,
    pageIndex: null,
    slot: null,
    arrange: null,
    label: labels?.[kind] ?? null,
    headingId: heading.id,
    headingText: heading.text,
    tier: object ? 'object' : 'text',
  };
}

// ── Identity in the model ───────────────────────────────────────────────────
//
// The chrome addresses blocks BY ID (the pane's ops, the slash anchor, the
// outline), so identity must live in the MODEL, not only at the serialize
// seam: a block born from Enter that waits for a commit to be named is a
// block the pane cannot see — and a serialize-time mint is random, so an
// unnamed block would churn its identity on every commit. normalizeStructure
// pass C's discipline (document order, first-wins dedup), applied where the
// blocks now live.

function mintInto(used: Set<string>): string {
  for (let i = 0; i < 10_000; i++) {
    const id = `b${Math.random().toString(36).slice(2, 6)}`;
    if (!used.has(id)) {
      used.add(id);
      return id;
    }
  }
  return `b${used.size.toString(36)}${Math.random().toString(36).slice(2, 4)}`;
}

/** Mint missing/duplicate top-level ids on a freshly parsed doc (mount time —
 *  BEFORE the commit ledger opens, so an id-less legacy document reads
 *  stably instead of phantom-writing on its first flush). */
export function withMintedIds(doc: PMNode): PMNode {
  const used = new Set<string>();
  doc.forEach((node) => {
    const id = node.attrs && 'id' in node.attrs ? (node.attrs.id as string | null) : null;
    if (id) used.add(id);
  });
  const seen = new Set<string>();
  const children: PMNode[] = [];
  let changed = false;
  doc.forEach((node) => {
    if (!node.attrs || !('id' in node.attrs)) {
      children.push(node);
      return;
    }
    const id = node.attrs.id as string | null;
    if (id && !seen.has(id)) {
      seen.add(id);
      children.push(node);
      return;
    }
    const fresh = mintInto(used);
    seen.add(fresh);
    children.push(node.type.create({ ...node.attrs, id: fresh }, node.content, node.marks));
    changed = true;
  });
  return changed ? doc.type.create(doc.attrs, children) : doc;
}

/** Keep every top-level block named as the member edits: Enter, paste and
 *  duplicate all create id-less (or id-duplicating) blocks; this names them
 *  in the same transaction cycle, so the chrome can address them at once. */
export function blockIdPlugin(): Plugin {
  return new Plugin({
    appendTransaction: (trs, _old, state) => {
      if (!trs.some((t) => t.docChanged)) return null;
      const used = new Set<string>();
      state.doc.forEach((node) => {
        const id = node.attrs && 'id' in node.attrs ? (node.attrs.id as string | null) : null;
        if (id) used.add(id);
      });
      const seen = new Set<string>();
      let tr: Transaction | null = null;
      state.doc.forEach((node, pos) => {
        if (!node.attrs || !('id' in node.attrs)) return;
        const id = node.attrs.id as string | null;
        if (id && !seen.has(id)) {
          seen.add(id);
          return;
        }
        const fresh = mintInto(used);
        seen.add(fresh);
        tr = (tr ?? state.tr).setNodeMarkup(pos, undefined, { ...node.attrs, id: fresh });
      });
      return tr;
    },
  });
}

/** An EXTERNAL write (a pane op's result, a foreign/lane write) re-enters the
 *  model as a TRANSACTION replacing the doc — never a fresh EditorState. The
 *  difference is undo: EditorState.create reinitializes plugin state, so the
 *  member's ⌘Z history died on every pane op. As a transaction, history
 *  survives and the external change is itself ONE undoable step — the same
 *  contract the legacy snapshot stack gave (everything replayable), now in
 *  the model's one history. */
export function externalReplaceTr(state: EditorState, next: PMNode): Transaction {
  // closeHistory: the external change must be ITS OWN undo step — without the
  // boundary, prosemirror-history coalesces it into the member's open typing
  // group and one Cmd-Z would swallow both.
  return closeHistory(state.tr.replaceWith(0, state.doc.content.size, next.content));
}

// ── Ops ─────────────────────────────────────────────────────────────────────

function setBlockAttrsById(
  tr: Transaction,
  doc: PMNode,
  blockId: string,
  patch: Record<string, unknown>,
): boolean {
  const hit = findBlockById(doc, blockId);
  if (!hit) return false;
  tr.setNodeMarkup(hit.pos, undefined, { ...hit.node.attrs, ...patch } as Attrs);
  return true;
}

/** setToken / setTokenMany (align · indent · tone) — null clears (absence is
 *  the default, ADR-461 B1). */
export function setTokenCmd(blockIds: string[], token: string, value: string | null): Command {
  return (state, dispatch) => {
    const tr = state.tr;
    let any = false;
    for (const id of blockIds) {
      if (setBlockAttrsById(tr, state.doc, id, { [token]: value })) any = true;
    }
    if (!any) return false;
    if (dispatch) dispatch(tr.scrollIntoView());
    return true;
  };
}

/** Turn-into (ADR-521 D2's structure tier): convert each named block to the
 *  target TEXT kind. Object kinds are never turn-into subjects on flow. */
export function convertBlocksCmd(schema: Schema, blockIds: string[], kind: string): Command {
  return (state, dispatch) => {
    let tr = state.tr;
    let any = false;
    for (const id of blockIds) {
      const hit = findBlockById(tr.doc, id);
      if (!hit) continue;
      const { node, pos } = hit;
      const base = {
        id: node.attrs.id ?? null,
        cls: null, // a conversion sheds the old kind's class (turn-into is a re-kind)
        align: node.attrs.align ?? null,
        indent: node.attrs.indent ?? null,
        tone: node.attrs.tone ?? null,
        extra: node.attrs.extra ?? {},
      };
      const inline = node.isTextblock
        ? node.content
        : node.type.name === 'list' || node.type.name === 'quote' || node.type.name === 'container'
          ? null // handled below — first textblock's content
          : null;
      const firstText = (() => {
        if (node.isTextblock) return node.content;
        let c: PMNode | null = null;
        node.descendants((n) => {
          if (c) return false;
          if (n.isTextblock) {
            c = n.content as unknown as PMNode;
            return false;
          }
          return true;
        });
        return (c ?? node.content) as typeof node.content;
      })();
      try {
        if (kind === 'prose') {
          tr = tr.replaceWith(pos, pos + node.nodeSize, schema.nodes.paragraph.create(base, inline ?? firstText));
        } else if (kind === 'heading' || /^h[1-6]$/.test(kind)) {
          const rung = /^h([1-6])$/.test(kind) ? Number(kind.slice(1)) : 2;
          tr = tr.replaceWith(
            pos,
            pos + node.nodeSize,
            schema.nodes.heading.create({ ...base, rung }, inline ?? firstText),
          );
        } else if (kind === 'quote') {
          tr = tr.replaceWith(
            pos,
            pos + node.nodeSize,
            schema.nodes.quote.create(base, schema.nodes.paragraph.create(null, inline ?? firstText)),
          );
        } else if (kind === 'list' || kind === 'numbered' || kind === 'checklist') {
          if (node.type.name === 'list') {
            tr.setNodeMarkup(pos, undefined, { ...node.attrs, kind });
          } else {
            tr = tr.replaceWith(
              pos,
              pos + node.nodeSize,
              schema.nodes.list.create({ ...base, kind }, [
                schema.nodes.list_item.create(null, [
                  schema.nodes.paragraph.create(null, inline ?? firstText),
                ]),
              ]),
            );
          }
        } else {
          continue; // never convert INTO an object kind on flow
        }
        any = true;
      } catch {
        continue; // an inconvertible shape (an island named by mistake) — skip
      }
    }
    if (!any) return false;
    if (dispatch) dispatch(tr.scrollIntoView());
    return true;
  };
}

export function deleteBlocksCmd(blockIds: string[]): Command {
  return (state, dispatch) => {
    let tr = state.tr;
    let any = false;
    for (const id of blockIds) {
      const hit = findBlockById(tr.doc, id);
      if (!hit) continue;
      tr = tr.delete(hit.pos, hit.pos + hit.node.nodeSize);
      any = true;
    }
    if (!any) return false;
    if (dispatch) dispatch(tr.scrollIntoView());
    return true;
  };
}

export function duplicateBlockCmd(blockId: string): Command {
  return (state, dispatch) => {
    const hit = findBlockById(state.doc, blockId);
    if (!hit) return false;
    // The copy sheds identity; the serialize seam mints a fresh id.
    const copy = hit.node.type.create({ ...hit.node.attrs, id: null }, hit.node.content, hit.node.marks);
    if (dispatch) dispatch(state.tr.insert(hit.pos + hit.node.nodeSize, copy).scrollIntoView());
    return true;
  };
}

/** ADR-546 D4 — Tab steps the rung, one meaning everywhere: nest in a list
 *  (clamped to the declared depth), step the prose indent elsewhere. */
export function stepRungCmd(schema: Schema, dir: 1 | -1, deepest: number): Command {
  return (state, dispatch, view) => {
    const { $from } = state.selection;
    // In a list item → nest / un-nest, clamped to the deepest declared rung.
    for (let d = $from.depth; d > 0; d--) {
      if ($from.node(d).type === schema.nodes.list_item) {
        if (dir === 1) {
          let depth = 0;
          for (let k = d; k > 0; k--) if ($from.node(k).type === schema.nodes.list) depth++;
          if (depth >= deepest) return true; // clamp — the gesture lands, the rung holds
          return sinkListItem(schema.nodes.list_item)(state, dispatch, view);
        }
        return liftListItem(schema.nodes.list_item)(state, dispatch, view);
      }
    }
    // In prose → step the indent token (the addressable prose rung).
    const block = $from.depth >= 1 ? $from.node(1) : null;
    if (!block || !block.attrs || isObjectNode(block)) return false;
    const cur = block.attrs.indent ? Number(block.attrs.indent) : 0;
    const next = Math.max(0, Math.min(deepest, cur + dir));
    if (next === cur) return true;
    if (dispatch) {
      dispatch(
        state.tr.setNodeMarkup($from.before(1), undefined, {
          ...block.attrs,
          indent: next === 0 ? null : String(next),
        }),
      );
    }
    return true;
  };
}

/** ADR-521 D3 — the deterministic toggle (the Word rule) with the heading
 *  exemption for bold: prosemirror's toggleMark already applies-if-any-lacks;
 *  the exemption narrows the RANGE test so a heading can never be the reason
 *  a span un-bolds, and bolding a heading is a no-op. */
export function fmtCmdToCommand(
  schema: Schema,
  op: string,
  value: string | null,
): Command | null {
  const wrapMark = (tag: string) => (state: EditorState, dispatch?: (tr: Transaction) => void) =>
    toggleMark(schema.marks.wrap, { tag, attrsJson: '{}' })(state, dispatch);
  switch (op) {
    case 'bold':
      return (state, dispatch) => {
        // Heading exemption: if the selection lies entirely in headings, no-op.
        const covered = coveredBlocks(state);
        if (covered.length > 0 && covered.every(({ node }) => node.type.name === 'heading')) {
          return true;
        }
        return toggleMark(schema.marks.strong)(state, dispatch);
      };
    case 'italic':
      return toggleMark(schema.marks.em);
    case 'strike':
      return toggleMark(schema.marks.strike);
    case 'underline':
      return wrapMark('u');
    case 'code':
      return toggleMark(schema.marks.code);
    case 'mark':
    case 'highlight': {
      const type = op === 'mark' ? schema.marks.mark_token : schema.marks.highlight_token;
      return (state, dispatch) => {
        const { from, to } = state.selection;
        if (from === to) return false;
        if (dispatch) {
          // Set-or-clear, never toggle: switching roles (accent → warn) must
          // RE-COLOR, and toggleMark would read the existing mark of the other
          // role as "already on" and remove instead.
          let tr = state.tr.removeMark(from, to, type);
          if (value != null) tr = tr.addMark(from, to, type.create({ role: value }));
          dispatch(tr);
        }
        return true;
      };
    }
    case 'clear':
      return (state, dispatch) => {
        const { from, to } = state.selection;
        if (from === to) return false;
        if (dispatch) {
          let tr = state.tr;
          for (const m of Object.values(schema.marks)) tr = tr.removeMark(from, to, m);
          dispatch(tr);
        }
        return true;
      };
    default:
      return null; // unknown op — never fall through (the runtime's own rule)
  }
}

/** Insert a served fragment (slash / picker) relative to a block. */
export function insertFragmentCmd(
  schema: Schema,
  fragmentEl: HTMLElement,
  anchor: { blockId: string; replaceEmpty: boolean },
): Command {
  return (state, dispatch) => {
    const hit = findBlockById(state.doc, anchor.blockId);
    if (!hit) return false;
    const slice = PMDOMParser.fromSchema(schema).parse(fragmentEl, { preserveWhitespace: true });
    const nodes: PMNode[] = [];
    slice.forEach((n) => nodes.push(n));
    if (nodes.length === 0) return false;
    let tr = state.tr;
    const after = hit.pos + hit.node.nodeSize;
    tr = tr.insert(after, nodes);
    if (anchor.replaceEmpty && hit.node.textContent.trim() === '' && kindOfNode(hit.node) !== 'heading') {
      tr = tr.delete(hit.pos, hit.pos + hit.node.nodeSize);
    }
    if (dispatch) {
      const sel = TextSelection.near(tr.doc.resolve(Math.min(after, tr.doc.content.size)), 1);
      dispatch(tr.setSelection(sel).scrollIntoView());
    }
    return true;
  };
}
