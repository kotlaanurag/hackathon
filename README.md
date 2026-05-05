# Multi-Agent Development Pipeline

An AI-powered automated development workflow with specialized agents for code implementation, review, testing, and PR management.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR                              │
│              (Coordinates entire pipeline)                       │
└─────────────────────┬───────────────────────────────────────────┘
                      │
        ┌─────────────▼─────────────┐
        │         ANALYST           │
        │  • Reads repo structure   │
        │  • Identifies files       │
        │  • Creates impl. plan     │
        └─────────────┬─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │          CODER            │
        │  • Creates branch         │
        │  • Reads relevant files   │
        │  • Writes code changes    │
        │  • Commits to git         │
        └─────────────┬─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │         REVIEWER          │
        │  • Reads git diff         │
        │  • Checks code quality    │
        │  • Returns findings       │
        └─────────────┬─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │          TESTER           │
        │  • Reads new code         │
        │  • Writes test files      │
        │  • Commits tests          │
        └─────────────┬─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │       PR MANAGER          │
        │  • Creates PR via API     │
        │  • Auto-merges on pass    │
        └───────────────────────────┘
```

## 📁 Project Structure

```
Hackathon/
├── app.py                      # FastAPI main application
├── requirements.txt            # Python dependencies
├── .env.template              # Environment variables template
├── agents/                    # Agent modules
│   ├── __init__.py
│   ├── base.py               # Base agent class and state
│   ├── orchestrator/         # Orchestrator agent
│   │   ├── __init__.py
│   │   └── agent.py
│   ├── analyst/              # Analyst agent
│   │   ├── __init__.py
│   │   └── agent.py
│   ├── coder/                # Coder agent
│   │   ├── __init__.py
│   │   └── agent.py
│   ├── reviewer/             # Reviewer agent
│   │   ├── __init__.py
│   │   └── agent.py
│   ├── tester/               # Tester agent
│   │   ├── __init__.py
│   │   └── agent.py
│   └── pr_manager/           # PR Manager agent
│       ├── __init__.py
│       └── agent.py
└── workflow/                  # Workflow orchestration
    ├── __init__.py
    └── pipeline.py           # LangGraph pipeline
```

## 🚀 Getting Started

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.template` to `.env` and fill in your credentials:

```bash
cp .env.template .env
```

Required variables:
- `GITHUB_TOKEN`: Your GitHub personal access token
- `GITHUB_REPO_OWNER`: Repository owner/organization
- `GITHUB_REPO_NAME`: Repository name

### 3. Run the Server

```bash
python -m uvicorn app:app --reload --port 8000
```

## 📡 API Endpoints

### Start Pipeline
```bash
POST /pipeline/run
{
    "issue": "Create a login feature with password validation",
    "repo_path": "/path/to/repo"  # optional
}
```

### Check Pipeline Status
```bash
GET /pipeline/{run_id}
```

### Single Request (Synchronous)
```bash
POST /agent
{
    "issue": "Implement user authentication"
}
```

### List Agents
```bash
GET /agents
```

### Get Workflow Visualization
```bash
GET /workflow
```

## 🤖 Agent Details

### 1. Orchestrator
- **Role**: Main coordinator
- **Responsibilities**:
  - Parse issue/requirements
  - Detect issue type (feature, bugfix, refactor)
  - Estimate complexity
  - Delegate to appropriate agents

### 2. Analyst
- **Role**: Repository analysis and planning
- **Responsibilities**:
  - Scan repository structure
  - Identify relevant files
  - Create detailed implementation plan
  - Suggest new files to create

### 3. Coder
- **Role**: Code implementation
- **Responsibilities**:
  - Create feature branch
  - Read existing code
  - Generate new code
  - Commit changes with descriptive messages

### 4. Reviewer
- **Role**: Code quality assurance
- **Responsibilities**:
  - Analyze git diff
  - Check code style (line length, whitespace)
  - Detect security issues (hardcoded secrets)
  - Verify documentation
  - Check naming conventions

### 5. Tester
- **Role**: Test generation
- **Responsibilities**:
  - Analyze code for testable units
  - Generate pytest test files
  - Create test fixtures
  - Commit test files

### 6. PR Manager
- **Role**: GitHub integration
- **Responsibilities**:
  - Push branch to remote
  - Create Pull Request via API
  - Build detailed PR description
  - Monitor review status
  - Auto-merge on approval

## 🔄 Workflow Flow

1. **Issue Received** → Orchestrator parses requirements
2. **Analysis** → Analyst reads repo, creates implementation plan
3. **Coding** → Coder creates branch, implements changes, commits
4. **Review** → Reviewer checks code quality, returns findings
5. **Testing** → Tester generates test files, commits
6. **PR Creation** → PR Manager creates PR, auto-merges on approval

## 📝 Example Usage

```python
import httpx

# Start a pipeline run
response = httpx.post(
    "http://localhost:8000/pipeline/run",
    json={
        "issue": "Add user authentication with JWT tokens",
        "repo_path": "/path/to/my/project"
    }
)
run_id = response.json()["run_id"]

# Check status
status = httpx.get(f"http://localhost:8000/pipeline/{run_id}")
print(status.json())
```

## 🛠️ Development

### Adding a New Agent

1. Create a new folder under `agents/`:
   ```
   agents/new_agent/
   ├── __init__.py
   └── agent.py
   ```

2. Inherit from `BaseAgent`:
   ```python
   from agents.base import BaseAgent, AgentState
   
   class NewAgent(BaseAgent):
       def __init__(self):
           super().__init__(
               name="NewAgent",
               description="Description"
           )
       
       async def execute(self, state: AgentState) -> AgentState:
           # Implementation
           return state
   ```

3. Add to workflow in `workflow/pipeline.py`

## 📄 License

MIT License
