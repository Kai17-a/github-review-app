"""GitHub REST API クライアント."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import requests

from .config import GITHUB_API_VERSION, GitHubConfig

FILES_PER_PAGE = 100
DEFAULT_TIMEOUT = 60.0


class GitHubAPIError(RuntimeError):
    """GitHub API 呼び出しの失敗."""


class GitHubClient:
    """Pull Request の差分取得とレビュー投稿を行う."""

    def __init__(
        self,
        config: GitHubConfig,
        *,
        session: requests.Session | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._config = config
        self._timeout = timeout
        self._session = session or requests.Session()
        self._session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {config.token}",
                "X-GitHub-Api-Version": GITHUB_API_VERSION,
            }
        )

    def fetch_pull_request_diff(self) -> str:
        """PR の変更ファイルから unified diff 相当のテキストを組み立てる."""
        patches = []
        for item in self._iter_pull_request_files():
            patch = self._format_file_patch(item)
            if patch is not None:
                patches.append(patch)
        return "\n".join(patches)

    def create_review(self, body: str) -> None:
        """PR にレビューコメントを投稿する."""
        self._request(
            "POST",
            self._pull_request_path("reviews"),
            json_body={"body": body, "event": "COMMENT"},
        )

    def _pull_request_path(self, suffix: str) -> str:
        repository = self._config.repository
        pull_number = self._config.pull_number
        return f"/repos/{repository}/pulls/{pull_number}/{suffix}"

    def _iter_pull_request_files(self) -> Iterator[dict[str, Any]]:
        page = 1
        while True:
            files = self._request(
                "GET",
                self._pull_request_path("files"),
                params={"per_page": FILES_PER_PAGE, "page": page},
            )
            if not isinstance(files, list):
                raise GitHubAPIError(
                    "the pull request files API returned an unexpected payload"
                )
            for item in files:
                if isinstance(item, dict):
                    yield item
            if len(files) < FILES_PER_PAGE:
                return
            page += 1

    @staticmethod
    def _format_file_patch(item: dict[str, Any]) -> str | None:
        filename = item.get("filename")
        patch = item.get("patch")
        if not filename or not patch:
            # バイナリファイルや差分が大きすぎるファイルは patch を持たない
            return None
        status = item.get("status")
        if status == "added":
            old_name = "/dev/null"
        else:
            old_name = f"a/{item.get('previous_filename', filename)}"
        new_name = "/dev/null" if status == "removed" else f"b/{filename}"
        return f"--- {old_name}\n+++ {new_name}\n{patch}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self._config.api_url}{path}"
        try:
            response = self._session.request(
                method,
                url,
                params=params,
                json=json_body,
                timeout=self._timeout,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            if exc.response is not None:
                status = exc.response.status_code
                detail = exc.response.text
            else:
                status = "unknown"
                detail = str(exc)
            raise GitHubAPIError(
                f"GitHub API {method} {path} failed with {status}: {detail}"
            ) from exc
        except requests.RequestException as exc:
            raise GitHubAPIError(
                f"GitHub API {method} {path} failed: {exc}"
            ) from exc
        try:
            return response.json()
        except ValueError:
            return None
