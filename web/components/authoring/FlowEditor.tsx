'use client';

/** ADR-560 — the flow editing surface: a parent-mounted editor over the
 *  document MODEL. Prop-compatible with StudioCanvas's flow subset, so the
 *  surface's chrome (pane, toolbar, slash palette, outline, breadcrumb) keeps
 *  its handlers; what changes is what holds the document between keystrokes.
 *
 *  One writer (ADR-560 D1): typing, ops and paste are transactions against
 *  one EditorState. Commits serialize the model (canonical, idempotent — the
 *  ADR-560 gate's property) and land through the surface's existing write
 *  door via `onFlowEdit`. An external write (an op computed over the html
 *  string, a foreign/lane write) flows back in as a content-prop change and
 *  the model re-parses from it SYNCHRONOUSLY — same process, same tick, no
 *  async wall for a stale snapshot to hide behind (the ADR-540/547 class has
 *  no host here).
 *
 *  The sandboxed iframe remains the RENDER path for foreign artifacts
 *  (ADR-560 D4); this component renders only the member's own document, with
 *  opaque substrate (citation islands, preserved blocks) kept INERT —
 *  executables are stripped at model capture (flow/sanitize.ts).
 */

import { useCallback, useEffect, useImperativeHandle, useMemo, useRef, forwardRef } from 'react';
import { EditorState, NodeSelection, TextSelection, Plugin } from 'prosemirror-state';
import { EditorView } from 'prosemirror-view';
import type { NodeView } from 'prosemirror-view';
import { keymap } from 'prosemirror-keymap';
import { history, undo, redo } from 'prosemirror-history';
import { baseKeymap, chainCommands, exitCode } from 'prosemirror-commands';
import { splitListItem } from 'prosemirror-schema-list';
import { DOMSerializer, Node as PMNode } from 'prosemirror-model';
import type { Schema } from 'prosemirror-model';

import { buildFlowSchema } from '@/lib/authoring/flow/schema';
import {
  parseRegion,
  serializeRegion,
  readRegionInner,
} from '@/lib/authoring/flow/roundtrip';
import {
  pointPayload,
  rangePayload,
  stepRungCmd,
  fmtCmdToCommand,
  findBlockById,
  withMintedIds,
  blockIdPlugin,
  externalReplaceTr,
  type FlowRangeRung,
  type FlowPointPayload,
} from '@/lib/authoring/flow/commands';
import { FLOW_HOST_CLASS, hostStylesFrom } from '@/lib/authoring/flow/hostStyles';
import { resolveArtifactHtml } from '@/components/workspace/viewers/projection';
import type { WorkspaceFile } from '@/types';

const COMMIT_IDLE_MS = 2000;

/** Chrome the editor host needs regardless of the artifact's own skin.
 *  The host is a flex child of the canvas wrap: without an explicit flex/width
 *  it sizes to its CONTENT column and the page's own background shows beside
 *  it (the split-screen defect the first click-pass caught). And the model's
 *  list_item holds a PARAGRAPH while the substrate dialect writes bare
 *  `<li>text</li>` — the serializer tightens the substrate; this rule tightens
 *  the VIEW, so the two render identically. */
const HOST_BASE_CSS = `
.${FLOW_HOST_CLASS} { display: block; flex: 1 1 0%; min-width: 0; width: 100%; overflow: auto; height: 100%; background: var(--surface, #fff); }
.${FLOW_HOST_CLASS} main { white-space: pre-wrap; outline: none; caret-color: auto; min-height: 100%; }
.${FLOW_HOST_CLASS} main li > p { margin: 0; }
.${FLOW_HOST_CLASS} main .ProseMirror-selectednode { outline: 2px solid var(--accent, #b4540a); outline-offset: 2px; }
.${FLOW_HOST_CLASS} [data-ref] { user-select: none; }
`;

export interface FlowEditorHandle {
  /** Serialize + commit any pending model state NOW (the surface calls this
   *  before computing an op over the html string, so the op never applies to
   *  a stale document — ADR-547's discipline collapsed to one chokepoint). */
  flush: () => void;
}

interface FlowEditorProps {
  file: WorkspaceFile;
  artifactPath: string;
  headingRungs: number[];
  kinds: string[];
  blockLabels?: Record<string, string>;
  zoom?: number;
  onPoint?: (p: FlowPointPayload) => void;
  onPointClear?: () => void;
  onRange?: (blockIds: string[], rungs?: FlowRangeRung[]) => void;
  selectedBlockId?: string | null;
  /** The commit door — same handler StudioCanvas's flow commits used. */
  onFlowEdit?: (selector: string, newInner: string) => void;
  onSlashOpen?: (
    blockId: string,
    empty: boolean,
    rect: { left: number; top: number; bottom: number; width: number },
  ) => void;
  onSlashFilter?: (filter: string) => void;
  onSlashClose?: () => void;
  onSlashMove?: (delta: number) => void;
  onSlashEnter?: () => void;
  onSlashTaken?: (blockId: string, beforeInner: string | null, afterInner: string | null) => void;
  slashTake?: { filterLen: number; nonce: number } | null;
  slashInvoke?: { nonce: number } | null;
  fmtCmd?: { op: string; value: string | null; nonce: number } | null;
  scrollToBlock?: { blockId: string; nonce: number } | null;
  onScrollPos?: (pos: { y: number; slide: number | null }) => void;
}

export const FlowEditor = forwardRef<FlowEditorHandle, FlowEditorProps>(function FlowEditor(
  {
    file,
    artifactPath,
    headingRungs,
    kinds,
    blockLabels,
    zoom = 1,
    onPoint,
    onPointClear,
    onRange,
    selectedBlockId,
    onFlowEdit,
    onSlashOpen,
    onSlashFilter,
    onSlashClose,
    onSlashMove,
    onSlashEnter,
    onSlashTaken,
    slashTake,
    slashInvoke,
    fmtCmd,
    scrollToBlock,
    onScrollPos,
  },
  ref,
) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const mountRef = useRef<HTMLElement | null>(null);
  const viewRef = useRef<EditorView | null>(null);
  const schema = useMemo(
    () => buildFlowSchema({ rungs: headingRungs, kinds }),
    // The rung set and roster are kernel constants per served vocabulary —
    // stable for the life of the surface.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [JSON.stringify(headingRungs), JSON.stringify(kinds)],
  );
  const deepest = Math.max(...headingRungs);

  // ── Commit bookkeeping — the ONE writer's ledger ─────────────────────────
  /** The region inner this editor last serialized (its own commits) or last
   *  consumed (an external write it re-parsed). Incoming content equal to it
   *  is already represented in the model — never re-parse for our own echo. */
  const knownInnerRef = useRef<string | null>(null);
  const commitTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onFlowEditRef = useRef(onFlowEdit);
  onFlowEditRef.current = onFlowEdit;

  const commitNow = useCallback(() => {
    if (commitTimer.current) {
      clearTimeout(commitTimer.current);
      commitTimer.current = null;
    }
    const view = viewRef.current;
    if (!view) return;
    const inner = serializeRegion(schema, view.state.doc);
    if (inner === knownInnerRef.current) return; // nothing new to say
    knownInnerRef.current = inner;
    onFlowEditRef.current?.('main', inner);
  }, [schema]);

  const scheduleCommit = useCallback(() => {
    if (commitTimer.current) clearTimeout(commitTimer.current);
    commitTimer.current = setTimeout(commitNow, COMMIT_IDLE_MS);
  }, [commitNow]);

  useImperativeHandle(ref, () => ({ flush: commitNow }), [commitNow]);

  // ── Slash run tracking (the palette handshake, model-side) ───────────────
  const slashRef = useRef<{ blockId: string; from: number } | null>(null);
  const slashOpenRef = useRef(false);
  const cbRef = useRef({ onSlashOpen, onSlashFilter, onSlashClose, onSlashMove, onSlashEnter, onSlashTaken, onPoint, onPointClear, onRange, onScrollPos });
  cbRef.current = { onSlashOpen, onSlashFilter, onSlashClose, onSlashMove, onSlashEnter, onSlashTaken, onPoint, onPointClear, onRange, onScrollPos };
  const labelsRef = useRef(blockLabels);
  labelsRef.current = blockLabels;

  const closeSlash = useCallback(() => {
    if (slashOpenRef.current) {
      slashOpenRef.current = false;
      slashRef.current = null;
      cbRef.current.onSlashClose?.();
    }
  }, []);

  /** Open the palette for a '/' at `from` — shared by the typed gesture and
   *  the toolbar's Insert (one mechanism, two doors — ADR-505 D4). */
  const openSlashAt = useCallback((v: EditorView, from: number) => {
    const host = hostRef.current;
    if (!host || slashOpenRef.current) return;
    const $from = v.state.doc.resolve(from);
    if ($from.depth < 1) return;
    const block = $from.node(1);
    const blockId = (block.attrs?.id as string | null) ?? null;
    if (!blockId) return;
    const empty = block.textContent.trim() === '';
    slashRef.current = { blockId, from };
    slashOpenRef.current = true;
    const hostBox = host.getBoundingClientRect();
    const c = v.coordsAtPos(from);
    cbRef.current.onSlashOpen?.(blockId, empty, {
      left: c.left - hostBox.left,
      top: c.top - hostBox.top,
      bottom: c.bottom - hostBox.top,
      width: 0,
    });
  }, []);

  // ── The view ──────────────────────────────────────────────────────────────
  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const mount = document.createElement('main');
    host.appendChild(mount);
    mountRef.current = mount;

    const initialInner = readRegionInner(file.content ?? '') ?? '';
    let doc: PMNode;
    try {
      // Identity is named at MOUNT (withMintedIds), so an id-less legacy block
      // reads stably — a serialize-time-only mint is random and would churn
      // the block's identity on every commit.
      doc = withMintedIds(parseRegion(schema, initialInner));
    } catch (e) {
      console.error('[FLOW] parse failed — refusing to mount an empty editor:', e);
      return;
    }
    // The ledger opens at the CANONICAL form of the current content: a flush
    // or teardown with no member edit is a byte-equal no-op, so opening a
    // document never manufactures a revision (migration-by-use, ADR-546 D7 —
    // the canonicalization lands with the member's first real edit).
    knownInnerRef.current = serializeRegion(schema, doc);

    const emitSelection = (state: EditorState) => {
      const sel = state.selection;
      if (sel.empty || sel instanceof NodeSelection) {
        const p = pointPayload(state, labelsRef.current);
        cbRef.current.onRange?.([], []);
        if (p) cbRef.current.onPoint?.(p);
        else cbRef.current.onPointClear?.();
      } else {
        const { blockIds, rungs } = rangePayload(state);
        cbRef.current.onRange?.(blockIds, rungs);
      }
    };

    const selectionPlugin = new Plugin({
      view: () => ({
        update: (v: EditorView, prev: EditorState) => {
          if (!prev.selection.eq(v.state.selection) || prev.doc !== v.state.doc) {
            emitSelection(v.state);
            // Track the slash filter while the palette is open.
            if (slashOpenRef.current && slashRef.current) {
              const run = slashRef.current;
              const $c = v.state.selection.$from;
              const hit = findBlockById(v.state.doc, run.blockId);
              if (!hit || v.state.selection.empty === false || $c.pos <= run.from) {
                closeSlash();
              } else {
                const text = v.state.doc.textBetween(run.from + 1, $c.pos, '\n');
                if (text.includes('\n') || /\s/.test(text)) closeSlash();
                else cbRef.current.onSlashFilter?.(text);
              }
            }
          }
        },
      }),
    });

    const slashKeys = keymap({
      ArrowDown: () => (slashOpenRef.current ? (cbRef.current.onSlashMove?.(1), true) : false),
      ArrowUp: () => (slashOpenRef.current ? (cbRef.current.onSlashMove?.(-1), true) : false),
      Enter: () => (slashOpenRef.current ? (cbRef.current.onSlashEnter?.(), true) : false),
      Escape: () => (slashOpenRef.current ? (closeSlash(), true) : false),
    });

    const view = new EditorView(
      { mount },
      {
        state: EditorState.create({
          doc,
          plugins: [
            selectionPlugin,
            blockIdPlugin(),
            slashKeys,
            history(),
            keymap({
              'Mod-z': undo,
              'Mod-y': redo,
              'Mod-Shift-z': redo,
              // ADR-546 D4 — Tab steps the rung, ONE meaning, never a literal
              // tab, and never leaves the writing session.
              Tab: stepRungCmd(schema, 1, deepest),
              'Shift-Tab': stepRungCmd(schema, -1, deepest),
              'Mod-b': fmtCmdToCommand(schema, 'bold', null) ?? (() => false),
              'Mod-i': fmtCmdToCommand(schema, 'italic', null) ?? (() => false),
              'Mod-Enter': exitCode,
              Enter: chainCommands(splitListItem(schema.nodes.list_item), baseKeymap.Enter),
            }),
            keymap(baseKeymap),
          ],
        }),
        nodeViews: {
          island: (node) => islandView(node),
          figure_block: (node) => figureView(node),
        },
        handleTextInput: (v, from, _to, text) => {
          // ADR-456 W2 — '/' opens the palette; the filter is typed INTO the
          // document (the caret never leaves) and mirrored to the palette.
          if (text === '/') openSlashAt(v, from);
          return false; // never consume — the character lands either way
        },
        handleDOMEvents: {
          blur: () => {
            commitNow();
            return false;
          },
        },
      },
    );
    viewRef.current = view;
    emitSelection(view.state);

    const beforeUnload = () => commitNow();
    window.addEventListener('beforeunload', beforeUnload);
    const onScroll = () => cbRef.current.onScrollPos?.({ y: host.scrollTop, slide: null });
    host.addEventListener('scroll', onScroll, { passive: true });

    return () => {
      window.removeEventListener('beforeunload', beforeUnload);
      host.removeEventListener('scroll', onScroll);
      commitNow(); // the teardown commit is the MODEL's own state — never stale
      view.destroy();
      viewRef.current = null;
      mount.remove();
    };
    // The view lives for the artifact; content changes flow through the
    // re-parse effect below, never a remount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [schema, artifactPath]);

  // Wire transaction dispatch AFTER mount so scheduleCommit sees fresh refs.
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    view.setProps({
      dispatchTransaction: (tr) => {
        const v = viewRef.current;
        if (!v) return;
        v.updateState(v.state.apply(tr));
        if (tr.docChanged) scheduleCommit();
      },
    });
  }, [scheduleCommit]);

  // ── External writes re-enter the model (ops, foreign/lane writes) ────────
  useEffect(() => {
    const view = viewRef.current;
    if (!view || file.content == null) return;
    const incoming = readRegionInner(file.content);
    if (incoming == null) return;
    if (incoming === knownInnerRef.current) return; // our own echo
    // Not ours: re-parse, preserving the caret by block identity.
    const sel = view.state.selection;
    const $from = sel.$from;
    const keepId =
      $from.depth >= 1 ? (($from.node(1).attrs?.id as string | null) ?? null) : null;
    const keepOffset = $from.depth >= 1 ? $from.pos - $from.start(1) : 0;
    let doc: PMNode;
    try {
      doc = withMintedIds(parseRegion(schema, incoming));
    } catch (e) {
      console.error('[FLOW] external content failed to parse — model unchanged:', e);
      return;
    }
    // The ledger re-opens at the canonical form of the NEW model (not the
    // incoming bytes): a flush with no member edit stays a no-op, and the
    // canonicalization of a legacy-dialect write rides the next real edit.
    knownInnerRef.current = serializeRegion(schema, doc);
    // A TRANSACTION, never EditorState.create — creating fresh state wipes
    // the history plugin, so ⌘Z died on every pane op. As a transaction the
    // external change is one undoable step and older typing stays reachable
    // (see externalReplaceTr). The dispatch routes through the ordinary
    // pipeline; the ledger line above makes its commit echo a no-op.
    let tr = externalReplaceTr(view.state, doc);
    if (keepId) {
      const hit = findBlockById(tr.doc, keepId);
      if (hit) {
        const pos = Math.min(hit.pos + 1 + keepOffset, hit.pos + hit.node.nodeSize - 1);
        tr = tr.setSelection(TextSelection.near(tr.doc.resolve(pos)));
      }
    }
    view.dispatch(tr);
  }, [file.content, schema]);

  // ── Chrome commands (props → transactions) ───────────────────────────────
  const lastFmtNonce = useRef(0);
  useEffect(() => {
    if (!fmtCmd || fmtCmd.nonce === lastFmtNonce.current) return;
    lastFmtNonce.current = fmtCmd.nonce;
    const view = viewRef.current;
    if (!view) return;
    if (fmtCmd.op === 'link') {
      const href = window.prompt('Link to (URL):');
      if (href) {
        const { from, to } = view.state.selection;
        if (from !== to) {
          view.dispatch(view.state.tr.addMark(from, to, view.state.schema.marks.link.create({ href })));
        }
      }
      view.focus();
      return;
    }
    const cmd = fmtCmdToCommand(schema, fmtCmd.op, fmtCmd.value);
    if (cmd) {
      cmd(view.state, view.dispatch);
      scheduleCommit();
      view.focus();
    }
  }, [fmtCmd, schema, scheduleCommit]);

  const lastTakeNonce = useRef(0);
  useEffect(() => {
    if (!slashTake || slashTake.nonce === lastTakeNonce.current) return;
    lastTakeNonce.current = slashTake.nonce;
    const view = viewRef.current;
    const run = slashRef.current;
    slashOpenRef.current = false;
    slashRef.current = null;
    if (!view || !run) return;
    // Delete the '/'+filter run, then hand back the block's halves around the
    // caret — the same contract the runtime honored (onSlashTaken).
    const to = Math.min(run.from + 1 + slashTake.filterLen, view.state.doc.content.size);
    view.dispatch(view.state.tr.delete(run.from, to));
    const hit = findBlockById(view.state.doc, run.blockId);
    if (!hit) {
      cbRef.current.onSlashTaken?.(run.blockId, null, null);
      return;
    }
    const caret = view.state.selection.from;
    const rel = Math.max(0, Math.min(caret - (hit.pos + 1), hit.node.content.size));
    const serializer = DOMSerializer.fromSchema(schema);
    const half = (slice: PMNode['content']): string => {
      const carrier = document.createElement('div');
      carrier.appendChild(serializer.serializeFragment(slice, { document }));
      return carrier.innerHTML;
    };
    cbRef.current.onSlashTaken?.(
      run.blockId,
      half(hit.node.content.cut(0, rel)),
      half(hit.node.content.cut(rel)),
    );
  }, [slashTake, schema]);

  const lastInvokeNonce = useRef(0);
  useEffect(() => {
    if (!slashInvoke || slashInvoke.nonce === lastInvokeNonce.current) return;
    lastInvokeNonce.current = slashInvoke.nonce;
    const view = viewRef.current;
    if (!view) return;
    view.focus();
    // Type the '/' through the ordinary door — the same detection the typed
    // gesture uses, so everything downstream is one mechanism (ADR-505 D4).
    const { from } = view.state.selection;
    openSlashAt(view, from);
    view.dispatch(view.state.tr.insertText('/'));
  }, [slashInvoke, openSlashAt]);

  const lastScrollNonce = useRef(0);
  useEffect(() => {
    if (!scrollToBlock || scrollToBlock.nonce === lastScrollNonce.current) return;
    lastScrollNonce.current = scrollToBlock.nonce;
    const view = viewRef.current;
    if (!view) return;
    const hit = findBlockById(view.state.doc, scrollToBlock.blockId);
    if (!hit) return;
    view.dispatch(
      view.state.tr.setSelection(TextSelection.near(view.state.doc.resolve(hit.pos + 1))).scrollIntoView(),
    );
    view.focus();
  }, [scrollToBlock]);

  // Parent-side selection (outline / navigator click) reaches the model.
  useEffect(() => {
    const view = viewRef.current;
    if (!view || !selectedBlockId) return;
    const cur = pointPayload(view.state, labelsRef.current);
    if (cur?.blockId === selectedBlockId) return;
    const hit = findBlockById(view.state.doc, selectedBlockId);
    if (!hit) return;
    const tr = view.state.tr;
    if (hit.node.isAtom || !hit.node.isTextblock) {
      view.dispatch(tr.setSelection(NodeSelection.create(view.state.doc, hit.pos)).scrollIntoView());
    } else {
      view.dispatch(tr.setSelection(TextSelection.near(view.state.doc.resolve(hit.pos + 1))).scrollIntoView());
    }
  }, [selectedBlockId]);

  // ── The artifact's own look, scoped into the host (D4) ───────────────────
  const styleRef = useRef<HTMLStyleElement | null>(null);
  const rootAttrsRef = useRef<string[]>([]);
  useEffect(() => {
    let cancelled = false;
    const content = file.content;
    if (!content) return;
    // The projection (no runtimes, no pointer chrome) resolves citations +
    // design-system CSS; we lift its <head> styles and scope them.
    resolveArtifactHtml(content, artifactPath)
      .then((resolved) => {
        if (cancelled || !hostRef.current) return;
        const { css, rootAttrs } = hostStylesFrom(resolved);
        if (!styleRef.current) {
          styleRef.current = document.createElement('style');
          styleRef.current.setAttribute('data-yarnnn-flow-host', '');
          document.head.appendChild(styleRef.current);
        }
        styleRef.current.textContent = HOST_BASE_CSS + '\n' + css;
        for (const name of rootAttrsRef.current) hostRef.current.removeAttribute(name);
        rootAttrsRef.current = Object.keys(rootAttrs);
        for (const [k, v] of Object.entries(rootAttrs)) hostRef.current.setAttribute(k, v);
        // Islands: swap each preserved block's INERT markup for its resolved
        // projection (images → blob URLs, CSVs → tables/charts). Read-only
        // decoration on atom node views — never model state, never serialized.
        const doc = new DOMParser().parseFromString(resolved, 'text/html');
        const host = hostRef.current;
        for (const el of Array.from(host.querySelectorAll('[data-yarnnn-island]'))) {
          const id = el.getAttribute('data-yarnnn-island');
          const source = id ? doc.querySelector(`[data-block-id="${CSS.escape(id)}"]`) : null;
          if (source) {
            el.innerHTML = '';
            el.appendChild(document.importNode(source, true));
          }
        }
      })
      .catch((e) => console.error('[FLOW] style/island resolution failed:', e));
    return () => {
      cancelled = true;
    };
  }, [file.content, artifactPath]);
  useEffect(
    () => () => {
      styleRef.current?.remove();
      styleRef.current = null;
    },
    [],
  );

  return (
    <div
      ref={hostRef}
      className={FLOW_HOST_CLASS}
      style={zoom !== 1 ? ({ zoom } as React.CSSProperties) : undefined}
      onMouseDown={(e) => {
        // A click on the host's empty gutter clears the selection (the
        // yarnnn-point-clear contract).
        if (e.target === hostRef.current) onPointClear?.();
      }}
    />
  );
});

// ── Node views ────────────────────────────────────────────────────────────

/** A preserved block (citation island / object kind / unknown kind): inert
 *  markup now, swapped for its resolved projection when the style effect
 *  completes. The wrapper carries the block id so the resolver can find it. */
function islandView(node: PMNode): NodeView {
  const dom = document.createElement('div');
  dom.setAttribute('data-yarnnn-nodeview', 'island');
  const idMatch = /data-block-id="([^"]+)"/.exec(node.attrs.html as string);
  if (idMatch) dom.setAttribute('data-yarnnn-island', idMatch[1]);
  dom.innerHTML = node.attrs.html as string;
  dom.style.cursor = 'default';
  return {
    dom,
    update: (n) => {
      if (n.type !== node.type) return false;
      if (n.attrs.html !== node.attrs.html) {
        dom.innerHTML = n.attrs.html as string;
        node = n;
      }
      return true;
    },
    // The interior is opaque substrate — the model owns none of it.
    ignoreMutation: () => true,
    stopEvent: () => false,
  };
}

/** A figure/chart: opaque lead (the citation) + an editable caption. */
function figureView(node: PMNode): NodeView {
  const dom = document.createElement('figure');
  for (const [k, v] of Object.entries(figureAttrs(node))) dom.setAttribute(k, v);
  const lead = document.createElement('div');
  lead.setAttribute('data-yarnnn-figure-lead', '');
  lead.contentEditable = 'false';
  lead.innerHTML = node.attrs.lead as string;
  const idAttr = node.attrs.id as string | null;
  if (idAttr) lead.setAttribute('data-yarnnn-island', idAttr);
  const contentDOM = document.createElement('figcaption');
  dom.appendChild(lead);
  dom.appendChild(contentDOM);
  return {
    dom,
    contentDOM,
    update: (n) => {
      if (n.type !== node.type) return false;
      if (n.attrs.lead !== node.attrs.lead) lead.innerHTML = n.attrs.lead as string;
      node = n;
      return true;
    },
    ignoreMutation: (m) => !contentDOM.contains(m.target),
  };
}

function figureAttrs(node: PMNode): Record<string, string> {
  const out: Record<string, string> = { 'data-block': node.attrs.kind as string };
  if (node.attrs.id) out['data-block-id'] = node.attrs.id as string;
  if (node.attrs.cls) out['class'] = node.attrs.cls as string;
  return out;
}
