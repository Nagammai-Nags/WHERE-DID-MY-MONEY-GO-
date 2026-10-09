from __future__ import annotations

from typing import Any

from backend.budget.budget import budget_status, validate_month

try:
    from fastapi import APIRouter
except ImportError:  # pragma: no cover - lets pure tests run before deps land.
    APIRouter = None

try:
    from backend.models import ApiError
except ImportError:  # pragma: no cover - replaced by M1's implementation.
    class ApiError(Exception):
        def __init__(self, status: int, code: str, message: str):
            self.status = status
            self.code = code
            self.message = message
            super().__init__(message)


router = APIRouter() if APIRouter else None


def _validation_error(message: str) -> ApiError:
    return ApiError(422, "VALIDATION_ERROR", message)


def _validate_limit_minor(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise _validation_error("limit_minor must be an integer")
    if value < 100:
        raise _validation_error("limit_minor must be at least 100")
    return value


def _validate_optional_month(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return validate_month(value)
    except ValueError as exc:
        raise _validation_error(str(exc)) from exc


def get_budget(month: str | None = None) -> dict:
    try:
        month = _validate_optional_month(month)
    except ApiError:
        raise
    return budget_status(month)


def put_budget(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise _validation_error("request body must be an object")

    month = _validate_optional_month(payload.get("month"))
    limit_minor = _validate_limit_minor(payload.get("limit_minor"))

    from backend import analytics, repo

    if month is None:
        month = analytics.reference_month()
    repo.set_budget(month, limit_minor)
    return budget_status(month)


if router:
    router.add_api_route("/budget", get_budget, methods=["GET"])
    router.add_api_route("/budget", put_budget, methods=["PUT"])
