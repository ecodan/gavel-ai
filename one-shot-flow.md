# OneShot Evaluation Flow: Single Scenario Processing & Judging

This document traces the execution path of a single scenario row through the gavel-ai one-shot workflow, from scenario input through processor execution to judge evaluation and storage.

## Sequence Diagram: Scenario → Output → Judged Result

```mermaid
sequenceDiagram
    participant User as User/<br/>CLI
    participant Workflow as OneShot<br/>Workflow
    participant ValidatorStep as ValidatorStep
    participant ScenarioStep as ScenarioProcessorStep
    participant Executor as Executor
    participant PromptProc as PromptInputProcessor
    participant Factory as ProviderFactory
    participant Agent as Pydantic-AI<br/>Agent
    participant Provider as LLM Provider<br/>(Anthropic/OpenAI/etc)
    participant Context as RunContext<br/>(LocalRunContext)
    participant JudgeStep as JudgeRunnerStep
    participant JudgeExec as JudgeExecutor
    participant DeepEval as DeepEval<br/>GEval
    participant Storage as Result Storage<br/>(JSONL)

    User->>Workflow: run(eval_name)
    activate Workflow
    
    Note over Workflow: Phase 1: Validation
    Workflow->>ValidatorStep: execute(context)
    activate ValidatorStep
    ValidatorStep->>Context: read configs
    ValidatorStep-->>Workflow: ✓ valid
    deactivate ValidatorStep

    Note over Workflow: Phase 2: Scenario Processing
    Workflow->>ScenarioStep: execute(context)
    activate ScenarioStep
    
    ScenarioStep->>Context: read scenarios
    Note right of Context: Scenario row:<br/>id: "headline-160000-www-bbc-com"<br/>input: {site, html}
    
    ScenarioStep->>ScenarioStep: Convert scenario→Input<br/>Input(id, text, metadata)
    Note right of ScenarioStep: Input.text = str(scenario.input)<br/>= "{site, html}" stringified
    
    ScenarioStep->>ScenarioStep: Load model_def from agents.json
    ScenarioStep->>PromptProc: new PromptInputProcessor(<br/>config, model_def)
    activate PromptProc
    PromptProc->>Factory: create_agent(model_def)
    activate Factory
    Factory->>Agent: Agent(model="claude-haiku...")
    activate Agent
    Agent-->>Factory: ✓ agent created
    deactivate Agent
    Factory-->>PromptProc: ✓ agent instance
    deactivate Factory
    deactivate PromptProc
    
    ScenarioStep->>Executor: new Executor(<br/>processor=PromptProc)
    activate Executor
    
    Executor->>PromptProc: process(inputs=[Input])
    activate PromptProc
    
    Note over PromptProc: BUG: Prompt not loaded!<br/>Should call context.get_prompt("default:v1")<br/>Instead uses Input.text directly
    
    PromptProc->>PromptProc: prompt = input.text<br/>(stringified dict, not template)
    PromptProc->>PromptProc: _call_llm(prompt)
    
    PromptProc->>Factory: call_agent(agent, prompt)
    activate Factory
    Factory->>Agent: agent.run(prompt)
    activate Agent
    Agent->>Provider: send_message(prompt)
    activate Provider
    
    Note over Provider: LLM receives malformed prompt:<br/>"{'site': 'www.bbc.com', 'html': '...'}"<br/>NOT the JSON extraction template
    
    Provider-->>Agent: response (verbose markdown analysis)
    deactivate Provider
    Agent-->>Factory: AgentRunResult<br/>(output, tokens)
    deactivate Agent
    Factory-->>PromptProc: (output, metadata)
    deactivate Factory
    
    deactivate PromptProc
    
    Note right of PromptProc: ProcessorResult<br/>output = "# BBC Homepage Analysis..."<br/>metadata = {tokens, latency_ms}
    
    Executor->>Executor: on_result callback
    Executor->>Context: OutputRecord append<br/>(scenario_id, processor_output,<br/>variant_id, test_subject)
    
    deactivate Executor
    
    ScenarioStep->>Context: context.processor_results =<br/>[OutputRecord, ...]
    deactivate ScenarioStep
    
    Workflow->>JudgeStep: execute(context)
    activate JudgeStep
    
    Note over JudgeStep: Phase 3: Judging
    Note right of JudgeStep: processor_output = markdown analysis<br/>Expected: JSON with "stories" key<br/>Judge evaluation will fail
    
    JudgeStep->>Context: read processor_results
    JudgeStep->>Context: read eval_config (judges)
    
    JudgeStep->>JudgeExec: new JudgeExecutor(judges)
    activate JudgeExec
    
    loop For each judge in eval_config
        JudgeExec->>DeepEval: evaluate(scenario, output)
        activate DeepEval
        
        Note over DeepEval: Judge expects JSON structure:<br/>{stories: [{title, url, date}]}<br/>Receives: markdown text
        
        DeepEval->>DeepEval: parse/validate output<br/>→ JSON schema mismatch
        DeepEval-->>JudgeExec: score, reason<br/>(or error on retry limit)
        deactivate DeepEval
    end
    
    JudgeExec-->>JudgeStep: evaluation_results
    deactivate JudgeExec
    
    JudgeStep->>Context: JudgedRecord append<br/>(scenario_id, judge_name,<br/>score, reason, error)
    deactivate JudgeStep
    
    Note over Context: Final Stored State:<br/>results_raw.jsonl:<br/>  {scenario_id, variant_id,<br/>   processor_output: "# BBC...",<br/>   test_subject: "default"}<br/>results_judged.jsonl:<br/>  {scenario_id, judge_name,<br/>   score: null, reason: "...",<br/>   error: "..."}

    Workflow->>Storage: report_runner.execute(context)
    activate Storage
    Storage->>Storage: Render HTML report<br/>with failed judge scores
    Storage-->>Workflow: ✓ report.html
    deactivate Storage
    
    Workflow-->>User: ✓ Evaluation complete<br/>(with judge failures)
    deactivate Workflow
```

---

## Data Flow: Transformations at Each Layer

### Layer 1: Input (Scenario → Input)

```
Scenario (from scenarios.json)
├── id: "headline-160000-www-bbc-com"
├── input: {
│     "site": "www.bbc.com",
│     "html": "<!DOCTYPE html>..."
│   }
└── metadata: {}

    ↓ ScenarioProcessorStep._convert_scenarios()

Input (for processor)
├── id: "headline-160000-www-bbc-com"
├── text: "{'site': 'www.bbc.com', 'html': '...'}"  ← BUG: Stringified input, not template
└── metadata: {}
```

### Layer 2: Processing (Input → ProcessorResult)

```
PromptInputProcessor.process([Input])
  │
  ├─ [BUG] Load prompt template
  │   Expected: context.get_prompt("default:v1")
  │   Actual:   (never called - prompt_processor.py is stub)
  │
  ├─ Render template
  │   Expected: template.format(input=Input.metadata)
  │   Actual:   (skipped)
  │
  └─ Call LLM
      Input to LLM: Input.text stringified dict
      Output: markdown analysis (not JSON)
      
      ↓

ProcessorResult
├── output: "# BBC Homepage Analysis\n\n## Overview\n..."
└── metadata: {
      "tokens": {"prompt": 0, "completion": 0},
      "latency_ms": 0
    }

    ↓ _make_output_record()

OutputRecord
├── test_subject: "default"
├── variant_id: "claude-haiku-4-5-20251001"
├── scenario_id: "headline-160000-www-bbc-com"
├── processor_output: "# BBC Homepage Analysis..."
├── tokens_prompt: 0
├── tokens_completion: 0
└── timestamp: "2026-04-11T15:12:41.243129+00:00"
```

### Layer 3: Judging (OutputRecord → JudgedRecord)

```
JudgeRunnerStep.execute(context)
  │
  ├─ Get processor results
  ├─ For each judge in eval_config
  │   │
  │   ├─ DeepEvalJudge.evaluate(scenario, output)
  │   │   │
  │   │   ├─ Schema: Expects JSON with "stories" key
  │   │   ├─ Actual output: Markdown analysis (no "stories")
  │   │   ├─ GEval criteria check fails
  │   │   └─ Score: null (or error)
  │   │
  │   └─ JudgeExecutor.execute() → evaluation_results
  │
  └─ Store results

JudgedRecord
├── scenario_id: "headline-160000-www-bbc-com"
├── variant_id: "claude-haiku-4-5-20251001"
├── judge_name: "schema_compliance"
├── score: null
├── reason: "Output does not contain expected JSON structure"
└── error: "JSON parsing failed" (or rate limit error)
```

---

## Class Hierarchy & Responsibilities

### Step Abstraction (Base Class: `core/steps/base.py::Step`)

```
Step (ABC)
├── phase: StepPhase enum
├── execute(context: RunContext) → None
└── safe_execute(context: RunContext) → None (error handling wrapper)

  ├── ValidatorStep
  │   └── Validates all config files before execution
  │
  ├── ScenarioProcessorStep
  │   ├── Converts scenarios → inputs
  │   ├── Instantiates processor (PromptInputProcessor or ClosedBoxInputProcessor)
  │   ├── Creates Executor
  │   └── Collects OutputRecords
  │
  ├── JudgeRunnerStep
  │   ├── Creates judge instances
  │   ├── Creates JudgeExecutor
  │   └── Collects JudgedRecords
  │
  └── ReportRunnerStep
      └── Renders reports from judged results
```

### Processor Abstraction (Base Class: `processors/base.py::InputProcessor`)

```
InputProcessor (ABC)
└── async process(inputs: List[Input]) → ProcessorResult

  ├── PromptInputProcessor [CURRENT - HAS BUG]
  │   ├── Uses Pydantic-AI Agent
  │   ├── Calls LLM with prompt
  │   └── Returns text output
  │       [MISSING: Prompt template loading & rendering]
  │
  ├── ClosedBoxInputProcessor
  │   ├── Calls external API
  │   └── Returns response
  │
  └── ScenarioProcessor [For conversational]
      └── Wraps inner processor for multi-turn
```

### Judge Abstraction (Base Class: `judges/base.py::Judge`)

```
Judge (ABC)
└── async evaluate(scenario, subject_output) → EvaluationResult

  ├── DeepEvalJudge
  │   ├── Wraps DeepEval metric
  │   ├── Criteria: schema validation, quality check
  │   └── Scores 1-10 or null on error
  │
  └── CustomGEvalJudge [Future]
      └── Custom evaluation logic
```

---

## Context Abstraction (Storage Layer)

```
RunContext (ABC)
├── eval_context: EvalContext
├── run_id: str
├── results_raw: RecordDataSource[OutputRecord]
├── results_judged: RecordDataSource[JudgedRecord]
└── run_logger: logging.Logger

  └── LocalRunContext [CONCRETE]
      ├── eval_context: LocalFileSystemEvalContext
      ├── .gavel/evaluations/{eval_name}/
      │   ├── config/
      │   │   ├── eval_config.json
      │   │   ├── agents.json
      │   │   ├── prompts/default.toml [NOT LOADED BY PROCESSOR]
      │   └── data/scenarios.json
      └── .gavel/evaluations/{eval_name}/runs/{run_id}/
          ├── .config/ (snapshot)
          ├── results_raw.jsonl [OutputRecord storage]
          ├── results_judged.jsonl [JudgedRecord storage]
          └── report.html
```

---

## The Bug: Missing Prompt Template Loading

### What Should Happen

```
ScenarioProcessorStep.execute(context)
  │
  ├─ test_subject = "default:v1"
  │
  └─ PromptInputProcessor(context, test_subject, model_def)
      
      PromptInputProcessor.process(inputs)
        │
        ├─ For each input:
        │   ├─ template = context.get_prompt(test_subject)
        │   │             → Loads .gavel/.../prompts/default.toml
        │   │             → Returns "You are a specialized news content analyzer..."
        │   │
        │   ├─ prompt = template.format(input=input.metadata)
        │   │           → Renders "{{ input.html }}" with actual HTML
        │   │
        │   └─ output = await self.agent.run(prompt)
        │              → LLM receives proper instructions + HTML
        │
        └─ OutputRecord with JSON output
```

### What Actually Happens

```
PromptInputProcessor.process(inputs)
  │
  ├─ For each input:
  │   ├─ prompt = input.text
  │   │           → Receives stringified dict: "{'site': '...', 'html': '...'}"
  │   │
  │   └─ output = await self.agent.run(prompt)
  │              → LLM sees malformed input, ignores template
  │              → Returns helpful markdown analysis instead
  │
  └─ OutputRecord with markdown output (mismatch!)
```

### Root Cause

1. **PromptInputProcessor is a stub** (`prompt_processor.py:119`)
   - Comment says: "Real implementation will load template and render with variables"
   - Currently just uses raw input text

2. **Prompt template never passed to processor**
   - `ScenarioProcessorStep` knows `test_subject = "default:v1"`
   - But doesn't pass it to `PromptInputProcessor`

3. **Processor has no access to context**
   - Can't call `context.get_prompt()`
   - No way to load TOML template files

---

## Summary

| Stage | Component | Data | Status |
|-------|-----------|------|--------|
| Input | ScenarioProcessorStep | Scenario → Input | ✓ Works |
| Process | PromptInputProcessor | Input → OutputRecord | ❌ BUG: No template loading |
| Judge | JudgeRunnerStep | OutputRecord → JudgedRecord | ✓ Works (but fails on bad output) |
| Store | RunContext | OutputRecord, JudgedRecord → JSONL | ✓ Works |
| Report | ReportRunnerStep | Results → HTML | ✓ Works |

**Fix Required**: Implement prompt template loading in `PromptInputProcessor` (see root cause section in debug output).
