'use client';

/**
 * StudioCanvas — the Studio's artifact canvas (ADR-440 D2).
 *
 * A MOUNT in the ADR-436 sense: it takes the loaded artifact, runs the
 * reference projection pass (resolveArtifactHtml — citations become
 * displayable content), and renders the result in a fully sandboxed iframe —
 * the same `sandbox=""` posture as the Web Viewer app. The canvas NEVER
 * edits (ADR-236): every mutation flows through the bound lane; the surface
 * refetches the file when the lane lands a write and this re-projects.
 */

import { useEffect, useState } from 'react';
import type { WorkspaceFile } from '@/types';
import { resolveArtifactHtml } from './resolveArtifactHtml';

interface StudioCanvasProps {
  /** The loaded artifact (the surface owns the fetch + reload cadence). */
  file: WorkspaceFile;
  /** Absolute workspace path — the base for relative citation resolution. */
  artifactPath: string;
}

export function StudioCanvas({ file, artifactPath }: StudioCanvasProps) {
  const [projected, setProjected] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (file.content == null) {
      setProjected(null);
      return;
    }
    resolveArtifactHtml(file.content, artifactPath)
      .then((html) => !cancelled && setProjected(html))
      .catch(() => !cancelled && setProjected(file.content ?? null));
    return () => {
      cancelled = true;
    };
  }, [file, artifactPath]);

  return (
    <iframe
      title={artifactPath}
      srcDoc={projected ?? file.content ?? ''}
      sandbox=""
      className="flex-1 w-full h-full border-0 bg-white"
    />
  );
}
