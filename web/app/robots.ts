import { MetadataRoute } from "next";
import { BRAND } from "@/lib/metadata";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/api/", "/auth/callback"],
      },
    ],
    sitemap: `${BRAND.url}/sitemap.xml`,
  };
}
