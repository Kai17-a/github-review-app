import os
import subprocess
import sys

from diff_reader import read_diff, truncate_diff
from github_client import submit_pr_review
from reviewer import build_review_body, review_diff
from settings import get_api_settings, get_github_settings

DEFAULT_MODEL = "preview/Kimi-K2.6"
DEFAULT_MAX_DIFF_CHARS = 12_000


def main() -> int:
    """レビュー処理の workflow を実行する。

    Returns:
        プロセスの終了コード。成功時または空 diff の場合は 0、
        ハンドリング済みの失敗時は 1。
    """
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
