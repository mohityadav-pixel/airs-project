"""Application error types and safe HTTP translation.

Error messages returned to clients never contain upstream URLs, tokens or
stack traces — those go to the structured log only.
"""
from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.core.logging_config import get_logger

logger = get_logger("airs.errors")


class AirsError(Exception):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "airs_error"
    public_message = "An unexpected error occurred."

    def __init__(self, public_message: str | None = None, *, detail: str | None = None):
        super().__init__(detail or public_message or self.public_message)
        if public_message:
            self.public_message = public_message
        self.detail = detail


class ProviderUnavailable(AirsError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "provider_unavailable"
    public_message = "An upstream data provider is currently unavailable."


class ProviderNotConfigured(AirsError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "provider_not_configured"
    public_message = "This data source is not configured on the server."


class DataUnavailable(AirsError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "data_unavailable"
    public_message = "No data is available for this request."


class ModelUnavailable(AirsError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "model_unavailable"
    public_message = "The prediction model is not available yet."


class AIUnavailable(AirsError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "ai_unavailable"
    public_message = "The AI service is unavailable."


class NotAuthorized(AirsError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "not_authorized"
    public_message = "You do not have permission to perform this action."


class InvalidRequest(AirsError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "invalid_request"
    public_message = "The request was invalid."


async def airs_error_handler(request: Request, exc: AirsError) -> JSONResponse:
    logger.warning(
        "handled_error",
        extra={"extra_fields": {"code": exc.code, "path": request.url.path,
                                 "detail": exc.detail}},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.public_message}},
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_error", extra={"extra_fields": {"path": request.url.path}})
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error",
                            "message": "An unexpected error occurred."}},
    )
