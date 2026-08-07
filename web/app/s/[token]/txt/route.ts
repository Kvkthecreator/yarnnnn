/**
 * The share link's MACHINE ADDRESS on the app domain — ADR-530 D4.
 *
 * `https://yarnnn.com/s/{token}.txt` is what a person pastes when they want an
 * agent to read a shared document. It is an ALIAS of `/s/{token}`, never a
 * second resource: same token, same capability, same revocation, same
 * lifecycle, and a `Link: rel="canonical"` back to the share URL so no crawler,
 * cache or agent treats it as separate content.
 *
 * Why this exists on the WEB origin and not only on the API: the address people
 * copy is `yarnnn.com/s/{token}`, so its machine sibling must be reachable by
 * adding `.txt` to the thing in their clipboard. An address you have to rewrite
 * onto another hostname is not pasteable, and pasteability is the entire reason
 * the alias exists beside content negotiation (agents in the wild paste; they
 * do not negotiate — the 2026-08-06 receipt is ChatGPT fetching a share link
 * with `Accept: text/html`).
 *
 * `/s/{token}.txt` is expressed as the route `/s/[token]/txt` plus a rewrite in
 * next.config.js, because a Next dynamic segment cannot carry a literal suffix.
 *
 * This is a pure transport hop: the API owns the projection, the lifecycle
 * checks and the capability headers (ADR-513 D4). Nothing is computed here.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const dynamic = "force-dynamic";

export async function GET(
  _req: Request,
  { params }: { params: { token: string } },
) {
  const token = params.token;
  const upstream = await fetch(
    `${API_BASE_URL}/api/s/${encodeURIComponent(token)}.txt`,
    { cache: "no-store", headers: { Accept: "text/plain" } },
  ).catch(() => null);

  // A capability link must not be cached by intermediaries, on EVERY status —
  // the dark states most of all (ADR-513 D4).
  //
  // `X-Robots-Tag: noindex` is deliberately ABSENT (ADR-531 D1): it was the one
  // failing item on the measured checklist for ChatGPT, whose retrieval is at
  // least partly search-mediated. Removing it removes an obstacle; it does not
  // guarantee retrieval (OpenAI: indexing is a common cause of delay, not a
  // strict requirement — MCP stays the reliable lane). Revocation stays
  // authoritative at the origin and becomes best-effort in the world — a named,
  // accepted trade, not an oversight.
  const headers: Record<string, string> = {
    "Content-Type": "text/plain; charset=utf-8",
    "Cache-Control": "no-store",
  };

  if (!upstream) {
    return new Response("Could not load this share right now.\n", {
      status: 502,
      headers,
    });
  }

  // Carry the canonical pointer through the hop — the alias points home.
  const link = upstream.headers.get("link");
  if (link) headers["Link"] = link;

  if (!upstream.ok) {
    return new Response(
      upstream.status === 404 || upstream.status === 410
        ? "This share link doesn't exist or has been revoked.\n"
        : "Could not load this share.\n",
      { status: upstream.status, headers },
    );
  }

  return new Response(await upstream.text(), { status: 200, headers });
}
