# github-review-app

GitHub pull request の diff を LLM にレビューさせ、PR review comment として投稿する GitHub Actions 用スクリプトです。

## Settings

Repository secrets:

- `LLM_API_BASE_URL`: OpenAI-compatible API のベース URL
- `LLM_API_KEY`: LLM API key

Repository variables:

- `REVIEW_MODEL`: 使用するモデル名。未設定時は `preview/Kimi-K2.6`

The workflow also uses the default `GITHUB_TOKEN`.

## Use As A GitHub Action

Use this repository from another workflow with `uses`.

```yaml
name: AI Review

on:
  workflow_dispatch:
    inputs:
      pr_number:
        description: Pull request number to review
        required: true
        type: number

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write

    steps:
      - uses: actions/checkout@v4

      - uses: your-org/github-review-app@v1
        with:
          pr-number: ${{ inputs.pr_number }}
          llm-api-base-url: ${{ secrets.LLM_API_BASE_URL }}
          llm-api-key: ${{ secrets.LLM_API_KEY }}
          review-model: ${{ vars.REVIEW_MODEL || 'preview/Kimi-K2.6' }}
```

Create a version tag to use `@v1`:

```bash
git tag v1
git push origin v1
```

## Run From This Repository

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
uv run --env-file .env python src/main.py
```

### Review Diff From Stdin

Reviews a diff passed through standard input:

```bash
git diff main...HEAD | uv run --env-file .env python src/main.py
```
