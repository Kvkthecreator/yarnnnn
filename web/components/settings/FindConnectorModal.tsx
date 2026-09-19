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
 *
 * TWO LANES, VISIBLY TWO (ADR-657). The browse step now shows the CURATED lane
 * first — a short authored list whose admission criterion is ADR-420 §10's
 * moat-leak test, each entry carrying its real name, its URL shape, its
 * credential step and its category. Below it, the consumed directory, unchanged.
 * At the foot, the OPEN lane — paste a URL — kept (ADR-635 am.2's media path
 * depends on it) but demoted and differentiated: it now SAYS that yarnnn has not
 * examined the server and cannot say where the member's work will accumulate.
 * That sentence is the whole reason the open lane is not silent any more.
 *
 * Both lanes converge: one POST /connectors/attach, one `mcp:{slug}` row, one
 * per-tool aperture. Curation is a discovery act, never an authority one.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Loader2, Search, ArrowLeft, X, ExternalLink, ShieldQuestion } from 'lucide-react';
import { Working } from '@/components/shared/Working';
import { api, APIError, type CuratedEntry, type DirectoryEntry } from '@/lib/api/client';
import { useFeedback } from '@/contexts/FeedbackContext';
import { Z_CONFIRM_BACKDROP, Z_CONFIRM_DIALOG } from '@/lib/shell/z-tiers';
import { ConnectorAvatar } from '@/components/connectors/ConnectorAvatar';

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

type Step = 'browse' | 'confirm' | 'curated';

/** ADR-657 D4 — the sentence the open lane owes the member before an attach.
 *  It is the one thing the paste box could never say, and its absence is what
 *  made the box "way too generic": the same keystroke served a dumb peripheral
 *  and a competing commons, with nothing between them. */
const OPEN_LANE_CAVEAT =
  'yarnnn has not examined this server. We cannot tell you what it does with what you send it, or whether your work will accumulate on its side instead of here.';

/** The address a curated entry will eventually have, with the member's hole
 *  removed so it parses. A curated entry carries a `url_shape`
 *  (`https://{store}.myshopify.com/api/mcp`) rather than a URL, because the
 *  member supplies one segment on the next step — but the BRAND is in the part
 *  that is already there, which is all the mark needs. Falls back to the
 *  entry's own key when there is no shape at all. */
const curatedUrlHint = (entry: CuratedEntry): string =>
  entry.url ?? (entry.url_shape ?? '').replace(/\{[^}]*\}\.?/g, '');

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
  // ADR-635 D7 — the CATEGORY is what scopes a skill to this connector
  // (`metadata.needs`). The directory supplies one for a seeded server; a
  // pasted server has none, and without it a needs-scoped skill can never
  // be offered for it. So the member names it, with the seed's own
  // vocabulary as suggestions (never a closed list).
  const [category, setCategory] = useState('');
  const [categoryOptions, setCategoryOptions] = useState<string[]>([]);
  const [headerName, setHeaderName] = useState('');
  const [headerValue, setHeaderValue] = useState('');
  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');
  const [pasteUrl, setPasteUrl] = useState('');

  // ADR-657 — the curated lane. Separate state from `results` on purpose: it is
  // a different source with a different shape and a different act, and merging
  // them into one list is exactly the undifferentiation this ADR removes.
  const [curated, setCurated] = useState<CuratedEntry[]>([]);
  const [pickedCurated, setPickedCurated] = useState<CuratedEntry | null>(null);
  /** The one field a shaped URL leaves to the member (e.g. the store name). */
  const [shapeValue, setShapeValue] = useState('');

  const searchRef = useRef<HTMLInputElement>(null);
  const { runAction } = useFeedback();

  const reset = useCallback(() => {
    setStep('browse');
    setQuery('');
    setPicked(null);
    setPickError(null);
    setListError(null);
    setAdvanced(false);
    setCategory('');
    setHeaderName('');
    setHeaderValue('');
    setClientId('');
    setClientSecret('');
    setPasteUrl('');
    setPickedCurated(null);
    setShapeValue('');
  }, []);

  useEffect(() => {
    if (open) {
      reset();
      requestAnimationFrame(() => searchRef.current?.focus());
    }
  }, [open, reset]);

  // The seed's category vocabulary — SUGGESTIONS for the field below, never a
  // closed list (`connector_directory.categories()` says so). Best-effort: the
  // field is free text, so a failed fetch costs the member nothing.
  useEffect(() => {
    if (!open) return;
    let alive = true;
    api.connectors
      .categories()
      .then((r) => {
        if (alive) setCategoryOptions(r.categories ?? []);
      })
      .catch(() => {
        /* suggestions are a convenience; the field still works */
      });
    // ADR-657 — the curated lane is small and unsearched: one fetch, rendered
    // whole above the directory. A failure costs the member the lane, never the
    // modal, so the directory and the open lane still answer.
    api.connectors
      .curated()
      .then((r) => {
        if (alive) setCurated(r.results ?? []);
      })
      .catch(() => {
        /* the other two lanes still work */
      });
    return () => {
      alive = false;
    };
  }, [open]);

  // Escape closes — but from the confirm step it goes BACK first, so a member
  // one keystroke from attaching does not lose the modal by reflex.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return;
      e.stopPropagation();
      if (step === 'confirm' || step === 'curated') {
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

  const pickCurated = (entry: CuratedEntry) => {
    setPickedCurated(entry);
    setPickError(null);
    setShapeValue('');
    setHeaderName(entry.header_name ?? '');
    setHeaderValue('');
    setStep('curated');
  };

  /** ADR-657 — the curated attach. It names the ENTRY and the one field the
   *  member filled; the server resolves the URL, the title, the slug and the
   *  category. From `begin_attach` on it is the same act as a pasted URL. */
  const attachCurated = async () => {
    const entry = pickedCurated;
    if (!entry) return;
    setAttaching(true);
    setPickError(null);
    try {
      const res = await runAction(
        () =>
          api.connectors.attach({
            curated_key: entry.key,
            shape_value: shapeValue.trim() || null,
            header_name: headerName.trim() || null,
            header_value: headerValue.trim() || null,
            redirect_to: redirectTo,
          }),
        {
          pending: `Connecting to ${entry.title}…`,
          success: (r) => (r.authorization_url ? '' : `Connected to ${entry.title}`),
          error: (e) =>
            e instanceof APIError
              ? (e.data as { detail?: string })?.detail || `Couldn't connect to ${entry.title}`
              : `Couldn't connect to ${entry.title}`,
        },
      );
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

  const attach = async () => {
    if (!picked) return;
    setAttaching(true);
    setPickError(null);
    try {
      // The toast is the outcome notice (docs/design/ACTION-FEEDBACK.md); the
      // in-surface `pickError` below stays because a failure has to remain
      // legible ON the server's own step, beside the fields the member may
      // need to correct — a toast evaporates and the modal is still open.
      const res = await runAction(
        () =>
          api.connectors.attach({
            url: picked.url,
            key: picked.key ?? null,
            title: picked.title ?? null,
            category: picked.category ?? (category.trim() || null),
            header_name: headerName.trim() || null,
            header_value: headerValue.trim() || null,
            client_id: clientId.trim() || null,
            client_secret: clientSecret.trim() || null,
            redirect_to: redirectTo,
          }),
        {
          pending: `Connecting to ${picked.title ?? 'the server'}\u2026`,
          // A redirect leaves the page, so the arrival is the receipt there;
          // the quiet success line is for the attach that finishes here.
          success: (r) => (r.authorization_url ? '' : `Connected to ${picked.title ?? 'the server'}`),
          error: (e) =>
            e instanceof APIError
              ? (e.data as { detail?: string })?.detail || "Couldn't connect to that server"
              : "Couldn't connect to that server",
        },
      );
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
            {step !== 'browse' && (
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
            {/* The picked connector keeps its face across the step change, so
                the member can see that the row they clicked is the one they
                are now being asked to trust. */}
            {step === 'curated' && pickedCurated ? (
              <ConnectorAvatar
                size="sm"
                url={curatedUrlHint(pickedCurated)}
                title={pickedCurated.title}
                connectorKey={pickedCurated.key}
              />
            ) : step === 'confirm' && picked ? (
              <ConnectorAvatar size="sm" url={picked.url} title={picked.title} connectorKey={picked.key} />
            ) : null}
            <h2 className="flex-1 text-sm font-semibold text-card-foreground">
              {step === 'browse'
                ? 'Find a connector'
                : step === 'curated'
                  ? (pickedCurated?.title ?? 'Connect')
                  : (picked?.title ?? 'Connect')}
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
                  A few yarnnn has set up, the public directory, or any server you know.
                  You sign in to it yourself, and nothing is used in a chat until you
                  choose which of its tools may run.
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
                {/* ── the curated lane (ADR-657 D1) ───────────────────────────
                    First, because these are the connections yarnnn has
                    deliberately made work: a real name, a setup step, a
                    pre-filled category, and a recorded verdict on where the
                    member's work accumulates. Not a ranking and not a store —
                    the list is one entry long by construction (D3). */}
                {curated.length > 0 && !query.trim() && (
                  <div className="mb-3 space-y-1">
                    <p className="px-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                      Set up by yarnnn
                    </p>
                    {curated.map((entry) => (
                      <button
                        key={entry.key}
                        type="button"
                        onClick={() => pickCurated(entry)}
                        className="flex w-full items-center gap-3 rounded-md border border-border px-3 py-2 text-left hover:bg-muted"
                      >
                        {/* A curated entry has no URL yet — its address is a
                            SHAPE with a hole the member fills on the next step.
                            The brand is in the domain part, which is already
                            there, so the identity resolves off the shape with
                            the hole removed. */}
                        <ConnectorAvatar
                          size="sm"
                          url={curatedUrlHint(entry)}
                          title={entry.title}
                          connectorKey={entry.key}
                        />
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium">{entry.title}</span>
                            <span className="text-[11px] text-muted-foreground">
                              {entry.category}
                            </span>
                          </div>
                          <div className="truncate text-xs text-muted-foreground">
                            {entry.description}
                          </div>
                        </div>
                        <span className="shrink-0 text-xs text-muted-foreground">Set up</span>
                      </button>
                    ))}
                    <p className="px-1 pt-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                      From the public directory
                    </p>
                  </div>
                )}
                {loading && results.length === 0 ? (
                  <Working label="Searching…" className="py-2 text-xs" />
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
                        <ConnectorAvatar
                          size="sm"
                          url={entry.url}
                          title={entry.title}
                          connectorKey={entry.key}
                        />
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

              {/* ── the open lane (ADR-657 D4) ─────────────────────────────
                  It stays: ADR-635 am.2 rents media generation through a
                  member's own attach of a vendor the seed does not carry, and
                  deleting this box makes that unreachable. It is demoted (last,
                  quiet) and DIFFERENTIATED — it names itself as attaching a
                  server yarnnn has not examined, which is the sentence ADR-420
                  §10 requires of the act and the box has never said. */}
              <div className="space-y-2 border-t border-border bg-muted/20 px-4 py-3">
                <div className="flex items-start gap-2">
                  <ShieldQuestion className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  <div className="space-y-0.5">
                    <p className="text-xs font-medium text-foreground/80">
                      Or attach any other server
                    </p>
                    <p className="text-[11px] leading-relaxed text-muted-foreground">
                      {OPEN_LANE_CAVEAT} You still choose, tool by tool, what may run.
                    </p>
                  </div>
                </div>
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
                    placeholder="https://…"
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
          ) : step === 'curated' && pickedCurated ? (
            /* ── curated set-up (ADR-657 D2) ─────────────────────────────
               The step that exists because a URL cannot carry any of this: the
               shape with one hole for the member to fill, the credential step
               in the vendor's own words, and the bounded endorsement — what the
               connection IS with, who holds the token, and where the member
               decides what runs. The verdict and its reason are shown as data,
               not as a claim that the far side is safe. */
            <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
              <p className="text-xs leading-relaxed text-muted-foreground">
                {pickedCurated.rationale}
              </p>

              {pickedCurated.url_shape && pickedCurated.shape_field && (
                <div className="mt-4 space-y-1">
                  <label
                    htmlFor="curated-shape"
                    className="text-[11px] font-medium text-muted-foreground"
                  >
                    {pickedCurated.shape_label ?? pickedCurated.shape_field}
                  </label>
                  <input
                    id="curated-shape"
                    value={shapeValue}
                    onChange={(e) => setShapeValue(e.target.value)}
                    placeholder={pickedCurated.shape_placeholder ?? ''}
                    className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                  />
                  {pickedCurated.shape_help && (
                    <p className="text-[11px] text-muted-foreground">
                      {pickedCurated.shape_help}
                    </p>
                  )}
                  <p className="truncate text-[11px] text-muted-foreground/80">
                    {pickedCurated.url_shape.replace(
                      `{${pickedCurated.shape_field}}`,
                      shapeValue.trim() || `{${pickedCurated.shape_field}}`,
                    )}
                  </p>
                </div>
              )}

              {pickedCurated.credential_steps.length > 0 && (
                <div className="mt-4 space-y-1">
                  <p className="text-[11px] font-medium text-muted-foreground">
                    Where the key comes from
                  </p>
                  <ol className="list-decimal space-y-1 pl-4 text-[11px] leading-relaxed text-muted-foreground">
                    {pickedCurated.credential_steps.map((s) => (
                      <li key={s}>{s}</li>
                    ))}
                  </ol>
                  {pickedCurated.credential_url && (
                    <a
                      href={pickedCurated.credential_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-[11px] text-primary hover:underline"
                    >
                      {pickedCurated.title}&apos;s own instructions
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                </div>
              )}

              {pickedCurated.header_name && (
                <div className="mt-4 space-y-1">
                  <label className="text-[11px] font-medium text-muted-foreground">
                    {pickedCurated.header_name}
                  </label>
                  <input
                    value={headerValue}
                    onChange={(e) => setHeaderValue(e.target.value)}
                    placeholder="Paste the token"
                    type="password"
                    className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                  />
                </div>
              )}

              {/* The honest cost, stated rather than slipped (ADR-657 §3.a/§8). */}
              {pickedCurated.credential_note && (
                <p className="mt-4 rounded-md border border-border/60 bg-muted/30 px-3 py-2 text-[11px] leading-relaxed text-muted-foreground">
                  {pickedCurated.credential_note}
                </p>
              )}

              {pickError && (
                <p
                  role="alert"
                  className="mt-3 rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive"
                >
                  {pickError}
                </p>
              )}

              <p className="mt-3 text-[11px] text-muted-foreground/70">
                Last checked by yarnnn on {pickedCurated.reviewed_at}.
              </p>

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
                  onClick={() => void attachCurated()}
                  disabled={attaching}
                  className="inline-flex items-center gap-2 rounded-md border border-border bg-foreground px-3 py-1.5 text-xs text-background hover:opacity-90 disabled:opacity-50"
                >
                  {attaching && <Loader2 className="h-3 w-3 animate-spin" />}
                  Continue
                </button>
              </div>
            </div>
          ) : (
            /* ── confirm ─────────────────────────────────────────────────
               One screen naming the server, what attaching does, and what it
               does NOT do. The aperture is named here as the NEXT step so the
               member knows nothing is offered yet — the promise the browse
               copy makes has to be kept where the credential is actually
               created. */
            <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
              {/* The header already carries the server's name on this step, so
                  the card states its ADDRESS — the thing the member is actually
                  being asked to trust — rather than repeating the title. */}
              <div className="rounded-md border border-border/60 px-3 py-2">
                <div className="truncate text-sm">
                  {picked?.url.replace(/^https?:\/\//, '')}
                </div>
                {picked?.category && (
                  <div className="text-xs text-muted-foreground">{picked.category}</div>
                )}
              </div>

              {/* A seeded server already carries its category; a pasted one does
                  not, and the category is what lets a needs-scoped skill be
                  offered for it (ADR-635 D7). Optional, so it never blocks an
                  attach — an unnamed connector simply scopes no skill. */}
              {!picked?.category && (
                <div className="mt-3 space-y-1">
                  <label
                    htmlFor="connector-category"
                    className="text-[11px] font-medium text-muted-foreground"
                  >
                    What kind of server is this? (optional — lets skills written
                    for this kind of work be offered in chat)
                  </label>
                  <input
                    id="connector-category"
                    list="connector-category-options"
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    placeholder="Media generation"
                    className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                  />
                  <datalist id="connector-category-options">
                    {categoryOptions.map((c) => (
                      <option key={c} value={c} />
                    ))}
                  </datalist>
                </div>
              )}

              <p className="mt-3 text-xs text-muted-foreground">
                You&apos;ll sign in at {picked?.title} if it asks. yarnnn keeps the
                sign-in under your account and nothing else. No tool is used in a chat
                until you choose, tool by tool, on the next screen.
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
