---
stepsCompleted: [1, 2, 3]
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
  - docs/.private/PRP-conversational-eval.md
  - docs/.private/TDD-conversational-eval.md
  - docs/.private/claude-conv-plan.md
workflowType: 'prd'
project_name: 'gavel-ai'
workflow: 'Conversational Evaluation (v2)'
date: '2026-01-18'
---

# Product Requirements Document - Conversational Evaluation

**gavel-ai v2 Feature: Multi-Turn Dialogue Evaluation**

**Date:** 2026-01-18

## Executive Summary

**Conversational Evaluation** extends gavel-ai's evaluation framework to assess LLM behavior in realistic multi-turn dialogue contexts. Rather than evaluating isolated prompt-response pairs, Conversational enables testing how models perform across sustained conversations with context-aware user interactions, interruptions, and complex scenarios.

Conversational Evaluation follows gavel-ai's established pattern-based architecture, building on the same Step abstraction and reusable components as OneShot. Users evaluate dialogue-based systems by:

1. **Creating rich scenarios** — Defining user goals, personalities, and dialogue context (optional elaboration via GenerateStep)
2. **Simulating realistic conversations** — Multi-turn exchanges where user inputs are generated on-the-fly based on dialogue history and scenario guidance
3. **Judging at both turn and conversation levels** — Assessing individual turn quality and overall dialogue coherence
4. **Re-judging as needed** — Modifying judges declaratively without re-running expensive conversations

### What Makes Conversational Special

- **On-the-Fly Turn Generation** — User inputs generated dynamically during conversation (not pre-written), enabling realistic branching and adaptive scenarios
- **Scenario Generation** — Optional GenerateStep generates scenarios from prompts describing test requirements
- **Turn-Level Judging** — Judge individual responses in context (e.g., "turn_relevancy", "turn_tone")
- **Conversation-Level Judging** — Judge overall dialogue quality (e.g., "conversation_coherence", "goal_achievement")
- **Pattern Consistency** — Uses same Step abstraction, config schema, and artifact patterns as OneShot (DRY architecture)
- **Complete Reproducibility** — Same scenario configuration + judges = identical conversation structure and judge results

---

## Project Classification

**Feature Type:** Multi-Turn Evaluation Workflow (v2)
**Domain:** AI Dialogue Testing (Chatbots, conversational agents, multi-turn systems)
**Complexity:** Medium (extends existing OneShot patterns with dialogue state management)
**Context:** Natural extension of OneShot within gavel-ai's phase-driven roadmap

---

## Success Criteria

### User Success

A developer using Conversational Evaluation achieves success when they can:

1. **Evaluate dialogue systems confidently** — Assess LLM behavior across realistic multi-turn conversations with clear metrics
2. **Create realistic test scenarios** — Define user goals and dialogue context; optionally elaborate with personas and edge cases
3. **Interpret conversation-level results** — Understand both turn-by-turn performance and overall dialogue quality through clear reports
4. **Iterate on dialogue behavior** — Change judges and re-evaluate without re-running conversations (fast iteration on evaluation logic)

### Technical Success

gavel-ai v2 Conversational Evaluation is successful when:

1. **Multi-Turn Execution Robust** — Conversations execute reliably with consistent turn generation, complete context tracking
2. **On-the-Fly Generation Working** — User turns generated dynamically based on scenario guidance + conversation history
3. **Scenario Generation Optional** — GenerateStep generates scenarios from prompts; users can skip if scenarios already exist
4. **Turn and Conversation Judging Complete** — Both turn-level and conversation-level judges working via 100% declarative config
5. **Re-Judge Workflow Functional** — Modify judges, re-judge existing conversations (no re-execution needed)
6. **Pattern Consistency Maintained** — Conversational follows same Step-based architecture as OneShot

### Measurable Outcomes

- Developers can create and run first Conversational eval in ~20 minutes (from install to results)
- Multi-turn conversations execute reliably with deterministic turn generation
- Turn-level and conversation-level judges working independently
- Re-judge CLI commands (`gavel conversational judge`, `gavel conversational report`) functional
- Conversation reports show both turn-level detail and conversation-level summary
- Test coverage at or above 70% on non-trivial code paths

---

## Product Scope

### MVP - Conversational Evaluation v2

**Core Deliverables:**

- **ValidateStep** (reused from OneShot) — Validates conversational eval configuration
- **GenerateStep** (new, optional) — Generates scenarios from prompts describing test requirements
- **ConversationalProcessingStep** (new, core) — Multi-turn dialogue execution with on-the-fly turn generation
- **JudgeRunnerStep** (reused, enhanced) — 100% declarative turn-level and conversation-level judging
- **ReportingStep** (reused) — HTML/Markdown reports showing turn-level detail + conversation summary
- **CLI support** — `gavel conversational create|run|judge|report|list|milestone`
- **Flattened judge output schema** — Same as OneShot (one record per judge result, no nesting)
- **Re-Judge capability** — Modify judges, re-judge existing conversations without re-execution

**Quality Gates:**

- Turn generation reproducible (same scenario + history = same turn)
- Judge results reproducible (same turn output + judges = same scores)
- Complete conversation transcripts preserved for analysis
- Conversation reports answer "How well did the conversation go?" clearly
- 70%+ unit test coverage on non-trivial code

### Growth Features (Post-MVP / v3+)

**v3: Autotune Workflow**
- Iterative prompt optimization using conversational evaluation
- Multi-turn conversational improvements tracked over optimization passes
- Metric convergence monitoring

**Post-v3 Enhancements:**
- Personality-driven turn generation (distinct user archetypes)
- Manual turn branching (explore "what if" paths)
- Interactive replay and debugging UI
- Memory and context window management analytics

---

## User Journeys

### Journey 1: Chatbot Behavior Testing

**Alex** is an AI product manager at a customer support automation company. They've deployed a multi-turn chatbot but are unsure how well it handles real customer conversations, especially when customers ask follow-up questions or deviate from expected paths.

Using Conversational Evaluation, Alex creates realistic customer service scenarios (frustrated customer, tech-challenged user, security-conscious user) and runs conversations between gavel-ai's turn generator and their deployed chatbot. Within 30 minutes, Alex sees conversation-level reports showing how well the chatbot maintained tone, addressed follow-up questions, and resolved customer issues.

When judges need tweaking, Alex modifies the eval config and re-judges existing conversations in seconds—no waiting for new API calls. This fast iteration helps Alex confidently optimize the chatbot before rolling out updates.

**Requirements Revealed:** Multi-turn conversation support, on-the-fly user simulation, conversation-level reporting, fast re-judging capability.

---

### Journey 2: Comparing Dialogue Models

**Sam** is a research engineer comparing Claude, GPT-4, and Gemini on a complex dialogue task (negotiation simulation). They need to evaluate not just individual responses but how each model sustains the negotiation over multiple turns.

Using Conversational Evaluation, Sam configures the same negotiation scenario with all three models and runs identical conversations (same user moves, same dialogue context). The conversation reports show which model negotiates most effectively—Claude wins on empathy, GPT-4 on detail, Gemini somewhere in between.

When Sam wants to adjust "empathy" judge criteria, they don't re-run the expensive conversations; they modify judges and re-execute judgment on the transcripts. This enables rapid hypothesis testing on dialogue evaluation.

**Requirements Revealed:** Multi-variant dialogue testing, consistent conversation structure across variants, turn-level and conversation-level comparison, re-judge efficiency.

---

### Journey 3: Safety Testing Multi-Turn Behavior

**Priya** is an AI safety researcher testing whether a language model's harmful behavior manifests differently across multi-turn conversations. She's concerned that safety guardrails might fail progressively or when the user "jailbreaks" gradually.

Using Conversational Evaluation, Priya creates scenarios where a user gradually escalates requests (starting innocent, becoming progressively problematic). Each scenario tests whether the model maintains safety boundaries across the dialogue.

Priya's judges look at turn-level safety ("Did this turn violate policy?") and conversation-level trends ("Did the model's refusals weaken over the conversation?"). When Priya refines her safety definitions, she re-judges all conversations in seconds.

The conversation reports provide audit trails showing exactly where safety violations occurred and whether boundaries held or eroded.

**Requirements Revealed:** Scenario progression capabilities, turn-level safety assessment, conversation-level trend analysis, complete audit trails for safety review.

---

### Journey 4: Evaluating Agent Reasoning Across Turns

**Jordan** is building an AI agent that solves complex multi-step problems through dialogue. They need to evaluate whether the agent reasons consistently across turns and whether it corrects course when given feedback.

Using Conversational Evaluation, Jordan creates problem-solving scenarios where an "expert evaluator" role (via scenario guidance) asks probing questions and corrects the agent when it goes astray. Jordan then runs conversations and judges:
- **Turn-level:** Does each response address the question? Does the agent accept feedback?
- **Conversation-level:** Did the agent solve the problem? Did reasoning stay consistent?

Jordan's re-judge workflow lets them iterate on evaluation logic: "Actually, I should reward self-correction more." Jordan modifies judges, re-judges, and quickly sees impact on conversation-level scores.

**Requirements Revealed:** Multi-role dialogue (agent + evaluator), turn-level behavior assessment, conversation-level reasoning evaluation, quick iteration on judgment logic.

---

### Journey Requirements Summary

| User Type | Key Requirements |
|-----------|-----------------|
| **Product Manager** | Multi-turn testing, realistic user simulation, conversation-level reports |
| **Researcher** | Scenario consistency, variant comparison, turn and conversation judging, re-judge speed |
| **Safety Engineer** | Safety progression scenarios, turn-level guardrails, conversation trend analysis, audit trails |
| **Agent Developer** | Multi-role dialogues, reasoning assessment, self-correction tracking, fast iteration |

---

## Feature Requirements

### 1. Scenario & Elaboration

**FR-C1.1:** Users can define conversational scenarios with user goal, context, and optional guidance

- Scenario schema: `id`, `user_goal` (required), `context` (optional), `dialogue_guidance` (optional)
- User goal: What the simulated user is trying to accomplish ("resolve refund issue", "explain quantum computing")
- Context: Background information (customer account, conversation history, domain knowledge)
- Dialogue guidance: Optional hints for turn generator (tone preference, escalation strategy, factual constraints)
- Users create scenarios.json or import via CSV
- **Traces to:** Journey 1, 3, 4 (scenario definition)

**FR-C1.2:** GenerateStep generates scenarios from prompts (optional in MVP)

- GenerateStep invoked via `gavel conversational generate --eval <name>`
- Takes input prompt (prompts/generate_scenarios.toml) describing test scenarios to create
- Generates scenarios.jsonl with LLM-created scenarios (id, user_goal, context, dialogue_guidance)
- Generation optional—users can skip and provide scenarios.jsonl manually
- Generated scenarios stored as input to ConversationalProcessingStep
- **Traces to:** Journey 1, 3 (scenario enrichment)

### 2. Multi-Turn Conversation Execution

**FR-C2.1:** Users can execute multi-turn conversations locally or in-situ

- `gavel conversational run --eval <name>` executes conversations
- Each scenario × variant combination produces one conversation transcript
- Conversations execute reliably with deterministic turn ordering
- **Traces to:** Journey 1, 2 (multi-turn execution)

**FR-C2.2:** Turn generation is on-the-fly based on scenario guidance and conversation history

- TurnGenerator creates user inputs dynamically during conversation
- Each turn generated based on: current conversation state, scenario guidance (user_goal + dialogue_guidance), prior outputs
- NOT pre-written turns; NOT streaming generation—purely reactive based on history
- Turn generation deterministic (same history + scenario = same turn)
- **Traces to:** Journey 1 (realistic user simulation), all journeys (conversation coherence)

**FR-C2.3:** Complete conversation transcripts are captured and preserved

- Each conversation includes: all user turns, all LLM responses, turn metadata (timing, tokens)
- Transcripts stored as JSON in run artifacts for analysis and replay
- Full context available for judging and reporting
- **Traces to:** Journey 3, 4 (audit trails, reasoning assessment)

**FR-C2.4:** Users can run multi-turn conversations against multiple variants (models, prompts, endpoints)

- Same scenario executed with all configured variants (Claude, GPT, Gemini, etc.)
- Identical turn sequence for each variant (same user inputs across all models)
- Variant comparison enabled at conversation level
- **Traces to:** Journey 2 (model comparison)

### 3. Turn-Level & Conversation-Level Judging

**FR-C3.1:** Turn-level judges assess individual responses in dialogue context

- Judge each response independently: "Is this turn relevant?", "Is the tone appropriate?"
- DeepEval turn-level judges available (via schema-configs.md)
- Custom GEval judges can define turn-level criteria
- Turn scores aggregated to inform conversation-level assessment
- **Traces to:** Journey 2, 3, 4 (turn-level evaluation)

**FR-C3.2:** Conversation-level judges assess overall dialogue quality

- Judges evaluate complete conversation: "Did the agent solve the problem?", "Did the model maintain safety?"
- Conversation-level judges receive full transcript for holistic assessment
- Separate from turn-level judges; can be configured independently
- **Traces to:** Journey 1, 4 (conversation outcome)

**FR-C3.3:** Both turn-level and conversation-level judges are 100% declarative via config

- All judges defined in eval_config.json or referenced judge config files
- Judge selection: predefined DeepEval or custom GEval
- No hardcoded judge logic; pure config-driven
- Judges configured once, reusable across all runs
- **Traces to:** All journeys (configuration repeatability)

**FR-C3.4:** Judge execution is reproducible

- Same conversation transcript + judges = identical judge results (deterministic)
- Judge output stored with conversation metadata
- Re-judging workflow enabled (modify judges, recompute on same transcripts)
- **Traces to:** All journeys (iteration, audit)

### 4. Re-Judge Workflow

**FR-C4.1:** Users can re-judge existing conversations without re-execution

- `gavel conversational judge --eval <name> --run <timestamp>` re-judges a specific run
- No API calls needed; judges recomputed from stored transcripts
- Fast iteration on evaluation logic (seconds vs minutes)
- **Traces to:** Journey 1, 2, 3 (iteration speed)

**FR-C4.2:** Judge changes are tracked and reportable

- Modified judges generate new judge results (appended to output_judged.jsonl)
- Original judge results preserved in immutable output_raw.jsonl
- Reports can compare judge iterations: "How did conversation scores change when we adjusted criteria?"
- **Traces to:** Journey 2, 4 (evaluation evolution tracking)

### 5. Conversation Reporting

**FR-C5.1:** Conversation reports follow conversational structure

- **Title:** Experiment name
- **Overview:** Variants tested, scenarios used, sample conversation structure
- **Summary:** Table showing conversation-level scores per variant
- **Detail:** One section per scenario; full conversation transcript (expandable) with turn-level scores and conversation-level scores below
- Report filename: `report.html` in run directory
- **Traces to:** Journey 1, 2 (result presentation)

**FR-C5.2:** Turn-level judge reasoning is visible and inspectable

- Each turn shows: turn text, turn-level judge scores, judge reasoning (expandable)
- Aggregated turn scores contribute to conversation-level view
- Readers can drill down from conversation summary → individual turns → judge reasoning
- **Traces to:** Journey 3, 4 (detailed analysis)

**FR-C5.3:** Reports answer "How did the conversation go?" clearly

- Prominent indication: Which variant(s) had best conversation-level scores
- Trade-off analysis: Where one variant excelled vs struggled
- Conversation arc: Did scores improve, degrade, or stabilize over turns?
- Actionable interpretation: What conversation patterns drove scores
- **Traces to:** Journey 1, 2 (decision making)

### 6. Data Artifacts & Reproducibility

**FR-C6.1:** Conversational runs follow same artifact structure as OneShot

- Run directory: `runs/<timestamp>/`
- Artifacts: `manifest.json`, `config/`, `telemetry.jsonl`, `results_raw.jsonl`, `results_judged.jsonl`, `run_metadata.json`, `report.html`
- Same result schema as OneShot (turn-level results stored in `results_raw.jsonl`, judges applied to produce `results_judged.jsonl`)
- **Traces to:** Architecture consistency, Journey (audit trail)

**FR-C6.2:** Conversation transcripts preserved in run artifacts

- Full conversation transcripts stored in `conversations.jsonl` (one entry per scenario × variant)
- Transcript includes: complete turn history, timing, tokens, metadata
- Available for analysis, replay, or re-judging
- **Traces to:** Journey 3, 4 (audit, debugging)

**FR-C6.3:** Re-Judging preserves original judge results

- `results_raw.jsonl` immutable (records turn execution)
- `results_judged.jsonl` mutable (regenerated when judges change)
- Original judges preserved in manifest; new judges tracked
- Enables historical comparison: "How did scores change when we updated judge criteria?"
- **Traces to:** Journey 2, 4 (iteration tracking)

### 7. CLI Interface

**FR-C7.1:** `gavel conversational create` scaffolds conversational evaluations

- `gavel conversational create --eval <name>` generates config directories
- Same structure as OneShot but with conversational-specific defaults
- Generates: config/, data/, prompts/, runs/ directories with templates
- **Traces to:** Usability, 15-minute onboarding

**FR-C7.2:** `gavel conversational run` executes conversations

- `gavel conversational run --eval <name> [--scenarios X-Y]`
- Runs all scenarios against all variants
- Produces conversation transcripts and raw results
- Progress indicators during execution
- **Traces to:** Journey 1, 2 (execution)

**FR-C7.3:** `gavel conversational judge` applies judges to existing conversations

- `gavel conversational judge --eval <name> --run <timestamp>` re-judges
- Fast, no API calls
- Can selectively update judges
- **Traces to:** Journey 1, 2 (iteration)

**FR-C7.4:** `gavel conversational report` generates reports

- `gavel conversational report --eval <name> --run <timestamp>` generates HTML/Markdown
- Re-generate with custom templates
- Supports filtering and formatting options
- **Traces to:** Journey 1, 2 (reporting)

**FR-C7.5:** `gavel conversational list` displays run history

- Shows all completed conversational runs with timestamps, statuses
- Filters by eval name, date range
- Traces to: Journey (run management)

---

## Non-Functional Requirements

### Performance

**NFR-C-P1: Realistic conversation timelines**
- Turn generation: <1 second per turn (LLM call + user input generation)
- Typical conversation: 5-10 turns × 2-3 variants = ~15 turns total = 15-30 seconds execution
- Example: 10 scenarios × 3 variants × 5 turns average = 150 LLM calls = 5-15 minutes
- Report generation: <5 seconds for typical conversation eval
- Re-judging: <1 second per 100 turns (no LLM calls)

**NFR-C-P2: Parallel execution within conversations**
- Multiple conversations (scenario × variant combos) execute in parallel
- Turns within single conversation are sequential (needed for realistic dialogue history)
- Support for configurable parallelism level

### Reliability

**NFR-C-R1: Reproducible conversation execution**
- Same scenario + context + random seed = identical turn sequence
- Failed conversations provide clear error messages and recovery paths
- Partial run recovery: resume interrupted runs without re-executing completed scenarios

**NFR-C-R2: Robust turn generation**
- Turn generation handles edge cases gracefully (circular conversation, topic drift)
- Timeout handling for long turns
- Clear error messages when turn generation fails

**NFR-C-R3: Data integrity**
- Complete conversation transcripts written durably
- Judge results stored immutably in results_raw.jsonl
- No partial or corrupted artifacts

### Reproducibility & Auditability

**NFR-C-R4: Turn generation reproducible**
- Same scenario + conversation history = identical next turn
- Deterministic (no randomness in turn selection logic)

**NFR-C-R5: Judge results reproducible**
- Same transcript + judges = identical judge results
- Audit trail of judge changes via manifest tracking

---

## Constraints & Considerations

### MVP Scope Boundaries (Silent)

**In MVP:**
- On-the-fly turn generation (reactive, based on conversation history)
- Turn-level and conversation-level judging
- Re-judge workflow
- Pattern reuse (GenerateStep, JudgeRunnerStep, ReportingStep)
- Scenario generation (optional, not required)

**Not in MVP:**
- Manual turn editing or branching
- Personality-driven turn generation
- Interactive replay or debugging UI
- Memory management or context window optimization
- Performance analytics

---

## Success Metrics

### Adoption Metrics

- Developers create first conversational eval in <20 minutes
- Conversational eval execution reliable (>98% success rate)
- Re-judge workflow fast (<5 seconds typical)

### Quality Metrics

- Conversation reproducibility: 100% (same scenario = same turns)
- Judge reproducibility: 100% (same transcript + judges = same scores)
- Turn generation success rate: >95% (handles edge cases gracefully)

### Coverage Metrics

- Test coverage: 70%+ on non-trivial code paths
- All user journeys testable via integration tests
- All turn-level and conversation-level judges functional

---

## Implementation Sequence

1. **Setup & Configuration** — Support conversational config schema (scenario generation, dialogue guidance)
2. **GenerateStep** — Scenario generation from prompts (optional enhancement)
3. **ConversationalProcessingStep** — Multi-turn dialogue execution + on-the-fly TurnGenerator
4. **JudgeRunnerStep Enhancement** — Turn-level and conversation-level judging
5. **Reporting** — Conversation report templates with turn-level detail
6. **Re-Judge Workflow** — Judge modification + re-judging on stored transcripts
7. **CLI Integration** — `gavel conversational` subcommands
8. **Testing & Validation** — Unit and integration tests

---

## Alignment with gavel-ai Vision

**Pattern Consistency:**
Conversational Evaluation is NOT a separate implementation—it's a new instance of gavel-ai's Step abstraction pattern. By reusing ValidateStep, JudgeRunnerStep, and ReportingStep, Conversational achieves:
- **DRY Architecture:** One judge system, one artifact schema, one report structure for all workflows
- **Extensibility:** Future workflows (Autotune, etc.) reuse same patterns
- **Maintainability:** Bugs fixed in shared components benefit all workflows

**Vision Enablement:**
Conversational enables gavel-ai's three-workflow vision (OneShot → Conversational → Autotune), positioning the framework as complete multi-workflow evaluation platform.

---

## Next Phase

**Implementation:** Detailed technical specification in TDD-Conversational-Eval-gavel-ai.md

**Epics & Stories:** Break down into user stories with acceptance criteria for sprint planning and implementation

---

**Document Status: ✅ READY FOR IMPLEMENTATION**

**Approval:** Architectural decisions locked, user journeys defined, feature requirements specified.
