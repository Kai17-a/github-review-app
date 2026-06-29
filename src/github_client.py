import json
import urllib.parse

import requests


def github_request(
    url: str,
    *,
    method: str = "GET",
    token: str,
    data: dict | None = None,
) -> tuple[int, str]:
    """GitHub API に認証付きリクエストを送信する。

    Args:
        url: 完全な GitHub API URL。
        method: 使用する HTTP メソッド。
        token: Bearer token として送信する GitHub token。
        data: 任意の JSON payload。

    Returns:
        HTTP status code と response body text のタプル。

    Raises:
        RuntimeError: レスポンス受信前にリクエストが失敗した場合。
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"

    try:
        response = requests.request(
            method,
            url,
            headers=headers,
            json=data,
        )
        return response.status_code, response.text
    except requests.RequestException as exc:
        raise RuntimeError(f"failed to send GitHub request: {exc}") from exc


def fetch_pr_diff_files(settings: dict) -> str:
    """Pull request の file patch を取得し、diff 文字列として結合する。

    Args:
        settings: repository、API URL、token、pull request 番号を含む
            GitHub 設定。

    Returns:
        file patch から生成した改行区切りの diff 文字列。

    Raises:
        RuntimeError: GitHub API のレスポンス形式が想定外の場合。
        json.JSONDecodeError: GitHub response body が valid JSON ではない場合。
    """
    owner_repo = settings["repository"]
    api_url = settings["api_url"]
    token = settings["token"]
    pull_number = settings["pull_number"]

    patches = []
    page = 1
    while True:
        params = urllib.parse.urlencode({"per_page": 100, "page": page})
        url = f"{api_url}/repos/{owner_repo}/pulls/{pull_number}/files?{params}"
        _, body = github_request(url, token=token)
        files = json.loads(body)
        if not isinstance(files, list):
            raise RuntimeError("GitHub files API returned an unexpected payload.")
        if not files:
            break

        for item in files:
            if not isinstance(item, dict):
                continue
            filename = item.get("filename")
            patch = item.get("patch")
            status = item.get("status")
            if not filename or patch is None:
                continue

            old_name = "/dev/null" if status == "added" else f"a/{filename}"
            new_name = "/dev/null" if status == "removed" else f"b/{filename}"
            patches.append(f"--- {old_name}\n+++ {new_name}\n{patch}")

        if len(files) < 100:
            break
        page += 1

    return "\n".join(patches)


def submit_pr_review(settings: dict, body: str) -> None:
    """Pull request review comment を投稿する。

    Args:
        settings: repository、API URL、token、pull request 番号を含む
            GitHub 設定。
        body: 投稿する Markdown 形式のレビュー本文。

    Raises:
        RuntimeError: レスポンス受信前に GitHub リクエストが失敗した場合。
    """
    url = (
        f"{settings['api_url']}/repos/{settings['repository']}/pulls/"
        f"{settings['pull_number']}/reviews"
    )
    payload = {"body": body, "event": "COMMENT"}
    github_request(url, method="POST", token=settings["token"], data=payload)
