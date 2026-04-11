---
title: Unified Reporting Specification
status: draft
author: Analyst Agent
date: 2026-01-20
---

# Unified Evaluation Report Specification

## 1. Overview
This specification defines the unified reporting format for `gavel-ai`, applicable to both **OneShot** (single-turn) and **Conversational** (multi-turn) (and eventually **Autotune**) workflows. The goal is to standardize the visualization of model performance, judging results, and conversation traces into a single, cohesive HTML report.

## 2. Design Philosophy
- **Unified Schema**: Treat all evaluations as "conversations". OneShot is simply a conversation with exactly one Request/Response pair.
- **Side-by-Side Comparison**: Primary focus is comparing multiple variants (models/prompts) against the same scenario.
- **Progressive Disclosure**: High-level summaries first, drilled down to specific scenarios, with expandable details for large text blobs and judge reasoning.

## 3. Report Structure

### 3.1. Header
- **Title**: e.g., "Conversational Evaluation Report" or "OneShot Evaluation Report"
- **Metadata Badge**:
  - Evaluation Name (`test_new_conv`)
  - Run ID (`20260118_114907`)
  - Generated Timestamp

### 3.2. Section 1: Evaluation Summary
A simplified high-level table comparing quality metrics across variants.

| Model | [Metric Name 1] | [Metric Name 2] | ... | Overall Avg |
|-------|-----------------|-----------------|-----|-------------|
| ai_gateway_claude | 0.82 | 1.00 | ... | **0.91** |
| ai_gateway_gemini | 0.85 | 1.00 | ... | **0.93** |

*   **Logic**: Aggregate average scores for each metric type per model.

### 3.3. Section 2: Performance Summary
A table comparing latency and timing execution stats.

| Model | Avg Turn Time | Avg Conversation Time | Total Time |
|-------|---------------|-----------------------|------------|
| ai_gateway_claude | 6.39s | 19.16s | 38.31s |

### 3.4. Section 3: Detailed Analysis (By Test Subject/Prompt)
The report is segmented by the "System Under Test" (e.g., `conversation_agent`).

#### Scenario Card
For each scenario within the subject:
1.  **Header**: Scenario ID (e.g., `conv_1`)
2.  **System Prompt / Context**: Collapsible section showing the initialization parameters or system prompt used.
3.  **Comparison Table**:
    A layout comparing variants side-by-side (or vertically stacked on mobile).

    | [Variant A Name] | [Variant B Name] |
    |------------------|------------------|
    | **Conversation Trace** | **Conversation Trace** |
    | (See 3.5 Conversation View) | (See 3.5 Conversation View) |
    | **Judge Results** | **Judge Results** |
    | Score: 5/5 | Score: 3/5 |
    | Reasoning: [Expandable] | Reasoning: [Expandable] |

### 3.5. Conversation View Component
A standardized UI component to render interaction traces.

*   **Wrapper**: `.conversation-turns`
*   **Turn Item**: `.turn`
    *   **User Message**: `.turn-user` (Right aligned or distinct color, e.g., Blue `#e3f2fd`)
        *   Role Badge: `USER`
        *   Content: Text
    *   **Assistant Message**: `.turn-assistant` (Left aligned or distinct color, e.g., Purple `#f3e5f5`)
        *   Role Badge: `ASSISTANT`
        *   Content: Text (Truncated by default if > N chars, with "Read More")
        *   Validation/Error State: If error occurred, show red border/box.
    *   **Metadata**:
        *   Duration: `3.77s` (small, gray text at bottom of turn)

## 4. Implementation Requirements

### 4.1. Data Model (`ReportData`)
The reporting engine should ingest a standardized object structure:

```python
class ReportData:
    title: str
    run_id: str
    generated_at: datetime
    summary_metrics: Dict[str, Dict[str, float]] # {model: {metric: score}}
    performance_metrics: Dict[str, Dict[str, float]]
    scenarios: List[ScenarioResult]

class ScenarioResult:
    scenario_id: str
    system_input: str
    variants: Dict[str, VariantResult] # {model_name: result}

class VariantResult:
    turns: List[Turn]
    judgments: List[Judgment]
    metrics: Dict[str, float]
    timing: TimingStats

class Turn:
    role: str # "user" | "assistant"
    content: str
    duration_ms: float
    timestamp: datetime
```

### 4.2. Templating
- Use **Jinja2** for generating the HTML.
- **CSS**: Embed logic for:
    - `truncated-content` / `expanded` classes (Text expansion)
    - `.judge-reasoning-box` (Toggle visibility)
    - Flexbox/Grid for side-by-side comparison tables.

### 4.3. OneShot Adaptation
- **OneShot** runs are legally "Conversations of Length 1".
- The `OneShot` reporter must map its single Request/Response pair into the `Turn` structure:
    - `Input` -> `Turn(role="user")`
    - `Output` -> `Turn(role="assistant")`
- This ensures a single template can maintain "OneShot" and "Conversational" reports.

### 4.4. Reference CSS
To ensure the "crisp" spacing and visual hierarchy, implementations must use the following core CSS values (or equivalent modern alternatives):

```css
/* Container & Spacing */
body { padding: 12px; background: #f5f7fa; }
.container { max-width: 1400px; padding: 0; background: white; border-radius: 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.content { padding: 12px 16px; }

/* Headers */
header { padding: 12px 16px; border-radius: 6px 6px 0 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
h2 { margin: 16px 0 8px 0; padding-bottom: 4px; border-bottom: 2px solid #667eea; }

/* Conversation Components */
.conversation-turns { margin: 8px 0; }
.turn { 
    margin: 8px 0; 
    padding: 8px; 
    background: white; 
    border-radius: 3px; 
    border-left: 3px solid #95a5a6; 
}

.turn-user, .turn-assistant {
    margin: 6px 0;
    padding: 6px;
    border-radius: 3px;
    font-size: 12px;
}

.turn-user { background: #e3f2fd; border-left: 3px solid #1976d2; }
.turn-assistant { background: #f3e5f5; border-left: 3px solid #7b1fa2; }

/* Typography & spacing */
.turn-content { margin-top: 6px; line-height: 1.4; }
.turn-time { margin-top: 4px; font-size: 0.8em; color: #7f8c8d; }
```

## 5. Migration Strategy
1.  **Refactor Reporter**: Create a generic `HTMLReporter` class that accepts the unified `ReportData` structure.
2.  **Adapter Pattern**:
    - `OneShotRun -> ReportData` adapter.
    - `ConversationRun -> ReportData` adapter.
3.  **Update Config**: Ensure `gavel report` command uses the new reporter by default.
