import requests


def llm_request(
    url: str,
    *,
    api_key: str,
    data: dict,
) -> tuple[int, str]:
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
