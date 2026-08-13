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
// The vendor marks live in ONE place (`components/ui/PlatformIcons.tsx`, which
// already owned them for the MCP principal badge). This module owns the
// ENGINE-ID → mark mapping, not the artwork. Before this, both files drew their
// own Claude and ChatGPT paths and the Claude ones were different glyphs
// entirely — same vendor, two brands, depending which surface you looked at.
import { ChatGPTIcon, ClaudeIcon, GeminiIcon } from '@/components/ui/PlatformIcons';

// ChatGPT + Claude marks are IMPORTED, never re-drawn (see the Claude note
// below). Two hand-copied SVG paths for one vendor is how the marks diverged.
const OpenAIMark = <ChatGPTIcon className="h-4 w-4" />;

// Claude mark — the PRODUCT's sunburst, not the Anthropic corporate "A"
// (operator ruling 2026-08-13).
//
// ⚠️ ONE MARK, ONE SOURCE. This file and `components/ui/PlatformIcons.tsx` each
// carried a Claude glyph and they were DIFFERENT: this one drew the Anthropic
// corporate "A" while the MCP principal badge drew the sunburst — so the same
// vendor appeared as two different brands on two surfaces of one product (the
// notification panel vs. the chat header, operator-observed). The mark is now
// IMPORTED from PlatformIcons rather than re-drawn, so a second copy cannot
// silently diverge again.
//
// WHY THE PRODUCT, NOT THE COMPANY: every other mark here names the product a
// member recognizes — ChatGPT (not OpenAI), Gemini (not Google). "Anthropic"
// was the odd one out, and a member choosing an engine is choosing Claude.
const AnthropicMark = <ClaudeIcon className="h-4 w-4" />;

// Gemini — the product's own four-point spark (never Google's 4-color "G"),
// for the same reason Claude is not the Anthropic "A": the mark names the
// PRODUCT a member picks. The artwork moved to PlatformIcons with the others.
const GeminiMark = <GeminiIcon className="h-4 w-4" />;

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

// ---------------------------------------------------------------------------
// Engines (ADR-558 D5) — the same marks, keyed by the LANE_MODELS prefix
// ---------------------------------------------------------------------------
//
// WHY HERE AND NOT A SECOND MODULE. The marks above are keyed by ADR-379
// HOST-ID (`chatgpt`, `claude.ai`) — the MCP connector's identity. An engine is
// named `provider/model` (`anthropic/claude-sonnet-4-6`), a different key space
// for the same brands. Copying the SVGs into a chat-side module would be two
// homes for one fact; the resolver below maps the engine's provider prefix onto
// the marks that already exist.
//
// Chat is the engine surface (ADR-558 D1), so wherever an engine is named it
// carries its maker's mark.

/** provider prefix (from `provider/model`) → the same brand marks. */
const ENGINE_PROVIDER_MARKS: Record<string, ReactNode> = {
  anthropic: AnthropicMark,
  openai: OpenAIMark,
  gemini: GeminiMark,
  // deepseek: no official monochrome glyph vendored yet → generic Cpu.
};

/** `anthropic/claude-sonnet-4-6` → `anthropic`. Bare names return themselves. */
export function engineProvider(model: string | null | undefined): string {
  if (!model) return '';
  const i = model.indexOf('/');
  return i === -1 ? model : model.slice(0, i);
}

/**
 * The brand mark for an ENGINE id (`provider/model`), or the generic Cpu glyph.
 * The chat-surface counterpart of `providerBrandIcon`.
 */
export function engineBrandIcon(model: string | null | undefined): ReactNode {
  return ENGINE_PROVIDER_MARKS[engineProvider(model)] ?? GenericProviderIcon;
}

/** True when the engine's provider has a distinct mark (not the fallback). */
export function hasEngineBrand(model: string | null | undefined): boolean {
  return engineProvider(model) in ENGINE_PROVIDER_MARKS;
}
