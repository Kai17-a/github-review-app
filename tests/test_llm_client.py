import pytest
import requests

import llm_client

from helpers import FakeResponse


def test_llm_request_uses_api_key_header(monkeypatch):
    captured = []

    def post(url, **kwargs):
        captured.append(kwargs["headers"])
        return FakeResponse()

    monkeypatch.setattr("requests.post", post)

    llm_client.llm_request(
        "https://llm.test",
        api_key="llm-token",
        data={"hello": "world"},
    )

    headers_lower = {key.lower(): value for key, value in captured[0].items()}
    assert headers_lower["apikey"] == "llm-token"
    assert "authorization" not in headers_lower
    assert captured[0]["Accept"] == "application/json"


def test_llm_request_sends_json_body(monkeypatch):
    captured = []

    def post(url, **kwargs):
        captured.append(kwargs)
        return FakeResponse()

    monkeypatch.setattr("requests.post", post)

    llm_client.llm_request(
        "https://llm.test",
        api_key="llm-token",
        data={"hello": "world"},
    )

    assert captured[0]["json"] == {"hello": "world"}
    assert captured[0]["headers"]["Content-Type"] == "application/json"


def test_llm_request_wraps_request_errors(monkeypatch):
    def post(url, **kwargs):
        raise requests.RequestException("network error")

    monkeypatch.setattr("requests.post", post)

    with pytest.raises(RuntimeError, match="failed to send LLM request"):
        llm_client.llm_request("https://llm.test", api_key="key", data={})
