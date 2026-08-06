"use client";

/**
 * The interactive island of the public share page — ADR-529 D3.
 *
 * The READ path is server-rendered (`page.tsx`); this component owns only what
 * genuinely needs a browser: the accept action (auth-gated) and the walk's
 * expand/collapse. Nothing here fetches the artifact — a reader without
 * JavaScript has already received it in the HTML.
 */

import { useCallback, useState } from "react";
import { ChevronDown, Loader2 } from "lucide-react";

import { api, APIError, setActiveWorkspace } from "@/lib/api/client";
import type { WalkEntry } from "./share-preview";

/** Attribution stays verbatim — `system:radar`, `freddie:…`, an email. The
 *  substrate's own spelling is the honest one; we do not prettify an author. */
function walkActor(authored_by: string | null): string {
  return authored_by || "unknown";
}

function walkDate(when: string | null): string {
  if (!when) return "";
  try {
    return new Date(when).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } catch {
    return "";
  }
}

/** The distinct authors, in first-seen order — the collapsed line's payload. */
function actors(walk: WalkEntry[]): string[] {
  const seen: string[] = [];
  for (const w of walk) {
    const a = walkActor(w.authored_by);
    if (!seen.includes(a)) seen.push(a);
  }
  return seen;
}

/**
 * ADR-529 D5 — the walk COLLAPSED to one line, expandable.
 *
 * The walk stays (it is ADR-513's whole thesis — the moat demonstrated on
 * contact); what changes is weight. It rendered as a card of equal size to the
 * artifact, asking the reader to treat "who changed this" as co-equal with
 * "what this is". Proof on contact, in a glance — the ledger is one click away.
 */
export function AttributionWalk({ walk }: { walk: WalkEntry[] }) {
  const [open, setOpen] = useState(false);
  if (walk.length === 0) return null;

  const names = actors(walk);
  const shown = names.slice(0, 3).join(", ");
  const rest = names.length > 3 ? ` +${names.length - 3}` : "";
  const count = `${walk.length} ${walk.length === 1 ? "change" : "changes"}`;

  return (
    <div className="border-t border-border/60">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-xs text-muted-foreground transition-colors hover:bg-muted/30"
      >
        <span className="font-medium text-foreground/80">Every change, signed</span>
        <span className="truncate">
          {count} · {shown}
          {rest}
        </span>
        <ChevronDown
          className={`ml-auto h-3.5 w-3.5 shrink-0 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <ul className="space-y-1.5 border-t border-border/60 px-4 py-3">
          {walk.map((w, i) => (
            <li key={i} className="flex items-baseline gap-2 text-sm">
              <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
                {walkDate(w.when)}
              </span>
              <span className="truncate font-medium">{walkActor(w.authored_by)}</span>
              {w.change && (
                <span className="truncate text-xs text-muted-foreground">— {w.change}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/**
 * The join action — the one thing on this page that is NOT public.
 *
 * ADR-513 D1: reading is a capability the token carries; BECOMING A PRINCIPAL
 * is auth-gated and always was. A 401 bounces through login with `?next`
 * preserved, which is the ADR-465 D2 unified-door flow.
 */
export function JoinAction({
  token,
  role,
  status,
  workspaceName,
  hasArtifact,
}: {
  token: string;
  role: string;
  status: string;
  workspaceName: string;
  hasArtifact: boolean;
}) {
  const [accepting, setAccepting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const accept = useCallback(async () => {
    setAccepting(true);
    setError(null);
    try {
      const result = await api.workspace.acceptShare(token);
      // Bind the commons for every subsequent API call. Shell state is keyed
      // per (workspace, user) — ADR-407 Phase 3 — so the new binding reads
      // fresh keys by construction; no wipe needed on accept.
      setActiveWorkspace(result.workspace_id);
      window.location.assign(result.artifact_path ? "/files" : "/desktop");
    } catch (e) {
      if (e instanceof APIError && e.status === 401) {
        window.location.assign(`/auth/login?next=${encodeURIComponent(`/s/${token}`)}`);
        return;
      }
      const data = e instanceof APIError ? (e.data as { detail?: unknown } | undefined) : undefined;
      setError(typeof data?.detail === "string" ? data.detail : "Could not accept the share.");
      setAccepting(false);
    }
  }, [token]);

  if (status !== "active") {
    return (
      <p className="text-sm text-muted-foreground">This share link is {status}.</p>
    );
  }

  const viewer = role === "viewer";
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
      <button
        onClick={() => void accept()}
        disabled={accepting}
        className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-60"
      >
        {accepting && <Loader2 className="h-4 w-4 animate-spin" />}
        {viewer ? "View read-only" : hasArtifact ? "Open & join" : "Accept & join"}
      </button>
      <p className="text-xs text-muted-foreground">
        {viewer
          ? "You'll see this and its history — read-only."
          : `Join ${workspaceName} with full access — every change signed by whoever made it, human or not.`}
      </p>
      {error && <p className="w-full text-xs text-destructive">{error}</p>}
    </div>
  );
}
