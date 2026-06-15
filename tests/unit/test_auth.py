from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from witty_service.api import auth


class RequestStub:
    def __init__(self, method: str) -> None:
        self.method = method


def test_require_bearer_auth_skips_options() -> None:
    auth.require_bearer_auth(RequestStub("OPTIONS"), authorization=None)


@pytest.mark.parametrize(
    "authorization",
    [None, "Basic token", "Bearer ", "Bearer wrong-token"],
)
def test_require_bearer_auth_rejects_invalid_token(
    monkeypatch,
    authorization: str | None,
) -> None:
    monkeypatch.setattr(
        auth,
        "get_settings",
        lambda: SimpleNamespace(auth_token="expected-token"),
    )

    with pytest.raises(HTTPException) as exc_info:
        auth.require_bearer_auth(RequestStub("GET"), authorization=authorization)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Unauthorized"
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


def test_require_bearer_auth_accepts_expected_token(monkeypatch) -> None:
    monkeypatch.setattr(
        auth,
        "get_settings",
        lambda: SimpleNamespace(auth_token="expected-token"),
    )

    auth.require_bearer_auth(
        RequestStub("GET"),
        authorization="Bearer expected-token",
    )
