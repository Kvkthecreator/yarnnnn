import fs from "fs";
import path from "path";
import matter from "gray-matter";
import readingTime from "reading-time";
import { BRAND } from "@/lib/metadata";

const postsDirectory = path.join(process.cwd(), "..", "content", "posts");

export interface BlogPost {
  slug: string;
  title: string;
  metaTitle: string;
  description: string;
  date: string;
  author: string;
  category: "core" | "opinion";
  tags: string[];
  concept?: string;
  series?: string;
  seriesPart?: number;
  geoTier: number;
  canonicalUrl: string;
  metaDescription: string;
  imageUrl: string;
  lastModified: string;
  wordCount: number;
  status: "draft" | "published";
  readingTime: string;
  content: string;
}

export interface BlogPostMeta
  extends Omit<BlogPost, "content"> {}

function toAbsoluteUrl(value: string): string {
  return new URL(value, BRAND.url).toString();
}

function toMetaDescription(description: string, maxLength = 160): string {
  const normalized = description.replace(/\s+/g, " ").trim();
  if (normalized.length <= maxLength) return normalized;

  const clipped = normalized.slice(0, maxLength + 1);
  const safe = clipped.slice(0, clipped.lastIndexOf(" "));
  return `${safe || normalized.slice(0, maxLength)}...`;
}

function toWordCount(content: string): number {
  return content.trim().split(/\s+/).filter(Boolean).length;
}

function getPostFiles(): string[] {
  if (!fs.existsSync(postsDirectory)) return [];
  return fs
    .readdirSync(postsDirectory)
    .filter((file) => file.endsWith(".md"));
}

export function getPostSlugs(): string[] {
  return getAllPosts().map((post) => post.slug);
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
    metaTitle: data.metaTitle || data.title,
    description: data.description || "",
    date: data.date,
    author: data.author || "yarnnn",
    category: data.category === "opinion" ? "opinion" : "core",
    tags: data.tags || [],
    concept: data.concept,
    series: data.series,
    seriesPart: data.seriesPart,
    geoTier: data.geoTier || 1,
    canonicalUrl: toAbsoluteUrl(
      data.canonicalUrl || `/blog/${data.slug || slug}`
    ),
    metaDescription: toMetaDescription(
      data.metaDescription || data.description || ""
    ),
    imageUrl: toAbsoluteUrl(data.image || BRAND.ogImage),
    lastModified: data.lastModified || data.updatedAt || data.date,
    wordCount: toWordCount(content),
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
        metaTitle: data.metaTitle || data.title,
        description: data.description || "",
        date: data.date,
        author: data.author || "yarnnn",
        category: (data.category === "opinion" ? "opinion" : "core") as BlogPost["category"],
        tags: data.tags || [],
        concept: data.concept,
        series: data.series,
        seriesPart: data.seriesPart,
        geoTier: data.geoTier || 1,
        canonicalUrl: toAbsoluteUrl(
          data.canonicalUrl || `/blog/${data.slug || slug}`
        ),
        metaDescription: toMetaDescription(
          data.metaDescription || data.description || ""
        ),
        imageUrl: toAbsoluteUrl(data.image || BRAND.ogImage),
        lastModified: data.lastModified || data.updatedAt || data.date,
        wordCount: toWordCount(content),
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

function normalizeTag(tag: string): string {
  return tag.trim().toLowerCase();
}

export function getSeriesPosts(series: string): BlogPostMeta[] {
  return getAllPosts()
    .filter((post) => post.series === series)
    .sort((a, b) => {
      const partA = a.seriesPart ?? Number.MAX_SAFE_INTEGER;
      const partB = b.seriesPart ?? Number.MAX_SAFE_INTEGER;
      if (partA !== partB) return partA - partB;
      return new Date(a.date).getTime() - new Date(b.date).getTime();
    });
}

export function getRelatedPosts(slug: string, limit = 3): BlogPostMeta[] {
  const current = getPostBySlug(slug);
  if (!current) return [];

  const currentTags = new Set((current.tags || []).map(normalizeTag));

  const scored = getAllPosts()
    .filter((post) => post.slug !== slug)
    .map((post) => {
      let score = 0;

      if (current.series && post.series && current.series === post.series) {
        score += 6;
      }

      if (current.concept && post.concept && current.concept === post.concept) {
        score += 4;
      }

      if (post.category === current.category) {
        score += 2;
      }

      const sharedTags = (post.tags || []).reduce((count, tag) => {
        return currentTags.has(normalizeTag(tag)) ? count + 1 : count;
      }, 0);
      score += Math.min(sharedTags * 2, 8);

      return { post, score };
    })
    .filter((item) => item.score > 0)
    .sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      return new Date(b.post.date).getTime() - new Date(a.post.date).getTime();
    })
    .map((item) => item.post)
    .slice(0, limit);

  if (scored.length === 0) {
    return getAllPosts()
      .filter((post) => post.slug !== slug && post.category === current.category)
      .slice(0, limit);
  }

  return scored;
}
