class FakeResponse:
    status_code = 200
    text = "{}"

    def __init__(self, text: str = "{}", status_code: int = 200):
        self.text = text
        self.status_code = status_code
