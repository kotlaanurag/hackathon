"""Tester Agent - Creates and runs tests using LLM-powered generation."""

import os
import subprocess
import re
import glob
from typing import Dict, Any, List, Optional, Tuple
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
    2. Detects project type (Python, C#/.NET, or Java)
    3. Uses LLM to generate comprehensive test files
    4. Writes and commits test files
    5. Runs tests with appropriate framework (pytest, dotnet test, or mvn/gradle test)
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
        
        # Detect project type
        project_type = self._detect_project_type(state.repo_path, state.code_changes)
        self.log(f"Detected project type: {project_type}", {
            "code_files": list(state.code_changes.keys())
        })

        try:
            test_files = await self._generate_tests_with_llm(
                state.code_changes,
                state.issue,
                state.implementation_plan,
                project_type
            )
            state.test_files = test_files
            self.log("Generated test files with LLM", {"test_files": list(test_files.keys())})

            self._write_test_files(state.repo_path, test_files, project_type)
            self.log("Wrote test files", {"count": len(test_files)})

            self._commit_test_files(state.repo_path, project_type)
            self.log("Committed test files")

            test_results = self._run_tests(state.repo_path, project_type)
            test_count = self._count_tests(test_files, project_type)
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

    def _detect_project_type(self, repo_path: str, code_changes: Dict[str, str]) -> str:
        """Detect the project type based on file extensions and project files."""
        # Check code changes for file extensions
        for file_path in code_changes.keys():
            if file_path.endswith('.cs'):
                return 'csharp'
            elif file_path.endswith('.java'):
                return 'java'
            elif file_path.endswith('.py'):
                return 'python'
        
        # Check for project files in repo
        if repo_path and os.path.exists(repo_path):
            # Check for .NET project files
            csproj_files = glob.glob(os.path.join(repo_path, '**', '*.csproj'), recursive=True)
            sln_files = glob.glob(os.path.join(repo_path, '**', '*.sln'), recursive=True)
            if csproj_files or sln_files:
                return 'csharp'
            
            # Check for Java project files (Maven or Gradle)
            pom_files = glob.glob(os.path.join(repo_path, '**', 'pom.xml'), recursive=True)
            gradle_files = glob.glob(os.path.join(repo_path, '**', 'build.gradle'), recursive=True)
            gradle_kts_files = glob.glob(os.path.join(repo_path, '**', 'build.gradle.kts'), recursive=True)
            if pom_files or gradle_files or gradle_kts_files:
                return 'java'
            
            # Check for Java source files
            java_files = glob.glob(os.path.join(repo_path, '**', '*.java'), recursive=True)
            if java_files:
                return 'java'
            
            # Check for Python project files
            py_files = glob.glob(os.path.join(repo_path, '**', '*.py'), recursive=True)
            if py_files:
                return 'python'
        
        return 'python'  # Default to Python

    async def _generate_tests_with_llm(
        self,
        code_changes: Dict[str, str],
        issue: str,
        implementation_plan: Dict[str, Any],
        project_type: str = 'python'
    ) -> Dict[str, str]:
        """Use LLM to generate comprehensive test files for each changed source file."""
        test_files = {}

        for file_path, content in code_changes.items():
            # Filter files based on project type
            if project_type == 'csharp':
                # Only generate tests for C# source files; skip existing test files
                if not file_path.endswith('.cs') or 'Test' in file_path or '.Tests' in file_path:
                    continue
            elif project_type == 'java':
                # Only generate tests for Java source files; skip existing test files
                if not file_path.endswith('.java') or 'Test' in file_path or '/test/' in file_path.lower():
                    continue
            else:
                # Only generate tests for Python source files; skip existing test files
                if not file_path.endswith('.py') or 'test_' in file_path or '/test_' in file_path:
                    continue

            test_file_path = self._get_test_file_path(file_path, project_type)
            self.log(f"Generating tests for: {file_path} (project_type={project_type})")

            prompt = self._build_test_generation_prompt(
                file_path=file_path,
                source_code=content,
                issue=issue,
                implementation_plan=implementation_plan,
                project_type=project_type
            )

            try:
                generated_tests = await self.llm.generate(
                    prompt=prompt,
                    system_prompt=self.prompt,
                    temperature=0.3
                )
                clean_tests = self._extract_code_from_response(generated_tests, project_type)
                test_files[test_file_path] = clean_tests
                self.log(f"Generated tests for {file_path}", {
                    "test_file": test_file_path,
                    "length": len(clean_tests)
                })

            except Exception as e:
                self.log(f"LLM test generation failed for {file_path}, using fallback: {e}")
                test_files[test_file_path] = self._generate_fallback_tests(file_path, content, project_type)

        return test_files

    def _build_test_generation_prompt(
        self,
        file_path: str,
        source_code: str,
        issue: str,
        implementation_plan: Dict[str, Any],
        project_type: str = 'python'
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

        if project_type == 'csharp':
            return self._build_csharp_test_prompt(
                file_path, source_code, issue, module_name,
                action_type, testing_reqs, security_considerations
            )
        elif project_type == 'java':
            return self._build_java_test_prompt(
                file_path, source_code, issue, module_name,
                action_type, testing_reqs, security_considerations
            )
        else:
            return self._build_python_test_prompt(
                file_path, source_code, issue, module_name,
                action_type, testing_reqs, security_considerations
            )

    def _build_java_test_prompt(
        self,
        file_path: str,
        source_code: str,
        issue: str,
        module_name: str,
        action_type: str,
        testing_reqs: Dict,
        security_considerations: List[str]
    ) -> str:
        """Build a prompt for generating Java JUnit 5 tests."""
        prompt_parts = [
            "You are Casey, Senior QA Engineer in the Verification phase of the SDLC.",
            "You think like a malicious user, a careless developer, and a tired ops engineer simultaneously.",
            "Write tests that fail for the right reasons and pass for the right reasons.",
            "",
            f"## Class Under Test: {module_name}",
            f"## Source File: {file_path}",
            f"## Change Type: {action_type}",
            f"## Language: Java",
            f"## Test Framework: JUnit 5 with Mockito for mocking",
            "",
            "## Source Code to Test:",
            "```java",
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
            "## Java JUnit 5 Test Design Rules (MANDATORY):",
            "",
            "NAMING CONVENTION: methodName_scenario_expectedResult()",
            "  Examples:",
            "  - login_withValidCredentials_returnsToken()",
            "  - login_withWrongPassword_throwsAuthenticationException()",
            "  - registerUser_withDuplicateEmail_returnsFalse()",
            "",
            "AAA PATTERN: Every test must follow Arrange-Act-Assert:",
            "  // Arrange — set up inputs, mocks, expected values",
            "  // Act     — call the method under test",
            "  // Assert  — verify result matches expectations",
            "",
            "TEST STRUCTURE:",
            "  - Use @Test for test methods",
            "  - Use @ParameterizedTest with @ValueSource, @CsvSource for parameterized tests",
            "  - Use @BeforeEach for setup, @AfterEach for cleanup",
            "  - Use Mockito (@Mock, @InjectMocks, @ExtendWith(MockitoExtension.class))",
            "  - Use AssertJ or JUnit assertions (assertEquals, assertTrue, assertThrows)",
            "",
            "FOR SPRING BOOT CONTROLLERS:",
            "  - Use @WebMvcTest for controller tests",
            "  - Use @MockBean to mock services",
            "  - Use MockMvc to perform HTTP requests",
            "  - Test ResponseEntity return types (OK, BAD_REQUEST, NOT_FOUND, etc.)",
            "  - Verify correct status codes and response bodies",
            "",
            "FOR AUTHENTICATION / SECURITY CODE:",
            "  - Valid credentials → success + token returned",
            "  - Invalid password → failure, same error as wrong username (no info leak)",
            "  - Null/empty credentials → IllegalArgumentException or equivalent",
            "  - SQL injection attempt in credentials → rejected safely",
            "",
            "JUNIT 5 BEST PRACTICES:",
            "  - Use @DisplayName for readable test descriptions",
            "  - Use @Nested for grouping related tests",
            "  - Use @ExtendWith(MockitoExtension.class) for Mockito",
            "  - NEVER make real network calls or write to real databases",
            "  - Each test must be independent",
            "  - Every test must have a meaningful assertion",
            "",
            "## Output Format:",
            "Provide ONLY the complete test file. No explanations. No markdown fencing.",
            "Structure:",
            "  package statements",
            "  import statements",
            "",
            "  @ExtendWith(MockitoExtension.class)",
            "  class {ClassName}Test {",
            "      @Mock",
            "      private DependencyClass mockDependency;",
            "",
            "      @InjectMocks",
            "      private ClassName sut; // System Under Test",
            "",
            "      @BeforeEach",
            "      void setUp() { /* setup */ }",
            "",
            "      @Test",
            "      @DisplayName(\"Should return token when credentials are valid\")",
            "      void methodName_scenario_expectedResult() { ... }",
            "",
            "      @ParameterizedTest",
            "      @ValueSource(strings = {...})",
            "      void methodName_multipleScenarios(String param) { ... }",
            "  }",
        ])

        return "\n".join(prompt_parts)

    def _build_csharp_test_prompt(
        self,
        file_path: str,
        source_code: str,
        issue: str,
        module_name: str,
        action_type: str,
        testing_reqs: Dict,
        security_considerations: List[str]
    ) -> str:
        """Build a prompt for generating C# xUnit tests."""
        prompt_parts = [
            "You are Casey, Senior QA Engineer in the Verification phase of the SDLC.",
            "You think like a malicious user, a careless developer, and a tired ops engineer simultaneously.",
            "Write tests that fail for the right reasons and pass for the right reasons.",
            "",
            f"## Class Under Test: {module_name}",
            f"## Source File: {file_path}",
            f"## Change Type: {action_type}",
            f"## Language: C# (.NET)",
            f"## Test Framework: xUnit with Moq for mocking",
            "",
            "## Source Code to Test:",
            "```csharp",
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
            "## C# xUnit Test Design Rules (MANDATORY):",
            "",
            "NAMING CONVENTION: {MethodName}_{Scenario}_{ExpectedResult}",
            "  Examples:",
            "  - Login_WithValidCredentials_ReturnsToken",
            "  - Login_WithWrongPassword_ThrowsAuthenticationException",
            "  - RegisterUser_WithDuplicateEmail_ReturnsFalse",
            "",
            "AAA PATTERN: Every test must follow Arrange-Act-Assert:",
            "  // Arrange — set up inputs, mocks, expected values",
            "  // Act     — call the method under test",
            "  // Assert  — verify result matches expectations",
            "",
            "TEST STRUCTURE:",
            "  - Use [Fact] for single test cases",
            "  - Use [Theory] with [InlineData] for parameterized tests",
            "  - Use Moq to mock ILogger, IConfiguration, and other dependencies",
            "  - Use FluentAssertions or Assert.* for assertions",
            "",
            "FOR ASP.NET CORE CONTROLLERS:",
            "  - Mock ILogger<T> using Mock<ILogger<ControllerName>>()",
            "  - Test ActionResult return types (Ok, BadRequest, NotFound, etc.)",
            "  - Verify correct status codes",
            "  - Test with valid and invalid model states",
            "",
            "FOR AUTHENTICATION / SECURITY CODE:",
            "  - Valid credentials → success + token returned",
            "  - Invalid password → failure, same error as wrong username (no info leak)",
            "  - Empty/null credentials → ArgumentException or equivalent",
            "  - SQL injection attempt in credentials → rejected safely",
            "",
            "XUNIT BEST PRACTICES:",
            "  - Use constructor for shared setup (replaces [SetUp])",
            "  - Implement IDisposable for cleanup (replaces [TearDown])",
            "  - Use IClassFixture<T> for expensive shared resources",
            "  - NEVER make real network calls or write to real databases",
            "  - Each test must be independent",
            "  - Every test must have a meaningful assertion",
            "",
            "## Output Format:",
            "Provide ONLY the complete test file. No explanations. No markdown fencing.",
            "Structure:",
            "  using statements",
            "  namespace {ProjectName}.Tests",
            "  {",
            "      public class {ClassName}Tests",
            "      {",
            "          private readonly Mock<ILogger<ClassName>> _mockLogger;",
            "          private readonly ClassName _sut; // System Under Test",
            "",
            "          public {ClassName}Tests() { /* constructor setup */ }",
            "",
            "          [Fact]",
            "          public void MethodName_Scenario_ExpectedResult() { ... }",
            "",
            "          [Theory]",
            "          [InlineData(...)]",
            "          public void MethodName_MultipleScenarios(params) { ... }",
            "      }",
            "  }",
        ])

        return "\n".join(prompt_parts)

    def _build_python_test_prompt(
        self,
        file_path: str,
        source_code: str,
        issue: str,
        module_name: str,
        action_type: str,
        testing_reqs: Dict,
        security_considerations: List[str]
    ) -> str:
        """Build a prompt for generating Python pytest tests."""
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

    def _extract_code_from_response(self, response: str, project_type: str = 'python') -> str:
        """Strip markdown fencing from LLM response."""
        code = response.strip()
        
        # Patterns for different languages
        if project_type == 'csharp':
            patterns = [
                r'^```(?:csharp|cs|c#)?\n?(.*?)```$',
                r'^```\n?(.*?)```$'
            ]
        elif project_type == 'java':
            patterns = [
                r'^```(?:java)?\n?(.*?)```$',
                r'^```\n?(.*?)```$'
            ]
        else:
            patterns = [
                r'^```(?:python|py)?\n?(.*?)```$',
                r'^```\n?(.*?)```$'
            ]
        
        for pattern in patterns:
            match = re.match(pattern, code, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return code

    def _generate_fallback_tests(self, file_path: str, source_code: str, project_type: str = 'python') -> str:
        """Generate basic skeleton tests when LLM fails."""
        if project_type == 'csharp':
            return self._generate_csharp_fallback_tests(file_path, source_code)
        elif project_type == 'java':
            return self._generate_java_fallback_tests(file_path, source_code)
        return self._generate_python_fallback_tests(file_path, source_code)

    def _generate_java_fallback_tests(self, file_path: str, source_code: str) -> str:
        """Generate basic Java JUnit 5 skeleton tests."""
        class_name = os.path.splitext(os.path.basename(file_path))[0]
        package_name = self._extract_java_package(source_code) or "com.example"
        
        # Extract methods from Java source
        methods = self._extract_java_methods(source_code)
        
        lines = [
            f"package {package_name};",
            "",
            "import org.junit.jupiter.api.BeforeEach;",
            "import org.junit.jupiter.api.Test;",
            "import org.junit.jupiter.api.DisplayName;",
            "import org.junit.jupiter.api.extension.ExtendWith;",
            "import org.mockito.Mock;",
            "import org.mockito.InjectMocks;",
            "import org.mockito.junit.jupiter.MockitoExtension;",
            "",
            "import static org.junit.jupiter.api.Assertions.*;",
            "import static org.mockito.Mockito.*;",
            "",
            "/**",
            f" * Tests for {class_name} class - auto-generated.",
            " */",
            "@ExtendWith(MockitoExtension.class)",
            f"class {class_name}Test {{",
            "",
            "    @InjectMocks",
            f"    private {class_name} sut;",
            "",
            "    @BeforeEach",
            "    void setUp() {",
            "        // Setup code here",
            "    }",
            "",
        ]
        
        for method in methods:
            lines.extend([
                "    @Test",
                f"    @DisplayName(\"Should succeed when {method} is called\")",
                f"    void {method}_whenCalled_shouldSucceed() {{",
                "        // Arrange",
                "",
                "        // Act",
                "",
                "        // Assert",
                "        assertTrue(true); // TODO: Add meaningful assertion",
                "    }",
                "",
            ])
        
        lines.append("}")
        
        return "\n".join(lines)

    def _generate_csharp_fallback_tests(self, file_path: str, source_code: str) -> str:
        """Generate basic C# xUnit skeleton tests."""
        class_name = os.path.splitext(os.path.basename(file_path))[0]
        namespace = self._extract_csharp_namespace(source_code) or "Tests"
        
        # Extract methods from C# source
        methods = self._extract_csharp_methods(source_code)
        
        lines = [
            "using System;",
            "using Xunit;",
            "using Moq;",
            "using Microsoft.Extensions.Logging;",
            "",
            f"namespace {namespace}.Tests",
            "{",
            f"    /// <summary>",
            f"    /// Tests for {class_name} class - auto-generated.",
            f"    /// </summary>",
            f"    public class {class_name}Tests",
            "    {",
            f"        private readonly Mock<ILogger<{class_name}>> _mockLogger;",
            f"        private readonly {class_name} _sut;",
            "",
            f"        public {class_name}Tests()",
            "        {",
            f"            _mockLogger = new Mock<ILogger<{class_name}>>();",
            f"            _sut = new {class_name}(_mockLogger.Object);",
            "        }",
            "",
        ]
        
        for method in methods:
            lines.extend([
                "        [Fact]",
                f"        public void {method}_WhenCalled_ShouldSucceed()",
                "        {",
                "            // Arrange",
                "",
                "            // Act",
                "",
                "            // Assert",
                "            Assert.True(true); // TODO: Add meaningful assertion",
                "        }",
                "",
            ])
        
        lines.extend([
            "    }",
            "}",
        ])
        
        return "\n".join(lines)

    def _generate_python_fallback_tests(self, file_path: str, source_code: str) -> str:
        """Generate basic Python pytest skeleton tests."""
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        classes = self._extract_classes(source_code)
        functions = self._extract_functions(source_code)

        lines = [
            f'"""Tests for {module_name} module - auto-generated."""',
            "",
            "import pytest",
            "import sys",
            "import os",
            "",
            "sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))",
            "",
            f"from {module_name} import *",
            "",
            ""
        ]

        for cls in classes:
            lines.append(f"class Test{cls['name']}:")
            lines.append(f'    """Tests for {cls["name"]} class."""')
            lines.append("")
            lines.append("    @pytest.fixture")
            lines.append("    def instance(self):")
            lines.append(f'        """Create {cls["name"]} instance."""')
            lines.append(f"        return {cls['name']}()")
            lines.append("")
            for method in cls.get("methods", []):
                lines.append(f"    def test_{method}(self, instance):")
                lines.append(f'        """Test {method} method."""')
                lines.append("        pass")
                lines.append("")

        if functions:
            lines.append("class TestFunctions:")
            lines.append('    """Tests for standalone functions."""')
            lines.append("")
            for func in functions:
                lines.append(f"    def test_{func['name']}(self):")
                lines.append(f'        """Test {func["name"]} function."""')
                lines.append("        pass")
                lines.append("")

        return "\n".join(lines)

    def _extract_classes(self, content: str) -> List[Dict[str, Any]]:
        """Extract class definitions and their public methods from source code."""
        classes = []
        lines = content.split('\n')
        current_class = None

        for i, line in enumerate(lines):
            class_match = re.match(r'class\s+(\w+)(?:\([^)]*\))?:', line)
            if class_match:
                if current_class:
                    classes.append(current_class)
                current_class = {"name": class_match.group(1), "methods": [], "line": i + 1}
            elif current_class and line.startswith('    def '):
                method_match = re.match(r'\s+def\s+(\w+)\s*\([^)]*\)', line)
                if method_match:
                    name = method_match.group(1)
                    if not name.startswith('_'):
                        current_class["methods"].append(name)

        if current_class:
            classes.append(current_class)
        return classes

    def _extract_functions(self, content: str) -> List[Dict[str, Any]]:
        """Extract top-level (non-indented) public function definitions."""
        functions = []
        for i, line in enumerate(content.split('\n')):
            match = re.match(r'^def\s+(\w+)\s*\([^)]*\)', line)
            if match:
                name = match.group(1)
                if not name.startswith('_'):
                    functions.append({"name": name, "line": i + 1})
        return functions

    def _extract_csharp_namespace(self, content: str) -> Optional[str]:
        """Extract namespace from C# source code."""
        match = re.search(r'namespace\s+([\w.]+)', content)
        return match.group(1) if match else None

    def _extract_csharp_methods(self, content: str) -> List[str]:
        """Extract public method names from C# source code."""
        methods = []
        # Match public methods: public ReturnType MethodName(...)
        pattern = r'public\s+(?:async\s+)?(?:virtual\s+)?(?:override\s+)?(?:static\s+)?[\w<>\[\],\s]+\s+(\w+)\s*\('
        matches = re.findall(pattern, content)
        for method in matches:
            # Skip constructors and common non-test methods
            if method not in ['Dispose', 'ToString', 'GetHashCode', 'Equals']:
                methods.append(method)
        return list(set(methods))[:10]  # Limit to 10 methods

    def _extract_java_package(self, content: str) -> Optional[str]:
        """Extract package name from Java source code."""
        match = re.search(r'package\s+([\w.]+)\s*;', content)
        return match.group(1) if match else None

    def _extract_java_methods(self, content: str) -> List[str]:
        """Extract public method names from Java source code."""
        methods = []
        # Match public methods: public ReturnType methodName(...)
        pattern = r'public\s+(?:static\s+)?(?:final\s+)?(?:synchronized\s+)?[\w<>\[\],\s]+\s+(\w+)\s*\('
        matches = re.findall(pattern, content)
        for method in matches:
            # Skip constructors, getters/setters, and common non-test methods
            if method not in ['toString', 'hashCode', 'equals', 'main'] and not method.startswith('get') and not method.startswith('set'):
                methods.append(method)
        return list(set(methods))[:10]  # Limit to 10 methods

    def _get_test_file_path(self, source_file: str, project_type: str = 'python') -> str:
        """Compute the test file path for a given source file."""
        dir_name = os.path.dirname(source_file)
        base_name = os.path.basename(source_file)
        
        if project_type == 'csharp':
            # For C#: MyController.cs -> MyControllerTests.cs in Tests folder
            name_without_ext = os.path.splitext(base_name)[0]
            test_name = f"{name_without_ext}Tests.cs"
            # Put tests in a Tests folder at the project root
            return os.path.join("Tests", test_name)
        elif project_type == 'java':
            # For Java: MyService.java -> MyServiceTest.java in src/test/java
            name_without_ext = os.path.splitext(base_name)[0]
            test_name = f"{name_without_ext}Test.java"
            # Put tests in src/test/java mirroring the source structure
            if 'src/main/java' in dir_name:
                test_dir = dir_name.replace('src/main/java', 'src/test/java')
            else:
                test_dir = os.path.join("src", "test", "java")
            return os.path.join(test_dir, test_name)
        else:
            # For Python: my_module.py -> test_my_module.py in tests folder
            test_name = f"test{base_name}" if base_name.startswith('_') else f"test_{base_name}"
            return os.path.join("tests", dir_name, test_name) if dir_name else os.path.join("tests", test_name)

    def _write_test_files(self, repo_path: str, test_files: Dict[str, str], project_type: str = 'python') -> None:
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

    def _commit_test_files(self, repo_path: str, project_type: str = 'python') -> None:
        """Stage and commit test files to git."""
        if not repo_path or not os.path.exists(repo_path):
            return

        try:
            # Determine test folder based on project type
            if project_type == 'csharp':
                tests_path = os.path.join(repo_path, "Tests")
                add_path = "Tests/"
            elif project_type == 'java':
                tests_path = os.path.join(repo_path, "src", "test")
                add_path = "src/test/"
            else:
                tests_path = os.path.join(repo_path, "tests")
                add_path = "tests/"
            
            if os.path.exists(tests_path):
                subprocess.run(
                    ["git", "add", add_path],
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

    def _find_dotnet_project_file(self, repo_path: str) -> Optional[str]:
        """Find the solution or test project file to use for dotnet test."""
        # First, look for a .sln file
        sln_files = glob.glob(os.path.join(repo_path, '*.sln'))
        if sln_files:
            return sln_files[0]  # Use the first solution file found
        
        # Look for test project files (*.Tests.csproj or *Tests.csproj)
        test_projects = glob.glob(os.path.join(repo_path, '**', '*Tests.csproj'), recursive=True)
        test_projects += glob.glob(os.path.join(repo_path, '**', '*.Tests.csproj'), recursive=True)
        if test_projects:
            return test_projects[0]  # Use the first test project found
        
        # Fall back to any .csproj file
        csproj_files = glob.glob(os.path.join(repo_path, '**', '*.csproj'), recursive=True)
        if csproj_files:
            # Prefer files in a Tests folder
            for csproj in csproj_files:
                if 'test' in csproj.lower():
                    return csproj
            return csproj_files[0]
        
        return None

    def _run_tests(self, repo_path: str, project_type: str = 'python') -> Dict[str, Any]:
        """Run the test suite and return detailed results including failure info."""
        if not repo_path:
            return {"status": "skipped", "reason": "No repo path provided"}

        try:
            if project_type == 'csharp':
                # Find the appropriate project/solution file
                project_file = self._find_dotnet_project_file(repo_path)
                
                if project_file:
                    self.log(f"Using project file for dotnet test: {project_file}")
                    # Run dotnet test with specific project/solution
                    result = subprocess.run(
                        ["dotnet", "test", project_file, "--verbosity", "normal", "--no-build"],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        timeout=300  # Longer timeout for .NET builds
                    )
                    
                    # If --no-build fails, try with build
                    if result.returncode != 0 and ("build" in result.stderr.lower() or "MSB1011" in result.stderr):
                        result = subprocess.run(
                            ["dotnet", "test", project_file, "--verbosity", "normal"],
                            cwd=repo_path,
                            capture_output=True,
                            text=True,
                            timeout=300
                        )
                else:
                    # Fallback: try without specifying project (original behavior)
                    self.log("No project file found, running dotnet test without project specification")
                    result = subprocess.run(
                        ["dotnet", "test", "--verbosity", "normal", "--no-build"],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    
                    # If --no-build fails, try with build
                    if result.returncode != 0 and "build" in result.stderr.lower():
                        result = subprocess.run(
                            ["dotnet", "test", "--verbosity", "normal"],
                            cwd=repo_path,
                            capture_output=True,
                            text=True,
                            timeout=300
                        )
            elif project_type == 'java':
                # Try Maven first, then Gradle for Java projects
                pom_exists = os.path.exists(os.path.join(repo_path, "pom.xml"))
                gradle_exists = os.path.exists(os.path.join(repo_path, "build.gradle")) or \
                               os.path.exists(os.path.join(repo_path, "build.gradle.kts"))
                
                if pom_exists:
                    # Run Maven tests
                    result = subprocess.run(
                        ["mvn", "test", "-B"],  # -B for batch mode (non-interactive)
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        timeout=300,
                        shell=True  # Required for Windows
                    )
                elif gradle_exists:
                    # Run Gradle tests
                    gradle_cmd = "gradlew.bat" if os.name == 'nt' else "./gradlew"
                    if not os.path.exists(os.path.join(repo_path, gradle_cmd.replace("./", ""))):
                        gradle_cmd = "gradle"
                    result = subprocess.run(
                        [gradle_cmd, "test", "--info"],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        timeout=300,
                        shell=True  # Required for Windows
                    )
                else:
                    return {"status": "skipped", "reason": "No Maven (pom.xml) or Gradle (build.gradle) found"}
            else:
                # Run pytest for Python projects
                result = subprocess.run(
                    ["python", "-m", "pytest", "tests/", "-v", "--tb=short"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
            
            combined_output = result.stdout + (result.stderr or "")
            
            test_result = {
                "status": "passed" if result.returncode == 0 else "failed",
                "return_code": result.returncode,
                "output": combined_output[:5000],  # More output for debugging
                "errors": result.stderr[:2000] if result.stderr else None,
                "failed_tests": [],
                "error_messages": []
            }
            
            # Parse failed tests from output if test failed
            if result.returncode != 0:
                test_result["failed_tests"] = self._parse_failed_tests(combined_output)
                test_result["error_messages"] = self._parse_error_messages(combined_output)
            
            return test_result
            
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "reason": "Tests took too long"}
        except FileNotFoundError:
            return {"status": "skipped", "reason": "pytest not installed"}
        except Exception as e:
            return {"status": "error", "reason": str(e)}
    
    def _parse_failed_tests(self, output: str) -> List[str]:
        """Parse failed test names from test output (supports pytest and dotnet test)."""
        failed_tests = []
        
        # pytest patterns: "FAILED tests/test_file.py::TestClass::test_method"
        failed_pattern = r'FAILED\s+([\w/\._:]+)'
        matches = re.findall(failed_pattern, output)
        failed_tests.extend(matches)
        
        # pytest ERROR patterns
        error_pattern = r'ERROR\s+([\w/\._:]+)'
        error_matches = re.findall(error_pattern, output)
        failed_tests.extend(error_matches)
        
        # dotnet test patterns: "Failed MethodName [time]"
        dotnet_failed_pattern = r'Failed\s+([\w_]+)\s*\['
        dotnet_matches = re.findall(dotnet_failed_pattern, output)
        failed_tests.extend(dotnet_matches)
        
        # dotnet test full name pattern: "Failed Namespace.ClassName.MethodName"
        dotnet_full_pattern = r'Failed\s+([\w.]+Tests?\.[\w_]+)'
        dotnet_full_matches = re.findall(dotnet_full_pattern, output)
        failed_tests.extend(dotnet_full_matches)
        
        return list(set(failed_tests))[:20]  # Limit to 20 unique failures
    
    def _parse_error_messages(self, output: str) -> List[str]:
        """Parse error messages from pytest output."""
        error_messages = []
        
        # Match common error patterns
        patterns = [
            r'(AssertionError:.+?)(?:\n|$)',
            r'(TypeError:.+?)(?:\n|$)',
            r'(ValueError:.+?)(?:\n|$)',
            r'(AttributeError:.+?)(?:\n|$)',
            r'(ImportError:.+?)(?:\n|$)',
            r'(ModuleNotFoundError:.+?)(?:\n|$)',
            r'(NameError:.+?)(?:\n|$)',
            r'(KeyError:.+?)(?:\n|$)',
            r'(IndexError:.+?)(?:\n|$)',
            r'(RuntimeError:.+?)(?:\n|$)',
            r'(Exception:.+?)(?:\n|$)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, output, re.MULTILINE)
            error_messages.extend(matches)
        
        # Also capture "assert" statements that failed
        assert_pattern = r'(assert\s+.+?)(?:\n|$)'
        assert_matches = re.findall(assert_pattern, output, re.MULTILINE)
        error_messages.extend([f"Failed: {m}" for m in assert_matches[:5]])
        
        return list(set(error_messages))[:15]  # Limit to 15 unique error messages

    def _count_tests(self, test_files: Dict[str, str], project_type: str = 'python') -> int:
        """Count total test methods across all generated test files."""
        total = 0
        for content in test_files.values():
            if project_type == 'csharp':
                # Count [Fact] and [Theory] attributes for xUnit
                total += len(re.findall(r'\[Fact\]', content))
                total += len(re.findall(r'\[Theory\]', content))
            elif project_type == 'java':
                # Count @Test and @ParameterizedTest annotations for JUnit
                total += len(re.findall(r'@Test', content))
                total += len(re.findall(r'@ParameterizedTest', content))
            else:
                # Count def test_ for pytest
                total += len(re.findall(r'def test_', content))
        return total
