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
          "/admin/",
          "/dashboard/",
          "/orchestrator/",
          "/memory/",
          "/context/",
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
