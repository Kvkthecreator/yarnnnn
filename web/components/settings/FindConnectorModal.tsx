'use client';

/**
 * FindConnectorModal — the whole "add a connector" act, in one place (ADR-635).
 *
 * WHY A MODAL, having argued against one. The first proposal was a modal that
 * PRESENTED AN ERROR, and that was the wrong instrument: it would have made a
 * better-looking dead end out of failures that were mostly ours to fix (see the
 * 2026-09-04 amendment in docs/evaluations/sessions/adr635-directory-
 * attachability-survey). Those are fixed — no-DCR servers now attempt the flow,
 * and the three no-member-can-resolve servers are opted out of the directory.
 *
 * What is left is not an error to explain but a FLOW to carry: search a
 * 52-server directory, pick one, and then a second step that VARIES BY SERVER
 * (nothing to do · sign in at the provider · an API key · a client id the
 * member registered themselves). That is more than a row in a settings list can
 * hold, and it is the shape Claude and ChatGPT already teach members to expect.
 *
 * The steps are the member's, not ours:
 *
 *   browse ──▶ [pick] ──▶ confirm ──▶ (needs a key/id? collect it) ──▶ attach
 *                                        │
 *                                        └─▶ redirect to the provider, or land
 *                                            on the connection's aperture page
 *
 * The aperture stays where it is — on the connection's own page — because it is
 * a standing decision the member revisits, not a step in adding something. This
 * modal ends the moment a credential exists.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Loader2, Search, ArrowLeft, X } from 'lucide-react';
import { api, type DirectoryEntry } from '@/lib/api/client';
import { Z_CONFIRM_BACKDROP, Z_CONFIRM_DIALOG } from '@/lib/shell/z-tiers';

interface FindConnectorModalProps {
  open: boolean;
  onClose: () => void;
  /** Server URLs already attached — their rows read "Attached", never "Connect". */
  attachedUrls: Set<string>;
  /** Where the provider sends the member back to. */
  redirectTo: string;
  /** An attach that completed without a redirect (anonymous / header / key). */
  onAttached: (slug: string) => void;
}

type Step = 'browse' | 'confirm';

/** A pasted URL is the same act as a directory pick, minus the search. */
const pastedEntry = (url: string): DirectoryEntry => ({
  name: url,
  key: null,
  title: url.replace(/^https?:\/\//, '').replace(/\/+$/, ''),
  description: '',
  url,
  category: null,
  source: 'registry',
  plugins: [],
});

export function FindConnectorModal({
  open,
  onClose,
  attachedUrls,
  redirectTo,
  onAttached,
}: FindConnectorModalProps) {
  const [step, setStep] = useState<Step>('browse');
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<DirectoryEntry[]>([]);
  const [loading, setLoading] = useState(false);
  /** A failure of the SEARCH — never of one server's attach (see `pickError`). */
  const [listError, setListError] = useState<string | null>(null);

  const [picked, setPicked] = useState<DirectoryEntry | null>(null);
  /** A failure of the PICKED server's attach. Rendered on its own step, where
   *  the member can see which server it belongs to — the defect this replaces
   *  put one shared error above the list, referring to nothing. */
  const [pickError, setPickError] = useState<string | null>(null);
  const [attaching, setAttaching] = useState(false);

  // Only shown when the member opens "Advanced" — the common case is empty.
  const [advanced, setAdvanced] = useState(false);
  const [headerName, setHeaderName] = useState('');
  const [headerValue, setHeaderValue] = useState('');
  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');
  const [pasteUrl, setPasteUrl] = useState('');

  const searchRef = useRef<HTMLInputElement>(null);

  const reset = useCallback(() => {
    setStep('browse');
    setQuery('');
    setPicked(null);
    setPickError(null);
    setListError(null);
    setAdvanced(false);
    setHeaderName('');
    setHeaderValue('');
    setClientId('');
    setClientSecret('');
    setPasteUrl('');
  }, []);

  useEffect(() => {
    if (open) {
      reset();
      requestAnimationFrame(() => searchRef.current?.focus());
    }
  }, [open, reset]);

  // Escape closes — but from the confirm step it goes BACK first, so a member
  // one keystroke from attaching does not lose the modal by reflex.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return;
      e.stopPropagation();
      if (step === 'confirm') {
        setStep('browse');
        setPickError(null);
      } else {
        onClose();
      }
    };
    window.addEventListener('keydown', onKey, true);
    return () => window.removeEventListener('keydown', onKey, true);
  }, [open, step, onClose]);

  useEffect(() => {
    if (!open || step !== 'browse') return;
    let cancelled = false;
    const handle = setTimeout(async () => {
      setLoading(true);
      setListError(null);
      try {
        const res = await api.connectors.directory(query.trim(), 24);
        if (!cancelled) setResults(res.results);
      } catch (e) {
        if (!cancelled) {
          setListError(e instanceof Error ? e.message : 'Could not search the directory.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(handle);
    };
  }, [query, open, step]);

  const pick = (entry: DirectoryEntry) => {
    setPicked(entry);
    setPickError(null);
    setAdvanced(false);
    setStep('confirm');
  };

  const attach = async () => {
    if (!picked) return;
    setAttaching(true);
    setPickError(null);
    try {
      const res = await api.connectors.attach({
        url: picked.url,
        key: picked.key ?? null,
        title: picked.title ?? null,
        category: picked.category ?? null,
        header_name: headerName.trim() || null,
        header_value: headerValue.trim() || null,
        client_id: clientId.trim() || null,
        client_secret: clientSecret.trim() || null,
        redirect_to: redirectTo,
      });
      if (res.authorization_url) {
        window.location.href = res.authorization_url;
        return;
      }
      onAttached(res.slug);
      onClose();
    } catch (e) {
      setPickError(e instanceof Error ? e.message : 'Could not attach that server.');
    } finally {
      setAttaching(false);
    }
  };

  if (!open) return null;

  const pasted = pasteUrl.trim();
  const pasteValid = pasted.startsWith('https://');

  return createPortal(
    <>
      <div
        className="fixed inset-0 bg-black/50 animate-in fade-in duration-150"
        style={{ zIndex: Z_CONFIRM_BACKDROP }}
        onClick={onClose}
      />
      <div
        className="pointer-events-none fixed inset-0 flex items-start justify-center p-4 pt-[8vh]"
        style={{ zIndex: Z_CONFIRM_DIALOG }}
      >
        <div
          className="pointer-events-auto flex max-h-[80vh] w-full max-w-lg flex-col overflow-hidden rounded-lg border border-border bg-card shadow-xl animate-in fade-in zoom-in-95 duration-150"
          role="dialog"
          aria-modal="true"
          aria-label="Find a connector"
        >
          {/* ── header ─────────────────────────────────────────────────── */}
          <div className="flex items-center gap-2 border-b border-border px-4 py-3">
            {step === 'confirm' && (
              <button
                type="button"
                onClick={() => {
                  setStep('browse');
                  setPickError(null);
                }}
                className="rounded-md p-1 text-muted-foreground hover:bg-muted"
                aria-label="Back to search"
              >
                <ArrowLeft className="h-4 w-4" />
              </button>
            )}
            <h2 className="flex-1 text-sm font-semibold text-card-foreground">
              {step === 'browse' ? 'Find a connector' : (picked?.title ?? 'Connect')}
            </h2>
            <button
              type="button"
              onClick={onClose}
              className="rounded-md p-1 text-muted-foreground hover:bg-muted"
              aria-label="Close"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {step === 'browse' ? (
            <>
              <div className="space-y-3 border-b border-border px-4 py-3">
                <p className="text-xs text-muted-foreground">
                  Any MCP server — the ones Claude&apos;s own plugins use, or anything in
                  the public registry. You sign in to the server yourself; nothing is
                  offered to a conversation until you choose which of its tools may run.
                </p>
                <div className="relative">
                  <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <input
                    ref={searchRef}
                    type="search"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Search — e.g. linear, hubspot, snowflake, docs"
                    className="w-full rounded-md border border-border bg-background py-2 pl-8 pr-3 text-sm"
                  />
                </div>
                {listError && (
                  <p role="alert" className="text-xs text-destructive">
                    {listError}
                  </p>
                )}
              </div>

              <div className="min-h-0 flex-1 space-y-1 overflow-y-auto px-4 py-3">
                {loading && results.length === 0 ? (
                  <div className="flex items-center gap-2 py-2 text-xs text-muted-foreground">
                    <Loader2 className="h-3 w-3 animate-spin" /> Searching…
                  </div>
                ) : (
                  results.map((entry) => {
                    const already = attachedUrls.has(entry.url);
                    return (
                      <button
                        key={entry.url}
                        type="button"
                        disabled={already}
                        onClick={() => pick(entry)}
                        className="flex w-full items-center gap-3 rounded-md border border-border/60 px-3 py-2 text-left hover:bg-muted disabled:cursor-default disabled:opacity-50 disabled:hover:bg-transparent"
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium">{entry.title}</span>
                            {entry.category && (
                              <span className="text-[11px] text-muted-foreground">
                                {entry.category}
                              </span>
                            )}
                            <span
                              className="text-[10px] uppercase tracking-wider text-muted-foreground"
                              title={
                                entry.source === 'official-plugins'
                                  ? "An endpoint Anthropic's knowledge-work plugins name"
                                  : 'Listed in the public MCP registry'
                              }
                            >
                              {entry.source === 'official-plugins' ? 'official' : 'registry'}
                            </span>
                          </div>
                          <div className="truncate text-xs text-muted-foreground">
                            {entry.description || entry.url.replace(/^https?:\/\//, '')}
                          </div>
                        </div>
                        <span className="shrink-0 text-xs text-muted-foreground">
                          {already ? 'Attached' : 'Connect'}
                        </span>
                      </button>
                    );
                  })
                )}
                {!loading && query.trim() && results.length === 0 && (
                  <p className="py-2 text-xs text-muted-foreground">
                    Nothing matched. Paste the server&apos;s URL below.
                  </p>
                )}
              </div>

              <div className="border-t border-border px-4 py-3">
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (pasteValid) pick(pastedEntry(pasted));
                  }}
                  className="flex gap-2"
                >
                  <input
                    type="url"
                    value={pasteUrl}
                    onChange={(e) => setPasteUrl(e.target.value)}
                    placeholder="…or paste a server URL (https://…)"
                    className="min-w-0 flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm"
                  />
                  <button
                    type="submit"
                    disabled={!pasteValid}
                    className="shrink-0 rounded-md border border-border px-3 py-1.5 text-xs hover:bg-muted disabled:opacity-50"
                  >
                    Connect
                  </button>
                </form>
              </div>
            </>
          ) : (
            /* ── confirm ─────────────────────────────────────────────────
               One screen naming the server, what attaching does, and what it
               does NOT do. The aperture is named here as the NEXT step so the
               member knows nothing is offered yet — the promise the browse
               copy makes has to be kept where the credential is actually
               created. */
            <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
              <div className="rounded-md border border-border/60 px-3 py-2">
                <div className="text-sm font-medium">{picked?.title}</div>
                <div className="truncate text-xs text-muted-foreground">
                  {picked?.url.replace(/^https?:\/\//, '')}
                </div>
              </div>

              <p className="mt-3 text-xs text-muted-foreground">
                You&apos;ll sign in at {picked?.title} if it asks. yarnnn stores the
                credential in your account and nothing else — no tool is offered to a
                conversation until you choose, tool by tool, on the next screen.
              </p>

              {pickError && (
                <p role="alert" className="mt-3 rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">
                  {pickError}
                </p>
              )}

              {/* Kept behind a disclosure: the overwhelming majority of servers
                  need neither, and a form of empty boxes reads as a demand. */}
              <button
                type="button"
                onClick={() => setAdvanced((v) => !v)}
                className="mt-4 text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground"
              >
                {advanced ? 'Hide' : 'This server needs an API key or my own app credentials'}
              </button>

              {advanced && (
                <div className="mt-3 space-y-3">
                  <div className="space-y-1">
                    <label className="text-[11px] font-medium text-muted-foreground">
                      API key header (for servers that authenticate with a key)
                    </label>
                    <div className="flex gap-2">
                      <input
                        value={headerName}
                        onChange={(e) => setHeaderName(e.target.value)}
                        placeholder="Authorization"
                        className="min-w-0 flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm"
                      />
                      <input
                        value={headerValue}
                        onChange={(e) => setHeaderValue(e.target.value)}
                        placeholder="Bearer …"
                        type="password"
                        className="min-w-0 flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm"
                      />
                    </div>
                  </div>
                  <div className="space-y-1">
                    <label className="text-[11px] font-medium text-muted-foreground">
                      OAuth client (only if you registered yarnnn as an app there)
                    </label>
                    <div className="flex gap-2">
                      <input
                        value={clientId}
                        onChange={(e) => setClientId(e.target.value)}
                        placeholder="Client ID"
                        className="min-w-0 flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm"
                      />
                      <input
                        value={clientSecret}
                        onChange={(e) => setClientSecret(e.target.value)}
                        placeholder="Client secret (optional)"
                        type="password"
                        className="min-w-0 flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm"
                      />
                    </div>
                    <p className="text-[11px] text-muted-foreground">
                      Most servers need none of this — yarnnn registers itself
                      automatically, and asks the server directly when it can&apos;t.
                    </p>
                  </div>
                </div>
              )}

              <div className="mt-5 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setStep('browse');
                    setPickError(null);
                  }}
                  className="rounded-md px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted"
                >
                  Back
                </button>
                <button
                  type="button"
                  onClick={() => void attach()}
                  disabled={attaching}
                  className="inline-flex items-center gap-2 rounded-md border border-border bg-foreground px-3 py-1.5 text-xs text-background hover:opacity-90 disabled:opacity-50"
                >
                  {attaching && <Loader2 className="h-3 w-3 animate-spin" />}
                  Continue
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </>,
    document.body,
  );
}
