import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function resolveBackendFeedUrl(): string {
  const baseUrl = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL;
  if (!baseUrl) {
    throw new Error("Missing API_URL or NEXT_PUBLIC_API_URL for feed proxy");
  }

  const normalized = baseUrl.endsWith("/") ? baseUrl.slice(0, -1) : baseUrl;
  return `${normalized}/api/feed`;
}

export async function POST(request: NextRequest): Promise<Response> {
  let upstreamUrl: string;
  try {
    upstreamUrl = resolveBackendFeedUrl();
  } catch (error) {
    console.error("[feed-proxy] configuration error:", error);
    return Response.json(
      { detail: "Feed proxy is not configured" },
      { status: 500 }
    );
  }

  const headers = new Headers();
  const authorization = request.headers.get("authorization");
  const contentType = request.headers.get("content-type");
  const cookie = request.headers.get("cookie");

  if (authorization) headers.set("authorization", authorization);
  if (contentType) headers.set("content-type", contentType);
  if (cookie) headers.set("cookie", cookie);

  let upstreamResponse: Response;
  try {
    upstreamResponse = await fetch(upstreamUrl, {
      method: "POST",
      headers,
      body: await request.text(),
      cache: "no-store",
    });
  } catch (error) {
    console.error("[feed-proxy] upstream request failed:", error);
    return Response.json(
      { detail: "Upstream feed request failed" },
      { status: 502 }
    );
  }

  const responseHeaders = new Headers();
  const upstreamContentType = upstreamResponse.headers.get("content-type");
  if (upstreamContentType) {
    responseHeaders.set("content-type", upstreamContentType);
  }
  responseHeaders.set("cache-control", "no-cache, no-store, must-revalidate");

  return new Response(upstreamResponse.body, {
    status: upstreamResponse.status,
    headers: responseHeaders,
  });
}
