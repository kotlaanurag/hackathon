"""Base Agent class that all agents inherit from."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel

# Import the centralized logger
from logger import agent_logger, log_action


class AgentState(BaseModel):
    """Base state that flows through the agent pipeline."""
    issue: str = ""
    repo_path: str = ""
    branch_name: str = ""
    repo_context: Dict[str, Any] = {}  # Context summary from RepoReader
    file_contents: Dict[str, str] = {}  # File contents from RepoReader
    implementation_plan: Dict[str, Any] = {}
    files_to_modify: list = []
    code_changes: Dict[str, str] = {}
    git_diff: str = ""
    review_findings: list = []
    test_files: Dict[str, str] = {}
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
        """Execute the agent's main logic."""
        pass
    
    def log(self, message: str, details: Optional[Dict] = None):
        """Log a message from this agent."""
        print(f"[{self.name}] {message}")
        log_action(self.name, message, details)
    
    def log_input(self, state: AgentState):
        """Log the input state for this agent."""
        self.logger.log_agent_start(self.name, {
            "issue": state.issue[:200] if state.issue else "",
            "repo_path": state.repo_path,
            "status": state.status,
            "files_to_modify": state.files_to_modify,
            "current_agent": state.current_agent
        })
    
    def log_output(self, state: AgentState, duration_ms: Optional[float] = None):
        """Log the output state from this agent."""
        self.logger.log_agent_end(self.name, {
            "status": state.status,
            "current_agent": state.current_agent,
            "files_modified": list(state.code_changes.keys()) if state.code_changes else [],
            "review_findings_count": len(state.review_findings),
            "test_files_count": len(state.test_files),
            "errors": state.errors
        }, duration_ms)
    
    def log_error(self, error: Exception, context: Optional[Dict] = None):
        """Log an error from this agent."""
        self.logger.log_agent_error(self.name, error, context)
