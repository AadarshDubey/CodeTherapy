---
title: Reflection Debug Agent
emoji: 🔬
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: "Process-supervised debugging with LLM-as-a-Judge reflections"
---

<div align="center">

# 🔬 Code Therapy — Reflection-Guided Debugging Agent

**An OpenEnv RL environment where AI agents learn to debug code _and_ explain their reasoning.**

[![Live Demo](https://img.shields.io/badge/🤗%20HF%20Space-Live-blue?style=for-the-badge)](https://huggingface.co/spaces/aady161103/reflection-debug-agent)
[![OpenEnv](https://img.shields.io/badge/OpenEnv-v1%20Compatible-0066ff?style=for-the-badge)](https://github.com/meta-pytorch/OpenEnv)
[![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ed?style=for-the-badge&logo=docker&logoColor=white)](Dockerfile)

---

_Most debugging environments reward only code correctness._
_This one rewards **how the agent thinks** — not just what it outputs._

</div>

---

## 💡 The Core Idea

Traditional code-debugging RL environments define reward as a binary: tests pass or they don't. This discards all signal about the agent's _reasoning process_.

**Code Therapy** introduces **process supervision** for debugging. At every step, the agent must produce:

| Component | What the agent writes | Why it matters |
|-----------|----------------------|----------------|
| **Hypothesis** | _"The bug exists because `float("")` throws `ValueError` on empty CSV cells"_ | Forces root-cause analysis, not random edits |
| **Action** | _"Wrap the conversion in a try/except and skip malformed rows"_ | Demands intentional, justified fixes |
| **Expected Result** | _"Tests 1-3 should now pass since empty rows are gracefully skipped"_ | Requires predictive reasoning about outcomes |

The reward function then combines both dimensions:

```
reward = 0.6 × code_correctness + 0.4 × reflection_quality
```

**Reflection quality** is scored by an **LLM-as-a-Judge** (Qwen2.5-72B-Instruct) using a structured rubric — making this a _process-supervised_ debugging environment.

---

## 🧩 Tasks — 3 Difficulty Levels

Each task presents real-world buggy Python code with automated test suites. Rewards are in `[0.0, 1.0]`.

### Task 1 · `api_json_fix` · Easy
> **Bug:** API handler fails to catch `JSONDecodeError` on malformed payloads and uses JavaScript-style dot notation (`data.username`) on Python dicts.
- 3 unit tests · Focuses on exception handling and dict access syntax.

### Task 2 · `csv_processor_fix` · Medium
> **Bug:** CSV sales processor crashes with `ValueError` on empty amount fields (`float("")`) and has missing `store_id` grouping logic.
- 3 unit tests (including edge cases) · Focuses on real-world data sanitization.

### Task 3 · `retry_decorator_fix` · Hard
> **Bug:** A `@retry_on_exception` decorator silently swallows exceptions when retries exhaust and loops an incorrect number of times.
- 4 unit tests tracking exact retry counts and exception propagation · Focuses on closures, decorators, and control flow.

---

## 📦 OpenEnv Specification

### Action Space — `DebugAction`
```python
class DebugAction(BaseModel):
    edits: List[CodeEdit]          # search-and-replace patches
    hypothesis: str                # why the bug exists
    action_description: str        # what was changed and why
    expected_result: str           # predicted outcome after fix
```

### Observation Space — `DebugObservation`
```python
class DebugObservation(BaseModel):
    buggy_code: str                # current source code
    test_output: str               # stdout/stderr from test run
    tests_passed: int              # passing test count
    tests_total: int               # total test count
    reflection_prompt: str         # structured H→A→R prompt
    step_number: int               # current step (1-based)
    done: bool                     # episode complete?
    reward: Optional[float]        # step reward (null on reset)
    reward_breakdown: Optional[dict]  # detailed scoring components
```

### State — `DebugState`
```python
class DebugState(BaseModel):
    episode_id: str
    step_count: int
    task_name: str
    max_steps: int                 # 8
    best_score: float
```

### API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/reset` | Reset env for a new task, returns initial `DebugObservation` |
| `POST` | `/step` | Submit a `DebugAction`, returns observation + reward + done |
| `GET` | `/state` | Query current environment state |
| `GET` | `/health` | Health check |

---

## 📊 Reward Function — Dual-Axis Scoring

```
total_reward = 0.6 × code_correctness + 0.4 × reflection_quality
```

### Code Correctness (weight: 0.6)
```
code_score = tests_passed / tests_total
```

### Reflection Quality (weight: 0.4) — LLM-as-a-Judge
An LLM evaluates the agent's structured reflection on four axes:

| Criterion | Weight | What's evaluated |
|-----------|--------|------------------|
| Bug Identification | 25% | Did the agent correctly identify a plausible root cause? |
| Fix Relevance | 25% | Does the proposed edit directly address the identified bug? |
| Reasoning Consistency | 25% | Does the expected result logically follow from the action? |
| Improvement Signal | 25% | Did test results actually improve after the fix? |

---

## 🏗️ Project Structure

```
reflection-debug-agent/
├── openenv.yaml                # OpenEnv manifest (spec v1)
├── pyproject.toml              # Python package config + dependencies
├── inference.py                # Baseline inference script (root)
├── Dockerfile                  # Multi-stage build (Node + Python)
├── docker-compose.yml          # Local development
│
├── backend/
│   ├── main.py                 # FastAPI server — /reset, /step, /state
│   ├── agent.py                # LLM agent wrapper
│   ├── requirements.txt        # Python dependencies
│   ├── models/                 # Pydantic typed models
│   │   ├── action.py           #   DebugAction + CodeEdit
│   │   ├── observation.py      #   DebugObservation
│   │   ├── state.py            #   DebugState
│   │   └── reward.py           #   RewardBreakdown
│   ├── tasks/                  # 3 difficulty-graded tasks
│   │   ├── base_task.py        #   Abstract task interface
│   │   ├── task_easy.py        #   api_json_fix
│   │   ├── task_medium.py      #   csv_processor_fix
│   │   ├── task_hard.py        #   retry_decorator_fix
│   │   └── custom_task.py      #   User-provided code support
│   └── engine/
│       ├── environment.py      #   OpenEnv environment loop
│       └── reflection_scorer.py #  LLM-as-a-Judge scorer
│
├── server/
│   └── app.py                  # Multi-mode deployment entry point
│
└── frontend/                   # React + Vite dashboard
    └── src/
        ├── components/         # UI components
        ├── store/              # Zustand state management
        └── services/           # API client
```

---

## 🚀 Quick Start

### Environment Variables

```bash
# Required
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export HF_TOKEN="your_huggingface_token"

# Optional
export ENV_URL="http://localhost:7860"   # defaults to localhost
```

### Option 1 — Docker (Recommended)

```bash
docker build -t reflection-debug-agent .
docker run -p 7860:7860 \
  -e HF_TOKEN=$HF_TOKEN \
  -e API_BASE_URL=$API_BASE_URL \
  -e MODEL_NAME=$MODEL_NAME \
  reflection-debug-agent
```

### Option 2 — Docker Compose

```bash
# Create .env file with your variables first
docker compose up --build
```

### Option 3 — Local Development

```bash
# Backend
cd backend && pip install -r requirements.txt && cd ..
uvicorn backend.main:app --host 0.0.0.0 --port 7860 --reload

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

### Running Inference

```bash
# Start the environment server first, then:
python inference.py
```

**Expected stdout format:**
```
[START] task=api_json_fix env=reflection_debug_agent model=Qwen/Qwen2.5-72B-Instruct
[STEP]  step=1 action=fix(Incorrect dict access ...) reward=0.45 done=false error=null
[STEP]  step=2 action=fix(Missing JSONDecodeError...) reward=0.78 done=false error=null
[STEP]  step=3 action=fix(Final cleanup of error ...) reward=1.00 done=true error=null
[END]   success=true steps=3 rewards=0.45,0.78,1.00
```

---

## ✅ Pre-Submission Checklist

- [x] **HF Space deploys** — automated ping returns 200 and responds to `POST /reset`
- [x] **OpenEnv spec compliance** — `openenv.yaml` + typed Pydantic models + `/step` `/reset` `/state`
- [x] **Dockerfile builds** — multi-stage (Node.js frontend → Python backend)
- [x] **Baseline inference reproduces** — `inference.py` at root with `[START]`/`[STEP]`/`[END]` stdout
- [x] **3+ tasks with graders** — easy/medium/hard, all scores in `[0.0, 1.0]`
- [x] **OpenAI client** — all LLM calls via `openai.OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)`
- [x] **pyproject.toml** — with `openenv-core>=0.2.0` dependency and `[project.scripts]` entry
- [x] **uv.lock** — dependency lock file present

---

## 🔗 Links

| Resource | URL |
|----------|-----|
| **Live Space** | [huggingface.co/spaces/aady161103/reflection-debug-agent](https://huggingface.co/spaces/aady161103/reflection-debug-agent) |
| **GitHub** | [github.com/AadarshDubey/CodeTherapy](https://github.com/AadarshDubey/CodeTherapy) |
| **OpenEnv Framework** | [github.com/meta-pytorch/OpenEnv](https://github.com/meta-pytorch/OpenEnv) |

---

## 📄 License

MIT