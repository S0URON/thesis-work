"""REST API routes."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..utils.file_utils import get_recent_outputs, get_recent_reports

router = APIRouter(prefix="/api")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None


class ClearSessionRequest(BaseModel):
    session_id: str = Field(..., min_length=1)


@router.post("/chat")
async def chat(request: Request, body: ChatRequest):
    chat_service = getattr(request.app.state, "chat_service", None)
    if not chat_service:
        raise HTTPException(status_code=503, detail="Service not ready")

    sid = chat_service.store.ensure_session(body.session_id)
    outcome = await chat_service.process_turn(sid, body.message)
    return {"session_id": sid, **outcome.result.model_dump()}


@router.post("/session/clear")
async def clear_session(request: Request, body: ClearSessionRequest):
    chat_service = getattr(request.app.state, "chat_service", None)
    if not chat_service:
        raise HTTPException(status_code=503, detail="Service not ready")

    chat_service.clear_session(body.session_id)
    return {"ok": True}


@router.get("/reports")
async def list_reports():
    paths = get_recent_reports()
    return {"reports": [str(p) for p in paths]}


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
