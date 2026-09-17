'use client';

/**
 * AppSection — the component vocabulary, dispatched by kind (ADR-653 D3.b).
 *
 * ⭐ THE DATA-DRIVEN RENDERING PATH RETURNS. YARNNN had exactly one — a
 * string-`kind` → component table with an honest amber miss for an
 * unregistered kind — and it died as COLLATERAL in `e18e178`, an agent-
 * hardening commit, six weeks after ADR-435 explicitly preserved it ("shared
 * with WorkDetail, do NOT delete"). Nothing ever ruled that YARNNN should not
 * have one (ADR-653 §1.3). This is that path, rebuilt for the case that needs
 * it: a surface whose shape is DECLARED rather than mirrored.
 *
 * ⚠️ THE VOCABULARY IS THE PRODUCT SURFACE, and it is the riskiest single
 * decision in ADR-653 (D3.b). Too small and nothing composes; too large and
 * this is a page builder — the feature race the app-seam analysis says we
 * lose. The discipline, verbatim from the ADR: **a kind is added when a real
 * app needs it and cannot be served, never speculatively**, and the count of
 * refused kinds is the demand measurement.
 *
 * THIS FILE SHIPS TWO OF THE FOUR (APP-BUILDER-UX §8 step 3):
 *   files — what is here?        (shipped)
 *   note  — what did we decide?  (shipped)
 *   recent    — what moved?            (declared server-side, not yet drawn)
 *   needs-you — what is waiting on me? (declared server-side, not yet drawn)
 *
 * A kind the server admits but the client cannot yet draw renders the SAME
 * honest miss as an unknown one. That is deliberate: the alternative is a
 * blank band that reads as "this app has nothing", which is the failure the
 * amber box exists to prevent.
 *
 * ⚠️ NO LAYOUT PROPS, EVER. `SECTION_KEYS` server-side admits `kind`, `source`
 * and `title` and nothing else. The moment a section takes `columns` or
 * `align`, this is a page builder (ADR-653 D3.b / APP-BUILDER-UX §5).
 */

import { useEffect, useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import { api } from '@/lib/api/client';
import type { WorkspaceTreeNode } from '@/types';
import { FileListHeader, FileListRow } from '@/components/workspace/FileListView';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { Working } from '@/components/shared/Working';
import { useFileLoad } from '@/components/workspace/useFileLoad';
import { formatTimestamp } from '@/lib/formatting';
import { authorAccent, formatAuthorLabel } from '@/lib/workspace/attribution';
import { cn } from '@/lib/utils';

/** One declared section, as the server parsed it (`member_apps.SECTION_KEYS`). */
export interface AppSectionDecl {
  kind: string;
  source?: string;
  title?: string;
}

/**
 * The kinds THIS CLIENT can draw. Deliberately narrower than the server's
 * `SECTION_KINDS`: the server validates what a member may DECLARE, this
 * validates what we can currently PAINT, and the gap between them renders
 * honestly rather than blank.
 */
export const DRAWABLE_SECTION_KINDS = ['files', 'note'] as const;

/**
 * Absolute workspace path for a declared `source`, which is relative.
 *
 * ⚠️ THE TRAILING SLASH IS STRIPPED, and it is not cosmetic. `getTree` matches
 * its `root` exactly: `/workspace/inbound/uploads/operator` lists two files,
 * and the same path with a trailing slash returns **200 with zero rows**. A
 * member naming a folder writes `clients/` — ADR-653 D1's own example does —
 * so without this the section renders a convincing "Nothing here yet" over a
 * folder full of their work.
 *
 * Found by DRIVING the surface, not by reading it: an empty 200 is
 * indistinguishable from an empty folder at every layer above the query.
 */
function sourcePath(source: string | undefined): string {
  const rel = (source || '').trim().replace(/^\/+/, '').replace(/\/+$/, '');
  if (!rel) return '';
  return rel.startsWith('workspace/')
    ? `/${rel}`
    : `/workspace/${rel}`;
}

/**
 * The honest miss (ADR-653 D3.b) — the amber box `dispatchComponent` used to
 * render, restored with it.
 *
 * ⭐ Silence is the failure mode this exists to prevent. A section we cannot
 * draw must SAY so: a blank band is indistinguishable from an app that has
 * nothing in it, and a member cannot tell a limit from an emptiness.
 */
function SectionMiss({ kind }: { kind: string }) {
  return (
    <div className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2">
      <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600 dark:text-amber-500" />
      <div className="text-[12px] text-foreground/80">
        This app asks for a <span className="font-medium">{kind || 'nameless'}</span>{' '}
        section, which this workspace cannot show yet.
      </div>
    </div>
  );
}

/** The shared empty-state idiom (ADR-198 §3 — a 404 is empty, not error chrome). */
function SectionEmpty({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-md border border-dashed border-border/60 bg-muted/10 px-4 py-5 text-sm text-muted-foreground">
      {children}
    </div>
  );
}

/** `files` — a filtered region. *What is here?* */
function FilesSection({ source }: { source?: string }) {
  const root = sourcePath(source);
  const [rows, setRows] = useState<WorkspaceTreeNode[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!root) {
      setRows([]);
      return;
    }
    let cancelled = false;
    setRows(null);
    setFailed(false);
    (async () => {
      try {
        const result = await api.workspace.getTree(root);
        if (cancelled) return;
        // Defensive: a read path never trusts the served shape (house style).
        setRows(Array.isArray(result) ? result : []);
      } catch {
        if (cancelled) return;
        setRows([]);
        setFailed(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [root]);

  if (!root) {
    return <SectionEmpty>This section doesn&apos;t say which folder to show.</SectionEmpty>;
  }
  // ADR-651 — the ONE way to say wait. A bare spinner is the shape it replaced.
  if (rows === null) return <Working label="Loading…" />;
  if (failed) {
    return <SectionEmpty>Couldn&apos;t read this folder just now.</SectionEmpty>;
  }
  if (rows.length === 0) {
    return (
      <SectionEmpty>
        Nothing here yet. Files you add to this folder show up here.
      </SectionEmpty>
    );
  }

  // Folders first, then by name — the ContentViewer ordering, so a member
  // reads one order everywhere.
  const ordered = [...rows].sort((a, b) => {
    if (a.type !== b.type) return a.type === 'folder' ? -1 : 1;
    return a.name.localeCompare(b.name);
  });

  return (
    <div className="rounded-md border border-border/60">
      <FileListHeader />
      {ordered.map((node) => {
        const label = formatAuthorLabel(node.authored_by);
        return (
          <FileListRow
            key={node.path}
            name={node.name}
            kind={node.type}
            title={node.path}
            when={formatTimestamp(node.updated_at)}
            author={
              label ? (
                <span className="inline-flex items-center gap-1.5">
                  <span className={cn('h-1.5 w-1.5 rounded-full', authorAccent(node.authored_by))} />
                  {label}
                </span>
              ) : undefined
            }
          />
        );
      })}
    </div>
  );
}

/** `note` — a rendered `.md` from the workspace. *What did we decide?* */
function NoteSection({ source }: { source?: string }) {
  const path = sourcePath(source);
  // `cachedFirst` is the display-only opt-in: this mount never edits, so
  // remount continuity is free and correct here (useFileLoad's own rule).
  const { file, loading, notFound } = useFileLoad(path, { cachedFirst: true });

  if (!path) {
    return <SectionEmpty>This section doesn&apos;t say which note to show.</SectionEmpty>;
  }
  if (loading) return <Working label="Loading…" />;
  // ADR-198 §3 — a 404 is an empty state, never error chrome.
  if (notFound || !file) {
    return <SectionEmpty>This note hasn&apos;t been written yet.</SectionEmpty>;
  }
  const content = (file.content || '').trim();
  if (!content) return <SectionEmpty>This note is empty.</SectionEmpty>;

  return (
    <div className="rounded-md border border-border/60 px-4 py-3">
      {/* `linkifySubstrate` stays FALSE — chat bubbles only, never file content. */}
      <MarkdownRenderer content={content} />
    </div>
  );
}

export function AppSection({ section }: { section: AppSectionDecl }) {
  const kind = (section?.kind || '').trim();
  const body = (() => {
    switch (kind) {
      case 'files':
        return <FilesSection source={section.source} />;
      case 'note':
        return <NoteSection source={section.source} />;
      default:
        // `recent` and `needs-you` land here too, by design (see the header).
        return <SectionMiss kind={kind} />;
    }
  })();

  return (
    <section className="space-y-2">
      {section.title ? (
        <h3 className="text-[13px] font-medium text-foreground/80">{section.title}</h3>
      ) : null}
      {body}
    </section>
  );
}
