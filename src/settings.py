import json
import os


def get_env(name: str) -> str:
    """必須の環境変数を読み込む。

    Args:
        name: 環境変数名。

    Returns:
        環境変数の値。

    Raises:
        RuntimeError: 環境変数が未設定または空の場合。
    """
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set.")
    return value


def get_api_settings() -> tuple[str, str]:
    """環境変数から LLM API 設定を読み込む。

    Returns:
        chat completions endpoint URL と API key のタプル。

    Raises:
        RuntimeError: 必須の LLM 設定が不足している場合。
    """
    base_url = get_env("LLM_API_BASE_URL")
    api_key = get_env("LLM_API_KEY")
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    return endpoint, api_key


def get_github_settings() -> dict:
    """環境変数または event payload から GitHub API 設定を読み込む。

    Returns:
        token、repository、API URL、pull request 番号を含む辞書。

    Raises:
        RuntimeError: 必須の GitHub 設定または pull request 情報が不足している場合。
        ValueError: pull request 番号が整数ではない場合。
        json.JSONDecodeError: GitHub event payload が invalid JSON の場合。
    """
    token = get_env("GITHUB_TOKEN")
    repository = get_env("GITHUB_REPOSITORY")
    api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    pr_number = os.environ.get("PR_NUMBER")
    if pr_number:
        pull_number = int(pr_number)
    else:
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        if not event_path:
            raise RuntimeError("PR_NUMBER or GITHUB_EVENT_PATH is not set.")
        with open(event_path, "r", encoding="utf-8") as fh:
            event = json.load(fh)
        pull_request = event.get("pull_request")
        if not isinstance(pull_request, dict):
            raise RuntimeError(
                "pull_request payload is missing from GITHUB_EVENT_PATH."
            )
        pull_number = int(pull_request["number"])
    return {
        "token": token,
        "repository": repository,
        "api_url": api_url,
        "pull_number": pull_number,
    }
