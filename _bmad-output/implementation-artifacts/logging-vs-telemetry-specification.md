# Logging vs Telemetry Specification

**Project:** gavel-ai
**Date:** 2025-12-31
**Author:** Dev Agent (Amelia) + Dan
**Purpose:** Clarify distinction between application logging and OpenTelemetry spans

---

## Problem Statement

Current implementation conflates two separate concerns:
1. **Application Logging** - Routine operational events for debugging and monitoring
2. **OpenTelemetry Spans** - Performance tracing and distributed observability

**Example of Current Confusion:**
```python
# Currently emitting OT span for routine config loading:
with tracer.start_as_current_span("config.load_config"):
    config = json.load(f)  # This doesn't need OT span!
```

This clutters telemetry.jsonl with routine operations instead of focusing on valuable performance data.

---

## Principles

### Application Logging (via Python logging module)
**Purpose:** Record operational events, errors, and debugging information
**Audience:** Developers, operators, users debugging issues
**Output:**
- **Application-level:** `.gavel/gavel.log` (rolling file) - Top-level lifecycle events
- **Run-level:** `.gavel/evaluations/{eval}/runs/{run_id}/run.log` - Run-specific operations
- **Console:** stdout (CLI user feedback)
**Format:** Structured text with timestamp, level, location, message

### OpenTelemetry Spans (via OpenTelemetry SDK)
**Purpose:** Trace execution flow, measure performance, track distributed operations
**Audience:** Performance analysis, observability platforms, telemetry visualization
**Output:** .gavel/runs/{run_id}/telemetry.jsonl (JSONL format)
**Format:** Structured JSON with trace_id, span_id, duration, attributes

---

## What to Log (Application Logging)

### ✅ USE LOGGING FOR:

1. **Configuration Events**
   ```python
   logger.info("Loaded eval_config.json")
   logger.info("Loaded 15 scenarios from scenarios.json")
   logger.debug("Using model provider: anthropic")
   ```

2. **Validation & Errors**
   ```python
   logger.error("Missing required field 'agents' in agents.json", exc_info=True)
   logger.warning("No judges configured - skipping judging")
   ```

3. **Lifecycle Events**
   ```python
   logger.info("Starting evaluation 'test_os'")
   logger.info("Executing 15 scenarios...")
   logger.info("✓ Completed evaluation in 45.2s")
   ```

4. **User-Facing Status**
   ```python
   logger.info("Running judge 'similarity' for scenario 'test-1'")
   logger.info("Judge scored 8/10")
   ```

### Format: Per project-context.md
```python
LOG_FORMAT = "%(asctime)s [%(levelname)s] <%(filename)s:%(lineno)s> %(message)s"
# Example output:
# 2025-12-31 11:45:30 [INFO] <oneshot.py:92> Running evaluation 'test_os'
```

---

## What to Trace (OpenTelemetry Spans)

### ✅ USE OT SPANS FOR:

1. **LLM API Calls** (expensive, measurable)
   ```python
   with tracer.start_as_current_span("llm.call") as span:
       span.set_attribute("llm.provider", "anthropic")
       span.set_attribute("llm.model", "claude-3-5-sonnet")
       span.set_attribute("llm.tokens.prompt", 150)
       span.set_attribute("llm.tokens.completion", 100)
       span.set_attribute("llm.latency_ms", 2333)
       response = await agent.run(prompt)
   ```

2. **Judge Evaluations** (expensive, measurable)
   ```python
   with tracer.start_as_current_span("judge.evaluate") as span:
       span.set_attribute("judge.id", "similarity")
       span.set_attribute("judge.score", 8)
       span.set_attribute("scenario.id", "test-1")
       result = await judge.evaluate(...)
   ```

3. **Scenario Processing** (workflow tracing)
   ```python
   with tracer.start_as_current_span("processor.execute") as span:
       span.set_attribute("processor.type", "prompt_input")
       span.set_attribute("scenario.id", scenario_id)
       span.set_attribute("input.length", len(input.text))
       result = await processor.process(inputs)
   ```

4. **Batch Operations** (high-level workflow coordination)
   ```python
   with tracer.start_as_current_span("executor.execute_batch") as span:
       span.set_attribute("executor.parallelism", parallelism)
       span.set_attribute("batch.size", len(inputs))
       results = await executor.execute(inputs)
   ```

### ❌ DON'T USE OT SPANS FOR:

1. **Report Generation** - Use logging instead
   ```python
   # ❌ WRONG
   with tracer.start_as_current_span("reporter.generate"):
       await reporter.generate(run, output_path)

   # ✅ CORRECT
   logger.info(f"Generating {format} report to {output_path}")
   await reporter.generate(run, output_path)
   logger.info(f"✓ Generated report: {output_path}")
   ```

2. **Storage/File I/O** - Use logging instead
   ```python
   # ❌ WRONG
   with tracer.start_as_current_span("storage.save"):
       await run.save()

   # ✅ CORRECT
   logger.info(f"Saving run {run_id}")
   await run.save()
   logger.debug(f"Saved {len(artifacts)} artifacts")
   ```

3. **Routine Config Loading** - Use logging instead
   ```python
   # ❌ WRONG
   with tracer.start_as_current_span("config.load_config"):
       config = json.load(f)

   # ✅ CORRECT
   logger.info("Loaded eval_config.json")
   config = json.load(f)
   ```

4. **Simple Validations** - Use logging instead
   ```python
   # ❌ WRONG
   with tracer.start_as_current_span("validate.check_required_fields"):
       if "agents" not in config:
           raise ConfigError(...)

   # ✅ CORRECT
   if "agents" not in config:
       logger.error("Missing required field 'agents'")
       raise ConfigError(...)
   ```

5. **Synchronous Data Transformations** - Too granular
   ```python
   # ❌ WRONG
   with tracer.start_as_current_span("transform.scenario_to_input"):
       return Input(id=scenario.id, text=scenario.input)

   # ✅ CORRECT
   return Input(id=scenario.id, text=scenario.input)  # No span needed
   ```

---

## Decision Matrix

| Operation | Duration | Network/IO | User Visibility | Use Logging | Use OT Span |
|-----------|----------|------------|----------------|-------------|-------------|
| Load config file | <1ms | File I/O | Yes | ✅ | ❌ |
| Parse JSON | <1ms | No | No | ❌ | ❌ |
| Validate config | <1ms | No | Errors only | ✅ (errors) | ❌ |
| LLM API call | 500-5000ms | Network | Yes | ✅ (status) | ✅ (perf) |
| Judge evaluation | 1000-3000ms | Network | Yes | ✅ (status) | ✅ (perf) |
| Process scenario | 500-5000ms | Network | Yes | ✅ (progress) | ✅ (workflow) |
| Save results | 1-50ms | File I/O | No | ✅ (completion) | ❌ |
| Generate report | 50-500ms | File I/O | Yes | ✅ (completion) | ❌ |
| Transform data | <1ms | No | No | ❌ | ❌ |
| Batch execution | Variable | Network | Yes | ✅ (progress) | ✅ (coordination) |

**Rule of Thumb:**
- **Logging:** Human-readable events, errors, status updates, I/O operations
- **OT Spans:** Expensive network operations (LLM calls, judge evals), high-level workflow coordination

---

## Implementation Guidelines

### Logging Setup

**Two-Level Logging Architecture:**

**1. Application-Level Logger** (top-level lifecycle)
```python
from gavel_ai.log_config import create_logger

app_logger = create_logger("gavel-ai")

# Usage - Top-level lifecycle events:
app_logger.info("Gavel-AI v0.1.0 started")
app_logger.info("Evaluation 'test_os' created")
app_logger.error("Failed to initialize provider", exc_info=True)
```

**Output:** `.gavel/gavel.log` (rolling file, 10MB max, 5 backups)

**2. Run-Level Logger** (run-specific operations)
```python
from gavel_ai.log_config import create_logger

run_logger = create_logger(f"gavel-ai.run.{run_id}")

# Usage - Run-specific operations:
run_logger.info("Loaded 15 scenarios")
run_logger.info("Executing scenario 'test-1'")
run_logger.info("Judge 'similarity' scored 8/10")
run_logger.error("LLM call failed", exc_info=True)
```

**Output:** `.gavel/evaluations/{eval}/runs/{run_id}/run.log`

**3. Console Output** (user feedback via typer.echo)
```python
import typer

# User-facing status updates (not logged to files):
typer.echo("✓ Loaded 15 scenarios")
typer.echo("Executing scenarios...")
typer.secho("Error: Missing API key", fg=typer.colors.RED, err=True)
```

**Output:** stdout/stderr

### Telemetry Setup

**Module-level tracer:**
```python
from gavel_ai.telemetry import get_tracer

tracer = get_tracer(__name__)

# Usage - ONLY for expensive/measurable operations:
with tracer.start_as_current_span("llm.call") as span:
    span.set_attribute("llm.provider", "anthropic")
    span.set_attribute("llm.latency_ms", duration_ms)
    result = await expensive_operation()
```

**Output Destination:**
- `.gavel/evaluations/{eval}/runs/{run_id}/telemetry.jsonl`

---

## Telemetry Span Schema

**Minimal Span Structure:**
```json
{
  "name": "llm.call",
  "trace_id": "7e5119529ba632d81ac0dac7b14e6a1e",
  "span_id": "b636602ef135a53c",
  "parent_id": "d4abb4363b352e2c",
  "start_time": 1735674974296088000,
  "end_time": 1735674976629510000,
  "duration_ns": 2333422000,
  "attributes": {
    "llm.provider": "anthropic",
    "llm.model": "claude-3-5-sonnet",
    "llm.tokens.prompt": 150,
    "llm.tokens.completion": 100,
    "llm.latency_ms": 2333,
    "run_id": "run-20251231-120000",
    "scenario.id": "test-1"
  }
}
```

**Standard Attributes (all spans):**
- `run_id` - Current run identifier
- `trace_id` - Distributed trace ID

**Operation-Specific Attributes:**

**LLM Calls:**
- `llm.provider` - Provider name (anthropic, openai, etc.)
- `llm.model` - Model version
- `llm.tokens.prompt` - Prompt token count
- `llm.tokens.completion` - Completion token count
- `llm.latency_ms` - API latency in milliseconds

**Judge Evaluations:**
- `judge.id` - Judge identifier
- `judge.name` - Judge DeepEval name
- `judge.score` - Evaluation score (1-10)
- `scenario.id` - Scenario being judged

**Processors:**
- `processor.type` - Processor type (prompt_input, closedbox_input)
- `scenario.id` - Scenario being processed
- `input.length` - Input text length

**Batch Execution:**
- `executor.parallelism` - Concurrency level
- `batch.size` - Number of items in batch
- `batch.completed` - Number completed
- `batch.failed` - Number failed

---

## Migration Plan

### Phase 1: Audit Current Spans
- [x] Identify all current OT span usage
- [ ] Classify each as "keep" (valuable) or "remove" (routine logging)

### Phase 2: Remove Non-Essential Spans
- [ ] Remove spans from config loading (config_loader.py)
- [ ] Remove spans from scenario loading
- [ ] Remove spans from simple validations
- [ ] Remove spans from storage operations
- [ ] Remove spans from report generation
- [ ] Keep spans ONLY for: LLM calls, judge evals, processors, batch execution

### Phase 3: Implement Two-Level Logging
- [ ] Create application-level logger → `.gavel/gavel.log` (rolling)
- [ ] Create run-level logger → `.gavel/evaluations/{eval}/runs/{run_id}/run.log`
- [ ] Add application-level logging for: startup, evaluation creation, shutdown
- [ ] Add run-level logging for: config loading, scenario execution, judge results, errors
- [ ] Keep console output (typer.echo) for user feedback only

### Phase 4: Configure Per-Run Telemetry Export
- [ ] Implement run-aware telemetry exporter
- [ ] Export to `.gavel/evaluations/{eval}/runs/{run_id}/telemetry.jsonl`
- [ ] Remove global `.gavel/telemetry.jsonl`

---

## Expected Results

**Before (Current):**
```
.gavel/telemetry.jsonl - 500 spans including config.load_config, storage.save, etc.
stdout - JSON spam + minimal user feedback
```

**After (Fixed):**
```
.gavel/gavel.log - Application lifecycle events (startup, eval creation)
.gavel/evaluations/test_os/runs/run-123/run.log - Run operations (config, scenarios, results)
.gavel/evaluations/test_os/runs/run-123/telemetry.jsonl - 15-20 spans (LLM, judge, processor only)
stdout - Clean progress updates and status (typer.echo)
```

**Telemetry File Size Reduction:** ~95% (500 spans → 15-20 spans)
**Telemetry Value Increase:** 100% signal, 0% noise
**Logging Clarity:** Application vs Run events clearly separated

---

## Acceptance Criteria

- [ ] Config loading uses logging, not OT spans
- [ ] Scenario loading uses logging, not OT spans
- [ ] LLM calls emit OT spans with token counts and latency
- [ ] Judge evaluations emit OT spans with scores
- [ ] Processor execution emits OT spans with scenario context
- [ ] Batch execution emits OT spans for workflow coordination
- [ ] Storage/report operations use logging, NOT OT spans
- [ ] telemetry.jsonl contains ONLY high-value performance data (network ops)
- [ ] .gavel/gavel.log contains application lifecycle events
- [ ] .gavel/evaluations/{eval}/runs/{run_id}/run.log contains run operations
- [ ] stdout shows clean user-facing progress updates (no JSON, no debug)

---

## References

- **Project Context:** _bmad-output/planning-artifacts/project-context.md (Telemetry section)
- **Architecture:** _bmad-output/planning-artifacts/architecture.md (Decision 9: Telemetry)
- **PRD:** _bmad-output/planning-artifacts/prd.md (FR-2.4, FR-8.3, FR-9.5)
- **Epic 7:** Story 7.1 - Implement Telemetry Collection & Storage

---

**Next Steps:**
1. Review and approve this specification
2. Implement Phase 2 (remove non-essential spans)
3. Implement Phase 3 (add missing logging)
4. Implement Phase 4 (per-run telemetry export) - Defer to Epic 7 Story 7.1
