import pytest


class FakeResponse:
    def __init__(self, body: bytes, content_type: str | None):
        self._body = body
        self.headers = {"content-type": content_type} if content_type else {}
        self._sent = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, size=-1):
        if self._sent:
            return b""
        self._sent = True
        return self._body


@pytest.fixture
def fake_urlopen():
    """Build a urlopen stand-in serving `body` once per call; optionally records requests."""
    def make(body: bytes, content_type: str | None = None, seen: list | None = None):
        def urlopen(request, timeout):
            if seen is not None:
                seen.append(request)
            return FakeResponse(body, content_type)
        return urlopen
    return make
