# Judges & Metrics Reference

> Authoritative guide to judge types, configuration, required scenario fields,
> score interpretation, and metric selection.

---

## Score Scale

All judges normalize scores to a **1–10 integer scale**.

| Score | Meaning |
|---|---|
| 9–10 | Excellent — meets or exceeds expectations |
| 7–8 | Good — minor gaps but acceptable |
| 5–6 | Marginal — noticeable issues, may pass depending on threshold |
| 3–4 | Poor — significant failure to meet criteria |
| 1–2 | Very poor — largely incorrect or missing |

DeepEval's native 0.0–1.0 float scores are normalized via:
`normalized = round(1 + raw_score * 9)`, clamped to [1, 10].

The pass/fail threshold in `eval_config.json` is also on the **1–10 scale**
after normalization. A `threshold: 0.7` in the raw config corresponds roughly
to a score of 7 after normalization.

---

## Available Judge Types

### `deepeval.geval` — Custom Criteria Judge

**Use when**: You want to define your own evaluation criteria tailored to your
use case. The most flexible judge — works for almost any evaluation goal.

**How it works**: Sends the model output to a judge LLM along with your
`criteria` and `evaluation_steps`. The judge LLM scores the output against
your criteria.

**Required scenario fields**: `input` (required). `expected_output` (or equivalent via
`field_mapping`) is always passed to the judge LLM. Every scenario must have a resolvable
value — gavel validates this upfront and raises `ConfigError` if any scenario is missing it.

**Config in `eval_config.json`:**
```json
{
  "name": "quality-judge",
  "type": "deepeval.geval",
  "config": {
    "model": "claude-haiku-4-5-20251001",
    "criteria": "Does the response correctly answer the user's question with accurate information?",
    "evaluation_steps": [
      "Check if the response directly addresses the question asked",
      "Verify factual accuracy of any claims made",
      "Assess whether the response is complete and not missing key information",
      "Check that the tone is appropriate for the context"
    ],
    "threshold": 0.7,
    "strict_mode": false
  }
}
```

**`strict_mode`** (bool, default `false`) — when `true`, GEval returns a binary 0 or 1
score instead of a continuous float. After normalization this becomes score 1 or 10.
Use for format/schema compliance checks where you want a hard pass/fail rather than a
gradient score.

**`expected_output` resolution** — in priority order:
1. `field_mapping.expected_output` in the `scenarios` config section (dot-notation path)
2. `expected_output_template` in the judge config (Jinja2, rendered with scenario fields)
3. `scenario.expected_behavior` / `scenario.expected` / `scenario.expected_output` fields

**Writing good criteria & evaluation steps:**
- `criteria` should be a single sentence describing what "good" looks like.
- `evaluation_steps` should be 3–6 concrete, testable checks. Vague steps
  produce inconsistent scores.
- Avoid double negatives and compound conditions in a single step.
- Steps are evaluated in order — put the most important checks first.

---

### `deepeval.answer_relevancy` — Relevancy Judge

**Use when**: You want to check whether the model's response is actually
relevant to the user's input (catches off-topic, evasive, or non-answers).

**How it works**: Measures whether the actual output addresses the input
question. Does not require expected output.

**Required scenario fields**: `input` (required)

**Config:**
```json
{
  "name": "relevancy",
  "type": "deepeval.answer_relevancy",
  "threshold": 0.7,
  "config": {
    "model": "claude-haiku-4-5-20251001"
  }
}
```

---

### `deepeval.contextual_relevancy` — Context Relevancy Judge

**Use when**: The model is expected to use retrieved context (RAG systems,
document QA). Checks if the provided context is actually relevant to the query.

**How it works**: Evaluates whether the `context` field in the scenario is
relevant to the `input`. Useful for diagnosing retrieval quality, not just
generation quality.

**Required scenario fields**: `input` (required), `context` (required — via
`input` dict key or scenario `context` field)

**Config:**
```json
{
  "name": "context-relevancy",
  "type": "deepeval.contextual_relevancy",
  "threshold": 0.6,
  "config": {
    "model": "claude-haiku-4-5-20251001"
  }
}
```

---

### `deepeval.faithfulness` — Faithfulness Judge

**Use when**: The model should ground its response in provided context (RAG,
summarization). Checks for hallucinations relative to the context.

**How it works**: Measures whether all claims in the response can be
attributed to the provided `context`. A low score means the model is
making things up that are not in the context.

**Required scenario fields**: `input` (required), `context` (required)

**Config:**
```json
{
  "name": "faithfulness",
  "type": "deepeval.faithfulness",
  "threshold": 0.8,
  "config": {
    "model": "claude-haiku-4-5-20251001"
  }
}
```

---

### `deepeval.hallucination` — Hallucination Judge

**Use when**: The model should NOT introduce information beyond what is in
the `retrieval_context`. Stricter than faithfulness — checks output against
a grounding document list.

**How it works**: Uses `retrieval_context` (a list of document strings) as
the ground truth. Penalizes any output claim not supported by those documents.

**Required scenario fields**: `input` (required), `retrieval_context` (required
— must be in the `input` dict as an array of strings)

**Scenario example:**
```json
{
  "id": "hallucination-001",
  "input": {
    "query": "What is the maximum file upload size?",
    "retrieval_context": [
      "The system supports file uploads up to 100MB per file.",
      "Batch uploads are limited to 10 files at a time."
    ]
  },
  "expected_behavior": "The response should state 100MB per file and 10 files per batch."
}
```

**Config:**
```json
{
  "name": "hallucination-check",
  "type": "deepeval.hallucination",
  "threshold": 0.85,
  "config": {
    "model": "claude-haiku-4-5-20251001"
  }
}
```

---

## Choosing Judges

| Evaluation goal | Recommended judges |
|---|---|
| General response quality | `deepeval.geval` with custom criteria |
| Response relevance / staying on topic | `deepeval.answer_relevancy` |
| RAG accuracy (does output match retrieved docs) | `deepeval.faithfulness` + `deepeval.hallucination` |
| Retrieval quality check | `deepeval.contextual_relevancy` |
| Comprehensive RAG eval | `deepeval.contextual_relevancy` + `deepeval.faithfulness` + `deepeval.geval` |
| Instruction-following | `deepeval.geval` with step-by-step instruction checks |

**Using multiple judges**: Combine judges to get layered coverage. Example for
a customer support bot: `answer_relevancy` (stays on topic) + `faithfulness`
(grounded in docs) + `geval` (tone and completeness).

---

## Interpreting Results

### Reading `results_judged.jsonl`

Each line is one scenario execution with embedded judge results:

```json
{
  "scenario_id": "refund-001",
  "processor_output": "Our refund policy allows returns within 30 days...",
  "judges": [
    {
      "judge_id": "quality-judge",
      "score": 8,
      "reasoning": "The response correctly addresses the refund window...",
      "evidence": "DeepEval deepeval.geval score: 0.789"
    }
  ]
}
```

**Triage low scores**: Read `reasoning` first — it explains what the judge
found wrong. Common root causes:

| Low score symptom | Likely cause |
|---|---|
| Consistently low across all scenarios | Prompt is too vague or model is wrong for the task |
| Low on specific scenario categories | Dataset coverage gap or prompt doesn't handle that case |
| Low `faithfulness` but high `geval` | Model is generating plausible but ungrounded content |
| Low `answer_relevancy` | Model is hedging, refusing, or going off-topic |
| Inconsistent scores for similar scenarios | Judge criteria / evaluation steps are ambiguous |

### Milestone comparison

After establishing a good baseline:
1. Mark it: `gavel oneshot milestone --run <run-id> --comment "baseline after prompt v2"`
2. After future changes, run again and compare scores.
3. A regression is any judge score that drops by more than 1 point on average,
   or any increase in the count of scenarios scoring below the threshold.

### Threshold calibration

Start with `threshold: 0.7` (→ score ≥ 7) for most judges. Adjust based on:
- **Raise threshold** if the product requires high precision (medical, legal, financial).
- **Lower threshold** if the task is open-ended or stylistic and strict grading is unfair.
- **Calibrate per judge**: faithfulness and hallucination are typically held to a higher
  standard (0.8+) than style judges (0.6).
