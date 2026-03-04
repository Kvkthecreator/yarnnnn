"use client";

import { useState } from "react";
import Link from "next/link";
import { format } from "date-fns";
import type { BlogPostMeta } from "@/lib/blog";

const TABS = [
  { key: "all", label: "All" },
  { key: "core", label: "Core" },
  { key: "opinion", label: "KVK Opinions" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

function getDisplayAuthor(author: string): string {
  if (author === "kvk") return "Kevin Kim";
  return author.toUpperCase();
}

export default function BlogPostList({ posts }: { posts: BlogPostMeta[] }) {
  const [activeTab, setActiveTab] = useState<TabKey>("all");

  const filtered =
    activeTab === "all"
      ? posts
      : posts.filter((p) => p.category === activeTab);

  return (
    <>
      <div className="flex gap-1 mb-16">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-3 py-1.5 text-sm rounded-full transition-colors ${
              activeTab === tab.key
                ? "text-white bg-white/10"
                : "text-white/40 hover:text-white/60"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <p className="text-white/30">No posts in this category yet.</p>
      ) : (
        <div className="space-y-12">
          {filtered.map((post) => (
            <article key={post.slug}>
              <Link href={`/blog/${post.slug}`} className="group block">
                <div className="flex items-center gap-3 text-sm text-white/30 mb-2">
                  <time dateTime={post.date}>
                    {format(new Date(post.date), "MMMM d, yyyy")}
                  </time>
                  <span>&middot;</span>
                  <span>{post.readingTime}</span>
                  {post.category === "opinion" && (
                    <>
                      <span>&middot;</span>
                      <span className="text-white/40">Opinion</span>
                    </>
                  )}
                </div>
                <h2 className="text-xl md:text-2xl font-medium group-hover:text-white/80 transition-colors mb-2">
                  {post.title}
                </h2>
                <p className="text-white/50 leading-relaxed">
                  {post.description}
                </p>
                {post.category === "opinion" && (
                  <p className="text-sm text-white/30 mt-2">
                    {getDisplayAuthor(post.author)}
                  </p>
                )}
              </Link>
            </article>
          ))}
        </div>
      )}
    </>
  );
}
