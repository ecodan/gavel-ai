# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**gavel-ai** is a Python project using the BMAD (Blended Methodology for Agentic Development) system. BMAD is an AI-assisted development framework that orchestrates multiple specialized agents to guide teams through product development phases: Analysis → Solutioning → Planning → Implementation.

The project uses Python 3.13+ with a minimal dependency footprint at the outset.

## Project Structure

- **pyproject.toml**: Python project metadata and dependencies (uses uv/pip for package management)
- **.python-version**: Specifies Python 3.13
- **_bmad/**: Contains the BMAD system configuration and workflows (do not edit directly)
  - `_bmad/bmm/config.yaml`: BMM module configuration with project metadata
  - `_bmad/core/config.yaml`: Core module configuration
  - `_bmad/_config/`: IDE and agent customizations for Claude Code
- **.claude/commands/**: Claude Code command definitions that expose BMAD workflows and agents
- **_bmad-output/**: Generated artifacts from BMAD workflows (planning, implementation docs)
- **docs/**: Project knowledge and documentation (referenced by BMAD for context)

## Development Commands

### Environment Setup
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies (add as needed to pyproject.toml)
pip install -e .
```

### Python Development
```bash
# Format code
python -m black src/

# Lint
python -m ruff check src/

# Type checking
python -m mypy src/

# Run tests
python -m pytest

# Run a single test
python -m pytest path/to/test.py::test_function
```

### BMAD Workflows (via Claude Code)

This project integrates with Claude Code skills to execute BMAD workflows:

- `/create-prd`: Develop product requirements document
- `/create-architecture`: Design system architecture
- `/create-epics-and-stories`: Break down requirements into implementation stories
- `/dev-story`: Execute a user story with implementation, tests, and validation
- `/sprint-planning`: Organize stories into sprints
- `/sprint-status`: Track sprint progress
- `/dev-story`: Implement a story from epics-and-stories output
- `/code-review`: Adversarial code review that finds 3-10 specific issues
- `/testarch-framework`: Initialize production-ready test framework (Playwright/Cypress)
- `/testarch-atdd`: Generate acceptance tests before implementation (TDD)
- `/testarch-automate`: Expand test automation coverage
- `/testarch-test-review`: Review test quality
- `/testarch-ci`: Scaffold CI/CD pipeline
- `/quick-dev`: Execute tech-specs or direct instructions with optional planning
- `/party-mode`: Multi-agent discussion orchestration

Detailed documentation exists in `.claude/commands/` for each skill.

## Code Style and Standards

Follow the global Python preferences in `/Users/dan/.claude/CLAUDE.md`:

### Imports and Type Hints
- All imports at the top of the file unless there's a strong reason for in-method imports
- Always add type hints in method signatures and variable declarations

### Logging
Use the standard log format:
```python
LOG_FORMAT = "%(asctime)s [%(levelname)s] <%(filename)s:%(lineno)s> %(message)s"
```

Create a centralized `log_config.py` with a module-level logger name and a `create_logger()` function that all modules can import:
```python
# log_config.py
import logging

LOGGER_NAME = "gavel-ai"

def create_logger(name: str = LOGGER_NAME) -> logging.Logger:
    logger = logging.getLogger(name)
    # Configure handlers (stdout, optional rotating file)
    return logger
```

## BMAD Workflow Outputs

BMAD artifacts are generated in `_bmad-output/`:
- **planning-artifacts/**: PRDs, architectures, epics, stories, tech specs
- **implementation-artifacts/**: Generated code, test frameworks, CI/CD configs

These documents are reference material for development and should inform implementation decisions.

## Git Workflow

- Only commit when explicitly requested by the user
- No proactive commits of code changes or file edits
- This maintains user control over version control

## Testing Strategy

BMAD includes comprehensive test architecture workflows:
- Use ATDD (Acceptance Test-Driven Development) for new features
- Leverage test frameworks (Playwright for UI, pytest for unit/integration)
- Test quality reviews are part of the development process
- CI/CD pipelines are scaffolded before implementation

### Test Layout

- `tests/unit/` — fast, no external dependencies; marked `@pytest.mark.unit`
- `tests/integration/` — real filesystem + mocked LLM calls; marked `@pytest.mark.integration`
  - `test_oneshot_pipeline_e2e.py` — end-to-end `ScenarioProcessorStep` coverage (happy path, prompt version resolution, error cases)

Run with:
```bash
pytest -m unit          # unit tests only
pytest -m integration   # integration tests only
```

## Agent Customizations

Claude Code integrates with BMAD agents through `.claude/_config/agents/`:
- **bmm-dev**: Development-focused agent
- **bmm-architect**: Architecture and design decisions
- **bmm-pm**: Product and requirements
- **bmm-sm**: Scrum master for sprint coordination
- **bmm-tea**: Test and QA automation
- **bmm-tech-writer**: Documentation generation
- **bmm-ux-designer**: UX/UI design
- **bmm-analyst**: Requirements and analysis
- **quick-flow-solo-dev**: Streamlined solo development flow

Each agent is configured with specific prompts and model parameters in customization files.

## Key Architectural Patterns

This project follows BMAD's phase-driven development:

1. **Analysis Phase**: Understand requirements and domain
2. **Solutioning Phase**: Design architecture and data models
3. **Planning Phase**: Create epics, stories, and sprints
4. **Implementation Phase**: Develop stories with tests and reviews

Each phase produces artifacts that feed into subsequent phases, ensuring alignment between requirements, design, and implementation.

## Common Tasks

- **Adding a new feature**: Start with `/create-epics-and-stories` to decompose requirements, then use `/dev-story` to implement
- **Reviewing code**: Use `/code-review` for adversarial review that identifies specific issues
- **Setting up tests**: Use `/testarch-framework` for scaffolding, then `/testarch-atdd` for test-first development
- **Performance optimization**: Profile first, then implement targeted optimizations
- **Documentation**: Use `/tech-writer` agent for generating comprehensive docs

## References

- BMAD Documentation: `_bmad/bmm/docs/`
- Project Knowledge: `docs/`
- BMAD Configuration: `_bmad/bmm/config.yaml`, `_bmad/core/config.yaml`
