"""FastAPI application factory for the Intelligence Engine.

`create_app` builds and wires a fully configured application; `app` is the
default instance used by Uvicorn:

    uvicorn app.main:app --reload --port 8201

The factory keeps configuration explicit (settings are stored on
`app.state.settings` and injected into request handlers from there) and makes
environment-specific behaviour testable without import-time side effects — in
particular, the temporary debug routes are only mounted outside production.

Every unhandled failure is normalised into the common error contract
(docs/gestao/fundamentos/backlog.md, section 6.5): `AppError` subclasses map
straight to their `status_code`; FastAPI's own
`RequestValidationError`/`StarletteHTTPException` are translated into the same
shape; any other exception is logged with its traceback server-side but
surfaced to the caller as a generic `internal_error` — no stack trace ever
reaches the response body.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.analysis import router as analysis_router
from app.api.health import router as health_router
from app.api.intelligence import router as intelligence_router
from app.api.internal_debug import router as internal_debug_router
from app.api.moments import router as moments_router
from app.api.recommendations import router as recommendations_router
from app.api.scoring import router as scoring_router
from app.core.config import Settings, get_settings
from app.core.errors import AppError, InternalError, InvalidPayloadError, NotFoundError
from app.core.logging import configure_logging, get_logger


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build a configured FastAPI application.

    Passing `settings` is mainly for tests; in normal operation the cached
    `get_settings()` is used. Constructing `Settings` validates the
    environment, so an invalid configuration (e.g. an empty
    `INTERNAL_API_TOKEN` in production) raises `ConfigError` here, before the
    app is created.
    """
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    logger = get_logger()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "service_startup",
            extra={"app_env": settings.app_env, "service": settings.service_name},
        )
        yield

    app = FastAPI(
        title="Intelligence Engine",
        version=settings.service_version,
        description=(
            "ChartRex / MomentFlow Intelligence Engine — calcula scores, detecta "
            "oportunidades e recomenda acções de campanha a partir de payloads "
            "técnicos enviados pelo Backend Core."
        ),
        lifespan=lifespan,
    )
    app.state.settings = settings

    app.include_router(health_router)

    # Engine endpoints (IE-003 contracts). The request/response contracts are
    # live and reflected in OpenAPI; the engine logic lands in IE-004+ (until
    # then each route validates input and returns a normalised 501).
    app.include_router(analysis_router)
    app.include_router(scoring_router)
    app.include_router(recommendations_router)
    app.include_router(moments_router)
    app.include_router(intelligence_router)

    # Temporary diagnostic routes (app/api/internal_debug.py) exist only to
    # exercise auth and the error contract. They are never mounted in
    # production, mirroring the renderer's dev-only route gating.
    if settings.app_env != "production":
        app.include_router(internal_debug_router)

    _register_exception_handlers(app, settings, logger)
    return app


def _register_exception_handlers(app: FastAPI, settings: Settings, logger: logging.Logger) -> None:
    def error_response(exc: AppError) -> JSONResponse:
        body = exc.to_response_body(
            engine=settings.service_name, engine_version=settings.service_version
        )
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(AppError)
    def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        logger.warning("app_error", extra={"code": exc.code, "status_code": exc.status_code})
        return error_response(exc)

    @app.exception_handler(RequestValidationError)
    def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        # `jsonable_encoder` (FastAPI's own pattern) makes the error list
        # JSON-safe: custom-validator ValueErrors put the raw exception object
        # in each error's `ctx`, which a plain JSONResponse cannot serialise.
        # exc.errors() never includes our internal token (it is a header
        # consumed by a separate dependency, not a validated body/query field).
        errors = jsonable_encoder(exc.errors())
        logger.warning("invalid_payload", extra={"error_count": len(errors)})
        return error_response(InvalidPayloadError(details={"errors": errors}))

    @app.exception_handler(StarletteHTTPException)
    def handle_http_exception(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        # Map framework-raised HTTPExceptions onto the contract without
        # mislabelling client errors (e.g. 405) as internal failures.
        if exc.status_code == 404:
            return error_response(NotFoundError())
        logger.warning("http_exception", extra={"status_code": exc.status_code})
        if exc.status_code < 500:
            detail = (
                exc.detail if isinstance(exc.detail, str) else "Request could not be processed."
            )
            return error_response(InvalidPayloadError(detail, status_code=exc.status_code))
        return error_response(InternalError())

    @app.exception_handler(Exception)
    def handle_unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
        # Full traceback goes to the structured logger only; the client never
        # sees more than a generic message. `exc_info` is passed explicitly
        # (rather than relying on `logger.exception`'s implicit
        # `sys.exc_info()`) because by the time this handler runs the active
        # exception context may already have been cleared by Starlette.
        logger.error(
            "unhandled_error",
            exc_info=exc,
            extra={"exception_type": type(exc).__name__},
        )
        return error_response(InternalError())


app = create_app()
