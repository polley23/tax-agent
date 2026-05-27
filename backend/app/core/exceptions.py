"""Domain-specific exceptions and global FastAPI error handlers."""

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


# ---------------------------------------------------------------------------
# Domain exceptions — raised by services / engine layers
# ---------------------------------------------------------------------------

class TaxAgentError(Exception):
    """Base exception for all tax-agent domain errors."""

    default_message: str = "An internal error occurred"

    def __init__(self, message: str | None = None, *, code: str | None = None):
        self.message = message or self.default_message
        self.code = code or self.__class__.__name__
        super().__init__(self.message)


class TaxRuleNotFound(TaxAgentError):
    """Raised when a tax rule or rule-pack for the requested financial year is missing."""
    default_message = "Tax rule not found"


class UnsupportedFinancialYear(TaxAgentError):
    """Raised when the financial year has no loaded rule-pack."""
    default_message = "Financial year not supported"


class DocumentProcessingError(TaxAgentError):
    """Raised when document parsing / extraction fails."""
    default_message = "Document processing failed"


class CalculationError(TaxAgentError):
    """Raised when the deterministic tax engine encounters an unexpected state."""
    default_message = "Tax calculation error"


class DataPurgeError(TaxAgentError):
    """Raised when data purging fails."""
    default_message = "Data purge failed"


# ---------------------------------------------------------------------------
# Global exception handlers — mounted on FastAPI app
# ---------------------------------------------------------------------------

async def http_exception_handler(_: Request, exception: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exception.status_code,
        content={"detail": exception.detail, "code": "HTTPError"},
    )


async def domain_exception_handler(_request: Request, exception: TaxAgentError) -> JSONResponse:
    status_map = {
        TaxRuleNotFound: status.HTTP_404_NOT_FOUND,
        UnsupportedFinancialYear: status.HTTP_422_UNPROCESSABLE_ENTITY,
        DocumentProcessingError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        CalculationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        DataPurgeError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    code = status_map.get(type(exception), status.HTTP_500_INTERNAL_SERVER_ERROR)
    return JSONResponse(
        status_code=code,
        content={"detail": exception.message, "code": exception.code},
    )


async def validation_exception_handler(_request: Request, exception: RequestValidationError | ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exception), "code": "ValidationError"},
    )


def register_exception_handlers(app):
    """Mount all global exception handlers on the FastAPI instance."""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(TaxAgentError, domain_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
