# github-review-app

GitHub pull request の diff を LLM にレビューさせ、PR review comment として投稿する GitHub Actions 用スクリプトです。

## Settings

Repository secrets:

- `LLM_API_BASE_URL`: OpenAI-compatible API のベース URL
- `LLM_API_KEY`: LLM API key

Repository variables:

- `REVIEW_MODEL`: 使用するモデル名。未設定時は `preview/Kimi-K2.6`

The workflow also uses the default `GITHUB_TOKEN`.

## Run From GitHub Actions

`.github/workflows/review.yaml` is triggered manually with `workflow_dispatch`.

The workflow requires these token permissions:

```yaml
permissions:
  contents: read
  pull-requests: write
```

1. Open the repository on GitHub.
2. Go to `Actions`.
3. Select the review workflow.
4. Click `Run workflow`.
5. Enter the pull request number in `pr_number`.

## Run Locally

### Prerequisites

- [uv](https://docs.astral.sh/uv/) is installed

Install dependencies:

```bash
uv sync
```

Create a local `.env` file. It is ignored by Git.

```bash
LLM_API_BASE_URL=https://example.com
LLM_API_KEY=sk-xxxxx
```

### Review Repository Changes

Automatically reviews the current Git diff in this repository:

```bash
uv run --env-file .env python main.py
```

### Review Diff From Stdin

Reviews a diff passed through standard input:

```bash
git diff main...HEAD | uv run --env-file .env python main.py
```
