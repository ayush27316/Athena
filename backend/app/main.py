from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.models import (
    DuplicateResourceException,
    Message,
    NotFoundException,
    ValidationException,
)


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.exception_handler(NotFoundException)
async def not_found_handler(request: Request, exc: NotFoundException):
    detail = str(exc) or "Resource not found"
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=Message.fail(message=detail, errors=[detail]).model_dump(exclude_none=True),
    )


@app.exception_handler(DuplicateResourceException)
async def duplicate_resource_handler(request: Request, exc: DuplicateResourceException):
    detail = str(exc) if exc.args else "Resource already exists"
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=Message.fail(message=detail, errors=[detail]).model_dump(exclude_none=True),
    )


@app.exception_handler(ValidationException)
async def validation_handler(request: Request, exc: ValidationException):
    detail = str(exc) if exc.args else "Validation error"
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=Message.fail(message=detail, errors=[detail]).model_dump(exclude_none=True),
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for any unhandled exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=Message.fail(message="Internal Server Error").model_dump(exclude_none=True),
    )