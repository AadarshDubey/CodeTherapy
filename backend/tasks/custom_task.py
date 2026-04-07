import os
import subprocess
import tempfile
import traceback
from typing import Tuple
import textwrap

from backend.tasks.base_task import BaseTask
from backend.tasks.timeout_util import run_with_timeout

class CustomTask(BaseTask):
    """
    A custom task that takes arbitrary buggy_code and test_code from the user.
    """
    name = "custom"
    difficulty = "custom"
    description = "Custom User-Provided Task"
    hint = "Rely on the provided test failures to guide your bug fixing."

    def __init__(self, buggy_code: str, test_code: str):
        self.buggy_code = buggy_code
        self.test_code = test_code

    def run_tests(self, code: str) -> Tuple[int, int, str]:
        if "#include" in code or "using namespace std" in code:
            return self._run_cpp(code)
        else:
            return self._run_python(code)

    def _run_cpp(self, code: str) -> Tuple[int, int, str]:
        # Check if g++ is installed
        try:
            subprocess.run(["g++", "--version"], capture_output=True, check=True)
        except Exception:
            return 0, 1, "Environment Error: g++ is not installed or not in PATH. Cannot compile C++ code."

        # Parse test code into blocks separated by \n\n
        blocks = [b.strip() for b in self.test_code.split("\n\n") if b.strip()]
        if not blocks:
            blocks = [""]

        passed = 0
        total = len(blocks)
        output_results = []
        
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = os.path.join(tmpdir, "main.cpp")
            exe_file = os.path.join(tmpdir, "main.exe" if os.name == "nt" else "main")
            
            with open(src_file, "w", encoding="utf-8") as f:
                f.write(code)
                
            # Compile
            compile_proc = subprocess.run(["g++", "-O2", src_file, "-o", exe_file], capture_output=True, text=True)
            if compile_proc.returncode != 0:
                return 0, total, f"Compilation Error:\n{compile_proc.stderr}"
                
            # Execute blocks
            for i, block in enumerate(blocks):
                # Check for expected output
                expected_out = None
                input_data = block
                if "---" in block:
                    parts = block.split("---")
                    input_data = parts[0].strip()
                    if len(parts) > 1:
                        expected_out = parts[1].strip()
                
                try:
                    run_proc = subprocess.run([exe_file], input=input_data, capture_output=True, text=True, timeout=2.0)
                    stdout = run_proc.stdout.strip()
                    stderr = run_proc.stderr.strip()
                    
                    if run_proc.returncode != 0:
                        output_results.append(f"Test {i+1} FAIL: Exit code {run_proc.returncode}\nStderr: {stderr}")
                        continue
                        
                    if expected_out is not None:
                        if stdout == expected_out:
                            passed += 1
                            output_results.append(f"Test {i+1} PASS")
                        else:
                            output_results.append(f"Test {i+1} FAIL:\nExpected:\n{expected_out}\nGot:\n{stdout}")
                    else:
                        # If no expected output is provided, we just assume any successful exit code is a pass
                        passed += 1
                        output_results.append(f"Test {i+1} PASS:\n{stdout}")
                        
                except subprocess.TimeoutExpired:
                    output_results.append(f"Test {i+1} FAIL: Timeout expired.")

        summary = f"C++ Tests: {passed}/{total} passed\n" + "\n".join(output_results)
        return passed, total, summary

    def _run_python(self, code: str) -> Tuple[int, int, str]:
        # Use regex to split test_code by "---" on lines by themselves
        import re
        blocks = [b.strip() for b in re.split(r'^\s*---\s*$', self.test_code, flags=re.MULTILINE) if b.strip()]
        
        # Fallback to single block if empty
        if not blocks and self.test_code.strip():
            blocks = [self.test_code.strip()]

        if not blocks:
            return 0, 1, "No test code provided."

        namespace = {}
        # Pre-evaluate the buggy code so it's loaded into the namespace
        try:
            exec(code, namespace)
        except Exception as e:
            return 0, 1, f"Code execution error:\n{traceback.format_exc()}"

        passed = 0
        total = len(blocks)
        output_results = []

        for i, block_code in enumerate(blocks):
            try:
                def _exec_code():
                    # We execute the test block inside the namespace wrapper
                    exec(block_code, namespace)
                    
                run_with_timeout(_exec_code, timeout_s=2.0)
                passed += 1
                output_results.append(f"Test {i+1} PASS")
            except AssertionError as e:
                msg = str(e) or "AssertionError"
                output_results.append(f"Test {i+1} FAIL: {msg}")
            except Exception as e:
                if isinstance(e, TimeoutError) or str(type(e).__name__) == "TimeoutError":
                    output_results.append(f"Test {i+1} FAIL: Time out")
                else:
                    output_results.append(f"Test {i+1} FAIL: {type(e).__name__}: {str(e)}")

        summary = f"Python Tests: {passed}/{total} passed\n" + "\n".join(output_results)
        return passed, total, summary

    def grade(self, tests_passed: int, tests_total: int) -> float:
        if tests_total == 0:
            return 0.0
        return float(tests_passed) / float(tests_total)
