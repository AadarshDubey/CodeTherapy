"""
FastAPI server for the Reflection Debug Agent environment.

Provides both:
1. OpenEnv-compatible endpoints: /reset, /step, /state
2. REST API endpoints for the frontend dashboard: /api/*

The server uses create_fastapi_app pattern internally but also
exposes additional routes needed for the React frontend.
"""

import os
import sys
import json
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

# Ensure the parent directory is in the path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.engine.environment import DebugEnvironment
from backend.models.action import DebugAction
from backend.models.observation import DebugObservation
from backend.models.state import DebugState
from backend.tasks import TASK_REGISTRY, TASK_LIST
from backend.agent import get_agent_action
from backend.engine.experiment import run_experiment


# --- App Setup ---
app = FastAPI(
    title="Reflection Debug Agent",
    description=(
        "An OpenEnv-compliant environment that simulates a software engineer "
        "iteratively debugging code with structured reflections."
    ),
    version="0.1.0",
)

# CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Per-session environment instances
_sessions: dict[str, DebugEnvironment] = {}


def _get_or_create_env(session_id: Optional[str] = None) -> tuple[str, DebugEnvironment]:
    """Get an existing env session or create a new one."""
    if session_id and session_id in _sessions:
        return session_id, _sessions[session_id]
    sid = session_id or str(uuid.uuid4())
    env = DebugEnvironment()
    _sessions[sid] = env
    return sid, env


# --- Request/Response Models ---

class ResetRequest(BaseModel):
    task_name: Optional[str] = "api_json_fix"
    session_id: Optional[str] = None
    episode_id: Optional[str] = None
    custom_buggy_code: Optional[str] = None
    custom_test_code: Optional[str] = None


class StepRequest(BaseModel):
    session_id: str
    edits: list[dict]
    hypothesis: str
    action_description: str
    expected_result: str


class AutoStepRequest(BaseModel):
    session_id: str


class ResetResponse(BaseModel):
    session_id: str
    observation: dict


class StepResponse(BaseModel):
    observation: dict
    reward: Optional[float]
    done: bool


class StateResponse(BaseModel):
    state: dict


# --- OpenEnv-Compatible Endpoints ---

@app.post("/reset")
async def reset(request: ResetRequest = ResetRequest()):
    """
    OpenEnv reset() endpoint.
    Initializes a new debugging episode.
    """
    sid, env = _get_or_create_env(request.session_id)
    obs = env.reset(
        task_name=request.task_name,
        episode_id=request.episode_id,
        custom_buggy_code=request.custom_buggy_code,
        custom_test_code=request.custom_test_code,
    )
    return {
        "session_id": sid,
        "observation": obs.model_dump(),
        "done": obs.done,
        "reward": obs.reward,
    }


@app.post("/step")
async def step(request: StepRequest):
    """
    OpenEnv step() endpoint.
    Executes one debugging attempt.
    """
    if request.session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found. Call /reset first.")

    env = _sessions[request.session_id]
    action = DebugAction(
        edits=request.edits,
        hypothesis=request.hypothesis,
        action_description=request.action_description,
        expected_result=request.expected_result,
    )
    obs = env.step(action)
    return {
        "observation": obs.model_dump(),
        "reward": obs.reward,
        "done": obs.done,
    }


@app.get("/state")
async def get_state(session_id: str = ""):
    """
    OpenEnv state() endpoint.
    Returns current environment metadata.
    """
    if session_id and session_id in _sessions:
        env = _sessions[session_id]
        return {"state": env.state.model_dump()}
    return {"state": DebugState().model_dump()}


# --- Frontend API Endpoints ---

@app.get("/api/tasks")
async def list_tasks():
    """List all available debugging tasks."""
    return {"tasks": TASK_LIST}


@app.post("/api/reset")
async def api_reset(request: ResetRequest = ResetRequest()):
    """Reset with task selection (frontend-friendly)."""
    return await reset(request)


@app.post("/api/step")
async def api_step(request: StepRequest):
    """Step with action payload (frontend-friendly)."""
    return await step(request)


@app.post("/api/auto_step")
async def api_auto_step(request: AutoStepRequest):
    """Run one step of the agent autonomously."""
    if request.session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found. Call /reset first.")

    env = _sessions[request.session_id]
    
    if env.state.tests_passed == env.state.tests_total or env.state.step_count >= env.MAX_STEPS:
        raise HTTPException(status_code=400, detail="Episode already finished")

    buggy_code = env.state.current_code
    try:
        _, _, test_output = env._task.run_tests(buggy_code)
    except Exception as e:
        test_output = f"Error executing code: {str(e)}"
    
    history_strs = [
        f"Step {h['step']}: {h['hypothesis'][:80]} -> reward {h['combined_reward']:+.2f}"
        for h in env.history
    ]
    
    action_dict = get_agent_action(
        buggy_code=buggy_code,
        test_output=test_output,
        step=env.state.step_count + 1,
        history=history_strs
    )
    
    action = DebugAction(
        edits=action_dict["edits"],
        hypothesis=action_dict["hypothesis"],
        action_description=action_dict["action_description"],
        expected_result=action_dict["expected_result"],
    )
    
    obs = env.step(action)
    return {
        "observation": obs.model_dump(),
        "reward": obs.reward,
        "done": obs.done,
        "action": action_dict,
    }


@app.get("/api/state")
async def api_state(session_id: str = ""):
    """Get current state (frontend-friendly)."""
    return await get_state(session_id)


@app.get("/api/history")
async def api_history(session_id: str = ""):
    """Get step history for the current episode."""
    if session_id and session_id in _sessions:
        env = _sessions[session_id]
        return {"history": env.history}
    return {"history": []}


# --- Experiment Endpoints ---

class ExperimentRequest(BaseModel):
    task_name: str = "api_json_fix"


@app.post("/api/experiment/run")
async def api_run_experiment(request: ExperimentRequest):
    """
    Run A/B experiment: blind mode vs reflection mode.
    Returns complete comparison data for both runs.
    """
    try:
        result = run_experiment(request.task_name)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Experiment failed: {str(exc)}")


@app.get("/api/task/{task_name}")
async def get_task_detail(task_name: str):
    """Get detailed info about a specific task."""
    if task_name not in TASK_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Task '{task_name}' not found.")
    task = TASK_REGISTRY[task_name]
    return {
        "name": task.name,
        "difficulty": task.difficulty,
        "description": task.description,
        "buggy_code": task.buggy_code,
        "hint": task.hint,
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "environment": "reflection-debug-agent", "version": "0.1.0"}


# --- Static File Serving (production) ---
# Serve built frontend from /frontend/dist if it exists
frontend_dist = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist"
)
if os.path.isdir(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_dist, "index.html"))

    @app.get("/{full_path:path}")
    async def serve_frontend_fallback(full_path: str):
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))
