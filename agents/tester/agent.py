"""Tester Agent - Creates and runs tests using LLM-powered generation."""

import os
import subprocess
import re
from typing import Dict, Any, List, Optional
from agents.base import BaseAgent, AgentState
from prompts import get_prompt
from model import get_llm


class GitNotFoundError(Exception):
    """Raised when Git is not installed or not found in PATH."""
    pass


class TesterAgent(BaseAgent):
    """
    The Tester Agent using LLM-powered test generation:
    1. Analyzes code changes to understand testing needs
    2. Uses LLM to generate comprehensive test files
    3. Commits test files
    4. Runs tests and reports results
    """
    
    def __init__(self):
        super().__init__(
            name="Tester",
            description="Creates tests using LLM-powered generation"
        )
        # Load prompt from file
        self.prompt = get_prompt("tester", default="")
        self.llm = get_llm()
    
    async def execute(self, state: AgentState) -> AgentState:
        """Execute the testing workflow with LLM-powered test generation."""
        import time
        start_time = time.time()
        
        # Log input
        self.log_input(state)
        self.log("Starting LLM-powered test generation...", {"code_files": list(state.code_changes.keys())})
        
        try:
            # Step 1: Generate test files using LLM
            test_files = await self._generate_tests_with_llm(
                state.code_changes,
                state.issue,
                state.implementation_plan
            )
            state.test_files = test_files
            self.log("Generated test files with LLM", {"test_files": list(test_files.keys())})
            
            # Step 2: Write test files
            self._write_test_files(state.repo_path, test_files)
            self.log("Wrote test files", {"count": len(test_files)})
            
            # Step 3: Commit test files
            self._commit_test_files(state.repo_path)
            self.log("Committed test files")
            
            # Step 4: Run tests
            test_results = self._run_tests(state.repo_path)
            test_count = self._count_tests(test_files)
            self.log("Ran tests", {"results": test_results})
            
            state.current_agent = self.name
            state.messages.append({
                "agent": self.name,
                "action": "tests_created",
                "data": {
                    "test_files": list(test_files.keys()),
                    "test_count": test_count,
                    "test_results": test_results
                }
            })
            
            self.log(f"Created {len(test_files)} test files with {test_count} tests", {"test_count": test_count})
            
            # Log output
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
        """
        Use LLM to generate comprehensive test files for the code changes.
        
        This is the core LLM-powered test generation method.
        """
        test_files = {}
        
        for file_path, content in code_changes.items():
            # Only generate tests for Python files, skip test files
            if not file_path.endswith('.py') or file_path.startswith('test_') or '/test_' in file_path:
                continue
            
            test_file_path = self._get_test_file_path(file_path)
            self.log(f"Generating tests for: {file_path}")
            
            # Build the prompt for test generation
            prompt = self._build_test_generation_prompt(
                file_path=file_path,
                source_code=content,
                issue=issue,
                implementation_plan=implementation_plan
            )
            
            try:
                # Call LLM to generate tests
                generated_tests = await self.llm.generate(
                    prompt=prompt,
                    system_prompt=self.prompt,
                    temperature=0.3  # Lower temperature for more consistent tests
                )
                
                # Extract code from response
                clean_tests = self._extract_code_from_response(generated_tests)
                test_files[test_file_path] = clean_tests
                
                self.log(f"Successfully generated tests for {file_path}", {
                    "test_file": test_file_path,
                    "test_length": len(clean_tests)
                })
                
            except Exception as e:
                self.log(f"LLM test generation failed for {file_path}: {e}")
                # Fallback: generate basic tests
                test_files[test_file_path] = self._generate_fallback_tests(file_path, content)
        
        return test_files
    
    def _build_test_generation_prompt(
        self,
        file_path: str,
        source_code: str,
        issue: str,
        implementation_plan: Dict[str, Any]
    ) -> str:
        """Build a comprehensive prompt for test generation."""
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        
        prompt_parts = [
            "Generate comprehensive pytest test cases for the following Python module.",
            "",
            f"## Module: {module_name}",
            f"## File: {file_path}",
            "",
            "## Source Code to Test:",
            "```python",
            source_code[:5000],  # Limit to avoid token overflow
            "```",
            ""
        ]
        
        if len(source_code) > 5000:
            prompt_parts.append("(Source code truncated)")
            prompt_parts.append("")
        
        prompt_parts.extend([
            f"## Original User Request:",
            issue[:500],
            "",
            "## Test Requirements:",
            "1. Use pytest framework with proper fixtures",
            "2. Test all public classes and methods",
            "3. Test all standalone functions",
            "4. Include positive test cases (expected behavior)",
            "5. Include negative test cases (error handling)",
            "6. Include edge cases (empty inputs, None values, boundaries)",
            "7. Add descriptive docstrings for each test",
            "8. Use appropriate assertions",
            "9. Mock external dependencies if needed",
            "",
            "## Output Format:",
            "Provide ONLY the complete test file code with:",
            "- Proper imports including pytest and the module under test",
            "- Test fixtures at the top",
            "- Test classes for each source class",
            "- Test functions for standalone functions",
            "- Clear naming: test_{function_name} or Test{ClassName}",
            "",
            "Do not include markdown code blocks in the output."
        ])
        
        return "\n".join(prompt_parts)
    
    def _extract_code_from_response(self, response: str) -> str:
        """Extract clean code from LLM response."""
        code = response.strip()
        
        # Remove markdown code blocks if present
        patterns = [
            r'^```(?:python|py)?\n?(.*?)```$',
            r'^```\n?(.*?)```$'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, code, re.DOTALL | re.IGNORECASE)
            if match:
                code = match.group(1).strip()
                break
        
        return code
    
    def _generate_fallback_tests(self, file_path: str, source_code: str) -> str:
        """Generate basic fallback tests when LLM fails."""
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        
        # Extract classes and functions for basic test structure
        classes = self._extract_classes(source_code)
        functions = self._extract_functions(source_code)
        
        tests = [
            f'"""Tests for {module_name} module - auto-generated."""',
            "",
            "import pytest",
            "import sys",
            "import os",
            "",
            "# Add parent directory to path",
            "sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))",
            "",
            f"from {module_name} import *",
            "",
            ""
        ]
        
        for cls in classes:
            tests.append(f'class Test{cls["name"]}:')
            tests.append(f'    """Tests for {cls["name"]} class."""')
            tests.append("")
            tests.append("    @pytest.fixture")
            tests.append("    def instance(self):")
            tests.append(f'        """Create {cls["name"]} instance."""')
            tests.append(f'        return {cls["name"]}()')
            tests.append("")
            
            for method in cls.get("methods", []):
                tests.append(f"    def test_{method}(self, instance):")
                tests.append(f'        """Test {method} method."""')
                tests.append("        # TODO: Implement test")
                tests.append("        pass")
                tests.append("")
        
        if functions:
            tests.append("")
            tests.append("class TestFunctions:")
            tests.append('    """Tests for standalone functions."""')
            tests.append("")
            
            for func in functions:
                tests.append(f'    def test_{func["name"]}(self):')
                tests.append(f'        """Test {func["name"]} function."""')
                tests.append("        # TODO: Implement test")
                tests.append("        pass")
                tests.append("")
        
        return "\n".join(tests)
    
    def _extract_classes(self, content: str) -> List[Dict[str, Any]]:
        """Extract class definitions from code."""
        classes = []
        
        class_pattern = r'class\s+(\w+)(?:\([^)]*\))?:'
        method_pattern = r'\s+def\s+(\w+)\s*\([^)]*\)'
        
        lines = content.split('\n')
        current_class = None
        
        for i, line in enumerate(lines):
            class_match = re.match(class_pattern, line)
            if class_match:
                if current_class:
                    classes.append(current_class)
                current_class = {
                    "name": class_match.group(1),
                    "methods": [],
                    "line": i + 1
                }
            elif current_class and line.startswith('    def '):
                method_match = re.match(method_pattern, line)
                if method_match:
                    method_name = method_match.group(1)
                    if not method_name.startswith('_'):
                        current_class["methods"].append(method_name)
        
        if current_class:
            classes.append(current_class)
        
        return classes
    
    def _extract_functions(self, content: str) -> List[Dict[str, Any]]:
        """Extract standalone function definitions from code."""
        functions = []
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            # Only match top-level functions (not indented)
            match = re.match(r'^def\s+(\w+)\s*\([^)]*\)', line)
            if match:
                func_name = match.group(1)
                if not func_name.startswith('_'):
                    functions.append({
                        "name": func_name,
                        "line": i + 1
                    })
        
        return functions
    
    def _generate_test_files(self, requirements: Dict, code_changes: Dict[str, str]) -> Dict[str, str]:
        """Generate test files based on requirements."""
        test_files = {}
        
        for file_path, reqs in requirements.items():
            test_file_path = self._get_test_file_path(file_path)
            test_content = self._generate_test_content(file_path, reqs, code_changes.get(file_path, ""))
            test_files[test_file_path] = test_content
        
        return test_files
    
    def _get_test_file_path(self, source_file: str) -> str:
        """Generate the test file path for a source file."""
        dir_name = os.path.dirname(source_file)
        base_name = os.path.basename(source_file)
        
        # Create test file name
        if base_name.startswith('_'):
            test_name = f"test{base_name}"
        else:
            test_name = f"test_{base_name}"
        
        # Put in tests directory
        if dir_name:
            return os.path.join("tests", dir_name, test_name)
        else:
            return os.path.join("tests", test_name)
    
    def _generate_test_content(self, source_file: str, reqs: Dict, source_content: str) -> str:
        """Generate test file content."""
        module_name = os.path.splitext(os.path.basename(source_file))[0]
        
        # Build imports
        imports = [
            '"""Tests for {} module."""'.format(module_name),
            "",
            "import pytest",
            "import sys",
            "import os",
            "",
            "# Add parent directory to path for imports",
            "sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))",
            ""
        ]
        
        # Import the module being tested
        imports.append(f"from {module_name} import *")
        imports.append("")
        imports.append("")
        
        # Generate test classes
        test_classes = []
        
        for cls in reqs.get("classes", []):
            class_tests = self._generate_class_tests(cls, source_content)
            test_classes.append(class_tests)
        
        # Generate function tests
        function_tests = []
        for func in reqs.get("functions", []):
            func_test = self._generate_function_test(func)
            function_tests.append(func_test)
        
        # Combine all parts
        content = "\n".join(imports)
        
        for class_test in test_classes:
            content += "\n" + class_test
        
        if function_tests:
            content += "\n\nclass TestFunctions:\n"
            content += '    """Tests for standalone functions."""\n\n'
            for func_test in function_tests:
                content += func_test
        
        return content
    
    def _generate_class_tests(self, cls: Dict, source_content: str) -> str:
        """Generate test class for a source class."""
        class_name = cls["name"]
        methods = cls["methods"]
        
        test_class = f'class Test{class_name}:\n'
        test_class += f'    """Tests for {class_name} class."""\n\n'
        
        # Add fixture for class instance
        test_class += f'    @pytest.fixture\n'
        test_class += f'    def instance(self):\n'
        test_class += f'        """Create a {class_name} instance for testing."""\n'
        test_class += f'        return {class_name}()\n\n'
        
        # Generate test for each method
        for method in methods:
            test_class += self._generate_method_test(class_name, method, source_content)
        
        # Add edge case tests
        test_class += self._generate_edge_case_tests(class_name, methods)
        
        return test_class
    
    def _generate_method_test(self, class_name: str, method_name: str, source_content: str) -> str:
        """Generate a test for a class method."""
        test = f'    def test_{method_name}(self, instance):\n'
        test += f'        """Test {class_name}.{method_name} method."""\n'
        
        # Try to generate meaningful test based on method name
        if method_name == "validate":
            test += f'        # Test validation logic\n'
            test += f'        result = instance.{method_name}("test_input")\n'
            test += f'        assert result is not None\n'
        elif method_name.startswith("get_"):
            test += f'        # Test getter method\n'
            test += f'        result = instance.{method_name}()\n'
            test += f'        assert result is not None\n'
        elif method_name.startswith("set_"):
            test += f'        # Test setter method\n'
            test += f'        instance.{method_name}("test_value")\n'
            test += f'        # Verify the value was set\n'
        elif method_name in ("login", "authenticate"):
            test += f'        # Test authentication\n'
            test += f'        result = instance.{method_name}("test_user", "test_password")\n'
            test += f'        assert isinstance(result, tuple)\n'
        elif method_name == "register_user":
            test += f'        # Test user registration\n'
            test += f'        success, message = instance.{method_name}("testuser", "test@example.com", "ValidPass123!")\n'
            test += f'        assert isinstance(success, bool)\n'
            test += f'        assert isinstance(message, str)\n'
        elif method_name == "hash_password":
            test += f'        # Test password hashing\n'
            test += f'        hashed = instance.{method_name}("test_password")\n'
            test += f'        assert isinstance(hashed, str)\n'
            test += f'        assert len(hashed) > 0\n'
            test += f'        # Same password should produce same hash\n'
            test += f'        assert instance.{method_name}("test_password") == hashed\n'
        else:
            test += f'        # TODO: Implement test for {method_name}\n'
            test += f'        # result = instance.{method_name}()\n'
            test += f'        # assert result == expected_value\n'
            test += f'        pass\n'
        
        test += '\n'
        return test
    
    def _generate_function_test(self, func: Dict) -> str:
        """Generate a test for a standalone function."""
        func_name = func["name"]
        
        test = f'    def test_{func_name}(self):\n'
        test += f'        """Test {func_name} function."""\n'
        
        if func_name.startswith("generate_"):
            test += f'        result = {func_name}()\n'
            test += f'        assert result is not None\n'
            test += f'        assert len(result) > 0\n'
        else:
            test += f'        # TODO: Implement test\n'
            test += f'        pass\n'
        
        test += '\n'
        return test
    
    def _generate_edge_case_tests(self, class_name: str, methods: List[str]) -> str:
        """Generate edge case tests for a class."""
        tests = ""
        
        # Add test for empty/None inputs
        tests += f'    def test_invalid_inputs(self, instance):\n'
        tests += f'        """Test {class_name} handles invalid inputs gracefully."""\n'
        tests += f'        # Test with None values\n'
        tests += f'        # Test with empty strings\n'
        tests += f'        # Test with invalid types\n'
        tests += f'        pass\n\n'
        
        # Add initialization test
        tests += f'    def test_initialization(self):\n'
        tests += f'        """Test {class_name} initializes correctly."""\n'
        tests += f'        instance = {class_name}()\n'
        tests += f'        assert instance is not None\n\n'
        
        return tests
    
    def _write_test_files(self, repo_path: str, test_files: Dict[str, str]) -> None:
        """Write test files to disk."""
        for file_path, content in test_files.items():
            full_path = os.path.join(repo_path, file_path) if repo_path else file_path
            
            # Create directory if needed
            os.makedirs(os.path.dirname(full_path) or '.', exist_ok=True)
            
            try:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.log(f"Wrote test file: {file_path}")
            except Exception as e:
                self.log(f"Failed to write {file_path}: {e}")
    
    def _commit_test_files(self, repo_path: str) -> None:
        """Commit test files to git."""
        if not repo_path or not os.path.exists(repo_path):
            return
        
        try:
            # Add test files using relative path with cwd set to repo_path
            tests_path = os.path.join(repo_path, "tests")
            if os.path.exists(tests_path):
                subprocess.run(
                    ["git", "add", "tests/"],
                    cwd=repo_path,
                    capture_output=True,
                    check=True
                )
            else:
                # Fallback: add all changed files
                subprocess.run(
                    ["git", "add", "-A"],
                    cwd=repo_path,
                    capture_output=True,
                    check=False  # Don't fail if nothing to add
                )
            
            # Check if there are staged changes before committing
            result = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                capture_output=True
            )
            
            if result.returncode != 0:  # There are staged changes
                subprocess.run(
                    ["git", "commit", "-m", "test: Add automated tests for new implementation"],
                    capture_output=True,
                    check=True
                )
                self.log("Test files committed")
            else:
                self.log("No new test files to commit (already committed or no changes)")
        except subprocess.CalledProcessError as e:
            self.log(f"Git commit failed: {e}")
            raise
        except FileNotFoundError:
            self.log("Git not found - stopping execution")
            raise GitNotFoundError("Git is not installed or not found in PATH. Please install Git to continue.")
    
    def _run_tests(self, repo_path: str) -> Dict[str, Any]:
        """Run the test suite and return results."""
        if not repo_path:
            return {"status": "skipped", "reason": "No repo path provided"}
        
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/", "-v", "--tb=short"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            return {
                "status": "passed" if result.returncode == 0 else "failed",
                "return_code": result.returncode,
                "output": result.stdout[:2000],  # Limit output size
                "errors": result.stderr[:1000] if result.stderr else None
            }
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "reason": "Tests took too long to run"}
        except FileNotFoundError:
            return {"status": "skipped", "reason": "pytest not installed"}
        except Exception as e:
            return {"status": "error", "reason": str(e)}
    
    def _count_tests(self, test_files: Dict[str, str]) -> int:
        """Count the total number of test methods in test files."""
        count = 0
        for content in test_files.values():
            count += len(re.findall(r'def test_', content))
        return count
