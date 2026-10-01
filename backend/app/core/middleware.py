"""Request timing, request IDs, security headers and consistent error responses."""
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger("app.requests")

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{elapsed_ms:.1f}ms"
        for k, v in _SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        if elapsed_ms > settings.SLOW_REQUEST_MS:
            logger.warning("slow request %s %s %.0fms [%s]", request.method, request.url.path, elapsed_ms, request_id)
        return response


def _plain_errors(exc: RequestValidationError) -> list[dict]:
    """Field errors as plain JSON. Pydantic's raw errors can hold exception objects (which can't be
    serialised) and echo the submitted value back (which could be a password), so keep only these."""
    return [{"loc": [str(p) for p in err.get("loc", [])], "msg": str(err.get("msg", "")).removeprefix("Value error, "),
             "type": str(err.get("type", ""))} for err in exc.errors()]


def _friendly_validation(exc: RequestValidationError) -> str:
    parts = []
    for err in exc.errors()[:3]:
        field = ".".join(str(p) for p in err.get("loc", []) if p not in ("body", "query", "path"))
        msg = str(err.get("msg", "is invalid")).removeprefix("Value error, ")
        parts.append(f"{field}: {msg}" if field else msg)
    return "; ".join(parts) or "Some of the submitted information is invalid."


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"detail": _friendly_validation(exc), "errors": _plain_errors(exc)})

    @app.exception_handler(IntegrityError)
    async def _integrity(request: Request, exc: IntegrityError):
        logger.warning("integrity error on %s %s: %s", request.method, request.url.path, exc.orig)
        return JSONResponse(status_code=409, content={
            "detail": "This conflicts with existing data (a duplicate or a missing linked record).",
        })

    @app.exception_handler(OperationalError)
    async def _db_unavailable(request: Request, exc: OperationalError):
        logger.error("database error on %s %s: %s", request.method, request.url.path, exc.orig)
        return JSONResponse(status_code=503, content={"detail": "The service is busy. Please try again in a moment."})

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        rid = getattr(request.state, "request_id", "-")
        logger.exception("unhandled error on %s %s [%s]", request.method, request.url.path, rid)
        return JSONResponse(status_code=500, content={
            "detail": "Something went wrong on our side. Please try again.",
            "request_id": rid,
        })
