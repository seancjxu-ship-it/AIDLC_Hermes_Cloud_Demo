from __future__ import annotations

import base64
import os
import secrets
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from aidlc.bus import RedisBus
from aidlc.models import RunRequest
from aidlc.settings import settings
from aidlc.skills import architecture_payload


STATIC = Path(__file__).resolve().parents[1] / "web"
app = FastAPI(title="AI-DLC Software Factory Demo", version="3.0.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.middleware("http")
async def basic_auth(request: Request, call_next):
    password = os.getenv("AIDLC_DEMO_PASSWORD", "")
    if not password or request.url.path == "/health":
        return await call_next(request)
    expected_user = os.getenv("AIDLC_DEMO_USERNAME", "demo")
    supplied_user = supplied_password = ""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Basic "):
        try:
            supplied_user, supplied_password = base64.b64decode(auth[6:]).decode().split(":", 1)
        except Exception:
            pass
    if not (
        secrets.compare_digest(supplied_user, expected_user)
        and secrets.compare_digest(supplied_password, password)
    ):
        return Response(status_code=401, headers={"WWW-Authenticate": 'Basic realm="AIDLC Demo"'})
    return await call_next(request)


def bus() -> RedisBus:
    return RedisBus()


TERMINAL_STATES = {"COMPLETED", "FAILED"}


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def token_usage(results: dict[str, Any] | None) -> dict[str, int]:
    results = results or {}
    usage_blocks = [
        results.get("dev", {}).get("outputs", {}).get("model", {}).get("usage", {}),
        results.get("review", {}).get("outputs", {}).get("model_review", {}).get("usage", {}),
    ]
    prompt = sum(int(item.get("prompt_tokens", 0) or 0) for item in usage_blocks)
    completion = sum(int(item.get("completion_tokens", 0) or 0) for item in usage_blocks)
    return {"prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": prompt + completion}


def dashboard_payload(client: RedisBus) -> dict[str, Any]:
    states = client.list_runs(limit=100)
    runs = []
    for state in states:
        events = client.events(state["run_id"])
        created = parse_time(state.get("created_at"))
        updated = parse_time(state.get("updated_at"))
        duration = round((updated - created).total_seconds(), 2) if created and updated else 0
        pull_request = state.get("pull_request") or {}
        runs.append({
            "run_id": state["run_id"],
            "status": state.get("status", "UNKNOWN"),
            "current_agent": state.get("current_agent"),
            "current_task": state.get("current_task"),
            "final_decision": state.get("final_decision"),
            "created_at": state.get("created_at"),
            "updated_at": state.get("updated_at"),
            "duration_seconds": duration,
            "repository": state.get("request", {}).get("repository"),
            "base_branch": state.get("request", {}).get("base_branch"),
            "event_count": len(events),
            "tokens": token_usage(state.get("results")),
            "pull_request": {"number": pull_request.get("number"), "url": pull_request.get("url")},
        })

    terminal = [item for item in runs if item["status"] in TERMINAL_STATES]
    successful = [item for item in terminal if str(item.get("final_decision") or "").startswith("ALLOW")]
    token_totals = {
        key: sum(item["tokens"][key] for item in runs)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    }
    average_duration = round(sum(item["duration_seconds"] for item in terminal) / len(terminal), 2) if terminal else 0
    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "summary": {
            "total_runs": len(runs),
            "completed_runs": sum(item["status"] == "COMPLETED" for item in runs),
            "failed_runs": sum(item["status"] == "FAILED" for item in runs),
            "active_runs": sum(item["status"] not in TERMINAL_STATES for item in runs),
            "success_rate": round(len(successful) * 100 / len(terminal), 1) if terminal else 0,
            "average_duration_seconds": average_duration,
            **token_totals,
        },
        "runs": runs,
    }


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health():
    redis_ok = False
    try:
        redis_ok = bus().ping()
    except Exception:
        pass
    return {
        "status": "ok" if redis_ok else "degraded",
        "service": "aidlc-software-factory",
        "redis_dcs": redis_ok,
        "model": settings.maas_model,
        "execution_region": "sa-brazil-1",
        "model_region": "ap-southeast-1",
    }


@app.get("/api/architecture")
def architecture():
    return architecture_payload()


@app.post("/api/runs", status_code=202)
def create_run(request: RunRequest):
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    client = bus()
    client.create_run(run_id, request.model_dump())
    client.submit_run(run_id)
    return {"run_id": run_id, "status": "QUEUED", "status_url": f"/api/runs/{run_id}"}


@app.get("/api/runs")
def list_runs():
    return {"runs": bus().list_runs()}


@app.get("/api/dashboard")
def dashboard():
    return dashboard_payload(bus())


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    state = bus().get_run(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Run not found")
    state["events"] = bus().events(run_id)
    return state


@app.get("/api/runs/{run_id}/events")
def get_events(run_id: str):
    if bus().get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"run_id": run_id, "events": bus().events(run_id)}


@app.get("/api/runs/{run_id}/evidence")
def get_evidence(run_id: str):
    evidence = bus().evidence(run_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail="Evidence is not ready")
    return evidence


@app.api_route("/preview/{run_id}/{path:path}", methods=["GET", "POST"])
async def preview_proxy(run_id: str, path: str, request: Request):
    state = bus().get_run(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Run not found")
    runtime = (
        state.get("results", {})
        .get("deploy", {})
        .get("outputs", {})
        .get("delivery", {})
        .get("runtime", {})
    )
    internal_url = runtime.get("internal_url")
    if not internal_url:
        raise HTTPException(status_code=404, detail="Preview environment is not available")
    body = await request.body()
    headers = {}
    if request.headers.get("content-type"):
        headers["content-type"] = request.headers["content-type"]
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            upstream = await client.request(
                request.method,
                f"{internal_url}/{path.lstrip('/')}",
                params=request.query_params,
                content=body,
                headers=headers,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Preview request failed: {type(exc).__name__}") from exc
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "application/json"),
    )
