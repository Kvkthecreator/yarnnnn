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
          "/deliverables/",
          "/docs/",
          "/integrations/",
        ],
      },
    ],
    host: BRAND.url,
    sitemap: `${BRAND.url}/sitemap.xml`,
  };
}
