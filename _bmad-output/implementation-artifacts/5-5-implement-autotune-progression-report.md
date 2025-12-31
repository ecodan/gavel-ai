# Story 5.5: Implement Autotune Progression Report

Status: backlog

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want autotune reports to show prompt evolution and improvement,
So that I can see how optimization progresses (v3+).

## Acceptance Criteria

- **Given** a completed autotune run with multiple passes
  **When** report is generated
  **Then** individual reports for each pass are generated
  - report-pass-1.html, report-pass-2.html, etc.
  - report-aggregate.html showing progression

- **Given** the aggregate report is viewed
  **When** examined
  **Then** it shows judge scores over passes, enabling trend analysis

**Note:** This story is deferred to v3.

**Related Requirements:** FR-5.4

## Tasks / Subtasks

- [ ] DEFERRED TO V3: Create Autotune HTML templates (AC: 1, 2)
  - [ ] Create autotune-pass.html for individual pass reports
  - [ ] Create autotune-aggregate.html for progression visualization
  - [ ] Add chart/graph visualization for score trends
  - [ ] Display prompt evolution across passes

- [ ] DEFERRED TO V3: Implement AutotuneReporter (AC: 1, 2)
  - [ ] Inherit from Jinja2Reporter
  - [ ] Generate individual pass reports
  - [ ] Generate aggregate progression report
  - [ ] Calculate and display score trends
  - [ ] Show prompt changes between passes

- [ ] DEFERRED TO V3: Write tests (AC: 1, 2)
  - [ ] Test individual pass report generation
  - [ ] Test aggregate report with score trends
  - [ ] Mock autotune run with multiple passes

## Dev Notes

### V3 Deferral

**This story is explicitly deferred to V3** as autotune workflows are not part of MVP (v1) or v2 scope.

**Reasoning:**
1. Autotune workflow requires extensive infrastructure not in v1/v2
2. Prompt optimization and multi-pass evaluation is advanced feature
3. OneShot (Story 5.3) and Conversational (Story 5.4) are higher priority
4. V3 will focus on automation and optimization workflows

**When implementing in V3:**
- Review autotune workflow requirements from architecture
- Design prompt evolution tracking system
- Implement score trend visualization (charts/graphs)
- Consider using charting library (Chart.js, Plotly, etc.)
- Ensure backward compatibility with v1/v2 reporters

**For now:**
- Mark story as "deferred-v3" in sprint-status.yaml
- Do not implement until v3 planning begins
- Focus Epic 5 efforts on Stories 5.1, 5.2, 5.3

### Placeholder Implementation (Optional)

If a placeholder is desired for v1:

```python
# src/gavel_ai/reporters/autotune_reporter.py
class AutotuneReporter(Jinja2Reporter):
    """Autotune progression report generator (V3+)."""

    async def generate(self, run: Run, template: str = "autotune-aggregate.html") -> str:
        """Generate autotune progression report."""
        raise NotImplementedError(
            "AutotuneReporter is planned for V3 - "
            "Use OneShotReporter for current evaluations"
        )
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.5: Implement Autotune Progression Report]
- [Source: _bmad-output/planning-artifacts/epics.md#FR Category 5 - Reporting & Result Presentation]

## Dev Agent Record

### Agent Model Used

_To be filled by dev agent (V3+)_

### Debug Log References

_To be filled by dev agent (V3+)_

### Completion Notes List

_To be filled by dev agent (V3+)_

### File List

_To be filled by dev agent (V3+)_

## Change Log

- 2025-12-29: Story created and marked for V3 deferral
