"use client";

import { useState } from "react";
import Link from "next/link";
import { format } from "date-fns";
import type { BlogPostMeta } from "@/lib/blog";
import {
  BLOG_CATEGORIES,
  getBlogCategoryLabel,
  type BlogCategory,
} from "@/lib/blog-categories";

const TABS = [
  { key: "all", label: "All" },
  ...BLOG_CATEGORIES.map((category) => ({
    key: category,
    label: getBlogCategoryLabel(category),
  })),
] as const;

type TabKey = (typeof TABS)[number]["key"];

export default function BlogPostList({ posts }: { posts: BlogPostMeta[] }) {
  const [activeTab, setActiveTab] = useState<TabKey>("all");

  const filtered =
    activeTab === "all"
      ? posts
      : posts.filter((p) => p.category === activeTab as BlogCategory);

  return (
    <>
      <div className="flex gap-1 mb-16">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-3 py-1.5 text-sm rounded-full transition-colors ${
              activeTab === tab.key
                ? "text-foreground bg-foreground/10"
                : "text-muted-foreground/60 hover:text-muted-foreground"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <p className="text-muted-foreground/60">No posts in this category yet.</p>
      ) : (
        <div className="space-y-12">
          {filtered.map((post) => (
            <article key={post.slug}>
              <Link href={`/blog/${post.slug}`} className="group block">
                <div className="flex items-center gap-3 text-sm text-muted-foreground/60 mb-2">
                  <time dateTime={post.date}>
                    {format(new Date(post.date), "MMMM d, yyyy")}
                  </time>
                  <span>&middot;</span>
                  <span>{post.readingTime}</span>
                  <span>&middot;</span>
                  <span className="text-muted-foreground/70">
                    {getBlogCategoryLabel(post.category)}
                  </span>
                </div>
                <h2 className="text-xl md:text-2xl font-medium group-hover:opacity-70 transition-colors mb-2">
                  {post.title}
                </h2>
                <p className="text-muted-foreground leading-relaxed">
                  {post.description}
                </p>
              </Link>
            </article>
          ))}
        </div>
      )}
    </>
  );
}
