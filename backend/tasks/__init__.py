"""Task registry — maps task names to task instances."""

from .task_easy import TaskEasy
from .task_medium import TaskMedium
from .task_hard import TaskHard

TASK_REGISTRY = {
    "api_json_fix": TaskEasy(),
    "csv_processor_fix": TaskMedium(),
    "retry_decorator_fix": TaskHard(),
}

TASK_LIST = [
    {
        "name": "api_json_fix",
        "difficulty": "easy",
        "description": TaskEasy.description,
    },
    {
        "name": "csv_processor_fix",
        "difficulty": "medium",
        "description": TaskMedium.description,
    },
    {
        "name": "retry_decorator_fix",
        "difficulty": "hard",
        "description": TaskHard.description,
    },
]

__all__ = ["TASK_REGISTRY", "TASK_LIST"]
