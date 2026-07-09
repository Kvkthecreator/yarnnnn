/**
 * AI-provider brand icons — the host-id → brand mark map for the Workspace
 * Members roster's AI-connection rows (ADR-431 §display follow-on).
 *
 * WHY a FE-side registry: like `web/lib/connectors/registry.tsx` (ADR-392) and
 * `WorkspaceMembersCard`'s `ROLE_META`, brand presentation is view-only chrome
 * the backend can't serve. The backend gives us a foreign-LLM principal's stable
 * HOST-ID (`chatgpt` | `claude.ai` | `gemini` | …, the ADR-379 registry key —
 * also the grant's `principal_id`); the operator-facing brand mark is the
 * frontend's job. This is the SINGLE source of that mapping — the Nth provider
 * is one more entry here, not a hardcoded branch (Singular Implementation).
 *
 * The keys mirror `api/mcp_server/presentation/hosts.py::HOSTS` ids exactly, so
 * a principal_id resolves to its mark without a translation layer. Unknown
 * host-ids fall back to the generic Cpu glyph (the pre-431 look) — legible,
 * just un-branded.
 *
 * Brand marks are the providers' official monochrome glyphs, rendered in
 * `currentColor` so they inherit the row's tone (no hardcoded brand color — the
 * roster is a neutral management surface, not a marketing card).
 */
import type { ReactNode } from 'react';
import { Cpu } from 'lucide-react';

// OpenAI mark (ChatGPT). Official monochrome glyph.
const OpenAIMark = (
  <svg viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4" aria-hidden="true">
    <path d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494zM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646zM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071.006l-4.83-2.786A4.504 4.504 0 0 1 2.34 7.872zm16.597 3.855l-5.833-3.387L15.119 7.2a.076.076 0 0 1 .071-.005l4.83 2.785a4.494 4.494 0 0 1-.676 8.105v-5.678a.79.79 0 0 0-.407-.667zm2.01-3.023l-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.83-2.787a4.5 4.5 0 0 1 6.68 4.66zm-12.64 4.135l-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08L8.704 5.46a.795.795 0 0 0-.393.681zm1.097-2.365l2.602-1.5 2.607 1.5v2.999l-2.597 1.5-2.607-1.5z" />
  </svg>
);

// Anthropic mark (Claude). Official monochrome glyph.
const AnthropicMark = (
  <svg viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4" aria-hidden="true">
    <path d="M17.304 3.541h-3.672l6.696 16.918H24Zm-10.608 0L0 20.459h3.744l1.37-3.553h7.005l1.369 3.553h3.744L10.536 3.541Zm-.371 10.223L8.616 7.65l2.291 6.114Z" />
  </svg>
);

// Google mark (Gemini) — the 4-color "G" reduced to a monochrome sparkle glyph
// (Gemini's own mark) so it reads in currentColor.
const GeminiMark = (
  <svg viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4" aria-hidden="true">
    <path d="M12 0c.62 6.44 5.56 11.38 12 12-6.44.62-11.38 5.56-12 12-.62-6.44-5.56-11.38-12-12C6.44 11.38 11.38 6.44 12 0Z" />
  </svg>
);

/**
 * host-id → brand mark. Keys mirror the ADR-379 registry ids
 * (api/mcp_server/presentation/hosts.py). A foreign-LLM grant's `principal_id`
 * IS the host-id, so callers key on it directly.
 */
const PROVIDER_MARKS: Record<string, ReactNode> = {
  chatgpt: OpenAIMark,
  'claude.ai': AnthropicMark,
  claude_desktop: AnthropicMark,
  claude_code: AnthropicMark,
  gemini: GeminiMark,
  // cursor / copilot / perplexity: no distinct mark yet → generic Cpu fallback.
};

/** The generic fallback glyph (the pre-431 look) for unknown providers. */
export const GenericProviderIcon = <Cpu className="h-4 w-4" aria-hidden="true" />;

/**
 * Resolve a foreign-LLM principal (its host-id) to its brand mark, or the
 * generic Cpu glyph when the provider has no mark. `principalId` is the grant's
 * principal_id (= the host-id for foreign-llm/a2a/platform rows).
 */
export function providerBrandIcon(principalId: string | null | undefined): ReactNode {
  if (!principalId) return GenericProviderIcon;
  return PROVIDER_MARKS[principalId] ?? GenericProviderIcon;
}

/** True when a distinct brand mark exists for this provider (not the fallback). */
export function hasProviderBrand(principalId: string | null | undefined): boolean {
  return !!principalId && principalId in PROVIDER_MARKS;
}
