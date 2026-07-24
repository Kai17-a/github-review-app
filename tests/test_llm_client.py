"""llm_client モジュールのテスト."""

from types import SimpleNamespace

import openai
import pytest

from github_review_app.config import LLMConfig
from github_review_app.llm_client import ReviewClient, ReviewError

CONFIG = LLMConfig(
    base_url="https://llm.example.com/v1",
    api_key="test-key",
    model="test-model",
    timeout=30.0,
    system_prompt="テスト用システムプロンプト",
)


def make_completion(content, model_extra=None):
    message = SimpleNamespace(content=content, model_extra=model_extra)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeCompletions:
    def __init__(self, result=None, error=None):
        self._result = result
        self._error = error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return self._result


def make_client(result=None, error=None):
    completions = FakeCompletions(result=result, error=error)
    fake_openai = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    # fake_openai は OpenAI クライアントのダックタイプ代替
    client = ReviewClient(
        CONFIG,
        client=fake_openai,  # ty: ignore[invalid-argument-type]
    )
    return client, completions


class TestReview:
    def test_sends_system_prompt_and_diff(self):
        client, completions = make_client(result=make_completion("レビュー"))

        review = client.review("some diff")

        assert review == "レビュー"
        (call,) = completions.calls
        assert call["model"] == "test-model"
        system, user = call["messages"]
        assert system == {
            "role": "system",
            "content": "テスト用システムプロンプト",
        }
        assert user == {
            "role": "user",
            "content": "```diff\nsome diff\n```",
        }

    def test_wraps_openai_errors(self):
        client, _ = make_client(error=openai.OpenAIError("boom"))

        with pytest.raises(ReviewError, match="boom"):
            client.review("diff")

    def test_raises_when_no_choices(self):
        client, _ = make_client(result=SimpleNamespace(choices=[]))

        with pytest.raises(ReviewError, match="no choices"):
            client.review("diff")

    def test_raises_when_content_is_empty(self):
        client, _ = make_client(result=make_completion(""))

        with pytest.raises(ReviewError, match="no assistant text"):
            client.review("diff")

    def test_falls_back_to_reasoning_content(self):
        completion = make_completion(
            None, model_extra={"reasoning_content": "考察テキスト"}
        )
        client, _ = make_client(result=completion)

        assert client.review("diff") == "考察テキスト"

    def test_joins_content_part_list(self):
        completion = make_completion([{"text": "part1"}, {"text": "part2"}])
        client, _ = make_client(result=completion)

        assert client.review("diff") == "part1part2"

    def test_debug_prints_request_and_response(self, capsys):
        completion = make_completion("ok")
        completion.model_dump_json = lambda **kwargs: '{"debug": true}'
        client, _ = make_client(result=completion)

        client.review("diff", debug=True)

        err = capsys.readouterr().err
        assert "test-model" in err
        assert '{"debug": true}' in err
