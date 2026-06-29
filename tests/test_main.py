import io
import os
import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import diff_reader
import http_client
import reviewer


class FakeResponse:
    status_code = 200
    text = "{}"

    def __init__(self, text: str = "{}", status_code: int = 200):
        self.text = text
        self.status_code = status_code


def test_http_request_uses_bearer_token_by_default(monkeypatch):
    captured = []

    def request(method, url, **kwargs):
        captured.append((method, url, kwargs))
        return FakeResponse()

    monkeypatch.setattr("requests.request", request)

    http_client.http_request("https://api.github.test", token="gh-token")

    assert captured[0][0] == "GET"
    assert captured[0][1] == "https://api.github.test"
    assert captured[0][2]["headers"]["Authorization"] == "Bearer gh-token"


def test_http_request_uses_raw_token_for_custom_auth_header(monkeypatch):
    captured = []

    def request(method, url, **kwargs):
        captured.append(kwargs["headers"])
        return FakeResponse()

    monkeypatch.setattr("requests.request", request)

    http_client.http_request(
        "https://llm.test",
        token="llm-token",
        auth_header="apiKey",
    )

    headers_lower = {key.lower(): value for key, value in captured[0].items()}
    assert headers_lower["apikey"] == "llm-token"
    assert "authorization" not in headers_lower


def test_http_request_sends_json_body(monkeypatch):
    captured = []

    def request(method, url, **kwargs):
        captured.append(kwargs)
        return FakeResponse()

    monkeypatch.setattr("requests.request", request)

    http_client.http_request(
        "https://api.test",
        method="POST",
        data={"hello": "world"},
    )

    assert captured[0]["json"] == {"hello": "world"}
    assert captured[0]["headers"]["Content-Type"] == "application/json"


def test_http_request_wraps_request_errors(monkeypatch):
    def request(method, url, **kwargs):
        raise requests.RequestException("network error")

    monkeypatch.setattr("requests.request", request)

    with pytest.raises(RuntimeError, match="failed to send request"):
        http_client.http_request("https://api.test")


@pytest.mark.parametrize(
    "auth_header",
    ["Bad\nHeader", "Bad Header", "Bad\tHeader", "Bad\x00Header", None],
)
def test_http_request_rejects_invalid_auth_header(auth_header):
    with pytest.raises(ValueError):
        http_client.http_request(
            "https://api.test",
            token="token",
            auth_header=auth_header,
        )


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


def test_review_diff_raises_on_api_error(monkeypatch):
    monkeypatch.setattr(
        reviewer,
        "http_request",
        lambda *args, **kwargs: (401, '{"error":"invalid key"}'),
    )

    with pytest.raises(ValueError, match="Review API request failed"):
        reviewer.review_diff("https://api.test", "key", "model", "diff", debug=False)
