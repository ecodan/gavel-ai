"""Score normalization for autotune convergence checks and reporting.

All `avg_score` and `IterationMetadata` fields use a 0.0-1.0 scale regardless
of the underlying judge's native scoring range, so convergence thresholds and
report comparisons are meaningful across mixed judge types.
"""

_DETERMINISTIC_JUDGE_TYPES: frozenset[str] = frozenset({"classifier", "regression"})


def normalize_score(score: float, judge_type: str) -> float:
    """Normalize a judge score to the 0.0-1.0 scale.

    Deterministic judges (`classifier`/`regression`) already produce 0/1 scores
    and pass through unchanged. LLM-based judges (e.g. `deepeval.geval` and the
    other `deepeval.*` types) score on a 1-10 scale and are divided by 10.0.
    """
    if judge_type in _DETERMINISTIC_JUDGE_TYPES:
        return float(score)
    return float(score) / 10.0
