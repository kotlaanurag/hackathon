"""Analyst Agent - Reads repo structure and drafts implementation plan using LLM."""

import os
import re
import json
from typing import Dict, Any, List, Optional
from agents.base import BaseAgent, AgentState
from prompts import get_prompt
from model import get_llm


class AnalystAgent(BaseAgent):
    """
    The Analyst Agent using LLM-powered analysis:
    1. Uses repository context from RepoReader
    2. Understands the codebase structure and contents
    3. Uses LLM to create detailed implementation plans
    4. Identifies relevant files based on user's request
    """
    
    def __init__(self):
        super().__init__(
            name="Analyst",
            description="Analyzes repository and creates LLM-powered implementation plans"
        )
        # Load prompt from file
        self.prompt = get_prompt("analyst", default="")
        self.llm = get_llm()
        self.ignored_dirs = {'.git', 'node_modules', '__pycache__', 'venv', 'env', '.venv', 'dist', 'build'}
        self.code_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', '.cpp', '.c', '.h'}
    
    async def execute(self, state: AgentState) -> AgentState:
        """Analyze the repo and create an LLM-powered implementation plan."""
        import time
        start_time = time.time()
        
        # Log input
        self.log_input(state)
        self.log("Analyzing repository with LLM...", {"repo_path": state.repo_path})
        
        try:
            # Check if we have repo context from RepoReader
            repo_context = self._get_repo_context_from_messages(state)
            file_contents = self._get_file_contents_from_messages(state)
            
            if repo_context:
                self.log("Using repo context from RepoReader", {
                    "main_language": repo_context.get("main_language"),
                    "project_type": repo_context.get("project_type"),
                    "total_files": repo_context.get("total_files")
                })
            
            # Read repository structure
            if file_contents:
                repo_structure = {
                    "files": list(file_contents.keys()),
                    "file_count": len(file_contents)
                }
                self.log("Using file contents from RepoReader", {"file_count": len(file_contents)})
            else:
                repo_structure = self._read_repo_structure(state.repo_path)
                self.log("Repository structure read from disk", {"file_count": repo_structure.get("file_count", 0)})
            
            # Identify relevant files
            relevant_files = self._identify_relevant_files_with_context(
                repo_structure, 
                state.issue,
                file_contents
            )
            self.log("Relevant files identified", {"count": len(relevant_files), "files": relevant_files[:5]})
            
            # Use LLM to create implementation plan
            implementation_plan = await self._create_implementation_plan_with_llm(
                state.issue,
                repo_structure,
                relevant_files,
                repo_context,
                file_contents
            )
            
            state.implementation_plan = implementation_plan
            
            # Get files to modify from the plan
            files_to_create = implementation_plan.get("files_to_create", [])
            files_to_modify = implementation_plan.get("files_to_modify", relevant_files)
            
            # Combine them
            all_files = list(set(files_to_create + files_to_modify))
            state.files_to_modify = all_files if all_files else relevant_files
            
            state.current_agent = self.name
            state.messages.append({
                "agent": self.name,
                "action": "created_implementation_plan",
                "data": {
                    "repo_structure": repo_structure,
                    "relevant_files": relevant_files,
                    "suggested_new_files": files_to_create,
                    "plan": implementation_plan,
                    "repo_context": repo_context
                }
            })
            
            self.log(f"LLM implementation plan created with {len(state.files_to_modify)} files", {
                "files": state.files_to_modify
            })
            
            # Log output
            duration_ms = (time.time() - start_time) * 1000
            self.log_output(state, duration_ms)
            return state
            
        except Exception as e:
            self.log_error(e, {"repo_path": state.repo_path})
            state.errors.append(str(e))
            return state
    
    async def _create_implementation_plan_with_llm(
        self,
        issue: str,
        repo_structure: Dict,
        relevant_files: List[str],
        repo_context: Dict,
        file_contents: Dict
    ) -> Dict[str, Any]:
        """
        Use LLM to create a comprehensive implementation plan.
        
        This is the core LLM-powered planning method.
        """
        # Build the prompt for plan generation
        prompt = self._build_planning_prompt(
            issue=issue,
            repo_structure=repo_structure,
            relevant_files=relevant_files,
            repo_context=repo_context,
            file_contents=file_contents
        )
        
        try:
            # Call LLM to generate the plan
            response = await self.llm.generate(
                prompt=prompt,
                system_prompt=self.prompt,
                temperature=0.4
            )
            
            # Parse the response as JSON
            plan = self._parse_plan_response(response)
            
            self.log("LLM generated implementation plan", {
                "summary": plan.get("summary", "")[:100]
            })
            
            return plan
            
        except Exception as e:
            self.log(f"LLM planning failed: {e}")
            # Fallback to basic planning
            return self._create_fallback_plan(issue, relevant_files, repo_context)
    
    def _build_planning_prompt(
        self,
        issue: str,
        repo_structure: Dict,
        relevant_files: List[str],
        repo_context: Dict,
        file_contents: Dict
    ) -> str:
        """Build a comprehensive prompt for implementation planning."""
        
        prompt_parts = [
            "Create a detailed implementation plan for the following request.",
            "",
            "## User Request:",
            issue,
            "",
            "## Repository Context:",
            f"- Main Language: {repo_context.get('main_language', 'Unknown')}",
            f"- Project Type: {repo_context.get('project_type', 'Unknown')}",
            f"- Total Files: {len(repo_structure.get('files', []))}",
            ""
        ]
        
        if relevant_files:
            prompt_parts.append("## Potentially Relevant Files:")
            for f in relevant_files[:10]:
                prompt_parts.append(f"- {f}")
            prompt_parts.append("")
        
        # Include snippets of relevant file contents
        if file_contents:
            prompt_parts.append("## Existing Code Snippets:")
            for file_path in relevant_files[:5]:
                content = file_contents.get(file_path, "")
                if content and not content.startswith("["):
                    prompt_parts.append(f"\n### {file_path}:")
                    prompt_parts.append("```")
                    prompt_parts.append(content[:1500])
                    if len(content) > 1500:
                        prompt_parts.append("... (truncated)")
                    prompt_parts.append("```")
            prompt_parts.append("")
        
        prompt_parts.extend([
            "## Required Output (JSON format):",
            "Return a JSON object with the following structure:",
            "```json",
            "{",
            '  "summary": "Brief summary of the implementation plan",',
            '  "action_type": "feature|bugfix|refactor|enhancement",',
            '  "steps": [',
            '    {"step": 1, "action": "Description of step", "files": ["file1.py"]}',
            '  ],',
            '  "files_to_create": ["new_file1.py", "new_file2.py"],',
            '  "files_to_modify": ["existing_file.py"],',
            '  "dependencies": ["package1", "package2"],',
            '  "estimated_complexity": "low|medium|high",',
            '  "risks": ["potential risk 1", "potential risk 2"],',
            '  "testing_requirements": "Description of tests needed"',
            "}",
            "```",
            "",
            "Provide ONLY the JSON object, no additional text."
        ])
        
        return "\n".join(prompt_parts)
    
    def _parse_plan_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM response into a structured plan."""
        # Try to extract JSON from the response
        response = response.strip()
        
        # Remove markdown code blocks if present
        if response.startswith("```"):
            lines = response.split("\n")
            # Remove first and last lines (``` markers)
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response = "\n".join(lines)
        
        try:
            plan = json.loads(response)
            return plan
        except json.JSONDecodeError:
            # Try to find JSON within the response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            # Return a basic plan if parsing fails
            return {
                "summary": response[:200],
                "action_type": "enhancement",
                "steps": [{"step": 1, "action": "Implement the requested changes"}],
                "files_to_create": [],
                "files_to_modify": [],
                "dependencies": [],
                "estimated_complexity": "medium",
                "risks": [],
                "testing_requirements": "Add appropriate tests"
            }
    
    def _create_fallback_plan(
        self,
        issue: str,
        relevant_files: List[str],
        repo_context: Dict
    ) -> Dict[str, Any]:
        """Create a basic fallback plan when LLM fails."""
        return {
            "summary": f"Implementation plan for: {issue[:100]}",
            "action_type": self._detect_issue_type(issue),
            "steps": [
                {"step": 1, "action": "Analyze existing code", "files": relevant_files[:5]},
                {"step": 2, "action": "Implement requested changes"},
                {"step": 3, "action": "Add error handling"},
                {"step": 4, "action": "Write tests"},
                {"step": 5, "action": "Add documentation"}
            ],
            "files_to_create": self._suggest_new_files(issue),
            "files_to_modify": relevant_files,
            "dependencies": [],
            "estimated_complexity": "medium",
            "risks": [],
            "testing_requirements": "Add appropriate unit tests"
        }
    
    def _detect_issue_type(self, issue: str) -> str:
        """Detect the type of issue."""
        issue_lower = issue.lower()
        if any(word in issue_lower for word in ["bug", "fix", "error", "broken"]):
            return "bugfix"
        elif any(word in issue_lower for word in ["add", "create", "implement", "new"]):
            return "feature"
        elif any(word in issue_lower for word in ["refactor", "improve", "optimize"]):
            return "refactor"
        return "enhancement"
    
    def _suggest_new_files(self, issue: str) -> List[str]:
        """Suggest new files that might need to be created."""
        suggestions = []
        issue_lower = issue.lower()
        
        if "login" in issue_lower or "auth" in issue_lower:
            suggestions.extend(["auth.py", "auth_utils.py"])
        if "api" in issue_lower or "endpoint" in issue_lower:
            suggestions.extend(["routes.py", "handlers.py"])
        if "test" in issue_lower:
            suggestions.append("tests/test_feature.py")
        if "model" in issue_lower or "database" in issue_lower:
            suggestions.append("models.py")
            
        return suggestions
    
    def _get_repo_context_from_messages(self, state: AgentState) -> Dict[str, Any]:
        """Get repo context from RepoReader messages."""
        for msg in state.messages:
            if msg.get("agent") == "RepoReader" and msg.get("action") == "repo_loaded":
                return msg.get("data", {}).get("context_summary", {})
        return {}
    
    def _get_file_contents_from_messages(self, state: AgentState) -> Dict[str, str]:
        """Get file contents from RepoReader messages."""
        for msg in state.messages:
            if msg.get("agent") == "RepoReader" and msg.get("action") == "repo_loaded":
                return msg.get("data", {}).get("file_contents", {})
        return {}
    
    def _understand_user_intent(self, issue: str, repo_context: Dict, file_contents: Dict) -> Dict[str, Any]:
        """Understand what the user actually wants to change."""
        intent = {
            "raw_request": issue,
            "action_type": self._detect_action_type(issue),
            "target_file": self._extract_target_file(issue),  # Specific file user mentioned
            "target_areas": self._detect_target_areas(issue, file_contents),
            "affected_components": [],
            "scope": "unknown"
        }
        
        # Analyze scope based on issue text
        issue_lower = issue.lower()
        if any(word in issue_lower for word in ["all", "entire", "whole", "complete"]):
            intent["scope"] = "large"
        elif any(word in issue_lower for word in ["small", "minor", "quick", "simple"]):
            intent["scope"] = "small"
        else:
            intent["scope"] = "medium"
        
        # Identify affected components from file contents
        if file_contents:
            intent["affected_components"] = self._find_affected_components(issue, file_contents)
        
        return intent
    
    def _extract_target_file(self, issue: str) -> Optional[str]:
        """Extract a specific file name mentioned in the issue."""
        import re
        
        # Look for patterns like "in login.py", "to login.py", "file login.py", etc.
        patterns = [
            r'in\s+(\w+\.py)',
            r'to\s+(\w+\.py)',
            r'file\s+(\w+\.py)',
            r'(\w+\.py)\s+file',
            r'modify\s+(\w+\.py)',
            r'update\s+(\w+\.py)',
            r'edit\s+(\w+\.py)',
            r'change\s+(\w+\.py)',
            r'create\s+(\w+\.py)',
            r'add.*?(\w+\.py)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, issue.lower())
            if match:
                return match.group(1)
        
        return None
    
    def _detect_action_type(self, issue: str) -> str:
        """Detect what type of action the user wants."""
        issue_lower = issue.lower()
        
        if any(word in issue_lower for word in ["fix", "bug", "error", "broken", "issue"]):
            return "bugfix"
        elif any(word in issue_lower for word in ["add", "create", "new", "implement"]):
            return "feature"
        elif any(word in issue_lower for word in ["update", "modify", "change"]):
            return "modification"
        elif any(word in issue_lower for word in ["refactor", "improve", "optimize", "clean"]):
            return "refactor"
        elif any(word in issue_lower for word in ["remove", "delete"]):
            return "removal"
        else:
            return "enhancement"
    
    def _detect_target_areas(self, issue: str, file_contents: Dict) -> List[str]:
        """Detect which areas of the codebase are targeted."""
        targets = []
        issue_lower = issue.lower()
        
        # Common target patterns
        target_patterns = {
            "api": ["api", "endpoint", "route", "request", "response"],
            "authentication": ["auth", "login", "logout", "password", "token", "session"],
            "database": ["database", "db", "model", "query", "sql", "migration"],
            "frontend": ["ui", "frontend", "component", "view", "template", "page"],
            "testing": ["test", "spec", "unittest", "pytest"],
            "configuration": ["config", "setting", "env", "environment"],
            "documentation": ["doc", "readme", "documentation", "comment"]
        }
        
        for area, keywords in target_patterns.items():
            if any(kw in issue_lower for kw in keywords):
                targets.append(area)
        
        return targets
    
    def _find_affected_components(self, issue: str, file_contents: Dict) -> List[str]:
        """Find which components/files might be affected based on issue and file contents."""
        affected = []
        issue_lower = issue.lower()
        keywords = self._extract_keywords(issue_lower)
        
        for file_path, content in file_contents.items():
            if not content or content.startswith("["):  # Skip error entries
                continue
                
            content_lower = content.lower()
            
            # Check if any keywords appear in file content
            for keyword in keywords:
                if keyword in content_lower:
                    affected.append(file_path)
                    break
        
        return affected[:10]  # Limit to top 10
    
    def _identify_relevant_files_with_context(self, repo_structure: Dict, issue: str, file_contents: Dict) -> List[str]:
        """Identify files relevant to the issue using both structure and content."""
        relevant = []
        issue_lower = issue.lower()
        keywords = self._extract_keywords(issue_lower)
        
        # FIRST: Check if user explicitly mentioned a target file
        target_file = self._extract_target_file(issue)
        if target_file:
            # Find the target file in the repo structure
            for file_path in repo_structure.get("files", []):
                if file_path.lower().endswith(target_file.lower()):
                    relevant.append(file_path)
                    self.log(f"Target file identified from user request: {file_path}")
                    break
            
            # If not found in repo, add it as a new file to create
            if not relevant:
                relevant.append(target_file)
                self.log(f"Target file not found, will create: {target_file}")
        
        # Then, check file names for keyword matches
        for file_path in repo_structure.get("files", []):
            if file_path in relevant:
                continue  # Already added
            file_lower = file_path.lower()
            ext = os.path.splitext(file_path)[1]
            
            if ext in self.code_extensions:
                if any(kw in file_lower for kw in keywords):
                    relevant.append(file_path)
        
        # Then, search in file contents for more context
        if file_contents:
            for file_path, content in file_contents.items():
                if file_path in relevant:
                    continue  # Already added
                    
                if not content or content.startswith("["):
                    continue
                
                content_lower = content.lower()
                # Look for more specific matches in content
                for keyword in keywords:
                    if keyword in content_lower and file_path not in relevant:
                        relevant.append(file_path)
                        break
        
        # Include main entry points if nothing found
        if not relevant:
            for file_path in repo_structure.get("files", []):
                file_lower = file_path.lower()
                if any(entry in file_lower for entry in ['main', 'app', 'index', '__init__']):
                    relevant.append(file_path)
        
        return relevant[:15]  # Limit to 15 most relevant
    
    def _read_repo_structure(self, repo_path: str) -> Dict[str, Any]:
        """Read and return the repository structure (fallback method)."""
        structure = {
            "root": repo_path,
            "directories": [],
            "files": [],
            "file_count": 0,
            "dir_count": 0
        }
        
        if not repo_path or not os.path.exists(repo_path):
            return structure
        
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in self.ignored_dirs]
            
            rel_root = os.path.relpath(root, repo_path)
            if rel_root != ".":
                structure["directories"].append(rel_root)
                structure["dir_count"] += 1
            
            for file in files:
                rel_path = os.path.join(rel_root, file) if rel_root != "." else file
                structure["files"].append(rel_path)
                structure["file_count"] += 1
        
        return structure
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from text."""
        stopwords = {'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                     'can', 'need', 'to', 'of', 'in', 'for', 'on', 'with', 'at',
                     'by', 'from', 'as', 'into', 'through', 'during', 'before',
                     'after', 'above', 'below', 'between', 'under', 'again',
                     'further', 'then', 'once', 'and', 'but', 'or', 'nor', 'so',
                     'yet', 'both', 'each', 'few', 'more', 'most', 'other', 'some',
                     'such', 'no', 'not', 'only', 'own', 'same', 'than', 'too',
                     'very', 'just', 'create', 'add', 'implement', 'feature'}
        
        words = text.replace(',', ' ').replace('.', ' ').split()
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        return keywords[:10]
    
    def _draft_implementation_plan_with_context(
        self, 
        issue: str, 
        repo_structure: Dict, 
        relevant_files: List[str],
        repo_context: Dict,
        file_contents: Dict,
        user_intent: Dict
    ) -> Dict[str, Any]:
        """Draft a detailed implementation plan using full repository context."""
        
        # Analyze existing code patterns if we have file contents
        code_patterns = self._analyze_code_patterns(file_contents) if file_contents else {}
        
        return {
            "summary": f"Implementation plan for: {issue[:100]}",
            "user_intent": user_intent,
            "repository_context": {
                "main_language": repo_context.get("main_language", "Unknown"),
                "project_type": repo_context.get("project_type", "Unknown"),
                "total_files": repo_context.get("total_files", 0)
            },
            "code_patterns": code_patterns,
            "steps": self._generate_implementation_steps(issue, relevant_files, user_intent, file_contents),
            "estimated_files_to_create": self._suggest_new_files(issue, user_intent),
            "estimated_files_to_modify": relevant_files,
            "dependencies": self._identify_dependencies(issue, file_contents),
            "risks": self._identify_risks(user_intent, relevant_files),
            "file_analysis": self._analyze_relevant_files(relevant_files, file_contents)
        }
    
    def _analyze_code_patterns(self, file_contents: Dict) -> Dict[str, Any]:
        """Analyze coding patterns in the existing codebase."""
        patterns = {
            "has_tests": False,
            "has_types": False,
            "has_docstrings": False,
            "frameworks": [],
            "common_imports": []
        }
        
        for file_path, content in file_contents.items():
            if not content or content.startswith("["):
                continue
            
            # Check for tests
            if "test_" in file_path or "_test." in file_path or "tests/" in file_path:
                patterns["has_tests"] = True
            
            # Check for type hints (Python)
            if ": str" in content or ": int" in content or "-> " in content:
                patterns["has_types"] = True
            
            # Check for docstrings
            if '"""' in content or "'''" in content:
                patterns["has_docstrings"] = True
            
            # Detect frameworks
            if "fastapi" in content.lower():
                patterns["frameworks"].append("FastAPI")
            if "django" in content.lower():
                patterns["frameworks"].append("Django")
            if "flask" in content.lower():
                patterns["frameworks"].append("Flask")
            if "react" in content.lower():
                patterns["frameworks"].append("React")
        
        patterns["frameworks"] = list(set(patterns["frameworks"]))
        return patterns
    
    def _generate_implementation_steps(
        self, 
        issue: str, 
        relevant_files: List[str], 
        user_intent: Dict,
        file_contents: Dict
    ) -> List[Dict]:
        """Generate detailed implementation steps based on context."""
        steps = []
        action_type = user_intent.get("action_type", "enhancement")
        
        # Step 1: Analysis (already done)
        steps.append({
            "step": 1,
            "action": "Analyze existing code",
            "files": relevant_files[:5],
            "description": f"Review {len(relevant_files)} relevant files to understand current implementation"
        })
        
        # Step 2: Based on action type
        if action_type == "bugfix":
            steps.append({
                "step": 2,
                "action": "Identify bug location",
                "description": "Locate the source of the bug in identified files"
            })
            steps.append({
                "step": 3,
                "action": "Implement fix",
                "description": "Apply the necessary code changes to fix the issue"
            })
        elif action_type == "feature":
            steps.append({
                "step": 2,
                "action": "Design feature structure",
                "description": "Plan the new code structure and interfaces"
            })
            steps.append({
                "step": 3,
                "action": "Implement feature",
                "files": relevant_files,
                "description": "Write the new feature code"
            })
        else:
            steps.append({
                "step": 2,
                "action": "Modify existing code",
                "files": relevant_files,
                "description": "Make the required changes to existing files"
            })
        
        # Common final steps
        steps.append({
            "step": len(steps) + 1,
            "action": "Add error handling",
            "description": "Implement proper error handling and validation"
        })
        steps.append({
            "step": len(steps) + 1,
            "action": "Write/update tests",
            "description": "Create or update tests for the changes"
        })
        steps.append({
            "step": len(steps) + 1,
            "action": "Add documentation",
            "description": "Update docstrings and comments"
        })
        
        return steps
    
    def _suggest_new_files(self, issue: str, user_intent: Dict = None) -> List[str]:
        """Suggest new files that might need to be created."""
        suggestions = []
        issue_lower = issue.lower()
        target_areas = user_intent.get("target_areas", []) if user_intent else []
        
        if "login" in issue_lower or "auth" in issue_lower or "authentication" in target_areas:
            suggestions.extend(["auth.py", "auth_utils.py"])
        if "api" in issue_lower or "endpoint" in issue_lower or "api" in target_areas:
            suggestions.extend(["routes.py", "handlers.py"])
        if "test" in issue_lower or "testing" in target_areas:
            suggestions.append("tests/test_feature.py")
        if "model" in issue_lower or "database" in issue_lower or "database" in target_areas:
            suggestions.append("models.py")
        if "config" in issue_lower or "configuration" in target_areas:
            suggestions.append("config.py")
            
        return suggestions
    
    def _identify_dependencies(self, issue: str, file_contents: Dict) -> List[str]:
        """Identify any new dependencies that might be needed."""
        dependencies = []
        issue_lower = issue.lower()
        
        # Common dependency patterns
        dep_patterns = {
            "jwt": "PyJWT",
            "bcrypt": "bcrypt",
            "hash": "passlib",
            "email": "email-validator",
            "database": "sqlalchemy",
            "async": "asyncio",
            "http": "httpx",
            "redis": "redis",
            "celery": "celery"
        }
        
        for keyword, dep in dep_patterns.items():
            if keyword in issue_lower:
                dependencies.append(dep)
        
        return dependencies
    
    def _identify_risks(self, user_intent: Dict, relevant_files: List[str]) -> List[str]:
        """Identify potential risks with the implementation."""
        risks = []
        
        action_type = user_intent.get("action_type", "")
        scope = user_intent.get("scope", "")
        
        if len(relevant_files) > 10:
            risks.append("Large number of files affected - higher risk of regression")
        
        if scope == "large":
            risks.append("Large scope change - consider breaking into smaller PRs")
        
        if action_type == "refactor":
            risks.append("Refactoring may affect multiple components")
        
        target_areas = user_intent.get("target_areas", [])
        if "authentication" in target_areas:
            risks.append("Authentication changes require careful security review")
        if "database" in target_areas:
            risks.append("Database changes may require migrations")
        
        return risks
    
    def _analyze_relevant_files(self, relevant_files: List[str], file_contents: Dict) -> List[Dict]:
        """Provide analysis of each relevant file."""
        analysis = []
        
        for file_path in relevant_files[:10]:  # Limit to 10 files
            content = file_contents.get(file_path, "")
            
            if not content or content.startswith("["):
                continue
            
            lines = content.split('\n')
            
            # Extract key info
            imports = [l for l in lines[:30] if l.strip().startswith(('import ', 'from '))]
            classes = [l for l in lines if l.strip().startswith('class ')]
            functions = [l for l in lines if l.strip().startswith('def ') or l.strip().startswith('async def ')]
            
            analysis.append({
                "file": file_path,
                "lines": len(lines),
                "imports_count": len(imports),
                "classes_count": len(classes),
                "functions_count": len(functions),
                "classes": [c.split('(')[0].replace('class ', '').strip() for c in classes[:5]],
                "functions": [f.split('(')[0].replace('def ', '').replace('async def ', '').strip() for f in functions[:10]]
            })
        
        return analysis