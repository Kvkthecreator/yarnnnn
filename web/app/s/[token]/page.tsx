/**
 * The shared-artifact page — ADR-437 D4 (the /s/{token} surface), made PUBLIC
 * by ADR-513, and SERVER-RENDERED by ADR-529 D3.
 *
 * A stranger with the link sees the artifact + who made it — with NO account
 * (the token is the read capability). Becoming a principal stays auth-gated.
 *
 * WHY THIS IS A SERVER COMPONENT (the defect it closes, measured live
 * 2026-08-06): the page used to fetch its preview in a `useEffect`, so the HTML
 * a non-JS reader received was `Loading…` and nothing else — while
 * `GET /api/s/{token}` was happily returning 200 with the full artifact. An LLM
 * handed the link read the blank shell and told the operator it was "a private
 * share link … the server intentionally prevents anyone" — a PERMISSIONS
 * REFUSAL hallucinated from an empty page. Every LLM fetcher, every Slack /
 * Notion unfurler and every crawler saw the same nothing. "Share with a link"
 * was true at the API and false at the URL.
 *
 * Rendering discipline (ADR-513 D3, UNCHANGED and non-negotiable):
 * member-authored HTML renders EXCLUSIVELY in a fully-locked iframe
 * (`sandbox=""` — the WebViewer grammar: no scripts, no same-origin). There is
 * no server-side sanitizer, so the sandbox IS the boundary: no looser form and
 * no inlining, ever — least of all now that this markup is server-rendered.
 * Text renders escaped. SSR renders the PAGE; the artifact still goes in the
 * locked frame.
 *
 * Standalone threshold page, deliberately OUTSIDE the (authenticated) shell
 * group — the same lesson as /invite (2026-07-04 incident: inside the shell,
 * SurfaceViewport renders page children only when no windows are mounted).
 */

import type { Metadata } from "next";
import { FileText } from "lucide-react";

import { AttributionWalk, JoinAction } from "./ShareClient";
import { artifactName, fetchSharePreview } from "./share-preview";

/** A capability link is served fresh or not at all — revocation must be the end
 *  of it (ADR-513 D4). Never statically rendered, never revalidated. */
export const dynamic = "force-dynamic";

type PageProps = { params: { token: string } };

/**
 * ADR-529 D3 — honest metadata, and the capability discipline closed at the
 * HTML layer.
 *
 * The page previously inherited the root layout's marketing title and
 * `og:url = https://yarnnn.com`, so a share pasted into any channel unfurled as
 * the landing page rather than the thing being shared. It also declared
 * `index, follow` while the API set `X-Robots-Tag: noindex` — ADR-513 D4 held
 * at the API and leaked here. A capability link must be legible to a reader who
 * was HANDED it and invisible to one who was not; those are not in tension.
 */
export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const result = await fetchSharePreview(params.token);
  const robots = { index: false, follow: false };

  if (result.kind !== "ok") {
    return { title: "Shared with you — yarnnn", robots };
  }

  const p = result.preview;
  const name = artifactName(p);
  const ws = p.workspace_name || "a shared workspace";
  const title = name ? `${name} — shared on yarnnn` : `Join ${ws} — yarnnn`;
  const description = name
    ? `Shared from ${ws}. Every change is signed by whoever made it, human or AI.`
    : `A shared, attributed workspace — every change records who made it.`;

  return {
    title,
    description,
    robots,
    // Explicitly NOT og:url — pointing at the canonical share URL would invite
    // crawlers to treat a capability link as a public address.
    openGraph: { title, description, type: "article" },
    twitter: { card: "summary", title, description },
    // ADR-530 D4 — discovery is DECLARED, not guessed. An agent that reads this
    // page learns where its own representation lives, using the convention the
    // web already has (and that this codebase already speaks via
    // .well-known/mcp.json). The alias is not a second resource: it carries
    // Link: rel="canonical" back here.
    alternates: {
      types: { "text/plain": `/s/${encodeURIComponent(params.token)}.txt` },
    },
  };
}

export default async function SharePublicPage({ params }: PageProps) {
  const token = params.token;
  const result = await fetchSharePreview(token);

  if (result.kind !== "ok") {
    return (
      <Shell>
        <div className="w-full max-w-md rounded-xl border border-border/60 bg-card p-8 text-center shadow-sm">
          <p className="text-sm text-muted-foreground">
            {result.kind === "gone"
              ? result.message
              : "Could not load the share. Try again in a moment."}
          </p>
        </div>
      </Shell>
    );
  }

  const p = result.preview;
  const name = artifactName(p);
  const ws = p.workspace_name || "a shared workspace";
  const walk = p.walk ?? [];
  const hasContent = Boolean(p.artifact_content);

  return (
    <Shell>
      <div className="flex w-full max-w-3xl flex-col gap-4">
        {/* ── The artifact IS the page (ADR-529 D5) — dominant, first, full
            width. The walk rides beneath it as a single line, and joining is a
            quiet footer: the reader came for the document. ── */}
        {hasContent ? (
          <div className="overflow-hidden rounded-xl border border-border/60 bg-card shadow-sm">
            <div className="flex items-center gap-2 border-b border-border/60 px-4 py-2.5">
              <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
              <span className="truncate text-sm font-medium">{name}</span>
              <span className="ml-auto shrink-0 text-xs text-muted-foreground">
                shared from {ws}
                {p.role === "viewer" ? " · read-only" : ""}
              </span>
            </div>

            {p.artifact_kind === "html" ? (
              <>
                {/* ADR-513 D3: the locked sandbox is the ONLY renderer for
                    member HTML. No scripts, no same-origin, no forms, no
                    popups. ADR-530 does NOT loosen this. */}
                <iframe
                  title={name ?? "shared artifact"}
                  srcDoc={p.artifact_content ?? ""}
                  sandbox=""
                  className="h-[75vh] w-full bg-white"
                />
                {/* ADR-530 D1/D2 — the projection, for readers that are not
                    browsers. An iframe's srcDoc is opaque to every fetcher, so
                    the document was invisible to the exact audience a share
                    link is pasted to (the 2026-08-06 defect). This is TEXT and
                    is rendered as text — never markup, never innerHTML. */}
                <noscript>
                  <pre className="max-h-[75vh] overflow-auto whitespace-pre-wrap px-5 py-4 text-sm leading-relaxed">
                    {p.artifact_text}
                  </pre>
                </noscript>
              </>
            ) : (
              <pre className="max-h-[75vh] overflow-auto whitespace-pre-wrap px-5 py-4 text-sm leading-relaxed">
                {p.artifact_text ?? p.artifact_content}
              </pre>
            )}

            {p.truncated && (
              <p className="border-t border-border/60 px-4 py-2 text-xs text-muted-foreground">
                Preview truncated — join the workspace to see the full document.
              </p>
            )}

            <AttributionWalk walk={walk} />
          </div>
        ) : p.artifact_note ? (
          // ADR-530 D3 — a format with no registered strategy yet. DP34's
          // anti-silent-drop clause: a KNOWN GAP said out loud. This boundary
          // used to emit the raw bytes of an xlsx/zip/pdf into a <pre>.
          <div className="rounded-xl border border-border/60 bg-card p-8 text-center shadow-sm">
            <div className="mb-2 flex items-center justify-center gap-2">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">{name}</span>
            </div>
            <p className="text-sm text-muted-foreground">{p.artifact_note}</p>
          </div>
        ) : (
          // A bare workspace share (no artifact) — the preview facts only.
          <div className="rounded-xl border border-border/60 bg-card p-8 text-center shadow-sm">
            <h1 className="text-base font-semibold">Join {ws}</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              A shared, attributed workspace — every change records who made it.
            </p>
          </div>
        )}

        {/* ── Joining: the quiet footer, not a peer column (ADR-529 D5) ── */}
        <div className="rounded-xl border border-border/60 bg-card px-5 py-4 shadow-sm">
          <JoinAction
            token={token}
            role={p.role}
            status={p.status}
            workspaceName={ws}
            hasArtifact={Boolean(name)}
          />
        </div>
      </div>
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center bg-background px-4 py-10">
      <p className="mb-8 font-brand text-2xl">yarnnn</p>
      {children}
    </div>
  );
}
