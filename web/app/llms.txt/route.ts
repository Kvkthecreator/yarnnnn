import { BRAND } from "@/lib/metadata";
import { getAllPosts } from "@/lib/blog";

export async function GET() {
  const posts = getAllPosts();
  const lines = [
    `# ${BRAND.name}`,
    "",
    `> ${BRAND.tagline}`,
    "",
    "## What this site is",
    `${BRAND.description}`,
    "",
    "## Canonical sources",
    `${BRAND.url}/blog`,
    `${BRAND.url}/blog/rss.xml`,
    `${BRAND.url}/sitemap.xml`,
    "",
    "## Recent blog posts",
    ...posts.slice(0, 20).map((post) => `- ${post.title}: ${post.canonicalUrl}`),
    "",
  ];

  return new Response(lines.join("\n"), {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
    },
  });
}
