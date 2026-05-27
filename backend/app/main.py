"""FastAPI application factory — creates, configures, and returns the app instance."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from db.session import async_session_factory


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    setup_logging()
    settings = get_settings()
    settings.uploads_path.mkdir(exist_ok=True)
    yield
    # Shutdown — close connection pool
    await async_session_factory.dispose()


# -- Security headers middleware (always runs last / outermost) --

class SecurityHeadersMiddleware:
    """Add security-focused HTTP headers to every response."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                headers["X-Content-Type-Options"] = b"nosniff"
                headers["X-Frame-Options"] = b"DENY"
                headers["X-XSS-Protection"] = b"1; mode=block"
                headers["Strict-Transport-Security"] = b"max-age=63072000; includeSubDomains"
                message["headers"] = list(headers.items())
            await send(message)

        await self.app(scope, receive, send_with_headers)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Tax Agent Backend",
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # Security headers (outermost)
    app.add_middleware(SecurityHeadersMiddleware)

    # Trusted host guard
    if not settings.debug:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(api_router)

    # Exception handlers
    register_exception_handlers(app)

    return app


app = create_app()
