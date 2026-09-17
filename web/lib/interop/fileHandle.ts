/**
 * fileHandle — the ADR-512 D5 handle grammar, browser side (ADR-587).
 *
 * `yarnnn://workspace/{workspace-relative-path}` is the canonical
 * cross-boundary name for a file. This module is the TypeScript twin of
 * `api/services/mcp_composition.py::parse_file_reference` /
 * `format_file_reference` — the SAME three spellings, the same refusals.
 *
 * Why a twin and not a fetch: a name is not a lookup. Resolving
 * `yarnnn://workspace/x.md` to `/workspace/x.md` is pure string grammar with
 * no workspace state in it, and the surfaces that need it (the Files arrival
 * door, quick-open) need it BEFORE any request is in flight. Round-tripping
 * to the server to learn how to spell a path would make every deep-link wait
 * on the network to discover it was well-formed.
 *
 * The asymmetry this closes (ADR-587 §1): before this file, `yarnnn://`
 * appeared in `web/` exactly twice, both EMITTING it. The app handed out a
 * name in a grammar it could not itself read back — the interop loop broken
 * on its return leg. Any surface that accepts a file name from outside
 * (paste, deep-link, drop) parses it HERE, so the accepted grammar cannot
 * drift per surface.
 *
 * Keep in lockstep with the Python. If the grammar gains a spelling (the
 * reserved `@{revision_id}` form, say), both halves move in one commit —
 * `api/test_adr587_handle_grammar_parity.py` asserts the pair agree.
 */

/** The canonical scheme prefix (ADR-512 D5). Lowercase; matching is case-insensitive. */
export const YARNNN_REF_SCHEME = 'yarnnn://workspace/';

/** The ledger's absolute root. Every stored path begins with this. */
export const WORKSPACE_PREFIX = '/workspace/';

/**
 * Normalize any honest spelling of a file's name to a workspace-relative path.
 *
 * Accepts (ADR-512 D5):
 *   · `yarnnn://workspace/marketing/gtm.md`  — the canonical handle
 *   · `/workspace/marketing/gtm.md`          — the ledger's absolute form
 *   · `marketing/gtm.md`                     — bare workspace-relative
 *
 * Returns the workspace-relative path (no leading slash), or `null` when the
 * reference is empty, carries another scheme, or escapes the workspace (`..`).
 *
 * A `null` return is a REFUSAL, not an error to swallow: the caller shows the
 * operator that the thing they pasted is not a file name, rather than
 * searching for it and reporting a confident miss.
 */
export function parseFileReference(reference: string | null | undefined): string | null {
  let ref = (reference ?? '').trim().replace(/^["']|["']$/g, '');
  if (!ref) return null;

  const lowered = ref.toLowerCase();
  if (lowered.startsWith(YARNNN_REF_SCHEME)) {
    ref = ref.slice(YARNNN_REF_SCHEME.length);
  } else if (ref.includes('://')) {
    // Some other scheme — an http(s) link, a file:// path. Not a yarnnn name.
    return null;
  } else if (ref.startsWith(WORKSPACE_PREFIX)) {
    ref = ref.slice(WORKSPACE_PREFIX.length);
  }

  ref = ref.replace(/^\/+/, '').trim();
  if (!ref) return null;
  // Refuse traversal: a name that climbs out of the workspace is not a name in it.
  if (ref.split('/').includes('..')) return null;
  return ref;
}

/**
 * The absolute ledger path for any honest spelling — what `workspace_files.path`
 * actually stores, and therefore what every read path wants.
 *
 * Returns `null` on the same refusals as `parseFileReference`.
 */
export function toWorkspacePath(reference: string | null | undefined): string | null {
  const rel = parseFileReference(reference);
  // ADR-588 D2, the RETURN LEG. The surface now DISPLAYS and COPIES the
  // told-name (`Downloads/uploads/a.png`), so the told-name is a spelling that
  // arrives here — from the address bar, a pasted link, a shared handle. Before
  // this call, `openPath` matched `workspace_files.path` verbatim and a
  // told-name resolved to `/workspace/Downloads/…`, which matches nothing: the
  // app would have emitted a name it could not read back, the exact ADR-587 §1
  // asymmetry this module exists to close. The Python doors resolve the same
  // told-names via `resolve_told_workspace_path`; this is that resolution for
  // every door that takes a path from a browser.
  return rel === null ? null : `${WORKSPACE_PREFIX}${resolveHomeAlias(rel)}`;
}

/**
 * The workspace-relative path — the form the operator reads and pastes back.
 *
 * Unlike `parseFileReference` this never refuses: it is for DISPLAYING a path
 * the workspace already gave us, where a refusal would blank the UI. Callers
 * holding untrusted input want `parseFileReference`.
 */
export function relPath(path: string): string {
  return path.startsWith(WORKSPACE_PREFIX) ? path.slice(WORKSPACE_PREFIX.length) : path;
}

/**
 * The canonical handle for a workspace path (ADR-512 D5) — the emit half.
 *
 * Mirrors `format_file_reference`: normalize if we can, else fall back to the
 * de-slashed input, so a display path always yields SOMETHING nameable.
 */
export function formatFileReference(path: string): string {
  const rel = parseFileReference(path) ?? (path || '').replace(/^\/+/, '');
  return `${YARNNN_REF_SCHEME}${rel}`;
}

/**
 * The handle wrapped in host guidance — what goes on the clipboard when the
 * destination is another AI's chat box.
 *
 * The handle is kernel grammar; this sentence is host guidance, and the two
 * are deliberately separable (ADR-512 D5). Built ONCE here because it shipped
 * hand-written in two apps that had already drifted apart: Studio said
 * "`trace` shows who changed it", Text said "`history` shows who changed it"
 * — and `history` is the verb that exists (ADR-543/545). A duplicated
 * sentence is a sentence that goes stale in one copy.
 */
export function formatAiReference(path: string, name: string): string {
  return (
    `"${name}" — ${formatFileReference(path)} ` +
    '(with the yarnnn connector, `open` this reference to read the exact ' +
    'current version; `history` shows who changed it and when).'
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// HOME ALIASES — the told-name is what the operator reads (ADR-588 D2)
// ─────────────────────────────────────────────────────────────────────────────
//
// The TypeScript twin of `HOME_ALIASES` / `display_home_alias` /
// `resolve_home_alias` in `api/services/workspace_paths.py`. Same two homes,
// same first-segment-only scope, same case-insensitive match.
//
// ⭐ WHY THE BROWSER NEEDS ITS OWN COPY. The Python display half had exactly
// ONE caller (an MCP refusal sentence) when this shipped, so every path string
// the WEB surface rendered spoke kernel vocabulary while the tree beside it
// spoke the told-name. The operator stood in a folder the sidebar called
// "Downloads", read `inbound/uploads` under its title, and `inbound/uploads/
// gate-427.png` under every tile — one folder, two names, on one screen
// (operator-observed, 2026-09-17). The tree label was aliased at
// `buildRootNodes`; nothing else was.
//
// Like the Python, this is pure string grammar with no workspace state in it,
// so it stays a twin rather than a fetch.
//
// Keep in lockstep with the Python. `api/test_adr588_interop_vocabulary.py`
// asserts the pair agree — a home added there without an edit here fails the
// gate rather than silently re-opening the split.

/** Told-name (what the operator is taught) → kernel root (what is stored). */
export const HOME_ALIASES: Readonly<Record<string, string>> = {
  Documents: 'operation',
  Downloads: 'inbound',
};

/** The INVERSE, derived — never a second hand-kept map. Two hand-kept
 *  directions are how the vocabularies diverged in the first place. */
const HOME_ALIAS_DISPLAY: Readonly<Record<string, string>> = Object.fromEntries(
  Object.entries(HOME_ALIASES).map(([told, kernel]) => [kernel, told]),
);

const HOME_ALIAS_LOOKUP: Readonly<Record<string, string>> = Object.fromEntries(
  Object.entries(HOME_ALIASES).map(([told, kernel]) => [told.toLowerCase(), kernel]),
);

/**
 * Resolve a told-name home in the FIRST segment to its kernel path — the twin
 * of `resolve_home_alias`. `Downloads/x` → `inbound/x`; case-insensitive.
 *
 * SCOPE IS THE FIRST SEGMENT ONLY. A nested `operation/Documents/notes.md` is
 * an ordinary folder someone named, exactly as ~/Projects/Documents is on any
 * real machine — aliasing it would be the same silent misroute this closes.
 *
 * Takes and returns a WORKSPACE-RELATIVE path (no leading slash).
 */
export function resolveHomeAlias(relativePath: string): string {
  const rel = relativePath || '';
  if (!rel || rel.startsWith('/')) return rel;
  const slash = rel.indexOf('/');
  const head = slash === -1 ? rel : rel.slice(0, slash);
  const tail = slash === -1 ? '' : rel.slice(slash);
  const kernel = HOME_ALIAS_LOOKUP[head.toLowerCase()];
  return kernel === undefined ? rel : `${kernel}${tail}`;
}

/**
 * The told-name spelling of a kernel path — the DISPLAY half, twin of
 * `display_home_alias`. `inbound/uploads/a.png` → `Downloads/uploads/a.png`.
 * Any other path is returned byte-identical.
 *
 * ⚠️ PROSE ONLY — never a `yarnnn://` handle. A handle is an ADDRESS that must
 * round-trip through other systems and back into `parse_file_reference`, so
 * `formatFileReference` deliberately does NOT call this. The ADR-395/588 rule
 * holds for storage and authorization: alias at PRESENTATION only.
 *
 * Takes and returns a WORKSPACE-RELATIVE path (no leading slash).
 */
export function displayHomeAlias(relativePath: string): string {
  const rel = relativePath || '';
  if (!rel || rel.startsWith('/')) return rel;
  const slash = rel.indexOf('/');
  const head = slash === -1 ? rel : rel.slice(0, slash);
  const tail = slash === -1 ? '' : rel.slice(slash);
  const told = HOME_ALIAS_DISPLAY[head];
  return told === undefined ? rel : `${told}${tail}`;
}

/**
 * THE ONE PATH STRING A HUMAN READS. `/workspace/inbound/uploads/a.png` →
 * `Downloads/uploads/a.png`.
 *
 * `relPath` strips the ledger prefix and stops; this also speaks the home in
 * the vocabulary the operator was taught. Every surface that renders a path
 * for a person — a title strip, a tile caption, a list subtitle, a Properties
 * row, a share target — calls THIS. `relPath` remains for the callers that
 * need the kernel spelling (a request parameter, a comparison against
 * `workspace_files.path`, a handle).
 */
export function displayPath(path: string): string {
  return displayHomeAlias(relPath(path));
}
