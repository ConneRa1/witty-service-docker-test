from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.domain.errors import DomainError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=_status_code_for_domain_error(exc),
            content={"error": exc.to_payload().to_dict()},
        )


def _status_code_for_domain_error(exc: DomainError) -> int:
    code = exc.code
    if code.endswith("_NOT_FOUND"):
        return 404
    if code.endswith("_NOT_SUPPORTED"):
        return 400
    if code.endswith("_MISMATCH"):
        return 400
    if code.startswith("INVALID_"):
        return 409
    if code.endswith("_FAILED"):
        return 500
    return 400
