import { BRAND } from "@/lib/metadata";
import { getAllPosts } from "@/lib/blog";

function xmlEscape(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

export async function GET() {
  const posts = getAllPosts();
  const now = new Date().toUTCString();

  const items = posts
    .map((post) => {
      const pubDate = new Date(post.date).toUTCString();
      const categories = (post.tags || [])
        .map((tag: string) => `      <category>${xmlEscape(tag)}</category>`)
        .join("\n");
      return `
    <item>
      <title>${xmlEscape(post.title)}</title>
      <link>${xmlEscape(post.canonicalUrl)}</link>
      <guid isPermaLink="true">${xmlEscape(post.canonicalUrl)}</guid>
      <pubDate>${pubDate}</pubDate>
      <description>${xmlEscape(post.metaDescription)}</description>
      <author>admin@yarnnn.com (${xmlEscape(BRAND.name)})</author>${categories ? `\n${categories}` : ""}
    </item>`;
    })
    .join("");

  const feed = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>${xmlEscape(`${BRAND.name} Blog`)}</title>
    <link>${xmlEscape(`${BRAND.url}/blog`)}</link>
    <description>${xmlEscape("Ideas on context-powered AI agents, autonomous work, and why your agent should get smarter the longer you use it.")}</description>
    <language>en-us</language>
    <lastBuildDate>${now}</lastBuildDate>${items}
  </channel>
</rss>`;

  return new Response(feed, {
    headers: {
      "Content-Type": "application/rss+xml; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
    },
  });
}
