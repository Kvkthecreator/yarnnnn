/**
 * Is a newer interface live than the one this window loaded? (ADR-663 D7)
 *
 * A web deploy reaches every browser and every desktop app (ADR-663 D1) — but
 * only on the next page load. A window left open keeps running the build it
 * loaded, for days in a desktop app, and meets the next deploy's missing chunks
 * as errors that look like bugs. So the page compares the build it was loaded
 * from (`NEXT_PUBLIC_DEPLOYMENT`, baked in by `next.config.js`) with the one the
 * site serves now (`/api/deployment`), and `UpdateNotice` offers a reload.
 *
 * Off Vercel both are empty and the check is off.
 */

/** The build this page was loaded from. */
export const LOADED_DEPLOYMENT = process.env.NEXT_PUBLIC_DEPLOYMENT || "";

/** The build the site serves now, or null when unknown (offline, dev). */
export async function servedDeployment(): Promise<string | null> {
  if (!LOADED_DEPLOYMENT) return null;
  try {
    const res = await fetch("/api/deployment", { cache: "no-store" });
    if (!res.ok) return null;
    const { deployment } = (await res.json()) as { deployment?: unknown };
    return typeof deployment === "string" && deployment ? deployment : null;
  } catch {
    return null;
  }
}
