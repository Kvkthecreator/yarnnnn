import { HOME_ROUTE } from "@/lib/routes";

const AUTH_PATH_PREFIX = "/auth/";

export function getSafeNextPath(next: string | null | undefined, fallback = HOME_ROUTE): string {
  if (!next) return fallback;

  if (!next.startsWith("/") || next.startsWith("//")) {
    return fallback;
  }

  if (next.startsWith(AUTH_PATH_PREFIX)) {
    return fallback;
  }

  return next;
}

export function getCurrentPathWithSearch(pathname: string, search: string): string {
  return `${pathname}${search || ""}`;
}
