"""Member 2 HTTP routes; mounted by Member 1 under /api/v1."""

from __future__ import annotations

from fastapi import APIRouter, Body

from .merchants import resolve_group, review_queue
from .pipeline import import_sample, import_text


router = APIRouter()


def _api_error(message: str):
    from backend.models import ApiError  # type: ignore
    return ApiError(422, "VALIDATION_ERROR", message)


@router.post("/imports")
def imports(payload: dict = Body(...)) -> dict:
    source_type, text = payload.get("source_type"), payload.get("text")
    if not isinstance(text, str) or len(text.encode("utf-8")) > 200 * 1024:
        raise _api_error("text must be a string up to 200 KB")
    return import_text(source_type, text)


@router.post("/imports/sample")
def imports_sample() -> dict:
    return import_sample()


@router.get("/merchants/review-queue")
def merchants_review_queue() -> dict:
    return {"items": review_queue()}


@router.post("/merchants/resolve")
def merchants_resolve(payload: dict = Body(...)) -> dict:
    group_key, display_name, category = payload.get("group_key"), payload.get("display_name"), payload.get("category")
    if not isinstance(group_key, str):
        raise _api_error("group_key is required")
    if not isinstance(display_name, str) or not display_name.strip() or len(display_name.strip()) > 50:
        raise _api_error("display_name must be 1 to 50 characters")
    from backend.models import CATEGORIES  # type: ignore
    if category not in CATEGORIES:
        raise _api_error("category must be a supported category")
    try:
        return resolve_group(group_key, display_name.strip(), category)
    except ValueError as exc:
        raise _api_error(str(exc)) from exc


@router.get("/merchants/aliases")
def merchants_aliases() -> dict:
    from backend import repo  # type: ignore
    return {"items": repo.list_aliases()}
