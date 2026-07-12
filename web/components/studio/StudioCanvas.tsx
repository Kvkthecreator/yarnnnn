'use client';

/**
 * StudioCanvas — the Studio's artifact canvas (ADR-440 D2; pointing v1.1).
 *
 * A MOUNT in the ADR-436 sense: it takes the loaded artifact, runs the
 * reference projection pass (citations become displayable content; every
 * artifact-authored executable is STRIPPED), injects the pointer runtime,
 * and renders in an iframe sandboxed to `allow-scripts` ONLY — an opaque
 * origin with no same-origin access, no credentials, no top-navigation.
 * The only script that runs is ours (pointing).
 *
 * The canvas NEVER edits (ADR-236): pointing is deixis — a click selects an
 * element and reports {tag, text, dataRef} via postMessage; the surface
 * seeds the lane's composer with it. Every mutation still flows through the
 * lane.
 */

import { useEffect, useState } from 'react';
import type { WorkspaceFile } from '@/types';
import { resolveArtifactHtml } from '@/components/workspace/viewers/projection';

export interface PointerEvent2 {
  tag: string;
  text: string;
  dataRef: string | null;
  /** ADR-443 D6 — the enclosing block's address, when the hit is inside one. */
  blockId: string | null;
  blockKind: string | null;
  /** ADR-444 — the enclosing slide's index (deck layouts), for slide ops. */
  slideIndex: number | null;
}

interface StudioCanvasProps {
  /** The loaded artifact (the surface owns the fetch + reload cadence). */
  file: WorkspaceFile;
  /** Absolute workspace path — the base for relative citation resolution. */
  artifactPath: string;
  /** Pointing (v1.1): the member clicked an element in the canvas. */
  onPoint?: (p: PointerEvent2) => void;
  /** The member clicked empty space — selection cleared. */
  onPointClear?: () => void;
}

export function StudioCanvas({ file, artifactPath, onPoint, onPointClear }: StudioCanvasProps) {
  const [projected, setProjected] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (file.content == null) {
      setProjected(null);
      return;
    }
    resolveArtifactHtml(file.content, artifactPath, { pointer: true })
      .then((html) => !cancelled && setProjected(html))
      // NEVER fall back to raw content: the iframe allows scripts, and only
      // the projection pass strips artifact-authored executables. A blank
      // canvas beats an unstripped one.
      .catch(() => !cancelled && setProjected(''));
    return () => {
      cancelled = true;
    };
  }, [file, artifactPath]);

  useEffect(() => {
    const handler = (e: MessageEvent) => {
      const d = e.data;
      if (!d || typeof d !== 'object') return;
      if (d.type === 'yarnnn-point' && typeof d.tag === 'string') {
        onPoint?.({
          tag: d.tag,
          text: typeof d.text === 'string' ? d.text : '',
          dataRef: typeof d.dataRef === 'string' ? d.dataRef : null,
          blockId: typeof d.blockId === 'string' ? d.blockId : null,
          blockKind: typeof d.blockKind === 'string' ? d.blockKind : null,
          slideIndex: typeof d.slideIndex === 'number' ? d.slideIndex : null,
        });
      } else if (d.type === 'yarnnn-point-clear') {
        onPointClear?.();
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, [onPoint, onPointClear]);

  return (
    <iframe
      title={artifactPath}
      srcDoc={projected ?? ''}
      sandbox="allow-scripts"
      className="flex-1 w-full h-full border-0 bg-white"
    />
  );
}
