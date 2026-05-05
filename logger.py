"""
Centralized Logging Module for Multi-Agent Pipeline

This module provides comprehensive logging for all agents,
tracking inputs, outputs, and execution flow.
"""

import os
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from functools import wraps
from pathlib import Path

# Create logs directory if it doesn't exist
LOGS_DIR = Path(__file__).parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Log file paths
MAIN_LOG_FILE = LOGS_DIR / "pipeline.log"
AGENT_LOG_FILE = LOGS_DIR / "agents.log"
JSON_LOG_FILE = LOGS_DIR / "agents.jsonl"


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    AGENT_COLORS = {
        'Orchestrator': '\033[94m',  # Light Blue
        'Analyst': '\033[95m',       # Light Magenta
        'Coder': '\033[96m',         # Light Cyan
        'Reviewer': '\033[93m',      # Light Yellow
        'Tester': '\033[92m',        # Light Green
        'PRManager': '\033[91m',     # Light Red
    }
    
    def format(self, record):
        # Add color based on level
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        
        # Add agent color if available
        if hasattr(record, 'agent_name') and record.agent_name in self.AGENT_COLORS:
            agent_color = self.AGENT_COLORS[record.agent_name]
            record.agent_name = f"{agent_color}{record.agent_name}{self.COLORS['RESET']}"
        
        return super().format(record)


class AgentLogger:
    """
    Centralized logger for all agents in the pipeline.
    
    Features:
    - Console output with colors
    - File logging (plain text)
    - JSON Lines logging for structured data
    - Agent-specific log filtering
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._setup_loggers()
        self.execution_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _setup_loggers(self):
        """Set up all loggers."""
        # Main logger for console and file
        self.logger = logging.getLogger("AgentPipeline")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []  # Clear existing handlers
        
        # Console handler with colors
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_format = ColoredFormatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
        
        # File handler for detailed logs
        file_handler = logging.FileHandler(MAIN_LOG_FILE, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        self.logger.addHandler(file_handler)
        
        # Agent-specific logger
        self.agent_logger = logging.getLogger("Agents")
        self.agent_logger.setLevel(logging.DEBUG)
        self.agent_logger.handlers = []
        
        agent_file_handler = logging.FileHandler(AGENT_LOG_FILE, encoding='utf-8')
        agent_file_handler.setLevel(logging.DEBUG)
        agent_format = logging.Formatter(
            '%(asctime)s | %(levelname)s | [%(agent_name)s] | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        agent_file_handler.setFormatter(agent_format)
        self.agent_logger.addHandler(agent_file_handler)
    
    def _serialize_value(self, value: Any) -> Any:
        """Serialize a value for JSON logging."""
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._serialize_value(v) for v in value]
        elif hasattr(value, '__dict__'):
            return self._serialize_value(vars(value))
        elif isinstance(value, (str, int, float, bool, type(None))):
            return value
        else:
            return str(value)
    
    def _log_to_json(self, data: Dict[str, Any]):
        """Append a log entry to the JSON Lines file."""
        try:
            serialized = self._serialize_value(data)
            with open(JSON_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(serialized) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to write JSON log: {e}")
    
    def log_agent_start(self, agent_name: str, input_data: Any):
        """Log when an agent starts execution."""
        timestamp = datetime.now().isoformat()
        
        # Console/File log
        self.logger.info(f"[{agent_name}] ▶ Starting execution")
        
        # Detailed agent log
        extra = {'agent_name': agent_name}
        self.agent_logger.info(f"Starting execution", extra=extra)
        self.agent_logger.debug(f"Input: {self._truncate(str(input_data), 500)}", extra=extra)
        
        # JSON log
        self._log_to_json({
            "timestamp": timestamp,
            "execution_id": self.execution_id,
            "agent": agent_name,
            "event": "start",
            "input": self._serialize_value(input_data)
        })
    
    def log_agent_end(self, agent_name: str, output_data: Any, duration_ms: Optional[float] = None):
        """Log when an agent completes execution."""
        timestamp = datetime.now().isoformat()
        
        duration_str = f" ({duration_ms:.2f}ms)" if duration_ms else ""
        
        # Console/File log
        self.logger.info(f"[{agent_name}] ✓ Completed{duration_str}")
        
        # Detailed agent log
        extra = {'agent_name': agent_name}
        self.agent_logger.info(f"Completed execution{duration_str}", extra=extra)
        self.agent_logger.debug(f"Output: {self._truncate(str(output_data), 500)}", extra=extra)
        
        # JSON log
        self._log_to_json({
            "timestamp": timestamp,
            "execution_id": self.execution_id,
            "agent": agent_name,
            "event": "end",
            "duration_ms": duration_ms,
            "output": self._serialize_value(output_data)
        })
    
    def log_agent_error(self, agent_name: str, error: Exception, context: Optional[Dict] = None):
        """Log an agent error."""
        timestamp = datetime.now().isoformat()
        
        # Console/File log
        self.logger.error(f"[{agent_name}] ✗ Error: {str(error)}")
        
        # Detailed agent log
        extra = {'agent_name': agent_name}
        self.agent_logger.error(f"Error: {str(error)}", extra=extra)
        if context:
            self.agent_logger.debug(f"Context: {context}", extra=extra)
        
        # JSON log
        self._log_to_json({
            "timestamp": timestamp,
            "execution_id": self.execution_id,
            "agent": agent_name,
            "event": "error",
            "error": str(error),
            "error_type": type(error).__name__,
            "context": self._serialize_value(context) if context else None
        })
    
    def log_agent_action(self, agent_name: str, action: str, details: Optional[Dict] = None):
        """Log a specific action within an agent."""
        timestamp = datetime.now().isoformat()
        
        # Console/File log
        self.logger.info(f"[{agent_name}] → {action}")
        
        # Detailed agent log
        extra = {'agent_name': agent_name}
        self.agent_logger.info(f"Action: {action}", extra=extra)
        if details:
            self.agent_logger.debug(f"Details: {details}", extra=extra)
        
        # JSON log
        self._log_to_json({
            "timestamp": timestamp,
            "execution_id": self.execution_id,
            "agent": agent_name,
            "event": "action",
            "action": action,
            "details": self._serialize_value(details) if details else None
        })
    
    def log_pipeline_start(self, issue: str, repo_path: str):
        """Log when the pipeline starts."""
        self.execution_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamp = datetime.now().isoformat()
        
        self.logger.info("=" * 60)
        self.logger.info("Pipeline Started")
        self.logger.info(f"Issue: {self._truncate(issue, 100)}")
        self.logger.info(f"Repo: {repo_path}")
        self.logger.info("=" * 60)
        
        self._log_to_json({
            "timestamp": timestamp,
            "execution_id": self.execution_id,
            "event": "pipeline_start",
            "issue": issue,
            "repo_path": repo_path
        })
    
    def log_pipeline_end(self, status: str, result: Optional[Dict] = None):
        """Log when the pipeline ends."""
        timestamp = datetime.now().isoformat()
        
        self.logger.info("=" * 60)
        self.logger.info(f"Pipeline Completed - Status: {status}")
        self.logger.info("=" * 60)
        
        self._log_to_json({
            "timestamp": timestamp,
            "execution_id": self.execution_id,
            "event": "pipeline_end",
            "status": status,
            "result": self._serialize_value(result) if result else None
        })
    
    def log_state_transition(self, from_agent: str, to_agent: str, state_summary: Optional[Dict] = None):
        """Log state transition between agents."""
        timestamp = datetime.now().isoformat()
        
        self.logger.info(f"State Transition: {from_agent} → {to_agent}")
        
        self._log_to_json({
            "timestamp": timestamp,
            "execution_id": self.execution_id,
            "event": "state_transition",
            "from_agent": from_agent,
            "to_agent": to_agent,
            "state_summary": self._serialize_value(state_summary) if state_summary else None
        })
    
    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to max length."""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."
    
    def get_logs(self, agent_name: Optional[str] = None, limit: int = 100) -> list:
        """
        Read logs from the JSON file.
        
        Args:
            agent_name: Filter by agent name (optional)
            limit: Maximum number of entries to return
        
        Returns:
            List of log entries
        """
        logs = []
        try:
            with open(JSON_LOG_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if agent_name is None or entry.get("agent") == agent_name:
                            logs.append(entry)
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            pass
        
        return logs[-limit:]
    
    def clear_logs(self):
        """Clear all log files."""
        for log_file in [MAIN_LOG_FILE, AGENT_LOG_FILE, JSON_LOG_FILE]:
            try:
                open(log_file, 'w').close()
            except Exception:
                pass


# Global logger instance
agent_logger = AgentLogger()


def log_agent_execution(func):
    """
    Decorator to automatically log agent execution.
    
    Usage:
        @log_agent_execution
        async def execute(self, state: AgentState) -> AgentState:
            ...
    """
    @wraps(func)
    async def wrapper(self, state, *args, **kwargs):
        import time
        
        agent_name = getattr(self, 'name', self.__class__.__name__)
        
        # Log start
        agent_logger.log_agent_start(agent_name, {
            "issue": state.issue,
            "status": state.status,
            "current_agent": state.current_agent
        })
        
        start_time = time.time()
        
        try:
            # Execute the agent
            result = await func(self, state, *args, **kwargs)
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Log end
            agent_logger.log_agent_end(agent_name, {
                "status": result.status,
                "files_modified": len(result.code_changes),
                "errors": result.errors
            }, duration_ms)
            
            return result
            
        except Exception as e:
            agent_logger.log_agent_error(agent_name, e, {
                "issue": state.issue,
                "status": state.status
            })
            raise
    
    return wrapper


# Convenience functions
def log_start(agent_name: str, input_data: Any):
    """Log agent start."""
    agent_logger.log_agent_start(agent_name, input_data)


def log_end(agent_name: str, output_data: Any, duration_ms: Optional[float] = None):
    """Log agent end."""
    agent_logger.log_agent_end(agent_name, output_data, duration_ms)


def log_error(agent_name: str, error: Exception, context: Optional[Dict] = None):
    """Log agent error."""
    agent_logger.log_agent_error(agent_name, error, context)


def log_action(agent_name: str, action: str, details: Optional[Dict] = None):
    """Log agent action."""
    agent_logger.log_agent_action(agent_name, action, details)


def log_pipeline_start(issue: str, repo_path: str):
    """Log pipeline start."""
    agent_logger.log_pipeline_start(issue, repo_path)


def log_pipeline_end(status: str, result: Optional[Dict] = None):
    """Log pipeline end."""
    agent_logger.log_pipeline_end(status, result)
