# AI-Powered Policy Connector Services Delivery (IRIS Integration)

**Theme:** AI-Accelerated Software Delivery & Quality Assurance

## The "Wow Factor": Zero-Touch to Self-Healing Lifecycle

A live, continuous demonstration of a user story moving from a simple text prompt to a deployed, self-healing service in minutes.

**The Execution:**
1. **Prompt to Code:** Type a raw requirement into EverAssist. It instantly generates the Markdown (MD) requirements and field mappings.
2. **Code to Pipeline:** GitHub Copilot auto-generates the connector code, interface mocks, and test cases based on the MD files.
3. **Break & Auto-Fix:** Purposefully introduce bad synthetic data that causes a mock deployment to fail on Everest's CaaS platform.
4. **Self-Healing:** Dynatrace detects the failure, triggers an alert via Microsoft Teams with an EverAssist-generated Root Cause Analysis (RCA), and provides an interactive "One-Click Remediation" button to roll back or patch the issue immediately.

---

## Problem Statement

Delivering policy connection services requires manual coding, interface mocking, and testing processes, leading to significant inefficiencies:

1. **Manual Development Overhead**
   - Manual coding, interface mocking, and testing processes are time-consuming and error-prone.

2. **Complex Requirements & Field Mappings**
   - Generating comprehensive requirements, complex field mappings, and validating business logic for the IRIS Policy Admin system is highly time-consuming.

3. **Extended Delivery Timelines**
   - Phased rollouts for various Lines of Business (LoBs) suffer from extended timelines due to inefficient delivery planning.

4. **Resource-Intensive Testing**
   - Creating, maintaining, and updating functional test cases and automated regression suites mapped directly to user story acceptance criteria is heavily resource-intensive.

5. **Environment Setup Bottlenecks**
   - Checking that various integration and test environments are correctly set up with required access for teams and synchronized test data takes time from multiple teams.

---

## Proposed Solution

An **AI-accelerated delivery lifecycle** for the Policy Connector Services application, utilizing **GitHub Copilot** for engineering and **EverAssist** for business analysis, planning, and QA optimization.

### Core Capabilities

#### AI-Assisted Engineering (GitHub Copilot)
- All AI coding is based on strict guidelines delivered in standard MD files with a standard format for architectural and security requirements/constraints and MD files in the codebase for requirements giving clear scope and definition.
- Rapidly generate code and unit test cases.
- Automatically mock interfaces for the IRIS Policy Admin system.
- Validate and check complex business logic in real-time.

#### Intelligent Requirements & Planning (EverAssist)
- Assist Business Analysts in creating clear, precise requirements and automated field mappings.
- Generate highly focused delivery plans to reduce the overall number of delivery phases while maintaining a structured, phased rollout for different LoBs.

#### AI-Driven QA & Testing
- Automatically generate functional test cases designed directly from user story acceptance criteria.
- Create and dynamically update automated regression test suites to ensure continuous quality.

#### Human-in-the-Loop
- Outputs (code, mappings, test suites, and plans) are generated for review, refinement, and validation by engineers, BAs, and QA teams.
- No unverified code is pushed to production without human oversight.
- Testing and generated code are checked before deployment.

---

## Target Audience/Users

- **Software Engineers / Developers**
- **Quality Assurance (QA) Engineers**
- **Business Analysts & Product Owners**
- **Project Managers / Delivery Leads**

---

## Potential Impact/Benefits

### Productivity & Efficiency
- Dramatically reduced time spent coding, mocking interfaces, and writing test scripts.
- Faster time-to-market for Policy Connector Services.

### Optimized Delivery Planning
- Fewer delivery phases without sacrificing the safety of LoB-specific rollouts.
- Better-scoped requirements reducing development rework.

### Quality & Consistency
- Accurate, AI-validated field mappings for IRIS.
- Direct traceability from acceptance criteria to automated regression and functional test cases.

### Scalability
- The AI-assisted delivery framework can be templated and scaled to other systems beyond IRIS.

---

## Comprehensive Hackathon Execution Plan

### Phase 1: Intelligent Planning & Requirements (BA & PM Focus)
- **Action:** Feed raw business rules into EverAssist to generate standardized Markdown (MD) files containing architectural constraints, security requirements, and clear User Stories with Acceptance Criteria.
- **AI Value:** Reduces requirement gathering and IRIS field mapping from days to minutes.
- **Deliverable:** A complete, AI-validated delivery plan with consolidated LoB rollout phases.

### Phase 2: AI-Assisted Engineering (Developer Focus)
- **Action:** Use GitHub Copilot within the IDE, constrained by the generated MD guidelines.
- **AI Value:** Auto-generate boilerplate code, complex business logic, and mock interfaces for the IRIS Policy Admin system.
- **Deliverable:** Rapidly prototyped Policy Connector Services code ready for deployment on Everest's CaaS Kubernetes platform.

### Phase 3: AI-Driven QA & Environment Automation (QA Focus)
- **Action:** EverAssist parses the Acceptance Criteria to generate functional test cases. Copilot writes the automated regression suite (e.g., Selenium, Cypress, or JUnit).
- **AI Value:** Ensures 100% traceability from requirement to test. Auto-generates synthetic policy data to solve environment setup delays.
- **Deliverable:** An automated test suite that runs seamlessly in the standard CI/CD pipeline.

### Phase 4: Intelligent Operations & Self-Healing (Ops Focus)
- **Action:** Integrate the service with Kafka (for event streaming) and Dynatrace (for monitoring).
- **AI Value:** If policy creation fails, the system automatically correlates the error in Dynatrace, logs it into an AI Knowledge Base (KB), and sends an actionable Teams/Outlook notification.
- **Deliverable:** A smart-alerting mechanism where the AI matches the incident to historical errors and offers the user 2-3 specific resolution options to click and enact.

---

## Additional Enhancement Ideas

To further strengthen the prototype, consider adding these capabilities:

1. **AI Shift-Left Security**
   - As Copilot generates code, use an AI hook to instantly scan for vulnerabilities (e.g., hardcoded credentials, injection flaws) before the code is even committed, outputting the fixes in real-time.

2. **Dynamic "Living" Documentation**
   - Have EverAssist automatically generate and update system architecture diagrams (via Mermaid.js markdown) and API Swagger documentation directly from the codebase.

3. **Smart Environment Access Provisioning**
   - Create an EverAssist script that automatically reads the team roster and generates the necessary Role-Based Access Control (RBAC) configuration files for the integration/test environments, solving the environment setup bottleneck.

4. **"Zero-to-Hero" Developer Onboarding AI Sandbox (Scaling)**
   - **The Idea:** Prove the scalability of the solution.
   - **Action:** Package strict Markdown (MD) architectural guidelines, mock data, and prompt templates into an interactive "Developer Onboarding Repo."
   - **AI Value:** Show that a brand new Everest engineer can clone this repo, interact with EverAssist to understand the IRIS system, and deploy their first mock service within hours instead of weeks.

---

## Testing Considerations & Data Sources

- Synthetic policy data and mock interface definitions for the IRIS Policy Admin system.
- Sample user stories and acceptance criteria to test EverAssist's QA test generation capabilities.
- Simulated GitHub Copilot prompts and required MD documents for checking business logic and automated testing creation.
- Focus on comparing the speed, output quality, and test coverage of the AI-assisted process versus traditional manual delivery.

---

## Hackathon Delivery Summary

Quick-reference workflow comparison for presentation:

| Delivery Stage | Traditional Process | AI-Accelerated Process (Hackathon) | Tools Used |
|----------------|---------------------|-------------------------------------|------------|
| **Requirements** | Manual BA interviews, manual Excel field mapping. | Instant MD generation, automated IRIS field mapping. | EverAssist |
| **Development** | Manual coding, manual mocking of IRIS interfaces. | Auto-generated code, instant interface mocking via MD rules. | GitHub Copilot |
| **Testing (QA)** | Manual test case creation, resource-heavy regression. | Auto-generated tests mapped to Acceptance Criteria, synthetic data. | EverAssist, Copilot |
| **Deployment** | Standard CI/CD to CaaS. | Standard CI/CD to CaaS (maintains Everest standards). | Kubernetes (CaaS) |
| **Operations** | Manual log checking, delayed incident response. | Proactive Dynatrace/Kafka alerts, Teams notifications, self-healing options. | Dynatrace, Kafka, EverAssist |

---

## Additional Notes

- The prototype should prioritize testing capabilities of the mocked IRIS interfaces using GitHub Copilot and EverAssist's requirement drafting.
- Long-term enhancements may align with enterprise-wide Agile/DevOps transformations, but this hackathon prototype should stand independently as a proof-of-concept for the Policy Connector Services.
- **PCS should remain delivered on Everest's managed Kubernetes platform (CaaS) and using the standard software development pipelines and tools (even where augmented).**

---

## Getting Started

### Prerequisites
- .NET 8.0 SDK
- Docker Desktop
- Access to Azure DevOps (Everest-Common-Packages feed)
- Git with SSL certificate bundle configured for Zscaler proxy

### Git Configuration for Zscaler Proxy
```powershell
git config --global http.sslCAInfo "C:/dev/certificates/ca-bundle.pem"
```

### Local Development
```bash
# Clone the repository
git clone https://github.com/EvGr-Hackathon-2026/InfoSys_Hackathon_2026.git
cd InfoSys_Hackathon_2026

# Run with Docker Compose
docker-compose -f docker-compose.local.yml up

# Access Swagger UI
# http://localhost:5000/swagger
```

### Running Tests
```bash
# Run all tests with code coverage
dotnet test --collect:"XPlat Code Coverage" --settings coverlet.runsettings

# Build solution
dotnet build --configuration Release
```

---

## Repository Structure

- **PolicyConnectorService/** - Main REST API project (.NET 8.0)
- **PolicyConnectorService.Tests/** - Unit tests with xUnit and Moq
- **InfoSys_Hackathon_2026.yaml** - Azure DevOps CI/CD pipeline
- **docker-compose.local.yml** - Local development environment
- **Dockerfile** - Production container image
- **nuget.config** - Azure Artifacts package source configuration
- **coverlet.runsettings** - Code coverage settings

### Validation Rules (`config/validation_rules.yml`)
- Required documents by policy type
- Folder structure standards
- File naming conventions
- Document type specifications

## Validation Logic

### File Completeness
Expected documents:
- Binder/Quote
- Application
- Medical Records (if required)
- Inspections (if required)
- Policy Document
- Endorsements (if applicable)

### Structure Standards
- Consistent folder naming: `[PolicyNumber]_[InsuredName]`
- Document classification folders
- Standardized file naming conventions
- Metadata tracking

## Data Sources & Testing
- **Peak System**: Live policy database (production)
- **Shared Drive**: File source (current)
- **Azure Blob Storage**: Staging area for analysis and archive
- **Sample Data**: `data/sample_files/` for testing

## Timeline & Milestones
- **Phase 1** (Apr-May 2026): Development & testing
- **Phase 2** (Jun 2026): Pilot with limited file set
- **Phase 3** (Jul-Aug 2026): Full production rollout
- **Phase 4** (Sep 2026-Jan 2027): Continuous improvement & DMS prep

## Reporting

### Daily Report Contents
- Files processed: X
- Files matched: Y (Z%)
- Missing files: N (%)
- Incomplete files: M (%)
- Structure violations: K (%)
- Detailed findings by issue type

### Report Destinations
- Excel export for Operations review
- Email distribution to UA Lead
- Dashboard/Portal view (future)

## DMS Migration Readiness
- Standardized file structure
- Complete metadata tagging
- Missing document identification
- Compliance audit trail

## Support & Maintenance
- Scheduled nightly runs (11 PM UTC)
- Daily Operations report delivery
- Monthly validation rule updates
- Quarterly performance metrics review

## Future Enhancements
- Machine learning for document classification
- OCR for content validation
- Real-time compliance dashboard
- Predictive issue identification
- Auto-remediation for common issues

## License
Internal use only

## Contact
Operations Team (UA Lead)