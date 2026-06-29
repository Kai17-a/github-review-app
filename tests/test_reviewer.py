import pytest

import reviewer


def test_review_diff_raises_on_api_error(monkeypatch):
    monkeypatch.setattr(
        reviewer,
        "llm_request",
        lambda *args, **kwargs: (401, '{"error":"invalid key"}'),
    )

    with pytest.raises(ValueError, match="Review API request failed"):
        reviewer.review_diff("https://api.test", "key", "model", "diff", debug=False)
