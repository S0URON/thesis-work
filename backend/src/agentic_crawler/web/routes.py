"""REST API routes."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..utils.file_utils import get_recent_outputs, get_recent_reports, read_report_file

router = APIRouter(prefix="/api")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None
    analysis_date: str | None = Field(
        None,
        max_length=128,
        description="Optional; shown as Executive Summary Analysis Date in reports. "
        "Server UTC time is used if omitted.",
    )


class ClearSessionRequest(BaseModel):
    session_id: str = Field(..., min_length=1)


@router.post("/chat")
async def chat(request: Request, body: ChatRequest):
    chat_service = getattr(request.app.state, "chat_service", None)
    if not chat_service:
        raise HTTPException(status_code=503, detail="Service not ready")

    sid = chat_service.store.ensure_session(body.session_id)
    outcome = await chat_service.process_turn(sid, body.message, analysis_date=body.analysis_date)
    return {"session_id": sid, **outcome.result.model_dump()}


@router.post("/session/clear")
async def clear_session(request: Request, body: ClearSessionRequest):
    chat_service = getattr(request.app.state, "chat_service", None)
    if not chat_service:
        raise HTTPException(status_code=503, detail="Service not ready")

    chat_service.clear_session(body.session_id)
    return {"ok": True}


@router.get("/reports")
async def list_reports(
    limit: int = Query(200, ge=1, le=500, description="Max number of reports to return"),
):
    paths = get_recent_reports(limit=limit)
    return {"reports": [str(p) for p in paths]}


@router.get("/reports/content")
async def get_report_content(
    name: str = Query(
        ...,
        min_length=1,
        max_length=512,
        description="Report basename (e.g. Website_Analysis_*.md)",
    ),
):
    """Return the contents of a saved report under the configured reports directory."""
    try:
        content, fmt = read_report_file(name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Report not found") from None
    return {
        "name": Path(name).name,
        "content": content,
        "format": fmt,
    }


@router.get("/outputs")
async def list_outputs():
    paths = get_recent_outputs()
    return {"outputs": [str(p) for p in paths]}


@router.get("/stats")
async def stats(request: Request):
    tracker = getattr(request.app.state, "tracker", None)
    cache = getattr(request.app.state, "cache", None)
    if tracker is None or cache is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    return {
        "execution": tracker.get_stats().model_dump(),
        "cache": cache.get_stats().model_dump(),
    }


@router.get("/health")
async def health(request: Request):
    ready = getattr(request.app.state, "chat_service", None) is not None
    return {"status": "ok" if ready else "starting", "ready": ready}
