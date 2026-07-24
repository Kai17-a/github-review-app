"""レビュー対象の diff の取得."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Mapping
from typing import TextIO

from .config import is_github_actions, load_github_config
from .github_client import GitHubClient


class DiffError(RuntimeError):
    """diff 取得の失敗."""


def truncate_diff(diff: str, max_chars: int) -> str:
    """LLM の入力上限に収まるよう diff を切り詰める."""
    if max_chars <= 0:
        raise ValueError(f"max_chars must be positive: {max_chars}")
    if len(diff) <= max_chars:
        return diff
    return (
        f"{diff[:max_chars]}\n\n"
        f"... diff truncated at {max_chars} characters "
        "to fit the review limit.\n"
    )


def read_stdin_diff(stream: TextIO = sys.stdin) -> str | None:
    """標準入力に diff がパイプされていれば返す."""
    if stream.isatty():
        return None
    data = stream.read()
    return data if data.strip() else None


def read_local_diff(env: Mapping[str, str] = os.environ) -> str:
    """ローカルリポジトリで git diff を実行して diff を取得する."""
    base = env.get("REVIEW_BASE", "HEAD")
    head = env.get("REVIEW_HEAD", "")
    cmd = ["git", "diff", "--no-color", base]
    if head:
        cmd.append(head)
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise DiffError("git command not found") from exc
    except subprocess.CalledProcessError as exc:
        message = (exc.stderr or str(exc)).strip()
        raise DiffError(f"git diff failed: {message}") from exc
    return result.stdout


def resolve_diff(
    *,
    env: Mapping[str, str] = os.environ,
    stream: TextIO = sys.stdin,
    github_client: GitHubClient | None = None,
) -> str:
    """diff の取得元を優先順位付きで解決する.

    1. 標準入力（パイプされた diff）
    2. GitHub Actions 上なら GitHub API から PR の差分を取得
    3. ローカルの git diff
    """
    stdin_diff = read_stdin_diff(stream)
    if stdin_diff is not None:
        return stdin_diff
    if is_github_actions(env):
        client = github_client or GitHubClient(load_github_config(env))
        return client.fetch_pull_request_diff()
    return read_local_diff(env)
