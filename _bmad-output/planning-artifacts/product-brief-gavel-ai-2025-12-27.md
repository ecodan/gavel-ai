---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - docs/.private/app-overview.md
  - docs/.private/arch-overview.md
date: 2025-12-27
author: Dan
---

# Product Brief: gavel-ai

## Executive Summary

**gavel-ai** is an open-source, provider-agnostic AI evaluation framework designed to eliminate the barrier to entry for evaluating LLM-based systems. Unlike closed, complex frameworks, gavel-ai gets developers from zero to their first rigorous evaluation in 15 minutes—with a clean CLI, intelligent scaffolding, and powerful evaluation workflows built on proven design patterns.

Inspired by successful evaluation system design but rebuilt from the ground up for the open-source community, gavel-ai removes the friction that prevents most AI projects from evaluating their systems at all.

---

## Core Vision

### Problem Statement

Most AI projects never evaluate their systems rigorously—not because they don't want to, but because existing evaluation frameworks are closed, complex, and require deep setup knowledge. The barrier to entry is the barrier to learning what actually works.

Current solutions either:
- Are locked to proprietary AI gateways
- Require extensive configuration and scaffolding
- Limit evaluation to a narrow set of workflows
- Lack clear onboarding for first-time users

**The real problem isn't advanced features—it's getting started.**

### Problem Impact

Without evaluation, AI projects operate blindly:
- No empirical data on which model performs best
- No systematic way to iterate on prompts or configurations
- No confidence in production behavior before deployment
- Teams waste time guessing instead of measuring

This affects any software developer building *on top of* AI—from indie developers to enterprise teams.

### Why Existing Solutions Fall Short

Existing evaluation frameworks treat evaluation as an advanced capability for specialists. They:
- Prioritize feature breadth over first-time user experience
- Lock developers into single AI provider ecosystems
- Require understanding of complex abstractions before writing first eval
- Lack intelligent scaffolding for the "zero to first eval" journey

**They solve for power users, not practitioners.**

### Proposed Solution

**gavel-ai** is built on four core principles:

1. **Open & Provider-Agnostic**: Work with Claude, GPT, Gemini, local models, or any LLM—not locked to a single gateway
2. **Scaffolded for Beginners**: CLI-driven workflows and smart defaults get developers to their first eval in 15 minutes
3. **Transparent & Debuggable**: All configurations, scenarios, results, and artifacts are stored as simple, structured files on the filesystem—no black boxes, everything is available for analysis, debugging, and integration with existing workflows
4. **Rigorous & Extensible**: Three powerful evaluation workflows (OneShot, Conversational, Autotune) designed for different testing scenarios, with a clean architecture for community contributions

The framework is inspired by proven evaluation design patterns but built from the ground up with modern Python practices, clean architecture, and a developer-first experience.

### Key Differentiators

- **Open Source First**: Built for the community, not locked to proprietary systems
- **Any Provider**: True provider-agnostic design—not an afterthought
- **Transparent by Default**: File-system-based architecture means all configs, scenarios, results, and metadata are human-readable and available for analysis, debugging, and integration with existing tools (git, version control, custom analysis scripts)
- **15-Minute Onboarding**: From install to first eval with intelligent CLI scaffolding and sensible defaults
- **Proven Design**: Built by the designer of the original evaluation framework, implementing lessons learned
- **Three Core Workflows**: OneShot (model comparison), Conversational (multi-turn testing), Autotune (prompt optimization)
- **Clean Architecture**: Modern, extensible codebase that invites community contribution

---

## Target Users

### Primary User: The Developer Building on AI

**Profile:**
A software developer (solo or small team) building a project that incorporates AI capabilities. They want confidence in their prompts and models but lack the infrastructure for rigorous evaluation.

**Core Workflow:**
1. Set up first evaluation in gavel-ai (config-driven, not code-heavy)
2. Run eval against their prompts/model configs
3. Review results and iterate
4. Re-run eval with new variants
5. Check eval configs into git for reproducibility and team access

**Key Need:**
Evaluation must be low-friction. Configuration changes → re-run eval → see results. No manual busywork. The goal is iterating toward better quality without spending weeks on tooling.

**Success Metric:**
"I went from eyeballing results to having data-driven confidence in my prompts, and I can run this eval again whenever I want."

---

### Secondary User: Product Managers & Stakeholders

**Profile:**
Product managers, team leads, or other stakeholders who need to review and approve AI feature quality before deployment.

**Core Interaction:**
They don't set up or run evals themselves—the developer shares results (from git or reports). They review comparative data, understand trade-offs (model A vs. B, prompt v1 vs. v2), and make informed decisions about what to ship.

**Key Need:**
Clear, actionable results that answer questions like "Is this version better?" and "Are we ready to deploy?"

---

## Success Metrics

### User Success: The Developer's Confidence Test

Success for gavel-ai is straightforward—the developer using it can:

1. **Set up and run evals reliably** — No surprises, no cryptic errors. Evals work as expected, or failures are clear and actionable.

2. **Trust the results** — Full transparency into the process. They can inspect inputs, outputs, judge reasoning, and metrics. Results are reproducible (same config + scenarios = same results every time).

3. **Get clear reports** — Reports answer their core question: "Which is better?" with context and reasoning, not just scores. Trade-offs are explicit.

4. **Iterate fast** — Config change → run eval → review results. The cycle is frictionless, removing friction from the iteration loop.

### Operational Success Indicators

gavel-ai is succeeding when:

- **Robust Execution**: Evals run reliably with clear error messages when something fails
- **Reproducible Results**: Same configuration and scenarios produce identical results across runs
- **Full Transparency**: All inputs, outputs, judge reasoning, and metrics are human-readable and available on the filesystem
- **Clear Reporting**: Reports articulate findings clearly, with sufficient context for informed decision-making

### Secondary Success: Community & Adoption

- **Organic Adoption**: Developers discover and use gavel-ai because it solves their evaluation problem
- **Community Contributions**: Extensions and improvements from the community (new processors, judge strategies, report formats)
- **Real-World Usage**: Shipping projects with gavel-ai evals as part of their AI development workflow

### The Bottom Line

**Success = robust, transparent one-shot and conversational evals with clear reporting that developers can trust.**

---

## MVP Scope

### Core Features for v1

**OneShot Evaluation Workflow**
- Local testing: Direct LLM calls (Claude, GPT, Gemini, local models via pydantic-ai or similar)
- In-Situ testing: Black-box testing of deployed systems
- Deterministic scenario ordering for reproducibility
- Scenario-based testing with flexible input configuration

**Run Management (Critical Abstraction)**
- RunContext abstraction for managing evaluation runs
- Timestamped run directories with complete artifact isolation
- Run metadata and manifest tracking
- Re-judging existing runs without re-execution
- Historical analysis and run comparison capabilities

**Unified Telemetry & Observability**
- OpenTelemetry instrumentation for local prompt testing
- OpenTelemetry collection from in-situ test targets
- Unified telemetry storage (no separate io.jsonl; telemetry is the source of truth)
- Complete visibility into execution traces, latency, and system behavior

**Transparent File-Based Artifacts**
- eval_config.json (evaluation definition)
- agents.json (provider and model configuration)
- scenarios.json (test cases)
- Run artifacts per RunContext: telemetry.jsonl (OpenTelemetry spans), results.jsonl (judged results), manifest.json (run metadata)
- HTML and Markdown reports generated per run

**Judging & Evaluation**
- DeepEval integration for LLM-as-judge evaluation
- Declaratively configured GEval judges
- Pairwise and multi-model scoring strategies
- Re-judging capability (apply new judges to existing run data)

**CLI Interface**
- Command pattern: `gavel [oneshot] [create|run|judge|report] --eval <name> [options]`
- Clean, composable action-based structure
- Intelligent scaffolding for first-time setup
- Run selection and history tracking

**Extensible Architecture**
- Storage abstraction layer with RunContext at the core (filesystem-based in v1, future adapters for databases, prompt servers, etc.)
- Provider abstraction (pydantic-ai or similar) for model provider flexibility
- OpenTelemetry abstraction for telemetry collection (local and in-situ)
- Presentation tier separated from business logic (CLI is one interface; future: GUI, API, CI integrations)

### Out of Scope for MVP

- Conversational workflow (v2)
- Autotune workflow (v3)
- Custom storage adapters beyond filesystem
- GUI or REST API interfaces
- Advanced reporting customization

### MVP Success Criteria

- OneShot evals are robust and reproducible with complete run isolation
- RunContext provides reliable artifact management and run traceability
- OpenTelemetry integration provides unified visibility across local and in-situ testing
- File-based architecture is transparent and extensible (abstractions in place)
- Developers can configure, run, and re-judge evals with minimal friction (15-minute target)
- Clear, actionable reports that help developers make decisions

### Future Vision (v2-v3)

**v2: Conversational Workflows**
- Multi-turn dialogue evaluation
- Agent behavior assessment
- Context window management

**v3: Autotune**
- Iterative prompt optimization
- Prompt versioning and evolution tracking
- Automated improvement suggestions

**Beyond v3:**
- GUI and API interfaces leveraging core abstractions
- CI/CD integration support
- Storage adapter ecosystem (databases, prompt servers, etc.)
- Advanced reporting and visualization
- Community-contributed judge strategies and processors
