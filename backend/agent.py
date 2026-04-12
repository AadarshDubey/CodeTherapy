"""
Agent — LLM-powered code debugging agent.

Two modes:
  1. Reflection agent: Multi-turn conversation. Sees its previous attempts,
     reflects on what worked and what didn't, tries different approaches.
  2. Blind agent: Single-turn. One shot, no history, no reflection.
"""

import os
import json
import textwrap
from typing import Dict, List, Tuple, Optional

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("API_KEY") or os.getenv("HF_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")

# Lazy-initialized client — created on first use so the server can
# start even when API_KEY is not yet available (e.g. Docker startup).
_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        key = os.getenv("API_KEY") or os.getenv("HF_TOKEN") or API_KEY
        _client = OpenAI(base_url=API_BASE_URL, api_key=key or "not-set")
    return _client

# ─── System Prompts ───────────────────────────────────────────────────

REFLECTION_SYSTEM_PROMPT = textwrap.dedent("""\
    You are an expert software engineer debugging code through iterative refinement.

    PROCESS:
    1. Read the buggy code and ALL test failures carefully
    2. Form a clear hypothesis about what's causing each failure
    3. Make targeted edits to fix the bugs
    4. If your previous fix didn't fully work, ANALYZE WHY and try a COMPLETELY DIFFERENT approach
    
    CRITICAL: If you already tried something and it failed, DO NOT repeat it.
    Think about what SPECIFICALLY went wrong and change your strategy.
    
    RESPONSE FORMAT — respond with ONLY a valid JSON object:
    {
        "hypothesis": "What bugs you found, referencing specific lines and variable names",
        "action_description": "Exactly what you're changing and why",
        "expected_result": "Which tests should pass after this fix and why",
        "edits": [{"search": "exact code to find", "replace": "fixed code"}]
    }
    
    EDIT RULES:
    - "search" MUST be copied EXACTLY from the Current Code — character for character
    - Include 2-3 surrounding lines of context to make the match unique
    - INDENTATION MATTERS — your "replace" must have correct Python indentation
    - Use MULTIPLE edits to fix multiple bugs at once
    - Respond with ONLY the JSON object, no other text
""")

BLIND_SYSTEM_PROMPT = textwrap.dedent("""\
    You are an expert software engineer. Fix the buggy code based on the test results.
    
    Respond with ONLY a JSON object:
    {
        "edits": [{"search": "exact code to find", "replace": "fixed code"}]
    }
    
    RULES:
    - "search" MUST match the code EXACTLY, including indentation
    - "replace" must have correct Python indentation
    - Respond with ONLY the JSON object
""")


# ─── Reflection Agent (Multi-turn) ───────────────────────────────────

def get_agent_action(
    buggy_code: str,
    test_output: str,
    step: int,
    history: List[str],  # kept for API compat but not used — messages handle history
    messages: Optional[List[dict]] = None,
    max_steps: int = 8,
) -> Tuple[Dict[str, str], List[dict]]:
    """
    Multi-turn reflection agent.
    
    On step 1: Initialize conversation with system prompt + first observation.
    On step 2+: Append feedback about what happened and ask for a different approach.
    
    Returns:
        (action_dict, updated_messages)
    """
    # Initialize messages on first step
    if messages is None or step == 1:
        messages = [{"role": "system", "content": REFLECTION_SYSTEM_PROMPT}]
    
    # Build the user message for this step
    if step == 1:
        user_msg = textwrap.dedent(f"""\
            Here is buggy code that needs debugging. Analyze ALL test failures and fix the bugs.
            
            Current Code:
            ```python
            {buggy_code}
            ```
            
            Test Results:
            {test_output}
            
            Step {step}/{max_steps}. Fix as many bugs as you can.
        """)
    else:
        user_msg = textwrap.dedent(f"""\
            Your previous fix was applied. Here are the results:
            
            Current Code (after your changes):
            ```python
            {buggy_code}
            ```
            
            Test Results:
            {test_output}
            
            Step {step}/{max_steps} — {max_steps - step} steps remaining.
            
            Your previous approach did NOT solve all tests.
            ANALYZE what went wrong and try a DIFFERENT strategy.
            Do NOT repeat the same fix — it already failed.
        """)
    
    messages.append({"role": "user", "content": user_msg})
    
    # Keep conversation bounded to avoid context overflow (last ~6 turns)
    if len(messages) > 13:  # system + 6 user/assistant pairs
        messages = [messages[0]] + messages[-12:]
    
    try:
        completion = _get_client().chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.3,
            max_tokens=4096,
        )
        raw = (completion.choices[0].message.content or "").strip()
        
        # Add assistant response to conversation
        messages.append({"role": "assistant", "content": raw})
        
        # Parse JSON
        text = raw
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        parsed = json.loads(text)
        
        action = {
            "edits": parsed.get("edits", []),
            "hypothesis": parsed.get("hypothesis", ""),
            "action_description": parsed.get("action_description", ""),
            "expected_result": parsed.get("expected_result", ""),
        }
        return action, messages
        
    except json.JSONDecodeError:
        messages.append({"role": "assistant", "content": raw if 'raw' in dir() else ""})
        return {
            "edits": [],
            "hypothesis": "Failed to parse LLM response as JSON",
            "action_description": "No changes made due to parse error",
            "expected_result": "No improvement expected",
        }, messages
    except Exception as exc:
        print(f"[DEBUG] Model request failed: {exc}", flush=True)
        return {
            "edits": [],
            "hypothesis": f"LLM call failed: {exc}",
            "action_description": "No changes possible",
            "expected_result": "No improvement expected",
        }, messages


# ─── Blind Agent (Single-turn) ────────────────────────────────────────

def get_blind_agent_action(
    buggy_code: str,
    test_output: str,
    step: int,
    history: List[str],
) -> Dict[str, str]:
    """Single-shot blind agent — no reflection, no history, one attempt."""
    user_prompt = textwrap.dedent(f"""\
        Fix the buggy code below. Make it pass all tests.
        
        Current Code:
        ```python
        {buggy_code}
        ```
        
        Test Results:
        {test_output}
        
        Fix ALL bugs. Respond with JSON only.
    """)

    try:
        completion = _get_client().chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": BLIND_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
        )
        raw = (completion.choices[0].message.content or "").strip()

        text = raw
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        parsed = json.loads(text)

        return {
            "edits": parsed.get("edits", []),
            "hypothesis": "N/A (blind mode)",
            "action_description": "N/A (blind mode)",
            "expected_result": "N/A (blind mode)",
        }
    except json.JSONDecodeError:
        return {
            "edits": [],
            "hypothesis": "Failed to parse LLM response",
            "action_description": "No changes made",
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
