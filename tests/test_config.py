"""config モジュールのテスト."""

import json

import pytest

from github_review_app.config import (
    DEFAULT_GITHUB_API_URL,
    DEFAULT_MAX_DIFF_CHARS,
    DEFAULT_MODEL,
    ConfigError,
    is_github_actions,
    load_app_config,
    load_github_config,
    load_llm_config,
)
from github_review_app.prompts import DEFAULT_SYSTEM_PROMPT

LLM_ENV = {
    "LLM_API_BASE_URL": "https://llm.example.com/v1",
    "LLM_API_KEY": "test-key",
}

GITHUB_ENV = {
    "GITHUB_TOKEN": "gh-token",
    "GITHUB_REPOSITORY": "owner/repo",
    "PR_NUMBER": "42",
}


class TestLoadLLMConfig:
    def test_loads_required_values(self):
        config = load_llm_config(LLM_ENV)

        assert config.base_url == "https://llm.example.com/v1"
        assert config.api_key == "test-key"
        assert config.model == DEFAULT_MODEL
        assert config.timeout > 0

    def test_strips_trailing_slash_from_base_url(self):
        config = load_llm_config(
            {**LLM_ENV, "LLM_API_BASE_URL": "https://a/v1/"}
        )

        assert config.base_url == "https://a/v1"

    def test_overrides_model_and_timeout(self):
        env = {
            **LLM_ENV,
            "REVIEW_MODEL": "custom-model",
            "LLM_TIMEOUT": "30",
        }

        config = load_llm_config(env)

        assert config.model == "custom-model"
        assert config.timeout == 30.0

    def test_uses_default_system_prompt(self):
        config = load_llm_config(LLM_ENV)

        assert config.system_prompt == DEFAULT_SYSTEM_PROMPT

    def test_overrides_system_prompt(self):
        env = {**LLM_ENV, "REVIEW_SYSTEM_PROMPT": "カスタムプロンプト"}

        config = load_llm_config(env)

        assert config.system_prompt == "カスタムプロンプト"

    def test_blank_system_prompt_falls_back_to_default(self):
        env = {**LLM_ENV, "REVIEW_SYSTEM_PROMPT": "  \n"}

        config = load_llm_config(env)

        assert config.system_prompt == DEFAULT_SYSTEM_PROMPT

    @pytest.mark.parametrize("missing", ["LLM_API_BASE_URL", "LLM_API_KEY"])
    def test_raises_when_required_value_is_missing(self, missing):
        env = {key: value for key, value in LLM_ENV.items() if key != missing}

        with pytest.raises(ConfigError, match=missing):
            load_llm_config(env)

    @pytest.mark.parametrize("value", ["abc", "-1", "0"])
    def test_raises_on_invalid_timeout(self, value):
        with pytest.raises(ConfigError, match="LLM_TIMEOUT"):
            load_llm_config({**LLM_ENV, "LLM_TIMEOUT": value})


class TestLoadGitHubConfig:
    def test_loads_values(self):
        config = load_github_config(GITHUB_ENV)

        assert config.token == "gh-token"
        assert config.repository == "owner/repo"
        assert config.pull_number == 42
        assert config.api_url == DEFAULT_GITHUB_API_URL

    def test_reads_pull_number_from_event_payload(self, tmp_path):
        event = {"pull_request": {"number": 7}}
        event_path = tmp_path / "event.json"
        event_path.write_text(json.dumps(event), encoding="utf-8")

        env = {
            key: value
            for key, value in GITHUB_ENV.items()
            if key != "PR_NUMBER"
        }
        config = load_github_config(
            {**env, "GITHUB_EVENT_PATH": str(event_path)}
        )

        assert config.pull_number == 7

    def test_raises_when_pull_number_is_not_an_integer(self):
        with pytest.raises(ConfigError, match="PR_NUMBER"):
            load_github_config({**GITHUB_ENV, "PR_NUMBER": "not-a-number"})

    def test_raises_without_pr_number_and_event_path(self):
        env = {
            key: value
            for key, value in GITHUB_ENV.items()
            if key != "PR_NUMBER"
        }

        with pytest.raises(ConfigError, match="GITHUB_EVENT_PATH"):
            load_github_config(env)

    def test_raises_on_event_payload_without_pull_request(self, tmp_path):
        event_path = tmp_path / "event.json"
        event_path.write_text("{}", encoding="utf-8")

        env = {
            key: value
            for key, value in GITHUB_ENV.items()
            if key != "PR_NUMBER"
        }
        with pytest.raises(ConfigError, match="pull_request"):
            load_github_config({**env, "GITHUB_EVENT_PATH": str(event_path)})


class TestLoadAppConfig:
    def test_defaults(self):
        config = load_app_config(LLM_ENV)

        assert config.max_diff_chars == DEFAULT_MAX_DIFF_CHARS
        assert config.debug is False

    def test_overrides(self):
        env = {**LLM_ENV, "MAX_DIFF_CHARS": "100", "REVIEW_DEBUG": "1"}

        config = load_app_config(env)

        assert config.max_diff_chars == 100
        assert config.debug is True

    @pytest.mark.parametrize("value", ["abc", "-5"])
    def test_raises_on_invalid_max_diff_chars(self, value):
        with pytest.raises(ConfigError, match="MAX_DIFF_CHARS"):
            load_app_config({**LLM_ENV, "MAX_DIFF_CHARS": value})


class TestIsGitHubActions:
    @pytest.mark.parametrize(
        ("env", "expected"),
        [
            ({"GITHUB_ACTIONS": "true"}, True),
            ({"GITHUB_ACTIONS": "false"}, False),
            ({}, False),
        ],
    )
    def test_detection(self, env, expected):
        assert is_github_actions(env) is expected
