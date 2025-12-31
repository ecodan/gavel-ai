# Story 5.4: Implement Conversational Report Format

Status: backlog

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want conversational evaluations to show full conversations with judge evaluations,
So that I can understand how models behave in multi-turn contexts (v2+).

## Acceptance Criteria

- **Given** a completed conversational evaluation
  **When** report is generated
  **Then** the report includes:
  - Full conversation history per scenario
  - Judge evaluations of each turn or final conversation
  - Variant comparison

**Note:** This story may be deferred to v2 depending on MVP scope.

**Related Requirements:** FR-5.3

## Tasks / Subtasks

- [ ] Create Conversational HTML template in src/gavel_ai/reporters/templates/conversational.html (AC: 1)
  - [ ] Implement conversation flow display (chat-like format)
  - [ ] Display turn-by-turn or final conversation evaluation
  - [ ] Show variant comparison side-by-side
  - [ ] Add responsive CSS for conversation threads

- [ ] Create Conversational Markdown template in src/gavel_ai/reporters/templates/conversational.md (AC: 1)
  - [ ] Format conversation as numbered turns
  - [ ] Display judge evaluations per turn or final
  - [ ] Show variant comparison

- [ ] Implement ConversationalReporter in src/gavel_ai/reporters/conversational_reporter.py (AC: 1)
  - [ ] Inherit from Jinja2Reporter
  - [ ] Override generate() to use conversational templates
  - [ ] Build context specific to conversational format
  - [ ] Format multi-turn conversations for display
  - [ ] Support turn-level and conversation-level judge evaluations
  - [ ] Integrate OpenTelemetry spans

- [ ] Implement conversation formatting logic (AC: 1)
  - [ ] Parse multi-turn conversation from results
  - [ ] Format turns with speaker labels (User, Assistant)
  - [ ] Extract judge evaluations per turn or final
  - [ ] Handle conversation context accumulation

- [ ] Write comprehensive tests in tests/unit/reporters/test_conversational_reporter.py (AC: 1)
  - [ ] Test HTML report generation with conversation display
  - [ ] Test Markdown report generation
  - [ ] Test turn-by-turn evaluation formatting
  - [ ] Test final conversation evaluation formatting
  - [ ] Mock Run with conversational results data
  - [ ] Achieve 70%+ coverage

- [ ] Update exports in src/gavel_ai/reporters/__init__.py (AC: 1)
  - [ ] Export ConversationalReporter

## Dev Notes

### Architecture Context

This story implements the **Conversational Report Format**, which extends reporting to support multi-turn conversational evaluations. This is a v2+ feature and may be deferred if not required for MVP.

**Key Architectural Principles:**
- Conversational workflow support (FR-6.2)
- Multi-turn evaluation display (FR-5.3)
- Extends Jinja2Reporter pattern (FR-6.1)

### Dependencies on Previous Stories

**CRITICAL: Stories 5.1, 5.2, and 5.3 should be complete before starting this story.**
- Requires Reporter ABC from Story 5.1
- Requires Jinja2Reporter from Story 5.2
- Follows pattern established in Story 5.3 (OneShotReporter)

**From Epic 3, Story 3.4:**
- ScenarioProcessor handles multi-turn conversations
- Context accumulates across turns
- Results include full conversation history

**Note:** If ScenarioProcessor (Story 3.4) is deferred, this story can also be deferred to v2.

### Implementation Patterns

**ConversationalReporter extends Jinja2Reporter:**
```python
from gavel_ai.reporters.jinja_reporter import Jinja2Reporter

class ConversationalReporter(Jinja2Reporter):
    """Conversational evaluation report generator."""

    async def generate(self, run: Run, template: str = "conversational.html") -> str:
        """Generate conversational report with full conversation display."""
        with self.tracer.start_as_current_span("reporter.generate") as span:
            span.set_attribute("reporter.type", "conversational")
            span.set_attribute("run.id", run.run_id)

            # Build conversational-specific context
            context = self._build_conversational_context(run)

            # Render using parent class
            return await super().generate(run, template)

    def _build_conversational_context(self, run: Run) -> Dict[str, Any]:
        """Build context specific to conversational format."""
        base_context = self._build_context(run)

        # Add conversational-specific formatting
        base_context["conversations"] = self._format_conversations(run)

        return base_context

    def _format_conversations(self, run: Run) -> List[Dict[str, Any]]:
        """Format multi-turn conversations for display."""
        conversations = []

        for scenario_results in self._group_results_by_scenario(run):
            conversation = {
                "scenario_id": scenario_results[0]["scenario_id"],
                "turns": self._extract_turns(scenario_results),
                "final_evaluation": self._extract_final_evaluation(scenario_results),
                "variants": self._compare_variants(scenario_results),
            }
            conversations.append(conversation)

        return conversations

    def _extract_turns(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract individual turns from conversation results."""
        # Parse conversation history into turns
        # Return list of {turn_number, speaker, message, judge_eval}
        pass
```

### Conversational HTML Template Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{ title }} - Conversational Evaluation</title>
    <style>
        .conversation { border: 1px solid #ccc; padding: 20px; margin: 20px 0; }
        .turn { margin: 10px 0; padding: 10px; border-left: 3px solid #007bff; }
        .turn.user { border-left-color: #28a745; }
        .turn.assistant { border-left-color: #007bff; }
        .speaker { font-weight: bold; }
        .message { margin-top: 5px; }
        .judge-eval { background-color: #f8f9fa; padding: 10px; margin-top: 5px; }
    </style>
</head>
<body>
    <header>
        <h1>{{ title }}</h1>
        <p><strong>Generated:</strong> {{ metadata.timestamp }}</p>
    </header>

    <section id="conversations">
        <h2>Conversations</h2>
        {% for conversation in conversations %}
        <div class="conversation">
            <h3>Scenario: {{ conversation.scenario_id }}</h3>

            <div class="turns">
                {% for turn in conversation.turns %}
                <div class="turn {{ turn.speaker|lower }}">
                    <div class="speaker">{{ turn.speaker }}:</div>
                    <div class="message">{{ turn.message }}</div>
                    {% if turn.judge_eval %}
                    <div class="judge-eval">
                        <strong>Judge Evaluation:</strong> Score {{ turn.judge_eval.score }}/10
                        <p>{{ turn.judge_eval.reasoning }}</p>
                    </div>
                    {% endif %}
                </div>
                {% endfor %}
            </div>

            {% if conversation.final_evaluation %}
            <div class="final-evaluation">
                <h4>Final Conversation Evaluation</h4>
                {% for judge_result in conversation.final_evaluation %}
                <div>
                    <strong>{{ judge_result.judge_id }}:</strong> {{ judge_result.score }}/10
                    <p>{{ judge_result.reasoning }}</p>
                </div>
                {% endfor %}
            </div>
            {% endif %}

            <div class="variant-comparison">
                <h4>Variant Comparison</h4>
                <table>
                    <thead>
                        <tr><th>Variant</th><th>Avg Score</th></tr>
                    </thead>
                    <tbody>
                        {% for variant in conversation.variants %}
                        <tr>
                            <td>{{ variant.variant_id }}</td>
                            <td>{{ variant.avg_score }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        {% endfor %}
    </section>
</body>
</html>
```

### V2 Deferral Note

**This story is marked for V2+ deferral because:**
1. Conversational workflow (ScenarioProcessor) may be deferred to v2
2. OneShot evaluation (Story 5.3) is the priority for MVP
3. Multi-turn conversation support requires additional processor infrastructure

**If implementing in v1:**
- Ensure ScenarioProcessor (Story 3.4) is complete
- Ensure results.jsonl supports conversation history
- Test with sample multi-turn conversations

**If deferring to v2:**
- Mark story as "deferred-v2" in sprint-status.yaml
- Focus on Stories 5.1, 5.2, 5.3 for v1 MVP
- Plan for v2 implementation after OneShot workflow is stable

### Testing Strategy

```python
# tests/unit/reporters/test_conversational_reporter.py
@pytest.fixture
def mock_conversational_run():
    """Mock Run with conversational evaluation data."""
    class MockRun:
        run_id = "run-20251229-120000"
        metadata = {
            "eval_name": "Multi-turn Conversation Test",
            "timestamp": "2025-12-29T12:00:00Z",
            "scenario_count": 2,
            "variant_count": 1,
        }
        results = [
            {
                "scenario_id": "conversation-1",
                "turn": 1,
                "speaker": "User",
                "message": "What is the capital of France?",
                "variant_id": "claude",
                "processor_output": "The capital of France is Paris.",
                "judges": [{"judge_id": "relevancy", "score": 9, "reasoning": "Relevant and accurate."}]
            },
            {
                "scenario_id": "conversation-1",
                "turn": 2,
                "speaker": "User",
                "message": "What about Germany?",
                "variant_id": "claude",
                "processor_output": "The capital of Germany is Berlin.",
                "judges": [{"judge_id": "relevancy", "score": 10, "reasoning": "Perfect context awareness."}]
            },
            # More turns...
        ]
    return MockRun()

async def test_conversational_reporter_formats_turns(mock_conversational_run):
    """ConversationalReporter formats conversation turns correctly."""
    reporter = ConversationalReporter(...)

    conversations = reporter._format_conversations(mock_conversational_run)

    assert len(conversations) > 0
    assert "turns" in conversations[0]
    assert conversations[0]["turns"][0]["speaker"] == "User"
    assert "message" in conversations[0]["turns"][0]
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.4: Implement Conversational Report Format]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.4: Implement ScenarioProcessor]
- [Source: _bmad-output/planning-artifacts/project-context.md#Code Organization & Anti-Patterns]

## Dev Agent Record

### Agent Model Used

_To be filled by dev agent_

### Debug Log References

_To be filled by dev agent_

### Completion Notes List

_To be filled by dev agent_

### File List

_To be filled by dev agent_

## Change Log

- 2025-12-29: Story created with v2+ deferral option and complete conversational report specification
