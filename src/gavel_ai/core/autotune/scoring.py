"""Score normalization for autotune convergence checks and reporting.

All `avg_score` and `IterationMetadata` fields use a 0.0-1.0 scale regardless
of the underlying judge's native scoring range, so convergence thresholds and
report comparisons are meaningful across mixed judge types.
"""

_DETERMINISTIC_JUDGE_TYPES: frozenset[str] = frozenset({"classifier", "regression"})


def normalize_score(score: float, judge_type: str) -> float:
    """Normalize a judge score to the 0.0-1.0 scale.

    Both deterministic judges (`classifier`/`regression`) and LLM-based judges
    (e.g. `deepeval.geval` and the other `deepeval.*` types) natively produce
    scores on the 0.0-1.0 scale, so this is a pass-through kept for call-site
    clarity and as a single seam if a judge type's native scale ever changes.
    """
    del judge_type  # unused: all judge types are natively 0.0-1.0
    return float(score)
