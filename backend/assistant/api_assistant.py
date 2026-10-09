from __future__ import annotations

from typing import Any

from backend.assistant.assistant import answer_question

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


def query_assistant(payload: dict[str, Any]) -> dict:
    if not isinstance(payload, dict):
        raise _validation_error("request body must be an object")
    question = payload.get("question")
    if not isinstance(question, str) or not question.strip():
        raise _validation_error("question is required")
    if len(question) > 500:
        raise _validation_error("question must be 500 characters or fewer")
    return answer_question(question.strip())


if router:
    router.add_api_route("/assistant/query", query_assistant, methods=["POST"])
