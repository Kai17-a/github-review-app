import json
import os


def get_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set.")
    return value


def get_api_settings() -> tuple[str, str]:
    base_url = get_env("LLM_API_BASE_URL")
    api_key = get_env("LLM_API_KEY")
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    return endpoint, api_key


def get_github_settings() -> dict:
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
