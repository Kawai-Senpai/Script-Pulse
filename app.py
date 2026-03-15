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
from core.services.normalizer import normalize_script_input
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
from core.utils.analysis_utils import build_token_usage
from core.utils.schema_utils import model_to_dict


log = logger("llm_log", **log_config)

DEFAULT_MODEL = "gpt-5.4::medium"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_ITERATIONS = 1
_MODEL_ALIAS_MAP = {
    "gpt-5.4": DEFAULT_MODEL,
    "openai/gpt-5.4": DEFAULT_MODEL,
    "claude-sonnet-4.5": "claude-sonnet-4.5",
    "anthropic/claude-sonnet-4.5": "claude-sonnet-4.5",
    "gemini-3.1-pro-preview": "gemini-3.1-pro-preview",
    "google/gemini-3.1-pro-preview": "gemini-3.1-pro-preview",
    "grok-4.1-fast": "grok-4.1-fast",
    "x-ai/grok-4.1-fast": "grok-4.1-fast",
}
for _effort in ("minimal", "low", "medium", "high"):
    _MODEL_ALIAS_MAP[f"openai/gpt-5.4::{_effort}"] = f"gpt-5.4::{_effort}"


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


def _coerce_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 1 else default


def _normalize_model_choice(value: Any) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        return DEFAULT_MODEL
    return _MODEL_ALIAS_MAP.get(cleaned, cleaned)


def _sanitize_session_config(config_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    config_data = config_data or {}
    return {
        "model": _normalize_model_choice(config_data.get("model")),
        "temperature": max(0.0, min(1.0, _coerce_float(config_data.get("temperature"), DEFAULT_TEMPERATURE))),
        "max_iterations": _coerce_int(config_data.get("max_iterations"), DEFAULT_MAX_ITERATIONS),
    }


def _build_runtime_config(config_data: Optional[Dict[str, Any]]) -> AnalysisConfig:
    clean = _sanitize_session_config(config_data)
    return AnalysisConfig(
        model=clean["model"],
        temperature=clean["temperature"],
        max_iterations=clean["max_iterations"],
        steps_pipeline=False,
        reasoning_pipeline=False,
    )


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

    config_data = _sanitize_session_config(payload.model_dump())
    set_config(session_id, config_data)
    return {"ok": True}


@app.get("/api/sessions/{session_id}")
def api_get_session(session_id: str) -> Dict[str, Any]:
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session["config"] = _sanitize_session_config(get_config(session_id))
    raw_text = session.get("raw_text")
    if raw_text:
        session["script_input"] = model_to_dict(
            normalize_script_input(raw_text, title=session.get("title"))
        )
    token_usage_raw = session.get("last_token_usage_json")
    if token_usage_raw:
        try:
            session["token_usage"] = json.loads(token_usage_raw)
        except Exception:
            session["token_usage"] = None
    else:
        session["token_usage"] = None
    return session


@app.delete("/api/sessions/{session_id}")
def api_delete_session(session_id: str) -> Dict[str, Any]:
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    delete_session(session_id)
    return {"ok": True}


def _serialize_result(result) -> Dict[str, Any]:
    token_usage = build_token_usage(result.step_details, result.tokens_used)
    return {
        "script_input": model_to_dict(result.script_input),
        "iterations": result.iterations,
        "tokens_used": result.tokens_used,
        "token_usage": token_usage,
        "beat_extraction": model_to_dict(result.beat_extraction),
        "emotion_analysis": model_to_dict(result.emotion_analysis),
        "engagement_analysis": model_to_dict(result.engagement_analysis),
        "improvement_plan": model_to_dict(result.improvement_plan),
        "report": model_to_dict(result.report),
        "validation": model_to_dict(result.validation) if result.validation else None,
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
            config = _build_runtime_config(get_config(session_id))
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
