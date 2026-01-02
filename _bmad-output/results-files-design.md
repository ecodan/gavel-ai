# Results Files Design - Two-File Architecture

## Overview

Run outputs now use a **two-file design** for results:
- **results_raw.jsonl** — Immutable processor outputs
- **results_judged.jsonl** — Mutable judgment artifacts

This separation enables reproducible re-judging without re-executing expensive LLM calls.

---

## Design Rationale

### Why Two Files?

**Problem:**
- Original design had single `results.jsonl` mixing processor outputs and judge results
- When judges change, unclear whether to re-run processors or update results
- No clean way to implement FR-3.3 (re-judge existing runs)

**Solution:**
- Immutable raw results preserve processor execution
- Mutable judged results can be regenerated independently
- Clear separation of concerns: execution vs. judgment

### File Lifecycle

```
1. User runs evaluation
   ↓
2. Processors execute → results_raw.jsonl written (IMMUTABLE)
   ↓
3. Judges applied → results_judged.jsonl written (mutable)
   ↓
4. User changes judges (add/remove/modify)
   ↓
5. results_judged.jsonl regenerated from results_raw.jsonl (NO API CALLS)
   ↓
6. results_raw.jsonl unchanged (source of truth for processor execution)
```

---

## File Specifications

### results_raw.jsonl (Immutable)

**Purpose:** Record of processor execution
**Written by:** Executor after running processors
**Mutable?** NO - Never changes once written
**Schema:** One entry per (test_subject × variant × scenario) combo

**Schema:**
```json
{
  "test_subject": "assistant:v1",
  "variant_id": "claude-sonnet-4-5-20250929",
  "scenario_id": "scenario_1",
  "processor_output": "The full LLM response text goes here",
  "timing_ms": 4250,
  "tokens_prompt": 156,
  "tokens_completion": 87,
  "error": null,
  "timestamp": "2026-01-01T23:29:10.123456Z"
}
```

**Fields:**
- `test_subject`: Prompt/system under test name (e.g., "assistant:v1", "research_agent:v2")
- `variant_id`: Model version or parameter configuration (e.g., "claude-sonnet-4-5-20250929", "gpt-4o")
- `scenario_id`: Reference to scenario being tested
- `processor_output`: Complete LLM response (preserve exactly as received)
- `timing_ms`: End-to-end latency for this processor call
- `tokens_prompt`: Input tokens consumed
- `tokens_completion`: Output tokens generated
- `error`: null if successful, error message if failed
- `timestamp`: ISO 8601 timestamp when processor ran

**Immutability Contract:**
- Once written, never modified
- Enables reproducibility: same scenario + variant always has same output
- Preserved across re-judging: source of truth for execution

**Example with 2 scenarios, 1 test_subject, 1 model variant:**
```jsonl
{"test_subject": "assistant:v1", "variant_id": "claude-sonnet-4-5-20250929", "scenario_id": "s1", "processor_output": "...", "timing_ms": 4200, "tokens_prompt": 150, "tokens_completion": 85, "error": null, "timestamp": "2026-01-01T23:29:10.000Z"}
{"test_subject": "assistant:v1", "variant_id": "claude-sonnet-4-5-20250929", "scenario_id": "s2", "processor_output": "...", "timing_ms": 4050, "tokens_prompt": 160, "tokens_completion": 92, "error": null, "timestamp": "2026-01-01T23:29:14.200Z"}
```

---

### results_judged.jsonl (Mutable)

**Purpose:** Complete evaluation picture with judge scores
**Written by:** Judge executor after applying judges
**Mutable?** YES - Regenerated when judges change
**Schema:** One entry per (test_subject × variant × scenario) combo with judges array

**Schema:**
```json
{
  "test_subject": "assistant:v1",
  "variant_id": "claude-sonnet-4-5-20250929",
  "scenario_id": "scenario_1",
  "processor_output": "The full LLM response text goes here",
  "timing_ms": 4250,
  "tokens_prompt": 156,
  "tokens_completion": 87,
  "error": null,
  "judges": [
    {
      "judge_id": "similarity",
      "judge_name": "deepeval.similarity",
      "judge_score": 8,
      "judge_reasoning": "Response closely matches expected output in tone and content",
      "judge_evidence": "Similarity score: 0.92/1.0"
    },
    {
      "judge_id": "faithfulness",
      "judge_name": "deepeval.faithfulness",
      "judge_score": 7,
      "judge_reasoning": "All claims grounded in provided context",
      "judge_evidence": "3 out of 3 claims verified"
    }
  ]
}
```

**Judge Entry Fields:**
- `judge_id`: Unique identifier (e.g., "similarity", "custom_eval")
- `judge_name`: DeepEval reference name (e.g., "deepeval.similarity")
- `judge_score`: Integer 1-10 score
- `judge_reasoning`: Human-readable explanation of score
- `judge_evidence`: Supporting evidence/details

**Mutability Contract:**
- Regenerated when judges change
- Can be safely deleted and re-created from results_raw.jsonl
- Always includes complete processor data (duplicated from results_raw.jsonl)
- Supports multiple judges per entry (judges array)

**Example with 2 judges per scenario:**
```jsonl
{"scenario_id": "s1", "variant_id": "v0", "processor_type": "prompt_input", "processor_output": "...", "judges": [{"judge_id": "j1", "judge_name": "deepeval.similarity", "judge_score": 8}, {"judge_id": "j2", "judge_name": "deepeval.faithfulness", "judge_score": 7}]}
{"scenario_id": "s2", "variant_id": "v0", "processor_type": "prompt_input", "processor_output": "...", "judges": [{"judge_id": "j1", "judge_name": "deepeval.similarity", "judge_score": 9}, {"judge_id": "j2", "judge_name": "deepeval.faithfulness", "judge_score": 6}]}
```

---

## Workflow Examples

### Example 1: Simple Local Eval (No Judges)

**Command:**
```bash
gavel oneshot run --eval my_eval
```

**Run Directory Output:**
```
runs/run-20260101-232906/
├── results_raw.jsonl           # 2 lines (2 scenarios × 1 variant)
├── results_judged.jsonl        # 2 lines (same as raw, empty judges array)
├── telemetry.jsonl
├── run_metadata.json
└── report.html
```

**results_raw.jsonl** (2 lines):
```jsonl
{"test_subject": "assistant:v1", "variant_id": "claude-sonnet-4-5-20250929", "scenario_id": "s1", "processor_output": "...", "timing_ms": 4200, "tokens_prompt": 150, "tokens_completion": 85, "error": null}
{"test_subject": "assistant:v1", "variant_id": "claude-sonnet-4-5-20250929", "scenario_id": "s2", "processor_output": "...", "timing_ms": 4050, "tokens_prompt": 160, "tokens_completion": 92, "error": null}
```

**results_judged.jsonl** (2 lines):
```jsonl
{"test_subject": "assistant:v1", "variant_id": "claude-sonnet-4-5-20250929", "scenario_id": "s1", "processor_output": "...", "judges": []}
{"test_subject": "assistant:v1", "variant_id": "claude-sonnet-4-5-20250929", "scenario_id": "s2", "processor_output": "...", "judges": []}
```

---

### Example 2: Eval with Judges

**Command:**
```bash
gavel oneshot run --eval my_eval
```

**Config includes judges:** similarity, faithfulness

**Run Directory Output:**
```
runs/run-20260101-233200/
├── results_raw.jsonl           # 2 lines (execution only)
├── results_judged.jsonl        # 2 lines (execution + 2 judges per line)
├── telemetry.jsonl
├── run_metadata.json
└── report.html
```

**results_raw.jsonl** (2 lines):
```jsonl
{"test_subject": "assistant:v1", "variant_id": "claude-sonnet-4-5-20250929", "scenario_id": "s1", "processor_output": "...", "timing_ms": 4200, "tokens_prompt": 150, "tokens_completion": 85, "error": null}
{"test_subject": "assistant:v1", "variant_id": "claude-sonnet-4-5-20250929", "scenario_id": "s2", "processor_output": "...", "timing_ms": 4050, "tokens_prompt": 160, "tokens_completion": 92, "error": null}
```

**results_judged.jsonl** (2 lines with judges):
```jsonl
{"test_subject": "assistant:v1", "variant_id": "claude-sonnet-4-5-20250929", "scenario_id": "s1", "processor_output": "...", "judges": [{"judge_id": "similarity", "judge_name": "deepeval.similarity", "judge_score": 8, "judge_reasoning": "...", "judge_evidence": "..."}, {"judge_id": "faithfulness", "judge_name": "deepeval.faithfulness", "judge_score": 7, "judge_reasoning": "...", "judge_evidence": "..."}]}
{"test_subject": "assistant:v1", "variant_id": "claude-sonnet-4-5-20250929", "scenario_id": "s2", "processor_output": "...", "judges": [{"judge_id": "similarity", "judge_name": "deepeval.similarity", "judge_score": 9}, {"judge_id": "faithfulness", "judge_name": "deepeval.faithfulness", "judge_score": 6}]}
```

---

### Example 3: Re-Judging Existing Run (FR-3.3)

**Original run had judges:** similarity, faithfulness
**User now wants to add:** "custom_eval" judge

**Command:**
```bash
gavel oneshot judge --run run-20260101-233200 --judges similarity,faithfulness,custom_eval
```

**Internal Process:**
1. Load results_raw.jsonl (immutable - contains processor outputs)
2. Load new judge configs for all 3 judges
3. Apply all 3 judges to data from results_raw.jsonl
4. Write new results_judged.jsonl (overwrites old version)
5. results_raw.jsonl unchanged

**Run Directory After Re-Judge:**
```
runs/run-20260101-233200/
├── results_raw.jsonl           # UNCHANGED (still 2 lines)
├── results_judged.jsonl        # UPDATED (2 lines, now with 3 judges per line)
├── telemetry.jsonl             # UNCHANGED
├── run_metadata.json           # UNCHANGED
└── report.html                 # REGENERATED with new judge scores
```

**New results_judged.jsonl** (2 lines with 3 judges):
```jsonl
{"test_subject": "assistant:v1", "variant_id": "claude-sonnet-4-5-20250929", "scenario_id": "s1", "processor_output": "...", "judges": [{"judge_id": "similarity", "judge_score": 8}, {"judge_id": "faithfulness", "judge_score": 7}, {"judge_id": "custom_eval", "judge_score": 9}]}
{"test_subject": "assistant:v1", "variant_id": "claude-sonnet-4-5-20250929", "scenario_id": "s2", "processor_output": "...", "judges": [{"judge_id": "similarity", "judge_score": 9}, {"judge_id": "faithfulness", "judge_score": 6}, {"judge_id": "custom_eval", "judge_score": 8}]}
```

**Key:** No LLM API calls made. Only judges executed against existing processor outputs.

---

## Usage for Developers

### Reading Raw Results
```python
# Access processor outputs (never changes)
import jsonlines

with jsonlines.open("results_raw.jsonl") as reader:
    for entry in reader:
        scenario_id = entry["scenario_id"]
        processor_output = entry["processor_output"]
        latency_ms = entry["timing_ms"]
        tokens = entry["tokens_completion"]
```

### Reading Judged Results
```python
# Access complete evaluation data with judge scores
import jsonlines

with jsonlines.open("results_judged.jsonl") as reader:
    for entry in reader:
        scenario_id = entry["scenario_id"]
        processor_output = entry["processor_output"]

        # Multiple judges per entry
        for judge in entry["judges"]:
            judge_score = judge["judge_score"]
            judge_reasoning = judge["judge_reasoning"]
```

### Re-Judging Logic
```python
# Read immutable raw results
raw_results = list(jsonlines.open("results_raw.jsonl"))

# Apply judges to get new judged results
judged_results = apply_judges(raw_results, new_judges)

# Write new judged version
with jsonlines.open("results_judged.jsonl", mode='w') as writer:
    writer.write_all(judged_results)
```

---

## Requirements Coverage

| Requirement | File | Supported |
|-------------|------|-----------|
| FR-3.2: RunContext manages evaluation artifacts | Both | ✅ |
| FR-3.3: Re-judge existing runs without re-execution | results_raw.jsonl → results_judged.jsonl | ✅ |
| FR-8.4: Results stored in evaluable format | Both (JSONL) | ✅ |
| FR-4.4: Judges produce detailed reasoning with scores | results_judged.jsonl | ✅ |
| Reproducibility: Preserve execution outputs | results_raw.jsonl (immutable) | ✅ |
| Transparency: Access all scenario outputs programmatically | results_raw.jsonl | ✅ |

---

## Backward Compatibility

**Note:** This design differs from the original PRD, which specified a single `results.jsonl` file.

**Migration Path:**
- New evals use two-file design (results_raw.jsonl + results_judged.jsonl)
- Old single-file approach deprecated
- Utility functions available to convert old format to new format (if needed)

---

## Summary

| Aspect | results_raw.jsonl | results_judged.jsonl |
|--------|-------------------|----------------------|
| **Purpose** | Execution record | Evaluation complete picture |
| **Created by** | Executor/Processor | Judge executor |
| **Mutable?** | NO (immutable) | YES (regenerable) |
| **Contains** | Outputs, timing, tokens, errors | Outputs + all judge scores |
| **Updated when** | Never | Judges change |
| **Used for** | Reproducibility, re-judging source | Reports, analysis, final results |
| **Dimensions** | test_subject × variant × scenario | test_subject × variant × scenario (+ judges) |

This design enables the FR-3.3 re-judge workflow while maintaining reproducibility and transparency.
