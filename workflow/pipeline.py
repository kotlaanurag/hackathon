"""Agent Pipeline - Two-phase sequential execution of the multi-agent workflow.

Phase 1  POST /plan    → Orchestrator → RepoReader → Analyst
Phase 2  POST /execute → Coder → Reviewer → Tester → PRManager
"""

from typing import Dict, Any

from agents.base import AgentState
from agents.orchestrator.agent import OrchestratorAgent
from agents.repo_reader.agent import RepoReaderAgent
from agents.analyst.agent import AnalystAgent
from agents.coder.agent import CoderAgent
from agents.reviewer.agent import ReviewerAgent
from agents.tester.agent import TesterAgent
from agents.pr_manager.agent import PRManagerAgent
from logger import log_pipeline_start, log_pipeline_end


class AgentPipeline:
    """
    Orchestrates agents in two sequential phases.

    Phase 1 — Planning (POST /plan):
        Orchestrator → RepoReader → Analyst
        Returns a slim plan for user review/edit.

    Phase 2 — Execution (POST /execute):
        Coder → Reviewer [→ Coder retry on errors]
              → Tester   [→ Coder+Reviewer retry on failures, max 2×]
              → PRManager
    """

    MAX_REVIEW_RETRIES = 1
    MAX_TEST_RETRIES = 2

    def __init__(self, repo_path: str = ""):
        self.repo_path = repo_path
        self.orchestrator = OrchestratorAgent()
        self.repo_reader = RepoReaderAgent()
        self.analyst = AnalystAgent()
        self.coder = CoderAgent()
        self.reviewer = ReviewerAgent()
        self.tester = TesterAgent()
        self.pr_manager = PRManagerAgent()

    # ── Phase 1 ──────────────────────────────────────────────────────────────

    async def run_planning(self, issue: str) -> Dict[str, Any]:
        """
        Orchestrator → RepoReader → Analyst (strict sequence, stops on first error).
        Returns the full AgentState dict; caller slims it before sending to the user.
        """
        log_pipeline_start(issue, self.repo_path)
        state = AgentState(issue=issue, repo_path=self.repo_path, status="pending")

        for agent in [self.orchestrator, self.repo_reader, self.analyst]:
            state = await agent.execute(state)
            if state.errors:
                state.status = "error"
                log_pipeline_end("error", state.model_dump())
                return state.model_dump()

        state.status = "planning_complete"
        log_pipeline_end("planning_complete", state.model_dump())
        return state.model_dump()

    # ── Phase 2 ──────────────────────────────────────────────────────────────

    async def run_execution(self, planning_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coder → Reviewer [retry] → Tester [retry] → PRManager (strict sequence).
        Accepts the slim dict from run_planning (or a user-edited version of it).

        Retry rules
        -----------
        Reviewer  : if any finding has severity=="error", loop Coder→Reviewer once.
        Tester    : if tests fail, loop Coder→Reviewer→Tester up to MAX_TEST_RETRIES.
        """
        state = AgentState(**{
            k: v for k, v in planning_state.items()
            if k in AgentState.model_fields
        })

        # ── 1. Coder ─────────────────────────────────────────────────────────
        state.status = "running:coder"
        print("[Pipeline] Step 1/4 — Coder")
        state = await self.coder.execute(state)
        if state.errors:
            state.status = "error"
            return state.model_dump()

        # ── 2. Reviewer (with one retry) ─────────────────────────────────────
        state.status = "running:reviewer"
        print("[Pipeline] Step 2/4 — Reviewer")
        state = await self.reviewer.execute(state)

        if self._has_error_findings(state) and not state.errors:
            print("[Pipeline]   ↺ Reviewer found errors → Coder retry 1")
            # Preserve first-pass findings so second Reviewer can diff against them
            state.prior_review_findings = list(state.review_findings)
            state.status = "running:coder-review-retry"
            state = await self.coder.execute(state)
            if state.errors:
                state.status = "error"
                return state.model_dump()
            state.status = "running:reviewer-retry"
            state = await self.reviewer.execute(state)

        if state.errors:
            state.status = "error"
            return state.model_dump()

        # ── 3. Tester (with up to MAX_TEST_RETRIES fix-cycles) ───────────────
        state.status = "running:tester"
        print("[Pipeline] Step 3/4 — Tester")
        for attempt in range(self.MAX_TEST_RETRIES + 1):
            state.test_iteration = attempt
            state.last_test_failure = ""        # clear before each tester run
            state = await self.tester.execute(state)

            if state.errors:
                state.status = "error"
                return state.model_dump()

            test_status = state.test_results.get("status", "skipped")
            if test_status != "failed":
                break

            if attempt >= self.MAX_TEST_RETRIES:
                print(f"[Pipeline]   Tests still failing after {self.MAX_TEST_RETRIES} retries — proceeding")
                break

            # Capture the full pytest output so the Coder knows exactly what broke
            failure_output = state.test_results.get("output", "")
            if state.test_results.get("errors"):
                failure_output += "\n" + state.test_results["errors"]
            state.last_test_failure = failure_output

            print(f"[Pipeline]   ↺ Tests FAILED (attempt {attempt + 1}/{self.MAX_TEST_RETRIES}) → Coder fix")
            state.status = f"running:coder-test-retry-{attempt + 1}"
            state = await self.coder.execute(state)
            if state.errors:
                state.status = "error"
                return state.model_dump()
            state.status = f"running:reviewer-test-retry-{attempt + 1}"
            state = await self.reviewer.execute(state)
            if state.errors:
                state.status = "error"
                return state.model_dump()
            state.status = "running:tester"

        # ── 4. PRManager ─────────────────────────────────────────────────────
        state.status = "running:pr_manager"
        print("[Pipeline] Step 4/4 — PRManager")
        state = await self.pr_manager.execute(state)

        state.status = "completed" if not state.errors else "error"
        log_pipeline_end(state.status, state.model_dump())
        return state.model_dump()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _has_error_findings(self, state: AgentState) -> bool:
        return any(f.get("severity") == "error" for f in state.review_findings)
