import { MetadataRoute } from "next";
import { BRAND } from "@/lib/metadata";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: [
          "/api/",
          // Google Search Console, 2026-09-17 — `/auth/` was disallowed while
          // `/auth/login` is linked from the header and footer of every
          // marketing page. That is the ADR-530 D4 distinction again, and it
          // fails the same way it did for `/s/`:
          //
          //   Disallow  = do not FETCH        (Google never reads the page)
          //   noindex   = do not LIST/RETAIN  (Google reads it, then drops it)
          //
          // A sitewide-linked URL WILL be discovered. Banning the fetch does
          // not make it un-indexable; it makes the `noindex` unreadable, so the
          // URL sits in "Blocked by robots.txt" indefinitely and can still be
          // listed on anchor text alone. Un-indexability is already carried
          // where it belongs and is unweakened: `robots: { index: false,
          // follow: false, noarchive, nosnippet }` in app/auth/login/layout.tsx
          // and the meta tag in app/auth/callback/head.tsx. Letting the crawler
          // READ those is what retires the URL for good.
          //
          // `/api/` stays disallowed — it is not linked for crawlers, serves no
          // HTML to read a directive from, and carries `X-Robots-Tag: noindex`
          // at the exit (ADR-513 D4).
          // ADR-530 D4 amendment (2026-08-07) — `/s/` is deliberately NOT
          // disallowed, and the distinction is the whole point:
          //
          //   Disallow  = do not FETCH        (blocks the reader entirely)
          //   noindex   = do not LIST/RETAIN  (blocks the search result)
          //
          // A capability link needs the SECOND, never the first. ADR-529 D3
          // added `/s/` here reasoning "a capability link must be invisible to
          // whoever was not handed it" — true of *indexing*, and wrong as a
          // fetch ban, because the audience a share link is PASTED TO is
          // exactly a well-behaved fetcher. ChatGPT's crawler honors
          // robots.txt, so it refused before ever reading the page: the same
          // "I can't access this" the whole arc exists to eliminate, this time
          // caused by our own policy file rather than by a blank shell.
          //
          // Un-indexability is carried where it belongs and is unweakened:
          // `X-Robots-Tag: noindex, nofollow` on every API exit (ADR-513 D4)
          // and `<meta name="robots" content="noindex, nofollow">` on the page
          // (ADR-529 D3). Those forbid RETENTION; this file must not forbid
          // READING. `/invite/` stays disallowed — it is auth-gated and has
          // nothing to offer a fetcher.
          "/invite/",
          "/admin/",
          "/dashboard/",
          "/orchestrator/",
          "/memory/",
          "/files/",
          "/context/", // redirect stub → /files
          "/system/",
          "/settings/",
          "/agents/",
          "/work/",
          "/chat/",
          "/docs/",
          "/integrations/",
          // Legacy routes (removed — prevent crawl attempts)
          "/baskets/",
          "/blocks/",
          "/projects/",
          "/activity/",
          "/tasks/",
        ],
      },
    ],
    host: BRAND.url,
    sitemap: `${BRAND.url}/sitemap.xml`,
  };
}
