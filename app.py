from __future__ import annotations

import json
import threading
from contextlib import asynccontextmanager
from queue import Queue
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from ultraprint.logging import logger

from core.config import log_config
from core.pipeline.run_analysis import AnalysisConfig, run_analysis
from core.storage import (
    create_session,
    delete_session,
    get_session,
    init_db,
    list_sessions,
    save_run_error,
    save_run_result,
    set_config,
    set_regeneration_prompt,
    get_config,
    upsert_input,
    update_status,
)
from core.utils.schema_utils import model_to_dict


log = logger("llm_log", **log_config)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")


class SessionCreateRequest(BaseModel):
    title: Optional[str] = None


class ScriptInputRequest(BaseModel):
    title: Optional[str] = None
    raw_text: str


class RegenerationRequest(BaseModel):
    regeneration_prompt: str


class ConfigRequest(BaseModel):
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_iterations: Optional[int] = None
    reasoning_iterations: Optional[int] = None
    steps_pipeline: Optional[bool] = None
    reasoning_pipeline: Optional[bool] = None


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> Any:
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/sessions")
def api_create_session(payload: SessionCreateRequest) -> Dict[str, Any]:
    session_id = create_session(title=payload.title)
    log.info("Created session %s", session_id)
    return {"session_id": session_id}


@app.get("/api/sessions")
def api_list_sessions() -> Dict[str, Any]:
    sessions = []
    for item in list_sessions():
        snippet = (item.get("raw_text") or "").strip().replace("\n", " ")
        sessions.append(
            {
                "session_id": item.get("session_id"),
                "title": item.get("title"),
                "snippet": snippet[:60] + ("..." if len(snippet) > 60 else ""),
                "status": item.get("status"),
                "updated_at": item.get("updated_at"),
            }
        )
    return {"sessions": sessions}


@app.post("/api/sessions/{session_id}/input")
def api_set_input(session_id: str, payload: ScriptInputRequest) -> Dict[str, Any]:
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    upsert_input(session_id, payload.title, payload.raw_text)
    return {"ok": True}


@app.post("/api/sessions/{session_id}/regeneration")
def api_set_regeneration(session_id: str, payload: RegenerationRequest) -> Dict[str, Any]:
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    set_regeneration_prompt(session_id, payload.regeneration_prompt)
    return {"ok": True}


@app.post("/api/sessions/{session_id}/config")
def api_set_config(session_id: str, payload: ConfigRequest) -> Dict[str, Any]:
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    config_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    set_config(session_id, config_data)
    return {"ok": True}


@app.get("/api/sessions/{session_id}")
def api_get_session(session_id: str) -> Dict[str, Any]:
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.delete("/api/sessions/{session_id}")
def api_delete_session(session_id: str) -> Dict[str, Any]:
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    delete_session(session_id)
    return {"ok": True}


def _serialize_result(result) -> Dict[str, Any]:
    return {
        "iterations": result.iterations,
        "tokens_used": result.tokens_used,
        "beat_extraction": model_to_dict(result.beat_extraction),
        "emotion_analysis": model_to_dict(result.emotion_analysis),
        "engagement_analysis": model_to_dict(result.engagement_analysis),
        "improvement_plan": model_to_dict(result.improvement_plan),
        "report": model_to_dict(result.report),
        "validation": model_to_dict(result.validation),
    }


def _load_previous_report(session: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    raw = session.get("last_report_json")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def stream_analysis(session_id: str, mode: str) -> StreamingResponse:
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    raw_text = session.get("raw_text")
    if not raw_text:
        raise HTTPException(status_code=400, detail="No script input saved")

    regeneration_prompt = None
    previous_report = None
    if mode == "regenerate":
        regeneration_prompt = session.get("regeneration_prompt")
        previous_report = _load_previous_report(session)

    queue: Queue = Queue()

    def _progress_callback(event: Dict[str, Any]) -> None:
        queue.put({"event": "progress", "data": event})

    def _worker() -> None:
        update_status(session_id, "running")
        try:
            config_data = get_config(session_id) or {}
            config = AnalysisConfig(**config_data)
            result = run_analysis(
                raw_text=raw_text,
                title=session.get("title"),
                config=config,
                previous_report=previous_report,
                regeneration_prompt=regeneration_prompt,
                progress_callback=_progress_callback,
            )
            payload = _serialize_result(result)
            save_run_result(session_id, payload)
            queue.put({"event": "result", "data": payload})
        except Exception as exc:
            log.error("Analysis failed: %s", exc)
            save_run_error(session_id, str(exc))
            queue.put({"event": "error", "data": {"message": str(exc)}})
        finally:
            queue.put({"event": "done", "data": {}})

    threading.Thread(target=_worker, daemon=True).start()

    def _event_stream():
        while True:
            item = queue.get()
            event = item.get("event")
            data = item.get("data")
            if event == "done":
                yield "event: done\ndata: {}\n\n"
                break
            yield f"event: {event}\ndata: {json.dumps(data, ensure_ascii=True)}\n\n"

    return StreamingResponse(_event_stream(), media_type="text/event-stream")


@app.get("/api/sessions/{session_id}/stream")
def api_stream(session_id: str, mode: str = "analyze") -> StreamingResponse:
    return stream_analysis(session_id, mode)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)
