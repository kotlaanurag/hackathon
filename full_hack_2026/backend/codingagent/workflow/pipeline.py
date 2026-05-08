"""Agent Pipeline - Orchestrates the multi-agent workflow using LangGraph."""

from typing import Dict, Any, Literal, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

from agents.base import AgentState
from agents.orchestrator.agent import OrchestratorAgent
from agents.repo_reader.agent import RepoReaderAgent
from agents.analyst.agent import AnalystAgent
from agents.coder.agent import CoderAgent
from agents.reviewer.agent import ReviewerAgent
from agents.tester.agent import TesterAgent
from agents.pr_manager.agent import PRManagerAgent
from logger import agent_logger, log_pipeline_start, log_pipeline_end


class WorkflowState(TypedDict):
    """State that flows through the LangGraph workflow."""
    issue: str
    repo_path: str
    branch_name: str
    repo_context: Dict[str, Any]
    file_contents: Dict[str, str]
    implementation_plan: Dict[str, Any]
    files_to_modify: list
    code_changes: Dict[str, str]
    git_diff: str
    review_findings: list
    test_files: Dict[str, str]
    test_results: Dict[str, Any]
    test_iteration: int
    pr_url: str
    status: str
    errors: list
    current_agent: str
    messages: list


class AgentPipeline:
    """
    Main pipeline that orchestrates all agents in the development workflow.
    
    Workflow:
    1. Orchestrator parses requirements
    2. RepoReader fetches and reads the GitHub repo from .env
    3. Analyst creates implementation plan based on repo context
    4. Coder implements changes
    5. Reviewer reviews code
    6. Tester creates tests
    7. PR Manager creates and merges PR
    """
    
    def __init__(self, repo_path: str = ""):
        self.repo_path = repo_path
        
        # Initialize all agents
        self.orchestrator = OrchestratorAgent()
        self.repo_reader = RepoReaderAgent()
        self.analyst = AnalystAgent()
        self.coder = CoderAgent()
        self.reviewer = ReviewerAgent()
        self.tester = TesterAgent()
        self.pr_manager = PRManagerAgent()
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow."""
        
        # Create the state graph
        workflow = StateGraph(WorkflowState)
        
        # Add nodes for each agent
        workflow.add_node("orchestrate", self._orchestrate_node)
        workflow.add_node("read_repo", self._read_repo_node)
        workflow.add_node("analyze", self._analyze_node)
        workflow.add_node("code", self._code_node)
        workflow.add_node("review", self._review_node)
        workflow.add_node("test", self._test_node)
        workflow.add_node("create_pr", self._create_pr_node)
        workflow.add_node("handle_error", self._handle_error_node)
        
        # Set entry point
        workflow.set_entry_point("orchestrate")
        
        # Add edges - Orchestrator -> RepoReader -> Analyst -> ...
        workflow.add_conditional_edges(
            "orchestrate",
            self._route_from_orchestrator,
            {
                "read_repo": "read_repo",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "read_repo",
            self._route_from_repo_reader,
            {
                "analyze": "analyze",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "analyze",
            self._route_from_analyst,
            {
                "code": "code",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "code",
            self._route_from_coder,
            {
                "review": "review",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "review",
            self._route_from_reviewer,
            {
                "test": "test",
                "code": "code",  # If changes requested, go back to coder
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "test",
            self._route_from_tester,
            {
                "create_pr": "create_pr",
                "code": "code",       # test failures → fix code and retry
                "error": "handle_error"
            }
        )
        
        workflow.add_edge("create_pr", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile()
    
    async def _orchestrate_node(self, state: WorkflowState) -> WorkflowState:
        """Orchestrator node - parses requirements."""
        agent_state = self._to_agent_state(state)
        result = await self.orchestrator.execute(agent_state)
        return self._from_agent_state(result, state)
    
    async def _read_repo_node(self, state: WorkflowState) -> WorkflowState:
        """RepoReader node - fetches and reads repository from GitHub."""
        agent_state = self._to_agent_state(state)
        result = await self.repo_reader.execute(agent_state)
        updated_state = self._from_agent_state(result, state)
        
        # Extract repo context and file contents from messages
        for msg in result.messages:
            if msg.get("agent") == "RepoReader" and msg.get("action") == "repo_loaded":
                data = msg.get("data", {})
                updated_state["repo_context"] = data.get("context_summary", {})
                updated_state["file_contents"] = data.get("file_contents", {})
                updated_state["repo_path"] = data.get("repo_path", "")
                break
        
        return updated_state
    
    async def _analyze_node(self, state: WorkflowState) -> WorkflowState:
        """Analyst node - creates implementation plan."""
        agent_state = self._to_agent_state(state)
        result = await self.analyst.execute(agent_state)
        return self._from_agent_state(result, state)
    
    async def _code_node(self, state: WorkflowState) -> WorkflowState:
        """Coder node - implements changes."""
        agent_state = self._to_agent_state(state)
        result = await self.coder.execute(agent_state)
        return self._from_agent_state(result, state)
    
    async def _review_node(self, state: WorkflowState) -> WorkflowState:
        """Reviewer node - reviews code changes."""
        agent_state = self._to_agent_state(state)
        result = await self.reviewer.execute(agent_state)
        return self._from_agent_state(result, state)
    
    async def _test_node(self, state: WorkflowState) -> WorkflowState:
        """Tester node - creates and runs tests."""
        agent_state = self._to_agent_state(state)
        result = await self.tester.execute(agent_state)
        return self._from_agent_state(result, state)
    
    async def _create_pr_node(self, state: WorkflowState) -> WorkflowState:
        """PR Manager node - creates and manages PR."""
        agent_state = self._to_agent_state(state)
        result = await self.pr_manager.execute(agent_state)
        return self._from_agent_state(result, state)
    
    async def _handle_error_node(self, state: WorkflowState) -> WorkflowState:
        """Handle errors in the workflow."""
        state["status"] = "error"
        state["messages"].append({
            "agent": "ErrorHandler",
            "action": "error_handled",
            "data": {"errors": state["errors"]}
        })
        return state
    
    def _route_from_orchestrator(self, state: WorkflowState) -> Literal["read_repo", "error"]:
        """Route from orchestrator to repo reader."""
        if state.get("errors"):
            return "error"
        return "read_repo"
    
    def _route_from_repo_reader(self, state: WorkflowState) -> Literal["analyze", "error"]:
        """Route from repo reader to analyst."""
        if state.get("errors"):
            return "error"
        if not state.get("repo_path"):
            return "error"
        return "analyze"
    
    def _route_from_analyst(self, state: WorkflowState) -> Literal["code", "error"]:
        """Route from analyst to next step."""
        if state.get("errors"):
            return "error"
        if not state.get("implementation_plan"):
            return "error"
        return "code"
    
    def _route_from_coder(self, state: WorkflowState) -> Literal["review", "error"]:
        """Route from coder to next step."""
        if state.get("errors"):
            return "error"
        return "review"
    
    def _route_from_reviewer(self, state: WorkflowState) -> Literal["test", "code", "error"]:
        """Route from reviewer to next step. Loop back to coder when errors are found."""
        if state.get("errors"):
            return "error"
        for finding in state.get("review_findings", []):
            if finding.get("severity") == "error":
                return "code"
        return "test"
    
    MAX_TEST_ITERATIONS = 2

    def _route_from_tester(self, state: WorkflowState) -> Literal["create_pr", "code", "error"]:
        """Route from tester: loop back to coder on failures up to MAX_TEST_ITERATIONS."""
        if state.get("errors"):
            return "error"
        test_status = state.get("test_results", {}).get("status", "skipped")
        if test_status == "failed" and state.get("test_iteration", 0) <= self.MAX_TEST_ITERATIONS:
            return "code"
        return "create_pr"
    
    def _to_agent_state(self, workflow_state: WorkflowState) -> AgentState:
        """Convert workflow state to agent state."""
        return AgentState(
            issue=workflow_state.get("issue", ""),
            repo_path=workflow_state.get("repo_path", self.repo_path),
            branch_name=workflow_state.get("branch_name", ""),
            repo_context=workflow_state.get("repo_context", {}),
            file_contents=workflow_state.get("file_contents", {}),
            implementation_plan=workflow_state.get("implementation_plan", {}),
            files_to_modify=workflow_state.get("files_to_modify", []),
            code_changes=workflow_state.get("code_changes", {}),
            git_diff=workflow_state.get("git_diff", ""),
            review_findings=workflow_state.get("review_findings", []),
            test_files=workflow_state.get("test_files", {}),
            test_results=workflow_state.get("test_results", {}),
            test_iteration=workflow_state.get("test_iteration", 0),
            pr_url=workflow_state.get("pr_url", ""),
            status=workflow_state.get("status", "pending"),
            errors=workflow_state.get("errors", []),
            current_agent=workflow_state.get("current_agent", ""),
            messages=workflow_state.get("messages", [])
        )
    
    def _from_agent_state(self, agent_state: AgentState, original_state: WorkflowState) -> WorkflowState:
        """Convert agent state back to workflow state."""
        return {
            "issue": agent_state.issue,
            "repo_path": agent_state.repo_path,
            "branch_name": agent_state.branch_name,
            "repo_context": original_state.get("repo_context", {}),
            "file_contents": original_state.get("file_contents", {}),
            "implementation_plan": agent_state.implementation_plan,
            "files_to_modify": agent_state.files_to_modify,
            "code_changes": agent_state.code_changes,
            "git_diff": agent_state.git_diff,
            "review_findings": agent_state.review_findings,
            "test_files": agent_state.test_files,
            "test_results": agent_state.test_results,
            "test_iteration": agent_state.test_iteration,
            "pr_url": agent_state.pr_url,
            "status": agent_state.status,
            "errors": agent_state.errors,
            "current_agent": agent_state.current_agent,
            "messages": agent_state.messages
        }
    
    async def run(self, issue: str) -> Dict[str, Any]:
        """
        Run the full development pipeline for an issue.
        
        Args:
            issue: The issue or feature request to implement
            
        Returns:
            Final workflow state with results
        """
        # Log pipeline start
        log_pipeline_start(issue, self.repo_path)
        
        # Initialize state with new repo fields
        initial_state: WorkflowState = {
            "issue": issue,
            "repo_path": self.repo_path,
            "branch_name": "",
            "repo_context": {},
            "file_contents": {},
            "implementation_plan": {},
            "files_to_modify": [],
            "code_changes": {},
            "git_diff": "",
            "review_findings": [],
            "test_files": {},
            "test_results": {},
            "test_iteration": 0,
            "pr_url": "",
            "status": "pending",
            "errors": [],
            "current_agent": "",
            "messages": []
        }
        
        # Run the workflow
        try:
            result = await self.workflow.ainvoke(initial_state)
            log_pipeline_end(result.get("status", "completed"), result)
            return result
        except Exception as e:
            error_result = {
                **initial_state,
                "status": "error",
                "errors": [str(e)]
            }
            log_pipeline_end("error", error_result)
            return error_result
    
    async def run_planning(self, issue: str) -> Dict[str, Any]:
        """
        Phase 1 — Orchestrator → RepoReader → Analyst.

        Returns the full AgentState dict (pass it unchanged to run_execution).
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

    async def run_execution(self, planning_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 2 — Coder → Reviewer (→ Coder retry on errors) → Tester (→ Coder retry on failures, max 2) → PRManager.

        Accepts the dict returned by run_planning as input.
        """
        state = AgentState(**{k: v for k, v in planning_state.items() if k in AgentState.model_fields})

        # ── Coder ────────────────────────────────────────────────────────────
        state = await self.coder.execute(state)
        if state.errors:
            state.status = "error"
            return state.model_dump()

        # ── Reviewer — one retry if error-severity findings exist ─────────
        state = await self.reviewer.execute(state)
        if any(f.get("severity") == "error" for f in state.review_findings) and not state.errors:
            print("[Pipeline] Reviewer found errors — looping back to Coder (retry 1)")
            state = await self.coder.execute(state)
            state = await self.reviewer.execute(state)

        if state.errors:
            state.status = "error"
            return state.model_dump()

        # ── Tester — loop back to Coder up to MAX_TEST_ITERATIONS on failure ─
        for test_iter in range(self.MAX_TEST_ITERATIONS + 1):
            state = await self.tester.execute(state)
            if state.errors:
                state.status = "error"
                return state.model_dump()

            test_status = state.test_results.get("status", "skipped")
            if test_status != "failed" or test_iter >= self.MAX_TEST_ITERATIONS:
                # Tests passed, were skipped/errored, or we've exhausted retries
                if test_status == "failed":
                    print(
                        f"[Pipeline] Tests still failing after {self.MAX_TEST_ITERATIONS} "
                        "retries — proceeding to PR"
                    )
                break

            # Tests failed and retries remain — fix the code and try again
            failed_tests = state.test_results.get("failed_tests", [])
            error_messages = state.test_results.get("error_messages", [])
            print(
                f"[Pipeline] Tests FAILED (iteration {test_iter + 1}/{self.MAX_TEST_ITERATIONS}) "
                "— looping back to Coder with failure details"
            )
            if failed_tests:
                print(f"[Pipeline] Failed tests: {', '.join(failed_tests[:5])}")
            if error_messages:
                print(f"[Pipeline] Errors: {error_messages[0][:100]}...")
            
            state = await self.coder.execute(state)
            if state.errors:
                state.status = "error"
                return state.model_dump()
            state = await self.reviewer.execute(state)
            if state.errors:
                state.status = "error"
                return state.model_dump()

        # ── PR Manager ───────────────────────────────────────────────────────
        state = await self.pr_manager.execute(state)

        state.status = "completed" if not state.errors else "error"
        log_pipeline_end(state.status, state.model_dump())
        return state.model_dump()

    def get_workflow_visualization(self) -> str:
        """Get a visual representation of the workflow."""
        return """
        ┌─────────────────┐
        │   Orchestrator  │
        │  (Parse Issue)  │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │   RepoReader    │
        │ (Fetch GitHub)  │
        │ (Read Files)    │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │    Analyst      │
        │ (Understand     │
        │  Context &      │
        │  Create Plan)   │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │     Coder       │
        │ (Implement)     │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │    Reviewer     │◄──────┐
        │ (Review Code)   │       │
        └────────┬────────┘       │
                 │          (Changes
        ┌────────▼────────┐  Requested)
        │     Tester      │       │
        │ (Create Tests)  │       │
        └────────┬────────┘       │
                 │                │
        ┌────────▼────────┐       │
        │   PR Manager    │───────┘
        │  (Create PR)    │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │      END        │
        │  (Auto Merge)   │
        └─────────────────┘
        """
