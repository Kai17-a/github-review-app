"""cli モジュールのテスト."""

import pytest

from github_review_app import cli
from github_review_app.cli import REVIEW_HEADER, build_review_body, main, run

LLM_ENV = {
    "LLM_API_BASE_URL": "https://llm.example.com/v1",
    "LLM_API_KEY": "test-key",
}


class FakeReviewClient:
    posted_diffs = []

    def __init__(self, config):
        self.config = config

    def review(self, diff, *, debug=False):
        type(self).posted_diffs.append(diff)
        return "素晴らしいコードです。"


class FakeGitHubClient:
    instances = []

    def __init__(self, config):
        self.config = config
        self.reviews = []
        type(self).instances.append(self)

    def create_review(self, body):
        self.reviews.append(body)


@pytest.fixture(autouse=True)
def reset_fakes():
    FakeReviewClient.posted_diffs = []
    FakeGitHubClient.instances = []


@pytest.fixture
def review_env(monkeypatch):
    for key, value in LLM_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("REVIEW_DEBUG", raising=False)
    monkeypatch.setattr(cli, "resolve_diff", lambda: "some diff")
    monkeypatch.setattr(cli, "ReviewClient", FakeReviewClient)
    monkeypatch.setattr(cli, "GitHubClient", FakeGitHubClient)


class TestBuildReviewBody:
    def test_includes_header_marker(self):
        body = build_review_body("review text")

        assert body.startswith(REVIEW_HEADER)
        assert "review text" in body


class TestRun:
    def test_skips_when_diff_is_empty(self, monkeypatch, capsys):
        monkeypatch.setattr(cli, "resolve_diff", lambda: "  \n")

        run()

        assert "スキップ" in capsys.readouterr().err

    def test_prints_review_without_posting_locally(self, review_env, capsys):
        run()

        out = capsys.readouterr().out
        assert REVIEW_HEADER in out
        assert "素晴らしいコードです。" in out
        assert FakeReviewClient.posted_diffs == ["some diff"]
        assert FakeGitHubClient.instances == []

    def test_posts_review_on_github_actions(self, review_env, monkeypatch):
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        monkeypatch.setenv("GITHUB_TOKEN", "gh-token")
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        monkeypatch.setenv("PR_NUMBER", "42")

        run()

        (client,) = FakeGitHubClient.instances
        assert client.config.pull_number == 42
        assert len(client.reviews) == 1
        assert client.reviews[0].startswith(REVIEW_HEADER)

    def test_truncates_diff_before_review(self, review_env, monkeypatch):
        monkeypatch.setenv("MAX_DIFF_CHARS", "10")
        monkeypatch.setattr(cli, "resolve_diff", lambda: "x" * 100)

        run()

        (diff,) = FakeReviewClient.posted_diffs
        assert diff.startswith("x" * 10)
        assert "truncated" in diff


class TestMain:
    def test_returns_zero_on_success(self, review_env):
        assert main() == 0

    def test_returns_one_on_failure(self, monkeypatch, capsys):
        monkeypatch.setattr(
            cli,
            "resolve_diff",
            lambda: (_ for _ in ()).throw(RuntimeError("x")),
        )

        assert main() == 1
        assert "error" in capsys.readouterr().err
