import json
import sys

from llm_client import llm_request

SYSTEM_PROMPT = """\
あなたは経験豊富なコードレビュアーです。提供された git diff をレビューし、以下の観点でフィードバックしてください。
1. バグ・ロジックエラー
2. セキュリティ上の問題（インジェクション、秘密情報の露出、認証不備など）
3. コード品質・可読性
4. パフォーマンス上の懸念
5. エラーハンドリング・エッジケースの不足
6. テストカバレッジのギャップ

各指摘は、必ず次の構成で Markdown 形式で記述してください。
- 問題の要約
- 修正前のコード
- 推奨する修正後のコード
- なぜその修正が望ましいか

修正前・修正後は、実際の差分に近い短いコードブロックで比較できるようにしてください。
差分に問題が見当たらない場合は、その旨を明記してください。
簡潔かつ具体的に記述してください。
必ず日本語で回答してください。
"""

REVIEW_HEADER = "<!-- ai-review -->"


def extract_message_text(message: dict) -> str | None:
    """chat completion の message から assistant text を取り出す。

    Args:
        message: chat completion response 内の message object。

    Returns:
        assistant text が存在する場合はその文字列。存在しない場合は None。
    """
    fallback = message.get("reasoning_content") or message.get("reasoning")
    content = message.get("content")

    if isinstance(content, str) and content:
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict):
                text = part.get("text") or part.get("content")
                if isinstance(text, str):
                    parts.append(text)
        joined = "".join(parts)
        return joined or fallback
    if isinstance(content, dict):
        text = content.get("text") or content.get("content")
        if isinstance(text, str) and text:
            return text
    return fallback


def review_diff(endpoint: str, api_key: str, model: str, diff: str, debug: bool) -> str:
    """diff のレビューを LLM に依頼する。

    Args:
        endpoint: chat completions endpoint URL。
        api_key: LLM API key。
        model: 使用する model 名。
        diff: レビュー対象の diff 文字列。
        debug: request/response の debug 出力を行うかどうか。

    Returns:
        LLM が生成したレビュー本文。

    Raises:
        ValueError: LLM API が 2xx 以外の status を返した場合。
        RuntimeError: response に assistant text が含まれない場合。
        json.JSONDecodeError: response body が valid JSON ではない場合。
    """
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"```diff\n{diff}\n```"},
        ],
    }

    if debug:
        print(f"POST {endpoint}", file=sys.stderr)
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)

    status, response_body = llm_request(
        endpoint,
        api_key=api_key,
        data=payload,
    )

    if debug:
        print(f"status: {status}", file=sys.stderr)
        print(response_body, file=sys.stderr)

    if status < 200 or status >= 300:
        raise ValueError(
            f"Review API request failed with status {status}: {response_body}"
        )

    data = json.loads(response_body)
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("chat completion response did not include any choices")

    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise RuntimeError("chat completion response did not include a valid message")

    text = extract_message_text(message)
    if not text:
        raise RuntimeError(
            "chat completion response did not include any assistant text"
        )
    return text


def build_review_body(review: str) -> str:
    """PR review として投稿する Markdown 本文を組み立てる。

    Args:
        review: LLM が生成したレビュー本文。

    Returns:
        AI review marker と heading を含む Markdown 本文。
    """
    return f"{REVIEW_HEADER}\n## AI Review\n\n{review}\n"
