"""
Programmatic reflection scorer using LLM-as-a-judge.

Scores the quality of an agent's structured reflection on three axes:
  - bug identification correctness
  - fix relevance
  - reasoning consistency
Plus a deterministic axis:
  - improvement signal

All 4 dimensions are weighted equally (0.25 each) to sum to 1.0.
"""

import os
import json
import textwrap
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_KEY = os.environ.get("API_KEY", os.environ.get("HF_TOKEN"))
API_BASE_URL = os.environ.get("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")

JUDGE_SYSTEM_PROMPT = textwrap.dedent("""\
You are an expert judge evaluating a software engineering agent's debugging reflection.
You will be given the agent's proposed Hypothesis, Action Description, and Expected Result.
Rate the reflection's quality on these 3 dimensions (0.0 to 1.0 float values):

1. bug_identification_correctness: Did they clearly and correctly identify a highly plausible bug? (0.0=vague/wrong, 1.0=precise/logical)
2. fix_relevance: Does the proposed action cleanly address the hypothesis? (0.0=unrelated/messy, 1.0=targeted/precise)
3. reasoning_consistency: Does the expected result logically follow the action without contradicting? (0.0=inconsistent, 1.0=perfectly consistent)

Return ONLY a valid JSON object:
{
    "bug_identification_correctness": 0.0,
    "fix_relevance": 0.0,
    "reasoning_consistency": 0.0
}
""")

class ReflectionScorer:
    """
    Scores reflection quality on a 0.0-1.0 scale via LLM-as-a-judge.
    """
    
    def __init__(self):
        self.client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    def score(
        self,
        hypothesis: str,
        action_description: str,
        expected_result: str,
        prev_tests_passed: int,
        curr_tests_passed: int,
        tests_total: int,
    ) -> dict:
        """
        Compute a combined reflection quality score using an LLM.
        Returns a dictionary with sub-scores.
        """
        # 1. Deterministic Improvement Score (0.25 weight)
        s_improve = self._score_improvement(prev_tests_passed, curr_tests_passed, tests_total)
        
        # 2. LLM-Judged Scores (0.75 weight distributed as 0.25 each)
        try:
            user_prompt = textwrap.dedent(f"""\
            Hypothesis:
            {hypothesis}
            
            Action Description:
            {action_description}
            
            Expected Result:
            {expected_result}
            """)
            
            completion = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=256,
                timeout=10.0
            )
            text = (completion.choices[0].message.content or "").strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
                
            parsed = json.loads(text)
            s_bug = float(parsed.get("bug_identification_correctness", 0.5))
            s_fix = float(parsed.get("fix_relevance", 0.5))
            s_res = float(parsed.get("reasoning_consistency", 0.5))
            
            # Bound them
            s_bug = min(max(s_bug, 0.0), 1.0)
            s_fix = min(max(s_fix, 0.0), 1.0)
            s_res = min(max(s_res, 0.0), 1.0)
            
        except Exception as exc:
            print(f"[LLM Judge Warning] Failed to score reflection: {exc}. Falling back to 0.5 averages.")
            s_bug, s_fix, s_res = 0.5, 0.5, 0.5

        combined = (0.25 * s_improve) + (0.25 * s_bug) + (0.25 * s_fix) + (0.25 * s_res)
        combined_rounded = round(min(max(combined, 0.0), 1.0), 4)

        return {
            "combined": combined_rounded,
            "s_improve": round(s_improve, 4),
            "s_bug": round(s_bug, 4),
            "s_fix": round(s_fix, 4),
            "s_res": round(s_res, 4)
        }

    def _score_improvement(
        self, prev_passed: int, curr_passed: int, total: int
    ) -> float:
        if total == 0:
            return 0.0
        if curr_passed > prev_passed:
            improvement = (curr_passed - prev_passed) / total
            return round(min(0.5 + improvement, 1.0), 4)
        elif curr_passed == prev_passed and curr_passed > 0:
            return 0.3
        elif curr_passed == prev_passed:
            return 0.1
        else:
            return 0.0
