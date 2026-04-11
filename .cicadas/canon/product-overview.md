# Product Overview

> Canon document. Updated by the Synthesis agent at the close of each initiative.

## What This Is

Gavel-AI is an open-source, provider-agnostic AI evaluation framework designed for testing LLM applications locally and in production. It enables developers to run structured evaluations across multiple AI providers (Claude, GPT, Gemini, Ollama) using consistent workflows and "LLM-as-a-judge" scoring.

## Why It Exists

Measuring the quality of LLM outputs is notoriously difficult due to non-deterministic behavior and the lack of traditional assertions. Gavel-AI provides a structured, git-friendly, and local-first alternative to proprietary evaluation platforms, allowing teams to build authoritative benchmarks and catch regressions before deployment.

---

## Users & Journeys

### AI Evaluation Engineer — The Architect

**Who they are:** A developer or data scientist responsible for the overall quality and safety of an LLM application. They care about scalability, reproducibility, and robust statistical evidence.

**Their journey:** They integrate Gavel-AI into their CI/CD pipeline or local dev workflow. They define large sets of scenarios, configure multiple judges, and analyze performance across model variants to make data-driven decisions about model upgrades.

**Key needs:**
- Parallel execution of large scenario batches.
- Reproducible runs with immutable artifacts.
- Integration with standard observability tools (OpenTelemetry).

---

### Prompt/Product Engineer — The Optimizer

**Who they are:** A developer focused on iterating on the specific behavior and tone of an AI agent. They care about speed of iteration and qualitative feedback.

**Their journey:** They use Gavel's CLI to scaffold new evaluations and quickly test system prompt variations. Success for them is seeing a "clear winner" indicated in a Jinja2-generated report after a 5-minute local run.

**Key needs:**
- Simple CLI for scaffolding and execution.
- Human-readable artifacts (JSON/YAML/Markdown).
- Clear, visual reporting of judge reasoning.

---

## Core Features (Current)

| Feature | Description | Status |
|---------|-------------|--------|
| OneShot Workflow | Batch processing of single-turn prompts against scenarios. | Shipped |
| Conversational v2 | Multi-turn interaction evaluation support. | Shipped |
| Provider Agnostic | Support for Claude, GPT, Gemini, and Ollama via Pydantic-AI. | Shipped |
| DeepEval Judges | Built-in integration for similarity, faithfulness, and custom GEval scores. | Shipped |
| Local-First Storage | Filesystem-based artifact storage for human-readable run history. | Shipped |
| OpenTelemetry | Native instrumentation for distributed tracing and performance metrics. | Shipped |
| Autotune v3 | Automated optimization of prompts and model parameters. | Beta |

## Out of Scope (Intentional)

- **Proprietary SaaS Platform** — Gavel is intentionally local-first and open-source to ensure data privacy and tool portability.
- **Production Monitoring (Live)** — While Gavel uses OTel, its primary focus is pre-deployment evaluation and benchmarking, not real-time production traffic monitoring.
- **Model Training/Fine-tuning** — Gavel evaluates model behavior but does not handle the training process itself.

---

## Success Criteria

- **Zero-regress detection**: Successfully identifying performance drops in model upgrades.
- **Evaluation Speed**: Running local benchmarks in < 5 minutes for typical scenario sets.
- **Artifact Portability**: Run results remaining human-readable and versionable in Git.

---

## Open Questions

- **Cloud Storage** — When will S3/Database storage adapters be required for team collaboration? — Post-v1
- **Real-world Parity** — How much does local evaluation performance correlate with production user experience? — ongoing research

