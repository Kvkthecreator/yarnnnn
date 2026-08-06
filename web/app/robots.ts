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
          "/auth/",
          // ADR-529 D3 / ADR-513 D4 — a capability link is legible to whoever
          // was HANDED it and invisible to whoever was not. The API has always
          // set X-Robots-Tag: noindex; the HTML surface leaked (it declared
          // `index, follow` and /s was absent here). The page now emits
          // noindex too — this is the second layer, not the only one.
          "/s/",
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
