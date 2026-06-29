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

1. Open the repository on GitHub.
2. Go to `Actions`.
3. Select the review workflow.
4. Click `Run workflow`.
5. Enter the pull request number in `pr_number`.

## Run Locally

Review a local diff:

```bash
LLM_API_BASE_URL="https://example.com" \
LLM_API_KEY="..." \
uv run python main.py
```

Review a provided diff:

```bash
git diff main...HEAD | \
LLM_API_BASE_URL="https://example.com" \
LLM_API_KEY="..." \
uv run python main.py
```
