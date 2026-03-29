"""
GitHub API Client — ADR-147: GitHub Platform Integration

Direct API client for GitHub operations (ADR-076 pattern).
Uses GitHub REST API v3 with OAuth access tokens.

Key difference from Slack/Notion: GitHub tokens can expire,
so this client supports transparent token refresh on 401.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Any

import httpx

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
_GITHUB_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
_MAX_RETRIES = 3
_RETRY_BACKOFF_SECONDS = [1, 2, 4]
_RATE_LIMIT_FLOOR = 100  # Back off when remaining < this


class GitHubAPIClient:
    """
    Direct API client for GitHub operations.

    Uses GitHub REST API v3 with user OAuth tokens.

    Usage:
        client = GitHubAPIClient()
        repos = await client.list_repos(token="gho_...")
        issues = await client.list_issues(token="gho_...", repo="owner/repo")
    """

    async def _request(
        self,
        method: str,
        path: str,
        token: str,
        params: Optional[dict] = None,
        json_body: Optional[dict] = None,
    ) -> Any:
        """
        Make GitHub API request with retry on transient failures.

        Handles:
        - Rate limiting (403 with X-RateLimit-Remaining: 0)
        - 401 (token expired — caller handles refresh)
        - Retries on 5xx and timeouts
        """
        url = f"{GITHUB_API_BASE}{path}"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        last_error = None

        for attempt in range(_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=_GITHUB_TIMEOUT) as client:
                    response = await client.request(
                        method, url, headers=headers,
                        params=params, json=json_body,
                    )

                # Rate limit check
                remaining = int(response.headers.get("X-RateLimit-Remaining", "999"))
                if remaining < _RATE_LIMIT_FLOOR:
                    reset_at = int(response.headers.get("X-RateLimit-Reset", "0"))
                    wait = max(reset_at - int(datetime.now(timezone.utc).timestamp()), 1)
                    if response.status_code == 403 and remaining == 0:
                        logger.warning(f"[GITHUB_API] Rate limited, waiting {wait}s")
                        await asyncio.sleep(min(wait, 60))
                        continue
                    logger.info(f"[GITHUB_API] Rate limit low: {remaining} remaining")

                # 401 = token expired — bubble up for refresh handling
                if response.status_code == 401:
                    return {"error": "token_expired", "status": 401}

                # 404 = not found
                if response.status_code == 404:
                    return {"error": "not_found", "status": 404}

                # 5xx = retry
                if response.status_code >= 500:
                    last_error = f"GitHub API {response.status_code}"
                    backoff = _RETRY_BACKOFF_SECONDS[min(attempt, len(_RETRY_BACKOFF_SECONDS) - 1)]
                    await asyncio.sleep(backoff)
                    continue

                # Success
                if response.status_code in (200, 201):
                    return response.json()

                return {"error": f"Unexpected status {response.status_code}", "status": response.status_code}

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = str(e)
                backoff = _RETRY_BACKOFF_SECONDS[min(attempt, len(_RETRY_BACKOFF_SECONDS) - 1)]
                logger.warning(f"[GITHUB_API] Request failed (attempt {attempt + 1}): {e}")
                await asyncio.sleep(backoff)
            except Exception as e:
                logger.error(f"[GITHUB_API] Unexpected error: {e}")
                return {"error": str(e)}

        return {"error": f"Max retries exceeded: {last_error}"}

    async def _paginate(
        self,
        path: str,
        token: str,
        params: Optional[dict] = None,
        max_pages: int = 10,
        per_page: int = 100,
    ) -> list:
        """Paginate through GitHub API results using page-based pagination."""
        all_results = []
        params = dict(params or {})
        params["per_page"] = per_page

        for page in range(1, max_pages + 1):
            params["page"] = page
            result = await self._request("GET", path, token, params=params)

            if isinstance(result, dict) and result.get("error"):
                logger.warning(f"[GITHUB_API] Pagination error on page {page}: {result}")
                break

            if isinstance(result, list):
                all_results.extend(result)
                if len(result) < per_page:
                    break  # Last page
            else:
                break

        return all_results

    # =========================================================================
    # User
    # =========================================================================

    async def get_user(self, token: str) -> dict:
        """Get authenticated user profile."""
        result = await self._request("GET", "/user", token)
        return result if isinstance(result, dict) else {}

    # =========================================================================
    # Repositories
    # =========================================================================

    async def list_repos(
        self,
        token: str,
        sort: str = "updated",
        direction: str = "desc",
        max_repos: int = 100,
    ) -> list[dict]:
        """
        List repos accessible to the authenticated user.

        Returns personal + collaborator repos, sorted by most recently updated.
        Excludes forks by default for cleaner landscape.
        """
        repos = await self._paginate(
            "/user/repos",
            token,
            params={
                "sort": sort,
                "direction": direction,
                "affiliation": "owner,collaborator",
            },
            max_pages=max(1, max_repos // 100),
        )
        return repos

    # =========================================================================
    # Issues
    # =========================================================================

    async def list_issues(
        self,
        token: str,
        repo: str,
        state: str = "open",
        since: Optional[str] = None,
        per_page: int = 50,
        max_pages: int = 5,
    ) -> list[dict]:
        """
        List issues for a repository.

        Args:
            repo: "owner/repo" format
            state: "open", "closed", or "all"
            since: ISO 8601 timestamp — only issues updated after this date
            per_page: Results per page (max 100)
            max_pages: Maximum pages to fetch
        """
        params: dict[str, Any] = {
            "state": state,
            "sort": "updated",
            "direction": "desc",
        }
        if since:
            params["since"] = since

        return await self._paginate(
            f"/repos/{repo}/issues",
            token,
            params=params,
            per_page=per_page,
            max_pages=max_pages,
        )

    async def get_issue_comments(
        self,
        token: str,
        repo: str,
        issue_number: int,
        per_page: int = 10,
    ) -> list[dict]:
        """Get comments on an issue (top N for context)."""
        result = await self._request(
            "GET",
            f"/repos/{repo}/issues/{issue_number}/comments",
            token,
            params={"per_page": per_page, "page": 1},
        )
        return result if isinstance(result, list) else []

    # =========================================================================
    # Pull Requests
    # =========================================================================

    async def list_pull_requests(
        self,
        token: str,
        repo: str,
        state: str = "all",
        sort: str = "updated",
        direction: str = "desc",
        per_page: int = 30,
        max_pages: int = 3,
    ) -> list[dict]:
        """
        List pull requests for a repository.

        Note: GitHub Issues API also returns PRs (they share numbering).
        This endpoint gives PR-specific fields (mergeable, head, base).
        """
        return await self._paginate(
            f"/repos/{repo}/pulls",
            token,
            params={"state": state, "sort": sort, "direction": direction},
            per_page=per_page,
            max_pages=max_pages,
        )

    # =========================================================================
    # Write operations (Phase 2 — delivery)
    # =========================================================================

    async def create_issue(
        self,
        token: str,
        repo: str,
        title: str,
        body: str,
        labels: Optional[list[str]] = None,
    ) -> dict:
        """Create an issue in a repository."""
        payload: dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        return await self._request("POST", f"/repos/{repo}/issues", token, json_body=payload)

    # =========================================================================
    # Token Refresh
    # =========================================================================

    async def refresh_token(self, refresh_token: str) -> Optional[dict]:
        """
        Refresh an expired GitHub OAuth token.

        ADR-147 D.2: GitHub OAuth tokens can expire. This method exchanges
        a refresh token for new access + refresh tokens.

        Returns dict with access_token, refresh_token, expires_in on success.
        Returns None on failure.
        """
        client_id = os.getenv("GITHUB_CLIENT_ID", "")
        client_secret = os.getenv("GITHUB_CLIENT_SECRET", "")

        if not client_id or not client_secret:
            logger.error("[GITHUB_API] Cannot refresh token — missing GITHUB_CLIENT_ID/SECRET")
            return None

        try:
            async with httpx.AsyncClient(timeout=_GITHUB_TIMEOUT) as client:
                response = await client.post(
                    "https://github.com/login/oauth/access_token",
                    headers={"Accept": "application/json"},
                    data={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                    },
                )
                data = response.json()

                if "error" in data:
                    logger.error(f"[GITHUB_API] Token refresh failed: {data.get('error')}")
                    return None

                if "access_token" not in data:
                    logger.error("[GITHUB_API] Token refresh response missing access_token")
                    return None

                return data

        except Exception as e:
            logger.error(f"[GITHUB_API] Token refresh error: {e}")
            return None


# Singleton
_github_client: Optional[GitHubAPIClient] = None


def get_github_client() -> GitHubAPIClient:
    """Get or create the GitHub API client singleton."""
    global _github_client
    if _github_client is None:
        _github_client = GitHubAPIClient()
    return _github_client
