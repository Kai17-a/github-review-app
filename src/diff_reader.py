import os
import subprocess
import sys

from github_client import fetch_pr_diff_files
from settings import get_github_settings


def read_local_diff() -> str:
    """ローカルの Git working tree から diff を読み込む。

    Returns:
        `git diff --no-color` の出力。

    Raises:
        subprocess.CalledProcessError: git コマンドが失敗した場合。
    """
    base = os.environ.get("REVIEW_BASE", "HEAD")
    head = os.environ.get("REVIEW_HEAD")
    cmd = ["git", "diff", "--no-color", base]
    if head:
        cmd.append(head)
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout


def read_diff() -> str:
    """レビュー対象の diff を利用可能な入力元から読み込む。

    入力元の優先順位は、非空の標準入力、GitHub Actions 上での
    GitHub Pull Request Files API、ローカルの `git diff` の順。

    Returns:
        diff 文字列。

    Raises:
        RuntimeError: GitHub Actions 上で必要な GitHub 設定が不足している場合。
        subprocess.CalledProcessError: ローカルの git コマンドが失敗した場合。
    """
    if not sys.stdin.isatty():
        stdin_diff = sys.stdin.read()
        if stdin_diff.strip():
            return stdin_diff

    if os.environ.get("GITHUB_ACTIONS") == "true":
        return fetch_pr_diff_files(get_github_settings())

    return read_local_diff()


def truncate_diff(diff: str, max_chars: int) -> str:
    """diff を指定された最大文字数に切り詰める。

    Args:
        diff: 切り詰め対象の diff 文字列。
        max_chars: 保持する最大文字数。

    Returns:
        上限以内の場合は元の diff。上限を超える場合は、切り詰めた diff と
        注記を連結した文字列。
    """
    if len(diff) <= max_chars:
        return diff
    truncated = diff[:max_chars]
    return (
        f"{truncated}\n\n"
        f"... diff truncated at {max_chars} characters to fit the review limit.\n"
    )
