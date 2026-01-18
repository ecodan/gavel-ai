---
stepsCompleted: [1, 2, 3]
inputDocuments:
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/prd-conversational-eval.md
  - docs/.private/TDD-conversational-eval.md
  - docs/.private/schema-configs.md
  - docs/.private/schema-outputs.md
workflowType: 'tdd'
project_name: 'gavel-ai'
workflow: 'Conversational Evaluation (v2)'
date: '2026-01-18'
---

# Technical Design Document - Conversational Evaluation

**gavel-ai v2: Multi-Turn Dialogue Evaluation Architecture**

**Date:** 2026-01-18

---

## Executive Summary

Conversational Evaluation implements gavel-ai's Step abstraction pattern to enable multi-turn dialogue evaluation. Rather than creating a parallel implementation, Conversational reuses ValidateStep, JudgeRunnerStep, and ReportingStep from OneShot while introducing two new steps:

1. **GenerateStep** (optional) — Generates scenarios from prompts describing test requirements
2. **ConversationalProcessingStep** (new, core) — Executes multi-turn conversations with dynamic turn generation

The complete MVP workflow:

```
ValidateStep
  ↓
GenerateStep (optional)
  ↓
ConversationalProcessingStep (new)
  ├→ TurnGenerator (dynamic on-the-fly generation)
  ├→ LLM Execution (variants against scenarios)
  └→ Outputs: conversations.jsonl + results_raw.jsonl
  ↓
JudgeRunnerStep (enhanced for turn + conversation judging)
  ├→ Turn-Level Judges (DeepEval)
  ├→ Conversation-Level Judges (DeepEval)
  └→ Outputs: results_judged.jsonl (flattened schema)
  ↓
ReportingStep (adapted for conversation structure)
  └→ Outputs: report.html (turn detail + conversation summary)
```

**Key Design Decisions:**

1. **Pattern Consistency:** Conversational is a Step instance, not a parallel workflow
2. **On-the-Fly Turn Generation:** Turns generated dynamically during execution (not pre-written)
3. **Flattened Judge Output:** Same schema as OneShot (one record per judge result)
4. **Re-Judge Architecture:** Separate raw transcripts from judged results for independent re-execution
5. **Scenario Generation:** Optional GenerateStep generates scenarios from prompts (not required for basic conversations)

---

## System Architecture

### High-Level Design

```
Conversational Evaluation Workflow (5 Steps)

┌─────────────────────────────────────────────────────────┐
│ 1. ValidateStep (reused from OneShot)                   │
│    - Validate conversational eval config                │
│    - Check scenarios, judge configs, variants          │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ 2. GenerateStep (optional, new)                         │
│    - Generate scenarios from prompts                    │
│    - Input: prompts/generate_scenarios.toml             │
│    - Output: scenarios.jsonl                            │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ 3. ConversationalProcessingStep (new, core)            │
│    ┌─────────────────────────────────────────────────┐ │
│    │ For each scenario × variant:                    │ │
│    │  - Initialize conversation context              │ │
│    │  - TurnGenerator creates first user turn        │ │
│    │  - Loop: LLM response → next user turn          │ │
│    │  - Repeat until conversation ends               │ │
│    │  - Store transcript + results_raw               │ │
│    └─────────────────────────────────────────────────┘ │
│    Output: conversations.jsonl + results_raw.jsonl    │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ 4. JudgeRunnerStep (reused, enhanced)                   │
│    ┌─────────────────────────────────────────────────┐ │
│    │ Turn-Level Judges (DeepEval via schema-configs) │ │
│    │  - Judge each turn: relevancy, tone, accuracy   │ │
│    │  - Aggregated for conversation context          │ │
│    └─────────────────────────────────────────────────┘ │
│    ┌─────────────────────────────────────────────────┐ │
│    │ Conversation-Level Judges (DeepEval)            │ │
│    │  - Judge complete transcript                    │ │
│    │  - Coherence, goal achievement, safety          │ │
│    └─────────────────────────────────────────────────┘ │
│    Output: results_judged.jsonl (flattened)           │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ 5. ReportingStep (reused, adapted for conversations)    │
│    - Generate HTML/Markdown with turn detail           │
│    - Show turn-level scores + conversation summary     │
│    - Answer "How did the conversation go?"             │
│    Output: report.html                                 │
└─────────────────────────────────────────────────────────┘
```

### Step Interface Instantiation

All steps implement the same `Step` abstraction:

```python
class ConversationalProcessingStep(Step):
    """Multi-turn dialogue execution step."""

    async def execute(self, config: ConversationalConfig) -> ConversationalResult:
        """Execute conversational evaluation."""
        pass
```

### Component Relationships

```
ConversationalProcessingStep
  ├→ TurnGenerator (generates user turns dynamically)
  ├→ Executor (runs LLM calls via pydantic-ai)
  ├→ ConversationStateManager (tracks dialogue history)
  └→ ResultCollector (collects transcripts and raw results)

JudgeRunnerStep
  ├→ TurnLevelJudges (judge individual responses)
  ├→ ConversationLevelJudges (judge complete transcripts)
  └→ ResultFormatter (flatten judge results to JSONL)

GenerateStep (optional)
  ├→ ScenarioGenerator (LLM-based scenario creation from prompt)
  └→ ScenarioValidator (validate generated scenarios schema)
```

---

## Core Components

### 1. GenerateStep (Optional Scenario Generation)

**Purpose:** Generate scenarios from a prompt describing test requirements

**Input:** Prompt file (prompts/generate_scenarios.toml)
```toml
v1 = """
Generate realistic customer support scenarios that test chatbot behavior.

Scenarios needed:
- Customer trying to get refund for defective product (frustrated)
- Customer asking about warranty coverage (confused)
- Customer attempting escalation to manager (escalatory)

For each scenario, provide: id, user_goal, context, dialogue_guidance
"""
```

**Output:** scenarios.jsonl (JSONL format, one scenario per line)
```json
{"id": "cs_refund_1", "user_goal": "Get refund for defective product", "context": "Customer purchased 2 weeks ago, item stopped working", "dialogue_guidance": {"tone": "frustrated", "escalation_strategy": "demand manager if not satisfied"}}
{"id": "cs_warranty_1", "user_goal": "Understand warranty coverage", "context": "Unsure if defect is covered", "dialogue_guidance": {"tone": "confused", "escalation_strategy": "ask for clarification"}}
{"id": "cs_escalation_1", "user_goal": "Speak to manager", "context": "Dissatisfied with first response", "dialogue_guidance": {"tone": "escalatory", "escalation_strategy": "insist on manager"}}
```

**Implementation Notes:**
- Optional; users can skip if scenarios.jsonl already exists
- Uses LLM (via Executor) to generate scenarios from prompt
- Prompt template (generate_scenarios.toml) specifies what scenarios to create
- Output stored as scenarios.jsonl for ConversationalProcessingStep input
- Generation is deterministic (temperature=0)

### 2. ConversationalProcessingStep (Core Multi-Turn Execution)

#### 2.1 TurnGenerator Component

**Purpose:** Generate realistic user turns on-the-fly during conversation

**Design Pattern:** On-the-fly generation (NOT pre-written, NOT streaming)

**Input to TurnGenerator:**
- Scenario (user goal, context, dialogue guidance)
- Current conversation history (all prior turns)
- Test_subject (the LLM system being tested)

**Output from TurnGenerator:**
```python
class GeneratedTurn:
    content: str  # The user's next input
    metadata: dict  # Turn metadata (reasoning, guidance applied)
    should_continue: bool  # Whether conversation should continue
```

**Algorithm:**
1. Receive conversation state (all prior turns + LLM responses)
2. Invoke TurnGenerator LLM with prompt:
   ```
   User goal: {scenario.user_goal}
   Dialogue guidance: {scenario.dialogue_guidance}

   Conversation so far:
   {conversation_history}

   Generate the next realistic user input that moves toward the goal.
   ```
3. Parse output to next user turn
4. Determine continuation criteria (goal achieved, max turns reached, conversation naturally ends)
5. Return GeneratedTurn with content, metadata, continuation flag

**Key Properties:**
- **Deterministic:** Same history + scenario = same turn (if temperature=0)
- **Context-Aware:** Turns adapt to conversation history
- **Guidance-Driven:** Dialogue guidance influences turn content
- **Goal-Oriented:** Turns progress toward scenario user_goal

#### 2.2 Conversation Execution Flow

```python
async def execute_conversation(
    scenario: Scenario,
    variant: Variant,
    turn_generator: TurnGenerator,
    executor: Executor,
) -> ConversationResult:
    """Execute single conversation (scenario × variant)."""

    # Initialize conversation state
    conversation = ConversationState()
    results_raw = []

    # Generate first user turn
    user_turn = await turn_generator.generate_turn(
        scenario=scenario,
        history=conversation.history,
    )

    # Multi-turn loop
    while user_turn.should_continue:
        # Append user turn to history
        conversation.add_turn("user", user_turn.content)

        # Get LLM response
        llm_response = await executor.process(
            input=user_turn.content,
            variant=variant,
        )
        conversation.add_turn("assistant", llm_response)

        # Store raw result (one per turn)
        results_raw.append(ProcessorResult(
            test_subject=scenario.id,
            variant_id=variant.id,
            scenario_id=scenario.id,
            processor_output=llm_response,
            # ... timing, tokens, etc
        ))

        # Generate next user turn (with updated history)
        user_turn = await turn_generator.generate_turn(
            scenario=scenario,
            history=conversation.history,  # Updated with LLM response
        )

    return ConversationResult(
        conversation_transcript=conversation,
        results_raw=results_raw,
    )
```

#### 2.3 Conversation State Management

```python
class ConversationState:
    """Manages conversation history and metadata."""

    def __init__(self, scenario_id: str, variant_id: str):
        self.scenario_id = scenario_id
        self.variant_id = variant_id
        self.turns: List[Turn] = []
        self.start_time: datetime = datetime.now()
        self.tokens_total: int = 0
        self.duration_ms: int = 0

    def add_turn(
        self,
        role: Literal["user", "assistant"],
        content: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Append turn to conversation history."""
        turn = Turn(
            role=role,
            content=content,
            turn_number=len(self.turns),
            timestamp=datetime.now(),
            metadata=metadata or {},
        )
        self.turns.append(turn)

    @property
    def history(self) -> str:
        """Return formatted conversation history for turn generator."""
        return "\n".join(f"{turn.role}: {turn.content}" for turn in self.turns)
```

#### 2.4 Output Schema (conversations.jsonl)

Stored as JSON Lines (one entry per scenario × variant):

```json
{
  "scenario_id": "customer_support_1",
  "variant_id": "claude-sonnet-4-5-20250929",
  "conversation": [
    {
      "turn_number": 0,
      "role": "user",
      "content": "Hi, I bought a product two weeks ago and it stopped working. I'd like a refund.",
      "timestamp": "2026-01-18T10:00:00Z"
    },
    {
      "turn_number": 1,
      "role": "assistant",
      "content": "I'm sorry to hear that. Let me help you with that. Can you provide your order number?",
      "timestamp": "2026-01-18T10:00:02Z",
      "metadata": {
        "tokens_prompt": 120,
        "tokens_completion": 25,
        "latency_ms": 1200
      }
    },
    {
      "turn_number": 2,
      "role": "user",
      "content": "It's order #12345. Should be under my account.",
      "timestamp": "2026-01-18T10:00:03Z"
    }
  ],
  "metadata": {
    "total_turns": 8,
    "total_tokens": 1500,
    "duration_ms": 8500,
    "start_time": "2026-01-18T10:00:00Z"
  }
}
```

### 3. Enhanced JudgeRunnerStep

#### 3.1 Turn-Level Judging

**Design:** Judge each turn independently, aggregating scores for conversation context

**Turn Judge Interface:**
```python
class TurnJudge(Judge):
    """Judge individual conversation turns."""

    async def evaluate(
        self,
        turn: Turn,
        conversation: ConversationState,
        scenario: Scenario,
    ) -> JudgeResult:
        """Score single turn in conversation context."""
        # Judge receives: the turn itself, full conversation history, scenario
        # This enables context-aware judging
        pass
```

**Example Turn Judges:**
- `turn_relevancy` — Is this response relevant to the user's input?
- `turn_tone` — Does the tone match the scenario guidance?
- `turn_accuracy` — Is the factual content accurate?
- `turn_completeness` — Does the response address all aspects of the user's input?

**Aggregation:** Turn scores feed into conversation-level summary:
```
Average turn_relevancy score across all turns → Conversation relevancy metric
Average turn_tone scores → Conversation tone consistency
Etc.
```

#### 3.2 Conversation-Level Judging

**Design:** Judge complete transcript holistically

**Conversation Judge Interface:**
```python
class ConversationJudge(Judge):
    """Judge complete conversation transcripts."""

    async def evaluate(
        self,
        conversation: ConversationState,
        scenario: Scenario,
    ) -> JudgeResult:
        """Score complete conversation."""
        # Judge receives: full transcript, scenario
        # Can evaluate end-to-end properties not visible in single turns
        pass
```

**Example Conversation Judges:**
- `conversation_coherence` — Does the conversation flow logically?
- `goal_achievement` — Did the user/agent accomplish the scenario goal?
- `conversation_safety` — Did the conversation maintain safety boundaries?
- `issue_resolution` — Was the customer issue resolved?

#### 3.3 Execution Model

Sequential execution:

```
For each turn in all conversations:
  For each turn-level judge in config:
    Score the turn (with conversation context)
    Store turn_judge result

For each conversation:
  For each conversation-level judge in config:
    Score the conversation
    Store conversation_judge result
```

#### 3.4 Flattened Judge Output Schema (results_judged.jsonl)

Same schema as OneShot—one record per judge result (not nested hierarchies):

```json
{
  "test_subject": "customer_support_system",
  "variant_id": "claude-sonnet-4-5-20250929",
  "scenario_id": "customer_support_1",
  "processor_output": "I'm sorry to hear that. Let me help you...",
  "judges": [
    {
      "judge_id": "turn_relevancy",
      "judge_name": "deepeval.turn_relevancy",
      "judge_score": 9,
      "judge_reasoning": "Response directly addresses customer's refund request",
      "judge_evidence": "Customer asked for refund, assistant offered help",
      "judge_type": "turn",
      "turn_number": 1
    },
    {
      "judge_id": "turn_tone",
      "judge_name": "deepeval.turn_tone",
      "judge_score": 8,
      "judge_reasoning": "Professional and empathetic tone maintained",
      "judge_evidence": "Used 'I'm sorry' and 'let me help', not dismissive",
      "judge_type": "turn",
      "turn_number": 1
    }
  ]
}
```

**Conversation-Level Results:**
```json
{
  "test_subject": "customer_support_system",
  "variant_id": "claude-sonnet-4-5-20250929",
  "scenario_id": "customer_support_1",
  "processor_output": "[Full conversation transcript]",
  "judges": [
    {
      "judge_id": "conversation_coherence",
      "judge_name": "deepeval.conversation_coherence",
      "judge_score": 8,
      "judge_reasoning": "Conversation flows naturally, relevant context maintained",
      "judge_evidence": "Each response builds on prior exchanges without contradictions",
      "judge_type": "conversation"
    },
    {
      "judge_id": "goal_achievement",
      "judge_name": "deepeval.goal_achievement",
      "judge_score": 7,
      "judge_reasoning": "Customer got refund approval, some friction on documentation",
      "judge_evidence": "Customer achieved primary goal but had to provide extra info",
      "judge_type": "conversation"
    }
  ]
}
```

### 4. Re-Judge Architecture

#### 4.1 Two-Artifact Design

**results_raw.jsonl (Immutable):**
- Stores processor outputs (turn-by-turn)
- Created during ConversationalProcessingStep
- Never changes
- Foundation for re-judging

**results_judged.jsonl (Mutable):**
- Stores judge results (applied to raw outputs)
- Created during JudgeRunnerStep
- Regenerated when judges change
- Same schema as results_raw.jsonl + judges array

#### 4.2 Re-Judge Workflow

```
Step 1: User modifies eval_config.json judges
Step 2: Run: gavel conversational judge --eval <name> --run <timestamp>
Step 3: JudgeRunnerStep executed independently:
  - Load conversations.jsonl (full transcripts)
  - Load results_raw.jsonl (turn-by-turn outputs)
  - Apply new judges from config
  - Overwrite results_judged.jsonl with new judge results
Step 4: Run: gavel conversational report --eval <name> --run <timestamp>
Step 5: New report generated with new judge scores
```

**Key Property:** No re-execution of LLM calls; judges reapplied to stored transcripts.

#### 4.3 Judge Tracking

Manifest stores judge history:
```json
{
  "timestamp": "2026-01-18T10:00:00Z",
  "judges": {
    "original": [
      {"id": "turn_relevancy", "name": "deepeval.turn_relevancy"},
      {"id": "conversation_coherence", "name": "deepeval.conversation_coherence"}
    ],
    "modified": [
      {"timestamp": "2026-01-18T10:05:00Z", "judges": [
        {"id": "turn_relevancy", "name": "deepeval.turn_relevancy"},
        {"id": "conversation_coherence", "name": "deepeval.conversation_coherence"},
        {"id": "goal_achievement", "name": "deepeval.goal_achievement"}
      ]}
    ]
  }
}
```

---

## Data Models

### Scenario (Conversational)

```python
from pydantic import BaseModel
from typing import Optional, Dict, Any

class ConversationScenario(BaseModel):
    """Scenario for conversational evaluation."""

    id: str  # Scenario identifier
    user_goal: str  # What the user is trying to accomplish
    context: Optional[str] = None  # Background context
    dialogue_guidance: Optional[Dict[str, Any]] = None  # Hints for turn generator (tone, escalation_strategy, factual_constraints, etc.)
```

### Turn

```python
class Turn(BaseModel):
    """Single conversation turn."""

    turn_number: int  # 0-indexed
    role: Literal["user", "assistant"]
    content: str  # Turn text
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None  # Tokens, latency, etc.
```

### ConversationState

```python
class ConversationState(BaseModel):
    """Active conversation state (in-memory during execution)."""

    scenario_id: str
    variant_id: str
    turns: list[Turn] = []
    start_time: datetime
    metadata: Optional[Dict[str, Any]] = None

    @property
    def history(self) -> str:
        """Formatted history for TurnGenerator input."""
        return "\n".join(f"{turn.role}: {turn.content}" for turn in self.turns)
```

### ConversationResult

```python
class ConversationResult(BaseModel):
    """Result from single conversation execution."""

    scenario_id: str
    variant_id: str
    conversation_transcript: ConversationState
    results_raw: list[ProcessorResult]  # Turn-by-turn outputs
    duration_ms: int
    tokens_total: int
```

### Configuration (eval_config.json extension)

```json
{
  "workflow_type": "conversational",
  "test_subject": "customer_support_system",
  "variants": ["claude-sonnet", "gpt-4"],

  "conversational": {
    "max_turns": 10,
    "max_turn_length": 500,
    "turn_generator": {
      "model": "claude-sonnet",
      "temperature": 0.0,
      "max_tokens": 200
    }
  },

  "judges": [
    {
      "id": "turn_relevancy",
      "type": "turn",
      "deepeval_name": "deepeval.turn_relevancy"
    },
    {
      "id": "conversation_coherence",
      "type": "conversation",
      "deepeval_name": "deepeval.conversation_coherence"
    }
  ]
}
```

---

## Integration with OneShot Patterns

### Shared Components

| Component | OneShot | Conversational | Reuse |
|-----------|---------|----------------|-------|
| ValidateStep | ✅ | ✅ | Reused, config adapted |
| RunContext | ✅ | ✅ | Reused (same artifact structure) |
| JudgeRunnerStep | ✅ | ✅ | Enhanced for turn + conversation judging |
| ReportingStep | ✅ | ✅ | Adapted for conversation structure |
| results_raw.jsonl schema | ✅ | ✅ | Reused (turn-level records) |
| results_judged.jsonl schema | ✅ | ✅ | Reused (flattened judges) |

### New Components

| Component | Purpose | Conversational-Only |
|-----------|---------|-------------------|
| GenerateStep | Scenario generation from prompts | Yes |
| ConversationalProcessingStep | Multi-turn execution | Yes |
| TurnGenerator | Dynamic turn generation | Yes |
| ConversationState | Dialogue state management | Yes |
| conversations.jsonl | Full transcripts | Yes |

### Architecture Consistency

Both OneShot and Conversational follow the same Step abstraction:

```python
# OneShot: Simple 4-step flow
ValidateStep → PromptInputProcessor → JudgeRunnerStep → ReportingStep

# Conversational: Extended 5-step flow (same pattern, more steps)
ValidateStep → GenerateStep → ConversationalProcessingStep → JudgeRunnerStep → ReportingStep
```

Both reuse ValidateStep, JudgeRunnerStep, ReportingStep—only middle section differs.

---

## Telemetry & Observability

### Span Hierarchy for Conversations

```
RUN_TRACE_ID (per evaluation run)
├── conversation.execute (scenario_id, variant_id)
│   ├── turn.generate (turn_number)
│   │   └── llm.call (turn generator model)
│   └── llm.call (test_subject model)
├── conversation.judge (scenario_id, variant_id)
│   ├── turn.judge (turn_number, judge_id)
│   │   └── llm.call (judge model)
│   └── conversation.judge (judge_id)
│       └── llm.call (judge model)
└── report.generate
```

### Standard Telemetry Attributes (Conversations)

```json
{
  "run_id": "run-20260118-100000",
  "trace_id": "trace-abc123",
  "scenario.id": "customer_support_1",
  "variant.id": "claude-sonnet-4-5-20250929",
  "turn.number": 2,
  "conversation.total_turns": 8,
  "processor.type": "conversation",
  "judge.id": "turn_relevancy",
  "judge.type": "turn",
  "llm.provider": "anthropic",
  "llm.model": "claude-3.5-sonnet",
  "llm.tokens.prompt": 150,
  "llm.tokens.completion": 50,
  "duration_ms": 1200
}
```

---

## Performance Considerations

### Execution Timeline

- Turn generation: ~0.5-1.5s per turn (LLM call)
- LLM response: ~1-3s per turn (depends on model)
- Judge execution: ~0.5-1s per judge per result
- Typical conversation: 5-10 turns = 10-50 LLM calls = 30-120 seconds per scenario

### Optimization Strategies

1. **Parallel Scenario × Variant Execution:** Multiple conversations run in parallel
2. **Sequential Turns:** Turns within single conversation sequential (required for history)
3. **Batch Judging:** Multiple judge evaluations in parallel across results
4. **Re-Judge Efficiency:** No LLM calls needed for re-judging (seconds not minutes)

### Memory Profile

- Per-conversation memory: ~100KB-1MB (depending on transcript length)
- Parallel conversations: 10-100 in-flight = 1-100MB total
- Target: <500MB for typical evaluation

---

## Error Handling & Edge Cases

### Turn Generation Failures

**Case:** TurnGenerator fails to produce next turn
- **Handling:** Log error, mark conversation as incomplete
- **Recovery:** User can retry with different guidance or temperature settings

**Case:** TurnGenerator produces nonsensical turn
- **Handling:** Continue conversation (allows evaluation of model's handling of nonsense)
- **Recovery:** Manual intervention not in MVP; handled in future versions

### Conversation Termination

**Natural ending:** User goal achieved or conversation naturally concludes
- TurnGenerator sets `should_continue=False`
- Conversation recorded as complete

**Timeout:** Conversation exceeds max_turns or max_duration
- ConversationalProcessingStep terminates loop
- Partial conversation recorded

**LLM Failure:** Model unable to respond
- Retry logic (configurable)
- If persistent, mark conversation as failed
- Continue with other scenario × variant combos

---

## Configuration Schema

### Conversational eval_config.json

```json
{
  "workflow_type": "conversational",

  "test_subject": "chatbot_system",
  "variants": ["claude-sonnet", "gpt-4-turbo", "gemini-2"],

  "conversational": {
    "turn_limit": 10,
    "max_turn_length": 500,
    "elaboration_enabled": true,
    "turn_generator": {
      "model": "claude-sonnet",
      "temperature": 0,
      "max_tokens": 200
    }
  },

  "scenarios": "data/scenarios.json",
  "judges": [
    {
      "id": "turn_relevancy",
      "type": "turn",
      "deepeval_name": "deepeval.turn_relevancy"
    },
    {
      "id": "conversation_goal_achievement",
      "type": "conversation",
      "config_ref": "config/judges/goal_achievement.json"
    }
  ]
}
```

---

## Implementation Roadmap

### Phase 1: Foundation (Blocking)

1. Create config schema for conversational scenarios
2. Implement ConversationState and Turn models
3. Implement GenerateStep skeleton (prompt-based scenario generation)

### Phase 2: Core Execution (Core Feature)

4. Implement TurnGenerator component
5. Implement ConversationalProcessingStep
6. Integration with Executor and Pydantic-AI
7. Output conversations.jsonl + results_raw.jsonl

### Phase 3: Judging (Enhancement)

8. Enhance JudgeRunnerStep for turn-level judges
9. Implement conversation-level judge support
10. Flatten judge output schema (same as OneShot)

### Phase 4: Re-Judge & Reporting (Iteration)

11. Implement re-judge workflow (`gavel conversational judge`)
12. Adapt ReportingStep for conversation structure
13. Generate conversation reports (turn detail + summary)

### Phase 5: Testing & Polish

14. Integration tests for multi-turn workflows
15. Mock turn generator and LLM provider
16. CLI integration (`gavel conversational` subcommands)

---

## Design Principles

### 1. Pattern Consistency

Conversational is a Step instance, not a parallel workflow. It reuses the same abstractions as OneShot.

### 2. On-the-Fly Generation

Turns are generated reactively during conversation, not pre-written. This enables:
- Adaptive branching based on model responses
- Realistic dialogue paths
- Deterministic reproducibility (same history = same turn)

### 3. Flattened Artifact Schema

Judge results use flat JSONL (one record per judge), not hierarchical nesting. This enables:
- Simple re-judging (delete results_judged, re-run judges)
- Consistent schema across workflows
- Easy parsing and analysis

### 4. Configuration-Driven

All judges, scenarios, and dialogue guidance defined declaratively in config files. No hardcoded logic.

### 5. Reproducibility

Conversations are deterministic (same scenario + history = same turns, same judge scores).

---

## Security Considerations

### Credential Protection

- Turn generator and judges receive no API credentials directly
- All API calls proxied through Executor (credential handling centralized)
- Conversation transcripts stored without credentials

### Data Confidentiality

- Conversation transcripts stored locally
- No automatic transmission to external services
- User controls export/sharing

### Content Safety

- Turn generator and judges don't bypass safety guidelines
- Scenarios can test safety, but framework doesn't weaken protections
- Model's safety guardrails applied at LLM layer, not overridden by framework

---

## Testing Strategy

### Unit Tests

- TurnGenerator: determinism, edge cases
- ConversationState: turn management, history formatting
- Judge interfaces: turn-level and conversation-level judging
- Configuration: schema validation, edge cases

### Integration Tests

- End-to-end multi-turn conversation execution
- Variant comparison (same scenario, different models)
- Judge aggregation (turn scores → conversation summary)
- Re-judge workflow (modify judges, verify results)

### Mock Infrastructure

- Mock TurnGenerator: returns predefined turns for testing
- Mock LLM provider: returns synthetic responses
- Mock judges: return synthetic scores

---

## Appendix: Example Scenario Generation

### Generation Prompt (Input to GenerateStep)

```toml
v1 = """
Generate price negotiation scenarios for testing procurement agent behavior.

Scenarios needed:
1. Buyer negotiating bulk order discount (professional, persistent)
2. Supplier counter-offering with value-adds (relationship-focused)
3. Multi-round negotiation with walking-away threat (escalatory)

For each scenario, provide: id, user_goal, context, dialogue_guidance

Include tone, escalation_strategy, and factual_constraints in dialogue_guidance.
"""
```

### Generated Scenarios (Output from GenerateStep - scenarios.jsonl)

```json
{"id": "negotiation_bulk_1", "user_goal": "Negotiate price down by 10% for bulk order", "context": "Buyer seeking 100-unit order, supplier's standard price $100/unit", "dialogue_guidance": {"tone": "professional, flexible", "escalation_strategy": "start reasonable, gradually increase pressure", "facts": ["Bulk rate available at 5% for 50+ units", "New customer discount possible"]}}

{"id": "negotiation_valueadd_1", "user_goal": "Lock in supplier for long-term relationship", "context": "Multiple suppliers bidding, value matters beyond price", "dialogue_guidance": {"tone": "collaborative", "escalation_strategy": "emphasize partnership benefits", "facts": ["Can offer 2-year contract", "Include priority support"]}}

{"id": "negotiation_walkaway_1", "user_goal": "Force supplier to match competitor pricing", "context": "Competing supplier offered better terms", "dialogue_guidance": {"tone": "escalatory", "escalation_strategy": "threaten to walk away to competitor", "facts": ["Competitor quoted $85/unit", "Decision deadline Friday"]}}
```

### Sample Conversation Execution

```
Turn 0 (User): "Hi, we're interested in ordering 100 units of your product. What's your bulk pricing?"

Turn 1 (Assistant): "Hello! For 100 units, I'd recommend our bulk rate. Let me check our current pricing... For that volume, we can offer $95 per unit."

Turn 2 (User): "That's competitive, but we're comparing with other suppliers. What if we committed to 200 units over the year?"

Turn 3 (Assistant): "That's an excellent point. For a 12-month commitment, we could look at $92 per unit and include free shipping."

Turn 4 (User): "Getting closer. Our budget target is $90 per unit. Can you work with that?"

Turn 5 (Assistant): "I appreciate you sharing your target. At $90, our margin gets tight, but given the volume and commitment, let me propose $91 per unit as a middle ground, plus priority support."

Turn 6 (User): "That works for us. Let's move forward with that pricing."

Turn 7 (Assistant): "Excellent! I'll prepare a proposal at $91/unit for 100 units with the commitment structure we discussed."
```

### Judge Results

**Turn-Level Judges:**
```
Turn 2: relevancy=9, tone=8, professionalism=9
Turn 4: relevancy=8, tone=7, negotiation_skill=7
Turn 6: relevancy=10, tone=9, goal_achievement=10
```

**Conversation-Level Judges:**
```
negotiation_coherence: 9 (natural progression, clear reasoning)
goal_achievement: 8 (user achieved price reduction to $91, slightly above $90 target)
supplier_professionalism: 9 (maintained professional tone, offered value-adds)
```

---

## Conclusion

Conversational Evaluation extends gavel-ai's Step-based architecture to enable realistic multi-turn dialogue testing. By reusing ValidateStep, JudgeRunnerStep, and ReportingStep while introducing GenerateStep and ConversationalProcessingStep, Conversational maintains architectural consistency and achieves a pattern-driven, extensible design.

The on-the-fly turn generation model enables adaptive, reproducible multi-turn scenarios. The flattened judge output schema and re-judge architecture enable fast iteration on evaluation logic. Together, these design decisions position Conversational as a powerful multi-turn evaluation capability within gavel-ai's framework.

---

**Document Status: ✅ READY FOR IMPLEMENTATION**

**Approval:** Technical decisions locked, component designs specified, data models defined, integration patterns established.
