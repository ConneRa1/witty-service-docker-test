from typing import Any

from pydantic import BaseModel


class ValidationResult(BaseModel):
    ok: bool
    error_code: str | None = None
    message: str | None = None


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str
    details: dict[str, Any] | None = None
