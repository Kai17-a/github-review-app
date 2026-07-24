# GitHub Review App

OpenAI 互換の chat completions API を使って、GitHub Pull Request の差分を自動レビューするツールです。

GitHub Actions から PR 番号を指定してワークフローを手動実行すると、PR の差分を LLM に渡してレビューを生成し、結果を PR のレビューコメントとして投稿します。

## Features

- GitHub Pull Request の変更ファイルから diff を取得（ページネーション対応）
- OpenAI 互換 API（OpenAI SDK）でレビューを生成
- 日本語でレビューコメントを生成
- 各指摘に「修正前のコード」と「推奨する修正後のコード」を含める
- GitHub Actions 上では PR にレビューコメントを投稿
- ローカル実行時はレビュー本文を標準出力に表示

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- OpenAI 互換の chat completions エンドポイント

## Project Structure

```
action.yml                      # GitHub Action 定義（他リポジトリから uses 可能）
main.py                         # エントリーポイント（github_review_app.cli の薄いラッパー）
src/github_review_app/
  cli.py                        # 全体のオーケストレーション
  config.py                     # 環境変数からの設定読み込み
  diff.py                       # diff の取得（stdin / GitHub API / ローカル git）
  github_client.py              # GitHub REST API クライアント
  llm_client.py                 # OpenAI 互換 API によるレビュー生成
  prompts.py                    # LLM へのプロンプト（デフォルトのシステムプロンプト）
tests/                          # pytest テスト
.github/workflows/review.yaml   # このリポジトリ用の手動実行ワークフロー（action.yml を利用）
.github/workflows/release.yaml  # リリースタグ push 時にメジャータグを更新するワークフロー
mise.toml                       # 開発用タスク定義
```

## GitHub Actions Setup

`.github/workflows/review.yaml` は `workflow_dispatch` トリガーのみで実行されます。
リポジトリの `Actions` タブから `AI Review` ワークフローを選び、レビュー対象の
Pull Request 番号を入力して `Run workflow` を実行してください。

事前に repository settings で以下を設定します。

### Repository Secrets

`Settings` -> `Secrets and variables` -> `Actions` -> `Secrets` に以下を設定します。

| Name               | Description                                                |
| ------------------ | ---------------------------------------------------------- |
| `LLM_API_BASE_URL` | OpenAI 互換 API の base URL。例: `https://example.com/v1`  |
| `LLM_API_KEY`      | OpenAI 互換 API の API key                                 |

### Repository Variables

`Settings` -> `Secrets and variables` -> `Actions` -> `Variables` に以下を設定できます。

| Name                   | Default                                    | Description                |
| ---------------------- | ------------------------------------------ | -------------------------- |
| `REVIEW_MODEL`         | `preview/Kimi-K2.6`                        | 使用するモデル名           |
| `REVIEW_SYSTEM_PROMPT` | `src/github_review_app/prompts.py` の内容 | レビュー用システムプロンプト |

### Automatically Provided Values

以下は GitHub Actions から自動的に渡されるため、手動設定は不要です。

| Name                | Source                     | Description                     |
| ------------------- | -------------------------- | ------------------------------- |
| `GITHUB_TOKEN`      | `secrets.GITHUB_TOKEN`     | PR 情報取得とレビュー投稿に使用 |
| `GITHUB_REPOSITORY` | GitHub Actions default env | `owner/repo` 形式のリポジトリ名 |
| `PR_NUMBER`         | workflow の入力値          | レビュー対象 Pull Request 番号  |

ワークフローは `GITHUB_TOKEN` を使って PR にレビューを投稿します。
`pull-requests: write` permission が必要です（ワークフロー内で付与済み）。

## 他のリポジトリの GitHub Actions から使う

このリポジトリは composite action（`action.yml`）として定義されているため、
別リポジトリのワークフローから `uses: Kai17-a/github-review-app@v1` のように指定して利用できます。

差分は GitHub API から取得するため、呼び出し側で `actions/checkout` を実行する必要はありません。

### 例: 手動実行で PR 番号を指定する場合

```yaml
name: AI Review

on:
  workflow_dispatch:
    inputs:
      pr_number:
        description: "レビュー対象の Pull Request 番号"
        required: true
        type: number

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - uses: Kai17-a/github-review-app@v1
        with:
          pr_number: ${{ inputs.pr_number }}
          github_token: ${{ secrets.GITHUB_TOKEN }}
          llm_api_base_url: ${{ secrets.LLM_API_BASE_URL }}
          llm_api_key: ${{ secrets.LLM_API_KEY }}
```

### 例: Pull Request の作成・更新時に自動実行する場合

`pull_request` イベントでは、PR 番号はイベントペイロードから自動取得されるため `pr_number` を省略できます。

```yaml
name: AI Review

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - uses: Kai17-a/github-review-app@v1
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          llm_api_base_url: ${{ secrets.LLM_API_BASE_URL }}
          llm_api_key: ${{ secrets.LLM_API_KEY }}
```

### Action Inputs

| Name                  | Required | Default             | Description                                       |
| --------------------- | -------- | ------------------- | ------------------------------------------------- |
| `github_token`        | Yes      | -                   | PR 情報取得とレビュー投稿に使う GitHub トークン   |
| `llm_api_base_url`    | Yes      | -                   | OpenAI 互換 API の base URL                       |
| `llm_api_key`         | Yes      | -                   | OpenAI 互換 API の API key                        |
| `pr_number`           | No       | イベントペイロードから取得 | レビュー対象の Pull Request 番号             |
| `repository`          | No       | 呼び出し元リポジトリ | `owner/repo` 形式の対象リポジトリ                 |
| `review_model`        | No       | `preview/Kimi-K2.6` | 使用するモデル名                                  |
| `review_system_prompt` | No      | デフォルトプロンプト | レビュー用システムプロンプト                      |
| `max_diff_chars`      | No       | `12000`             | LLM に渡す diff の最大文字数                      |
| `llm_timeout`         | No       | `120`               | LLM API のタイムアウト秒数                        |
| `review_debug`        | No       | -                   | `1` で API request / response をログ出力          |

呼び出し元のワークフローには `pull-requests: write` permission が必要です。

### バージョン指定について

`@v1` はメジャーバージョンのタグです。最新の開発版を使いたい場合は `@main` も指定できます。

## Release

`vX.Y.Z` 形式のタグを push すると、`.github/workflows/release.yaml` が
メジャーバージョンタグ（例: `v1`）をそのコミットへ自動的に付け替えます。

```bash
git tag v1.0.0
git push origin v1.0.0   # => v1 タグがこのコミットを指すよう自動更新される
```

利用側は `@v1` を指定しておけば、以降の v1 系リリースを自動的に追随します。

## Environment Variables

アプリケーションは以下の環境変数を参照します。

| Name                | Required            | Description                                            |
| ------------------- | ------------------- | ------------------------------------------------------ |
| `LLM_API_BASE_URL`  | Yes                 | OpenAI 互換 API の base URL                            |
| `LLM_API_KEY`       | Yes                 | API key                                                |
| `REVIEW_MODEL`      | No                  | 使用するモデル名。default: `preview/Kimi-K2.6`         |
| `REVIEW_SYSTEM_PROMPT` | No               | レビュー用システムプロンプト。default: `src/github_review_app/prompts.py` の内容 |
| `LLM_TIMEOUT`       | No                  | LLM API のタイムアウト秒数。default: `120`             |
| `MAX_DIFF_CHARS`    | No                  | LLM に渡す diff の最大文字数。default: `12000`         |
| `REVIEW_DEBUG`      | No                  | `1` の場合、API request / response を stderr に出力    |
| `GITHUB_TOKEN`      | GitHub Actions only | PR 情報取得とレビュー投稿に使用                        |
| `GITHUB_REPOSITORY` | GitHub Actions only | `owner/repo` 形式のリポジトリ名                        |
| `PR_NUMBER`         | GitHub Actions only | レビュー対象 Pull Request 番号                         |
| `GITHUB_API_URL`    | No                  | GitHub API base URL。default: `https://api.github.com` |
| `REVIEW_BASE`       | Local only          | ローカル実行時の diff 基準。default: `HEAD`            |
| `REVIEW_HEAD`       | Local only          | ローカル実行時の diff 先                               |

## Local Usage

事前に `uv sync` で依存関係をインストールしてください。

ローカルでは標準入力から diff を渡して実行できます。

```bash
git diff --no-color main...HEAD | \
  LLM_API_BASE_URL="https://example.com/v1" \
  LLM_API_KEY="your-api-key" \
  REVIEW_MODEL="preview/Kimi-K2.6" \
  uv run python main.py
```

標準入力がない場合は、`REVIEW_BASE` と `REVIEW_HEAD` を使って `git diff` を実行します。

```bash
LLM_API_BASE_URL="https://example.com/v1" \
LLM_API_KEY="your-api-key" \
REVIEW_BASE="main" \
REVIEW_HEAD="HEAD" \
uv run python main.py
```

ローカル実行時はレビュー本文が標準出力に表示され、PR への投稿は行われません。

## Review Format

生成されるレビューは日本語です。指摘がある場合、各項目は次の構成になります。

- 問題の要約
- 修正前のコード
- 推奨する修正後のコード
- なぜその修正が望ましいか

差分に問題が見当たらない場合は、その旨をコメントします。

## Development

[mise](https://mise.jdx.dev/) のタスクとして開発用コマンドを定義しています。

```bash
mise run sync            # 依存関係のインストール（dev 含む）
mise run format          # format
mise run lint            # lint（自動修正付き）
mise run test            # テスト
mise run typecheck       # 型チェック
mise run check           # 上記すべてを一括検証（CI 相当）
```

mise を使わない場合は、以下のコマンドを直接実行してください。

```bash
uv sync                  # 依存関係のインストール（dev 含む）
uv run pytest            # テスト
uv run ruff check .      # lint
uv run ruff format .     # format
uv run ty check          # 型チェック
```

## Notes

- 外部 fork からの Pull Request では、GitHub Actions から repository secrets を利用できない場合があります。
- 大きい diff は `MAX_DIFF_CHARS` の文字数で切り詰められます。
- バイナリファイルや差分が大きすぎるファイルは GitHub API が patch を返さないため、レビュー対象から除外されます。
- 現在の実装は PR 全体へのレビューコメントを投稿します。ファイル行単位の inline comment には対応していません。
