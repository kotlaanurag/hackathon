"""Base Agent class that all agents inherit from."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel

from logger import agent_logger, log_action


class AgentState(BaseModel):
    """State that flows through the agent pipeline."""
    issue: str = ""
    repo_path: str = ""
    branch_name: str = ""
    repo_context: Dict[str, Any] = {}
    file_contents: Dict[str, str] = {}
    implementation_plan: Dict[str, Any] = {}
    files_to_modify: list = []
    code_changes: Dict[str, str] = {}
    git_diff: str = ""
    review_findings: list = []
    prior_review_findings: list = []
    test_files: Dict[str, str] = {}
    test_results: Dict[str, Any] = {}
    test_iteration: int = 0
    last_test_failure: str = ""   # pytest output from last failed run; fed to Coder on retry
    pr_url: str = ""
    status: str = "pending"
    errors: list = []
    current_agent: str = ""
    messages: list = []


class BaseAgent(ABC):
    """Abstract base class for all agents in the pipeline."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.logger = agent_logger

    @abstractmethod
    async def execute(self, state: AgentState) -> AgentState:
        pass

    # ── Logging helpers ──────────────────────────────────────────────────────

    def log(self, message: str, details: Optional[Dict] = None) -> None:
        print(f"[{self.name}] {message}")
        log_action(self.name, message, details)

    def log_input(self, state: AgentState) -> None:
        self.logger.log_agent_start(self.name, {
            "issue": state.issue[:200] if state.issue else "",
            "repo_path": state.repo_path,
            "status": state.status,
            "files_to_modify": state.files_to_modify,
            "current_agent": state.current_agent,
        })

    def log_output(self, state: AgentState, duration_ms: Optional[float] = None) -> None:
        self.logger.log_agent_end(self.name, {
            "status": state.status,
            "current_agent": state.current_agent,
            "files_modified": list(state.code_changes.keys()) if state.code_changes else [],
            "review_findings_count": len(state.review_findings),
            "test_files_count": len(state.test_files),
            "errors": state.errors,
        }, duration_ms)

    def log_error(self, error: Exception, context: Optional[Dict] = None) -> None:
        self.logger.log_agent_error(self.name, error, context)

    # ── Input sanitisation ───────────────────────────────────────────────────

    def _sanitize_input(self, text: str, max_len: int = 2000) -> str:
        """Sanitize user-supplied text before embedding it in LLM prompts.

        Prevents prompt-injection attacks where a crafted issue string could
        override system instructions (e.g. "Ignore all previous instructions…").
        """
        if not text:
            return ""
        text = text[:max_len]
        # Neutralise markdown code fences that could break prompt structure
        text = text.replace("```", "'''")
        # Strip null bytes and non-printable control chars (preserve newlines/tabs)
        text = "".join(ch for ch in text if ch in ("\n", "\t") or ch >= " ")
        return text
