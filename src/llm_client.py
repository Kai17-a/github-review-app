import requests


def llm_request(
    url: str,
    *,
    api_key: str,
    data: dict,
) -> tuple[int, str]:
    """設定済みの LLM API に chat completion リクエストを送信する。

    Args:
        url: 完全な LLM endpoint URL。
        api_key: `apiKey` ヘッダーで送信する API key。
        data: LLM API に送る JSON payload。

    Returns:
        HTTP status code と response body text のタプル。

    Raises:
        RuntimeError: レスポンス受信前にリクエストが失敗した場合。
    """
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "apiKey": api_key,
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=data,
        )
        return response.status_code, response.text
    except requests.RequestException as exc:
        raise RuntimeError(f"failed to send LLM request: {exc}") from exc
