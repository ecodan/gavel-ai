---
stepsCompleted: [1, 2, 3, 4, 7, 8, 9, 10]
inputDocuments:
  - _bmad-output/planning-artifacts/product-brief-gavel-ai-2025-12-27.md
  - docs/.private/app-overview.md
  - docs/.private/arch-overview.md
  - docs/.private/TDD-unified-architecture.md
workflowType: 'prd'
lastStep: 1
---

# Product Requirements Document - gavel-ai

**Author:** Dan
**Date:** 2025-12-27

## Executive Summary

**gavel-ai** is an open-source, provider-agnostic AI evaluation framework designed to eliminate the barrier to entry for evaluating LLM-based systems. Unlike closed, complex frameworks, gavel-ai gets developers from zero to their first rigorous evaluation in 15 minutes—with a clean CLI, intelligent scaffolding, and powerful evaluation workflows built on proven design patterns.

Inspired by successful evaluation system design but rebuilt from the ground up for the open-source community, gavel-ai removes the friction that prevents most AI projects from evaluating their systems at all.

### What Makes This Special

- **Open Source First** — Built for the community, not locked to proprietary systems
- **Any Provider** — True provider-agnostic design (Claude, GPT, Gemini, local models)
- **Local & In-Situ Evals** — Evaluate both direct LLM calls and deployed systems ("closed box" testing)
- **OpenTelemetry Native** — Full observability and telemetry support across local and in-situ testing
- **Transparent by Default** — Filesystem-based architecture means all configs, scenarios, results, and metadata are human-readable and available for analysis, debugging, and integration with existing tools
- **15-Minute Onboarding** — Scaffolded for beginners with intelligent CLI and sensible defaults
- **Proven Design** — Built by the designer of the original evaluation framework, implementing lessons learned
- **Three Core Workflows** — OneShot (model comparison), Conversational (multi-turn testing), Autotune (prompt optimization)

## Project Classification

**Technical Type:** Developer Tool (Framework/SDK for AI evaluation)
**Domain:** Scientific (Rigorous evaluation methodology, reproducibility, validation)
**Complexity:** Medium (Sophisticated architecture with clear MVP scope)
**Project Context:** Greenfield - New open-source project

---

## Success Criteria

### User Success

A developer using gavel-ai achieves success when they can:

1. **Set up and run evals reliably** — From install to first eval in 15 minutes (aspirational). No surprises, no cryptic errors. Evals work as expected, or failures are clear and actionable.

2. **Trust the results** — Full transparency into the process. They can inspect inputs, outputs, judge reasoning, and metrics. Results are reproducible (same config + scenarios = same results every time).

3. **Get clear reports** — Reports answer their core question: "Which is better?" with context and reasoning, not just scores. Trade-offs are explicit.

4. **Iterate fast** — Config change → run eval → review results. The cycle is frictionless, removing friction from the iteration loop.

### Technical Success

gavel-ai v1 is successful when:

1. **OneShot Workflow is Robust** — Local and in-situ evaluations work reliably with complete artifact isolation via RunContext

2. **OpenTelemetry Integration Complete** — Full observability across local and in-situ testing with unified telemetry storage

3. **Extensible Architecture** — Clear abstractions enable community to add new workflows and evaluation primitives without modifying core framework

4. **Solid Test Foundation** — 70%+ unit test coverage on non-trivial code

5. **Transparent & Reproducible** — All configurations, scenarios, results, and artifacts are stored as simple structured files on filesystem

### Measurable Outcomes

- Developers can configure and run first OneShot eval from install in ~15 minutes (aspirational target)
- All core OneShot features working: local testing, in-situ testing, scenario-based evaluation, judge execution, run artifact management
- OpenTelemetry instrumentation capturing complete execution traces
- Architectural extensibility demonstrated (documented patterns for adding new workflows)
- Test coverage at or above 70% on non-trivial code paths

---

## Product Scope

### MVP - Minimum Viable Product (v1)

**Core Deliverables:**
- OneShot evaluation workflow (local and in-situ testing)
- RunContext abstraction for managing runs and artifacts
- OpenTelemetry instrumentation and collection
- DeepEval integration for LLM-as-judge evaluation
- CLI interface with intelligent scaffolding
- File-based configuration (agents.json, eval_config.json, scenarios.json)
- HTML and Markdown report generation
- Extensible architecture with clear patterns for future workflows

**Quality Gates:**
- 70%+ unit test coverage on non-trivial code
- Reproducible runs (same config + scenarios = identical results)
- Complete OpenTelemetry integration working
- Clear documentation for extending framework

### Growth Features (Post-MVP / v2-v3)

**v2: Conversational Workflow**
- Multi-turn dialogue evaluation
- Agent behavior assessment
- Context window management
- Dynamic user simulation

**v3: Autotune Workflow**
- Iterative prompt optimization
- Prompt versioning and evolution tracking
- Automated improvement suggestions
- Performance convergence monitoring

### Vision (Future)

**Post-v3 Enhancements:**
- GUI and API interfaces (separate presentation tier from business logic)
- CI/CD integration support
- Storage adapter ecosystem (databases, prompt servers, alternative filesystems)
- Advanced reporting and visualization
- Community-contributed judge strategies and processors
- Multi-provider judge execution (ensemble judging)
- Real-time streaming evaluation support

---

## User Journeys

### Journey 1: Alex Chen - From Guessing to Confidence

Alex is a backend engineer at a mid-size fintech startup who just finished building an AI-powered fraud detection feature using Claude. The feature works in their local testing, but Alex is anxious about deployment—what if it performs differently in production? What if they chose the wrong model? They've been staring at output logs for hours, trying to convince themselves it's good enough.

One afternoon, a colleague mentions gavel-ai. Skeptical but desperate, Alex installs it in 12 minutes and sets up their first evaluation comparing Claude 3.5 Sonnet vs GPT-4 on 50 real fraud scenarios from their test data. Within 15 minutes of running the eval, Alex has a beautiful HTML report showing Claude winning on both speed and accuracy for their specific domain. More importantly, they can see exactly why—the judge's reasoning is transparent, and they can inspect every scenario, output, and decision.

With this data in hand, Alex feels genuinely confident deploying Claude to production. Three months later, when the model needs updating, Alex's first step is running a new eval—now a routine 20-minute process instead of days of manual testing.

**Requirements Revealed:** Easy setup, quick first eval execution, clear reports with judge reasoning, confidence in production readiness.

---

### Journey 2: Sam Patel - Recovering from a Bad Deployment

Sam is a product manager at a health tech company who approved a new LLM model for their patient-facing chatbot based on demo videos from the vendor. Two weeks into production, support tickets skyrocket—the model is giving borderline medical advice that sounds confident but isn't safe enough. The rollback costs them a week of user trust and engineering time.

After this painful lesson, Sam discovers gavel-ai and becomes its advocate. Now, before any model change, Sam requires the engineering team to run comprehensive evaluations showing performance on safety-critical scenarios. Sam doesn't understand Python or run evals themselves, but they can read the generated reports and approve/reject changes based on clear metrics.

When the next model update comes, Sam reviews the gavel-ai eval report showing the new model handles safety edge cases 15% better than the current one. With confidence, Sam approves the deployment. The smooth rollout reinforces gavel-ai's value to the entire organization.

**Requirements Revealed:** Human-readable reports, clear trade-off analysis, metrics that answer "is this safer/better?", ability for non-technical stakeholders to trust and review results.

---

### Journey 3: Jordan Rivera - Building the Next Evaluation Primitive

Jordan is an open-source enthusiast and ML researcher who uses gavel-ai's OneShot workflow but realizes they need custom evaluation logic for their specific domain (multi-modal reasoning). Instead of forking the project, Jordan wants to contribute a new evaluation primitive back to the community.

They dive into gavel-ai's documentation and find the extensibility patterns crystal clear—the architecture was designed exactly for this. Within a few hours, Jordan implements a custom `MultimodalEvaluator` class, writes tests, and submits a pull request. The gavel-ai maintainers quickly review it and merge it.

Six months later, Jordan sees their contribution being used by dozens of other researchers and is genuinely excited to be part of the growing ecosystem. They stay engaged, reviewing PRs and helping other contributors.

**Requirements Revealed:** Clear architectural abstractions, excellent documentation for extending, modular design that invites contribution, community that values additions.

---

### Journey 4: Priya Desai - Standardizing Evaluations Across Her Team

Priya leads an AI engineering team at a large enterprise with 8 developers working on different AI features across the product. Before gavel-ai, each developer was evaluating their changes differently—some manually, some with custom scripts, no consistency. Priya needed a standardized, reproducible approach to eval that could work across all projects.

Priya pilots gavel-ai on one project, then rolls it out across the team. She creates a shared evaluation config template that all projects use, defines standard scenarios relevant to their domain, and sets up a Makefile that runs `gavel oneshot run` in CI. Within a month, every PR includes eval results, and the team has a transparent record of model performance over time.

When budget cuts force a reassessment of LLM vendors, Priya's team has 6 months of eval data showing how each model performs on their real workloads—data that justifies staying with Claude instead of switching. The eval infrastructure becomes a strategic asset.

**Requirements Revealed:** Reproducible config-based setup, CI/CD integration, ability to store and compare runs over time, team-wide standardization, clear artifact organization for historical analysis.

---

### Journey 5: Dr. Lisa Wong - Publishing Rigorous Evaluation Methodology

Dr. Wong is an AI safety researcher at a university who's publishing a paper on evaluating LLM alignment in conversational contexts. She needs evaluation infrastructure that is transparent, auditable, and reproducible—her results need to survive peer review scrutiny.

She chooses gavel-ai because everything is stored on the filesystem and in human-readable files. She can commit her entire evaluation setup (agents.json, scenarios.json, judges, run artifacts) to GitHub, and reviewers can reproduce her results exactly. The OpenTelemetry instrumentation gives her complete visibility into what happened during evaluation—no black boxes, no hidden hyperparameters.

Her paper's evaluation methodology becomes a model of rigor. Peer reviewers are impressed by the transparency, and other researchers start citing gavel-ai's design principles in their own work.

**Requirements Revealed:** Complete transparency and auditability, reproducible runs, human-readable artifacts, ability to archive and share entire evaluation setups, comprehensive observability.

---

### Journey 6: Morgan Kim - Integrating Evaluations into CI/CD

Morgan is a DevOps engineer at a rapidly scaling AI startup where LLM models are deployed to production frequently. They're tasked with automating eval execution in the CI/CD pipeline—when a developer updates a prompt or switches models, the pipeline should automatically run evaluations and block bad deployments.

Morgan loves that gavel-ai's CLI is straightforward: `gavel oneshot run --eval my_eval` works perfectly in shell scripts. The exit codes are predictable, output is structured JSON/markdown they can parse, and everything integrates cleanly with their existing GitHub Actions workflows.

Within a week, Morgan has set up gavel-ai to run on every PR. Model regressions are caught immediately. The team gains confidence that bad changes can't sneak through, and engineers feel empowered to iterate because evaluations are instant feedback, not a manual testing bottleneck.

**Requirements Revealed:** Clean CLI interface, predictable exit codes, structured output formats, scriptability, fast execution, integration with standard CI/CD tools, clear error messages for automation.

---

### Journey Requirements Summary

Each journey reveals distinct capability areas needed for gavel-ai:

| User Type | Key Requirements |
|-----------|-----------------|
| **Developer (Primary)** | Fast setup, clear reports, reproducible results, easy iteration |
| **Product Manager** | Human-readable reports, metrics for decision-making, non-technical accessibility |
| **Contributor** | Clear architectural abstractions, extensibility patterns, documentation, modularity |
| **Enterprise/Team Lead** | Config-based reproducibility, standardization, historical tracking, team scaling |
| **Researcher** | Complete transparency, auditability, artifact preservation, observability |
| **DevOps/CI Engineer** | Clean CLI, structured output, scriptability, fast execution, exit codes |

These journeys collectively define the full feature set and design principles that make gavel-ai successful for all stakeholders.

---

## Developer Tool Specific Requirements

### Installation & Distribution

gavel-ai will be distributed as a Python package via PyPI with multiple installation methods:

**Primary Installation:**
- `pip install gavel-ai` — Standard PyPI installation
- Python 3.10+ (minimum, with no strict dependency barriers)
- No git clone required; production-ready distribution

**Quickstart Approach:**
- Single `pip install` brings you from zero to working tool
- Bundled quickstart examples in package (local and in-situ examples)
- Clear, guided setup that reaches "first eval running" in ~15 minutes
- Sensible defaults for common use cases

**Package Quality:**
- Wheels for major Python versions and platforms (Windows, macOS, Linux)
- Clear dependency management (minimal required dependencies; optional enhancements)
- Version pinning strategy for reproducibility

### API Surface

gavel-ai exposes three complementary interfaces for different automation contexts:

**1. CLI Interface**
- Command pattern: `gavel [oneshot|conv|autotune] [create|run|judge|report] --eval <name> [options]`
- Primary interface for interactive development
- Designed for scripting and CI/CD integration
- Predictable exit codes and structured output

**2. HTTP API - Command Execution**
- RESTful API exposing same operations as CLI
- Endpoints: `POST /api/workflows/{workflow}/actions/{action}`
- Enables remote execution and integration with other systems
- JSON request/response for eval execution, judging, reporting
- Useful for dashboard backends, hosted services, team setups

**3. HTTP API - Lower-Level Primitives**
- Programmatic access to core evaluation primitives
- Direct access to processors, judges, evaluation execution
- Enables building higher-level automation on top of gavel-ai
- Useful for custom evaluation orchestration, batch processing, experimental workflows

**4. HTTP API - In-Situ Agentic Operations**
- Support for driving agent behavior in deployed systems
- Agents can call gavel-ai endpoints to trigger evaluations
- Bidirectional: gavel-ai can observe and evaluate agent actions
- Enables continuous evaluation of production agent behavior

**5. Python SDK/Library Interface** (Optional v1, Recommended)
- Direct Python imports for programmatic access: `from gavel import ...`
- Classes and functions matching HTTP API surface
- Type hints throughout for IDE support and type checking
- Useful for notebooks, custom evaluation scripts, research

### Documentation Strategy

**Quick-Start Guide**
- From install to first eval in 15 minutes
- Step-by-step walkthrough with example eval
- Local testing example and in-situ testing example
- Common troubleshooting

**CLI Reference**
- Complete command documentation
- Examples for each command
- Configuration file format reference (agents.json, scenarios.json, eval_config.json)

**HTTP API Documentation**
- OpenAPI/Swagger specification for machine readability
- Endpoint reference with request/response examples
- Authentication and error handling patterns
- Integration examples (CI/CD, dashboard backends, agentic systems)

**Architecture Guide**
- System design and core abstractions (RunContext, Workflows, Processors, Judges)
- Extension patterns for new workflows and evaluation primitives
- Design philosophy and key principles
- Data flow diagrams for local and in-situ evaluation

**Code Examples**
- Example evaluations (local and in-situ)
- Custom processor/judge implementation
- CI/CD integration examples
- HTTP API usage examples

**Contribution Workflow**
- Development setup and running tests
- Contributing new workflows or primitives
- Pull request process
- Community guidelines

### Developer Experience

**Error Handling Philosophy**
- Errors are informative and actionable
- Clear messages explain what failed and why
- Guidance on recovery steps built into error messages
- Different error categories (configuration, execution, validation, network)
- Full stack traces available in debug mode

**Configuration & Reproducibility**
- YAML/JSON configuration files (human-readable, versionable)
- All configs stored on filesystem for inspection and debugging
- Clear configuration schema documentation
- Sensible defaults to minimize required configuration

**Extensibility as First-Class Concept**
- Clear patterns for adding new workflows
- Clear patterns for adding evaluation primitives (judges, processors)
- Documented extension points with examples
- Community contributions encouraged and valued

**Testing Support**
- Unit test helpers for custom workflows/primitives
- Test fixtures for common evaluation scenarios
- Mock providers for testing without API calls

### Python Package Details

**Dependencies:**
- Minimal core dependencies (pydantic-ai or similar for providers, deepeval for judges)
- Optional dependencies for advanced features (visualization, database adapters)
- Version constraints that ensure reproducibility

**Module Structure:**
- Clear public API surface
- Internal modules documented for contributors
- Type hints throughout codebase
- Consistent naming conventions

**Package Versioning:**
- Semantic versioning (major.minor.patch)
- Clear changelog documenting breaking changes
- Deprecation period for breaking changes
- Backwards compatibility where practical

---

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Problem-Solving MVP focused on eliminating the entry barrier to AI evaluation

gavel-ai v1 solves the core problem: developers can evaluate their AI systems confidently in 15 minutes. We achieve this with OneShot workflow, transparent file-based architecture, OpenTelemetry integration, and clear reporting—nothing more, nothing less.

**Intentional Deferral Strategy:**
- HTTP API planned in architecture but implemented in v2+ (CLI is primary interface for v1)
- Python SDK deferred to v2+ (focus on CLI accessibility)
- Conversational and Autotune workflows deferred to v2+ (OneShot covers immediate need)
- Comprehensive documentation deferred to v3 (focus on essentials in v1)

This keeps v1 focused and shippable while building foundation for future expansion.

### MVP Feature Set (Phase 1 - v1)

**Core Capabilities:**
- OneShot evaluation workflow (local and in-situ testing)
- RunContext abstraction for managing evaluation runs
- OpenTelemetry instrumentation for local and in-situ telemetry collection
- DeepEval integration for LLM-as-judge evaluation
- File-based configuration system (agents.json, scenarios.json, eval_config.json)
- HTML and Markdown report generation
- CLI interface: `gavel [oneshot] [create|run|judge|report] --eval <name> [options]`
- Extensible architecture with clear patterns for future workflows and primitives

**User Journeys Supported in v1:**
- Alex Chen (Developer): Setup, run, iterate on evals
- Sam Patel (Product Manager): Review reports and make decisions
- Priya Desai (Team Lead): Config-based reproducibility and team setup
- Dr. Lisa Wong (Researcher): Complete transparency and auditability
- Morgan Kim (DevOps): CLI-driven CI/CD integration

**Quality Gates:**
- 70%+ unit test coverage on non-trivial code
- OpenTelemetry integration fully working
- Reproducible runs (identical results for same config + scenarios)
- Clear error messages and documentation for common issues

### Post-MVP Features

**Phase 2 (v2): Conversational Workflow**
- Multi-turn dialogue evaluation
- Agent behavior assessment
- Context window management
- HTTP API - Command Execution (expose CLI operations over HTTP)
- Enhanced documentation

**Phase 3 (v3): Autotune Workflow**
- Iterative prompt optimization
- Prompt versioning and evolution tracking
- Automated improvement suggestions
- HTTP API - Lower-Level Primitives (programmatic access to evaluation primitives)
- Python SDK/Library Interface (optional but recommended)
- Comprehensive documentation suite

**Post-v3 Vision:**
- HTTP API - In-Situ Agentic Operations (agent-driven evaluation)
- GUI and API interfaces (separate presentation tier)
- Storage adapter ecosystem (databases, prompt servers, alternative filesystems)
- Community-contributed judge strategies and processors
- Advanced reporting and visualization
- Real-time streaming evaluation support

### Architecture Planning for Future Phases

**HTTP API Architecture (Planned for v2+, Design Now):**
- REST API design for CLI command exposure
- Low-level primitives API design
- Agentic operation endpoints design
- Authentication and authorization patterns
- All planned in v1 architecture but implemented incrementally

**Python SDK Architecture (Planned for v2+, Design Now):**
- Module structure and public API surface
- Type hints and IDE support patterns
- Alignment with HTTP API surface

### Documentation Strategy for v1

**Focus on Essentials:**
- Quick-Start Guide (install to first eval in 15 minutes)
- CLI Reference (commands, options, configuration format)
- Architecture Guide (core abstractions for future contributors)

**Defer to v3:**
- Comprehensive API documentation
- Advanced integration examples
- Extensive code examples library
- Contribution workflow guide
- Full HTTP API specification

### Risk Mitigation Strategy

**Technical Risk:** OneShot workflow must be robust and reproducible
- Mitigation: Heavy testing (70%+ coverage), multiple test scenarios, real-world evaluation examples

**Technical Risk:** OpenTelemetry integration complexity
- Mitigation: Use proven OT libraries, simple instrumentation patterns, clear observability examples

**Market Risk:** Developers need to trust eval results
- Mitigation: Complete transparency (filesystem storage), clear judge reasoning, reproducible runs

**Resource Risk:** Documentation and examples become overwhelming
- Mitigation: Ruthlessly defer non-essential docs to v2+, focus on essentials in v1

### Success Criteria for v1 Launch

✅ OneShot workflow is robust and reproducible
✅ Developers can setup and run first eval in ~15 minutes
✅ OpenTelemetry integration complete and working
✅ Reports clearly answer "which is better?"
✅ Architecture supports future workflows and primitives
✅ 70%+ test coverage on non-trivial code
✅ Clear error messages guide users to solutions
✅ Essential documentation in place (quickstart, CLI ref, arch guide)

---

## Functional Requirements

### 1. Evaluation Setup & Configuration

**FR-1.1:** Users can create a new evaluation configuration via CLI scaffolding
- `gavel oneshot create --eval <name> --type [local (default) | in-situ]` generates new evaluation directory
- Scaffolding generates minimal default config files (agents.json, eval_config.json, scenarios.json)
- Default config runs out-of-the-box with only LLM API key or local model configured
- User manually edits config files to customize models, judges, and scenarios (no interactive prompts)
- Traces to: Alex Chen journey (15-min setup), Priya Desai (template-based setup)

**FR-1.2:** Evaluation configuration persists as human-readable JSON/YAML
- Configuration files: agents.json, eval_config.json, scenarios.json
- All configs stored in project filesystem for version control and inspection
- Schema documentation available for manual editing
- Traces to: Dr. Lisa Wong journey (transparency), Priya Desai (reproducibility)

**FR-1.3:** Users can load provider configurations from agents.json
- agents.json contains _models section with reusable model definitions (provider, model version, temperature, max_tokens, auth)
- agents.json contains 0..n agent definitions. Each agent = model_id + prompt reference + optional parameter overrides
- Model IDs enable multiple agents to share the same model (e.g., "claude-standard" used by multiple agents with different prompts)
- Prompt references are versioned (e.g., "researcher:v1", "creative:v2") and resolved from prompt files
- Multiple agents can be compared in single eval
- Provider authentication via environment variables or config
- Traces to: Alex Chen journey (Claude vs GPT comparison)

**FR-1.4:** Users can define test scenarios via scenarios.json
- Scenario format: id, input (key/value pairs (Dict) or columns (csv)), expected_behavior (optional)
- keys/columns map to placeholders in prompt templates
- Bulk import support (CSV, JSON lines, inline)
- Traces to: Priya Desai (shared scenario templates), Alex Chen (fraud scenarios)

**FR-1.5:** Users can customize evaluation judges and metrics
- DeepEval integration with declarative GEval judge configuration
- Any predefined DeepEval judge can be used by name.
- GEval judges can be configures inline in the config or via reference to a judge config file.
- Judge definition specifies: criteria, evaluation logic, scoring method
- Pairwise scoring for model/prompt comparison
- Custom metric plugins support (future extensibility)
- Traces to: Sam Patel journey (safety metrics), Dr. Wong (custom evaluation)

**FR-1.6:** Evaluation configs support templating and environment variable substitution
- Variables like `{{ANTHROPIC_API_KEY}}`, `{{OPENAI_API_KEY}}` can be templated in config files
- Automatic `.env` file loading via `python-dotenv` on CLI startup
- Environment variable injection for secrets management (no hardcoded API keys)
- Config files use `{{VAR_NAME}}` syntax for substitution
- Config inheritance for standardized team setups
- `.env` files automatically excluded from git via `.gitignore`
- Traces to: Priya Desai (team standardization), Morgan Kim (CI/CD scripting)

---

### 2. Evaluation Execution & Orchestration

**FR-2.1:** Users can execute a complete OneShot evaluation locally
- `gavel oneshot run --eval <name>` runs all scenarios against all variants
- Deterministic execution order for reproducibility
- Parallel execution support (with safety guarantees)
- Timeout handling for long-running evaluations
- Traces to: Alex Chen journey (fraud model eval), Priya Desai (team runs)

**FR-2.2:** System supports local LLM provider testing
- Direct API calls to Claude, GPT, Gemini, and compatible models
- Provider abstraction (pydantic-ai) enables new providers without code changes
- Authentication management via environment variables
- Request/response capture with OpenTelemetry instrumentation as OTLP server/proxy
- Rate limiting and retry logic
- Traces to: Alex Chen (local model comparison), Morgan Kim (CI/CD reliability)

**FR-2.3:** System supports in-situ evaluation of deployed systems
- Black-box testing against HTTP endpoints or other deployed systems
- Request/response capture with OpenTelemetry instrumentation
- Scenario mapping to actual endpoint calls
- In-situ telemetry collection and analysis
- Traces to: Sam Patel journey (production safety eval), Morgan Kim (deployed model testing)

**FR-2.4:** Execution captures complete observability data via OpenTelemetry
- All LLM API calls instrumented with OpenTelemetry spans
- Latency, token counts, error rates captured automatically
- In-situ systems emit OT data captured by gavel-ai
- Unified telemetry storage (no separate io.jsonl; telemetry is source of truth)
- Traces to: Dr. Wong (complete transparency), Morgan Kim (performance metrics)

**FR-2.5:** Users can selectively re-run scenarios or test subsets
- `gavel oneshot run --eval <name> --scenarios 1-10` runs subset
- Tag-based filtering (run only "safety-critical" scenarios)
- Resume capability for interrupted runs
- Traces to: Alex Chen (iterative testing), Morgan Kim (fast feedback loops)

**FR-2.6:** Execution flow is reproducible and traceable
- Same config + scenarios produces deterministic execution order and judge application
- No non-deterministic behavior in gavel-ai framework logic (order, scenario routing, judge selection)
- Each run fully traced and auditable (what scenarios ran, which models, judge reasoning)
- LLM response variation is expected and captured; framework behavior is deterministic
- Traces to: Dr. Wong (scientific reproducibility), Priya Desai (historical comparison)
---

### 3. Run Management & Artifacts

**FR-3.1:** System creates isolated RunContext for each evaluation execution
- Each run gets timestamped directory: `runs/run-20251227-143022/` (in v1; future runs may persist in other stores)
- Complete artifact isolation between runs
- Run metadata and manifest tracking
- Traces to: Product Brief (Run/RunContext critical abstraction)

**FR-3.2:** RunContext manages complete evaluation artifacts
- Standard artifacts: telemetry.jsonl (OT spans), results.jsonl (judged results), manifest.json
- Workflow-specific artifacts may also exist (e.g., raw conversations for Conversational evals)
- Workflow-specific artifacts use JSON format in v1; JSONL or other formats possible in future
- All artifacts organized hierarchically within run directory
- Manifest contains: timestamp, config hash, scenario count, judge versions, metadata
- A copy of all eval configs is also saved for each run under /run/config for reproducibility
- Traces to: Dr. Wong (artifact preservation), Priya Desai (historical tracking)

**FR-3.3:** Users can re-judge existing runs without re-execution
- `gavel oneshot judge --run <run-id>` applies new judges to existing telemetry
- Quick iteration on evaluation logic without re-running expensive API calls
- Maintains audit trail (original judges preserved)
- Traces to: Alex Chen (iteration), Morgan Kim (fast feedback)

**FR-3.4:** System tracks and displays run history
- `gavel oneshot list` shows all completed runs with timestamps and statuses
- Basic run comparison (model A vs B across multiple runs)
- Run artifacts retained for at least N days (configurable)
- Traces to: Priya Desai (historical analysis), Morgan Kim (trend tracking)

**FR-3.5:** Users can archive and export complete runs for reproduction
- Export complete run including config, scenarios, telemetry, results
- Archive format suitable for long-term storage (zip, tar.gz)
- Re-import archived runs for analysis or reproduction
- Traces to: Dr. Wong (paper reproducibility), research teams

**FR-3.6:** RunContext provides API for programmatic run inspection
- Load run artifacts programmatically (future SDK)
- Access raw telemetry, results, metadata
- Enable custom analysis scripts and notebooks
- Traces to: Dr. Wong (custom analysis), Morgan Kim (automation)

**FR-3.7:** Users can mark runs as "milestone" runs with comments
- `gavel oneshot milestone --run <run-id> --comment "Baseline for v1.0"` marks run as milestone
- Milestone runs are preserved indefinitely (not subject to cleanup)
- Milestone status stored in manifest.json with timestamp and comment
- `gavel oneshot list --milestones` displays only milestone runs with comments
- Useful for preserving baseline evaluations, production deployments, release candidates
- Traces to: Priya Desai (historical tracking), Morgan Kim (CI/CD baselines)

---

### 4. Judging & Evaluation

**FR-4.1:** System integrates DeepEval for LLM-as-judge evaluation
- DeepEval judges available out-of-the-box
- Configurable scoring criteria and evaluation logic
- Multiple judge types: similarity, hallucination, faithfulness, custom
- Traces to: Product Brief (DeepEval integration)

**FR-4.2:** System supports declarative GEval judge configuration
- Define judges without code: criteria, evaluation steps, scoring method
- YAML/JSON config format
- GEval can be defined inline in the eval_config or via standalone judge config files (for longer criteria)
- Testable judge logic (can be validated before execution)
- Traces to: Alex Chen (custom evaluation logic)

**FR-4.3:** Pairwise variant comparison scoring
- Compare outputs from multiple variants on same scenarios (variant = different model, prompt, in-situ endpoint config, or remote API flags)
- Judge determines which variant is better, by how much
- Aggregate scoring across all scenarios
- Traces to: Alex Chen (Claude vs GPT), Sam Patel (variant selection)

**FR-4.4:** Judges produce detailed reasoning with scores
- Each judgment includes: score, reasoning, supporting evidence
- Reasoning is transparent and human-readable
- Multi-level scoring (e.g., 1-10 scale with explanations at each level)
- Traces to: Sam Patel (decision confidence), Dr. Wong (audit trail)

**FR-4.5:** Judge execution is configurable and extensible
- Judge retry logic for transient failures
- Configurable judge models (use faster model for quick evals, slower for thorough)
- Judge output caching (same scenario/judge pair = cached result)
- Traces to: Morgan Kim (cost control), extensibility principle

**FR-4.6:** Custom judge plugins can be implemented and registered
- Clear interface for judge plugins
- Judge plugins receive scenario, outputs, and metadata
- Plugin registration and discovery mechanism
- Traces to: Jordan Rivera journey (extensibility), community contributions

---

### 5. Reporting & Result Presentation

**FR-5.1:** Reports use Jinja2 templating system
- All reports generated via Jinja2 templates (HTML, Markdown, custom formats)
- User can provide custom template or use built-in defaults
- Template variables: {{title}}, {{overview}}, {{summary}}, {{detail}}, {{metadata}}, {{telemetry}}
- Enables flexible customization for different stakeholders (executives, engineers, researchers)
- Traces to: Morgan Kim (CI/CD dashboards), Dr. Wong (custom analysis output)

**FR-5.2:** OneShot/SXS reports follow structured format
- **Title:** Name of experiment/eval
- **Overview:** Experiment details (local vs in-situ, input sources, variants tested)
- **Summary:** One table per prompt/system-under-test; rows=variants, columns=judge scores + total score
- **Detail:** One section per X-under-test; cards for each input (user input expandable) with variant outputs table below (columns=variants, judge scores, comments expandable)
- Report filename: `report.html` in run directory
- Traces to: Sam Patel journey (stakeholder review), Alex Chen (confidence building)

**FR-5.3:** Conversational reports follow structured format
- **Title:** Name of experiment/eval
- **Overview:** Experiment details (local vs in-situ, input sources, variants tested)
- **Summary:** One table per prompt/system-under-test; rows=variants, columns=judge scores + total score
- **Detail:** One section per X-under-test; cards for each scenario with full conversation (expandable) and variant outputs table below (columns=variants, judge scores, comments expandable)
- Report filename: `report.html` in run directory
- Traces to: Future v2 (Conversational workflow)

**FR-5.4:** Autotune reports provide progression visualization
- Series of numbered one-shot/SXS reports (one per optimization pass)
- Aggregate visualization showing judge scores over entire tuning run
- Enables tracking prompt/variant evolution and improvement trajectory
- Report filenames: `report-pass-1.html`, `report-pass-2.html`, ..., `report-aggregate.html`
- Traces to: Future v3 (Autotune workflow)

**FR-5.5:** Reports include complete judge reasoning and evidence
- For each input/variant pair: input (expandable), variant outputs, judge scores, judge reasoning (expandable)
- All detail cards support expand/collapse for readability without overwhelming display
- Links to raw telemetry and run artifacts for deep inspection
- Traces to: Dr. Wong (audit trail), transparency principle

**FR-5.6:** Reports answer "which is better?" clearly
- Prominent winner indicator per prompt/system-under-test with total scores
- Trade-off analysis highlighting variant strengths/weaknesses
- Judge comment summaries explaining key differences
- Actionable interpretation based on evaluation criteria
- Traces to: Sam Patel (decision making), Alex Chen (confidence)

---

### 6. Extensibility & Architecture

**FR-6.1:** Architecture uses clean abstractions for future workflow addition
- RunContext abstraction manages all artifact storage and retrieval
- Workflow interface enables new evaluation types (Conversational, Autotune)
- Processor interface for custom evaluation logic
- Storage abstraction enables future adapters (databases, cloud storage)
- Traces to: Product Brief (architectural principle)

**FR-6.2:** Clear extension patterns for new evaluation workflows
- Documentation on implementing new workflow (e.g., Conversational, Autotune)
- Example workflow implementation included
- Workflow registration mechanism
- Traces to: Jordan Rivera journey (contribution), future phases (v2, v3)

**FR-6.3:** Clear extension patterns for evaluation primitives
- Processor interface for custom scenario transformation
- Judge interface for custom evaluation logic
- Example implementations and test helpers
- Traces to: Jordan Rivera journey (multimodal evaluator)

**FR-6.4:** Architecture supports pluggable storage backends
- Current implementation: filesystem-based (default for v1)
- Storage interface abstraction for future adapters
- Future adapters: SQL database, cloud storage, prompt servers
- Traces to: Product Brief (extensible architecture), post-v3 vision

**FR-6.5:** Architecture separates presentation tier from business logic
- CLI is one interface implementation
- HTTP API can be added as second interface without core changes
- Future GUI can reuse same business logic
- Traces to: Product Brief (future interfaces), post-v3 vision

**FR-6.6:** Code is modular and dependency-managed
- Core evaluation logic isolated from provider integrations
- Optional dependencies for advanced features
- Clear public API surface for library use (future SDK)
- Traces to: extensibility principle, future SDK (v2+)

---

### 7. CLI Interface & Commands

**FR-7.1:** CLI provides command pattern: `gavel [workflow] [action] [options]`
- Workflow: oneshot (v1), conversational (v2), autotune (v3)
- Actions: create, run, judge, report
- Options: --eval, --scenarios, --output, --config, etc
- Traces to: Product Brief (CLI design)

**FR-7.2:** `gavel oneshot create` scaffolds new evaluations
- CLI flags to specify evaluation type, optional config file references
- Generates default config files (agents.json, eval_config.json, scenarios.json) with sensible defaults
- User manually edits generated configs to customize models, prompts, judges, and scenarios
- No interactive prompts; all configuration via generated files or CLI flags
- Traces to: Alex Chen journey (15-min setup)

**FR-7.3:** `gavel oneshot run` executes complete evaluation
- Runs all scenarios against all agents with all judges
- Progress indicators during execution
- Return code indicates success/failure
- Output: structured JSON (for scripting), human-readable summary (interactive)
- Traces to: Morgan Kim (CI/CD integration), Alex Chen (execution)

**FR-7.4:** `gavel oneshot judge` applies judges to existing run
- Re-judges existing telemetry with new or modified judges
- Faster than re-running (no API calls)
- Can selectively update specific judges
- Traces to: Alex Chen (iteration), Morgan Kim (fast feedback)

**FR-7.5:** `gavel oneshot report` generates reports from run
- Generates HTML and Markdown reports
- Can re-generate with custom templates
- Supports output filtering and formatting options
- Traces to: Sam Patel (reporting), Priya Desai (documentation)

**FR-7.6:** `gavel oneshot list` displays run history
- Lists all completed runs with timestamps, statuses, summaries
- Can filter by eval name, date range, status
- Shows run directories for artifact inspection
- Traces to: Priya Desai (historical tracking), Morgan Kim (automation)

**FR-7.7:** CLI supports structured output formats for automation
- JSON output for machine parsing (--output json)
- Markdown/HTML for human consumption
- Exit codes: 0 (success), 1 (error), 2 (evaluation failed quality gate)
- Traces to: Morgan Kim (CI/CD scripting), automation principle

**FR-7.8:** CLI provides help and examples
- `gavel --help` and `gavel oneshot --help` show options
- `gavel oneshot --examples` shows common usage patterns
- Error messages include guidance and example commands
- Traces to: Alex Chen (15-min onboarding), error handling principle

---

### 8. File System & Transparency

**FR-8.1:** All evaluation artifacts stored as human-readable files
- agents.json: provider configuration
- eval_config.json: evaluation definition
- scenarios.json: test cases
- Run artifacts in timestamped directory: telemetry.jsonl, results.jsonl, manifest.json
- Traces to: Product Brief (transparent by default)

**FR-8.2:** Configuration files use standard JSON/YAML format
- No custom binary formats
- Configs are versionable and diffable
- Easy manual inspection and editing
- Traces to: Dr. Wong (transparency), Priya Desai (git integration)

**FR-8.3:** Telemetry data stored in OpenTelemetry-compatible format
- telemetry.jsonl: one OT span per line (JSON Lines)
- Includes: timestamps, trace IDs, span names, attributes, duration
- Standard OT attributes for LLM calls (model, provider, tokens, etc)
- Traces to: Product Brief (OT native)

**FR-8.4:** Results stored in evaluable format
- results.jsonl: one result per line (JSON Lines)
- Each result: scenario, model output, judge reasoning, score
- Structured format for programmatic analysis
- Traces to: Dr. Wong (auditability)

**FR-8.5:** Run manifest provides complete run metadata
- manifest.json: run timestamp, config hash, scenario count, judge versions
- Reproducibility information for future re-runs
- Links to all artifacts within run directory
- Traces to: Priya Desai (reproducibility), Dr. Wong (documentation)

**FR-8.6:** Directory structure is logical and discoverable
- Evaluations stored in: `.gavel/evaluations/<eval-name>/`
- Runs stored in: `.gavel/evaluations/<eval-name>/runs/run-<timestamp>/`
- Reports stored alongside run artifacts
- Easy to understand and navigate
- Traces to: transparency principle, usability

**FR-8.7:** Cleanup and archival support
- `gavel clean` removes old runs (default: >30 days old)
- Manual deletion of specific runs
- Archive runs before cleanup for long-term storage
- Traces to: Priya Desai (storage management)

---

### 9. Error Handling & Observability

**FR-9.1:** All errors are informative and actionable
- Error messages explain what failed and why
- Suggest recovery steps or example commands
- Include relevant context (file names, line numbers, config values)
- Traces to: success criteria (clear error messages)

**FR-9.2:** Error categories are well-defined
- Configuration errors: invalid config, missing required fields
- Execution errors: API failures, timeout, provider unavailable
- Validation errors: invalid scenario, judge failure
- System errors: file I/O, permissions, disk space
- Traces to: error handling principle

**FR-9.3:** Debug mode provides complete visibility
- `gavel oneshot run --debug` enables verbose logging
- Full stack traces for exceptions
- API request/response logging (with secrets masked)
- Telemetry preview during execution
- Traces to: Morgan Kim (troubleshooting), Dr. Wong (debugging)

**FR-9.4:** Logging uses consistent format and levels
- Log format: "%(asctime)s [%(levelname)s] <%(filename)s:%(lineno)s> %(message)s"
- Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Logs stored in run directory for analysis
- Traces to: observability principle

**FR-9.5:** System captures detailed execution telemetry and metrics
- Via run_metadata.json stored in run directory
- **Timing metrics:** Run start/end time, total duration, mean/median/min/max/std for processing time per input
- **Input metrics:** Total inputs processed (inputs × variants × XUT count)
- **LLM call tracking:** List of all distinct LLM calls (prompt+variant combination) with individual timing stats
- **Execution stats:** Completed inputs, failed inputs, retry counts
- Traces to: Morgan Kim (performance monitoring), Dr. Wong (profiling analysis)

**FR-9.6:** Validation before execution catches common issues
- Config validation: required fields, type checking, schema validation
- Scenario validation: format, required fields
- Judge validation: configuration syntax
- Early failure with clear error messages
- Traces to: error handling principle, user experience

**FR-9.7:** Health checks and diagnostics available
- `gavel health` checks API keys, connectivity, disk space
- `gavel diagnose` collects system info for troubleshooting
- Clear output indicating what's working/broken
- Traces to: support and troubleshooting

**FR-9.8:** Telemetry data is available in reports and accessible programmatically
- run_metadata.json contains all performance metrics (timing, input counts, LLM calls, execution stats)
- Telemetry variables automatically injected into report templates: {{telemetry}}, {{metadata}}
- Programmatic access to telemetry via RunContext API for custom analysis
- Enables performance profiling, cost analysis, bottleneck identification
- Traces to: Morgan Kim (performance dashboards), Dr. Wong (detailed analysis)

---

## Non-Functional Requirements

### Performance

**NFR-P1: Realistic evaluation execution timelines**
- LLM API calls: 2-5 seconds per call (realistic for provider latency)
- Typical evaluation timeline: minutes to longer depending on scenario count and variant count
  - Example: 10 scenarios × 2 variants × 2 judges = 40+ API calls = 2-4+ minutes
  - Example: 100 scenarios × 3 variants × 3 judges = 900+ API calls = 45+ minutes
- Report generation: <5 seconds for typical eval
- CLI commands (list, health, diagnose): <2 seconds response time
- Re-judging existing runs (no API calls): <1 second per 100 results

**NFR-P2: Maximize parallelization and native batching**
- Scenario execution supports concurrent processing (all variants against all scenarios in parallel where possible)
- Judge execution parallelizes across all scenarios/variants to minimize total wall-clock time
- Support for native LLM batching APIs (e.g., OpenAI Batch API) when available to reduce per-call latency
- Support for LLM prompt caching to reduce redundant processing and API costs across similar scenarios
- Batching and caching are transparent to user (automatically applied where applicable)
- Configuration options for controlling parallelism level (balance speed vs resource usage)

**NFR-P3: Efficient resource utilization**
- Memory footprint: <500MB for typical evaluation run
- Telemetry collection adds <5% overhead to evaluation time

### Reliability

**NFR-R1: Reproducible evaluation execution**
- Same config + scenarios + random seed = identical deterministic execution flow (not output, but execution path)
- Failed evaluations provide clear error messages and recovery paths
- Partial run recovery: ability to resume interrupted runs without re-executing completed scenarios

**NFR-R2: Robust error handling**
- All transient API failures (rate limits, timeouts) are retried with exponential backoff
- Provider unavailability detected and reported within 30 seconds
- Configuration or scenario errors caught and reported before execution begins
- OpenTelemetry instrumentation failures do not block evaluation execution

**NFR-R3: Data integrity**
- All run artifacts (telemetry, results, manifest) are written durably to filesystem
- Config hash stored in manifest enables validation of reproducibility
- No partial or corrupted artifacts in run directory even if process crashes

### Integration

**NFR-I1: Multi-provider compatibility**
- Support for Claude, GPT, Gemini, Ollama, and compatible LLM APIs (via pydantic-ai abstraction)
- New providers can be added without code modification via provider abstraction
- Timeout and rate-limit handling works across all supported providers
- Consistent authentication pattern (environment variables) across all providers

**NFR-I2: In-situ system integration**
- Out-of-the-box adapters for common in-situ interfaces: Agent Communication Protocol (ACP) and OpenAI HTTP chat interface
- HTTP endpoint invocation with configurable request/response mapping
- OpenTelemetry span capture from in-situ systems works reliably
- Variant flags (different API parameters) passed cleanly to in-situ endpoints
- In-situ failures isolated from eval runner (one failed endpoint doesn't block other variants)
- New adapters can be added without code modification via adapter abstraction pattern

**NFR-I3: Storage and reporting integration**
- File artifacts (JSON/JSONL) integrate cleanly with version control (git) systems
- Report templates (Jinja2) integrate with custom CI/CD dashboards
- Future storage adapters (S3, databases) enabled via storage abstraction interface

### Security

**NFR-S1: Credential protection**
- API keys not logged, displayed, or stored in plaintext in telemetry
- Secrets masked in debug output (show "***" for API key values)
- Environment variable injection for credentials (no hardcoding in configs)
- Automatic `.env` file loading via `python-dotenv>=1.0.0` dependency
- `.env.example` template provided for easy setup
- `.env` files excluded from git via `.gitignore` to prevent accidental commits
- Config files use `{{VAR_NAME}}` substitution pattern for secure credential injection
- Run artifact permissions prevent world-readable access to stored credentials (if present)

**NFR-S2: Data confidentiality**
- All run data stored locally by default (no automatic cloud transmission)
- User controls what data leaves their machine (explicit export/archive if desired)
- In-situ system response data captured only as configured (no implicit logging beyond telemetry)

### Maintainability

**NFR-M1: Code clarity and extensibility**
- Core evaluation logic separated from provider integrations via abstractions
- Processor, Workflow, Judge, and Storage interfaces enable extension without modifying core
- Clear extension patterns with example implementations for new workflows and primitives
- Public API surface documented for future SDK development

**NFR-M2: Documentation for contributors**
- Architecture guide explains core abstractions and extension patterns
- Example implementations provided for custom workflows and judges
- Clear test helpers and fixtures available for testing extensions
- Codebase follows consistent naming, structure, and style conventions

### Testability

**NFR-T1: Test coverage**
- 70%+ unit test coverage on non-trivial code paths (FRs, core evaluation logic, artifact management)
- Unit tests for all provider integrations
- Mock providers and test fixtures available for offline testing
- Integration tests for OneShot workflow with multiple providers

**NFR-T2: Debuggability**
- Debug mode (`--debug`) provides detailed execution traces
- OpenTelemetry data available for post-execution analysis
- Clear separation between framework behavior and LLM response variation
- Test utilities for validating custom processors, judges, and workflows
