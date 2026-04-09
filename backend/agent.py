import os
import json
import textwrap
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

if "API_KEY" not in os.environ and "HF_TOKEN" in os.environ:
    os.environ["API_KEY"] = os.environ["HF_TOKEN"]
if "API_BASE_URL" not in os.environ:
    os.environ["API_BASE_URL"] = "https://router.huggingface.co/v1"

from openai import OpenAI

MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
TEMPERATURE = 0.7
MAX_TOKENS = 2048

SYSTEM_PROMPT = textwrap.dedent("""\
    You are an expert software engineer debugging code.
    You will be given buggy code and test results.
    
    You must respond with a JSON object containing exactly these fields:
    {
        "hypothesis": "Why the bug exists — reference specific code constructs, variable names, or logic errors.",
        "action_description": "What you will change and why — describe the concrete modification.",
        "expected_result": "What you expect after the fix — which tests should now pass and why.",
        "edits": [{"search": "old code...", "replace": "new code..."}]
    }
    
    IMPORTANT:
    - "edits" must be a list of objects, each containing a "search" and "replace" string.
    - "search" MUST be an EXACT match of a block of code, including all spaces and indentation.
    - "replace" is the exact string to substitute it with.
    - INDENTATION MATTERS: Your "replace" string must include the exact leading spaces/tabs required for proper Python indentation!
    - To insert code, make "search" match the surrounding lines and include them in "replace".
    - Be specific in your hypothesis.
    - Respond ONLY with the JSON object, no other text.
""")

def build_user_prompt(buggy_code: str, test_output: str, step: int, history: List[str]) -> str:
    history_block = "\n".join(history[-4:]) if history else "None"
    return textwrap.dedent(f"""\
        Step: {step}
        
        Current Code:
        ```python
        {buggy_code}
        ```
        
        Test Results:
        {test_output}
        
        Previous attempts:
        {history_block}
        
        Analyze the bug, fix the code, and provide your structured reflection as JSON.
    """)

def get_agent_action(buggy_code: str, test_output: str, step: int, history: List[str]) -> Dict[str, str]:
    """Call the LLM and parse its JSON response for the next action."""
    client = OpenAI(base_url=os.environ["API_BASE_URL"], api_key=os.environ["API_KEY"])
    user_prompt = build_user_prompt(buggy_code, test_output, step, history)
    
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        text = (completion.choices[0].message.content or "").strip()

        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        parsed = json.loads(text)
        return {
            "edits": parsed.get("edits", []),
            "hypothesis": parsed.get("hypothesis", "No hypothesis provided"),
            "action_description": parsed.get("action_description", "No action described"),
            "expected_result": parsed.get("expected_result", "No expected result"),
        }
    except json.JSONDecodeError as e:
        print(f"[DEBUG] JSON parse failed: {e}", flush=True)
        return {
            "edits": [],
            "hypothesis": "Failed to parse LLM response",
            "action_description": "No changes made due to parse error",
            "expected_result": "No improvement expected",
        }
    except Exception as exc:
        print(f"[DEBUG] Model request failed: {exc}", flush=True)
        return {
            "edits": [],
            "hypothesis": f"LLM call failed: {exc}",
            "action_description": "No changes possible",
            "expected_result": "No improvement expected",
        }
