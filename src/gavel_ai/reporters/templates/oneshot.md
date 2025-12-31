# {{ title }}

**Generated:** {{ metadata.timestamp }}

---

## Overview

- **Variants Tested:** {{ overview.variant_count }}
- **Scenarios:** {{ overview.scenario_count }}
- **Judges:**
{% for judge in judges %}
  - {{ judge.judge_id }} ({{ judge.judge_name }})
{% endfor %}

---

## 🏆 Winner

{% if winner.is_tie %}
**TIE:** {{ winner.variant_id }} and others (Score: {{ winner.total_score }})
{% else %}
**{{ winner.variant_id }}** (Total Score: {{ winner.total_score }}, Avg: {{ winner.avg_score|round(2) }})
{% endif %}

---

## Summary

| Variant | Avg Score | Total Score | Scenarios |
|---------|-----------|-------------|-----------|
{% for variant in summary %}
| {{ '**' + variant.variant_id + '**' if variant.variant_id == winner.variant_id else variant.variant_id }} | {{ variant.avg_score|round(2) }} | {{ variant.total_score|round(2) }} | {{ variant.scenario_count }} |
{% endfor %}

---

## Detailed Results

{% for result in results %}
### Scenario: {{ result.scenario_id }}

**Input:**
```
{{ result.input }}
```

| Variant | Output | Scores |
|---------|--------|--------|
{% for output in result.variant_outputs %}
| {{ output.variant_id }} | {{ output.output }} | {% for judge_result in output.judge_results %}**{{ judge_result.judge_id }}:** {{ judge_result.score }}/10<br>*Reasoning:* {{ judge_result.reasoning }}{% if judge_result.evidence %}<br>*Evidence:* {{ judge_result.evidence }}{% endif %}<br>{% endfor %} |
{% endfor %}

---

{% endfor %}

## Execution Metrics

- **Total Duration:** {{ telemetry.total_duration_seconds }}s
- **LLM Calls:** {{ telemetry.llm_calls.total }}
- **Tokens:** {{ telemetry.llm_calls.tokens.prompt_total }} prompt, {{ telemetry.llm_calls.tokens.completion_total }} completion

---

**Config Hash:** {{ metadata.config_hash }}
