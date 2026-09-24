/**
 * /api/deployment — the build the site serves now (ADR-663 D7), read by
 * `lib/shell/deployment.ts` to tell a long-open window a newer one is live.
 *
 * Static on purpose: rendered once per build, so it answers with THAT build's
 * commit from the CDN and never invokes a function. The same variable
 * `next.config.js` bakes into the client, so a window and the build it came
 * from always agree.
 */
export const dynamic = "force-static";

export function GET() {
  return Response.json({ deployment: process.env.VERCEL_GIT_COMMIT_SHA || "" });
}
