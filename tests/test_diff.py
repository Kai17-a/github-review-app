"""diff モジュールのテスト."""

import io
import subprocess

import pytest

from github_review_app import diff
from github_review_app.diff import (
    DiffError,
    read_local_diff,
    read_stdin_diff,
    resolve_diff,
    truncate_diff,
)


class _TtyStream(io.StringIO):
    def isatty(self):
        return True


class TestTruncateDiff:
    def test_returns_diff_as_is_when_short_enough(self):
        assert truncate_diff("short diff", 100) == "short diff"

    def test_truncates_long_diff(self):
        result = truncate_diff("x" * 200, 100)

        assert result.startswith("x" * 100)
        assert "truncated at 100 characters" in result

    def test_rejects_non_positive_limit(self):
        with pytest.raises(ValueError, match="max_chars"):
            truncate_diff("diff", 0)


class TestReadStdinDiff:
    def test_returns_none_for_tty(self):
        assert read_stdin_diff(_TtyStream("diff")) is None

    def test_returns_none_for_blank_input(self):
        assert read_stdin_diff(io.StringIO("  \n")) is None

    def test_returns_piped_input(self):
        assert read_stdin_diff(io.StringIO("some diff")) == "some diff"


class TestReadLocalDiff:
    def test_runs_git_diff_with_default_base(self, monkeypatch):
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return subprocess.CompletedProcess(cmd, 0, stdout="local-diff")

        monkeypatch.setattr(diff.subprocess, "run", fake_run)

        assert read_local_diff({}) == "local-diff"
        assert captured["cmd"] == ["git", "diff", "--no-color", "HEAD"]

    def test_appends_head_when_set(self, monkeypatch):
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return subprocess.CompletedProcess(cmd, 0, stdout="diff")

        monkeypatch.setattr(diff.subprocess, "run", fake_run)

        read_local_diff({"REVIEW_BASE": "main", "REVIEW_HEAD": "feature"})

        assert captured["cmd"] == [
            "git",
            "diff",
            "--no-color",
            "main",
            "feature",
        ]

    def test_wraps_git_failure(self, monkeypatch):
        def fake_run(cmd, **kwargs):
            raise subprocess.CalledProcessError(
                128, cmd, stderr="fatal: bad revision"
            )

        monkeypatch.setattr(diff.subprocess, "run", fake_run)

        with pytest.raises(DiffError, match="bad revision"):
            read_local_diff({})

    def test_wraps_missing_git_command(self, monkeypatch):
        def fake_run(cmd, **kwargs):
            raise FileNotFoundError("git")

        monkeypatch.setattr(diff.subprocess, "run", fake_run)

        with pytest.raises(DiffError, match="git command not found"):
            read_local_diff({})


class _FakeGitHubClient:
    def __init__(self, diff_text):
        self._diff_text = diff_text

    def fetch_pull_request_diff(self):
        return self._diff_text


class TestResolveDiff:
    def test_prefers_stdin(self):
        result = resolve_diff(
            env={"GITHUB_ACTIONS": "true"},
            stream=io.StringIO("stdin-diff"),
            github_client=_FakeGitHubClient(  # ty: ignore[invalid-argument-type]
                "api-diff"
            ),
        )

        assert result == "stdin-diff"

    def test_uses_github_api_on_actions(self):
        result = resolve_diff(
            env={"GITHUB_ACTIONS": "true"},
            stream=io.StringIO(""),
            github_client=_FakeGitHubClient(  # ty: ignore[invalid-argument-type]
                "api-diff"
            ),
        )

        assert result == "api-diff"

    def test_falls_back_to_local_diff(self, monkeypatch):
        monkeypatch.setattr(diff, "read_local_diff", lambda env: "local-diff")

        result = resolve_diff(env={}, stream=io.StringIO(""))

        assert result == "local-diff"
