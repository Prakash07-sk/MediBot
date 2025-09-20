
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi import status
from utils import ErrorResponse


def add_exception_handlers(app):
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        err = ErrorResponse(errors={"detail": exc.detail}, message=str(exc.detail))
        return JSONResponse(
            status_code=exc.status_code,
            content=err.dict(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # Convert validation errors to a field:message dict
        error_dict = {}
        for e in exc.errors():
            loc = ".".join(str(l) for l in e.get("loc", []))
            error_dict[loc] = e.get("msg", "Validation error")
        err = ErrorResponse(errors=error_dict, message="Validation failed")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=err.dict(),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        err = ErrorResponse(errors={"detail": str(exc)}, message="Internal server error")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=err.dict(),
        )
