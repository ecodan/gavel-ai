## Core Invariants

All changes to this slice must honor these fundamental system rules:

1. **Immutable Raw Results**: Once `results_raw.jsonl` is written and the run has exited, its contents must never be modified. All subsequent evaluation (judging) must happen in `results_judged.jsonl`.
2. **Standard Score Scale**: All judges must output a score on a 1-10 integer scale. This is a fundamental assumption for the reporting and analysis layer.
3. **Trace-per-Run**: Every evaluation run must have exactly one unique `trace_id` provided by the `TelemetryManager`. all nested scopes (llm calls, judge calls) must use this ID as their parent.
4. **Provider Neutrality**: No business logic in the `processors/` or `judges/` should depend on provider-specific response formats. All responses must be normalized by the `ProviderFactory` layer.
5. **No Blind Retries**: Retries must only be applied to transient network or rate-limit errors (e.g., HTTP 429). Logic errors or configuration errors must fail immediately to avoid token waste.
