# 🔬 Reflection-Guided Debugging Agent

> We introduce process-supervised debugging environments that reward how models think, not just what they output. The agent must fix bugs AND write structured reflections — both contribute to the reward.

[![OpenEnv](https://img.shields.io/badge/OpenEnv-Compatible-blue)](https://github.com/meta-pytorch/OpenEnv)
[![Python](https://img.shields.io/badge/Python-3.11-green)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 🎯 What Makes This Environment Unique

Most debugging environments reward **only** code correctness. This environment adds a novel dimension: **LLM-as-a-Judge reflection quality scoring**.

At every step the agent must provide:
1. **Hypothesis** — Why does the bug exist?
2. **Action** — What will you change and why?
3. **Expected Result** — What should happen after the fix?

The reward is: `0.6 × code_correctness + 0.4 × reflection_quality`

This forces the agent to develop **systematic debugging skills**, not just pattern-match code fixes.

---

## 📦 Environment Specification

### Action Space (`DebugAction`)

| Field | Type | Description |
|-------|------|-------------|
| `edits` | `List[CodeEdit]` | List of search-and-replace changes |
| `hypothesis` | `str` | Why the bug exists (reference code constructs) |
| `action_description` | `str` | What was changed and why |
| `expected_result` | `str` | What's expected after the fix |

### Observation Space (`DebugObservation`)

| Field | Type | Description |
|-------|------|-------------|
| `buggy_code` | `str` | Current code under test |
| `test_output` | `str` | Captured stdout/stderr from tests |
| `tests_passed` | `int` | Number of passing tests |
| `tests_total` | `int` | Total tests in the suite |
| `reflection_prompt` | `str` | Structured H→A→R prompt |
| `step_number` | `int` | Current step (1-based) |
| `done` | `bool` | Episode terminated? |
| `reward` | `float?` | Step reward (null on reset) |
| `reward_breakdown` | `dict?` | Detailed scoring components |

### State (`DebugState`)

| Field | Type | Description |
|-------|------|-------------|
| `episode_id` | `str` | Episode identifier |
| `step_count` | `int` | Steps taken |
| `task_name` | `str` | Active task name |
| `max_steps` | `int` | Max allowed (8) |
| `best_score` | `float` | Best reward so far |

---

## 🧩 Tasks (Easy → Medium → Hard)

### 1. `api_json_fix` (Easy)
**Bug**: API handler fails to catch `JSONDecodeError` on invalid payloads and incorrectly accesses Python dicts using JS-like dot notation (`data.username`).
- 3 unit tests
- Focuses on basic exception handling and dictionary syntax.

### 2. `csv_processor_fix` (Medium)
**Bug**: CSV sales data processor crashes with `ValueError` when encountering empty amounts (`float("")`) and missing `store_id` logic.
- 3 unit tests including edge cases (empty rows, missing fields)
- Focuses on real-world data sanitization.

### 3. `retry_decorator_fix` (Hard)
**Bug**: A `@retry_on_exception` decorator silently swallows exceptions when retries are exhausted and loops the wrong number of times.
- 4 unit tests tracking exact retry attempts and exception propagation.
- Focuses on closures, decorators, and control flow bugs.

---

## 🏗️ Architecture

```
reflection-debug-agent/
├── Dockerfile                  # Multi-stage build
├── docker-compose.yml          # Local dev
├── openenv.yaml                # OpenEnv manifest
├── inference.py                # Baseline inference script
│
├── backend/
│   ├── main.py                 # FastAPI server (OpenEnv + REST API)
│   ├── requirements.txt
│   ├── models/                 # Pydantic typed models
│   │   ├── observation.py      #   DebugObservation
│   │   ├── action.py           #   DebugAction
│   │   ├── reward.py           #   RewardBreakdown
│   │   └── state.py            #   DebugState
│   ├── tasks/                  # 3 difficulty-scaled tasks
│   │   ├── base_task.py        #   Abstract base
│   │   ├── task_easy.py        #   FizzBuzz
│   │   ├── task_medium.py      #   Binary Search
│   │   └── task_hard.py        #   Linked List
│   └── engine/                 # Core logic
│       ├── environment.py      #   OpenEnv Environment
│       └── reflection_scorer.py #  Reflection quality scorer
│
└── frontend/                   # React + Vite dashboard
    ├── src/
    │   ├── components/         # UI components
    │   ├── store/              # Zustand state management
    │   └── services/           # API client
    └── ...
```

---

## 🚀 Setup & Running

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker (for containerized deployment)

### Local Development

```bash
# Backend
cd backend
pip install -r requirements.txt
cd ..
uvicorn backend.main:app --host 0.0.0.0 --port 7860 --reload

# Frontend (in a separate terminal)
cd frontend
npm install
npm run dev
```

### Docker

```bash
docker build -t reflection-debug-agent .
docker run -p 7860:7860 reflection-debug-agent
```

### Docker Compose

```bash
docker-compose up --build
```

### Running Inference

```bash
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export HF_TOKEN="your_token_here"
export ENV_URL="http://localhost:7860"

python inference.py
```

---

## 📊 Reward Function

The combined reward at each step:

```
reward = 0.6 × code_correctness + 0.4 × reflection_quality
```

**Code Correctness** (0.6 weight):
- `tests_passed / tests_total`

**Reflection Quality** (0.4 weight) — scored via LLM-as-a-Judge (Qwen2.5-72B-Instruct):
- Bug Identification Correctness (0.25): Did they clearly and correctly identify a plausible bug?
- Fix Relevance (0.25): Does the proposed action cleanly address the hypothesis?
- Reasoning Consistency (0.25): Does the Expected Result logically flow from the Action?
- Improvement Signal (0.25): Did test execution explicitly improve due to the proposed fix?

---

## ✅ Pre-Submission Checklist

- [x] HF Space deploys and responds to `/reset` with 200
- [x] OpenEnv spec compliance (`openenv.yaml`, typed models, endpoints)
- [x] Dockerfile builds successfully
- [x] Baseline `inference.py` reproduces with structured logs
- [x] 3+ tasks with graders returning scores in 0.0–1.0

---

## 📄 License

MIT
