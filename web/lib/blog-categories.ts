export const BLOG_CATEGORIES = [
  "how-it-works",
  "where-its-going",
  "what-were-seeing",
] as const;

export type BlogCategory = (typeof BLOG_CATEGORIES)[number];

export const BLOG_CATEGORY_LABELS: Record<BlogCategory, string> = {
  "how-it-works": "How It Works",
  "where-its-going": "Where It's Going",
  "what-were-seeing": "What We're Seeing",
};

export function normalizeBlogCategory(value?: string | null): BlogCategory {
  if (value && BLOG_CATEGORIES.includes(value as BlogCategory)) {
    return value as BlogCategory;
  }

  if (value === "core") return "how-it-works";
  if (value === "opinion") return "where-its-going";

  return "how-it-works";
}

export function getBlogCategoryLabel(category: string): string {
  return BLOG_CATEGORY_LABELS[normalizeBlogCategory(category)];
}
