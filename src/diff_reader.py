import os
import subprocess
import sys

from github_client import fetch_pr_diff_files
from settings import get_github_settings


def read_local_diff() -> str:
    base = os.environ.get("REVIEW_BASE", "HEAD")
    head = os.environ.get("REVIEW_HEAD")
    cmd = ["git", "diff", "--no-color", base]
    if head:
        cmd.append(head)
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout


def read_diff() -> str:
    if not sys.stdin.isatty():
        stdin_diff = sys.stdin.read()
        if stdin_diff.strip():
            return stdin_diff

    if os.environ.get("GITHUB_ACTIONS") == "true":
        return fetch_pr_diff_files(get_github_settings())

    return read_local_diff()


def truncate_diff(diff: str, max_chars: int) -> str:
    if len(diff) <= max_chars:
        return diff
    truncated = diff[:max_chars]
    return (
        f"{truncated}\n\n"
        f"... diff truncated at {max_chars} characters to fit the review limit.\n"
    )
