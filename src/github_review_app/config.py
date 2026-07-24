"""環境変数から設定を読み込む."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass

from .prompts import DEFAULT_SYSTEM_PROMPT

DEFAULT_MODEL = "preview/Kimi-K2.6"
DEFAULT_MAX_DIFF_CHARS = 12_000
DEFAULT_GITHUB_API_URL = "https://api.github.com"
DEFAULT_LLM_TIMEOUT = 120.0
GITHUB_API_VERSION = "2022-11-28"


class ConfigError(RuntimeError):
    """設定値が不足・不正な場合のエラー."""


@dataclass(frozen=True)
class LLMConfig:
    """OpenAI 互換 API の接続設定."""

    base_url: str
    api_key: str
    model: str
    timeout: float
    system_prompt: str


@dataclass(frozen=True)
class GitHubConfig:
    """GitHub API の接続設定."""

    token: str
    repository: str
    pull_number: int
    api_url: str


@dataclass(frozen=True)
class AppConfig:
    """レビュー実行全体の設定."""

    llm: LLMConfig
    max_diff_chars: int
    debug: bool


def _require(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise ConfigError(f"environment variable {name} is not set")
    return value


def _parse_positive_int(raw: str | None, *, default: int, name: str) -> int:
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ConfigError(
            f"environment variable {name} must be an integer: {raw!r}"
        ) from None
    if value <= 0:
        raise ConfigError(
            f"environment variable {name} must be positive: {raw!r}"
        )
    return value


def _parse_positive_float(
    raw: str | None, *, default: float, name: str
) -> float:
    if raw is None or not raw.strip():
        return default
    try:
        value = float(raw)
    except ValueError:
        raise ConfigError(
            f"environment variable {name} must be a number: {raw!r}"
        ) from None
    if value <= 0:
        raise ConfigError(
            f"environment variable {name} must be positive: {raw!r}"
        )
    return value


def load_llm_config(env: Mapping[str, str] = os.environ) -> LLMConfig:
    """LLM 接続設定を環境変数から読み込む."""
    return LLMConfig(
        base_url=_require(env, "LLM_API_BASE_URL").rstrip("/"),
        api_key=_require(env, "LLM_API_KEY"),
        model=env.get("REVIEW_MODEL", "").strip() or DEFAULT_MODEL,
        timeout=_parse_positive_float(
            env.get("LLM_TIMEOUT"),
            default=DEFAULT_LLM_TIMEOUT,
            name="LLM_TIMEOUT",
        ),
        system_prompt=(
            env.get("REVIEW_SYSTEM_PROMPT", "").strip() or DEFAULT_SYSTEM_PROMPT
        ),
    )


def load_github_config(env: Mapping[str, str] = os.environ) -> GitHubConfig:
    """GitHub 接続設定を環境変数から読み込む."""
    api_url = (
        env.get("GITHUB_API_URL", "").strip() or DEFAULT_GITHUB_API_URL
    ).rstrip("/")
    return GitHubConfig(
        token=_require(env, "GITHUB_TOKEN"),
        repository=_require(env, "GITHUB_REPOSITORY"),
        pull_number=_resolve_pull_number(env),
        api_url=api_url,
    )


def _resolve_pull_number(env: Mapping[str, str]) -> int:
    raw = env.get("PR_NUMBER", "").strip()
    if raw:
        try:
            return int(raw)
        except ValueError:
            raise ConfigError(
                f"environment variable PR_NUMBER must be an integer: {raw!r}"
            ) from None

    event_path = env.get("GITHUB_EVENT_PATH", "").strip()
    if not event_path:
        raise ConfigError(
            "environment variable PR_NUMBER or GITHUB_EVENT_PATH is required"
        )
    try:
        with open(event_path, encoding="utf-8") as fh:
            event = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(
            f"failed to read GITHUB_EVENT_PATH ({event_path}): {exc}"
        ) from exc

    pull_request = event.get("pull_request")
    if not isinstance(pull_request, dict) or "number" not in pull_request:
        raise ConfigError("pull_request.number is missing in the event payload")
    return int(pull_request["number"])


def load_app_config(env: Mapping[str, str] = os.environ) -> AppConfig:
    """レビュー実行に必要な設定をまとめて読み込む."""
    return AppConfig(
        llm=load_llm_config(env),
        max_diff_chars=_parse_positive_int(
            env.get("MAX_DIFF_CHARS"),
            default=DEFAULT_MAX_DIFF_CHARS,
            name="MAX_DIFF_CHARS",
        ),
        debug=env.get("REVIEW_DEBUG") == "1",
    )


def is_github_actions(env: Mapping[str, str] = os.environ) -> bool:
    """GitHub Actions 上で実行されているかどうか."""
    return env.get("GITHUB_ACTIONS") == "true"
