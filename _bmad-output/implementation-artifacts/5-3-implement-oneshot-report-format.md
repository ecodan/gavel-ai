# Story 5.3: Implement Unified Report Format for OneShot

Status: done

## Story

As a user,
I want OneShot reports to match the Unified Reporting Specification,
So that I have a consistent, high-quality viewing experience across all evaluation types.

## Acceptance Criteria

- **Given** a completed OneShot evaluation
  **When** report is generated
  **Then** it follows the `_bmad-output/planning-artifacts/tech-specs/unified-reporting-spec.md` specification exactly

- **Given** OneShot is a single turn
  **When** rendered in the Conversation View component
  **Then** it is mapped to:
  - Input -> Turn 1 (Role: USER)
  - Output -> Turn 2 (Role: ASSISTANT)
  - Timestamps, duration, and error states are preserved

- **Given** multiple variants
  **When** rendered
  **Then** they are shown side-by-side (or responsive equivalent) just like conversational evaluations

- **Given** the report is opened
  **When** viewed
  **Then** it includes:
  - Header with run metadata
  - Eval Summary Table (Metrics)
  - Performance Summary Table (Timing)
  - Detailed Scenario Cards with Conversation View

**Report Output:**
- Default: HTML (report.html in run directory)
- Template: Jinja2 template implementing the Unified Spec

**Related Requirements:** FR-5.2, FR-5.5, FR-5.6, Unified Reporting Spec

## Tasks / Subtasks

- [x] Refactor OneShot HTML template in src/gavel_ai/reporters/templates/oneshot.html (AC: all)
  - [x] Implement Unified Header with Run ID and Status Badges
  - [x] Implement Eval Summary Table per Spec 3.2
  - [x] Implement Performance Summary Table per Spec 3.3
  - [x] Create reusable CSS for Conversation View (Spec 3.5 & 4.4)
  - [x] Update scenario cards to use side-by-side Layout (Spec 3.4)

- [x] Refactor OneShotReporter in src/gavel_ai/reporters/oneshot_reporter.py (AC: all)
  - [x] Map OneShot input/output into the `Turn` data model
  - [x] Ensure `duration_ms` and timestamps are extracted for both turns
  - [x] Update context building to match the Unified Data Model (Spec 4.1)

- [x] Update/Add tests in tests/unit/reporters/test_oneshot_reporter.py
  - [x] Verify OneShot is correctly mapped to a 2-turn conversation
  - [x] Verify Summary tables contain all Spec-required columns
  - [x] Verify HTML structure matches the Spec components

## Dev Notes

### Architecture Context

This story refactors the OneShot reporting to use the **Unified Reporting Spec**. 
We treat OneShot as a "Conversation of Length 1".

### Implementation Plan
1. Update `ReportData` models if necessary to align with Spec 4.1.
2. Refactor `oneshot.html` to use the new CSS spacing and component hierarchy defined in Spec 4.4.
3. Update `OneShotReporter` to populate the `ReportData` object.

## Dev Agent Record

### Implementation Plan
- Align existing `OneShotReporter` with the `Unified Reporting Spec`.
- Refactor the Jinja2 template to include the "crisp" spacing and sidebar/side-by-side variant comparison.

### Completion Notes
- Refactored `oneshot.html` and `oneshot.md` to use Unified Reporting Format.
- Implemented `Turn`, `VariantResult`, `ScenarioResult`, and `ReportData` in `src/gavel_ai/models/runtime.py`.
- Updated `OneShotReporter` to act as an adapter for the Unified Spec.
- OneShot input/output is now mapped to a USER/ASSISTANT turn pair.
- Added comprehensive unit tests for the new unified reporting logic.

## File List

- src/gavel_ai/reporters/oneshot_reporter.py
- src/gavel_ai/reporters/templates/oneshot.html
- tests/unit/reporters/test_oneshot_reporter.py

## Change Log

- 2026-01-19: Re-opened story for refactor to Unified Reporting Format.
