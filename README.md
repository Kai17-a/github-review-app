# GitHub Review App

OpenAI-compatible chat completions API を使って、GitHub Pull Request の差分を自動レビューするツールです。

Pull Request が作成または更新されると、GitHub Actions から `main.py` が実行され、PR の差分を LLM に渡してレビュー結果を PR review comment として投稿します。

## Features

- GitHub Pull Request の変更ファイルから diff を取得
- OpenAI-compatible API の `/chat/completions` にレビューを依頼
- 日本語でレビューコメントを生成
- 各指摘に「修正前のコード」と「推奨する修正後のコード」を含める
- GitHub Actions 上では PR に review comment を投稿
- ローカル実行時はレビュー本文を標準出力に表示

## Requirements

- Python 3.12+
- GitHub Actions
- OpenAI-compatible chat completions endpoint

HTTP request には `requests` を使用します。GitHub Actions では workflow 内で `requests` をインストールします。

## GitHub Actions Setup

`.github/workflows/review.yaml` により、次のタイミングでレビューが実行されます。

- Pull Request opened
- Pull Request synchronize

GitHub の repository settings で以下を設定してください。

### Repository Secrets

`Settings` -> `Secrets and variables` -> `Actions` -> `Secrets` に以下を設定します。

| Name                | Description                                                     |
| ------------------- | --------------------------------------------------------------- |
| `SAKURA_AI_URL`     | OpenAI-compatible API の base URL。例: `https://example.com/v1` |
| `SAKURA_AI_API_KEY` | OpenAI-compatible API の API key                                |

### Repository Variables

`Settings` -> `Secrets and variables` -> `Actions` -> `Variables` に以下を設定できます。

| Name           | Default             | Description      |
| -------------- | ------------------- | ---------------- |
| `REVIEW_MODEL` | `qwen2.5-coder:14b` | 使用するモデル名 |

`REVIEW_MODEL` を設定しない場合は、workflow 側の default として `qwen2.5-coder:14b` が使われます。

### Automatically Provided Values

以下は GitHub Actions から自動的に渡されるため、GitHub の Secrets / Variables に手動設定する必要はありません。

| Name                | Source                             | Description                     |
| ------------------- | ---------------------------------- | ------------------------------- |
| `GITHUB_TOKEN`      | `secrets.GITHUB_TOKEN`             | PR 情報取得とレビュー投稿に使用 |
| `GITHUB_REPOSITORY` | GitHub Actions default env         | `owner/repo` 形式のリポジトリ名 |
| `PR_NUMBER`         | `github.event.pull_request.number` | レビュー対象 Pull Request 番号  |

workflow は `GITHUB_TOKEN` を使って PR にレビューを投稿します。`pull-requests: write` permission が必要です。

## Environment Variables

`main.py` は以下の環境変数を参照します。

| Name                | Required            | Description                                            |
| ------------------- | ------------------- | ------------------------------------------------------ |
| `SAKURA_AI_URL`     | Yes                 | OpenAI-compatible API の base URL                      |
| `SAKURA_AI_API_KEY` | Yes                 | API key                                                |
| `REVIEW_MODEL`      | No                  | 使用するモデル名                                       |
| `MAX_DIFF_CHARS`    | No                  | LLM に渡す diff の最大文字数。default: `12000`         |
| `REVIEW_DEBUG`      | No                  | `1` の場合、API request / response を stderr に出力    |
| `GITHUB_TOKEN`      | GitHub Actions only | PR 情報取得とレビュー投稿に使用                        |
| `GITHUB_REPOSITORY` | GitHub Actions only | `owner/repo` 形式のリポジトリ名                        |
| `PR_NUMBER`         | GitHub Actions only | レビュー対象 Pull Request 番号                         |
| `GITHUB_API_URL`    | No                  | GitHub API base URL。default: `https://api.github.com` |

## Local Usage

ローカルでは標準入力から diff を渡して実行できます。

```bash
git diff --no-color main...HEAD | \
  SAKURA_AI_URL="https://example.com/v1" \
  SAKURA_AI_API_KEY="your-api-key" \
  REVIEW_MODEL="qwen2.5-coder:14b" \
  python3 main.py
```

標準入力がない場合は、`REVIEW_BASE` と `REVIEW_HEAD` を使って `git diff` を実行します。

```bash
SAKURA_AI_URL="https://example.com/v1" \
SAKURA_AI_API_KEY="your-api-key" \
REVIEW_BASE="main" \
REVIEW_HEAD="HEAD" \
python3 main.py
```

## Review Format

生成されるレビューは日本語です。指摘がある場合、各項目は次の構成になります。

- 問題の要約
- 修正前のコード
- 推奨する修正後のコード
- なぜその修正が望ましいか

差分に問題が見当たらない場合は、その旨をコメントします。

## Notes

- 外部 fork からの Pull Request では、GitHub Actions の `pull_request` event から repository secrets を利用できない場合があります。
- 大きい diff は `MAX_DIFF_CHARS` の文字数で切り詰められます。
- 現在の実装は PR 全体への review comment を投稿します。ファイル行単位の inline comment はまだ実装していません。
