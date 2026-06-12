import io
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return b"{}"


def test_http_request_uses_bearer_token_by_default(monkeypatch):
    captured = []

    def urlopen(request):
        captured.append(dict(request.header_items()))
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", urlopen)

    main.http_request("https://api.github.test", token="gh-token")

    assert captured[0]["Authorization"] == "Bearer gh-token"


def test_http_request_uses_raw_token_for_custom_auth_header(monkeypatch):
    captured = []

    def urlopen(request):
        captured.append(dict(request.header_items()))
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", urlopen)

    main.http_request(
        "https://llm.test",
        token="llm-token",
        auth_header="apiKey",
    )

    headers_lower = {key.lower(): value for key, value in captured[0].items()}
    assert headers_lower["apikey"] == "llm-token"
    assert "authorization" not in headers_lower


@pytest.mark.parametrize(
    "auth_header",
    ["Bad\nHeader", "Bad Header", "Bad\tHeader", "Bad\x00Header", None],
)
def test_http_request_rejects_invalid_auth_header(auth_header):
    with pytest.raises(ValueError):
        main.http_request(
            "https://api.test",
            token="token",
            auth_header=auth_header,
        )


def test_read_diff_falls_back_on_whitespace_stdin(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("   \n"))
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setattr(main, "read_local_diff", lambda: "local-diff")

    assert main.read_diff() == "local-diff"


def test_read_diff_falls_back_to_local_on_empty_stdin(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setattr(main, "read_local_diff", lambda: "local-diff")

    assert main.read_diff() == "local-diff"


def test_read_diff_falls_back_on_empty_stdin_in_github_actions(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    monkeypatch.setitem(os.environ, "GITHUB_ACTIONS", "true")
    monkeypatch.setattr(main, "get_github_settings", lambda: {})
    monkeypatch.setattr(main, "fetch_pr_diff_files", lambda settings: "api-diff")

    assert main.read_diff() == "api-diff"


def test_review_diff_raises_on_api_error(monkeypatch):
    monkeypatch.setattr(
        main,
        "http_request",
        lambda *args, **kwargs: (401, '{"error":"invalid key"}'),
    )

    with pytest.raises(ValueError, match="Review API request failed"):
        main.review_diff("https://api.test", "key", "model", "diff", debug=False)
