import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

SYSTEM_PROMPT = """\
あなたは経験豊富なコードレビュアーです。提供された git diff をレビューし、以下の観点でフィードバックしてください。
1. バグ・ロジックエラー
2. セキュリティ上の問題（インジェクション、秘密情報の露出、認証不備など）
3. コード品質・可読性
4. パフォーマンス上の懸念
5. エラーハンドリング・エッジケースの不足
6. テストカバレッジのギャップ

各指摘は、必ず次の構成で Markdown 形式で記述してください。
- 問題の要約
- 修正前のコード
- 推奨する修正後のコード
- なぜその修正が望ましいか

修正前・修正後は、実際の差分に近い短いコードブロックで比較できるようにしてください。
差分に問題が見当たらない場合は、その旨を明記してください。
簡潔かつ具体的に記述してください。
必ず日本語で回答してください。
"""

DEFAULT_MODEL = "preview/Kimi-K2.6"
DEFAULT_MAX_DIFF_CHARS = 12_000
REVIEW_HEADER = "<!-- ai-review -->"


def http_request(
    url: str,
    *,
    method: str = "GET",
    token: str | None = None,
    auth_header: str = "Authorization",
    data: dict | None = None,
    accept: str = "application/vnd.github+json",
) -> tuple[int, str]:
    body = None
    headers = {"Accept": accept}
    if token:
        if (
            not auth_header
            or not auth_header.isascii()
            or any(char in auth_header for char in ":\r\n")
        ):
            raise ValueError(f"Invalid auth_header: {auth_header!r}")
        if auth_header == "Authorization":
            headers[auth_header] = f"Bearer {token}"
        else:
            headers[auth_header] = token
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"request failed with {exc.code}: {error_body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"failed to send request: {exc}") from exc


def get_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set.")
    return value


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


def fetch_pr_diff_files(settings: dict) -> str:
    owner_repo = settings["repository"]
    api_url = settings["api_url"]
    token = settings["token"]
    pull_number = settings["pull_number"]

    patches = []
    page = 1
    while True:
        params = urllib.parse.urlencode({"per_page": 100, "page": page})
        url = f"{api_url}/repos/{owner_repo}/pulls/{pull_number}/files?{params}"
        _, body = http_request(url, token=token)
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


def read_diff() -> str:
    if not sys.stdin.isatty():
        stdin_diff = sys.stdin.read()
        if stdin_diff:
            return stdin_diff

    if os.environ.get("GITHUB_ACTIONS") == "true":
        return fetch_pr_diff_files(get_github_settings())

    base = os.environ.get("REVIEW_BASE", "HEAD")
    head = os.environ.get("REVIEW_HEAD")
    cmd = ["git", "diff", "--no-color", base]
    if head:
        cmd.append(head)
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout


def truncate_diff(diff: str, max_chars: int) -> str:
    if len(diff) <= max_chars:
        return diff
    truncated = diff[:max_chars]
    return (
        f"{truncated}\n\n"
        f"... diff truncated at {max_chars} characters to fit the review limit.\n"
    )


def get_api_settings() -> tuple[str, str]:
    base_url = get_env("SAKURA_AI_URL")
    api_key = get_env("SAKURA_AI_API_KEY")
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    return endpoint, api_key


def extract_message_text(message: dict) -> str | None:
    fallback = message.get("reasoning_content") or message.get("reasoning")
    content = message.get("content")

    if isinstance(content, str) and content:
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict):
                text = part.get("text") or part.get("content")
                if isinstance(text, str):
                    parts.append(text)
        joined = "".join(parts)
        return joined or fallback
    if isinstance(content, dict):
        text = content.get("text") or content.get("content")
        if isinstance(text, str) and text:
            return text
    return fallback


def review_diff(endpoint: str, api_key: str, model: str, diff: str, debug: bool) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"```diff\n{diff}\n```"},
        ],
    }

    if debug:
        print(f"POST {endpoint}", file=sys.stderr)
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)

    status, response_body = http_request(
        endpoint,
        method="POST",
        token=api_key,
        auth_header="apiKey",
        data=payload,
        accept="application/json",
    )

    if debug:
        print(f"status: {status}", file=sys.stderr)
        print(response_body, file=sys.stderr)

    data = json.loads(response_body)
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("chat completion response did not include any choices")

    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise RuntimeError("chat completion response did not include a valid message")

    text = extract_message_text(message)
    if not text:
        raise RuntimeError(
            "chat completion response did not include any assistant text"
        )
    return text


def build_review_body(review: str) -> str:
    return f"{REVIEW_HEADER}\n## AI Review\n\n{review}\n"


def submit_pr_review(settings: dict, body: str) -> None:
    url = (
        f"{settings['api_url']}/repos/{settings['repository']}/pulls/"
        f"{settings['pull_number']}/reviews"
    )
    payload = {"body": body, "event": "COMMENT"}
    http_request(url, method="POST", token=settings["token"], data=payload)


def main() -> int:
    try:
        diff = read_diff()
    except subprocess.CalledProcessError as exc:
        print(exc.stderr or str(exc), file=sys.stderr)
        return exc.returncode or 1
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not diff.strip():
        print("Diff is empty. Skipping review.", file=sys.stderr)
        return 0

    try:
        endpoint, api_key = get_api_settings()
        model = os.environ.get("REVIEW_MODEL", DEFAULT_MODEL)
        max_diff_chars = int(os.environ.get("MAX_DIFF_CHARS", DEFAULT_MAX_DIFF_CHARS))
        debug = os.environ.get("REVIEW_DEBUG") == "1"
        review = review_diff(
            endpoint,
            api_key,
            model,
            truncate_diff(diff, max_diff_chars),
            debug,
        )
        body = build_review_body(review)
        print(body)
        if os.environ.get("GITHUB_ACTIONS") == "true":
            submit_pr_review(get_github_settings(), body)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
