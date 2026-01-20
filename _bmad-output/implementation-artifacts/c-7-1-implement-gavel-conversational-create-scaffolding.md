# Story C-7.1: Implement `gavel conversational create` Scaffolding

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want `gavel conversational create --eval <name>` to scaffold evaluations,
so that I can get started quickly.

## Acceptance Criteria

1. **Given** `gavel conversational create --eval my_conv_eval` executed
   **When** completed
   **Then** directory created: `.gavel/evaluations/my_conv_eval/` with structure:
   - config/ (agents.json, eval_config.json, async_config.json)
   - data/ (scenarios.json, scenarios.csv template)
   - prompts/ (default.toml)
   - runs/ (empty)

2. **Given** eval_config.json scaffolded
   **When** examined
   **Then** contains conversational-specific defaults: workflow_type="conversational", max_turns=10, elaboration_enabled=false

3. **Given** scenarios.json scaffolded
   **When** examined
   **Then** contains 2-3 example scenarios with user_goal, context, dialogue_guidance filled in

4. **Given** scaffolded eval created
   **When** modified by user
   **Then** ready for `gavel conversational run`

## Tasks / Subtasks

- [ ] Task 1: Create `conv create` CLI command (AC: 1)
  - [ ] Subtask 1.1: Add `create` subcommand to `conv` command group in Typer
  - [ ] Subtask 1.2: Add `--eval` parameter for evaluation name
  - [ ] Subtask 1.3: Add optional `--template` parameter for custom scaffolding templates
- [ ] Task 2: Implement directory scaffolding (AC: 1)
  - [ ] Subtask 2.1: Create `.gavel/evaluations/<name>/` directory structure
  - [ ] Subtask 2.2: Create subdirectories: config/, data/, prompts/, runs/
  - [ ] Subtask 2.3: Handle existing evaluation directories (error or update?)
- [ ] Task 3: Generate eval_config.json with conversational defaults (AC: 2)
  - [ ] Subtask 3.1: Load conversational config schema
  - [ ] Subtask 3.2: Set workflow_type="conversational"
  - [ ] Subtask 3.3: Set max_turns=10, elaboration_enabled=false (and other conversational-specific fields)
  - [ ] Subtask 3.4: Write to config/eval_config.json
- [ ] Task 4: Generate agents.json and async_config.json scaffolds (AC: 1)
  - [ ] Subtask 4.1: Create agents.json with example agent definitions
  - [ ] Subtask 4.2: Create async_config.json with default async settings
- [ ] Task 5: Generate example scenarios (AC: 3)
  - [ ] Subtask 5.1: Create scenarios.json with 2-3 example ConversationScenario objects
  - [ ] Subtask 5.2: Include user_goal, context, dialogue_guidance fields in examples
  - [ ] Subtask 5.3: Make examples realistic and self-documenting
- [ ] Task 6: Generate prompts/default.toml (AC: 1)
  - [ ] Subtask 6.1: Create default.toml with prompt templates
  - [ ] Subtask 6.2: Include turn generation prompt template
- [ ] Task 7: Generate scenarios.csv template (AC: 1)
  - [ ] Subtask 7.1: Create scenarios.csv.template showing CSV structure for scenarios
  - [ ] Subtask 7.2: Include headers and 1-2 example rows
- [ ] Task 8: Implement error handling and user feedback (AC: 1, 4)
  - [ ] Subtask 8.1: Validate evaluation name (alphanumeric, hyphens, underscores)
  - [ ] Subtask 8.2: Display success message with created evaluation path
  - [ ] Subtask 8.3: Handle directory creation errors gracefully

## Dev Notes

- The `gavel conversational create` command extends the existing Typer CLI structure
- Follow patterns established in `gavel oneshot create` implementation (see Epic 2 stories)
- Scaffolding should be idempotent (safe to run again)
- Conversational defaults differ from OneShot defaults - ensure proper separation
- Review existing ConversationScenario and eval_config schema from Epic C-1 stories

### Architecture Alignment

- **Command Pattern**: Extend `src/gavel_ai/cli/commands/conv.py` with `create` subcommand
- **Scaffolding Logic**: Use `src/gavel_ai/scaffolding/conversational_scaffolder.py` (may need to create)
- **Config Schema**: Use `gavel_ai.config.conversational_config.ConversationalEvalConfig` (defined in C-1.4)
- **Directory Root**: `.gavel/evaluations/<name>/` (consistent with OneShot pattern)
- **Error Handling**: Follow project's error format (FR-9.1) with clear recovery guidance

### Project Structure Notes

- CLI code: `src/gavel_ai/cli/commands/conv.py` (already exists from C-2)
- Scaffolding: `src/gavel_ai/scaffolding/` directory pattern
- Config models: `src/gavel_ai/config/` directory
- Templates: `templates/scaffolding/conversational/` for TOML/JSON templates

### References

- [Source: epics-conversational-eval.md#Story-C7.1](epics-conversational-eval.md#Story-C7.1)
- [Source: _bmad-output/implementation-artifacts/c-1-4-extend-eval-config-json-with-conversational-schema.md](c-1-4-extend-eval-config-json-with-conversational-schema.md)
- [Source: _bmad-output/implementation-artifacts/c-1-1-define-scenario-schema-with-user-goal-and-context.md](c-1-1-define-scenario-schema-with-user-goal-and-context.md)
- [Source: architecture.md#CLI-Structure](../../planning-artifacts/architecture.md#CLI-Structure)
- Related Requirements: FR-C7.1, FR-1.1 (setup & config), FR-1.2 (JSON persistence)

## Dev Agent Record

### Agent Model Used

Claude-4.5-Sonnet-latest

### Debug Log References

### Completion Notes List

### File List
