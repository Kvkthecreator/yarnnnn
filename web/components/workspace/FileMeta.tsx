'use client';

/**
 * FileMeta — the shared file-identity strip (ADR-436 §6).
 *
 * The icon + filename + type label that every mount's header shows. Before
 * this, `ContentViewer` and `ArtifactCard` each built it from `FileIcon` +
 * `describeViewerApplication` independently. This is the singular piece; each
 * mount still owns its OUTER frame (a document header vs. a compact card) and
 * composes this inside it.
 */

import { FileIcon } from '@/components/workspace/FileIcon';
import { describeViewerApplication } from '@/lib/file-types';
import { cn } from '@/lib/utils';
import type { WorkspaceFile } from '@/types';

interface FileMetaProps {
  file: WorkspaceFile;
  /** Icon size — 'sm' for a card, 'md' for a document header. */
  iconSize?: 'sm' | 'md';
  /** Extra metadata to render after the type label (verb, attribution, path). */
  trailing?: React.ReactNode;
  className?: string;
}

export function FileMeta({ file, iconSize = 'sm', trailing, className }: FileMetaProps) {
  const filename = file.path.split('/').pop() || file.path;
  return (
    <div className={cn('flex items-start gap-2 min-w-0', className)}>
      <FileIcon filename={filename} size={iconSize} />
      <div className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium">{filename}</span>
        <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-muted-foreground">
          <span>{describeViewerApplication(file.path, file.content_type)}</span>
          {trailing}
        </div>
      </div>
    </div>
  );
}
