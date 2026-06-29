import pytest
import requests

import github_client

from helpers import FakeResponse


def test_github_request_uses_bearer_token(monkeypatch):
    captured = []

    def request(method, url, **kwargs):
        captured.append((method, url, kwargs))
        return FakeResponse()

    monkeypatch.setattr("requests.request", request)

    github_client.github_request("https://api.github.test", token="gh-token")

    assert captured[0][0] == "GET"
    assert captured[0][1] == "https://api.github.test"
    assert captured[0][2]["headers"]["Authorization"] == "Bearer gh-token"
    assert captured[0][2]["headers"]["Accept"] == "application/vnd.github+json"


def test_github_request_sends_json_body(monkeypatch):
    captured = []

    def request(method, url, **kwargs):
        captured.append(kwargs)
        return FakeResponse()

    monkeypatch.setattr("requests.request", request)

    github_client.github_request(
        "https://api.github.test",
        method="POST",
        token="gh-token",
        data={"hello": "world"},
    )

    assert captured[0]["json"] == {"hello": "world"}
    assert captured[0]["headers"]["Content-Type"] == "application/json"


def test_github_request_wraps_request_errors(monkeypatch):
    def request(method, url, **kwargs):
        raise requests.RequestException("network error")

    monkeypatch.setattr("requests.request", request)

    with pytest.raises(RuntimeError, match="failed to send GitHub request"):
        github_client.github_request("https://api.github.test", token="gh-token")
