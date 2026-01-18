---
stepsCompleted: [1, 2, 3]
inputDocuments:
  - _bmad-output/planning-artifacts/prd-conversational-eval.md
  - _bmad-output/planning-artifacts/tdd-conversational-eval.md
workflowType: 'epics-and-stories'
projectName: 'gavel-ai'
workflow: 'Conversational Evaluation (v2) - Incremental Epics'
date: '2026-01-18'
epicStructureApproved: true
allStoriesApproved: true
---

# gavel-ai Conversational Evaluation - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for **Conversational Evaluation (v2)**, decomposing requirements from the PRD and TDD into implementable stories organized by user value.

Conversational Evaluation extends gavel-ai's Step-based architecture to enable realistic multi-turn dialogue evaluation. The epic structure emphasizes **pattern reuse** (ValidateStep, JudgeRunnerStep, ReportingStep) while introducing new capabilities (GenerateStep, ConversationalProcessingStep, TurnGenerator).

---

## Requirements Inventory

### Functional Requirements (23 FRs across 7 categories)

**FR-C1: Scenario Definition & Generation (2 FRs)**
- FR-C1.1: Define conversational scenarios with user goal, context, dialogue guidance (scenarios.json or CSV import)
- FR-C1.2: GenerateStep generates scenarios from prompts (prompts/generate_scenarios.toml → scenarios.jsonl) - optional in MVP

**FR-C2: Multi-Turn Execution (4 FRs)**
- FR-C2.1: Execute multi-turn conversations locally or in-situ (deployedsystems via HTTP)
- FR-C2.2: Turn generation on-the-fly based on scenario guidance and conversation history (NOT pre-written; deterministic)
- FR-C2.3: Complete conversation transcripts captured and preserved for analysis
- FR-C2.4: Run multi-turn conversations against multiple variants (models, prompts, endpoints) with identical turn sequences

**FR-C3: Turn & Conversation Judging (4 FRs)**
- FR-C3.1: Turn-level judges assess individual responses in dialogue context (relevancy, tone, accuracy, completeness)
- FR-C3.2: Conversation-level judges assess overall dialogue quality (coherence, goal achievement, safety)
- FR-C3.3: Both turn and conversation judges 100% declarative via config (deepeval.turn_* and deepeval.conversation_* via schema-configs.md)
- FR-C3.4: Judge execution reproducible (same transcript + judges = identical results)

**FR-C4: Re-Judge Workflow (2 FRs)**
- FR-C4.1: Re-judge existing conversations without re-execution (`gavel conversational judge --run <timestamp>` fast iteration)
- FR-C4.2: Judge changes tracked and reportable (original judges preserved in manifest; modifications timestamped)

**FR-C5: Conversation Reporting (3 FRs)**
- FR-C5.1: Conversation reports follow dialogue structure (summary + per-scenario detail with turn-level scores)
- FR-C5.2: Turn-level judge reasoning visible and inspectable (expandable sections)
- FR-C5.3: Reports answer "How did conversation go?" clearly (variant comparison, score trends)

**FR-C6: Data Artifacts & Reproducibility (3 FRs)**
- FR-C6.1: Conversational runs follow same artifact structure as OneShot (manifest.json, config/, telemetry.jsonl, results_raw.jsonl, results_judged.jsonl, run_metadata.json, report.html)
- FR-C6.2: Conversation transcripts preserved in conversations.jsonl (one entry per scenario × variant with full turn history)
- FR-C6.3: Re-judging preserves original judge results (results_raw.jsonl immutable; results_judged.jsonl regenerable)

**FR-C7: CLI Interface (5 FRs)**
- FR-C7.1: `gavel conversational create --eval <name>` scaffolds conversational evaluations
- FR-C7.2: `gavel conversational run --eval <name>` executes conversations with progress indicators
- FR-C7.3: `gavel conversational judge --eval <name> --run <timestamp>` applies judges to existing conversations (no API calls)
- FR-C7.4: `gavel conversational report --eval <name> --run <timestamp>` generates HTML/Markdown reports
- FR-C7.5: `gavel conversational list` displays run history with filtering

**Total: 23 FRs**

### Non-Functional Requirements (8 NFRs across 5 categories)

**Performance (2 NFRs)**
- NFR-C-P1: Realistic conversation timelines (turn generation <1s, typical 5-10 turn conversation 15-30s, re-judging <1s per 100 turns)
- NFR-C-P2: Parallel scenario × variant execution; sequential turns within conversations

**Reliability (3 NFRs)**
- NFR-C-R1: Reproducible execution (same scenario + context = identical turn sequence)
- NFR-C-R2: Robust turn generation (graceful edge cases, timeout handling, clear errors)
- NFR-C-R3: Data integrity (durable writes, no partial artifacts)

**Reproducibility & Auditability (2 NFRs)**
- NFR-C-R4: Turn generation deterministic (same scenario + history = same turn if temperature=0)
- NFR-C-R5: Judge reproducibility (same transcript + judges = identical scores)

**Total: 8 NFRs**

### Additional Requirements from Architecture & Design

**Architecture Patterns**
- Conversational is a Step instance (same abstraction as OneShot); reuses ValidateStep, JudgeRunnerStep, ReportingStep
- GenerateStep (optional, new) elaborates scenarios
- ConversationalProcessingStep (new, core) executes multi-turn dialogues
- TurnGenerator (new component) creates user turns dynamically on-the-fly

**Two-Artifact Design**
- results_raw.jsonl (immutable): Processor outputs (turn-by-turn records)
- results_judged.jsonl (mutable): Judge results (regenerable when judges change)
- conversations.jsonl (new): Full transcripts for analysis and re-judging

**Configuration & Reproducibility**
- eval_config.json extension for conversational-specific settings (max_turns, turn_limit, turn_generator config, elaboration_enabled)
- Scenario schema: id, user_goal (required), context (optional), dialogue_guidance (optional)
- Judge configuration: turn-level judges (type: "turn", deepeval_name) and conversation-level judges (type: "conversation", deepeval_name)
- Deterministic execution: temperature=0 for turn generation and judges

**Data Models Required**
- ConversationScenario: id, user_goal, context, dialogue_guidance, elaborated (bool), personas, edge_cases
- Turn: turn_number, role (user|assistant), content, timestamp, metadata
- ConversationState: scenario_id, variant_id, turns[], start_time, metadata
- ConversationResult: scenario_id, variant_id, conversation_transcript, results_raw[], duration_ms, tokens_total
- TurnGenerator: algorithm for on-the-fly generation (NOT pre-written, NOT streaming; purely reactive to history)

**Implementation Phases**
1. Config schema + data models
2. TurnGenerator + ConversationalProcessingStep core execution
3. Turn-level and conversation-level judge enhancement
4. Re-judge workflow + conversation reporting
5. CLI integration (`gavel conversational` subcommands) + testing

---

## Epic List

1. **Epic C1: Configuration & Data Models** - Setup conversational evaluation configuration schema and core data structures (foundation)
2. **Epic C7: CLI Infrastructure** - Establish `gavel conv|conversational` command structure enabling testing after each epic (moved early for incremental validation)
3. **Epic C2: Scenario Elaboration (GenerateStep)** - Optional scenario enrichment with personas and dialogue guidance
4. **Epic C3: Multi-Turn Execution** - Core conversational processing with on-the-fly turn generation
5. **Epic C4: Turn & Conversation Judging** - Enhanced judge execution for turn-level and conversation-level assessment
6. **Epic C5: Re-Judge Workflow** - Re-judge existing conversations without re-execution
7. **Epic C6: Conversation Reporting** - Generate reports showing turn-level detail + conversation summary
8. **Epic C8: Testing & Validation** - Unit, integration, and end-to-end tests for conversational workflows (formalized after each epic)

---

## Epic C1: Configuration & Data Models

**Epic Goal:** Establish conversational evaluation configuration schema and core data structures needed for all subsequent epics.

**User Stories:**

### Story C1.1: Define Conversational Scenario Schema

As a developer,
I want scenarios to support user_goal, context, and dialogue_guidance,
So that turn generation can be realistic and context-aware.

**Acceptance Criteria:**

- **Given** a scenarios.json file exists with conversational scenarios
  **When** it is loaded
  **Then** each scenario has: id (required), user_goal (required), context (optional), dialogue_guidance (optional)

- **Given** a scenario defines user_goal
  **When** examined
  **Then** it's a clear, actionable description of what the simulated user is trying to accomplish

- **Given** dialogue_guidance is defined
  **When** examined
  **Then** it contains: tone_preference, escalation_strategy, factual_constraints

- **Given** scenarios are loaded
  **When** validated
  **Then** missing user_goal raises ValidationError with clear guidance

**Related Requirements:** FR-C1.1, NFR-C-R1 (Reproducibility)

---

### Story C1.2: Implement ConversationScenario Pydantic Model

As a developer,
I want a ConversationScenario data model,
So that scenarios are type-safe and can be elaborated.

**Acceptance Criteria:**

- **Given** ConversationScenario model exists
  **When** examined
  **Then** it has fields: id, user_goal, context, dialogue_guidance, elaborated (bool), personas, edge_cases, factual_constraints

- **Given** a scenario is parsed
  **When** elaborated=False
  **Then** personas, edge_cases, factual_constraints are null

- **Given** a scenario is elaborated
  **When** elaborated=True
  **Then** personas, edge_cases, factual_constraints contain enriched content

- **Given** scenarios are serialized to JSON
  **When** examined
  **Then** all fields serialize correctly; null fields omitted

**Related Requirements:** FR-C1.1, FR-C1.2

---

### Story C1.3: Implement Turn and ConversationState Models

As a developer,
I want Turn and ConversationState models to manage dialogue history,
So that turns can be tracked and conversation state maintained during execution.

**Acceptance Criteria:**

- **Given** Turn model exists
  **When** examined
  **Then** it has: turn_number (int), role (user|assistant), content (str), timestamp (datetime), metadata (dict, optional)

- **Given** ConversationState is initialized
  **When** examined
  **Then** it has: scenario_id, variant_id, turns (list), start_time, metadata

- **Given** add_turn(role, content) is called
  **When** completed
  **Then** Turn is appended to turns list with auto-incremented turn_number and current timestamp

- **Given** conversation has multiple turns
  **When** history property is accessed
  **Then** formatted string is returned: "user: content\nassistant: content\nuser: content..."

- **Given** metadata is provided with a turn
  **When** stored
  **Then** tokens_prompt, tokens_completion, latency_ms can be accessed

**Related Requirements:** FR-C2.3, NFR-C-R1 (Reproducibility)

---

### Story C1.4: Extend eval_config.json for Conversational Settings

As a user,
I want to configure conversational-specific settings in eval_config.json,
So that turn generation and elaboration behavior can be customized.

**Acceptance Criteria:**

- **Given** eval_config.json includes "conversational" section
  **When** loaded
  **Then** it contains: max_turns (int), max_turn_length (int), turn_generator (model, temperature, max_tokens), elaboration (enabled, elaboration_template)

- **Given** max_turns = 10
  **When** conversation executes
  **Then** loop terminates after 10 turns (or earlier if goal achieved)

- **Given** turn_generator temperature = 0
  **When** same scenario runs twice
  **Then** identical turns are generated (deterministic)

- **Given** elaboration.enabled = true
  **When** run includes --elaborate-scenarios flag
  **Then** GenerateStep is invoked before ConversationalProcessingStep

**Related Requirements:** FR-C1.1, FR-C2.2, NFR-C-R4 (Determinism)

---

### Story C1.5: Implement ConversationResult Data Model

As a developer,
I want ConversationResult to capture execution outcome,
So that results can be stored and passed to judge runner.

**Acceptance Criteria:**

- **Given** ConversationResult is created
  **When** examined
  **Then** it has: scenario_id, variant_id, conversation_transcript (ConversationState), results_raw (list), duration_ms, tokens_total

- **Given** ConversationResult is created with results_raw
  **When** examined
  **Then** each entry contains: processor_output, timing_ms, tokens_prompt, tokens_completion, error (optional)

- **Given** multiple conversations are executed
  **When** results are aggregated
  **Then** each ConversationResult is independent and complete

- **Given** ConversationResult is serialized
  **When** written to conversations.jsonl
  **Then** full transcript and metadata are preserved

**Related Requirements:** FR-C2.3, FR-C6.2

---

## Epic C2: Scenario Generation (GenerateStep)

**Epic Goal:** Implement optional scenario generation where prompts describe desired test scenarios and GenerateStep produces scenarios.jsonl (optional in MVP).

**User Stories:**

### Story C2.1: Create GenerateStep Skeleton for Scenario Generation

As a developer,
I want GenerateStep to fit into the Step abstraction and generate scenarios from prompts,
So that scenarios can be created via LLM generation before execution.

**Acceptance Criteria:**

- **Given** GenerateStep class exists
  **When** examined
  **Then** it implements Step interface: async execute(config) → result

- **Given** config references a prompt file (prompts/generate_scenarios.toml)
  **When** execute() called
  **Then** prompt loaded and scenarios generated via LLM (via Executor)

- **Given** GenerateStep.execute() is called
  **When** completed
  **Then** output is scenarios.jsonl with generated scenarios (JSONL format, one per line)

- **Given** each generated scenario examined
  **When** checked
  **Then** it contains: id, user_goal (required), context (optional), dialogue_guidance (optional)

- **Given** GenerateStep completes
  **When** telemetry recorded
  **Then** span recorded with trace_id, scenario_count, prompt_file used, LLM model

---

### Story C2.2: Implement Scenario Generation Logic with LLM

As a developer,
I want GenerateStep to invoke LLM to generate scenarios from a prompt,
So that users can describe test needs and get scenarios automatically.

**Acceptance Criteria:**

- **Given** prompts/generate_scenarios.toml loaded with scenario generation task
  **When** LLM invoked (via Executor) with temperature=0
  **Then** LLM generates N scenarios based on prompt description

- **Given** LLM generates scenarios
  **When** output parsed
  **Then** each scenario has: id (auto-generated or from LLM), user_goal (from LLM), context (from LLM), dialogue_guidance (from LLM, optional)

- **Given** dialogue_guidance included
  **When** examined
  **Then** it contains tone, escalation_strategy, factual_constraints as appropriate for scenario

- **Given** same prompt run twice with temperature=0
  **When** scenarios generated
  **Then** identical scenario set produced (deterministic)

- **Given** scenarios generated
  **When** written to scenarios.jsonl (JSONL format)
  **Then** each line is valid JSON; one scenario per line; no nesting; ready for ConversationalProcessingStep

**Related Requirements:** FR-C1.2, NFR-C-R4 (Determinism)

---

### Story C2.3: Wire GenerateStep into Workflow via CLI Command

As a user,
I want to use `gavel conv generate --eval <name>` to generate scenarios from a prompt,
So that I can create scenarios without writing JSON manually.

**Acceptance Criteria:**

- **Given** `gavel conv generate --eval my_eval` executed
  **When** runs
  **Then** GenerateStep invoked; prompt loaded from prompts/generate_scenarios.toml; scenarios generated and written to data/scenarios.jsonl

- **Given** generation completes successfully
  **When** progress displayed
  **Then** user sees: "Generated N scenarios with LLM"

- **Given** scenarios.jsonl created
  **When** user runs `gavel conv run --eval my_eval`
  **Then** existing scenarios.jsonl used (no re-generation unless `gavel conv generate` run again)

- **Given** user provides custom prompt with `--prompt-file` flag
  **When** `gavel conv generate --eval my_eval --prompt-file custom_scenarios.toml` executed
  **Then** custom prompt used instead of default prompts/generate_scenarios.toml

- **Given** generation fails (invalid prompt, LLM error, parsing error)
  **When** error caught
  **Then** clear error message displayed: "Failed to generate scenarios: [reason]"; scenarios.jsonl not modified/deleted

**Related Requirements:** FR-C1.2

---

## Epic C3: Multi-Turn Execution

**Epic Goal:** Implement core conversational processing with on-the-fly turn generation (TurnGenerator), conversation state management, and multi-turn execution.

**User Stories:**

### Story C3.1: Create TurnGenerator Interface and Algorithm

As a developer,
I want a TurnGenerator component that creates turns dynamically,
So that conversations adapt to LLM responses in real-time.

**Acceptance Criteria:**

- **Given** TurnGenerator is initialized with a scenario and LLM model
  **When** examined
  **Then** it has: generate_turn(scenario, history) → GeneratedTurn

- **Given** generate_turn() is called
  **When** completed
  **Then** it returns: {content (str), metadata (dict), should_continue (bool)}

- **Given** same scenario and history are provided twice with temperature=0
  **When** generate_turn() called
  **Then** identical turns are generated (deterministic)

- **Given** conversation history is provided
  **When** turn generated
  **Then** next turn moves toward scenario.user_goal and respects dialogue_guidance

- **Given** user_goal is achieved or max_turns reached
  **When** should_continue evaluated
  **Then** it's set to False to end conversation

**Related Requirements:** FR-C2.2, NFR-C-R4 (Determinism), NFR-C-P1 (Performance <1s per turn)

---

### Story C3.2: Implement ConversationalProcessingStep

As a developer,
I want ConversationalProcessingStep to orchestrate multi-turn conversations,
So that scenarios × variants are executed with complete transcripts.

**Acceptance Criteria:**

- **Given** ConversationalProcessingStep is initialized with scenarios and variants
  **When** execute() is called
  **Then** for each scenario × variant, one conversation is executed

- **Given** conversation starts
  **When** initialized
  **Then** ConversationState created; TurnGenerator generates first user turn

- **Given** first user turn generated
  **When** appended to ConversationState
  **Then** conversation.add_turn("user", turn_content) called; turn_number=0

- **Given** user turn added
  **When** LLM called via Executor
  **Then** assistant response received and add_turn("assistant", response) called

- **Given** assistant response added
  **When** next iteration
  **Then** TurnGenerator called with updated conversation.history to generate next user turn

- **Given** should_continue=False or max_turns reached
  **When** loop evaluated
  **Then** conversation terminates; transcript is complete

- **Given** conversation complete
  **When** results collected
  **Then** conversations.jsonl entry created with full transcript; results_raw entries created (one per turn)

**Related Requirements:** FR-C2.1, FR-C2.2, FR-C2.3, NFR-C-R1 (Reproducibility)

---

### Story C3.3: Support Multiple Variants in Conversational Execution

As a user,
I want to test the same scenario against multiple models,
So that I can compare dialogue behavior across variants.

**Acceptance Criteria:**

- **Given** multiple variants (Claude, GPT, Gemini) are configured
  **When** scenario is executed
  **Then** ConversationalProcessingStep creates N conversations (one per variant)

- **Given** same scenario is executed against 3 variants
  **When** completed
  **Then** all 3 conversations have identical user turns (same TurnGenerator output)

- **Given** conversations × variants completed
  **When** examined
  **Then** each variant has unique LLM responses but same user inputs (deterministic setup)

- **Given** results_raw.jsonl is examined
  **When** checked
  **Then** multiple entries per scenario_id (one per variant)

**Related Requirements:** FR-C2.4, NFR-C-R1 (Reproducibility)

---

### Story C3.4: Export Conversations and Raw Results to JSONL

As a developer,
I want conversations and results_raw written to disk,
So that transcripts can be analyzed and re-judged.

**Acceptance Criteria:**

- **Given** ConversationalProcessingStep completes
  **When** results saved
  **Then** conversations.jsonl created with one entry per scenario × variant

- **Given** conversations.jsonl entry examined
  **When** checked
  **Then** it contains: scenario_id, variant_id, conversation array (full turn history), metadata

- **Given** results_raw.jsonl created
  **When** examined
  **Then** one JSONL entry per turn (not nested; same schema as OneShot)

- **Given** results_raw entry examined
  **When** checked
  **Then** it has: scenario_id, variant_id, processor_output, timing_ms, tokens_prompt, tokens_completion, timestamp

**Related Requirements:** FR-C6.2, FR-C6.3

---

### Story C3.5: Implement Conversation Timeout and Error Handling

As a developer,
I want conversations to timeout and handle errors gracefully,
So that long conversations don't hang and errors are clearly reported.

**Acceptance Criteria:**

- **Given** max_turns or max_duration configured
  **When** conversation executes
  **Then** loop terminates when limits reached

- **Given** TurnGenerator fails (returns error)
  **When** handled
  **Then** error logged; conversation marked incomplete; next scenario × variant proceeds

- **Given** LLM call times out
  **When** error caught
  **Then** retry logic applied (configurable max_retries); if all fail, mark conversation failed

- **Given** conversation fails
  **When** results_raw created
  **Then** error field populated with error message; execution continues

**Related Requirements:** NFR-C-R2 (Robust turn generation), NFR-C-R3 (Data integrity)

---

## Epic C4: Turn & Conversation Judging

**Epic Goal:** Implement unified Judge interface that accepts entire conversations and supports three judge types: out-of-the-box DeepEval judges, manually configured GEval judges, and bespoke custom judges. Orchestrate all judge types through JudgeRunnerStep with declarative configuration.

**User Stories:**

### Story C4.1: Implement Unified Judge Interface

As a developer,
I want a single Judge interface that supports DeepEval, GEval, and bespoke judges,
So that all judge types work consistently.

**Acceptance Criteria:**

- **Given** Judge base class/interface exists
  **When** examined
  **Then** it has: `async evaluate(conversation, scenario, variant_id, scenario_id) → JudgeResult`

- **Given** evaluate() is called
  **When** completed
  **Then** JudgeResult contains: judge_id, judge_name, judge_score (1-10), judge_reasoning, judge_evidence

- **Given** judge receives full conversation as input
  **When** executed
  **Then** entire conversation transcript is available for judging

- **Given** judge implementations created (DeepEvalJudge, GEvalJudge, BespokeJudge subclasses)
  **When** examined
  **Then** each inherits from Judge interface and implements evaluate()

- **Given** judge result created
  **When** examined
  **Then** it includes metadata: scenario_id, variant_id, judge_type (turn|conversation), judge_class_name

**Related Requirements:** FR-C3.1, FR-C3.2, NFR-C-R5 (Judge reproducibility)

---

### Story C4.2: Integrate Turn Judges into Orchestration

As a developer,
I want turn judges (DeepEval, GEval, bespoke) to be applied to conversations,
So that turn-level scoring is supported.

**Acceptance Criteria:**

- **Given** turn judges configured in eval_config.json
  **When** executed
  **Then** each turn judge receives entire conversation; produces aggregate score

- **Given** turn judge types: DeepEval (out-of-box), GEval (manual config), Bespoke (custom)
  **When** applied
  **Then** each type executes via unified Judge interface; one JudgeResult per judge

- **Given** multiple turn judges of different types
  **When** applied to one conversation
  **Then** all turn judges execute; all results collected

**Related Requirements:** FR-C3.1

---

### Story C4.3: Integrate Conversation Judges into Orchestration

As a developer,
I want conversation judges (DeepEval, GEval, bespoke) to be applied to conversations,
So that holistic conversation-level scoring is supported.

**Acceptance Criteria:**

- **Given** conversation judges configured in eval_config.json
  **When** executed
  **Then** each conversation judge receives entire conversation; produces score

- **Given** conversation judge types: DeepEval (out-of-box), GEval (manual config), Bespoke (custom)
  **When** applied
  **Then** each type executes via unified Judge interface; one JudgeResult per judge

- **Given** multiple conversation judges of different types
  **When** applied to one conversation
  **Then** all conversation judges execute; all results collected

**Related Requirements:** FR-C3.2

---

### Story C4.4: Enhance JudgeRunnerStep for Multi-Level Orchestration

As a developer,
I want JudgeRunnerStep to orchestrate all judge types and produce flattened JSONL output,
So that complete multi-level judging is available.

**Acceptance Criteria:**

- **Given** JudgeRunnerStep receives conversational results (conversations.jsonl, results_raw.jsonl)
  **When** executed
  **Then** it applies all configured judges (turn + conversation, any type) to each conversation

- **Given** judges complete
  **When** results collected
  **Then** results_judged.jsonl created with one entry per (scenario × variant × judge) combo

- **Given** results_judged.jsonl examined
  **When** checked
  **Then** each line is independent JSONL entry with: scenario_id, variant_id, judge_id, judge_score, judge_reasoning, judge_evidence

**Related Requirements:** FR-C3.1, FR-C3.2, FR-C3.3

---

### Story C4.5: Wire Judge Configuration and Factory for All Judge Types

As a user,
I want any judge type (DeepEval, GEval, bespoke) defined in eval_config.json,
So that judges can be modified without code changes.

**Acceptance Criteria:**

- **Given** eval_config.json includes judges array with judge_type field
  **When** loaded
  **Then** judges parsed with: id, type (turn|conversation), judge_class (deepeval|geval|custom), config_or_name

- **Given** judge_class="deepeval" and judge_name="turn_relevancy"
  **When** executed
  **Then** DeepEvalJudge loaded from registry and applied

- **Given** judge_class="geval" with manual_metric config
  **When** executed
  **Then** GEvalJudge loaded and applied with provided metric definition

- **Given** judge_class="custom" with bespoke_class reference
  **When** executed
  **Then** custom BespokeJudge loaded and applied

- **Given** invalid judge configuration
  **When** loaded
  **Then** JudgeError raised with guidance on supported judge types and examples

**Related Requirements:** FR-C3.3, FR-C3.4

---

## Epic C5: Re-Judge Workflow

**Epic Goal:** Implement fast re-judging of existing conversations without re-execution. Enable users to modify judge definitions and apply them to stored transcripts.

**User Stories:**

### Story C5.1: Implement Re-Judge CLI Command

As a user,
I want `gavel conversational judge --eval <name> --run <timestamp>` to re-judge conversations,
So that I can iterate on judge definitions quickly without re-running scenarios.

**Acceptance Criteria:**

- **Given** previous run completed with results_raw.jsonl and conversations.jsonl
  **When** `gavel conversational judge --eval test_conv --run 20260118-100000` executed
  **Then** JudgeRunnerStep loads conversations and applies judges from current eval_config.json

- **Given** judges have been modified since previous run
  **When** re-judge command executed
  **Then** new judges applied; results_judged.jsonl overwritten with new results

- **Given** re-judge runs
  **When** completed
  **Then** no LLM processor calls made (only judges invoked); execution fast (<5 seconds typical)

- **Given** re-judge completes successfully
  **When** confirmed
  **Then** message displays: "Re-judged [N] conversations with [M] judges in [X]s"

**Related Requirements:** FR-C4.1, NFR-C-P1 (Re-judging <1s per 100 turns)

---

### Story C5.2: Load and Apply Judges to Existing Transcripts

As a developer,
I want JudgeRunnerStep to load results_raw and conversations.jsonl for re-judging,
So that judges can be applied without re-execution.

**Acceptance Criteria:**

- **Given** re-judge workflow initiated
  **When** JudgeRunnerStep executed
  **Then** it loads: conversations.jsonl (full transcripts), results_raw.jsonl (turn-by-turn outputs)

- **Given** conversations loaded
  **When** judges applied
  **Then** for each conversation: all configured judges (turn, conversation, any type) score the transcript

- **Given** new judges applied
  **When** results created
  **Then** results_judged.jsonl written with all new judge results; results_raw.jsonl unchanged

- **Given** re-judge completes
  **When** checked
  **Then** results_raw.jsonl unchanged; results_judged.jsonl completely regenerated

**Related Requirements:** FR-C4.1, FR-C6.3

---

## Epic C6: Conversation Reporting

**Epic Goal:** Generate professional reports with Eval Summary, Performance Summary, per-scenario detail with side-by-side variants, turn-level display, judge scores, and timing metrics.

**User Stories:**

### Story C6.1: Implement Report Structure with Eval Summary and Performance Summary

As a developer,
I want ReportingStep to generate reports with Eval Summary and Performance Summary sections,
So that users can quickly see judge scores and timing metrics across variants.

**Acceptance Criteria:**

- **Given** ReportingStep receives conversational results
  **When** execute() called
  **Then** generates HTML report with sections: Header, Eval Summary, Performance Summary, Scenario Detail

- **Given** Eval Summary section rendered
  **When** viewed
  **Then** displays table with: Variant | Judge Score 1 | Judge Score 2 | ... | Overall Avg (aggregated from results_judged.jsonl)

- **Given** Performance Summary section rendered
  **When** viewed
  **Then** displays table with: Variant | Avg Turn Time | Avg Conversation Time | Total Time (calculated from results_raw.jsonl)

- **Given** report header rendered
  **When** viewed
  **Then** shows: Evaluation name, Run ID, Generated timestamp

- **Given** report generation completes
  **When** saved
  **Then** report.html written to run directory; readable in browser

**Related Requirements:** FR-C5.1

---

### Story C6.2: Implement Scenario Detail Sections with Side-by-Side Variant Comparison

As a developer,
I want scenario detail sections to show side-by-side variant comparison,
So that users can compare how different variants performed on the same scenario.

**Acceptance Criteria:**

- **Given** scenario detail section rendered
  **When** viewed
  **Then** section contains: Scenario header (with initial user message), side-by-side table with one column per variant

- **Given** side-by-side table created
  **When** examined
  **Then** each column header is variant name (e.g., "ai_gateway_claude", "ai_gateway_gemini")

- **Given** variant column populated
  **When** viewed
  **Then** contains full conversation transcript (all turns) for that variant

- **Given** scenario has N variants
  **When** rendered
  **Then** table has N columns for variants (each column same width)

- **Given** template uses CSS for styling
  **When** viewed
  **Then** responsive, professional appearance with clear column separation

**Related Requirements:** FR-C5.1, FR-C5.2

---

### Story C6.3: Implement Turn-Level Display with Duration and Judge Score Badges

**As a** developer,
**I want** turn-level display to show turn text, duration, and judge score badges,
**So that** users can see detailed turn-by-turn performance.

**Acceptance Criteria:**

- **Given** conversation transcript rendered
  **When** viewed
  **Then** each turn displays: role (USER/ASSISTANT), turn text, duration (e.g., "Duration: 3.77s")

- **Given** turn displayed
  **When** examined
  **Then** user turns colored blue (background #e3f2fd, left border #1976d2); assistant turns purple (background #f3e5f5, left border #7b1fa2)

- **Given** judge scores for conversation
  **When** rendered below conversation
  **Then** displays score badges for each judge (e.g., "0.88/10" badge)

- **Given** score badge clicked
  **When** expanded
  **Then** shows: judge name, score, detailed reasoning (expandable/collapsible)

- **Given** long turn text provided
  **When** rendered
  **Then** text can be expanded/collapsed with "expand"/"collapse" button to show preview vs full text

**Related Requirements:** FR-C5.2, FR-C5.3

---

### Story C6.4: Implement Judge Reasoning Display and Insight Summary

**As a** user,
**I want** to see judge reasoning in reports and understand why conversations were scored,
**So that** I get actionable insights on conversation performance.

**Acceptance Criteria:**

- **Given** judge score badge expanded
  **When** examined
  **Then** displays: judge_name, judge_score (formatted like "0.88/10"), judge_reasoning

- **Given** judge reasoning displayed
  **When** viewed
  **Then** reasoning is formatted readable (preserves line breaks, paragraphs, lists); can be styled for readability

- **Given** Eval Summary section viewed
  **When** checked
  **Then** clear indication: which variant(s) had best overall scores; which had lowest

- **Given** multiple judge scores visible
  **When** evaluated
  **Then** users can compare judge opinions across variants (e.g., Variant A scored 0.95 by Judge 1, Variant B scored 0.88)

- **Given** report styling applied
  **When** viewed
  **Then** professional appearance with readable fonts, colors, spacing; responsive on desktop and mobile

**Related Requirements:** FR-C5.3

---

## Epic C7: CLI Integration

**Epic Goal:** Wire Conversational Evaluation into CLI with `gavel conversational` subcommands.

**User Stories:**

### Story C7.1: Implement `gavel conversational create` Scaffolding

As a user,
I want `gavel conversational create --eval <name>` to scaffold evaluations,
So that I can get started quickly.

**Acceptance Criteria:**

- **Given** `gavel conversational create --eval my_conv_eval` executed
  **When** completed
  **Then** directory created: `.gavel/evaluations/my_conv_eval/` with structure:
  - config/ (agents.json, eval_config.json, async_config.json)
  - data/ (scenarios.json, scenarios.csv template)
  - prompts/ (default.toml)
  - runs/ (empty)

- **Given** eval_config.json scaffolded
  **When** examined
  **Then** contains conversational-specific defaults: workflow_type="conversational", max_turns=10, elaboration_enabled=false

- **Given** scenarios.json scaffolded
  **When** examined
  **Then** contains 2-3 example scenarios with user_goal, context, dialogue_guidance filled in

- **Given** scaffolded eval created
  **When** modified by user
  **Then** ready for `gavel conversational run`

**Related Requirements:** FR-C7.1

---

### Story C7.2: Implement `gavel conversational run` Execution

As a user,
I want `gavel conversational run --eval <name>` to execute conversations end-to-end,
So that I can test dialogue systems comprehensively.

**Acceptance Criteria:**

- **Given** `gavel conversational run --eval my_conv_eval` executed
  **When** runs
  **Then** orchestrates: ValidateStep → GenerateStep (optional) → ConversationalProcessingStep → JudgeRunnerStep → ReportingStep

- **Given** execution progresses
  **When** running
  **Then** progress indicators shown: "Executing scenario 3/10 with variant Claude..."

- **Given** run completes successfully
  **When** finished
  **Then** run directory created: `runs/<timestamp>/` with all artifacts

- **Given** invalid config detected
  **When** execution attempted
  **Then** ConfigError raised with clear recovery guidance before execution starts

- **Given** partial failure during execution (one scenario fails)
  **When** error_handling="collect_all"
  **Then** other scenarios continue; failed scenario recorded; run completes with partial results

**Related Requirements:** FR-C7.2

---

### Story C7.3: Implement `gavel conversational judge` Re-judging

As a user,
I want `gavel conversational judge --eval <name> --run <timestamp>` to re-judge,
So that I can iterate on judge definitions without re-running conversations.

**Acceptance Criteria:**

- **Given** previous run exists with results_raw.jsonl
  **When** `gavel conversational judge --eval my_conv_eval --run 20260118-100000` executed
  **Then** JudgeRunnerStep loads conversations and applies current judges from eval_config.json

- **Given** re-judge execution starts
  **When** running
  **Then** progress shown: "Judging conversation N/M..."

- **Given** re-judge completes
  **When** finished
  **Then** results_judged.jsonl overwritten; manifest.json updated with judge history

- **Given** report already exists
  **When** re-judge completes
  **Then** old report.html preserved; new report can be generated

**Related Requirements:** FR-C7.3

---

### Story C7.4: Implement `gavel conversational report` Report Generation

As a user,
I want `gavel conversational report --eval <name> --run <timestamp>` to generate reports,
So that I can view conversation results in human-readable format.

**Acceptance Criteria:**

- **Given** completed run exists with results_judged.jsonl
  **When** `gavel conversational report --eval my_conv_eval --run 20260118-100000` executed
  **Then** ReportingStep generates report.html from Jinja2 template

- **Given** report template specified with `--template custom.html`
  **When** executed
  **Then** custom template used instead of default

- **Given** report generation completes
  **When** verified
  **Then** report.html in run directory; opens successfully in browser

- **Given** report markdown variant requested with `--format markdown`
  **When** executed
  **Then** report.md generated instead of (or in addition to) report.html

**Related Requirements:** FR-C7.4

---

### Story C7.5: Implement `gavel conversational list` Run History

As a user,
I want `gavel conversational list --eval <name>` to show run history,
So that I can track evaluation progress.

**Acceptance Criteria:**

- **Given** `gavel conversational list` executed
  **When** completed
  **Then** displays all conversational runs with: run_id, timestamp, eval_name, scenario_count, variant_count, status

- **Given** multiple eval_names exist
  **When** `gavel conversational list --eval specific_eval` filtered
  **Then** only runs for that evaluation shown

- **Given** runs from different dates
  **When** `gavel conversational list --after 2026-01-15` filtered
  **Then** only runs after that date shown

- **Given** large run history
  **When** displayed
  **Then** pagination or summary format used for readability

**Related Requirements:** FR-C7.5

---

## Epic C8: Testing & Validation

**Epic Goal:** Implement comprehensive unit, integration, and end-to-end tests; achieve 70%+ coverage.

**User Stories:**

### Story C8.1: Unit Tests for TurnGenerator

As a developer,
I want TurnGenerator tested thoroughly,
So that turn generation is deterministic and reliable.

**Acceptance Criteria:**

- **Given** TurnGenerator unit tests exist
  **When** executed
  **Then** all tests pass; coverage >90% on TurnGenerator class

- **Given** same scenario and history provided twice
  **When** generate_turn() called with temperature=0
  **Then** identical turns returned (determinism test)

- **Given** various conversation histories provided
  **When** turns generated
  **Then** turns adapt to history; move toward scenario goal (coherence tests)

- **Given** edge cases (empty history, very long history, circular conversation)
  **When** generate_turn() called
  **Then** graceful handling; no exceptions (robustness tests)

**Related Requirements:** NFR-C-R4 (Determinism), NFR-C-R2 (Robustness)

---

### Story C8.2: Unit Tests for ConversationState Management

As a developer,
I want ConversationState tested for correctness,
So that conversation history is reliable.

**Acceptance Criteria:**

- **Given** ConversationState tests exist
  **When** executed
  **Then** all tests pass; coverage >90%

- **Given** add_turn() called multiple times
  **When** turns examined
  **Then** turn_numbers auto-increment; timestamps recorded; history property formatted correctly

- **Given** conversation with user and assistant turns
  **When** history property accessed
  **Then** formatted string contains alternating user/assistant turns

- **Given** metadata added to turns
  **When** stored and retrieved
  **Then** tokens, latency, other metadata preserved

**Related Requirements:** NFR-C-R1 (Reproducibility)

---

### Story C8.3: Integration Tests for Multi-Turn Execution

As a developer,
I want end-to-end multi-turn conversations tested,
So that ConversationalProcessingStep is reliable.

**Acceptance Criteria:**

- **Given** integration tests exist with mock LLM provider
  **When** executed
  **Then** all tests pass; coverage >70%

- **Given** mock LLM configured to return synthetic responses
  **When** conversation executed with 5 scenarios × 2 variants
  **Then** 10 complete conversations generated; transcripts preserved; results_raw created

- **Given** same scenario/variant executed twice
  **When** results compared
  **Then** identical conversation structure (determinism test with mocks)

- **Given** edge cases (max_turns reached, goal achieved early, error in LLM)
  **When** scenarios tested
  **Then** conversations terminate gracefully; errors handled

**Related Requirements:** FR-C3.2, NFR-C-R1 (Reproducibility)

---

### Story C8.4: Integration Tests for Judge Execution

As a developer,
I want turn-level and conversation-level judges tested,
So that judging is reliable and correct.

**Acceptance Criteria:**

- **Given** judge integration tests exist with mock judges
  **When** executed
  **Then** all tests pass; coverage >70%

- **Given** mock turn judges configured (turn_relevancy, turn_tone)
  **When** applied to conversation
  **Then** each turn scored independently; scores 1-10; reasoning provided

- **Given** mock conversation judges configured
  **When** applied to full transcript
  **Then** conversation scored holistically; score reflects overall quality

- **Given** same conversation judged twice
  **When** results compared
  **Then** identical judge scores (reproducibility)

**Related Requirements:** FR-C3.1, FR-C3.2, NFR-C-R5 (Judge reproducibility)

---

### Story C8.5: Integration Tests for Re-Judge Workflow

As a developer,
I want re-judge workflow tested comprehensively,
So that judge modification is safe and fast.

**Acceptance Criteria:**

- **Given** re-judge tests exist
  **When** executed
  **Then** all tests pass; coverage >80%

- **Given** conversation executed and judged with 2 judges
  **When** additional judge added to config
  **Then** re-judge workflow loads existing transcripts; applies new judges; new results recorded

- **Given** re-judge runs
  **When** completed
  **Then** execution time <1 second per 100 turns (performance verified)

- **Given** original and re-judged results compared
  **When** examined
  **Then** manifest shows judge history; both iterations auditable

**Related Requirements:** FR-C5.1, NFR-C-P1 (Re-judge performance)

---

### Story C8.6: End-to-End Test of Conversational Workflow

As a developer,
I want complete conversational workflow tested end-to-end,
So that all components work together.

**Acceptance Criteria:**

- **Given** end-to-end test exists with mock infrastructure
  **When** executed
  **Then** full workflow tested: create → run → judge → report; all tests pass

- **Given** test scaffolds evaluation, runs scenarios, judges results
  **When** completed
  **Then** all artifacts created: manifest.json, conversations.jsonl, results_raw.jsonl, results_judged.jsonl, report.html

- **Given** report generated from end-to-end test
  **When** examined
  **Then** report contains turn-level detail, conversation summary, correct variant comparison

- **Given** workflow tested with various scenario counts and variant combinations
  **When** executed
  **Then** all combinations work correctly; no regressions

**Related Requirements:** All Conversational FRs, NFRs

---

### Story C8.7: CLI Integration Tests

As a developer,
I want CLI commands tested for usability and correctness,
So that users get reliable commands.

**Acceptance Criteria:**

- **Given** CLI tests exist
  **When** executed
  **Then** all tests pass

- **Given** `gavel conversational create --eval test_name` tested
  **When** invoked
  **Then** evaluation scaffolded correctly; configs generated with correct defaults

- **Given** `gavel conversational run --eval test_name` tested with mock infrastructure
  **When** invoked
  **Then** execution completes; run directory created; all artifacts present

- **Given** `gavel conversational judge --eval test_name --run <timestamp>` tested
  **When** invoked
  **Then** judges reapplied; new results recorded; fast execution verified

- **Given** `gavel conversational report` tested
  **When** invoked
  **Then** reports generated; files created; readable in browser

**Related Requirements:** FR-C7.1, FR-C7.2, FR-C7.3, FR-C7.4, FR-C7.5

---

## Summary Statistics

- **Total Epics:** 8 (Configuration, GenerateStep, Execution, Judging, Re-Judge, Reporting, CLI, Testing)
- **Total Stories:** 34 user stories with detailed acceptance criteria
  - Epic C1: 5 stories
  - Epic C2: 3 stories
  - Epic C3: 5 stories
  - Epic C4: 5 stories (unified judge interface with 3 judge types: DeepEval, GEval, Bespoke)
  - Epic C5: 2 stories (re-judge without history tracking)
  - Epic C6: 4 stories (LoomEval-aligned reporting with variant comparison)
  - Epic C7: 5 stories
  - Epic C8: 7 stories
- **Functional Coverage:** 23 FRs implemented across stories
- **Non-Functional Coverage:** 8 NFRs ensured through architecture decisions
- **Implementation Phases:** 5 phases from foundation to testing
- **Pattern Reuse:** 5 components reused from OneShot (ValidateStep, JudgeRunnerStep, ReportingStep, RunContext, artifact schema)
- **New Components:** 5 components new to gavel-ai (GenerateStep, ConversationalProcessingStep, TurnGenerator, ConversationState, conversations.jsonl)

---

## Next Phase

**Step 02: Design Epics** - Refine epic boundaries, sequence stories by value and dependencies, confirm epic structure with user input.

---

**Document Status: ✅ READY FOR EPIC DESIGN**

**Step Completed:** Requirements extracted, verified, and captured.
