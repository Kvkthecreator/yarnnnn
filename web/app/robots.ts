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
          "/activity/",
          "/memory/",
          "/context/",
          "/system/",
          "/settings/",
          "/agents/",
          "/docs/",
          "/integrations/",
          // Legacy routes (removed — prevent crawl attempts)
          "/baskets/",
          "/blocks/",
          "/projects/",
        ],
      },
    ],
    host: BRAND.url,
    sitemap: `${BRAND.url}/sitemap.xml`,
  };
}
