"""コマンドラインエントリーポイント."""

from __future__ import annotations

import sys

from .config import is_github_actions, load_app_config, load_github_config
from .diff import resolve_diff, truncate_diff
from .github_client import GitHubClient
from .llm_client import ReviewClient

REVIEW_HEADER = "<!-- ai-review -->"


def build_review_body(review: str) -> str:
    """PR に投稿するレビュー本文を組み立てる."""
    return f"{REVIEW_HEADER}\n## AI Review\n\n{review}\n"


def run() -> None:
    """diff の取得からレビュー投稿までを一気通貫で実行する."""
    diff = resolve_diff()
    if not diff.strip():
        print(
            "レビュー対象の差分がありません。スキップします。", file=sys.stderr
        )
        return

    config = load_app_config()
    review = ReviewClient(config.llm).review(
        truncate_diff(diff, config.max_diff_chars),
        debug=config.debug,
    )
    body = build_review_body(review)
    print(body)

    if is_github_actions():
        GitHubClient(load_github_config()).create_review(body)
        print("レビューコメントを投稿しました。", file=sys.stderr)


def main() -> int:
    """CLI エントリーポイント. 失敗時は 1 を返す."""
    try:
        run()
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
