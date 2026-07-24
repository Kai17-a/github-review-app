"""github-review-app のエントリーポイント.

実体は `github_review_app.cli` にある。`python main.py` で実行するための
薄いラッパー。
"""

from github_review_app.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
