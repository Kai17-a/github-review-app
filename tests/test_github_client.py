"""github_client モジュールのテスト."""

import pytest
import requests

from github_review_app.config import GitHubConfig
from github_review_app.github_client import (
    FILES_PER_PAGE,
    GitHubAPIError,
    GitHubClient,
)

CONFIG = GitHubConfig(
    token="gh-token",
    repository="owner/repo",
    pull_number=42,
    api_url="https://api.github.test",
)


class FakeResponse:
    def __init__(self, payload, status_code=200, text=""):
        self._payload = payload
        self.status_code = status_code
        self.text = text

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError("http error", response=self)


class FakeSession:
    """requests.Session のテスト用フェイク."""

    def __init__(self, responses):
        self.headers = {}
        self._responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        if not self._responses:
            raise AssertionError("no more fake responses queued")
        return self._responses.pop(0)


def make_client(responses):
    session = FakeSession(responses)
    # FakeSession は requests.Session のダックタイプ代替
    client = GitHubClient(CONFIG, session=session)  # ty: ignore[invalid-argument-type]
    return client, session


class TestInit:
    def test_sets_authentication_headers(self):
        client, session = make_client([])

        assert session.headers["Authorization"] == "Bearer gh-token"
        assert session.headers["Accept"] == "application/vnd.github+json"
        assert session.headers["X-GitHub-Api-Version"]


class TestFetchPullRequestDiff:
    def test_builds_unified_diff_from_file_patches(self):
        files = [
            {"filename": "a.py", "status": "modified", "patch": "@@ -1 +1 @@"},
            {"filename": "b.py", "status": "added", "patch": "@@ -0,0 +1 @@"},
            {"filename": "c.py", "status": "removed", "patch": "@@ -1 +0,0 @@"},
            {"filename": "image.png", "status": "modified"},  # patch なし
        ]
        client, session = make_client([FakeResponse(files)])

        result = client.fetch_pull_request_diff()

        assert result == (
            "--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n"
            "--- /dev/null\n+++ b/b.py\n@@ -0,0 +1 @@\n"
            "--- a/c.py\n+++ /dev/null\n@@ -1 +0,0 @@"
        )
        call = session.calls[0]
        assert call["method"] == "GET"
        assert call["url"] == (
            "https://api.github.test/repos/owner/repo/pulls/42/files"
        )
        assert call["params"] == {"per_page": FILES_PER_PAGE, "page": 1}

    def test_uses_previous_filename_for_renamed_files(self):
        files = [
            {
                "filename": "new.py",
                "previous_filename": "old.py",
                "status": "renamed",
                "patch": "@@ -1 +1 @@",
            }
        ]
        client, _ = make_client([FakeResponse(files)])

        result = client.fetch_pull_request_diff()

        assert result.startswith("--- a/old.py\n+++ b/new.py")

    def test_paginates_until_short_page(self):
        first_page = [
            {
                "filename": f"file{i}.py",
                "status": "modified",
                "patch": f"@@ patch{i} @@",
            }
            for i in range(FILES_PER_PAGE)
        ]
        second_page = [
            {"filename": "last.py", "status": "modified", "patch": "@@ last @@"}
        ]
        client, session = make_client(
            [FakeResponse(first_page), FakeResponse(second_page)]
        )

        result = client.fetch_pull_request_diff()

        assert len(session.calls) == 2
        assert session.calls[1]["params"]["page"] == 2
        assert "@@ patch0 @@" in result
        assert "@@ last @@" in result

    def test_raises_on_unexpected_payload(self):
        client, _ = make_client([FakeResponse({"message": "not found"})])

        with pytest.raises(GitHubAPIError, match="unexpected payload"):
            client.fetch_pull_request_diff()

    def test_raises_on_http_error(self):
        response = FakeResponse(None, status_code=404, text="not found")
        client, _ = make_client([response])

        with pytest.raises(GitHubAPIError, match="404: not found"):
            client.fetch_pull_request_diff()

    def test_raises_on_connection_error(self):
        class ErrorSession(FakeSession):
            def request(self, method, url, **kwargs):
                raise requests.ConnectionError("connection refused")

        client = GitHubClient(
            CONFIG,
            session=ErrorSession([]),  # ty: ignore[invalid-argument-type]
        )

        with pytest.raises(GitHubAPIError, match="connection refused"):
            client.fetch_pull_request_diff()


class TestCreateReview:
    def test_posts_comment_review(self):
        client, session = make_client([FakeResponse({"id": 1})])

        client.create_review("review body")

        call = session.calls[0]
        assert call["method"] == "POST"
        assert call["url"] == (
            "https://api.github.test/repos/owner/repo/pulls/42/reviews"
        )
        assert call["json"] == {"body": "review body", "event": "COMMENT"}
