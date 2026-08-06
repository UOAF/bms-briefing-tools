from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .mission_context import build_context_with_llm, fallback_context
from .providers import ProviderRouter
from .workflow import JobStore, ROOT, bms_status, pyopencam_status, start_job


STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="UOAF BMS Briefing Tool")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

providers = ProviderRouter()
jobs = JobStore()


class ChatRequest(BaseModel):
    message: str
    form: dict[str, Any] = {}
    history: list[dict[str, str]] = []
    provider: str = "auto"


class ContextRequest(BaseModel):
    form: dict[str, Any]
    planner_text: str
    provider: str = "auto"


class WorkflowRequest(BaseModel):
    form: dict[str, Any]
    mission_context: dict[str, Any] | None = None


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
def status(prefix: str = "") -> dict[str, Any]:
    return {
        "providers": providers.status(),
        "pyopencam": pyopencam_status(),
        "bms": bms_status(prefix),
        "repo_root": str(ROOT),
        "skill": str(ROOT / "skills" / "bms-briefing-planner"),
    }


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict[str, Any]:
    system = (
        "You are the local UOAF BMS briefing assistant. Help the mission planner capture enough "
        "information to run the existing BMS briefing pipeline. Ask concise follow-up questions. "
        "Do not invent mission facts. If the user is ready, tell them to draft mission context or run the workflow."
    )
    messages = [{"role": "system", "content": system}]
    messages.extend(request.history[-12:])
    messages.append({"role": "user", "content": request.message})
    result = providers.chat(messages, requested=request.provider, temperature=0.3)
    return {"provider": result.provider, "message": result.text}


@app.post("/api/context")
def context(request: ContextRequest) -> dict[str, Any]:
    context_data, provider = build_context_with_llm(providers, request.form, request.planner_text, provider=request.provider)
    return {"provider": provider, "mission_context": context_data}


@app.post("/api/jobs")
def create_job(request: WorkflowRequest) -> dict[str, Any]:
    payload = dict(request.form)
    payload["mission_context"] = request.mission_context or fallback_context(request.form, request.form.get("planner_text", ""))
    job = start_job(jobs, payload)
    return {"job_id": job.id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job.id,
        "status": job.status,
        "logs": job.logs,
        "artifacts": job.artifacts,
        "error": job.error,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }
