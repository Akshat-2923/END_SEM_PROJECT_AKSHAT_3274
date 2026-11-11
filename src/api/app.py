"""FastAPI application factory, middleware configuration, and error handling."""

import logging
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.aoi_validation import AOIValidationError
from src.api.routers import analyses, aois, artifacts, auth, health
from src.reporting import ReportingError

logger = logging.getLogger("dhara_scope.api")


def create_app() -> FastAPI:
    """Create and configure the DharaScope FastAPI application instance."""
    app = FastAPI(
        title="DharaScope API",
        description=(
            "Enterprise-grade satellite-based river surface water dynamics platform. "
            "Exposes multi-temporal Sentinel-2 spectral indices, NDWI water classification, "
            "categorical change detection, PostGIS geographical AOI boundaries, "
            "and publication-grade reporting endpoints."
        ),
        version="2.2.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # 1. Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Register API Routers
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(aois.router)
    app.include_router(analyses.router)
    app.include_router(artifacts.router)

    # 3. Custom Exception Handlers (Standardized & Sanitized Error Responses)
    @app.exception_handler(AOIValidationError)
    async def aoi_validation_exception_handler(request: Request, exc: AOIValidationError):
        logger.warning("AOI Validation Error on %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "AOIValidationError",
                "detail": str(exc),
                "status_code": status.HTTP_400_BAD_REQUEST,
            },
        )

    @app.exception_handler(ReportingError)
    async def reporting_exception_handler(request: Request, exc: ReportingError):
        logger.warning("Reporting Error on %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "ReportingError",
                "detail": str(exc),
                "status_code": status.HTTP_400_BAD_REQUEST,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.info("Request payload validation error on %s: %s", request.url.path, exc)
        # Format field errors cleanly
        error_details = []
        for err in exc.errors():
            loc = " -> ".join(str(item) for item in err.get("loc", []))
            msg = err.get("msg", "Invalid value")
            error_details.append(f"{loc}: {msg}")

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "error": "RequestValidationError",
                "detail": "; ".join(error_details) if error_details else str(exc),
                "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        headers = getattr(exc, "headers", None)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTPException",
                "detail": exc.detail,
                "status_code": exc.status_code,
            },
            headers=headers,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Log complete stack trace internally for developers
        logger.exception("Unhandled internal exception on %s: %s", request.url.path, exc)
        # Return strictly sanitized error envelope to client (never expose internal paths or secrets!)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "detail": "An internal server error occurred while processing the request. Please contact the administrator.",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            },
        )

    return app
