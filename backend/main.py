"""FastAPI application and optional team-router integration."""
from __future__ import annotations
from contextlib import asynccontextmanager
import importlib
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config, db
from .api_core import router as core_router
from .models import ApiError

OPTIONAL_ROUTERS = (
    ("backend.ingestion.api_ingest", "router"),
    ("backend.sankey", "router"),
    ("backend.budget.api_budget", "router"),
    ("backend.assistant.api_assistant", "router"),
)

@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield

app = FastAPI(title="Where Did My Money Go?", lifespan=lifespan)

@app.exception_handler(ApiError)
async def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content={"error": {"code": exc.code, "message": exc.message}})

@app.exception_handler(RequestValidationError)
async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(x) for x in first.get("loc", ()) if x not in ("query", "path", "body"))
    message = f"invalid {field}" if field else "invalid request"
    return JSONResponse(status_code=422, content={"error": {"code": "VALIDATION_ERROR", "message": message}})

app.include_router(core_router, prefix=config.API_PREFIX)
for module_name, attr in OPTIONAL_ROUTERS:
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name == module_name or module_name.startswith(f"{exc.name}."):
            continue
        raise
    app.include_router(getattr(module, attr), prefix=config.API_PREFIX)

# Static content is deliberately mounted after all API routers.
frontend_dir = Path(config.ROOT_DIR) / "frontend"
if frontend_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
