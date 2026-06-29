import io
import os

import diff_reader


def test_read_diff_falls_back_on_whitespace_stdin(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("   \n"))
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setattr(diff_reader, "read_local_diff", lambda: "local-diff")

    assert diff_reader.read_diff() == "local-diff"


def test_read_diff_falls_back_to_local_on_empty_stdin(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setattr(diff_reader, "read_local_diff", lambda: "local-diff")

    assert diff_reader.read_diff() == "local-diff"


def test_read_diff_falls_back_on_empty_stdin_in_github_actions(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    monkeypatch.setitem(os.environ, "GITHUB_ACTIONS", "true")
    monkeypatch.setattr(diff_reader, "get_github_settings", lambda: {})
    monkeypatch.setattr(
        diff_reader,
        "fetch_pr_diff_files",
        lambda settings: "api-diff",
    )

    assert diff_reader.read_diff() == "api-diff"
