"""Tester Agent - Creates and runs tests using LLM-powered generation."""

import os
import subprocess
import re
from typing import Dict, Any, List
from agents.base import BaseAgent, AgentState
from prompts import get_prompt
from model import get_llm


class GitNotFoundError(Exception):
    """Raised when Git is not installed or not found in PATH."""
    pass


class TesterAgent(BaseAgent):
    """
    The Tester Agent using LLM-powered test generation:
    1. Analyses code changes to understand testing needs
    2. Uses LLM to generate comprehensive test files
    3. Writes and commits test files
    4. Runs tests and reports results
    """

    def __init__(self):
        super().__init__(
            name="Tester",
            description="Creates tests using LLM-powered generation"
        )
        self.prompt = get_prompt("tester", default="")
        self.llm = get_llm()

    async def execute(self, state: AgentState) -> AgentState:
        """Execute the testing workflow with LLM-powered test generation."""
        import time
        start_time = time.time()

        self.log_input(state)
        self.log("Starting LLM-powered test generation...", {
            "code_files": list(state.code_changes.keys())
        })

        try:
            test_files = await self._generate_tests_with_llm(
                state.code_changes,
                self._sanitize_input(state.issue),
                state.implementation_plan
            )
            state.test_files = test_files
            self.log("Generated test files with LLM", {"test_files": list(test_files.keys())})

            self._write_test_files(state.repo_path, test_files)
            self.log("Wrote test files", {"count": len(test_files)})

            self._commit_test_files(state.repo_path)
            self.log("Committed test files")

            test_results = self._run_tests(state.repo_path, list(test_files.keys()))
            test_count = self._count_tests(test_files)
            self.log("Ran tests", {"results": test_results})

            # Surface results on state so the pipeline router can act on them
            state.test_results = test_results
            if test_results.get("status") == "failed":
                state.test_iteration += 1
                self.log(
                    f"Tests FAILED (iteration {state.test_iteration})",
                    {"output": test_results.get("output", "")[:500]}
                )

            state.current_agent = self.name
            state.messages.append({
                "agent": self.name,
                "action": "tests_created",
                "data": {
                    "test_files": list(test_files.keys()),
                    "test_count": test_count,
                    "test_results": test_results,
                    "test_iteration": state.test_iteration
                }
            })

            self.log(f"Created {len(test_files)} test files with {test_count} tests")

            duration_ms = (time.time() - start_time) * 1000
            self.log_output(state, duration_ms)
            return state

        except Exception as e:
            self.log_error(e, {"code_files": list(state.code_changes.keys())})
            state.errors.append(str(e))
            return state

    async def _generate_tests_with_llm(
        self,
        code_changes: Dict[str, str],
        issue: str,
        implementation_plan: Dict[str, Any]
    ) -> Dict[str, str]:
        """Use LLM to generate comprehensive test files for each changed source file."""
        test_files = {}

        for file_path, content in code_changes.items():
            # Only generate tests for Python source files; skip existing test files
            if not file_path.endswith('.py') or 'test_' in file_path or '/test_' in file_path:
                continue

            test_file_path = self._get_test_file_path(file_path)
            self.log(f"Generating tests for: {file_path}")

            prompt = self._build_test_generation_prompt(
                file_path=file_path,
                source_code=content,
                issue=issue,
                implementation_plan=implementation_plan
            )

            # Call LLM - errors will propagate to user
            generated_tests = await self.llm.generate(
                prompt=prompt,
                system_prompt=self.prompt,
                temperature=0.3
            )
            clean_tests = self._extract_code_from_response(generated_tests)
            test_files[test_file_path] = clean_tests
            self.log(f"Generated tests for {file_path}", {
                "test_file": test_file_path,
                "length": len(clean_tests)
            })

        return test_files

    def _build_test_generation_prompt(
        self,
        file_path: str,
        source_code: str,
        issue: str,
        implementation_plan: Dict[str, Any]
    ) -> str:
        """Build a Casey-persona SDLC-aware prompt for comprehensive test generation."""
        module_name = os.path.splitext(os.path.basename(file_path))[0]

        # Extract testing requirements from implementation plan
        testing_reqs = {}
        if implementation_plan:
            testing_reqs = implementation_plan.get("testing_requirements", {})
            if isinstance(testing_reqs, str):
                testing_reqs = {"unit_tests": [testing_reqs]}

        action_type = implementation_plan.get("action_type", "feature") if implementation_plan else "feature"
        security_considerations = implementation_plan.get("security_considerations", []) if implementation_plan else []

        prompt_parts = [
            "You are Casey, Senior QA Engineer in the Verification phase of the SDLC.",
            "You think like a malicious user, a careless developer, and a tired ops engineer simultaneously.",
            "Write tests that fail for the right reasons and pass for the right reasons.",
            "",
            f"## Module Under Test: {module_name}",
            f"## Source File: {file_path}",
            f"## Change Type: {action_type}",
            "",
            "## Source Code to Test:",
            "```python",
            source_code[:5000],
            "```",
        ]

        if len(source_code) > 5000:
            prompt_parts.append("(Source code truncated — test what is visible)")

        prompt_parts.extend([
            "",
            "## Original User Request:",
            issue[:500],
            "",
        ])

        if testing_reqs:
            unit_tests = testing_reqs.get("unit_tests", [])
            security_tests = testing_reqs.get("security_tests", [])
            if unit_tests:
                prompt_parts.extend([
                    "## Required Test Cases (from Analyst plan):",
                    *[f"- {t}" for t in unit_tests],
                    "",
                ])
            if security_tests:
                prompt_parts.extend([
                    "## Required Security Tests:",
                    *[f"- {t}" for t in security_tests],
                    "",
                ])

        if security_considerations:
            prompt_parts.extend([
                "## Security Concerns to Test:",
                *[f"- {s}" for s in security_considerations],
                "",
            ])

        prompt_parts.extend([
            "## Test Design Rules (MANDATORY):",
            "",
            "NAMING CONVENTION: test_{method}_{scenario}_{expected_outcome}",
            "  Examples:",
            "  - test_login_with_valid_credentials_returns_token",
            "  - test_login_with_wrong_password_raises_authentication_error",
            "  - test_register_user_with_duplicate_email_returns_false",
            "",
            "AAA PATTERN: Every test must follow Arrange-Act-Assert:",
            "  # Arrange — set up inputs, mocks, expected values",
            "  # Act     — call the function/method under test",
            "  # Assert  — verify result matches expectations",
            "",
            "TEST PYRAMID — write mostly unit tests:",
            "  - Happy path: valid inputs, expected output",
            "  - Boundary values: empty string, None, zero, max int, empty list",
            "  - Invalid types: str where int expected, etc.",
            "  - Error conditions: what happens when it fails?",
            "",
            "FOR AUTHENTICATION / SECURITY CODE:",
            "  - Valid credentials → success + token returned",
            "  - Invalid password → failure, same error as wrong username (no info leak)",
            "  - Empty/None credentials → ValueError or equivalent",
            "  - SQL injection attempt in credentials → rejected safely",
            "  - Password hashing: same password always produces same hash; different passwords differ",
            "",
            "FOR API ENDPOINTS / ROUTE HANDLERS:",
            "  - 200 success with valid request body",
            "  - 400 bad request with missing required fields",
            "  - 401 unauthenticated when no token provided",
            "  - 403 forbidden when token lacks permissions",
            "  - 404 for non-existent resources",
            "",
            "PYTEST BEST PRACTICES:",
            "  - @pytest.fixture for reusable test data and instances",
            "  - @pytest.mark.parametrize for multiple inputs to same logic",
            "  - unittest.mock.patch to mock external dependencies (DB, HTTP, filesystem)",
            "  - NEVER make real network calls or write to real databases",
            "  - Each test must be independent — no shared mutable state",
            "  - Every test must have a meaningful assertion (assert True is a failure)",
            "",
            "## Output Format:",
            "Provide ONLY the complete test file. No explanations. No markdown fencing.",
            "Structure:",
            "  imports",
            "  fixtures",
            "  class Test{ClassName}: (one per source class)",
            "    def test_{method}_{scenario}_{outcome}(self, fixture): ...",
            "  class TestFunctions: (for standalone functions)",
        ])

        return "\n".join(prompt_parts)

    def _extract_code_from_response(self, response: str) -> str:
        """Strip markdown fencing from LLM response."""
        code = response.strip()
        for pattern in [r'^```(?:python|py)?\n?(.*?)```$', r'^```\n?(.*?)```$']:
            match = re.match(pattern, code, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return code

    def _get_test_file_path(self, source_file: str) -> str:
        """Compute the test file path for a given source file."""
        dir_name = os.path.dirname(source_file)
        base_name = os.path.basename(source_file)
        test_name = f"test{base_name}" if base_name.startswith('_') else f"test_{base_name}"
        return os.path.join("tests", dir_name, test_name) if dir_name else os.path.join("tests", test_name)

    def _write_test_files(self, repo_path: str, test_files: Dict[str, str]) -> None:
        """Write test files to disk."""
        for file_path, content in test_files.items():
            full_path = os.path.join(repo_path, file_path) if repo_path else file_path
            os.makedirs(os.path.dirname(full_path) or '.', exist_ok=True)
            try:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.log(f"Wrote test file: {file_path}")
            except Exception as e:
                self.log(f"Failed to write {file_path}: {e}")

    def _commit_test_files(self, repo_path: str) -> None:
        """Stage and commit test files to git."""
        if not repo_path or not os.path.exists(repo_path):
            return

        try:
            tests_path = os.path.join(repo_path, "tests")
            if os.path.exists(tests_path):
                subprocess.run(
                    ["git", "add", "tests/"],
                    cwd=repo_path,
                    capture_output=True,
                    check=True
                )
            else:
                subprocess.run(
                    ["git", "add", "-A"],
                    cwd=repo_path,
                    capture_output=True,
                    check=False
                )

            # Only commit if there are staged changes
            result = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=repo_path,
                capture_output=True
            )

            if result.returncode != 0:
                subprocess.run(
                    ["git", "commit", "-m", "test: Add automated tests for new implementation"],
                    cwd=repo_path,
                    capture_output=True,
                    check=True
                )
                self.log("Test files committed")
            else:
                self.log("No new test files to commit")

        except subprocess.CalledProcessError as e:
            self.log(f"Git commit failed: {e}")
            raise
        except FileNotFoundError:
            self.log("Git not found")
            raise GitNotFoundError("Git is not installed or not found in PATH.")

    def _run_tests(self, repo_path: str, test_file_paths: List[str]) -> Dict[str, Any]:
        """Run only the generated test files — not the entire test suite.

        Running the full suite risks failing on pre-existing broken tests that
        are unrelated to the current change, which would incorrectly trigger a
        Coder retry loop.
        """
        if not repo_path:
            return {"status": "skipped", "reason": "No repo path provided"}

        if not test_file_paths:
            return {"status": "skipped", "reason": "No test files generated"}

        # Verify pytest is installed before attempting to run tests.
        # Missing pytest is an environment problem, not a code problem — returning
        # "skipped" prevents the pipeline from triggering a pointless Coder retry loop.
        env_check = subprocess.run(
            ["python", "-m", "pytest", "--version"],
            capture_output=True,
            text=True,
        )
        if env_check.returncode != 0:
            self.log("pytest not found — skipping test run (install with: pip install pytest)")
            return {"status": "skipped", "reason": "pytest not installed — run: pip install pytest"}

        try:
            result = subprocess.run(
                ["python", "-m", "pytest"] + test_file_paths + ["-v", "--tb=short"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=120,
            )
            # Capture full output — truncation here was hiding failure details from the Coder retry
            stdout = result.stdout
            stderr = result.stderr
            return {
                "status": "passed" if result.returncode == 0 else "failed",
                "return_code": result.returncode,
                "output": stdout[:4000],
                "errors": stderr[:2000] if stderr else None,
            }
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "reason": "Tests took longer than 120 s"}
        except FileNotFoundError:
            return {"status": "skipped", "reason": "pytest not installed"}
        except Exception as exc:
            return {"status": "error", "reason": str(exc)}

    def _count_tests(self, test_files: Dict[str, str]) -> int:
        """Count total test methods across all generated test files."""
        return sum(len(re.findall(r'def test_', content)) for content in test_files.values())
