import re

import requests

_VALID_AUTH_HEADER = re.compile(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+")


def http_request(
    url: str,
    *,
    method: str = "GET",
    token: str | None = None,
    auth_header: str = "Authorization",
    data: dict | None = None,
    accept: str = "application/vnd.github+json",
) -> tuple[int, str]:
    headers = {"Accept": accept}
    if token:
        if not isinstance(auth_header, str) or not _VALID_AUTH_HEADER.fullmatch(
            auth_header
        ):
            raise ValueError(f"Invalid auth_header: {auth_header!r}")
        if auth_header == "Authorization":
            headers[auth_header] = f"Bearer {token}"
        else:
            headers[auth_header] = token
    if data is not None:
        headers["Content-Type"] = "application/json"

    try:
        response = requests.request(
            method,
            url,
            headers=headers,
            json=data,
        )
        return response.status_code, response.text
    except requests.RequestException as exc:
        raise RuntimeError(f"failed to send request: {exc}") from exc
