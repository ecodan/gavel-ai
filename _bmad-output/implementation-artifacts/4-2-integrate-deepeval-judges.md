# Story 4.2: Integrate DeepEval Judges

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want to use DeepEval judges out-of-the-box,
So that I have immediate access to proven evaluation logic.

## Acceptance Criteria

1. **DeepEval Similarity Judge:**
   - Given DeepEval is installed
   - When a judge is configured with deepeval.similarity
   - Then the DeepEval similarity judge is instantiated and functional

2. **DeepEval Faithfulness Judge:**
   - Given a judge is configured with deepeval.faithfulness
   - When evaluate() is called
   - Then the DeepEval faithfulness logic is executed correctly

3. **JudgeResult Wrapping:**
   - Given a DeepEval judge completes
   - When it returns
   - Then the result is wrapped in JudgeResult with score (1-10) and reasoning

4. **Error Handling:**
   - Given a DeepEval judge fails
   - When the error occurs
   - Then it's wrapped in JudgeError with recovery guidance

## Tasks / Subtasks

- [ ] Task 1: Create DeepEvalJudge adapter in `src/gavel_ai/judges/deepeval_judge.py` (AC: #1, #2, #3)
  - [ ] Implement `DeepEvalJudge` class inheriting from `Judge` ABC
  - [ ] Implement `__init__(config: JudgeConfig)` with DeepEval judge instantiation
  - [ ] Implement `async evaluate()` method calling DeepEval judge
  - [ ] Convert DeepEval scores to 1-10 integer scale
  - [ ] Extract reasoning from DeepEval results
  - [ ] Add telemetry spans for judge execution

- [ ] Task 2: Support multiple DeepEval judge types (AC: #1, #2)
  - [ ] Implement `deepeval.similarity` judge integration
  - [ ] Implement `deepeval.faithfulness` judge integration
  - [ ] Implement `deepeval.hallucination` judge integration
  - [ ] Implement `deepeval.answer_relevancy` judge integration
  - [ ] Use judge name from config to select appropriate DeepEval judge

- [ ] Task 3: Implement score normalization (AC: #3)
  - [ ] Convert DeepEval float scores to 1-10 integer range
  - [ ] Handle edge cases (scores outside expected range)
  - [ ] Ensure consistent rounding logic

- [ ] Task 4: Implement error handling (AC: #4)
  - [ ] Wrap DeepEval exceptions in JudgeError
  - [ ] Provide recovery guidance in error messages
  - [ ] Log errors with telemetry spans
  - [ ] Handle missing dependencies gracefully

- [ ] Task 5: Write comprehensive tests in `tests/unit/test_deepeval_judge.py` (All ACs)
  - [ ] Test DeepEval similarity judge instantiation and execution
  - [ ] Test DeepEval faithfulness judge instantiation and execution
  - [ ] Test score conversion to 1-10 range
  - [ ] Test reasoning extraction
  - [ ] Test error handling and JudgeError wrapping
  - [ ] Mock DeepEval for offline testing
  - [ ] Ensure 70%+ coverage

- [ ] Task 6: Run validation and quality checks (All ACs)
  - [ ] Run `black src/ tests/` to format code
  - [ ] Run `ruff check src/ tests/` for linting
  - [ ] Run `mypy src/` for type checking
  - [ ] Run `pytest tests/unit/test_deepeval_judge.py` to verify all tests pass
  - [ ] Ensure pre-commit hooks pass

## Dev Notes

### Architecture Requirements (Decision 5: Judge Integration & Plugin System)

**CRITICAL: DeepEval-native integration**

From Architecture Document (Decision 5):
- Use DeepEval directly (wrap/adapt their judges)
- Judge references use `deepeval.<name>` namespace (e.g., "deepeval.similarity", "deepeval.faithfulness")
- Sequential execution model (judge A evaluates all outputs, then judge B, etc.)
- Score format: Integer 1-10 scale (convert from DeepEval float scores)
- DeepEval Integration: Adapter pattern wrapping DeepEval judges

**Supported DeepEval Judges:**
- deepeval.similarity
- deepeval.faithfulness
- deepeval.hallucination
- deepeval.answer_relevancy

**DeepEval Integration Pattern:**
```python
from gavel_ai.judges.base import Judge
from gavel_ai.core.models import JudgeConfig, JudgeResult, Scenario
from gavel_ai.telemetry import get_tracer

class DeepEvalJudge(Judge):
    """Adapter for DeepEval judges."""

    def __init__(self, config: JudgeConfig):
        super().__init__(config)
        self.tracer = get_tracer(__name__)
        self._init_deepeval_judge()

    def _init_deepeval_judge(self) -> None:
        """Initialize the appropriate DeepEval judge based on config."""
        # Map deepeval_name to DeepEval judge class
        # Instantiate with config parameters

    async def evaluate(
        self, scenario: Scenario, subject_output: str
    ) -> JudgeResult:
        """Evaluate using DeepEval judge and convert to JudgeResult."""
        with self.tracer.start_as_current_span("judge.evaluate") as span:
            span.set_attribute("judge.id", self.config.judge_id)
            span.set_attribute("judge.name", self.config.deepeval_name)

            # Call DeepEval judge
            deepeval_result = await self._call_deepeval(scenario, subject_output)

            # Convert score to 1-10 integer
            score = self._normalize_score(deepeval_result.score)
            span.set_attribute("judge.score", score)

            return JudgeResult(
                score=score,
                reasoning=deepeval_result.reasoning,
                evidence=deepeval_result.evidence,
            )
```

### Technology Stack & Versions

**Python Runtime:** 3.10+ (currently 3.13)

**Core Dependencies:**
- **DeepEval** (LLM-as-judge library) - latest stable version
- **OpenTelemetry** (telemetry instrumentation)
- **Pydantic v2** (data validation)

**DeepEval Judge Types:**
- `deepeval.similarity`: Semantic similarity between output and expected
- `deepeval.faithfulness`: Factual accuracy and adherence to source
- `deepeval.hallucination`: Detection of hallucinated information
- `deepeval.answer_relevancy`: Relevance of answer to question

### Previous Story Intelligence

**From Story 4.1 (Create Judge Base Class and Interface):**
- ✅ Judge ABC with `async evaluate()` method defined
- ✅ JudgeResult model with score (1-10), reasoning, evidence defined
- ✅ JudgeConfig model with judge_id, deepeval_name defined
- ✅ JudgeError exception for error handling
- ✅ Tracer setup pattern: `get_tracer(__name__)`
- **Dependency:** DeepEvalJudge inherits from Judge ABC
- **Reuse:** JudgeResult, JudgeConfig, JudgeError, get_tracer()

### Score Normalization Strategy

**DeepEval Score Conversion:**
```python
def _normalize_score(self, deepeval_score: float) -> int:
    """
    Convert DeepEval float score to 1-10 integer.

    DeepEval typically returns scores in 0.0-1.0 range.
    Convert to 1-10 scale with rounding.
    """
    # Scale 0.0-1.0 to 1-10
    scaled_score = (deepeval_score * 9) + 1
    # Round to nearest integer
    normalized = round(scaled_score)
    # Clamp to 1-10 range
    return max(1, min(10, normalized))
```

### Error Handling Pattern (MANDATORY)

**DeepEval Error Wrapping:**
```python
async def evaluate(self, scenario: Scenario, subject_output: str) -> JudgeResult:
    try:
        deepeval_result = await self._call_deepeval(scenario, subject_output)
        return JudgeResult(...)
    except ImportError as e:
        raise JudgeError(
            f"DeepEval not installed - Install with 'pip install deepeval'"
        ) from e
    except Exception as e:
        raise JudgeError(
            f"DeepEval judge '{self.config.deepeval_name}' failed: {e} - "
            f"Check scenario format and DeepEval configuration"
        ) from e
```

### Testing Strategy

**Mock DeepEval for Offline Testing:**
```python
# tests/unit/test_deepeval_judge.py
from unittest.mock import Mock, patch
import pytest

@patch('gavel_ai.judges.deepeval_judge.DeepEvalSimilarityJudge')
def test_deepeval_similarity_integration(mock_deepeval):
    """Test DeepEval similarity judge integration."""
    # Mock DeepEval judge
    mock_instance = Mock()
    mock_instance.evaluate.return_value = Mock(score=0.85, reasoning="High similarity")
    mock_deepeval.return_value = mock_instance

    # Test judge
    config = JudgeConfig(judge_id="test", deepeval_name="deepeval.similarity")
    judge = DeepEvalJudge(config)
    result = await judge.evaluate(scenario, output)

    assert result.score == 9  # 0.85 * 9 + 1 = 8.65 → rounds to 9
    assert "similarity" in result.reasoning.lower()
```

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 5: Judge Integration & Plugin System]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.2: Integrate DeepEval Judges]
- [Source: _bmad-output/implementation-artifacts/4-1-create-judge-base-class-and-interface.md#Dev Notes]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

### Completion Notes List

### File List

## Change Log

- **2025-12-29**: Story created with DeepEval integration requirements, score normalization strategy, and comprehensive testing approach
- **2025-12-29**: ✅ Implementation verified - 11 tests passing (test_deepeval_judge.py), DeepEvalJudge with answer_relevancy, faithfulness, hallucination, GEval support complete
