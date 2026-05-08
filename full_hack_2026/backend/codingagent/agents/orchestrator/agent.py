"""Orchestrator Agent - Coordinates the entire development pipeline with LLM."""

import json
from typing import Dict, Any
from agents.base import BaseAgent, AgentState
from prompts import get_prompt
from model import get_llm


class OrchestratorAgent(BaseAgent):
    """
    The Orchestrator Agent using LLM-powered coordination:
    1. Uses LLM to parse and understand issues/requirements
    2. Delegates to Analyst for implementation planning
    3. Delegates to Coder for code changes
    4. Delegates to Reviewer for code review
    5. Delegates to Tester for test creation
    6. Creates PR via PR Manager
    """
    
    def __init__(self):
        super().__init__(
            name="Orchestrator",
            description="Coordinates the development pipeline using LLM-powered analysis"
        )
        # Load prompt from file
        self.prompt = get_prompt("orchestrator", default="")
        self.llm = get_llm()
        self.workflow_stages = [
            "analyze",
            "code", 
            "review",
            "test",
            "create_pr"
        ]
    
    async def execute(self, state: AgentState) -> AgentState:
        """Parse the issue using LLM and prepare the state for the pipeline."""
        import time
        start_time = time.time()
        
        # Log input
        self.log_input(state)
        self.log(f"Received issue: {state.issue[:100]}...", {"issue_length": len(state.issue)})
        
        try:
            # Use LLM to parse and understand the requirements
            parsed_requirements = await self._parse_requirements_with_llm(state.issue)
            
            state.current_agent = self.name
            state.status = "in_progress"
            state.messages.append({
                "agent": self.name,
                "action": "parsed_requirements",
                "data": parsed_requirements
            })
            
            self.log("Requirements parsed by LLM, delegating to RepoReader...", parsed_requirements)
            
            # Log output
            duration_ms = (time.time() - start_time) * 1000
            self.log_output(state, duration_ms)
            return state
            
        except Exception as e:
            self.log_error(e, {"issue": state.issue[:200]})
            state.errors.append(str(e))
            return state
    
    async def _parse_requirements_with_llm(self, issue: str) -> Dict[str, Any]:
        """
        Use LLM to parse the issue text into structured requirements.

        This is the core LLM-powered parsing method.
        """
        prompt = f"""You are Alex, Senior Technical Lead operating in the Requirements & Analysis phase of the SDLC.

Analyze the following development request and extract complete, structured requirements that will drive the entire pipeline.

## Request:
{issue}

## Your Analysis Tasks:
1. Identify the true intent — what is ACTUALLY needed, not just what was literally said
2. Classify the change type and risk level accurately
3. Define testable acceptance criteria (not vague goals)
4. Flag any security, breaking-change, or architectural concerns upfront
5. Identify which SDLC phases and components will be involved

## Required Output (JSON format):
```json
{{
    "raw_issue": "original request text",
    "type": "feature|bugfix|refactor|enhancement|security|performance",
    "summary": "Precise 1-2 sentence summary of what needs to be built and why",
    "key_requirements": [
        "Specific, verifiable requirement 1",
        "Specific, verifiable requirement 2"
    ],
    "acceptance_criteria": [
        "Given X, when Y, then Z — testable criterion 1",
        "Given X, when Y, then Z — testable criterion 2"
    ],
    "technical_considerations": [
        "Architecture or implementation constraint 1",
        "Relevant existing pattern or component to reuse"
    ],
    "target_files": ["likely_file1.py", "likely_file2.py"],
    "affected_components": ["auth", "api", "models", "database"],
    "sdlc_phases": ["design", "implementation", "review", "testing", "delivery"],
    "priority": "low|normal|high|critical",
    "risk_level": "low|medium|high|critical",
    "estimated_complexity": "low|medium|high",
    "technologies": ["python", "fastapi"],
    "breaking_changes": false,
    "breaking_change_details": "null or description of what breaks and migration path",
    "requires_security_review": false,
    "security_concerns": ["list any auth, injection, or data-exposure concerns, or empty array"]
}}
```

Provide ONLY the JSON object, no additional text."""

        try:
            response = await self.llm.generate(
                prompt=prompt,
                system_prompt=self.prompt,
                temperature=0.3
            )
            
            # Parse the response as JSON
            requirements = self._parse_json_response(response)
            requirements["raw_issue"] = issue  # Ensure we keep the original
            
            self.log("LLM parsed requirements", {
                "type": requirements.get("type"),
                "complexity": requirements.get("estimated_complexity")
            })
            
            return requirements
            
        except Exception as e:
            self.log(f"LLM parsing failed: {e}")
            # Fallback to basic parsing
            return self._basic_parse_requirements(issue)
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response."""
        response = response.strip()
        
        # Remove markdown code blocks if present
        if response.startswith("```"):
            lines = response.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response = "\n".join(lines)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            
            return {
                "type": "enhancement",
                "summary": response[:200],
                "key_requirements": [],
                "priority": "normal",
                "estimated_complexity": "medium"
            }
    
    def _basic_parse_requirements(self, issue: str) -> Dict[str, Any]:
        """Basic fallback parsing when LLM fails."""
        return {
            "raw_issue": issue,
            "type": self._detect_issue_type(issue),
            "summary": issue[:200],
            "key_requirements": [],
            "priority": "normal",
            "estimated_complexity": self._estimate_complexity(issue)
        }
    
    def _detect_issue_type(self, issue: str) -> str:
        """Detect the type of issue (feature, bugfix, refactor, etc.)."""
        issue_lower = issue.lower()
        if any(word in issue_lower for word in ["bug", "fix", "error", "broken"]):
            return "bugfix"
        elif any(word in issue_lower for word in ["add", "create", "implement", "new"]):
            return "feature"
        elif any(word in issue_lower for word in ["refactor", "improve", "optimize"]):
            return "refactor"
        else:
            return "enhancement"
    
    def _estimate_complexity(self, issue: str) -> str:
        """Estimate the complexity of the issue."""
        word_count = len(issue.split())
        if word_count < 20:
            return "low"
        elif word_count < 50:
            return "medium"
        else:
            return "high"
    
