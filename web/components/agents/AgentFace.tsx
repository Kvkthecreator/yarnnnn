'use client';

/**
 * AgentFace — a colleague's picture (the operator's ruling, 2026-07-16).
 *
 * The face is an UPLOADED IMAGE, like a person's profile picture — not a
 * colour swatch (the shipped placeholder, which was debt §6.2: "a picture you
 * upload and never see is worse than no picture"), and not a generated
 * Freddie-style animation (which would make every agent a variant of the same
 * system creature — system-authored identity, cutting against "you named her").
 * An agent you HIRED having a face you CHOSE is the point.
 *
 * The URL chain (the ADR-395 bucket lane, the FileTile pattern): the manifest
 * stores a workspace PATH → the registry resolves it to the file's
 * `content_url` → this trades that for a fresh signed URL. A browser <img src>
 * can't carry a Bearer header, so the exchange must happen here.
 *
 * Fallback is the initial, never a broken image: an agent without a picture is
 * ordinary, and a colleague whose face fails to load should still be legible.
 *
 * ---------------------------------------------------------------------------
 * ADR-641 amendment (2026-09-08) — THE FALLBACK CARRIES THE CLASS ACCENT.
 *
 * ADR-641 gave every app glyph a hue and deliberately exempted the face,
 * drawing its line at "a glyph is not a face": a face is an uploaded PICTURE
 * (the 2026-07-16 operator ruling), and per-agent colour swatches were shipped
 * once, judged debt, and deleted. That ruling is UNTOUCHED — a picture still
 * renders as itself, unaccented, and there is still no per-agent hue.
 *
 * But the INITIAL is neither a picture nor a mark, and it was the one thing in
 * the shell that named a principal while saying nothing about their class:
 * driven on production, Designer rendered a grey "D" in the Slides chat pane
 * while the same agent wore violet two surfaces away on Agents. That is the
 * ADR-258 fault (colour disagreeing with itself), not the ADR-641 one it was
 * exempted for.
 *
 * ⭐ THE STRUCTURAL FIX, and the reason this cannot drift again: `kind` is a
 * REQUIRED prop, not an optional one with a default. The five call sites all
 * ALREADY KNEW the principal's class (`member_kind`, `MentionCandidate.kind`,
 * the agent-vs-people branch) and every one of them threw it away, passing
 * only display strings — so no amount of CSS here could have coloured the
 * fallback correctly, because the information never arrived. A required prop
 * means a NEW call site cannot compile without answering "who is this?", which
 * is the question the accent depends on. An optional `kind` with an `?? 'human'`
 * default would restore the exact silence this amendment deletes (the ADR-592
 * lesson: a declaration that nothing declares is not a declaration; and
 * ADR-633's "REQUIRED: no `?`, no default").
 *
 * The hue is `authorAccent`'s, not a new palette — a member who sees a violet
 * dot beside an agent-authored file in Files meets the same violet on that
 * agent's face in chat. One vocabulary, three renderings (dot, glyph, face).
 */

import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { faceAccent, type PrincipalKind } from '@/lib/workspace/attribution';

interface AgentFaceProps {
  name: string;
  /** The file's `content_url` (served by the registry), if they have a picture. */
  avatarUrl?: string | null;
  /**
   * WHO this is — the principal's class, which decides the fallback's accent.
   *
   * REQUIRED, deliberately: no `?`, no default. See the header note. Every
   * caller already holds this (`member_kind`, `MentionCandidate.kind`, or the
   * branch it is already rendering inside); passing it costs a word and is the
   * whole reason the accent cannot silently go grey again.
   */
  kind: PrincipalKind;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const SIZE: Record<string, string> = {
  sm: 'w-6 h-6 text-[10px]',
  md: 'w-9 h-9 text-xs',
  lg: 'w-14 h-14 text-lg',
};

export function AgentFace({ name, avatarUrl, kind, size = 'md', className }: AgentFaceProps) {
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!avatarUrl) return;
    // Already a usable URL (data:/blob:/http:) — no exchange needed.
    if (/^(https?:|data:|blob:)/i.test(avatarUrl)) {
      setUrl(avatarUrl);
      return;
    }
    let cancelled = false;
    api.documents
      .blobUrl(avatarUrl)
      .then((r) => !cancelled && setUrl(r.url))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [avatarUrl]);

  const base = cn(
    'rounded-full shrink-0 grid place-items-center overflow-hidden',
    SIZE[size],
    className,
  );

  if (url && !failed) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={url}
        alt={name}
        className={cn(base, 'object-cover')}
        onError={() => setFailed(true)}
      />
    );
  }

  // The PICTURE is unaccented (above) — the 2026-07-16 ruling. Only the
  // initial, which is a mark rather than a face, carries the class hue.
  return (
    <span className={cn(base, 'font-medium', faceAccent(kind))}>
      {(name || '?').slice(0, 1).toUpperCase()}
    </span>
  );
}
