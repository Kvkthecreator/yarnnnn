import fs from "fs";
import path from "path";
import matter from "gray-matter";
import readingTime from "reading-time";

const postsDirectory = path.join(process.cwd(), "..", "content", "posts");

export interface BlogPost {
  slug: string;
  title: string;
  description: string;
  date: string;
  author: string;
  tags: string[];
  geoTier: number;
  canonicalUrl: string;
  status: "draft" | "published";
  readingTime: string;
  content: string;
}

export interface BlogPostMeta
  extends Omit<BlogPost, "content"> {}

function getPostFiles(): string[] {
  if (!fs.existsSync(postsDirectory)) return [];
  return fs
    .readdirSync(postsDirectory)
    .filter((file) => file.endsWith(".md"));
}

export function getPostSlugs(): string[] {
  return getPostFiles().map((file) => file.replace(/\.md$/, ""));
}

export function getPostBySlug(slug: string): BlogPost | null {
  const fullPath = path.join(postsDirectory, `${slug}.md`);
  if (!fs.existsSync(fullPath)) return null;

  const fileContents = fs.readFileSync(fullPath, "utf8");
  const { data, content } = matter(fileContents);

  if (data.status !== "published") return null;

  const stats = readingTime(content);

  return {
    slug: data.slug || slug,
    title: data.title,
    description: data.description || "",
    date: data.date,
    author: data.author || "yarnnn",
    tags: data.tags || [],
    geoTier: data.geoTier || 1,
    canonicalUrl:
      data.canonicalUrl || `https://www.yarnnn.com/blog/${data.slug || slug}`,
    status: data.status,
    readingTime: stats.text,
    content,
  };
}

export function getAllPosts(): BlogPostMeta[] {
  const files = getPostFiles();

  const posts = files
    .map((file) => {
      const slug = file.replace(/\.md$/, "");
      const fullPath = path.join(postsDirectory, file);
      const fileContents = fs.readFileSync(fullPath, "utf8");
      const { data, content } = matter(fileContents);

      if (data.status !== "published") return null;

      const stats = readingTime(content);

      return {
        slug: data.slug || slug,
        title: data.title,
        description: data.description || "",
        date: data.date,
        author: data.author || "yarnnn",
        tags: data.tags || [],
        geoTier: data.geoTier || 1,
        canonicalUrl:
          data.canonicalUrl ||
          `https://www.yarnnn.com/blog/${data.slug || slug}`,
        status: data.status as "published",
        readingTime: stats.text,
      };
    })
    .filter((post): post is NonNullable<typeof post> => post !== null)
    .sort(
      (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
    );

  return posts;
}
