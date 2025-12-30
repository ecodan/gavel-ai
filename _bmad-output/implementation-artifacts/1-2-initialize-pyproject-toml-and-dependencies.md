# Story 1.2: Initialize pyproject.toml and Dependencies

Status: review

## Story

As a developer,
I want pyproject.toml configured with correct metadata, dependencies, and tool settings,
So that the project is distributable and all development tools are properly configured.

## Acceptance Criteria

1. **Project Metadata & Dependencies:**
   - Given an empty pyproject.toml
   - When configured per architecture
   - Then it specifies:
     - Project name: gavel-ai, version, description
     - Python 3.10+ requirement (no strict version barriers)
     - Core dependencies: pydantic-ai>=1.39.0, typer, deepeval, jinja2, pydantic, opentelemetry-api, rich
     - Development dependencies: pytest, black, ruff, mypy, pre-commit

2. **Tool Configuration:**
   - Given tool configuration in pyproject.toml
   - When tools are invoked (black, ruff, mypy)
   - Then they run with expected configurations

3. **Package Installation:**
   - Given the package is built
   - When installed with `pip install -e .`
   - Then the gavel command is available and CLI is invokable

## Tasks / Subtasks

- [x] Task 1: Create pyproject.toml with metadata (AC: #1)
  - [x] Project name, version, description
  - [x] Python version requirement
  - [x] Add core runtime dependencies
  - [x] Add optional development dependencies

- [x] Task 2: Configure tools in pyproject.toml (AC: #2)
  - [x] Black configuration (line-length: 100)
  - [x] Ruff configuration
  - [x] Mypy configuration
  - [x] Pytest configuration

- [x] Task 3: Verify installation (AC: #3)
  - [x] Test package can be imported
  - [x] Verify no import errors

### Review Follow-ups (AI Code Review)

- [x] [CRITICAL] Missing CLI entry point implementation - RESOLVED: cli/main.py:12 exists with app variable
- [x] [CRITICAL] Ruff configuration uses deprecated API - FIXED: Moved to [tool.ruff.lint] format [pyproject.toml:67-81]
- [x] [CRITICAL] No test verifies AC#3 (CLI invocation) - RESOLVED: tests/unit/test_cli.py exists with CLI tests
- [x] [MEDIUM] Ruff isort config references wrong module - FIXED: Changed to ["gavel_ai"] [pyproject.toml:81]
- [x] [LOW] Python version specifications - MINOR: Versions are consistent across tools

## Dev Notes

### Critical Dependencies

**Core Runtime (Minimal):**
- `pydantic-ai>=1.39.0` - MUST use this version for provider abstraction
- `typer` - CLI framework with hierarchical commands
- `deepeval` - LLM-as-judge evaluation
- `jinja2` - Report templating
- `pydantic>=2.0` - Data validation
- `opentelemetry-api` - Telemetry instrumentation
- `rich` - Terminal output formatting

**Development Tools:**
- `pytest>=7.0` - Testing framework
- `black>=23.0` - Code formatting (line-length: 100)
- `ruff>=0.1` - Fast linting with isort
- `mypy>=1.0` - Type checking (lenient mode)
- `pre-commit>=3.0` - Git hooks

### Tool Configuration Standards

From project-context.md:
- Black: line-length = 100
- Ruff: Include isort, all checks
- Mypy: Lenient on untyped code
- Pytest: Async support, test discovery from tests/

## File List

- `pyproject.toml` (modified/created)

## Change Log

- **2025-12-28:** Story created with complete pyproject.toml configuration
- **2025-12-28:** Implementation completed and tested
  - ✅ All acceptance criteria met
  - ✅ pyproject.toml configured with all dependencies and tool settings
  - ✅ Package installed successfully with `pip install -e .`
  - ✅ Tools configured: black, ruff, mypy, pytest
  - ✅ Included in test coverage with full test suite passing
