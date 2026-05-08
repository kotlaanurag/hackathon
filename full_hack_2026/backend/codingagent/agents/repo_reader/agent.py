"""Repo Reader Agent - Fetches repo from GitHub and reads file contents with LLM analysis."""

import os
import subprocess
import tempfile
from typing import Dict, Any, List, Optional
from agents.base import BaseAgent, AgentState
from dotenv import load_dotenv
from prompts import get_prompt
from model import get_llm

load_dotenv()


class RepoReaderAgent(BaseAgent):
    """
    The Repo Reader Agent using LLM-powered analysis:
    1. Reads GitHub repo configuration from .env
    2. Clones the repository locally
    3. Reads and indexes all relevant files
    4. Uses LLM to create intelligent context summaries
    5. Provides file contents and structure to other agents
    """
    
    def __init__(self):
        super().__init__(
            name="RepoReader",
            description="Fetches repository and creates LLM-powered context analysis"
        )
        # Load prompt from file
        self.prompt = get_prompt("repo_reader", default="")
        self.llm = get_llm()
        self.github_token = os.getenv("GITHUB_TOKEN", "")
        self.repo_owner = os.getenv("GITHUB_REPO_OWNER", "")
        self.repo_name = os.getenv("GITHUB_REPO_NAME", "")
        self.base_branch = os.getenv("GITHUB_BASE_BRANCH", "main")
        
        # File types to read
        self.code_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', 
            '.cpp', '.c', '.h', '.cs', '.rb', '.php', '.swift', '.kt',
            '.scala', '.r', '.sql', '.sh', '.bash', '.yml', '.yaml',
            '.json', '.xml', '.html', '.css', '.scss', '.md', '.txt'
        }
        
        # Directories to ignore
        self.ignored_dirs = {
            '.git', 'node_modules', '__pycache__', 'venv', 'env', '.venv',
            'dist', 'build', '.next', '.nuxt', 'coverage', '.pytest_cache',
            '.mypy_cache', '.tox', 'eggs', '*.egg-info', '.eggs'
        }
        
        # Files to ignore
        self.ignored_files = {
            '.gitignore', '.dockerignore', 'package-lock.json', 'yarn.lock',
            'poetry.lock', 'Pipfile.lock', '*.pyc', '*.pyo', '*.so', '*.dll'
        }
        
        # Maximum file size to read (in bytes) - 500KB
        self.max_file_size = 500 * 1024
    
    async def execute(self, state: AgentState) -> AgentState:
        """
        Fetch the repository and read all relevant files.
        
        This is the entry point that:
        1. Clones the repo from GitHub (using .env config)
        2. Reads all code files
        3. Creates a comprehensive repo context
        4. Updates state with repo info for other agents
        """
        import time
        start_time = time.time()
        
        # Log input
        self.log_input(state)
        self.log("Starting repository fetch and analysis...", {
            "repo_owner": self.repo_owner,
            "repo_name": self.repo_name
        })
        
        try:
            # Step 1: Validate GitHub configuration
            if not self._validate_config():
                state.errors.append("GitHub configuration missing in .env file")
                return state
            
            # Step 2: Clone or update the repository
            repo_path = await self._clone_or_update_repo()
            if not repo_path:
                state.errors.append("Failed to clone repository")
                return state
            
            state.repo_path = repo_path
            self.log(f"Repository cloned to: {repo_path}")
            
            # Step 3: Read repository structure
            repo_structure = self._read_repo_structure(repo_path)
            self.log("Repository structure analyzed", {
                "total_files": repo_structure["file_count"],
                "total_dirs": repo_structure["dir_count"]
            })
            
            # Step 4: Read file contents
            file_contents = self._read_all_files(repo_path, repo_structure["files"])
            self.log(f"Read {len(file_contents)} files", {
                "files_read": list(file_contents.keys())[:10]
            })
            
            # Step 5: Create repo context summary
            repo_context = self._create_repo_context(repo_structure, file_contents)
            
            # Step 6: Update state with repo information
            state.current_agent = self.name
            state.status = "repo_loaded"
            state.messages.append({
                "agent": self.name,
                "action": "repo_loaded",
                "data": {
                    "repo_owner": self.repo_owner,
                    "repo_name": self.repo_name,
                    "repo_path": repo_path,
                    "branch": self.base_branch,
                    "structure": repo_structure,
                    "file_contents": file_contents,
                    "context_summary": repo_context
                }
            })
            
            self.log("Repository loaded successfully", {
                "files_indexed": len(file_contents),
                "repo_path": repo_path
            })
            
            # Log output
            duration_ms = (time.time() - start_time) * 1000
            self.log_output(state, duration_ms)
            return state
            
        except Exception as e:
            self.log_error(e, {
                "repo_owner": self.repo_owner,
                "repo_name": self.repo_name
            })
            state.errors.append(f"RepoReader error: {str(e)}")
            return state
    
    def _validate_config(self) -> bool:
        """Validate that all required GitHub configuration is present."""
        if not self.github_token:
            self.log("Missing GITHUB_TOKEN in .env")
            return False
        if not self.repo_owner:
            self.log("Missing GITHUB_REPO_OWNER in .env")
            return False
        if not self.repo_name:
            self.log("Missing GITHUB_REPO_NAME in .env")
            return False
        return True
    
    async def _clone_or_update_repo(self) -> Optional[str]:
        """Clone the repository or update if it already exists."""
        # Create a workspace directory for repos
        workspace_dir = os.path.join(os.getcwd(), ".repos")
        os.makedirs(workspace_dir, exist_ok=True)
        
        repo_dir = os.path.join(workspace_dir, self.repo_name)
        repo_url = f"https://{self.github_token}@github.com/{self.repo_owner}/{self.repo_name}.git"
        
        try:
            if os.path.exists(repo_dir):
                # Update existing repo
                self.log(f"Updating existing repository at {repo_dir}")
                result = subprocess.run(
                    ["git", "fetch", "--all"],
                    cwd=repo_dir,
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    self.log(f"Git fetch warning: {result.stderr}")
                
                # Checkout the base branch
                subprocess.run(
                    ["git", "checkout", self.base_branch],
                    cwd=repo_dir,
                    capture_output=True,
                    text=True
                )
                
                # Pull latest changes
                subprocess.run(
                    ["git", "pull", "origin", self.base_branch],
                    cwd=repo_dir,
                    capture_output=True,
                    text=True
                )
            else:
                # Clone the repository
                self.log(f"Cloning repository from GitHub...")
                result = subprocess.run(
                    ["git", "clone", "--branch", self.base_branch, repo_url, repo_dir],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    self.log(f"Git clone error: {result.stderr}")
                    return None
            
            return repo_dir
            
        except Exception as e:
            self.log(f"Error cloning/updating repository: {str(e)}")
            return None
    
    def _read_repo_structure(self, repo_path: str) -> Dict[str, Any]:
        """Read and return the repository structure."""
        structure = {
            "root": repo_path,
            "directories": [],
            "files": [],
            "file_count": 0,
            "dir_count": 0,
            "file_types": {}
        }
        
        if not repo_path or not os.path.exists(repo_path):
            return structure
        
        for root, dirs, files in os.walk(repo_path):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if d not in self.ignored_dirs and not d.startswith('.')]
            
            rel_root = os.path.relpath(root, repo_path)
            if rel_root != ".":
                structure["directories"].append(rel_root)
                structure["dir_count"] += 1
            
            for file in files:
                # Skip ignored files
                if file in self.ignored_files or file.startswith('.'):
                    continue
                    
                rel_path = os.path.join(rel_root, file) if rel_root != "." else file
                ext = os.path.splitext(file)[1].lower()
                
                structure["files"].append(rel_path)
                structure["file_count"] += 1
                
                # Track file types
                if ext:
                    structure["file_types"][ext] = structure["file_types"].get(ext, 0) + 1
        
        return structure
    
    def _read_all_files(self, repo_path: str, files: List[str]) -> Dict[str, str]:
        """Read contents of all relevant code files."""
        file_contents = {}
        
        for file_path in files:
            full_path = os.path.join(repo_path, file_path)
            ext = os.path.splitext(file_path)[1].lower()
            
            # Only read code files
            if ext not in self.code_extensions:
                continue
            
            # Skip large files
            try:
                file_size = os.path.getsize(full_path)
                if file_size > self.max_file_size:
                    file_contents[file_path] = f"[File too large: {file_size} bytes]"
                    continue
                
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    file_contents[file_path] = content
                    
            except Exception as e:
                file_contents[file_path] = f"[Error reading file: {str(e)}]"
        
        return file_contents
    
    def _create_repo_context(self, structure: Dict[str, Any], file_contents: Dict[str, str]) -> Dict[str, Any]:
        """Create a summary context of the repository for AI understanding."""
        context = {
            "repository": f"{self.repo_owner}/{self.repo_name}",
            "branch": self.base_branch,
            "total_files": structure["file_count"],
            "total_directories": structure["dir_count"],
            "file_types": structure["file_types"],
            "main_language": self._detect_main_language(structure["file_types"]),
            "project_type": self._detect_project_type(file_contents),
            "key_files": self._identify_key_files(file_contents),
            "dependencies": self._extract_dependencies(file_contents),
            "structure_summary": self._create_structure_summary(structure)
        }
        return context
    
    def _detect_main_language(self, file_types: Dict[str, int]) -> str:
        """Detect the main programming language of the project."""
        language_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.go': 'Go',
            '.rs': 'Rust',
            '.cpp': 'C++',
            '.c': 'C',
            '.cs': 'C#',
            '.rb': 'Ruby',
            '.php': 'PHP'
        }
        
        if not file_types:
            return "Unknown"
        
        # Find the most common code file type
        code_types = {k: v for k, v in file_types.items() if k in language_map}
        if not code_types:
            return "Unknown"
        
        main_ext = max(code_types, key=code_types.get)
        return language_map.get(main_ext, "Unknown")
    
    def _detect_project_type(self, file_contents: Dict[str, str]) -> str:
        """Detect the type of project based on config files."""
        # Check for common project indicators
        if "package.json" in file_contents:
            content = file_contents["package.json"]
            if "next" in content.lower():
                return "Next.js"
            elif "react" in content.lower():
                return "React"
            elif "vue" in content.lower():
                return "Vue.js"
            elif "express" in content.lower():
                return "Express.js"
            return "Node.js"
        
        if "requirements.txt" in file_contents or "setup.py" in file_contents:
            if "django" in str(file_contents).lower():
                return "Django"
            elif "flask" in str(file_contents).lower():
                return "Flask"
            elif "fastapi" in str(file_contents).lower():
                return "FastAPI"
            return "Python"
        
        if "pom.xml" in file_contents:
            return "Maven/Java"
        
        if "build.gradle" in file_contents:
            return "Gradle/Java"
        
        if "go.mod" in file_contents:
            return "Go"
        
        if "Cargo.toml" in file_contents:
            return "Rust"
        
        return "Unknown"
    
    def _identify_key_files(self, file_contents: Dict[str, str]) -> List[str]:
        """Identify key/important files in the project."""
        key_file_patterns = [
            'README', 'readme', 'CONTRIBUTING', 'LICENSE',
            'main', 'app', 'index', '__init__', 'server',
            'config', 'settings', 'setup', 'package.json',
            'requirements.txt', 'Dockerfile', 'docker-compose'
        ]
        
        key_files = []
        for file_path in file_contents.keys():
            file_name = os.path.basename(file_path).lower()
            file_base = os.path.splitext(file_name)[0]
            
            if any(pattern.lower() in file_base for pattern in key_file_patterns):
                key_files.append(file_path)
        
        return key_files[:20]  # Limit to 20 key files
    
    def _extract_dependencies(self, file_contents: Dict[str, str]) -> Dict[str, List[str]]:
        """Extract project dependencies from config files."""
        dependencies = {}
        
        # Python dependencies
        if "requirements.txt" in file_contents:
            try:
                reqs = file_contents["requirements.txt"]
                deps = [line.strip().split('==')[0].split('>=')[0].split('<=')[0] 
                       for line in reqs.split('\n') 
                       if line.strip() and not line.startswith('#')]
                dependencies["python"] = deps[:30]
            except:
                pass
        
        # Node.js dependencies
        if "package.json" in file_contents:
            try:
                import json
                pkg = json.loads(file_contents["package.json"])
                deps = list(pkg.get("dependencies", {}).keys())
                dev_deps = list(pkg.get("devDependencies", {}).keys())
                dependencies["node"] = (deps + dev_deps)[:30]
            except:
                pass
        
        return dependencies
    
    def _create_structure_summary(self, structure: Dict[str, Any]) -> str:
        """Create a text summary of the project structure."""
        summary_lines = [
            f"Repository: {self.repo_owner}/{self.repo_name}",
            f"Total Files: {structure['file_count']}",
            f"Total Directories: {structure['dir_count']}",
            "",
            "Directory Structure (top-level):"
        ]
        
        # Add top-level directories
        top_dirs = sorted(set(
            d.split(os.sep)[0] for d in structure["directories"] 
            if os.sep in d or d in structure["directories"]
        ))[:15]
        
        for d in top_dirs:
            summary_lines.append(f"  ├── {d}/")
        
        # Add top-level files
        top_files = sorted([f for f in structure["files"] if os.sep not in f])[:10]
        for f in top_files:
            summary_lines.append(f"  ├── {f}")
        
        return "\n".join(summary_lines)
    
    def get_file_content(self, state: AgentState, file_path: str) -> Optional[str]:
        """Get content of a specific file from the loaded repo."""
        for msg in state.messages:
            if msg.get("agent") == self.name and msg.get("action") == "repo_loaded":
                file_contents = msg.get("data", {}).get("file_contents", {})
                return file_contents.get(file_path)
        return None
    
    def get_repo_context(self, state: AgentState) -> Optional[Dict[str, Any]]:
        """Get the repository context from state."""
        for msg in state.messages:
            if msg.get("agent") == self.name and msg.get("action") == "repo_loaded":
                return msg.get("data", {}).get("context_summary")
        return None
